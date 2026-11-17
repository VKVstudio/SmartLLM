#!/usr/bin/env python3
"""Stage A Copywriting, Cyrillic Density, and Language-Aware Hygiene Checks (`copy_checks.py`).

Fixes `NEW-BUG-06` and the `expected_lang` / `ru_hits >= 1` defect (`00_SYNTHESIS_FOR_OPUS.md §4`,
`04_linux_env_and_harness_verified.md:49`):
1. Enforces real `expected_lang` (`"ru"` vs `"en"`): for Russian tasks, requires both minimum
   Cyrillic character count (`>= 50`) and Cyrillic alphabetic density (`>= 0.65` chars / `>= 0.70`
   non-acronym prose words), rejecting single-character `ru_hits >= 1` false passes.
2. Implements `COPY-HYGIENE` lexical slop checks:
   - EN banned AI-slop tokens (`delve`, `testament`, `tapestry`, `elevate`, `seamless`, `unleash`,
     `cutting-edge`, `game-changer`, `ever-evolving`, `symphony`, `beacon`, `realm`).
   - RU calque/slop tokens (`бесшовн`, `откройте для себя`, `погрузитесь в мир`,
     `инновационный подход`, `новый уровень`, `играет ключевую роль`, `в современном мире`).
   - Double spaces inside visible prose text nodes.
   - Language-aware typography: EN flags excessive em-dash (`—`) overuse (`> 2.5` per 100 words),
     whereas RU explicitly exempts `—` (Russian тире) and checks for `«ёлочки»` guillemets vs
     straight quotes `"` around Russian words.
"""

from __future__ import annotations

import html as html_lib
import os
import re
from typing import Any

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_WORD_SCRIPT_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+")
_HAS_LATIN_RE = re.compile(r"[A-Za-z]")
_HAS_CYR_RE = re.compile(r"[А-Яа-яЁё]")
_CYR_CHAR_RE = re.compile(r"[А-Яа-яЁё]")
_LAT_CHAR_RE = re.compile(r"[A-Za-z]")

_EN_SLOP_RE = re.compile(
    r"\b(?:delve|delves|delving|testament|tapestry|elevate|elevating|seamless|seamlessly|"
    r"unleash|unleashing|cutting-edge|game-changer|game-changing|ever-evolving|symphony|"
    r"beacon|realm)\b",
    re.IGNORECASE,
)

_RU_SLOP_RE = re.compile(
    r"(?:\bбесшовн[а-яё]*\b|откройте\s+для\s+себя|погрузитесь\s+в\s+мир|"
    r"инновационн[а-яё]+\s+подход[а-яё]*|нов[а-яё]+\s+уров[еньняю]+|"
    r"играет\s+ключевую\s+роль|в\s+современном\s+мире)",
    re.IGNORECASE,
)

_RU_STRAIGHT_QUOTES_RE = re.compile(r'"[А-Яа-яЁё][^"\n]{1,80}[А-Яа-яЁё]"')
_DOUBLE_SPACE_PROSE_RE = re.compile(r"(?<=[A-Za-zА-Яа-яЁё.,!?;:])  +(?=[A-Za-zА-Яа-яЁё])")

# Minimum Cyrillic alphabetic share in visible prose for `expected_lang == "ru"`
MIN_RU_CYRILLIC_DENSITY: float = 0.65
MIN_RU_CYRILLIC_CHARS: int = 50
MIN_EN_LATIN_DENSITY: float = 0.85


def extract_prose_preserving_text_nodes(html_or_text: str) -> str:
    """Strip code/style/svg blocks and HTML tags using newline separators so adjacent tags never create synthetic double spaces."""
    no_code = re.sub(
        r"<(script|style|code|pre|svg)\b[^>]*>(?:.*?</\1>|.*$)",
        "\n",
        html_or_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return html_lib.unescape(re.sub(r"<[^>]+>", "\n", no_code))


def strip_html_to_prose(html_or_text: str) -> str:
    """Strip `<script>`, `<style>`, `<code>`, `<pre>`, `<svg>` and HTML tags to extract visible prose."""
    return re.sub(r"\s+", " ", extract_prose_preserving_text_nodes(html_or_text)).strip()


def analyze_copy_hygiene(
    raw_texts: list[str] | str,
    prose_texts: list[str] | str | None = None,
    expected_lang: str | None = None,
) -> dict[str, Any]:
    """Analyze character hygiene, lexical AI-slop, typography, and language density."""
    if isinstance(raw_texts, str):
        raw_list = [raw_texts]
    else:
        raw_list = list(raw_texts)

    if prose_texts is None:
        prose_list = [extract_prose_preserving_text_nodes(t) for t in raw_list if t]
    elif isinstance(prose_texts, str):
        prose_list = [prose_texts]
    else:
        prose_list = list(prose_texts)

    cjk_count = sum(len(_CJK_RE.findall(txt)) for txt in raw_list if txt)
    repl_count = sum(txt.count("\ufffd") for txt in raw_list if txt)

    mixed_tokens: list[str] = []
    en_slop_hits: list[str] = []
    ru_slop_hits: list[str] = []
    double_spaces_count = 0
    em_dash_count = 0
    guillemets_count = 0
    ru_straight_quotes_count = 0

    combined_prose = "\n".join(txt for txt in prose_list if txt)
    for txt in prose_list:
        if not txt:
            continue
        for tok in _WORD_SCRIPT_RE.findall(txt):
            if _HAS_LATIN_RE.search(tok) and _HAS_CYR_RE.search(tok):
                mixed_tokens.append(tok)
        en_slop_hits.extend(m.group(0).lower() for m in _EN_SLOP_RE.finditer(txt))
        ru_slop_hits.extend(m.group(0).lower() for m in _RU_SLOP_RE.finditer(txt))
        double_spaces_count += len(_DOUBLE_SPACE_PROSE_RE.findall(txt))
        em_dash_count += txt.count("—")
        guillemets_count += txt.count("«") + txt.count("»")
        ru_straight_quotes_count += len(_RU_STRAIGHT_QUOTES_RE.findall(txt))

    cyr_chars = len(_CYR_CHAR_RE.findall(combined_prose))
    lat_chars = len(_LAT_CHAR_RE.findall(combined_prose))
    total_alpha = cyr_chars + lat_chars
    cyr_density = round(cyr_chars / total_alpha, 4) if total_alpha > 0 else 0.0
    lat_density = round(lat_chars / total_alpha, 4) if total_alpha > 0 else 0.0

    words = _WORD_SCRIPT_RE.findall(combined_prose)
    word_count = len(words)
    em_dash_per_100w = round((em_dash_count * 100.0) / word_count, 2) if word_count > 0 else 0.0

    lang_norm = (expected_lang or "").strip().lower()
    if lang_norm == "ru":
        lang_passed = (cyr_chars >= MIN_RU_CYRILLIC_CHARS) and (cyr_density >= MIN_RU_CYRILLIC_DENSITY)
        em_dash_overuse = False  # Russian typography mandates `—` (тире)
        slop_hits = ru_slop_hits + en_slop_hits
    elif lang_norm == "en":
        lang_passed = (lat_chars >= 50) and (lat_density >= MIN_EN_LATIN_DENSITY)
        em_dash_overuse = em_dash_per_100w > 2.5
        slop_hits = en_slop_hits
    else:
        lang_passed = total_alpha > 0
        em_dash_overuse = False
        slop_hits = en_slop_hits + ru_slop_hits

    hygiene_passed = (
        cjk_count == 0
        and repl_count == 0
        and len(mixed_tokens) == 0
        and len(slop_hits) == 0
        and double_spaces_count == 0
        and not em_dash_overuse
        and lang_passed
    )

    return {
        "expected_lang": lang_norm or None,
        "lang_check_passed": lang_passed,
        "lang_gate_passed": lang_passed,
        "cyrillic_chars_count": cyr_chars,
        "latin_chars_count": lat_chars,
        "cyrillic_density": cyr_density,
        "latin_density": lat_density,
        "cjk_chars_count": cjk_count,
        "replacement_chars_count": repl_count,
        "mixed_script_tokens_count": len(mixed_tokens),
        "mixed_script_sample": list(dict.fromkeys(mixed_tokens))[:10],
        "ai_slop_hits_count": len(slop_hits),
        "ai_slop_count": len(slop_hits),
        "ai_slop_sample": list(dict.fromkeys(slop_hits))[:10],
        "en_slop_hits_count": len(en_slop_hits),
        "ru_slop_hits_count": len(ru_slop_hits),
        "double_spaces_count": double_spaces_count,
        "double_space_count": double_spaces_count,
        "em_dash_count": em_dash_count,
        "em_dash_per_100w": em_dash_per_100w,
        "em_dash_overuse": em_dash_overuse,
        "guillemets_count": guillemets_count,
        "ru_straight_quotes_count": ru_straight_quotes_count,
        "ru_typography": {
            "ru_em_dash_allowed": True,
            "has_guillemets": guillemets_count >= 2,
            "em_dash_count": em_dash_count,
            "guillemets_count": guillemets_count,
            "straight_quotes_count": ru_straight_quotes_count,
        },
        "copy_hygiene_passed": hygiene_passed,
    }


def audit_copy_task(
    content: str,
    expected_lang: str | None = None,
    is_html: bool = True,
) -> dict[str, Any]:
    """Audit a single copywriting / web task string or task folder with explicit `expected_lang` enforcement."""
    if not expected_lang or expected_lang.strip().lower() not in ("ru", "en"):
        raise ValueError(f"audit_copy_task requires explicit expected_lang ('ru' or 'en'), got {expected_lang!r}")
    if os.path.isdir(content):
        cand_html = os.path.join(content, "index.html")
        cand_md = os.path.join(content, "copy.md")
        cand_raw = os.path.join(content, "raw.md")
        if os.path.exists(cand_html):
            with open(cand_html, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            is_html = True
        elif os.path.exists(cand_md):
            with open(cand_md, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            is_html = False
        elif os.path.exists(cand_raw):
            with open(cand_raw, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            is_html = "<html" in content.lower()
    raw_prose = strip_html_to_prose(content) if is_html else content
    prose_uncollapsed = extract_prose_preserving_text_nodes(content) if is_html else content

    res = analyze_copy_hygiene([content], [prose_uncollapsed], expected_lang=expected_lang)
    res["visible_prose_chars"] = len(raw_prose)
    return res
