# Canon 15_organic_biophilic_eco: Organic Biophilic / Low-Carbon Web

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/15_organic_biophilic_eco.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A calm, nature-led page that is also light to load: sage-mist and Nordic pine palette, smooth "pebble" cards (20px radius), pill buttons, natural daylight photos, and a hard page-weight budget of about 400KB.
- It works because the look (plants, stone, daylight) and the build (small, fast pages) tell the same story: care for people and resources. Visitors trust eco claims more when the site itself is lean.
- Good fits: sustainability and climate brands, clinics and wellness, botanical and garden businesses, green architecture, NGOs, local food.
- Weak fits: luxury fashion, gaming, heavy media showcases, crypto.
- Mood: calm, fresh, honest. Default polarity: light. Dark: deep forest with pale sage text.
- Avoid (canon): yellow beige + brass, SVG paper grain (that belongs to `16_artisan_craft_zine`), background video, WebGL, heavy blur.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 22px gutter, container 1312px, section padding 96px, card padding 28px (tokens).
- Typical landing order:
  - nav + one CTA ("Book a visit", "Get involved", "Shop plants");
  - hero: h1, short promise, one daylight photo;
  - 3 value cards (what you do, for whom, how);
  - impact band: 3–4 honest numbers with units and the year ("12 t CO₂e saved in 2026");
  - services or products grid;
  - process or "how we work" steps;
  - testimonials; FAQ; contact; footer with a page-weight / green-hosting note (optional).
- Keep sections few and light. Each image must earn its bytes.
- Mobile: one column; cards stack; impact numbers in a 2×2 grid.

<!-- section:hero -->
## Hero
- h1: Geologica 600, `clamp(2rem, 1.5rem + 2.22vw, 3.5rem)` (56px desktop, 42 tablet, 32 mobile), line-height 1.12, tracking −0.02em, measure about 22ch.
- Option 1, "Split daylight" (default): text in 6 columns, one photo in a 20px-radius frame in the other 6.
- Option 2, "Type on mist": h1 and CTA on the sage `bg`, a small row of 3 photos below. Pick it when the budget is tight or photos are weak.
- Option 3, "Full photo": one calm photo with text on a solid card over it. Pick it for botanical and hospitality.
- The hero image is the biggest file: AVIF, ≤ 120KB, `fetchpriority="high"`.

<!-- section:blocks -->
## Blocks
- Pebble card: 20px radius, 1px border in `border`, very soft shadow (tokens); hover darkens the border (canon).
- Pill button: `border-radius: 9999px`; primary filled pine, secondary outlined.
- Impact numbers: big Geologica numbers + Mulish label + source line ("Own data, 2026"). Never vague claims.
- Steps: numbered list with icons as inline SVG (one colour, `currentColor`, < 1KB each).
- Icons: inline SVG sprites, no icon font (an icon font loads hundreds of unused glyphs).
- Map or location: a static image linking to a map, not an embedded map iframe (iframes load MBs).

<!-- section:motion -->
## Motion
- Motion budget: low (dial 3). Tokens: ease `cubic-bezier(0.22,1,0.36,1)`, 300ms, stagger 45ms.
- Options (class A):
  - Hover: `translateY(-2px)` + border darken (canon).
  - Press: `scale(0.98)`.
  - Reveal: once only, opacity + 12px rise (canon). Use CSS `animation-timeline: view()` inside `@supports`; IntersectionObserver is the JS fallback; no scroll listeners.
- Library choice: CSS only (`css_scroll_driven`, catalog default). No JS motion library.
- Reduced motion (canon): 0ms, settled layout.

<!-- section:typography -->
## Typography
- Display: Geologica Variable 500–600.
- Body: Mulish Variable 16–18px, line-height 1.6, measure 60–70ch.
- Mono: Source Code Pro only for data labels and units, sparingly.
- Budget: load at most 2 variable fonts on the first screen (heading + body), latin + cyrillic subsets only; mono can load later.

<!-- section:color -->
## Color
- Light (default): sage-mist `bg` `oklch(0.966 0.010 152)`, `surface` `oklch(0.992 0.005 152)`, deep green text `oklch(0.195 0.024 158)`, pine `accent` `oklch(0.405 0.095 152)`, teal `accent_2` `oklch(0.460 0.068 205)`.
- Dark: forest `bg` `oklch(0.148 0.018 158)`, `surface` `oklch(0.196 0.022 158)`, pale text, light green `accent` `oklch(0.775 0.115 146)`.
- No yellow beige. Green is the only accent family plus one teal.
- A dark theme can save energy on OLED screens only; offer it via `prefers-color-scheme`, but do not claim big savings.

<!-- section:surfaces -->
## Surfaces
- Radius 20px cards, pill buttons and badges, 12px inputs; 1px solid borders (tokens).
- Shadows very soft (`0 10px 26px -10px rgba(15,48,28,0.08)`).
- Zero `backdrop-filter`, zero SVG noise filters, zero large background images (canon).

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Light base prompt (canon): "Natural overcast daylight editorial photograph of {subject} beside pale Nordic ash timber, cool river slate, celadon ceramic, and deep pine botanical leaves on pale sage mineral stone, 50mm lens, clean blank unmarked surfaces".
- Dark base prompt (canon): "Serene botanical nocturnal still life of {subject} resting on wet dark basalt and deep forest moss under soft cool moonlight, matte glass and pale sage foliage, 50mm lens, clean unmarked surfaces".
- Team portrait (canon): vertical 3:4, natural overcast light, organic linen knitwear, pale sage-mist or forest-slate wall.
- Fewer, smaller images: 4–6 per page; AVIF; each ≤ 120KB at its largest `srcset` width.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`. Presets: `css_scroll_native`, `classic_corporate`.
- Page budget (canon): ≤ 400KB total transfer on first load (HTML + CSS + fonts + images + JS). Rough split: fonts ≤ 120KB, hero ≤ 120KB, other images ≤ 120KB, CSS+JS ≤ 40KB.
- No third-party scripts by default (no chat widgets, trackers, embedded maps or videos). If analytics is needed, a small self-hosted, cookie-less one.
- Sustainability practices follow the W3C Web Sustainability Guidelines (a Group Note Draft): measurable budgets, optimised media and fonts, no waste.

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: eco claims must be specific and dated (avoid greenwashing); `Organization` with `sameAs` and certifications as text; `LocalBusiness` for clinics and shops.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Soft sage-on-mist palette lowers contrast for text and borders. Fix: body text deep green ≥ 4.5:1; card and input borders ≥ 3:1.
- Pill buttons and pebble cards look alike, so the action is unclear. Fix: primary button filled pine; cards never look like buttons unless they are links.
- Saving bytes by dropping useful content (no photos of the place, no map link, no prices). Fix: cut decoration, never key facts.
- Static map image as the only location info. Fix: address as text, a link to a map app, opening hours as text.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): geologica, mulish, source_code_pro.
- JS: none (CSS only).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- First-load page weight ≤ 400KB.
- No background video, WebGL, `backdrop-filter` or SVG noise filters.
- No third-party embeds by default.
- Eco numbers always have a unit, a year and a source line.
- Reduced motion: settled layout at once.
