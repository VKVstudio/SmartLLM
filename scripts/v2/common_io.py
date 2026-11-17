#!/usr/bin/env python3
"""Shared Linux-native I/O, pure-PyTorch meta materialization, ping-pong activation
stores, qwen4_exp helpers, and GGUF imatrix writer for SmartLLM v2 (WP-C1).

Key invariants:
- Zero accelerate dependency (pure PyTorch parameter/buffer placement).
- Explicit os.posix_fadvise(..., POSIX_FADV_DONTNEED) after donor shard reads and
  sequential activation / GGUF writes to keep Linux page cache bounded and pswpout == 0.
- PLE (per_layer_token_embd) never stays resident in RAM.
"""

from __future__ import annotations

import gc
import hashlib
import json
import math
import os
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from safetensors import safe_open

REPO_ROOT = Path("/mnt/rescue/projects/SmartLLM")
ROOT_DIR = REPO_ROOT
GGUF_PY_PATH = REPO_ROOT / "tools" / "llama.cpp" / "gguf-py"
if str(GGUF_PY_PATH) not in sys.path:
    sys.path.insert(0, str(GGUF_PY_PATH))

import gguf  # noqa: E402

DONOR_DIR = REPO_ROOT / "models" / "Qwen3.8-Flash-Next"
REF_205E_GGUF = REPO_ROOT / "models" / "SmartLLM-205E-IQ3_XXS.gguf"
MMPROJ_GGUF = REPO_ROOT / "models" / "mmproj-Qwen3.8-Flash-Next-BF16.gguf"
_CACHE_BASE = Path(os.environ.get("SMARTLLM_CACHE_DIR", str(Path.home() / ".cache" / "smartllm")))
STAGE_DIR = _CACHE_BASE / "v2_stage"
SCRATCH_DIR = Path(os.environ.get("SMARTLLM_SCRATCH_DIR", "/mnt/windows/smartllm_scratch"))
RUNS_DIR = REPO_ROOT / "research" / "v2_runs"
LLAMA_CPU_GGML_SO = _CACHE_BASE / "llama_cpu_ggml" / "bin" / "libggml-base.so"
LLAMA_BUILD_BIN_CANDIDATES = (
    _CACHE_BASE / "llama_build" / "bin",
    REPO_ROOT / "tools" / "llama.cpp" / "build_linux" / "bin",
)

POSIX_FADV_DONTNEED = getattr(os, "POSIX_FADV_DONTNEED", 4)
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def find_llama_bin(binary_name: str) -> Path:
    """Locate a compiled native Linux llama.cpp binary (e.g. llama-quantize)."""
    for cand_dir in LLAMA_BUILD_BIN_CANDIDATES:
        p = cand_dir / binary_name
        if p.is_file() and os.access(p, os.X_OK):
            return p
    raise FileNotFoundError(
        f"Native Linux binary {binary_name!r} not found in {LLAMA_BUILD_BIN_CANDIDATES}"
    )


def drop_fd_page_cache(fd: int, offset: int = 0, length: int = 0) -> None:
    """Advise the Linux kernel to drop clean page-cache pages immediately."""
    if hasattr(os, "posix_fadvise"):
        try:
            os.posix_fadvise(fd, int(offset), int(length), POSIX_FADV_DONTNEED)
        except OSError:
            pass


def drop_file_page_cache(path: Path | str, offset: int = 0, length: int = 0) -> None:
    """Open file read-only, issue POSIX_FADV_DONTNEED, and close."""
    p = Path(path)
    if not p.is_file():
        return
    try:
        fd = os.open(str(p), os.O_RDONLY)
        try:
            drop_fd_page_cache(fd, offset=offset, length=length)
        finally:
            os.close(fd)
    except OSError:
        pass


from scripts.infra.sla_watchdog import (
    SwapBaseline,
    capture_swap_baseline,
    evaluate_swap_and_mem_sla,
)

DEFAULT_GPU_RUNS_LOG = REPO_ROOT / ".system" / "gpu_runs.log"
_PROCESS_SWAP_BASELINE: Optional[SwapBaseline] = None


@dataclass
class LinuxMemTelemetry:
    mem_total_gib: float
    mem_available_gib: float
    cached_gib: float
    swap_total_gib: float
    swap_used_gib: float
    pswpin: int
    pswpout: int
    disk_swap_used_kb: int = 0
    disk_swap_write_sectors: int = 0
    zram_orig_mib: float = 0.0


def capture_v2_swap_baseline() -> SwapBaseline:
    """Capture a fresh SwapBaseline via Single-Source-of-Truth sla_watchdog and set process baseline."""
    global _PROCESS_SWAP_BASELINE
    sw = capture_swap_baseline()
    if _PROCESS_SWAP_BASELINE is None:
        _PROCESS_SWAP_BASELINE = sw
    return sw


def read_linux_mem_telemetry() -> LinuxMemTelemetry:
    """Read /proc/meminfo and OPUS §0.3a swap/zram telemetry via sla_watchdog."""
    global _PROCESS_SWAP_BASELINE
    info: Dict[str, int] = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                info[parts[0].rstrip(":")] = int(parts[1])  # kB

    sw = capture_swap_baseline()
    if _PROCESS_SWAP_BASELINE is None:
        _PROCESS_SWAP_BASELINE = sw

    kb_to_gib = 1.0 / (1024.0 * 1024.0)
    swap_total = info.get("SwapTotal", 0)
    swap_free = info.get("SwapFree", 0)
    return LinuxMemTelemetry(
        mem_total_gib=info.get("MemTotal", 0) * kb_to_gib,
        mem_available_gib=info.get("MemAvailable", 0) * kb_to_gib,
        cached_gib=info.get("Cached", 0) * kb_to_gib,
        swap_total_gib=swap_total * kb_to_gib,
        swap_used_gib=max(0, swap_total - swap_free) * kb_to_gib,
        pswpin=sw.pswpin,
        pswpout=sw.pswpout,
        disk_swap_used_kb=sw.disk_swap_used_kb,
        disk_swap_write_sectors=sw.disk_swap_write_sectors,
        zram_orig_mib=sw.zram_orig_mib,
    )


def assert_zero_swap_and_mem(
    baseline_pswpout: SwapBaseline | int | None = None,
    min_avail_gib: float = 3.0,
    max_proc_swap_mib: float = 256.0,
) -> LinuxMemTelemetry:
    """Enforce OPUS §0.3a Zero-Disk-Swap & memory SLA via shared sla_watchdog."""
    global _PROCESS_SWAP_BASELINE
    if isinstance(baseline_pswpout, SwapBaseline):
        eff_base = baseline_pswpout
    else:
        if _PROCESS_SWAP_BASELINE is None:
            _PROCESS_SWAP_BASELINE = capture_swap_baseline()
        if isinstance(baseline_pswpout, int):
            eff_base = replace(_PROCESS_SWAP_BASELINE, pswpout=int(baseline_pswpout))
        else:
            eff_base = _PROCESS_SWAP_BASELINE

    sla = evaluate_swap_and_mem_sla(
        eff_base,
        root_pid=os.getpid(),
        min_mem_avail_gib=min_avail_gib,
        max_proc_swap_mib=max_proc_swap_mib,
    )
    if not sla["passed"]:
        raise RuntimeError(f"SLA §0.3a invariant breached: {sla['breach_reason']}")
    return read_linux_mem_telemetry()


def compare_files_byte_equal(path_a: Path | str, path_b: Path | str, chunk_bytes: int = 16 * 1024 * 1024) -> bool:
    """Compare two binary files byte-for-byte in bounded chunks while dropping VFS page cache."""
    pa = Path(path_a)
    pb = Path(path_b)
    if not (pa.is_file() and pb.is_file()):
        return False
    sz_a = int(pa.stat().st_size)
    sz_b = int(pb.stat().st_size)
    if sz_a != sz_b:
        return False
    if sz_a == 0:
        return True
    fd_a = os.open(str(pa), os.O_RDONLY)
    fd_b = os.open(str(pb), os.O_RDONLY)
    try:
        off = 0
        while off < sz_a:
            n_read = min(chunk_bytes, sz_a - off)
            buf_a = os.pread(fd_a, n_read, off)
            buf_b = os.pread(fd_b, n_read, off)
            drop_fd_page_cache(fd_a, off, n_read)
            drop_fd_page_cache(fd_b, off, n_read)
            if len(buf_a) != n_read or buf_a != buf_b:
                return False
            off += n_read
    finally:
        os.close(fd_a)
        os.close(fd_b)
    return True


def append_gpu_resume_log(
    pipeline: str,
    resume_bid: int,
    cur_slot: str,
    verified_files: Dict[str, int],
    probe_mode: str,
    probe_max_rel_l2: float,
    log_path: Path = DEFAULT_GPU_RUNS_LOG,
) -> str:
    """Append a structured OPUS §0.3a.4 [RESUME] entry to .system/gpu_runs.log and stdout."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "ts": ts,
        "event": "RESUME",
        "pipeline": str(pipeline),
        "resume_bid": int(resume_bid),
        "cur_slot": str(cur_slot),
        "probe_mode": str(probe_mode),
        "probe_max_rel_l2": round(float(probe_max_rel_l2), 8),
        "verified_files_bytes": {str(k): int(v) for k, v in verified_files.items()},
    }
    line = f"[RESUME] {json.dumps(payload, sort_keys=True)}"
    lp = Path(log_path)
    lp.parent.mkdir(parents=True, exist_ok=True)
    with lp.open("a", encoding="utf-8") as lf:
        lf.write(line + "\n")
        lf.flush()
    print(line, flush=True)
    return line


def compute_file_sha256_streaming(
    path: Path | str,
    chunk_bytes: int = 32 * 1024 * 1024,
    drop_cache: bool = True,
) -> str:
    """Compute SHA-256 of a large binary file via os.pread + POSIX_FADV_DONTNEED (0 B cache bloat)."""
    p = Path(path)
    sz = int(p.stat().st_size)
    h = hashlib.sha256()
    if sz == 0:
        return h.hexdigest()
    fd = os.open(str(p), os.O_RDONLY)
    try:
        off = 0
        while off < sz:
            step = min(chunk_bytes, sz - off)
            buf = os.pread(fd, step, off)
            if len(buf) != step:
                raise EOFError(f"Short pread in compute_file_sha256_streaming on {p}: {len(buf)} != {step}")
            h.update(buf)
            if drop_cache:
                drop_fd_page_cache(fd, offset=off, length=step)
            off += step
    finally:
        os.close(fd)
    return h.hexdigest()


def assert_post_write_free_gib(
    target_path: Path | str,
    expected_bytes: int,
    min_free_gib: float = 10.0,
    label: str = "",
) -> Dict[str, Any]:
    """OPUS §1.D2b.4 storage guard: assert post-write free space >= min_free_gib on target's mount."""
    tp = Path(target_path)
    probe = tp if tp.exists() else tp.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    real_probe = Path(os.path.realpath(probe))
    existing_bytes = int(tp.stat().st_size) if tp.is_file() else 0
    additional_bytes = max(0, int(expected_bytes) - existing_bytes)
    usage = shutil.disk_usage(real_probe)
    free_before_gib = float(usage.free) / (1024.0**3)
    additional_gib = float(additional_bytes) / (1024.0**3)
    projected_free_gib = float(usage.free - additional_bytes) / (1024.0**3)
    info = {
        "label": label or tp.name,
        "target_path": str(tp),
        "mount_probe": str(real_probe),
        "free_before_gib": round(free_before_gib, 3),
        "additional_gib": round(additional_gib, 3),
        "projected_free_after_gib": round(projected_free_gib, 3),
        "min_free_gib": float(min_free_gib),
    }
    print(f"[STORAGE_GUARD] {json.dumps(info, sort_keys=True)}", flush=True)
    if projected_free_gib < float(min_free_gib):
        raise RuntimeError(
            f"OPUS §1.D2b.4 storage guard FAILED for {tp} (mount {real_probe}): "
            f"free_before={free_before_gib:.3f} GiB, additional={additional_gib:.3f} GiB -> "
            f"projected_free_after={projected_free_gib:.3f} GiB < min_free_gib={min_free_gib:.1f} GiB"
        )
    return info


def bf16_to_u16_numpy(t: torch.Tensor) -> np.ndarray:
    """Convert a bfloat16/float tensor to raw bfloat16 uint16 NumPy array."""
    if t.dtype != torch.bfloat16:
        t = t.to(torch.bfloat16)
    return t.detach().cpu().contiguous().view(torch.uint16).numpy()


def u16_numpy_to_bf16(arr: np.ndarray) -> torch.Tensor:
    """View a uint16 NumPy array as a CPU torch.bfloat16 tensor."""
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr)
    return torch.from_numpy(arr).view(torch.bfloat16)


_ST_DTYPE_MAP: Dict[str, Tuple[torch.dtype, int]] = {
    "BF16": (torch.bfloat16, 2),
    "F16": (torch.float16, 2),
    "F32": (torch.float32, 4),
    "F64": (torch.float64, 8),
    "I64": (torch.int64, 8),
    "I32": (torch.int32, 4),
    "I16": (torch.int16, 2),
    "I8": (torch.int8, 1),
    "U8": (torch.uint8, 1),
    "BOOL": (torch.bool, 1),
}
_PREAD_CHUNK_BYTES = 32 * 1024 * 1024  # 32 MiB bounded VFS page-cache window


def _pread_exact_into_mv(
    fd: int,
    mv: memoryview,
    file_offset: int,
    drop_cache: bool = True,
    chunk_bytes: int = _PREAD_CHUNK_BYTES,
) -> None:
    """Read exact bytes from `fd` into `mv` via `os.preadv` in bounded windows without mmap."""
    total = len(mv)
    pos = 0
    while pos < total:
        step = min(chunk_bytes, total - pos)
        sub_off = 0
        while sub_off < step:
            n_read = os.preadv(fd, [mv[pos + sub_off : pos + step]], file_offset + pos + sub_off)
            if n_read <= 0:
                raise EOFError(
                    f"Unexpected EOF in preadv at offset {file_offset + pos + sub_off} "
                    f"(wanted {total} B, got {pos + sub_off} B)"
                )
            sub_off += n_read
        if drop_cache:
            drop_fd_page_cache(fd, offset=file_offset + pos, length=step)
        pos += step


def evict_stage_dir_page_cache(stage_dir: Path | str) -> int:
    """Evict stale clean VFS file-cache pages under `stage_dir` before long runs."""
    p = Path(stage_dir)
    if not p.is_dir():
        return 0
    count = 0
    for fpath in p.rglob("*"):
        if fpath.is_file():
            drop_file_page_cache(fpath)
            count += 1
    return count


class SafetensorsIndex:
    """Linux-native sharded safetensors reader using direct header+preadv (zero full-shard mmap)
    with immediate 32 MiB windowed POSIX_FADV_DONTNEED eviction."""

    def __init__(self, model_dir: Path | str, drop_cache: bool = True) -> None:
        self.model_dir = Path(model_dir)
        self.drop_cache = bool(drop_cache)
        self._header_cache: Dict[str, Tuple[int, Dict[str, Any]]] = {}
        idx_path = self.model_dir / "model.safetensors.index.json"
        if idx_path.is_file():
            with open(idx_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.weight_map: Dict[str, str] = dict(data["weight_map"])
        else:
            single = self.model_dir / "model.safetensors"
            if single.is_file():
                _, hdr = self._get_shard_header("model.safetensors")
                self.weight_map = {k: "model.safetensors" for k in hdr.keys() if k != "__metadata__"}
            else:
                self.weight_map = {}
                for p in sorted(self.model_dir.glob("*.safetensors")):
                    _, hdr = self._get_shard_header(p.name)
                    for k in hdr.keys():
                        if k != "__metadata__":
                            self.weight_map[k] = p.name

    def _get_shard_header(self, shard_name: str) -> Tuple[int, Dict[str, Any]]:
        cached = self._header_cache.get(shard_name)
        if cached is not None:
            return cached
        shard_path = self.model_dir / shard_name
        fd = os.open(str(shard_path), os.O_RDONLY)
        try:
            raw_len = os.pread(fd, 8, 0)
            if len(raw_len) != 8:
                raise EOFError(f"Truncated safetensors header in {shard_path}")
            hdr_len = int.from_bytes(raw_len, byteorder="little", signed=False)
            raw_hdr = os.pread(fd, hdr_len, 8)
            if len(raw_hdr) != hdr_len:
                raise EOFError(f"Truncated safetensors JSON header in {shard_path}")
            if self.drop_cache:
                drop_fd_page_cache(fd, offset=0, length=8 + hdr_len)
        finally:
            os.close(fd)
        hdr = json.loads(raw_hdr.decode("utf-8"))
        res = (8 + hdr_len, hdr)
        self._header_cache[shard_name] = res
        return res

    def get_tensor_info(
        self, name: str
    ) -> Tuple[Path, torch.dtype, int, Tuple[int, ...], int, int]:
        """Return (shard_path, torch_dtype, elem_bytes, shape, abs_byte_offset, byte_length)."""
        shard_name = self.weight_map.get(name)
        if shard_name is None:
            raise KeyError(f"Tensor {name!r} not found in {self.model_dir}")
        data_base, hdr = self._get_shard_header(shard_name)
        meta = hdr.get(name)
        if meta is None:
            raise KeyError(f"Tensor {name!r} missing from header of {shard_name}")
        dt_str = str(meta["dtype"])
        if dt_str not in _ST_DTYPE_MAP:
            raise ValueError(f"Unsupported safetensors dtype {dt_str!r} for {name!r}")
        t_dtype, elem_bytes = _ST_DTYPE_MAP[dt_str]
        shape = tuple(int(d) for d in meta["shape"])
        off_beg, off_end = int(meta["data_offsets"][0]), int(meta["data_offsets"][1])
        return (
            self.model_dir / shard_name,
            t_dtype,
            elem_bytes,
            shape,
            data_base + off_beg,
            off_end - off_beg,
        )

    def keys_with_prefix(self, prefix: str) -> List[str]:
        return [k for k in self.weight_map.keys() if k.startswith(prefix)]

    def load_tensors(
        self,
        names: Iterable[str],
        device: str | torch.device = "cpu",
        dtype: Optional[torch.dtype] = None,
    ) -> Dict[str, torch.Tensor]:
        by_shard: Dict[str, List[str]] = defaultdict(list)
        for name in names:
            shard = self.weight_map.get(name)
            if shard is None:
                raise KeyError(f"Tensor {name!r} not found in {self.model_dir}")
            by_shard[shard].append(name)

        dev_str = str(device)
        out: Dict[str, torch.Tensor] = {}
        for shard_name, shard_keys in by_shard.items():
            shard_path = self.model_dir / shard_name
            # Sort reads within shard by ascending file offset for sequential NVMe preadv
            infos = [(k, *self.get_tensor_info(k)[1:]) for k in shard_keys]
            infos.sort(key=lambda item: item[4])
            fd = os.open(str(shard_path), os.O_RDONLY)
            try:
                for k, t_dtype, _eb, shape, abs_off, nbytes in infos:
                    if nbytes == 0:
                        t = torch.empty(shape, dtype=t_dtype)
                    else:
                        u8 = torch.empty((nbytes,), dtype=torch.uint8)
                        _pread_exact_into_mv(
                            fd,
                            memoryview(u8.numpy()),
                            abs_off,
                            drop_cache=self.drop_cache,
                        )
                        t = u8.view(t_dtype).reshape(shape)
                    if dtype is not None and t.dtype != dtype:
                        t = t.to(dtype)
                    if dev_str != "cpu":
                        t = t.to(device)
                    out[k] = t
                if self.drop_cache:
                    drop_fd_page_cache(fd, offset=0, length=0)
            finally:
                os.close(fd)
        return out

    def load_expert_slice(
        self,
        name: str,
        keep_indices: Sequence[int] | np.ndarray,
        dtype: Optional[torch.dtype] = None,
    ) -> torch.Tensor:
        """Read ONLY the kept dim-0 expert slices via preadv (zero full-tensor allocation or mmap)."""
        shard_path, t_dtype, elem_bytes, shape, abs_off, _nbytes = self.get_tensor_info(name)
        if len(shape) < 2:
            raise ValueError(f"Expected >=2D expert tensor for {name!r}, got shape={shape}")
        idx_list = [int(i) for i in keep_indices]
        k_count = len(idx_list)
        inner_shape = shape[1:]
        expert_elems = 1
        for d in inner_shape:
            expert_elems *= d
        expert_bytes = expert_elems * elem_bytes

        out_u8 = torch.empty((k_count * expert_bytes,), dtype=torch.uint8)
        mv = memoryview(out_u8.numpy())
        fd = os.open(str(shard_path), os.O_RDONLY)
        try:
            pos = 0
            while pos < k_count:
                e_start = idx_list[pos]
                if e_start < 0 or e_start >= shape[0]:
                    raise IndexError(f"Expert index {e_start} out of range [0, {shape[0]}) for {name!r}")
                run_len = 1
                while pos + run_len < k_count and idx_list[pos + run_len] == e_start + run_len:
                    e_next = idx_list[pos + run_len]
                    if e_next < 0 or e_next >= shape[0]:
                        raise IndexError(f"Expert index {e_next} out of range [0, {shape[0]}) for {name!r}")
                    run_len += 1
                dst_off = pos * expert_bytes
                n_read = run_len * expert_bytes
                src_off = abs_off + e_start * expert_bytes
                _pread_exact_into_mv(
                    fd,
                    mv[dst_off : dst_off + n_read],
                    src_off,
                    drop_cache=self.drop_cache,
                )
                pos += run_len
            if self.drop_cache:
                drop_fd_page_cache(fd, offset=0, length=0)
        finally:
            os.close(fd)

        sliced = out_u8.view(t_dtype).reshape((k_count, *inner_shape))
        if dtype is not None and sliced.dtype != dtype:
            sliced = sliced.to(dtype)
        return sliced


def set_module_tensor_pure_torch(
    root_module: nn.Module,
    tensor_path: str,
    value: torch.Tensor,
) -> None:
    """Pure-PyTorch replacement for accelerate.utils.set_module_tensor_to_device."""
    parts = tensor_path.split(".")
    mod = root_module
    for p in parts[:-1]:
        mod = mod[int(p)] if p.isdigit() else getattr(mod, p)
    leaf = parts[-1]
    if leaf in mod._parameters:
        old = mod._parameters[leaf]
        req_grad = False if old is None else bool(old.requires_grad)
        mod._parameters[leaf] = nn.Parameter(value, requires_grad=req_grad)
    elif leaf in mod._buffers:
        mod._buffers[leaf] = value
    else:
        setattr(mod, leaf, nn.Parameter(value, requires_grad=False))


def materialize_submodule(
    root_module: nn.Module,
    sub_prefix: str,
    st_index: SafetensorsIndex,
    device: str | torch.device = "cpu",
    skip_patterns: Sequence[str] = (),
) -> int:
    """Materialize a meta-initialized submodule directly from safetensors shards.

    Works seamlessly whether `root_module` is the top-level model (containing `sub_prefix`
    as a nested submodule path) or is already the standalone submodule at `sub_prefix`.
    """
    full_prefix = f"{sub_prefix}."
    matched = [
        k for k in st_index.keys_with_prefix(full_prefix)
        if not any(pat in k for pat in skip_patterns)
    ]
    loaded = st_index.load_tensors(matched, device=device)

    target_mod: nn.Module = root_module
    resolved = True
    cur: Any = root_module
    for p in sub_prefix.split("."):
        if p.isdigit() and hasattr(cur, "__getitem__") and int(p) < len(cur):
            cur = cur[int(p)]
        elif hasattr(cur, p):
            cur = getattr(cur, p)
        else:
            resolved = False
            break
    if resolved and isinstance(cur, nn.Module):
        target_mod = cur

    for k, val in loaded.items():
        rel_k = k[len(full_prefix) :]
        set_module_tensor_pure_torch(target_mod, rel_k, val)
    n = len(loaded)
    loaded.clear()
    return n


def free_submodule_to_meta(submodule: nn.Module) -> None:
    """Release all materialized parameters and buffers in submodule back to meta."""
    for mod in submodule.modules():
        for k, p in list(mod._parameters.items()):
            if p is not None and p.device.type != "meta":
                mod._parameters[k] = nn.Parameter(
                    torch.empty(p.shape, dtype=p.dtype, device="meta"),
                    requires_grad=False,
                )
        for k, b in list(mod._buffers.items()):
            if b is not None and b.device.type != "meta":
                mod._buffers[k] = torch.empty(b.shape, dtype=b.dtype, device="meta")


@dataclass
class SampleDomainFlags:
    stratum: str
    subbucket: str
    is_ru: bool
    is_copy_craft: bool
    is_vision: bool


def classify_sample_domains(sample: Dict[str, Any]) -> SampleDomainFlags:
    """Deterministically classify calibration/eval records across v1 and v2 schemas."""
    stratum = str(
        sample.get("stratum")
        or sample.get("domain")
        or sample.get("pillar")
        or sample.get("category")
        or "general"
    ).strip().lower()
    subbucket = str(
        sample.get("subbucket") or sample.get("subdomain") or sample.get("subcategory") or ""
    ).strip().lower()
    lang = str(sample.get("lang") or sample.get("language") or "").strip().lower()
    sid = str(sample.get("id") or sample.get("sample_id") or "").strip().lower()
    raw_qtags = sample.get("quota_tags")
    if isinstance(raw_qtags, list):
        qtags = {str(t).strip().lower() for t in raw_qtags}
        return SampleDomainFlags(
            stratum=stratum,
            subbucket=subbucket,
            is_ru=("ru" in qtags) or (lang == "ru"),
            is_copy_craft=("copy_craft" in qtags),
            is_vision=("vision" in qtags) or (str(sample.get("modality") or "").lower() == "multimodal"),
        )

    tags_blob = f"{stratum} {subbucket} {lang} {sid}"
    tag_tokens = set(re.findall(r"[a-z0-9]+", tags_blob))

    is_ru = (
        lang == "ru"
        or "ru" in tag_tokens
        or stratum.startswith("ru")
        or subbucket.startswith("ru")
    )
    if not is_ru:
        txt = str(sample.get("text") or sample.get("prompt") or "")
        if txt:
            alpha = [c for c in txt[:2048] if c.isalpha()]
            if len(alpha) >= 16:
                cyr = len(CYRILLIC_RE.findall("".join(alpha)))
                is_ru = (cyr / len(alpha)) >= 0.15

    craft_tokens = {"copy", "copywriting", "craft", "p4", "ux", "brand", "editorial"}
    is_copy_craft = bool(tag_tokens & craft_tokens) or ("landing_copy" in tags_blob) or ("design_brief" in tags_blob)

    vis_tokens = {"vision", "vis", "mm", "multimodal", "image", "screenshot"}
    has_img_fields = bool(
        sample.get("image")
        or sample.get("images")
        or sample.get("image_path")
        or sample.get("pixel_values") is not None
        or sample.get("has_vision")
        or str(sample.get("modality") or "").lower() == "multimodal"
    )
    is_vision = has_img_fields or bool(tag_tokens & vis_tokens) or ("ui_audit" in tags_blob)
    return SampleDomainFlags(
        stratum=stratum,
        subbucket=subbucket,
        is_ru=is_ru,
        is_copy_craft=is_copy_craft,
        is_vision=is_vision,
    )


class SafeStreamingPLENGramEmbedding(nn.Module):
    """Zero-RAM-resident PLE n-gram hash lookup (streams rows from safetensors shards
    and immediately evicts shard pages via POSIX_FADV_DONTNEED).

    Matches transformers Qwen4ExpTextNGramEmbedding and llama.cpp qwen4exp.cpp:1381-1402
    exact XOR + EOS-context-fill hash semantics.
    """

    def __init__(self, text_cfg: Any, st_index: SafetensorsIndex, ple_prefix: str) -> None:
        super().__init__()
        self.st_index = st_index
        self.ple_prefix = ple_prefix
        self.ple_layer_ids: List[int] = list(text_cfg.ple_layer_ids)
        self.ngram_size: int = int(text_cfg.ngram_size)
        self.context_len: int = self.ngram_size - 1
        self.heads_per_ngram: int = int(text_cfg.heads_per_ngram)
        self.num_heads_per_layer: int = (self.ngram_size - 1) * self.heads_per_ngram
        self.ple_embed_dim: int = int(text_cfg.ple_embed_dim)
        self.head_dim: int = self.ple_embed_dim // self.num_heads_per_layer
        self.split_ngram_parts: int = int(text_cfg.split_ngram_parts)

        eos = text_cfg.eos_token_id
        self.eos_token_id: int = int(eos[0] if isinstance(eos, list) else eos)

        consts = st_index.load_tensors(
            [
                f"{ple_prefix}.layer_multipliers",
                f"{ple_prefix}.ngram_heads_vocab_sizes",
                f"{ple_prefix}.ngram_heads_offsets",
            ],
            device="cpu",
        )
        self.register_buffer("layer_multipliers", consts[f"{ple_prefix}.layer_multipliers"].to(torch.int64))
        self.register_buffer("ngram_heads_vocab_sizes", consts[f"{ple_prefix}.ngram_heads_vocab_sizes"].to(torch.int64))
        self.register_buffer("ngram_heads_offsets", consts[f"{ple_prefix}.ngram_heads_offsets"].to(torch.int64))

        shard0_key = f"{ple_prefix}.ngram_embedding.shard_0.weight"
        unsharded_key = f"{ple_prefix}.ngram_embedding.weight"
        self._is_sharded = shard0_key in st_index.weight_map
        self._embed_dtype = torch.bfloat16

        shard_row_counts: List[int] = []
        if self._is_sharded:
            for s_idx in range(self.split_ngram_parts):
                t_name = f"{ple_prefix}.ngram_embedding.shard_{s_idx}.weight"
                _sp, t_dt, _eb, shape, _off, _nb = st_index.get_tensor_info(t_name)
                shard_row_counts.append(int(shape[0]))
                if s_idx == 0:
                    self._embed_dtype = t_dt
        elif unsharded_key in st_index.weight_map:
            self.split_ngram_parts = 1
            _sp, t_dt, _eb, shape, _off, _nb = st_index.get_tensor_info(unsharded_key)
            shard_row_counts.append(int(shape[0]))
            self._embed_dtype = t_dt
        else:
            raise KeyError(f"Missing PLE embedding shards ({shard0_key} or {unsharded_key}) in {st_index.model_dir}")

        bounds = [0]
        for c in shard_row_counts:
            bounds.append(bounds[-1] + c)
        self.shard_bounds = bounds
        self._preindexed_map: Optional[Tuple[np.ndarray, torch.Tensor]] = None

    def _shift_right_ignore_eos(self, token_ids: torch.Tensor, shift: int) -> torch.Tensor:
        if shift == 0:
            return token_ids
        batch_size, seq_len = token_ids.shape
        positions = torch.arange(seq_len, device=token_ids.device, dtype=torch.long)
        eos_positions = torch.where(token_ids == self.eos_token_id, positions, -1)
        previous_eos_inclusive = torch.cummax(eos_positions, dim=1).values
        previous_eos = torch.cat(
            [eos_positions.new_full((batch_size, 1), -1), previous_eos_inclusive[:, :-1]], dim=1
        )
        segment_start = previous_eos + 1
        position_in_segment = positions.unsqueeze(0) - segment_start
        source_positions = positions - shift
        gather_positions = source_positions.clamp_min(0).unsqueeze(0).expand(batch_size, -1)
        shifted = token_ids.gather(dim=1, index=gather_positions)
        valid = (position_in_segment >= shift) & (source_positions.unsqueeze(0) >= 0)
        return torch.where(valid, shifted, token_ids.new_full((), self.eos_token_id))

    @torch.no_grad()
    def _compute_global_ngram_ids(self, input_ids_cpu: torch.Tensor) -> torch.Tensor:
        ids = input_ids_cpu.to(torch.int64)
        bsz, seq_len = ids.shape
        previous_context = ids.new_full((bsz, self.context_len), self.eos_token_id)
        token_history = torch.cat([previous_context, ids], dim=-1)
        shifted_tokens = [self._shift_right_ignore_eos(token_history, s) for s in range(self.ngram_size)]

        mults = self.layer_multipliers.reshape(-1)
        blocks = []
        for ngram in range(2, self.ngram_size + 1):
            start_idx = (ngram - 2) * self.heads_per_ngram
            end_idx = start_idx + self.heads_per_ngram
            mixed_ids = shifted_tokens[0] * mults[0]
            for pos in range(1, ngram):
                mixed_ids = torch.bitwise_xor(mixed_ids, shifted_tokens[pos] * mults[pos])
            head_vocab_sizes = self.ngram_heads_vocab_sizes[start_idx:end_idx]
            head_offsets = self.ngram_heads_offsets[start_idx:end_idx]
            ngram_ids = torch.remainder(mixed_ids.unsqueeze(-1), head_vocab_sizes.view(1, 1, -1))
            blocks.append(ngram_ids + head_offsets.view(1, 1, -1))

        return torch.cat(blocks, dim=-1)[:, -seq_len:, :]

    @torch.no_grad()
    def _fetch_sorted_unique_rows(self, unique_ids: torch.Tensor) -> torch.Tensor:
        unique_embeds = torch.empty((unique_ids.numel(), self.head_dim), dtype=self._embed_dtype)
        if unique_ids.numel() == 0:
            return unique_embeds
        u_np = np.asarray(unique_ids.numpy(), dtype=np.int64)
        win_cap_bytes = 16 * 1024 * 1024  # 16 MiB reusable scratch buffer
        win_u8 = torch.empty((win_cap_bytes,), dtype=torch.uint8)
        win_mv = memoryview(win_u8.numpy())

        for s_idx in range(self.split_ngram_parts):
            lo, hi = self.shard_bounds[s_idx], self.shard_bounds[s_idx + 1]
            left = int(np.searchsorted(u_np, lo, side="left"))
            right = int(np.searchsorted(u_np, hi, side="left"))
            if left >= right:
                continue
            local_rows_np = u_np[left:right] - lo
            t_name = (
                f"{self.ple_prefix}.ngram_embedding.shard_{s_idx}.weight"
                if self._is_sharded
                else f"{self.ple_prefix}.ngram_embedding.weight"
            )
            shard_file, t_dt, elem_bytes, shape, abs_off, _nb = self.st_index.get_tensor_info(t_name)
            row_bytes = int(shape[1]) * elem_bytes
            rows_per_win = max(1, win_cap_bytes // row_bytes)

            fd = os.open(str(shard_file), os.O_RDONLY)
            try:
                cur = 0
                n_loc = int(local_rows_np.size)
                while cur < n_loc:
                    r_start = int(local_rows_np[cur])
                    r_limit = min(int(shape[0]), r_start + rows_per_win)
                    nxt = int(np.searchsorted(local_rows_np, r_limit, side="left"))
                    r_end = int(local_rows_np[nxt - 1]) + 1
                    span_rows = r_end - r_start
                    span_bytes = span_rows * row_bytes
                    _pread_exact_into_mv(
                        fd,
                        win_mv[:span_bytes],
                        abs_off + r_start * row_bytes,
                        drop_cache=self.st_index.drop_cache,
                    )
                    win_t = win_u8[:span_bytes].view(t_dt).reshape(span_rows, self.head_dim)
                    rel_idx = torch.from_numpy(local_rows_np[cur:nxt] - r_start)
                    unique_embeds[left + cur : left + nxt] = win_t.index_select(0, rel_idx).to(
                        self._embed_dtype
                    )
                    cur = nxt
                if self.st_index.drop_cache:
                    drop_fd_page_cache(fd, offset=0, length=0)
            finally:
                os.close(fd)
        del win_mv, win_u8
        return unique_embeds

    @torch.no_grad()
    def preindex_for_sequences(self, input_ids_list: Sequence[torch.Tensor]) -> int:
        """One-pass shard scan for layer 1 across active batch/dataset, evicted immediately via clear()."""
        if not input_ids_list:
            return 0
        all_flat = torch.cat([self._compute_global_ngram_ids(t.cpu()).reshape(-1) for t in input_ids_list], dim=0)
        unique_ids = torch.unique(all_flat, sorted=True)
        del all_flat
        unique_embeds = self._fetch_sorted_unique_rows(unique_ids)
        self._preindexed_map = (unique_ids.numpy(), unique_embeds)
        return int(unique_ids.numel())

    def clear_preindex(self) -> None:
        self._preindexed_map = None
        gc.collect()

    @torch.no_grad()
    def compute_layer1_ple_embeds(self, input_ids_cpu: torch.Tensor) -> torch.Tensor:
        bsz, seq_len = input_ids_cpu.shape
        global_ids = self._compute_global_ngram_ids(input_ids_cpu)
        flat_ids = global_ids.reshape(-1)
        if self._preindexed_map is not None:
            keys_np, vals_t = self._preindexed_map
            pos = np.searchsorted(keys_np, flat_ids.numpy())
            gathered = vals_t[torch.from_numpy(pos)]
        else:
            unique_ids, inv_idx = torch.unique(flat_ids, sorted=True, return_inverse=True)
            unique_embeds = self._fetch_sorted_unique_rows(unique_ids)
            gathered = unique_embeds[inv_idx]
        return gathered.view(bsz, seq_len, self.num_heads_per_layer * self.head_dim).contiguous()

    @torch.no_grad()
    def forward(self, input_ids: torch.Tensor, past_key_values: Any = None) -> torch.Tensor:
        out = self.compute_layer1_ple_embeds(input_ids.detach().cpu())
        return out if input_ids.device.type == "cpu" else out.to(input_ids.device)


@torch.no_grad()
def fast_exact_qsa_indexer_forward(
    indexer: nn.Module,
    hidden_states: torch.Tensor,
    position_embeddings: Tuple[torch.Tensor, torch.Tensor],
    attention_mask: torch.Tensor,
    past_key_values: Any = None,
    q_chunk_size: int = 512,
) -> torch.Tensor:
    """Exact vectorized QSA boolean selection mask matching Qwen4ExpTextQSAIndexer.forward."""
    import math
    from transformers.models.qwen4_exp.modeling_qwen4_exp import apply_rotary_pos_emb

    bsz, seq_len, _ = hidden_states.shape
    device = hidden_states.device

    if (
        past_key_values is not None
        or attention_mask is None
        or attention_mask.shape[-2] != seq_len
        or attention_mask.shape[-1] != seq_len
    ):
        return indexer(hidden_states, position_embeddings, attention_mask, past_key_values)

    visible = attention_mask if attention_mask.dtype == torch.bool else (attention_mask == 0)
    q_idx = torch.arange(seq_len, device=device)[:, None]
    k_idx = torch.arange(seq_len, device=device)[None, :]
    causal_bool = (k_idx <= q_idx).unsqueeze(0).unsqueeze(0).expand(bsz, 1, seq_len, seq_len)
    if not torch.equal(visible, causal_bool):
        return indexer(hidden_states, position_embeddings, attention_mask, past_key_values)

    c_ratio = int(indexer.compress_ratio)
    block_topk = int(indexer.block_topk)
    num_complete_total = seq_len // c_ratio

    has_hooks = bool(indexer.index_qk_proj._forward_pre_hooks or indexer.index_qk_proj._forward_hooks)
    if num_complete_total <= block_topk:
        if has_hooks:
            _ = indexer.index_qk_proj(hidden_states)
        return causal_bool.clone()

    n_heads = int(indexer.index_n_heads)
    kv_heads = int(indexer.index_kv_heads)
    h_dim = int(indexer.index_head_dim)

    full_cos, full_sin = position_embeddings
    cur_cos, cur_sin = full_cos[:, -seq_len:, :], full_sin[:, -seq_len:, :]

    qk = indexer.index_qk_proj(hidden_states)
    q, token_k = torch.split(qk, [n_heads * h_dim, kv_heads * h_dim], dim=-1)
    q = indexer.q_layernorm(q.reshape(bsz, seq_len, n_heads, h_dim))
    q = apply_rotary_pos_emb(q, cos=cur_cos, sin=cur_sin, unsqueeze_dim=2)
    raw_keys = token_k.reshape(bsz, seq_len, kv_heads, h_dim).squeeze(2)

    key_groups = raw_keys[:, : num_complete_total * c_ratio, :].reshape(bsz, num_complete_total, c_ratio, h_dim)
    pooled_keys = indexer.k_layernorm(key_groups.float().mean(dim=2).to(raw_keys.dtype))
    group_starts = torch.arange(num_complete_total, device=device, dtype=torch.long) * c_ratio
    cos_g = full_cos.index_select(1, group_starts)
    sin_g = full_sin.index_select(1, group_starts)
    block_key_states = apply_rotary_pos_emb(
        pooled_keys.unsqueeze(2), cos=cos_g, sin=sin_g, unsqueeze_dim=2
    ).squeeze(2)

    selected_mask = torch.zeros((bsz, 1, seq_len, seq_len), dtype=torch.bool, device=device)
    q_cut = min(seq_len, (block_topk + 1) * c_ratio - 1)
    if q_cut > 0:
        selected_mask[:, :, :q_cut, :] = causal_bool[:, :, :q_cut, :]

    inv_sqrt_d = 1.0 / math.sqrt(float(h_dim))
    bk_f32_t = block_key_states.float().unsqueeze(1).transpose(-1, -2)  # [B, 1, D, G]
    g_arange = torch.arange(num_complete_total, device=device)[None, :]  # [1, G]
    ar_c = torch.arange(c_ratio, device=device)

    for q0 in range(q_cut, seq_len, q_chunk_size):
        q1 = min(seq_len, q0 + q_chunk_size)
        q_vec = torch.arange(q0, q1, device=device)[:, None]  # [q_len, 1]
        n_comp_q = (q_vec + 1) // c_ratio  # [q_len, 1] > block_topk

        # Always keep incomplete tail [n_comp_q * c_ratio .. q]
        tail_start = n_comp_q * c_ratio
        tail_mask = (k_idx >= tail_start) & (k_idx <= q_vec)  # [q_len, S]
        selected_mask[:, :, q0:q1, :] = tail_mask.unsqueeze(0).unsqueeze(0)

        qc = q[:, q0:q1, :, :].float()  # [B, q_len, H, D]
        raw_scores = torch.matmul(qc, bk_f32_t)  # [B, q_len, H, G]
        scores = F.relu(raw_scores).sum(dim=2) * inv_sqrt_d  # [B, q_len, G]
        valid_blocks = (g_arange < n_comp_q).unsqueeze(0)  # [1, q_len, G]
        scores = scores.masked_fill(~valid_blocks, float("-inf"))

        sel_blocks = scores.topk(block_topk, dim=-1).indices  # [B, q_len, block_topk]
        sel_toks = (sel_blocks.unsqueeze(-1) * c_ratio + ar_c).reshape(bsz, 1, q1 - q0, block_topk * c_ratio)
        selected_mask[:, :, q0:q1, :].scatter_(-1, sel_toks, True)

    return selected_mask


class QSAIndexerWrapper(nn.Module):
    """Drop-in wrapper around Qwen4ExpTextQSAIndexer using fast_exact_qsa_indexer_forward."""

    def __init__(self, orig_indexer: nn.Module) -> None:
        super().__init__()
        self.orig = orig_indexer

    def forward(
        self,
        hidden_states: torch.Tensor,
        position_embeddings: Tuple[torch.Tensor, torch.Tensor],
        attention_mask: torch.Tensor,
        past_key_values: Any = None,
    ) -> torch.Tensor:
        return fast_exact_qsa_indexer_forward(
            self.orig, hidden_states, position_embeddings, attention_mask, past_key_values=past_key_values
        )


@torch.no_grad()
def compute_position_embeddings_for_sample(
    rotary_emb: nn.Module,
    sample: Dict[str, Any],
    seq_len: int,
    device: str | torch.device = "cpu",
    dtype: torch.dtype = torch.bfloat16,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Compute (cos, sin) M-RoPE embeddings for either multimodal or text-only samples."""
    dummy = torch.empty((1, seq_len, 1), dtype=dtype, device=device)
    if sample.get("mrope_position_ids") is not None:
        pos_ids = sample["mrope_position_ids"].to(device=device, dtype=torch.long)
    else:
        pos_ids = torch.arange(seq_len, device=device, dtype=torch.long).view(1, 1, seq_len).expand(3, 1, seq_len)
    cos, sin = rotary_emb(dummy, pos_ids)
    return cos, sin


def reorder_gdn_v_heads_activation(
    x: torch.Tensor,
    num_k_heads: int = 16,
    num_v_heads: int = 48,
    head_v_dim: int = 128,
) -> torch.Tensor:
    """Permute linear_attn.out_proj input activation from grouped to tiled V-head order
    matching tools/llama.cpp/conversion/qwen.py:_reorder_v_heads."""
    if num_k_heads <= 0 or num_v_heads <= 0 or num_k_heads == num_v_heads:
        return x
    num_v_per_k = num_v_heads // num_k_heads
    orig_shape = x.shape
    x2 = x.reshape(-1, num_k_heads, num_v_per_k, head_v_dim)
    return x2.permute(0, 2, 1, 3).contiguous().reshape(orig_shape)


class ResumableFlatSequenceStore:
    """Sequential binary store for [total_tokens, hc_count, hidden_size] BF16 states.

    Uses raw file read/write + POSIX_FADV_DONTNEED instead of persistent mmap so
    multi-GiB activation buffers never pollute Linux page cache.
    """

    def __init__(
        self,
        bin_path: Path,
        seq_lengths: Sequence[int],
        hc_count: int = 4,
        hidden_size: int = 2560,
        create: bool = False,
    ) -> None:
        self.bin_path = Path(bin_path)
        self.seq_lengths = [int(s) for s in seq_lengths]
        self.hc_count = int(hc_count)
        self.hidden_size = int(hidden_size)
        self.row_elems = self.hc_count * self.hidden_size
        self.row_bytes = self.row_elems * 2  # uint16 (bf16)

        offsets = [0]
        for s in self.seq_lengths:
            offsets.append(offsets[-1] + s)
        self.seq_offsets = offsets
        self.total_tokens = offsets[-1]
        self.total_bytes = self.total_tokens * self.row_bytes
        self._dirty_bytes = 0

        if create:
            self.bin_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(self.bin_path), os.O_CREAT | os.O_RDWR | os.O_TRUNC, 0o644)
            try:
                if self.total_bytes > 0:
                    os.ftruncate(fd, self.total_bytes)
            finally:
                os.close(fd)
        elif not self.bin_path.is_file():
            raise FileNotFoundError(f"Sequence store missing: {self.bin_path}")
        else:
            actual_sz = int(self.bin_path.stat().st_size)
            if actual_sz != self.total_bytes:
                raise ValueError(
                    f"Sequence store byte-size mismatch on {self.bin_path}: "
                    f"actual={actual_sz} != expected={self.total_bytes}"
                )

    def write_seq(self, idx: int, tensor_1_s_hc_d: torch.Tensor) -> None:
        s_len = self.seq_lengths[idx]
        byte_off = self.seq_offsets[idx] * self.row_bytes
        u16 = bf16_to_u16_numpy(tensor_1_s_hc_d.reshape(s_len, self.hc_count, self.hidden_size))
        mv = memoryview(u16).cast("B")
        nbytes = len(mv)
        fd = os.open(str(self.bin_path), os.O_RDWR)
        try:
            pos = 0
            while pos < nbytes:
                nw = os.pwritev(fd, [mv[pos:]], byte_off + pos)
                if nw <= 0:
                    raise OSError(f"Short pwritev on {self.bin_path} at {byte_off + pos}")
                pos += nw
            self._dirty_bytes += nbytes
            if self._dirty_bytes >= (32 * 1024 * 1024) or idx == len(self.seq_lengths) - 1:
                os.fdatasync(fd)
                drop_fd_page_cache(fd, offset=0, length=0)
                self._dirty_bytes = 0
        finally:
            os.close(fd)

    def read_seq(self, idx: int, device: str | torch.device = "cpu") -> torch.Tensor:
        s_len = self.seq_lengths[idx]
        byte_off = self.seq_offsets[idx] * self.row_bytes
        arr = np.empty((1, s_len, self.hc_count, self.hidden_size), dtype=np.uint16)
        mv = memoryview(arr).cast("B")
        fd = os.open(str(self.bin_path), os.O_RDONLY)
        try:
            _pread_exact_into_mv(fd, mv, byte_off, drop_cache=True)
        finally:
            os.close(fd)
        t = u16_numpy_to_bf16(arr)
        return t if str(device) == "cpu" else t.to(device)


class ResumablePingPong:
    """Two-slot (A/B) resumable layer-by-layer activation ping-pong manager."""

    def __init__(
        self,
        stage_dir: Path,
        name: str,
        seq_lengths: Sequence[int],
        hc_count: int = 4,
        hidden_size: int = 2560,
    ) -> None:
        self.stage_dir = Path(stage_dir)
        self.stage_dir.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.seq_lengths = [int(s) for s in seq_lengths]
        self.hc_count = int(hc_count)
        self.hidden_size = int(hidden_size)
        self.state_path = self.stage_dir / f"{name}_pingpong_state.json"
        self.slot_paths = {
            "A": self.stage_dir / f"{name}_slot_A.bin",
            "B": self.stage_dir / f"{name}_slot_B.bin",
        }

    def load_state(self) -> Optional[Dict[str, Any]]:
        if not self.state_path.is_file():
            return None
        with open(self.state_path, "r", encoding="utf-8") as f:
            st = json.load(f)
        if st.get("seq_lengths") != self.seq_lengths:
            return None
        return st

    def save_state(self, completed_layer: int, active_slot: str, extra: Optional[Dict[str, Any]] = None) -> None:
        payload: Dict[str, Any] = {
            "name": self.name,
            "completed_layer": int(completed_layer),
            "active_slot": str(active_slot),
            "seq_lengths": self.seq_lengths,
            "hc_count": self.hc_count,
            "hidden_size": self.hidden_size,
        }
        if extra:
            payload.update(extra)
        tmp = self.state_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, self.state_path)

    def open_slot(self, slot: str, create: bool = False) -> ResumableFlatSequenceStore:
        return ResumableFlatSequenceStore(
            self.slot_paths[slot],
            self.seq_lengths,
            hc_count=self.hc_count,
            hidden_size=self.hidden_size,
            create=create,
        )


class LayerImatrixCollector:
    """Exact llama.cpp GGUF imatrix accumulator (quantize.cpp:199-215, llama-quant.cpp:820-840)."""

    def __init__(self, chunk_size: int = 512) -> None:
        self.chunk_size = int(chunk_size)
        self.sum2: Dict[str, np.ndarray] = {}
        self.counts: Dict[str, np.ndarray] = {}

    def record_2d(self, gguf_names: Sequence[str], x: torch.Tensor | np.ndarray) -> None:
        if isinstance(x, torch.Tensor):
            arr = x.detach().to(torch.float32).cpu().numpy()
        else:
            arr = np.asarray(x, dtype=np.float32)
        arr = arr.reshape(-1, arr.shape[-1])
        n_tok, in_dim = arr.shape
        if n_tok == 0:
            return
        sq_sum = np.sum(arr.astype(np.float64) ** 2, axis=0)
        for name in gguf_names:
            if name not in self.sum2:
                self.sum2[name] = np.zeros(in_dim, dtype=np.float64)
                self.counts[name] = np.zeros(1, dtype=np.int64)
            self.sum2[name] += sq_sum
            self.counts[name][0] += n_tok

    def ensure_3d(self, gguf_name: str, n_experts: int, in_dim: int) -> None:
        if gguf_name not in self.sum2:
            self.sum2[gguf_name] = np.zeros((n_experts, in_dim), dtype=np.float64)
            self.counts[gguf_name] = np.zeros(n_experts, dtype=np.int64)

    def record_3d_expert(
        self,
        gguf_names: Sequence[str],
        n_experts: int,
        expert_idx: int,
        x: torch.Tensor | np.ndarray,
    ) -> None:
        if isinstance(x, torch.Tensor):
            arr = x.detach().to(torch.float32).cpu().numpy()
        else:
            arr = np.asarray(x, dtype=np.float32)
        arr = arr.reshape(-1, arr.shape[-1])
        n_tok, in_dim = arr.shape
        if n_tok == 0:
            return
        sq_sum = np.sum(arr.astype(np.float64) ** 2, axis=0)
        for name in gguf_names:
            self.ensure_3d(name, n_experts, in_dim)
            self.sum2[name][expert_idx] += sq_sum
            self.counts[name][expert_idx] += n_tok

    def record_mtp_eh_proj(self, name: str, e_norm: torch.Tensor, h_norm_4d: torch.Tensor) -> None:
        """Record blk.{bid}.nextn.eh_proj.weight ([2560, 5120]) matching qwen4exp.cpp:641-644."""
        hc = int(h_norm_4d.shape[2])
        d = int(e_norm.shape[-1])
        e_flat = e_norm.detach().to(torch.float32).cpu().numpy().reshape(-1, d)
        n_tok = int(e_flat.shape[0])
        if n_tok == 0:
            return
        e_s2 = float(hc) * np.sum(e_flat.astype(np.float64) ** 2, axis=0)
        h_flat = h_norm_4d.detach().to(torch.float32).cpu().numpy().reshape(-1, d)
        h_s2 = np.sum(h_flat.astype(np.float64) ** 2, axis=0)
        cat_s2 = np.concatenate([e_s2, h_s2], axis=0)
        if name not in self.sum2:
            self.sum2[name] = np.zeros(cat_s2.shape[0], dtype=np.float64)
            self.counts[name] = np.zeros(1, dtype=np.int64)
        self.sum2[name] += cat_s2
        self.counts[name][0] += n_tok * hc

    def merge_from(self, other: "LayerImatrixCollector") -> None:
        for name, s2 in other.sum2.items():
            cnt = other.counts[name]
            if name not in self.sum2:
                self.sum2[name] = s2.copy()
                self.counts[name] = cnt.copy()
            else:
                self.sum2[name] += s2
                self.counts[name] += cnt

    def normalized_vector_for_expert(self, gguf_name: str, expert_idx: int) -> np.ndarray:
        """Return float32 importance vector [in_dim] matching quantize.cpp:204-214."""
        s2 = self.sum2[gguf_name][expert_idx]
        c = float(self.counts[gguf_name][expert_idx])
        if c > 0.0:
            return (s2 / c).astype(np.float32)
        return np.ones(s2.shape[-1], dtype=np.float32)


def write_imatrix_gguf(
    out_path: Path | str,
    collector: LayerImatrixCollector,
    dataset_name: str = "data/calib/v2/calib_v2_896.jsonl",
) -> int:
    """Serialize LayerImatrixCollector into exact llama.cpp GGUF imatrix format."""
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    writer = gguf.GGUFWriter(str(out_p), arch="imatrix")

    max_tokens = 0
    for cnt in collector.counts.values():
        if cnt.size > 0:
            max_tokens = max(max_tokens, int(cnt.max()))
    chunk_count = max(1, math.ceil(max_tokens / max(1, collector.chunk_size)))

    writer.add_uint32("imatrix.chunk_count", chunk_count)
    writer.add_uint32("imatrix.chunk_size", collector.chunk_size)
    writer.add_array("imatrix.datasets", [dataset_name])

    n_entries = 0
    for base_name in sorted(collector.sum2.keys()):
        s2_f32 = np.ascontiguousarray(collector.sum2[base_name], dtype=np.float32)
        cnt_f32 = np.ascontiguousarray(
            np.clip(collector.counts[base_name], 0, 1e15).astype(np.float32)
        )
        writer.add_tensor(f"{base_name}.in_sum2", s2_f32, raw_dtype=gguf.GGMLQuantizationType.F32)
        writer.add_tensor(f"{base_name}.counts", cnt_f32, raw_dtype=gguf.GGMLQuantizationType.F32)
        n_entries += 1

    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()
    drop_file_page_cache(out_p)
    gc.collect()
    return n_entries
