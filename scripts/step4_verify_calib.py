#!/usr/bin/env python3
r"""
Step 4 acceptance gate (authored by Claude Opus reviewer, 08.11.2026).

DO NOT MODIFY THIS FILE. The executor (Argon) must make the dataset pass this gate unchanged.
Its SHA-256 is recorded in research/step4_fix_tz.md; any edit invalidates Step 4 acceptance.

Usage:
  D:\projects\SmartLLM\.venv\Scripts\python.exe D:\projects\SmartLLM\scripts\step4_verify_calib.py
Exit code 0 = PASS, 1 = FAIL. Writes research/step4_raw/verify_report.json.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image
from transformers import AutoProcessor, AutoTokenizer

ROOT = Path(r"D:\projects\SmartLLM")
MODEL_DIR = ROOT / "models" / "Qwen3.8-Flash-Next"
JSONL = ROOT / "data" / "calib" / "PremiumWebStudio-Calib.jsonl"
IMATRIX = ROOT / "data" / "calib" / "imatrix_corpus.txt"
AUDIT = ROOT / "research" / "step4_raw" / "hf_datasets_audit.json"
TASKS = ROOT / "eval" / "suite" / "tasks.json"
REF_DIR = ROOT / "eval" / "suite" / "ref"
REPORT = ROOT / "research" / "step4_raw" / "verify_report.json"

LOCAL_GENERATOR = "SmartLLM/curated-bilingual-canons"
PERMISSIVE = {"apache-2.0", "mit", "cc-by-4.0", "cc0-1.0", "bsd-3-clause", "bsd-2-clause", "odc-by", "cdla-permissive-2.0"}
STRATA = {
    "pillar_1_frontend_3d_svg", "pillar_2_seo_geo_security", "pillar_3_style_canons_vision",
    "pillar_4_art_direction_copywriting", "agentic_tool_calling", "long_context", "general_anti_starvation",
}
REQUIRED_KEYS = {
    "id", "pillar", "lang", "subdomain", "source_repo", "source_ref", "license", "synthetic", "modality",
    "images", "messages", "tools", "text", "qwen38_tokens",
}
EVAL_IDS = [
    "thermotech engineering", "vkvstudio", "северная мануфактура", "dagexecutor", "dagcycleerror",
    "dagvalidationerror", "nodeexecutionreport", "helvetica kinetic lab", "vortex compute", "цех №4",
    "архив технологий", "aetheria bio-robotics", "контур-спектр", "kronos precision gearworks",
]
RE_CYR = re.compile(r"[А-Яа-яЁё]")
RE_LAT = re.compile(r"[A-Za-z]")
RE_FENCE = re.compile(r"```.*?```", re.S)
RE_TAG = re.compile(r"<[^>]{0,400}>")

failures: list[str] = []
metrics: dict = {}


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


def prose_cyr_ratio(s: str) -> float:
    s = RE_FENCE.sub(" ", s)
    s = RE_TAG.sub(" ", s)
    c, l = len(RE_CYR.findall(s)), len(RE_LAT.findall(s))
    return c / max(1, c + l)


def main() -> int:
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
    proc = AutoProcessor.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
    image_pad_id = tok.convert_tokens_to_ids("<|image_pad|>")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    ref_hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in REF_DIR.glob("*.png")}
    eval_fp = [t["prompt"][:100].lower() for t in json.loads(TASKS.read_text(encoding="utf-8")).get("tasks", []) if len(t.get("prompt", "")) >= 80]
    eval_fp += EVAL_IDS

    rows = [json.loads(l) for l in JSONL.open(encoding="utf-8") if l.strip()]
    check(len(rows) > 0, "dataset is empty")

    tok_by = defaultdict(int)
    tok_lang = Counter()
    tok_synth = 0
    tok_reason = 0
    reason_strata = set()
    lc_lens = []
    gen_en_sub = Counter()
    seen_text = set()
    total = 0

    for r in rows:
        rid = r.get("id", "?")
        missing = REQUIRED_KEYS - set(r)
        check(not missing, f"{rid}: missing keys {sorted(missing)}")
        if missing:
            continue
        check(r["pillar"] in STRATA, f"{rid}: unknown pillar {r['pillar']}")
        check(r["lang"] in ("en", "ru"), f"{rid}: bad lang")
        check(isinstance(r["synthetic"], bool), f"{rid}: synthetic must be bool")
        check(bool(r["source_ref"]), f"{rid}: empty source_ref (file/offset/row id required)")

        # License provenance
        src = r["source_repo"]
        if src == LOCAL_GENERATOR:
            check(r["synthetic"] is True, f"{rid}: local generator rows must be synthetic=true")
        else:
            a = audit.get(src)
            check(a is not None, f"{rid}: source {src} missing from hf_datasets_audit.json")
            if a:
                check(a.get("status") == 200 and a.get("private") is False and a.get("gated") is False,
                      f"{rid}: source {src} not public/ungated in audit")
                check(str(a.get("license", "")).lower() in PERMISSIVE, f"{rid}: source {src} license {a.get('license')} not permissive")
                check(r["license"] == a.get("license"), f"{rid}: license field != audit license")

        # Exact re-render through the OFFICIAL chat template
        try:
            rendered = tok.apply_chat_template(r["messages"], tools=r["tools"] or None, tokenize=False)
        except Exception as e:  # noqa: BLE001
            check(False, f"{rid}: apply_chat_template failed: {e}")
            continue
        text = r["text"]
        check(rendered == text, f"{rid}: text != apply_chat_template(messages, tools)")
        check("<|im_start|>tool" not in text, f"{rid}: raw 'tool' role leaked (template wraps tool output into user <tool_response>)")
        check("<image:" not in text, f"{rid}: textual <image:...> placeholder present")

        # Tool calls must be structured, never JSON-in-content
        for m in r["messages"]:
            c = m.get("content")
            cs = c if isinstance(c, str) else " ".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
            if m.get("role") == "assistant":
                check("<tool_call>" not in cs, f"{rid}: tool call embedded as text in assistant content (use structured tool_calls)")
            st = cs.strip()
            if st.startswith("{") and st.endswith("}"):
                try:
                    obj = json.loads(st)
                    check(not (isinstance(obj, dict) and ({"system", "messages", "conversations"} & set(obj))),
                          f"{rid}: message content is a JSON-dumped conversation")
                except Exception:  # noqa: BLE001
                    pass
        if r["pillar"] == "agentic_tool_calling":
            has_calls = any(m.get("role") == "assistant" and m.get("tool_calls") for m in r["messages"])
            check(bool(r["tools"]) and has_calls, f"{rid}: agentic row needs tools[] and structured tool_calls")
            check("<function=" in text, f"{rid}: agentic row not rendered in native <function=...> format")

        # Token count (multimodal through the processor)
        imgs = r["images"] or []
        if r["modality"] == "multimodal":
            check(len(imgs) >= 1, f"{rid}: multimodal row without images")
            check(text.count("<|vision_start|><|image_pad|><|vision_end|>") == len(imgs), f"{rid}: vision token count != images")
            pil = []
            for im in imgs:
                p = ROOT / im["path"]
                if not p.exists():
                    check(False, f"{rid}: image missing {im['path']}")
                    continue
                b = p.read_bytes()
                h = hashlib.sha256(b).hexdigest()
                check(h == im.get("sha256"), f"{rid}: sha mismatch {im['path']}")
                check(h not in ref_hashes, f"{rid}: eval ref image leaked")
                pil.append(Image.open(p).convert("RGB"))
            if pil and len(pil) == len(imgs):
                out = proc(text=[text], images=pil, return_tensors=None)
                ids = out["input_ids"][0]
                n = len(ids)
                check(sum(1 for t in ids if t == image_pad_id) > len(imgs), f"{rid}: processor did not expand image tokens")
                check(n == r["qwen38_tokens"], f"{rid}: qwen38_tokens {r['qwen38_tokens']} != processor count {n}")
        else:
            check(not imgs, f"{rid}: text row has images")
            n = len(tok.encode(text, add_special_tokens=False))
            check(n == r["qwen38_tokens"], f"{rid}: qwen38_tokens {r['qwen38_tokens']} != recount {n}")
        n = r["qwen38_tokens"]
        total += n
        tok_by[r["pillar"]] += n
        tok_lang[r["lang"]] += n
        if r["synthetic"]:
            tok_synth += n

        # Reasoning traces (real, non-trivial)
        reas = [m.get("reasoning_content", "") for m in r["messages"] if m.get("role") == "assistant" and isinstance(m.get("reasoning_content"), str)]
        if any(len(tok.encode(x, add_special_tokens=False)) >= 200 for x in reas):
            check(r["synthetic"] is False, f"{rid}: reasoning traces must come from real datasets, not synthetic")
            tok_reason += n
            reason_strata.add(r["pillar"])

        # Language by prose (code/HTML stripped)
        ratio = prose_cyr_ratio(text)
        if r["lang"] == "ru":
            check(ratio >= 0.30, f"{rid}: lang=ru but prose Cyrillic ratio {ratio:.2f} < 0.30")
        else:
            check(ratio <= 0.05, f"{rid}: lang=en but prose Cyrillic ratio {ratio:.2f} > 0.05")

        # Structure, leakage, dupes
        check(text.count("```") % 2 == 0, f"{rid}: unclosed code fence")
        low = text.lower()
        check(not ("<!doctype html" in low and "</html>" not in low), f"{rid}: unclosed HTML document")
        for fp in eval_fp:
            if fp in low:
                check(False, f"{rid}: eval leakage '{fp[:40]}'")
                break
        hh = hashlib.sha256(text.encode()).hexdigest()
        check(hh not in seen_text, f"{rid}: duplicate text")
        seen_text.add(hh)

        if r["pillar"] == "long_context":
            lc_lens.append(n)
        if r["pillar"] == "general_anti_starvation" and r["lang"] == "en":
            gen_en_sub[r["subdomain"]] += n

    # Global gates
    check(500_000 <= total <= 1_000_000, f"total tokens {total} outside [500K, 1M]")
    ru_share = tok_lang["ru"] / max(1, total)
    check(0.27 <= ru_share <= 0.33, f"RU token share {ru_share:.3f} outside [0.27, 0.33]")
    pil14 = sum(tok_by[k] for k in STRATA if k.startswith("pillar_")) / max(1, total)
    check(pil14 >= 0.65, f"Pillars 1-4 share {pil14:.3f} < 0.65")
    for k, lo, hi in (("agentic_tool_calling", 0.09, 0.13), ("long_context", 0.05, 0.15), ("general_anti_starvation", 0.09, 0.13)):
        s = tok_by[k] / max(1, total)
        check(lo <= s <= hi, f"{k} share {s:.3f} outside [{lo}, {hi}]")
    check(tok_synth / max(1, total) <= 0.25, f"synthetic share {tok_synth / max(1, total):.3f} > 0.25")
    check(tok_reason / max(1, total) >= 0.12, f"reasoning-trace rows share {tok_reason / max(1, total):.3f} < 0.12")
    check(len(reason_strata) >= 3, f"reasoning traces present in only {len(reason_strata)} strata (need >= 3)")
    check(sum(1 for x in lc_lens if x >= 16_384) >= 6, "need >= 6 long_context rows >= 16,384 tokens")
    check(sum(1 for x in lc_lens if x >= 32_000) >= 2, "need >= 2 long_context rows >= 32,000 tokens")
    ge = sum(gen_en_sub.values())
    check(len(gen_en_sub) >= 3, f"general EN has {len(gen_en_sub)} subdomains (need >= 3)")
    check(gen_en_sub.get("code_general", 0) / max(1, ge) >= 0.20, "general EN code_general share < 0.20")
    check(all(v / max(1, ge) <= 0.50 for v in gen_en_sub.values()), "a general EN subdomain exceeds 50%")

    # Images on disk vs references
    img_dir = ROOT / "data" / "calib" / "images"
    on_disk = {p.name for p in img_dir.iterdir()} if img_dir.exists() else set()
    refd = {Path(im["path"]).name for r in rows for im in (r.get("images") or [])}
    check(on_disk == refd, f"images on disk vs referenced mismatch: orphans={len(on_disk - refd)} missing={len(refd - on_disk)}")

    # imatrix corpus: text-only rows, no vision/placeholder tokens
    im_txt = IMATRIX.read_text(encoding="utf-8")
    check("<image:" not in im_txt and "<|vision_start|>" not in im_txt, "imatrix_corpus.txt contains image placeholders/vision tokens")

    metrics.update({
        "rows": len(rows), "total_tokens": total, "ru_share": round(ru_share, 4), "pillars_1_4_share": round(pil14, 4),
        "by_stratum": dict(tok_by), "synthetic_share": round(tok_synth / max(1, total), 4),
        "reasoning_share": round(tok_reason / max(1, total), 4), "reasoning_strata": sorted(reason_strata),
        "long_context_lens": sorted(lc_lens), "general_en_subdomains": dict(gen_en_sub),
    })
    verdict = "PASS" if not failures else "FAIL"
    REPORT.write_text(json.dumps({"verdict": verdict, "failures": failures[:500], "n_failures": len(failures), "metrics": metrics},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=1))
    print(f"\n{verdict}: {len(failures)} failures")
    for f in failures[:40]:
        print(" -", f)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
