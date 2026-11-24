"""Standalone-first ProjectDraft store, Blueprint Compiler & Zip/Folder Exporter (Opus Spec Q3, Q5, Q6)."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any
import zipfile

from . import __version__
from .adapters import get_rag_selector
from .catalog import AI_CRAWLERS_DEFAULT, CANON_MOTION_DEFAULTS
from .config import DEFAULT_REPO_ROOT, STUDIO_ROOT, discover_studio_paths
from .kb_loader import compute_real_scorecard, route_block_variants
from .pages import DEFAULT_PAGE_SLUGS, build_default_company, build_routes_from_pages, default_page_blocks, normalize_hours_for_lang, read_png_dimensions
from .rag import make_synthetic_png
from .sanitizer import ingest_brand_logo
from .templates_engine import (
    build_canon_theme_css,
    bundle_vendor_assets_for_canon,
    emit_stack_scaffold,
    normalize_motion_id,
    normalize_stack_id,
    write_page_model_json,
)


def sha256_csp(content: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(content.encode("utf-8")).digest()).decode("ascii")


def _safe_project_dir(raw: Any, default_dir: Path) -> Path:
    """Portable output_dir resolution: reject foreign-OS absolute paths (shared dual-boot drives)
    and unwritable/deleted folders, falling back to the per-project default directory."""
    s = str(raw or "").strip().strip("`\"'")
    if s:
        foreign_win = bool(re.match(r"^[A-Za-z]:[\\/]", s)) or s.startswith("\\\\")
        foreign_posix = s.startswith("/") and not s.startswith("//")
        # Windows driveless rooted paths ("\mnt\rescue\...", "/mnt/...") are foreign/ambiguous:
        # they silently resolve onto the current drive (D:\mnt\rescue\...) on dual-boot shares.
        driveless_rooted = s.startswith(("/", "\\")) and not foreign_win
        if (os.name != "nt" and foreign_win) or (os.name == "nt" and (foreign_posix or driveless_rooted)):
            s = ""
    if s:
        try:
            p = Path(s)
            if not p.is_absolute():
                p = default_dir.parent / p
            p = p.resolve()
            p.mkdir(parents=True, exist_ok=True)
            return p
        except OSError:
            pass
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir.resolve()


def default_project_draft(project_id: str = "default", repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or DEFAULT_REPO_ROOT).resolve()
    safe_id = "".join(c for c in str(project_id or "default") if c.isalnum() or c in ("-", "_")) or "default"
    projects_root = Path(discover_studio_paths(repo_root=root)["projects_root"])
    page_blocks = default_page_blocks(DEFAULT_PAGE_SLUGS)
    routes = build_routes_from_pages(DEFAULT_PAGE_SLUGS, page_blocks, "ru")
    company = build_default_company("Quartz-Field Atelier", "High-craft industrial design and acoustic engineering", "ru")
    if routes:
        routes[0]["copy_en"] = {"headline": "Modular Architectural Systems & Studio Craft", "subhead": "Precision digital flagships built with semantic clarity, accessible typography, and verified performance."}
        routes[0]["copy_ru"] = {"headline": "Модульная архитектура и инженерный дизайн", "subhead": "Точные цифровые решения с выверенной типографикой, высокой доступностью и подтверждённой скоростью работы."}
    return {
        "id": project_id,
        "revision": 1,
        "name": "Quartz-Field Atelier",
        "audience": "Principal systems engineers & industrial architects",
        "goal": "High-craft Astro 7.4 Islands landing page with CSS Scroll-Driven choreography and zero-swap telemetry.",
        "tone_formality": 75,
        "tone_energy": 65,
        "languages": "en+ru",
        "canon_id": "01_bento_grid",
        "polarity": "auto",
        "compare_canon_id": "18_devtool_command_ui",
        "stack": "astro",
        "motion": "css_scroll_driven",
        "landing_preset": "gsap_scrollytelling",
        "output_dir": str(projects_root / safe_id),
        "site_type": "multi",
        "selected_pages": list(DEFAULT_PAGE_SLUGS),
        "page_blocks": page_blocks,
        "company": company,
        "selected_blocks": [b for b in page_blocks.get("index", []) if b != "footer"],
        "logo": {
            "filename": "smartllm-logo.svg",
            "relpath": "assets/brand-logo.svg",
            "favicon_relpath": "assets/favicon.svg",
            "swatches": ["#0b0d12", "#151923", "#c084fc", "#e5b869", "#eceef3", "#4ade80"],
        },
        "zimage_direction": {
            "style_chip": "Architectural Orthographic",
            "mood": "High-Contrast Studio",
            "aspect_ratio": "16:9",
            "selected_variant": 0,
        },
        "routes": routes,
        "seo": {
            "base_url": "https://smartllm-studio.example.org",
            "title": "Quartz-Field Atelier — Zero-Swap Industrial Telemetry",
            "description": "Deterministic industrial telemetry and acoustic verification platform built with OKLCH AAA tokens and SHA-256 CSP.",
            "schema_type": "Organization",
            "llms_txt_enabled": True,
            "faqs": [
                {
                    "q": "How does the runtime guarantee zero disk swap?",
                    "a": "The combine executes strictly on 127.0.0.1 with locked MoE expert budgets and direct NVMe pread for PLE tables, keeping disk swap at 0 B.",
                },
                {
                    "q": "Who owns the generated website code and visual assets?",
                    "a": "You retain 100% ownership of all generated HTML, CSS, TypeScript, Astro islands, and Z-Image assets for personal, client, or commercial deployment.",
                },
            ],
        },
        "geo": {
            "author": "Dr. Viktor K. Voronov",
            "expertise": "Principal Storage & Acoustics Systems Architect",
            "last_updated": "2026-11-16",
            "facts": [
                {"claim": "Sustains 19.6s 1024x1024 Z-Image synthesis with 0 B disk swap.", "source_url": "https://smartllm-studio.example.org/specs.html"},
                {"claim": "Enforces 7.0:1 WCAG AAA primary text contrast in OKLCH.", "source_url": "https://smartllm-studio.example.org/"},
            ],
        },
        "ai_crawlers": dict(AI_CRAWLERS_DEFAULT),
    }


_RU_TRANSLIT_MAP: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _slugify_route(raw: str, fallback: str = "index") -> str:
    lower = str(raw or "").strip().lower()
    translit = "".join(_RU_TRANSLIT_MAP.get(ch, ch) for ch in lower)
    slug = re.sub(r"[^a-z0-9_-]+", "-", translit).strip("-")
    return slug or fallback


def _normalize_routes(raw_routes: list[dict[str, Any]] | None, lang: str) -> list[dict[str, Any]]:
    if not raw_routes:
        return default_project_draft()["routes"]
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, r in enumerate(raw_routes):
        raw_slug = str(r.get("slug") or ("index" if idx == 0 else f"page-{idx}")).strip()
        slug = _slugify_route(raw_slug, fallback="index" if idx == 0 else f"page-{idx}")
        if slug in seen:
            continue
        seen.add(slug)
        filename = "index.html" if slug in ("index", "home", "root") else f"{slug}.html"
        path = "/" if filename == "index.html" else f"/{filename}"
        bricks = list(r.get("bricks") or ["hero", "features", "faq", "contact", "footer"])
        default_title = raw_slug if any(ch in _RU_TRANSLIT_MAP for ch in raw_slug.lower()) else ("Главная" if lang == "ru" and filename == "index.html" else slug.title())
        out.append(
            {
                "slug": slug,
                "filename": filename,
                "path": path,
                "title": str(r.get("title") or default_title),
                "bricks": bricks,
                "copy_en": dict(r.get("copy_en") or {}),
                "copy_ru": dict(r.get("copy_ru") or {}),
            }
        )
    return out


def compile_project_blueprint(payload: dict[str, Any], repo_root: Path | None = None) -> dict[str, Any]:
    """Compile a ProjectDraft / Express / Constructor payload into static bundle + audit scorecard."""
    root = (repo_root or DEFAULT_REPO_ROOT).resolve()
    selector = get_rag_selector(repo_root=root)

    brief = str(payload.get("brief") or payload.get("goal") or "Offline-first industrial engineering platform").strip()
    lang_pref = str(payload.get("languages") or payload.get("lang") or "auto")
    explicit_canon = payload.get("canon_id")
    rag = selector.select(brief=brief, lang="ru" if lang_pref == "ru" else ("en" if lang_pref == "en" else "auto"), explicit_canon_id=explicit_canon)
    resolved_lang = "ru" if lang_pref == "ru" else rag["lang"]
    card = rag["canon_card"]
    req_pol = str(payload.get("polarity") or "auto").strip().lower()
    default_pol = str(card.get("default_polarity") or "light").strip().lower()
    resolved_polarity = req_pol if req_pol in ("light", "dark") else (default_pol if default_pol in ("light", "dark") else "light")
    pal = (card.get("palettes") or {}).get(resolved_polarity) or card["palette"]
    fonts = card["fonts"]

    project_name = str(payload.get("name") or payload.get("project_name") or ("Кварц-Ателье" if resolved_lang == "ru" else "Quartz-Field Atelier")).strip()
    seo_cfg = dict(payload.get("seo") or {})
    base_url = str(seo_cfg.get("base_url") or payload.get("base_url") or "https://smartllm-studio.example.org").rstrip("/")
    canon_motion = CANON_MOTION_DEFAULTS.get(str(card.get("id") or ""), {})
    raw_stack = str(payload.get("stack") or "").strip()
    stack = normalize_stack_id(raw_stack or str(canon_motion.get("default_stack") or "astro"))
    raw_motion = str(payload.get("motion") or "").strip()
    motion = normalize_motion_id(raw_motion or str(canon_motion.get("default_motion") or "css_scroll_driven"))
    valid_landings = {"gsap_scrollytelling", "kinetic_showreel", "bento_interactive", "css_scroll_native", "classic_corporate"}
    raw_landing = str(payload.get("landing_preset") or "").strip().lower()
    if raw_landing in valid_landings:
        landing_preset = raw_landing
    elif str(canon_motion.get("default_landing_preset") or "") in valid_landings:
        landing_preset = str(canon_motion["default_landing_preset"])
    elif motion == "motion":
        landing_preset = "gsap_scrollytelling"
    elif motion == "animejs":
        landing_preset = "kinetic_showreel"
    else:
        landing_preset = "css_scroll_native"
    raw_routes = payload.get("routes")
    if not raw_routes and payload.get("selected_pages"):
        routes = build_routes_from_pages(
            [str(x) for x in payload.get("selected_pages") or []],
            payload.get("page_blocks") if isinstance(payload.get("page_blocks"), dict) else None,
            resolved_lang,
        )
    elif not raw_routes and str(payload.get("site_type") or "") == "single":
        routes = build_routes_from_pages(
            ["index"],
            {"index": list(payload.get("selected_blocks") or [])} if payload.get("selected_blocks") else None,
            resolved_lang,
        )
    else:
        routes = _normalize_routes(raw_routes, resolved_lang)

    if payload.get("express_generate") and brief:
        clean_b = " ".join(brief.split()).rstrip(".,;:")
        short_hl = clean_b if len(clean_b) <= 68 else clean_b[:65].rsplit(" ", 1)[0]
        lead_sub = clean_b[:220]
        if routes:
            routes[0]["copy_en"] = {"headline": short_hl, "subhead": lead_sub}
            routes[0]["copy_ru"] = {"headline": short_hl, "subhead": lead_sub}
        seo_cfg["title"] = f"{project_name} — {short_hl[:48]}"
        seo_cfg["description"] = lead_sub[:155]

    safe_id = "".join(c for c in str(payload.get("id") or "default") if c.isalnum() or c in ("-", "_")) or "default"
    default_projects_root = Path(discover_studio_paths(repo_root=root)["projects_root"])
    project_dir = _safe_project_dir(payload.get("output_dir") or payload.get("project_dir"), default_projects_root / safe_id)
    assets_dir = project_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    logo_src_key = "selected_logo_path" if payload.get("selected_logo_path") else ("logo_path" if payload.get("logo_path") else "")
    if payload.get("logo_bytes_b64") and payload.get("logo_filename"):
        logo_meta = ingest_brand_logo(str(payload["logo_filename"]), base64.b64decode(str(payload["logo_bytes_b64"])), assets_dir)
    elif logo_src_key:
        lp = Path(str(payload[logo_src_key])).resolve()
        allowed_roots = (
            (root / "eval" / "studio_projects").resolve(),
            (root / "studio_projects").resolve(),
            STUDIO_ROOT.resolve(),
            project_dir.parent.resolve(),
            project_dir.resolve(),
        )
        if lp.exists() and lp.is_file() and any(lp.is_relative_to(r) for r in allowed_roots):
            logo_meta = ingest_brand_logo(lp.name, lp.read_bytes(), assets_dir)
        else:
            default_svg = (STUDIO_ROOT / "assets" / "smartllm-logo.svg").read_bytes()
            logo_meta = ingest_brand_logo("smartllm-logo.svg", default_svg, assets_dir)
    elif (assets_dir / "brand-logo.png").exists():
        logo_meta = {
            "logo_relpath": "assets/brand-logo.png",
            "favicon_relpath": "assets/brand-logo.png",
            "swatches": ["#0b0d12", "#151923", "#c084fc", "#e5b869", "#eceef3", "#4ade80"],
        }
    else:
        default_svg = (STUDIO_ROOT / "assets" / "smartllm-logo.svg").read_bytes()
        logo_meta = ingest_brand_logo("smartllm-logo.svg", default_svg, assets_dir)

    hero_png = assets_dir / "hero_primary.png"
    if not hero_png.exists():
        default_hero = STUDIO_ROOT / "assets" / "art" / "default_hero_preview.png"
        if default_hero.exists():
            shutil.copyfile(default_hero, hero_png)
        else:
            make_synthetic_png(hero_png, width=1024, height=1024, seed_shift=1)
    hero_dims = read_png_dimensions(hero_png, (1024, 576))
    image_dims: dict[str, tuple[int, int]] = {"assets/hero_primary.png": hero_dims}

    faqs = list(seo_cfg.get("faqs") or payload.get("faqs") or [])
    pipe = payload.get("pipeline") if isinstance(payload.get("pipeline"), dict) else {}
    pipe_pages = pipe.get("pages") if isinstance(pipe.get("pages"), dict) else {}
    chrome = pipe.get("chrome") if isinstance(pipe.get("chrome"), dict) else {}
    if not faqs:
        faqs = list(pipe.get("faqs") or [])
    if not faqs:
        if resolved_lang == "ru":
            faqs = [
                {"q": f"Как строится работа с «{project_name}»?", "a": "Каждый проект начинается с фиксации объёма работ, сметы и контрольных сроков до запуска."},
                {"q": "Как получить смету и консультацию?", "a": "Оставьте заявку через форму на сайте или по указанным контактам — подготовим расчёт и план этапов."},
            ]
        else:
            faqs = [
                {"q": f"How does {project_name} structure project delivery?", "a": "Every engagement begins with fixed milestones, transparent scope documentation, and upfront pricing."},
                {"q": "How can we request a tailored proposal?", "a": "Use the contact form or reach our team directly by phone or email to schedule an initial scoping session."},
            ]
    geo_cfg = dict(payload.get("geo") or {})
    if not geo_cfg:
        geo_cfg = {
            "author": project_name,
            "expertise": brief[:90],
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "facts": [],
        }
    pipe_facts = [f for f in (pipe.get("geo_facts") or []) if isinstance(f, dict) and str(f.get("claim") or "").strip()]
    if pipe_facts:
        geo_cfg["facts"] = [
            {"claim": str(f["claim"]).strip(), "source_url": str(f.get("source_url") or f"{base_url}/{('' if i == 0 else 'about.html')}")}
            for i, f in enumerate(pipe_facts)
        ]
    ai_crawlers = {**AI_CRAWLERS_DEFAULT, **(payload.get("ai_crawlers") or {})}

    dossier = load_canon_dossier(card["id"])
    vendor_bundle = bundle_vendor_assets_for_canon(card["id"], project_dir, motion)
    theme_css = build_canon_theme_css(card["id"], default_polarity=resolved_polarity)
    css_text = (
        (vendor_bundle["font_css"] + "\n" if vendor_bundle["font_css"] else "")
        + theme_css
        + "\n"
        + _build_tokens_css(pal, fonts, card.get("layout", {}), polarity=resolved_polarity, canon_responsive=card.get("responsive"))
        + _build_canon_css(card, dossier, polarity=resolved_polarity, motion=motion, landing_preset=landing_preset)
    )
    from .canon_layouts import apply_layout, canon_layout_css, is_layout_canon
    if is_layout_canon(card["id"]):
        # canon-owned layout: fonts + canon vars + canon CSS only (no shared base stylesheet)
        css_text = canon_layout_css(
            card["id"],
            _build_tokens_css(pal, fonts, card.get("layout", {}), polarity=resolved_polarity, canon_responsive=card.get("responsive")),
            vendor_bundle["font_css"],
        )
    style_hash = sha256_csp(css_text)
    bilingual = lang_pref == "en+ru"
    alt_lang = "en" if resolved_lang == "ru" else "ru"
    i18n: dict[str, dict[str, str]] = {}
    js_placeholder = "/*__SLM_APP_JS__*/"
    hash_placeholder = "__SLM_SCRIPT_HASH__"

    csp_meta = (
        f"default-src 'none'; script-src 'self' '{hash_placeholder}'; style-src 'self' '{style_hash}'; style-src-attr 'none'; "
        f"img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; "
        f"form-action 'self'; object-src 'none'; require-trusted-types-for 'script'"
    )

    written_files: list[str] = ["tokens.css", "app.js", "_headers", "robots.txt", "sitemap.xml", "zimage_prompts.json", "project_blueprint.json", logo_meta["logo_relpath"], "assets/hero_primary.png"]
    written_files.extend(f for f in vendor_bundle["files"] if f not in written_files)
    if seo_cfg.get("llms_txt_enabled", True):
        written_files.append("llms.txt")

    audience = str(payload.get("audience") or "").strip()
    block_prompts = dict(payload.get("block_prompts") or {})
    page_block_prompts = payload.get("page_block_prompts") if isinstance(payload.get("page_block_prompts"), dict) else {}
    company = dict(payload.get("company") or build_default_company(project_name, brief, resolved_lang))
    if company.get("hours"):
        company["hours"] = normalize_hours_for_lang(str(company["hours"]), resolved_lang)
    asset_rev = int(payload.get("revision") or 1)
    page_images = {
        r["slug"]: f"assets/hero_{r['slug']}.png"
        for r in routes
        if (project_dir / "assets" / f"hero_{r['slug']}.png").exists()
    }
    team_images = [f"assets/team_{i}.png" for i in range(1, 5) if (project_dir / "assets" / f"team_{i}.png").exists()]
    gallery_all = [str(x) for x in (pipe.get("gallery_images") or []) if (project_dir / str(x)).exists()]
    for img_rel in [*page_images.values(), *team_images, *gallery_all]:
        fallback_d = (576, 768) if "team_" in img_rel else (1024, 576)
        image_dims[img_rel] = read_png_dimensions(project_dir / img_rel, fallback_d)
    loc_chrome = pipe.get("loc_chrome") if isinstance(pipe.get("loc_chrome"), dict) else {}
    routed_variants: dict[str, dict[str, str]] = {}
    rendered_docs: list[tuple[dict[str, Any], str]] = []
    for page_idx, route in enumerate(routes):
        route_prompts = page_block_prompts.get(route["slug"]) if isinstance(page_block_prompts.get(route["slug"]), dict) else {}
        if route_prompts:
            route["block_prompts"] = dict(route_prompts)
        page_meta = pipe_pages.get(route["slug"]) if isinstance(pipe_pages.get(route["slug"]), dict) else {}
        vmap = route_block_variants(
            card["id"],
            list(route.get("bricks") or []),
            preferred=(page_meta.get("variants") if isinstance(page_meta.get("variants"), dict) else None),
            page_idx=page_idx,
        )
        routed_variants[route["slug"]] = vmap
        page_meta_eff = {**page_meta, "variants": {**(page_meta.get("variants") or {}), **vmap}}
        gallery_images = gallery_all
        html_doc = _render_route_html(
            route=route,
            all_routes=routes,
            project_name=project_name,
            brief=brief,
            lang=resolved_lang,
            bilingual=bilingual,
            card=card,
            copy_pairs=rag["copy_pairs"],
            faqs=faqs,
            geo_cfg=geo_cfg,
            seo_cfg=seo_cfg,
            logo_relpath=logo_meta["logo_relpath"],
            favicon_relpath=logo_meta["favicon_relpath"],
            base_url=base_url,
            csp_meta=csp_meta,
            css_text=css_text,
            js_text=js_placeholder,
            stack=stack,
            motion=motion,
            audience=audience,
            block_prompts=block_prompts,
            company=company,
            asset_rev=asset_rev,
            chrome=chrome,
            page_meta=page_meta_eff,
            gallery_images=gallery_images,
            hero_dims=hero_dims,
            dossier=dossier,
            alt_lang=alt_lang,
            loc=page_meta.get("loc") if isinstance(page_meta.get("loc"), dict) else {},
            loc_chrome=loc_chrome,
            page_images=page_images,
            team_images=team_images,
            image_dims=image_dims,
            i18n=i18n,
            page_idx=page_idx,
            polarity=resolved_polarity,
            vendor_scripts=vendor_bundle.get("js_relpaths") or [],
            landing_preset=landing_preset,
        )
        if is_layout_canon(card["id"]):
            _nav_lbl = ((chrome or {}).get("nav_labels") or {}) if isinstance((chrome or {}).get("nav_labels"), dict) else {}
            html_doc = apply_layout(
                html_doc, card["id"], slug=route["slug"], page_no=page_idx + 1,
                page_label=str(_nav_lbl.get(route["slug"]) or route.get("title") or route["slug"]),
                lang=resolved_lang,
                extras={"topline": str(company.get("tagline") or company.get("positioning") or "")[:90]},
            )
        _vis_p = project_dir / ".smartllm" / "memory" / "vision_check.json"
        if _vis_p.exists():
            from .vision_stage import apply_vision_alts
            try:
                html_doc = apply_vision_alts(html_doc, json.loads(_vis_p.read_text(encoding="utf-8")))
            except ValueError:
                pass
        rendered_docs.append((route, html_doc))
        if route["filename"] not in written_files:
            written_files.insert(0, route["filename"])

    js_text = _build_motion_and_ui_js(stack=stack, motion=motion, lang=resolved_lang, d=dossier, i18n=i18n, bilingual=bilingual, canon_id=card["id"], landing_preset=landing_preset)
    script_hash = sha256_csp(js_text)
    csp_header = csp_meta.replace(hash_placeholder, script_hash).replace("object-src 'none';", "frame-ancestors 'none'; object-src 'none';")
    (project_dir / "tokens.css").write_text(css_text, encoding="utf-8")
    (project_dir / "app.js").write_text(js_text, encoding="utf-8")
    rendered_pages: dict[str, str] = {}
    for route, html_doc in rendered_docs:
        html_doc = html_doc.replace(js_placeholder, js_text).replace(hash_placeholder, script_hash)
        (project_dir / route["filename"]).write_text(html_doc, encoding="utf-8")
        rendered_pages[route["slug"]] = html_doc
    written_files.extend(p for p in page_images.values() if p not in written_files)
    written_files.extend(t for t in team_images if t not in written_files)

    _write_seo_and_security_files(
        project_dir, project_name, brief, card, routes, base_url, csp_header, style_hash, script_hash,
        rag["copy_pairs"], ai_crawlers, bool(seo_cfg.get("llms_txt_enabled", True)),
        dict(payload.get("zimage_direction") or {}), company,
        page_seo={slug: (meta.get("seo") or {}) for slug, meta in pipe_pages.items()},
        visuals=pipe.get("visuals") if isinstance(pipe.get("visuals"), dict) else {},
        hero_variant=str((((routed_variants.get("index") or {}).get("hero")) or ((pipe_pages.get("index") or {}).get("variants") or {}).get("hero")) or ""),
    )
    scaffolds = emit_stack_scaffold(project_dir, stack, motion, project_name, card["id"], routes)
    pm_file = write_page_model_json(
        project_dir,
        canon_id=card["id"],
        polarity=resolved_polarity,
        stack=stack,
        motion=motion,
        routes=routes,
        block_variants=routed_variants,
        page_block_prompts=page_block_prompts,
    )
    written_files.extend(f for f in [*scaffolds, pm_file] if f not in written_files)
    if (project_dir / "smartllm.md").exists():
        written_files.append("smartllm.md")
    written_files.extend(g for g in (pipe.get("gallery_images") or []) if g not in written_files)

    scorecard = compute_real_scorecard(
        project_dir=project_dir,
        rendered_pages=rendered_pages,
        css_text=css_text,
        js_text=js_text,
        style_hash=style_hash,
        script_hash=script_hash,
        card=card,
        headers_text=(project_dir / "_headers").read_text(encoding="utf-8"),
        robots_text=(project_dir / "robots.txt").read_text(encoding="utf-8"),
        sitemap_text=(project_dir / "sitemap.xml").read_text(encoding="utf-8"),
        llms_enabled=bool(seo_cfg.get("llms_txt_enabled", True)),
        ai_crawlers=ai_crawlers,
        geo_cfg=geo_cfg,
        min_target_px=44,
    )

    blueprint_doc = {
        "schema_version": __version__,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project_id": str(payload.get("id") or project_dir.name),
        "revision": int(payload.get("revision") or 1),
        "project_name": project_name,
        "project_dir": str(project_dir),
        "brief": brief,
        "lang": resolved_lang,
        "languages": lang_pref,
        "stack": stack,
        "motion": motion,
        "landing_preset": landing_preset,
        "canon_id": card["id"],
        "canon_name": card["name"],
        "polarity": resolved_polarity,
        "page_model": pm_file,
        "company": company,
        "logo": logo_meta,
        "routes": routes,
        "faqs": faqs,
        "geo": geo_cfg,
        "ai_crawlers": ai_crawlers,
        "style_sha256": style_hash,
        "script_sha256": script_hash,
        "audit_scorecard": scorecard,
        "skill_directives": rag.get("skill_directives", {}),
        "files": written_files,
    }
    (project_dir / "project_blueprint.json").write_text(json.dumps(blueprint_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return blueprint_doc


def export_project_bundle(project_dir: Path, target_dir: Path | None = None, as_zip: bool = False) -> dict[str, Any]:
    """Export compiled project bundle to a target folder or .zip archive inside target folder."""
    src = project_dir.resolve()
    dest = (target_dir or src).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    if as_zip:
        zip_path = dest / f"{src.name}_bundle.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in sorted(src.rglob("*")):
                if not fp.is_file() or fp.resolve() == zip_path.resolve():
                    continue
                rel = fp.relative_to(src)
                if ".smartllm" in rel.parts or fp.suffix.lower() == ".zip":
                    continue
                zf.write(fp, rel)
        return {"exported": True, "format": "zip", "path": str(zip_path), "bytes": zip_path.stat().st_size}

    if dest != src:
        shutil.copytree(src, dest, dirs_exist_ok=True)
    return {"exported": True, "format": "folder", "path": str(dest)}


from .blueprint_render import (  # noqa: E402
    _build_canon_css,
    _build_motion_and_ui_js,
    _build_tokens_css,
    _render_route_html,
    _write_seo_and_security_files,
    _write_stack_scaffold_files,
    load_canon_dossier,
)
