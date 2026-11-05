import base64
import hashlib
import json
import math
import os
import re
import shutil
import urllib.parse
from html.parser import HTMLParser

BASE_DIR = r"D:\projects\SmartLLM\eval\round2"
SLUGS = ["qwen3.8-no-think", "qwen3.8-think-8k", "qwen3.6-35b-a3b"]


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


class StructHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.styles = []
        self.inline_styles_only = []
        self.style_attrs = []
        self.scripts = []
        self.meta_csp = None
        self.meta_tags = []
        self.h1_count = 0
        self.landmarks = set()
        self.imgs = []
        self.svgs = []
        self.inputs = []
        self.labels = []
        self._in_tag = None
        self._in_script_type = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        t = tag.lower()
        if "style" in attr_dict and attr_dict["style"]:
            self.style_attrs.append(attr_dict["style"])
        if t == "h1":
            self.h1_count += 1
        if t in ("header", "nav", "main", "section", "article", "aside", "footer", "figure"):
            self.landmarks.add(t)
        if t == "meta":
            self.meta_tags.append(attr_dict)
            if attr_dict.get("http-equiv", "").lower() == "content-security-policy":
                self.meta_csp = attr_dict.get("content", "")
        if t == "link" and attr_dict.get("rel", "").lower() == "stylesheet":
            href = attr_dict.get("href", "")
            if href.lower().startswith("data:text/css"):
                comma_idx = href.find(",")
                if comma_idx != -1:
                    self.styles.append(urllib.parse.unquote(href[comma_idx + 1 :]))
        if t == "img":
            self.imgs.append(attr_dict)
        if t == "svg":
            self.svgs.append(attr_dict)
        if t in ("input", "select", "textarea"):
            if attr_dict.get("type", "").lower() not in ("hidden", "submit", "button", "reset"):
                self.inputs.append(attr_dict)
        if t == "label":
            self.labels.append(attr_dict)
        if t in ("style", "script"):
            self._in_tag = t
            self._in_script_type = attr_dict.get("type", "").lower()
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
                self.inline_styles_only.append(content)
            elif t == "script":
                self.scripts.append({"type": self._in_script_type, "content": content})
            self._in_tag = None
            self._in_script_type = None
            self._buf = []

    def flush_unclosed(self):
        if self._in_tag and self._buf:
            content = "".join(self._buf)
            if self._in_tag == "style":
                self.styles.append(content)
                self.inline_styles_only.append(content)
            elif self._in_tag == "script":
                self.scripts.append({"type": self._in_script_type, "content": content})
            self._in_tag = None
            self._buf = []


def sha256_b64(text: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


def rebuild_clean_postprocessed(folder: str, task: str):
    """Re-copy from orig/ and cleanly inject SHA-256 CSP into index.html and _headers."""
    orig_dir = os.path.join(folder, "orig")
    if not os.path.exists(orig_dir):
        return
    for fname in os.listdir(orig_dir):
        src = os.path.join(orig_dir, fname)
        dst = os.path.join(folder, fname)
        if os.path.isfile(src):
            shutil.copy2(src, dst)

    if task not in ("t1", "t3"):
        return

    html_path = os.path.join(folder, "index.html")
    if not os.path.exists(html_path):
        return
    with open(html_path, "r", encoding="utf-8") as fh:
        html_text = fh.read()

    parser = StructHTMLParser()
    parser.feed(html_text)
    parser.flush_unclosed()

    uses_data_css = "data:text/css" in html_text.lower()
    uses_data_js = "data:text/javascript" in html_text.lower()

    style_attr_hashes = sorted({f"'{sha256_b64(sa)}'" for sa in parser.style_attrs})
    style_hashes = (
        [f"'{sha256_b64(s)}'" for s in parser.inline_styles_only]
        + (["'unsafe-hashes'"] + style_attr_hashes if style_attr_hashes else [])
        + (["data:"] if uses_data_css else [])
    )
    script_hashes = [f"'{sha256_b64(sc['content'])}'" for sc in parser.scripts] + (["data:"] if uses_data_js else [])

    style_src_val = " ".join(style_hashes) if style_hashes else "'none'"
    script_src_val = " ".join(script_hashes) if script_hashes else "'none'"

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
    new_meta_tag = f'<meta http-equiv="Content-Security-Policy" content="{meta_policy}">'

    meta_re = re.compile(r'<meta\b[^>]*http-equiv\s*=\s*["\']Content-Security-Policy["\'][^>]*>', re.IGNORECASE)
    if meta_re.search(html_text):
        html_fixed = meta_re.sub(new_meta_tag, html_text)
    else:
        html_fixed = re.sub(r"(<head[^>]*>\s*)", r"\1" + new_meta_tag + "\n", html_text, count=1, flags=re.I)

    with open(html_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html_fixed)

    headers_path = os.path.join(folder, "_headers")
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


def compute_all_reasonable_contrasts(tokens: dict) -> dict:
    bg_keys = [k for k in tokens if any(w in k.lower() for w in ("bg", "surface", "panel", "card", "paper", "canvas"))]
    fg_keys = [
        k
        for k in tokens
        if any(w in k.lower() for w in ("text", "ink", "fg", "muted", "dim", "sub", "accent", "primary", "heading", "body"))
    ]
    res = {}
    for fg in fg_keys:
        for bg in bg_keys:
            if fg == bg:
                continue
            res[f"{fg} on {bg}"] = contrast_ratio(tokens[fg]["luminance"], tokens[bg]["luminance"])
    return res


def extract_jsonld_nodes(obj) -> list[dict]:
    nodes = []
    if isinstance(obj, list):
        for item in obj:
            nodes.extend(extract_jsonld_nodes(item))
    elif isinstance(obj, dict):
        if "@graph" in obj and isinstance(obj["@graph"], list):
            for item in obj["@graph"]:
                nodes.extend(extract_jsonld_nodes(item))
        else:
            nodes.append(obj)
    return nodes


def audit_landing(folder: str, task: str) -> dict:
    rebuild_clean_postprocessed(folder, task)

    report = {}
    html_path = os.path.join(folder, "index.html")
    orig_html_path = os.path.join(folder, "orig", "index.html")
    if not os.path.exists(html_path):
        return {"error": "index.html not found"}

    with open(html_path, "r", encoding="utf-8") as fh:
        html_text = fh.read()
    with open(orig_html_path, "r", encoding="utf-8") as fh:
        orig_html_text = fh.read()

    orig_parser = StructHTMLParser()
    orig_parser.feed(orig_html_text)
    orig_parser.flush_unclosed()

    parser = StructHTMLParser()
    parser.feed(html_text)
    parser.flush_unclosed()

    meta_csp = parser.meta_csp or ""
    csp_hashes_in_policy = set(re.findall(r"sha256-[A-Za-z0-9+/=]+", meta_csp))

    jsonld_blocks = []
    for sc in parser.scripts:
        if sc["type"] == "application/ld+json":
            jsonld_blocks.append(sc["content"])

    report["csp"] = {
        "orig_had_meta_csp": bool(orig_parser.meta_csp),
        "orig_meta_csp": orig_parser.meta_csp or "",
        "orig_has_unsafe_inline": "'unsafe-inline'" in (orig_parser.meta_csp or "").lower(),
        "postprocessed_meta_csp": meta_csp,
        "postprocessed_hashes_count": len(csp_hashes_in_policy),
    }

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

    jsonld_report = {"blocks_count": len(jsonld_blocks), "valid_json": False, "graph_types": [], "faq_questions": []}
    if jsonld_blocks:
        try:
            types = []
            faq_items = []
            for blk in jsonld_blocks:
                parsed_ld = json.loads(blk)
                nodes = extract_jsonld_nodes(parsed_ld)
                for node in nodes:
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
            jsonld_report["valid_json"] = True
            jsonld_report["graph_types"] = types
            jsonld_report["has_all_4_types"] = all(
                req_t in types for req_t in ("Organization", "Product", "FAQPage", "BreadcrumbList")
            )
            jsonld_report["product_count"] = sum(1 for x in types if x == "Product")
            verbatim_matches = []
            for item in faq_items:
                q_in_html = item["q"] in html_text
                a_in_html = item["a"] in html_text
                verbatim_matches.append({"q": item["q"], "q_in_html": q_in_html, "a_in_html": a_in_html})
            jsonld_report["faq_count"] = len(faq_items)
            jsonld_report["faq_verbatim_check"] = verbatim_matches
            jsonld_report["faq_all_verbatim"] = bool(verbatim_matches) and all(
                m["q_in_html"] and m["a_in_html"] for m in verbatim_matches
            )
        except Exception as e:
            jsonld_report["parse_error"] = str(e)
    report["json_ld"] = jsonld_report

    headers_path = os.path.join(folder, "_headers")
    headers_report = {"exists": os.path.exists(headers_path)}
    if headers_report["exists"]:
        with open(headers_path, "r", encoding="utf-8") as fh:
            h_text = fh.read()
        headers_report["raw"] = h_text
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
        headers_report["passed_count"] = sum(1 for v in req_headers.values() if v)
        headers_report["all_passed"] = all(req_headers.values())
    report["_headers"] = headers_report

    llms_path = os.path.join(folder, "llms.txt")
    llms_report = {"exists": os.path.exists(llms_path)}
    if llms_report["exists"]:
        with open(llms_path, "r", encoding="utf-8") as fh:
            l_text = fh.read()
        llms_report["has_h1"] = bool(re.search(r"^#\s+.+", l_text, re.MULTILINE))
        llms_report["has_blockquote"] = bool(re.search(r"^>\s+.+", l_text, re.MULTILINE))
        llms_report["has_h2_sections"] = bool(re.search(r"^##\s+.+", l_text, re.MULTILINE))
        llms_report["has_markdown_links"] = bool(re.search(r"^-\s+\[.+?\]\(.+?\)", l_text, re.MULTILINE))
    report["llms_txt"] = llms_report

    robots_path = os.path.join(folder, "robots.txt")
    robots_report = {"exists": os.path.exists(robots_path)}
    if robots_report["exists"]:
        with open(robots_path, "r", encoding="utf-8") as fh:
            r_text = fh.read()
        robots_report["has_user_agent"] = "user-agent:" in r_text.lower()
        robots_report["has_allow_or_disallow"] = ("allow:" in r_text.lower()) or ("disallow:" in r_text.lower())
    report["robots_txt"] = robots_report

    label_fors = {lbl.get("for") for lbl in parser.labels if lbl.get("for")}
    inputs_labeled = []
    for inp in parser.inputs:
        inp_id = inp.get("id")
        has_label = bool(
            (inp_id and inp_id in label_fors) or inp.get("aria-label") or inp.get("aria-labelledby")
        )
        inputs_labeled.append({"id": inp_id, "name": inp.get("name"), "labeled": has_label})

    all_css = "\n".join(parser.styles)
    report["semantics_a11y"] = {
        "h1_count": parser.h1_count,
        "landmarks": sorted(parser.landmarks),
        "img_count": len(parser.imgs),
        "imgs_with_alt": sum(1 for im in parser.imgs if "alt" in im),
        "svg_count": len(parser.svgs),
        "inputs_count": len(parser.inputs),
        "inputs_labeled": inputs_labeled,
        "all_inputs_labeled": all(x["labeled"] for x in inputs_labeled),
        "prefers_reduced_motion": "prefers-reduced-motion" in all_css,
    }

    tokens = parse_oklch_tokens(all_css)
    report["oklch_tokens"] = tokens
    report["contrasts"] = compute_all_reasonable_contrasts(tokens)

    if task == "t1":
        report["canon"] = {
            "oklch_token_count": len(tokens),
            "has_signal_orange_068_019_45": bool(
                re.search(r"oklch\(\s*(?:0\.68|68%)\s+0\.19\s+45", all_css, re.IGNORECASE)
            ),
            "has_blueprint_grid_2a2e35_or_1px": ("#2a2e35" in all_css.lower()) or ("linear-gradient" in all_css.lower()),
            "has_jetbrains_mono": "jetbrains mono" in all_css.lower(),
            "has_ibm_plex_sans": "ibm plex sans" in all_css.lower(),
            "has_external_font_cdn": ("fonts.googleapis.com" in html_text.lower())
            or ("fonts.gstatic.com" in html_text.lower()),
        }
    elif task == "t3":
        report["canon"] = {
            "oklch_token_count": len(tokens),
            "has_warm_bg_095_001_85": bool(
                re.search(r"oklch\(\s*(?:0\.95|95%)\s+0\.01\s+85", all_css, re.IGNORECASE)
            ),
            "has_clamp_4rem_10vw_12rem": bool(
                re.search(r"clamp\(\s*4rem\s*,\s*10vw\s*,\s*12rem\s*\)", all_css, re.IGNORECASE)
            ),
            "has_cormorant_or_playfair": ("cormorant" in all_css.lower()) or ("playfair" in all_css.lower()),
            "has_external_font_cdn": ("fonts.googleapis.com" in html_text.lower())
            or ("fonts.gstatic.com" in html_text.lower()),
        }
    elif task == "t2":
        report["canon"] = {
            "oklch_token_count": len(tokens),
            "has_responsive_media": "@media" in all_css,
            "prefers_reduced_motion": "prefers-reduced-motion" in all_css,
        }

    return report


if __name__ == "__main__":
    out = {}
    for slug in SLUGS:
        out[slug] = {}
        for task in ("t1", "t2", "t3"):
            out[slug][task] = audit_landing(os.path.join(BASE_DIR, slug, task), task)
    out_path = os.path.join(BASE_DIR, "static_audit.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print("Round 2 static audit saved to", out_path)
