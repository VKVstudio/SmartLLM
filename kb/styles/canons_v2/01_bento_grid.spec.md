# Canon 01_bento_grid: Bento Grid

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/01_bento_grid.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A bento grid is one closed frame of rounded tiles in different sizes. Each tile holds one idea.
- Popularised by Apple keynote recaps (2022), then Linear, Vercel and Supabase feature sections.
- It works because size shows importance. The eye goes to the biggest tile first, so you need fewer headings and less colour to rank content.
- Good fits: SaaS and devtools features, hardware spec sheets, dashboards, mixed-media portfolios, "everything on one screen" summaries.
- Weak fits: long stories, editorial reading, step-by-step content. Bento summarises; it does not narrate.
- Mood: orderly, crisp, proud of the product. Default polarity: light. Dark works well for devtools.
- It is bento only if: ≥ 2 tile sizes, one gap and one radius, heights in one row unit (flat bottom edge), the biggest tile holds the best proof, and the set is closed. Three equal cards is a plain card grid.

<!-- section:structure -->
## Structure
- Typical landing page, top to bottom:
  - header pill;
  - hero (see Hero);
  - logo or proof strip;
  - feature bento with 5–7 tiles (the main section);
  - split section: text 5 columns + one visual tile 7 columns;
  - metrics bento with 3–5 tiles and big numbers;
  - testimonial or case tiles;
  - pricing as 2–3 tiles, with one plan larger;
  - FAQ as plain text, not tiles;
  - CTA tile across 12 columns;
  - footer.
- Rhythm: put a calm text or split section between two bento sections. Many bentos in a row feel like a dashboard, not a story [assumption].
- One large anchor tile (7 columns) per screen is the canon rule. Switch the anchor side between sections (left, then right) to keep the page alive.
- Grid values (canon tokens): 12 columns desktop, 8 tablet, 4 mobile; container 1312px; gap `clamp(14px,2vw,22px)`; section padding `clamp(48px,5vw,88px)`.
- Tile sizes (12 cols): anchor 7×2, companion 5×1, wide 5–6×1, square 3–4×1, tall 4–5×2, full 12×1; rows `minmax(180px, auto)` [assumption].
- Example template for a 5-tile feature bento (`grid-template-areas`):
```
"anchor anchor anchor anchor anchor anchor anchor side side side side side"
"anchor anchor anchor anchor anchor anchor anchor sq1  sq1  sq2  sq2  sq2"
"wide   wide   wide   wide   wide   wide   tall   tall tall tall tall tall"
```
- Content shrinks with the tile: anchor = visual + headline + sentence; 5×1 = headline + sentence; square = one number or icon + 2 words; tall = 3–4 proof points.
- If text does not fit a tile, cut the text. A smaller font breaks the type system.
- Mobile: one column. Tiles follow source order, with the anchor first. Rows size to their content.

<!-- section:hero -->
## Hero
- Option 1, "Bento hero": anchor tile (7×2) holds the h1 (≤ 22 chars per line), lede and two CTAs; right side: a product image tile (B) and two stat tiles. Pick it with 2–3 strong numbers.
- Option 2, "Headline then bento": centred h1, lede and CTAs; a feature bento 48–64px below. Pick it when one message matters most.
- Option 3, "Product render anchor": a product still (B) fills the anchor; text in the 5-column side; two spec tiles below. Pick it for hardware.

<!-- section:blocks -->
## Blocks
- Feature anchor (7×2): a visual, an h3 and one line. Image: a UI mock built in HTML, or a product still (B).
- Feature side (5×1): an h3, one line and a small visual. Image: a detail crop (B) or an SVG icon (A).
- Metric (3–4×1): one big number and a 2-word label. No image. Use the accent colour on the number.
- Integrations (5×1): a cluster of SVG logos.
- Quote (5×1 or 5×2): a quote, name and role. Image: a 3:4 portrait shown as a 40px circle (B).
- Spec list (tall 5×2): 3–4 stacked specs.
- Pricing: 4×2 per plan, with the featured plan 5×2. Plan name, price, 4 bullets, a CTA.
- CTA (12×1): an h2 and one button.
- Tile anatomy: `article.tile` > optional `figure.tile__media` > `h3` > `p` > optional link.
- Tile padding: 26px desktop, 20px tablet, 18px mobile (tokens). Radius 24px. 1px hairline border.
- Media sits flush to the tile edge, inside `overflow: hidden`.
- Accent colour: only on the main metric or the CTA (canon rule). Different colours per tile break the calm, uniform frame.

<!-- section:motion -->
## Motion
- Motion budget: moderate (dial 5). The tiles should feel precise, not playful.
- Options:
  - Scroll reveal (A, CSS): inside `@supports (animation-timeline: view())`, use `animation-timeline: view()` with `animation-range: entry 0% entry 60%`, from `opacity:0; translateY(16px)`. Zero JS.
  - Fallback reveal (A, JS): an IntersectionObserver adds `.in` once. Transition 220ms with ease `cubic-bezier(.22,1,.36,1)`, 40ms stagger by tile order (tokens).
  - Hover lift (A): `translateY(-2px)` with a bigger shadow (light) or a brighter border (dark), 220ms.
  - Press (A): `scale(.985)`, 110ms.
  - Cursor spotlight (A, best on dark):
    - One `pointermove` listener on the grid sets `--mx` and `--my` on each tile.
    - A `::before` ring uses `radial-gradient(360px circle at var(--mx) var(--my), accent 45%, transparent)` and is masked to 1px with `mask-composite: exclude`.
    - It fades in on hover only. Why: one listener and CSS variables are cheap, and the browser repaints the gradient natively.
  - Tile micro-demo (A): a small CSS/SVG loop in one tile (typing caret, toggle, counter). At most one per section, so it stays a highlight.
  - Number count-up (A): once on entry, up to 800ms. The final value is in the HTML.
- Avoid: elastic bounces (clash with the precise grid), marquees and 3D tilt (canon), scroll-jacking. Lenis adds little here [assumption].
- Reduced motion: no spotlight, instant border change.

<!-- section:typography -->
## Typography
- Fonts (canon tokens):
  - headings: Manrope Variable 700, tracking −0.03em (h1) / −0.025em (h2);
  - body: Inter Variable 400, line-height 1.6;
  - labels and specs: JetBrains Mono.
- Tiles use three type sizes only. Fewer sizes keep the many tiles looking like one system:
  - tile title: h3, 21px, weight 600;
  - support line: 16px, up to 2 lines;
  - big metric: `clamp(2.5rem, 5cqi, 4.5rem)`, weight 700, `font-variant-numeric: tabular-nums`.
- Eyebrow labels: 12px, weight 600, uppercase, tracking 0.06em, muted colour.
- Inside tiles, use container units (`cqi`) so type scales with the tile, not the window.

<!-- section:color -->
## Color
- Layers (light): page `bg` (cool off-white) < tile `surface` (near white) < `surface_elevated` (hover or featured).
- Layers (dark): graphite page, tiles one step lighter, inner hairline `inset 0 1px 0` at 7% white.
- `text` for titles, `muted` for support lines.
- `accent` (cobalt): one metric and the primary CTA per section.
- `accent_2` (green): status or positive values only.
- Option: one "inverted" tile per section (dark fill, light text) to make a focal point [assumption].

<!-- section:surfaces -->
## Surfaces
- Radius: card 24px, button and input 12px, badge 999px (tokens).
- Media inside a padded tile: radius = 24px minus padding, so the corners stay concentric [assumption].
- Matte surfaces: no blur, no glass, no gradient fills. A matte surface keeps attention on the content.
- Shadow (light): a soft two-layer shadow (tokens). Dark: a 1px ring instead of a shadow, because shadows disappear on dark backgrounds.
- Nest cards at most 2 levels deep (canon rule).

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Light base prompt (canon): "Clean modular industrial product flat-lay of {subject} arranged in disciplined compartments on honed cool off-white limestone, crisp north-window softbox shadows, single restrained cobalt anodized detail, 50mm, blank unmarked surfaces".
- Dark base prompt (canon): "Anodized dark graphite studio flat-lay of {subject} on matte obsidian slate, cool cobalt rim highlight, precision bevels, 50mm".
- Ratios: anchor 16:9 or 4:3 (15% safe margin), side 4:3 detail, square 1:1 one object, quote 3:4.
- One light setup and one background material site-wide, so tiles read as one product.
- Do not put text, logos or UI in images: Z-Image cannot draw reliable text. Build UI mocks in HTML/CSS [assumption].

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`, `nextjs`, `sveltekit`, `vite_ts`. Landing preset: `bento_interactive`.
- Layout: CSS Grid `grid-template-areas`, one template per section (readable as ASCII art).
- Responsive: `container-type: inline-size` on the section; 2 columns below 900px, 1 below 560px (reacts to its own width).
- `grid-auto-flow: dense` only for independent tiles (it can reorder visually).
- Avoid JS masonry and absolute positioning (CSS Grid does it), and a heavy SPA for a marketing bento.

<!-- section:seo -->
## SEO / AEO / GEO
- Mark up each tile as an `article` with a real `h3`, inside a `section` with an `h2`. Answer engines can then pull "feature → claim" pairs.
- Metric numbers are real HTML text with unit and context ("48 MP main camera"), not images.
- Option: list the features in `SoftwareApplication` or `Product` JSON-LD as `featureList` [assumption].

<!-- section:ux_check -->
## UX check (risks of this style only)
- Tile order: with `grid-auto-flow: dense` the visual order can differ from DOM and Tab order. Fix: place important tiles explicitly; DOM order = priority.
- Whole-tile links: make the tile one `<a>` or put one link inside and stretch its hit area; never nested links or a clickable `<div>`.
- Equal-looking tiles hide the main action. Fix: one anchor tile with the primary CTA, clearly bigger.
- Cursor spotlight and hover effects do nothing on touch. Fix: all content and links visible without hover.
- Text inside small tiles gets cramped on mobile. Fix: one column below ~640px, tiles grow to fit content, no fixed heights.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): inter, jetbrains_mono, manrope.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- No video or frame sequences (asset class C is deferred).
- Visual order must not break reading or focus order. No `dense` on steps, pricing or other ordered content.
- No text inside generated images.
- Every motion has a reduced-motion version.
- Static and offline: self-hosted fonts, no CDN scripts.
