# Canon 17_fintech_institutional: Institutional Fintech / Precision Ledger

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/17_fintech_institutional.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A precise, trustworthy ledger look: pale slate background, crisp white 8px cards with fine elevation, midnight navy text, one blue accent and an emerald "verified" accent, dense but tidy tables with tabular numbers.
- It works because finance and legal buyers judge risk: calm order, exact numbers, visible licences and clear terms say "safe and regulated". Decoration would look like hype.
- Good fits: fintech, banks, payments, insurance, legal firms, accounting, enterprise B2B.
- Weak fits: lifestyle, food, kids, art, festivals.
- Mood: trustworthy, exact, sober. Default polarity: light. Dark: deep navy for dashboards.
- Avoid (canon): playful springs, marquees, neon glow, fake animated stock tickers, poster-style 0px layouts.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 20px gutter, container 1312px, section padding 84px, card padding 24px (tokens). Density medium-high (dial 6).
- Typical landing order:
  - top bar (optional): licence/regulator line, language, login;
  - nav (product groups, pricing, security, company) + primary CTA ("Open an account", "Book a demo");
  - hero: h1, one-line value, CTA pair, trust row (regulator, certifications, client logos);
  - key figures band (assets, clients, uptime) with dates and sources;
  - product cards (3–4);
  - pricing/fees table and comparison;
  - security and compliance section (encryption, audits, certifications);
  - case studies; FAQ; legal disclosures; footer with full legal entity, licence numbers, addresses.
- Tables are first-class content, not images.
- Mobile: cards stack; wide tables either stack into rows-as-cards or scroll in their own box with a sticky first column (canon).

<!-- section:hero -->
## Hero
- h1: Wix Madefor Display 700, `clamp(2rem, 1.583rem + 1.85vw, 3.25rem)` (52px desktop, 40 tablet, 32 mobile), line-height 1.12, tracking −0.025em, measure about 24ch.
- Option 1, "Split with product" (default): text 6 columns, a real product screenshot or B architectural photo in a white card.
- Option 2, "Figures hero": h1 + CTA, then 3–4 key numbers in cards right under it. Pick it for B2B and asset managers.
- Option 3, "Calculator hero": h1 + a small, honest calculator (fees, savings, rate) with assumptions stated. Pick it for lending, savings, payments.
- Trust row under the CTA: regulator name and licence number as text, certifications (ISO 27001, SOC 2, PCI DSS) only if real.

<!-- section:blocks -->
## Blocks
- Card: white, 8px radius, 1px border, two-stop soft elevation (tokens). Hover: border turns accent and the shadow deepens slightly (canon).
- Data table: `<table>` with `<caption>`, `<th scope>`, right-aligned numbers, `font-variant-numeric: tabular-nums`, zebra rows, units in headers (canon).
- Pricing/fees: every fee and condition visible; no "from" prices without the full table.
- Status/verified: emerald icon + word ("Verified", "Regulated"), never colour alone.
- Disclosures: short readable summary plus "Full terms" link; risk warnings next to the product, not only in the footer.
- Charts: simple line/bar with labelled axes and a data table alternative.

<!-- section:motion -->
## Motion
- Motion budget: very low (dial 3); catalog motion `reduced_motion_instant` only. Tokens: ease `cubic-bezier(0.2,0,0,1)`, 180ms, stagger 25ms.
- Options (class A):
  - Hover: border to accent + shadow deepen (canon).
  - Press: `scale(0.99)`.
  - Entrance: optional fast 10px opacity entrance once (canon); no parallax.
- No JS motion library. CSS transitions only.
- Reduced motion (canon): 0ms, instant layout.

<!-- section:typography -->
## Typography
- Display: Wix Madefor Display Variable 600–700.
- Body: IBM Plex Sans Variable 16px, line-height 1.55, measure 60–72ch. Tables 14–15px.
- Mono: IBM Plex Mono for account numbers, IBAN, codes, API snippets.
- Numbers: `tabular-nums` everywhere (prices, metrics, tables) (canon). Format money and percentages with `Intl.NumberFormat` for the page locale and currency.

<!-- section:color -->
## Color
- Light (default): slate `bg` `oklch(0.984 0.003 252)`, white `surface`, navy text `oklch(0.175 0.022 256)`, blue `accent` `oklch(0.455 0.152 258)`, emerald `accent_2` `oklch(0.465 0.092 162)` for verification, `border` `oklch(0.845 0.012 252)`.
- Dark: navy `bg` `oklch(0.138 0.018 256)`, `surface` `oklch(0.184 0.020 256)`, pale text, light blue `accent` `oklch(0.735 0.132 244)`.
- Red and green for gains/losses always with a sign (+/−) and arrow, never colour alone.

<!-- section:surfaces -->
## Surfaces
- Radius 8px cards, 6px buttons and inputs, 4px badges; 1px borders (tokens).
- Light shadow: `0 1px 2px rgba(10,17,26,0.05), 0 8px 20px -10px rgba(10,17,26,0.06)`.
- No blur, no glow, no textures.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Light base prompt (canon): "Architectural Swiss-bank editorial photograph of {subject}, precision brushed architectural glass, cool white granite, and subtle midnight navy steel geometry under crisp daylight, 50mm tilt-shift lens, clean blank surfaces".
- Dark base prompt (canon): "Precision institutional architectural night study of {subject} in smoked curtain-wall glass and midnight navy-slate steel, calm disciplined sky-blue and emerald interior illumination, 50mm lens, clean blank surfaces".
- Team portrait (canon): vertical 3:4 executive portrait, navy or charcoal attire, even softbox light.
- Prefer real product UI screenshots over stock. Never fake charts or numbers in images.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Preset: `classic_corporate` only.
- Calculators: small vanilla JS island; show the formula and assumptions; results announced with `aria-live="polite"`.
- No third-party tracking before consent (finance sites are audited for this).

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: `FinancialService` or `LegalService` with legal name, address, `identifier` (licence/registry number); `FinancialProduct`/`LoanOrCredit` with real rates; fee tables as HTML so answer engines can quote them.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Dense tables overflow on phones. Fix: rows become cards below 768px, or scroll inside the table box with a sticky first column and a visible hint.
- Small grey table text fails contrast. Fix: table text ≥ 14px and ≥ 4.5:1; zebra rows must not lower contrast.
- Hidden fees and fine print erode trust and may break consumer rules. Fix: fees and risks next to the offer, plain language.
- Long sign-up forms. Fix: steps with progress, save state, explain why each personal field is needed.
- Login and 'Open account' compete. Fix: one primary CTA; login is a secondary link in the top bar.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): ibm_plex_mono, ibm_plex_sans, wix_madefor_display.
- JS: none (CSS only).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- `tabular-nums` on every number in prices, metrics and tables.
- Licence/regulator info and full legal entity as text.
- No fake tickers, charts or numbers; every figure has a date or source.
- Gains/losses never by colour alone.
- No marquees, parallax or playful springs.
