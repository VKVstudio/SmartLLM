# Canon 13_cinematic_documentary: Cinematic Documentary / Darkroom

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/13_cinematic_documentary.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A dark, filmic storytelling page: charcoal "darkroom" background, Literata serif headlines, one warm amber accent like a tungsten key light, wide still frames with captions, a subtle film grain on desktop.
- It works because it borrows the grammar of documentary film: wide establishing shot, chapters, captions with place and date, slow reveals. Visitors read it as a story, not as an ad.
- Good fits: film and documentary studios, hospitality, restaurants and gastronomy, wineries, NGOs and long-form brand stories.
- Weak fits: SaaS feature pages, dashboards, discount retail, kids, anything that must be scanned fast.
- Mood: warm, serious, intimate. Default polarity: dark (the only dark serif canon). Light: archival baryta paper with slate and burnt amber.
- Avoid (canon): cyan/violet "AI glow", wheel scroll-jacking, springy bounce.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 28px gutter, container 1312px, section padding 104px, card padding 24px (tokens). Density is low (dial 3): few blocks, big frames.
- Typical landing order, built as chapters:
  - nav: logo, 3–5 links, one CTA ("Book a table", "Watch the trailer", "Get in touch");
  - hero: one wide still (2.39:1 or 16:9) with h1 and a short logline;
  - chapter 1–3: each = chapter number + title, one frame, 1–3 short paragraphs;
  - filmstrip gallery (horizontal scroll-snap row) with Prev/Next buttons;
  - quote or testimonial in large Literata italic;
  - facts band (year, place, awards, runtime) in mono;
  - final CTA + contact; footer with credits-style list.
- Text column: 60–68ch, often offset (columns 2–8) next to a wide frame; frames may break out to full bleed.
- A 2px reading progress bar at the top shows how far the story goes (canon).
- Mobile (<768px): one column; full-bleed images stack above text with the scrim removed, so text is never on top of a busy photo (canon).

<!-- section:hero -->
## Hero
- h1: Literata 600, `clamp(2.25rem, 1.625rem + 2.78vw, 4.125rem)` (66px desktop, 48 tablet, 36 mobile), line-height 1.1, tracking −0.02em, measure about 20ch. Italic only for one or two accent words.
- Option 1, "Establishing shot": full-width B still with a directional vignette scrim (dark gradient from one side) and the h1 on the dark side. Pick it as the default.
- Option 2, "Title card": h1 and logline centred on charcoal, the still below in a 2.39:1 frame. Pick it when the photo is busy or text contrast is hard.
- Option 3, "Split frame": still in columns 1–7, h1 + logline + CTA in 8–12. Pick it for hospitality and restaurants that need the CTA early.
- Under the h1: one logline (≤ 25 words) and one primary CTA. A caption line (place · year) in mono adds the documentary feel.
- The hero image is the LCP element: `fetchpriority="high"`, no lazy loading, no fade-in on it.

<!-- section:blocks -->
## Blocks
- Frame: image with a 1px rule and a small mono caption below (place, date, credit), like a contact sheet (canon). Radius 4px.
- Chapter header: number (mono, accent), title (Literata), one-line summary.
- Filmstrip: a row of frames using `scroll-snap-type: x mandatory` on the row and `scroll-snap-align: start` on items; visible Prev/Next buttons that scroll by one frame; the row is also keyboard-scrollable (`tabindex="0"` with a label) (canon).
- Pull quote: Literata italic 28–36px, attribution in sans.
- Facts band: 3–5 key numbers in Source Code Pro with labels.
- Menu or programme list (restaurants, festivals): plain `<dl>` or table, prices in `tabular-nums`.
- Cards: 1px border, 4px radius, soft deep shadow on dark (tokens).

<!-- section:motion -->
## Motion
- Motion budget: medium (dial 6), slow and calm. Tokens: ease `cubic-bezier(0.22,1,0.36,1)`, 460ms, stagger 65ms.
- Options (class A):
  - Hover on frames: "Ken Burns" — the image inside its frame scales to 1.035 while the caption brightens (canon). The frame itself does not move.
  - Press: `scale(0.98)`.
  - Scroll reveal: frames and text fade in with a small rise via `animation-timeline: view()`; reading bar via `animation-timeline: scroll(root)`.
  - Chapter change: optional slow cross-fade of a background tone.
  - Page transitions: View Transitions API cross-fade.
- Scroll-driven CSS is Baseline since October 2026 (Chrome/Edge 115, Safari 26, Firefox 159). Wrap it in `@supports (animation-timeline: view())` so older browsers just show content.
- Library choice: native CSS first (`css_scroll_driven`); Motion (vendored) for sequenced reveals (catalog default `motion`).
- Never hijack the wheel or pin a section for more than one screen. Scrollytelling here means "content changes as you scroll", not "scroll is taken over".
- Reduced motion (canon): plates appear instantly (0ms); Ken Burns zoom disabled.

<!-- section:typography -->
## Typography
- Display: Literata Variable 500–600; italic for accents and quotes.
- Body: Commissioner Variable, 17–18px on dark, line-height 1.6–1.7, measure 60–68ch. Light text on dark looks bolder, so use weight 400 and slightly more line-height.
- Mono: Source Code Pro for captions, timecodes, chapter numbers, facts (12–14px, uppercase optional, tracking 0.06em).
- Captions must still be ≥ 12px and pass contrast; they carry real facts.

<!-- section:color -->
## Color
- Dark (default): charcoal `bg` `oklch(0.130 0.005 60)`, `surface` `oklch(0.175 0.007 60)`, warm off-white text `oklch(0.942 0.008 82)`, amber `accent` `oklch(0.785 0.142 74)`.
- Light: archival grey `bg` `oklch(0.968 0.004 250)`, near-black text, burnt-amber `accent` `oklch(0.490 0.132 44)`, slate `accent_2`.
- Amber only for the CTA, links, chapter numbers and the reading bar. Amber is a key light, not a fill.
- Avoid pure black `#000` and pure white text; the warm near-black and off-white feel like film and reduce glare.

<!-- section:surfaces -->
## Surfaces
- Radius 4px cards/buttons, 2px badges; 1px solid borders (tokens).
- Film grain: a tiny tiled noise PNG/AVIF (≤ 10KB) at 3–6% opacity on desktop only; skip it on mobile and under `prefers-reduced-transparency` (canon). Never an animated SVG `feTurbulence` filter — it costs CPU on every frame.
- Vignette scrim: `linear-gradient` from `bg` at 85% to transparent behind hero text. Test text contrast at the brightest part of the photo.
- Shadows: deep and soft on dark (`0 24px 48px -16px oklch(0 0 0 / 0.65)`), almost none on light.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Stills only. A "film" feel comes from framing and light, not from video (class C deferred).
- Dark base prompt (canon): "Cinematic widescreen 35mm documentary still of {subject} inside a darkroom-lit architectural space, single warm practical tungsten lamp carving deep selenium-charcoal shadows, authentic organic film grain, anamorphic depth, clean blank surfaces".
- Light base prompt (canon): "Archival baryta-paper documentary wide shot of {subject} in natural overcast daylight, crisp tonal depth, muted slate and burnt-amber practical accents, 35mm Leica reportage framing, clean unmarked surfaces".
- Team portrait (canon): vertical 3:4 environmental portrait, warm side key light, 50mm, dark espresso-charcoal (dark) or baryta grey (light) wall.
- Use wide ratios (2.39:1, 16:9) for chapter frames and 3:4 for people. Leave a dark calm area where text will sit.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`, `nextjs`. Presets: `gsap_scrollytelling` (use Motion/CSS instead of GSAP), `css_scroll_native`, `classic_corporate`.
- Static pages with long text are ideal for static HTML; only the filmstrip buttons and optional Motion reveals need JS.
- Long story pages: lazy images, `content-visibility: auto` on far chapters to save rendering work.

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: each chapter has a real h2 and text, not text baked into images; captions as `<figcaption>`.
- Films: `Movie` or `VideoObject` JSON-LD only if a real video exists elsewhere; restaurants: `Restaurant` with `menu`, `servesCuisine`, opening hours; stories: `Article`.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Dark low-light design makes secondary text and captions too dim. Fix: captions ≥ 12px and ≥ 4.5:1; never grey on charcoal below that.
- Text over photos fails contrast where the image is bright. Fix: vignette scrim tested at the brightest point; on mobile put text below the image.
- Scrollytelling can feel like losing control of the page. Fix: native scroll, no pinning beyond one screen, content complete without scrolling effects.
- Horizontal filmstrips hide content and are hard on desktop without a trackpad. Fix: Prev/Next buttons, visible next-frame peek, keyboard focusable row.
- Long story pages hide the CTA. Fix: CTA in nav, after the hero and at the end.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): commissioner, literata, source_code_pro.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- No wheel scroll-jacking; pinning at most one screen.
- Text never sits on a busy photo without a scrim that keeps ≥ 4.5:1.
- Filmstrip has Prev/Next buttons and keyboard scroll.
- Grain only as a tiny static texture, desktop only.
- Reduced motion: instant plates, no Ken Burns.
