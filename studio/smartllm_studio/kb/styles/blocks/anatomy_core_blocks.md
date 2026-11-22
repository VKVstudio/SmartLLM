# Core Conversion & Grid Blocks Anatomy (`9` Primary Blocks)

Format: `variant`: Desktop (`>=1280px`, 12-col) | Tablet (`768–1279px`, 8-col) | Mobile (`360–767px`, 4-col). Inherit all 9 invariants from `anatomy_19_blocks.md`.

1. **`hero`** *(max 4 text elements, H1<=8w EN / <=6w RU, sub<=20w, 1 canonical CTA intent; NEVER hide behind `opacity: 0`)*
   - `asymmetric_split`: D `7+5` split (copy left, `16:9`/`4:3` figure right) | T `5+3` or `8+8` | M `1-col` copy then visual (`16:9`)
   - `editorial_poster`: D `12-col` monumental H1 + inline subtext/CTA + `16:9` plate below | T `8-col` stacked | M `1-col` compact display H1 + CTA + visual
   - `bento_showcase`: D `7-col` `--surface` copy tile + `5-col` (`1:1` or `4:5`) visual tile | T `5+3` tiles | M `1-col` stacked (`16px` gap)
   - `fullbleed_scrim`: D `16:9` right-anchored visual + directional `90deg` scrim + `7-col` copy | T `4:3` + bottom scrim | M stacked `16:9` top + solid `--bg` copy below
   - `command_stage`: D `6+6` split (lead + `<kbd>` CTA left; elevated hardware stage + `32px` mono spec bar right) | T `8+8` | M `1-col`

2. **`manifesto`** *(statement<=24w, positioning<=45w, max 3 extra lines)*
   - `monument_statement`: D `10-col` left oversized quote + `7-col` positioning lead | T `8-col` left-aligned | M `1-col`
   - `ruled_thesis`: D `5+7` split w/ `1px` vertical border | T `4+4` split | M `1-col` w/ horizontal `1px` rule
   - `editorial_band`: D full-width `--surface-elevated` band (`8-col` offset) | T `8-col` band | M `1-col` `20px` pad

3. **`values`** *(3–4 items, title<=4w, body<=28w)*
   - `numbered_pillars`: D `3/4-col` open-sided `01..04` columns (`1px` vertical or `4px` top rules) | T `2×2` grid | M `1-col` w/ top rules
   - `tactile_cards`: D `3-col` (`N=3`) or `6+6` (`N=4`) surface cards | T `4+4` grid | M `1-col` vertical cards
   - `editorial_rows`: D `4+8` full-width `1px` border-top rows | T `3+5` rows | M `1-col` stacked rows
   - `accent_bento`: D `N=1..6` zero-empty-cell bento w/ `--surface-elevated` anchor | T `4+4` grid | M `1-col`

4. **`priorities`** *(3–6 items, <=8w/item)*
   - `indexed_matrix`: D `2-col` (`4`) or `3-col` (`3/6`) hairline cells w/ `01..06` mono prefix | T `2-col` | M `2-col` (`<=4w`) or `1-col`
   - `horizontal_ribbon`: D single-row pill rail (or max 1 pauseable marquee if canon allows) | T wrapped pills | M `2-col` pill grid
   - `ledger_checklist`: D `2-col` border-bottom declaration rows w/ accent marker | T `2-col` | M `1-col` (`>=44px` rows)

5. **`features`** *(3–6 capabilities, title<=6w, detail<=26w; NEVER mix pricing tiers)*
   - `bento_asymmetric`: D `N=1..6` bento grid w/ `>=1` `--surface-elevated` tile | T `4+4` (odd item spans `8`) | M `1-col`
   - `editorial_rows`: D `1+4+7` border-top rows (`Index | H3 | Detail`) | T `3+5` rows | M `1-col`
   - `hairline_matrix`: D border-collapsed `1px` CSS grid (`0` shadows) | T `2-col` hairline grid | M `1-col`
   - `sticky_narrative`: D `4-col` sticky H2 (`top: 96px`) + `8-col` card stack | T static header + `2-col` | M `1-col`
   - `tactile_cards`: D `4+4+4` (`3/6`) or `6+6` (`2/4`) surface cards | T `4+4` | M `1-col`

6. **`stats`** *(3–4 metrics, `tabular-nums`, value<=10 chars, label<=8w)*
   - `kpi_band`: D frameless `3/4-col` strip w/ vertical `1px` dividers | T `2×2` ruled grid | M `repeat(auto-fit, minmax(min(100%, 165px), 1fr))`
   - `metric_cards`: D `3/4-col` elevated cards w/ display `stat-value` | T `2×2` cards | M `2-col` compact or `1-col`
   - `asymmetric_spotlight`: D `6-col` hero stat (`--surface-elevated`) + `6-col` stacked stats | T `8-col` + `2-col` | M `1-col`
   - `ledger_strip`: D compact `1px` bordered telemetry bar w/ mono labels | T `2×2` cells | M `2×2` bordered cells

7. **`pricing`** *(2–4 tiers, <=5 scope bullets, `tabular-nums`, single-line `white-space: nowrap` CTA)*
   - `tier_cards_featured`: D `3-col` (`2/4=6+6`); featured tier `--surface-elevated` + `2px solid var(--accent)` | T `2-col` | M `1-col`
   - `spec_comparison_table`: D semantic `<table scope=col|row>` | T sticky col 1 + `tabindex="0" role="region"` | M collapses `<768px` into stacked `data-label` tier cards
   - `split_value_anchor`: D `4-col` sticky guarantee/terms + `8-col` horizontal tier strips | T `8-col` + strips | M `1-col` cards
   - `modular_toggle_cards`: D `3/2-col` cards (large price top, divider, bullets, full CTA) | T `2-col` | M `1-col`

8. **`cta`** *(headline<=12w, subline<=18w, 1 canonical button)*
   - `split_action_band`: D `8+4` elevated band (H2+subline left, single-line CTA right) | T flex wrap | M `1-col` + `100%` `48px` CTA
   - `centered_monolith`: D framed `--surface-elevated` box + `2px` accent border | T `8-col` box | M `1-col` + `100%` CTA
   - `inline_command_bar`: D compact single-row bordered bar (mono status + CTA) | T flex wrap | M `1-col` + `100%` CTA

9. **`footer`** *(<=4 columns, legal link + copyright mandatory)*
   - `multi_column_grid`: D `5+3+4` (`Brand+Tagline | Nav | Contacts`) + bottom legal/copyright bar | T `2-col` + bottom | M `1-col`
   - `compact_colophon`: D single-row horizontal flex bar | T 2-row clean bar | M `1-col` vertical list
   - `editorial_monogram`: D `12-col` oversized wordmark top + `3-col` utility directory below | T wordmark + `2-col` | M `1-col`
