# SmartLLM Offline Eval Suite — Judge Rubric v3 (`eval/suite/judge_rubric.md`)

**Version:** `3.0.0` (Stage A Locked Standard)  
**Judge Families:** Minimum 2 independent model families (`Family 1` and `Family 2`, e.g., two distinct frontier/local VLM evaluators). Single-family or non-blind judging is strictly invalid.  
**Constraint:** Strictly offline / local evaluation (`127.0.0.1` only; zero external paid inference APIs). Every judge inspects:
1. Task specification (`eval/suite/tasks.json`, `eval/suite/tasks/*.json`, or `eval/holdout/tasks_holdout.json`) and canon token rules.
2. **Raw** model-generated files (`orig/index.html`, `orig/_headers`, `llms.txt`, `robots.txt`, `zimage_prompts.json`, `dag.ts`, `handler.ts`) **prior** to any CSP hash packaging postprocessor.
3. Deterministic audit outputs (`static_audit.json`, `runtime_audit.json`, TypeScript unit test reports).
4. Rendered desktop (`1440×900`, `shot-desktop.png`, `shot-desktop-full.png`) and mobile (`375×812`, `shot-mobile.png`) screenshots (plus reference images `ref/t2.png`, `ref/t12.png`, or sequential Z-Image renders).

---

## 1. Eight Explicit Subscores (`0.0` to `10.0`, step `0.5`)

Every task is scored across 8 explicit criteria (`0.0`–`10.0`, step `0.5`). Non-applicable language subscores (`copy_ru` on EN-only tasks, `copy_en` on RU-only tasks) are set to `null` and excluded from the weighted `overall` denominator; bilingual tasks (`t_zimage_site`) require **both** `copy_en` and `copy_ru`.

### 1.1. `layout_craft` — Layout, Visual Hierarchy & Responsive Rhythm (`Weight: 15%`)
- **`9.0–10.0`**: Crisp 12-column CSS Grid / `subgrid` alignment, modular spacing rhythm (`clamp()`), geometric typographic scale (`1.2`–`1.333`), bespoke multi-element inline `<svg>` schematics or working `<canvas>`/WebGL visuals, zero bounding-box collisions or text clipping in `shot-desktop.png` and `shot-mobile.png`, zero horizontal overflow at `1440×900` and `375×812`, `CLS = 0`.
- **`7.0–8.5`**: Clean desktop and mobile layout (`overflowX = false`), functional visual schematics, minor density or alignment imperfections.
- **`4.0–6.5`**: Generic 3-card centered boilerplate, primitive placeholder boxes, cramped whitespace, or minor mobile clipping.
- **`0.0–3.5`**: Broken layout, overlapping DOM elements, horizontal scroll overflow on desktop/mobile, or blank render.

### 1.2. `canon_fidelity` — OKLCH Tokens, CSS Modernity & Canon Adherence (`Weight: 15%`)
- **`9.0–10.0`**: Unmistakable adherence to the requested canon (`Swiss Typographic Grid`, `Neo-Brutalism`, `High-Tech SaaS Dark Mode`, `Editorial`, `Industrial B2B Engineering`, `Luxury Minimalism`). All palette colors defined as `:root` `oklch(L C H)` tokens with polarity/chroma/radius/shadow matching canon rules; uses modern CSS (`@container` queries, `100dvh`/`100svh` instead of legacy `100vh`, `subgrid`, `clamp()`, `tabular-nums`); **zero** Tailwind utility classes and **zero** AI purple-blue slop gradients.
- **`7.0–8.5`**: Correct canon polarity and `:root` OKLCH palette, minor omissions in `@container` or `subgrid` usage.
- **`4.0–6.5`**: Drift toward generic template styling, legacy `100vh` mobile viewport bugs, or hardcoded hex colors bypassing `:root` OKLCH tokens.
- **`0.0–3.5`**: Complete disregard of canon, Tailwind class pollution, or unstyled HTML.

### 1.3. `copy_persuasiveness` (`copy_en` & `copy_ru`) — Copywriting Persuasiveness, Brand Voice & Hygiene (`Weight: 15%`)
- **Hard Gate:** Across RU and bilingual tasks, mean **`copy_ru >= 6.5`** is required for milestone pass.
- **`9.0–10.0`**: Authentic domain terminology (`ГОСТ ИСО 10816-3`, `квалитет точности IT6`, `СКЗ виброскорости`, `EUV 13.5 нм High-NA 0.55`, `HHV`, `RT60`), persuasive commercial positioning, sharp editorial brand voice. Russian copy (`copy_ru`) uses idiomatic syntax, `«ёлочки»`, and spaced `—` (тире) with zero English calques (`бесшовный`, `откройте для себя`, `погрузитесь в мир`). English copy (`copy_en`) has zero AI-slop tokens (`delve`, `testament`, `tapestry`, `unleash`, `seamless`, `game-changer`, `cutting-edge`). Zero CJK characters, zero `U+FFFD`, zero mixed Latin/Cyrillic homoglyphs.
- **`7.0–8.5`**: Solid domain accuracy and persuasive structure; minor stylistic stiffness in 1–2 sentences.
- **`4.0–6.5`**: Noticeable machine-translation calques, repetitive marketing fluff, straight quotes `"` in Russian prose, or weak brand voice.
- **`0.0–3.5`**: `Lorem ipsum`, language switching, severe grammar breakdown, or homoglyph/encoding corruption.

### 1.4. `seo_aeo_geo` — SEO, AEO, GEO & Structured Data (`Weight: 12.5%`)
- **`9.0–10.0`**: Complete `<title>`, `<meta name="description">`, `<link rel="canonical">`, OpenGraph tags, and bidirectional `<link rel="alternate" hreflang="ru|en|x-default">` (on bilingual sites). Valid `<script type="application/ld+json">` `@graph` uniting `Organization`, `WebSite`, `WebPage`, `Product`/`TechArticle`, `BreadcrumbList`, and `FAQPage` whose Q&A strings match visible DOM FAQ text **verbatim**. Valid `/llms.txt` (`# H1`, `> summary`, `## sections` per `llmstxt.org`) and `/robots.txt` explicitly distinguishing AI training crawlers (`GPTBot`, `ClaudeBot`, `Google-Extended`, `CCBot`) from AI search/citation crawlers (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`) plus `Sitemap:`.
- **`7.0–8.5`**: Valid JSON-LD `@graph`, `llms.txt`, and `robots.txt` present; minor omissions in `hreflang` or secondary schema properties.
- **`4.0–6.5`**: Missing `FAQPage` verbatim parity, shallow single-entity JSON-LD, or generic `robots.txt` lacking AI crawler rules.
- **`0.0–3.5`**: Malformed JSON-LD syntax, missing `llms.txt`/`robots.txt`, or missing `<title>`/meta description.

### 1.5. `security_csp_headers` — Security, Raw CSP & Edge Isolation Headers (`Weight: 15%`)
- **Critical Rule (`NEW-BUG-01` Fix):** Graded strictly on **raw** model outputs (`orig/index.html`, `orig/_headers`, or backend response headers) **before** any packaging postprocessor runs.
- **`9.0–10.0`**: Raw `<meta http-equiv="Content-Security-Policy">` and `_headers` contain `'sha256-__CSP_STYLE__'` and `'sha256-__CSP_SCRIPT__'` placeholders with **zero** `'unsafe-inline'` in `script-src`/`style-src`, plus `default-src 'none'`/`'self'`, `object-src 'none'`, `base-uri 'none'`/`'self'`, `frame-ancestors 'none'`, and `require-trusted-types-for 'script'`. `_headers` uses valid Cloudflare Pages syntax (`/*` route, `#` comments only, zero `/* ... */` C-comments or JSON `{}`) and sets RFC 6797 HSTS (`max-age>=31536000; includeSubDomains; preload`), `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy: same-origin` (COOP), `Cross-Origin-Embedder-Policy: require-corp` or `credentialless` (COEP), and `Cross-Origin-Resource-Policy: same-origin` (CORP).
- **`7.0–8.5`**: Valid raw CSP placeholders and valid `_headers` syntax with HSTS/CSP/COOP; missing 1 secondary isolation header (e.g. CORP or Trusted Types).
- **`4.0–6.5`**: Missing CSP directives (`object-src 'none'`), weak COOP (`unsafe-none`), or missing form anti-automation hygiene.
- **`0.0–3.5`**: Raw output omits CSP, uses `'unsafe-inline'` in `script-src`, emits invalid `/* ... */` block comments in `_headers`, or uses inline HTML `on*` event attributes.

### 1.6. `ts_js_correctness` — TypeScript / JavaScript & Backend Architecture (`Weight: 12.5%`)
- **`9.0–10.0`**: Compiles cleanly under `tsc --noEmit --strict --target ES2022` with **zero** `any` types (`explicit_any_count == 0`). Passes 100% of deterministic unit tests (`dag.ts` 12/12 tests, or `t_backend_form` validation/rate-limit/CSRF/headers contract). Browser JS binds all events via `addEventListener`, never mutates `element.style.*` or calls `setAttribute('style', ...)` (toggles CSS classes/SVG attributes instead), and produces zero runtime console/page errors.
- **`7.0–8.5`**: Strict `tsc` passes and $\ge 85\%$ unit tests or interactive calculators work cleanly with zero runtime console errors.
- **`4.0–6.5`**: Non-strict TS typing errors, partial unit test pass ($50\text{–}80\%$), or non-functional interactive widget.
- **`0.0–3.5`**: Fails to compile/parse, deadlocks/times out, mutates inline `.style` breaking CSP, or throws uncaught runtime exceptions.

### 1.7. `accessibility_wcag22` — Accessibility & WCAG 2.2 AA/AAA Compliance (`Weight: 7.5%`)
- **`9.0–10.0`**: Semantic HTML5 landmarks (`header`, `nav`, `main`, `section`, `article`, `aside`, `footer`), exactly one `<h1>`, explicit `<label for>` or `aria-label` on 100% of inputs, `@media (prefers-reduced-motion: reduce)` rules, semantic foreground-vs-surface OKLCH contrast $\ge 7.0:1$ (AAA), WCAG 2.2 SC 2.5.8 Target Size Minimum ($\ge 24\times 24$ CSS px on all interactive targets), and WCAG 2.2 SC 2.4.11 Focus Not Obscured (`scroll-padding-top` $\ge$ sticky header height).
- **`7.0–8.5`**: AA contrast ($\ge 4.5:1$), full landmarks and form labels, reduced-motion support, minor target-size exception on 1 secondary link.
- **`4.0–6.5`**: Missing form labels, contrast $< 4.5:1$ on muted text, or interactive buttons $< 24\times 24$ px.
- **`0.0–3.5`**: Inaccessible markup (`<div>`-soup), missing `lang`/`viewport`, or unreadable text contrast.

### 1.8. `prompt_adherence` — Prompt Adherence, Completeness & Z-Image Pipeline Spec (`Weight: 7.5%`)
- **`9.0–10.0`**: 100% of requested files emitted completely (`finish_reason == "stop"`, closing `</html>` present, zero mid-tag truncation), all domain sections/calculators/tables/SVGs delivered. On Z-Image tasks (`t9`, `t_zimage_site`), `zimage_prompts.json` is valid JSON specifying sequential local `stable-diffusion.cpp` (`beyond_reality_z_image_3.0_fp8` / `q8_0`) assets (`id`, `target_section`, `output_path`, `width`, `height`, `aspect_ratio`, `steps`, `seed`, `prompt` 300–800 chars, `exact_text_in_frame` verbatim inside `prompt`), matched 1-to-1 with DOM `<figure>`/`<img>` slots having explicit `width`/`height`/`aspect-ratio` (`CLS = 0`).
- **`7.0–8.5`**: All required files complete and valid; minor simplification in 1 secondary table or prompt field.
- **`4.0–6.5`**: Missing 1 secondary section or incomplete `zimage_prompts.json` metadata.
- **`0.0–3.5`**: Missing required file(s), mid-tag truncation (`t7`-style failure), or hallucinated external image URLs.

---

## 2. Strict Anonymized A/B Shuffling Protocol (`>= 2` Judge Families)

To prevent self-family bias, ordering effects, and model-name anchoring (`TZ §1.4, §2.A.4`):
1. **Cryptographic Blind Anonymization:** Before any judge receives evaluation artifacts, the harness strips all model identifiers (`model_slug`, CLI flags, timestamps, `<think>` logs) and maps each `(model_slug, task_id)` folder to an opaque candidate label (`candidate_A`, `candidate_B`, `candidate_C`, ...) using a per-task salted permutation:
   $$\pi_{\text{task}} = \text{Shuffle}\bigl(\text{Models},\ \text{seed} = \text{HMAC-SHA256}(\text{salt},\ \text{task\_id})\bigr)$$
   so `candidate_A` in `t1` is NOT the same model as `candidate_A` in `t2`.
2. **Isolated Key Vault:** The mapping file (`blind_key.json`) is stored outside the judge prompt context and is read **only** by `aggregate_judges.py` after all judge JSON artifacts are finalized and SHA-256 hashed.
3. **Cross-Family Requirement:** Every gated evaluation requires at least two independent judge families (`Judge 1` from Family 1 or local VLM; `Judge 2` from Family 2).
4. **Discrepancy Flagging (`> 2.0` Points):** For every `(model, task, criterion)` across the 8 subscores and `overall`, if $|s_{1,c} - s_{2,c}| > 2.0$ (or if one judge emits `null` where the other emits a numeric score), `aggregate_judges.py` sets `"discrepancy_flagged": true` and lists the item in the discrepancy audit table for mandatory tie-break review.

---

## 3. Clean `PENDING-JUDGE` Handling Protocol

When deterministic static, runtime, and unit-test audits have executed (`static_audit.json`, `runtime_audit.json`), but blind evaluation from $\ge 2$ independent judge families is not yet complete (e.g., during automated benchmark runs prior to final review, or when only 1 judge family is available):
1. **No Silent Pass or Score Fabrication:** Automated scripts and reports MUST record `"judge_status": "PENDING-JUDGE"` and `"overall_judge_score": null`. Never substitute deterministic static scores for human/LLM judge subscores, never mark a run `"PASS"` on qualitative rubric gates without 2-family blind judge JSONs, and never default missing judge scores to `0.0` or `10.0`.
2. **Split Gate Reporting:** Reports must separate:
   - `"deterministic_gate"`: `"PASS"` or `"FAIL"` (computed strictly from raw CSP validity, `_headers` syntax, `tsc --noEmit --strict`, unit test pass count, zero console/page errors, `375px`/`1440px` zero overflow, and Zero-Swap SLA `Δpswpout == 0` & `MemAvailable >= 3.0 GiB`).
   - `"judge_gate"`: `"PENDING-JUDGE"` until both `judge_1.json` and `judge_2.json` (from distinct model families, unblinded via `blind_key.json`) are present and verified, at which point it transitions to `"PASS"` (if `overall >= 0.90 * donor_overall` and `copy_ru >= 6.5` with zero unresolved critical discrepancies) or `"FAIL"`.

---

## 4. Output Schema (`eval/suite/results/judge_1.json` & `judge_2.json`)

```json
{
  "schema_version": "3.0.0",
  "judge_id": "judge_1",
  "judge_family": "model-family-1",
  "blind_pack_sha256": "<sha256_of_blind_manifest>",
  "judge_status": "COMPLETE",
  "evaluations": {
    "<candidate_id_or_unblinded_model_slug>": {
      "<task_id>": {
        "layout_craft": 9.0,
        "canon_fidelity": 9.0,
        "copy_persuasiveness": 8.5,
        "copy_en": 8.5,
        "copy_ru": 8.5,
        "seo_aeo_geo": 9.5,
        "security_csp_headers": 9.0,
        "ts_js_correctness": 9.0,
        "accessibility_wcag22": 9.0,
        "prompt_adherence": 9.5,
        "overall": 9.0,
        "screenshots_inspected": ["shot-desktop.png", "shot-mobile.png"],
        "strengths": "Exact OKLCH Swiss grid, verbatim FAQ JSON-LD parity, strict raw CSP.",
        "weaknesses": "Minor rhythm compression on 375px mobile cards."
      }
    }
  }
}
```
When awaiting blind multi-family scoring, stub files or summary manifests MUST emit `"judge_status": "PENDING-JUDGE"` and `"evaluations": {}`.
