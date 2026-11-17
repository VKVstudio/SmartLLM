#!/usr/bin/env python3
"""Comprehensive Stage A Harness v3 Unit & Integration Test Suite (`WP-A1`).

Proves every fixed bug (`NEW-BUG-01..07`, `CODE-01..04`, WCAG 2.2, AI crawlers,
COOP/COEP/CORP, hreflang, OKLCH semantic contrast, 100dvh/100svh, Tailwind ban,
in-process TypeScript 6.0.3 + comment-stripping regex, Linux /proc telemetry +
PLE Rss check, and eval_gate_v1.yaml SLA gates) with both positive and negative
tests, including assertions against REAL files in `eval/suite/runs/`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.suite import aggregate_judges, audit_suite, code_checks as cc, copy_checks as cp, run_suite
from scripts import platform_paths as pp, run_step8_eval, step7_smoke_antiswap as s7


class TestHarnessV3(unittest.TestCase):
    """Stage A Harness v3 Verification Suite."""

    # ------------------------------------------------------------------
    # 1. Platform Paths & Linux /proc Telemetry + SLA Gates
    # ------------------------------------------------------------------
    def test_01_platform_paths_and_linux_telemetry(self) -> None:
        self.assertTrue(pp.ROOT.exists())
        self.assertTrue(pp.SUITE_DIR.exists())
        self.assertTrue(pp.TASKS_JSON.exists())
        self.assertTrue(Path(pp.NODE_EXE).exists())
        self.assertTrue(Path(pp.CHROME_EXE).exists())
        self.assertTrue(pp.TYPESCRIPT_LIB_JS.exists())
        self.assertTrue(pp.MCP_THIRD_PARTY_INDEX.exists())

        # Local endpoint guard: positive & negative
        pp.assert_local_endpoint("http://127.0.0.1:8080/v1/chat/completions")
        pp.assert_local_endpoint("http://localhost:8080/health")
        with self.assertRaises(RuntimeError):
            pp.assert_local_endpoint("https://openrouter.ai/api/v1/chat/completions")

        # Linux /proc readers
        mem = s7.read_proc_meminfo()
        vm = s7.read_proc_vmstat()
        smaps = s7.read_proc_smaps_rollup(os.getpid())
        self.assertGreater(mem["MemTotal_kB"], 1_000_000)
        self.assertGreater(mem["MemAvailable_kB"], 1_000_000)
        self.assertIn("pswpout", vm)
        self.assertGreater(smaps["Rss_kB"], 0)

        # PLE Rss check against unmapped byte range -> 0 kB (positive) & resident PLE VMA (negative)
        ple_rss = s7.check_ple_rss_kb(os.getpid(), (10**12, 10**12 + 4096))
        self.assertEqual(ple_rss["ple_rss_kb"], 0)
        self.assertTrue(ple_rss["ple_zero_rss_ok"])

        synthetic_bad_smaps = (
            "7f0000000000-7f0000400000 r--p 00001000 08:01 12345 /models/SmartLLM-256E.gguf\n"
            "Size:               4096 kB\n"
            "Rss:                2048 kB\n"
        )
        ple_bad = s7.check_ple_rss_kb(
            os.getpid(),
            ple_byte_range=(0x1000, 0x200000),
            smaps_text_override=synthetic_bad_smaps,
        )
        self.assertEqual(ple_bad["ple_rss_kb"], 2048)
        self.assertFalse(ple_bad["ple_zero_rss_ok"])

        # SLA gate evaluator: positive vs negative
        good_tel = {
            "summary": {
                "pswpout_delta_max": 0,
                "min_avail_phys_mib": 4096.0,
                "max_gpu_used_mib": 8200.0,
                "max_ple_rss_kb": 0,
                "aborted_due_to_ram_pressure": False,
            },
            "post_cleanup": {
                "post_compute_apps": [],
                "post_vram_used_mib": 32.0,
                "idle_vram_mib": 32.0,
            },
        }
        res_ok = s7.evaluate_telemetry_against_sla(good_tel)
        self.assertTrue(res_ok["all_sla_passed"])

        bad_tel = {
            "summary": {
                "pswpout_delta_max": 4,
                "min_avail_phys_mib": 2048.0,
                "max_gpu_used_mib": 11200.0,
                "max_ple_rss_kb": 512,
                "aborted_due_to_ram_pressure": True,
            },
            "post_cleanup": {
                "post_compute_apps": [{"pid": "9999", "name": "llama-server"}],
                "post_vram_used_mib": 500.0,
                "idle_vram_mib": 32.0,
            },
        }
        res_bad = s7.evaluate_telemetry_against_sla(bad_tel)
        self.assertFalse(res_bad["all_sla_passed"])
        self.assertFalse(res_bad["zero_swap_pswpout_ok"])
        self.assertFalse(res_bad["avail_ram_3gib_ok"])
        self.assertFalse(res_bad["vram_budget_ok"])
        self.assertFalse(res_bad["ple_zero_rss_ok"])
        self.assertFalse(res_bad["clean_exit_ok"])

    # ------------------------------------------------------------------
    # 2. CODE-04: Watchdog 3.0 GiB Floor (No Reclaimable RAM Exemption)
    # ------------------------------------------------------------------
    def test_02_code04_watchdog_no_reclaimable_exemption(self) -> None:
        self.assertEqual(run_step8_eval.WATCHDOG_MIN_AVAIL_MIB, 3072.0)
        self.assertEqual(run_step8_eval.WATCHDOG_CRIT_AVAIL_MIB, 2048.0)

        # Positive: 4500 MiB available, 0 swap, 6000 MiB VRAM, 0 PLE Rss
        ok_sample = {
            "avail_phys_mib": 4500.0,
            "reclaimable_ram_gib": 20.0,
            "pswpout_delta": 0,
            "gpu_used_mib": 6000.0,
            "ple_rss_kb": 0,
        }
        any_b, crit_b, _ = run_step8_eval.evaluate_watchdog_sample(ok_sample)
        self.assertFalse(any_b)
        self.assertFalse(crit_b)

        # Negative: 2500 MiB available (< 3072 MiB) EVEN WITH 22 GiB reclaimable RAM must breach!
        low_avail_sample = {
            "avail_phys_mib": 2500.0,
            "reclaimable_ram_gib": 22.0,
            "pswpout_delta": 0,
            "gpu_used_mib": 6000.0,
            "ple_rss_kb": 0,
        }
        any_b2, _, _ = run_step8_eval.evaluate_watchdog_sample(low_avail_sample)
        self.assertTrue(any_b2)

        # Negative: pswpout_delta > 0 or ple_rss_kb > 0 triggers critical breach immediately
        swap_sample = {"avail_phys_mib": 8000.0, "pswpout_delta": 1, "gpu_used_mib": 5000.0, "ple_rss_kb": 0}
        any_b3, crit_b3, _ = run_step8_eval.evaluate_watchdog_sample(swap_sample)
        self.assertTrue(any_b3)
        self.assertTrue(crit_b3)

    # ------------------------------------------------------------------
    # 3. NEW-BUG-01 & CODE-01: Raw CSP Grading Before Postprocessor
    # ------------------------------------------------------------------
    def test_03_new_bug_01_and_code_01_csp_raw_grading(self) -> None:
        # CODE-01 Negative: bare unquoted `unsafe-inline` and quoted `'unsafe-inline'` both rejected
        bare_csp = "default-src 'self'; script-src 'self' unsafe-inline; style-src 'self'; object-src 'none'; base-uri 'self'"
        bare_res = cc.audit_csp_policy_string(bare_csp)
        self.assertTrue(bare_res["has_unsafe_inline"])
        self.assertFalse(bare_res["script_no_unsafe_inline"])
        self.assertFalse(bare_res["strict_csp_passed"])

        quoted_csp = "default-src 'none'; script-src 'unsafe-inline'; style-src 'self'"
        quoted_res = cc.audit_csp_policy_string(quoted_csp)
        self.assertTrue(quoted_res["has_unsafe_inline"])
        self.assertFalse(quoted_res["script_no_unsafe_inline"])

        # CODE-01 Positive: strict CSP with placeholders, object-src 'none', require-trusted-types-for 'script'
        strict_csp = (
            "default-src 'none'; style-src 'sha256-__CSP_STYLE__'; script-src 'sha256-__CSP_SCRIPT__'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'; "
            "frame-ancestors 'none'; require-trusted-types-for 'script'"
        )
        strict_res = cc.audit_csp_policy_string(strict_csp, is_header=True)
        self.assertFalse(strict_res["has_unsafe_inline"])
        self.assertTrue(strict_res["script_no_unsafe_inline"])
        self.assertTrue(strict_res["style_no_unsafe_inline"])
        self.assertTrue(strict_res["has_object_src_none"])
        self.assertTrue(strict_res["has_trusted_types"])
        self.assertTrue(strict_res["strict_csp_passed"])

        # NEW-BUG-01 Positive: Postprocessor preserves object-src 'none' & require-trusted-types-for 'script'
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = os.path.join(tmpdir, "index.html")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(
                    f'<!DOCTYPE html><html lang="en"><head>'
                    f'<meta http-equiv="Content-Security-Policy" content="{strict_csp}">'
                    f"<style>body {{ color: oklch(0.95 0.01 250); }}</style>"
                    f"<script>console.log(1);</script>"
                    f"</head><body><h1>Test</h1></body></html>"
                )
            raw_grade = cc.audit_raw_csp_and_headers(tmpdir)
            self.assertTrue(raw_grade["raw_csp_passed"])
            self.assertTrue(raw_grade["raw_has_object_src_none"])
            self.assertTrue(raw_grade["raw_has_trusted_types"])

            cc.apply_csp_postprocessor(tmpdir)
            with open(html_path, "r", encoding="utf-8") as fh:
                patched_html = fh.read()
            self.assertIn("object-src 'none'", patched_html)
            self.assertIn("require-trusted-types-for 'script'", patched_html)
            self.assertNotIn("__CSP_STYLE__", patched_html)
            self.assertNotIn("__CSP_SCRIPT__", patched_html)

        # NEW-BUG-01 Negative: Missing CSP meta tag fails raw grade AND postprocessor does NOT inject fake CSP tag
        with tempfile.TemporaryDirectory() as tmpdir2:
            html_path2 = os.path.join(tmpdir2, "index.html")
            with open(html_path2, "w", encoding="utf-8") as fh:
                fh.write("<!DOCTYPE html><html><head><style>body{}</style></head><body><h1>No CSP</h1></body></html>")
            raw_grade2 = cc.audit_raw_csp_and_headers(tmpdir2)
            self.assertFalse(raw_grade2["raw_meta_csp_present"])
            self.assertFalse(raw_grade2["raw_csp_passed"])
            cc.apply_csp_postprocessor(tmpdir2)
            with open(html_path2, "r", encoding="utf-8") as fh:
                after_html2 = fh.read()
            self.assertNotIn("Content-Security-Policy", after_html2)

        # Real file checks on eval/suite/runs/:
        # - qwen3.8-think-8k/t1 has hallucinated raw sha256 hashes in orig/index.html -> fails raw_csp_passed
        # - smartllm-205e-iq3-s/t2 omitted <meta> CSP in orig/index.html (injected by v1 postprocessor) -> fails raw_csp_passed
        # - smartllm-205e-iq3-s/t1 emitted valid placeholders in orig/index.html -> passes raw_csp_passed
        real_qwen_t1 = str(pp.RUNS_DIR / "qwen3.8-think-8k" / "t1")
        real_raw_grade = cc.audit_raw_csp_and_headers(real_qwen_t1)
        self.assertTrue(real_raw_grade["raw_meta_csp_present"])
        self.assertFalse(real_raw_grade["raw_csp_passed"])

        real_s_t2 = cc.audit_raw_csp_and_headers(str(pp.RUNS_DIR / "smartllm-205e-iq3-s" / "t2"))
        self.assertFalse(real_s_t2["raw_meta_csp_present"])
        self.assertFalse(real_s_t2["raw_csp_passed"])

        real_s_t1 = cc.audit_raw_csp_and_headers(str(pp.RUNS_DIR / "smartllm-205e-iq3-s" / "t1"))
        self.assertTrue(real_s_t1["raw_meta_csp_present"])
        self.assertTrue(real_s_t1["raw_csp_passed"])

    # ------------------------------------------------------------------
    # 4. NEW-BUG-02: Cloudflare _headers Multi-Route + HSTS + COOP/COEP/CORP
    # ------------------------------------------------------------------
    def test_04_new_bug_02_headers_hsts_and_isolation(self) -> None:
        # Positive: Multi-route _headers (`/*` + `/*.html` + `/assets/*`) merges headers for `/index.html`
        multi_route_headers = (
            "# Cloudflare Pages headers\n"
            "/*\n"
            "  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload\n"
            "  X-Content-Type-Options: nosniff\n"
            "  Referrer-Policy: strict-origin-when-cross-origin\n"
            "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
            "  Cross-Origin-Opener-Policy: same-origin\n"
            "  Cross-Origin-Embedder-Policy: require-corp\n"
            "  Cross-Origin-Resource-Policy: same-origin\n"
            "/*.html\n"
            "  Content-Security-Policy: default-src 'none'; frame-ancestors 'none'\n"
            "/assets/*\n"
            "  Cache-Control: public, max-age=31536000, immutable\n"
        )
        parsed = cc._parse_cloudflare_headers(multi_route_headers)
        self.assertTrue(parsed["has_route_rule"])
        self.assertIn("content-security-policy", parsed["headers"])
        self.assertIn("strict-transport-security", parsed["headers"])

        hsts_ok = cc.check_hsts_header(parsed["headers"]["strict-transport-security"])
        self.assertTrue(hsts_ok["passed"])
        iso_ok = cc.check_cross_origin_isolation_headers(parsed["headers"])
        self.assertTrue(iso_ok["full_isolation_passed"])

        # Negative: HSTS with short max-age or missing includeSubDomains fails
        self.assertFalse(cc.check_hsts_header("max-age=86400; includeSubDomains")["passed"])
        self.assertFalse(cc.check_hsts_header("max-age=63072000")["passed"])
        self.assertFalse(
            cc.check_cross_origin_isolation_headers({"cross-origin-opener-policy": "unsafe-none"})[
                "full_isolation_passed"
            ]
        )

        # Real file checks: smartllm-205e-iq3-s/t1/_headers (valid) vs t3/_headers (wrapped in C-comment /* ... */)
        t1_hdr_text = (pp.RUNS_DIR / "smartllm-205e-iq3-s" / "t1" / "orig" / "_headers").read_text(encoding="utf-8")
        t3_hdr_text = (pp.RUNS_DIR / "smartllm-205e-iq3-s" / "t3" / "orig" / "_headers").read_text(encoding="utf-8")
        self.assertTrue(cc._parse_cloudflare_headers(t1_hdr_text)["has_route_rule"])
        t3_parsed = cc._parse_cloudflare_headers(t3_hdr_text)
        self.assertFalse(t3_parsed["has_route_rule"])
        self.assertEqual(t3_parsed.get("format_error"), "invalid_comment_or_json_syntax")

    # ------------------------------------------------------------------
    # 5. NEW-BUG-03, CODE-02 & CODE-03: run_suite Extraction & Sampler
    # ------------------------------------------------------------------
    def test_05_new_bug_03_and_code_02_03_run_suite(self) -> None:
        # CODE-03: Frozen donor sampler settings (no -3.0 eos_logit_bias or -1000 token suppression)
        self.assertEqual(run_suite.DEFAULT_EOS_LOGIT_BIAS, 0.0)
        self.assertEqual(run_suite.DEFAULT_LOGIT_BIAS_TOKENS, ())
        self.assertEqual(run_suite.DEFAULT_DRY_MULTIPLIER, 0.0)
        self.assertEqual(run_suite.DEFAULT_TEMPERATURE, 0.6)
        self.assertEqual(run_suite.DEFAULT_TOP_P, 0.95)
        self.assertEqual(run_suite.DEFAULT_TOP_K, 20)

        # CODE-02 Positive: Unclosed leading <think> before FILE: index.html preserves the deliverable
        raw_unclosed_think = (
            "<think>\nLet me plan the layout carefully...\n"
            "FILE: index.html\n```html\n<!DOCTYPE html><html><body><h1>Saved</h1></body></html>\n```"
        )
        cleaned = run_suite.clean_model_text(raw_unclosed_think)
        self.assertTrue(cleaned.startswith("FILE: index.html"))
        self.assertIn("<h1>Saved</h1>", cleaned)

        # CODE-02 Negative/Guard: Literal <think> inside deliverable code is NOT wiped out
        raw_literal_in_code = (
            "FILE: index.html\n```html\n<!DOCTYPE html><html><body>"
            "<script>const tag = '<think>'; console.log(tag);</script></body></html>\n```"
        )
        cleaned_code = run_suite.clean_model_text(raw_literal_in_code)
        self.assertIn("const tag = '<think>';", cleaned_code)

        # NEW-BUG-03 Positive: _strip_section_fences strips trailing commentary even if it mentions <svg> or <T>
        fenced_with_svg_note = (
            "```html\n<!DOCTYPE html>\n<html>\n<body><svg></svg></body>\n</html>\n```\n"
            "Note: All icons use inline <svg> and <div> containers for zero network requests."
        )
        stripped = run_suite._strip_section_fences(fenced_with_svg_note, is_markdown=False)
        self.assertTrue(stripped.endswith("</html>"))
        self.assertNotIn("Note: All icons", stripped)
        self.assertNotIn("```", stripped)

        # Real truncation detection on smartllm-205e-iq3-s/t7 (mid-<input truncation at L792, 1/4 files)
        tasks_by_id = {t["id"]: t for t in json.loads(pp.TASKS_JSON.read_text(encoding="utf-8"))["tasks"]}
        t7_dir = str(pp.RUNS_DIR / "smartllm-205e-iq3-s" / "t7")
        t7_comp = run_suite.check_extraction_completeness(t7_dir, tasks_by_id["t7"], ["index.html"])
        self.assertFalse(t7_comp["all_required_files_present"])
        self.assertFalse(t7_comp["html_structurally_complete"])
        self.assertFalse(t7_comp["deliverable_complete"])

    # ------------------------------------------------------------------
    # 6. NEW-BUG-04, Tailwind Ban & 100vh Hygiene
    # ------------------------------------------------------------------
    def test_06_new_bug_04_oklch_tailwind_and_100vh(self) -> None:
        # NEW-BUG-04 Positive: Dark theme with high-contrast semantic --bg / --text tokens passes
        good_css = [
            ":root { --bg: oklch(0.13 0.01 260); --surface: oklch(0.18 0.01 260); "
            "--text: oklch(0.95 0.01 250); --muted: oklch(0.72 0.01 250); --accent: oklch(0.65 0.18 45); }"
        ]
        oklch_good = cc.evaluate_oklch_compliance(good_css, "")
        self.assertTrue(oklch_good["semantic_bg_fg_contrast_passed"])
        self.assertGreaterEqual(oklch_good["semantic_bg_fg_min_contrast"], 7.0)

        # NEW-BUG-04 Negative: Unreadable dark-on-dark --bg / --text FAILS even if two accents have 12:1 contrast
        bad_css = [
            ":root { --bg: oklch(0.15 0.01 260); --text: oklch(0.22 0.01 260); "
            "--accent-light: oklch(0.98 0.01 90); --accent-dark: oklch(0.10 0.01 260); }"
        ]
        oklch_bad = cc.evaluate_oklch_compliance(bad_css, "")
        self.assertGreater(oklch_bad["max_contrast_ratio_est"], 10.0)
        self.assertFalse(oklch_bad["semantic_bg_fg_contrast_passed"])

        # Tailwind ban: positive & negative
        self.assertTrue(cc.check_tailwind_ban('<div class="grid-layout card-header">', ["body { margin: 0; }"])["tailwind_ban_passed"])
        self.assertFalse(
            cc.check_tailwind_ban(
                '<div class="flex items-center justify-between px-4 py-2 bg-slate-900 text-white">', []
            )["tailwind_ban_passed"]
        )

        # 100vh check: bare 100vh fails, progressive 100vh + 100dvh passes
        self.assertFalse(cc.check_viewport_vh_hygiene([" .hero { min-height: 100vh; } "], "")["viewport_vh_passed"])
        self.assertTrue(
            cc.check_viewport_vh_hygiene([" .hero { min-height: 100vh; min-height: 100dvh; } "], "")[
                "viewport_vh_passed"
            ]
        )

        # Real file check on gyro-m-local/t1/index.html (contains bare 100vh without 100dvh)
        gyro_t1_html = (pp.RUNS_DIR / "gyro-m-local" / "t1" / "index.html").read_text(encoding="utf-8")
        p_gyro = cc.StructHTMLParser()
        p_gyro.feed(gyro_t1_html)
        vh_gyro = cc.check_viewport_vh_hygiene(p_gyro.styles, " ".join(p_gyro.inline_style_attrs))
        self.assertGreater(vh_gyro["bare_100vh_count"], 0)
        self.assertFalse(vh_gyro["viewport_vh_passed"])

    # ------------------------------------------------------------------
    # 7. NEW-BUG-06 & Cyrillic Density Threshold (`copy_checks.py`)
    # ------------------------------------------------------------------
    def test_07_new_bug_06_copy_checks_and_cyrillic_density(self) -> None:
        # Negative: English text with a single Cyrillic char ('Я') MUST FAIL expected_lang='ru'
        fake_ru_text = (
            "Industrial boiler engineering specification with high efficiency thermal transfer "
            "and automated pressure control systems for modern plants Я."
        )
        fake_ru_res = cp.analyze_copy_hygiene(fake_ru_text, expected_lang="ru")
        self.assertFalse(fake_ru_res["lang_gate_passed"])
        self.assertLess(fake_ru_res["cyrillic_density"], 0.05)

        # Positive: Clean Russian engineering prose with «ёлочки» and em-dash (—) passes expected_lang='ru'
        clean_ru_text = (
            "Завод «Северная Мануфактура» проектирует и изготавливает акустические панели "
            "и столярные конструкции из массива северного дуба — точность обработки до 0,1 мм "
            "по ГОСТ 7016-2013 с полным контролем влажности древесины."
        )
        clean_ru_res = cp.analyze_copy_hygiene(clean_ru_text, expected_lang="ru")
        self.assertTrue(clean_ru_res["lang_gate_passed"])
        self.assertGreaterEqual(clean_ru_res["cyrillic_density"], 0.65)
        self.assertTrue(clean_ru_res["ru_typography"]["ru_em_dash_allowed"])
        self.assertTrue(clean_ru_res["ru_typography"]["has_guillemets"])
        self.assertTrue(clean_ru_res["copy_hygiene_passed"])

        # Negative: AI-slop banned phrases (EN & RU) and double spaces fail
        slop_en = cp.analyze_copy_hygiene(
            "In today's fast-paced world, we delve into a rich tapestry of seamless integration  with double spaces.",
            expected_lang="en",
        )
        self.assertGreaterEqual(slop_en["ai_slop_count"], 3)
        self.assertGreater(slop_en["double_space_count"], 0)
        self.assertFalse(slop_en["copy_hygiene_passed"])

        # Real file check: smartllm-205e-iq3-s/t3 (RU task) vs t1 (EN task audited as RU)
        t3_folder = str(pp.RUNS_DIR / "smartllm-205e-iq3-s" / "t3")
        t1_folder = str(pp.RUNS_DIR / "smartllm-205e-iq3-s" / "t1")
        t3_copy = cp.audit_copy_task(t3_folder, expected_lang="ru")
        t1_as_ru = cp.audit_copy_task(t1_folder, expected_lang="ru")
        self.assertTrue(t3_copy["lang_gate_passed"])
        self.assertFalse(t1_as_ru["lang_gate_passed"])

        # DEFECT-W1-02 Regression: Adjacent HTML tags (`</span> <span>`) must NOT create synthetic double spaces
        adjacent_tag_html = (
            "<p><span>Industrial</span> <span>boiler</span> <strong>engineering</strong> "
            "<span>specification for high-efficiency thermal power generation plants.</span></p>"
        )
        adj_res = cp.audit_copy_task(adjacent_tag_html, expected_lang="en", is_html=True)
        self.assertEqual(adj_res["double_space_count"], 0)
        self.assertTrue(adj_res["copy_hygiene_passed"])

        # Verify donor runs (qwen3.8-no-think/t1 and qwen3.8-think-8k/t1) pass copy_hygiene_passed
        q_nt_t1 = cp.audit_copy_task(str(pp.RUNS_DIR / "qwen3.8-no-think" / "t1"), expected_lang="en")
        q_th_t1 = cp.audit_copy_task(str(pp.RUNS_DIR / "qwen3.8-think-8k" / "t1"), expected_lang="en")
        self.assertEqual(q_nt_t1["double_space_count"], 0)
        self.assertTrue(q_nt_t1["copy_hygiene_passed"])
        self.assertEqual(q_th_t1["double_space_count"], 0)
        self.assertTrue(q_th_t1["copy_hygiene_passed"])

    # ------------------------------------------------------------------
    # 8. AI Crawlers (robots.txt), hreflang/canonical, and JSON-LD
    # ------------------------------------------------------------------
    def test_08_robots_ai_crawlers_hreflang_and_json_ld(self) -> None:
        good_robots = (
            "User-agent: *\nAllow: /\n\n"
            "User-agent: GPTBot\nDisallow: /\n\n"
            "User-agent: OAI-SearchBot\nAllow: /\n\n"
            "Sitemap: https://example.com/sitemap.xml\n"
        )
        rob_ok = cc.check_robots_txt_ai_crawlers(good_robots)
        self.assertTrue(rob_ok["valid_syntax"])
        self.assertTrue(rob_ok["has_ai_crawler_policy"])
        self.assertTrue(rob_ok["has_sitemap"])

        # Negative: real smartllm-205e-iq3-s/t1/robots.txt has only `User-agent: *` and no AI crawlers
        t1_robots = (pp.RUNS_DIR / "smartllm-205e-iq3-s" / "t1" / "robots.txt").read_text(encoding="utf-8")
        rob_t1 = cc.check_robots_txt_ai_crawlers(t1_robots)
        self.assertTrue(rob_t1["valid_syntax"])
        self.assertFalse(rob_t1["has_ai_crawler_policy"])

        # Hreflang & canonical: positive & negative
        links_good = [
            {"rel": "canonical", "href": "https://example.com/en"},
            {"rel": "alternate", "hreflang": "en", "href": "https://example.com/en"},
            {"rel": "alternate", "hreflang": "ru", "href": "https://example.com/ru"},
            {"rel": "alternate", "hreflang": "x-default", "href": "https://example.com/en"},
        ]
        hl_ok = cc.check_hreflang_and_canonical(links_good)
        self.assertTrue(hl_ok["has_canonical"])
        self.assertTrue(hl_ok["has_bilingual_en_ru_hreflang"])
        self.assertTrue(hl_ok["has_x_default_hreflang"])
        self.assertFalse(cc.check_hreflang_and_canonical([])["has_canonical"])

    # ------------------------------------------------------------------
    # 9. In-Process TS 6.0.3 & Comment-Stripping Regex (`test_dag_runner.mjs`)
    # ------------------------------------------------------------------
    def test_09_dag_runner_comment_regex_and_real_dag_ts(self) -> None:
        # Positive: Promise.all and `: any` inside comments must NOT be flagged in code counts
        comment_snippet = (
            "// Do not use Promise.all(nodes) or x: any in strict mode\n"
            "/* Block comment mentioning Promise.all(arr) and val as any */\n"
            "export const x: number = 42;\n"
        )
        p_c = subprocess.run(
            [str(pp.NODE_EXE), str(pp.SUITE_DIR / "test_dag_runner.mjs"), "--analyze-snippet", comment_snippet],
            capture_output=True,
            text=True,
            check=True,
        )
        info_c = json.loads(p_c.stdout)
        self.assertEqual(info_c["explicit_any_count"], 0)
        self.assertEqual(info_c["promise_all_code_count"], 0)
        self.assertEqual(info_c["promise_all_comment_count"], 2)

        # Negative: Real Promise.all and `: any` in executable code ARE flagged
        code_snippet = "export async function f(x: any) { return Promise.all([x]); }"
        p_bad = subprocess.run(
            [str(pp.NODE_EXE), str(pp.SUITE_DIR / "test_dag_runner.mjs"), "--analyze-snippet", code_snippet],
            capture_output=True,
            text=True,
            check=True,
        )
        info_bad = json.loads(p_bad.stdout)
        self.assertEqual(info_bad["explicit_any_count"], 1)
        self.assertEqual(info_bad["promise_all_code_count"], 1)

        # Real file test: smartllm-205e-iq3-s/t4/dag.ts via in-process TypeScript 6.0.3
        real_dag = pp.RUNS_DIR / "smartllm-205e-iq3-s" / "t4" / "dag.ts"
        p_dag = subprocess.run(
            [str(pp.NODE_EXE), str(pp.SUITE_DIR / "test_dag_runner.mjs"), str(real_dag)],
            capture_output=True,
            text=True,
            check=True,
        )
        dag_res = json.loads(p_dag.stdout)
        self.assertTrue(dag_res["tsc_strict_passed"])
        self.assertEqual(dag_res["explicit_any_count"], 0)
        self.assertEqual(dag_res["tests_passed"], 10)
        self.assertEqual(dag_res["tests_total"], 12)

        # Verify audit_typescript_task dispatches t_backend_form to t_backend_form_runner.mjs
        with tempfile.TemporaryDirectory() as tmp_ts_dir:
            ref_ts = pp.SUITE_DIR / "tasks" / "t_backend_form_reference.ts"
            target_ts = Path(tmp_ts_dir) / "form_api.ts"
            target_ts.write_text(ref_ts.read_text(encoding="utf-8"), encoding="utf-8")
            form_audit = audit_suite.audit_typescript_task(
                tmp_ts_dir,
                {
                    "id": "t_backend_form",
                    "category": "typescript_coding",
                    "language": "en",
                    "required_files": ["form_api.ts"],
                },
            )
            self.assertTrue(form_audit["typescript_eval"]["tsc_strict_passed"])
            self.assertEqual(form_audit["typescript_eval"]["tests_passed"], 10)
            self.assertEqual(form_audit["typescript_eval"]["tests_total"], 10)

    # ------------------------------------------------------------------
    # 10. NEW-BUG-05 & WCAG 2.2 Target Size in Headless Chrome 148
    # ------------------------------------------------------------------
    def test_10_browser_lh_suite_wcag22_and_new_bug_05(self) -> None:
        # Negative (real file): smartllm-205e-iq3-s/t1 has 19.19px high nav links (< 24px WCAG 2.2)
        # and in file-snapshot mode performance is None ('unmeasured_snapshot'), NEVER fabricated 100!
        real_t1 = pp.RUNS_DIR / "smartllm-205e-iq3-s" / "t1"
        p_t1 = subprocess.run(
            [
                str(pp.NODE_EXE),
                str(pp.SUITE_DIR / "browser_and_lh_suite.mjs"),
                "--single-folder",
                str(real_t1),
                "--no-screenshots",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        rt_t1 = json.loads(p_t1.stdout)
        self.assertIsNone(rt_t1["lighthouse"]["performance"])
        self.assertEqual(rt_t1["lighthouse"]["performanceMode"], "unmeasured_snapshot")
        self.assertFalse(rt_t1["desktop"]["wcag22TargetSizePassed"])
        self.assertGreater(rt_t1["desktop"]["wcag22TargetSizeViolationsCount"], 0)

        # Positive: Compliant page with >= 24x24px interactive targets and scroll-padding-top passes WCAG 2.2
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "index.html").write_text(
                '<!DOCTYPE html><html lang="en" style="scroll-padding-top: 64px;"><head>'
                '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>WCAG 2.2 Compliant Page</title>'
                '<meta name="description" content="Compliant test page.">'
                "<style>"
                "header { position: sticky; top: 0; height: 48px; }"
                "a.btn, button { display: inline-flex; align-items: center; justify-content: center; "
                "min-width: 44px; min-height: 36px; padding: 8px 16px; }"
                "</style></head><body>"
                '<header><nav><a class="btn" href="#main">Main</a></nav></header>'
                '<main id="main"><h1>Compliant</h1><button type="button">Action</button></main>'
                "</body></html>",
                encoding="utf-8",
            )
            p_ok = subprocess.run(
                [
                    str(pp.NODE_EXE),
                    str(pp.SUITE_DIR / "browser_and_lh_suite.mjs"),
                    "--single-folder",
                    tmpdir,
                    "--no-screenshots",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            rt_ok = json.loads(p_ok.stdout)
            self.assertTrue(rt_ok["desktop"]["wcag22TargetSizePassed"])
            self.assertEqual(rt_ok["desktop"]["wcag22TargetSizeViolationsCount"], 0)
            self.assertTrue(rt_ok["desktop"]["wcag22FocusNotObscuredPassed"])

    # ------------------------------------------------------------------
    # 11. NEW-BUG-07: Dual-Judge Independence & eval_gate_v1.yaml
    # ------------------------------------------------------------------
    def test_11_new_bug_07_aggregate_judges_and_eval_gate_yaml(self) -> None:
        gate_cfg = yaml.safe_load((pp.SUITE_DIR / "eval_gate_v1.yaml").read_text(encoding="utf-8"))
        self.assertEqual(gate_cfg["runtime_sla_gates"]["pswpout_delta_max"], 0)
        self.assertEqual(gate_cfg["runtime_sla_gates"]["min_avail_phys_gib"], 3.0)
        self.assertEqual(gate_cfg["runtime_sla_gates"]["max_vram_gib"], 10.5)
        self.assertEqual(gate_cfg["runtime_sla_gates"]["max_ple_rss_kb"], 0)
        self.assertEqual(gate_cfg["frozen_sampler"]["eos_logit_bias"], 0.0)
        self.assertEqual(gate_cfg["deterministic_gates"]["copywriting"]["ru_min_cyrillic_density"], 0.65)
        self.assertEqual(gate_cfg["deterministic_gates"]["accessibility_wcag22"]["min_target_size_css_px"], 24)

        with tempfile.TemporaryDirectory() as tmpdir:
            j1_path = os.path.join(tmpdir, "j1.json")
            j2_same_path = os.path.join(tmpdir, "j2_same.json")
            j2_opus_path = os.path.join(tmpdir, "j2_opus.json")
            bmap_path = os.path.join(tmpdir, "blind_map.json")

            with open(j1_path, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "judge_id": "argon_judge_1",
                        "blind": True,
                        "evaluations": {"pack_01": {"layout_craft": 8.5, "overall": 8.5}},
                    },
                    fh,
                )
            with open(j2_same_path, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "judge_id": "argon_judge_2",
                        "blind": True,
                        "evaluations": {"pack_01": {"layout_craft": 8.0, "overall": 8.0}},
                    },
                    fh,
                )
            with open(j2_opus_path, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "judge_id": "claude_opus_judge_2",
                        "blind": True,
                        "evaluations": {"pack_01": {"layout_craft": 9.0, "overall": 9.0}},
                    },
                    fh,
                )
            with open(bmap_path, "w", encoding="utf-8") as fh:
                json.dump({"packs": {"pack_01": {"model": "cand-256e", "task": "t1"}}}, fh)

            # Negative: Single judge or same judge family ('argon' + 'argon') -> PENDING-JUDGE
            single_res = aggregate_judges.aggregate(j1_path, None, None, blind_map_path=bmap_path)
            self.assertEqual(single_res["judge_gate_status"], "PENDING-JUDGE")
            self.assertFalse(single_res["independent_dual_judge_verified"])

            same_fam_res = aggregate_judges.aggregate(j1_path, j2_same_path, None, blind_map_path=bmap_path)
            self.assertEqual(same_fam_res["judge_gate_status"], "PENDING-JUDGE")
            self.assertFalse(same_fam_res["independent_dual_judge_verified"])

            # Positive: Two independent families ('argon' + 'opus') + blind map -> VERIFIED-BLIND-DUAL-JUDGE
            dual_res = aggregate_judges.aggregate(j1_path, j2_opus_path, None, blind_map_path=bmap_path)
            self.assertEqual(dual_res["judge_gate_status"], "VERIFIED-BLIND-DUAL-JUDGE")
            self.assertTrue(dual_res["independent_dual_judge_verified"])
            self.assertTrue(dual_res["blind_evaluation_verified"])
            self.assertEqual(dual_res["models"]["cand-256e"]["t1"]["mean"]["overall"], 8.75)


if __name__ == "__main__":
    unittest.main(verbosity=2)
