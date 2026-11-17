Let me analyze this request carefully. The user wants a production-ready single-page landing for «ЦЕХ №4» — an industrial prototyping bureau in Yekaterinburg doing 5-axis CNC metalworking (titanium, inconel, hardened steels) and small-series pressure casting.

Design canon: Neo-Brutalism — constructivist geometry, hard 2px borders, offset flat shadows without blur, warm limestone/craft background, charcoal text, signal-yellow and cinabar red accents. All colors via OKLCH tokens in :root. No purple gradients, no rounded fluffy cards, no stock photos, no anglicisms.

Sections:
1. Brutalist hero with production passport (tolerances per GOST 25346 / IT6, roughness Ra 0.4, dimensions up to 1200×800×600 mm) and vector isometric drawing of turbine impeller (inline SVG with dimensional chains).
2. Interactive cost/timeline calculator for batch (alloy selection: ВТ6 titanium / 12Х18Н10Т / Д16Т / 40Х; precision class IT6–IT10; batch size 1–500 pcs; calculation of workpiece mass, machine-hours and price in rubles without page reload).
3. Machine park table and technological reworks (3 complexes: 5-axis milling center, wire EDM, vacuum casting in silicone and TPA) with real engineering characteristics.
4. Quality control (CMM Carl Zeiss, radiography, melting passports).
5. FAQ (5 specific questions and answers for chief engineers and procurement department) and application form for calculation by STEP/IGES model (client-side validation).
6. Footer with requisites.

Requirements:
- Vanilla HTML/CSS/JS only, 0 external network requests.
- Semantic HTML5, exactly one h1, ARIA markup, contrast ≥ 7:1, full keyboard accessibility, prefers-reduced-motion.
- Performance: CLS 0, explicit sizes for all SVG and blocks.
- SEO/GEO: title, meta description, canonical, Open Graph; JSON-LD @graph with Organization, Product (for 3 complexes/services), FAQPage (verbatim match with visible FAQ), BreadcrumbList; llms.txt; robots.txt.
- Security: strict CSP in meta with exact builder placeholders 'sha256-__CSP_STYLE__' and 'sha256-__CSP_SCRIPT__' (no 'unsafe-inline', no manual base64 hashes; all event handlers via addEventListener) and Cloudflare Pages _headers file with all 7 mandatory security headers (CSP with frame-ancestors 'none', HSTS max-age=63072000 includeSubDomains preload, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy).

Files: index.html, llms.txt, robots.txt, _headers.

Let me think about the design carefully. Neo-Brutalism constructivist style. This is a great fit for industrial content. Let me plan the design identity:

- Warm limestone background `oklch(0.94 0.03 90)`
- Charcoal text `oklch(0.14 0.01 260)`
- Signal yellow `oklch(0.86 0.16 90)`
- Cinabar red `oklch(0.58 0.21 30)`
- Hard borders 2px solid
- Offset flat shadows `4px 4px 0px`

Typography: I can't use external fonts (0 network requests). So I need to use system font stacks. For a constructivist industrial feel, I want a strong grotesque display face. System fonts available: I can use a stack that leans toward condensed grotesque. Let me think: for display, something like "Arial Narrow", "Helvetica Neue Condensed", system-ui. Actually for constructivist feel, condensed grotesque is good. For body, a readable grotesque. Let me define:

Display font stack: system-ui with condensed fallbacks. Actually to make it distinctive, I could use a stack like: font-family with condensed options. Let me think about what's available cross-platform without network:
- Display: a condensed grotesque stack. I'll use something like a stack that leans toward condensed grotesque. Let me define:
  - Display: system-ui with condensed fallbacks. Actually to make it distinctive, I could use a stack like: font-family with condensed options. Let me think about what's available cross-platform without network.
- Body: a readable grotesque.

Hmm. Since no external fonts, I'll rely on system fonts. Let me define a display stack that uses condensed grotesque characteristics. For constructivist feel, condensed is key. I'll define:
- `--font-display`: 'Arial Narrow', 'Helvetica Neue', 'Impact'... no, Impact is too heavy. Let me try a stack that uses system-ui but with font-stretch where supported? Actually font-stretch only works with variable fonts which we don't have. Let me just use a robust stack.

Actually, a good approach for a distinctive look without web fonts is to lean heavily on typographic treatment: uppercase, tight tracking, heavy weights, condensed where available. I'll create the display identity through treatment rather than a specific face. Let me use a stack like:

`--font-display: system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;` with heavy weights and uppercase + tight letter-spacing. That reads as brutalist.

For body, I'll use a monospace-ish for technical data (which fits industrial context) and a readable sans for prose. The technical monospace gives a nice engineering feel. So:
- `--font-mono: ui-monospace, 'Cascadia Code', 'Consolas', 'Menlo', monospace` for technical data, tables, passport values.
- `--font-body: system-ui, ...` for prose.

This gives a strong contrast between display and body. Good.

Now let me plan the page structure:

Header: sticky top bar with logo ЦЕХ №4 and nav, plus a signal-yellow "ЗАКАЗАТЬ РАСЧЁТ" button. Nav links to sections.

Hero: brutalist. Big h1. Production passport as a spec block. Isometric SVG drawing of turbine impeller with dimensional chains. The SVG needs explicit width/height to avoid CLS.

Let me design the SVG impeller. An isometric vector drawing of a milled turbine impeller (крыльчатка турбины). This is a radial impeller with blades. I'll draw it isometrically with dimensional chains (размерные цепи) — these are the dimension callouts with arrows and numbers. Let me create a technical drawing look: a grid, the impeller shape, dimension lines with arrows, tolerance annotations. This is the signature technical element.

I'll make the SVG detailed but clean. Let me think about the geometry: an impeller has a hub, blades radiating, a shroud. Isometric view. I'll draw it with lines. Let me create a reasonable technical illustration.

Calculator: interactive. Select alloy (ВТ6 титан / 12Х18Н10Т / Д16Т / 40Х), precision class IT6–IT10, batch size 1–500. Compute workpiece mass, machine-hours, price in rubles. No reload. I'll use addEventListener. The values update live.

Let me think about realistic engineering numbers. Alloys:
- ВТ6 (titanium, Ti-6Al-1Zr equivalent-ish, actually ВТ6 is a Russian titanium alloy VT6). Density ~4.5 g/cm³? Actually ВТ6 density around 4.4. Let me use realistic. Machining of titanium is slow, high machine-hours.
- 12Х18Н10Т (austenitic stainless steel, like 304/316 family). Density ~7.9 g/cm³.
- Д16Т (duralumin, Al-Cu, aluminum). Density ~2.7 g/cm³. Fast machining.
- 40Х (carbon steel, hardened). Density ~7.85 g/cm³.

The calculator computes workpiece mass based on volume, density. Machine-hours depend on alloy hardness/machining speed. Price in rubles.

Let me make the calculation logic realistic:
- Volume of workpiece: I'll estimate from a nominal bounding envelope. Maybe let user input part dimensions? Actually the request says "расчёт массы заготовки, машино-часов и цены". Let me keep it simple but realistic: part dimensions (L×W×H) plus the alloy density gives mass. Machine-hours per part depend on alloy (machining time factor). Batch size multiplies.

Let me define alloy data:
- ВТ6: density 4.5, machinability factor (slow), cost per kg, tooling wear high.
- 12Х18Н10Т: density 7.9, moderate.
- Д16Т: density 2.7, fast.
- 40Х: density 7.85, hardened, slow for hardened.

Precision class IT6–IT10 affects machine-hours (tighter tolerance = more time) and price.

Let me build the JS with a data object and a compute function. I'll compute:
- workpiece mass (kg) from dimensions × density
- machine-hours per part
- total machine-hours
- price per part and total
- lead time (days)

I'll present results in a results panel with monospace numbers.

Machine park table: 3 complexes with real specs. Use a table with table-wrap for overflow. Include columns: станок, тип, передел, зона обработки, шпиндель, точность, etc.

Quality control section: КИМ Carl Zeiss, рентгеноскопия, паспорта плавки. Cards with brutalist style.

FAQ: 5 questions with accordion (details/summary or custom with addEventListener). JSON-LD must match verbatim.

Form: STEP/IGES model application with client-side validation. Fields: name, company, email, phone, file reference (STEP/IGES), task description, batch, deadline. Validate email, required fields. Show validation messages.

Footer: requisites (ИНН, ОГРН, address, etc.) — I'll invent plausible ones but keep them clearly as the company's requisites. Actually I should be careful not to invent fake legal numbers that could be problematic. Let me use placeholder-ish but realistic-looking. Hmm, the user wants "реквизиты". I'll provide plausible requisites for a fictional company. That's fine for a demo landing. I'll include ИНН, ОГРН, address, bank details. These are fictional. Let me make them look real but note they're for a fictional entity. Actually I'll just present them as the company's data.

Let me think about the motion/signature elements:
- Scramble-decode on the h1 or section titles (technical feel) — but respect prefers-reduced-motion.
- Dimensional chain drawing animation on the SVG (line draw) — respect reduced motion.
- Offset shadow brutalist cards.
- A blueprint grid background.
- Marquee ticker of technical specs? Maybe a ticker strip with signal yellow.
- Scroll-reveal for sections.

For the interactive calculator, I'll use range slider for batch size and select buttons for alloy, segmented control for precision.

Let me think about the color palette and contrast. Charcoal `oklch(0.14 0.01 260)` on limestone `oklch(0.94 0.03 90)` gives very high contrast, well above 7:1. Signal yellow `oklch(0.86 0.16 90)` with black text — that's fine, black text on yellow gives high contrast. Cinabar red `oklch(0.58 0.21 30)` — for accents, used with black text on it or as line color. For text on red, contrast might be lower; I'll use red mainly as accent/border and for badges with black text on it, or as decorative. Actually cinabar is fairly dark; white text on it might not reach 7:1. Let me use black text on the yellow and red badges to keep contrast high, and use red as border/accent color, not as body text.

Let me plan the layout grid. The hero will be a two-column on desktop: left text + passport, right the SVG drawing. On mobile, stacked.

Let me write the CSS with design tokens. I'll set up a strong typographic hierarchy.

Let me think about the "passport" block — it's like a technical passport/spec sheet with hard borders and monospace values. Good constructivist element.

Now let me think about the SVG impeller drawing. I want it to look like a technical isometric drawing with dimension chains. Let me create an SVG with:
- A blueprint grid background (fine lines)
- The impeller rendered as an isometric assembly: hub cylinder, blades, shroud ring
- Dimension lines with arrowheads and labels (Ø, length, etc.)
- Tolerance annotations

I'll set explicit width/height and viewBox. Let me make it ~ 640×480 viewBox.

Let me design the impeller geometry. A turbine impeller (крыльчатка) typically has a hub, blades (лопатки), and a shroud. In isometric, I'll represent it as a cylinder-ish shape with blades. Let me draw it as a set of lines forming an isometric radial impeller. I'll use a constructivist approach: straight lines, offset planes.

Actually, let me make it a clean technical line drawing. I'll draw the impeller as a radial fan with blades seen from an isometric angle, plus the hub. Then dimension chains around it: overall diameter Ø, blade length, hub diameter, height.

Let me write the SVG carefully with paths. I'll define arrow markers.

Let me now think about the JS. All via addEventListener. No inline on* attributes. No style changes via JS (no element.style, setAttribute('style'), setProperty). I'll toggle classes and hidden attributes and SVG geometry attributes (d, points, x2). For the calculator, I'll update text content via textContent (allowed, not style). Good.

Wait — the rule says never mutate element.style, setAttribute('style'), or setProperty. I can use textContent updates which is fine. For the scramble decode effect, I'll change textContent. For scroll reveal I'll toggle classes. For the SVG dimension animation I might animate via CSS class toggling. Good.

Let me also implement the calculator with proper number formatting in rubles.

Let me think about the JSON-LD @graph: Organization, Product (3 products/services), FAQPage (verbatim), BreadcrumbList. I'll place it in head before </head>.

FAQPage must match visible FAQ verbatim. So I'll write the FAQ questions and answers in the HTML exactly as they appear, and mirror them in JSON-LD.

Let me draft the FAQ (5 questions for chief engineers and procurement):
1. Какие допуски вы держите на 5-осевом участке? (IT6, Ra 0.4, etc.)
2. Можно ли заказать мелкосерийное литьё под давлением без оснастки? / литьё в силикон
3. Как оформляется паспорт плавки и контроль качества?
4. Как передать модель — STEP/IGES, есть ли ограничения по размеру?
5. Какие сроки и условия оплаты для отдела снабжения? / отсрочка, НДС

Let me make them concrete and technical.

Let me now think about the _headers file. 7 mandatory headers:
1. Content-Security-Policy (with frame-ancestors 'none', placeholders)
2. Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
3. X-Content-Type-Options: nosniff
4. Referrer-Policy
5. Permissions-Policy
6. Cross-Origin-Opener-Policy
Plus X-Frame-Options? The request says "все 7 обязательные заголовки". Let me count: CSP, HSTS, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy — that's 6 named. The 7th could be X-Frame-Options (redundant with frame-ancestors) or Cross-Origin-Embedder-Policy. Let me include X-Frame-Options: DENY as the 7th. Actually the request lists them; let me ensure I cover all. The request mentions CSP with frame-ancestors 'none', HSTS, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy. That's 6 explicitly. Let me add X-Frame-Options and maybe Cross-Origin-Embedder-Policy to reach 7. Let me include:
- Content-Security-Policy
- Strict-Transport-Security
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy
- Cross-Origin-Opener-Policy
- X-Frame-Options
That's 7. Good. I'll also add Cross-Origin-Embedder-Policy? Hmm, COEP might break same-origin... but we have no cross-origin resources so it's fine. But the rule says no external resources; COEP require-corp could be fine. Let me keep it simple and not add COEP to avoid breaking. Actually let me add it as it's a good security header. Hmm but with no external resources, COEP: require-corp is safe. Let me include it. But then that's 8. The request says 7. Let me stick to the 7 that are commonly "mandatory": CSP, HSTS, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, COOP, X-Frame-Options. I'll add COEP too as bonus? Let me just include the 7 named ones plus maybe COEP. Hmm the instructions say "все 7 обязательные заголовки безопасности" and then lists CSP (with frame