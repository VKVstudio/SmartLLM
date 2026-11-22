# Supporting Proof, Directory & Editorial Blocks Anatomy (`10` Blocks)

Format: `variant`: Desktop (`>=1280px`, 12-col) | Tablet (`768–1279px`, 8-col) | Mobile (`360–767px`, 4-col). Inherit all 9 invariants from `anatomy_19_blocks.md`.

10. **`locations`** *(1–4 offices: city, street address, hours)*
    - `city_cards`: D `12`/`6+6`/`4+4+4`/`6+6×2` | T `4+4` grid | M `1-col` stack
    - `directory_ledger`: D `3+6+3` hairline rows (`City | Address | Hours`) | T stacked 2-line rows | M `1-col` grouped rows
    - `split_hub_list`: D `5-col` HQ (`--surface-elevated`) + `7-col` satellite rows | T HQ top + `2-col` | M `1-col`

11. **`about`** *(lead<=55w, <=3 milestones, <=2 verified facts)*
    - `story_metrics_split`: D `7-col` story/method left + `5-col` stacked verified facts right | T `8-col` + `2-col` | M `1-col`
    - `monograph_column`: D `8-col` (`68ch`) narrative + `12-col` hairline bottom fact strip | T `8-col` + `2-col` | M `1-col`
    - `milestone_chronicle`: D `12-col` lead + `3/4-col` dated horizontal track | T `2-col` milestones | M `1-col` left-ruled list
    - `architectural_grid`: D `5-col` thesis + `7-col` `2×2` fact matrix | T `8-col` + `4+4` | M `1-col`

12. **`gallery`** *(2–6 figures, caption<=120 chars, explicit IHDR `width`/`height`)*
    - `bento_mosaic`: D `7+5` (`2`), `7-r2+5+5` (`3`), `7+5/5+7` (`4`) | T `4+4` | M `1-col` full-width figures
    - `editorial_grid`: D `2-col` (`2/4`) or `3-col` (`3/6`) uniform aspect | T `2-col` | M `1-col`
    - `horizontal_filmstrip`: D `scroll-snap` (`420px`) + `tabindex="0" role="region"` + `44×44px` Prev/Next buttons | T `340px` + buttons | M `84vw` + peek + buttons
    - `cinematic_spotlight`: D `12-col` `16:9` lead top + `2/3-col` below | T `8-col` + `2-col` | M `1-col`
    - `collage_stagger`: D `6+6` w/ `48px` right-col top stagger (zero text overlap) | T even `2-col` | M `1-col`

13. **`testimonials`** *(2–4 quotes, <=3 lines, attribution: Name + Role + Company)*
    - `editorial_pullquotes`: D `10-col` pull-quotes w/ `3px–6px` left `--accent` bar (`«»`/`“”`) | T `8-col` | M `1-col`
    - `verified_cards`: D `3-col` (`3`) or `2×2` (`4`) cards w/ outcome badge | T `2-col` | M `1-col`
    - `featured_spotlight`: D `7-col` hero quote (`--surface-elevated`) + `5-col` stacked 2 compact quotes | T `8-col` + `2-col` | M `1-col`
    - `horizontal_carousel`: D `scroll-snap` (`380px`) + `tabindex="0" role="region"` + `44×44px` Prev/Next buttons | T `320px` + buttons | M `86vw` + buttons

14. **`process`** *(3–5 steps, title<=5w, detail<=24w)*
    - `numbered_steps_grid`: D `4-col` (`4`) or `3-col` (`3`) cards w/ `01..04` index | T `2×2` | M `1-col`
    - `vertical_timeline`: D `4-col` sticky H2 + `8-col` ruled `<ol>` (`square` nodes in `07_avant_garde_poster`) | T `8-col` + `<ol>` | M `1-col` `<ol>`
    - `horizontal_stepper`: D connected horizontal node track | T `2×2` badges | M `1-col` vertical rail
    - `ledger_rows`: D `1+4+7` hairline rows (`01 | Step | Deliverable`) | T `1+3+4` | M `1-col`

15. **`team`** *(2–4 canonical specialists, `3:4` headroom photo, `object-position: 50% 15%`, 0 URLs)*
    - `portrait_grid_3x4`: D `3/4-col` cards w/ `3:4` photo | T `2-col` | M `1-col` (or `2-col` `>=420px`)
    - `editorial_directory`: D `6+6` horizontal cards (`140px` `3:4` left + bio right) | T `2/1-col` | M `104px` photo left
    - `spotlight_leadership`: D `4+8` founder top + `3-col` below | T `3+5` + `2-col` | M `1-col`
    - `minimal_roster`: D frameless `3/4-col` `3:4` portraits + bottom hairline rule | T `2-col` | M `1-col`

16. **`blog`** *(3–4 posts, title<=12w, excerpt<=24w)*
    - `featured_plus_grid`: D `12-col` split lead (`N=4`) + `3-col` | T `8-col` + `2-col` | M `1-col`
    - `editorial_index`: D `2+5+5` border-top rows (`Meta | H3 | Excerpt`) | T stacked meta + `2-col` | M `1-col`
    - `card_deck`: D `3-col` (`3`) or `2×2` (`4`) article cards | T `2-col` | M `1-col`

17. **`faq`** *(2–8 Q&A, 100% verbatim JSON-LD match, `<details><summary>` preferred)*
    - `sticky_split_accordion`: D `4-col` sticky H2 + `8-col` `<details>` stack | T `8-col` + `<details>` | M `1-col` (`>=48px` `<summary>`)
    - `single_column_accordion`: D `8-col` (`72ch`) `<details>` stack w/ `1px`/`2px` dividers | T `8-col` | M `1-col` (`>=48px` `<summary>`)
    - `two_column_qa_grid`: D `6+6` always-open Q&A grid (0 click friction) | T `4+4` | M `1-col`

18. **`legal`** *(68ch measure, lh>=1.65, >=3 clauses)*
    - `document_column`: D `8-col` (`68ch`) prose + H3 clause anchors | T `8-col` | M `1-col`
    - `sticky_toc_clauses`: D `3-col` sticky jump-list + `9-col` (`68ch`) body | T jump links + `8-col` | M `<details>` TOC + `1-col`
    - `structured_cards`: D `6+6` categorized cards (`Privacy | Terms | Registry`) | T `2-col` | M `1-col`

19. **`contact`** *(<=4 fields, visible `<label>` ABOVE input, `--border-control`, `.hp-trap`, `role="status"`)*
    - `split_form_details`: D `7-col` form + `5-col` contact card | T `8-col` + `8-col` | M `1-col` (`48px` inputs)
    - `centered_concierge`: D `3-col` contact strip + centered `7-col` form | T `3-col` + `8-col` | M `1-col`
    - `ledger_intake`: D `5-col` hairline directory + `7-col` enterprise form | T `8-col` stack | M `1-col`
