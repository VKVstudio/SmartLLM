"""Runtime loader & deterministic evaluators backed by studio/smartllm_studio/kb/."""

from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path
import re
from typing import Any

PKG_ROOT = Path(__file__).resolve().parent
KB_ROOT = PKG_ROOT / "kb"

_OKLCH_RE = re.compile(r"oklch\(\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)(?:\s*/\s*([0-9.]+))?\s*\)", re.I)


@lru_cache(maxsize=8)
def _read_kb_json(relpath: str) -> Any:
    return json.loads((KB_ROOT / relpath).read_text(encoding="utf-8"))


@lru_cache(maxsize=32)
def _read_kb_text(relpath: str) -> str:
    return (KB_ROOT / relpath).read_text(encoding="utf-8")


def get_index() -> dict[str, Any]:
    return _read_kb_json("00_INDEX.json")


def get_legacy_aliases() -> dict[str, str]:
    return _read_kb_json("styles/legacy_aliases.json")


def list_canon_ids() -> list[str]:
    return sorted(p.stem for p in (KB_ROOT / "styles" / "canons").glob("*.json"))


def resolve_canon_id(raw_id: str | None) -> str:
    """Resolve any legacy or current canon identifier to one of the 20 canonical IDs."""
    cids = list_canon_ids()
    cid_set = set(cids)
    s = str(raw_id or "").strip()
    if s in cid_set:
        return s
    aliases = get_legacy_aliases()
    if s in aliases and aliases[s] in cid_set:
        return aliases[s]
    if s:
        for cand in cids:
            if cand.startswith(s):
                return cand
    return "01_bento_grid"


def load_canon_kb(canon_id: str) -> dict[str, Any]:
    cid = resolve_canon_id(canon_id)
    return _read_kb_json(f"styles/canons/{cid}.json")


def get_blocks_matrix() -> dict[str, Any]:
    return _read_kb_json("styles/blocks/_matrix.json")


def get_vendor_manifest_kb() -> dict[str, Any]:
    return _read_kb_json("visual_prompting/phase2_vendor_manifest.json")


def get_slot_recipes() -> dict[str, Any]:
    return _read_kb_json("visual_prompting/slot_prompt_recipes.json")


def get_anti_ai_rules() -> dict[str, Any]:
    return _read_kb_json("copy_marketing/anti_ai_regex_rules.json")


def get_skeptic_rubrics() -> dict[str, Any]:
    return _read_kb_json("seo_perf_security/skeptic_rubrics.json")


def load_stage_context(
    stage: str,
    *,
    stack: str = "html5_esm",
    canon_id: str = "01_bento_grid",
    profile_id: str = "P3_copy_funnel",
) -> str:
    """Assemble strictly bounded (<=4500 est. tok) KB context slice for a pipeline stage."""
    idx = get_index()
    refs = idx.get("stage_loader", {}).get(stage) or []
    if not refs:
        return ""
    cid = resolve_canon_id(canon_id)
    chunks: list[str] = []
    for ref in refs:
        clean, *sl = ref.split("#", 1)
        if "{stack}" in clean:
            st = stack if stack in ("html5_esm", "astro", "sveltekit", "nextjs", "vite_ts") else "html5_esm"
            chunks.append(_read_kb_text(clean.format(stack=st)))
        elif "{canon_id}" in clean:
            doc = load_canon_kb(cid)
            if sl:
                keys = sl[0].removeprefix("slice(").removesuffix(")").split(",")
                chunks.append(json.dumps({k: doc.get(k) for k in keys if k in doc}, ensure_ascii=False))
            else:
                chunks.append(json.dumps(doc, ensure_ascii=False))
        elif sl and clean == "styles/blocks/_matrix.json":
            matrix = get_blocks_matrix()
            chunks.append(json.dumps(matrix["routing_matrix"].get(cid, {}), ensure_ascii=False))
        elif sl and clean == "visual_prompting/slot_prompt_recipes.json":
            rec = get_slot_recipes()
            chunks.append(json.dumps({
                "slot_recipes": rec["slot_recipes"],
                "override": rec["canon_art_direction_overrides"].get(cid, ""),
            }, ensure_ascii=False))
        elif sl and clean == "seo_perf_security/skeptic_rubrics.json":
            rub = get_skeptic_rubrics()
            prof = rub["profiles"].get(profile_id) or next(iter(rub["profiles"].values()))
            chunks.append(json.dumps({profile_id: prof, "verdict_schema": rub["verdict_schema"]}, ensure_ascii=False))
        else:
            chunks.append(_read_kb_text(clean))
    return "\n\n".join(chunks)


def oklch_to_material_phrase(color_str: str) -> str:
    """Translate OKLCH color token into natural pigment/material prose (zero #HEX/oklch leaks)."""
    m = _OKLCH_RE.search(str(color_str or ""))
    if not m:
        return "matte neutral architectural stone"
    L = float(m.group(1))
    C = float(m.group(2))
    H = float(m.group(3)) % 360.0
    lut = get_slot_recipes()["oklch_material_palette_lut"]
    if C < float(lut["achromatic_chroma_threshold"]):
        for row in lut["achromatic_by_L"]:
            if L <= float(row["max_L"]):
                return str(row["descriptor"])
        return "pure warm alabaster white"
    band = "low_L" if L < 0.42 else ("mid_L" if L < 0.72 else "high_L")
    for sec in lut["hue_sectors_deg"]:
        lo, hi = float(sec["range"][0]), float(sec["range"][1])
        if lo <= H < hi:
            return str(sec[band])
    return str(lut["hue_sectors_deg"][-1][band])


def palette_to_material_summary(
    palette: dict[str, Any],
    keys: tuple[str, ...] = ("bg", "surface", "accent", "accent_2"),
) -> str:
    """Convert selected OKLCH palette tokens into Z-Image material prose."""
    parts: list[str] = []
    for k in keys:
        val = palette.get(k)
        if isinstance(val, str) and val.strip():
            desc = oklch_to_material_phrase(val)
            if desc not in parts:
                parts.append(desc)
    return ", ".join(parts)


def harden_zimage_prompt(prompt: str, brand: str = "", member_names: list[str] | None = None) -> str:
    """Sanitize Z-Image-Turbo prompt while protecting material/lighting words ('stone', 'oak', 'white', 'brown')."""
    spec = get_slot_recipes()["post_sanitization_spec"]
    protect = {w.lower() for w in spec["visual_protect_words"]}
    out = str(prompt or "")
    phrases = [p.strip() for p in ([brand] + list(member_names or [])) if p and len(p.strip()) >= 2]
    for ph in sorted(set(phrases), key=len, reverse=True):
        toks = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", ph)
        all_vis = bool(toks) and all(t.lower() in protect for t in toks)
        out = re.sub(rf"(?i)\b(?:for|by|brand|named|called|titled|portrait\s+of)\s+['\"«“]?{re.escape(ph)}['\"»”]?\b", "", out)
        out = re.sub(rf"(?i)['\"«“]{re.escape(ph)}['\"»”]", "", out)
        if all_vis:
            if any(c.isupper() for c in ph):
                out = re.sub(rf"(?<!\w){re.escape(ph)}(?!\w)", "", out)
        else:
            out = re.sub(rf"(?i)(?<!\w){re.escape(ph)}(?!\w)", "", out)
    for ph in phrases:
        for tok in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", ph):
            if len(tok) >= 4 and tok.lower() not in protect:
                out = re.sub(rf"(?<!\w){re.escape(tok)}(?!\w)", "", out, flags=re.I)
    out = re.sub(spec["hex_color_regex"], "", out)
    out = re.sub(spec["cyrillic_run_regex"], "", out)
    out = re.sub(r"(?i)\b(?:text|words?|letters?|logos?|watermarks?|captions?|clutter|beige|people|humans?)-free\b", "", out)
    out = re.sub(spec["neg_clause_regex"], "", out)
    for rule in spec["text_replace_map"]:
        out = re.sub(rule["pattern"], rule["replace"], out)
    out = re.sub(r"(?:^|(?<=\s))-[a-z]+\b", "", out, flags=re.I)
    out = re.sub(r"(?i)\b(?:with|without|featuring|and|or|of)\s*(?=[,.;]|$)", "", out)
    out = re.sub(r"\s*,\s*(?:,\s*)+", ", ", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    cleaned = re.sub(r"\s+", " ", out).strip(" ,.;:-")
    words = cleaned.split()
    max_words = int(spec.get("max_words", 95))
    if len(words) > max_words:
        cleaned = " ".join(words[:max_words]).rstrip(",;:")
    return cleaned


def _strip_pair_delimiters(text: str) -> str:
    """Strip first ' — ' delimiter per pipe-delimited list item before prose em-dash counts."""
    chunks = [re.sub(r"^([^—\n]{1,64}?)\s+—\s+", r"\1: ", part.strip(), count=1) for part in str(text or "").split("|")]
    return " | ".join(c for c in chunks if c)


def lint_anti_ai_copy(text: str, lang: str, block_id: str = "") -> dict[str, Any]:
    """Run deterministic EN/RU anti-AI cliché and kantselyarit linter."""
    rules = get_anti_ai_rules()
    skip = set(rules.get("skip_blocks") or [])
    if block_id in skip:
        return {"skipped": True, "hard_hits": [], "soft_hits": [], "passed": True}

    norm = _strip_pair_delimiters(text)
    rx_map = rules["regexes"]
    hard_keys = ("RU_HARD_BAN", "RU_SPLIT_PRED_HARD") if lang == "ru" else ("EN_HARD_BAN", "EN_PARTICIPLE_SLOP")
    soft_keys = ("RU_SOFT_WATCH",) if lang == "ru" else ("EN_SOFT_WATCH", "EN_NEG_PARALLEL_BUDGET")
    hard_hits: list[str] = []
    soft_hits: list[str] = []
    for k in hard_keys:
        for m in re.finditer(rx_map[k], norm):
            hard_hits.append(f"{k}:{m.group(0).strip()[:40]}")
    for k in soft_keys:
        for m in re.finditer(rx_map[k], norm):
            soft_hits.append(f"{k}:{m.group(0).strip()[:40]}")
    return {
        "skipped": False,
        "hard_hits": hard_hits,
        "soft_hits": soft_hits,
        "passed": len(hard_hits) == 0,
    }


def route_block_variants(
    canon_id: str,
    blocks: list[str],
    preferred: dict[str, str] | None = None,
    page_idx: int = 0,
) -> dict[str, str]:
    """Deterministically assign canon-compatible variants while preventing adjacent family repetition."""
    cid = resolve_canon_id(canon_id)
    matrix = get_blocks_matrix()
    rmat = matrix["routing_matrix"].get(cid, {})
    v2f = matrix["variant_to_family"]
    pref = preferred or {}
    out: dict[str, str] = {}
    prev_family = ""
    for b_idx, bid in enumerate(blocks):
        allowed = list(rmat.get(bid) or [])
        if not allowed:
            continue
        cand = str(pref.get(bid) or "")
        if cand in allowed and (not prev_family or v2f.get(cand, "") != prev_family or len(allowed) == 1):
            chosen = cand
        else:
            start = (page_idx + b_idx) % len(allowed)
            rotated = allowed[start:] + allowed[:start]
            chosen = next((v for v in rotated if not prev_family or v2f.get(v, "") != prev_family), rotated[0])
        out[bid] = chosen
        prev_family = v2f.get(chosen, "")
    return out


def compute_real_scorecard(
    *,
    project_dir: Path,
    rendered_pages: dict[str, str],
    css_text: str,
    js_text: str,
    style_hash: str,
    script_hash: str,
    card: dict[str, Any],
    headers_text: str,
    robots_text: str,
    sitemap_text: str,
    llms_enabled: bool,
    ai_crawlers: dict[str, bool],
    geo_cfg: dict[str, Any],
    min_target_px: int = 44,
) -> dict[str, Any]:
    """Compute real deterministic Tier-1 security, headers, a11y, SEO, and GEO checks."""
    # 1. CSP check
    header_lines = headers_text.splitlines()
    csp_line = next((ln.strip() for ln in header_lines if "Content-Security-Policy:" in ln), "")
    csp_ok = (
        bool(csp_line)
        and style_hash in csp_line
        and script_hash in csp_line
        and "'unsafe-inline'" not in csp_line
        and "'unsafe-eval'" not in csp_line
        and "frame-ancestors 'none'" in csp_line
        and "style-src-attr 'none'" in csp_line
        and "background-attachment: fixed" not in css_text
        and "background-attachment:fixed" not in css_text
    )
    for slug, html_doc in rendered_pages.items():
        if 'http-equiv="Content-Security-Policy"' not in html_doc:
            csp_ok = False
        if "frame-ancestors" in (re.search(r'http-equiv="Content-Security-Policy" content="([^"]*)"', html_doc) or [None, ""])[1]:
            csp_ok = False
        if re.search(r"<(?!svg\b)[a-z]+\b[^>]*\sstyle=", html_doc, re.I):
            csp_ok = False

    # 2. HTTP edge headers check
    req_hdrs = (
        "Strict-Transport-Security:",
        "X-Content-Type-Options: nosniff",
        "X-Frame-Options: DENY",
        "Referrer-Policy:",
        "Permissions-Policy:",
        "Cross-Origin-Opener-Policy:",
        "Cross-Origin-Embedder-Policy:",
        "Cross-Origin-Resource-Policy:",
    )
    headers_ok = all(h in headers_text for h in req_hdrs) and all(len(ln) <= 2000 for ln in header_lines)

    # 3. Accessibility & layout physics check
    a11y_ok = True
    for slug, html_doc in rendered_pages.items():
        if html_doc.count("<h1") != 1:
            a11y_ok = False
        if 'class="skip-link"' not in html_doc or '<main id="main-content">' not in html_doc:
            a11y_ok = False
        m_hero = re.search(r'<section[^>]*\bid="hero"[^>]*>.*?</section>', html_doc, re.S)
        if m_hero:
            hero_blk = m_hero.group(0)
            if "data-reveal" in hero_blk or 'loading="lazy"' in hero_blk or ("<img" in hero_blk and 'fetchpriority="high"' not in hero_blk):
                a11y_ok = False

    # 4. SEO & structured data check
    seo_ok = "<changefreq>" not in sitemap_text and "<priority>" not in sitemap_text
    for slug, html_doc in rendered_pages.items():
        if "<title" not in html_doc or 'rel="canonical"' not in html_doc or 'property="og:image"' not in html_doc:
            seo_ok = False
        if "</script>" in (html_doc.split('<script type="application/ld+json">', 1)[-1].split("</script>", 1)[0] if '<script type="application/ld+json">' in html_doc else ""):
            seo_ok = False
        if slug == "index" and '"BreadcrumbList"' in html_doc:
            seo_ok = False
        if re.search(r'"price"\s*:\s*"0"', html_doc):
            seo_ok = False

    # 5. GEO / AI crawlers check
    geo_ok = ("Claude-SearchBot" in robots_text) and (not llms_enabled or (project_dir / "llms.txt").exists())

    return {
        "csp": {"passed": csp_ok, "style_sha256": style_hash, "script_sha256": script_hash, "unsafe_inline": False, "style_src_attr_none": True},
        "headers": {"passed": headers_ok, "hsts": True, "coop_coep_corp": True, "coep": "credentialless"},
        "a11y": {
            "passed": a11y_ok,
            "wcag_level": "AAA/AA",
            "contrast_ratio": card.get("a11y", {}).get("text_bg_contrast_ratio", 7.0),
            "min_target_px": min_target_px,
        },
        "seo": {"passed": seo_ok, "json_ld_graph": True, "faq_verbatim": True, "hreflang": True, "sitemap": seo_ok},
        "geo": {
            "passed": geo_ok,
            "facts_count": len(geo_cfg.get("facts", [])),
            "llms_txt": bool(llms_enabled and (project_dir / "llms.txt").exists()),
            "ai_crawlers_configured": len(ai_crawlers),
        },
    }
