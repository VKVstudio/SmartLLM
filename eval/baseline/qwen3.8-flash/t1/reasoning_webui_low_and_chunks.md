# Reasoning (Low reasoning + Shell run)

Let me build this. Key challenge: strict CSP with sha256 hashes for inline script and style. I need to write the files, then compute hashes of the exact inline script/style content, and put them in the CSP meta tag. Since the CSP meta tag is in the same HTML file that contains the inline style/script, I need to compute hashes after finalizing content — careful: the hash must be of the exact text between <style> and </style>, <script> and </script>.

Plan: write index.html with placeholder for CSP, then use a script (python) to compute hashes and inject them. Let me do it iteratively in the sandbox.

Design canon: dark industrial, blueprint grid 1px #2A2E35, JetBrains Mono for labels/mono, IBM Plex Sans for body (system fallbacks, no external CDN). Signal orange oklch(0.68 0.19 45). All colors as OKLCH tokens in :root. Contrast >= 7:1 for text — so body text should be near-white on near-black. Orange on dark: oklch(0.68 0.19 45) on a dark background — contrast ~5.5:1 (< 7:1). So use orange for non-text accents/borders, and for text use a lighter variant token like oklch(0.822 0.124 60.5) (#FFB16E, 10.6:1 on #0E1116 and 9.0:1 on #1D222A).

Computed tokens in sandbox (oklch.py):
--bg-0: oklch(0.177 0.0114 260.6); /* #0E1116 */
--bg-1: oklch(0.195 0.0112 260.7); /* #12151A */
--bg-2: oklch(0.221 0.0132 258.4); /* #171B21 */
--bg-3: oklch(0.250 0.0169 259.8); /* #1D222A */
--grid: oklch(0.300 0.0139 261.7); /* #2A2E35 exact */
--rule: oklch(0.369 0.0159 255.6); /* #3A4048 */
--rule-2: oklch(0.435 0.0195 254.0); /* #4A525C */
--ink-1: oklch(0.969 0.0062 255.5); /* #F2F5F9 16.7:1 / 14.6:1 */
--ink-2: oklch(0.908 0.0110 256.7); /* #DCE1E8 13.9:1 / 12.2:1 */
--ink-3: oklch(0.774 0.0193 258.4); /* #AEB6C2 8.9:1 / 7.8:1 */
--signal: oklch(0.68 0.19 45); /* #F3680F — graphics, borders, focus */
--signal-ink: oklch(0.822 0.124 60.5); /* #FFB16E 10.6:1 / 9.0:1 */
--signal-deep: oklch(0.55 0.17 45); /* #BD4600 */
--water: oklch(0.779 0.090 230.6); /* #78C2E6 9.3:1 */
--error-ink: oklch(0.822 0.140 25); /* #FF9E96 9.2:1 / 8.1:1 */

Assembled chunks in /workspace/site/index.html before session timeout:
- CHUNK1..CHUNK3: Full <head> + complete inline <style> (responsive, print, forced-colors, prefers-reduced-motion)
- CHUNK4: Full <script type="application/ld+json"> @graph with Organization, WebSite, WebPage, 3x Product (TT-HW 5.0, TT-ST 12.0, TT-ST 25.0), FAQPage (5 Q&As), BreadcrumbList
- CHUNK5: Header + Hero section with interactive ARIA tablist nameplate (TT-HW 5.0 / TT-ST 12.0 / TT-ST 25.0)
- CHUNK6: Section 01 Product line table (14 columns x 3 boiler models + 5 engineering footnotes)
- CHUNK7: Section 02 Boiler circuit schematic (1280x760 inline P&ID SVG with 10 interactive numbered callout groups + circuit index legend)
(Session expired right after CHUNK7 before CHUNK8 Certifications/FAQ/Contact/Footer).
