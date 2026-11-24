# Canon 06_neo_brutalism: Neo-Brutalism / Raw Print

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/06_neo_brutalism.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- Neo-brutalism: flat bright fills, thick black outlines, hard offset shadows with no blur, square corners and oversized bold type. Every box looks like a printed sticker or stamp.
- Background: a 2020s web trend that mixes raw "brutalist" web pages with 90s print graphics. Brutalism is bare HTML; neo-brutalism is more colourful and orderly.
- It works because high contrast and thick strokes make every control obvious, and the look is memorable.
- Risk: everything shouts at once. The main action must win by colour or size, and the page needs empty space so the eye can rest.
- Good fits: startups, agencies, campaigns, communities, creative tools, events, indie products.
- Weak fits: banks, healthcare, luxury, long docs and dense dashboards (tiring on long tasks).
- Mood: direct, energetic, honest. Default polarity: light (cream paper). Dark version: near-black with acid-lime accent.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 24px gutter, container 1312px, section padding 84px, card padding 24px (tokens).
- All boxes are orthogonal: 0° rotation, 0px radius. Rotated "sticker" cards belong to canon 20, not here.
- Typical landing order:
  - top bar with a framed logo and one filled CTA;
  - hero (big uppercase statement + CTA + framed image);
  - marquee band with a Pause button (optional);
  - 3–6 feature cards in a grid;
  - a "how it works" row of numbered steps;
  - pricing cards (one highlighted with the yellow fill);
  - FAQ as framed accordions;
  - footer as one big framed block.
- Leave clear space between framed boxes (at least the gutter). Boxes that touch turn into a noisy pattern [assumption].
- Mobile: one column. Keep 3px borders. Reduce the offset shadow to 4px so cards do not overflow the screen edge [assumption].

<!-- section:hero -->
## Hero
- h1: Unbounded 800, uppercase, `clamp(1.5rem, 0.875rem + 2.78vw, 3.375rem)` (54px desktop, 40 tablet, 24 mobile), line-height 1.06, tracking −0.025em, measure about 16ch.
- Unbounded is a very wide face. Long words (Russian especially) can overflow on 360px screens. Use `overflow-wrap: anywhere` or `hyphens: auto` with `lang` set, and test the longest word [assumption].
- Option 1, "Poster block": the h1 on the cream background, one highlighted word with the yellow fill behind black text, a filled CTA with offset shadow. Pick it as the default.
- Option 2, "Split card": text left, a framed image card right (3px border, 6px offset shadow). Pick it when a product shot exists.
- Option 3, "Sticker grid": the h1 above a row of 3–4 small framed cards with key facts. Pick it for a campaign or event.
- Keep one primary CTA in the hero. Two equal loud buttons compete.

<!-- section:blocks -->
## Blocks
- Card: surface fill, `border: 3px solid ink`, `box-shadow: 6px 6px 0 ink`, radius 0.
- Button: same frame and shadow. Hover lifts it, press "stamps" it into its shadow (see Motion).
- Highlight: `accent_2` volt yellow is used only as a fill behind dark text (labels, a word in the headline, a featured price card). Never as text colour on cream.
- Tag / badge: small framed rectangle, mono font, uppercase.
- Pricing card: framed card; the featured one gets the yellow fill.
- FAQ: framed `<details>`/`<summary>` blocks. They work without JS and are keyboard accessible.
- Form: inputs with 3px borders, radius 0, labels above, visible errors in text (not colour only).
- Marquee band: full-width strip with a top and bottom border, mono or display text, Pause button.

<!-- section:motion -->
## Motion
- Motion budget: medium (dial 7), but short and mechanical. Tokens: ease `cubic-bezier(0.2,0,0,1)`, 110ms, stagger 20ms.
- Options (class A, CSS first):
  - Hover "lift": `transform: translate(-2px,-2px)` and the shadow grows to `8px 8px 0`.
  - Press "stamp": `translate(4px,4px)` and the shadow goes to 0. This shows the box is a control.
  - Optional 4px scroll progress bar at the top (CSS `animation-timeline: scroll()` inside `@supports`).
  - Marquee with a visible Pause button.
  - Entry reveals: a short slide or clip of cards on view (`animation-timeline: view()`), 20ms stagger.
- Animate only `transform` and `box-shadow` on small elements; for long lists prefer `transform` only, because shadow changes repaint [assumption].
- Libraries: CSS is enough for most of this. Use `animejs` or `motion` (catalog) only for staggered sequences.
- Avoid (canon): tilted or rotated cards, blurred shadows, rounded pills.
- Reduced motion (canon): 0ms transforms; hover becomes an instant colour inversion.

<!-- section:typography -->
## Typography
- Display: Unbounded Variable (`wght` 200–900, Latin + Cyrillic). Use 700–900 for headlines only.
- Body: Golos Text Variable (good Cyrillic). Body 16–18px, line-height 1.5, measure 60–70ch.
- Mono: Martian Mono Variable (`wdth` 75–112.5, `wght` 100–800) for tags, prices, labels and numbers.
- Uppercase only for short display lines and tags. Body text stays sentence case.
- Avoid using Unbounded for paragraphs. Its wide letters make long text slow to read.

<!-- section:color -->
## Color
- Light (default): cream `bg`, white `surface`, near-black ink for text and borders, magenta `accent` for links and the main CTA, volt yellow `accent_2` as highlight fill.
- Dark: near-black `bg`, dark `surface`, cream text, acid-lime `accent`; the offset shadow becomes lime.
- Contrast rules:
  - yellow and lime are fills behind dark text. As text on cream or white they fail contrast;
  - white text on bright yellow or lime also fails. Use ink text on them;
  - check every text/fill pair: 4.5:1 for normal text, 3:1 for large text and UI borders (WCAG 1.4.3, 1.4.11).
- Keep the palette to ink + 2 accents. More colours turn the page into noise.

<!-- section:surfaces -->
## Surfaces
- Radius 0 on cards, buttons, inputs and badges (tokens).
- Borders: 3px solid ink.
- Shadow: hard offset `6px 6px 0` ink (light) or lime (dark). Blur is always 0.
- Focus (canon): `outline: 3px solid` + `outline-offset: 4px`, so the ring sits outside the 3px border and stays visible. Use `:focus-visible`.
- Windows High Contrast / `forced-colors: active`: box-shadows are removed, borders stay. Because the style uses real borders, it survives; do not rely on the shadow alone to show a state.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Look: direct flash, hard shadows, flat saturated colour, no soft gradients.
- Light base prompt (canon): "Raw direct-flash studio still life of poured concrete cubes and solid magenta acrylic slabs on warm cream newsprint surface, crisp sharp hard shadows, 35mm lens, completely blank unmarked surfaces".
- Dark base prompt (canon): "Direct-flash architectural concrete monolith lit by saturated acid-lime and magenta studio gel lights against pitch-black shadow, sharp edges, 35mm lens, completely unmarked surfaces".
- Team portraits: vertical 3:4, punchy direct flash, plain backdrop.
- Every image sits in a framed card (3px border, offset shadow). Never full-bleed soft photos.
- Simple icons and arrows as inline SVG with thick strokes (2–3px), so they match the borders.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`, `vite_ts`, `sveltekit`.
- Landing presets: `css_scroll_native` (lightest, fits the CSS-first motion), `kinetic_showreel` (type-led launch), `gsap_scrollytelling` (scroll story, built with anime.js or Motion; GSAP is optional and license-restricted).
- Motion: CSS first. Catalog motions: `animejs` (default), `motion`, `css_scroll_driven`.
- Design tokens as CSS custom properties: `--border: 3px solid var(--ink)`, `--shadow: 6px 6px 0 var(--ink)`, `--shadow-hover: 8px 8px 0 var(--ink)`. One change restyles all boxes.
- No component library needed. Plain HTML elements (`button`, `details`, `input`) with these tokens cover the style.

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only (general rules are in the baseline):
  - keep headline words as real text, not images;
  - put the facts (price, dates, features) in plain text inside cards, not only in the marquee.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Everything is loud, so the main action gets lost. Fix: one filled primary CTA per section, others outlined.
- Yellow/lime fills with white text fail contrast. Fix: ink text on bright fills.
- Offset shadows plus press movement can shift layout. Fix: animate `transform` only; reserve shadow space.
- Thick borders on dense cards cramp text on mobile. Fix: reduce shadow to 4px and keep 16px+ padding.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): golos_text, martian_mono, unbounded.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); anime.js 4.5.0 (`anime.esm.min.js`); Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Text contrast at least 4.5:1; yellow/lime only behind dark text.
- Marquee or any loop over 5 seconds has a visible Pause button.
- Reduced motion: no transforms.
