# Anti-AI-Writing Canon (EN `WP:AISIGNS` + RU Anti-Kantselyarit)

> Deterministic linter regexes live in `copy_marketing/anti_ai_regex_rules.json` (run automatically by Python with 0 LLM tokens).

## 1. EN Canon — `Wikipedia:Signs of AI writing` (`WP:AISIGNS`)
Descriptive clustering taxonomy across **5–6 top-level groups and ~24+ named patterns** (cluster co-occurrence exposes unedited LLM prose, NOT single-word bans; note `WP:AISIGNS` targets encyclopedic NPOV while marketing uses active direct persuasion):
- **Content & Emphasis:** (1) Inflated significance/symbolism (`serves as a testament`, `pivotal moment`, `enduring legacy`); (2) Promotional brochure puffery (`nestled in the heart of`, `breathtaking`, `vibrant tapestry`); (3) Superficial `-ing` participial tails (`..., highlighting its commitment to...`, `..., underscoring a broader shift` — keep causal specs like `CNC milled to ±0.01mm, ensuring zero backlash`); (4) Vague unsourced attributions (`experts believe`, `studies show`); (5) Formulaic "Challenges & Future Prospects" wraps.
- **Language & Grammar:** (6) AI cliché vocabulary (`delve`, `tapestry`, `testament`, `myriad`, `paramount`, `multifaceted`, `meticulously`, `revolutionize`, `synergy`, `unlock potential`); (7) Overused abstract negative parallelisms (`It's not just X — it's a journey`, cap `<=1` general `not just..but` per page); (8) Rule-of-three adjective triads; (9) Copula avoidance (`serves as`, `stands as`, `boasts` instead of `is`/`has`); (10) Synonym cycling across sentences (hurts term/brand consistency); (11) False ranges (`from X to Y`) & filler hedging.
- **Formatting & Artifacts:** (12) Rhetorical em-dash overuse (*strip SmartLLM structural `Item — Detail` delimiters first!*); (13) `- **Bold Lead:** ...` bullet spam, decorative emoji bullets, unnecessary Title Case; (14) Chatbot leakage (`Sure, here is...`, `[Placeholder]`).

## 2. RU Anti-AI & Anti-Kantselyarit Canon (Ilyakhov / Glavred + 2026 Audit)
- **Water Openers:** `в современном мире`, `в эпоху цифровизации`, `стоит отметить`, `важно подчеркнуть`, `давайте разберёмся`, `погрузиться в мир`.
- **EN->RU Calques:** `бесшовная интеграция` (seamless), `раскрыть потенциал`, `вывести на новый уровень`, `цифровой/сложный ландшафт`, `богатый гобелен`, `синергия`.
- **Corporate Fluff:** `динамично развивающаяся компания`, `команда опытных профессионалов`, `индивидуальный подход к каждому`, `оптимальное соотношение цены и качества`, `гибкая система скидок`, `широкий ассортимент`. *(Allow `"под ключ"` in RU construction/engineering when concrete deliverables follow; allow `"эффективность"` with real metrics like `"энергоэффективность класса A++"`.)*
- **Kantselyarit Tells:** Split predicates before deverbal action nouns (`осуществлять проверку`, `производить монтаж` -> `проверить`, `смонтировать` — NEVER flag real manufacturing like `производим стальные детали`!), stacked genitive chains, and `это не просто X — это философия/путешествие`. *(Skip `legal` statutory wording like `в целях исполнения договора`.)*

## 3. Calibrated Metrics & Anti-Hallucination Guard
- **Skip Blocks:** Do not run stylistic AI regexes on `legal, contact, locations, stats, team, pricing`.
- **Page-Level Burstiness CV:** Pool true prose (`hero.subhead`, `manifesto`, `about`, `testimonials`, `faq` answers, `cta`) after protecting decimals (`\d[.,]\d`) & abbreviations (`г.`, `ул.`, `Dr.`, `Inc.`). Warn softly only if `N >= 8` sentences and `CV < 0.25`.
- **Specificity & Single Truth:** Credit `foundation.json` numbers + concrete materials/deliverables/timeframes (`>= 0.20` warn). **NEVER invent unverified numbers, ISO certs, or awards missing from `foundation.json`.**
- **Prose Em-Dash Cap:** Strip ` — ` item delimiter first; warn if `>= 3` rhetorical dashes/paragraph or `>= 6`/page.

## 4. Compact Before/After Rewrites (EN & RU)
- `[EN CNC]` ❌ *Seamless next-gen CNC solutions, fostering precision.* -> ✅ *5-axis titanium and 7075 aluminum parts held to ±0.015 mm. First-article inspection ships in 72 hours.*
- `[EN Dental]` ❌ *It's not just dentistry — it's a vibrant smile journey.* -> ✅ *Same-day ceramic crowns milled in-house in 90 minutes. Open 7 AM–7 PM on Oak Street.*
- `[RU Столярка]` ❌ *В современном мире кухня играет ключевую роль.* -> ✅ *Кухни из массива дуба и эмали МДФ с точностью до 1 мм. Изготовление за 28 дней, монтаж за 1 день, фурнитура Blum — 10 лет гарантии.*
- `[RU M&A Юрист]` ❌ *Осуществляем комплексное сопровождение и оказываем содействие бизнесу.* -> ✅ *Проверяем компании перед сделкой за 10 рабочих дней: находим налоговые разрывы, залоги и спорные доли до подписания договора.*
