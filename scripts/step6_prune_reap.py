#!/usr/bin/env python3
"""Step 6: Full-Model Streaming REAP Pruning (512 -> 205), Inline GPU imatrix, and Atomic Safetensors Export.

Implements `research/step5_7_tz.md` (§2) on Lenovo Legion Pro 7 (RTX 4080 Laptop 12 GB VRAM, 32 GB RAM):
1. Stage 0 (CPU/Disk, resumable):
   - Verifies frozen Step 4 SHA-256 (`PremiumWebStudio-Calib.jsonl`).
   - Copies metadata (`config.json` with `text_config.num_experts = keep_k`, tokenizers, preprocessors).
   - Hardlinks 31 pure PLE shards (`0 B` extra disk) + writes `model-ple-boundary.safetensors` (`13` tensors,
     preserving exact `torch.int64` hash constants) and `model-root-visual.safetensors` (`338` tensors).
2. Stage A (Embed + Vision + M-RoPE, resumable):
   - Streams 684 calibration rows (`947,424` tokens, decoding `111` PNGs 1 sample at a time) through
     `embed_tokens` + `model.visual` + `rotary_emb`, writing unbuffered `e0_buf.bin`, `rotary_cos.bin`,
     `rotary_sin.bin`, `samples_meta.pt`, and `hc_buf_0.bin` (`H^(0)`).
3. Stage B (Layers `0..47`, atomic per-layer resume + graceful `--max-minutes` & `STOP` sentinel):
   - Runs exact hybrid streaming forward (`GDN chunk=4096`, `QSA long_chunk=512`, `fast_exact_a` QSA indexer,
     pre-indexed `StreamingPLENGramEmbedding` on `layer_1` with `pos.clamp_max` guard).
   - Accumulates FP64 REAP metrics (`Workhorse Floor`: `Top-64` stratum-balanced `WSUM` union outlier-guarded
     REAP `S_{l,j}` with `min_count_floor=5`, `stable=True`, ascending `keep_indices`, pure `<|image_pad|>`
     and `vision_cond_specialist_top50_retained_in_k205` diagnostics) AND inline GPU `imatrix` statistics.
   - Slices `[512 -> 205]` along `dim=0`, writes `model-layer-{li:02d}.safetensors` atomically (`tmp -> fsync -> replace`),
     saves `_work/imatrix/layer_{li:02d}.pt` and `research/step6_raw/scores/layer_{li:02d}.json`, flushes `out_slot`,
     and updates `_work/checkpoint.json` atomically. NEVER deletes `_work/*.bin` on pause/interrupt/error.
4. Stage C (Trunk Output Head `hyper_connection_mixer` + `output.weight` imatrix, resumable):
   - Materializes only `model.language_model.hyper_connection_mixer` (`~26 MiB`) over `H^(47)` (`hc_buf_0.bin`).
5. Stage D (`mtp.layers.0` / `blk.48` causal `S - 1` pairs, resumable):
   - Runs `S - 1` causal pairs (`k = 1..S-1`, strictly skipping unpaired `k = 0`) from `E^(0)[:, 1:, :]` and
     pre-mixer `H^(47)[:, :-1, :]`, scores & prunes `mtp.layers.0.mlp` (`512 -> 205`), records `blk.48.*`
     imatrix (including `nextn.eh_proj` and `nextn.hc_head_{down,up}`), and writes `model-mtp.safetensors`.
6. Stage E (Finalize `imatrix_step6.gguf` + `model.safetensors.index.json` `1,658`-tensor bijection gate).
"""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import math
import os
import shutil
import signal
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gguf
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from safetensors import safe_open
from safetensors.torch import save_file
from transformers import AutoConfig, AutoProcessor, AutoTokenizer, DynamicCache
from transformers.models.qwen4_exp.configuration_qwen4_exp import (
    Qwen4ExpConfig,
    Qwen4ExpTextConfig,
    Qwen4ExpVisionConfig,
)
from transformers.models.qwen4_exp.modeling_qwen4_exp import (
    Qwen4ExpModel,
    Qwen4ExpTextDecoderLayer,
    Qwen4ExpTextGatedResidual,
    Qwen4ExpTextRMSNorm,
    Qwen4ExpTextRotaryEmbedding,
    Qwen4ExpVisionRotaryEmbedding,
)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from step5_pilot_observer import (  # noqa: E402
    DEFAULT_CHUNK_TOKENS,
    PLAN_TARGET_STRATUM_SHARES,
    QSA_LONG_CHUNK_TOKENS,
    PreparedSample,
    QSAIndexerWrapper,
    SafetensorsIndex,
    StreamingPLENGramEmbedding,
    compute_position_embeddings_for_sample,
    free_submodule_to_meta,
    get_windows_ram_telemetry,
    materialize_submodule,
    query_nvidia_smi_apps,
    sample_pages_output_per_sec,
)

EXPECTED_CALIB_SHA256 = "6f14f3470ab0b7797fb2d501a0bbd1abb46f7b42e5dcb13c626caa709ccdb16e"
DEFAULT_DONOR_DIR = ROOT / "models" / "Qwen3.8-Flash-Next"
DEFAULT_OUT_DIR = ROOT / "models" / "pruned_safetensors"
DEFAULT_CALIB_PATH = ROOT / "data" / "calib" / "PremiumWebStudio-Calib.jsonl"
DEFAULT_IMATRIX_OUT = ROOT / "data" / "calib" / "imatrix_step6.gguf"
DEFAULT_TELEMETRY_DIR = ROOT / "research" / "step6_raw"

METADATA_FILES_TO_COPY = (
    "tokenizer.json",
    "tokenizer_config.json",
    "preprocessor_config.json",
    "video_preprocessor_config.json",
    "generation_config.json",
    "chat_template.jinja",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "added_tokens.json",
    "LICENSE",
    "README.md",
)


# ---------------------------------------------------------------------------
# Graceful Interrupt & Sentinel Handling
# ---------------------------------------------------------------------------


class GracefulPauseRequested(Exception):
    """Raised when `SIGINT` or `_work/STOP` requests an immediate safe pause."""


class StopController:
    def __init__(self, stop_file: Path, max_minutes: float = 0.0):
        self.stop_file = Path(stop_file)
        self.max_minutes = float(max_minutes)
        self.t_start = time.perf_counter()
        self.sigint_received = False
        self._prev_handler = signal.getsignal(signal.SIGINT)

    def install(self) -> None:
        def _handler(signum: int, frame: Any) -> None:
            self.sigint_received = True
            print(
                "\n[PAUSE] SIGINT received — stopping current sample cleanly and preserving _work buffers...",
                flush=True,
            )

        signal.signal(signal.SIGINT, _handler)

    def restore(self) -> None:
        try:
            signal.signal(signal.SIGINT, self._prev_handler)
        except Exception:
            pass

    def elapsed_minutes(self) -> float:
        return (time.perf_counter() - self.t_start) / 60.0

    def check_immediate_stop(self) -> None:
        if self.sigint_received:
            raise GracefulPauseRequested("SIGINT (Ctrl+C) received")
        if self.stop_file.exists():
            raise GracefulPauseRequested(f"STOP sentinel detected at {self.stop_file}")

    def should_pause_between_stages(self) -> str | None:
        if self.sigint_received:
            return "SIGINT (Ctrl+C)"
        if self.stop_file.exists():
            return f"STOP sentinel ({self.stop_file})"
        if self.max_minutes > 0.0 and self.elapsed_minutes() >= self.max_minutes:
            return f"--max-minutes {self.max_minutes:.1f} reached ({self.elapsed_minutes():.2f} min elapsed)"
        return None


# ---------------------------------------------------------------------------
# Atomic File & JSON Helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_save_safetensors(tensors: dict[str, torch.Tensor], out_path: Path, metadata: dict[str, str] | None = None) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    save_file(tensors, str(tmp_path), metadata=metadata or {"format": "pt"})
    with open(tmp_path, "r+b") as fh:
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, out_path)
    return int(out_path.stat().st_size)


def atomic_torch_save(obj: Any, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".tmp")
    torch.save(obj, str(tmp_path))
    with open(tmp_path, "r+b") as fh:
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, out_path)


# ---------------------------------------------------------------------------
# Resumable Unbuffered Sequential Binary Stores (`0 B` OS mmap Working Set)
# ---------------------------------------------------------------------------


class ResumableFlatSequenceStore:
    """Unbuffered sequential BF16 store `[total_tokens, width]` supporting crash-safe `r+b` reopen."""

    def __init__(self, path: Path, seq_lens: list[int], width: int, reopen_existing: bool):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.seq_lens = list(seq_lens)
        self.width = int(width)
        self.total_tokens = int(sum(seq_lens))
        self.bytes_total = self.total_tokens * self.width * 2
        self.offsets: list[tuple[int, int]] = []
        cur = 0
        for sl in self.seq_lens:
            self.offsets.append((cur, cur + sl))
            cur += sl

        if reopen_existing:
            if not self.path.exists():
                raise FileNotFoundError(f"Resume error: missing buffer {self.path}")
            actual = self.path.stat().st_size
            if actual != self.bytes_total:
                raise RuntimeError(
                    f"Resume error: {self.path} size {actual} != expected {self.bytes_total}"
                )
            self._fh = open(self.path, "r+b", buffering=0)
        else:
            self._fh = open(self.path, "w+b", buffering=0)
            if self.bytes_total > 0:
                self._fh.seek(self.bytes_total - 1)
                self._fh.write(b"\x00")
                self._fh.flush()

    def write_sample(self, sample_idx: int, tensor_bf16_cpu: torch.Tensor) -> None:
        assert tensor_bf16_cpu.dtype == torch.bfloat16 and tensor_bf16_cpu.device.type == "cpu"
        st, ed = self.offsets[sample_idx]
        assert tensor_bf16_cpu.numel() == (ed - st) * self.width
        byte_offset = st * self.width * 2
        u8 = tensor_bf16_cpu.reshape(-1).contiguous().view(torch.uint8).numpy()
        mv = memoryview(u8)
        self._fh.seek(byte_offset)
        written = 0
        total = len(mv)
        while written < total:
            n = self._fh.write(mv[written:])
            if not n:
                raise IOError(f"Short write on {self.path} at {byte_offset + written}")
            written += n

    def read_sample(self, sample_idx: int) -> torch.Tensor:
        st, ed = self.offsets[sample_idx]
        seq_len = ed - st
        byte_offset = st * self.width * 2
        byte_len = seq_len * self.width * 2
        out_u8 = torch.empty((byte_len,), dtype=torch.uint8, device="cpu")
        mv = memoryview(out_u8.numpy())
        self._fh.seek(byte_offset)
        read_n = 0
        while read_n < byte_len:
            n = self._fh.readinto(mv[read_n:])
            if not n:
                raise EOFError(f"Unexpected EOF on {self.path} at {byte_offset + read_n}/{byte_len}")
            read_n += n
        return out_u8.view(torch.bfloat16).view(1, seq_len, self.width)

    def flush(self) -> None:
        if self._fh is not None:
            self._fh.flush()
            os.fsync(self._fh.fileno())

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.flush()
            except OSError:
                pass
            self._fh.close()
            self._fh = None


class ResumablePingPong:
    """Two-slot unbuffered BF16 ping-pong (`hc_buf_0.bin`, `hc_buf_1.bin`) that NEVER deletes on pause."""

    def __init__(self, work_dir: Path, seq_lens: list[int], hc_width: int, reopen_slot0: bool):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        p0 = self.work_dir / "hc_buf_0.bin"
        p1 = self.work_dir / "hc_buf_1.bin"
        self.slots = [
            ResumableFlatSequenceStore(p0, seq_lens, hc_width, reopen_existing=reopen_slot0),
            ResumableFlatSequenceStore(
                p1, seq_lens, hc_width, reopen_existing=(reopen_slot0 and p1.exists() and p1.stat().st_size == sum(seq_lens) * hc_width * 2)
            ),
        ]

    def write_sample(self, slot: int, sample_idx: int, tensor_bf16_cpu: torch.Tensor) -> None:
        self.slots[slot].write_sample(sample_idx, tensor_bf16_cpu)

    def read_sample(self, slot: int, sample_idx: int) -> torch.Tensor:
        return self.slots[slot].read_sample(sample_idx)

    def flush_slot(self, slot: int) -> None:
        self.slots[slot].flush()

    def close(self) -> None:
        for s in self.slots:
            s.close()


# ---------------------------------------------------------------------------
# Safe Streaming PLE Subclass (`pos.clamp_max(numel - 1)` guard per TZ §2.1)
# ---------------------------------------------------------------------------


class SafeStreamingPLENGramEmbedding(StreamingPLENGramEmbedding):
    def forward(self, ngram_ids: torch.Tensor) -> torch.Tensor:
        ids_cpu = ngram_ids.to("cpu", dtype=torch.int64)
        if self._capture_only:
            self.captured_chunks.append(ids_cpu.reshape(-1))
            return torch.zeros((*ids_cpu.shape, self.embed_dim), dtype=self.out_dtype, device="cpu")

        if self.unique_ids is not None and self.cached_rows is not None:
            flat = ids_cpu.reshape(-1)
            numel = int(self.unique_ids.numel())
            if numel == 0:
                raise RuntimeError("PLE cache empty while evaluating non-empty ngram_ids")
            pos = torch.searchsorted(self.unique_ids, flat).clamp_max(numel - 1)
            if not torch.equal(self.unique_ids.index_select(0, pos), flat):
                raise RuntimeError("PLE cache miss: encountered ngram_id absent from pre-indexed set!")
            return self.cached_rows.index_select(0, pos).view(*ids_cpu.shape, self.embed_dim).to(self.out_dtype)

        return super().forward(ngram_ids)


# ---------------------------------------------------------------------------
# Inline GPU `imatrix` Accumulator (`+13 MiB` VRAM/layer, FP32 chunk -> FP64 sum)
# ---------------------------------------------------------------------------


def reorder_gdn_v_heads_activation(
    x_2d: torch.Tensor,
    num_k_heads: int,
    num_v_heads: int,
    head_v_dim: int,
) -> torch.Tensor:
    """Permute `[N, num_v_heads * head_v_dim]` to match `Qwen4ExpTextModel._reorder_v_heads(..., dim=1)` on `ssm_out`."""
    if num_k_heads <= 0 or num_v_heads <= 0 or num_k_heads == num_v_heads:
        return x_2d
    num_v_per_k = num_v_heads // num_k_heads
    return (
        x_2d.reshape(-1, num_k_heads, num_v_per_k, head_v_dim)
        .permute(0, 2, 1, 3)
        .reshape(-1, num_v_heads * head_v_dim)
    )


class LayerImatrixCollector:
    """Accumulates `in_sum2`, `in_sum`, and `counts` in GPU FP64 without 1/64-rate FP64 GEMMs."""

    def __init__(self, device: str):
        self.device = device
        self.sum2: dict[str, torch.Tensor] = {}
        self.sum1: dict[str, torch.Tensor] = {}
        self.counts: dict[str, torch.Tensor] = {}

    def record_2d(self, names: list[str] | tuple[str, ...], x: torch.Tensor) -> None:
        flat = x.detach().reshape(-1, x.shape[-1])
        n_tok = int(flat.shape[0])
        if n_tok == 0:
            return
        xf = flat.to(torch.float32)
        s1 = xf.sum(dim=0).to(torch.float64)
        s2 = (xf * xf).sum(dim=0).to(torch.float64)
        ne0 = int(xf.shape[1])
        first_name = names[0]
        if first_name not in self.sum2:
            self.sum2[first_name] = torch.zeros((1, ne0), dtype=torch.float64, device=self.device)
            self.sum1[first_name] = torch.zeros((1, ne0), dtype=torch.float64, device=self.device)
            self.counts[first_name] = torch.zeros((1, 1), dtype=torch.float64, device=self.device)
        self.sum2[first_name][0] += s2
        self.sum1[first_name][0] += s1
        self.counts[first_name][0, 0] += float(n_tok)
        for alias in names[1:]:
            if alias not in self.sum2:
                # Share reference when identical input feeds multiple GGUF tensors (cloned on CPU export)
                self.sum2[alias] = self.sum2[first_name]
                self.sum1[alias] = self.sum1[first_name]
                self.counts[alias] = self.counts[first_name]

    def ensure_3d(self, name: str, n_experts: int, ne0: int) -> None:
        if name not in self.sum2:
            self.sum2[name] = torch.zeros((n_experts, ne0), dtype=torch.float64, device=self.device)
            self.sum1[name] = torch.zeros((n_experts, ne0), dtype=torch.float64, device=self.device)
            self.counts[name] = torch.zeros((n_experts, 1), dtype=torch.float64, device=self.device)

    def record_expert_slice(self, names: tuple[str, ...], n_experts: int, expert_idx: int, x_2d: torch.Tensor) -> None:
        n_tok = int(x_2d.shape[0])
        if n_tok == 0:
            return
        ne0 = int(x_2d.shape[1])
        xf = x_2d.detach().to(torch.float32)
        s1 = xf.sum(dim=0).to(torch.float64)
        s2 = (xf * xf).sum(dim=0).to(torch.float64)
        first = names[0]
        self.ensure_3d(first, n_experts, ne0)
        self.sum2[first][expert_idx] += s2
        self.sum1[first][expert_idx] += s1
        self.counts[first][expert_idx, 0] += float(n_tok)
        for alias in names[1:]:
            if alias not in self.sum2:
                self.sum2[alias] = self.sum2[first]
                self.sum1[alias] = self.sum1[first]
                self.counts[alias] = self.counts[first]

    def record_mtp_eh_proj(self, name: str, e_norm: torch.Tensor, h_norm_4d: torch.Tensor) -> None:
        """Record `blk.{bid}.nextn.eh_proj.weight` (`[2560, 5120]`):
        In GGUF (`qwen4exp.cpp:641-644`), `e_norm` is repeated across `hc=4` streams and concatenated
        with `h_norm` `[1, S-1, 4, 2560]` along feature dim `0`, producing `4 * (S-1)` rows of `[e ; h_s]`."""
        hc = int(h_norm_4d.shape[2])
        d = int(e_norm.shape[-1])
        e_flat = e_norm.detach().reshape(-1, d).to(torch.float32)
        n_tok = int(e_flat.shape[0])
        if n_tok == 0:
            return
        e_s1 = (float(hc) * e_flat.sum(dim=0)).to(torch.float64)
        e_s2 = (float(hc) * (e_flat * e_flat).sum(dim=0)).to(torch.float64)

        h_flat = h_norm_4d.detach().reshape(-1, d).to(torch.float32)  # [n_tok * hc, d]
        h_s1 = h_flat.sum(dim=0).to(torch.float64)
        h_s2 = (h_flat * h_flat).sum(dim=0).to(torch.float64)

        cat_s1 = torch.cat([e_s1, h_s1], dim=0)
        cat_s2 = torch.cat([e_s2, h_s2], dim=0)
        ne0 = int(cat_s1.numel())
        if name not in self.sum2:
            self.sum2[name] = torch.zeros((1, ne0), dtype=torch.float64, device=self.device)
            self.sum1[name] = torch.zeros((1, ne0), dtype=torch.float64, device=self.device)
            self.counts[name] = torch.zeros((1, 1), dtype=torch.float64, device=self.device)
        self.sum2[name][0] += cat_s2
        self.sum1[name][0] += cat_s1
        self.counts[name][0, 0] += float(n_tok * hc)

    def export_cpu_float32(self, keep_indices: list[int] | None = None) -> dict[str, dict[str, torch.Tensor]]:
        out: dict[str, dict[str, torch.Tensor]] = {}
        keep_t = torch.tensor(keep_indices, dtype=torch.long, device=self.device) if keep_indices is not None else None
        for name in sorted(self.sum2.keys()):
            s2 = self.sum2[name]
            s1 = self.sum1[name]
            cnt = self.counts[name]
            if s2.shape[0] > 1 and keep_t is not None:
                s2 = s2.index_select(0, keep_t)
                s1 = s1.index_select(0, keep_t)
                cnt = cnt.index_select(0, keep_t)
            out[name] = {
                "in_sum2": s2.detach().to("cpu", dtype=torch.float32).contiguous().clone(),
                "in_sum": s1.detach().to("cpu", dtype=torch.float32).contiguous().clone(),
                "counts": cnt.detach().to("cpu", dtype=torch.float32).contiguous().clone(),
            }
        return out


# ---------------------------------------------------------------------------
# Step 6 REAP Accumulator (`Workhorse Floor` + Pure `<|image_pad|>` + `stable=True`)
# ---------------------------------------------------------------------------


class Step6REAPAccumulator:
    """Full-dataset FP64 REAP accumulator implementing Workhorse Floor (`RT-05`) and TZ §1.3.3/§2.3."""

    def __init__(self, num_experts: int, image_pad_token_id: int = 248056):
        self.num_experts = int(num_experts)
        self.image_pad_token_id = int(image_pad_token_id)
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

        # Pure `<|image_pad|>` (`id == 248056`) bucket separate from Pillar 3 HTML/CSS text tokens
        self.visual_patch_tokens: int = 0
        self.freq_visual_patch = torch.zeros(num_experts, dtype=torch.int64, device="cpu")
        self.weighted_ean_visual_patch = torch.zeros(num_experts, dtype=torch.float64, device="cpu")

        self.current_stratum: str = "unknown"
        self.current_subbucket: str | None = None
        self.current_lang: str = "en"

    def select_keep_indices_and_finalize(
        self,
        gate_weight_cpu: torch.Tensor,
        keep_k: int = 205,
        workhorse_floor_k: int = 64,
        min_count_floor: int = 5,
    ) -> dict[str, Any]:
        keep_k_eff = min(self.num_experts, keep_k)
        wf_k_eff = min(keep_k_eff, workhorse_floor_k if self.num_experts >= 205 else max(1, round(keep_k_eff * 64 / 205)))

        freq_raw_f64 = self.expert_frequency.clamp_min(1).to(torch.float64)
        reap_raw_f64 = torch.where(
            self.expert_frequency > 0,
            self.weighted_ean_sum / freq_raw_f64,
            torch.zeros_like(self.weighted_ean_sum),
        )
        # Outlier-guarded REAP (`max(count, 5)` denominator per TZ §2.3)
        freq_guarded_f64 = self.expert_frequency.clamp_min(max(1, min_count_floor)).to(torch.float64)
        reap_guarded_f64 = torch.where(
            self.expert_frequency > 0,
            self.weighted_ean_sum / freq_guarded_f64,
            torch.zeros_like(self.weighted_ean_sum),
        )

        # Stratum-balanced WSUM (`WSUM^bal_{l,j}`) across `PLAN_TARGET_STRATUM_SHARES`
        wsum_bal = torch.zeros(self.num_experts, dtype=torch.float64)
        for sk, tgt_share in PLAN_TARGET_STRATUM_SHARES.items():
            st_tok = self.tokens_by_stratum.get(sk, 0)
            if st_tok <= 0:
                continue
            obs_share = st_tok / max(1, self.total_tokens)
            mult = float(tgt_share) / max(1e-9, obs_share)
            wsum_bal += mult * self.weighted_ean_by_stratum[sk]
        if float(wsum_bal.sum().item()) <= 0.0:
            wsum_bal = self.weighted_ean_sum.clone()

        active_mask = self.expert_frequency > 0
        n_active = int(active_mask.sum().item())
        n_dead = int((~active_mask).sum().item())

        # Unconditional Top-64 Workhorse Floor (only among active experts)
        wsum_bal_masked = torch.where(active_mask, wsum_bal, torch.full_like(wsum_bal, -1.0))
        _, wf_order = torch.sort(wsum_bal_masked, descending=True, stable=True)
        workhorse_ids: list[int] = [
            int(idx) for idx in wf_order[:wf_k_eff].tolist() if bool(active_mask[idx].item())
        ]
        selected_set: set[int] = set(workhorse_ids)

        # Fill remaining slots up to `keep_k_eff` by outlier-guarded REAP `S_{l,j}` (`stable=True`)
        reap_masked = torch.where(active_mask, reap_guarded_f64, torch.full_like(reap_guarded_f64, -1.0))
        _, reap_order = torch.sort(reap_masked, descending=True, stable=True)
        for idx in reap_order.tolist():
            if len(selected_set) >= keep_k_eff:
                break
            if bool(active_mask[idx].item()) and int(idx) not in selected_set:
                selected_set.add(int(idx))

        # Dead-expert fallback ONLY if `active_experts < keep_k_eff`: rank dead experts by L2 norm of `mlp.gate.weight`
        gate_l2_fallback_used = 0
        if len(selected_set) < keep_k_eff:
            gate_norms = gate_weight_cpu.detach().to(torch.float64).norm(p=2, dim=-1)
            dead_norms = torch.where(~active_mask, gate_norms, torch.full_like(gate_norms, -1.0))
            _, dead_order = torch.sort(dead_norms, descending=True, stable=True)
            for idx in dead_order.tolist():
                if len(selected_set) >= keep_k_eff:
                    break
                if int(idx) not in selected_set:
                    selected_set.add(int(idx))
                    gate_l2_fallback_used += 1

        # Strictly ascending expert indices to preserve exact router `topk(10)` BF16 tie-break order!
        keep_indices = sorted(selected_set)
        assert len(keep_indices) == keep_k_eff

        # Compare against pure unguarded REAP Top-K
        _, pure_reap_order = torch.sort(reap_raw_f64, descending=True, stable=True)
        pure_reap_set = set(pure_reap_order[:keep_k_eff].tolist())
        rescued_by_workhorse_or_guard = sorted(selected_set - pure_reap_set)
        displaced_from_pure_reap = sorted(pure_reap_set - selected_set)
        jaccard_vs_pure_reap = len(selected_set & pure_reap_set) / max(1, len(selected_set | pure_reap_set))

        _, wsum_raw_order = torch.sort(self.weighted_ean_sum, descending=True, stable=True)
        top_wsum_set = set(wsum_raw_order[:keep_k_eff].tolist())
        reap_vs_wsum_jaccard = len(selected_set & top_wsum_set) / max(1, len(selected_set | top_wsum_set))

        top_m = 50 if self.num_experts >= 205 else max(1, round(self.num_experts * 50 / 512))
        min_spec_f = max(5, min(25, max(1, self.total_tokens // 4000)))

        def _bucket_retention(w_sum_vec: torch.Tensor, freq_vec: torch.Tensor, ref_set: set[int]) -> dict[str, Any]:
            _, raw_ord = torch.sort(w_sum_vec, descending=True, stable=True)
            raw_top_m = set(raw_ord[:top_m].tolist())
            elig = freq_vec >= min_spec_f
            if int(elig.sum().item()) >= max(5, top_m // 2):
                cond_vec = torch.where(elig, w_sum_vec / freq_vec.clamp_min(1).to(torch.float64), torch.full_like(w_sum_vec, -1.0))
            else:
                cond_vec = torch.where(freq_vec > 0, w_sum_vec / freq_vec.clamp_min(1).to(torch.float64), torch.full_like(w_sum_vec, -1.0))
            _, cond_ord = torch.sort(cond_vec, descending=True, stable=True)
            cond_top_m = set(cond_ord[:top_m].tolist())
            return {
                "raw_top50_retained_in_k205": len(raw_top_m & ref_set),
                "cond_specialist_top50_retained_in_k205": len(cond_top_m & ref_set),
                "eligible_specialists": int(elig.sum().item()),
            }

        all_bucket_keys = sorted(set(PLAN_TARGET_STRATUM_SHARES.keys()) | set(self.weighted_ean_by_stratum.keys()))
        per_stratum_retention = {
            sk: _bucket_retention(self.weighted_ean_by_stratum[sk], self.freq_by_stratum[sk], selected_set)
            for sk in all_bucket_keys
        }
        ru_ret = _bucket_retention(self.weighted_ean_by_lang["ru"], self.freq_by_lang["ru"], selected_set)
        vis_patch_ret = _bucket_retention(self.weighted_ean_visual_patch, self.freq_visual_patch, selected_set)

        reap_cond_f32 = reap_raw_f64.to(torch.float32)
        ean_mean_f32 = (self.ean_sum / freq_raw_f64).to(torch.float32)
        router_w_mean_f32 = (self.weighted_expert_frequency_sum / freq_raw_f64).to(torch.float32)
        max_signed_clean = torch.where(
            torch.isinf(self.max_activations_signed),
            torch.zeros_like(self.max_activations_signed),
            self.max_activations_signed,
        )
        sorted_reap_vals, sorted_reap_idx = torch.sort(reap_cond_f32, descending=True, stable=True)

        return {
            "total_tokens": int(self.total_tokens),
            "visual_image_pad_tokens": int(self.visual_patch_tokens),
            "num_experts": int(self.num_experts),
            "keep_k": int(keep_k_eff),
            "workhorse_floor_k": int(wf_k_eff),
            "min_count_floor": int(min_count_floor),
            "active_experts": n_active,
            "dead_experts": n_dead,
            "gate_l2_fallback_used": gate_l2_fallback_used,
            "nan_or_inf_count": int(
                torch.isnan(reap_guarded_f64).sum().item() + torch.isinf(reap_guarded_f64).sum().item()
            ),
            "selector_audit": {
                "jaccard_vs_pure_reap": round(jaccard_vs_pure_reap, 6),
                "rescued_ids": rescued_by_workhorse_or_guard,
                "displaced_ids": displaced_from_pure_reap,
                "workhorse_top64_retained": len(set(workhorse_ids) & selected_set),
            },
            "reap_summary": {
                "min": round(float(reap_cond_f32.min().item()), 6),
                "p10": round(float(torch.quantile(reap_cond_f32, 0.10).item()), 6),
                "median": round(float(reap_cond_f32.median().item()), 6),
                "mean": round(float(reap_cond_f32.mean().item()), 6),
                "p90": round(float(torch.quantile(reap_cond_f32, 0.90).item()), 6),
                "max": round(float(reap_cond_f32.max().item()), 6),
            },
            "retention_diagnostics_k205": {
                "ru_top50_retained_in_k205": ru_ret["raw_top50_retained_in_k205"],
                "ru_cond_specialist_top50_retained_in_k205": ru_ret["cond_specialist_top50_retained_in_k205"],
                "vision_top50_retained_in_k205": per_stratum_retention.get("pillar_3_style_canons_vision", {}).get(
                    "raw_top50_retained_in_k205", 0
                ),
                "vision_cond_specialist_top50_retained_in_k205": per_stratum_retention.get(
                    "pillar_3_style_canons_vision", {}
                ).get("cond_specialist_top50_retained_in_k205", 0),
                "visual_image_pad_tokens_retention": vis_patch_ret,
                "pillar4_top50_retained_in_k205": per_stratum_retention.get(
                    "pillar_4_art_direction_copywriting", {}
                ).get("raw_top50_retained_in_k205", 0),
                "pillar4_cond_specialist_top50_retained_in_k205": per_stratum_retention.get(
                    "pillar_4_art_direction_copywriting", {}
                ).get("cond_specialist_top50_retained_in_k205", 0),
                "craft_p4_top50_retained_in_k205": per_stratum_retention.get("craft_p4", {}).get(
                    "raw_top50_retained_in_k205", 0
                ),
                "craft_p4_cond_specialist_top50_retained_in_k205": per_stratum_retention.get("craft_p4", {}).get(
                    "cond_specialist_top50_retained_in_k205", 0
                ),
                "by_stratum_all": per_stratum_retention,
                "reap_vs_weighted_sum_k205_jaccard": round(reap_vs_wsum_jaccard, 6),
                "retained_share_of_total_weighted_ean": round(
                    float(
                        self.weighted_ean_sum[keep_indices].sum().item()
                        / max(1e-12, self.weighted_ean_sum.sum().item())
                    ),
                    6,
                ),
            },
            "top_15_experts_by_reap": [
                {
                    "expert_idx": int(idx),
                    "reap": round(float(val), 6),
                    "freq": int(self.expert_frequency[idx].item()),
                    "ean_mean": round(float(ean_mean_f32[idx].item()), 6),
                    "router_weight_mean": round(float(router_w_mean_f32[idx].item()), 6),
                    "max_act_abs": round(float(self.max_activations[idx].item()), 6),
                    "max_act_signed": round(float(max_signed_clean[idx].item()), 6),
                }
                for val, idx in zip(sorted_reap_vals[:15].tolist(), sorted_reap_idx[:15].tolist())
            ],
            "keep_indices_k205_sorted": keep_indices,
            "arrays": {
                "reap_raw": [round(float(x), 6) for x in reap_raw_f64.tolist()],
                "reap_guarded": [round(float(x), 6) for x in reap_guarded_f64.tolist()],
                "wsum_balanced": [round(float(x), 4) for x in wsum_bal.tolist()],
                "expert_frequency": [int(x) for x in self.expert_frequency.tolist()],
                "weighted_ean_sum": [round(float(x), 4) for x in self.weighted_ean_sum.tolist()],
                "freq_visual_image_pad": [int(x) for x in self.freq_visual_patch.tolist()],
                "weighted_ean_visual_image_pad": [round(float(x), 4) for x in self.weighted_ean_visual_patch.tolist()],
            },
        }


# ---------------------------------------------------------------------------
# Fused MoE Forward + REAP + Inline GPU `imatrix` Recording
# ---------------------------------------------------------------------------


@torch.no_grad()
def forward_moe_reap_and_imatrix(
    moe_block: nn.Module,
    hidden_states: torch.Tensor,
    token_ids_2d: torch.Tensor,
    bid: int,
    reap_acc: Step6REAPAccumulator,
    imat: LayerImatrixCollector,
) -> torch.Tensor:
    """Bit-identical to `Qwen4ExpTextSparseMoeBlock.forward`, recording REAP + all 8 FFN GGUF imatrix tensors."""
    batch_size, sequence_length, hidden_dim = hidden_states.shape
    hidden_states_reshaped = hidden_states.view(-1, hidden_dim)
    flat_token_ids = token_ids_2d.reshape(-1)
    n_tok = int(hidden_states_reshaped.shape[0])

    # Shared-input 2D FFN weights (`ffn_gate_inp`, `ffn_gate_shexp`, `ffn_up_shexp`, `ffn_gate_inp_shexp`)
    imat.record_2d(
        (
            f"blk.{bid}.ffn_gate_inp.weight",
            f"blk.{bid}.ffn_gate_shexp.weight",
            f"blk.{bid}.ffn_up_shexp.weight",
            f"blk.{bid}.ffn_gate_inp_shexp.weight",
        ),
        hidden_states_reshaped,
    )

    # Shared expert forward (unrolled identically to `Qwen4ExpTextMLP.forward` to capture `down_proj` input)
    sh_mlp = moe_block.shared_expert
    sh_inter = sh_mlp.act_fn(sh_mlp.gate_proj(hidden_states_reshaped)) * sh_mlp.up_proj(hidden_states_reshaped)
    imat.record_2d((f"blk.{bid}.ffn_down_shexp.weight",), sh_inter)
    shared_expert_output = sh_mlp.down_proj(sh_inter)
    del sh_inter

    _, top_k_weights, top_k_index = moe_block.gate(hidden_states_reshaped)

    experts = moe_block.experts
    num_experts = int(experts.num_experts)
    inter_dim = int(experts.intermediate_dim)
    gate_exps_name = f"blk.{bid}.ffn_gate_exps.weight"
    up_exps_name = f"blk.{bid}.ffn_up_exps.weight"
    down_exps_name = f"blk.{bid}.ffn_down_exps.weight"
    imat.ensure_3d(gate_exps_name, num_experts, hidden_dim)
    if up_exps_name not in imat.sum2:
        imat.sum2[up_exps_name] = imat.sum2[gate_exps_name]
        imat.sum1[up_exps_name] = imat.sum1[gate_exps_name]
        imat.counts[up_exps_name] = imat.counts[gate_exps_name]
    imat.ensure_3d(down_exps_name, num_experts, inter_dim)

    final_hidden_states = torch.zeros_like(hidden_states_reshaped)

    freq_dev = torch.zeros(num_experts, dtype=torch.int64, device=hidden_states.device)
    ean_dev = torch.zeros(num_experts, dtype=torch.float64, device=hidden_states.device)
    wean_dev = torch.zeros(num_experts, dtype=torch.float64, device=hidden_states.device)
    wfreq_dev = torch.zeros(num_experts, dtype=torch.float64, device=hidden_states.device)
    max_act_dev = torch.zeros(num_experts, dtype=torch.float32, device=hidden_states.device)
    max_signed_dev = torch.full((num_experts,), float("-inf"), dtype=torch.float32, device=hidden_states.device)

    has_vis_patches = bool((flat_token_ids == reap_acc.image_pad_token_id).any().item())
    vis_mask_dev = (flat_token_ids == reap_acc.image_pad_token_id) if has_vis_patches else None
    vis_freq_dev = torch.zeros(num_experts, dtype=torch.int64, device=hidden_states.device) if has_vis_patches else None
    vis_wean_dev = torch.zeros(num_experts, dtype=torch.float64, device=hidden_states.device) if has_vis_patches else None

    with torch.no_grad():
        expert_mask = F.one_hot(top_k_index, num_classes=num_experts).permute(2, 1, 0)
        expert_hit = torch.greater(expert_mask.sum(dim=(-1, -2)), 0).nonzero()

    for expert_idx_t in expert_hit:
        expert_idx = int(expert_idx_t[0].item())
        top_k_pos, token_idx = torch.where(expert_mask[expert_idx])
        current_state = hidden_states_reshaped[token_idx]

        # Record routed expert inputs for `ffn_gate_exps` & `ffn_up_exps`
        imat.record_expert_slice((gate_exps_name, up_exps_name), num_experts, expert_idx, current_state)

        gate, up = F.linear(current_state, experts.gate_up_proj[expert_idx]).chunk(2, dim=-1)
        act_hidden = experts.act_fn(gate) * up

        # Record routed expert intermediate activations for `ffn_down_exps`
        imat.record_expert_slice((down_exps_name,), num_experts, expert_idx, act_hidden)

        unweighted_out = F.linear(act_hidden, experts.down_proj[expert_idx])
        w = top_k_weights[token_idx, top_k_pos, None]
        weighted_out = unweighted_out * w
        final_hidden_states.index_add_(0, token_idx, weighted_out.to(final_hidden_states.dtype))

        norms_f32 = torch.linalg.vector_norm(unweighted_out.float(), ord=2, dim=-1)
        w_f64 = w.squeeze(-1).to(torch.float64)
        norms_f64 = norms_f32.to(torch.float64)
        wn_f64 = w_f64 * norms_f64

        freq_dev[expert_idx] += token_idx.numel()
        ean_dev[expert_idx] += norms_f64.sum()
        wean_dev[expert_idx] += wn_f64.sum()
        wfreq_dev[expert_idx] += w_f64.sum()
        cur_max_abs = unweighted_out.abs().max().float()
        cur_max_signed = unweighted_out.max().float()
        max_act_dev[expert_idx] = torch.maximum(max_act_dev[expert_idx], cur_max_abs)
        max_signed_dev[expert_idx] = torch.maximum(max_signed_dev[expert_idx], cur_max_signed)

        if has_vis_patches and vis_mask_dev is not None and vis_freq_dev is not None and vis_wean_dev is not None:
            is_vis = vis_mask_dev[token_idx]
            if bool(is_vis.any().item()):
                vis_freq_dev[expert_idx] += int(is_vis.sum().item())
                vis_wean_dev[expert_idx] += wn_f64[is_vis].sum()

    freq_cpu = freq_dev.cpu()
    wean_cpu = wean_dev.cpu()
    reap_acc.total_tokens += n_tok
    reap_acc.expert_frequency += freq_cpu
    reap_acc.ean_sum += ean_dev.cpu()
    reap_acc.weighted_ean_sum += wean_cpu
    reap_acc.weighted_expert_frequency_sum += wfreq_dev.cpu()
    reap_acc.max_activations = torch.maximum(reap_acc.max_activations, max_act_dev.cpu())
    reap_acc.max_activations_signed = torch.maximum(reap_acc.max_activations_signed, max_signed_dev.cpu())

    st = reap_acc.current_stratum
    reap_acc.tokens_by_stratum[st] += n_tok
    reap_acc.freq_by_stratum[st] += freq_cpu
    reap_acc.weighted_ean_by_stratum[st] += wean_cpu

    sb = reap_acc.current_subbucket
    if sb:
        reap_acc.tokens_by_stratum[sb] += n_tok
        reap_acc.freq_by_stratum[sb] += freq_cpu
        reap_acc.weighted_ean_by_stratum[sb] += wean_cpu

    lg = reap_acc.current_lang
    reap_acc.tokens_by_lang[lg] += n_tok
    reap_acc.freq_by_lang[lg] += freq_cpu
    reap_acc.weighted_ean_by_lang[lg] += wean_cpu

    if has_vis_patches and vis_mask_dev is not None and vis_freq_dev is not None and vis_wean_dev is not None:
        reap_acc.visual_patch_tokens += int(vis_mask_dev.sum().item())
        reap_acc.freq_visual_patch += vis_freq_dev.cpu()
        reap_acc.weighted_ean_visual_patch += vis_wean_dev.cpu()

    shared_expert_output = F.sigmoid(moe_block.shared_expert_gate(hidden_states_reshaped)) * shared_expert_output
    out = final_hidden_states + shared_expert_output
    return out.reshape(batch_size, sequence_length, hidden_dim)


# ---------------------------------------------------------------------------
# Single-Layer Forward with Hooks for All Non-MoE Quantizable GGUF Tensors
# ---------------------------------------------------------------------------


def attach_non_moe_imatrix_hooks(
    layer: Qwen4ExpTextDecoderLayer,
    text_cfg: Qwen4ExpTextConfig,
    bid: int,
    imat: LayerImatrixCollector,
) -> list[Any]:
    """Attach zero-copy forward pre-hooks for HC, PLE (`blk.1`), Linear GDN, and QSA `o_proj`."""
    handles: list[Any] = []
    num_k_heads = int(getattr(text_cfg, "linear_num_key_heads", 0) or 0)
    num_v_heads = int(getattr(text_cfg, "linear_num_value_heads", 0) or 0)
    head_v_dim = int(getattr(text_cfg, "linear_value_head_dim", 128) or 128)

    # 1. Hyper-connection mixers (`hc_attn_down_inject`, `hc_attn_up`, `hc_ffn_down_inject`, `hc_ffn_up`)
    handles.append(
        layer.attn_hyper_connection.input_mix_weight_down.register_forward_pre_hook(
            lambda _m, inp: imat.record_2d((f"blk.{bid}.hc_attn_down_inject.weight",), inp[0])
        )
    )
    handles.append(
        layer.attn_hyper_connection.input_mix_weight_up.register_forward_pre_hook(
            lambda _m, inp: imat.record_2d((f"blk.{bid}.hc_attn_up.weight",), inp[0])
        )
    )
    handles.append(
        layer.mlp_hyper_connection.input_mix_weight_down.register_forward_pre_hook(
            lambda _m, inp: imat.record_2d((f"blk.{bid}.hc_ffn_down_inject.weight",), inp[0])
        )
    )
    handles.append(
        layer.mlp_hyper_connection.input_mix_weight_up.register_forward_pre_hook(
            lambda _m, inp: imat.record_2d((f"blk.{bid}.hc_ffn_up.weight",), inp[0])
        )
    )

    # 2. Optional PLE (`blk.1.ple_key.weight` and `blk.1.ple_value.weight` share input)
    if layer.ple is not None:
        handles.append(
            layer.ple.key_proj.register_forward_pre_hook(
                lambda _m, inp: imat.record_2d((f"blk.{bid}.ple_key.weight", f"blk.{bid}.ple_value.weight"), inp[0])
            )
        )

    # 3. Attention (`linear_attention` vs `full_attention` QSA)
    if layer.layer_type == "linear_attention":
        handles.append(
            layer.linear_attn.out_proj.register_forward_pre_hook(
                lambda _m, inp: imat.record_2d(
                    (f"blk.{bid}.ssm_out.weight",),
                    reorder_gdn_v_heads_activation(
                        inp[0].detach().reshape(-1, inp[0].shape[-1]),
                        num_k_heads=num_k_heads,
                        num_v_heads=num_v_heads,
                        head_v_dim=head_v_dim,
                    ),
                )
            )
        )
    else:
        handles.append(
            layer.self_attn.o_proj.register_forward_pre_hook(
                lambda _m, inp: imat.record_2d((f"blk.{bid}.attn_output.weight",), inp[0])
            )
        )

    return handles


@torch.no_grad()
def forward_decoder_layer_step6(
    layer: Qwen4ExpTextDecoderLayer,
    text_cfg: Qwen4ExpTextConfig,
    bid: int,
    hidden_states_cpu: torch.Tensor,
    full_cos_cpu: torch.Tensor,
    full_sin_cpu: torch.Tensor,
    ple_input_ids_cpu: torch.Tensor,
    device: str,
    reap_acc: Step6REAPAccumulator,
    imat: LayerImatrixCollector,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    qsa_long_chunk_tokens: int = QSA_LONG_CHUNK_TOKENS,
) -> torch.Tensor:
    seq_len = int(hidden_states_cpu.shape[1])
    is_full_attn = layer.layer_type != "linear_attention"
    is_cuda = device.startswith("cuda")
    eff_chunk = qsa_long_chunk_tokens if (is_full_attn and seq_len > chunk_tokens) else chunk_tokens

    def _run_step(
        h_dev: torch.Tensor,
        cos_dev: torch.Tensor,
        sin_dev: torch.Tensor,
        attn_mask_dev: torch.Tensor | None,
        ple_ids_dev: torch.Tensor,
        cache: DynamicCache | None,
    ) -> torch.Tensor:
        if layer.ple is not None:
            h_dev = h_dev + layer.ple(h_dev, ple_ids_dev, cache, conv_mask=None)

        h_attn_in, hyper_input, injection_weights = layer.attn_hyper_connection(h_dev)
        if layer.layer_type == "linear_attention":
            imat.record_2d(
                (f"blk.{bid}.attn_qkv_gate.weight", f"blk.{bid}.ssm_beta_alpha.weight"),
                h_attn_in,
            )
            h_attn_out = layer.linear_attn(h_attn_in, cache_params=cache, attention_mask=None)
        else:
            # Record directly from `h_attn_in` so `indexer.{q,k}_proj` are captured even on `kv_len <= 2051` dense bypass!
            imat.record_2d(
                (
                    f"blk.{bid}.attn_q.weight",
                    f"blk.{bid}.attn_k.weight",
                    f"blk.{bid}.attn_v.weight",
                    f"blk.{bid}.indexer.q_proj.weight",
                    f"blk.{bid}.indexer.k_proj.weight",
                ),
                h_attn_in,
            )
            h_attn_out, _ = layer.self_attn(
                h_attn_in,
                (cos_dev, sin_dev),
                attention_mask=attn_mask_dev,
                past_key_values=cache,
            )

        injection = h_attn_out.unsqueeze(-2) * injection_weights.unsqueeze(-1)
        h_dev = hyper_input + injection.flatten(-2)

        h_mlp_in, hyper_input, injection_weights = layer.mlp_hyper_connection(h_dev)
        h_mlp_out = forward_moe_reap_and_imatrix(layer.mlp, h_mlp_in, ple_ids_dev, bid, reap_acc, imat)
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
# Safetensors Pruning & GGUF `imatrix` Writer
# ---------------------------------------------------------------------------


def load_tensors_from_donor(st_index: SafetensorsIndex, keys: list[str]) -> dict[str, torch.Tensor]:
    by_shard: dict[str, list[str]] = defaultdict(list)
    for k in keys:
        by_shard[st_index.weight_map[k]].append(k)
    loaded: dict[str, torch.Tensor] = {}
    for sf in sorted(by_shard):
        with safe_open(str(st_index.checkpoint_dir / sf), framework="pt", device="cpu") as f:
            for k in by_shard[sf]:
                loaded[k] = f.get_tensor(k)
    return loaded


def slice_expert_tensors_inplace(tensors: dict[str, torch.Tensor], keep_indices: list[int]) -> None:
    idx_t = torch.tensor(keep_indices, dtype=torch.long, device="cpu")
    for k in list(tensors.keys()):
        if k.endswith((".mlp.gate.weight", ".mlp.experts.gate_up_proj", ".mlp.experts.down_proj")):
            old_t = tensors.pop(k)
            tensors[k] = old_t.index_select(0, idx_t).contiguous()
            del old_t
    gc.collect()


def write_imatrix_gguf(
    imatrix_parts_dir: Path,
    part_names: list[str],
    out_path: Path,
    dataset_label: str,
    total_tokens: int,
    chunk_size: int = 512,
    n_layer_nextn: int = 1,
) -> int:
    merged: dict[str, dict[str, torch.Tensor]] = {}
    for pname in part_names:
        pt_path = imatrix_parts_dir / f"{pname}.pt"
        part = torch.load(str(pt_path), map_location="cpu", weights_only=True)
        for wname, stats in part.items():
            if wname in merged:
                raise ValueError(f"Duplicate GGUF imatrix tensor across parts: {wname}")
            merged[wname] = stats

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    gw = gguf.GGUFWriter(str(tmp_path), arch=None)
    gw.add_string("general.type", "imatrix")
    gw.add_array("imatrix.datasets", [dataset_label])
    gw.add_uint32("imatrix.chunk_count", max(1, math.ceil(total_tokens / max(1, chunk_size))))
    gw.add_uint32("imatrix.chunk_size", int(chunk_size))
    gw.add_uint32("imatrix.n_layer_nextn", int(n_layer_nextn))

    for wname in sorted(merged.keys()):
        st = merged[wname]
        s2_np = st["in_sum2"].numpy().astype(np.float32, copy=False)
        cnt_np = st["counts"].numpy().astype(np.float32, copy=False)
        s1_np = st["in_sum"].numpy().astype(np.float32, copy=False)
        assert s2_np.ndim == 2 and s1_np.shape == s2_np.shape
        assert cnt_np.shape == (s2_np.shape[0], 1)
        if not (np.isfinite(s2_np).all() and np.isfinite(s1_np).all() and np.isfinite(cnt_np).all()):
            raise ValueError(f"Non-finite values in imatrix tensor {wname}")
        gw.add_tensor(f"{wname}.in_sum2", s2_np)
        gw.add_tensor(f"{wname}.counts", cnt_np)
        gw.add_tensor(f"{wname}.in_sum", s1_np)

    gw.write_header_to_file()
    gw.write_kv_data_to_file()
    gw.write_tensors_to_file()
    gw.close()
    os.replace(tmp_path, out_path)
    return len(merged)


# ---------------------------------------------------------------------------
# Stage 0: Static Non-Pruned Shards (`31` PLE Hardlinks + `ple-boundary` + `root-visual`)
# ---------------------------------------------------------------------------


def run_stage0_static_exports(
    donor_dir: Path,
    st_index: SafetensorsIndex,
    out_dir: Path,
    keep_k: int,
) -> dict[str, str]:
    """Export metadata, hardlink pure PLE shards, and write `model-ple-boundary` & `model-root-visual`."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Metadata & updated `config.json` (`text_config.num_experts = keep_k`)
    with open(donor_dir / "config.json", "r", encoding="utf-8") as f:
        cfg_json = json.load(f)
    if "text_config" in cfg_json:
        cfg_json["text_config"]["num_experts"] = int(keep_k)
    else:
        cfg_json["num_experts"] = int(keep_k)
    atomic_write_json(out_dir / "config.json", cfg_json)

    for fname in METADATA_FILES_TO_COPY:
        src = donor_dir / fname
        dst = out_dir / fname
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)

    # Partition all keys in donor `weight_map`
    by_donor_file: dict[str, list[str]] = defaultdict(list)
    for k, sf in st_index.weight_map.items():
        by_donor_file[sf].append(k)

    pure_ple_files: set[str] = set()
    for sf, ks in by_donor_file.items():
        if ks and all(".ngram_embedding.shard_" in k for k in ks):
            pure_ple_files.add(sf)

    static_weight_map: dict[str, str] = {}

    # 2. Hardlink pure PLE shard files (`0 B` extra disk on same volume)
    for sf in sorted(pure_ple_files):
        src = donor_dir / sf
        dst = out_dir / sf
        if not dst.exists():
            try:
                os.link(src, dst)
            except OSError:
                shutil.copy2(src, dst)
        for k in by_donor_file[sf]:
            static_weight_map[k] = sf

    # 3. `model-ple-boundary.safetensors`: non-pure PLE shards (`shard_0,1,126,127`) + all non-shard `.ple.` keys
    ple_boundary_keys = sorted(
        k
        for k, sf in st_index.weight_map.items()
        if sf not in pure_ple_files and (".ngram_embedding.shard_" in k or ".ple." in k)
    )
    if ple_boundary_keys:
        ple_b_name = "model-ple-boundary.safetensors"
        ple_b_path = out_dir / ple_b_name
        if not ple_b_path.exists():
            ple_tensors = load_tensors_from_donor(st_index, ple_boundary_keys)
            # Enforce exact int64 on hash constants (`conversion/qwen4exp.py:66-72`)
            for hk in ple_tensors:
                if hk.endswith(("layer_multipliers", "ngram_heads_offsets", "ngram_heads_vocab_sizes")):
                    assert ple_tensors[hk].dtype == torch.int64, f"{hk} dtype {ple_tensors[hk].dtype} != int64"
            atomic_save_safetensors(ple_tensors, ple_b_path)
            del ple_tensors
            gc.collect()
        for k in ple_boundary_keys:
            static_weight_map[k] = ple_b_name

    # 4. `model-root-visual.safetensors`: root trunk keys + `model.visual.*`
    root_vis_keys = sorted(
        k
        for k in st_index.weight_map
        if not k.startswith("model.language_model.layers.") and not k.startswith("mtp.")
    )
    rv_name = "model-root-visual.safetensors"
    rv_path = out_dir / rv_name
    if not rv_path.exists():
        rv_tensors = load_tensors_from_donor(st_index, root_vis_keys)
        atomic_save_safetensors(rv_tensors, rv_path)
        del rv_tensors
        gc.collect()
    for k in root_vis_keys:
        static_weight_map[k] = rv_name

    return static_weight_map


# ---------------------------------------------------------------------------
# Main Step 6 Resumable Pipeline
# ---------------------------------------------------------------------------


@dataclass
class SampleMetaLite:
    sample_id: str
    pillar: str
    lang: str
    modality: str
    subdomain: str
    source_repo: str
    seq_len: int
    input_ids: torch.Tensor  # [1, S] int64 CPU


def build_mtp_decoder_config(base_text_cfg: Qwen4ExpTextConfig) -> Qwen4ExpTextConfig:
    mtp_cfg = copy.deepcopy(base_text_cfg)
    mtp_cfg.num_hidden_layers = 1
    non_linear_types = [lt for lt in base_text_cfg.layer_types if lt != "linear_attention"]
    mtp_cfg.layer_types = [non_linear_types[0] if non_linear_types else "indexed_attention"]
    mtp_cfg.ple_layer_ids = []
    mtp_cfg._attn_implementation = "sdpa"
    return mtp_cfg


def run_step6_pipeline(
    donor_dir: Path,
    out_dir: Path,
    calib_path: Path,
    imatrix_out_path: Path,
    telemetry_dir: Path,
    device: str = "cuda:0",
    keep_k: int = 205,
    resume: bool = True,
    max_minutes: float = 0.0,
    max_layers: int = 0,
    stop_file: Path | None = None,
    verify_calib_sha: bool = True,
) -> int:
    work_dir = out_dir / "_work"
    imat_parts_dir = work_dir / "imatrix"
    scores_dir = telemetry_dir / "scores"
    ckpt_path = work_dir / "checkpoint.json"
    work_dir.mkdir(parents=True, exist_ok=True)
    imat_parts_dir.mkdir(parents=True, exist_ok=True)
    scores_dir.mkdir(parents=True, exist_ok=True)

    stop_sentinel = stop_file if stop_file is not None else (work_dir / "STOP")
    if stop_sentinel.exists():
        stop_sentinel.unlink()
    stopper = StopController(stop_file=stop_sentinel, max_minutes=max_minutes)
    stopper.install()

    is_cuda = device.startswith("cuda")
    if is_cuda:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available!")
        gpu_apps = query_nvidia_smi_apps()
        benign_win_procs = (
            "explorer.exe",
            "dwm.exe",
            "searchhost.exe",
            "shellexperiencehost.exe",
            "startmenuexperiencehost.exe",
            "textinputhost.exe",
        )
        other_apps = [
            a
            for a in gpu_apps
            if int(a.get("pid", -1)) != os.getpid()
            and not str(a.get("process_name", "")).lower().endswith(benign_win_procs)
            and str(a.get("process_name", "")) != "[Insufficient Permissions]"
        ]
        if other_apps:
            raise RuntimeError(f"Other GPU process already occupies VRAM: {other_apps}")
        torch.cuda.set_per_process_memory_fraction(0.88, 0)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False

    calib_sha = sha256_file(calib_path)
    if verify_calib_sha and calib_sha != EXPECTED_CALIB_SHA256:
        raise RuntimeError(f"Calibration SHA-256 mismatch: {calib_sha} != {EXPECTED_CALIB_SHA256}")

    with open(calib_path, "r", encoding="utf-8") as f:
        calib_rows = [json.loads(line) for line in f if line.strip()]
    seq_lens = [int(r["qwen38_tokens"]) for r in calib_rows]
    total_tokens = int(sum(seq_lens))

    st_index = SafetensorsIndex(donor_dir)
    cfg: Qwen4ExpConfig = AutoConfig.from_pretrained(str(donor_dir))
    cfg._attn_implementation = "sdpa"
    cfg.text_config._attn_implementation = "sdpa"
    cfg.vision_config._attn_implementation = "sdpa"
    text_cfg = cfg.text_config

    n_layers = int(text_cfg.num_hidden_layers)
    hidden_size = int(text_cfg.hidden_size)
    hc_count = int(text_cfg.hc_count)
    hc_width = hidden_size * hc_count
    head_dim = int(text_cfg.head_dim)

    state: dict[str, Any] = {
        "calib_sha256": calib_sha,
        "num_rows": len(calib_rows),
        "total_tokens": total_tokens,
        "keep_k": int(keep_k),
        "stage0_done": False,
        "stage_a_done": False,
        "last_completed_layer": -1,
        "trunk_head_done": False,
        "mtp_done": False,
        "finalized": False,
        "layer_timings_sec": {},
    }
    if resume and ckpt_path.exists():
        with open(ckpt_path, "r", encoding="utf-8") as f:
            loaded_state = json.load(f)
        if loaded_state.get("calib_sha256") != calib_sha or loaded_state.get("total_tokens") != total_tokens:
            raise RuntimeError("Checkpoint calibration dataset mismatch; refusing unsafe --resume.")
        state.update(loaded_state)
        print(
            f"[RESUME] Loaded {ckpt_path}: stage0={state['stage0_done']}, stageA={state['stage_a_done']}, "
            f"last_layer={state['last_completed_layer']}/{n_layers - 1}, "
            f"trunk_head={state['trunk_head_done']}, mtp={state['mtp_done']}",
            flush=True,
        )

    e0_store: ResumableFlatSequenceStore | None = None
    cos_store: ResumableFlatSequenceStore | None = None
    sin_store: ResumableFlatSequenceStore | None = None
    pingpong: ResumablePingPong | None = None

    try:
        # -------------------------------------------------------------------
        # Stage 0: Static metadata + 31 PLE hardlinks + ple-boundary + root-visual
        # -------------------------------------------------------------------
        t0 = time.perf_counter()
        print(f"[Stage 0] Preparing static shards & metadata in {out_dir} ...", flush=True)
        static_weight_map = run_stage0_static_exports(donor_dir, st_index, out_dir, keep_k=keep_k)
        if not state["stage0_done"]:
            state["stage0_done"] = True
            atomic_write_json(ckpt_path, state)
        print(
            f"[Stage 0] Ready in {time.perf_counter() - t0:.2f}s ({len(static_weight_map)} static tensors mapped).",
            flush=True,
        )

        # Instantiate meta skeleton once (`0 B` allocation)
        with torch.device("meta"):
            obs_model = Qwen4ExpModel(cfg)
        obs_model.eval()
        obs_model.visual.rotary_pos_emb = Qwen4ExpVisionRotaryEmbedding(cfg.vision_config)
        obs_model.language_model.rotary_emb = Qwen4ExpTextRotaryEmbedding(config=text_cfg)

        # Install streaming PLE on `ple_layer_ids` (1-based in config -> 0-based `layer_idx`)
        ple_layer_indices = [int(i) - 1 for i in (getattr(text_cfg, "ple_layer_ids", None) or [])]
        stream_ple_map: dict[int, SafeStreamingPLENGramEmbedding] = {}
        for pli in ple_layer_indices:
            ple_prefix = f"model.language_model.layers.{pli}.ple.ple_embedding.ngram_embedding"
            sh0_name = f"{ple_prefix}.shard_0.weight"
            with safe_open(str(st_index.checkpoint_dir / st_index.weight_map[sh0_name]), framework="pt", device="cpu") as f:
                sh0_shape = f.get_slice(sh0_name).get_shape()
            stream_ple = SafeStreamingPLENGramEmbedding(
                index=st_index,
                shard_prefix=ple_prefix,
                num_shards=int(text_cfg.split_ngram_parts),
                shard_rows=int(sh0_shape[0]),
                embed_dim=int(sh0_shape[1]),
                dtype=torch.bfloat16,
            )
            obs_model.language_model.layers[pli].ple.ple_embedding.ngram_embedding = stream_ple
            stream_ple_map[pli] = stream_ple

        # Install bit-exact fast QSA indexer on all full-attention trunk layers
        for li in range(n_layers):
            if obs_model.language_model.layers[li].layer_type != "linear_attention":
                QSAIndexerWrapper(
                    obs_model.language_model.layers[li].self_attn.indexer, mode="fast_exact_a", sync_timing=False
                )

        samples_meta_path = work_dir / "samples_meta.pt"
        reopen_a = bool(state["stage_a_done"])
        rotary_dim = int(obs_model.language_model.rotary_emb.inv_freq.numel() * 2)
        e0_store = ResumableFlatSequenceStore(work_dir / "e0_buf.bin", seq_lens, hidden_size, reopen_existing=reopen_a)
        cos_store = ResumableFlatSequenceStore(work_dir / "rotary_cos.bin", seq_lens, rotary_dim, reopen_existing=reopen_a)
        sin_store = ResumableFlatSequenceStore(work_dir / "rotary_sin.bin", seq_lens, rotary_dim, reopen_existing=reopen_a)
        pingpong = ResumablePingPong(work_dir, seq_lens, hc_width, reopen_slot0=reopen_a)

        # -------------------------------------------------------------------
        # Stage A: Streaming Embed + Vision (1 PNG decoded at a time) + M-RoPE
        # -------------------------------------------------------------------
        samples_meta: list[SampleMetaLite] = []
        if not state["stage_a_done"]:
            t_a0 = time.perf_counter()
            print(
                f"[Stage A] Streaming {len(calib_rows)} samples ({total_tokens:,} tokens) through embed_tokens + ViT ...",
                flush=True,
            )
            tok = AutoTokenizer.from_pretrained(str(donor_dir), trust_remote_code=False)
            has_mm = any(r.get("modality") == "multimodal" for r in calib_rows)
            proc = AutoProcessor.from_pretrained(str(donor_dir), trust_remote_code=False) if has_mm else None
            image_pad_id = int(getattr(text_cfg, "image_token_id", 248056))

            materialize_submodule(obs_model.language_model.embed_tokens, "model.language_model.embed_tokens", st_index, "cpu")
            if has_mm:
                materialize_submodule(obs_model.visual, "model.visual", st_index, device)
                obs_model.visual.rotary_pos_emb = obs_model.visual.rotary_pos_emb.to(device)
                if is_cuda:
                    torch.cuda.synchronize(device)

            with torch.no_grad():
                for idx_s, r in enumerate(calib_rows):
                    stopper.check_immediate_stop()
                    text = r["text"]
                    if r["modality"] == "multimodal":
                        assert proc is not None
                        pil_imgs = [Image.open(calib_path.parent.parent.parent / im["path"]).convert("RGB") for im in r["images"]]
                        out_p = proc(text=[text], images=pil_imgs, return_tensors="pt")
                        for im_obj in pil_imgs:
                            im_obj.close()
                        input_ids = out_p["input_ids"].to(torch.int64)
                        mm_tt = out_p["mm_token_type_ids"].to(torch.int64)
                        pix = out_p["pixel_values"].to(torch.float32)
                        grid = out_p["image_grid_thw"].to(torch.int64)
                        exp_vis = int((grid.prod(-1) // 4).sum().item())
                        act_pad = int((input_ids == image_pad_id).sum().item())
                        if exp_vis != act_pad:
                            raise AssertionError(f"{r['id']}: grid visual tokens {exp_vis} != pad tokens {act_pad}")
                    else:
                        input_ids = tok(text, add_special_tokens=False, return_tensors="pt")["input_ids"].to(torch.int64)
                        mm_tt = None
                        pix = None
                        grid = None

                    sl = int(input_ids.shape[1])
                    if sl != int(r["qwen38_tokens"]):
                        raise AssertionError(f"{r['id']}: seq_len {sl} != qwen38_tokens {r['qwen38_tokens']}")

                    emb = obs_model.language_model.embed_tokens(input_ids).to(torch.bfloat16)
                    if pix is not None and grid is not None:
                        vis_out = obs_model.get_image_features(pix.to(device), grid.to(device), return_dict=True)
                        img_emb = torch.cat(vis_out.pooler_output, dim=0).to("cpu", emb.dtype)
                        img_mask, _ = obs_model.get_placeholder_mask(input_ids, inputs_embeds=emb, image_features=img_emb)
                        emb = emb.masked_scatter(img_mask, img_emb)
                        del vis_out, img_emb, img_mask

                    prep_tmp = PreparedSample(
                        sample_id=r["id"],
                        pillar=r["pillar"],
                        lang=r["lang"],
                        modality=r["modality"],
                        subdomain=r.get("subdomain", ""),
                        seq_len=sl,
                        input_ids=input_ids,
                        mm_token_type_ids=mm_tt,
                        pixel_values=None,
                        image_grid_thw=grid,
                        source_repo=str(r.get("source_repo", "")),
                    )
                    cos, sin = compute_position_embeddings_for_sample(obs_model, prep_tmp, emb, rotary_device=device)

                    e0_store.write_sample(idx_s, emb)
                    cos_store.write_sample(idx_s, cos.to(torch.bfloat16))
                    sin_store.write_sample(idx_s, sin.to(torch.bfloat16))
                    pingpong.write_sample(0, idx_s, emb.repeat(1, 1, hc_count))

                    samples_meta.append(
                        SampleMetaLite(
                            sample_id=r["id"],
                            pillar=r["pillar"],
                            lang=r["lang"],
                            modality=r["modality"],
                            subdomain=r.get("subdomain", ""),
                            source_repo=str(r.get("source_repo", "")),
                            seq_len=sl,
                            input_ids=input_ids,
                        )
                    )
                    del emb, cos, sin, pix, grid, mm_tt
                    if (idx_s + 1) % 150 == 0 or (idx_s + 1) == len(calib_rows):
                        print(f"  [Stage A] {idx_s + 1}/{len(calib_rows)} samples prepared...", flush=True)

            e0_store.flush()
            cos_store.flush()
            sin_store.flush()
            pingpong.flush_slot(0)
            atomic_torch_save(
                [
                    {
                        "sample_id": s.sample_id,
                        "pillar": s.pillar,
                        "lang": s.lang,
                        "modality": s.modality,
                        "subdomain": s.subdomain,
                        "source_repo": s.source_repo,
                        "seq_len": s.seq_len,
                        "input_ids": s.input_ids,
                    }
                    for s in samples_meta
                ],
                samples_meta_path,
            )

            obs_model.visual.rotary_pos_emb = obs_model.visual.rotary_pos_emb.to("cpu")
            free_submodule_to_meta(
                obs_model.visual, keep_non_checkpoint_names={"rotary_pos_emb.inv_freq", "rotary_pos_emb.original_inv_freq"}
            )
            free_submodule_to_meta(obs_model.language_model.embed_tokens)
            gc.collect()
            if is_cuda:
                torch.cuda.empty_cache()

            state["stage_a_done"] = True
            atomic_write_json(ckpt_path, state)
            print(f"[Stage A] Completed in {time.perf_counter() - t_a0:.2f}s.", flush=True)
        else:
            raw_meta = torch.load(str(samples_meta_path), map_location="cpu", weights_only=True)
            samples_meta = [SampleMetaLite(**d) for d in raw_meta]

        image_pad_id = int(getattr(text_cfg, "image_token_id", 248056))
        layers_completed_this_session = 0

        # -------------------------------------------------------------------
        # Stage B: Trunk Decoder Layers `0..47`
        # -------------------------------------------------------------------
        start_layer = int(state["last_completed_layer"]) + 1
        for li in range(start_layer, n_layers):
            pause_reason = stopper.should_pause_between_stages()
            if pause_reason or (max_layers > 0 and layers_completed_this_session >= max_layers):
                reason = pause_reason or f"--max-layers {max_layers} reached"
                print(
                    f"[PAUSE] Cleanly pausing before layer {li:02d}/{n_layers - 1} ({reason}). "
                    f"Completed layers: 0..{li - 1}.",
                    flush=True,
                )
                return 0

            t_l0 = time.perf_counter()
            in_slot = li % 2
            out_slot = (li + 1) % 2
            layer_mod = obs_model.language_model.layers[li]
            ltype = layer_mod.layer_type

            # Pre-index PLE cache ONLY right before `pli` and release right after `pli` (`1.41 GiB` RAM)
            if li in stream_ple_map:
                ple_parent = layer_mod.ple.ple_embedding
                materialize_submodule(
                    ple_parent, f"model.language_model.layers.{li}.ple.ple_embedding", st_index, "cpu"
                )
                ple_stats = stream_ple_map[li].build_preindexed_cache(
                    ple_parent, [s.input_ids for s in samples_meta]
                )
                free_submodule_to_meta(ple_parent, keep_non_checkpoint_names={"ngram_embedding.weight"})
                print(
                    f"  [Layer {li:02d} PLE] Pre-indexed {ple_stats['unique_ngram_rows']:,} unique rows "
                    f"({ple_stats['cache_ram_mib']} MiB RAM) in {ple_stats['safetensors_slice_io_sec']:.2f}s.",
                    flush=True,
                )

            if is_cuda:
                torch.cuda.reset_peak_memory_stats(device)

            materialize_submodule(
                layer_mod,
                f"model.language_model.layers.{li}",
                st_index,
                device,
            )
            if is_cuda:
                torch.cuda.synchronize(device)

            reap_acc = Step6REAPAccumulator(num_experts=int(text_cfg.num_experts), image_pad_token_id=image_pad_id)
            imat = LayerImatrixCollector(device=device)
            hooks = attach_non_moe_imatrix_hooks(layer_mod, text_cfg, bid=li, imat=imat)

            try:
                for idx_s, sm in enumerate(samples_meta):
                    stopper.check_immediate_stop()
                    reap_acc.current_stratum = sm.pillar
                    reap_acc.current_subbucket = (
                        "craft_p4"
                        if (
                            sm.pillar == "pillar_4_art_direction_copywriting"
                            and sm.source_repo == "SmartLLM/curated-bilingual-canons"
                        )
                        else None
                    )
                    reap_acc.current_lang = sm.lang

                    h_in = pingpong.read_sample(in_slot, idx_s)
                    cos_s = cos_store.read_sample(idx_s)
                    sin_s = sin_store.read_sample(idx_s)
                    h_out = forward_decoder_layer_step6(
                        layer=layer_mod,
                        text_cfg=text_cfg,
                        bid=li,
                        hidden_states_cpu=h_in,
                        full_cos_cpu=cos_s,
                        full_sin_cpu=sin_s,
                        ple_input_ids_cpu=sm.input_ids,
                        device=device,
                        reap_acc=reap_acc,
                        imat=imat,
                    )
                    pingpong.write_sample(out_slot, idx_s, h_out)
                    del h_in, cos_s, sin_s, h_out
            finally:
                for h in hooks:
                    h.remove()

            gate_w_cpu = layer_mod.mlp.gate.weight.detach().to("cpu")
            score_report = reap_acc.select_keep_indices_and_finalize(gate_w_cpu, keep_k=keep_k)
            keep_indices = score_report["keep_indices_k205_sorted"]
            imat_cpu = imat.export_cpu_float32(keep_indices=keep_indices)
            del gate_w_cpu, imat

            vram_alloc_gib = round(torch.cuda.max_memory_allocated(device) / (1024**3), 3) if is_cuda else 0.0
            vram_res_gib = round(torch.cuda.max_memory_reserved(device) / (1024**3), 3) if is_cuda else 0.0

            # Free GPU layer & PLE cache BEFORE loading CPU safetensors shard for slicing
            free_submodule_to_meta(layer_mod)
            if li in stream_ple_map:
                stream_ple_map[li].clear_cache()
            gc.collect()
            if is_cuda:
                torch.cuda.empty_cache()

            # Slice & atomically write `model-layer-{li:02d}.safetensors` (24 non-PLE keys)
            layer_prefix = f"model.language_model.layers.{li}."
            layer_keys = sorted(
                k for k in st_index.weight_map if k.startswith(layer_prefix) and ".ple." not in k
            )
            layer_tensors = load_tensors_from_donor(st_index, layer_keys)
            slice_expert_tensors_inplace(layer_tensors, keep_indices)
            out_sf_name = f"model-layer-{li:02d}.safetensors"
            written_bytes = atomic_save_safetensors(layer_tensors, out_dir / out_sf_name)
            del layer_tensors
            gc.collect()

            atomic_torch_save(imat_cpu, imat_parts_dir / f"layer_{li:02d}.pt")
            del imat_cpu

            ram_info = get_windows_ram_telemetry()
            pages_out = sample_pages_output_per_sec()
            dt_layer = time.perf_counter() - t_l0
            score_report["layer_idx"] = li
            score_report["layer_type"] = ltype
            score_report["wall_sec"] = round(dt_layer, 2)
            score_report["vram_peak_alloc_gib"] = vram_alloc_gib
            score_report["vram_peak_reserved_gib"] = vram_res_gib
            score_report["avail_ram_gib"] = ram_info["avail_phys_gib"]
            score_report["pages_output_per_sec"] = pages_out
            score_report["pruned_safetensors_bytes"] = written_bytes
            atomic_write_json(scores_dir / f"layer_{li:02d}.json", score_report)

            # Flush ping-pong output slot BEFORE advancing `last_completed_layer`
            pingpong.flush_slot(out_slot)
            state["last_completed_layer"] = li
            state["layer_timings_sec"][str(li)] = round(dt_layer, 2)
            atomic_write_json(ckpt_path, state)
            layers_completed_this_session += 1

            rem_blocks = (n_layers - 1 - li) + 1  # remaining trunk layers + MTP
            eta_min = (rem_blocks * dt_layer) / 60.0
            ret = score_report["retention_diagnostics_k205"]
            print(
                f"[Layer {li:02d}/{n_layers - 1} DONE] ({ltype}) {dt_layer / 60.0:.2f}m | "
                f"VRAM {vram_alloc_gib:.2f}/{vram_res_gib:.2f} GiB | AvailRAM {ram_info['avail_phys_gib']:.2f} GiB | "
                f"PagesOut={pages_out} | RU={ret['ru_top50_retained_in_k205']}/50 "
                f"P4={ret['pillar4_top50_retained_in_k205']}/50 | Elapsed {stopper.elapsed_minutes():.1f}m, ETA ~{eta_min:.0f}m",
                flush=True,
            )

        # -------------------------------------------------------------------
        # Stage C: Trunk Output Head (`output_hc_down`, `output_hc_up`, `output`)
        # -------------------------------------------------------------------
        h47_slot = n_layers % 2  # For n_layers=48, layer 47 wrote into slot `(47+1)%2 = 0`!
        if not state["trunk_head_done"]:
            pause_reason = stopper.should_pause_between_stages()
            if pause_reason:
                print(f"[PAUSE] Cleanly pausing before Trunk Head ({pause_reason}).", flush=True)
                return 0

            t_th0 = time.perf_counter()
            print("[Stage C] Collecting imatrix for Trunk Output Head (hyper_connection_mixer + output.weight)...", flush=True)
            hc_mixer = obs_model.language_model.hyper_connection_mixer
            materialize_submodule(hc_mixer, "model.language_model.hyper_connection_mixer", st_index, device)
            imat_head = LayerImatrixCollector(device=device)
            h_down = hc_mixer.input_mix_weight_down.register_forward_pre_hook(
                lambda _m, inp: imat_head.record_2d(("output_hc_down.weight",), inp[0])
            )
            h_up = hc_mixer.input_mix_weight_up.register_forward_pre_hook(
                lambda _m, inp: imat_head.record_2d(("output_hc_up.weight",), inp[0])
            )
            try:
                with torch.no_grad():
                    for idx_s, sm in enumerate(samples_meta):
                        stopper.check_immediate_stop()
                        h47_cpu = pingpong.read_sample(h47_slot, idx_s)
                        for st in range(0, sm.seq_len, DEFAULT_CHUNK_TOKENS):
                            ed = min(sm.seq_len, st + DEFAULT_CHUNK_TOKENS)
                            hc_c = h47_cpu[:, st:ed, :].to(device, non_blocking=False)
                            out_c = hc_mixer(hc_c)
                            if isinstance(out_c, tuple):
                                out_c = out_c[0]
                            imat_head.record_2d(("output.weight",), out_c)
                            del hc_c, out_c
                        del h47_cpu
            finally:
                h_down.remove()
                h_up.remove()
                free_submodule_to_meta(hc_mixer)
                if is_cuda:
                    torch.cuda.empty_cache()

            atomic_torch_save(imat_head.export_cpu_float32(), imat_parts_dir / "trunk_head.pt")
            del imat_head
            state["trunk_head_done"] = True
            atomic_write_json(ckpt_path, state)
            print(f"[Stage C] Trunk Output Head done in {time.perf_counter() - t_th0:.2f}s.", flush=True)

        # -------------------------------------------------------------------
        # Stage D: `mtp.layers.0` (`blk.{n_layers}` on `S - 1` causal pairs, NO `k = 0`)
        # -------------------------------------------------------------------
        has_mtp = any(k.startswith("mtp.") for k in st_index.weight_map)
        if has_mtp and not state["mtp_done"]:
            pause_reason = stopper.should_pause_between_stages()
            if pause_reason or (max_layers > 0 and layers_completed_this_session >= max_layers):
                print(f"[PAUSE] Cleanly pausing before MTP block ({pause_reason or '--max-layers'}).", flush=True)
                return 0

            t_m0 = time.perf_counter()
            mtp_bid = n_layers
            print(f"[Stage D] Scoring & pruning MTP block (blk.{mtp_bid}) on exact S - 1 causal pairs...", flush=True)
            mtp_cfg = build_mtp_decoder_config(text_cfg)

            with torch.device("meta"):
                pre_enorm = Qwen4ExpTextRMSNorm(hidden_size, eps=float(text_cfg.rms_norm_eps))
                pre_hnorm = Qwen4ExpTextRMSNorm(hc_width, group_size=hidden_size, eps=float(text_cfg.rms_norm_eps))
                fc_emb = nn.Linear(hidden_size, hidden_size, bias=False)
                fc_hid = nn.Linear(hidden_size, hidden_size, bias=False)
                mtp_layer = Qwen4ExpTextDecoderLayer(mtp_cfg, layer_idx=0)
                mtp_head_mixer = Qwen4ExpTextGatedResidual(mtp_cfg, use_combine=False)

            QSAIndexerWrapper(mtp_layer.self_attn.indexer, mode="fast_exact_a", sync_timing=False)

            materialize_submodule(pre_enorm, "mtp.pre_fc_norm_embedding", st_index, device)
            materialize_submodule(pre_hnorm, "mtp.pre_fc_norm_hidden", st_index, device)
            materialize_submodule(fc_emb, "mtp.fc_embedding", st_index, device)
            materialize_submodule(fc_hid, "mtp.fc_hidden", st_index, device)
            materialize_submodule(mtp_layer, "mtp.layers.0", st_index, device)
            materialize_submodule(mtp_head_mixer, "mtp.hyper_connection_mixer", st_index, device)
            if is_cuda:
                torch.cuda.synchronize(device)

            reap_mtp = Step6REAPAccumulator(num_experts=int(text_cfg.num_experts), image_pad_token_id=image_pad_id)
            imat_mtp = LayerImatrixCollector(device=device)
            hooks_mtp = attach_non_moe_imatrix_hooks(mtp_layer, mtp_cfg, bid=mtp_bid, imat=imat_mtp)
            hooks_mtp.append(
                mtp_head_mixer.input_mix_weight_down.register_forward_pre_hook(
                    lambda _m, inp: imat_mtp.record_2d((f"blk.{mtp_bid}.nextn.hc_head_down.weight",), inp[0])
                )
            )
            hooks_mtp.append(
                mtp_head_mixer.input_mix_weight_up.register_forward_pre_hook(
                    lambda _m, inp: imat_mtp.record_2d((f"blk.{mtp_bid}.nextn.hc_head_up.weight",), inp[0])
                )
            )

            try:
                with torch.no_grad():
                    for idx_s, sm in enumerate(samples_meta):
                        stopper.check_immediate_stop()
                        if sm.seq_len < 2:
                            continue
                        reap_mtp.current_stratum = sm.pillar
                        reap_mtp.current_subbucket = (
                            "craft_p4"
                            if (
                                sm.pillar == "pillar_4_art_direction_copywriting"
                                and sm.source_repo == "SmartLLM/curated-bilingual-canons"
                            )
                            else None
                        )
                        reap_mtp.current_lang = sm.lang

                        # Strictly `S - 1` causal pairs (`k = 1..S-1`): `E^(0)[:, 1:, :]` + pre-mixer `H^(47)[:, :-1, :]`
                        e0_s = e0_store.read_sample(idx_s)[:, 1:, :]
                        h47_s = pingpong.read_sample(h47_slot, idx_s)[:, :-1, :]
                        cos_mtp = cos_store.read_sample(idx_s)[:, 1:, :]
                        sin_mtp = sin_store.read_sample(idx_s)[:, 1:, :]
                        ids_mtp = sm.input_ids[:, 1:]
                        mtp_len = sm.seq_len - 1

                        res_hc_cpu = torch.empty((1, mtp_len, hc_width), dtype=torch.bfloat16, device="cpu")
                        for st in range(0, mtp_len, DEFAULT_CHUNK_TOKENS):
                            ed = min(mtp_len, st + DEFAULT_CHUNK_TOKENS)
                            e_c = e0_s[:, st:ed, :].to(device, non_blocking=False)
                            h_c = h47_s[:, st:ed, :].to(device, non_blocking=False)
                            e_norm = pre_enorm(e_c)
                            h_norm_4d = pre_hnorm(h_c).view(1, ed - st, hc_count, hidden_size)
                            imat_mtp.record_mtp_eh_proj(f"blk.{mtp_bid}.nextn.eh_proj.weight", e_norm, h_norm_4d)
                            res_c = (fc_emb(e_norm).unsqueeze(2) + fc_hid(h_norm_4d)).reshape(1, ed - st, hc_width)
                            res_hc_cpu[:, st:ed, :] = res_c.to("cpu", dtype=torch.bfloat16)
                            del e_c, h_c, e_norm, h_norm_4d, res_c

                        h_mtp_out_cpu = forward_decoder_layer_step6(
                            layer=mtp_layer,
                            text_cfg=mtp_cfg,
                            bid=mtp_bid,
                            hidden_states_cpu=res_hc_cpu,
                            full_cos_cpu=cos_mtp,
                            full_sin_cpu=sin_mtp,
                            ple_input_ids_cpu=ids_mtp,
                            device=device,
                            reap_acc=reap_mtp,
                            imat=imat_mtp,
                        )
                        for st in range(0, mtp_len, DEFAULT_CHUNK_TOKENS):
                            ed = min(mtp_len, st + DEFAULT_CHUNK_TOKENS)
                            hm_c = h_mtp_out_cpu[:, st:ed, :].to(device, non_blocking=False)
                            _ = mtp_head_mixer(hm_c)
                            del hm_c
                        del e0_s, h47_s, cos_mtp, sin_mtp, res_hc_cpu, h_mtp_out_cpu
            finally:
                for h in hooks_mtp:
                    h.remove()

            gate_mtp_cpu = mtp_layer.mlp.gate.weight.detach().to("cpu")
            mtp_report = reap_mtp.select_keep_indices_and_finalize(gate_mtp_cpu, keep_k=keep_k)
            mtp_keep = mtp_report["keep_indices_k205_sorted"]
            imat_mtp_cpu = imat_mtp.export_cpu_float32(keep_indices=mtp_keep)
            del gate_mtp_cpu, imat_mtp

            for mod in (pre_enorm, pre_hnorm, fc_emb, fc_hid, mtp_layer, mtp_head_mixer):
                free_submodule_to_meta(mod)
            gc.collect()
            if is_cuda:
                torch.cuda.empty_cache()

            mtp_keys = sorted(k for k in st_index.weight_map if k.startswith("mtp."))
            mtp_tensors = load_tensors_from_donor(st_index, mtp_keys)
            slice_expert_tensors_inplace(mtp_tensors, mtp_keep)
            mtp_bytes = atomic_save_safetensors(mtp_tensors, out_dir / "model-mtp.safetensors")
            del mtp_tensors
            gc.collect()

            atomic_torch_save(imat_mtp_cpu, imat_parts_dir / "mtp.pt")
            del imat_mtp_cpu

            dt_mtp = time.perf_counter() - t_m0
            mtp_report["layer_idx"] = mtp_bid
            mtp_report["layer_type"] = "mtp_full_attention"
            mtp_report["wall_sec"] = round(dt_mtp, 2)
            mtp_report["pruned_safetensors_bytes"] = mtp_bytes
            atomic_write_json(scores_dir / "mtp.json", mtp_report)

            state["mtp_done"] = True
            state["layer_timings_sec"]["mtp"] = round(dt_mtp, 2)
            atomic_write_json(ckpt_path, state)
            print(f"[Stage D] MTP block (blk.{mtp_bid}) DONE in {dt_mtp / 60.0:.2f}m.", flush=True)
        elif not has_mtp:
            state["mtp_done"] = True

        # -------------------------------------------------------------------
        # Stage E: Finalize `imatrix_step6.gguf`, `model.safetensors.index.json`, and Bijection Gate
        # -------------------------------------------------------------------
        if not state["finalized"]:
            print("[Stage E] Writing final imatrix GGUF & verifying 100% safetensors bijection...", flush=True)
            part_names = [f"layer_{li:02d}" for li in range(n_layers)] + ["trunk_head"]
            if has_mtp:
                part_names.append("mtp")
            n_imat_weights = write_imatrix_gguf(
                imatrix_parts_dir=imat_parts_dir,
                part_names=part_names,
                out_path=imatrix_out_path,
                dataset_label="data/calib/PremiumWebStudio-Calib.jsonl",
                total_tokens=total_tokens,
                chunk_size=512,
                n_layer_nextn=1 if has_mtp else 0,
            )

            # Build complete `weight_map` and verify exact key bijection against donor
            final_weight_map: dict[str, str] = dict(static_weight_map)
            for li in range(n_layers):
                sf_name = f"model-layer-{li:02d}.safetensors"
                l_prefix = f"model.language_model.layers.{li}."
                for k in st_index.weight_map:
                    if k.startswith(l_prefix) and ".ple." not in k:
                        final_weight_map[k] = sf_name
            if has_mtp:
                for k in st_index.weight_map:
                    if k.startswith("mtp."):
                        final_weight_map[k] = "model-mtp.safetensors"

            donor_keys = set(st_index.weight_map.keys())
            pruned_keys = set(final_weight_map.keys())
            sym_diff = donor_keys.symmetric_difference(pruned_keys)
            if sym_diff:
                raise RuntimeError(f"Bijection gate FAILED! Symmetric difference ({len(sym_diff)}): {sorted(sym_diff)[:10]}")

            # Verify every referenced physical file exists & compute exact total byte size
            total_param_bytes = 0
            unique_files = sorted(set(final_weight_map.values()))
            actual_keys_on_disk: set[str] = set()
            for sf in unique_files:
                sf_path = out_dir / sf
                if not sf_path.exists():
                    raise FileNotFoundError(f"Missing output safetensors file {sf_path}")
                with safe_open(str(sf_path), framework="pt", device="cpu") as f:
                    for k in f.keys():
                        actual_keys_on_disk.add(k)
                        sl = f.get_slice(k)
                        shape = sl.get_shape()
                        dt_str = sl.get_dtype()
                        bpe = {"BF16": 2, "F16": 2, "F32": 4, "I64": 8, "F64": 8, "I32": 4, "U8": 1, "I8": 1}[dt_str]
                        numel = 1
                        for d in shape:
                            numel *= int(d)
                        total_param_bytes += numel * bpe
                        if k.endswith((".mlp.gate.weight", ".mlp.experts.gate_up_proj", ".mlp.experts.down_proj")):
                            if int(shape[0]) != int(keep_k):
                                raise AssertionError(f"{k} in {sf} has shape[0]={shape[0]} != {keep_k}")

            if actual_keys_on_disk.symmetric_difference(donor_keys):
                raise RuntimeError("On-disk safetensors headers do not match index weight_map 1:1!")

            atomic_write_json(
                out_dir / "model.safetensors.index.json",
                {"metadata": {"total_size": int(total_param_bytes)}, "weight_map": dict(sorted(final_weight_map.items()))},
            )

            # Close binary stores BEFORE removing `_work` scratch buffers on 100% completion
            e0_store.close()
            e0_store = None
            cos_store.close()
            cos_store = None
            sin_store.close()
            sin_store = None
            pingpong.close()
            pingpong = None
            gc.collect()

            for bin_name in ("hc_buf_0.bin", "hc_buf_1.bin", "e0_buf.bin", "rotary_cos.bin", "rotary_sin.bin"):
                bp = work_dir / bin_name
                if bp.exists():
                    bp.unlink()

            state["finalized"] = True
            state["imatrix_weights_count"] = n_imat_weights
            state["pruned_safetensors_files_count"] = len(unique_files)
            state["pruned_tensors_count"] = len(final_weight_map)
            state["pruned_total_size_bytes"] = total_param_bytes
            state["completed_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_write_json(ckpt_path, state)
            atomic_write_json(telemetry_dir / "step6_summary.json", state)
            print(
                f"[STEP 6 COMPLETE] {len(unique_files)} safetensors files, {len(final_weight_map)} tensors "
                f"(symmetric_difference=0), {n_imat_weights} imatrix weights -> {imatrix_out_path}.",
                flush=True,
            )

        return 0

    except GracefulPauseRequested as gp:
        print(f"[PAUSED CLEANLY] {gp}. All completed layers & _work buffers preserved intact.", flush=True)
        return 0
    finally:
        stopper.restore()
        for st_obj in (e0_store, cos_store, sin_store, pingpong):
            if st_obj is not None:
                st_obj.close()
        gc.collect()
        if is_cuda and torch.cuda.is_available():
            torch.cuda.empty_cache()


# ---------------------------------------------------------------------------
# End-to-End CPU Synthetic Self-Test (`--self-test-cpu`, 0 GPU, ~5 s)
# ---------------------------------------------------------------------------


def run_cpu_self_test() -> int:
    print("=== Running Step 6 CPU Synthetic Self-Test (0 GPU VRAM) ===", flush=True)
    torch.manual_seed(20261111)

    # 1. Verify GDN `_reorder_v_heads` activation permutation exactness (`linear_num_value_heads=48, key_heads=16 => 3:1`)
    w_orig = torch.randn(32, 48 * 8, dtype=torch.float32)  # [out, 16 * 3 * 8]
    x_orig = torch.randn(7, 48 * 8, dtype=torch.float32)
    y_ref = F.linear(x_orig, w_orig)
    w_perm = w_orig.reshape(32, 16, 3, 8).permute(0, 2, 1, 3).reshape(32, 48 * 8)
    x_perm = reorder_gdn_v_heads_activation(x_orig, num_k_heads=16, num_v_heads=48, head_v_dim=8)
    y_perm = F.linear(x_perm, w_perm)
    assert torch.allclose(y_ref, y_perm, atol=1e-5), "GDN 3:1 V-head activation permutation mismatch!"

    # 2. Build miniature synthetic 4-layer + PLE + QSA + MTP donor checkpoint in a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        donor = tmp / "donor"
        pruned = tmp / "pruned"
        calib_dir = tmp / "data" / "calib"
        donor.mkdir(parents=True)
        calib_dir.mkdir(parents=True)

        v_cfg = Qwen4ExpVisionConfig(
            depth=1,
            hidden_size=32,
            intermediate_size=64,
            num_heads=4,
            in_channels=3,
            patch_size=16,
            spatial_merge_size=2,
            temporal_patch_size=2,
            out_hidden_size=32,
            num_position_embeddings=16,
        )
        t_cfg = Qwen4ExpTextConfig(
            vocab_size=248320,
            hidden_size=32,
            num_hidden_layers=4,
            layer_types=["linear_attention", "linear_attention", "linear_attention", "full_attention"],
            hc_count=4,
            hc_lowrank=16,
            num_attention_heads=4,
            num_key_value_heads=2,
            head_dim=16,
            linear_num_key_heads=2,
            linear_num_value_heads=6,  # 3:1 V-to-K head ratio matching real Qwen3.8-Flash-Next!
            linear_key_head_dim=16,
            linear_value_head_dim=16,
            linear_conv_kernel_dim=4,
            moe_intermediate_size=16,
            shared_expert_intermediate_size=16,
            num_experts=16,
            num_experts_per_tok=4,
            norm_topk_prob=True,
            indexer_n_heads=2,
            indexer_kv_heads=1,
            indexer_head_dim=16,
            indexer_budget=8,
            indexer_compress_ratio=4,
            ple_layer_ids=[2],  # 1-based -> layer 1
            ngram_vocab_size_base=64,
            make_ngram_vocab_size_divisible_by=16,
            ngram_size=3,
            heads_per_ngram=2,
            ple_conv_kernel_size=2,
            ple_embed_dim=16,
            split_ngram_parts=4,
            eos_token_id=2,
            partial_rotary_factor=0.5,
            rope_parameters={
                "rope_type": "default",
                "rope_theta": 10000.0,
                "partial_rotary_factor": 0.5,
                "mrope_interleaved": True,
                "mrope_section": [1, 1, 2],
            },
        )
        full_cfg = Qwen4ExpConfig(text_config=t_cfg.to_dict(), vision_config=v_cfg.to_dict(), image_token_id=248056)
        full_cfg.save_pretrained(str(donor))

        model = Qwen4ExpModel(full_cfg).to(torch.bfloat16)
        sd = {f"model.{k}": v for k, v in model.state_dict().items()}
        weight_map: dict[str, str] = {}

        # Split PLE `ngram_embedding.weight` into 4 shards (shards 1 & 2 as pure PLE files!)
        ple_key = "model.language_model.layers.1.ple.ple_embedding.ngram_embedding.weight"
        ple_full = sd.pop(ple_key)
        shard_rows = ple_full.shape[0] // 4

        shard0_tensors: dict[str, torch.Tensor] = {}
        for k, v in sd.items():
            shard0_tensors[k] = v if v.dtype == torch.int64 else v.to(torch.bfloat16)
            weight_map[k] = "model-00001.safetensors"
        # Add boundary shards 0 & 3 into mixed file, and shards 1 & 2 into pure PLE files
        for si in (0, 3):
            sk = f"model.language_model.layers.1.ple.ple_embedding.ngram_embedding.shard_{si}.weight"
            shard0_tensors[sk] = ple_full[si * shard_rows : (si + 1) * shard_rows].contiguous()
            weight_map[sk] = "model-00001.safetensors"
        shard0_tensors["lm_head.weight"] = torch.randn(248320, 32, dtype=torch.bfloat16)
        weight_map["lm_head.weight"] = "model-00001.safetensors"
        save_file(shard0_tensors, str(donor / "model-00001.safetensors"))

        for si in (1, 2):
            sk = f"model.language_model.layers.1.ple.ple_embedding.ngram_embedding.shard_{si}.weight"
            sf = f"model-ple-pure-{si}.safetensors"
            save_file({sk: ple_full[si * shard_rows : (si + 1) * shard_rows].contiguous()}, str(donor / sf))
            weight_map[sk] = sf

        # Synthetic MTP block (`31` keys)
        mtp_cfg = build_mtp_decoder_config(t_cfg)
        mtp_layer = Qwen4ExpTextDecoderLayer(mtp_cfg, layer_idx=0).to(torch.bfloat16)
        mtp_mixer = Qwen4ExpTextGatedResidual(mtp_cfg, use_combine=False).to(torch.bfloat16)
        mtp_tensors: dict[str, torch.Tensor] = {
            "mtp.pre_fc_norm_embedding.weight": torch.zeros(32, dtype=torch.bfloat16),
            "mtp.pre_fc_norm_hidden.weight": torch.zeros(128, dtype=torch.bfloat16),
            "mtp.fc_embedding.weight": torch.randn(32, 32, dtype=torch.bfloat16) * 0.02,
            "mtp.fc_hidden.weight": torch.randn(32, 32, dtype=torch.bfloat16) * 0.02,
        }
        for k, v in mtp_layer.state_dict().items():
            mtp_tensors[f"mtp.layers.0.{k}"] = v.to(torch.bfloat16)
        for k, v in mtp_mixer.state_dict().items():
            mtp_tensors[f"mtp.hyper_connection_mixer.{k}"] = v.to(torch.bfloat16)
        assert len(mtp_tensors) == 31, f"Expected 31 MTP keys, got {len(mtp_tensors)}"
        save_file(mtp_tensors, str(donor / "model-mtp-src.safetensors"))
        for k in mtp_tensors:
            weight_map[k] = "model-mtp-src.safetensors"

        atomic_write_json(donor / "model.safetensors.index.json", {"metadata": {}, "weight_map": weight_map})

        # Minimal dummy tokenizer via donor Qwen3.8 tokenizer copied for fast tokenize_rows compatibility
        real_tok_dir = DEFAULT_DONOR_DIR
        for fn in ("tokenizer.json", "tokenizer_config.json"):
            if (real_tok_dir / fn).exists():
                shutil.copy2(real_tok_dir / fn, donor / fn)
        tok = AutoTokenizer.from_pretrained(str(donor), trust_remote_code=False)
        s1_txt = "const hero = { color: 'oklch(0.72 0.14 250)' };"
        s2_txt = ("Премиальный минимализм и строгая модульная сетка. " * 420).strip()
        ids1 = tok(s1_txt, add_special_tokens=False)["input_ids"]
        ids2 = tok(s2_txt, add_special_tokens=False)["input_ids"]
        assert len(ids2) > DEFAULT_CHUNK_TOKENS, f"Expected chunked seq_len > {DEFAULT_CHUNK_TOKENS}, got {len(ids2)}"
        assert max(ids1 + ids2) < 248320

        calib_p = calib_dir / "calib.jsonl"
        rows = [
            {
                "id": "s1",
                "pillar": "pillar_1_frontend_3d_svg",
                "lang": "en",
                "modality": "text",
                "subdomain": "ui",
                "source_repo": "test",
                "text": s1_txt,
                "qwen38_tokens": len(ids1),
            },
            {
                "id": "s2",
                "pillar": "pillar_4_art_direction_copywriting",
                "lang": "ru",
                "modality": "text",
                "subdomain": "copy",
                "source_repo": "SmartLLM/curated-bilingual-canons",
                "text": s2_txt,
                "qwen38_tokens": len(ids2),
            },
        ]
        with open(calib_p, "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

        imat_out = calib_dir / "test_imatrix.gguf"
        telem_dir = tmp / "telemetry"

        # Pass 1: Run ONLY 2 layers (`max_layers=2`) to test clean pause!
        rc1 = run_step6_pipeline(
            donor_dir=donor,
            out_dir=pruned,
            calib_path=calib_p,
            imatrix_out_path=imat_out,
            telemetry_dir=telem_dir,
            device="cpu",
            keep_k=6,
            resume=True,
            max_layers=2,
            verify_calib_sha=False,
        )
        assert rc1 == 0
        with open(pruned / "_work" / "checkpoint.json", "r", encoding="utf-8") as f:
            ck1 = json.load(f)
        assert ck1["last_completed_layer"] == 1 and not ck1["finalized"]
        assert (pruned / "_work" / "hc_buf_0.bin").exists()

        # Pass 2: Resume (`--resume`) and finish Layers 2..3 + Trunk Head + MTP + Finalization!
        rc2 = run_step6_pipeline(
            donor_dir=donor,
            out_dir=pruned,
            calib_path=calib_p,
            imatrix_out_path=imat_out,
            telemetry_dir=telem_dir,
            device="cpu",
            keep_k=6,
            resume=True,
            max_layers=0,
            verify_calib_sha=False,
        )
        assert rc2 == 0

        with open(pruned / "config.json", "r", encoding="utf-8") as f:
            out_cfg = json.load(f)
        assert out_cfg["text_config"]["num_experts"] == 6

        # Expected quantizable GGUF weights for 3 linear (one with PLE) + 1 QSA + 1 MTP + Trunk Head:
        # 2*15 + 1*17 + 1*18 + 1*21 + 3 = 30 + 17 + 18 + 21 + 3 = 89 weights => 267 GGUF tensors!
        rd = gguf.GGUFReader(str(imat_out))
        n_gguf_tensors = len(rd.tensors)
        del rd
        gc.collect()
        assert n_gguf_tensors == 89 * 3, f"Expected {89 * 3} GGUF tensors, got {n_gguf_tensors}"

    if DEFAULT_DONOR_DIR.exists():
        real_cfg = AutoConfig.from_pretrained(str(DEFAULT_DONOR_DIR))
        real_rot = Qwen4ExpTextRotaryEmbedding(config=real_cfg.text_config)
        dummy_x = torch.zeros((1, 8, int(real_cfg.text_config.hidden_size)), dtype=torch.bfloat16)
        dummy_pos = torch.arange(8, dtype=torch.long).view(1, 1, 8).expand(3, 1, 8)
        rcos, rsin = real_rot(dummy_x, dummy_pos)
        expected_rot_dim = int(real_rot.inv_freq.numel() * 2)
        assert rcos.shape == (1, 8, expected_rot_dim) and rsin.shape == (1, 8, expected_rot_dim), (
            f"Real donor rotary shape {rcos.shape} != expected (1, 8, {expected_rot_dim})"
        )
        real_idx = SafetensorsIndex(DEFAULT_DONOR_DIR)
        assert len(real_idx.weight_map) == 1658
        real_mtp_cfg = build_mtp_decoder_config(real_cfg.text_config)
        real_mtp_cache = DynamicCache(config=real_mtp_cfg)
        assert "IndexedLayer" in type(real_mtp_cache.layers[0]).__name__, (
            f"Expected DynamicIndexedLayer for MTP, got {type(real_mtp_cache.layers[0]).__name__}"
        )

    print("=== Step 6 CPU Synthetic Self-Test PASSED (0 errors, resume + bijection + imatrix verified) ===", flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step 6 Full-Model REAP Pruning + Inline GPU imatrix")
    p.add_argument("--donor-dir", type=Path, default=DEFAULT_DONOR_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--calib-path", type=Path, default=DEFAULT_CALIB_PATH)
    p.add_argument("--imatrix-out", type=Path, default=DEFAULT_IMATRIX_OUT)
    p.add_argument("--telemetry-dir", type=Path, default=DEFAULT_TELEMETRY_DIR)
    p.add_argument("--device", type=str, default="cuda:0")
    p.add_argument("--keep-k", type=int, default=205)
    p.add_argument("--resume", action="store_true", default=True)
    p.add_argument("--no-resume", dest="resume", action="store_false")
    p.add_argument("--max-minutes", type=float, default=0.0, help="Cleanly pause between layers after N minutes")
    p.add_argument("--max-layers", type=int, default=0, help="Cleanly pause after completing N layers in this run")
    p.add_argument("--stop-file", type=Path, default=None, help="Path to STOP sentinel file")
    p.add_argument("--self-test-cpu", action="store_true", help="Run synthetic 0-GPU end-to-end self-test")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test_cpu:
        return run_cpu_self_test()
    return run_step6_pipeline(
        donor_dir=args.donor_dir,
        out_dir=args.out_dir,
        calib_path=args.calib_path,
        imatrix_out_path=args.imatrix_out,
        telemetry_dir=args.telemetry_dir,
        device=args.device,
        keep_k=args.keep_k,
        resume=args.resume,
        max_minutes=args.max_minutes,
        max_layers=args.max_layers,
        stop_file=args.stop_file,
        verify_calib_sha=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
