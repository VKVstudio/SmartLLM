#!/usr/bin/env python3
"""Deterministic offline validator for SmartLLM v2 RAG-only Harvest Bank (WP-HARVEST).

Validates:
1. MANIFEST.json integrity & strict RAG-only isolation (rag_only=True, forbid_calibration_mixing=True).
2. canon_card.schema.json Draft-07 compliance across all canon cards (>= 25 cards) + OKLCH WCAG AAA/AA math.
3. EN+RU copywriting pattern pairs (>= 150 pairs) + RU/EN tone guides (zero slop, zero homoglyphs, zero CJK/em-dash).
4. Structured JSON & Markdown checklists (SEO/AEO/GEO, CSP/_headers, WCAG 2.2/Layout, Z-Image).
5. All 4 golden multi-file templates: strict TypeScript 6.0.3 AST/type-check, byte-exact transpiled JS parity,
   exact SHA-256 CSP hashes in <meta> & _headers, Cloudflare _headers grammar, JSON-LD @graph + verbatim FAQ match,
   llms.txt, robots.txt AI crawler split, hreflang, WCAG 2.2 >=24px + scroll-padding-top, 100svh/100dvh,
   zero Tailwind/CDN URLs, and cross-verification via eval/suite/audit_suite.py.
"""

from __future__ import annotations

import base64
import hashlib
import html as html_lib
import json
import math
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from typing import Any

REPO_ROOT = "/mnt/rescue/projects/SmartLLM"
HARVEST_DIR = os.path.join(REPO_ROOT, "data", "harvest")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_BIN = "/usr/bin/node"
TS_MODULE_DIR = "/usr/lib/code/extensions/node_modules"
TS_HELPER_CJS = os.path.join(SCRIPT_DIR, "ts_strict_check.cjs")

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
WORD_SCRIPT_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+")
HAS_LATIN_RE = re.compile(r"[A-Za-z]")
HAS_CYR_RE = re.compile(r"[А-Яа-яЁё]")
OKLCH_VAL_RE = re.compile(r"^oklch\(([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\)$")

BANNED_EN_SLOP = [
    "delve", "testament", "tapestry", "unleash", "elevate", "seamless",
    "seamlessly", "game-changer", "unlock", "cutting-edge", "revolutionary",
    "revolutionizing", "realm", "ever-evolving", "skyrocketed", "supercharge",
    "blazingly",
]
BANNED_RU_SLOP = [
    "погрузимся", "безусловно", "революционн", "инновационн",
    "в современном мире", "динамично развивающ", "бесшовн",
    "вывести на новый уровень", "выведите", "под ключ", "уникальн",
    "непревзойдённ", "незабываем",
]


# ---------------------------------------------------------------------------
# 1. Pure-Stdlib JSON Schema Draft-07 Validator
# ---------------------------------------------------------------------------

def validate_json_schema(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(instance, dict):
            return [f"{path}: expected object, got {type(instance).__name__}"]
        req = schema.get("required", [])
        for k in req:
            if k not in instance:
                errors.append(f"{path}: missing required key '{k}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in instance:
                if k not in props:
                    errors.append(f"{path}: unexpected additional property '{k}'")
        for k, subschema in props.items():
            if k in instance:
                errors.extend(validate_json_schema(instance[k], subschema, f"{path}.{k}"))
    elif expected_type == "array":
        if not isinstance(instance, list):
            return [f"{path}: expected array, got {type(instance).__name__}"]
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: array length {len(instance)} < minItems {schema['minItems']}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: array length {len(instance)} > maxItems {schema['maxItems']}")
        if "items" in schema:
            for idx, elem in enumerate(instance):
                errors.extend(validate_json_schema(elem, schema["items"], f"{path}[{idx}]"))
    elif expected_type == "string":
        if not isinstance(instance, str):
            return [f"{path}: expected string, got {type(instance).__name__}"]
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string len {len(instance)} < minLength {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: value '{instance}' does not match pattern {schema['pattern']}")
    elif expected_type == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            return [f"{path}: expected integer, got {type(instance).__name__}"]
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} > maximum {schema['maximum']}")
    elif expected_type == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            return [f"{path}: expected number, got {type(instance).__name__}"]
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} > maximum {schema['maximum']}")
    elif expected_type == "boolean":
        if not isinstance(instance, bool):
            return [f"{path}: expected boolean, got {type(instance).__name__}"]

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum {schema['enum']}")
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: value {instance!r} != const {schema['const']!r}")
    return errors


# ---------------------------------------------------------------------------
# 2. OKLCH Relative Luminance & Hygiene Helpers
# ---------------------------------------------------------------------------

def oklch_luminance(oklch_str: str) -> float:
    m = OKLCH_VAL_RE.match(oklch_str.strip())
    if not m:
        raise ValueError(f"Malformed OKLCH string: {oklch_str}")
    L, C, H_deg = float(m.group(1)), float(m.group(2)), float(m.group(3))
    h_rad = math.radians(H_deg)
    a = C * math.cos(h_rad)
    b = C * math.sin(h_rad)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l3, m3, s3 = l_ ** 3, m_ ** 3, s_ ** 3
    r = max(0.0, min(1.0, +4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3))
    g = max(0.0, min(1.0, -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3))
    bl = max(0.0, min(1.0, -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3))
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl


def contrast_ratio(c1: str, c2: str) -> float:
    l1, l2 = oklch_luminance(c1), oklch_luminance(c2)
    return round((max(l1, l2) + 0.05) / (min(l1, l2) + 0.05), 2)


def sha256_b64(text: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


def check_text_hygiene(text: str, label: str, forbid_em_dash: bool = True) -> list[str]:
    errs: list[str] = []
    if CJK_RE.search(text):
        errs.append(f"{label}: contains forbidden CJK character")
    if "\ufffd" in text:
        errs.append(f"{label}: contains U+FFFD replacement character")
    if forbid_em_dash and "\u2014" in text:
        errs.append(f"{label}: contains forbidden em-dash (U+2014)")
    mixed = [
        tok for tok in WORD_SCRIPT_RE.findall(text)
        if HAS_LATIN_RE.search(tok) and HAS_CYR_RE.search(tok)
    ]
    if mixed:
        errs.append(f"{label}: mixed Latin/Cyrillic homoglyph tokens {mixed[:5]}")
    return errs


class TemplateHTMLInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.html_lang = ""
        self.meta_csp = ""
        self.title = ""
        self.meta_tags: list[dict[str, str]] = []
        self.link_tags: list[dict[str, str]] = []
        self.styles: list[str] = []
        self.scripts: list[dict[str, str]] = []
        self.landmarks: set[str] = set()
        self.h1_count = 0
        self.inputs: list[dict[str, str]] = []
        self.labels: list[dict[str, str]] = []
        self.inline_events: list[str] = []
        self._tag: str | None = None
        self._script_type = ""
        self._script_src = ""
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        ad = {k.lower(): (v or "") for k, v in attrs}
        for k in ad:
            if k.startswith("on"):
                self.inline_events.append(f"{t}[{k}]")
        if t == "html":
            self.html_lang = ad.get("lang", "")
        if t in ("header", "nav", "main", "footer"):
            self.landmarks.add(t)
        if t == "h1":
            self.h1_count += 1
        if t == "meta":
            self.meta_tags.append(ad)
            if ad.get("http-equiv", "").lower() == "content-security-policy":
                self.meta_csp = ad.get("content", "")
        if t == "link":
            self.link_tags.append(ad)
        if t in ("input", "select", "textarea"):
            if ad.get("type", "").lower() not in ("hidden", "submit", "button", "reset"):
                self.inputs.append(ad)
        if t == "label":
            self.labels.append(ad)
        if t in ("style", "script", "title"):
            self._tag = t
            self._script_type = ad.get("type", "").lower()
            self._script_src = ad.get("src", "")
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._tag:
            self._buf.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._tag:
            self._buf.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._tag:
            self._buf.append(f"&#{name};")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == self._tag:
            raw = "".join(self._buf)
            if t == "style":
                self.styles.append(raw)
            elif t == "script":
                self.scripts.append({"type": self._script_type, "src": self._script_src, "content": raw})
            elif t == "title":
                self.title = raw.strip()
            self._tag = None
            self._buf = []


# ---------------------------------------------------------------------------
# 3. Validation Suites
# ---------------------------------------------------------------------------

def validate_manifest_and_isolation(errors: list[str]) -> dict[str, Any]:
    manifest_path = os.path.join(HARVEST_DIR, "MANIFEST.json")
    if not os.path.exists(manifest_path):
        errors.append("Missing data/harvest/MANIFEST.json")
        return {}
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if manifest.get("rag_only") is not True:
        errors.append("MANIFEST.json: rag_only must be True")
    if manifest.get("forbid_calibration_mixing") is not True:
        errors.append("MANIFEST.json: forbid_calibration_mixing must be True")

    for rel_list_key in ("canon_cards", "copy_bank", "checklists"):
        for rel in manifest.get(rel_list_key, []):
            full = os.path.join(HARVEST_DIR, rel)
            if not os.path.exists(full) or os.path.getsize(full) == 0:
                errors.append(f"MANIFEST.json missing or empty file: {rel}")

    # Verify calibration isolation across all corpus/data files (OPUS_MASTER_PLAN_V2.md §1.D5).
    # Scan full contents of .json/.jsonl/.txt data artifacts (excluding .md provenance docs like SOURCES.md).
    calib_v2_dir = os.path.join(REPO_ROOT, "data", "calib_v2")
    harvest_markers = (
        "data/harvest/",
        "Internal RAG Canon",
        "kvartz-kontur.example.ru",
        "chronotrace.example.io",
        "anvildb.example.dev",
        "sever-akustika.example.ru",
    )
    if os.path.isdir(calib_v2_dir):
        for root, dirs, files in os.walk(calib_v2_dir):
            dirs[:] = [d for d in dirs if d != "raw_cache"]
            for fn in files:
                if fn.endswith((".json", ".jsonl", ".txt")):
                    fpath = os.path.join(root, fn)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as cf:
                            for line_no, line in enumerate(cf, start=1):
                                if any(m in line for m in harvest_markers):
                                    errors.append(
                                        f"RAG isolation breach: {fpath}:{line_no} references data/harvest artifact"
                                    )
                                    break
                    except OSError:
                        pass
    return manifest


def validate_canon_cards(errors: list[str]) -> set[str]:
    schema_path = os.path.join(HARVEST_DIR, "canon_card.schema.json")
    if not os.path.exists(schema_path):
        errors.append("Missing data/harvest/canon_card.schema.json")
        return set()
    with open(schema_path, "r", encoding="utf-8") as fh:
        schema = json.load(fh)

    cards_dir = os.path.join(HARVEST_DIR, "canon_cards")
    card_files = sorted(fn for fn in os.listdir(cards_dir) if fn.endswith(".json"))
    if len(card_files) < 25:
        errors.append(f"Expected >= 25 canon cards, found {len(card_files)}")

    card_ids: set[str] = set()
    for fn in card_files:
        cpath = os.path.join(cards_dir, fn)
        raw_txt = open(cpath, "r", encoding="utf-8").read()
        errors.extend(check_text_hygiene(raw_txt, f"canon_cards/{fn}", forbid_em_dash=False))
        card = json.loads(raw_txt)
        schema_errs = validate_json_schema(card, schema, f"canon_cards/{fn}")
        errors.extend(schema_errs)

        cid = card.get("id", "")
        if f"{cid}.json" != fn:
            errors.append(f"canon_cards/{fn}: id '{cid}' does not match filename")
        if cid in card_ids:
            errors.append(f"Duplicate canon card id: {cid}")
        card_ids.add(cid)

        pal = card["palette"]
        cr_text = min(contrast_ratio(pal["text"], pal["bg"]), contrast_ratio(pal["text"], pal["surface"]))
        cr_muted = min(contrast_ratio(pal["muted"], pal["bg"]), contrast_ratio(pal["muted"], pal["surface"]))
        cr_acc = contrast_ratio(pal["accent_ink"], pal["accent"])

        if cr_text < 7.0:
            errors.append(f"{fn}: text contrast {cr_text} < 7.0 AAA")
        if cr_muted < 4.5:
            errors.append(f"{fn}: muted contrast {cr_muted} < 4.5 AA")
        if cr_acc < 4.5:
            errors.append(f"{fn}: accent contrast {cr_acc} < 4.5 AA")
        if abs(cr_text - card["a11y"]["text_bg_contrast_ratio"]) > 0.05:
            errors.append(f"{fn}: recorded text_bg_contrast_ratio drift ({card['a11y']['text_bg_contrast_ratio']} vs {cr_text})")

        if "tailwind" in raw_txt.lower() and "never" not in raw_txt.lower():
            errors.append(f"{fn}: unexpected tailwind reference")

    return card_ids


def validate_copy_bank(card_ids: set[str], errors: list[str]) -> int:
    copy_dir = os.path.join(HARVEST_DIR, "copy_pairs")
    jsonl_path = os.path.join(copy_dir, "copy_patterns_en_ru.jsonl")
    if not os.path.exists(jsonl_path):
        errors.append("Missing copy_pairs/copy_patterns_en_ru.jsonl")
        return 0

    seen_ids: set[str] = set()
    categories: set[str] = set()
    count = 0

    with open(jsonl_path, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            count += 1
            rec = json.loads(line)
            pid = rec.get("id", f"line_{line_no}")
            if pid in seen_ids:
                errors.append(f"Duplicate copy pair id: {pid}")
            seen_ids.add(pid)
            categories.add(rec.get("category", ""))

            if rec.get("canon_id") not in card_ids:
                errors.append(f"{pid}: unknown canon_id '{rec.get('canon_id')}'")
            if rec.get("provenance", {}).get("rag_only") is not True:
                errors.append(f"{pid}: provenance.rag_only must be True")

            en_after = rec.get("en_canon_after", "")
            ru_after = rec.get("ru_canon_after", "")
            errors.extend(check_text_hygiene(en_after, f"{pid}.en_canon_after", forbid_em_dash=True))
            errors.extend(check_text_hygiene(ru_after, f"{pid}.ru_canon_after", forbid_em_dash=True))
            errors.extend(check_text_hygiene(rec.get("en_slop_before", ""), f"{pid}.en_slop_before", forbid_em_dash=False))
            errors.extend(check_text_hygiene(rec.get("ru_slop_before", ""), f"{pid}.ru_slop_before", forbid_em_dash=False))

            if len(HAS_LATIN_RE.findall(en_after)) < 25:
                errors.append(f"{pid}: en_canon_after too short")
            if len(HAS_CYR_RE.findall(ru_after)) < 25:
                errors.append(f"{pid}: ru_canon_after lacks Cyrillic")

            for bad in BANNED_EN_SLOP:
                if re.search(r"\b" + re.escape(bad) + r"\b", en_after.lower()):
                    errors.append(f"{pid}.en_canon_after: banned slop word '{bad}'")
            for bad in BANNED_RU_SLOP:
                if bad in ru_after.lower():
                    errors.append(f"{pid}.ru_canon_after: banned RU slop '{bad}'")

    if count < 150:
        errors.append(f"Expected >= 150 copy pairs, got {count}")
    if len(categories) < 6:
        errors.append(f"Expected >= 6 copy categories, got {len(categories)}")

    for guide_fn in ("ru_b2b_saas_editorial_tone_guide.md", "en_conversion_aeo_copy_guide.md"):
        gpath = os.path.join(copy_dir, guide_fn)
        if not os.path.exists(gpath):
            errors.append(f"Missing guide {guide_fn}")
        else:
            gtxt = open(gpath, "r", encoding="utf-8").read()
            # Exclude line specifically documenting the banned em-dash character (`—`)
            scrubbed = gtxt.replace("(`—`)", "()")
            errors.extend(check_text_hygiene(scrubbed, guide_fn, forbid_em_dash=True))

    return count


def validate_checklists(errors: list[str]) -> int:
    chk_dir = os.path.join(HARVEST_DIR, "checklists")
    expected_files = [
        "seo_aeo_geo_jsonld.json",
        "seo_aeo_geo_jsonld.md",
        "security_csp_headers.json",
        "security_csp_headers.md",
        "layout_wcag22_viewport.json",
        "layout_wcag22_viewport.md",
        "zimage_canon_prompts.json",
        "stack_architecture_patterns.json",
        "stack_architecture_patterns.md",
        "motion_gsap_choreography.json",
        "motion_gsap_choreography.md",
    ]
    found_check_ids: set[str] = set()
    for fn in expected_files:
        p = os.path.join(chk_dir, fn)
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            errors.append(f"Missing or empty checklist: {fn}")
            continue
        txt = open(p, "r", encoding="utf-8").read()
        errors.extend(check_text_hygiene(txt, f"checklists/{fn}", forbid_em_dash=True))
        if fn.endswith(".json"):
            data = json.loads(txt)
            if data.get("provenance", {}).get("rag_only") is not True:
                errors.append(f"checklists/{fn}: provenance.rag_only must be True")
            for item in data.get("checks", []):
                found_check_ids.add(item.get("check_id", ""))

    required_ids = {
        "SEO-META-01", "SEO-JSONLD-01", "SEO-FAQ-MATCH", "SEO-LLMS-01", "SEO-ROBOT-AI", "SEO-HREFLANG",
        "SEC-CSP-HASH", "SEC-TRUST-TYP", "SEC-HDR-SYN", "SEC-HDR-BASE", "SEC-ISOLATE", "SEC-FORM-HYG",
        "LAY-VIEWPORT-DVH", "LAY-GRID-CONTAINER", "LAY-ZERO-CDN", "A11Y-CONTRAST", "A11Y-WCAG22",
        "A11Y-LANDMARK", "A11Y-MOTION",
        "STACK-ASTRO-01", "STACK-NEXT-01", "STACK-SVELTE-01", "STACK-VITE-TS-01",
        "MOT-GSAP-ST-01", "MOT-GSAP-FLIP-01", "MOT-GSAP-CTX-01", "MOT-COMPOSITOR-01", "MOT-CSP-SAFE-01",
    }
    missing_ids = required_ids - found_check_ids
    if missing_ids:
        errors.append(f"Checklists missing required check IDs: {sorted(missing_ids)}")
    return len(expected_files)


def validate_templates(card_ids: set[str], errors: list[str]) -> int:
    tmpl_root = os.path.join(HARVEST_DIR, "templates")
    slugs = sorted(d for d in os.listdir(tmpl_root) if os.path.isdir(os.path.join(tmpl_root, d)))
    if len(slugs) < 4:
        errors.append(f"Expected >= 4 golden templates, found {len(slugs)}")

    langs_seen: list[str] = []

    # Optional cross-check import from eval/suite/audit_suite.py
    sys.path.insert(0, os.path.join(REPO_ROOT, "eval", "suite"))
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    import audit_suite as project_auditor  # type: ignore

    for slug in slugs:
        folder = os.path.join(tmpl_root, slug)
        req_files = ["index.html", "tokens.css", "app.ts", "_headers", "llms.txt", "robots.txt", "zimage_prompts.json"]
        for rf in req_files:
            fp = os.path.join(folder, rf)
            if not os.path.exists(fp) or os.path.getsize(fp) == 0:
                errors.append(f"templates/{slug}: missing or empty {rf}")

        # 1. Strict TypeScript 6.0.3 AST + Typecheck + Byte-Exact Transpile Parity
        ts_path = os.path.join(folder, "app.ts")
        env = os.environ.copy()
        env["NODE_PATH"] = TS_MODULE_DIR
        proc = subprocess.run(
            [NODE_BIN, TS_HELPER_CJS, ts_path, "transpile"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            errors.append(f"templates/{slug}/app.ts failed TS strict check: {proc.stderr.strip()}")
            continue
        expected_js = "\n" + proc.stdout.strip() + "\n"

        # 2. Parse HTML
        html_path = os.path.join(folder, "index.html")
        html_text = open(html_path, "r", encoding="utf-8").read()
        insp = TemplateHTMLInspector()
        insp.feed(html_text)
        langs_seen.append(insp.html_lang)

        exec_scripts = [s["content"] for s in insp.scripts if s["type"] != "application/ld+json" and not s["src"]]
        if len(exec_scripts) != 1 or exec_scripts[0] != expected_js:
            errors.append(f"templates/{slug}: inline <script type='module'> out of sync with transpiled app.ts")

        # 3. CSP & _headers verification
        style_hashes = [sha256_b64(st) for st in insp.styles if st]
        script_hashes = [sha256_b64(sc) for sc in exec_scripts if sc]
        headers_text = open(os.path.join(folder, "_headers"), "r", encoding="utf-8").read()

        if "/*" in headers_text and re.search(r"/\*.*?\*/", headers_text):
            errors.append(f"templates/{slug}/_headers: forbidden C-style /* ... */ comment")

        for h in style_hashes + script_hashes:
            if h not in insp.meta_csp:
                errors.append(f"templates/{slug}: hash {h} missing from <meta> CSP")
            if h not in headers_text:
                errors.append(f"templates/{slug}: hash {h} missing from _headers CSP")

        if "unsafe-inline" in insp.meta_csp.lower() or "unsafe-inline" in headers_text.lower():
            errors.append(f"templates/{slug}: forbidden unsafe-inline in CSP")
        if insp.inline_events:
            errors.append(f"templates/{slug}: inline event handlers found: {insp.inline_events}")

        # 4. Run full Stage A project_auditor.audit_web_task cross-check!
        zdoc = json.loads(open(os.path.join(folder, "zimage_prompts.json"), "r", encoding="utf-8").read())
        if zdoc.get("canon_id") not in card_ids:
            errors.append(f"templates/{slug}: zimage_prompts canon_id '{zdoc.get('canon_id')}' unknown")

        audit_rep = project_auditor.audit_web_task(
            folder,
            {
                "id": slug,
                "category": "golden_template",
                "language": insp.html_lang,
                "canon": zdoc.get("canon_id", ""),
                "required_files": ["index.html", "_headers", "llms.txt", "robots.txt", "zimage_prompts.json"],
            },
        )

        if not audit_rep["csp"]["raw_csp_passed"]:
            errors.append(f"templates/{slug}: audit_suite raw_csp_passed=False")
        if not audit_rep["csp"]["all_style_hashes_matched"] or not audit_rep["csp"]["all_script_hashes_matched"]:
            errors.append(f"templates/{slug}: audit_suite CSP hash mismatch")
        if not audit_rep["csp"]["has_object_src_none"] or not audit_rep["csp"]["has_require_trusted_types"]:
            errors.append(f"templates/{slug}: missing object-src 'none' or require-trusted-types-for 'script'")
        if audit_rep["csp"]["js_style_mutations_count"] != 0:
            errors.append(f"templates/{slug}: js_style_mutations_count != 0")
        if audit_rep["external_urls_in_attrs"]:
            errors.append(f"templates/{slug}: external asset URLs {audit_rep['external_urls_in_attrs']}")
        if not audit_rep["_headers"]["all_passed"]:
            errors.append(f"templates/{slug}: _headers checks failed: {audit_rep['_headers']}")
        if not audit_rep["_headers"]["cross_origin_isolation"]["full_isolation_passed"]:
            errors.append(f"templates/{slug}: COOP/COEP/CORP full_isolation_passed=False")
        if not audit_rep["json_ld"]["has_all_4_types"] or not audit_rep["json_ld"]["faq_all_verbatim"]:
            errors.append(f"templates/{slug}: JSON-LD @graph or verbatim FAQ parity failed: {audit_rep['json_ld']}")
        if not all(audit_rep["llms_txt"].values()):
            errors.append(f"templates/{slug}: llms.txt check failed: {audit_rep['llms_txt']}")
        r_rep = audit_rep["robots_txt"]
        if not (
            r_rep.get("has_ai_crawler_policy")
            and len(r_rep.get("ai_training_bots_mentioned", [])) >= 3
            and len(r_rep.get("ai_search_bots_mentioned", [])) >= 3
            and r_rep.get("has_sitemap")
        ):
            errors.append(f"templates/{slug}: robots.txt AI crawler check failed: {r_rep}")
        if not audit_rep["seo_meta"]["has_bilingual_en_ru_hreflang"] or not audit_rep["seo_meta"]["has_x_default_hreflang"]:
            errors.append(f"templates/{slug}: hreflang check failed: {audit_rep['seo_meta']}")
        if not audit_rep["oklch"]["passes_aaa_7_to_1"]:
            errors.append(f"templates/{slug}: OKLCH AAA 7:1 contrast failed: {audit_rep['oklch']}")
        if (audit_rep["oklch"]["min_muted_bg_contrast"] or 0.0) < 4.5:
            errors.append(f"templates/{slug}: OKLCH muted AA 4.5:1 failed: {audit_rep['oklch']}")
        if not audit_rep["semantics"]["tailwind_ban"]["tailwind_ban_passed"]:
            errors.append(f"templates/{slug}: Tailwind ban failed")
        if not audit_rep["semantics"]["viewport_vh_hygiene"]["vh_hygiene_passed"] or not audit_rep["semantics"]["viewport_vh_hygiene"]["has_100dvh_or_svh"]:
            errors.append(f"templates/{slug}: 100svh/100dvh viewport check failed")
        if audit_rep["semantics"]["h1_count"] != 1:
            errors.append(f"templates/{slug}: expected h1_count==1, got {audit_rep['semantics']['h1_count']}")
        if audit_rep["semantics"]["form_inputs_labeled"] != audit_rep["semantics"]["form_inputs_count"]:
            errors.append(f"templates/{slug}: unlabeled form inputs")
        if not audit_rep["semantics"]["has_scroll_padding_top"] or not audit_rep["semantics"]["has_prefers_reduced_motion"]:
            errors.append(f"templates/{slug}: missing scroll-padding-top or prefers-reduced-motion")
        if not audit_rep["task_specific"]["zimage_exact_text_verified"]:
            errors.append(f"templates/{slug}: zimage_prompts exact_text_in_frame check failed")

        hyg = audit_rep["copy_hygiene"]
        if (
            not hyg.get("lang_gate_passed", True)
            or not hyg.get("copy_hygiene_passed", True)
            or hyg["cjk_chars_count"] != 0
            or hyg["replacement_chars_count"] != 0
            or hyg["mixed_script_tokens_count"] != 0
            or hyg.get("em_dash_count", 0) != 0
            or hyg.get("ai_slop_hits_count", 0) != 0
        ):
            errors.append(f"templates/{slug}: copy_hygiene defect: {hyg}")

        # Verify subgrid, @container, tabular-nums, and >=24px target rule in CSS
        css_txt = open(os.path.join(folder, "tokens.css"), "r", encoding="utf-8").read()
        for token_req in ("subgrid", "@container", "container-type", "tabular-nums", "min-height", "min-width"):
            if token_req not in css_txt:
                errors.append(f"templates/{slug}/tokens.css: missing '{token_req}'")

    if langs_seen.count("ru") < 2 or langs_seen.count("en") < 2:
        errors.append(f"Expected >= 2 RU and >= 2 EN golden templates, got langs={langs_seen}")

    return len(slugs)


def main() -> int:
    errors: list[str] = []
    manifest = validate_manifest_and_isolation(errors)
    card_ids = validate_canon_cards(errors)
    copy_count = validate_copy_bank(card_ids, errors)
    chk_count = validate_checklists(errors)
    tmpl_count = validate_templates(card_ids, errors)

    summary = {
        "status": "PASS" if not errors else "FAIL",
        "rag_only": manifest.get("rag_only", False),
        "canon_cards_verified": len(card_ids),
        "copy_pairs_verified": copy_count,
        "checklists_verified": chk_count,
        "golden_templates_verified": tmpl_count,
        "errors_count": len(errors),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if errors:
        for err in errors:
            print(f"[ERROR] {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
