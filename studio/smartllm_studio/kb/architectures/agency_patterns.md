# Premium Landing Page Engineering Patterns (Late 2026)

Target Core Web Vitals (CrUX p75): **LCP <= 2.5s**, **INP <= 200ms**, **CLS <= 0.1 (goal 0.00)**.

## 1. Canonical Folder Topology
- `tokens/` (`tokens.css`): 3-tier OKLCH token hierarchy (`primitive` -> `semantic` -> `component`) + fluid `clamp()` typography & spacing; cascade locked via `@layer reset, tokens, base, layout, components, utilities;`.
- `layouts/`: Document shell (`<head>`, canonical, JSON-LD `@graph`, OpenGraph, skip-link, `<header>`, `<main>`, `<footer>`).
- `sections/`: Pure server/static sections (`0` client hydration by default).
- `islands/` (or leaf `'use client'`): Minimal interactive widgets (mobile nav drawer, calculator, filmstrip prev/next, form feedback) loaded lazily (`client:visible` / `client:idle`).
- `content/` / `data/`: Zod-validated structured copy, pricing tiers, testimonials, FAQ, i18n bundles.
- `server/` (when dynamic): DAL (`import 'server-only'`), Zod v4 schemas, CSRF/rate-limit guard, SSRF-safe outbound HTTP client.

## 2. Semantic HTML & Native UI Landmarks
- Mandatory landmarks: `<header>`, `<nav aria-label="...">`, `<main id="main-content">`, `<section aria-labelledby="...">`, `<article>`, `<footer>`, skip link, exactly **one `<h1>`** per page, monotonic heading hierarchy (`h1 -> h2 -> h3`).
- Prefer native primitives over JS widget bloat: `<dialog>` + `commandfor`/`command`, `popover` + CSS Anchor Positioning, `<details><summary>` accordions.

## 3. Zero-CLS & Fast-LCP Asset Pipeline
- **Hero LCP Image:** Serve AVIF/WebP (`<picture>` PNG fallback), explicit integer `width` + `height` + CSS `aspect-ratio`, **`fetchpriority="high"`**, `loading="eager" decoding="sync"`. **CRITICAL:** Never lazy-load LCP image and **NEVER apply `opacity: 0` scroll-reveal to hero H1 or hero image** (browsers exclude `opacity: 0` nodes from LCP).
- **Below-Fold Media:** Explicit `width` + `height`, `loading="lazy" decoding="async"`, `content-visibility: auto; contain-intrinsic-size: auto 600px;` on below-fold sections (never on `#hero`).
- **Fonts:** Self-host `.woff2` subsets (`cyrillic` + `latin`), `font-display: swap`, paired with `@font-face` fallback metric overrides (`size-adjust`, `ascent-override`, `descent-override`) to eliminate layout shift on swap.

## 4. INP-Safe Motion & State Physics (`<= 200ms`)
- **Hard Rule:** NEVER store scroll Y, pointer X/Y, or animation ticks in React `useState` / Svelte `$state` (triggers main-thread re-render storms).
- **Approved Patterns:** CSS Scroll-Driven Animations (`scroll()`/`view()`, Baseline Oct 2026), compositor-only CSS transforms (`transform`, `opacity`, `clip-path`), Web Animations API (`el.animate()`), or rAF updating DOM refs / `el.style.setProperty('--p', v)` directly (CSP-safe without `style="..."` attributes!).
- **Long Tasks:** Feature-detect `scheduler?.yield` with `setTimeout(0)` fallback (Safari lacks `scheduler.yield()`).
- **Reduced Motion:** Wrap all non-essential motion in `@media (prefers-reduced-motion: no-preference)`.

## 5. Progressive Enhancement Baseline
With JS disabled, every generated landing/corporate site MUST still render complete semantic copy, pricing tables, navigation links, `<details>` FAQ answers, properly sized images, and functional `<form method="POST">` submission.
