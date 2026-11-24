# Canon 12_quiet_luxury_minimal: Quiet Luxury / Architectural Atelier

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/12_quiet_luxury_minimal.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- Cold, quiet luxury: pale platinum and stone tones, twice the usual whitespace, large thin serif headlines (Cormorant Garamond 300–400), borderless cards separated only by tone, very slow fades. Few words, big images.
- It works because restraint signals confidence and price. Empty space and slow pacing tell the visitor nothing is being pushed.
- Good fits: luxury brands, architecture studios, ateliers, high-end real estate, hotels and hospitality, galleries.
- Weak fits: discount retail, SaaS with many features, dashboards, kids, anything urgent.
- Mood: calm, cold, exclusive. Default polarity: light (platinum). Dark: obsidian with silver.
- Canon rule: avoid the warm beige + brass cliché; this canon is cold (platinum, chrome, deep pine-slate).

<!-- section:structure -->
## Structure
- Grid: 12 columns, 32px gutter, container 1280px, section padding 120px, card padding 32px (tokens). Spacing is about 2× other canons.
- Typical landing order:
  - minimal nav: logo, 3–4 links, "Enquire";
  - full-width image hero with a short h1;
  - one short statement paragraph, centred or in columns 3–8;
  - project or collection grid with large images and short captions;
  - one detail section (materials, craft, location);
  - quiet contact/enquiry block; footer.
- Asymmetric placement works well: image in columns 1–7, text in 9–12 [assumption].
- Few sections. Each one has one idea.
- Mobile: same order, padding about 64–80px, images full width.

<!-- section:hero -->
## Hero
- h1: Cormorant Garamond 400 (never bold, canon), `clamp(2.375rem, 1.583rem + 3.52vw, 4.75rem)` (76px desktop, 52 tablet, 38 mobile), line-height 1.08, tracking −0.02em, measure about 18ch.
- Option 1, "Full-bleed still": one large B image, small h1 in a corner on a tonal band or over a calm area of the photo. Pick it as the default.
- Option 2, "Split atelier": image 7 columns, h1 and one line of text in the remaining space with lots of air. Pick it for architecture and ateliers.
- Option 3, "Type only": a big h1 on platinum with one thin line and a small caption; image starts below. Pick it when photos are weak.
- One quiet CTA as a text link with a thin underline ("Enquire", "View collection"), not a loud button.

<!-- section:blocks -->
## Blocks
- Card: no border, no shadow, no radius (tokens). Separate by `surface` tone and whitespace (canon).
- Labels: uppercase sans (Wix Madefor Text) with 0.14em tracking instead of monospace (canon).
- Project tile: large image (4:5 or 3:2), title in Cormorant 400, one line of meta.
- Statement: a short paragraph in Cormorant 300–400 at ≥ 24px.
- Details list: materials, size, location as a quiet `<dl>`.
- Enquiry form: few fields, labels above, thin bottom borders on inputs are fine if they pass 3:1 [assumption].

<!-- section:motion -->
## Motion
- Motion budget: low (dial 4) and slow. Tokens: ease `cubic-bezier(0.22,1,0.36,1)`, 500ms, stagger 60ms.
- Options (class A):
  - Hover: slow opacity to 0.78 + inner image `scale(1.02)`, no vertical jump (canon).
  - Press: opacity 0.85.
  - Scroll: 500ms opacity fade-in only (canon), via `animation-timeline: view()` or IntersectionObserver.
  - Page transitions: optional cross-fade with the View Transitions API.
- Library choice: native CSS (`css_scroll_driven`, catalog default); Lenis optional for a slow, smooth scroll on desktop.
- Avoid (canon): bouncy springs, visible card borders, monospace labels.
- Reduced motion (canon): 0ms, instant render.

<!-- section:typography -->
## Typography
- Display: Cormorant Garamond Variable, weights 300–400 only and never below 24px (canon). Thin serifs break up at small sizes.
- Body and labels: Wix Madefor Text Variable, 16–17px, line-height 1.6, measure 55–65ch.
- Tracking: display slightly tight (−0.02em); uppercase labels wide (0.14em).
- No bold headlines. Hierarchy comes from size and space.

<!-- section:color -->
## Color
- Light (default): platinum `bg` `oklch(0.972 0.004 242)`, near-white `surface`, near-black text, deep pine-slate `accent` `oklch(0.320 0.052 168)`, cool grey `accent_2`.
- Dark: obsidian `bg`, slightly lighter `surface`, pale text, silver `accent`.
- Accent only on links, the enquiry action and tiny details.
- Avoid (canon): warm cream/beige + brass.

<!-- section:surfaces -->
## Surfaces
- Radius 0, borders 0, shadows none (tokens).
- Separation strictly by tonal contrast and whitespace.
- Focus ring must still be clearly visible (the page has no borders, so the ring stands out — make it 2px, accent colour, with offset).

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Images carry this canon. Use few, large, very clean ones.
- Light base prompt (canon): "Cold-luxury architectural gallery still life of {subject} crafted in brushed stainless steel, cool pale limestone, and dark pine glass on a platinum plinth, soft north-window daylight, vast quiet negative space, 50mm lens, clean unmarked surfaces".
- Dark base prompt (canon): "Sculptural monolith study of {subject} in smoked obsidian glass, brushed titanium, and dark alpine slate against a matte obsidian gallery wall, razor-clean silver rim light, architectural stillness, 85mm lens, clean unmarked surfaces".
- Team portrait (canon): vertical 3:4, restrained low saturation, tailored charcoal wool, north-window light.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`, `nextjs`. Presets: `css_scroll_native`, `classic_corporate`.
- Almost no JS: CSS fades, optional Lenis, View Transitions for page changes.

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: short pages still need real descriptive text (materials, location, services) for search; good `alt` text on every project image; `LocalBusiness`/`Hotel`/`RealEstateListing` JSON-LD where it fits.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Thin serif and pale palette lower readability. Fix: Cormorant ≥ 24px only, body in the sans at ≥ 16px with ≥ 4.5:1.
- Borderless, minimal UI hides links and the enquiry action. Fix: underlined text links, a clearly labelled 'Enquire' action in nav and at the end.
- Huge whitespace pushes content below the fold on mobile. Fix: reduce section padding to 64–80px on mobile; first screen shows what it is.
- Slow 500ms fades feel laggy for interactions. Fix: slow fades only for content reveal; hover/press feedback under 200ms.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): cormorant_garamond, wix_madefor_text.
- JS (`vendor/js/<lib>/`): Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Cormorant only at weights 300–400 and ≥ 24px.
- Text contrast ≥ 4.5:1 even with the pale palette.
- Visible focus ring despite the borderless look.
- Reduced motion: instant render.
