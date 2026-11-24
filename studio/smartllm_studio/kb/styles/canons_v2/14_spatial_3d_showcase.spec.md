# Canon 14_spatial_3d_showcase: Spatial Hardware / 3D Stage

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/14_spatial_3d_showcase.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A dark "stage" for one product: pitch-dark cyclorama, one hero object lit with an ice-cyan rim light, crisp mono coordinate labels, panels that tilt slightly in 3D. Optional live WebGL model, always with a static image first.
- It works because a single lit object on a dark stage focuses attention like a product launch keynote; labels and specs make it feel engineered.
- Good fits: hardware, consumer electronics, automotive, AR/VR, industrial products, 3D/CGI studios.
- Weak fits: text-heavy services, editorial, local businesses, accessibility-first public services.
- Mood: precise, futuristic, premium. Default polarity: dark. Light: cool ceramic stage with cobalt accents.
- Avoid (canon): auto-spinning WebGL that drains the battery, fake 3D drawn with divs, purple cyberpunk glow.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 22px gutter, container 1312px, section padding 96px, card padding 26px (tokens).
- Typical landing order:
  - nav + one CTA ("Pre-order", "Configure", "Book a demo");
  - stage hero: product image (or 3D) centred, h1 above or to the side;
  - callout section: the product with 3–6 numbered labels pointing to parts;
  - feature panels (3–4) with one image each;
  - spec table (dimensions, weight, battery, materials);
  - configurator or colour picker (optional);
  - comparison or FAQ; final CTA; footer.
- One 3D canvas per page at most (canon). Everything else is images and CSS.
- Mobile: the stage is a static image; labels become a numbered list under it.

<!-- section:hero -->
## Hero
- h1: Tektur 700, `clamp(1.875rem, 1.292rem + 2.59vw, 3.625rem)` (58px desktop, 42 tablet, 30 mobile), line-height 1.08, tracking −0.02em, measure about 20ch.
- Option 1, "Static stage" (default): one B render of the product on the dark cyclorama, sharp rim light. This image is the LCP and must load first (canon).
- Option 2, "Live stage": same image first; after load and only on capable devices, swap in a three.js canvas the user can rotate. Pick it when a real GLB model exists.
- Option 3, "Split spec": image in 7 columns, h1 + 3 key specs + CTA in 5. Pick it for B2B hardware.
- Key specs under the h1 in Martian Mono (e.g. `48 MP · 1.2 kg · 12 h`).

<!-- section:blocks -->
## Blocks
- Stage panel: dark surface, 16px radius, inset 1px top highlight + deep shadow (tokens), subtle coordinate grid background (CSS `linear-gradient` lines at 4–6% opacity).
- Callouts: numbered dots placed with `position:absolute` in % over the image; each has a matching list item with text (labels are never only on the image).
- Feature panel: image, short title, 1–2 lines, one key number.
- Spec table: real `<table>`, mono numbers with `tabular-nums`, units in a lighter colour.
- Colour/variant picker: native radio buttons styled as swatches, each with a text label; swapping changes the image.

<!-- section:motion -->
## Motion
- Motion budget: medium-high (dial 7). Tokens: ease `cubic-bezier(0.16,1,0.3,1)`, 340ms, stagger 45ms.
- Options (class A):
  - Hover on panels (fine pointer only): `perspective(1200px) rotateX(2deg) rotateY(-2deg) translateY(-3px)` (canon).
  - Press: `scale(0.97)`.
  - Scroll: stage panel goes `scale(0.97)` → 1 with opacity via `animation-timeline: view()`.
  - Light spot: a CSS custom property (`--x`, `--y`) updated in `requestAnimationFrame` from the pointer moves a radial highlight; no framework state per frame (canon).
  - 3D model: rotates only when the user drags (OrbitControls) or a slow turn while in view; stops when idle.
- Library choice: three.js for the one canvas (catalog default `three`); Motion for panel reveals; Lenis optional.
- 3D loading pattern:
  - load three.js with dynamic `import()` after the page is interactive and only if WebGL2 works (`canvas.getContext('webgl2')`);
  - load the model as compressed GLB (≤ 2–3 MB) with `GLTFLoader`;
  - keep the static image until the first frame renders, then cross-fade;
  - on error or low memory keep the image.
- Follow the canvas rules in `_engineering_baseline.md` (DPR cap, pause off-screen and in hidden tabs).
- Reduced motion (canon): no tilt, no orbit, no auto-turn; show the static image.

<!-- section:typography -->
## Typography
- Display: Tektur Variable 600–700 for h1/h2 and big numbers.
- Body: Geologica Variable 16–17px, line-height 1.55, measure 60–70ch.
- Mono: Martian Mono for labels, coordinates, specs (12–14px, uppercase, tracking 0.04em).

<!-- section:color -->
## Color
- Dark (default): stage `bg` `oklch(0.128 0.014 255)`, `surface` `oklch(0.176 0.017 255)`, text `oklch(0.952 0.008 240)`, ice-cyan `accent` `oklch(0.780 0.125 212)`.
- Light: ceramic `bg` `oklch(0.965 0.006 246)`, near-black text, cobalt `accent` `oklch(0.475 0.108 244)`, amber `accent_2` for small indicators.
- Accent for rim light, CTA, callout dots and focus. Amber only for tiny status details.

<!-- section:surfaces -->
## Surfaces
- Radius 16px cards, 10px buttons and inputs, 6px badges; 1px borders (tokens).
- Dark shadow: `inset 0 1px 0 rgba(165,220,245,0.22), 0 24px 48px -12px rgba(0,4,12,0.72)`.
- No backdrop blur on large areas; the stage is solid dark.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Dark base prompt (canon): "Studio HDRI physically-based industrial hardware sculpture of {subject} suspended inside a pitch-dark titanium cyclorama, razor-sharp glacial cyan specular rim light and warm amber indicator detail, 50mm lens, clean unmarked hardware".
- Light base prompt (canon): "Wind-tunnel studio HDRI product render of {subject} in bead-blasted aluminum and optical sapphire glass floating above cool ceramic cyclorama, crisp cobalt reflections, 50mm technical lens, clean unmarked surfaces".
- Team portrait (canon): vertical 3:4, cool specular rim highlight, dark charcoal-slate or light grey backdrop, 85mm.
- Render the same product from 3–5 angles for feature panels; keep the background identical so the page feels like one stage.
- A Z-Image still is not a 3D model. Live 3D needs a real GLB from the client; without it use Option 1.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `vite_ts`, `nextjs`, `sveltekit`, `astro`. Presets: `gsap_scrollytelling` (use Motion/CSS), `bento_interactive`.
- In `html5_esm` use an import map: `"three": "assets/vendor/three/three.module.js"`, `"three/addons/": "assets/vendor/three/addons/"`.
- Studio gap: the engine copies only `three.module.js` today; `three.core.js` and `addons/` must be copied too (see `_vendor_manifest.md`).

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: `Product` JSON-LD with real specs (`additionalProperty`), offers and images; spec table as HTML text, not inside the canvas.

<!-- section:ux_check -->
## UX check (risks of this style only)
- 3D canvas can trap scroll on touch (drag rotates instead of scrolling). Fix: `touch-action: pan-y` on the canvas, rotate only with a horizontal drag or a 'Rotate' toggle.
- Canvas is invisible to keyboard and screen readers. Fix: rotate buttons (Left/Right/Reset) with labels; text description and spec list next to it.
- Heavy models freeze low-end phones and waste data. Fix: static image on mobile and Save-Data; load 3D on demand ('View in 3D' button).
- Tilt hover makes text harder to read and does nothing on touch. Fix: max 2° tilt, text panels stay flat.
- Dark stage with small mono labels fails contrast. Fix: labels ≥ 12px and ≥ 4.5:1.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): geologica, martian_mono, tektur.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); Lenis 1.3.27 (`lenis.mjs`); three.js 0.187.0 (`three.module.js + three.core.js + addons/`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Static image is the LCP; WebGL never blocks first paint.
- Max one 3D canvas; no auto-spin when idle or off screen.
- Every callout label also exists as text in a list.
- Reduced motion: no tilt, no orbit, static image.
