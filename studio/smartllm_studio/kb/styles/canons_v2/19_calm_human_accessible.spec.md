# Canon 19_calm_human_accessible: Calm Humanist / Trust-First Accessible (WCAG AAA)

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/19_calm_human_accessible.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A calm, plain, very readable page built to WCAG 2.2 AAA where possible: near-black ink on white (canon target ≥ 14:1), 48px touch targets, thick visible focus rings, always-underlined links, no motion, plain language.
- It works because the people these sites serve (patients, older adults, citizens in stress, people with disabilities) need to find one answer and act. Calm and clarity are the brand.
- Good fits: healthcare, clinics, government and civic services, education, social services, insurance claims, utilities.
- Weak fits: fashion, gaming, festivals, luxury, "wow" product launches.
- Mood: calm, kind, trustworthy. Default polarity: light. Dark: calm ocean-slate (not pure black).
- Applies on top of `_ux_baseline.md`: this canon raises its AA limits to AAA.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 24px gutter, container 1312px, section padding 88px, card padding 28px (tokens). Content column ≤ 70ch.
- Typical landing order:
  - skip link "Skip to main content" (visible on focus);
  - header: logo, search, 4–6 task-based nav items ("Book an appointment", "Find a service"), language, contact phone;
  - hero: h1 saying who it is for, 1–2 sentences, 2–4 big task buttons;
  - top tasks grid (cards with a clear verb);
  - urgent info band (opening hours, emergencies) with an icon + text;
  - how it works: numbered steps;
  - FAQ as always-open Q&A or `<details>` (canon);
  - contact options (phone, form, address, accessibility of the building); footer with accessibility statement link.
- Simple, predictable layout: same nav and footer on every page; no surprises.
- Mobile: single column; task buttons full width, ≥ 48px tall.

<!-- section:hero -->
## Hero
- h1: Golos Text 700, `clamp(2rem, 1.625rem + 1.67vw, 3.125rem)` (50px desktop, 40 tablet, 32 mobile), line-height 1.18, tracking −0.015em, measure about 26ch.
- Option 1, "Task hero" (default): h1 + one sentence + 2–4 large task buttons. No image needed.
- Option 2, "Photo + tasks": calm daylight photo to the side (never behind text), tasks next to the h1.
- Option 3, "Search hero": h1 + a large labelled search field with example queries. Pick it for big service catalogues.
- Phone number and opening hours visible in the first screen for clinics and services.

<!-- section:blocks -->
## Blocks
- Card: white, 12px radius, 2px border, soft shadow (tokens); whole card is one link with a verb title.
- Buttons: ≥ 48×48px, text label (icon optional, never icon-only), 8px radius.
- Links: always underlined in text (canon), visited state different.
- Alerts/status: icon + word + text ("Warning: …"), never colour only (canon).
- FAQ: questions as headings, answers visible or in native `<details>` (canon). No custom accordions without keyboard support.
- Forms: one question per screen for long flows; no time limits, or the user can extend them (WCAG 2.2.6 AAA); no CAPTCHA puzzles — use honeypot/rate limits from the baseline (WCAG 3.3.8 accessible authentication).
- Language switch and "Easy read" / plain-language versions where the content is complex.

<!-- section:motion -->
## Motion
- Motion budget: none (dial 2); catalog motion `reduced_motion_instant` only. Tokens: ease `cubic-bezier(0.25,0.1,0.25,1)`, 180ms, no stagger.
- Allowed (class A): colour and border changes on hover/focus (canon: no transform), press `scale(0.99)`, optional opacity-only reveal (no movement, to avoid vestibular triggers) (canon).
- Forbidden (canon): parallax, marquees, transform/scale on scroll, auto-playing carousels.
- This meets WCAG 2.3.3 "Animation from interactions" (AAA).

<!-- section:typography -->
## Typography
- Headings: Golos Text Variable 600–700.
- Body: Source Sans 3 Variable 18px (≥ 17px on mobile), line-height 1.6, measure ≤ 70ch, left-aligned, never justified (WCAG 1.4.8 AAA).
- Mono: Fira Code only for reference numbers and codes.
- Text must reflow at 200% zoom and work with user spacing overrides (WCAG 1.4.12).
- Plain language: short sentences, common words, explain terms; aim at a lower-secondary reading level (WCAG 3.1.5 AAA).

<!-- section:color -->
## Color
- Light (default): `bg` `oklch(0.985 0.004 215)`, white `surface`, ink text `oklch(0.155 0.015 222)`, deep teal `accent` `oklch(0.355 0.056 212)`, brown `accent_2` `oklch(0.395 0.088 56)`, `border` `oklch(0.540 0.016 218)`.
- Dark: slate `bg` `oklch(0.155 0.014 225)` (not pure black, avoids halation), `surface` `oklch(0.205 0.016 225)`, pale text, light aqua `accent` `oklch(0.820 0.090 204)`.
- Contrast targets: body text ≥ 7:1 (WCAG 1.4.6 AAA); canon aims ≥ 14:1 for main text; muted text and accents ≥ 7:1 (canon); borders of controls ≥ 3:1.

<!-- section:surfaces -->
## Surfaces
- Radius 12px cards, 8px buttons and inputs, 6px badges; 2px solid borders (tokens).
- Light shadow `0 2px 8px rgba(6,14,17,0.06)`; dark: none.
- Focus ring: 3px solid, high contrast, offset 2px, on every focusable element (canon); this meets WCAG 2.4.13 focus appearance (AAA).
- No blur, no text over images.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Optional and supportive. Real people and places beat illustrations.
- Light base prompt (canon): "Calm glare-free daylight architectural interior photograph of {subject}, pale Nordic birch wood, soft sea-glass teal ceramic accents, and warm porcelain surfaces with open airy clarity, 50mm lens, clean blank unmarked walls".
- Dark base prompt (canon): "Calm evening civic-clinic architectural photograph of {subject} with soft glare-free warm-white interior lamps, deep calm ocean-slate walls, and gentle pale aqua-glass accents, 50mm lens, clean unmarked surfaces".
- Team portrait (canon): vertical 3:4, natural smile, glare-free softbox daylight.
- Every meaningful image has `alt`; text is never inside images.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Preset: `classic_corporate`.
- Works without JS: navigation, FAQ (`<details>`), forms with server-side validation. JS only adds conveniences.
- Publish an accessibility statement page (required for public bodies in the EU; good practice everywhere). The European Accessibility Act applies to many private services since June 2025.

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: `MedicalClinic`/`Physician`/`GovernmentService` with `areaServed`, hours, phone; FAQ in visible HTML (FAQPage only when visible, per baseline).

<!-- section:ux_check -->
## UX check (risks of this style only)
- Calm can become bland: everything looks equal, top tasks get lost. Fix: 2–4 big task buttons in the hero; one primary action per screen.
- Many always-open FAQs make pages very long. Fix: group by topic with an in-page contents list; use `<details>` for long lists.
- Full AAA is not always reachable for all content (W3C does not require it site-wide). Fix: AAA for templates, colours, targets and focus; state exceptions in the accessibility statement.
- Large text and targets push content down on phones. Fix: compact header, key task above the fold, no decorative hero image on mobile.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): fira_code, golos_text, source_sans_3.
- JS: none (CSS only).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Body text ≥ 7:1 (canon main text ≥ 14:1); controls ≥ 48×48px; 3px focus ring.
- Links always underlined; status never by colour alone.
- No parallax, marquee, carousel autoplay or movement on scroll.
- No time limits without extend; no CAPTCHA puzzles.
