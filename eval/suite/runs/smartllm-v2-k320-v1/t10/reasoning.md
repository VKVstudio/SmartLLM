Let me analyze this request carefully. The user wants a production-ready single-page B2B portal for "КОНТУР-СПЕКТР" — a Russian engineering platform for continuous vibration diagnostics, wavelet analysis, and predictive analytics of gas turbine and compressor units.

Let me plan the structure:

1. **Design canon**: High-Tech SaaS Dark Mode with OKLCH tokens
   - Background: oklch(0.14 0.02 255) — deep graphite/obsidian
   - Panels: oklch(0.19 0.02 255)
   - Grid lines: oklch(0.28 0.03 255)
   - Text: oklch(0.95 0.01 250)
   - Teal indicator: oklch(0.76 0.14 195)
   - Amber indicator: oklch(0.75 0.16 75)

2. **Sections**:
   - Hero with live turbine status panel (vibration velocity mm/s per GOST ISO 10816-3, bearing temperature, RUL prediction) and interactive inline SVG FFT spectrogram with mode switching (Normal, Rotor Imbalance, Outer Ring Bearing Defect)
   - Bento grid architecture (IEPE accelerometers up to 25 kHz, edge controller with 24-bit ADC, neural anomaly detector without cloud, Modbus TCP / OPC UA integration)
   - Specification 3 delivery kits (Спектр-М8 8-channel, Спектр-М32 for turbogenerators, Спектр-Взрыв Ex ia for petrochemical)
   - Interactive damage prevention calculator (unit power MW, cost per hour of downtime, number of units → system payback calculation)
   - FAQ (5 engineering questions about GOST ISO 10816, sampling frequency, intrinsically safe protection, local deployment) and questionnaire request form (client validation)
   - Footer

3. **Requirements**:
   - Vanilla HTML/CSS/JS, 0 external network requests
   - Semantic HTML5, one h1, ARIA attributes, contrast ≥ 7:1, prefers-reduced-motion
   - Performance: CLS 0
   - SEO/GEO: title, meta description, canonical, Open Graph; JSON-LD @graph with Organization, Product (3 kits), FAQPage (verbatim match with visible FAQ), BreadcrumbList; llms.txt; robots.txt
   - Security: strict CSP in meta with exact placeholders, _headers file with all 7 mandatory security headers

Let me design this carefully. I need to keep it concise enough to complete without truncation.

Let me think about the OKLCH tokens:
- --bg: oklch(0.14 0.02 255)
- --panel: oklch(0.19 0.02 255)
- --line: oklch(0.28 0.03 255)
- --text: oklch(0.95 0.01 250)
- --teal: oklch(0.76 0.14 195)
- --amber: oklch(0.75 0.16 75)

For contrast ≥ 7:1, I need to ensure text colors are light enough against the dark backgrounds. oklch(0.95 0.01 250) against oklch(0.14 0.02 255) should give very high contrast.

The SVG FFT spectrogram needs to be interactive with mode switching. I'll use SVG with different paths for different states.

Let me structure the HTML:
- One h1
- Header with nav
- Hero section
- Architecture bento grid
- Specifications table
- Calculator
- FAQ
- Form
- Footer

For the JSON-LD, I need to match the visible FAQ verbatim.

Let me write the files now. I'll start with index.html.

Let me think about the SVG spectrogram. I'll create an SVG that shows frequency bins with peaks at different positions depending on the mode. The modes are:
- "Норма" (Normal) — peaks at 1X, 2X, 3X are small
- "Дисбаланс ротора" (Rotor Imbalance) — peak at 1X is large
- "Дефект наружного кольца подшипника" (Outer Ring Bearing Defect) — peak at BPFO (Ball Pass Frequency Outer) is large

I'll create the SVG with multiple path groups that are shown/hidden based on the mode.

For the calculator, I'll use addEventListener to bind events and compute the payback.

Let me write this carefully and concisely.

Now let me think about the structure more carefully to ensure I complete everything without truncation.

For the FFT spectrogram SVG, I'll create a simplified representation with bars at different frequency positions. The bars will have different heights based on the mode.

Let me plan the SVG:
- A frequency axis with bins
- Bars representing 1X, 2X, 3X harmonics
- For "Норма" mode: all bars are small
- For "Дисбаланс": 1X bar is tall
- For "Дефект наружного кольца": BPFO bar is tall

I'll use CSS classes to toggle visibility of different SVG groups.

For the live status panel, I'll use JS to update values periodically (or just static values that look dynamic).

Let me write the code now. I'll be careful to keep it concise.

Let me structure the CSS:
- :root tokens
- Reset
- Layout
- Typography
- Components

Let me write the JavaScript:
- Mode switching for FFT
- Calculator logic
- Form validation

Let me start writing.