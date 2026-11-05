FILE: index.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'sha256-Zm9vYmFyLWludmFsaWQtaGFzaA==;' 'nonce-vortex-2024'; style-src 'sha256-Zm9vYmFyLWludmFsaWQtaGFzaA==;' 'nonce-vortex-2024'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests; report-uri /csp-report">

  <title>VORTEX COMPUTE | Sovereign Distributed GPU & NVMe-over-Fabrics Inference Engine for MoE Models</title>
  <meta name="description" content="VORTEX COMPUTE is a sovereign distributed GPU and NVMe-over-Fabrics inference engine for low-latency mixture-of-experts models. Size VRAM, throughput, benchmarks, and request cluster provisioning.">
  <link rel="canonical" href="https://vortexcompute.example/index.html">

  <meta property="og:type" content="website">
  <meta property="og:title" content="VORTEX COMPUTE | Sovereign Distributed GPU & NVMe-over-Fabrics Inference Engine">
  <meta property="og:description" content="Low-latency MoE inference with RDMA tensor sharding, speculative tree verification, NVMe page-cache pinning, zero-copy KV ring, deterministic quantization, and hardware enclave isolation.">
  <meta property="og:url" content="https://vortexcompute.example/index.html">
  <meta property="og:image" content="https://vortexcompute.example/vortex-og.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">

  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='oklch(0.13 0.02 260)'/%3E%3Cpath d='M16 14h10l12 20 12-20h10L38 46h-12z' fill='oklch(0.76 0.15 195)'/%3E%3Cpath d='M22 18h6l8 14 8-14h6L40 38h-8z' fill='oklch(0.72 0.17 155)'/%3E%3C/svg%3E">

  <style nonce="vortex-2024">
    :root {
      --obsidian: oklch(0.13 0.02 260);
      --surface: oklch(0.18 0.02 260);
      --surface-2: oklch(0.21 0.025 260);
      --hairline: oklch(0.28 0.03 260);
      --hairline-strong: oklch(0.36 0.04 260);
      --alabaster: oklch(0.95 0.01 250);
      --muted: oklch(0.78 0.02 250);
      --cyan: oklch(0.76 0.15 195);
      --emerald: oklch(0.72 0.17 155);
      --danger: oklch(0.78 0.14 25);
      --amber: oklch(0.82 0.12 90);
      --mono: ui-monospace, "SFMono-Regular", "Menlo", "Monaco", "Cascadia Code", monospace;
      --sans: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
      --radius: 16px;
      --radius-sm: 10px;
      --shadow: 0 18px 48px color-mix(in oklch, var(--obsidian) 70%, transparent);
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--alabaster);
      background:
        radial-gradient(circle at 12% 8%, color-mix(in oklch, var(--cyan) 10%, transparent), transparent 34%),
        radial-gradient(circle at 88% 18%, color-mix(in oklch, var(--emerald) 8%, transparent), transparent 30%),
        var(--obsidian);
      font-family: var(--sans);
      font-size: 16px;
      line-height: 1.65;
      text-rendering: optimizeLegibility;
    }

    ::selection { background: color-mix(in oklch, var(--cyan) 35%, var(--obsidian)); color: var(--alabaster); }
    :focus-visible { outline: 2px solid var(--cyan); outline-offset: 3px; }

    .skip-link {
      position: absolute; left: 12px; top: -40px; z-index: 100;
      background: var(--surface); color: var(--alabaster); border: 1px solid var(--hairline);
      padding: 10px 14px; border-radius: var(--radius-sm);
    }
    .skip-link:focus { top: 12px; }

    .page {
      width: min(1180px, calc(100% - 32px));
      margin-inline: auto;
    }

    header.site-header {
      position: sticky; top: 0; z-index: 20;
      backdrop-filter: blur(14px);
      background: color-mix(in oklch, var(--obsidian) 82%, transparent);
      border-bottom: 1px solid var(--hairline);
    }
    .header-inner {
      display: flex; align-items: center; justify-content: space-between; gap: 18px;
      min-height: 68px; padding: 10px 0;
    }
    .brand {
      display: inline-flex; align-items: center; gap: 12px;
      text-decoration: none; color: var(--alabaster);
      font-weight: 700; letter-spacing: .08em;
    }
    .brand-mark {
      width: 38px; height: 38px; border-radius: 12px;
      border: 1px solid var(--hairline);
      background: linear-gradient(135deg, color-mix(in oklch, var(--cyan) 24%, var(--surface)), var(--surface));
      display: grid; place-items: center;
    }
    .brand-mark svg { width: 24px; height: 24px; }
    .brand small { display: block; font-size: 11px; color: var(--muted); letter-spacing: .12em; }

    nav.primary-nav ul {
      list-style: none; margin: 0; padding: 0;
      display: flex; gap: 8px; flex-wrap: wrap;
    }
    nav.primary-nav a {
      display: inline-flex; align-items: center; gap: 8px;
      color: var(--muted); text-decoration: none;
      border: 1px solid transparent; padding: 8px 12px; border-radius: 999px;
      font-size: 13px; letter-spacing: .06em; text-transform: uppercase;
    }
    nav.primary-nav a:hover, nav.primary-nav a:focus-visible {
      color: var(--alabaster); border-color: var(--hairline); background: var(--surface);
    }

    .hero {
      display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 560px);
      gap: 28px; align-items: stretch; padding: 34px 0 42px;
    }
    .eyebrow {
      display: inline-flex; align-items: center; gap: 10px;
      color: var(--cyan); font: 700 12px/1 var(--mono); letter-spacing: .16em; text-transform: uppercase;
      border: 1px solid color-mix(in oklch, var(--cyan) 30%, var(--hairline));
      background: color-mix(in oklch, var(--cyan) 10%, var(--surface));
      padding: 8px 12px; border-radius: 999px;
    }
    h1 {
      margin: 18px 0 14px;
      font-size: clamp(40px, 6vw, 74px);
      line-height: 0.96;
      letter-spacing: -0.045em;
      font-weight: 800;
      text-wrap: balance;
    }
    h1 .accent { color: var(--cyan); }
    .hero-copy p {
      max-width: 64ch; color: var(--muted); font-size: clamp(16px, 1.6vw, 19px);
    }
    .hero-actions {
      display: flex; flex-wrap: wrap; gap: 12px; margin-top: 24px;
    }
    .btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 10px;
      min-height: 46px; padding: 12px 18px; border-radius: var(--radius-sm);
      border: 1px solid var(--hairline); background: var(--surface); color: var(--alabaster);
      text-decoration: none; font-weight: 650; letter-spacing: .02em; cursor: pointer;
      transition: border-color 160ms ease, background-color 160ms ease, color 160ms ease;
    }
    .btn:hover { border-color: var(--hairline-strong); background: var(--surface-2); }
    .btn-primary {
      border-color: color-mix(in oklch, var(--cyan) 45%, var(--hairline));
      background: color-mix(in oklch, var(--cyan) 18%, var(--surface));
    }
    .btn-primary:hover { background: color-mix(in oklch, var(--cyan) 24%, var(--surface)); }

    .canvas-panel {
      position: relative; min-height: 420px; border: 1px solid var(--hairline);
      border-radius: var(--radius); overflow: hidden; background: var(--surface);
      box-shadow: var(--shadow);
    }
    canvas {
      display: block; width: 100%; height: 100%;
      background: var(--obsidian);
    }
    .telemetry {
      position: absolute; inset: 0; pointer-events: none;
      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px;
      padding: 12px; font: 600 11px/1.25 var(--mono); color: var(--alabaster);
    }
    .telemetry span {
      display: inline-flex; align-items: center; gap: 8px;
      border: 1px solid color-mix(in oklch, var(--hairline) 80%, transparent);
      background: color-mix(in oklch, var(--obsidian) 72%, transparent);
      padding: 8px 10px; border-radius: 8px;
    }
    .dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--emerald); box-shadow: 0 0 14px color-mix(in oklch, var(--emerald) 70%, transparent);
    }
    .dot.cyan { background: var(--cyan); box-shadow: 0 0 14px color-mix(in oklch, var(--cyan) 70%, transparent); }
    .dot.amber { background: var(--amber); box-shadow: 0 0 14px color-mix(in oklch, var(--amber) 70%, transparent); }

    .status-strip {
      display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px;
      margin: 0 0 38px;
    }
    .status-card {
      min-height: 112px; padding: 16px; border: 1px solid var(--hairline);
      border-radius: var(--radius); background: var(--surface);
    }
    .status-card strong { display: block; font: 700 24px/1 var(--mono); color: var(--cyan); }
    .status-card span { display: block; margin-top: 10px; color: var(--muted); font-size: 13px; }

    section {
      padding: 54px 0; border-top: 1px solid var(--hairline);
    }
    .section-head {
      display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 520px);
      gap: 24px; align-items: end; margin-bottom: 28px;
    }
    h2 {
      margin: 0; font-size: clamp(28px, 4vw, 44px); line-height: 1.05; letter-spacing: -0.035em;
    }
    .section-head p { margin: 0; color: var(--muted); }

    .bento {
      display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 16px;
    }
    .pillar {
      border: 1px solid var(--hairline); border-radius: var(--radius); background: var(--surface);
      padding: 22px; display: grid; gap: 16px; min-height: 260px;
      transition: transform 180ms ease, border-color 180ms ease, background-color 180ms ease;
    }
    .pillar:hover { transform: translateY(-2px); border-color: var(--hairline-strong); background: var(--surface-2); }
    .pillar:nth-child(1) { grid-column: span 3; }
    .pillar:nth-child(2) { grid-column: span 3; }
    .pillar:nth-child(3) { grid-column: span 2; }
    .pillar:nth-child(4) { grid-column: span 4; }
    .pillar:nth-child(5) { grid-column: span 3; }
    .pillar:nth-child(6) { grid-column: span 3; }

    .pillar h3 { margin: 0; font-size: 21px; letter-spacing: -0.02em; }
    .pillar p { margin: 0; color: var(--muted); font-size: 15px; }
    .diagram {
      width: 100%; height: 128px; border: 1px solid var(--hairline);
      border-radius: 12px; background: color-mix(in oklch, var(--obsidian) 72%, var(--surface));
      overflow: hidden;
    }
    .diagram svg { width: 100%; height: 100%; display: block; }

    .calculator {
      display: grid; grid-template-columns: minmax(0, 560px) minmax(0, 1fr); gap: 20px;
      align-items: start;
    }
    form.calc-form {
      display: grid; gap: 16px; padding: 22px; border: 1px solid var(--hairline);
      border-radius: var(--radius); background: var(--surface);
    }
    .field {
      display: grid; gap: 8px;
    }
    .field label { font-size: 13px; color: var(--muted); letter-spacing: .04em; }
    .field input, .field select, .field textarea {
      width: 100%; color: var(--alabaster); background: var(--obsidian);
      border: 1px solid var(--hairline); border-radius: var(--radius-sm);
      padding: 12px 14px; font: 500 15px var(--sans);
    }
    .field input:focus, .field select:focus, .field textarea:focus { border-color: var(--cyan); }
    .field textarea { min-height: 112px; resize: vertical; }
    .range-row {
      display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center;
    }
    output {
      font: 700 13px/1 var(--mono); color: var(--cyan);
      border: 1px solid color-mix(in oklch, var(--cyan) 35%, var(--hairline));
      padding: 8px 10px; border-radius: 8px; background: color-mix(in oklch, var(--cyan) 12%, var(--obsidian));
    }

    .results {
      display: grid; gap: 12px;
    }
    .result-card {
      border: 1px solid var(--hairline); border-radius: var(--radius); background: var(--surface);
      padding: 18px; display: grid; gap: 8px;
    }
    .result-card strong { font: 700 32px/1 var(--mono); color: var(--emerald); }
    .result-card span { color: var(--muted); font-size: 13px; }
    .result-grid {
      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px;
    }

    .table-wrap {
      overflow: auto; border: 1px solid var(--hairline); border-radius: var(--radius);
      background: var(--surface); box-shadow: var(--shadow);
    }
    table {
      width: 100%; border-collapse: collapse; min-width: 900px;
      font: 500 14px/1.45 var(--mono); color: var(--alabaster);
    }
    th, td {
      padding: 16px; border-bottom: 1px solid var(--hairline); text-align: left;
      white-space: nowrap;
    }
    th {
      color: var(--cyan); font-size: 12px; letter-spacing: .12em; text-transform: uppercase;
      background: color-mix(in oklch, var(--surface-2) 80%, var(--obsidian));
    }
    tbody tr:last-child td { border-bottom: 0; }
    td.metric { color: var(--emerald); }
    .tier {
      display: inline-flex; align-items: center; gap: 10px; font-weight: 700;
    }
    .tier-badge {
      width: 10px; height: 10px; border-radius: 50%; background: var(--cyan);
      box-shadow: 0 0 12px color-mix(in oklch, var(--cyan) 80%, transparent);
    }
    .tier-badge.emerald { background: var(--emerald); box-shadow: 0 0 12px color-mix(in oklch, var(--emerald) 80%, transparent); }

    .faq {
      display: grid; gap: 12px;
    }
    details {
      border: 1px solid var(--hairline); border-radius: var(--radius); background: var(--surface);
      padding: 18px 20px;
    }
    summary {
      cursor: pointer; font-weight: 700; font-size: 18px; list-style: none;
      display: flex; justify-content: space-between; gap: 16px; align-items: center;
    }
    summary::-webkit-details-marker { display: none; }
    summary::after {
      content: "+"; color: var(--cyan); font: 700 22px/1 var(--mono);
    }
    details[open] summary::after { content: "−"; }
    details p { margin: 12px 0 0; color: var(--muted); }

    .provision {
      display: grid; grid-template-columns: minmax(0, 520px) minmax(0, 1fr); gap: 20px;
      align-items: start;
    }
    .provision-copy {
      display: grid; gap: 14px; color: var(--muted);
    }
    .provision-copy ul { margin: 0; padding-left: 20px; }
    .provision-copy li { margin: 8px 0; }
    .form-status {
      margin-top: 12px; border: 1px solid var(--hairline); border-radius: var(--radius-sm);
      padding: 12px; font: 600 13px/1.35 var(--mono); color: var(--emerald);
      background: color-mix(in oklch, var(--emerald) 10%, var(--obsidian));
    }
    .form-status.error { color: var(--danger); background: color-mix(in oklch, var(--danger) 10%, var(--obsidian)); }

    footer {
      border-top: 1px solid var(--hairline); padding: 34px 0 46px;
      display: grid; gap: 18px; color: var(--muted); font-size: 13px;
    }
    .footer-grid {
      display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 420px) minmax(0, 320px); gap: 24px;
    }
    footer a { color: var(--cyan); text-decoration: none; }
    footer a:hover { text-decoration: underline; }
    .footer-meta { font: 500 12px/1.45 var(--mono); }

    @media (max-width: 980px) {
      .hero, .section-head, .calculator, .provision, .footer-grid {
        grid-template-columns: 1fr;
      }
      .bento { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .pillar:nth-child(n) { grid-column: span 2; }
      .status-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .result-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    @media (max-width: 680px) {
      .bento { grid-template-columns: 1fr; }
      .pillar:nth-child(n) { grid-column: span 1; }
      .status-strip, .result-grid { grid-template-columns: 1fr; }
      nav.primary-nav a { padding: 7px 10px; font-size: 12px; }
    }

    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
      *, *::before, *::after { animation: none !important; transition: none !important; }
    }
  </style>

  <script nonce="vortex-2024">
    const vortexState = {
      fps: 0,
      latencyMs: 0,
      tokensPerSec: 0,
      running: true,
      mode: "webgl2",
      startTime: performance.now(),
      frameCount: 0,
      lastFrame: performance.now(),
      lastTelemetry: performance.now()
    };

    const $ = (sel, root = document) => root.querySelector(sel);

    function clamp(value, min, max) {
      return Math.min(max, Math.max(min, value));
    }

    function format(value, digits = 1) {
      return Number(value).toLocaleString("en-US", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
      });
    }

    function estimateInference(params) {
      const active = clamp(params.activeParams, 0.1, 120);
      const total = clamp(params.totalParams, active, 2600);
      const bpw = clamp(params.bpw, 2, 16);
      const batch = clamp(params.batch, 1, 128);
      const pcie = params.pcie === "gen5" ? 64 : params.pcie === "gen4" ? 32 : 16;
      const experts = Math.max(8, Math.round(total / active));
      const activeBytes = active * 1e9 * bpw / 8;
      const totalBytes = total * 1e9 * bpw / 8;
      const kvBytes = batch * 4096 * 2 * 16;
      const overhead = 1.18;
      const vramGB = (activeBytes * 0.38 + kvBytes * 1.15 + 1.2e9) * overhead / 1e9;
      const ramGB = (totalBytes * 0.72 + activeBytes * 0.28 + kvBytes * 0.55 + 4e9) * overhead / 1e9;
      const bandwidthTok = pcie * 0.78 * (16 / bpw) * 0.92;
      const expertPenalty = 1 / Math.pow(experts / 8, 0.18);
      const batchGain = 0.74 + Math.log2(batch + 1) * 0.22;
      const activeGain = Math.pow(active / 7, 0.62);
      const tokPerSec = clamp(
        bandwidthTok * expertPenalty * batchGain * activeGain * 2.8,
        2,
        4200
      );
      const latencyMs = clamp(1000 / (tokPerSec / batch), 0.22, 520);
      const contextGB = clamp((batch * 4096 * 2 * 16) / 1e9, 0.02, 24);
      return {
        vramGB,
        ramGB,
        tokPerSec,
        latencyMs,
        contextGB,
        experts
      };
    }

    function updateCalculator() {
      const form = $("#sizing-form");
      if (!form) return;
      const data = new FormData(form);
      const params = {
        activeParams: Number(data.get("active") || 7),
        totalParams: Number(data.get("total") || 47),
        bpw: Number(data.get("bpw") || 4),
        pcie: String(data.get("pcie") || "gen4"),
        batch: Number(data.get("batch") || 8)
      };
      const result = estimateInference(params);

      $("#out-active").textContent = `${format(params.activeParams)}B active`;
      $("#out-total").textContent = `${format(params.totalParams)}B total`;
      $("#out-bpw").textContent = `${params.bpw} bpw`;
      $("#out-batch").textContent = `${params.batch} batch`;
      $("#out-pcie").textContent = params.pcie.toUpperCase();

      $("#vram-value").textContent = `${format(result.vramGB)} GB`;
      $("#ram-value").textContent = `${format(result.ramGB)} GB`;
      $("#throughput-value").textContent = `${format(result.tokPerSec)} tok/s`;
      $("#latency-value").textContent = `${format(result.latencyMs, 2)} ms/token`;
      $("#context-value").textContent = `${format(result.contextGB)} GB KV`;
      $("#expert-value").textContent = `${result.experts} routed experts`;
    }

    function validateProvisionForm(event) {
      event.preventDefault();
      const form = $("#provision-form");
      const status = $("#provision-status");
      if (!form || !status) return;

      const data = new FormData(form);
      const required = ["organization", "email", "tier", "region", "message"];
      const email = String(data.get("email") || "");
      const message = String(data.get("message") || "");
      const errors = [];

      required.forEach(name => {
        if (!String(data.get(name) || "").trim()) {
          errors.push(`${name} is required.`);
        }
      });

      if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
        errors.push("Enter a valid work email address.");
      }

      if (message.length < 24) {
        errors.push("Describe the cluster request in at least 24 characters.");
      }

      if (errors.length) {
        status.classList.add("error");
        status.setAttribute("aria-live", "assertive");
        status.textContent = `Validation failed: ${errors.join(" ")}`;
        form.setAttribute("aria-invalid", "true");
        return;
      }

      status.classList.remove("error");
      status.setAttribute("aria-live", "polite");
      status.textContent = "Request accepted. Provisioning dossier generated locally. Reference: VTX-" +
        String(Math.floor(Math.random() * 900000) + 100000);
      form.setAttribute("aria-invalid", "false");
      form.reset();
    }

    function initCalculator() {
      const form = $("#sizing-form");
      if (!form) return;
      updateCalculator();
      form.addEventListener("input", updateCalculator);
      form.addEventListener("change", updateCalculator);
    }

    function initProvisionForm() {
      const form = $("#provision-form");
      if (!form) return;
      form.addEventListener("submit", validateProvisionForm);
    }

    function createCanvasFallback(canvas, ctx2d) {
      let raf = 0;
      let t = 0;
      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      function draw() {
        if (!ctx2d) return;
        const width = canvas.width;
        const height = canvas.height;
        ctx2d.fillStyle = "oklch(0.13 0.02 260)";
        ctx2d.fillRect(0, 0, width, height);

        const cols = 14;
        const rows = 8;
        const cellW = width / cols;
        const cellH = height / rows;

        for (let y = 0; y < rows; y++) {
          for (let x = 0; x < cols; x++) {
            const phase = reduced ? 0 : Math.sin(t * 0.002 + x * 0.7 + y * 0.45);
            const intensity = 0.18 + 0.34 * (phase + 1) / 2;
            ctx2d.strokeStyle = `color-mix(in oklch, oklch(0.28 0.03 260) ${40 + intensity * 45}%, transparent)`;
            ctx2d.strokeRect(x * cellW + 1, y * cellH + 1, cellW - 2, cellH - 2);

            ctx2d.fillStyle = phase > 0.55
              ? "color-mix(in oklch, oklch(0.76 0.15 195) 55%, transparent)"
              : phase < -0.35
                ? "color-mix(in oklch, oklch(0.72 0.17 155) 45%, transparent)"
                : "color-mix(in oklch, oklch(0.95 0.01 250) 12%, transparent)";

            const size = 3 + intensity * 5;
            ctx2d.fillRect(
              x * cellW + cellW / 2 - size / 2,
              y * cellH + cellH / 2 - size / 2,
              size,
              size
            );
          }
        }

        if (!reduced) t += 16;
        updateTelemetry();
        raf = requestAnimationFrame(draw);
      }

      draw();
      return () => cancelAnimationFrame(raf);
    }

    function initWebGL(canvas) {
      const gl = canvas.getContext("webgl2", { antialias: false, alpha: false, desynchronized: true });
      if (!gl) return null;

      const vertexSource = `#version 300 es
        precision highp float;
        in vec2 aPosition;
        out vec2 vUv;
        void main() {
          vUv = aPosition * 0.5 + 0.5;
          gl_Position = vec4(aPosition, 0.0, 1.0);
        }
      `;

      const fragmentSource = `#version 300 es
        precision highp float;
        in vec2 vUv;
        out vec4 fragColor;

        uniform vec2 uResolution;
        uniform float uTime;
        uniform float uMotion;
        uniform float uLatency;

        float hash(vec2 p) {
          return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
        }

        float noise(vec2 p) {
          vec2 i = floor(p);
          vec2 f = fract(p);
          vec2 u = f * f * (3.0 - 2.0 * f);
          return mix(
            mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
            mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
            u.y
          );
        }

        float fbm(vec2 p) {
          float value = 0.0;
          float amplitude = 0.55;
          for (int i = 0; i < 5; i++) {
            value += amplitude * noise(p);
            p *= 2.02;
            amplitude *= 0.52;
          }
          return value;
        }

        vec3 oklchApprox(float L, float C, float H) {
          // Stylized approximation for visual telemetry only.
          float h = radians(H);
          float a = C * cos(h);
          float b = C * sin(h);
          vec3 rgb = vec3(
            L + 0.82 * a + 0.18 * b,
            L - 0.08 * a + 0.34 * b,
            L - 0.12 * a - 0.28 * b
          );
          return clamp(rgb, 0.0, 1.0);
        }

        void main() {
          vec2 uv = vUv;
          vec2 p = (uv - 0.5) * vec2(uResolution.x / max(uResolution.y, 1.0), 1.0);
          float t = uTime * 0.28 * uMotion;

          vec2 warp = vec2(
            fbm(p * 2.4 + vec2(t * 0.22, -t * 0.17)),
            fbm(p * 2.8 + vec2(-t * 0.25, t * 0.19))
          );

          float field = fbm(p * 3.0 + warp * 1.2);
          float routing = smoothstep(0.42, 0.86, field);
          float edge = smoothstep(0.18, 0.72, abs(sin(p.x * 18.0 + t) * cos(p.y * 16.0 - t * 0.8)));
          float latencyPulse = exp(-abs(fract(t * 0.7) - 0.5) * 14.0) * (0.35 + uLatency * 0.03);

          vec3 cyan = oklchApprox(0.76, 0.15, 195.0);
          vec3 emerald = oklchApprox(0.72, 0.17, 155.0);
          vec3 obsidian = oklchApprox(0.13, 0.02, 260.0);
          vec3 slate = oklchApprox(0.18, 0.02, 260.0);
          vec3 hairline = oklchApprox(0.28, 0.03, 260.0);
          vec3 alabaster = oklchApprox(0.95, 0.01, 250.0);

          vec3 color = mix(obsidian, slate, smoothstep(0.2, 0.8, field));
          color = mix(color, hairline, edge * 0.22);
          color = mix(color, cyan, routing * 0.58);
          color = mix(color, emerald, smoothstep(0.58, 0.98, field) * 0.36);
          color += cyan * latencyPulse * 0.18;
          color += alabaster * pow(routing, 3.0) * 0.08;

          vec2 vign = smoothstep(0.78, 0.18, length(p));
          color *= mix(0.72, 1.0, vign);

          float scan = 0.985 + 0.015 * sin((uv.y * 220.0) + t * 1.2);
          color *= scan;

          fragColor = vec4(color, 1.0);
        }
      `;

      function compile(type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
          const info = gl.getShaderInfoLog(shader);
          gl.deleteShader(shader);
          throw new Error(info || "Shader compile failed");
        }
        return shader;
      }

      try {
        const program = gl.createProgram();
        gl.attachShader(program, compile(gl.VERTEX_SHADER, vertexSource));
        gl.attachShader(program, compile(gl.FRAGMENT_SHADER, fragmentSource));
        gl.bindAttribLocation(program, 0, "aPosition");
        gl.linkProgram(program);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
          throw new Error(gl.getProgramInfoLog(program) || "Program link failed");
        }

        const buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
          -1, -1, 1, -1, -1, 1,
          -1, 1, 1, -1, 1, 1
        ]), gl.STATIC_DRAW);

        gl.useProgram(program);
        gl.enableVertexAttribArray(0);
        gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

        const uResolution = gl.getUniformLocation(program, "uResolution");
        const uTime = gl.getUniformLocation(program, "uTime");
        const uMotion = gl.getUniformLocation(program, "uMotion");
        const uLatency = gl.getUniformLocation(program, "uLatency");

        let raf = 0;
        const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        let paused = reduced;
        let pausedTime = 0;

        function resize() {
          const dpr = Math.min(window.devicePixelRatio || 1, 2);
          const rect = canvas.getBoundingClientRect();
          const width = Math.max(1, Math.floor(rect.width * dpr));
          const height = Math.max(1, Math.floor(rect.height * dpr));
          canvas.width = width;
          canvas.height = height;
          gl.viewport(0, 0, width, height);
          gl.uniform2f(uResolution, width, height);
        }

        function render(now) {
          const elapsed = paused ? pausedTime : (now - vortexState.startTime) / 1000;
          if (paused) pausedTime = elapsed;
          gl.uniform1f(uTime, elapsed);
          gl.uniform1f(uMotion, paused ? 0 : 1);
          gl.uniform1f(uLatency, clamp(vortexState.latencyMs, 0, 120));
          gl.drawArrays(gl.TRIANGLES, 0, 6);
          updateTelemetry();
          raf = requestAnimationFrame(render);
        }

        resize();
        window.addEventListener("resize", resize);
        window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", event => {
          paused = event.matches;
          vortexState.running = !paused;
        });
        raf = requestAnimationFrame(render);

        return () => {
          cancelAnimationFrame(raf);
          window.removeEventListener("resize", resize);
        };
      } catch (err) {
        console.warn("WebGL2 init failed:", err);
        return null;
      }
    }

    function updateTelemetry() {
      const now = performance.now();
      vortexState.frameCount++;

      const fps = 1000 / Math.max(1, now - vortexState.lastFrame);
      vortexState.lastFrame = now;
      vortexState.fps = vortexState.fps ? vortexState.fps * 0.82 + fps * 0.18 : fps;

      if (now - vortexState.lastTelemetry > 420) {
        vortexState.lastTelemetry = now;
        const active = Number($("#active-params")?.value || 7);
        const batch = Number($("#batch-size")?.value || 8);
        const estimate = estimateInference({
          activeParams: active,
          totalParams: Number($("#total-params")?.value || 47),
          bpw: Number($("#quant-bpw")?.value || 4),
          pcie: $("#pcie-gen")?.value || "gen4",
          batch
        });
        vortexState.latencyMs = estimate.latencyMs;
        vortexState.tokensPerSec = estimate.tokPerSec;

        const fpsEl = $("#fps-value");
        const latencyEl = $("#token-latency");
        const throughputEl = $("#shader-throughput");
        const modeEl = $("#renderer-mode");

        if (fpsEl) fpsEl.textContent = `${Math.round(vortexState.fps)} FPS`;
        if (latencyEl) latencyEl.textContent = `${format(vortexState.latencyMs, 2)} ms/tok`;
        if (throughputEl) throughputEl.textContent = `${format(vortexState.tokensPerSec)} tok/s`;
        if (modeEl) modeEl.textContent = vortexState.mode;
      }
    }

    function initCanvas() {
      const canvas = $("#vortex-canvas");
      if (!canvas) return;

      canvas.setAttribute("aria-label", "Live tensor routing telemetry visualization");
      canvas.setAttribute("role", "img");

      let cleanup = initWebGL(canvas);
      if (!cleanup) {
        vortexState.mode = "2d-fallback";
        cleanup = createCanvasFallback(canvas, canvas.getContext("2d"));
      } else {
        vortexState.mode = "webgl2";
      }

      updateTelemetry();
      window.addEventListener("pagehide", () => {
        cleanup?.();
        vortexState.running = false;
      });
    }

    document.addEventListener("DOMContentLoaded", () => {
      initCanvas();
      initCalculator();
      initProvisionForm();
    });
  </script>

  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": "https://vortexcompute.example/#organization",
        "name": "VORTEX COMPUTE",
        "url": "https://vortexcompute.example/",
        "logo": {
          "@type": "ImageObject",
          "url": "https://vortexcompute.example/vortex-logo.png",
          "width": 512,
          "height": 512
        },
        "description": "Sovereign distributed GPU and NVMe-over-Fabrics inference engine for low-latency mixture-of-experts models.",
        "sameAs": [
          "https://vortexcompute.example/llms.txt"
        ]
      },
      {
        "@type": "Product",
        "@id": "https://vortexcompute.example/#product-edge-node-8gb",
        "name": "Edge Node 8GB",
        "description": "A compact deployment tier for 8GB edge inference with pinned NVMe page cache, deterministic quantization, and hardware enclave isolation.",
        "brand": {
          "@id": "https://vortexcompute.example/#organization"
        },
        "category": "GPU Inference Engine",
        "offers": {
          "@type": "Offer",
          "price": "0",
          "priceCurrency": "USD",
          "availability": "https://schema.org/InStock",
          "url": "https://vortexcompute.example/#edge-node-8gb"
        },
        "aggregateRating": {
          "@type": "AggregateRating",
          "ratingValue": "4.8",
          "reviewCount": "14"
        }
      },
      {
        "@type": "Product",
        "@id": "https://vortexcompute.example/#product-workstation-12gb",
        "name": "Workstation 12GB",
        "description": "A workstation deployment tier for 12GB VRAM systems, balancing speculative tree verification, zero-copy KV ring, and routed expert prefetch.",
        "brand": {
          "@id": "https://vortexcompute.example/#organization"
        },
        "category": "GPU Inference Engine",
        "offers": {
          "@type": "Offer",
          "price": "0",
          "priceCurrency": "USD",
          "availability": "https://schema.org/InStock",
          "url": "https://vortexcompute.example/#workstation-12gb"
        },
        "aggregateRating": {
          "@type": "AggregateRating",
          "ratingValue": "4.7",
          "reviewCount": "22"
        }
      },
      {
        "@type": "Product",
        "@id": "https://vortexcompute.example/#product-rack-pod-8xgpu",
        "name": "Rack Pod 8xGPU",
        "description": "A rack-scale deployment tier with 8 GPUs, RDMA tensor sharding, NVMe-over-Fabrics page cache, and deterministic quantization for production MoE serving.",
        "brand": {
          "@id": "https://vortexcompute.example/#organization"
        },
        "category": "GPU Inference Engine",
        "offers": {
          "@type": "Offer",
          "price": "0",
          "priceCurrency": "USD",
          "availability": "https://schema.org/InStock",
          "url": "https://vortexcompute.example/#rack-pod-8xgpu"
        },
        "aggregateRating": {
          "@type": "AggregateRating",
          "ratingValue": "4.9",
          "reviewCount": "31"
        }
      },
      {
        "@type": "FAQPage",
        "@id": "https://vortexcompute.example/#faq",
        "mainEntity": [
          {
            "@type": "Question",
            "name": "How does VORTEX COMPUTE shard tensors across GPUs without increasing tail latency?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "VORTEX COMPUTE uses RDMA tensor sharding with deterministic expert placement. MoE layers are partitioned by routed expert affinity, while attention and shared components remain replicated or pinned close to the active token stream. The scheduler avoids dynamic rebalancing during decode, so tail latency stays bounded and predictable."
            }
          },
          {
            "@type": "Question",
            "name": "Why is NVMe-over-Fabrics used for model weights instead of keeping all parameters in VRAM?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "MoE models can exceed local VRAM because most experts are rarely active for a given token. VORTEX COMPUTE keeps active experts, KV state, and speculative branches in VRAM, while total parameters remain pinned in NVMe page cache or remote fabric pages. This reduces VRAM pressure without paying full cold-load penalties."
            }
          },
          {
            "@type": "Question",
            "name": "What is speculative tree verification in VORTEX COMPUTE?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Speculative tree verification drafts multiple token branches in parallel and verifies them against the target model using a tree-aware acceptance mask. Accepted branches commit immediately, while rejected branches are pruned without serializing the full sequence. This improves decode throughput while preserving target-model fidelity."
            }
          },
          {
            "@type": "Question",
            "name": "How does zero-copy KV ring reduce memory traffic during long-context inference?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "The zero-copy KV ring maintains key-value pages as immutable, ring-addressed blocks. Attention kernels reference blocks directly instead of copying them into temporary buffers. Sliding windows and speculative branches share pages through reference counts, reducing allocator churn and PCIe traffic."
            }
          },
          {
            "@type": "Question",
            "name": "How does hardware enclave isolation protect sovereign inference workloads?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Hardware enclave isolation binds model weights, KV state, and scheduler metadata to attested device memory. Kernel launch, DMA descriptors, and NVMe page-cache pinning are restricted to the enclave context. Remote fabric reads require signed page manifests, so untrusted hosts cannot inspect or mutate active inference state."
            }
          }
        ]
      },
      {
        "@type": "BreadcrumbList",
        "@id": "https://vortexcompute.example/#breadcrumb",
        "itemListElement": [
          {
            "@type": "ListItem",
            "position": 1,
            "name": "Home",
            "item": "https://vortexcompute.example/"
          },
          {
            "@type": "ListItem",
            "position": 2,
            "name": "Product Portal",
            "item": "https://vortexcompute.example/index.html"
          }
        ]
      }
    ]
  }
  </script>
</head>

<body>
  <a class="skip-link" href="#main">Skip to main content</a>

  <header class="site-header">
    <div class="page header-inner">
      <a class="brand" href="#top" aria-label="VORTEX COMPUTE home">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 64 64" role="presentation" focusable="false">
            <path d="M14 14h12l16 26 16-26h12L44 50H30z" fill="oklch(0.76 0.15 195)"/>
            <path d="M22 20h8l10 16 10-16h8L42 38h-12z" fill="oklch(0.72 0.17 155)"/>
          </svg>
        </span>
        <span>
          VORTEX COMPUTE
          <small>SOVEREIGN INFERENCE FABRIC</small>
        </span>
      </a>

      <nav class="primary-nav" aria-label="Primary navigation">
        <ul>
          <li><a href="#architecture">Architecture</a></li>
          <li><a href="#sizing">Sizing</a></li>
          <li><a href="#benchmarks">Benchmarks</a></li>
          <li><a href="#faq">FAQ</a></li>
          <li><a href="#provision">Provision</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <main id="main">
    <section class="hero" id="top" aria-labelledby="hero-heading">
      <div class="hero-copy">
        <span class="eyebrow">
          <span class="dot" aria-hidden="true"></span>
          Distributed GPU + NVMe-oF
        </span>

        <h1 id="hero-heading">
          Low-latency <span class="accent">MoE inference</span> across sovereign GPU and NVMe fabrics.
        </h1>

        <p>
          VORTEX COMPUTE routes sparse expert activations, pinned NVMe pages, and speculative token trees
          through a deterministic execution plane. The result is bounded tail latency, isolated model state,
          and production-grade throughput without centralized cloud dependencies.
        </p>

        <div class="hero-actions">
          <a class="btn btn-primary" href="#sizing">Size a deployment</a>
          <a class="btn" href="#benchmarks">View benchmark tiers</a>
          <a class="btn" href="#provision">Request provisioning</a>
        </div>
      </div>

      <div class="canvas-panel" aria-label="Live tensor routing telemetry visualization">
        <canvas id="vortex-canvas" width="1120" height="840"></canvas>
        <div class="telemetry" aria-live="off" aria-atomic="true">
          <span><span class="dot cyan" aria-hidden="true"></span><span id="fps-value">— FPS</span></span>
          <span><span class="dot emerald" aria-hidden="true"></span><span id="token-latency">— ms/tok</span></span>
          <span><span class="dot amber" aria-hidden="true"></span><span id="shader-throughput">— tok/s</span></span>
        </div>
        <div class="visually-hidden" style="position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; border:0;">
          Renderer mode: <span id="renderer-mode">webgl2</span>
        </div>
      </div>
    </section>

    <div class="page">
      <div class="status-strip" role="list" aria-label="Deployment telemetry summary">
        <div class="status-card" role="listitem">
          <strong>0.6 ms</strong>
          <span>Median expert activation overhead under pinned NVMe page cache.</span>
        </div>
        <div class="status-card" role="listitem">
          <strong>4.8×</strong>
          <span>Decode throughput uplift with speculative tree verification on 4 bpw workloads.</span>
        </div>
        <div class="status-card" role="listitem">
          <strong>128 GB/s</strong>
          <span>Reference RDMA fabric ceiling for tensor shard movement between GPU pods.</span>
        </div>
        <div class="status-card" role="listitem">
          <strong>8 nodes</strong>
          <span>Minimum sovereign rack pod topology with enclave attestation and KV ring isolation.</span>
        </div>
      </div>
    </div>

    <section id="architecture" aria-labelledby="architecture-heading">
      <div class="page">
        <div class="section-head">
          <h2 id="architecture-heading">Architecture pillars</h2>
          <p>
            Six tightly coupled subsystems govern memory movement, expert routing, speculative execution,
            and isolation. Each pillar is designed for deterministic decode paths, not best-effort throughput.
          </p>
        </div>

        <div class="bento" role="list" aria-label="Architecture pillars">
          <article class="pillar" role="listitem" aria-labelledby="pillar-rdma">
            <div class="diagram" aria-hidden="true">
              <svg viewBox="0 0 420 128" role="presentation" focusable="false">
                <defs>
                  <linearGradient id="rdma-g" x1="0" x2="1">
                    <stop offset="0" stop-color="oklch(0.76 0.15 195)"/>
                    <stop offset="1" stop-color="oklch(0.72 0.17 155)"/>
                  </linearGradient>
                </defs>
                <rect x="20" y="42" width="70" height="44" rx="8" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <rect x="175" y="30" width="70" height="34" rx="8" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <rect x="175" y="64" width="70" height="34" rx="8" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <rect x="330" y="42" width="70" height="44" rx="8" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <path d="M90 64 H175" stroke="url(#rdma-g)" stroke-width="2"/>
                <path d="M245 47 L330 60" stroke="url(#rdma-g)" stroke-width="2"/>
                <path d="M245 81 L330 68" stroke="url(#rdma-g)" stroke-width="2"/>
                <circle cx="132" cy="64" r="3" fill="oklch(0.76 0.15 195)"/>
                <circle cx="290" cy="54" r="3" fill="oklch(0.72 0.17 155)"/>
                <circle cx="290" cy="74" r="3" fill="oklch(0.72 0.17 155)"/>
                <text x="20" y="24" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">GPU A</text>
                <text x="175" y="20" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">SHARD 0</text>
                <text x="175" y="112" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">SHARD 1</text>
                <text x="330" y="24" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">GPU B</text>
              </svg>
            </div>
            <h3 id="pillar-rdma">RDMA Tensor Sharding</h3>
            <p>
              Expert tensors are partitioned by affinity and moved through RDMA queues with signed page manifests.
              Scheduler decisions are precomputed, so decode-time shard movement avoids lock contention and avoids
              unpredictable network tail effects.
            </p>
          </article>

          <article class="pillar" role="listitem" aria-labelledby="pillar-speculative">
            <div class="diagram" aria-hidden="true">
              <svg viewBox="0 0 420 128" role="presentation" focusable="false">
                <path d="M30 70 C70 24 110 24 150 70 C190 116 230 116 270 70 C310 24 350 24 390 70"
                      fill="none" stroke="oklch(0.76 0.15 195)" stroke-width="2"/>
                <path d="M30 70 C70 58 110 82 150 70 C190 58 230 82 270 70 C310 58 350 82 390 70"
                      fill="none" stroke="oklch(0.72 0.17 155)" stroke-width="2"/>
                <circle cx="30" cy="70" r="5" fill="oklch(0.95 0.01 250)"/>
                <circle cx="150" cy="70" r="5" fill="oklch(0.76 0.15 195)"/>
                <circle cx="270" cy="70" r="5" fill="oklch(0.72 0.17 155)"/>
                <circle cx="390" cy="70" r="5" fill="oklch(0.95 0.01 250)"/>
                <text x="30" y="24" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">DRAFT TREE</text>
                <text x="270" y="112" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">VERIFY MASK</text>
              </svg>
            </div>
            <h3 id="pillar-speculative">Speculative Tree Verification</h3>
            <p>
              Multiple token branches are drafted in parallel, then verified against the target model using a
              tree-aware acceptance mask. Accepted branches commit immediately; rejected branches are pruned
              without serializing the full sequence.
            </p>
          </article>

          <article class="pillar" role="listitem" aria-labelledby="pillar-nvme">
            <div class="diagram" aria-hidden="true">
              <svg viewBox="0 0 420 128" role="presentation" focusable="false">
                <rect x="24" y="28" width="84" height="72" rx="10" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <rect x="138" y="28" width="144" height="72" rx="10" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <rect x="314" y="28" width="84" height="72" rx="10" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <path d="M108 64 H138" stroke="oklch(0.76 0.15 195)" stroke-width="2"/>
                <path d="M282 64 H314" stroke="oklch(0.72 0.17 155)" stroke-width="2"/>
                <rect x="152" y="42" width="26" height="18" rx="4" fill="oklch(0.76 0.15 195)" opacity="0.75"/>
                <rect x="186" y="42" width="26" height="18" rx="4" fill="oklch(0.72 0.17 155)" opacity="0.75"/>
                <rect x="220" y="42" width="26" height="18" rx="4" fill="oklch(0.76 0.15 195)" opacity="0.55"/>
                <text x="24" y="22" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">NVMe</text>
                <text x="138" y="22" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">PAGE CACHE</text>
                <text x="314" y="22" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">VRAM</text>
              </svg>
            </div>
            <h3 id="pillar-nvme">NVMe Page-Cache Pinning</h3>
            <p>
              Cold expert pages are pinned in NVMe page cache and remote fabric pages. Active expert pages are
              promoted into VRAM with reference-counted residency, avoiding full model reloads.
            </p>
          </article>

          <article class="pillar" role="listitem" aria-labelledby="pillar-kv">
            <div class="diagram" aria-hidden="true">
              <svg viewBox="0 0 420 128" role="presentation" focusable="false">
                <defs>
                  <marker id="kv-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                    <path d="M0 0 L10 5 L0 10 z" fill="oklch(0.76 0.15 195)"/>
                  </marker>
                </defs>
                <path d="M60 64 A52 34 0 1 1 360 64 A52 34 0 1 1 60 64" fill="none" stroke="oklch(0.28 0.03 260)" stroke-width="2"/>
                <path d="M110 36 A52 34 0 0 1 310 36" fill="none" stroke="oklch(0.76 0.15 195)" stroke-width="2" marker-end="url(#kv-arrow)"/>
                <path d="M310 92 A52 34 0 0 1 110 92" fill="none" stroke="oklch(0.72 0.17 155)" stroke-width="2" marker-end="url(#kv-arrow)"/>
                <circle cx="110" cy="36" r="4" fill="oklch(0.95 0.01 250)"/>
                <circle cx="310" cy="36" r="4" fill="oklch(0.95 0.01 250)"/>
                <circle cx="110" cy="92" r="4" fill="oklch(0.95 0.01 250)"/>
                <circle cx="310" cy="92" r="4" fill="oklch(0.95 0.01 250)"/>
                <text x="156" y="24" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">KV PAGE 0</text>
                <text x="156" y="112" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">KV PAGE 1</text>
              </svg>
            </div>
            <h3 id="pillar-kv">Zero-Copy KV Ring</h3>
            <p>
              Key-value pages are ring-addressed and reference-counted. Attention kernels read pages directly,
              while sliding windows and speculative branches share immutable blocks. This reduces allocator churn
              and PCIe traffic during long-context serving.
            </p>
          </article>

          <article class="pillar" role="listitem" aria-labelledby="pillar-quant">
            <div class="diagram" aria-hidden="true">
              <svg viewBox="0 0 420 128" role="presentation" focusable="false">
                <rect x="24" y="34" width="92" height="60" rx="10" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <rect x="138" y="34" width="144" height="60" rx="10" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <rect x="314" y="34" width="84" height="60" rx="10" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <path d="M116 64 H138" stroke="oklch(0.76 0.15 195)" stroke-width="2"/>
                <path d="M282 64 H314" stroke="oklch(0.72 0.17 155)" stroke-width="2"/>
                <text x="42" y="68" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">fp16</text>
                <text x="172" y="68" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">INT4/INT8</text>
                <text x="332" y="68" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">GPU</text>
                <rect x="150" y="46" width="18" height="18" rx="3" fill="oklch(0.76 0.15 195)" opacity="0.8"/>
                <rect x="176" y="46" width="18" height="18" rx="3" fill="oklch(0.72 0.17 155)" opacity="0.8"/>
                <rect x="202" y="46" width="18" height="18" rx="3" fill="oklch(0.76 0.15 195)" opacity="0.5"/>
                <rect x="228" y="46" width="18" height="18" rx="3" fill="oklch(0.72 0.17 155)" opacity="0.5"/>
              </svg>
            </div>
            <h3 id="pillar-quant">Deterministic Quantization</h3>
            <p>
              Quantization plans are fixed at provisioning time. Bit widths, activation scales, and expert block
              layouts are pinned to a manifest so repeated decode runs produce stable memory and latency behavior.
            </p>
          </article>

          <article class="pillar" role="listitem" aria-labelledby="pillar-enclave">
            <div class="diagram" aria-hidden="true">
              <svg viewBox="0 0 420 128" role="presentation" focusable="false">
                <path d="M60 92 V54 C60 36 82 24 110 24 H310 C338 24 360 36 360 54 V92"
                      fill="none" stroke="oklch(0.76 0.15 195)" stroke-width="2"/>
                <rect x="110" y="52" width="200" height="40" rx="10" fill="oklch(0.21 0.025 260)" stroke="oklch(0.28 0.03 260)"/>
                <rect x="132" y="64" width="28" height="16" rx="4" fill="oklch(0.72 0.17 155)" opacity="0.8"/>
                <rect x="172" y="64" width="28" height="16" rx="4" fill="oklch(0.76 0.15 195)" opacity="0.8"/>
                <rect x="212" y="64" width="28" height="16" rx="4" fill="oklch(0.72 0.17 155)" opacity="0.5"/>
                <rect x="252" y="64" width="28" height="16" rx="4" fill="oklch(0.76 0.15 195)" opacity="0.5"/>
                <text x="110" y="20" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">ENCLAVE BOUNDARY</text>
                <text x="110" y="112" fill="oklch(0.78 0.02 250)" font-family="ui-monospace" font-size="12">WEIGHTS · KV · SCHEDULER</text>
              </svg>
            </div>
            <h3 id="pillar-enclave">Hardware Enclave Isolation</h3>
            <p>
              Model weights, KV state, DMA descriptors, and scheduler metadata are bound to attested device memory.
              Remote fabric reads require signed page manifests, so untrusted hosts cannot inspect or mutate active
              inference state.
            </p>
          </article>
        </div>
      </div>
    </section>

    <section id="sizing" aria-labelledby="sizing-heading">
      <div class="page">
        <div class="section-head">
          <h2 id="sizing-heading">VRAM &amp; throughput sizing calculator</h2>
          <p>
            Estimate resident VRAM, host RAM, KV context footprint, and approximate token throughput for a
            sparse MoE workload. Values are engineering estimates, not vendor guarantees.
          </p>
        </div>

        <div class="calculator">
          <form id="sizing-form" class="calc-form" aria-labelledby="sizing-heading">
            <div class="field">
              <label for="active-params">Active parameters</label>
              <div class="range-row">
                <input id="active-params" name="active" type="range" min="0.5" max="40" step="0.1" value="7" aria-label="Active parameters in billions">
                <output id="out-active" for="active-params">7.0B active</output>
              </div>
            </div>

            <div class="field">
              <label for="total-params">Total MoE parameters</label>
              <div class="range-row">
                <input id="total-params" name="total" type="range" min="7" max="2600" step="1" value="47" aria-label="Total MoE parameters in billions">
                <output id="out-total" for="total-params">47B total</output>
              </div>
            </div>

            <div class="field">
              <label for="quant-bpw">Quantization bits per weight</label>
              <div class="range-row">
                <input id="quant-bpw" name="bpw" type="range" min="2" max="16" step="1" value="4" aria-label="Quantization bits per weight">
                <output id="out-bpw" for="quant-bpw">4 bpw</output>
              </div>
            </div>

            <div class="field">
              <label for="pcie-gen">PCIe generation</label>
              <select id="pcie-gen" name="pcie">
                <option value="gen3">Gen 3 — 16 GB/s reference</option>
                <option value="gen4" selected>Gen 4 — 32 GB/s reference</option>
                <option value="gen5">Gen 5 — 64 GB/s reference</option>
              </select>
            </div>

            <div class="field">
              <label for="batch-size">Batch size</label>
              <div class="range-row">
                <input id="batch-size" name="batch" type="range" min="1" max="128" step="1" value="8" aria-label="Batch size">
                <output id="out-batch" for="batch-size">8 batch</output>
              </div>
            </div>

            <div class="field">
              <label for="out-pcie">Fabric reference</label>
              <output id="out-pcie">GEN4</output>
            </div>
          </form>

          <div class="results" aria-live="polite" aria-atomic="true">
            <div class="result-grid">
              <div class="result-card">
                <strong id="vram-value">— GB</strong>
                <span>Resident VRAM estimate</span>
              </div>
              <div class="result-card">
                <strong id="ram-value">— GB</strong>
                <span>Host RAM / NVMe cache estimate</span>
              </div>
              <div class="result-card">
                <strong id="throughput-value">— tok/s</strong>
                <span>Estimated aggregate throughput</span>
              </div>
            </div>

            <div class="result-grid">
              <div class="result-card">
                <strong id="latency-value">— ms/token</strong>
                <span>Estimated decode latency per token</span>
              </div>
              <div class="result-card">
                <strong id="context-value">— GB KV</strong>
                <span>Approximate KV ring footprint</span>
              </div>
              <div class="result-card">
                <strong id="expert-value">— routed experts</strong>
                <span>Derived expert fan-out estimate</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="benchmarks" aria-labelledby="benchmarks-heading">
      <div class="page">
        <div class="section-head">
          <h2 id="benchmarks-heading">Benchmark comparison</h2>
          <p>
            Reference deployment tiers measured with a 47B total / 7B active MoE workload, 4 bpw quantization,
            4K context, and 8-request batch. Values are directional engineering benchmarks.
          </p>
        </div>

        <div class="table-wrap">
          <table aria-label="Benchmark comparison table for deployment tiers">
            <thead>
              <tr>
                <th scope="col">Tier</th>
                <th scope="col">Topology</th>
                <th scope="col">VRAM</th>
                <th scope="col">RAM</th>
                <th scope="col">Throughput</th>
                <th scope="col">P50 latency</th>
                <th scope="col">P95 latency</th>
                <th scope="col">KV ring</th>
              </tr>
            </thead>
            <tbody>
              <tr id="edge-node-8gb">
                <td><span class="tier"><span class="tier-badge" aria-hidden="true"></span>Edge Node 8GB</span></td>
                <td>1 GPU · 1 NVMe</td>
                <td class="metric">7.2 GB</td>
                <td class="metric">18.4 GB</td>
                <td class="metric">38 tok/s</td>
                <td class="metric">210 ms</td>
                <td class="metric">318 ms</td>
                <td class="metric">1.1 GB</td>
              </tr>
              <tr id="workstation-12gb">
                <td><span class="tier"><span class="tier-badge emerald" aria-hidden="true"></span>Workstation 12GB</span></td>
                <td>1 GPU · 2 NVMe</td>
                <td class="metric">10.8 GB</td>
                <td class="metric">32.9 GB</td>
                <td class="metric">86 tok/s</td>
                <td class="metric">94 ms</td>
                <td class="metric">151 ms</td>
                <td class="metric">2.4 GB</td>
              </tr>
              <tr id="rack-pod-8xgpu">
                <td><span class="tier"><span class="tier-badge" aria-hidden="true"></span>Rack Pod 8xGPU</span></td>
                <td>8 GPU · RDMA · NVMe-oF</td>
                <td class="metric">96 GB</td>
                <td class="metric">148 GB</td>
                <td class="metric">1,840 tok/s</td>
                <td class="metric">11 ms</td>
                <td class="metric">27 ms</td>
                <td class="metric">18.6 GB</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section id="faq" aria-labelledby="faq-heading">
      <div class="page">
        <div class="section-head">
          <h2 id="faq-heading">Engineering FAQ</h2