The user wants a recreation of this screenshot as a single self-contained index.html file. Let me carefully analyze the screenshot.

Layout analysis:
- Dark background (very dark navy/black, like #0a0e14 or similar)
- Top bar: "[Q9-09] QUANTUM-GRID TELEMETRY FABRIC" on left in white monospace bold, with a letter-spaced look. On right: a bordered pill with green text "● CLUSTER HEALTH: 99.9968% | P99 LATENCY: 1.42 ms" with a green border.
- Main content: two columns. Left column is a hero panel (bordered box) with:
  - Eyebrow: "SWISS GRID // DETERMINISTIC COMPUTE ENGINE" in cyan monospace uppercase
  - H1: "Sub-Millisecond Tensor Routing for Sovereign AI Clusters" in white bold sans-serif (looks like Inter/Helvetica bold)
  - Paragraph: gray text describing NVMe-over-Fabrics
  - Two buttons: "DEPLOY NODE SPEC" cyan filled with dark text, "INSPECT TOPOLOGY (3264-LD)" outlined with white text
- Right column: a grid of 4 metric cards (2x2). Each card has a bordered box with:
  - Label uppercase gray mono: "ACTIVE THROUGHPUT", "VRAM FOOTPRINT", "EXPERT CACHE HIT", "P99 E & R16 DMA" (actually "P99 E 4 R16 DMA"? Let me look: "P99 E 4 R16 DMA" hmm. The screenshot says "P99 E 4 R16 DMA"? Let me read: "P99 E 4 R16 DMA". Hmm hard to read. Looks like "P99 E 4 R16 DMA". Actually probably "P99 E4 R16 DMA"? I'll go with "P99 E4 R16 DMA"? The screenshot text: "P99 E 4 R16 DMA". I'll write "P99 E4 R16 DMA" maybe. Let me look more carefully: "P99 E 4 R16 DMA" — could be "P99 E4 R16 DMA". I'll use "P99 E4 R16 DMA". Hmm but to match closely maybe "P99 E 4 R16 DMA". I'll keep it as displayed: "P99 E 4 R16 DMA"? That looks odd. Could be "P99 / R16 DMA"? The screenshot shows "P99 E 4 R16 DMA". I'll reproduce literally "P99 E4 R16 DMA" — risky. Let me just go with what's visible: "P99 E 4 R16 DMA". Hmm.

Actually zooming: top-right metric label reads "P99 E 4 R16 DMA"? The characters: "P99 E 4 R16 DMA". I think it's "P99 E4 R16 DMA". I'll write "P99 E4 R16 DMA".

  - Big value: "48.6 tok/s", "6.52 GiB", "98.4%", "0.38 s" in white bold mono
  - Sub line green mono: "+14.2% vs baseline", "Budget: 8.00 GiB", "200 / 213 routed", "p99 warm stalls"
- Bottom row: three node spec cards:
  - "EDGE NODE // E-08" cyan label + price "$0.12 / hr" cyan on right
  - Rows separated by lines: "VRAM Allocation" gray label, right value "8 GiB GDDR6" white mono
  - "System DDR5 Pool" — "32 GiB Dual-Ch"
  - "Active Experts" — "10 / 205 per tok"
  - "Quantization" — "IQ3_XXS + imatrix"
  - Middle card "WORKSTATION // W-12" highlighted with cyan border (active state), price "$0.24 / hr"
    - "32 GiB RTX 4080", "32 GiB DDR5-5600", "10 / 205 per tok", "IQ1_S + Q8_0 KV"
  - "SOVEREIGN POD // S-64" "$1.40 / hr"
    - "64 GiB Multi-GPU", "256 GiB OCTA-Ch", "10 / 512 full MoE", "BF16 / Q6_K"

Colors:
- Background: very dark, maybe oklch(0.13 0.02 250) ~ #0b0f16. Let me approximate. The page bg looks like #0a0d14. Panels slightly lighter: #10151d. Cards inside slightly lighter: #141a24. Borders: subtle gray-blue rgba.
- Cyan accent: bright cyan like #22d3ee / oklch(0.78 0.15 200).
- Green: #4ade80-ish / oklch(0.75 0.18 145).
- Text primary white: #f2f5f9. Secondary gray: #9aa4b2.

Typography: headings sans-serif (Inter-like), mono for labels/values (IBM Plex Mono / JetBrains Mono style). Use system fonts: ui-sans-serif, system-ui; mono: ui-monospace, "SF Mono", Menlo, Consolas.

Contrast >= 7:1 for primary text: white on dark bg is fine.

Responsive down to 375px: stack columns.

Let me build a CSS grid: main container max-width ~1200px? The screenshot content spans nearly full width with padding ~24px. Top bar full width with border-bottom.

Structure:
- header (top bar): flex space-between, border-bottom 1px.
- main: grid with two columns: left hero (approx 55%), right metrics (approx 45%). Actually left hero panel width ~570px, right metrics ~570px in a 1200 container. Use grid-template-columns: 1fr 1fr? The right metrics grid is 2x2. Left hero is one panel. Let's do `grid-template-columns: 1.05fr 1fr` gap 24px.

- metrics grid: 2 columns, gap ~14px. Each metric card: border 1px, padding 16px, bg slightly lighter.

- bottom specs: grid 3 columns gap 24px. Each card border, padding. Title row flex between. Rows with border-top separators.

The middle card has cyan border and slight glow.

Let me write OKLCH tokens:

--bg: oklch(0.145 0.015 255) ~ #0d1117? Let me compute: oklch(0.15 0.02 255) is dark navy. I'll pick:
--surface-0: oklch(0.16 0.015 255) page bg? The screenshot bg is near black with slight blue: maybe #0a0e15. oklch(0.13 0.012 250).
--surface-1: panel bg: oklch(0.18 0.018 255)
--surface-2: inner card bg: oklch(0.21 0.02 255)
--border: oklch(0.28 0.02 255)
--border-strong: oklch(0.35 0.03 255)
--text-hi: oklch(0.97 0.005 250)
--text-mid: oklch(0.72 0.02 250)
--text-low: oklch(0.62 0.02 250)
--cyan: oklch(0.78 0.14 200)
--cyan-dim: oklch(0.7 0.12 200)
--green: oklch(0.78 0.17 150)

Check contrast: text-hi on surface-0: L 0.97 vs 0.13 => contrast ~ (0.97+0.05)/(0.13+0.05)? OKLCH L is perceptual lightness, roughly relative luminance mapping is nonlinear but approx. Fine, white on near-black is >7:1.

text-mid (0.72) on surface-0 (0.13): contrast approx (0.72+0.05)/(0.13+0.05)=0.77/0.18=4.3. That's secondary text, acceptable (the requirement is primary text >=7:1). Secondary gray in screenshot is like #8b95a5 which is ~4.5:1. OK.

Cyan on dark for button text? Button is cyan bg with dark text: dark text on cyan: cyan L 0.78 => luminance approx? For contrast we need dark text on cyan: (0.78+0.05)/(0.15+0.05)=0.83/0.20=4.15. Hmm button label "DEPLOY NODE SPEC" dark on cyan — in screenshot it's dark text on cyan, contrast maybe ~5. It's a button, fine.

Cyan text on dark bg: cyan L 0.78 vs bg 0.13 => (0.83)/(0.18)=4.6. Cyan labels are decorative; fine.

Let me make cyan a bit brighter: oklch(0.82 0.13 205) for text cyan to improve contrast (~5.3). Good enough.

Now spacing: top bar height ~48px. Main padding 24px. Hero panel padding 28px. H1 font-size ~32px bold, line-height 1.15. Paragraph 14px, color mid, line-height 1.6, max-width ~420px.

Buttons: mono uppercase 12px, letter-spacing 0.08em, padding 10px 18px.

Metric label: 10px mono uppercase letter-spacing 0.12em color low. Value: 22px mono bold white. Sub: 11px mono green.

Spec card: title 12px mono cyan bold; price 16px mono cyan bold. Rows: label 12px sans gray; value 12px mono white right aligned. Row padding 10px 0, border-top.

Let me build HTML semantically: <header>, <main>, <section>, <article>, <dl> for metrics rows? Use dl with dt/dd for spec rows. Use <ul> or grid.

I'll use dl for each spec card: <dl class="spec-rows"><div><dt>VRAM Allocation</dt><dd>8 GiB GDDR6</dd></div>...</dl>. Actually dt/dd wrapper div is valid HTML5? In HTML5 you can wrap dt+dd in div inside dl. Yes allowed.

For metrics cards use <article> with <p class="metric-label">, <p class="metric-value">, <p class="metric-sub">. Or use dl too. Keep simple.

Responsive: at <=900px stack hero and metrics (1 column). At <=640px metrics grid becomes 1 col? Screenshot at mobile: metrics 2x2 could become 1 col or keep 2. Let's do: <=900: main 1 col; specs 1 col; metrics stay 2 col until 520 then 1 col. Actually at 375, metrics 2-col would be cramped; make 1 col below 560.

Add subtle glow on active card: box-shadow 0 0 0 1px cyan inset? The screenshot shows cyan border plus slight outer glow. Use border-color cyan and box-shadow 0 0 12px -4px cyan.

Top-right pill: border 1px green-ish? In screenshot border looks teal/green faint. Use border: 1px solid color-mix? Use rgba via oklch with alpha: oklch(0.78 0.17 150 / 0.35). Text green. Dot green.

Font sizes scale: use clamp for h1.

Let me also add letter-spacing to top bar title: 0.12em, 12px bold mono.

Now write the file.

Details to match text exactly:

Top bar left: "[Q9-09] QUANTUM-GRID TELEMETRY FABRIC"
Top bar right: "● CLUSTER HEALTH: 99.9968% | P99 LATENCY: 1.42 ms"

Hero eyebrow: "SWISS GRID // DETERMINISTIC COMPUTE ENGINE"
H1: "Sub-Millisecond Tensor Routing for Sovereign AI Clusters"
Para: "Zero-jitter NVMe-over-Fabrics paging paired with hardware-enforced isolation. Inspect live expert utilization, memory bandwidth, and thermal envelopes in real time."
Buttons: "DEPLOY NODE SPEC", "INSPECT TOPOLOGY (3264-LD)"

Metrics:
1. ACTIVE THROUGHPUT / 48.6 tok/s / +14.2% vs baseline
2. VRAM FOOTPRINT / 6.52 GiB / Budget: 8.00 GiB
3. EXPERT CACHE HIT / 98.4% / 200 / 213 routed
4. P99 E4 R16 DMA? Let me decide: I'll write "P99 E4 R16 DMA"? Hmm the screenshot: "P99 E 4 R16 DMA". Could actually be "P99 / R16 DMA"? I'll go with "P99 E4 R16 DMA". Hmm wait maybe "P99 E 4 R16 DMA" is "P99 (E4) R16 DMA"? Not sure. Let me just reproduce "P99 E4 R16 DMA". Value "0.38 s", sub "p99 warm stalls".

Specs:
Card1: EDGE NODE // E-08, $0.12 / hr
 rows: VRAM Allocation — 8 GiB GDDR6; System DDR5 Pool — 32 GiB Dual-Ch; Active Experts — 10 / 205 per tok; Quantization — IQ3_XXS + imatrix
Card2 (active): WORKSTATION // W-12, $0.24 / hr
 rows: VRAM Allocation — 32 GiB RTX 4080; System DDR5 Pool — 32 GiB DDR5-5600; Active Experts — 10 / 205 per tok; Quantization — IQ1_S + Q8_0 KV
Card3: SOVEREIGN POD // S-64, $1.40 / hr
 rows: VRAM Allocation — 64 GiB Multi-GPU; System DDR5 Pool — 256 GiB OCTA-Ch; Active Experts — 10 / 512 full MoE; Quantization — BF16 / Q6_K

Prices in screenshot: "$0.12 / hr" cyan bold mono ~18px.

Now CSS.

I'll set body font-family sans; mono class for specific elements.

Let me produce final code.

Also add focus styles for buttons/links for accessibility.

Use `color-scheme: dark`.

Write it out.

One more: the hero panel and metrics panel area: In screenshot, hero is inside a bordered panel; metrics cards each bordered but the group not in a panel. Bottom spec cards bordered individually.

Top bar has bottom border line spanning full width.

Let me craft grid:

.page { max-width: 1180px; margin: 0 auto; padding: 24px; }

Actually screenshot content width ~ from 24px to 1176px in a 1200 viewport. Use max-width 1200 padding 24.

Header full width with border-bottom; inner max-width container.

main layout: .hero-grid { display:grid; grid-template-columns: 1.02fr 0.98fr; gap:24px; align-items:stretch }

Hero panel: border 1px, padding 28px 30px, bg surface-1.

Metrics: .metrics { display:grid; grid-template-columns:1fr 1fr; gap:14px; }

Each metric: border, padding 14px 16px, bg surface-2? In screenshot metric cards bg slightly lighter than panel bg. Panel bg ~ #10151c; metric bg ~ #151b25. Use surface-2.

Specs: .specs { display:grid; grid-template-columns: repeat(3,1fr); gap:24px; margin-top:24px; }

Spec card: border, bg surface-1, padding 20px.

Active card: border-color cyan; box-shadow: 0 0 18px -6px cyan, inset 0 0 0 1px? The screenshot active card has cyan border and a faint glow. Good.

dl rows: dt gray 12px sans; dd mono 1

I have thought about this long enough; time to give my answer.
