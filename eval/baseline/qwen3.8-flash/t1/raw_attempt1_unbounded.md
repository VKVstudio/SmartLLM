FILE: index.html
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>THERMOTECH ENGINEERING — Industrial Hot-Water and Steam Boilers 5–25 MW</title>
  <meta name="description" content="THERMOTECH ENGINEERING manufactures industrial hot-water and steam boilers from 5 to 25 MW for district heating, process heat, and power generation. ISO and GOST certified, PLC controls, 14–20 week lead times.">
  <link rel="canonical" href="https://www.thermotech-engineering.example/">
  <meta name="robots" content="index,follow">
  <meta property="og:type" content="website">
  <meta property="og:title" content="THERMOTECH ENGINEERING — Industrial Hot-Water and Steam Boilers 5–25 MW">
  <meta property="og:description" content="Industrial hot-water and steam boilers from 5 to 25 MW. ISO and GOST certified, PLC controls, 14–20 week lead times.">
  <meta property="og:url" content="https://www.thermotech-engineering.example/">
  <meta property="og:image" content="https://www.thermotech-engineering.example/og-cover.png">
  <meta property="og:image:alt" content="THERMOTECH ENGINEERING industrial boiler schematic">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="THERMOTECH ENGINEERING — Industrial Hot-Water and Steam Boilers 5–25 MW">
  <meta name="twitter:description" content="Industrial hot-water and steam boilers from 5 to 25 MW. ISO and GOST certified, PLC controls, 14–20 week lead times.">
  <meta name="twitter:image" content="https://www.thermotech-engineering.example/og-cover.png">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'sha256-Y2ZkN2E1YjIzNGM2ZDhlMGYxMjM0NTY3ODlhYmNkZWYwMTIzNDU2Nzg5YWJjZGVm'; script-src 'sha256-MTJhM2I0YzVkNmU3ZjhhYjEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmM=' 'sha256-YWJjZGVmMTIzNDU2Nzg5MGFiY2RlZjEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY='; img-src 'self' data:; font-src 'self'; connect-src 'none'; form-action 'self'; base-uri 'none'; object-src 'none'; frame-src 'none'; child-src 'none'; worker-src 'none'; manifest-src 'self'; upgrade-insecure-requests;">

  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' fill='%230d0f12'/%3E%3Cpath d='M14 48h36M22 18h20v24H22z' fill='none' stroke='%23ff8a3d' stroke-width='4'/%3E%3C/svg%3E">

  <style>
    :root {
      --bg: oklch(0.12 0.01 255);
      --surface: oklch(0.16 0.012 255);
      --surface-2: oklch(0.20 0.014 255);
      --grid: oklch(0.223 0.012 255);
      --line: oklch(0.30 0.015 255);
      --line-strong: oklch(0.42 0.018 255);
      --text: oklch(0.97 0.005 255);
      --muted: oklch(0.82 0.008 255);
      --accent: oklch(0.68 0.19 45);
      --accent-ink: oklch(0.12 0.02 45);
      --accent-soft: oklch(0.68 0.19 45 / 0.18);
      --danger: oklch(0.72 0.19 25);
      --success: oklch(0.80 0.15 150);
      --focus: oklch(0.88 0.16 45);
      --sans: 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      --mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace;
      --page-max: 1280px;
      --gutter: clamp(1rem, 3vw, 2rem);
      --section-y: clamp(3rem, 8vw, 6rem);
    }

    * { box-sizing: border-box; }

    html {
      scroll-behavior: smooth;
      background: var(--bg);
      color: var(--text);
    }

    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
      *, *::before, *::after {
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001ms !important;
        scroll-behavior: auto !important;
      }
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: var(--sans);
      font-size: 1rem;
      line-height: 1.55;
      background-color: var(--bg);
      background-image:
        linear-gradient(to right, var(--grid) 1px, transparent 1px),
        linear-gradient(to bottom, var(--grid) 1px, transparent 1px);
      background-size: 32px 32px;
      background-position: 0 0;
    }

    [hidden] { display: none !important; }

    .skip-link {
      position: absolute;
      left: -9999px;
      top: 0;
      display: inline-block;
      padding: 0.75rem 1rem;
      background: var(--accent);
      color: var(--accent-ink);
      font-family: var(--mono);
      font-size: 0.875rem;
      text-decoration: none;
      z-index: 100;
    }

    .skip-link:focus-visible {
      left: 1rem;
      top: 1rem;
    }

    .wrap {
      width: min(100%, var(--page-max));
      margin-inline: auto;
      padding-inline: var(--gutter);
    }

    .site-header {
      position: sticky;
      top: 0;
      z-index: 20;
      background: oklch(0.12 0.01 255 / 0.92);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(6px);
    }

    .site-header .wrap {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      min-height: 72px;
    }

    .brand {
      display: inline-flex;
      align-items: center;
      gap: 0.75rem;
      color: var(--text);
      text-decoration: none;
      font-family: var(--mono);
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: clamp(0.9rem, 2vw, 1.05rem);
    }

    .brand-mark {
      width: 34px;
      height: 34px;
      flex: 0 0 auto;
      display: block;
    }

    .brand-mark .bm-frame { fill: none; stroke: var(--accent); stroke-width: 2; }
    .brand-mark .bm-core { fill: var(--accent); }

    .site-nav {
      display: flex;
      gap: 1.25rem;
      align-items: center;
      flex-wrap: wrap;
      font-family: var(--mono);
      font-size: 0.875rem;
    }

    .site-nav a {
      color: var(--muted);
      text-decoration: none;
      border-bottom: 1px solid transparent;
      padding-bottom: 0.125rem;
    }

    .site-nav a:hover,
    .site-nav a:focus-visible {
      color: var(--text);
      border-bottom-color: var(--accent);
    }

    .site-nav .nav-cta {
      color: var(--accent-ink);
      background: var(--accent);
      padding: 0.5rem 0.85rem;
      border: 1px solid var(--accent);
    }

    .site-nav .nav-cta:hover,
    .site-nav .nav-cta:focus-visible {
      color: var(--accent-ink);
      outline: 2px solid var(--focus);
      outline-offset: 2px;
    }

    main {
      display: block;
    }

    section {
      padding-block: var(--section-y);
      border-bottom: 1px solid var(--line);
    }

    .section-head {
      display: grid;
      gap: 0.75rem;
      margin-bottom: 2rem;
    }

    .eyebrow {
      font-family: var(--mono);
      font-size: 0.8125rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      margin: 0;
    }

    h1, h2, h3 {
      margin: 0;
      line-height: 1.12;
      letter-spacing: -0.01em;
    }

    h1 {
      font-size: clamp(2.25rem, 6vw, 4.25rem);
      font-weight: 700;
    }

    h2 {
      font-size: clamp(1.75rem, 4vw, 2.5rem);
      font-weight: 700;
    }

    h3 {
      font-size: 1.125rem;
      font-weight: 700;
    }

    p {
      margin: 0;
    }

    .lead {
      font-size: clamp(1.05rem, 2vw, 1.25rem);
      color: var(--muted);
      max-width: 70ch;
    }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
      gap: clamp(2rem, 5vw, 4rem);
      align-items: start;
    }

    .hero-copy {
      display: grid;
      gap: 1.25rem;
    }

    .hero-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-top: 0.5rem;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      min-height: 48px;
      padding: 0.75rem 1.1rem;
      font-family: var(--mono);
      font-size: 0.9375rem;
      font-weight: 700;
      letter-spacing: 0.03em;
      text-decoration: none;
      border: 1px solid var(--line-strong);
      background: var(--surface);
      color: var(--text);
    }

    .btn-primary {
      background: var(--accent);
      color: var(--accent-ink);
      border-color: var(--accent);
    }

    .btn:hover,
    .btn:focus-visible {
      outline: 2px solid var(--focus);
      outline-offset: 2px;
    }

    .hero-metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1px;
      background: var(--line);
      border: 1px solid var(--line);
      margin-top: 2rem;
    }

    .metric {
      background: var(--surface);
      padding: 1rem;
      min-height: 112px;
      display: grid;
      align-content: start;
      gap: 0.35rem;
    }

    .metric strong {
      font-family: var(--mono);
      font-size: clamp(1.5rem, 3vw, 2.25rem);
      line-height: 1;
      color: var(--accent);
    }

    .metric span {
      color: var(--muted);
      font-size: 0.875rem;
    }

    .hero-panel {
      background: var(--surface);
      border: 1px solid var(--line);
      padding: 1.25rem;
      display: grid;
      gap: 1rem;
    }

    .hero-panel-title {
      font-family: var(--mono);
      font-size: 0.8125rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      border-bottom: 1px solid var(--line);
      padding-bottom: 0.75rem;
    }

    .spec-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 0.75rem;
    }

    .spec-list li {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 1rem;
      align-items: baseline;
      border-bottom: 1px dashed var(--line);
      padding-bottom: 0.75rem;
    }

    .spec-list li:last-child {
      border-bottom: 0;
      padding-bottom: 0;
    }

    .spec-list span {
      color: var(--muted);
      font-size: 0.9375rem;
    }

    .spec-list strong {
      font-family: var(--mono);
      font-size: 0.9375rem;
      color: var(--text);
      text-align: right;
    }

    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--line);
      background: var(--surface);
    }

    table {
      width: 100%;
      min-width: 980px;
      border-collapse: collapse;
      font-size: 0.9375rem;
    }

    caption {
      text-align: left;
      caption-side: top;
      padding: 1rem;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-family: var(--mono);
      font-size: 0.8125rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: var(--surface-2);
    }

    th, td {
      border-bottom: 1px solid var(--line);
      padding: 0.9rem 1rem;
      text-align: left;
      vertical-align: top;
    }

    thead th {
      background: var(--surface-2);
      color: var(--text);
      font-family: var(--mono);
      font-size: 0.8125rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      position: sticky;
      top: 0;
    }

    tbody tr:hover {
      background: oklch(0.20 0.014 255 / 0.7);
    }

    .model-cell {
      display: grid;
      gap: 0.25rem;
      min-width: 180px;
    }

    .model-cell strong {
      font-family: var(--mono);
      font-size: 1rem;
      color: var(--accent);
    }

    .model-cell span {
      color: var(--muted);
      font-size: 0.875rem;
    }

    .mono {
      font-family: var(--mono);
    }

    .schematic {
      display: block;
      width: 100%;
      height: auto;
      aspect-ratio: 16 / 9;
      background: var(--surface);
      border: 1px solid var(--line);
    }

    .schematic-bg { fill: var(--surface); }
    .schematic-grid { stroke: var(--grid); stroke-width: 1; }
    .schematic-frame { fill: var(--surface-2); stroke: var(--line-strong); stroke-width: 2; }
    .schematic-accent-frame { fill: var(--surface-2); stroke: var(--accent); stroke-width: 2; }
    .schematic-line { stroke: var(--line-strong); stroke-width: 2; fill: none; }
    .schematic-feed { stroke: var(--muted); stroke-width: 3; fill: none; }
    .schematic-steam { stroke: var(--accent); stroke-width: 4; fill: none; }
    .schematic-gas { stroke: var(--danger); stroke-width: 3; fill: none; }
    .schematic-arrow { fill: var(--accent); }
    .schematic-text {
      fill: var(--text);
      font-family: