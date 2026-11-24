# Canon 18_devtool_command_ui: DevTool / Command Terminal UI

- Always load with `_engineering_baseline.md` and `_ux_baseline.md`; they win on build and UX and are not repeated here.
- Values (colours, sizes, spacing): `kb/styles/canons/18_devtool_command_ui.json`. "(canon)" = rule from those tokens. `[assumption]` = unverified default.
- Sections: `<!-- section:NAME -->`; load only what the task needs. Assets: A code motion, B Z-Image stills; no C (video).

<!-- section:essence -->
## Essence
- A dark developer-workstation look: flat near-black zinc surfaces, a faint 24px dot grid, Geist and Geist Mono, one terminal-emerald accent, hairline borders, `<kbd>` shortcut chips, real code and real command output. Zero purple.
- It works because developers trust what they can copy and run. A real install command, real code and fast, keyboard-friendly UI prove the product better than marketing words.
- Good fits: developer tools, CLIs, APIs and SDKs, infrastructure, databases, cybersecurity, open-source projects.
- Weak fits: consumer lifestyle, food, fashion, kids, local services.
- Mood: technical, fast, precise. Default polarity: dark. Light: white zinc with the same structure.
- Compared with `04_hyper_minimal_speed` (light docs-first reading): this canon is a dark product landing with code as the hero.
- Avoid (canon): purple aurora blobs, `backdrop-filter` blur, slow 600ms fades, fake typing-cursor loops, fake terminals drawn with divs.

<!-- section:structure -->
## Structure
- Grid: 12 columns, 20px gutter, container 1312px, section padding 88px, card padding 24px (tokens).
- Typical landing order:
  - nav: logo, Docs, Pricing, Changelog, GitHub (with star count as text), CTA ("Get started");
  - hero: h1, one-line value, install command with copy button, secondary "Read the docs";
  - code example: 10–25 lines of real code with tabs per language;
  - features grid (4–6 cards with an icon, title, one line, optional snippet);
  - integrations/logos row; performance numbers or benchmarks with method;
  - pricing (free/pro/enterprise); changelog teaser; final CTA; footer with status page link.
- Mobile: code blocks scroll inside their box; tabs become a select or scrollable tab row.

<!-- section:hero -->
## Hero
- h1: Geist 600, `clamp(2rem, 1.5rem + 2.22vw, 3.5rem)` (56px desktop, 42 tablet, 32 mobile), line-height 1.08, tracking −0.035em, measure about 22ch.
- Option 1, "Install first" (default): h1 + subline + a terminal-style block with the install command (`npm i …`, `brew install …`, `curl … | sh` only if the product really uses it) and a Copy button.
- Option 2, "Code split": text left, real code editor block right (syntax-highlighted, line numbers optional).
- Option 3, "Command palette": a static, styled ⌘K palette showing real commands; clicking opens the real palette (optional). Pick it for apps with many commands.
- Show OS/package-manager tabs when there are several install paths.

<!-- section:blocks -->
## Blocks
- Code block: `<pre><code>` real text, Geist Mono 13–14px, line-height 1.6, a language label, a Copy button with "Copied" feedback. Highlight at build time (no runtime highlighter JS).
- Terminal output: real text in `<pre>`, prompt `$` as `user-select: none` so copy gets only the command.
- Shortcut chips: semantic `<kbd>` (`<kbd>⌘</kbd><kbd>K</kbd>`), 6px radius, 1px border (canon).
- Feature card: flat surface, hairline border, hover border turns accent + top rim brightens (canon).
- Command palette (if built): follow the ARIA combobox + listbox pattern; opens with ⌘K/Ctrl+K and a visible button; Esc closes.
- Changelog: date + version (mono) + 1–3 lines per item.
- Background dot grid: `radial-gradient(circle, <dot colour> 1px, transparent 1px)` with `background-size: 24px 24px` at low opacity (canon).

<!-- section:motion -->
## Motion
- Motion budget: low (dial 4); catalog motion `reduced_motion_instant` only. Tokens: ease `cubic-bezier(0.16,1,0.3,1)`, 160ms, stagger 25ms.
- Options (class A):
  - Hover: border to accent + top rim brighten, no Y bounce (canon).
  - Press: `scale(0.98)`.
  - Reveal: snappy 160ms opacity + 8px, once (canon).
  - Tabs and copy feedback: instant state swap.
- No JS motion library; no typing animations.
- Reduced motion (canon): 0ms state swaps.

<!-- section:typography -->
## Typography
- Display and body: Geist Variable (one family = one font file). Body 15–16px, line-height 1.6, measure 60–72ch.
- Mono: Geist Mono for code, commands, versions, numbers in benchmarks.
- Turn off ligatures in code if they hide characters people must type (`font-variant-ligatures: none`) [assumption].

<!-- section:color -->
## Color
- Dark (default): `bg` `oklch(0.118 0.004 260)` (≈ `#09090B`), `surface` `oklch(0.162 0.006 260)`, text `oklch(0.958 0.004 260)`, emerald `accent` `oklch(0.768 0.142 164)`.
- Light: `bg` `oklch(0.990 0.002 260)`, `surface` `oklch(0.960 0.004 260)`, near-black text, green `accent` `oklch(0.450 0.088 165)`, blue `accent_2` `oklch(0.485 0.145 255)`.
- Syntax highlight theme: few colours, all ≥ 4.5:1 on the code background; comments too.
- Zero purple/violet gradients (canon).

<!-- section:surfaces -->
## Surfaces
- Radius 10px cards, 8px buttons and inputs, 6px badges; 1px borders (tokens).
- Dark: `inset 0 1px 0 rgba(255,255,255,0.07), 0 0 0 1px rgba(255,255,255,0.04)`; no drop shadows on dark.
- No blur, no glow.

<!-- section:imagery -->
## Imagery (Z-Image, class B)
- Few images; code and UI screenshots carry the page.
- Dark base prompt (canon): "Precision carbon-black hardware macro study of {subject} featuring matte graphite heatsink fins, smoked optical silicon, and a single calibrated emerald status beam on deep obsidian, 85mm lens, clean blank surfaces".
- Light base prompt (canon): "Minimalist studio macro of {subject} in precision anodized aluminum and dark optical silicon on a crisp white-zinc drafting table with one subtle emerald optical fiber glint, 85mm lens, clean blank surfaces".
- Team portrait (canon): vertical 3:4, black/grey attire, tight key light, zinc cyclorama.
- Product screenshots: real UI, PNG/AVIF at 2× with `srcset`, `alt` saying what it shows.

<!-- section:stack -->
## Stack
- Default now: `html5_esm`. Others need npm install (see baseline).
- Preset: `classic_corporate`.
- JS only for copy buttons, tabs and the optional palette (small vanilla islands).
- Syntax highlighting at build time; with `html5_esm` pre-render the highlighted HTML.

<!-- section:seo -->
## SEO / AEO / GEO
- Style-specific only: `SoftwareApplication` (or `SoftwareSourceCode` for OSS) with `operatingSystem`, `applicationCategory`, `offers`; code examples as text so answer engines can quote them; link docs and changelog in `llms.txt`.

<!-- section:ux_check -->
## UX check (risks of this style only)
- Keyboard shortcuts clash with browser and screen-reader keys. Fix: use ⌘K/Ctrl+K and '/' only, always a visible button too; never single-letter shortcuts without a way to turn them off (WCAG 2.1.4).
- Long code lines break mobile layout. Fix: scroll inside the code block, never the page; keep the Copy button visible.
- Copy button with no feedback. Fix: label changes to 'Copied' for ~2s and is announced via `aria-live`.
- Grey-on-black secondary text and syntax comments fail contrast. Fix: ≥ 4.5:1 for all text including comments.
- Jargon-only copy loses evaluators. Fix: one plain-language line under the h1 saying what the tool does.

<!-- section:vendor -->
## Vendor
- Fonts (`vendor/fonts/<id>/`): geist, geist_mono.
- JS: none (CSS only).
- No CDN, no GSAP; stack and offline rules: `_engineering_baseline.md` → vendor.

<!-- section:hard_limits -->
## Hard limits
- Real code and commands as text, never images or fake div terminals.
- Every code block has a working Copy button.
- Zero purple, no blur, no typing-cursor loops.
- Motion ≤ 160ms; reduced motion = instant.
