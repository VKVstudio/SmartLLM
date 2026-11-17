#!/usr/bin/env python3
"""Deterministic validator and self-test suite for blind holdout tasks (eval/holdout/)."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

HOLDOUT_DIR = Path(__file__).resolve().parent
TASKS_HOLDOUT_JSON = HOLDOUT_DIR / "tasks_holdout.json"
SUITE_TASKS_JSON = HOLDOUT_DIR.parent / "suite" / "tasks.json"
NODE_EXE = os.environ.get("SMARTLLM_NODE_EXE") or "/usr/bin/node"

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_WORD_SCRIPT_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+")
_HAS_LATIN_RE = re.compile(r"[A-Za-z]")
_HAS_CYR_RE = re.compile(r"[А-Яа-яЁё]")
_EN_SLOP_RE = re.compile(
    r"\b(delve|testament|tapestry|unleash|seamless|game-changer|cutting-edge)\b",
    re.IGNORECASE,
)
_RU_SLOP_RE = re.compile(
    r"(бесшовн\w+|откройте для себя|погрузитесь в мир|инновационный подход|новый уровень)",
    re.IGNORECASE,
)
_TAILWIND_CLASS_RE = re.compile(
    r'\bclass\s*=\s*["\'][^"\']*\b(bg-(?:slate|zinc|indigo|purple)-\d{2,3}|text-(?:xs|sm|lg|xl|2xl)|flex-col|items-center|justify-between|p-\d+|px-\d+|py-\d+|rounded-(?:lg|xl|2xl|full))\b',
    re.IGNORECASE,
)
_LEGACY_100VH_RE = re.compile(r":\s*100vh\b", re.IGNORECASE)
_JS_STYLE_MUTATION_RE = re.compile(
    r"(\.\s*style\s*\.[A-Za-z_$]+|\.\s*style\s*\.\s*setProperty\s*\(|setAttribute\s*\(\s*['\"]style['\"])"
)


def oklch_to_srgb(L: float, C: float, H_deg: float) -> tuple[float, float, float]:
    """Convert OKLCH (L in 0..1 or 0..100%, C, H in degrees) to sRGB linear channels."""
    if L > 1.0:
        L = L / 100.0
    h_rad = math.radians(H_deg)
    a = C * math.cos(h_rad)
    b = C * math.sin(h_rad)

    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    l = l_ * l_ * l_
    m = m_ * m_ * m_
    s = s_ * s_ * s_

    r_lin = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g_lin = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b_lin = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    return (
        max(0.0, min(1.0, r_lin)),
        max(0.0, min(1.0, g_lin)),
        max(0.0, min(1.0, b_lin)),
    )


def relative_luminance(L: float, C: float, H_deg: float) -> float:
    r, g, b = oklch_to_srgb(L, C, H_deg)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(lum1: float, lum2: float) -> float:
    hi = max(lum1, lum2)
    lo = min(lum1, lum2)
    return round((hi + 0.05) / (lo + 0.05), 2)


def parse_oklch_tokens(css_text: str) -> dict[str, dict]:
    tokens: dict[str, dict] = {}
    pat = re.compile(
        r"(--[A-Za-z0-9_\-]+)\s*:\s*oklch\(\s*([0-9.]+%?)\s+([0-9.]+)\s+([0-9.]+)(?:\s*/\s*([0-9.]+%?))?\s*\)",
        re.IGNORECASE,
    )
    for name, l_str, c_str, h_str, alpha in pat.findall(css_text):
        if alpha:
            continue
        L = float(l_str.rstrip("%")) / (100.0 if l_str.endswith("%") else 1.0)
        C = float(c_str)
        H = float(h_str)
        tokens[name] = {
            "L": round(L, 4),
            "C": round(C, 4),
            "H": round(H, 2),
            "luminance": round(relative_luminance(L, C, H), 4),
        }
    return tokens


def evaluate_semantic_oklch_contrast(tokens: dict[str, dict]) -> dict:
    bg_keys = [k for k in tokens if any(p in k.lower() for p in ("bg", "surface", "panel", "paper"))]
    fg_keys = [k for k in tokens if any(p in k.lower() for p in ("text", "ink", "fg"))]
    if not bg_keys or not fg_keys:
        return {"semantic_pairs_checked": 0, "primary_contrast": 0.0, "passes_aaa_7_to_1": False}

    primary_bg = [k for k in bg_keys if "main" in k.lower() or "paper" in k.lower() or k.lower() == "--bg"] or bg_keys
    primary_fg = [k for k in fg_keys if "main" in k.lower() or "primary" in k.lower() or k.lower() in ("--text", "--ink")] or fg_keys

    best_primary = 0.0
    for bk in primary_bg:
        for fk in primary_fg:
            cr = contrast_ratio(tokens[bk]["luminance"], tokens[fk]["luminance"])
            if cr > best_primary:
                best_primary = cr

    return {
        "semantic_pairs_checked": len(primary_bg) * len(primary_fg),
        "primary_contrast": best_primary,
        "passes_aaa_7_to_1": best_primary >= 7.0,
    }


def parse_cloudflare_headers(h_text: str) -> dict:
    lines = h_text.splitlines()
    has_route = False
    headers: dict[str, str] = {}
    in_route = False

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(("{", "}", "[", "]", '"')) or stripped.endswith("*/") or ("/*" in stripped and stripped != "/*" and not stripped.startswith("/*.")):
            return {"valid_syntax": False, "headers": {}, "error": "invalid_comment_or_json_syntax"}
        if line[0] not in (" ", "\t"):
            if stripped in ("/*", "/index.html", "/*.html"):
                has_route = True
                in_route = True
            else:
                in_route = False
            continue
        if in_route:
            m = re.match(r"^[ \t]+([A-Za-z0-9\-]+)[ \t]*:[ \t]*(.+?)[ \t]*$", line)
            if m:
                headers[m.group(1).lower()] = m.group(2).strip()

    return {"valid_syntax": has_route and len(headers) > 0, "headers": headers}


class HoldoutHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.styles: list[str] = []
        self.scripts: list[tuple[str, str]] = []
        self.inline_events: list[tuple[str, str]] = []
        self.meta_csp: str | None = None
        self.meta_tags: list[dict[str, str]] = []
        self.link_tags: list[dict[str, str]] = []
        self.title_text = ""
        self.h1_count = 0
        self.landmarks: set[str] = set()
        self.svgs_count = 0
        self._in_tag: str | None = None
        self._script_type: str = ""
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k.lower(): (v or "") for k, v in attrs if k}
        t = tag.lower()
        for k in ad:
            if k.startswith("on") and len(k) > 2:
                self.inline_events.append((t, k))
        if t == "h1":
            self.h1_count += 1
        if t in ("header", "nav", "main", "section", "article", "aside", "footer", "figure"):
            self.landmarks.add(t)
        if t == "svg":
            self.svgs_count += 1
        if t == "meta":
            self.meta_tags.append(ad)
            if ad.get("http-equiv", "").lower() == "content-security-policy":
                self.meta_csp = ad.get("content", "")
        if t == "link":
            self.link_tags.append(ad)
        if t in ("style", "script", "title"):
            self._in_tag = t
            self._script_type = ad.get("type", "").lower()
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._in_tag is not None:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if self._in_tag == t:
            txt = "".join(self._buf)
            if t == "style":
                self.styles.append(txt)
            elif t == "script":
                self.scripts.append((self._script_type, txt))
            elif t == "title":
                self.title_text = txt.strip()
            self._in_tag = None
            self._buf = []


def strip_html_to_prose(html_text: str) -> str:
    no_code = re.sub(r"<(script|style)\b[^>]*>(?:.*?</\1>|.*$)", " ", html_text, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", no_code))).strip()


def validate_raw_csp_policy(csp_value: str | None) -> dict:
    if not csp_value:
        return {"passed": False, "reason": "missing_csp"}
    low = csp_value.lower()
    has_unsafe_inline_script = False
    for directive in csp_value.split(";"):
        d = directive.strip().lower()
        if d.startswith("script-src") and "'unsafe-inline'" in d:
            has_unsafe_inline_script = True
        if d.startswith("style-src") and "'unsafe-inline'" in d:
            has_unsafe_inline_script = True

    checks = {
        "has_style_placeholder": "sha256-__csp_style__" in low,
        "has_script_placeholder": "sha256-__csp_script__" in low,
        "no_unsafe_inline": not has_unsafe_inline_script and "'unsafe-eval'" not in low,
        "has_object_src_none": "object-src 'none'" in low,
        "has_base_uri_none_or_self": "base-uri 'none'" in low or "base-uri 'self'" in low,
        "has_frame_ancestors_none": "frame-ancestors 'none'" in low,
        "has_trusted_types": "require-trusted-types-for 'script'" in low,
    }
    checks["passed"] = all(checks.values())
    return checks


def validate_web_or_copy_holdout(task_spec: dict, files_map: dict[str, str]) -> dict:
    req_files = task_spec["required_files"]
    missing = [f for f in req_files if f not in files_map or not files_map[f].strip()]
    if missing:
        return {"passed": False, "stage": "required_files", "missing_files": missing}

    html_text = files_map["index.html"]
    if "</html>" not in html_text.lower():
        return {"passed": False, "stage": "html_closure", "reason": "unclosed_html_tag"}

    parser = HoldoutHTMLParser()
    parser.feed(html_text)
    combined_css = "\n".join(parser.styles)
    combined_js = "\n".join(body for stype, body in parser.scripts if stype != "application/ld+json")
    ld_blocks = [body for stype, body in parser.scripts if stype == "application/ld+json"]
    prose = strip_html_to_prose(html_text)

    # 1. Raw CSP & Security Headers check (pre-postprocessor)
    raw_csp = validate_raw_csp_policy(parser.meta_csp)
    js_style_muts = len(_JS_STYLE_MUTATION_RE.findall(combined_js))
    hdr_parsed = parse_cloudflare_headers(files_map["_headers"])
    hdrs = hdr_parsed.get("headers", {})
    hsts_m = re.search(r"max-age=(\d+)", hdrs.get("strict-transport-security", ""), re.I)
    hsts_ok = bool(hsts_m and int(hsts_m.group(1)) >= 31536000 and "includesubdomains" in hdrs.get("strict-transport-security", "").lower())
    headers_ok = (
        hdr_parsed["valid_syntax"]
        and validate_raw_csp_policy(hdrs.get("content-security-policy"))["passed"]
        and hsts_ok
        and hdrs.get("cross-origin-opener-policy", "").lower() == "same-origin"
        and hdrs.get("cross-origin-embedder-policy", "").lower() in ("require-corp", "credentialless")
        and hdrs.get("cross-origin-resource-policy", "").lower() == "same-origin"
        and hdrs.get("x-content-type-options", "").lower() == "nosniff"
    )

    # 2. Modern CSS & OKLCH contrast check
    tokens = parse_oklch_tokens(combined_css)
    contrast_info = evaluate_semantic_oklch_contrast(tokens)
    css_modern_ok = (
        len(tokens) >= 5
        and contrast_info["passes_aaa_7_to_1"]
        and "100dvh" in combined_css.lower()
        and not bool(_LEGACY_100VH_RE.search(combined_css))
        and not bool(_TAILWIND_CLASS_RE.search(html_text))
        and "grid" in combined_css.lower()
        and "subgrid" in combined_css.lower()
        and "@container" in combined_css.lower()
        and "scroll-padding-top" in combined_css.lower()
        and "prefers-reduced-motion" in combined_css.lower()
    )

    # 3. JSON-LD @graph & FAQ verbatim check
    json_ld_ok = False
    if ld_blocks:
        try:
            ld_obj = json.loads(ld_blocks[0])
            graph = ld_obj.get("@graph", []) if isinstance(ld_obj, dict) else []
            g_types = {item.get("@type") for item in graph if isinstance(item, dict)}
            req_types = {"Organization", "WebSite", "WebPage", "Product", "BreadcrumbList", "FAQPage"}
            faq_items = [item for item in graph if isinstance(item, dict) and item.get("@type") == "FAQPage"]
            faq_verbatim = False
            if faq_items:
                entities = faq_items[0].get("mainEntity", [])
                faq_verbatim = len(entities) >= 3 and all(
                    isinstance(q, dict)
                    and q.get("name", "").strip() in prose
                    and q.get("acceptedAnswer", {}).get("text", "").strip() in prose
                    for q in entities
                )
            json_ld_ok = req_types.issubset(g_types) and faq_verbatim
        except Exception:
            json_ld_ok = False

    # 4. Robots & llms.txt check
    robots_txt = files_map.get("robots.txt", "")
    robots_ok = all(
        bot in robots_txt
        for bot in ("GPTBot", "ClaudeBot", "Google-Extended", "OAI-SearchBot", "PerplexityBot", "Sitemap:")
    )
    llms_txt = files_map.get("llms.txt", "")
    llms_ok = llms_txt.lstrip().startswith("# ") and "\n> " in llms_txt and "\n## " in llms_txt

    # 5. Copy & Language Hygiene
    lang = task_spec["language"]
    all_prose = [prose]
    for extra_md in ("copy_deck.md", "copy_deck_ru.md", "audit_critique_ru.md"):
        if extra_md in files_map:
            all_prose.append(files_map[extra_md])
    joined_prose = "\n".join(all_prose)

    cjk_count = len(_CJK_RE.findall(joined_prose))
    mixed_words = [
        w for w in _WORD_SCRIPT_RE.findall(joined_prose) if _HAS_LATIN_RE.search(w) and _HAS_CYR_RE.search(w)
    ]
    if lang == "ru":
        cyr_chars = len(re.findall(r"[А-Яа-яЁё]", prose))
        lat_chars = len(re.findall(r"[A-Za-z]", prose))
        cyr_ratio = cyr_chars / max(1, cyr_chars + lat_chars)
        copy_ok = (
            cjk_count == 0
            and len(mixed_words) == 0
            and cyr_ratio >= 0.70
            and "«" in joined_prose
            and "»" in joined_prose
            and "—" in joined_prose
            and not bool(_RU_SLOP_RE.search(joined_prose))
        )
    else:
        copy_ok = (
            cjk_count == 0
            and len(mixed_words) == 0
            and not bool(_EN_SLOP_RE.search(joined_prose))
        )

    # 6. Task-specific checks
    task_specific_ok = True
    tid = task_spec["id"]
    if tid == "h1":
        try:
            zobj = json.loads(files_map["zimage_prompts.json"])
            plist = zobj.get("prompts", zobj) if isinstance(zobj, dict) else zobj
            task_specific_ok = (
                isinstance(plist, list)
                and len(plist) == 3
                and all(
                    isinstance(p, dict)
                    and len(str(p.get("prompt", ""))) >= 200
                    and str(p.get("exact_text_in_frame", "")) in str(p.get("prompt", ""))
                    for p in plist
                )
            )
        except Exception:
            task_specific_ok = False
    elif tid in ("h3", "h4"):
        deck_name = "copy_deck.md" if tid == "h3" else "copy_deck_ru.md"
        deck_txt = files_map.get(deck_name, "")
        task_specific_ok = deck_txt.count("## ") >= 3 and "|" in deck_txt
    elif tid == "h6":
        crit_txt = files_map.get("audit_critique_ru.md", "")
        task_specific_ok = all(f"Дефект {i}" in crit_txt for i in range(1, 9)) and "WCAG 2.2" in crit_txt

    passed = (
        raw_csp["passed"]
        and len(parser.inline_events) == 0
        and js_style_muts == 0
        and headers_ok
        and css_modern_ok
        and json_ld_ok
        and robots_ok
        and llms_ok
        and copy_ok
        and task_specific_ok
    )

    return {
        "passed": passed,
        "raw_csp": raw_csp["passed"],
        "no_inline_events": len(parser.inline_events) == 0,
        "no_js_style_mutations": js_style_muts == 0,
        "headers_ok": headers_ok,
        "css_modern_ok": css_modern_ok,
        "primary_contrast": contrast_info["primary_contrast"],
        "json_ld_ok": json_ld_ok,
        "robots_ok": robots_ok,
        "llms_ok": llms_ok,
        "copy_ok": copy_ok,
        "task_specific_ok": task_specific_ok,
    }


def validate_h5_typescript_holdout(files_map: dict[str, str]) -> dict:
    if "webhook_router.ts" not in files_map or not files_map["webhook_router.ts"].strip():
        return {"passed": False, "reason": "missing_webhook_router_ts"}

    ts_code = files_map["webhook_router.ts"]
    any_matches = re.findall(r"\b:\s*any\b|\bas\s+any\b|<any>", ts_code)
    if any_matches:
        return {"passed": False, "reason": "explicit_any_detected", "explicit_any_count": len(any_matches)}

    with tempfile.TemporaryDirectory(prefix="holdout_h5_") as tmpdir:
        tmp_path = Path(tmpdir)
        ts_file = tmp_path / "webhook_router.ts"
        ts_file.write_text(ts_code, encoding="utf-8")

        runner_mjs = tmp_path / "run_h5_check.mjs"
        runner_mjs.write_text(
            r"""
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const ts = require('/usr/lib/code/extensions/node_modules/typescript/lib/typescript.js');

const workDir = process.argv[2];
const absTs = path.join(workDir, 'webhook_router.ts');
const shimsPath = path.join(workDir, 'node_builtins.d.ts');
fs.writeFileSync(shimsPath, [
  'declare class Buffer extends Uint8Array {',
  '  static from(data: string, encoding?: string): Buffer;',
  '  toString(encoding?: string): string;',
  '}',
  'declare module "node:crypto" {',
  '  export interface Hmac { update(data: string | Uint8Array): this; digest(encoding: "hex"): string; }',
  '  export function createHmac(algorithm: string, key: string | Uint8Array): Hmac;',
  '  export function timingSafeEqual(a: Uint8Array, b: Uint8Array): boolean;',
  '}',
].join('\n'), 'utf-8');

const prog = ts.createProgram([shimsPath, absTs], {
  noEmit: true,
  strict: true,
  target: ts.ScriptTarget.ES2022,
  module: ts.ModuleKind.ES2022,
  moduleResolution: ts.ModuleResolutionKind.Bundler,
  skipLibCheck: true,
});
const diags = ts.getPreEmitDiagnostics(prog);
if (diags.length > 0) {
  console.log(JSON.stringify({ passed: false, stage: 'tsc_strict', diagnostics: diags.map(d => ts.flattenDiagnosticMessageText(d.messageText, '\n')) }));
  process.exit(0);
}

const src = fs.readFileSync(absTs, 'utf-8');
const out = ts.transpileModule(src, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } });
const mjsPath = path.join(workDir, 'webhook_router.mjs');
fs.writeFileSync(mjsPath, out.outputText, 'utf-8');

const mod = await import(pathToFileURL(mjsPath).href);
const { buildWebhookSecurityHeaders, signWebhookPayload, verifyWebhookSignature, WebhookRouter } = mod;

function assert(c, m) { if (!c) throw new Error(m); }

const secret = 'webhook-signing-secret-key-2026';
let now = 1_763_000_000_000;

const hdrs = buildWebhookSecurityHeaders();
assert(hdrs['cross-origin-opener-policy'] === 'same-origin', 'missing COOP');
assert(hdrs['cross-origin-embedder-policy'] === 'require-corp', 'missing COEP');
assert(hdrs['cross-origin-resource-policy'] === 'same-origin', 'missing CORP');
assert(hdrs['content-security-policy'].includes("require-trusted-types-for 'script'"), 'missing Trusted Types');
assert(!hdrs['content-security-policy'].includes('unsafe-inline'), 'unsafe-inline forbidden');

const bodyStr = JSON.stringify({
  eventId: 'evt_01',
  eventType: 'invoice.paid',
  occurredAtMs: now,
  tenantId: 'tenant_nordic',
  data: { amountUsd: 12000 },
});
const sig = signWebhookPayload(bodyStr, now, secret);
assert(verifyWebhookSignature(bodyStr, sig, secret, now + 1000) === true, 'valid signature rejected');
assert(verifyWebhookSignature(bodyStr, sig, secret, now + 600_000, 300_000) === false, 'expired replay accepted');

const router = new WebhookRouter({ signingSecret: secret, toleranceMs: 300_000, idempotencyTtlMs: 60_000, nowFn: () => now });
let dispatched = 0;
router.on('invoice.paid', () => { dispatched += 1; });

const r405 = router.handle({ method: 'GET', signatureHeader: sig, idempotencyKey: 'idem_01', rawBody: bodyStr });
assert(r405.status === 405 && r405.body.errorCode === 'METHOD_NOT_ALLOWED', '405 failed');

const r401 = router.handle({ method: 'POST', signatureHeader: `t=${now},v1=0000`, idempotencyKey: 'idem_01', rawBody: bodyStr });
assert(r401.status === 401 && r401.body.errorCode === 'INVALID_SIGNATURE', '401 failed');

const r200 = router.handle({ method: 'POST', signatureHeader: sig, idempotencyKey: 'idem_01', rawBody: bodyStr });
assert(r200.status === 200 && r200.body.statusText === 'processed' && dispatched === 1, 'first dispatch failed');

const rDup = router.handle({ method: 'POST', signatureHeader: sig, idempotencyKey: 'idem_01', rawBody: bodyStr });
assert(rDup.status === 200 && rDup.body.statusText === 'duplicate_ignored' && dispatched === 1, 'idempotency dedup failed');

console.log(JSON.stringify({ passed: true, tests_passed: 8 }));
""",
            encoding="utf-8",
        )

        proc = subprocess.run(
            [NODE_EXE, str(runner_mjs), str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return {"passed": False, "stage": "runtime_exception", "stderr": proc.stderr[:500]}
        try:
            return json.loads(proc.stdout.strip())
        except Exception as e:
            return {"passed": False, "stage": "json_parse", "error": str(e)}


def validate_holdout_submission(task_spec: dict, files_map: dict[str, str]) -> dict:
    if task_spec["category"] == "typescript_coding":
        return validate_h5_typescript_holdout(files_map)
    return validate_web_or_copy_holdout(task_spec, files_map)


def _build_synthetic_valid_web(task_spec: dict) -> dict[str, str]:
    lang = task_spec["language"]
    tid = task_spec["id"]
    if lang == "ru":
        q1, a1 = "Каков расчётный срок службы системы?", "Расчётный срок эксплуатации составляет 25 лет по ГОСТ."
        q2, a2 = "Как выполняется поверка датчиков?", "Межповерочный интервал составляет 24 месяца в аккредитованной лаборатории."
        q3, a3 = "Поддерживается ли автономная работа?", "Все узлы работают локально без облачных зависимостей."
        hero_text = "Инженерный комплекс «Север-Эталон» — прецизионная метрология и надёжность."
    else:
        q1, a1 = "What is the base operating temperature?", "The mixing chamber achieves 7 mK continuous base temperature."
        q2, a2 = "How is vibration isolation achieved?", "Dual bellows decoupling isolates pulse-tube cryocooler harmonics."
        q3, a3 = "What calibration standards are included?", "Each unit ships with NIST and METAS traceable calibration certificates."
        hero_text = "Precision cryogenic metrology and reference instrumentation."

    ld_json = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "Organization", "name": "Reference Lab"},
                {"@type": "WebSite", "name": "Reference Portal"},
                {"@type": "WebPage", "name": "Technical Specification"},
                {"@type": "Product", "name": "Model Alpha"},
                {"@type": "BreadcrumbList", "itemListElement": []},
                {
                    "@type": "FAQPage",
                    "mainEntity": [
                        {"@type": "Question", "name": q1, "acceptedAnswer": {"@type": "Answer", "text": a1}},
                        {"@type": "Question", "name": q2, "acceptedAnswer": {"@type": "Answer", "text": a2}},
                        {"@type": "Question", "name": q3, "acceptedAnswer": {"@type": "Answer", "text": a3}},
                    ],
                },
            ],
        },
        ensure_ascii=False,
    )

    html_doc = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <title>Technical Reference Portal</title>
  <meta name="description" content="Reference engineering specification.">
  <link rel="canonical" href="https://example.org/">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self' 'sha256-__CSP_STYLE__'; script-src 'self' 'sha256-__CSP_SCRIPT__'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; require-trusted-types-for 'script'">
  <script type="application/ld+json">{ld_json}</script>
  <style>
    :root {{
      --bg-main: oklch(0.97 0.01 85);
      --bg-surface: oklch(0.93 0.015 85);
      --text-main: oklch(0.14 0.015 255);
      --text-muted: oklch(0.32 0.015 255);
      --border-grid: oklch(0.24 0.015 255);
      --accent-primary: oklch(0.52 0.20 28);
    }}
    html {{ scroll-padding-top: 4.5rem; }}
    .hero {{ min-height: 100dvh; display: grid; grid-template-columns: repeat(12, 1fr); }}
    .sub {{ display: grid; grid-template-columns: subgrid; container-type: inline-size; }}
    @container (min-width: 400px) {{ .card {{ padding: 1.5rem; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
  </style>
</head>
<body>
  <header><nav><a href="#main">Nav</a></nav></header>
  <main id="main">
    <section class="hero">
      <h1>{hero_text}</h1>
      <svg viewBox="0 0 100 100" width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>
    </section>
    <section>
      <p>{q1} {a1}</p>
      <p>{q2} {a2}</p>
      <p>{q3} {a3}</p>
    </section>
  </main>
  <footer>Footer</footer>
  <script>
    document.addEventListener('DOMContentLoaded', () => {{
      const btn = document.querySelector('a');
      if (btn) btn.classList.add('active');
    }});
  </script>
</body>
</html>"""

    headers_txt = """# Cloudflare Pages headers
/*
  Content-Security-Policy: default-src 'none'; style-src 'self' 'sha256-__CSP_STYLE__'; script-src 'self' 'sha256-__CSP_SCRIPT__'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; require-trusted-types-for 'script'
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: require-corp
  Cross-Origin-Resource-Policy: same-origin
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
"""

    robots_txt = """User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

Sitemap: https://example.org/sitemap.xml
"""

    llms_txt = "# Reference Portal\n\n> Technical engineering portal.\n\n## Core Sections\n- [Specs](https://example.org/)\n"

    out = {
        "index.html": html_doc,
        "_headers": headers_txt,
        "robots.txt": robots_txt,
        "llms.txt": llms_txt,
    }
    if tid == "h1":
        out["zimage_prompts.json"] = json.dumps(
            {
                "prompts": [
                    {
                        "id": f"slot_{i}",
                        "target_section": "hero",
                        "output_path": f"assets/z_{i}.png",
                        "width": 1024,
                        "height": 1024,
                        "aspect_ratio": "1:1",
                        "steps": 9,
                        "exact_text_in_frame": f"CRYOFLUX STAGE {i}",
                        "prompt": (
                            f"Photorealistic technical studio photograph of gold-plated dilution refrigerator stage {i} "
                            f"with laser-engraved plate reading \"CRYOFLUX STAGE {i}\", sharp geometric lighting, "
                            "high-contrast monochrome precision metrology, 85mm macro lens, crisp metal texture."
                        ),
                    }
                    for i in (1, 2, 3)
                ]
            }
        )
    elif tid == "h3":
        out["copy_deck.md"] = (
            "# Brand Deck\n## 1. Matrix\n| Segment | Claim |\n|---|---|\n| Studio | 0.00018% THD |\n"
            "## 2. Rewrites\nConcrete acoustic metrics.\n## 3. Microcopy\n30-day audition.\n"
        )
    elif tid == "h4":
        out["copy_deck_ru.md"] = (
            "# Матрица аргументации «ГРАФИТ И СТАЛЬ»\n## 1. Сегменты\n| Роль | Выгода |\n|---|---|\n| R&D | ГОСТ IEC |\n"
            "## 2. Было / Стало\nТочные цифры нагрузки — 650 кг.\n## 3. Возражения\nСрок поставки — 5 дней.\n"
        )
    elif tid == "h6":
        out["audit_critique_ru.md"] = "\n".join(
            [f"## Дефект {i}\nАудит по стандарту WCAG 2.2 и W3C CSP — устранено в коде «КВАНТ-НАВИГАТОР»." for i in range(1, 9)]
        )
    return out


def _build_synthetic_valid_h5() -> dict[str, str]:
    return {
        "webhook_router.ts": """import { createHmac, timingSafeEqual } from "node:crypto";

export type WebhookEventType = "invoice.paid" | "deployment.completed" | "alert.triggered";

export interface WebhookEventPayload {
  eventId: string;
  eventType: WebhookEventType;
  occurredAtMs: number;
  tenantId: string;
  data: Readonly<Record<string, unknown>>;
}

export interface WebhookRequest {
  method: string;
  signatureHeader: string;
  idempotencyKey: string;
  rawBody: string;
}

export interface WebhookResponse {
  status: number;
  headers: Readonly<Record<string, string>>;
  body: {
    readonly ok: boolean;
    readonly statusText: "processed" | "duplicate_ignored" | "rejected";
    readonly eventId?: string;
    readonly errorCode?: string;
  };
}

export interface RouterConfig {
  signingSecret: string;
  toleranceMs?: number;
  idempotencyTtlMs?: number;
  nowFn?: () => number;
}

export function buildWebhookSecurityHeaders(): Record<string, string> {
  return {
    "content-security-policy": "default-src 'none'; script-src 'self' 'sha256-__CSP_SCRIPT__'; style-src 'self' 'sha256-__CSP_STYLE__'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; require-trusted-types-for 'script'",
    "cross-origin-opener-policy": "same-origin",
    "cross-origin-embedder-policy": "require-corp",
    "cross-origin-resource-policy": "same-origin",
    "strict-transport-security": "max-age=63072000; includeSubDomains; preload",
    "x-content-type-options": "nosniff",
    "content-type": "application/json; charset=utf-8",
  };
}

export function signWebhookPayload(rawBody: string, timestampMs: number, secret: string): string {
  const hex = createHmac("sha256", secret).update(`${timestampMs}.${rawBody}`).digest("hex");
  return `t=${timestampMs},v1=${hex}`;
}

export function verifyWebhookSignature(
  rawBody: string,
  signatureHeader: string,
  secret: string,
  nowMs: number,
  toleranceMs = 300_000
): boolean {
  const m = /^t=(\\d+),v1=([0-9a-f]{64})$/i.exec(signatureHeader.trim());
  if (!m) return false;
  const ts = Number(m[1]);
  const sigHex = m[2].toLowerCase();
  if (!Number.isSafeInteger(ts) || Math.abs(nowMs - ts) > toleranceMs) return false;
  const expected = createHmac("sha256", secret).update(`${ts}.${rawBody}`).digest("hex").toLowerCase();
  const a = Buffer.from(sigHex, "utf-8");
  const b = Buffer.from(expected, "utf-8");
  return a.length === b.length && timingSafeEqual(a, b);
}

const VALID_EVENTS = new Set<WebhookEventType>(["invoice.paid", "deployment.completed", "alert.triggered"]);

export class WebhookRouter {
  private readonly secret: string;
  private readonly toleranceMs: number;
  private readonly ttlMs: number;
  private readonly nowFn: () => number;
  private readonly seen: Map<string, number> = new Map();
  private readonly handlers: Map<WebhookEventType, Array<(ev: WebhookEventPayload) => void>> = new Map();

  constructor(config: RouterConfig) {
    if (!config || typeof config.signingSecret !== "string" || config.signingSecret.trim().length < 16) {
      throw new Error("Invalid signingSecret");
    }
    this.secret = config.signingSecret;
    this.toleranceMs = config.toleranceMs ?? 300_000;
    this.ttlMs = config.idempotencyTtlMs ?? 86_400_000;
    this.nowFn = config.nowFn ?? (() => Date.now());
  }

  on(eventType: WebhookEventType, handler: (event: WebhookEventPayload) => void): this {
    const list = this.handlers.get(eventType) ?? [];
    list.push(handler);
    this.handlers.set(eventType, list);
    return this;
  }

  handle(req: WebhookRequest): WebhookResponse {
    const headers = buildWebhookSecurityHeaders();
    if (!req || req.method.toUpperCase() !== "POST") {
      return { status: 405, headers, body: { ok: false, statusText: "rejected", errorCode: "METHOD_NOT_ALLOWED" } };
    }
    if (!req.idempotencyKey || req.idempotencyKey.trim().length < 4) {
      return { status: 400, headers, body: { ok: false, statusText: "rejected", errorCode: "MISSING_IDEMPOTENCY_KEY" } };
    }
    const now = this.nowFn();
    if (!verifyWebhookSignature(req.rawBody, req.signatureHeader, this.secret, now, this.toleranceMs)) {
      return { status: 401, headers, body: { ok: false, statusText: "rejected", errorCode: "INVALID_SIGNATURE" } };
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(req.rawBody);
    } catch {
      return { status: 400, headers, body: { ok: false, statusText: "rejected", errorCode: "INVALID_PAYLOAD" } };
    }
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return { status: 400, headers, body: { ok: false, statusText: "rejected", errorCode: "INVALID_PAYLOAD" } };
    }
    const obj = parsed as Record<string, unknown>;
    const eventId = typeof obj.eventId === "string" ? obj.eventId.trim() : "";
    const eventType = obj.eventType as WebhookEventType;
    const occurredAtMs = obj.occurredAtMs;
    const tenantId = typeof obj.tenantId === "string" ? obj.tenantId.trim() : "";
    const data = obj.data;
    if (
      !eventId ||
      !VALID_EVENTS.has(eventType) ||
      typeof occurredAtMs !== "number" ||
      !Number.isFinite(occurredAtMs) ||
      !tenantId ||
      typeof data !== "object" ||
      data === null ||
      Array.isArray(data)
    ) {
      return { status: 400, headers, body: { ok: false, statusText: "rejected", errorCode: "INVALID_PAYLOAD" } };
    }

    for (const [k, ts] of this.seen.entries()) {
      if (now - ts > this.ttlMs) this.seen.delete(k);
    }
    const idemKey = `k:${req.idempotencyKey.trim()}`;
    const evtKey = `e:${eventId}`;
    if (this.seen.has(idemKey) || this.seen.has(evtKey)) {
      return { status: 200, headers, body: { ok: true, statusText: "duplicate_ignored", eventId } };
    }
    this.seen.set(idemKey, now);
    this.seen.set(evtKey, now);

    const payload: WebhookEventPayload = {
      eventId,
      eventType,
      occurredAtMs,
      tenantId,
      data: data as Readonly<Record<string, unknown>>,
    };
    for (const fn of this.handlers.get(eventType) ?? []) {
      fn(payload);
    }
    return { status: 200, headers, body: { ok: true, statusText: "processed", eventId } };
  }
}
"""
    }


def run_self_tests() -> int:
    with open(TASKS_HOLDOUT_JSON, "r", encoding="utf-8") as fh:
        holdout_data = json.load(fh)
    tasks = holdout_data.get("tasks", [])
    assert len(tasks) == 6, f"Expected 6 holdout tasks, got {len(tasks)}"

    en_tasks = [t for t in tasks if t["language"] == "en"]
    ru_tasks = [t for t in tasks if t["language"] == "ru"]
    assert len(en_tasks) == 3 and len(ru_tasks) == 3, "Holdout must contain 3 EN and 3 RU tasks"

    if SUITE_TASKS_JSON.exists():
        with open(SUITE_TASKS_JSON, "r", encoding="utf-8") as fh:
            suite_ids = {t["id"] for t in json.load(fh).get("tasks", [])}
        holdout_ids = {t["id"] for t in tasks}
        assert suite_ids.isdisjoint(holdout_ids), "Holdout IDs must be disjoint from suite task IDs"

    results_summary = []

    for t in tasks:
        tid = t["id"]
        # 1. Valid synthetic case -> MUST PASS
        valid_files = _build_synthetic_valid_h5() if tid == "h5" else _build_synthetic_valid_web(t)
        res_valid = validate_holdout_submission(t, valid_files)
        assert res_valid["passed"] is True, f"Valid synthetic test failed for {tid}: {res_valid}"

        # 2. Broken synthetic case -> MUST FAIL
        broken_files = dict(valid_files)
        if tid == "h1":
            # Inject unsafe-inline CSP & broken zimage_prompts.json
            broken_files["index.html"] = broken_files["index.html"].replace("sha256-__CSP_SCRIPT__", "unsafe-inline")
        elif tid == "h2":
            # Inject trailing */ in _headers and legacy 100vh
            broken_files["_headers"] = broken_files["_headers"] + "\n*/\n"
            broken_files["index.html"] = broken_files["index.html"].replace("100dvh", "100vh")
        elif tid == "h3":
            # Inject EN AI-slop words & Tailwind classes
            broken_files["index.html"] = broken_files["index.html"].replace(
                "<h1>", '<h1 class="bg-purple-600 text-2xl rounded-xl">Delve into our seamless testament: '
            )
        elif tid == "h4":
            # Inject RU machine-translation calques & low contrast
            broken_files["copy_deck_ru.md"] += "\nПогрузитесь в мир и откройте для себя бесшовный инновационный подход.\n"
        elif tid == "h5":
            # Inject explicit `any` and broken COOP header in TypeScript
            broken_files["webhook_router.ts"] = broken_files["webhook_router.ts"].replace(
                "parsed: unknown", "parsed: any"
            )
        elif tid == "h6":
            # Inject JS .style mutation & incomplete critique
            broken_files["index.html"] = broken_files["index.html"].replace(
                "btn.classList.add('active')", "btn.style.color = 'red'"
            )
            broken_files["audit_critique_ru.md"] = "## Дефект 1 только"

        res_broken = validate_holdout_submission(t, broken_files)
        assert res_broken["passed"] is False, f"Broken synthetic test was NOT caught for {tid}: {res_broken}"

        results_summary.append(
            {
                "task_id": tid,
                "language": t["language"],
                "category": t["category"],
                "synthetic_valid_passed": res_valid["passed"],
                "synthetic_broken_rejected": not res_broken["passed"],
            }
        )

    print(
        json.dumps(
            {
                "holdout_schema_valid": True,
                "total_tasks": len(tasks),
                "en_count": len(en_tasks),
                "ru_count": len(ru_tasks),
                "synthetic_valid_cases_passed": "6/6",
                "synthetic_broken_cases_rejected": "6/6",
                "results": results_summary,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate SmartLLM Blind Holdout Tasks")
    ap.add_argument("--self-test", action="store_true", help="Run synthetic valid + broken validator self-tests")
    args = ap.parse_args()
    return run_self_tests()


if __name__ == "__main__":
    sys.exit(main())
