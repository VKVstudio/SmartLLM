# Canon 10_industrial_tactile: Industrial Tactile Hardware

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/10_industrial_tactile.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- The page looks like a precision instrument: warm grey bead-blasted surfaces, raised "keycap" buttons, recessed input wells, thin chassis seams, small mono labels (CH-01, SPEC) and one signal-orange control.
- Background: in the spirit of Braun industrial design (Dieter Rams: "as little design as possible") and modern hardware makers.
- It works because physical cues (raised = press me, recessed = type here) make controls obvious and feel well-made.
- Good fits: hardware, audio gear, engineering, manufacturing, IoT, tools, configurators.
- Weak fits: editorial reading, luxury fashion, kids, purely abstract SaaS.
- Mood: precise, tactile, trustworthy. Default polarity: light (warm aluminium). Dark: anodized titanium.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 18px gutter, container 1280px, section padding 80px, card padding 24px (tokens).
- Think in "panels" of a device: each section is a panel with a seam (1px line + light inner highlight) and small labels in the corner.
- Typical landing order:
  - top bar like a device header (logo, model number, links);
  - hero: product image + h1 + keycap CTA;
  - spec panel (table of specs, mono labels);
  - feature panels (2–3 columns) with small diagrams;
  - an interactive control demo (knob, toggle, slider) if relevant;
  - comparison or model picker;
  - support/downloads panel; footer.
- Mobile: panels stack; spec tables scroll horizontally with a visible hint.

<!-- section:hero -->
## Hero
- h1: Jura 700, `clamp(2rem, 1.583rem + 1.85vw, 3.25rem)` (52px desktop, 40 tablet, 32 mobile), line-height 1.08, tracking −0.02em, measure about 24ch.
- Option 1, "Product on plinth": a large B product shot, h1 and one orange keycap CTA beside it, a row of 3 mono spec markers. Pick it as the default.
- Option 2, "Control panel": the hero built as a device face: h1 on a panel, a few real controls (toggle, slider) that change a small readout. Pick it for audio, synths, configurators.
- Option 3, "Exploded spec": product image with thin leader lines to labels (inline SVG). Pick it for engineering detail.

<!-- section:blocks -->
## Blocks
- Keycap button (raised): radius 8px, `box-shadow` from tokens (inner top highlight + inner bottom shade + small outer shadow). Primary keycap uses the orange accent.
- Input well (recessed): radius 6px, inset shadow, crisp 1px border (canon: inputs recessed, CTAs raised).
- Panel/card: radius 10px, 1px border, seam highlight.
- Spec table: `<table>`, mono labels, `tabular-nums`, units in a lighter colour.
- Telemetry marker: 11px Fira Code uppercase tag (CH-01, SPEC, V2.1) (canon).
- Controls: native `<input type="range">`, checkbox styled as a toggle, `<select>`; all keyboard operable.
- Status LED: small round dot with green `accent_2` for "ok".

<!-- section:motion -->
## Motion
- Motion budget: medium-low (dial 6), all mechanical. Tokens: ease `cubic-bezier(0.34,1.45,0.64,1)` (small overshoot), 170ms, stagger 30ms.
- Options (class A):
  - Hover: keycap micro-lift `translateY(-1px)` + sharper top highlight (canon).
  - Press: key travel `translateY(2px)` + `inset 0 2px 5px oklch(0 0 0 / 0.28)` (canon).
  - Knob/slider: value readouts update instantly; a dial can rotate with `transform: rotate()` bound to the input value.
  - Toggle: thumb slides 150–200ms.
- Scroll: none. The "chassis stays bolted" (canon). No parallax.
- Library choice: CSS is enough; `motion` (catalog default) only for small sequences. GSAP is optional and license-restricted (not vendored).
- Avoid (canon): mushy neumorphism, floaty parallax, huge 32px pills.
- Reduced motion (canon): no translate; instant recessed press state.

<!-- section:typography -->
## Typography
- Display: Jura Variable (technical, slightly squared; Cyrillic). Body: Source Sans 3 Variable. Mono: Fira Code for labels, values, part numbers.
- Body 16px, line-height 1.5. Labels 11–12px mono uppercase with 0.06em tracking.
- Use `tabular-nums` for all values and specs.

<!-- section:color -->
## Color
- Light (default): warm aluminium `bg`, lighter `surface`, near-black text, signal orange `accent` `oklch(0.520 0.168 38)`, green `accent_2` for status.
- Dark: titanium `bg`, light text, brighter orange `oklch(0.695 0.185 42)`.
- Orange marks the one primary control per panel, like a physical device. Do not spread it.
- Neumorphism risk: low-contrast raised/recessed shapes fail WCAG 1.4.11 (UI parts need 3:1). Always keep a visible 1px border on controls (canon: crisp border on inputs).

<!-- section:surfaces -->
## Surfaces
- Radius: card 10px, button 8px, input 6px, badge 4px (tokens: "6–10px machined corners").
- Borders 1px, mid-grey.
- Shadows: layered insets from tokens; never one big soft blur.
- No glass blur over controls (canon).
- Optional fine texture (bead-blasted) only in B images, not as CSS noise over text.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Light base prompt (canon): "Macro studio product study of {subject} featuring bead-blasted warm aluminum chassis, tactile matte ceramic switches, knurled rotary dials, and signal-orange mechanical toggle, overhead softbox light, 90mm macro lens, clean unmarked hardware".
- Dark base prompt (canon): "Macro studio photograph of {subject} in matte dark anodized titanium with knurled charcoal encoder knobs and signal-orange tactile mechanical buttons, crisp rim light, 90mm macro lens, clean unmarked surfaces".
- Team portrait (canon): vertical 3:4, warm studio light, textured knitwear, light stone or titanium-slate backdrop.
- Diagrams and leader lines as inline SVG, not images.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`, `vite_ts`, `sveltekit`. Presets: `bento_interactive`, `css_scroll_native`, `gsap_scrollytelling` (built with Motion).
- Controls are native HTML elements styled with CSS. A configurator needs only a small script (vanilla or Motion), no framework.
- Tokens: `--key-shadow`, `--key-shadow-pressed`, `--well-shadow` as CSS custom properties.

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: specs in a real `<table>` (answer engines quote tables well); add `Product` JSON-LD with model, brand and key properties.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Raised/recessed looks without borders fail as controls (neumorphism problem). Fix: 1px border with 3:1 contrast on every control.
- Custom knobs and sliders break keyboard and screen readers. Fix: native `<input type=range>`/checkbox under the styling, with labels and visible values.
- Small 11px mono labels carry meaning. Fix: use them only as extra tags; key info in ≥ 14px text.
- Spec tables overflow on mobile. Fix: scroll inside the table box with a visible hint or a stacked card view.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): fira_code, jura, source_sans_3.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Every control has a visible border or outline (3:1 against its background) and a `:focus-visible` ring.
- All controls are native and keyboard operable.
- No scroll effects, no parallax.
- Reduced motion: instant press states.
