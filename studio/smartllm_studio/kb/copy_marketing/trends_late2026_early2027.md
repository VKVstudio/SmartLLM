# Late November 2026 -> Early 2027 Web Design & Anti-Slop Canon

## 1. Verified Landscape (Nov 2026)
- **The "Anti-Slop" Cultural Correction:** Both First-Wave AI Slop (*dark purple-to-cyan neon gradients, Inter everywhere, 3 equal cards*) AND Second-Wave Safe Editorial Slop (*unmotivated `#f5f1ea` cream/beige + `#b08947` brass on every SaaS*) trigger immediate template fatigue. Authentic 2026–2027 sites show **intentional human judgment**: asymmetric grids, domain-grounded `oklch()` palettes, dramatic scale contrast, and tactile craft.
- **Native CSS Motion Baseline (Zero JS Bloat):**
  - **CSS Scroll-Driven Animations (`scroll()`, `view()`, `animation-range`):** **Baseline Newly Available (Oct 2026)** across Chrome 115+, **Safari 26+**, and **Firefox 159+**. Use inside `@supports (animation-timeline: view())` and `@media (prefers-reduced-motion: no-preference)`.
  - **View Transitions API:** Same-document `startViewTransition()` is Baseline; cross-document MPA `@view-transition { navigation: auto; }` works in Chrome 126+ & Safari 18.2+ (Firefox Nightly ~161 flag) — emit purely as progressive enhancement.
- **Dual-Audience Architecture (Human UX + AI Agent AX):** Raw static/SSR HTML5 landmarks, native `<button>`/`<a>`/`<details>`, complete JSON-LD `@graph`, and `/llms.txt` let non-JS AI search bots (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`) cite exact facts cleanly without `<div>`-soup token waste.

## 2. 12-Point Anti-Flat-Design Checklist (Hardened for WCAG 2.2 & CWV)
Pass `>= 10 / 12` deterministic checks on every build:
1. **Break 3-Equal-Card Monotony:** Never stack two consecutive identical 3-column equal card grids. Alternate asymmetric Bento (`7/5`), horizontal hairline rows, numbered pillars, and full-bleed bands.
2. **Ban Both Slop Palettes:** Reject unmotivated AI purple-cyan glow AND generic cream/beige+brass defaults. Lock 1 dominant surface, `>= 7:1` ink, and 1 accent (`<= 10%` viewport area).
3. **Dramatic Scale & Distinct Cyrillic Pairings:** Pair characterful display + body (`H1/body >= 3.0` desktop where canon permits, `text-wrap: balance`, `tabular-nums` on numbers). Never default to lone Inter or non-Cyrillic fonts.
4. **Structural Hairline Architecture:** Expose `1px` collapsed grid rules, `2px`/`4px` top bars, or tabular `01 / 02 / 03` indices rather than floating identical white boxes on gray.
5. **Tactile Surface Micro-Contrast (Mobile-Safe):** Differentiate bands via `--bg` / `--surface` / `--surface-elevated` steps within the locked polarity, `inset 0 1px 0` dark top rims, or lightweight static grain (`<= 0.04` opacity — skip expensive fullscreen `feTurbulence` compositing on mobile or low-carbon `15_organic`). NEVER use `body { background-attachment: fixed; }` (iOS jank) or `< 0.72` low-alpha dark glass without `@media (prefers-reduced-transparency: reduce)` + `[data-solid-ui]` fallback.
6. **Zero Generic Icon-in-Circle Cards:** Replace abstract icon circles with concrete metric readouts, comparison tables, or authentic Z-Image material/product frames.
7. **Layout-Locked Visuals:** Match `<img>` integer `width`/`height` to real PNG IHDR dimensions; enforce `3:4` headroom on `team` (`object-position: 50% 15%`); never hide LCP hero media at `opacity: 0`.
8. **Interactive Proof Surface (`>= 1` per landing):** Comparison `<table>`, `<details>` objection accordion, ROI/cost calculator, or state switcher.
9. **Native CSS Motion + MPA View Transitions:** Progressive-enhance reveals with `animation-timeline: view()` + `@view-transition { navigation: auto; }`, gated behind `prefers-reduced-motion: no-preference`.
10. **Scannable Frosting & Micro-Type:** Max `62–68ch` line length, `text-wrap: pretty`, bolding reserved for real anchors (never `- **Bold:**` bullet walls).
11. **Dual-Audience Clean Semantic DOM:** Shallow `<main>` -> `<section>` landmarks, single `<h1>`, complete JSON-LD `@graph` matching visible pricing/contacts/FAQ 1:1.
12. **Tactile Accessible Interaction States:** Crisp `:hover`, `>= 2px` outside `:focus-visible` outline (`>= 3:1`, never obscured behind `3px` brutalist borders), `:active` press feedback, `CLS == 0.00`, zero external CDN assets.
