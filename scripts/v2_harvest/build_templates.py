#!/usr/bin/env python3
"""Compile strict TypeScript (.ts), compute exact SHA-256 CSP hashes, and emit 4 golden templates + MANIFEST.json."""

import base64
import hashlib
import html
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from templates_data_a import (  # noqa: E402
    SHARED_ROBOTS_TXT_TEMPLATE,
    TEMPLATE_01_RU_SWISS,
    TEMPLATE_02_EN_DARK_SAAS,
)
from templates_data_b import (  # noqa: E402
    TEMPLATE_03_EN_NEOBRUTAL,
    TEMPLATE_04_RU_NORDIC,
)

HARVEST_DIR = "/mnt/rescue/projects/SmartLLM/data/harvest"
TEMPLATES_DIR = os.path.join(HARVEST_DIR, "templates")
NODE_BIN = "/usr/bin/node"
TS_MODULE_DIR = "/usr/lib/code/extensions/node_modules"
CURATED_DATE = "2026-11-15"


def sha256_b64(text: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


TS_HELPER_CJS = os.path.join(SCRIPT_DIR, "ts_strict_check.cjs")


def compile_and_typecheck_ts(ts_path: str) -> str:
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
        raise RuntimeError(f"TypeScript strict check failed for {ts_path}:\n{proc.stderr}")
    js_code = "\n" + proc.stdout.strip() + "\n"
    return js_code


def build_single_template(spec: dict) -> dict:
    folder = os.path.join(TEMPLATES_DIR, spec["slug"])
    os.makedirs(folder, exist_ok=True)

    ts_path = os.path.join(folder, "app.ts")
    with open(ts_path, "w", encoding="utf-8") as fh:
        fh.write(spec["ts_code"].strip() + "\n")

    compiled_js = compile_and_typecheck_ts(ts_path)
    css_block = "\n" + spec["css"].strip() + "\n"

    tokens_css_path = os.path.join(folder, "tokens.css")
    with open(tokens_css_path, "w", encoding="utf-8") as fh:
        fh.write(spec["css"].strip() + "\n")

    style_hash = sha256_b64(css_block)
    script_hash = sha256_b64(compiled_js)

    meta_csp = (
        f"default-src 'none'; "
        f"script-src 'self' '{script_hash}'; "
        f"style-src 'self' '{style_hash}'; "
        f"img-src 'self' data:; "
        f"font-src 'self'; "
        f"connect-src 'self'; "
        f"base-uri 'none'; "
        f"form-action 'self'; "
        f"object-src 'none'; "
        f"require-trusted-types-for 'script'"
    )

    header_csp = (
        f"default-src 'none'; "
        f"script-src 'self' '{script_hash}'; "
        f"style-src 'self' '{style_hash}'; "
        f"img-src 'self' data:; "
        f"font-src 'self'; "
        f"connect-src 'self'; "
        f"base-uri 'none'; "
        f"form-action 'self'; "
        f"frame-ancestors 'none'; "
        f"object-src 'none'; "
        f"require-trusted-types-for 'script'"
    )

    hreflang_lines = "\n".join(
        f'  <link rel="alternate" hreflang="{hl}" href="{html.escape(url, quote=True)}">'
        for hl, url in spec["hreflangs"].items()
    )
    jsonld_str = json.dumps(spec["json_ld"], ensure_ascii=False, indent=2)

    index_html = f"""<!DOCTYPE html>
<html lang="{spec['lang']}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{meta_csp}">
  <title>{html.escape(spec['title'])}</title>
  <meta name="description" content="{html.escape(spec['description'], quote=True)}">
  <link rel="canonical" href="{html.escape(spec['base_url'] + '/', quote=True)}">
{hreflang_lines}
  <meta property="og:type" content="website">
  <meta property="og:locale" content="{spec['og_locale']}">
  <meta property="og:url" content="{html.escape(spec['base_url'] + '/', quote=True)}">
  <meta property="og:title" content="{html.escape(spec['title'], quote=True)}">
  <meta property="og:description" content="{html.escape(spec['description'], quote=True)}">
  <style>{css_block}</style>
  <script type="application/ld+json">
{jsonld_str}
  </script>
</head>
<body>
{spec['body_html'].strip()}
  <script type="module">{compiled_js}</script>
</body>
</html>
"""

    with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index_html)

    headers_txt = (
        f"# Cloudflare Pages strict edge security headers for {spec['slug']}\n"
        f"# Curated: {CURATED_DATE} (RAG-only golden reference)\n"
        f"/*\n"
        f"  Content-Security-Policy: {header_csp}\n"
        f"  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload\n"
        f"  X-Content-Type-Options: nosniff\n"
        f"  X-Frame-Options: DENY\n"
        f"  Referrer-Policy: strict-origin-when-cross-origin\n"
        f"  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()\n"
        f"  Cross-Origin-Opener-Policy: same-origin\n"
        f"  Cross-Origin-Embedder-Policy: require-corp\n"
        f"  Cross-Origin-Resource-Policy: same-origin\n"
    )
    with open(os.path.join(folder, "_headers"), "w", encoding="utf-8") as fh:
        fh.write(headers_txt)

    with open(os.path.join(folder, "llms.txt"), "w", encoding="utf-8") as fh:
        fh.write(spec["llms_txt"].strip() + "\n")

    robots_txt = SHARED_ROBOTS_TXT_TEMPLATE.format(base_url=spec["base_url"])
    with open(os.path.join(folder, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(robots_txt)

    zimage_doc = {
        "template_slug": spec["slug"],
        "canon_id": spec["canon_id"],
        "provenance": {
            "source": "SmartLLM v2 Golden Starter Archetype",
            "curated_date": CURATED_DATE,
            "rag_only": True,
        },
        "prompts": spec["zimage_prompts"],
    }
    with open(os.path.join(folder, "zimage_prompts.json"), "w", encoding="utf-8") as fh:
        json.dump(zimage_doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    return {
        "slug": spec["slug"],
        "canon_id": spec["canon_id"],
        "lang": spec["lang"],
        "style_sha256": style_hash,
        "script_sha256": script_hash,
        "files": [
            "index.html",
            "tokens.css",
            "app.ts",
            "_headers",
            "llms.txt",
            "robots.txt",
            "zimage_prompts.json",
        ],
    }


def main() -> None:
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    specs = [
        TEMPLATE_01_RU_SWISS,
        TEMPLATE_02_EN_DARK_SAAS,
        TEMPLATE_03_EN_NEOBRUTAL,
        TEMPLATE_04_RU_NORDIC,
    ]
    built_templates = [build_single_template(s) for s in specs]

    cards_dir = os.path.join(HARVEST_DIR, "canon_cards")
    card_files = sorted(fn for fn in os.listdir(cards_dir) if fn.endswith(".json"))

    copy_jsonl = os.path.join(HARVEST_DIR, "copy_pairs", "copy_patterns_en_ru.jsonl")
    with open(copy_jsonl, "r", encoding="utf-8") as fh:
        copy_count = sum(1 for ln in fh if ln.strip())

    manifest = {
        "name": "SmartLLM v2 Web, Design & Bilingual Copywriting Canon Bank",
        "version": "2.0.0",
        "curated_date": CURATED_DATE,
        "rag_only": True,
        "forbid_calibration_mixing": True,
        "policy_ref": "OPUS_MASTER_PLAN_V2.md §1.D5 (L68) & TZ_carbon_orchestrator.md §4",
        "counts": {
            "canon_cards": len(card_files),
            "copy_pairs_en_ru": copy_count,
            "checklists": 11,
            "golden_templates": len(built_templates),
        },
        "schema_file": "canon_card.schema.json",
        "canon_cards": [f"canon_cards/{fn}" for fn in card_files],
        "copy_bank": [
            "copy_pairs/copy_patterns_en_ru.jsonl",
            "copy_pairs/ru_b2b_saas_editorial_tone_guide.md",
            "copy_pairs/en_conversion_aeo_copy_guide.md",
        ],
        "checklists": [
            "checklists/seo_aeo_geo_jsonld.json",
            "checklists/seo_aeo_geo_jsonld.md",
            "checklists/security_csp_headers.json",
            "checklists/security_csp_headers.md",
            "checklists/layout_wcag22_viewport.json",
            "checklists/layout_wcag22_viewport.md",
            "checklists/zimage_canon_prompts.json",
            "checklists/stack_architecture_patterns.json",
            "checklists/stack_architecture_patterns.md",
            "checklists/motion_gsap_choreography.json",
            "checklists/motion_gsap_choreography.md",
        ],
        "templates": built_templates,
    }

    manifest_path = os.path.join(HARVEST_DIR, "MANIFEST.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"Built {len(built_templates)} golden templates (TS 6.0.3 strict verified) and MANIFEST.json")


if __name__ == "__main__":
    main()
