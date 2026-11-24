# Canon 04_hyper_minimal_speed: Hyper-Minimalist Technical / Speed-First

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/04_hyper_minimal_speed.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- This style is a fast, quiet reading page. Speed is the main feature. It is built from text, thin dividers and code blocks, with almost no decoration.
- It works because developers and technical buyers judge a product by how fast and clear its docs are. Fast pages feel trustworthy, and slow pages lose users on weak connections.
- Real references:
  - McMaster-Carr: server-rendered HTML, inline critical CSS, cached and prefetched pages;
  - TigerBeetle docs: no breadcrumbs, no TOC chrome, no animations, a service worker caches pages;
  - Vercel Geist: neutral type and a strict grid.
- Good fits: documentation, devtools, APIs, SaaS docs and changelogs, engineering specs, status pages.
- Weak fits: brand storytelling, lifestyle, fashion, anything that sells a feeling more than facts.
- Mood: clinical, efficient, honest. Default polarity: light. Dark is fine for devtools.

<!-- section:structure -->
## Structure
- The core is a "reading spine": one text column of about 68ch, no boxed cards, and 1px horizontal dividers between parts (canon tokens).
- Grid: 12 columns, 16px gutter, container 1120px, section padding 56px (tokens). This is denser than other canons on purpose.
- Typical docs page:
  - top bar: name, search, 3–5 links, version tag;
  - left sidebar (desktop): a list of pages, current page in bold or with an accent bar;
  - main column: h1, a one-line summary, then content;
  - right column (optional, wide screens): "On this page" heading links;
  - footer: one line (edit link, version, licence).
- Typical landing page in this style:
  - one short hero (no 100vh, see Hero);
  - a benchmark or "facts" table;
  - a code example;
  - 3–6 short feature rows separated by dividers;
  - a plain CTA row.
- Content types (from the Diátaxis docs model): tutorials, how-to guides, reference and explanation. Keep them on separate pages, because readers come with different goals.
- Mobile: one column. The sidebar becomes a menu button at the top. The page stays the same reading spine.

<!-- section:hero -->
## Hero
- Option 1, "Docs header":
  - Content: an h1 (40px desktop, tokens), a 1–2 line summary, two links ("Get started", "API reference").
  - Pick it for a docs home.
- Option 2, "Command hero":
  - Content: the h1, a one-line promise, and a copyable install command in a mono code block (`npm i …`) with a copy button.
  - Pick it for a CLI, library or SDK.
- Option 3, "Benchmark hero":
  - Content: the h1 plus a small table with 3–4 numbers (latency, size, score) in tabular figures (canon: "format all benchmarks in tabular-nums").
  - Pick it for a performance product.
- Avoid a giant 100vh hero with empty padding (canon rule). It hides the content the reader came for.
- Images in the hero are optional. If you use one, keep it small (B, under ~60 KB AVIF) so the text stays the LCP element [assumption].

<!-- section:blocks -->
## Blocks
- Each block is separated by a 1px divider. None of them is a card.
- Text section: h2, paragraphs and lists inside 68ch.
- Code block: mono, `surface` background, radius 0, a copy button, the language label at the top right.
- Callout (note / warning): a 2px left border in the accent or warning colour, a short bold label, no icon images.
- Reference table: real `<table>`, `tabular-nums`, sticky header on long tables, horizontal scroll on mobile.
- Feature row: an h3 and one sentence on the left, a short code or number on the right.
- Changelog entry: date (mono), version, a list of changes.
- Product image block (optional): one precise studio photo (B) on a white or charcoal background.
- Prev / next links at the end of a docs page.

<!-- section:motion -->
## Motion
- Motion budget: almost zero (dial 2). The catalog marks this canon "Zero-Motion".
- Options (A only, all instant or very short):
  - Hover: text or border colour shift only, no transform (canon). 100ms, ease `cubic-bezier(0.2,0,0,1)`.
  - Press: instant background step.
  - Copy button: the label changes to "Copied" for about 1.5s.
- Avoid:
  - scroll listeners and reveal animations (the canon says 0 scroll listeners and 0 reveal delays), because they delay content;
  - stagger delays and parallax;
  - glass blur and ambient meshes, because they cost paint time.
- No class C here: no video, no animated backgrounds.
- Reduced motion: nothing changes, because almost nothing moves.

<!-- section:typography -->
## Typography
- Fonts (canon): Geist for headings and body, Geist Mono for code and numbers. Geist is a neutral grotesk (OFL licence); Geist Sans and Mono cover Cyrillic.
- Sizes: h1 40px, weight 600, tracking −0.025em; body 16px; code 14px [assumption].
- Line length: about 68ch. Long lines tire the eye; very short lines break technical text too often.
- Use `tabular-nums` for every number in tables and benchmarks, so digits line up.
- Few weights: 400 and 600 are enough.
- Option: use the system font stack instead of Geist when the speed budget is extreme. It saves one or two font files [assumption].

<!-- section:color -->
## Color
- White or near-white background, near-black text, light grey `surface` for code and tables.
- `accent` (blue): links and the current page marker. `accent_2` (green): success, "passing", positive deltas.
- Keep colour functional. Every coloured thing should mean something (a link, a state, a warning).
- Dark version: near-black background, light text, the same accents.

<!-- section:surfaces -->
## Surfaces
- Radius: cards 0 (there are no cards), buttons and inputs 4px, badges 3px (tokens).
- Borders: 1px light grey dividers. No boxes around sections.
- Shadows: none. Blur: none.
- Focus ring: clear and visible, because keyboard users rely on docs.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Images are rare. Use them only for a product page or the landing hero.
- Light base prompt (canon): "Minimalist technical studio photograph of a single precision matte-black anodized aluminum instrument resting on a crisp white cyclorama, clinical even softbox illumination, 50mm, clean blank unmarked surface".
- Dark base prompt (canon): "Precision technical studio photograph of a single matte graphite server chassis and optical fiber patch on flat dark charcoal cyclorama, single crisp edge highlight, 50mm".
- Sizes: 16:9 or 3:2, served as AVIF/WebP with explicit `width` and `height` to keep CLS at 0.
- Diagrams are better as inline SVG or HTML than as images: they stay sharp, small and searchable [assumption].

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Catalog: default `html5_esm`; npm options: `astro`. Landing preset: `classic_corporate`.
- Performance targets (Core Web Vitals, 75th percentile): LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1.
- Speed budget: fit the HTML and critical CSS of the first screen into about 14 KB compressed. That is what arrives in the first network round trip.
- Options for each need:
  - CSS: one small inlined stylesheet. Why: no extra request before first paint.
  - JS: none by default. Add only small modules for search, copy buttons or theme switch.
  - Search: a prebuilt static index loaded on demand [assumption].
  - Fast navigation: prefetch likely next pages (Speculation Rules or `<link rel="prefetch">`).
  - Offline docs: an optional service worker that caches pages.
  - Fonts: self-hosted WOFF2, preload only the one used above the fold, `font-display: swap`.
- Avoid: animation libraries, GSAP, Lenis, client-side routers and big UI frameworks. They add bytes and work before the text appears.

<!-- section:seo -->
## SEO / AEO / GEO
- Docs are the content answer engines quote most. Write one clear question-like h2 per topic and answer it in the first sentence [assumption].
- Use real `<code>`, `<pre>`, `<table>` and `<dl>` markup.
- Add `TechArticle` or `Article` JSON-LD with `dateModified` on docs pages, and `SoftwareApplication` on the product page [assumption].
- Publish `llms.txt` with links to the key docs pages.
- Speed itself helps: Core Web Vitals are a measured page-experience signal.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Borderless layout can hide what is clickable. Fix: underline links, give buttons a fill or border, clear hover/focus.
- Dense sidebars on mobile. Fix: collapse to a labelled menu button; keep search reachable at the top.
- Long code blocks overflow. Fix: horizontal scroll inside the block, a copy button with a visible 'Copied' state announced via `aria-live`.
- Zero motion still needs feedback. Fix: instant colour change on hover/press and visible focus.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): geist, geist_mono.
- JS: none (CSS only).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- No video or frame sequences (asset class C is deferred).
- Visible focus states and keyboard navigation everywhere.
- Every image has explicit size attributes (CLS 0).
- Static and offline: self-hosted fonts, no third-party scripts.
