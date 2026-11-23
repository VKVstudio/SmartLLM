#!/usr/bin/env python3
"""Rebuild data/canon_cards.json & data/canon_dossiers.json from verified Phase 1 KB canons."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PKG_ROOT = Path(__file__).resolve().parents[1] / "smartllm_studio"
KB_CANONS_DIR = PKG_ROOT / "kb" / "styles" / "canons"
MATRIX_PATH = PKG_ROOT / "kb" / "styles" / "blocks" / "_matrix.json"
OUT_CARDS = PKG_ROOT / "data" / "canon_cards.json"
OUT_DOSSIERS = PKG_ROOT / "data" / "canon_dossiers.json"

DESCRIPTIONS: dict[str, tuple[str, str, list[str], list[str]]] = {
    "01_bento_grid": (
        "Modular asymmetric Bento compartments with 24px matte tiles, 1px cool hairlines, and balanced 7/5 layout rhythm.",
        "Модульная асимметричная бенто-сетка: матовые карточки 24px, рамки 1px и ритм отсеков 7/5 без лишнего шума.",
        ["saas", "hardware", "product", "portfolio", "dashboard"],
        ["бенто", "сетка", "карточки", "bento", "saas", "hardware", "product"],
    ),
    "02_swiss_international": (
        "Swiss International Typographic grid with 0px sharp corners, exposed 1px black borders, and vivid crimson CTA anchor.",
        "Швейцарская интернациональная сетка: острые углы 0px, открытые линии 1px и единственный акцент-якорь.",
        ["corporate", "architecture", "engineering", "consulting", "specs"],
        ["швейцарский", "сетка", "строгий", "swiss", "grid", "black", "minimal"],
    ),
    "03_editorial_magazine": (
        "Broadsheet literary editorial canon with Source Serif 4 masthead, 2px ink bar, 1px column dividers, and warm newsprint tone.",
        "Газетно-журнальная типографика: крупная антиква Source Serif 4, линия шапки 2px и полосы с 1px-разделителями.",
        ["editorial", "journalism", "research", "publishing", "monograph"],
        ["журнал", "газета", "редакционный", "антиква", "editorial", "magazine", "serif"],
    ),
    "04_hyper_minimal_speed": (
        "Borderless high-speed documentation canon: 68ch measure, crisp Geist family, 0-120ms transitions, zero decorative clutter.",
        "Ультраминимализм и скорость: безрамочная вёрстка 68ch, шрифт Geist, мгновенные отклики и чистая иерархия.",
        ["docs", "devtools", "saas", "engineering", "specs"],
        ["быстрый", "минимализм", "документация", "hyper", "speed", "docs", "clean"],
    ),
    "05_kinetic_typography": (
        "Dark museum-poster kinetic stage with variable-width Tektur display typography, 2px frames, and crisp color-flood hover.",
        "Тёмная выставочная кинетическая сцена: переменная ширина Tektur, рамки 2px и инверсия цвета при наведении.",
        ["culture", "exhibition", "agency", "launch", "creative"],
        ["кинетика", "постер", "выставка", "тёмный", "kinetic", "poster", "dark"],
    ),
    "06_neo_brutalism": (
        "Raw direct-flash Neo-Brutalism: 0px corners, 3px ink borders, 6px orthogonal offset shadow, volt highlight behind black text.",
        "Нео-брутализм: углы 0px, обводка 3px, чёткая жёсткая тень 6px под 0° и высокий контраст акцентов.",
        ["startup", "agency", "creative", "campaign", "community"],
        ["брутализм", "смелый", "постер", "brutal", "raw", "volt", "magenta"],
    ),
    "07_avant_garde_poster": (
        "Constructivist geometric exhibition canon with condensed uppercase display type, 4px scarlet top bars, and zero drop shadows.",
        "Конструктивистский авангард: высокий рубленый капс, верхние плашки 4px и строгая плоскостная композиция без теней.",
        ["culture", "festival", "architecture", "exhibition", "media"],
        ["авангард", "конструктивизм", "баухаус", "poster", "avant", "bauhaus"],
    ),
    "08_liquid_glass": (
        "Spatial obsidian liquid-glass UI with opaque-safe >=0.72 alpha panels, blur(20px), specular top rims, and solid fallbacks.",
        "Тёмное матовое стекло (alpha >= 0.72, blur 20px) со световой верхней кромкой и обязательным твёрдым фолбэком.",
        ["ai", "spatial", "saas", "hardware", "fintech"],
        ["стекло", "пространственный", "тёмный", "glass", "spatial", "dark"],
    ),
    "09_aurora_obsidian_mesh": (
        "Restrained obsidian aurora field on fixed body::before paired strictly with solid opaque matte cards and sharp teal accent.",
        "Сдержанное обсидиановое сияние в фоне и строго непрозрачные матовые карточки без потери контраста текста.",
        ["ai", "cloud", "platform", "analytics", "saas"],
        ["аврора", "меш", "обсидиан", "тёмный", "aurora", "obsidian", "mesh", "dark"],
    ),
    "10_industrial_tactile": (
        "Precision industrial instrument inspired by Dieter Rams: bead-blasted surfaces, beveled keycaps, recessed inputs, orange dial.",
        "Индустриальный прибор в духе Брауна: матовый алюминий, объёмные клавиши, углублённые поля и сигнальный оранжевый акцент.",
        ["hardware", "audio", "engineering", "manufacturing", "iot"],
        ["индустриальный", "прибор", "тактильный", "hardware", "audio", "industrial", "tactile"],
    ),
    "11_soft_clay_playful": (
        "Friendly soft-claymorphism with 28px pill contours, double inset specular bevels, soft shadows, and Rubik/Nunito warmth.",
        "Мягкая глина и дружелюбный тактильный UI: радиус 28px, двойные блики, округлые пилюли и спокойная пастель.",
        ["edtech", "education", "wellness", "app", "family"],
        ["глина", "образование", "дружелюбный", "clay", "soft", "edtech", "playful"],
    ),
    "12_quiet_luxury_minimal": (
        "Cold architectural quiet luxury: pale platinum stone palette, 2x open whitespace, borderless cards, thin Cormorant Garamond 300-400.",
        "Холодный архитектурный тихий люкс: платина и камень, 2x воздуха, безрамочные блоки и тонкий Cormorant Garamond.",
        ["luxury", "architecture", "atelier", "real_estate", "hospitality"],
        ["люкс", "архитектура", "платина", "минимал", "luxury", "minimal", "atelier"],
    ),
    "13_cinematic_documentary": (
        "The ONLY dark serif canon: 35mm selenium charcoal atmosphere, subtle film grain, Literata serif typography, and amber key light.",
        "Единственный тёмный антиквенный канон: 35-мм плёночная глубина, селеновый уголь, антиква Literata и янтарный свет.",
        ["film", "documentary", "hospitality", "gastronomy", "storytelling"],
        ["кино", "документальный", "история", "тёмный", "cinema", "dark", "serif", "film"],
    ),
    "14_spatial_3d_showcase": (
        "Pitch-dark cyclorama stage framing a single lazy WebGL 3D showcase with specular ice-cyan rim and reduced-motion static fallback.",
        "Тёмная студийная циклорама для 3D/WebGL-объекта с ледяным контурным светом и статичным фолбэком без анимации.",
        ["3d", "hardware", "automotive", "ar", "product"],
        ["3d", "webgl", "пространственный", "сцена", "spatial", "showcase"],
    ),
    "15_organic_biophilic_eco": (
        "Low-carbon biophilic canon: sage-mist + Nordic pine (zero yellow beige), sub-400KB footprint, zero heavy SVG grain.",
        "Низкоуглеродный эко-канон: туманный шалфей и северная сосна (без жёлтого бежа), вес <= 400 КБ и чистый дневной свет.",
        ["eco", "sustainability", "clinic", "botanical", "architecture"],
        ["эко", "биотэк", "природа", "зелёный", "eco", "biophilic", "organic"],
    ),
    "16_artisan_craft_zine": (
        "Risograph craft zine aesthetic combining cool cotton-slate paper, kiln terracotta, Prussian indigo, and Vollkorn serif warmth.",
        "Ризография и ремесленный зин: хлопковая бумага, терракота, прусский индиго и тёплый Vollkorn с печатной тенью.",
        ["artisan", "coffee", "bakery", "craft", "design_studio"],
        ["крафт", "ремесло", "ризография", "кофе", "artisan", "craft", "zine"],
    ),
    "17_fintech_institutional": (
        "Swiss banking & legal trust ledger: crisp elevated 8px white cards on pale slate, midnight navy + emerald compliance accents.",
        "Институциональный финтех и право: приподнятые белые карточки 8px, тёмно-синий индиго, изумрудный статус и табличная строгость.",
        ["fintech", "legal", "finance", "enterprise", "b2b"],
        ["финтех", "банк", "право", "b2b", "fintech", "legal", "institutional"],
    ),
    "18_devtool_command_ui": (
        "Dark IDE developer workstation UI: flat #09090B surface, subtle 24px dot-grid, Geist Mono commands, emerald accent, zero purple.",
        "Тёмный интерфейс разработчика: плоский карбон, точечная сетка 24px, Geist Mono команды и изумрудный акцент без фиолетового.",
        ["devtools", "cli", "cybersecurity", "api", "infrastructure"],
        ["терминал", "разработка", "код", "кибербезопасность", "devtool", "cli", "ide", "dark"],
    ),
    "19_calm_human_accessible": (
        "WCAG 2.2 AAA-first civic & medical canon: >=14:1 ink contrast, 48px+ touch targets, visible focus halos, 0ms calm motion.",
        "Канон максимальной доступности WCAG AAA: контраст >= 14:1, кнопки 48px+, заметный фокус и отсутствие лишнего движения.",
        ["healthcare", "clinic", "gov", "civic", "education"],
        ["доступный", "клиника", "медицина", "образование", "calm", "accessible", "aaa"],
    ),
    "20_maximalist_collage_pop": (
        "Expressive archival pop collage: multi-hue ultramarine, marigold, and coral layers with 5px colored offset shadows.",
        "Максималистский поп-коллаж: смелый многоцветный ритм ультрамарина и охры с цветной офсетной тенью без потери читаемости.",
        ["festival", "youth", "agency", "creative", "media"],
        ["коллаж", "поп", "яркий", "фестиваль", "maximalist", "collage", "pop"],
    ),
}

MICRO_PROFILE: dict[str, tuple[str, str]] = {
    "01_bento_grid": ("lift", "clean"),
    "02_swiss_international": ("invert", "clean"),
    "03_editorial_magazine": ("underline", "paper"),
    "04_hyper_minimal_speed": ("underline", "clean"),
    "05_kinetic_typography": ("invert", "kinetic"),
    "06_neo_brutalism": ("invert", "brutal"),
    "07_avant_garde_poster": ("invert", "clean"),
    "08_liquid_glass": ("glow", "glass"),
    "09_aurora_obsidian_mesh": ("glow", "mesh"),
    "10_industrial_tactile": ("lift", "tactile"),
    "11_soft_clay_playful": ("lift", "clay"),
    "12_quiet_luxury_minimal": ("underline", "clean"),
    "13_cinematic_documentary": ("underline", "grain"),
    "14_spatial_3d_showcase": ("glow", "clean"),
    "15_organic_biophilic_eco": ("underline", "clean"),
    "16_artisan_craft_zine": ("lift", "paper"),
    "17_fintech_institutional": ("underline", "clean"),
    "18_devtool_command_ui": ("glow", "clean"),
    "19_calm_human_accessible": ("underline", "clean"),
    "20_maximalist_collage_pop": ("invert", "clean"),
}


def main() -> None:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    cards_out: list[dict[str, Any]] = []
    dossiers_out: dict[str, Any] = {}

    for cf in sorted(KB_CANONS_DIR.glob("*.json")):
        c = json.loads(cf.read_text(encoding="utf-8"))
        cid = c["id"]
        pol = c["default_polarity"]
        pal_def = dict(c["palettes"][pol])
        pal_compat = {**pal_def, "accent_3": pal_def.get("muted")}
        g = c["geometry"]
        r = c["responsive"]
        m = c["motion"]
        f = c["fonts"]
        desc_en, desc_ru, best_for, search_terms = DESCRIPTIONS[cid]
        hover_mode, surf_mode = MICRO_PROFILE[cid]

        card = {
            "id": cid,
            "name": c["name"],
            "name_ru": c["name_ru"],
            "category": c["category"],
            "description_en": desc_en,
            "description_ru": desc_ru,
            "best_for": best_for,
            "search_terms": search_terms,
            "preview_image": f"/static/art/canons/{cid}.webp",
            "default_polarity": pol,
            "marquee_allowed": bool(c["marquee_allowed"]),
            "dials": c["dials"],
            "legacy_ids": c.get("legacy_ids") or [],
            "fonts": {
                "heading": f["heading"],
                "body": f["body"],
                "mono": f["mono"] if f.get("mono") and f["mono"] != "none" else f["body"],
                "packages": f["packages"],
                "license": f["license"],
                "cyrillic_verified": True,
            },
            "palette": pal_compat,
            "palettes": c["palettes"],
            "layout": {
                "grid_cols": 12,
                "radius_px": int(g["radius_card_px"]),
                "radius_card_px": int(g["radius_card_px"]),
                "radius_button_px": int(g["radius_button_px"]),
                "radius_input_px": int(g["radius_input_px"]),
                "radius_badge_px": int(g["radius_badge_px"]),
                "border_width_px": int(g["border_width_px"]),
                "shadow": str(g["shadow_light"] if pol == "light" else g["shadow_dark"]),
                "shadow_light": str(g["shadow_light"]),
                "shadow_dark": str(g["shadow_dark"]),
                "pad_clamp": f"clamp({r['grid']['mobile']['section_py_px']}px, 5vw, {r['grid']['desktop']['section_py_px']}px)",
                "gap_clamp": f"clamp({r['grid']['mobile']['gutter_px']}px, 2vw, {r['grid']['desktop']['gutter_px']}px)",
                "heading_transform": r["typography"]["h1"].get("transform", "none"),
                "heading_tracking": r["typography"]["h1"]["ls"],
                "body_leading": r["typography"]["body"]["lh"],
                "surface_blur_px": 20 if cid == "08_liquid_glass" else 0,
                "page_bg_image": "radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px)" if cid == "18_devtool_command_ui" else "none",
            },
            "responsive": r,
            "motion": {
                "ease": m["ease"],
                "duration_ms": int(m["duration_ms"]),
                "stagger_ms": int(m["stagger_ms"]),
                "reduced_motion_policy": m["reduced_motion"],
            },
            "a11y": {
                "wcag_level": "AAA" if cid == "19_calm_human_accessible" else "AA+",
                "min_target_px": 48 if cid == "19_calm_human_accessible" else 44,
                "scroll_padding_top_px": 92,
                "text_bg_contrast_ratio": pal_def["contrast_verified"]["text_bg"],
                "border_control_contrast_ratio": pal_def["contrast_verified"]["border_control_surface"],
            },
            "rules": c["rules"],
            "imagery": {
                "aspect_ratio": "16:9",
                "prompt_tmpl": f"{c['zimage_direction'][pol]}, depicting {{subject}}",
                "style_tags": search_terms[:5],
            },
        }
        cards_out.append(card)

        rmap = matrix["routing_matrix"][cid]
        dossiers_out[cid] = {
            "default_polarity": pol,
            "motion": {
                "reveal": "scale" if surf_mode in ("glass", "clay") else ("clip" if cid in ("05_kinetic_typography", "07_avant_garde_poster") else "rise"),
                "stagger_ms": int(m["stagger_ms"]),
                "duration_ms": int(m["duration_ms"]),
                "ease": m["ease"],
                "scroll": "progress" if c["marquee_allowed"] else "none",
                "marquee": bool(c["marquee_allowed"]),
                "parallax": cid in ("13_cinematic_documentary", "14_spatial_3d_showcase"),
            },
            "micro": {
                "hover": hover_mode,
                "press_scale": 1.0 if surf_mode == "brutal" else 0.98,
                "press_ms": min(140, int(m["duration_ms"])),
                "link": "invert" if hover_mode == "invert" else "underline",
                "card_hover": str(m.get("hover") or ""),
            },
            "surface": surf_mode,
            "variants": rmap,
            "design_code": g["surface_treatment"],
            "block_rules": " | ".join(c["rules"]["do"]),
            "imagery": c["zimage_direction"][pol],
            "team": c["zimage_direction"]["team_portrait"],
        }

    OUT_CARDS.write_text(json.dumps(cards_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_DOSSIERS.write_text(json.dumps(dossiers_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"SYNCED_CANON_DATA: cards={len(cards_out)}, dossiers={len(dossiers_out)}")


if __name__ == "__main__":
    main()
