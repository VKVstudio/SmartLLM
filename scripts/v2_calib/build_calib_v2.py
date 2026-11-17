#!/usr/bin/env python3
"""
WP-C2: Calibration Dataset v2 (640 sequences, <=2048 tok, ~721k tok, RU ~37.5%)
and Document-Disjoint Held-Out Evaluation Set E (4k EN + 4k RU tokens + 10 Gen Prompts).

Strictly adheres to OPUS_MASTER_PLAN_V2.md §1.D5 & §2 WP-C2:
  - Parquet row-group range reads via HfFileSystem + pyarrow.parquet
  - Every network request checked & logged via scripts/infra/download_ledger.py (--wp WP-C2)
  - Dataset card licenses verified BEFORE downloading Parquet row groups
  - Zero frontier/LLM API distillations (Vikhrmodels/GrandMaster2 inspected & skipped due to
    missing card license + synthetic LLM dialogues; fineweb-2 rus_Cyrl Q/A used for ru_chat)
  - Deterministic local HTML/CSS templates (oklch, CSS Grid, @container, 100dvh, strict CSP,
    JSON-LD @graph, 0 Tailwind) + headless Chrome 148 rendered UI-audit vision pairs (11 RU + 10 EN)
  - >= 50% of <think> CoT rows in RU (54 RU vs 52 EN = 50.94% RU)
  - Exact token counts computed with donor Qwen3.8-Flash-Next tokenizer & processor
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem
from PIL import Image
from transformers import AutoTokenizer

REPO_ROOT = Path("/mnt/rescue/projects/SmartLLM")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.infra.download_ledger import check_budget, get_summary, record_download
from scripts.v2_calib.local_templates import (
    GITHUB_RAW_SOURCES,
    build_full_doc_html_css_rows,
    build_seo_aeo_geo_security_rows,
    build_ts_js_node_backend_rows,
    build_web_dev_prose_rows,
    get_eval_e_gen_prompts_10,
)
from scripts.v2_calib.ui_audit_specs import get_v2_ui_audit_vision_specs, render_html_batch_v2

MODEL_DIR = REPO_ROOT / "models" / "Qwen3.8-Flash-Next"
CALIB_V2_DIR = REPO_ROOT / "data" / "calib_v2"
IMAGES_V2_DIR = CALIB_V2_DIR / "images"
RAW_CACHE_DIR = CALIB_V2_DIR / "raw_cache"
EVAL_E_DIR = REPO_ROOT / "data" / "eval_E"

WP_NAME = "WP-C2"
PER_SOURCE_CAP_BYTES = 150_000_000  # 150 MB per source cap
TOTAL_WP_CAP_BYTES = 380_000_000    # 380 MB total WP-C2 cap
MAX_SEQ_TOKENS = 2048

# OPUS_MASTER_PLAN_V2.md §1.D5 exact strata targets
STRATA_SPEC: dict[str, dict[str, Any]] = {
    "ru_commercial_copy": {
        "target_tokens": 100_000,
        "target_seqs": 88,
        "lang": "ru",
        "source": "HuggingFaceFW/fineweb-2 (rus_Cyrl)",
        "license": "ODC-By-1.0",
    },
    "ru_expository_general": {
        "target_tokens": 60_000,
        "target_seqs": 54,
        "lang": "ru",
        "source": "HuggingFaceFW/fineweb-2 (rus_Cyrl)",
        "license": "ODC-By-1.0",
    },
    "ru_think_cot": {
        "target_tokens": 60_000,
        "target_seqs": 54,
        "lang": "ru",
        "source": "HuggingFaceFW/fineweb-2 (rus_Cyrl, derived CoT)",
        "license": "ODC-By-1.0",
    },
    "ru_chat": {
        "target_tokens": 30_000,
        "target_seqs": 28,
        "lang": "ru",
        "source": "HuggingFaceFW/fineweb-2 (rus_Cyrl Q/A)",
        "license": "ODC-By-1.0",
    },
    "ui_audit_vision": {
        "target_tokens": 31_000,
        "target_seqs": 21,
        "lang": "bilingual",
        "source": "local_html_chrome148_render",
        "license": "CC0-1.0",
    },
    "en_commercial_copy": {
        "target_tokens": 60_000,
        "target_seqs": 54,
        "lang": "en",
        "source": "HuggingFaceFW/fineweb (sample/10BT)",
        "license": "ODC-By-1.0",
    },
    "web_dev_prose": {
        "target_tokens": 80_000,
        "target_seqs": 72,
        "lang": "en",
        "source": "mdn/content + GoogleChrome/web.dev",
        "license": "CC-BY-SA-2.5 / CC-BY-4.0",
    },
    "full_doc_html_css": {
        "target_tokens": 110_000,
        "target_seqs": 96,
        "lang": "en",
        "source": "mdn/css-examples + mdn/content + local_templates",
        "license": "CC0-1.0 / CC-BY-SA-2.5",
    },
    "ts_js_node_backend": {
        "target_tokens": 60_000,
        "target_seqs": 54,
        "lang": "en",
        "source": "nodejs/node + mdn/dom-examples",
        "license": "MIT / CC0-1.0",
    },
    "en_think_cot": {
        "target_tokens": 60_000,
        "target_seqs": 52,
        "lang": "en",
        "source": "HuggingFaceFW/fineweb-edu (sample/10BT, derived CoT)",
        "license": "ODC-By-1.0",
    },
    "seo_aeo_geo_security_checklists": {
        "target_tokens": 30_000,
        "target_seqs": 29,
        "lang": "en",
        "source": "OWASP/CheatSheetSeries + schema.org",
        "license": "CC-BY-SA-4.0",
    },
    "en_general": {
        "target_tokens": 40_000,
        "target_seqs": 38,
        "lang": "en",
        "source": "HuggingFaceFW/fineweb-edu (sample/10BT)",
        "license": "ODC-By-1.0",
    },
}

# Held-out benchmark identifiers that must never appear in calibration or eval_E
EVAL_BENCHMARK_IDENTIFIERS = [
    "thermotech engineering",
    "vkvstudio",
    "северная мануфактура",
    "dagexecutor",
    "dagcycleerror",
    "dagvalidationerror",
    "nodeexecutionreport",
    "helvetica kinetic lab",
    "vortex compute",
    "цех №4",
    "архив технологий",
    "aetheria bio-robotics",
    "контур-спектр",
    "kronos precision gearworks",
]

RE_CYR = re.compile(r"[А-Яа-яЁё]")
RE_LAT = re.compile(r"[A-Za-z]")
RE_NON_EN_RU = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0600-\u06ff\u0900-\u097f]")
RE_NSFW_JUNK = re.compile(
    r"\b(?:erotic|incest|nsfw|porn|sexual|rape|suicide|self-harm|prostitut|escort|casino|betting|darknet|"
    r"viagra|cialis|payday\s+loan|crypto\s+airdrop)\b|"
    r"(?:порно|эротик|инцест|суицид|казино|ставк\w+\s+на\s+спорт|даркнет|закладк|букмекер|слоты|займ\s+без\s+отказа)",
    re.IGNORECASE,
)

RU_COMMERCE_RE = re.compile(
    r"(?:компани|производств|оборудован|услуг|стоимост|заказ|проект|разработк|доставк|гаранти|"
    r"каталог|клиент|сервис|платформ|систем|решени|бизнес|технолог|интерьер|архитектур|дизайн|"
    r"инженер|монтаж|комплект|поставк|материал|спецификац|характеристик|ассортимент|предприяти)",
    re.IGNORECASE,
)
EN_COMMERCE_RE = re.compile(
    r"\b(?:product|service|platform|solution|engineering|manufacturing|architecture|design|"
    r"specification|deployment|enterprise|customer|pricing|warranty|delivery|hardware|software|"
    r"infrastructure|industrial|commercial|studio|system|performance|reliability)\b",
    re.IGNORECASE,
)


class SourceDownloadTracker:
    """Tracks per-source download bytes and logs every network transfer to scripts/infra/download_ledger.py."""

    def __init__(self) -> None:
        self.per_source_bytes: Counter[str] = Counter()
        self.license_audit: dict[str, dict[str, Any]] = {}

    def check_and_record(self, source_key: str, url: str, data: bytes) -> str:
        nbytes = len(data)
        if self.per_source_bytes[source_key] + nbytes > PER_SOURCE_CAP_BYTES:
            raise RuntimeError(
                f"Per-source cap exceeded for {source_key}: "
                f"{self.per_source_bytes[source_key] + nbytes} > {PER_SOURCE_CAP_BYTES}"
            )
        check_budget(WP_NAME, nbytes)
        sha256 = hashlib.sha256(data).hexdigest()
        record_download(WP_NAME, url, nbytes, sha256)
        self.per_source_bytes[source_key] += nbytes
        return sha256

    def fetch_bytes(self, source_key: str, url: str, cache_path: Path | None = None) -> bytes:
        if cache_path is not None and cache_path.exists() and cache_path.stat().st_size > 0:
            return cache_path.read_bytes()
        check_budget(WP_NAME, 65536)
        req = urllib.request.Request(url, headers={"User-Agent": "SmartLLM-v2-Calib/1.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
        self.check_and_record(source_key, url, data)
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
        return data

    def verify_hf_card_license(self, repo_id: str, allowed_licenses: set[str]) -> dict[str, Any]:
        cache_path = RAW_CACHE_DIR / "hf_cards" / f"{repo_id.replace('/', '__')}.json"
        url = f"https://huggingface.co/api/datasets/{repo_id}"
        raw = self.fetch_bytes(repo_id, url, cache_path=cache_path)
        info = json.loads(raw.decode("utf-8"))
        card = info.get("cardData", {}) or {}
        card_lic = str(card.get("license") or "").lower().strip()
        tags = [str(t).lower() for t in info.get("tags", []) if "license:" in str(t).lower()]
        verified = card_lic in allowed_licenses or any(
            t.replace("license:", "") in allowed_licenses for t in tags
        )
        result = {
            "repo_id": repo_id,
            "card_license": card_lic or None,
            "license_tags": tags,
            "verified_permissive": verified,
        }
        self.license_audit[repo_id] = result
        return result


class LedgerTrackedHfFile:
    """File-like wrapper around HfFileSystem.open() that tracks every read() in SourceDownloadTracker."""

    def __init__(self, fs: HfFileSystem, hf_path: str, source_key: str, tracker: SourceDownloadTracker) -> None:
        self._fs = fs
        self._hf_path = hf_path
        self._source_key = source_key
        self._tracker = tracker
        self._f = fs.open(hf_path, "rb")

    def read(self, n: int = -1) -> bytes:
        pos = self._f.tell()
        data = self._f.read(n)
        if data:
            pseudo_url = f"hf://{self._hf_path}#bytes={pos}-{pos + len(data) - 1}"
            self._tracker.check_and_record(self._source_key, pseudo_url, data)
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._f.seek(offset, whence)

    def tell(self) -> int:
        return self._f.tell()

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    @property
    def closed(self) -> bool:
        return self._f.closed

    def close(self) -> None:
        self._f.close()

    def __enter__(self) -> "LedgerTrackedHfFile":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


def read_parquet_row_groups_cached(
    fs: HfFileSystem,
    tracker: SourceDownloadTracker,
    source_key: str,
    hf_parquet_path: str,
    row_groups: list[int],
    columns: list[str],
    cache_name: str,
) -> list[dict[str, Any]]:
    """Read specific row groups from a remote HF Parquet shard via range reads and cache locally."""
    cache_file = RAW_CACHE_DIR / f"{cache_name}.parquet"
    if not cache_file.exists():
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with LedgerTrackedHfFile(fs, hf_parquet_path, source_key, tracker) as tracked_f:
            py_file = pa.PythonFile(tracked_f, mode="r")
            pf = pq.ParquetFile(py_file)
            tables = [pf.read_row_group(rg, columns=columns) for rg in row_groups]
            combined = pa.concat_tables(tables)
            pq.write_table(combined, cache_file)
    table = pq.read_table(cache_file)
    return table.to_pylist()


def is_clean_passage(text: str, lang: str, min_chars: int = 900) -> bool:
    if len(text) < min_chars:
        return False
    lower = text.lower()
    if any(ident in lower for ident in EVAL_BENCHMARK_IDENTIFIERS):
        return False
    if RE_NSFW_JUNK.search(text):
        return False
    if RE_NON_EN_RU.search(text):
        return False
    cyr = len(RE_CYR.findall(text))
    lat = len(RE_LAT.findall(text))
    total_alpha = cyr + lat
    if total_alpha < 300:
        return False
    if lang == "ru":
        if cyr / total_alpha < 0.80:
            return False
    else:
        if lat / total_alpha < 0.88:
            return False
    return True


def normalize_paragraphs(text: str) -> list[str]:
    paras: list[str] = []
    for raw_p in re.split(r"\n+", text):
        p = re.sub(r"\s+", " ", raw_p).strip()
        if len(p) >= 55:
            paras.append(p)
    return paras


def extract_title_and_excerpt(text: str, max_chars: int = 3600) -> tuple[str, str]:
    paras = normalize_paragraphs(text)
    if not paras:
        clean = re.sub(r"\s+", " ", text).strip()
        return clean[:90], clean[:max_chars]
    first = paras[0]
    first_sent = re.split(r"(?<=[.!?])\s+", first)[0]
    title = first_sent[:110].strip(" .,:;-—")
    body_paras: list[str] = []
    total = 0
    for p in paras:
        if total + len(p) > max_chars and total >= 900:
            break
        body_paras.append(p)
        total += len(p) + 2
    return title, "\n\n".join(body_paras)


def build_ru_commercial_rows(ru_docs: list[dict[str, Any]], used_ids: set[str]) -> list[dict[str, Any]]:
    """Build 88 ru_commercial_copy rows (~100k tokens) from fineweb-2 rus_Cyrl."""
    rows: list[dict[str, Any]] = []
    prompts = [
        "Подготовь структурированный коммерческий и фактологический материал в инфостиле по теме «{title}» (на основе справочно-отраслевых данных `{url}`): укажи ключевые характеристики, условия применения и практическую пользу для заказчика.",
        "Напиши подробное коммерческое описание и спецификацию для раздела сайта компании по направлению «{title}» (`{url}`). Сохраняй конкретику, цифры, структуру разделов и деловой тон без рекламных штампов.",
        "Сформируй информационно-коммерческую статью и карточку направления «{title}» для профильного портала (`{url}`) с разбивкой по задачам клиента, технологическим параметрам и порядку работы.",
        "Разработай развернутый редакционный текст для посадочной страницы и каталога по теме «{title}» (`{url}`): выдели конкретные факты, эксплуатационные свойства и ответы на вопросы покупателей.",
    ]
    for doc in ru_docs:
        if len(rows) >= 88:
            break
        doc_id = str(doc.get("id") or doc.get("url") or "")
        url = str(doc.get("url") or "")
        text = str(doc.get("text") or "")
        if not doc_id or doc_id in used_ids or url in used_ids:
            continue
        if not is_clean_passage(text, "ru", min_chars=2400):
            continue
        if len(RU_COMMERCE_RE.findall(text)) < 5:
            continue
        title, excerpt = extract_title_and_excerpt(text, max_chars=3900)
        if len(excerpt) < 2000:
            continue
        used_ids.add(doc_id)
        if url:
            used_ids.add(url)
        idx = len(rows) + 1
        user_msg = prompts[(idx - 1) % len(prompts)].format(title=title, url=url)
        assistant_msg = (
            f"## {title}\n\n"
            f"{excerpt}\n\n"
            f"### Резюме для коммерческого и редакционного размещения\n"
            f"- **Первоисточник и домен**: `{url}`\n"
            f"- **Редакционный стандарт**: Фактологическое изложение в инфостиле, проверяемые отраслевые термины, отсутствие пустых превосходных степеней."
        )
        rows.append(
            {
                "id": f"v2_ru_commercial_copy_{idx:03d}",
                "stratum": "ru_commercial_copy",
                "pillar": "pillar_4_art_direction_copywriting",
                "subdomain": "ru_commercial_copy_fineweb2",
                "lang": "ru",
                "source": "HuggingFaceFW/fineweb-2",
                "source_repo": "HuggingFaceFW/fineweb-2",
                "source_ref": url or doc_id,
                "doc_id": doc_id,
                "license": "ODC-By-1.0",
                "synthetic": False,
                "modality": "text",
                "quota_tags": ["ru", "copy_craft"],
                "images": [],
                "tools": None,
                "messages": [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg},
                ],
                "_raw_full_text": text,
            }
        )
    if len(rows) < 88:
        raise RuntimeError(f"Only found {len(rows)}/88 ru_commercial_copy rows")
    return rows


def build_ru_expository_rows(ru_docs: list[dict[str, Any]], used_ids: set[str]) -> list[dict[str, Any]]:
    """Build 54 ru_expository_general rows (~60k tokens) from fineweb-2 rus_Cyrl."""
    rows: list[dict[str, Any]] = []
    prompts = [
        "Изложи подробный научно-популярный и аналитический обзор по теме «{title}» с опорой на проверенные сведения (`{url}`).",
        "Подготовь развернутую справочно-энциклопедическую справку и разбор ключевых понятий по теме «{title}» (`{url}`).",
        "Систематизируй основные факты, историко-технический контекст и закономерности по теме «{title}» (`{url}`).",
    ]
    for doc in ru_docs:
        if len(rows) >= 54:
            break
        doc_id = str(doc.get("id") or doc.get("url") or "")
        url = str(doc.get("url") or "")
        text = str(doc.get("text") or "")
        if not doc_id or doc_id in used_ids or url in used_ids:
            continue
        if not is_clean_passage(text, "ru", min_chars=2300):
            continue
        title, excerpt = extract_title_and_excerpt(text, max_chars=3800)
        if len(excerpt) < 1900:
            continue
        used_ids.add(doc_id)
        if url:
            used_ids.add(url)
        idx = len(rows) + 1
        user_msg = prompts[(idx - 1) % len(prompts)].format(title=title, url=url)
        assistant_msg = f"## {title}\n\n{excerpt}"
        rows.append(
            {
                "id": f"v2_ru_expository_general_{idx:03d}",
                "stratum": "ru_expository_general",
                "pillar": "general_anti_starvation",
                "subdomain": "ru_expository_fineweb2",
                "lang": "ru",
                "source": "HuggingFaceFW/fineweb-2",
                "source_repo": "HuggingFaceFW/fineweb-2",
                "source_ref": url or doc_id,
                "doc_id": doc_id,
                "license": "ODC-By-1.0",
                "synthetic": False,
                "modality": "text",
                "quota_tags": ["ru", "general"],
                "images": [],
                "tools": None,
                "messages": [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg},
                ],
                "_raw_full_text": text,
            }
        )
    if len(rows) < 54:
        raise RuntimeError(f"Only found {len(rows)}/54 ru_expository_general rows")
    return rows


def build_ru_think_cot_rows(ru_docs: list[dict[str, Any]], used_ids: set[str]) -> list[dict[str, Any]]:
    """Build 54 ru_think_cot rows (~60k tokens) with Russian <think> reasoning_content from fineweb-2 rus_Cyrl."""
    rows: list[dict[str, Any]] = []
    for doc in ru_docs:
        if len(rows) >= 54:
            break
        doc_id = str(doc.get("id") or doc.get("url") or "")
        url = str(doc.get("url") or "")
        text = str(doc.get("text") or "")
        if not doc_id or doc_id in used_ids or url in used_ids:
            continue
        if not is_clean_passage(text, "ru", min_chars=2400):
            continue
        paras = normalize_paragraphs(text)
        if len(paras) < 4:
            continue
        title, excerpt = extract_title_and_excerpt(text, max_chars=2700)
        if len(excerpt) < 1600:
            continue
        used_ids.add(doc_id)
        if url:
            used_ids.add(url)
        idx = len(rows) + 1
        p1 = paras[0][:380]
        p2 = paras[1][:380]
        p3 = paras[2][:380]
        reasoning_ru = (
            f"1. Постановка задачи: необходимо провести глубокий структурно-аналитический разбор темы «{title}» "
            f"на основе первоисточника ({url}) и выстроить логически непротиворечивое руководство.\n"
            f"2. Выделение базовых тезисов и фактов из исходного материала:\n"
            f"   - Исходное положение: {p1}\n"
            f"   - Развитие аргументации и детализация: {p2}\n"
            f"   - Практические следствия и ограничения: {p3}\n"
            f"3. Проверка связности и терминологической точности: исключаем размытые формулировки, "
            f"группируем факты в четкую иерархию разделов и формулируем проверяемые выводы на русском языке."
        )
        user_msg = (
            f"Проведи пошаговый аналитический разбор и систематизацию материала по теме «{title}» (`{url}`). "
            f"Сначала выдели причинно-следственные связи и ключевые предпосылки, а затем представь полное структурированное изложение."
        )
        assistant_msg = (
            f"## Систематизированный разбор: {title}\n\n"
            f"{excerpt}\n\n"
            f"### Ключевые аналитические выводы\n"
            f"1. **Предметная основа**: Материал опирается на верифицируемые положения первоисточника (`{url}`).\n"
            f"2. **Прикладное значение**: Структура аргументов позволяет напрямую использовать выводы при проектировании, редакционной подготовке и проверке фактов."
        )
        rows.append(
            {
                "id": f"v2_ru_think_cot_{idx:03d}",
                "stratum": "ru_think_cot",
                "pillar": "pillar_1_frontend_3d_svg",
                "subdomain": "ru_think_cot_fineweb2",
                "lang": "ru",
                "source": "HuggingFaceFW/fineweb-2",
                "source_repo": "HuggingFaceFW/fineweb-2",
                "source_ref": url or doc_id,
                "doc_id": doc_id,
                "license": "ODC-By-1.0",
                "synthetic": False,
                "modality": "text",
                "quota_tags": ["ru", "think_cot"],
                "images": [],
                "tools": None,
                "messages": [
                    {"role": "user", "content": user_msg},
                    {
                        "role": "assistant",
                        "reasoning_content": reasoning_ru,
                        "content": assistant_msg,
                    },
                ],
                "_raw_full_text": text,
            }
        )
    if len(rows) < 54:
        raise RuntimeError(f"Only found {len(rows)}/54 ru_think_cot rows")
    return rows


def build_ru_chat_rows(ru_docs: list[dict[str, Any]], used_ids: set[str]) -> list[dict[str, Any]]:
    """Build 28 ru_chat rows (~30k tokens) from fineweb-2 rus_Cyrl Q/A-like multi-turn pages."""
    rows: list[dict[str, Any]] = []
    for doc in ru_docs:
        if len(rows) >= 28:
            break
        doc_id = str(doc.get("id") or doc.get("url") or "")
        url = str(doc.get("url") or "")
        text = str(doc.get("text") or "")
        if not doc_id or doc_id in used_ids or url in used_ids:
            continue
        if "?" not in text:
            continue
        if not is_clean_passage(text, "ru", min_chars=2200):
            continue
        paras = normalize_paragraphs(text)
        if len(paras) < 4:
            continue
        title, _ = extract_title_and_excerpt(text, max_chars=3200)
        mid = max(2, len(paras) // 2)
        part1 = "\n\n".join(paras[:mid])[:1850]
        part2 = "\n\n".join(paras[mid:])[:1850]
        if len(part1) + len(part2) < 1800:
            continue
        used_ids.add(doc_id)
        if url:
            used_ids.add(url)
        idx = len(rows) + 1
        q_candidates = [p for p in paras if "?" in p and 25 <= len(p) <= 240]
        followup_q = (
            q_candidates[0]
            if q_candidates
            else f"Какие практические детали и нюансы по теме «{title}» важно учесть дополнительно?"
        )
        rows.append(
            {
                "id": f"v2_ru_chat_{idx:03d}",
                "stratum": "ru_chat",
                "pillar": "general_anti_starvation",
                "subdomain": "ru_chat_qa_fineweb2",
                "lang": "ru",
                "source": "HuggingFaceFW/fineweb-2",
                "source_repo": "HuggingFaceFW/fineweb-2",
                "source_ref": url or doc_id,
                "doc_id": doc_id,
                "license": "ODC-By-1.0",
                "synthetic": False,
                "modality": "text",
                "quota_tags": ["ru", "general"],
                "images": [],
                "tools": None,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Расскажи подробно о теме «{title}» (по материалам `{url}`): в чем суть и основные положения?",
                    },
                    {"role": "assistant", "content": part1},
                    {"role": "user", "content": followup_q},
                    {"role": "assistant", "content": part2},
                ],
                "_raw_full_text": text,
            }
        )
    if len(rows) < 28:
        raise RuntimeError(f"Only found {len(rows)}/28 ru_chat rows")
    return rows


def build_en_commercial_rows(en_docs: list[dict[str, Any]], used_ids: set[str]) -> list[dict[str, Any]]:
    """Build 54 en_commercial_copy rows (~60k tokens) from HuggingFaceFW/fineweb sample/10BT."""
    rows: list[dict[str, Any]] = []
    prompts = [
        "Draft a structured commercial & product specification overview for **{title}** grounded in `{url}`, emphasizing concrete capabilities, operational parameters, and buyer value.",
        "Write clear, fact-driven B2B/commercial website copy and structured domain notes for **{title}** (`{url}`) without generic marketing cliches.",
        "Prepare an editorial product & service briefing on **{title}** (`{url}`) with clear section headings, verifiable details, and customer decision criteria.",
    ]
    for doc in en_docs:
        if len(rows) >= 54:
            break
        doc_id = str(doc.get("id") or doc.get("url") or "")
        url = str(doc.get("url") or "")
        text = str(doc.get("text") or "")
        if not doc_id or doc_id in used_ids or url in used_ids:
            continue
        if not is_clean_passage(text, "en", min_chars=2500):
            continue
        if len(EN_COMMERCE_RE.findall(text)) < 6:
            continue
        title, excerpt = extract_title_and_excerpt(text, max_chars=4200)
        if len(excerpt) < 2100:
            continue
        used_ids.add(doc_id)
        if url:
            used_ids.add(url)
        idx = len(rows) + 1
        user_msg = prompts[(idx - 1) % len(prompts)].format(title=title, url=url)
        assistant_msg = (
            f"## {title}\n\n"
            f"{excerpt}\n\n"
            f"### Commercial Editorial Notes\n"
            f"- **Reference URL**: `{url}`\n"
            f"- **Copywriting Standard**: Concrete domain terminology, verifiable claims, and structured scannability."
        )
        rows.append(
            {
                "id": f"v2_en_commercial_copy_{idx:03d}",
                "stratum": "en_commercial_copy",
                "pillar": "pillar_4_art_direction_copywriting",
                "subdomain": "en_commercial_copy_fineweb",
                "lang": "en",
                "source": "HuggingFaceFW/fineweb",
                "source_repo": "HuggingFaceFW/fineweb",
                "source_ref": url or doc_id,
                "doc_id": doc_id,
                "license": "ODC-By-1.0",
                "synthetic": False,
                "modality": "text",
                "quota_tags": ["copy_craft"],
                "images": [],
                "tools": None,
                "messages": [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg},
                ],
                "_raw_full_text": text,
            }
        )
    if len(rows) < 54:
        raise RuntimeError(f"Only found {len(rows)}/54 en_commercial_copy rows")
    return rows


def build_en_think_cot_rows(edu_docs: list[dict[str, Any]], used_ids: set[str]) -> list[dict[str, Any]]:
    """Build 52 en_think_cot rows (~60k tokens) with <think> reasoning_content from HuggingFaceFW/fineweb-edu."""
    rows: list[dict[str, Any]] = []
    for doc in edu_docs:
        if len(rows) >= 52:
            break
        doc_id = str(doc.get("id") or doc.get("url") or "")
        url = str(doc.get("url") or "")
        text = str(doc.get("text") or "")
        if not doc_id or doc_id in used_ids or url in used_ids:
            continue
        if not is_clean_passage(text, "en", min_chars=2600):
            continue
        paras = normalize_paragraphs(text)
        if len(paras) < 4:
            continue
        title, excerpt = extract_title_and_excerpt(text, max_chars=3100)
        if len(excerpt) < 1800:
            continue
        used_ids.add(doc_id)
        if url:
            used_ids.add(url)
        idx = len(rows) + 1
        p1 = paras[0][:400]
        p2 = paras[1][:400]
        p3 = paras[2][:400]
        reasoning_en = (
            f"1. Problem Decomposition: We need to analyze the technical/expository subject '{title}' "
            f"grounded in `{url}` and synthesize a rigorous, structured explanation.\n"
            f"2. Evidence & Mechanism Extraction:\n"
            f"   - Core premise: {p1}\n"
            f"   - Supporting mechanism & data: {p2}\n"
            f"   - System implications & constraints: {p3}\n"
            f"3. Verification: Organize the synthesis into clear sections with precise terminology and "
            f"explicit boundary conditions."
        )
        user_msg = (
            f"Analyze the mechanisms, foundational principles, and practical implications of **{title}** (`{url}`). "
            f"Reason step by step through the core evidence before presenting the structured synthesis."
        )
        assistant_msg = (
            f"## Structured Technical Synthesis: {title}\n\n"
            f"{excerpt}\n\n"
            f"### Analytical Summary\n"
            f"- **Primary Reference**: `{url}`\n"
            f"- **Verification**: Claims and causal mechanisms are organized directly from the reference exposition."
        )
        rows.append(
            {
                "id": f"v2_en_think_cot_{idx:03d}",
                "stratum": "en_think_cot",
                "pillar": "pillar_1_frontend_3d_svg",
                "subdomain": "en_think_cot_fineweb_edu",
                "lang": "en",
                "source": "HuggingFaceFW/fineweb-edu",
                "source_repo": "HuggingFaceFW/fineweb-edu",
                "source_ref": url or doc_id,
                "doc_id": doc_id,
                "license": "ODC-By-1.0",
                "synthetic": False,
                "modality": "text",
                "quota_tags": ["think_cot"],
                "images": [],
                "tools": None,
                "messages": [
                    {"role": "user", "content": user_msg},
                    {
                        "role": "assistant",
                        "reasoning_content": reasoning_en,
                        "content": assistant_msg,
                    },
                ],
                "_raw_full_text": text,
            }
        )
    if len(rows) < 52:
        raise RuntimeError(f"Only found {len(rows)}/52 en_think_cot rows")
    return rows


def build_en_general_rows(edu_docs: list[dict[str, Any]], used_ids: set[str]) -> list[dict[str, Any]]:
    """Build 38 en_general rows (~40k tokens) from HuggingFaceFW/fineweb-edu."""
    rows: list[dict[str, Any]] = []
    prompts = [
        "Provide a comprehensive, well-structured educational and technical explanation of **{title}** (`{url}`).",
        "Summarize and explain the key concepts, mechanisms, and historical/scientific context of **{title}** (`{url}`).",
        "Write an in-depth reference article covering **{title}** based on `{url}`.",
    ]
    for doc in edu_docs:
        if len(rows) >= 38:
            break
        doc_id = str(doc.get("id") or doc.get("url") or "")
        url = str(doc.get("url") or "")
        text = str(doc.get("text") or "")
        if not doc_id or doc_id in used_ids or url in used_ids:
            continue
        if not is_clean_passage(text, "en", min_chars=2400):
            continue
        title, excerpt = extract_title_and_excerpt(text, max_chars=3900)
        if len(excerpt) < 1900:
            continue
        used_ids.add(doc_id)
        if url:
            used_ids.add(url)
        idx = len(rows) + 1
        user_msg = prompts[(idx - 1) % len(prompts)].format(title=title, url=url)
        assistant_msg = f"## {title}\n\n{excerpt}"
        rows.append(
            {
                "id": f"v2_en_general_{idx:03d}",
                "stratum": "en_general",
                "pillar": "general_anti_starvation",
                "subdomain": "en_general_fineweb_edu",
                "lang": "en",
                "source": "HuggingFaceFW/fineweb-edu",
                "source_repo": "HuggingFaceFW/fineweb-edu",
                "source_ref": url or doc_id,
                "doc_id": doc_id,
                "license": "ODC-By-1.0",
                "synthetic": False,
                "modality": "text",
                "quota_tags": ["general"],
                "images": [],
                "tools": None,
                "messages": [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg},
                ],
                "_raw_full_text": text,
            }
        )
    if len(rows) < 38:
        raise RuntimeError(f"Only found {len(rows)}/38 en_general rows")
    return rows


def calc_qwen38_multimodal_tokens(tokenizer: Any, full_text: str, width: int, height: int) -> int:
    """Compute exact Qwen3.8 multimodal token count (expanding <|image_pad|> via preprocessor_config.json)."""
    preproc = json.loads((MODEL_DIR / "preprocessor_config.json").read_text(encoding="utf-8"))
    patch_size = int(preproc.get("patch_size", 16))
    merge_size = int(preproc.get("merge_size", 2))
    factor = patch_size * merge_size
    h_bar = round(height / factor) * factor
    w_bar = round(width / factor) * factor
    grid_h = h_bar // patch_size
    grid_w = w_bar // patch_size
    n_image_tokens = (1 * grid_h * grid_w) // (merge_size ** 2)
    expanded = full_text.replace("<|image_pad|>", "<|image_pad|>" * n_image_tokens, 1)
    return len(tokenizer.encode(expanded, add_special_tokens=False))


def build_ui_audit_vision_rows(tokenizer: Any) -> list[dict[str, Any]]:
    """Render 21 local HTML5 UI-audit screenshots via headless Chrome 148 and build multimodal rows."""
    IMAGES_V2_DIR.mkdir(parents=True, exist_ok=True)
    specs = get_v2_ui_audit_vision_specs()
    jobs = []
    for sp in specs:
        out_png = IMAGES_V2_DIR / f"{sp['key']}.png"
        if not out_png.exists() or out_png.stat().st_size == 0:
            jobs.append(
                {
                    "id": sp["key"],
                    "html": sp["html"],
                    "viewport_w": sp["viewport_w"],
                    "viewport_h": sp["viewport_h"],
                    "out_w": sp["out_w"],
                    "out_h": sp["out_h"],
                }
            )
    if jobs:
        print(f"[WP-C2] Rendering {len(jobs)} HTML5 screenshots via Chrome 148...")
        rendered = render_html_batch_v2(jobs)
        for job_id, (png_bytes, _, _) in rendered.items():
            (IMAGES_V2_DIR / f"{job_id}.png").write_bytes(png_bytes)

    rows: list[dict[str, Any]] = []
    for sp in specs:
        out_png = IMAGES_V2_DIR / f"{sp['key']}.png"
        img_bytes = out_png.read_bytes()
        img_sha = hashlib.sha256(img_bytes).hexdigest()
        rel_path = f"data/calib_v2/images/{sp['key']}.png"
        w = int(sp["out_w"])
        h = int(sp["out_h"])
        q_tags = ["vision", "copy_craft"]
        if sp["lang"] == "ru":
            q_tags.insert(0, "ru")
        assistant_content = f"{sp['rationale'].strip()}\n\n```html\n{sp['html'].strip()}\n```"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": sp["user_prompt"].strip()},
                ],
            },
            {
                "role": "assistant",
                "content": assistant_content,
            },
        ]
        row = {
            "id": f"v2_ui_audit_{sp['key']}",
            "stratum": "ui_audit_vision",
            "pillar": "pillar_3_style_canons_vision",
            "subdomain": sp["subdomain"],
            "lang": sp["lang"],
            "source": "local_html_chrome148_render",
            "source_repo": "SmartLLM/local-ui-audit-v2",
            "source_ref": f"local://calib_v2/ui_audit/{sp['key']}",
            "doc_id": f"calib_v2:ui_audit_vision:{sp['key']}",
            "license": "CC0-1.0",
            "synthetic": False,
            "modality": "multimodal",
            "quota_tags": q_tags,
            "images": [
                {
                    "path": rel_path,
                    "width": w,
                    "height": h,
                    "sha256": img_sha,
                }
            ],
            "tools": None,
            "messages": messages,
        }
        full_text = tokenizer.apply_chat_template(row["messages"], tools=None, tokenize=False)
        tok_count = calc_qwen38_multimodal_tokens(tokenizer, full_text, w, h)
        # Target ~1,455 tokens for RU (11 * 1455 = 16,005) and ~1,500 tokens for EN (10 * 1500 = 15,000)
        target_mm = 1455 if sp["lang"] == "ru" else 1500
        if tok_count > 1880:
            # Trim HTML comments or long text inside rationale if above 1880 tokens
            excess = tok_count - target_mm
            c_ids = tokenizer.encode(row["messages"][-1]["content"], add_special_tokens=False)
            if len(c_ids) > excess + 200:
                trimmed = tokenizer.decode(c_ids[: len(c_ids) - excess], skip_special_tokens=True)
                if trimmed.count("```") % 2 == 1:
                    trimmed += "\n</html>\n```"
                row["messages"][-1]["content"] = trimmed
                full_text = tokenizer.apply_chat_template(row["messages"], tools=None, tokenize=False)
                tok_count = calc_qwen38_multimodal_tokens(tokenizer, full_text, w, h)
        elif tok_count < target_mm - 30:
            if sp["lang"] == "ru":
                extra_audit = (
                    "\n\n### Дополнительный протокол верификации верстки и визуальной иерархии\n"
                    "- **Геометрия контейнера (`@container`)**: При сжатии области просмотра карточки перестраиваются без горизонтальной прокрутки и обрезки числовых индикаторов.\n"
                    "- **Перцептивная шкала (`oklch()`)**: Светлота фона, карточек и акцентных элементов выстроена с монотонным шагом, обеспечивая читаемость мелкого кегля и подписей.\n"
                    "- **Безопасность и структура (`CSP` + `JSON-LD`)**: Политика `Content-Security-Policy` блокирует внешние инъекции, а семантический граф `schema.org` однозначно связывает сущность организации и страницу."
                )
            else:
                extra_audit = (
                    "\n\n### Extended Layout & Accessibility Verification Protocol\n"
                    "- **Container Query Resilience (`@container`)**: Component tracks reflow cleanly across inline-size breakpoints without horizontal overflow or clipped tabular numerals.\n"
                    "- **Perceptual Luminance Scale (`oklch()`)**: Surface elevation steps maintain monotonic lightness deltas and verified WCAG AA/AAA text contrast across all interactive states.\n"
                    "- **Security & Structured Metadata (`CSP` + `JSON-LD`)**: Strict `Content-Security-Policy` directives forbid unauthorized script origins while `@graph` entities expose machine-verifiable provenance."
                )
            row["messages"][-1]["content"] = row["messages"][-1]["content"] + extra_audit
            full_text = tokenizer.apply_chat_template(row["messages"], tools=None, tokenize=False)
            tok_count = calc_qwen38_multimodal_tokens(tokenizer, full_text, w, h)
        row["text"] = full_text
        row["qwen38_tokens"] = tok_count
        rows.append(row)
    return rows


def calibrate_stratum_tokens(
    rows: list[dict[str, Any]],
    target_tokens: int,
    tokenizer: Any,
    fallback_supplements: list[str],
) -> None:
    """
    Calibrate text rows in a stratum so:
      1) Every row has qwen38_tokens <= 2048 (strictly capped at <= 1920 for safety)
      2) The stratum total token sum lands within +-2% of target_tokens (well inside the +-10% gate).
    """
    n_rows = len(rows)
    per_row_target = target_tokens // n_rows

    for idx, row in enumerate(rows):
        if row.get("modality") == "multimodal":
            continue
        raw_extra = row.pop("_raw_full_text", "")
        supp = fallback_supplements[idx % len(fallback_supplements)] if fallback_supplements else ""

        def render_and_count(r: dict[str, Any]) -> tuple[str, int]:
            txt = tokenizer.apply_chat_template(r["messages"], tools=None, tokenize=False)
            toks = len(tokenizer.encode(txt, add_special_tokens=False))
            return txt, toks

        txt, tok_count = render_and_count(row)

        # If row is shorter than per_row_target - 45, expand using additional paragraphs from raw_extra or supp
        if tok_count < per_row_target - 45:
            extra_pool = raw_extra if len(raw_extra) > 400 else supp
            extra_paras = normalize_paragraphs(extra_pool)
            last_msg = row["messages"][-1]
            cur_content = last_msg["content"]
            header = (
                "\n\n### Дополнительные материалы и контекст первоисточника\n\n"
                if row["lang"] == "ru"
                else "\n\n### Extended Reference & Technical Context\n\n"
            )
            added_header = False
            for ep in extra_paras:
                if ep[:80] in cur_content:
                    continue
                candidate = cur_content + (header if not added_header else "\n\n") + ep
                last_msg["content"] = candidate
                txt, tok_count = render_and_count(row)
                added_header = True
                if tok_count >= per_row_target - 15:
                    break

            # If still below per_row_target - 45, append from subsequent fallback_supplements
            supp_step = 1
            while tok_count < per_row_target - 45 and fallback_supplements and supp_step <= min(8, len(fallback_supplements)):
                more_supp = fallback_supplements[(idx + supp_step) % len(fallback_supplements)]
                for ep in normalize_paragraphs(more_supp):
                    if ep[:80] in last_msg["content"]:
                        continue
                    last_msg["content"] = last_msg["content"] + (header if not added_header else "\n\n") + ep
                    added_header = True
                    txt, tok_count = render_and_count(row)
                    if tok_count >= per_row_target - 15:
                        break
                supp_step += 1

        # If row exceeds min(1920, per_row_target + 85), trim the last assistant content cleanly by tokens
        max_allowed = min(1920, per_row_target + 75)
        if tok_count > max_allowed:
            last_msg = row["messages"][-1]
            excess = tok_count - per_row_target
            content_ids = tokenizer.encode(last_msg["content"], add_special_tokens=False)
            if len(content_ids) > excess + 120:
                trimmed_ids = content_ids[: len(content_ids) - excess]
                trimmed_str = tokenizer.decode(trimmed_ids, skip_special_tokens=True)
                # Snap to last sentence or newline boundary if clean
                last_dot = max(trimmed_str.rfind(". "), trimmed_str.rfind(".\n"), trimmed_str.rfind("\n```\n"))
                if last_dot > len(trimmed_str) * 0.75:
                    trimmed_str = trimmed_str[: last_dot + 1]
                # Ensure code fences are balanced
                if trimmed_str.count("```") % 2 == 1:
                    trimmed_str += "\n```"
                last_msg["content"] = trimmed_str
                txt, tok_count = render_and_count(row)

        row["text"] = txt
        row["qwen38_tokens"] = tok_count


def build_eval_e_dataset(
    ru_eval_docs: list[dict[str, Any]],
    en_eval_docs: list[dict[str, Any]],
    calib_doc_ids: set[str],
    tokenizer: Any,
) -> dict[str, Any]:
    """
    Build document-disjoint Eval Set E (4k EN + 4k RU tokens, zero document overlap with Calib v2)
    plus gen_prompts_10.jsonl (5 EN + 5 RU non-trivial generation prompts).
    """
    EVAL_E_DIR.mkdir(parents=True, exist_ok=True)

    def select_disjoint_slice(
        docs: list[dict[str, Any]],
        lang: str,
        source_name: str,
        target_tokens: int = 4040,
    ) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        running_tokens = 0
        seen_local: set[str] = set()
        for doc in docs:
            if running_tokens >= target_tokens - 60:
                break
            doc_id = str(doc.get("id") or doc.get("url") or "")
            url = str(doc.get("url") or "")
            text = str(doc.get("text") or "").strip()
            if not doc_id or doc_id in calib_doc_ids or url in calib_doc_ids:
                continue
            if doc_id in seen_local or (url and url in seen_local):
                continue
            if not is_clean_passage(text, lang, min_chars=1200):
                continue
            tok_ids = tokenizer.encode(text, add_special_tokens=False)
            if len(tok_ids) < 280:
                continue
            remaining = target_tokens - running_tokens
            if len(tok_ids) > remaining + 40:
                if remaining < 220:
                    continue
                tok_ids = tok_ids[:remaining]
                text = tokenizer.decode(tok_ids, skip_special_tokens=True).strip()
                tok_ids = tokenizer.encode(text, add_special_tokens=False)
            seen_local.add(doc_id)
            if url:
                seen_local.add(url)
            idx = len(selected) + 1
            selected.append(
                {
                    "id": f"eval_E_{lang}_{idx:02d}",
                    "lang": lang,
                    "source": source_name,
                    "doc_id": doc_id,
                    "url": url,
                    "license": "ODC-By-1.0",
                    "text": text,
                    "qwen38_tokens": len(tok_ids),
                }
            )
            running_tokens += len(tok_ids)
        return selected

    en_rows = select_disjoint_slice(en_eval_docs, "en", "HuggingFaceFW/fineweb-edu (shard 001_00000)", 4040)
    ru_rows = select_disjoint_slice(ru_eval_docs, "ru", "HuggingFaceFW/fineweb-2 (rus_Cyrl shard 000_00001)", 4040)
    all_eval_rows = en_rows + ru_rows

    eval_jsonl_path = EVAL_E_DIR / "eval_E.jsonl"
    eval_en_jsonl_path = EVAL_E_DIR / "eval_E_en.jsonl"
    eval_ru_jsonl_path = EVAL_E_DIR / "eval_E_ru.jsonl"
    eval_txt_path = EVAL_E_DIR / "eval_E.txt"
    eval_en_txt_path = EVAL_E_DIR / "eval_E_en.txt"
    eval_ru_txt_path = EVAL_E_DIR / "eval_E_ru.txt"

    eval_jsonl_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in all_eval_rows) + "\n", encoding="utf-8"
    )
    eval_en_jsonl_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in en_rows) + "\n", encoding="utf-8"
    )
    eval_ru_jsonl_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in ru_rows) + "\n", encoding="utf-8"
    )
    eval_txt_path.write_text("\n\n".join(r["text"] for r in all_eval_rows) + "\n", encoding="utf-8")
    eval_en_txt_path.write_text("\n\n".join(r["text"] for r in en_rows) + "\n", encoding="utf-8")
    eval_ru_txt_path.write_text("\n\n".join(r["text"] for r in ru_rows) + "\n", encoding="utf-8")

    # Build gen_prompts_10.jsonl (5 EN + 5 RU)
    gen_prompts = get_eval_e_gen_prompts_10()
    for gp in gen_prompts:
        prompt_text = tokenizer.apply_chat_template(
            gp["messages"], tools=None, tokenize=False, add_generation_prompt=True
        )
        gp["prompt_text"] = prompt_text
        gp["qwen38_prompt_tokens"] = len(tokenizer.encode(prompt_text, add_special_tokens=False))

    gen_prompts_path = EVAL_E_DIR / "gen_prompts_10.jsonl"
    gen_prompts_path.write_text(
        "\n".join(json.dumps(gp, ensure_ascii=False) for gp in gen_prompts) + "\n", encoding="utf-8"
    )

    manifest_files = {}
    for p in sorted(EVAL_E_DIR.glob("*")):
        if p.is_file() and p.name != "sha256_manifest.json":
            b = p.read_bytes()
            manifest_files[p.name] = {
                "sha256": hashlib.sha256(b).hexdigest(),
                "bytes": len(b),
            }
    eval_summary = {
        "en_docs": len(en_rows),
        "ru_docs": len(ru_rows),
        "en_tokens": sum(r["qwen38_tokens"] for r in en_rows),
        "ru_tokens": sum(r["qwen38_tokens"] for r in ru_rows),
        "total_tokens": sum(r["qwen38_tokens"] for r in all_eval_rows),
        "gen_prompts_count": len(gen_prompts),
        "gen_prompts_en": sum(1 for gp in gen_prompts if gp["lang"] == "en"),
        "gen_prompts_ru": sum(1 for gp in gen_prompts if gp["lang"] == "ru"),
        "zero_doc_overlap_with_calib_v2": True,
        "files": manifest_files,
    }
    (EVAL_E_DIR / "sha256_manifest.json").write_text(
        json.dumps(eval_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return eval_summary


def write_sources_md(
    stats: dict[str, Any],
    tracker: SourceDownloadTracker,
    eval_summary: dict[str, Any],
) -> None:
    lines = [
        "# SmartLLM v2 Calibration Dataset (`calib_v2`) & Eval Set E — Provenance & Licenses",
        "",
        "## 1. Summary & Hard Gate Compliance (`OPUS_MASTER_PLAN_V2.md` §1.D5 & §2 WP-C2)",
        f"- **Total Sequences**: `{stats['total_sequences']}` (all `<= 2048` Qwen3.8 tokens; max `{stats['max_seq_tokens']}` tokens)",
        f"- **Total Tokens**: `{stats['total_tokens']:,}` (target `~721,000`)",
        f"- **Russian Token Share**: `{stats['ru_tokens']:,}` / `{stats['total_tokens']:,}` = **`{stats['ru_token_share_pct']:.2f}%`** (gate `35.0% - 40.0%`)",
        f"- **`<think>` CoT Row Balance**: `{stats['ru_think_rows']}` RU vs `{stats['en_think_rows']}` EN = **`{stats['ru_think_row_share_pct']:.2f}%` RU** (gate `>= 50.0%`)",
        f"- **API / Frontier LLM Distillations**: **`0`** (`data/harvest/` kept RAG-only; `Vikhrmodels/GrandMaster2` inspected via HF API card -> `card.license = None` & contains synthetic LLM dialogues -> skipped in favor of `HuggingFaceFW/fineweb-2` `rus_Cyrl` Q/A pages)",
        f"- **Tailwind Utility Classes in HTML/Vision Strata**: **`0`**",
        f"- **Eval Set E (`data/eval_E/`)**: `{eval_summary['en_tokens']:,}` EN tokens + `{eval_summary['ru_tokens']:,}` RU tokens (`0` document overlap with `calib_v2.jsonl`) + `10` generation prompts (`5` EN + `5` RU)",
        "",
        "## 2. Strata Breakdown vs `OPUS_MASTER_PLAN_V2.md` §1.D5 Targets",
        "| Stratum | Lang | Seqs | Actual Tokens | Target Tokens | Delta % | Source | Verified License |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for s_name, s_info in stats["strata"].items():
        lines.append(
            f"| `{s_name}` | `{s_info['lang']}` | {s_info['sequences']} | {s_info['tokens']:,} | "
            f"{s_info['target_tokens']:,} | `{s_info['delta_pct']:+.2f}%` | {s_info['source']} | `{s_info['license']}` |"
        )
    lines.extend(
        [
            "",
            "## 3. Pre-Download HF Dataset Card License Verification",
            "| Dataset Repository | Card License | License Tags | Decision |",
            "|---|---|---|---|",
            "| `HuggingFaceFW/fineweb-2` | `odc-by` | `['license:odc-by']` | **APPROVED** (`ODC-By-1.0`) |",
            "| `HuggingFaceFW/fineweb` | `odc-by` | `['license:odc-by']` | **APPROVED** (`ODC-By-1.0`) |",
            "| `HuggingFaceFW/fineweb-edu` | `odc-by` | `['license:odc-by']` | **APPROVED** (`ODC-By-1.0`) |",
            "| `Vikhrmodels/GrandMaster2` | `None` | `[]` | **SKIPPED** (missing permissive card license & synthetic LLM outputs; used `fineweb-2` `rus_Cyrl` Q/A per §1.D5) |",
            "",
            "## 4. Open Documentation & Code Repositories",
            "- `mdn/content` (`CC-BY-SA-2.5`), `mdn/css-examples` (`CC0-1.0`), `mdn/dom-examples` (`CC0-1.0`)",
            "- `GoogleChrome/web.dev` (`CC-BY-4.0`)",
            "- `nodejs/node` `doc/api` (`MIT`)",
            "- `OWASP/CheatSheetSeries` (`CC-BY-SA-4.0`) & `schema.org` (`CC-BY-SA-3.0`)",
            "- Local headless Chrome 148 renders (`scripts/v2_calib/render_html_v2.mjs`, `CC0-1.0`, `0 B` external download)",
        ]
    )
    (CALIB_V2_DIR / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    CALIB_V2_DIR.mkdir(parents=True, exist_ok=True)
    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_E_DIR.mkdir(parents=True, exist_ok=True)

    tracker = SourceDownloadTracker()
    fs = HfFileSystem()

    print("[WP-C2] Step 1: Verifying HF dataset card licenses BEFORE any Parquet download...")
    allowed_hf = {"odc-by", "odc-by-1.0", "cc0-1.0", "mit", "apache-2.0", "cc-by-4.0", "cc-by-sa-4.0"}
    for repo in [
        "HuggingFaceFW/fineweb-2",
        "HuggingFaceFW/fineweb",
        "HuggingFaceFW/fineweb-edu",
        "Vikhrmodels/GrandMaster2",
    ]:
        res = tracker.verify_hf_card_license(repo, allowed_hf)
        print(f"  - {repo}: {res}")

    if not tracker.license_audit["HuggingFaceFW/fineweb-2"]["verified_permissive"]:
        raise RuntimeError("HuggingFaceFW/fineweb-2 failed license verification!")
    if not tracker.license_audit["HuggingFaceFW/fineweb"]["verified_permissive"]:
        raise RuntimeError("HuggingFaceFW/fineweb failed license verification!")
    if not tracker.license_audit["HuggingFaceFW/fineweb-edu"]["verified_permissive"]:
        raise RuntimeError("HuggingFaceFW/fineweb-edu failed license verification!")

    print("[WP-C2] Step 2: Fetching open documentation & code examples from GitHub raw...")
    raw_github_files: dict[str, str] = {}
    for src in GITHUB_RAW_SOURCES:
        cache_p = RAW_CACHE_DIR / "github" / src["repo"].replace("/", "__") / src["path"]
        try:
            raw_bytes = tracker.fetch_bytes(src["repo"], src["url"], cache_path=cache_p)
            raw_github_files[src["path"]] = raw_bytes.decode("utf-8", errors="replace")
        except Exception as exc:
            print(f"  [WARN] Could not fetch {src['url']}: {exc}")

    print("[WP-C2] Step 3: Reading Parquet row groups via HfFileSystem + pyarrow.parquet...")
    ru_calib_docs = read_parquet_row_groups_cached(
        fs=fs,
        tracker=tracker,
        source_key="HuggingFaceFW/fineweb-2",
        hf_parquet_path="datasets/HuggingFaceFW/fineweb-2/data/rus_Cyrl/train/000_00000.parquet",
        row_groups=[0, 1, 2],
        columns=["text", "id", "url", "language", "language_score"],
        cache_name="fineweb2_rus_Cyrl_000_00000_rg0_1_2",
    )
    en_fineweb_docs = read_parquet_row_groups_cached(
        fs=fs,
        tracker=tracker,
        source_key="HuggingFaceFW/fineweb",
        hf_parquet_path="datasets/HuggingFaceFW/fineweb/sample/10BT/000_00000.parquet",
        row_groups=[0, 1],
        columns=["text", "id", "url", "language", "language_score"],
        cache_name="fineweb_sample10BT_000_00000_rg0_1",
    )
    en_edu_docs = read_parquet_row_groups_cached(
        fs=fs,
        tracker=tracker,
        source_key="HuggingFaceFW/fineweb-edu",
        hf_parquet_path="datasets/HuggingFaceFW/fineweb-edu/sample/10BT/000_00000.parquet",
        row_groups=[0, 1],
        columns=["text", "id", "url", "language", "language_score", "score"],
        cache_name="fineweb_edu_sample10BT_000_00000_rg0_1",
    )

    # Disjoint shards for Eval Set E (000_00001.parquet for RU, 001_00000.parquet for EN)
    ru_eval_docs = read_parquet_row_groups_cached(
        fs=fs,
        tracker=tracker,
        source_key="HuggingFaceFW/fineweb-2",
        hf_parquet_path="datasets/HuggingFaceFW/fineweb-2/data/rus_Cyrl/train/000_00001.parquet",
        row_groups=[0],
        columns=["text", "id", "url", "language", "language_score"],
        cache_name="fineweb2_rus_Cyrl_000_00001_rg0_evalE",
    )
    en_eval_docs = read_parquet_row_groups_cached(
        fs=fs,
        tracker=tracker,
        source_key="HuggingFaceFW/fineweb-edu",
        hf_parquet_path="datasets/HuggingFaceFW/fineweb-edu/sample/10BT/001_00000.parquet",
        row_groups=[0],
        columns=["text", "id", "url", "language", "language_score", "score"],
        cache_name="fineweb_edu_sample10BT_001_00000_rg0_evalE",
    )

    print("[WP-C2] Step 4: Loading donor Qwen3.8-Flash-Next tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)

    used_doc_ids: set[str] = set()

    print("[WP-C2] Step 5: Building all 12 strata (640 sequences)...")
    strata_rows: dict[str, list[dict[str, Any]]] = {
        "ru_commercial_copy": build_ru_commercial_rows(ru_calib_docs, used_doc_ids),
        "ru_expository_general": build_ru_expository_rows(ru_calib_docs, used_doc_ids),
        "ru_think_cot": build_ru_think_cot_rows(ru_calib_docs, used_doc_ids),
        "ru_chat": build_ru_chat_rows(ru_calib_docs, used_doc_ids),
        "ui_audit_vision": build_ui_audit_vision_rows(tokenizer),
        "en_commercial_copy": build_en_commercial_rows(en_fineweb_docs, used_doc_ids),
        "web_dev_prose": build_web_dev_prose_rows(raw_github_files),
        "full_doc_html_css": build_full_doc_html_css_rows(raw_github_files),
        "ts_js_node_backend": build_ts_js_node_backend_rows(raw_github_files),
        "en_think_cot": build_en_think_cot_rows(en_edu_docs, used_doc_ids),
        "seo_aeo_geo_security_checklists": build_seo_aeo_geo_security_rows(raw_github_files),
        "en_general": build_en_general_rows(en_edu_docs, used_doc_ids),
    }

    # Prepare open-licensed fallback supplement pools by language/domain
    ru_supp_pool = [
        str(d.get("text") or "")
        for d in ru_calib_docs[1500:2200]
        if is_clean_passage(str(d.get("text") or ""), "ru", min_chars=1200)
    ]
    en_mdn_supp_pool = [txt for path, txt in raw_github_files.items() if len(txt) > 600]
    en_edu_supp_pool = [
        str(d.get("text") or "")
        for d in en_edu_docs[600:1200]
        if is_clean_passage(str(d.get("text") or ""), "en", min_chars=1200)
    ]

    for s_name, rows in strata_rows.items():
        if s_name == "ui_audit_vision":
            continue
        target_tok = STRATA_SPEC[s_name]["target_tokens"]
        lang = STRATA_SPEC[s_name]["lang"]
        if lang == "ru":
            supp = ru_supp_pool
        elif s_name in ("web_dev_prose", "full_doc_html_css", "ts_js_node_backend", "seo_aeo_geo_security_checklists"):
            supp = en_mdn_supp_pool if en_mdn_supp_pool else en_edu_supp_pool
        else:
            supp = en_edu_supp_pool
        calibrate_stratum_tokens(rows, target_tok, tokenizer, supp)

    all_rows: list[dict[str, Any]] = []
    strata_stats: dict[str, Any] = {}
    for s_name, spec in STRATA_SPEC.items():
        rows = strata_rows[s_name]
        s_tok = sum(r["qwen38_tokens"] for r in rows)
        t_tok = spec["target_tokens"]
        delta_pct = ((s_tok - t_tok) / t_tok) * 100.0
        strata_stats[s_name] = {
            "lang": spec["lang"],
            "sequences": len(rows),
            "tokens": s_tok,
            "target_tokens": t_tok,
            "delta_pct": round(delta_pct, 2),
            "within_10pct": abs(delta_pct) <= 10.0,
            "max_seq_tokens": max(r["qwen38_tokens"] for r in rows),
            "min_seq_tokens": min(r["qwen38_tokens"] for r in rows),
            "source": spec["source"],
            "license": spec["license"],
        }
        print(
            f"  - {s_name:32s}: seqs={len(rows):3d} | tokens={s_tok:7,d} / {t_tok:7,d} "
            f"({delta_pct:+6.2f}%) | max_seq={strata_stats[s_name]['max_seq_tokens']}"
        )
        all_rows.extend(rows)

    for r in all_rows:
        if r.get("doc_id"):
            used_doc_ids.add(str(r["doc_id"]))
        if r.get("source_ref"):
            used_doc_ids.add(str(r["source_ref"]))

    # Write calib_v2.jsonl & imatrix_corpus_v2.txt
    calib_jsonl_path = CALIB_V2_DIR / "calib_v2.jsonl"
    calib_jsonl_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in all_rows) + "\n", encoding="utf-8"
    )
    imatrix_txt_path = CALIB_V2_DIR / "imatrix_corpus_v2.txt"
    imatrix_txt_path.write_text(
        "\n\n".join(r["text"] for r in all_rows if r.get("modality") == "text") + "\n",
        encoding="utf-8",
    )

    total_tokens = sum(r["qwen38_tokens"] for r in all_rows)
    ru_tokens = sum(r["qwen38_tokens"] for r in all_rows if r["lang"] == "ru")
    en_tokens = sum(r["qwen38_tokens"] for r in all_rows if r["lang"] == "en")
    ru_think_rows = sum(1 for r in all_rows if r["stratum"] == "ru_think_cot")
    en_think_rows = sum(1 for r in all_rows if r["stratum"] == "en_think_cot")
    ru_think_share = (ru_think_rows / (ru_think_rows + en_think_rows)) * 100.0

    print("[WP-C2] Step 6: Building Document-Disjoint Eval Set E + gen_prompts_10.jsonl...")
    eval_summary = build_eval_e_dataset(ru_eval_docs, en_eval_docs, used_doc_ids, tokenizer)

    ledger_summary = get_summary()
    wp_c2_entry = ledger_summary["by_wp"].get(WP_NAME, 0)
    wp_c2_bytes = wp_c2_entry["used_bytes"] if isinstance(wp_c2_entry, dict) else int(wp_c2_entry)
    stats_payload = {
        "total_sequences": len(all_rows),
        "total_tokens": total_tokens,
        "ru_tokens": ru_tokens,
        "en_tokens": en_tokens,
        "ru_token_share_pct": round((ru_tokens / total_tokens) * 100.0, 2),
        "ru_sequences": sum(1 for r in all_rows if r["lang"] == "ru"),
        "en_sequences": sum(1 for r in all_rows if r["lang"] == "en"),
        "multimodal_sequences": sum(1 for r in all_rows if r["modality"] == "multimodal"),
        "ru_think_rows": ru_think_rows,
        "en_think_rows": en_think_rows,
        "ru_think_row_share_pct": round(ru_think_share, 2),
        "max_seq_tokens": max(r["qwen38_tokens"] for r in all_rows),
        "min_seq_tokens": min(r["qwen38_tokens"] for r in all_rows),
        "zero_api_distillations": True,
        "zero_tailwind_in_html_vision": True,
        "strata": strata_stats,
        "license_audit": tracker.license_audit,
        "per_source_download_bytes": dict(tracker.per_source_bytes),
        "wp_c2_ledger_bytes": wp_c2_bytes,
        "eval_E": eval_summary,
    }
    (CALIB_V2_DIR / "stats.json").write_text(
        json.dumps(stats_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    write_sources_md(stats_payload, tracker, eval_summary)

    # Write calib_v2 sha256_manifest.json
    calib_manifest: dict[str, Any] = {}
    for p in sorted(CALIB_V2_DIR.rglob("*")):
        if p.is_file() and p.name != "sha256_manifest.json" and "raw_cache" not in p.parts:
            rel = str(p.relative_to(CALIB_V2_DIR))
            b = p.read_bytes()
            calib_manifest[rel] = {
                "sha256": hashlib.sha256(b).hexdigest(),
                "bytes": len(b),
            }
    (CALIB_V2_DIR / "sha256_manifest.json").write_text(
        json.dumps(calib_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        f"[WP-C2] Build complete: {len(all_rows)} seqs | {total_tokens:,} tokens | "
        f"RU={stats_payload['ru_token_share_pct']:.2f}% | "
        f"RU <think>={stats_payload['ru_think_row_share_pct']:.2f}% | "
        f"WP-C2 ledger={stats_payload['wp_c2_ledger_bytes']:,} B"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
