# canons_v2 — INDEX (исследование канонов v2)

Папка: `D:\projects\SmartLLM\kb\styles\canons_v2\`. Её НЕ читает загрузчик (`kb_loader.py:37` глобит только `kb/styles/canons/*.json` в `studio/smartllm_studio/kb/`). В код ничего не подключено.
Схема загрузки для модели: `_router.md` ИЛИ `_router.json` — модель грузит один из них (каждый ≤1.5K токенов при 20 канонах, ~60 на канон) → выбор канона → загрузка `<id>.spec.md` (≤3K токенов, секции `<!-- section:NAME -->`) + ВСЕГДА `_engineering_baseline.md` и `_ux_baseline.md` (архитектура, безопасность, формы, производительность, SEO/AEO/GEO; по инженерии база главнее канона, по внешнему виду — канон).
НЕ для модели: `INDEX.md`, `_ux_skills_audit.md` (какие UX-скиллы использованы и есть ли новее), `_vendor_manifest.md` (офлайн-ассеты: версия, лицензия, размер, путь, sha256, какие каноны; вердикт по GSAP). Ссылок на источники нигде не хранить (решение владельца): ресёрч по авторитетным источникам с перекрёстной проверкой, но без URL в файлах.
Приватно, вне репо: визуальный стиль VKV не поставляется.

| # | Канон | Файл | Статус | Дата |
|---|---|---|---|---|
| U | _ux_baseline — стиль-независимые UX-правила (грузится всегда вместе с каноном) | `_ux_baseline.{md,json}` | done | 2026-11-23 |
| B | _engineering_baseline — стиль-независимая инженерная база (грузится всегда вместе с каноном) | `_engineering_baseline.{md,json}` | done | 2026-11-23 |
| 0 | 01_vkv_studio — private reference, not shipped | – | private | 2026-11-23 |
| 1 | 01_bento_grid — Bento Grid | `01_bento_grid.spec.{md,json}` | done | 2026-11-23 |
| 2 | 03_editorial_magazine — Editorial Monograph / Broadsheet | `03_editorial_magazine.spec.{md,json}` | done | 2026-11-23 |
| 3 | 02_swiss_international | `02_swiss_international.spec.{md,json}` | done | 2026-11-23 |
| 4 | 04_hyper_minimal_speed | `04_hyper_minimal_speed.spec.{md,json}` | done | 2026-11-23 |
| 5 | 05_kinetic_typography | `05_kinetic_typography.spec.{md,json}` | done | 2026-11-23 |
| 6 | 06_neo_brutalism | `06_neo_brutalism.spec.{md,json}` | done | 2026-11-23 |
| 7 | 07_avant_garde_poster | `07_avant_garde_poster.spec.{md,json}` | done | 2026-11-23 |
| 8 | 08_liquid_glass | `08_liquid_glass.spec.{md,json}` | done | 2026-11-23 |
| 9 | 09_aurora_obsidian_mesh | `09_aurora_obsidian_mesh.spec.{md,json}` | done | 2026-11-23 |
| 10 | 10_industrial_tactile | `10_industrial_tactile.spec.{md,json}` | done | 2026-11-23 |
| 11 | 11_soft_clay_playful | `11_soft_clay_playful.spec.{md,json}` | done | 2026-11-23 |
| 12 | 12_quiet_luxury_minimal | `12_quiet_luxury_minimal.spec.{md,json}` | done | 2026-11-23 |
| 13 | 13_cinematic_documentary | `13_cinematic_documentary.spec.{md,json}` | done | 2026-11-23 |
| 14 | 14_spatial_3d_showcase | `14_spatial_3d_showcase.spec.{md,json}` | done | 2026-11-23 |
| 15 | 15_organic_biophilic_eco | `15_organic_biophilic_eco.spec.{md,json}` | done | 2026-11-23 |
| 16 | 16_artisan_craft_zine | `16_artisan_craft_zine.spec.{md,json}` | done | 2026-11-23 |
| 17 | 17_fintech_institutional | `17_fintech_institutional.spec.{md,json}` | done | 2026-11-23 |
| 18 | 18_devtool_command_ui | `18_devtool_command_ui.spec.{md,json}` | done | 2026-11-23 |
| 19 | 19_calm_human_accessible | `19_calm_human_accessible.spec.{md,json}` | done | 2026-11-23 |
| 20 | 20_maximalist_collage_pop | `20_maximalist_collage_pop.spec.{md,json}` | done | 2026-11-23 |

Порядок задан владельцем: bento → editorial → остальные по номеру. Список и имена канонов берутся из `studio/smartllm_studio/data/canon_cards.json`.

## Стиль текста спек (для маленькой Qwen)
- Короткие простые предложения на простом английском. Плоская структура: короткие заголовки и пункты, вложенность максимум 1 уровень.
- Одинаковые имена секций во всех канонах: `essence, structure, hero, blocks, motion, typography, color, surfaces, imagery, stack, seo, ux_check, vendor, hard_limits`. Секции `sources`, тегов `[S#]` и URL нет. Тег `[assumption]` остаётся для непроверенных выводов.
- Не жёсткий скрипт, а факты, принципы, варианты и причины: «Options: A, B or C. Pick by …», «Avoid X, because Y», «This works because …». Модель решает сама, опираясь на факты.
- Жёсткие ограничения — только в `Hard limits`: безопасность, a11y, класс C отложен, офлайн.
- JSON с теми же ключами: `essence{what,why,fits,weak_fits,mood,polarity}, structure, hero_options[{id,desc,pick_when,assets}], blocks{}, motion{budget,options[],avoid[[x,why]],reduced_motion}, typography, color, surfaces, imagery, stack{recommended,landing_preset,options[],avoid[]}, seo[], hard_limits[], assumptions[]` (без `sources`).

## Процедура (по одному канону за раз)
1. Прочитать карточку канона (`canon_cards.json`) и `kb/styles/canons/<id>.json`: id, токены, разрешённые стеки/моторика/пресеты.
2. Ресёрч только по устоявшимся авторитетным источникам (MDN, W3C/WCAG, web.dev, Google Search Central, документация библиотек и шрифтов, первоисточники по истории дизайна, Codrops/Awwwards для живых примеров). Каждый факт перепроверить минимум по двум источникам. Невоспроизводимое — `[assumption]`.
3. Написать `<id>.spec.md` (≤3K токенов cl100k, секции как выше; не повторять то, что уже есть в базах) и `<id>.spec.json` (те же данные). Никаких ссылок, `[S#]` и секции sources.
4. Инженерию (CSP, формы, i18n, перф, SEO/AEO/GEO) в спеку канона не дублировать — она в `_engineering_baseline.md`. В спеке — только то, что зависит от стиля.
5. Vendor: всё, что нужно канону (шрифты woff2 latin+cyrillic, JS MIT/Apache, CSS), должно лежать в `studio/smartllm_studio/templates/vendor/` (MANIFEST.json). Сначала проверить, что уже есть; докачивать только MIT/Apache/OFL, min/woff2, >50 MB — спросить владельца. В спеку — секция `vendor` с точными локальными путями (генерирует `gen_vendor.py` на боксе), строки — в `_vendor_manifest.md`. GSAP не вендорить (лицензия Webflow) — только «optional, license-restricted»; по умолчанию Motion / anime.js / Lenis / CSS scroll-driven / View Transitions.
6. UX: в каждой спеке секция `ux_check` — риски именно этого стиля и как их снять; общие правила не дублировать (они в `_ux_baseline.md`). UX важнее стиля.
6a. Классы ассетов: A — код (можно), B — стоп-кадры Z-Image (можно), C — видео/последовательности кадров — ОТЛОЖЕНО.
7. Сразу после записи: строка в `_router.md/.json`, строка этой таблицы (status, дата), `HANDOFF.md` §6 (≤35 строк), `.system/checkpoint.md`.
8. Никаких VKV-деталей в канонах; `C:\projects\VKVstudio\.system\canon` не читать. Код SmartLLM, GPU и git не трогать. Temp-файлы не удалять.

## Бюджеты токенов (cl100k, после trim-прохода 2026-11-23)
Лимиты владельца на одну загрузку: router ≤1.5K, `_engineering_baseline` ≤2.5K, `_ux_baseline` ≤2K, спека канона ≤3K. Модель грузит md ИЛИ json (компактный). Общие правила (vendor/CDN/GSAP/стек по умолчанию, класс C, generic image/a11y) вынесены в базы и в спеках не повторяются. JSON 01 и 03 — ручные (старее md по формулировкам).

| файл | md | json | лимит |
|---|---|---|---|
| _router | 1247 | 1413 | 1500 |
| _engineering_baseline | 2494 | 2478 | 2500 |
| _ux_baseline | 1940 | 2000 | 2000 |
| 01_bento_grid | 2992 | 2143 | 3000 |
| 02_swiss_international | 2613 | 2672 | 3000 |
| 03_editorial_magazine | 2868 | 1701 | 3000 |
| 04_hyper_minimal_speed | 2413 | 2463 | 3000 |
| 05_kinetic_typography | 2753 | 2864 | 3000 |
| 06_neo_brutalism | 2557 | 2655 | 3000 |
| 07_avant_garde_poster | 2399 | 2498 | 3000 |
| 08_liquid_glass | 2335 | 2404 | 3000 |
| 09_aurora_obsidian_mesh | 2112 | 2180 | 3000 |
| 10_industrial_tactile | 2114 | 2189 | 3000 |
| 11_soft_clay_playful | 2046 | 2122 | 3000 |
| 12_quiet_luxury_minimal | 2003 | 2061 | 3000 |
| 13_cinematic_documentary | 2705 | 2794 | 3000 |
| 14_spatial_3d_showcase | 2408 | 2475 | 3000 |
| 15_organic_biophilic_eco | 2145 | 2198 | 3000 |
| 16_artisan_craft_zine | 2101 | 2152 | 3000 |
| 17_fintech_institutional | 2108 | 2157 | 3000 |
| 18_devtool_command_ui | 2187 | 2223 | 3000 |
| 19_calm_human_accessible | 2212 | 2249 | 3000 |
| 20_maximalist_collage_pop | 2212 | 2298 | 3000 |
