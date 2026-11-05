Let me build this carefully. Key challenge: strict CSP with sha256 hashes for every inline script and style. I need to compute hashes of the exact inline script/style contents. I can use the shell tool to do that.
Plan:
Write index.html with inline critical CSS in a <style> block and inline JS in <script> blocks.
Compute sha256 hashes of exact content between tags using a script.
Insert hashes into CSP meta tag and _headers.
To avoid hash mismatch churn, I should generate the HTML via a build script in the sandbox: write CSS file, JS file(s), then a Node/Python script that assembles index.html with CSP hashes computed. That's robust. Then I output the final files in fenced code blocks.
Let me check the sandbox for python3/node.
Design considerations:
Dark industrial theme with blueprint grid 1px #2A2E35 (as OKLCH token — note the canon says grid #2A2E35 but all colors as OKLCH tokens; I'll convert #2A2E35 to OKLCH ≈ oklch(0.28 0.012 251) roughly. Let me compute: #2A2E35 → rgb(42,46,53). OKLCH approx: L ≈ 0.28, C ≈ 0.012, h ≈ 258. I'll compute precisely with a script maybe. Let me just compute oklab conversion in python to get accurate tokens for the hex colors I want.
Contrast ≥ 7:1: body text on dark background needs to be high. Use near-white text oklch(0.95 ...) on bg oklch(0.17 ...). Signal orange accent oklch(0.68 0.19 45) — contrast against dark bg: L 0.68 → relative luminance? Let me compute. oklch(0.68 0.19 45) is roughly a strong orange, maybe #E5651? Let me compute with python (oklab to srgb). Contrast vs bg #10131a-ish likely ~7:1? Let me check numerically. Orange at L=0.68 has Y ≈ maybe 0.26 → luminance ~0.26. bg with L=0.17 → Y≈0.024. Contrast = (0.26+0.05)/(0.024+0.05) ≈ 4.3. Not 7:1. So orange must not be used for body text; only for accents, borders, large headings, and non-text elements. Requirement says "text contrast ≥ 7:1" — I'll ensure all text uses tokens with ≥7:1, and orange used only for graphical accents / large display text where possible... but large text also counts? The requirement says text contrast ≥7:1. Safer: use orange only for non-text graphics (grid lines, markers, borders, icons, rules) and for text use a lighter "signal tint" token, e.g., oklch(0.85 0.11 60) for any orange-tinted text, ensuring ≥7:1. Actually for headings I could use a brighter orange token derived from accent: --accent-ink: oklch(0.82 0.14 60). Let me compute contrast numerically in python for chosen tokens and adjust.
Let me define palette:
--bg-0: oklch(0.16 0.015 255) (deep blue-black)
--bg-1: oklch(0.21 0.015 255)
--bg-2: oklch(0.26 0.012 255)
--grid: oklch(0.28 0.012 258) ≈ #2A2E35
--line: oklch(0.35 0.015 255)
--ink-0: oklch(0.97 0.005 255) main text
--ink-1: oklch(0.86 0.008 255) secondary
--ink-2: oklch(0.72 0.01 255) tertiary
Content plan:
- Models: TT-HW 06/150 (6 MW hot water), TT-HW 14/150 (14 MW hot water), TT-ST 25/25 (25 MW / 36 t/h saturated steam at 2.5 MPa / 224 °C).
- Certifications register: ISO 9001:2015, ISO 14001:2015, ISO 45001:2018, GOST 30748-2001, GOST 12.2.003-91, TR CU 032/2013 EAC declaration.
- Automated JSON-LD FAQPage extraction from HTML <details> in build.py to guarantee verbatim match.
- Automated SHA-256 CSP calculation over <style> and <script> blocks in build.py.
