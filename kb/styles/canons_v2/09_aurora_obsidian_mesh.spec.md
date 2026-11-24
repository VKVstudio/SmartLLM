# Canon 09_aurora_obsidian_mesh: Aurora Mesh & Luminous Depth

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/09_aurora_obsidian_mesh.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A dark obsidian page with a soft, slowly drifting aurora (violet and teal light) far behind the content. On top: fully opaque matte cards with one sharp teal or violet accent. No glass.
- The difference from canon 08: here cards are 100% opaque and have no `backdrop-filter`. The light lives only in the background layer.
- It works because the glow gives depth and a "platform" feel, while opaque cards keep text contrast stable everywhere.
- Good fits: AI platforms, cloud, data and analytics, developer platforms, SaaS.
- Weak fits: warm human brands, print/editorial, kids, very light minimal brands.
- Mood: deep, luminous, controlled. Default polarity: dark. Light version: pearl with pastel aura.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 22px gutter, container 1312px, section padding 92px, card padding 28px (tokens).
- Layers: `body::before` aura (fixed, `z-index: -1`, opacity ≤ 0.24, canon) → opaque cards → controls.
- Typical landing order:
  - nav on solid bg;
  - hero with h1, sub-line, CTA and a product UI shot (B) in an opaque frame;
  - logos row;
  - 3–6 feature cards;
  - a metrics band (big numbers);
  - an integration or architecture diagram (inline SVG);
  - pricing cards;
  - CTA and footer.
- Let the aura show mostly in the gaps between cards and around the hero. Heavy glow under body text lowers contrast.
- Mobile: same order, aura at lower opacity, no drift animation on low-power devices (optional).

<!-- section:hero -->
## Hero
- h1: Unbounded 600, `clamp(1.625rem, 1.167rem + 2.04vw, 3rem)` (48px desktop, 36 tablet, 26 mobile), line-height 1.12, tracking −0.02em, measure about 20ch.
- Canon rule: h1 floor is 26px at 360px. Unbounded is wide, so long words need `overflow-wrap: anywhere` or shorter wording.
- Option 1, "Aurora horizon": the aura brightest behind the hero, h1 + CTA centred or left, product shot below. Pick it as the default.
- Option 2, "Split + UI": text left, an opaque product UI card right with a thin accent rim. Pick it for analytics and dashboards.
- Option 3, "Canvas aurora": a small procedural canvas or three.js shader (class A) instead of CSS gradients, desktop only, paused off screen. Pick it when the brand wants a "living" hero.

<!-- section:blocks -->
## Blocks
- Card: opaque `surface`, radius 18px, 1px border, soft deep shadow (tokens). No blur.
- Accent rim: on hover the border changes to `var(--accent)` (canon).
- Metric: big Unbounded number, small Geologica label, optional sparkline as inline SVG.
- Code or API sample: Fira Code on `surface`, radius 10px.
- Diagram: inline SVG with thin lines and accent nodes.
- Buttons: radius 12px; primary filled with accent, secondary outlined.
- Badges: pill (999px), low-contrast fill.

<!-- section:motion -->
## Motion
- Motion budget: medium (dial 6). Tokens: ease `cubic-bezier(0.22,1,0.36,1)`, 280ms, stagger 40ms.
- Options (class A):
  - Aura drift: animate only `transform: translate3d()` (and maybe `scale`) of the `body::before` layer, about 16s loop (canon). Transform runs on the compositor and does not repaint.
  - Hover: card rim lights to the accent + `translateY(-2px)` (canon). Press: `scale(0.98)` 120ms.
  - Scroll: optional rise with `animation-timeline: view()` inside `@supports`.
  - Number count-up on view for metrics (Motion or anime.js), final value present in the HTML.
- Library choice: `motion` (catalog default); Lenis optional. GSAP is optional and license-restricted (not vendored).
- Avoid (canon): animating gradient colour stops directly (repaints the whole layer every frame), translucent glass cards (canon 08), rainbow gradient text on every h2.
- Reduced motion (canon): aura frozen at frame 0; rim highlight instant.

<!-- section:typography -->
## Typography
- Display: Unbounded Variable (`wght` 200–900) at 600 for headlines. Body: Geologica Variable. Mono: Fira Code (code, metrics labels). All cover Cyrillic.
- Body 16–17px, line-height 1.6 on dark, measure 60–70ch.
- Gradient text only on one hero word at most. It is hard to read and fails contrast checks easily.

<!-- section:color -->
## Color
- Dark (default): obsidian `bg` `oklch(0.115 0.020 278)`, opaque `surface`, light text, violet `accent` `oklch(0.740 0.140 288)`; teal as second accent.
- Light: pearl `bg`, white `surface`, deep violet text, violet `accent`, teal `accent_2`.
- Aura recipe: 2–3 `radial-gradient()` blobs (violet, teal, a little blue) on `body::before`, opacity ≤ 0.24, large blur via big gradient radius (not `filter: blur`) [assumption].
- One accent per element. The glow is the colour; cards stay neutral.

<!-- section:surfaces -->
## Surfaces
- Radius: card 18px, button 12px, input 10px, badge pill (tokens).
- Borders 1px, subtle; accent on hover/focus.
- Shadows: soft and deep (tokens), with a faint inner top line on dark.
- No `backdrop-filter` anywhere (canon). This keeps it fast and separates it from canon 08.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Dark base prompt (canon): "Sculpted dark smoked obsidian glass ribbons framing {subject} and catching subtle refracted aurora violet and glacier cyan light beams in a dark studio void, 85mm lens, clean blank surfaces".
- Light base prompt (canon): "Translucent iridescent pearl and opalescent silk ribbons around {subject} refracting pastel orchid and soft aqua dawn light on white ceramic, 85mm studio macro, clean blank surfaces".
- Team portrait (canon): vertical 3:4, violet-cyan rim light, obsidian-charcoal or pearl-white backdrop, 85mm.
- Product UI shots are better as real HTML/SVG mockups than as images: sharp, small and translatable [assumption].

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `nextjs`, `astro`, `sveltekit`, `vite_ts`. Presets: `bento_interactive`, `css_scroll_native`, `gsap_scrollytelling` (built with Motion).
- The aura is pure CSS (gradients + transform). A canvas or three.js version is optional and must follow the baseline rules (DPR cap, pause off screen, static frame for reduced motion).

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: put metrics and integrations in real text and lists, not only in images or canvas; the aura layer is `aria-hidden`.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Glow behind text lowers contrast in spots. Fix: opaque cards for all text; aura ≤ 0.24 opacity.
- Constant background motion distracts and drains battery. Fix: slow drift, pause when tab hidden, freeze under reduced motion.
- Dark-only UI with low-contrast secondary text. Fix: secondary text ≥ 4.5:1 for body, ≥ 3:1 only for large or non-essential text.
- Wide Unbounded headings overflow at 360px. Fix: 26px floor and `overflow-wrap`.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): fira_code, geologica, unbounded.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Cards are 100% opaque; no blur on cards.
- Aura opacity ≤ 0.24; animate it with transform only.
- Text contrast ≥ 4.5:1; gradient text only on large display words.
- Reduced motion: aura frozen.
