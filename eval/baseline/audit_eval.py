import base64
import hashlib
import json
import math
import os
import re
import urllib.parse
from html.parser import HTMLParser

BASE_DIR = r"D:\projects\SmartLLM\eval\baseline"


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
            elif self._in_tag == "script":
                self.scripts.append({"type": self._in_script_type, "content": content})
            self._in_tag = None
            self._buf = []


def sha256_b64(text: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


def compute_pair_contrasts(tokens: dict, pairs: list[tuple[str, str]]) -> dict:
    res = {}
    for fg, bg in pairs:
        if fg in tokens and bg in tokens:
            res[f"{fg} on {bg}"] = contrast_ratio(tokens[fg]["luminance"], tokens[bg]["luminance"])
    return res


def audit_t1(folder: str) -> dict:
    report = {}
    html_path = os.path.join(folder, "index.html")
    if not os.path.exists(html_path):
        return {"error": "index.html not found"}

    with open(html_path, "r", encoding="utf-8") as fh:
        html_text = fh.read()

    parser = StructHTMLParser()
    parser.feed(html_text)
    parser.flush_unclosed()
    if not parser.styles and "<style" in html_text.lower():
        m_st = re.search(r"<style[^>]*>(.*)", html_text, re.DOTALL | re.IGNORECASE)
        if m_st:
            parser.styles.append(m_st.group(1))

    meta_csp = parser.meta_csp or ""
    csp_hashes_in_policy = set(re.findall(r"sha256-[A-Za-z0-9+/=]+", meta_csp))
    has_unsafe_inline = "'unsafe-inline'" in meta_csp.lower()

    style_hashes = []
    for idx, st in enumerate(parser.styles):
        h_exact = sha256_b64(st)
        h_strip = sha256_b64(st.strip())
        style_hashes.append(
            {
                "index": idx,
                "len": len(st),
                "sha256_exact": h_exact,
                "sha256_stripped": h_strip,
                "matched_exact": h_exact in csp_hashes_in_policy,
                "matched_stripped": h_strip in csp_hashes_in_policy,
            }
        )

    script_hashes = []
    jsonld_blocks = []
    for idx, sc in enumerate(parser.scripts):
        st_type = sc["type"]
        content = sc["content"]
        if st_type == "application/ld+json":
            jsonld_blocks.append(content)
        h_exact = sha256_b64(content)
        h_strip = sha256_b64(content.strip())
        script_hashes.append(
            {
                "index": idx,
                "type": st_type or "text/javascript",
                "len": len(content),
                "sha256_exact": h_exact,
                "sha256_stripped": h_strip,
                "matched_exact": h_exact in csp_hashes_in_policy,
                "matched_stripped": h_strip in csp_hashes_in_policy,
            }
        )

    report["csp"] = {
        "has_meta_csp": bool(meta_csp),
        "meta_csp": meta_csp,
        "has_unsafe_inline": has_unsafe_inline,
        "policy_hashes": sorted(csp_hashes_in_policy),
        "style_hashes": style_hashes,
        "script_hashes": script_hashes,
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
            parsed_ld = json.loads(jsonld_blocks[0])
            jsonld_report["valid_json"] = True
            graph = parsed_ld.get("@graph", [])
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
                q_in_html = item["q"] in html_text
                a_in_html = item["a"] in html_text
                verbatim_matches.append({"q": item["q"], "q_in_html": q_in_html, "a_in_html": a_in_html})
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
        "prefers_reduced_motion": "prefers-reduced-motion" in all_css,
    }

    tokens = parse_oklch_tokens(all_css)
    report["oklch_tokens"] = tokens
    report["contrasts"] = compute_pair_contrasts(
        tokens,
        [
            ("--text", "--bg"),
            ("--text", "--bg-soft"),
            ("--text", "--panel"),
            ("--text", "--surface"),
            ("--text", "--surface-2"),
            ("--muted", "--bg"),
            ("--muted", "--bg-soft"),
            ("--muted", "--panel"),
            ("--muted", "--surface"),
            ("--accent", "--bg"),
            ("--accent", "--surface"),
            ("--accent-text", "--bg"),
            ("--accent-text", "--panel"),
            ("--on-accent", "--accent"),
            ("--accent-ink", "--accent"),
            ("--c-text", "--c-bg"),
            ("--c-text", "--c-surface"),
            ("--c-text-muted", "--c-bg"),
            ("--c-text-muted", "--c-surface"),
            ("--c-accent-dark", "--c-bg"),
            ("--c-accent-dark", "--c-surface"),
            ("--c-accent", "--c-bg"),
            ("--c-footer-text", "--c-footer-bg"),
        ],
    )
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

    return report


def audit_t2(folder: str) -> dict:
    html_path = os.path.join(folder, "index.html")
    if not os.path.exists(html_path):
        return {"error": "index.html not found"}
    with open(html_path, "r", encoding="utf-8") as fh:
        html_text = fh.read()
    parser = StructHTMLParser()
    parser.feed(html_text)
    parser.flush_unclosed()
    if not parser.styles and "<style" in html_text.lower():
        m_st = re.search(r"<style[^>]*>(.*)", html_text, re.DOTALL | re.IGNORECASE)
        if m_st:
            parser.styles.append(m_st.group(1))
    all_css = "\n".join(parser.styles)
    tokens = parse_oklch_tokens(all_css)
    return {
        "h1_count": parser.h1_count,
        "landmarks": sorted(parser.landmarks),
        "oklch_token_count": len(tokens),
        "oklch_tokens": tokens,
        "contrasts": compute_pair_contrasts(
            tokens,
            [
                ("--ink", "--bg"),
                ("--ink", "--surface"),
                ("--ink-soft", "--bg"),
                ("--ink-soft", "--surface"),
                ("--muted", "--bg"),
                ("--accent-ink", "--bg"),
                ("--on-accent", "--accent"),
                ("--on-accent", "--accent-deep"),
                ("--text", "--bg"),
                ("--text", "--bg-card"),
                ("--text-muted", "--bg"),
                ("--text-muted", "--bg-card"),
                ("--accent", "--bg"),
                ("--teal-text", "--bg"),
                ("--btn-text", "--btn-bg"),
            ],
        ),
        "has_responsive_375_or_media": "@media" in all_css,
        "prefers_reduced_motion": "prefers-reduced-motion" in all_css,
        "external_urls": re.findall(
            r"""(?:src|href|url)\s*(?:=|\()\s*['"]?(https?://[^'"\s)>]+)""", html_text, re.IGNORECASE
        ),
    }


if __name__ == "__main__":
    out = {}
    for slug in ("qwen3.8-flash", "ling-3.0-flash-vl"):
        out[slug] = {
            "t1": audit_t1(os.path.join(BASE_DIR, slug, "t1")),
            "t2": audit_t2(os.path.join(BASE_DIR, slug, "t2")),
        }
    out_path = os.path.join(BASE_DIR, "static_audit.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print("Static audit saved to", out_path)
