#!/usr/bin/env python3
"""Split SmartLLM-v2-K320-V1.gguf into <2 GiB GitHub-Release parts and verify parity.

Why binary chunking instead of ``llama-gguf-split``?
``SmartLLM-v2-K320-V1.gguf`` embeds ``per_layer_token_embd.weight`` as a single
26.82 GiB (28.80 GB) contiguous tensor. ``llama-gguf-split`` splits strictly on
tensor boundaries and therefore cannot keep shards under GitHub's 2 GiB release
asset ceiling. Splitting at 1900 MiB (1,992,294,400 bytes) produces 30 assets
under 2.0 GB each and reassembles bit-for-bit into the exact GGUF verified for
direct NVMe pread and zero-swap execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = ROOT / "models" / "SmartLLM-v2-K320-V1.gguf"
DEFAULT_MMPROJ = ROOT / "models" / "mmproj-Qwen3.8-Flash-Next-BF16.gguf"
DEFAULT_OUT_DIR = ROOT / "dist" / "releases" / "model"

IO_BLOCK_BYTES = 16 * 1024 * 1024
GITHUB_SAFE_LIMIT_BYTES = 2 * 1000 * 1000 * 1000  # < 2.0 GB decimal & < 2 GiB binary
DEFAULT_CHUNK_MIB = 1900  # 1,992,294,400 bytes (< 2.0 GB)


def _fadvise_dontneed(fd: int, offset: int, length: int) -> None:
    fn = getattr(os, "posix_fadvise", None)
    flag = getattr(os, "POSIX_FADV_DONTNEED", None)
    if fn is None or flag is None:
        return
    try:
        fn(fd, offset, length, flag)
    except OSError:
        pass


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as fh:
        fd = fh.fileno()
        while True:
            buf = fh.read(IO_BLOCK_BYTES)
            if not buf:
                break
            digest.update(buf)
            _fadvise_dontneed(fd, total, len(buf))
            total += len(buf)
    return digest.hexdigest(), total


def copy_reassembly_helpers(out_dir: Path, mmproj_path: Path | None) -> None:
    rel_dir = Path(__file__).resolve().parent
    for script_name in ("reassemble_model.py", "reassemble_model.sh", "reassemble_model.ps1"):
        src = rel_dir / script_name
        if not src.is_file():
            raise FileNotFoundError(f"Missing helper script: {src}")
        dst = out_dir / script_name
        shutil.copy2(src, dst)
        if script_name.endswith((".py", ".sh")):
            dst.chmod(0o755)

    mmproj_line = (
        f"- Keep `{mmproj_path.name}` in the same `models/` folder (no split needed, `< 1 GiB`).\n"
        if mmproj_path and mmproj_path.is_file()
        else ""
    )
    readme_text = (
        "# SmartLLM v2 (`K=320-V1`) — GitHub Release Reassembly\n\n"
        "Download all `SmartLLM-v2-K320-V1.gguf.part01` .. `.partNN` files, "
        "`MODEL_SHA256SUMS.txt`, and one of the reassembly scripts below into the same directory.\n\n"
        "### Linux / macOS\n"
        "```bash\n"
        "bash reassemble_model.sh\n"
        "# Optional: verify and remove .part* files after assembly passes\n"
        "bash reassemble_model.sh --cleanup\n"
        "```\n\n"
        "### Windows 11 (`PowerShell`)\n"
        "```powershell\n"
        "powershell -ExecutionPolicy Bypass -File .\\reassemble_model.ps1\n"
        "# Or delete .part* automatically once SHA-256 matches:\n"
        "powershell -ExecutionPolicy Bypass -File .\\reassemble_model.ps1 -Cleanup\n"
        "```\n\n"
        "### Cross-Platform Python (3.10+)\n"
        "```bash\n"
        "python3 reassemble_model.py --cleanup\n"
        "```\n\n"
        f"{mmproj_line}"
    )
    (out_dir / "README_MODEL_ASSEMBLY.md").write_text(readme_text, encoding="utf-8")


def split_model(
    model_path: Path,
    out_dir: Path,
    chunk_mib: int = DEFAULT_CHUNK_MIB,
    mmproj_path: Path | None = None,
) -> dict[str, object]:
    if not model_path.is_file():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    chunk_bytes = chunk_mib * 1024 * 1024
    if chunk_bytes <= 0 or chunk_bytes >= GITHUB_SAFE_LIMIT_BYTES:
        raise ValueError(f"chunk_mib={chunk_mib} ({chunk_bytes} B) exceeds GitHub-safe 2.0 GB ceiling")

    total_size = model_path.stat().st_size
    num_parts = (total_size + chunk_bytes - 1) // chunk_bytes
    pad_width = max(2, len(str(num_parts)))

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob(f"{model_path.name}.part*"):
        stale.unlink()

    whole_hasher = hashlib.sha256()
    parts_meta: list[dict[str, object]] = []
    bytes_read_total = 0

    with model_path.open("rb") as src_fh:
        src_fd = src_fh.fileno()
        for idx in range(1, num_parts + 1):
            part_name = f"{model_path.name}.part{idx:0{pad_width}d}"
            part_path = out_dir / part_name
            part_hasher = hashlib.sha256()
            part_written = 0
            remaining_in_part = min(chunk_bytes, total_size - bytes_read_total)

            with part_path.open("wb") as dst_fh:
                dst_fd = dst_fh.fileno()
                while part_written < remaining_in_part:
                    to_read = min(IO_BLOCK_BYTES, remaining_in_part - part_written)
                    buf = src_fh.read(to_read)
                    if not buf:
                        raise EOFError(f"Unexpected EOF in {model_path} at offset {bytes_read_total}")
                    dst_fh.write(buf)
                    whole_hasher.update(buf)
                    part_hasher.update(buf)
                    _fadvise_dontneed(src_fd, bytes_read_total, len(buf))
                    _fadvise_dontneed(dst_fd, part_written, len(buf))
                    part_written += len(buf)
                    bytes_read_total += len(buf)
                dst_fh.flush()
                os.fsync(dst_fd)

            parts_meta.append(
                {
                    "part_index": idx,
                    "name": part_name,
                    "bytes": part_written,
                    "sha256": part_hasher.hexdigest(),
                }
            )
            print(f"[{idx}/{num_parts}] {part_name} ({part_written} B, sha256={parts_meta[-1]['sha256'][:12]}...)", flush=True)

    if bytes_read_total != total_size:
        raise RuntimeError(f"Read size mismatch: {bytes_read_total} != {total_size}")

    model_sha256 = whole_hasher.hexdigest()
    mmproj_meta: dict[str, object] | None = None
    if mmproj_path and mmproj_path.is_file():
        mm_sha, mm_size = sha256_file(mmproj_path)
        mmproj_meta = {
            "name": mmproj_path.name,
            "path": str(mmproj_path),
            "bytes": mm_size,
            "sha256": mm_sha,
        }

    # Verify streaming concatenation matches source SHA-256 identically before finishing
    verify_hasher = hashlib.sha256()
    verify_total = 0
    for part in parts_meta:
        p = out_dir / str(part["name"])
        p_hash, p_size = sha256_file(p)
        if p_size != part["bytes"] or p_hash != part["sha256"]:
            raise RuntimeError(f"On-disk verification failed for {p}")
        with p.open("rb") as vh:
            vfd = vh.fileno()
            voff = 0
            while True:
                buf = vh.read(IO_BLOCK_BYTES)
                if not buf:
                    break
                verify_hasher.update(buf)
                _fadvise_dontneed(vfd, voff, len(buf))
                voff += len(buf)
                verify_total += len(buf)

    if verify_total != total_size or verify_hasher.hexdigest() != model_sha256:
        raise RuntimeError("Reassembly stream parity check FAILED!")

    manifest_lines = [
        f"# SmartLLM-v2-K320-V1 GitHub Release Split Manifest ({num_parts} parts x <= {chunk_mib} MiB)",
        f"{model_sha256}  {model_path.name}",
    ]
    if mmproj_meta:
        manifest_lines.append(f"{mmproj_meta['sha256']}  {mmproj_meta['name']}")
    for part in parts_meta:
        manifest_lines.append(f"{part['sha256']}  {part['name']}")

    (out_dir / "MODEL_SHA256SUMS.txt").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    copy_reassembly_helpers(out_dir, mmproj_path)

    report = {
        "status": "PASS",
        "source_model": model_path.name,
        "bytes": total_size,
        "sha256": model_sha256,
        "chunk_mib": chunk_mib,
        "chunk_bytes": chunk_bytes,
        "parts_count": len(parts_meta),
        "out_dir": str(out_dir),
        "mmproj": mmproj_meta,
        "parts": parts_meta,
    }
    (out_dir / "model_split_manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Split SmartLLM GGUF into <2 GiB parts with SHA-256 parity verification.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--mmproj", type=Path, default=DEFAULT_MMPROJ)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--chunk-mib", type=int, default=DEFAULT_CHUNK_MIB)
    args = parser.parse_args(argv)

    report = split_model(
        model_path=args.model.resolve(),
        out_dir=args.out_dir.resolve(),
        chunk_mib=args.chunk_mib,
        mmproj_path=args.mmproj.resolve() if args.mmproj else None,
    )
    print(
        f"PASS: {report['parts_count']} parts in {report['out_dir']} "
        f"(total={report['bytes']} B, sha256={report['sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
