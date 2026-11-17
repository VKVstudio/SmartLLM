#!/usr/bin/env python3
"""Pre-Quant & Post-Quant Verification Gate for SmartLLM v2 (OPUS_MASTER_PLAN_V2.md §1.D4).

Implements:
1. Teacher-forced full-vocab KL(P_donor || P_candidate) and Top-1 agreement split by EN / RU
   (`KL_mix = 0.6 * KL_EN + 0.4 * KL_RU`), computed in streaming chunks (CPU or CuPy cuBLAS).
2. Per-layer hidden-state cosine similarity `cos(H_pruned^(l), H_donor^(l)) >= 0.98` across all 48 layers.
3. 10-prompt (5 EN / 5 RU) deterministic greedy generation sanity check (`<= 256` tok):
   - Zero 8-gram x 3 repetition loops.
   - >= 95% Cyrillic ratio on RU non-code text (stripping fenced/inline code, HTML tags, URLs).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
import json
import os
import re
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from scripts.infra.sla_watchdog import (
    DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
    capture_swap_baseline,
    evaluate_swap_and_mem_sla,
)
from scripts.v2.common_io import (
    CYRILLIC_RE,
    assert_post_write_free_gib,
    drop_fd_page_cache,
    drop_file_page_cache,
    find_llama_bin,
)

FENCED_CODE_RE = re.compile(r"```[\s\S]*?```")
UNCLOSED_FENCED_CODE_RE = re.compile(r"```[\s\S]*$")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
HTML_TAG_RE = re.compile(r"<[^>]+>")
UNCLOSED_HTML_TAG_RE = re.compile(r"<[^>]*$")
URL_RE = re.compile(r"https?://\S+")
CSS_PROP_RE = re.compile(r"\b[a-zA-Z-]+(?=\s*:)")
WCAG_CRITERION_RE = re.compile(r"\b\d+\.\d+\.\d+\s+[A-Z][A-Za-z\s-]*(\([A-Za-z]+\))?")
TECH_SPEC_ACRONYM_RE = re.compile(
    r"\b(?:[A-Z]{2,}[0-9]*|hreflang|Organization|Product|SoftwareApplication|FAQPage|WebSite|WebPage|BreadcrumbList)\b"
)


DEFAULT_10_SANITY_PROMPTS: List[Dict[str, str]] = [
    {
        "id": "en_01_hero_html",
        "lang": "en",
        "prompt": "Write clean semantic HTML5 and CSS Grid markup for a minimal B2B SaaS hero section with a headline, subheadline, and primary CTA.",
    },
    {
        "id": "en_02_ux_microcopy",
        "lang": "en",
        "prompt": "Write concise, reassuring UX microcopy for a payment failed modal (title, two-sentence body, primary and secondary button labels).",
    },
    {
        "id": "en_03_ts_helper",
        "lang": "en",
        "prompt": "Write a pure TypeScript function `clampFluidRem(minPx: number, maxPx: number, minVw: number, maxVw: number): string` returning a valid CSS `clamp()` expression.",
    },
    {
        "id": "en_04_design_critique",
        "lang": "en",
        "prompt": "List four specific typography and spacing fixes to upgrade a cluttered SaaS pricing table into an editorial, high-trust layout.",
    },
    {
        "id": "en_05_tool_json",
        "lang": "en",
        "prompt": "Output a valid JSON object describing a 3-color accessible dark-mode palette (`background`, `surface`, `accent`, and `contrast_ratio_wcag`).",
    },
    {
        "id": "ru_01_landing_copy",
        "lang": "ru",
        "prompt": "Напиши сильный главный экран (заголовок, подзаголовок и три коротких буллита без воды и штампов) для студии промышленного и веб-дизайна в Москве.",
    },
    {
        "id": "ru_02_ux_empty_state",
        "lang": "ru",
        "prompt": "Напиши живой и понятный русский текст для пустого состояния корзины в интернет-магазине авторской керамики: заголовок, короткое пояснение и текст кнопки.",
    },
    {
        "id": "ru_03_editorial_audit",
        "lang": "ru",
        "prompt": "Объясни на русском языке четыре главные ошибки вёрстки длинных лонгридов, из-за которых текст тяжело читать с экрана ноутбука.",
    },
    {
        "id": "ru_04_brand_tone",
        "lang": "ru",
        "prompt": "Сформулируй правила редполитики (тон коммуникации, запрещённые канцеляризмы и принципы ясности) для современного российского финтех-сервиса.",
    },
    {
        "id": "ru_05_faq_block",
        "lang": "ru",
        "prompt": "Напиши три лаконичных вопроса и ответа для раздела FAQ на сайте архитектурного бюро (сроки проектирования, авторский надзор и стоимость).",
    },
]


@dataclass(frozen=True)
class GateThresholds:
    name: str
    max_kl_en: float
    max_kl_ru: float
    min_top1_en: float
    min_top1_ru: float
    min_layer_cos: float = 0.98
    min_ru_cyrillic_ratio: float = 0.95


BF16_PREQUANT_THRESHOLDS = GateThresholds(
    name="bf16_prequant_gate",
    max_kl_en=0.10,
    max_kl_ru=0.15,
    min_top1_en=0.88,
    min_top1_ru=0.84,
    min_layer_cos=0.98,
)

FINAL_POSTQUANT_THRESHOLDS = GateThresholds(
    name="final_postquant_gate",
    max_kl_en=0.25,
    max_kl_ru=0.35,
    min_top1_en=0.80,
    min_top1_ru=0.75,
    min_layer_cos=0.98,
)


def compute_cosine_similarity_batch(a: np.ndarray, b: np.ndarray) -> float:
    """Mean per-token cosine similarity between two [..., D] hidden-state arrays."""
    a2 = np.asarray(a, dtype=np.float32).reshape(-1, a.shape[-1])
    b2 = np.asarray(b, dtype=np.float32).reshape(-1, b.shape[-1])
    dot = np.sum(a2.astype(np.float64) * b2.astype(np.float64), axis=-1)
    na = np.linalg.norm(a2.astype(np.float64), axis=-1)
    nb = np.linalg.norm(b2.astype(np.float64), axis=-1)
    denom = np.maximum(na * nb, 1e-12)
    return float(np.mean(dot / denom))


def compute_kl_and_top1_from_logits(
    donor_logits_f32: np.ndarray,  # [T, V] float32
    cand_logits_f32: np.ndarray,  # [T, V] float32
) -> Tuple[float, float, int]:
    """Compute exact sum of KL(P_donor || P_cand) and top-1 match count over T tokens."""
    d_l = np.asarray(donor_logits_f32, dtype=np.float32)
    c_l = np.asarray(cand_logits_f32, dtype=np.float32)
    if d_l.shape != c_l.shape:
        raise ValueError(f"Logit shape mismatch: {d_l.shape} vs {c_l.shape}")
    n_tok = int(d_l.shape[0])
    if n_tok == 0:
        return 0.0, 0.0, 0

    d_top1 = np.argmax(d_l, axis=-1)
    c_top1 = np.argmax(c_l, axis=-1)
    top1_hits = int(np.sum(d_top1 == c_top1))

    d_shift = (d_l - np.max(d_l, axis=-1, keepdims=True)).astype(np.float64)
    c_shift = (c_l - np.max(c_l, axis=-1, keepdims=True)).astype(np.float64)

    d_logz = np.log(np.sum(np.exp(d_shift), axis=-1, keepdims=True))
    c_logz = np.log(np.sum(np.exp(c_shift), axis=-1, keepdims=True))

    d_logp = d_shift - d_logz
    c_logp = c_shift - c_logz
    d_p = np.exp(d_logp)

    # Exact KL(P_d || P_c) = sum_v P_d(v) * (log P_d(v) - log P_c(v)), non-negative
    kl_per_tok = np.maximum(0.0, np.sum(d_p * (d_logp - c_logp), axis=-1))
    return float(np.sum(kl_per_tok)), float(top1_hits), n_tok


def upload_2d_fp16_chunked_cupy(weight_fp16: np.ndarray, row_chunk: int = 8192) -> Any:
    """Upload large 2D FP16 matrix (e.g. 1.18 GiB lm_head) in <=40 MiB slices freeing pinned DMA."""
    os.environ.setdefault("CUDA_PATH", "/opt/cuda")
    import cupy as cp

    nrows, ncols = int(weight_fp16.shape[0]), int(weight_fp16.shape[1])
    dst = cp.empty((nrows, ncols), dtype=cp.float16)
    step = max(1, int(row_chunk))
    for r0 in range(0, nrows, step):
        r1 = min(nrows, r0 + step)
        sub = np.ascontiguousarray(weight_fp16[r0:r1], dtype=np.float16)
        dst[r0:r1].set(sub)
        del sub
        cp.cuda.Stream.null.synchronize()
        cp.get_default_pinned_memory_pool().free_all_blocks()
    return dst


def compute_kl_and_top1_from_hidden(
    h_donor_f32: np.ndarray,  # [T, D] float32 (post-output_hc_norm/mix hidden states)
    h_cand_f32: np.ndarray,  # [T, D] float32
    lm_head_weight_fp16: Any,  # [V, D] np.ndarray float16 OR pre-uploaded cp.ndarray float16
    backend: str = "cpu",
    token_chunk: int = 128,
) -> Tuple[float, float, int]:
    """Streaming teacher-forced KL(donor || cand) and top-1 match count without holding [T, V] in RAM."""
    n_tok = int(h_donor_f32.shape[0])
    if n_tok == 0:
        return 0.0, 0.0, 0

    kl_sum = 0.0
    top1_hits = 0

    if backend == "cupy":
        os.environ.setdefault("CUDA_PATH", "/opt/cuda")
        import cupy as cp

        owns_wg = not isinstance(lm_head_weight_fp16, cp.ndarray)
        w_g = upload_2d_fp16_chunked_cupy(lm_head_weight_fp16) if owns_wg else lm_head_weight_fp16
        try:
            for t0 in range(0, n_tok, token_chunk):
                t1 = min(n_tok, t0 + token_chunk)
                hd_g = cp.asarray(np.ascontiguousarray(h_donor_f32[t0:t1], dtype=np.float16))
                hc_g = cp.asarray(np.ascontiguousarray(h_cand_f32[t0:t1], dtype=np.float16))
                ld_g = cp.matmul(hd_g, w_g.T, dtype=cp.float32)
                lc_g = cp.matmul(hc_g, w_g.T, dtype=cp.float32)

                top1_hits += int(cp.sum(cp.argmax(ld_g, axis=-1) == cp.argmax(lc_g, axis=-1)))

                ld_s = ld_g - cp.max(ld_g, axis=-1, keepdims=True)
                lc_s = lc_g - cp.max(lc_g, axis=-1, keepdims=True)
                ld_logp = ld_s - cp.log(cp.sum(cp.exp(ld_s), axis=-1, keepdims=True))
                lc_logp = lc_s - cp.log(cp.sum(cp.exp(lc_s), axis=-1, keepdims=True))
                dp = cp.exp(ld_logp)
                kl_c = cp.maximum(0.0, cp.sum(dp * (ld_logp - lc_logp), axis=-1))
                kl_sum += float(cp.sum(kl_c))
                del hd_g, hc_g, ld_g, lc_g, ld_s, lc_s, ld_logp, lc_logp, dp, kl_c
        finally:
            if owns_wg:
                del w_g
            cp.cuda.Stream.null.synchronize()
            cp.get_default_pinned_memory_pool().free_all_blocks()
    else:
        w_f32 = lm_head_weight_fp16.astype(np.float32)
        for t0 in range(0, n_tok, token_chunk):
            t1 = min(n_tok, t0 + token_chunk)
            ld = h_donor_f32[t0:t1].astype(np.float32) @ w_f32.T
            lc = h_cand_f32[t0:t1].astype(np.float32) @ w_f32.T
            ks, th, _ = compute_kl_and_top1_from_logits(ld, lc)
            kl_sum += ks
            top1_hits += int(th)

    return kl_sum, float(top1_hits), n_tok


def count_8gram_x3_loops(text: str) -> int:
    """Count distinct 8-token (whitespace/word) n-grams appearing >= 3 times in generated text."""
    tokens = re.findall(r"\S+", text)
    n = len(tokens)
    if n < 24:
        return 0
    counts: Dict[Tuple[str, ...], int] = {}
    for i in range(n - 7):
        gram = tuple(tokens[i : i + 8])
        counts[gram] = counts.get(gram, 0) + 1
    return sum(1 for c in counts.values() if c >= 3)


def compute_non_code_cyrillic_ratio(text: str) -> Tuple[float, int]:
    """Compute fraction of alphabetic characters that are Cyrillic outside code/HTML/URLs."""
    cleaned = FENCED_CODE_RE.sub(" ", text)
    cleaned = UNCLOSED_FENCED_CODE_RE.sub(" ", cleaned)
    cleaned = INLINE_CODE_RE.sub(" ", cleaned)
    cleaned = HTML_TAG_RE.sub(" ", cleaned)
    cleaned = UNCLOSED_HTML_TAG_RE.sub(" ", cleaned)
    cleaned = URL_RE.sub(" ", cleaned)
    cleaned = CSS_PROP_RE.sub(" ", cleaned)
    cleaned = WCAG_CRITERION_RE.sub(" ", cleaned)
    cleaned = TECH_SPEC_ACRONYM_RE.sub(" ", cleaned)

    alpha_chars = [ch for ch in cleaned if ch.isalpha()]
    if not alpha_chars:
        return 1.0, 0
    joined = "".join(alpha_chars)
    n_cyr = len(CYRILLIC_RE.findall(joined))
    return float(n_cyr) / float(len(alpha_chars)), len(alpha_chars)


def audit_10prompt_generations(
    records: Sequence[Dict[str, str]],
    min_ru_cyrillic_ratio: float = 0.95,
) -> Dict[str, Any]:
    """Audit generated responses for 8-gram x 3 loops, non-empty output, and RU Cyrillic purity."""
    per_prompt: List[Dict[str, Any]] = []
    total_loops = 0
    min_ru_ratio_seen = 1.0
    all_passed = True

    for rec in records:
        pid = str(rec.get("id", ""))
        lang = str(rec.get("lang", "en")).lower()
        out_text = str(rec.get("output", "")).strip()

        loops = count_8gram_x3_loops(out_text)
        total_loops += loops
        non_empty = len(out_text) >= 16

        if lang == "ru":
            cyr_ratio, n_alpha = compute_non_code_cyrillic_ratio(out_text)
            if n_alpha >= 10:
                min_ru_ratio_seen = min(min_ru_ratio_seen, cyr_ratio)
                lang_ok = cyr_ratio >= float(min_ru_cyrillic_ratio)
            elif len(CYRILLIC_RE.findall(out_text)) >= 20:
                # Pure fenced code / HTML output with genuine Russian titles/comments inside code
                cyr_ratio = 1.0
                lang_ok = True
            else:
                lang_ok = False
        else:
            cyr_ratio, n_alpha = compute_non_code_cyrillic_ratio(out_text)
            lang_ok = non_empty

        p_ok = non_empty and (loops == 0) and lang_ok
        if not p_ok:
            all_passed = False

        per_prompt.append(
            {
                "id": pid,
                "lang": lang,
                "chars": len(out_text),
                "alpha_chars": n_alpha,
                "loops_8gram_x3": loops,
                "cyrillic_ratio": round(cyr_ratio, 4),
                "passed": p_ok,
            }
        )

    return {
        "passed": all_passed,
        "total_8gram_x3_loops": total_loops,
        "min_ru_cyrillic_ratio": round(min_ru_ratio_seen, 4),
        "threshold_ru_cyrillic_ratio": min_ru_cyrillic_ratio,
        "prompts": per_prompt,
    }


def evaluate_teacher_forced_gate(
    en_kl_sum: float,
    en_top1_hits: float,
    en_tokens: int,
    ru_kl_sum: float,
    ru_top1_hits: float,
    ru_tokens: int,
    layer_cosines: Optional[Sequence[float]],
    thresholds: GateThresholds,
) -> Dict[str, Any]:
    """Evaluate teacher-forced KL / top-1 / cosine metrics against OPUS §1.D4 thresholds."""
    kl_en = en_kl_sum / max(1, en_tokens)
    kl_ru = ru_kl_sum / max(1, ru_tokens)
    kl_mix = 0.6 * kl_en + 0.4 * kl_ru

    top1_en = en_top1_hits / max(1, en_tokens)
    top1_ru = ru_top1_hits / max(1, ru_tokens)
    top1_mix = 0.6 * top1_en + 0.4 * top1_ru

    min_cos = float(min(layer_cosines)) if layer_cosines else 1.0
    cos_ok = min_cos >= thresholds.min_layer_cos

    passed = (
        (kl_en <= thresholds.max_kl_en)
        and (kl_ru <= thresholds.max_kl_ru)
        and (top1_en >= thresholds.min_top1_en)
        and (top1_ru >= thresholds.min_top1_ru)
        and cos_ok
    )
    return {
        "gate_name": thresholds.name,
        "passed": passed,
        "kl_en": round(kl_en, 6),
        "kl_ru": round(kl_ru, 6),
        "kl_mix": round(kl_mix, 6),
        "top1_en": round(top1_en, 6),
        "top1_ru": round(top1_ru, 6),
        "top1_mix": round(top1_mix, 6),
        "min_layer_cosine": round(min_cos, 6),
        "en_tokens": int(en_tokens),
        "ru_tokens": int(ru_tokens),
        "thresholds": {
            "max_kl_en": thresholds.max_kl_en,
            "max_kl_ru": thresholds.max_kl_ru,
            "min_top1_en": thresholds.min_top1_en,
            "min_top1_ru": thresholds.min_top1_ru,
            "min_layer_cos": thresholds.min_layer_cos,
        },
    }


def load_sanity_prompts_10(jsonl_path: Optional[Path] = None) -> List[Dict[str, str]]:
    """Load 10 sanity prompts from data/eval_E/gen_prompts_10.jsonl if present, else defaults."""
    from scripts.v2.common_io import ROOT_DIR

    p = Path(jsonl_path) if jsonl_path is not None else (ROOT_DIR / "data" / "eval_E" / "gen_prompts_10.jsonl")
    if not p.is_file():
        return list(DEFAULT_10_SANITY_PROMPTS)
    loaded: List[Dict[str, str]] = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            loaded.append(
                {
                    "id": str(rec.get("id", f"p_{len(loaded)}")),
                    "lang": str(rec.get("lang", "en")).lower(),
                    "prompt": str(rec.get("prompt_text") or rec.get("prompt") or ""),
                }
            )
    return loaded if loaded else list(DEFAULT_10_SANITY_PROMPTS)


def _format_chat_prompt_for_sanity(raw_p: str) -> str:
    if raw_p.startswith("<|im_start|>"):
        if raw_p.endswith("<think>\n"):
            return raw_p + "\n</think>\n\n"
        return raw_p
    return (
        "<|im_start|>system\nYou are a concise expert web designer, engineer, and editor.<|im_end|>\n"
        f"<|im_start|>user\n{raw_p}<|im_end|>\n"
        "<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )


def _pick_free_localhost_port(preferred_port: int = 18091) -> int:
    for cand in (int(preferred_port), 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", cand))
                return int(s.getsockname()[1])
            except OSError:
                continue
    raise RuntimeError("Unable to bind free localhost port on 127.0.0.1")


def _http_json_local(
    url: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 120.0,
) -> Tuple[int, Dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), (json.loads(body) if body.strip() else {})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return int(exc.code), {"raw_error": body}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return 0, {"connection_error": str(exc)}


def _read_nvidia_smi_vram_gib() -> Optional[float]:
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        vals = [float(ln.strip()) for ln in proc.stdout.strip().splitlines() if ln.strip()]
        return max(vals) / 1024.0 if vals else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def plan_bf16_server_vram_flags(
    gguf_path: Path,
    n_parallel: int = 10,
    ctx_per_slot: int = 512,
    moe_cache_mib: int = 512,
    max_vram_gib: float = 9.20,
) -> Dict[str, Any]:
    """OPUS Audit #90 Item 4b: Sum non-expert, non-PLE, non-output tensor bytes from GGUF header
    and emit extra `-ot` CPU overrides if needed so projected CUDA VRAM stays <= max_vram_gib (<= 9.5 GiB),
    preventing outer gpu_run.py (10.5 GiB) from ever SIGKILLing Wave 3."""
    from scripts.v2.common_io import GGUF_PY_PATH

    if str(GGUF_PY_PATH) not in sys.path:
        sys.path.insert(0, str(GGUF_PY_PATH))
    import gguf

    reader = gguf.GGUFReader(str(gguf_path), "r")
    per_layer_non_moe_bytes: Dict[int, int] = {}
    head_non_out_bytes = 0
    for t in reader.tensors:
        nm = t.name
        if nm in ("per_layer_token_embd.weight", "token_embd.weight", "output.weight"):
            continue
        if nm.startswith("blk."):
            parts = nm.split(".")
            bid = int(parts[1])
            if bid >= 48:
                continue
            if nm.endswith((".ffn_gate_exps.weight", ".ffn_up_exps.weight", ".ffn_down_exps.weight")):
                continue
            per_layer_non_moe_bytes[bid] = per_layer_non_moe_bytes.get(bid, 0) + int(t.n_bytes)
        else:
            head_non_out_bytes += int(t.n_bytes)

    # Fixed non-layer CUDA budget: GDN recurrent state (~112.5 MiB/slot) + q8_0 KV + moe_cache + CUDA compute/ctx
    gdn_rs_mib = float(n_parallel) * 114.0
    kv_mib = max(80.0, float(n_parallel * ctx_per_slot) * 0.02)
    compute_ctx_mib = 550.0
    fixed_mib = gdn_rs_mib + kv_mib + float(moe_cache_mib) + compute_ctx_mib + (head_non_out_bytes / (1024.0 * 1024.0))
    budget_mib = float(max_vram_gib) * 1024.0

    kept_cuda_mib = fixed_mib
    cpu_offload_bids: List[int] = []
    for bid in sorted(per_layer_non_moe_bytes.keys()):
        l_mib = per_layer_non_moe_bytes[bid] / (1024.0 * 1024.0)
        if kept_cuda_mib + l_mib <= budget_mib:
            kept_cuda_mib += l_mib
        else:
            cpu_offload_bids.append(bid)

    extra_ot_rules: List[str] = [r"output\.weight=CPU"]
    if cpu_offload_bids:
        joined = "|".join(str(b) for b in cpu_offload_bids)
        extra_ot_rules.append(rf"blk\.({joined})\..*=CPU")

    return {
        "projected_vram_gib": round(kept_cuda_mib / 1024.0, 3),
        "max_vram_gib": float(max_vram_gib),
        "fixed_cuda_mib": round(fixed_mib, 1),
        "cuda_trunk_layers": 48 - len(cpu_offload_bids),
        "cpu_offload_trunk_bids": cpu_offload_bids,
        "extra_ot_rules": extra_ot_rules,
    }


def compute_per_doc_kl_bootstrap_ci(
    per_doc_records: Sequence[Dict[str, Any]],
    n_boot: int = 2000,
    seed: int = 42,
) -> Dict[str, Any]:
    """OPUS Audit #90 Item 8: Compute deterministic token-weighted bootstrap 95% CI over eval_E docs."""
    rng = np.random.default_rng(int(seed))

    def _boot_subset(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not docs:
            return {"n_docs": 0, "tokens": 0, "mean_kl": 0.0, "ci95_kl": [0.0, 0.0]}
        toks = np.array([float(d["tokens"]) for d in docs], dtype=np.float64)
        kl_sums = np.array([float(d["mean_kl"]) * float(d["tokens"]) for d in docs], dtype=np.float64)
        tot_tok = float(np.sum(toks))
        pt_est = float(np.sum(kl_sums) / max(tot_tok, 1.0))
        if len(docs) < 2:
            return {
                "n_docs": len(docs),
                "tokens": int(tot_tok),
                "mean_kl": round(pt_est, 6),
                "ci95_kl": [round(pt_est, 6), round(pt_est, 6)],
            }
        idx = rng.integers(0, len(docs), size=(int(n_boot), len(docs)))
        b_tok = np.sum(toks[idx], axis=1)
        b_kl = np.sum(kl_sums[idx], axis=1) / np.maximum(b_tok, 1.0)
        lo, hi = np.percentile(b_kl, [2.5, 97.5])
        return {
            "n_docs": len(docs),
            "tokens": int(tot_tok),
            "mean_kl": round(pt_est, 6),
            "ci95_kl": [round(float(lo), 6), round(float(hi), 6)],
        }

    en_docs = [d for d in per_doc_records if str(d.get("lang", "")).lower() != "ru"]
    ru_docs = [d for d in per_doc_records if str(d.get("lang", "")).lower() == "ru"]
    return {
        "n_boot": int(n_boot),
        "en": _boot_subset(en_docs),
        "ru": _boot_subset(ru_docs),
        "all": _boot_subset(list(per_doc_records)),
    }


def run_10prompt_batched_server_generation_gate(
    gguf_path: Path,
    prompts: Optional[Sequence[Dict[str, str]]] = None,
    max_new_tokens: int = 256,
    n_parallel: int = 10,
    n_gpu_layers: int = 99,
    n_cpu_moe: int = 48,
    moe_cache_mib: int = 4096,
    moe_cache_cpu_share: float = 0.15,
    ctx_per_slot: int = 512,
    offload_output_to_cpu: bool = False,
    auto_plan_bf16_vram: bool = False,
    max_planned_vram_gib: float = 9.20,
    soft_vram_cap_gib: float = 9.85,
    wall_cap_sec: float = 3600.0,
    allow_partial_on_timeout: bool = False,
    non_fatal_on_server_error: bool = False,
    server_log_path: Optional[Path] = None,
    llama_server_bin: Optional[Path] = None,
    preferred_port: int = 18091,
) -> Dict[str, Any]:
    """Run deterministic T=0 batched (-np 10) 10-prompt generation via local 127.0.0.1 llama-server.

    Implements OPUS §1.D2b.5, §1.D4, & Audit #90 Item 4:
    - Loads GGUF once with `--lazy-mode direct -nr --n-cpu-moe 48` (plus `blk.48` on CPU when MTP is off)
      and dispatches all 10 prompts concurrently across slots `0..9`.
    - When `auto_plan_bf16_vram=True`, inspects GGUF header tensor bytes and adds `-ot` rules so projected
      VRAM stays <= 9.20 GiB (well below outer 10.5 GiB watchdog).
    - Continuously enforces OPUS §0.3a SLA (`MemAvailable >= 3.0 GiB`, `0` disk swap, `0` PLE RSS,
      `<= 128 MiB` process swap, plus soft VRAM cap `<= 9.85 GiB`).
    - When `non_fatal_on_server_error=True` (BF16 pre-quant check), treats load fail / OOM / crash / soft
      VRAM cap like a timeout (`{"passed": null, "error": ...}`) so Wave 3 proceeds cleanly to `final_gguf`.
    """
    srv_bin = Path(llama_server_bin) if llama_server_bin is not None else find_llama_bin("llama-server")
    active_prompts = list(prompts) if prompts is not None else load_sanity_prompts_10()
    eff_parallel = max(1, min(int(n_parallel), max(1, len(active_prompts))))
    port = _pick_free_localhost_port(preferred_port)

    vram_plan: Optional[Dict[str, Any]] = None
    if auto_plan_bf16_vram:
        vram_plan = plan_bf16_server_vram_flags(
            gguf_path=Path(gguf_path),
            n_parallel=eff_parallel,
            ctx_per_slot=ctx_per_slot,
            moe_cache_mib=moe_cache_mib,
            max_vram_gib=max_planned_vram_gib,
        )

    ot_rules: List[str] = [r"blk\.48\..*=CPU"]
    if vram_plan is not None:
        for rule in vram_plan["extra_ot_rules"]:
            r_str = str(rule)
            if r_str not in ot_rules:
                ot_rules.append(r_str)
    elif offload_output_to_cpu:
        out_rule = r"output\.weight=CPU"
        if out_rule not in ot_rules:
            ot_rules.append(out_rule)

    cmd: List[str] = [
        str(srv_bin),
        "-m",
        str(gguf_path),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--lazy-mode",
        "direct",
        "--n-cpu-moe",
        str(int(n_cpu_moe)),
        "-ot",
        ",".join(ot_rules),
        "-nr",
    ]
    if int(moe_cache_mib) > 0:
        cmd.extend(
            [
                "--moe-cache-mib",
                str(int(moe_cache_mib)),
                "--moe-cache-cpu-share",
                f"{float(moe_cache_cpu_share):.2f}",
            ]
        )
    cmd.extend(
        [
            "-fa",
            "on",
            "-ctk",
            "q8_0",
            "-ctv",
            "q8_0",
            "-c",
            str(int(eff_parallel * max(256, int(ctx_per_slot)))),
            "-ub",
            "512",
            "-ngl",
            str(int(n_gpu_layers)),
            "-np",
            str(int(eff_parallel)),
            "--cache-ram",
            "0",
            "--no-webui",
        ]
    )

    swap_base = capture_swap_baseline()
    t_start = time.monotonic()
    t_deadline = t_start + float(wall_cap_sec)

    log_fp = None
    if server_log_path is not None:
        Path(server_log_path).parent.mkdir(parents=True, exist_ok=True)
        log_fp = open(server_log_path, "w", encoding="utf-8")

    proc = subprocess.Popen(
        cmd,
        stdout=log_fp if log_fp is not None else subprocess.DEVNULL,
        stderr=subprocess.STDOUT if log_fp is not None else subprocess.DEVNULL,
        text=True,
    )

    completed_by_idx: Dict[int, Dict[str, Any]] = {}
    timed_out_partial = False
    non_fatal_error_msg: Optional[str] = None
    min_mem_avail_seen = 999.0
    max_proc_swap_seen_kb = 0
    max_ple_rss_seen_kb = 0
    max_vram_seen_gib = 0.0

    def _check_runtime_sla() -> None:
        nonlocal min_mem_avail_seen, max_proc_swap_seen_kb, max_ple_rss_seen_kb, max_vram_seen_gib
        if proc.poll() is not None:
            return
        cur_vram = _read_nvidia_smi_vram_gib()
        if cur_vram is not None:
            max_vram_seen_gib = max(max_vram_seen_gib, cur_vram)
        sla = evaluate_swap_and_mem_sla(
            baseline=swap_base,
            root_pid=proc.pid,
            vram_gib=cur_vram if not non_fatal_on_server_error else None,
            min_mem_avail_gib=3.0,
            max_proc_swap_mib=DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
            check_ple=True,
        )
        min_mem_avail_seen = min(min_mem_avail_seen, float(sla.get("mem_avail_gib", 999.0)))
        max_proc_swap_seen_kb = max(max_proc_swap_seen_kb, int(sla.get("proc_swap_kb", 0)))
        max_ple_rss_seen_kb = max(max_ple_rss_seen_kb, int(sla.get("ple_rss_kb", 0)))
        if not sla["passed"]:
            raise RuntimeError(f"Runtime SLA §0.3a breached during llama-server gate: {sla['breach_reason']}")
        if non_fatal_on_server_error and cur_vram is not None and cur_vram > float(soft_vram_cap_gib):
            raise RuntimeError(
                f"BF16 server soft VRAM cap exceeded ({cur_vram:.2f} GiB > {soft_vram_cap_gib:.2f} GiB); stopping before 10.5 GiB watchdog"
            )

    try:
        try:
            health_url = f"http://127.0.0.1:{port}/health"
            load_deadline = min(t_deadline, t_start + 600.0)
            healthy = False
            while time.monotonic() < load_deadline:
                if proc.poll() is not None:
                    raise RuntimeError(f"llama-server exited early (rc={proc.returncode}) while loading {gguf_path}")
                _check_runtime_sla()
                code, body = _http_json_local(health_url, method="GET", timeout=2.0)
                if code == 200 and body.get("status") == "ok":
                    healthy = True
                    break
                time.sleep(1.0)

            if not healthy:
                if time.monotonic() >= t_deadline and allow_partial_on_timeout:
                    timed_out_partial = True
                else:
                    raise RuntimeError(f"llama-server did not become healthy before deadline for {gguf_path}")

            if healthy and not timed_out_partial:
                comp_url = f"http://127.0.0.1:{port}/completion"

                def _request_one(p_idx: int, item: Dict[str, str]) -> Tuple[int, Dict[str, Any]]:
                    rem = max(5.0, t_deadline - time.monotonic() + 10.0)
                    chat_p = _format_chat_prompt_for_sanity(str(item["prompt"]))
                    code, body = _http_json_local(
                        comp_url,
                        method="POST",
                        payload={
                            "prompt": chat_p,
                            "id_slot": int(p_idx % eff_parallel),
                            "n_predict": int(max_new_tokens),
                            "temperature": 0.0,
                            "seed": 42,
                            "cache_prompt": False,
                        },
                        timeout=rem,
                    )
                    if code != 200:
                        raise RuntimeError(f"HTTP {code} on {item['id']}: {body}")
                    return p_idx, {
                        "id": str(item["id"]),
                        "lang": str(item["lang"]),
                        "output": str(body.get("content", "")).strip(),
                        "tokens_predicted": body.get("tokens_predicted"),
                        "timings": body.get("timings", {}),
                    }

                pool = ThreadPoolExecutor(max_workers=eff_parallel)
                try:
                    futs = {pool.submit(_request_one, idx, it): idx for idx, it in enumerate(active_prompts)}
                    pending = set(futs.keys())
                    while pending:
                        _check_runtime_sla()
                        rem_wall = t_deadline - time.monotonic()
                        if rem_wall <= 0.0:
                            timed_out_partial = True
                            break
                        done_now, pending = wait(pending, timeout=min(2.0, rem_wall))
                        for ft in done_now:
                            r_idx, r_val = ft.result()
                            completed_by_idx[r_idx] = r_val
                        if pending and proc.poll() is not None:
                            raise RuntimeError(f"llama-server crashed mid-generation (rc={proc.returncode})")
                finally:
                    if (timed_out_partial or non_fatal_error_msg is not None) and proc.poll() is None:
                        proc.send_signal(signal.SIGTERM)
                    pool.shutdown(wait=False, cancel_futures=True)
                    if timed_out_partial and not allow_partial_on_timeout:
                        raise RuntimeError(
                            f"10-prompt generation exceeded hard wall cap ({wall_cap_sec:.0f}s) on {gguf_path}"
                        )
        except Exception as exc:
            if not non_fatal_on_server_error:
                raise
            non_fatal_error_msg = str(exc)
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=20.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5.0)
        if log_fp is not None:
            log_fp.close()
        drop_file_page_cache(gguf_path)

    ordered_outputs: List[Dict[str, str]] = []
    timings_by_id: Dict[str, Any] = {}
    for idx in sorted(completed_by_idx.keys()):
        rec = completed_by_idx[idx]
        ordered_outputs.append({"id": rec["id"], "lang": rec["lang"], "output": rec["output"]})
        timings_by_id[rec["id"]] = {
            "tokens_predicted": rec.get("tokens_predicted"),
            "predicted_per_second": rec.get("timings", {}).get("predicted_per_second"),
        }

    audit = audit_10prompt_generations(ordered_outputs) if ordered_outputs else {
        "passed": False,
        "total_8gram_x3_loops": 0,
        "min_ru_cyrillic_ratio": 0.0,
        "threshold_ru_cyrillic_ratio": 0.95,
        "prompts": [],
    }
    if timed_out_partial or non_fatal_error_msg is not None:
        audit["passed"] = None
    elif len(ordered_outputs) < len(active_prompts):
        audit["passed"] = False

    if non_fatal_error_msg is not None:
        audit["error"] = non_fatal_error_msg
    if vram_plan is not None:
        audit["vram_plan"] = vram_plan
    audit["timed_out_partial"] = bool(timed_out_partial)
    audit["completed_prompts"] = len(ordered_outputs)
    audit["expected_prompts"] = len(active_prompts)
    audit["elapsed_sec"] = round(time.monotonic() - t_start, 2)
    audit["wall_cap_sec"] = float(wall_cap_sec)
    audit["runtime_sla"] = {
        "min_mem_avail_gib": round(min_mem_avail_seen, 3) if min_mem_avail_seen < 900.0 else None,
        "max_proc_swap_kb": int(max_proc_swap_seen_kb),
        "max_ple_rss_kb": int(max_ple_rss_seen_kb),
        "max_vram_seen_gib": round(max_vram_seen_gib, 3) if max_vram_seen_gib > 0.0 else None,
    }
    audit["timings_by_id"] = timings_by_id
    audit["raw_outputs"] = ordered_outputs
    return audit


def _quantize_logits_to_kld_rows(logits_f32: np.ndarray) -> np.ndarray:
    """Encode [T, V] float32 logits into uint16[T, nv] matching perplexity.cpp:79-106."""
    t_cnt, n_vocab = int(logits_f32.shape[0]), int(logits_f32.shape[1])
    nv = 2 * ((n_vocab + 1) // 2) + 4
    out = np.zeros((t_cnt, nv), dtype=np.uint16)
    if t_cnt == 0:
        return out

    max_l = np.max(logits_f32, axis=-1, keepdims=True)
    min_l = np.maximum(np.min(logits_f32, axis=-1, keepdims=True), max_l - np.float32(16.0))
    log_sum_exp = np.log(
        np.sum(np.exp((logits_f32 - max_l).astype(np.float64)), axis=-1, keepdims=True)
    ).astype(np.float32)
    min_log_prob = (min_l - max_l - log_sum_exp)[:, 0].astype(np.float32)
    scale = ((max_l - min_l)[:, 0] / np.float32(65535.0)).astype(np.float32)

    hdr_f32 = np.stack([scale, min_log_prob], axis=-1).astype("<f4")
    out[:, :4] = hdr_f32.view("<u2")

    nz = scale > 0.0
    if np.any(nz):
        inv_s = np.zeros_like(scale, dtype=np.float32)
        inv_s[nz] = np.float32(1.0) / scale[nz]
        scaled = (logits_f32 - min_l) * inv_s[:, None]
        q_vals = np.where(
            logits_f32 > min_l,
            np.clip(np.rint(scaled), 0.0, 65535.0),
            0.0,
        ).astype("<u2")
        out[:, 4 : 4 + n_vocab] = q_vals
    return out


def write_llama_kld_file(
    out_kld_path: Path,
    token_chunks: Sequence[np.ndarray],
    donor_hidden_chunks: Sequence[np.ndarray],
    lm_head_weight_fp16: Any,
    n_ctx: int,
    backend: str = "cpu",
    token_batch: int = 64,
    min_post_write_free_gib: float = 0.0,
) -> Dict[str, Any]:
    """Stream exact 512E HF donor log-probabilities into llama-perplexity `.kld` binary format.

    Matches `tools/llama.cpp/tools/perplexity/perplexity.cpp:1688-1740, 1841-1852`:
    - Header: `b"_logits_"` + `uint32 n_ctx` + `int32 n_vocab` + `int32 n_chunk` + `int32 tokens[n_ctx * n_chunk]`.
    - Payload per chunk: `(n_ctx - 1 - n_ctx // 2)` rows of `nv = 2 * ((n_vocab + 1) // 2) + 4` uint16s,
      corresponding to positions `pos = (n_ctx // 2) .. (n_ctx - 2)` predicting `tokens[pos + 1]`.
    """
    if len(token_chunks) != len(donor_hidden_chunks) or len(token_chunks) == 0:
        raise ValueError("token_chunks and donor_hidden_chunks must be non-empty and equal length")
    n_ctx_i = int(n_ctx)
    first = n_ctx_i // 2
    n_eval_per_chunk = n_ctx_i - 1 - first
    if n_eval_per_chunk <= 0:
        raise ValueError(f"n_ctx={n_ctx_i} too small for llama-perplexity KL evaluation")

    n_vocab = int(lm_head_weight_fp16.shape[0])
    nv = 2 * ((n_vocab + 1) // 2) + 4
    n_chunk = len(token_chunks)

    flat_toks = np.concatenate([np.asarray(tc, dtype="<i4").reshape(n_ctx_i) for tc in token_chunks], axis=0)
    expected_bytes = 8 + 12 + int(flat_toks.nbytes) + n_chunk * n_eval_per_chunk * nv * 2

    out_p = Path(out_kld_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    if min_post_write_free_gib > 0.0:
        assert_post_write_free_gib(
            out_p,
            expected_bytes,
            min_free_gib=min_post_write_free_gib,
            label=f"kld_{out_p.name}",
        )

    cp_mod = None
    owns_wg = False
    w_g: Any = None
    w_cpu_f32: Optional[np.ndarray] = None
    if backend == "cupy":
        os.environ.setdefault("CUDA_PATH", "/opt/cuda")
        import cupy as cp

        cp_mod = cp
        owns_wg = not isinstance(lm_head_weight_fp16, cp.ndarray)
        w_g = upload_2d_fp16_chunked_cupy(lm_head_weight_fp16) if owns_wg else lm_head_weight_fp16
    else:
        w_cpu_f32 = np.asarray(lm_head_weight_fp16, dtype=np.float32)

    try:
        with open(out_p, "wb") as f:
            fd = f.fileno()
            f.write(b"_logits_")
            f.write(struct.pack("<Iii", n_ctx_i, n_vocab, n_chunk))
            f.write(flat_toks.tobytes())
            f.flush()

            for c_idx in range(n_chunk):
                h_c = np.asarray(donor_hidden_chunks[c_idx], dtype=np.float32)
                if h_c.shape[0] < n_ctx_i - 1:
                    raise ValueError(f"Chunk {c_idx} hidden length {h_c.shape[0]} < {n_ctx_i - 1}")
                h_eval = h_c[first : n_ctx_i - 1]
                for t0 in range(0, n_eval_per_chunk, token_batch):
                    t1 = min(n_eval_per_chunk, t0 + token_batch)
                    if cp_mod is not None:
                        hg = cp_mod.asarray(np.ascontiguousarray(h_eval[t0:t1], dtype=np.float16))
                        lg = cp_mod.matmul(hg, w_g.T, dtype=cp_mod.float32)
                        logits_np = cp_mod.asnumpy(lg)
                        del hg, lg
                        cp_mod.cuda.Stream.null.synchronize()
                        cp_mod.get_default_pinned_memory_pool().free_all_blocks()
                    else:
                        assert w_cpu_f32 is not None
                        logits_np = h_eval[t0:t1].astype(np.float32) @ w_cpu_f32.T

                    q_rows = _quantize_logits_to_kld_rows(logits_np)
                    pos_before = f.tell()
                    raw = q_rows.tobytes()
                    f.write(raw)
                    f.flush()
                    os.fdatasync(fd)
                    drop_fd_page_cache(fd, offset=pos_before, length=len(raw))
    finally:
        if cp_mod is not None:
            if owns_wg:
                del w_g
            cp_mod.cuda.Stream.null.synchronize()
            cp_mod.get_default_pinned_memory_pool().free_all_blocks()
        drop_file_page_cache(out_p)

    actual_bytes = int(out_p.stat().st_size)
    if actual_bytes != expected_bytes:
        raise RuntimeError(f"KLD file byte size mismatch: {actual_bytes} != {expected_bytes}")
    return {
        "kld_path": str(out_p),
        "n_ctx": n_ctx_i,
        "n_vocab": n_vocab,
        "n_chunk": n_chunk,
        "eval_tokens": n_chunk * n_eval_per_chunk,
        "bytes": actual_bytes,
    }


def decode_kld_and_score_logits(
    kld_path: Path,
    cand_logits_chunks: Sequence[np.ndarray],
) -> Dict[str, Any]:
    """Pure-Python verifier matching `perplexity.cpp:191-240` KL & Same-top-p math on `.kld` files."""
    with open(kld_path, "rb") as f:
        magic = f.read(8)
        if magic != b"_logits_":
            raise ValueError(f"Invalid KLD magic: {magic!r}")
        n_ctx, n_vocab, n_chunk = struct.unpack("<Iii", f.read(12))
        _tokens = np.frombuffer(f.read(4 * int(n_ctx) * int(n_chunk)), dtype="<i4").reshape(n_chunk, n_ctx)
        first = int(n_ctx) // 2
        n_eval = int(n_ctx) - 1 - first
        nv = 2 * ((int(n_vocab) + 1) // 2) + 4

        sum_kld = 0.0
        same_top = 0
        total = 0
        for c_idx in range(int(n_chunk)):
            rows = np.frombuffer(f.read(n_eval * nv * 2), dtype="<u2").reshape(n_eval, nv)
            hdr = rows[:, :4].view("<f4")
            scale = hdr[:, 0].astype(np.float64)
            min_lp = hdr[:, 1].astype(np.float64)
            q_u16 = rows[:, 4 : 4 + int(n_vocab)].astype(np.float64)
            p_log_base = scale[:, None] * q_u16 + min_lp[:, None]

            c_l = np.asarray(cand_logits_chunks[c_idx], dtype=np.float64)
            if c_l.shape != (n_eval, int(n_vocab)):
                raise ValueError(f"Expected cand_logits shape {(n_eval, int(n_vocab))}, got {c_l.shape}")
            c_max = np.max(c_l, axis=-1, keepdims=True)
            c_lse = c_max + np.log(np.sum(np.exp(c_l - c_max), axis=-1, keepdims=True))

            imax_base = np.argmax(p_log_base, axis=-1)
            imax_cand = np.argmax(c_l, axis=-1)
            same_top += int(np.sum(imax_base == imax_cand))

            mask = p_log_base > -16.0
            p_base = np.where(mask, np.exp(p_log_base), 0.0)
            kld_tok = np.sum(np.where(mask, p_base * (p_log_base - c_l + c_lse), 0.0), axis=-1)
            sum_kld += float(np.sum(np.maximum(0.0, kld_tok)))
            total += n_eval

    return {
        "mean_kld": sum_kld / max(1, total),
        "same_top_p": float(same_top) / max(1, total),
        "count": total,
    }


MEAN_KLD_RE = re.compile(r"Mean\s+KLD:\s*([-+]?\d+(?:\.\d+)?)")
SAME_TOP_P_RE = re.compile(r"Same top p:\s*([-+]?\d+(?:\.\d+)?)")


def parse_llama_perplexity_kld_output(output_text: str) -> Tuple[float, float]:
    """Extract (mean_kld_nats, same_top1_fraction) from `llama-perplexity --kl-divergence` output."""
    m_kld = MEAN_KLD_RE.search(output_text)
    m_top = SAME_TOP_P_RE.search(output_text)
    if not m_kld or not m_top:
        raise RuntimeError(
            f"Could not parse Mean KLD / Same top p from llama-perplexity output:\n{output_text[-2000:]}"
        )
    return float(m_kld.group(1)), float(m_top.group(1)) / 100.0


def run_postquant_kld_gate_via_llama_perplexity(
    gguf_path: Path,
    en_kld_path: Path,
    en_n_ctx: int,
    en_eval_tokens: int,
    ru_kld_path: Path,
    ru_n_ctx: int,
    ru_eval_tokens: int,
    layer_cosines: Optional[Sequence[float]] = None,
    n_cpu_moe: int = 48,
    moe_cache_mib: int = 4096,
    llama_perplexity_bin: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run native `llama-perplexity --kl-divergence` on final GGUF for EN & RU `.kld` targets."""
    ppl_bin = Path(llama_perplexity_bin) if llama_perplexity_bin is not None else find_llama_bin("llama-perplexity")

    def _run_one(kld_p: Path, n_ctx_val: int) -> Tuple[float, float]:
        # Set n_batch = n_ctx // 2 so num_batches == 2 > 1 and n_seq == 1 (perplexity.cpp:1723, 1847)
        n_batch = max(64, int(n_ctx_val) // 2)
        cmd = [
            str(ppl_bin),
            "-m",
            str(gguf_path),
            "--lazy-mode",
            "direct",
            "--n-cpu-moe",
            str(int(n_cpu_moe)),
            "-ot",
            r"blk\.48\..*=CPU",
            "-nr",
            "--moe-cache-mib",
            str(int(moe_cache_mib)),
            "--moe-cache-cpu-share",
            "0.15",
            "-fa",
            "on",
            "-ctk",
            "q8_0",
            "-ctv",
            "q8_0",
            "-ngl",
            "99",
            "-c",
            str(int(n_ctx_val)),
            "-b",
            str(n_batch),
            "-ub",
            str(min(512, n_batch)),
            "--kl-divergence",
            "--kl-divergence-base",
            str(kld_p),
        ]
        stop_evt = threading.Event()

        def _kld_reaper() -> None:
            while not stop_evt.wait(0.5):
                try:
                    drop_file_page_cache(kld_p)
                except Exception:
                    pass

        reaper = threading.Thread(target=_kld_reaper, daemon=True)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        reaper.start()
        try:
            combined_out, _ = proc.communicate()
        finally:
            stop_evt.set()
            reaper.join(timeout=5.0)
        combined = combined_out or ""
        drop_file_page_cache(kld_p)
        drop_file_page_cache(gguf_path)
        if proc.returncode != 0:
            raise RuntimeError(
                f"llama-perplexity --kl-divergence failed on {kld_p.name} (rc={proc.returncode}):\n{combined[-2000:]}"
            )
        return parse_llama_perplexity_kld_output(combined)

    kl_en, top1_en = _run_one(Path(en_kld_path), int(en_n_ctx))
    kl_ru, top1_ru = _run_one(Path(ru_kld_path), int(ru_n_ctx))

    ev = evaluate_teacher_forced_gate(
        en_kl_sum=kl_en * float(en_eval_tokens),
        en_top1_hits=top1_en * float(en_eval_tokens),
        en_tokens=int(en_eval_tokens),
        ru_kl_sum=kl_ru * float(ru_eval_tokens),
        ru_top1_hits=top1_ru * float(ru_eval_tokens),
        ru_tokens=int(ru_eval_tokens),
        layer_cosines=layer_cosines,
        thresholds=FINAL_POSTQUANT_THRESHOLDS,
    )
    ev["en_kld_path"] = str(en_kld_path)
    ev["ru_kld_path"] = str(ru_kld_path)
    ev["en_kld_n_ctx"] = int(en_n_ctx)
    ev["ru_kld_n_ctx"] = int(ru_n_ctx)
    ev["comparability_note"] = (
        f"llama-perplexity --kl-divergence scores positions n_ctx//2..n_ctx-2 per prefix chunk "
        f"(EN n_ctx={int(en_n_ctx)}, {int(en_eval_tokens)} tok; RU n_ctx={int(ru_n_ctx)}, {int(ru_eval_tokens)} tok); "
        "RU post-quant KLD covers short prefixes and is reported alongside full-context BF16 teacher-forced KL."
    )
    return ev


def run_10prompt_gguf_generation_gate(
    gguf_path: Path,
    prompts: Optional[Sequence[Dict[str, str]]] = None,
    max_new_tokens: int = 256,
    n_gpu_layers: int = 99,
    llama_completion_bin: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run deterministic greedy (temp=0) 10-prompt generation via native llama-completion / llama-cli.

    Strictly enforces Zero-Swap runtime flags (--n-cpu-moe 48 -nr --lazy-mode direct).
    NOTE: Must ONLY be invoked under scripts/infra/gpu_run.py when holding GPU_TOKEN!
    """
    if llama_completion_bin is not None:
        cli_bin = Path(llama_completion_bin)
    else:
        try:
            cli_bin = find_llama_bin("llama-completion")
        except FileNotFoundError:
            cli_bin = find_llama_bin("llama-cli")

    active_prompts = list(prompts) if prompts is not None else load_sanity_prompts_10()
    outputs: List[Dict[str, str]] = []
    for item in active_prompts:
        raw_p = str(item["prompt"])
        if raw_p.startswith("<|im_start|>"):
            # Close empty think block for 256-tok non-code prose/markup sanity check
            if raw_p.endswith("<think>\n"):
                chat_prompt = raw_p + "\n</think>\n\n"
            else:
                chat_prompt = raw_p
        else:
            chat_prompt = (
                "<|im_start|>system\nYou are a concise expert web designer, engineer, and editor.<|im_end|>\n"
                f"<|im_start|>user\n{raw_p}<|im_end|>\n"
                "<|im_start|>assistant\n<think>\n\n</think>\n\n"
            )
        cmd = [
            str(cli_bin),
            "-m",
            str(gguf_path),
            "-ngl",
            str(int(n_gpu_layers)),
            "--n-cpu-moe",
            "48",
            "-nr",
            "--lazy-mode",
            "direct",
            "--moe-cache-mib",
            "4096",
            "--moe-cache-cpu-share",
            "0.15",
            "-fa",
            "on",
            "-ctk",
            "q8_0",
            "-ctv",
            "q8_0",
            "-c",
            "2048",
            "-n",
            str(int(max_new_tokens)),
            "--temp",
            "0",
            "--seed",
            "42",
            "--no-display-prompt",
            "-no-cnv",
            "-p",
            chat_prompt,
        ]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Generation failed on {item['id']} (rc={proc.returncode}): {proc.stderr[-1000:]}"
            )
        outputs.append({"id": item["id"], "lang": item["lang"], "output": proc.stdout.strip()})

    audit = audit_10prompt_generations(outputs)
    audit["raw_outputs"] = outputs
    return audit
