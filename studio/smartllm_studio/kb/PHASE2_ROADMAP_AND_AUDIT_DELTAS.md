# SmartLLM Studio Phase 2 Roadmap & Verified `v0.0.4-beta` Audit Deltas

> **Scope:** Phase 1 delivers `studio/smartllm_studio/kb/` + `studio/tests/test_kb_integrity.py`. Execute these upgrades, asset downloads, and bug fixes in **Phase 2** after owner approval.

## 1. 4-Layer Orthogonal Template Architecture (Tab 3 Pro Ready)
Compile from 4 orthogonal layers instead of `5×20×2 = 200` duplicated folders:
1. `templates/vendor/` — Self-hosted SIL OFL-1.1 `.woff2` subsets (`cyrillic`+`latin`) + MIT JS libs + `LICENSES.json` + SHA-256.
2. `templates/stacks/` — 5 authentic scaffolds (`html5_esm`, `vite_ts 8.3.8/TS 7.x`, `astro 7.4.13`, `sveltekit 3.4.0/Svelte 5.59.1`, `nextjs 16.4.6 LTS`).
3. `templates/themes/` — 20 visual canons (`01`..`20`) with `light` + `dark` OKLCH palettes (`border_control >= 3.0:1`), Desktop/Tablet/Mobile clamp scales, and polarity shadows.
4. `templates/blocks/` — 19 blocks × 3–5 variants routed by `styles/blocks/_matrix.json`; pages serialize as JSON arrays `{id, block, variant, overrides, copy, media}` for post-v0.0.5 **Tab 3 Pro Editor**.

## 2. Launcher UI Upgrades (`A4`) & GSAP License Boundary
- **UI (`A4`):** Remove always-open half-screen preview pane on boot (open ONLY after build). Generate 20 `"SmartLLM"` style preview cards via Nano Banana (`image-generator`).
- **GSAP vs 100% MIT:** Webflow Standard License `Prohibited Uses` bars bundling GSAP inside visual animation/website builders (`Competitive Products`). Bundle ONLY **100% MIT** (`motion 14.14.0` core — NOT paid `Motion+`, `animejs 4.5.0`, `lenis 1.3.27`, `three 0.187.0`) + CSS Scroll-Driven Animations (`scroll()`/`view()`, Baseline Oct 2026); mention GSAP only as optional external user `npm install`.

## 3. Sixteen Audited `v0.0.4-beta` Bugs to Fix in Phase 2
1. Hero `opacity: 0` `[data-reveal]` hides LCP copy/img + missing `fetchpriority="high"` (`blueprint_render.py:310,704,714`).
2. Broken single-URL `/en/`/`/ru/` `hreflang` (`blueprint_render.py:630-635`).
3. JSON-LD hardcoded `DE`, `BreadcrumbList` on `index`, bare `Product`, fake `price:"0"`, missing `og:image`, ignored `<changefreq>` (`blueprint_render.py:588,601,606,613,1266,1391`).
4. Missing `Claude-SearchBot: True` in `catalog.py:58-67`.
5. SVG sanitizer missing SMIL/`<style>`/`<use>`/`data:image/svg+xml`/XXE (`sanitizer.py:12-61`); `logo_path` lacks `allowed_roots` check (`blueprint.py:237-239`).
6. Hardcoded `"passed": True` scorecard (`blueprint.py:402-408`).
7. Missing `@font-face` / `.woff2` bundling in `blueprint.py`/`blueprint_render.py`.
8. Non-Cyrillic `Archivo Black` in `canon_cards.json:2088`.
9. 5 card/dossier polarity mismatches (`06,07,08,10,19`) + `0.32` dark glass alpha (`canon_cards.json:299`).
10. Single `--radius`, missing `--border-control` (`WCAG 1.4.11`), invisible dark hover shadows (`blueprint_render.py:96,133,163,222`).
11. iOS `background-attachment: fixed` jank (`blueprint_render.py:109`).
12. `360px` & WCAG bugs: `hero-overlay` mobile scrim, 5th `#node-calc-output` element, tall mobile sticky header, unpausable marquee, non-keyboard `.price-table-wrap`/`.gal-filmstrip`, RU `h1`/`.stat-band` clipping, `<44px` coarse targets, `aria-live` on disabled button (`blueprint_render.py`).
13. `brand_words`/`member_names` word-deletion bug (`pipeline.py:126-133`, `orchestrator.py:198-201,1570`).
14. Z-Image `"zero text"`, `"no outline"`, `#HEX`, `oklch()` leaks (`pipeline.py:1161`, `orchestrator.py:102,105,167`, `canon_cards.json`).
15. Visuals prompt receives 1-line `hero_subject` instead of finalized block copy (`pipeline.py:1162-1182`).
16. Outdated stack catalog & 2-line scaffolds (`catalog.py:13-19`, `blueprint.py:1424-1438`); wire EN/RU anti-AI linter.
