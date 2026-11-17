#!/usr/bin/env python3
"""Deterministic builder for SmartLLM v2 RAG Checklists (SEO/AEO/GEO, CSP/Headers, WCAG 2.2/Layout, Z-Image)."""

import json
import os

HARVEST_DIR = "/mnt/rescue/projects/SmartLLM/data/harvest"
CHECKLISTS_DIR = os.path.join(HARVEST_DIR, "checklists")
CURATED_DATE = "2026-11-15"

SEO_JSON = {
    "id": "checklist_seo_aeo_geo_jsonld_v2",
    "title": "SEO, AEO, GEO, Schema.org @graph, llms.txt & AI Crawler Checklist",
    "provenance": {
        "source": "research/replan/web_reference_standard.md + W3C/Schema.org/llmstxt.org",
        "curated_date": CURATED_DATE,
        "license": "CC0-1.0 / Internal RAG Canon",
        "rag_only": True,
    },
    "checks": [
        {
            "check_id": "SEO-META-01",
            "severity": "critical",
            "summary": "Complete document head metadata (<title>, description, canonical, OpenGraph)",
            "rule": "Include non-empty <title> (45-65 chars), <meta name='description'> (120-160 chars), <link rel='canonical' href='https://...'>, and og:title, og:description, og:type, og:url, og:locale.",
            "verification": "HTML AST check on head tags; zero empty content attributes.",
        },
        {
            "check_id": "SEO-JSONLD-01",
            "severity": "critical",
            "summary": "Unified Schema.org @graph in <script type='application/ld+json'>",
            "rule": "Provide a single valid JSON-LD @graph uniting WebSite, Organization, WebPage, Product (or SoftwareApplication/TechArticle), BreadcrumbList, and FAQPage linked via @id URIs.",
            "verification": "json.loads() succeeds; @graph contains Organization, Product, BreadcrumbList, FAQPage.",
        },
        {
            "check_id": "SEO-FAQ-MATCH",
            "severity": "critical",
            "summary": "100% verbatim parity between JSON-LD FAQPage and visible <main> HTML text",
            "rule": "Every Question.name and acceptedAnswer.text string inside FAQPage.mainEntity MUST appear character-for-character verbatim in visible HTML prose.",
            "verification": "Normalized substring match of every JSON-LD Q&A pair against stripped visible HTML.",
        },
        {
            "check_id": "SEO-LLMS-01",
            "severity": "high",
            "summary": "Root /llms.txt machine-readable index per llmstxt.org",
            "rule": "Start with single '# Project Title' H1, immediately followed by '> Concise one-paragraph summary' blockquote, then '## Section' H2 lists containing markdown links with factual descriptions.",
            "verification": "Multiline regex check for ^# \\S+, ^> \\S+, and ^## \\S+.",
        },
        {
            "check_id": "SEO-ROBOT-AI",
            "severity": "high",
            "summary": "Granular /robots.txt separating AI weight-training vs live AI search citation bots",
            "rule": "Disallow foundation-model training crawlers (GPTBot, ClaudeBot, Google-Extended, CCBot) while explicitly allowing live search/citation crawlers (OAI-SearchBot, Claude-SearchBot, PerplexityBot, Googlebot) plus Sitemap URL.",
            "verification": "Parse User-agent blocks in robots.txt and verify both training and search agent groups appear.",
        },
        {
            "check_id": "SEO-HREFLANG",
            "severity": "high",
            "summary": "Bidirectional i18n hreflang links (en, ru, x-default)",
            "rule": "Include self-referencing and alternate <link rel='alternate' hreflang='en' href='...'>, hreflang='ru', and fallback hreflang='x-default'.",
            "verification": "Check <link rel='alternate'> set contains {'en', 'ru', 'x-default'}.",
        },
        {
            "check_id": "SEO-CWV-2026",
            "severity": "high",
            "summary": "Core Web Vitals field & synthetic thresholds",
            "rule": "LCP <= 2.5s, INP <= 200ms, CLS <= 0.1 (target CLS = 0.00 via explicit width/height on SVGs/images and zero external font waterfalls).",
            "verification": "Playwright + Lighthouse synthetic audit at 375x812 and 1440x900.",
        },
    ],
    "robots_txt_reference": (
        "# AI Training Crawlers (Opt-out of weight training)\n"
        "User-agent: GPTBot\nDisallow: /\n\n"
        "User-agent: ClaudeBot\nDisallow: /\n\n"
        "User-agent: Google-Extended\nDisallow: /\n\n"
        "User-agent: CCBot\nDisallow: /\n\n"
        "# Live Search & AI Citation Retrieval Crawlers (Permitted)\n"
        "User-agent: OAI-SearchBot\nAllow: /\n\n"
        "User-agent: Claude-SearchBot\nAllow: /\n\n"
        "User-agent: PerplexityBot\nAllow: /\n\n"
        "User-agent: Googlebot\nAllow: /\n\n"
        "User-agent: *\nAllow: /\nSitemap: https://example.org/sitemap.xml\n"
    ),
}

SEO_MD = """# SEO / AEO / GEO & Schema.org `@graph` Checklist (2026 Baseline)

**Status:** RAG-only (`data/harvest/checklists/`) | **Date:** 2026-11-15

## 1. Mandatory Head & `hreflang` Contract
- Include `<title>`, `<meta name="description">`, `<link rel="canonical">`, and OpenGraph tags (`og:title`, `og:description`, `og:type`, `og:url`, `og:locale`).
- Include bidirectional `<link rel="alternate" hreflang="en" href="...">`, `hreflang="ru"`, and `hreflang="x-default"`.

## 2. Schema.org JSON-LD `@graph` + Verbatim FAQ Parity
- Embed one `<script type="application/ld+json">` (exempt from `script-src` execution hashes, parsed as data) uniting `WebSite`, `Organization`, `WebPage`, `Product`, `BreadcrumbList`, and `FAQPage`.
- **Hard Invariant (`SEO-FAQ-MATCH`):** Every `Question.name` and `acceptedAnswer.text` inside `FAQPage.mainEntity` MUST match the visible HTML text inside `<main>` character-for-character. Never summarize or paraphrase FAQ text inside JSON-LD.

## 3. `/llms.txt` & `/robots.txt` AI Crawler Separation
- `/llms.txt` MUST contain: `# Brand / Product Name` (H1), `> Single-paragraph factual summary` (blockquote), and `## Documentation` / `## Specifications` (H2 sections with markdown links).
- `/robots.txt` MUST separate corpus-training bots (`GPTBot`, `ClaudeBot`, `Google-Extended`, `CCBot` -> `Disallow: /`) from real-time citation/retrieval bots (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `Googlebot` -> `Allow: /`).

## 4. Core Web Vitals & Inverted-Pyramid Copy
- Place a 40-60 word factual answer with concrete numbers directly beneath semantic `<h2>`/`<h3>` question headings.
- Hold `LCP <= 2.5s`, `INP <= 200ms`, and `CLS <= 0.1` by shipping local fonts/system stacks and explicit `viewBox`/`width`/`height` on all inline SVGs.
"""

SEC_JSON = {
    "id": "checklist_security_csp_headers_v2",
    "title": "Hash-Based CSP, Trusted Types & Cloudflare _headers Checklist",
    "provenance": {
        "source": "research/replan/web_reference_standard.md + W3C CSP3 + Cloudflare Pages Spec",
        "curated_date": CURATED_DATE,
        "license": "CC0-1.0 / Internal RAG Canon",
        "rag_only": True,
    },
    "checks": [
        {
            "check_id": "SEC-CSP-HASH",
            "severity": "critical",
            "summary": "Exact SHA-256 hashes for every inline <style> and executable <script>; zero 'unsafe-inline'",
            "rule": "Compute sha256-<base64> over exact UTF-8 inner text of each <style> and executable <script>. Set default-src 'none'; script-src 'self' 'sha256-...'; style-src 'self' 'sha256-...'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; object-src 'none'. Include frame-ancestors 'none' in _headers (omit frame-ancestors inside <meta http-equiv>).",
            "verification": "Recompute SHA-256 base64 digests of all inline blocks and assert 100% match in both <meta> and _headers.",
        },
        {
            "check_id": "SEC-TRUST-TYP",
            "severity": "critical",
            "summary": "Enforce require-trusted-types-for 'script' and zero inline DOM style/event mutations",
            "rule": "Include require-trusted-types-for 'script' in CSP. Never use inline HTML event attributes (onclick, oninput) or JS .style.* / setAttribute('style', ...) mutations; mutate textContent, hidden, aria-*, dataset, classList, or SVG geometry attributes.",
            "verification": "HTML parser inline_event_handlers == 0 and JS AST/regex js_style_mutations == 0.",
        },
        {
            "check_id": "SEC-HDR-SYN",
            "severity": "critical",
            "summary": "Strict Cloudflare Pages _headers grammar (# comments only, NEVER /* ... */)",
            "rule": "Comments MUST start at column 0 with '#'. NEVER write C-style /* ... */ comments because '/*' is parsed as a literal catch-all URL route. Place '/*' alone on an unindented line followed by 2-space indented Header: value lines.",
            "verification": "Deterministic _parse_cloudflare_headers() reports format_error is None and has_route_rule is True.",
        },
        {
            "check_id": "SEC-HDR-BASE",
            "severity": "critical",
            "summary": "Transport & browser hardening headers",
            "rule": "Include Strict-Transport-Security: max-age=63072000; includeSubDomains; preload, X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Referrer-Policy: strict-origin-when-cross-origin, and Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=().",
            "verification": "All 5 headers present and valid under /* route.",
        },
        {
            "check_id": "SEC-ISOLATE",
            "severity": "high",
            "summary": "Cross-origin isolation triad (COOP + COEP + CORP)",
            "rule": "Set Cross-Origin-Opener-Policy: same-origin, Cross-Origin-Embedder-Policy: require-corp, and Cross-Origin-Resource-Policy: same-origin.",
            "verification": "Verify exact COOP, COEP, and CORP directives in _headers.",
        },
        {
            "check_id": "SEC-FORM-HYG",
            "severity": "high",
            "summary": "Form honeypot, autocomplete tokens, and zero client secrets",
            "rule": "Bind every visible input to an explicit <label for='...'> with standard autocomplete tokens; add an off-screen/hidden honeypot field (aria-hidden='true', tabindex='-1', autocomplete='off') checked before submission.",
            "verification": "All visible inputs labeled; honeypot input present on lead/intake forms; zero API keys.",
        },
    ],
}

SEC_MD = """# Strict CSP, Trusted Types & Cloudflare `_headers` Checklist

**Status:** RAG-only (`data/harvest/checklists/`) | **Date:** 2026-11-15

## 1. Hash-Based CSP & Zero `.style.*` Mutation Invariant
1. Compute `sha256-<base64>` on the exact UTF-8 string inside every `<style>...</style>` and executable `<script>...</script>` (note: `<script type="application/ld+json">` is inert JSON data, not executable JS).
2. **Never** use `'unsafe-inline'` or `'unsafe-eval'`.
3. **Never** mutate `.style.foo = ...`, `.style.setProperty(...)`, or `setAttribute('style', ...)` in TypeScript/JavaScript: under strict `style-src` hashes without `'unsafe-inline'`, inline style attribute writes are blocked or flagged. Update `textContent`, `<output>`, `<progress>`, `dataset`, `classList`, `aria-*`, or SVG `width`/`y`/`points` attributes instead.
4. Include `require-trusted-types-for 'script'` and avoid `innerHTML` completely (use `textContent` or `document.createElement`).

## 2. Cloudflare Pages `_headers` Golden Template
```text
# Global security policy for static edge deployment
/*
  Content-Security-Policy: default-src 'none'; script-src 'self' 'sha256-SCRIPT_HASH'; style-src 'self' 'sha256-STYLE_HASH'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; require-trusted-types-for 'script'
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: require-corp
  Cross-Origin-Resource-Policy: same-origin
```
- **CRITICAL GRAMMAR TRAP:** Never write `/* comment */` in `_headers`! Only `# comment` starting at column 0 is legal.
"""

LAY_JSON = {
    "id": "checklist_layout_wcag22_viewport_v2",
    "title": "Modern CSS Grid/Subgrid, Container Queries, Dynamic Viewport & WCAG 2.2 AA/AAA Checklist",
    "provenance": {
        "source": "research/replan/design_eval_and_canons.md + W3C WCAG 2.2 + CSS Grid Level 2 / Values Level 4",
        "curated_date": CURATED_DATE,
        "license": "CC0-1.0 / Internal RAG Canon",
        "rag_only": True,
    },
    "checks": [
        {
            "check_id": "LAY-VIEWPORT-DVH",
            "severity": "critical",
            "summary": "Use 100svh / 100dvh dynamic viewport units; forbid raw 100vh layout overflow",
            "rule": "Size full-height hero shells and mobile drawers with min-height: 100svh or 100dvh so mobile browser chrome never clips sticky actions. Never use raw 100vh.",
            "verification": "CSS scan confirms 100svh or 100dvh present and zero bare 100vh tokens.",
        },
        {
            "check_id": "LAY-GRID-CONTAINER",
            "severity": "high",
            "summary": "12-column CSS Grid + subgrid card lock + @container queries + tabular-nums",
            "rule": "Build macro page structure on explicit CSS Grid; align multi-card header/body/footer rows with grid-template-rows: subgrid; adapt component internals via container-type: inline-size and @container; enforce font-variant-numeric: tabular-nums on metrics and tables.",
            "verification": "CSS contains grid-template-columns, subgrid, container-type, @container, and tabular-nums.",
        },
        {
            "check_id": "LAY-ZERO-CDN",
            "severity": "critical",
            "summary": "Zero Tailwind utility slop and zero external HTTP(S) asset requests",
            "rule": "Author semantic custom CSS with oklch() custom properties. Never import cdn.tailwindcss.com, Google Fonts, unpkg, jsdelivr, or remote images.",
            "verification": "Zero Tailwind class matches and external_urls_in_attrs == [].",
        },
        {
            "check_id": "A11Y-CONTRAST",
            "severity": "critical",
            "summary": "OKLCH 3-channel custom properties achieving >= 7.0:1 AAA primary text & >= 4.5:1 AA muted/accent",
            "rule": "Declare core palette tokens (--bg, --surface, --border, --text, --text-muted, --accent, --accent-ink) as 3-number oklch(L C H) values verified via linearized sRGB relative luminance.",
            "verification": "parse_oklch_tokens() confirms contrast(text, bg) >= 7.0 and contrast(accent_ink, accent) >= 4.5.",
        },
        {
            "check_id": "A11Y-WCAG22",
            "severity": "critical",
            "summary": "WCAG 2.2 2.4.11 Focus Not Obscured & 2.5.8 Target Size >= 24x24 CSS px",
            "rule": "Set html { scroll-padding-top: 72px; } (>= sticky header height) so focused anchors are never obscured. Enforce min-width: 24px; min-height: 24px on all buttons, inputs, and interactive controls.",
            "verification": "CSS defines scroll-padding-top and min-height/min-width >= 24px on interactive selectors.",
        },
        {
            "check_id": "A11Y-LANDMARK",
            "severity": "critical",
            "summary": "Semantic HTML5 landmarks, single <h1>, skip-link, and 100% labeled inputs",
            "rule": "Provide <header>, <nav>, <main id='main-content'>, <footer>, skip-to-main link, exactly one <h1>, and explicit <label for='...'> for every visible form control.",
            "verification": "h1_count == 1, landmarks >= {header, nav, main, footer}, form_inputs_labeled == visible_inputs.",
        },
        {
            "check_id": "A11Y-MOTION",
            "severity": "high",
            "summary": "Respect @media (prefers-reduced-motion: reduce)",
            "rule": "Include an explicit @media (prefers-reduced-motion: reduce) block zeroing transition-duration, animation-duration, and smooth scroll.",
            "verification": "CSS contains @media (prefers-reduced-motion: reduce).",
        },
    ],
}

LAY_MD = """# Modern CSS Layout, Dynamic Viewport & WCAG 2.2 AA/AAA Checklist

**Status:** RAG-only (`data/harvest/checklists/`) | **Date:** 2026-11-15

## 1. Viewport & Responsive Grid Rules
- **Dynamic Viewport (`100svh` / `100dvh`):** Never write `height: 100vh` or `min-height: 100vh` (causes mobile browser toolbar overflow). Use `min-height: 100svh` for stable hero shells and `100dvh` for dynamic sheets.
- **Macro Grid + Micro Container Queries:** Use a 12-column CSS Grid (`grid-template-columns: repeat(12, minmax(0, 1fr))`), lock card internal tracks with `grid-template-rows: subgrid; grid-row: span 3;`, and wrap modular widgets in `container-type: inline-size` with `@container (max-width: ...)` rules.
- **Modular Scale & Numeric Rhythm:** Adhere to `4, 8, 16, 24, 32, 48, 64px` spacing steps, `clamp()` fluid section padding, `55ch-66ch` prose measure, and `font-variant-numeric: tabular-nums` on every KPI, price, and table cell.

## 2. WCAG 2.2 AA/AAA Hard Gates
- **1.4.6 Contrast (Enhanced):** Define `--bg`, `--surface`, `--border`, `--text`, `--text-muted`, `--accent`, `--accent-ink` in pure `oklch(L C H)` syntax (no `/ alpha` on base tokens) with `contrast(--text, --bg) >= 7.0:1` and `contrast(--accent-ink, --accent) >= 4.5:1`.
- **2.4.11 Focus Not Obscured:** Declare `html { scroll-padding-top: 4.75rem; }` whenever `<header>` is `position: sticky`, and style `:focus-visible` with a `2px solid var(--accent)` outline + `2px` offset.
- **2.5.8 Target Size (Minimum):** Guarantee `min-width: 24px; min-height: 24px` (prefer `>= 36px-44px` on primary buttons/inputs) across all interactive controls.
- **2.3.3 / Reduced Motion:** Include `@media (prefers-reduced-motion: reduce)` disabling transitions and animations.
"""

ZIMAGE_JSON = {
    "id": "checklist_zimage_canon_prompts_v2",
    "title": "Sequential Z-Image Visual Pipeline & Canon Prompt Checklist",
    "provenance": {
        "source": "CLAUDE.md §4.2 Zero-Swap Sequential GPU Rule + design_eval_and_canons.md",
        "curated_date": CURATED_DATE,
        "license": "CC0-1.0 / Internal RAG Canon",
        "rag_only": True,
    },
    "sequential_vram_protocol": [
        "1. Generate HTML/CSS/TS + zimage_prompts.json via LLM while Z-Image is unloaded.",
        "2. Stop llama-server cleanly and assert 0 compute MiB on RTX 4080 (12 GB VRAM) and pswpout == 0.",
        "3. Load Z-Image sequentially, render each prompt to local WebP/PNG matching exact aspect_ratio, then unload Z-Image and re-verify 0 compute MiB.",
        "4. On any GPU error, stop immediately without auto-retry loops.",
    ],
    "prompt_engineering_rules": [
        "Length >= 200 characters specifying physical material, focal length (e.g. 35mm tilt-shift, 90mm macro), lighting geometry, and tonal palette matching the active canon_card.",
        "Include exact_text_in_frame field (1-3 crisp uppercase/numeric stencil words) and embed that exact string verbatim inside the prompt when typographic signage or label detail is requested.",
        "Always attach explicit negative_prompt banning purple neon fog, floating 3D blobs, stock handshakes, lens flare clutter, and garbled watermarks.",
    ],
    "canon_prompt_archetypes": [
        {
            "canon_id": "01_swiss_international_typographic",
            "aspect_ratio": "16:9",
            "exact_text_in_frame": "NODE 04",
            "prompt": "Architectural brutalist board-formed concrete telemetry hall interior, crisp geometric morning sunlight casting sharp 45-degree shadow across brushed steel equipment bay stenciled with exact industrial typography 'NODE 04', Leica Summicron 35mm f/8 orthographic perspective, silver-gelatin neutral monochrome with tiny vermilion status indicator, museum-grade clarity.",
            "negative_prompt": "purple neon glow, floating 3d spheres, corporate handshake, lens flare, cartoon, oversaturated HDR",
        },
        {
            "canon_id": "02_neo_brutalism_tactile",
            "aspect_ratio": "4:3",
            "exact_text_in_frame": "WAL SYNC",
            "prompt": "Isometric cutaway mechanical storage cartridge diagram printed on warm cream heavy drafting stock, bold 2.5pt matte black ink outlines, flat screenprint electric lime and charcoal spot fills, crisp technical callout plate reading 'WAL SYNC', overhead flat-lay studio illumination, sharp paper grain.",
            "negative_prompt": "blurry airbrush gradient, photorealistic face, dark cyberpunk fog, soft drop shadow, watermark",
        },
        {
            "canon_id": "03_dark_precision_saas_linear",
            "aspect_ratio": "16:9",
            "exact_text_in_frame": "P99 4.2MS",
            "prompt": "Macro studio product photograph of CNC-machined dark slate anodized aluminum network tap chassis on matte obsidian stone, subtle indigo optical fiber edge light and crisp laser-etched OLED readout displaying 'P99 4.2MS', 90mm apochromatic macro lens f/5.6, controlled specular micro-bevels.",
            "negative_prompt": "glowing purple brain, sci-fi hologram clutter, lens flare explosion, stock office team, washed-out fog",
        },
        {
            "canon_id": "05_nordic_architectural_minimal",
            "aspect_ratio": "16:9",
            "exact_text_in_frame": "RT60 0.48S",
            "prompt": "Nordic acoustic chamber crafted from vertical untreated Karelian birch slats and honed pale limestone floor, soft high-latitude overcast daylight entering tall timber mullions, discreet brass acoustic plaque engraved 'RT60 0.48S', Hasselblad 50mm medium-format natural color rendition, serene spatial calm.",
            "negative_prompt": "neon LED strips, cluttered furniture, glossy plastic, artificial HDR halo, people posing",
        },
    ],
}

STACK_JSON = {
    "id": "checklist_stack_architecture_patterns_v2",
    "title": "Modern Web Stack Architecture Patterns: Astro 5, Next.js App Router, SvelteKit & Vite + Strict TypeScript",
    "provenance": {
        "source": "Astro 5 Docs + Next.js App Router Spec + SvelteKit Docs + Vite/TS 6.0 Standard",
        "curated_date": CURATED_DATE,
        "license": "CC0-1.0 / Internal RAG Canon",
        "rag_only": True,
    },
    "checks": [
        {
            "check_id": "STACK-ASTRO-01",
            "severity": "critical",
            "summary": "Astro 5 Islands architecture, client:visible/client:idle hydration discipline, Content Collections + Zod schemas, zero-JS static/SSR split, and View Transitions",
            "rule": "Default all Astro components (.astro) to zero-JS static HTML rendering. Hydrate interactive UI islands strictly with client:visible or client:idle (reserve client:load only for above-the-fold critical interactive controls). Define structured content in src/content/config.ts using Astro Content Collections validated by strict Zod schemas (z.object). Keep static vs SSR route split explicit (prerender = true by default) and wire <ClientRouter /> View Transitions with prefers-reduced-motion fallback.",
            "verification": "Astro component audit confirms client:visible/client:idle directives, Zod Content Collection schema in config.ts, and zero unnecessary client:load islands.",
        },
        {
            "check_id": "STACK-NEXT-01",
            "severity": "critical",
            "summary": "Next.js App Router Server Components vs leaf 'use client', streaming Suspense, and Zod-validated Server Actions",
            "rule": "Keep root layouts, pages, and data-fetching trees as React Server Components (RSC) with zero client JS bundle overhead. Push 'use client' boundaries strictly to small interactive leaf components. Wrap async data boundaries in <Suspense fallback={...}> skeletons with fixed reserve geometry (CLS = 0.00). Validate every Server Action ('use server') and Route Handler input with a strict Zod schema before executing mutations.",
            "verification": "App Router tree check confirms RSC pages/layouts, leaf-only 'use client' modules, <Suspense> boundaries, and Zod .safeParse() in Server Actions.",
        },
        {
            "check_id": "STACK-SVELTE-01",
            "severity": "high",
            "summary": "SvelteKit +page.server.ts load/actions isolation and progressive form enhancement",
            "rule": "Keep privileged data loading and form mutations inside +page.server.ts Load and Actions exports so server secrets and database handles never leak into client bundles. Wire <form method='POST'> with SvelteKit use:enhance for progressive enhancement that functions before and after hydration.",
            "verification": "SvelteKit route audit confirms +page.server.ts data/action boundaries and progressive form enhancement.",
        },
        {
            "check_id": "STACK-VITE-TS-01",
            "severity": "critical",
            "summary": "Vite + strict TypeScript 6.0 modular offline bundle and deterministic state management",
            "rule": "Compile TypeScript with strict: true, noImplicitAny: true, strictNullChecks: true, and noUncheckedIndexedAccess: true. Package offline static bundles with explicit ES modules (<script type='module'>), deterministic finite state machines, zero external CDN dependencies, and zero inline DOM .style.* mutations under strict SHA-256 CSP.",
            "verification": "TypeScript 6.0.3 strict compiler check passes with 0 diagnostics and byte-exact SHA-256 CSP parity.",
        },
    ],
    "stack_profiles": {
        "astro": "Astro 5 Islands: render .astro pages to zero-JS static HTML; hydrate interactive islands only with client:visible or client:idle; validate src/content/config.ts collections with Zod schemas; keep static/SSR split explicit; guard View Transitions with prefers-reduced-motion.",
        "nextjs": "Next.js App Router: default layouts/pages to React Server Components (RSC); isolate 'use client' at leaf widgets; stream async sections via <Suspense fallback={...}>; validate all 'use server' Server Actions with Zod .safeParse().",
        "sveltekit": "SvelteKit: isolate server loads and form actions in +page.server.ts; apply progressive enhancement via <form method='POST' use:enhance>; preserve full functionality without client JS.",
        "vite_ts": "Vite + Strict TypeScript 6.0: compile under strict: true and noUncheckedIndexedAccess: true; emit self-contained ES module (<script type='module'>) with SHA-256 CSP hash and zero inline .style.* mutations.",
    },
}

STACK_MD = """# Modern Web Stack Architecture Patterns (Astro 5, Next.js, SvelteKit, Vite + TS)

**Status:** RAG-only (`data/harvest/checklists/`) | **Date:** 2026-11-15

## 1. Astro 5 Islands & Content Collections (`STACK-ASTRO-01`)
- **Zero-JS Default:** Render all `.astro` layouts, hero sections, specifications, and footers as pure static HTML with `0 KB` client JavaScript.
- **Selective Island Hydration:** Attach `client:visible` for below-the-fold interactive calculators/charts and `client:idle` for non-critical telemetry toggles. Never attach `client:load` to static sections.
- **Content Collections + Zod:** Define all domain schemas in `src/content/config.ts` via `defineCollection({ schema: z.object({ ... }) })` for build-time type safety.
- **Static/SSR Split & View Transitions:** Keep `export const prerender = true` on marketing and documentation routes; use `<ClientRouter />` View Transitions with `@media (prefers-reduced-motion: reduce)` fallback.

## 2. Next.js App Router (`STACK-NEXT-01`)
- **RSC First:** Keep `app/layout.tsx` and `app/page.tsx` as React Server Components; push `'use client'` down to leaf interactive controls (`FilterBar.tsx`, `ROICalculator.tsx`).
- **Streaming Suspense:** Wrap slow or independent data reads in `<Suspense fallback={<SkeletonCard />}>` with matching `min-height` to hold `CLS = 0.00`.
- **Zod-Validated Server Actions:** Every `'use server'` action MUST validate `FormData` or JSON inputs through `schema.safeParse()` before touching persistence layers.

## 3. SvelteKit Progressive Enhancement (`STACK-SVELTE-01`)
- **Server Boundary:** Place data fetching and form handlers in `+page.server.ts` (`load` and `actions`) so secrets and SQL/RPC clients stay strictly server-side.
- **Progressive Forms:** Pair native `<form method="POST">` with `use:enhance` so forms submit cleanly both with and without client JavaScript.

## 4. Vite + Strict TypeScript Modular Offline Bundles (`STACK-VITE-TS-01`)
- **Strict Compiler Gate:** Enforce `strict: true`, `noImplicitAny: true`, `strictNullChecks: true`, and `noUncheckedIndexedAccess: true` under TypeScript 6.0.
- **CSP-Clean DOM Updates:** Mutate `textContent`, `dataset`, `classList`, `aria-*`, `<output>`, or SVG geometry attributes (`width`, `y`, `points`); never mutate `.style.*` directly under hash-locked CSP.
"""

MOTION_JSON = {
    "id": "checklist_motion_gsap_choreography_v2",
    "title": "GSAP 3, ScrollTrigger, Flip Layout Choreography, Compositor 60fps & Reduced-Motion Checklist",
    "provenance": {
        "source": "GSAP 3.12+ Official Architecture + W3C WCAG 2.2 2.3.3 + CWV CLS=0.00 Spec",
        "curated_date": CURATED_DATE,
        "license": "CC0-1.0 / Internal RAG Canon",
        "rag_only": True,
    },
    "checks": [
        {
            "check_id": "MOT-GSAP-ST-01",
            "severity": "critical",
            "summary": "GSAP 3 + ScrollTrigger deterministic choreography (scrub, pin, batch, once: true)",
            "rule": "Register plugins explicitly with gsap.registerPlugin(ScrollTrigger, Flip). Use ScrollTrigger.batch() with once: true for staggered grid/card entrance reveals, numeric scrub (e.g. scrub: 0.6) only on dedicated narrative tracks, and pin: true with anticipatePin: 1 inside pre-sized containers so scroll pinning never triggers layout shift (CLS = 0.00).",
            "verification": "Motion script registers ScrollTrigger, uses batch/once or bounded scrub/pin, and preserves CLS == 0.00.",
        },
        {
            "check_id": "MOT-GSAP-FLIP-01",
            "severity": "high",
            "summary": "GSAP Flip (First-Last-Invert-Play) layout transitions for filtering and state changes",
            "rule": "Capture pre-change geometry via const state = Flip.getState(items), apply DOM class or attribute filtering synchronously, and animate via Flip.from(state, { duration: 0.45, ease: 'power2.out', nested: true }) to transition layout changes smoothly at 60fps without manual top/left reflow thrashing.",
            "verification": "Stateful layout filters use Flip.getState() -> DOM update -> Flip.from() sequence.",
        },
        {
            "check_id": "MOT-GSAP-CTX-01",
            "severity": "critical",
            "summary": "Lifecycle cleanup via gsap.context() and gsap.matchMedia() reduced-motion settled state",
            "rule": "Wrap all GSAP timelines and ScrollTriggers inside const ctx = gsap.context(() => { ... }, scopeEl) and invoke ctx.revert() on unmount. Gate animations with const mm = gsap.matchMedia(); when (prefers-reduced-motion: reduce) matches, bypass scrub/pin timelines and set elements immediately to their final settled visual state.",
            "verification": "Code contains gsap.context() with revert() cleanup and gsap.matchMedia() or prefers-reduced-motion guard.",
        },
        {
            "check_id": "MOT-COMPOSITOR-01",
            "severity": "critical",
            "summary": "Compositor-only 60fps properties (x, y, scale, opacity/autoAlpha) and zero layout thrashing",
            "rule": "Animate only GPU-composited transform and opacity channels (x, y, xPercent, yPercent, scale, rotation, opacity, autoAlpha). Never animate layout-inducing CSS properties (top, left, width, height, margin, padding) on scroll or frame ticks, keeping frame times <= 16.6ms (60fps) and CLS = 0.00.",
            "verification": "Zero top/left/width/height/margin tweens; all motion uses transform/opacity or SVG attributes.",
        },
        {
            "check_id": "MOT-CSP-SAFE-01",
            "severity": "critical",
            "summary": "Strict CSP / SHA-256 and external ES-module compliance (zero 'unsafe-inline', zero eval)",
            "rule": "Load GSAP/ScrollTrigger from local self-hosted ES modules ('self') or SHA-256 hashed <script type='module'> blocks with zero eval() and zero 'unsafe-inline'. Under strict style-src without 'unsafe-inline', drive motion via CSS class/dataset state transitions, Web Animations API element.animate(), SVG attribute tweens, or CSP-scoped module scripts without direct element.style.* string injection.",
            "verification": "CSP audit confirms zero 'unsafe-inline', zero 'unsafe-eval', and zero blocked inline style mutations.",
        },
    ],
}

MOTION_MD = """# GSAP 3, ScrollTrigger & Flip Choreography Checklist (60fps + Zero-CLS + CSP-Safe)

**Status:** RAG-only (`data/harvest/checklists/`) | **Date:** 2026-11-15

## 1. GSAP 3 + ScrollTrigger Discipline (`MOT-GSAP-ST-01`)
- Explicitly register plugins: `gsap.registerPlugin(ScrollTrigger, Flip);`.
- Use `ScrollTrigger.batch('.spec-card', { onEnter: (batch) => gsap.to(batch, { autoAlpha: 1, y: 0, stagger: 0.06, overwrite: true }), once: true })` for high-craft card reveals.
- Reserve `scrub: 0.6` and `pin: true` (`anticipatePin: 1`) for bounded architectural storytelling sections with explicit `min-height: 100svh` so pinning never shifts surrounding document flow (`CLS = 0.00`).

## 2. Flip Layout Transitions (`MOT-GSAP-FLIP-01`)
- When filtering nodes or toggling layout density:
  1. `const state = Flip.getState('.canon-grid > [data-node]');`
  2. Toggle `hidden` or `data-active` attributes synchronously.
  3. `Flip.from(state, { duration: 0.4, ease: 'power2.out', scale: true });`

## 3. `gsap.context()` Cleanup & `gsap.matchMedia()` Reduced Motion (`MOT-GSAP-CTX-01`)
- Always scope animations inside `const ctx = gsap.context(() => { ... }, rootNode)` and call `ctx.revert()` on teardown or Astro View Transition swap (`astro:before-swap`).
- Use `const mm = gsap.matchMedia(); mm.add('(prefers-reduced-motion: no-preference)', () => { ... });` so users with `prefers-reduced-motion: reduce` receive an instant settled layout (`opacity: 1`, `transform: none`) with zero scroll-jacking.

## 4. Compositor-Only 60fps & Strict CSP Compliance (`MOT-COMPOSITOR-01`, `MOT-CSP-SAFE-01`)
- Animate only `x`, `y`, `xPercent`, `yPercent`, `scale`, `rotation`, and `opacity` / `autoAlpha` (`60fps`, `CLS = 0.00`). Never tween `top`, `left`, `width`, `height`, or `margin`.
- Keep all scripts compliant with strict SHA-256 `script-src` and `style-src` (zero `'unsafe-inline'`, zero `eval`). When strict `style-src` hashes are enforced without `'unsafe-inline'`, use `element.animate()` (Web Animations API), CSS custom property classes, or SVG geometry attributes (`width`, `y`, `points`) so zero inline `style=""` attribute mutations are emitted.
"""


def main() -> None:
    os.makedirs(CHECKLISTS_DIR, exist_ok=True)
    files = [
        ("seo_aeo_geo_jsonld.json", json.dumps(SEO_JSON, ensure_ascii=False, indent=2) + "\n"),
        ("seo_aeo_geo_jsonld.md", SEO_MD),
        ("security_csp_headers.json", json.dumps(SEC_JSON, ensure_ascii=False, indent=2) + "\n"),
        ("security_csp_headers.md", SEC_MD),
        ("layout_wcag22_viewport.json", json.dumps(LAY_JSON, ensure_ascii=False, indent=2) + "\n"),
        ("layout_wcag22_viewport.md", LAY_MD),
        ("zimage_canon_prompts.json", json.dumps(ZIMAGE_JSON, ensure_ascii=False, indent=2) + "\n"),
        ("stack_architecture_patterns.json", json.dumps(STACK_JSON, ensure_ascii=False, indent=2) + "\n"),
        ("stack_architecture_patterns.md", STACK_MD),
        ("motion_gsap_choreography.json", json.dumps(MOTION_JSON, ensure_ascii=False, indent=2) + "\n"),
        ("motion_gsap_choreography.md", MOTION_MD),
    ]
    for fn, content in files:
        with open(os.path.join(CHECKLISTS_DIR, fn), "w", encoding="utf-8") as fh:
            fh.write(content)
    print(f"Built {len(files)} checklist artifacts in {CHECKLISTS_DIR}")


if __name__ == "__main__":
    main()
