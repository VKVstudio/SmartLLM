#!/usr/bin/env python3
"""Fetch and verify SIL OFL-1.1 WOFF2 fonts & 100% MIT JS libraries into templates/vendor/."""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import tarfile
from typing import Any
import urllib.parse
import urllib.request

STUDIO_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = STUDIO_ROOT / "smartllm_studio"
MANIFEST_SRC = PKG_ROOT / "kb" / "visual_prompting" / "phase2_vendor_manifest.json"
VENDOR_DIR = PKG_ROOT / "templates" / "vendor"

FACE_RE = re.compile(r"(?:/\*[^*]*\*/\s*)?@font-face\s*\{[^}]+\}", re.S)
URL_WOFF2_RE = re.compile(r"url\(\./files/([^)]+\.woff2)\)")


def _fetch_npm_tarball(pkg: str) -> tuple[dict[str, Any], bytes]:
    url = f"https://registry.npmjs.org/{urllib.parse.quote(pkg, safe='')}/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "SmartLLM-Vendor-Fetch/2.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        meta = json.loads(resp.read().decode("utf-8"))
    tb_url = str(meta["dist"]["tarball"])
    integ = str(meta["dist"].get("integrity") or "")
    req_tb = urllib.request.Request(tb_url, headers={"User-Agent": "SmartLLM-Vendor-Fetch/2.0"})
    with urllib.request.urlopen(req_tb, timeout=45) as resp:
        raw = resp.read()
    if integ.startswith("sha512-"):
        expected = integ.removeprefix("sha512-")
        actual = base64.b64encode(hashlib.sha512(raw).digest()).decode("ascii")
        if actual != expected:
            raise ValueError(f"SRI SHA-512 mismatch for {pkg}: expected {expected[:16]}, got {actual[:16]}")
    elif meta["dist"].get("shasum"):
        actual_sha1 = hashlib.sha1(raw).hexdigest()
        if actual_sha1 != meta["dist"]["shasum"]:
            raise ValueError(f"SHA-1 mismatch for {pkg}")
    return meta, raw


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _wanted_woff2(fname: str, base_prefix: str) -> bool:
    for subset in ("cyrillic", "latin", "latin-ext"):
        if fname.startswith(f"{base_prefix}-{subset}-") and f"-{subset}-ext-" not in fname:
            return True
    return False


def _extract_font(entry: dict[str, Any], out_root: Path) -> dict[str, Any]:
    pkg = str(entry["pkg"])
    fid = str(entry["id"])
    fdir = out_root / "fonts" / fid
    fdir.mkdir(parents=True, exist_ok=True)
    meta, raw = _fetch_npm_tarball(pkg)
    version = str(meta.get("version") or "")
    pkg_slug = pkg.split("/", 1)[-1]

    css_candidates: list[str] = []
    if entry.get("pkg_kind") == "static":
        for w in entry.get("weights") or [400]:
            css_candidates.append(f"package/{w}.css")
            if entry.get("italic"):
                css_candidates.append(f"package/{w}-italic.css")
    else:
        css_candidates.append("package/index.css")
        if entry.get("italic"):
            css_candidates.append("package/wght-italic.css")
        if "wdth" in str(entry.get("axes") or ""):
            css_candidates.append("package/wdth.css")

    files_written: list[dict[str, Any]] = []
    seen_woff2: set[str] = set()
    css_blocks: list[str] = []

    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        members = {m.name: m for m in tf.getmembers() if m.isfile()}

        # Extract LICENSE / OFL
        for lic_cand in ("package/LICENSE", "package/LICENSE.md", "package/OFL.txt"):
            if lic_cand in members:
                lic_bytes = tf.extractfile(members[lic_cand]).read()
                lic_out = fdir / Path(lic_cand).name
                lic_out.write_bytes(lic_bytes)
                files_written.append({
                    "relpath": lic_out.relative_to(VENDOR_DIR).as_posix(),
                    "bytes": len(lic_bytes),
                    "sha256": _sha256_bytes(lic_bytes),
                })
                break

        for css_member in css_candidates:
            if css_member not in members:
                continue
            css_raw = tf.extractfile(members[css_member]).read().decode("utf-8", errors="replace")
            for m in FACE_RE.finditer(css_raw):
                block = m.group(0)
                wmatch = URL_WOFF2_RE.search(block)
                if not wmatch:
                    continue
                wf_name = Path(wmatch.group(1)).name
                if not _wanted_woff2(wf_name, pkg_slug):
                    continue
                tar_wf = f"package/files/{wf_name}"
                if tar_wf not in members:
                    continue
                if wf_name not in seen_woff2:
                    seen_woff2.add(wf_name)
                    wf_bytes = tf.extractfile(members[tar_wf]).read()
                    wf_out = fdir / wf_name
                    wf_out.write_bytes(wf_bytes)
                    files_written.append({
                        "relpath": wf_out.relative_to(VENDOR_DIR).as_posix(),
                        "bytes": len(wf_bytes),
                        "sha256": _sha256_bytes(wf_bytes),
                    })
                # Clean .woff legacy entries if any & rewrite path to ./assets/fonts/<id>/
                clean_block = re.sub(
                    r"src:\s*url\(\./files/([^)]+\.woff2)\)\s*format\((['\"][^'\"]+['\"])\)(?:\s*,\s*url\([^)]+\.woff\)\s*format\(['\"]woff['\"]\))?\s*;",
                    rf"src: url('./assets/fonts/{fid}/\1') format('woff2');",
                    block,
                )
                css_blocks.append(clean_block.strip())

    has_cyr = any("-cyrillic-" in w and "-cyrillic-ext-" not in w for w in seen_woff2)
    has_lat = any("-latin-" in w and "-latin-ext-" not in w for w in seen_woff2)
    if not (has_cyr and has_lat):
        raise RuntimeError(f"Missing cyrillic/latin WOFF2 in {pkg}: {sorted(seen_woff2)}")

    font_css = "\n\n".join(css_blocks) + "\n"
    font_css_path = fdir / "font.css"
    font_css_bytes = font_css.encode("utf-8")
    font_css_path.write_bytes(font_css_bytes)
    files_written.append({
        "relpath": font_css_path.relative_to(VENDOR_DIR).as_posix(),
        "bytes": len(font_css_bytes),
        "sha256": _sha256_bytes(font_css_bytes),
    })

    return {
        "id": fid,
        "kind": "font",
        "pkg": pkg,
        "version": version,
        "license": str(entry["license"]),
        "family": str(entry["family"]),
        "css_name": str(entry["css_name"]),
        "woff2_files": sorted(seen_woff2),
        "files": files_written,
    }


JS_FILE_PLANS: dict[str, dict[str, Any]] = {
    "motion": {
        "pkg": "motion",
        "license_paths": ("package/LICENSE.md", "package/LICENSE"),
        "extract": {"package/dist/motion.js": "motion.js"},
    },
    "animejs": {
        "pkg": "animejs",
        "license_paths": ("package/LICENSE.md", "package/LICENSE"),
        "extract": {
            "package/dist/bundles/anime.esm.min.js": "anime.esm.min.js",
            "package/dist/bundles/anime.umd.min.js": "anime.umd.min.js",
        },
    },
    "lenis": {
        "pkg": "lenis",
        "license_paths": ("package/LICENSE", "package/LICENSE.md"),
        "extract": {
            "package/dist/lenis.mjs": "lenis.mjs",
            "package/dist/lenis.min.js": "lenis.min.js",
        },
    },
    "three": {
        "pkg": "three",
        "license_paths": ("package/LICENSE", "package/LICENSE.md"),
        "extract": {
            "package/build/three.module.js": "three.module.js",
            "package/build/three.core.js": "three.core.js",
        },
    },
}


def _extract_js(entry: dict[str, Any], out_root: Path) -> dict[str, Any]:
    lid = str(entry["id"])
    plan = JS_FILE_PLANS[lid]
    pkg = str(plan["pkg"])
    jdir = out_root / "js" / lid
    jdir.mkdir(parents=True, exist_ok=True)
    meta, raw = _fetch_npm_tarball(pkg)
    version = str(meta.get("version") or "")
    files_written: list[dict[str, Any]] = []

    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        members = {m.name: m for m in tf.getmembers() if m.isfile()}
        for lp in plan["license_paths"]:
            if lp in members:
                b = tf.extractfile(members[lp]).read()
                out_f = jdir / Path(lp).name
                out_f.write_bytes(b)
                files_written.append({"relpath": out_f.relative_to(VENDOR_DIR).as_posix(), "bytes": len(b), "sha256": _sha256_bytes(b)})
                break
        for src_path, dest_name in plan["extract"].items():
            if src_path not in members:
                raise KeyError(f"{src_path} missing in {pkg}@{version}")
            b = tf.extractfile(members[src_path]).read()
            out_f = jdir / dest_name
            out_f.write_bytes(b)
            files_written.append({"relpath": out_f.relative_to(VENDOR_DIR).as_posix(), "bytes": len(b), "sha256": _sha256_bytes(b)})

    return {
        "id": lid,
        "kind": "js",
        "pkg": pkg,
        "version": version,
        "license": str(entry["license"]),
        "repo": str(entry.get("repo") or ""),
        "files": files_written,
    }


def main() -> None:
    src = json.loads(MANIFEST_SRC.read_text(encoding="utf-8"))
    if VENDOR_DIR.exists():
        shutil.rmtree(VENDOR_DIR)
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)

    fonts = list(src["fonts_verified_cyrillic_ruble_numero"])
    js_libs = list(src["js_libraries_approved_for_bundling"])

    with ThreadPoolExecutor(max_workers=8) as ex:
        font_records = list(ex.map(lambda e: _extract_font(e, VENDOR_DIR), fonts))
        js_records = list(ex.map(lambda e: _extract_js(e, VENDOR_DIR), js_libs))

    total_bytes = sum(f["bytes"] for r in (font_records + js_records) for f in r["files"])
    manifest_out = {
        "schema_version": src["manifest_version"],
        "verified_date": src["verified_date"],
        "total_bytes": total_bytes,
        "fonts_count": len(font_records),
        "js_libs_count": len(js_records),
        "fonts": font_records,
        "js_libs": js_records,
    }
    (VENDOR_DIR / "MANIFEST.json").write_text(json.dumps(manifest_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    licenses_out = {
        "policy": src["policy"],
        "approved_fonts": [{"id": r["id"], "family": r["family"], "pkg": r["pkg"], "version": r["version"], "license": r["license"]} for r in font_records],
        "approved_js": [{"id": r["id"], "pkg": r["pkg"], "version": r["version"], "license": r["license"], "repo": r["repo"]} for r in js_records],
        "excluded_libraries": src["excluded_libraries_legal_boundary"],
    }
    (VENDOR_DIR / "LICENSES.json").write_text(json.dumps(licenses_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"VENDOR_FETCH_COMPLETE: fonts={len(font_records)}, js={len(js_records)}, total_mb={total_bytes / (1024*1024):.2f}")


if __name__ == "__main__":
    main()
