"""Golden production starter templates 03 (EN Neo-Brutalist DevTools) and 04 (RU Nordic Architectural Atelier)."""

TEMPLATE_03_EN_NEOBRUTAL = {
    "slug": "03_neobrutalist_devtools_sdk_en",
    "canon_id": "02_neo_brutalism_tactile",
    "lang": "en",
    "base_url": "https://anvildb.example.dev",
    "title": "AnvilDB: 42 KB WebAssembly SQLite WAL Sync Engine",
    "description": "Embed deterministic offline-first SQLite WAL replication in 42 KB of WebAssembly with sub-millisecond local reads and zero vendor lock-in.",
    "og_locale": "en_US",
    "hreflangs": {
        "en": "https://anvildb.example.dev/",
        "ru": "https://anvildb.example.dev/ru/",
        "x-default": "https://anvildb.example.dev/",
    },
    "css": """:root {
  --bg: oklch(0.96 0.028 95);
  --surface: oklch(0.995 0.004 95);
  --border: oklch(0.12 0.005 95);
  --text: oklch(0.12 0.005 95);
  --text-muted: oklch(0.38 0.015 95);
  --accent: oklch(0.86 0.18 118);
  --accent-ink: oklch(0.12 0.01 118);
  --font-display: 'Space Grotesk', system-ui, sans-serif;
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-padding-top: 4.75rem; font-size: 16px; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  line-height: 1.5;
  overflow-x: hidden;
}
.skip-link {
  position: absolute;
  left: -9999px;
  top: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--accent);
  color: var(--accent-ink);
  border: 2px solid var(--border);
  min-width: 24px;
  min-height: 24px;
}
.skip-link:focus { left: 0.75rem; z-index: 100; }
.site-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background: var(--surface);
  border-bottom: 2.5px solid var(--border);
}
.header-bar, .container {
  max-width: 80rem;
  margin: 0 auto;
  padding-inline: clamp(1.25rem, 4vw, 3rem);
}
.header-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  min-height: 4.25rem;
  gap: 1rem;
}
.logo-stamp {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--text);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 28px;
}
.nav-menu {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.nav-menu a {
  color: var(--text);
  text-decoration: none;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  min-width: 28px;
  padding: 0.25rem 0.5rem;
}
.nav-menu a:focus-visible {
  outline: 2.5px solid var(--border);
  outline-offset: 2px;
}
.hero-deck {
  min-height: 100svh;
  display: grid;
  align-items: center;
  padding-block: clamp(2rem, 4.5vw, 5rem);
  border-bottom: 2.5px solid var(--border);
}
.brutal-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 1.5rem;
}
.hero-main { grid-column: span 7; }
.hero-cli-box {
  grid-column: span 5;
  background: var(--surface);
  border: 2.5px solid var(--border);
  border-radius: 4px;
  box-shadow: 4px 4px 0px oklch(0.12 0.005 95);
  padding: 1.5rem;
}
.stamp-badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  font-weight: 700;
  background: var(--accent);
  color: var(--accent-ink);
  border: 2px solid var(--border);
  padding: 0.2rem 0.6rem;
  margin-bottom: 1rem;
}
h1, h2, h3 { font-family: var(--font-display); }
h1 {
  font-size: clamp(2.1rem, 4vw, 3.35rem);
  line-height: 1.06;
  margin: 0 0 1.25rem;
  max-width: 19ch;
}
.lead-text {
  font-size: 1.0625rem;
  max-width: 60ch;
  margin: 0 0 1.75rem;
}
.cta-strip { display: flex; flex-wrap: wrap; gap: 1rem; }
.brutal-btn, .brutal-btn-alt {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  min-width: 44px;
  padding: 0.65rem 1.25rem;
  font-family: var(--font-mono);
  font-size: 0.9375rem;
  font-weight: 700;
  text-decoration: none;
  border: 2.5px solid var(--border);
  border-radius: 4px;
  box-shadow: 4px 4px 0px oklch(0.12 0.005 95);
  cursor: pointer;
  transition: transform 100ms steps(3, end), box-shadow 100ms steps(3, end);
}
.brutal-btn {
  background: var(--accent);
  color: var(--accent-ink);
}
.brutal-btn-alt {
  background: var(--surface);
  color: var(--text);
}
.brutal-btn:active, .brutal-btn-alt:active {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0px oklch(0.12 0.005 95);
}
.brutal-btn:focus-visible, .brutal-btn-alt:focus-visible, input:focus-visible {
  outline: 3px solid var(--border);
  outline-offset: 3px;
}
pre.cli-snippet {
  font-family: var(--font-mono);
  background: var(--bg);
  border: 2px solid var(--border);
  padding: 0.85rem;
  overflow-x: auto;
  margin: 0 0 1rem;
  font-size: 0.875rem;
}
.section-zone {
  padding-block: clamp(2.5rem, 4.5vw, 4.5rem);
  border-bottom: 2.5px solid var(--border);
}
.tier-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
}
.tier-card {
  display: grid;
  grid-template-rows: subgrid;
  grid-row: span 3;
  background: var(--surface);
  border: 2.5px solid var(--border);
  border-radius: 4px;
  box-shadow: 4px 4px 0px oklch(0.12 0.005 95);
  padding: 1.5rem;
  gap: 0.75rem;
}
.tier-card h3 { margin: 0; font-size: 1.25rem; }
.tier-card p { margin: 0; color: var(--text-muted); }
.calc-panel {
  container-type: inline-size;
  background: var(--surface);
  border: 2.5px solid var(--border);
  border-radius: 4px;
  box-shadow: 4px 4px 0px oklch(0.12 0.005 95);
  padding: 1.5rem;
}
.calc-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}
@container (max-width: 560px) {
  .calc-split { grid-template-columns: 1fr; }
}
.ctrl-block {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 1rem;
}
.ctrl-block label { font-weight: 700; }
.ctrl-block input {
  min-height: 40px;
  min-width: 40px;
  padding: 0.45rem 0.75rem;
  border: 2px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
}
.num-cell, output, table td {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.brutal-table { width: 100%; border-collapse: collapse; }
.brutal-table th, .brutal-table td {
  text-align: left;
  padding: 0.6rem 0.5rem;
  border-bottom: 2px solid var(--border);
}
.faq-grid { display: grid; gap: 1.25rem; max-width: 64ch; }
.faq-box {
  background: var(--surface);
  border: 2px solid var(--border);
  padding: 1.25rem;
}
.faq-box h3 { margin: 0 0 0.5rem; }
.faq-box p { margin: 0; color: var(--text); }
.hp-hide { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
.site-footer { padding-block: 2rem; font-family: var(--font-mono); font-size: 0.875rem; }
@media (max-width: 900px) {
  .hero-main, .hero-cli-box { grid-column: span 12; }
  .tier-cards { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    transform: none !important;
    scroll-behavior: auto !important;
  }
}
""",
    "json_ld": {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": "https://anvildb.example.dev/#org",
                "name": "AnvilDB Open Systems",
                "url": "https://anvildb.example.dev/",
            },
            {
                "@type": "WebSite",
                "@id": "https://anvildb.example.dev/#website",
                "url": "https://anvildb.example.dev/",
                "name": "AnvilDB",
                "inLanguage": "en",
                "publisher": {"@id": "https://anvildb.example.dev/#org"},
            },
            {
                "@type": "WebPage",
                "@id": "https://anvildb.example.dev/#webpage",
                "url": "https://anvildb.example.dev/",
                "name": "AnvilDB: 42 KB WebAssembly SQLite WAL Sync Engine",
                "isPartOf": {"@id": "https://anvildb.example.dev/#website"},
            },
            {
                "@type": "Product",
                "@id": "https://anvildb.example.dev/#product",
                "name": "AnvilDB Cloud Relay & WASM Sync SDK",
                "brand": {"@id": "https://anvildb.example.dev/#org"},
                "description": "Deterministic SQLite WAL delta replication SDK with per-column Hybrid Logical Clock merge.",
                "offers": {
                    "@type": "Offer",
                    "price": "0",
                    "priceCurrency": "USD",
                    "availability": "https://schema.org/InStock",
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": "https://anvildb.example.dev/#breadcrumbs",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://anvildb.example.dev/"},
                    {"@type": "ListItem", "position": 2, "name": "Pricing Calculator", "item": "https://anvildb.example.dev/#calculator"},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": "https://anvildb.example.dev/#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "How does AnvilDB resolve concurrent offline writes across devices?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Concurrent offline edits resolve deterministically via per-column Hybrid Logical Clock (HLC) last-writer-wins registers or custom merge hooks. Every superseded row version remains queryable in a local _conflict_log table for 30 days.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Are we locked into a proprietary database format if we leave AnvilDB?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Zero proprietary storage format: every replica is a standard .sqlite3 file readable by upstream sqlite3 CLI, Python sqlite3, or DuckDB even if you uninstall our SDK tomorrow.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "What happens if a browser tab goes offline mid-transaction?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Local transactions commit atomically to the Origin Private File System (OPFS) SQLite WAL in under 0.4 milliseconds and queue binary frame diffs until WebSocket reachability returns.",
                        },
                    },
                ],
            },
        ],
    },
    "body_html": """<a class="skip-link" href="#main-content">Skip to main content</a>
<header class="site-header">
  <div class="header-bar">
    <a class="logo-stamp" href="#main-content">
      <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18v4l-5 4v4H8v-4L3 10V6z" fill="currentColor"/></svg>
      <span>ANVILDB // v1.8</span>
    </a>
    <nav aria-label="Primary navigation">
      <ul class="nav-menu">
        <li><a href="#guarantees">Guarantees</a></li>
        <li><a href="#calculator">Row Calculator</a></li>
        <li><a href="#faq">FAQ</a></li>
        <li><a href="#releases">Release Feed</a></li>
      </ul>
    </nav>
  </div>
</header>

<main id="main-content">
  <section class="hero-deck">
    <div class="container brutal-grid">
      <div class="hero-main">
        <span class="stamp-badge">APACHE-2.0 CORE // 42 KB GZIPPED WASM</span>
        <h1>Embed deterministic SQLite WAL sync with sub-ms local reads</h1>
        <p class="lead-text">Stop waiting 180 ms on round-trip REST spinners. AnvilDB mounts a real OPFS SQLite database inside the browser, runs analytical joins in 0.6 ms, and streams compressed WAL frames over WebSockets.</p>
        <div class="cta-strip">
          <a class="brutal-btn" href="#calculator">Calculate exact monthly bill ($0 idle floor)</a>
          <button type="button" class="brutal-btn-alt" id="copyCmdBtn">Copy CLI install (no signup)</button>
        </div>
        <p id="copyFeedback" class="num-cell" role="status" aria-live="polite">Command: curl -fsSL https://anvildb.example.dev/install.sh | sh</p>
      </div>
      <div class="hero-cli-box" aria-label="Local read latency benchmark">
        <span class="stamp-badge">BENCHMARK: 100K ROWS JOIN</span>
        <pre class="cli-snippet"><code>$ anvildb bench --opfs --rows 100000
local_select_p99 : 0.62 ms
wal_frame_diff   : 1.80 KB
conflict_replay  : deterministic OK</code></pre>
        <svg width="340" height="86" viewBox="0 0 340 86" role="img" aria-labelledby="benchSvgTitle">
          <title id="benchSvgTitle">Latency comparison: AnvilDB OPFS 0.6ms vs REST JSON 165ms</title>
          <text x="2" y="22" font-size="12" fill="currentColor">AnvilDB OPFS (0.6 ms)</text>
          <rect x="2" y="28" width="16" height="14" fill="currentColor"/>
          <text x="2" y="60" font-size="12" fill="currentColor">REST Fetch (165 ms)</text>
          <rect x="2" y="66" width="310" height="14" fill="none" stroke="currentColor" stroke-width="2"/>
        </svg>
      </div>
    </div>
  </section>

  <section id="guarantees" class="section-zone">
    <div class="container">
      <h2>Three mechanical guarantees, zero hand-waving</h2>
      <div class="tier-cards">
        <article class="tier-card">
          <span class="stamp-badge">01 // HLC MERGE</span>
          <h3>Per-column Hybrid Logical Clocks</h3>
          <p>Offline edits on separate columns of the same row merge cleanly without overwriting sibling fields or losing audit history.</p>
        </article>
        <article class="tier-card">
          <span class="stamp-badge">02 // PLAIN .SQLITE3</span>
          <h3>Upstream SQLite3 byte compatibility</h3>
          <p>Inspect, back up, or query every user replica directly with standard sqlite3 CLI, DuckDB, or Rust rusqlite.</p>
        </article>
        <article class="tier-card">
          <span class="stamp-badge">03 // $0 IDLE</span>
          <h3>Scale-to-zero WebSocket relay</h3>
          <p>Dormant replicas hibernate on object storage at $0 compute charge and wake in 11 ms on incoming frame push.</p>
        </article>
      </div>
    </div>
  </section>

  <section id="calculator" class="section-zone">
    <div class="container">
      <h2>Deterministic row-write &amp; storage bill calculator</h2>
      <div class="calc-panel">
        <div class="calc-split">
          <div>
            <div class="ctrl-block">
              <label for="dailyWritesInput">Daily synced row writes (thousands)</label>
              <input id="dailyWritesInput" name="daily_writes_k" type="number" min="10" max="50000" step="50" value="500" autocomplete="off"/>
            </div>
            <div class="ctrl-block">
              <label for="storageGbInput">Total replicated SQLite database size (GB)</label>
              <input id="storageGbInput" name="storage_gb" type="number" min="1" max="5000" step="1" value="25" autocomplete="off"/>
            </div>
          </div>
          <div>
            <table class="brutal-table" aria-label="Monthly usage cost breakdown">
              <tbody>
                <tr>
                  <th scope="row">Monthly synced WAL writes</th>
                  <td><output id="monthlyWritesOut" for="dailyWritesInput storageGbInput">15.0M writes</output></td>
                </tr>
                <tr>
                  <th scope="row">Write charge ($0.60 per 1M writes, 5M free)</th>
                  <td><output id="writeFeeOut" for="dailyWritesInput storageGbInput">$6.00</output></td>
                </tr>
                <tr>
                  <th scope="row">Total monthly invoice (+ $0.15/GB storage)</th>
                  <td><output id="totalInvoiceOut" for="dailyWritesInput storageGbInput">$9.75 / mo</output></td>
                </tr>
              </tbody>
            </table>
            <svg width="300" height="32" viewBox="0 0 300 32" aria-label="Relative monthly budget meter">
              <rect x="0" y="8" width="296" height="16" fill="none" stroke="currentColor" stroke-width="2"/>
              <rect id="budgetMeterRect" x="3" y="11" width="42" height="10" fill="currentColor"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="faq" class="section-zone">
    <div class="container">
      <h2>Technical FAQ</h2>
      <div class="faq-grid">
        <article class="faq-box">
          <h3>How does AnvilDB resolve concurrent offline writes across devices?</h3>
          <p>Concurrent offline edits resolve deterministically via per-column Hybrid Logical Clock (HLC) last-writer-wins registers or custom merge hooks. Every superseded row version remains queryable in a local _conflict_log table for 30 days.</p>
        </article>
        <article class="faq-box">
          <h3>Are we locked into a proprietary database format if we leave AnvilDB?</h3>
          <p>Zero proprietary storage format: every replica is a standard .sqlite3 file readable by upstream sqlite3 CLI, Python sqlite3, or DuckDB even if you uninstall our SDK tomorrow.</p>
        </article>
        <article class="faq-box">
          <h3>What happens if a browser tab goes offline mid-transaction?</h3>
          <p>Local transactions commit atomically to the Origin Private File System (OPFS) SQLite WAL in under 0.4 milliseconds and queue binary frame diffs until WebSocket reachability returns.</p>
        </article>
      </div>
    </div>
  </section>

  <section id="releases" class="section-zone">
    <div class="container">
      <h2>Subscribe to signed binary release checksums</h2>
      <form id="releaseForm" action="#releases" method="post" novalidate>
        <div class="calc-split">
          <div class="ctrl-block">
            <label for="maintEmailInput">Developer email for SHA-256 release notes</label>
            <input id="maintEmailInput" name="email" type="email" required autocomplete="email"/>
          </div>
          <div class="ctrl-block">
            <label for="ghHandleInput">Optional GitHub / Forgejo handle</label>
            <input id="ghHandleInput" name="username" type="text" autocomplete="username"/>
          </div>
        </div>
        <div class="hp-hide" aria-hidden="true">
          <label for="faxTrapInput">Do not fill this bot trap field</label>
          <input id="faxTrapInput" name="fax_hp" type="text" tabindex="-1" autocomplete="off"/>
        </div>
        <button class="brutal-btn" type="submit">Subscribe (1 email per minor release, 0 ads)</button>
        <p id="releaseMsg" class="num-cell" role="status" aria-live="polite">Plaintext release notes only; 1-click RFC-8058 unsubscribe header included.</p>
      </form>
    </div>
  </section>
</main>

<footer class="site-footer">
  <div class="container">
    <p>AnvilDB Open Systems, 2026. Hard-offset Neo-Brutalist canon, strict SHA-256 CSP, zero external requests.</p>
  </div>
</footer>""",
    "ts_code": """interface BillingBreakdown {
  monthlyMillions: number;
  writeFeeUsd: number;
  totalUsd: number;
  meterWidth: number;
}

function initTrustedTypesPolicy(): void {
  const w = window as unknown as {
    trustedTypes?: { createPolicy: (name: string, rules: { createHTML: (s: string) => string }) => unknown };
  };
  if (w.trustedTypes && typeof w.trustedTypes.createPolicy === "function") {
    try {
      w.trustedTypes.createPolicy("default", {
        createHTML: (s: string): string => s.replace(/[<>]/g, ""),
      });
    } catch {
      // Policy already exists
    }
  }
}

function calcInvoice(dailyWritesThousands: number, storageGb: number): BillingBreakdown {
  const safeDailyK = Math.max(10, Math.min(50000, dailyWritesThousands));
  const safeGb = Math.max(1, Math.min(5000, storageGb));
  const monthlyMillions = (safeDailyK * 30) / 1000;
  const billableMillions = Math.max(0, monthlyMillions - 5);
  const writeFeeUsd = billableMillions * 0.6;
  const totalUsd = writeFeeUsd + safeGb * 0.15;
  const meterWidth = Math.max(10, Math.min(290, Math.round((totalUsd / 250) * 290)));
  return { monthlyMillions, writeFeeUsd, totalUsd, meterWidth };
}

function bootAnvilDb(): void {
  initTrustedTypesPolicy();

  const writesIn = document.getElementById("dailyWritesInput") as HTMLInputElement | null;
  const gbIn = document.getElementById("storageGbInput") as HTMLInputElement | null;
  const writesOut = document.getElementById("monthlyWritesOut") as HTMLOutputElement | null;
  const feeOut = document.getElementById("writeFeeOut") as HTMLOutputElement | null;
  const totalOut = document.getElementById("totalInvoiceOut") as HTMLOutputElement | null;
  const meter = document.getElementById("budgetMeterRect");

  const refreshCalc = (): void => {
    if (!writesIn || !gbIn || !writesOut || !feeOut || !totalOut) {
      return;
    }
    const dailyK = Number.parseFloat(writesIn.value || "500") || 500;
    const gb = Number.parseFloat(gbIn.value || "25") || 25;
    const res = calcInvoice(dailyK, gb);
    writesOut.textContent = `${res.monthlyMillions.toFixed(1)}M writes`;
    feeOut.textContent = `$${res.writeFeeUsd.toFixed(2)}`;
    totalOut.textContent = `$${res.totalUsd.toFixed(2)} / mo`;
    if (meter) {
      meter.setAttribute("width", String(res.meterWidth));
    }
  };

  if (writesIn && gbIn) {
    writesIn.addEventListener("input", refreshCalc);
    gbIn.addEventListener("input", refreshCalc);
    refreshCalc();
  }

  const copyBtn = document.getElementById("copyCmdBtn");
  const copyFeedback = document.getElementById("copyFeedback");
  if (copyBtn && copyFeedback) {
    copyBtn.addEventListener("click", (): void => {
      const cmd = "curl -fsSL https://anvildb.example.dev/install.sh | sh";
      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        navigator.clipboard.writeText(cmd).catch(() => undefined);
      }
      copyFeedback.textContent = "Copied install snippet (14 MB static binary, SHA-256 verified).";
    });
  }

  const form = document.getElementById("releaseForm") as HTMLFormElement | null;
  const trap = document.getElementById("faxTrapInput") as HTMLInputElement | null;
  const email = document.getElementById("maintEmailInput") as HTMLInputElement | null;
  const msg = document.getElementById("releaseMsg");

  if (form && msg) {
    form.addEventListener("submit", (ev: Event): void => {
      ev.preventDefault();
      if (trap && trap.value.trim().length > 0) {
        msg.textContent = "Bot honeypot triggered; submission discarded.";
        return;
      }
      const val = email ? email.value.trim() : "";
      if (!val.includes("@") || !val.includes(".")) {
        msg.textContent = "Enter a valid developer email address (example: alex@crate.dev).";
        return;
      }
      msg.textContent = "Subscribed locally to signed v1.x checksum announcements.";
    });
  }
}

bootAnvilDb();
export {};
""",
    "llms_txt": """# AnvilDB (42 KB WebAssembly SQLite WAL Sync Engine)

> Deterministic offline-first SQLite WAL replication engine delivering sub-millisecond OPFS local queries, per-column Hybrid Logical Clock conflict resolution, and upstream .sqlite3 byte compatibility.

## SDK & Guarantees
- [Mechanical Guarantees](https://anvildb.example.dev/#guarantees): Per-column HLC merge registers, standard .sqlite3 files, and $0 idle scale-to-zero WebSocket relay.
- [Pricing Calculator](https://anvildb.example.dev/#calculator): 5M free monthly synced writes, then $0.60 per 1M writes and $0.15/GB storage.

## Conflict & Durability Specification
- [Technical FAQ](https://anvildb.example.dev/#faq): 30-day local _conflict_log retention, zero vendor lock-in, and 0.4ms OPFS WAL commits.
""",
    "zimage_prompts": [
        {
            "id": "anvil_wal_cartridge",
            "slot": "hero_primary",
            "canon_id": "02_neo_brutalism_tactile",
            "aspect_ratio": "4:3",
            "exact_text_in_frame": "ANVIL WAL",
            "prompt": "Isometric cutaway mechanical storage cartridge diagram printed on warm cream heavy drafting paper, bold 2.5pt matte black ink outlines, flat screenprint electric lime and charcoal fills, crisp stenciled nameplate reading 'ANVIL WAL', overhead studio flat-lay lighting, tactile risograph ink texture.",
            "negative_prompt": "soft airbrush gradient, blurry drop shadow, purple neon fog, stock office worker, watermark",
        },
        {
            "id": "anvil_hlc_clock",
            "slot": "card_01",
            "canon_id": "02_neo_brutalism_tactile",
            "aspect_ratio": "1:1",
            "exact_text_in_frame": "HLC SYNC",
            "prompt": "Technical pop-brutalist blueprint illustration of twin interlocking brass and matte black split-flap counter gears on warm ivory cardstock, crisp 2.5pt ink linework, vibrant lime accent arrow and stamped callout tag 'HLC SYNC', razor-sharp flat studio illumination.",
            "negative_prompt": "3d glossy plastic, glowing blue lasers, lens flare, blurry background, photorealistic face",
        },
        {
            "id": "anvil_sqlite_block",
            "slot": "card_02",
            "canon_id": "02_neo_brutalism_tactile",
            "aspect_ratio": "4:3",
            "exact_text_in_frame": "42KB WASM",
            "prompt": "Bold geometric isometric diagram of a compact solid steel machinist gauge block resting on millimeter grid drafting vellum, sharp black ink outlines, electric lime measurement caliper bar labeled '42KB WASM', clean daylight flat-lay composition.",
            "negative_prompt": "purple cyberpunk city, soft pastel watercolor, messy cables, low contrast gray",
        },
    ],
}


TEMPLATE_04_RU_NORDIC = {
    "slug": "04_nordic_architectural_atelier_ru",
    "canon_id": "05_nordic_architectural_minimal",
    "lang": "ru",
    "base_url": "https://sever-akustika.example.ru",
    "title": "Северная Мастерская Акустики: панели из карельской берёзы КМ1",
    "description": "Проектирование и производство акустических потолков и стеновых панелей из массива берёзы со временем реверберации RT60 0,45-0,60 с.",
    "og_locale": "ru_RU",
    "hreflangs": {
        "ru": "https://sever-akustika.example.ru/",
        "en": "https://sever-akustika.example.ru/en/",
        "x-default": "https://sever-akustika.example.ru/",
    },
    "css": """:root {
  --bg: oklch(0.97 0.008 85);
  --surface: oklch(0.935 0.012 85);
  --border: oklch(0.76 0.014 85);
  --text: oklch(0.19 0.012 80);
  --text-muted: oklch(0.44 0.015 80);
  --accent: oklch(0.38 0.065 155);
  --accent-ink: oklch(0.98 0.005 85);
  --font-serif: 'Newsreader', 'Source Serif 4', Georgia, serif;
  --font-sans: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  --font-mono: 'IBM Plex Mono', ui-monospace, monospace;
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-padding-top: 5rem; font-size: 16px; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  line-height: 1.58;
  overflow-x: hidden;
}
.skip-link {
  position: absolute;
  left: -9999px;
  top: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--accent);
  color: var(--accent-ink);
  min-width: 24px;
  min-height: 24px;
}
.skip-link:focus { left: 0.75rem; z-index: 100; }
.site-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}
.header-wrap, .container {
  max-width: 78rem;
  margin: 0 auto;
  padding-inline: clamp(1.25rem, 5vw, 3.5rem);
}
.header-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  min-height: 4.5rem;
  gap: 1rem;
}
.atelier-title {
  font-family: var(--font-serif);
  font-size: 1.1875rem;
  font-weight: 600;
  color: var(--text);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 28px;
}
.atelier-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.atelier-nav a {
  color: var(--text);
  text-decoration: none;
  font-size: 0.9375rem;
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  min-width: 28px;
  padding: 0.25rem 0.4rem;
}
.atelier-nav a:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.hero-chamber {
  min-height: 100svh;
  display: grid;
  align-items: center;
  padding-block: clamp(2.25rem, 6vw, 6.5rem);
  border-bottom: 1px solid var(--border);
}
.nordic-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 2rem;
}
.hero-essay { grid-column: span 7; }
.hero-acoustics {
  grid-column: span 5;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 1.75rem;
}
h1, h2, h3 { font-family: var(--font-serif); font-weight: 500; }
h1 {
  font-size: clamp(2.1rem, 3.9vw, 3.2rem);
  line-height: 1.12;
  margin: 0 0 1.25rem;
  max-width: 20ch;
}
.dropcap-lead {
  max-width: 60ch;
  font-size: 1.0625rem;
  margin: 0 0 1.75rem;
}
.dropcap-lead::first-letter {
  font-family: var(--font-serif);
  font-size: 2.9rem;
  line-height: 0.9;
  float: left;
  padding-right: 0.5rem;
  color: var(--accent);
}
.btn-row { display: flex; flex-wrap: wrap; gap: 1rem; clear: both; }
.btn-pine, .btn-stone {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  min-width: 44px;
  padding: 0.65rem 1.35rem;
  border-radius: 2px;
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: opacity 240ms cubic-bezier(0.22, 1, 0.36, 1);
}
.btn-pine {
  background: var(--accent);
  color: var(--accent-ink);
  border-color: var(--accent);
}
.btn-stone {
  background: var(--surface);
  color: var(--text);
}
.btn-pine:focus-visible, .btn-stone:focus-visible, input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.chapter-section {
  padding-block: clamp(2.5rem, 6vw, 5.5rem);
  border-bottom: 1px solid var(--border);
}
.dossier-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
}
.dossier-card {
  display: grid;
  grid-template-rows: subgrid;
  grid-row: span 3;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 1.5rem;
  gap: 0.75rem;
}
.dossier-card h3 { margin: 0; font-size: 1.25rem; }
.dossier-card p { margin: 0; color: var(--text-muted); }
.sabine-container {
  container-type: inline-size;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 1.75rem;
}
.sabine-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.75rem;
}
@container (max-width: 640px) {
  .sabine-cols { grid-template-columns: 1fr; }
}
.form-line {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 1rem;
}
.form-line label { font-weight: 600; font-size: 0.9375rem; }
.form-line input {
  min-height: 40px;
  min-width: 40px;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
}
.mono-val, output, table td {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.acoustic-table { width: 100%; border-collapse: collapse; }
.acoustic-table th, .acoustic-table td {
  text-align: left;
  padding: 0.65rem 0.5rem;
  border-bottom: 1px solid var(--border);
}
.faq-column { display: grid; gap: 1.25rem; max-width: 62ch; }
.faq-entry {
  border-top: 1px solid var(--border);
  padding-top: 1rem;
}
.faq-entry h3 { margin: 0 0 0.5rem; font-size: 1.15rem; }
.faq-entry p { margin: 0; color: var(--text); }
.hp-box { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
.site-footer { padding-block: 2.25rem; color: var(--text-muted); font-size: 0.875rem; }
@media (max-width: 900px) {
  .hero-essay, .hero-acoustics { grid-column: span 12; }
  .dossier-grid { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
""",
    "json_ld": {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": "https://sever-akustika.example.ru/#org",
                "name": "Северная Мастерская Акустики",
                "url": "https://sever-akustika.example.ru/",
            },
            {
                "@type": "WebSite",
                "@id": "https://sever-akustika.example.ru/#website",
                "url": "https://sever-akustika.example.ru/",
                "name": "Северная Мастерская Акустики",
                "inLanguage": "ru",
                "publisher": {"@id": "https://sever-akustika.example.ru/#org"},
            },
            {
                "@type": "WebPage",
                "@id": "https://sever-akustika.example.ru/#webpage",
                "url": "https://sever-akustika.example.ru/",
                "name": "Северная Мастерская Акустики: панели из карельской берёзы КМ1",
                "isPartOf": {"@id": "https://sever-akustika.example.ru/#website"},
            },
            {
                "@type": "Product",
                "@id": "https://sever-akustika.example.ru/#product",
                "name": "Реечный резонатор Гельмгольца «Берёза-КМ1» (NRC 0,85)",
                "brand": {"@id": "https://sever-akustika.example.ru/#org"},
                "description": "Перфорированные акустические панели из карельской берёзы камерной сушки с классом пожарной опасности КМ1.",
                "offers": {
                    "@type": "Offer",
                    "price": "11400",
                    "priceCurrency": "RUB",
                    "availability": "https://schema.org/InStock",
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": "https://sever-akustika.example.ru/#breadcrumbs",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Мастерская", "item": "https://sever-akustika.example.ru/"},
                    {"@type": "ListItem", "position": 2, "name": "Расчёт Сэбина RT60", "item": "https://sever-akustika.example.ru/#sabine"},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": "https://sever-akustika.example.ru/#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "Проходят ли деревянные панели пожарную сертификацию для общественных залов?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Все реечные потолочные и стеновые панели из берёзы проходят антипиреновую пропитку с сертификатом КМ1 (Г1, В1, Д2, Т1) и европейским классом B-s1,d0. К каждой партии прилагается протокол испытаний с эмиссией ЛОС ниже 0,05 мг/м3.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Деформируется ли массив берёзы в отопительный сезон при сухом воздухе?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Перекрёстно-клеёное основание из лущёного берёзового шпона камерной сушки 7,5% удерживает сезонную поводку в пределах +/-0,4 мм на погонный метр при колебаниях влажности воздуха от 20% до 70%.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Какой коэффициент звукопоглощения обеспечивают панели на речевых частотах?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "При монтаже на относе 50 мм с базальтовым вкладышем плотностью 45 кг/м3 взвешенный индекс звукопоглощения alpha_w составляет 0,85 (класс поглощения A по ГОСТ ISO 11654).",
                        },
                    },
                ],
            },
        ],
    },
    "body_html": """<a class="skip-link" href="#main-content">Перейти к основному содержимому</a>
<header class="site-header">
  <div class="header-wrap">
    <a class="atelier-title" href="#main-content">
      <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><line x1="4" y1="4" x2="4" y2="20" stroke="currentColor" stroke-width="2"/><line x1="10" y1="4" x2="10" y2="20" stroke="currentColor" stroke-width="2"/><line x1="16" y1="4" x2="16" y2="20" stroke="currentColor" stroke-width="2"/><line x1="21" y1="4" x2="21" y2="20" stroke="currentColor" stroke-width="2"/></svg>
      <span>Северная Мастерская Акустики</span>
    </a>
    <nav aria-label="Навигация по разделам">
      <ul class="atelier-nav">
        <li><a href="#projects">Объекты</a></li>
        <li><a href="#sabine">Калькулятор RT60</a></li>
        <li><a href="#faq">Нормативы КМ1</a></li>
        <li><a href="#consult">Запрос расчёта</a></li>
      </ul>
    </nav>
  </div>
</header>

<main id="main-content">
  <section class="hero-chamber">
    <div class="container nordic-grid">
      <div class="hero-essay">
        <p class="mono-val">ПЕТРОЗАВОДСК • САНКТ-ПЕТЕРБУРГ // ГОСТ ISO 3382-1</p>
        <h1>Акустические интерьеры из берёзы со временем реверберации 0,45-0,60 с</h1>
        <p class="dropcap-lead">Монолитный бетон и трёхкамерное панорамное остекление берегут тепло в северных залах, но растягивают затухание речевых частот за отметку 1,9 секунды. Мы изготавливаем калиброванные резонаторы Гельмгольца из карельской берёзы класса КМ1, приводящие разборчивость речи к норме лектория и камерной сцены.</p>
        <div class="btn-row">
          <a class="btn-pine" href="#sabine">Рассчитать затухание RT60 по формуле Сэбина</a>
          <a class="btn-stone" href="#consult">Отправить план зала инженеру-акустику</a>
        </div>
      </div>
      <div class="hero-acoustics" aria-label="Кривая спада звукового давления на 60 дБ">
        <p class="mono-val">Спад уровня -60 дБ в полосе 500-2000 Гц</p>
        <svg width="360" height="170" viewBox="0 0 360 170" role="img" aria-labelledby="decayTitle">
          <title id="decayTitle">График затухания реверберации до и после монтажа берёзовых панелей</title>
          <line x1="32" y1="18" x2="32" y2="146" stroke="currentColor" stroke-width="1.2"/>
          <line x1="32" y1="146" x2="342" y2="146" stroke="currentColor" stroke-width="1.2"/>
          <polyline points="32,24 330,144" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 4"/>
          <polyline id="treatedCurvePoly" points="32,24 148,144" fill="none" stroke="currentColor" stroke-width="2.5"/>
          <text x="200" y="76" font-size="11" fill="currentColor">Бетон без отделки: 1,92 с</text>
          <text x="72" y="136" font-size="11" fill="currentColor">После КМ1: 0,52 с</text>
        </svg>
      </div>
    </div>
  </section>

  <section id="projects" class="chapter-section">
    <div class="container">
      <h2>Завершённые акустические паспорта объектов</h2>
      <div class="dossier-grid">
        <article class="dossier-card">
          <span class="mono-val">ОБЪЕКТ 01 // 420 М2</span>
          <h3>Читальный зал политехнической библиотеки</h3>
          <p>Монтаж 190 м2 потолочных кассет снизил фоновый шум на 7,5 дБА и довёл индекс STI до 0,72 на последнем ряду.</p>
        </article>
        <article class="dossier-card">
          <span class="mono-val">ОБЪЕКТ 02 // 680 М2</span>
          <h3>Атриум инженерного бюро на Выборгской стороне</h3>
          <p>Стеновые рейки шагом 16 мм погасили порхающее эхо между стеклянными перегородками, сократив RT60 с 2,10 до 0,56 с.</p>
        </article>
        <article class="dossier-card">
          <span class="mono-val">ОБЪЕКТ 03 // 310 М2</span>
          <h3>Камерный зал музыкальной школы</h3>
          <p>Сочетание рассеивающих выпуклых профилей и щелевых ловушек выровняло АЧХ в диапазоне от 125 до 4000 Гц.</p>
        </article>
      </div>
    </div>
  </section>

  <section id="sabine" class="chapter-section">
    <div class="container">
      <h2>Предварительный расчёт времени реверберации Сэбина</h2>
      <div class="sabine-container">
        <div class="sabine-cols">
          <div>
            <div class="form-line">
              <label for="roomVolumeInput">Воздушный объём помещения (м3)</label>
              <input id="roomVolumeInput" name="volume_m3" type="number" min="60" max="15000" step="10" value="480" autocomplete="off"/>
            </div>
            <div class="form-line">
              <label for="panelAreaInput">Площадь панелей «Берёза-КМ1» NRC 0,85 (м2)</label>
              <input id="panelAreaInput" name="panel_m2" type="number" min="10" max="3000" step="5" value="140" autocomplete="off"/>
            </div>
          </div>
          <div>
            <table class="acoustic-table" aria-label="Расчёт акустических параметров">
              <tbody>
                <tr>
                  <th scope="row">Эквивалентный фонд поглощения A</th>
                  <td><output id="sabineAreaOut" for="roomVolumeInput panelAreaInput">147.8 Сэбин</output></td>
                </tr>
                <tr>
                  <th scope="row">Расчётное время реверберации RT60</th>
                  <td><output id="rt60SecondsOut" for="roomVolumeInput panelAreaInput">0.52 с</output></td>
                </tr>
                <tr>
                  <th scope="row">Смета комплекта КМ1 (11 400 ₽/м2)</th>
                  <td><output id="panelBudgetOut" for="roomVolumeInput panelAreaInput">1 596 000 ₽</output></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="faq" class="chapter-section">
    <div class="container">
      <h2>Ответы по пожарным нормам и микроклимату</h2>
      <div class="faq-column">
        <article class="faq-entry">
          <h3>Проходят ли деревянные панели пожарную сертификацию для общественных залов?</h3>
          <p>Все реечные потолочные и стеновые панели из берёзы проходят антипиреновую пропитку с сертификатом КМ1 (Г1, В1, Д2, Т1) и европейским классом B-s1,d0. К каждой партии прилагается протокол испытаний с эмиссией ЛОС ниже 0,05 мг/м3.</p>
        </article>
        <article class="faq-entry">
          <h3>Деформируется ли массив берёзы в отопительный сезон при сухом воздухе?</h3>
          <p>Перекрёстно-клеёное основание из лущёного берёзового шпона камерной сушки 7,5% удерживает сезонную поводку в пределах +/-0,4 мм на погонный метр при колебаниях влажности воздуха от 20% до 70%.</p>
        </article>
        <article class="faq-entry">
          <h3>Какой коэффициент звукопоглощения обеспечивают панели на речевых частотах?</h3>
          <p>При монтаже на относе 50 мм с базальтовым вкладышем плотностью 45 кг/м3 взвешенный индекс звукопоглощения alpha_w составляет 0,85 (класс поглощения A по ГОСТ ISO 11654).</p>
        </article>
      </div>
    </div>
  </section>

  <section id="consult" class="chapter-section">
    <div class="container">
      <h2>Отправить габариты зала для акустической модели</h2>
      <form id="acousticConsultForm" action="#consult" method="post" novalidate>
        <div class="sabine-cols">
          <div class="form-line">
            <label for="archNameInput">Имя главного архитектора или инженера проекта</label>
            <input id="archNameInput" name="name" type="text" required autocomplete="name"/>
          </div>
          <div class="form-line">
            <label for="archEmailInput">Электронная почта проектного бюро</label>
            <input id="archEmailInput" name="email" type="email" required autocomplete="email"/>
          </div>
        </div>
        <div class="hp-box" aria-hidden="true">
          <label for="telexTrapInput">Не заполняйте это техническое поле</label>
          <input id="telexTrapInput" name="telex_hp" type="text" tabindex="-1" autocomplete="off"/>
        </div>
        <button class="btn-pine" type="submit">Получить ведомость узлов примыкания DWG и расчёт RT60</button>
        <p id="consultStatus" class="mono-val" role="status" aria-live="polite">Прямая связь с акустическим отделом без рекламных рассылок.</p>
      </form>
    </div>
  </section>
</main>

<footer class="site-footer">
  <div class="container">
    <p>Северная Мастерская Акустики, 2026. Палитра OKLCH AAA, строгая политика CSP SHA-256, шрифты SIL OFL-1.1.</p>
  </div>
</footer>""",
    "ts_code": """interface SabineResult {
  absorptionSabins: number;
  rt60Sec: number;
  budgetRub: number;
  endX: number;
}

function enableTrustedTypes(): void {
  const w = window as unknown as {
    trustedTypes?: { createPolicy: (name: string, rules: { createHTML: (s: string) => string }) => unknown };
  };
  if (w.trustedTypes && typeof w.trustedTypes.createPolicy === "function") {
    try {
      w.trustedTypes.createPolicy("default", {
        createHTML: (s: string): string => s.replace(/[<>]/g, ""),
      });
    } catch {
      // Default policy already registered
    }
  }
}

function calculateSabine(volumeM3: number, panelM2: number): SabineResult {
  const safeVol = Math.max(60, Math.min(15000, volumeM3));
  const safePanels = Math.max(10, Math.min(3000, panelM2));
  const baseConcreteAbsorption = Math.pow(safeVol, 2 / 3) * 6 * 0.08;
  const absorptionSabins = baseConcreteAbsorption + safePanels * 0.85;
  const rt60Sec = (0.161 * safeVol) / Math.max(1, absorptionSabins);
  const budgetRub = Math.round(safePanels * 11400);
  const endX = Math.max(80, Math.min(330, Math.round(32 + (rt60Sec / 2.0) * 298)));
  return { absorptionSabins, rt60Sec, budgetRub, endX };
}

function initNordicAtelier(): void {
  enableTrustedTypes();

  const volInput = document.getElementById("roomVolumeInput") as HTMLInputElement | null;
  const areaInput = document.getElementById("panelAreaInput") as HTMLInputElement | null;
  const areaOut = document.getElementById("sabineAreaOut") as HTMLOutputElement | null;
  const rt60Out = document.getElementById("rt60SecondsOut") as HTMLOutputElement | null;
  const budgetOut = document.getElementById("panelBudgetOut") as HTMLOutputElement | null;
  const poly = document.getElementById("treatedCurvePoly");

  const updateSabine = (): void => {
    if (!volInput || !areaInput || !areaOut || !rt60Out || !budgetOut) {
      return;
    }
    const vol = Number.parseFloat(volInput.value || "480") || 480;
    const area = Number.parseFloat(areaInput.value || "140") || 140;
    const res = calculateSabine(vol, area);
    areaOut.textContent = `${res.absorptionSabins.toFixed(1)} Сэбин`;
    rt60Out.textContent = `${res.rt60Sec.toFixed(2)} с`;
    budgetOut.textContent = `${res.budgetRub.toLocaleString("ru-RU")} ₽`;
    if (poly) {
      poly.setAttribute("points", `32,24 ${res.endX},144`);
    }
  };

  if (volInput && areaInput) {
    volInput.addEventListener("input", updateSabine);
    areaInput.addEventListener("input", updateSabine);
    updateSabine();
  }

  const form = document.getElementById("acousticConsultForm") as HTMLFormElement | null;
  const trap = document.getElementById("telexTrapInput") as HTMLInputElement | null;
  const email = document.getElementById("archEmailInput") as HTMLInputElement | null;
  const status = document.getElementById("consultStatus");

  if (form && status) {
    form.addEventListener("submit", (ev: Event): void => {
      ev.preventDefault();
      if (trap && trap.value.trim().length > 0) {
        status.textContent = "Запрос отклонён защитной проверкой поля.";
        return;
      }
      const mail = email ? email.value.trim() : "";
      if (!mail.includes("@") || !mail.includes(".")) {
        status.textContent = "Введите корректный адрес электронной почты проектного бюро.";
        return;
      }
      status.textContent = "Параметры зала приняты: альбом узлов примыкания DWG подготовлен.";
    });
  }
}

initNordicAtelier();
export {};
""",
    "llms_txt": """# Северная Мастерская Акустики (Nordic Birch Acoustic Panels KM1)

> Проектирование и производство перфорированных акустических потолков и стеновых резонаторов Гельмгольца из карельской берёзы класса КМ1 (NRC 0,85) для лекториев, библиотек и общественных залов.

## Инженерные разделы
- [Паспорта объектов](https://sever-akustika.example.ru/#projects): Реализованные залы от 310 до 680 м2 со снижением RT60 до 0,52-0,56 с.
- [Калькулятор Сэбина](https://sever-akustika.example.ru/#sabine): Интерактивный расчёт эквивалентной площади поглощения и времени реверберации RT60.

## Сертификация и устойчивость
- [Нормативы КМ1 и микроклимат](https://sever-akustika.example.ru/#faq): Пожарный класс КМ1 / Euroclass B-s1,d0, эмиссия ЛОС ниже 0,05 мг/м3 и влажностный коридор 20-70%.
""",
    "zimage_prompts": [
        {
            "id": "nordic_hall_slats",
            "slot": "hero_primary",
            "canon_id": "05_nordic_architectural_minimal",
            "aspect_ratio": "16:9",
            "exact_text_in_frame": "KM1 NRC85",
            "prompt": "Nordic architectural lecture hall interior featuring vertical untreated Karelian birch acoustic wall slats and honed pale limestone floor, soft diffused high-latitude daylight through tall timber mullions, discreet brushed brass acoustic certification plate engraved 'KM1 NRC85', Hasselblad 50mm medium-format photography, serene spatial calm.",
            "negative_prompt": "neon LED strips, cluttered office chairs, glossy plastic, artificial HDR halo, people posing",
        },
        {
            "id": "nordic_helmholtz_joinery",
            "slot": "dossier_01",
            "canon_id": "05_nordic_architectural_minimal",
            "aspect_ratio": "4:3",
            "exact_text_in_frame": "RT60 0.52",
            "prompt": "Studio architectural macro cross-section sample of cross-laminated rotary-peeled birch acoustic panel showing precision 8mm Helmholtz micro-perforations and dark mineral wool backing on limestone plinth, stamped edge mark 'RT60 0.52', natural north-window daylight, 80mm planar macro lens.",
            "negative_prompt": "purple glow, plastic laminate woodgrain, cartoon hammer, harsh flash shadow, watermark",
        },
        {
            "id": "nordic_baffle_ceiling",
            "slot": "dossier_02",
            "canon_id": "05_nordic_architectural_minimal",
            "aspect_ratio": "16:9",
            "exact_text_in_frame": "HALL B2",
            "prompt": "Upward architectural perspective of suspended pale birch ceiling acoustic baffles inside minimalist reading room with clean concrete column stenciled 'HALL B2', balanced overcast skylight illumination, rectilinear 35mm tilt-shift lens, warm stone and natural timber tones.",
            "negative_prompt": "cyberpunk lights, messy HVAC ducts, lens flare, oversaturated sky, stock crowd",
        },
    ],
}
