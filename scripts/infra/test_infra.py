#!/usr/bin/env python3
"""Unit tests for WP-A2 infrastructure scripts (download_ledger, gpu_exit_check, sla_watchdog §0.3a)."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

INFRA_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(INFRA_DIR))

import download_ledger  # noqa: E402
import gpu_exit_check  # noqa: E402
import sla_watchdog  # noqa: E402


def test_download_ledger() -> dict:
    with tempfile.TemporaryDirectory(prefix="smartllm_ledger_test_") as tmp:
        ledger = Path(tmp) / "download_ledger.tsv"
        ok, details = download_ledger.check_budget("WP-A2", 400_000_000, ledger_path=ledger, raise_on_exceed=False)
        assert ok is True, f"Expected 400 MB to pass WP-A2 cap: {details}"

        ok_over, _ = download_ledger.check_budget("WP-A2", 440_000_001, ledger_path=ledger, raise_on_exceed=False)
        assert ok_over is False, "Expected >440 MB to fail WP-A2 cap"

        res1 = download_ledger.record_download(
            wp="WP-A2",
            url="https://example.org/pkg1.whl",
            num_bytes=200_000_000,
            sha256="a" * 64,
            ledger_path=ledger,
        )
        assert res1["status"] == "recorded"

        # Dedup check
        res_dup = download_ledger.record_download(
            wp="WP-A2",
            url="https://example.org/pkg1.whl",
            num_bytes=200_000_000,
            sha256="a" * 64,
            ledger_path=ledger,
        )
        assert res_dup["status"] == "duplicate_skipped"
        assert res_dup["summary"]["total_used_bytes"] == 200_000_000

        # Cap breach check
        exceeded = False
        try:
            download_ledger.record_download(
                wp="WP-A3",
                url="https://example.org/sd.tar.gz",
                num_bytes=50_000_001,
                sha256="b" * 64,
                ledger_path=ledger,
            )
        except download_ledger.LedgerBudgetExceededError:
            exceeded = True
        assert exceeded, "Expected >50 MB on WP-A3 to raise LedgerBudgetExceededError"
    return {"test_download_ledger": "PASS"}


def test_swap_parser_and_opus_03a_sla() -> dict:
    fake_swaps = (
        "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n"
        "/dev/zram0                              partition\t32566268\t1279416\t\t100\n"
        "/dev/nvme0n1p3                          partition\t33554428\t0\t\t10\n"
    )
    # Field 7 (1-indexed, index 6 0-indexed) = write sectors (0)
    fake_nvme_stat = "      58        0     4792        2        0        0        0        0        0        1        2\n"
    # Field 0 = orig_data_size bytes (1000 MiB)
    fake_zram_mm = f"{1000 * 1024 * 1024} 185585949 197660672 0 259313664 48628 18261 1489 3000\n"

    parsed = sla_watchdog.parse_proc_swaps_and_sysfs(
        proc_swaps_text=fake_swaps,
        block_stat_reader=lambda dev: fake_nvme_stat if dev == "nvme0n1p3" else None,
        zram_mm_stat_reader=lambda zdev: fake_zram_mm,
    )
    assert parsed["disk_swap_used_kb"] == 0, parsed
    assert parsed["disk_swap_write_sectors"] == 0, parsed
    assert abs(parsed["zram_orig_mib"] - 1000.0) < 1e-6, parsed

    base = sla_watchdog.SwapBaseline(
        pswpout=500000,
        pswpin=100,
        disk_swap_used_kb=0,
        disk_swap_write_sectors=0,
        zram_orig_bytes=1000 * 1024 * 1024,
        zram_orig_mib=1000.0,
        mem_available_gib=24.0,
    )
    clean_smaps = {"rollup_swap_kb": 16 * 1024, "rss_kb": 512 * 1024, "ple_rss_kb": 0}

    # 1. Benign CachyOS zram0 pswpout (+65 pages) with 0 disk swap and 23 GiB MemAvail -> PASS
    r_ok = sla_watchdog.evaluate_swap_and_mem_sla(
        baseline=base,
        check_ple=True,
        vram_gib=7.3,
        _vmstat_override=(100, 500065),
        _swaps_override=parsed,
        _mem_avail_override=23.07,
        _smaps_override=clean_smaps,
    )
    assert r_ok["passed"] is True and r_ok["pswpout_delta"] == 65, r_ok

    # 2. Non-zram disk swap write sectors > 0 -> FAIL
    r_disk_wr = sla_watchdog.evaluate_swap_and_mem_sla(
        baseline=base,
        _vmstat_override=(100, 500065),
        _swaps_override={**parsed, "disk_swap_write_sectors": 8},
        _mem_avail_override=23.07,
        _smaps_override=clean_smaps,
    )
    assert r_disk_wr["passed"] is False and "disk_swap_write_sectors_delta=8" in r_disk_wr["breach_reason"], r_disk_wr

    # 3. Non-zram disk_swap_used_kb > 0 -> FAIL
    r_disk_used = sla_watchdog.evaluate_swap_and_mem_sla(
        baseline=base,
        _vmstat_override=(100, 500065),
        _swaps_override={**parsed, "disk_swap_used_kb": 4},
        _mem_avail_override=23.07,
        _smaps_override=clean_smaps,
    )
    assert r_disk_used["passed"] is False and "disk_swap_used_kb=4" in r_disk_used["breach_reason"], r_disk_used

    # 4. zram0 orig_data_size delta > 512 MiB -> FAIL
    r_zram_over = sla_watchdog.evaluate_swap_and_mem_sla(
        baseline=base,
        _vmstat_override=(100, 500065),
        _swaps_override={**parsed, "zram_orig_mib": 1520.0},
        _mem_avail_override=23.07,
        _smaps_override=clean_smaps,
    )
    assert r_zram_over["passed"] is False and "zram_orig_delta_mib" in r_zram_over["breach_reason"], r_zram_over

    # 5. Process-tree Swap > 128 MiB in runtime mode (while <= 256 MiB in offline mode)
    smaps_150m = {"rollup_swap_kb": 150 * 1024, "rss_kb": 512 * 1024, "ple_rss_kb": 0}
    r_off_ok = sla_watchdog.evaluate_swap_and_mem_sla(
        baseline=base,
        max_proc_swap_mib=256.0,
        _swaps_override=parsed,
        _mem_avail_override=23.07,
        _smaps_override=smaps_150m,
    )
    assert r_off_ok["passed"] is True, r_off_ok
    r_rt_fail = sla_watchdog.evaluate_swap_and_mem_sla(
        baseline=base,
        max_proc_swap_mib=128.0,
        _swaps_override=parsed,
        _mem_avail_override=23.07,
        _smaps_override=smaps_150m,
    )
    assert r_rt_fail["passed"] is False and "proc_swap_kb=" in r_rt_fail["breach_reason"], r_rt_fail

    return {"test_swap_parser_and_opus_03a_sla": "PASS"}


def test_sla_watchdog_kills_synthetic_hog() -> dict:
    with tempfile.TemporaryDirectory(prefix="smartllm_wd_test_") as tmp:
        tmp_path = Path(tmp)
        ckpt_file = tmp_path / "checkpoint_test.md"
        telemetry_file = tmp_path / "wd_telemetry.json"

        cur_avail = sla_watchdog.read_meminfo_avail_gib()
        trigger_avail_gib = round(cur_avail - 0.12, 3)

        hog_code = (
            "import time\n"
            "buf = bytearray(280 * 1024 * 1024)\n"
            "for i in range(0, len(buf), 4096):\n"
            "    buf[i] = 1\n"
            "time.sleep(30)\n"
        )
        cmd = [
            sys.executable,
            str(INFRA_DIR / "sla_watchdog.py"),
            "--interval-sec",
            "0.2",
            "--min-mem-avail-gib",
            str(trigger_avail_gib),
            "--max-proc-rss-mib",
            "128",
            "--kill-grace-sec",
            "2.0",
            "--checkpoint-file",
            str(ckpt_file),
            "--telemetry-out",
            str(telemetry_file),
            "--",
            sys.executable,
            "-c",
            hog_code,
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
        assert p.returncode != 0, f"Expected watchdog to kill hog with non-zero rc, got {p.returncode}"
        assert telemetry_file.exists(), "Watchdog did not write telemetry JSON"
        telemetry = json.loads(telemetry_file.read_text(encoding="utf-8"))
        assert telemetry["sla_passed"] is False
        assert telemetry["breach_reason"] is not None
        required_keys = (
            "baseline_pswpout",
            "max_pswpout_delta",
            "disk_swap_used_kb",
            "max_disk_swap_write_sectors_delta",
            "max_zram_orig_delta_mib",
            "max_proc_swap_kb",
            "min_mem_avail_gib",
            "max_vram_gib",
            "max_ple_rss_kb",
            "max_proc_rss_kb",
        )
        for k in required_keys:
            assert k in telemetry, f"Missing required §0.3a.2 key '{k}' in {telemetry}"
        assert telemetry["disk_swap_used_kb"] == 0, f"Unexpected physical disk swap: {telemetry}"
        assert telemetry["max_disk_swap_write_sectors_delta"] == 0, f"Unexpected disk swap writes: {telemetry}"
        assert ckpt_file.exists() and "SLA-BREACH" in ckpt_file.read_text(encoding="utf-8")
        return {
            "test_sla_watchdog_hog": "PASS",
            "return_code": p.returncode,
            "breach_reason": telemetry["breach_reason"],
            "elapsed_sec": telemetry["elapsed_sec"],
            "disk_swap_used_kb": telemetry["disk_swap_used_kb"],
            "max_disk_swap_write_sectors_delta": telemetry["max_disk_swap_write_sectors_delta"],
            "max_pswpout_delta": telemetry["max_pswpout_delta"],
        }


def test_gpu_exit_check() -> dict:
    res = gpu_exit_check.check_gpu_exit()
    assert res["passed"] is True, f"gpu_exit_check failed: {res}"
    return {"test_gpu_exit_check": "PASS", "gpu_state": res}


def main() -> int:
    out = {}
    out.update(test_download_ledger())
    out.update(test_swap_parser_and_opus_03a_sla())
    out.update(test_sla_watchdog_kills_synthetic_hog())
    out.update(test_gpu_exit_check())
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
