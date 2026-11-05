import base64
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from html.parser import HTMLParser

SUITE_DIR = r"D:\projects\SmartLLM\eval\suite"
TASKS_JSON = os.path.join(SUITE_DIR, "tasks.json")
RUNS_DIR = os.path.join(SUITE_DIR, "runs")
NODE_EXE = r"C:\Program Files\nodejs\node.exe"
DAG_RUNNER = os.path.join(SUITE_DIR, "test_dag_runner.mjs")


def oklch_to_srgb(L: float, C: float, H_deg: float) -> tuple[float, float, float]:
    """Convert OKLCH (L in 0..1 or 0..100%, C, H in degrees) to linear sRGB (0..1)."""
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

    def clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    return (clamp01(r_lin), clamp01(g_lin), clamp01(b_lin))


def relative_luminance_from_lin_rgb(r_lin: float, g_lin: float, b_lin: float) -> float:
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(lum1: float, lum2: float) -> float:
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def parse_oklch_tokens(css_text: str) -> dict:
    tokens = {}
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


def sha256_b64(text: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


class StructHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.styles = []
        self.scripts = []
        self.inline_style_attrs = []
        self.meta_csp = None
        self.meta_tags = []
        self.link_tags = []
        self.title_text = ""
        self.h1_count = 0
        self.landmarks = set()
        self.imgs = []
        self.svgs = []
        self.canvases = []
        self.inputs = []
        self.labels = []
        self._in_tag = None
        self._in_script_type = None
        self._in_script_src = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        t = tag.lower()
        if "style" in attr_dict and attr_dict["style"]:
            self.inline_style_attrs.append(attr_dict["style"])
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
        if t == "svg":
            self.svgs.append(attr_dict)
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

    def handle_data(self, data):
        if self._in_tag in ("style", "script", "title"):
            self._buf.append(data)

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == self._in_tag:
            content = "".join(self._buf)
            if t == "style":
                self.styles.append(content)
            elif t == "script":
                self.scripts.append(
                    {"type": self._in_script_type, "src": self._in_script_src, "content": content}
                )
            elif t == "title":
                self.title_text = content.strip()
            self._in_tag = None
            self._in_script_type = None
            self._in_script_src = None
            self._buf = []

    def flush_unclosed(self):
        if self._in_tag and self._buf:
            content = "".join(self._buf)
            if self._in_tag == "style":
                self.styles.append(content)
            elif self._in_tag == "script":
                self.scripts.append(
                    {"type": self._in_script_type, "src": self._in_script_src, "content": content}
                )
            self._in_tag = None
            self._buf = []


def apply_csp_postprocessor(folder: str) -> dict:
    """
    Deterministic SmartLLM CSP postprocessor:
    1. Backs up raw index.html and _headers to orig/ (if not already backed up).
    2. Computes exact SHA-256 hashes of every inline <style>, inline <script>, and static style="..." attribute.
    3. Replaces <meta http-equiv="Content-Security-Policy"> and _headers CSP with exact sha256-... hashes.
    """
    html_path = os.path.join(folder, "index.html")
    if not os.path.exists(html_path):
        return {"applied": False, "reason": "index.html missing"}

    orig_dir = os.path.join(folder, "orig")
    os.makedirs(orig_dir, exist_ok=True)
    orig_html_path = os.path.join(orig_dir, "index.html")
    if not os.path.exists(orig_html_path):
        shutil.copy2(html_path, orig_html_path)

    headers_path = os.path.join(folder, "_headers")
    orig_headers_path = os.path.join(orig_dir, "_headers")
    if os.path.exists(headers_path) and not os.path.exists(orig_headers_path):
        shutil.copy2(headers_path, orig_headers_path)

    with open(orig_html_path, "r", encoding="utf-8") as fh:
        raw_html = fh.read()

    # Strip empty no-op <link rel="stylesheet" href="data:text/css,"> and <style></style> tags,
    # and convert non-empty data:text/css stylesheets into inline <style> blocks for strict SHA-256 CSP
    raw_html = re.sub(
        r'<link\s+[^>]*href\s*=\s*["\']data:text/css,\s*["\'][^>]*>\r?\n?',
        "",
        raw_html,
        flags=re.IGNORECASE,
    )
    raw_html = re.sub(
        r"<style>\s*</style>\r?\n?",
        "",
        raw_html,
        flags=re.IGNORECASE,
    )

    def _data_css_to_style(match: re.Match) -> str:
        decoded_css = urllib.parse.unquote(match.group(2))
        return f"<style>{decoded_css}</style>"

    raw_html = re.sub(
        r'<link\s+[^>]*href\s*=\s*(["\'])data:text/css,(.*?)\1[^>]*>',
        _data_css_to_style,
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    parser = StructHTMLParser()
    parser.feed(raw_html)
    parser.flush_unclosed()

    raw_meta_csp = parser.meta_csp or ""
    raw_has_unsafe_inline = "'unsafe-inline'" in raw_meta_csp.lower()

    style_hashes = [f"'{sha256_b64(st)}'" for st in parser.styles if st]
    attr_style_hashes = []
    seen_attr = set()
    for st_attr in parser.inline_style_attrs:
        h = f"'{sha256_b64(st_attr)}'"
        if h not in seen_attr:
            seen_attr.add(h)
            attr_style_hashes.append(h)

    script_hashes = [
        f"'{sha256_b64(sc['content'])}'"
        for sc in parser.scripts
        if sc["content"] and not sc.get("src")
    ]

    style_tokens = ["'self'"]
    if attr_style_hashes:
        style_tokens.append("'unsafe-hashes'")
    style_tokens.extend(style_hashes)
    style_tokens.extend(attr_style_hashes)
    style_src = " ".join(style_tokens)

    script_src = " ".join(["'self'"] + script_hashes) if script_hashes else "'self'"

    meta_csp_policy = (
        f"default-src 'none'; "
        f"style-src {style_src}; "
        f"script-src {script_src}; "
        f"img-src 'self' data: blob:; "
        f"font-src 'self' data:; "
        f"connect-src 'self'; "
        f"base-uri 'none'; "
        f"form-action 'none'"
    )
    header_csp_policy = meta_csp_policy + "; frame-ancestors 'none'"

    meta_csp_re = re.compile(
        r'(<meta\s+[^>]*http-equiv\s*=\s*["\']Content-Security-Policy["\'][^>]*>)',
        re.IGNORECASE | re.DOTALL,
    )
    new_meta_tag = f'<meta http-equiv="Content-Security-Policy" content="{meta_csp_policy}">'
    if meta_csp_re.search(raw_html):
        patched_html = meta_csp_re.sub(lambda _: new_meta_tag, raw_html)
        had_meta_csp = True
    else:
        had_meta_csp = False
        head_re = re.compile(r"(<head\b[^>]*>)", re.IGNORECASE)
        if head_re.search(raw_html):
            patched_html = head_re.sub(lambda m: m.group(1) + "\n  " + new_meta_tag, raw_html, count=1)
        else:
            patched_html = new_meta_tag + "\n" + raw_html

    with open(html_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(patched_html)

    headers_patched = False
    if os.path.exists(orig_headers_path):
        with open(orig_headers_path, "r", encoding="utf-8") as fh:
            raw_headers = fh.read()
        csp_line_re = re.compile(r"(^[ \t]*Content-Security-Policy:\s*).*$", re.IGNORECASE | re.MULTILINE)
        if csp_line_re.search(raw_headers):
            patched_headers = csp_line_re.sub(lambda m: m.group(1) + header_csp_policy, raw_headers)
            with open(headers_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(patched_headers)
            headers_patched = True

    return {
        "applied": True,
        "had_meta_csp_in_raw": had_meta_csp,
        "raw_has_unsafe_inline": raw_has_unsafe_inline,
        "headers_patched": headers_patched,
        "computed_style_block_hashes_count": len(style_hashes),
        "computed_inline_style_attr_hashes_count": len(attr_style_hashes),
        "computed_script_hashes_count": len(script_hashes),
        "injected_meta_csp": meta_csp_policy,
    }


def audit_web_task(folder: str, task_spec: dict) -> dict:
    task_id = task_spec["id"]
    req_files = task_spec.get("required_files", ["index.html"])
    report = {
        "task_id": task_id,
        "category": task_spec["category"],
        "language": task_spec["language"],
        "canon": task_spec["canon"],
    }

    # Check required files
    files_status = {}
    for rf in req_files:
        p = os.path.join(folder, rf)
        files_status[rf] = {
            "exists": os.path.exists(p),
            "size_bytes": os.path.getsize(p) if os.path.exists(p) else 0,
        }
    report["required_files"] = files_status
    report["all_required_files_present"] = all(
        v["exists"] and v["size_bytes"] > 0 for v in files_status.values()
    )

    html_path = os.path.join(folder, "index.html")
    if not os.path.exists(html_path):
        report["error"] = "index.html not found"
        return report

    with open(html_path, "r", encoding="utf-8") as fh:
        html_text = fh.read()

    parser = StructHTMLParser()
    parser.feed(html_text)
    parser.flush_unclosed()

    # Load external local CSS if linked (e.g. T9 tokens.css)
    combined_css = "\n".join(parser.styles)
    tokens_css_path = os.path.join(folder, "tokens.css")
    if os.path.exists(tokens_css_path):
        with open(tokens_css_path, "r", encoding="utf-8") as fh:
            combined_css = fh.read() + "\n" + combined_css

    # Load external local JS if present (e.g. T9 app.js), excluding JSON-LD data blocks
    combined_js = "\n".join(
        sc["content"] for sc in parser.scripts if sc.get("content") and sc.get("type") != "application/ld+json"
    )
    app_js_path = os.path.join(folder, "app.js")
    if os.path.exists(app_js_path):
        with open(app_js_path, "r", encoding="utf-8") as fh:
            combined_js = fh.read() + "\n" + combined_js

    # CSP verification after postprocessor
    meta_csp = parser.meta_csp or ""
    csp_hashes_in_policy = set(re.findall(r"sha256-[A-Za-z0-9+/=]+", meta_csp))
    has_unsafe_inline = "'unsafe-inline'" in meta_csp.lower()

    style_hashes = []
    for idx, st in enumerate(parser.styles):
        if not st:
            continue
        h_exact = sha256_b64(st)
        style_hashes.append({"index": idx, "len": len(st), "matched_exact": h_exact in csp_hashes_in_policy})

    script_hashes = []
    jsonld_blocks = []
    for idx, sc in enumerate(parser.scripts):
        st_type = sc["type"]
        content = sc["content"]
        if st_type == "application/ld+json":
            jsonld_blocks.append(content)
        if content and not sc.get("src"):
            h_exact = sha256_b64(content)
            script_hashes.append(
                {"index": idx, "type": st_type or "text/javascript", "matched_exact": h_exact in csp_hashes_in_policy}
            )

    report["csp"] = {
        "has_meta_csp": bool(meta_csp),
        "has_unsafe_inline": has_unsafe_inline,
        "all_style_hashes_matched": all(x["matched_exact"] for x in style_hashes),
        "all_script_hashes_matched": all(x["matched_exact"] for x in script_hashes),
    }

    # External HTTP(S) resource URLs check
    urls = re.findall(r"""(?:src|href|url)\s*(?:=|\()\s*['"]?(https?://[^'"\s)>]+)""", html_text, re.IGNORECASE)
    ext_resource_urls = []
    for u in urls:
        if any(
            u.startswith(prefix)
            for prefix in ("http://www.w3.org/", "https://www.w3.org/", "https://schema.org", "http://schema.org")
        ):
            continue
        ext_resource_urls.append(u)
    report["external_urls_in_attrs"] = ext_resource_urls

    # SEO Meta tags check
    meta_names = {m.get("name", "").lower(): m.get("content", "") for m in parser.meta_tags if m.get("name")}
    meta_props = {m.get("property", "").lower(): m.get("content", "") for m in parser.meta_tags if m.get("property")}
    has_canonical = any(l.get("rel", "").lower() == "canonical" for l in parser.link_tags)
    report["seo_meta"] = {
        "has_title": bool(parser.title_text),
        "has_description": bool(meta_names.get("description")),
        "has_canonical": has_canonical,
        "has_og_title": bool(meta_props.get("og:title")),
        "has_og_description": bool(meta_props.get("og:description")),
    }

    # JSON-LD @graph & verbatim FAQ check (for tasks requiring llms.txt / full SEO)
    if "llms.txt" in req_files:
        jsonld_report = {"blocks_count": len(jsonld_blocks), "valid_json": False, "graph_types": [], "faq_all_verbatim": False}
        if jsonld_blocks:
            try:
                graph = []
                for blk in jsonld_blocks:
                    parsed_ld = json.loads(blk)
                    if isinstance(parsed_ld, list):
                        graph.extend(parsed_ld)
                    elif isinstance(parsed_ld, dict):
                        if parsed_ld.get("@graph"):
                            graph.extend(parsed_ld["@graph"])
                        elif parsed_ld.get("@type"):
                            graph.append(parsed_ld)
                jsonld_report["valid_json"] = True
                types = []
                faq_items = []
                for node in graph:
                    t = node.get("@type")
                    if isinstance(t, list):
                        types.extend(t)
                    elif t:
                        types.append(t)
                    if t == "FAQPage" or (isinstance(t, list) and "FAQPage" in t):
                        for q in node.get("mainEntity", []):
                            q_name = q.get("name", "").strip()
                            a_text = (q.get("acceptedAnswer") or {}).get("text", "").strip()
                            faq_items.append({"q": q_name, "a": a_text})
                jsonld_report["graph_types"] = types
                jsonld_report["has_all_4_types"] = all(
                    req_t in types for req_t in ("Organization", "Product", "FAQPage", "BreadcrumbList")
                )
                jsonld_report["product_count"] = sum(1 for x in types if x == "Product")
                verbatim_matches = []
                for item in faq_items:
                    q_in_html = bool(item["q"]) and (item["q"] in html_text)
                    a_in_html = bool(item["a"]) and (item["a"] in html_text)
                    verbatim_matches.append({"q": item["q"], "q_in_html": q_in_html, "a_in_html": a_in_html})
                jsonld_report["faq_count"] = len(faq_items)
                jsonld_report["faq_all_verbatim"] = bool(verbatim_matches) and all(
                    m["q_in_html"] and m["a_in_html"] for m in verbatim_matches
                )
            except Exception as e:
                jsonld_report["parse_error"] = str(e)
        report["json_ld"] = jsonld_report

    # _headers check
    if "_headers" in req_files:
        headers_path = os.path.join(folder, "_headers")
        headers_report = {"exists": os.path.exists(headers_path), "all_passed": False}
        if headers_report["exists"]:
            with open(headers_path, "r", encoding="utf-8") as fh:
                h_text = fh.read()
            headers_report["has_route_rule"] = bool(re.search(r"^/\*", h_text, re.MULTILINE))
            req_headers = {
                "Content-Security-Policy": "content-security-policy:" in h_text.lower(),
                "frame-ancestors 'none'": "frame-ancestors 'none'" in h_text.lower(),
                "Strict-Transport-Security": "strict-transport-security:" in h_text.lower()
                and "max-age=63072000" in h_text.lower()
                and "includesubdomains" in h_text.lower()
                and "preload" in h_text.lower(),
                "X-Content-Type-Options": "x-content-type-options:" in h_text.lower() and "nosniff" in h_text.lower(),
                "Referrer-Policy": "referrer-policy:" in h_text.lower(),
                "Permissions-Policy": "permissions-policy:" in h_text.lower(),
                "Cross-Origin-Opener-Policy": "cross-origin-opener-policy:" in h_text.lower(),
            }
            headers_report["checks"] = req_headers
            headers_report["all_passed"] = headers_report["has_route_rule"] and all(req_headers.values())
        report["_headers"] = headers_report

    # llms.txt check
    if "llms.txt" in req_files:
        llms_path = os.path.join(folder, "llms.txt")
        llms_report = {"exists": os.path.exists(llms_path)}
        if llms_report["exists"]:
            with open(llms_path, "r", encoding="utf-8") as fh:
                l_text = fh.read()
            llms_report["has_h1"] = bool(re.search(r"^#\s+\S+", l_text, re.MULTILINE))
            llms_report["has_blockquote"] = bool(re.search(r"^>\s+\S+", l_text, re.MULTILINE))
            llms_report["has_h2_sections"] = bool(re.search(r"^##\s+\S+", l_text, re.MULTILINE))
        report["llms_txt"] = llms_report

    # HTML5 Semantics & Accessibility
    label_fors = {l.get("for") for l in parser.labels if l.get("for")}
    inputs_labeled = sum(
        1
        for inp in parser.inputs
        if (inp.get("id") and inp.get("id") in label_fors) or inp.get("aria-label") or inp.get("aria-labelledby")
    )
    report["semantics"] = {
        "h1_count": parser.h1_count,
        "landmarks": sorted(parser.landmarks),
        "svg_count": len(parser.svgs),
        "canvas_count": len(parser.canvases),
        "form_inputs_count": len(parser.inputs),
        "form_inputs_labeled": inputs_labeled,
        "has_prefers_reduced_motion": "prefers-reduced-motion" in combined_css,
    }

    # OKLCH Tokens & Contrast
    tokens = parse_oklch_tokens(combined_css)
    all_pairs = {}
    t_names = list(tokens.keys())
    for i in range(len(t_names)):
        for j in range(i + 1, len(t_names)):
            n1, n2 = t_names[i], t_names[j]
            cr = contrast_ratio(tokens[n1]["luminance"], tokens[n2]["luminance"])
            if cr >= 4.5:
                all_pairs[f"{n1} vs {n2}"] = cr
    max_contrast = max(all_pairs.values()) if all_pairs else 0.0
    report["oklch"] = {
        "token_count": len(tokens),
        "max_contrast_pair": max_contrast,
        "passes_aaa_7_to_1": max_contrast >= 7.0,
        "tokens": tokens,
    }

    # Task-specific technical checks
    if task_id == "t5":
        report["task_specific"] = {
            "has_subgrid": "subgrid" in combined_css.lower(),
            "has_tabular_nums": "tabular-nums" in combined_css.lower(),
        }
    elif task_id == "t6":
        report["task_specific"] = {
            "has_canvas": len(parser.canvases) >= 1,
            "has_webgl_or_shader": bool(
                re.search(r"webgl|createShader|shaderSource|gl_FragColor|fragColor", combined_js, re.IGNORECASE)
            ),
        }
    elif task_id == "t7":
        report["task_specific"] = {
            "has_hard_offset_shadow": bool(re.search(r"[3-8]px\s+[3-8]px\s+0(?:px)?", combined_css)),
            "has_interactive_calc": len(parser.inputs) >= 2 and len(combined_js) > 200,
        }
    elif task_id == "t8":
        report["task_specific"] = {
            "has_container_query": "@container" in combined_css.lower() or "container-type" in combined_css.lower(),
            "has_subgrid": "subgrid" in combined_css.lower(),
            "has_dropcap": "first-letter" in combined_css.lower(),
        }
    elif task_id == "t9":
        zpath = os.path.join(folder, "zimage_prompts.json")
        z_valid = False
        z_count = 0
        z_exact_match = False
        if os.path.exists(zpath):
            try:
                with open(zpath, "r", encoding="utf-8") as fh:
                    zdata = json.load(fh)
                if isinstance(zdata, dict) and "prompts" in zdata:
                    zdata = zdata["prompts"]
                if isinstance(zdata, list):
                    z_valid = True
                    z_count = len(zdata)
                    z_exact_match = (
                        z_count >= 3
                        and all(
                            isinstance(item, dict)
                            and len(str(item.get("prompt", ""))) >= 200
                            and bool(item.get("exact_text_in_frame"))
                            and str(item.get("exact_text_in_frame")) in str(item.get("prompt", ""))
                            for item in zdata
                        )
                    )
            except Exception:
                pass
        report["task_specific"] = {
            "zimage_json_valid": z_valid,
            "zimage_prompts_count": z_count,
            "zimage_exact_text_verified": z_exact_match,
        }
    elif task_id == "t11":
        report["task_specific"] = {
            "has_canvas": len(parser.canvases) >= 1,
            "has_kinematics_js": len(combined_js) > 300,
        }

    return report


def audit_typescript_task(folder: str, task_spec: dict) -> dict:
    dag_path = os.path.join(folder, "dag.ts")
    report = {
        "task_id": task_spec["id"],
        "category": "typescript_coding",
        "language": "en",
        "canon": task_spec["canon"],
        "required_files": {
            "dag.ts": {
                "exists": os.path.exists(dag_path),
                "size_bytes": os.path.getsize(dag_path) if os.path.exists(dag_path) else 0,
            }
        },
        "all_required_files_present": os.path.exists(dag_path) and os.path.getsize(dag_path) > 0,
    }
    if not os.path.exists(dag_path):
        report["error"] = "dag.ts not found"
        return report

    proc = subprocess.run(
        [NODE_EXE, DAG_RUNNER, dag_path],
        capture_output=True,
        text=True,
        timeout=90,
    )
    try:
        ts_res = json.loads(proc.stdout)
    except Exception as e:
        ts_res = {
            "tsc_strict_passed": False,
            "parse_error": str(e),
            "raw_stdout": proc.stdout[:2000],
            "raw_stderr": proc.stderr[:2000],
        }
    report["typescript_eval"] = ts_res
    return report


def audit_model_run(model_slug: str, tasks: list[dict]) -> dict:
    model_dir = os.path.join(RUNS_DIR, model_slug)
    if not os.path.exists(model_dir):
        return {"error": f"Run directory {model_dir} does not exist"}

    model_report = {}
    for t in tasks:
        tid = t["id"]
        tfolder = os.path.join(model_dir, tid)
        if not os.path.exists(tfolder):
            model_report[tid] = {"status": "missing"}
            continue
        if t["category"] == "typescript_coding":
            model_report[tid] = audit_typescript_task(tfolder, t)
        else:
            csp_post = apply_csp_postprocessor(tfolder)
            rep = audit_web_task(tfolder, t)
            rep["csp_postprocessor"] = csp_post
            model_report[tid] = rep

    out_file = os.path.join(model_dir, "static_audit.json")
    with open(out_file, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(model_report, fh, indent=2, ensure_ascii=False)
    return model_report


def main():
    with open(TASKS_JSON, "r", encoding="utf-8") as fh:
        tasks_data = json.load(fh)
    tasks = tasks_data["tasks"]

    os.makedirs(RUNS_DIR, exist_ok=True)
    target_models = sys.argv[1:] if len(sys.argv) > 1 else sorted(
        d for d in os.listdir(RUNS_DIR) if os.path.isdir(os.path.join(RUNS_DIR, d))
    )

    all_reports = {}
    for m in target_models:
        print(f"[AUDIT] Running static + CSP + tsc audit for {m} ...")
        all_reports[m] = audit_model_run(m, tasks)

    summary_path = os.path.join(SUITE_DIR, "results", "static_audit_all.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(all_reports, fh, indent=2, ensure_ascii=False)
    print(f"Saved static audit summary to {summary_path}")


if __name__ == "__main__":
    main()
