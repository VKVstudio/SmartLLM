# Промпты и сценарии SmartLLM Studio (`examples/`)

Три эталонных промпта и сценария для проверки и записи **SmartLLM Studio** (`v10`, `6.0/6` по всем страницам): два в **Автоматическом режиме** (`EN` и `RU`) и один в **5-шаговом Конструкторе** (`EN`) с полным ручным вводом блоков. Названия канонов, страниц, блоков и порядок полей соответствуют живому интерфейсу Studio.

| # | Режим | Язык / UI | Бренд и тема | Канон в интерфейсе | Формат | Гайд |
|---|---|---|---|---|---|---|
| 01 | Auto | `EN` / `EN UI` | **Aether Compute** — Sovereign GPU Cloud | `Bento Grid` | Multi-page (автоподбор, `8` стр.) | [01_auto_en_aether_compute.md](01_auto_en_aether_compute.md) |
| 02 | Auto | `RU` / `RU UI` | **Северный Контур** — Архбюро | `Визуальный сторителлинг` | Автоподбор (`7` стр.) | [02_auto_ru_sever_arch.md](02_auto_ru_sever_arch.md) |
| 03 | Ctor | `EN` / `EN UI` | **Kuro Specialty Roasters** — Микролоты кофе | `Micro-Interactions & Tactile UI` | `Home, About, Pricing, Contact` (`4` стр., 100% Manual) | [03_ctor_en_kuro_roasters.md](03_ctor_en_kuro_roasters.md) |

> **Подсказка:** Для англоязычных сценариев (`01`, `03`) перед началом переключи язык интерфейса кнопкой **`RU | EN` -> `EN | RU`** в верхней панели. Папки сохранения для прогонов: `/mnt/rescue/projects/SmartLLM/eval/showcase/01_aether_ai_cloud`, `02_sever_arch` и `03_kuro_roasters`.
