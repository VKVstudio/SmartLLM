"""Composition stage: a schema-validated per-page section plan built from block primitives.

The LLM (or the deterministic fallback) only chooses ORDER and LAYOUT VARIANT of the blocks the
user/planner already selected for each page. The compiler then renders the plan deterministically,
so block structure differs per canon and brief while content truth stays untouched.
"""

from __future__ import annotations

import json
from typing import Any

# Blocks that keep a fixed position.
_PINNED_FIRST = ("hero",)
_PINNED_LAST = ("cta", "contact", "legal", "footer")

# Narrative families: preferred order of the movable blocks for each canon.
_FAMILY_ORDER: dict[str, list[str]] = {
    # proof first: numbers, then what you get, then price, then trust
    "proof": ["stats", "features", "process", "pricing", "testimonials", "team", "about", "values", "priorities", "gallery", "locations", "blog", "faq", "manifesto"],
    # story first: manifesto/about, visuals, process, proof later
    "story": ["manifesto", "about", "gallery", "process", "features", "testimonials", "team", "values", "stats", "pricing", "priorities", "locations", "blog", "faq"],
    # product showcase: capabilities, visuals, specs/stats, price
    "showcase": ["features", "gallery", "stats", "process", "pricing", "testimonials", "team", "about", "values", "priorities", "locations", "blog", "faq", "manifesto"],
    # loud/kinetic: visuals and voice early, social proof before price
    "loud": ["gallery", "manifesto", "features", "testimonials", "stats", "team", "pricing", "process", "about", "values", "priorities", "locations", "blog", "faq"],
    # devtool/docs: how it works, then specs, then price, FAQ before proof
    "tool": ["features", "process", "stats", "pricing", "faq", "testimonials", "about", "team", "values", "priorities", "gallery", "locations", "blog", "manifesto"],
    # calm service: tasks first, steps, contacts and FAQ prominent
    "service": ["features", "process", "faq", "locations", "pricing", "team", "testimonials", "about", "stats", "values", "priorities", "gallery", "blog", "manifesto"],
}
CANON_FAMILY: dict[str, str] = {
    "01_bento_grid": "showcase", "02_swiss_international": "proof", "03_editorial_magazine": "story",
    "04_hyper_minimal_speed": "tool", "05_kinetic_typography": "loud", "06_neo_brutalism": "loud",
    "07_avant_garde_poster": "loud", "08_liquid_glass": "showcase", "09_aurora_obsidian_mesh": "showcase",
    "10_industrial_tactile": "showcase", "11_soft_clay_playful": "loud", "12_quiet_luxury_minimal": "story",
    "13_cinematic_documentary": "story", "14_spatial_3d_showcase": "showcase", "15_organic_biophilic_eco": "story",
    "16_artisan_craft_zine": "story", "17_fintech_institutional": "proof", "18_devtool_command_ui": "tool",
    "19_calm_human_accessible": "service", "20_maximalist_collage_pop": "loud",
}


def _pin(blocks: list[str], order: list[str]) -> list[str]:
    first = [b for b in _PINNED_FIRST if b in blocks]
    last = [b for b in _PINNED_LAST if b in blocks]
    middle = [b for b in order if b in blocks and b not in first and b not in last]
    middle += [b for b in blocks if b not in middle and b not in first and b not in last]
    return list(dict.fromkeys(first + middle + last))


def deterministic_page_plan(
    canon_id: str, slug: str, blocks: list[str], dossier: dict[str, Any], page_idx: int, keep_order: bool = False
) -> dict[str, Any]:
    """Fallback plan. keep_order=True when the orchestrator site_plan already ordered the blocks (LLM decision wins)."""
    fam = CANON_FAMILY.get(canon_id, "showcase")
    pref = list(blocks) if keep_order else _FAMILY_ORDER[fam]
    order = _pin(list(blocks), pref)
    allowed = dossier.get("variants") or {}
    variants: dict[str, str] = {}
    for i, bid in enumerate(order):
        opts = allowed.get(bid) or []
        if opts:
            variants[bid] = str(opts[page_idx % len(opts)])
    return {"order": order, "variants": variants, "family": fam, "source": "deterministic"}


def validate_page_plan(raw: Any, blocks: list[str], dossier: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    """Schema check: order is a permutation of the page's blocks (pins enforced), variants are allowed ids."""
    if not isinstance(raw, dict):
        return fallback
    raw_order = [str(x).strip().lower() for x in (raw.get("order") or []) if str(x).strip()]
    known = [b for b in raw_order if b in blocks]
    if len(set(known)) < max(1, len([b for b in blocks if b not in _PINNED_FIRST + _PINNED_LAST]) // 2):
        order = fallback["order"]
    else:
        order = _pin(list(blocks), list(dict.fromkeys(known)) + fallback["order"])
    allowed = dossier.get("variants") or {}
    variants = dict(fallback.get("variants") or {})
    for k, v in (raw.get("variants") or {}).items() if isinstance(raw.get("variants"), dict) else []:
        k_s, v_s = str(k).strip().lower(), str(v).strip()
        if k_s in order and v_s in (allowed.get(k_s) or []):
            variants[k_s] = v_s
    return {"order": order, "variants": variants, "family": fallback.get("family"), "source": "llm",
            "rationale": str(raw.get("rationale") or "")[:300]}


def composition_schema_example(pages: list[str]) -> str:
    return json.dumps({"pages": {s: {"order": ["hero", "..."], "variants": {"block_id": "allowed variant"}, "rationale": "one sentence"} for s in pages[:2]}}, ensure_ascii=False)


GALLERY_COUNT = {"bento_mosaic": 5, "collage_stagger": 5, "horizontal_filmstrip": 5, "editorial_grid": 4, "cinematic_spotlight": 3}
GALLERY_FRAMES = [
    "wide establishing view of the flagship work in its real environment",
    "tight macro close-up of materials, texture and craft detail",
    "candid documentary scene of people using or making it, faces not the focus",
    "clean still life of the product or key object on a canon-coloured surface",
    "the same world at a different time of day or season, contrasting light",
    "overhead flat-lay of tools, materials and small objects of the trade",
]


def gallery_count(canon_id: str, dossier: dict[str, Any], composition: dict[str, Any] | None = None) -> int:
    """How many gallery images this canon/brief needs (3-6), driven by the chosen gallery layout."""
    variant = ""
    for plan in ((composition or {}).get("pages") or {}).values():
        variant = str((plan.get("variants") or {}).get("gallery") or "")
        if variant:
            break
    if not variant:
        variant = str(((dossier.get("variants") or {}).get("gallery") or [""])[0])
    return max(3, min(6, GALLERY_COUNT.get(variant, 4)))


def distinct_list(items: list[str], n: int, fallback: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in list(items) + list(fallback):
        k = x.strip().lower()[:80]
        if x.strip() and k not in seen:
            seen.add(k)
            out.append(x.strip())
        if len(out) >= n:
            break
    return out
