# Conversion Copywriting, Marketing Funnels & Engagement

## 1. Frameworks Adapted to Multi-Block Websites
- **Eugene Schwartz — 5 Stages of Market Awareness:** Match Hero H1 to visitor mental state:
  - **S1 Unaware:** Hidden symptom -> Surprising concrete fact/friction (`AIDA` Attention + `StoryBrand` Character). Low-friction CTA (audit/guide).
  - **S2 Problem Aware:** Active pain -> Name bottleneck & cost of delay (`PAS`: Problem -> Agitate -> Solution).
  - **S3 Solution Aware:** Knows category -> Prove Unique Mechanism (`BAB`: Before -> After -> Bridge).
  - **S4 Product Aware:** Comparing vendors -> Specs, deltas, comparison `<table>`, risk-reversal, objection-killing FAQ (`StoryBrand` Stakes + `BAB` Proof).
  - **S5 Most Aware:** Ready to buy -> Offer, pricing, SLA/guarantee, direct CTA (`AIDA` Action).
- **Frameworks:** `PAS` (local services, urgent B2B pain), `AIDA` (DTC, flagship launches, S5 direct offers), `StoryBrand SB7` (Customer=Hero, Brand=Guide -> 3-step plan -> stakes; high-trust B2B/agencies), `BAB` (industrial/SaaS measurable ROI).
- **Verified Benchmarks (Unbounce Q4 2024 Benchmark Report, 41k+ campaign landing pages — CXL cited):** All-industry median CVR for dedicated paid/campaign landing pages (incl. lead-magnet signups) is **6.6%**, **SaaS 3.8%**, **Financial Services 8.3%**, **Education 8.4%** (multi-page corporate sites typically convert lower at 1–3%; traffic source & message match outweigh industry baseline).

## 2. Deterministic Funnel Router (`pages.py:93-113` `AVAILABLE_BLOCKS`)
```python
def route_funnel(business_model: str, price_tier: str, awareness_level: int):
    # awareness_level: 1..5 (0=mixed homepage walks S2->S3->S4->S5); price_tier: low|mid|high|enterprise
    if awareness_level == 5:
        return "AIDA_Direct", ["hero", "stats", "pricing", "testimonials", "faq", "cta", "contact", "footer"]
    routes = {
        "B2B_SaaS": ("BAB" if awareness_level in (3, 4) else "PAS",
                     ["hero", "stats", "manifesto", "features", "process", "testimonials", "pricing", "faq", "cta", "footer"]),
        "Local_Service": ("PAS", ["hero", "stats", "features", "process", "gallery", "testimonials", "pricing", "faq", "locations", "contact", "footer"]),
        "Agency_Studio": ("StoryBrand_SB7" if price_tier in ("high", "enterprise") else "BAB",
                          ["hero", "manifesto", "gallery", "stats", "process", "testimonials", "team", "pricing", "faq", "cta", "contact", "footer"]),
        "Ecom_DTC": ("AIDA" if price_tier == "low" else "BAB",
                     ["hero", "gallery", "features", "values", "testimonials", "stats", "pricing", "faq", "cta", "footer"]),
        "Industrial_Engineering": ("BAB_Technical",
                                   ["hero", "stats", "priorities", "features", "process", "gallery", "about", "team", "faq", "locations", "contact", "footer"]),
        "Portfolio": ("StoryBrand_Lite", ["hero", "manifesto", "gallery", "about", "process", "testimonials", "contact", "footer"]),
    }
    fw, seq = routes.get(business_model, ("PAS", ["hero", "features", "stats", "process", "pricing", "faq", "contact", "footer"]))
    seq = list(seq)
    if price_tier == "enterprise" and "contact" not in seq:
        seq.insert(-1, "contact")
    if awareness_level == 1:
        seq = ["hero", "manifesto", "about"] + [b for b in seq if b not in ("hero", "manifesto", "about")]
    return fw, seq
```

## 3. Persuasive Job per Block Slot (Zero Overlap)
1. **`hero`:** WHO + SPECIFIC OUTCOME + MECHANISM/TIMEFRAME in H1 (`<= 8w EN / 6w RU`), backed by 1 constraint/proof in subhead (`<= 20w`) + primary CTA.
2. **`manifesto` / `priorities`:** Name status-quo failure and trade-offs ("Built for X, not for Y").
3. **`features` / `process`:** Explain *how* the outcome is achieved (specs, tolerances, workflow steps, SLA) — zero pricing tiers inside `features`.
4. **`stats` / `testimonials` / `gallery`:** Grounded numbers with units/scope; testimonials require Name + Role + Company + measurable delta (ban generic praise).
5. **`pricing`:** Transparent scope, turnaround, and explicit guarantee/cancellation terms next to CTA.
6. **`faq`:** Kill real buying blockers (migration, downtime, SLA, hidden fees, compliance, refund) — never filler trivia.
7. **`cta` / `contact`:** Restate outcome + friction reducer ("15-min technical review, quote in 24h").

## 4. Reader Engagement & Single-Intent CTA Discipline
- **NN/g Layer-Cake Frosting:** Visitors scan H1 -> H2 -> H3 horizontally. Reading headings alone MUST convey `Pain -> Mechanism -> Proof -> Offer -> Action` (ban vague headings like "Our Philosophy" or "Step into Tomorrow").
- **Specificity Rule (Without Hallucinating):** Anchor claims in `foundation.json` numbers OR concrete **mechanisms, materials, timeframes, and named trade-offs** (`±0.015 mm 7075 aluminum`, `2h Slack SLA, no phone support on Starter`).
- **Micro-Rhythm:** Max 2–3 sentences per paragraph (`<= 50 words`), front-load concrete nouns/numbers in the first 3 words.
- **Native Interactive Hooks:** Comparison `<table>` (concrete deltas), `<details>` objection FAQ, pricing/ROI slider calculator, sticky `process` rail, or before/after switcher.
- **Single-Intent CTA:** `[Action Verb] + [Concrete Outcome] + [Risk-Reducer Microcopy]` (EN: `Get My 48h Audit` · `No card, 3-min form`; RU: `Получить смету за 24 часа` · `Без звонков · PDF на почту`). Keep ONE primary conversion intent across header, hero, and footer (max 1 softer secondary CTA).
