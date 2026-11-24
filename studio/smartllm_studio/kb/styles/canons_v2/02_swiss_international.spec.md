# Canon 02_swiss_international: Swiss International / Neo-Grid

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/02_swiss_international.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- Background: Swiss (International Typographic) style, 1950s–60s. Its tools: a mathematical grid, asymmetric layouts, flush-left ragged-right text, sans-serif type and objective photography.
- It works because the grid makes order visible. The reader finds things fast, and the design looks neutral and trustworthy. The aim: inform "clearly, rapidly, and without misunderstanding".
- Good fits: corporate sites, architecture, engineering, consulting, technical specs, museums and schools, public institutions.
- Weak fits: playful consumer brands, emotional lifestyle products, anything that needs warmth or softness.
- Mood: rational, precise, calm, confident. Default polarity: light (white paper, black ink, one red).
- The modern web version ("neo-grid") keeps the grid visible as 1px lines and breaks it on purpose in one or two places.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 24px gutter, container 1344px, section padding 96px (canon tokens).
- Asymmetry is the base. The canon rule is a "flush-left 4/8 asymmetry": a 4-column label column and an 8-column content column. Why: a centred layout looks like a generic marketing page; asymmetry gives tension and direction.
- Typical page, top to bottom:
  - top bar: wordmark left, a few text links right, a 1px rule below;
  - hero (see Hero);
  - numbered sections: `01`, `02`, `03` indices in the 4-column label column, content in the 8 columns (canon rule "tabular 01/02/03 section indices");
  - a facts or specs table with ruled rows;
  - a project or case index: a list or a grid of equal modules;
  - contact block: plain address, email and phone in the grid;
  - footer: small text in 3–4 grid columns.
- Modules: split the page into fields of equal size. Images take 1, 2, 3 or 4 fields. "The fewer the differences in the size of the illustrations, the quieter the impression".
- Show the grid. Draw columns and rows as 1px black lines (canon: "exposed collapsed 1px black grid lines"). Keep empty columns empty.
- Vertical rhythm: choose one rhythm unit (for example 1.5rem) and make spacing and line-heights multiples of it.
- Mobile: 4 columns. The label column moves above its content. Lines stay as horizontal rules.

<!-- section:hero -->
## Hero
- Option 1, "Wordmark on the grid":
  - A very large wordmark or headline set flush left across the grid. A visible 12-column hairline grid sits behind it.
  - Pick it for a studio, architecture office or institution.
- Option 2, "Asymmetric statement + photo":
  - The h1 spans 8 columns, flush left. One objective photo (B) fills the other 4 columns or bleeds off the right edge. A small mono caption sits on the grid line.
  - Pick it for a corporate or engineering firm.
- Option 3, "Index hero":
  - A short h1, then a numbered list of 3–5 services or facts (01–05) directly in the hero.
  - Pick it for consulting and specs-heavy products.
- Avoid a centred marketing hero (canon rule). It removes the asymmetry that defines the style.
- For every option: one `h1`, real text (not an image), LCP image with `fetchpriority="high"`.

<!-- section:blocks -->
## Blocks
- Numbered section:
  - Content: index `01` (mono, tabular), title, then text in 8 columns.
  - Why: numbers give order without decoration.
- Facts table:
  - Content: label / value rows with 1px rules, tabular figures.
  - Good for specs, prices, key numbers.
- Project index:
  - Content: rows of year, name, type and place, like a catalogue. Hover tints the row border red.
  - Image: optional thumbnail in a fixed grid field (B).
- Image module:
  - Content: an objective photo in 1, 2, 3 or 4 grid fields with a mono caption under it.
- Quote:
  - Content: a short quote in bold sans, flush left, no quote marks graphic.
- CTA:
  - Content: one red button or a red text link with an arrow, placed on a grid line.
  - The accent red is the only strong colour on the page (canon: "vivid crimson CTA anchor").
- Team list:
  - Content: name, role, email in table rows.
  - Image: optional square portraits in equal fields, desaturated [assumption].

<!-- section:motion -->
## Motion
- Motion budget: very low (dial 3). The catalog marks this canon static (`reduced_motion_instant`). Swiss design gets energy from layout, not from movement.
- Options (all A, all small):
  - Hover: border colour changes to the accent, and a 1px underline slides in. No lift (canon). 180ms, ease `cubic-bezier(0.2,0,0,1)`.
  - Press: background contrast shift, no scale.
  - Scroll: stillness. Option: a 2px progress rule at the top of the page (canon).
  - Column hover tint on a hero grid: a column lightly tints and shows its number when hovered.
  - Video or motion posters (C): deferred.
- Avoid:
  - drop shadows and rounded pills, because they soften the hard grid;
  - parallax, because it moves things off the grid;
  - spring overshoot, because it looks playful.
- Reduced motion: colour and border swap instantly (0ms).

<!-- section:typography -->
## Typography
- Fonts (canon): Golos Text for headings, IBM Plex Sans for body, IBM Plex Mono for indices and data. All are grotesk-style sans with Cyrillic, close in spirit to Helvetica and Univers.
- Headlines: weight 700, tight tracking (−0.035em), line-height about 1.02, flush left. h1 68px on desktop.
- Body: flush left, ragged right, never justified. Justified text makes uneven gaps; ragged right keeps word spacing even.
- Use few sizes: about 3–4 in the whole site. Hierarchy comes from size, weight and position on the grid, not from colour.
- Numbers: `font-variant-numeric: tabular-nums` for indices, tables and prices.
- Avoid tight leading and squeezed letters for effect, because it hurts reading.

<!-- section:color -->
## Color
- White paper (`bg`), black ink (`text` and `border`), and one red (`accent`, crimson). This is the classic Swiss palette: "sparing use of colour".
- Use the red for the CTA, the active state and maybe one key word or shape. More red weakens it.
- `accent_2` (blue) is a backup for links in data or charts. Avoid using both red and blue as big fills.
- Surface grey: for table headers or a calm band.
- Dark version: carbon black background, white text, the same red.

<!-- section:surfaces -->
## Surfaces
- Radius: 0 everywhere (canon). Any radius above 0 breaks the style.
- Lines: 1px black for the grid and the tables, 2px for major breaks (canon: "edge-to-edge 1px/2px rules").
- Shadows: none. Glass and blur: none.
- Boxes are made by lines, not by fills. A cell is a space between lines.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Swiss design prefers photography over illustration. The photo should show the object, its form, material and colour, without effects.
- Light base prompt (canon): "Stark Swiss modernist architectural study of {subject} in concrete and brushed steel on crisp white alabaster plaster, razor-sharp geometric morning shadow, signal-red focal detail, vast negative space, 50mm lens, clean unmarked surfaces".
- Dark base prompt (canon): "High-contrast monochromatic Swiss architectural photograph of {subject} on matte carbon-black backdrop, crisp light planes, a single vermilion edge reflection, 50mm".
- Per block:
  - hero 4:5 or 3:4 for the 4-column side, 16:9 for full bleed;
  - image module 1:1 or 4:3, matching the grid field;
  - portraits 1:1, plain background.
- Keep images few and of few sizes, so the page stays quiet.
- No text inside images. Type is always HTML.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`. Landing preset: `classic_corporate`. The site is static and needs almost no JS.
- Options for each need:
  - Page grid: CSS Grid with 12 columns; place items with `grid-column: 5 / span 8` style spans.
  - Aligned nested content (cards, table rows): `grid-template-columns: subgrid` so inner items share the page columns.
  - Visible grid lines: borders on cells, or a background `repeating-linear-gradient` overlay set to the column width [assumption].
  - Vertical rhythm: a `--rhythm` token, with spacing and line-heights as multiples.
  - Progress rule: CSS `animation-timeline: scroll()` on a 2px bar, inside `@supports` [assumption].
- Avoid:
  - GSAP and Lenis, because the canon is static and they add weight;
  - CSS frameworks that add radius and shadow by default.

<!-- section:seo -->
## SEO / AEO / GEO
- The numbered sections map well to headings: index + `h2`. Answer engines like clear, labelled facts.
- Put facts tables in real `<table>` or `<dl>` markup, not divs. Engines and screen readers can read them.
- Organization JSON-LD with address and contact suits corporate and architecture sites.
- Grid lines are decoration. Mark overlay elements `aria-hidden="true"`.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Small grey captions and thin rules can fail contrast. Fix: captions ≥ 14px and ≥ 4.5:1; UI borders ≥ 3:1.
- Strong asymmetry (4/8) leaves a narrow column on tablets. Fix: switch to one column below ~900px.
- Numbered sections (01/02/03) are not navigation by themselves. Fix: keep a normal nav and real heading text.
- Red accent for links only by colour. Fix: underline links in body text.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): golos_text, ibm_plex_mono, ibm_plex_sans.
- JS: none (CSS only).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- No video or frame sequences (asset class C is deferred).
- Red on white and black on white must meet the canon contrast values.
- No text inside generated images.
- Static and offline: self-hosted fonts.
- Reading order follows the DOM. Do not reorder content with grid placement only.
