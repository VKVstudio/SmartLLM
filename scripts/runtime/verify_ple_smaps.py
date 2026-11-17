#!/usr/bin/env python3
"""Verify 0 B PLE RSS and VMA fragmentation in /proc/<pid>/smaps & smaps_rollup.

Provides two independent proofs for WP-B1 and W1/W3 Skeptic Gates:
1. Exact GGUF file-offset overlap check: parses the GGUF v3 header (< 12 MiB read,
   no mmap) to locate `per_layer_token_embd.weight` [ple_start, ple_end) and checks
   every VMA in `/proc/<pid>/smaps` mapped from that GGUF for any byte-range overlap
   and RSS contribution.
2. Watchdog heuristic parity check: matches `scripts/infra/sla_watchdog.py`
   (`.gguf` VMA with `Size >= 8_000_000 kB` or `"ple"` in VMA path).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import struct
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.infra.sla_watchdog import (  # noqa: E402
    DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
    SwapBaseline,
    capture_swap_baseline,
    evaluate_swap_and_mem_sla,
    parse_proc_swaps_and_sysfs,
    read_meminfo_avail_gib,
    read_vmstat_pswpout,
)

# GGML block size & type size table (bytes per block, elements per block)
GGML_TYPE_TRAITS: dict[int, tuple[int, int]] = {
    0: (4, 1),      # F32
    1: (2, 1),      # F16
    2: (18, 32),    # Q4_0
    3: (20, 32),    # Q4_1
    6: (22, 32),    # Q5_0
    7: (24, 32),    # Q5_1
    8: (34, 32),    # Q8_0
    9: (36, 32),    # Q8_1
    10: (84, 256),  # Q2_K
    11: (110, 256), # Q3_K
    12: (144, 256), # Q4_K
    13: (176, 256), # Q5_K
    14: (210, 256), # Q6_K
    15: (292, 256), # Q8_K
    16: (66, 256),  # IQ2_XXS
    17: (74, 256),  # IQ2_XS
    18: (98, 256),  # IQ3_XXS
    19: (50, 256),  # IQ1_S
    20: (18, 32),   # IQ4_NL
    21: (110, 256), # IQ3_S
    22: (82, 256),  # IQ2_S
    23: (136, 256), # IQ4_XS
    24: (1, 1),     # I8
    25: (2, 1),     # I16
    26: (4, 1),     # I32
    27: (8, 1),     # I64
    28: (8, 1),     # F64
    29: (56, 256),  # IQ1_M
    30: (2, 1),     # BF16
    40: (18, 64),   # Q2_0
    42: (18, 64),   # Q2_0 (b11960 ggml.h)
}


def _skip_gguf_val(f: Any, vtype: int) -> Any:
    scalar_sizes = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
    if vtype == 8:
        n = struct.unpack("<Q", f.read(8))[0]
        return f.read(n).decode("utf-8", errors="replace")
    if vtype == 9:
        atype, alen = struct.unpack("<IQ", f.read(12))
        if atype in scalar_sizes:
            f.seek(alen * scalar_sizes[atype], os.SEEK_CUR)
        else:
            for _ in range(alen):
                _skip_gguf_val(f, atype)
        return None
    if vtype == 4:
        return struct.unpack("<I", f.read(4))[0]
    if vtype == 10:
        return struct.unpack("<Q", f.read(8))[0]
    f.seek(scalar_sizes[vtype], os.SEEK_CUR)
    return None


def read_gguf_ple_range(gguf_path: Path, tensor_name: str = "per_layer_token_embd.weight") -> dict[str, Any]:
    """Read only the GGUF header (< 12 MiB) to find exact file byte range of PLE."""
    with gguf_path.open("rb") as f:
        magic = f.read(4)
        if magic != b"GGUF":
            raise ValueError(f"Not a GGUF file: {gguf_path}")
        version, n_tensors, n_kv = struct.unpack("<IQQ", f.read(20))
        alignment = 32
        for _ in range(n_kv):
            klen = struct.unpack("<Q", f.read(8))[0]
            key = f.read(klen).decode("utf-8", errors="replace")
            vtype = struct.unpack("<I", f.read(4))[0]
            val = _skip_gguf_val(f, vtype)
            if key == "general.alignment" and isinstance(val, int) and val > 0:
                alignment = val

        ple_entry: dict[str, Any] | None = None
        for _ in range(n_tensors):
            nlen = struct.unpack("<Q", f.read(8))[0]
            name = f.read(nlen).decode("utf-8", errors="replace")
            n_dims = struct.unpack("<I", f.read(4))[0]
            dims = [struct.unpack("<Q", f.read(8))[0] for _ in range(n_dims)]
            ttype, rel_offs = struct.unpack("<IQ", f.read(12))
            if name == tensor_name:
                ple_entry = {
                    "name": name,
                    "dims": dims,
                    "ggml_type": ttype,
                    "rel_offs": rel_offs,
                }

        header_end = f.tell()
        data_offset = ((header_end + alignment - 1) // alignment) * alignment

    if ple_entry is None:
        return {"found": False, "version": version, "data_offset": data_offset}

    ttype = ple_entry["ggml_type"]
    if ttype not in GGML_TYPE_TRAITS:
        raise ValueError(f"Unsupported ggml_type={ttype} for {tensor_name}")
    type_size, blck_size = GGML_TYPE_TRAITS[ttype]
    dims = ple_entry["dims"]
    row_elems = dims[0]
    n_rows = 1
    for d in dims[1:]:
        n_rows *= d
    row_bytes = (row_elems // blck_size) * type_size
    nbytes = row_bytes * n_rows
    file_start = data_offset + ple_entry["rel_offs"]
    file_end = file_start + nbytes
    return {
        "found": True,
        "name": tensor_name,
        "dims": dims,
        "ggml_type": ttype,
        "row_bytes": row_bytes,
        "nbytes": nbytes,
        "file_start": file_start,
        "file_end": file_end,
    }


def parse_smaps_text(
    smaps_text: str,
    gguf_realpath: str | None = None,
    ple_range: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse `/proc/<pid>/smaps` text and compute exact PLE overlap & GGUF VMA stats."""
    vmas: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None

    for raw_line in smaps_text.splitlines():
        if not raw_line:
            continue
        first_ch = raw_line[0]
        if first_ch in "0123456789abcdef":
            if cur is not None:
                vmas.append(cur)
            parts = raw_line.split(None, 5)
            addr_part = parts[0]
            perms = parts[1] if len(parts) > 1 else ""
            file_offs_hex = parts[2] if len(parts) > 2 else "0"
            pathname = parts[5].strip() if len(parts) > 5 else ""
            a_start_s, a_end_s = addr_part.split("-", 1)
            vma_bytes = int(a_end_s, 16) - int(a_start_s, 16)
            file_offs = int(file_offs_hex, 16)
            cur = {
                "perms": perms,
                "file_start": file_offs,
                "file_end": file_offs + vma_bytes,
                "vma_bytes": vma_bytes,
                "pathname": pathname,
                "metrics_kb": {},
            }
        elif cur is not None and ":" in raw_line:
            k, rest = raw_line.split(":", 1)
            toks = rest.split()
            if toks and toks[0].isdigit():
                cur["metrics_kb"][k.strip()] = int(toks[0])

    if cur is not None:
        vmas.append(cur)

    gguf_vmas_count = 0
    gguf_total_mapped_kb = 0
    gguf_total_rss_kb = 0
    max_gguf_vma_size_kb = 0
    watchdog_ple_rss_kb = 0
    ple_overlap_vmas = 0
    ple_overlap_mapped_bytes = 0
    ple_overlap_rss_kb = 0
    ple_boundary_shared_bytes = 0
    total_swap_kb = 0

    page_size = 4096
    ple_start = ple_range["file_start"] if (ple_range and ple_range.get("found")) else None
    ple_end = ple_range["file_end"] if (ple_range and ple_range.get("found")) else None
    # GGUF v3 aligns tensors to 32 B, while Linux munmap operates on 4096 B hardware pages.
    # Dedicated PLE pages are [ceil_4k(ple_start), floor_4k(ple_end)); up to 2 boundary pages
    # (< 8192 B total) may share bytes with adjacent non-PLE tensors.
    ple_page_start = ((ple_start + page_size - 1) // page_size) * page_size if ple_start is not None else None
    ple_page_end = (ple_end // page_size) * page_size if ple_end is not None else None

    for v in vmas:
        m = v["metrics_kb"]
        size_kb = m.get("Size", v["vma_bytes"] // 1024)
        rss_kb = m.get("Rss", 0)
        swap_kb = m.get("Swap", 0)
        total_swap_kb += swap_kb
        path_str = v["pathname"]
        path_low = path_str.lower()

        is_gguf = ".gguf" in path_low
        if gguf_realpath and path_str:
            try:
                if os.path.realpath(path_str) == gguf_realpath:
                    is_gguf = True
            except OSError:
                pass

        if is_gguf:
            gguf_vmas_count += 1
            gguf_total_mapped_kb += size_kb
            gguf_total_rss_kb += rss_kb
            if size_kb > max_gguf_vma_size_kb:
                max_gguf_vma_size_kb = size_kb
            if size_kb >= 8_000_000 or "ple" in path_low:
                watchdog_ple_rss_kb += rss_kb

            if ple_page_start is not None and ple_page_end is not None and ple_page_end > ple_page_start:
                ov_lo = max(v["file_start"], ple_page_start)
                ov_hi = min(v["file_end"], ple_page_end)
                if ov_hi > ov_lo:
                    ple_overlap_vmas += 1
                    ple_overlap_mapped_bytes += ov_hi - ov_lo
                    ple_overlap_rss_kb += rss_kb
            if ple_start is not None and ple_end is not None:
                raw_lo = max(v["file_start"], ple_start)
                raw_hi = min(v["file_end"], ple_end)
                if raw_hi > raw_lo:
                    ple_boundary_shared_bytes += (raw_hi - raw_lo) - max(
                        0,
                        min(v["file_end"], ple_page_end or 0) - max(v["file_start"], ple_page_start or 0),
                    )

    return {
        "total_vmas": len(vmas),
        "gguf_vmas_count": gguf_vmas_count,
        "gguf_total_mapped_kb": gguf_total_mapped_kb,
        "gguf_total_rss_kb": gguf_total_rss_kb,
        "max_gguf_vma_size_kb": max_gguf_vma_size_kb,
        "watchdog_ple_rss_kb": watchdog_ple_rss_kb,
        "ple_overlap_vmas": ple_overlap_vmas,
        "ple_overlap_mapped_bytes": ple_overlap_mapped_bytes,
        "ple_overlap_rss_kb": ple_overlap_rss_kb,
        "ple_boundary_shared_bytes": ple_boundary_shared_bytes,
        "total_swap_kb": total_swap_kb,
    }


def read_smaps_rollup(pid: int) -> dict[str, int]:
    out: dict[str, int] = {}
    p = Path(f"/proc/{pid}/smaps_rollup")
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        k, rest = line.split(":", 1)
        toks = rest.split()
        if toks and toks[0].isdigit():
            out[k.strip()] = int(toks[0])
    return out


def read_host_mem_swap() -> dict[str, Any]:
    sw = parse_proc_swaps_and_sysfs()
    return {
        "mem_available_gib": round(read_meminfo_avail_gib(), 3),
        "pswpout": read_vmstat_pswpout(),
        "disk_swap_used_kb": sw["disk_swap_used_kb"],
        "disk_swap_write_sectors": sw["disk_swap_write_sectors"],
        "zram_orig_mib": round(sw["zram_orig_mib"], 3),
    }


def run_self_test() -> int:
    fake_ple = {"found": True, "file_start": 527682560, "file_end": 29327820800}
    # Case 1: unmapped PLE (only MoE fragments after 29,327,820,800) -> PASS
    smaps_clean = (
        "7f0000000000-7f000b880000 r--s 6d41c5000 08:02 123 /models/SmartLLM.gguf\n"
        "Size:             188928 kB\n"
        "Rss:              188928 kB\n"
        "Swap:                  0 kB\n"
    )
    r_clean = parse_smaps_text(smaps_clean, ple_range=fake_ple)
    assert r_clean["ple_overlap_vmas"] == 0, r_clean
    assert r_clean["ple_overlap_rss_kb"] == 0, r_clean
    assert r_clean["watchdog_ple_rss_kb"] == 0, r_clean
    assert r_clean["max_gguf_vma_size_kb"] == 188928, r_clean

    # Case 2: mapped PLE -> detected immediately
    smaps_dirty = (
        "7f0000000000-7f06d41c5000 r--s 01f739000 08:02 123 /models/SmartLLM.gguf\n"
        "Size:           28125136 kB\n"
        "Rss:                4096 kB\n"
        "Swap:                  0 kB\n"
    )
    r_dirty = parse_smaps_text(smaps_dirty, ple_range=fake_ple)
    assert r_dirty["ple_overlap_vmas"] == 1, r_dirty
    assert r_dirty["ple_overlap_rss_kb"] == 4096, r_dirty
    assert r_dirty["watchdog_ple_rss_kb"] == 4096, r_dirty

    # Case 3: shared §0.3a swap SLA check (128 MiB runtime cap)
    base = capture_swap_baseline()
    sla_ok = evaluate_swap_and_mem_sla(
        baseline=base,
        max_proc_swap_mib=DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
        check_ple=True,
        _smaps_override={"rollup_swap_kb": 1024, "rss_kb": 188928, "ple_rss_kb": 0},
    )
    assert sla_ok["passed"] is True, sla_ok
    sla_fail = evaluate_swap_and_mem_sla(
        baseline=base,
        max_proc_swap_mib=DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
        check_ple=True,
        _smaps_override={"rollup_swap_kb": 140 * 1024, "rss_kb": 188928, "ple_rss_kb": 0},
    )
    assert sla_fail["passed"] is False, sla_fail
    print(json.dumps({"self_test": "PASSED"}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify 0 B PLE RSS in /proc/<pid>/smaps")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--pid", type=int, help="Target runtime process PID")
    ap.add_argument("--gguf", type=Path, help="Optional GGUF path for exact PLE byte-range overlap check")
    ap.add_argument("--out", type=Path, help="Optional JSON output path")
    args = ap.parse_args()

    if args.self_test:
        return run_self_test()

    if not args.pid:
        ap.error("--pid is required unless --self-test is passed")

    ple_range = read_gguf_ple_range(args.gguf) if args.gguf else None
    gguf_real = os.path.realpath(args.gguf) if args.gguf else None

    smaps_path = Path(f"/proc/{args.pid}/smaps")
    if not smaps_path.exists():
        print(json.dumps({"passed": False, "error": f"/proc/{args.pid}/smaps not found"}))
        return 1

    baseline = capture_swap_baseline()
    smaps_stats = parse_smaps_text(
        smaps_path.read_text(encoding="utf-8", errors="replace"),
        gguf_realpath=gguf_real,
        ple_range=ple_range,
    )
    rollup = read_smaps_rollup(args.pid)
    host = read_host_mem_swap()
    sla_eval = evaluate_swap_and_mem_sla(
        baseline=baseline,
        root_pid=args.pid,
        max_proc_swap_mib=DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
        check_ple=True,
    )

    passed = (
        smaps_stats["ple_overlap_rss_kb"] == 0
        and smaps_stats["ple_overlap_mapped_bytes"] == 0
        and smaps_stats["watchdog_ple_rss_kb"] == 0
        and sla_eval["passed"]
    )

    report = {
        "passed": passed,
        "pid": args.pid,
        "ple_range": ple_range,
        "smaps": smaps_stats,
        "smaps_rollup_kb": rollup,
        "host": host,
        "sla_eval": sla_eval,
    }
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
