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