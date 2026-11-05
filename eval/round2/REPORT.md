# SmartLLM — Round 2 Evaluation Report (`eval/round2/REPORT.md`)

**Date:** 2026-10-24  
**Tasks:**
- **T1 (`Industrial B2B Engineering`, EN):** `"THERMOTECH ENGINEERING"` — 5–25 MW industrial boilers (`index.html`, `llms.txt`, `robots.txt`, `_headers`).
- **T2 (`Vision-to-Code`, EN):** Pixel-accurate single-file HTML/CSS/SVG recreation of `eval/baseline/ref/t2.png` (`VKVstudio.pro`).
- **T3 (`Luxury Minimalism`, RU):** `«Северная Мануфактура»` — бутик-производитель мебели из массива дуба (`index.html`, `llms.txt`, `robots.txt`, `_headers`, antiqua `Cormorant Garamond / Playfair Display` system fallbacks, `clamp(4rem, 10vw, 12rem)`, `oklch(0.95 0.01 85)`).

**Configurations (OpenRouter API, `temperature=0.2`, `max_tokens=32768`):**
1. **`qwen3.8-no-think`:** `qwen/qwen3.8-flash` with `reasoning: {"enabled": false}` (verified `reasoning_tokens = 0` across all 3 tasks).
2. **`qwen3.8-think-8k`:** `qwen/qwen3.8-flash` with `reasoning: {"max_tokens": 8000}` (actual usage: `1,200–1,543` reasoning tokens).
3. **`qwen3.6-35b-a3b`:** `qwen/qwen3.6-35b-a3b` (`Qwen/Qwen3.6-35B-A3B`) with default reasoning (`562–8,629` reasoning tokens).

**CSP Postprocessor Rule:** Raw model outputs are preserved untouched in `<config>/<task>/orig/`. Before Playwright rendering and Lighthouse auditing, `audit_round2.py` computes SHA-256 hashes of all inline `<style>`, `<script>`, and `style="..."` attributes and injects them into `<meta http-equiv="Content-Security-Policy">` and `_headers`. As a result, **0 CSP console errors** occurred across all 9 runs.

---

## 1. Summary Table (Config × Task)

| Config | Task | Wall Time (s) | Reas. Toks | Comp. Toks | Finish | Cost ($) | Files | Lighthouse (P / A / BP / SEO)* | JSON-LD / FAQ | `_headers` | Contrast (AAA/AA) | Canon (0–10) | Design (0–10) | Copy / RU (0–10) | T2 Ref Sim (0–10) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **`qwen3.8-no-think`** | **T1** | 219.6 | **0** | 19,931 | `stop` | $0.0094 | 4/4 | **100 / 89 / 96 / 100** | 4/4 types, 5/5 FAQ | 7/7 | 1 minor badge warn | **9.5** | **9.5** | **9.5** | — |
| **`qwen3.8-no-think`** | **T2** | 58.7 | **0** | 7,111 | `stop` | $0.0037 | 1/1 | **100 / 96 / 93 / 91** | N/A | N/A | Pass | **8.5** | **8.0** | **9.0** | **8.0** |
| **`qwen3.8-no-think`** | **T3** | 191.3 | **0** | 16,368 | `stop` | $0.0078 | 4/4 | **100 / 98 / 96 / 100** | 4/4 types, 5/5 FAQ | 7/7 | Pass (19.6:1 body) | **9.5** | **9.0** | **9.5** (RU: **9.5**) | — |
| **`qwen3.8-think-8k`** | **T1** | 176.4 | **1,288** | 13,770 | `stop` | $0.0065 | 4/4 | **100 / 99 / 96 / 100** | 4/4 types, 5/5 FAQ | 7/7 | Pass AAA | **9.5** | **9.5** | **9.5** | — |
| **`qwen3.8-think-8k`** | **T2** | 75.9 | **1,200** | 9,155 | `stop` | $0.0044 | 1/1 | **100 / 88 / 96 / 90** | N/A | N/A | 1 muted pill warn | **9.0** | **9.0** | **9.5** | **9.0** |
| **`qwen3.8-think-8k`** | **T3** | 197.3 | **1,543** | 15,955 | `stop` | $0.0075 | 4/4 | **100 / 100 / 96 / 100** | 4/4 types, 5/5 FAQ | 7/7 | Pass AAA (15.8:1) | **10.0** | **9.5** | **10.0** (RU: **10.0**) | — |
| **`qwen3.6-35b-a3b`** | **T1** | 140.5 | **8,629** | 15,864 | `stop` | $0.0151 | 4/4 | **100 / 100 / 96 / 100** | 4/4 types, 5/5 FAQ | 7/7 | Pass | **7.0** | **6.5** | **7.5** | — |
| **`qwen3.6-35b-a3b`** | **T2** | 89.9 | **562** | 6,905 | `stop` | $0.0067 | 1/1 | **100 / 88 / 96 / 90** | N/A | N/A | 1 muted text warn | **5.5** | **6.0** | **7.0** | **6.5** |
| **`qwen3.6-35b-a3b`** | **T3** | 102.9 | **4,932** | 10,993 | `stop` | $0.0099 | 4/4 | **100 / 96 / 96 / 100** | 4/4 types, 5/5 FAQ | 7/7 | Pass | **6.5** | **6.0** | **7.0** (RU: **6.5**) | — |

*\*Note on Lighthouse Best Practices = 96:* The only 4-point deduction across runs is headless Chromium requesting `/favicon.ico` (HTTP 404) when no inline `<link rel="icon" href="data:...">` is present. Zero CSP errors occurred after SHA-256 postprocessing.

---

## 2. Main Conclusions

### Question 1: «Qwen без длинного reasoning сохраняет качество?»
**Вердикт: ДА — на 90–95% сохраняет, а в связке с коротким бюджетом (`reasoning.max_tokens=8000`, фактически `~1,200–1,550` токенов) даёт идеальный результат `10/10` без единого обрыва (`finish_reason="stop"`).**

1. **Режим `reasoning=OFF` (`qwen3.8-no-think`, `0` reasoning-токенов):**
   - Полностью устранил проблему Раунда 1 (где модель тратила 16K–24K токенов на рассуждения и обрезалась по `length`).
   - В **T1** и **T3** сгенерировал самый объёмный и детальный код (`64.4 КБ` / `1,017` строк в T1; `48.5 КБ` / `794` строки в T3): 11-строчную инженерную матрицу котлов, сложнейший чертёж продольного разреза котла в SVG, `4/4` файлов, `5/5` дословных FAQ в DOM и JSON-LD `@graph`, `7/7` заголовков безопасности.
   - Мелкие промахи без reasoning: в **T1** забыл продублировать `<meta http-equiv="Content-Security-Policy">` в `<head>` (оставил CSP только в `_headers`), в **T2** подставил 3 внешних URL `https://picsum.photos/...` вместо инлайновых SVG-заглушек, а в **T3** оставил один непереведённый английский термин в технической подписи (`mortise-and-tenon & dovetail`, `Кодекс цепочки custody COC`).
2. **Режим с коротким reasoning (`qwen3.8-think-8k`, фактически `1,200–1,543` reasoning-токена):**
   - При наличии лимита `max_tokens: 8000` модель **сама укладывается в `1.2K–1.5K` токенов рассуждений** и выдаёт самый чистый результат в тесте:
     - **T1:** Lighthouse `100 / 99 / 96 / 100`, `0` внешних URL, эталонный Industrial B2B канон (`9.5/10`).
     - **T2:** Лучшее визуальное попадание в референс (`9.0/10`) — все 3 иллюстрации карточек и круговая орбитальная диаграмма отрисованы чистым инлайновым SVG без внешних картинок.
     - **T3:** Lighthouse **`100 / 100 / 96 / 100`**, канон `10/10`, русский язык **`10/10`** (ни одной кальки или англицизма, точные ссылки на ГОСТ 19917-2014 и ГОСТ 16797-2001, двухсекционный чертёж соединений «шип-паз» и «ласточкин хвост» с размерными линиями в мм).
   - **Практический вывод для локального продакшена:** Отключать reasoning в ноль не обязательно и даже чуть дешевле держать **короткий бюджет рассуждений (`1,024–2,048` токенов)** либо `enable_thinking=false` для простых правок. Это экономит `~15,000` токенов генерации на запрос и полностью исключает обрывы.

---

### Question 2: «Qwen3.8 обходит Qwen3.6-35B-A3B на вебе и насколько?»
**Вердикт: ДА, кардинально — отрыв составляет `+2.5…+3.5 балла из 10` по дизайну, канону, вёрстке и качеству русского языка, причём `Qwen3.8-Flash` работает в 1.5–2 раза дешевле за счёт отсутствия раздутого reasoning.**

1. **Объём и глубина кода (`2x–3x` разница):**
   - На **T1** и **T3** `qwen3.6-35b-a3b` тратит **50–55% всех токенов на reasoning** (`8,629` и `4,932` токенов), а на сам сайт выдаёт всего `18–23 КБ` (`259–413` строк) против `36–64 КБ` (`794–1,093` строк) у `Qwen3.8-Flash`.
2. **Ошибки вёрстки и JS у `Qwen3.6-35B-A3B`:**
   - **Горизонтальный скролл на мобильном (`375px`):** и в T1 (`scrollWidth = 515px`), и в T3 (`scrollWidth = 551px`) вёрстка `Qwen3.6-35B-A3B` ломает мобильный вьюпорт (у `Qwen3.8-Flash` во всех 6 прогонах `scrollWidth = 375px`, `overflow = false`).
   - **Runtime JS crash в T3:** `Qwen3.6-35B-A3B` поместил `<script>` в `<head>` без `defer` / `DOMContentLoaded`, вызвав `TypeError: Cannot read properties of null (reading 'addEventListener')` при загрузке страницы.
   - **Нарушение OKLCH в T2:** `Qwen3.6-35B-A3B` использовал **0 токенов `oklch()`** в T2 (против 9–10 у `Qwen3.8`), заменил все иллюстрации серыми полосатыми заглушками с надписью `Image` и исказил текст со скриншота (`Pause notion` вместо `Pause motion`, `VIEW AUDIT COST` вместо `View audit scope`, `2024` вместо `2026`).
3. **Качество русского языка в T3 (`Северная Мануфактура`):**
   - **`qwen3.8-think-8k` (`10/10`) и `qwen3.8-no-think` (`9.5/10`):** Богатая профессиональная столярная терминология (*радиальный распил, сердцевинные лучи, столярное соединение «ласточкин хвост» и сквозной «шип-паз», царга, компенсационные пазы, тунговое масло и карнаубский воск*), естественный ритм текста без канцелярита и ИИ-штампов.
   - **`qwen3.6-35b-a3b` (`6.5/10`):** В `<meta name="description">` допустил склейку латиницы и кириллицы в одном слове (**`«Бoutique-производство»`**), оставил английский email `info@northern-manufactory.ru` и `https://example.com/`, а тексты секций написал сухими однострочными тезисами.

---

## 3. Artifacts & File Paths

- Сводные JSON-метрики прогонов: [`eval/round2/run_summary.json`](file:///d:/projects/SmartLLM/eval/round2/run_summary.json)
- Статический аудит и отчёт CSP-постпроцессора: [`eval/round2/static_audit.json`](file:///d:/projects/SmartLLM/eval/round2/static_audit.json)
- Playwright + Lighthouse runtime-аудит: [`eval/round2/runtime_audit.json`](file:///d:/projects/SmartLLM/eval/round2/runtime_audit.json)
- Сгенерированные сайты и скриншоты (`orig/` — сырой ответ модели, корень задачи — с проставленными SHA-256 CSP):
  - `qwen3.8-no-think`: [`T1`](file:///d:/projects/SmartLLM/eval/round2/qwen3.8-no-think/t1/index.html), [`T2`](file:///d:/projects/SmartLLM/eval/round2/qwen3.8-no-think/t2/index.html), [`T3`](file:///d:/projects/SmartLLM/eval/round2/qwen3.8-no-think/t3/index.html)
  - `qwen3.8-think-8k`: [`T1`](file:///d:/projects/SmartLLM/eval/round2/qwen3.8-think-8k/t1/index.html), [`T2`](file:///d:/projects/SmartLLM/eval/round2/qwen3.8-think-8k/t2/index.html), [`T3`](file:///d:/projects/SmartLLM/eval/round2/qwen3.8-think-8k/t3/index.html)
  - `qwen3.6-35b-a3b`: [`T1`](file:///d:/projects/SmartLLM/eval/round2/qwen3.6-35b-a3b/t1/index.html), [`T2`](file:///d:/projects/SmartLLM/eval/round2/qwen3.6-35b-a3b/t2/index.html), [`T3`](file:///d:/projects/SmartLLM/eval/round2/qwen3.6-35b-a3b/t3/index.html)
