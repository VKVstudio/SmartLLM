#!/usr/bin/env python3
"""Stage D Sequential GPU Combine State Machine (OPUS_MASTER_PLAN_V2 §1 Stage D & §2 WP-A3).

Enforces strict sequential GPU sharing between llama-server (SmartLLM) and
stable-diffusion.cpp (Z-Image) on a single 12 GB VRAM GPU with Zero-Swap SLA:

State sequence:
    IDLE
    -> LLM_STARTING (llama-server bound strictly to 127.0.0.1 with --slot-save-path)
    -> LLM_ACTIVE (health ok, optional prompt warm-up on slot 0)
    -> SLOT_SAVING (POST /slots/0?action=save -> verify slot file on disk)
    -> LLM_STOPPING (SIGTERM llama-server -> wait for clean exit)
    -> VRAM_VERIFY_POST_LLM (scripts/infra/gpu_exit_check.py: 0 compute apps, VRAM <= idle+64 MiB)
    -> SD_BATCH_RUNNING (stable-diffusion.cpp batch for all site prompts in one process)
    -> VRAM_VERIFY_POST_SD (verify non-blank PNG artifacts + gpu_exit_check.py)
    -> LLM_RESTARTING (restart llama-server on 127.0.0.1 with --slot-save-path)
    -> SLOT_RESTORING (POST /slots/0?action=restore -> verify n_restored == n_saved)
    -> COMPLETED (optional final SIGTERM + gpu_exit_check when --stop-llm-on-exit)

Invariants:
- Max 1 model in VRAM at any instant.
- Zero auto-retry on any GPU/subprocess/HTTP/SLA failure -> immediate ABORTED_FATAL.
- LLM bound strictly to 127.0.0.1 only.
- Wrapped in flock -n .system/gpu.lock + scripts/infra/sla_watchdog.py + .system/gpu_runs.log.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from enum import Enum
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Callable
import urllib.error
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.infra.gpu_exit_check import check_gpu_exit  # noqa: E402
from scripts.infra.sla_watchdog import (  # noqa: E402
    DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
    SwapBaseline,
    append_checkpoint_incident,
    capture_swap_baseline,
    evaluate_swap_and_mem_sla,
    read_meminfo_avail_gib,
    read_ple_smaps_telemetry,
    read_vmstat_pswpout,
    read_vram_used_gib,
    terminate_process_group,
)

DEFAULT_LOCK_PATH = ROOT / ".system" / "gpu.lock"
DEFAULT_LOG_PATH = ROOT / ".system" / "gpu_runs.log"
DEFAULT_CHECKPOINT_PATH = ROOT / ".system" / "checkpoint.md"
WATCHDOG_SCRIPT = ROOT / "scripts" / "infra" / "sla_watchdog.py"
EXIT_CHECK_SCRIPT = ROOT / "scripts" / "infra" / "gpu_exit_check.py"

DEFAULT_LLAMA_SERVER = ROOT / "tools" / "llama.cpp" / "build_linux" / "bin" / "llama-server"
DEFAULT_MODEL_205E = ROOT / "models" / "SmartLLM-205E-IQ3_S.gguf"
DEFAULT_SD_CLI = ROOT / "tools" / "stable-diffusion.cpp" / "build_linux" / "bin" / "sd-cli"

COMFY_MODELS_DIR = Path("/mnt/rescue/ComfyUI_windows_portable/ComfyUI/models")
DEFAULT_DIT_FP8 = COMFY_MODELS_DIR / "diffusion_models" / "beyond_reality_z_image_3.0_fp8.safetensors"
DEFAULT_DIT_TURBO_BF16 = COMFY_MODELS_DIR / "diffusion_models" / "z_image_turbo_bf16.safetensors"
DEFAULT_QWEN_TE = COMFY_MODELS_DIR / "text_encoders" / "qwen_3_4b.safetensors"
DEFAULT_VAE = COMFY_MODELS_DIR / "vae" / "ae.safetensors"

DEFAULT_SLOT_SAVE_DIR = Path(os.environ.get("SMARTLLM_CACHE_DIR", str(Path.home() / ".cache" / "smartllm"))) / "slot_cache"
DEFAULT_SD_OUT_DIR = Path(os.environ.get("SMARTLLM_CACHE_DIR", str(Path.home() / ".cache" / "smartllm"))) / "sd_outputs"


class CombineState(str, Enum):
    IDLE = "IDLE"
    LLM_STARTING = "LLM_STARTING"
    LLM_ACTIVE = "LLM_ACTIVE"
    SLOT_SAVING = "SLOT_SAVING"
    LLM_STOPPING = "LLM_STOPPING"
    VRAM_VERIFY_POST_LLM = "VRAM_VERIFY_POST_LLM"
    SD_BATCH_RUNNING = "SD_BATCH_RUNNING"
    VRAM_VERIFY_POST_SD = "VRAM_VERIFY_POST_SD"
    LLM_RESTARTING = "LLM_RESTARTING"
    SLOT_RESTORING = "SLOT_RESTORING"
    COMPLETED = "COMPLETED"
    ABORTED_FATAL = "ABORTED_FATAL"


VALID_TRANSITIONS: dict[CombineState, set[CombineState]] = {
    CombineState.IDLE: {
        CombineState.LLM_STARTING,
        CombineState.VRAM_VERIFY_POST_LLM,
        CombineState.ABORTED_FATAL,
    },
    CombineState.LLM_STARTING: {CombineState.LLM_ACTIVE, CombineState.ABORTED_FATAL},
    CombineState.LLM_ACTIVE: {CombineState.SLOT_SAVING, CombineState.ABORTED_FATAL},
    CombineState.SLOT_SAVING: {CombineState.LLM_STOPPING, CombineState.ABORTED_FATAL},
    CombineState.LLM_STOPPING: {CombineState.VRAM_VERIFY_POST_LLM, CombineState.ABORTED_FATAL},
    CombineState.VRAM_VERIFY_POST_LLM: {CombineState.SD_BATCH_RUNNING, CombineState.ABORTED_FATAL},
    CombineState.SD_BATCH_RUNNING: {CombineState.VRAM_VERIFY_POST_SD, CombineState.ABORTED_FATAL},
    CombineState.VRAM_VERIFY_POST_SD: {
        CombineState.LLM_RESTARTING,
        CombineState.COMPLETED,
        CombineState.ABORTED_FATAL,
    },
    CombineState.LLM_RESTARTING: {CombineState.SLOT_RESTORING, CombineState.ABORTED_FATAL},
    CombineState.SLOT_RESTORING: {CombineState.COMPLETED, CombineState.ABORTED_FATAL},
    CombineState.COMPLETED: set(),
    CombineState.ABORTED_FATAL: set(),
}


class CombineError(RuntimeError):
    """Base fatal error in Stage D combine (zero auto-retry)."""


class SecurityInvariantError(CombineError):
    """Raised if host binding or local-only invariant is violated."""


class StateTransitionError(CombineError):
    """Raised on illegal state transition."""


def _ancestor_pids() -> list[int]:
    """Return list of ancestor PIDs from os.getppid() up to PID 1."""
    ancestors: list[int] = []
    cur = os.getppid()
    seen: set[int] = set()
    while cur > 1 and cur not in seen:
        ancestors.append(cur)
        seen.add(cur)
        stat_path = Path(f"/proc/{cur}/stat")
        if not stat_path.exists():
            break
        try:
            raw = stat_path.read_text(encoding="utf-8")
            rparen = raw.rfind(")")
            if rparen == -1:
                break
            fields = raw[rparen + 2 :].split()
            cur = int(fields[1])
        except Exception:
            break
    return ancestors


def _ancestor_holds_lock(lock_path: Path) -> int | None:
    """Check if any ancestor process already holds an open fd to lock_path."""
    try:
        target_real = str(lock_path.resolve())
    except Exception:
        return None
    for pid in _ancestor_pids():
        fd_dir = Path(f"/proc/{pid}/fd")
        if not fd_dir.exists():
            continue
        try:
            for fd_entry in os.listdir(fd_dir):
                link_target = os.readlink(fd_dir / fd_entry)
                if link_target == target_real:
                    return pid
        except Exception:
            continue
    return None


def _ancestor_is_watchdog() -> int | None:
    """Check if any ancestor process is scripts/infra/sla_watchdog.py."""
    for pid in _ancestor_pids():
        cmdline_path = Path(f"/proc/{pid}/cmdline")
        if not cmdline_path.exists():
            continue
        try:
            raw = cmdline_path.read_bytes().replace(b"\x00", b" ").decode("utf-8", errors="replace")
            if "sla_watchdog.py" in raw:
                return pid
        except Exception:
            continue
    return None


def _paeth_predictor(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def verify_png_artifact(
    image_path: Path,
    expected_width: int = 0,
    expected_height: int = 0,
    min_std: float = 1.5,
) -> dict[str, Any]:
    """Verify that image_path exists, is a valid PNG, matches dimensions, and is non-blank.

    Uses Pillow if installed in current interpreter, or falls back to pure-stdlib
    zlib/struct PNG scanline decoding so it works in any Python environment.
    """
    if not image_path.exists():
        return {"valid": False, "error": f"File does not exist: {image_path}"}
    file_size = image_path.stat().st_size
    if file_size < 128:
        return {"valid": False, "error": f"File too small ({file_size} B): {image_path}"}

    raw = image_path.read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return {"valid": False, "error": "Invalid PNG signature"}

    # Parse IHDR and collect IDAT chunks
    pos = 8
    width = 0
    height = 0
    bit_depth = 0
    color_type = 0
    interlace = 0
    idat_parts: list[bytes] = []

    while pos + 8 <= len(raw):
        length = struct.unpack(">I", raw[pos : pos + 4])[0]
        chunk_type = raw[pos + 4 : pos + 8]
        chunk_data = raw[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if chunk_type == b"IHDR" and len(chunk_data) >= 13:
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk_data[:13]
            )
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width <= 0 or height <= 0:
        return {"valid": False, "error": "Missing or invalid IHDR dimensions"}
    if expected_width > 0 and width != expected_width:
        return {"valid": False, "error": f"Width {width} != expected {expected_width}"}
    if expected_height > 0 and height != expected_height:
        return {"valid": False, "error": f"Height {height} != expected {expected_height}"}

    # Pure stdlib PNG scanline reconstruction first (zero extra C-library RSS overhead)
    pixel_min = 0
    pixel_max = 0
    pixel_mean = 0.0
    pixel_std = 0.0
    decoded_ok = False

    if not decoded_ok:
        # Pure stdlib PNG scanline reconstruction for 8-bit Grayscale/RGB/RGBA
        try:
            decompressed = zlib.decompress(b"".join(idat_parts))
            channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color_type, 3)
            bpp = max(1, (channels * bit_depth) // 8)
            stride = width * bpp
            expected_len = height * (1 + stride)
            if interlace == 0 and len(decompressed) >= expected_len:
                prev_row = bytearray(stride)
                cur_row = bytearray(stride)
                sample_vals: list[int] = []
                row_step = max(1, height // 128)
                col_step = max(1, stride // 512)
                offset = 0
                for r in range(height):
                    ftype = decompressed[offset]
                    offset += 1
                    row_raw = decompressed[offset : offset + stride]
                    offset += stride
                    if ftype == 0:
                        cur_row[:] = row_raw
                    elif ftype == 1:
                        for i in range(stride):
                            left = cur_row[i - bpp] if i >= bpp else 0
                            cur_row[i] = (row_raw[i] + left) & 0xFF
                    elif ftype == 2:
                        for i in range(stride):
                            cur_row[i] = (row_raw[i] + prev_row[i]) & 0xFF
                    elif ftype == 3:
                        for i in range(stride):
                            left = cur_row[i - bpp] if i >= bpp else 0
                            up = prev_row[i]
                            cur_row[i] = (row_raw[i] + ((left + up) >> 1)) & 0xFF
                    elif ftype == 4:
                        for i in range(stride):
                            left = cur_row[i - bpp] if i >= bpp else 0
                            up = prev_row[i]
                            up_left = prev_row[i - bpp] if i >= bpp else 0
                            cur_row[i] = (row_raw[i] + _paeth_predictor(left, up, up_left)) & 0xFF
                    else:
                        cur_row[:] = row_raw
                    if r % row_step == 0:
                        for c in range(0, stride, col_step):
                            sample_vals.append(cur_row[c])
                    prev_row[:] = cur_row
                if sample_vals:
                    pixel_min = min(sample_vals)
                    pixel_max = max(sample_vals)
                    pixel_mean = sum(sample_vals) / len(sample_vals)
                    var = sum((x - pixel_mean) ** 2 for x in sample_vals) / len(sample_vals)
                    pixel_std = math.sqrt(var)
                    decoded_ok = True
        except Exception as exc:
            return {"valid": False, "error": f"PNG IDAT decode failed: {exc}"}

    if not decoded_ok:
        try:
            from PIL import Image  # type: ignore

            with Image.open(image_path) as im:
                rgb = im.convert("RGB")
                px_bytes = rgb.tobytes()
                n_vals = len(px_bytes)
                if n_vals > 0:
                    pixel_min = min(px_bytes)
                    pixel_max = max(px_bytes)
                    step = max(1, n_vals // 65536)
                    samples = [px_bytes[i] for i in range(0, n_vals, step)]
                    pixel_mean = sum(samples) / len(samples)
                    var = sum((x - pixel_mean) ** 2 for x in samples) / len(samples)
                    pixel_std = math.sqrt(var)
                    decoded_ok = True
        except Exception:
            pass

    if not decoded_ok:
        return {"valid": False, "error": "Could not decode PNG pixel data"}

    non_blank = (pixel_max > pixel_min) and (pixel_std >= min_std)
    return {
        "valid": non_blank,
        "path": str(image_path),
        "file_size_bytes": file_size,
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "color_type": color_type,
        "pixel_min": pixel_min,
        "pixel_max": pixel_max,
        "pixel_mean": round(pixel_mean, 2),
        "pixel_std": round(pixel_std, 2),
        "non_blank": non_blank,
        "error": None if non_blank else f"Blank/constant image (std={pixel_std:.2f} < {min_std})",
    }


def _http_json(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(body) if body.strip() else {}
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        try:
            parsed = json.loads(body) if body.strip() else {"raw_error": body}
        except Exception:
            parsed = {"raw_error": body}
        return exc.code, parsed
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return 0, {"connection_error": str(exc)}


def parse_aspect_ratio_dims(aspect_ratio: str, default_w: int = 1024, default_h: int = 1024) -> tuple[int, int]:
    ar = aspect_ratio.strip()
    mapping = {
        "1:1": (1024, 1024),
        "16:9": (1280, 720),
        "9:16": (720, 1280),
        "4:3": (1152, 896),
        "3:4": (896, 1152),
        "3:2": (1216, 832),
        "2:3": (832, 1216),
    }
    return mapping.get(ar, (default_w, default_h))


class SequentialGPUCombineMachine:
    """Deterministic finite state machine for LLM <-> Z-Image sequential GPU switching."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 18080,
        llama_server_bin: Path = DEFAULT_LLAMA_SERVER,
        llama_model_path: Path = DEFAULT_MODEL_205E,
        llama_extra_args: list[str] | None = None,
        slot_save_dir: Path = DEFAULT_SLOT_SAVE_DIR,
        slot_filename: str = "slot_0_combine.bin",
        sd_cli_bin: Path = DEFAULT_SD_CLI,
        dit_model_path: Path = DEFAULT_DIT_FP8,
        llm_encoder_path: Path = DEFAULT_QWEN_TE,
        vae_model_path: Path = DEFAULT_VAE,
        sd_out_dir: Path = DEFAULT_SD_OUT_DIR,
        sd_type: str = "q8_0",
        sd_steps: int = 8,
        sd_cfg: float = 1.0,
        sd_flow_shift: float = 3.0,
        sd_width: int = 1024,
        sd_height: int = 1024,
        sd_seed: int = 42,
        sd_extra_args: list[str] | None = None,
        idle_vram_mib: float = 31.0,
        vram_margin_mib: float = 64.0,
        checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH,
        no_checkpoint_log: bool = False,
        exit_check_fn: Callable[[float, float], dict[str, Any]] | None = None,
    ) -> None:
        if host != "127.0.0.1":
            raise SecurityInvariantError(
                f"Security invariant violation: llama-server host must be '127.0.0.1', got '{host}'"
            )
        self.host = host
        self.port = port
        self.llama_server_bin = llama_server_bin
        self.llama_model_path = llama_model_path
        self.llama_extra_args = list(llama_extra_args or [])
        self.slot_save_dir = slot_save_dir
        self.slot_filename = slot_filename
        self.sd_cli_bin = sd_cli_bin
        self.dit_model_path = dit_model_path
        self.llm_encoder_path = llm_encoder_path
        self.vae_model_path = vae_model_path
        self.sd_out_dir = sd_out_dir
        self.sd_type = sd_type
        self.sd_steps = sd_steps
        self.sd_cfg = sd_cfg
        self.sd_flow_shift = sd_flow_shift
        self.sd_width = sd_width
        self.sd_height = sd_height
        self.sd_seed = sd_seed
        self.sd_extra_args = list(sd_extra_args or [])
        self.idle_vram_mib = idle_vram_mib
        self.vram_margin_mib = vram_margin_mib
        self.checkpoint_path = checkpoint_path
        self.no_checkpoint_log = no_checkpoint_log
        self.exit_check_fn = exit_check_fn or check_gpu_exit

        self.state: CombineState = CombineState.IDLE
        self.state_history: list[dict[str, Any]] = []
        self.llama_proc: subprocess.Popen[str] | None = None
        self.sd_proc: subprocess.Popen[str] | None = None
        self.swap_baseline: SwapBaseline = capture_swap_baseline()
        self.baseline_pswpout: int = self.swap_baseline.pswpout
        self.min_mem_avail_gib: float = self.swap_baseline.mem_available_gib
        self.max_vram_gib: float = read_vram_used_gib()
        self.max_pswpout_delta: int = 0
        self.disk_swap_used_kb: int = self.swap_baseline.disk_swap_used_kb
        self.max_disk_swap_write_sectors_delta: int = 0
        self.max_zram_orig_delta_mib: float = 0.0
        self.max_proc_swap_kb: int = 0
        self.max_ple_rss_kb: int = 0
        self.max_swap_kb: int = 0
        self.ple_snapshots: dict[str, dict[str, Any]] = {}
        self.slot_save_metrics: dict[str, Any] = {}
        self.slot_restore_metrics: dict[str, Any] = {}
        self.generated_images: list[dict[str, Any]] = []
        self.vram_barriers: dict[str, dict[str, Any]] = {}
        self.abort_reason: str | None = None

        self._record_state(CombineState.IDLE, "initialized")

    @staticmethod
    def _evict_file_page_cache(paths: list[Path]) -> None:
        """Drop clean VFS page-cache pages via POSIX_FADV_DONTNEED to maximize MemAvailable."""
        if not hasattr(os, "posix_fadvise") or not hasattr(os, "POSIX_FADV_DONTNEED"):
            return
        for p in paths:
            if not p.exists() or not p.is_file():
                continue
            try:
                fd = os.open(str(p), os.O_RDONLY)
                try:
                    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                finally:
                    os.close(fd)
            except Exception:
                pass

    def _sample_ple_if_running(self, label: str = "") -> dict[str, Any] | None:
        if self.llama_proc is None or self.llama_proc.poll() is not None:
            return None
        info = read_ple_smaps_telemetry(target_pid=self.llama_proc.pid, check_ple=True)
        ple_kb = int(info.get("ple_rss_kb", 0))
        swap_kb = int(info.get("rollup_swap_kb", 0))
        self.max_ple_rss_kb = max(self.max_ple_rss_kb, ple_kb)
        self.max_proc_swap_kb = max(self.max_proc_swap_kb, swap_kb)
        self.max_swap_kb = max(self.max_swap_kb, swap_kb)
        if label:
            self.ple_snapshots[label] = info
        eval_res = evaluate_swap_and_mem_sla(
            baseline=self.swap_baseline,
            root_pid=self.llama_proc.pid,
            max_proc_swap_mib=DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
            check_ple=True,
            _smaps_override=info,
        )
        self.disk_swap_used_kb = max(self.disk_swap_used_kb, eval_res["disk_swap_used_kb"])
        self.max_disk_swap_write_sectors_delta = max(
            self.max_disk_swap_write_sectors_delta, eval_res["disk_swap_write_sectors_delta"]
        )
        self.max_zram_orig_delta_mib = max(
            self.max_zram_orig_delta_mib, eval_res["zram_orig_delta_mib"]
        )
        if (not eval_res["passed"] or ple_kb > 0) and self.state != CombineState.ABORTED_FATAL:
            reason = eval_res["breach_reason"] or f"ple_rss_kb={ple_kb}"
            self.abort_fatal(
                f"PLE/Swap SLA violation at {label or self.state.value}: {reason} "
                f"(ple_rss_kb={ple_kb}, rollup_swap_kb={swap_kb})"
            )
        return info

    def _sample_sla(self) -> dict[str, Any]:
        active_pid: int | None = None
        if self.llama_proc is not None and self.llama_proc.poll() is None:
            active_pid = self.llama_proc.pid
        elif self.sd_proc is not None and self.sd_proc.poll() is None:
            active_pid = self.sd_proc.pid

        vram_gib = read_vram_used_gib()
        eval_res = evaluate_swap_and_mem_sla(
            baseline=self.swap_baseline,
            root_pid=active_pid,
            max_proc_swap_mib=DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
            check_ple=bool(self.llama_proc is not None and self.llama_proc.poll() is None),
            vram_gib=vram_gib,
        )
        delta_pswpout = eval_res["pswpout_delta"]
        mem_avail = eval_res["mem_available_gib"]
        self.max_pswpout_delta = max(self.max_pswpout_delta, delta_pswpout)
        self.min_mem_avail_gib = min(self.min_mem_avail_gib, mem_avail)
        self.max_vram_gib = max(self.max_vram_gib, vram_gib)
        self.disk_swap_used_kb = max(self.disk_swap_used_kb, eval_res["disk_swap_used_kb"])
        self.max_disk_swap_write_sectors_delta = max(
            self.max_disk_swap_write_sectors_delta, eval_res["disk_swap_write_sectors_delta"]
        )
        self.max_zram_orig_delta_mib = max(
            self.max_zram_orig_delta_mib, eval_res["zram_orig_delta_mib"]
        )
        self.max_proc_swap_kb = max(self.max_proc_swap_kb, eval_res["proc_swap_kb"])
        self.max_swap_kb = max(self.max_swap_kb, eval_res["proc_swap_kb"])
        self.max_ple_rss_kb = max(self.max_ple_rss_kb, eval_res["ple_rss_kb"])

        if not eval_res["passed"] and self.state != CombineState.ABORTED_FATAL:
            self.abort_fatal(f"SLA breach during {self.state.value}: {eval_res['breach_reason']}")

        return {
            "delta_pswpout": delta_pswpout,
            "disk_swap_used_kb": eval_res["disk_swap_used_kb"],
            "disk_swap_write_sectors_delta": eval_res["disk_swap_write_sectors_delta"],
            "zram_orig_delta_mib": eval_res["zram_orig_delta_mib"],
            "proc_swap_kb": eval_res["proc_swap_kb"],
            "mem_avail_gib": round(mem_avail, 3),
            "vram_gib": round(vram_gib, 3),
            "max_ple_rss_kb": self.max_ple_rss_kb,
        }

    def _record_state(self, new_state: CombineState, note: str = "") -> None:
        sla = self._sample_sla()
        entry = {
            "state": new_state.value,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "monotonic_sec": round(time.monotonic(), 3),
            "note": note,
            "sla": sla,
        }
        self.state_history.append(entry)

    def transition(self, target: CombineState, note: str = "") -> None:
        allowed = VALID_TRANSITIONS.get(self.state, set())
        if target not in allowed:
            raise StateTransitionError(
                f"Illegal state transition {self.state.value} -> {target.value}"
            )
        self.state = target
        self._record_state(target, note)

    def abort_fatal(self, reason: str) -> None:
        self.abort_reason = reason
        if self.state != CombineState.ABORTED_FATAL:
            self.state = CombineState.ABORTED_FATAL
            self._record_state(CombineState.ABORTED_FATAL, reason)
        self._kill_active_processes()
        if not self.no_checkpoint_log:
            append_checkpoint_incident(self.checkpoint_path, f"STAGE-D-ABORT: {reason}", "gpu_switch.py")
        raise CombineError(reason)

    def _kill_active_processes(self) -> None:
        for proc_attr in ("llama_proc", "sd_proc"):
            proc: subprocess.Popen[str] | None = getattr(self, proc_attr)
            if proc is not None and proc.poll() is None:
                try:
                    terminate_process_group(proc.pid, grace_sec=5.0)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
            setattr(self, proc_attr, None)

    def verify_vram_exit_barrier(self, barrier_name: str, poll_timeout_sec: float = 6.0) -> dict[str, Any]:
        """Wait briefly for GPU driver context cleanup, then enforce strict gpu_exit_check."""
        deadline = time.monotonic() + poll_timeout_sec
        last_res: dict[str, Any] = {}
        while True:
            last_res = self.exit_check_fn(self.idle_vram_mib, self.vram_margin_mib)
            if last_res.get("passed"):
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(0.25)

        self.vram_barriers[barrier_name] = last_res
        if not last_res.get("passed"):
            self.abort_fatal(
                f"gpu_exit_check failed at {barrier_name}: "
                f"used={last_res.get('memory_used_mib')} MiB (max={last_res.get('max_allowed_mib')} MiB), "
                f"active_apps={last_res.get('active_compute_apps')}, err={last_res.get('error')}"
            )
        return last_res

    def _build_llama_cmd(self) -> list[str]:
        # Hard check: reject any user-supplied --host in extra_args that isn't 127.0.0.1
        for i, arg in enumerate(self.llama_extra_args):
            if arg == "--host" and i + 1 < len(self.llama_extra_args):
                if self.llama_extra_args[i + 1] != "127.0.0.1":
                    raise SecurityInvariantError(
                        f"Extra arg --host must be 127.0.0.1, got {self.llama_extra_args[i + 1]}"
                    )
        self.slot_save_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.llama_server_bin),
            "-m",
            str(self.llama_model_path),
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--slots",
            "--slot-save-path",
            str(self.slot_save_dir),
        ]
        cmd.extend(self.llama_extra_args)
        return cmd

    def _start_and_wait_llama(self, startup_timeout_sec: float = 180.0, log_suffix: str = "start") -> None:
        cmd = self._build_llama_cmd()
        log_path = self.slot_save_dir / f"llama_server_{log_suffix}.log"
        log_f = log_path.open("w", encoding="utf-8")
        try:
            self.llama_proc = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
        except Exception as exc:
            log_f.close()
            self.abort_fatal(f"Failed to spawn llama-server: {exc}")

        health_url = f"http://127.0.0.1:{self.port}/health"
        deadline = time.monotonic() + startup_timeout_sec
        while time.monotonic() < deadline:
            assert self.llama_proc is not None
            rc = self.llama_proc.poll()
            if rc is not None:
                log_f.close()
                tail = ""
                try:
                    tail = log_path.read_text(encoding="utf-8", errors="replace")[-1200:]
                except Exception:
                    pass
                self.abort_fatal(f"llama-server exited prematurely (rc={rc}): {tail}")

            status, body = _http_json(health_url, method="GET", timeout=2.0)
            if status == 200 and body.get("status") == "ok":
                log_f.close()
                return
            time.sleep(0.5)

        log_f.close()
        self.abort_fatal(f"llama-server failed to reach healthy state within {startup_timeout_sec}s")

    def start_llm(self, seed_prompt: str | None = None, startup_timeout_sec: float = 180.0) -> None:
        self.verify_vram_exit_barrier("pre_llm_start")
        self.transition(CombineState.LLM_STARTING, f"spawning llama-server on 127.0.0.1:{self.port}")
        self._start_and_wait_llama(startup_timeout_sec=startup_timeout_sec, log_suffix="start")
        self._sample_ple_if_running("post_llm_start")
        self.transition(CombineState.LLM_ACTIVE, "llama-server healthy")

        if seed_prompt:
            comp_url = f"http://127.0.0.1:{self.port}/completion"
            status, body = _http_json(
                comp_url,
                method="POST",
                payload={
                    "id_slot": 0,
                    "prompt": seed_prompt,
                    "n_predict": 8,
                    "temperature": 0.0,
                    "cache_prompt": True,
                },
                timeout=120.0,
            )
            if status != 200:
                self.abort_fatal(f"Warmup completion on slot 0 failed (HTTP {status}): {body}")
            self._sample_ple_if_running("post_llm_warmup")

    def save_slot_and_stop_llm(self) -> None:
        self.transition(CombineState.SLOT_SAVING, f"saving slot 0 to {self.slot_filename}")
        slot_file = self.slot_save_dir / self.slot_filename
        if slot_file.exists():
            # Truncate existing slot cache file in our scratch dir without deleting repo files
            slot_file.write_bytes(b"")

        save_url = f"http://127.0.0.1:{self.port}/slots/0?action=save"
        status, body = _http_json(
            save_url,
            method="POST",
            payload={"filename": self.slot_filename},
            timeout=60.0,
        )
        if status != 200:
            self.abort_fatal(f"POST /slots/0?action=save failed (HTTP {status}): {body}")
        if not slot_file.exists() or slot_file.stat().st_size == 0:
            self.abort_fatal(f"Slot save file missing or 0 bytes: {slot_file}")

        self.slot_save_metrics = {
            "id_slot": body.get("id_slot", 0),
            "filename": body.get("filename", self.slot_filename),
            "n_saved": body.get("n_saved", 0),
            "n_written": body.get("n_written", slot_file.stat().st_size),
            "save_ms": body.get("timings", {}).get("save_ms", 0.0),
            "file_size_bytes": slot_file.stat().st_size,
        }

        self.transition(CombineState.LLM_STOPPING, "sending SIGTERM to llama-server")
        if self.llama_proc is not None:
            terminate_process_group(self.llama_proc.pid, grace_sec=10.0)
            try:
                self.llama_proc.wait(timeout=5)
            except Exception:
                pass
            self.llama_proc = None

        self._evict_file_page_cache([self.llama_model_path, slot_file])
        self.transition(CombineState.VRAM_VERIFY_POST_LLM, "verifying clean VRAM after LLM exit")
        self.verify_vram_exit_barrier("post_llm_stop")

    def run_sd_batch(
        self,
        prompts: list[dict[str, Any]],
        batch_timeout_sec: float = 600.0,
    ) -> list[dict[str, Any]]:
        if not prompts:
            self.abort_fatal("No prompts provided for sd.cpp batch")

        if self.state == CombineState.IDLE:
            self.transition(CombineState.VRAM_VERIFY_POST_LLM, "verifying clean VRAM before sd.cpp batch")
            self.verify_vram_exit_barrier("pre_sd_batch")

        self.transition(
            CombineState.SD_BATCH_RUNNING,
            f"running sd.cpp batch ({len(prompts)} image(s), timeout={batch_timeout_sec}s)",
        )
        self.sd_out_dir.mkdir(parents=True, exist_ok=True)

        # Prepare normalized prompt batch manifest in sd_out_dir
        normalized_items: list[dict[str, Any]] = []
        for idx, item in enumerate(prompts):
            img_id = str(item.get("id") or f"img_{idx:02d}")
            prompt_text = str(item.get("prompt") or "")
            if not prompt_text.strip():
                self.abort_fatal(f"Empty prompt text in item {img_id}")
            if "width" in item and "height" in item:
                w, h = int(item["width"]), int(item["height"])
            elif "aspect_ratio" in item:
                w, h = parse_aspect_ratio_dims(
                    str(item["aspect_ratio"]), default_w=self.sd_width, default_h=self.sd_height
                )
            else:
                w, h = self.sd_width, self.sd_height
            steps = int(item.get("steps") or self.sd_steps)
            cfg = float(item.get("cfg_scale") or item.get("cfg") or self.sd_cfg)
            seed = int(item.get("seed") if item.get("seed") is not None else (self.sd_seed + idx))
            out_path = Path(item.get("output_path") or (self.sd_out_dir / f"{img_id}.png"))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            normalized_items.append(
                {
                    "id": img_id,
                    "prompt": prompt_text,
                    "width": w,
                    "height": h,
                    "steps": steps,
                    "cfg_scale": cfg,
                    "seed": seed,
                    "output_path": str(out_path),
                }
            )

        first = normalized_items[0]
        cmd = [
            str(self.sd_cli_bin),
            "--diffusion-model",
            str(self.dit_model_path),
            "--llm",
            str(self.llm_encoder_path),
            "--vae",
            str(self.vae_model_path),
            "--type",
            self.sd_type,
            "--clip-on-cpu",
            "--vae-tiling",
            "--cfg-scale",
            str(first["cfg_scale"]),
            "--steps",
            str(first["steps"]),
            "--sampling-method",
            "euler",
            "--flow-shift",
            str(self.sd_flow_shift),
            "-W",
            str(first["width"]),
            "-H",
            str(first["height"]),
            "-s",
            str(first["seed"]),
            "-p",
            first["prompt"],
            "-o",
            first["output_path"],
            "-v",
        ]
        if len(normalized_items) == 1:
            cmd.extend(["--params-backend", "te=disk"])
        elif len(normalized_items) > 1:
            batch_manifest = self.sd_out_dir / "sd_batch_manifest.json"
            batch_manifest.write_text(json.dumps(normalized_items, indent=2), encoding="utf-8")
            cmd.extend(["--batch-json", str(batch_manifest)])
        cmd.extend(self.sd_extra_args)

        sd_log_path = self.sd_out_dir / "sd_batch.log"
        t0 = time.monotonic()
        with sd_log_path.open("w", encoding="utf-8") as log_f:
            try:
                self.sd_proc = subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    start_new_session=True,
                )
            except Exception as exc:
                self.abort_fatal(f"Failed to launch sd-cli ({self.sd_cli_bin}): {exc}")

            while True:
                assert self.sd_proc is not None
                rc = self.sd_proc.poll()
                self._sample_sla()
                if rc is not None:
                    break
                if time.monotonic() - t0 > batch_timeout_sec:
                    self.abort_fatal(f"sd-cli batch exceeded SLA timeout ({batch_timeout_sec}s)")
                time.sleep(0.5)

        rc = self.sd_proc.returncode if self.sd_proc else -1
        self.sd_proc = None
        sd_elapsed = round(time.monotonic() - t0, 3)

        if rc != 0:
            tail = ""
            try:
                tail = sd_log_path.read_text(encoding="utf-8", errors="replace")[-1500:]
            except Exception:
                pass
            self.abort_fatal(f"sd-cli exited with rc={rc} after {sd_elapsed}s: {tail}")

        # Verify all output PNG artifacts before checking VRAM exit
        verified_list: list[dict[str, Any]] = []
        for item in normalized_items:
            out_p = Path(item["output_path"])
            vinfo = verify_png_artifact(
                out_p,
                expected_width=item["width"],
                expected_height=item["height"],
            )
            vinfo["id"] = item["id"]
            vinfo["elapsed_sec"] = sd_elapsed
            if not vinfo.get("valid"):
                self.abort_fatal(f"Generated image verification failed for {out_p}: {vinfo.get('error')}")
            verified_list.append(vinfo)

        self.generated_images = verified_list
        self._evict_file_page_cache([self.dit_model_path, self.llm_encoder_path, self.vae_model_path])
        self.transition(CombineState.VRAM_VERIFY_POST_SD, "verifying clean VRAM after sd.cpp exit")
        self.verify_vram_exit_barrier("post_sd_batch")
        return verified_list

    def restart_llm_and_restore_slot(
        self,
        startup_timeout_sec: float = 180.0,
        stop_on_exit: bool = True,
    ) -> None:
        self.transition(CombineState.LLM_RESTARTING, f"restarting llama-server on 127.0.0.1:{self.port}")
        self._start_and_wait_llama(startup_timeout_sec=startup_timeout_sec, log_suffix="restart")
        self._sample_ple_if_running("post_llm_restart")

        self.transition(CombineState.SLOT_RESTORING, f"restoring slot 0 from {self.slot_filename}")
        restore_url = f"http://127.0.0.1:{self.port}/slots/0?action=restore"
        status, body = _http_json(
            restore_url,
            method="POST",
            payload={"filename": self.slot_filename},
            timeout=60.0,
        )
        if status != 200:
            self.abort_fatal(f"POST /slots/0?action=restore failed (HTTP {status}): {body}")
        self._sample_ple_if_running("post_slot_restore")

        n_saved = self.slot_save_metrics.get("n_saved", 0)
        n_restored = body.get("n_restored", 0)
        if n_saved > 0 and n_restored != n_saved:
            self.abort_fatal(
                f"Slot token count mismatch on restore: n_restored={n_restored} != n_saved={n_saved}"
            )

        self.slot_restore_metrics = {
            "id_slot": body.get("id_slot", 0),
            "filename": body.get("filename", self.slot_filename),
            "n_restored": n_restored,
            "n_read": body.get("n_read", 0),
            "restore_ms": body.get("timings", {}).get("restore_ms", 0.0),
        }

        if stop_on_exit and self.llama_proc is not None:
            terminate_process_group(self.llama_proc.pid, grace_sec=10.0)
            try:
                self.llama_proc.wait(timeout=5)
            except Exception:
                pass
            self.llama_proc = None
            self._evict_file_page_cache([self.llama_model_path, self.slot_save_dir / self.slot_filename])
            self.verify_vram_exit_barrier("final_exit")

        self.transition(CombineState.COMPLETED, "Stage D combine cycle completed cleanly")

    def summary_dict(self) -> dict[str, Any]:
        return {
            "final_state": self.state.value,
            "host": self.host,
            "port": self.port,
            "max_retries": 0,
            "slot_save": self.slot_save_metrics,
            "slot_restore": self.slot_restore_metrics,
            "generated_images": self.generated_images,
            "vram_barriers": self.vram_barriers,
            "ple_snapshots": self.ple_snapshots,
            "sla_summary": {
                "baseline_pswpout": self.baseline_pswpout,
                "max_pswpout_delta": self.max_pswpout_delta,
                "disk_swap_used_kb": self.disk_swap_used_kb,
                "max_disk_swap_write_sectors_delta": self.max_disk_swap_write_sectors_delta,
                "max_zram_orig_delta_mib": round(self.max_zram_orig_delta_mib, 3),
                "max_proc_swap_kb": self.max_proc_swap_kb,
                "min_mem_avail_gib": round(self.min_mem_avail_gib, 3),
                "max_vram_gib": round(self.max_vram_gib, 3),
                "max_ple_rss_kb": self.max_ple_rss_kb,
                "max_swap_kb": self.max_swap_kb,
            },
            "state_history": self.state_history,
            "abort_reason": self.abort_reason,
        }


def _make_synthetic_png(path: Path, width: int = 64, height: int = 64, blank: bool = False) -> None:
    """Create a valid dark-obsidian architectural wireframe PNG file for pure-CPU self-testing."""
    w = max(16, int(width))
    h = max(16, int(height))
    if blank:
        row_bytes = b"\x00" + (b"\x80\x80\x80" * w)
        raw_data = row_bytes * h
    else:
        margin_x = max(4, w // 12)
        margin_y = max(4, h // 12)
        grid_step_x = max(12, w // 8)
        grid_step_y = max(12, h // 8)
        rows_list: list[bytes] = []
        for y in range(h):
            ny = y / max(1, h - 1)
            row = bytearray(1 + w * 3)
            row[0] = 0
            on_border_y = y in (margin_y, margin_y + 1, h - 1 - margin_y, h - 2 - margin_y)
            on_grid_y = (y % grid_step_y == 0) and (margin_y <= y <= h - 1 - margin_y)
            base_g_row = int(17 + 14 * (1.0 - ny))
            base_b_row = int(24 + 18 * (1.0 - ny))
            for x in range(w):
                nx = x / max(1, w - 1)
                r = min(26, max(14, int(14 + 12 * (0.5 * nx + 0.5 * (1.0 - ny)))))
                g = min(31, max(17, int(base_g_row + 4 * nx)))
                b = min(42, max(24, int(base_b_row + 6 * nx)))
                on_border_x = x in (margin_x, margin_x + 1, w - 1 - margin_x, w - 2 - margin_x)
                on_grid_x = (x % grid_step_x == 0) and (margin_x <= x <= w - 1 - margin_x)
                in_frame = (margin_x <= x <= w - 1 - margin_x) and (margin_y <= y <= h - 1 - margin_y)
                on_diag = in_frame and (abs((x * h) - (y * w)) <= max(w, h) // 2)
                if (on_border_y and margin_x <= x <= w - 1 - margin_x) or (on_border_x and margin_y <= y <= h - 1 - margin_y):
                    r, g, b = 200, 164, 93
                elif on_grid_x or on_grid_y or on_diag:
                    r, g, b = 96, 82, 148
                pos = 1 + x * 3
                row[pos] = r
                row[pos + 1] = g
                row[pos + 2] = b
            rows_list.append(bytes(row))
        raw_data = b"".join(rows_list)

    def _chunk(ctype: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw_data, level=1)
    png_bytes = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes)


def run_cpu_self_test() -> int:
    """Pure CPU self-test of the Stage D state machine, security checks, and PNG verifier."""
    with tempfile.TemporaryDirectory(prefix="smartllm_combine_test_") as tmp:
        tmp_dir = Path(tmp)

        # 1. Verify host=127.0.0.1 security invariant
        try:
            SequentialGPUCombineMachine(host="0.0.0.0", no_checkpoint_log=True)
            raise AssertionError("Expected SecurityInvariantError for host=0.0.0.0")
        except SecurityInvariantError:
            pass

        # 2. Verify PNG artifact validator (valid vs blank)
        good_png = tmp_dir / "good.png"
        blank_png = tmp_dir / "blank.png"
        _make_synthetic_png(good_png, 128, 128, blank=False)
        _make_synthetic_png(blank_png, 128, 128, blank=True)
        res_good = verify_png_artifact(good_png, expected_width=128, expected_height=128)
        res_blank = verify_png_artifact(blank_png, expected_width=128, expected_height=128)
        assert res_good["valid"] is True and res_good["pixel_std"] > 50.0, f"Good PNG failed: {res_good}"
        assert res_blank["valid"] is False, f"Blank PNG should have failed: {res_blank}"

        # 3. Create mock llama-server and mock sd-cli scripts for full state-machine CPU dry-run
        mock_llama = tmp_dir / "mock_llama_server.py"
        mock_llama.write_text(
            """#!/usr/bin/env python3
import argparse, json, sys, signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

parser = argparse.ArgumentParser()
parser.add_argument("-m", default="")
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=18089)
parser.add_argument("--slots", action="store_true")
parser.add_argument("--slot-save-path", type=Path, required=True)
args, _ = parser.parse_known_args()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a): pass
    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path.startswith("/health"):
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": "not found"})
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        data = json.loads(raw) if raw else {}
        if self.path.startswith("/completion"):
            self._send(200, {"content": "ok", "tokens_cached": 24})
        elif self.path.startswith("/slots/0"):
            qs = parse_qs(urlparse(self.path).query)
            action = qs.get("action", [""])[0]
            fname = data.get("filename", "slot.bin")
            fpath = args.slot_save_path / fname
            if action == "save":
                payload = b"KV_SLOT_CACHE_TEST_BYTES" * 64
                fpath.write_bytes(payload)
                self._send(200, {"id_slot": 0, "filename": fname, "n_saved": 24, "n_written": len(payload), "timings": {"save_ms": 1.2}})
            elif action == "restore":
                sz = fpath.stat().st_size if fpath.exists() else 0
                self._send(200, {"id_slot": 0, "filename": fname, "n_restored": 24, "n_read": sz, "timings": {"restore_ms": 0.9}})
            else:
                self._send(400, {"error": "bad action"})
        else:
            self._send(404, {"error": "not found"})

srv = HTTPServer((args.host, args.port), Handler)
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
srv.serve_forever()
""",
            encoding="utf-8",
        )
        mock_llama.chmod(0o755)

        mock_sd = tmp_dir / "mock_sd_cli.py"
        mock_sd.write_text(
            f"""#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, {repr(str(ROOT))})
from scripts.combine.gpu_switch import _make_synthetic_png

parser = argparse.ArgumentParser()
parser.add_argument("-W", type=int, default=1024)
parser.add_argument("-H", type=int, default=1024)
parser.add_argument("-o", type=Path, required=True)
parser.add_argument("--batch-json", type=Path, default=None)
args, _ = parser.parse_known_args()

if args.batch_json and args.batch_json.exists():
    items = json.loads(args.batch_json.read_text(encoding="utf-8"))
    for it in items:
        _make_synthetic_png(Path(it["output_path"]), int(it["width"]), int(it["height"]), blank=False)
else:
    _make_synthetic_png(args.o, args.W, args.H, blank=False)
""",
            encoding="utf-8",
        )
        mock_sd.chmod(0o755)

        # Find an ephemeral port on 127.0.0.1
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]

        mock_exit_ok = lambda idle, margin: {
            "passed": True,
            "memory_used_mib": 31.0,
            "max_allowed_mib": idle + margin,
            "active_compute_apps": [],
            "error": None,
        }

        sm = SequentialGPUCombineMachine(
            host="127.0.0.1",
            port=free_port,
            llama_server_bin=mock_llama,
            llama_model_path=tmp_dir / "dummy.gguf",
            slot_save_dir=tmp_dir / "slots",
            sd_cli_bin=mock_sd,
            dit_model_path=tmp_dir / "dit.safetensors",
            llm_encoder_path=tmp_dir / "te.safetensors",
            vae_model_path=tmp_dir / "vae.safetensors",
            sd_out_dir=tmp_dir / "sd_out",
            sd_width=256,
            sd_height=256,
            no_checkpoint_log=True,
            exit_check_fn=mock_exit_ok,
        )
        sm.start_llm(seed_prompt="System: test slot 0 cache")
        sm.save_slot_and_stop_llm()
        sm.run_sd_batch(
            [
                {"id": "hero_test", "prompt": "Industrial precision drone", "width": 256, "height": 256},
                {"id": "detail_test", "prompt": "LiDAR telemetry array", "width": 256, "height": 256},
            ]
        )
        sm.restart_llm_and_restore_slot(stop_on_exit=True)
        summary = sm.summary_dict()
        visited = [st["state"] for st in summary["state_history"]]
        expected_sequence = [
            "IDLE",
            "LLM_STARTING",
            "LLM_ACTIVE",
            "SLOT_SAVING",
            "LLM_STOPPING",
            "VRAM_VERIFY_POST_LLM",
            "SD_BATCH_RUNNING",
            "VRAM_VERIFY_POST_SD",
            "LLM_RESTARTING",
            "SLOT_RESTORING",
            "COMPLETED",
        ]
        assert visited == expected_sequence, f"State sequence mismatch: {visited} != {expected_sequence}"
        assert summary["slot_save"]["n_saved"] == 24
        assert summary["slot_restore"]["n_restored"] == 24
        assert len(summary["generated_images"]) == 2
        print(json.dumps({"self_test": "PASSED", "visited_states": visited}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage D Sequential GPU Combine state machine (LLM <-> stable-diffusion.cpp)."
    )
    parser.add_argument("--self-test", action="store_true", help="Run pure-CPU state machine self-test")
    parser.add_argument(
        "--mode",
        choices=("switch", "sd-only"),
        default="switch",
        help="Execution mode: 'switch' (full LLM->SD->LLM cycle) or 'sd-only' (single/batch SD under SLA)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run full switch cycle with seed prompt & clean exit")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="LLM server bind host (MUST be 127.0.0.1)")
    parser.add_argument("--port", type=int, default=18080, help="LLM server bind port")
    parser.add_argument("--llama-server", type=Path, default=DEFAULT_LLAMA_SERVER)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_205E, help="GGUF model path for llama-server")
    parser.add_argument(
        "--llama-arg",
        action="append",
        default=[],
        help="Additional argument passed to llama-server (repeatable)",
    )
    parser.add_argument("--slot-save-dir", type=Path, default=DEFAULT_SLOT_SAVE_DIR)
    parser.add_argument("--slot-filename", type=str, default="slot_0_combine.bin")
    parser.add_argument(
        "--seed-prompt",
        type=str,
        default="Design a Swiss-grid telemetry header in OKLCH.",
        help="Prompt cached in slot 0 before saving slot state",
    )
    parser.add_argument("--sd-cli", type=Path, default=DEFAULT_SD_CLI)
    parser.add_argument("--dit-model", type=Path, default=DEFAULT_DIT_FP8)
    parser.add_argument("--llm-encoder", type=Path, default=DEFAULT_QWEN_TE)
    parser.add_argument("--vae-model", type=Path, default=DEFAULT_VAE)
    parser.add_argument("--sd-type", type=str, default="q8_0")
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--cfg-scale", type=float, default=1.0)
    parser.add_argument("--flow-shift", type=float, default=3.0)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--prompt",
        type=str,
        default=(
            "Photorealistic architectural studio shot of an autonomous precision-agriculture "
            "drone platform on a light bone laboratory surface, carbon-fiber tri-rotor frame, "
            "amber telemetry LEDs, crisp lighting, sharp focus."
        ),
    )
    parser.add_argument("--prompts-json", type=Path, help="Optional zimage_prompts.json file for batch generation")
    parser.add_argument("--output", type=Path, help="Explicit output PNG path for single-image generation")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_SD_OUT_DIR)
    parser.add_argument("--sd-timeout-sec", type=float, default=600.0, help="SLA timeout for sd.cpp (<= 600s)")
    parser.add_argument("--idle-mib", type=float, default=31.0)
    parser.add_argument("--margin-mib", type=float, default=64.0)
    parser.add_argument("--keep-llm-alive", action="store_true", help="Leave llama-server running after restore")
    parser.add_argument("--summary-out", type=Path, help="Write JSON state-machine telemetry summary to path")
    parser.add_argument("--hypothesis", type=str, default="Stage D sequential GPU switch maintains max 1 model in VRAM and 0 swap")
    parser.add_argument("--expected", type=str, default="Slot save/restore n_restored==n_saved, valid 1024x1024 PNG, clean VRAM exit")
    parser.add_argument("--factor", type=str, default="Sequential LLM<->sd.cpp state machine under SLA watchdog")
    parser.add_argument("--_under-watchdog", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args(argv)

    if args.self_test:
        return run_cpu_self_test()

    # Enforce host == 127.0.0.1 before touching locks or GPU
    if args.host != "127.0.0.1":
        print(
            json.dumps({"error": "SECURITY_VIOLATION", "message": f"--host must be 127.0.0.1, got {args.host}"}),
            file=sys.stderr,
        )
        return 2

    # Ensure single GPU owner via .system/gpu.lock (unless already held by our ancestor gpu_run.py)
    anc_lock_pid = _ancestor_holds_lock(DEFAULT_LOCK_PATH)
    anc_wd_pid = _ancestor_is_watchdog()
    lock_file_handle = None

    if anc_lock_pid is None and not args._under_watchdog:
        DEFAULT_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        lock_file_handle = DEFAULT_LOCK_PATH.open("a+", encoding="utf-8")
        try:
            fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(
                json.dumps(
                    {
                        "error": "GPU_LOCK_BUSY",
                        "message": f"Another process holds {DEFAULT_LOCK_PATH}; aborting without retry.",
                    }
                ),
                file=sys.stderr,
            )
            lock_file_handle.close()
            return 3

        # Append one line to .system/gpu_runs.log before launching under sla_watchdog.py
        ts_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cmd_str = " ".join([sys.executable, str(Path(__file__).resolve())] + sys.argv[1:])
        log_line = (
            f"{ts_start}\twp=WP-A3\t"
            f"hypothesis={args.hypothesis.replace(chr(9), ' ')}\t"
            f"expected={args.expected.replace(chr(9), ' ')}\t"
            f"single_factor={args.factor.replace(chr(9), ' ')}\t"
            f"cmd={cmd_str}\n"
        )
        with DEFAULT_LOG_PATH.open("a", encoding="utf-8") as lf:
            lf.write(log_line)
            lf.flush()

    try:
        # If not already supervised by sla_watchdog.py, re-invoke self under sla_watchdog.py
        if anc_wd_pid is None and not args._under_watchdog:
            wd_cmd = [
                sys.executable,
                str(WATCHDOG_SCRIPT),
                "--interval-sec",
                "1.0",
                "--max-proc-swap-mib",
                str(DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB),
                "--check-ple",
                "--",
                sys.executable,
                str(Path(__file__).resolve()),
                "--_under-watchdog",
            ] + sys.argv[1:]
            proc_wd = subprocess.run(wd_cmd, check=False)
            return proc_wd.returncode

        # Load prompts from --prompts-json or single --prompt
        prompts_list: list[dict[str, Any]] = []
        if args.prompts_json:
            raw_data = json.loads(args.prompts_json.read_text(encoding="utf-8"))
            if isinstance(raw_data, dict) and "prompts" in raw_data:
                raw_data = raw_data["prompts"]
            if not isinstance(raw_data, list):
                raise CombineError(f"Invalid prompts JSON format in {args.prompts_json}")
            prompts_list = list(raw_data)
        else:
            out_path = args.output if args.output else (args.out_dir / "zimage_1024.png")
            prompts_list = [
                {
                    "id": out_path.stem,
                    "prompt": args.prompt,
                    "width": args.width,
                    "height": args.height,
                    "steps": args.steps,
                    "cfg_scale": args.cfg_scale,
                    "seed": args.seed,
                    "output_path": str(out_path),
                }
            ]

        llama_extra = list(args.llama_arg)
        if not llama_extra:
            # Verified WP-B1/Stage D runtime args on b11960 (12 GB VRAM + 32 GB RAM, 0 B PLE Rss)
            llama_extra = [
                "--lazy-mode",
                "direct",
                "--n-cpu-moe",
                "48",
                "-nr",
                "--moe-cache-mib",
                "4096",
                "--moe-cache-cpu-share",
                "0.15",
                "-fa",
                "on",
                "-ctk",
                "q8_0",
                "-ctv",
                "q8_0",
                "-c",
                "32768",
                "-ub",
                "512",
                "-ngl",
                "99",
                "-np",
                "1",
                "--cache-ram",
                "0",
                "--spec-type",
                "draft-mtp",
                "--spec-draft-n-max",
                "3",
                "--spec-draft-p-min",
                "0.5",
                "-ctkd",
                "q8_0",
                "-ctvd",
                "q8_0",
                "--no-webui",
            ]

        sm = SequentialGPUCombineMachine(
            host=args.host,
            port=args.port,
            llama_server_bin=args.llama_server,
            llama_model_path=args.model,
            llama_extra_args=llama_extra,
            slot_save_dir=args.slot_save_dir,
            slot_filename=args.slot_filename,
            sd_cli_bin=args.sd_cli,
            dit_model_path=args.dit_model,
            llm_encoder_path=args.llm_encoder,
            vae_model_path=args.vae_model,
            sd_out_dir=args.out_dir,
            sd_type=args.sd_type,
            sd_steps=args.steps,
            sd_cfg=args.cfg_scale,
            sd_flow_shift=args.flow_shift,
            sd_width=args.width,
            sd_height=args.height,
            sd_seed=args.seed,
            idle_vram_mib=args.idle_mib,
            vram_margin_mib=args.margin_mib,
        )

        def _handle_sigterm(signum: int, _frame: Any) -> None:
            sm._kill_active_processes()
            sys.exit(128 + signum)

        signal.signal(signal.SIGTERM, _handle_sigterm)
        signal.signal(signal.SIGINT, _handle_sigterm)

        try:
            if args.mode == "sd-only":
                sm.run_sd_batch(prompts_list, batch_timeout_sec=args.sd_timeout_sec)
                sm.transition(CombineState.COMPLETED, "sd-only batch completed cleanly")
            else:
                sm.start_llm(seed_prompt=args.seed_prompt)
                sm.save_slot_and_stop_llm()
                sm.run_sd_batch(prompts_list, batch_timeout_sec=args.sd_timeout_sec)
                sm.restart_llm_and_restore_slot(stop_on_exit=not args.keep_llm_alive)
        except CombineError as exc:
            summary = sm.summary_dict()
            if args.summary_out:
                args.summary_out.parent.mkdir(parents=True, exist_ok=True)
                args.summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(json.dumps(summary, indent=2), file=sys.stderr)
            return 1

        summary = sm.summary_dict()
        if args.summary_out:
            args.summary_out.parent.mkdir(parents=True, exist_ok=True)
            args.summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        if lock_file_handle is not None:
            try:
                fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
            finally:
                lock_file_handle.close()


if __name__ == "__main__":
    sys.exit(main())
