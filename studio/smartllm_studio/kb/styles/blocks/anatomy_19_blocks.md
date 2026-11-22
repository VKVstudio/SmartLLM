# 19-Block Architecture Router & Global Structural Invariants

> Load this hub alongside `anatomy_core_blocks.md` (primary conversion/grid blocks) and `anatomy_supporting_blocks.md` (proof/directory/editorial blocks). Deterministic per-canon variant selection lives in `styles/blocks/_matrix.json`.

## Global Page Invariants (All 9 Skeptic-Hardened Rules)
1. **Desktop Nav (`>=1024px`):** Single horizontal line, `height <= 72px`, `<= 6` links (`white-space: nowrap`). Below `768px`, collapse links into accessible `<button aria-expanded="false" aria-controls="mobile-nav">` (header `<= 64px`).
2. **Hero Fold & 4-Element Cap:** Fits `min(86svh, 840px)`, `padding-top <= 96px`. Strict **4-element cap**: `[optional eyebrow (<=4 words), H1 (<=8w EN / <=6w RU, <=2 lines), subhead (<=20w, <=4 lines), cta_row (1 primary + <=1 secondary)]`. **BAN `#node-calc-output` debug status, trust logos, and pricing teasers inside hero.**
3. **Eyebrow & Anti-Repetition Cap:** Max `ceil(sections / 3)` eyebrows (`hero` counts; `>= 2` sections gap). Adjacent blocks NEVER share `layout_family`; max `2` consecutive `split` blocks; max `1` `marquee` page-wide.
4. **Zero-Empty-Cell Bento:** `data-count="1..6"` sums to `12` cols/row on desktop (`12`; `7+5`; `7-r2+5+5`; `7+5/5+7`; `7+5/4+4+4`; `6+3+3/3+3+6`), with `>= 1` `--surface-elevated` tile.
5. **Hero `fullbleed_scrim` Contrast:** Desktop directional scrim `linear-gradient(90deg, color-mix(in oklab, var(--bg) 92%, transparent) 0%, color-mix(in oklab, var(--bg) 82%, transparent) 52%, color-mix(in oklab, var(--bg) 28%, transparent) 100%)`. **Mobile (`<768px`):** stack `16:9` figure above solid `var(--bg)` copy OR enforce `>= 88%` vertical scrim (`180deg`).
6. **Team `3:4` Headroom:** Z-Image `576×768`; CSS `.team-photo { aspect-ratio: 3/4; object-fit: cover; object-position: 50% 15%; }`.
7. **Accessible Carousels & Tables:** `horizontal_filmstrip` and `horizontal_carousel` MUST expose `tabindex="0" role="region" aria-roledescription="carousel"` + visible `44×44px` Prev/Next `<button type="button">` controls (WCAG 2.1.1 & 2.5.7). `spec_comparison_table` stacks into `data-label` cards `<768px` (or uses `tabindex="0" role="region"` + sticky `th[scope="row"]`).
8. **Pauseable Marquee (SC 2.2.2):** `.marquee:hover .marquee-track, .marquee:focus-within .marquee-track { animation-play-state: paused; }` + explicit Pause/Play button.
9. **Forms & FAQ Accessibility:** Visible `<label>` ABOVE input; `font-size >= 16px` mobile; `48px` mobile targets; `.hp-trap` honeypot; `<p class="form-status" role="status" aria-live="polite">` (NOT on disabled submit button); native `<details class="faq-item"><summary>` preferred for FAQ accordions.
