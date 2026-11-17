#!/usr/bin/env python3
"""Step 7.5 / Stage B Cross-Platform Anti-Swap & Multimodal Smoke Test (`llama-server`).

Supports CachyOS Linux (`/proc/vmstat`, `/proc/meminfo`, `/proc/<pid>/smaps_rollup`, `/proc/<pid>/smaps`,
`nvidia-smi`) and Windows 11 (`GlobalMemoryStatusEx`, `GetProcessMemoryInfo`, Win32 PDH) without
import-time crashes on either OS.

Hard Runtime SLA Gates (CLAUDE.md §4.2 & OPUS_MASTER_PLAN_V2.md §0.3):
- `pswpout_delta == 0` (`/proc/vmstat` delta from job start)
- `min_avail_phys_gib >= 3.0` (`MemAvailable >= 3.0 GiB` in `/proc/meminfo`)
- `max_gpu_used_mib <= 10752` (`VRAM <= 10.5 GiB`)
- `max_ple_rss_kb == 0` (`per_layer_token_embd` `Rss == 0 kB` in `/proc/<pid>/smaps`)
- Clean exit: `post_compute_apps == []` and `post_vram_used_mib <= idle_vram_mib + 64`
"""

from __future__ import annotations

import base64
import ctypes
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Ensure scripts/ is importable
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import platform_paths as pp  # noqa: E402

ROOT: Path = pp.ROOT
SERVER_EXE: Path = pp.SERVER_EXE
MMPROJ_PATH: Path = pp.MMPROJ_PATH
IQ3_S_PATH: Path = pp.IQ3_S_PATH
IQ3_XXS_PATH: Path = pp.IQ3_XXS_PATH
VISION_PNG: Path = pp.VISION_PNG
OUT_DIR: Path = pp.STEP7_RAW_DIR
OUT_JSON: Path = OUT_DIR / "smoke_antiswap_results.json"

HOST = "127.0.0.1"
PORT = 8080
BASE_URL = f"http://{HOST}:{PORT}"

SLA_MIN_MEM_AVAIL_GIB: float = 3.0
SLA_MIN_MEM_AVAIL_MIB: float = SLA_MIN_MEM_AVAIL_GIB * 1024.0
SLA_MAX_VRAM_GIB: float = 10.5
SLA_MAX_VRAM_MIB: int = int(SLA_MAX_VRAM_GIB * 1024)
SLA_MAX_PSWPOUT_DELTA: int = 0
SLA_MAX_PLE_RSS_KB: int = 0

if sys.platform == "win32":
    from ctypes import wintypes

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

    class _PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    class _PDH_FMT_COUNTERVALUE(ctypes.Structure):
        _fields_ = [
            ("CStatus", wintypes.DWORD),
            ("pad", wintypes.DWORD),
            ("doubleValue", ctypes.c_double),
        ]


def read_proc_meminfo(proc_meminfo_path: str = "/proc/meminfo") -> dict[str, int]:
    """Parse `/proc/meminfo` values in kB on Linux."""
    info: dict[str, int] = {}
    if not os.path.exists(proc_meminfo_path):
        return info
    try:
        with open(proc_meminfo_path, "r", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split(":")
                if len(parts) != 2:
                    continue
                key = parts[0].strip()
                val_parts = parts[1].strip().split()
                if val_parts and val_parts[0].isdigit():
                    val_int = int(val_parts[0])
                    info[key] = val_int
                    info[f"{key}_kB"] = val_int
    except Exception:
        pass
    return info


def read_proc_vmstat(proc_vmstat_path: str = "/proc/vmstat") -> dict[str, int]:
    """Parse `/proc/vmstat` counters (`pswpin`, `pswpout`, `pgpgin`, `pgpgout`) on Linux."""
    stats: dict[str, int] = {}
    if not os.path.exists(proc_vmstat_path):
        return stats
    try:
        with open(proc_vmstat_path, "r", encoding="utf-8") as fh:
            for line in fh:
                parts = line.strip().split()
                if len(parts) == 2 and (parts[1].isdigit() or (parts[1].startswith("-") and parts[1][1:].isdigit())):
                    stats[parts[0]] = int(parts[1])
    except Exception:
        pass
    return stats


def read_proc_smaps_rollup(pid: int, proc_root: str = "/proc") -> dict[str, int]:
    """Parse `/proc/<pid>/smaps_rollup` values in kB on Linux."""
    rollup_path = os.path.join(proc_root, str(pid), "smaps_rollup")
    out: dict[str, int] = {}
    if not os.path.exists(rollup_path):
        return out
    try:
        with open(rollup_path, "r", encoding="utf-8") as fh:
            for line in fh:
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                toks = v.strip().split()
                if toks and toks[0].isdigit():
                    val_int = int(toks[0])
                    out[k.strip()] = val_int
                    out[f"{k.strip()}_kB"] = val_int
    except Exception:
        pass
    return out


def get_gguf_ple_byte_range(gguf_path: Path | str | None) -> tuple[int, int] | None:
    """Inspect GGUF header (<= 2 MB) to locate exact file byte range of `per_layer_token_embd.weight`."""
    if not gguf_path:
        return None
    p = Path(gguf_path)
    if not p.exists():
        return None
    gguf_py_dir = ROOT / "tools" / "llama.cpp" / "gguf-py"
    if gguf_py_dir.exists() and str(gguf_py_dir) not in sys.path:
        sys.path.insert(0, str(gguf_py_dir))
    try:
        import gguf  # type: ignore

        reader = gguf.GGUFReader(str(p), "r")
        for t in reader.tensors:
            if "per_layer_token_embd" in t.name:
                start = int(reader.data_offset + t.data_offset)
                end = int(start + t.n_bytes)
                return (start, end)
    except Exception:
        pass
    return None


def check_ple_rss_kb(
    pid: int,
    ple_byte_range: tuple[int, int] | None = None,
    proc_root: str = "/proc",
    smaps_text_override: str | None = None,
) -> dict[str, Any]:
    """Measure resident RAM (`Rss` in kB) of `per_layer_token_embd` (PLE) in `/proc/<pid>/smaps`.

    Under `--lazy-mode direct`, `per_layer_token_embd.weight` is unmapped via `munmap` and read
    via `O_DIRECT pread`, so either zero VMAs overlap `ple_byte_range` or their `Rss` is `0 kB`.
    """
    smaps_path = os.path.join(proc_root, str(pid), "smaps")
    text = smaps_text_override
    if text is None:
        if not os.path.exists(smaps_path):
            return {"available": False, "ple_rss_kb": 0, "ple_vmas_count": 0}
        try:
            with open(smaps_path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception:
            return {"available": False, "ple_rss_kb": 0, "ple_vmas_count": 0}

    header_re = re.compile(
        r"^([0-9a-fA-F]+)-([0-9a-fA-F]+)\s+\S+\s+([0-9a-fA-F]+)\s+\S+\s+\d+\s*(.*)$"
    )
    ple_rss_kb = 0
    ple_vmas_count = 0
    total_gguf_file_rss_kb = 0

    in_ple_vma = False
    in_gguf_vma = False

    for line in text.splitlines():
        m = header_re.match(line)
        if m:
            start_addr = int(m.group(1), 16)
            end_addr = int(m.group(2), 16)
            vma_size = max(0, end_addr - start_addr)
            file_off = int(m.group(3), 16)
            pathname = (m.group(4) or "").strip()

            is_gguf = pathname.endswith(".gguf") and "mmproj" not in os.path.basename(pathname).lower()
            in_gguf_vma = is_gguf
            in_ple_vma = False

            if is_gguf:
                base_lower = os.path.basename(pathname).lower()
                if "per_layer_token_embd" in base_lower or "ple" in base_lower:
                    in_ple_vma = True
                elif ple_byte_range is not None:
                    ple_start, ple_end = ple_byte_range
                    vma_end = file_off + vma_size
                    if max(file_off, ple_start) < min(vma_end, ple_end):
                        in_ple_vma = True
                elif vma_size >= 24 * (1024**3):
                    # Single unsplit mapping >= 24 GiB covering the 26.82 GiB PLE table
                    in_ple_vma = True

            if in_ple_vma:
                ple_vmas_count += 1
            continue

        if line.startswith("Rss:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                rss_val = int(parts[1])
                if in_gguf_vma:
                    total_gguf_file_rss_kb += rss_val
                if in_ple_vma:
                    ple_rss_kb += rss_val

    return {
        "available": True,
        "ple_rss_kb": ple_rss_kb,
        "ple_vmas_count": ple_vmas_count,
        "total_gguf_file_rss_kb": total_gguf_file_rss_kb,
        "ple_zero_rss_ok": ple_rss_kb <= SLA_MAX_PLE_RSS_KB,
    }


def get_phys_ram() -> tuple[float, float, float, float]:
    """Return `(avail_gib, avail_mib, used_gib, total_gib)` across Linux (`/proc/meminfo`) and Windows."""
    if sys.platform != "win32":
        info = read_proc_meminfo()
        total_kb = info.get("MemTotal", 0)
        avail_kb = info.get("MemAvailable", info.get("MemFree", 0))
        used_kb = max(0, total_kb - avail_kb)
        avail_mib = avail_kb / 1024.0
        avail_gib = avail_kb / (1024.0**2)
        used_gib = used_kb / (1024.0**2)
        total_gib = total_kb / (1024.0**2)
        return avail_gib, avail_mib, used_gib, total_gib

    st = _MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
    avail_mib = st.ullAvailPhys / (1024**2)
    avail_gib = st.ullAvailPhys / (1024**3)
    used_gib = (st.ullTotalPhys - st.ullAvailPhys) / (1024**3)
    total_gib = st.ullTotalPhys / (1024**3)
    return avail_gib, avail_mib, used_gib, total_gib


def get_process_mem_gib(pid: int) -> tuple[float | None, float | None]:
    """Return `(private_usage_gib, working_set_gib)` for `pid` across Linux and Windows."""
    if sys.platform != "win32":
        rollup = read_proc_smaps_rollup(pid)
        if not rollup:
            return None, None
        rss_kb = rollup.get("Rss", 0)
        anon_kb = rollup.get("Anonymous", rollup.get("Private_Dirty", 0) + rollup.get("Private_Clean", 0))
        return anon_kb / (1024.0**2), rss_kb / (1024.0**2)

    hproc = ctypes.windll.kernel32.OpenProcess(0x1000 | 0x0010, False, int(pid))
    if not hproc:
        return None, None
    try:
        pmc = _PROCESS_MEMORY_COUNTERS_EX()
        pmc.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS_EX)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(hproc, ctypes.byref(pmc), pmc.cb)
        if not ok:
            return None, None
        return pmc.PrivateUsage / (1024**3), pmc.WorkingSetSize / (1024**3)
    finally:
        ctypes.windll.kernel32.CloseHandle(hproc)


def query_nvidia_smi() -> tuple[int, list[dict[str, Any]]]:
    """Return `(total_used_mib, compute_apps)`."""
    used_mib = -1
    apps: list[dict[str, Any]] = []
    try:
        p1 = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if p1.returncode == 0 and p1.stdout.strip():
            used_mib = int(p1.stdout.strip().splitlines()[0].strip())
        p2 = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_gpu_memory", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if p2.returncode == 0:
            for line in p2.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = [x.strip() for x in line.split(",")]
                if len(parts) >= 3:
                    apps.append(
                        {
                            "pid": int(parts[0]) if parts[0].isdigit() else parts[0],
                            "name": parts[1],
                            "used_mib": int(parts[2]) if parts[2].isdigit() else parts[2],
                        }
                    )
    except Exception:
        pass
    return used_mib, apps


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


class TelemetryRecorder:
    """Background 250 ms telemetry collector with Zero-Swap / MemAvailable / VRAM / PLE-RSS SLA checks."""

    def __init__(
        self,
        pid: int,
        watchdog_min_avail_mib: float = SLA_MIN_MEM_AVAIL_MIB,
        on_watchdog: Any = None,
        model_path: Path | str | None = None,
    ):
        self.pid = int(pid)
        self.watchdog_min_avail_mib = float(watchdog_min_avail_mib)
        self.on_watchdog = on_watchdog
        self.model_path = Path(model_path) if model_path else None
        self.ple_byte_range = get_gguf_ple_byte_range(self.model_path)
        self.aborted_due_to_ram_pressure = False
        self.abort_reason: str = ""
        self.samples: list[dict[str, Any]] = []
        self._ready_t: float | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._t0 = time.perf_counter()

        vm0 = read_proc_vmstat() if sys.platform != "win32" else {}
        self.pswpout_start: int = vm0.get("pswpout", 0)
        self.pswpin_start: int = vm0.get("pswpin", 0)

    def mark_ready(self) -> None:
        self._ready_t = round(time.perf_counter() - self._t0, 2)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)

    @staticmethod
    def _read_pdh(pdh: Any, hc: Any) -> float | None:
        if hc is None:
            return None
        val = _PDH_FMT_COUNTERVALUE()
        if pdh.PdhGetFormattedCounterValue(hc, 0x00000200, None, ctypes.byref(val)) == 0:
            return round(float(val.doubleValue), 4)
        return None

    def _loop(self) -> None:
        if sys.platform != "win32":
            self._loop_linux()
        else:
            self._loop_windows()

    def _loop_linux(self) -> None:
        tick = 0
        last_gpu_mib = -1
        last_pswpout = self.pswpout_start
        last_t = time.perf_counter()
        last_ple_rss_kb = 0

        while not self._stop.is_set():
            now_t = time.perf_counter()
            dt = max(1e-3, now_t - last_t)

            meminfo = read_proc_meminfo()
            vmstat = read_proc_vmstat()
            rollup = read_proc_smaps_rollup(self.pid)

            total_kb = meminfo.get("MemTotal", 0)
            avail_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
            avail_mib = avail_kb / 1024.0
            avail_gib = avail_kb / (1024.0**2)
            used_gib = max(0, total_kb - avail_kb) / (1024.0**2)

            swap_total_kb = meminfo.get("SwapTotal", 0)
            swap_free_kb = meminfo.get("SwapFree", 0)
            swap_used_kb = max(0, swap_total_kb - swap_free_kb)
            swap_pct = (swap_used_kb * 100.0 / swap_total_kb) if swap_total_kb > 0 else 0.0

            cur_pswpout = vmstat.get("pswpout", self.pswpout_start)
            pswpout_delta = cur_pswpout - self.pswpout_start
            pswpout_rate = max(0.0, (cur_pswpout - last_pswpout) / dt)
            last_pswpout = cur_pswpout
            last_t = now_t

            ws_gib: float | None = None
            cpu_priv_ws_gib: float | None = None
            shareable_mmap_ws_gib: float | None = None
            proc_swap_kb: int = 0
            if rollup:
                rss_kb = rollup.get("Rss", 0)
                anon_kb = rollup.get("Anonymous", 0)
                proc_swap_kb = rollup.get("Swap", 0)
                ws_gib = round(rss_kb / (1024.0**2), 4)
                cpu_priv_ws_gib = round(anon_kb / (1024.0**2), 4)
                shareable_mmap_ws_gib = round(max(0.0, (rss_kb - anon_kb) / (1024.0**2)), 4)

            if tick % 4 == 0:
                total_vram, _apps = query_nvidia_smi()
                if total_vram >= 0:
                    last_gpu_mib = total_vram
                ple_info = check_ple_rss_kb(self.pid, self.ple_byte_range)
                if ple_info.get("available"):
                    last_ple_rss_kb = int(ple_info.get("ple_rss_kb", 0))

            self.samples.append(
                {
                    "t": round(now_t - self._t0, 2),
                    "phase": "gen" if (self._ready_t is not None) else "load",
                    "avail_phys_gib": round(avail_gib, 4),
                    "avail_phys_mib": round(avail_mib, 1),
                    "used_phys_gib": round(used_gib, 4),
                    "private_commit_gib": cpu_priv_ws_gib,
                    "working_set_gib": ws_gib,
                    "cpu_private_ws_gib": cpu_priv_ws_gib,
                    "shareable_mmap_ws_gib": shareable_mmap_ws_gib,
                    "reclaimable_ram_gib": round(avail_gib, 4),
                    "pswpout": cur_pswpout,
                    "pswpout_delta": pswpout_delta,
                    "pswpout_per_sec": round(pswpout_rate, 4),
                    "pages_output_per_sec": round(pswpout_rate, 4),
                    "page_writes_per_sec": round(pswpout_rate, 4),
                    "pagefile_usage_pct": round(swap_pct, 4),
                    "proc_swap_kb": proc_swap_kb,
                    "ple_rss_kb": last_ple_rss_kb,
                    "gpu_used_mib": last_gpu_mib,
                }
            )

            # Enforce hard Zero-Swap SLA on Linux
            if (
                (self.watchdog_min_avail_mib > 0 and avail_mib < self.watchdog_min_avail_mib)
                or pswpout_delta > SLA_MAX_PSWPOUT_DELTA
                or (last_gpu_mib > SLA_MAX_VRAM_MIB)
            ):
                self.aborted_due_to_ram_pressure = True
                self.abort_reason = (
                    f"SLA breach: avail_mib={avail_mib:.1f}, pswpout_delta={pswpout_delta}, gpu_mib={last_gpu_mib}"
                )
                if self.on_watchdog is not None:
                    self.on_watchdog()
                break

            tick += 1
            time.sleep(0.25)

    def _loop_windows(self) -> None:
        pdh = ctypes.windll.pdh
        hq = wintypes.HANDLE()
        has_pdh = pdh.PdhOpenQueryW(None, 0, ctypes.byref(hq)) == 0
        c_pages: Any = None
        c_pgwrites: Any = None
        c_pgfile: Any = None
        c_priv_ws: Any = None
        c_pid_chk: Any = None

        def _try_add(path: str) -> Any:
            if not has_pdh:
                return None
            h = wintypes.HANDLE()
            return h if pdh.PdhAddEnglishCounterW(hq, path, 0, ctypes.byref(h)) == 0 else None

        if has_pdh:
            c_pages = _try_add(r"\Memory\Pages Output/sec")
            c_pgwrites = _try_add(r"\Memory\Page Writes/sec")
            c_pgfile = _try_add(r"\Paging File(_Total)\% Usage")
            c_priv_ws = _try_add(r"\Process(llama-server)\Working Set - Private")
            c_pid_chk = _try_add(r"\Process(llama-server)\ID Process")
            pdh.PdhCollectQueryData(hq)
        try:
            tick = 0
            last_gpu_mib = -1
            while not self._stop.is_set():
                avail_gib, avail_mib, used_gib, _total_gib = get_phys_ram()
                priv_commit_gib, ws_gib = get_process_mem_gib(self.pid)

                pages_out = None
                page_writes = None
                pgfile_pct = None
                cpu_priv_ws_gib = None
                if has_pdh:
                    if c_priv_ws is None:
                        c_priv_ws = _try_add(r"\Process(llama-server)\Working Set - Private")
                        c_pid_chk = _try_add(r"\Process(llama-server)\ID Process")
                    if pdh.PdhCollectQueryData(hq) == 0:
                        pages_out = self._read_pdh(pdh, c_pages)
                        page_writes = self._read_pdh(pdh, c_pgwrites)
                        pgfile_pct = self._read_pdh(pdh, c_pgfile)
                        pdh_pid = self._read_pdh(pdh, c_pid_chk)
                        priv_ws_bytes = self._read_pdh(pdh, c_priv_ws)
                        if priv_ws_bytes is not None and (pdh_pid is None or int(round(pdh_pid)) == self.pid):
                            cpu_priv_ws_gib = round(priv_ws_bytes / (1024**3), 4)

                shareable_mmap_ws_gib = None
                reclaimable_ram_gib = None
                if ws_gib is not None and cpu_priv_ws_gib is not None:
                    shareable_mmap_ws_gib = round(max(0.0, ws_gib - cpu_priv_ws_gib), 4)
                    reclaimable_ram_gib = round(avail_gib + shareable_mmap_ws_gib, 4)

                if tick % 4 == 0:
                    total_vram, _apps = query_nvidia_smi()
                    if total_vram >= 0:
                        last_gpu_mib = total_vram

                self.samples.append(
                    {
                        "t": round(time.perf_counter() - self._t0, 2),
                        "phase": "gen" if (self._ready_t is not None) else "load",
                        "avail_phys_gib": round(avail_gib, 4),
                        "avail_phys_mib": round(avail_mib, 1),
                        "used_phys_gib": round(used_gib, 4),
                        "private_commit_gib": round(priv_commit_gib, 4) if priv_commit_gib is not None else None,
                        "working_set_gib": round(ws_gib, 4) if ws_gib is not None else None,
                        "cpu_private_ws_gib": cpu_priv_ws_gib,
                        "shareable_mmap_ws_gib": shareable_mmap_ws_gib,
                        "reclaimable_ram_gib": reclaimable_ram_gib,
                        "pswpout_delta": 0 if (pages_out or 0.0) == 0.0 else 1,
                        "pages_output_per_sec": pages_out,
                        "page_writes_per_sec": page_writes,
                        "pagefile_usage_pct": pgfile_pct,
                        "ple_rss_kb": 0,
                        "gpu_used_mib": last_gpu_mib,
                    }
                )

                if self.watchdog_min_avail_mib > 0 and avail_mib < self.watchdog_min_avail_mib:
                    self.aborted_due_to_ram_pressure = True
                    if self.on_watchdog is not None:
                        self.on_watchdog()
                    break

                tick += 1
                time.sleep(0.25)
        finally:
            if has_pdh:
                pdh.PdhCloseQuery(hq)

    def summary(self) -> dict[str, Any]:
        if not self.samples:
            return {"count": 0}
        avail = [s["avail_phys_gib"] for s in self.samples]
        priv_c = [s["private_commit_gib"] for s in self.samples if s.get("private_commit_gib") is not None]
        ws = [s["working_set_gib"] for s in self.samples if s.get("working_set_gib") is not None]
        cws = [s["cpu_private_ws_gib"] for s in self.samples if s.get("cpu_private_ws_gib") is not None]
        sh_ws = [s["shareable_mmap_ws_gib"] for s in self.samples if s.get("shareable_mmap_ws_gib") is not None]
        recl = [s["reclaimable_ram_gib"] for s in self.samples if s.get("reclaimable_ram_gib") is not None]
        pg = [s["pages_output_per_sec"] for s in self.samples if s.get("pages_output_per_sec") is not None]
        pg_gen = [
            s["pages_output_per_sec"]
            for s in self.samples
            if s.get("phase") == "gen" and s.get("pages_output_per_sec") is not None
        ]
        pgw = [s["page_writes_per_sec"] for s in self.samples if s.get("page_writes_per_sec") is not None]
        pgw_gen = [
            s["page_writes_per_sec"]
            for s in self.samples
            if s.get("phase") == "gen" and s.get("page_writes_per_sec") is not None
        ]
        recl_gen = [
            s["reclaimable_ram_gib"]
            for s in self.samples
            if s.get("phase") == "gen" and s.get("reclaimable_ram_gib") is not None
        ]
        recl_sorted = sorted(recl)
        pgf = [s["pagefile_usage_pct"] for s in self.samples if s.get("pagefile_usage_pct") is not None]
        vram = [s["gpu_used_mib"] for s in self.samples if s.get("gpu_used_mib", -1) >= 0]
        pswp_deltas = [int(s.get("pswpout_delta", 0)) for s in self.samples]
        ple_rss = [int(s.get("ple_rss_kb", 0)) for s in self.samples]

        min_avail = min(avail)
        max_pswp_delta = max(pswp_deltas) if pswp_deltas else 0
        max_vram = max(vram) if vram else 0
        max_ple_rss = max(ple_rss) if ple_rss else 0
        max_pg_out = max(pg) if pg else 0.0

        sla_passed = (
            not self.aborted_due_to_ram_pressure
            and min_avail >= SLA_MIN_MEM_AVAIL_GIB
            and max_pswp_delta <= SLA_MAX_PSWPOUT_DELTA
            and max_pg_out == 0.0
            and max_vram <= SLA_MAX_VRAM_MIB
            and max_ple_rss <= SLA_MAX_PLE_RSS_KB
        )

        return {
            "samples_count": len(self.samples),
            "aborted_due_to_ram_pressure": self.aborted_due_to_ram_pressure,
            "abort_reason": self.abort_reason,
            "sla_passed": sla_passed,
            "min_avail_phys_gib": min_avail,
            "last_avail_phys_gib": avail[-1],
            "pswpout_start": self.pswpout_start,
            "pswpout_delta_max": max_pswp_delta,
            "max_ple_rss_kb": max_ple_rss,
            "max_private_commit_gib": max(priv_c) if priv_c else None,
            "last_private_commit_gib": priv_c[-1] if priv_c else None,
            "max_working_set_gib": max(ws) if ws else None,
            "max_cpu_private_ws_gib": max(cws) if cws else None,
            "last_cpu_private_ws_gib": cws[-1] if cws else None,
            "max_shareable_mmap_ws_gib": max(sh_ws) if sh_ws else None,
            "min_reclaimable_ram_gib": min(recl) if recl else None,
            "median_reclaimable_ram_gib": round(recl_sorted[len(recl_sorted) // 2], 4) if recl_sorted else None,
            "gen_min_reclaimable_ram_gib": min(recl_gen) if recl_gen else None,
            "last_reclaimable_ram_gib": recl[-1] if recl else None,
            "pages_output_per_sec_mean": round(sum(pg) / len(pg), 4) if pg else None,
            "pages_output_per_sec_max": max(pg) if pg else None,
            "pages_output_per_sec_gen_mean": round(sum(pg_gen) / len(pg_gen), 4) if pg_gen else None,
            "pages_output_per_sec_gen_max": max(pg_gen) if pg_gen else None,
            "page_writes_per_sec_mean": round(sum(pgw) / len(pgw), 4) if pgw else None,
            "page_writes_per_sec_gen_mean": round(sum(pgw_gen) / len(pgw_gen), 4) if pgw_gen else None,
            "page_writes_per_sec_max": max(pgw) if pgw else None,
            "pagefile_usage_pct_start": pgf[0] if pgf else None,
            "pagefile_usage_pct_max": max(pgf) if pgf else None,
            "pagefile_usage_pct_delta": round(max(pgf) - pgf[0], 4) if pgf else None,
            "max_gpu_used_mib": max(vram) if vram else None,
        }


def evaluate_telemetry_against_sla(tel: dict[str, Any]) -> dict[str, Any]:
    """Validate a telemetry summary (or full telemetry_*.json) against the hard Zero-Swap SLA invariants."""
    summary = tel.get("summary") if isinstance(tel.get("summary"), dict) else tel
    post = tel.get("post_cleanup") if isinstance(tel.get("post_cleanup"), dict) else {}

    min_avail_gib = summary.get("min_avail_phys_gib")
    if min_avail_gib is None and isinstance(summary.get("min_avail_phys_mib"), (int, float)):
        min_avail_gib = float(summary["min_avail_phys_mib"]) / 1024.0
    pswp_delta = summary.get("pswpout_delta_max")
    pg_out_max = summary.get("pages_output_per_sec_max")
    vram_max = summary.get("max_gpu_used_mib")
    ple_rss_kb = summary.get("max_ple_rss_kb", 0)
    aborted = bool(summary.get("aborted_due_to_ram_pressure", False))

    avail_ok = isinstance(min_avail_gib, (int, float)) and float(min_avail_gib) >= SLA_MIN_MEM_AVAIL_GIB
    if pswp_delta is not None:
        swap_ok = int(pswp_delta) == 0 and (pg_out_max is None or float(pg_out_max) == 0.0)
    else:
        swap_ok = isinstance(pg_out_max, (int, float)) and float(pg_out_max) == 0.0
    vram_ok = isinstance(vram_max, (int, float)) and 0 <= float(vram_max) <= SLA_MAX_VRAM_MIB
    ple_ok = int(ple_rss_kb or 0) <= SLA_MAX_PLE_RSS_KB

    clean_exit_ok = True
    if post:
        post_apps = post.get("post_compute_apps") or []
        post_vram = float(post.get("post_vram_used_mib", 0.0) or 0.0)
        idle_vram = float(post.get("idle_vram_mib", 64.0) or 64.0)
        clean_exit_ok = (len(post_apps) == 0) and (post_vram <= idle_vram + 64.0)

    all_ok = avail_ok and swap_ok and vram_ok and ple_ok and clean_exit_ok and not aborted
    return {
        "mem_avail_gte_3gib": avail_ok,
        "avail_ram_3gib_ok": avail_ok,
        "zero_swap_pswpout_delta": swap_ok,
        "zero_swap_pswpout_ok": swap_ok,
        "vram_lte_10_5gib": vram_ok,
        "vram_budget_ok": vram_ok,
        "ple_rss_zero_kb": ple_ok,
        "ple_zero_rss_ok": ple_ok,
        "clean_exit_ok": clean_exit_ok,
        "all_sla_passed": all_ok,
    }


def wait_for_health(proc: subprocess.Popen[Any], timeout_sec: float = 180.0) -> tuple[bool, float]:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout_sec:
        if proc.poll() is not None:
            return False, round(time.perf_counter() - t0, 2)
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == "ok":
                        return True, round(time.perf_counter() - t0, 2)
        except Exception:
            pass
        time.sleep(0.5)
    return False, round(time.perf_counter() - t0, 2)


def post_chat(payload: dict[str, Any], timeout_sec: float = 300.0) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    elapsed = round(time.perf_counter() - t0, 2)
    choice = (raw.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    usage = raw.get("usage") or {}
    timings = raw.get("timings") or {}
    return {
        "elapsed_sec": elapsed,
        "finish_reason": choice.get("finish_reason"),
        "usage": usage,
        "prompt_per_second": timings.get("prompt_per_second"),
        "predicted_per_second": timings.get("predicted_per_second"),
        "reasoning_content": msg.get("reasoning_content") or "",
        "content": msg.get("content") or "",
    }


def make_prompt_a() -> dict[str, Any]:
    return {
        "model": "smartllm",
        "messages": [
            {
                "role": "system",
                "content": "You are a Senior AI Design Engineer. Reply strictly with clean, production-grade code.",
            },
            {
                "role": "user",
                "content": (
                    "Create a single self-contained semantic HTML5 <section> hero card with embedded CSS using "
                    "oklch() custom properties (`--bg`, `--fg`, `--accent`), editorial typography, a Russian <h1> "
                    "headline about architectural minimalism, a concise Russian subtitle, and one primary CTA button."
                ),
            },
        ],
        "temperature": 0.0,
        "max_tokens": 3072,
        "cache_prompt": False,
        "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": "medium"},
    }


def make_prompt_b(png_b64: str) -> dict[str, Any]:
    return {
        "model": "smartllm",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Опиши на русском языке в 3–4 предложениях структуру сетки, типографику "
                            "и цветовую палитру этого интерфейса."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{png_b64}"}},
                ],
            }
        ],
        "temperature": 0.0,
        "max_tokens": 1536,
        "cache_prompt": False,
        "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": "medium"},
    }


def stop_server_and_verify(proc: subprocess.Popen[Any] | None, idle_vram_mib: int = 64) -> dict[str, Any]:
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
    time.sleep(1.5)
    vram_mib, apps = query_nvidia_smi()
    return {
        "port_8080_open": is_port_open(HOST, PORT),
        "post_vram_used_mib": vram_mib,
        "post_compute_apps": apps,
        "vram_exit_clean": (len(apps) == 0) and (vram_mib <= idle_vram_mib + 64),
    }


def run_single_config(
    name: str,
    model_path: Path,
    use_nr: bool,
    run_vision: bool,
    log_path: Path,
    png_b64: str,
    watchdog_min_avail_mib: float = SLA_MIN_MEM_AVAIL_MIB,
    lazy_mode: str = "direct",
    n_cpu_moe: int = 48,
    moe_cache_mib: int = 4096,
) -> dict[str, Any]:
    pre_vram, pre_apps = query_nvidia_smi()
    if pre_vram > 256 or pre_apps or is_port_open(HOST, PORT):
        raise RuntimeError(f"Unsafe pre-state for {name}: pre_vram={pre_vram}, pre_apps={pre_apps}")
    pre_avail_gib, _pre_avail_mib, pre_used_gib, total_phys_gib = get_phys_ram()

    cmd = [
        str(SERVER_EXE),
        "-m",
        str(model_path),
        "--mmproj",
        str(MMPROJ_PATH),
        "--load-mode",
        "mmap",
        "--lazy-mode",
        lazy_mode,
        "-ngl",
        "99",
        "--n-cpu-moe",
        str(n_cpu_moe),
        *(["-nr"] if use_nr else []),
        "--moe-cache-mib",
        str(moe_cache_mib),
        "-fa",
        "on",
        "-fit",
        "off",
        "-np",
        "1",
        "-c",
        "32768",
        "-ctk",
        "q8_0",
        "-ctv",
        "q8_0",
        "--cache-ram",
        "0",
        "--ctx-checkpoints",
        "0",
        "--no-cache-prompt",
        "--reasoning-budget",
        "4000",
        "--reasoning-effort",
        "medium",
        "--host",
        HOST,
        "--port",
        str(PORT),
    ]

    result: dict[str, Any] = {
        "name": name,
        "model": model_path.name,
        "use_nr": use_nr,
        "cmd": " ".join(cmd),
        "log_path": str(log_path),
        "pre_vram_used_mib": pre_vram,
        "total_phys_gib": round(total_phys_gib, 4),
        "pre_avail_phys_gib": round(pre_avail_gib, 4),
        "pre_used_phys_gib": round(pre_used_gib, 4),
        "status": "unknown",
    }

    proc: subprocess.Popen[Any] | None = None
    recorder: TelemetryRecorder | None = None
    with open(log_path, "w", encoding="utf-8", errors="replace") as log_fh:
        try:
            proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT, text=True)

            def _abort() -> None:
                if proc is not None and proc.poll() is None:
                    proc.terminate()

            recorder = TelemetryRecorder(
                proc.pid,
                watchdog_min_avail_mib=watchdog_min_avail_mib,
                on_watchdog=_abort,
                model_path=model_path,
            )
            recorder.start()

            healthy, ready_sec = wait_for_health(proc, timeout_sec=180.0)
            result["health_ok"] = healthy
            result["ready_sec"] = ready_sec
            if not healthy:
                result["status"] = "aborted_watchdog" if recorder.aborted_due_to_ram_pressure else "health_failed"
                result["returncode"] = proc.poll()
            else:
                recorder.mark_ready()
                result["prompt_a"] = post_chat(make_prompt_a())
                if run_vision:
                    result["prompt_b_vision"] = post_chat(make_prompt_b(png_b64))
                result["status"] = "PASS"
        except Exception as exc:
            result["status"] = "aborted_watchdog" if (recorder and recorder.aborted_due_to_ram_pressure) else "error"
            result["error"] = str(exc)
        finally:
            if recorder is not None:
                recorder.stop()
                tel_sum = recorder.summary()
                tel_sum["sla_checks"] = evaluate_telemetry_against_sla(tel_sum)
                result["telemetry"] = tel_sum
                if not tel_sum["sla_checks"]["all_sla_passed"]:
                    result["status"] = "FAIL_SLA"
            result["post_cleanup"] = stop_server_and_verify(proc, idle_vram_mib=max(31, pre_vram))
            if result.get("returncode") is None and proc is not None:
                result["returncode"] = proc.returncode
    return result


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png_b64 = base64.b64encode(VISION_PNG.read_bytes()).decode("ascii")

    runs = [
        run_single_config(
            name="IQ3_S_no_repack",
            model_path=IQ3_S_PATH,
            use_nr=True,
            run_vision=True,
            log_path=OUT_DIR / "server_iq3_s_nr.log",
            png_b64=png_b64,
        ),
    ]

    def _prompts_complete(r: dict[str, Any]) -> bool:
        pa = r.get("prompt_a") or {}
        pb = r.get("prompt_b_vision") or {}
        pa_ok = pa.get("finish_reason") == "stop" and len(str(pa.get("content", "")).strip()) > 40
        pb_ok = pb.get("finish_reason") == "stop" and len(str(pb.get("content", "")).strip()) > 40
        return pa_ok and pb_ok

    def _sla_passed(r: dict[str, Any]) -> bool:
        tel = r.get("telemetry") or {}
        sla = tel.get("sla_checks") or evaluate_telemetry_against_sla(tel)
        return bool(sla.get("all_sla_passed"))

    overall_ok = all(
        r["status"] == "PASS"
        and _prompts_complete(r)
        and _sla_passed(r)
        and r["post_cleanup"].get("vram_exit_clean", False)
        and not r["post_cleanup"]["port_8080_open"]
        for r in runs
    )
    report = {
        "overall_status": "PASS" if overall_ok else "FAIL",
        "runs": runs,
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for r in runs:
        tel = r.get("telemetry") or {}
        pa = r.get("prompt_a") or {}
        print(
            f"{r['name']}: status={r['status']}, min_avail={tel.get('min_avail_phys_gib')} GiB, "
            f"pswpout_d={tel.get('pswpout_delta_max')}, ple_rss={tel.get('max_ple_rss_kb')} kB, "
            f"vram_max={tel.get('max_gpu_used_mib')} MiB, tok_s={pa.get('predicted_per_second')}, fin={pa.get('finish_reason')}",
            flush=True,
        )
    print(f"=== STEP 7.5 SMOKE TEST: {report['overall_status']} -> {OUT_JSON} ===", flush=True)
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
