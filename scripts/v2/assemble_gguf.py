#!/usr/bin/env python3
"""Zero-Intermediate-Safetensors Streaming GGUF Assembler & GSQ Q2_0 In-Place Splicer.

Implements OPUS_MASTER_PLAN_V2.md §1.D1, §1.D2c, §2 WP-C1, and §3 Wave 3:
1. Subclasses upstream llama.cpp `Qwen4ExpTextModel` (`tools/llama.cpp/conversion/qwen4exp.py`)
   so 100% of qwen4exp tensor transforms (+1 Gemma norms, _SHARED_INPUT_MERGES, 3:1 GDN
   _reorder_v_heads, index_qk_proj split, nextn.eh_proj, ssm_a) are authoritative.
2. Streams donor safetensors directly into BF16-routed intermediate GGUF on
   `/mnt/windows/smartllm_scratch/` applying per-layer `keep_indices` + C3 heal overlays
   (`w_gate_f32`, `alpha_scales`, `w_down_shexp_f32`) with `POSIX_FADV_DONTNEED` shard eviction
   (ZERO 245 GiB pruned safetensors directory!).
3. Copies `per_layer_token_embd.weight` (28,800,138,240 B Q4_0) and optionally `tokenizer.*`
   KV metadata verbatim from `models/SmartLLM-205E-IQ3_XXS.gguf` in 64 MiB chunks with
   `POSIX_FADV_DONTNEED` on both source and destination fds (0 B PLE RAM residency).
4. Drives `llama-quantize` (`--imatrix` + `--tensor-type` + `--max-buffer-size 2048`) for both
   the 4.5-bpw proxy GGUF and final D1 variant GGUF, then overwrites `blk.{0..48}.ffn_down_exps`
   in-place with clean-room GSQ Q2_0 payloads and verifies exact header & dequant integrity.
"""

from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, cast

import numpy as np
import torch
from torch import Tensor

from scripts.v2.common_io import (
    DONOR_DIR,
    GGUF_PY_PATH,
    REF_205E_GGUF,
    REPO_ROOT,
    SCRATCH_DIR,
    STAGE_DIR,
    SafetensorsIndex,
    drop_fd_page_cache,
    drop_file_page_cache,
    find_llama_bin,
)
from scripts.v2.gsq_q2_0 import (
    BLOCK_Q2_0_BYTES,
    GGML_TYPE_Q2_0,
    QK2_0,
    LibGGMLQuantSimulator,
    dequantize_q2_0_cleanroom,
)

LLAMA_CPP_DIR = REPO_ROOT / "tools" / "llama.cpp"
if str(GGUF_PY_PATH) not in sys.path:
    sys.path.insert(0, str(GGUF_PY_PATH))
if str(LLAMA_CPP_DIR) not in sys.path:
    sys.path.insert(0, str(LLAMA_CPP_DIR))

import gguf  # noqa: E402
from conversion.base import LazyTorchTensor  # noqa: E402
from conversion.qwen4exp import Qwen4ExpTextModel  # noqa: E402


@dataclass
class LayerPruneHealOverlay:
    bid: int
    keep_indices: np.ndarray  # [K] int64 strictly ascending
    w_gate_f32: Optional[np.ndarray] = None  # [K, 2560] float32
    alpha_scales: Optional[np.ndarray] = None  # [K] float32
    w_down_shexp_f32: Optional[np.ndarray] = None  # [2560, 640] float32


@dataclass(frozen=True)
class QuantVariantSpec:
    variant_id: str
    target_k: int
    base_ftype: str
    gate_up_exps_qtype: str
    down_exps_qtype: str
    use_gsq_q2_0_splice: bool


# OPUS_MASTER_PLAN_V2.md §1.D1 & §1.D2b candidate table + 4.5-bpw proxy
VARIANT_SPECS: Dict[str, QuantVariantSpec] = {
    "V1": QuantVariantSpec("V1", 320, "IQ3_XXS", "iq3_xxs", "q2_0", True),
    "V2": QuantVariantSpec("V2", 320, "IQ3_XXS", "iq2_s", "q2_0", True),
    "V3": QuantVariantSpec("V3", 288, "IQ3_S", "iq3_s", "q2_0", True),
    "V4": QuantVariantSpec("V4", 288, "IQ3_XXS", "iq2_s", "iq4_nl", False),
    "PROXY_K320": QuantVariantSpec("PROXY_K320", 320, "Q4_K_M", "q4_k", "q4_k", False),
    "PROXY_K288": QuantVariantSpec("PROXY_K288", 288, "Q4_K_M", "q4_k", "q4_k", False),
}


class _StreamingGGUFByteSliceArray:
    """Array-like proxy accepted by GGUFWriter.add_tensor that streams raw pre-quantized
    bytes (e.g. 28.80 GB Q4_0 per_layer_token_embd.weight) from an existing GGUF file
    in 64 MiB chunks with POSIX_FADV_DONTNEED on both source and destination fds."""

    def __init__(
        self,
        src_gguf_path: Path,
        abs_offset: int,
        byte_shape: Tuple[int, ...],
        chunk_bytes: int = 64 * 1024 * 1024,
    ) -> None:
        self.src_gguf_path = Path(src_gguf_path)
        self.abs_offset = int(abs_offset)
        self.shape = tuple(int(x) for x in byte_shape)
        self.dtype = np.dtype(np.uint8)
        self.nbytes = int(np.prod(self.shape, dtype=np.int64))
        self.chunk_bytes = int(chunk_bytes)

    def tofile(self, fout: Any) -> None:
        src_fd = os.open(str(self.src_gguf_path), os.O_RDONLY)
        dst_fd = fout.fileno() if hasattr(fout, "fileno") else None
        fout.flush()
        dst_start = fout.tell()
        remaining = self.nbytes
        rel = 0
        try:
            while remaining > 0:
                step = min(self.chunk_bytes, remaining)
                buf = os.pread(src_fd, step, self.abs_offset + rel)
                if len(buf) != step:
                    raise IOError(f"Short read from {self.src_gguf_path}: got {len(buf)}, expected {step}")
                fout.write(buf)
                fout.flush()
                drop_fd_page_cache(src_fd, offset=self.abs_offset + rel, length=step)
                if dst_fd is not None:
                    os.fdatasync(dst_fd)
                    drop_fd_page_cache(dst_fd, offset=dst_start + rel, length=step)
                rel += step
                remaining -= step
        finally:
            os.close(src_fd)


def locate_tensor_in_gguf(gguf_path: Path, tensor_name: str) -> Tuple[int, Tuple[int, ...], gguf.GGMLQuantizationType, int]:
    """Read ONLY the <=2 MB GGUF header via gguf-py and return (abs_offset, ne_shape, qtype, n_bytes)."""
    reader = gguf.GGUFReader(str(gguf_path), "r")
    for t in reader.tensors:
        if t.name == tensor_name:
            # Note: gguf_reader.py:353 already sets t.data_offset = int(start_offs + offset_tensor[0])
            abs_off = int(t.data_offset)
            ne_shape = tuple(int(x) for x in t.shape)
            return abs_off, ne_shape, t.tensor_type, int(t.n_bytes)
    raise KeyError(f"Tensor {tensor_name!r} not found in {gguf_path}")


def copy_vocab_kv_from_gguf(src_gguf: Path, writer: gguf.GGUFWriter) -> int:
    """Copy exact tokenizer.* KV metadata from reference GGUF without re-running AutoTokenizer."""
    reader = gguf.GGUFReader(str(src_gguf), "r")
    copied = 0
    for key, field in reader.fields.items():
        if not key.startswith("tokenizer."):
            continue
        vtype = field.types[0]
        val = field.contents()
        if vtype == gguf.GGUFValueType.ARRAY:
            writer.add_array(key, val)
        elif vtype == gguf.GGUFValueType.STRING:
            writer.add_string(key, str(val))
        elif vtype == gguf.GGUFValueType.UINT32:
            writer.add_uint32(key, int(val))
        elif vtype == gguf.GGUFValueType.INT32:
            writer.add_int32(key, int(val))
        elif vtype == gguf.GGUFValueType.BOOL:
            writer.add_bool(key, bool(val))
        elif vtype == gguf.GGUFValueType.FLOAT32:
            writer.add_float32(key, float(val))
        else:
            writer.add_key_value(key, val, vtype)
        copied += 1
    return copied


def _make_lazy_overlay_tensor(
    shape: Sequence[int],
    dtype: torch.dtype,
    loader_fn: Callable[[], torch.Tensor],
) -> Tensor:
    """Construct a LazyTorchTensor with exact target metadata shape/dtype that computes
    on-the-fly during GGUF streaming and frees immediately after writing."""
    return cast(
        Tensor,
        LazyTorchTensor(
            meta=LazyTorchTensor.meta_with_dtype_and_shape(dtype, tuple(int(s) for s in shape)),
            args=(loader_fn,),
            func=lambda fn: fn(),
        ),
    )


class StreamingPrunedQwen4ExpModel(Qwen4ExpTextModel):
    """Streaming subclass of llama.cpp Qwen4ExpTextModel applying pruning + C3 heals
    on-the-fly with POSIX_FADV_DONTNEED and verbatim Q4_0 PLE copy."""

    model_arch = gguf.MODEL_ARCH.QWEN4EXP

    def __init__(
        self,
        dir_model: Path,
        ftype: gguf.LlamaFileType,
        fname_out: Path,
        target_k: int,
        overlays: Dict[int, LayerPruneHealOverlay],
        reuse_ple_gguf: Optional[Path] = REF_205E_GGUF,
        reuse_vocab_gguf: Optional[Path] = REF_205E_GGUF,
        model_name: Optional[str] = None,
        is_big_endian: bool = False,
        dry_run: bool = False,
    ) -> None:
        hparams = dict(Qwen4ExpTextModel.load_hparams(dir_model, False))
        top_arch = hparams.get("architectures")
        if "text_config" in hparams and isinstance(hparams["text_config"], dict):
            tc = dict(hparams["text_config"])
            if tc.get("architectures") is None:
                tc.pop("architectures", None)
            tc["num_experts"] = int(target_k)
            hparams = {**hparams, **tc, "text_config": tc}
        if top_arch:
            hparams["architectures"] = top_arch
        hparams["num_experts"] = int(target_k)

        self._target_k = int(target_k)
        self._overlays = dict(overlays)
        self._reuse_ple_gguf = Path(reuse_ple_gguf) if reuse_ple_gguf is not None else None
        self._reuse_vocab_gguf = Path(reuse_vocab_gguf) if reuse_vocab_gguf is not None else None
        self._ple_prequant_added = False

        # Build shard lookup + zero-mmap preadv SafetensorsIndex for POSIX_FADV_DONTNEED
        idx_json = Path(dir_model) / "model.safetensors.index.json"
        if idx_json.is_file():
            with open(idx_json, "r", encoding="utf-8") as f:
                self._donor_weight_map: Dict[str, str] = dict(json.load(f)["weight_map"])
            self._st_index: Optional[SafetensorsIndex] = SafetensorsIndex(Path(dir_model), drop_cache=True)
        else:
            self._donor_weight_map = {}
            self._st_index = None

        super().__init__(
            dir_model=dir_model,
            ftype=ftype,
            fname_out=fname_out,
            is_big_endian=is_big_endian,
            use_temp_file=False,
            eager=False,
            metadata_override=None,
            model_name=model_name or f"SmartLLM-v2-K{target_k}",
            split_max_tensors=0,
            split_max_size=0,
            dry_run=bool(dry_run),
            small_first_shard=False,
            hparams=hparams,
        )
        self._filtered_to_hf_key: Dict[str, str] = {}
        if self._donor_weight_map:
            _dummy = lambda: torch.empty(0)  # noqa: E731
            for orig_k in self._donor_weight_map:
                ft = self.filter_tensors((orig_k, _dummy))
                if ft is not None:
                    self._filtered_to_hf_key[ft[0]] = orig_k
        self._wrap_model_tensors_with_fadvise()

    def _wrap_model_tensors_with_fadvise(self) -> None:
        """Wrap lazy tensor generators so donor shard pages are evicted right after materialization."""
        if not self._donor_weight_map:
            return
        for t_name, orig_gen in list(self.model_tensors.items()):
            hk = self._resolve_hf_key(t_name)
            shard_rel = self._donor_weight_map.get(hk) if hk is not None else None
            if shard_rel is None:
                continue
            shard_path = self.dir_model / shard_rel

            def _make_gen(gen_fn: Callable[[], Tensor], sp: Path) -> Callable[[], Tensor]:
                def _wrapped() -> Tensor:
                    lazy_t = gen_fn()
                    return _make_lazy_overlay_tensor(
                        shape=lazy_t.shape,
                        dtype=lazy_t.dtype,
                        loader_fn=lambda lt=lazy_t, p=sp: self._eager_and_evict(lt, p),
                    )

                return _wrapped

            self.model_tensors[t_name] = _make_gen(orig_gen, shard_path)

    def _flush_and_evict_writer_fout(self) -> None:
        """Flush GGUF output stream and drop clean page cache so dirty pages never pile up."""
        fouts = getattr(self.gguf_writer, "fout", None)
        if not fouts:
            return
        for f_obj in fouts:
            if f_obj is None or getattr(f_obj, "closed", False):
                continue
            f_obj.flush()
            if hasattr(f_obj, "fileno"):
                fd = f_obj.fileno()
                os.fdatasync(fd)
                drop_fd_page_cache(fd, offset=0, length=0)

    def _eager_and_evict(self, lazy_t: Tensor, shard_path: Path) -> torch.Tensor:
        self._flush_and_evict_writer_fout()
        t = LazyTorchTensor.to_eager(lazy_t).clone()
        drop_file_page_cache(shard_path)
        return t

    def set_vocab(self) -> None:
        if self._reuse_vocab_gguf is not None and self._reuse_vocab_gguf.is_file():
            n_copied = copy_vocab_kv_from_gguf(self._reuse_vocab_gguf, self.gguf_writer)
            if n_copied > 0:
                return
        super().set_vocab()

    def _place_ple_shard(self, data_torch: Tensor, name: str) -> Iterable[tuple[str, Tensor]]:
        if self._reuse_ple_gguf is None or not self._reuse_ple_gguf.is_file():
            yield from super()._place_ple_shard(data_torch, name)
            return

        idx = int(name.rpartition(".shard_")[2].partition(".")[0])
        n_parts = int(self.hparams["split_ngram_parts"])
        self._ple_shards[idx] = name
        self._ple_row_dim = int(data_torch.shape[-1])
        if len(self._ple_shards) < n_parts or self._ple_prequant_added:
            return

        gguf_name = gguf.TENSOR_NAMES[gguf.MODEL_TENSOR.PER_LAYER_TOKEN_EMBD] + ".weight"
        abs_off, ne_shape, qtype, n_bytes = locate_tensor_in_gguf(self._reuse_ple_gguf, gguf_name)
        if qtype != gguf.GGMLQuantizationType.Q4_0:
            raise ValueError(f"Expected Q4_0 PLE in {self._reuse_ple_gguf}, got {qtype}")
        # ne_shape in GGUFReader is [ne0=160, ne1=320001536] -> numpy byte shape is (ne1, ne0 // 32 * 18)
        row_bytes = (ne_shape[0] // 32) * 18
        byte_shape = (ne_shape[1], row_bytes)
        if byte_shape[0] * byte_shape[1] != n_bytes:
            raise ValueError(f"PLE byte shape mismatch: {byte_shape} != {n_bytes}")

        proxy = _StreamingGGUFByteSliceArray(
            src_gguf_path=self._reuse_ple_gguf,
            abs_offset=abs_off,
            byte_shape=byte_shape,
        )
        self.gguf_writer.add_tensor(
            gguf_name,
            cast(Any, proxy),
            raw_dtype=gguf.GGMLQuantizationType.Q4_0,
        )
        self._ple_prequant_added = True

    def _resolve_hf_key(self, filtered_name: str) -> Optional[str]:
        if not self._donor_weight_map:
            return None
        if filtered_name in self._filtered_to_hf_key:
            return self._filtered_to_hf_key[filtered_name]
        for ck in (
            filtered_name,
            f"model.language_model.{filtered_name.removeprefix('model.')}",
            f"language_model.{filtered_name}",
        ):
            if ck in self._donor_weight_map:
                return ck
        return None

    def modify_tensors(self, data_torch: Tensor, name: str, bid: int | None) -> Iterable[tuple[str, Tensor]]:
        if bid is not None and bid in self._overlays:
            ov = self._overlays[bid]
            keep = [int(i) for i in ov.keep_indices]

            if name.endswith(".mlp.experts.gate_up_proj"):
                new_shape = (len(keep), int(data_torch.shape[1]), int(data_torch.shape[2]))
                hf_key = self._resolve_hf_key(name)

                def _load_gu(dt=data_torch, kp=keep, hk=hf_key) -> torch.Tensor:
                    self._flush_and_evict_writer_fout()
                    if self._st_index is not None and hk is not None:
                        return self._st_index.load_expert_slice(hk, kp, dtype=torch.float32).contiguous()
                    return LazyTorchTensor.to_eager(dt)[kp].to(torch.float32).contiguous()

                # Note: LazyTorchTensor.numpy() requires float32/float16; base.py:1313 quantizes to BF16 on disk
                data_torch = _make_lazy_overlay_tensor(new_shape, torch.float32, _load_gu)
            elif name.endswith(".mlp.experts.down_proj"):
                new_shape = (len(keep), int(data_torch.shape[1]), int(data_torch.shape[2]))
                alpha = ov.alpha_scales
                hf_key = self._resolve_hf_key(name)

                def _load_down(dt=data_torch, kp=keep, al=alpha, hk=hf_key) -> torch.Tensor:
                    self._flush_and_evict_writer_fout()
                    if self._st_index is not None and hk is not None:
                        sliced = self._st_index.load_expert_slice(hk, kp, dtype=torch.float32).contiguous()
                    else:
                        sliced = LazyTorchTensor.to_eager(dt)[kp].to(torch.float32).contiguous()
                    if al is not None:
                        al_np = np.asarray(al, dtype=np.float32)
                        k_n = len(kp)
                        for i0 in range(0, k_n, 16):
                            i1 = min(k_n, i0 + 16)
                            al_t = torch.from_numpy(al_np[i0:i1]).view(-1, 1, 1)
                            sliced[i0:i1].mul_(al_t)
                    # Round through BF16 before base.py:1313 BF16 write so values match BF16 precision
                    return sliced.to(torch.bfloat16).to(torch.float32).contiguous()

                data_torch = _make_lazy_overlay_tensor(new_shape, torch.float32, _load_down)
            elif name.endswith(".mlp.gate.weight"):
                if ov.w_gate_f32 is not None:
                    wg = np.ascontiguousarray(ov.w_gate_f32, dtype=np.float32)
                    data_torch = _make_lazy_overlay_tensor(
                        wg.shape, torch.float32, lambda arr=wg: torch.from_numpy(arr.copy())
                    )
                else:
                    new_shape = (len(keep), int(data_torch.shape[1]))
                    data_torch = _make_lazy_overlay_tensor(
                        new_shape,
                        torch.float32,
                        lambda dt=data_torch, kp=keep: LazyTorchTensor.to_eager(dt)[kp].to(torch.float32).contiguous(),
                    )
            elif name.endswith(".mlp.shared_expert.down_proj.weight") and ov.w_down_shexp_f32 is not None:
                ws = np.ascontiguousarray(ov.w_down_shexp_f32, dtype=np.float32)
                data_torch = _make_lazy_overlay_tensor(
                    ws.shape, torch.float32, lambda arr=ws: torch.from_numpy(arr.copy())
                )

        yield from super().modify_tensors(data_torch, name, bid)

    def write(self) -> None:
        super().write()
        drop_file_page_cache(self.fname_out)
        gc.collect()


def bf16_gguf_complete_marker_path(gguf_path: Path) -> Path:
    return Path(f"{gguf_path}.complete.json")


def verify_bf16_gguf_complete_marker(gguf_path: Path, expected_target_k: Optional[int] = None) -> bool:
    """OPUS Audit #90 Item 5: Require exact .complete.json bytes + tensor count on BF16 resume."""
    p = Path(gguf_path)
    m_path = bf16_gguf_complete_marker_path(p)
    if not (p.is_file() and m_path.is_file()):
        return False
    try:
        meta = json.loads(m_path.read_text(encoding="utf-8"))
        if int(p.stat().st_size) != int(meta["exact_bytes"]):
            return False
        if expected_target_k is not None and int(meta.get("expert_count", -1)) != int(expected_target_k):
            return False
        reader = gguf.GGUFReader(str(p), "r")
        if len(reader.tensors) != int(meta["tensor_count"]):
            return False
        return True
    except (OSError, ValueError, KeyError):
        return False


def _canonical_ggml_ne4(ne: Sequence[int]) -> Tuple[int, int, int, int]:
    vals = [int(x) for x in ne] + [1, 1, 1, 1]
    return (vals[0], vals[1], vals[2], vals[3])


def verify_streaming_gguf_dry_run_parity(
    target_k: int = 320,
    donor_dir: Path = DONOR_DIR,
    ref_gguf: Path = REF_205E_GGUF,
) -> Dict[str, Any]:
    """OPUS Audit #90 Item 3: Dry-run StreamingPrunedQwen4ExpModel with synthetic keep=range(K)
    and diff all 1,086 tensor names, shapes, and dtypes against BOTH:
      1) upstream Qwen4ExpTextModel(ftype=MOSTLY_BF16, dry_run=True) (512 -> target_k), and
      2) SmartLLM-205E-IQ3_XXS.gguf header (205 -> target_k)."""
    ref_reader = gguf.GGUFReader(str(ref_gguf), "r")
    ref_map = {t.name: (tuple(int(x) for x in t.shape), t.tensor_type) for t in ref_reader.tensors}
    exp_field = ref_reader.fields["qwen4exp.expert_count"]
    ref_k = int(exp_field.parts[exp_field.data[0]][0])

    raw_hp = dict(Qwen4ExpTextModel.load_hparams(Path(donor_dir), False))
    top_arch = raw_hp.get("architectures")
    if "text_config" in raw_hp and isinstance(raw_hp["text_config"], dict):
        tc0 = dict(raw_hp["text_config"])
        if tc0.get("architectures") is None:
            tc0.pop("architectures", None)
        donor_hp = {**raw_hp, **tc0, "text_config": tc0}
    else:
        donor_hp = dict(raw_hp)
    if top_arch:
        donor_hp["architectures"] = top_arch

    donor_k = int(donor_hp["num_experts"])
    n_layers = int(donor_hp["num_hidden_layers"])
    total_blocks = n_layers + int(donor_hp.get("num_nextn_predict_layers", 1) or 0)
    keep = np.arange(int(target_k), dtype=np.int64)
    overlays = {bid: LayerPruneHealOverlay(bid=bid, keep_indices=keep) for bid in range(total_blocks)}

    # 1. Upstream stock Qwen4ExpTextModel dry-run (512E MOSTLY_BF16)
    stock_conv = Qwen4ExpTextModel(
        dir_model=Path(donor_dir),
        ftype=gguf.LlamaFileType.MOSTLY_BF16,
        fname_out=Path("/tmp/dry_run_stock_unused.gguf"),
        is_big_endian=False,
        use_temp_file=False,
        eager=False,
        metadata_override=None,
        model_name="Qwen4ExpStockDryRun",
        split_max_tensors=0,
        split_max_size=0,
        dry_run=True,
        small_first_shard=False,
        hparams=donor_hp,
    )
    stock_conv.prepare_tensors()
    stock_tensors = stock_conv.gguf_writer.tensors[0]

    # 2. StreamingPrunedQwen4ExpModel dry-run (target_k MOSTLY_BF16)
    conv = StreamingPrunedQwen4ExpModel(
        dir_model=Path(donor_dir),
        ftype=gguf.LlamaFileType.MOSTLY_BF16,
        fname_out=Path("/tmp/dry_run_unused.gguf"),
        target_k=int(target_k),
        overlays=overlays,
        reuse_ple_gguf=Path(ref_gguf),
        reuse_vocab_gguf=Path(ref_gguf),
        dry_run=True,
    )
    conv.prepare_tensors()
    conv.prepare_metadata(vocab_only=False)
    dry_tensors = conv.gguf_writer.tensors[0]

    # Check A: Exact 1-to-1 parity vs stock Qwen4ExpTextModel(MOSTLY_BF16)
    stock_missing = sorted(set(stock_tensors.keys()) - set(dry_tensors.keys()))
    stock_extra = sorted(set(dry_tensors.keys()) - set(stock_tensors.keys()))
    if stock_missing or stock_extra:
        raise ValueError(f"Dry-run vs stock Qwen4ExpTextModel mismatch! missing={stock_missing[:10]}, extra={stock_extra[:10]}")

    shape_mismatches: List[str] = []
    type_mismatches: List[str] = []
    for t_name, st_ti in stock_tensors.items():
        ti = dry_tensors[t_name]
        st_ne = tuple(int(x) for x in reversed(st_ti.shape))
        dry_ne = tuple(int(x) for x in reversed(ti.shape))
        exp_st_ne = list(st_ne)
        if t_name.endswith((".ffn_gate_exps.weight", ".ffn_up_exps.weight", ".ffn_down_exps.weight")):
            assert exp_st_ne[2] == donor_k
            exp_st_ne[2] = int(target_k)
        elif t_name.endswith(".ffn_gate_inp.weight"):
            assert exp_st_ne[1] == donor_k
            exp_st_ne[1] = int(target_k)
        if dry_ne != tuple(exp_st_ne):
            shape_mismatches.append(f"[vs stock] {t_name}: got {dry_ne}, expected {tuple(exp_st_ne)}")
        if ti.dtype != st_ti.dtype:
            type_mismatches.append(f"[vs stock] {t_name}: got {ti.dtype.name}, expected {st_ti.dtype.name}")

    # Check B: Parity vs SmartLLM-205E-IQ3_XXS.gguf header (ggml canonical ne4 + pre-quantize types)
    missing = sorted(set(ref_map.keys()) - set(dry_tensors.keys()))
    extra = sorted(set(dry_tensors.keys()) - set(ref_map.keys()))
    if missing or extra:
        raise ValueError(f"GGUF dry-run tensor name mismatch vs 205E! missing={missing[:10]}, extra={extra[:10]}")

    for t_name, (ref_ne, ref_qt) in ref_map.items():
        ti = dry_tensors[t_name]
        dry_ne = tuple(int(x) for x in reversed(ti.shape))
        expected_ne_list = list(ref_ne)
        if t_name.endswith((".ffn_gate_exps.weight", ".ffn_up_exps.weight", ".ffn_down_exps.weight")):
            assert expected_ne_list[2] == ref_k
            expected_ne_list[2] = int(target_k)
        elif t_name.endswith(".ffn_gate_inp.weight"):
            assert expected_ne_list[1] == ref_k
            expected_ne_list[1] = int(target_k)
            if ti.dtype != gguf.GGMLQuantizationType.F32:
                type_mismatches.append(f"{t_name}: router expected F32, got {ti.dtype.name}")
        # Note: llama-quantize trims trailing 1-dims (e.g. ffn_gate_inp_shexp [2560, 1] -> [2560]),
        # so canonical 4D ggml ne=(ne0, ne1, ne2, ne3) must match identically.
        if _canonical_ggml_ne4(dry_ne) != _canonical_ggml_ne4(expected_ne_list):
            shape_mismatches.append(f"[vs 205E] {t_name}: got {dry_ne}, expected {tuple(expected_ne_list)}")

        if t_name == "per_layer_token_embd.weight":
            if ti.dtype != gguf.GGMLQuantizationType.Q4_0:
                type_mismatches.append(f"{t_name}: expected Q4_0, got {ti.dtype.name}")
        elif ref_qt == gguf.GGMLQuantizationType.F32:
            if ti.dtype != gguf.GGMLQuantizationType.F32:
                type_mismatches.append(f"{t_name}: expected F32, got {ti.dtype.name}")
        elif ref_qt == gguf.GGMLQuantizationType.F16:
            # llama-quantize tensor_type_fallback (llama-quant.cpp:469) converts BF16 tensors with
            # ne[0] % 32 != 0 (such as blk.1.ple_conv1d.weight with ne[0]=4) to F16 during quantization.
            if dry_ne[0] % 32 != 0:
                if ti.dtype not in (gguf.GGMLQuantizationType.BF16, gguf.GGMLQuantizationType.F16):
                    type_mismatches.append(f"{t_name}: expected BF16/F16 pre-fallback, got {ti.dtype.name}")
            elif ti.dtype != gguf.GGMLQuantizationType.F16:
                type_mismatches.append(f"{t_name}: expected F16, got {ti.dtype.name}")
        else:
            if ti.dtype != gguf.GGMLQuantizationType.BF16:
                type_mismatches.append(f"{t_name}: expected BF16 pre-quantize, got {ti.dtype.name}")

    if shape_mismatches or type_mismatches:
        raise ValueError(
            f"GGUF dry-run parity failed! shape_mismatches={shape_mismatches[:10]}, type_mismatches={type_mismatches[:10]}"
        )

    total_bf16_bytes = int(sum(ti.nbytes for ti in dry_tensors.values()))
    return {
        "passed": True,
        "tensor_count": len(dry_tensors),
        "stock_parity_exact": True,
        "ref_205e_parity_exact": True,
        "ref_expert_count": ref_k,
        "donor_expert_count": donor_k,
        "target_k": int(target_k),
        "projected_bf16_payload_bytes": total_bf16_bytes,
        "projected_bf16_payload_gib": round(total_bf16_bytes / (1024.0**3), 3),
    }


def verify_imatrix_coverage_against_gguf(
    imatrix_sum2_shapes: Dict[str, Tuple[int, ...]],
    imatrix_count_shapes: Dict[str, Tuple[int, ...]],
    ref_gguf: Path = REF_205E_GGUF,
    expected_k: int = 320,
    check_completeness: bool = True,
) -> Dict[str, Any]:
    """OPUS Audit #90 Item 2a: Verify imatrix keys map 1-to-1 to GGUF tensor names, ne0 dims, and 3-D K counts."""
    reader = gguf.GGUFReader(str(ref_gguf), "r")
    t_map = {t.name: (tuple(int(x) for x in t.shape), t.tensor_type) for t in reader.tensors}

    errors: List[str] = []
    for k_name, s2_shape in sorted(imatrix_sum2_shapes.items()):
        if k_name not in t_map:
            errors.append(f"Unknown imatrix tensor key not in GGUF: {k_name}")
            continue
        ne, _qt = t_map[k_name]
        ne0 = int(ne[0])
        c_shape = imatrix_count_shapes.get(k_name, ())
        if len(ne) == 3:
            if s2_shape != (int(expected_k), ne0):
                errors.append(f"3D sum2 shape mismatch on {k_name}: got {s2_shape}, expected {(int(expected_k), ne0)}")
            if c_shape != (int(expected_k),):
                errors.append(f"3D counts shape mismatch on {k_name}: got {c_shape}, expected {(int(expected_k),)}")
        else:
            if s2_shape != (ne0,):
                errors.append(f"2D sum2 shape mismatch on {k_name}: got {s2_shape}, expected {(ne0,)}")
            if c_shape != (1,):
                errors.append(f"2D counts shape mismatch on {k_name}: got {c_shape}, expected (1,)")

    missing_quantizable: List[str] = []
    if check_completeness:
        skip_types = {gguf.GGMLQuantizationType.F32, gguf.GGMLQuantizationType.F16, gguf.GGMLQuantizationType.BF16}
        for t_name, (_ne, qt) in sorted(t_map.items()):
            if t_name == "per_layer_token_embd.weight" or qt in skip_types:
                continue
            if t_name not in imatrix_sum2_shapes:
                missing_quantizable.append(t_name)
        if missing_quantizable:
            errors.append(f"Missing imatrix entries for {len(missing_quantizable)} quantizable tensors: {missing_quantizable[:10]}")

    if errors:
        raise ValueError("imatrix GGUF coverage check FAILED:\n" + "\n".join(errors[:20]))
    return {
        "passed": True,
        "checked_keys": len(imatrix_sum2_shapes),
        "expected_k": int(expected_k),
        "missing_quantizable_count": len(missing_quantizable),
    }


def assemble_bf16_intermediate_gguf(
    out_gguf_path: Path,
    target_k: int,
    overlays: Dict[int, LayerPruneHealOverlay],
    donor_dir: Path = DONOR_DIR,
    reuse_ple_gguf: Optional[Path] = REF_205E_GGUF,
    reuse_vocab_gguf: Optional[Path] = REF_205E_GGUF,
    model_name: Optional[str] = None,
) -> Path:
    """Stream donor safetensors + keep_indices + C3 heals + verbatim Q4_0 PLE into BF16 GGUF."""
    out_p = Path(out_gguf_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    converter = StreamingPrunedQwen4ExpModel(
        dir_model=Path(donor_dir),
        ftype=gguf.LlamaFileType.MOSTLY_BF16,
        fname_out=out_p,
        target_k=int(target_k),
        overlays=overlays,
        reuse_ple_gguf=reuse_ple_gguf,
        reuse_vocab_gguf=reuse_vocab_gguf,
        model_name=model_name,
    )
    converter.write()
    reader = gguf.GGUFReader(str(out_p), "r")
    marker_p = bf16_gguf_complete_marker_path(out_p)
    tmp_m = marker_p.with_suffix(".tmp.json")
    tmp_m.write_text(
        json.dumps(
            {
                "gguf_path": str(out_p),
                "exact_bytes": int(out_p.stat().st_size),
                "tensor_count": int(len(reader.tensors)),
                "expert_count": int(target_k),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    os.replace(tmp_m, marker_p)
    return out_p


def build_tensor_type_overrides(spec: QuantVariantSpec) -> List[str]:
    """Return exact --tensor-type rules conforming to OPUS_MASTER_PLAN_V2 §1.D1 & Audit #90 Item 6."""
    rules = [
        "per_layer_token_embd.weight=q4_0",
        "token_embd.weight=iq3_s",
        "output.weight=q6_k",
        "output_hc_down.weight=q6_k",
        "output_hc_up.weight=q8_0",
        r"blk\.\d+\.attn_q\.weight=q4_k",
        r"blk\.\d+\.attn_k\.weight=q4_k",
        r"blk\.\d+\.attn_v\.weight=q4_k",
        r"blk\.\d+\.attn_output\.weight=iq3_s",
        r"blk\.\d+\.attn_qkv_gate\.weight=q4_k",
        r"blk\.\d+\.hc_attn_down_inject\.weight=q6_k",
        r"blk\.\d+\.hc_attn_up\.weight=q8_0",
        r"blk\.\d+\.hc_ffn_down_inject\.weight=q6_k",
        r"blk\.\d+\.hc_ffn_up\.weight=q8_0",
        r"blk\.\d+\.indexer\.q_proj\.weight=bf16",
        r"blk\.\d+\.indexer\.k_proj\.weight=bf16",
        r"blk\.\d+\.ssm_beta_alpha\.weight=iq3_xxs",
        r"blk\.\d+\.ssm_out\.weight=iq3_xxs",
        r"blk\.\d+\.ple_key\.weight=q8_0",
        r"blk\.\d+\.ple_value\.weight=q8_0",
        r"blk\.\d+\.nextn\.eh_proj\.weight=q8_0",
        r"blk\.\d+\.nextn\.hc_head_down\.weight=q6_k",
        r"blk\.\d+\.nextn\.hc_head_up\.weight=q8_0",
        r"blk\.\d+\.ffn_gate_shexp\.weight=q5_k",
        r"blk\.\d+\.ffn_up_shexp\.weight=q5_k",
        r"blk\.\d+\.ffn_down_shexp\.weight=q8_0",
        rf"blk\.\d+\.ffn_gate_exps\.weight={spec.gate_up_exps_qtype}",
        rf"blk\.\d+\.ffn_up_exps\.weight={spec.gate_up_exps_qtype}",
        rf"blk\.\d+\.ffn_down_exps\.weight={spec.down_exps_qtype}",
    ]
    return rules


def check_quantize_log_for_missing_imatrix(log_text: str) -> None:
    """OPUS Audit #90 Item 2b: Fail if llama-quantize reports missing/mismatched imatrix weights."""
    bad_lines: List[str] = []
    for line in log_text.splitlines():
        ll = line.lower()
        if "did not find weights for" in ll and ".ple_conv1d.weight" in ll:
            continue
        if (
            "did not find weights for" in ll
            or "missing importance matrix" in ll
            or "imatrix size" in ll
        ):
            bad_lines.append(line.strip())
    if bad_lines:
        raise RuntimeError(
            "llama-quantize reported missing or mismatched importance matrix entries:\n"
            + "\n".join(bad_lines[:20])
        )


def run_llama_quantize_variant(
    src_bf16_gguf: Path,
    dst_gguf: Path,
    imatrix_gguf: Path,
    spec: QuantVariantSpec,
    n_threads: int = 16,
    max_buffer_mib: int = 2048,
    quantize_bin: Optional[Path] = None,
) -> Path:
    """Invoke native llama-quantize with imatrix, exact per-tensor types, and bounded RAM buffer."""
    qbin = Path(quantize_bin) if quantize_bin is not None else find_llama_bin("llama-quantize")
    src_p = Path(src_bf16_gguf)
    imat_p = Path(imatrix_gguf)
    dst_p = Path(dst_gguf)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    quant_log_path = dst_p.with_suffix(dst_p.suffix + ".quantize.log")

    cmd: List[str] = [
        str(qbin),
        "--imatrix",
        str(imat_p),
        "--max-buffer-size",
        str(int(max_buffer_mib)),
    ]
    for rule in build_tensor_type_overrides(spec):
        cmd.extend(["--tensor-type", rule])
    cmd.extend([str(src_p), str(dst_p), spec.base_ftype, str(int(n_threads))])

    drop_file_page_cache(src_p)
    drop_file_page_cache(imat_p)

    stop_evt = threading.Event()

    def _page_cache_reaper() -> None:
        while not stop_evt.wait(0.5):
            try:
                drop_file_page_cache(src_p)
                if dst_p.is_file():
                    drop_file_page_cache(dst_p)
            except Exception:
                pass

    reaper = threading.Thread(target=_page_cache_reaper, daemon=True)
    with open(quant_log_path, "w", encoding="utf-8") as qlog_fp:
        proc = subprocess.Popen(cmd, stdout=qlog_fp, stderr=subprocess.STDOUT, text=True)
        reaper.start()
        try:
            rc = proc.wait()
        finally:
            stop_evt.set()
            reaper.join(timeout=5.0)

    drop_file_page_cache(src_p)
    if dst_p.is_file():
        drop_file_page_cache(dst_p)

    combined_out = quant_log_path.read_text(encoding="utf-8", errors="replace") if quant_log_path.is_file() else ""
    if rc != 0:
        raise RuntimeError(
            f"llama-quantize failed (rc={rc}):\nLOG ({quant_log_path}):\n{combined_out[-2000:]}"
        )
    check_quantize_log_for_missing_imatrix(combined_out)
    return dst_p


def splice_gsq_q2_0_into_gguf(
    gguf_path: Path,
    q2_0_bins_by_layer: Dict[int, Path | np.ndarray],
    verify_with_libggml: bool = True,
    check_semantic_cosine: bool = True,
    min_expert_cosine: float = 0.55,
    ref_bf16_gguf: Optional[Path] = None,
    min_bf16_cosine: float = 0.80,
) -> Dict[str, Any]:
    """Overwrite blk.{bid}.ffn_down_exps.weight in-place with clean-room GSQ Q2_0 payloads.

    Verifies exact GGUF tensor_type == Q2_0 (42), shape, byte size, semantic per-expert
    cosine BEFORE pwrite against stock llama-quantize Q2_0 (>= 0.55; note stock Q2_0 itself has
    only ~0.77 cos vs BF16, so cos(GSQ, stock_Q2_0) ~ 0.65-0.80 while transposed/misordered is ~0.00)
    AND optionally against ref_bf16_gguf ground-truth BF16 weights (>= 0.80, typically 0.90-0.93)
    (OPUS Audit #90 Item 1), plus post-write libggml dequant match.
    """
    target_p = Path(gguf_path)
    reader = gguf.GGUFReader(str(target_p), "r")

    t_map = {t.name: t for t in reader.tensors}
    bf16_reader: Any = None
    bf16_map: Optional[Dict[str, Any]] = None
    bf16_fd: Optional[int] = None
    if ref_bf16_gguf is not None and Path(ref_bf16_gguf).is_file():
        bf16_reader = gguf.GGUFReader(str(ref_bf16_gguf), "r")
        bf16_map = {t.name: t for t in bf16_reader.tensors}
        bf16_fd = os.open(str(ref_bf16_gguf), os.O_RDONLY)

    sim = LibGGMLQuantSimulator() if verify_with_libggml else None

    fd = os.open(str(target_p), os.O_RDWR)
    spliced_layers = 0
    total_bytes_written = 0
    min_observed_expert_cos = 1.0
    min_observed_bf16_cos = 1.0
    try:
        for bid in sorted(q2_0_bins_by_layer.keys()):
            t_name = f"blk.{bid}.ffn_down_exps.weight"
            if t_name not in t_map:
                raise KeyError(f"Missing {t_name} in {target_p}")
            t_info = t_map[t_name]
            if int(t_info.tensor_type) != GGML_TYPE_Q2_0:
                raise ValueError(
                    f"{t_name} has type {t_info.tensor_type} ({t_info.tensor_type.name}), expected Q2_0 (42)"
                )

            src_item = q2_0_bins_by_layer[bid]
            if isinstance(src_item, np.ndarray):
                raw_bytes = np.ascontiguousarray(src_item, dtype=np.uint8).tobytes()
            else:
                with open(src_item, "rb") as bf:
                    raw_bytes = bf.read()

            expected_bytes = int(t_info.n_bytes)
            if len(raw_bytes) != expected_bytes:
                raise ValueError(
                    f"Byte size mismatch on {t_name}: GSQ payload={len(raw_bytes)} B vs GGUF slot={expected_bytes} B"
                )

            # Note: gguf_reader.py:353 sets t_info.data_offset to the absolute file byte offset
            abs_off = int(t_info.data_offset)

            # OPUS Audit #90 Item 1: Semantic splice check BEFORE pwrite on >= 2 experts/layer.
            if check_semantic_cosine and len(t_info.shape) == 3:
                n_experts = int(t_info.shape[2])
                expert_bytes = expected_bytes // max(1, n_experts)
                check_exps = sorted({0, min(1, n_experts - 1), n_experts // 2, n_experts - 1})
                for e_idx in check_exps:
                    e_off = int(e_idx) * expert_bytes
                    stock_e_raw = os.pread(fd, expert_bytes, abs_off + e_off)
                    if len(stock_e_raw) != expert_bytes:
                        raise IOError(f"Short pread on stock {t_name} expert {e_idx}")
                    dq_stock = dequantize_q2_0_cleanroom(np.frombuffer(stock_e_raw, dtype=np.uint8)).astype(np.float64)
                    dq_gsq = dequantize_q2_0_cleanroom(
                        np.frombuffer(raw_bytes[e_off : e_off + expert_bytes], dtype=np.uint8)
                    ).astype(np.float64)
                    n_stock = float(np.linalg.norm(dq_stock))
                    n_gsq = float(np.linalg.norm(dq_gsq))
                    if n_stock <= 1e-12 or n_gsq <= 1e-12:
                        raise ValueError(
                            f"Semantic splice check failed on {t_name} expert {e_idx}: zero norm (stock={n_stock}, gsq={n_gsq})"
                        )
                    cos_e = float(np.dot(dq_stock, dq_gsq) / (n_stock * n_gsq))
                    min_observed_expert_cos = min(min_observed_expert_cos, cos_e)
                    if cos_e < float(min_expert_cosine):
                        raise ValueError(
                            f"Semantic splice check FAILED on {t_name} expert {e_idx}: "
                            f"cos(GSQ, stock_Q2_0)={cos_e:.6f} < {min_expert_cosine:.2f}; aborting before pwrite!"
                        )

                    if bf16_map is not None and bf16_fd is not None and t_name in bf16_map:
                        tb = bf16_map[t_name]
                        if tb.tensor_type == gguf.GGMLQuantizationType.BF16:
                            bf16_exp_bytes = int(tb.n_bytes) // max(1, n_experts)
                            bf16_raw = os.pread(bf16_fd, bf16_exp_bytes, int(tb.data_offset) + int(e_idx) * bf16_exp_bytes)
                            w_bf16 = (
                                torch.frombuffer(bytearray(bf16_raw), dtype=torch.bfloat16)
                                .to(torch.float32)
                                .numpy()
                                .astype(np.float64)
                            )
                            n_bf16 = float(np.linalg.norm(w_bf16))
                            cos_bf16 = float(np.dot(w_bf16, dq_gsq) / (max(n_bf16, 1e-12) * n_gsq))
                            min_observed_bf16_cos = min(min_observed_bf16_cos, cos_bf16)
                            if cos_bf16 < float(min_bf16_cosine):
                                raise ValueError(
                                    f"Semantic BF16 splice check FAILED on {t_name} expert {e_idx}: "
                                    f"cos(GSQ, BF16)={cos_bf16:.6f} < {min_bf16_cosine:.2f}; aborting before pwrite!"
                                )
                            drop_fd_page_cache(bf16_fd, offset=int(tb.data_offset) + int(e_idx) * bf16_exp_bytes, length=bf16_exp_bytes)

            written = os.pwrite(fd, raw_bytes, abs_off)
            if written != expected_bytes:
                raise IOError(f"Short pwrite on {t_name}: {written} != {expected_bytes}")
            os.fsync(fd)

            # Immediate readback & bit-exact dequant verification on first 2 rows (1280 weights)
            sample_n_blocks = min(20, expected_bytes // BLOCK_Q2_0_BYTES)
            sample_bytes = sample_n_blocks * BLOCK_Q2_0_BYTES
            rb = os.pread(fd, sample_bytes, abs_off)
            if rb != raw_bytes[:sample_bytes]:
                raise RuntimeError(f"Readback byte mismatch on {t_name}")
            if sim is not None:
                rb_u8 = np.frombuffer(rb, dtype=np.uint8)
                dq_clean = dequantize_q2_0_cleanroom(rb_u8)
                dq_c = sim.dequantize_bytes(rb_u8, GGML_TYPE_Q2_0, n_elems=sample_n_blocks * QK2_0)
                if not np.array_equal(dq_clean.view(np.uint32), dq_c.view(np.uint32)):
                    raise RuntimeError(f"libggml-base.so Q2_0 dequant mismatch on {t_name}")

            drop_fd_page_cache(fd, offset=abs_off, length=expected_bytes)
            spliced_layers += 1
            total_bytes_written += expected_bytes
    finally:
        os.close(fd)
        if bf16_fd is not None:
            os.close(bf16_fd)

    reader = None
    bf16_reader = None
    gc.collect()
    drop_file_page_cache(target_p)
    if ref_bf16_gguf is not None and Path(ref_bf16_gguf).is_file():
        drop_file_page_cache(Path(ref_bf16_gguf))

    return {
        "gguf_path": str(target_p),
        "spliced_layers": spliced_layers,
        "total_bytes_written": total_bytes_written,
        "min_semantic_expert_cosine": round(float(min_observed_expert_cos), 6),
        "min_semantic_bf16_cosine": round(float(min_observed_bf16_cos), 6) if bf16_map is not None else None,
    }
