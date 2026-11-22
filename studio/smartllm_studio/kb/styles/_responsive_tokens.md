# Shared Responsive, Grid, Form & Fontsource Canon (`_responsive_tokens.md`)

## 1. Breakpoints, Viewports & Container Queries
- **Mobile (`360–767px`):** `4` cols, `100%` fluid, `16–20px` pad, `12–16px` gutter. **Tablet (`768–1279px`):** `8` cols, `100%`, `24–32px` pad, `16–22px` gutter. **Desktop (`>=1280px`):** `12` cols, `max-width: 1200–1360px`, `32–56px` pad, `20–32px` gutter.
- **Viewports (Baseline):** Hero uses `min-height: min(86svh, 840px)` (no mobile URL-bar jump); drawers/modals use `100dvh; overscroll-behavior: contain;`. **BAN raw `100vh`.**
- **Container Queries & Overflow:** `container-type: inline-size;` on `.hero-shell, .section-block` (`@container (max-width: 760px)` collapses grids). Use `body { overflow-x: clip; }` (preserves `position: sticky`) + `min-width: 0` on grid/flex items.

## 2. WCAG 2.2 + Apple HIG + Material 3 Ergonomics
- **SC 2.4.11/2.4.12 Focus Not Obscured:** `html { scroll-padding-top: 92px; }` + `scroll-margin-top: 96px` on focusables. Sticky header `<= 72px` desktop, `<= 64px` mobile (collapse links into `<button aria-expanded>` drawer `<768px`).
- **SC 2.4.13 Focus Ring:** `:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }` (`3px` on brutalist/AAA, outside borders).
- **SC 2.5.8 Touch Targets:** Mobile `<768px` CTAs/inputs/toggles **`min-height: 48px`** (`44px` floor, `>= 8px` gap). Desktop `40–44px`; footer/breadcrumb links `padding-block: 0.4rem` (`>=32px`).
- **SC 1.4.3/1.4.6/1.4.11 Contrast:** `text/bg & surface >= 7.0:1`, `muted >= 4.5:1`, `accent_ink/accent >= 4.5:1`, **`--border-control/surface >= 3.0:1`** across all 40 polarities (`14:1 / 7:1` on `19_calm`).
- **SC 2.2.2 & Glass/Motion Safety:** Pause marquees on `:hover, :focus-within` + Pause/Play button; `@media (prefers-reduced-motion: reduce)` settles immediately. Translucent glass (`08_liquid_glass`) requires dark `alpha >= 0.72` + triple fallback (`prefers-reduced-transparency`, `@supports`, `[data-solid-ui]`). Put ambient gradients on fixed `body::before` — **NEVER `body { background-attachment: fixed; }`** (iOS jank).

## 3. Forms, CTAs & Russian Cyrillic Rules
- Mobile inputs `font-size >= 16px` (no iOS auto-zoom); `<label>` ABOVE input (`display: block; margin-bottom: 6px;`), `.hp-trap` honeypot, `<p class="form-status" role="status" aria-live="polite">`. `.btn { white-space: nowrap; }`. Shape Consistency Lock (`radius_card` -> `radius_button` -> `radius_input` -> `radius_badge`).
- **Cyrillic Compensation (`lang="ru"`):** Apply `overflow-wrap: break-word; hyphens: auto; text-wrap: balance;` on `h1..h3, .manifesto-statement, .stat-value`; clamp wide display H1 down to `24–28px` at `360px`; `.stat-band` `<480px` uses `repeat(auto-fit, minmax(min(100%, 165px), 1fr))`.

## 4. Fontsource Packaging Traps (4 Skeptic-Verified Rules)
1. **Variable Suffix:** `@fontsource-variable/*` `index.css` registers `font-family: '<Name> Variable'` — declare `'<Name> Variable', '<Name>'` in CSS tokens.
2. **Italics & Axes:** `index.css` omits italics & secondary axes — explicitly bundle `wght-italic.css` / `wdth.css` / `opsz.css` as needed (italic display lines need `lh >= 1.1; padding-bottom: 0.08em;` for Cyrillic descenders).
3. **Static-Only Fonts (`@fontsource/*`):** `ibm-plex-mono` and `pt-mono` have NO variable pkg — bundle static weights (`400/500/600`).
4. **Payload Budget:** Subset `cyrillic`+`latin` `.woff2`; avoid `roboto-flex/full.css` (`506 KB`) in favor of `tektur` (`~10 KB`) or `geologica` (`~22 KB`).

```json
{"breakpoints_px":{"mobile":[360,767],"tablet":[768,1279],"desktop":[1280,1920]},"grid_cols":{"mobile":4,"tablet":8,"desktop":12},"container_max_px":1312,"viewport_hero":"min(86svh, 840px)","viewport_drawer":"100dvh","scroll_padding_top_px":92,"touch_target_px":{"wcag":24,"desktop":40,"mobile_floor":44,"mobile_rec":48,"gap":8},"input_min_h":{"desktop":44,"tablet":46,"mobile":48,"font_min_px":16}}
```
