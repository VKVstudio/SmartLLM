FILE: DESIGN.md
```markdown
# AETHERIA BIO-ROBOTICS DESIGN SYSTEM MANIFEST

## 1. Design Intent
AETHERIA BIO-ROBOTICS is an autonomous environmental and precision-agriculture drone platform. The interface expresses a Swiss typographic grid system with high-tech telemetry instrumentation. The visual tone is laboratory-grade, precise, calm, and operational.

The system prioritizes:
- measurable clarity
- dense but breathable data presentation
- monospaced telemetry where appropriate
- high-contrast accessibility
- deterministic layout behavior
- minimal ornament
- field-ready legibility on large screens and tablets

## 2. Color System: OKLCH Tokens

### Core surface and ink tokens
| Token | Value | Use | Target contrast on bone | Approx. contrast ratio |
|---|---|---|---:|---:|
| `--color-bone` | `oklch(0.97 0.008 95)` | Primary light laboratory surface | n/a | n/a |
| `--color-bone-soft` | `oklch(0.94 0.010 92)` | Secondary panels, table headers, subtle surfaces | n/a | n/a |
| `--color-bone-strong` | `oklch(0.91 0.012 90)` | Dividers, inset panels, hover surfaces | n/a | n/a |
| `--color-ink` | `oklch(0.14 0.015 255)` | Primary carbon ink text | 15.8:1 | ≥7:1 |
| `--color-ink-muted` | `oklch(0.36 0.020 255)` | Secondary text, captions, labels | 7.2:1 | ≥7:1 |
| `--color-ink-faint` | `oklch(0.50 0.022 255)` | Decorative non-text only | 4.2:1 | decorative only |

### Telemetry accent tokens
| Token | Value | Use | Text use | Approx. contrast on bone |
|---|---|---|---|---:|
| `--color-forest` | `oklch(0.45 0.14 155)` | Primary telemetry accent, borders, icons, active states | Not for body text | 5.4:1 |
| `--color-forest-ink` | `oklch(0.30 0.11 155)` | Accessible forest text and link text | Primary accessible forest text | 7.6:1 |
| `--color-forest-deep` | `oklch(0.22 0.09 155)` | High-emphasis forest UI text on bone | Strong text | 10.8:1 |
| `--color-signal` | `oklch(0.66 0.17 65)` | Signal amber, non-text indicators, warning markers | Not for body text | 3.1:1 |
| `--color-signal-ink` | `oklch(0.36 0.15 65)` | Accessible amber text on bone | Primary accessible amber text | 7.1:1 |
| `--color-signal-deep` | `oklch(0.28 0.13 65)` | High-emphasis amber UI text | Strong text | 10.2:1 |

### Contrast invariant
All body text, labels, links, form text, table text, and instructional copy must meet WCAG 2.2 AA text contrast of at least 7:1 against bone surfaces.

Allowed:
- `--color-ink` on `--color-bone`
- `--color-ink-muted` on `--color-bone`
- `--color-forest-ink` on `--color-bone`
- `--color-signal-ink` on `--color-bone`
- `--color-bone` on `--color-ink`

Forbidden:
- `--color-forest` as body text on bone
- `--color-signal` as body text on bone
- low-contrast muted text used for required form labels or validation messages

## 3. Modular Grid Rules

### Base module
- Base unit: `4px`
- Grid module: `8px`
- Section rhythm: multiples of `24px`
- Container gutters: `24px` mobile, `32px` tablet, `48px` desktop
- Max content width: `1280px`
- Max reading width: `72ch`

### Swiss grid structure
The layout uses a 12-column modular grid on desktop:
- 12 columns
- 24px gutter
- 8px baseline rhythm
- content blocks align to column boundaries
- data tables align numerals on the right
- telemetry values align to a monospaced optical column
- hero content spans columns 2–11 on desktop
- planner spans 7 columns, telemetry spans 5 columns
- comparison table spans full grid width
- FAQ spans columns 2–11

### Breakpoints
| Breakpoint | Grid |
|---|---|
| `< 640px` | 1 column, 24px gutters |
| `640–960px` | 6 columns, 32px gutters |
| `960–1280px` | 12 columns, 40px gutters |
| `> 1280px` | 12 columns, 48px gutters, max width 1280px |

## 4. Typography Scale

### Font stack
- Display/UI: system sans-serif stack with grotesque Swiss proportions
- Telemetry/data: system monospace stack
- No external font requests

### Modular scale
Base ratio: `1.25`
Mobile base: `17px`
Desktop base: `18px`

| Token | Approx. size | Use |
|---|---:|---|
| `--text-2xs` | `12px` | micro labels, table meta |
| `--text-xs` | `13px` | captions, helper text |
| `--text-sm` | `15px` | dense UI labels |
| `--text-base` | `18px` | body text |
| `--text-md` | `20px` | lead paragraphs |
| `--text-lg` | `24px` | section headings |
| `--text-xl` | `30px` | subheads |
| `--text-2xl` | `38px` | major headings |
| `--text-3xl` | `48px` | hero display |
| `--text-4xl` | `60px` | large telemetry display |

### Typography invariants
- Body line height: `1.55`
- Heading line height: `1.1`
- Display line height: `1.05`
- Telemetry line height: `1.25`
- Paragraph max width: `72ch`
- Table numerals use tabular figures
- Micro labels use `letter-spacing: 0.08em`
- Headings use `letter-spacing: -0.025em`
- No justified text
- No decorative uppercase body copy
- Uppercase only for micro labels, badges, and table headers

## 5. Component Invariants

### Panels
- 1px border using `--color-bone-strong`
- background using `--color-bone` or `--color-bone-soft`
- corner radius: `0px` for Swiss precision, `4px` max for interactive controls
- no drop shadows except inset telemetry glow
- focus ring: `2px solid --color-forest-ink` with `outline-offset: 2px`

### Buttons
- Primary: bone background, ink text, forest border
- Secondary: bone-soft background, ink text, bone-strong border
- Destructive/alert: signal ink text, signal border
- Minimum touch target: `44px`
- Disabled: `opacity: 0.55`, cursor `not-allowed`

### Inputs
- Label always visible
- Helper text optional
- Error text uses `--color-signal-ink`
- Error border uses `--color-signal-ink`
- Success state uses `--color-forest-ink`
- Numeric telemetry inputs use monospace
- Inputs must not rely on placeholder as label

### Tables
- Header row uses bone-soft background
- Numeric columns right-aligned
- Row dividers use bone-strong
- Filtered rows must remain semantically present in DOM
- Table must expose status via aria-live

### Telemetry chips
- Chip text must use ink or accessible ink variants
- Accent chip borders may use forest or signal
- Accent fill only for non-text decorative areas

### FAQ
- Native `<details>` preferred for zero-JS resilience
- Question text uses `--color-ink`
- Answer text uses `--color-ink-muted`
- Disclosure indicator uses accessible forest ink

### Mission planner
- Outputs must update live
- Invalid inputs display inline validation
- Battery swap count must be integer
- Waypoint count must be integer
- Coverage area must be displayed in hectares and square meters
- Mission duration displayed in hours, minutes, seconds

## 6. Motion and Interaction
- Transitions: `120ms` ease-out for UI state changes
- No parallax
- No autoplay motion
- Respect `prefers-reduced-motion: reduce`
- Focus states must remain visible without motion

## 7. Accessibility
- Semantic HTML5 landmarks
- Skip link
- Visible focus indicators
- Form labels associated with controls
- Validation messages announced via `aria-live`
- Table filter controls announced via `aria-live`
- Contrast ratio target: 7:1 for all text
- No color-only status communication
- SVG schematic includes `<title>` and `<desc>`
- JSON-LD FAQ text must match visible FAQ verbatim

## 8. Security Invariants
- Strict Content-Security-Policy
- No external HTTP requests
- Inline scripts and styles only
- No third-party analytics
- No remote fonts
- No external images
- Frame ancestors disabled
- MIME sniffing disabled
- Referrer leakage minimized

## 9. Content Architecture
Primary sections:
1. Hero: autonomous environmental and precision-agriculture platform
2. Mission planner: live coverage calculation
3. Telemetry filter: platform comparison
4. Drone comparison table
5. Multispectral sensor schematic
6. FAQ
7. Fleet deployment inquiry form

## 10. Data Model
Platform entities:
- `AETHER-X4 Multispectral`
- `AETHER-H8 Heavy Lidar`
- `AETHER-S2 Soil Probe`

Telemetry fields:
- payload
- sensor array
- endurance
- RTK accuracy
- IP rating
- deployment class
- data link
- power draw
- coverage profile

Mission fields:
- field area
- swath width
- cruise speed
- battery capacity
- battery swaps
- waypoint count
- estimated mission time
- path length
- coverage pass count

## 11. File Map
- `DESIGN.md`: design manifest
- `tokens.css`: standalone design tokens
- `app.js`: interactive mission planner, telemetry filter, form validation
- `index.html`: standalone semantic application page
- `zimage_prompts.json`: Z-Image-Turbo art-direction prompts
- `llms.txt`: llmstxt.org documentation
- `_headers`: Cloudflare Pages security headers
```

FILE: tokens.css
```css
:root {
  /* Core laboratory surface */
  --color-bone: oklch(0.97 0.008 95);
  --color-bone-soft: oklch(0.94 0.010 92);
  --color-bone-strong: oklch(0.91 0.012 90);
  --color-bone-inset: oklch(0.88 0.012 88);

  /* Carbon ink */
  --color-ink: oklch(0.14 0.015 255);
  --color-ink-muted: oklch(0.36 0.020 255);
  --color-ink-faint: oklch(0.50 0.022 255);

  /* Forest telemetry accent */
  --color-forest: oklch(0.45 0.14 155);
  --color-forest-ink: oklch(0.30 0.11 155);
  --color-forest-deep: oklch(0.22 0.09 155);
  --color-forest-soft: oklch(0.88 0.055 155);

  /* Signal amber accent */
  --color-signal: oklch(0.66 0.17 65);
  --color-signal-ink: oklch(0.36 0.15 65);
  --color-signal-deep: oklch(0.28 0.13 65);
  --color-signal-soft: oklch(0.92 0.070 75);

  /* Semantic tokens */
  --surface-page: var(--color-bone);
  --surface-panel: var(--color-bone);
  --surface-subtle: var(--color-bone-soft);
  --surface-inset: var(--color-bone-inset);
  --border-default: var(--color-bone-strong);
  --border-strong: var(--color-ink);
  --border-accent: var(--color-forest);
  --border-signal: var(--color-signal);

  --text-primary: var(--color-ink);
  --text-secondary: var(--color-ink-muted);
  --text-accent: var(--color-forest-ink);
  --text-signal: var(--color-signal-ink);
  --text-inverse: var(--color-bone);

  --focus-ring: var(--color-forest-ink);
  --status-ok: var(--color-forest-ink);
  --status-warn: var(--color-signal-ink);
  --status-error: var(--color-signal-deep);

  /* Spacing scale */
  --space-0: 0px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 40px;
  --space-8: 48px;
  --space-9: 64px;
  --space-10: 80px;
  --space-11: 96px;
  --space-12: 128px;

  /* Typography */
  --font-ui: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
    "Liberation Mono", monospace;

  --text-2xs: 0.75rem;
  --text-xs: 0.8125rem;
  --text-sm: 0.9375rem;
  --text-base: 1.125rem;
  --text-md: 1.25rem;
  --text-lg: 1.5rem;
  --text-xl: 1.875rem;
  --text-2xl: 2.375rem;
  --text-3xl: 3rem;
  --text-4xl: 3.75rem;

  --line-ui: 1.55;
  --line-heading: 1.1;
  --line-display: 1.05;
  --line-telemetry: 1.25;

  --tracking-tight: -0.025em;
  --tracking-normal: -0.01em;
  --tracking-wide: 0.08em;
  --tracking-mono: 0.02em;

  --weight-regular: 400;
  --weight-medium: 500;
  --weight-semibold: 600;
  --weight-bold: 700;

  /* Layout */
  --container-max: 1280px;
  --reading-max: 72ch;
  --grid-gutter: var(--space-5);
  --grid-columns: 12;
  --grid-column-gap: var(--space-5);

  /* Borders and radii */
  --border-width: 1px;
  --radius-none: 0px;
  --radius-sm: 4px;
  --radius-md: 8px;

  /* Motion */
  --transition-fast: 120ms ease-out;
  --transition-base: 180ms ease-out;

  /* Shadows */
  --shadow-none: none;
  --shadow-inset: inset 0 0 0 1px var(--color-bone-strong);
}

@media (min-width: 640px) {
  :root {
    --grid-gutter: var(--space-6);
    --grid-column-gap: var(--space-6);
  }
}

@media (min-width: 960px) {
  :root {
    --grid-gutter: var(--space-7);
    --grid-column-gap: var(--space-7);
  }
}

@media (min-width: 1280px) {
  :root {
    --grid-gutter: var(--space-8);
    --grid-column-gap: var(--space-8);
  }
}

@media (prefers-reduced-motion: reduce) {
  :root {
    --transition-fast: 0ms;
    --transition-base: 0ms;
  }
}
```

FILE: app.js
```js
/**
 * AETHERIA BIO-ROBOTICS — interactive mission planner, telemetry filter,
 * and fleet deployment inquiry validation.
 *
 * Standalone ES6 module.
 */

const AetheriaApp = (() => {
  "use strict";

  const PLATFORMS = [
    {
      id: "x4",
      name: "AETHER-X4 Multispectral",
      payload: "12-band multispectral + RTK gimbal",
      enduranceMin: 38,
      powerW: 180,
      cruiseSpeed: 14,
      swath: 112,
      ip: "IP67",
      accuracy: "±1.2 cm RTK",
      deployment: "Small-field crop scouting",
      dataLink: "2.4 GHz telemetry + 5.8 GHz video",
      coverageProfile: "RGB / NIR / RedEdge / Vegetation indices",
      status: "active",
    },
    {
      id: "h8",
      name: "AETHER-H8 Heavy Lidar",
      payload: "128-channel LiDAR + thermal payload",
      enduranceMin: 26,
      powerW: 320,
      cruiseSpeed: 11,
      swath: 180,
      ip: "IP68",
      accuracy: "±2.8 cm RTK",
      deployment: "Terrain mapping / biomass volume",
      dataLink: "2.4 GHz telemetry + encrypted uplink",
      coverageProfile: "LiDAR point cloud / thermal / canopy height",
      status: "active",
    },
    {
      id: "s2",
      name: "AETHER-S2 Soil Probe",
      payload: "Electrical conductivity + moisture probe",
      enduranceMin: 42,
      powerW: 150,
      cruiseSpeed: 9,
      swath: 72,
      ip: "IP66",
      accuracy: "±3.5 cm RTK",
      deployment: "Soil sampling / moisture mapping",
      dataLink: "2.4 GHz telemetry + local SD logging",
      coverageProfile: "Conductivity / moisture / compaction",
      status: "active",
    },
  ];

  const state = {
    filter: "all",
    platform: "x4",
    formErrors: {},
  };

  const selectors = {
    filterButtons: "[data-filter-button]",
    platformRows: "[data-platform-row]",
    telemetrySummary: "[data-telemetry-summary]",
    plannerForm: "[data-planner-form]",
    plannerOutputs: "[data-output]",
    inquiryForm: "[data-inquiry-form]",
    inquiryErrors: "[data-inquiry-errors]",
    inquiryStatus: "[data-inquiry-status]",
  };

  function clampNumber(value, min, max, fallback) {
    const n = Number(value);
    if (!Number.isFinite(n)) return fallback;
    return Math.min(max, Math.max(min, n));
  }

  function formatDuration(seconds) {
    if (!Number.isFinite(seconds) || seconds <= 0) return "0h 00m 00s";
    const total = Math.max(0, Math.floor(seconds));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return `${h}h ${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`;
  }

  function formatNumber(value, digits = 2) {
    if (!Number.isFinite(value)) return "0";
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: digits,
    }).format(value);
  }

  function calculateMission(inputs) {
    const fieldHa = clampNumber(inputs.fieldHa, 0.01, 100000, 0);
    const swathM = clampNumber(inputs.swathM, 1, 500, 0);
    const cruiseSpeed = clampNumber(inputs.cruiseSpeed, 1, 40, 0);
    const batteryWh = clampNumber(inputs.batteryWh, 1, 20000, 0);
    const powerW = clampNumber(inputs.powerW, 50, 800, 180);
    const overlapPct = clampNumber(inputs.overlapPct, 0, 60, 10);
    const headlandFactor = 1.12;
    const turnSecondsPerPass = 5;

    if (fieldHa <= 0 || swathM <= 0 || cruiseSpeed <= 0 || batteryWh <= 0) {
      return {
        valid: false,
        areaM2: 0,
        effectiveSwath: 0,
        pathLengthM: 0,
        missionTimeSec: 0,
        enduranceSec: 0,
        batterySwaps: 0,
        waypointCount: 0,
        coveragePasses: 0,
      };
    }

    const areaM2 = fieldHa * 10000;
    const effectiveSwath = swathM * (1 - overlapPct / 100);
    const pathLengthM = areaM2 / effectiveSwath;
    const squareSideM = Math.sqrt(areaM2);
    const coveragePasses = Math.max(1, Math.ceil(squareSideM / effectiveSwath));
    const waypointSpacingM = Math.max(50, effectiveSwath * 2);
    const waypointCount = Math.max(
      coveragePasses * 2,
      Math.ceil(pathLengthM / waypointSpacingM) + coveragePasses
    );

    const straightTimeSec = pathLengthM / cruiseSpeed;
    const maneuverTimeSec = coveragePasses * turnSecondsPerPass;
    const missionTimeSec = straightTimeSec * headlandFactor + maneuverTimeSec;

    const enduranceSec = (batteryWh / powerW) * 3600;
    const batterySwaps = enduranceSec > 0
      ? Math.max(1, Math.ceil(missionTimeSec / enduranceSec))
      : 1;

    return {
      valid: true,
      areaM2,
      effectiveSwath,
      pathLengthM,
      missionTimeSec,
      enduranceSec,
      batterySwaps,
      waypointCount,
      coveragePasses,
    };
  }

  function setOutput(name, value) {
    const el = document.querySelector(`${selectors.plannerOutputs}[data-output="${name}"]`);
    if (el) el.textContent = value;
  }

  function updatePlanner() {
    const form = document.querySelector(selectors.plannerForm);
    if (!form) return;

    const inputs = {
      fieldHa: form.elements["field-ha"]?.value,
      swathM: form.elements["swath-m"]?.value,
      cruiseSpeed: form.elements["cruise-speed"]?.value,
      batteryWh: form.elements["battery-wh"]?.value,
      powerW: form.elements["power-w"]?.value,
      overlapPct: form.elements["overlap-pct"]?.value,
    };

    const result = calculateMission(inputs);

    setOutput("area-m2", result.valid ? formatNumber(result.areaM2, 0) : "—");
    setOutput("effective-swath", result.valid ? formatNumber(result.effectiveSwath, 1) : "—");
    setOutput("path-length", result.valid ? formatNumber(result.pathLengthM, 1) : "—");
    setOutput("coverage-passes", result.valid ? formatNumber(result.coveragePasses, 0) : "—");
    setOutput("waypoint-count", result.valid ? formatNumber(result.waypointCount, 0) : "—");
    setOutput("mission-time", result.valid ? formatDuration(result.missionTimeSec) : "—");
    setOutput("endurance", result.valid ? formatDuration(result.enduranceSec) : "—");
    setOutput("battery-swaps", result.valid ? formatNumber(result.batterySwaps, 0) : "—");

    const status = document.querySelector("[data-planner-status]");
    if (status) {
      status.textContent = result.valid
        ? "Coverage model active. Inputs updated live."
        : "Enter positive values to generate a coverage model.";
    }
  }

  function filterPlatforms(filter) {
    state.filter = filter;

    const rows = document.querySelectorAll(selectors.platformRows);
    rows.forEach((row) => {
      const id = row.getAttribute("data-platform-row");
      const visible = filter === "all" || id === filter;
      row.hidden = !visible;
      row.setAttribute("aria-hidden", String(!visible));
    });

    const buttons = document.querySelectorAll(selectors.filterButtons);
    buttons.forEach((button) => {
      const isActive = button.getAttribute("data-filter-button") === filter;
      button.setAttribute("aria-pressed", String(isActive));
    });

    const summary = document.querySelector(selectors.telemetrySummary);
    if (summary) {
      const visible = filter === "all"
        ? "all platforms"
        : PLATFORMS.find((p) => p.id === filter)?.name || filter;
      summary.textContent = `Telemetry filter: ${visible}.`;
    }
  }

  function bindFilterButtons() {
    const buttons = document.querySelectorAll(selectors.filterButtons);
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        filterPlatforms(button.getAttribute("data-filter-button"));
      });
    });
  }

  function bindPlatformSelection() {
    const selects = document.querySelectorAll("[data-platform-select]");
    selects.forEach((select) => {
      select.addEventListener("change", () => {
        state.platform = select.value || "x4";
        const platform = PLATFORMS.find((p) => p.id === state.platform);
        if (!platform) return;

        const form = document.querySelector(selectors.plannerForm);
        if (!form) return;

        if (form.elements["swath-m"]) form.elements["swath-m"].value = platform.swath;
        if (form.elements["cruise-speed"]) form.elements["cruise-speed"].value = platform.cruiseSpeed;
        if (form.elements["power-w"]) form.elements["power-w"].value = platform.powerW;

        updatePlanner();
      });
    });
  }

  function isEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value.trim());
  }

  function validateInquiryForm(form) {
    const errors = {};
    const data = new FormData(form);

    const name = String(data.get("name") || "").trim();
    const email = String(data.get("email") || "").trim();
    const organization = String(data.get("organization") || "").trim();
    const fleet = String(data.get("fleet-size") || "").trim();
    const hectares = String(data.get("hectares") || "").trim();
    const message = String(data.get("message") || "").trim();
    const consent = form.elements["consent"]?.checked;

    if (!name) errors.name = "Required: operator or team name.";
    else if (name.length < 2) errors.name = "Name must be at least 2 characters.";

    if (!email) errors.email = "Required: contact email.";
    else if (!isEmail(email)) errors.email = "Enter a valid email address.";

    if (!organization) errors.organization = "Required: organization name.";
    else if (organization.length < 2) errors.organization = "Organization must be at least 2 characters.";

    const fleetNum = Number(fleet);
    if (!fleet) errors.fleet = "Required: requested fleet size.";
    else if (!Number.isInteger(fleetNum) || fleetNum < 1 || fleetNum > 50) {
      errors.fleet = "Fleet size must be an integer between 1 and 50.";
    }

    const hectaresNum = Number(hectares);
    if (!hectares) errors.hectares = "Required: approximate field hectares.";
    else if (!Number.isFinite(hectaresNum) || hectaresNum < 1 || hectaresNum > 100000) {
      errors.hectares = "Hectares must be between 1 and 100000.";
    }

    if (message.length > 1200) errors.message = "Message must be 1200 characters or fewer.";

    if (!consent) errors.consent = "Required: consent to deployment coordination.";

    state.formErrors = errors;
    return errors;
  }

  function renderInquiryErrors(errors) {
    const container = document.querySelector(selectors.inquiryErrors);
    const status = document.querySelector(selectors.inquiryStatus);

    if (!container) return;

    container.innerHTML = "";

    const entries = Object.entries(errors);
    if (entries.length === 0) {
      if (status) status.textContent = "Inquiry valid. Ready for secure fleet deployment coordination.";
      return;
    }

    entries.forEach(([field, message]) => {
      const p = document.createElement("p");
      p.className = "form-error";
      p.textContent = message;
      container.appendChild(p);

      const input = document.querySelector(`[data-field="${field}"]`);
      if (input) {
        input.setAttribute("aria-invalid", "true");
        input.classList.add("is-invalid");
      }
    });

    if (status) status.textContent = "Inquiry contains validation errors.";
  }

  function clearInquiryErrors() {
    const container = document.querySelector(selectors.inquiryErrors);
    const status = document.querySelector(selectors.inquiryStatus);

    if (container) container.innerHTML = "";

    document.querySelectorAll("[data-field]").forEach((input) => {
      input.removeAttribute("aria-invalid");
      input.classList.remove("is-invalid");
    });

    if (status) status.textContent = "";
  }

  function bindInquiryForm() {
    const form = document.querySelector(selectors.inquiryForm);
    if (!form) return;

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      clearInquiryErrors();

      const errors = validateInquiryForm(form);
      renderInquiryErrors(errors);

      if (Object.keys(errors).length === 0) {
        const status = document.querySelector(selectors.inquiryStatus);
        if (status) {
          status.textContent = "Inquiry submitted locally. A fleet deployment coordinator will route this to mission operations.";
        }
        form.reset();
      }
    });

    form.addEventListener("input", () => {
      clearInquiryErrors();
    });
  }

  function initPlanner() {
    const form = document.querySelector(selectors.plannerForm);
    if (!form) return;

    form.addEventListener("input", updatePlanner);
    form.addEventListener("change", updatePlanner);

    const platformSelect = document.querySelector("[data-platform-select]");
    if (platformSelect && PLATFORMS.length > 0) {
      platformSelect.value = state.platform;
      platformSelect.dispatchEvent(new Event("change"));
    }

    updatePlanner();
  }

  function init() {
    bindFilterButtons();
    bindPlatformSelection();
    initPlanner();
    bindInquiryForm();

    filterPlatforms(state.filter);

    document.querySelectorAll("[data-platform-card]").forEach((card) => {
      const id = card.getAttribute("data-platform-card");
      const platform = PLATFORMS.find((p) => p.id === id);
      if (!platform) return;

      const nameEl = card.querySelector("[data-platform-name]");
      const payloadEl = card.querySelector("[data-platform-payload]");
      const enduranceEl = card.querySelector("[data-platform-endurance]");
      const powerEl = card.querySelector("[data-platform-power]");

      if (nameEl) nameEl.textContent = platform.name;
      if (payloadEl) payloadEl.textContent = platform.payload;
      if (enduranceEl) enduranceEl.textContent = `${platform.enduranceMin} min`;
      if (powerEl) powerEl.textContent = `${platform.powerW} W`;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }

  return {
    init,
    calculateMission,
    filterPlatforms,
    PLATFORMS,
  };
})();

window.AetheriaApp = AetheriaApp;

export default AetheriaApp;
export { AetheriaApp, calculateMission, filterPlatforms };
```

FILE: index.html
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="AETHERIA BIO-ROBOTICS autonomous environmental and precision-agriculture drone platform with live mission planning, telemetry filtering, and fleet deployment inquiry." />
  <meta name="theme-color" content="oklch(0.97 0.008 95)" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'data:'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'" />

  <title>AETHERIA BIO-ROBOTICS — Autonomous Environmental &amp; Precision-Agriculture Drone Platform</title>

  <style>
    :root {
      --color-bone: oklch(0.97 0.008 95);
      --color-bone-soft: oklch(0.94 0.010 92);
      --color-bone-strong: oklch(0.91 0.012 90);
      --color-bone-inset: oklch(0.88 0.012 88);

      --color-ink: oklch(0.14 0.015 255);
      --color-ink-muted: oklch(0.36 0.020 255);
      --color-ink-faint: oklch(0.50 0.022 255);

      --color-forest: oklch(0.45 0.14 155);
      --color-forest-ink: oklch(0.30 0.11 155);
      --color-forest-deep: oklch(0.22 0.09 155);
      --color-forest-soft: oklch(0.88 0.055 155);

      --color-signal: oklch(0.66 0.17 65);
      --color-signal-ink: oklch(0.36 0.15 65);
      --color-signal-deep: oklch(0.28 0.13 65);
      --color-signal-soft: oklch(0.92 0.070 75);

      --surface-page: var(--color-bone);
      --surface-panel: var(--color-bone);
      --surface-subtle: var(--color-bone-soft);
      --surface-inset: var(--color-bone-inset);

      --border-default: var(--color-bone-strong);
      --border-strong: var(--color-ink);
      --border-accent: var(--color-forest);
      --border-signal: var(--color-signal);

      --text-primary: var(--color-ink);
      --text-secondary: var(--color-ink-muted);
      --text-accent: var(--color-forest-ink);
      --text-signal: var(--color-signal-ink);
      --text-inverse: var(--color-bone);

      --focus-ring: var(--color-forest-ink);

      --space-1: 4px;
      --space-2: 8px;
      --space-3: 12px;
      --space-4: 16px;
      --space-5: 24px;
      --space-6: 32px;
      --space-7: 40px;
      --space-8: 48px;
      --space-9: 64px;
      --space-10: 80px;
      --space-11: 96px;

      --font-ui: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;

      --text-2xs: 0.75rem;
      --text-xs: 0.8125rem;
      --text-sm: 0.9375rem;
      --text-base: 1.125rem;
      --text-md: 1.25rem;
      --text-lg: 1.5rem;
      --text-xl: 1.875rem;
      --text-2xl: 2.375rem;
      --text-3xl: 3rem;
      --text-4xl: 3.75rem;

      --line-ui: 1.55;
      --line-heading: 1.1;
      --line-display: 1.05;
      --line-telemetry: 1.25;

      --tracking-tight: -0.025em;
      --tracking-normal: -0.01em;
      --tracking-wide: 0.08em;
      --tracking-mono: 0.02em;

      --container-max: 1280px;
      --reading-max: 72ch;

      --border-width: 1px;
      --radius-none: 0px;
      --radius-sm: 4px;
      --radius-md: 8px;

      --transition-fast: 120ms ease-out;
      --transition-base: 180ms ease-out;
    }

    @media (min-width: 640px) {
      :root {
        --space-page: var(--space-6);
      }
    }

    @media (min-width: 960px) {
      :root {
        --space-page: var(--space-7);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      :root {
        --transition-fast: 0ms;
        --transition-base: 0ms;
      }
      * {
        animation: none !important;
        transition: none !important;
      }
    }

    *,
    *::before,
    *::after {
      box-sizing: border-box;
    }

    html {
      color-scheme: light;
      background: var(--surface-page);
      scroll-behavior: smooth;
    }

    body {
      margin: 0;
      font-family: var(--font-ui);
      font-size: var(--text-base);
      line-height: var(--line-ui);
      color: var(--text-primary);
      background: var(--surface-page);
      letter-spacing: var(--tracking-normal);
    }

    .skip-link {
      position: absolute;
      left: var(--space-4);
      top: var(--space-4);
      padding: var(--space-3) var(--space-4);
      background: var(--color-ink);
      color: var(--text-inverse);
      border: var(--border-width) solid var(--color-ink);
      text-decoration: none;
      font-weight: 600;
    }

    .skip-link:focus {
      outline: 2px solid var(--focus-ring);
      outline-offset: 2px;
    }

    .container {
      width: min(100%, var(--container-max));
      margin-inline: auto;
      padding-inline: var(--space-5);
    }

    @media (min-width: 640px) {
      .container { padding-inline: var(--space-6); }
    }

    @media (min-width: 960px) {
      .container { padding-inline: var(--space-7); }
    }

    header.site-header {
      border-bottom: var(--border-width) solid var(--border-default);
      background: var(--surface-page);
    }

    .header-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: var(--space-4);
      align-items: center;
      padding-block: var(--space-5);
    }

    @media (min-width: 960px) {
      .header-grid {
        grid-template-columns: minmax(0, 1fr) auto;
        gap: var(--space-6);
      }
    }

    .brand {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      min-width: 0;
    }

    .brand-mark {
      width: 44px;
      height: 44px;
      border: 1px solid var(--color-forest);
      background: var(--color-forest-soft);
      display: grid;
      place-items: center;
      color: var(--color-forest-deep);
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      font-weight: 700;
      letter-spacing: var(--tracking-wide);
    }

    .brand-text {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    .brand-name {
      font-size: var(--text-md);
      font-weight: 700;
      letter-spacing: var(--tracking-tight);
      line-height: 1.1;
    }

    .brand-sub {
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      color: var(--text-secondary);
      letter-spacing: var(--tracking-wide);
      text-transform: uppercase;
    }

    nav.site-nav {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3);
    }

    nav.site-nav a {
      color: var(--text-secondary);
      text-decoration: none;
      font-size: var(--text-sm);
      font-weight: 600;
      padding: var(--space-2) var(--space-3);
      border: 1px solid transparent;
      transition: color var(--transition-fast), border-color var(--transition-fast);
    }

    nav.site-nav a:hover,
    nav.site-nav a:focus {
      color: var(--color-forest-deep);
      border-color: var(--color-forest);
    }

    main {
      display: grid;
      gap: var(--space-9);
      padding-block: var(--space-8);
    }

    .hero {
      display: grid;
      gap: var(--space-6);
      border: var(--border-width) solid var(--border-default);
      background: var(--surface-panel);
      padding: var(--space-6);
    }

    @media (min-width: 960px) {
      .hero {
        grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
        padding: var(--space-8);
      }
    }

    .eyebrow {
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      color: var(--text-accent);
      letter-spacing: var(--tracking-wide);
      text-transform: uppercase;
      margin: 0 0 var(--space-3);
    }

    h1 {
      margin: 0;
      font-size: clamp(2.5rem, 4vw, var(--text-4xl));
      line-height: var(--line-display);
      letter-spacing: var(--tracking-tight);
      font-weight: 700;
      max-width: 18ch;
    }

    .lead {
      margin: var(--space-4) 0 0;
      max-width: var(--reading-max);
      color: var(--text-secondary);
      font-size: var(--text-md);
    }

    .hero-actions {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3);
      margin-top: var(--space-5);
    }

    .button {
      appearance: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      padding: var(--space-3) var(--space-4);
      border: 1px solid var(--color-forest);
      background: var(--surface-panel);
      color: var(--text-primary);
      font: inherit;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
      transition: background var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast);
    }

    .button:hover,
    .button:focus {
      border-color: var(--color-forest-deep);
      color: var(--color-forest-deep);
    }

    .button.secondary {
      border-color: var(--border-default);
      color: var(--text-secondary);
      background: var(--surface-subtle);
    }

    .button.secondary:hover,
    .button.secondary:focus {
      border-color: var(--color-forest);
      color: var(--color-forest-deep);
    }

    .button:focus-visible,
    a:focus-visible,
    input:focus-visible,
    select:focus-visible,
    textarea:focus-visible,
    summary:focus-visible,
    button:focus-visible {
      outline: 2px solid var(--focus-ring);
      outline-offset: 2px;
    }

    .hero-panel {
      border: 1px solid var(--border-default);
      background: var(--surface-subtle);
      padding: var(--space-5);
      display: grid;
      gap: var(--space-4);
      align-content: start;
    }

    .panel-title {
      margin: 0;
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      color: var(--text-secondary);
      letter-spacing: var(--tracking-wide);
      text-transform: uppercase;
    }

    .metric-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: var(--space-3);
    }

    .metric {
      border: 1px solid var(--border-default);
      background: var(--surface-panel);
      padding: var(--space-3);
      display: grid;
      gap: var(--space-1);
    }

    .metric-label {
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      color: var(--text-secondary);
      letter-spacing: var(--tracking-wide);
      text-transform: uppercase;
    }

    .metric-value {
      font-family: var(--font-mono);
      font-size: var(--text-lg);
      line-height: var(--line-telemetry);
      font-weight: 700;
      color: var(--color-forest-deep);
      font-variant-numeric: tabular-nums;
    }

    .metric-unit {
      font-size: var(--text-xs);
      color: var(--text-secondary);
    }

    section {
      display: grid;
      gap: var(--space-5);
    }

    .section-head {
      display: grid;
      gap: var(--space-2);
      border-top: 1px solid var(--border-default);
      padding-top: var(--space-5);
    }

    h2 {
      margin: 0;
      font-size: clamp(1.75rem, 2.5vw, var(--text-2xl));
      line-height: var(--line-heading);
      letter-spacing: var(--tracking-tight);
      font-weight: 700;
    }

    .section-subtitle {
      margin: 0;
      color: var(--text-secondary);
      max-width: var(--reading-max);
    }

    .grid-2 {
      display: grid;
      gap: var(--space-5);
    }

    @media (min-width: 960px) {
      .grid-2 {
        grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
      }
    }

    .panel {
      border: 1px solid var(--border-default);
      background: var(--surface-panel);
      padding: var(--space-5);
    }

    .panel + .panel {
      margin-top: var(--space-4);
    }

    .form-grid {
      display: grid;
      gap: var(--space-4);
    }

    .field {
      display: grid;
      gap: var(--space-2);
    }

    .field label {
      font-size: var(--text-sm);
      font-weight: 700;
      color: var(--text-primary);
    }

    .field .help {
      font-size: var(--text-xs);
      color: var(--text-secondary);
    }

    input,
    select,
    textarea {
      width: 100%;
      font: inherit;
      color: var(--text-primary);
      background: var(--surface-panel);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-none);
      padding: var(--space-3);
      min-height: 44px;
      transition: border-color var(--transition-fast);
    }

    textarea {
      min-height: 120px;
      resize: vertical;
    }

    input[type="checkbox"] {
      width: 24px;
      height: 24px;
      min-height: 24px;
      accent-color: var(--color-forest-ink);
    }

    input:hover,
    select:hover,
    textarea:hover {
      border-color: var(--color-forest);
    }

    input.is-invalid,
    select.is-invalid,
    textarea.is-invalid {
      border-color: var(--color-signal-ink);
      background: var(--color-signal-soft);
    }

    .form-error {
      margin: 0;
      color: var(--color-signal-deep);
      font-size: var(--text-sm);
      font-weight: 700;
    }

    .status {
      margin: var(--space-2) 0 0;
      color: var(--text-accent);
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      min-height: 1.5rem;
    }

    .status.error {
      color: var(--color-signal-deep);
    }

    .output-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: var(--space-3);
    }

    @media (min-width: 640px) {
      .output-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }
    }

    .output {
      border: 1px solid var(--border-default);
      background: var(--surface-subtle);
      padding: var(--space-3);
      display: grid;
      gap: var(--space-1);
    }

    .output-label {
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      color: var(--text-secondary);
      letter-spacing: var(--tracking-wide);
      text-transform: uppercase;
    }

    .output-value {
      font-family: var(--font-mono);
      font-size: var(--text-md);
      line-height: var(--line-telemetry);
      font-weight: 700;
      color: var(--color-forest-deep);
      font-variant-numeric: tabular-nums;
    }

    .filter-bar {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
      margin-bottom: var(--space-4);
    }

    .filter-button {
      appearance: none;
      border: 1px solid var(--border-default);
      background: var(--surface-subtle);
      color: var(--text-secondary);
      font: inherit;
      font-size: var(--text-sm);
      font-weight: 700;
      padding: var(--space-2) var(--space-3);
      min-height: 40px;
      cursor: pointer;
      transition: border-color var(--transition-fast), color var(--transition-fast), background var(--transition-fast);
    }

    .filter-button:hover,
    .filter-button:focus {
      border-color: var(--color-forest);
      color: var(--color-forest-deep);
    }

    .filter-button[aria-pressed="true"] {
      border-color: var(--color-forest);
      background: var(--color-forest-soft);
      color: var(--color-forest-deep);
    }

    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--border-default);
      background: var(--surface-panel);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 900px;
      font-size: var(--text-sm);
    }

    th,
    td {
      border-bottom: 1px solid var(--border-default);
      padding: var(--space-4);
      text-align: left;
      vertical-align: top;
    }

    th {
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      color: var(--text-secondary);
      letter-spacing: var(--tracking-wide);
      text-transform: uppercase;
      background: var(--surface-subtle);
      font-weight: 700;
    }

    td {
      color: var(--text-primary);
    }

    td.numeric {
      text-align: right;
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }

    tbody tr:last-child td {
      border-bottom: 0;
    }

    tbody tr[hidden] {
      display: none;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: var(--space-2);
      border: 1px solid var(--color-forest);
      background: var(--color-forest-soft);
      color: var(--color-forest-deep);
      font-family: var(--font-mono);
      font-size: var(--text-2xs);
      font-weight: 700;
      letter-spacing: var(--tracking-wide);
      text-transform: uppercase;
      padding: var(--space-2) var(--space-3);
    }

    .badge.signal {
      border-color: var(--color-signal);
      background: var(--color-signal-soft);
      color: var(--color-signal-deep);
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--color-forest);
      display: inline-block;
    }

    .dot.signal {
      background: var(--color-signal);
    }

    .telemetry-grid {
      display: grid;
      gap: var(--space-4);
    }

    .platform-card {
      border: 1px solid var(--border-default);
      background: var(--surface-panel);
      padding: var(--space-5);
      display: grid;
      gap: var(--space-3);
    }

    .platform-card h3 {
      margin: 0;
      font-size: var(--text-lg);
      line-height: var(--line-heading);
      letter-spacing: var(--tracking-tight);
    }

    .platform-meta {
      display: grid;
      gap: var(--space-2);
      color: var(--text-secondary);
      font-size: var(--text-sm);
    }

    .platform-telemetry {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: var(--space-3);
    }

    .schematic {
      border: 1px solid var(--border-default);
      background: var(--surface-subtle);
      padding: var(--space-5);
    }

    .schematic svg {
      width: 100%;
      height: auto;
      display: block;
      background: var(--surface-panel);
      border: 1px solid var(--border-default);
    }

    .schematic-caption {
      margin: var(--space-4) 0 0;
      color: var(--text-secondary);
      font-size: var(--text-sm);
      max-width: var(--reading-max);
    }

    .faq-list {
      display: grid;
      gap: var(--space-3);
      border: 1px solid var(--border-default);
      background: var(--surface-panel);
    }

    details {
      border-bottom: 1px solid var(--border-default);
    }

    details:last-child {
      border-bottom: 0;
    }

    summary {
      cursor: pointer;
      padding: var(--space-4);
      font-weight: 700;
      color: var(--text-primary);
      list-style: none;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--space-3);
    }

    summary::-webkit-details-marker {
      display: none;
    }

    summary::after {
      content: "+";
      font-family: var(--font-mono);
      color: var(--color-forest-deep);
      font-size: var(--text-md);
      line-height: 1;
    }

    details[open] summary::after {
      content: "−";
    }

    .faq-answer {
      padding: 0 var(--space-4) var(--space-4);
      color: var(--text-secondary);
      max-width: var(--reading-max);
    }

    .inquiry-panel {
      border: 1px solid var(--border-default);
      background: var(--surface-panel);
      padding: var(--space-5);
    }

    .inquiry-grid {
      display: grid;
      gap: var(--space-4);
    }

    @media (min-width: 960px) {
      .inquiry-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .inquiry-grid .full {
        grid-column: 1 / -1;
      }
    }

    footer.site-footer {
      border-top: 1px solid var(--border-default);
      background: var(--surface-page);
      padding-block: var(--space-6);
      color: var(--text-secondary);
      font-size: var(--text-sm);
    }

    .footer-grid {
      display: grid;
      gap: var(--space-3);
    }

    @media (min-width: 960px) {
      .footer-grid {
        grid-template-columns: minmax(0, 1fr) minmax(0, auto);
      }
    }

    .mono {
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
    }

    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }

    .visually-hidden-live {
      min-height: 1.5rem;
      color: var(--text-secondary);
      font-family: var(--font-mono);
      font-size: var(--text-xs);
    }
  </style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>

  <header class="site-header">
    <div class="container header-grid">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">A</div>
        <div class="brand-text">
          <span class="brand-name">AETHERIA BIO-ROBOTICS</span>
          <span class="brand-sub">Autonomous Environmental &amp; Precision-Agriculture Drone Platform</span>
        </div>
      </div>
      <nav class="site-nav" aria-label="Primary navigation">
        <a href="#mission-planner">Mission Planner</a>
        <a href="#platforms">Platforms</a>
        <a href="#comparison">Comparison</a>
        <a href="#schematic">Schematic</a>
        <a href="#faq">FAQ</a>
        <a href="#deployment">Deployment</a>
      </nav>
    </div>
  </header>

  <main id="main" class="container">
    <section class="hero" aria-labelledby="hero-heading">
      <div>
        <p class="eyebrow">Aetheria Bio-Robotics // Mission Operations</p>
        <h1 id="hero-heading">Autonomous coverage for environmental and precision-agriculture missions.</h1>
        <p class="lead">
          AETHERIA BIO-ROBOTICS coordinates multispectral, LiDAR, and soil-probe drone fleets with RTK navigation,
          battery-swap planning, waypoint generation, and telemetry filtering for field-ready deployment.
        </p>
        <div class="hero-actions">
          <a class="button" href="#mission-planner">Open Mission Planner</a>
          <a class="button secondary" href="#deployment">Request Fleet Deployment</a>
        </div>
      </div>

      <aside class="hero-panel" aria-label="Platform summary">
        <p class="panel-title">Fleet Telemetry Summary</p>
        <div class="metric-grid">
          <div class="metric">
            <span class="metric-label">Platforms</span>
            <span class="metric-value">3</span>
            <span class="metric-unit">active classes</span>
          </div>
          <div class="metric">
            <span class="metric-label">Navigation</span>
            <span class="metric-value">RTK</span>
            <span class="metric-unit">centimeter-class</span>
          </div>
          <div class="metric">
            <span class="metric-label">Planner</span>
            <span class="metric-value">Live</span>
            <span class="metric-unit">coverage model</span>
          </div>
          <div class="metric">
            <span class="metric-label">Security</span>
            <span class="metric-value">CSP</span>
            <span class="metric-unit">standalone page</span>
          </div>
        </div>
      </aside>
    </section>

    <section id="mission-planner" aria-labelledby="planner-heading">
      <div class="section-head">
        <h2 id="planner-heading">Live Flight-Path Coverage Calculator</h2>
        <p class="section-subtitle">
          Calculate path length, coverage passes, waypoint count, battery endurance, and battery swaps from field area,
          swath width, cruise speed, and battery capacity.
        </p>
      </div>

      <div class="grid-2">
        <form class="panel" data-planner-form aria-labelledby="planner-inputs-heading">
          <h3 id="planner-inputs-heading" class="panel-title">Mission Inputs</h3>

          <div class="form-grid">
            <div class="field">
              <label for="platform-select">Platform profile</label>
              <select id="platform-select" data-platform-select name="platform">
                <option value="x4">AETHER-X4 Multispectral</option>
                <option value="h8">AETHER-H8 Heavy Lidar</option>
                <option value="s2">AETHER-S2 Soil Probe</option>
              </select>
              <p class="help">Selecting a platform updates default swath, cruise speed, and power draw.</p>
            </div>

            <div class="field">
              <label for="field-ha">Field area in hectares</label>
              <input id="field-ha" name="field-ha" type="number" step="0.01" min="0.01" max="100000" value="12" inputmode="decimal" />
              <p class="help">Total mission coverage area.</p>
            </div>

            <div class="field">
              <label for="swath-m">Swath width in meters</label>
              <input id="swath-m" name="swath-m" type="number" step="0.1" min="1" max="500" value="112" inputmode="decimal" />
              <p class="help">Effective sensor footprint width before overlap adjustment.</p>
            </div>

            <div class="field">
              <label for="cruise-speed">Cruise speed in meters per second</label>
              <input id="cruise-speed" name="cruise-speed" type="number" step="0.1" min="1" max="40" value="14" inputmode="decimal" />
              <p class="help">Average mission speed along coverage lines.</p>
            </div>

            <div class="field">
              <label for="battery-wh">Battery capacity in watt-hours</label>
              <input id="battery-wh" name="battery-wh" type="number" step="1" min="1" max="20000" value="900" inputmode="decimal" />
              <p class="help">Total usable energy per battery pack.</p>
            </div>

            <div class="field">
              <label for="power-w">Average power draw in watts</label>
              <input id="power-w" name="power-w" type="number" step="1" min="50" max="800" value="180" inputmode="decimal" />
              <p class="help">Used to convert battery watt-hours into flight endurance.</p>
            </div>

            <div class="field">
              <label for="overlap-pct">Swath overlap percentage</label>
              <input id="overlap-pct" name="overlap-pct" type="number" step="1" min="0" max="60" value="10" inputmode="decimal" />
              <p class="help">Higher overlap increases path length for seamless mosaics.</p>
            </div>

            <p class="status" data-planner-status role="status" aria-live="polite">Coverage model active. Inputs updated live.</p>
          </div>
        </form>

        <aside class="panel" aria-labelledby="planner-output-heading">
          <h3 id="planner-output-heading" class="panel-title">Coverage Outputs</h3>
          <div class="output-grid">
            <div class="output">
              <span class="output-label">Area m²</span>
              <span class="output-value" data-output="area-m2">120000</span>
            </div>
            <div class="output">
              <span class="output-label">Effective swath</span>
              <span class="output-value" data-output="effective-swath">100.8</span>
            </div>
            <div class="output">
              <span class="output-label">Path length m</span>
              <span class="output-value" data-output="path-length">1190.5</span>
            </div>
            <div class="output">
              <span class="output-label">Coverage passes</span>
              <span class="output-value" data-output="coverage-passes">11</span>
            </div>
            <div class="output">
              <span class="output-label">Waypoint count</span>
              <span class="output-value" data-output="waypoint-count">37</span>
            </div>
            <div class="output">
              <span class="output-label">Mission time</span>
              <span class="output-value" data-output="mission-time">0h 01m 33s</span>
            </div>
            <div class="output">
              <span class="output-label">Endurance</span>
              <span class="output-value" data-output="endurance">5h 00m 00s</span>
            </div>
            <div class="output">
              <span class="output-label">Battery swaps</span>
              <span class="output-value" data-output="battery-swaps">1</span>
            </div>
          </div>

          <p class="status" aria-live="polite" style="margin-top: var(--space-4);">
            Battery swap count is the minimum number of battery packs required to complete the modeled mission.
          </p>
        </aside>
      </div>
    </section>

    <section id="platforms" aria-labelledby="platforms-heading">
      <div class="section-head">
        <h2 id="platforms-heading">Interactive Telemetry Filter</h2>
        <p class="section-subtitle">
          Filter the three AETHERIA drone platforms by mission class. Filtered rows remain available in the DOM for
          assistive technology and table semantics.
        </p>
      </div>

      <div class="filter-bar" role="group" aria-label="Platform filter">
        <button type="button" class="filter-button" data-filter-button="all" aria-pressed="true">All Platforms</button>
        <button type="button" class="filter-button" data-filter-button="x4" aria-pressed="false">Multispectral</button>
        <button type="button" class="filter-button" data-filter-button="h8" aria-pressed="false">Heavy Lidar</button>
        <button type="button" class="filter-button" data-filter-button="s2" aria-pressed="false">Soil Probe</button>
      </div>

      <p class="visually-hidden-live" data-telemetry-summary aria-live="polite">Telemetry filter: all platforms.</p>

      <div class="telemetry-grid">
        <article class="platform-card" data-platform-card="x4">
          <span class="badge"><span class="dot" aria-hidden="true"></span>Multispectral Active</span>
          <h3 data-platform-name>AETHER-X4 Multispectral</h3>
          <div class="platform-meta">
            <p><strong>Payload:</strong> <span data-platform-payload>12-band multispectral + RTK gimbal</span></p>
            <p><strong>Deployment:</strong> Small-field crop scouting</p>
            <p><strong>Coverage profile:</strong> RGB / NIR / RedEdge / Vegetation indices</p>
          </div>
          <div class="platform-telemetry">
            <div class="metric">
              <span class="metric-label">Endurance</span>
              <span class="metric-value" data-platform-endurance>38 min</span>
            </div>
            <div class="metric">
              <span class="metric-label">Power draw</span>
              <span class="metric-value" data-platform-power>180 W</span>
            </div>
          </div>
        </article>

        <article class="platform-card" data-platform-card="h8">
          <span class="badge signal"><span class="dot signal" aria-hidden="true"></span>Heavy Lidar Active</span>
          <h3 data-platform-name>AETHER-H8 Heavy Lidar</h3>
          <div class="platform-meta">
            <p><strong>Payload:</strong> <span data-platform-payload>128-channel LiDAR + thermal payload</span></p>
            <p><strong>Deployment:</strong> Terrain mapping / biomass volume</p>
            <p><strong>Coverage profile:</strong> LiDAR point cloud / thermal / canopy height</p>
          </div>
          <div class="platform-telemetry">
            <div class="metric">
              <span class="metric-label">Endurance</span>
              <span class="metric-value" data-platform-endurance>26 min</span>
            </div>
            <div class="metric">
              <span class="metric-label">Power draw</span>
              <span class="metric-value" data-platform-power>320 W</span>
            </div>
          </div>
        </article>

        <article class="platform-card" data-platform-card="s2">
          <span class="badge"><span class="dot" aria-hidden="true"></span>Soil Probe Active</span>
          <h3 data-platform-name>AETHER-S2 Soil Probe</h3>
          <div class="platform-meta">
            <p><strong>Payload:</strong> <span data-platform-payload>Electrical conductivity + moisture probe</span></p>
            <p><strong>Deployment:</strong> Soil sampling / moisture mapping</p>
            <p><strong>Coverage profile:</strong> Conductivity / moisture / compaction</p>
          </div>
          <div class="platform-telemetry">
            <div class="metric">
              <span class="metric-label">Endurance</span>
              <span class="metric-value" data-platform-endurance>42 min</span>
            </div>
            <div class="metric">
              <span class="metric-label">Power draw</span>
              <span class="metric-value" data-platform-power>150 W</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section id="comparison" aria-labelledby="comparison-heading">
      <div class="section-head">
        <h2 id="comparison-heading">3-Drone Comparison Table</h2>
        <p class="section-subtitle">
          Platform specifications for coverage planning, payload selection, environmental resilience, and field deployment.
        </p>
      </div>

      <div class="table-wrap" role="region" aria-label="Drone comparison table" tabindex="0">
        <table>
          <caption class="sr-only">AETHERIA drone platform comparison</caption>
          <thead>
            <tr>
              <th scope="col">Platform</th>
              <th scope="col">Payload</th>
              <th scope="col">Swath m</th>
              <th scope="col">Cruise m/s</th>
              <th scope="col">Endurance min</th>
              <th scope="col">Power W</th>
              <th scope="col">RTK accuracy</th>
              <th scope="col">IP rating</th>
              <th scope="col">Deployment class</th>
            </tr>
          </thead>
          <tbody>
            <tr data-platform-row="x4">
              <th scope="row">AETHER-X4 Multispectral</th>
              <td>12-band multispectral + RTK gimbal</td>
              <td class="numeric">112</td>
              <td class="numeric">14</td>
              <td class="numeric">38</td>
              <td class="numeric">180</td>
              <td>±1.2 cm RTK</td>
              <td>IP67</td>
              <td>Small-field crop scouting</td>
            </tr>
            <tr data-platform-row="h8">
              <th scope="row">AETHER-H8 Heavy Lidar</th>
              <td>128-channel LiDAR + thermal payload</td>
              <td class="numeric">180</td>
              <td class="numeric">11</td>
              <td class="numeric">26</td>
              <td class="numeric">320</td>
              <td>±2.8 cm RTK</td>
              <td>IP68</td>
              <td>Terrain mapping / biomass volume</td>
            </tr>
            <tr data-platform-row="s2">
              <th scope="row">AETHER-S2 Soil Probe</th>
              <td>Electrical conductivity + moisture probe</td>
              <td class="numeric">72</td>
              <td class="numeric">9</td>
              <td class="numeric">42</td>
              <td class="numeric">150</td>
              <td>±3.5 cm RTK</td>
              <td>IP66</td>
              <td>Soil sampling / moisture mapping</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section id="schematic" aria-labelledby="schematic-heading">
      <div class="section-head">
        <h2 id="schematic-heading">Multispectral Sensor Schematic</h2>
        <p class="section-subtitle">
          Inline SVG schematic showing gimbal, multispectral sensor array, RTK antenna, telemetry link, and battery module.
        </p>
      </div>

      <div class="schematic">
        <svg viewBox="0 0 900 420" role="img" aria-labelledby="svg-title svg-desc">
          <title id="svg-title">AETHERIA X4 multispectral sensor schematic</title>
          <desc id="svg-desc">
            A Swiss-grid drone schematic showing central body, gimbal, multispectral sensor array, RTK antenna,
            telemetry link indicator, battery module, and coverage swath projection.
          </desc>

          <style>
            .svg-bg { fill: var(--color-bone); }
            .svg-line { stroke: var(--color-ink); stroke-width: 2; fill: none; }
            .svg-accent { stroke: var(--color-forest); stroke-width: 3; fill: none; }
            .svg-signal { stroke: var(--color-signal); stroke-width: 3; fill: none; }
            .svg-text { fill: var(--color-ink); font-family: var(--font-mono); font-size: 16px; }
            .svg-muted { fill: var(--color-ink-muted); font-family: var(--font-mono); font-size: 14px; }
            .svg-panel { fill: var(--color-bone-soft); stroke: var(--color-bone-strong); stroke-width: 1; }
            .svg-chip { fill: var(--color-forest-soft); stroke: var(--color-forest); stroke-width: 2; }
          </style>

          <rect x="0" y="0" width="900" height="420" class="svg-bg" />

          <line x1="0" y1="40" x2="900" y2="40" class="svg-line" />
          <line x1="0" y1="380" x2="900" y2="380" class="svg-line" />
          <line x1="40" y1="0" x2="40" y2="420" class="svg-line" />
          <line x1="860" y1="0" x2="860" y2="420" class="svg-line" />

          <rect x="350" y="150" width="200" height="80" class="svg-panel" />
          <rect x="375" y="165" width="150" height="50" class="svg-chip" />
          <text x="390" y="195" class="svg-text">X4 CORE</text>

          <line x1="350" y1="190" x2="220" y2="190" class="svg-line" />
          <line x1="550" y1="190" x2="680" y2="190" class="svg-line" />

          <circle cx="180" cy="190" r="34" class="svg-line" />
          <circle cx="180" cy="190" r="10" class="svg-accent" />

          <circle cx="720" cy="190" r="34" class="svg-line" />
          <circle cx="720" cy="190" r="10" class="svg-accent" />

          <line x1="180" y1="156" x2="180" y2="86" class="svg-line" />
          <line x1="720" y1="156" x2="720" y2="86" class="svg-line" />

          <rect x="140" y="56" width="80" height="30" class="svg-panel" />
          <rect x="680" y="56" width="80" height="30" class="svg-panel" />

          <line x1="450" y1="150" x2="450" y2="90" class="svg-line" />
          <rect x="405" y="68" width="90" height="22" class="svg-panel" />
          <text x="415" y="84" class="svg-muted">RTK GNSS</text>

          <line x1="450" y1="230" x2="450" y2="292" class="svg-accent" />
          <rect x="395" y="292" width="110" height="44" class="svg-chip" />
          <text x="410" y="318" class="svg-text">GIMBAL</text>

          <rect x="300" y="336" width="300" height="28" class="svg-panel" />
          <text x="315" y="355" class="svg-muted">MULTISPECTRAL SENSOR ARRAY</text>

          <line x1="340" y1="364" x2="340" y2="400" class="svg-signal" stroke-dasharray="6 6" />
          <line x1="560" y1="364" x2="