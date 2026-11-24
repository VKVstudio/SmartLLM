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

from smartllm_studio.canon_layouts import LAYOUTS as _CANON_LAYOUTS  # noqa: E402  canons with their own CSS (0.0.7)
from smartllm_studio.blueprint import compile_project_blueprint, default_project_draft  # noqa: E402
from smartllm_studio.catalog import AI_CRAWLERS_DEFAULT, MOTION_CATALOG, STACK_CATALOG, load_studio_catalog  # noqa: E402
from smartllm_studio.kb_loader import (  # noqa: E402
    compute_real_scorecard,
    get_slot_recipes,
    harden_zimage_prompt,
    lint_anti_ai_copy,
    list_canon_ids,
    palette_to_material_summary,
    resolve_canon_id,
    route_block_variants,
)
from smartllm_studio.orchestrator import LOGO_FINISHERS, _LOGO_FALLBACK_SPECS, ProjectOrchestrator  # noqa: E402
from smartllm_studio.os_compat import CrossPlatformFileLock  # noqa: E402
from smartllm_studio.pipeline import _enforce_portrait_gender, _sanitize_zimage_prompt  # noqa: E402
from smartllm_studio.sanitizer import sanitize_svg_bytes  # noqa: E402
from smartllm_studio.server import create_studio_server  # noqa: E402


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
                    assert cid in _CANON_LAYOUTS or "@supports not (backdrop-filter: blur(1px))" in css_txt  # legacy shared-CSS specific
                # Bug #11
                assert "background-attachment: fixed" not in css_txt and "overflow-x: clip;" in css_txt
                assert cid in _CANON_LAYOUTS or "html { scroll-padding-top: 4.75rem; font-size: 16px; scroll-behavior: smooth; }" in css_txt  # legacy shared-CSS specific
                assert cid in _CANON_LAYOUTS or ":is(.spec-card," in css_txt  # legacy shared-CSS specific
                assert ".faq-item:hover" not in css_txt and ".faq-item:active" not in css_txt and ".faq-item::before" not in css_txt
                assert '[data-solid-ui="true"] .spec-card,' not in css_txt
                # Bug #12
                assert "node-calc-btn" not in idx_html
                assert 'class="form-status" role="status" aria-live="polite"' in idx_html
                assert "min-height: 44px;" in css_txt and (cid in _CANON_LAYOUTS or "min-height: 48px;" in css_txt)
                assert 'id="mobile-nav-toggle"' in idx_html

        results["canon_polarity_builds"] = builds_checked

        # 8. Bug #6 Proof: compute_real_scorecard fails when CSP / SEO / A11y broken
        sample_dir = td_p / "build_01_bento_grid_light"
        sample_js_txt = (sample_dir / "app.js").read_text(encoding="utf-8")
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

    # 12. Live-QA visual & review regressions (desktop nav-toggle cascade, -free artifact, neutral scene tones, review current text)
    p_clean_free = harden_zimage_prompt("Architectural concrete wall, text-free, logo-free, 50mm lens")
    assert "-free" not in p_clean_free.lower(), p_clean_free
    neutral_dark = palette_to_material_summary(canon_cards[0]["palettes"]["dark"], keys=("bg", "surface"))
    assert neutral_dark and "violet" not in neutral_dark.lower() and "emerald" not in neutral_dark.lower(), neutral_dark
    pipe_src = (PKG_ROOT / "pipeline.py").read_text(encoding="utf-8")
    assert "(current):" in pipe_src and "keys=(\"bg\", \"surface\")" in pipe_src
    assert ".btn.nav-toggle { display: none;" in css_txt and css_txt.index(".btn.nav-toggle { display: none;") > css_txt.index(".btn {")
    assert "main, .hero-shell, .section-block, .price-table-wrap { min-width: 0; max-width: 100%; }" in css_txt
    assert "revealVisible" in sample_js_txt and "setTimeout(revealVisible" in sample_js_txt
    assert sample_js_txt.index("revealVisible();") < sample_js_txt.index('root.classList.add("js");')

    # 13. Live-QA Z-Image hygiene, lock thread safety, and Downloads-only ZIP export regressions
    import io as _io_mod
    import threading as _thr_mod
    import urllib.request as _url_req
    import zipfile as _zip_mod

    lut_dump = json.dumps(get_slot_recipes()["oklch_material_palette_lut"], ensure_ascii=False).lower()
    for bad_prop in ("eucalyptus", "pistachio", "apricot", "aubergine"):
        assert bad_prop not in lut_dump, f"Prop trap {bad_prop!r} still in oklch_material_palette_lut"

    clean_stage = harden_zimage_prompt("Sculptural beam inside museum-poster stage")
    assert "museum- " not in clean_stage.lower() and "poster" not in clean_stage.lower(), clean_stage

    clean_no_p = harden_zimage_prompt("Studio workspace, no close-up portraits, crisp lighting")
    assert "portrait" not in clean_no_p.lower() and "close-up" not in clean_no_p.lower(), clean_no_p

    clean_dep = harden_zimage_prompt("Editorial photo of light installation, 50mm lens, depicting light installation")
    assert "depicting" not in clean_dep.lower(), clean_dep

    clean_opt = harden_zimage_prompt("Macro detail of optical diffuser and LED module, 50mm lens")
    assert "50mm lens" not in clean_opt.lower(), clean_opt

    p_once = _enforce_portrait_gender("Vertical 3:4 high-contrast studio portrait of a 29-year-old woman", "female")
    assert p_once.count("Vertical 3:4") == 1 and "headroom" in p_once.lower(), p_once

    lock_errors: list[str] = []
    with tempfile.TemporaryDirectory() as lock_td:
        lock_obj = CrossPlatformFileLock(Path(lock_td) / "gpu.lock")

        def _lock_worker() -> None:
            try:
                for _ in range(15):
                    if lock_obj.acquire():
                        lock_obj.release()
            except Exception as exc:
                lock_errors.append(repr(exc))

        threads = [_thr_mod.Thread(target=_lock_worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
        assert not lock_errors, f"Concurrent CrossPlatformFileLock errors: {lock_errors}"

        srv_exp, state_exp = create_studio_server(
            host="127.0.0.1",
            port=0,
            repo_root=REPO_ROOT,
            projects_root_override=Path(lock_td) / "projects",
            lock_path_override=Path(lock_td) / "srv_gpu.lock",
        )
        exp_port = srv_exp.server_address[1]
        exp_thr = _thr_mod.Thread(target=srv_exp.serve_forever, daemon=True)
        exp_thr.start()
        try:
            proj_dir_exp = state_exp.project_dir("default")
            for extra_payload in ({}, {"target_dir": str(proj_dir_exp)}):
                req_p = _url_req.Request(
                    f"http://127.0.0.1:{exp_port}/api/export/default",
                    data=json.dumps({"as_zip": True, **extra_payload}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with _url_req.urlopen(req_p, timeout=5.0) as r_post:
                    exp_res = json.loads(r_post.read().decode("utf-8"))
                exp_zip_path = Path(exp_res["path"]).resolve()
                assert not exp_zip_path.is_relative_to(proj_dir_exp.resolve()), f"ZIP polluted project_dir: {exp_zip_path}"
                assert exp_zip_path.is_relative_to(state_exp.exports_dir.resolve()), exp_zip_path
                assert not list(proj_dir_exp.glob("*.zip")), list(proj_dir_exp.glob("*.zip"))
                with _url_req.urlopen(f"http://127.0.0.1:{exp_port}{exp_res['download_url']}", timeout=5.0) as r_dl:
                    assert r_dl.status == 200
                    assert "attachment;" in (r_dl.headers.get("Content-Disposition") or "")
                    zbytes = r_dl.read()
                with _zip_mod.ZipFile(_io_mod.BytesIO(zbytes), "r") as zf_dl:
                    assert "index.html" in zf_dl.namelist()
        finally:
            srv_exp.shutdown()
            srv_exp.server_close()

    # 14. v0.0.5-beta Upgrade Regressions: MIT Motion wiring, 20-canon signature CSS, faithful logos, luminous domain, copy truth
    from smartllm_studio.orchestrator import _default_logo_variant_prompts
    from smartllm_studio.pipeline import _is_luminous_domain, _sync_page_copy_to_foundation
    from smartllm_studio.templates_engine import normalize_motion_id

    orch_src = (PKG_ROOT / "orchestrator.py").read_text(encoding="utf-8")
    assert "Koenigsberg" not in orch_src and "Prussian Gothic" not in orch_src
    ru_logo_prompts = _default_logo_variant_prompts(
        "Абажур Labs", "Студия световых решений", "красный логотип закольцован в четырехугольник", "ru"
    )
    assert len(ru_logo_prompts) == 6
    assert all("crimson" in p.lower() and "quadrilateral" in p.lower() for p in ru_logo_prompts), ru_logo_prompts[0]

    assert _is_luminous_domain("Абажур Labs", "Студия световых решений, инсталляции")
    assert _is_luminous_domain("Lumen Atelier", "Bespoke architectural lighting design")
    assert not _is_luminous_domain("SoundCraft", "Acoustic timber panels and diffusers")

    assert normalize_motion_id("gsap_scrolltrigger") == "motion"
    assert normalize_motion_id("animejs") == "animejs"
    assert normalize_motion_id("css_scroll_driven") == "css_scroll_driven"

    synced_sub = _sync_page_copy_to_foundation(
        "portfolio",
        {
            "values": "Product: Точная сборка | Team: Инженеры | Clients: Прозрачная смета",
            "manifesto": "Свет как материал | Инженерная светотехника",
        },
        {"tagline": "Свет как материал", "positioning": "Инженерная светотехника"},
        "ru",
        set(),
    )
    assert "Продукт — Точная сборка" in synced_sub["values"] and "Product:" not in synced_sub["values"], synced_sub["values"]
    assert synced_sub["manifesto"] != "Свет как материал | Инженерная светотехника", synced_sub["manifesto"]

    with tempfile.TemporaryDirectory(prefix="smartllm_motion_v005_") as mtd:
        mtd_p = Path(mtd)
        for m_in, expected_scripts in (
            ("gsap_scrolltrigger", ("assets/vendor/lenis/lenis.min.js", "assets/vendor/motion/motion.js")),
            ("animejs", ("assets/vendor/lenis/lenis.min.js", "assets/vendor/animejs/anime.umd.min.js")),
        ):
            mdir = mtd_p / f"m_{m_in}"
            bp_m = compile_project_blueprint(
                {
                    "id": f"m_{m_in}",
                    "name": "Абажур Labs",
                    "brief": "Студия архитектурного освещения",
                    "languages": "en+ru",
                    "canon_id": "10_industrial_tactile",
                    "polarity": "light",
                    "motion": m_in,
                    "output_dir": str(mdir),
                    "site_type": "single",
                    "selected_blocks": ["hero", "features", "stats", "pricing", "testimonials", "faq", "cta", "contact"],
                },
                repo_root=REPO_ROOT,
            )
            sc_m = bp_m["audit_scorecard"]
            assert all(sc_m[k]["passed"] for k in ("csp", "headers", "a11y", "seo", "geo")), (m_in, sc_m)
            html_m = (mdir / "index.html").read_text(encoding="utf-8")
            css_m = (mdir / "tokens.css").read_text(encoding="utf-8")
            assert len(html_m.encode("utf-8")) < 200_000
            assert 'data-canon="10_industrial_tactile"' in html_m
            assert "radial-gradient(circle, var(--border-control)" in css_m
            for rel_s in expected_scripts:
                assert (mdir / rel_s).exists(), rel_s
                assert f'<script src="{rel_s}" defer></script>' in html_m

    app_js_src = (PKG_ROOT / "static" / "app.js").read_text(encoding="utf-8")
    studio_css_src = (PKG_ROOT / "static" / "styles.css").read_text(encoding="utf-8")
    assert 'id="s3-motion-select"' in index_src and 'id="exp-motion-select"' in index_src
    assert set(en_i18n) == set(ru_i18n) and "lbl_motion_engine" in en_i18n and "lbl_exp_motion" in ru_i18n
    assert "Object.assign({}, store.company || {}" in app_js_src
    assert "logo_prompt:" in app_js_src and "s2-logo-prompt" in app_js_src
    assert "flex-wrap: wrap;" in studio_css_src and ".canon-card-head strong" in studio_css_src

    # 15. Folder Browser Fallback, 5 Animated Landing Presets, Cohesive Starter & Tactile/Scrolly Architecture
    from smartllm_studio.catalog import CANON_MOTION_DEFAULTS, LANDING_PRESET_CATALOG
    from smartllm_studio.orchestrator import generate_random_starter_template
    from smartllm_studio.os_compat import create_directory_safe, list_directory_entries

    cat_v5 = load_studio_catalog(REPO_ROOT)
    assert cat_v5["canons_count"] == 20 and len(cat_v5["canons"]) == 20
    assert len(cat_v5["landing_presets"]) == 5 and len(LANDING_PRESET_CATALOG) == 5
    by_id = {c["id"]: c for c in cat_v5["canons"]}
    for static_cid in (
        "02_swiss_international",
        "03_editorial_magazine",
        "04_hyper_minimal_speed",
        "17_fintech_institutional",
        "18_devtool_command_ui",
        "19_calm_human_accessible",
    ):
        assert by_id[static_cid].get("supports_animation") is False, static_cid
        assert CANON_MOTION_DEFAULTS[static_cid]["default_motion"] == "reduced_motion_instant"
    for anim_cid in (
        "01_bento_grid",
        "05_kinetic_typography",
        "06_neo_brutalism",
        "10_industrial_tactile",
        "14_spatial_3d_showcase",
        "20_maximalist_collage_pop",
    ):
        assert by_id[anim_cid].get("supports_animation") is True, anim_cid

    with tempfile.TemporaryDirectory(prefix="smartllm_fs_starter_") as ftd:
        ftd_p = Path(ftd)
        created_dir = create_directory_safe(str(ftd_p), "demo_sub")
        assert Path(created_dir["path"]).is_dir() and created_dir["created"] is True
        listing = list_directory_entries(str(ftd_p))
        assert any(d["name"] == "demo_sub" for d in listing["dirs"]), listing

        tpl = generate_random_starter_template(None, lang="ru", use_llm=False)
        valid_canon_ids = {c["id"] for c in cat_v5["canons"]}
        valid_preset_ids = {p["id"] for p in cat_v5["landing_presets"]}
        assert tpl["canon_id"] in valid_canon_ids, tpl
        assert tpl["landing_preset"] in valid_preset_ids, tpl
        assert tpl["motion"] in {"motion", "animejs", "css_scroll_driven", "lenis", "three", "reduced_motion_instant"}
        assert tpl["name"] and tpl["brief"] and tpl["logo_prompt"]
        assert tpl["page_block_prompts"] == {} and tpl["block_prompts"] == {}
        assert re.search(r"[А-Яа-яЁё]", tpl["brief"]) and re.search(r"[А-Яа-яЁё]", tpl["company"]["tagline"])
        assert "starter_" in Path(tpl["output_dir"]).name

        scrolly_dir = ftd_p / "scrolly_tactile"
        bp_sc = compile_project_blueprint(
            {
                "id": "scrolly_tactile",
                "name": "Волна-08 Акустика",
                "brief": "Модульные полевые рекордеры и тактильные микшеры в алюминиевом корпусе.",
                "languages": "ru",
                "canon_id": "10_industrial_tactile",
                "polarity": "light",
                "landing_preset": "gsap_scrollytelling",
                "motion": "motion",
                "output_dir": str(scrolly_dir),
                "site_type": "single",
                "selected_blocks": ["hero", "features", "stats", "pricing", "cta", "contact"],
            },
            repo_root=REPO_ROOT,
        )
        assert bp_sc["landing_preset"] == "gsap_scrollytelling"
        sc_html = (scrolly_dir / "index.html").read_text(encoding="utf-8")
        assert 'data-landing="gsap_scrollytelling"' in sc_html
        assert "hw-console-bar" in sc_html and "hw-screen-bezel" in sc_html
        assert "scrolly-stage" in sc_html and "scrolly-pin" in sc_html
        assert 'class="marquee"' not in sc_html
        assert "assets/vendor/lenis/lenis.min.js" in sc_html
        assert "assets/vendor/motion/motion.js" in sc_html
        assert " style=" not in sc_html, "CSP style-src-attr 'none' violation: inline style attribute found"

    assert 'id="modal-folder-picker"' in index_src and 'id="starter-preloader"' in index_src
    assert 'id="s3-landing-presets"' in index_src and 'id="btn-topbar-random-template"' in index_src
    assert 'id="s3-static-canon-note"' in index_src and 'id="exp-anim-controls"' in index_src
    assert index_src.index('id="s3-canon-gallery"') < index_src.index('id="s3-animation-section"') < index_src.index('id="s3-motion-select"')
    assert "setStageOpen(true)" not in app_js_src
    assert "runRandomStarterTemplate" in app_js_src and "openFolderPickerModal" in app_js_src and "setLandingPreset" in app_js_src

    # 16. v0.0.6 Style-Filtered Stacks/Motions & Russian Consistency Fixes
    from smartllm_studio.kb_loader import harden_zimage_prompt as _hzp
    from smartllm_studio.pages import normalize_hours_for_lang
    from smartllm_studio.pipeline import _sync_page_copy_to_foundation

    valid_stack_ids = {s["id"] for s in cat_v5["stacks"]}
    valid_motion_ids = {m["id"] for m in cat_v5["motions"]}
    three_canons = []
    for cid_chk, meta_chk in CANON_MOTION_DEFAULTS.items():
        c_cat = by_id[cid_chk]
        for req_k in ("default_stack", "allowed_stacks", "allowed_motions", "allowed_landing_presets"):
            assert c_cat.get(req_k), (cid_chk, req_k)
        assert c_cat["default_stack"] in c_cat["allowed_stacks"] and set(c_cat["allowed_stacks"]) <= valid_stack_ids, cid_chk
        assert c_cat["default_motion"] in c_cat["allowed_motions"] and set(c_cat["allowed_motions"]) <= valid_motion_ids, cid_chk
        assert c_cat["default_landing_preset"] in c_cat["allowed_landing_presets"] and set(c_cat["allowed_landing_presets"]) <= valid_preset_ids, cid_chk
        if "three" in c_cat["allowed_motions"]:
            three_canons.append(cid_chk)
    assert three_canons == ["14_spatial_3d_showcase"], three_canons
    assert set(by_id["15_organic_biophilic_eco"]["allowed_stacks"]) <= {"html5_esm", "astro"}
    assert "three" not in by_id["15_organic_biophilic_eco"]["allowed_motions"]
    assert "lenis" not in by_id["13_cinematic_documentary"]["allowed_motions"]
    assert "kinetic_showreel" not in by_id["01_bento_grid"]["allowed_landing_presets"]

    assert 'id="s3-stack-select"' in index_src and 'id="exp-stack-select"' in index_src
    assert "v=0.0.6-r5" in index_src and "</script></script>" not in index_src and "renderStackSelects" in app_js_src
    assert 'setPolarity("auto", false);' in app_js_src and "setStageOpen(true)" not in app_js_src

    from smartllm_studio.pipeline import _pick_team_personas
    from smartllm_studio.server import StudioState

    slots_cmp = [
        {"name": "Иван Соколов", "role": "Инженер", "gender": "male"},
        {"name": "Анна Петрова", "role": "Дизайнер", "gender": "female"},
        {"name": "Дмитрий Волков", "role": "Монтаж", "gender": "male"},
        {"name": "Мария Лебедева", "role": "Проекты", "gender": "female"},
    ]
    p_akustika = _pick_team_personas(slots_cmp, "Акустическая Керамика")
    p_tok = _pick_team_personas(slots_cmp, "Городской Ток")
    assert len(set(p_akustika)) == 4 and len(set(p_tok)) == 4
    assert p_akustika != p_tok, "Combinatorial portrait personas must not collide across brands"

    with tempfile.TemporaryDirectory(prefix="smartllm_iso_prev_") as itd:
        itd_p = Path(itd)
        built_site = itd_p / "built_site"
        built_site.mkdir(parents=True, exist_ok=True)
        sentinel_html = "<!doctype html><html><body>BUILT_SENTINEL</body></html>"
        (built_site / "index.html").write_text(sentinel_html, encoding="utf-8")
        st_iso = StudioState(repo_root=REPO_ROOT, projects_root_override=itd_p / "projects")
        saved_iso = st_iso.save_project("starter", {"name": "New Preview Brand", "canon_id": "13_cinematic_documentary", "output_dir": str(built_site)})
        bp_iso, _ = st_iso.compile_isolated_preview("starter", saved_iso)
        assert "_live_preview" in str(bp_iso["project_dir"])
        assert (built_site / "index.html").read_text(encoding="utf-8") == sentinel_html

    assert normalize_hours_for_lang("Mon-Fri 10:00-19:00", "ru") == "Пн–Пт 10:00–19:00"
    assert not _hzp("Wide concrete studio room. visual").lower().endswith("visual")
    synced_test = _sync_page_copy_to_foundation(
        "pricing",
        {
            "manifesto": "Продукт — общий стандарт | Коротко о тарифах",
            "testimonials": "Иван Соколов, ведущий инженер — снизили эхо на 15 дБ | Сергей Орлов, клиент — точный замер и монтаж",
            "contact": "+7 495 111-22-33 | a@b.ru | ул. Мира, 5 | Mon-Fri 10:00-19:00",
        },
        {
            "tagline": "Точная акустика",
            "positioning": "Глиняные панели под ключ.",
            "products": [{"name": "Стандарт", "scope": "монтаж", "price": "120 000 ₽"}],
            "features": [{"title": "Дизайн", "detail": "Подбор"}, {"title": "Монтаж", "detail": "Сборка"}, {"title": "Тесты", "detail": "Замеры"}],
            "stats": [{"value": "48", "label": "проектов"}, {"value": "1200 м²", "label": "панелей"}, {"value": "96%", "label": "точность"}],
            "team": [{"name": "Иван Соколов", "role": "ведущий инженер"}],
        },
        "ru",
        set(),
        canonical_team=[{"name": "Иван Соколов", "role": "ведущий инженер"}],
    )
    assert not synced_test["manifesto"].startswith("Продукт")
    assert "Иван Соколов" not in synced_test["testimonials"]
    assert "Сергей Орлов" in synced_test["testimonials"]
    assert "Пн–Пт 10:00–19:00" in synced_test["contact"] and "Mon-Fri" not in synced_test["contact"]

    with tempfile.TemporaryDirectory(prefix="smartllm_ru_consistency_") as rtd:
        rtd_p = Path(rtd)
        bp_ru = compile_project_blueprint(
            {
                "id": "ru_check",
                "name": "Акустика Глины",
                "brief": "Глиняные панели для точной акустики помещений и студий.",
                "languages": "ru",
                "canon_id": "10_industrial_tactile",
                "polarity": "light",
                "landing_preset": "gsap_scrollytelling",
                "motion": "motion",
                "company": {
                    "tagline": "Глиняные панели для точной акустики",
                    "positioning": "Глиняные панели под ключ.",
                    "hours": "Mon-Fri 10:00-19:00",
                    "phone": "+7 495 123-45-67",
                    "email": "hello@example.ru",
                    "address": "ул. Звучания, 12, Москва",
                    "history": {"founded": 2017, "milestones": ["2017 — основана компания", "2023 — расширен цех"]},
                },
                "page_block_prompts": {
                    "index": {
                        "features": "Дизайн панелей — разработка акустических и визуальных решений | Монтаж — инженерная установка панелей | Акустические тесты — замеры до и после",
                        "process": "01 Аудит помещения — замеры акустики | 02 Дизайн — проект раскладки | 03 Монтаж — установка панелей | 04 Тесты — финальный замер",
                    }
                },
                "output_dir": str(rtd_p),
                "site_type": "single",
                "selected_blocks": ["hero", "features", "process", "contact", "footer"],
            },
            repo_root=REPO_ROOT,
        )
        ru_html = (rtd_p / "index.html").read_text(encoding="utf-8")
        assert "Mon-Fri" not in ru_html and "Пн–Пт 10:00–19:00" in ru_html
        assert ">Company<" not in ru_html and ' logo"' not in ru_html and "Логотип Акустика Глины" in ru_html
        assert "<h3>01 Аудит" not in ru_html and "<h3>Аудит помещения</h3>" in ru_html
        assert "<h3>Дизайн панелей</h3><p>разработка акустических" in ru_html

    # 17. v0.0.6-r3: preview never touches a finished output_dir, crypto Z-Image seeds, canon -> CSS fidelity
    import difflib as _difflib
    import threading as _thr17
    import urllib.request as _url17

    orch_src = (PKG_ROOT / "orchestrator.py").read_text(encoding="utf-8")
    assert "sum(ord(c)" not in orch_src and "brand_seed_offset" not in orch_src
    assert '"seed": 42 +' not in orch_src and '"seed": 101,' not in orch_src and '"seed": 60 + g_idx' not in orch_src
    assert "secrets.SystemRandom().randrange" in orch_src and "zimage_seeds.json" in orch_src
    srv_src = (PKG_ROOT / "server.py").read_text(encoding="utf-8")
    assert srv_src.count("compile_project_blueprint(draft, repo_root=state.repo_root)") == 1, "only /api/export may compile into output_dir"
    with tempfile.TemporaryDirectory(prefix="smartllm_preview_iso_") as iso_td:
        iso_p = Path(iso_td)
        finished = iso_p / "finished_site"
        finished.mkdir(parents=True)
        (finished / "assets").mkdir()
        sentinel_html = "<!doctype html><title>FINISHED</title>"
        (finished / "index.html").write_text(sentinel_html, encoding="utf-8")
        (finished / "assets" / "brand-logo.png").write_bytes(b"FINISHED-LOGO")
        srv_i, state_i = create_studio_server(
            host="127.0.0.1", port=0, repo_root=REPO_ROOT,
            projects_root_override=iso_p / "projects", lock_path_override=iso_p / "gpu.lock",
        )
        port_i = srv_i.server_address[1]
        _thr17.Thread(target=srv_i.serve_forever, daemon=True).start()
        try:
            def _post17(path: str, body: dict) -> dict:
                rq = _url17.Request(f"http://127.0.0.1:{port_i}{path}", data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
                with _url17.urlopen(rq, timeout=30.0) as rr:
                    return json.loads(rr.read().decode("utf-8"))
            pv = _post17("/api/preview/starter", {"name": "Other Brand", "canon_id": "14_spatial_3d_showcase", "output_dir": str(finished)})
            assert "/preview/starter/" in pv["preview_url"], pv.get("preview_url")
            assert Path(pv["project_dir"]).resolve().is_relative_to((iso_p / "projects" / "_live_preview").resolve()), pv["project_dir"]
            logo_src = state_i.logo_batches_dir / "variant_1.png"
            logo_src.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (64, 64), (200, 40, 40)).save(logo_src)
            sel = _post17("/api/logo/select", {"project_id": "starter", "path": str(logo_src), "output_dir": str(finished)})
            assert sel["status"] == "selected" and "/preview/starter/" in sel["preview_url"]
            assert (finished / "index.html").read_text(encoding="utf-8") == sentinel_html, "preview overwrote finished index.html"
            assert (finished / "assets" / "brand-logo.png").read_bytes() == b"FINISHED-LOGO", "logo select overwrote finished logo"
            assert sorted(p.name for p in finished.iterdir()) == ["assets", "index.html"], list(finished.iterdir())
            assert state_i.load_project("starter")["selected_logo_path"] == str(logo_src.resolve())
            with _url17.urlopen(f"http://127.0.0.1:{port_i}{sel['preview_url']}", timeout=10.0) as r_iso:
                assert r_iso.status == 200 and b"Other Brand" in r_iso.read()
        finally:
            srv_i.shutdown()
            srv_i.server_close()

    with tempfile.TemporaryDirectory(prefix="smartllm_canon_css_") as ctd:
        css_by: dict[str, str] = {}
        html_by: dict[str, str] = {}
        for cid in ("05_kinetic_typography", "13_cinematic_documentary", "12_quiet_luxury_minimal"):
            od = Path(ctd) / cid
            compile_project_blueprint({"id": "cc", "name": "Same Brand", "brief": "Same brief for every canon.", "languages": "en", "canon_id": cid, "polarity": "auto", "output_dir": str(od)}, repo_root=REPO_ROOT)
            css_by[cid] = (od / "tokens.css").read_text(encoding="utf-8")
            html_by[cid] = (od / "index.html").read_text(encoding="utf-8")
            assert f'data-canon="{cid}"' in html_by[cid]
        keys = list(css_by)
        for a_i in range(len(keys)):
            for b_i in range(a_i + 1, len(keys)):
                ca, cb = css_by[keys[a_i]], css_by[keys[b_i]]
                ratio = _difflib.SequenceMatcher(None, ca.splitlines(), cb.splitlines()).ratio()
                assert ratio < 0.85, f"{keys[a_i]} vs {keys[b_i]} CSS too similar: {ratio:.3f}"
                root_a = re.search(r":root\s*\{[^}]*\}", ca).group(0)
                root_b = re.search(r":root\s*\{[^}]*\}", cb).group(0)
                assert root_a != root_b, f"identical :root tokens for {keys[a_i]} / {keys[b_i]}"
        results["canon_css_fidelity"] = "PASS"

    from smartllm_studio.orchestrator import generate_random_starter_template
    for _ in range(6):
        tpl_av = generate_random_starter_template(None, lang="en", use_llm=False, avoid_canons=["08_liquid_glass", "12_quiet_luxury_minimal"])
        assert tpl_av["canon_id"] not in ("08_liquid_glass", "12_quiet_luxury_minimal"), tpl_av["canon_id"]
    results["preview_isolation_and_seeds"] = "PASS"

    results["status"] = "ALL_PHASE2_GATES_PASSED"
    return results


if __name__ == "__main__":
    print(json.dumps(run_all_tests(), indent=2, ensure_ascii=False))
