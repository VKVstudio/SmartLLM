#!/usr/bin/env python3
"""SmartLLM Stage A Static, Security (CSP/Headers), SEO/AEO/GEO, OKLCH, Copy & TypeScript Auditor."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_SUITE_DIR_PATH = Path(__file__).resolve().parent
_SCRIPTS_DIR_PATH = _SUITE_DIR_PATH.parents[1] / "scripts"
for _p in (str(_SUITE_DIR_PATH), str(_SCRIPTS_DIR_PATH)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import platform_paths as pp  # noqa: E402
import code_checks as cc  # noqa: E402
import copy_checks as cpc  # noqa: E402

SUITE_DIR: str = str(pp.SUITE_DIR)
TASKS_JSON: str = str(pp.TASKS_JSON)
RUNS_DIR: str = str(pp.RUNS_DIR)
NODE_EXE: str = str(pp.NODE_EXE)
DAG_RUNNER: str = os.path.join(SUITE_DIR, "test_dag_runner.mjs")

# Re-export core helpers for backward compatibility
oklch_to_srgb = cc.oklch_to_srgb
relative_luminance_from_lin_rgb = cc.relative_luminance_from_lin_rgb
contrast_ratio = cc.contrast_ratio
parse_oklch_tokens = cc.parse_oklch_tokens
sha256_b64 = cc.sha256_b64
StructHTMLParser = cc.StructHTMLParser
_parse_cloudflare_headers = cc._parse_cloudflare_headers
apply_csp_postprocessor = cc.apply_csp_postprocessor
analyze_copy_hygiene = cpc.analyze_copy_hygiene
_strip_code_tags_and_markup = cc.strip_code_tags_and_markup
_normalize_data_css_and_empty_styles = cc.normalize_data_css_and_empty_styles
_csp_skeleton_html = cc.csp_skeleton_html
_csp_skeleton_headers = cc.csp_skeleton_headers


def audit_web_task(folder: str, task_spec: dict[str, Any], raw_security: dict[str, Any] | None = None) -> dict[str, Any]:
    task_id = task_spec["id"]
    req_files = task_spec.get("required_files", ["index.html"])
    expected_lang = task_spec.get("language", "en")
    report: dict[str, Any] = {
        "task_id": task_id,
        "category": task_spec["category"],
        "language": expected_lang,
        "canon": task_spec.get("canon", ""),
    }

    # 1. Check required files
    files_status: dict[str, dict[str, Any]] = {}
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

    with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
        html_text = fh.read()

    report["html_structurally_complete"] = "</html>" in html_text.lower()

    # Grade RAW security artifacts BEFORE or independent of packaging postprocessor (NEW-BUG-01 fix)
    if raw_security is None:
        raw_security = cc.audit_raw_csp_and_headers(folder)
    report["raw_csp"] = raw_security

    parser = StructHTMLParser()
    parser.feed(html_text)
    parser.flush_unclosed()

    # Load external local CSS if linked (e.g. T9 tokens.css)
    combined_css = "\n".join(parser.styles)
    tokens_css_path = os.path.join(folder, "tokens.css")
    if os.path.exists(tokens_css_path):
        with open(tokens_css_path, "r", encoding="utf-8", errors="replace") as fh:
            combined_css = fh.read() + "\n" + combined_css

    # Load external local JS if present (e.g. T9 app.js), excluding JSON-LD data blocks
    combined_js = "\n".join(
        sc["content"] for sc in parser.scripts if sc.get("content") and sc.get("type") != "application/ld+json"
    )
    app_js_path = os.path.join(folder, "app.js")
    if os.path.exists(app_js_path):
        with open(app_js_path, "r", encoding="utf-8", errors="replace") as fh:
            combined_js = fh.read() + "\n" + combined_js

    # 2. CSP verification (anchored to RAW model CSP presence & unsafe-inline check)
    meta_csp = parser.meta_csp or ""
    meta_csp_audit = cc.audit_csp_policy_string(meta_csp, is_header=False)
    csp_hashes_in_policy = set(re.findall(r"sha256-[A-Za-z0-9+/=]+", meta_csp))

    has_meta_csp = bool(raw_security.get("raw_meta_csp_present")) and bool(meta_csp)
    has_unsafe_inline = bool(raw_security.get("raw_has_unsafe_inline")) or meta_csp_audit["has_unsafe_inline"]

    style_hashes = []
    for idx, st in enumerate(parser.styles):
        if not st:
            continue
        h_exact = sha256_b64(st)
        style_hashes.append(
            {
                "index": idx,
                "len": len(st),
                "matched_exact": has_meta_csp and (h_exact in csp_hashes_in_policy),
            }
        )

    script_hashes = []
    jsonld_blocks = []
    for idx, sc in enumerate(parser.scripts):
        st_type = sc["type"]
        content = sc["content"]
        if st_type == "application/ld+json":
            jsonld_blocks.append(content)
        elif content and not sc.get("src"):
            h_exact = sha256_b64(content)
            script_hashes.append(
                {
                    "index": idx,
                    "type": st_type or "text/javascript",
                    "matched_exact": has_meta_csp and (h_exact in csp_hashes_in_policy),
                }
            )

    js_no_comments = re.sub(r"/\*.*?\*/", " ", combined_js, flags=re.DOTALL)
    js_no_comments = re.sub(r"(^|[ \t;{}(),])//[^\r\n]*", r"\1 ", js_no_comments, flags=re.MULTILINE)
    js_style_muts = re.findall(
        r"(?:\.style\.[A-Za-z_][A-Za-z0-9_]*\s*=|\.style\.cssText\s*=|\.style\.setProperty\s*\(|setAttribute\(\s*['\"]style['\"])",
        js_no_comments,
    )

    all_styles_ok = has_meta_csp and all(x["matched_exact"] for x in style_hashes)
    all_scripts_ok = has_meta_csp and all(x["matched_exact"] for x in script_hashes)

    report["csp"] = {
        "has_meta_csp": has_meta_csp,
        "has_unsafe_inline": has_unsafe_inline,
        "has_unsafe_inline_script": bool(raw_security.get("raw_has_unsafe_inline_script")) or meta_csp_audit["has_unsafe_inline_script"],
        "has_object_src_none": meta_csp_audit["has_object_src_none"],
        "has_require_trusted_types": meta_csp_audit["has_require_trusted_types"],
        "all_style_hashes_matched": all_styles_ok,
        "all_script_hashes_matched": all_scripts_ok,
        "inline_event_handlers_count": len(parser.inline_event_handlers),
        "js_style_mutations_count": len(js_style_muts),
        "raw_csp_passed": bool(raw_security.get("raw_csp_passed")),
    }

    # 3. External HTTP(S) resource URLs check
    allowed_prefixes = ("http://www.w3.org/", "https://www.w3.org/", "https://schema.org", "http://schema.org")
    asset_rels = {"stylesheet", "preload", "modulepreload", "icon", "shortcut icon", "apple-touch-icon", "manifest"}
    ext_resource_urls: list[str] = []
    info_urls: list[str] = []

    for img in parser.imgs:
        src = (img.get("src") or "").strip()
        if src.lower().startswith(("http://", "https://")) and not src.startswith(allowed_prefixes):
            ext_resource_urls.append(src)
    for _tag, src in parser.media_srcs:
        s_clean = src.strip()
        if s_clean.lower().startswith(("http://", "https://")) and not s_clean.startswith(allowed_prefixes):
            ext_resource_urls.append(s_clean)
    for lnk in parser.link_tags:
        href = (lnk.get("href") or "").strip()
        rel = (lnk.get("rel") or "").lower()
        if href.lower().startswith(("http://", "https://")) and not href.startswith(allowed_prefixes):
            rel_tokens = set(rel.split())
            if rel_tokens & asset_rels:
                ext_resource_urls.append(href)
            else:
                info_urls.append(href)
    for u in parser.svg_uses:
        s_clean = u.strip()
        if s_clean.lower().startswith(("http://", "https://")) and not s_clean.startswith(allowed_prefixes):
            ext_resource_urls.append(s_clean)
    for u in re.findall(r"""url\(\s*['"]?(https?://[^'"\s)>]+)['"]?\s*\)""", combined_css, re.IGNORECASE):
        if not u.startswith(allowed_prefixes):
            ext_resource_urls.append(u)
    for href in parser.a_hrefs:
        s_clean = href.strip()
        if s_clean.lower().startswith(("http://", "https://")) and not s_clean.startswith(allowed_prefixes):
            info_urls.append(s_clean)

    report["external_urls_in_attrs"] = ext_resource_urls
    report["informational_urls"] = sorted(set(info_urls))

    # 4. SEO Meta & Hreflang/Canonical check
    meta_names = {m.get("name", "").lower(): m.get("content", "") for m in parser.meta_tags if m.get("name")}
    meta_props = {m.get("property", "").lower(): m.get("content", "") for m in parser.meta_tags if m.get("property")}
    hreflang_info = cc.check_hreflang_and_canonical(parser.link_tags)
    report["seo_meta"] = {
        "has_title": bool(parser.title_text),
        "has_description": bool(meta_names.get("description")),
        "has_canonical": hreflang_info["has_canonical"],
        "canonical_href": hreflang_info["canonical_href"],
        "has_og_title": bool(meta_props.get("og:title")),
        "has_og_description": bool(meta_props.get("og:description")),
        "hreflang_tags": hreflang_info["hreflang_tags"],
        "has_hreflang": hreflang_info["has_hreflang"],
        "has_bilingual_en_ru_hreflang": hreflang_info["has_bilingual_en_ru_hreflang"],
        "has_x_default_hreflang": hreflang_info["has_x_default_hreflang"],
    }

    # 5. JSON-LD @graph & verbatim visible FAQ check
    if "llms.txt" in req_files or jsonld_blocks:
        report["json_ld"] = cc.check_json_ld_blocks(jsonld_blocks, html_text)

    # 6. _headers check (Cloudflare Pages parser + RFC 6797 HSTS + COOP/COEP/CORP)
    if "_headers" in req_files or os.path.exists(os.path.join(folder, "_headers")):
        headers_path = os.path.join(folder, "_headers")
        headers_report: dict[str, Any] = {"exists": os.path.exists(headers_path), "all_passed": False}
        if headers_report["exists"]:
            with open(headers_path, "r", encoding="utf-8", errors="replace") as fh:
                h_text = fh.read()
            parsed_hdr = _parse_cloudflare_headers(h_text)
            hdrs = parsed_hdr["headers"]
            headers_report["has_route_rule"] = bool(parsed_hdr["has_route_rule"])
            headers_report["routes_found"] = sorted(parsed_hdr.get("routes", {}).keys())
            if parsed_hdr.get("format_error"):
                headers_report["format_error"] = parsed_hdr["format_error"]

            csp_v = hdrs.get("content-security-policy", "")
            csp_hdr_audit = cc.audit_csp_policy_string(csp_v, is_header=True)
            hsts_info = cc.check_hsts_header(hdrs.get("strict-transport-security", ""))
            iso_info = cc.check_cross_origin_isolation_headers(hdrs)
            xcto_v = hdrs.get("x-content-type-options", "").lower()
            ref_v = hdrs.get("referrer-policy", "").lower()
            perm_v = hdrs.get("permissions-policy", "").lower()

            req_headers = {
                "Content-Security-Policy": bool(csp_v) and not csp_hdr_audit["has_unsafe_inline"],
                "frame-ancestors 'none'": csp_hdr_audit["has_frame_ancestors_none"],
                "Strict-Transport-Security": hsts_info["passed"],
                "X-Content-Type-Options": xcto_v == "nosniff" or "nosniff" in xcto_v,
                "Referrer-Policy": bool(ref_v),
                "Permissions-Policy": bool(perm_v) and perm_v.count("interest-cohort=()") <= 2,
                "Cross-Origin-Opener-Policy": iso_info["coop_same_origin"],
            }
            headers_report["checks"] = req_headers
            headers_report["hsts_details"] = hsts_info
            headers_report["cross_origin_isolation"] = iso_info
            headers_report["csp_details"] = {
                "has_object_src_none": csp_hdr_audit["has_object_src_none"],
                "has_require_trusted_types": csp_hdr_audit["has_require_trusted_types"],
                "has_unsafe_inline": csp_hdr_audit["has_unsafe_inline"],
            }
            headers_report["all_passed"] = headers_report["has_route_rule"] and all(req_headers.values())
        report["_headers"] = headers_report

    # 7. robots.txt AI crawler policy check (`SEO-ROBOT-AI`)
    if "robots.txt" in req_files or os.path.exists(os.path.join(folder, "robots.txt")):
        robots_path = os.path.join(folder, "robots.txt")
        robots_report: dict[str, Any] = {"exists": os.path.exists(robots_path)}
        if robots_report["exists"]:
            with open(robots_path, "r", encoding="utf-8", errors="replace") as fh:
                r_text = fh.read()
            robots_report.update(cc.check_robots_txt_ai_crawlers(r_text))
        report["robots_txt"] = robots_report

    # 8. llms.txt check
    if "llms.txt" in req_files or os.path.exists(os.path.join(folder, "llms.txt")):
        llms_path = os.path.join(folder, "llms.txt")
        llms_report: dict[str, Any] = {"exists": os.path.exists(llms_path)}
        if llms_report["exists"]:
            with open(llms_path, "r", encoding="utf-8", errors="replace") as fh:
                l_text = fh.read()
            llms_report["has_h1"] = bool(re.search(r"^#\s+\S+", l_text, re.MULTILINE))
            llms_report["has_blockquote"] = bool(re.search(r"^>\s+\S+", l_text, re.MULTILINE))
            llms_report["has_h2_sections"] = bool(re.search(r"^##\s+\S+", l_text, re.MULTILINE))
        report["llms_txt"] = llms_report

    # 9. HTML5 Semantics, Accessibility, Viewport `100dvh`/`100svh`, and Tailwind Ban
    label_fors = {l.get("for") for l in parser.labels if l.get("for")}
    inputs_labeled = sum(
        1
        for inp in parser.inputs
        if (inp.get("id") and inp.get("id") in label_fors) or inp.get("aria-label") or inp.get("aria-labelledby")
    )
    vh_hygiene = cc.check_viewport_vh_hygiene(combined_css)
    tailwind_check = cc.check_tailwind_ban(html_text, combined_css)

    report["semantics"] = {
        "html_lang": parser.html_lang,
        "h1_count": parser.h1_count,
        "landmarks": sorted(parser.landmarks),
        "svg_count": len(parser.svgs),
        "canvas_count": len(parser.canvases),
        "form_inputs_count": len(parser.inputs),
        "form_inputs_labeled": inputs_labeled,
        "has_prefers_reduced_motion": "prefers-reduced-motion" in combined_css,
        "has_scroll_padding_top": "scroll-padding-top" in combined_css.lower(),
        "viewport_vh_hygiene": vh_hygiene,
        "tailwind_ban": tailwind_check,
    }

    # 10. OKLCH Tokens & Semantic Contrast (NEW-BUG-04 fix)
    report["oklch"] = cc.evaluate_oklch_compliance(combined_css)

    # 11. Task-specific technical checks
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
    elif task_id == "t9" or "zimage_prompts.json" in req_files:
        zpath = os.path.join(folder, "zimage_prompts.json")
        z_valid = False
        z_count = 0
        z_exact_match = False
        if os.path.exists(zpath):
            try:
                with open(zpath, "r", encoding="utf-8", errors="replace") as fh:
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

    # 12. Language-aware Copy Hygiene across delivered artifacts (`expected_lang` passed!)
    raw_copy_texts = [html_text]
    no_code_html = re.sub(
        r"<(script|style|code|pre|svg)\b[^>]*>(?:.*?</\1>|.*$)",
        "\n",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    prose_copy_texts = [html_lib.unescape(re.sub(r"<[^>]+>", "\n", no_code_html))]
    for extra_name in ("llms.txt", "DESIGN.md", "app.js", "tokens.css", "robots.txt", "_headers", "zimage_prompts.json"):
        ep = os.path.join(folder, extra_name)
        if os.path.exists(ep):
            with open(ep, "r", encoding="utf-8", errors="replace") as fh:
                etxt = fh.read()
            raw_copy_texts.append(etxt)
            if extra_name in ("llms.txt", "DESIGN.md"):
                prose_copy_texts.append(etxt)
    report["copy_hygiene"] = analyze_copy_hygiene(
        raw_copy_texts,
        prose_copy_texts,
        expected_lang=expected_lang,
    )

    return report


def audit_typescript_task(folder: str, task_spec: dict[str, Any]) -> dict[str, Any]:
    req_files = task_spec.get("required_files", ["dag.ts"])
    ts_filename = req_files[0] if req_files else "dag.ts"
    dag_path = os.path.join(folder, ts_filename)
    expected_lang = task_spec.get("language", "en")
    report: dict[str, Any] = {
        "task_id": task_spec["id"],
        "category": task_spec.get("category", "typescript_coding"),
        "language": expected_lang,
        "canon": task_spec.get("canon", ""),
        "required_files": {
            ts_filename: {
                "exists": os.path.exists(dag_path),
                "size_bytes": os.path.getsize(dag_path) if os.path.exists(dag_path) else 0,
            }
        },
        "all_required_files_present": os.path.exists(dag_path) and os.path.getsize(dag_path) > 0,
    }
    if not os.path.exists(dag_path):
        report["error"] = f"{ts_filename} not found"
        return report

    with open(dag_path, "r", encoding="utf-8", errors="replace") as fh:
        dag_text = fh.read()
    report["copy_hygiene"] = analyze_copy_hygiene([dag_text], [dag_text], expected_lang=expected_lang)

    runner_script = (
        os.path.join(SUITE_DIR, "tasks", "t_backend_form_runner.mjs")
        if task_spec.get("id") == "t_backend_form"
        else DAG_RUNNER
    )
    proc = subprocess.run(
        [NODE_EXE, runner_script, dag_path],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
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


def audit_model_run(
    model_slug: str,
    tasks: list[dict[str, Any]],
    task_filter: set[str] | None = None,
) -> dict[str, Any]:
    model_dir = os.path.join(RUNS_DIR, model_slug)
    if not os.path.exists(model_dir):
        return {"error": f"Run directory {model_dir} does not exist"}

    out_file = os.path.join(model_dir, "static_audit.json")
    existing_report: dict[str, Any] = {}
    if task_filter and os.path.exists(out_file):
        try:
            with open(out_file, "r", encoding="utf-8", errors="replace") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                existing_report = loaded
        except Exception:
            existing_report = {}

    model_report: dict[str, Any] = {}
    for t in tasks:
        tid = t["id"]
        if task_filter and tid not in task_filter:
            if tid in existing_report:
                model_report[tid] = existing_report[tid]
            continue
        tfolder = os.path.join(model_dir, tid)
        if not os.path.exists(tfolder):
            model_report[tid] = {"status": "missing"}
            continue
        if t.get("category") == "typescript_coding":
            model_report[tid] = audit_typescript_task(tfolder, t)
        else:
            # 1. Grade RAW model files FIRST (NEW-BUG-01 fix)
            raw_sec = cc.audit_raw_csp_and_headers(tfolder)
            # 2. Run packaging placeholder substitution second (preserving all directives)
            csp_post = apply_csp_postprocessor(tfolder)
            # 3. Run full web task audit
            rep = audit_web_task(tfolder, t, raw_security=raw_sec)
            rep["csp_postprocessor"] = csp_post
            model_report[tid] = rep

    with open(out_file, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(model_report, fh, indent=2, ensure_ascii=False)
    return model_report


def main() -> None:
    parser = argparse.ArgumentParser(description="SmartLLM Offline Static + CSP + TypeScript Audit (v3)")
    parser.add_argument("models", nargs="*", help="Optional model folder slugs under eval/suite/runs/")
    parser.add_argument("--tasks", nargs="*", help="Optional task IDs to audit and merge into static_audit.json")
    args = parser.parse_args()

    with open(TASKS_JSON, "r", encoding="utf-8") as fh:
        tasks_data = json.load(fh)
    tasks = tasks_data["tasks"]
    task_filter = set(args.tasks) if args.tasks else None

    os.makedirs(RUNS_DIR, exist_ok=True)
    target_models = args.models if args.models else sorted(
        d for d in os.listdir(RUNS_DIR) if os.path.isdir(os.path.join(RUNS_DIR, d))
    )

    summary_path = os.path.join(SUITE_DIR, "results", "static_audit_all.json")
    all_reports: dict[str, Any] = {}
    if args.models and os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8", errors="replace") as fh:
                loaded_sum = json.load(fh)
            if isinstance(loaded_sum, dict):
                all_reports = loaded_sum
        except Exception:
            all_reports = {}

    for m in target_models:
        print(f"[AUDIT] Running static + CSP + tsc audit for {m} ...")
        all_reports[m] = audit_model_run(m, tasks, task_filter=task_filter)

    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(all_reports, fh, indent=2, ensure_ascii=False)
    print(f"Saved static audit summary to {summary_path}")


if __name__ == "__main__":
    main()
