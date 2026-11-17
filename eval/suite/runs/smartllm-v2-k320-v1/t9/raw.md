FILE: DESIGN.md
```md
# DESIGN.md — AETHERIA BIO-ROBOTICS Design Manifest

## 1. Design Canon
Swiss typographic grid meets high-tech telemetry. The interface is a light laboratory bone surface with carbon ink, forest telemetry accents, and signal amber status cues. The system favors precision, clarity, instrument-grade hierarchy, and restrained visual density.

## 2. OKLCH Color Tokens
- `--surface`: `oklch(0.97 0.008 95)` — laboratory bone surface.
- `--surface-dim`: `oklch(0.94 0.010 95)` — panel and table surface.
- `--surface-deep`: `oklch(0.91 0.012 95)` — recessed surfaces.
- `--ink`: `oklch(0.14 0.015 255)` — carbon ink for primary text.
- `--ink-muted`: `oklch(0.35 0.018 255)` — secondary text.
- `--accent`: `oklch(0.45 0.14 155)` — forest telemetry accent.
- `--accent-strong`: `oklch(0.36 0.16 155)` — hover / active accent.
- `--signal`: `oklch(0.66 0.17 65)` — signal amber for alerts, telemetry highlights, and warnings.
- `--signal-strong`: `oklch(0.54 0.18 65)` — strong signal for emphasis.
- `--line`: `oklch(0.82 0.012 255)` — hairline borders.
- `--line-strong`: `oklch(0.72 0.016 255)` — stronger borders.

## 3. Contrast Requirements
- Body text on `--surface` must meet `≥ 7:1`.
- Secondary text on `--surface-dim` must meet `≥ 7:1`.
- Accent text on light surfaces must meet `≥ 7:1` when used for information, not decoration.
- Signal amber is reserved for status and alerts; avoid using it as primary body text.
- Focus states must remain visible and contrast-safe.

## 4. Modular Grid Rules
- Base grid: 12-column fluid grid.
- Max container width: `1120px`.
- Gutter: `clamp(1rem, 2.5vw, 1.75rem)`.
- Breakpoints:
  - `375px` mobile
  - `768px` tablet
  - `1024px` desktop
  - `1280px` wide
- Mobile invariant: `overflow-x: clip` on `html` and `body`.
- Grid children must have `min-width: 0`.
- Tables must be wrapped in `.table-wrap` with `overflow-x: auto`.
- Decorative absolute shapes must remain within viewport bounds.

## 5. Typography Scale
- Display: `clamp(2.25rem, 5vw, 4rem)`
- Section title: `clamp(1.5rem, 2.6vw, 2.25rem)`
- Body: `clamp(1rem, 1.35vw, 1.125rem)`
- Meta / telemetry labels: `0.875rem`
- Monospace telemetry values: `0.9375rem`
- Line height:
  - Display: `1.05`
  - Body: `1.6`
  - Labels: `1.35`

## 6. Spacing Scale
- `--space-1`: `0.5rem`
- `--space-2`: `0.75rem`
- `--space-3`: `1rem`
- `--space-4`: `1.5rem`
- `--space-5`: `2rem`
- `--space-6`: `3rem`
- `--space-7`: `4rem`

## 7. Component Invariants
- Header nav must wrap below `480px`.
- Cards must use hairline borders, subtle surface elevation, and telemetry metadata.
- Buttons must be keyboard accessible and use `aria-pressed` for filters.
- Inputs must have visible focus states and validation feedback.
- Tables must remain readable via horizontal scroll without page overflow.
- SVG schematics must be inline, accessible, and non-decorative when meaningful.
- No inline event handlers; all event bindings live in `./app.js`.
- No `element.style.*`, `setAttribute('style', ...)`, or `style.setProperty(...)` in JS.
- Use `classList.toggle()`, `hidden`, or SVG geometry attributes only.
- Honor `prefers-reduced-motion`.

## 8. Motion Policy
- Default motion is restrained.
- Transitions are limited to opacity and transform.
- Reduced motion disables transitions and smooth scrolling.
- Telemetry updates should remain legible and non-jittery.
```

FILE: tokens.css
```css
:root {
  color-scheme: light;

  --surface: oklch(0.97 0.008 95);
  --surface-dim: oklch(0.94 0.010 95);
  --surface-deep: oklch(0.91 0.012 95);
  --ink: oklch(0.14 0.015 255);
  --ink-muted: oklch(0.35 0.018 255);
  --accent: oklch(0.45 0.14 155);
  --accent-strong: oklch(0.36 0.16 155);
  --signal: oklch(0.66 0.17 65);
  --signal-strong: oklch(0.54 0.18 65);
  --line: oklch(0.82 0.012 255);
  --line-strong: oklch(0.72 0.016 255);

  --space-1: 0.5rem;
  --space-2: 0.75rem;
  --space-3: 1rem;
  --space-4: 1.5rem;
  --space-5: 2rem;
  --space-6: 3rem;
  --space-7: 4rem;

  --font-display: "Helvetica Neue", Helvetica, Arial, sans-serif;
  --font-body: "Helvetica Neue", Helvetica, Arial, sans-serif;
  --font-mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;

  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;

  --shadow-sm: 0 1px 2px oklch(0.14 0.015 255 / 0.06);
  --shadow-md: 0 4px 12px oklch(0.14 0.015 255 / 0.08);

  --transition-fast: 180ms ease-out;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body {
  max-width: 100%;
  overflow-x: clip;
}

body {
  margin: 0;
  background: var(--surface);
  color: var(--ink);
  font-family: var(--font-body);
  line-height: 1.6;
}

img,
svg,
canvas {
  max-width: 100%;
  height: auto;
}

:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.container {
  width: min(100%, 1120px);
  margin-inline: auto;
  padding-inline: var(--space-4);
}

.skip-link {
  position: absolute;
  left: -9999px;
  top: 0;
  background: var(--ink);
  color: var(--surface);
  padding: var(--space-2) var(--space-3);
}

.skip-link:focus {
  left: var(--space-3);
  z-index: 100;
}
```

FILE: app.js
```js
(function () {
  'use strict';

  const platformData = {
    x4: {
      name: 'AETHER-X4 Multispectral',
      powerDrawW: 28,
      sensor: '12-band multispectral',
      link: '2.4 GHz telemetry',
      ip: 'IP67',
      payload: '2.4 kg'
    },
    h8: {
      name: 'AETHER-H8 Heavy Lidar',
      powerDrawW: 58,
      sensor: '128-channel lidar',
      link: '2.4 GHz telemetry',
      ip: 'IP67',
      payload: '6.2 kg'
    },
    s2: {
      name: 'AETHER-S2 Soil Probe',
      powerDrawW: 24,
      sensor: 'Soil probe array',
      link: '2.4 GHz telemetry',
      ip: 'IP66',
      payload: '1.8 kg'
    }
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const formatNumber = (value) => Number(value).toLocaleString('en-US');

  const state = {
    filter: 'all'
  };

  const filterButtons = $$('[data-filter]');
  const platformCards = $$('[data-platform-card]');
  const tableRows = $$('[data-platform-row]');
  const form = $('#deployment-form');
  const formStatus = $('#form-status');

  const coverageForm = $('#coverage-form');
  const coverageStatus = $('#coverage-status');
  const outputFlightTime = $('#output-flight-time');
  const outputBatterySwaps = $('#output-battery-swaps');
  const outputWaypoints = $('#output-waypoints');
  const outputCoverageTime = $('#output-coverage-time');
  const outputAreaCovered = $('#output-area-covered');

  function setFilter(filter) {
    state.filter = filter;

    filterButtons.forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.filter === filter));
    });

    platformCards.forEach((card) => {
      const platform = card.dataset.platform;
      const visible = filter === 'all' || platform === filter;
      card.classList.toggle('is-hidden', !visible);
    });

    tableRows.forEach((row) => {
      const platform = row.dataset.platform;
      const visible = filter === 'all' || platform === filter;
      row.classList.toggle('is-hidden', !visible);
    });
  }

  filterButtons.forEach((button) => {
    button.addEventListener('click', () => setFilter(button.dataset.filter));
  });

  function formatDuration(seconds) {
    if (!Number.isFinite(seconds) || seconds <= 0) return '0 min';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor(seconds % 3600 / 60);
    if (hours > 0) return `${hours} h ${minutes} min`;
    return `${minutes} min`;
  }

  function calculateCoverage() {
    const fieldAreaHa = Number($('#field-area').value);
    const swathWidth = Number($('#swath-width').value);
    const cruiseSpeed = Number($('#cruise-speed').value);
    const batteryWh = Number($('#battery-capacity').value);
    const selectedPlatform = $('#platform-select').value;
    const platform = platformData[selectedPlatform] || platformData.x4;

    const valid =
      fieldAreaHa > 0 &&
      swathWidth > 0 &&
      cruiseSpeed > 0 &&
      batteryWh > 0;

    if (!valid) {
      coverageStatus.textContent = 'Enter positive values for field area, swath width, cruise speed, and battery capacity.';
      return;
    }

    coverageStatus.textContent = 'Telemetry estimate updated.';

    const fieldAreaM2 = fieldAreaHa * 10000;
    const coverageSeconds = fieldAreaM2 / (swathWidth * cruiseSpeed);
    const flightSeconds = batteryWh / platform.powerDrawW * 3600;
    const requiredBatteries = Math.max(1, Math.ceil(coverageSeconds / flightSeconds));
    const batterySwaps = requiredBatteries > 1 ? requiredBatteries - 1 : 0;
    const waypoints = Math.max(1, Math.ceil(coverageSeconds / flightSeconds));

    outputAreaCovered.textContent = `${formatNumber(fieldAreaHa)} ha`;
    outputCoverageTime.textContent = formatDuration(coverageSeconds);
    outputFlightTime.textContent = formatDuration(flightSeconds);
    outputBatterySwaps.textContent = String(batterySwaps);
    outputWaypoints.textContent = String(waypoints);
  }

  if (coverageForm) {
    coverageForm.addEventListener('submit', (event) => {
      event.preventDefault();
      calculateCoverage();
    });

    coverageForm.addEventListener('input', () => {
      calculateCoverage();
    });
  }

  if (form) {
    form.addEventListener('submit', (event) => {
      event.preventDefault();

      const errors = [];
      const name = $('#contact-name').value.trim();
      const email = $('#contact-email').value.trim();
      const organization = $('#contact-org').value.trim();
      const message = $('#contact-message').value.trim();

      if (name.length < 2) errors.push('Enter a valid contact name.');
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.push('Enter a valid email address.');
      if (organization.length < 2) errors.push('Enter your organization.');
      if (message.length < 10) errors.push('Enter a deployment request with at least 10 characters.');

      if (errors.length > 0) {
        formStatus.textContent = `Validation issues: ${errors.join(' ')}`;
        return;
      }

      formStatus.textContent = 'Deployment inquiry validated. A fleet planning team will review the request.';
    });
  }
})();
```

FILE: index.html
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'sha256-__CSP_STYLE__'; script-src 'sha256-__CSP_SCRIPT__'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'">
  <title>AETHERIA BIO-ROBOTICS | Autonomous Environmental & Precision Agriculture Drones</title>
  <meta name="description" content="AETHERIA BIO-ROBOTICS autonomous drone platforms for environmental monitoring, precision agriculture, multispectral sensing, lidar telemetry, and soil probe operations.">
  <link rel="stylesheet" href="./tokens.css">
  <style>
    :root {
      color-scheme: light;
      --surface: oklch(0.97 0.008 95);
      --surface-dim: oklch(0.94 0.010 95);
      --surface-deep: oklch(0.91 0.012 95);
      --ink: oklch(0.14 0.015 255);
      --ink-muted: oklch(0.35 0.018 255);
      --accent: oklch(0.45 0.14 155);
      --accent-strong: oklch(0.36 0.16 155);
      --signal: oklch(0.66 0.17 65);
      --signal-strong: oklch(0.54 0.18 65);
      --line: oklch(0.82 0.012 255);
      --line-strong: oklch(0.72 0.016 255);
      --space-1: 0.5rem;
      --space-2: 0.75rem;
      --space-3: 1rem;
      --space-4: 1.5rem;
      --space-5: 2rem;
      --space-6: 3rem;
      --space-7: 4rem;
      --font-display: "Helvetica Neue", Helvetica, Arial, sans-serif;
      --font-body: "Helvetica Neue", Helvetica, Arial, sans-serif;
      --font-mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      --radius-sm: 0.25rem;
      --radius-md: 0.5rem;
      --radius-lg: 0.75rem;
      --shadow-sm: 0 1px 2px oklch(0.14 0.015 255 / 0.06);
      --shadow-md: 0 4px 12px oklch(0.14 0.015 255 / 0.08);
      --transition-fast: 180ms ease-out;
    }

    *,
    *::before,
    *::after {
      box-sizing: border-box;
    }

    html,
    body {
      max-width: 100%;
      overflow-x: clip;
    }

    body {
      margin: 0;
      background: var(--surface);
      color: var(--ink);
      font-family: var(--font-body);
      line-height: 1.6;
    }

    img,
    svg,
    canvas {
      max-width: 100%;
      height: auto;
    }

    .container {
      width: min(100%, 1120px);
      margin-inline: auto;
      padding-inline: var(--space-4);
    }

    .skip-link {
      position: absolute;
      left: -9999px;
      top: 0;
      background: var(--ink);
      color: var(--surface);
      padding: var(--space-2) var(--space-3);
    }

    .skip-link:focus {
      left: var(--space-3);
      z-index: 100;
    }

    header {
      border-bottom: 1px solid var(--line);
      background: var(--surface-dim);
    }

    .masthead {
      display: grid;
      gap: var(--space-3);
      padding-block: var(--space-4);
      align-items: center;
    }

    .brand {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: var(--space-2);
      font-family: var(--font-display);
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .brand span:last-child {
      color: var(--ink-muted);
      font-size: 0.875rem;
      font-family: var(--font-mono);
      letter-spacing: 0.08em;
      text-transform: none;
    }

    .nav-wrap {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3);
    }

    .nav-wrap a {
      color: var(--ink);
      text-decoration: none;
      font-size: 0.9375rem;
      letter-spacing: 0.04em;
    }

    .hero {
      display: grid;
      gap: var(--space-5);
      padding-block: var(--space-6);
    }

    .hero h1 {
      font-family: var(--font-display);
      font-size: clamp(2.25rem, 5vw, 4rem);
      line-height: 1.05;
      margin: 0;
      letter-spacing: -0.02em;
    }

    .hero p {
      max-width: 60ch;
      color: var(--ink-muted);
      margin: 0;
    }

    .telemetry-strip {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3);
      padding: var(--space-3);
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: var(--surface-dim);
      font-family: var(--font-mono);
      font-size: 0.875rem;
    }

    .telemetry-strip span {
      white-space: normal;
    }

    .telemetry-strip .signal {
      color: var(--signal-strong);
    }

    section {
      padding-block: var(--space-6);
      border-top: 1px solid var(--line);
    }

    h2 {
      font-family: var(--font-display);
      font-size: clamp(1.5rem, 2.6vw, 2.25rem);
      margin: 0 0 var(--space-4);
      letter-spacing: -0.01em;
    }

    .lead {
      color: var(--ink-muted);
      max-width: 72ch;
      margin: 0 0 var(--space-5);
    }

    .layout-grid {
      display: grid;
      gap: var(--space-5);
      grid-template-columns: 1fr;
    }

    @media (min-width: 768px) {
      .layout-grid {
        grid-template-columns: 1.1fr 0.9fr;
      }
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: var(--surface-dim);
      padding: var(--space-4);
      box-shadow: var(--shadow-md);
    }

    .panel h3 {
      margin: 0 0 var(--space-3);
      font-family: var(--font-display);
      font-size: 1.25rem;
      letter-spacing: 0.01em;
    }

    .form-grid {
      display: grid;
      gap: var(--space-3);
      min-width: 0;
    }

    .form-grid label {
      font-size: 0.875rem;
      font-family: var(--font-mono);
      letter-spacing: 0.04em;
      color: var(--ink-muted);
    }

    .form-grid input,
    .form-grid select,
    .form-grid textarea {
      width: 100%;
      min-width: 0;
      padding: var(--space-2) var(--space-3);
      border: 1px solid var(--line-strong);
      border-radius: var(--radius-sm);
      background: var(--surface);
      color: var(--ink);
      font: inherit;
    }

    .form-grid textarea {
      min-height: 8rem;
      resize: vertical;
    }

    .button {
      border: 1px solid var(--line-strong);
      background: var(--surface);
      color: var(--ink);
      padding: var(--space-2) var(--space-3);
      border-radius: var(--radius-sm);
      font: inherit;
      cursor: pointer;
    }

    .button:hover {
      background: var(--surface-deep);
    }

    .button-primary {
      background: var(--accent);
      color: var(--surface);
      border-color: var(--accent-strong);
    }

    .button-primary:hover {
      background: var(--accent-strong);
    }

    .button[aria-pressed="true"] {
      background: var(--ink);
      color: var(--surface);
    }

    .output-grid {
      display: grid;
      gap: var(--space-3);
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      min-width: 0;
    }

    .output-item {
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: var(--surface);
      padding: var(--space-3);
      min-width: 0;
    }

    .output-item span {
      display: block;
      font-family: var(--font-mono);
      font-size: 0.875rem;
      color: var(--ink-muted);
      letter-spacing: 0.04em;
    }

    .output-item strong {
      display: block;
      margin-top: var(--space-1);
      font-size: 1.25rem;
      font-family: var(--font-mono);
    }

    .status {
      min-height: 1.5rem;
      color: var(--ink-muted);
      font-family: var(--font-mono);
      font-size: 0.875rem;
    }

    .status.success {
      color: var(--accent-strong);
    }

    .status.error {
      color: var(--signal-strong);
    }

    .filter-row {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
      margin-bottom: var(--space-4);
    }

    .card-grid {
      display: grid;
      gap: var(--space-4);
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      min-width: 0;
    }

    .card {
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: var(--surface);
      padding: var(--space-4);
      min-width: 0;
      box-shadow: var(--shadow-sm);
    }

    .card h3 {
      margin: 0 0 var(--space-2);
      font-family: var(--font-display);
      letter-spacing: 0.01em;
    }

    .card-meta {
      display: grid;
      gap: var(--space-2);
      font-family: var(--font-mono);
      font-size: 0.875rem;
      color: var(--ink-muted);
    }

    .card-meta span {
      white-space: normal;
    }

    .is-hidden {
      display: none;
    }

    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: var(--surface-dim);
    }

    table {
      width: 100%;
      min-width: 640px;
      border-collapse: collapse;
    }

    th,
    td {
      padding: var(--space-3);
      border-bottom: 1px solid var(--line);
      text-align: left;
      font-size: 0.9375rem;
    }

    th {
      font-family: var(--font-mono);
      font-weight: 700;
      color: var(--ink);
      background: var(--surface-deep);
    }

    .schematic {
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: var(--surface);
      padding: var(--space-4);
    }

    .schematic svg {
      width: 100%;
      height: auto;
      display: block;
    }

    .faq {
      display: grid;
      gap: var(--space-3);
    }

    .faq details {
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: var(--surface);
      padding: var(--space-3);
    }

    .faq summary {
      cursor: pointer;
      font-family: var(--font-display);
      font-size: 1.125rem;
      letter-spacing: 0.01em;
    }

    .faq p {
      margin: var(--space-2) 0 0;
      color: var(--ink-muted);
    }

    .form-block {
      display: grid;
      gap: var(--space-4);
    }

    footer {
      border-top: 1px solid var(--line);
      padding-block: var(--space-5);
      background: var(--surface-dim);
    }

    .footer-meta {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3);
      font-family: var(--font-mono);
      font-size: 0.875rem;
      color: var(--ink-muted);
    }

    @media (max-width: 480px) {
      .nav-wrap,
      .telemetry-strip,
      .filter-row,
      .card-meta {
        gap: var(--space-2);
      }

      .nav-wrap a,
      .button,
      .telemetry-strip span,
      .card-meta span {
        white-space: normal;
      }

      table {
        min-width: 560px;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      *,
      *::before,
      *::after {
        transition: none !important;
        scroll-behavior: auto !important;
      }
    }
  </style>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": "#organization",
        "name": "AETHERIA BIO-ROBOTICS",
        "description": "Autonomous environmental and precision agriculture drone platform.",
        "url": "https://example.com",
        "logo": "https://example.com/logo.svg"
      },
      {
        "@type": "Product",
        "@id": "#aether-x4",
        "name": "AETHER-X4 Multispectral",
        "description": "12-band multispectral autonomous drone for crop health telemetry and environmental monitoring.",
        "brand": {
          "@id": "#organization"
        },
        "category": "Multispectral Drone Platform"
      },
      {
        "@type": "Product",
        "@id": "#aether-h8",
        "name": "AETHER-H8 Heavy Lidar",
        "description": "128-channel lidar payload platform for terrain mapping, biomass estimation, and environmental surveying.",
        "brand": {
          "@id": "#organization"
        },
        "category": "Heavy Lidar Drone Platform"
      },
      {
        "@type": "Product",
        "@id": "#aether-s2",
        "name": "AETHER-S2 Soil Probe",
        "description": "Soil probe array drone for moisture, nutrient, and substrate telemetry in precision agriculture operations.",
        "brand": {
          "@id": "#organization"
        },
        "category": "Soil Probe Drone Platform"
      },
      {
        "@type": "FAQPage",
        "@id": "#faq",
        "mainEntity": [
          {
            "@type": "Question",
            "name": "What is AETHERIA BIO-ROBOTICS?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "AETHERIA BIO-ROBOTICS is an autonomous environmental and precision agriculture drone platform."
            }
          },
          {
            "@type": "Question",
            "name": "Which platforms are available?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "The AETHER-X4 Multispectral, AETHER-H8 Heavy Lidar, and AETHER-S2 Soil Probe platforms are available."
            }
          },
          {
            "@type": "Question",
            "name": "Can the calculator estimate battery swaps?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Yes. The flight-path coverage calculator estimates flight time, battery swaps, waypoint count, and coverage time."
            }
          },
          {
            "@type": "Question",
            "name": "How does the telemetry filter work?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "The telemetry filter lets users isolate specific drone platforms and view related sensor, link, and payload metadata."
            }
          },
          {
            "@type": "Question",
            "name": "Is deployment inquiry validation client-side?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Yes. The deployment inquiry form uses client-side validation before submission."
            }
          }
        ]
      },
      {
        "@type": "BreadcrumbList",
        "@id": "#breadcrumbs",
        "itemListElement": [
          {
            "@type": "ListItem",
            "position": 1,
            "name": "Home",
            "item": "https://example.com/"
          },
          {
            "@type": "ListItem",
            "position": 2,
            "name": "Platforms",
            "item": "https://example.com/#platforms"
          },
          {
            "@type": "ListItem",
            "position": 3,
            "name": "Coverage Calculator",
            "item": "https://example.com/#calculator"
          }
        ]
      }
    ]
  }
  </script>
  <script src="./app.js" defer></script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to main content</a>
  <header>
    <div class="container masthead">
      <div class="brand">
        <span>AETHERIA BIO-ROBOTICS</span>
        <span>ENVIRONMENTAL + AGRICULTURE TELEMETRY</span>
      </div>
      <nav class="nav-wrap" aria-label="Primary navigation">
        <a href="#platforms">Platforms</a>
        <a href="#calculator">Calculator</a>
        <a href="#schematic">Schematic</a>
        <a href="#faq">FAQ</a>
        <a href="#deployment">Deployment</a>
      </nav>
    </div>
  </header>

  <main id="main">
    <div class="container hero">
      <div>
        <h1>Autonomous bio-robotic telemetry for environmental and precision agriculture operations</h1>
        <p>
          AETHERIA platforms combine multispectral sensing, lidar surveying, soil probe arrays,
          and RTK flight planning to map crop health, terrain, moisture, and environmental change.
        </p>
      </div>
      <div class="telemetry-strip" aria-label="Live telemetry status">
        <span>TELEMETRY LINK ACTIVE 2.4 GHZ</span>
        <span class="signal">RTK LOCK: NOMINAL</span>
        <span>SIGNAL AMBER: MONITOR</span>
        <span>SWARM: 3 PLATFORMS</span>
      </div>
    </div>

    <section id="platforms">
      <div class="container">
        <h2>Platform Telemetry Filter</h2>
        <p class="lead">
          Filter the AETHERIA fleet by platform. Cards and comparison rows update without inline style mutation.
        </p>
        <div class="filter-row" role="group" aria-label="Platform filters">
          <button class="button" type="button" data-filter="all" aria-pressed="true">All Platforms</button>
          <button class="button" type="button" data-filter="x4" aria-pressed="false">AETHER-X4 Multispectral</button>
          <button class="button" type="button" data-filter="h8" aria-pressed="false">AETHER-H8 Heavy Lidar</button>
          <button class="button" type="button" data-filter="s2" aria-pressed="false">AETHER-S2 Soil Probe</button>
        </div>

        <div class="card-grid">
          <article class="card" data-platform-card data-platform="x4">
            <h3>AETHER-X4 Multispectral</h3>
            <div class="card-meta">
              <span>SENSOR: 12-BAND MULTISPECTRAL</span>
              <span>LINK: 2.4 GHZ TELEMETRY</span>
              <span>ENVELOPE: IP67</span>
              <span>PAYLOAD: 2.4 KG</span>
            </div>
          </article>
          <article class="card" data-platform-card data-platform="h8">
            <h3>AETHER-H8 Heavy Lidar</h3>
            <div class="card-meta">
              <span>SENSOR: 128-CHANNEL LIDAR</span>
              <span>LINK: 2.4 GHZ TELEMETRY</span>
              <span>ENVELOPE: IP67</span>
              <span>PAYLOAD: 6.2 KG</span>
            </div>
          </article>
          <article class="card" data-platform-card data-platform="s2">
            <h3>AETHER-S2 Soil Probe</h3>
            <div class="card-meta">
              <span>SENSOR: SOIL PROBE ARRAY</span>
              <span>LINK: 2.4 GHZ TELEMETRY</span>
              <span>ENVELOPE: IP66</span>
              <span>PAYLOAD: 1.8 KG</span>
            </div>
          </article>
        </div>

        <div class="table-wrap">
          <table aria-label="AETHERIA drone platform comparison">
            <thead>
              <tr>
                <th scope="col">Platform</th>
                <th scope="col">Sensor Payload</th>
                <th scope="col">Telemetry Link</th>
                <th scope="col">Power Draw</th>
                <th scope="col">Best For</th>
              </tr>
            </thead>
            <tbody>
              <tr data-platform-row data-platform="x4">
                <td>AETHER-X4 Multispectral</td>
                <td>12-band multispectral</td>
                <td>2.4 GHz telemetry</td>
                <td>28 W</td>
                <td>Crop health mapping</td>
              </tr>
              <tr data-platform-row data-platform="h8">
                <td>AETHER-H8 Heavy Lidar</td>
                <td>128-channel lidar</td>
                <td>2.4 GHz telemetry</td>
                <td>58 W</td>
                <td>Topography and biomass</td>
              </tr>
              <tr data-platform-row data-platform="s2">
                <td>AETHER-S2 Soil Probe</td>
                <td>Soil probe array</td>
                <td>2.4 GHz telemetry</td>
                <td>24 W</td>
                <td>Moisture and nutrient scans</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section id="calculator">
      <div class="container">
        <h2>Live Flight-Path Coverage Calculator</h2>
        <p class="lead">
          Estimate coverage time, battery capacity, battery swaps, waypoint count, and mission duration.
        </p>

        <form id="coverage-form" class="panel form-grid" novalidate>
          <label for="platform-select">Platform</label>
          <select id="platform-select" name="platform">
            <option value="x4" selected>AETHER-X4 Multispectral</option>
            <option value="h8">AETHER-H8 Heavy Lidar</option>
            <option value="s2">AETHER-S2 Soil Probe</option>
          </select>

          <label for="field-area">Field Area (ha)</label>
          <input id="field-area" name="field-area" type="number" inputmode="decimal" min="0" step="0.1" value="120" aria-describedby="coverage-status">

          <label for="swath-width">Swath Width (m)</label>
          <input id="swath-width" name="swath-width" type="number" inputmode="decimal" min="0" step="0.1" value="12" aria-describedby="coverage-status">

          <label for="cruise-speed">Cruise Speed (m/s)</label>
          <input id="cruise-speed" name="cruise-speed" type="number" inputmode="decimal" min="0" step="0.1" value="12" aria-describedby="coverage-status">

          <label for="battery-capacity">Battery Capacity (Wh)</label>
          <input id="battery-capacity" name="battery-capacity" type="number" inputmode="decimal" min="0" step="1" value="120" aria-describedby="coverage-status">

          <p id="coverage-status" class="status" aria-live="polite">Telemetry estimate ready.</p>

          <div class="output-grid">
            <div class="output-item">
              <span>AREA COVERED</span>
              <strong id="output-area-covered">120 ha</strong>
            </div>
            <div class="output-item">
              <span>COVERAGE TIME</span>
              <strong id="output-coverage-time">1 h 54 min</strong>
            </div>
            <div class="output-item">
              <span>FLIGHT TIME</span>
              <strong id="output-flight-time">4 h 0 min</strong>
            </div>
            <div class="output-item">
              <span>BATTERY SWAPS</span>
              <strong id="output-battery-swaps">0</strong>
            </div>
            <div class="output-item">
              <span>WAYPOINTS</span>
              <strong id="output-waypoints">1</strong>
            </div>
          </div>

          <button class="button button-primary" type="submit">Update Telemetry Estimate</button>
        </form>
      </div>
    </section>

    <section id="schematic">
      <div class="container layout-grid">
        <div>
          <h2>Multispectral Sensor Schematic</h2>
          <p class="lead">
            Inline SVG schematic showing multispectral bands, telemetry link, RTK lock, and payload routing.
          </p>
        </div>
        <div class="schematic">
          <svg viewBox="0 0 640 360" role="img" aria-labelledby="svg-title svg-desc">
            <title id="svg-title">Multispectral sensor schematic</title>
            <desc id="svg-desc">Diagram of the AETHER-X4 multispectral payload, telemetry link, and RTK lock.</desc>
            <rect x="0" y="0" width="640" height="360" fill="var(--surface)" />
            <rect x="40" y="40" width="600" height="320" rx="18" fill="var(--surface-dim)" stroke="var(--line)" stroke-width="2" />
            <rect x="70" y="70" width="180" height="90" rx="12" fill="var(--surface)" stroke="var(--line-strong)" stroke-width="2" />
            <rect x="260" y="70" width="180" height="90" rx="12" fill="var(--surface)" stroke="var(--line-strong)" stroke-width="2" />
            <rect x="450" y="70" width="180" height="90" rx="12" fill="var(--surface)" stroke="var(--line-strong)" stroke-width="2" />
            <text x="70" y="120" font-family="var(--font-mono)" font-size="16" fill="var(--ink)">MULTISPECTRAL</text>
            <text x="70" y="145" font-family="var(--font-mono)" font-size="14" fill="var(--ink-muted)">12-BAND PAYLOAD</text>
            <text x="260" y="120" font-family="var(--font-mono)" font-size="16" fill="var(--ink)">TELEMETRY LINK</text>
            <text x="260" y="145" font-family="var(--font-mono)" font-size="14" fill="var(--ink-muted)">2.4 GHZ ACTIVE</text>
            <text x="450" y="120" font-family="var(--font-mono)" font-size="16" fill="var(--ink)">RTK LOCK</text>
            <text x="450" y="145" font-family="var(--font-mono)" font-size="14" fill="var(--ink-muted)">NOMINAL</text>
            <line x1="70" y1="165" x2="260" y2="165" stroke="var(--accent)" stroke-width="3" />
            <line x1="260" y1="165" x2="450" y2="165" stroke="var(--signal)" stroke-width="3" />
            <circle cx="70" cy="165" r="6" fill="var(--accent)" />
            <circle cx="260" cy="165" r="6" fill="var(--signal)" />
            <circle cx="450" cy="165" r="6" fill="var(--accent-strong)" />
            <text x="70" y="205" font-family="var(--font-mono)" font-size="14" fill="var(--accent-strong)">BAND ROUTING</text>
            <text x="260" y="205" font-family="var(--font-mono)" font-size="14" fill="var(--ink-muted)">DATA PIPELINE</text>
            <text x="450" y="205" font-family="var(--font-mono)" font-size="14" fill="var(--ink-muted)">POSITIONING</text>
          </svg>
        </div>
      </div>
    </section>

    <section id="faq">
      <div class="container">
        <h2>Frequently Asked Questions</h2>
        <div class="faq">
          <details>
            <summary>What is AETHERIA BIO-ROBOTICS?</summary>
            <p>AETHERIA BIO-ROBOTICS is an autonomous environmental and precision agriculture drone platform.</p>
          </details>
          <details>
            <summary>Which platforms are available?</summary>
            <p>The AETHER-X4 Multispectral, AETHER-H8 Heavy Lidar, and AETHER-S2 Soil Probe platforms are available.</p>
          </details>
          <details>
            <summary>Can the calculator estimate battery swaps?</summary>
            <p>Yes. The flight-path coverage calculator estimates flight time, battery swaps, waypoint count, and coverage time.</p>
          </details>
          <details>
            <summary>How does the telemetry filter work?</summary>
            <p>The telemetry filter lets users isolate specific drone platforms and view related sensor, link, and payload metadata.</p>
          </details>
          <details>
            <summary>Is deployment inquiry validation client-side?</summary>
            <p>Yes. The deployment inquiry form uses client-side validation before submission.</p>
          </details>
        </div>
      </div>
    </section>

    <section id="deployment">
      <div class="container form-block">
        <h2>Fleet Deployment Inquiry</h2>
        <form id="deployment-form" class="panel form-grid" novalidate>
          <label for="contact-name">Contact Name</label>
          <input id="contact-name" name="contact-name" type="text" autocomplete="name" aria-describedby="form-status">

          <label for="contact-email">Email</label>
          <input id="contact-email" name="contact-email" type="email" autocomplete="email" aria-describedby="form-status">

          <label for="contact-org">Organization</label>
          <input id="contact-org" name="contact-org" type="text" autocomplete="organization" aria-describedby="form-status">

          <label for="contact-message">Deployment Request</label>
          <textarea id="contact-message" name="contact-message" aria-describedby="form-status"></textarea>

          <p id="form-status" class="status" aria-live="polite">Ready to validate deployment request.</p>
          <button class="button button-primary" type="submit">Submit Inquiry</button>
        </form>
      </div>
    </section>
  </main>

  <footer>
    <div class="container footer-meta">
      <span>AETHERIA BIO-ROBOTICS</span>
      <span>TELEMETRY LINK ACTIVE 2.4 GHZ</span>
      <span>LIDAR PAYLOAD 128-CH | IP67</span>
      <span>AETHERIA X4 | MULTISPECTRAL RTK</span>
    </div>
  </footer>
</body>
</html>
```

FILE: zimage_prompts.json
```json
[
  {
    "id": "x4-multispectral-frame",
    "target_section": "platform-cards",
    "aspect_ratio": "16:9",
    "steps": 9,
    "prompt": "Photorealistic industrial laboratory photograph of a high-tech bio-robotics drone platform on a bone-white bench surface. Carbon ink accents, forest telemetry green, and amber signal cues. Swiss typographic layout with crisp modular grid, instrument-grade typography, and telemetry overlays. The frame shows a compact multispectral sensor module, RTK antenna, and data cable routing. Exact readable English typography in quotes: \"AETHERIA X4 | MULTISPECTRAL RTK\". Clean, clinical, precise, no clutter, no CJK, no Cyrillic, no mojibake.",
    "exact_text_in_frame": "AETHERIA X4 | MULTISPECTRAL RTK"
  },
  {
    "id": "h8-lidar-frame",
    "target_section": "comparison-table",
    "aspect_ratio": "16:9",
    "steps": 9,
    "prompt": "Photorealistic industrial image of a heavy lidar payload drone platform in a controlled laboratory environment. Bone surface background, carbon ink labels, forest telemetry accents, and amber signal highlights. Modular Swiss grid composition with precise instrument typography and telemetry metadata. The frame includes a 128-channel lidar module, IP67 housing, carbon fiber frame, and sensor routing. Exact readable English typography in quotes: \"LIDAR PAYLOAD 128-CH | IP67\". Clean, high-tech, no clutter, no CJK, no Cyrillic, no mojibake.",
    "exact_text_in_frame": "LIDAR PAYLOAD 128-CH | IP67"
  },
  {
    "id": "s2-telemetry-frame",
    "target_section": "schematic",
    "aspect_ratio": "16:9",
    "steps": 9,
    "prompt": "Photorealistic industrial schematic frame featuring a soil probe drone payload connected to a telemetry link on a bone-white laboratory surface. Carbon ink typography, forest telemetry green, amber signal cues, and precise modular grid alignment. The frame shows a soil probe array, data pipeline, and telemetry link status. Exact readable English typography in quotes: \"TELEMETRY LINK ACTIVE 2.4 GHZ\". Clean, high-tech, no clutter, no CJK, no Cyrillic, no mojibake.",
    "exact_text_in_frame": "TELEMETRY LINK ACTIVE 2.4 GHZ"
  }
]
```

FILE: llms.txt
```txt
# AETHERIA BIO-ROBOT