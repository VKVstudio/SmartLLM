# Canon 11_soft_clay_playful: Tactile Clay & Playful Product

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/11_soft_clay_playful.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- Friendly "clay" UI: big rounded cards (28px), pill buttons, soft outer shadows plus inner highlights that make shapes look like soft plastic or clay. Warm coral and mint accents on a pale sky background.
- It works because round, soft, slightly bouncy shapes feel safe and fun, which lowers the barrier for beginners, kids and families.
- Risk: soft shadows alone give weak edges. Controls still need a crisp border (canon: "crisp border_control on clay inputs").
- Good fits: edtech, education, wellness, consumer apps, family products, onboarding flows.
- Weak fits: banks, legal, luxury, B2B infrastructure, serious news.
- Mood: warm, playful, encouraging. Default polarity: light. Dark: twilight indigo.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 24px gutter, container 1312px, section padding 96px, card padding 28px (tokens).
- Typical landing order:
  - nav with a pill CTA;
  - hero with h1, short promise, pill CTA and a clay illustration (B);
  - 3 benefit cards with icons;
  - "how it works" in 3–4 numbered steps;
  - app screenshot or interactive demo;
  - testimonials (parents, teachers, users) on clay cards;
  - pricing; FAQ; CTA; footer.
- Generous spacing: clay shapes need air so shadows do not overlap.
- Mobile: one column; keep 28px radius on cards (the brand), buttons full width.

<!-- section:hero -->
## Hero
- h1: Rubik 700, `clamp(2.125rem, 1.625rem + 2.22vw, 3.625rem)` (58px desktop, 44 tablet, 34 mobile), line-height 1.08, tracking −0.025em, measure about 20ch.
- Option 1, "Clay scene": h1 left, an isometric clay scene (B) right. Pick it as the default.
- Option 2, "App in hand": a phone mockup with the real app UI in HTML/CSS, floating clay badges around it (achievements, streak). Pick it for consumer apps.
- Option 3, "Big friendly card": the hero is one large clay card with h1, CTA and 3 small stat pills. Pick it for wellness or simple services.

<!-- section:blocks -->
## Blocks
- Clay card: radius 28px, `surface` fill, 1px soft border, triple shadow from tokens (outer lift + top inner highlight + bottom inner compression).
- Pill button: radius 9999px, accent fill, same clay shadows, bold label.
- Input: radius 18px, crisp 1px border, inset highlight; label above.
- Icon badge: round clay chip with a simple icon (inline SVG, 2px rounded strokes).
- Progress / milestone: a pill progress bar and small celebration states, short and honest (canon: no dark-pattern streaks).
- Step card: big number in a coral circle, title, one sentence.
- Testimonial: avatar circle, quote, name.

<!-- section:motion -->
## Motion
- Motion budget: high (dial 8) but gentle. Tokens: ease `cubic-bezier(0.34,1.45,0.64,1)` (soft overshoot), 320ms, stagger 50ms.
- Options (class A):
  - Hover: buoyant lift `translateY(-4px) scale(1.015)` (canon).
  - Press: squish `translateY(1px) scale(0.95)` (canon).
  - Scroll: once per element, `scale(0.95)→1` + opacity (canon), via `animation-timeline: view()` or Motion `inView`.
  - Success: a short pop of the button or a small checkmark draw (SVG stroke), under 600ms.
- Library choice: `motion` (catalog default) or `animejs` for springs and staggers; CSS for hover/press. GSAP is optional and license-restricted (not vendored).
- Avoid (canon): infinite floating cards, confetti spam, blur-heavy glass over clay.
- Reduced motion (canon): 0ms, settled layout; hover only shifts the inner highlight colour.

<!-- section:typography -->
## Typography
- Display: Rubik Variable (rounded corners, Cyrillic). Body: Nunito Variable (rounded, friendly). Mono: JetBrains Mono only for codes or numbers in apps.
- Body 17–18px, line-height 1.6, measure 55–65ch. Larger body text suits young and casual readers [assumption].
- Headings 600–700; avoid weights below 400 on clay surfaces.

<!-- section:color -->
## Color
- Light (default): pale sky `bg`, near-white `surface`, deep navy text, coral `accent` `oklch(0.535 0.185 28)`, mint/teal `accent_2`.
- Dark: twilight indigo `bg`, lighter indigo `surface`, light text, peach `accent`.
- Pastel fills are for backgrounds of cards and icons; text stays dark navy (or white on the coral button if it passes 4.5:1).
- Avoid (canon): dark muddy plum plastic rings.

<!-- section:surfaces -->
## Surfaces
- Radius: card 28px, input 18px, buttons and badges pill (tokens).
- Shadows: clay triple shadow (tokens). Keep the outer shadow soft and low (alpha ≤ 0.12 light).
- Borders: 1px soft border on cards; crisp border on inputs and toggles so they pass 3:1 (WCAG 1.4.11).
- Never 0px brutalist corners (canon).

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Light base prompt (canon): "Isometric tactile miniature studio scene of {subject} built from smooth matte-clay and frosted ceramic geometric forms in coral-terracotta and mint accents on pale sky-chalk stage, wraparound daylight softbox, 50mm macro lens, completely blank smooth surfaces".
- Dark base prompt (canon): "Playful satin-clay and matte anodized geometric props for {subject} on a deep twilight-indigo studio tabletop, warm coral-peach key light and mint rim reflection, 50mm macro lens, smooth unmarked surfaces".
- Team portrait (canon): vertical 3:4, warm friendly light, smart-casual knitwear, pale ice-blue or deep navy backdrop.
- Icons: simple inline SVG, rounded caps; no emoji as the only label.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `nextjs`, `astro`, `sveltekit`, `vite_ts`. Presets: `bento_interactive`, `css_scroll_native`, `gsap_scrollytelling` (built with Motion).
- Clay is CSS only: radius + layered `box-shadow`. Put shadows in tokens (`--clay`, `--clay-pressed`) so every card matches.
- Many layered shadows on many moving cards cost paint time; animate `transform` only and keep the shadow static [assumption].

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: FAQ for parents/users in visible text; `SoftwareApplication` or `Course` JSON-LD where it fits.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Soft shadows without borders make inputs and buttons hard to see. Fix: crisp border on controls.
- Bouncy motion everywhere tires users and can cause motion sickness. Fix: only on interaction, once on reveal, off under reduced motion.
- Gamified streaks and rewards can become dark patterns. Fix: honest, optional celebrations; no guilt messages.
- Pastel text on pastel fills fails contrast. Fix: dark navy text on all fills.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): jetbrains_mono, nunito, rubik.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); anime.js 4.5.0 (`anime.esm.min.js`); Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Controls have a crisp border (3:1) and a visible focus ring.
- Text contrast ≥ 4.5:1; pastel only as background.
- No infinite motion, no confetti spam, no manipulative streak or reward patterns.
- Reduced motion: settled layout.
