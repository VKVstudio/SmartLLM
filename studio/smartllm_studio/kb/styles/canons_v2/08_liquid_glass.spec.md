# Canon 08_liquid_glass: Liquid Glass / Frosted Depth

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/08_liquid_glass.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- Frosted glass panels float over a soft coloured "aura" background. Panels blur what is behind them, have a thin bright top rim and soft depth shadows. Default is dark (obsidian/cobalt).
- It works because layered translucent planes show depth and hierarchy without heavy borders, and the look feels modern and "spatial".
- Main risk: text on glass loses contrast. Canon rule: dark frosted panels keep alpha ≥ 0.72, and every panel has a solid fallback.
- Good fits: AI products, spatial/AR, SaaS, hardware, fintech apps, dashboards with few layers.
- Weak fits: long reading, print-like brands, low-end devices (blur is expensive), strict accessibility contexts without fallbacks.
- Mood: calm, premium, futuristic. Default polarity: dark. A light pearl version exists.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 22px gutter, container 1312px, section padding 88px, card padding 28px (tokens).
- Depth: at most 3 planes (canon): background aura → glass panels → small controls or popovers on top. More planes turn into blur soup.
- The aura lives on `body::before` with `position: fixed; inset: 0; z-index: -1` (canon). Do not use `background-attachment: fixed` (janks on iOS, canon).
- Typical landing order:
  - floating glass nav bar (sticky, small);
  - hero with a large glass card or product image;
  - 3–6 feature panels;
  - a glass "spec" or pricing panel;
  - testimonial or logo row on glass;
  - CTA panel;
  - footer on solid surface.
- Put glass only on cards and nav. Large full-width glass areas cost GPU time and look muddy [assumption].
- Mobile: blur 12px instead of 20px (canon), fewer panels, a solid nav.

<!-- section:hero -->
## Hero
- h1: Wix Madefor Display 700, `clamp(2rem, 1.5rem + 2.22vw, 3.5rem)` (56px desktop, 42 tablet, 32 mobile), line-height 1.08, tracking −0.028em, measure about 22ch.
- Option 1, "Glass card hero": the h1 and CTA inside one big glass panel over the aura. Pick it as the default.
- Option 2, "Product behind glass": a B image of the product with glass panels around it showing 2–3 key specs. Pick it for hardware and devices.
- Option 3, "Floating UI": 2–3 small glass UI cards (chat bubble, chart, toggle) layered at different depths next to the h1. Pick it for AI and SaaS.
- Do not promise real liquid refraction from CSS. True refraction needs WebGL (three.js, class A); CSS gives blur and tint only (canon).

<!-- section:blocks -->
## Blocks
- Glass panel recipe:
  - `background: var(--surface)` with alpha 0.72 (dark) or 0.78 (light);
  - `backdrop-filter: blur(20px) saturate(1.5)` (12px on mobile); unprefixed works in Chrome 76+, Firefox 103+, Safari 18+; add `-webkit-backdrop-filter` for older Safari;
  - `border: 1px solid var(--border)` (translucent);
  - top rim: `::before` with a 1px light line, or `box-shadow: inset 0 1px 0 oklch(1 0 0 / 0.28)`;
  - depth shadow from tokens (soft, large, low alpha).
- Radii: cards 22px, buttons 14px, inputs 12px, badges pill (tokens).
- Nav bar: glass pill or bar, sticky.
- Popover / dialog: native `<dialog>` or `popover` with a glass panel.
- Stat panel: a big number (Wix Madefor Display) with a mono label.
- Chips and badges: pill shape, translucent fill.

<!-- section:motion -->
## Motion
- Motion budget: medium (dial 6). Tokens: ease `cubic-bezier(0.22,1,0.36,1)`, 280ms, stagger 45ms.
- Options (class A):
  - Hover: `translateY(-2px)` and the top rim gets brighter (canon).
  - Press: `scale(0.975)` for 130ms.
  - Scroll: panels rise `scale(0.97)→1` plus opacity with `animation-timeline: view()` inside `@supports`.
  - Aura: a slow `transform: translate3d()` drift of the `body::before` layer (transform only).
  - Cursor light: a radial highlight that follows the pointer via CSS variables on fine pointers only.
- Library choice: `motion` (catalog default) for sequences, CSS for the rest, Lenis optional. GSAP is optional and license-restricted (not vendored).
- Avoid (canon): animating the blur radius of `backdrop-filter` (very expensive); `background-attachment: fixed`; alpha below 0.72 behind dark body text.
- Reduced motion (canon): `opacity: 1; transform: none`, glass stays static.

<!-- section:typography -->
## Typography
- Display: Wix Madefor Display Variable. Body: Onest Variable (both cover Cyrillic). Mono: JetBrains Mono for numbers and code.
- Body 16–17px, line-height 1.55, weight 400–450. Slightly heavier body text helps on blurred backgrounds [assumption].
- Never put thin weights (≤300) on glass.

<!-- section:color -->
## Color
- Dark (default): deep cobalt `bg`, glass `surface` `oklch(0.230 0.030 258 / 0.72)`, near-white text, cyan `accent`.
- Light: pale blue-grey `bg`, glass `surface` `oklch(0.990 0.003 240 / 0.78)`, navy text, blue `accent`, violet `accent_2`.
- The aura uses 2–3 soft radial gradients of the accent hues at low opacity. Keep it calm behind text.
- Contrast: test text against the worst point of the aura behind the panel, not against the average.

<!-- section:surfaces -->
## Surfaces
- Glass rules as above. Triple fallback (canon):
  - `@supports not (backdrop-filter: blur(1px))` → opaque `surface` without alpha;
  - `@media (prefers-reduced-transparency: reduce)` → opaque panels (works in Chromium only, Safari and Firefox ignore it);
  - a `[data-solid-ui]` attribute on `<html>` set by a user toggle → opaque panels in every browser. This closes the Safari gap (canon).
- `forced-colors: active`: backgrounds become system colours, so keep the 1px border; it stays visible.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Dark base prompt (canon): "Macro optical studio still life of {subject} refracted behind thick beveled frosted sapphire glass panels, soft cyan-silver caustic reflections over deep midnight cobalt slate, 85mm macro lens, completely blank unmarked glass surfaces".
- Light base prompt (canon): "Sunlit translucent frosted acrylic slabs and clear optical prisms framing {subject} on cool pearl alabaster stone, crisp cerulean caustic highlights, 85mm lens, clean blank glass surfaces".
- Team portrait (canon): vertical 3:4, cool rim light, cobalt-slate or pearl-grey backdrop, 85mm.
- Optional real refraction: a small three.js scene (class A, vendored) with a transmission material over a still image, desktop only, paused off screen.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `nextjs`, `astro`, `sveltekit`, `vite_ts`. Presets: `bento_interactive`, `css_scroll_native`, `gsap_scrollytelling` (built with Motion).
- The glass look is pure CSS: `backdrop-filter`, alpha colours in `oklch(... / a)`, `::before` rims, `body::before` aura.
- Performance: blur is costly on big areas and on scroll. Keep blurred panels small, avoid stacking blurred elements, and test on a mid-range phone [assumption].

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: keep all panel text as real HTML (not baked into images); decorative aura layers get `aria-hidden="true"`.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Text on blur loses contrast over busy backgrounds. Fix: alpha ≥ 0.72, test at the worst background point, solid fallback toggle.
- Blur makes scrolling slow on low-end phones. Fix: smaller blur on mobile, few blurred elements, no blur animation.
- Glass buttons look like plain panels. Fix: clear fill or border on buttons and visible focus rings.
- Stacked translucent layers confuse hierarchy. Fix: max 3 planes; modals use a strong scrim (40–60%).

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): jetbrains_mono, onest, wix_madefor_display.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Dark glass alpha ≥ 0.72 behind body text; text contrast ≥ 4.5:1 at the worst background point.
- Every glass panel has the three opaque fallbacks.
- Never animate blur radius; no `background-attachment: fixed`.
- Reduced motion: static glass.
