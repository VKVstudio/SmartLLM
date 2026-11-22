# Copywriting, Persuasion & Anti-Slop Router (`copy_marketing/_router.md`)

## 1. Execution Order Across Pipeline Stages
1. **`foundation` + `architect` -> Load `funnels_and_persuasion.md`**
   - Classify `{business_model, price_tier, awareness_level}` -> select `funnel_framework`, ordered `AVAILABLE_BLOCKS` sequence (`pages.py:93-113`), per-block persuasive role, and single primary CTA intent.
2. **`hero` + `copy` + `localize` -> Load `anti_ai_writing_en_ru.md`**
   - Enforce EN (`WP:AISIGNS` 24+ pattern model) or RU (Anti-Kantselyarit / Glavred) editorial discipline.
   - Run deterministic regex linter (`EN_HARD_BAN`, `EN_SOFT_WATCH`, `EN_PARTICIPLE_SLOP`, `RU_HARD_BAN`, `RU_SPLIT_PRED_HARD`, `RU_SOFT_WATCH`) skipping `ANTI_AI_SKIP_BLOCKS`; check page-level Burstiness CV & Specificity without triggering hallucination.
3. **`architect` + `compile` -> Load `trends_late2026_early2027.md`**
   - Enforce Anti-Slop visual diversity, dramatic type scale, Baseline CSS `scroll()`/`view()`, and Dual-Audience UX+AX semantic HTML.

## 2. Fast Dispatch Matrix
| Trigger | Load Leaf | Hard Gate |
|---|---|---|
| Brief / block planning | `funnels_and_persuasion.md` | Exact `route_funnel()` sequence; 1 primary CTA intent/page; Layer-Cake scannable headings |
| EN copy / `review` | `anti_ai_writing_en_ru.md` §1, §3–§4 | `0` `EN_HARD_BAN`; `<2` `EN_SOFT_WATCH`/block; `<=1` `not just..but`/page; `0` fake numbers |
| RU copy / `review` | `anti_ai_writing_en_ru.md` §2–§4 | `0` `RU_HARD_BAN`; `0` `RU_SPLIT_PRED_HARD` (skip `legal`); strip ` — ` pair delimiter first |
| Layout / QA | `trends_late2026_early2027.md` | `>= 10/12` Anti-Flat items; glass alpha `>= 0.72`; 0 external requests |

## 3. Non-Negotiable Cross-Cutting Invariants
- **Single Source of Truth (`foundation.json`):** Every metric, price, year, address, and team member MUST trace to `foundation.json` or explicit user brief. NEVER fabricate ISO certs, awards, or percentages to game specificity.
- **No Slop Stack:** Reject simultaneously (a) AI cliché prose, (b) flat equal-card Inter/purple/beige-cream layouts, and (c) generic CTAs (`Submit`, `Learn More`, `Отправить`, `Подробнее`).
