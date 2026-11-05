# SmartLLM — Reference Evaluation Results (`eval/suite/results/reference.md`)

**Updated:** 03.11.2026 (verified against `static_audit_all.json`, `runtime_audit.json`, `run_summary.json`, `judges_aggregated.json`)  
**Status:** `COMPLETE` (All 12 tasks `t1–t12` evaluated on local `gyro-m-local` (`D:\Strata`) + historical `qwen3.8-think-8k` & `qwen3.8-no-think` (`t1–t3`) + 2 independent blind judges `Gemini 3.8 Flash`)

---

## 1. Overview of Reference Runs

| Run ID | Model / Quantization | Source / Runtime | Reasoning Budget | Evaluated Tasks | Mean Judge `overall` | Status |
|---|---|---|---|---|---|---|
| `qwen3.8-think-8k` | `Qwen/Qwen3.8-Flash-Next` (FP8/BF16 reference) | Historical `eval/round2` (24.10.2026, imported offline) | `max_tokens: 8000` (`4,488–5,268` chars) | `t1, t2, t3` (`3/3`) | **`9.45 / 10`** (`t1–t3`) | **COMPLETE** (Historical Donor Reference) |
| `qwen3.8-no-think` | `Qwen/Qwen3.8-Flash-Next` (FP8/BF16 reference) | Historical `eval/round2` (24.10.2026, imported offline) | `max_tokens: 0` (`0` chars) | `t1, t2, t3` (`3/3`) | **`7.86 / 10`** (`t1–t3`) | **COMPLETE** (Historical Ablation Reference) |
| `gyro-m-local` | `GadflyII/Gyro-M` (`TQ2_0` 2.06 bpw, 512 experts; GGUF `91.97 GB` / `85.65 GiB`, unpacked pack `35.9 GB`) + `mmproj-BF16.gguf` (`900 MB`) | Local `D:\Strata` (`strata-server` `0.1.47`, `127.0.0.1:8080`, `10,820 MiB` VRAM used) | `"reasoning_budget_tokens": 4000` (`10,938–19,699` chars) | `t1–t12` (`12/12`) | **`8.72 / 10`** (`t1–t3`)<br>**`7.95 / 10`** (`8` non-loop tasks)<br>**`5.40 / 10`** (all `12` tasks) | **COMPLETE** (`12/12` done; VRAM freed to `0 MiB`) |

---

## 2. Head-to-Head Comparison on `t1–t3` (`qwen3.8-think-8k` vs `qwen3.8-no-think` vs `gyro-m-local`)

### 2.1. Task `t1` — EN Industrial B2B Landing + SEO/GEO + CSP (`Thermocore-X 500`)

| Metric | `qwen3.8-think-8k` | `qwen3.8-no-think` | `gyro-m-local` (`TQ2_0`) |
|---|---|---|---|
| Generation Time / Speed | `176.39 s` (historical API) | `219.59 s` (historical API) | `652.63 s` (`31.1 tok/s`, `20,000` tok, `length`) |
| Reasoning / Content Chars | `4,607` / `35,670` | `0` / `64,359` | `15,778` / `51,626` |
| Files Extracted | `index.html`, `llms.txt`, `robots.txt`, `_headers` (`4/4`) | `index.html`, `llms.txt`, `robots.txt`, `_headers` (`4/4`) | `index.html`, `llms.txt`, `robots.txt`, `_headers` (`4/4`) |
| Lighthouse (`Perf / A11y / BP / SEO`) | `100 / 99 / 100 / 100` (`80` raw `file://`)* | `100 / 90 / 100 / 100` (`80` raw `file://`)* | `100 / 100 / 100 / 100` (`80` raw `file://`)* |
| CLS / LCP | `0` / `320 ms` | `0` / `328 ms` | `0` / `368 ms` |
| Console / Page Errors (Post-CSP) | `0` / `0` | `0` / `0` | `0` / `0` |
| External Network Requests | `0` | `0` | `0` |
| Horizontal Overflow (`1440px` / `375px`) | `false` / `false` | `false` / `false` | `false` / `false` |
| `:root` OKLCH Tokens & Max Contrast | `12` (`17.72:1` PASS) | `14` (`18.30:1` PASS) | `15` (`18.79:1` PASS) |
| Semantic Landmark Tags | `footer, header, main, nav, section` (`5`) | `article, aside, figure, footer, header, main, nav, section` (`8`) | `figure, footer, header, main, nav, section` (`6`) |
| JSON-LD `@graph` Entities | `Organization, Product (×3), FAQPage, BreadcrumbList` (`4/4` req types) | `Organization, WebSite, BreadcrumbList, ItemList, Product (×3), FAQPage` (`4/4` req types) | `Organization, BreadcrumbList, Product (×3), FAQPage` (`4/4` req types) |
| Verbatim FAQ Match (HTML vs JSON-LD) | `5/5` (`100%` exact) | `5/5` (`100%` exact) | `5/5` (`100%` exact) |
| Security Headers in `_headers` | `7/7` (`all_passed: true`) | `7/7` (`all_passed: true`) | `6/7` (`all_passed: false`, missing `Cross-Origin-Opener-Policy`) |
| CSP Postprocessor (`audit_suite.py`) | `<meta>` + `_headers` patched (`1` style, `2` scripts, `6` style-attrs; stripped empty `data:text/css,`) | `<meta>` injected (`had_meta_csp_in_raw: false`) + `_headers` patched (`1` style, `2` scripts, `1` style-attr) | `<meta>` + `_headers` patched (`1` style, `2` scripts, `5` style-attrs) |

*\*Note: In port-free `file://` snapshot mode, Lighthouse's `robots-txt` check resolves to drive root (`file:///D:/robots.txt`), scoring `seoRawFileMode: 80`; `browser_and_lh_suite.mjs` recomputes `seo: 100` when valid local `robots.txt` is present in the run folder.*

### 2.2. Task `t2` — Vision-to-Code (`eval/suite/ref/t2.png` → Responsive Editorial Landing)

| Metric | `qwen3.8-think-8k` | `qwen3.8-no-think` | `gyro-m-local` (`TQ2_0` + `mmproj-BF16`) |
|---|---|---|---|
| Generation Time / Speed | `75.90 s` (historical API) | `58.74 s` (historical API) | `415.72 s` (`28.4 tok/s`, `11,559` tok, `stop`) |
| Reasoning / Content Chars | `4,488` / `21,740` | `0` / `21,615` | `11,649` / `22,511` |
| Lighthouse (`Perf / A11y / BP / SEO`) | `100 / 93 / 100 / 60` | `90 / 97 / 100 / 67` | `100 / 100 / 100 / 60` |
| CLS / LCP | `0` / `316 ms` | `0` / `348 ms` | `0` / `312 ms` |
| Console / Page Errors (Post-CSP) | `0` / `0` | `8` / `0` (`4` desktop + `4` mobile `picsum.photos` blocked by injected strict CSP) | `0` / `0` |
| External URLs in HTML / Requests | `0` (`7` inline SVGs) | `4` `picsum.photos` `<img>` URLs (**FAIL**; `8` external requests attempted & `8` failed/blocked by CSP) | `0` (`9` inline SVGs) |
| Horizontal Overflow (`1440px` / `375px`) | `false` / `false` | `true` (`1538px`) / `true` (`922px`) | `false` / `false` |
| `:root` OKLCH Tokens & Max Contrast | `11` (`15.74:1` PASS) | `10` (`15.61:1` PASS) | `11` (`13.33:1` PASS) |
| Headline OCR (`<h1>`) | `"When the story changes, what should you do?"` | `"When the story changes, what should you do?"` | `"When the story changes,\nwhat should you do?"` |

### 2.3. Task `t3` — RU Luxury Minimalism + Interactive Configurator (`Северная Мануфактура`)

| Metric | `qwen3.8-think-8k` | `qwen3.8-no-think` | `gyro-m-local` (`TQ2_0`, `--max-tokens 24000`) |
|---|---|---|---|
| Generation Time / Speed | `197.25 s` (historical API) | `191.34 s` (historical API) | `821.12 s` (`20.9 tok/s`, `16,939` tok, `stop`) |
| Reasoning / Content Chars | `5,268` / `40,368` | `0` / `48,532` | `16,840` / `32,240` |
| Files Extracted | `index.html`, `llms.txt`, `robots.txt`, `_headers` (`4/4`) | `index.html`, `llms.txt`, `robots.txt`, `_headers` (`4/4`) | `index.html`, `llms.txt`, `robots.txt`, `_headers` (`4/4`) |
| Lighthouse (`Perf / A11y / BP / SEO`) | `100 / 100 / 100 / 100` (`80` raw) | `100 / 99 / 100 / 100` (`80` raw) | `100 / 100 / 100 / 100` (`80` raw) |
| CLS / LCP | `0` / `268 ms` | `0` / `288 ms` | `0` / `308 ms` |
| Console / Page Errors (Post-CSP) | `0` / `0` | `0` / `0` | `0` / `0` (after converting `data:text/css,` to `<style>`) |
| External Network Requests | `0` | `0` | `0` |
| Horizontal Overflow (`1440px` / `375px`) | `false` / `true` (`376px` vs `375px`) | `false` / `false` | `false` / `false` (`375px` vs `375px`) |
| `:root` OKLCH Tokens & Max Contrast | `11` (`15.00:1` PASS) | `11` (`15.56:1` PASS) | `7` (`18.32:1` PASS) |
| Security Headers in `_headers` | `7/7` (`all_passed: true`) | `7/7` (`all_passed: true`) | `7/7` (`all_passed: true`) |
| Verbatim FAQ Match (HTML vs JSON-LD) | `5/5` (`100%` exact) | `5/5` (`100%` exact) | `5/5` (`100%` exact) |

---

## 3. Full 12-Task Matrix on Local `gyro-m-local` (`D:\Strata`, `TQ2_0` 2.06 bpw)

| Task | Category / Canon (Lang) | Time (`s`) | Speed (`tok/s`) | Comp. Tokens (`finish`) | Files (`pres/req`) | Lighthouse (`P/A/BP/SEO`) | Overflow (`1440`/`375`) | OKLCH (`count` / `contrast`) | Verbatim FAQ | Key Automated / Runtime Findings |
|---|---|---:|---:|---:|---:|---|---|---|---|---|
| `t1` | Industrial B2B (`EN`) | `652.63` | `31.1` | `20,000` (`length`) | `4/4` | `100/100/100/100` (`80` raw) | `false` / `false` | `15` (`18.79:1`) | `5/5` (`True`) | `CLS=0`, `LCP=368ms`, `0` console errs; `_headers` `6/7` (missing `COOP`, repetition tail in `Permissions-Policy`) |
| `t2` | Vision-to-Code #1 (`EN`) | `415.72` | `28.4` | `11,559` (`stop`) | `1/1` | `100/100/100/60` | `false` / `false` | `11` (`13.33:1`) | — | `CLS=0`, `LCP=312ms`, `0` external requests (`9` inline SVGs), accurate layout & OCR |
| `t3` | Luxury Minimalism (`RU`) | `821.12` | `20.9` | `16,939` (`stop`) | `4/4` | `100/100/100/100` (`80` raw) | `false` / `false` | `7` (`18.32:1`) | `5/5` (`True`) | `CLS=0`, `LCP=308ms`, `_headers` `7/7`, `data:text/css,` converted to `<style>` by CSP postprocessor; desktop H1 word `'архитектурных'` clips into hero SVG |
| `t4` | TypeScript Async DAG (`EN`) | `278.38` | `31.3` | `8,482` (`stop`) | `1/1` | — (`dag.ts`) | — | — | — | `tsc --strict` **FAIL** (`TS2683` `'this'` implicit `any` at line 405); Unit tests **`5/12 PASS`** (IDs `1,4,5,6,7` pass; IDs `2,3,8–12` timeout at `3000ms` due to `ready.size` on an Array) |
| `t5` | Swiss Grid + Subgrid (`EN`) | `667.65` | `36.5` | `24,000` (`length`) | `1/4` | `100/77/100/40` | `false` / `false` | `0` (`0.0:1`) | `0` (`False`) | **2-bit `TQ2_0` repetition loop** inside `<meta http-equiv="Content-Security-Policy">` (`3Z0Qq3Z0...`), truncated before `</head>` |
| `t6` | High-Tech SaaS + WebGL (`EN`) | `971.06` | `25.5` | `24,000` (`length`) | `1/4` | `100/100/100/80` | `false` / `false` | `11` (`17.40:1`) | `5/5` (`True`) | `CLS=0`, `LCP=440ms`, `0` console errs, `has_canvas=True`, `has_webgl_or_shader=True`, 6-cell Bento grid + VRAM calculator; GLSL shader dimension mismatch & truncated at 24k tok mid-FAQ |
| `t7` | Neo-Brutalism (`RU`) | `445.53` | `55.4` | `24,000` (`length`) | `1/4` | `100/77/100/40` | `false` / `false` | `0` (`0.0:1`) | `0` (`False`) | **2-bit `TQ2_0` repetition loop** inside `<meta http-equiv="Content-Security-Policy">` (`n3m5n9n5...`), truncated before `</head>` |
| `t8` | Editorial + Container (`RU`) | `411.45` | `31.2` | `12,450` (`stop`) | `1/4` | `100/93/100/80` | `false` / `false` | `0` (`0.0:1`) | `0` (`False`) | **2-bit `TQ2_0` repetition loop** of base64 string (`Ig0LXRgtGB0Y...`) in `<head>`, terminated before `<body>` |
| `t9` | Agentic 7-File + Z-Image (`EN`) | `790.52` | `30.7` | `24,000` (`length`) | `4/7` | `100/100/100/80` | `false` / `false` | `15` (`18.24:1`) | `0` (`False`) | Extracted `DESIGN.md` (`8,525 B`), `tokens.css` (`3,468 B`), `app.js` (`13,987 B`), `index.html` (`38,891 B`); `CLS=0`, `LCP=292ms`, `0` console errs; truncated at 24k tok inside SVG before `zimage_prompts.json`, `llms.txt`, `_headers` |
| `t10` | High-Tech SaaS Dark (`RU`) | `862.42` | `28.2` | `24,000` (`length`) | `1/4` | `100/100/100/80` | `false` / `true` (`377px`) | `12` (`17.23:1`) | `5/5` (`True`) | `CLS=0`, `LCP=368ms`, `0` console errs, interactive FFT harmonics SVG & GOST ISO 10816 copy; `2px` mobile overflow (`377px` vs `375px`), truncated at 24k tok at tail of inline `<script>` |
| `t11` | 3D/Canvas Kinematics (`EN`) | `164.88` | `28.4` | `4,360` (`length`) | `1/4` | `100/77/100/40` | `false` / `false` | `0` (`0.0:1`) | `0` (`False`) | **2-bit `TQ2_0` repetition loop** inside `<meta>` CSP (`sha256-KRONOS_INLINE_SCRIPT_HASH_PLACEHOLDER_00000...`), truncated before `<body>` |
| `t12` | Vision-to-Code #2 (`EN`) | `274.38` | `31.6` | `7,849` (`stop`) | `1/1` | `100/100/100/60` | `false` / `false` | `11` (`18.62:1`) | — | `CLS=0`, `LCP=264ms`, `0` console errs, `0` external requests, near-pixel-perfect dark telemetry + Swiss pricing matrix match to `eval/suite/ref/t12.png` |

---

## 4. Independent Blind Judge Scores (`Gemini 3.8 Flash`, `n=2`)

Aggregated by [`eval/suite/aggregate_judges.py`](../aggregate_judges.py) ([`eval/suite/results/judges_aggregated.json`](judges_aggregated.json)) across the 4 rubric criteria (`canon`, `design`, `copy`, `ru` + `overall`).  
- **Historical `t1–t3` (`qwen3.8-think-8k`, `qwen3.8-no-think`):** evaluated by blind Judge 1 (`6f2608fd`) and Judge 2 (`981f31f2`) — `0` discrepancies `> 2.0` points.  
- **Local `t1–t12` (`gyro-m-local`):** evaluated by blind Judge 1 (`21f65f3a`) and Judge 2 (`460d6fe0`) — `1` discrepancy `> 2.0` points (`gyro-m-local / t4 / copy`: Judge 1 `5.5` vs Judge 2 `8.0`, `diff = 2.5`, because Judge 2 weighted type/interface completeness higher while Judge 1 penalized `copy` alongside `canon`/`design` for the runtime hang).

| Run | Task | `canon` (`0–10`) | `design` (`0–10`) | `copy` (`0–10`) | `ru` (`0–10`) | **Mean `overall`** |
|---|---|---|---|---|---|---|
| `qwen3.8-think-8k` | `t1` | `10.00` (`10.0 / 10.0`) | `9.50` (`9.5 / 9.5`) | `9.50` (`9.5 / 9.5`) | — | **`9.67`** |
| `qwen3.8-think-8k` | `t2` | `9.50` (`9.5 / 9.5`) | `9.25` (`9.5 / 9.0`) | `9.75` (`9.5 / 10.0`) | — | **`9.50`** |
| `qwen3.8-think-8k` | `t3` | `9.50` (`9.5 / 9.5`) | `8.25` (`8.5 / 8.0`) | `9.50` (`9.5 / 9.5`) | `9.50` (`9.5 / 9.5`) | **`9.19`** |
| `qwen3.8-no-think` | `t1` | `9.00` (`9.0 / 9.0`) | `8.75` (`8.5 / 9.0`) | `9.25` (`9.0 / 9.5`) | — | **`9.00`** |
| `qwen3.8-no-think` | `t2` | `6.25` (`6.0 / 6.5`) | `5.75` (`5.5 / 6.0`) | `9.25` (`9.0 / 9.5`) | — | **`7.08`** |
| `qwen3.8-no-think` | `t3` | `7.50` (`7.0 / 8.0`) | `4.50` (`4.0 / 5.0`) | `9.00` (`9.0 / 9.0`) | `9.00` (`9.0 / 9.0`) | **`7.50`** |
| `gyro-m-local` | `t1` | `9.50` (`9.5 / 9.5`) | `9.25` (`9.0 / 9.5`) | `9.50` (`9.5 / 9.5`) | — | **`9.41`** |
| `gyro-m-local` | `t2` | `8.50` (`9.0 / 8.0`) | `8.00` (`8.5 / 7.5`) | `8.00` (`8.5 / 7.5`) | — | **`8.17`** |
| `gyro-m-local` | `t3` | `8.50` (`8.5 / 8.5`) | `7.25` (`7.5 / 7.0`) | `9.25` (`9.0 / 9.5`) | `9.25` (`9.0 / 9.5`) | **`8.57`** |
| `gyro-m-local` | `t4` | `5.50` (`5.5 / 5.5`) | `4.25` (`5.0 / 3.5`) | `6.75` (`5.5 / 8.0`)* | — | **`5.50`** |
| `gyro-m-local` | `t5` | `0.25` (`0.5 / 0.0`) | `0.25` (`0.5 / 0.0`) | `0.25` (`0.5 / 0.0`) | — | **`0.25`** |
| `gyro-m-local` | `t6` | `7.25` (`7.5 / 7.0`) | `6.50` (`7.0 / 6.0`) | `6.50` (`6.5 / 6.5`) | — | **`6.75`** |
| `gyro-m-local` | `t7` | `0.25` (`0.5 / 0.0`) | `0.25` (`0.5 / 0.0`) | `0.25` (`0.5 / 0.0`) | `0.25` (`0.5 / 0.0`) | **`0.25`** |
| `gyro-m-local` | `t8` | `0.25` (`0.5 / 0.0`) | `0.25` (`0.5 / 0.0`) | `0.75` (`0.5 / 1.0`) | `0.75` (`0.5 / 1.0`) | **`0.50`** |
| `gyro-m-local` | `t9` | `7.75` (`8.0 / 7.5`) | `7.00` (`7.5 / 6.5`) | `6.50` (`6.5 / 6.5`) | — | **`7.08`** |
| `gyro-m-local` | `t10` | `8.75` (`9.0 / 8.5`) | `8.25` (`8.5 / 8.0`) | `8.75` (`9.0 / 8.5`) | `9.25` (`9.5 / 9.0`) | **`8.75`** |
| `gyro-m-local` | `t11` | `0.25` (`0.5 / 0.0`) | `0.25` (`0.5 / 0.0`) | `0.25` (`0.5 / 0.0`) | — | **`0.25`** |
| `gyro-m-local` | `t12` | `9.50` (`9.5 / 9.5`) | `9.50` (`9.5 / 9.5`) | `9.00` (`9.0 / 9.0`) | — | **`9.33`** |

---

## 5. Architectural Conclusions for Steps 4–8 (Why REAP + `IQ3_S`/`IQ3_XXS` Beats 2-Bit `TQ2_0`)

1. **Empirical Proof of 2-Bit (`TQ2_0` 2.06 bpw) Fragility:** While `Gyro-M` (`TQ2_0`, all 512 experts at 2.06 bpw) achieves strong scores when generation completes (`9.41` on `t1`, `9.33` on `t12`, `8.75` on `t10`, `8.57` on `t3`, `8.17` on `t2`), extreme 2-bit quantization suffers from **two severe failure modes**:
   - **High-entropy string repetition loops (`4/12` tasks: `t5, t7, t8, t11`):** When asked to emit a `<meta http-equiv="Content-Security-Policy">` with `'sha256-...'` hashes in `<head>`, `TQ2_0` falls into an infinite base64 token repetition loop (`3Z0Qq3Z0...`, `n3m5n9n5...`), burning all `24,000` tokens before `<body>`.
   - **Logical/type precision degradation on `t4` (`dag.ts`):** `TQ2_0` wrote `ready.size` on a JavaScript `Array` (`const ready: string[] = []`), causing an infinite synchronous busy-wait loop when `activeCount > 0`, and used unbound `this.nodes` inside a nested `function runNode` (`TS2683`).
2. **Direct Implication for SmartLLM Surgery & Calibration (Steps 4–8):**
   - Keeping **205 experts at 3.2–3.7 bpw (`IQ3_XXS` / `IQ3_S` with calibration `imatrix`)** instead of 512 experts at 2.06 bpw (`TQ2_0`) preserves token logit precision during high-entropy sequences (SHA-256 base64 strings, GLSL shaders, TypeScript strict generics).
   - In Step 4 (`data/calib/`) and Step 8 inference, models should use a short deterministic placeholder token in `<meta http-equiv="Content-Security-Policy">` during generation and let `apply_csp_postprocessor` in `eval/suite/audit_suite.py` inject the exact SHA-256 hashes deterministically.
