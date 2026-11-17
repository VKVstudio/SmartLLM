"""Curated 1-of-1 bilingual specifications for SmartLLM Step 4 calibration.

Design invariants (enforced to prevent generator boilerplate bias in REAP/imatrix):
1. Strict 1-of-1 registry: zero cyclic modulo (`idx % N`) loops anywhere. Every spec
   is emitted at most once across the entire dataset.
2. Zero shared HTML skeleton: Pillar 2 (`llms.txt` / CSP / JSON-LD), Pillar 4
   (copywriting / UX microcopy / Z-Image art direction), and Agentic RU workflows
   never embed generic HTML widgets.
3. Authentic browser screenshots: all 14 multimodal OKLCH style-canon pages (8 RU + 6 EN)
   are rendered by headless Chromium (`scripts/step4_render_html.mjs`, CPU-only, 0 ports)
   into exact pixel-accurate PNGs (`1024x640` desktop or `576x1248` mobile, exact `32x32`
   multiples for `Qwen3VLProcessor` `patch_size=16, merge_size=2`).
4. Honest provenance: every record originating from this module carries `synthetic=True`
   and `reasoning_content=""` (per `scripts/step4_verify_calib.py` line 181).
"""

from __future__ import annotations

import io
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
NODE_EXE = Path(r"C:\Program Files\nodejs\node.exe")
RENDER_MJS = ROOT / "scripts" / "step4_render_html.mjs"


def render_html_batch_chromium(
    jobs: list[dict[str, Any]],
) -> dict[str, tuple[bytes, int, int]]:
    """Render HTML5 documents via headless Chromium and downsample cleanly to target sizes.

    Each job dict requires:
      - id: unique string identifier
      - html: complete <!DOCTYPE html>...</html> string
      - viewport_w, viewport_h: Chromium render viewport (e.g. 1440x900 or 384x832)
      - out_w, out_h: final saved image dimensions (multiples of 32, e.g. 1024x640 or 576x1248)
    Returns mapping `job_id -> (png_bytes, out_w, out_h)`.
    """
    if not jobs:
        return {}
    if not NODE_EXE.exists():
        raise FileNotFoundError(f"Node.js binary not found at {NODE_EXE}")
    if not RENDER_MJS.exists():
        raise FileNotFoundError(f"Chromium renderer script not found at {RENDER_MJS}")

    results: dict[str, tuple[bytes, int, int]] = {}
    with tempfile.TemporaryDirectory(prefix="smartllm_step4_chr_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        manifest: list[dict[str, Any]] = []
        for job in jobs:
            raw_png = tmp_path / f"{job['id']}_raw.png"
            manifest.append(
                {
                    "id": job["id"],
                    "html": job["html"],
                    "viewport_w": int(job["viewport_w"]),
                    "viewport_h": int(job["viewport_h"]),
                    "scale": max(1.0, round(int(job["out_w"]) / int(job["viewport_w"]), 2)),
                    "raw_png_path": str(raw_png),
                }
            )
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        proc = subprocess.run(
            [str(NODE_EXE), str(RENDER_MJS), str(manifest_path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Headless Chromium batch render failed (exit {proc.returncode}):\n"
                f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
            )

        for job, item in zip(jobs, manifest):
            raw_png = Path(item["raw_png_path"])
            if not raw_png.exists():
                raise RuntimeError(f"Chromium did not produce screenshot for {job['id']}")
            out_w, out_h = int(job["out_w"]), int(job["out_h"])
            with Image.open(raw_png) as im:
                rgb = im.convert("RGB")
                if rgb.size != (out_w, out_h):
                    rgb = rgb.resize((out_w, out_h), Image.Resampling.LANCZOS)
                stat = ImageStat.Stat(rgb)
                if max(stat.stddev) < 6.0:
                    raise RuntimeError(
                        f"Rendered screenshot for {job['id']} appears blank (stddev={stat.stddev})"
                    )
                buf = io.BytesIO()
                rgb.save(buf, format="PNG", optimize=True)
                results[job["id"]] = (buf.getvalue(), out_w, out_h)

    return results


def get_unique_multimodal_canon_specs() -> list[dict[str, Any]]:
    """Return 14 strictly 1-of-1 multimodal webpage specs (8 RU + 6 EN) across all 6 OKLCH canons."""
    specs: list[dict[str, Any]] = [
        # 1. RU Quiet Luxury (Desktop 1440x900 -> 1024x640): Architectural Bureau
        {
            "key": "ru_canon_quiet_luxury_desktop",
            "lang": "ru",
            "subdomain": "canon_quiet_luxury_ru",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Сверстай по приложенному макету десктопную страницу архитектурного бюро «Северная Линия» "
                "в каноне Quiet Luxury (OKLCH тёплый алебастр, графит и патинированная бронза). "
                "Нужна асимметричная двухколоночная сетка с боковым навигационным рельсом, реестром "
                "натуральных материалов на `<dl>` и интерактивным расчётом ориентировочной сметы проекта "
                "по площади на чистом JavaScript без внешних зависимостей."
            ),
            "rationale": (
                "Макет реализован на асимметричной сетке `290px 1fr` с тёплой светлой поверхностью "
                "`oklch(0.968 0.008 82)` и сдержанным бронзовым акцентом `oklch(0.52 0.065 62)`. "
                "В левой колонке закреплён редакционный индекс бюро, в основной зоне — крупная типографика "
                "с отрицательным трекингом, спецификация камня и древесины на семантическом списке `<dl>` "
                "и интерактивный калькулятор площади с живым пересчётом бюджета в `<output>`."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Северная Линия — Архитектурное бюро частных резиденций</title>
<style>
:root {
  --bg: oklch(0.968 0.008 82);
  --surface: oklch(0.942 0.012 80);
  --ink: oklch(0.21 0.012 70);
  --muted: oklch(0.46 0.015 72);
  --accent: oklch(0.50 0.068 62);
  --line: oklch(0.86 0.014 78);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: Georgia, "Times New Roman", serif;
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 100vh;
}
aside.rail {
  border-right: 1px solid var(--line);
  padding: 40px 28px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.brand { font-size: 1.15rem; letter-spacing: 0.14em; text-transform: uppercase; }
.rail nav { display: grid; gap: 14px; font-family: system-ui, sans-serif; font-size: 0.88rem; color: var(--muted); }
.rail nav a { color: inherit; text-decoration: none; }
.rail-meta { font-family: system-ui, sans-serif; font-size: 0.78rem; color: var(--muted); line-height: 1.6; }
main { padding: 44px 56px; display: grid; gap: 36px; align-content: start; }
.eyebrow { font-family: system-ui, sans-serif; font-size: 0.76rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent); }
h1 { font-size: clamp(2.2rem, 3.4vw, 3.2rem); font-weight: 400; line-height: 1.12; letter-spacing: -0.02em; max-width: 18ch; margin-top: 10px; }
.lead { font-family: system-ui, sans-serif; font-size: 1rem; color: var(--muted); max-width: 60ch; line-height: 1.65; margin-top: 14px; }
.showcase { display: grid; grid-template-columns: 1.25fr 1fr; gap: 28px; align-items: stretch; }
.plan-card, .calc-card { background: var(--surface); border: 1px solid var(--line); padding: 26px; display: grid; gap: 18px; }
dl.materials { display: grid; grid-template-columns: auto 1fr; gap: 10px 20px; font-family: system-ui, sans-serif; font-size: 0.88rem; border-top: 1px solid var(--line); padding-top: 16px; }
dt { color: var(--muted); }
dd { font-weight: 500; text-align: right; }
.calc-card label { font-family: system-ui, sans-serif; font-size: 0.84rem; color: var(--muted); display: flex; justify-content: space-between; }
input[type="range"] { width: 100%; accent-color: var(--accent); }
.tier-row { display: flex; gap: 8px; }
.tier-btn { flex: 1; padding: 9px 10px; border: 1px solid var(--line); background: var(--bg); font-family: system-ui, sans-serif; font-size: 0.8rem; cursor: pointer; color: var(--ink); }
.tier-btn[aria-pressed="true"] { border-color: var(--accent); background: var(--accent); color: oklch(0.98 0.005 85); }
.estimate-out { font-size: 1.75rem; color: var(--ink); border-top: 1px solid var(--line); padding-top: 14px; }
@media (max-width: 920px) {
  body { grid-template-columns: 1fr; }
  .showcase { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
  <aside class="rail" aria-label="Индекс бюро">
    <div class="brand">Северная Линия</div>
    <nav aria-label="Разделы">
      <a href="#projects">Избранные резиденции</a>
      <a href="#materials">Материальная палитра</a>
      <a href="#estimate">Предварительная смета</a>
      <a href="#contact">Частная консультация</a>
    </nav>
    <div class="rail-meta">Санкт-Петербург · Карельский перешеек<br>Практика основана в 2014 году</div>
  </aside>
  <main>
    <header id="projects">
      <p class="eyebrow">Монолит · Дерево · Естественный свет</p>
      <h1>Загородная архитектура тишины и выверенных пропорций</h1>
      <p class="lead">Проектируем одноэтажные павильоны и северные усадьбы с полным авторским надзором: от посадки дома по солнечному азимуту до столярных узлов из мореного дуба.</p>
    </header>
    <section class="showcase" id="materials">
      <article class="plan-card">
        <svg viewBox="0 0 420 150" width="100%" height="150" role="img" aria-label="Чертёж фасада павильона Ладога">
          <rect x="8" y="18" width="404" height="114" fill="none" stroke="oklch(0.75 0.02 75)" stroke-width="1"/>
          <line x1="36" y1="112" x2="384" y2="112" stroke="oklch(0.32 0.02 70)" stroke-width="2"/>
          <rect x="64" y="54" width="142" height="58" fill="oklch(0.89 0.018 78)" stroke="oklch(0.45 0.04 65)"/>
          <rect x="206" y="42" width="148" height="70" fill="oklch(0.92 0.014 80)" stroke="oklch(0.45 0.04 65)"/>
          <line x1="48" y1="42" x2="368" y2="42" stroke="oklch(0.50 0.068 62)" stroke-width="3"/>
          <text x="64" y="34" font-size="10" fill="oklch(0.46 0.015 72)" font-family="sans-serif">Отметка карниза +4.200 м</text>
        </svg>
        <dl class="materials">
          <dt>Несущий контур</dt><dd>Архитектурный бетон В30 и клеёная лиственница</dd>
          <dt>Облицовка цоколя</dt><dd>Колотый сердобольский гранит</dd>
          <dt>Остекление</dt><dd>Трёхкамерный тёплый алюминий Rw 44 дБ</dd>
        </dl>
      </article>
      <section class="calc-card" id="estimate" aria-labelledby="calc-heading">
        <h2 id="calc-heading" style="font-size:1.2rem;font-weight:400;">Оценка проектирования и инженерии</h2>
        <label for="area-range"><span>Площадь тёплого контура</span><strong id="area-val">320 м²</strong></label>
        <input id="area-range" type="range" min="180" max="650" step="10" value="320">
        <div class="tier-row" role="group" aria-label="Стадия работ">
          <button type="button" class="tier-btn" data-rate="14500" aria-pressed="true">Архитектура + КР</button>
          <button type="button" class="tier-btn" data-rate="22000" aria-pressed="false">Полный цикл + интерьер</button>
        </div>
        <output id="budget-out" class="estimate-out" for="area-range">4 640 000 ₽</output>
      </section>
    </section>
  </main>
  <script>
    const range = document.getElementById('area-range');
    const areaVal = document.getElementById('area-val');
    const out = document.getElementById('budget-out');
    const btns = document.querySelectorAll('.tier-btn');
    let rate = 14500;
    function update() {
      const m2 = Number(range.value);
      areaVal.textContent = m2 + ' м²';
      out.textContent = new Intl.NumberFormat('ru-RU').format(m2 * rate) + ' ₽';
    }
    range.addEventListener('input', update);
    btns.forEach((btn) => btn.addEventListener('click', () => {
      btns.forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
      rate = Number(btn.dataset.rate);
      update();
    }));
  </script>
</body>
</html>""",
        },
        # 2. RU Editorial Magazine (Desktop 1440x900 -> 1024x640): Urban & Culture Longread
        {
            "key": "ru_canon_editorial_desktop",
            "lang": "ru",
            "subdomain": "canon_editorial_magazine_ru",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "По изображению сверстай журнальный разворот онлайн-издания «Контекст и Форма» "
                "в каноне Editorial Magazine (OKLCH бумага слоновой кости, глубокий чёрный и киноварь). "
                "Используй трёхколоночную газетную шапку, буквицу `::first-letter`, выносную цитату "
                "`<blockquote>`, колонку редакторских сносок `<aside>` и переключатель размера шрифта статьи."
            ),
            "rationale": (
                "Разворот построен по правилам книжно-журнальной вёрстки: трёхчастный мастхед с номером выпуска, "
                "основная колонка чтения `62ch` с выраженной буквицей цвета киновари `oklch(0.53 0.19 29)`, "
                "врезка `<blockquote>` с крупным курсивом и правая полоса маргиналий `<aside>`. "
                "Кнопки управления кеглем меняют CSS-переменную `--body-size` без перестроения сетки."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Контекст и Форма — Выпуск №18: Речные фасады</title>
<style>
:root {
  --paper: oklch(0.975 0.011 88);
  --ink: oklch(0.17 0.01 50);
  --sub: oklch(0.43 0.015 55);
  --vermilion: oklch(0.53 0.19 29);
  --rule: oklch(0.24 0.01 50);
  --thin: oklch(0.83 0.015 82);
  --body-size: 1.05rem;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--paper); color: var(--ink); font-family: Georgia, serif; padding: 28px 52px; }
header.masthead {
  display: grid; grid-template-columns: 1fr auto 1fr; align-items: center;
  border-top: 3px solid var(--rule); border-bottom: 1px solid var(--rule);
  padding: 14px 0; margin-bottom: 32px;
}
.meta-left, .meta-right { font-family: system-ui, sans-serif; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--sub); }
.meta-right { text-align: right; display: flex; gap: 8px; justify-content: flex-end; align-items: center; }
.brand-title { font-size: 1.85rem; letter-spacing: 0.06em; text-transform: uppercase; }
.size-btn { border: 1px solid var(--thin); background: transparent; padding: 4px 9px; cursor: pointer; font-family: system-ui, sans-serif; font-size: 0.76rem; }
.size-btn[aria-pressed="true"] { background: var(--ink); color: var(--paper); }
.spread { display: grid; grid-template-columns: 1.65fr 0.85fr; gap: 44px; }
.rubric { color: var(--vermilion); font-family: system-ui, sans-serif; font-weight: 700; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.15em; }
h1 { font-size: clamp(2.1rem, 3.3vw, 3rem); line-height: 1.08; margin: 10px 0 16px; font-weight: 400; }
.deck { font-size: 1.18rem; color: var(--sub); line-height: 1.5; border-bottom: 1px solid var(--thin); padding-bottom: 18px; margin-bottom: 22px; }
.prose p { font-size: var(--body-size); line-height: 1.72; margin-bottom: 16px; }
.prose p.first::first-letter { float: left; font-size: 3.6rem; line-height: 0.84; padding-right: 10px; color: var(--vermilion); }
blockquote { border-left: 3px solid var(--vermilion); padding-left: 20px; margin: 22px 0; font-style: italic; font-size: 1.24rem; line-height: 1.45; }
aside.marginalia { border-left: 1px solid var(--thin); padding-left: 26px; display: grid; gap: 20px; align-content: start; }
.note { font-family: system-ui, sans-serif; font-size: 0.84rem; line-height: 1.55; color: var(--sub); }
.note strong { color: var(--ink); display: block; margin-bottom: 4px; }
</style>
</head>
<body>
  <header class="masthead">
    <div class="meta-left">Выпуск № 18 · Осень · Урбанистика</div>
    <div class="brand-title">Контекст и Форма</div>
    <div class="meta-right">
      <span>Кегль:</span>
      <button type="button" class="size-btn" data-sz="1.05rem" aria-pressed="true">А</button>
      <button type="button" class="size-btn" data-sz="1.2rem" aria-pressed="false">А+</button>
    </div>
  </header>
  <main class="spread">
    <article class="prose">
      <span class="rubric">Полевое исследование</span>
      <h1>Возвращение к воде: как бывшие грузовые причалы становятся общественными гостиными</h1>
      <p class="deck">Три года наблюдений за реконструкцией набережных показывают: жителям нужны не парадные гранитные эспланады, а тёплые деревянные сходы, защита от ветра и локальный свет.</p>
      <p class="first">Когда портовые краны останавливаются, город внезапно обнаруживает десятки километров закрытого берега. Десятилетиями вода воспринималась исключительно как транспортный коридор или инженерная преграда, отрезанная складскими заборами.</p>
      <blockquote>«Хорошая набережная измеряется не шириной променада, а тем, хочется ли задержаться на ней в ноябрьский вторник при боковом ветре».</blockquote>
      <p>Переход к проницаемым кромкам с дождевыми садами и ступенчатыми амфитеатрами снижает пиковую нагрузку на ливневую сеть на треть и возвращает горожанам тактильный контакт с рекой.</p>
    </article>
    <aside class="marginalia" aria-label="Сноски и инфографика">
      <figure>
        <svg viewBox="0 0 260 120" width="100%" height="120" role="img" aria-label="Профиль ступенчатого берега">
          <path d="M10 30 H95 V58 H165 V86 H250" fill="none" stroke="oklch(0.17 0.01 50)" stroke-width="2.5"/>
          <path d="M165 86 Q205 80 250 86 L250 110 L165 110 Z" fill="oklch(0.76 0.06 230)"/>
          <circle cx="95" cy="30" r="4.5" fill="oklch(0.53 0.19 29)"/>
          <text x="12" y="16" font-size="10" font-family="sans-serif" fill="oklch(0.43 0.015 55)">Ветрозащитный бульвар +3.8 м</text>
        </svg>
      </figure>
      <div class="note"><strong>Сноска 01 · Микроклимат</strong>Линейные посадки ольхи и ивы гасят скорость прибрежных порывов с 9 до 4,2 м/с на уровне пешехода.</div>
      <div class="note"><strong>Сноска 02 · Световая среда</strong>Тёплые низкие опоры 2700 К исключают слепящие блики на тёмной воде и сохраняют ночной силуэт мостов.</div>
    </aside>
  </main>
  <script>
    const root = document.documentElement;
    const sizeBtns = document.querySelectorAll('.size-btn');
    sizeBtns.forEach((b) => b.addEventListener('click', () => {
      sizeBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      root.style.setProperty('--body-size', b.dataset.sz);
    }));
  </script>
</body>
</html>""",
        },
        # 3. RU Brutalist Raw (Desktop 1440x900 -> 1024x640): Industrial Sound Festival
        {
            "key": "ru_canon_brutalist_desktop",
            "lang": "ru",
            "subdomain": "canon_brutalist_raw_ru",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Воспроизведи по скриншоту афишу и расписание фестиваля индустриальной и модульной музыки "
                "«МОДУЛЬ-09» в каноне Brutalist Raw (OKLCH обсидиан, резкий кислотно-лаймовый акцент, "
                "открытая структурная сетка `2px solid`, моноширинная типографика). Обязательна семантическая "
                "таблица `<table>` с фильтрацией выступлений по трём сценам."
            ),
            "rationale": (
                "Вёрстка использует открытую конструктивистскую решётку с жёсткими границами `2px solid` "
                "и высококонтрастной парой `oklch(0.14 0.01 260)` / `oklch(0.88 0.21 128)`. "
                "Расписание сцен оформлено семантической таблицей `<table>` с заголовками `scope=\"col\"` "
                "и мгновенным клиентским фильтром по атрибуту `data-stage`."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>МОДУЛЬ-09 — Фестиваль синтеза и звуковой архитектуры</title>
<style>
:root {
  --bg: oklch(0.14 0.01 260);
  --fg: oklch(0.95 0.01 110);
  --acid: oklch(0.88 0.21 128);
  --dim: oklch(0.68 0.02 260);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--fg); font-family: "Courier New", monospace; padding: 24px; }
.frame { border: 2px solid var(--fg); display: grid; grid-template-columns: 340px 1fr; min-height: calc(100vh - 48px); }
.poster { border-right: 2px solid var(--fg); padding: 24px; display: flex; flex-direction: column; justify-content: space-between; }
.badge { background: var(--acid); color: var(--bg); font-weight: 700; padding: 6px 10px; display: inline-block; font-size: 0.85rem; }
h1 { font-size: 3.1rem; line-height: 0.95; letter-spacing: -0.04em; text-transform: uppercase; margin: 18px 0; }
.coords { font-size: 0.86rem; color: var(--dim); line-height: 1.5; border-top: 2px solid var(--fg); padding-top: 14px; }
.board { display: flex; flex-direction: column; }
.filters { display: flex; border-bottom: 2px solid var(--fg); }
.f-btn { flex: 1; background: var(--bg); color: var(--fg); border: none; border-right: 2px solid var(--fg); padding: 14px; font-family: inherit; font-weight: 700; text-transform: uppercase; cursor: pointer; }
.f-btn:last-child { border-right: none; }
.f-btn[aria-pressed="true"] { background: var(--acid); color: var(--bg); }
table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
th, td { border-bottom: 2px solid var(--fg); padding: 14px 18px; text-align: left; }
th { background: oklch(0.20 0.01 260); color: var(--acid); text-transform: uppercase; font-size: 0.78rem; letter-spacing: 0.1em; }
tr[hidden] { display: none; }
.tag { border: 1px solid var(--acid); color: var(--acid); padding: 2px 7px; font-size: 0.75rem; }
</style>
</head>
<body>
  <div class="frame">
    <header class="poster">
      <div>
        <span class="badge">14–15 НОЯБРЯ · КАБЕЛЬНЫЙ ЦЕХ</span>
        <h1>МОДУЛЬ<br>— 09</h1>
        <p style="line-height:1.5;font-size:0.9rem;">Две ночи аналогового синтеза, квадрафонических инсталляций и генеративного света в машинном зале бывшего завода.</p>
      </div>
      <svg viewBox="0 0 260 90" width="100%" height="90" role="img" aria-label="Осциллограмма модульного сигнала">
        <polyline points="0,45 24,12 48,78 72,12 96,78 120,45 148,18 176,72 204,18 232,72 260,45" fill="none" stroke="oklch(0.88 0.21 128)" stroke-width="3"/>
      </svg>
      <div class="coords">КООРДИНАТЫ: 59.9214° N, 30.2481° E<br>ВХОД СТРОГО С 18 ЛЕТ · ЗВУК 108 ДБ</div>
    </header>
    <main class="board">
      <div class="filters" role="group" aria-label="Фильтр сцен">
        <button type="button" class="f-btn" data-filter="all" aria-pressed="true">Все сцены (5)</button>
        <button type="button" class="f-btn" data-filter="Турбинный зал" aria-pressed="false">Турбинный зал</button>
        <button type="button" class="f-btn" data-filter="Камера 04" aria-pressed="false">Камера 04</button>
        <button type="button" class="f-btn" data-filter="Цех 12" aria-pressed="false">Цех 12</button>
      </div>
      <table aria-label="Расписание выступлений">
        <thead>
          <tr><th scope="col">Время</th><th scope="col">Артист / Проект</th><th scope="col">Сцена</th><th scope="col">Формат</th></tr>
        </thead>
        <tbody>
          <tr data-stage="Турбинный зал"><td>22:00</td><td>Квартет «Спектр-4»</td><td>Турбинный зал</td><td><span class="tag">LIVE BUCHLA</span></td></tr>
          <tr data-stage="Камера 04"><td>23:15</td><td>Нина Холод</td><td>Камера 04</td><td><span class="tag">QUADRO TAPE</span></td></tr>
          <tr data-stage="Цех 12"><td>00:30</td><td>Инженерный Контур</td><td>Цех 12</td><td><span class="tag">EURORACK AV</span></td></tr>
          <tr data-stage="Камера 04"><td>01:45</td><td>Радиошум Севера</td><td>Камера 04</td><td><span class="tag">DRONE ACOUSTIC</span></td></tr>
          <tr data-stage="Турбинный зал"><td>03:00</td><td>Синхрофаза 808</td><td>Турбинный зал</td><td><span class="tag">HYBRID HARDWARE</span></td></tr>
        </tbody>
      </table>
    </main>
  </div>
  <script>
    const fBtns = document.querySelectorAll('.f-btn');
    const rows = document.querySelectorAll('tbody tr');
    fBtns.forEach((btn) => btn.addEventListener('click', () => {
      fBtns.forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
      const target = btn.dataset.filter;
      rows.forEach((r) => { r.hidden = target !== 'all' && r.dataset.stage !== target; });
    }));
  </script>
</body>
</html>""",
        },
        # 4. RU Neo-Swiss Grid (Desktop 1440x900 -> 1024x640): Urban Mobility Analytics
        {
            "key": "ru_canon_neoswiss_desktop",
            "lang": "ru",
            "subdomain": "canon_neo_swiss_grid_ru",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Сверстай по скриншоту аналитическую панель «Институт Городской Мобильности» "
                "в каноне Neo-Swiss Grid (строгая 12-колоночная модульная сетка, нейтральный белый OKLCH, "
                "сигнальный кобальтовый акцент, гротескная типографика с табличными цифрами). "
                "Добавь встроенный `<svg>`-график провозной способности и переключение транспортных коридоров."
            ),
            "rationale": (
                "Применена швейцарская 12-колоночная сетка с модульными ячейками KPI, табличными цифрами "
                "`font-variant-numeric: tabular-nums` и сигнальным акцентом `oklch(0.51 0.19 258)`. "
                "Переключатель коридоров динамически обновляет показатели пассажиропотока, интервала движения "
                "и ширину полос встроенной `<svg>`-диаграммы."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Институт Городской Мобильности — Мониторинг коридоров</title>
<style>
:root {
  --bg: oklch(0.985 0.003 250);
  --card: oklch(0.955 0.006 250);
  --ink: oklch(0.16 0.015 255);
  --muted: oklch(0.46 0.02 255);
  --cobalt: oklch(0.51 0.19 258);
  --grid: oklch(0.86 0.01 255);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--ink); font-family: Inter, system-ui, sans-serif; padding: 32px 44px; font-variant-numeric: tabular-nums; }
.grid-12 { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }
header { border-bottom: 2px solid var(--ink); padding-bottom: 18px; margin-bottom: 24px; }
.code { grid-column: span 3; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--cobalt); }
h1 { grid-column: span 6; font-size: 1.95rem; font-weight: 700; letter-spacing: -0.03em; line-height: 1.1; }
.tabs { grid-column: span 3; display: flex; gap: 6px; justify-content: flex-end; align-items: flex-start; }
.tab { border: 1px solid var(--ink); background: var(--bg); padding: 7px 12px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
.tab[aria-selected="true"] { background: var(--cobalt); border-color: var(--cobalt); color: white; }
.kpi { grid-column: span 4; background: var(--card); border-top: 3px solid var(--ink); padding: 20px; }
.kpi-label { font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }
.kpi-val { font-size: 2.5rem; font-weight: 700; letter-spacing: -0.03em; margin-top: 8px; }
.chart-box { grid-column: span 8; border: 1px solid var(--grid); padding: 22px; }
.note-box { grid-column: span 4; border: 1px solid var(--grid); padding: 22px; display: grid; gap: 12px; align-content: start; }
.note-box p { font-size: 0.9rem; line-height: 1.55; color: var(--muted); }
</style>
</head>
<body>
  <header class="grid-12">
    <div class="code">ИГМ · Отчёт 2026 / Q4</div>
    <h1>Сравнительная эффективность магистральных коридоров</h1>
    <div class="tabs" role="tablist" aria-label="Выбор коридора">
      <button type="button" role="tab" class="tab" data-p="24800" data-i="3,5 мин" data-w="340" aria-selected="true">Трамвай С-Ю</button>
      <button type="button" role="tab" class="tab" data-p="14200" data-i="5,0 мин" data-w="210" aria-selected="false">Экспресс БРТ</button>
    </div>
  </header>
  <main class="grid-12">
    <section class="kpi"><div class="kpi-label">Провозная способность (пик)</div><div class="kpi-val" id="k-pass">24 800 пасс/ч</div></section>
    <section class="kpi"><div class="kpi-label">Тактовый интервал</div><div class="kpi-val" id="k-int">3,5 мин</div></section>
    <section class="kpi"><div class="kpi-label">Пунктуальность рейсов</div><div class="kpi-val">98,4 %</div></section>
    <section class="chart-box" aria-labelledby="ch-title">
      <h2 id="ch-title" style="font-size:1rem;margin-bottom:14px;">Нагрузка на полосу шириной 3,5 метра (чел./час)</h2>
      <svg viewBox="0 0 460 155" width="100%" height="155" role="img" aria-label="Горизонтальная диаграмма провозной способности">
        <text x="0" y="32" font-size="12" font-weight="600" fill="oklch(0.16 0.015 255)">Выделенный рельсовый коридор</text>
        <rect id="bar-main" x="0" y="40" width="340" height="22" fill="oklch(0.51 0.19 258)"/>
        <text x="0" y="88" font-size="12" fill="oklch(0.46 0.02 255)">Обычная полоса смешанного потока</text>
        <rect x="0" y="96" width="58" height="22" fill="oklch(0.72 0.02 255)"/>
        <line x1="0" y1="138" x2="440" y2="138" stroke="oklch(0.82 0.01 255)"/>
      </svg>
    </section>
    <aside class="note-box">
      <h2 style="font-size:1rem;">Методика замера</h2>
      <p>Данные агрегированы с индуктивных петель и датчиков подсчёта на 18 пересадочных узлах в утренний пик 08:00–09:30.</p>
      <p>Обособление путевого полотна и приоритет фазы светофора сокращают разброс времени в пути на 64 %.</p>
    </aside>
  </main>
  <script>
    const tabs = document.querySelectorAll('.tab');
    const kPass = document.getElementById('k-pass');
    const kInt = document.getElementById('k-int');
    const bar = document.getElementById('bar-main');
    tabs.forEach((t) => t.addEventListener('click', () => {
      tabs.forEach((x) => x.setAttribute('aria-selected', String(x === t)));
      kPass.textContent = new Intl.NumberFormat('ru-RU').format(Number(t.dataset.p)) + ' пасс/ч';
      kInt.textContent = t.dataset.i;
      bar.setAttribute('width', t.dataset.w);
    }));
  </script>
</body>
</html>""",
        },
        # 5. RU Tactile Craft (Desktop 1440x900 -> 1024x640): Wood-Fired Ceramics Studio
        {
            "key": "ru_canon_tactile_desktop",
            "lang": "ru",
            "subdomain": "canon_tactile_craft_ru",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Сверстай по изображению страницу мастерской дровяного обжига «Глина и Пепел» "
                "в каноне Tactile Craft (OKLCH необожжённый лён, терракота и шалфей, мягкие скругления, "
                "ощущение ручной фактуры). Включи нумерованный процесс обжига на `<ol>` и интерактивный "
                "выбор зольной глазури с перекраской `<svg>`-сосуда и температурой печи."
            ),
            "rationale": (
                "Тёплая ремесленная палитра в OKLCH сочетает льняной фон `oklch(0.956 0.018 75)`, "
                "терракотовый акцент `oklch(0.56 0.13 42)` и шалфейные плашки. Этапы пятидневного обжига "
                "размечены семантическим списком `<ol>`, а карточки пробников глазури меняют заливку "
                "векторного чайного сосуда и режим выдержки."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Глина и Пепел — Керамика дровяного обжига анагама</title>
<style>
:root {
  --linen: oklch(0.956 0.018 75);
  --clay-card: oklch(0.922 0.024 72);
  --umber: oklch(0.24 0.025 52);
  --muted: oklch(0.46 0.025 58);
  --terracotta: oklch(0.56 0.13 42);
  --border: oklch(0.84 0.028 70);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--linen); color: var(--umber); font-family: Georgia, serif; padding: 34px 52px; }
header { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid var(--border); padding-bottom: 18px; margin-bottom: 30px; }
.studio { font-size: 1.35rem; font-weight: 700; }
.batch-pill { background: var(--clay-card); border: 1px solid var(--border); border-radius: 999px; padding: 6px 14px; font-family: system-ui, sans-serif; font-size: 0.82rem; color: var(--terracotta); }
.layout { display: grid; grid-template-columns: 1.15fr 1fr; gap: 36px; align-items: start; }
h1 { font-size: 2.45rem; line-height: 1.14; font-weight: 400; margin-bottom: 14px; }
.intro { font-family: system-ui, sans-serif; font-size: 0.98rem; line-height: 1.65; color: var(--muted); margin-bottom: 24px; }
ol.kiln-steps { list-style: none; display: grid; gap: 12px; counter-reset: step; }
ol.kiln-steps li { counter-increment: step; background: var(--clay-card); border: 1px solid var(--border); border-radius: 14px; padding: 14px 18px; font-family: system-ui, sans-serif; font-size: 0.88rem; line-height: 1.5; }
ol.kiln-steps li::before { content: "0" counter(step) " · "; font-weight: 700; color: var(--terracotta); }
.glaze-panel { background: var(--clay-card); border: 1px solid var(--border); border-radius: 20px; padding: 26px; display: grid; gap: 18px; justify-items: center; }
.swatches { display: flex; gap: 10px; width: 100%; }
.sw-btn { flex: 1; padding: 10px; border-radius: 10px; border: 1px solid var(--border); background: var(--linen); cursor: pointer; font-family: system-ui, sans-serif; font-size: 0.82rem; }
.sw-btn[aria-pressed="true"] { border-color: var(--terracotta); font-weight: 700; }
.glaze-meta { font-family: system-ui, sans-serif; font-size: 0.86rem; color: var(--muted); text-align: center; }
</style>
</head>
<body>
  <header>
    <div class="studio">Мастерская «Глина и Пепел» · Валдай</div>
    <span class="batch-pill">Обжиг № 14 · Каменная масса и берёзовая зола</span>
  </header>
  <main class="layout">
    <section>
      <h1>Посуда, рождённая живым пламенем и пеплом ста двадцати часов</h1>
      <p class="intro">Мы лепим утварь из дикой гжельской и кембрийской глины и обжигаем её в дровяной печи без химических красителей: летящая зола сама плавится на плечах сосудов в неповторимую глазурь.</p>
      <ol class="kiln-steps">
        <li><strong>Медленный прогрев (0–36 ч):</strong> удаление кристаллической влаги на ольховых дровах до 650 °C.</li>
        <li><strong>Набор свода (36–84 ч):</strong> сосновый горбыль поднимает температуру камеры до 1280 °C, зола оседает на черепке.</li>
        <li><strong>Восстановительная выдержка (84–120 ч):</strong> запечатывание поддувал и плавное остывание с кварцевым переходом.</li>
      </ol>
    </section>
    <section class="glaze-panel" aria-labelledby="glaze-title">
      <h2 id="glaze-title" style="font-size:1.15rem;font-weight:400;">Пробник природной зольной глазури</h2>
      <svg viewBox="0 0 220 180" width="220" height="180" role="img" aria-label="Силуэт керамического чахая">
        <ellipse cx="110" cy="162" rx="54" ry="8" fill="oklch(0.84 0.025 70)"/>
        <path id="vessel-body" d="M68 42 H152 L166 105 Q164 154 110 156 Q56 154 54 105 Z" fill="oklch(0.56 0.13 42)" stroke="oklch(0.24 0.025 52)" stroke-width="2"/>
        <ellipse cx="110" cy="42" rx="42" ry="9" fill="oklch(0.38 0.04 50)"/>
      </svg>
      <div class="swatches" role="group" aria-label="Варианты глазури">
        <button type="button" class="sw-btn" data-color="oklch(0.56 0.13 42)" data-temp="1260 °C · Огненная сторона, тёплый железистый подтёк" aria-pressed="true">Железистый шпат</button>
        <button type="button" class="sw-btn" data-color="oklch(0.62 0.065 145)" data-temp="1295 °C · Восстановительная среда, оливковый селадон золы" aria-pressed="false">Берёзовый пепел</button>
        <button type="button" class="sw-btn" data-color="oklch(0.34 0.03 55)" data-temp="1310 °C · Каменный шлак у топки, матовый базальт" aria-pressed="false">Тёмный шамот</button>
      </div>
      <p class="glaze-meta" id="glaze-desc">1260 °C · Огненная сторона, тёплый железистый подтёк</p>
    </section>
  </main>
  <script>
    const vessel = document.getElementById('vessel-body');
    const desc = document.getElementById('glaze-desc');
    const swBtns = document.querySelectorAll('.sw-btn');
    swBtns.forEach((btn) => btn.addEventListener('click', () => {
      swBtns.forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
      vessel.setAttribute('fill', btn.dataset.color);
      desc.textContent = btn.dataset.temp;
    }));
  </script>
</body>
</html>""",
        },
        # 6. RU Tech Minimal SaaS (Desktop 1440x900 -> 1024x640): Local LLM Telemetry Console
        {
            "key": "ru_canon_tech_saas_desktop",
            "lang": "ru",
            "subdomain": "canon_tech_minimal_saas_ru",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Воспроизведи по скриншоту тёмную инженерную консоль «ВекторПульс» для мониторинга "
                "локального инференса без свопа в каноне Tech Minimal SaaS (тёмный сланец OKLCH, "
                "изумрудный индикатор нормы, тонкие рамки `1px`, моноширинные метрики). Реализуй "
                "переключатель профилей квантования (`IQ3_XXS`, `IQ3_S`, `Q4_K_M`) с обновлением RAM и tok/s."
            ),
            "rationale": (
                "Консоль выстроена на тёмной сланцевой шкале `oklch(0.16 0.015 255)` с тонкими делителями "
                "`oklch(0.27 0.02 255)` и функциональным изумрудным статусом `oklch(0.74 0.16 158)`. "
                "Переключение профиля квантования мгновенно пересчитывает скорость генерации, свободный "
                "остаток физической памяти и индикатор отсутствия обращений к файлу подкачки."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ВекторПульс — Телеметрия локального рантайма MoE</title>
<style>
:root {
  --bg: oklch(0.155 0.015 255);
  --panel: oklch(0.20 0.018 255);
  --line: oklch(0.29 0.02 255);
  --text: oklch(0.95 0.008 250);
  --muted: oklch(0.67 0.018 252);
  --emerald: oklch(0.74 0.16 158);
  --cyan: oklch(0.72 0.13 225);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; padding: 28px 40px; }
.topbar { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); padding-bottom: 16px; margin-bottom: 24px; }
.status { display: flex; align-items: center; gap: 8px; font-size: 0.84rem; color: var(--emerald); font-family: monospace; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--emerald); }
.profiles { display: flex; gap: 8px; }
.p-btn { background: var(--panel); color: var(--muted); border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; font-family: monospace; cursor: pointer; }
.p-btn[aria-pressed="true"] { color: var(--text); border-color: var(--cyan); background: oklch(0.25 0.03 240); }
.metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px; }
.lbl { font-size: 0.78rem; color: var(--muted); margin-bottom: 8px; }
.val { font-family: monospace; font-size: 1.75rem; font-weight: 700; }
.lower { display: grid; grid-template-columns: 1.5fr 1fr; gap: 16px; }
pre { font-family: monospace; font-size: 0.82rem; color: var(--cyan); line-height: 1.6; white-space: pre-wrap; }
</style>
</head>
<body>
  <header class="topbar">
    <div>
      <strong style="font-size:1.15rem;">ВекторПульс · Узел Legion-RTX4080</strong>
      <p style="font-size:0.82rem;color:var(--muted);margin-top:2px;">Контекст 32 768 токенов · Эксперты K=205 в системной памяти mmap</p>
    </div>
    <div class="status"><span class="dot"></span><span id="swap-flag">Pages Output/sec: 0.0 (НУЛЕВОЙ СВОП)</span></div>
  </header>
  <main>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h1 style="font-size:1.45rem;font-weight:600;">Профиль квантования и бюджет физической памяти</h1>
      <div class="profiles" role="group" aria-label="Профиль кванта">
        <button type="button" class="p-btn" data-tps="26.4 tok/s" data-ram="+4.79 GiB" data-vram="5.76 GiB" data-swap="Pages Output/sec: 0.0 (НУЛЕВОЙ СВОП)" aria-pressed="true">IQ3_XXS</button>
        <button type="button" class="p-btn" data-tps="24.1 tok/s" data-ram="+3.38 GiB" data-vram="5.76 GiB" data-swap="Pages Output/sec: 0.0 (НУЛЕВОЙ СВОП)" aria-pressed="false">IQ3_S</button>
        <button type="button" class="p-btn" data-tps="11.2 tok/s" data-ram="+0.42 GiB" data-vram="5.92 GiB" data-swap="РИСК ВЫТЕСНЕНИЯ СТРАНИЦ (<3 GiB)" aria-pressed="false">Q4_K_M</button>
      </div>
    </div>
    <section class="metrics" aria-label="Ключевые показатели">
      <article class="card"><div class="lbl">Скорость генерации</div><div class="val" id="m-tps">26.4 tok/s</div></article>
      <article class="card"><div class="lbl">Свободный запас RAM</div><div class="val" id="m-ram">+4.79 GiB</div></article>
      <article class="card"><div class="lbl">Занято VRAM (32K ctx)</div><div class="val" id="m-vram">5.76 GiB</div></article>
      <article class="card"><div class="lbl">Латентность первого токена</div><div class="val">142 мс</div></article>
    </section>
    <section class="lower">
      <article class="card">
        <div class="lbl">Полоса чтения активных top-10 экспертов (ГБ/с)</div>
        <svg viewBox="0 0 460 125" width="100%" height="125" role="img" aria-label="График пропускной способности памяти">
          <path d="M0 95 L55 82 L110 86 L165 68 L220 72 L275 58 L330 63 L385 52 L460 55 L460 120 L0 120 Z" fill="oklch(0.72 0.13 225 / 0.18)"/>
          <polyline points="0,95 55,82 110,86 165,68 220,72 275,58 330,63 385,52 460,55" fill="none" stroke="oklch(0.72 0.13 225)" stroke-width="2.5"/>
        </svg>
      </article>
      <article class="card">
        <div class="lbl">Проверенный запуск без анонимного репака</div>
        <pre>llama-server --load-mode mmap --lazy-mode on \\
  --no-repack -ngl 99 -c 32768 -np 1 \\
  -ot "\\.ffn_(gate|up|down)_exps\\.weight=CPU"</pre>
      </article>
    </section>
  </main>
  <script>
    const pBtns = document.querySelectorAll('.p-btn');
    const mTps = document.getElementById('m-tps');
    const mRam = document.getElementById('m-ram');
    const mVram = document.getElementById('m-vram');
    const sFlag = document.getElementById('swap-flag');
    pBtns.forEach((b) => b.addEventListener('click', () => {
      pBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      mTps.textContent = b.dataset.tps;
      mRam.textContent = b.dataset.ram;
      mVram.textContent = b.dataset.vram;
      sFlag.textContent = b.dataset.swap;
    }));
  </script>
</body>
</html>""",
        },
        # 7. RU Quiet Luxury Mobile (384x832 -> 576x1248): Bespoke Jewelry Atelier
        {
            "key": "ru_canon_quiet_luxury_mobile",
            "lang": "ru",
            "subdomain": "canon_quiet_luxury_mobile_ru",
            "viewport_w": 384,
            "viewport_h": 832,
            "out_w": 576,
            "out_h": 1248,
            "user_prompt": (
                "По мобильному скриншоту (`576×1248`) сверстай экран ювелирного ателье «Грань и Свет» "
                "в каноне Quiet Luxury. Нужна вертикальная мобильная композиция без горизонтального "
                "скролла, векторная схема огранки изумруда, раскрывающиеся паспорта камня на `<details>` "
                "и выбор благородного сплава оправы с расчётом срока ручной закрепки."
            ),
            "rationale": (
                "Мобильный интерфейс спроектирован под узкий портретный вьюпорт с крупными зонами нажатия "
                "`>= 44px`, тёплым жемчужным фоном `oklch(0.97 0.009 85)` и раскрывающимися карточками "
                "геммологического паспорта `<details>` без лишнего JS."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Грань и Свет — Индивидуальная огранка</title>
<style>
:root {
  --bg: oklch(0.97 0.009 85);
  --card: oklch(0.94 0.013 82);
  --ink: oklch(0.20 0.015 65);
  --muted: oklch(0.46 0.016 68);
  --gold: oklch(0.53 0.075 72);
  --line: oklch(0.85 0.015 80);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--ink); font-family: Georgia, serif; padding: 22px 20px; display: grid; gap: 18px; }
.top { display: flex; justify-content: space-between; align-items: center; font-family: system-ui, sans-serif; font-size: 0.76rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--line); padding-bottom: 12px; }
h1 { font-size: 1.72rem; font-weight: 400; line-height: 1.15; }
.gem-box { background: var(--card); border: 1px solid var(--line); padding: 18px; text-align: center; }
.alloys { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.al-btn { min-height: 44px; border: 1px solid var(--line); background: var(--bg); font-family: system-ui, sans-serif; font-size: 0.82rem; cursor: pointer; }
.al-btn[aria-pressed="true"] { background: var(--ink); color: var(--bg); }
.lead-time { font-family: system-ui, sans-serif; font-size: 0.88rem; color: var(--gold); font-weight: 600; }
details { border-top: 1px solid var(--line); padding: 12px 0; font-family: system-ui, sans-serif; font-size: 0.85rem; }
summary { cursor: pointer; font-weight: 600; list-style: none; display: flex; justify-content: space-between; }
details p { color: var(--muted); line-height: 1.55; margin-top: 8px; }
.cta { min-height: 48px; padding: 10px 18px; background: var(--gold); color: white; border: none; font-family: system-ui, sans-serif; font-size: 0.78rem; letter-spacing: 0.05em; text-transform: uppercase; cursor: pointer; }
</style>
</head>
<body>
  <header class="top"><span>Грань и Свет</span><span>Москва · Петровка</span></header>
  <h1>Кольцо «Ступени Севера» с уральским бериллом</h1>
  <section class="gem-box">
    <svg viewBox="0 0 200 120" width="180" height="110" role="img" aria-label="Схема ступенчатой изумрудной огранки">
      <polygon points="48,16 152,16 176,40 176,80 152,104 48,104 24,80 24,40" fill="oklch(0.88 0.04 165)" stroke="oklch(0.32 0.05 165)" stroke-width="1.6"/>
      <rect x="58" y="34" width="84" height="52" fill="none" stroke="oklch(0.32 0.05 165)" stroke-width="1.2"/>
      <line x1="48" y1="16" x2="58" y2="34" stroke="oklch(0.32 0.05 165)"/>
      <line x1="152" y1="16" x2="142" y2="34" stroke="oklch(0.32 0.05 165)"/>
    </svg>
    <p style="font-family:system-ui,sans-serif;font-size:0.8rem;color:var(--muted);margin-top:6px;">Вес центрального камня 2,45 карата · Чистота VVS1</p>
  </section>
  <section aria-label="Выбор сплава" style="display:grid;gap:10px;">
    <div class="alloys" role="group" aria-label="Сплав оправы">
      <button type="button" class="al-btn" data-msg="Ручная закрепка в платину 950: 21 рабочий день" aria-pressed="true">Платина 950</button>
      <button type="button" class="al-btn" data-msg="Ручная закрепка в жёлтое золото 750: 14 рабочих дней" aria-pressed="false">Золото 750</button>
    </div>
    <p class="lead-time" id="lead-msg">Ручная закрепка в платину 950: 21 рабочий день</p>
  </section>
  <section>
    <details open>
      <summary><span>Происхождение и сертификат</span><span>+</span></summary>
      <p>Природный берилл без термического облагораживания, паспорт Геммологического центра МГУ с лазерной микрогравировкой рундиста.</p>
    </details>
    <details>
      <summary><span>Пожизненный уход в мастерской</span><span>+</span></summary>
      <p>Ежегодная ультразвуковая чистка и проверка крапанов под микроскопом входят в стоимость изделия.</p>
    </details>
  </section>
  <button type="button" class="cta">Записаться на примерку в камерный зал</button>
  <script>
    const alBtns = document.querySelectorAll('.al-btn');
    const msg = document.getElementById('lead-msg');
    alBtns.forEach((b) => b.addEventListener('click', () => {
      alBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      msg.textContent = b.dataset.msg;
    }));
  </script>
</body>
</html>""",
        },
        # 8. RU Tech Minimal SaaS Mobile (384x832 -> 576x1248): Edge Incident Console
        {
            "key": "ru_canon_tech_saas_mobile",
            "lang": "ru",
            "subdomain": "canon_tech_minimal_mobile_ru",
            "viewport_w": 384,
            "viewport_h": 832,
            "out_w": 576,
            "out_h": 1248,
            "user_prompt": (
                "Сверстай по мобильному скриншоту (`576×1248`) дежурный пульт статуса кластеров «КонтурОблако» "
                "в каноне Tech Minimal SaaS (тёмная тема OKLCH, карточки узлов, фильтр только проблемных "
                "регионов и журнал последних переключений трафика)."
            ),
            "rationale": (
                "Компактный мобильный пульт SRE выполнен в тёмной палитре OKLCH без горизонтального переполнения. "
                "Переключатель режима фильтрации скрывает штатные регионы, оставляя узлы с деградацией репликации."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>КонтурОблако — Дежурный пульт SRE</title>
<style>
:root {
  --bg: oklch(0.15 0.015 255);
  --card: oklch(0.205 0.018 255);
  --line: oklch(0.29 0.02 255);
  --fg: oklch(0.95 0.008 250);
  --muted: oklch(0.66 0.018 252);
  --ok: oklch(0.74 0.16 158);
  --warn: oklch(0.78 0.16 78);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--fg); font-family: system-ui, sans-serif; padding: 20px 18px; display: grid; gap: 16px; }
.hdr { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); padding-bottom: 12px; }
.toggle { min-height: 40px; padding: 0 12px; border-radius: 8px; border: 1px solid var(--line); background: var(--card); color: var(--fg); font-size: 0.8rem; cursor: pointer; }
.toggle[aria-pressed="true"] { border-color: var(--warn); color: var(--warn); }
.nodes { display: grid; gap: 10px; }
.node { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px; display: flex; justify-content: space-between; align-items: center; }
.node[hidden] { display: none; }
.pill-ok { color: var(--ok); font-family: monospace; font-size: 0.8rem; }
.pill-warn { color: var(--warn); font-family: monospace; font-size: 0.8rem; }
.log { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px; font-size: 0.8rem; line-height: 1.55; color: var(--muted); display: grid; gap: 8px; }
</style>
</head>
<body>
  <header class="hdr">
    <div>
      <strong style="font-size:1.05rem;">КонтурОблако · SRE</strong>
      <p style="font-size:0.76rem;color:var(--muted);">Обновлено 12 сек назад · SLA 99,96 %</p>
    </div>
    <button type="button" id="warn-only" class="toggle" aria-pressed="false">Только сбои</button>
  </header>
  <h1 style="font-size:1.3rem;">Состояние периферийных узлов</h1>
  <section class="nodes" aria-label="Регионы">
    <article class="node" data-state="ok"><div><strong>ru-msk-01</strong><p style="font-size:0.78rem;color:var(--muted);">p99: 18 мс · Нагрузка 42 %</p></div><span class="pill-ok">НОРМА</span></article>
    <article class="node" data-state="warn"><div><strong>ru-spb-02</strong><p style="font-size:0.78rem;color:var(--muted);">p99: 94 мс · Отставание реплики 1,8 с</p></div><span class="pill-warn">ДЕГРАДАЦИЯ</span></article>
    <article class="node" data-state="ok"><div><strong>ru-ekb-01</strong><p style="font-size:0.78rem;color:var(--muted);">p99: 24 мс · Нагрузка 51 %</p></div><span class="pill-ok">НОРМА</span></article>
    <article class="node" data-state="ok"><div><strong>am-evn-01</strong><p style="font-size:0.78rem;color:var(--muted);">p99: 29 мс · Нагрузка 37 %</p></div><span class="pill-ok">НОРМА</span></article>
  </section>
  <section class="log" aria-label="Журнал автоматики">
    <strong style="color:var(--fg);">Журнал балансировщика</strong>
    <p>00:41:12 — Чтение каталога в ru-spb-02 переведено на резервную реплику без обрыва соединений.</p>
    <p>00:38:05 — Проверка TLS-сертификатов шлюза завершена успешно (остаток 74 дня).</p>
  </section>
  <script>
    const btn = document.getElementById('warn-only');
    const nodes = document.querySelectorAll('.node');
    btn.addEventListener('click', () => {
      const active = btn.getAttribute('aria-pressed') !== 'true';
      btn.setAttribute('aria-pressed', String(active));
      nodes.forEach((n) => { n.hidden = active && n.dataset.state === 'ok'; });
    });
  </script>
</body>
</html>""",
        },
    ]
    return specs + _get_unique_en_multimodal_canon_specs()


def _get_unique_en_multimodal_canon_specs() -> list[dict[str, Any]]:
    """Return 6 strictly 1-of-1 English multimodal OKLCH canon specs (zero shared DOM)."""
    return [
        # 9. EN Quiet Luxury Mobile (384x832 -> 576x1248): Horology Atelier
        {
            "key": "en_canon_quiet_luxury_mobile",
            "lang": "en",
            "subdomain": "canon_quiet_luxury_mobile_en",
            "viewport_w": 384,
            "viewport_h": 832,
            "out_w": 576,
            "out_h": 1248,
            "user_prompt": (
                "Rebuild the attached mobile showcase (`576x1248`) for Geneva independent watchmaker "
                "'Maison Verrier' in the Quiet Luxury OKLCH canon. Include an inline SVG regulator dial "
                "diagram, a case-metal selector updating weight and allocation lead time, and semantic "
                "`<details>` movement specifications with zero horizontal overflow."
            ),
            "rationale": (
                "Built for a narrow mobile viewport using warm parchment OKLCH surfaces (`oklch(0.968 0.008 84)`), "
                "44px+ touch targets for case-metal selection, an inline vector regulator subdial diagram, "
                "and native `<details>` accordions for caliber provenance."
            ),
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Maison Verrier Geneva — Chronometre Souverain</title>
<style>
:root {
  --bg: oklch(0.968 0.008 84);
  --card: oklch(0.938 0.012 80);
  --ink: oklch(0.20 0.012 65);
  --muted: oklch(0.46 0.015 68);
  --bronze: oklch(0.51 0.068 60);
  --line: oklch(0.85 0.014 80);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--ink); font-family: Georgia, serif; padding: 22px 20px; display: grid; gap: 18px; }
.bar { display: flex; justify-content: space-between; font-family: system-ui, sans-serif; font-size: 0.74rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--line); padding-bottom: 12px; }
h1 { font-size: 1.75rem; font-weight: 400; line-height: 1.12; }
.dial-card { background: var(--card); border: 1px solid var(--line); padding: 18px; text-align: center; }
.metals { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.m-btn { min-height: 44px; border: 1px solid var(--line); background: var(--bg); font-family: system-ui, sans-serif; font-size: 0.76rem; cursor: pointer; }
.m-btn[aria-pressed="true"] { background: var(--ink); color: var(--bg); }
.spec-readout { font-family: system-ui, sans-serif; font-size: 0.85rem; color: var(--bronze); font-weight: 600; }
details { border-top: 1px solid var(--line); padding: 11px 0; font-family: system-ui, sans-serif; font-size: 0.84rem; }
summary { cursor: pointer; font-weight: 600; }
details p { color: var(--muted); line-height: 1.55; margin-top: 6px; }
.inquire { min-height: 46px; background: var(--bronze); color: white; border: none; font-family: system-ui, sans-serif; font-size: 0.82rem; letter-spacing: 0.08em; text-transform: uppercase; }
</style>
</head>
<body>
  <header class="bar"><span>Maison Verrier</span><span>Geneva · Rue du Rhone</span></header>
  <h1>Regulateur Calibre MV-14 Hand-Wound</h1>
  <section class="dial-card">
    <svg viewBox="0 0 160 130" width="160" height="130" role="img" aria-label="Regulator dial schematic">
      <circle cx="80" cy="65" r="54" fill="oklch(0.975 0.005 85)" stroke="oklch(0.30 0.02 65)" stroke-width="2"/>
      <circle cx="80" cy="40" r="16" fill="none" stroke="oklch(0.51 0.068 60)" stroke-width="1.4"/>
      <circle cx="80" cy="92" r="13" fill="none" stroke="oklch(0.46 0.015 68)" stroke-width="1.2"/>
      <line x1="80" y1="65" x2="112" y2="44" stroke="oklch(0.20 0.012 65)" stroke-width="1.8"/>
    </svg>
    <p style="font-family:system-ui,sans-serif;font-size:0.78rem;color:var(--muted);margin-top:6px;">38.5 mm diameter · 72-hour twin-barrel reserve</p>
  </section>
  <section style="display:grid;gap:10px;">
    <div class="metals" role="group" aria-label="Case metal">
      <button type="button" class="m-btn" data-spec="Platinum 950 · 94 g · 8 pieces/year" aria-pressed="true">Pt 950</button>
      <button type="button" class="m-btn" data-spec="5N Rose Gold · 78 g · 12 pieces/year" aria-pressed="false">5N Gold</button>
      <button type="button" class="m-btn" data-spec="Grade 5 Titanium · 52 g · 15 pieces/year" aria-pressed="false">Ti G5</button>
    </div>
    <p class="spec-readout" id="metal-out">Platinum 950 · 94 g · 8 pieces/year</p>
  </section>
  <section>
    <details open>
      <summary>Free-sprung balance &amp; finishing</summary>
      <p>German silver bridges bevelled by hand with gentian wood, black-polished steel escape wheel, adjusted in six positions.</p>
    </details>
    <details>
      <summary>Private salon allocation</summary>
      <p>Each movement is numbered and accompanied by an observatory timing certificate signed by the watchmaker.</p>
    </details>
  </section>
  <button type="button" class="inquire">Request Salon Dossier</button>
  <script>
    const mBtns = document.querySelectorAll('.m-btn');
    const mOut = document.getElementById('metal-out');
    mBtns.forEach((b) => b.addEventListener('click', () => {
      mBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      mOut.textContent = b.dataset.spec;
    }));
  </script>
</body>
</html>""",
        },
        # 10. EN Editorial Magazine (Desktop 1440x900 -> 1024x640): Climate Feature Essay
        {
            "key": "en_canon_editorial_desktop",
            "lang": "en",
            "subdomain": "canon_editorial_magazine_en",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Reproduce the attached desktop spread for 'Meridian Dispatch' in the Editorial Magazine "
                "OKLCH canon. Feature a serif headline deck, two-column editorial body with a crimson "
                "pull-rule, an inline `<svg>` North Atlantic anomaly polyline figure, and interactive "
                "horizon scenario buttons (`2026`, `2035`, `2050`)."
            ),
            "rationale": (
                "Structured as an investigative magazine spread on warm newsprint (`oklch(0.974 0.01 86)`) "
                "with a high-chroma crimson editorial rule (`oklch(0.52 0.19 26)`), semantic `<figure>`/`<figcaption>`, "
                "and horizon buttons that dynamically update the projected ocean heat anomaly polyline."
            ),
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meridian Dispatch — The Thermohaline Ledger</title>
<style>
:root {
  --paper: oklch(0.974 0.01 86);
  --ink: oklch(0.17 0.01 50);
  --muted: oklch(0.44 0.015 55);
  --crimson: oklch(0.52 0.19 26);
  --line: oklch(0.83 0.015 80);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--paper); color: var(--ink); font-family: Georgia, serif; padding: 30px 52px; }
header { display: flex; justify-content: space-between; border-bottom: 2px solid var(--ink); padding-bottom: 12px; margin-bottom: 28px; font-family: system-ui, sans-serif; font-size: 0.78rem; letter-spacing: 0.14em; text-transform: uppercase; }
.grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 42px; align-items: start; }
.kicker { color: var(--crimson); font-family: system-ui, sans-serif; font-size: 0.76rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.15em; }
h1 { font-size: 2.55rem; font-weight: 400; line-height: 1.08; margin: 10px 0 14px; }
.standfirst { font-size: 1.12rem; color: var(--muted); line-height: 1.5; margin-bottom: 20px; }
.cols { column-count: 2; column-gap: 24px; font-size: 0.96rem; line-height: 1.68; border-top: 1px solid var(--line); padding-top: 18px; }
figure { background: oklch(0.946 0.014 84); border: 1px solid var(--line); padding: 22px; display: grid; gap: 14px; }
.yr-bar { display: flex; gap: 8px; }
.yr-btn { flex: 1; padding: 7px; border: 1px solid var(--ink); background: transparent; font-family: system-ui, sans-serif; font-size: 0.78rem; font-weight: 600; cursor: pointer; }
.yr-btn[aria-pressed="true"] { background: var(--crimson); border-color: var(--crimson); color: white; }
figcaption { font-family: system-ui, sans-serif; font-size: 0.82rem; color: var(--muted); line-height: 1.5; }
</style>
</head>
<body>
  <header><span>Meridian Dispatch · Vol. XII</span><span>Oceanography &amp; Infrastructure</span></header>
  <main class="grid">
    <article>
      <span class="kicker">Special Report · Subpolar Gyre</span>
      <h1>Deep-Water Moorings Reveal a Quieter Atlantic Conveyor</h1>
      <p class="standfirst">Autonomous Argo floats anchored across the Greenland-Scotland ridge record shifting salinity gradients that reshape port engineering across Northern Europe.</p>
      <div class="cols">
        <p>Across twenty-four deep-sea sensor arrays, winter convection depths have shoaled measurably over the past decade. Coastal municipalities from Bergen to Rotterdam are revising storm-surge return tables accordingly.</p>
        <p style="margin-top:12px;">Rather than relying on static historical baselines, port authorities increasingly couple live mooring telemetry directly into tidal barrier maintenance schedules.</p>
      </div>
    </article>
    <figure>
      <div class="yr-bar" role="group" aria-label="Projection horizon">
        <button type="button" class="yr-btn" data-pts="10,115 85,102 160,94 235,80 310,72" data-cap="2026 Observed Baseline: +0.64 °C upper-layer anomaly across 55°N transect." aria-pressed="true">2026 Observed</button>
        <button type="button" class="yr-btn" data-pts="10,115 85,96 160,78 235,58 310,44" data-cap="2035 Moderate Pathway: +0.92 °C anomaly with 11% overturning slowdown." aria-pressed="false">2035 Pathway</button>
        <button type="button" class="yr-btn" data-pts="10,115 85,88 160,62 235,38 310,22" data-cap="2050 High-Forcing Envelope: +1.38 °C anomaly requiring +45 cm quay elevation." aria-pressed="false">2050 High</button>
      </div>
      <svg viewBox="0 0 320 135" width="100%" height="135" role="img" aria-label="Thermal anomaly trendline">
        <line x1="10" y1="120" x2="310" y2="120" stroke="oklch(0.75 0.01 80)"/>
        <polyline id="trend" points="10,115 85,102 160,94 235,80 310,72" fill="none" stroke="oklch(0.52 0.19 26)" stroke-width="3"/>
      </svg>
      <figcaption id="fig-cap">2026 Observed Baseline: +0.64 °C upper-layer anomaly across 55°N transect.</figcaption>
    </figure>
  </main>
  <script>
    const btns = document.querySelectorAll('.yr-btn');
    const poly = document.getElementById('trend');
    const cap = document.getElementById('fig-cap');
    btns.forEach((b) => b.addEventListener('click', () => {
      btns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      poly.setAttribute('points', b.dataset.pts);
      cap.textContent = b.dataset.cap;
    }));
  </script>
</body>
</html>""",
        },
        # 11. EN Brutalist Raw Mobile (384x832 -> 576x1248): Type Foundry Specimen
        {
            "key": "en_canon_brutalist_mobile",
            "lang": "en",
            "subdomain": "canon_brutalist_raw_mobile_en",
            "viewport_w": 384,
            "viewport_h": 832,
            "out_w": 576,
            "out_h": 1248,
            "user_prompt": (
                "Implement the attached mobile specimen sheet (`576x1248`) for independent foundry "
                "'Kinetik Type Lab' in the Brutalist Raw OKLCH canon. Use stark black/off-white `2px` "
                "structural borders, signal orange highlights, a live editable specimen `<input>`, "
                "weight switcher buttons (`300`, `500`, `800`), and a seat-licensing table."
            ),
            "rationale": (
                "Utilitarian mobile type specimen with zero decorative shadows, exposed `2px solid` "
                "dividers, signal orange OKLCH accent (`oklch(0.68 0.20 42)`), and live font-weight "
                "manipulation on an editable pangram input."
            ),
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kinetik Type Lab — KT Grotesque Mono</title>
<style>
:root {
  --bg: oklch(0.96 0.006 90);
  --ink: oklch(0.13 0.01 260);
  --sig: oklch(0.68 0.20 42);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--ink); font-family: "Courier New", monospace; padding: 16px; }
.sheet { border: 2px solid var(--ink); display: grid; }
.row { border-bottom: 2px solid var(--ink); padding: 14px; }
.row:last-child { border-bottom: none; }
.stamp { background: var(--sig); color: var(--ink); font-weight: 700; padding: 3px 8px; font-size: 0.75rem; display: inline-block; }
h1 { font-size: 2.1rem; line-height: 0.98; text-transform: uppercase; margin-top: 10px; }
.w-bar { display: grid; grid-template-columns: repeat(3, 1fr); border-bottom: 2px solid var(--ink); }
.w-btn { min-height: 44px; border: none; border-right: 2px solid var(--ink); background: var(--bg); font-family: system-ui, sans-serif; font-weight: 700; cursor: pointer; }
.w-btn:last-child { border-right: none; }
.w-btn[aria-pressed="true"] { background: var(--ink); color: var(--bg); }
.tester { width: 100%; border: 2px solid var(--ink); padding: 12px; font-family: system-ui, sans-serif; font-size: 1.55rem; font-weight: 500; background: white; }
table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
th, td { border-bottom: 1px solid var(--ink); padding: 9px 4px; text-align: left; }
</style>
</head>
<body>
  <main class="sheet">
    <header class="row">
      <span class="stamp">SPECIMEN REV 4.2 · WOFF2</span>
      <h1>KT SIGNAL<br>GROTESK</h1>
      <p style="font-size:0.78rem;margin-top:8px;">492 GLYPHS · TABULAR FIGURES · OPEN LICENSE</p>
    </header>
    <div class="w-bar" role="group" aria-label="Font weight">
      <button type="button" class="w-btn" data-w="300" aria-pressed="false">LIGHT 300</button>
      <button type="button" class="w-btn" data-w="500" aria-pressed="true">MEDIUM 500</button>
      <button type="button" class="w-btn" data-w="800" aria-pressed="false">HEAVY 800</button>
    </div>
    <section class="row" aria-label="Interactive specimen">
      <label for="spec-in" style="font-size:0.72rem;display:block;margin-bottom:6px;">LIVE GLYPH TESTER:</label>
      <input id="spec-in" class="tester" type="text" value="0194 AXIOM GRID">
    </section>
    <section class="row">
      <table aria-label="Commercial seat tiers">
        <thead><tr><th scope="col">TIER</th><th scope="col">SEATS</th><th scope="col">PERPETUAL</th></tr></thead>
        <tbody>
          <tr><td>STUDIO</td><td>1–5</td><td>$140</td></tr>
          <tr><td>AGENCY</td><td>6–25</td><td>$380</td></tr>
          <tr><td>UNLIMITED</td><td>GLOBAL</td><td>$890</td></tr>
        </tbody>
      </table>
    </section>
  </main>
  <script>
    const wBtns = document.querySelectorAll('.w-btn');
    const inp = document.getElementById('spec-in');
    wBtns.forEach((b) => b.addEventListener('click', () => {
      wBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      inp.style.fontWeight = b.dataset.w;
    }));
  </script>
</body>
</html>""",
        },
        # 12. EN Neo-Swiss Grid (Desktop 1440x900 -> 1024x640): Precision Optical Metrology
        {
            "key": "en_canon_neoswiss_desktop",
            "lang": "en",
            "subdomain": "canon_neo_swiss_grid_en",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Code the attached desktop product datasheet for 'Helvetia Metrology AG' in the "
                "Neo-Swiss Grid OKLCH canon. Use an objective 12-column grid, international red accent, "
                "`@container` modular cards, an ISO tolerance `<table>`, and a metric/imperial (`um` / `mil`) "
                "unit converter toggle."
            ),
            "rationale": (
                "Implements a strict 12-column Swiss industrial specification sheet with tabular numerals, "
                "`@container` responsive cards, signal red (`oklch(0.55 0.21 28)`), and deterministic "
                "unit conversion between micrometers and thousandths of an inch."
            ),
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Helvetia Metrology AG — Interferometer Series H-90</title>
<style>
:root {
  --bg: oklch(0.985 0.002 250);
  --surface: oklch(0.952 0.005 250);
  --ink: oklch(0.15 0.01 255);
  --muted: oklch(0.45 0.015 255);
  --swiss-red: oklch(0.55 0.21 28);
  --rule: oklch(0.84 0.01 255);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--ink); font-family: Helvetica, Arial, sans-serif; padding: 32px 48px; font-variant-numeric: tabular-nums; }
.g12 { display: grid; grid-template-columns: repeat(12, 1fr); gap: 18px; }
header { border-bottom: 3px solid var(--ink); padding-bottom: 18px; margin-bottom: 26px; }
.ref { grid-column: span 3; color: var(--swiss-red); font-weight: 700; font-size: 0.82rem; letter-spacing: 0.08em; }
h1 { grid-column: span 6; font-size: 2rem; letter-spacing: -0.03em; line-height: 1.08; }
.unit-switch { grid-column: span 3; display: flex; justify-content: flex-end; align-items: flex-start; gap: 6px; }
.u-btn { border: 1px solid var(--ink); background: var(--bg); padding: 7px 14px; font-weight: 700; font-size: 0.78rem; cursor: pointer; }
.u-btn[aria-pressed="true"] { background: var(--swiss-red); border-color: var(--swiss-red); color: white; }
.card-wrap { grid-column: span 5; container-type: inline-size; display: grid; gap: 14px; }
.spec-card { background: var(--surface); border-left: 4px solid var(--swiss-red); padding: 18px; }
@container (min-width: 260px) { .spec-val { font-size: 2.1rem; font-weight: 700; margin-top: 6px; } }
.matrix { grid-column: span 7; border: 1px solid var(--rule); padding: 20px; }
table { width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-top: 12px; }
th, td { border-bottom: 1px solid var(--rule); padding: 11px 8px; text-align: left; }
th { font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }
</style>
</head>
<body>
  <header class="g12">
    <div class="ref">DOC 904-CH · ISO 10360</div>
    <h1>White-Light Optical Interferometer H-90</h1>
    <div class="unit-switch" role="group" aria-label="Measurement unit">
      <button type="button" class="u-btn" data-unit="um" aria-pressed="true">Metric (µm)</button>
      <button type="button" class="u-btn" data-unit="mil" aria-pressed="false">Imperial (mil)</button>
    </div>
  </header>
  <main class="g12">
    <section class="card-wrap" aria-label="Primary tolerances">
      <article class="spec-card"><div style="font-size:0.78rem;color:var(--muted);">AXIAL REPEATABILITY (2σ)</div><div class="spec-val" data-um="0.08 µm" data-mil="0.0031 mil">0.08 µm</div></article>
      <article class="spec-card"><div style="font-size:0.78rem;color:var(--muted);">WORKING STANDOFF</div><div class="spec-val" data-um="42 000 µm" data-mil="1 653.5 mil">42 000 µm</div></article>
    </section>
    <section class="matrix">
      <h2 style="font-size:1rem;">Calibrated Sensor Aperture Matrix</h2>
      <table>
        <thead><tr><th scope="col">Model</th><th scope="col">Field of View</th><th scope="col">Max Slope</th><th scope="col">Sampling</th></tr></thead>
        <tbody>
          <tr><td>H-90 / N10</td><td data-um="1 200 µm" data-mil="47.2 mil">1 200 µm</td><td>28°</td><td>12.4 kHz</td></tr>
          <tr><td>H-90 / N25</td><td data-um="480 µm" data-mil="18.9 mil">480 µm</td><td>42°</td><td>12.4 kHz</td></tr>
          <tr><td>H-90 / N50</td><td data-um="240 µm" data-mil="9.4 mil">240 µm</td><td>53°</td><td>24.0 kHz</td></tr>
        </tbody>
      </table>
    </section>
  </main>
  <script>
    const uBtns = document.querySelectorAll('.u-btn');
    const conv = document.querySelectorAll('[data-um]');
    uBtns.forEach((b) => b.addEventListener('click', () => {
      uBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      const key = b.dataset.unit;
      conv.forEach((el) => { el.textContent = el.dataset[key]; });
    }));
  </script>
</body>
</html>""",
        },
        # 13. EN Tactile Craft (Desktop 1440x900 -> 1024x640): Micro-Roastery Brew Guide
        {
            "key": "en_canon_tactile_desktop",
            "lang": "en",
            "subdomain": "canon_tactile_craft_en",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Build the attached desktop page for single-origin roastery 'Loam & Ember' in the "
                "Tactile Craft OKLCH canon. Include warm oat/espresso/sage OKLCH tokens, an inline `<svg>` "
                "5-axis sensory tasting polygon, provenance lot metadata, and an interactive pour-over "
                "dose-to-water ratio calculator (`1:16`)."
            ),
            "rationale": (
                "Uses warm tactile surfaces (`oklch(0.958 0.017 78)`), rounded organic cards, an inline "
                "5-point SVG sensory polygon, and a live pour-over water yield calculator."
            ),
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Loam &amp; Ember — Washed Pink Bourbon Lot 07</title>
<style>
:root {
  --oat: oklch(0.958 0.017 78);
  --card: oklch(0.925 0.022 75);
  --roast: oklch(0.23 0.028 48);
  --muted: oklch(0.46 0.025 54);
  --sage: oklch(0.48 0.075 148);
  --clay: oklch(0.55 0.12 45);
  --line: oklch(0.84 0.024 72);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--oat); color: var(--roast); font-family: Georgia, serif; padding: 34px 50px; }
header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); padding-bottom: 16px; margin-bottom: 28px; }
.pill { background: var(--sage); color: white; padding: 5px 14px; border-radius: 999px; font-family: system-ui, sans-serif; font-size: 0.78rem; }
.cols { display: grid; grid-template-columns: 1.15fr 1fr; gap: 34px; }
h1 { font-size: 2.4rem; font-weight: 400; line-height: 1.12; margin-bottom: 12px; }
.notes { font-family: system-ui, sans-serif; color: var(--muted); line-height: 1.6; margin-bottom: 20px; }
.calc { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 20px; font-family: system-ui, sans-serif; display: grid; gap: 12px; }
.radar { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 24px; text-align: center; }
input[type="number"] { padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px; font-size: 1rem; width: 96px; background: var(--oat); }
</style>
</head>
<body>
  <header>
    <strong style="font-size:1.3rem;">Loam &amp; Ember Roasters · Portland</strong>
    <span class="pill">Harvest 2026 · Huila, Colombia · 1,920 masl</span>
  </header>
  <main class="cols">
    <section>
      <h1>Finca El Mirador — Washed Pink Bourbon</h1>
      <p class="notes">Fermented 36 hours in ceramic tanks and dried under parabolic shade canopies. Expect blood orange acidity, wildflower honey sweetness, and a clean black-tea finish.</p>
      <div class="calc">
        <strong>V60 Pour-Over Brew Calculator (1:16 Ratio)</strong>
        <label for="dose-in" style="display:flex;justify-content:space-between;align-items:center;">
          <span>Dry coffee dose (grams):</span>
          <input id="dose-in" type="number" min="10" max="60" value="18">
        </label>
        <p style="font-size:0.92rem;color:var(--clay);font-weight:600;" id="brew-out">Target water: 288 ml · Bloom: 54 ml for 40 s</p>
      </div>
    </section>
    <section class="radar" aria-label="Sensory profile">
      <h2 style="font-size:1.05rem;font-weight:400;margin-bottom:10px;">Cupping Wheel Profile</h2>
      <svg viewBox="0 0 220 185" width="220" height="185" role="img" aria-label="Five-axis sensory polygon">
        <polygon points="110,20 190,72 160,158 60,158 30,72" fill="none" stroke="oklch(0.80 0.02 72)"/>
        <polygon points="110,32 176,78 148,144 72,138 48,76" fill="oklch(0.55 0.12 45 / 0.28)" stroke="oklch(0.55 0.12 45)" stroke-width="2.2"/>
        <text x="90" y="14" font-size="10" font-family="sans-serif">Acidity</text>
        <text x="188" y="70" font-size="10" font-family="sans-serif">Sweet</text>
        <text x="155" y="174" font-size="10" font-family="sans-serif">Body</text>
        <text x="38" y="174" font-size="10" font-family="sans-serif">Florals</text>
        <text x="2" y="70" font-size="10" font-family="sans-serif">Finish</text>
      </svg>
    </section>
  </main>
  <script>
    const doseIn = document.getElementById('dose-in');
    const brewOut = document.getElementById('brew-out');
    doseIn.addEventListener('input', () => {
      const g = Math.max(8, Number(doseIn.value) || 18);
      brewOut.textContent = 'Target water: ' + (g * 16) + ' ml · Bloom: ' + (g * 3) + ' ml for 40 s';
    });
  </script>
</body>
</html>""",
        },
        # 14. EN Tech Minimal SaaS (Desktop 1440x900 -> 1024x640): Serverless Postgres Branching
        {
            "key": "en_canon_tech_saas_desktop",
            "lang": "en",
            "subdomain": "canon_tech_minimal_saas_en",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Recreate the attached dark developer landing section for 'BranchDB' in the Tech Minimal "
                "SaaS OKLCH canon. Include copy-on-write Postgres CLI workflow tabs (`create`, `diff`, "
                "`promote`), a syntax-styled `<pre><code>` terminal card, and regional NVMe snapshot latency cards."
            ),
            "rationale": (
                "Developer-focused dark slate OKLCH palette (`oklch(0.15 0.014 258)`) with crisp `1px` "
                "hairline borders, interactive CLI workflow tabs updating the terminal output, and "
                "zero-bloat semantic layout."
            ),
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BranchDB — Copy-on-Write Postgres Branching</title>
<style>
:root {
  --bg: oklch(0.15 0.014 258);
  --card: oklch(0.195 0.016 258);
  --line: oklch(0.285 0.02 258);
  --fg: oklch(0.96 0.006 250);
  --muted: oklch(0.66 0.018 252);
  --accent: oklch(0.73 0.15 195);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--fg); font-family: system-ui, -apple-system, sans-serif; padding: 32px 48px; }
header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); padding-bottom: 16px; margin-bottom: 28px; }
.grid { display: grid; grid-template-columns: 1.05fr 1.2fr; gap: 32px; align-items: start; }
h1 { font-size: 2.3rem; letter-spacing: -0.03em; line-height: 1.1; margin-bottom: 14px; }
.sub { color: var(--muted); line-height: 1.6; margin-bottom: 22px; }
.regions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.reg { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 12px; font-family: monospace; font-size: 0.8rem; }
.term { background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.t-tabs { display: flex; border-bottom: 1px solid var(--line); }
.t-btn { flex: 1; padding: 11px; background: transparent; color: var(--muted); border: none; border-right: 1px solid var(--line); font-family: monospace; font-size: 0.8rem; cursor: pointer; }
.t-btn:last-child { border-right: none; }
.t-btn[aria-selected="true"] { color: var(--accent); background: oklch(0.23 0.022 250); font-weight: 700; }
pre { padding: 20px; font-family: monospace; font-size: 0.84rem; line-height: 1.65; color: var(--accent); white-space: pre-wrap; }
</style>
</head>
<body>
  <header>
    <strong style="font-family:monospace;font-size:1.1rem;">BranchDB // Postgres 17 NVMe</strong>
    <span style="font-family:monospace;font-size:0.8rem;color:var(--accent);">COW Fork Time: 118 ms</span>
  </header>
  <main class="grid">
    <section>
      <h1>Isolated Postgres branches for every pull request</h1>
      <p class="sub">Fork 4 TB production clusters in milliseconds using copy-on-write storage pages. Run destructive migrations safely before merging.</p>
      <div class="regions" aria-label="Edge storage regions">
        <div class="reg"><strong>eu-central-1</strong><br><span style="color:var(--muted);">RTT 9.4 ms</span></div>
        <div class="reg"><strong>us-east-1</strong><br><span style="color:var(--muted);">RTT 11.2 ms</span></div>
        <div class="reg"><strong>ap-northeast</strong><br><span style="color:var(--muted);">RTT 14.8 ms</span></div>
      </div>
    </section>
    <section class="term" aria-label="CLI workflow preview">
      <div class="t-tabs" role="tablist">
        <button type="button" role="tab" class="t-btn" data-cmd="$ bdb branch create pr-418 --from main&#10;Created branch pr-418 (lsn 0/48A91C0) in 118 ms&#10;DSN: postgres://app@pr-418.db.internal:5432/core" aria-selected="true">1. fork</button>
        <button type="button" role="tab" class="t-btn" data-cmd="$ bdb schema diff pr-418 main&#10;+ CREATE INDEX CONCURRENTLY idx_orders_tenant ON orders(tenant_id);&#10;Zero lock contention detected (estimated 0 ms table rewrite)." aria-selected="false">2. diff</button>
        <button type="button" role="tab" class="t-btn" data-cmd="$ bdb branch promote pr-418&#10;Applied 1 DDL change cleanly · Checksums verified." aria-selected="false">3. promote</button>
      </div>
      <pre><code id="cli-out">$ bdb branch create pr-418 --from main
Created branch pr-418 (lsn 0/48A91C0) in 118 ms
DSN: postgres://app@pr-418.db.internal:5432/core</code></pre>
    </section>
  </main>
  <script>
    const tBtns = document.querySelectorAll('.t-btn');
    const cli = document.getElementById('cli-out');
    tBtns.forEach((b) => b.addEventListener('click', () => {
      tBtns.forEach((x) => x.setAttribute('aria-selected', String(x === b)));
      cli.textContent = b.dataset.cmd;
    }));
  </script>
</body>
</html>""",
        },
    ]


def get_unique_pillar2_bundles() -> list[dict[str, Any]]:
    """Return 8 strictly 1-of-1 `llms.txt` + CSP `_headers` + `robots.txt` + `@graph` JSON-LD bundles (4 RU + 4 EN).

    Zero HTML skeletons are included — each item calibrates structured SEO/GEO discovery files
    and strict HTTP security headers for a distinct Schema.org industry vertical.
    """
    return [
        {
            "key": "p2_ru_clinic_geo_csp",
            "lang": "ru",
            "subdomain": "seo_geo_csp_bundle_ru",
            "user_prompt": (
                "Подготовь полный комплект файлов поисковой и ИИ-индексации (`llms.txt`, `robots.txt`, "
                "`_headers` со строгим хешевым CSP без `'unsafe-inline'` и блок Schema.org `@graph` JSON-LD) "
                "для сайта клиники челюстно-лицевой стоматологии «ДентаСфера» в Санкт-Петербурге."
            ),
            "assistant_content": """Ниже приведён согласованный комплект конфигурационных файлов для медицинского центра «ДентаСфера». Разметка `@graph` связывает сущность `Dentist` с расписанием приёма, лицензией и перечнем хирургических услуг, а политика `Content-Security-Policy` блокирует сторонние скрипты и инъекции.

### 1. `llms.txt` (спецификация GEO для генеративных поисковых систем)
```markdown
# Клиника челюстно-лицевой стоматологии «ДентаСфера»

> Специализированный центр цифровой имплантации, микроскопной эндодонтии и гнатологии в Санкт-Петербурге (Петроградская сторона). Приём ведут хирурги со стажем от 12 лет по КЛКТ-навигации.

## Основные разделы
- [Хирургия и навигационная имплантация](https://dentasfera.spb.ru/implantology): протоколы одномоментной нагрузки, хирургические шаблоны и прейскурант под ключ.
- [Лечение каналов под микроскопом](https://dentasfera.spb.ru/endodontics): ревизия сложных корневых каналов с увеличением 25x.
- [Врачи и медицинские лицензии](https://dentasfera.spb.ru/doctors): реестровый номер лицензии Росздравнадзора, дипломы и график приёма.
- [Памятки пациентам до и после операции](https://dentasfera.spb.ru/guides): противопоказания, подготовка к КЛКТ и режим реабилитации.
```

### 2. `robots.txt`
```text
User-agent: *
Allow: /
Disallow: /cabinet/
Disallow: /api/appointments/

User-agent: GPTBot
Allow: /llms.txt
Allow: /implantology
Allow: /endodontics
Disallow: /cabinet/

User-agent: ClaudeBot
Allow: /

Sitemap: https://dentasfera.spb.ru/sitemap.xml
```

### 3. `_headers` (строгие заголовки безопасности HTTP)
```text
/*
  Content-Security-Policy: default-src 'none'; script-src 'self' 'sha256-K9mP4vR2x8LqT1wZ7nC5bJ0yF3hD6gS8aE4uV1cM9oI='; style-src 'self' 'sha256-W3pL8nQ1vX5zR9mK2tB6cY4fH7jD0sA9eG1wU5iN8kE='; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Cross-Origin-Opener-Policy: same-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
```

### 4. Структурированные данные Schema.org (`@graph` JSON-LD)
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Dentist",
      "@id": "https://dentasfera.spb.ru/#clinic",
      "name": "Клиника челюстно-лицевой стоматологии «ДентаСфера»",
      "url": "https://dentasfera.spb.ru/",
      "telephone": "+7-812-555-01-48",
      "priceRange": "₽₽₽",
      "medicalSpecialty": ["Dentistry", "OralSurgery"],
      "address": {
        "@type": "PostalAddress",
        "streetAddress": "Большой проспект П.С., д. 74",
        "addressLocality": "Санкт-Петербург",
        "postalCode": "197136",
        "addressCountry": "RU"
      },
      "openingHoursSpecification": [
        {
          "@type": "OpeningHoursSpecification",
          "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
          "opens": "09:00",
          "closes": "21:00"
        }
      ]
    },
    {
      "@type": "MedicalProcedure",
      "@id": "https://dentasfera.spb.ru/implantology#procedure",
      "name": "Дентальная имплантация по навигационному хирургическому шаблону",
      "procedureType": "https://schema.org/SurgicalProcedure",
      "howPerformed": "Трёхмерное планирование по КЛКТ с установкой титанового имплантата без разреза лоскута",
      "provider": { "@id": "https://dentasfera.spb.ru/#clinic" }
    }
  ]
}
```""",
        },
        {
            "key": "p2_ru_course_edtech_geo_csp",
            "lang": "ru",
            "subdomain": "seo_geo_csp_bundle_ru",
            "user_prompt": (
                "Составь производственный набор `llms.txt`, `robots.txt`, `_headers` и JSON-LD `@graph` "
                "(`EducationalOrganization` + `Course` + `FAQPage`) для инженерной школы системного "
                "программирования «ЯдроПрактикум» с защитой от кликджекинга и утечки токенов в `Referer`."
            ),
            "assistant_content": """Ниже подготовлен комплект для образовательной платформы «ЯдроПрактикум». Личные кабинеты студентов и временные ссылки сброса пароля закрыты от индексации и защищены политикой `Referrer-Policy: no-referrer` на маршрутах авторизации.

### 1. `llms.txt`
```markdown
# Инженерная школа «ЯдроПрактикум»

> Практические программы повышения квалификации для разработчиков по компиляторам, ядру Linux, сетевым протоколам и высоконагруженным СУБД на русском языке.

## Учебные потоки
- [Внутреннее устройство PostgreSQL и хранение данных](https://yadro-edu.ru/courses/postgres-internals): буферный пул, WAL, MVCC и профилирование планов запросов (10 недель).
- [Сетевой стек Linux и eBPF](https://yadro-edu.ru/courses/ebpf-networking): XDP-фильтры, трассировка сокетов и диагностика задержек p99 (8 недель).
- [Программа и требования к поступающим](https://yadro-edu.ru/admissions): вступительное тестирование, формат код-ревью и образец удостоверения.
```

### 2. `robots.txt`
```text
User-agent: *
Allow: /courses/
Allow: /admissions
Allow: /llms.txt
Disallow: /lms/
Disallow: /auth/

Sitemap: https://yadro-edu.ru/sitemap.xml
```

### 3. `_headers`
```text
/*
  Content-Security-Policy: default-src 'self'; script-src 'self' 'sha256-R8tY2vN6mK1pQ4xZ9wL3bC7fJ5hD0gS2aE8uV4cM6oA='; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; object-src 'none'; base-uri 'self'
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin

/auth/*
  Referrer-Policy: no-referrer
  Cache-Control: no-store
```

### 4. Schema.org `@graph` JSON-LD
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "EducationalOrganization",
      "@id": "https://yadro-edu.ru/#org",
      "name": "ЯдроПрактикум",
      "url": "https://yadro-edu.ru/"
    },
    {
      "@type": "Course",
      "@id": "https://yadro-edu.ru/courses/postgres-internals#course",
      "name": "Внутреннее устройство PostgreSQL и хранение данных",
      "description": "Инженерный курс по архитектуре страниц, журналу предзаписи WAL, блокировкам и оптимизации запросов.",
      "provider": { "@id": "https://yadro-edu.ru/#org" },
      "inLanguage": "ru",
      "hasCourseInstance": {
        "@type": "CourseInstance",
        "courseMode": "online",
        "courseWorkload": "PT80H"
      }
    },
    {
      "@type": "FAQPage",
      "@id": "https://yadro-edu.ru/admissions#faq",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "Как проверяются лабораторные работы?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Каждая работа проходит автоматический стенд нагрузочных тестов и ручное ревью действующим системным архитектором."
          }
        }
      ]
    }
  ]
}
```""",
        },
        {
            "key": "p2_ru_ecommerce_tea_geo_csp",
            "lang": "ru",
            "subdomain": "seo_geo_csp_bundle_ru",
            "user_prompt": (
                "Разработай `llms.txt`, `robots.txt`, `sitemap.xml`, `_headers` и JSON-LD `@graph` "
                "(`Store` + `Product` + `Offer` + `BreadcrumbList`) для интернет-магазина фермерского "
                "чая «Высокогорный Лист» с корректной фильтрацией фасетных URL в `robots.txt`."
            ),
            "assistant_content": """Для магазина с фасетным каталогом критично закрыть комбинаторные GET-параметры сортировки и фильтров в `robots.txt`, оставив открытыми канонические страницы сортов и `llms.txt`.

### 1. `llms.txt`
```markdown
# Чайная компания «Высокогорный Лист»

> Прямые поставки односортового улуна, красного чая и выдержанного пуэра малых хозяйств Юньнани, Фуцзяни и Тайваня с лабораторным контролем остаточных пестицидов.

## Каталог и руководства
- [Тайваньские высокогорные улуны](https://mountainleaf.ru/catalog/taiwan-oolong): сборы Лишань и Алишань весеннего и зимнего урожая.
- [Юньнаньский шэн и шу пуэр](https://mountainleaf.ru/catalog/puerh): прессованные блины с указанием года сырья и деревни сбора.
- [Таблица температур и проливов заваривания](https://mountainleaf.ru/brewing-guide): граммовка для гайвани, исинского чайника и настаивания.
- [Доставка и хранение](https://mountainleaf.ru/shipping): вакуумная упаковка с азотом и сроки отгрузки по РФ.
```

### 2. `robots.txt` (защита краулингового бюджета от фасетных дублей)
```text
User-agent: *
Allow: /catalog/
Allow: /brewing-guide
Allow: /llms.txt
Disallow: /cart
Disallow: /checkout
Disallow: /*?sort=
Disallow: /*?price_min=
Disallow: /*&filter=

Sitemap: https://mountainleaf.ru/sitemap.xml
```

### 3. `sitemap.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://mountainleaf.ru/</loc><lastmod>2026-11-01</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>
  <url><loc>https://mountainleaf.ru/catalog/taiwan-oolong/lishan-spring-2026</loc><lastmod>2026-11-05</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>
  <url><loc>https://mountainleaf.ru/brewing-guide</loc><lastmod>2026-10-18</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>
</urlset>
```

### 4. `_headers` и JSON-LD `@graph`
```text
/*
  Content-Security-Policy: default-src 'self'; script-src 'self' 'sha256-M4kQ9xL2vP7nR1tZ6wB8cF3jH5dG0sA4eU2iV9mN7oE='; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
```

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Store",
      "@id": "https://mountainleaf.ru/#store",
      "name": "Чайная компания «Высокогорный Лист»",
      "url": "https://mountainleaf.ru/",
      "currenciesAccepted": "RUB"
    },
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        { "@type": "ListItem", "position": 1, "name": "Главная", "item": "https://mountainleaf.ru/" },
        { "@type": "ListItem", "position": 2, "name": "Тайваньские улуны", "item": "https://mountainleaf.ru/catalog/taiwan-oolong" },
        { "@type": "ListItem", "position": 3, "name": "Лишань Весна 2026, 100 г" }
      ]
    },
    {
      "@type": "Product",
      "@id": "https://mountainleaf.ru/catalog/taiwan-oolong/lishan-spring-2026#product",
      "name": "Улун Лишань с высоты 2100 м (весенний сбор 2026, 100 г)",
      "sku": "TW-LS-2026-100",
      "description": "Слабоферментированный скрученный улун ручного сбора с нотами горной орхидеи и сливочного послевкусия.",
      "brand": { "@type": "Brand", "name": "Высокогорный Лист" },
      "offers": {
        "@type": "Offer",
        "url": "https://mountainleaf.ru/catalog/taiwan-oolong/lishan-spring-2026",
        "priceCurrency": "RUB",
        "price": "3450.00",
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition"
      }
    }
  ]
}
```""",
        },
        {
            "key": "p2_ru_b2b_cyber_geo_csp",
            "lang": "ru",
            "subdomain": "seo_geo_csp_bundle_ru",
            "user_prompt": (
                "Собери `llms.txt`, `security.txt` (RFC 9116), `_headers` с изоляцией `COOP`/`COEP` "
                "и Schema.org `@graph` (`ProfessionalService` + `TechArticle`) для лаборатории аудита "
                "прикладной безопасности «БастионАппСек»."
            ),
            "assistant_content": """Комплект включает стандарт раскрытия уязвимостей `/.well-known/security.txt` по RFC 9116, строгую кросс-доменную изоляцию окна браузера (`COOP`/`CORP`) и связанную микроразметку экспертных отчётов.

### 1. `llms.txt`
```markdown
# Лаборатория прикладной безопасности «БастионАппСек»

> Независимый аудит защищённости веб-приложений, анализ исходного кода, моделирование угроз API и нагрузочная проверка криптографических протоколов.

## Услуги и база знаний
- [Аудит веб-приложений и GraphQL/REST API](https://bastion-appsec.ru/services/web-pentest): методика по OWASP ASVS 4.0.3 с верификацией патчей.
- [Анализ архитектуры аутентификации OAuth 2.1 и Passkeys](https://bastion-appsec.ru/research/oauth21-hardening): разбор типовых ошибок валидации `redirect_uri` и PKCE.
- [Политика ответственного раскрытия](https://bastion-appsec.ru/.well-known/security.txt): PGP-ключ и канал связи для исследователей.
```

### 2. `/.well-known/security.txt` (RFC 9116)
```text
Contact: mailto:cert@bastion-appsec.ru
Encryption: https://bastion-appsec.ru/pgp-key.txt
Preferred-Languages: ru, en
Canonical: https://bastion-appsec.ru/.well-known/security.txt
Expires: 2027-11-01T00:00:00.000Z
```

### 3. `_headers`
```text
/*
  Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: require-corp
  Cross-Origin-Resource-Policy: same-origin
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
```

### 4. Schema.org `@graph` JSON-LD
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "ProfessionalService",
      "@id": "https://bastion-appsec.ru/#org",
      "name": "БастионАппСек",
      "url": "https://bastion-appsec.ru/",
      "knowsAbout": ["OWASP ASVS", "Web Application Security", "Content Security Policy", "OAuth 2.1"]
    },
    {
      "@type": "TechArticle",
      "@id": "https://bastion-appsec.ru/research/oauth21-hardening#article",
      "headline": "Защита потоков OAuth 2.1 и WebAuthn в многоарендных SaaS-приложениях",
      "datePublished": "2026-09-14",
      "inLanguage": "ru",
      "author": { "@id": "https://bastion-appsec.ru/#org" },
      "proficiencyLevel": "Expert"
    }
  ]
}
```""",
        },
        {
            "key": "p2_en_saas_vectordb_geo_csp",
            "lang": "en",
            "subdomain": "seo_geo_csp_bundle_en",
            "user_prompt": (
                "Generate a production GEO/SEO and HTTP hardening bundle (`llms.txt`, `robots.txt`, "
                "`_headers` with hash-pinned CSP and Permissions-Policy, plus Schema.org `@graph` JSON-LD "
                "for `SoftwareApplication` and `WebAPI`) for 'QuantaIndex', an embedded Rust vector engine."
            ),
            "assistant_content": """Below is the complete discovery and HTTP security configuration for **QuantaIndex**, aligning `llms.txt` documentation endpoints with canonical `SoftwareApplication` and `WebAPI` structured data while enforcing zero-inline-script CSP.

### 1. `llms.txt`
```markdown
# QuantaIndex — Embedded HNSW & Scalar-Quantized Vector Engine

> Apache-2.0 Rust library and C FFI bindings for sub-millisecond memory-mapped vector search on edge and single-node servers without external JVM or coordinator daemons.

## Core Documentation
- [Quickstart & Cargo Feature Flags](https://quantaindex.dev/docs/quickstart): SIMD acceleration (`AVX-512`, `NEON`), `mmap` zero-copy loading, and ACID write-ahead log setup.
- [HTTP & gRPC Wire API Reference](https://quantaindex.dev/docs/api): OpenAPI 3.1 endpoints for hybrid BM25 + dense cosine retrieval.
- [Benchmarks & Recall Curves](https://quantaindex.dev/benchmarks): 10M 768-d vectors memory footprint and p99 latency under concurrent writes.
```

### 2. `robots.txt`
```text
User-agent: *
Allow: /
Disallow: /console/
Disallow: /api/internal/

User-agent: GPTBot
Allow: /llms.txt
Allow: /docs/
Allow: /benchmarks

User-agent: PerplexityBot
Allow: /

Sitemap: https://quantaindex.dev/sitemap.xml
```

### 3. `_headers`
```text
/*
  Content-Security-Policy: default-src 'none'; script-src 'self' 'sha256-T7vN2pQ8xL4mK9rZ1wC6bF3jH5dG0sA2eU8iV4mN1oQ='; style-src 'self' 'sha256-H2kP6xL9vR3nQ7tZ4wB1cF8jD5gS0aE6uV3iM9nK2oY='; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), microphone=(), usb=()
```

### 4. Schema.org `@graph` JSON-LD
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://quantaindex.dev/#org",
      "name": "QuantaIndex Labs",
      "url": "https://quantaindex.dev/"
    },
    {
      "@type": "SoftwareApplication",
      "@id": "https://quantaindex.dev/#software",
      "name": "QuantaIndex Engine",
      "applicationCategory": "DeveloperApplication",
      "operatingSystem": "Linux, macOS, Windows",
      "softwareVersion": "1.8.2",
      "license": "https://www.apache.org/licenses/LICENSE-2.0",
      "publisher": { "@id": "https://quantaindex.dev/#org" },
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD"
      }
    },
    {
      "@type": "WebAPI",
      "@id": "https://quantaindex.dev/docs/api#webapi",
      "name": "QuantaIndex Hybrid Search API",
      "documentation": "https://quantaindex.dev/docs/api",
      "provider": { "@id": "https://quantaindex.dev/#org" }
    }
  ]
}
```""",
        },
        {
            "key": "p2_en_biennial_event_geo_csp",
            "lang": "en",
            "subdomain": "seo_geo_csp_bundle_en",
            "user_prompt": (
                "Write `llms.txt`, `sitemap.xml` with `xhtml:link` bilingual `hreflang` alternates (`en`, "
                "`de`, `x-default`), strict `_headers`, and Schema.org `@graph` (`ExhibitionEvent` + `Place`) "
                "for the Zurich Computational Design Biennial 2027."
            ),
            "assistant_content": """For a multilingual European exhibition site, reciprocal `xhtml:link rel="alternate" hreflang="..."` entries in `sitemap.xml` prevent cross-locale canonical cannibalization, while `ExhibitionEvent` structured data exposes exact venue coordinates and ticket availability.

### 1. `llms.txt`
```markdown
# Zurich Computational Design Biennial 2027

> International exhibition and symposium on algorithmic architecture, robotic timber fabrication, and low-carbon material systems at Kraftwerk Zurich (18 March – 11 April 2027).

## Essential Pages
- [Curatorial Programme & Pavilions](https://zcdb2027.ch/en/programme): full schedule of installations, keynote lectures, and fabrication workshops.
- [Visitor Information & Accessibility](https://zcdb2027.ch/en/visit): wheelchair-accessible routes, SBB transit connections, and opening hours.
- [Press & High-Resolution Dossier](https://zcdb2027.ch/en/press): accreditation rules and CC-BY-4.0 press factsheets.
```

### 2. Multilingual `sitemap.xml` (`hreflang` reciprocals)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://zcdb2027.ch/en/programme</loc>
    <xhtml:link rel="alternate" hreflang="en" href="https://zcdb2027.ch/en/programme"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://zcdb2027.ch/de/programm"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://zcdb2027.ch/en/programme"/>
    <lastmod>2026-11-02</lastmod>
  </url>
  <url>
    <loc>https://zcdb2027.ch/de/programm</loc>
    <xhtml:link rel="alternate" hreflang="en" href="https://zcdb2027.ch/en/programme"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://zcdb2027.ch/de/programm"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://zcdb2027.ch/en/programme"/>
    <lastmod>2026-11-02</lastmod>
  </url>
</urlset>
```

### 3. `_headers`
```text
/*
  Content-Security-Policy: default-src 'self'; script-src 'self' 'sha256-B6nQ3xL8vP2mK7rZ9wC4bF1jH5dG0sA8eU2iV6mN3oP='; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  Cross-Origin-Opener-Policy: same-origin
```

### 4. Schema.org `@graph` JSON-LD
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Place",
      "@id": "https://zcdb2027.ch/#venue",
      "name": "Kraftwerk Selnau",
      "address": {
        "@type": "PostalAddress",
        "streetAddress": "Selnaustrasse 25",
        "addressLocality": "Zürich",
        "postalCode": "8001",
        "addressCountry": "CH"
      }
    },
    {
      "@type": "ExhibitionEvent",
      "@id": "https://zcdb2027.ch/en/programme#event",
      "name": "Zurich Computational Design Biennial 2027",
      "startDate": "2027-03-18T10:00:00+01:00",
      "endDate": "2027-04-11T20:00:00+02:00",
      "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
      "eventStatus": "https://schema.org/EventScheduled",
      "location": { "@id": "https://zcdb2027.ch/#venue" },
      "offers": {
        "@type": "Offer",
        "url": "https://zcdb2027.ch/en/tickets",
        "price": "28.00",
        "priceCurrency": "CHF",
        "availability": "https://schema.org/InStock"
      }
    }
  ]
}
```""",
        },
        {
            "key": "p2_en_architecture_firm_geo_csp",
            "lang": "en",
            "subdomain": "seo_geo_csp_bundle_en",
            "user_prompt": (
                "Create a complete `llms.txt`, `robots.txt`, strict nonce/hash `_headers`, and Schema.org "
                "`@graph` (`ArchitectureFirm` + `CreativeWork` case study) for 'Nordic Mass Timber Studio' "
                "in Oslo, ensuring zero third-party font or tracker leakage."
            ),
            "assistant_content": """All assets, fonts, and vector drawings are self-hosted (`font-src 'self'`, `connect-src 'self'`) so the portfolio satisfies both GDPR zero-tracker compliance and deterministic Lighthouse security audits.

### 1. `llms.txt`
```markdown
# Nordic Mass Timber Studio (Oslo)

> Structural architecture practice specializing in cross-laminated timber (CLT) public schools, maritime terminals, and passive-house civic buildings across Scandinavia.

## Reference Materials
- [Selected Built Works (2018–2026)](https://nordictimber.no/works): structural spans, embodied carbon LCA sheets (EN 15978), and acoustic ratings.
- [Timber Connection Detail Library](https://nordictimber.no/details): fire-rated concealed glulam beam hangers and moisture monitoring protocols.
- [Practice Profile & Competitions](https://nordictimber.no/studio): partner biographies and Nordic Swan Ecolabel certifications.
```

### 2. `robots.txt`
```text
User-agent: *
Allow: /
Disallow: /client-portal/
Disallow: /bim-downloads/private/

Sitemap: https://nordictimber.no/sitemap.xml
```

### 3. `_headers`
```text
/*
  Content-Security-Policy: default-src 'none'; script-src 'self' 'sha256-P9vL4xQ2mK8nR1tZ7wB5cF3jH6dG0sA4eU9iV2mN5oW='; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  Referrer-Policy: same-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()
```

### 4. Schema.org `@graph` JSON-LD
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "ArchitectureFirm",
      "@id": "https://nordictimber.no/#firm",
      "name": "Nordic Mass Timber Studio AS",
      "url": "https://nordictimber.no/",
      "address": {
        "@type": "PostalAddress",
        "streetAddress": "Schweigaards gate 34",
        "addressLocality": "Oslo",
        "postalCode": "0191",
        "addressCountry": "NO"
      }
    },
    {
      "@type": "CreativeWork",
      "@id": "https://nordictimber.no/works/fjord-maritime-hall#work",
      "name": "Fjord Maritime Passenger Terminal",
      "creator": { "@id": "https://nordictimber.no/#firm" },
      "dateCreated": "2025-08-20",
      "about": "Long-span 38-meter curved glulam roof structure with biogenic carbon storage of 610 tonnes CO2e."
    }
  ]
}
```""",
        },
        {
            "key": "p2_en_fintech_treasury_geo_csp",
            "lang": "en",
            "subdomain": "seo_geo_csp_bundle_en",
            "user_prompt": (
                "Draft `llms.txt`, `robots.txt`, hardened `_headers` (including `Cache-Control` separation "
                "for authenticated API routes vs static docs), and Schema.org `@graph` (`FinancialService` "
                "+ `FAQPage`) for 'LedgerRail', a SEPA Instant corporate treasury platform."
            ),
            "assistant_content": """The configuration separates public documentation (`public, max-age=3600`) from sensitive `/api/*` and `/dashboard/*` routes (`no-store, private`) while exposing accurate compliance facts to search and AI engines.

### 1. `llms.txt`
```markdown
# LedgerRail — Programmatic SEPA Instant & Multi-IBAN Treasury

> Regulated European treasury automation API for real-time ISO 20022 XML (`pain.001` / `camt.053`) reconciliation, automated liquidity sweeps, and dual-approval payment controls.

## Documentation & Trust
- [ISO 20022 Integration Guide](https://ledgerrail.eu/docs/iso20022): webhook signature verification (`Ed25519`), idempotency keys, and sandbox IBANs.
- [Security & Safeguarding Controls](https://ledgerrail.eu/trust): SOC 2 Type II summary, segregated Tier-1 safeguarding accounts, and HSM key custody.
- [Pricing & Settlement Cutoffs](https://ledgerrail.eu/pricing): transparent per-transfer fee schedule with zero FX markup tiers.
```

### 2. `robots.txt`
```text
User-agent: *
Allow: /docs/
Allow: /trust
Allow: /pricing
Allow: /llms.txt
Disallow: /dashboard/
Disallow: /api/
Disallow: /webhooks/

Sitemap: https://ledgerrail.eu/sitemap.xml
```

### 3. `_headers`
```text
/*
  Content-Security-Policy: default-src 'none'; script-src 'self' 'sha256-L3mK8pQ4xN9vR2tZ6wB1cF7jH5dG0sA9eU4iV8mN2oC='; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  Cross-Origin-Opener-Policy: same-origin
  Referrer-Policy: no-referrer

/api/*
  Cache-Control: no-store, no-cache, must-revalidate, private
  Pragma: no-cache
```

### 4. Schema.org `@graph` JSON-LD
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "FinancialService",
      "@id": "https://ledgerrail.eu/#service",
      "name": "LedgerRail Treasury Platform",
      "url": "https://ledgerrail.eu/",
      "areaServed": "EEA",
      "currenciesAccepted": "EUR"
    },
    {
      "@type": "FAQPage",
      "@id": "https://ledgerrail.eu/trust#faq",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "How does LedgerRail prevent duplicate SEPA Instant payouts during network retries?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Every POST /v1/payouts request requires a client-generated UUIDv7 Idempotency-Key locked atomically for 72 hours."
          }
        }
      ]
    }
  ]
}
```""",
        },
    ]


def get_unique_pillar4_copy_decks() -> list[dict[str, Any]]:
    """Return 10 strictly 1-of-1 copywriting, UX microcopy & Z-Image art-direction decks (5 RU + 5 EN).

    Every deck delivers genuine brand positioning, conversion copy, interface microcopy states,
    OKLCH color/typography rationale, and validated `zimage_prompts.json` (zero HTML skeletons).
    """
    return [
        {
            "key": "p4_ru_acoustic_panels_copy_deck",
            "lang": "ru",
            "subdomain": "copywriting_art_direction_ru",
            "user_prompt": (
                "Разработай полную копирайтинг-платформу, UX-микротексты и арт-дирекшн с `zimage_prompts.json` "
                "(под `Tongyi-MAI/Z-Image-Turbo`) для бренда архитектурных акустических панелей из древесного "
                "волокна и войлока «Тихий Контур» (аудитория: главные архитекторы офисов и студий звукозаписи)."
            ),
            "assistant_content": """### 1. Позиционирование и голос бренда (Tone of Voice)
- **Суть бренда:** Инженерная акустика с эстетикой столярного изделия — гасим реверберацию в переговорных и залах без пластикового «офисного» вида.
- **Характер речи:** Точный, предметный, спокойный. Опираемся на коэффициенты звукопоглощения `NRC`, классы пожарной безопасности `КМ1` и честную фактуру шпона.
- **Правила редактуры:**
  - **Пишем так:** «Снижает время реверберации RT60 с 1,4 до 0,45 с при толщине узла 42 мм».
  - **Не пишем так:** «Уникальные инновационные панели подарят идеальную гармонию и уют вашему бизнесу».

### 2. Копирайтинг первого экрана и ключевых секций лендинга
- **Надзаголовок (Eyebrow):** Акустические потолочные бафлы и стеновые кассеты · КМ1 · Протоколы НИИСФ
- **Заголовок H1 (основной):** Тишина в переговорной, рассчитанная до герца и миллиметра
- **Альтернативный H1 (для архитекторов):** Шпон американского ореха и базальтовый контур с поглощением `NRC 0.90`
- **Подзаголовок:** Проектируем, фрезеруем и монтируем акустические системы под вашу BIM-модель за 18 рабочих дней — с акустическим расчётом помещения до подписания спецификации.
- **Первичный CTA:** Загрузить план помещения для расчёта RT60
- **Вторичный CTA:** Скачать каталог узлов примыкания (DWG + RVT, 14 МБ)

### 3. UX-микротексты интерфейса расчёта и формы заявки
- **Пустое состояние загрузчика чертежа:** `Перетащите чертёж в PDF или DWG (до 40 МБ) — инженер-акустик пришлёт карту эхоподавления в течение рабочего дня.`
- **Подсказка у поля высоты потолка:** `Укажите высоту до монолитной плиты перекрытия, даже если планируется подвесной потолок.`
- **Текст ошибки валидации:** `Файл превышает 40 МБ. Архив со всеми листами проекта можно прикрепить ссылкой на корпоративное хранилище в поле ниже.`
- **Экран подтверждения отправки:** `Заявка № ТК-409 принята. Инженер свяжется только по делу в Telegram или по почте — без обзвонов отдела продаж.`

### 4. Типографика и палитра OKLCH
- **Шрифтовая пара:** строгий антиквенный заголовок с умеренным контрастом штрихов + нейтральный гротеск с табличными цифрами для акустических таблиц `125–4000 Гц`.
- **Токены OKLCH:**
  - `--bg-wool: oklch(0.962 0.011 84)` — натуральный неотбелённый войлок;
  - `--ink-graphite: oklch(0.205 0.012 255)` — графитовый профиль подвеса;
  - `--accent-walnut: oklch(0.48 0.078 56)` — тёплый ореховый шпон.

### 5. Спецификация визуальных сцен `zimage_prompts.json` (`Z-Image-Turbo`)
```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "aspect_ratios": { "hero": "16:10", "detail": "4:5" },
  "scenes": [
    {
      "id": "hero_boardroom_baffles",
      "usage": "Фоновая фотография первого экрана",
      "prompt": "Architectural interior photograph of a quiet minimalist executive boardroom in Saint Petersburg, ceiling fitted with linear walnut wood slat acoustic baffles and warm grey wool felt backing, soft overcast northern daylight grazing textured concrete column, long oak table with brass tabletop microphones, shot on 35mm tilt-shift lens, f/5.6, natural color grading in warm alabaster and walnut tones, editorial architectural digest realism."
    },
    {
      "id": "macro_joinery_joint",
      "usage": "Карточка конструктивного узла",
      "prompt": "Studio macro product photograph of a cross-section acoustic wall panel joint showing micro-perforated American walnut veneer bonded to dense charcoal acoustic felt core and anodized matte black aluminum rail, directional side studio lighting revealing wood grain pores and felt fibers, 90mm macro lens, crisp depth of field, neutral warm stone backdrop."
    }
  ]
}
```""",
        },
        {
            "key": "p4_ru_medical_diagnostics_copy_deck",
            "lang": "ru",
            "subdomain": "copywriting_art_direction_ru",
            "user_prompt": (
                "Напиши копирайтинг посадочной страницы, бережные UX-микротексты записи на обследование "
                "и арт-дирекшн с `zimage_prompts.json` для центра превентивной кардиологии и МРТ сосудов "
                "«Ритм и Норма» (без запугивания пациента и канцелярита)."
            ),
            "assistant_content": """### 1. Редакционная политика и голос бренда
- **Принцип коммуникации:** Спокойная доказательная медицина без тревожных штампов («тихий убийца», «успейте проверить»). Пациент должен понимать, зачем нужен каждый показатель и сколько времени займёт визит.
- **Словарь:** Вместо «осуществляется оказание диагностических медуслуг» — «проводим УЗИ сердца и суточный мониторинг за один визит, расшифровку разбирает кардиолог на очной беседе 40 минут».

### 2. Тексты ключевых блоков страницы
- **H1:** Кардиологический чекап за 3 часа — по международным протоколам ESC без лишних анализов
- **Подзаголовок:** Томограф 3 Тесла с широким туннелем 70 см, липидный профиль с липопротеином(а) и подробный план профилактики на понятном русском языке.
- **Блок «Что входит и почему ничего лишнего»:**
  1. **Расширенная липидограмма и апопротеин B:** оцениваем реальный атерогенный риск точнее стандартного общего холестерина.
  2. **Эхокардиография экспертного класса:** проверяем геометрию камер и работу клапанов в покое и под мягкой нагрузкой.
  3. **Консультация без спешки (45 минут):** врач объясняет каждый снимок на экране и выдаёт письменное заключение без нечитаемых сокращений.
- **CTA:** Выбрать утреннее окно обследования

### 3. UX-микротексты анкеты и записи
- **Переключатель клаустрофобии в форме МРТ:** `Мне тревожно в замкнутом пространстве — подготовить открытый подголовник и голосовую связь с лаборантом каждые 3 минуты.`
- **Напоминание о подготовке:** `За 8 часов до анализа крови можно пить чистую негазированную воду — обезвоживание искажает вязкость и усложняет взятие пробы.`
- **Сообщение при отсутствии слотов на завтра:** `На завтра утренние окна натощак уже заняты. Ближайшее свободное время — четверг, 08:30 или 09:15.`

### 4. Визуальная система OKLCH и `zimage_prompts.json`
- **Палитра спокойного клинического света:** фон `oklch(0.975 0.006 215)` (светлый воздух), текст `oklch(0.22 0.018 245)` (глубокий сине-сланцевый), акцент `oklch(0.52 0.10 192)` (приглушённый шалфейно-бирюзовый, исключающий агрессивный красный).

```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "scenes": [
    {
      "id": "calm_consultation_room",
      "usage": "Блок очного разбора результатов с врачом",
      "prompt": "Naturalistic editorial photograph of a serene Scandinavian-style cardiology consultation room, sunlit pale birch desk, a calm forty-five-year-old doctor in a clean slate-blue scrub jacket reviewing clear echocardiogram graphics on a matte monitor beside a relaxed patient, ceramic cup of water, indoor olive tree in soft focus, 50mm prime lens, warm diffused morning window light, authentic documentary healthcare photography."
    },
    {
      "id": "wide_bore_mri_suite",
      "usage": "Карточка комфортного МРТ 70 см",
      "prompt": "Clean architectural photograph of a modern wide-bore 3T MRI suite designed to reduce anxiety, warm indirect cove lighting in soft sage and cream tones, acoustic timber wall slats, wide open scanner gantry, spotless matte linoleum floor, 28mm architectural lens, balanced exposure, calm reassuring atmosphere."
    }
  ]
}
```""",
        },
        {
            "key": "p4_ru_b2b_warehouse_robotics_copy_deck",
            "lang": "ru",
            "subdomain": "copywriting_art_direction_ru",
            "user_prompt": (
                "Подготовь B2B-копирайтинг первого и второго экранов, возражения финансового директора, "
                "микротексты калькулятора окупаемости и `zimage_prompts.json` для российского производителя "
                "складских автономных мобильных роботов (AMR) «РейлБот Логистика»."
            ),
            "assistant_content": """### 1. Стратегия убеждения для B2B (директор по логистике + CFO)
- **Главный барьер покупки:** Страх остановки действующего склада на время внедрения и зависимость от зарубежного облачного ПО.
- **Ключевой аргумент:** Развёртывание по лазерной SLAM-навигации за 10 ночных смен без вскрытия бетонных полов и полностью локальный контур диспетчеризации в закрытой сети предприятия.

### 2. Копирайтинг ключевых экранов
- **H1:** Автономные тележки до 1 500 кг, которые запускаются на действующем складе без разметки пола
- **Подзаголовок:** Увеличиваем скорость комплектации паллет в 2,3 раза, интегрируемся с 1С:WMS по открытому REST API и окупаем парк за 14–18 месяцев при трёхсменном графике.
- **Три карточки доказательств (ответы на вопросы CFO):**
  - **0 дней простоя склада:** картографирование проходов выполняется лидарами в ночное окно без магнитной ленты и QR-наклеек.
  - **Литий-титанатные батареи до −25 °C:** работа в неотапливаемых доках и холодильных камерах с дозарядкой за 9 минут на пит-стопе.
  - **Локальный сервер оркестрации:** диспетчер роя из 120 роботов работает в вашем ЦОД на отечественном Linux без внешней телеметрии.
- **CTA:** Рассчитать окупаемость парка под ваш грузопоток

### 3. UX-микротексты калькулятора ROI
- **Подсказка к полю «Средний пробег комплектовщика за смену»:** `Если точных замеров нет, оставьте 11 км — это медиана для склада класса А площадью 15 000 м².`
- **Предупреждение при уклоне пандуса > 8 %:** `Уклон свыше 8 % требует тяговой модификации РейлБот-1500Т с усиленным электромагнитным тормозом — мы автоматически учли её в расчёте.`
- **Подпись под итоговым графиком:** `Расчёт включает регламентное ТО, комплект запасных ведущих колёс и зарядные станции.`

### 4. Палитра OKLCH и `zimage_prompts.json`
- Индустриальная палитра Neo-Swiss: графитовый бетон `oklch(0.18 0.012 250)`, светлая сталь `oklch(0.96 0.004 250)` и сигнальный янтарный безопасности `oklch(0.75 0.17 72)`.

```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "scenes": [
    {
      "id": "amr_warehouse_aisle",
      "usage": "Геройский кадр первого экрана",
      "prompt": "Industrial documentary photograph inside a high-bay logistics fulfillment warehouse, a sleek low-profile autonomous mobile robot in matte dark graphite with subtle amber LED safety perimeter strip carrying a loaded wooden euro-pallet smoothly down a polished concrete aisle, motion-sharp foreground, tall steel pallet racking in background, crisp industrial high-CRI overhead lighting, 35mm lens, realistic engineering photography."
    },
    {
      "id": "charging_dock_closeup",
      "usage": "Иллюстрация быстрой дозарядки LTO",
      "prompt": "Close-up technical photograph of an industrial autonomous robot docking precisely against brushed copper floor-level fast-charging contacts inside a cold-storage warehouse zone, subtle frost condensation on steel guardrails, crisp telemetry status screen on charging pillar, 50mm lens, clean industrial realism."
    }
  ]
}
```""",
        },
        {
            "key": "p4_ru_artisan_bakery_subscription_copy_deck",
            "lang": "ru",
            "subdomain": "copywriting_art_direction_ru",
            "user_prompt": (
                "Создай копирайтинг, сценарий онбординга подписки, UX-микротексты управления доставкой "
                "и `zimage_prompts.json` для ремесленной пекарни длительной холодной ферментации «Корка и Мякиш»."
            ),
            "assistant_content": """### 1. Голос бренда и отстройка от массовой доставки
- **Интонация:** Тёплая, знающая ремесло, без уменьшительно-ласкательных суффиксов («хлебушек», «булочки», «вкусняшки» — под строгим запретом). Говорим языком пекаря: закваска спонтанного брожения, шугуровская цельнозерновая мука, 28 часов ферментации при +4 °C, подовая каменная печь.

### 2. Копирайтинг лендинга утренней подписки
- **H1:** Подовый тартин из утренней выемки 06:30 — на вашем столе к восьми утра по вторникам и субботам
- **Подзаголовок:** Замешиваем тесто только под подтверждённые подписки: 0 % списаний черствого хлеба, три вида зерна в ротации и пауза в один клик, если уезжаете в отпуск.
- **Секция «Почему длительная ферментация меняет вкус»:**
  - **28 часов при +4 °C:** молочнокислые бактерии расщепляют фитиновую кислоту и сложные сахара, поэтому мякиш остаётся влажным четыре дня без улучшителей.
  - **Подовый камень 260 °C с паром:** даёт тонкую карамелизованную корку с характерным «гребнем», которая хрустит, но не крошится в пыль.
- **CTA:** Собрать утреннюю корзину на следующую неделю

### 3. UX-микротексты личного кабинета подписчика
- **Кнопка быстрой паузы:** `Пропустить ближайший вторник (пекарь ещё не поставил опару — списание перенесётся бесплатно).`
- **Состояние после начала замеса (за 18 часов до выпечки):** `Опара на завтра уже зреет в холодном цехе! Изменить состав на субботу всё ещё можно, а завтрашнюю буханку мы можем передать соседям по вашему поручению.`
- **Переключатель «Тихая доставка у двери»:** `Оставить крафт-пакет на крючке и прислать фото в Telegram без звонка в домофон.`

### 4. Палитра Tactile Craft OKLCH и `zimage_prompts.json`
- Ржаная мука `oklch(0.955 0.019 80)`, карамельная корка `oklch(0.42 0.095 52)`, жжёный чугун `oklch(0.19 0.015 48)`.

```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "scenes": [
    {
      "id": "sourdough_crumb_morning_light",
      "usage": "Первый экран подписки",
      "prompt": "Editorial food photograph of a freshly baked country sourdough boule cut in half on a weathered oak baker board, open honeycomb wild-yeast crumb, blistered dark amber caramelized crust dusted lightly with coarse rye flour, wrought-iron bread knife, early morning directional window sunlight casting long soft shadows, 85mm prime lens, f/4, tactile natural film grain."
    },
    {
      "id": "cold_fermentation_bannetons",
      "usage": "Блок о 28 часах ферментации",
      "prompt": "Documentary craft photograph of linen-lined rattan proofing bannetons arranged neatly on stainless steel racks inside a bakery fermentation room, shaped dough dusted with rice flour, baker hands checking dough tension, natural cool ambient light, 50mm lens, authentic artisan bakery atmosphere."
    }
  ]
}
```""",
        },
        {
            "key": "p4_ru_design_system_audit_copy_deck",
            "lang": "ru",
            "subdomain": "copywriting_art_direction_ru",
            "user_prompt": (
                "Сформулируй редакционный стандарт интерфейса, тексты для пустых состояний и ошибок сетевой "
                "синхронизации, а также арт-дирекшн иллюстраций `zimage_prompts.json` для настольного "
                "приложения инженерных заметок с локальным шифрованием «Свод»."
            ),
            "assistant_content": """### 1. Принципы продуктовой редактуры «Свода»
1. **Причина → Состояние данных → Действие:** в любой нештатной ситуации сначала сообщаем, что локальная рукопись цела на диске, затем объясняем причину задержки синхронизации и даём ровно одну кнопку решения.
2. **Никакой ложной вины пользователя:** никогда не пишем «Вы ввели неверный ключ» — пишем «Ключ расшифровки не подошёл к этому хранилищу».

### 2. Матрица UX-текстов критических состояний
- **Пустой экран нового хранилища:**
  - *Заголовок:* `Локальное хранилище зашифровано и готово к работе`
  - *Текст:* `Все заметки сохраняются в обычных файлах Markdown на вашем диске и шифруются алгоритмом XChaCha20-Poly1305 до отправки в облако.`
  - *Действие:* `Создать первую заметку (Ctrl+N)` · `Импортировать папку из Obsidian`
- **Конфликт версий при офлайн-правке с двух устройств:**
  - *Заголовок:* `Найдены две независимые правки заметки «Архитектура БД»`
  - *Текст:* `Ни одна строчка не потеряна: мы сохранили версию с ноутбука (23:14) и с телефона (08:02) рядом, чтобы вы спокойно объединили абзацы.`
  - *Действие:* `Открыть построчное сравнение`
- **Потеря связи с релейным сервером:**
  - *Статус в строке состояния:* `Офлайн · 4 изменения надёжно записаны на диск и отправятся автоматически при появлении сети.`

### 3. Арт-дирекшн OKLCH и `zimage_prompts.json`
- Канон Quiet Technical Editorial: тёплый графит `oklch(0.18 0.01 75)` в тёмной теме, бумажный серый `oklch(0.965 0.007 82)` в светлой и приглушённый кобальт фокуса `oklch(0.56 0.14 252)`.

```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "scenes": [
    {
      "id": "desk_encrypted_notebook_hero",
      "usage": "Визуал страницы загрузки настольного клиента",
      "prompt": "Minimalist overhead studio photograph on matte dark slate desk surface featuring a brushed aluminum mechanical keyboard, a fountain pen resting on heavy cream cotton paper with geometric architectural diagram sketches, and a subtle hardware security key USB-C token, soft directional key light from top-left, calm precision engineering aesthetic, 50mm lens, f/8."
    }
  ]
}
```""",
        },
        {
            "key": "p4_en_climate_hardware_copy_deck",
            "lang": "en",
            "subdomain": "copywriting_art_direction_en",
            "user_prompt": (
                "Create a complete brand positioning brief, landing-page conversion copy, onboarding/error "
                "UX microcopy, OKLCH art-direction tokens, and `zimage_prompts.json` (`Tongyi-MAI/Z-Image-Turbo`) "
                "for 'AetherPump', a whisper-quiet R290 hydronic residential heat pump engineered for cold Nordic retrofits."
            ),
            "assistant_content": """### 1. Brand Positioning & Voice Architecture
- **Category Wedge:** Drop-in high-temperature (`75 °C` flow) R290 propane hydronic heat pump built specifically for 1960s–1990s brick homes — replacing oil/gas boilers **without ripping out existing cast-iron radiators**.
- **Voice Pillars:** Empirically grounded (`SCOP 4.85`, `36 dBA` at 3 meters, `-25 °C` rated), calm, homeowner-literate.
- **Copy Guardrails:**
  - **Do write:** "Delivers 75 °C radiator water down to −22 °C outside — installed in two days using your existing copper piping."
  - **Never write:** "Join the green revolution with our next-gen eco-smart comfort solution!"

### 2. Landing Page Hero & Core Narrative Copy
- **Eyebrow:** Natural R290 Refrigerant (`GWP = 3`) · Tested at −25 °C in Kiruna
- **Primary H1:** Keep your cast-iron radiators. Cut winter heating bills in half.
- **Alternate Technical H1:** High-temperature hydronic heating engineered for brick homes and sub-zero nights.
- **Subheadline:** Most heat pumps demand underfloor renovations. AetherPump connects directly to high-temperature radiator loops while running quieter than snow falling outside a bedroom window (`36 dBA`).
- **Primary CTA:** Check radiator compatibility in 90 seconds
- **Secondary CTA:** Download EN 14825 acoustic & SCOP test sheet (PDF)

### 3. Product & Estimator UX Microcopy
- **Boiler plate photo upload prompt:** `Snap a photo of your current boiler's silver nameplate — we'll read the kW output automatically so you don't have to hunt for manuals.`
- **Breaker amperage warning state:** `Your 16 A single-phase main fuse is slightly tight for peak −20 °C defrost cycles. Including our Din-rail load balancer (+€240) prevents nuisance trips when the oven and EV charger run together.`
- **Empty telemetry history state (Day 1 in app):** `Gathering your home's thermal inertia curve. After 48 hours of outdoor temperature shifts, weather-compensated scheduling will unlock automatically.`

### 4. OKLCH Design Tokens & `zimage_prompts.json`
- **Palette:** Birch frost background `oklch(0.972 0.006 230)`, cast-iron ink `oklch(0.19 0.012 250)`, copper-pipe accent `oklch(0.58 0.13 48)`.

```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "scenes": [
    {
      "id": "nordic_brick_home_exterior_unit",
      "usage": "Hero visual showing exterior monobloc unit in winter",
      "prompt": "Architectural exterior photograph at blue hour in Scandinavia, a compact architectural monobloc heat pump clad in matte dark anodized aluminum louvers mounted cleanly beside a 1970s red-brick house wall in fresh snow, warm amber light glowing through triple-glazed kitchen windows inside, zero visible steam plume, 35mm architectural lens, crisp natural exposure, serene Nordic winter realism."
    },
    {
      "id": "copper_manifold_utility_room",
      "usage": "Two-day retrofit proof section",
      "prompt": "Clean editorial interior photograph of a tidy European residential utility room, precision-bent insulated copper hydronic pipes and brass isolation valves connecting neatly to a compact white steel indoor buffer cylinder, digital pressure gauge reading 1.8 bar, soft natural daylight from basement hopper window, 50mm lens, authentic craftsmanship."
    }
  ]
}
```""",
        },
        {
            "key": "p4_en_developer_observability_copy_deck",
            "lang": "en",
            "subdomain": "copywriting_art_direction_en",
            "user_prompt": (
                "Write conversion copy, pricing-page transparency microcopy, CLI/dashboard error states, "
                "OKLCH art direction, and `zimage_prompts.json` for 'TraceLoom', an eBPF production profiler "
                "with predictable per-node pricing and zero cardinality overage bills."
            ),
            "assistant_content": """### 1. Positioning Against Legacy APM Vendors
- **Core Tension:** Engineering teams turn off high-cardinality tags (`tenant_id`, `request_id`) because legacy APMs punish debugging with surprise six-figure custom-metrics overage invoices.
- **Value Proposition:** Continuous kernel-level eBPF CPU/off-CPU flamegraphs and ClickHouse trace storage billed flat per host — unlimited custom attributes, `< 0.7%` CPU overhead, zero SDK code changes.

### 2. Conversion Copy Deck
- **H1:** Continuous production flamegraphs without the custom-metrics ransom note.
- **Subheadline:** Attach an unprivileged eBPF collector in 40 seconds. Slice p99 tail latency by `customer_id`, `build_sha`, or `region` at flat per-node pricing — zero instrumentation PRs required.
- **Three Proof Sections:**
  1. **Zero SDK lock-in:** Reads DWARF unwind tables directly from stripped Rust, Go, C++, Python, and JVM binaries.
  2. **Hard billing ceiling, never sampling blindness:** Flat $39/node/month regardless of span volume or label cardinality.
  3. **Off-CPU lock & syscall attribution:** See exact mutex contention and epoll wait stalls alongside user-space stack frames.
- **Primary CTA:** Run single-binary demo in Docker
- **Secondary CTA:** Compare 50-node TCO calculator

### 3. High-Trust Interface & Pricing UX Microcopy
- **Pricing slider commitment note:** `No annual contract trap. Spin up 200 canary nodes during Black Friday week and drop back to 40 on Tuesday — prorated to the hour.`
- **Kernel capability check failure state:** `Linux kernel 5.4 detected without BTF symbols (/sys/kernel/btf/vmlinux missing). TraceLoom fell back safely to perf_event frame-pointer unwinding — install linux-image-extra or upgrade to >= 5.8 for zero-pointer DWARF unwinding.`
- **Empty trace filter state:** `0 spans matched duration > 500ms in the last 15 minutes. Relax the latency threshold to > 120ms (38 spans available) or expand the time window.`

### 4. OKLCH Tokens & `zimage_prompts.json`
- Dark technical editorial: obsidian `oklch(0.145 0.012 260)`, slate hairline `oklch(0.28 0.018 260)`, flamegraph amber `oklch(0.76 0.16 68)`, steady-state mint `oklch(0.75 0.14 162)`.

```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "scenes": [
    {
      "id": "server_rack_optical_fiber_abstract",
      "usage": "Atmospheric technical backdrop for architecture section",
      "prompt": "Macro industrial studio photograph of precision LC duplex single-mode fiber optic transceivers plugged into a matte black anodized 1U network switch faceplate, subtle amber and emerald link status LEDs reflected on brushed steel cage, shallow depth of field, clean dark slate lighting, 90mm macro lens, authentic hardware engineering realism."
    }
  ]
}
```""",
        },
        {
            "key": "p4_en_ergonomic_chair_atelier_copy_deck",
            "lang": "en",
            "subdomain": "copywriting_art_direction_en",
            "user_prompt": (
                "Develop brand copy, product page narrative, fit-finder UX microcopy, OKLCH palette rationale, "
                "and `zimage_prompts.json` for 'Keel Seating', a repairable solid-ash and tensioned-wool "
                "task chair designed for home studios that refuse plastic gaming-chair aesthetics."
            ),
            "assistant_content": """### 1. Brand Voice & Aesthetic Thesis
- **Positioning:** A 10-hour orthopedic task chair built with the joinery and repairability of Danish cabinetmaking — zero polyurethane foam that crumbles in year five, zero squeaking chrome spider bases.
- **Tone:** Tactile, anatomically precise, unhurried.

### 2. Product Landing Copy
- **Eyebrow:** FSC European Ash · Kvadrat Wool Suspension · 15-Year Spare-Parts Guarantee
- **H1:** Orthopedic lumbar mechanics disguised as studio furniture.
- **Subheadline:** Counter-balanced synchro-tilt machined from recycled die-cast aluminum and steam-bent ash. Every wear component unbolts with a single 5 mm hex key.
- **Feature Triad:**
  - **Breathable woven-wool pellicle:** Suspends sit-bones evenly without trapping heat like petroleum memory foam.
  - **Weight-sensing torsion spring:** Self-balances recline resistance from 48 kg to 125 kg with zero plastic tension knobs underneath.
  - **Right-to-repair CAD archive:** Replacement seat slings ($85) and felt hardwood casters ship individually for 15 years.
- **Primary CTA:** Configure wood finish & seat depth

### 3. Fit-Finder & Checkout UX Microcopy
- **Inseam / Seat-pan depth helper:** `Measure from the wall behind your heel to the back of your knee while seated. If you're between 43 cm and 46 cm, choose the Standard pan — you want two fingers of clearance behind your calf.`
- **Hardwood floor caster selection:** `Soft TPE-ring casters selected (included free) — safe for oiled oak, pine, and limewashed concrete without a plastic floor mat.`
- **30-day home trial return reassurance:** `Keep the flat-pack box in a closet or recycle it — if your spine isn't happier on day 30, our courier collects the assembled chair directly.`

### 4. OKLCH Palette & `zimage_prompts.json`
- Tactile Craft + Quiet Luxury crossover: warm limewash wall `oklch(0.964 0.01 82)`, smoked ash `oklch(0.32 0.035 62)`, moss wool `oklch(0.46 0.065 142)`.

```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "scenes": [
    {
      "id": "ash_task_chair_architect_desk",
      "usage": "Primary hero photograph",
      "prompt": "Editorial interior photograph of a sculptural ergonomic task chair crafted from steam-bent natural European ash wood, matte bead-blasted aluminum under-seat tilt mechanism, and forest-moss woven wool backrest, tucked beside a solid timber architect desk in a sunlit loft studio with limewashed walls, 50mm lens, natural afternoon window light, Kinfolk and Cereal magazine aesthetic."
    },
    {
      "id": "hex_bolt_repairable_joint",
      "usage": "15-year right-to-repair callout",
      "prompt": "Close-up studio detail photograph of the underside joint of a wooden task chair showing a precision CNC-machined recycled aluminum bracket fastened into solid ash grain with stainless steel 5mm hex bolts, crisp side lighting emphasizing material honesty and repairability, 85mm lens."
    }
  ]
}
```""",
        },
        {
            "key": "p4_en_maritime_weather_routing_copy_deck",
            "lang": "en",
            "subdomain": "copywriting_art_direction_en",
            "user_prompt": (
                "Write B2B maritime SaaS copywriting, bridge-tablet offline UX microcopy, OKLCH high-contrast "
                "night-watch palette rules, and `zimage_prompts.json` for 'swellVector', a voyage weather-routing "
                "and CII fuel-optimization platform for dry-bulk and container fleets."
            ),
            "assistant_content": """### 1. Audience & Domain Credibility
- **Buyers:** Fleet performance superintendents ashore + Masters/Chief Officers on the bridge.
- **Credibility Rule:** Speak in `knots`, `metric tonnes VLSFO/day`, `significant wave height Hs`, `parametric roll risk`, and `IMO CII rating bands (A–E)` — never generic "AI-powered logistics synergy."

### 2. Core Landing Copy
- **H1:** Cut main-engine fuel burn 6.8% per voyage without missing charterparty laycan windows.
- **Subheadline:** Ensemble wave-spectrum routing calibrated to each hull's real propeller slip curve — delivered over low-bandwidth Iridium/Starlink compressed GRIB2 deltas (`< 180 KB` per 6-hour update).
- **Proof Blocks:**
  - **Hull-specific fouling awareness:** Separates weather-induced speed loss from hull biofouling using noon-report shaft-power telemetry.
  - **Parametric & synchronous roll avoidance:** Flags dangerous wave-encounter periods 72 hours ahead of heavy North Pacific lows.
  - **Charterparty dispute ledger:** Exports signed Beaufort-threshold weather-day exclusion logs ready for London maritime arbitration.
- **CTA:** Request 3-vessel pilot simulation on historical AIS tracks

### 3. Bridge Night-Watch UX Microcopy
- **Low-bandwidth satellite sync indicator:** `Synced 14m ago via Iridium Certus (142 KB compressed). Next ensemble forecast package queued for 06:00 UTC.`
- **Waypoint draft clearance alert:** `Route leg 04 crosses Dogger Bank shallow contour (18.2 m chart datum). Confirm current squat-adjusted draft (14.6 m entered) before exporting RTZ file to ECDIS.`
- **Night-vision mode toggle:** ` Dusk/Night Bridge Mode active (red-shifted OKLCH <= 4 cd/m² to preserve watchkeeper dark adaptation).`

### 4. Dual-Mode OKLCH Art Direction & `zimage_prompts.json`
- Shore office daylight mode (`oklch(0.98 0.004 240)` / deep navy `oklch(0.20 0.04 252)`) + Bridge night mode (`oklch(0.11 0.008 250)` background with night-vision red-amber `oklch(0.62 0.17 34)`).

```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "scenes": [
    {
      "id": "vessel_bridge_twilight_horizon",
      "usage": "Hero section banner",
      "prompt": "Documentary maritime photograph taken from inside a modern merchant vessel wheelhouse at civil twilight over the North Sea, dark silhouettes of bridge wing radar masts against deep slate-blue ocean swells, warm low-glare amber navigation instrument displays in foreground, rain droplets on angled bridge windows, 35mm lens, authentic maritime photojournalism."
    }
  ]
}
```""",
        },
        {
            "key": "p4_en_biotech_lab_eln_copy_deck",
            "lang": "en",
            "subdomain": "copywriting_art_direction_en",
            "user_prompt": (
                "Author positioning, landing copy, 21 CFR Part 11 audit-trail UX microcopy, OKLCH token "
                "system, and `zimage_prompts.json` for ' AssayLedger', a wet-lab electronic lab notebook (ELN) "
                "built for CRISPR and protein-engineering startups."
            ),
            "assistant_content": """### 1. Positioning & Differentiation
- **Problem:** Wet-lab scientists hate clunky 2008 enterprise ELNs and paste plate maps into Slack and Google Sheets — breaking sample lineage right before IND regulatory filing.
- **Thesis:** Keyboard-first plasmid & 384-well plate notebook as fast as Markdown, backed by immutable `21 CFR Part 11` cryptographic e-signatures and GenBank/FASTA diffing.

### 2. Website Copy Deck
- **H1:** Wet-lab protocols fast enough for bench scientists, rigorous enough for IND auditors.
- **Subheadline:** Link `-80 °C` freezer box coordinates, Sanger/Nanopore sequence reads, and liquid-handler CSV runs in one typed graph — with zero-click `21 CFR Part 11` audit trails.
- **Section Highlights:**
  - **384-well plate map keyboard grid:** Assign titrations, replicates, and DMSO controls in seconds without dragging tiny mouse cells in nitrile gloves.
  - **Sequence-aware versioning:** Visualizes codon optimizations, restriction sites, and primer overhangs directly inside protocol steps.
- **CTA:** Explore live CRISPR knockout notebook

### 3. Regulatory & Bench UX Microcopy
- **Protocol countersignature modal (`21 CFR Part 11`):** `Signing locks Experiment EXP-2026-118 permanently. Any post-signature correction must be recorded as a timestamped addendum with a stated scientific reason.`
- **Freezer rack barcode mismatch toast:** `Vial BC-90412 belongs to Passage 14 (expected Passage 6 per protocol step 3). Scan another aliquot or log a deliberate protocol deviation.`

### 4. OKLCH Palette & `zimage_prompts.json`
- Crisp laboratory precision: borosilicate white `oklch(0.985 0.003 235)`, carbon ink `oklch(0.17 0.012 250)`,cobalt reagent marker `oklch(0.52 0.18 256)`.

```json
{
  "model": "Tongyi-MAI/Z-Image-Turbo",
  "scenes": [
    {
      "id": "wetlab_multichannel_pipette_plate",
      "usage": "Product hero visual",
      "prompt": "Crisp editorial science photograph of a researcher hand in slate-blue nitrile glove holding a precision 12-channel micropipette over a crystal-clear 384-well optical assay plate on a clean anodized aluminum cooling block, soft laboratory daylight, shallow depth of field with stainless biosafety cabinet in background, 85mm lens, clean modern biotech aesthetic."
    }
  ]
}
```""",
        },
    ]


def get_unique_agentic_ru_workflows() -> list[dict[str, Any]]:
    """Return 8 strictly 1-of-1 Russian multi-step tool-calling workflows across 18 distinct tools.

    Every workflow uses a disjoint toolset, structured `tool_calls` matching JSON Schema `required`
    parameters, native `tool` role responses (wrapped into `<tool_response>` by Qwen3.8 Jinja),
    and a concise Russian engineering resolution (zero cloned HTML skeletons).
    """
    return [
        # 1. TypeScript strictness & race-condition fix workflow
        {
            "key": "ag_ru_tsc_dag_fix",
            "subdomain": "agentic_typescript_build_ru",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_project_file",
                        "description": "Прочитать исходный текстовый файл проекта в кодировке UTF-8 по относительному пути.",
                        "parameters": {
                            "type": "object",
                            "properties": {"path": {"type": "string", "description": "Относительный путь к файлу в рабочей директории проекта."}},
                            "required": ["path"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "run_tsc_strict",
                        "description": "Запустить строгую проверку типов компилятора TypeScript с флагами --noEmit --strict.",
                        "parameters": {
                            "type": "object",
                            "properties": {"entry": {"type": "string", "description": "Проверяемый входной модуль TypeScript."}},
                            "required": ["entry"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "apply_file_patch",
                        "description": "Точечно заменить фрагмент кода в файле проекта и сохранить изменения на диск.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "Путь к изменяемому файлу."},
                                "old_snippet": {"type": "string", "description": "Исходный фрагмент для замены."},
                                "new_snippet": {"type": "string", "description": "Новый исправленный фрагмент."},
                            },
                            "required": ["path", "old_snippet", "new_snippet"],
                        },
                    },
                },
            ],
            "messages": [
                {
                    "role": "user",
                    "content": "При сборке серверной очереди задач падает строгая проверка типов в модуле `src/queue/taskRunner.ts`. Прочитай файл, запусти строгий компилятор TypeScript, выясни точную причину конфликта типов таймера между браузерным окружением и Node.js, внеси аккуратный патч и убедись, что повторная проверка проходит без единого предупреждения.",
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"type": "function", "function": {"name": "read_project_file", "arguments": {"path": "src/queue/taskRunner.ts"}}},
                        {"type": "function", "function": {"name": "run_tsc_strict", "arguments": {"entry": "src/queue/taskRunner.ts"}}},
                    ],
                },
                {
                    "role": "tool",
                    "content": '{"path":"src/queue/taskRunner.ts","content":"export async function withDeadline<T>(work: () => Promise<T>, ms: number): Promise<T> {\\n  let timer: number | undefined;\\n  const timeout = new Promise<never>((_, rej) => { timer = setTimeout(() => rej(new Error(\'Timeout\')), ms); });\\n  try { return await Promise.race([work(), timeout]); } finally { clearTimeout(timer); }\\n}"}',
                },
                {
                    "role": "tool",
                    "content": '{"exit_code":2,"diagnostics":["src/queue/taskRunner.ts(3,53): error TS2322: Type \'Timeout\' is not assignable to type \'number\'."]}',
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "apply_file_patch",
                                "arguments": {
                                    "path": "src/queue/taskRunner.ts",
                                    "old_snippet": "let timer: number | undefined;\n  const timeout = new Promise<never>((_, rej) => { timer = setTimeout(() => rej(new Error('Timeout')), ms); });\n  try { return await Promise.race([work(), timeout]); } finally { clearTimeout(timer); }",
                                    "new_snippet": "let timer: ReturnType<typeof setTimeout> | undefined;\n  const timeout = new Promise<never>((_, rej) => { timer = setTimeout(() => rej(new Error('Timeout')), ms); });\n  try { return await Promise.race([work(), timeout]); } finally { if (timer !== undefined) clearTimeout(timer); }",
                                },
                            },
                        },
                        {"type": "function", "function": {"name": "run_tsc_strict", "arguments": {"entry": "src/queue/taskRunner.ts"}}},
                    ],
                },
                {"role": "tool", "content": '{"patched":true,"bytes_written":328}'},
                {"role": "tool", "content": '{"exit_code":0,"diagnostics":[]}'},
                {
                    "role": "assistant",
                    "content": "Причина сбоя строгой компиляции (`TS2322`) заключалась в жёстком объявлении переменной таймера как числового типа: в клиентском браузерном окружении глобальная функция установки задержки действительно возвращает целое число, однако при подключённых серверных определениях типов глобальная перегрузка возвращает объектный дескриптор таймера с методами управления циклом событий.\n\nАннотация переменной заменена на выводимый тип возвращаемого значения функции таймера с явной проверкой перед очисткой, что обеспечивает полную совместимость кода как в серверной среде исполнения, так и при сборке под браузер, гарантируя корректное снятие отложенного обработчика в блоке завершения даже при мгновенном выполнении целевой задачи. Повторная проверка компилятором завершилась с нулевым кодом возврата и пустым списком диагностических замечаний.",
                },
            ],
        },
        # 2. Deterministic CSP SHA-256 hash computation & header verification
        {
            "key": "ag_ru_csp_sha256_headers",
            "subdomain": "agentic_csp_security_ru",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "extract_inline_blocks",
                        "description": "Извлечь встроенные теги скриптов и стилей и вычислить их криптографические хеши SHA-256 в кодировке Base64.",
                        "parameters": {
                            "type": "object",
                            "properties": {"html_path": {"type": "string", "description": "Путь к итоговому HTML-документу."}},
                            "required": ["html_path"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "write_edge_headers",
                        "description": "Записать файл конфигурации заголовков безопасности HTTP для периферийного веб-сервера.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "headers_path": {"type": "string", "description": "Путь сохранения файла заголовков."},
                                "policy_body": {"type": "string", "description": "Полное текстовое содержимое правил заголовков."},
                            },
                            "required": ["headers_path", "policy_body"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "verify_csp_compliance",
                        "description": "Проверить соответствие встроенных блоков HTML-страницы строгой политике безопасности контента.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "html_path": {"type": "string", "description": "Путь к проверяемому HTML-файлу."},
                                "headers_path": {"type": "string", "description": "Путь к файлу правил заголовков."},
                            },
                            "required": ["html_path", "headers_path"],
                        },
                    },
                },
            ],
            "messages": [
                {
                    "role": "user",
                    "content": "Подготовь статическую сборку `dist/index.html` к публикации на строгом контуре безопасности: вычисли точные криптографические хеши всех встроенных блоков стилей и сценариев, сформируй файл `dist/_headers` с запретом `'unsafe-inline'` и встраивания во фреймы, а затем выполни автоматическую сверку политики.",
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"type": "function", "function": {"name": "extract_inline_blocks", "arguments": {"html_path": "dist/index.html"}}},
                    ],
                },
                {
                    "role": "tool",
                    "content": '{"scripts":["sha256-8mK4pQ2vL9xR1tZ7wB5cF3jH6dG0sA4eU9iV2mN5oW8="],"styles":["sha256-3nL9vP4xK2mR8tZ1wC6bF7jH5dG0sA2eU8iV4mN1oQ4="]}',
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "write_edge_headers",
                                "arguments": {
                                    "headers_path": "dist/_headers",
                                    "policy_body": "/*\n  Content-Security-Policy: default-src 'none'; script-src 'self' 'sha256-8mK4pQ2vL9xR1tZ7wB5cF3jH6dG0sA4eU9iV2mN5oW8='; style-src 'self' 'sha256-3nL9vP4xK2mR8tZ1wC6bF7jH5dG0sA2eU8iV4mN1oQ4='; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'\n  X-Content-Type-Options: nosniff\n",
                                },
                            },
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "verify_csp_compliance",
                                "arguments": {"html_path": "dist/index.html", "headers_path": "dist/_headers"},
                            },
                        },
                    ],
                },
                {"role": "tool", "content": '{"written":true}'},
                {"role": "tool", "content": '{"status":"PASS","blocked_inline_scripts":0,"blocked_inline_styles":0,"unsafe_inline_present":false}'},
                {
                    "role": "assistant",
                    "content": "Для всех встроенных блоков стилей и сценариев в статической сборке вычислены детерминированные криптографические отпечатки и записаны в файл правил заголовков периферийного сервера. Базовая запрещающая директива по умолчанию в сочетании с явным белым списком проверенных хешей, запретом подмены базового адреса документа и полным запретом отображения страницы внутри сторонних фреймов надёжно блокирует выполнение внедрённого пользовательского кода и перехват кликов. Повторная инструментальная сверка подтвердила нулевое число заблокированных легитимных ресурсов и полное отсутствие небезопасных встроенных разрешений.",
                },
            ],
        },
        # 3. WCAG OKLCH contrast & mobile 375px overflow audit
        {
            "key": "ag_ru_wcag_oklch_responsive",
            "subdomain": "agentic_accessibility_css_ru",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "audit_wcag_contrast",
                        "description": "Проверить коэффициенты визуального контраста цветовых токенов CSS по стандарту доступности WCAG 2.2 AA.",
                        "parameters": {
                            "type": "object",
                            "properties": {"css_path": {"type": "string", "description": "Путь к таблице стилей."}},
                            "required": ["css_path"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "test_viewport_overflow",
                        "description": "Измерить горизонтальное переполнение документа при заданной ширине мобильного экрана.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "url_or_file": {"type": "string", "description": "Проверяемый HTML-файл страницы."},
                                "width": {"type": "integer", "description": "Ширина окна просмотра в пикселях."},
                            },
                            "required": ["url_or_file", "width"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "update_css_tokens",
                        "description": "Обновить значения цветовых переменных OKLCH и правила селекторов в CSS-файле.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "css_path": {"type": "string", "description": "Путь к таблице стилей."},
                                "updates": {"type": "object", "description": "Словарь обновляемых токенов и правил."},
                            },
                            "required": ["css_path", "updates"],
                        },
                    },
                },
            ],
            "messages": [
                {
                    "role": "user",
                    "content": "Прогони автоматический аудит контрастности цветовых переменных в `styles/theme.css` и проверку вёрстки тарифной страницы `public/pricing.html` на узком мобильном вьюпорте `375px`. Найденные нарушения доступности и горизонтального скролла исправь и подтверди повторным замером.",
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"type": "function", "function": {"name": "audit_wcag_contrast", "arguments": {"css_path": "styles/theme.css"}}},
                        {"type": "function", "function": {"name": "test_viewport_overflow", "arguments": {"url_or_file": "public/pricing.html", "width": 375}}},
                    ],
                },
                {
                    "role": "tool",
                    "content": '{"failures":[{"pair":"--text-muted on --surface-card","fg":"oklch(0.68 0.02 250)","bg":"oklch(0.95 0.01 250)","ratio":3.12,"required":4.5}]}',
                },
                {
                    "role": "tool",
                    "content": '{"scrollWidth":428,"innerWidth":375,"offending_selector":".pricing-compare-table","min_width_px":420}',
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "update_css_tokens",
                                "arguments": {
                                    "css_path": "styles/theme.css",
                                    "updates": {
                                        "--text-muted": "oklch(0.45 0.02 250)",
                                        ".pricing-compare-table": "width: 100%; min-width: 0; overflow-x: auto; display: block;",
                                    },
                                },
                            },
                        },
                        {"type": "function", "function": {"name": "audit_wcag_contrast", "arguments": {"css_path": "styles/theme.css"}}},
                        {"type": "function", "function": {"name": "test_viewport_overflow", "arguments": {"url_or_file": "public/pricing.html", "width": 375}}},
                    ],
                },
                {"role": "tool", "content": '{"updated":true}'},
                {"role": "tool", "content": '{"failures":[],"min_ratio":5.84}'},
                {"role": "tool", "content": '{"scrollWidth":375,"innerWidth":375,"offending_selector":null}'},
                {
                    "role": "assistant",
                    "content": "Оба дефекта устранены и перепроверены инструментально:\n1. Перцептивная светлота вторичного приглушённого текста скорректирована в цветовом пространстве с сохранением исходного холодного оттенка и насыщенности, благодаря чему коэффициент визуального контраста на светлой карточке вырос с `3.12:1` до `5.84:1`, обеспечивая уверенный запас выше обязательного порога доступности `4.5:1`.\n2. Сравнительная таблица тарифов освобождена от жёстко заданной минимальной ширины и переведена на адаптивный блочный контейнер с внутренней прокруткой при необходимости: на мобильном экране шириной `375` пикселей страница укладывается без малейшего горизонтального разъезда макета.",
                },
            ],
        },
        # 4. Schema.org JSON-LD validation & llms.txt sync
        {
            "key": "ag_ru_jsonld_llms_validation",
            "subdomain": "agentic_seo_schema_ru",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "validate_jsonld_graph",
                        "description": "Проверить корректность встроенного графа структурированных данных Schema.org JSON-LD в HTML-файле.",
                        "parameters": {
                            "type": "object",
                            "properties": {"html_path": {"type": "string", "description": "Путь к HTML-странице."}},
                            "required": ["html_path"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "check_llms_txt_links",
                        "description": "Проверить структуру заголовков Markdown и доступность всех внутренних маршрутов в файле llms.txt.",
                        "parameters": {
                            "type": "object",
                            "properties": {"llms_path": {"type": "string", "description": "Путь к файлу llms.txt."}},
                            "required": ["llms_path"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "write_utf8_file",
                        "description": "Сохранить исправленное содержимое текстового файла в кодировке UTF-8.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "Целевой путь файла."},
                                "content": {"type": "string", "description": "Полный обновлённый текст файла."},
                            },
                            "required": ["path", "content"],
                        },
                    },
                },
            ],
            "messages": [
                {
                    "role": "user",
                    "content": "Перед релизом образовательной страницы `site/course.html` проверь валидность графа микроразметки `JSON-LD` и актуальность маршрутов в индексном файле для языковых моделей `site/llms.txt`. Если найдутся битые ссылки — исправь их и перепроверь.",
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"type": "function", "function": {"name": "validate_jsonld_graph", "arguments": {"html_path": "site/course.html"}}},
                        {"type": "function", "function": {"name": "check_llms_txt_links", "arguments": {"llms_path": "site/llms.txt"}}},
                    ],
                },
                {
                    "role": "tool",
                    "content": '{"valid":true,"entities":["EducationalOrganization","Course","Offer"],"warnings":[]}',
                },
                {
                    "role": "tool",
                    "content": '{"valid":false,"broken_links":[{"url":"/syllabus-2025","status":404,"suggested":"/syllabus-2026"}]}',
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "write_utf8_file",
                                "arguments": {
                                    "path": "site/llms.txt",
                                    "content": "# Инженерный курс по распределённым системам\n\n> Практикум по алгоритмам консенсуса Raft, репликации журналов и тестированию отказоустойчивости.\n\n## Разделы\n- [Учебная программа 2026](/syllabus-2026): расписание модулей и лабораторных работ.\n- [Требования к поступающим](/admissions): входное профильное задание на Go или Rust.\n",
                                },
                            },
                        },
                        {"type": "function", "function": {"name": "check_llms_txt_links", "arguments": {"llms_path": "site/llms.txt"}}},
                    ],
                },
                {"role": "tool", "content": '{"saved":true}'},
                {"role": "tool", "content": '{"valid":true,"broken_links":[]}'},
                {
                    "role": "assistant",
                    "content": "Инструментальная проверка показала, что связанные сущности образовательной организации, учебного курса и коммерческого предложения на странице размечены без единого замечания, однако в индексном файле для языковых систем оставалась устаревшая ссылка на прошлогодний учебный план, возвращавшая ошибку отсутствия ресурса. Адрес обновлён на действующую программу текущего года, а повторная автоматическая проверка подтвердила полную целостность всех маршрутов.",
                },
            ],
        },
        # 5. Z-Image asset generation + AVIF compression + LCP preload
        {
            "key": "ag_ru_zimage_avif_pipeline",
            "subdomain": "agentic_media_pipeline_ru",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "generate_zimage_turbo",
                        "description": "Сгенерировать редакционную иллюстрацию локальной моделью Z-Image-Turbo через последовательное переключение без свопа.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "prompt": {"type": "string", "description": "Детальное фотографическое описание кадра."},
                                "width": {"type": "integer", "description": "Ширина изображения в пикселях."},
                                "height": {"type": "integer", "description": "Высота изображения в пикселях."},
                                "out_png": {"type": "string", "description": "Путь сохранения исходного PNG."},
                            },
                            "required": ["prompt", "width", "height", "out_png"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "encode_responsive_avif",
                        "description": "Сжать исходный PNG в адаптивные варианты формата AVIF с контролем максимального веса в килобайтах.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "src_png": {"type": "string", "description": "Путь к мастер-файлу PNG."},
                                "max_kb": {"type": "integer", "description": "Верхний предел размера файла в килобайтах."},
                            },
                            "required": ["src_png", "max_kb"],
                        },
                    },
                },
            ],
            "messages": [
                {
                    "role": "user",
                    "content": "Сгенерируй через локальный конвейер `Z-Image-Turbo` предметную фотографию матовой керамической воронки для заваривания кофе (`1280×800`) для первого экрана магазина и подготовь адаптивные AVIF-файлы весом строго не более `95 КБ`, чтобы удержать быстрый показатель `LCP`.",
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "generate_zimage_turbo",
                                "arguments": {
                                    "prompt": "Studio product photograph of a ribbed matte stoneware pour-over coffee dripper resting on a smoked oak stand, soft morning window light, warm stone background, 85mm lens.",
                                    "width": 1280,
                                    "height": 800,
                                    "out_png": "assets/raw/dripper_hero.png",
                                },
                            },
                        },
                    ],
                },
                {"role": "tool", "content": '{"status":"ok","out_png":"assets/raw/dripper_hero.png","bytes":1482910,"swap_pages_out":0}'},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "encode_responsive_avif",
                                "arguments": {"src_png": "assets/raw/dripper_hero.png", "max_kb": 95},
                            },
                        },
                    ],
                },
                {
                    "role": "tool",
                    "content": '{"variants":[{"path":"assets/img/dripper_hero_640w.avif","kb":38.4},{"path":"assets/img/dripper_hero_1280w.avif","kb":84.2}],"ssim":0.986}',
                },
                {
                    "role": "assistant",
                    "content": "Предметная фотография матовой керамической воронки в разрешении `1280×800` успешно сгенерирована локальным графическим конвейером без вытеснения памяти в файл подкачки и сжата в два адаптивных файла современного формата: облегчённый мобильный вариант (`38.4 КБ`) и полноразмерный вариант для широких экранов (`84.2 КБ`, что укладывается в жёсткий порог `95 КБ` при высоком индексе структурного сходства `0.986`). При подключении ключевого изображения первого экрана в разметку обязательно задайте высокий приоритет загрузки, асинхронное декодирование и фиксированные геометрические пропорции контейнера, чтобы полностью исключить визуальный скачок вёрстки при отрисовке.",
                },
            ],
        },
        # 6. PostgreSQL N+1 query profiling & composite index migration
        {
            "key": "ag_ru_sql_explain_index",
            "subdomain": "agentic_backend_perf_ru",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "explain_sql_query",
                        "description": "Выполнить анализ плана запроса EXPLAIN (ANALYZE, BUFFERS) на стендовой реплике базы данных PostgreSQL.",
                        "parameters": {
                            "type": "object",
                            "properties": {"sql": {"type": "string", "description": "Текст диагностируемого SQL-запроса."}},
                            "required": ["sql"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "create_sql_migration",
                        "description": "Создать идемпотентный файл миграции базы данных без блокировки таблиц.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "migration_name": {"type": "string", "description": "Имя файла миграции."},
                                "up_sql": {"type": "string", "description": "DDL-команды накатывания миграции."},
                            },
                            "required": ["migration_name", "up_sql"],
                        },
                    },
                },
            ],
            "messages": [
                {
                    "role": "user",
                    "content": "Серверный маршрут истории покупок `/api/orders` отвечает около `410 мс` под нагрузкой. Сними реальный план выполнения `EXPLAIN (ANALYZE, BUFFERS)` для выборки 20 последних оплаченных заказов по полю `account_id` и подготовь безопасную миграцию индекса без остановки записи в рабочую таблицу.",
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "explain_sql_query",
                                "arguments": {
                                    "sql": "SELECT id, total_cents, created_at FROM orders WHERE account_id = 'acc_9042' AND status = 'paid' ORDER BY created_at DESC LIMIT 20;",
                                },
                            },
                        },
                    ],
                },
                {
                    "role": "tool",
                    "content": '{"plan":"Limit (actual time=398.4..398.5 ms) -> Sort (created_at DESC) -> Seq Scan on orders (Filter: account_id = \'acc_9042\' AND status = \'paid\', Rows Removed by Filter: 1842900, Buffers: shared hit=14210 read=9840)"}',
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "create_sql_migration",
                                "arguments": {
                                    "migration_name": "20261111_idx_orders_account_paid_created",
                                    "up_sql": "-- migrate: no-transaction\nCREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_account_paid_created\n  ON orders (account_id, created_at DESC)\n  INCLUDE (total_cents)\n  WHERE status = 'paid';\n",
                                },
                            },
                        },
                    ],
                },
                {"role": "tool", "content": '{"path":"db/migrations/20261111_idx_orders_account_paid_created.sql","created":true}'},
                {
                    "role": "assistant",
                    "content": "Диагностика буферов показала полное последовательное чтение всей таблицы заказов с отбрасыванием `1,84 млн` неподходящих записей, внешней сортировкой на лету и чтением `9 840` дисковых страниц, что и вызывало просадку времени ответа до четырёхсот миллисекунд.\n\nСоздан файл безопасной миграции с отключением транзакционной обёртки и неблокирующим построением индекса в фоновом режиме. Частичный покрывающий индекс по составному ключу идентификатора клиента и убывающей даты создания с фильтром только оплаченных заказов и включением суммы платежа непосредственно в листовые страницы индекса переводит запрос на чтение исключительно по индексу без обращения к основной куче таблицы и без остановки параллельной записи.",
                },
            ],
        },
        # 7. SVG optimization & JS bundle budget enforcement
        {
            "key": "ag_ru_svg_bundle_budget",
            "subdomain": "agentic_perf_budget_ru",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "inspect_bundle_stats",
                        "description": "Получить сводку размеров сжатых клиентских ресурсов JS, CSS и SVG относительно установленного лимита.",
                        "parameters": {
                            "type": "object",
                            "properties": {"build_dir": {"type": "string", "description": "Директория собранных клиентских артефактов."}},
                            "required": ["build_dir"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "optimize_inline_svg",
                        "description": "Очистить векторный файл SVG от редакторских метаданных и округлить координаты кривых Безье.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "svg_path": {"type": "string", "description": "Путь к оптимизируемому SVG-файлу."},
                                "precision": {"type": "integer", "description": "Число знаков после запятой для координат."},
                            },
                            "required": ["svg_path", "precision"],
                        },
                    },
                },
            ],
            "messages": [
                {
                    "role": "user",
                    "content": "В CI сработало ограничение на вес клиентской сборки в каталоге `build/client` (порог `120 КБ` в gzip). Найди самый тяжёлый ассет, выполни безопасную векторную оптимизацию без искажения геометрии подписей и убедись, что сборка уложилась в бюджет.",
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"type": "function", "function": {"name": "inspect_bundle_stats", "arguments": {"build_dir": "build/client"}}},
                    ],
                },
                {
                    "role": "tool",
                    "content": '{"total_gzip_kb":164.2,"budget_gzip_kb":120.0,"largest":[{"file":"assets/campus-map.svg","raw_kb":312.0,"gzip_kb":78.5},{"file":"assets/app.js","raw_kb":118.0,"gzip_kb":41.2}]}',
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"type": "function", "function": {"name": "optimize_inline_svg", "arguments": {"svg_path": "build/client/assets/campus-map.svg", "precision": 1}}},
                        {"type": "function", "function": {"name": "inspect_bundle_stats", "arguments": {"build_dir": "build/client"}}},
                    ],
                },
                {"role": "tool", "content": '{"before_raw_kb":312.0,"after_raw_kb":54.6,"removed_editor_nodes":418}'},
                {"role": "tool", "content": '{"total_gzip_kb":101.4,"budget_gzip_kb":120.0,"status":"WITHIN_BUDGET"}'},
                {
                    "role": "assistant",
                    "content": "Анализ весовой сводки выявил причину перерасхода бюджета: необработанная векторная схема кампуса занимала `312 КБ` (`78.5 КБ` в сжатом виде) из-за оставшихся служебных пространств имён настольного графического редактора и избыточной восьмизначной дробной точности опорных точек кривых. Безопасная очистка `418` скрытых редакторских узлов и округление координат до одного десятичного знака сократили исходный файл до `54.6 КБ` без искажения контуров зданий и подписей, а общий сжатый размер клиентской директории снизился со `164.2 КБ` до `101.4 КБ` при установленном пороге `120 КБ`.",
                },
            ],
        },
        # 8. WebGL GLSL fragment shader compilation check & precision fix
        {
            "key": "ag_ru_webgl_glsl_shader_fix",
            "subdomain": "agentic_webgl_shader_ru",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "validate_glsl_shader",
                        "description": "Скомпилировать вершинный или фрагментный шейдер GLSL ES 3.00 в эталонном валидаторе WebGL2.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "shader_path": {"type": "string", "description": "Путь к файлу исходного кода шейдера."},
                                "stage": {"type": "string", "description": "Стадия конвейера: vertex или fragment."},
                            },
                            "required": ["shader_path", "stage"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "patch_shader_source",
                        "description": "Заменить строки исходного кода в файле шейдера GLSL и сохранить правку.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "shader_path": {"type": "string", "description": "Путь к файлу шейдера."},
                                "find": {"type": "string", "description": "Заменяемый фрагмент кода."},
                                "replace": {"type": "string", "description": "Исправленный фрагмент кода."},
                            },
                            "required": ["shader_path", "find", "replace"],
                        },
                    },
                },
            ],
            "messages": [
                {
                    "role": "user",
                    "content": "Интерактивный водный фон на мобильных устройствах остаётся пустым: в консоли ошибка компиляции фрагментного шейдера `shaders/caustics.frag` под WebGL2 (`GLSL ES 3.00`). Запусти валидатор шейдеров, определи точную причину отказа компилятора, внеси исправление и убедись в успешной сборке.",
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"type": "function", "function": {"name": "validate_glsl_shader", "arguments": {"shader_path": "shaders/caustics.frag", "stage": "fragment"}}},
                    ],
                },
                {
                    "role": "tool",
                    "content": '{"ok":false,"log":"ERROR: 0:4: \'float\' : No precision specified for (float)\\nERROR: 0:12: \'u_time\' : syntax error"}',
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "patch_shader_source",
                                "arguments": {
                                    "shader_path": "shaders/caustics.frag",
                                    "find": "#version 300 es\nuniform float u_time;",
                                    "replace": "#version 300 es\nprecision highp float;\nuniform float u_time;",
                                },
                            },
                        },
                        {"type": "function", "function": {"name": "validate_glsl_shader", "arguments": {"shader_path": "shaders/caustics.frag", "stage": "fragment"}}},
                    ],
                },
                {"role": "tool", "content": '{"patched":true}'},
                {"role": "tool", "content": '{"ok":true,"log":"","uniforms":["u_time","u_resolution"]}'},
                {
                    "role": "assistant",
                    "content": "Причина отказа компиляции на мобильных графических ускорителях заключается в строгом требовании стандарта шейдерного языка явно указывать квалификатор разрядности для чисел с плавающей точкой во фрагментной стадии конвейера. Чтобы расчёт фазы водной каустики от времени выполнялся плавно и без ступенчатого распада градиента на длинных сессиях, сразу после заголовочной директивы версии добавлено объявление высокой точности вычислений. Повторный прогон эталонного валидатора завершился успешно, все входные переменные времени и разрешения экрана распознаны корректно.",
                },
            ],
        },
    ]

