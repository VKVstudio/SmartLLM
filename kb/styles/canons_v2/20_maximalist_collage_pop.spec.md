# Canon 20_maximalist_collage_pop: Curated Maximalism / Pop Collage

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/20_maximalist_collage_pop.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A loud but curated pop collage: colour-blocked sections in ultramarine, coral and marigold, mixed card shapes (18px cards + pill stickers), 5px coloured offset shadows, slightly tilted cards, big heavy Rubik headlines, one pausable marquee.
- It works because energy and surprise signal youth culture, events and creativity. "Curated" means a strict palette and grid under the chaos, so it stays readable.
- Good fits: festivals, youth brands, creative agencies, media, music, events, pop-up shops.
- Weak fits: banks, legal, medical, government, enterprise B2B.
- Mood: energetic, playful, bold. Default polarity: light. Dark: midnight cobalt with marigold.
- Compared with `06_neo_brutalism`: here shadows are coloured and shapes rounded; no black 0px stamps (canon).
- Avoid (canon): text over busy photos, light/dark polarity flips mid-page, more than one marquee.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 24px gutter, container 1312px, section padding 92px, card padding 26px (tokens).
- Typical landing order:
  - nav + CTA ("Get tickets", "Work with us");
  - hero: huge h1, collage of 3–5 cut-out images and stickers, date/place or one-line offer;
  - marquee band (one per page, canon): lineup, clients or key words;
  - colour-block sections alternating `surface` colours but keeping page polarity (canon);
  - lineup / work grid with mixed card sizes;
  - info: dates, venue, prices (clear, not collaged);
  - FAQ; final CTA; footer.
- The chaos is only visual: reading order, headings and grid stay simple.
- Mobile: tilts reduced to 0–1°, collage becomes a stacked set of 2–3 images.

<!-- section:hero -->
## Hero
- h1: Rubik 800, `clamp(2rem, 1.458rem + 2.41vw, 3.625rem)` (58px desktop, 44 tablet, 32 mobile), line-height 1.06, tracking −0.03em, measure about 18ch.
- Option 1, "Collage stage" (default): h1 over a solid colour block, 3–5 B images as cut-out cards around it with tilts −3°…3°, 2–3 pill stickers ("New!", dates).
- Option 2, "Poster type": h1 fills the width in two colours, one image sticker. Pick it for festivals with strong names.
- Option 3, "Grid pop": 2×2 coloured tiles, h1 in one, images in others. Pick it for agencies.
- Key facts (date, city, price from) as real text near the h1, never inside images.

<!-- section:blocks -->
## Blocks
- Card: 18px radius, 2px ink border, `5px 5px 0` coral offset shadow (tokens); alternating tilt (±1–3°) straightened on hover and under reduced motion (canon).
- Sticker: pill (`9999px`), bold Rubik, rotated, with real text.
- Marquee: one band, CSS `@keyframes` translate, duplicated content `aria-hidden` on the copy, visible Pause button (WCAG 2.2.2), stops on hover and focus (canon).
- Lineup/work grid: mixed sizes via `grid-template-areas`; DOM order = importance.
- Ticket/price block: calm card, no tilt, clear tiers and a button each.

<!-- section:motion -->
## Motion
- Motion budget: high (dial 8). Tokens: ease `cubic-bezier(0.34,1.38,0.64,1)` (slight overshoot), 280ms, stagger 40ms.
- Options (class A):
  - Hover: tilt to 0°, `translate(-3px,-3px)`, shadow grows to `8px 8px 0` (canon).
  - Press: `translate(4px,4px)`, shadow 0.
  - Entrance: staggered "pop" (scale 0.92 → 1 + opacity) on reveal, once.
  - Marquee: one, pausable (canon).
- Library choice: anime.js (vendored, catalog default `animejs`) for staggered pops; Motion as an alternative; CSS `animation-timeline: view()` for simple reveals.
- Avoid infinite wobble; at most the marquee loops.
- Reduced motion (canon): cards at 0°, no pops; marquee stops and becomes wrapped pills.

<!-- section:typography -->
## Typography
- Display: Rubik Variable 700–900.
- Body: Nunito Variable 16–18px, line-height 1.55, measure 55–68ch.
- Accent notes: Shantell Sans for small sticker text (optional).
- Mono: JetBrains Mono for dates, times, codes.
- Mixed weights and sizes in one heading are fine; keep it one family.

<!-- section:color -->
## Color
- Light (default): `bg` `oklch(0.976 0.008 98)`, `surface` `oklch(0.946 0.028 98)`, ink text `oklch(0.145 0.014 265)`, ultramarine `accent` `oklch(0.455 0.202 264)`, coral `accent_2` `oklch(0.515 0.195 22)`, ink `border`.
- Dark: cobalt `bg` `oklch(0.148 0.030 268)`, `surface` `oklch(0.205 0.036 266)`, pale text, marigold `accent` `oklch(0.865 0.162 94)`.
- Colour blocks: 3–4 colours max on one page plus ink and paper. Check text contrast on every block colour.

<!-- section:surfaces -->
## Surfaces
- Radius 18px cards, pill buttons and badges, 12px inputs; 2px solid borders (tokens).
- Shadow: `5px 5px 0 oklch(0.515 0.195 22)` light, `5px 5px 0 oklch(0.715 0.168 24)` dark.
- No blur and no gradients over text.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Light base prompt (canon): "Editorial pop-art studio still life of {subject} arranged as bold geometric color blocks in ultramarine cobalt, vermilion red, and pale canary ceramic props under crisp directional sunlight, 50mm lens, clean blank unmarked objects".
- Dark base prompt (canon): "Curated maximalist theater still life of {subject} lit with sharp marigold-yellow and hot-coral studio gel planes against deep midnight cobalt, crisp sculptural ceramic props, 50mm lens, clean unmarked surfaces".
- Team portrait (canon): vertical 3:4 punchy headshot, solid-colour styling, studio strobe, cobalt or indigo backdrop.
- Cut-out look: images in rounded cards or with `clip-path` shapes; no text inside images.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Presets: `kinetic_showreel`, `gsap_scrollytelling` (use anime.js/Motion/CSS), `css_scroll_native`.
- Many images: lazy-load all below the hero; collage images ≤ 80KB each.

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: `Event`/`MusicEvent` with dates, location, `offers`, performers; lineup as HTML text.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Visual noise hides the main action. Fix: one primary CTA colour used nowhere else; ticket/CTA block calm and untilted.
- Tilted text and stickers are harder to read and may overlap on small screens. Fix: tilt only cards, max 3°, 0–1° on mobile; no overlap with text.
- Coral and marigold fills with white text fail contrast. Fix: ink text on light fills; check every block colour pair.
- Motion everywhere can trigger vestibular issues. Fix: pops once, no infinite wobble, one pausable marquee, all off under reduced motion.
- Collage order differs from reading order. Fix: DOM order = reading order; decorative images `alt=""`.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): jetbrains_mono, nunito, rubik, shantell_sans.
- JS (`vendor/js/<lib>/`): Motion 14.14.0 (`motion.js`); anime.js 4.5.0 (`anime.esm.min.js`); Lenis 1.3.27 (`lenis.mjs`).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- One marquee max, with Pause; stops under reduced motion.
- Never text over busy photos; check contrast on every block colour.
- Page polarity stays the same top to bottom.
- Prices, dates and venue in calm, untilted blocks.
