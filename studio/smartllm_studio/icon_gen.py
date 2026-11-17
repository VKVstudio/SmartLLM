#!/usr/bin/env python3
"""Deterministic CPU-only icon generator for SmartLLM Studio (PNG + multi-res Windows ICO)."""

from __future__ import annotations

import os
from pathlib import Path
import struct
import zlib

ICO_SIZES = (16, 32, 48, 64, 256)


def render_svg_to_png_and_ico(
    svg_path: Path,
    png_out: Path,
    ico_out: Path,
    png_size: int = 256,
    ico_sizes: tuple[int, ...] = ICO_SIZES,
) -> dict[str, object]:
    """Render smartllm-logo.svg to a 256x256 PNG and multi-size RGBA Windows .ico on CPU."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

    png_out.parent.mkdir(parents=True, exist_ok=True)
    ico_out.parent.mkdir(parents=True, exist_ok=True)

    rendered_buffers: dict[int, bytes] = {}
    used_backend = "fallback_stdlib"

    try:
        from PyQt6.QtCore import QByteArray, QBuffer, QIODevice, QRectF
        from PyQt6.QtGui import QColor, QGuiApplication, QImage, QPainter
        from PyQt6.QtSvg import QSvgRenderer

        app = QGuiApplication.instance() or QGuiApplication([])
        renderer = QSvgRenderer(str(svg_path))
        if not renderer.isValid():
            raise RuntimeError(f"Invalid SVG file: {svg_path}")

        all_sizes = sorted(set(ico_sizes) | {png_size})
        for sz in all_sizes:
            img = QImage(sz, sz, QImage.Format.Format_RGBA8888)
            img.fill(QColor(11, 13, 18, 255))  # Obsidian #0b0d12 background badge
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            margin = max(1.0, sz * 0.08)
            renderer.render(painter, QRectF(margin, margin, sz - 2 * margin, sz - 2 * margin))
            painter.end()

            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            img.save(buf, "PNG")
            buf.close()
            rendered_buffers[sz] = bytes(ba)
        used_backend = "PyQt6.QtSvg"
        _ = app
    except Exception:
        for sz in sorted(set(ico_sizes) | {png_size}):
            rendered_buffers[sz] = _make_obsidian_violet_png(sz)

    png_out.write_bytes(rendered_buffers[png_size])
    ico_bytes = _pack_pngs_to_ico([rendered_buffers[s] for s in ico_sizes], list(ico_sizes))
    ico_out.write_bytes(ico_bytes)

    return {
        "backend": used_backend,
        "png_path": str(png_out),
        "png_bytes": png_out.stat().st_size,
        "ico_path": str(ico_out),
        "ico_bytes": ico_out.stat().st_size,
        "ico_sizes": list(ico_sizes),
    }


def _pack_pngs_to_ico(png_blobs: list[bytes], sizes: list[int]) -> bytes:
    """Pack multiple RGBA PNG blobs into a standard Windows Vista/11 ICONDIR container."""
    count = len(png_blobs)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries = bytearray()
    payload = bytearray()
    for blob, sz in zip(png_blobs, sizes):
        w_byte = 0 if sz >= 256 else sz
        h_byte = 0 if sz >= 256 else sz
        entry = struct.pack(
            "<BBBBHHII",
            w_byte,
            h_byte,
            0,
            0,
            1,
            32,
            len(blob),
            offset,
        )
        entries.extend(entry)
        payload.extend(blob)
        offset += len(blob)
    return bytes(header) + bytes(entries) + bytes(payload)


def _make_obsidian_violet_png(size: int) -> bytes:
    """Pure-stdlib RGBA PNG fallback in Obsidian (#0b0d12) & Violet (#c084fc)."""
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            cx = abs(x - size // 2) < max(2, size // 10)
            cy = (y > size * 0.2 and y < size * 0.8)
            if cx and cy:
                rows.extend((192, 132, 252, 255))
            else:
                rows.extend((11, 13, 18, 255))

    def _chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(rows), level=6)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


if __name__ == "__main__":
    studio_root = Path(__file__).resolve().parents[1]
    res = render_svg_to_png_and_ico(
        svg_path=studio_root / "assets" / "smartllm-logo.svg",
        png_out=studio_root / "assets" / "smartllm-studio.png",
        ico_out=studio_root / "assets" / "smartllm-studio.ico",
    )
    print(res)
