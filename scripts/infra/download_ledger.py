#!/usr/bin/env python3
"""Atomic file-locked download budget ledger for SmartLLM v2.

Enforces OPUS_MASTER_PLAN_V2 §0.1 hard cumulative download caps:
- Total overnight cap: <= 950,000,000 B (950 MB decimal)
- Per-WP caps:
  - WP-A2: <= 440,000,000 B (440 MB)
  - WP-C2: <= 380,000,000 B (380 MB)
  - WP-B1: <=  80,000,000 B ( 80 MB)
  - WP-A3: <=  50,000,000 B ( 50 MB)

Ledger format (.system/download_ledger.tsv):
bytes\turl\twp\tsha256\ttimestamp
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER_PATH = ROOT / ".system" / "download_ledger.tsv"

TOTAL_CAP_BYTES = 950_000_000
WP_CAPS_BYTES: dict[str, int] = {
    "WP-A2": 440_000_000,
    "WP-C2": 380_000_000,
    "WP-B1": 80_000_000,
    "WP-A3": 50_000_000,
}

WP_ALIASES: dict[str, str] = {
    "A2": "WP-A2",
    "WP-A2": "WP-A2",
    "WPA2": "WP-A2",
    "C2": "WP-C2",
    "WP-C2": "WP-C2",
    "WPC2": "WP-C2",
    "B1": "WP-B1",
    "WP-B1": "WP-B1",
    "WPB1": "WP-B1",
    "A3": "WP-A3",
    "WP-A3": "WP-A3",
    "WPA3": "WP-A3",
    "WP-A3-COMBINE": "WP-A3",
    "WP-A3-EVAL": "WP-A3",
}

HEADER_LINE = "bytes\turl\twp\tsha256\ttimestamp\n"


class LedgerBudgetExceededError(RuntimeError):
    """Raised when a download would exceed either the WP cap or total 950 MB cap."""


def normalize_wp(wp: str) -> str:
    key = wp.strip().upper().replace("_", "-")
    if key not in WP_ALIASES:
        raise ValueError(
            f"Unknown work package '{wp}'. Expected one of {sorted(WP_CAPS_BYTES.keys())}"
        )
    return WP_ALIASES[key]


def compute_file_sha256_and_size(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    total = 0
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            total += len(chunk)
    return h.hexdigest(), total


@contextmanager
def _locked_ledger(ledger_path: Path) -> Iterator[Path]:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if not ledger_path.exists():
        ledger_path.write_text(HEADER_LINE, encoding="utf-8")
    with ledger_path.open("r+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield ledger_path
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _read_entries_unlocked(ledger_path: Path) -> list[dict[str, Any]]:
    if not ledger_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for raw_line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("bytes\t"):
            continue
        parts = raw_line.split("\t")
        if len(parts) < 4:
            continue
        entries.append(
            {
                "bytes": int(parts[0]),
                "url": parts[1],
                "wp": normalize_wp(parts[2]),
                "sha256": parts[3],
                "timestamp": parts[4] if len(parts) > 4 else "",
            }
        )
    return entries


def _summarize_unlocked(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_wp: dict[str, int] = {wp: 0 for wp in WP_CAPS_BYTES}
    total_bytes = 0
    for e in entries:
        b = int(e["bytes"])
        wp = e["wp"]
        by_wp[wp] = by_wp.get(wp, 0) + b
        total_bytes += b
    wp_status = {}
    for wp, cap in WP_CAPS_BYTES.items():
        used = by_wp.get(wp, 0)
        wp_status[wp] = {
            "used_bytes": used,
            "cap_bytes": cap,
            "remaining_bytes": cap - used,
            "used_mb": round(used / 1_000_000, 3),
            "cap_mb": round(cap / 1_000_000, 3),
            "remaining_mb": round((cap - used) / 1_000_000, 3),
        }
    return {
        "total_used_bytes": total_bytes,
        "total_cap_bytes": TOTAL_CAP_BYTES,
        "total_remaining_bytes": TOTAL_CAP_BYTES - total_bytes,
        "total_used_mb": round(total_bytes / 1_000_000, 3),
        "total_cap_mb": round(TOTAL_CAP_BYTES / 1_000_000, 3),
        "total_remaining_mb": round((TOTAL_CAP_BYTES - total_bytes) / 1_000_000, 3),
        "entry_count": len(entries),
        "by_wp": wp_status,
    }


def get_summary(ledger_path: Path = DEFAULT_LEDGER_PATH) -> dict[str, Any]:
    with _locked_ledger(ledger_path):
        entries = _read_entries_unlocked(ledger_path)
        return _summarize_unlocked(entries)


def check_budget(
    wp: str,
    num_bytes: int,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    raise_on_exceed: bool = True,
) -> tuple[bool, dict[str, Any]]:
    norm_wp = normalize_wp(wp)
    if num_bytes < 0:
        raise ValueError(f"num_bytes must be non-negative, got {num_bytes}")
    with _locked_ledger(ledger_path):
        entries = _read_entries_unlocked(ledger_path)
        summary = _summarize_unlocked(entries)
        wp_info = summary["by_wp"][norm_wp]
        new_wp_used = wp_info["used_bytes"] + num_bytes
        new_total_used = summary["total_used_bytes"] + num_bytes
        ok_wp = new_wp_used <= wp_info["cap_bytes"]
        ok_total = new_total_used <= TOTAL_CAP_BYTES
        allowed = ok_wp and ok_total
        details = {
            "allowed": allowed,
            "wp": norm_wp,
            "requested_bytes": num_bytes,
            "wp_used_bytes": wp_info["used_bytes"],
            "wp_new_bytes": new_wp_used,
            "wp_cap_bytes": wp_info["cap_bytes"],
            "wp_remaining_after_bytes": wp_info["cap_bytes"] - new_wp_used,
            "total_used_bytes": summary["total_used_bytes"],
            "total_new_bytes": new_total_used,
            "total_cap_bytes": TOTAL_CAP_BYTES,
            "total_remaining_after_bytes": TOTAL_CAP_BYTES - new_total_used,
        }
        if not allowed and raise_on_exceed:
            raise LedgerBudgetExceededError(
                f"Download budget exceeded for {norm_wp} (+{num_bytes} B): "
                f"WP {new_wp_used}/{wp_info['cap_bytes']} B, "
                f"Total {new_total_used}/{TOTAL_CAP_BYTES} B"
            )
        return allowed, details


def record_download(
    wp: str,
    url: str,
    num_bytes: int,
    sha256: str,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    dedup: bool = True,
) -> dict[str, Any]:
    norm_wp = normalize_wp(wp)
    if num_bytes < 0:
        raise ValueError(f"num_bytes must be non-negative, got {num_bytes}")
    clean_url = url.strip().replace("\t", " ").replace("\n", " ")
    clean_sha = sha256.strip() or "none"
    with _locked_ledger(ledger_path):
        entries = _read_entries_unlocked(ledger_path)
        if dedup and clean_sha != "none":
            for e in entries:
                if e["wp"] == norm_wp and e["sha256"] == clean_sha and e["url"] == clean_url:
                    summary = _summarize_unlocked(entries)
                    return {"status": "duplicate_skipped", "entry": e, "summary": summary}

        summary = _summarize_unlocked(entries)
        wp_info = summary["by_wp"][norm_wp]
        new_wp_used = wp_info["used_bytes"] + num_bytes
        new_total_used = summary["total_used_bytes"] + num_bytes
        if new_wp_used > wp_info["cap_bytes"] or new_total_used > TOTAL_CAP_BYTES:
            raise LedgerBudgetExceededError(
                f"Download budget exceeded for {norm_wp} (+{num_bytes} B from {clean_url}): "
                f"WP {new_wp_used}/{wp_info['cap_bytes']} B, "
                f"Total {new_total_used}/{TOTAL_CAP_BYTES} B"
            )

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"{num_bytes}\t{clean_url}\t{norm_wp}\t{clean_sha}\t{ts}\n"
        with ledger_path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
        entry = {
            "bytes": num_bytes,
            "url": clean_url,
            "wp": norm_wp,
            "sha256": clean_sha,
            "timestamp": ts,
        }
        entries.append(entry)
        return {"status": "recorded", "entry": entry, "summary": _summarize_unlocked(entries)}


def record_file(
    wp: str,
    file_path: Path,
    url: str | None = None,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    dedup: bool = True,
) -> dict[str, Any]:
    sha256, num_bytes = compute_file_sha256_and_size(file_path)
    effective_url = url if url else f"file://{file_path.resolve()}"
    return record_download(
        wp=wp,
        url=effective_url,
        num_bytes=num_bytes,
        sha256=sha256,
        ledger_path=ledger_path,
        dedup=dedup,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Atomic file-locked download budget ledger (.system/download_ledger.tsv)."
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=DEFAULT_LEDGER_PATH,
        help="Path to download_ledger.tsv",
    )
    parser.add_argument("--wp", type=str, help="Work package (WP-A2, WP-C2, WP-B1, WP-A3)")
    parser.add_argument("--url", type=str, help="Source URL or identifier")
    parser.add_argument("--bytes", dest="num_bytes", type=int, help="Download size in bytes")
    parser.add_argument("--sha256", type=str, default="none", help="SHA-256 hex digest")
    parser.add_argument("--file", type=Path, help="Local downloaded file to hash & size")
    parser.add_argument("--no-dedup", action="store_true", help="Disable duplicate entry skip")
    parser.add_argument("--check-only", action="store_true", help="Only check budget without recording")

    subparsers = parser.add_subparsers(dest="subcommand")

    p_status = subparsers.add_parser("status", help="Show ledger budget usage summary")
    p_status.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)

    p_check = subparsers.add_parser("check", help="Check if bytes fit within WP and total budget")
    p_check.add_argument("--wp", required=True, type=str)
    p_check.add_argument("--bytes", dest="num_bytes", required=True, type=int)
    p_check.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)

    p_rec = subparsers.add_parser("record", help="Verify budget and append download entry")
    p_rec.add_argument("--wp", required=True, type=str)
    p_rec.add_argument("--url", type=str, default="")
    p_rec.add_argument("--bytes", dest="num_bytes", type=int)
    p_rec.add_argument("--sha256", type=str, default="none")
    p_rec.add_argument("--file", type=Path, help="Compute bytes & sha256 from local file")
    p_rec.add_argument("--no-dedup", action="store_true")
    p_rec.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)

    args = parser.parse_args(argv)
    cmd = args.subcommand

    try:
        if cmd == "status" or (cmd is None and not args.wp):
            summary = get_summary(args.ledger)
            print(json.dumps(summary, indent=2))
            return 0

        if cmd == "check" or args.check_only:
            if not args.wp or args.num_bytes is None:
                parser.error("--wp and --bytes are required for budget check")
            allowed, details = check_budget(
                args.wp, args.num_bytes, ledger_path=args.ledger, raise_on_exceed=False
            )
            print(json.dumps(details, indent=2))
            return 0 if allowed else 2

        # Default or 'record'
        if not args.wp:
            parser.error("--wp is required to record a download")
        if args.file is not None:
            res = record_file(
                wp=args.wp,
                file_path=args.file,
                url=args.url or None,
                ledger_path=args.ledger,
                dedup=not args.no_dedup,
            )
        else:
            if args.num_bytes is None or not args.url:
                parser.error("Either --file or both --url and --bytes must be provided")
            res = record_download(
                wp=args.wp,
                url=args.url,
                num_bytes=args.num_bytes,
                sha256=args.sha256,
                ledger_path=args.ledger,
                dedup=not args.no_dedup,
            )
        print(json.dumps(res, indent=2))
        return 0
    except LedgerBudgetExceededError as exc:
        print(json.dumps({"error": "BUDGET_EXCEEDED", "message": str(exc)}), file=sys.stderr)
        return 2
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
