"""Standalone-first RAG catalog loader (20 classical design canons, checklists, stacks, motions, bricks)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import STUDIO_ROOT

DATA_DIR = STUDIO_ROOT / "smartllm_studio" / "data"

STACK_CATALOG: list[dict[str, Any]] = [
    {"id": "astro", "name_en": "Astro 5 Islands + Content Collections (Zod)", "name_ru": "Astro 5 Острова + Коллекции контента (Zod)", "checklist_id": "STACK-ASTRO-01"},
    {"id": "html5", "name_en": "Semantic HTML5 + OKLCH CSS + ES Module", "name_ru": "Семантический HTML5 + OKLCH CSS + ES-модуль", "checklist_id": "STACK-VITE-TS-01"},
    {"id": "vite_ts", "name_en": "Vite + Strict TypeScript 6.0 Bundle", "name_ru": "Vite + Строгий бандл TypeScript 6.0", "checklist_id": "STACK-VITE-TS-01"},
    {"id": "nextjs", "name_en": "Next.js App Router (RSC + Suspense + Zod)", "name_ru": "Next.js App Router (RSC + Suspense + Zod)", "checklist_id": "STACK-NEXT-01"},
    {"id": "sveltekit", "name_en": "SvelteKit (+page.server.ts + Progressive Enhance)", "name_ru": "SvelteKit (+page.server.ts + Прогрессивные формы)", "checklist_id": "STACK-SVELTE-01"},
]

MOTION_CATALOG: list[dict[str, Any]] = [
    {"id": "gsap_scrolltrigger", "name_en": "GSAP 3 + ScrollTrigger (batch, scrub, pin, CLS=0.00)", "name_ru": "GSAP 3 + ScrollTrigger (пакет, скраб, пин, CLS=0.00)"},
    {"id": "gsap_flip", "name_en": "GSAP 3 + Flip Layout Choreography", "name_ru": "GSAP 3 + Flip хореография раскладки"},
    {"id": "compositor_css", "name_en": "60fps GPU Compositor Transitions", "name_ru": "60fps переходы композитора GPU"},
    {"id": "reduced_motion_instant", "name_en": "Zero-Motion Instant Settled Layout", "name_ru": "Мгновенная статика без анимаций"},
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
            "best_for": c.get("best_for", []),
            "search_terms": c.get("search_terms", []),
            "palette": c.get("palette", {}),
            "fonts": c.get("fonts", {}),
            "layout": c.get("layout", {}),
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
        "bricks": BRICK_CATALOG,
        "ai_crawlers_default": AI_CRAWLERS_DEFAULT,
    }
