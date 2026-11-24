# Canon 07_avant_garde_poster: Avant-Garde Constructivist / Poster

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/07_avant_garde_poster.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A poster-like page: tall condensed uppercase headlines, flat geometric blocks, strong diagonals, a strict palette of ink, paper and one scarlet. Columns are open on the sides and marked by a 4px top bar. No shadows.
- Background: based on 1920s Constructivist posters (diagonal axes, type as a building block, red/black/paper).
- It works because few elements carry a lot of energy: one headline, one image, one action. The limited palette reads as intent.
- Good fits: culture, festivals, exhibitions, architecture, media, theatre, manifestos and campaigns.
- Weak fits: dashboards, docs, healthcare, finance, long forms. Diagonals break reading order on long content.
- Mood: bold, urgent, constructed. Default polarity: light (kraft-cream paper). Dark version: soot black with vermilion.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 20px gutter, container 1344px, section padding 88px, card padding 24px (tokens).
- Columns are "open-sided": no box, only a 4px solid top bar (`border-top: 4px solid`) in ink or scarlet. This separates it from canon 06 (boxes with shadows).
- Typical landing order:
  - top bar: logo, 3–5 links, one CTA;
  - poster hero (see Hero);
  - programme or projects in 3–4 open-sided columns;
  - one inverted manifesto band (dark bg, light text) — the only place the grid is broken;
  - a timeline with square nodes;
  - venue/contact facts;
  - footer.
- Canon rule: break the grid at most once, with the inverted manifesto/CTA band.
- Diagonals: use them for headlines, colour wedges and section edges only. Body text, labels and forms stay horizontal.
- Mobile: one column. Reduce diagonal angles or remove them below 600px, so long words do not overflow [assumption].

<!-- section:hero -->
## Hero
- h1: Alumni Sans 800, uppercase, `clamp(2.75rem, 1.583rem + 5.19vw, 6.25rem)` (100px desktop, 68 tablet, 44 mobile), line-height 0.9, tracking −0.015em, measure about 16ch.
- Option 1, "Diagonal poster": the h1 rotated about −6° to −12° (`transform: rotate()`), a scarlet wedge or bar behind it, one image in a hard rectangle. Pick it for festivals and campaigns.
- Option 2, "Tower headline": the h1 stacked in 2–4 short lines, flush left, upright, with a scarlet circle or bar as the only shape. Pick it for architecture and institutions (calmer).
- Option 3, "Photomontage": a cut-out B image (hard edges, duotone) overlapping big type and one geometric block. Pick it for exhibitions and media.
- Rotating text with `transform` keeps it real text, selectable and readable by screen readers. DOM order must still match reading order.
- Keep one CTA. The poster has one message.

<!-- section:blocks -->
## Blocks
- Open-sided column: 4px top bar, title in Alumni Sans, body in IBM Plex Sans, no box, no shadow.
- Manifesto band: inverted colours, a huge statement, maybe one diagonal edge made with `clip-path: polygon()`.
- Timeline: a vertical or horizontal 4px line with square nodes (small squares, not circles), dates in PT Mono.
- Programme list: rows with date (mono), title (display), place; hover inverts the row.
- Geometric shapes: circles, bars, triangles and wedges as inline SVG or CSS (`clip-path`, `border-radius: 50%` for circles only). They are structure, not decoration.
- Image block: hard-edged rectangle, duotone or high contrast, no rounded corners.
- Number/fact block: a big number in the display face with a short label.

<!-- section:motion -->
## Motion
- Motion budget: medium (dial 6). Tokens: ease `cubic-bezier(0.7,0,0.2,1)`, 180ms, stagger 25ms.
- Options (class A):
  - Hover: instant ink inversion (surface↔text) on rows and buttons (canon).
  - Press: no bounce, instant accent swap (canon).
  - Scroll: crisp `clip-path: polygon()` wipe on headlines and images with `animation-timeline: view()` inside `@supports` (canon).
  - Optional: a slow marquee of programme dates with a Pause button.
  - Optional: shapes slide in along their diagonal on view (transform only).
- Library choice: CSS first. `animejs` (catalog default) or `motion` for staggered timelines. GSAP is optional and license-restricted (not vendored).
- Avoid (canon): drop shadows, rounded corners, blur and glass, tilting paragraphs.
- Reduced motion (canon): `clip-path: none; opacity: 1`, static "litho plates".

<!-- section:typography -->
## Typography
- Display: Alumni Sans Variable (`wght` 100–900, roman and italic, Latin + Cyrillic). A condensed face, so long headlines still fit.
- Body: IBM Plex Sans Variable, 16–18px, line-height 1.5, measure 60–70ch.
- Mono: PT Mono for dates, numbers, labels.
- Display weights 700–900 for headlines; 300–400 Alumni for big quiet numbers.
- Avoid thin romantic serifs (they belong to canons 03 and 12).
- Uppercase only for display and labels. Add small letter-spacing (0.04–0.08em) to uppercase labels for legibility.

<!-- section:color -->
## Color
- Light (default): kraft-cream `bg`, warmer `surface`, near-black ink, scarlet `accent` `oklch(0.505 0.195 26)`, ochre `accent_2` for secondary marks.
- Dark: soot-black `bg`, cream text, vermilion `accent` `oklch(0.640 0.200 26)`.
- Roles: ink = structure (bars, text); scarlet = the one action and key shapes; paper = active empty space.
- Check scarlet text on cream for 4.5:1 at small sizes; use scarlet mainly for large type, bars and fills [assumption].

<!-- section:surfaces -->
## Surfaces
- Radius 0 everywhere (tokens).
- Borders: 4px solid, used as top bars, timeline lines and dividers, rarely as full boxes.
- Shadows: none in both themes (canon). This is what separates it from neo-brutalism.
- Texture: optional light paper grain in a B image, never as a CSS noise filter over text [assumption].

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Light base prompt (canon): "Constructivist photomontage-inspired architectural photography on warm archival kraft-cream stone, stark soot-black diagonal steel truss shadows, one geometric scarlet industrial cylinder, 35mm film grain, completely unmarked surfaces".
- Dark base prompt (canon): "Avant-garde darkroom architectural composition on matte soot-black surface, sharp warm ivory spotlight cutting across concrete geometry, one vivid vermilion plane, 35mm film grain, clean blank surfaces".
- Team portrait (canon): vertical 3:4, high-contrast duotone, angular key light, kraft-grey or soot-black backdrop, 50mm.
- Duotone in code: a CSS `filter: grayscale(1) contrast(1.2)` plus a `mix-blend-mode: multiply` scarlet layer gives a print-like look without new images [assumption].
- No text inside generated images. All words are HTML.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`, `vite_ts`. Landing presets: `kinetic_showreel`, `gsap_scrollytelling` (built with anime.js or Motion), `css_scroll_native`.
- Most of this style is plain CSS: `transform: rotate()`, `clip-path: polygon()`, `border-top`, `mix-blend-mode`, scroll-driven animations.
- Tokens as CSS custom properties: `--bar: 4px solid var(--ink)`, `--angle: -8deg` (one angle for the whole site keeps diagonals consistent).
- Shapes as inline SVG, so they scale and stay crisp.

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only (general rules are in the baseline):
  - rotated headlines stay real `<h1>`/`<h2>` text;
  - event facts (dates, venue, prices) in plain horizontal text, plus `Event` JSON-LD for each event.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Rotated headlines and diagonals break reading order and can overflow. Fix: rotate display text only, keep DOM order, reduce angles on mobile.
- Condensed uppercase type at small sizes is hard to read. Fix: Alumni Sans only for display; labels in the body face.
- One inverted band can be mistaken for the footer. Fix: content and nav continue after it clearly.
- Scarlet small text on cream may fail contrast. Fix: scarlet for large type and shapes; small text in ink.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): alumni_sans, ibm_plex_sans, pt_mono.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); anime.js 4.5.0 (`anime.esm.min.js`); Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Body text, labels and form fields are never rotated.
- DOM order matches reading order, whatever the visual diagonal.
- No shadows, no blur, no rounded corners.
- Text contrast at least 4.5:1 (3:1 for large text).
- Reduced motion: no clip-path animation, content fully visible.
