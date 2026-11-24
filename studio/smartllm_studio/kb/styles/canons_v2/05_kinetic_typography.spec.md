# Canon 05_kinetic_typography: Kinetic & Variable Typography

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/05_kinetic_typography.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- In this style the words are the main image. Big display type moves, stretches and changes weight. Photos and decoration play a small supporting role.
- Canon look: a dark "museum poster" stage, the variable Tektur display face, 2px frames, and a hard colour flood on hover.
- It works because motion pulls the eye to the message. Codrops puts it this way: animate a few words at a time, at the pace you would read them aloud, and remove distractions.
- Variable fonts let one file change weight and width smoothly, so the type can "breathe" without extra images.
- Good fits: culture, exhibitions, festivals, agencies, product launches, type foundries, creative studios.
- Weak fits: banks, healthcare, long-form docs, forms-heavy apps, any audience that needs calm.
- Mood: loud, rhythmic, confident. Default polarity: dark. A light gallery-white version exists.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 20px gutter, container 1360px, section padding 88px, card padding 26px (tokens).
- The page is a sequence of "stages". Each stage has one short statement (2–6 words) and some supporting content.
- Typical landing order:
  - hero statement;
  - a marquee band (names, dates or keywords) with a Pause button;
  - an "about" block in calm body text;
  - a programme or work list as big typographic rows (hover floods the row);
  - a featured item with one photo;
  - a final call-to-action statement.
- Keep body text calm and readable between the loud parts. The contrast between loud and calm is what makes the loud parts work [assumption].
- Mobile: the same stages, smaller type, fewer moving parts. The Exat microsite simplified interactions on mobile instead of copying them.

<!-- section:hero -->
## Hero
- Rule from the canon: the display headline takes about 55% of the hero fold.
- h1: Tektur 800, uppercase, `clamp(1.75rem, 0.75rem + 4.44vw, 4.75rem)` (76px desktop, 52 tablet, 28 mobile), line-height 0.96, tracking −0.03em, measure about 14ch.
- Option 1, "Stretch reveal": letters enter by line with a mask and settle while the `wdth` axis grows from 75 to 100. Pick it for a launch or a festival.
- Option 2, "Scroll statement": a few words per step move through the screen on scroll and slow down in the centre so they can be read. Build it with anime.js `onScroll` (ScrollObserver) or Motion `scroll()`, or CSS `animation-timeline: view()`; use an ease that is slow in the middle so the words can be read. Pick it for a story with 3–6 short claims.
- Option 3, "Glyph field": a grid of letters that change weight near the cursor, as on the Exat microsite. Replace it with a static grid on touch screens. Pick it for a type or design brand.
- Option 4, "Static poster": the same big type with no motion and one B image behind or beside it. Pick it for a short budget or reduced motion.
- Load the font before measuring or splitting text. If you split too early, the line breaks come out wrong.

<!-- section:blocks -->
## Blocks
- Marquee band: one line of big words that loops. It needs a visible Pause button (see Motion and Hard limits).
- Typographic list: each row is a title, a date and a tag. On hover or focus the row floods with the accent colour and the text switches to the accent ink (canon "flood inversion").
- Statement block: one sentence at display size, revealed with a clip-path wipe on scroll.
- Framed card: 2px solid border, radius 2px, no shadow.
- Calm text block: Commissioner body text, 60–70ch, no motion.
- Number block: big numbers in JetBrains Mono for dates, counts and prices.
- Image block: one high-contrast photo (B) with a 2px frame.

<!-- section:motion -->
## Motion
- Motion budget: high (dial 8). Motion is the brand here, but each effect still needs a reason.
- Tokens: ease `cubic-bezier(0.16,1,0.3,1)`, 200ms, stagger 30ms. Press: `scale(0.97)` for 90ms.
- Options (class A):
  - Text split by lines, words or chars with a stagger: anime.js v4 `splitText()` (vendored) or a small custom splitter. Keep the full text for screen readers: `aria-label` with the full text on the parent and `aria-hidden="true"` on the pieces.
  - Variable axis animation: animate `font-variation-settings` or `font-stretch` (`wdth` 75–100, `wght` 400–900 in Tektur).
  - CSS scroll-driven clip-path wipe: `animation-timeline: view()` inside `@supports`. It runs off the main thread and needs no JS.
  - CSS marquee: a duplicated track with `translateX` keyframes and `animation-play-state` for pause.
  - Hover flood: instant background swap plus a short colour transition.
- Library choice (catalog motions are `animejs`, `motion`, `css_scroll_driven`; default `animejs`):
  - `css_scroll_driven` for wipes and reveals. Why: no JS cost.
  - `animejs` or `motion` for split-text staggers and timelines. Why: small and in the catalog.
  - GSAP: optional, license-restricted, not vendored. The preset `gsap_scrollytelling` is built with anime.js or Motion instead (same scroll-story pattern).
- Pause loops when they are off screen. The Exat team did this to keep performance part of the design.
- Avoid:
  - animating `font-size` of flowing paragraphs, because the text reflows and jumps (canon);
  - unpausable flashing or tickers, because of SC 2.2.2 and flash risk (canon);
  - blurry shadows, because they fight the crisp poster look (canon);
  - too many effects at once. Codrops warns that type animation should not be used excessively.
- Reduced motion (canon): the marquee is paused, `clip-path: none`, `opacity: 1`. Show the final state of every text effect.
- No class C: no video loops or frame sequences behind the type.

<!-- section:typography -->
## Typography
- Display: Tektur Variable. It is an octagonal, blocky face with a `wdth` axis 75–100 and `wght` 400–900. It is free (OFL) and covers Cyrillic.
- Body: Commissioner Variable. Mono: JetBrains Mono Variable for numbers, dates and labels.
- Canon rule: narrow Tektur `wdth` at 360px screens for long Russian words, so they do not overflow.
- Canon rule: never use the uppercase display face for body paragraphs. It is hard to read in long runs.
- Use `text-wrap: balance` on headlines so the lines are even.
- Keep words as real HTML text, not images or SVG paths, so they stay searchable and translatable.

<!-- section:color -->
## Color
- Dark (default): near-black stage, near-white text, crimson accent `oklch(0.675 0.205 18)`.
- Light: gallery white, near-black ink, crimson accent `oklch(0.505 0.195 18)`, blue `accent_2` for links or secondary tags.
- One loud accent only. The flood hover uses it, so it must be rare elsewhere.
- Check contrast for text placed on the accent flood (accent ink colour) [assumption].

<!-- section:surfaces -->
## Surfaces
- Radius 2px everywhere: cards, buttons, inputs, badges (tokens).
- Borders: 2px solid, in the text colour.
- Shadows: none in both themes. Blur: none.
- The "stage" feel comes from big empty dark areas and framed blocks, not from effects.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Images are supporting actors. Use 1–3 per page.
- Dark base prompt (canon): "High-contrast monochromatic exhibition photograph of {subject} sliced by razor diagonal studio light beams across brushed titanium and matte carbon concrete with one vivid crimson highlight, 50mm lens, clean blank surfaces".
- Light base prompt (canon): "Stark white exhibition gallery space displaying {subject} under crisp diagonal architectural shadow, matte plaster and dark steel with one scarlet sculptural plane, 50mm lens, clean unmarked surfaces".
- Team portrait (canon): vertical 3:4, hard side light, obsidian or white backdrop, 85mm, empty headroom.
- Do not put text into the image prompt. Set all words in HTML on top.
- Motion on images is limited to code: a clip-path reveal or a small scale on scroll (class A).

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`, `vite_ts`, `sveltekit`, `nextjs`.
- Landing presets: `kinetic_showreel` (default fit), `gsap_scrollytelling` (scroll story, built with anime.js or Motion), `css_scroll_native` (lightest).
- Fonts: self-host the variable WOFF2 files. One variable file replaces many static weights.
- Split text only after `document.fonts.ready`, and re-split on resize if you split by lines.
- Smooth scroll (Lenis) is optional. Apply it only if the scroll story needs it.

<!-- section:seo -->
## SEO / AEO / GEO
- The real headline text stays in the DOM. Split pieces are `aria-hidden` and the parent keeps the full text.
- Put the facts (dates, venue, price, artist names) in plain text blocks, not only in moving bands.
- Use `Event` or `ExhibitionEvent` JSON-LD for events, `CreativeWork` for works [assumption].

<!-- section:ux_check -->
## UX check (risks of this style only)
- Moving or split headlines are hard to read and can be read letter by letter by screen readers. Fix: full text in `aria-label`, pieces `aria-hidden`, final state readable within ~1s.
- Marquee distracts and fails SC 2.2.2 without control. Fix: visible Pause button, stop under reduced motion.
- Scroll-driven statements can feel like scroll hijacking. Fix: native scroll speed, no pinning longer than one screen, content reachable by keyboard.
- Uppercase display type for long words on 360px overflows. Fix: narrower `wdth`, `overflow-wrap`, test longest word.
- Flood-inversion hover only on fine pointers; on touch the row must still look like a link.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): commissioner, jetbrains_mono, tektur.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); anime.js 4.5.0 (`anime.esm.min.js`); Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Any loop longer than 5 seconds has a visible, keyboard-operable Pause button (WCAG 2.2.2). Hover-pause is not enough.
- No content flashes more than 3 times per second (WCAG 2.3.1).
- `prefers-reduced-motion`: show the final static state.
- Self-hosted fonts and scripts. Works offline.
