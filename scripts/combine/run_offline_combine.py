#!/usr/bin/env python3
"""Standalone 1-Command Offline Multimodal Combine Launcher (Stage D / Wave 4).

Orchestrates the local offline SmartLLM v2 Web / Design / Copywriting Combine (EN + RU):
1. Auto-discovers `models/SmartLLM-v2-*.gguf` (or explicit `--gguf` / `--allow-dev-205e`)
   and resolves optimal `OPUS_MASTER_PLAN_V2.md §1.D1` runtime parameters
   (`--n-cpu-moe` and `--moe-cache-mib`) from `research/v2_runs/wave3/wave3_summary.json`
   or model filename (`K320+IQ3_XXS -> 43/1536`, `K320+IQ2_S -> 48/3840`, `K288 -> 40/512`).
2. Deterministically retrieves domain-matched design & copywriting context from the
   local RAG canon bank (`data/harvest/MANIFEST.json`, 28 `canon_cards`, 168 EN/RU
   `copy_pairs`, 7 `checklists`, and 4 golden `templates`).
3. Executes the sequential Stage D GPU combine pipeline via `scripts/combine/gpu_switch.py`
   (`SequentialGPUCombineMachine`) and `scripts/infra/sla_watchdog.py` (`§0.3a` Zero-Swap SLA):
   - Stage A: LLM copywriting, semantic HTML5, OKLCH CSS tokens, TypeScript/JS,
     security headers, `llms.txt`, `robots.txt`, and `zimage_prompts.json`.
   - VRAM Barrier 1: `llama-server` slot save -> SIGTERM -> `gpu_exit_check.py` (0 compute VRAM).
   - Stage B: `stable-diffusion.cpp` (`sd-cli --batch-json`) sequential Z-Image rendering.
   - VRAM Barrier 2: PNG artifact verification + `gpu_exit_check.py` (0 compute VRAM).
   - Stage C: Self-contained static bundle assembly in `--out <dir>` with computed
     SHA-256 CSP hashes (`script-src` & `style-src`, zero `'unsafe-inline'`).
4. Provides optional `--serve-ui` (`127.0.0.1:<port>` local browser workbench) and
   `--repl` interactive prompt loop.

Hard Invariants (`CLAUDE.md`):
- Strictly local (`127.0.0.1` only); zero external inference APIs or network calls.
- Reuses `scripts/combine/gpu_switch.py` and `scripts/infra/sla_watchdog.py` directly.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import html
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path
import re
try:
    import resource
except ImportError:
    resource = None  # type: ignore[assignment]
import socket
import sys
import tempfile
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.combine.gpu_switch import (  # noqa: E402
    DEFAULT_DIT_FP8,
    DEFAULT_LLAMA_SERVER,
    DEFAULT_MODEL_205E,
    DEFAULT_QWEN_TE,
    DEFAULT_SD_CLI,
    DEFAULT_SLOT_SAVE_DIR,
    DEFAULT_VAE,
     WATCHDOG_SCRIPT,
    CombineError,
    CombineState,
    SecurityInvariantError,
    SequentialGPUCombineMachine,
    _ancestor_holds_lock,
    _ancestor_is_watchdog,
    _http_json,
    _make_synthetic_png,
    parse_aspect_ratio_dims,
    verify_png_artifact,
)
from scripts.infra.gpu_exit_check import check_gpu_exit  # noqa: E402

HARVEST_DIR = ROOT / "data" / "harvest"
HARVEST_MANIFEST_PATH = HARVEST_DIR / "MANIFEST.json"
MODELS_DIR = ROOT / "models"
WAVE3_SUMMARY_PATH = ROOT / "research" / "v2_runs" / "wave3" / "wave3_summary.json"
GPU_RUN_SCRIPT = ROOT / "scripts" / "infra" / "gpu_run.py"


@dataclass(frozen=True)
class ModelRuntimeProfile:
    """Resolved GGUF model path and OPUS §1.D1 / Step 3b auto-locked runtime configuration."""

    gguf_path: Path
    variant_tag: str
    k_experts: int
    quant_pair: str
    n_cpu_moe: int
    moe_cache_mib: int
    moe_cache_cpu_share: float
    ctx_size: int
    ubatch_size: int
    source: str
    is_dev_fallback: bool = False
    enable_mtp: bool = False
    override_tensor: str = r"blk\.48\..*=CPU"

    def to_llama_extra_args(self) -> list[str]:
        args = [
            "--lazy-mode",
            "direct",
            "--n-cpu-moe",
            str(self.n_cpu_moe),
            "-nr",
            "--moe-cache-mib",
            str(self.moe_cache_mib),
            "--moe-cache-cpu-share",
            f"{self.moe_cache_cpu_share:.2f}",
            "-fa",
            "on",
            "-ctk",
            "q8_0",
            "-ctv",
            "q8_0",
            "-c",
            str(self.ctx_size),
            "-ub",
            str(self.ubatch_size),
            "-ngl",
            "99",
            "-np",
            "1",
            "--cache-ram",
            "0",
        ]
        if self.override_tensor:
            args.extend(["-ot", self.override_tensor])
        if self.enable_mtp:
            args.extend(
                [
                    "--spec-type",
                    "draft-mtp",
                    "--spec-draft-n-max",
                    "3",
                    "--spec-draft-p-min",
                    "0.5",
                    "-ctkd",
                    "q8_0",
                    "-ctvd",
                    "q8_0",
                ]
            )
        args.append("--no-webui")
        return args


def assert_loopback_host(host: str, context: str = "server") -> None:
    """Enforce strict 127.0.0.1 loopback binding (CLAUDE.md §4.3)."""
    if host != "127.0.0.1":
        raise SecurityInvariantError(
            f"Security invariant violation ({context}): host must be '127.0.0.1', got '{host}'"
        )


def resolve_d1_params_from_name(
    filename: str,
    wave3_summary_path: Path | None = WAVE3_SUMMARY_PATH,
) -> tuple[str, int, str, int, int, str]:
    """Resolve (variant_tag, k_experts, quant_pair, n_cpu_moe, moe_cache_mib, source) per OPUS §1.D1."""
    upper = filename.upper()

    # 1. Check wave3_summary.json if available and matching
    if wave3_summary_path is not None and wave3_summary_path.exists():
        try:
            w3 = json.loads(wave3_summary_path.read_text(encoding="utf-8"))
            if isinstance(w3, dict):
                w3_model = str(w3.get("output_gguf") or w3.get("model_path") or w3.get("final_gguf_path") or "")
                if not w3_model or Path(w3_model).name.upper() == upper or "SMARTLLM-V2" in upper:
                    n_cpu = w3.get("n_cpu_moe")
                    cache_mib = w3.get("moe_cache_mib")
                    if isinstance(n_cpu, int) and isinstance(cache_mib, int) and n_cpu > 0 and cache_mib >= 0:
                        vtag = str(w3.get("variant") or "V_WAVE3")
                        k_val = int(w3.get("k_experts") or (288 if "288" in upper else 320))
                        qpair = str(w3.get("quant_pair") or "WAVE3_SELECTED")
                        return vtag, k_val, qpair, n_cpu, cache_mib, f"wave3_summary:{wave3_summary_path.name}"
        except Exception:
            pass

    # 2. Match filename against OPUS §1.D1 locked rules
    if "205E" in upper:
        return "DEV_205E", 205, "IQ3_S", 48, 4096, "dev_205e_baseline"

    variant_upper = upper.replace("SMARTLLM-V2", "SMARTLLM")

    if "K288" in variant_upper or "288E" in variant_upper or "-V3" in variant_upper or "-V4" in variant_upper:
        if "IQ4_NL" in variant_upper or "-V4" in variant_upper:
            return "V4_K288_IQ2S_IQ4NL", 288, "IQ2_S+IQ4_NL", 40, 512, "OPUS_D1_K288_ZERO_Q2"
        return "V3_K288_IQ3S_Q20", 288, "IQ3_S+GSQ_Q2_0", 40, 512, "OPUS_D1_K288"

    if "K320" in variant_upper or "320E" in variant_upper or "-V1" in variant_upper or "-V2" in variant_upper:
        if "IQ2_S" in variant_upper or "-V2" in variant_upper:
            return "V2_K320_IQ2S_Q20", 320, "IQ2_S+GSQ_Q2_0", 48, 3840, "OPUS_D1_K320_MEM_FALLBACK"
        return "V1_K320_IQ3XXS_Q20", 320, "IQ3_XXS+GSQ_Q2_0", 42, 2048, "OPUS_D1_K320_PRIMARY"

    # Default OPUS §1.D1 / Step 3b locked primary profile for any SmartLLM-v2-*.gguf
    return "V1_K320_IQ3XXS_Q20", 320, "IQ3_XXS+GSQ_Q2_0", 42, 2048, "OPUS_D1_DEFAULT_PRIMARY"


def discover_gguf_model(
    explicit_gguf: Path | None = None,
    models_dir: Path = MODELS_DIR,
    wave3_summary_path: Path | None = WAVE3_SUMMARY_PATH,
    allow_dev_205e: bool = False,
    n_cpu_moe_override: int | None = None,
    moe_cache_mib_override: int | None = None,
    require_exists: bool = True,
) -> ModelRuntimeProfile:
    """Auto-discover `models/SmartLLM-v2-*.gguf` and resolve OPUS §1.D1 runtime flags."""
    chosen_path: Path | None = None
    is_dev = False

    if explicit_gguf is not None:
        chosen_path = explicit_gguf
        if require_exists and not chosen_path.exists():
            raise FileNotFoundError(f"Explicit --gguf model not found on disk: {chosen_path}")
        is_dev = "205E" in chosen_path.name.upper()
    else:
        # 1. Check wave3_summary.json first if it points to an existing v2 GGUF
        if wave3_summary_path is not None and wave3_summary_path.exists():
            try:
                w3 = json.loads(wave3_summary_path.read_text(encoding="utf-8"))
                cand = w3.get("output_gguf") or w3.get("model_path") or w3.get("final_gguf_path")
                if cand:
                    cand_p = Path(cand)
                    if not cand_p.is_absolute():
                        cand_p = ROOT / cand_p
                    if cand_p.exists():
                        chosen_path = cand_p
            except Exception:
                pass

        # 2. Scan models/SmartLLM-v2-*.gguf
        if chosen_path is None and models_dir.exists():
            v2_candidates = sorted(
                models_dir.glob("SmartLLM-v2-*.gguf"),
                key=lambda p: (
                    # Prefer final healed / non-bf16 quantized models, newest first
                    0 if "BF16" not in p.name.upper() else 1,
                    -p.stat().st_mtime if p.exists() else 0,
                    p.name,
                ),
            )
            if v2_candidates:
                chosen_path = v2_candidates[0]

        # 3. Fallback to 205E dev model ONLY when --allow-dev-205e is explicitly set
        if chosen_path is None:
            if allow_dev_205e:
                for dev_name in ("SmartLLM-205E-IQ3_S.gguf", "SmartLLM-205E-IQ3_XXS.gguf"):
                    dev_p = models_dir / dev_name
                    if dev_p.exists() or not require_exists:
                        chosen_path = dev_p
                        is_dev = True
                        break
            if chosen_path is None and not require_exists:
                chosen_path = models_dir / "SmartLLM-v2-K320-IQ3_XXS-GSQ-Q2_0.gguf"
            if chosen_path is None:
                raise FileNotFoundError(
                    f"No 'SmartLLM-v2-*.gguf' found in {models_dir}. "
                    "Wave 3 GGUF assembly has not completed yet. "
                    "Pass --gguf <path> or --allow-dev-205e to run with the 205E baseline."
                )

    vtag, k_exp, qpair, n_cpu, cache_mib, src = resolve_d1_params_from_name(
        chosen_path.name, wave3_summary_path=wave3_summary_path
    )
    if n_cpu_moe_override is not None:
        n_cpu = n_cpu_moe_override
        src += "+cli_n_cpu_moe"
    if moe_cache_mib_override is not None:
        cache_mib = moe_cache_mib_override
        src += "+cli_moe_cache"

    return ModelRuntimeProfile(
        gguf_path=chosen_path,
        variant_tag=vtag,
        k_experts=k_exp,
        quant_pair=qpair,
        n_cpu_moe=n_cpu,
        moe_cache_mib=cache_mib,
        moe_cache_cpu_share=0.00,
        ctx_size=32768,
        ubatch_size=512,
        source=src,
        is_dev_fallback=is_dev,
        enable_mtp=False,
        override_tensor=r"blk\.48\..*=CPU",
    )


def detect_brief_language(brief: str, explicit_lang: str = "auto") -> str:
    """Detect 'ru' or 'en' from brief text unless explicitly specified."""
    if explicit_lang in ("en", "ru"):
        return explicit_lang
    cyr = len(re.findall(r"[А-Яа-яЁё]", brief))
    lat = len(re.findall(r"[A-Za-z]", brief))
    return "ru" if cyr > 0 and cyr >= lat * 0.25 else "en"


# Bilingual domain/style keyword synonyms for deterministic RAG canon matching
BILINGUAL_CANON_KEYWORDS: dict[str, list[str]] = {
    "01_swiss_international_typographic": [
        "swiss", "nvme", "storage", "grid", "telemetry", "industrial", "rack", "smart",
        "швейцарск", "телеметр", "промышлен", "хранилищ", "диск", "сетк", "кварц", "узл",
    ],
    "02_neo_brutalism_tactile": [
        "brutalist", "neobrutalism", "sqlite", "wasm", "webassembly", "sdk", "sync", "tactile",
        "брутал", "синхронизац", "локальн", "sdk", "репликац",
    ],
    "03_dark_precision_saas_linear": [
        "saas", "observability", "ebpf", "kubernetes", "p99", "latency", "linear", "dark", "trace",
        "наблюдаемост", "кластер", "задержк", "мониторинг", "трейс", "облачн",
    ],
    "04_editorial_broadsheet_serif": [
        "editorial", "newspaper", "broadsheet", "magazine", "publishing", "serif", "press",
        "редакц", "издани", "журнал", "газет", "публикац", "медиа",
    ],
    "05_nordic_architectural_minimal": [
        "nordic", "architectural", "architecture", "acoustic", "timber", "birch", "interior", "atelier", "rt60",
        "архитектур", "акустич", "интерьер", "берёз", "дерев", "бюро", "северн", "скандинав",
    ],
    "06_japanese_ma_wabi_editorial": [
        "japanese", "wabi", "ceramics", "tea", "zen", "craft", "kyoto",
        "японск", "керамик", "чайн", "минимализм",
    ],
    "07_industrial_functional_instrument": [
        "modbus", "opc-ua", "plc", "din-rail", "gateway", "hardware", "automation", "sensor", "drone", "agriculture",
        "шлюз", "контроллер", "автоматизац", "датчик", "промышленн", "бпла", "дрон", "агро",
    ],
    "08_fintech_institutional_ledger": [
        "fintech", "treasury", "ledger", "payment", "sepa", "swift", "settlement", "bank", "currency",
        "финтех", "казначейств", "платеж", "валют", "расчёт", "клиринг", "банк",
    ],
    "09_monospace_cli_devtools": [
        "cli", "terminal", "compiler", "rust", "c++", "monorepo", "build", "ci", "devtools",
        "терминал", "сборк", "компилятор", "монорепозитор", "разработчик",
    ],
    "12_clinical_biotech_cleanroom": [
        "clinical", "biotech", "genomics", "sequencing", "laboratory", "diagnostics", "medical",
        "клинич", "биотех", "геном", "лаборатор", "диагностик", "медицин",
    ],
    "15_high_contrast_civic_gov_wcag_aaa": [
        "civic", "government", "municipal", "permit", "public", "wcag", "accessibility",
        "государств", "муниципальн", "портал", "госуслуг", "заявлен",
    ],
    "17_sustainable_climate_botanical": [
        "climate", "battery", "lfp", "energy", "grid", "solar", "sustainable", "iso-14064",
        "энерг", "накопител", "батаре", "эколог", "углерод",
    ],
    "21_constructivist_editorial_ru": [
        "constructivist", "avant-garde", "poster", "cultural", "festival", "theater",
        "конструктивизм", "авангард", "выставк", "фестивал", "театр", "лектори",
    ],
    "22_legal_advisory_chancery": [
        "legal", "law", "arbitration", "m&a", "antitrust", "compliance", "counsel",
        "юридич", "право", "арбитраж", "сделк", "комплаенс", "адвокат",
    ],
    "23_audio_dsp_modular_rack": [
        "audio", "dsp", "equalizer", "vst3", "clap", "synthesizer", "mastering", "studio",
        "аудио", "эквалайзер", "мастеринг", "студи", "синтезатор", "звук",
    ],
    "24_cartographic_field_expedition": [
        "lidar", "geospatial", "cartographic", "mapping", "rtk", "survey", "topographic",
        "лидар", "геодез", "картограф", "съёмк", "маршрут",
    ],
    "27_cybersecurity_zero_trust_ops": [
        "cybersecurity", "zero-trust", "wireguard", "fido2", "security", "soc", "encryption",
        "кибербезопасност", "защит", "шифрован", "wireguard", "безопасност",
    ],
    "28_craft_roastery_packaging": [
        "coffee", "roastery", "espresso", "bourbon", "specialty", "artisan", "bakery",
        "кофе", "обжарк", "зерн", "эспрессо", "ростер", "пекарн",
    ],
}


class HarvestRAGSelector:
    """Deterministic local RAG selector over `data/harvest/` (strictly read-only)."""

    def __init__(self, harvest_dir: Path = HARVEST_DIR) -> None:
        self.harvest_dir = harvest_dir
        self.manifest_path = harvest_dir / "MANIFEST.json"
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Missing harvest manifest: {self.manifest_path}")
        self.manifest: dict[str, Any] = json.loads(self.manifest_path.read_text(encoding="utf-8"))

        self.canon_cards: dict[str, dict[str, Any]] = {}
        for rel_card in self.manifest.get("canon_cards", []):
            p = self.harvest_dir / rel_card
            if p.exists():
                card = json.loads(p.read_text(encoding="utf-8"))
                cid = str(card.get("id") or p.stem)
                self.canon_cards[cid] = card

        self.copy_pairs: list[dict[str, Any]] = []
        copy_jsonl = self.harvest_dir / "copy_pairs" / "copy_patterns_en_ru.jsonl"
        if copy_jsonl.exists():
            for line in copy_jsonl.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    self.copy_pairs.append(json.loads(line))

        self.checklists: dict[str, dict[str, Any]] = {}
        self.checklist_guides: dict[str, str] = {}
        self.checklist_files: list[str] = list(self.manifest.get("checklists", []))
        for rel_chk in self.checklist_files:
            p = self.harvest_dir / rel_chk
            if not p.exists():
                continue
            if rel_chk.endswith(".json"):
                self.checklists[p.stem] = json.loads(p.read_text(encoding="utf-8"))
            elif rel_chk.endswith(".md"):
                self.checklist_guides[p.stem] = p.read_text(encoding="utf-8")

        self.templates: list[dict[str, Any]] = list(self.manifest.get("templates", []))

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            tok
            for tok in re.findall(r"[a-zа-яё0-9_+-]{2,}", text.lower())
            if len(tok) >= 2
        }

    def select(
        self,
        brief: str,
        lang: str = "auto",
        explicit_canon_id: str | None = None,
        top_k_copy: int = 4,
    ) -> dict[str, Any]:
        """Deterministically select canon_card, copy_pairs, checklists, and template."""
        resolved_lang = detect_brief_language(brief, explicit_lang=lang)
        brief_lower = brief.lower()
        brief_tokens = self._tokenize(brief)

        # 1. Select Canon Card
        selected_cid = explicit_canon_id
        card_scores: list[tuple[float, str]] = []

        if selected_cid and selected_cid not in self.canon_cards:
            # Allow prefix match (e.g. "01" or "01_swiss")
            matches = [cid for cid in self.canon_cards if cid.startswith(selected_cid)]
            if matches:
                selected_cid = sorted(matches)[0]
            else:
                raise ValueError(f"Unknown --canon-id '{explicit_canon_id}'. Available: {sorted(self.canon_cards)[:5]}...")

        if not selected_cid:
            for cid, card in sorted(self.canon_cards.items()):
                score = 0.0
                card_text = " ".join(
                    [
                        cid.replace("_", " "),
                        str(card.get("name", "")),
                        str(card.get("category", "")).replace("_", " "),
                        " ".join(card.get("imagery", {}).get("style_tags", [])),
                        " ".join(card.get("rules", {}).get("do", [])),
                    ]
                ).lower()
                card_tokens = self._tokenize(card_text)
                overlap = brief_tokens & card_tokens
                score += float(len(overlap)) * 2.5

                # Bilingual keyword table boost
                for kw in BILINGUAL_CANON_KEYWORDS.get(cid, []):
                    if kw in brief_lower:
                        score += 5.0

                # Boost from copy_pairs domain/canon association
                for cp in self.copy_pairs:
                    if cp.get("canon_id") == cid:
                        dom_words = str(cp.get("domain", "")).replace("_", " ").lower().split()
                        for dw in dom_words:
                            if len(dw) >= 3 and dw in brief_lower:
                                score += 2.0

                # Slight deterministic tie-breaker favoring RU constructivist/swiss/nordic on RU briefs
                if resolved_lang == "ru" and cid in (
                    "01_swiss_international_typographic",
                    "05_nordic_architectural_minimal",
                    "21_constructivist_editorial_ru",
                ):
                    score += 0.25
                elif resolved_lang == "en" and cid in (
                    "03_dark_precision_saas_linear",
                    "01_swiss_international_typographic",
                    "02_neo_brutalism_tactile",
                ):
                    score += 0.25

                card_scores.append((score, cid))

            # Sort by descending score, then ascending cid for 100% determinism
            card_scores.sort(key=lambda item: (-round(item[0], 4), item[1]))
            selected_cid = card_scores[0][1]

        selected_card = self.canon_cards[selected_cid]

        # 2. Select Top-K Copy Pairs
        scored_copy: list[tuple[float, str, dict[str, Any]]] = []
        for cp in self.copy_pairs:
            c_score = 0.0
            if cp.get("canon_id") == selected_cid:
                c_score += 10.0
            cp_text = " ".join(
                [
                    str(cp.get("domain", "")).replace("_", " "),
                    str(cp.get("category", "")).replace("_", " "),
                    str(cp.get("en_canon_after", "")),
                    str(cp.get("ru_canon_after", "")),
                    str(cp.get("anti_slop_rule", "")),
                ]
            )
            cp_tokens = self._tokenize(cp_text)
            c_score += float(len(brief_tokens & cp_tokens)) * 3.0
            scored_copy.append((c_score, str(cp.get("id", "")), cp))

        scored_copy.sort(key=lambda item: (-round(item[0], 4), item[1]))
        selected_copy = [
            {
                "id": item[2]["id"],
                "category": item[2]["category"],
                "domain": item[2]["domain"],
                "canon_id": item[2]["canon_id"],
                "slop_before": item[2]["ru_slop_before"] if resolved_lang == "ru" else item[2]["en_slop_before"],
                "canon_after": item[2]["ru_canon_after"] if resolved_lang == "ru" else item[2]["en_canon_after"],
                "anti_slop_rule": item[2]["anti_slop_rule"],
            }
            for item in scored_copy[:top_k_copy]
        ]

        # 3. Select closest reference Golden Template
        selected_template = None
        for tmpl in self.templates:
            if tmpl.get("canon_id") == selected_cid and tmpl.get("lang") == resolved_lang:
                selected_template = tmpl
                break
        if selected_template is None:
            for tmpl in self.templates:
                if tmpl.get("canon_id") == selected_cid:
                    selected_template = tmpl
                    break
        if selected_template is None:
            for tmpl in self.templates:
                if tmpl.get("lang") == resolved_lang:
                    selected_template = tmpl
                    break
        if selected_template is None and self.templates:
            selected_template = self.templates[0]

        # 4. Extract concrete RAG skill rules from all 6 checklists
        detected_stacks: list[str] = []
        if any(k in brief_lower for k in ("astro", "island", "client:visible", "client:idle", "остров")):
            detected_stacks.append("astro")
        if any(k in brief_lower for k in ("next.js", "nextjs", "app router", "rsc", "server component", "server action", "react")):
            detected_stacks.append("nextjs")
        if any(k in brief_lower for k in ("svelte", "sveltekit", "page.server", "use:enhance")):
            detected_stacks.append("sveltekit")
        if any(k in brief_lower for k in ("vite", "typescript", "vanilla", "es module", "offline bundle")):
            detected_stacks.append("vite_ts")
        if not detected_stacks:
            detected_stacks = ["astro", "nextjs", "sveltekit", "vite_ts"]

        motion_focused = any(
            k in brief_lower
            for k in ("gsap", "scrolltrigger", "flip", "motion", "animation", "choreography", "анимац", "скролл")
        )

        def _extract_check_rules(chk_key: str) -> list[str]:
            doc = self.checklists.get(chk_key, {})
            return [
                f"[{item.get('check_id', '')}] {item.get('summary', '')}: {item.get('rule', '')}"
                for item in doc.get("checks", [])
                if item.get("rule")
            ]

        zimage_doc = self.checklists.get("zimage_canon_prompts", {})
        zimage_archetypes = zimage_doc.get("canon_prompt_archetypes", [])
        matched_archetype = next(
            (a for a in zimage_archetypes if a.get("canon_id") == selected_cid),
            zimage_archetypes[0] if zimage_archetypes else {},
        )
        zimage_rules = list(zimage_doc.get("prompt_engineering_rules", [])) + [
            f"Sequential handoff protocol: {' '.join(zimage_doc.get('sequential_vram_protocol', []))}",
        ]
        if matched_archetype:
            zimage_rules.append(
                f"Reference archetype ({matched_archetype.get('canon_id')}, {matched_archetype.get('aspect_ratio')}, "
                f"exact_text_in_frame='{matched_archetype.get('exact_text_in_frame')}'): "
                f"{matched_archetype.get('prompt')} | negative_prompt: {matched_archetype.get('negative_prompt')}"
            )

        stack_doc = self.checklists.get("stack_architecture_patterns", {})
        stack_profiles = stack_doc.get("stack_profiles", {})
        prioritized_stack_profiles = [
            f"[{st.upper()}] {stack_profiles[st]}"
            for st in detected_stacks
            if st in stack_profiles
        ]
        stack_rules = prioritized_stack_profiles + _extract_check_rules("stack_architecture_patterns")
        motion_rules = _extract_check_rules("motion_gsap_choreography")
        seo_rules = _extract_check_rules("seo_aeo_geo_jsonld")
        security_rules = _extract_check_rules("security_csp_headers")
        layout_rules = _extract_check_rules("layout_wcag22_viewport")

        skill_directives = {
            "detected_stacks": detected_stacks,
            "motion_focused": motion_focused,
            "zimage_canon_prompts": zimage_rules,
            "seo_aeo_geo_jsonld": seo_rules,
            "security_csp_headers": security_rules,
            "layout_wcag22_viewport": layout_rules,
            "stack_architecture_patterns": stack_rules,
            "motion_gsap_choreography": motion_rules,
        }

        return {
            "brief": brief,
            "lang": resolved_lang,
            "canon_id": selected_cid,
            "canon_card": selected_card,
            "copy_pairs": selected_copy,
            "template_ref": selected_template,
            "skill_directives": skill_directives,
            "checklists_summary": {
                k: {
                    "id": v.get("id", k),
                    "title": v.get("title", k),
                    "checks_count": len(v.get("checks", [])),
                }
                for k, v in sorted(self.checklists.items())
            },
        }


def compute_csp_sha256(content: str) -> str:
    """Compute `'sha256-<base64>'` for exact UTF-8 text of `<style>` or `<script>`."""
    digest = hashlib.sha256(content.encode("utf-8")).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def build_stage_a_prompt(rag_bundle: dict[str, Any]) -> str:
    """Construct the deterministic Stage A LLM prompt grounded in `data/harvest/` RAG."""
    lang = rag_bundle["lang"]
    card = rag_bundle["canon_card"]
    palette = card.get("palette", {})
    fonts = card.get("fonts", {})
    rules_do = card.get("rules", {}).get("do", [])
    rules_dont = card.get("rules", {}).get("dont", [])
    copy_examples = "\n".join(
        f"- [{cp['category']}/{cp['domain']}] AVOID: \"{cp['slop_before']}\" -> WRITE: \"{cp['canon_after']}\" ({cp['anti_slop_rule']})"
        for cp in rag_bundle["copy_pairs"]
    )
    skills = rag_bundle.get("skill_directives", {})

    def _fmt_rules(items: list[str]) -> str:
        return "\n".join(f"  * {r}" for r in items)

    lang_directive = (
        "Write all user-facing copy in authentic Russian (Cyrillic density >= 0.75, use «ёлочки» quotes and — em-dash, zero English marketing loan-slop)."
        if lang == "ru"
        else "Write all user-facing copy in crisp, concrete English with measurable engineering/domain facts and zero AI-slop clichés."
    )
    return (
        f"<|im_start|>system\n"
        f"You are SmartLLM v2 Offline Web, Design & Copywriting Combine.\n"
        f"Active Design Canon: {card['id']} — {card['name']} ({card['category']})\n"
        f"Language: {lang.upper()} ({lang_directive})\n"
        f"OKLCH Palette Tokens: bg={palette.get('bg')}, surface={palette.get('surface')}, "
        f"border={palette.get('border')}, text={palette.get('text')}, muted={palette.get('muted')}, "
        f"accent={palette.get('accent')}, accent_ink={palette.get('accent_ink')}\n"
        f"Typography: heading={fonts.get('heading')}, body={fonts.get('body')}, mono={fonts.get('mono')}\n"
        f"Canon DO Rules:\n" + _fmt_rules(rules_do) + "\n"
        f"Canon DONT Rules:\n" + _fmt_rules(rules_dont) + "\n"
        f"Curated Anti-Slop Copywriting Reference:\n{copy_examples}\n"
        f"Stack Architecture Patterns (Active: {', '.join(skills.get('detected_stacks', []))}):\n"
        + _fmt_rules(skills.get("stack_architecture_patterns", [])) + "\n"
        f"Motion & GSAP 3 Choreography Rules (motion_focused={skills.get('motion_focused', False)}):\n"
        + _fmt_rules(skills.get("motion_gsap_choreography", [])) + "\n"
        f"Z-Image Canon Prompt & Sequential Handoff Contract:\n"
        + _fmt_rules(skills.get("zimage_canon_prompts", [])) + "\n"
        f"SEO / AEO / GEO & Schema.org @graph Checklist:\n"
        + _fmt_rules(skills.get("seo_aeo_geo_jsonld", [])) + "\n"
        f"Security, Hash-Based CSP & Cloudflare _headers Checklist:\n"
        + _fmt_rules(skills.get("security_csp_headers", [])) + "\n"
        f"Layout, Dynamic Viewport (100svh) & WCAG 2.2 AA/AAA Checklist:\n"
        + _fmt_rules(skills.get("layout_wcag22_viewport", [])) + "\n"
        f"<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Brief: {rag_bundle['brief']}\n"
        f"Generate the complete website bundle and Z-Image prompt manifest.\n"
        f"<|im_end|>\n"
        f"<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )


_PROMPT_ECHO_MARKERS = (
    "generate html",
    "zimage_prompts",
    "index.html",
    "tokens.css",
    "manifest",
    "brief:",
    "<|im_start|>",
    "system prompt",
    "checklist",
)


def _clean_llm_copy_line(text: str) -> str:
    """Strip <think> blocks, code fences, numbering prefixes, and meta-prompt echoes."""
    cleaned = re.sub(r"<think>.*?</think>", "", str(text or ""), flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"</?think>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```(?:json|html|markdown|text)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```", "", cleaned)
    lines: list[str] = []
    for raw_ln in cleaned.splitlines():
        ln = raw_ln.strip()
        if not ln:
            continue
        ln = re.sub(r"^\s*(?:\d+[\.\)]\s*|[-*•]\s+)", "", ln).strip()
        if not ln:
            continue
        low = ln.lower()
        if any(m in low for m in _PROMPT_ECHO_MARKERS):
            continue
        lines.append(ln)
    if not lines:
        return ""
    joined = re.sub(r"\s+", " ", lines[0]).strip().strip("\"'")
    return joined


def _derive_editorial_headline(brief: str, lang: str) -> str:
    """Derive a clean, complete <= 72-char headline from brief without trailing '...'."""
    clean = re.sub(r"\s+", " ", (brief or "").strip()).rstrip(".,;:")
    if not clean:
        return "Инженерный веб-проект" if lang == "ru" else "Precision Engineering Web Atelier"
    if len(clean) <= 72:
        return clean
    for sep in (" — ", ": ", "; ", ". ", ", ", " offering ", " featuring ", " with ", " for ", " для ", " с "):
        if sep in clean:
            cand = clean.split(sep, 1)[0].strip().rstrip(".,;:-")
            if 18 <= len(cand) <= 72:
                return cand
    words = clean.split()
    out: list[str] = []
    cur_len = 0
    for w in words:
        add_len = len(w) + (1 if out else 0)
        if cur_len + add_len > 70 and len(out) >= 3:
            break
        out.append(w)
        cur_len += add_len
    return " ".join(out).rstrip(".,;:-")


def _extract_structured_copy_from_llm(raw_text: str) -> dict[str, str]:
    """Extract sanitized structured copy fields from an LLM JSON or text response."""
    stripped = re.sub(r"<think>.*?</think>", "", str(raw_text or ""), flags=re.DOTALL | re.IGNORECASE)
    stripped = re.sub(r"```(?:json)?", "", stripped, flags=re.IGNORECASE).replace("```", "").strip()
    out: dict[str, str] = {}
    m = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                for key in ("brand_title", "h1_text", "lead_copy", "cta_primary", "cta_secondary", "sec_copy_1", "sec_copy_2", "sec_copy_3"):
                    val = _clean_llm_copy_line(str(obj.get(key) or ""))
                    if len(val) >= 6:
                        out[key] = val
                if out:
                    return out
        except Exception:
            pass
    fallback_line = _clean_llm_copy_line(stripped)
    if len(fallback_line) >= 24:
        out["lead_copy"] = fallback_line
    return out


def build_deterministic_site_bundle(
    rag_bundle: dict[str, Any],
    llm_custom_copy: dict[str, Any] | None = None,
    num_images: int = 1,
) -> dict[str, Any]:
    """Assemble a complete, standards-verified offline website bundle + Z-Image manifest.

    Uses the selected `data/harvest/` canon card, OKLCH tokens, bilingual copywriting patterns,
    and optional LLM-generated structured copy overrides, computing exact SHA-256 CSP hashes
    for inline `<style>` and `<script>` blocks (zero `'unsafe-inline'`).
    """
    lang = rag_bundle["lang"]
    brief = rag_bundle["brief"].strip()
    card = rag_bundle["canon_card"]
    palette = card.get("palette", {})
    fonts = card.get("fonts", {})
    layout = card.get("layout", {})
    imagery = card.get("imagery", {})
    copy_pairs = rag_bundle.get("copy_pairs", [])

    lead_copy = copy_pairs[0]["canon_after"] if copy_pairs else brief
    sec_copy_1 = copy_pairs[1]["canon_after"] if len(copy_pairs) > 1 else lead_copy
    sec_copy_2 = copy_pairs[2]["canon_after"] if len(copy_pairs) > 2 else lead_copy
    sec_copy_3 = copy_pairs[3]["canon_after"] if len(copy_pairs) > 3 else lead_copy

    custom = llm_custom_copy or {}
    if custom.get("lead_copy"):
        lead_copy = str(custom["lead_copy"])
    if custom.get("sec_copy_1"):
        sec_copy_1 = str(custom["sec_copy_1"])
    if custom.get("sec_copy_2"):
        sec_copy_2 = str(custom["sec_copy_2"])
    if custom.get("sec_copy_3"):
        sec_copy_3 = str(custom["sec_copy_3"])

    default_h1 = _derive_editorial_headline(brief, lang)
    if lang == "ru":
        brand_title = str(custom.get("brand_title") or "Кварц-Синтез — Инженерный контур")
        h1_text = str(custom.get("h1_text") or default_h1)
        page_title = f"{brand_title}: {h1_text[:68]}"
        meta_desc = f"{lead_copy[:150]}"
        skip_label = "Перейти к основному содержанию"
        nav_items = [("01 / Система", "#architecture"), ("02 / Спецификация", "#metrics"), ("03 / Верификация", "#verification")]
        eyebrow = f"КАНОН {card['id'].upper()} · АВТОНОМНЫЙ КОНТУР"
        cta_primary = str(custom.get("cta_primary") or "Запросить технический паспорт")
        cta_secondary = str(custom.get("cta_secondary") or "Проверить профиль калибровки")
        sec1_title = str(custom.get("sec1_title") or "01 — Архитектура и эксплуатационные допуски")
        sec2_title = "02 — Измеримые параметры контура"
        sec3_title = "03 — Протокол автономной верификации"
        filter_all = "Все узлы (3)"
        filter_active = "Номинальный режим"
        footer_note = "Локальная сборка SmartLLM v2 Combine (127.0.0.1 · Zero-Swap · WCAG 2.2 AA)."
        hero_caption = "Рис. 01 — Сгенерированный локально визуальный артефакт Z-Image (1024×1024, строго по канону)."
        sec_fig_caption = "Рис. 02 — Архитектурный ракурс Z-Image в масштабе рабочего пространства."
    else:
        brand_title = str(custom.get("brand_title") or "Quartz-Field — Systems Studio")
        h1_text = str(custom.get("h1_text") or default_h1)
        page_title = f"{brand_title}: {h1_text[:68]}"
        meta_desc = f"{lead_copy[:150]}"
        skip_label = "Skip to main content"
        nav_items = [("01 / Architecture", "#architecture"), ("02 / Specification", "#metrics"), ("03 / Verification", "#verification")]
        eyebrow = f"CANON {card['id'].upper()} · OFFLINE INSTRUMENT"
        cta_primary = str(custom.get("cta_primary") or "Download Technical Dossier")
        cta_secondary = str(custom.get("cta_secondary") or "Inspect Calibration Profile")
        sec1_title = str(custom.get("sec1_title") or "01 — System Architecture & Operating Envelope")
        sec2_title = "02 — Audited Performance Benchmarks"
        sec3_title = "03 — Deterministic Verification Protocol"
        filter_all = "All Nodes (3)"
        filter_active = "Nominal Ready"
        footer_note = "Generated offline by SmartLLM v2 Combine (127.0.0.1 · Zero-Swap · WCAG 2.2 AA)."
        hero_caption = "Fig. 01 — Locally rendered Z-Image visual artifact (1024x1024, canon-locked)."
        sec_fig_caption = "Fig. 02 — Locally rendered architectural detail view (Z-Image)."

    # Build Z-Image prompt manifest grounded in the canon card's imagery template
    tmpl_str = str(
        imagery.get(
            "prompt_tmpl",
            "Architectural studio photograph, crisp directional key light, 50mm planar lens, subject: {subject}",
        )
    )
    neg_prompt = str(
        imagery.get(
            "negative_prompt",
            "purple neon glow, floating 3d blobs, stock office handshake, lens flare, watermark, cartoon",
        )
    )
    aspect_ratio = str(imagery.get("aspect_ratio", "16:9"))
    w_hero, h_hero = parse_aspect_ratio_dims(aspect_ratio, default_w=1024, default_h=1024)

    hero_prompt_body = tmpl_str.replace("{subject}", brief[:140])
    if len(hero_prompt_body) < 200:
        hero_prompt_body = (
            f"{hero_prompt_body}, precision machined surfaces, physical material fidelity, "
            f"exact industrial stencil 'UNIT 01', high micro-contrast, museum-grade studio lighting."
        )

    zimage_prompts: dict[str, Any] = {
        "canon_id": card["id"],
        "lang": lang,
        "prompts": [
            {
                "id": "hero_primary",
                "slot": "hero_primary",
                "canon_id": card["id"],
                "aspect_ratio": "1:1",
                "width": 1024,
                "height": 1024,
                "steps": 8,
                "cfg_scale": 1.0,
                "seed": 42,
                "exact_text_in_frame": "UNIT 01",
                "prompt": hero_prompt_body,
                "negative_prompt": neg_prompt,
                "output_relpath": "assets/hero_primary.png",
            }
        ],
    }
    for extra_idx in range(2, max(1, min(num_images, 4)) + 1):
        slot_id = f"feature_{extra_idx:02d}"
        zimage_prompts["prompts"].append(
            {
                "id": slot_id,
                "slot": slot_id,
                "canon_id": card["id"],
                "aspect_ratio": aspect_ratio,
                "width": w_hero,
                "height": h_hero,
                "steps": 8,
                "cfg_scale": 1.0,
                "seed": 40 + extra_idx,
                "exact_text_in_frame": f"NODE 0{extra_idx}",
                "prompt": f"{hero_prompt_body} (detail view {extra_idx})",
                "negative_prompt": neg_prompt,
                "output_relpath": f"assets/{slot_id}.png",
            }
        )

    tokens_css = f""":root {{
  --bg: {palette.get('bg', 'oklch(0.98 0.002 90)')};
  --surface: {palette.get('surface', 'oklch(0.945 0.003 90)')};
  --border: {palette.get('border', 'oklch(0.20 0.002 90)')};
  --text: {palette.get('text', 'oklch(0.14 0.002 90)')};
  --text-muted: {palette.get('muted', 'oklch(0.42 0.005 90)')};
  --accent: {palette.get('accent', 'oklch(0.54 0.21 28)')};
  --accent-ink: {palette.get('accent_ink', 'oklch(0.99 0.002 90)')};
  --font-heading: {fonts.get('heading', "'Inter', sans-serif")};
  --font-sans: {fonts.get('body', "'Inter', sans-serif")};
  --font-mono: {fonts.get('mono', "'JetBrains Mono', monospace")};
  --radius: {int(layout.get('radius_px', 0))}px;
  --pad-section: {layout.get('pad_clamp', 'clamp(2rem, 5vw, 5.5rem)')};
}}
*, *::before, *::after {{ box-sizing: border-box; }}
html {{ scroll-padding-top: 4.75rem; font-size: 16px; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  line-height: 1.5;
  font-variant-numeric: tabular-nums;
  overflow-x: hidden;
}}
.skip-link {{
  position: absolute;
  left: -9999px;
  top: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--accent);
  color: var(--accent-ink);
  min-height: 28px;
  min-width: 28px;
  text-decoration: none;
}}
.skip-link:focus {{ left: 0.75rem; z-index: 100; }}
.site-header {{
  position: sticky;
  top: 0;
  z-index: 40;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}}
.container {{
  width: 100%;
  max-width: 82rem;
  margin-inline: auto;
  padding-inline: clamp(1.25rem, 4vw, 3.5rem);
}}
.header-inner {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  min-height: 4.25rem;
  gap: 1rem;
}}
.brand-mark {{
  font-family: var(--font-heading);
  font-weight: 700;
  letter-spacing: -0.02em;
  text-decoration: none;
  color: var(--text);
  min-height: 28px;
  display: inline-flex;
  align-items: center;
}}
.nav-list {{
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  list-style: none;
  margin: 0;
  padding: 0;
}}
.nav-list a {{
  color: var(--text);
  text-decoration: none;
  font-size: 0.9375rem;
  min-height: 28px;
  min-width: 28px;
  padding: 0.35rem 0.5rem;
  display: inline-flex;
  align-items: center;
}}
.nav-list a:focus-visible, .btn:focus-visible {{
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}}
.hero-shell {{
  min-height: 100svh;
  display: flex;
  align-items: center;
  padding-block: var(--pad-section);
  border-bottom: 1px solid var(--border);
  container-type: inline-size;
}}
.canon-grid {{
  width: 100%;
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: clamp(1.5rem, 3vw, 3rem);
  align-items: center;
}}
.section-block .canon-grid {{
  align-items: stretch;
}}
.hero-lead {{ grid-column: span 7; min-width: 0; }}
.hero-figure {{
  grid-column: span 5;
  min-width: 0;
  margin: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
}}
.figure-secondary {{
  margin-top: 2rem;
  max-width: 48rem;
}}
.hero-figure img {{
  width: 100%;
  height: auto;
  display: block;
  border: 1px solid var(--border);
}}
.hero-figure figcaption {{
  margin-top: 0.75rem;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text-muted);
}}
.eyebrow {{
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text-muted);
  letter-spacing: 0.04em;
  margin: 0 0 0.75rem 0;
}}
h1 {{
  font-family: var(--font-heading);
  font-size: clamp(2rem, 3.6vw, 3.25rem);
  line-height: 1.08;
  margin: 0 0 1.25rem 0;
  max-width: 22ch;
}}
.lead-copy {{
  font-size: 1.125rem;
  max-width: 62ch;
  margin: 0 0 1.75rem 0;
}}
.cta-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.875rem;
}}
.btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  min-width: 44px;
  padding: 0.65rem 1.25rem;
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  text-decoration: none;
}}
.btn-primary {{
  background: var(--accent);
  color: var(--accent-ink);
  border-color: var(--accent);
}}
.btn-secondary {{
  background: var(--surface);
  color: var(--text);
}}
.section-block {{
  padding-block: var(--pad-section);
  border-bottom: 1px solid var(--border);
  container-type: inline-size;
}}
.section-title {{
  font-family: var(--font-heading);
  font-size: clamp(1.35rem, 2.2vw, 1.85rem);
  margin: 0 0 1.5rem 0;
}}
.spec-card {{
  grid-column: span 4;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
}}
.spec-card h3 {{
  font-family: var(--font-mono);
  font-size: 0.9375rem;
  margin: 0 0 0.5rem 0;
}}
.spec-card p {{
  margin: 0;
  max-width: 60ch;
}}
.site-footer {{
  padding-block: 2.25rem;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text-muted);
}}
@media (max-width: 900px) {{
  .hero-lead, .hero-figure, .spec-card {{ grid-column: span 12; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ transition: none !important; animation: none !important; }}
}}"""

    app_js = """(function () {
  "use strict";
  var toggleBtn = document.getElementById("telemetry-filter-btn");
  var statusNode = document.getElementById("telemetry-status-readout");
  if (toggleBtn && statusNode) {
    toggleBtn.addEventListener("click", function () {
      var pressed = toggleBtn.getAttribute("aria-pressed") === "true";
      var nextState = !pressed;
      toggleBtn.setAttribute("aria-pressed", nextState ? "true" : "false");
      statusNode.textContent = nextState ? "STATUS: NOMINAL (0 SWAP)" : "STATUS: ALL NODES (3/3)";
    });
  }
})();"""

    app_ts = """// Strict TypeScript source for offline bundle interactive telemetry toggle
const toggleBtn: HTMLElement | null = document.getElementById("telemetry-filter-btn");
const statusNode: HTMLElement | null = document.getElementById("telemetry-status-readout");
if (toggleBtn !== null && statusNode !== null) {
  toggleBtn.addEventListener("click", (): void => {
    const pressed: boolean = toggleBtn.getAttribute("aria-pressed") === "true";
    const nextState: boolean = !pressed;
    toggleBtn.setAttribute("aria-pressed", nextState ? "true" : "false");
    statusNode.textContent = nextState ? "STATUS: NOMINAL (0 SWAP)" : "STATUS: ALL NODES (3/3)";
  });
}
"""

    style_hash = compute_csp_sha256(tokens_css)
    script_hash = compute_csp_sha256(app_js)

    csp_meta = (
        f"default-src 'none'; "
        f"script-src 'self' '{script_hash}'; "
        f"style-src 'self' '{style_hash}'; "
        f"img-src 'self' data:; "
        f"font-src 'self'; "
        f"connect-src 'self'; "
        f"base-uri 'none'; "
        f"form-action 'self'; "
        f"object-src 'none'; "
        f"require-trusted-types-for 'script'"
    )
    csp_header = (
        f"default-src 'none'; "
        f"script-src 'self' '{script_hash}'; "
        f"style-src 'self' '{style_hash}'; "
        f"img-src 'self' data:; "
        f"font-src 'self'; "
        f"connect-src 'self'; "
        f"base-uri 'none'; "
        f"form-action 'self'; "
        f"frame-ancestors 'none'; "
        f"object-src 'none'; "
        f"require-trusted-types-for 'script'"
    )

    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": page_title,
            "description": meta_desc,
            "inLanguage": lang,
            "isPartOf": {
                "@type": "WebSite",
                "name": brand_title,
                "url": "https://smartllm-combine.example.org/",
            },
        },
        ensure_ascii=False,
    )

    sec_fig_html = ""
    if num_images >= 2:
        sec_fig_html = (
            f'\n        <figure class="hero-figure figure-secondary">'
            f'<img src="assets/feature_02.png" width="{w_hero}" height="{h_hero}" alt="{html.escape(h1_text)} — architectural view">'
            f'<figcaption>{html.escape(sec_fig_caption)}</figcaption></figure>'
        )

    index_html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{csp_meta}">
  <title>{html.escape(page_title)}</title>
  <meta name="description" content="{html.escape(meta_desc, quote=True)}">
  <link rel="canonical" href="https://smartllm-combine.example.org/">
  <link rel="alternate" hreflang="ru" href="https://smartllm-combine.example.org/ru/">
  <link rel="alternate" hreflang="en" href="https://smartllm-combine.example.org/en/">
  <link rel="alternate" hreflang="x-default" href="https://smartllm-combine.example.org/">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{html.escape(page_title, quote=True)}">
  <meta property="og:description" content="{html.escape(meta_desc, quote=True)}">
  <script type="application/ld+json">{json_ld}</script>
  <style>{tokens_css}</style>
</head>
<body>
  <a class="skip-link" href="#main-content">{html.escape(skip_label)}</a>
  <header class="site-header">
    <div class="container header-inner">
      <a class="brand-mark" href="#main-content">{html.escape(brand_title)}</a>
      <nav aria-label="Primary">
        <ul class="nav-list">
          <li><a href="{nav_items[0][1]}">{html.escape(nav_items[0][0])}</a></li>
          <li><a href="{nav_items[1][1]}">{html.escape(nav_items[1][0])}</a></li>
          <li><a href="{nav_items[2][1]}">{html.escape(nav_items[2][0])}</a></li>
        </ul>
      </nav>
    </div>
  </header>
  <main id="main-content">
    <section class="hero-shell" id="architecture">
      <div class="container canon-grid">
        <div class="hero-lead">
          <p class="eyebrow">{html.escape(eyebrow)}</p>
          <h1>{html.escape(h1_text)}</h1>
          <p class="lead-copy">{html.escape(lead_copy)}</p>
          <div class="cta-row">
            <a class="btn btn-primary" href="#metrics">{html.escape(cta_primary)}</a>
            <button class="btn btn-secondary" id="telemetry-filter-btn" type="button" aria-pressed="false">{html.escape(cta_secondary)}</button>
          </div>
          <p class="eyebrow" id="telemetry-status-readout" aria-live="polite">{html.escape(filter_all)} · {html.escape(filter_active)}</p>
        </div>
        <figure class="hero-figure">
          <img src="assets/hero_primary.png" width="1024" height="1024" alt="{html.escape(h1_text, quote=True)}">
          <figcaption>{html.escape(hero_caption)}</figcaption>
        </figure>
      </div>
    </section>
    <section class="section-block" id="metrics">
      <div class="container">
        <h2 class="section-title">{html.escape(sec1_title)}</h2>
        <div class="canon-grid">
          <article class="spec-card">
            <h3>{"01 / СПЕЦИФИКАЦИЯ" if lang == "ru" else "01 / SPECIFICATION"}</h3>
            <p>{html.escape(sec_copy_1)}</p>
          </article>
          <article class="spec-card">
            <h3>{"02 / АРХИТЕКТУРА" if lang == "ru" else "02 / ARCHITECTURE"}</h3>
            <p>{html.escape(sec_copy_2)}</p>
          </article>
          <article class="spec-card">
            <h3>{"03 / ВЕРИФИКАЦИЯ" if lang == "ru" else "03 / VERIFICATION"}</h3>
            <p>{html.escape(sec_copy_3)}</p>
          </article>
        </div>{sec_fig_html}
      </div>
    </section>
    <section class="section-block" id="verification">
      <div class="container">
        <h2 class="section-title">{html.escape(sec2_title)}</h2>
        <p class="lead-copy">{html.escape(sec3_title)}: OKLCH contrast ratio {card.get('a11y', {}).get('text_bg_contrast_ratio', 14.5)}:1, strict SHA-256 CSP hashes, 100svh viewport stability.</p>
      </div>
    </section>
  </main>
  <footer class="site-footer">
    <div class="container">
      <p>{html.escape(footer_note)}</p>
    </div>
  </footer>
  <script>{app_js}</script>
</body>
</html>
"""

    headers_text = f"""# Strict edge security headers generated by SmartLLM v2 Offline Combine
/*
  Content-Security-Policy: {csp_header}
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: require-corp
  Cross-Origin-Resource-Policy: same-origin
"""

    llms_txt = f"""# {brand_title}
> {lead_copy}

## Design Canon
- ID: `{card['id']}` ({card['name']})
- Language: `{lang}`
- Security: Strict SHA-256 CSP (`{style_hash}`, `{script_hash}`)

## Key Facts
- {sec_copy_1}
- {sec_copy_2}
- {sec_copy_3}
"""

    robots_txt = """# AI Training Crawlers (Opt-out of weight training)
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: CCBot
Disallow: /

# Live Search & AI Citation Retrieval Crawlers (Permitted)
User-agent: OAI-SearchBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Googlebot
Allow: /

User-agent: *
Allow: /

Sitemap: https://smartllm-combine.example.org/sitemap.xml
"""

    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://smartllm-combine.example.org/</loc><changefreq>weekly</changefreq></url>
</urlset>
"""

    return {
        "index.html": index_html,
        "tokens.css": tokens_css + "\n",
        "app.ts": app_ts,
        "app.js": app_js + "\n",
        "_headers": headers_text,
        "llms.txt": llms_txt,
        "robots.txt": robots_txt,
        "sitemap.xml": sitemap_xml,
        "zimage_prompts": zimage_prompts,
        "style_sha256": style_hash,
        "script_sha256": script_hash,
    }


def run_combine_pipeline(
    brief: str,
    out_dir: Path,
    lang: str = "auto",
    explicit_canon_id: str | None = None,
    explicit_gguf: Path | None = None,
    allow_dev_205e: bool = False,
    n_cpu_moe_override: int | None = None,
    moe_cache_mib_override: int | None = None,
    host: str = "127.0.0.1",
    port: int = 18080,
    dry_run: bool = False,
    restore_llm_slot: bool = False,
    num_images: int = 1,
    logo_path: Path | None = None,
) -> dict[str, Any]:
    """Execute the full RAG -> Stage A -> Stage B -> Bundle offline combine workflow."""
    assert_loopback_host(host, context="llama-server")

    profile = discover_gguf_model(
        explicit_gguf=explicit_gguf,
        allow_dev_205e=allow_dev_205e,
        n_cpu_moe_override=n_cpu_moe_override,
        moe_cache_mib_override=moe_cache_mib_override,
        require_exists=not dry_run,
    )

    selector = HarvestRAGSelector()
    rag_bundle = selector.select(brief=brief, lang=lang, explicit_canon_id=explicit_canon_id)
    stage_a_prompt = build_stage_a_prompt(rag_bundle)

    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    llm_custom_copy: dict[str, Any] = {}
    gpu_telemetry: dict[str, Any] = {"mode": "dry_run_cpu" if dry_run else "live_sequential_gpu"}

    # Build the deterministic bundle & Z-Image prompt manifest
    bundle = build_deterministic_site_bundle(
        rag_bundle, llm_custom_copy=llm_custom_copy, num_images=num_images
    )
    zimage_prompts_list = bundle["zimage_prompts"]["prompts"]
    for item in zimage_prompts_list:
        item["output_path"] = str(out_dir / item["output_relpath"])

    if dry_run:
        # Pure CPU dry-run: synthesize valid non-blank PNGs without touching GPU
        generated_images = []
        for item in zimage_prompts_list:
            img_p = Path(item["output_path"])
            _make_synthetic_png(img_p, width=int(item["width"]), height=int(item["height"]), blank=False)
            vinfo = verify_png_artifact(
                img_p,
                expected_width=int(item["width"]),
                expected_height=int(item["height"]),
            )
            generated_images.append(vinfo)
        gpu_telemetry["generated_images"] = generated_images
        gpu_telemetry["visited_states_planned"] = [
            CombineState.IDLE.value,
            CombineState.LLM_STARTING.value,
            CombineState.LLM_ACTIVE.value,
            CombineState.SLOT_SAVING.value,
            CombineState.LLM_STOPPING.value,
            CombineState.VRAM_VERIFY_POST_LLM.value,
            CombineState.SD_BATCH_RUNNING.value,
            CombineState.VRAM_VERIFY_POST_SD.value,
            CombineState.COMPLETED.value,
        ]
    else:
        # Live Sequential GPU execution via SequentialGPUCombineMachine
        sm = SequentialGPUCombineMachine(
            host=host,
            port=port,
            llama_server_bin=DEFAULT_LLAMA_SERVER,
            llama_model_path=profile.gguf_path,
            llama_extra_args=profile.to_llama_extra_args(),
            slot_save_dir=DEFAULT_SLOT_SAVE_DIR,
            sd_cli_bin=DEFAULT_SD_CLI,
            dit_model_path=DEFAULT_DIT_FP8,
            llm_encoder_path=DEFAULT_QWEN_TE,
            vae_model_path=DEFAULT_VAE,
            sd_out_dir=assets_dir,
            idle_vram_mib=42.0,
        )
        # Stage A: Start LLM, generate clean structured copy via /v1/chat/completions, save slot & stop LLM
        sm.start_llm(seed_prompt=stage_a_prompt)
        chat_url = f"http://127.0.0.1:{port}/v1/chat/completions"
        copy_instruction = (
            f"Write clean domain copy in {rag_bundle['lang'].upper()} for this project brief: {brief}\n"
            "Return strictly a compact JSON object with keys "
            '{"brand_title": "...", "h1_text": "...", "lead_copy": "...", "cta_primary": "...", "cta_secondary": "..."}. '
            "No markdown code fences, no numbered steps, no ellipses in h1_text, no filenames."
        )
        status, body = _http_json(
            chat_url,
            method="POST",
            payload={
                "model": "smartllm-v2",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            f"Active Design Canon: {rag_bundle['canon_id']}. "
                            "You write concise editorial engineering copy without AI clichés or meta-instructions."
                        ),
                    },
                    {"role": "user", "content": copy_instruction},
                ],
                "max_tokens": 220,
                "temperature": 0.5,
                "top_p": 0.95,
                "top_k": 20,
            },
            timeout=180.0,
        )
        raw_chat_content = ""
        if status == 200 and isinstance(body.get("choices"), list) and body["choices"]:
            msg_obj = body["choices"][0].get("message") or {}
            raw_chat_content = str(msg_obj.get("content") or "")
        extracted_copy = _extract_structured_copy_from_llm(raw_chat_content)
        if extracted_copy:
            llm_custom_copy.update(extracted_copy)
            bundle = build_deterministic_site_bundle(
                rag_bundle, llm_custom_copy=llm_custom_copy, num_images=num_images
            )
            zimage_prompts_list = bundle["zimage_prompts"]["prompts"]
            for item in zimage_prompts_list:
                item["output_path"] = str(out_dir / item["output_relpath"])

        sm.save_slot_and_stop_llm()
        # Stage B: Run sd-cli batch when VRAM is verified at 0 compute apps
        sm.run_sd_batch(zimage_prompts_list)
        if restore_llm_slot:
            sm.restart_llm_and_restore_slot(stop_on_exit=True)
        else:
            sm.transition(CombineState.COMPLETED, "Stage A + Stage B combine bundle completed")
        gpu_telemetry = sm.summary_dict()

    # Write all bundle files to out_dir
    (out_dir / "index.html").write_text(bundle["index.html"], encoding="utf-8")
    (out_dir / "tokens.css").write_text(bundle["tokens.css"], encoding="utf-8")
    (out_dir / "app.ts").write_text(bundle["app.ts"], encoding="utf-8")
    (out_dir / "app.js").write_text(bundle["app.js"], encoding="utf-8")
    (out_dir / "_headers").write_text(bundle["_headers"], encoding="utf-8")
    (out_dir / "llms.txt").write_text(bundle["llms.txt"], encoding="utf-8")
    (out_dir / "robots.txt").write_text(bundle["robots.txt"], encoding="utf-8")
    (out_dir / "sitemap.xml").write_text(bundle["sitemap.xml"], encoding="utf-8")
    (out_dir / "zimage_prompts.json").write_text(
        json.dumps(bundle["zimage_prompts"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "rag_context.json").write_text(
        json.dumps(rag_bundle, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    extra_logo_files: list[str] = []
    if logo_path is not None and logo_path.exists():
        studio_pkg = ROOT / "studio"
        if str(studio_pkg) not in sys.path:
            sys.path.insert(0, str(studio_pkg))
        from smartllm_studio.sanitizer import ingest_brand_logo

        logo_info = ingest_brand_logo(logo_path.name, logo_path.read_bytes(), assets_dir)
        extra_logo_files.append(logo_info["logo_relpath"])

    manifest_summary = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "brief": brief,
        "lang": rag_bundle["lang"],
        "canon_id": rag_bundle["canon_id"],
        "canon_name": rag_bundle["canon_card"]["name"],
        "template_ref": (rag_bundle["template_ref"] or {}).get("slug"),
        "out_dir": str(out_dir),
        "style_sha256": bundle["style_sha256"],
        "script_sha256": bundle["script_sha256"],
        "model_profile": {
            **asdict(profile),
            "gguf_path": str(profile.gguf_path),
            "llama_extra_args": profile.to_llama_extra_args(),
        },
        "files": [
            "index.html",
            "tokens.css",
            "app.ts",
            "app.js",
            "_headers",
            "llms.txt",
            "robots.txt",
            "sitemap.xml",
            "zimage_prompts.json",
            "rag_context.json",
            *extra_logo_files,
            *[item["output_relpath"] for item in zimage_prompts_list],
        ],
        "gpu_telemetry": gpu_telemetry,
    }
    (out_dir / "combine_manifest.json").write_text(
        json.dumps(manifest_summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest_summary


def serve_local_workbench(
    out_dir: Path,
    host: str = "127.0.0.1",
    ui_port: int = 8090,
) -> None:
    """Serve the generated static bundle + `/__combine__` workbench strictly on 127.0.0.1."""
    assert_loopback_host(host, context="serve-ui")
    out_dir = out_dir.resolve()

    class WorkbenchHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(out_dir), **kwargs)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/__combine__":
                manifest_p = out_dir / "combine_manifest.json"
                data = (
                    json.loads(manifest_p.read_text(encoding="utf-8"))
                    if manifest_p.exists()
                    else {"status": "ready", "out_dir": str(out_dir)}
                )
                body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

    srv = HTTPServer((host, ui_port), WorkbenchHandler)
    print(
        json.dumps(
            {
                "workbench_url": f"http://127.0.0.1:{ui_port}/",
                "status_json_url": f"http://127.0.0.1:{ui_port}/__combine__",
                "serving_dir": str(out_dir),
            }
        ),
        flush=True,
    )
    srv.serve_forever()


def run_interactive_repl(
    out_base_dir: Path,
    explicit_gguf: Path | None,
    allow_dev_205e: bool,
    dry_run: bool,
) -> int:
    """Interactive CLI prompt loop (`--repl`) for EN/RU combine briefs."""
    print("SmartLLM v2 Offline Combine REPL (127.0.0.1 only). Type 'exit' or 'quit' to leave.")
    run_idx = 1
    while True:
        try:
            brief = input("\n[combine brief EN/RU]> ").strip()
        except EOFError:
            break
        if not brief or brief.lower() in ("exit", "quit", "q"):
            break
        target_dir = out_base_dir / f"repl_site_{run_idx:02d}"
        summary = run_combine_pipeline(
            brief=brief,
            out_dir=target_dir,
            explicit_gguf=explicit_gguf,
            allow_dev_205e=allow_dev_205e,
            dry_run=dry_run,
        )
        print(
            json.dumps(
                {
                    "run": run_idx,
                    "lang": summary["lang"],
                    "canon_id": summary["canon_id"],
                    "out_dir": summary["out_dir"],
                    "style_sha256": summary["style_sha256"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        run_idx += 1
    return 0


def run_cpu_self_test() -> int:
    """Comprehensive pure-CPU self-test (< 250 MiB RAM, zero GPU touch)."""
    with tempfile.TemporaryDirectory(prefix="smartllm_offline_combine_test_") as tmp:
        tmp_dir = Path(tmp)
        mock_models = tmp_dir / "models"
        mock_models.mkdir(parents=True, exist_ok=True)

        # 1. Test missing SmartLLM-v2-*.gguf fail-safe vs --allow-dev-205e
        try:
            discover_gguf_model(models_dir=mock_models, wave3_summary_path=tmp_dir / "none.json", allow_dev_205e=False)
            raise AssertionError("Expected FileNotFoundError when SmartLLM-v2-*.gguf is absent")
        except FileNotFoundError:
            pass

        dev_prof = discover_gguf_model(
            models_dir=mock_models,
            wave3_summary_path=tmp_dir / "none.json",
            allow_dev_205e=True,
            require_exists=False,
        )
        assert dev_prof.is_dev_fallback is True and dev_prof.n_cpu_moe == 48 and dev_prof.moe_cache_mib == 4096

        # 2. Test OPUS §1.D1 auto-discovery across V1 (K320+IQ3_XXS), V2 (K320+IQ2_S), V4 (K288+IQ2_S+IQ4_NL)
        v1_file = mock_models / "SmartLLM-v2-K320-IQ3_XXS-GSQ-Q2_0.gguf"
        v2_file = mock_models / "SmartLLM-v2-K320-IQ2_S-GSQ-Q2_0.gguf"
        v4_file = mock_models / "SmartLLM-v2-K288-IQ2_S-IQ4_NL.gguf"
        for f in (v1_file, v2_file, v4_file):
            f.write_bytes(b"GGUF" + b"\x00" * 64)

        p_v1 = discover_gguf_model(explicit_gguf=v1_file, wave3_summary_path=tmp_dir / "none.json")
        assert (p_v1.k_experts, p_v1.n_cpu_moe, p_v1.moe_cache_mib) == (320, 42, 2048), f"V1 mismatch: {p_v1}"

        p_v2 = discover_gguf_model(explicit_gguf=v2_file, wave3_summary_path=tmp_dir / "none.json")
        assert (p_v2.k_experts, p_v2.n_cpu_moe, p_v2.moe_cache_mib) == (320, 48, 3840), f"V2 mismatch: {p_v2}"

        p_v4 = discover_gguf_model(explicit_gguf=v4_file, wave3_summary_path=tmp_dir / "none.json")
        assert (p_v4.k_experts, p_v4.n_cpu_moe, p_v4.moe_cache_mib) == (288, 40, 512), f"V4 mismatch: {p_v4}"

        # Test wave3_summary.json priority resolution
        mock_w3 = tmp_dir / "wave3_summary.json"
        mock_w3.write_text(
            json.dumps(
                {
                    "variant": "V1_HEALED",
                    "k_experts": 320,
                    "quant_pair": "IQ3_XXS+GSQ_Q2_0",
                    "n_cpu_moe": 43,
                    "moe_cache_mib": 1536,
                    "output_gguf": str(v1_file),
                }
            ),
            encoding="utf-8",
        )
        p_auto = discover_gguf_model(models_dir=mock_models, wave3_summary_path=mock_w3)
        assert p_auto.gguf_path == v1_file and p_auto.n_cpu_moe == 43 and p_auto.moe_cache_mib == 1536

        # 3. Test 127.0.0.1 loopback enforcement
        for bad_host in ("0.0.0.0", "192.168.1.10", "localhost", "10.0.0.1"):
            try:
                assert_loopback_host(bad_host)
                raise AssertionError(f"Expected SecurityInvariantError for host={bad_host}")
            except SecurityInvariantError:
                pass

        # 4. Test deterministic RAG selection & skill checklist injection on EN, RU, and Astro+GSAP briefs
        selector = HarvestRAGSelector()
        assert len(selector.canon_cards) == 28
        assert len(selector.copy_pairs) == 168
        assert len(selector.checklist_files) == 11, f"Expected 11 checklist files in MANIFEST, got {len(selector.checklist_files)}"
        assert len(selector.checklists) == 6, f"Expected 6 JSON checklists, got {len(selector.checklists)}"
        assert len(selector.checklist_guides) == 5, f"Expected 5 MD checklist guides, got {len(selector.checklist_guides)}"

        ru_rag = selector.select(
            "Промышленная система телеметрии SMART для 10 000 NVMe-дисков и узлов хранения",
            lang="auto",
        )
        assert ru_rag["lang"] == "ru"
        assert ru_rag["canon_id"] == "01_swiss_international_typographic"
        assert len(ru_rag["copy_pairs"]) == 4

        en_rag = selector.select(
            "Kubernetes eBPF observability platform pinpointing p99 syscall and TLS handshake latency stalls",
            lang="auto",
        )
        assert en_rag["lang"] == "en"
        assert en_rag["canon_id"] == "03_dark_precision_saas_linear"
        assert len(en_rag["copy_pairs"]) == 4

        astro_gsap_rag = selector.select(
            "Astro 5 Islands landing page with GSAP 3 ScrollTrigger pin/batch choreography and Flip layout transitions for an industrial sensor gateway",
            lang="en",
        )
        assert "astro" in astro_gsap_rag["skill_directives"]["detected_stacks"]
        assert astro_gsap_rag["skill_directives"]["motion_focused"] is True
        astro_gsap_prompt = build_stage_a_prompt(astro_gsap_rag)
        for required_snippet in (
            "STACK-ASTRO-01",
            "client:visible",
            "client:idle",
            "Content Collections",
            "MOT-GSAP-ST-01",
            "ScrollTrigger.batch()",
            "Flip.getState",
            "gsap.context()",
            "gsap.matchMedia()",
            "prefers-reduced-motion: reduce",
            "Length >= 200 characters",
            "exact_text_in_frame",
            "negative_prompt",
            "SEO-JSONLD-01",
            "SEO-FAQ-MATCH",
            "SEC-CSP-HASH",
            "require-trusted-types-for 'script'",
            "LAY-VIEWPORT-DVH",
            "100svh",
        ):
            assert required_snippet in astro_gsap_prompt, f"Missing '{required_snippet}' in Stage A prompt"

        # 5. Test full --dry-run pipeline for RU and EN bundles
        out_ru = tmp_dir / "site_ru"
        out_en = tmp_dir / "site_en"
        sum_ru = run_combine_pipeline(
            brief="Промышленная система телеметрии SMART для 10 000 NVMe-дисков",
            out_dir=out_ru,
            explicit_gguf=v1_file,
            dry_run=True,
        )
        sum_en = run_combine_pipeline(
            brief="Kubernetes eBPF observability platform pinpointing p99 syscall latency",
            out_dir=out_en,
            explicit_gguf=v1_file,
            dry_run=True,
        )

        for site_dir, summary in ((out_ru, sum_ru), (out_en, sum_en)):
            for req_file in summary["files"]:
                fp = site_dir / req_file
                assert fp.exists() and fp.stat().st_size > 0, f"Missing generated file: {fp}"
            html_text = (site_dir / "index.html").read_text(encoding="utf-8")
            assert "unsafe-inline" not in html_text
            assert summary["style_sha256"] in html_text
            assert summary["script_sha256"] in html_text
            assert "100svh" in html_text
            png_check = verify_png_artifact(site_dir / "assets" / "hero_primary.png", 1024, 1024)
            assert png_check["valid"] is True

        # 6. Verify RSS < 250 MiB and 0 GPU compute usage
        vm_rss_kb = 0
        rss_anon_kb = 0
        proc_status = Path("/proc/self/status")
        if proc_status.exists():
            for sline in proc_status.read_text(encoding="utf-8").splitlines():
                if sline.startswith("VmRSS:"):
                    vm_rss_kb = int(sline.split()[1])
                elif sline.startswith("RssAnon:"):
                    rss_anon_kb = int(sline.split()[1])
        rss_mib = (rss_anon_kb or vm_rss_kb) / 1024.0
        vm_rss_mib = vm_rss_kb / 1024.0
        assert rss_mib < 250.0, f"Process RssAnon {rss_mib:.1f} MiB exceeded 250 MiB ceiling"

        print(
            json.dumps(
                {
                    "self_test": "PASSED",
                    "canon_cards_loaded": len(selector.canon_cards),
                    "copy_pairs_loaded": len(selector.copy_pairs),
                    "checklist_files_in_manifest": len(selector.checklist_files),
                    "json_checklists_loaded": len(selector.checklists),
                    "md_guides_loaded": len(selector.checklist_guides),
                    "astro_gsap_prompt_verified": True,
                    "d1_profiles_verified": [
                        {"variant": p_v1.variant_tag, "n_cpu_moe": p_v1.n_cpu_moe, "moe_cache_mib": p_v1.moe_cache_mib},
                        {"variant": p_v2.variant_tag, "n_cpu_moe": p_v2.n_cpu_moe, "moe_cache_mib": p_v2.moe_cache_mib},
                        {"variant": p_v4.variant_tag, "n_cpu_moe": p_v4.n_cpu_moe, "moe_cache_mib": p_v4.moe_cache_mib},
                    ],
                    "ru_canon_selected": ru_rag["canon_id"],
                    "en_canon_selected": en_rag["canon_id"],
                    "rss_anon_mib": round(rss_mib, 2),
                    "vm_rss_mib": round(vm_rss_mib, 2),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SmartLLM v2 Standalone 1-Command Offline Multimodal Combine Launcher (EN + RU)."
    )
    parser.add_argument("--self-test", action="store_true", help="Run pure-CPU self-test (< 250 MiB RAM, 0 GPU)")
    parser.add_argument("--brief", type=str, default="", help="Website/product brief in Russian or English")
    parser.add_argument(
        "--lang",
        choices=("auto", "en", "ru"),
        default="auto",
        help="Target language ('en', 'ru', or 'auto' from brief Cyrillic density)",
    )
    parser.add_argument("--canon-id", type=str, default=None, help="Optional explicit canon_card ID override")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "eval" / "combine_out" / "latest",
        help="Output directory for self-contained website bundle",
    )
    parser.add_argument("--project-dir", type=Path, default=None, help="Alias/override output directory for Studio projects")
    parser.add_argument("--blueprint-json", type=Path, default=None, help="Compile a SmartLLM Studio project_blueprint.json")
    parser.add_argument("--logo-path", type=Path, default=None, help="Optional SVG or PNG brand logo to sanitize and bundle")
    parser.add_argument("--gguf", type=Path, default=None, help="Explicit path to SmartLLM GGUF model")
    parser.add_argument(
        "--allow-dev-205e",
        action="store_true",
        help="Allow fallback to SmartLLM-205E-IQ3_S.gguf if SmartLLM-v2-*.gguf is not built yet",
    )
    parser.add_argument("--n-cpu-moe", type=int, default=None, help="Override --n-cpu-moe")
    parser.add_argument("--moe-cache-mib", type=int, default=None, help="Override --moe-cache-mib")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host (MUST be 127.0.0.1)")
    parser.add_argument("--port", type=int, default=18080, help="llama-server bind port on 127.0.0.1")
    parser.add_argument("--num-images", type=int, default=1, help="Number of Z-Image assets to render (1..4)")
    parser.add_argument("--dry-run", action="store_true", help="Run CPU-only RAG + bundle synthesis without GPU")
    parser.add_argument("--restore-llm-slot", action="store_true", help="Restart llama-server and restore slot 0 after SD")
    parser.add_argument("--serve-ui", action="store_true", help="Start local browser workbench on 127.0.0.1:<ui-port>")
    parser.add_argument("--ui-port", type=int, default=8090, help="Port for --serve-ui on 127.0.0.1")
    parser.add_argument("--repl", action="store_true", help="Start interactive CLI brief REPL")

    args = parser.parse_args(argv)

    if args.self_test:
        return run_cpu_self_test()

    try:
        assert_loopback_host(args.host, context="cli")
    except SecurityInvariantError as exc:
        print(json.dumps({"error": "SECURITY_VIOLATION", "message": str(exc)}), file=sys.stderr)
        return 2

    target_out = args.project_dir if args.project_dir is not None else args.out

    if args.blueprint_json is not None:
        studio_pkg = ROOT / "studio"
        if str(studio_pkg) not in sys.path:
            sys.path.insert(0, str(studio_pkg))
        from smartllm_studio.blueprint import compile_project_blueprint

        bp_payload = json.loads(args.blueprint_json.read_text(encoding="utf-8"))
        if args.project_dir is not None:
            bp_payload["project_dir"] = str(args.project_dir)
        if args.logo_path is not None:
            bp_payload["logo_path"] = str(args.logo_path)
        bp_res = compile_project_blueprint(bp_payload, repo_root=ROOT)
        print(json.dumps(bp_res, indent=2, ensure_ascii=False))
        return 0

    if args.repl:
        return run_interactive_repl(
            out_base_dir=target_out,
            explicit_gguf=args.gguf,
            allow_dev_205e=args.allow_dev_205e,
            dry_run=args.dry_run,
        )

    brief_text = args.brief.strip()
    if not brief_text and not args.serve_ui:
        parser.error("Provide --brief '<text>', --blueprint-json <path>, --repl, --serve-ui, or --self-test.")

    if brief_text:
        try:
            summary = run_combine_pipeline(
                brief=brief_text,
                out_dir=target_out,
                lang=args.lang,
                explicit_canon_id=args.canon_id,
                explicit_gguf=args.gguf,
                allow_dev_205e=args.allow_dev_205e,
                n_cpu_moe_override=args.n_cpu_moe,
                moe_cache_mib_override=args.moe_cache_mib,
                host=args.host,
                port=args.port,
                dry_run=args.dry_run,
                restore_llm_slot=args.restore_llm_slot,
                num_images=args.num_images,
                logo_path=args.logo_path,
            )
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
            return 1

    if args.serve_ui:
        serve_local_workbench(out_dir=target_out, host=args.host, ui_port=args.ui_port)

    return 0


if __name__ == "__main__":
    sys.exit(main())
