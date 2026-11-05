import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = r"D:\projects\SmartLLM\eval\baseline"
REF_IMAGE = os.path.join(BASE_DIR, "ref", "t2.png")

SYSTEM_PROMPT = (
    "You are a senior front-end engineer and designer. "
    "Output only the requested files, each in its own fenced code block preceded by a line `FILE: <name>`. "
    "No explanations."
)

T1_PROMPT = """Build a production-ready single-page landing for THERMOTECH ENGINEERING — a manufacturer of industrial hot-water and steam boilers (5–25 MW). Language: English. Design canon: Industrial B2B Engineering — 1px blueprint grid #2A2E35, JetBrains Mono + IBM Plex Sans (system fallbacks, no external font CDNs), signal orange accent oklch(0.68 0.19 45), all colors as OKLCH design tokens in :root. No purple gradients, no centered 3-card template, no stock photos of people.
Sections: hero, product line table (3 boiler models with specs), technical inline SVG schematic of the boiler circuit, certifications (ISO/GOST), FAQ (5 Q&A), contact form (no backend, client-side validation only), footer.
Requirements:
- Vanilla HTML/CSS/JS only, no frameworks, no external requests at all.
- Semantic HTML5, one h1, ARIA where needed, text contrast ≥ 7:1, keyboard accessible, prefers-reduced-motion respected.
- Performance: CLS 0 (explicit sizes / aspect-ratio), critical CSS inline, no render-blocking resources.
- SEO/GEO: title, meta description, canonical, Open Graph; JSON-LD @graph with Organization, Product (for each model), FAQPage (must match visible FAQ verbatim), BreadcrumbList; llms.txt per llmstxt.org format; robots.txt.
- Security: strict CSP in a meta tag using sha256 hashes for every inline script and style (no 'unsafe-inline'), plus a Cloudflare Pages `_headers` file with CSP (same policy + frame-ancestors 'none'), HSTS (max-age=63072000; includeSubDomains; preload), X-Content-Type-Options, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy.
Files: index.html, llms.txt, robots.txt, _headers."""

T2_PROMPT = (
    "Recreate this screenshot as a single self-contained index.html (inline CSS, no external requests, no frameworks). "
    "Match layout, spacing, typography hierarchy and colors as closely as possible; use OKLCH tokens in :root. "
    "Semantic HTML5, responsive down to 375px, contrast ≥ 7:1 where the design allows. Files: index.html."
)

MODELS = [
    {
        "slug": "qwen3.8-flash",
        "id": "qwen/qwen3.8-flash",
        "hugging_face_id": "Qwen/Qwen3.8-Flash-Next",
        "expected_provider": "Alibaba",
        "precision": "unknown (Alibaba cloud native)",
        "price_input_per_1m": 0.15,
        "price_output_per_1m": 0.47,
        "temperature": 0.6,
    },
    {
        "slug": "ling-3.0-flash-vl",
        "id": "inclusionai/ling-3.0-flash-vl",
        "hugging_face_id": "inclusionAI/Ling-3.0-flash-VL",
        "expected_provider": "DeepInfra",
        "precision": "fp16",
        "price_input_per_1m": 0.06,
        "price_output_per_1m": 0.18,
        "temperature": 0.6,
    },
]


def extract_files_from_raw(raw_text: str, out_dir: str, task: str) -> list[str]:
    """Extract files preceded by FILE: <name> (with or without fenced code blocks) without modifying model code."""
    extracted = []
    # 1. Match FILE: <name> followed by a fenced code block
    pattern = re.compile(
        r"(?:^|\n)\s*[`*#\-]*\s*FILE:\s*`?([A-Za-z0-9_.\-]+)`?[ `*:]*\r?\n+```[^\r\n]*\r?\n(.*?)(?:\r?\n```|$)",
        re.DOTALL,
    )
    matches = pattern.findall(raw_text)
    if matches:
        for fname, code in matches:
            fname_clean = os.path.basename(fname.strip())
            if not fname_clean:
                continue
            target_path = os.path.join(out_dir, fname_clean)
            with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(code)
            extracted.append(fname_clean)
        return extracted

    # 2. Match FILE: <name> blocks without fenced code blocks (split by FILE: <name> headers)
    plain_headers = list(
        re.finditer(r"(?:^|\n)[ \t]*[`*#\-]*[ \t]*FILE:[ \t]*`?([A-Za-z0-9_.\-]+)`?[ `*:\t]*\r?\n", raw_text)
    )
    if plain_headers:
        for idx, m in enumerate(plain_headers):
            fname_clean = os.path.basename(m.group(1).strip())
            start_pos = m.end()
            end_pos = plain_headers[idx + 1].start() if idx + 1 < len(plain_headers) else len(raw_text)
            code = raw_text[start_pos:end_pos].strip("\r\n")
            if not fname_clean:
                continue
            target_path = os.path.join(out_dir, fname_clean)
            with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(code)
            extracted.append(fname_clean)
        return extracted

    # 3. Fallback for T2 if the model output a single ```html block without FILE: index.html
    if not extracted and task == "t2":
        fallback = re.search(r"```(?:html)?\r?\n(.*?)(?:\r?\n```|$)", raw_text, re.DOTALL)
        if fallback:
            target_path = os.path.join(out_dir, "index.html")
            with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(fallback.group(1))
            extracted.append("index.html (fallback-no-FILE-prefix)")
    return extracted


def run_single(model_cfg: dict, task: str, api_key: str) -> dict:
    out_dir = os.path.join(BASE_DIR, model_cfg["slug"], task)
    os.makedirs(out_dir, exist_ok=True)
    meta_path = os.path.join(out_dir, "meta.json")
    raw_path = os.path.join(out_dir, "raw.md")

    # Guard against accidental re-runs if raw.md already exists and is non-empty
    if os.path.exists(raw_path) and os.path.getsize(raw_path) > 0 and os.path.exists(meta_path):
        print(f"[SKIP] {model_cfg['slug']} / {task} already exists.")
        with open(meta_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    if task == "t1":
        user_content = T1_PROMPT
    else:
        with open(REF_IMAGE, "rb") as img_f:
            b64_img = base64.b64encode(img_f.read()).decode("ascii")
        user_content = [
            {"type": "text", "text": T2_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
        ]

    payload = {
        "model": model_cfg["id"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": model_cfg["temperature"],
        "max_tokens": 32000,
        "reasoning": {"enabled": True},
        "include_reasoning": True,
        "usage": {"include": True},
    }

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://smartllm.local",
            "X-Title": "SmartLLM Donor Baseline Eval",
        },
        method="POST",
    )

    print(f"[START] {model_cfg['id']} -> {task} ...")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            resp_bytes = resp.read()
        elapsed = round(time.perf_counter() - t0, 2)
        data = json.loads(resp_bytes.decode("utf-8"))
    except urllib.error.HTTPError as e:
        elapsed = round(time.perf_counter() - t0, 2)
        err_body = e.read().decode("utf-8", errors="replace")
        meta = {
            "model_id": model_cfg["id"],
            "model_slug": model_cfg["slug"],
            "task": task,
            "status": "http_error",
            "http_code": e.code,
            "error": err_body,
            "elapsed_sec": elapsed,
        }
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
        print(f"[ERROR] {model_cfg['id']} / {task}: HTTP {e.code} in {elapsed}s")
        return meta
    except Exception as e:
        elapsed = round(time.perf_counter() - t0, 2)
        meta = {
            "model_id": model_cfg["id"],
            "model_slug": model_cfg["slug"],
            "task": task,
            "status": "exception",
            "error": str(e),
            "elapsed_sec": elapsed,
        }
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
        print(f"[ERROR] {model_cfg['id']} / {task}: {e} in {elapsed}s")
        return meta

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    reasoning_text = msg.get("reasoning") or ""
    finish_reason = choice.get("finish_reason")
    native_finish_reason = choice.get("native_finish_reason")
    usage = data.get("usage") or {}

    # Save raw.md (if reasoning was returned in a separate field, save reasoning to reasoning.md and raw content to raw.md)
    with open(raw_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)

    if reasoning_text:
        with open(os.path.join(out_dir, "reasoning.md"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(reasoning_text)

    extracted_files = extract_files_from_raw(content, out_dir, task)

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
    reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
    calc_cost = round(
        (prompt_tokens / 1_000_000.0) * model_cfg["price_input_per_1m"]
        + (completion_tokens / 1_000_000.0) * model_cfg["price_output_per_1m"],
        6,
    )
    reported_cost = usage.get("cost", calc_cost)

    meta = {
        "model_id": model_cfg["id"],
        "hugging_face_id": model_cfg["hugging_face_id"],
        "model_slug": model_cfg["slug"],
        "task": task,
        "provider": data.get("provider", model_cfg["expected_provider"]),
        "precision": model_cfg["precision"],
        "temperature": model_cfg["temperature"],
        "max_tokens": 32000,
        "price_input_per_1m_usd": model_cfg["price_input_per_1m"],
        "price_output_per_1m_usd": model_cfg["price_output_per_1m"],
        "finish_reason": finish_reason,
        "native_finish_reason": native_finish_reason,
        "truncated": finish_reason == "length",
        "elapsed_sec": elapsed,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": total_tokens,
            "cost_usd": reported_cost,
            "calculated_cost_usd": calc_cost,
            "raw_usage": usage,
        },
        "content_chars": len(content),
        "reasoning_chars": len(reasoning_text),
        "extracted_files": extracted_files,
        "openrouter_id": data.get("id"),
    }

    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print(
        f"[DONE] {model_cfg['id']} / {task} in {elapsed}s | "
        f"finish={finish_reason} | prompt={prompt_tokens} comp={completion_tokens} (reas={reasoning_tokens}) | "
        f"cost=${reported_cost} | files={extracted_files}"
    )
    return meta


def main():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    jobs = []
    for m in MODELS:
        for t in ("t1", "t2"):
            jobs.append((m, t))

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(run_single, m, t, api_key): (m["slug"], t) for m, t in jobs}
        for fut in as_completed(futs):
            results.append(fut.result())

    summary_path = os.path.join(BASE_DIR, "run_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print("All 4 jobs finished. Summary written to", summary_path)


if __name__ == "__main__":
    main()
