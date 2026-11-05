import base64
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser

BASE_DIR = r"D:\projects\SmartLLM\eval\round2"
REF_IMAGE = r"D:\projects\SmartLLM\eval\baseline\ref\t2.png"

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

T3_PROMPT = """Build a production-ready single-page landing for «Северная Мануфактура» — a boutique manufacturer of solid oak furniture (dining tables, cabinetry, architectural joinery). Language: Russian. Design canon: Luxury Minimalism — generous whitespace padding clamp(4rem, 10vw, 12rem), antiqua Cormorant Garamond / Playfair Display + clean sans-serif (system fallbacks, no external font CDNs), warm muted tones oklch(0.95 0.01 85), all colors as OKLCH design tokens in :root. No purple gradients, no centered 3-card template, no stock photos of people.
Sections: hero, product line table (3 flagship solid oak models with specs), technical inline SVG schematic of the joinery assembly (mortise-and-tenon / dovetail cross-section), certifications (FSC/GOST), FAQ (5 Q&A in Russian), contact form (no backend, client-side validation only), footer.
Requirements:
- Vanilla HTML/CSS/JS only, no frameworks, no external requests at all.
- Semantic HTML5, one h1, ARIA where needed, text contrast ≥ 7:1, keyboard accessible, prefers-reduced-motion respected.
- Performance: CLS 0 (explicit sizes / aspect-ratio), critical CSS inline, no render-blocking resources.
- SEO/GEO: title, meta description, canonical, Open Graph; JSON-LD @graph with Organization, Product (for each model), FAQPage (must match visible FAQ verbatim), BreadcrumbList; llms.txt per llmstxt.org format; robots.txt.
- Security: strict CSP in a meta tag using sha256 hashes for every inline script and style (no 'unsafe-inline'), plus a Cloudflare Pages `_headers` file with CSP (same policy + frame-ancestors 'none'), HSTS (max-age=63072000; includeSubDomains; preload), X-Content-Type-Options, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy.
Files: index.html, llms.txt, robots.txt, _headers."""

CONFIGS = [
    {
        "slug": "qwen3.8-no-think",
        "id": "qwen/qwen3.8-flash",
        "hugging_face_id": "Qwen/Qwen3.8-Flash-Next",
        "expected_provider": "Alibaba",
        "precision": "unknown (Alibaba cloud native)",
        "price_input_per_1m": 0.15,
        "price_output_per_1m": 0.47,
        "temperature": 0.6,
        "max_tokens": 32000,
        "reasoning": {"enabled": False},
    },
    {
        "slug": "qwen3.8-think-8k",
        "id": "qwen/qwen3.8-flash",
        "hugging_face_id": "Qwen/Qwen3.8-Flash-Next",
        "expected_provider": "Alibaba",
        "precision": "unknown (Alibaba cloud native)",
        "price_input_per_1m": 0.15,
        "price_output_per_1m": 0.47,
        "temperature": 0.6,
        "max_tokens": 32000,
        "reasoning": {"max_tokens": 8000},
    },
    {
        "slug": "qwen3.6-35b-a3b",
        "id": "qwen/qwen3.6-35b-a3b",
        "hugging_face_id": "Qwen/Qwen3.6-35B-A3B",
        "expected_provider": "DeepInfra / Parasail / AkashML",
        "precision": "fp8",
        "price_input_per_1m": 0.10,
        "price_output_per_1m": 0.95,
        "temperature": 0.6,
        "max_tokens": 32000,
        "reasoning": {"enabled": True},
        "provider": {"quantizations": ["fp8"]},
    },
]


class InlineBlockExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.styles = []
        self.scripts = []
        self._in_tag = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("style", "script"):
            self._in_tag = t
            self._buf = []

    def handle_data(self, data):
        if self._in_tag in ("style", "script"):
            self._buf.append(data)

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == self._in_tag:
            content = "".join(self._buf)
            if t == "style":
                self.styles.append(content)
            elif t == "script":
                self.scripts.append(content)
            self._in_tag = None
            self._buf = []


def sha256_b64(text: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


def extract_files_from_raw(raw_text: str, orig_dir: str, task: str) -> list[str]:
    """Extract files from raw.md into orig_dir without modifying model output."""
    os.makedirs(orig_dir, exist_ok=True)
    extracted = []
    # 1. Fenced code blocks preceded by FILE: <name>
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
            target_path = os.path.join(orig_dir, fname_clean)
            with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(code)
            extracted.append(fname_clean)
        return extracted

    # 2. Plain FILE: <name> headers without fenced blocks
    plain_headers = list(
        re.finditer(r"(?:^|\n)[ \t]*[`*#\-]*[ \t]*FILE:[ \t]*`?([A-Za-z0-9_.\-]+)`?[ `*:\t]*\r?\n", raw_text)
    )
    if plain_headers:
        for idx, m in enumerate(plain_headers):
            fname_clean = os.path.basename(m.group(1).strip())
            start_pos = m.end()
            end_pos = plain_headers[idx + 1].start() if idx + 1 < len(plain_headers) else len(raw_text)
            code = raw_text[start_pos:end_pos].strip("\r\n")
            code = re.sub(r"^```[^\r\n]*\r?\n", "", code)
            code = re.sub(r"\r?\n```\s*$", "", code)
            if not fname_clean:
                continue
            target_path = os.path.join(orig_dir, fname_clean)
            with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(code)
            extracted.append(fname_clean)
        return extracted

    # 3. Fallback single html block
    fallback = re.search(r"```(?:html)?\r?\n(.*?)(?:\r?\n```|$)", raw_text, re.DOTALL)
    if fallback:
        target_path = os.path.join(orig_dir, "index.html")
        with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(fallback.group(1))
        extracted.append("index.html (fallback)")
    elif "<!doctype html" in raw_text.lower() or "<html" in raw_text.lower():
        target_path = os.path.join(orig_dir, "index.html")
        with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(raw_text.strip())
        extracted.append("index.html (raw-html)")
    return extracted


def postprocess_csp(orig_dir: str, out_dir: str) -> dict:
    """Copy orig files to out_dir and inject exact sha256 hashes into CSP meta tag and _headers."""
    for fname in os.listdir(orig_dir):
        src = os.path.join(orig_dir, fname)
        dst = os.path.join(out_dir, fname)
        if os.path.isfile(src):
            shutil.copy2(src, dst)

    html_path = os.path.join(out_dir, "index.html")
    if not os.path.exists(html_path):
        return {"postprocessed": False, "reason": "no index.html"}

    with open(html_path, "r", encoding="utf-8") as fh:
        html_text = fh.read()

    ext = InlineBlockExtractor()
    ext.feed(html_text)

    style_hashes = [f"'{sha256_b64(s)}'" for s in ext.styles]
    script_hashes = [f"'{sha256_b64(s)}'" for s in ext.scripts]

    uses_data_css = "data:text/css" in html_text.lower()
    uses_data_js = "data:text/javascript" in html_text.lower()

    style_src_parts = style_hashes + (["data:"] if uses_data_css else [])
    script_src_parts = script_hashes + (["data:"] if uses_data_js else [])

    style_src_val = " ".join(style_src_parts) if style_src_parts else "'none'"
    script_src_val = " ".join(script_src_parts) if script_src_parts else "'none'"

    meta_policy = (
        f"default-src 'none'; "
        f"style-src {style_src_val}; "
        f"script-src {script_src_val}; "
        f"img-src 'self' data:; "
        f"font-src 'self' data:; "
        f"connect-src 'self'; "
        f"form-action 'self'; "
        f"base-uri 'none'; "
        f"object-src 'none'"
    )

    has_meta_csp = bool(re.search(r'<meta[^>]+http-equiv=["\']Content-Security-Policy["\'][^>]*>', html_text, re.I))
    if has_meta_csp:
        html_text_fixed = re.sub(
            r'(<meta[^>]+http-equiv=["\']Content-Security-Policy["\'][^>]*content=["\'])([^"\']*)(["\'][^>]*>)',
            lambda m: m.group(1) + meta_policy + m.group(3),
            html_text,
            flags=re.I,
        )
        # Also handle content before http-equiv
        if html_text_fixed == html_text:
            html_text_fixed = re.sub(
                r'(<meta[^>]+content=["\'])([^"\']*)(["\'][^>]+http-equiv=["\']Content-Security-Policy["\'][^>]*>)',
                lambda m: m.group(1) + meta_policy + m.group(3),
                html_text,
                flags=re.I,
            )
        with open(html_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html_text_fixed)

    headers_path = os.path.join(out_dir, "_headers")
    if os.path.exists(headers_path):
        with open(headers_path, "r", encoding="utf-8") as fh:
            h_text = fh.read()
        header_policy = meta_policy + "; frame-ancestors 'none'"
        h_text_fixed = re.sub(
            r"(Content-Security-Policy:\s*)([^\r\n]+)",
            lambda m: m.group(1) + header_policy,
            h_text,
            flags=re.I,
        )
        with open(headers_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(h_text_fixed)

    return {
        "postprocessed": True,
        "has_meta_csp": has_meta_csp,
        "injected_style_hashes": style_hashes,
        "injected_script_hashes": script_hashes,
        "uses_data_css": uses_data_css,
        "uses_data_js": uses_data_js,
    }


def run_single(cfg: dict, task: str, api_key: str) -> dict:
    out_dir = os.path.join(BASE_DIR, cfg["slug"], task)
    orig_dir = os.path.join(out_dir, "orig")
    os.makedirs(out_dir, exist_ok=True)
    meta_path = os.path.join(out_dir, "meta.json")
    raw_path = os.path.join(out_dir, "raw.md")

    if os.path.exists(raw_path) and os.path.getsize(raw_path) > 0 and os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as fh:
            existing = json.load(fh)
        if existing.get("finish_reason") in ("stop", "length"):
            print(f"[SKIP] {cfg['slug']} / {task} already completed.", flush=True)
            return existing

    if task == "t1":
        user_content = T1_PROMPT
    elif task == "t3":
        user_content = T3_PROMPT
    else:
        with open(REF_IMAGE, "rb") as img_f:
            b64_img = base64.b64encode(img_f.read()).decode("ascii")
        user_content = [
            {"type": "text", "text": T2_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
        ]

    payload = {
        "model": cfg["id"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
        "reasoning": cfg["reasoning"],
        "include_reasoning": True,
        "usage": {"include": True},
    }
    if "provider" in cfg:
        payload["provider"] = cfg["provider"]

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://smartllm.local",
            "X-Title": "SmartLLM Round 2 Eval",
        },
        method="POST",
    )

    print(f"[START] {cfg['slug']} ({cfg['id']}) -> {task} ...", flush=True)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            resp_bytes = resp.read()
        elapsed = round(time.perf_counter() - t0, 2)
        data = json.loads(resp_bytes.decode("utf-8"))
    except urllib.error.HTTPError as e:
        elapsed = round(time.perf_counter() - t0, 2)
        err_body = e.read().decode("utf-8", errors="replace")
        meta = {
            "config_slug": cfg["slug"],
            "model_id": cfg["id"],
            "task": task,
            "status": "http_error",
            "http_code": e.code,
            "error": err_body,
            "elapsed_sec": elapsed,
        }
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
        print(f"[ERROR] {cfg['slug']} / {task}: HTTP {e.code} in {elapsed}s -> {err_body[:200]}", flush=True)
        return meta
    except Exception as e:
        elapsed = round(time.perf_counter() - t0, 2)
        meta = {
            "config_slug": cfg["slug"],
            "model_id": cfg["id"],
            "task": task,
            "status": "exception",
            "error": str(e),
            "elapsed_sec": elapsed,
        }
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
        print(f"[ERROR] {cfg['slug']} / {task}: {e} in {elapsed}s", flush=True)
        return meta

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    reasoning_text = msg.get("reasoning") or ""
    finish_reason = choice.get("finish_reason")
    native_finish_reason = choice.get("native_finish_reason")
    usage = data.get("usage") or {}

    with open(raw_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)

    extracted_files = extract_files_from_raw(content, orig_dir, task)
    csp_post = postprocess_csp(orig_dir, out_dir)

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
    reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
    calc_cost = round(
        (prompt_tokens / 1_000_000.0) * cfg["price_input_per_1m"]
        + (completion_tokens / 1_000_000.0) * cfg["price_output_per_1m"],
        6,
    )
    reported_cost = usage.get("cost", calc_cost)

    meta = {
        "config_slug": cfg["slug"],
        "model_id": cfg["id"],
        "hugging_face_id": cfg["hugging_face_id"],
        "task": task,
        "provider": data.get("provider", cfg["expected_provider"]),
        "precision": cfg["precision"],
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
        "reasoning_config": cfg["reasoning"],
        "price_input_per_1m_usd": cfg["price_input_per_1m"],
        "price_output_per_1m_usd": cfg["price_output_per_1m"],
        "finish_reason": finish_reason,
        "native_finish_reason": native_finish_reason,
        "truncated": finish_reason == "length",
        "elapsed_sec": elapsed,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "content_tokens": max(0, completion_tokens - reasoning_tokens),
            "total_tokens": total_tokens,
            "cost_usd": reported_cost,
            "calculated_cost_usd": calc_cost,
            "raw_usage": usage,
        },
        "content_chars": len(content),
        "reasoning_chars": len(reasoning_text),
        "extracted_files": extracted_files,
        "csp_postprocessor": csp_post,
        "openrouter_id": data.get("id"),
    }

    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print(
        f"[DONE] {cfg['slug']} / {task} in {elapsed}s | "
        f"finish={finish_reason} | prompt={prompt_tokens} comp={completion_tokens} (reas={reasoning_tokens}) | "
        f"cost=${reported_cost} | files={extracted_files}",
        flush=True,
    )
    return meta


def main():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(BASE_DIR, exist_ok=True)
    jobs = []
    for cfg in CONFIGS:
        for task in ("t1", "t2", "t3"):
            jobs.append((cfg, task))

    results = []
    with ThreadPoolExecutor(max_workers=9) as pool:
        futs = {pool.submit(run_single, c, t, api_key): (c["slug"], t) for c, t in jobs}
        for fut in as_completed(futs):
            results.append(fut.result())

    summary_path = os.path.join(BASE_DIR, "run_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print("All 9 Round-2 jobs finished. Summary saved to", summary_path, flush=True)


if __name__ == "__main__":
    main()
