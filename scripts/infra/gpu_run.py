#!/usr/bin/env python3
"""GPU single-owner lock & execution wrapper for SmartLLM v2 (OPUS_MASTER_PLAN_V2 §0.2 & §0.3a).

Workflow:
1. Acquires non-blocking exclusive flock on .system/gpu.lock (fails immediately if busy).
2. Appends a single structured line to .system/gpu_runs.log containing:
   timestamp, wp, hypothesis, expected_result, single_changed_factor, command.
3. Runs the target command under scripts/infra/sla_watchdog.py.
4. Always runs scripts/infra/gpu_exit_check.py on completion and logs final status.
5. Never auto-retries on failure.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCK_PATH = ROOT / ".system" / "gpu.lock"
DEFAULT_LOG_PATH = ROOT / ".system" / "gpu_runs.log"
WATCHDOG_SCRIPT = Path(__file__).resolve().parent / "sla_watchdog.py"
EXIT_CHECK_SCRIPT = Path(__file__).resolve().parent / "gpu_exit_check.py"


def _clean_field(val: str) -> str:
    return val.strip().replace("\t", " ").replace("\n", " ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a GPU command under flock(.system/gpu.lock), sla_watchdog.py, and gpu_exit_check.py."
    )
    parser.add_argument("--wp", type=str, default="UNSPECIFIED", help="Work package ID (e.g. WP-A2, WP-B1, WP-C1)")
    parser.add_argument("--hypothesis", required=True, type=str, help="Hypothesis for this GPU run")
    parser.add_argument("--expected", required=True, type=str, help="Expected metric/outcome")
    parser.add_argument("--factor", required=True, type=str, help="Single changed factor vs baseline")
    parser.add_argument("--lock-file", type=Path, default=DEFAULT_LOCK_PATH)
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--check-ple", action="store_true", help="Pass --check-ple to sla_watchdog.py")
    parser.add_argument(
        "--max-proc-swap-mib",
        type=float,
        default=256.0,
        help="Max allowed process-tree Swap in MiB forwarded to sla_watchdog.py (default: 256.0)",
    )
    parser.add_argument("--interval-sec", type=float, default=1.0, help="Watchdog sampling interval (s)")
    parser.add_argument("--idle-mib", type=float, default=31.0, help="Idle VRAM baseline for exit check (MiB)")
    parser.add_argument("--margin-mib", type=float, default=64.0, help="Allowed VRAM margin above idle (MiB)")
    parser.add_argument("--telemetry-out", type=Path, help="Optional JSON path for watchdog telemetry")
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run (after '--')")

    args = parser.parse_args(argv)
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        parser.error("No command specified after '--'")

    args.lock_file.parent.mkdir(parents=True, exist_ok=True)
    args.log_file.parent.mkdir(parents=True, exist_ok=True)

    lock_f = args.lock_file.open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(
            json.dumps(
                {
                    "error": "GPU_LOCK_BUSY",
                    "message": f"Another GPU process holds {args.lock_file}. Aborting without retry.",
                }
            ),
            file=sys.stderr,
        )
        lock_f.close()
        return 3

    try:
        ts_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cmd_str = " ".join(cmd)
        log_line = (
            f"{ts_start}\twp={_clean_field(args.wp)}\t"
            f"hypothesis={_clean_field(args.hypothesis)}\t"
            f"expected={_clean_field(args.expected)}\t"
            f"single_factor={_clean_field(args.factor)}\t"
            f"cmd={_clean_field(cmd_str)}\n"
        )
        with args.log_file.open("a", encoding="utf-8") as lf:
            lf.write(log_line)
            lf.flush()

        watchdog_cmd = [
            sys.executable,
            str(WATCHDOG_SCRIPT),
            "--interval-sec",
            str(args.interval_sec),
            "--max-proc-swap-mib",
            str(args.max_proc_swap_mib),
        ]
        if args.check_ple:
            watchdog_cmd.append("--check-ple")
        if args.telemetry_out:
            watchdog_cmd.extend(["--telemetry-out", str(args.telemetry_out)])
        watchdog_cmd.append("--")
        watchdog_cmd.extend(cmd)

        proc_wd = subprocess.run(watchdog_cmd, check=False)

        exit_check_cmd = [
            sys.executable,
            str(EXIT_CHECK_SCRIPT),
            "--idle-mib",
            str(args.idle_mib),
            "--margin-mib",
            str(args.margin_mib),
        ]
        proc_exit = subprocess.run(exit_check_cmd, capture_output=True, text=True, check=False)
        if proc_exit.stdout:
            print(proc_exit.stdout.strip(), file=sys.stderr, flush=True)

        if proc_wd.returncode != 0:
            return proc_wd.returncode
        if proc_exit.returncode != 0:
            print("[gpu_run] ERROR: gpu_exit_check failed after command exit!", file=sys.stderr)
            return 4
        return 0
    finally:
        try:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
        finally:
            lock_f.close()


if __name__ == "__main__":
    sys.exit(main())
