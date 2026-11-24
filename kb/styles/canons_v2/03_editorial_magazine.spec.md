# Canon 03_editorial_magazine: Editorial Monograph / Broadsheet

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/03_editorial_magazine.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- This style copies the printed newspaper and the scholarly book: a strong nameplate, columns, thin ink rules, serif headlines and a clear story hierarchy.
- It works because readers already know how to scan a front page. The biggest headline is the most important story, and the rules and columns tell the eye where one story ends.
- Good fits: journalism, research labs, publishers, think tanks, essay-driven brands, annual reports, a long case study, a monograph or book site.
- Weak fits: playful consumer apps, image-only portfolios, anything with no text worth reading. Without real copy, the style looks empty.
- Mood: serious, literate, trustworthy. Default polarity: light (warm newsprint). Dark works for evening or culture titles.

<!-- section:structure -->
## Structure
- Page model: a front page that ranks stories, and article pages built for long reading.
- Typical front page, top to bottom:
  - Nameplate (the site name, big) with a dateline row: date, issue or edition, a small menu.
  - Section bar: a 2px rule, then the section links, then a 1px rule.
  - Lead story: one dominant headline, a standfirst (the lede paragraph) and a large image.
  - Secondary stories: 2 to 4 smaller headlines in columns, split by 1px vertical rules.
  - Briefs rail: a narrow column of short items, numbers or a "most read" list.
  - Feature band: one wide image and a pull quote.
  - Newsletter or CTA set like a printed box with a rule, not a soft card.
  - Footer like a colophon: publisher, address, small print.
- Why: the eye goes top-left to bottom-right (Gutenberg principle); the lead sits above the fold.
- Grid: 12 columns, 24px gutter, section padding about 84px (canon tokens). Common splits are 8+4 (lead + rail), 6+3+3 (lead + 2 secondary) or 4+4+4 (three equal stories, used below the lead only).
- Never flow body text across columns; readers would scroll up again.
- Article page options:
  - "Broadsheet article": a 12-col grid, the body in about 7 columns, a side rail for notes and figures.
  - "Monograph page": a 9-column grid with the text in columns 2–7, based on the Van de Graaf / Tschichold page canon. It feels like a well-made book.
- Body measure: 45–75 characters per line, about 66 is ideal (Bringhurst). Use `max-width: 66ch` for body text.
- Mobile: one column. Keep the rules as horizontal dividers. The rail moves below the lead.

<!-- section:hero -->
## Hero
- Option 1, "Front page lead":
  - Content: nameplate, a big serif headline over 8 columns, a standfirst, then a large B image (16:9 or 3:2) with a caption and credit line.
  - Pick it for a news-like or publisher home page.
- Option 2, "Cover statement":
  - Content: a very large serif headline (h1 72px desktop), with an italic emphasis word, on plain paper colour. No image. A thin rule and a dateline sit below.
  - Pick it for an essay, a manifesto or a book.
- Option 3, "Plate and caption":
  - Content: a B image as a printed plate (inside `overflow:hidden`, no radius), with the headline in the column beside it and a mono caption under the image.
  - Pick it for a research or architecture monograph.
- Rules for every option:
  - The headline is real text, never inside the image.
  - One `h1` per page.
  - The hero image uses `fetchpriority="high"` and AVIF/WebP.

<!-- section:blocks -->
## Blocks
- Story card (not a visual card): kicker (section in small caps), headline, 2-line summary, byline; a top rule, no box or shadow; optional 3:2 B photo above.
- Pull quote: large italic serif with attribution; 2px rule above, 1px below; in the rail or across 8 columns.
- Drop cap: `::first-letter` with `initial-letter: 3` where supported, floated fallback.
- Data/spec table: mono datelines and figures (canon); rules between rows, no zebra.
- Figure: B image + mono caption and credit (captions are among the most read text [assumption]).
- Briefs list: numbered short items with a bold lead-in ("most read", milestones, contents).
- Author box: name, role, short bio, 3:4 B portrait.
- Footnotes: numbered notes at the end with back-links (credibility for research sites).
- Marquee (allowed): one slow headline ticker in the dateline row, pauses on hover.

<!-- section:motion -->
## Motion
- Motion budget: low. Reading comes first. Catalog dial motion = 5.
- Options:
  - Link hover (A): an underline that draws from left to right, 220ms, ease `cubic-bezier(0.22,1,0.36,1)` (canon token).
  - Image hover (A): `scale(1.025)` inside an `overflow:hidden` plate (canon token). It feels like a printed plate.
  - Press (A): opacity 0.85.
  - Section reveal (A): an optional crisp clip reveal using CSS `animation-timeline: view()` inside `@supports`. Prefer a clip (`clip-path: inset`) over a fade, because ink on paper does not fade [assumption].
  - Headline ticker (A): CSS keyframes translateX, very slow, paused on `:hover` and `:focus-within`.
- Avoid: bouncy springs (app-like), blurry glass and floating cards (canons 08, 12), parallax on body text.
- Reduced motion: the ticker stops.
- Catalog lists only `reduced_motion_instant`; treat hover and clip reveal as allowed extras [assumption, owner to confirm].

<!-- section:typography -->
## Typography
- Fonts (canon): Source Serif 4 for headlines and long text, Source Sans 3 for UI, labels and captions, Source Code Pro for datelines and tables. Source Serif was designed as a companion to Source Sans, so the pair is safe.
- Headlines: weight 700–800, line-height at least 1.1 (h1 1.02 in tokens), slight negative tracking (−0.025em). Use italic for one emphasis word.
- Body: at least 16px (never smaller, canon rule), line-height about 1.6, `text-wrap: pretty` to avoid lonely last words.
- Headlines and decks: use `text-wrap: balance` so lines have similar length.
- Kickers and datelines: small caps or uppercase mono, 12px, letter-spacing 0.06em.
- Hierarchy is made by size and weight, not colour. A front page uses at least 3 clear headline sizes: lead, secondary, brief.
- Source Serif 4 and Source Sans 3 cover Cyrillic.

<!-- section:color -->
## Color
- Paper (`bg`): warm newsprint ivory. Surface: one step darker, for boxes and the rail.
- Ink (`text` and `border`): near-black. The rules use ink colour, so they read like printed lines.
- Accent: vermilion red (`accent`), used for kickers, the live/new marker, one link state or the drop cap. A red accent on black and ivory is a classic newspaper move [assumption].
- `accent_2` (deep blue): use for links inside long text, or for charts.
- Keep colour rare. One accent per view.

<!-- section:surfaces -->
## Surfaces
- Radius is 0 everywhere: cards, buttons, inputs and badges (canon tokens). Printed paper has square corners.
- Separation comes from rules, not shadows:
  - 2px double or solid rule under the masthead;
  - 1px vertical rules between columns (`column-rule` or borders);
  - 1px horizontal rules between stories.
- Shadows: none. Glass: none.
- Boxes (newsletter, sidebars): a 1px ink border with a surface fill.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Light base prompt (canon): "Editorial broadsheet architectural photography of {subject} on archival bone-ivory paper tone, dramatic natural daylight chiaroscuro, crisp stone and dark walnut textures with subtle vermilion editorial accent, 35mm Leica film look, unmarked surfaces".
- Dark base prompt (canon): "Low-key editorial broadsheet still life of {subject} on dark espresso slate, sculpted directional key light, brushed bronze and ink tones, crisp vermilion highlight, 35mm medium-format grain".
- Per block:
  - lead image 16:9 or 3:2, the subject off-centre to leave room for a caption;
  - story image 3:2;
  - plate 4:5 for a monograph;
  - author portrait 3:4 (canon portrait prompt).
- Keep one photographic voice for the whole site: same light and same film grain. A newspaper looks edited because its photos agree [assumption].
- Never put text in images. Headlines and captions are HTML.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`. Landing preset: `classic_corporate`.
- Options for X:
  - Columns of stories: CSS Grid with explicit spans (8+4, 6+3+3). Why: every story keeps a fixed place.
  - Multi-column body text: CSS `columns` with `column-rule`. Only for short blocks (briefs, footnotes), never the whole article, because of the scroll-up problem.
  - Monograph text block: a 9-column grid, content in columns 2–7.
  - Drop cap: `initial-letter` plus a float fallback.
  - Ticker: CSS keyframes, no library.
  - Reveal: CSS scroll-driven in `@supports`, otherwise no animation.
- Avoid: GSAP and Lenis for this canon. They add weight and scroll feel that fight reading [assumption].

<!-- section:seo -->
## SEO / AEO / GEO
- This style is text-first, so it suits answer engines well.
- Article pages emit `Article` or `NewsArticle` JSON-LD with `headline`, `datePublished` (ISO 8601 with timezone), `dateModified` and `author` as a `Person` with a profile URL.
- Optional `speakable` with `cssSelector` for the headline and standfirst. Google marks it beta.
- Show the byline and the dates in HTML, matching the JSON-LD. Readers and engines trust dated, signed text.
- Use real `<figure>` and `<figcaption>`, `<blockquote cite>`, `<time datetime>` and an ordered list for footnotes.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Multi-column body text forces readers to scroll up and down. Fix: CSS columns only for short blocks; long articles in one 66ch column.
- Drop caps and `initial-letter` can confuse screen readers if built from images or split letters. Fix: real text with CSS only.
- Dense front pages overload mobile. Fix: lead story first, then a simple list; hide nothing important.
- Serif body at small sizes on low-DPI screens. Fix: body ≥ 17px, line-height ≥ 1.5.
- Thin ink rules as the only separators. Fix: also use spacing and headings.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): source_code_pro, source_sans_3, source_serif_4.
- JS: none (CSS only).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- No video or frame sequences (asset class C is deferred).
- Body text is at least 16px and meets the canon contrast (text/bg 17.6:1).
- A ticker or marquee must pause on hover, on focus and under reduced motion (WCAG 2.2.2 pause, stop, hide).
- No text inside generated images.
- Everything works offline and static. No third-party font CDNs: fonts are self-hosted @fontsource packages.
