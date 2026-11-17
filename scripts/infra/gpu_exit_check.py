#!/usr/bin/env python3
"""GPU exit hygiene checker for SmartLLM v2 (OPUS_MASTER_PLAN_V2 §0.2).

Verifies after any GPU run:
1. Non-display compute apps list is empty (filtering out OS display compositors
   like kwin_wayland / Xorg / Xwayland that hold <= 64 MiB on CachyOS KDE Wayland).
2. Total GPU memory.used <= idle_mib + margin_mib (default: 31 + 64 = 95 MiB).
"""

from __future__ import annotations

import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

DEFAULT_IDLE_MIB = 31.0
DEFAULT_MARGIN_MIB = 64.0
DEFAULT_DISPLAY_PROC_MAX_MIB = 64.0

OS_DISPLAY_PROCS = (
    "kwin_wayland",
    "kwin_x11",
    "xorg",
    "xwayland",
    "plasmashell",
    "gnome-shell",
    "hyprland",
    "sway",
    "mutter",
    "wayland",
)


def _is_display_compositor(proc_name: str, used_mib: float) -> bool:
    if used_mib > DEFAULT_DISPLAY_PROC_MAX_MIB:
        return False
    low = proc_name.strip().lower()
    if "--type=gpu-process" in low:
        return True
    base = Path(proc_name.strip()).name.lower()
    return any(base == dp or base.startswith(dp) for dp in OS_DISPLAY_PROCS)


def _query_nvml_fallback() -> tuple[float, float] | None:
    """Fallback to libnvidia-ml.so.1 if nvidia-smi CLI is unavailable."""
    for libname in ("libnvidia-ml.so.1", "libnvidia-ml.so"):
        try:
            nvml = ctypes.CDLL(libname)
            if nvml.nvmlInit_v2() != 0:
                continue
            handle = ctypes.c_void_p()
            if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) != 0:
                nvml.nvmlShutdown()
                continue

            class _NvmlMemory(ctypes.Structure):
                _fields_ = [
                    ("total", ctypes.c_ulonglong),
                    ("free", ctypes.c_ulonglong),
                    ("used", ctypes.c_ulonglong),
                ]

            mem = _NvmlMemory()
            rc = nvml.nvmlDeviceGetMemoryInfo(handle, ctypes.byref(mem))
            nvml.nvmlShutdown()
            if rc == 0:
                return mem.used / (1024.0 * 1024.0), mem.total / (1024.0 * 1024.0)
        except Exception:
            continue
    return None


def check_gpu_exit(
    idle_mib: float = DEFAULT_IDLE_MIB,
    margin_mib: float = DEFAULT_MARGIN_MIB,
) -> dict[str, Any]:
    max_allowed_mib = idle_mib + margin_mib
    mem_used_mib = -1.0
    mem_total_mib = -1.0
    raw_compute_apps: list[dict[str, Any]] = []
    active_compute_apps: list[dict[str, Any]] = []
    error_msg: str | None = None

    try:
        p_mem = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if p_mem.returncode == 0 and p_mem.stdout.strip():
            first_line = p_mem.stdout.strip().splitlines()[0]
            parts = [x.strip() for x in first_line.split(",")]
            mem_used_mib = float(parts[0])
            mem_total_mib = float(parts[1]) if len(parts) > 1 else 12282.0
        else:
            nvml_res = _query_nvml_fallback()
            if nvml_res is not None:
                mem_used_mib, mem_total_mib = nvml_res
            else:
                error_msg = f"nvidia-smi memory query failed: {p_mem.stderr.strip()}"

        p_apps = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,process_name,used_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if p_apps.returncode == 0 and p_apps.stdout.strip():
            for line in p_apps.stdout.strip().splitlines():
                line_s = line.strip()
                if not line_s:
                    continue
                cols = [c.strip() for c in line_s.split(",")]
                if len(cols) < 2:
                    continue
                try:
                    pid = int(cols[0])
                except ValueError:
                    continue
                proc_name = cols[1]
                try:
                    used_proc_mib = float(cols[2]) if len(cols) > 2 else 0.0
                except ValueError:
                    used_proc_mib = 0.0
                app_entry = {
                    "pid": pid,
                    "process_name": proc_name,
                    "used_memory_mib": used_proc_mib,
                }
                raw_compute_apps.append(app_entry)
                if not _is_display_compositor(proc_name, used_proc_mib):
                    active_compute_apps.append(app_entry)
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"

    passed = (
        error_msg is None
        and mem_used_mib >= 0.0
        and mem_used_mib <= max_allowed_mib
        and len(active_compute_apps) == 0
    )
    return {
        "passed": passed,
        "memory_used_mib": mem_used_mib,
        "memory_total_mib": mem_total_mib,
        "idle_baseline_mib": idle_mib,
        "margin_mib": margin_mib,
        "max_allowed_mib": max_allowed_mib,
        "active_compute_apps": active_compute_apps,
        "raw_compute_apps": raw_compute_apps,
        "error": error_msg,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify clean GPU VRAM exit state.")
    parser.add_argument(
        "--idle-mib",
        type=float,
        default=DEFAULT_IDLE_MIB,
        help="Idle OS desktop VRAM baseline in MiB (default: 31.0)",
    )
    parser.add_argument(
        "--margin-mib",
        type=float,
        default=DEFAULT_MARGIN_MIB,
        help="Allowed margin above idle in MiB (default: 64.0)",
    )
    args = parser.parse_args(argv)
    res = check_gpu_exit(idle_mib=args.idle_mib, margin_mib=args.margin_mib)
    print(json.dumps(res, indent=2))
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
