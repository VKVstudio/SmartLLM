#!/usr/bin/env python3
"""Deterministic builder & hygiene verifier for 168 EN+RU copy pairs and tone guides."""

import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from copy_data_part1 import PAIRS_PART1  # noqa: E402
from copy_data_part2 import PAIRS_PART2  # noqa: E402

HARVEST_DIR = "/mnt/rescue/projects/SmartLLM/data/harvest"
COPY_DIR = os.path.join(HARVEST_DIR, "copy_pairs")
CARDS_DIR = os.path.join(HARVEST_DIR, "canon_cards")
CURATED_DATE = "2026-11-15"

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
WORD_SCRIPT_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+")
HAS_LATIN_RE = re.compile(r"[A-Za-z]")
HAS_CYR_RE = re.compile(r"[А-Яа-яЁё]")

BANNED_EN_SLOP = [
    "delve", "testament", "tapestry", "unleash", "elevate", "seamless",
    "seamlessly", "game-changer", "unlock", "cutting-edge", "revolutionary",
    "revolutionizing", "realm", "ever-evolving", "skyrocketed", "supercharge",
    "blazingly",
]
BANNED_RU_SLOP = [
    "погрузимся", "безусловно", "революционн", "инновационн",
    "в современном мире", "динамично развивающ", "бесшовн",
    "вывести на новый уровень", "выведите", "под ключ", "уникальн",
    "непревзойдённ", "незабываем",
]

RU_GUIDE_MD = """# Русский редакционный и B2B/SaaS канон (RAG Reference)

**Статус:** RAG-only (`data/harvest/copy_pairs/`) | **Дата:** 2026-11-15 | **Назначение:** Few-shot и контроль чистоты русского текста

## 1. Синтаксис и морфология (активный глагол вместо канцелярита)
1. **Личные глаголы действия вместо отглагольных существительных:**
   - Плохо: *«Осуществляется произведение расчёта параметров задержки и обеспечение сохранности реплик»*.
   - Канон: *«Прокси считает задержку каждые 100 мс и сохраняет реплики на трёх узлах»*.
2. **Прямой порядок слов без кальки с английского:**
   - Избегай пассивных связок *«является решением для...»*, *«позволяет вам наслаждаться...»*, *«разработан с любовью к деталям»*.
   - Называй субъект, физический механизм и измеримый результат в первом предложении.
3. **Числовая фактура вместо оценочных прилагательных:**
   - Запрещены пустые усилители (*уникальный, инновационный, передовой, бесшовный, революционный, под ключ, безусловно*).
   - Вместо *«мгновенный отклик»* пиши *«отклик p99 за 4,6 мс при 120 Гц»*; вместо *«надёжное хранение»* пиши *«буфер pSLC на 72 часа при -40 C»*.

## 2. Типографика и гигиена смешанных алфавитов (Zero Homoglyphs)
1. **Строгое разделение кириллицы и латиницы через дефис или пробел:**
   - Никогда не склеивай латинские аббревиатуры с кириллическими окончаниями или корнями без дефиса: пиши `B2B-платформа`, `API-ключ`, `TLS-сессия`, `NVMe-диск`, `SQL-запрос`, `FIDO2-токен`.
   - Проверяй отсутствие латинских букв-двойников (`a, c, e, o, p, x, K, M, H, B, T`) внутри русских слов.
2. **Чистая пунктуация и кавычки:**
   - В русском тексте используй кавычки-«ёлочки» (`«...»`), а при вложенности - кавычки-„лапки“.
   - Не используй длинное тире (`—`) как универсальную замену двоеточию, запятой или глаголу-связке; строй ясные сложноподчинённые предложения либо ставь двоеточие перед перечислением и выводом.
   - Десятичный разделитель в русской технической прозе - запятая (`4,6 мс`, `99,6%`, `1,2%`), кроме синтаксиса кода и CSS (`0.45rem`, `oklch(...)`).
3. **Запрет восточноазиатских и битых символов:**
   - В тексте должно быть ровно `0` иероглифов CJK и `0` символов замены `U+FFFD`.

## 3. Структура B2B-блоков и AEO-ответов
1. **Формула первого экрана (`H1 + Подзаголовок + CTA`):**
   - `H1`: Что делает продукт + для какого контура + главное ограничение/метрика (`<= 12` слов).
   - `Подзаголовок`: Как устроен механизм внутри и чем подтверждён ресурс (`1-2` предложения).
   - `CTA`: Глагол в инфинитиве + точный артефакт/длительность + снятие барьера (*«Скопировать команду установки (14 МБ, без регистрации)»*).
2. **Перевёрнутая пирамида для FAQ (`Schema.org FAQPage`):**
   - Первое предложение начинается с прямого ответа (*«Да, агент работает автономно...»* или точного порога/стандарта).
   - Второе предложение даёт версию ядра, размер пакета, срок хранения или номер ГОСТ / СП / ISO.
   - Текст вопроса и ответа в JSON-LD обязан совпадать с видимым HTML-текстом посимвольно.
"""

EN_GUIDE_MD = """# English B2B, Technical & AEO Copywriting Canon (RAG Reference)

**Status:** RAG-only (`data/harvest/copy_pairs/`) | **Date:** 2026-11-15 | **Scope:** Few-shot retrieval & deterministic copy hygiene

## 1. Core Lexical & Structural Rules
1. **Mechanism Over Adjective:**
   - Replace unverifiable superlatives (*blazingly fast, seamless, revolutionary, military-grade, cutting-edge, game-changer, effortless*) with physical or algorithmic mechanisms, units, and test conditions.
   - Bad: *"Experience blazingly fast analytics at any scale."*
   - Canon: *"SIMD AVX2 scans over Zstd Parquet evaluate 1.1B event rows in 380 ms on a single 16-core node."*
2. **Banned AI Throat-Clearing & Clichés:**
   - Never open headings, essays, or FAQ answers with: *In today's fast-paced world, Let's delve into, Testament to, Rich tapestry, Unleash, Elevate, Unlock potential, Ever-evolving landscape, Realm*.
   - Never use em-dashes (`—`) as rhetorical crutches; use colons, semicolons, parentheses, or crisp active verbs.
3. **Pain -> Mechanism -> Verifiable Proof (`PMP`):**
   - **Sentence 1 (Pain):** Name the concrete operational failure mode and its cost/latency (e.g., *"DNS Postgres failovers stall clients for 45-90s on stale TTLs"*).
   - **Sentence 2 (Mechanism):** Explain how the architecture resolves that exact failure (e.g., *"Our proxy holds client sockets in RAM while promoting the Raft standby via WAL replay"*).
   - **Sentence 3 (Proof):** Provide sample size `N`, median/p99 measurement, and error floor (e.g., *"Across 1,400 production switchovers, median write pause measured 310 ms with zero dropped transactions"*).

## 2. CTA & Microcopy Honesty
1. **Zero-Surprise CTAs:**
   - Never write vague buttons (*Get Started, Learn More, Click Here, Submit*).
   - Name the exact deliverable, file format/size, duration, and friction floor (*"Open live read-only trace sandbox (50M spans, zero card required)"*).
2. **Diagnostic Empty & Error States:**
   - Never blame the user (*"Oops! Invalid input"*). State the expected format, digit count, concrete example, and what the parser normalizes automatically.
   - Turn empty telemetry states into copyable CLI diagnostic commands.

## 3. AEO / GEO Citation Readiness
1. **40-60 Word Inverted-Pyramid FAQ Answers:**
   - Answer the H2/H3 question directly in the first clause, followed by version thresholds, compliance standards (`ISO-14064`, `WCAG 2.2 2.5.8`, `FIPS-203`), or retention windows.
   - Maintain 100% character-for-character parity between visible `<main>` FAQ text and `application/ld+json` `FAQPage` entities.
"""


def check_mixed_script(text: str, label: str) -> None:
    if CJK_RE.search(text):
        raise AssertionError(f"{label}: contains forbidden CJK character")
    if "\ufffd" in text:
        raise AssertionError(f"{label}: contains U+FFFD replacement char")
    for tok in WORD_SCRIPT_RE.findall(text):
        if HAS_LATIN_RE.search(tok) and HAS_CYR_RE.search(tok):
            raise AssertionError(f"{label}: mixed Latin/Cyrillic token '{tok}'")


def main() -> None:
    os.makedirs(COPY_DIR, exist_ok=True)
    known_canons = {
        fn[:-5] for fn in os.listdir(CARDS_DIR) if fn.endswith(".json")
    }

    all_pairs = PAIRS_PART1 + PAIRS_PART2
    if len(all_pairs) < 150:
        raise AssertionError(f"Expected >= 150 pairs, got {len(all_pairs)}")

    seen_ids = set()
    records = []

    for p in all_pairs:
        pid = p["id"]
        if pid in seen_ids:
            raise AssertionError(f"Duplicate pair id: {pid}")
        seen_ids.add(pid)

        if p["canon_id"] not in known_canons:
            raise AssertionError(f"{pid}: unknown canon_id '{p['canon_id']}'")

        for field in ("en_slop_before", "en_canon_after", "ru_slop_before", "ru_canon_after", "anti_slop_rule"):
            val = p[field]
            check_mixed_script(val, f"{pid}.{field}")
            if "  " in val:
                raise AssertionError(f"{pid}.{field}: contains double spaces")

        en_after = p["en_canon_after"]
        ru_after = p["ru_canon_after"]

        if "\u2014" in en_after or "\u2014" in ru_after:
            raise AssertionError(f"{pid}: em-dash found in canon_after")

        en_low = en_after.lower()
        for bad in BANNED_EN_SLOP:
            if re.search(r"\b" + re.escape(bad) + r"\b", en_low):
                raise AssertionError(f"{pid}.en_canon_after: contains banned slop '{bad}'")

        ru_low = ru_after.lower()
        for bad in BANNED_RU_SLOP:
            if bad in ru_low:
                raise AssertionError(f"{pid}.ru_canon_after: contains banned RU slop '{bad}'")

        if len(HAS_CYR_RE.findall(ru_after)) < 25:
            raise AssertionError(f"{pid}.ru_canon_after: insufficient Cyrillic content")
        if len(HAS_LATIN_RE.findall(en_after)) < 25:
            raise AssertionError(f"{pid}.en_canon_after: insufficient Latin content")

        rec = {
            "id": pid,
            "category": p["category"],
            "domain": p["domain"],
            "canon_id": p["canon_id"],
            "en_slop_before": p["en_slop_before"],
            "en_canon_after": en_after,
            "ru_slop_before": p["ru_slop_before"],
            "ru_canon_after": ru_after,
            "anti_slop_rule": p["anti_slop_rule"],
            "provenance": {
                "source": "SmartLLM v2 Curated EN/RU Domain Copy Bank (TZ §4)",
                "curated_date": CURATED_DATE,
                "license": "CC0-1.0 / Internal RAG Canon",
                "rag_only": True,
            },
        }
        records.append(rec)

    check_mixed_script(RU_GUIDE_MD, "ru_b2b_saas_editorial_tone_guide.md")
    check_mixed_script(EN_GUIDE_MD, "en_conversion_aeo_copy_guide.md")

    jsonl_path = os.path.join(COPY_DIR, "copy_patterns_en_ru.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    ru_path = os.path.join(COPY_DIR, "ru_b2b_saas_editorial_tone_guide.md")
    with open(ru_path, "w", encoding="utf-8") as fh:
        fh.write(RU_GUIDE_MD)

    en_path = os.path.join(COPY_DIR, "en_conversion_aeo_copy_guide.md")
    with open(en_path, "w", encoding="utf-8") as fh:
        fh.write(EN_GUIDE_MD)

    print(f"Built {len(records)} verified EN+RU copy pairs and 2 tone guides in {COPY_DIR}")


if __name__ == "__main__":
    main()
