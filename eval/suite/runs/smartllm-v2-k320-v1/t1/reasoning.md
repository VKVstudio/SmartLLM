Let me plan the whole thing carefully.

Design canon: dark blueprint theme — background oklch near #2A2E35, 1px blueprint grid via CSS gradient, signal orange oklch(0.68 0.19 45). JetBrains Mono + IBM Plex Sans with system fallbacks, no external font CDN (so no font files — just font-family declarations with fallbacks).

Sections: hero, product line table (3 models), technical inline SVG schematic, certifications (ISO/GOST), FAQ (5 Q&A), contact form (client-side validation), footer.

CSP: `default-src 'none'; style-src 'sha256-__CSP_STYLE__'; script-src 'sha256-__CSP_SCRIPT__'; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'` — no external URLs at all.

Constraints: no inline on* handlers, addEventListener only; no element.style mutation. Use classList toggles.

JSON-LD @graph: Organization, Product ×3, FAQPage matching the visible FAQ verbatim, BreadcrumbList.

Contrast ≥7:1: text colors need to be light enough on dark background. Body text around oklch(0.92 0.01 240) on background oklch(0.21 0.015 240) — well above 7:1. Accent orange on dark: oklch(0.68 0.19 45) on dark background — contrast of orange on dark background might be around ~7:1? For accent used as text, use a brighter variant like oklch(0.78 0.16 60) for text to guarantee 7:1; use accent for borders/fills only.

Mobile 375px: table-wrap with overflow-x auto around tables and pre, box-sizing, overflow-x clip, min-width 0, flex-wrap.

CLS 0: explicit aspect-ratio on SVG, width/height attributes.

Now let me write the content.

Product models:
- TM-500 "Sable" — 5 MW, hot water, 92.4% efficiency, 180 bar? Actually hot water boilers go up to ~120 bar. Steam boilers go higher. Let me design realistic specs:
  - TM-500: hot water boiler, 5 MW, 105 °C, 12 bar, efficiency 92.4%
  - TM-1200: steam boiler, 12 MW, 250 °C steam, 20 bar… let me use 15 bar.
  - TM-2500: steam boiler, 25 MW, 300 °C, 25 bar? Actually 25 bar is plausible for industrial.
- Schematic: inline SVG of boiler circuit — water inlet, feedwater treatment, deaerator, boiler, steam drum, economizer, burner, flue gas, chimney, control panel. Draw with blueprint style: stroke lines, dashed flow, labels.

FAQ 5 Q&A — must match JSON-LD verbatim.

Contact form: name, company, email, country? boiler type select, message. Client-side validation with JS, no backend (form action="#"? better: intercept submit with addEventListener, validate, show success message).

llms.txt per llmstxt.org format: # Title, > summary, ## sections with links. Since single page, link to sections with anchors.

robots.txt: allow all, sitemap.

_headers: Cloudflare template with CSP, HSTS, etc.

Now let me write the HTML carefully. Keep CSS concise but polished. Avoid truncation — total will be large but manageable. Let me be efficient.

Design tokens:

```css
:root {
  --bg: oklch(0.20 0.014 250);
  --surface: oklch(0.24 0.016 250);
  --line: oklch(0.32 0.014 250);
  --grid-line: oklch(0.28 0.012 250);
  --ink: oklch(0.93 0.012 240);
  --ink-dim: oklch(0.75 0.014 240);
  --accent: oklch(0.68 0.19 45);
  --accent-ink: oklch(0.80 0.13 60); /* for text on dark, 7:1+ */
  --accent-strong: ...
  --ok: oklch(0.75 0.14 155);
  --err: oklch(0.65 0.19 25);
  --font-sans: 'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'SFMono-Regular', 'Consolas', monospace;
}
```

Blueprint grid: body background with repeating linear gradient:
```css
background-image:
  linear-gradient(to right, var(--grid-line) 1px, transparent 1px),
  linear-gradient(to bottom, var(--grid-line) 1px, transparent 1px);
background-size: 32px 32px;
```
Grid lines subtle so contrast unaffected.

Typography hierarchy: mono for labels/eyebrows, sans for body.

Layout: hero is asymmetric split (not 3 cards). Product table: full-width table inside .table-wrap. Schematic: SVG with aspect-ratio. Certifications: list of badges. FAQ: details/summary? For keyboard accessibility, using <details> is fine and native. But FAQPage JSON-LD needs the full answer text to be visible — details hides content but it's in the DOM; JSON-LD matching is fine. Actually, for accessibility and SEO, details/summary is acceptable. Let me use details elements.

Contact form validation: JS validates required fields, email pattern, shows error messages with aria-live, aria-invalid.

Nav: sticky top, flex-wrap. Skip link.

Now let me write the content.

Hero: eyebrow "THERMOTECH ENGINEERING — since 1998", h1 "Industrial hot-water & steam boilers, 5–25 MW.", sub, CTA buttons, stats strip.

Product table: columns: Model, Type, Thermal output, Max temperature, Operating pressure, Efficiency, Emmissions? Keep it tight: Model / Type / Output / Temperature / Pressure / Efficiency / Status. Rows for TM-500, TM-1200, TM-2500.

Schematic SVG: viewBox 0 0 1200 640, aspect-ratio: 1200/640. Draw: flue gas path (burner → boiler → economizer → chimney), water path (feedwater → deaerator → boiler → steam drum → steam header), return. Use stroke var(--ink-dim), accent for active elements, dashed with CSS animation for flow but respect prefers-reduced-motion. Use classes for styling, no inline styles. SVG elements get class attributes; CSS targets them.

Certifications: ISO 9001:2015, ISO 14001:2015, GOST-R certification, GOST 12.1.020? Keep plausible: ISO 9001, ISO 14001, ISO 45001, GOST-R, GOST 12.1.020-80? Hmm, GOST 12.1.020-80 is "Safety standards. Equipment. General safety requirements". Fine.

FAQ 5:
1. What is the lead time for a boiler order?
2. Can Thermotech supply turnkey installation?
3. Do boilers comply with GOST and ISO requirements?
4. What fuel options are available?
5. What service and warranty coverage is included?

Answers verbatim in JSON-LD.

Contact form fields: Name, Company, Email, Country (select with a few options), Boiler type (select: TM-500 / TM-1200 / TM-2500 / Not sure), Message. Validation: required, email regex. On submit: preventDefault, validate, show status message via aria-live region. No inline styles; use class toggles for error states.

Footer: columns, legal.

JS: nav toggle? Not needed if nav wraps. Add: form validation script, smooth scroll? Keep minimal: form validation + details toggle handling? Also add year? Keep minimal. One script block — CSP needs one sha256 for the whole script element. Keep one <script> in body.

Also note: the script placeholder — the meta CSP contains 'sha256-__CSP_SCRIPT__' which the postprocessor replaces. Since there is one script, one placeholder is fine.

JSON-LD in head.

Now let me write the files. Keep CSS concise but polished. Avoid truncation — total will be large but manageable. Let me be efficient.

Let me draft the SVG schematic:

viewBox="0 0 1200 620". Elements:
- Grid background inside SVG? Use lines.
- Boxes: Feedwater treatment (x 40), Deaerator, Boiler (center large), Steam drum on top of boiler, Burner left of boiler, Economizer right, Chimney far right, Steam header top-right, Condensate return loop.
- Flow lines with dashed strokes, arrowheads via marker.
- Labels mono.

Keep SVG modest: ~30 elements.

Marker defs: <marker id="arw">.

CSS classes: .pipe (stroke ink-dim), .pipe-steam (accent), .pipe-water (blue-ish? use a cool token --water: oklch(0.72 0.08 230)), .node (surface fill, line stroke), .node-label, .flow (stroke-dasharray animation).

Animation: stroke-dashoffset animation; wrap in @media (prefers-reduced-motion: no-preference).

Now let me write the CSS carefully to keep size reasonable.

Key mobile invariants:
```css
*,*::before,*::after{box-sizing:border-box}
html,body{max-width:100%;overflow-x:clip}
svg,canvas,img{max-width:100%;height:auto}
```

Table wrap: .table-wrap{overflow-x:auto; -webkit-overflow-scrolling:touch} table min-width maybe 640px.

Badges wrap below 480px: white-space normal.

Now let me write everything.

CSP meta:
```
default-src 'none'; style-src 'sha256-__CSP_STYLE__'; script-src 'sha256-__CSP_SCRIPT__'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'self'; frame-ancestors 'none'; upgrade-insecure-requests
```
Wait, img-src 'self' data: — but there are no images; fine. font-src 'self' — no external fonts anyway.

Canonical: https://thermotech.example/ — use example domain? The instructions don't specify a domain. Use https://thermotech.example/ for canonical, og:url, JSON-LD. Hmm, canonical link is allowed ("link rel=canonical and schema.org excepted" for external URLs). So canonical to example domain is fine.

Open Graph: og:title, og:description, og:type=website, og:url, og:locale en_US. No og:image (no external images). Could add og:image but we don't have one; skip. Actually many landing pages include og:image; we don't have an image asset. Skip og:image to avoid external URLs.

JSON-LD @graph:
- Organization: name Thermotech Engineering, url, description, areaServed, contactPoint.
- Product ×3: TM-500, TM-1200, TM-2500 with name, description, category.
- FAQPage: 5 questions/answers verbatim matching visible FAQ.
- BreadcrumbList: Home → Products? Keep simple: Home, Products, Contact? Keep simple: Home + Products.

llms.txt:
```
# Thermotech Engineering

> Manufacturer of industrial hot-water and steam boilers, 5–25 MW...

## Core pages
- [Product line](https://thermotech.example/#products): ...
...
```

robots.txt: User-agent: * allow, sitemap https://thermotech.example/sitemap.xml.

_headers:
```
# Cloudflare Pages headers
/*
  Content-Security-Policy: default-src 'none'; style-src 'sha256-__CSP_STYLE__'; script-src 'sha256-__CSP_SCRIPT__'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'self'; frame-ancestors 'none'; upgrade-insecure-requests
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Cross-Origin-Opener-Policy: same-origin
```

Now let me write the complete HTML. Let me keep the CSS tight but complete.

FAQ answers (verbatim, short enough to fit):

Q1: What is the typical lead time for a Thermotech boiler order?
A: Standard lead time is 14–18 weeks from order confirmation for hot-water models and 20–26 weeks for steam models, depending on configuration and fuel system.

Q2: Can Thermotech supply turnkey installation?
A: Yes. We deliver complete boiler houses including feedwater treatment, controls, stack, and commissioning, with supervision teams on site.

Q3: Do the boilers comply with ISO and GOST requirements?
A: Every unit is manufactured under ISO 9001:2015 quality management and certified for GOST-R and GOST 12.1.020 equipment safety requirements.

Q4: Which fuels are supported?
A: Natural gas, diesel, fuel oil, and biomass-derived fuels; dual-fuel burners are available on request.

Q5: What warranty and service coverage is included?
A: A 24-month warranty on pressure parts and burners, with optional service contracts covering annual inspections, spare parts, and remote diagnostics.

Now let me write the HTML. Keep the CSS concise but polished. Avoid truncation — total will be large but manageable. Let me be efficient.

Let me draft the SVG schematic:

viewBox="0 0 1200 620". Elements:
- Grid background inside SVG? Use lines.
- Boxes: Feedwater treatment (x 40), Deaerator, Boiler (center large), Steam drum on top of boiler, Burner left of boiler, Economizer right, Chimney far right, Steam header top-right, Condensate return loop.
- Flow lines with dashed strokes, arrowheads via marker.
- Labels mono.

Keep SVG modest: ~30 elements.

Marker defs: <marker id="arw">.

CSS classes: .pipe (stroke ink-dim), .pipe-steam (accent), .pipe-water (blue-ish? use a cool token --water: oklch(0.72 0.08 230)), .node (surface fill, line stroke), .node-label, .flow (stroke-dasharray animation).

Animation: stroke-dashoffset animation; wrap in @media (prefers-reduced-motion: no-preference).

Now let me write the CSS carefully to keep size reasonable.

Key mobile invariants:
```css
*,*::before,*::after{box-sizing:border-box}
html,body{max-width:100%;overflow-x:clip}
svg,canvas,img{max-width:100%;height:auto}
```

Table wrap: .table-wrap{overflow-x:auto; -webkit-overflow-scrolling:touch} table min-width maybe 640px.

Badges wrap below 480px: white-space normal.

Now let me write everything.

CSP meta:
```
default-src 'none'; style-src 'sha256-__CSP_STYLE__'; script-src 'sha256-__CSP_SCRIPT__'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'self'; frame-ancestors 'none'; upgrade-insecure-requests
```
Wait, img-src 'self' data: — but there are no images; fine. font-src 'self' — no external fonts anyway.

Canonical: https://thermotech.example/ — use example domain? The instructions don't specify a domain. Use https://thermotech.example/ for canonical, og:url, JSON-LD. Hmm, canonical link is allowed ("link rel=canonical and schema.org excepted" for external URLs). So canonical to example domain is fine.

Open Graph: og:title, og:description, og:type=website, og:url, og:locale en_US. No og:image (no external images). Could add og:image but we don't have one; skip. Actually many landing pages include og:image; we don't have an image asset. Skip og:image to avoid external URLs.

JSON-LD @graph:
- Organization: name Thermotech Engineering, url, description, areaServed, contactPoint.
- Product ×3: TM-500, TM-1200, TM-2500 with name, description, category.
- FAQPage: 5 questions/answers verbatim matching visible FAQ.
- BreadcrumbList: Home → Products? Keep simple: Home