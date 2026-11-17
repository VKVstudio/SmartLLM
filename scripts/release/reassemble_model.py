#!/usr/bin/env python3
"""Cross-platform verifier and reassembler for split SmartLLM GGUF Release parts.

Verifies every ``*.partNN`` file against ``MODEL_SHA256SUMS.txt``, streams them
sequentially into a temporary file using bounded RAM (and ``POSIX_FADV_DONTNEED``
on Linux when available), checks the reassembled byte count and SHA-256 digest,
and atomically promotes the final GGUF file.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

CHUNK_BYTES = 16 * 1024 * 1024
DEFAULT_MODEL_NAME = "SmartLLM-v2-K320-V1.gguf"
DEFAULT_MANIFEST = "MODEL_SHA256SUMS.txt"


def _fadvise_dontneed(fd: int, offset: int, length: int) -> None:
    """Release Linux filesystem page cache pages when supported."""
    fn = getattr(os, "posix_fadvise", None)
    flag = getattr(os, "POSIX_FADV_DONTNEED", None)
    if fn is None or flag is None:
        return
    try:
        fn(fd, offset, length, flag)
    except OSError:
        pass


def parse_sha256sums(manifest_path: Path) -> tuple[tuple[str, str] | None, list[tuple[str, str]]]:
    """Return (final_model_entry, sorted_part_entries) parsed from MODEL_SHA256SUMS.txt."""
    final_entry: tuple[str, str] | None = None
    parts: list[tuple[str, str]] = []
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split(None, 1)
        if len(fields) != 2:
            raise ValueError(f"Malformed SHA256SUMS line in {manifest_path}: {raw_line!r}")
        digest, filename = fields[0].lower(), fields[1].lstrip("*").strip()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError(f"Invalid SHA-256 hex digest in {manifest_path}: {digest!r}")
        if ".part" in filename:
            parts.append((digest, filename))
        elif filename.endswith(".gguf") and "mmproj" not in filename.lower():
            final_entry = (digest, filename)
    parts.sort(key=lambda item: item[1])
    return final_entry, parts


def sha256_file(path: Path) -> tuple[str, int]:
    """Stream-compute (sha256_hex, size_bytes) of a file with minimal page-cache retention."""
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as fh:
        fd = fh.fileno()
        while True:
            buf = fh.read(CHUNK_BYTES)
            if not buf:
                break
            digest.update(buf)
            _fadvise_dontneed(fd, total, len(buf))
            total += len(buf)
    return digest.hexdigest(), total


def reassemble(
    source_dir: Path,
    output_path: Path | None = None,
    manifest_name: str = DEFAULT_MANIFEST,
    cleanup: bool = False,
    skip_part_check: bool = False,
) -> dict[str, object]:
    """Verify part hashes, stream-concatenate into output_path, and verify final digest."""
    manifest_path = source_dir / manifest_name
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    final_entry, part_entries = parse_sha256sums(manifest_path)
    if not part_entries:
        raise ValueError(f"No .partNN entries found in {manifest_path}")

    target_name = final_entry[1] if final_entry else DEFAULT_MODEL_NAME
    target_path = output_path if output_path is not None else (source_dir / target_name)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_name(target_path.name + ".assembling.tmp")

    for digest_expected, part_name in part_entries:
        part_path = source_dir / part_name
        if not part_path.is_file():
            raise FileNotFoundError(f"Missing part file: {part_path}")
        if not skip_part_check:
            actual_digest, _ = sha256_file(part_path)
            if actual_digest != digest_expected:
                raise ValueError(
                    f"Checksum mismatch for {part_name}: expected {digest_expected}, got {actual_digest}"
                )

    final_hasher = hashlib.sha256()
    written_bytes = 0
    try:
        with tmp_path.open("wb") as out_fh:
            out_fd = out_fh.fileno()
            for _, part_name in part_entries:
                part_path = source_dir / part_name
                part_offset = 0
                with part_path.open("rb") as in_fh:
                    in_fd = in_fh.fileno()
                    while True:
                        buf = in_fh.read(CHUNK_BYTES)
                        if not buf:
                            break
                        out_fh.write(buf)
                        final_hasher.update(buf)
                        _fadvise_dontneed(in_fd, part_offset, len(buf))
                        _fadvise_dontneed(out_fd, written_bytes, len(buf))
                        part_offset += len(buf)
                        written_bytes += len(buf)
            out_fh.flush()
            os.fsync(out_fd)

        final_digest = final_hasher.hexdigest()
        if final_entry and final_digest != final_entry[0]:
            raise ValueError(
                f"Assembled SHA-256 mismatch for {target_path.name}: "
                f"expected {final_entry[0]}, got {final_digest}"
            )
        os.replace(tmp_path, target_path)
    except BaseException:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    removed_parts: list[str] = []
    if cleanup:
        for _, part_name in part_entries:
            part_path = source_dir / part_name
            if part_path.exists():
                part_path.unlink()
                removed_parts.append(part_name)

    return {
        "status": "PASS",
        "output": str(target_path),
        "bytes": written_bytes,
        "sha256": final_digest,
        "parts_joined": len(part_entries),
        "cleaned_up_parts": len(removed_parts),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify & reassemble SmartLLM GGUF release parts.")
    parser.add_argument("--dir", type=Path, default=Path("."), help="Directory containing partNN files and MODEL_SHA256SUMS.txt")
    parser.add_argument("--output", type=Path, default=None, help="Output GGUF file path (defaults to --dir/SmartLLM-v2-K320-V1.gguf)")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, help="SHA-256 manifest filename inside --dir")
    parser.add_argument("--skip-part-check", action="store_true", help="Skip pre-pass part checks and verify only the final assembled SHA-256")
    parser.add_argument("--cleanup", action="store_true", help="Remove .partNN files only after final SHA-256 passes")
    args = parser.parse_args(argv)

    result = reassemble(
        source_dir=args.dir.resolve(),
        output_path=args.output.resolve() if args.output else None,
        manifest_name=args.manifest,
        cleanup=args.cleanup,
        skip_part_check=args.skip_part_check,
    )
    print(f"PASS: {result['output']} ({result['bytes']} bytes, sha256={result['sha256']}, parts={result['parts_joined']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
