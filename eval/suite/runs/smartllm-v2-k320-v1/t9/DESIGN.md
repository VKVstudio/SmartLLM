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