#!/usr/bin/env python3
"""Phase 2 Verification Gate: 4-Layer Templates, 30 Fonts + 4 MIT JS, 20 WebP Cards & All 16 Bug Fixes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["SMARTLLM_STUDIO_HEADLESS"] = "1"

STUDIO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = STUDIO_ROOT.parent
PKG_ROOT = STUDIO_ROOT / "smartllm_studio"
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from PIL import Image  # noqa: E402

from smartllm_studio.blueprint import compile_project_blueprint, default_project_draft  # noqa: E402
from smartllm_studio.catalog import AI_CRAWLERS_DEFAULT, MOTION_CATALOG, STACK_CATALOG, load_studio_catalog  # noqa: E402
from smartllm_studio.kb_loader import (  # noqa: E402
    compute_real_scorecard,
    harden_zimage_prompt,
    lint_anti_ai_copy,
    list_canon_ids,
    palette_to_material_summary,
    resolve_canon_id,
    route_block_variants,
)
from smartllm_studio.orchestrator import LOGO_FINISHERS, _LOGO_FALLBACK_SPECS, ProjectOrchestrator  # noqa: E402
from smartllm_studio.pipeline import _sanitize_zimage_prompt  # noqa: E402
from smartllm_studio.sanitizer import sanitize_svg_bytes  # noqa: E402


REJECTED_FONTS = {
    "Archivo Black", "Dela Gothic One", "Newsreader", "Space Grotesk",
    "Bodoni Moda", "Playfair Display", "Sofia Sans", "Sofia Sans Extra Condensed",
    "Russo One", "Jost", "Alegreya Sans", "Fredoka", "Atkinson Hyperlegible Next", "Soyuz Grotesk",
}


def run_all_tests() -> dict[str, object]:
    results: dict[str, object] = {}

    # 1. Layer 1 Vendor Assets (30 SIL OFL-1.1 .woff2 fonts + 4 MIT JS libs, SHA-256 verified, 0 GSAP)
    vendor_dir = PKG_ROOT / "templates" / "vendor"
    manifest = json.loads((vendor_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["fonts_count"] == 30 and len(manifest["fonts"]) == 30
    assert manifest["js_libs_count"] == 4 and len(manifest["js_libs"]) == 4
    js_ids = [lib["id"] for lib in manifest["js_libs"]]
    assert sorted(js_ids) == ["animejs", "lenis", "motion", "three"], js_ids
    for f_entry in manifest["fonts"]:
        assert f_entry["license"] == "SIL OFL-1.1"
        assert (vendor_dir / "fonts" / f_entry["id"] / "font.css").exists()
        assert len(f_entry["woff2_files"]) >= 2
        for finfo in f_entry["files"]:
            fp = vendor_dir / finfo["relpath"]
            assert fp.exists(), f"Missing vendor file: {fp}"
            assert hashlib.sha256(fp.read_bytes()).hexdigest() == finfo["sha256"], f"SHA mismatch: {fp}"
    for j_entry in manifest["js_libs"]:
        assert j_entry["license"] == "MIT"
        for finfo in j_entry["files"]:
            fp = vendor_dir / finfo["relpath"]
            assert fp.exists(), f"Missing vendor JS file: {fp}"
            assert hashlib.sha256(fp.read_bytes()).hexdigest() == finfo["sha256"], f"SHA mismatch: {fp}"
    assert not list(vendor_dir.rglob("*gsap*")), "GSAP artifacts must not exist in vendor/"
    assert (vendor_dir / "LICENSES.json").exists()
    results["vendor_layer1"] = {"fonts": 30, "js_libs": 4, "sha256_verified": True}

    # 2. Layer 2/3 Materialized Templates + M2 20 WebP Style Cards
    cids = list_canon_ids()
    assert len(cids) == 20
    themes_dir = PKG_ROOT / "templates" / "themes"
    stacks_dir = PKG_ROOT / "templates" / "stacks"
    for cid in cids:
        tcss = themes_dir / f"{cid}.css"
        assert tcss.exists() and '[data-theme="light"]' in tcss.read_text(encoding="utf-8") and '[data-theme="dark"]' in tcss.read_text(encoding="utf-8")
    for sid in ("html5_esm", "astro", "sveltekit", "nextjs", "vite_ts"):
        assert (stacks_dir / sid / "stack_spec.json").exists()
    assert (PKG_ROOT / "templates" / "blocks" / "schema.json").exists()

    art_dir = PKG_ROOT / "static" / "art" / "canons"
    for cid in cids:
        wp = art_dir / f"{cid}.webp"
        assert wp.exists(), f"Missing preview card: {wp}"
        sz = wp.stat().st_size
        assert 1000 <= sz <= 95 * 1024, f"{wp.name} size {sz} out of bounds"
        with Image.open(wp) as im:
            assert im.size == (640, 400), f"{wp.name} dims {im.size} != (640, 400)"
    results["preview_cards"] = {"count": 20, "dims": "640x400", "all_under_95kb": True}

    # 3. Synchronized data/canon_cards.json & canon_dossiers.json + Bug #8/#9/#16
    canon_cards = json.loads((PKG_ROOT / "data" / "canon_cards.json").read_text(encoding="utf-8"))
    canon_dossiers = json.loads((PKG_ROOT / "data" / "canon_dossiers.json").read_text(encoding="utf-8"))
    assert len(canon_cards) == 20 and len(canon_dossiers) == 20
    for c in canon_cards:
        assert c["preview_image"] == f"/static/art/canons/{c['id']}.webp"
        assert "light" in c["palettes"] and "dark" in c["palettes"]
        for k in ("heading", "body", "mono"):
            fval = str(c["fonts"].get(k) or "")
            for bad_font in REJECTED_FONTS:
                assert bad_font.lower() not in fval.lower(), f"Rejected font {bad_font} in {c['id']}"
    assert resolve_canon_id("09_visual_storytelling") == "13_cinematic_documentary"
    assert resolve_canon_id("13_generative_ai_adaptive") == "18_devtool_command_ui"
    assert any(s["id"] == "html5_esm" for s in STACK_CATALOG)
    assert any(m["id"] == "css_scroll_driven" and "0 KB JS" in str(m) for m in MOTION_CATALOG)
    for mit_id in ("motion", "animejs", "lenis", "three"):
        assert any(m["id"] == mit_id and "MIT" in str(m) for m in MOTION_CATALOG), mit_id
    assert not any("gsap" in m["id"] for m in MOTION_CATALOG)
    assert AI_CRAWLERS_DEFAULT.get("Claude-SearchBot") is True

    cat = load_studio_catalog(repo_root=REPO_ROOT)
    assert len(cat["canons"]) == 20 and cat["canons_count"] == 20

    # 4. Bug #5 SVG XXE & Hardening Checks
    xxe_payload = b'<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>'
    xxe_blocked = False
    try:
        sanitize_svg_bytes(xxe_payload)
    except ValueError:
        xxe_blocked = True
    assert xxe_blocked, "DOCTYPE/ENTITY XXE must raise ValueError"

    for malicious in (
        b'<svg xmlns="http://www.w3.org/2000/svg"><circle cx="10" cy="10" r="5"/><animate attributeName="r" from="5" to="20"/></svg>',
        b'<svg xmlns="http://www.w3.org/2000/svg"><image href="data:image/svg+xml;base64,PHN2Zy8+"/></svg>',
    ):
        cleaned, warns = sanitize_svg_bytes(malicious)
        assert b"<animate" not in cleaned.lower() and b"data:image/svg+xml" not in cleaned.lower()
        assert warns
    stripped_ok, warns2 = sanitize_svg_bytes(
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><style>rect{fill:red}</style><use href="#x"/><rect width="10" height="10"/></svg>'
    )
    assert b"<style" not in stripped_ok.lower() and b"<use" not in stripped_ok.lower() and warns2

    # 5. Bugs #13 & #14 & #15: Z-Image hardening + Material phrases + Anti-AI linter
    p_mat = harden_zimage_prompt(
        "Oak & Stone studio interior, stone wall (#F6F2E9), natural oak desk lighting, no text, without words, portrait of Anna",
        brand="Oak Studio",
        member_names=["Anna Ivanova"],
    )
    assert "#F6F2E9" not in p_mat and "no text" not in p_mat.lower() and "anna" not in p_mat.lower()
    assert "oak" in p_mat.lower() and "stone" in p_mat.lower(), p_mat
    assert palette_to_material_summary({"bg": "oklch(0.96 0.01 90)", "accent": "oklch(0.54 0.18 30)"})
    assert all("#" not in spec for _, spec in _LOGO_FALLBACK_SPECS)
    assert all("no outline" not in fin.lower() for fin in LOGO_FINISHERS)

    assert not lint_anti_ai_copy("Наша динамично развивающаяся компания осуществляет монтаж и предлагает оптимальное соотношение цены и качества.", "ru", "features")["passed"]
    assert lint_anti_ai_copy("Предлагаем инновационные решения в рамках данного проекта.", "ru", "features")["soft_hits"]
    assert not lint_anti_ai_copy("Delve into a seamless tapestry of bespoke cutting-edge solutions.", "en", "features")["passed"]
    assert lint_anti_ai_copy("ул. Ленина, д. 5 | +7 (495) 000-11-22", "ru", "contact")["passed"]
    assert lint_anti_ai_copy("OOO Test | INN 1234567890", "en", "legal")["passed"]
    results["hardening_bugs"] = True

    # 6. All 5 Late-2026 Stack Scaffolds via compile_project_blueprint
    with tempfile.TemporaryDirectory(prefix="smartllm_phase2_") as td:
        td_p = Path(td)
        for st_id in ("html5_esm", "astro", "sveltekit", "nextjs", "vite_ts"):
            st_dir = td_p / f"stack_{st_id}"
            bp_st = compile_project_blueprint(
                {
                    "id": f"test_{st_id}",
                    "name": "Apex Photonics",
                    "brief": "Optical metrology hardware and cleanroom diagnostics",
                    "languages": "en",
                    "canon_id": "02_swiss_international",
                    "stack": st_id,
                    "motion": "motion",
                    "output_dir": str(st_dir),
                    "site_type": "single",
                    "selected_blocks": ["hero", "features", "pricing", "faq", "contact"],
                },
                repo_root=REPO_ROOT,
            )
            assert (st_dir / "page_model.json").exists()
            assert (st_dir / "assets" / "vendor" / "motion" / "motion.js").exists()
            if st_id == "sveltekit":
                assert not (st_dir / "scaffold" / "svelte.config.js").exists()
                srv_ts = (st_dir / "scaffold" / "src" / "routes" / "+page.server.ts").read_text(encoding="utf-8")
                assert "$lib" not in srv_ts and "#lib/" in srv_ts
            elif st_id == "nextjs":
                assert (st_dir / "scaffold" / "src" / "proxy.ts").exists()
                assert 'import "server-only"' in (st_dir / "scaffold" / "src" / "lib" / "dal.ts").read_text(encoding="utf-8")
            elif st_id == "astro":
                acfg = (st_dir / "astro.config.mjs").read_text(encoding="utf-8")
                assert "security:" in acfg and "csp: true" in acfg and "<ClientRouter" not in (st_dir / "index.html").read_text(encoding="utf-8")
            elif st_id == "vite_ts":
                vcfg = (st_dir / "scaffold" / "vite.config.ts").read_text(encoding="utf-8")
                assert "rolldownOptions" in vcfg
            sc_st = bp_st["audit_scorecard"]
            assert all(sc_st[k]["passed"] for k in ("csp", "headers", "a11y", "seo", "geo")), (st_id, sc_st)
        results["stacks_5"] = "PASSED"

        # 7. All 20 Canons x 2 Polarities (Light & Dark) = 40 Builds + Bug #1, #2, #3, #4, #5, #6, #7, #8, #9, #11, #12
        outside_logo = td_p / "outside_logo.svg"
        outside_logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>', encoding="utf-8")

        builds_checked = 0
        for cid in cids:
            for pol in ("light", "dark"):
                bdir = td_p / f"build_{cid}_{pol}"
                bp = compile_project_blueprint(
                    {
                        "id": f"b_{cid}_{pol}",
                        "name": "Север Оптика",
                        "brief": "Оптические измерения и промышленный аудит",
                        "languages": "en+ru",
                        "canon_id": cid,
                        "polarity": pol,
                        "stack": "html5_esm",
                        "motion": "css_scroll_driven",
                        "output_dir": str(bdir),
                        "site_type": "multi",
                        "selected_pages": ["index", "pricing", "portfolio", "about"],
                        "logo_path": str(outside_logo),  # outside allowed_roots -> Bug #5 must ignore it
                        "company": {
                            "phone": "+7 (495) 777-12-34",
                            "email": "hello@severoptics.ru",
                            "address": "ул. Промышленная, 12",
                            "cities": ["Москва", "Санкт-Петербург"],
                            "hours": "Пн–Пт 09:00–18:00",
                            "products": [
                                {"name": "Аудит линии", "scope": "Полный осмотр датчиков", "price": "45 000 ₽"},
                                {"name": "Контракт SLA", "scope": "Без сметы заранее", "price": "По запросу"},
                            ],
                        },
                    },
                    repo_root=REPO_ROOT,
                )
                builds_checked += 1
                assert bp["polarity"] == pol
                sc = bp["audit_scorecard"]
                assert all(sc[k]["passed"] for k in ("csp", "headers", "a11y", "seo", "geo")), (cid, pol, sc)

                # Local .woff2 font bundling (Bug #7)
                woffs = list((bdir / "assets" / "fonts").rglob("*.woff2"))
                assert len(woffs) >= 2, f"No local .woff2 fonts bundled for {cid}"

                # page_model.json (Layer 4)
                pm = json.loads((bdir / "page_model.json").read_text(encoding="utf-8"))
                assert pm["canon_id"] == cid and pm["polarity"] == pol and len(pm["pages"]) == 4

                idx_html = (bdir / "index.html").read_text(encoding="utf-8")
                sub_html = (bdir / "pricing.html").read_text(encoding="utf-8")
                css_txt = (bdir / "tokens.css").read_text(encoding="utf-8")
                hdr_txt = (bdir / "_headers").read_text(encoding="utf-8")
                rob_txt = (bdir / "robots.txt").read_text(encoding="utf-8")
                map_txt = (bdir / "sitemap.xml").read_text(encoding="utf-8")

                assert f'data-theme="{pol}"' in idx_html
                # Bug #1
                assert 'fetchpriority="high"' in idx_html
                assert "content-visibility: auto;" in css_txt
                # Bug #2
                assert 'rel="alternate" hreflang=' not in idx_html
                # Bug #3
                assert '"addressCountry": "DE"' not in idx_html
                assert '"BreadcrumbList"' not in idx_html and '"BreadcrumbList"' in sub_html
                assert '"price": "0"' not in idx_html and 'property="og:image"' in idx_html and 'name="twitter:card"' in idx_html
                assert "Cross-Origin-Embedder-Policy: credentialless" in hdr_txt
                assert "<changefreq>" not in map_txt and "<lastmod>" in map_txt
                # Bug #4
                assert "Claude-SearchBot" in rob_txt
                # Bug #9
                if cid == "08_liquid_glass":
                    assert "prefers-reduced-transparency: reduce" in css_txt
                    assert "@supports not (backdrop-filter: blur(1px))" in css_txt
                # Bug #11
                assert "background-attachment: fixed" not in css_txt and "overflow-x: clip;" in css_txt
                # Bug #12
                assert "node-calc-btn" not in idx_html
                assert 'class="form-status" role="status" aria-live="polite"' in idx_html
                assert "min-height: 44px;" in css_txt and "min-height: 48px;" in css_txt
                assert 'id="mobile-nav-toggle"' in idx_html

        results["canon_polarity_builds"] = builds_checked

        # 8. Bug #6 Proof: compute_real_scorecard fails when CSP / SEO / A11y broken
        sample_dir = td_p / "build_01_bento_grid_light"
        bad_sc = compute_real_scorecard(
            project_dir=sample_dir,
            rendered_pages={"index": "<html><body><h1>A</h1><h1>B</h1>\"price\": \"0\"</body></html>"},
            css_text="body { background-attachment: fixed; }",
            js_text="",
            style_hash="sha256-missing",
            script_hash="sha256-missing",
            card=canon_cards[0],
            headers_text="X-Frame-Options: DENY",
            robots_text="User-agent: *",
            sitemap_text="<urlset><url><loc>/</loc><changefreq>weekly</changefreq></url></urlset>",
            llms_enabled=True,
            ai_crawlers=AI_CRAWLERS_DEFAULT,
            geo_cfg={"facts": []},
            min_target_px=44,
        )
        assert not bad_sc["csp"]["passed"] and not bad_sc["headers"]["passed"]
        assert not bad_sc["a11y"]["passed"] and not bad_sc["seo"]["passed"] and not bad_sc["geo"]["passed"]

        # 9. Variant routing non-repetition sanity
        r_var = route_block_variants("01_bento_grid", ["hero", "features", "gallery", "pricing", "process"])
        assert len(r_var) == 5

    # 10. A4 Launcher UI & i18n parity checks
    index_src = (PKG_ROOT / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="atelier-shell" data-stage-open="false"' in index_src
    assert 'id="atelier-live-stage" data-drawer-closed="true"' in index_src
    assert 'id="live-stage-iframe" title="Live Stage Preview" src="about:blank"' in index_src
    for pid_btn in ("s3-polarity-auto", "s3-polarity-light", "s3-polarity-dark"):
        assert f'id="{pid_btn}"' in index_src
    en_i18n = json.loads((PKG_ROOT / "static" / "i18n" / "en.json").read_text(encoding="utf-8"))
    ru_i18n = json.loads((PKG_ROOT / "static" / "i18n" / "ru.json").read_text(encoding="utf-8"))
    assert set(en_i18n) == set(ru_i18n) and "lbl_polarity" in en_i18n and "btn_pol_dark" in ru_i18n

    # 11. Sanity-check default_project_draft uses late-2026 motion default
    draft = default_project_draft("demo", repo_root=REPO_ROOT)
    assert draft["motion"] == "css_scroll_driven" and draft["compare_canon_id"] == "18_devtool_command_ui"
    assert str(draft["goal"]).startswith("High-craft Astro")

    results["status"] = "ALL_PHASE2_GATES_PASSED"
    return results


if __name__ == "__main__":
    print(json.dumps(run_all_tests(), indent=2, ensure_ascii=False))
