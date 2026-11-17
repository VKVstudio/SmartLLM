# SmartLLM v2 — Быстрый старт офлайн-комбайна (Web + Design + Copywriting + Z-Image)

Офлайн-комбайн `SmartLLM v2` в одну команду собирает готовый сайт (копирайтинг `EN/RU`, верстка `HTML5 + OKLCH CSS + TypeScript/JS`, строгие SHA-256 CSP-хэши, `JSON-LD`, `llms.txt`) и генерирует визуальные ассеты через `Z-Image` (`stable-diffusion.cpp`) с последовательным переключением GPU (`LLM -> 0 VRAM -> Z-Image -> 0 VRAM`). Все сервисы привязаны строго к `127.0.0.1` без внешних сетевых вызовов.

## 1. Запуск в одну команду (Боевой GPU-режим)
```bash
# Русский бриф (автоопределение языка, RAG-канонов и GGUF-профиля OPUS §1.D1):
./run_combine.sh \
  --brief "Премиальный лендинг для студии промышленного дизайна и робототехники в Москве" \
  --out eval/combine_out/robotics_ru

# Английский бриф с двумя Z-Image иллюстрациями (hero + feature):
./run_combine.sh \
  --brief "High-craft developer landing page for an offline-first Rust vector database" \
  --lang en --num-images 2 --out eval/combine_out/vectordb_en
```

## 2. Автовыбор GGUF и профилей `OPUS §1.D1`
Скрипт автоматически ищет `models/SmartLLM-v2-*.gguf` и применяет параметры из `research/v2_runs/wave3/wave3_summary.json` или таблицы `§1.D1`:
- `K320 + IQ3_XXS`: `--n-cpu-moe 43 --moe-cache-mib 1536`
- `K320 + IQ2_S`: `--n-cpu-moe 48 --moe-cache-mib 3840`
- `K288`: `--n-cpu-moe 40 --moe-cache-mib 512`
- Временный запуск на baseline-модели v1 (`205E`): добавь флаг `--allow-dev-205e` или укажи `--gguf <path>`.
- Обязательные флаги рантайма (`--lazy-mode direct -nr --moe-cache-cpu-share 0.15 -fa on -ctk q8_0 -ctv q8_0 -c 32768 -ub 512 -np 1 --cache-ram 0 --spec-type draft-mtp --host 127.0.0.1`) и `SLA Watchdog` (`0 B SSD/NVMe свопа, zram0 <= 512 MiB`, `MemAvailable >= 3.0 GiB`, `PLE RSS == 0 KB`) включаются автоматически.

## 3. CPU-предпросмотр, REPL и локальный браузерный стенд (`127.0.0.1`)
```bash
# Мгновенная сборка на CPU без загрузки GPU (0 MiB VRAM, < 250 MiB RAM):
./run_combine.sh --dry-run \
  --brief "Лендинг инженерной платформы финтех-инфраструктуры" \
  --out eval/combine_out/fintech_preview

# Интерактивный терминальный режим (REPL):
./run_combine.sh --repl

# Локальный веб-интерфейс (Workbench) на http://127.0.0.1:8090:
./run_combine.sh --serve-ui --ui-port 8090

# Полный CPU self-test (проверка D1-профилей, RAG-выборки, CSP и 127.0.0.1):
./run_combine.sh --self-test
```

## 4. Структура выходного пакета (`--out <dir>`)
- `index.html` — семантическая страница (`100svh`, нулевой `'unsafe-inline'`, точные SHA-256 CSP-хэши, `JSON-LD`).
- `tokens.css` — дизайн-токены (`OKLCH`, адаптивная сетка, `clamp()`-типографика).
- `app.ts` / `app.js` — интерактивный калькулятор и телеметрия без внешних зависимостей.
- `assets/hero_primary.png` — сгенерированный `1024x1024` визуал `Z-Image` (`q8_0 DiT + qwen_3_4b + ae.safetensors`).
- `rag_context.json`, `zimage_prompts.json`, `combine_manifest.json`, `_headers`, `llms.txt`, `robots.txt`.
