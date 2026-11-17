Let me analyze the request carefully:
- Single-page landing for "Северная Мануфактура" — boutique solid oak furniture manufacturer
- Russian language
- Luxury Minimalism design
- Sections: hero, product line table, technical SVG schematic, certifications, FAQ (5 Q&A), contact form, footer
- Strict CSP with placeholders
- All four files: index.html, llms.txt, robots.txt, _headers
- No external requests, no font CDNs
- System font fallbacks for Cormorant Garamond / Playfair Display (local() references allowed)

Let me plan the structure:

1. `FILE: index.html` starting at line 1
2. `FILE: llms.txt`
3. `FILE: robots.txt`
4. `FILE: _headers`

CSP: `default-src 'self'; style-src 'self' 'sha256-__CSP_STYLE__'; script-src 'self' 'sha256__CSP_SCRIPT__'`

Design tokens in OKLCH:
- oklch(0.95 0.01 85) for background
- Warm muted tones
- Text contrast ≥ 7:1

Fonts: Cormorant Garamond / Playfair Display with local() references and system fallbacks — no external requests.

Product line table: 3 flagship models with specs
SVG schematic: mortise-and-tenon / dovetail cross-section
FAQ: 5 Q&A in Russian
Contact form: client-side validation

JSON-LD @graph: Organization, Product (3 models), FAQPage, BreadcrumbList

Let me keep the CSS and JS concise so nothing gets truncated.

Let me write the HTML carefully, keeping the CSS compact but polished.

For the fonts, I'll use local() references since Cormorant Garamond and Playfair Display may be installed locally on some machines, with system fallbacks.

Let me design the layout:
- Hero: asymmetric layout, not centered
- Product table: proper semantic table with wrapper
- SVG schematic: technical drawing style
- Certifications: badges
- FAQ: accordion
- Contact form: validation
- Footer

Colors in OKLCH:
- --bg: oklch(0.95 0.01 85)
- --surface: oklch(0.97 0.01 85)
- --ink: oklch(0.25 0.01 75) — dark enough for 7:1 contrast
- --accent: oklch(0.55 0.05 70) — warm bronze/amber
- --line: oklch(0.85 0.01 85)

Let me ensure the contrast: oklch(0.25 0.01 75) on oklch(0.95 0.01 85) should give roughly 11:1+ contrast.

For the SVG schematic, I'll draw a technical cross-section showing mortise and tenon joint.

Let me keep everything concise. The CSS needs to be complete but not overly verbose.

Let me write the files now.

For the FAQ JSON-LD, I need to match the visible FAQ verbatim.

Let me think about the 5 FAQ questions:
1. Как долго служит мебель из массива дуба?
2. Можно ли заказать нестандартные размеры?
3. Как ухаживать за мебелью из массива?
4. Каковы сроки изготовления?
5. Доставляете ли вы по России?

Let me structure the page:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Северная Мануфактура — мебель из массива дуба</title>
  <meta name="description" content="...">
  <link rel="canonical" href="https://severmanufaktura.ru/">
  <meta property="og:...">
  <meta http-equiv="Content-Security-Policy" content="...">
  <style>...</style>
  <script type="application/ld+json">...</script>
</head>
```

Let me keep CSS concise. I'll use clamp() for padding.

Let me think about the table — 3 models:
1. Обеденный стол «Карелия» — solid oak
2. Буфет «Онего» — cabinetry
3. Архитектурная столярка «Соловки» — joinery

Let me write the SVG schematic. It should show a mortise-and-tenon joint cross-section with technical labels.

Now let me write everything carefully, ensuring no truncation.

For the contact form — client-side validation with addEventListener.

Let me make sure the JS is concise.

Let me finalize the plan and write all files.

One thing: I need to make sure the JSON-LD FAQ matches the visible FAQ verbatim. So I'll write the FAQ in HTML first, then copy into JSON-LD.

Let me be careful about the table wrapper.

For decorative absolute positioned shapes, constrain within viewport.

Let me write now.