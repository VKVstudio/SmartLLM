#!/usr/bin/env python3
"""Split the official Apache-2.0 Z-Image-Turbo weights into GitHub-Release-safe parts.

Inputs (local ComfyUI-style files, byte-identical to Comfy-Org/Z-Image-Turbo on HF):
  - z_image_turbo_bf16.safetensors  (DiT, 12.3 GB -> 7 parts)
  - qwen_3_4b.safetensors           (text encoder, 8.0 GB -> 5 parts)
  - ae.safetensors                  (Flux.1 AE VAE, Apache-2.0, 335 MB -> single asset)

Output: dist/releases/zimage/ with <= 1900 MiB parts + ZIMAGE_SHA256SUMS.txt
(final-file digests first, then per-part digests) + streaming reassembly parity check.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

CHUNK_MIB = 1900
IO_BLOCK = 16 * 1024 * 1024
COMFY = Path("/mnt/rescue/ComfyUI_windows_portable/ComfyUI/models")
DEFAULT_FILES = [
    COMFY / "diffusion_models" / "z_image_turbo_bf16.safetensors",
    COMFY / "text_encoders" / "qwen_3_4b.safetensors",
    COMFY / "vae" / "ae.safetensors",
]
SPLIT_THRESHOLD = 2 * 1024**3


def _fadvise(fd: int, off: int, ln: int) -> None:
    fn = getattr(os, "posix_fadvise", None)
    flag = getattr(os, "POSIX_FADV_DONTNEED", None)
    if fn and flag:
        try:
            fn(fd, off, ln, flag)
        except OSError:
            pass


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        fd = f.fileno()
        off = 0
        while True:
            b = f.read(IO_BLOCK)
            if not b:
                break
            h.update(b)
            _fadvise(fd, off, len(b))
            off += len(b)
    return h.hexdigest()


def split_one(src: Path, out_dir: Path) -> list[tuple[str, str]]:
    """Return [(name, sha256)] for the final file and its parts (or the file itself)."""
    total = src.stat().st_size
    entries: list[tuple[str, str]] = []
    if total < SPLIT_THRESHOLD:
        dst = out_dir / src.name
        if not dst.exists() or dst.stat().st_size != total:
            with src.open("rb") as fi, dst.open("wb") as fo:
                while True:
                    b = fi.read(IO_BLOCK)
                    if not b:
                        break
                    fo.write(b)
        entries.append((src.name, sha256_file(dst)))
        print(f"  {src.name}: single asset ({total} B)", flush=True)
        return entries

    chunk = CHUNK_MIB * 1024 * 1024
    n_parts = (total + chunk - 1) // chunk
    width = max(2, len(str(n_parts)))
    whole = hashlib.sha256()
    parts: list[tuple[str, str, int]] = []
    read_total = 0
    with src.open("rb") as fi:
        fd = fi.fileno()
        for i in range(1, n_parts + 1):
            name = f"{src.name}.part{i:0{width}d}"
            pp = out_dir / name
            ph = hashlib.sha256()
            remaining = min(chunk, total - read_total)
            written = 0
            with pp.open("wb") as fo:
                ofd = fo.fileno()
                while written < remaining:
                    b = fi.read(min(IO_BLOCK, remaining - written))
                    if not b:
                        raise EOFError(f"Unexpected EOF in {src}")
                    fo.write(b)
                    whole.update(b)
                    ph.update(b)
                    _fadvise(fd, read_total, len(b))
                    _fadvise(ofd, written, len(b))
                    written += len(b)
                    read_total += len(b)
                fo.flush()
                os.fsync(ofd)
            parts.append((name, ph.hexdigest(), written))
            print(f"  [{i}/{n_parts}] {name} ({written} B)", flush=True)

    vh = hashlib.sha256()
    vtotal = 0
    for name, psha, psize in parts:
        pp = out_dir / name
        if pp.stat().st_size != psize or sha256_file(pp) != psha:
            raise RuntimeError(f"On-disk part verification failed: {pp}")
        with pp.open("rb") as f:
            fd = f.fileno()
            off = 0
            while True:
                b = f.read(IO_BLOCK)
                if not b:
                    break
                vh.update(b)
                _fadvise(fd, off, len(b))
                off += len(b)
                vtotal += len(b)
    if vtotal != total or vh.hexdigest() != whole.hexdigest():
        raise RuntimeError(f"Reassembly parity FAILED for {src.name}")
    entries.append((src.name, whole.hexdigest()))
    entries.extend((name, psha) for name, psha, _ in parts)
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Split official Z-Image-Turbo weights for GitHub Release.")
    parser.add_argument("--out-dir", type=Path, default=Path("dist/releases/zimage"))
    parser.add_argument("--files", type=Path, nargs="*", default=DEFAULT_FILES)
    args = parser.parse_args(argv)
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    all_entries: list[tuple[str, str]] = []
    for src in args.files:
        src = src.resolve()
        if not src.is_file():
            raise FileNotFoundError(src)
        print(f"== {src.name} ({src.stat().st_size} B)", flush=True)
        all_entries.extend(split_one(src, out_dir))

    finals = {(out_dir / n) for n, _ in all_entries if ".part" not in n}
    manifest = ["# Z-Image-Turbo (official, Apache-2.0) GitHub Release Split Manifest",
                "# Sources: Comfy-Org/Z-Image-Turbo (HF) + Tongyi-MAI/Z-Image-Turbo; VAE: Flux.1 AE (Apache-2.0)"]
    manifest += [f"{sha}  {name}" for name, sha in all_entries]
    (out_dir / "ZIMAGE_SHA256SUMS.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"PASS: {len(all_entries)} manifest entries, {len(finals)} final files -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())