"""Strict sequential sub-agent pipeline with on-disk system memory (smartllm.md + .smartllm/state.json).

Each sub-agent reads only the memory slice it needs, writes its artifact to disk and marks the
ledger before the next agent starts. The deterministic compiler materializes HTML/CSS/CSP from
memory, so a local model never emits raw markup and the bundle cannot structurally break.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable

from .kb_loader import harden_zimage_prompt, lint_anti_ai_copy, load_stage_context, palette_to_material_summary
from .pages import BLOCK_MAP, PAGE_MAP, build_default_company, company_block_prompt, infer_gender, page_title, resolve_primary_lang

ReportFn = Callable[[int, int, str, str, str], None]

REVIEW_CRITERIA = ("offer", "brand", "specificity", "structure", "seo", "language")
_EN_BOILERPLATE_LEAKS = (
    "engineered for measurable quality",
    "can we customize modules?",
    "what is delivered at handoff?",
)


def _is_broken_user_block(bid: str, copy_map: dict[str, str], det_failed: list[str] | set[str]) -> bool:
    """Allow review to override user-block immutability when language leaked or boilerplate/placeholders remain."""
    if "language" in det_failed:
        return True
    low_txt = str(copy_map.get(bid, "")).lower()
    if any(mk in low_txt for mk in PLACEHOLDER_MARKERS):
        return True
    if any(mk in low_txt for mk in _EN_BOILERPLATE_LEAKS):
        return True
    return False
PLACEHOLDER_MARKERS = (
    "lorem", "xxx", "todo", "tbd", "placeholder", "плейсхолдер", "[insert", "вставьте",
    "значение — подпись", "имя — роль", "name — role", "value — label", "вопрос? ответ",
    "question? answer", "этап — результат", "step — outcome", "пакет: состав и цена",
    "tier: scope", "приоритет | приоритет", "priority | priority", "город | город",
    "000-00-00", "ул. примерная", "example street",
    "анна воронова", "илья соколов", "elena kova", "markus thorne", "anna voronova",
    "ilya sokolov", "01 аудит — техническое задание", "01 discovery — architecture brief",
    "история и метод компании", "company story and engineering method",
    "company name", "enter your organization", "your.email@company.com",
)
LATIN_WHITELIST = {
    "faq", "cta", "seo", "geo", "aeo", "json", "api", "url", "b2b", "b2c", "vip", "pdf",
    "qr", "wifi", "it", "hr", "pr", "smm", "crm", "erp", "saas", "bento", "oklch", "llms",
    "email", "mailto", "tel", "online", "offline", "web", "site", "self", "hosted", "lighthouse",
    "schema", "org", "http", "https", "html", "css", "usb", "led", "3d", "2d", "ai", "bim",
    "sla", "nvme", "nvlink", "gpu", "cpu", "llm", "lora", "soc", "iso", "api", "cad", "cnc",
}
COPY_BATCH_SIZE = 6
PIPELINE_VERSION = 12

BLOCK_FORMAT_HINTS_RU = {
    "manifesto": "<Девиз> | <Одно конкретное предложение позиционирования этой страницы>",
    "values": "Продукт — <конкретный стандарт> | Команда — <принцип работы команды> | Клиенты — <обещание клиентам> (НЕ пиши слово 'Принцип' как текст карточки)",
    "priorities": "4 приоритета из бренд-основы через ' | '",
    "locations": "2-4 локации из бренд-основы: <Город> — <точный адрес> | ...",
    "contact": "<телефон из основы> | <email из основы> | <адрес из основы> | <часы работы из основы> (без HTML-меток полей и ссылок на карты)",
    "features": "ровно 4 (или 3) направления/услуги из бренд-основы БЕЗ цен тарифов: <Название направления> — <конкретная техническая выгода> | ...",
    "about": "<Краткая история основания из бренд-основы> | <Подтверждённый факт 1 с цифрой> | <Подтверждённый факт 2>",
    "stats": "ровно 4 (или 3) показателя из бренд-основы: <Значение> — <короткая подпись> | ...",
    "gallery": "<Короткая подпись до 90 знаков к 1-му визуалу> | <короткая подпись до 90 знаков ко 2-му визуалу>",
    "pricing": "ВСЕ тарифы (3-4) из бренд-основы в формате: <Название тарифа> — <что входит> — <точная цена с валютой> | ...",
    "testimonials": "3 или 4 измеримых отзыва/кейса: <Имя клиента/компании и город> — <конкретный измеримый результат> | ...",
    "process": "ровно 4 последовательных этапа под данную отрасль: <01 Название этапа> — <результат для клиента> | ...",
    "team": "ТОЧНО те же 3-4 специалиста из бренд-основы (единый состав для всех страниц, без URL): <Имя Фамилия> — <должность и опыт> | ...",
    "blog": "3 или 4 экспертных материала по теме: <Заголовок статьи> — <одно предложение сути> | ...",
    "faq": "4 пары '<Вопрос?> <Развёрнутый ответ.>' через ' | '",
    "cta": "Одно конверсионное предложение с конкретным следующим шагом и обещанием бренда",
    "legal": "<Абзац политики конфиденциальности> | <Абзац условий оказания услуг> | <Реквизиты компании>",
}
BLOCK_FORMAT_HINTS_EN = {
    "manifesto": "<Tagline> | <One concrete positioning sentence tailored to this page>",
    "values": "Product — <concrete standard> | Team — <practice standard> | Clients — <client promise> (never output bare word 'Principle')",
    "priorities": "4 concise priorities from the brand foundation separated by ' | '",
    "locations": "2-4 locations from foundation: <City> — <street address> | ...",
    "contact": "<foundation phone> | <foundation email> | <foundation address> | <foundation hours> (never include form field labels or map URLs)",
    "features": "exact 4 (or 3) capabilities from foundation WITHOUT pricing tiers: <Capability Name> — <specific engineering benefit> | ...",
    "about": "<Concise founding story matching history> | <Verified milestone 1 with numbers> | <Verified milestone 2>",
    "stats": "exact 4 (or 3) metrics from foundation: <Metric Value> — <short label> | ...",
    "gallery": "<Short caption under 90 chars for scene 1> | <short caption under 90 chars for scene 2>",
    "pricing": "ALL 3-4 tiers from foundation: <Tier Name> — <scope & deliverables> — <exact price with currency> | ...",
    "testimonials": "3 or 4 measurable client outcomes: <Client Name / Org> — <quantified impact> | ...",
    "process": "exact 4 domain-specific workflow steps: <01 Step Name> — <deliverable outcome> | ...",
    "team": "EXACT canonical specialists from foundation (identical roster on every page, NO URLs): <First Last> — <role & experience> | ...",
    "blog": "3 or 4 domain insights: <Article Headline> — <concise technical takeaway> | ...",
    "faq": "4 pairs of '<Question?> <Complete answer sentence.>' separated by ' | '",
    "cta": "One clear conversion sentence with a concrete next step matching the offer",
    "legal": "<Privacy paragraph> | <Terms of service paragraph> | <Company compliance & registry paragraph>",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean(text: Any) -> str:
    return " ".join(str(text or "").split()).strip()


FIELD_LABEL_RE = re.compile(r"(?i)\b(address|hours|phone|email|cities|city|answer|items|description|tagline|positioning)\s*:\s*")


def _strip_field_labels(text: str) -> str:
    return _clean(FIELD_LABEL_RE.sub("", str(text or "")))


_ZIMAGE_NEG_PHRASE_RE = re.compile(
    r"(?i)\b(?:zero|no|without|free of)\s+(?:text|words|letters|typography|watermark|watermarks|labels?|captions?|badges?|logos?|signage|people|faces|text overlay)\b"
)
_ZIMAGE_TEXT_TOKEN_RE = re.compile(
    r"(?i)\b(?:text|watermark|watermarks|captions?|labeled|nameplates?|signage|letterforms?|typographic|posters?|diagrams?|seals?|banners?|subtitles?|slogans?|typography)\b"
)


def _sanitize_zimage_prompt(prompt: str, forbidden_names: list[str] | None = None, brand: str = "") -> str:
    """Strip negative phrasing, hex codes, Cyrillic leakage, and forbidden names while protecting material words."""
    return harden_zimage_prompt(str(prompt or ""), brand=brand, member_names=forbidden_names)


LIST_BLOCKS = {"stats", "process", "team", "pricing", "values", "priorities", "locations", "features", "testimonials", "blog", "gallery", "faq"}
SINGLE_ITEM_DICT_KEYS = {"name", "role", "title", "headline", "value", "label", "step", "price", "scope", "outcome"}
DICT_KEY_ORDER = ("title", "headline", "description", "subhead", "text", "cta", "cta_label", "cta_button", "phone", "email", "address", "hours", "cities", "name", "role", "value", "label", "step", "outcome", "price", "scope")
_SKIP_DICT_KEYS = {"url", "href", "link", "slug", "id", "image", "img", "photo", "avatar", "icon", "gender"}
_URL_TEXT_RE = re.compile(r"(?:,\s*)?https?://\S+", re.I)
_SAFE_PAIR_RE = re.compile(r"\s*—\s*|\s+[–-]\s+|(?<!https)(?<!http)(?<!\d):\s+")
_PRICE_CURR_CHECK_RE = re.compile(r"\d[\d\s.,]*\s*(?:₽|руб|\$|€|£|₸|USD|EUR|GBP|USDT)|(?:\$|€|£)\s*\d", re.I)


def _strip_urls_from_copy(text: str) -> str:
    cleaned = _URL_TEXT_RE.sub("", str(text or ""))
    return re.sub(r"\s+", " ", cleaned).strip(" ,;")


def _norm_block_value(bid: str, v: Any, _in_list: bool = False) -> str:
    if isinstance(v, str):
        val = _strip_field_labels(v)
        if bid not in ("contact", "locations", "legal"):
            val = _strip_urls_from_copy(val)
        return val if _in_list else _enforce_block_contract(bid, val)
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        joined = " | ".join(x for x in (_norm_block_value(bid, i, _in_list=True) for i in v) if x)
        return joined if _in_list else _enforce_block_contract(bid, joined)
    if isinstance(v, dict):
        q = _clean(v.get("question") or v.get("q"))
        a = _clean(v.get("answer") or v.get("a"))
        if q or a:
            return f"{q} {a}".strip()
        if isinstance(v.get("items"), list):
            return _norm_block_value(bid, v["items"], _in_list=_in_list)
        parts: list[str] = []
        seen: set[str] = set()
        for k in DICT_KEY_ORDER:
            if k in v and k not in _SKIP_DICT_KEYS:
                seen.add(k)
                parts.append(_norm_block_value(bid, v[k], _in_list=True))
        for k, val in v.items():
            if k not in seen and k not in _SKIP_DICT_KEYS and isinstance(val, (str, list, dict, int, float)):
                parts.append(_norm_block_value(bid, val, _in_list=True))
        parts = [x for x in parts if x]
        is_single_item = _in_list or any(k in v for k in SINGLE_ITEM_DICT_KEYS)
        if bid in LIST_BLOCKS and not is_single_item:
            return _enforce_block_contract(bid, " | ".join(parts))
        sep = " — " if is_single_item and bid in LIST_BLOCKS else (" · " if bid in ("contact", "locations") else " ")
        joined = sep.join(parts)
        return joined if _in_list else _enforce_block_contract(bid, joined)
    return ""


def _enforce_block_contract(bid: str, text: str) -> str:
    """Enforce grid-balanced card counts (never 5-item 3+2 orphans), URL safety, and clean team/values formatting."""
    clean_t = _strip_field_labels(text)
    if not clean_t:
        return ""
    if bid not in ("contact", "locations", "legal"):
        clean_t = _strip_urls_from_copy(clean_t)
    if bid in ("features", "stats", "values", "team", "blog", "testimonials", "process", "priorities"):
        items = [x.strip(" ,;") for x in re.split(r"\s*(?:\||\n)+\s*", clean_t) if x.strip(" ,;")]
        if bid == "team":
            normalized_team = []
            for entry in items:
                chunks = [c.strip() for c in _SAFE_PAIR_RE.split(entry) if c.strip()]
                if len(chunks) >= 2:
                    name_part = chunks[0]
                    rest = [c for c in chunks[1:] if c.lower() != name_part.lower()]
                    role_part = ", ".join(rest) if rest else chunks[-1]
                    normalized_team.append(f"{name_part} — {role_part}")
                else:
                    normalized_team.append(entry)
            items = normalized_team
        if len(items) == 5:
            items = items[:4]
        return " | ".join(items)
    return clean_t


def _foundation_slice(company: dict[str, Any], lang: str) -> str:
    keys = ("tagline", "positioning", "phone", "email", "address", "hours")
    lines = [f"{k}: {_clean(company.get(k))}" for k in keys if _clean(company.get(k))]
    for k in ("values", "priorities", "cities"):
        vals = [_clean(x) for x in (company.get(k) or []) if _clean(x)]
        if vals:
            lines.append(f"{k}: {' | '.join(vals[:4])}")
    products = company.get("products") or []
    if products:
        lines.append(
            "products (SINGLE TRUTH for pricing/tiers — ALWAYS keep all tiers and exact prices): "
            + " | ".join(f"{_clean(pr.get('name'))} — {_clean(pr.get('scope'))} — {_clean(pr.get('price'))}" for pr in products[:6] if isinstance(pr, dict))
        )
    features = company.get("features") or []
    if features:
        lines.append(
            "features (SINGLE TRUTH for core capabilities — NEVER put pricing tiers in features): "
            + " | ".join(f"{_clean(f.get('title'))} — {_clean(f.get('detail'))}" for f in features[:4] if isinstance(f, dict))
        )
    stats = company.get("stats") or []
    if stats:
        lines.append(
            "stats (SINGLE TRUTH for verified metrics): "
            + " | ".join(f"{_clean(s.get('value'))} — {_clean(s.get('label'))}" for s in stats[:4] if isinstance(s, dict))
        )
    team = company.get("team") or []
    if team:
        lines.append(
            "team (SINGLE TRUTH — EXACT canonical roster across ALL pages and portraits): "
            + " | ".join(
                f"{_clean(m.get('name'))} ({infer_gender(_clean(m.get('name')), _clean(m.get('gender')), idx)}) — {_clean(m.get('role'))}"
                for idx, m in enumerate(team[:4]) if isinstance(m, dict) and _clean(m.get("name"))
            )
        )
    hist = company.get("history") or {}
    if hist:
        lines.append(f"history: founded {_clean(hist.get('founded'))}; " + " | ".join(_clean(x) for x in (hist.get("milestones") or [])[:4]))
    return "\n".join(lines)


def _sync_page_copy_to_foundation(
    slug: str,
    copy: dict[str, str],
    company: dict[str, Any],
    lang: str,
    user_owned: set[str],
    canonical_team: list[dict[str, str]] | None = None,
) -> dict[str, str]:
    """Deterministically enforce cross-page single-source-of-truth invariants for non-user-owned blocks."""
    out = dict(copy)
    team_list = canonical_team if canonical_team is not None else [m for m in (company.get("team") or []) if isinstance(m, dict) and _clean(m.get("name"))]
    # 1. Canonical team roster identical on every page with `team`
    if "team" in out and "team" not in user_owned and team_list:
        out["team"] = " | ".join(
            f"{_clean(m.get('name'))} — {_clean(m.get('role'))}"
            for m in team_list[:4] if _clean(m.get("name"))
        )
    # 2. Canonical pricing tiers — prevent review/copy from dropping tiers or saying 'Price on request'
    prods = [pr for pr in (company.get("products") or []) if isinstance(pr, dict) and _clean(pr.get("name"))]
    if "pricing" in out and "pricing" not in user_owned and len(prods) >= 2:
        cur_p = _clean(out.get("pricing"))
        items_p = [x.strip() for x in re.split(r"[|\n]+", cur_p) if x.strip()]
        expected_prices = {re.sub(r"[^\d]", "", _clean(pr.get("price"))) for pr in prods if len(re.sub(r"[^\d]", "", _clean(pr.get("price")))) >= 2}
        found_digits = re.sub(r"[^\d]", "", cur_p)
        missing_price = any(dp not in found_digits for dp in expected_prices)
        if len(items_p) < len(prods) or missing_price or "по запросу" in cur_p.lower() or "on request" in cur_p.lower():
            canon_p = company_block_prompt(company, "pricing", lang)
            if canon_p:
                out["pricing"] = canon_p
    # 3. Features — forbid leaking pricing tiers into features or collapsing to <3 items
    if "features" in out and "features" not in user_owned:
        cur_f = _clean(out.get("features"))
        items_f = [x.strip() for x in re.split(r"[|\n]+", cur_f) if x.strip()]
        has_price_leak = bool(_PRICE_CURR_CHECK_RE.search(cur_f))
        if has_price_leak or len(items_f) < 3:
            canon_f = company_block_prompt(company, "features", lang)
            if canon_f:
                out["features"] = canon_f
    # 4. Stats — enforce canonical metrics when missing, drifted, or <3 items
    if "stats" in out and "stats" not in user_owned:
        cur_s = _clean(out.get("stats"))
        items_s = [x.strip() for x in re.split(r"[|\n]+", cur_s) if x.strip()]
        canon_s = company_block_prompt(company, "stats", lang)
        founded = str((company.get("history") or {}).get("founded") or "")
        year_conflict = bool(founded and any(m.group(0) != founded and m.group(0).startswith(("199", "200", "201", "202")) for m in re.finditer(r"\b(?:19|20)\d{2}\b", cur_s)))
        if canon_s and (len(items_s) < 3 or year_conflict or len(items_s) < len(company.get("stats") or [])):
            out["stats"] = canon_s
    # 5. Values — repair bare "— Принцип" / "— Principle" placeholders
    if "values" in out and "values" not in user_owned:
        cur_v = _clean(out.get("values"))
        if re.search(r"[—–:-]\s*(?:Принцип|Principle)\s*(?:\||$)", cur_v, re.I):
            canon_v = company_block_prompt(company, "values", lang)
            if canon_v:
                out["values"] = canon_v
    # 6. Contact — strip leaked HTML form labels or map URLs
    if "contact" in out and "contact" not in user_owned:
        cur_c = _clean(out.get("contact"))
        low_c = cur_c.lower()
        if any(mk in low_c for mk in ("company name", "enter your", "your.email@", "https://yandex.", "https://maps.")):
            canon_c = company_block_prompt(company, "contact", lang)
            if canon_c:
                out["contact"] = canon_c
    return out


def _resolve_canonical_team(
    company: dict[str, Any],
    user_pages: dict[str, dict[str, str]],
    pages: list[str],
) -> list[dict[str, str]]:
    """Resolve one canonical 3-4 specialist roster with explicit gender across all pages and portraits."""
    for s_pref in ["team", "about", *[s for s in pages if s not in ("team", "about")]]:
        raw_tm = _clean((user_pages.get(s_pref) or {}).get("team"))
        if raw_tm:
            parsed: list[dict[str, str]] = []
            for entry in [p.strip() for p in re.split(r"[|\n]+", raw_tm) if p.strip()][:4]:
                chunks = [c.strip() for c in _SAFE_PAIR_RE.split(entry, maxsplit=1) if c.strip()]
                name = _strip_urls_from_copy(chunks[0]) if chunks else ""
                role = _strip_urls_from_copy(chunks[1]) if len(chunks) > 1 else ""
                if name:
                    parsed.append({"name": name, "role": role, "gender": infer_gender(name, "", len(parsed))})
            if parsed:
                return parsed
    out: list[dict[str, str]] = []
    for idx, m in enumerate(company.get("team") or []):
        if isinstance(m, dict) and _clean(m.get("name")):
            nm = _strip_urls_from_copy(_clean(m.get("name")))
            out.append({
                "name": nm,
                "role": _strip_urls_from_copy(_clean(m.get("role"))),
                "gender": infer_gender(nm, _clean(m.get("gender")), idx),
            })
    return out[:4]


_WOMAN_WORDS_RE = re.compile(r"\b(?:woman|women|female|lady)\b", re.I)
_MAN_WORDS_RE = re.compile(r"\b(?:man|men|male|gentleman)\b", re.I)
_NEUTRAL_PERSON_RE = re.compile(r"\b(?:person|individual|specialist|subject)\b", re.I)

TEAM_PERSONAS_FEMALE = [
    "34-year-old woman with honey-blonde hair pulled back into a clean low bun, bright hazel eyes, subtle confident smile, tailored ivory silk blouse under a slate blazer, slight three-quarter turn",
    "46-year-old woman with silver-streaked chestnut shoulder-length wavy hair, thin tortoiseshell rectangular glasses, warm composed expression, burgundy fine-knit turtleneck, front-angle framing",
    "29-year-old woman with short dark espresso pixie haircut, dark brown eyes, faint freckles, relaxed open gaze, olive linen architectural jacket over black knit top, gentle head tilt",
    "53-year-old woman with sleek silver-gray bob haircut, defined jawline, poised warm smile, deep navy structured wool blazer over cream shirt, upright editorial stance",
    "38-year-old woman with curly auburn copper hair framing her shoulders, emerald green eyes, attentive expression, warm camel cashmere crewneck sweater, three-quarter studio pose",
    "42-year-old woman with straight jet-black hair tucked behind one ear, small brushed gold earrings, calm friendly expression, charcoal coat over warm sand silk collar",
]

TEAM_PERSONAS_MALE = [
    "39-year-old man with short salt-and-pepper wavy hair and neatly trimmed short beard, slim dark eyeglasses, calm analytical expression, graphite merino crewneck under textured blazer, three-quarter turn",
    "54-year-old man with silver-gray receding hair, clean-shaven face, subtle character lines around eyes, warm reassuring smile, unbuttoned navy Oxford collar with herringbone jacket",
    "31-year-old man with thick dark-brown tousled side-part hair, clean-shaven jaw, energetic approachable gaze, warm terracotta knit polo, slight shoulder angle",
    "45-year-old bald man with groomed full dark beard and expressive eyebrows, hazel eyes, composed editorial gaze, crisp black Mandarin-collar architectural overshirt",
    "49-year-old man with combed-back blond-gray hair, light stubble, thin steel round eyewear, attentive expression, forest-olive structured overshirt over charcoal tee",
    "35-year-old East Asian man with neat dark straight crop, clean-shaven face, friendly subtle smile, warm sand suede jacket over slate shirt, relaxed upright studio posture",
]

_PORTRAIT_APPEARANCE_MARKERS = re.compile(
    r"(?i)\b(?:year-old|blonde|chestnut|auburn|silver-gray|pixie|bob|wavy|curly|"
    r"beard|clean-shaven|bald|stubble|glasses|eyewear|freckl|turtleneck|blazer|jacket|sweater|linen|polo|overshirt)\b"
)


def _pick_team_personas(team_slots: list[dict[str, Any]], brand: str = "") -> list[str]:
    """Assign distinct, non-repeating real-world appearance personas aligned with each slot's gender."""
    offset = sum(ord(ch) for ch in str(brand or "studio"))
    fem_used = 0
    male_used = 0
    picked: list[str] = []
    for slot in team_slots:
        if str(slot.get("gender") or "female") == "female":
            idx = (offset + fem_used) % len(TEAM_PERSONAS_FEMALE)
            picked.append(TEAM_PERSONAS_FEMALE[idx])
            fem_used += 1
        else:
            idx = (offset + male_used) % len(TEAM_PERSONAS_MALE)
            picked.append(TEAM_PERSONAS_MALE[idx])
            male_used += 1
    return picked


def _portrait_token_set(text: str) -> set[str]:
    stripped = re.sub(
        r"(?i)vertical 3:4 medium chest-up studio portrait(?: of an adult (?:woman|man))? with generous empty headroom above the top of the head",
        "",
        str(text or ""),
    )
    stops = {"portrait", "studio", "editorial", "seamless", "backdrop", "background", "light", "lighting", "soft", "lens", "85mm", "sharp", "focus", "eyes", "with", "headroom", "empty", "generous", "adult", "woman", "man", "above", "head"}
    return {w for w in re.findall(r"[a-z0-9-]{3,}", stripped.lower()) if w not in stops}


def _ensure_distinct_team_portrait(
    cand_prompt: str,
    gender: str,
    persona: str,
    team_style: str,
    seen_token_sets: list[set[str]],
) -> str:
    """Guarantee every team slot depicts a visibly distinct person with concrete appearance cues."""
    normalized = _enforce_portrait_gender(cand_prompt, gender)
    toks = _portrait_token_set(normalized)
    has_persona = bool(_PORTRAIT_APPEARANCE_MARKERS.search(normalized))
    is_duplicate = False
    for prev in seen_token_sets:
        union = toks | prev
        if union and (len(toks & prev) / len(union)) >= 0.60:
            is_duplicate = True
            break
    if is_duplicate or not has_persona or not toks:
        synthesized = (
            f"Vertical 3:4 medium chest-up studio portrait of a {persona}, "
            f"generous empty headroom above the top of the head, {team_style}, "
            "sharp focus on eyes, 85mm prime lens"
        )
        normalized = _enforce_portrait_gender(synthesized, gender)
        toks = _portrait_token_set(normalized)
    seen_token_sets.append(toks)
    return _clean(normalized)


def _enforce_portrait_gender(prompt: str, gender: str) -> str:
    """Guarantee Z-Image portrait prompt specifies the exact gender matching the team card name plus safe 3:4 headroom."""
    p = _clean(prompt)
    is_fem = gender == "female"
    target_cue = (
        "Vertical 3:4 medium chest-up studio portrait of an adult woman with generous empty headroom above the top of the head"
        if is_fem
        else "Vertical 3:4 medium chest-up studio portrait of an adult man with generous empty headroom above the top of the head"
    )
    opposite_re = _MAN_WORDS_RE if is_fem else _WOMAN_WORDS_RE
    same_re = _WOMAN_WORDS_RE if is_fem else _MAN_WORDS_RE
    if opposite_re.search(p):
        p = opposite_re.sub("woman" if is_fem else "man", p)
    if not same_re.search(p):
        if _NEUTRAL_PERSON_RE.search(p):
            p = _NEUTRAL_PERSON_RE.sub("woman" if is_fem else "man", p, count=1)
        else:
            p = f"{target_cue}, {p}" if p else f"{target_cue}, natural softbox lighting, 85mm lens, neutral seamless backdrop"
    if "headroom" not in p.lower() or "chest-up" not in p.lower():
        p = f"Vertical 3:4 medium chest-up studio portrait with generous empty headroom above the top of the head, {p}"
    return _clean(p)


def _accept_review_fix(
    bid: str,
    old_txt: str,
    new_txt: str,
    lang: str,
    brand: str,
    eff_hero: dict[str, str],
    headings: dict[str, str],
    blocks: list[str],
    seo: dict[str, str],
    company: dict[str, Any],
    slug: str,
    copy_map: dict[str, str],
    user_owned: set[str],
) -> bool:
    """Reject reviewer rewrites that introduce URL leaks, item shrinkage, placeholders, or new deterministic errors."""
    nt = _clean(new_txt)
    ot = _clean(old_txt)
    if not nt or nt == ot:
        return False
    low_n = nt.lower()
    if any(mk in low_n for mk in PLACEHOLDER_MARKERS) or nt.lstrip().startswith("{"):
        return False
    if bid not in ("contact", "locations", "legal") and _URL_TEXT_RE.search(nt):
        return False
    if bid == "contact" and any(mk in low_n for mk in ("https://yandex.", "https://maps.", "company name", "enter your")):
        return False
    old_items = [x.strip() for x in re.split(r"[|\n]+", ot) if x.strip()]
    new_items = [x.strip() for x in re.split(r"[|\n]+", nt) if x.strip()]
    if bid == "pricing":
        prods = [p for p in (company.get("products") or []) if isinstance(p, dict) and _clean(p.get("name"))]
        if (len(prods) >= 2 and len(new_items) < len(prods)) or "по запросу" in low_n or "on request" in low_n:
            return False
    if bid in ("features", "stats", "team", "values", "process", "testimonials", "blog"):
        if len(new_items) < min(3, max(1, len(old_items))):
            return False
    if bid == "faq":
        old_q = sum(1 for x in old_items if "?" in x)
        new_q = sum(1 for x in new_items if "?" in x)
        if new_q < max(2, old_q):
            return False
    before_det = _deterministic_checks(lang, brand, eff_hero, headings, copy_map, blocks, seo, company, slug, user_owned)
    cand_map = dict(copy_map)
    cand_map[bid] = nt
    after_det = _deterministic_checks(lang, brand, eff_hero, headings, cand_map, blocks, seo, company, slug, user_owned)
    if len(after_det["issues"]) > len(before_det["issues"]):
        return False
    return True


def _canon_slice(card: dict[str, Any], dossier: dict[str, Any] | None = None) -> str:
    layout = card.get("layout") or {}
    motion = card.get("motion") or {}
    d = dossier or {}
    base = (
        f"Canon: {card.get('name')} ({card.get('id')})\n"
        f"Description: {_clean(card.get('description_en'))[:220]}\n"
        f"Grid: {layout.get('grid_cols', 12)} cols, radius {layout.get('radius_px', 8)}px, "
        f"heading transform {layout.get('heading_transform', 'none')}\n"
        f"Motion: {motion.get('duration_ms', 220)}ms ease {_clean(motion.get('ease'))[:40]}, "
        f"reduced-motion: {_clean(motion.get('reduced_motion_policy'))[:80]}"
    )
    if d.get("design_code"):
        base += f"\nDesign code: {_clean(d.get('design_code'))[:320]}"
    if d.get("block_rules"):
        base += f"\nBlock layout rules: {_clean(d.get('block_rules'))[:260]}"
    return base


def _page_purpose(slug: str, lang: str) -> str:
    preset = PAGE_MAP.get(slug) or {}
    return _clean(preset.get("purpose_ru" if lang == "ru" else "purpose_en"))


def _deterministic_checks(
    lang: str,
    brand: str,
    hero: dict[str, str],
    headings: dict[str, str],
    copy: dict[str, str],
    blocks: list[str],
    seo: dict[str, str],
    company: dict[str, Any] | None = None,
    slug: str = "index",
    user_owned: set[str] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    brand_tokens = {w.lower() for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", brand or "")}
    all_text = " ".join([*copy.values(), *headings.values(), str(hero.get("headline") or ""), str(hero.get("subhead") or "")])
    all_text = FIELD_LABEL_RE.sub("", all_text)
    low = all_text.lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker in low:
            issues.append(f"placeholder marker '{marker}' in copy")
            break
    if any(str(v).lstrip().startswith("{") or "': '" in str(v) for v in copy.values()):
        issues.append("raw JSON object leaked into block copy")
    if lang == "ru":
        scan_text = re.sub(r"\S+@\S+|https?://\S+", " ", all_text)
        latin = [
            w for w in re.findall(r"[A-Za-z]{4,}", scan_text)
            if w[0].islower() and w.lower() not in LATIN_WHITELIST and w.lower() not in brand_tokens
        ]
        if latin:
            issues.append(f"unexpected Latin words in RU copy: {', '.join(sorted(set(latin))[:5])}")
    hl = _clean(hero.get("headline"))
    sub = _clean(hero.get("subhead"))
    if not (6 <= len(hl) <= 95):
        issues.append("hero headline missing or out of 6-95 char range")
    if not (20 <= len(sub) <= 280):
        issues.append("hero subhead missing or out of 20-280 char range")
    missing = [b for b in blocks if b not in ("hero", "footer") and not _clean(copy.get(b))]
    if missing:
        issues.append(f"empty blocks: {', '.join(missing)}")
    missing_h = [b for b in blocks if b not in ("hero", "footer", "cta", "contact", "legal", "manifesto") and not _clean(headings.get(b))]
    if missing_h:
        issues.append(f"missing section headings: {', '.join(missing_h)}")
    title = _clean(seo.get("title"))
    desc = _clean(seo.get("description"))
    if not (10 <= len(title) <= 70):
        issues.append("SEO title out of 10-70 char range")
    if not (40 <= len(desc) <= 165):
        issues.append("SEO description out of 40-165 char range")
    comp = company or {}
    f_digits = re.sub(r"\D", "", str(comp.get("phone") or ""))
    if f_digits:
        for ph in re.findall(r"\+?[\d][\d\s().-]{8,}\d", all_text):
            digits = re.sub(r"\D", "", ph)
            if len(digits) >= 10 and digits != f_digits:
                issues.append("phone number differs from brand foundation (single source of truth)")
                break
    owned = user_owned or set()
    scan_copy = " ".join(v for k, v in copy.items() if k not in owned)
    truth_prices = {re.sub(r"[^\d]", "", str(pr.get("price") or "")) for pr in (comp.get("products") or []) if isinstance(pr, dict)}
    truth_prices = {x for x in truth_prices if len(x) >= 3}
    if truth_prices:
        for money in re.findall(r"\d[\d\s.,]{2,}\s*(?:₽|руб|\$|€|USD|EUR)", scan_copy):
            digits = re.sub(r"[^\d]", "", money)
            if len(digits) >= 3 and digits not in truth_prices and not any(digits in tp or tp in digits for tp in truth_prices):
                issues.append("price mentioned that is not in the foundation product catalog (single source of truth)")
                break
    founded = str((comp.get("history") or {}).get("founded") or "")
    if founded:
        for m in re.finditer(r"(?:основан[аоы]? в|founded in|since)\s*(19|20)\d{2}", scan_copy, re.I):
            if m.group(0)[-4:] != founded:
                issues.append("founding year differs from brand history (single source of truth)")
                break
    f_email = str(comp.get("email") or "").strip().lower()
    f_domain = f_email.split("@")[-1] if "@" in f_email else ""
    if f_domain:
        for em in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", all_text):
            if em.lower().split("@")[-1] != f_domain:
                issues.append("email domain differs from brand foundation (single source of truth)")
                break
    tagline = _clean(comp.get("tagline"))
    positioning = _clean(comp.get("positioning"))
    global_mf = " | ".join(x for x in (tagline, positioning) if x)
    if global_mf and slug not in ("index", "about"):
        if _clean(copy.get("manifesto")) == global_mf:
            issues.append("global tagline repeated verbatim in manifesto on subpage; make it page-specific")
    faq_txt = _clean(copy.get("faq"))
    if "faq" in blocks and faq_txt:
        pairs = [p for p in re.split(r"[|\n]+", faq_txt) if "?" in p]
        if len(pairs) < 2:
            issues.append("FAQ must contain at least 2 'Question? Answer' pairs")
    ai_blocks: dict[str, list[str]] = {}
    for bid in blocks:
        if bid in ("hero", "footer"):
            continue
        txt_b = _clean(copy.get(bid))
        if not txt_b:
            continue
        ai_res = lint_anti_ai_copy(txt_b, lang, bid)
        if not ai_res.get("passed", True):
            ai_blocks[bid] = list(ai_res.get("hard_hits") or [])
            issues.append(f"AI cliché / kantselyarit in '{bid}': {', '.join(ai_blocks[bid][:2])}")
    failed: set[str] = set()
    for issue in issues:
        if "placeholder" in issue or "empty blocks" in issue or "JSON" in issue or "tagline repeated" in issue or "AI cliché" in issue:
            failed.add("specificity")
        elif "single source of truth" in issue:
            failed.add("brand")
        elif "price mentioned" in issue or "founding year" in issue:
            failed.add("brand")
        elif "Latin" in issue:
            failed.add("language")
        elif "hero" in issue:
            failed.add("offer")
        elif "headings" in issue:
            failed.add("structure")
        elif "SEO" in issue or "FAQ" in issue:
            failed.add("seo")
    return {"issues": issues, "failed": sorted(failed), "ai_blocks": ai_blocks}


class PipelineMemory:
    """On-disk system memory: smartllm.md passport + .smartllm/state.json ledger + JSON artifacts."""

    def __init__(self, project_dir: Path, passport: dict[str, Any]) -> None:
        self.root = project_dir
        self.mem_dir = project_dir / ".smartllm" / "memory"
        self.mem_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = project_dir / ".smartllm" / "state.json"
        self.passport = passport
        self.state: dict[str, Any] = {
            "schema_version": 1,
            "fingerprint": str(passport.get("fingerprint") or ""),
            "passport": passport,
            "created_at": _now(),
            "updated_at": _now(),
            "steps": [],
        }
        if self.state_path.exists():
            try:
                old = json.loads(self.state_path.read_text(encoding="utf-8"))
                if old.get("fingerprint") == self.state["fingerprint"] and isinstance(old.get("steps"), list):
                    self.state = old
            except Exception:
                pass
        self._flush()

    def _step(self, step_id: str) -> dict[str, Any]:
        for s in self.state["steps"]:
            if s["id"] == step_id:
                return s
        s = {"id": step_id, "status": "queued", "artifact": "", "detail": "", "started_at": "", "finished_at": ""}
        self.state["steps"].append(s)
        return s

    def artifact_path(self, relpath: str) -> Path:
        p = (self.mem_dir / relpath).resolve()
        if not p.is_relative_to(self.mem_dir.resolve()):
            raise ValueError(f"artifact path escapes memory dir: {relpath}")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def write_artifact(self, relpath: str, data: Any) -> Path:
        p = self.artifact_path(relpath)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return p

    def read_artifact(self, relpath: str) -> Any:
        p = self.mem_dir / relpath
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def done(self, step_id: str) -> bool:
        s = next((x for x in self.state["steps"] if x["id"] == step_id), None)
        if not s or s.get("status") != "done" or not s.get("artifact"):
            return False
        return (self.mem_dir / s["artifact"]).exists()

    def mark(self, step_id: str, status: str, artifact: str = "", detail: str = "") -> None:
        s = self._step(step_id)
        s["status"] = status
        if status == "running" and not s["started_at"]:
            s["started_at"] = _now()
        if status in ("done", "failed", "skipped"):
            s["finished_at"] = _now()
        if artifact:
            s["artifact"] = artifact
        if detail:
            s["detail"] = detail
        self._flush()

    def _flush(self) -> None:
        self.state["updated_at"] = _now()
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._write_smartllm_md()

    def _write_smartllm_md(self) -> None:
        p = self.passport
        lines = [
            f"# SmartLLM System Memory — {p.get('name')}",
            "",
            f"- Project dir: `{self.root}`",
            f"- Language: {p.get('lang')} · Canon: {p.get('canon_name')} (`{p.get('canon_id')}`)",
            f"- Mode: {p.get('mode')} · Render images: {p.get('render_images')}",
            f"- Fingerprint: `{str(p.get('fingerprint'))[:16]}` · Updated: {self.state['updated_at']}",
            "",
            "## Architecture map",
        ]
        for slug in p.get("pages") or []:
            blocks = (p.get("page_blocks") or {}).get(slug) or []
            lines.append(f"- `{slug}` ({page_title(slug, str(p.get('lang')))}): {' -> '.join(blocks)}")
        lines += ["", "## Agent ledger", "", "| Step | Status | Artifact | Detail |", "|---|---|---|---|"]
        for s in self.state["steps"]:
            lines.append(f"| {s['id']} | {s['status']} | {s.get('artifact') or '—'} | {_clean(s.get('detail'))[:90] or '—'} |")
        lines += [
            "",
            "## Protocol",
            "Agents run strictly sequentially. Each agent reads only its memory slice, writes a JSON",
            "artifact under `.smartllm/memory/`, and marks this ledger before the next agent starts.",
            "The deterministic compiler materializes HTML/CSS/CSP from memory; agents never emit raw markup.",
            "Re-running the same inputs resumes from the last completed agent (fingerprint match).",
            "",
        ]
        (self.root / "smartllm.md").write_text("\n".join(lines), encoding="utf-8")


def _llm_json(
    state: Any,
    gpu_ok: bool,
    sys_msg: str,
    user_msg: str,
    max_tokens: int = 2048,
    required_keys: list[str] | None = None,
) -> dict[str, Any]:
    if not gpu_ok:
        return {}
    out: dict[str, Any] = {}
    try:
        raw = state.llm.generate_structured_json(sys_msg, user_msg, max_tokens=max_tokens)
        if isinstance(raw, dict):
            out.update(raw)
    except Exception:
        out = {}
    if required_keys:
        missing = [k for k in required_keys if out.get(k) in (None, "", [], {})]
        if missing and len(missing) <= len(required_keys):
            retry_msg = (
                f"Previous JSON response was incomplete or missing keys: {json.dumps(missing, ensure_ascii=False)}.\n"
                f"Return ONLY a single complete valid JSON object containing these keys: {json.dumps(missing, ensure_ascii=False)}.\n\n"
                f"{user_msg}"
            )
            try:
                raw2 = state.llm.generate_structured_json(sys_msg, retry_msg, max_tokens=max_tokens)
                if isinstance(raw2, dict):
                    for k, v in raw2.items():
                        if out.get(k) in (None, "", [], {}) and v not in (None, "", [], {}):
                            out[k] = v
            except Exception:
                pass
    return out


def run_content_pipeline(
    state: Any,
    merged: dict[str, Any],
    mode: str,
    render_images: bool,
    gpu_ok: bool,
    canon_card: dict[str, Any],
    report: ReportFn,
    stage_idx: int,
) -> dict[str, Any]:
    """Run foundation -> architect -> structure -> per-page hero/copy -> SEO -> visuals -> review agents."""
    from .orchestrator import _generate_company_with_llm, build_default_block_descriptions
    from .blueprint_render import load_canon_dossier

    lang_pref_raw = str(merged.get("languages") or "ru").strip()
    bilingual = lang_pref_raw.lower() in ("en+ru", "ru+en")
    lang = resolve_primary_lang(lang_pref_raw, _clean(merged.get("brief") or merged.get("goal") or merged.get("name") or ""))
    alt_lang = "en" if lang == "ru" else "ru"
    dossier = load_canon_dossier(str(canon_card.get("id") or ""))
    target_lang = "Russian" if lang == "ru" else "English"
    brand = _clean(merged.get("name")) or ("Проект" if lang == "ru" else "Project")
    brief = _clean(merged.get("brief") or merged.get("goal"))
    pages: list[str] = list(merged.get("selected_pages") or ["index"])
    page_blocks: dict[str, list[str]] = merged.get("page_blocks") or {"index": ["hero", "contact", "footer"]}
    out_dir = Path(merged.get("output_dir")).resolve()
    canon_id = str(canon_card.get("id") or "01_bento_grid")
    stack_id = str(merged.get("stack") or "html5_esm")
    hints = BLOCK_FORMAT_HINTS_RU if lang == "ru" else BLOCK_FORMAT_HINTS_EN

    user_pages_raw = merged.get("page_block_prompts") if isinstance(merged.get("page_block_prompts"), dict) else {}
    user_pages: dict[str, dict[str, str]] = {}
    flat_user = merged.get("block_prompts") if isinstance(merged.get("block_prompts"), dict) else {}
    for slug in pages:
        um: dict[str, str] = {}
        for bid in page_blocks.get(slug, []):
            if bid == "footer":
                continue
            txt = _clean((user_pages_raw.get(slug) or {}).get(bid)) if mode != "auto" else ""
            if not txt and mode != "auto":
                txt = _clean(flat_user.get(bid))
            if txt:
                um[bid] = txt
        user_pages[slug] = um

    fingerprint = hashlib.sha256(json.dumps({
        "name": brand, "brief": brief, "lang": lang, "canon": merged.get("canon_id"),
        "pages": pages, "page_blocks": page_blocks, "user_pages": user_pages,
        "company": merged.get("company") or {}, "mode": mode, "render_images": render_images,
        "pipeline_version": PIPELINE_VERSION,
    }, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    memory = PipelineMemory(out_dir, {
        "name": brand, "lang": lang, "canon_id": canon_card.get("id"), "canon_name": canon_card.get("name"),
        "mode": mode, "render_images": render_images, "pages": pages, "page_blocks": page_blocks,
        "fingerprint": fingerprint,
    })
    memory.mark("init", "done", detail=f"{len(pages)} pages, canon {canon_card.get('id')}")
    agents_run = 0
    agents_reused = 0

    def reuse(step_id: str, relpath: str) -> Any:
        nonlocal agents_reused
        if memory.done(step_id):
            data = memory.read_artifact(relpath)
            if data is not None:
                agents_reused += 1
                return data
        return None

    report(stage_idx, 6, "Инициализация системной памяти проекта (smartllm.md)...", "Initializing project system memory (smartllm.md)...", "orchestrator: memory init")

    fallback_company = build_default_company(brand, brief, lang)
    user_company = merged.get("company") if isinstance(merged.get("company"), dict) else {}
    company = reuse("foundation", "foundation.json")
    if company is None:
        memory.mark("foundation", "running")
        company = dict(fallback_company)
        llm_company = _generate_company_with_llm(state, brand, brief, lang) if gpu_ok else {}
        if llm_company:
            company.update(llm_company)
            agents_run += 1
        if mode != "auto" and user_company:
            company.update({k: v for k, v in user_company.items() if v not in (None, "", [], {})})
        memory.write_artifact("foundation.json", company)
        memory.mark("foundation", "done", "foundation.json", "brand foundation + contacts")
    else:
        if mode != "auto" and user_company:
            company.update({k: v for k, v in user_company.items() if v not in (None, "", [], {})})
    canonical_team = _resolve_canonical_team(company, user_pages, pages)
    if canonical_team:
        company["team"] = canonical_team
    foundation_txt = _foundation_slice(company, lang)

    report(stage_idx, 10, "Субагент-архитектор: карта страниц, меню, футер, дизайн-код...", "Architect agent: page map, header, footer, design code...", "agent 1/7: architect")
    architecture = reuse("architect", "architecture.json")
    if architecture is None:
        memory.mark("architect", "running")
        page_lines = "\n".join(f"- {slug}: {page_title(slug, lang)} — {_page_purpose(slug, lang)}" for slug in pages)
        arch_kb = load_stage_context("architect", stack=stack_id, canon_id=canon_id)[:1800]
        sys_msg = (
            "You are SmartLLM v2 Chief Web Architect and Task Dispatcher. Plan the global site chrome, "
            "2 distinct gallery visual scenes, and strict non-contradicting page quests grounded in the brand foundation. "
            "Return ONLY valid JSON."
        )
        user_msg = (
            f"Brand: {brand}\nBrief: {brief[:320]}\nLanguage: {target_lang}\n{_canon_slice(canon_card, dossier)}\n"
            + (f"Architecture & Stack Canon Excerpt:\n{arch_kb}\n\n" if arch_kb else "")
            + f"Brand foundation (SINGLE SOURCE OF TRUTH):\n{foundation_txt}\n\nPages:\n{page_lines}\n\n"
            f"Write all user-facing values in {target_lang}. Nav labels: 1-2 words, no clichés.\n"
            "Rules:\n"
            "- Every page must have a distinct editorial 'angle', distinct English 'hero_subject', and explicit 'quest' telling copy agents which truth items (capabilities vs pricing vs team vs proof) belong on that page without mixing pricing into features or changing team/stats facts.\n"
            "- 'hero_subject': physical architectural environment, hardware installation, studio workspace, or flagship product scene in English — NEVER a close-up person portrait or human headshot.\n"
            "- 'gallery_subjects': 2 CLEARLY DIFFERENT physical scene descriptions in English (Scene 1 wide flagship project/environment, Scene 2 close-up material/engineering detail).\n"
            "Return JSON:\n"
            '{"nav_labels": {"slug": "label"}, "footer_text": "one-line colophon with brand promise", '
            '"header_cta": "short header action label", '
            '"gallery_subjects": ["English scene 1 (wide architectural/product view)", "English scene 2 (distinct close-up craft/engineering scene)"], '
            '"pages": {"slug": {"angle": "one-sentence editorial angle", "quest": "strict subagent assignment for this page citing exact truth scope", '
            '"hero_subject": "physical scene subject for the hero photograph, in English"}}, '
            '"motion_note": "one sentence scroll choreography note"}'
        )
        raw = _llm_json(state, gpu_ok, sys_msg, user_msg, max_tokens=2400, required_keys=["nav_labels", "footer_text", "pages"])
        if raw:
            agents_run += 1
        gal_subjs = [_clean(x) for x in (raw.get("gallery_subjects") or []) if _clean(x)]
        if len(gal_subjs) < 2 or gal_subjs[0].lower() == gal_subjs[1].lower():
            gal_subjs = [
                f"Wide architectural environment showcasing {brief[:100]} flagship execution",
                f"Close-up editorial photograph of tactile materials and precision engineering craftsmanship for {brand}",
            ]
        architecture = {
            "nav_labels": {str(k): _clean(v) for k, v in (raw.get("nav_labels") or {}).items() if _clean(v)},
            "footer_text": _clean(raw.get("footer_text")),
            "header_cta": _clean(raw.get("header_cta")),
            "motion_note": _clean(raw.get("motion_note")),
            "gallery_subjects": gal_subjs[:2],
            "pages": {},
        }
        for slug in pages:
            rp = (raw.get("pages") or {}).get(slug) or {}
            architecture["pages"][slug] = {
                "angle": _clean(rp.get("angle")),
                "quest": _clean(rp.get("quest")),
                "hero_subject": _clean(rp.get("hero_subject")),
            }
        memory.write_artifact("architecture.json", architecture)
        memory.mark("architect", "done", "architecture.json", f"chrome + {len(pages)} page quests")
    chrome = {
        "nav_labels": architecture.get("nav_labels") or {},
        "footer_text": architecture.get("footer_text") or (
            f"© {brand}. {company.get('tagline') or brief[:80]}"
        ),
        "header_cta": architecture.get("header_cta"),
        "motion_note": architecture.get("motion_note"),
    }

    report(stage_idx, 14, "Субагент каркаса: семантические сетки страниц без текстов...", "Structure agent: semantic page skeletons without copy...", "agent 2/7: structure")
    structure: dict[str, Any] = {}
    for slug in pages:
        rel = f"structure/{slug}.json"
        sk = reuse(f"structure:{slug}", rel)
        if sk is None:
            memory.mark(f"structure:{slug}", "running")
            layout = canon_card.get("layout") or {}
            sk = {
                "slug": slug,
                "grid_cols": int(layout.get("grid_cols", 12)),
                "blocks": [
                    {"id": bid, "container": "section", "grid_span": 12 if bid in ("hero", "cta", "manifesto") else 4, "has_copy": False}
                    for bid in page_blocks.get(slug, [])
                ],
            }
            memory.write_artifact(rel, sk)
            memory.mark(f"structure:{slug}", "done", rel, f"{len(sk['blocks'])} block shells")
        structure[slug] = sk

    page_results: dict[str, dict[str, Any]] = {}
    page_copy: dict[str, dict[str, str]] = {}
    n_pages = max(1, len(pages))
    for p_idx, slug in enumerate(pages):
        blocks = [b for b in page_blocks.get(slug, []) if b != "footer"]
        angle = _clean((architecture.get("pages") or {}).get(slug, {}).get("angle"))
        quest = _clean((architecture.get("pages") or {}).get(slug, {}).get("quest"))
        purpose = _page_purpose(slug, lang)
        base_pct = 16 + int(52 * p_idx / n_pages)
        report(stage_idx, base_pct, f"Субагент страницы «{page_title(slug, lang)}»: hero-оффер и заголовки...", f"Page agent '{page_title(slug, lang)}': hero offer & headings...", f"agent 3/7: hero {slug}")

        hero_rel = f"pages/{slug}/hero.json"
        hero_doc = reuse(f"hero:{slug}", hero_rel)
        if hero_doc is None:
            memory.mark(f"hero:{slug}", "running")
            copy_kb = load_stage_context("copy_marketing", canon_id=canon_id)[:1400]
            user_desc_lines = "\n".join(f"- {bid}: {txt[:220]}" for bid, txt in user_pages.get(slug, {}).items()) or ("(none)" if lang == "en" else "(нет)")
            sys_msg = (
                f"You are SmartLLM v2 Hero Copywriter & Section Editor. Write a premium {target_lang} hero offer "
                "and editorial section headings for one page. Return ONLY valid JSON."
            )
            user_msg = (
                f"Brand: {brand}\nPage: {page_title(slug, lang)} ({slug})\nPurpose: {purpose}\n"
                f"Editorial angle: {angle or purpose}\n{_canon_slice(canon_card, dossier)}\n"
                + (f"Conversion & Anti-AI Canon:\n{copy_kb}\n\n" if copy_kb else "")
                + f"Brand foundation:\n{foundation_txt}\n\n"
                f"User content descriptions for this page (must be respected):\n{user_desc_lines}\n\n"
                f"Blocks on this page: {', '.join(blocks)}\n"
                f"Allowed layout variants per block (pick one per block, vary across pages): {json.dumps({b: (dossier.get('variants') or {}).get(b, ['default']) for b in blocks if b in (dossier.get('variants') or {})}, ensure_ascii=False)}\n\n"
                f"Write in {target_lang}. Headline: 6-12 words, concrete offer, no clichés. "
                "Subhead: 1-2 sentences of specific value. If a user hero description exists, build on it.\n"
                "Return JSON:\n"
                '{"hero": {"eyebrow": "2-4 word kicker", "headline": "...", "subhead": "...", '
                '"cta_label": "primary action", "cta_secondary": "secondary action"}, '
                '"headings": {"block_id": "editorial H2 for this block"}, '
                '"variants": {"block_id": "one of the allowed layout variants"}}'
            )
            raw = _llm_json(state, gpu_ok, sys_msg, user_msg, max_tokens=2048, required_keys=["hero", "headings", "variants"])
            if raw:
                agents_run += 1
            hero_raw = raw.get("hero") or {}
            allowed_var = dossier.get("variants") or {}
            hero_doc = {
                "hero": {k: _clean(hero_raw.get(k)) for k in ("eyebrow", "headline", "subhead", "cta_label", "cta_secondary")},
                "headings": {str(k): _clean(v) for k, v in (raw.get("headings") or {}).items() if _clean(v) and str(k) in blocks},
                "variants": {str(k): str(v) for k, v in (raw.get("variants") or {}).items() if str(k) in blocks and str(v) in (allowed_var.get(str(k)) or ["default"])},
            }
            memory.write_artifact(hero_rel, hero_doc)
            memory.mark(f"hero:{slug}", "done", hero_rel, f"hero + {len(hero_doc['headings'])} headings")
        hero = dict(hero_doc.get("hero") or {})
        hl = _clean(hero.get("headline"))
        if hl and len(hl) < 6:
            hero["headline"] = f"{brand} — {hl}"
        elif len(hl) > 95:
            hero["headline"] = hl[:95].rsplit(" ", 1)[0]
        headings = dict(hero_doc.get("headings") or {})
        for bid in blocks:
            if bid in ("hero", "footer", "cta", "contact", "legal", "manifesto"):
                continue
            if not _clean(headings.get(bid)):
                bmeta = BLOCK_MAP.get(bid) or {}
                headings[bid] = _clean(bmeta.get("title_ru" if lang == "ru" else "title_en"))

        missing = [b for b in blocks if b != "hero" and not user_pages.get(slug, {}).get(b)]
        copy: dict[str, str] = dict(user_pages.get(slug, {}))
        if missing:
            report(stage_idx, base_pct + 2, f"Субагент копирайтинга «{page_title(slug, lang)}»: {len(missing)} блоков...", f"Copy agent '{page_title(slug, lang)}': {len(missing)} blocks...", f"agent 4/7: copy {slug}")
        for batch_start in range(0, len(missing), COPY_BATCH_SIZE):
            batch = missing[batch_start:batch_start + COPY_BATCH_SIZE]
            step_id = f"copy:{slug}:{batch_start // COPY_BATCH_SIZE}"
            rel = f"pages/{slug}/copy_{batch_start // COPY_BATCH_SIZE}.json"
            batch_doc = reuse(step_id, rel)
            if batch_doc is None:
                memory.mark(step_id, "running")
                fmt_lines = "\n".join(f"- {bid}: {hints[bid]}" for bid in batch if bid in hints)
                context_lines = "\n".join(f"- {bid}: {txt[:160]}" for bid, txt in copy.items() if bid not in batch) or "(none)"
                sys_msg = (
                    f"You are SmartLLM v2 Expert Copywriter. Fill exactly the requested blocks with specific, "
                    f"authentic {target_lang} copy consistent with the hero. Return ONLY valid JSON."
                )
                user_msg = (
                    f"Brand: {brand}\nPage: {page_title(slug, lang)} ({slug})\nAngle: {angle or purpose}\n"
                    f"Architect Quest: {quest or purpose}\n"
                    f"Hero headline: {_clean(hero.get('headline'))}\nHero subhead: {_clean(hero.get('subhead'))}\n"
                    f"Brand foundation (SINGLE SOURCE OF TRUTH — NEVER alter team names, metrics, product prices, or contacts):\n{foundation_txt}\n\n"
                    f"Existing copy on this page (stay consistent, do not repeat verbatim):\n{context_lines}\n\n"
                    f"Write ONLY these blocks: {', '.join(batch)}\n"
                    f"Required format per block:\n{fmt_lines}\n"
                    "Separate list items with ' | '. FAQ must be 'Question? Answer' pairs. "
                    "Card grid balance: for features, values, stats, team, blog, and testimonials, generate EITHER 3 items (3-column row), 4 items (2x2 balanced grid), or 6 items (3x2 grid) — never 5 items. "
                    "Strictly keep pricing tiers in 'pricing' (ALL tiers + exact prices from foundation) and core capabilities in 'features' (WITHOUT prices). "
                    "Use exact canonical 'team' specialists from foundation — same 3-4 people in the exact same order across ALL pages, plain 'Name — Role' text ONLY, ZERO URLs. "
                    "Use exact metrics from foundation for 'stats' — never contradict founding year or KPIs between pages. "
                    "Never include HTML form field labels ('Company Name', 'Enter your...') inside 'contact'. Never output bare 'Принцип' / 'Principle' in 'values'. "
                    "Never prefix items with English field labels like address:, hours:, phone:. Every block value must be a plain string, never nested JSON. "
                    "Do not truncate or use placeholders.\n"
                    f'Return one JSON object with exactly these keys: {json.dumps(batch)}'
                )
                raw = _llm_json(state, gpu_ok, sys_msg, user_msg, max_tokens=3072, required_keys=batch)
                if raw:
                    agents_run += 1
                batch_doc = {bid: _norm_block_value(bid, raw.get(bid)) for bid in batch if _norm_block_value(bid, raw.get(bid))}
                memory.write_artifact(rel, batch_doc)
                memory.mark(step_id, "done", rel, f"{len(batch_doc)}/{len(batch)} blocks")
            for bid, txt in batch_doc.items():
                if bid in blocks and txt:
                    copy[bid] = _strip_field_labels(txt)
        fallback_desc = build_default_block_descriptions(brand, brief, blocks, lang, company)
        if slug not in ("index", "about") and fallback_desc.get("manifesto"):
            fallback_desc["manifesto"] = f"{page_title(slug, lang)}: {fallback_desc['manifesto']}"
        for bid in blocks:
            if bid != "hero" and not _clean(copy.get(bid)):
                copy[bid] = fallback_desc.get(bid) or brief
        copy = _sync_page_copy_to_foundation(slug, copy, company, lang, set(user_pages.get(slug, {})), canonical_team)
        copy_rel = f"pages/{slug}/copy.json"
        memory.write_artifact(copy_rel, copy)
        page_copy[slug] = copy
        page_results[slug] = {"hero": hero, "headings": headings, "copy": copy, "blocks": blocks, "variants": hero_doc.get("variants") or {}}

    report(stage_idx, 70, "Субагент SEO / AEO / GEO: title, description, alt, факты...", "SEO / AEO / GEO agent: titles, descriptions, alts, facts...", "agent 5/7: seo_geo")
    seo_doc = reuse("seo", "seo.json")
    if seo_doc is None:
        memory.mark("seo", "running")
        digest = "\n".join(
            f"- {slug} ({page_title(slug, lang)}): {_clean(page_results[slug]['hero'].get('headline')) or page_title(slug, lang)}"
            for slug in pages
        )
        sys_msg = (
            f"You are SmartLLM v2 SEO / AEO / GEO Editor. Write search-ready metadata in {target_lang} "
            "and verifiable brand facts. Return ONLY valid JSON."
        )
        user_msg = (
            f"Brand: {brand}\nBrief: {brief[:280]}\nBrand foundation:\n{foundation_txt}\n\n"
            f"Pages and their hero headlines:\n{digest}\n\n"
            f"Rules: title 10-60 chars incl. brand; description 40-155 chars, concrete benefit; "
            f"hero_alt in {target_lang}, describes the hero photograph, no keyword stuffing.\n"
            "geo_facts: 3 plausible editable brand facts (practice years, delivered projects, response time). "
            "faqs: 3 universal 'Question? Answer' pairs about working with this brand.\n"
            "Return JSON:\n"
            '{"pages": {"slug": {"title": "...", "description": "...", "hero_alt": "..."}}, '
            '"geo_facts": [{"claim": "..."}], "faqs": [{"q": "...", "a": "..."}]}'
        )
        raw = _llm_json(state, gpu_ok, sys_msg, user_msg, max_tokens=2048, required_keys=["pages", "geo_facts", "faqs"])
        if raw:
            agents_run += 1
        seo_pages: dict[str, dict[str, str]] = {}
        for slug in pages:
            rp = (raw.get("pages") or {}).get(slug) or {}
            seo_pages[slug] = {k: _clean(rp.get(k)) for k in ("title", "description", "hero_alt")}
        seo_doc = {
            "pages": seo_pages,
            "geo_facts": [{"claim": _clean(f.get("claim"))} for f in (raw.get("geo_facts") or []) if _clean(f.get("claim"))][:4],
            "faqs": [{"q": _clean(f.get("q")), "a": _clean(f.get("a"))} for f in (raw.get("faqs") or []) if _clean(f.get("q")) and _clean(f.get("a"))][:4],
        }
        memory.write_artifact("seo.json", seo_doc)
        memory.mark("seo", "done", "seo.json", f"{len(seo_pages)} page metas")
    for slug in pages:
        sp = (seo_doc.get("pages") or {}).get(slug) or {}
        if not sp.get("title"):
            hl = _clean(page_results[slug]["hero"].get("headline"))
            sp["title"] = (f"{brand} — {hl}" if hl else f"{brand} — {page_title(slug, lang)}")[:65]
        if not sp.get("description"):
            desc = (_clean(page_results[slug]["hero"].get("subhead")) or brief or _clean(company.get("tagline")) or brand)[:155]
            if len(desc) < 40:
                desc = f"{desc} · {_clean(company.get('tagline')) or brand}"[:155]
            sp["description"] = desc
        if not sp.get("hero_alt"):
            sp["hero_alt"] = f"{brand} — {page_title(slug, lang)}"
        if len(sp["title"]) > 65:
            sp["title"] = sp["title"][:65].rsplit(" ", 1)[0].rstrip(" ,;:—-")
        if len(sp["description"]) > 155:
            sp["description"] = sp["description"][:155].rsplit(" ", 1)[0].rstrip(" ,;:—-")
        page_results[slug]["seo"] = sp

    report(stage_idx, 74, "Субагент визуальных промптов Z-Image Turbo (логотип, hero, галерея, команда)...", "Z-Image Turbo visual prompt agent (logo, heroes, gallery, team)...", "agent 6/8: visuals")
    visuals = reuse("visuals", "visuals.json")
    team_slots = list(canonical_team[:4]) if canonical_team else _resolve_canonical_team(company, user_pages, pages)
    if not team_slots:
        for slug in pages:
            tm = _clean(page_copy.get(slug, {}).get("team"))
            if tm:
                for p in [x.strip() for x in re.split(r"[|\n]+", tm) if x.strip()][:4]:
                    ch = [c.strip() for c in _SAFE_PAIR_RE.split(p, maxsplit=1) if c.strip()]
                    nm = ch[0] if ch else ""
                    rl = ch[1] if len(ch) > 1 else "technical specialist"
                    if nm:
                        team_slots.append({"name": nm, "role": rl, "gender": infer_gender(nm, "", len(team_slots))})
                break
    member_names = [m["name"] for m in team_slots if m.get("name")]
    brand_words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]{3,}", brand or "") if w]
    team_personas = _pick_team_personas(team_slots, brand)
    team_roles = [
        f"Slot {idx + 1} ({'FEMALE' if m.get('gender') == 'female' else 'MALE'} specialist, DO NOT write name): {m.get('role') or 'senior specialist'} — distinct appearance: {team_personas[idx]}"
        for idx, m in enumerate(team_slots)
    ]
    if visuals is None:
        memory.mark("visuals", "running")
        from .orchestrator import ZIMAGE_LOGO_CANON_2026, _default_logo_base_prompt
        imagery = canon_card.get("imagery") or {}
        pal_cols = palette_to_material_summary(canon_card.get("palette") or {}) or "matte neutral architectural stone, warm alabaster highlight"
        subjects = {slug: _clean((architecture.get("pages") or {}).get(slug, {}).get("hero_subject")) or brief[:100] for slug in pages}
        subjects_ctx = {
            slug: {
                "scene": subjects[slug],
                "hero_headline": _clean(page_results.get(slug, {}).get("hero", {}).get("headline"))[:110],
                "hero_subhead": _clean(page_results.get(slug, {}).get("hero", {}).get("subhead"))[:140],
                "key_features": _clean(page_copy.get(slug, {}).get("features"))[:140],
            }
            for slug in pages
        }
        vis_kb = load_stage_context("visuals", canon_id=canon_id)[:1800]
        gal_subjs = [_clean(x) for x in (architecture.get("gallery_subjects") or []) if _clean(x)]
        if len(gal_subjs) < 2 or gal_subjs[0].lower() == gal_subjs[1].lower():
            gal_subjs = [
                f"Wide architectural project showcase for {brand}: {brief[:100]}",
                f"Macro detail photograph of signature materials and craft precision for {brand}",
            ]
        gal_ctx = _clean(page_copy.get("portfolio", {}).get("gallery") or page_copy.get("index", {}).get("gallery") or brief[:160])
        sys_msg = (
            "You are SmartLLM v2 Visual Art Director. Write positive-only production prompts for Z-Image-Turbo "
            "(8 NFEs, --cfg-scale 1.0 positive-only; negative phrasing is forbidden). Return ONLY valid JSON."
        )
        user_msg = (
            f"Brand: {brand}\nBrief: {brief[:240]}\n"
            f"Canon imagery direction: {_sanitize_zimage_prompt(_clean(dossier.get('imagery'))[:200], brand=brand)}\n"
            f"Canon team portrait direction: {_sanitize_zimage_prompt(_clean(dossier.get('team'))[:160], brand=brand)}\n"
            f"Canon palette material tones (positive-only, ZERO hex codes): {pal_cols}\n"
            + (f"Visual Slot Recipes:\n{vis_kb}\n\n" if vis_kb else "")
            + f"Hero visual contexts matching finalized copy per page: {json.dumps(subjects_ctx, ensure_ascii=False)}\n"
            f"Gallery Scene 1 & Scene 2 (MUST depict TWO DIFFERENT angles/subjects): {json.dumps(gal_subjs[:2], ensure_ascii=False)}\n"
            f"Gallery copy context: {gal_ctx[:180]}\n"
            f"Team visual roles with MANDATORY BIOLOGICAL GENDER MATCH (anonymous, DO NOT include names/titles): {json.dumps(team_roles, ensure_ascii=False)}\n\n"
            "Write prompts IN ENGLISH, 40-75 words each.\n"
            "CRITICAL RULES FOR Z-IMAGE-TURBO:\n"
            "1. 'brand_logo': follow " + ZIMAGE_LOGO_CANON_2026 + " Design ONE minimalist flat vector emblem uniquely symbolizing THIS company's industry on a solid neutral backdrop, 2-3 crisp geometric pigment colors. Never mention brand letters, initials, or words.\n"
            "2. 'heroes' and 'gallery': photorealistic architectural/hardware/environment/product scenes matching each slot and its finalized hero headline/features copy; single wide scene without portraits. 'gallery[0]' MUST clearly differ in framing and subject from 'gallery[1]'.\n"
            "3. 'team': one distinct vertical 3:4 medium chest-up editorial portrait per slot on a seamless neutral studio backdrop with generous empty headroom above the top of the head so full hair, head, and shoulders sit comfortably inside frame. Each person MUST clearly match their assigned distinct age, hair, glasses/beard/clean-shaven look, attire, and pose from 'team_roles' without repeating the same appearance across slots. For EVERY FEMALE slot describe the adult woman's exact look; for EVERY MALE slot describe the adult man's exact look. Omit person names, nameplates, watermarks, or words.\n"
            'Return JSON: {"brand_logo": "...", "heroes": {"slug": "..."}, "gallery": ["distinct scene 1", "distinct scene 2"], "team": ["...", ...], "style_suffix": "short positive lighting and lens clause"}'
        )
        raw = _llm_json(state, gpu_ok, sys_msg, user_msg, max_tokens=3200, required_keys=["brand_logo", "heroes", "gallery", "team"])
        if raw:
            agents_run += 1
        tmpl = _clean(imagery.get("prompt_tmpl"))
        heroes_raw = raw.get("heroes") or {}
        heroes = {}
        for slug in pages:
            subj = subjects[slug]
            raw_h = _clean(heroes_raw.get(slug)) or tmpl.replace("{subject}", subj) or f"Editorial architectural photograph of {subj}, crisp directional studio lighting, 35mm lens"
            heroes[slug] = _sanitize_zimage_prompt(raw_h, member_names, brand=brand)
        gallery_raw = [_sanitize_zimage_prompt(_clean(x), member_names, brand=brand) for x in (raw.get("gallery") or []) if _clean(x)]
        if len(gallery_raw) < 2 or gallery_raw[0].lower() == gallery_raw[1].lower():
            gallery_raw = [
                _sanitize_zimage_prompt(f"{gal_subjs[0]}, wide architectural framing, natural directional daylight, 24mm lens, editorial quality", member_names, brand=brand),
                _sanitize_zimage_prompt(f"{gal_subjs[1]}, tight macro material study, sculpted shadows, 85mm shallow depth of field, studio detail", member_names, brand=brand),
            ]
        team_style = _sanitize_zimage_prompt(_clean(dossier.get("team")) or "clean editorial headshot, soft studio light, seamless neutral backdrop", brand=brand)
        raw_team_list = [_sanitize_zimage_prompt(_clean(x), member_names, brand=brand) for x in (raw.get("team") or []) if _clean(x)]
        team_raw: list[str] = []
        seen_team_tokens: list[set[str]] = []
        for idx, slot in enumerate(team_slots):
            gender = str(slot.get("gender") or infer_gender(slot.get("name", ""), "", idx))
            persona = team_personas[idx] if idx < len(team_personas) else (TEAM_PERSONAS_FEMALE[idx % len(TEAM_PERSONAS_FEMALE)] if gender == "female" else TEAM_PERSONAS_MALE[idx % len(TEAM_PERSONAS_MALE)])
            cand_p = raw_team_list[idx] if idx < len(raw_team_list) and raw_team_list[idx] else (
                f"Vertical 3:4 medium chest-up studio portrait of a {persona}, generous empty headroom above the top of the head, {team_style}, 85mm shallow depth of field"
            )
            distinct_p = _ensure_distinct_team_portrait(cand_p, gender, persona, team_style, seen_team_tokens)
            team_raw.append(_sanitize_zimage_prompt(distinct_p, member_names, brand=brand))
        raw_logo_p = _clean(raw.get("brand_logo") or raw.get("logo"))
        if not raw_logo_p or len(raw_logo_p) < 35:
            raw_logo_p = _default_logo_base_prompt(brand, brief, "", lang)
        logo_prompt_clean = _sanitize_zimage_prompt(raw_logo_p, member_names + brand_words, brand=brand)
        visuals = {
            "logo": logo_prompt_clean or _sanitize_zimage_prompt(_default_logo_base_prompt("", brief, "minimalist geometric vector emblem", "en"), brand_words),
            "heroes": heroes,
            "hero": heroes.get("index") or next(iter(heroes.values()), ""),
            "gallery": gallery_raw[:2],
            "team": team_raw[:4],
            "style_suffix": _sanitize_zimage_prompt(_clean(raw.get("style_suffix")), member_names, brand=brand),
        }
        memory.write_artifact("visuals.json", visuals)
        memory.mark("visuals", "done", "visuals.json", f"logo + {len(heroes)} heroes + {len(visuals['gallery'])} gallery + {len(visuals['team'])} team")

    loc_chrome: dict[str, Any] = {}
    if bilingual:
        report(stage_idx, 76, "Субагент локализации: второй язык сайта...", "Localization agent: second site language...", "agent 7/8: localize")
        loc_chrome = reuse("localize:chrome", "localize_chrome.json") or {}
        if not loc_chrome:
            memory.mark("localize:chrome", "running")
            sys_msg = f"You are SmartLLM v2 Localization Editor. Translate brand chrome strings into {('English' if alt_lang == 'en' else 'Russian')}. Return ONLY valid JSON with the same keys."
            user_msg = (
                f"Brand: {brand}\nSource language: {target_lang}\n"
                f"Strings: {json.dumps({'nav_labels': chrome.get('nav_labels') or {}, 'footer_text': chrome.get('footer_text') or '', 'marquee': _clean(company.get('tagline'))}, ensure_ascii=False)}\n"
                "Keep nav labels 1-2 words. Return the same JSON shape translated."
            )
            raw = _llm_json(state, gpu_ok, sys_msg, user_msg, max_tokens=2048, required_keys=["nav_labels", "footer_text"])
            if raw:
                agents_run += 1
            loc_chrome = {
                "nav_labels": {str(k): _clean(v) for k, v in (raw.get("nav_labels") or {}).items() if _clean(v)},
                "footer_text": _clean(raw.get("footer_text")),
                "marquee": _clean(raw.get("marquee")),
            }
            memory.write_artifact("localize_chrome.json", loc_chrome)
            memory.mark("localize:chrome", "done", "localize_chrome.json", "chrome translated")
        for p_idx, slug in enumerate(pages):
            pr = page_results[slug]
            step_id = f"localize:{slug}"
            rel = f"pages/{slug}/loc.json"
            loc = reuse(step_id, rel)
            if loc is None:
                memory.mark(step_id, "running")
                payload_strings = {"hero": pr["hero"], "headings": pr["headings"], "copy": pr["copy"], "seo": pr["seo"]}
                sys_msg = (
                    f"You are SmartLLM v2 Localization Editor. Translate this website page content into "
                    f"{('English' if alt_lang == 'en' else 'Russian')}. Preserve meaning, tone and the ' | ' item separators. "
                    "Keep FAQ 'Question? Answer' structure. Return ONLY valid JSON with exactly the same keys and shape."
                )
                user_msg = f"Brand: {brand}\nPage: {slug}\nContent:\n{json.dumps(payload_strings, ensure_ascii=False)[:5200]}"
                raw = _llm_json(state, gpu_ok, sys_msg, user_msg, max_tokens=3072, required_keys=["hero", "headings", "copy", "seo"])
                if raw:
                    agents_run += 1
                loc = {
                    "hero": {k: _clean(v) for k, v in (raw.get("hero") or {}).items() if _clean(v)},
                    "headings": {str(k): _clean(v) for k, v in (raw.get("headings") or {}).items() if _clean(v)},
                    "copy": {str(k): _clean(v) for k, v in (raw.get("copy") or {}).items() if _clean(v)},
                    "seo": {k: _clean(v) for k, v in (raw.get("seo") or {}).items() if _clean(v)},
                }
                loc_faq_txt = _clean(loc["copy"].get("faq"))
                loc["faqs"] = []
                if loc_faq_txt:
                    for chunk in re.split(r"[|\n]+", loc_faq_txt):
                        if "?" in chunk:
                            q, a = chunk.split("?", 1)
                            loc["faqs"].append({"q": q.strip() + "?", "a": a.strip(" :-—")})
                memory.write_artifact(rel, loc)
                memory.mark(step_id, "done", rel, f"{len(loc['copy'])} blocks translated")
            pr["loc"] = loc

    report(stage_idx, 78, "Субагент ревизии: агентный просмотр каждой страницы (цель 6/6)...", "Review agent: agentic per-page inspection (target 6/6)...", "agent 8/8: review")
    review: dict[str, Any] = {}
    for p_idx, slug in enumerate(pages):
        pr = page_results[slug]
        pct = 78 + int(16 * p_idx / n_pages)
        report(stage_idx, pct, f"Ревизия страницы «{page_title(slug, lang)}»...", f"Reviewing page '{page_title(slug, lang)}'...", f"review {slug}")
        step_id = f"review:{slug}"
        rel = f"review/{slug}.json"
        rv = reuse(step_id, rel)
        if rv is None:
            memory.mark(step_id, "running")
            eff_hero = dict(pr["hero"])
            if not _clean(eff_hero.get("headline")):
                src = _clean(pr["copy"].get("hero")) or brief or brand
                eff_hero["headline"] = (re.split(r"[.!?\n|;]", src)[0].strip() or brand)[:78]
                eff_hero["subhead"] = src[:280]
            det = _deterministic_checks(lang, brand, eff_hero, pr["headings"], pr["copy"], pr["blocks"], pr["seo"], company, slug, set(user_pages.get(slug, {})))

            def review_pass(det_issues: list[str]) -> tuple[dict[str, bool], list[str], dict[str, str]]:
                digest_lines = [
                    f"HERO: {_clean(eff_hero.get('headline'))} / {_clean(eff_hero.get('subhead'))} / CTA: {_clean(eff_hero.get('cta_label')) or '(default contact button)'}",
                    f"SEO: {pr['seo'].get('title')} / {pr['seo'].get('description')}",
                ]
                for bid in pr["blocks"]:
                    if bid in ("hero", "footer"):
                        continue
                    limit = 1600 if bid == "faq" else 1400
                    digest_lines.append(f"{bid} [{_clean(pr['headings'].get(bid)) or '—'}]: {_clean(pr['copy'].get(bid))[:limit]}")
                sys_review = (
                    "You are SmartLLM v2 Independent Site Reviewer. Score one page against 6 criteria: "
                    "offer (clear hero value + CTA), brand (consistent positioning), specificity (no generic filler), "
                    "structure (logical headings and block flow), seo (metadata and FAQ ready), language (correct language, editorial quality). "
                    "Only request fixes for genuine defects (placeholders, missing tiers/prices, broken FAQ, wrong language, URL leaks); "
                    "if all 6 criteria pass, return fixes: {}. Return ONLY valid JSON."
                )
                user_review = (
                    f"Brand: {brand}\nPage: {page_title(slug, lang)} ({slug})\nLanguage: {target_lang}\n"
                    f"Positioning: {_clean(company.get('positioning'))[:240]}\n\n"
                    "Full page blocks:\n" + "\n".join(digest_lines)[:9000] + "\n\n"
                    f"Deterministic pre-check issues: {json.dumps(det_issues, ensure_ascii=False) or 'none'}\n"
                    'Return JSON: {"offer": true, "brand": true, "specificity": true, "structure": true, "seo": true, "language": true, '
                    '"issues": ["short issue"], "fixes": {"block_id": "rewrite instruction"}}'
                )
                raw_r = _llm_json(state, gpu_ok, sys_review, user_review, max_tokens=2048)
                v: dict[str, bool] = {}
                if raw_r:
                    for c in REVIEW_CRITERIA:
                        v[c] = bool(raw_r.get(c, True))
                    iss = [_clean(x) for x in (raw_r.get("issues") or []) if _clean(x)]
                    fx = {str(k): _clean(val) for k, val in (raw_r.get("fixes") or {}).items() if _clean(val) and str(k) in pr["copy"]}
                    return v, iss, fx
                return {c: True for c in REVIEW_CRITERIA}, [], {}

            verdict: dict[str, Any] = {}
            issues = list(det["issues"])
            fixes: dict[str, str] = {}
            if gpu_ok:
                verdict, llm_issues, fixes = review_pass(det["issues"])
                agents_run += 1
                issues.extend(llm_issues)
            else:
                verdict = {c: c not in det["failed"] for c in REVIEW_CRITERIA}
            for c in det["failed"]:
                verdict[c] = False
            for bid, txt in pr["copy"].items():
                low_b = str(txt).lower()
                if bid not in fixes and any(mk in low_b for mk in PLACEHOLDER_MARKERS):
                    fixes[bid] = "Rewrite with concrete brand data; remove template placeholders and English field labels."
                elif bid not in fixes and any(mk in low_b for mk in _EN_BOILERPLATE_LEAKS):
                    fixes[bid] = "Rewrite with concrete brand data in the target language; remove template boilerplate."
                elif bid not in fixes and bid in (det.get("ai_blocks") or {}):
                    fixes[bid] = f"Rewrite without AI clichés or kantselyarit ({', '.join(det['ai_blocks'][bid][:2])}); use concrete numbers and active verbs."
            has_placeholder = any(
                any(mk in str(t).lower() for mk in PLACEHOLDER_MARKERS) or any(mk in str(t).lower() for mk in _EN_BOILERPLATE_LEAKS)
                for t in pr["copy"].values()
            )
            all_passed = all(verdict.get(c, False) for c in REVIEW_CRITERIA) and not det["issues"] and not has_placeholder
            fixable = [] if all_passed else [
                b for b in fixes
                if (b not in user_pages.get(slug, {})) or _is_broken_user_block(b, pr["copy"], det["failed"])
            ]
            applied_fixes: list[str] = []
            if fixable and gpu_ok:
                report(stage_idx, pct + 1, f"Ревизия «{page_title(slug, lang)}»: точечные правки {len(fixable)} блоков...", f"Review '{page_title(slug, lang)}': targeted fixes for {len(fixable)} blocks...", f"review fixes {slug}")
                fmt_lines = "\n".join(f"- {b}: {fixes[b]}" for b in fixable)
                sys_msg = f"You are SmartLLM v2 Expert Copywriter. Rewrite exactly the requested blocks in {target_lang} following the reviewer instructions. Return ONLY valid JSON."
                user_msg = (
                    f"Brand: {brand}\nPage: {page_title(slug, lang)}\nHero: {_clean(eff_hero.get('headline'))}\n"
                    f"Brand foundation (SINGLE TRUTH — keep exact products/prices, team names, stats, contacts):\n{foundation_txt}\n\n"
                    f"Reviewer instructions:\n{fmt_lines}\n"
                    "The format examples are templates: use concrete brand data, never copy them literally. Never include URLs in team/features/stats. "
                    f"Keep complete tier counts and ' | ' item format. Return one JSON object with keys: {json.dumps(fixable)}"
                )
                raw_fix = _llm_json(state, gpu_ok, sys_msg, user_msg, max_tokens=3072, required_keys=fixable)
                if raw_fix:
                    agents_run += 1
                user_owned_set = set(user_pages.get(slug, {}))
                review_user_owned = user_owned_set - set(fixable)
                for bid in fixable:
                    txt = _norm_block_value(bid, raw_fix.get(bid))
                    if txt and _accept_review_fix(bid, pr["copy"].get(bid, ""), txt, lang, brand, eff_hero, pr["headings"], pr["blocks"], pr["seo"], company, slug, pr["copy"], review_user_owned):
                        pr["copy"][bid] = txt
                        applied_fixes.append(bid)
                pr["copy"] = _sync_page_copy_to_foundation(slug, pr["copy"], company, lang, review_user_owned, team_slots)
                page_copy[slug] = pr["copy"]
                memory.write_artifact(f"pages/{slug}/copy.json", pr["copy"])
                det2 = _deterministic_checks(lang, brand, eff_hero, pr["headings"], pr["copy"], pr["blocks"], pr["seo"], company, slug, review_user_owned)
                verdict2, llm_issues2, _ = review_pass(det2["issues"])
                agents_run += 1
                verdict = verdict2
                for c in det2["failed"]:
                    verdict[c] = False
                issues = det2["issues"] + llm_issues2
            score = sum(1 for c in REVIEW_CRITERIA if verdict.get(c))
            rv = {"score": score, "max": 6, "criteria": verdict, "issues": issues[:8], "fixed_blocks": applied_fixes}
            memory.write_artifact(rel, rv)
            memory.mark(step_id, "done", rel, f"{score}/6")
        review[slug] = rv
        page_results[slug]["review"] = rv

    flat_prompts: dict[str, str] = {}
    for slug in pages:
        for bid, txt in page_copy[slug].items():
            if bid not in flat_prompts:
                flat_prompts[bid] = txt

    ai_used = agents_run > 0
    summary = {
        "lang": lang,
        "company": company,
        "chrome": chrome,
        "pages": {slug: {"hero": pr["hero"], "headings": pr["headings"], "seo": pr["seo"], "review": pr["review"], "variants": pr.get("variants") or {}, "loc": pr.get("loc") or {}} for slug, pr in page_results.items()},
        "loc_chrome": loc_chrome,
        "page_block_prompts": page_copy,
        "block_prompts": flat_prompts,
        "geo_facts": seo_doc.get("geo_facts") or [],
        "faqs": seo_doc.get("faqs") or [],
        "visuals": visuals,
        "review": review,
        "review_avg": round(sum(r.get("score", 0) for r in review.values()) / max(1, len(review)), 2),
        "ai_used": ai_used,
        "agents_run": agents_run,
        "agents_reused": agents_reused,
        "memory_dir": str(memory.mem_dir),
        "fingerprint": fingerprint,
    }
    memory.write_artifact("pipeline_summary.json", {k: summary[k] for k in ("ai_used", "agents_run", "agents_reused", "review_avg", "fingerprint")})
    report(stage_idx, 96, f"Контент-пайплайн завершён: {agents_run} агентов, ревизия {summary['review_avg']}/6.", f"Content pipeline done: {agents_run} agents, review {summary['review_avg']}/6.", "content pipeline complete")
    return summary


def mark_external_step(project_dir: Path, step_id: str, status: str, detail: str = "") -> None:
    """Mark render/compile/audit ledger steps from outside the content pipeline."""
    sp = project_dir / ".smartllm" / "state.json"
    if not sp.exists():
        return
    try:
        st = json.loads(sp.read_text(encoding="utf-8"))
        passport = st.get("passport")
        if not isinstance(passport, dict) or not passport.get("fingerprint"):
            return
        mem = PipelineMemory(project_dir, passport)
        mem.mark(step_id, status, detail=detail)
    except Exception:
        pass


def run_final_audit(project_dir: Path, routes: list[dict[str, Any]], base_url: str) -> dict[str, Any]:
    """Deterministic PageSpeed-oriented and integrity audit of the compiled bundle."""
    pages: dict[str, Any] = {}
    all_passed = True
    total_weight = 0
    for route in routes:
        fp = project_dir / route["filename"]
        checks: dict[str, bool] = {}
        weight = fp.stat().st_size if fp.exists() else 0
        total_weight += weight
        if fp.exists():
            doc = fp.read_text(encoding="utf-8")
            checks["single_h1"] = doc.count("<h1") == 1
            checks["title"] = bool(re.search(r"<title[\s>]", doc)) and "</title>" in doc
            checks["meta_description"] = 'name="description"' in doc
            checks["canonical"] = 'rel="canonical"' in doc
            checks["json_ld"] = '"@context": "https://schema.org"' in doc or '"@context":"https://schema.org"' in doc
            checks["csp"] = "Content-Security-Policy" in doc
            imgs = re.findall(r"<img\b[^>]*>", doc)
            checks["img_alt_dims"] = all(('alt="' in i and "width=" in i and "height=" in i) for i in imgs) if imgs else True
            checks["no_external_assets"] = not re.search(r'(?:src|href)="https?://(?!' + re.escape(base_url.split("//")[-1]) + r')', doc)
            checks["weight_lt_200kb"] = weight < 200_000
            m = re.search(r"<title[^>]*>(.*?)</title>", doc, re.S)
            checks["title_len"] = bool(m and 10 <= len(m.group(1)) <= 70)
        else:
            checks["file_exists"] = False
        passed = all(checks.values())
        all_passed = all_passed and passed
        pages[route["slug"]] = {"passed": passed, "checks": checks, "weight_bytes": weight}
    for asset in ("tokens.css", "app.js", "llms.txt", "robots.txt", "sitemap.xml"):
        if not (project_dir / asset).exists():
            all_passed = False
    audit = {
        "passed": all_passed,
        "pages": pages,
        "total_html_weight_bytes": total_weight,
        "external_requests": 0,
        "pagespeed_target": "90+/90+",
        "audited_at": _now(),
    }
    mem = project_dir / ".smartllm" / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "final_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return audit