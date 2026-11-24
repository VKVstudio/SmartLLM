# Canon 16_artisan_craft_zine: Artisan Craft / Tactile Zine

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/16_artisan_craft_zine.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A hand-made zine look: cool cotton-slate paper, terracotta and Prussian indigo like two risograph inks, Vollkorn serif headlines, 2px ink borders with a 4px indigo offset shadow, small hand-written notes in the margins.
- It works because visible craft (ink, paper, stamps, notes) signals small-batch, human work. It feels local and honest, not corporate.
- Good fits: coffee roasters, bakeries, ceramics and craft makers, small design studios, bookshops, local markets, workshops.
- Weak fits: banks, enterprise SaaS, medical, luxury.
- Mood: warm, crafted, friendly. Default polarity: light (paper). Dark: indigo night paper with terracotta.
- Avoid (canon): glass blur, endless wiggle loops, warm cream `#f5f1ea` + brass, blurry neon shadows.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 24px gutter, container 1312px, section padding 96px, card padding 26px (tokens).
- Typical landing order:
  - nav (logo as a stamp mark) + CTA ("Order beans", "Book a class", "Visit us");
  - hero: big Vollkorn h1, one-line story, product or workshop photo;
  - "made by hand" story block with a margin note;
  - product or menu grid (cards with price);
  - process strip: 3–5 steps (source, roast, pack…);
  - workshop/classes or events list with dates;
  - visit block: address, hours, map link; footer.
- Use asymmetry: a photo slightly offset over a coloured block, a note in the margin column [assumption].
- Mobile: one column; margin notes move inline below their paragraph.

<!-- section:hero -->
## Hero
- h1: Vollkorn 700, `clamp(2.25rem, 1.708rem + 2.41vw, 3.875rem)` (62px desktop, 46 tablet, 36 mobile), line-height 1.1, tracking −0.02em, measure about 20ch.
- Option 1, "Cover page" (default): h1 left, photo right in a 2px ink frame with offset shadow, a Shantell Sans note ("roasted Tuesday!") near it.
- Option 2, "Two-ink poster": h1 on a terracotta block, photo duotone-styled with CSS (indigo + paper) using `mix-blend-mode: multiply` on a coloured layer. Pick it for events and design studios.
- Option 3, "Product hero": one product photo centred with price and an "Add/Order" CTA. Pick it for shops.

<!-- section:blocks -->
## Blocks
- Card: 2px solid ink border, 6px radius, `4px 4px 0` indigo offset shadow (tokens). Optional dashed inner rule like a zine page.
- Margin note: Shantell Sans 15–17px, slight rotation (−2°…2°), accent colour; short, only extras (canon: sparingly). Never put prices or key facts only in a note.
- Stamp/badge: 3px radius, uppercase PT Mono, 2px border ("Small batch", "New").
- Menu/price list: `<dl>` or table with dotted leaders; prices `tabular-nums`.
- Events list: date in PT Mono, title in Vollkorn, a "Book" link per row.

<!-- section:motion -->
## Motion
- Motion budget: medium-low (dial 5). Tokens: ease `cubic-bezier(0.22,1,0.36,1)`, 260ms, stagger 55ms.
- Options (class A):
  - Hover "letterpress": `translate(-2px,-2px)` and shadow grows to `6px 6px 0` (canon).
  - Press: `translate(3px,3px)` and shadow `1px 1px 0` — the card is "pressed into paper".
  - Scroll: "print stamp" — opacity + 12px rise once, via `animation-timeline: view()` in `@supports`.
- Library choice: CSS only (`css_scroll_driven`, catalog default); Lenis optional on desktop.
- Reduced motion (canon): no transforms; shadows stay static.

<!-- section:typography -->
## Typography
- Display: Vollkorn Variable 600–700; italic for small accents.
- Body: Source Sans 3 Variable 16–18px, line-height 1.6, measure 60–68ch.
- Notes: Shantell Sans, only for short annotations.
- Labels and prices: PT Mono 13–14px.

<!-- section:color -->
## Color
- Light (default): cotton-slate `bg` `oklch(0.970 0.005 244)`, near-white `surface`, indigo-black text `oklch(0.195 0.028 256)`, terracotta `accent` `oklch(0.495 0.155 34)`, Prussian indigo `accent_2` `oklch(0.400 0.115 258)`, ink `border` `oklch(0.280 0.032 256)`.
- Dark: indigo `bg` `oklch(0.155 0.024 258)`, pale text, light terracotta `accent` `oklch(0.725 0.148 38)`.
- Two "inks" only (terracotta + indigo) plus paper and ink black, like a two-colour riso print.

<!-- section:surfaces -->
## Surfaces
- Radius 6px cards, 4px buttons and inputs, 3px badges; 2px solid borders (tokens).
- Shadow: `4px 4px 0 oklch(0.280 0.032 256 / 0.85)` light, `4px 4px 0 oklch(0.520 0.040 250 / 0.70)` dark.
- Paper grain (optional): one tiny static noise image (≤ 8KB) at low opacity; or none. No live SVG filter on large areas.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Light base prompt (canon): "Tactile risograph printshop and workshop composition of {subject} with unglazed terracotta stoneware, Prussian indigo ink tools, and cool slate-tinted cotton paper under morning window raking light, 50mm lens, clean blank paper".
- Dark base prompt (canon): "Artisan printmaking studio photograph of {subject} on a deep indigo-slate workbench with warm kiln terracotta ceramics, chalk-blue linen, and woodblock tools under warm bench lamp, 50mm lens, clean unmarked surfaces".
- Team portrait (canon): vertical 3:4 workshop portrait, indigo canvas apron, window light.
- Show hands, tools and real products; close-ups sell craft.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`. Presets: `css_scroll_native`, `classic_corporate`.
- Small shops: link to an existing shop/checkout or a simple order form; do not build a cart in this canon.

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: `LocalBusiness` subtype (`CafeOrCoffeeShop`, `Bakery`, `Store`) with address, hours, `geo`; `Product` with `offers` for items; `Event` for classes with dates.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Hand-written font is hard to read. Fix: Shantell Sans only for short notes ≥ 15px; all body and prices in Source Sans 3.
- Rotated notes and stamps overlap content on small screens. Fix: on mobile no rotation, notes inline.
- Offset shadows make cards look clickable when they are not. Fix: only interactive cards get hover/press; static cards keep a flat shadow.
- Terracotta text on paper can be weak at small sizes. Fix: terracotta for large text, buttons and shapes; small text in ink.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): pt_mono, shantell_sans, source_sans_3, vollkorn.
- JS (`vendor/js/<lib>/`): Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Two inks only: terracotta + indigo, plus paper and ink.
- Hand-written notes only for extras, never key facts.
- No glass blur, no endless wiggle loops.
- Reduced motion: no transforms.
