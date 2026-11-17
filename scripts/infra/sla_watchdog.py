#!/usr/bin/env python3
"""1 Hz Zero-Disk-Swap & VRAM SLA Watchdog for SmartLLM v2 (OPUS_MASTER_PLAN_V2 §0.3 & §0.3a).

Single Source of Truth for swap/memory/PLE SLA enforcement across all SmartLLM v2 scripts.

Tracks at 1 Hz (or configurable --interval-sec) per Binding Addendum §0.3a:
- Non-zram physical disk swap: disk_swap_used_kb == 0 (/proc/swaps) AND
  disk_swap_write_sectors_delta == 0 (/sys/class/block/<dev>/stat field 7, 1-indexed)
- MemAvailable >= 3.0 GiB (in /proc/meminfo)
- VRAM <= 10.5 GiB (10,752 MiB via nvidia-smi)
- zram0 orig_data_size delta <= 512.0 MiB (/sys/block/zram0/mm_stat field 0)
- Watched process-tree Swap <= max_proc_swap_mib (256 MiB offline default,
  128 MiB for llama-server soak/combine) via /proc/<pid>/smaps_rollup
- Optional PLE Rss == 0 kB check (--check-ple or --check-ple-pid <pid>) via
  /proc/<pid>/smaps (any PLE / large >=8 GiB lazy GGUF file mapping Rss == 0 kB)
- Global /proc/vmstat pswpout delta is logged (baseline_pswpout, max_pswpout_delta)
  as informational telemetry (or enforced if --max-pswpout-delta >= 0).

On breach:
- Appends a single concise incident line to .system/checkpoint.md (or --checkpoint-file)
- Sends SIGTERM to target process group -> waits up to 10s -> sends SIGKILL.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKPOINT_PATH = ROOT / ".system" / "checkpoint.md"

DEFAULT_MIN_MEM_AVAIL_GIB = 3.0
DEFAULT_MAX_VRAM_GIB = 10.5
DEFAULT_MAX_PSWPOUT_DELTA = -1  # Informational per OPUS §0.3a unless >= 0
DEFAULT_MAX_ZRAM_ORIG_DELTA_MIB = 512.0
DEFAULT_MAX_PROC_SWAP_MIB = 256.0
DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB = 128.0
DEFAULT_KILL_GRACE_SEC = 10.0


@dataclass
class SwapBaseline:
    pswpout: int
    pswpin: int
    disk_swap_used_kb: int
    disk_swap_write_sectors: int
    zram_orig_bytes: int
    zram_orig_mib: float
    mem_available_gib: float


def read_vmstat_pswpin_pswpout() -> tuple[int, int]:
    pswpin = 0
    pswpout = 0
    with open("/proc/vmstat", "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("pswpin "):
                pswpin = int(line.split()[1])
            elif line.startswith("pswpout "):
                pswpout = int(line.split()[1])
    return pswpin, pswpout


def read_vmstat_pswpout() -> int:
    return read_vmstat_pswpin_pswpout()[1]


def read_meminfo_avail_gib() -> float:
    with open("/proc/meminfo", "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                kb = int(line.split()[1])
                return kb / (1024.0 * 1024.0)
    return 0.0


def read_vram_used_gib() -> float:
    try:
        p = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if p.returncode == 0 and p.stdout.strip():
            mib = float(p.stdout.strip().splitlines()[0].strip())
            return mib / 1024.0
    except Exception:
        pass
    return 0.0


def _default_block_stat_reader(dev_name: str) -> str | None:
    p = Path(f"/sys/class/block/{dev_name}/stat")
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def _default_zram_mm_stat_reader(zram_name: str = "zram0") -> str | None:
    for candidate in (
        Path(f"/sys/block/{zram_name}/mm_stat"),
        Path(f"/sys/class/block/{zram_name}/mm_stat"),
    ):
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8")
            except Exception:
                continue
    return None


def parse_proc_swaps_and_sysfs(
    proc_swaps_text: str | None = None,
    block_stat_reader: Callable[[str], str | None] | None = None,
    zram_mm_stat_reader: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    """Parse /proc/swaps, /sys/class/block/<dev>/stat (field 7 = write sectors), and zram0 mm_stat (field 0)."""
    if proc_swaps_text is None:
        try:
            proc_swaps_text = Path("/proc/swaps").read_text(encoding="utf-8")
        except Exception:
            proc_swaps_text = ""

    b_reader = block_stat_reader or _default_block_stat_reader
    z_reader = zram_mm_stat_reader or _default_zram_mm_stat_reader

    disk_swap_used_kb = 0
    disk_swap_write_sectors = 0
    zram_used_kb = 0
    non_zram_devs: list[str] = []
    zram_devs: list[str] = []

    for line in proc_swaps_text.splitlines():
        s = line.strip()
        if not s or s.startswith("Filename"):
            continue
        cols = s.split()
        if len(cols) < 4:
            continue
        filename = cols[0]
        try:
            used_kb = int(cols[3])
        except ValueError:
            used_kb = 0

        try:
            real_dev = os.path.realpath(filename)
        except Exception:
            real_dev = filename
        dev_name = os.path.basename(real_dev)

        if filename.startswith("/dev/zram") or dev_name.startswith("zram"):
            zram_used_kb += used_kb
            zram_devs.append(dev_name if dev_name.startswith("zram") else "zram0")
        else:
            disk_swap_used_kb += used_kb
            if dev_name:
                non_zram_devs.append(dev_name)
                stat_raw = b_reader(dev_name)
                if stat_raw:
                    stat_fields = stat_raw.split()
                    # Kernel block stat field 7 (1-indexed, index 6 0-indexed) = write sectors
                    if len(stat_fields) >= 7:
                        try:
                            disk_swap_write_sectors += int(stat_fields[6])
                        except ValueError:
                            pass

    if not zram_devs:
        zram_devs = ["zram0"]

    zram_orig_bytes = 0
    seen_zram: set[str] = set()
    for zdev in zram_devs:
        if zdev in seen_zram:
            continue
        seen_zram.add(zdev)
        mm_raw = z_reader(zdev)
        if mm_raw:
            mm_fields = mm_raw.split()
            if mm_fields:
                try:
                    zram_orig_bytes += int(mm_fields[0])
                except ValueError:
                    pass

    return {
        "disk_swap_used_kb": disk_swap_used_kb,
        "disk_swap_write_sectors": disk_swap_write_sectors,
        "zram_orig_bytes": zram_orig_bytes,
        "zram_orig_mib": zram_orig_bytes / (1024.0 * 1024.0),
        "zram_used_kb": zram_used_kb,
        "non_zram_devs": non_zram_devs,
    }


def capture_swap_baseline() -> SwapBaseline:
    """Capture baseline swap, zram0, and memory counters at job start."""
    pswpin, pswpout = read_vmstat_pswpin_pswpout()
    sw = parse_proc_swaps_and_sysfs()
    mem_avail = read_meminfo_avail_gib()
    return SwapBaseline(
        pswpout=pswpout,
        pswpin=pswpin,
        disk_swap_used_kb=int(sw["disk_swap_used_kb"]),
        disk_swap_write_sectors=int(sw["disk_swap_write_sectors"]),
        zram_orig_bytes=int(sw["zram_orig_bytes"]),
        zram_orig_mib=float(sw["zram_orig_mib"]),
        mem_available_gib=mem_avail,
    )


def _iter_descendant_pids(root_pid: int | None = None, pgid: int | None = None) -> list[int]:
    """Return full descendant closure of root_pid (ppid tree) union processes with pgrp == pgid."""
    if (root_pid is None or root_pid <= 0) and (pgid is None or pgid <= 0):
        return []

    children_map: dict[int, list[int]] = {}
    pgrp_matches: set[int] = set()
    all_live: set[int] = set()

    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            pid = int(entry)
            stat_path = Path(f"/proc/{pid}/stat")
            try:
                raw = stat_path.read_text(encoding="utf-8")
                rparen = raw.rfind(")")
                if rparen == -1:
                    continue
                fields = raw[rparen + 2 :].split()
                if len(fields) < 3:
                    continue
                ppid = int(fields[1])
                pgrp = int(fields[2])
                all_live.add(pid)
                children_map.setdefault(ppid, []).append(pid)
                if pgid is not None and pgid > 0 and pgrp == pgid:
                    pgrp_matches.add(pid)
            except Exception:
                continue
    except Exception:
        pass

    result_set: set[int] = set(pgrp_matches)
    queue: list[int] = []
    if root_pid is not None and root_pid > 0:
        result_set.add(root_pid)
        queue.append(root_pid)
    for p in pgrp_matches:
        queue.append(p)

    while queue:
        cur = queue.pop()
        for child in children_map.get(cur, ()):
            if child not in result_set:
                result_set.add(child)
                queue.append(child)

    return sorted(result_set)


def read_ple_smaps_telemetry(
    target_pid: int | None = None,
    pgid: int | None = None,
    check_ple: bool = True,
) -> dict[str, Any]:
    """Inspect /proc/<pid>/smaps_rollup (always) and /proc/<pid>/smaps (only when check_ple=True)."""
    rollup_rss_kb = 0
    rollup_anon_kb = 0
    rollup_file_kb = 0
    rollup_swap_kb = 0
    ple_rss_kb = 0

    pids = _iter_descendant_pids(root_pid=target_pid, pgid=pgid)
    for pid in pids:
        rollup_path = Path(f"/proc/{pid}/smaps_rollup")
        if rollup_path.exists():
            try:
                for line in rollup_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("Rss:"):
                        rollup_rss_kb += int(line.split()[1])
                    elif line.startswith("RssAnon:"):
                        rollup_anon_kb += int(line.split()[1])
                    elif line.startswith("RssFile:"):
                        rollup_file_kb += int(line.split()[1])
                    elif line.startswith("Swap:"):
                        rollup_swap_kb += int(line.split()[1])
            except Exception:
                pass

        if check_ple:
            smaps_path = Path(f"/proc/{pid}/smaps")
            if smaps_path.exists():
                try:
                    cur_name = ""
                    cur_size_kb = 0
                    cur_rss_kb = 0
                    for line in smaps_path.read_text(encoding="utf-8", errors="replace").splitlines():
                        if "-" in line.split()[0] and ":" in line:
                            if cur_name and (
                                "ple" in cur_name.lower()
                                or (cur_name.endswith(".gguf") and cur_size_kb >= 8_000_000)
                            ):
                                ple_rss_kb += cur_rss_kb
                            parts = line.split(maxsplit=5)
                            cur_name = parts[5].strip() if len(parts) >= 6 else ""
                            cur_size_kb = 0
                            cur_rss_kb = 0
                        elif line.startswith("Size:"):
                            cur_size_kb = int(line.split()[1])
                        elif line.startswith("Rss:"):
                            cur_rss_kb = int(line.split()[1])
                    if cur_name and (
                        "ple" in cur_name.lower()
                        or (cur_name.endswith(".gguf") and cur_size_kb >= 8_000_000)
                    ):
                        ple_rss_kb += cur_rss_kb
                except Exception:
                    pass

    return {
        "rss_kb": rollup_rss_kb,
        "rss_anon_kb": rollup_anon_kb,
        "rss_file_kb": rollup_file_kb,
        "swap_kb": rollup_swap_kb,
        "rollup_swap_kb": rollup_swap_kb,
        "ple_rss_kb": ple_rss_kb,
        "pids": pids,
    }


def evaluate_swap_and_mem_sla(
    baseline: SwapBaseline | int,
    root_pid: int | None = None,
    pgid: int | None = None,
    min_mem_avail_gib: float = DEFAULT_MIN_MEM_AVAIL_GIB,
    max_vram_gib: float = DEFAULT_MAX_VRAM_GIB,
    max_zram_orig_delta_mib: float = DEFAULT_MAX_ZRAM_ORIG_DELTA_MIB,
    max_proc_swap_mib: float = DEFAULT_MAX_PROC_SWAP_MIB,
    check_ple: bool = False,
    vram_gib: float | None = None,
    max_pswpout_delta: int = DEFAULT_MAX_PSWPOUT_DELTA,
    max_proc_rss_mib: float = 0.0,
    _swaps_override: dict[str, Any] | None = None,
    _mem_avail_override: float | None = None,
    _smaps_override: dict[str, Any] | None = None,
    _vmstat_override: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Evaluate OPUS §0.3a SLA invariants in one shared call."""
    if isinstance(baseline, int):
        base_pswpout = baseline
        base_write_sectors = 0
        base_zram_mib = 0.0
    else:
        base_pswpout = baseline.pswpout
        base_write_sectors = baseline.disk_swap_write_sectors
        base_zram_mib = baseline.zram_orig_mib

    pswpin, pswpout = _vmstat_override if _vmstat_override is not None else read_vmstat_pswpin_pswpout()
    pswpout_delta = max(0, pswpout - base_pswpout)

    sw = _swaps_override if _swaps_override is not None else parse_proc_swaps_and_sysfs()
    disk_swap_used_kb = int(sw["disk_swap_used_kb"])
    disk_swap_write_sectors = int(sw["disk_swap_write_sectors"])
    disk_swap_write_sectors_delta = max(0, disk_swap_write_sectors - base_write_sectors)
    zram_orig_mib = float(sw["zram_orig_mib"])
    zram_orig_delta_mib = max(0.0, zram_orig_mib - base_zram_mib) if not isinstance(baseline, int) else 0.0

    mem_avail_gib = _mem_avail_override if _mem_avail_override is not None else read_meminfo_avail_gib()
    eff_vram_gib = vram_gib if vram_gib is not None else 0.0

    if _smaps_override is not None:
        smaps_info = _smaps_override
    elif (root_pid is not None and root_pid > 0) or (pgid is not None and pgid > 0):
        smaps_info = read_ple_smaps_telemetry(target_pid=root_pid, pgid=pgid, check_ple=check_ple)
    else:
        rpid = os.getpid()
        smaps_info = read_ple_smaps_telemetry(target_pid=rpid, pgid=None, check_ple=check_ple)

    proc_swap_kb = int(smaps_info.get("rollup_swap_kb", smaps_info.get("swap_kb", 0)))
    proc_rss_kb = int(smaps_info.get("rss_kb", 0))
    ple_rss_kb = int(smaps_info.get("ple_rss_kb", 0))
    max_proc_swap_kb_limit = max_proc_swap_mib * 1024.0

    breach_reason: str | None = None
    if disk_swap_used_kb > 0:
        breach_reason = f"disk_swap_used_kb={disk_swap_used_kb} > 0 kB"
    elif disk_swap_write_sectors_delta > 0:
        breach_reason = f"disk_swap_write_sectors_delta={disk_swap_write_sectors_delta} > 0"
    elif mem_avail_gib < min_mem_avail_gib:
        breach_reason = f"MemAvailable={mem_avail_gib:.3f} GiB < {min_mem_avail_gib:.3f} GiB"
    elif vram_gib is not None and eff_vram_gib > max_vram_gib:
        breach_reason = f"VRAM={eff_vram_gib:.3f} GiB > {max_vram_gib:.3f} GiB"
    elif check_ple and ple_rss_kb > 0:
        breach_reason = f"PLE_Rss={ple_rss_kb} kB > 0 kB"
    elif zram_orig_delta_mib > max_zram_orig_delta_mib:
        breach_reason = (
            f"zram_orig_delta_mib={zram_orig_delta_mib:.2f} MiB > {max_zram_orig_delta_mib:.1f} MiB"
        )
    elif proc_swap_kb > max_proc_swap_kb_limit:
        breach_reason = (
            f"proc_swap_kb={proc_swap_kb} kB ({proc_swap_kb / 1024.0:.2f} MiB) > "
            f"{max_proc_swap_mib:.1f} MiB"
        )
    elif max_pswpout_delta >= 0 and pswpout_delta > max_pswpout_delta:
        breach_reason = f"delta_pswpout={pswpout_delta} > {max_pswpout_delta}"
    elif max_proc_rss_mib > 0 and (proc_rss_kb / 1024.0) > max_proc_rss_mib:
        breach_reason = f"proc_Rss={proc_rss_kb / 1024.0:.1f} MiB > {max_proc_rss_mib:.1f} MiB"

    return {
        "passed": breach_reason is None,
        "breach_reason": breach_reason,
        "baseline_pswpout": base_pswpout,
        "pswpout": pswpout,
        "pswpin": pswpin,
        "pswpout_delta": pswpout_delta,
        "disk_swap_used_kb": disk_swap_used_kb,
        "disk_swap_write_sectors": disk_swap_write_sectors,
        "disk_swap_write_sectors_delta": disk_swap_write_sectors_delta,
        "zram_orig_mib": round(zram_orig_mib, 3),
        "zram_orig_delta_mib": round(zram_orig_delta_mib, 3),
        "proc_swap_kb": proc_swap_kb,
        "proc_rss_kb": proc_rss_kb,
        "ple_rss_kb": ple_rss_kb,
        "mem_available_gib": round(mem_avail_gib, 3),
        "vram_gib": round(eff_vram_gib, 3),
    }


def append_checkpoint_incident(checkpoint_path: Path, reason: str, cmd_str: str) -> None:
    try:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        line = f"- **[SLA-BREACH {ts}]** `{reason}` on `{cmd_str[:120]}` (SIGTERM->SIGKILL)\n"
        with checkpoint_path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
    except Exception as exc:
        print(f"[sla_watchdog] Failed to append incident to {checkpoint_path}: {exc}", file=sys.stderr)


def terminate_process_group(pgid: int, grace_sec: float = DEFAULT_KILL_GRACE_SEC) -> None:
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        pass

    deadline = time.monotonic() + grace_sec
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)

    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="1 Hz SLA Watchdog (OPUS §0.3a: 0 physical disk swap, MemAvailable >= 3.0 GiB, VRAM <= 10.5 GiB, PLE Rss == 0 kB)."
    )
    parser.add_argument("--interval-sec", type=float, default=1.0, help="Sampling period in seconds (default: 1.0)")
    parser.add_argument("--min-mem-avail-gib", type=float, default=DEFAULT_MIN_MEM_AVAIL_GIB)
    parser.add_argument("--max-vram-gib", type=float, default=DEFAULT_MAX_VRAM_GIB)
    parser.add_argument(
        "--max-pswpout-delta",
        type=int,
        default=DEFAULT_MAX_PSWPOUT_DELTA,
        help="Optional pswpout delta cap (-1 = informational only per OPUS §0.3a)",
    )
    parser.add_argument(
        "--max-zram-orig-delta-mib",
        type=float,
        default=DEFAULT_MAX_ZRAM_ORIG_DELTA_MIB,
        help="Max allowed zram0 orig_data_size increase in MiB (default: 512.0)",
    )
    parser.add_argument(
        "--max-proc-swap-mib",
        type=float,
        default=DEFAULT_MAX_PROC_SWAP_MIB,
        help="Max allowed process-tree Swap in MiB (256.0 offline default, 128.0 for runtime/soak/combine)",
    )
    parser.add_argument(
        "--max-proc-rss-mib",
        type=float,
        default=0.0,
        help="Optional per-process RSS cap in MiB (useful for safe synthetic watchdog tests without risking host OOM)",
    )
    parser.add_argument("--check-ple", action="store_true", help="Enforce PLE Rss == 0 kB on child process")
    parser.add_argument("--check-ple-pid", type=int, default=0, help="Explicit PID to check PLE Rss == 0 kB")
    parser.add_argument("--kill-grace-sec", type=float, default=DEFAULT_KILL_GRACE_SEC)
    parser.add_argument("--checkpoint-file", type=Path, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--no-checkpoint-log", action="store_true", help="Do not write to checkpoint.md (for unit tests)")
    parser.add_argument("--telemetry-out", type=Path, help="Optional JSON summary output path")
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to execute (after '--')")

    args = parser.parse_args(argv)
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        parser.error("No command specified to run under sla_watchdog.py")

    baseline = capture_swap_baseline()
    start_vram_gib = read_vram_used_gib()
    t0 = time.monotonic()

    child_env = os.environ.copy()
    child_env.setdefault("CUDA_PATH", "/opt/cuda")
    if Path("/opt/cuda/lib64").is_dir():
        cur_ld = child_env.get("LD_LIBRARY_PATH", "")
        if "/opt/cuda/lib64" not in cur_ld.split(":"):
            child_env["LD_LIBRARY_PATH"] = f"/opt/cuda/lib64:{cur_ld}" if cur_ld else "/opt/cuda/lib64"

    proc = subprocess.Popen(cmd, start_new_session=True, env=child_env)
    pgid = proc.pid

    min_mem_avail_seen = baseline.mem_available_gib
    max_vram_seen = start_vram_gib
    max_pswpout_delta_seen = 0
    max_disk_swap_used_kb_seen = baseline.disk_swap_used_kb
    max_disk_swap_write_sectors_delta_seen = 0
    max_zram_orig_delta_mib_seen = 0.0
    max_proc_swap_kb_seen = 0
    max_ple_rss_kb_seen = 0
    max_proc_rss_kb_seen = 0
    breach_reason: str | None = None
    samples = 0

    try:
        while True:
            rc = proc.poll()
            vram_gib = read_vram_used_gib()
            ple_pid = args.check_ple_pid if args.check_ple_pid > 0 else proc.pid
            need_ple = bool(args.check_ple or args.check_ple_pid > 0)

            eval_res = evaluate_swap_and_mem_sla(
                baseline=baseline,
                root_pid=ple_pid,
                pgid=pgid,
                min_mem_avail_gib=args.min_mem_avail_gib,
                max_vram_gib=args.max_vram_gib,
                max_zram_orig_delta_mib=args.max_zram_orig_delta_mib,
                max_proc_swap_mib=args.max_proc_swap_mib,
                check_ple=need_ple,
                vram_gib=vram_gib,
                max_pswpout_delta=args.max_pswpout_delta,
                max_proc_rss_mib=args.max_proc_rss_mib,
            )

            min_mem_avail_seen = min(min_mem_avail_seen, eval_res["mem_available_gib"])
            max_vram_seen = max(max_vram_seen, vram_gib)
            max_pswpout_delta_seen = max(max_pswpout_delta_seen, eval_res["pswpout_delta"])
            max_disk_swap_used_kb_seen = max(max_disk_swap_used_kb_seen, eval_res["disk_swap_used_kb"])
            max_disk_swap_write_sectors_delta_seen = max(
                max_disk_swap_write_sectors_delta_seen, eval_res["disk_swap_write_sectors_delta"]
            )
            max_zram_orig_delta_mib_seen = max(
                max_zram_orig_delta_mib_seen, eval_res["zram_orig_delta_mib"]
            )
            max_proc_swap_kb_seen = max(max_proc_swap_kb_seen, eval_res["proc_swap_kb"])
            max_ple_rss_kb_seen = max(max_ple_rss_kb_seen, eval_res["ple_rss_kb"])
            max_proc_rss_kb_seen = max(max_proc_rss_kb_seen, eval_res["proc_rss_kb"])
            samples += 1

            if not eval_res["passed"]:
                breach_reason = eval_res["breach_reason"]
                print(f"[sla_watchdog] BREACH DETECTED: {breach_reason}", file=sys.stderr, flush=True)
                if not args.no_checkpoint_log:
                    append_checkpoint_incident(args.checkpoint_file, str(breach_reason), " ".join(cmd))
                terminate_process_group(pgid, grace_sec=args.kill_grace_sec)
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
                break

            if rc is not None:
                break

            time.sleep(args.interval_sec)
    except KeyboardInterrupt:
        terminate_process_group(pgid, grace_sec=2.0)
        raise

    elapsed_sec = round(time.monotonic() - t0, 3)
    final_rc = proc.returncode if breach_reason is None else 137
    summary = {
        "sla_passed": breach_reason is None and final_rc == 0,
        "breach_reason": breach_reason,
        "exit_code": final_rc,
        "elapsed_sec": elapsed_sec,
        "samples": samples,
        "baseline_pswpout": baseline.pswpout,
        "max_pswpout_delta": max_pswpout_delta_seen,
        "disk_swap_used_kb": max_disk_swap_used_kb_seen,
        "max_disk_swap_write_sectors_delta": max_disk_swap_write_sectors_delta_seen,
        "max_zram_orig_delta_mib": round(max_zram_orig_delta_mib_seen, 3),
        "max_proc_swap_kb": max_proc_swap_kb_seen,
        "min_mem_avail_gib": round(min_mem_avail_seen, 3),
        "max_vram_gib": round(max_vram_seen, 3),
        "max_ple_rss_kb": max_ple_rss_kb_seen,
        "max_proc_rss_kb": max_proc_rss_kb_seen,
        "command": cmd,
    }
    if args.telemetry_out:
        args.telemetry_out.parent.mkdir(parents=True, exist_ok=True)
        args.telemetry_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[sla_watchdog] summary={json.dumps(summary)}", file=sys.stderr, flush=True)
    return 0 if (breach_reason is None and final_rc == 0) else (final_rc or 1)


if __name__ == "__main__":
    sys.exit(main())
