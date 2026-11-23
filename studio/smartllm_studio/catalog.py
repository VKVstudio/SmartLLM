"""Standalone-first RAG catalog loader (20 classical design canons, checklists, stacks, motions, bricks)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import STUDIO_ROOT

DATA_DIR = STUDIO_ROOT / "smartllm_studio" / "data"

STACK_CATALOG: list[dict[str, Any]] = [
    {"id": "astro", "name_en": "Astro 7.4 Islands + Content Layer (Zod v4)", "name_ru": "Astro 7.4 Острова + Content Layer (Zod v4)", "checklist_id": "STACK-ASTRO-01"},
    {"id": "html5_esm", "name_en": "Zero-Build Semantic HTML5 + OKLCH CSS + Native ESM", "name_ru": "Семантический HTML5 + OKLCH CSS + Native ESM", "checklist_id": "STACK-VITE-TS-01"},
    {"id": "vite_ts", "name_en": "Vite 8.3 (Rolldown) + TypeScript 7 + Same-Origin BFF", "name_ru": "Vite 8.3 (Rolldown) + TypeScript 7 + Same-Origin BFF", "checklist_id": "STACK-VITE-TS-01"},
    {"id": "nextjs", "name_en": "Next.js 16.4 LTS (App Router + proxy.ts + React 19.3)", "name_ru": "Next.js 16.4 LTS (App Router + proxy.ts + React 19.3)", "checklist_id": "STACK-NEXT-01"},
    {"id": "sveltekit", "name_en": "SvelteKit 3.4 + Svelte 5.59 Runes (#lib/* + csrf.trustedOrigins)", "name_ru": "SvelteKit 3.4 + Svelte 5.59 Runes (#lib/* + csrf.trustedOrigins)", "checklist_id": "STACK-SVELTE-01"},
]

MOTION_CATALOG: list[dict[str, Any]] = [
    {"id": "css_scroll_driven", "name_en": "Native CSS Scroll-Driven Animations (0 KB JS, CLS=0.00)", "name_ru": "Нативные CSS Scroll-Driven анимации (0 КБ JS, CLS=0.00)"},
    {"id": "motion", "name_en": "Motion 14.14 Core (MIT — animate, scroll, spring)", "name_ru": "Motion 14.14 Core (MIT — animate, scroll, spring)"},
    {"id": "animejs", "name_en": "Anime.js 4.5 Timeline & Stagger (MIT)", "name_ru": "Anime.js 4.5 таймлайны и стэггеры (MIT)"},
    {"id": "lenis", "name_en": "Lenis 1.3 Smooth Scroll (MIT)", "name_ru": "Lenis 1.3 плавный скролл (MIT)"},
    {"id": "three", "name_en": "Three.js 0.187 Lazy 3D Stage (MIT)", "name_ru": "Three.js 0.187 ленивая 3D-сцена (MIT)"},
    {"id": "reduced_motion_instant", "name_en": "Zero-Motion Instant Settled Layout", "name_ru": "Мгновенная статика без анимаций"},
]

LANDING_PRESET_CATALOG: list[dict[str, Any]] = [
    {
        "id": "gsap_scrollytelling",
        "name_en": "GSAP-Class Scrollytelling Landing",
        "name_ru": "Скроллтеллинг-лендинг (GSAP-класс)",
        "badge_en": "Motion 14 + Lenis",
        "badge_ru": "Motion 14 + Lenis",
        "desc_en": "Sticky pinned visual stage, numbered scroll chapters, marquee ribbon, counters & parallax.",
        "desc_ru": "Липкая сцена с главами при скролле, бегущая строка, живые счётчики и параллакс.",
        "motion": "motion",
        "recommended_canons": ["10_industrial_tactile", "12_quiet_luxury_minimal", "14_spatial_3d_showcase", "15_organic_biophilic_eco"],
    },
    {
        "id": "kinetic_showreel",
        "name_en": "Kinetic Showreel & Filmstrip",
        "name_ru": "Кинетический шоурил (Anime.js)",
        "badge_en": "Anime.js 4.5 + Lenis",
        "badge_ru": "Anime.js 4.5 + Lenis",
        "desc_en": "Timeline headline stagger, sticky narrative chapters, 3D tilt frame & magnetic CTA.",
        "desc_ru": "Таймлайн-каскад заголовков, скролл-главы, 3D-наклон сцены и магнитные кнопки.",
        "motion": "animejs",
        "recommended_canons": ["06_neo_brutalism", "05_kinetic_typography", "13_cinematic_documentary", "02_swiss_international"],
    },
    {
        "id": "bento_interactive",
        "name_en": "Interactive Modular Bento",
        "name_ru": "Интерактивный Bento-лендинг",
        "badge_en": "Motion 14 + Lenis",
        "badge_ru": "Motion 14 + Lenis",
        "desc_en": "Asymmetric 12-column bento modules, KPI stat counters, crisp elevation & spring hover.",
        "desc_ru": "Асимметричная 12-колоночная сетка, модульные карточки, счётчики и пружинный отклик.",
        "motion": "motion",
        "recommended_canons": ["01_bento_grid", "08_liquid_glass", "17_fintech_institutional", "18_devtool_command_ui"],
    },
    {
        "id": "css_scroll_native",
        "name_en": "Zero-JS Native CSS Scroll-Driven",
        "name_ru": "Нативный CSS Scroll-Driven",
        "badge_en": "0 KB JS · CLS 0.00",
        "badge_ru": "0 КБ JS · CLS 0.00",
        "desc_en": "Pure browser compositor animation-timeline: view() & scroll() with zero runtime JS overhead.",
        "desc_ru": "Чистый композиторный скролл-таймлайн браузера без лишнего JS-рантайма.",
        "motion": "css_scroll_driven",
        "recommended_canons": ["03_editorial_magazine", "04_hyper_minimal_speed", "19_calm_human_accessible"],
    },
    {
        "id": "classic_corporate",
        "name_en": "Structured Editorial Architecture",
        "name_ru": "Классический корпоративный",
        "badge_en": "Balanced Rhythm",
        "badge_ru": "Спокойный ритм",
        "desc_en": "High-readability multi-page hierarchy focused on dense proof, pricing matrices & SEO.",
        "desc_ru": "Чёткая деловая иерархия разделов, матрицы тарифов и максимальная читаемость.",
        "motion": "css_scroll_driven",
        "recommended_canons": ["02_swiss_international", "12_quiet_luxury_minimal", "17_fintech_institutional"],
    },
]

BRICK_CATALOG: list[dict[str, Any]] = [
    {"id": "hero", "name_en": "Hero Viewport (100svh + Z-Image)", "name_ru": "Главный экран (100svh + Z-Image)"},
    {"id": "manifesto", "name_en": "Tagline, Positioning & Brand Promise", "name_ru": "Девиз, позиционирование и обещание бренда"},
    {"id": "values", "name_en": "Product, People & Client Values", "name_ru": "Отношение к продукту, людям и клиентам"},
    {"id": "priorities", "name_en": "Top Priorities & Key Phrases", "name_ru": "Топ-приоритеты и ключевые фразы"},
    {"id": "locations", "name_en": "Locations, Offices & Addresses", "name_ru": "География, офисы и адреса"},
    {"id": "features", "name_en": "Engineering Features & Capabilities Grid", "name_ru": "Сетка инженерных возможностей"},
    {"id": "about", "name_en": "About, Methodology & Proof", "name_ru": "О компании, подход и факты"},
    {"id": "stats", "name_en": "Metrics & Verified Proof Points", "name_ru": "Метрики и подтверждённые факты"},
    {"id": "gallery", "name_en": "Z-Image Optical Asset Gallery", "name_ru": "Галерея визуальных артефактов Z-Image"},
    {"id": "pricing", "name_en": "Transparent Tier & Specification Matrix", "name_ru": "Матрица тарифов и комплектаций"},
    {"id": "testimonials", "name_en": "Verified Deployment Case Studies", "name_ru": "Проверенные кейсы внедрения"},
    {"id": "process", "name_en": "Delivery Process & Timeline", "name_ru": "Процесс работы и сроки"},
    {"id": "team", "name_en": "Team & Principal Experts", "name_ru": "Команда и ключевые эксперты"},
    {"id": "blog", "name_en": "Insights & Editorial Articles", "name_ru": "Статьи и экспертные материалы"},
    {"id": "faq", "name_en": "AEO Verbatim FAQ (JSON-LD Synced)", "name_ru": "Вопросы и ответы AEO (синхронно с JSON-LD)"},
    {"id": "cta", "name_en": "Primary Action Banner", "name_ru": "Баннер целевого действия"},
    {"id": "contact", "name_en": "Accessible Intake Form (+ Honeypot)", "name_ru": "Доступная форма заявки (+ Honeypot)"},
    {"id": "footer", "name_en": "Colophon & Security Verification Footer", "name_ru": "Подвал верификации и контактов"},
]

CANON_CATEGORIES: list[dict[str, str]] = [
    {"id": "layout", "label_en": "Layout & Composition", "label_ru": "Сетка и композиция"},
    {"id": "typography", "label_en": "Typography", "label_ru": "Типографика"},
    {"id": "surface", "label_en": "Color & Surface", "label_ru": "Цвет и поверхности"},
    {"id": "immersive", "label_en": "Immersive Experience", "label_ru": "Иммерсивный опыт"},
    {"id": "experimental", "label_en": "Experimental", "label_ru": "Экспериментальные"},
    {"id": "accessible", "label_en": "Accessible & Sustainable", "label_ru": "Доступность и устойчивость"},
]

AI_CRAWLERS_DEFAULT: dict[str, bool] = {
    "GPTBot": False,
    "OAI-SearchBot": True,
    "ClaudeBot": False,
    "Claude-SearchBot": True,
    "PerplexityBot": True,
    "Google-Extended": False,
    "Applebot-Extended": False,
    "CCBot": False,
    "Bytespider": False,
}


def load_studio_catalog(repo_root: Path | None = None) -> dict[str, Any]:
    """Load the 20 classical design canons, checklists, stacks, motions, bricks and page-type taxonomy."""
    _ = repo_root
    canons_raw = json.loads((DATA_DIR / "canon_cards.json").read_text(encoding="utf-8"))
    canons = [
        {
            "id": c.get("id"),
            "name": c.get("name"),
            "name_ru": c.get("name_ru") or c.get("name"),
            "category": c.get("category", "general"),
            "description_en": c.get("description_en", ""),
            "description_ru": c.get("description_ru", ""),
            "preview_image": c.get("preview_image", ""),
            "default_polarity": c.get("default_polarity", "light"),
            "best_for": c.get("best_for", []),
            "search_terms": c.get("search_terms", []),
            "palette": c.get("palette", {}),
            "palettes": c.get("palettes", {}),
            "fonts": c.get("fonts", {}),
            "layout": c.get("layout", {}),
            "responsive": c.get("responsive", {}),
            "a11y": c.get("a11y", {}),
            "imagery": c.get("imagery", {}),
            "rules": c.get("rules", {}),
            "specimen": "Aa Яя 123",
        }
        for c in canons_raw
    ]
    category_counts = {str(cat["id"]): 0 for cat in CANON_CATEGORIES}
    for canon in canons:
        cat_id = str(canon.get("category") or "")
        if cat_id in category_counts:
            category_counts[cat_id] += 1
    categories = [
        {**cat, "count": category_counts.get(str(cat["id"]), 0)}
        for cat in CANON_CATEGORIES
    ]

    chk_map: dict[str, Any] = json.loads((DATA_DIR / "checklists.json").read_text(encoding="utf-8"))
    checklists: list[dict[str, Any]] = []
    for stem, doc in sorted(chk_map.items()):
        checklists.append(
            {
                "file": f"checklists/{stem}.json",
                "stem": stem,
                "kind": "json",
                "id": doc.get("id", stem),
                "title": doc.get("title", stem),
                "checks_count": len(doc.get("checks", [])),
            }
        )
        if stem != "zimage_canon_prompts":
            checklists.append(
                {
                    "file": f"checklists/{stem}.md",
                    "stem": f"{stem}_guide",
                    "kind": "markdown",
                    "id": f"md_{stem}",
                    "title": f"{doc.get('title', stem)} (Guide)",
                    "checks_count": 0,
                }
            )

    return {
        "canons": canons,
        "canons_count": len(canons),
        "canon_categories": categories,
        "checklists": checklists,
        "checklists_count": len(checklists),
        "stacks": STACK_CATALOG,
        "motions": MOTION_CATALOG,
        "landing_presets": LANDING_PRESET_CATALOG,
        "bricks": BRICK_CATALOG,
        "ai_crawlers_default": AI_CRAWLERS_DEFAULT,
    }
