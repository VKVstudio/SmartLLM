#!/usr/bin/env python3
"""
WP-C2 Independent Deterministic Verifier (`scripts/v2_calib/verify_calib_v2.py`).
Audits `data/calib_v2/` and `data/eval_E/` against all OPUS_MASTER_PLAN_V2.md §1.D5, §2 WP-C2,
and §3 Skeptic Gate W1 invariants. Exits 0 only if all checks pass.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from transformers import AutoTokenizer

REPO_ROOT = Path("/mnt/rescue/projects/SmartLLM")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.infra.download_ledger import get_summary
from scripts.v2_calib.build_calib_v2 import (
    EVAL_BENCHMARK_IDENTIFIERS,
    STRATA_SPEC,
    calc_qwen38_multimodal_tokens,
)

MODEL_DIR = REPO_ROOT / "models" / "Qwen3.8-Flash-Next"
CALIB_V2_DIR = REPO_ROOT / "data" / "calib_v2"
EVAL_E_DIR = REPO_ROOT / "data" / "eval_E"

FORBIDDEN_SOURCES_RE = re.compile(
    r"(?:runanlab|glyphsoftware|uigen|mihenk|websight|openthoughts|grandmaster|vikhr|"
    r"ultrachat|capybara|longwriter|swe-smith|trendyol|humanlearning|data/harvest)",
    re.IGNORECASE,
)

TAILWIND_UTILITY_RE = re.compile(
    r'class="[^"]*\b(?:bg-(?:slate|zinc|neutral|stone|red|blue|emerald|indigo)-\d{2,3}|'
    r'text-(?:xs|sm|base|lg|xl|2xl|3xl|slate-\d{2,3})|px-\d+|py-\d+|rounded-(?:md|lg|xl|2xl)|'
    r'shadow-(?:sm|md|lg|xl)|grid-cols-\d+|flex-col)\b[^"]*"'
)

ALLOWED_LICENSES = {
    "ODC-By-1.0",
    "CC0-1.0",
    "MIT",
    "CC-BY-4.0",
    "CC-BY-SA-2.5",
    "CC-BY-SA-4.0",
    "CC-BY-SA-3.0",
}


def word_5grams(text: str) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+", text.lower())
    if len(words) < 5:
        return {tuple(words)} if words else set()
    return {tuple(words[i : i + 5]) for i in range(0, len(words) - 4, 3)}


def main() -> int:
    errors: list[str] = []

    calib_jsonl = CALIB_V2_DIR / "calib_v2.jsonl"
    if not calib_jsonl.exists():
        print("FAIL: data/calib_v2/calib_v2.jsonl does not exist", file=sys.stderr)
        return 1

    rows = [json.loads(line) for line in calib_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 640:
        errors.append(f"Expected 640 sequences in calib_v2.jsonl, got {len(rows)}")

    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)

    required_fields = {"id", "stratum", "lang", "source", "license", "doc_id", "messages", "text", "qwen38_tokens"}
    strata_tokens: Counter[str] = Counter()
    strata_seqs: Counter[str] = Counter()
    lang_tokens: Counter[str] = Counter()
    seen_ids: set[str] = set()
    calib_doc_ids: set[str] = set()
    calib_5gram_sets: list[tuple[str, set[tuple[str, ...]]]] = []

    ru_think_count = 0
    en_think_count = 0
    mm_ru_tokens = 0
    mm_en_tokens = 0

    for idx, r in enumerate(rows):
        missing = required_fields - set(r.keys())
        if missing:
            errors.append(f"Row {idx} ({r.get('id')}) missing required fields: {missing}")
            continue
        rid = r["id"]
        if rid in seen_ids:
            errors.append(f"Duplicate row id: {rid}")
        seen_ids.add(rid)

        if r.get("doc_id"):
            calib_doc_ids.add(str(r["doc_id"]))
        if r.get("source_ref"):
            calib_doc_ids.add(str(r["source_ref"]))

        stratum = r["stratum"]
        if stratum not in STRATA_SPEC:
            errors.append(f"Row {rid} has unknown stratum: {stratum}")

        lic = r["license"]
        if lic not in ALLOWED_LICENSES:
            errors.append(f"Row {rid} has unapproved license: {lic}")

        src_combined = f"{r.get('source', '')} {r.get('source_repo', '')} {r.get('source_ref', '')}"
        if FORBIDDEN_SOURCES_RE.search(src_combined):
            errors.append(f"Row {rid} references forbidden/API-distilled source: {src_combined}")

        toks = int(r["qwen38_tokens"])
        if toks <= 0 or toks > 2048:
            errors.append(f"Row {rid} token count {toks} violates (0, 2048] cap")

        # Spot-check token counts and multimodal images
        if r.get("modality") == "multimodal":
            imgs = r.get("images") or []
            if len(imgs) != 1:
                errors.append(f"Multimodal row {rid} must have 1 image, got {len(imgs)}")
            else:
                im_info = imgs[0]
                im_path = REPO_ROOT / im_info["path"]
                if not im_path.exists():
                    errors.append(f"Missing image file for {rid}: {im_path}")
                else:
                    actual_sha = hashlib.sha256(im_path.read_bytes()).hexdigest()
                    if actual_sha != im_info["sha256"]:
                        errors.append(f"Image sha256 mismatch for {rid}")
                    with Image.open(im_path) as pil_im:
                        rgb = pil_im.convert("RGB")
                        w, h = rgb.size
                        if (w, h) != (im_info["width"], im_info["height"]):
                            errors.append(f"Image dimensions mismatch for {rid}: {(w, h)} vs {im_info}")
                        arr = np.asarray(rgb, dtype=np.float32)
                        if float(arr.std()) < 5.0:
                            errors.append(f"Blank/low-variance image for {rid}: std={arr.std():.2f}")
                        exact_mm_toks = calc_qwen38_multimodal_tokens(tokenizer, r["text"], w, h)
                        if exact_mm_toks != toks:
                            errors.append(f"Multimodal token mismatch for {rid}: stored {toks} vs exact {exact_mm_toks}")
            if r["lang"] == "ru":
                mm_ru_tokens += toks
            else:
                mm_en_tokens += toks
        else:
            if idx % 16 == 0 or toks > 1900:
                exact_toks = len(tokenizer.encode(r["text"], add_special_tokens=False))
                if exact_toks != toks:
                    errors.append(f"Token count mismatch on {rid}: stored {toks} vs exact {exact_toks}")

        if stratum in ("ru_think_cot", "en_think_cot"):
            assistant_msg = r["messages"][-1]
            rc = str(assistant_msg.get("reasoning_content") or "").strip()
            if len(rc) < 80:
                errors.append(f"CoT row {rid} has empty or too-short reasoning_content")
            if f"<think>\n{rc}\n</think>" not in r["text"]:
                errors.append(f"CoT row {rid} text does not contain rendered <think> block")
            if stratum == "ru_think_cot":
                ru_think_count += 1
            else:
                en_think_count += 1

        if stratum in ("full_doc_html_css", "ui_audit_vision"):
            if TAILWIND_UTILITY_RE.search(r["text"]):
                errors.append(f"Tailwind utility class detected in {rid} ({stratum})")

        lower_txt = r["text"].lower()
        for ident in EVAL_BENCHMARK_IDENTIFIERS:
            if ident in lower_txt:
                errors.append(f"Held-out benchmark identifier '{ident}' leaked in {rid}")

        strata_tokens[stratum] += toks
        strata_seqs[stratum] += 1
        lang_tokens[r["lang"]] += toks
        calib_5gram_sets.append((rid, word_5grams(r["text"])))

    # Check all 12 strata against +-10% target
    for s_name, spec in STRATA_SPEC.items():
        actual_t = strata_tokens[s_name]
        target_t = spec["target_tokens"]
        delta_pct = ((actual_t - target_t) / target_t) * 100.0
        if abs(delta_pct) > 10.0:
            errors.append(
                f"Stratum {s_name} tokens {actual_t} outside +-10% of target {target_t} ({delta_pct:+.2f}%)"
            )
    if mm_ru_tokens < 14_400 or mm_ru_tokens > 17_600:
        errors.append(f"ui_audit_vision RU tokens {mm_ru_tokens} outside 16k +-10%")
    if mm_en_tokens < 13_500 or mm_en_tokens > 16_500:
        errors.append(f"ui_audit_vision EN tokens {mm_en_tokens} outside 15k +-10%")

    total_tokens = sum(strata_tokens.values())
    ru_share_pct = (lang_tokens["ru"] / total_tokens) * 100.0 if total_tokens else 0.0
    if not (35.0 <= ru_share_pct <= 40.0):
        errors.append(f"RU token share {ru_share_pct:.2f}% outside [35.0%, 40.0%]")

    if ru_think_count < en_think_count:
        errors.append(f"RU <think> CoT rows ({ru_think_count}) < EN <think> CoT rows ({en_think_count})")

    # Verify Eval Set E
    eval_jsonl = EVAL_E_DIR / "eval_E.jsonl"
    gen_jsonl = EVAL_E_DIR / "gen_prompts_10.jsonl"
    eval_manifest = EVAL_E_DIR / "sha256_manifest.json"
    if not eval_jsonl.exists() or not gen_jsonl.exists() or not eval_manifest.exists():
        errors.append("Missing required files in data/eval_E/")
    else:
        eval_rows = [json.loads(l) for l in eval_jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
        en_eval_toks = sum(int(r["qwen38_tokens"]) for r in eval_rows if r["lang"] == "en")
        ru_eval_toks = sum(int(r["qwen38_tokens"]) for r in eval_rows if r["lang"] == "ru")
        if not (3800 <= en_eval_toks <= 4300):
            errors.append(f"Eval E EN tokens {en_eval_toks} outside [3800, 4300]")
        if not (3800 <= ru_eval_toks <= 4300):
            errors.append(f"Eval E RU tokens {ru_eval_toks} outside [3800, 4300]")

        max_jaccard = 0.0
        for er in eval_rows:
            if er["doc_id"] in calib_doc_ids or (er.get("url") and er["url"] in calib_doc_ids):
                errors.append(f"Eval E row {er['id']} shares doc_id/url with calib_v2: {er['doc_id']}")
            e_grams = word_5grams(er["text"])
            if e_grams:
                for cid, c_grams in calib_5gram_sets:
                    if not c_grams:
                        continue
                    inter = len(e_grams & c_grams)
                    if inter > 0:
                        jac = inter / len(e_grams | c_grams)
                        if jac > max_jaccard:
                            max_jaccard = jac
                        if jac >= 0.15:
                            errors.append(
                                f"Eval E row {er['id']} has 5-gram Jaccard {jac:.3f} >= 0.15 with {cid}"
                            )

        gen_rows = [json.loads(l) for l in gen_jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
        if len(gen_rows) != 10:
            errors.append(f"Expected 10 prompts in gen_prompts_10.jsonl, got {len(gen_rows)}")
        if sum(1 for g in gen_rows if g["lang"] == "en") != 5 or sum(1 for g in gen_rows if g["lang"] == "ru") != 5:
            errors.append("gen_prompts_10.jsonl must contain exactly 5 EN and 5 RU prompts")

    ledger = get_summary()
    wp_c2_entry = ledger["by_wp"].get("WP-C2", 0)
    wp_c2_bytes = wp_c2_entry["used_bytes"] if isinstance(wp_c2_entry, dict) else int(wp_c2_entry)
    if wp_c2_bytes > 380_000_000:
        errors.append(f"WP-C2 download ledger {wp_c2_bytes} exceeds 380 MB cap")

    report = {
        "passed": len(errors) == 0,
        "total_sequences": len(rows),
        "total_tokens": total_tokens,
        "ru_tokens": lang_tokens["ru"],
        "en_tokens": lang_tokens["en"],
        "ru_share_pct": round(ru_share_pct, 2),
        "ru_think_rows": ru_think_count,
        "en_think_rows": en_think_count,
        "ui_audit_vision_ru_tokens": mm_ru_tokens,
        "ui_audit_vision_en_tokens": mm_en_tokens,
        "eval_E_max_5gram_jaccard": round(max_jaccard, 4),
        "wp_c2_ledger_bytes": wp_c2_bytes,
        "error_count": len(errors),
        "errors": errors,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
