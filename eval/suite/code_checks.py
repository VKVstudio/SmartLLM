#!/usr/bin/env python3
"""Stage A Deterministic Web, Security, SEO/AEO/GEO, OKLCH, and CSS/HTML Code Checks (`code_checks.py`).

Fixes all code/security/SEO/CSS bugs identified in `TZ_carbon_orchestrator.md §1.5` and
`research/deep_dive/04_linux_env_and_harness_verified.md`:
- `NEW-BUG-01`: Grades RAW model `html_code` and `_headers` BEFORE `apply_csp_postprocessor()`.
  Postprocessor only substitutes `'sha256-__CSP_STYLE__'` / `'sha256-__CSP_SCRIPT__'` placeholders
  without injecting missing `<meta>` CSP tags or stripping `object-src 'none'` /
  `require-trusted-types-for 'script'`.
- `CODE-01`: `_parse_cloudflare_headers` merges all valid Cloudflare routes matching `/index.html`
  (`/*`, `/*.html`, `/index.html`), rejects JSON and C `/* ... */` comments, and validates RFC 6797
  HSTS `max-age >= 31536000` + `includeSubDomains`.
- Bare `unsafe-inline` check: rejects both `'unsafe-inline'` and unquoted `unsafe-inline` in
  `script-src`, `style-src`, and `default-src`.
- `100vh` check: flags bare `100vh` when not paired with `100dvh` or `100svh`.
- `NEW-BUG-04`: Gamut-maps OKLCH via CSS Color 4 chroma binary search and evaluates semantic
  background-vs-foreground token pairs alongside max contrast.
- Stage A additions: `SEO-ROBOT-AI` (AI training vs search crawlers in `robots.txt`), `SEO-HREFLANG`
  (`hreflang` + `canonical`), `SEC-ISOLATE` (`COOP: same-origin`, `COEP`, `CORP`), `SEC-TRUST-TYP`
  (`object-src 'none'`, `require-trusted-types-for 'script'`), `application/ld+json` `@graph` +
  verbatim FAQ, and Tailwind utility class ban compliance.
"""

from __future__ import annotations

import base64
import hashlib
import html as html_lib
import json
import math
import os
import re
import shutil
import urllib.parse
from html.parser import HTMLParser
from typing import Any


# ---------------------------------------------------------------------------
# 1. OKLCH Color Space (CSS Color 4 Gamut Mapping + Semantic Contrast)
# ---------------------------------------------------------------------------

def _oklch_to_lin_srgb_unclamped(L: float, C: float, H_deg: float) -> tuple[float, float, float]:
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
    return (r_lin, g_lin, b_lin)


def _in_srgb_gamut(r_lin: float, g_lin: float, b_lin: float, eps: float = 1e-4) -> bool:
    return (-eps <= r_lin <= 1.0 + eps) and (-eps <= g_lin <= 1.0 + eps) and (-eps <= b_lin <= 1.0 + eps)


def oklch_to_srgb(L: float, C: float, H_deg: float) -> tuple[float, float, float]:
    """Convert OKLCH to linear sRGB (0..1) with CSS Color 4 chroma reduction gamut mapping."""
    if L > 1.0:
        L = L / 100.0
    if L <= 0.0:
        return (0.0, 0.0, 0.0)
    if L >= 1.0:
        return (1.0, 1.0, 1.0)

    r_lin, g_lin, b_lin = _oklch_to_lin_srgb_unclamped(L, C, H_deg)
    if not _in_srgb_gamut(r_lin, g_lin, b_lin) and C > 0.0:
        lo, hi = 0.0, C
        for _ in range(16):
            mid = 0.5 * (lo + hi)
            rm, gm, bm = _oklch_to_lin_srgb_unclamped(L, mid, H_deg)
            if _in_srgb_gamut(rm, gm, bm):
                lo = mid
            else:
                hi = mid
        r_lin, g_lin, b_lin = _oklch_to_lin_srgb_unclamped(L, lo, H_deg)

    def clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    return (clamp01(r_lin), clamp01(g_lin), clamp01(b_lin))


def relative_luminance_from_lin_rgb(r_lin: float, g_lin: float, b_lin: float) -> float:
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(lum1: float, lum2: float) -> float:
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


_BG_TOKEN_RE = re.compile(
    r"^--(?:bg|background|surface|canvas|paper|panel|card|page)(?:$|[-_](?!text|fg|ink|border|line|accent))",
    re.IGNORECASE,
)
_FG_PRIMARY_TOKEN_RE = re.compile(
    r"^--(?:text|fg|foreground|ink|body|copy|heading|title)(?:$|[-_](?:primary|main|base|default|0|1|dark|light|color)?$)",
    re.IGNORECASE,
)
_FG_MUTED_TOKEN_RE = re.compile(
    r"^--(?:muted|subtext|text[-_]muted|text[-_]secondary|fg[-_]muted|ink[-_]muted|secondary[-_]text)",
    re.IGNORECASE,
)


def parse_oklch_tokens(css_text: str) -> dict[str, dict[str, Any]]:
    tokens: dict[str, dict[str, Any]] = {}
    pattern = re.compile(
        r"(--[A-Za-z0-9_\-]+)\s*:\s*oklch\(\s*([0-9.]+%?)\s+([0-9.]+)\s+([0-9.]+)(?:\s*/\s*([0-9.]+%?))?\s*\)",
        re.IGNORECASE,
    )
    for name, l_str, c_str, h_str, alpha in pattern.findall(css_text):
        if alpha:
            continue
        L = float(l_str.rstrip("%")) / (100.0 if l_str.endswith("%") else 1.0)
        C = float(c_str)
        H = float(h_str)
        r_l, g_l, b_l = oklch_to_srgb(L, C, H)
        lum = relative_luminance_from_lin_rgb(r_l, g_l, b_l)
        tokens[name] = {
            "raw": f"oklch({l_str} {c_str} {h_str})",
            "L": round(L, 4),
            "C": round(C, 4),
            "H": round(H, 2),
            "luminance": round(lum, 4),
        }
    return tokens


def evaluate_oklch_compliance(css_text: str | list[str], extra_css: str = "") -> dict[str, Any]:
    """Evaluate OKLCH token usage, all-pairs contrast, and semantic bg-vs-text contrast (NEW-BUG-04)."""
    joined_css = "\n".join(css_text) if isinstance(css_text, list) else str(css_text or "")
    if extra_css:
        joined_css = joined_css + "\n" + str(extra_css)
    tokens = parse_oklch_tokens(joined_css)
    all_pairs: dict[str, float] = {}
    t_names = list(tokens.keys())
    for i in range(len(t_names)):
        for j in range(i + 1, len(t_names)):
            n1, n2 = t_names[i], t_names[j]
            cr = contrast_ratio(tokens[n1]["luminance"], tokens[n2]["luminance"])
            if cr >= 4.5:
                all_pairs[f"{n1} vs {n2}"] = cr
    max_contrast = max(all_pairs.values()) if all_pairs else 0.0

    bg_names = [n for n in t_names if _BG_TOKEN_RE.search(n)]
    fg_names = [n for n in t_names if _FG_PRIMARY_TOKEN_RE.search(n)]
    muted_names = [n for n in t_names if _FG_MUTED_TOKEN_RE.search(n)]

    semantic_pairs: dict[str, float] = {}
    for b in bg_names:
        for f in fg_names:
            semantic_pairs[f"{b} vs {f}"] = contrast_ratio(tokens[b]["luminance"], tokens[f]["luminance"])

    muted_pairs: dict[str, float] = {}
    for b in bg_names:
        for m in muted_names:
            muted_pairs[f"{b} vs {m}"] = contrast_ratio(tokens[b]["luminance"], tokens[m]["luminance"])

    # Primary bg vs primary text (first matched --bg / --surface against first --text / --fg / --ink)
    primary_semantic_contrast = max(semantic_pairs.values()) if semantic_pairs else max_contrast
    min_muted_contrast = min(muted_pairs.values()) if muted_pairs else None

    return {
        "token_count": len(tokens),
        "max_contrast_pair": max_contrast,
        "max_contrast_ratio_est": max_contrast,
        "semantic_text_bg_contrast": primary_semantic_contrast,
        "semantic_bg_fg_min_contrast": primary_semantic_contrast,
        "min_muted_bg_contrast": min_muted_contrast,
        "passes_aaa_7_to_1": primary_semantic_contrast >= 7.0,
        "passes_aa_4_5_to_1": primary_semantic_contrast >= 4.5,
        "semantic_bg_fg_contrast_passed": primary_semantic_contrast >= 4.5,
        "passes_any_pair_aaa_7_to_1": max_contrast >= 7.0,
        "semantic_pairs": semantic_pairs,
        "tokens": tokens,
    }


# ---------------------------------------------------------------------------
# 2. Tailwind Ban & Modern CSS (`100dvh`/`100svh` vs `100vh`) Checks
# ---------------------------------------------------------------------------

_TAILWIND_CLASS_PATTERNS = re.compile(
    r"\b(?:"
    r"bg-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|[1-9]00|950)|"
    r"text-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|[1-9]00|950)|"
    r"text-(?:xs|sm|base|lg|xl|[2-9]xl)|"
    r"font-(?:thin|extralight|light|normal|medium|semibold|bold|extrabold|black)|"
    r"rounded-(?:none|sm|md|lg|xl|2xl|3xl|full)|"
    r"shadow-(?:sm|md|lg|xl|2xl|inner|none)|"
    r"p[xytblr]?-(?:0\.5|1\.5|2\.5|3\.5|[0-9]{1,2})|"
    r"m[xytblr]?-(?:0\.5|1\.5|2\.5|3\.5|[0-9]{1,2}|auto)|"
    r"grid-cols-(?:[1-9]|1[0-2]|none)|"
    r"gap-(?:0\.5|1\.5|2\.5|3\.5|[0-9]{1,2})|"
    r"items-(?:start|end|center|baseline|stretch)|"
    r"justify-(?:start|end|center|between|around|evenly)"
    r")\b"
)
_TAILWIND_CDN_RE = re.compile(r"cdn\.tailwindcss\.com|@tailwind\s+(?:base|components|utilities)", re.IGNORECASE)
_CLASS_ATTR_RE = re.compile(r'\bclass\s*=\s*(["\'])(.*?)\1', re.IGNORECASE | re.DOTALL)


def check_tailwind_ban(html_text: str, css_text: str | list[str] = "") -> dict[str, Any]:
    """Verify absence of Tailwind CDN scripts/directives and utility-class chains."""
    joined_css = "\n".join(css_text) if isinstance(css_text, list) else str(css_text or "")
    cdn_hits = _TAILWIND_CDN_RE.findall(html_text + "\n" + joined_css)
    utility_hits: list[str] = []
    for _quote, cls_val in _CLASS_ATTR_RE.findall(html_text):
        matches = _TAILWIND_CLASS_PATTERNS.findall(cls_val)
        # Require >= 2 utility tokens in a single class="" attribute to avoid false positives on semantic BEM names
        if len(matches) >= 2:
            utility_hits.extend(matches)
    passed = (len(cdn_hits) == 0) and (len(utility_hits) == 0)
    return {
        "tailwind_ban_passed": passed,
        "tailwind_cdn_hits": cdn_hits,
        "tailwind_utility_hits_count": len(utility_hits),
        "tailwind_utility_sample": list(dict.fromkeys(utility_hits))[:10],
    }


_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_BARE_100VH_RE = re.compile(r"(?<![0-9.])100vh\b", re.IGNORECASE)
_MODERN_DVH_SVH_RE = re.compile(r"(?<![0-9.])100(?:dvh|svh|lvh)\b", re.IGNORECASE)


def check_viewport_vh_hygiene(css_text: str | list[str], extra_css: str = "") -> dict[str, Any]:
    """Check `100vh` usage: bare `100vh` without `100dvh`/`100svh` progressive override fails mobile viewport hygiene."""
    joined_css = "\n".join(css_text) if isinstance(css_text, list) else str(css_text or "")
    if extra_css:
        joined_css = joined_css + "\n" + str(extra_css)
    clean_css = _CSS_COMMENT_RE.sub(" ", joined_css)
    vh_hits = _BARE_100VH_RE.findall(clean_css)
    dvh_hits = _MODERN_DVH_SVH_RE.findall(clean_css)
    has_unfallback_100vh = len(vh_hits) > 0 and len(dvh_hits) == 0
    return {
        "has_100vh": len(vh_hits) > 0,
        "has_100dvh_or_svh": len(dvh_hits) > 0,
        "has_unfallback_100vh": has_unfallback_100vh,
        "bare_100vh_count": len(vh_hits) if has_unfallback_100vh else 0,
        "vh_hygiene_passed": not has_unfallback_100vh,
        "viewport_vh_passed": not has_unfallback_100vh,
    }


# ---------------------------------------------------------------------------
# 3. CSP & Security Headers Parsing, Raw Auditing & Packaging Postprocessor
# ---------------------------------------------------------------------------

def sha256_b64(text: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


_META_CSP_RE = re.compile(
    r'(<meta\s+[^>]*http-equiv\s*=\s*["\']Content-Security-Policy["\'][^>]*>)',
    re.IGNORECASE | re.DOTALL,
)
_HEADER_CSP_LINE_RE = re.compile(r"(^[ \t]*Content-Security-Policy:\s*)(.+?)[ \t]*$", re.IGNORECASE | re.MULTILINE)
_UNSAFE_INLINE_TOKEN_RE = re.compile(r"(?:^|[\s;'\"])unsafe-inline(?:$|[\s;'\"])", re.IGNORECASE)
_UNSAFE_EVAL_TOKEN_RE = re.compile(r"(?:^|[\s;'\"])unsafe-eval(?:$|[\s;'\"])", re.IGNORECASE)


def parse_csp_directives(csp_string: str) -> dict[str, list[str]]:
    """Parse a CSP header/meta content string into `{directive_lower: [tokens]}`."""
    directives: dict[str, list[str]] = {}
    if not csp_string:
        return directives
    for part in csp_string.split(";"):
        stripped = part.strip()
        if not stripped:
            continue
        tokens = stripped.split()
        name = tokens[0].lower()
        directives[name] = tokens[1:]
    return directives


def audit_csp_policy_string(csp_string: str, is_header: bool = False) -> dict[str, Any]:
    """Audit a raw or packaged CSP string for unsafe-inline (quoted or bare), hashes, and Trusted Types."""
    directives = parse_csp_directives(csp_string)
    script_src = " ".join(directives.get("script-src", directives.get("default-src", [])))
    style_src = " ".join(directives.get("style-src", directives.get("default-src", [])))
    object_src = [t.strip("'\"").lower() for t in directives.get("object-src", directives.get("default-src", []))]
    base_uri = [t.strip("'\"").lower() for t in directives.get("base-uri", [])]
    frame_anc = [t.strip("'\"").lower() for t in directives.get("frame-ancestors", [])]
    req_tt = [t.strip("'\"").lower() for t in directives.get("require-trusted-types-for", [])]

    has_unsafe_inline_any = bool(_UNSAFE_INLINE_TOKEN_RE.search(csp_string))
    has_unsafe_inline_script = bool(_UNSAFE_INLINE_TOKEN_RE.search(script_src))
    has_unsafe_inline_style = bool(_UNSAFE_INLINE_TOKEN_RE.search(style_src))
    has_unsafe_eval = bool(_UNSAFE_EVAL_TOKEN_RE.search(csp_string))

    has_style_placeholder = "__CSP_STYLE__" in csp_string
    has_script_placeholder = "__CSP_SCRIPT__" in csp_string
    sha256_tokens = re.findall(r"sha256-[A-Za-z0-9+/=_\-]+", csp_string)

    has_object_src_none = "none" in object_src
    has_base_uri_restricted = ("none" in base_uri) or ("self" in base_uri)
    has_frame_ancestors_none = "none" in frame_anc
    has_trusted_types = "script" in req_tt

    strict_passed = (
        bool(csp_string.strip())
        and not has_unsafe_inline_any
        and not has_unsafe_eval
        and (len(sha256_tokens) > 0 or "'self'" in script_src.lower() or "'none'" in script_src.lower())
        and (not is_header or has_frame_ancestors_none)
    )

    return {
        "present": bool(csp_string.strip()),
        "has_unsafe_inline": has_unsafe_inline_any,
        "has_unsafe_inline_script": has_unsafe_inline_script,
        "has_unsafe_inline_style": has_unsafe_inline_style,
        "script_no_unsafe_inline": not has_unsafe_inline_script,
        "style_no_unsafe_inline": not has_unsafe_inline_style,
        "has_unsafe_eval": has_unsafe_eval,
        "has_style_placeholder": has_style_placeholder,
        "has_script_placeholder": has_script_placeholder,
        "sha256_tokens_count": len(sha256_tokens),
        "has_object_src_none": has_object_src_none,
        "has_base_uri_restricted": has_base_uri_restricted,
        "has_frame_ancestors_none": has_frame_ancestors_none,
        "has_require_trusted_types": has_trusted_types,
        "has_trusted_types": has_trusted_types,
        "strict_csp_passed": strict_passed,
        "directives": directives,
    }


def _route_matches_index_html(route: str) -> bool:
    """Return True if a Cloudflare Pages `_headers` route pattern applies to `/index.html` or `/`."""
    r = route.strip()
    if r in ("/*", "/", "/index.html", "/*.html", "/index*"):
        return True
    if r.startswith("/*") and not r.endswith("*/"):
        ext_part = r[2:]
        if not ext_part or ext_part == ".html":
            return True
    return False


def _parse_cloudflare_headers(h_text: str) -> dict[str, Any]:
    """Parse Cloudflare Pages `_headers` syntax.

    Fixes `CODE-01` (`04_linux_env_and_harness_verified.md:30,116`):
    - Rejects JSON (`{`, `[`, `"`) and C block comments (`/* ... */` or trailing `*/`).
    - Parses all valid route blocks (`/*`, `/index.html`, `/*.html`, `/*.css`, etc.) into `routes`.
    - Merges all route blocks that match `/index.html` into `headers` (so headers placed under
      `/index.html` or `/*.html` are preserved rather than silently discarded!).
    """
    lines = h_text.splitlines()
    routes: dict[str, dict[str, str]] = {}
    merged_index_headers: dict[str, str] = {}
    all_route_headers: dict[str, str] = {}
    current_route: str | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Reject C-style block comments (`/* ... */` or closing `*/`) and JSON syntax
        if (
            stripped.startswith(("{", "}", "[", "]", '"'))
            or stripped.endswith("*/")
            or ("/*" in stripped and "*/" in stripped)
        ):
            return {
                "has_route_rule": False,
                "headers": {},
                "routes": {},
                "format_error": "invalid_comment_or_json_syntax",
            }
        if line[0] not in (" ", "\t"):
            # Unindented route line: must start with `/` and must not contain `: ` header syntax
            if not stripped.startswith("/") or stripped.endswith(":"):
                return {
                    "has_route_rule": False,
                    "headers": {},
                    "routes": {},
                    "format_error": "invalid_route_syntax",
                }
            current_route = stripped
            routes.setdefault(current_route, {})
            continue

        if current_route is None:
            return {
                "has_route_rule": False,
                "headers": {},
                "routes": {},
                "format_error": "indented_header_without_route",
            }

        m = re.match(r"^[ \t]+([A-Za-z0-9\-]+)[ \t]*:[ \t]*(.+?)[ \t]*$", line)
        if m:
            h_name = m.group(1).lower()
            h_val = m.group(2).strip()
            # Reject inline `#` comments or trailing `*/` inside header values
            if h_val.endswith("*/"):
                return {
                    "has_route_rule": False,
                    "headers": {},
                    "routes": {},
                    "format_error": "invalid_comment_or_json_syntax",
                }
            routes[current_route][h_name] = h_val
            all_route_headers[h_name] = h_val
            if _route_matches_index_html(current_route):
                merged_index_headers[h_name] = h_val

    has_index_route = any(_route_matches_index_html(r) for r in routes)
    return {
        "has_route_rule": has_index_route,
        "headers": merged_index_headers,
        "all_route_headers": all_route_headers,
        "routes": routes,
    }


def check_hsts_header(hsts_value: str) -> dict[str, Any]:
    """Validate RFC 6797 HSTS header (`max-age >= 31536000` + `includeSubDomains`)."""
    v = (hsts_value or "").lower()
    m = re.search(r"max-age\s*=\s*(\d+)", v)
    max_age = int(m.group(1)) if m else 0
    has_subdomains = "includesubdomains" in v
    has_preload = "preload" in v
    passed = (max_age >= 31536000) and has_subdomains
    return {
        "present": bool(v),
        "max_age": max_age,
        "has_include_subdomains": has_subdomains,
        "has_preload": has_preload,
        "passed": passed,
    }


def check_cross_origin_isolation_headers(hdrs: dict[str, str]) -> dict[str, Any]:
    """Validate `SEC-ISOLATE`: COOP (`same-origin`), COEP (`require-corp`/`credentialless`), CORP (`same-origin`/`same-site`)."""
    coop_v = (hdrs.get("cross-origin-opener-policy") or "").strip().lower()
    coep_v = (hdrs.get("cross-origin-embedder-policy") or "").strip().lower()
    corp_v = (hdrs.get("cross-origin-resource-policy") or "").strip().lower()

    coop_ok = coop_v == "same-origin"
    coep_ok = coep_v in ("require-corp", "credentialless")
    corp_ok = corp_v in ("same-origin", "same-site")

    return {
        "coop": coop_v,
        "coep": coep_v,
        "corp": corp_v,
        "coop_same_origin": coop_ok,
        "coep_valid": coep_ok,
        "corp_valid": corp_ok,
        "full_isolation_passed": coop_ok and coep_ok and corp_ok,
    }


# ---------------------------------------------------------------------------
# 4. SEO / AEO / GEO Checks (`robots.txt` AI Crawlers, `hreflang`, `JSON-LD`)
# ---------------------------------------------------------------------------

_AI_TRAINING_BOTS = ("gptbot", "claudebot", "google-extended", "ccbot", "anthropic-ai", "bytespider")
_AI_SEARCH_BOTS = ("oai-searchbot", "claude-searchbot", "perplexitybot", "applebot-extended")


def check_robots_txt_ai_crawlers(robots_text: str) -> dict[str, Any]:
    """Validate `SEO-ROBOT-AI` (`robots.txt` user-agent stanzas, AI crawler rules, and `Sitemap:`)."""
    if not robots_text or not robots_text.strip():
        return {
            "valid_syntax": False,
            "user_agents": [],
            "has_wildcard_agent": False,
            "ai_training_bots_mentioned": [],
            "ai_search_bots_mentioned": [],
            "has_ai_crawler_policy": False,
            "has_sitemap": False,
        }

    agents: list[str] = []
    has_sitemap = False
    has_allow_or_disallow = False

    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k_low = k.strip().lower()
        v_clean = v.strip()
        if k_low == "user-agent" and v_clean:
            agents.append(v_clean.lower())
        elif k_low in ("allow", "disallow"):
            has_allow_or_disallow = True
        elif k_low == "sitemap" and v_clean:
            has_sitemap = True

    train_mentioned = sorted({b for b in _AI_TRAINING_BOTS if any(b in a for a in agents)})
    search_mentioned = sorted({b for b in _AI_SEARCH_BOTS if any(b in a for a in agents)})
    has_wildcard = "*" in agents

    return {
        "valid_syntax": bool(agents) and has_allow_or_disallow,
        "user_agents": agents,
        "has_wildcard_agent": has_wildcard,
        "ai_training_bots_mentioned": train_mentioned,
        "ai_search_bots_mentioned": search_mentioned,
        "has_ai_crawler_policy": len(train_mentioned) > 0 or len(search_mentioned) > 0,
        "has_sitemap": has_sitemap,
    }


def check_hreflang_and_canonical(link_tags: list[dict[str, str]]) -> dict[str, Any]:
    """Validate `SEO-HREFLANG` and `<link rel="canonical">` tags."""
    canonical_hrefs: list[str] = []
    hreflangs: dict[str, str] = {}

    for lnk in link_tags:
        rel_tokens = {t.lower() for t in (lnk.get("rel") or "").split()}
        href = (lnk.get("href") or "").strip()
        if "canonical" in rel_tokens and href:
            canonical_hrefs.append(href)
        if "alternate" in rel_tokens and lnk.get("hreflang"):
            hl = lnk["hreflang"].strip().lower()
            hreflangs[hl] = href

    has_en = any(k == "en" or k.startswith("en-") for k in hreflangs)
    has_ru = any(k == "ru" or k.startswith("ru-") for k in hreflangs)
    has_x_default = "x-default" in hreflangs

    return {
        "has_canonical": len(canonical_hrefs) > 0,
        "canonical_href": canonical_hrefs[0] if canonical_hrefs else None,
        "hreflang_tags": hreflangs,
        "has_hreflang": len(hreflangs) > 0,
        "has_bilingual_en_ru_hreflang": has_en and has_ru,
        "has_x_default_hreflang": has_x_default,
    }


def strip_code_tags_and_markup(html_text: str) -> str:
    """Remove `<script>`/`<style>` blocks (including unclosed EOF blocks) and HTML tags."""
    no_code = re.sub(
        r"<(script|style)\b[^>]*>(?:.*?</\1>|.*$)",
        " ",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", no_code))).strip()


def check_json_ld_blocks(jsonld_blocks: list[str], html_text: str) -> dict[str, Any]:
    """Validate `<script type="application/ld+json">` `@graph` entities and verbatim visible FAQ."""
    def _norm_txt(s: str) -> str:
        return re.sub(r"\s+", " ", html_lib.unescape(s or "")).strip()

    report: dict[str, Any] = {
        "blocks_count": len(jsonld_blocks),
        "valid_json": False,
        "graph_types": [],
        "faq_all_verbatim": False,
    }
    if not jsonld_blocks:
        return report

    try:
        graph: list[Any] = []
        for blk in jsonld_blocks:
            parsed_ld = json.loads(blk)
            if isinstance(parsed_ld, list):
                graph.extend(parsed_ld)
            elif isinstance(parsed_ld, dict):
                if isinstance(parsed_ld.get("@graph"), list):
                    graph.extend(parsed_ld["@graph"])
                elif parsed_ld.get("@type"):
                    graph.append(parsed_ld)
        report["valid_json"] = True
        types: list[str] = []
        faq_items: list[dict[str, str]] = []
        invalid_faq_schema = False
        for node in graph:
            if not isinstance(node, dict):
                continue
            t = node.get("@type")
            if isinstance(t, list):
                types.extend(str(x) for x in t)
            elif t:
                types.append(str(t))
            if t == "FAQPage" or (isinstance(t, list) and "FAQPage" in t):
                me = node.get("mainEntity", [])
                if isinstance(me, dict):
                    me = [me]
                if not isinstance(me, list):
                    invalid_faq_schema = True
                    continue
                for q in me:
                    if not isinstance(q, dict):
                        invalid_faq_schema = True
                        continue
                    q_name = _norm_txt(str(q.get("name") or ""))
                    ans_obj = q.get("acceptedAnswer")
                    if isinstance(ans_obj, dict):
                        raw_ans = ans_obj.get("text")
                        if not isinstance(raw_ans, str):
                            invalid_faq_schema = True
                        a_text = _norm_txt(str(raw_ans or ""))
                    else:
                        invalid_faq_schema = True
                        a_text = ""
                    faq_items.append({"q": q_name, "a": a_text})

        visible_text = strip_code_tags_and_markup(html_text)
        report["graph_types"] = types
        report["has_all_4_types"] = all(
            req_t in types for req_t in ("Organization", "Product", "FAQPage", "BreadcrumbList")
        )
        report["product_count"] = sum(1 for x in types if x == "Product")
        report["invalid_faq_schema"] = invalid_faq_schema
        verbatim_matches = []
        for item in faq_items:
            q_in_html = bool(item["q"]) and (item["q"] in visible_text)
            a_in_html = bool(item["a"]) and (item["a"] in visible_text)
            verbatim_matches.append({"q": item["q"][:120], "q_in_html": q_in_html, "a_in_html": a_in_html})
        report["faq_count"] = len(faq_items)
        report["faq_matches"] = verbatim_matches
        report["faq_all_verbatim"] = (
            not invalid_faq_schema
            and bool(verbatim_matches)
            and all(m["q_in_html"] and m["a_in_html"] for m in verbatim_matches)
        )
    except Exception as e:
        report["parse_error"] = str(e)

    return report


# ---------------------------------------------------------------------------
# 5. HTML Structural Parser & Packaging-Only CSP Postprocessor (NEW-BUG-01 Fix)
# ---------------------------------------------------------------------------

def normalize_data_css_and_empty_styles(raw_html: str) -> str:
    """Strip no-op stylesheet links/tags and convert `data:text/css` links into inline `<style>`."""
    out = re.sub(
        r'<link\s+[^>]*href\s*=\s*["\']data:text/css,\s*["\'][^>]*>\r?\n?',
        "",
        raw_html,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"<style>\s*</style>\r?\n?",
        "",
        out,
        flags=re.IGNORECASE,
    )

    def _data_css_to_style(match: re.Match) -> str:
        decoded_css = urllib.parse.unquote(match.group(2))
        return f"<style>{decoded_css}</style>"

    return re.sub(
        r'<link\s+[^>]*href\s*=\s*(["\'])data:text/css,(.*?)\1[^>]*>',
        _data_css_to_style,
        out,
        flags=re.IGNORECASE | re.DOTALL,
    )


def csp_skeleton_html(text: str) -> str:
    """Return canonical HTML skeleton independent of CSP meta tag & whitespace formatting."""
    norm = normalize_data_css_and_empty_styles(text)
    stripped = _META_CSP_RE.sub("", norm)
    collapsed = re.sub(r"\s+", " ", stripped).strip()
    return re.sub(r">\s+<", "><", collapsed)


def csp_skeleton_headers(text: str) -> str:
    """Return canonical `_headers` skeleton independent of Content-Security-Policy line value."""
    no_csp = _HEADER_CSP_LINE_RE.sub("", text)
    return "\n".join(ln.rstrip() for ln in no_csp.splitlines() if ln.strip())


class StructHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.styles: list[str] = []
        self.scripts: list[dict[str, str]] = []
        self.inline_style_attrs: list[str] = []
        self.inline_event_handlers: list[tuple[str, str]] = []
        self.meta_csp: str | None = None
        self.meta_tags: list[dict[str, str]] = []
        self.link_tags: list[dict[str, str]] = []
        self.title_text: str = ""
        self.html_lang: str = ""
        self.h1_count: int = 0
        self.landmarks: set[str] = set()
        self.imgs: list[dict[str, str]] = []
        self.svgs: list[dict[str, str]] = []
        self.svg_uses: list[str] = []
        self.media_srcs: list[tuple[str, str]] = []
        self.a_hrefs: list[str] = []
        self.canvases: list[dict[str, str]] = []
        self.inputs: list[dict[str, str]] = []
        self.labels: list[dict[str, str]] = []
        self._in_tag: str | None = None
        self._in_script_type: str | None = None
        self._in_script_src: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: (v or "") for k, v in attrs if k}
        t = tag.lower()
        if t == "html" and attr_dict.get("lang"):
            self.html_lang = attr_dict["lang"].strip()
        if "style" in attr_dict and attr_dict["style"]:
            self.inline_style_attrs.append(attr_dict["style"])
        for k in attr_dict:
            if k.lower().startswith("on") and len(k) > 2:
                self.inline_event_handlers.append((t, k.lower()))
        if t == "h1":
            self.h1_count += 1
        if t in ("header", "nav", "main", "section", "article", "aside", "footer", "figure"):
            self.landmarks.add(t)
        if t == "meta":
            self.meta_tags.append(attr_dict)
            if attr_dict.get("http-equiv", "").lower() == "content-security-policy":
                self.meta_csp = attr_dict.get("content", "")
        if t == "link":
            self.link_tags.append(attr_dict)
            if attr_dict.get("rel", "").lower() == "stylesheet":
                href = attr_dict.get("href", "")
                if href.lower().startswith("data:text/css"):
                    comma_idx = href.find(",")
                    if comma_idx != -1:
                        self.styles.append(urllib.parse.unquote(href[comma_idx + 1 :]))
        if t == "img":
            self.imgs.append(attr_dict)
        if t in ("script", "iframe", "video", "audio", "source", "embed", "track") and attr_dict.get("src"):
            self.media_srcs.append((t, attr_dict["src"]))
        if t == "a" and attr_dict.get("href"):
            self.a_hrefs.append(attr_dict["href"])
        if t == "svg":
            self.svgs.append(attr_dict)
        if t in ("use", "image") and (attr_dict.get("href") or attr_dict.get("xlink:href")):
            self.svg_uses.append(attr_dict.get("href") or attr_dict.get("xlink:href") or "")
        if t == "canvas":
            self.canvases.append(attr_dict)
        if t in ("input", "select", "textarea"):
            if attr_dict.get("type", "").lower() not in ("hidden", "submit", "button", "reset"):
                self.inputs.append(attr_dict)
        if t == "label":
            self.labels.append(attr_dict)
        if t in ("style", "script", "title"):
            self._in_tag = t
            self._in_script_type = attr_dict.get("type", "").lower()
            self._in_script_src = attr_dict.get("src", "")
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._in_tag in ("style", "script", "title"):
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == self._in_tag:
            content = "".join(self._buf)
            if t == "style":
                self.styles.append(content)
            elif t == "script":
                self.scripts.append(
                    {"type": self._in_script_type or "", "src": self._in_script_src or "", "content": content}
                )
            elif t == "title":
                self.title_text = content.strip()
            self._in_tag = None
            self._in_script_type = None
            self._in_script_src = None
            self._buf = []

    def flush_unclosed(self) -> None:
        if self._in_tag in ("style", "script", "title"):
            tail_raw = getattr(self, "rawdata", "") or ""
            content = "".join(self._buf) + tail_raw
            if content:
                if self._in_tag == "style":
                    self.styles.append(content)
                elif self._in_tag == "script":
                    self.scripts.append(
                        {"type": self._in_script_type or "", "src": self._in_script_src or "", "content": content}
                    )
                elif self._in_tag == "title":
                    self.title_text = content.strip()
            self._in_tag = None
            self._in_script_type = None
            self._in_script_src = None
            self._buf = []


def _substitute_csp_placeholders_preserving_directives(
    raw_csp: str,
    style_hashes: list[str],
    attr_style_hashes: list[str],
    script_hashes: list[str],
) -> str:
    """Substitute `'sha256-__CSP_STYLE__'` and `'sha256-__CSP_SCRIPT__'` in-place while preserving all directives.

    Fixes `NEW-BUG-01`:
    - Does NOT overwrite surrounding directives (`object-src 'none'`, `require-trusted-types-for 'script'`,
      `upgrade-insecure-requests`, `frame-ancestors 'none'`, etc. remain 100% intact).
    - Does NOT strip `'unsafe-inline'` if the model emitted it.
    """
    style_replacement_parts: list[str] = []
    if attr_style_hashes and "'unsafe-hashes'" not in raw_csp:
        style_replacement_parts.append("'unsafe-hashes'")
    style_replacement_parts.extend(style_hashes)
    style_replacement_parts.extend(attr_style_hashes)
    style_replacement = " ".join(style_replacement_parts) if style_replacement_parts else "'self'"

    script_replacement = " ".join(script_hashes) if script_hashes else "'self'"

    patched = re.sub(
        r"['\"]?sha256-__CSP_STYLE__['\"]?",
        style_replacement,
        raw_csp,
    )
    patched = re.sub(
        r"['\"]?sha256-__CSP_SCRIPT__['\"]?",
        script_replacement,
        patched,
    )
    return patched


def audit_raw_csp_and_headers(folder: str) -> dict[str, Any]:
    """Grade RAW model `index.html` and `_headers` (from `orig/` if present, else `folder`) BEFORE postprocessing."""
    orig_dir = os.path.join(folder, "orig")
    raw_html_path = (
        os.path.join(orig_dir, "index.html")
        if os.path.exists(os.path.join(orig_dir, "index.html"))
        else os.path.join(folder, "index.html")
    )
    raw_headers_path = (
        os.path.join(orig_dir, "_headers")
        if os.path.exists(os.path.join(orig_dir, "_headers"))
        else os.path.join(folder, "_headers")
    )

    out: dict[str, Any] = {
        "raw_html_path": raw_html_path,
        "raw_meta_csp_present": False,
        "raw_has_unsafe_inline": False,
        "raw_has_style_placeholder": False,
        "raw_has_script_placeholder": False,
        "raw_has_object_src_none": False,
        "raw_has_trusted_types": False,
        "raw_csp_passed": False,
    }
    if not os.path.exists(raw_html_path):
        return out

    with open(raw_html_path, "r", encoding="utf-8", errors="replace") as fh:
        raw_html = fh.read()

    parser = StructHTMLParser()
    parser.feed(raw_html)
    parser.flush_unclosed()

    raw_meta_csp = parser.meta_csp or ""
    meta_audit = audit_csp_policy_string(raw_meta_csp, is_header=False)

    # Check if raw inline styles/scripts either used placeholders or valid exact sha256 hashes
    style_hashes = [sha256_b64(st) for st in parser.styles if st]
    script_hashes = [
        sha256_b64(sc["content"])
        for sc in parser.scripts
        if sc["content"] and not sc.get("src") and sc.get("type") != "application/ld+json"
    ]
    hashes_in_raw = set(re.findall(r"sha256-[A-Za-z0-9+/=]+", raw_meta_csp))
    styles_covered = (
        not style_hashes
        or meta_audit["has_style_placeholder"]
        or all(h in hashes_in_raw for h in style_hashes)
    )
    scripts_covered = (
        not script_hashes
        or meta_audit["has_script_placeholder"]
        or all(h in hashes_in_raw for h in script_hashes)
    )

    raw_csp_passed = (
        meta_audit["present"]
        and not meta_audit["has_unsafe_inline"]
        and not meta_audit["has_unsafe_eval"]
        and styles_covered
        and scripts_covered
        and len(parser.inline_event_handlers) == 0
    )

    out.update(
        {
            "raw_meta_csp_present": meta_audit["present"],
            "raw_has_unsafe_inline": meta_audit["has_unsafe_inline"],
            "raw_has_unsafe_inline_script": meta_audit["has_unsafe_inline_script"],
            "raw_has_unsafe_inline_style": meta_audit["has_unsafe_inline_style"],
            "raw_has_style_placeholder": meta_audit["has_style_placeholder"],
            "raw_has_script_placeholder": meta_audit["has_script_placeholder"],
            "raw_has_object_src_none": meta_audit["has_object_src_none"],
            "raw_has_trusted_types": meta_audit["has_require_trusted_types"],
            "raw_styles_covered": styles_covered,
            "raw_scripts_covered": scripts_covered,
            "raw_csp_passed": raw_csp_passed,
        }
    )

    if os.path.exists(raw_headers_path):
        with open(raw_headers_path, "r", encoding="utf-8", errors="replace") as fh:
            raw_hdr_text = fh.read()
        parsed_hdr = _parse_cloudflare_headers(raw_hdr_text)
        raw_hdr_csp = parsed_hdr.get("headers", {}).get("content-security-policy", "")
        hdr_csp_audit = audit_csp_policy_string(raw_hdr_csp, is_header=True)
        out["raw_headers_csp"] = {
            "present": hdr_csp_audit["present"],
            "has_unsafe_inline": hdr_csp_audit["has_unsafe_inline"],
            "has_object_src_none": hdr_csp_audit["has_object_src_none"],
            "has_trusted_types": hdr_csp_audit["has_require_trusted_types"],
            "has_frame_ancestors_none": hdr_csp_audit["has_frame_ancestors_none"],
        }

    return out


def apply_csp_postprocessor(folder: str) -> dict[str, Any]:
    """Packaging-only placeholder substitution for `'sha256-__CSP_STYLE__'` and `'sha256-__CSP_SCRIPT__'`.

    Fixes `NEW-BUG-01`:
    1. Backs up raw `index.html` and `_headers` to `orig/` BEFORE any packaging edits.
    2. NEVER injects a `<meta http-equiv="Content-Security-Policy">` tag if the model omitted one.
    3. Substitutes ONLY `'sha256-__CSP_STYLE__'` and `'sha256-__CSP_SCRIPT__'` placeholders inside
       existing CSP strings, preserving `object-src 'none'`, `require-trusted-types-for 'script'`,
       and all other model-authored directives verbatim.
    """
    html_path = os.path.join(folder, "index.html")
    if not os.path.exists(html_path):
        return {"applied": False, "reason": "index.html missing"}

    orig_dir = os.path.join(folder, "orig")
    os.makedirs(orig_dir, exist_ok=True)
    orig_html_path = os.path.join(orig_dir, "index.html")
    headers_path = os.path.join(folder, "_headers")
    orig_headers_path = os.path.join(orig_dir, "_headers")

    with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
        cur_html_text = fh.read()
    refresh_html = not os.path.exists(orig_html_path)
    if not refresh_html:
        with open(orig_html_path, "r", encoding="utf-8", errors="replace") as fh:
            prev_orig_text = fh.read()
        refresh_html = csp_skeleton_html(prev_orig_text) != csp_skeleton_html(cur_html_text)
    if refresh_html:
        shutil.copy2(html_path, orig_html_path)

    if os.path.exists(headers_path):
        with open(headers_path, "r", encoding="utf-8", errors="replace") as fh:
            cur_hdr_text = fh.read()
        refresh_hdr = not os.path.exists(orig_headers_path)
        if not refresh_hdr:
            with open(orig_headers_path, "r", encoding="utf-8", errors="replace") as fh:
                prev_orig_hdr = fh.read()
            refresh_hdr = csp_skeleton_headers(prev_orig_hdr) != csp_skeleton_headers(cur_hdr_text)
        if refresh_hdr:
            shutil.copy2(headers_path, orig_headers_path)

    with open(orig_html_path, "r", encoding="utf-8", errors="replace") as fh:
        raw_html = normalize_data_css_and_empty_styles(fh.read())

    parser = StructHTMLParser()
    parser.feed(raw_html)
    parser.flush_unclosed()

    raw_meta_csp = parser.meta_csp or ""
    raw_audit = audit_csp_policy_string(raw_meta_csp, is_header=False)

    style_hashes = [f"'{sha256_b64(st)}'" for st in parser.styles if st]
    attr_style_hashes: list[str] = []
    seen_attr: set[str] = set()
    for st_attr in parser.inline_style_attrs:
        h = f"'{sha256_b64(st_attr)}'"
        if h not in seen_attr:
            seen_attr.add(h)
            attr_style_hashes.append(h)

    script_hashes = [
        f"'{sha256_b64(sc['content'])}'"
        for sc in parser.scripts
        if sc["content"] and not sc.get("src") and sc.get("type") != "application/ld+json"
    ]

    had_meta_csp = bool(_META_CSP_RE.search(raw_html))
    patched_meta_csp = raw_meta_csp
    html_modified = False

    if had_meta_csp and ("__CSP_STYLE__" in raw_meta_csp or "__CSP_SCRIPT__" in raw_meta_csp):
        patched_meta_csp = _substitute_csp_placeholders_preserving_directives(
            raw_meta_csp, style_hashes, attr_style_hashes, script_hashes
        )
        new_meta_tag = f'<meta http-equiv="Content-Security-Policy" content="{patched_meta_csp}">'
        patched_html = _META_CSP_RE.sub(lambda _: new_meta_tag, raw_html, count=1)
        with open(html_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(patched_html)
        html_modified = True
    elif raw_html != cur_html_text and had_meta_csp and "sha256-" in cur_html_text and "__CSP_" in raw_html:
        # Restore from raw if needed
        with open(html_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(raw_html)

    headers_patched = False
    if os.path.exists(headers_path) and os.path.exists(orig_headers_path):
        with open(orig_headers_path, "r", encoding="utf-8", errors="replace") as fh:
            raw_headers = fh.read()
        parsed_hdr = _parse_cloudflare_headers(raw_headers)
        if parsed_hdr.get("has_route_rule") and ("__CSP_STYLE__" in raw_headers or "__CSP_SCRIPT__" in raw_headers):
            def _sub_hdr_line(m: re.Match) -> str:
                prefix = m.group(1)
                raw_val = m.group(2)
                return prefix + _substitute_csp_placeholders_preserving_directives(
                    raw_val, style_hashes, attr_style_hashes, script_hashes
                )

            patched_headers = _HEADER_CSP_LINE_RE.sub(_sub_hdr_line, raw_headers)
            with open(headers_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(patched_headers)
            headers_patched = True

    return {
        "applied": html_modified or headers_patched,
        "had_meta_csp_in_raw": had_meta_csp,
        "raw_has_unsafe_inline": raw_audit["has_unsafe_inline"],
        "raw_has_object_src_none": raw_audit["has_object_src_none"],
        "raw_has_trusted_types": raw_audit["has_require_trusted_types"],
        "headers_patched": headers_patched,
        "computed_style_block_hashes_count": len(style_hashes),
        "computed_inline_style_attr_hashes_count": len(attr_style_hashes),
        "computed_script_hashes_count": len(script_hashes),
        "patched_meta_csp": patched_meta_csp,
    }
