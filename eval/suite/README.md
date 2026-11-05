# SmartLLM Offline Evaluation Suite (`eval/suite/`)

**Версия:** `1.0.0`  
**Режим:** Строго офлайн / локальный (`$0`, внешние платные API и OpenRouter заблокированы в `run_suite.py` на уровне кода).

---

## 1. Назначение и архитектура

Набор `eval/suite/` фиксирует единый неизменный эталон из **12 задач (`T1–T12`)** для объективного сравнения:
1. **Донора до обрезки (`Qwen/Qwen3.8-Flash-Next` full 512 экспертов/слой):**
   - Сохранённые полные ответы на `T1–T3` (`eval/suite/runs/qwen3.8-think-8k/` и `eval/suite/runs/qwen3.8-no-think/`),
   - Локальный референс по всем 12 задачам на `Gyro-M` (`Qwen3.8-Flash-Next-Gyro-M-TQ2_0.gguf` + `mmproj-Qwen3.8-Flash-Next-BF16.gguf`, бюджет reasoning `~4000`).
2. **Обрезанной модели (`512 → 205` экспертов/слой, `IQ3_XXS` / `IQ3_S` + `imatrix` на mainline `llama.cpp`)**.

---

## 2. Матрица 12 задач (`T1–T12` в `eval/suite/tasks.json`)

Распределение задач:
- **Языки и модальности:** **6 EN** (`t1, t4, t5, t6, t9, t11`) + **4 RU** (`t3, t7, t8, t10`) + **2 по скриншоту Vision-to-Code** (`t2, t12`) = **12 задач**.
- **Преемственность:** `t1`, `t2`, `t3` включены из `eval/round2` **без единого изменения промпта** (побайтовое совпадение проверено).
- **Покрытие всех 6 дизайн-канонов в `OKLCH`:**
  1. `Industrial B2B Engineering` — `t1` (EN, котлы 5–25 МВт) и `t11` (EN, волновые редукторы + 3D/Canvas кинематика).
  2. `Luxury Minimalism` — `t3` (RU, «Северная Мануфактура», столярная мануфактура).
  3. `Swiss Typographic Grid` — `t5` (EN, акустическая метрология + CSS Subgrid + кинетический таймлайн) и `t9` (EN, агентное многофайловое приложение).
  4. `High-Tech SaaS Dark Mode` — `t6` (EN, WebGL/GLSL шейдер + Bento-сетка) и `t10` (RU, «КОНТУР-СПЕКТР», вибродиагностика турбоагрегатов).
  5. `Neo-Brutalism` — `t7` (RU, «ЦЕХ №4», 5-осевая ЧПУ-металлообработка + интерактивный калькулятор партии).
  6. `Editorial` — `t8` (RU, «АРХИВ ТЕХНОЛОГИЙ», журнальный лонгрид по EUV-литографии + `@container` + `subgrid` + буквица).
- **Специальные задачи:**
  - `t4` — **Общий кодинг (DAG на TypeScript):** генерация `dag.ts` (топологическая сортировка, детекция циклов `DAGCycleError`, ограничение параллелизма `maxConcurrency`, ретраи с экспоненциальным backoff, пропуск зависимых веток при сбое, `AbortSignal`), проверяется строгой компиляцией `tsc --noEmit --strict` и 12 детерминированными unit-тестами (`eval/suite/test_dag_runner.mjs`).
  - `t9` — **Агентная многофайловая задача (7 файлов):** координированный выпуск `DESIGN.md`, `tokens.css`, `app.js`, `index.html`, `zimage_prompts.json` (3 промпта для `Z-Image-Turbo` с проверкой дословного вхождения текста в кавычках `exact_text_in_frame`), `llms.txt`, `_headers`.

| ID | Язык / Модальность | Дизайн-канон / Категория | Проверяемые технологии и выходные файлы |
|---|---|---|---|
| `t1` | EN (Text) *(из round2)* | `Industrial B2B Engineering` | OKLCH, 1px сетка, таблица 3 котлов, inline SVG схема, JSON-LD `@graph`, CSP, `index.html`, `llms.txt`, `robots.txt`, `_headers` |
| `t2` | EN (`Vision` `ref/t2.png`) *(из round2)* | `Editorial / Studio Light` | Вёрстка по скриншоту `1440×3548`, OKLCH-токены, адаптивность `375px`, `index.html` |
| `t3` | RU (Text) *(из round2)* | `Luxury Minimalism` | Русский копирайтинг, OKLCH, SVG столярного узла, JSON-LD `@graph`, CSP, `index.html`, `llms.txt`, `robots.txt`, `_headers` |
| `t4` | EN (Code) | `General Coding (TypeScript)` | `dag.ts` — строгий `tsc --noEmit --strict --target ES2022` + 12 автотестов (`test_dag_runner.mjs`) |
| `t5` | EN (Text) | `Swiss Typographic Grid` | 12-колоночный Grid + `subgrid`, `tabular-nums`, кинетический таймлайн, RT60 калькулятор + SVG кривая, `index.html`, `llms.txt`, `robots.txt`, `_headers` |
| `t6` | EN (Text) | `High-Tech SaaS Dark Mode` | Интерактивный `WebGL / GLSL` шейдер в `<canvas>`, 6-ячеечная Bento-сетка, калькулятор VRAM/tok/s, `index.html`, `llms.txt`, `robots.txt`, `_headers` |
| `t7` | RU (Text) | `Neo-Brutalism` | Жёсткие тени `4px 4px 0`, рамки `2px solid`, калькулятор ЧПУ-партии (ВТ6/12Х18Н10Т, IT6), изометрический SVG, `index.html`, `llms.txt`, `robots.txt`, `_headers` |
| `t8` | RU (Text) | `Editorial` | Многоколоночный лонгрид, `@container`, `subgrid`, буквица `::first-letter`, SVG тракта EUV 13.5 нм, калькулятор Рэлея, `index.html`, `llms.txt`, `robots.txt`, `_headers` |
| `t9` | EN (Agentic Multi-File) | `Swiss Typographic Grid` | 7 файлов: `DESIGN.md`, `tokens.css`, `app.js`, `index.html`, `zimage_prompts.json` (промпты `Z-Image-Turbo`), `llms.txt`, `_headers` |
| `t10` | RU (Text) | `High-Tech SaaS Dark Mode` | Панель вибродиагностики по ГОСТ ИСО 10816-3, интерактивный SVG БПФ-спектр (1X/2X/3X), Bento-сетка, `index.html`, `llms.txt`, `robots.txt`, `_headers` |
| `t11` | EN (Text) | `Industrial B2B Engineering` | Интерактивный `<canvas>` визуализатор планетарного/волнового редуктора, SVG кривая момента, `index.html`, `llms.txt`, `robots.txt`, `_headers` |
| `t12` | EN (`Vision` `ref/t12.png`) | `High-Tech SaaS Dark / Swiss` | Вёрстка по тёмному телеметрическому скриншоту `1440×900` (`ref/t12.png`), OKLCH, `375px`, `index.html` |

---

## 3. Автоматические проверки (`audit_suite.py` + `browser_and_lh_suite.mjs`)

1. **Детерминированный CSP-постпроцессор (`apply_csp_postprocessor` в `audit_suite.py`):**
   - Сохраняет нетронутые исходники модели в `orig/index.html` и `orig/_headers`.
   - Вычисляет точные `sha256-...` хэши всех блоков `<style>`, всех инлайновых `<script>` и всех статических атрибутов `style="..."` (с добавлением `'unsafe-hashes'` при наличии `style="..."`).
   - Инжектирует вычисленную политику в `<meta http-equiv="Content-Security-Policy">` и `_headers`.
2. **Статический аудит HTML5, SEO/GEO, Security и OKLCH (`audit_suite.py`):**
   - Полнота файлов, семантика (`1× h1`, landmarks, связка `label`/`input`, `prefers-reduced-motion`).
   - Отсутствие внешних URL в атрибутах (`0` внешних зависимостей).
   - Валидность `JSON-LD @graph` (`Organization`, `Product`, `FAQPage`, `BreadcrumbList`) и **дословное совпадение (`faq_all_verbatim`)** вопросов и ответов с видимым HTML.
   - Проверка всех 7 заголовков безопасности в `_headers` (`CSP + frame-ancestors 'none'`, `HSTS 63072000 + includeSubDomains + preload`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`).
   - Парсинг `:root` `oklch(L C H)` токенов, перевод `OKLCH → linear sRGB → relative luminance` и расчёт контраста WCAG AAA (`≥ 7:1`).
3. **Компиляция и тестирование TypeScript (`test_dag_runner.mjs` для `t4`):**
   - Строгая проверка типов `tsc --noEmit --strict --target ES2022` (через локальный `C:\projects\VKVstudio\node_modules\typescript\bin\tsc`, `Version 6.0.3`).
   - Запуск 12 детерминированных unit-тестов (`Empty`, `Linear`, `Diamond`, `3-node Cycle`, `Self-Cycle`, `Missing Dep`, `Duplicate ID`, `maxConcurrency=2`, `Exponential Backoff Retry`, `Downstream Skipping on Failure`, `AbortSignal Cancellation`, `Typed Context & Duration`).
4. **Playwright + Lighthouse аудит (`browser_and_lh_suite.mjs`):**
   - Рендер в headless Chromium (`1440×900` и `375×812`), скриншоты `shot-desktop.png`, `shot-desktop-full.png`, `shot-mobile.png`, `shot-mobile-full.png`.
   - Проверка отсутствия горизонтального скролла (`overflowX: false`), `consoleErrors`, `pageErrors`, внешних запросов, `CLS = 0` и оценок Lighthouse (`Performance`, `Accessibility`, `Best Practices`, `SEO`).
   - Работает в двух режимах: полностью без открытия портов (`file://` + встроенный `snapshot` Lighthouse) и через локальный HTTP-сервер (`--http-nav`).

---

## 4. Судьи (`judge_rubric.md` + `aggregate_judges.py`)

- 2 независимых слепых судьи (`Gemini 3.8 Flash`).
- Каждый судья независимо выставляет оценки `0–10` по 4 осям (`canon`, `design`, `copy`, `ru`) в `results/judge_1.json` и `results/judge_2.json`.
- Скрипт `aggregate_judges.py` считает средние баллы и автоматически помечает любое расхождение `|score_1 - score_2| > 2.0` (`discrepancy_flagged: true`).

---

## 5. Команды запуска

```powershell
# 1. Статический аудит + CSP-постпроцессор + tsc/DAG-тесты (без GPU и без портов):
.venv\Scripts\python.exe eval\suite\audit_suite.py

# 2. Браузерный рендер Playwright (1440x900 и 375x812) + Lighthouse в режиме file:// (без открытия портов):
node eval\suite\browser_and_lh_suite.mjs

# 3. Агрегация оценок 2 слепых судей и проверка расхождений > 2 баллов:
.venv\Scripts\python.exe eval\suite\aggregate_judges.py

# 4. Локальный прогон всех 12 задач через локальный OpenAI-совместимый сервер (llama-server):
.venv\Scripts\python.exe eval\suite\run_suite.py --endpoint http://127.0.0.1:8080/v1/chat/completions --model-slug qwen3.8-reap-205 --model-id qwen3.8-reap-205 --reasoning-budget 4000
```
