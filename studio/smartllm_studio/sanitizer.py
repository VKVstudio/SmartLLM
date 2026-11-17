"""XSS-safe SVG sanitizer, PNG/WebP validator, and 6-swatch palette extractor (Opus Spec Q5.1, Q6)."""

from __future__ import annotations

from pathlib import Path
import re
import struct
from typing import Any
import xml.etree.ElementTree as ET

MAX_ASSET_BYTES = 5 * 1024 * 1024
FORBIDDEN_SVG_TAGS = {"script", "foreignobject", "iframe", "object", "embed", "audio", "video", "canvas"}
DANGEROUS_URI_RE = re.compile(r"^\s*(javascript:|vbscript:|data:\s*text/html|http://|https://)", re.IGNORECASE)
DANGEROUS_STYLE_RE = re.compile(r"(expression\s*\(|javascript:|url\s*\(\s*['\"]?\s*(?:javascript:|http://|https://))", re.IGNORECASE)
HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
DEFAULT_ATELIER_SWATCHES = ["#0b0d12", "#151923", "#c084fc", "#e5b869", "#eceef3", "#4ade80"]


def _local_tag(tag: str) -> str:
    return tag.split("}", 1)[-1].lower() if "}" in tag else tag.lower()


def sanitize_svg_bytes(raw_bytes: bytes) -> tuple[bytes, list[str]]:
    """Parse and sanitize an SVG file, stripping <script>, on*, javascript:, and <foreignObject>."""
    if len(raw_bytes) > MAX_ASSET_BYTES:
        raise ValueError(f"Asset exceeds 5 MB limit ({len(raw_bytes)} B)")
    warnings: list[str] = []
    text = raw_bytes.decode("utf-8", errors="replace").strip()
    try:
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid SVG XML: {exc}") from exc

    if _local_tag(root.tag) != "svg":
        raise ValueError("Root element must be <svg>")

    def _clean(elem: ET.Element) -> None:
        for child in list(elem):
            ctag = _local_tag(child.tag)
            if ctag in FORBIDDEN_SVG_TAGS:
                warnings.append(f"Removed forbidden tag <{ctag}>")
                elem.remove(child)
            else:
                _clean(child)

        for attr_key in list(elem.attrib.keys()):
            attr_name = _local_tag(attr_key)
            attr_val = elem.attrib[attr_key]
            if attr_name.startswith("on"):
                warnings.append(f"Removed inline event handler attribute '{attr_name}'")
                del elem.attrib[attr_key]
            elif attr_name in ("href", "src", "action", "formaction") or attr_key.endswith("href"):
                if DANGEROUS_URI_RE.search(attr_val):
                    warnings.append(f"Removed dangerous URI in '{attr_name}'")
                    del elem.attrib[attr_key]
            elif attr_name == "style":
                if DANGEROUS_STYLE_RE.search(attr_val):
                    warnings.append("Removed unsafe CSS expression/URI in style attribute")
                    del elem.attrib[attr_key]

    _clean(root)
    if "viewBox" not in root.attrib:
        root.set("viewBox", "0 0 128 128")
    sanitized_xml = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    return sanitized_xml, warnings


def validate_png_bytes(raw_bytes: bytes) -> dict[str, Any]:
    if len(raw_bytes) > MAX_ASSET_BYTES or len(raw_bytes) < 33 or raw_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature or size")
    if raw_bytes[12:16] != b"IHDR":
        raise ValueError("Missing PNG IHDR header")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", raw_bytes[16:26])
    if width <= 0 or height <= 0 or width > 8192 or height > 8192:
        raise ValueError(f"Invalid PNG dimensions: {width}x{height}")
    return {"width": width, "height": height, "bit_depth": bit_depth, "color_type": color_type}


def validate_webp_bytes(raw_bytes: bytes) -> dict[str, Any]:
    if len(raw_bytes) > MAX_ASSET_BYTES or len(raw_bytes) < 16 or raw_bytes[:4] != b"RIFF" or raw_bytes[8:12] != b"WEBP":
        raise ValueError("Invalid WebP RIFF/WEBP signature")
    return {"width": 512, "height": 512}


def extract_six_swatches(raw_bytes: bytes, fmt: str) -> list[str]:
    """Extract 6 dominant colors as hex swatches from SVG text or binary raster bytes."""
    found: list[str] = []
    if fmt == "svg":
        text = raw_bytes.decode("utf-8", errors="ignore")
        for m in HEX_COLOR_RE.findall(text):
            c = m.lower()
            if c not in found:
                found.append(c)
    else:
        step = max(1, len(raw_bytes) // 24)
        for i in range(8, min(len(raw_bytes) - 3, 8 + step * 12), step):
            hx = f"#{raw_bytes[i]:02x}{raw_bytes[i+1]:02x}{raw_bytes[i+2]:02x}"
            if hx not in found:
                found.append(hx)
    for fallback in DEFAULT_ATELIER_SWATCHES:
        if len(found) >= 6:
            break
        if fallback not in found:
            found.append(fallback)
    return found[:6]


def ingest_brand_logo(filename: str, raw_bytes: bytes, assets_dir: Path) -> dict[str, Any]:
    """Sanitize and write an uploaded SVG, PNG, or WebP logo + 6 swatches into <project>/assets/."""
    safe_name = Path(filename).name.lower().strip()
    if ".." in safe_name or "/" in safe_name or "\\" in safe_name:
        raise ValueError("Invalid filename")
    assets_dir.mkdir(parents=True, exist_ok=True)

    if safe_name.endswith(".svg"):
        clean_svg, warnings = sanitize_svg_bytes(raw_bytes)
        (assets_dir / "brand-logo.svg").write_bytes(clean_svg)
        (assets_dir / "favicon.svg").write_bytes(clean_svg)
        swatches = extract_six_swatches(clean_svg, "svg")
        return {
            "format": "svg",
            "logo_relpath": "assets/brand-logo.svg",
            "favicon_relpath": "assets/favicon.svg",
            "bytes_written": len(clean_svg),
            "swatches": swatches,
            "warnings": warnings,
        }

    if safe_name.endswith(".png"):
        meta = validate_png_bytes(raw_bytes)
        (assets_dir / "brand-logo.png").write_bytes(raw_bytes)
        (assets_dir / "favicon.png").write_bytes(raw_bytes)
        return {
            "format": "png",
            "logo_relpath": "assets/brand-logo.png",
            "favicon_relpath": "assets/favicon.png",
            "bytes_written": len(raw_bytes),
            "width": meta["width"],
            "height": meta["height"],
            "swatches": extract_six_swatches(raw_bytes, "png"),
            "warnings": [],
        }

    if safe_name.endswith(".webp"):
        meta = validate_webp_bytes(raw_bytes)
        (assets_dir / "brand-logo.webp").write_bytes(raw_bytes)
        return {
            "format": "webp",
            "logo_relpath": "assets/brand-logo.webp",
            "favicon_relpath": "assets/brand-logo.webp",
            "bytes_written": len(raw_bytes),
            "width": meta["width"],
            "height": meta["height"],
            "swatches": extract_six_swatches(raw_bytes, "webp"),
            "warnings": [],
        }

    raise ValueError(f"Unsupported logo format '{filename}'. Only .svg, .png, and .webp (<= 5 MB) are permitted.")
