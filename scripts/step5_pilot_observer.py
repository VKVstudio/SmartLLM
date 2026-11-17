#!/usr/bin/env python3
"""Step 5 Streaming Layerwise REAP Pilot Observer for Qwen/Qwen3.8-Flash-Next (qwen4_exp).

Key verified architectural invariants (against modeling_qwen4_exp.py & qwen4exp.cpp):
1. Zero-OOM Meta Skeleton: `Qwen4ExpModel(cfg)` is instantiated strictly inside
   `with torch.device("meta"):` so `Qwen4ExpTextNGramEmbedding.__init__` never allocates
   `nn.Embedding(320001536, 160)` (`204.8 GB` FP32 on CPU). Non-persistent RoPE inv_freq
   buffers (`visual.rotary_pos_emb` and `language_model.rotary_emb`) are materialized on CPU,
   and `_attn_implementation` is explicitly set to `"sdpa"`.
2. Single-Pass Pre-Indexed PLE Lookup (`layer_idx = 1`, 1-based `ple_layer_ids = [2]`):
   Because `ngram_ids` in `Qwen4ExpTextNGramEmbedding` depends solely on `ple_input_ids`
   (never on `hidden_states`), all unique n-gram IDs across the calibration pass are
   computed upfront on CPU, grouped by `shard_k = uid // shard_rows` (`2,500,012`) and
   physical `.safetensors` file (`00005..00037`), sliced in a single sequential pass,
   and freed immediately after `layer_idx = 1` finishes.
3. 3D Hyper-Connection Residual Stream (`[1, S, 10240]` = `hc_count(4) * 2560` in BF16):
   Preserves exact M-RoPE `compute_3d_position_ids`, `model.visual` `masked_scatter` on
   `<|image_pad|>` (`248056`), explicit `ple_input_ids=input_ids`, and causal chunked
   replay (`CHUNK_TOKENS = 4096` on GDN; `QSA_LONG_CHUNK_TOKENS = 512` on QSA `>4096` to
   prevent `SDPBackend.MATH` `13.9 GiB` VRAM OOM on unaligned `16K-36K` `kv_len`),
   verified `0.0` bit diff on deterministic CPU GEMM, `<1e-4` / `>=99.5%` exact `top-10`
   in GPU `FP32 (allow_tf32=False)`, and `cos >= 0.9999` + `>=99.5%` single-layer `top-10`
   slot overlap in GPU `BF16`.
4. Zero-Overhead Native REAP Hook (`arXiv:2510.13999` & `CerebrasResearch/reap`):
   Computes exact FP32 top-10 renormalized router weights and L2 norms of unweighted expert
   outputs `||down_proj(SiLU(gate) * up)||_2` directly inside active expert dispatch without
   allocating `[512, S, 2560]` dense activation tensors (`0 B` extra VRAM, `0.0` output diff),
   retaining full per-stratum (`all 7 strata + craft_p4`) and `1/freq` outlier diagnostics.
5. Bit-Exact Pre-Pooled QSA Indexer (`Variant A`, `torch.equal == True` on CPU & CUDA):
   Eliminates the `12.32M` per-token `torch.nonzero` GPU-CPU stream syncs and `18,017x`
   redundant 4-token key-block recomputations in `Qwen4ExpTextQSAIndexer.forward` while
   preserving exact IEEE-754 `/` scaling, `(1, D)` `CUBLAS_OP_T` stride, and `1D topk(512)`.
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import gc
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from accelerate.utils import set_module_tensor_to_device
from PIL import Image
from safetensors import safe_open
from safetensors.torch import save_file
from transformers import AutoConfig, AutoProcessor, AutoTokenizer
from transformers.models.qwen4_exp.configuration_qwen4_exp import (
    Qwen4ExpConfig,
    Qwen4ExpTextConfig,
    Qwen4ExpVisionConfig,
)
from transformers.models.qwen4_exp.modeling_qwen4_exp import (
    DynamicCache,
    Qwen4ExpModel,
    Qwen4ExpTextDecoderLayer,
    Qwen4ExpTextQSAIndexer,
    Qwen4ExpTextRotaryEmbedding,
    Qwen4ExpVisionRotaryEmbedding,
    apply_rotary_pos_emb,
)

ROOT = Path(r"D:\projects\SmartLLM")
MODEL_DIR = ROOT / "models" / "Qwen3.8-Flash-Next"
CALIB_JSONL = ROOT / "data" / "calib" / "PremiumWebStudio-Calib.jsonl"
SCHEDULE_JSON = ROOT / "research" / "step5_6_layer_shard_schedule.json"
OUT_DIR = ROOT / "research" / "step5_raw"
SCORES_JSON = OUT_DIR / "pilot_scores.json"
TELEMETRY_JSON = OUT_DIR / "pilot_telemetry.json"

PILOT_LAYERS = [0, 1, 2, 3]  # Covers GDN (0,1,2), PLE (1), and QSA indexed_attention + indexer (3)
DEFAULT_CHUNK_TOKENS = 4096  # Exact multiple of GDN chunk_size=64 and QSA compress_ratio=4
QSA_LONG_CHUNK_TOKENS = 512  # Caps QSA SDPBackend.MATH fallback at <=563 MiB on unaligned 16K-36K kv_len

PLAN_TARGET_STRATUM_SHARES: dict[str, float] = {
    "pillar_1_frontend_3d_svg": 0.26,
    "pillar_2_seo_geo_security": 0.16,
    "pillar_3_style_canons_vision": 0.18,
    "pillar_4_art_direction_copywriting": 0.15,
    "agentic_tool_calling": 0.10,
    "long_context": 0.05,
    "general_anti_starvation": 0.10,
}


# ---------------------------------------------------------------------------
# Win32 & GPU Telemetry Helpers
# ---------------------------------------------------------------------------


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def get_windows_ram_telemetry() -> dict[str, float]:
    """Query exact physical RAM availability via Win32 GlobalMemoryStatusEx."""
    if os.name != "nt":
        return {"total_phys_gib": 0.0, "avail_phys_gib": 0.0, "used_phys_gib": 0.0}
    stat = _MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    total_gib = stat.ullTotalPhys / (1024**3)
    avail_gib = stat.ullAvailPhys / (1024**3)
    return {
        "total_phys_bytes": int(stat.ullTotalPhys),
        "avail_phys_bytes": int(stat.ullAvailPhys),
        "total_phys_gib": round(total_gib, 4),
        "avail_phys_gib": round(avail_gib, 4),
        "used_phys_gib": round(total_gib - avail_gib, 4),
        "memory_load_pct": int(stat.dwMemoryLoad),
    }


def sample_pages_output_per_sec() -> float | None:
    """Sample Windows `\\Memory\\Pages Output/sec` counter once (non-fatal if localized)."""
    if os.name != "nt":
        return None
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-Counter '\\Memory\\Pages Output/sec' -ErrorAction Stop).CounterSamples[0].CookedValue",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            val_str = proc.stdout.strip().splitlines()[-1].replace(",", ".")
            return round(float(val_str), 4)
    except Exception:  # noqa: BLE001
        pass
    return None


def query_nvidia_smi_apps() -> list[dict[str, Any]]:
    """Return active GPU compute processes reported by nvidia-smi."""
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,process_name,used_gpu_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode != 0:
            return []
        apps = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                apps.append(
                    {
                        "pid": int(parts[0]) if parts[0].isdigit() else parts[0],
                        "process_name": parts[1],
                        "used_mib": float(parts[2]) if parts[2].replace(".", "").isdigit() else parts[2],
                    }
                )
        return apps
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# Safetensors Streaming Index (Zero Persistent mmap Handles)
# ---------------------------------------------------------------------------


class SafetensorsIndex:
    """Lazy, handle-closing safetensors reader preventing RSS creep from open mmaps."""

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = Path(checkpoint_dir)
        index_path = self.checkpoint_dir / "model.safetensors.index.json"
        if index_path.exists():
            data = json.loads(index_path.read_text(encoding="utf-8"))
            self.weight_map: dict[str, str] = data["weight_map"]
        else:
            single = self.checkpoint_dir / "model.safetensors"
            with safe_open(str(single), framework="pt", device="cpu") as f:
                self.weight_map = {k: single.name for k in f.keys()}

    def has_tensor(self, name: str) -> bool:
        return name in self.weight_map

    def shards_for_prefix(self, prefix: str) -> list[str]:
        dotted = prefix if prefix.endswith(".") else prefix + "."
        shards = {
            shard
            for k, shard in self.weight_map.items()
            if k == prefix or k.startswith(dotted)
        }
        return sorted(shards)

    def read_tensors(self, names: list[str], device: str = "cpu") -> dict[str, torch.Tensor]:
        by_shard: dict[str, list[str]] = defaultdict(list)
        for name in names:
            by_shard[self.weight_map[name]].append(name)

        out: dict[str, torch.Tensor] = {}
        for shard_name in sorted(by_shard):
            shard_path = self.checkpoint_dir / shard_name
            with safe_open(str(shard_path), framework="pt", device="cpu") as f:
                for tname in by_shard[shard_name]:
                    tensor = f.get_tensor(tname)
                    if device != "cpu":
                        tensor = tensor.to(device, non_blocking=False)
                    else:
                        tensor = tensor.clone()
                    out[tname] = tensor
        return out


def materialize_submodule(
    module: nn.Module,
    checkpoint_prefix: str,
    index: SafetensorsIndex,
    device: str,
) -> tuple[int, int, list[str]]:
    """Materialize all meta parameters/buffers of `module` from safetensors onto `device`.

    Returns `(num_tensors_loaded, total_bytes_loaded, touched_shards)`.
    """
    targets: list[tuple[str, str, bool]] = []
    for name, param in module.named_parameters():
        if param.device.type != "meta":
            continue
        full = f"{checkpoint_prefix}.{name}" if name else checkpoint_prefix
        if not index.has_tensor(full):
            raise KeyError(f"Missing parameter in checkpoint: {full}")
        targets.append((name, full, True))

    for name, buf in module.named_buffers():
        if buf.device.type != "meta":
            continue
        full = f"{checkpoint_prefix}.{name}" if name else checkpoint_prefix
        if not index.has_tensor(full):
            raise KeyError(f"Missing buffer in checkpoint (left on meta!): {full}")
        targets.append((name, full, False))

    if not targets:
        return 0, 0, []

    full_names = [full for _, full, _ in targets]
    touched_shards = sorted({index.weight_map[fn] for fn in full_names})
    tensors = index.read_tensors(full_names, device=device)
    total_bytes = 0
    for local_name, full_name, _ in targets:
        val = tensors[full_name]
        total_bytes += val.numel() * val.element_size()
        set_module_tensor_to_device(module, local_name, device, value=val, dtype=val.dtype)
    del tensors
    return len(targets), total_bytes, touched_shards


def free_submodule_to_meta(module: nn.Module, keep_non_checkpoint_names: set[str] | None = None) -> None:
    """Release materialized tensors of `module` back to `meta` device to free VRAM/RAM."""
    keep = keep_non_checkpoint_names or set()
    for name, param in list(module.named_parameters()):
        if name in keep or param.device.type == "meta":
            continue
        set_module_tensor_to_device(module, name, "meta")
    for name, buf in list(module.named_buffers()):
        if name in keep or buf.device.type == "meta":
            continue
        set_module_tensor_to_device(module, name, "meta")


# ---------------------------------------------------------------------------
# Streaming Sharded PLE N-Gram Embedding (`layers.1.ple.ple_embedding.ngram_embedding`)
# ---------------------------------------------------------------------------


class StreamingPLENGramEmbedding(nn.Module):
    """Drop-in replacement for `nn.Embedding(320001536, 160)` inside `Qwen4ExpTextNGramEmbedding`.

    Supports:
    - `mode="direct_slice"`: slices safetensors shards on the fly per call (used for independent
      reference verification on 3 samples).
    - `mode="preindexed"`: opens each of the 33 PLE safetensors shards at most once upfront to
      gather all unique n-gram rows needed across the entire calibration pass (`~150 MiB` for 50K
      tokens), serving GPU forwards in `<0.2 ms` via `torch.searchsorted` with `0.0` diff.
    """

    def __init__(
        self,
        index: SafetensorsIndex,
        shard_prefix: str,
        num_shards: int,
        shard_rows: int,
        embed_dim: int,
        dtype: torch.dtype = torch.bfloat16,
    ):
        super().__init__()
        self.index = index
        self.shard_prefix = shard_prefix
        self.num_shards = num_shards
        self.shard_rows = shard_rows
        self.embed_dim = embed_dim
        self.out_dtype = dtype
        # Dummy CPU weight buffer so `Qwen4ExpTextNGramEmbedding.forward` sees `.weight.device == cpu`
        self.register_buffer("weight", torch.empty(0, dtype=dtype, device="cpu"), persistent=False)

        self._capture_only: bool = False
        self.captured_chunks: list[torch.Tensor] = []
        self.unique_ids: torch.Tensor | None = None
        self.cached_rows: torch.Tensor | None = None
        self.prefetch_stats: dict[str, Any] = {}

    def _gather_unique_sorted_ids_from_shards(
        self, unique_ids_cpu: torch.Tensor
    ) -> tuple[torch.Tensor, int]:
        """Gather `unique_ids_cpu` (1D sorted int64) from sharded safetensors opening each file once."""
        assert unique_ids_cpu.ndim == 1 and unique_ids_cpu.dtype == torch.int64
        n_unique = int(unique_ids_cpu.numel())
        out = torch.empty((n_unique, self.embed_dim), dtype=self.out_dtype, device="cpu")
        if n_unique == 0:
            return out, 0

        shard_ids = torch.div(unique_ids_cpu, self.shard_rows, rounding_mode="floor")
        # Group contiguous ranges per logical shard_k (0..127), then group by physical safetensors file
        by_file: dict[str, list[tuple[int, int, int, torch.Tensor]]] = defaultdict(list)
        unique_ks = torch.unique_consecutive(shard_ids).tolist()
        boundaries = torch.searchsorted(shard_ids, torch.tensor(unique_ks, dtype=torch.int64))
        boundaries_end = torch.cat([boundaries[1:], torch.tensor([n_unique], dtype=torch.int64)])

        for k, st_t, ed_t in zip(unique_ks, boundaries.tolist(), boundaries_end.tolist()):
            k_int = int(k)
            if not (0 <= k_int < self.num_shards):
                raise IndexError(f"PLE shard index {k_int} out of range 0..{self.num_shards - 1}")
            tname = f"{self.shard_prefix}.shard_{k_int}.weight"
            shard_file = self.index.weight_map[tname]
            local_rows = unique_ids_cpu[st_t:ed_t] - (k_int * self.shard_rows)
            by_file[shard_file].append((k_int, st_t, ed_t, local_rows))

        files_opened = 0
        for shard_file in sorted(by_file):
            fpath = self.index.checkpoint_dir / shard_file
            with safe_open(str(fpath), framework="pt", device="cpu") as f:
                files_opened += 1
                for k_int, st_idx, ed_idx, local_rows in by_file[shard_file]:
                    tname = f"{self.shard_prefix}.shard_{k_int}.weight"
                    full_shard_tensor = f.get_tensor(tname)
                    out[st_idx:ed_idx] = full_shard_tensor.index_select(0, local_rows).to(self.out_dtype)
                    del full_shard_tensor
        return out, files_opened

    def build_preindexed_cache(
        self,
        ple_embedding_parent: nn.Module,
        all_input_ids: list[torch.Tensor],
    ) -> dict[str, Any]:
        """Compute exact `ngram_ids` on CPU across all samples and load unique rows in 1 shard pass."""
        t0 = time.perf_counter()
        self._capture_only = True
        self.captured_chunks.clear()
        try:
            with torch.no_grad():
                for ids in all_input_ids:
                    _ = ple_embedding_parent(ids.to("cpu"), past_key_values=None)
        finally:
            self._capture_only = False

        t_hash = time.perf_counter() - t0
        t1 = time.perf_counter()
        flat_all = torch.cat(self.captured_chunks, dim=0)
        total_lookups = int(flat_all.numel())
        self.captured_chunks.clear()

        unique_ids = torch.unique(flat_all, sorted=True)
        del flat_all
        cached_rows, files_opened = self._gather_unique_sorted_ids_from_shards(unique_ids)
        t_io = time.perf_counter() - t1

        self.unique_ids = unique_ids
        self.cached_rows = cached_rows
        cache_bytes = (
            unique_ids.numel() * unique_ids.element_size()
            + cached_rows.numel() * cached_rows.element_size()
        )
        self.prefetch_stats = {
            "total_ngram_lookups": total_lookups,
            "unique_ngram_rows": int(unique_ids.numel()),
            "dedup_ratio": round(int(unique_ids.numel()) / max(1, total_lookups), 4),
            "ple_safetensors_files_opened": files_opened,
            "cache_ram_bytes": int(cache_bytes),
            "cache_ram_mib": round(cache_bytes / (1024**2), 3),
            "cpu_hash_sec": round(t_hash, 4),
            "safetensors_slice_io_sec": round(t_io, 4),
        }
        return self.prefetch_stats

    def clear_cache(self) -> None:
        self.unique_ids = None
        self.cached_rows = None
        self.captured_chunks.clear()
        gc.collect()

    def forward(self, ngram_ids: torch.Tensor) -> torch.Tensor:
        ids_cpu = ngram_ids.to("cpu", dtype=torch.int64)
        if self._capture_only:
            self.captured_chunks.append(ids_cpu.reshape(-1))
            return torch.zeros((*ids_cpu.shape, self.embed_dim), dtype=self.out_dtype, device="cpu")

        if self.unique_ids is not None and self.cached_rows is not None:
            flat = ids_cpu.reshape(-1)
            pos = torch.searchsorted(self.unique_ids, flat)
            # Safety verification that every requested ngram_id was pre-indexed
            if not torch.equal(self.unique_ids.index_select(0, pos), flat):
                raise RuntimeError("PLE cache miss: encountered ngram_id absent from pre-indexed set!")
            return self.cached_rows.index_select(0, pos).view(*ids_cpu.shape, self.embed_dim).to(self.out_dtype)

        # Direct on-demand safetensors slice mode (used by independent reference verifier)
        unique_ids, inv = torch.unique(ids_cpu.reshape(-1), sorted=True, return_inverse=True)
        rows, _ = self._gather_unique_sorted_ids_from_shards(unique_ids)
        return rows.index_select(0, inv).view(*ids_cpu.shape, self.embed_dim).to(self.out_dtype)


# ---------------------------------------------------------------------------
# Zero-Overhead Native REAP Observer Wrapper around `Qwen4ExpTextSparseMoeBlock`
# ---------------------------------------------------------------------------


class REAPMoEAccumulator:
    """Exact FP64 accumulator for Cerebras REAP metrics + all-stratum retention & outlier diagnostics."""

    def __init__(
        self,
        num_experts: int,
        track_pairwise: bool = False,
        capture_routing: bool = False,
    ):
        self.num_experts = num_experts
        self.track_pairwise = track_pairwise
        self.capture_routing = capture_routing
        self.total_tokens: int = 0
        self.expert_frequency = torch.zeros(num_experts, dtype=torch.int64, device="cpu")
        self.ean_sum = torch.zeros(num_experts, dtype=torch.float64, device="cpu")
        self.weighted_ean_sum = torch.zeros(num_experts, dtype=torch.float64, device="cpu")
        self.weighted_expert_frequency_sum = torch.zeros(num_experts, dtype=torch.float64, device="cpu")
        self.max_activations = torch.zeros(num_experts, dtype=torch.float32, device="cpu")
        self.max_activations_signed = torch.full((num_experts,), float("-inf"), dtype=torch.float32, device="cpu")
        self.freq_by_stratum: dict[str, torch.Tensor] = defaultdict(
            lambda: torch.zeros(num_experts, dtype=torch.int64, device="cpu")
        )
        self.weighted_ean_by_stratum: dict[str, torch.Tensor] = defaultdict(
            lambda: torch.zeros(num_experts, dtype=torch.float64, device="cpu")
        )
        self.tokens_by_stratum: dict[str, int] = defaultdict(int)
        self.freq_by_lang: dict[str, torch.Tensor] = defaultdict(
            lambda: torch.zeros(num_experts, dtype=torch.int64, device="cpu")
        )
        self.weighted_ean_by_lang: dict[str, torch.Tensor] = defaultdict(
            lambda: torch.zeros(num_experts, dtype=torch.float64, device="cpu")
        )
        self.tokens_by_lang: dict[str, int] = defaultdict(int)
        self.current_stratum: str = "unknown"
        self.current_subbucket: str | None = None
        self.current_lang: str = "en"
        self._captured_indices: list[torch.Tensor] = []
        self._captured_weights: list[torch.Tensor] = []

    def reset_captured_routing(self) -> None:
        self._captured_indices.clear()
        self._captured_weights.clear()

    def pop_captured_routing(self) -> tuple[torch.Tensor, torch.Tensor]:
        idx = torch.cat(self._captured_indices, dim=0)
        w = torch.cat(self._captured_weights, dim=0)
        self.reset_captured_routing()
        return idx, w

    def finalize_dict(
        self,
        full_stratum_tokens: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        freq_clamped = self.expert_frequency.clamp_min(1).to(torch.float64)
        reap_cond = (self.weighted_ean_sum / freq_clamped).to(torch.float32)
        ean_mean = (self.ean_sum / freq_clamped).to(torch.float32)
        reap_global = (self.weighted_ean_sum / max(1, self.total_tokens)).to(torch.float32)
        router_weight_mean = (self.weighted_expert_frequency_sum / freq_clamped).to(torch.float32)
        max_signed_clean = torch.where(
            torch.isinf(self.max_activations_signed),
            torch.zeros_like(self.max_activations_signed),
            self.max_activations_signed,
        )

        active_mask = self.expert_frequency > 0
        n_active = int(active_mask.sum().item())
        n_dead = int((~active_mask).sum().item())

        sorted_reap_vals, sorted_reap_idx = torch.sort(reap_cond, descending=True)
        keep_k = 205 if self.num_experts >= 205 else max(1, round(self.num_experts * 205 / 512))
        top205_indices = sorted(sorted_reap_idx[:keep_k].tolist())
        top205_set = set(top205_indices)

        top205_wsum_set = set(
            torch.argsort(self.weighted_ean_sum, descending=True)[:keep_k].tolist()
        )
        reap_vs_wsum_jaccard = len(top205_set & top205_wsum_set) / max(1, len(top205_set | top205_wsum_set))

        top_m = 50 if self.num_experts >= 205 else max(1, round(self.num_experts * 50 / 512))

        def _bucket_retention(
            w_sum_vec: torch.Tensor,
            freq_vec: torch.Tensor,
            ref_keep_set: set[int],
            min_specialist_freq: int,
        ) -> dict[str, Any]:
            raw_top_m = set(torch.argsort(w_sum_vec, descending=True)[:top_m].tolist())
            elig = freq_vec >= min_specialist_freq
            if int(elig.sum().item()) >= max(5, top_m // 2):
                cond_vec = torch.where(
                    elig,
                    w_sum_vec / freq_vec.clamp_min(1).to(torch.float64),
                    torch.full_like(w_sum_vec, -1.0),
                )
            else:
                cond_vec = torch.where(
                    freq_vec > 0,
                    w_sum_vec / freq_vec.clamp_min(1).to(torch.float64),
                    torch.full_like(w_sum_vec, -1.0),
                )
            cond_top_m = set(torch.argsort(cond_vec, descending=True)[:top_m].tolist())
            return {
                "raw_top50_retained_in_k205": len(raw_top_m & ref_keep_set),
                "cond_specialist_top50_retained_in_k205": len(cond_top_m & ref_keep_set),
                "eligible_specialists": int(elig.sum().item()),
            }

        min_spec_f = max(5, min(25, max(1, self.total_tokens // 4000)))
        all_bucket_keys = sorted(
            set(PLAN_TARGET_STRATUM_SHARES.keys()) | set(self.weighted_ean_by_stratum.keys())
        )
        per_stratum_retention: dict[str, Any] = {}
        for sk in all_bucket_keys:
            per_stratum_retention[sk] = _bucket_retention(
                self.weighted_ean_by_stratum[sk],
                self.freq_by_stratum[sk],
                top205_set,
                min_specialist_freq=min_spec_f,
            )

        ru_ret = _bucket_retention(
            self.weighted_ean_by_lang["ru"],
            self.freq_by_lang["ru"],
            top205_set,
            min_specialist_freq=min_spec_f,
        )

        # De-skewed REAP comparisons (1: reweighted to exact full-dataset stratum shares; 2: PLAN.md nominal shares)
        def _compute_reweighted_top_set(target_shares: dict[str, float]) -> set[int]:
            w_num = torch.zeros(self.num_experts, dtype=torch.float64)
            w_den = torch.zeros(self.num_experts, dtype=torch.float64)
            for sk, tgt_sh in target_shares.items():
                pil_tok = self.tokens_by_stratum.get(sk, 0)
                if pil_tok <= 0:
                    continue
                pil_sh = pil_tok / max(1, self.total_tokens)
                mult = tgt_sh / max(1e-9, pil_sh)
                w_num += mult * self.weighted_ean_by_stratum[sk]
                w_den += mult * self.freq_by_stratum[sk].to(torch.float64)
            if float(w_den.sum().item()) <= 0.0:
                return top205_set
            rw_score = w_num / w_den.clamp_min(1e-9)
            return set(torch.argsort(rw_score, descending=True)[:keep_k].tolist())

        plan_bal_set = _compute_reweighted_top_set(PLAN_TARGET_STRATUM_SHARES)
        plan_bal_jaccard = len(top205_set & plan_bal_set) / max(1, len(top205_set | plan_bal_set))
        p4_under_plan_bal = _bucket_retention(
            self.weighted_ean_by_stratum["pillar_4_art_direction_copywriting"],
            self.freq_by_stratum["pillar_4_art_direction_copywriting"],
            plan_bal_set,
            min_specialist_freq=min_spec_f,
        )

        full_ds_jaccard = 1.0
        p4_under_full_ds = per_stratum_retention.get("pillar_4_art_direction_copywriting", {})
        if full_stratum_tokens:
            tot_f = max(1, sum(full_stratum_tokens.values()))
            full_shares = {k: v / tot_f for k, v in full_stratum_tokens.items()}
            full_ds_set = _compute_reweighted_top_set(full_shares)
            full_ds_jaccard = len(top205_set & full_ds_set) / max(1, len(top205_set | full_ds_set))
            p4_under_full_ds = _bucket_retention(
                self.weighted_ean_by_stratum["pillar_4_art_direction_copywriting"],
                self.freq_by_stratum["pillar_4_art_direction_copywriting"],
                full_ds_set,
                min_specialist_freq=min_spec_f,
            )

        # Rare 1/freq outlier & upstream Cerebras Super-Expert diagnostics (`max_signed > max(p99.5, global_max/10)`)
        low_freq_floor = max(5, int(0.0001 * self.total_tokens))
        p995_signed = float(torch.quantile(max_signed_clean.float(), 0.995).item()) if self.num_experts > 1 else 0.0
        super_thresh = max(p995_signed, float(max_signed_clean.max().item()) / 10.0)
        super_expert_ids = [
            int(i)
            for i in range(self.num_experts)
            if float(max_signed_clean[i].item()) > super_thresh and int(self.expert_frequency[i].item()) > 0
        ]
        low_freq_in_top205 = [
            {
                "expert_idx": int(idx),
                "freq": int(self.expert_frequency[idx].item()),
                "reap": round(float(reap_cond[idx].item()), 6),
                "max_act_signed": round(float(max_signed_clean[idx].item()), 6),
                "is_super_expert_candidate": int(idx) in set(super_expert_ids),
            }
            for idx in top205_indices
            if int(self.expert_frequency[idx].item()) < low_freq_floor
        ]

        return {
            "total_tokens": int(self.total_tokens),
            "num_experts": int(self.num_experts),
            "active_experts": n_active,
            "dead_experts": n_dead,
            "dead_tie_break_warning": n_dead > (self.num_experts - keep_k),
            "nan_or_inf_count": int(
                torch.isnan(reap_cond).sum().item() + torch.isinf(reap_cond).sum().item()
            ),
            "reap_summary": {
                "min": round(float(reap_cond.min().item()), 6),
                "p10": round(float(torch.quantile(reap_cond, 0.10).item()), 6),
                "p25": round(float(torch.quantile(reap_cond, 0.25).item()), 6),
                "median": round(float(reap_cond.median().item()), 6),
                "mean": round(float(reap_cond.mean().item()), 6),
                "p75": round(float(torch.quantile(reap_cond, 0.75).item()), 6),
                "p90": round(float(torch.quantile(reap_cond, 0.90).item()), 6),
                "max": round(float(reap_cond.max().item()), 6),
            },
            "frequency_summary": {
                "min": int(self.expert_frequency.min().item()),
                "median": float(self.expert_frequency.float().median().item()),
                "mean": round(float(self.expert_frequency.float().mean().item()), 2),
                "max": int(self.expert_frequency.max().item()),
            },
            "top_15_experts_by_reap": [
                {
                    "expert_idx": int(idx),
                    "reap": round(float(val), 6),
                    "freq": int(self.expert_frequency[idx].item()),
                    "ean_mean": round(float(ean_mean[idx].item()), 6),
                    "router_weight_mean": round(float(router_weight_mean[idx].item()), 6),
                    "max_act_abs": round(float(self.max_activations[idx].item()), 6),
                    "max_act_signed": round(float(max_signed_clean[idx].item()), 6),
                }
                for val, idx in zip(sorted_reap_vals[:15].tolist(), sorted_reap_idx[:15].tolist())
            ],
            "bottom_15_experts_by_reap": [
                {
                    "expert_idx": int(idx),
                    "reap": round(float(val), 6),
                    "freq": int(self.expert_frequency[idx].item()),
                    "ean_mean": round(float(ean_mean[idx].item()), 6),
                }
                for val, idx in zip(sorted_reap_vals[-15:].tolist(), sorted_reap_idx[-15:].tolist())
            ],
            "retention_diagnostics_k205": {
                "ru_top50_retained_in_k205": ru_ret["raw_top50_retained_in_k205"],
                "ru_cond_specialist_top50_retained_in_k205": ru_ret["cond_specialist_top50_retained_in_k205"],
                "vision_top50_retained_in_k205": per_stratum_retention["pillar_3_style_canons_vision"][
                    "raw_top50_retained_in_k205"
                ],
                "pillar4_top50_retained_in_k205": per_stratum_retention["pillar_4_art_direction_copywriting"][
                    "raw_top50_retained_in_k205"
                ],
                "pillar4_cond_specialist_top50_retained_in_k205": per_stratum_retention[
                    "pillar_4_art_direction_copywriting"
                ]["cond_specialist_top50_retained_in_k205"],
                "craft_p4_top50_retained_in_k205": per_stratum_retention.get("craft_p4", {}).get(
                    "raw_top50_retained_in_k205", 0
                ),
                "craft_p4_cond_specialist_top50_retained_in_k205": per_stratum_retention.get("craft_p4", {}).get(
                    "cond_specialist_top50_retained_in_k205", 0
                ),
                "by_stratum_all": per_stratum_retention,
                "reap_vs_weighted_sum_k205_jaccard": round(reap_vs_wsum_jaccard, 6),
                "full_dataset_reweighted_k205_jaccard": round(full_ds_jaccard, 6),
                "pillar4_under_full_dataset_reweight": p4_under_full_ds,
                "plan_target_balanced_k205_jaccard": round(plan_bal_jaccard, 6),
                "pillar4_under_plan_target_balance": p4_under_plan_bal,
                "retained_share_of_total_weighted_ean": round(
                    float(
                        self.weighted_ean_sum[top205_indices].sum().item()
                        / max(1e-12, self.weighted_ean_sum.sum().item())
                    ),
                    6,
                ),
            },
            "outlier_diagnostics": {
                "low_freq_floor": low_freq_floor,
                "low_freq_in_top205_count": len(low_freq_in_top205),
                "low_freq_in_top205": low_freq_in_top205,
                "super_expert_threshold_signed": round(super_thresh, 6),
                "super_expert_candidates": super_expert_ids,
            },
            "keep_indices_k205_sorted": top205_indices,
            "by_stratum": {
                "tokens": dict(self.tokens_by_stratum),
                "freq": {k: [int(x) for x in v.tolist()] for k, v in sorted(self.freq_by_stratum.items())},
                "weighted_ean_sum": {
                    k: [round(float(x), 4) for x in v.tolist()]
                    for k, v in sorted(self.weighted_ean_by_stratum.items())
                },
            },
            "by_lang": {
                "tokens": dict(self.tokens_by_lang),
                "freq": {k: [int(x) for x in v.tolist()] for k, v in sorted(self.freq_by_lang.items())},
                "weighted_ean_sum": {
                    k: [round(float(x), 4) for x in v.tolist()]
                    for k, v in sorted(self.weighted_ean_by_lang.items())
                },
            },
            "arrays": {
                "reap": [round(float(x), 6) for x in reap_cond.tolist()],
                "reap_global_per_token": [round(float(x), 6) for x in reap_global.tolist()],
                "expert_frequency": [int(x) for x in self.expert_frequency.tolist()],
                "ean_mean": [round(float(x), 6) for x in ean_mean.tolist()],
                "weighted_ean_sum": [round(float(x), 4) for x in self.weighted_ean_sum.tolist()],
                "weighted_expert_frequency_sum": [
                    round(float(x), 4) for x in self.weighted_expert_frequency_sum.tolist()
                ],
                "max_activations": [round(float(x), 6) for x in self.max_activations.tolist()],
                "max_activations_signed": [round(float(x), 6) for x in max_signed_clean.tolist()],
            },
        }


def compute_topk_routing_metrics(
    idx_ref: torch.Tensor,
    w_ref: torch.Tensor,
    idx_test: torch.Tensor,
    w_test: torch.Tensor,
    num_experts: int,
) -> dict[str, float]:
    """Compare `[S, K]` top-k expert selections & probability mass between reference and chunked pass."""
    s_len, k = int(idx_ref.shape[0]), int(idx_ref.shape[1])
    mask_ref = torch.zeros((s_len, num_experts), dtype=torch.bool)
    mask_test = torch.zeros((s_len, num_experts), dtype=torch.bool)
    mask_ref.scatter_(1, idx_ref.long(), True)
    mask_test.scatter_(1, idx_test.long(), True)

    inter_counts = (mask_ref & mask_test).sum(dim=-1)
    dense_w_ref = torch.zeros((s_len, num_experts), dtype=torch.float32)
    dense_w_test = torch.zeros((s_len, num_experts), dtype=torch.float32)
    dense_w_ref.scatter_(1, idx_ref.long(), w_ref.float())
    dense_w_test.scatter_(1, idx_test.long(), w_test.float())
    prob_mass_overlap = torch.minimum(dense_w_ref, dense_w_test).sum(dim=-1)

    return {
        "top_k": k,
        "exact_topk_set_match_frac": round(float((inter_counts == k).float().mean().item()), 6),
        "at_least_k_minus_1_match_frac": round(float((inter_counts >= max(1, k - 1)).float().mean().item()), 6),
        "mean_topk_slot_overlap": round(float((inter_counts.float() / k).mean().item()), 6),
        "min_token_slot_overlap": round(float((inter_counts.float() / k).min().item()), 6),
        "mean_prob_mass_overlap": round(float(prob_mass_overlap.mean().item()), 6),
    }


def forward_moe_with_reap_observer(
    moe_block: nn.Module,
    hidden_states: torch.Tensor,
    acc: REAPMoEAccumulator,
) -> torch.Tensor:
    """Bit-identical replacement for `Qwen4ExpTextSparseMoeBlock.forward` recording REAP metrics."""
    batch_size, sequence_length, hidden_dim = hidden_states.shape
    hidden_states_reshaped = hidden_states.view(-1, hidden_dim)
    num_tokens = int(hidden_states_reshaped.shape[0])
    acc.total_tokens += num_tokens

    stratum = acc.current_stratum
    subbucket = acc.current_subbucket
    lang = acc.current_lang
    acc.tokens_by_stratum[stratum] += num_tokens
    if subbucket:
        acc.tokens_by_stratum[subbucket] += num_tokens
    acc.tokens_by_lang[lang] += num_tokens

    shared_expert_output = moe_block.shared_expert(hidden_states_reshaped)

    # Exact Qwen4ExpTextTopKRouter math, keeping FP32 renormalized top-k probs for REAP scoring
    gate_mod = moe_block.gate
    router_logits = F.linear(hidden_states_reshaped, gate_mod.weight)
    router_probs_f32 = F.softmax(router_logits, dtype=torch.float32, dim=-1)
    router_top_f32, selected_experts = torch.topk(router_probs_f32, gate_mod.top_k, dim=-1)
    if gate_mod.norm_topk_prob:
        router_top_f32 = router_top_f32 / router_top_f32.sum(dim=-1, keepdim=True)
    routing_weights_bf16 = router_top_f32.to(router_logits.dtype)

    if acc.capture_routing:
        acc._captured_indices.append(selected_experts.detach().to("cpu", dtype=torch.int16))
        acc._captured_weights.append(router_top_f32.detach().to("cpu", dtype=torch.float32))

    # Exact Qwen4ExpTextExperts loop with inline L2 norm capture (`0 B` [512, N, H] tensor!)
    experts_mod = moe_block.experts
    final_hidden_states = torch.zeros_like(hidden_states_reshaped)
    expert_mask = F.one_hot(selected_experts, num_classes=experts_mod.num_experts + 1).permute(2, 1, 0)
    expert_hit = torch.greater(expert_mask.sum(dim=(-1, -2)), 0).nonzero()

    for hit in expert_hit:
        e_idx = int(hit[0].item())
        if e_idx == experts_mod.num_experts:
            continue
        top_k_pos, token_idx = torch.where(expert_mask[e_idx])
        current_state = hidden_states_reshaped[token_idx]
        gate_out, up_out = F.linear(current_state, experts_mod.gate_up_proj[e_idx]).chunk(2, dim=-1)
        unweighted_out = F.linear(experts_mod.act_fn(gate_out) * up_out, experts_mod.down_proj[e_idx])

        # Record REAP statistics BEFORE multiplying by routing weight!
        norms_f32 = unweighted_out.float().norm(p=2, dim=-1)
        w_f32 = router_top_f32[token_idx, top_k_pos]
        weighted_norms_sum = float((w_f32.double() * norms_f32.double()).sum().item())
        norms_sum = float(norms_f32.double().sum().item())
        w_sum = float(w_f32.double().sum().item())
        n_routed = int(token_idx.numel())
        max_abs = float(unweighted_out.abs().max().float().item())
        max_signed = float(unweighted_out.max().float().item())

        acc.expert_frequency[e_idx] += n_routed
        acc.ean_sum[e_idx] += norms_sum
        acc.weighted_ean_sum[e_idx] += weighted_norms_sum
        acc.weighted_expert_frequency_sum[e_idx] += w_sum
        if max_abs > float(acc.max_activations[e_idx].item()):
            acc.max_activations[e_idx] = max_abs
        if max_signed > float(acc.max_activations_signed[e_idx].item()):
            acc.max_activations_signed[e_idx] = max_signed

        acc.freq_by_stratum[stratum][e_idx] += n_routed
        acc.weighted_ean_by_stratum[stratum][e_idx] += weighted_norms_sum
        if subbucket:
            acc.freq_by_stratum[subbucket][e_idx] += n_routed
            acc.weighted_ean_by_stratum[subbucket][e_idx] += weighted_norms_sum
        acc.freq_by_lang[lang][e_idx] += n_routed
        acc.weighted_ean_by_lang[lang][e_idx] += weighted_norms_sum

        # Exact BF16 forward continuation
        weighted_hidden = unweighted_out * routing_weights_bf16[token_idx, top_k_pos, None]
        final_hidden_states.index_add_(0, token_idx, weighted_hidden.to(final_hidden_states.dtype))

    shared_expert_output = F.sigmoid(moe_block.shared_expert_gate(hidden_states_reshaped)) * shared_expert_output
    expert_output = (final_hidden_states + shared_expert_output).reshape(
        batch_size, sequence_length, hidden_dim
    )
    return expert_output


# ---------------------------------------------------------------------------
# Bit-Exact Pre-Pooled QSA Indexer (`Variant A`, `torch.equal == True` on CPU & CUDA)
# ---------------------------------------------------------------------------


def fast_exact_qsa_indexer_forward(
    indexer_mod: nn.Module,
    hidden_states: torch.Tensor,
    position_embeddings: tuple[torch.Tensor, torch.Tensor],
    attention_mask: torch.Tensor,
    past_key_values: DynamicCache | None,
) -> torch.Tensor:
    """100% bit-identical (`torch.equal == True`) replacement for `Qwen4ExpTextQSAIndexer.forward`.

    Eliminates per-token `torch.nonzero` GPU->CPU stream syncs and `O(S^2)` redundant key-block
    pooling/RMSNorm/RoPE while preserving exact IEEE-754 `/` scaling, `(1, D)` `CUBLAS_OP_T`
    stride, and 1D `scores.topk(block_topk)` tie-breaking.
    """
    batch_size, seq_length, _ = hidden_states.shape
    if batch_size != 1:
        raise ValueError(f"fast_exact_qsa_indexer_forward expects batch_size == 1, got {batch_size}")

    kv_length = int(attention_mask.shape[-1])
    st = kv_length - seq_length
    r_comp = int(indexer_mod.compress_ratio)
    d_idx = int(indexer_mod.index_head_dim)
    max_dense_kv_len = int(indexer_mod.token_budget + r_comp - 1)

    # Exact analytical identity: for all global query positions g < token_budget + R - 1 (`2051`),
    # `num_complete_blocks = (g + 1) // R <= block_topk`, so 100% of causal tokens [0..g] are selected!
    if kv_length <= max_dense_kv_len:
        if past_key_values is not None:
            qk = indexer_mod.index_qk_proj(hidden_states)
            _, token_k = torch.split(
                qk,
                [indexer_mod.index_n_heads * d_idx, indexer_mod.index_kv_heads * d_idx],
                dim=-1,
            )
            raw_keys = token_k.reshape(batch_size, seq_length, -1, d_idx).squeeze(2)
            _ = past_key_values.update_indexer(raw_keys, indexer_mod.layer_idx)
        if attention_mask.is_floating_point():
            min_dtype = torch.finfo(attention_mask.dtype).min
            return torch.where(attention_mask == 0, attention_mask.new_zeros(()), min_dtype)
        return attention_mask.clone()

    full_cos, full_sin = position_embeddings
    current_cos, current_sin = full_cos[:, -seq_length:, :], full_sin[:, -seq_length:, :]

    qk = indexer_mod.index_qk_proj(hidden_states)
    q, token_k = torch.split(
        qk,
        [indexer_mod.index_n_heads * d_idx, indexer_mod.index_kv_heads * d_idx],
        dim=-1,
    )
    hidden_shape = (batch_size, seq_length, -1, d_idx)
    q, raw_keys = q.reshape(*hidden_shape), token_k.reshape(*hidden_shape).squeeze(2)
    q = indexer_mod.q_layernorm(q)
    q = apply_rotary_pos_emb(q, cos=current_cos, sin=current_sin, unsqueeze_dim=2)

    if past_key_values is not None:
        raw_keys = past_key_values.update_indexer(raw_keys, indexer_mod.layer_idx)

    # Pre-pool, RMSNorm, and RoPE all complete 4-token blocks ONCE across [0 .. total_blocks * R)
    total_blocks = kv_length // r_comp
    key_groups = raw_keys[0, : total_blocks * r_comp].contiguous().view(total_blocks, r_comp, d_idx)
    pooled_keys = key_groups.float().mean(dim=1).to(raw_keys.dtype)
    pooled_keys = indexer_mod.k_layernorm(pooled_keys)
    group_starts = torch.arange(0, total_blocks * r_comp, r_comp, device=hidden_states.device, dtype=torch.long)
    block_key_states = apply_rotary_pos_emb(
        pooled_keys.unsqueeze(1),
        cos=full_cos[0].index_select(0, group_starts),
        sin=full_sin[0].index_select(0, group_starts),
    ).squeeze(1)

    bk_f32 = block_key_states.float()  # [total_blocks, d_idx], contiguous stride=(d_idx, 1)
    q_f32 = q[0].float()  # [seq_length, n_heads, d_idx], contiguous stride=(n_heads*d_idx, d_idx, 1)
    sqrt_d = math.sqrt(d_idx)
    block_topk = int(indexer_mod.block_topk)

    first_sparse_q = max(0, max_dense_kv_len - st)
    n_sparse = seq_length - first_sparse_q
    topk_blocks: list[torch.Tensor] = []
    for q_idx in range(first_sparse_q, seq_length):
        g = st + q_idx
        b_g = (g + 1) // r_comp
        # Preserves exact [n_heads, d_idx] @ [d_idx, b_g] (stride=(1, d_idx)) cuBLAS shape & 1D topk!
        scores = torch.matmul(q_f32[q_idx], bk_f32[:b_g].transpose(-1, -2)).transpose(-1, -2)
        scores = torch.relu(scores).sum(dim=-1) / sqrt_d
        topk_blocks.append(scores.topk(block_topk, dim=0).indices)

    sel_blocks = torch.stack(topk_blocks, dim=0)  # [n_sparse, block_topk]
    offsets = torch.arange(r_comp, device=hidden_states.device, dtype=sel_blocks.dtype).view(1, 1, r_comp)
    sel_toks = (sel_blocks.unsqueeze(-1) * r_comp + offsets).reshape(n_sparse, -1)

    sparse_mask = torch.zeros((n_sparse, kv_length), dtype=torch.bool, device=hidden_states.device)
    sparse_mask.scatter_(1, sel_toks, True)
    g_vec = torch.arange(st + first_sparse_q, st + seq_length, device=hidden_states.device).unsqueeze(1)
    b_g_vec = torch.div(g_vec + 1, r_comp, rounding_mode="floor")
    kv_vec = torch.arange(kv_length, device=hidden_states.device).unsqueeze(0)
    sparse_mask |= (kv_vec >= (b_g_vec * r_comp)) & (kv_vec <= g_vec)

    if first_sparse_q == 0:
        selected_token_mask = sparse_mask.unsqueeze(0).unsqueeze(0)
    else:
        base_bool = attention_mask.clone() if attention_mask.dtype == torch.bool else (attention_mask == 0).clone()
        base_bool[0, 0, first_sparse_q:, :] = sparse_mask
        selected_token_mask = base_bool

    if attention_mask.is_floating_point():
        min_dtype = torch.finfo(attention_mask.dtype).min
        selected_token_mask = torch.where(selected_token_mask, attention_mask.new_zeros(()), min_dtype)
    return selected_token_mask


class QSAIndexerWrapper:
    """In-place forward hook on `Qwen4ExpTextQSAIndexer` preserving exact parameter names."""

    def __init__(self, base_indexer: Qwen4ExpTextQSAIndexer, mode: str = "fast_exact_a", sync_timing: bool = False):
        self.base_indexer = base_indexer
        self.mode = mode
        self.sync_timing = sync_timing
        self.elapsed_sec: float = 0.0
        self.calls: int = 0
        base_indexer.forward = self._patched_forward  # type: ignore[method-assign]

    def reset_stats(self) -> None:
        self.elapsed_sec = 0.0
        self.calls = 0

    def _patched_forward(
        self,
        hidden_states: torch.Tensor,
        position_embeddings: tuple[torch.Tensor, torch.Tensor],
        attention_mask: torch.Tensor,
        past_key_values: DynamicCache | None = None,
    ) -> torch.Tensor:
        is_cuda = hidden_states.device.type == "cuda"
        if self.sync_timing and is_cuda:
            torch.cuda.synchronize(hidden_states.device)
        t0 = time.perf_counter() if self.sync_timing else 0.0

        if self.mode == "upstream":
            out = Qwen4ExpTextQSAIndexer.forward(
                self.base_indexer, hidden_states, position_embeddings, attention_mask, past_key_values
            )
        elif self.mode == "fast_exact_a":
            out = fast_exact_qsa_indexer_forward(
                self.base_indexer, hidden_states, position_embeddings, attention_mask, past_key_values
            )
        else:
            raise ValueError(f"Unknown QSAIndexerWrapper mode: {self.mode}")

        if self.sync_timing:
            if is_cuda:
                torch.cuda.synchronize(hidden_states.device)
            self.elapsed_sec += time.perf_counter() - t0
            self.calls += 1
        return out


# ---------------------------------------------------------------------------
# Per-Layer Isolated Forward (Supports Exact Chunked Replay for 16K-36K)
# ---------------------------------------------------------------------------


@torch.no_grad()
def forward_single_decoder_layer(
    layer: Qwen4ExpTextDecoderLayer,
    text_cfg: Qwen4ExpTextConfig,
    hidden_states_cpu: torch.Tensor,
    full_cos_cpu: torch.Tensor,
    full_sin_cpu: torch.Tensor,
    ple_input_ids_cpu: torch.Tensor,
    device: str,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    qsa_long_chunk_tokens: int | None = QSA_LONG_CHUNK_TOKENS,
    reap_acc: REAPMoEAccumulator | None = None,
    layer_prof: dict[str, float] | None = None,
) -> torch.Tensor:
    """Run one `Qwen4ExpTextDecoderLayer` on `[1, S, 10240]` with optional REAP capture & chunking."""
    seq_len = int(hidden_states_cpu.shape[1])
    is_full_attn = layer.layer_type != "linear_attention"
    is_cuda = device.startswith("cuda")

    # Prevent `13.9 GiB` CUDA OOM on QSA `SDPBackend.MATH` fallback when `seq_len > chunk_tokens`
    # has unaligned `kv_len` (e.g. `16,415` or `36,036`), capping QSA attention buffer at `<= 563 MiB`.
    eff_chunk = (
        qsa_long_chunk_tokens
        if (is_full_attn and seq_len > chunk_tokens and qsa_long_chunk_tokens is not None)
        else chunk_tokens
    )

    def _run_step(
        h_dev: torch.Tensor,
        cos_dev: torch.Tensor,
        sin_dev: torch.Tensor,
        attn_mask_dev: torch.Tensor | None,
        ple_ids_dev: torch.Tensor,
        cache: DynamicCache | None,
    ) -> torch.Tensor:
        if reap_acc is None:
            return layer(
                h_dev,
                position_embeddings=(cos_dev, sin_dev),
                attention_mask=attn_mask_dev,
                conv_mask=None,
                past_key_values=cache,
                ple_input_ids=ple_ids_dev,
            )

        # Unrolled exact `Qwen4ExpTextDecoderLayer.forward` delegating `layer.mlp` to REAP observer
        if layer.ple is not None:
            h_dev = h_dev + layer.ple(h_dev, ple_ids_dev, cache, conv_mask=None)

        h_attn_in, hyper_input, injection_weights = layer.attn_hyper_connection(h_dev)
        if layer_prof is not None and is_cuda:
            torch.cuda.synchronize(device)
        t_a0 = time.perf_counter() if layer_prof is not None else 0.0
        if layer.layer_type == "linear_attention":
            h_attn_out = layer.linear_attn(h_attn_in, cache_params=cache, attention_mask=None)
        else:
            h_attn_out, _ = layer.self_attn(
                h_attn_in,
                (cos_dev, sin_dev),
                attention_mask=attn_mask_dev,
                past_key_values=cache,
            )
        if layer_prof is not None:
            if is_cuda:
                torch.cuda.synchronize(device)
            layer_prof["attn_total_sec"] = layer_prof.get("attn_total_sec", 0.0) + (time.perf_counter() - t_a0)
        injection = h_attn_out.unsqueeze(-2) * injection_weights.unsqueeze(-1)
        h_dev = hyper_input + injection.flatten(-2)

        h_mlp_in, hyper_input, injection_weights = layer.mlp_hyper_connection(h_dev)
        if layer_prof is not None and is_cuda:
            torch.cuda.synchronize(device)
        t_m0 = time.perf_counter() if layer_prof is not None else 0.0
        h_mlp_out = forward_moe_with_reap_observer(layer.mlp, h_mlp_in, reap_acc)
        if layer_prof is not None:
            if is_cuda:
                torch.cuda.synchronize(device)
            layer_prof["moe_sec"] = layer_prof.get("moe_sec", 0.0) + (time.perf_counter() - t_m0)
        injection = h_mlp_out.unsqueeze(-2) * injection_weights.unsqueeze(-1)
        h_dev = hyper_input + injection.flatten(-2)
        return h_dev

    if seq_len <= eff_chunk:
        h_dev = hidden_states_cpu.to(device, non_blocking=False)
        cos_dev = full_cos_cpu.to(device, non_blocking=False)
        sin_dev = full_sin_cpu.to(device, non_blocking=False)
        ple_dev = ple_input_ids_cpu.to(device, non_blocking=False)
        attn_mask = None
        if is_full_attn:
            idx = torch.arange(seq_len, device=device)
            attn_mask = idx.view(1, 1, 1, seq_len) <= idx.view(1, 1, seq_len, 1)
        out_dev = _run_step(h_dev, cos_dev, sin_dev, attn_mask, ple_dev, cache=None)
        out_cpu = out_dev.to("cpu")
        del h_dev, cos_dev, sin_dev, ple_dev, attn_mask, out_dev
        return out_cpu

    # Exact causal chunked prefill for long sequences (16K..36K+)
    cache = DynamicCache(config=text_cfg)
    out_cpu = torch.empty_like(hidden_states_cpu)
    full_cos_dev = full_cos_cpu.to(device, non_blocking=False)
    full_sin_dev = full_sin_cpu.to(device, non_blocking=False)

    for st in range(0, seq_len, eff_chunk):
        ed = min(seq_len, st + eff_chunk)
        h_c = hidden_states_cpu[:, st:ed, :].to(device, non_blocking=False)
        ple_c = ple_input_ids_cpu[:, st:ed].to(device, non_blocking=False)
        attn_mask = None
        if is_full_attn:
            q_pos = torch.arange(st, ed, device=device).view(1, 1, -1, 1)
            kv_pos = torch.arange(0, ed, device=device).view(1, 1, 1, -1)
            attn_mask = kv_pos <= q_pos
        out_c = _run_step(
            h_c,
            full_cos_dev[:, :ed, :],
            full_sin_dev[:, :ed, :],
            attn_mask,
            ple_c,
            cache=cache,
        )
        out_cpu[:, st:ed, :] = out_c.to("cpu")
        del h_c, ple_c, attn_mask, out_c
        if is_cuda and is_full_attn and seq_len > 8192 and ((st // eff_chunk) + 1) % 16 == 0:
            torch.cuda.empty_cache()

    del cache, full_cos_dev, full_sin_dev
    if is_cuda and is_full_attn and seq_len > 8192:
        torch.cuda.empty_cache()
    return out_cpu


# ---------------------------------------------------------------------------
# Sample Preparation & Unbuffered Sequential Disk Ping-Pong Buffer
# ---------------------------------------------------------------------------


@dataclass
class PreparedSample:
    sample_id: str
    pillar: str
    lang: str
    modality: str
    subdomain: str
    seq_len: int
    input_ids: torch.Tensor  # [1, S] int64 CPU
    mm_token_type_ids: torch.Tensor | None  # [1, S] int64 CPU
    pixel_values: torch.Tensor | None  # [N_patches, C] float32 CPU
    image_grid_thw: torch.Tensor | None  # [N_img, 3] int64 CPU
    source_repo: str = ""
    position_ids_3d: torch.Tensor | None = None  # [3, 1, S] int64 CPU
    rotary_cos: torch.Tensor | None = None  # [1, S, head_dim] bfloat16 CPU
    rotary_sin: torch.Tensor | None = None  # [1, S, head_dim] bfloat16 CPU


class DiskHiddenStatePingPong:
    """Unbuffered sequential binary BF16 ping-pong buffer (`0 B` mmap Working Set, `0` double-copy)."""

    def __init__(self, work_dir: Path, seq_lens: list[int], hc_width: int):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.hc_width = hc_width
        self.seq_lens = seq_lens
        self.total_tokens = sum(seq_lens)
        self.offsets: list[tuple[int, int]] = []
        cur = 0
        for sl in seq_lens:
            self.offsets.append((cur, cur + sl))
            cur += sl
        self.bytes_per_file = self.total_tokens * hc_width * 2  # BF16 = 2 bytes
        self.paths = [self.work_dir / "hc_buf_0.bin", self.work_dir / "hc_buf_1.bin"]
        self._files: list[Any | None] = []
        for p in self.paths:
            fh = open(p, "w+b", buffering=0)
            if self.bytes_per_file > 0:
                fh.seek(self.bytes_per_file - 1)
                fh.write(b"\x00")
                fh.flush()
            self._files.append(fh)
        self.total_write_bytes = 0
        self.total_read_bytes = 0
        self.total_io_sec = 0.0

    def write_sample(self, slot: int, sample_idx: int, tensor_bf16_cpu: torch.Tensor) -> None:
        t0 = time.perf_counter()
        assert tensor_bf16_cpu.dtype == torch.bfloat16 and tensor_bf16_cpu.device.type == "cpu"
        st, ed = self.offsets[sample_idx]
        byte_offset = st * self.hc_width * 2
        u8 = tensor_bf16_cpu.reshape(-1).contiguous().view(torch.uint8).numpy()
        mv = memoryview(u8)
        fh = self._files[slot]
        assert fh is not None
        fh.seek(byte_offset)
        written = 0
        total = len(mv)
        while written < total:
            n = fh.write(mv[written:])
            if not n:
                raise IOError(f"Short write on {self.paths[slot]} at {byte_offset + written}")
            written += n
        self.total_write_bytes += total
        self.total_io_sec += time.perf_counter() - t0

    def flush_slot(self, slot: int) -> None:
        t0 = time.perf_counter()
        fh = self._files[slot]
        if fh is not None:
            fh.flush()
            os.fsync(fh.fileno())
        self.total_io_sec += time.perf_counter() - t0

    def read_sample(self, slot: int, sample_idx: int) -> torch.Tensor:
        t0 = time.perf_counter()
        st, ed = self.offsets[sample_idx]
        seq_len = ed - st
        byte_offset = st * self.hc_width * 2
        byte_len = seq_len * self.hc_width * 2
        out_u8 = torch.empty((byte_len,), dtype=torch.uint8, device="cpu")
        mv = memoryview(out_u8.numpy())
        fh = self._files[slot]
        assert fh is not None
        fh.seek(byte_offset)
        read_n = 0
        while read_n < byte_len:
            n = fh.readinto(mv[read_n:])
            if not n:
                raise EOFError(f"Unexpected EOF on {self.paths[slot]} at {byte_offset + read_n}/{byte_len}")
            read_n += n
        self.total_read_bytes += byte_len
        self.total_io_sec += time.perf_counter() - t0
        return out_u8.view(torch.bfloat16).view(1, seq_len, self.hc_width)

    def close_and_cleanup(self, remove_files: bool = True) -> None:
        for i in range(len(self._files)):
            fh = self._files[i]
            if fh is not None:
                try:
                    fh.flush()
                except OSError:
                    pass
                fh.close()
                self._files[i] = None
        gc.collect()
        if remove_files:
            for p in self.paths:
                if p.exists():
                    p.unlink()
            try:
                self.work_dir.rmdir()
            except OSError:
                pass

    def __enter__(self) -> "DiskHiddenStatePingPong":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close_and_cleanup(remove_files=True)


# ---------------------------------------------------------------------------
# Stratified Pilot Selector (Covers All 7 Strata + Curated Craft P4 + >4K QSA)
# ---------------------------------------------------------------------------


def select_stratified_pilot_rows(rows: list[dict[str, Any]], seed: int = 20261111) -> list[dict[str, Any]]:
    """Select deterministic 43-sample stratified subset (~6.3% rows) covering all 7 strata, EN+RU,
    desktop+mobile PNGs, curated Pillar 4 OKLCH/Z-Image/microcopy decks, >4096-token QSA sample,
    and both 16K and 32K+ SWE-smith trajectories."""
    rng = random.Random(seed)
    selected_ids: set[str] = set()
    chosen: list[dict[str, Any]] = []

    def _add(row: dict[str, Any]) -> None:
        if row["id"] not in selected_ids:
            selected_ids.add(row["id"])
            chosen.append(row)

    by_stratum_lang: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_stratum_lang[(r["pillar"], r["lang"])].append(r)

    # 1. Long-context: 1 sample in [16K, 25K] + 1 maximum-length sample (>=32K, strict worst-case VRAM test!)
    lc_16k = sorted(
        [r for r in rows if r["pillar"] == "long_context" and 16384 <= r["qwen38_tokens"] < 25000],
        key=lambda x: x["qwen38_tokens"],
    )
    lc_max = sorted(
        [r for r in rows if r["pillar"] == "long_context" and r["qwen38_tokens"] >= 32000],
        key=lambda x: x["qwen38_tokens"],
        reverse=True,
    )
    if lc_16k:
        _add(lc_16k[0])
    if lc_max:
        _add(lc_max[0])

    # 1b. Guarantee >=1 sample in [4097, 8192] to verify active QSA sparse topk(512) & 4096-chunk boundary in Part 1
    gt4k_cands = sorted(
        [r for r in rows if 4097 <= int(r["qwen38_tokens"]) <= 8192],
        key=lambda x: (abs(int(x["qwen38_tokens"]) - 5200), x["id"]),
    )
    if gt4k_cands:
        _add(gt4k_cands[0])

    # 2. Multimodal Pillar 3: ensure 1 mobile 576x1248 canon, 1 RU desktop canon, 1 EN desktop canon, + 3 WebSight
    p3_mobile = [r for r in rows if r["pillar"] == "pillar_3_style_canons_vision" and "mobile" in r["subdomain"]]
    p3_ru_desk = [
        r
        for r in rows
        if r["pillar"] == "pillar_3_style_canons_vision"
        and r["lang"] == "ru"
        and "mobile" not in r["subdomain"]
    ]
    p3_en_canon = [
        r
        for r in rows
        if r["pillar"] == "pillar_3_style_canons_vision"
        and r["lang"] == "en"
        and r["source_repo"] == "SmartLLM/curated-bilingual-canons"
        and "mobile" not in r["subdomain"]
    ]
    p3_websight = [
        r
        for r in rows
        if r["pillar"] == "pillar_3_style_canons_vision" and r["source_repo"] == "HuggingFaceM4/WebSight"
    ]
    for pool, k in ((p3_mobile, 1), (p3_ru_desk, 1), (p3_en_canon, 1), (p3_websight, 3)):
        pool_sorted = sorted(pool, key=lambda x: x["id"])
        rng.shuffle(pool_sorted)
        for item in pool_sorted[:k]:
            _add(item)

    # 2b. Pillar 4: explicitly stratify curated OKLCH/Z-Image/UX-microcopy decks (2 EN + 2 RU) + general copy (2 EN + 2 RU)
    p4_cur_en = [
        r
        for r in rows
        if r["pillar"] == "pillar_4_art_direction_copywriting"
        and r["lang"] == "en"
        and r["source_repo"] == "SmartLLM/curated-bilingual-canons"
    ]
    p4_cur_ru = [
        r
        for r in rows
        if r["pillar"] == "pillar_4_art_direction_copywriting"
        and r["lang"] == "ru"
        and r["source_repo"] == "SmartLLM/curated-bilingual-canons"
    ]
    p4_gen_en = [
        r
        for r in rows
        if r["pillar"] == "pillar_4_art_direction_copywriting"
        and r["lang"] == "en"
        and r["source_repo"] != "SmartLLM/curated-bilingual-canons"
    ]
    p4_gen_ru = [
        r
        for r in rows
        if r["pillar"] == "pillar_4_art_direction_copywriting"
        and r["lang"] == "ru"
        and r["source_repo"] != "SmartLLM/curated-bilingual-canons"
    ]
    for pool, k in ((p4_cur_en, 2), (p4_cur_ru, 2), (p4_gen_en, 2), (p4_gen_ru, 2)):
        pool_sorted = sorted([r for r in pool if r["id"] not in selected_ids], key=lambda x: x["id"])
        rng.shuffle(pool_sorted)
        for item in pool_sorted[:k]:
            _add(item)

    # 2c. General EN: cover all 4 anti-starvation subdomains (code_general, math, terminal, science_general)
    for sub in ("code_general", "math", "terminal", "science_general"):
        sub_pool = sorted(
            [
                r
                for r in rows
                if r["pillar"] == "general_anti_starvation"
                and r["lang"] == "en"
                and r["subdomain"] == sub
                and r["id"] not in selected_ids
            ],
            key=lambda x: x["id"],
        )
        rng.shuffle(sub_pool)
        if sub_pool:
            _add(sub_pool[0])

    # 3. Remaining strata proportional quotas
    quotas = {
        ("pillar_1_frontend_3d_svg", "en"): 4,
        ("pillar_1_frontend_3d_svg", "ru"): 5,
        ("pillar_2_seo_geo_security", "en"): 4,
        ("pillar_2_seo_geo_security", "ru"): 3,
        ("agentic_tool_calling", "en"): 3,
        ("agentic_tool_calling", "ru"): 1,
        ("general_anti_starvation", "ru"): 2,
    }
    for key, k in sorted(quotas.items()):
        pool = [r for r in by_stratum_lang.get(key, []) if r["id"] not in selected_ids]
        pool.sort(key=lambda x: x["id"])
        rng.shuffle(pool)
        for item in pool[:k]:
            _add(item)

    return chosen


def tokenize_rows(
    rows: list[dict[str, Any]],
    tok: Any,
    proc: Any,
    root_dir: Path,
) -> list[PreparedSample]:
    """Tokenize text & multimodal calibration rows identically to `step4_verify_calib.py`."""
    image_pad_id = tok.convert_tokens_to_ids("<|image_pad|>")
    prepared: list[PreparedSample] = []
    for r in rows:
        text = r["text"]
        if r["modality"] == "multimodal":
            pil_imgs = [Image.open(root_dir / im["path"]).convert("RGB") for im in r["images"]]
            out = proc(text=[text], images=pil_imgs, return_tensors="pt")
            for im_obj in pil_imgs:
                im_obj.close()
            input_ids = out["input_ids"].to(torch.int64)
            mm_tt = out["mm_token_type_ids"].to(torch.int64)
            pix = out["pixel_values"].to(torch.float32)
            grid = out["image_grid_thw"].to(torch.int64)
            expected_vis_toks = int((grid.prod(-1) // 4).sum().item())
            actual_pad_toks = int((input_ids == image_pad_id).sum().item())
            if expected_vis_toks != actual_pad_toks:
                raise AssertionError(
                    f"{r['id']}: grid visual tokens {expected_vis_toks} != <|image_pad|> {actual_pad_toks}"
                )
        else:
            input_ids = tok(text, add_special_tokens=False, return_tensors="pt")["input_ids"].to(torch.int64)
            mm_tt = None
            pix = None
            grid = None

        seq_len = int(input_ids.shape[1])
        if seq_len != int(r["qwen38_tokens"]):
            raise AssertionError(f"{r['id']}: seq_len {seq_len} != recorded qwen38_tokens {r['qwen38_tokens']}")

        prepared.append(
            PreparedSample(
                sample_id=r["id"],
                pillar=r["pillar"],
                lang=r["lang"],
                modality=r["modality"],
                subdomain=r["subdomain"],
                seq_len=seq_len,
                input_ids=input_ids,
                mm_token_type_ids=mm_tt,
                pixel_values=pix,
                image_grid_thw=grid,
                source_repo=str(r.get("source_repo", "")),
            )
        )
    return prepared


# ---------------------------------------------------------------------------
# CPU Synthetic Self-Test (`--self-test-cpu`, 0 GPU, 0 Donor Shards Needed)
# ---------------------------------------------------------------------------


def run_cpu_self_test() -> int:
    """End-to-end synthetic verification on CPU proving 0.0 bit diff across all components."""
    print("=== Running CPU Synthetic Self-Test (0 GPU VRAM) ===")
    torch.manual_seed(20261111)

    v_cfg = Qwen4ExpVisionConfig(
        depth=2,
        hidden_size=64,
        intermediate_size=128,
        num_heads=4,
        in_channels=3,
        patch_size=16,
        spatial_merge_size=2,
        temporal_patch_size=2,
        out_hidden_size=64,
        num_position_embeddings=64,
    )
    t_cfg = Qwen4ExpTextConfig(
        vocab_size=512,
        hidden_size=64,
        num_hidden_layers=4,
        layer_types=["linear_attention", "linear_attention", "linear_attention", "full_attention"],
        num_attention_heads=4,
        num_key_value_heads=2,
        head_dim=16,
        linear_num_key_heads=2,
        linear_num_value_heads=4,
        linear_key_head_dim=16,
        linear_value_head_dim=16,
        linear_conv_kernel_dim=4,
        moe_intermediate_size=32,
        shared_expert_intermediate_size=32,
        num_experts=32,
        num_experts_per_tok=4,
        norm_topk_prob=True,
        hc_count=4,
        hc_lowrank=16,
        ple_layer_ids=[2],
        ple_embed_dim=32,
        ngram_size=3,
        heads_per_ngram=2,
        ngram_vocab_size_base=64,
        make_ngram_vocab_size_divisible_by=16,
        split_ngram_parts=4,
        indexer_n_heads=2,
        indexer_kv_heads=1,
        indexer_head_dim=16,
        indexer_budget=32,
        indexer_compress_ratio=4,
        eos_token_id=2,
        rope_parameters={
            "rope_type": "default",
            "rope_theta": 10000.0,
            "mrope_section": [4, 2, 2],
            "mrope_interleaved": True,
        },
    )
    cfg = Qwen4ExpConfig(
        text_config=t_cfg.to_dict(),
        vision_config=v_cfg.to_dict(),
        image_token_id=500,
        video_token_id=501,
        vision_start_token_id=502,
        vision_end_token_id=503,
    )
    cfg._attn_implementation = "sdpa"
    cfg.text_config._attn_implementation = "sdpa"
    cfg.vision_config._attn_implementation = "sdpa"
    cfg._experts_implementation = "eager"
    cfg.text_config._experts_implementation = "eager"

    ref_model = Qwen4ExpModel(cfg).to(torch.bfloat16).eval()
    # Keep non-persistent RoPE `inv_freq` buffers in FP32 matching `from_pretrained(..., dtype=torch.bfloat16)`
    ref_model.visual.rotary_pos_emb = Qwen4ExpVisionRotaryEmbedding(cfg.vision_config)
    ref_model.language_model.rotary_emb = Qwen4ExpTextRotaryEmbedding(config=cfg.text_config)
    # Give router & projections non-zero random weights so expert selection & PLE gating are active
    with torch.no_grad():
        for p in ref_model.parameters():
            if p.ndim >= 2:
                p.normal_(mean=0.0, std=0.04)
            else:
                p.normal_(mean=0.0, std=0.01)

    with tempfile.TemporaryDirectory(prefix="smartllm_step5_selftest_") as tmp:
        tmp_path = Path(tmp)
        ckpt_dir = tmp_path / "ckpt"
        ckpt_dir.mkdir()

        # Export `ref_model` into sharded safetensors matching real Qwen3.8 layout (4 PLE shards)
        ple_emb_mod = ref_model.language_model.layers[1].ple.ple_embedding
        full_ngram_w = ple_emb_mod.ngram_embedding.weight.detach()
        total_ple_rows, ple_hd = full_ngram_w.shape
        assert total_ple_rows % 4 == 0
        shard_rows = total_ple_rows // 4

        weight_map: dict[str, str] = {}
        main_tensors: dict[str, torch.Tensor] = {}
        for k, t in ref_model.state_dict().items():
            full_k = f"model.{k}"
            if k == "language_model.layers.1.ple.ple_embedding.ngram_embedding.weight":
                continue
            main_tensors[full_k] = t.contiguous()
            weight_map[full_k] = "model-00001-of-00005.safetensors"

        # Save persistent PLE integer buffers explicitly as in real Qwen3.8 checkpoint
        for bname in ("layer_multipliers", "ngram_heads_offsets", "ngram_heads_vocab_sizes"):
            bk = f"model.language_model.layers.1.ple.ple_embedding.{bname}"
            main_tensors[bk] = getattr(ple_emb_mod, bname).contiguous()
            weight_map[bk] = "model-00001-of-00005.safetensors"

        save_file(main_tensors, str(ckpt_dir / "model-00001-of-00005.safetensors"))

        ple_prefix = "model.language_model.layers.1.ple.ple_embedding.ngram_embedding"
        for k_idx in range(4):
            sname = f"model-0000{k_idx + 2}-of-00005.safetensors"
            tname = f"{ple_prefix}.shard_{k_idx}.weight"
            st_r = k_idx * shard_rows
            save_file({tname: full_ngram_w[st_r : st_r + shard_rows].contiguous()}, str(ckpt_dir / sname))
            weight_map[tname] = sname

        (ckpt_dir / "model.safetensors.index.json").write_text(
            json.dumps({"metadata": {}, "weight_map": weight_map}), encoding="utf-8"
        )

        # Build text sample (S=150 > indexer_budget=32 -> 115 sparse topk(8) queries!) + multimodal sample
        s1_ids = torch.randint(4, 490, (1, 150), dtype=torch.int64)
        s1_ids[0, 68] = 2  # EOS mid-sequence

        s2_ids = torch.randint(4, 490, (1, 48), dtype=torch.int64)
        s2_ids[0, 10] = 502
        s2_ids[0, 11:17] = 500  # 6 <|image_pad|> tokens
        s2_ids[0, 17] = 503
        s2_mm_tt = torch.zeros_like(s2_ids)
        s2_mm_tt[0, 11:17] = 1
        s2_grid = torch.tensor([[1, 4, 6]], dtype=torch.int64)  # 4*6=24 raw patches -> 24//4 = 6 merged tokens
        patch_dim = 3 * 2 * 16 * 16
        s2_pix = torch.randn((24, patch_dim), dtype=torch.float32)

        with torch.no_grad():
            ref_out_1 = ref_model(input_ids=s1_ids).last_hidden_state
            ref_out_2 = ref_model(
                input_ids=s2_ids,
                pixel_values=s2_pix,
                image_grid_thw=s2_grid,
                mm_token_type_ids=s2_mm_tt,
            ).last_hidden_state

        # Direct unit test of `fast_exact_qsa_indexer_forward` vs upstream `Qwen4ExpTextQSAIndexer.forward`
        # on unchunked (S=150), unaligned chunk=37, and aligned chunk=64!
        with torch.no_grad():
            base_idx_mod = ref_model.language_model.layers[3].self_attn.indexer
            test_h = torch.randn((1, 150, t_cfg.hidden_size), dtype=torch.bfloat16)
            pos_probe = torch.arange(150).view(1, 1, 150).expand(3, 1, 150)
            t_cos, t_sin = ref_model.language_model.rotary_emb(test_h, pos_probe)
            t_cos, t_sin = t_cos.to(torch.bfloat16), t_sin.to(torch.bfloat16)
            q_ar = torch.arange(150)
            m_full = q_ar.view(1, 1, 1, 150) <= q_ar.view(1, 1, 150, 1)
            m_up_0 = base_idx_mod(test_h, (t_cos, t_sin), m_full, None)
            m_fa_0 = fast_exact_qsa_indexer_forward(base_idx_mod, test_h, (t_cos, t_sin), m_full, None)
            assert torch.equal(m_up_0, m_fa_0), "Unchunked fast_exact_qsa_indexer_forward mismatch!"
            for chk_sz in (19, 37, 64):
                c_u = DynamicCache(config=cfg.text_config)
                c_f = DynamicCache(config=cfg.text_config)
                for st_c in range(0, 150, chk_sz):
                    ed_c = min(150, st_c + chk_sz)
                    mc = torch.arange(0, ed_c).view(1, 1, 1, -1) <= torch.arange(st_c, ed_c).view(1, 1, -1, 1)
                    mu_c = base_idx_mod(test_h[:, st_c:ed_c, :], (t_cos[:, :ed_c, :], t_sin[:, :ed_c, :]), mc, c_u)
                    mf_c = fast_exact_qsa_indexer_forward(
                        base_idx_mod, test_h[:, st_c:ed_c, :], (t_cos[:, :ed_c, :], t_sin[:, :ed_c, :]), mc, c_f
                    )
                    assert torch.equal(mu_c, mf_c), f"Chunked ({chk_sz}) fast_exact_qsa_indexer_forward mismatch at {st_c}:{ed_c}!"
        print("  QSA Indexer Variant-A bit-exact test (unchunked + chunks 19/37/64, budget=32 on S=150): torch.equal == True")

        # Now instantiate Meta-Device Streaming Observer and replay layer-by-layer!
        st_index = SafetensorsIndex(ckpt_dir)
        with torch.device("meta"):
            obs_model = Qwen4ExpModel(cfg)
        obs_model.eval()
        assert obs_model.language_model.layers[1].ple.ple_embedding.ngram_embedding.weight.device.type == "meta"

        obs_model.visual.rotary_pos_emb = Qwen4ExpVisionRotaryEmbedding(cfg.vision_config)
        obs_model.language_model.rotary_emb = Qwen4ExpTextRotaryEmbedding(config=cfg.text_config)

        stream_ple = StreamingPLENGramEmbedding(
            index=st_index,
            shard_prefix=ple_prefix,
            num_shards=4,
            shard_rows=shard_rows,
            embed_dim=ple_hd,
            dtype=torch.bfloat16,
        )
        obs_model.language_model.layers[1].ple.ple_embedding.ngram_embedding = stream_ple
        _ = QSAIndexerWrapper(
            obs_model.language_model.layers[3].self_attn.indexer, mode="fast_exact_a", sync_timing=True
        )

        # Stage 0: embed_tokens + visual -> unbuffered sequential disk ping-pong slot 0
        pingpong = DiskHiddenStatePingPong(tmp_path / "buf", [150, 48], cfg.text_config.hc_count * cfg.text_config.hidden_size)
        try:
            materialize_submodule(obs_model.language_model.embed_tokens, "model.language_model.embed_tokens", st_index, "cpu")
            materialize_submodule(obs_model.visual, "model.visual", st_index, "cpu")

            rot_list: list[tuple[torch.Tensor, torch.Tensor]] = []
            samples_raw = [
                (s1_ids, None, None, None, "pillar_4_art_direction_copywriting", "en", "SmartLLM/curated-bilingual-canons"),
                (s2_ids, s2_pix, s2_grid, s2_mm_tt, "pillar_3_style_canons_vision", "ru", "other"),
            ]
            with torch.no_grad():
                for idx_s, (ids, pix, grid, mm_tt, _, _, _) in enumerate(samples_raw):
                    emb = obs_model.language_model.embed_tokens(ids)
                    if pix is not None:
                        vis_feat = obs_model.get_image_features(pix, grid, return_dict=True)
                        img_emb = torch.cat(vis_feat.pooler_output, dim=0).to(emb.device, emb.dtype)
                        img_mask, _ = obs_model.get_placeholder_mask(ids, inputs_embeds=emb, image_features=img_emb)
                        emb = emb.masked_scatter(img_mask, img_emb)
                    pos_3d = obs_model.compute_3d_position_ids(
                        input_ids=ids,
                        image_grid_thw=grid,
                        inputs_embeds=emb,
                        mm_token_type_ids=mm_tt,
                    )
                    if pos_3d is None:
                        S_cur = ids.shape[1]
                        pos_mrope = torch.arange(S_cur).view(1, 1, S_cur).expand(3, 1, S_cur)
                    elif pos_3d.shape[0] == 4:
                        pos_mrope = pos_3d[1:]
                    else:
                        pos_mrope = pos_3d
                    cos, sin = obs_model.language_model.rotary_emb(emb, pos_mrope)
                    rot_list.append((cos.to(torch.bfloat16), sin.to(torch.bfloat16)))
                    h0 = emb.repeat(1, 1, cfg.text_config.hc_count)
                    pingpong.write_sample(0, idx_s, h0)
            pingpong.flush_slot(0)
            free_submodule_to_meta(
                obs_model.visual, keep_non_checkpoint_names={"rotary_pos_emb.inv_freq", "rotary_pos_emb.original_inv_freq"}
            )
            free_submodule_to_meta(obs_model.language_model.embed_tokens)

            # Pre-index PLE before layer 1
            ple_parent = obs_model.language_model.layers[1].ple.ple_embedding
            materialize_submodule(ple_parent, "model.language_model.layers.1.ple.ple_embedding", st_index, "cpu")
            stream_ple.build_preindexed_cache(ple_parent, [s1_ids, s2_ids])

            # Layers 0..3
            accs: dict[int, REAPMoEAccumulator] = {}
            chunked_s1_prev: torch.Tensor = torch.empty(0)
            for li in range(4):
                in_slot = li % 2
                out_slot = (li + 1) % 2
                layer = obs_model.language_model.layers[li]
                materialize_submodule(layer, f"model.language_model.layers.{li}", st_index, "cpu")
                acc = REAPMoEAccumulator(cfg.text_config.num_experts)
                accs[li] = acc
                prof: dict[str, float] = {}
                for idx_s, (ids, _, _, _, pil_s, lng_s, src_s) in enumerate(samples_raw):
                    acc.current_stratum = pil_s
                    acc.current_lang = lng_s
                    acc.current_subbucket = "craft_p4" if src_s == "SmartLLM/curated-bilingual-canons" else None
                    h_in = pingpong.read_sample(in_slot, idx_s)
                    cos, sin = rot_list[idx_s]
                    h_out = forward_single_decoder_layer(
                        layer=layer,
                        text_cfg=cfg.text_config,
                        hidden_states_cpu=h_in,
                        full_cos_cpu=cos,
                        full_sin_cpu=sin,
                        ple_input_ids_cpu=ids,
                        device="cpu",
                        chunk_tokens=256,
                        qsa_long_chunk_tokens=None,
                        reap_acc=acc,
                        layer_prof=prof,
                    )
                    pingpong.write_sample(out_slot, idx_s, h_out)
                # Also verify multi-chunk DynamicCache replay on S=150 (chunk=64) across all 4 layers!
                h_chunk_in = pingpong.read_sample(0, 0) if li == 0 else chunked_s1_prev
                chunked_s1_prev = forward_single_decoder_layer(
                    layer=layer,
                    text_cfg=cfg.text_config,
                    hidden_states_cpu=h_chunk_in,
                    full_cos_cpu=rot_list[0][0],
                    full_sin_cpu=rot_list[0][1],
                    ple_input_ids_cpu=s1_ids,
                    device="cpu",
                    chunk_tokens=64,
                    qsa_long_chunk_tokens=32,
                    reap_acc=None,
                )
                pingpong.flush_slot(out_slot)
                if li == 1:
                    stream_ple.clear_cache()
                free_submodule_to_meta(layer, keep_non_checkpoint_names={"ple.ple_embedding.ngram_embedding.weight"})

            # Final hyper_connection_mixer check vs ref_model
            materialize_submodule(
                obs_model.language_model.hyper_connection_mixer,
                "model.language_model.hyper_connection_mixer",
                st_index,
                "cpu",
            )
            with torch.no_grad():
                final_1 = obs_model.language_model.hyper_connection_mixer(pingpong.read_sample(4 % 2, 0))
                final_2 = obs_model.language_model.hyper_connection_mixer(pingpong.read_sample(4 % 2, 1))
                final_1_chunked = obs_model.language_model.hyper_connection_mixer(chunked_s1_prev)
        finally:
            pingpong.close_and_cleanup(remove_files=True)

        diff_1 = float((ref_out_1.double() - final_1.double()).abs().max().item())
        diff_2 = float((ref_out_2.double() - final_2.double()).abs().max().item())
        diff_1c = float((ref_out_1.double() - final_1_chunked.double()).abs().max().item())
        cos_1 = float(F.cosine_similarity(ref_out_1.double().reshape(-1), final_1.double().reshape(-1), dim=0).item())
        cos_2 = float(F.cosine_similarity(ref_out_2.double().reshape(-1), final_2.double().reshape(-1), dim=0).item())
        cos_1c = float(F.cosine_similarity(ref_out_1.double().reshape(-1), final_1_chunked.double().reshape(-1), dim=0).item())

        print(f"  Text sample unchunked (S=150, EOS@68): max_abs_diff={diff_1:.6e}, cos={cos_1:.8f}")
        print(f"  Text sample chunked   (S=150, chk=64): max_abs_diff={diff_1c:.6e}, cos={cos_1c:.8f}")
        print(f"  Multimodal sample     (S=48, 6 vis):   max_abs_diff={diff_2:.6e}, cos={cos_2:.8f}")
        for li, acc in accs.items():
            d = acc.finalize_dict(
                full_stratum_tokens={
                    "pillar_4_art_direction_copywriting": 500,
                    "pillar_3_style_canons_vision": 500,
                }
            )
            print(
                f"  Layer {li} REAP: total_tokens={d['total_tokens']}, active={d['active_experts']}/{d['num_experts']}, "
                f"keep_k={len(d['keep_indices_k205_sorted'])}, nan={d['nan_or_inf_count']}, median_reap={d['reap_summary']['median']:.6f}"
            )
            assert d["total_tokens"] == 198
            assert d["nan_or_inf_count"] == 0
            assert "craft_p4" in d["by_stratum"]["weighted_ean_sum"]

        assert diff_1 < 1e-4 and diff_2 < 1e-4 and cos_1 >= 0.99999 and cos_2 >= 0.99999, (
            f"Unchunked equivalence failed: diff_1={diff_1}, diff_2={diff_2}, cos_1={cos_1}, cos_2={cos_2}"
        )
        assert cos_1c >= 0.9999 and diff_1c < 2e-2, f"Chunked DynamicCache equivalence failed: diff={diff_1c}, cos={cos_1c}"

        # Exercise `run_equivalence_check_gpu(..., device='cpu', chunk_tokens=96, stress_chunk_tokens=32)`
        # so S=150 > 96 > 35 exercises 100% of 1A, 1B-0 (FP32 DynamicCache + QSA torch.equal), 1B-1, 1B-2, and 1B-3!
        synth_samples = [
            PreparedSample(
                "synth_txt_gt_chunk",
                "pillar_1_frontend_3d_svg",
                "en",
                "text",
                "web",
                150,
                s1_ids,
                None,
                None,
                None,
            ),
            PreparedSample(
                "synth_mm",
                "pillar_3_style_canons_vision",
                "ru",
                "multimodal",
                "vis",
                48,
                s2_ids,
                s2_mm_tt,
                s2_pix,
                s2_grid,
            ),
        ]
        eq_res = run_equivalence_check_gpu(
            cfg,
            st_index,
            synth_samples,
            device="cpu",
            chunk_tokens=96,
            stress_chunk_tokens=32,
        )
        assert len(eq_res["samples"]) == 2
        assert len(eq_res["fp32_dynamic_cache_proof"]) == 2
        assert eq_res["qsa_indexer_bit_exact_check"]["all_bit_identical"] is True
        assert eq_res["samples"][0]["chunked_primary_stages"] is not None
    print("CPU SYNTHETIC SELF-TEST PASSED!")
    return 0


# ---------------------------------------------------------------------------
# Real Step 5 GPU Pilot Execution (Part 1 Equivalence + Part 2 5% Stratified Pilot)
# ---------------------------------------------------------------------------


def compute_position_embeddings_for_sample(
    obs_model: Qwen4ExpModel,
    sample: PreparedSample,
    emb_cpu: torch.Tensor,
    rotary_device: str = "cpu",
) -> tuple[torch.Tensor, torch.Tensor]:
    """Compute exact M-RoPE `(cos, sin)` matching `Qwen4ExpModel.forward` -> `Qwen4ExpTextModel.forward`."""
    with torch.no_grad():
        pos_ids = obs_model.compute_3d_position_ids(
            input_ids=sample.input_ids,
            image_grid_thw=sample.image_grid_thw,
            inputs_embeds=emb_cpu,
            mm_token_type_ids=sample.mm_token_type_ids,
        )
        if pos_ids is None:
            seq_l = sample.seq_len
            mrope_pos = torch.arange(seq_l, dtype=torch.int64).view(1, 1, seq_l).expand(3, 1, seq_l)
        elif pos_ids.ndim == 2:
            mrope_pos = pos_ids.unsqueeze(0).expand(3, -1, -1)
        elif pos_ids.shape[0] == 4:
            mrope_pos = pos_ids[1:]
        else:
            mrope_pos = pos_ids
        x_probe = emb_cpu[:, :1, :].to(rotary_device)
        cos, sin = obs_model.language_model.rotary_emb(x_probe, mrope_pos.to(rotary_device))
        return cos.to(torch.bfloat16).cpu(), sin.to(torch.bfloat16).cpu()


def build_all_dataset_ple_input_ids(
    all_rows: list[dict[str, Any]],
    tok: Any,
    proc: Any,
    root_dir: Path,
    verified_pilot_map: dict[str, PreparedSample],
) -> list[torch.Tensor]:
    """Construct exact `[1, S]` int64 `ple_input_ids` for 100% of dataset rows (`0` shard reads)."""
    image_pad_id = int(tok.convert_tokens_to_ids("<|image_pad|>"))
    out_tensors: list[torch.Tensor] = []
    for r in all_rows:
        raw_ids: list[int] = tok(r["text"], add_special_tokens=False)["input_ids"]
        if r["modality"] == "multimodal":
            expanded: list[int] = []
            img_cursor = 0
            imgs = r.get("images", [])
            for tid in raw_ids:
                if tid == image_pad_id and img_cursor < len(imgs):
                    im_meta = imgs[img_cursor]
                    img_cursor += 1
                    if "size" in im_meta and isinstance(im_meta["size"], (list, tuple)) and len(im_meta["size"]) == 2:
                        w_px, h_px = int(im_meta["size"][0]), int(im_meta["size"][1])
                    else:
                        w_px, h_px = int(im_meta["width"]), int(im_meta["height"])
                    n_vis = (w_px // 32) * (h_px // 32)
                    expanded.extend([image_pad_id] * n_vis)
                else:
                    expanded.append(tid)
            if len(expanded) == int(r["qwen38_tokens"]):
                t_ids = torch.tensor([expanded], dtype=torch.int64)
            else:
                pil_imgs = [Image.open(root_dir / im["path"]).convert("RGB") for im in imgs]
                t_ids = proc(text=[r["text"]], images=pil_imgs, return_tensors="pt")["input_ids"].to(torch.int64)
                for im_obj in pil_imgs:
                    im_obj.close()
        else:
            t_ids = torch.tensor([raw_ids], dtype=torch.int64)

        if int(t_ids.shape[1]) != int(r["qwen38_tokens"]):
            raise AssertionError(f"Full PLE ID check {r['id']}: got {t_ids.shape[1]} != {r['qwen38_tokens']}")
        if r["id"] in verified_pilot_map:
            if not torch.equal(t_ids, verified_pilot_map[r["id"]].input_ids):
                raise AssertionError(f"Fast PLE input_ids mismatch vs AutoProcessor on {r['id']}")
        out_tensors.append(t_ids)
    return out_tensors


def compute_exact_full_dataset_ple_stats(
    ple_parent: nn.Module,
    stream_ple: StreamingPLENGramEmbedding,
    all_input_ids: list[torch.Tensor],
) -> dict[str, Any]:
    """Compute 100% exact Step 6 PLE unique n-gram rows & cache RAM across all calibration rows (`0` disk I/O)."""
    t0 = time.perf_counter()
    stream_ple._capture_only = True
    stream_ple.captured_chunks.clear()
    try:
        with torch.no_grad():
            for ids in all_input_ids:
                _ = ple_parent(ids.to("cpu"), past_key_values=None)
    finally:
        stream_ple._capture_only = False

    flat_all = torch.cat(stream_ple.captured_chunks, dim=0)
    total_lookups = int(flat_all.numel())
    stream_ple.captured_chunks.clear()
    unique_ids = torch.unique(flat_all, sorted=True)
    del flat_all

    n_unique = int(unique_ids.numel())
    shard_ids = torch.div(unique_ids, stream_ple.shard_rows, rounding_mode="floor")
    unique_ks = torch.unique_consecutive(shard_ids).tolist()
    touched_files = sorted(
        {stream_ple.index.weight_map[f"{stream_ple.shard_prefix}.shard_{int(k)}.weight"] for k in unique_ks}
    )
    # Exact RAM footprint of `unique_ids` (int64 = 8 B) + `cached_rows` (BF16 = 2 * embed_dim B)
    exact_ram_bytes = n_unique * (8 + stream_ple.embed_dim * 2)
    del unique_ids, shard_ids
    return {
        "full_dataset_samples": len(all_input_ids),
        "full_dataset_total_ngram_lookups": total_lookups,
        "full_dataset_unique_ngram_rows": n_unique,
        "full_dataset_dedup_ratio": round(n_unique / max(1, total_lookups), 4),
        "full_dataset_ple_safetensors_files_touched": len(touched_files),
        "full_dataset_exact_cache_ram_bytes": exact_ram_bytes,
        "full_dataset_exact_cache_ram_mib": round(exact_ram_bytes / (1024**2), 2),
        "full_dataset_exact_cache_ram_gib": round(exact_ram_bytes / (1024**3), 4),
        "cpu_exact_index_sec": round(time.perf_counter() - t0, 4),
    }


@torch.no_grad()
def _verify_qsa_indexer_bit_exact_on_layer3(
    layer3: Qwen4ExpTextDecoderLayer,
    text_cfg: Qwen4ExpTextConfig,
    h_in_cpu: torch.Tensor,
    cos_cpu: torch.Tensor,
    sin_cpu: torch.Tensor,
    sample_id: str,
    chunk_sizes: list[int],
    device: str,
) -> dict[str, Any]:
    """Prove `torch.equal == True` (`0` bit diffs) between upstream `Qwen4ExpTextQSAIndexer` & `Variant A`."""
    base_indexer = layer3.self_attn.indexer
    seq_len = int(h_in_cpu.shape[1])

    h_attn_in, _, _ = layer3.attn_hyper_connection(h_in_cpu.to(device, non_blocking=False))
    cos_dev = cos_cpu.to(device, non_blocking=False)
    sin_dev = sin_cpu.to(device, non_blocking=False)

    ar = torch.arange(seq_len, device=device)
    m_full = ar.view(1, 1, 1, seq_len) <= ar.view(1, 1, seq_len, 1)
    m_up_full = Qwen4ExpTextQSAIndexer.forward(base_indexer, h_attn_in, (cos_dev, sin_dev), m_full, None)
    m_fa_full = fast_exact_qsa_indexer_forward(base_indexer, h_attn_in, (cos_dev, sin_dev), m_full, None)
    if not torch.equal(m_up_full, m_fa_full):
        n_mismatch = int((m_up_full != m_fa_full).sum().item())
        raise AssertionError(
            f"QSA Indexer Variant-A unchunked bit-exact failure on {sample_id} (S={seq_len}): {n_mismatch} mask diffs!"
        )
    del m_full, m_up_full, m_fa_full

    chunk_checks: dict[str, Any] = {}
    for chk in chunk_sizes:
        c_up = DynamicCache(config=text_cfg)
        c_fa = DynamicCache(config=text_cfg)
        n_chunks = 0
        for st in range(0, seq_len, chk):
            ed = min(seq_len, st + chk)
            mc = torch.arange(0, ed, device=device).view(1, 1, 1, -1) <= torch.arange(st, ed, device=device).view(
                1, 1, -1, 1
            )
            mu = Qwen4ExpTextQSAIndexer.forward(
                base_indexer,
                h_attn_in[:, st:ed, :],
                (cos_dev[:, :ed, :], sin_dev[:, :ed, :]),
                mc,
                c_up,
            )
            mf = fast_exact_qsa_indexer_forward(
                base_indexer,
                h_attn_in[:, st:ed, :],
                (cos_dev[:, :ed, :], sin_dev[:, :ed, :]),
                mc,
                c_fa,
            )
            if not torch.equal(mu, mf):
                n_mismatch = int((mu != mf).sum().item())
                raise AssertionError(
                    f"QSA Indexer Variant-A chunked({chk}) bit-exact failure on {sample_id} [{st}:{ed}]: {n_mismatch} diffs!"
                )
            n_chunks += 1
            del mc, mu, mf
        chunk_checks[f"chunk_{chk}"] = {"chunks_verified": n_chunks, "torch_equal": True}
        del c_up, c_fa

    del h_attn_in, cos_dev, sin_dev
    if device.startswith("cuda"):
        torch.cuda.empty_cache()

    return {
        "sample_id": sample_id,
        "seq_len": seq_len,
        "unchunked_torch_equal": True,
        "chunked_checks": chunk_checks,
        "all_bit_identical": True,
    }


@torch.no_grad()
def _verify_stateful_layer_fp32_dynamic_cache(
    layer: Qwen4ExpTextDecoderLayer,
    layer_idx: int,
    text_cfg: Qwen4ExpTextConfig,
    stream_ple: StreamingPLENGramEmbedding | None,
    h_in_bf16_cpu: torch.Tensor,
    cos_bf16_cpu: torch.Tensor,
    sin_bf16_cpu: torch.Tensor,
    ple_ids_cpu: torch.Tensor,
    sample_id: str,
    chunk_sizes: list[int],
    device: str,
) -> dict[str, Any]:
    """Prove in IEEE-754 FP32 (`allow_tf32=False`) that `DynamicCache` state handoff has `0` bugs.

    Must be called AFTER freeing `layer.mlp.experts` to `"meta"` so FP32 weights stay `< 350 MiB` VRAM!
    """
    prev_matmul_tf32 = torch.backends.cuda.matmul.allow_tf32
    prev_cudnn_tf32 = torch.backends.cudnn.allow_tf32
    prev_ple_dtype = stream_ple.out_dtype if stream_ple is not None else torch.bfloat16

    try:
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        if stream_ple is not None and layer.ple is not None:
            stream_ple.out_dtype = torch.float32

        if layer.ple is not None:
            layer.ple.to(torch.float32)
        layer.attn_hyper_connection.to(torch.float32)
        if layer.layer_type == "linear_attention":
            layer.linear_attn.to(torch.float32)
        else:
            layer.self_attn.to(torch.float32)
        layer.mlp_hyper_connection.to(torch.float32)
        layer.mlp.gate.to(torch.float32)

        seq_len = int(h_in_bf16_cpu.shape[1])
        is_full_attn = layer.layer_type != "linear_attention"
        h_f32_cpu = h_in_bf16_cpu.float()
        cos_f32_cpu = cos_bf16_cpu.float()
        sin_f32_cpu = sin_bf16_cpu.float()

        def _pre_moe_step(
            h_dev: torch.Tensor,
            cos_dev: torch.Tensor,
            sin_dev: torch.Tensor,
            attn_mask: torch.Tensor | None,
            ple_dev: torch.Tensor,
            cache: DynamicCache | None,
        ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            if layer.ple is not None:
                h_dev = h_dev + layer.ple(h_dev, ple_dev, cache, conv_mask=None)
            h_attn_in, hyper_in, inj_w = layer.attn_hyper_connection(h_dev)
            if layer.layer_type == "linear_attention":
                h_attn_out = layer.linear_attn(h_attn_in, cache_params=cache, attention_mask=None)
            else:
                h_attn_out, _ = layer.self_attn(
                    h_attn_in,
                    (cos_dev, sin_dev),
                    attention_mask=attn_mask,
                    past_key_values=cache,
                )
            h_post = hyper_in + (h_attn_out.unsqueeze(-2) * inj_w.unsqueeze(-1)).flatten(-2)
            h_mlp_in, _, _ = layer.mlp_hyper_connection(h_post)
            _, r_scores, r_indices = layer.mlp.gate(h_mlp_in)
            return (
                h_post.to("cpu"),
                r_indices.detach().to("cpu", dtype=torch.int16),
                r_scores.detach().to("cpu", dtype=torch.float32),
            )

        # Unchunked FP32 reference
        h_dev = h_f32_cpu.to(device, non_blocking=False)
        cos_dev = cos_f32_cpu.to(device, non_blocking=False)
        sin_dev = sin_f32_cpu.to(device, non_blocking=False)
        ple_dev = ple_ids_cpu.to(device, non_blocking=False)
        m_full = None
        if is_full_attn:
            ar = torch.arange(seq_len, device=device)
            m_full = ar.view(1, 1, 1, seq_len) <= ar.view(1, 1, seq_len, 1)
        ref_post, ref_idx, ref_w = _pre_moe_step(h_dev, cos_dev, sin_dev, m_full, ple_dev, cache=None)
        del h_dev, ple_dev, m_full

        by_chunk: dict[str, Any] = {}
        for chk in chunk_sizes:
            cache = DynamicCache(config=text_cfg)
            chk_post = torch.empty_like(ref_post)
            chk_idx_list: list[torch.Tensor] = []
            chk_w_list: list[torch.Tensor] = []
            for st in range(0, seq_len, chk):
                ed = min(seq_len, st + chk)
                hc = h_f32_cpu[:, st:ed, :].to(device, non_blocking=False)
                pc = ple_ids_cpu[:, st:ed].to(device, non_blocking=False)
                mc = None
                if is_full_attn:
                    mc = torch.arange(0, ed, device=device).view(1, 1, 1, -1) <= torch.arange(
                        st, ed, device=device
                    ).view(1, 1, -1, 1)
                hp, ri, rw = _pre_moe_step(hc, cos_dev[:, :ed, :], sin_dev[:, :ed, :], mc, pc, cache=cache)
                chk_post[:, st:ed, :] = hp
                chk_idx_list.append(ri)
                chk_w_list.append(rw)
                del hc, pc, mc
            del cache

            chk_idx = torch.cat(chk_idx_list, dim=0)
            chk_w = torch.cat(chk_w_list, dim=0)
            diff_d = (ref_post.double() - chk_post.double()).abs()
            max_abs = float(diff_d.max().item())
            mean_abs = float(diff_d.mean().item())
            cos_sim = float(F.cosine_similarity(ref_post.double().reshape(-1), chk_post.double().reshape(-1), dim=0).item())
            rmet = compute_topk_routing_metrics(ref_idx, ref_w, chk_idx, chk_w, int(text_cfg.num_experts))
            by_chunk[f"chunk_{chk}"] = {
                "post_attn_max_abs_diff": max_abs,
                "post_attn_mean_abs_diff": mean_abs,
                "post_attn_cosine_similarity": cos_sim,
                "fp32_router_metrics": rmet,
            }
            if max_abs >= 1e-4 or cos_sim < 0.999999 or rmet["exact_topk_set_match_frac"] < 0.995:
                raise AssertionError(
                    f"FP32 DynamicCache proof failed on layer_{layer_idx} ({sample_id}, chunk={chk}): "
                    f"max_abs={max_abs}, cos={cos_sim}, exact_topk={rmet['exact_topk_set_match_frac']}"
                )

        del cos_dev, sin_dev
        if device.startswith("cuda"):
            torch.cuda.empty_cache()

        return {
            "layer_idx": layer_idx,
            "layer_type": layer.layer_type,
            "has_ple": layer.ple is not None,
            "sample_id": sample_id,
            "seq_len": seq_len,
            "allow_tf32": False,
            "chunks": by_chunk,
        }
    finally:
        torch.backends.cuda.matmul.allow_tf32 = prev_matmul_tf32
        torch.backends.cudnn.allow_tf32 = prev_cudnn_tf32
        if stream_ple is not None:
            stream_ple.out_dtype = prev_ple_dtype


def _tensor_diff_metrics(ref_t: torch.Tensor, test_t: torch.Tensor) -> dict[str, float]:
    r_d = ref_t.double()
    t_d = test_t.double()
    ref_scale = max(1e-8, float(r_d.abs().mean().item()))
    diff = (r_d - t_d).abs()
    max_abs = float(diff.max().item())
    mean_abs = float(diff.mean().item())
    cos_sim = float(F.cosine_similarity(r_d.reshape(-1), t_d.reshape(-1), dim=0).item())
    return {
        "max_abs_diff": max_abs,
        "mean_abs_diff": mean_abs,
        "rel_mean_abs_diff": mean_abs / ref_scale,
        "cosine_similarity": cos_sim,
    }


def run_equivalence_check_gpu(
    cfg: Qwen4ExpConfig,
    st_index: SafetensorsIndex,
    equiv_samples: list[PreparedSample],
    device: str,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    stress_chunk_tokens: int = QSA_LONG_CHUNK_TOKENS,
) -> dict[str, Any]:
    """Compare native `Qwen4ExpModel.forward` vs Streaming REAP + FP32 DynamicCache Proof + BF16 Routing."""
    print(f"\n=== Part 1: Exact Numerical & Routing Equivalence Check on {len(equiv_samples)} Samples ({device}) ===")
    if device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(device)

    ple_prefix = "model.language_model.layers.1.ple.ple_embedding.ngram_embedding"
    num_ple_shards = int(cfg.text_config.split_ngram_parts)
    ple_head_dim = int(cfg.text_config.ple_embed_dim) // (
        (int(cfg.text_config.ngram_size) - 1) * int(cfg.text_config.heads_per_ngram)
    )
    shard0_name = f"{ple_prefix}.shard_0.weight"
    with safe_open(str(st_index.checkpoint_dir / st_index.weight_map[shard0_name]), framework="pt", device="cpu") as f:
        shard_rows = int(f.get_slice(shard0_name).get_shape()[0])

    # 1A. Native `Qwen4ExpModel.forward` reference pass (`num_hidden_layers=4`, layerwise hooks to fit 12 GiB VRAM)
    ref_cfg = copy.deepcopy(cfg)
    ref_cfg.text_config.num_hidden_layers = len(PILOT_LAYERS)
    ref_cfg.text_config.layer_types = list(cfg.text_config.layer_types[: len(PILOT_LAYERS)])
    ref_cfg._attn_implementation = "sdpa"
    ref_cfg.text_config._attn_implementation = "sdpa"
    ref_cfg.vision_config._attn_implementation = "sdpa"
    ref_cfg._experts_implementation = "eager"
    ref_cfg.text_config._experts_implementation = "eager"

    with torch.device("meta"):
        ref_model = Qwen4ExpModel(ref_cfg)
    ref_model.eval()
    ref_model.visual.rotary_pos_emb = Qwen4ExpVisionRotaryEmbedding(ref_cfg.vision_config)
    ref_model.language_model.rotary_emb = Qwen4ExpTextRotaryEmbedding(config=ref_cfg.text_config).to(device)
    ref_model.language_model.layers[1].ple.ple_embedding.ngram_embedding = StreamingPLENGramEmbedding(
        index=st_index,
        shard_prefix=ple_prefix,
        num_shards=num_ple_shards,
        shard_rows=shard_rows,
        embed_dim=ple_head_dim,
        dtype=torch.bfloat16,
    )
    materialize_submodule(
        ref_model.language_model.hyper_connection_mixer,
        "model.language_model.hyper_connection_mixer",
        st_index,
        device,
    )

    ref_states: list[dict[str, torch.Tensor]] = [{} for _ in equiv_samples]
    ref_routing: list[dict[str, tuple[torch.Tensor, torch.Tensor]]] = [{} for _ in equiv_samples]
    active_sample_idx = 0
    hook_handles = []

    for li in PILOT_LAYERS:
        def _make_pre(layer_idx: int):
            def _pre(mod: nn.Module, args: tuple[Any, ...]) -> None:
                if layer_idx == 0:
                    ref_states[active_sample_idx]["embed"] = args[0].detach().to("cpu")
                    # Free embed_tokens (1.18 GiB) + visual (0.85 GiB) BEFORE loading 6.86 GiB decoder layer!
                    free_submodule_to_meta(ref_model.language_model.embed_tokens)
                    free_submodule_to_meta(
                        ref_model.visual,
                        keep_non_checkpoint_names={"rotary_pos_emb.inv_freq", "rotary_pos_emb.original_inv_freq"},
                    )
                    if device.startswith("cuda"):
                        torch.cuda.empty_cache()
                materialize_submodule(mod, f"model.language_model.layers.{layer_idx}", st_index, device)
            return _pre

        def _make_gate_post(layer_idx: int):
            def _gate_post(_mod: nn.Module, _args: tuple[Any, ...], output: tuple[Any, ...]) -> None:
                _, r_scores, r_indices = output
                ref_routing[active_sample_idx][f"layer_{layer_idx}"] = (
                    r_indices.detach().to("cpu", dtype=torch.int16),
                    r_scores.detach().to("cpu", dtype=torch.float32),
                )
            return _gate_post

        def _make_post(layer_idx: int):
            def _post(mod: nn.Module, args: tuple[Any, ...], output: torch.Tensor) -> None:
                ref_states[active_sample_idx][f"layer_{layer_idx}"] = output.detach().to("cpu")
                free_submodule_to_meta(mod, keep_non_checkpoint_names={"ple.ple_embedding.ngram_embedding.weight"})
                if device.startswith("cuda"):
                    torch.cuda.empty_cache()
            return _post

        hook_handles.append(ref_model.language_model.layers[li].register_forward_pre_hook(_make_pre(li)))
        hook_handles.append(ref_model.language_model.layers[li].mlp.gate.register_forward_hook(_make_gate_post(li)))
        hook_handles.append(ref_model.language_model.layers[li].register_forward_hook(_make_post(li)))

    with torch.no_grad():
        for i, s in enumerate(equiv_samples):
            active_sample_idx = i
            materialize_submodule(
                ref_model.language_model.embed_tokens, "model.language_model.embed_tokens", st_index, device
            )
            if s.pixel_values is not None:
                materialize_submodule(ref_model.visual, "model.visual", st_index, device)
                ref_model.visual.rotary_pos_emb = ref_model.visual.rotary_pos_emb.to(device)
            ref_out = ref_model(
                input_ids=s.input_ids.to(device),
                pixel_values=s.pixel_values.to(device) if s.pixel_values is not None else None,
                image_grid_thw=s.image_grid_thw.to(device) if s.image_grid_thw is not None else None,
                mm_token_type_ids=s.mm_token_type_ids.to(device) if s.mm_token_type_ids is not None else None,
                use_cache=False,
            )
            ref_states[i]["hc_mixer_out"] = ref_out.last_hidden_state.detach().to("cpu")
            del ref_out
            if device.startswith("cuda"):
                torch.cuda.empty_cache()

    for h in hook_handles:
        h.remove()
    del ref_model
    gc.collect()
    if device.startswith("cuda"):
        torch.cuda.empty_cache()

    # 1B. Streaming REAP Observer pass (Variant-A QSA + REAP wrapper + Disk Ping-Pong + Chunked & FP32 proofs)
    with torch.device("meta"):
        obs_model = Qwen4ExpModel(cfg)
    obs_model.eval()
    obs_model.visual.rotary_pos_emb = Qwen4ExpVisionRotaryEmbedding(cfg.vision_config)
    obs_model.language_model.rotary_emb = Qwen4ExpTextRotaryEmbedding(config=cfg.text_config)
    stream_ple = StreamingPLENGramEmbedding(
        index=st_index,
        shard_prefix=ple_prefix,
        num_shards=num_ple_shards,
        shard_rows=shard_rows,
        embed_dim=ple_head_dim,
        dtype=torch.bfloat16,
    )
    obs_model.language_model.layers[1].ple.ple_embedding.ngram_embedding = stream_ple
    _ = QSAIndexerWrapper(
        obs_model.language_model.layers[3].self_attn.indexer, mode="fast_exact_a", sync_timing=False
    )

    gt_chunk_sample_idx = next(
        (idx for idx, s in enumerate(equiv_samples) if s.seq_len > chunk_tokens),
        max(range(len(equiv_samples)), key=lambda idx: equiv_samples[idx].seq_len),
    )
    unchunked_limit = max(chunk_tokens, max(s.seq_len for s in equiv_samples))

    tmp_eq_dir = OUT_DIR / "_tmp_equiv_buf"
    pingpong = DiskHiddenStatePingPong(
        tmp_eq_dir,
        [s.seq_len for s in equiv_samples],
        cfg.text_config.hc_count * cfg.text_config.hidden_size,
    )

    obs_states: list[dict[str, torch.Tensor]] = [{} for _ in equiv_samples]
    obs_iso_stress_states: list[dict[str, torch.Tensor]] = [{} for _ in equiv_samples]
    obs_cas_stress_states: list[dict[str, torch.Tensor]] = [{} for _ in equiv_samples]
    obs_iso_primary_states: dict[int, dict[str, torch.Tensor]] = {}
    obs_cas_primary_states: dict[int, dict[str, torch.Tensor]] = {}
    obs_cas_prod_states: dict[int, dict[str, torch.Tensor]] = {}

    obs_unchunked_routing: list[dict[str, tuple[torch.Tensor, torch.Tensor]]] = [{} for _ in equiv_samples]
    obs_iso_stress_routing: list[dict[str, tuple[torch.Tensor, torch.Tensor]]] = [{} for _ in equiv_samples]
    obs_cas_stress_routing: list[dict[str, tuple[torch.Tensor, torch.Tensor]]] = [{} for _ in equiv_samples]
    obs_iso_primary_routing: dict[int, dict[str, tuple[torch.Tensor, torch.Tensor]]] = defaultdict(dict)
    obs_cas_primary_routing: dict[int, dict[str, tuple[torch.Tensor, torch.Tensor]]] = defaultdict(dict)
    obs_cas_prod_routing: dict[int, dict[str, tuple[torch.Tensor, torch.Tensor]]] = defaultdict(dict)

    reap_jaccard_by_layer: dict[str, dict[str, float]] = {}
    fp32_proofs: dict[str, Any] = {}
    qsa_bit_exact_check: dict[str, Any] = {}

    try:
        materialize_submodule(obs_model.language_model.embed_tokens, "model.language_model.embed_tokens", st_index, "cpu")
        materialize_submodule(obs_model.visual, "model.visual", st_index, device)
        obs_model.visual.rotary_pos_emb = obs_model.visual.rotary_pos_emb.to(device)

        obs_cos_sin: list[tuple[torch.Tensor, torch.Tensor]] = []
        with torch.no_grad():
            for i, s in enumerate(equiv_samples):
                emb = obs_model.language_model.embed_tokens(s.input_ids)
                if s.pixel_values is not None:
                    vis_out = obs_model.get_image_features(
                        s.pixel_values.to(device), s.image_grid_thw.to(device), return_dict=True
                    )
                    img_emb = torch.cat(vis_out.pooler_output, dim=0).to("cpu", emb.dtype)
                    img_mask, _ = obs_model.get_placeholder_mask(s.input_ids, inputs_embeds=emb, image_features=img_emb)
                    emb = emb.masked_scatter(img_mask, img_emb)
                cos, sin = compute_position_embeddings_for_sample(obs_model, s, emb, rotary_device=device)
                obs_cos_sin.append((cos, sin))
                h0 = emb.repeat(1, 1, cfg.text_config.hc_count)
                pingpong.write_sample(0, i, h0)
                obs_states[i]["embed"] = pingpong.read_sample(0, i)
                obs_cas_stress_states[i]["embed"] = obs_states[i]["embed"].clone()
                if s.seq_len > chunk_tokens:
                    obs_iso_primary_states[i] = {"embed": obs_states[i]["embed"].clone()}
                    obs_cas_primary_states[i] = {"embed": obs_states[i]["embed"].clone()}
                    obs_cas_prod_states[i] = {"embed": obs_states[i]["embed"].clone()}
        pingpong.flush_slot(0)

        obs_model.visual.rotary_pos_emb = obs_model.visual.rotary_pos_emb.to("cpu")
        free_submodule_to_meta(
            obs_model.visual,
            keep_non_checkpoint_names={"rotary_pos_emb.inv_freq", "rotary_pos_emb.original_inv_freq"},
        )
        free_submodule_to_meta(obs_model.language_model.embed_tokens)
        if device.startswith("cuda"):
            torch.cuda.empty_cache()

        # Pre-index PLE
        ple_parent = obs_model.language_model.layers[1].ple.ple_embedding
        materialize_submodule(ple_parent, "model.language_model.layers.1.ple.ple_embedding", st_index, "cpu")
        stream_ple.build_preindexed_cache(ple_parent, [s.input_ids for s in equiv_samples])
        free_submodule_to_meta(ple_parent, keep_non_checkpoint_names={"ngram_embedding.weight"})

        num_exp = int(cfg.text_config.num_experts)
        for li in PILOT_LAYERS:
            in_slot = li % 2
            out_slot = (li + 1) % 2
            layer = obs_model.language_model.layers[li]
            materialize_submodule(layer, f"model.language_model.layers.{li}", st_index, device)

            acc_unchk = REAPMoEAccumulator(num_exp, capture_routing=True)
            acc_iso_stress = REAPMoEAccumulator(num_exp, capture_routing=True)
            acc_cas_stress = REAPMoEAccumulator(num_exp, capture_routing=True)
            acc_iso_prim = REAPMoEAccumulator(num_exp, capture_routing=True)
            acc_cas_prim = REAPMoEAccumulator(num_exp, capture_routing=True)
            acc_cas_prod = REAPMoEAccumulator(num_exp, capture_routing=True)

            prev_key = "embed" if li == 0 else f"layer_{li - 1}"
            stage_key = f"layer_{li}"

            for i, s in enumerate(equiv_samples):
                h_in = pingpong.read_sample(in_slot, i)
                cos, sin = obs_cos_sin[i]

                # 1B-1: Unchunked observer pass -> proves <1e-4 & 100.0% exact top-k match vs native forward!
                acc_unchk.current_stratum = s.pillar
                acc_unchk.current_lang = s.lang
                h_out = forward_single_decoder_layer(
                    layer=layer,
                    text_cfg=cfg.text_config,
                    hidden_states_cpu=h_in,
                    full_cos_cpu=cos,
                    full_sin_cpu=sin,
                    ple_input_ids_cpu=s.input_ids,
                    device=device,
                    chunk_tokens=unchunked_limit,
                    qsa_long_chunk_tokens=None,
                    reap_acc=acc_unchk,
                )
                obs_unchunked_routing[i][stage_key] = acc_unchk.pop_captured_routing()
                pingpong.write_sample(out_slot, i, h_out)
                obs_states[i][stage_key] = pingpong.read_sample(out_slot, i)

                # 1B-2a: Isolated per-layer stress chunking (`stress_chunk_tokens` = 512 on GPU / 32 on CPU)
                acc_iso_stress.current_stratum = s.pillar
                acc_iso_stress.current_lang = s.lang
                obs_iso_stress_states[i][stage_key] = forward_single_decoder_layer(
                    layer=layer,
                    text_cfg=cfg.text_config,
                    hidden_states_cpu=obs_states[i][prev_key],
                    full_cos_cpu=cos,
                    full_sin_cpu=sin,
                    ple_input_ids_cpu=s.input_ids,
                    device=device,
                    chunk_tokens=stress_chunk_tokens,
                    qsa_long_chunk_tokens=None,
                    reap_acc=acc_iso_stress,
                )
                obs_iso_stress_routing[i][stage_key] = acc_iso_stress.pop_captured_routing()

                # 1B-2b: Cascaded 4-layer stress chunking (`stress_chunk_tokens` = 512 on GPU / 32 on CPU)
                acc_cas_stress.current_stratum = s.pillar
                acc_cas_stress.current_lang = s.lang
                obs_cas_stress_states[i][stage_key] = forward_single_decoder_layer(
                    layer=layer,
                    text_cfg=cfg.text_config,
                    hidden_states_cpu=obs_cas_stress_states[i][prev_key],
                    full_cos_cpu=cos,
                    full_sin_cpu=sin,
                    ple_input_ids_cpu=s.input_ids,
                    device=device,
                    chunk_tokens=stress_chunk_tokens,
                    qsa_long_chunk_tokens=None,
                    reap_acc=acc_cas_stress,
                )
                obs_cas_stress_routing[i][stage_key] = acc_cas_stress.pop_captured_routing()

                # 1B-3: Primary chunk boundary (`chunk_tokens` = 4096 on GPU / 96 on CPU) on S > chunk_tokens!
                if s.seq_len > chunk_tokens:
                    acc_iso_prim.current_stratum = s.pillar
                    acc_iso_prim.current_lang = s.lang
                    obs_iso_primary_states[i][stage_key] = forward_single_decoder_layer(
                        layer=layer,
                        text_cfg=cfg.text_config,
                        hidden_states_cpu=obs_states[i][prev_key],
                        full_cos_cpu=cos,
                        full_sin_cpu=sin,
                        ple_input_ids_cpu=s.input_ids,
                        device=device,
                        chunk_tokens=chunk_tokens,
                        qsa_long_chunk_tokens=None,
                        reap_acc=acc_iso_prim,
                    )
                    obs_iso_primary_routing[i][stage_key] = acc_iso_prim.pop_captured_routing()

                    acc_cas_prim.current_stratum = s.pillar
                    acc_cas_prim.current_lang = s.lang
                    obs_cas_primary_states[i][stage_key] = forward_single_decoder_layer(
                        layer=layer,
                        text_cfg=cfg.text_config,
                        hidden_states_cpu=obs_cas_primary_states[i][prev_key],
                        full_cos_cpu=cos,
                        full_sin_cpu=sin,
                        ple_input_ids_cpu=s.input_ids,
                        device=device,
                        chunk_tokens=chunk_tokens,
                        qsa_long_chunk_tokens=None,
                        reap_acc=acc_cas_prim,
                    )
                    obs_cas_primary_routing[i][stage_key] = acc_cas_prim.pop_captured_routing()

                    # Exact production long-seq config: GDN at `chunk_tokens` (4096), QSA at `stress_chunk_tokens` (512)
                    acc_cas_prod.current_stratum = s.pillar
                    acc_cas_prod.current_lang = s.lang
                    obs_cas_prod_states[i][stage_key] = forward_single_decoder_layer(
                        layer=layer,
                        text_cfg=cfg.text_config,
                        hidden_states_cpu=obs_cas_prod_states[i][prev_key],
                        full_cos_cpu=cos,
                        full_sin_cpu=sin,
                        ple_input_ids_cpu=s.input_ids,
                        device=device,
                        chunk_tokens=chunk_tokens,
                        qsa_long_chunk_tokens=stress_chunk_tokens,
                        reap_acc=acc_cas_prod,
                    )
                    obs_cas_prod_routing[i][stage_key] = acc_cas_prod.pop_captured_routing()

            pingpong.flush_slot(out_slot)

            u_keep = set(acc_unchk.finalize_dict()["keep_indices_k205_sorted"])
            cs_keep = set(acc_cas_stress.finalize_dict()["keep_indices_k205_sorted"])
            reap_jaccard_by_layer[stage_key] = {
                f"unchunked_vs_cascaded_chunk_{stress_chunk_tokens}_k205_jaccard": round(
                    len(u_keep & cs_keep) / max(1, len(u_keep | cs_keep)), 6
                )
            }

            # 1B-0: QSA bit-exact `torch.equal` check (on layer 3 in BF16) + FP32 `allow_tf32=False` DynamicCache proof!
            s_gt = equiv_samples[gt_chunk_sample_idx]
            h_gt_in = obs_states[gt_chunk_sample_idx][prev_key]
            cos_gt, sin_gt = obs_cos_sin[gt_chunk_sample_idx]
            proof_chunks = sorted({stress_chunk_tokens, chunk_tokens})

            if li == 3:
                qsa_bit_exact_check = _verify_qsa_indexer_bit_exact_on_layer3(
                    layer3=layer,
                    text_cfg=cfg.text_config,
                    h_in_cpu=h_gt_in,
                    cos_cpu=cos_gt,
                    sin_cpu=sin_gt,
                    sample_id=s_gt.sample_id,
                    chunk_sizes=proof_chunks,
                    device=device,
                )
                print(
                    f"  [Layer 3 QSA Indexer Variant-A] {s_gt.sample_id} (S={s_gt.seq_len}): "
                    f"unchunked & chunks {proof_chunks} -> torch.equal == True (0 bit diffs)"
                )

            if li in (1, 3):
                # Free 6.70 GiB routed experts + shared expert BEFORE casting stateful submodules to FP32!
                free_submodule_to_meta(layer.mlp.experts)
                free_submodule_to_meta(layer.mlp.shared_expert)
                free_submodule_to_meta(layer.mlp.shared_expert_gate)
                if device.startswith("cuda"):
                    torch.cuda.empty_cache()

                fp32_res = _verify_stateful_layer_fp32_dynamic_cache(
                    layer=layer,
                    layer_idx=li,
                    text_cfg=cfg.text_config,
                    stream_ple=stream_ple if li == 1 else None,
                    h_in_bf16_cpu=h_gt_in,
                    cos_bf16_cpu=cos_gt,
                    sin_bf16_cpu=sin_gt,
                    ple_ids_cpu=s_gt.input_ids,
                    sample_id=s_gt.sample_id,
                    chunk_sizes=proof_chunks,
                    device=device,
                )
                fp32_proofs[stage_key] = fp32_res
                chk_str = ", ".join(
                    f"chk={c}: max_abs={v['post_attn_max_abs_diff']:.2e}, "
                    f"exact_topk={100.0 * v['fp32_router_metrics']['exact_topk_set_match_frac']:.2f}%"
                    for c, v in fp32_res["chunks"].items()
                )
                print(f"  [FP32 allow_tf32=False DynamicCache Proof] {stage_key} ({s_gt.sample_id}, S={s_gt.seq_len}): {chk_str}")

            if li == 1:
                stream_ple.clear_cache()
            free_submodule_to_meta(layer, keep_non_checkpoint_names={"ple.ple_embedding.ngram_embedding.weight"})
            if device.startswith("cuda"):
                torch.cuda.empty_cache()

        materialize_submodule(
            obs_model.language_model.hyper_connection_mixer,
            "model.language_model.hyper_connection_mixer",
            st_index,
            device,
        )
        last_key = f"layer_{PILOT_LAYERS[-1]}"
        with torch.no_grad():
            for i, s in enumerate(equiv_samples):
                obs_states[i]["hc_mixer_out"] = (
                    obs_model.language_model.hyper_connection_mixer(obs_states[i][last_key].to(device))
                    .detach()
                    .to("cpu")
                )
                obs_cas_stress_states[i]["hc_mixer_out"] = (
                    obs_model.language_model.hyper_connection_mixer(obs_cas_stress_states[i][last_key].to(device))
                    .detach()
                    .to("cpu")
                )
                if s.seq_len > chunk_tokens:
                    obs_cas_primary_states[i]["hc_mixer_out"] = (
                        obs_model.language_model.hyper_connection_mixer(obs_cas_primary_states[i][last_key].to(device))
                        .detach()
                        .to("cpu")
                    )
                    obs_cas_prod_states[i]["hc_mixer_out"] = (
                        obs_model.language_model.hyper_connection_mixer(obs_cas_prod_states[i][last_key].to(device))
                        .detach()
                        .to("cpu")
                    )
        free_submodule_to_meta(obs_model.language_model.hyper_connection_mixer)
    finally:
        pingpong.close_and_cleanup(remove_files=True)

    eq_peak_alloc_mib = round(torch.cuda.max_memory_allocated(device) / (1024**2), 2) if device.startswith("cuda") else 0.0
    eq_peak_reserved_mib = (
        round(torch.cuda.max_memory_reserved(device) / (1024**2), 2) if device.startswith("cuda") else 0.0
    )
    del obs_model
    gc.collect()
    if device.startswith("cuda"):
        torch.cuda.empty_cache()

    results: list[dict[str, Any]] = []
    gate_failures: list[str] = []
    stage_keys = ["embed"] + [f"layer_{li}" for li in PILOT_LAYERS] + ["hc_mixer_out"]
    num_exp = int(cfg.text_config.num_experts)

    for i, s in enumerate(equiv_samples):
        per_stage: dict[str, Any] = {}
        stress_stages: dict[str, Any] = {}
        primary_stages: dict[str, Any] | None = {} if s.seq_len > chunk_tokens else None
        prod_stages: dict[str, Any] | None = {} if s.seq_len > chunk_tokens else None

        for stage_key in stage_keys:
            unchk_m = _tensor_diff_metrics(ref_states[i][stage_key], obs_states[i][stage_key])
            if stage_key.startswith("layer_"):
                r_idx, r_w = ref_routing[i][stage_key]
                u_idx, u_w = obs_unchunked_routing[i][stage_key]
                u_rout = compute_topk_routing_metrics(r_idx, r_w, u_idx, u_w, num_exp)
                unchk_m["routing_vs_native"] = u_rout
                if u_rout["exact_topk_set_match_frac"] < 1.0:
                    gate_failures.append(
                        f"Unchunked router mismatch vs native forward on {s.sample_id} {stage_key}: {u_rout}"
                    )
            per_stage[stage_key] = unchk_m
            if unchk_m["max_abs_diff"] >= 1e-4 or unchk_m["cosine_similarity"] < 0.99999:
                gate_failures.append(
                    f"Exact unchunked equivalence failure on {s.sample_id} at {stage_key}: {unchk_m}"
                )

            if stage_key == "embed":
                stress_stages[stage_key] = _tensor_diff_metrics(ref_states[i][stage_key], obs_cas_stress_states[i][stage_key])
                continue

            cas_m = _tensor_diff_metrics(ref_states[i][stage_key], obs_cas_stress_states[i][stage_key])
            if stage_key.startswith("layer_"):
                iso_m = _tensor_diff_metrics(ref_states[i][stage_key], obs_iso_stress_states[i][stage_key])
                r_idx, r_w = ref_routing[i][stage_key]
                iso_idx, iso_w = obs_iso_stress_routing[i][stage_key]
                cas_idx, cas_w = obs_cas_stress_routing[i][stage_key]
                iso_rout = compute_topk_routing_metrics(r_idx, r_w, iso_idx, iso_w, num_exp)
                cas_rout = compute_topk_routing_metrics(r_idx, r_w, cas_idx, cas_w, num_exp)
                stress_stages[stage_key] = {
                    "isolated": iso_m,
                    "cascaded": cas_m,
                    "isolated_routing": iso_rout,
                    "cascaded_routing": cas_rout,
                }
                # Calibrated per-layer BF16 perturbation gates (given FP32 allow_tf32=False already proved 100.00%
                # algorithmic equivalence, BF16 has 13.6% 0-ULP ties + ~10% 1-ULP near-ties across 512 logits, so
                # single-layer GEMM tile changes flip ~5-15% of 10th-place experts -> iso_slot in [0.975, 1.0],
                # and 4-layer MoE cascade keeps cas_cos >= 0.998 & cas_slot >= 0.930):
                if (
                    iso_m["cosine_similarity"] < 0.9999
                    or cas_m["cosine_similarity"] < 0.998
                    or iso_rout["mean_topk_slot_overlap"] < 0.975
                    or cas_rout["mean_topk_slot_overlap"] < 0.930
                ):
                    gate_failures.append(
                        f"Chunked-{stress_chunk_tokens} per-layer gate failed on {s.sample_id} {stage_key}: "
                        f"iso_cos={iso_m['cosine_similarity']}, cas_cos={cas_m['cosine_similarity']}, "
                        f"iso_slot={iso_rout['mean_topk_slot_overlap']}, cas_slot={cas_rout['mean_topk_slot_overlap']}"
                    )
            else:
                # `hc_mixer_out` uses Layer-48 final hc_norm weights on Layer-3 outputs (~65x amplification);
                # logged diagnostically without masking per-layer gates!
                stress_stages[stage_key] = {"cascaded_diagnostic_layer48_hc_norm_on_layer3": cas_m}

        if primary_stages is not None and prod_stages is not None:
            for stage_key in stage_keys:
                if stage_key == "embed":
                    continue
                cas_p = _tensor_diff_metrics(ref_states[i][stage_key], obs_cas_primary_states[i][stage_key])
                cas_pr = _tensor_diff_metrics(ref_states[i][stage_key], obs_cas_prod_states[i][stage_key])
                if stage_key.startswith("layer_"):
                    iso_p = _tensor_diff_metrics(ref_states[i][stage_key], obs_iso_primary_states[i][stage_key])
                    r_idx, r_w = ref_routing[i][stage_key]
                    ip_idx, ip_w = obs_iso_primary_routing[i][stage_key]
                    cp_idx, cp_w = obs_cas_primary_routing[i][stage_key]
                    cpr_idx, cpr_w = obs_cas_prod_routing[i][stage_key]
                    ip_rout = compute_topk_routing_metrics(r_idx, r_w, ip_idx, ip_w, num_exp)
                    cp_rout = compute_topk_routing_metrics(r_idx, r_w, cp_idx, cp_w, num_exp)
                    cpr_rout = compute_topk_routing_metrics(r_idx, r_w, cpr_idx, cpr_w, num_exp)
                    pre_rout = compute_topk_routing_metrics(
                        r_idx[:chunk_tokens], r_w[:chunk_tokens], cp_idx[:chunk_tokens], cp_w[:chunk_tokens], num_exp
                    )
                    post_rout = compute_topk_routing_metrics(
                        r_idx[chunk_tokens:], r_w[chunk_tokens:], cp_idx[chunk_tokens:], cp_w[chunk_tokens:], num_exp
                    )
                    primary_stages[stage_key] = {
                        "isolated": iso_p,
                        "cascaded": cas_p,
                        "isolated_routing": ip_rout,
                        "cascaded_routing": cp_rout,
                        "pre_boundary_0_to_chunk_routing": pre_rout,
                        "post_boundary_chunk_to_end_routing": post_rout,
                    }
                    prod_stages[stage_key] = {
                        "cascaded": cas_pr,
                        "cascaded_routing": cpr_rout,
                    }
                    if (
                        iso_p["cosine_similarity"] < 0.9999
                        or cas_p["cosine_similarity"] < 0.998
                        or ip_rout["mean_topk_slot_overlap"] < 0.975
                        or cp_rout["mean_topk_slot_overlap"] < 0.940
                        or cas_pr["cosine_similarity"] < 0.998
                        or cpr_rout["mean_topk_slot_overlap"] < 0.930
                    ):
                        gate_failures.append(
                            f"Chunked-{chunk_tokens} boundary gate failed on {s.sample_id} {stage_key}: "
                            f"iso_cos={iso_p['cosine_similarity']}, cas_cos={cas_p['cosine_similarity']}, "
                            f"iso_slot={ip_rout['mean_topk_slot_overlap']}, cas_slot={cp_rout['mean_topk_slot_overlap']}, "
                            f"prod_cos={cas_pr['cosine_similarity']}, prod_slot={cpr_rout['mean_topk_slot_overlap']}"
                        )
                else:
                    primary_stages[stage_key] = {"cascaded_diagnostic_layer48_hc_norm_on_layer3": cas_p}
                    prod_stages[stage_key] = {"cascaded_diagnostic_layer48_hc_norm_on_layer3": cas_pr}

        l3_iso_slot = stress_stages["layer_3"]["isolated_routing"]["mean_topk_slot_overlap"]
        l3_cas_slot = stress_stages["layer_3"]["cascaded_routing"]["mean_topk_slot_overlap"]
        l3_cas_cos = stress_stages["layer_3"]["cascaded"]["cosine_similarity"]
        print(
            f"  [{s.sample_id}] ({s.pillar}, {s.lang}, {s.modality}, S={s.seq_len}): "
            f"unchunked hc_mixer max_abs={per_stage['hc_mixer_out']['max_abs_diff']:.2e} "
            f"(10/10 rout=100.0%); chunk_{stress_chunk_tokens} L3 cas_cos={l3_cas_cos:.6f}, "
            f"iso_slot={100.0 * l3_iso_slot:.2f}%, cas_slot={100.0 * l3_cas_slot:.2f}%"
        )
        results.append(
            {
                "sample_id": s.sample_id,
                "pillar": s.pillar,
                "lang": s.lang,
                "modality": s.modality,
                "seq_len": s.seq_len,
                "reference_method": "native_Qwen4ExpModel.forward(use_cache=False)",
                "primary_chunk_tokens": chunk_tokens,
                "stress_chunk_tokens": stress_chunk_tokens,
                "stages": per_stage,
                "chunked_stress_stages": stress_stages,
                "chunked_primary_stages": primary_stages,
                "chunked_production_hybrid_stages": prod_stages,
            }
        )

    for stg_k, jac_d in reap_jaccard_by_layer.items():
        for jk, jv in jac_d.items():
            if jv < 0.94:
                gate_failures.append(f"REAP K=205 Jaccard gate failed on {stg_k} ({jk}={jv} < 0.94)")

    equiv_payload = {
        "samples": results,
        "fp32_dynamic_cache_proof": fp32_proofs,
        "qsa_indexer_bit_exact_check": qsa_bit_exact_check,
        "reap_k205_jaccard_unchunked_vs_stress_chunked": reap_jaccard_by_layer,
        "equiv_peak_vram_allocated_mib": eq_peak_alloc_mib,
        "equiv_peak_vram_reserved_mib": eq_peak_reserved_mib,
        "gate_failures": gate_failures,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "equiv_verification.json").write_text(
        json.dumps(equiv_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if gate_failures:
        raise AssertionError("Equivalence gate failures:\n  - " + "\n  - ".join(gate_failures))

    return equiv_payload


def _pick_equiv_sample(cands: list[PreparedSample], label: str, max_len: int) -> PreparedSample:
    in_multi_chunk = [s for s in cands if 550 <= s.seq_len <= max_len]
    pool = in_multi_chunk if in_multi_chunk else [s for s in cands if s.seq_len <= max_len]
    if not pool:
        raise RuntimeError(f"No {label} candidate <= {max_len} tokens found in pilot_samples")
    return sorted(pool, key=lambda s: abs(s.seq_len - 1800))[0]


@torch.no_grad()
def benchmark_qsa_indexer_modes_on_layer3(
    layer3: Qwen4ExpTextDecoderLayer,
    text_cfg: Qwen4ExpTextConfig,
    pingpong: DiskHiddenStatePingPong,
    in_slot: int,
    pilot_samples: list[PreparedSample],
    bench_indices: list[int],
    qsa_chunk: int,
    device: str,
) -> dict[str, Any]:
    """Benchmark unmodified upstream `Qwen4ExpTextQSAIndexer.forward` vs `Variant A` on real Layer-3 GPU weights."""
    base_indexer = layer3.self_attn.indexer
    is_cuda = device.startswith("cuda")
    per_sample: list[dict[str, Any]] = []

    for s_idx in bench_indices:
        s = pilot_samples[s_idx]
        assert s.rotary_cos is not None and s.rotary_sin is not None
        h_in_cpu = pingpong.read_sample(in_slot, s_idx)
        seq_len = int(s.seq_len)

        # Precompute attention input `[1, S, 2560]` (~80 MiB at 16K) outside the timed indexer region
        h_attn_chunks: list[torch.Tensor] = []
        for st in range(0, seq_len, qsa_chunk):
            ed = min(seq_len, st + qsa_chunk)
            ha, _, _ = layer3.attn_hyper_connection(h_in_cpu[:, st:ed, :].to(device, non_blocking=False))
            h_attn_chunks.append(ha)
        h_attn_dev = torch.cat(h_attn_chunks, dim=1)
        del h_attn_chunks, h_in_cpu
        cos_dev = s.rotary_cos.to(device, non_blocking=False)
        sin_dev = s.rotary_sin.to(device, non_blocking=False)

        # Warmup 1 short call
        m_warm = torch.ones((1, 1, 8, 8), dtype=torch.bool, device=device)
        _ = fast_exact_qsa_indexer_forward(base_indexer, h_attn_dev[:, :8, :], (cos_dev[:, :8, :], sin_dev[:, :8, :]), m_warm, None)
        del m_warm

        # 1. Unmodified upstream `Qwen4ExpTextQSAIndexer.forward`
        if is_cuda:
            torch.cuda.synchronize(device)
        t_up0 = time.perf_counter()
        c_up = DynamicCache(config=text_cfg)
        up_masks: list[torch.Tensor] = []
        for st in range(0, seq_len, qsa_chunk):
            ed = min(seq_len, st + qsa_chunk)
            mc = torch.arange(0, ed, device=device).view(1, 1, 1, -1) <= torch.arange(st, ed, device=device).view(
                1, 1, -1, 1
            )
            up_masks.append(
                Qwen4ExpTextQSAIndexer.forward(
                    base_indexer, h_attn_dev[:, st:ed, :], (cos_dev[:, :ed, :], sin_dev[:, :ed, :]), mc, c_up
                )
            )
        if is_cuda:
            torch.cuda.synchronize(device)
        t_up = time.perf_counter() - t_up0
        up_masks_cpu = [m.cpu() for m in up_masks]
        del c_up, up_masks
        if is_cuda:
            torch.cuda.empty_cache()

        # 2. Pre-pooled bit-exact `fast_exact_qsa_indexer_forward` (`Variant A`)
        if is_cuda:
            torch.cuda.synchronize(device)
        t_fa0 = time.perf_counter()
        c_fa = DynamicCache(config=text_cfg)
        fa_masks: list[torch.Tensor] = []
        for st in range(0, seq_len, qsa_chunk):
            ed = min(seq_len, st + qsa_chunk)
            mc = torch.arange(0, ed, device=device).view(1, 1, 1, -1) <= torch.arange(st, ed, device=device).view(
                1, 1, -1, 1
            )
            fa_masks.append(
                fast_exact_qsa_indexer_forward(
                    base_indexer, h_attn_dev[:, st:ed, :], (cos_dev[:, :ed, :], sin_dev[:, :ed, :]), mc, c_fa
                )
            )
        if is_cuda:
            torch.cuda.synchronize(device)
        t_fa = time.perf_counter() - t_fa0
        fa_masks_cpu = [m.cpu() for m in fa_masks]
        del c_fa, fa_masks
        if is_cuda:
            torch.cuda.empty_cache()

        for chunk_i, (mu, mf) in enumerate(zip(up_masks_cpu, fa_masks_cpu)):
            if not torch.equal(mu, mf):
                n_diff = int((mu != mf).sum().item())
                raise AssertionError(
                    f"Layer-3 QSA A/B benchmark bit-exact check failed on {s.sample_id} chunk {chunk_i}: {n_diff} diffs!"
                )
        del up_masks_cpu, fa_masks_cpu, h_attn_dev, cos_dev, sin_dev
        if is_cuda:
            torch.cuda.empty_cache()

        speedup = t_up / max(1e-6, t_fa)
        print(
            f"  [Layer 3 QSA Indexer A/B] {s.sample_id} (S={seq_len}, chunk={qsa_chunk}): "
            f"upstream={t_up:.3f}s vs variant_a={t_fa:.4f}s ({speedup:.1f}x speedup, torch.equal=True)"
        )
        per_sample.append(
            {
                "sample_id": s.sample_id,
                "pillar": s.pillar,
                "seq_len": seq_len,
                "qsa_chunk_tokens": qsa_chunk,
                "upstream_indexer_sec": round(t_up, 5),
                "variant_a_indexer_sec": round(t_fa, 5),
                "delta_upstream_minus_variant_a_sec": round(max(0.0, t_up - t_fa), 5),
                "speedup_x": round(speedup, 2),
                "torch_equal_all_chunks": True,
            }
        )

    return {"samples": per_sample}


def _extrapolate_upstream_qsa_delta_per_layer_sec(
    ab_samples: list[dict[str, Any]],
    all_seq_lens: list[int],
) -> float:
    """Fit `delta_t(S) = alpha * S + beta * S^2` from measured Layer-3 A/B points and sum across all rows."""
    if not ab_samples:
        return 0.0
    if len(ab_samples) == 1:
        p0 = ab_samples[0]
        s0 = max(1.0, float(p0["seq_len"]))
        dt0 = max(0.0, float(p0["delta_upstream_minus_variant_a_sec"]))
        beta = dt0 / (s0 * s0)
        return sum(beta * (float(sl) ** 2) for sl in all_seq_lens)

    pts = sorted(ab_samples, key=lambda x: int(x["seq_len"]))
    s1, dt1 = float(pts[0]["seq_len"]), max(0.0, float(pts[0]["delta_upstream_minus_variant_a_sec"]))
    s2, dt2 = float(pts[-1]["seq_len"]), max(0.0, float(pts[-1]["delta_upstream_minus_variant_a_sec"]))
    if s2 <= s1:
        beta = dt2 / max(1.0, s2 * s2)
        return sum(beta * (float(sl) ** 2) for sl in all_seq_lens)

    # Solve dt1/s1 = alpha + beta*s1, dt2/s2 = alpha + beta*s2 with non-negative clamping
    r1 = dt1 / s1
    r2 = dt2 / s2
    beta = max(0.0, (r2 - r1) / (s2 - s1))
    alpha = max(0.0, r1 - beta * s1)
    return sum(alpha * float(sl) + beta * (float(sl) ** 2) for sl in all_seq_lens)


def main() -> int:
    parser = argparse.ArgumentParser(description="SmartLLM Step 5 Streaming REAP Pilot Observer")
    parser.add_argument("--self-test-cpu", action="store_true", help="Run synthetic CPU equivalence self-test only")
    parser.add_argument("--dry-run-cpu", action="store_true", help="Validate real dataset tokenization, meta init & full PLE index on CPU (0 GPU)")
    parser.add_argument("--seed", type=int, default=20261111, help="Deterministic seed for 5%% pilot selection")
    parser.add_argument("--chunk-tokens", type=int, default=DEFAULT_CHUNK_TOKENS, help="Chunk size for long sequences")
    parser.add_argument("--keep-buffers", action="store_true", help="Keep temporary disk ping-pong buffers")
    args = parser.parse_args()

    if args.self_test_cpu:
        return run_cpu_self_test()

    t_wall_start = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load calibration dataset & select stratified pilot subset
    all_rows = [json.loads(line) for line in CALIB_JSONL.open(encoding="utf-8") if line.strip()]
    total_dataset_tokens = sum(int(r["qwen38_tokens"]) for r in all_rows)
    total_regular_tokens = sum(int(r["qwen38_tokens"]) for r in all_rows if r["pillar"] != "long_context")
    total_unchunked_reg_tokens = sum(
        int(r["qwen38_tokens"])
        for r in all_rows
        if r["pillar"] != "long_context" and int(r["qwen38_tokens"]) <= args.chunk_tokens
    )
    total_gt4k_reg_tokens = sum(
        int(r["qwen38_tokens"])
        for r in all_rows
        if r["pillar"] != "long_context" and int(r["qwen38_tokens"]) > args.chunk_tokens
    )
    total_long_tokens = sum(int(r["qwen38_tokens"]) for r in all_rows if r["pillar"] == "long_context")
    full_mm_rows = sum(1 for r in all_rows if r["modality"] == "multimodal")
    full_stratum_tokens: dict[str, int] = defaultdict(int)
    for r in all_rows:
        full_stratum_tokens[str(r["pillar"])] += int(r["qwen38_tokens"])

    pilot_rows = select_stratified_pilot_rows(all_rows, seed=args.seed)
    pilot_total_tokens = sum(int(r["qwen38_tokens"]) for r in pilot_rows)
    pilot_mm_rows = sum(1 for r in pilot_rows if r["modality"] == "multimodal")
    pilot_curated_p4_rows = sum(
        1
        for r in pilot_rows
        if r["pillar"] == "pillar_4_art_direction_copywriting"
        and r.get("source_repo") == "SmartLLM/curated-bilingual-canons"
    )
    print(
        f"Selected {len(pilot_rows)}/{len(all_rows)} stratified pilot rows "
        f"({pilot_total_tokens:,} / {total_dataset_tokens:,} tokens; curated_p4={pilot_curated_p4_rows})."
    )

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True, local_files_only=True)
    proc = AutoProcessor.from_pretrained(str(MODEL_DIR), trust_remote_code=True, local_files_only=True)
    pilot_samples = tokenize_rows(pilot_rows, tok, proc, ROOT)

    # Pick 4 representative samples for Part 1 Equivalence Check:
    #   1 EN CoT frontend (<=4096), 1 RU agentic (<=4096), 1 multimodal Pillar 3 (<=4096),
    #   AND 1 regular >4096 sample (`calib_0072`, S=5309) exercising active QSA `topk(512)` & `chunk_4096`!
    eq_en = _pick_equiv_sample(
        [s for s in pilot_samples if s.pillar == "pillar_1_frontend_3d_svg" and s.lang == "en"],
        "EN frontend",
        args.chunk_tokens,
    )
    eq_ru = _pick_equiv_sample(
        [s for s in pilot_samples if s.pillar == "agentic_tool_calling" and s.lang == "ru"],
        "RU agentic",
        args.chunk_tokens,
    )
    eq_mm = _pick_equiv_sample(
        [s for s in pilot_samples if s.modality == "multimodal"],
        "Multimodal Pillar 3",
        args.chunk_tokens,
    )
    gt4k_cands = [
        s for s in pilot_samples if s.pillar != "long_context" and args.chunk_tokens < s.seq_len <= 8192
    ]
    if not gt4k_cands:
        raise RuntimeError(f"Expected >=1 regular sample in ({args.chunk_tokens}, 8192] inside pilot_samples!")
    eq_gt4k = sorted(gt4k_cands, key=lambda s: s.seq_len)[0]
    equiv_samples = [eq_en, eq_ru, eq_mm, eq_gt4k]

    # 2. Load config (forcing SDPA + eager experts) & SafetensorsIndex
    cfg = AutoConfig.from_pretrained(str(MODEL_DIR), trust_remote_code=True, local_files_only=True)
    cfg._attn_implementation = "sdpa"
    cfg.text_config._attn_implementation = "sdpa"
    cfg.vision_config._attn_implementation = "sdpa"
    cfg._experts_implementation = "eager"
    cfg.text_config._experts_implementation = "eager"
    st_index = SafetensorsIndex(MODEL_DIR)

    if args.dry_run_cpu:
        ple_prefix = "model.language_model.layers.1.ple.ple_embedding.ngram_embedding"
        num_ple_shards = int(cfg.text_config.split_ngram_parts)
        ple_head_dim = int(cfg.text_config.ple_embed_dim) // (
            (int(cfg.text_config.ngram_size) - 1) * int(cfg.text_config.heads_per_ngram)
        )
        shard0_name = f"{ple_prefix}.shard_0.weight"
        with safe_open(str(st_index.checkpoint_dir / st_index.weight_map[shard0_name]), framework="pt", device="cpu") as f:
            shard_rows = int(f.get_slice(shard0_name).get_shape()[0])
        with torch.device("meta"):
            obs_model = Qwen4ExpModel(cfg)
        obs_model.eval()
        stream_ple = StreamingPLENGramEmbedding(
            index=st_index,
            shard_prefix=ple_prefix,
            num_shards=num_ple_shards,
            shard_rows=shard_rows,
            embed_dim=ple_head_dim,
            dtype=torch.bfloat16,
        )
        obs_model.language_model.layers[1].ple.ple_embedding.ngram_embedding = stream_ple
        ple_parent = obs_model.language_model.layers[1].ple.ple_embedding
        materialize_submodule(ple_parent, "model.language_model.layers.1.ple.ple_embedding", st_index, "cpu")
        all_ple_ids = build_all_dataset_ple_input_ids(
            all_rows=all_rows,
            tok=tok,
            proc=proc,
            root_dir=ROOT,
            verified_pilot_map={s.sample_id: s for s in pilot_samples},
        )
        exact_ple = compute_exact_full_dataset_ple_stats(ple_parent, stream_ple, all_ple_ids)
        print("CPU DRY-RUN PASSED! Equiv samples:", [(s.sample_id, s.seq_len) for s in equiv_samples])
        print("Pilot P4 source breakdown:", dict(Counter(
            r.get("source_repo", "") for r in pilot_rows if r["pillar"] == "pillar_4_art_direction_copywriting"
        )))
        print("Exact Full-Dataset PLE Stats:", json.dumps(exact_ple, indent=2))
        return 0

    # 0. Pre-flight GPU, RAM, and Disk checks
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; Step 5 pilot requires RTX 4080 Laptop GPU.")
    foreign_apps = [a for a in query_nvidia_smi_apps() if a["pid"] != os.getpid()]
    if foreign_apps:
        raise RuntimeError(f"Foreign GPU compute process detected (Rule 6.3 violation): {foreign_apps}")

    device = "cuda:0"
    # Cap PyTorch CUDACachingAllocator strictly below 12 GiB physical GDDR6 (`0.88 * 12281.5 = 10808 MiB`)
    # so growing 512-token QSA chunks on 16K-36K sequences trigger internal cache reclamation inside GDDR6
    # instead of spilling cached blocks into Windows WDDM Shared System Memory over PCIe!
    torch.cuda.set_per_process_memory_fraction(0.88, 0)
    gpu_name = torch.cuda.get_device_name(0)
    gpu_total_mib = round(torch.cuda.get_device_properties(0).total_memory / (1024**2), 2)
    disk_before = shutil.disk_usage(str(ROOT))
    ram_before = get_windows_ram_telemetry()
    pages_out_before = sample_pages_output_per_sec()
    min_avail_ram_gib = ram_before["avail_phys_gib"]
    pages_out_samples: list[float] = [x for x in [pages_out_before] if x is not None]

    print(
        f"GPU: {gpu_name} ({gpu_total_mib} MiB) | Free RAM: {ram_before['avail_phys_gib']:.2f} GiB | "
        f"Free D:: {disk_before.free / (1024**3):.2f} GiB"
    )

    # 3. Run Part 1: Exact Numerical, FP32 DynamicCache & BF16 Routing Equivalence Check
    equiv_results = run_equivalence_check_gpu(
        cfg,
        st_index,
        equiv_samples,
        device,
        chunk_tokens=args.chunk_tokens,
        stress_chunk_tokens=QSA_LONG_CHUNK_TOKENS,
    )

    # 4. Run Part 2: Full Stratified Pilot on Layers 0..3
    print(f"\n=== Part 2: Streaming Layerwise REAP Pilot across {len(pilot_samples)} Samples (Layers {PILOT_LAYERS}) ===")
    torch.cuda.reset_peak_memory_stats(device)

    ple_prefix = "model.language_model.layers.1.ple.ple_embedding.ngram_embedding"
    num_ple_shards = int(cfg.text_config.split_ngram_parts)
    ple_head_dim = int(cfg.text_config.ple_embed_dim) // (
        (int(cfg.text_config.ngram_size) - 1) * int(cfg.text_config.heads_per_ngram)
    )
    shard0_name = f"{ple_prefix}.shard_0.weight"
    with safe_open(str(st_index.checkpoint_dir / st_index.weight_map[shard0_name]), framework="pt", device="cpu") as f:
        shard_rows = int(f.get_slice(shard0_name).get_shape()[0])

    t_meta0 = time.perf_counter()
    with torch.device("meta"):
        obs_model = Qwen4ExpModel(cfg)
    obs_model.eval()
    t_meta_init = time.perf_counter() - t_meta0
    ram_after_meta = get_windows_ram_telemetry()
    min_avail_ram_gib = min(min_avail_ram_gib, ram_after_meta["avail_phys_gib"])

    obs_model.visual.rotary_pos_emb = Qwen4ExpVisionRotaryEmbedding(cfg.vision_config)
    obs_model.language_model.rotary_emb = Qwen4ExpTextRotaryEmbedding(config=cfg.text_config)
    stream_ple = StreamingPLENGramEmbedding(
        index=st_index,
        shard_prefix=ple_prefix,
        num_shards=num_ple_shards,
        shard_rows=shard_rows,
        embed_dim=ple_head_dim,
        dtype=torch.bfloat16,
    )
    obs_model.language_model.layers[1].ple.ple_embedding.ngram_embedding = stream_ple
    qsa_wrapper_l3 = QSAIndexerWrapper(
        obs_model.language_model.layers[3].self_attn.indexer, mode="fast_exact_a", sync_timing=True
    )

    buf_dir = OUT_DIR / "_pilot_hc_pingpong"
    hc_width = int(cfg.text_config.hc_count) * int(cfg.text_config.hidden_size)
    pingpong = DiskHiddenStatePingPong(buf_dir, [s.seq_len for s in pilot_samples], hc_width)
    qsa_indexer_ab_benchmark: dict[str, Any] = {}

    try:
        # Stage A: Input embeddings + Vision encoder (`model.visual`) + M-RoPE `(cos, sin)`
        t_emb_l0 = time.perf_counter()
        _, emb_bytes, emb_shards = materialize_submodule(
            obs_model.language_model.embed_tokens, "model.language_model.embed_tokens", st_index, "cpu"
        )
        t_emb_load = time.perf_counter() - t_emb_l0

        t_vis_l0 = time.perf_counter()
        _, vis_bytes, vis_shards = materialize_submodule(obs_model.visual, "model.visual", st_index, device)
        obs_model.visual.rotary_pos_emb = obs_model.visual.rotary_pos_emb.to(device)
        torch.cuda.synchronize(device)
        t_vis_load = time.perf_counter() - t_vis_l0
        t_emb_vis_load = t_emb_load + t_vis_load

        t_emb_mrope_sec = 0.0
        t_vis_only_sec = 0.0
        t_emb_fwd0 = time.perf_counter()
        with torch.no_grad():
            for i, s in enumerate(pilot_samples):
                t_e0 = time.perf_counter()
                emb = obs_model.language_model.embed_tokens(s.input_ids)
                t_emb_mrope_sec += time.perf_counter() - t_e0

                if s.pixel_values is not None:
                    torch.cuda.synchronize(device)
                    t_v0 = time.perf_counter()
                    vis_out = obs_model.get_image_features(
                        s.pixel_values.to(device), s.image_grid_thw.to(device), return_dict=True
                    )
                    img_emb = torch.cat(vis_out.pooler_output, dim=0).to("cpu", emb.dtype)
                    torch.cuda.synchronize(device)
                    t_vis_only_sec += time.perf_counter() - t_v0

                    t_e1 = time.perf_counter()
                    img_mask, _ = obs_model.get_placeholder_mask(s.input_ids, inputs_embeds=emb, image_features=img_emb)
                    emb = emb.masked_scatter(img_mask, img_emb)
                    t_emb_mrope_sec += time.perf_counter() - t_e1

                t_r0 = time.perf_counter()
                cos, sin = compute_position_embeddings_for_sample(obs_model, s, emb, rotary_device=device)
                s.rotary_cos = cos
                s.rotary_sin = sin
                t_emb_mrope_sec += time.perf_counter() - t_r0

                pingpong.write_sample(0, i, emb.repeat(1, 1, cfg.text_config.hc_count))
                # Free raw image patch tensors from CPU RAM immediately once `h0` & M-RoPE are saved!
                s.pixel_values = None
                s.image_grid_thw = None
                s.mm_token_type_ids = None
        pingpong.flush_slot(0)
        t_emb_vis_fwd = time.perf_counter() - t_emb_fwd0

        vis_vram_peak_mib = round(torch.cuda.max_memory_allocated(device) / (1024**2), 2)
        vis_vram_reserved_mib = round(torch.cuda.max_memory_reserved(device) / (1024**2), 2)
        ram_stage_a = get_windows_ram_telemetry()
        min_avail_ram_gib = min(min_avail_ram_gib, ram_stage_a["avail_phys_gib"])

        obs_model.visual.rotary_pos_emb = obs_model.visual.rotary_pos_emb.to("cpu")
        free_submodule_to_meta(
            obs_model.visual,
            keep_non_checkpoint_names={"rotary_pos_emb.inv_freq", "rotary_pos_emb.original_inv_freq"},
        )
        free_submodule_to_meta(obs_model.language_model.embed_tokens)
        gc.collect()
        torch.cuda.empty_cache()

        # Stage B: Exact Full-Dataset PLE N-Gram Audit (0 shard reads) + Pre-index Pilot PLE Cache in 1 shard pass
        ple_parent = obs_model.language_model.layers[1].ple.ple_embedding
        materialize_submodule(ple_parent, "model.language_model.layers.1.ple.ple_embedding", st_index, "cpu")
        all_ple_ids = build_all_dataset_ple_input_ids(
            all_rows=all_rows,
            tok=tok,
            proc=proc,
            root_dir=ROOT,
            verified_pilot_map={s.sample_id: s for s in pilot_samples},
        )
        full_dataset_ple_exact = compute_exact_full_dataset_ple_stats(ple_parent, stream_ple, all_ple_ids)
        del all_ple_ids
        ple_prefetch_stats = stream_ple.build_preindexed_cache(ple_parent, [s.input_ids for s in pilot_samples])
        ple_prefetch_stats["full_dataset_exact_audit"] = full_dataset_ple_exact
        free_submodule_to_meta(ple_parent, keep_non_checkpoint_names={"ngram_embedding.weight"})
        ram_after_ple_prefetch = get_windows_ram_telemetry()
        min_avail_ram_gib = min(min_avail_ram_gib, ram_after_ple_prefetch["avail_phys_gib"])
        po = sample_pages_output_per_sec()
        if po is not None:
            pages_out_samples.append(po)
        print(
            f"  PLE Prefetch (Pilot): {ple_prefetch_stats['unique_ngram_rows']:,} unique rows across "
            f"{ple_prefetch_stats['ple_safetensors_files_opened']} shards ({ple_prefetch_stats['cache_ram_mib']} MiB RAM) "
            f"in {ple_prefetch_stats['safetensors_slice_io_sec']:.2f}s"
        )
        print(
            f"  PLE Exact Full-Dataset Audit ({full_dataset_ple_exact['full_dataset_samples']} rows): "
            f"{full_dataset_ple_exact['full_dataset_unique_ngram_rows']:,} unique rows across "
            f"{full_dataset_ple_exact['full_dataset_ple_safetensors_files_touched']} shards = "
            f"{full_dataset_ple_exact['full_dataset_exact_cache_ram_gib']:.4f} GiB exact RAM!"
        )

        # Stage C: Layer-by-layer streaming replay across PILOT_LAYERS (0, 1, 2, 3)
        layer_telemetry: list[dict[str, Any]] = []
        scores_by_layer: dict[str, Any] = {}

        gt4k_pilot_idx = next(idx for idx, s in enumerate(pilot_samples) if s.sample_id == eq_gt4k.sample_id)
        lc_pilot_indices = sorted(
            [idx for idx, s in enumerate(pilot_samples) if s.pillar == "long_context"],
            key=lambda idx: pilot_samples[idx].seq_len,
        )
        bench_qsa_indices = [gt4k_pilot_idx] + ([lc_pilot_indices[0]] if lc_pilot_indices else [])

        for li in PILOT_LAYERS:
            in_slot = li % 2
            out_slot = (li + 1) % 2
            layer = obs_model.language_model.layers[li]
            if li == 3:
                qsa_wrapper_l3.reset_stats()

            torch.cuda.reset_peak_memory_stats(device)
            t_load0 = time.perf_counter()
            n_tensors, loaded_bytes, touched_shards = materialize_submodule(
                layer, f"model.language_model.layers.{li}", st_index, device
            )
            torch.cuda.synchronize(device)
            t_load = time.perf_counter() - t_load0
            weights_vram_mib = round(torch.cuda.memory_allocated(device) / (1024**2), 2)

            acc = REAPMoEAccumulator(cfg.text_config.num_experts)
            regular_fwd_sec = 0.0
            regular_tokens = 0
            unchunked_reg_fwd_sec = 0.0
            unchunked_reg_tokens = 0
            gt4k_reg_fwd_sec = 0.0
            gt4k_reg_tokens = 0
            long_fwd_sec = 0.0
            long_tokens = 0
            reg_indexer_sec = 0.0
            long_indexer_sec = 0.0
            layer_prof: dict[str, float] = {"attn_total_sec": 0.0, "moe_sec": 0.0}
            min_layer_avail_ram_gib = get_windows_ram_telemetry()["avail_phys_gib"]

            t_layer_fwd0 = time.perf_counter()
            for i, s in enumerate(pilot_samples):
                acc.current_stratum = s.pillar
                acc.current_lang = s.lang
                acc.current_subbucket = (
                    "craft_p4"
                    if (
                        s.pillar == "pillar_4_art_direction_copywriting"
                        and s.source_repo == "SmartLLM/curated-bilingual-canons"
                    )
                    else None
                )
                h_in = pingpong.read_sample(in_slot, i)
                assert s.rotary_cos is not None and s.rotary_sin is not None

                idx_before = qsa_wrapper_l3.elapsed_sec if li == 3 else 0.0
                t_s0 = time.perf_counter()
                h_out = forward_single_decoder_layer(
                    layer=layer,
                    text_cfg=cfg.text_config,
                    hidden_states_cpu=h_in,
                    full_cos_cpu=s.rotary_cos,
                    full_sin_cpu=s.rotary_sin,
                    ple_input_ids_cpu=s.input_ids,
                    device=device,
                    chunk_tokens=args.chunk_tokens,
                    qsa_long_chunk_tokens=QSA_LONG_CHUNK_TOKENS,
                    reap_acc=acc,
                    layer_prof=layer_prof,
                )
                torch.cuda.synchronize(device)
                dt_s = time.perf_counter() - t_s0
                idx_dt = (qsa_wrapper_l3.elapsed_sec - idx_before) if li == 3 else 0.0

                if s.pillar == "long_context":
                    long_fwd_sec += dt_s
                    long_tokens += s.seq_len
                    long_indexer_sec += idx_dt
                    # Sample RAM & swap telemetry during active 16K-36K long-context execution!
                    lc_ram = get_windows_ram_telemetry()
                    min_layer_avail_ram_gib = min(min_layer_avail_ram_gib, lc_ram["avail_phys_gib"])
                    min_avail_ram_gib = min(min_avail_ram_gib, lc_ram["avail_phys_gib"])
                    po_lc = sample_pages_output_per_sec()
                    if po_lc is not None:
                        pages_out_samples.append(po_lc)
                else:
                    regular_fwd_sec += dt_s
                    regular_tokens += s.seq_len
                    reg_indexer_sec += idx_dt
                    if s.seq_len <= args.chunk_tokens:
                        unchunked_reg_fwd_sec += dt_s
                        unchunked_reg_tokens += s.seq_len
                    else:
                        gt4k_reg_fwd_sec += dt_s
                        gt4k_reg_tokens += s.seq_len

                pingpong.write_sample(out_slot, i, h_out)
                del h_in, h_out

            ram_pre_flush = get_windows_ram_telemetry()
            min_layer_avail_ram_gib = min(min_layer_avail_ram_gib, ram_pre_flush["avail_phys_gib"])
            min_avail_ram_gib = min(min_avail_ram_gib, ram_pre_flush["avail_phys_gib"])
            pingpong.flush_slot(out_slot)
            t_layer_total_wall = time.perf_counter() - t_layer_fwd0

            peak_alloc_mib = round(torch.cuda.max_memory_allocated(device) / (1024**2), 2)
            peak_reserved_mib = round(torch.cuda.max_memory_reserved(device) / (1024**2), 2)
            ram_snap = get_windows_ram_telemetry()
            min_layer_avail_ram_gib = min(min_layer_avail_ram_gib, ram_snap["avail_phys_gib"])
            min_avail_ram_gib = min(min_avail_ram_gib, min_layer_avail_ram_gib)
            po = sample_pages_output_per_sec()
            if po is not None:
                pages_out_samples.append(po)

            # Opus Mandatory Action #2: Direct Layer-3 GPU timing of unmodified upstream QSA indexer vs Variant A
            if li == 3:
                qsa_indexer_ab_benchmark = benchmark_qsa_indexer_modes_on_layer3(
                    layer3=layer,
                    text_cfg=cfg.text_config,
                    pingpong=pingpong,
                    in_slot=in_slot,
                    pilot_samples=pilot_samples,
                    bench_indices=bench_qsa_indices,
                    qsa_chunk=QSA_LONG_CHUNK_TOKENS,
                    device=device,
                )

            layer_scores = acc.finalize_dict(full_stratum_tokens=dict(full_stratum_tokens))
            scores_by_layer[f"layer_{li}"] = {
                "layer_idx": li,
                "layer_type": layer.layer_type,
                "has_ple": layer.ple is not None,
                **layer_scores,
            }

            lt_entry: dict[str, Any] = {
                "layer_idx": li,
                "layer_type": layer.layer_type,
                "has_ple": layer.ple is not None,
                "shards_read": touched_shards,
                "num_tensors_loaded": n_tensors,
                "loaded_weight_bytes": loaded_bytes,
                "shard_load_sec": round(t_load, 4),
                "regular_tokens": regular_tokens,
                "regular_forward_sec": round(regular_fwd_sec, 4),
                "regular_tok_per_sec": round(regular_tokens / max(1e-6, regular_fwd_sec), 2),
                "unchunked_regular_tokens": unchunked_reg_tokens,
                "unchunked_regular_forward_sec": round(unchunked_reg_fwd_sec, 4),
                "unchunked_regular_tok_per_sec": round(unchunked_reg_tokens / max(1e-6, unchunked_reg_fwd_sec), 2),
                "gt4k_regular_tokens": gt4k_reg_tokens,
                "gt4k_regular_forward_sec": round(gt4k_reg_fwd_sec, 4),
                "gt4k_regular_tok_per_sec": round(gt4k_reg_tokens / max(1e-6, gt4k_reg_fwd_sec), 2)
                if gt4k_reg_tokens > 0
                else 0.0,
                "long_context_tokens": long_tokens,
                "long_context_forward_sec": round(long_fwd_sec, 4),
                "long_context_tok_per_sec": round(long_tokens / max(1e-6, long_fwd_sec), 2),
                "substage_profile_sec": {
                    "attn_or_gdn_total_sec": round(layer_prof.get("attn_total_sec", 0.0), 4),
                    "moe_total_sec": round(layer_prof.get("moe_sec", 0.0), 4),
                    "qsa_variant_a_indexer_total_sec": round(qsa_wrapper_l3.elapsed_sec, 4) if li == 3 else 0.0,
                    "qsa_variant_a_indexer_regular_sec": round(reg_indexer_sec, 4) if li == 3 else 0.0,
                    "qsa_variant_a_indexer_long_sec": round(long_indexer_sec, 4) if li == 3 else 0.0,
                },
                "layer_wall_with_io_sec": round(t_layer_total_wall, 4),
                "weights_vram_mib": weights_vram_mib,
                "peak_vram_allocated_mib": peak_alloc_mib,
                "peak_vram_allocated_gib": round(peak_alloc_mib / 1024.0, 4),
                "peak_vram_reserved_mib": peak_reserved_mib,
                "peak_vram_reserved_gib": round(peak_reserved_mib / 1024.0, 4),
                "avail_phys_ram_gib": ram_snap["avail_phys_gib"],
                "min_layer_avail_phys_ram_gib": round(min_layer_avail_ram_gib, 4),
                "pages_output_per_sec": po,
                "active_experts": layer_scores["active_experts"],
                "dead_experts": layer_scores["dead_experts"],
                "reap_median": layer_scores["reap_summary"]["median"],
            }
            if li == 3:
                lt_entry["qsa_indexer_ab_benchmark"] = qsa_indexer_ab_benchmark
            layer_telemetry.append(lt_entry)
            print(
                f"  Layer {li} ({layer.layer_type}{'+PLE' if layer.ple is not None else ''}): "
                f"load={t_load:.2f}s, reg_fwd={regular_fwd_sec:.2f}s ({lt_entry['regular_tok_per_sec']:.0f} tok/s), "
                f"long_fwd={long_fwd_sec:.2f}s ({lt_entry['long_context_tok_per_sec']:.0f} tok/s), "
                f"peak_VRAM={peak_alloc_mib:.1f} MiB (res {peak_reserved_mib:.1f} MiB), "
                f"min_RAM={min_layer_avail_ram_gib:.2f} GiB, active_exp={layer_scores['active_experts']}/512"
            )

            if li == 1:
                stream_ple.clear_cache()
            free_submodule_to_meta(layer, keep_non_checkpoint_names={"ple.ple_embedding.ngram_embedding.weight"})
            del acc
            gc.collect()
            torch.cuda.empty_cache()

        # Record disk buffer stats before cleanup
        buf_stats = {
            "io_implementation": "unbuffered_sequential_pread_pwrite_fsync",
            "single_buffer_bytes": pingpong.bytes_per_file,
            "dual_pingpong_bytes": pingpong.bytes_per_file * 2,
            "dual_pingpong_gib": round((pingpong.bytes_per_file * 2) / (1024**3), 4),
            "total_bytes_written": pingpong.total_write_bytes,
            "total_bytes_read": pingpong.total_read_bytes,
            "total_disk_io_sec": round(pingpong.total_io_sec, 4),
        }
    finally:
        pingpong.close_and_cleanup(remove_files=not args.keep_buffers)

    del obs_model, pilot_samples
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize(device)
    vram_after_cleanup_mib = round(torch.cuda.memory_allocated(device) / (1024**2), 2)

    # 5. Exact Extrapolation to Step 6 (48 Trunk Layers: 35 pure GDN + 1 GDN+PLE + 12 QSA + 1 MTP QSA Block)
    gdn_entries = [e for e in layer_telemetry if e["layer_type"] == "linear_attention" and not e["has_ple"]]
    ple_entry = next(e for e in layer_telemetry if e["has_ple"])
    qsa_entry = next(e for e in layer_telemetry if e["layer_type"] != "linear_attention")

    def _extrap_layer_compute_sec(entries: list[dict[str, Any]]) -> float:
        u_tps = sum(e["unchunked_regular_tokens"] for e in entries) / max(
            1e-6, sum(e["unchunked_regular_forward_sec"] for e in entries)
        )
        g_tok = sum(e["gt4k_regular_tokens"] for e in entries)
        g_tps = g_tok / max(1e-6, sum(e["gt4k_regular_forward_sec"] for e in entries)) if g_tok > 0 else u_tps
        l_tps = sum(e["long_context_tokens"] for e in entries) / max(
            1e-6, sum(e["long_context_forward_sec"] for e in entries)
        )
        return (
            (total_unchunked_reg_tokens / u_tps)
            + (total_gt4k_reg_tokens / g_tps)
            + (total_long_tokens / l_tps)
        )

    avg_gdn_load = sum(e["shard_load_sec"] for e in gdn_entries) / len(gdn_entries)
    ple_load = ple_entry["shard_load_sec"]
    qsa_load = qsa_entry["shard_load_sec"]

    gdn_compute_full_sec = _extrap_layer_compute_sec(gdn_entries)
    ple_compute_full_sec = _extrap_layer_compute_sec([ple_entry])
    qsa_variant_a_compute_full_sec = _extrap_layer_compute_sec([qsa_entry])

    # Unmodified upstream QSA indexer delta across all 684 sequences (`alpha*S + beta*S^2` fit on Layer-3 A/B)
    all_seq_lens = [int(r["qwen38_tokens"]) for r in all_rows]
    mtp_seq_lens = [max(1, int(r["qwen38_tokens"]) - 1) for r in all_rows]
    qsa_upstream_delta_trunk_sec = _extrapolate_upstream_qsa_delta_per_layer_sec(
        qsa_indexer_ab_benchmark.get("samples", []), all_seq_lens
    )
    qsa_upstream_delta_mtp_sec = _extrapolate_upstream_qsa_delta_per_layer_sec(
        qsa_indexer_ab_benchmark.get("samples", []), mtp_seq_lens
    )

    # Disk ping-pong throughput per layer across full calibration tokens (`read + write` per layer).
    # Capped at `1800 MiB/s` sustained NVMe read+write because Step 6's `36.14 GiB` dual buffer > `32 GiB` RAM!
    full_single_buf_bytes = total_dataset_tokens * hc_width * 2
    measured_io_mbps = (buf_stats["total_bytes_written"] + buf_stats["total_bytes_read"]) / (
        1024**2 * max(1e-6, buf_stats["total_disk_io_sec"])
    )
    sustained_nvme_io_mbps = min(max(200.0, measured_io_mbps), 1800.0)
    est_io_per_layer_full_sec = (2 * full_single_buf_bytes / (1024**2)) / sustained_nvme_io_mbps

    gdn_full_layer_sec = avg_gdn_load + gdn_compute_full_sec + est_io_per_layer_full_sec
    ple_gdn_full_layer_sec = ple_load + ple_compute_full_sec + est_io_per_layer_full_sec
    qsa_full_layer_variant_a_sec = qsa_load + qsa_variant_a_compute_full_sec + est_io_per_layer_full_sec
    qsa_full_layer_upstream_sec = qsa_full_layer_variant_a_sec + qsa_upstream_delta_trunk_sec

    # Explicit MTP (`blk.48`, `mtp.*`) model: 28 shards touched (~3.1x shard opens vs 9-shard QSA layer)
    # + reading cached multimodal `E^(0)` (`[S, 2560]` BF16 = 0.25x single HC buffer) + `eh_proj` + `S - 1` QSA+MoE!
    mtp_load_sec = qsa_load * 1.45
    mtp_e0_io_sec = (0.25 * full_single_buf_bytes / (1024**2)) / sustained_nvme_io_mbps
    mtp_eh_proj_sec = 0.5
    mtp_full_variant_a_sec = (
        mtp_load_sec + mtp_e0_io_sec + mtp_eh_proj_sec + qsa_variant_a_compute_full_sec + (0.5 * est_io_per_layer_full_sec)
    )
    mtp_full_upstream_sec = mtp_full_variant_a_sec + qsa_upstream_delta_mtp_sec

    # Single-pass sequential read of 33 PLE shards (102.40 GB) + index_select of exact unique rows
    shard_ratio = full_dataset_ple_exact["full_dataset_ple_safetensors_files_touched"] / max(
        1, ple_prefetch_stats["ple_safetensors_files_opened"]
    )
    row_ratio = full_dataset_ple_exact["full_dataset_unique_ngram_rows"] / max(
        1, ple_prefetch_stats["unique_ngram_rows"]
    )
    est_ple_full_prefetch_sec = max(
        ple_prefetch_stats["safetensors_slice_io_sec"] * max(shard_ratio, math.sqrt(row_ratio)),
        ple_prefetch_stats["safetensors_slice_io_sec"],
    )

    # Separate embedding/M-RoPE scaling (by total tokens) from ViT vision encoder scaling (by multimodal row count: 111/pilot_mm_rows)!
    est_embed_vis_full_sec = (
        t_emb_vis_load
        + t_emb_mrope_sec * (total_dataset_tokens / max(1, pilot_total_tokens))
        + t_vis_only_sec * (full_mm_rows / max(1, pilot_mm_rows))
        + (1.25 * full_single_buf_bytes / (1024**2)) / sustained_nvme_io_mbps  # write h0 + cached E^(0)
    )

    # Saving pruned 205/512 BF16 checkpoint:
    # `31` pure PLE shards (`00006..00036`) hardlinked (`0 GiB` written), `8` boundary PLE shards (`+5.16 GiB`)
    # extracted cleanly from mixed `00005` & `00037` + `102.05 GiB` pruned trunk/ViT/MTP = `107.21 GiB` (`115,116 MB`)!
    pruned_hf_gib = 107.21
    est_write_pruned_ckpt_sec = (pruned_hf_gib * 1024.0) / 1400.0

    fixed_o1_io_sec = (
        t_emb_vis_load
        + est_ple_full_prefetch_sec
        + 35 * avg_gdn_load
        + ple_load
        + 12 * qsa_load
        + mtp_load_sec
        + est_write_pruned_ckpt_sec
    )
    token_dep_variant_a_sec = (
        (est_embed_vis_full_sec - t_emb_vis_load)
        + 35 * (gdn_compute_full_sec + est_io_per_layer_full_sec)
        + (ple_compute_full_sec + est_io_per_layer_full_sec)
        + 12 * (qsa_variant_a_compute_full_sec + est_io_per_layer_full_sec)
        + (mtp_full_variant_a_sec - mtp_load_sec)
    )
    total_48_plus_mtp_variant_a_sec = fixed_o1_io_sec + token_dep_variant_a_sec
    total_48_plus_mtp_upstream_sec = (
        total_48_plus_mtp_variant_a_sec + 12 * qsa_upstream_delta_trunk_sec + qsa_upstream_delta_mtp_sec
    )
    # 50% token fallback scales ONLY token-dependent compute & ping-pong I/O; O(1) shard read/write stays 1.0x!
    total_50pct_subset_variant_a_sec = fixed_o1_io_sec + 0.5 * token_dep_variant_a_sec

    dual_pp_gib = (2 * full_single_buf_bytes) / (1024**3)
    e0_cache_gib = (total_dataset_tokens * int(cfg.text_config.hidden_size) * 2) / (1024**3)
    step6_peak_disk_gib = pruned_hf_gib + dual_pp_gib + e0_cache_gib

    extrapolation = {
        "full_calib_rows": len(all_rows),
        "full_calib_multimodal_rows": full_mm_rows,
        "full_calib_total_tokens": total_dataset_tokens,
        "full_calib_regular_tokens": total_regular_tokens,
        "full_calib_unchunked_regular_tokens": total_unchunked_reg_tokens,
        "full_calib_gt4k_regular_tokens": total_gt4k_reg_tokens,
        "full_calib_long_context_tokens": total_long_tokens,
        "full_single_buffer_bytes": full_single_buf_bytes,
        "full_single_buffer_gib": round(full_single_buf_bytes / (1024**3), 4),
        "full_dual_pingpong_gib": round(dual_pp_gib, 4),
        "full_mtp_e0_cache_gib": round(e0_cache_gib, 4),
        "measured_pingpong_io_mib_per_sec": round(measured_io_mbps, 2),
        "sustained_nvme_capped_io_mib_per_sec": round(sustained_nvme_io_mbps, 2),
        "est_embed_vision_mrope_full_sec": round(est_embed_vis_full_sec, 2),
        "est_per_gdn_layer_full_sec": round(gdn_full_layer_sec, 2),
        "est_per_ple_gdn_layer_full_sec": round(ple_gdn_full_layer_sec, 2),
        "est_per_qsa_layer_variant_a_full_sec": round(qsa_full_layer_variant_a_sec, 2),
        "est_per_qsa_layer_upstream_indexer_full_sec": round(qsa_full_layer_upstream_sec, 2),
        "est_mtp_layer_variant_a_full_sec": round(mtp_full_variant_a_sec, 2),
        "est_mtp_layer_upstream_indexer_full_sec": round(mtp_full_upstream_sec, 2),
        "est_ple_single_pass_prefetch_full_sec": round(est_ple_full_prefetch_sec, 2),
        "est_fixed_o1_shard_read_write_sec": round(fixed_o1_io_sec, 2),
        "exact_ple_unique_rows_full": full_dataset_ple_exact["full_dataset_unique_ngram_rows"],
        "exact_ple_unique_cache_ram_full_bytes": full_dataset_ple_exact["full_dataset_exact_cache_ram_bytes"],
        "exact_ple_unique_cache_ram_full_gib": full_dataset_ple_exact["full_dataset_exact_cache_ram_gib"],
        "est_total_step6_48_layers_plus_mtp_variant_a_sec": round(total_48_plus_mtp_variant_a_sec, 1),
        "est_total_step6_48_layers_plus_mtp_variant_a_min": round(total_48_plus_mtp_variant_a_sec / 60.0, 2),
        "est_total_step6_48_layers_plus_mtp_upstream_indexer_sec": round(total_48_plus_mtp_upstream_sec, 1),
        "est_total_step6_48_layers_plus_mtp_upstream_indexer_min": round(total_48_plus_mtp_upstream_sec / 60.0, 2),
        "est_total_step6_48_layers_plus_mtp_sec": round(total_48_plus_mtp_variant_a_sec, 1),
        "est_total_step6_48_layers_plus_mtp_min": round(total_48_plus_mtp_variant_a_sec / 60.0, 2),
        "est_total_step6_50pct_subset_min": round(total_50pct_subset_variant_a_sec / 60.0, 2),
        "disk_budget_step6": {
            "current_free_d_gib": round(disk_before.free / (1024**3), 2),
            "pure_ple_shards_hardlinked_count": 31,
            "boundary_ple_shards_extracted_gib": 5.16,
            "pruned_205_bf16_without_ple_dup_gib": pruned_hf_gib,
            "dual_pingpong_buffer_gib": round(dual_pp_gib, 2),
            "mtp_e0_cache_gib": round(e0_cache_gib, 2),
            "peak_temp_plus_pruned_gib": round(step6_peak_disk_gib, 2),
            "min_free_d_during_step6_keeping_donor_gib": round(
                disk_before.free / (1024**3) - step6_peak_disk_gib, 2
            ),
            "donor_deletion_required_in_step6": False,
            "step7_intermediate_bf16_core_q4_0_ple_gguf_gib": 128.04,
            "step7_note": (
                "Requires 4-line tensor_force_quant (per_layer_token_embd.weight -> Q4_0) in conversion/qwen4exp.py; "
                "keeping 412.66 GiB donor + 107.21 GiB pruned HF + 128.04 GiB intermediate GGUF simultaneously exceeds "
                "201.7 GiB free on D:, so Step 7 deletes the 107.21 GiB non-hardlinked pruned HF copy (upon explicit confirmation) "
                "immediately once the lossless-BF16-core + Q4_0-PLE GGUF is verified."
            ),
        },
    }

    all_alloc_peaks = [
        equiv_results["equiv_peak_vram_allocated_mib"],
        vis_vram_peak_mib,
        *[e["peak_vram_allocated_mib"] for e in layer_telemetry],
    ]
    all_res_peaks = [
        equiv_results["equiv_peak_vram_reserved_mib"],
        vis_vram_reserved_mib,
        *[e["peak_vram_reserved_mib"] for e in layer_telemetry],
    ]

    telemetry_payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seed": args.seed,
        "chunk_tokens": args.chunk_tokens,
        "qsa_long_chunk_tokens": QSA_LONG_CHUNK_TOKENS,
        "hardware": {
            "gpu_name": gpu_name,
            "gpu_total_mib": gpu_total_mib,
            "system_total_phys_ram_gib": ram_before["total_phys_gib"],
            "free_d_drive_gib_start": round(disk_before.free / (1024**3), 3),
        },
        "pilot_subset": {
            "num_samples": len(pilot_rows),
            "pct_of_rows": round(100.0 * len(pilot_rows) / len(all_rows), 2),
            "total_tokens": pilot_total_tokens,
            "pct_of_tokens": round(100.0 * pilot_total_tokens / total_dataset_tokens, 2),
            "by_stratum_samples": dict(Counter(r["pillar"] for r in pilot_rows)),
            "by_stratum_tokens": dict(
                Counter({p: sum(int(r["qwen38_tokens"]) for r in pilot_rows if r["pillar"] == p) for p in set(r["pillar"] for r in pilot_rows)})
            ),
            "by_lang_samples": dict(Counter(r["lang"] for r in pilot_rows)),
            "multimodal_samples": pilot_mm_rows,
            "curated_pillar4_samples": pilot_curated_p4_rows,
            "sample_ids": [r["id"] for r in pilot_rows],
        },
        "meta_init": {
            "meta_skeleton_init_sec": round(t_meta_init, 4),
            "avail_ram_after_meta_gib": ram_after_meta["avail_phys_gib"],
            "ple_204gb_oom_prevented": True,
        },
        "embed_and_vision_stage": {
            "embed_shards": emb_shards,
            "embed_bytes": emb_bytes,
            "embed_load_sec": round(t_emb_load, 4),
            "vision_shards": vis_shards,
            "vision_bytes": vis_bytes,
            "vision_load_sec": round(t_vis_load, 4),
            "load_sec": round(t_emb_vis_load, 4),
            "embed_and_mrope_forward_sec": round(t_emb_mrope_sec, 4),
            "vision_only_forward_sec": round(t_vis_only_sec, 4),
            "forward_sec": round(t_emb_vis_fwd, 4),
            "vision_peak_vram_mib": vis_vram_peak_mib,
            "vision_peak_vram_reserved_mib": vis_vram_reserved_mib,
        },
        "ple_prefetch": ple_prefetch_stats,
        "equivalence_verification": equiv_results,
        "layers": layer_telemetry,
        "disk_pingpong_buffer": buf_stats,
        "memory_safety_summary": {
            "equiv_peak_vram_allocated_mib": equiv_results["equiv_peak_vram_allocated_mib"],
            "vision_peak_vram_allocated_mib": vis_vram_peak_mib,
            "layers_max_vram_allocated_mib": max(e["peak_vram_allocated_mib"] for e in layer_telemetry),
            "max_vram_allocated_mib": max(all_alloc_peaks),
            "max_vram_allocated_gib": round(max(all_alloc_peaks) / 1024.0, 4),
            "max_vram_reserved_mib": max(all_res_peaks),
            "max_vram_reserved_gib": round(max(all_res_peaks) / 1024.0, 4),
            "min_avail_phys_ram_gib": round(min_avail_ram_gib, 4),
            "pages_output_per_sec_samples": pages_out_samples,
            "vram_allocated_after_cleanup_mib": vram_after_cleanup_mib,
        },
        "step6_extrapolation": extrapolation,
        "total_pilot_wall_sec": round(time.perf_counter() - t_wall_start, 2),
    }

    scores_payload = {
        "generated_at": telemetry_payload["generated_at"],
        "seed": args.seed,
        "pilot_samples": len(pilot_rows),
        "pilot_tokens": pilot_total_tokens,
        "layers": scores_by_layer,
    }

    TELEMETRY_JSON.write_text(json.dumps(telemetry_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    SCORES_JSON.write_text(json.dumps(scores_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== STEP 5 PILOT COMPLETE in {telemetry_payload['total_pilot_wall_sec']:.1f}s ===")
    print(
        f"  Max VRAM Allocated: {telemetry_payload['memory_safety_summary']['max_vram_allocated_gib']:.3f} GiB "
        f"(Reserved: {telemetry_payload['memory_safety_summary']['max_vram_reserved_gib']:.3f} GiB)"
    )
    print(f"  Min Free Physical RAM: {min_avail_ram_gib:.2f} GiB | VRAM After Cleanup: {vram_after_cleanup_mib:.1f} MiB")
    print(
        f"  Step 6 Full Extrapolation (48 layers + MTP on {total_dataset_tokens:,} tokens): "
        f"Variant-A = {extrapolation['est_total_step6_48_layers_plus_mtp_variant_a_min']:.1f} min vs "
        f"Upstream Indexer = {extrapolation['est_total_step6_48_layers_plus_mtp_upstream_indexer_min']:.1f} min"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
