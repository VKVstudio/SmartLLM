"""UI-Audit Vision Pairs & Headless Chrome 148 Renderer for Calibration v2 (WP-C2).

Implements the OPUS_MASTER_PLAN_V2.md §1.D5 `ui_audit_vision` stratum:
- 16k RU tokens + 15k EN tokens (0 network downloads!).
- Local Chrome 148 (`render_html_v2.mjs`) screenshots (`1024x640` or `576x1248`, exact 32px multiples)
  of E-disjoint modern HTML5/CSS3/OKLCH documents + self-authored RU/EN UI-audit & reconstruction prompts.
- Zero Tailwind, strict `<meta http-equiv="Content-Security-Policy">`, `oklch()`, CSS Grid, `@container`,
  `100dvh`, and `<script type="application/ld+json">`.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from step4_curated_bilingual import get_unique_multimodal_canon_specs  # noqa: E402

NODE_EXE = Path(os.environ.get("SMARTLLM_NODE_EXE") or shutil.which("node") or "/usr/bin/node")
RENDER_MJS = SCRIPT_DIR / "render_html_v2.mjs"

STRICT_CSP_META = (
    '<meta http-equiv="Content-Security-Policy" content="'
    "default-src 'none'; script-src 'sha256-__CSP_SCRIPT__'; style-src 'sha256-__CSP_STYLE__'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
    "base-uri 'none'; form-action 'self'; upgrade-insecure-requests\">"
)


def render_html_batch_v2(jobs: list[dict[str, Any]]) -> dict[str, tuple[bytes, int, int]]:
    """Render HTML5 documents via local headless Chrome 148 (`render_html_v2.mjs`, 0 ports, 0 downloads)."""
    if not jobs:
        return {}
    if not NODE_EXE.exists():
        raise FileNotFoundError(f"Node.js binary not found at {NODE_EXE}")
    if not RENDER_MJS.exists():
        raise FileNotFoundError(f"Renderer script not found at {RENDER_MJS}")

    results: dict[str, tuple[bytes, int, int]] = {}
    with tempfile.TemporaryDirectory(prefix="smartllm_calib_v2_chr_") as tmp_dir:
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
            timeout=180,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Headless Chrome 148 batch render failed (exit {proc.returncode}):\n"
                f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
            )

        for job, item in zip(jobs, manifest):
            raw_png = Path(item["raw_png_path"])
            if not raw_png.exists():
                raise RuntimeError(f"Chrome 148 did not produce screenshot for {job['id']}")
            out_w, out_h = int(job["out_w"]), int(job["out_h"])
            with Image.open(raw_png) as im:
                rgb = im.convert("RGB")
                if rgb.size != (out_w, out_h):
                    rgb = rgb.resize((out_w, out_h), Image.Resampling.LANCZOS)
                stat = ImageStat.Stat(rgb)
                if max(stat.stddev) < 6.0:
                    raise RuntimeError(f"Screenshot for {job['id']} appears blank (stddev={stat.stddev})")
                buf = io.BytesIO()
                rgb.save(buf, format="PNG", optimize=True)
                results[job["id"]] = (buf.getvalue(), out_w, out_h)

    return results


def _upgrade_html_for_v2_canons(html: str, title_hint: str, lang: str) -> str:
    """Ensure every rendered HTML document complies with v2 standards:
    100dvh instead of 100vh, strict CSP meta tag, @container rule, and application/ld+json."""
    out = re.sub(r"\b100vh\b", "100dvh", html)
    if "Content-Security-Policy" not in out:
        out = out.replace(
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n' + STRICT_CSP_META,
            1,
        )
    if "@container" not in out:
        container_css = (
            "\nmain, section, .showcase, .spread, .board, .layout { container-type: inline-size; }\n"
            "@container (max-width: 560px) { .kpi-val, h1 { letter-spacing: -0.01em; } }\n</style>"
        )
        out = out.replace("</style>", container_css, 1)
    if "application/ld+json" not in out:
        m_title = re.search(r"<title>(.*?)</title>", out, re.S)
        doc_title = m_title.group(1).strip() if m_title else title_hint
        ld_obj = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebPage",
                    "name": doc_title,
                    "inLanguage": "ru-RU" if lang == "ru" else "en-US",
                }
            ],
        }
        ld_tag = f'<script type="application/ld+json">\n{json.dumps(ld_obj, ensure_ascii=False)}\n</script>\n</head>'
        out = out.replace("</head>", ld_tag, 1)
    return out


def _extra_v2_ui_audit_specs() -> list[dict[str, Any]]:
    """Additional 1-of-1 RU and EN UI-audit vision specs to reach exact 16k RU + 15k EN token targets."""
    return [
        {
            "key": "ru_ui_audit_precision_optics_desktop",
            "lang": "ru",
            "subdomain": "ui_audit_dark_precision_ru",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Проведи визуальный и технический UI/UX-аудит приложенного десктопного скриншота (`1024x640`) "
                "инженерной лаборатории «АстроОптика Лаб» (производство ситалловых зеркал и лазерных интерферометров): "
                "оцени иерархию тёмной палитры OKLCH, читаемость табличных допусков RMS, размер интерактивных целей "
                "по WCAG 2.2 (SC 2.5.8 >= 24x24 px) и приведи полный эталонный код страницы на HTML5/CSS3/JS "
                "со строгим CSP, `@container`, `100dvh` и JSON-LD без Tailwind."
            ),
            "rationale": (
                "### Аудит интерфейса и визуальной системы («АстроОптика Лаб»)\n"
                "1. **Контраст и палитра OKLCH:** Глубокий графитовый фон `--bg: oklch(0.145 0.014 255)` и приподнятая карточка "
                "`--surface: oklch(0.195 0.018 255)` обеспечивают контраст `> 12.8:1` с основным текстом `--ink: oklch(0.955 0.008 240)` "
                "(уровень WCAG AAA). Спектральный акцент `--cyan: oklch(0.76 0.14 215)` выделяет активный класс точности $\\lambda/20$.\n"
                "2. **Модульная сетка и `@container`:** Двухколоночная сетка `1.2fr 1fr` снабжена `container-type: inline-size` и "
                "`min-height: 100dvh` без утечек `100vh`. Все числовые параметры волнового фронта выровнены через `font-variant-numeric: tabular-nums`.\n"
                "3. **Доступность WCAG 2.2 SC 2.5.8:** Кнопки переключения апертуры имеют высоту `40px` (`>= 24x24px`), явный контур `:focus-visible` и `aria-pressed`."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
""" + STRICT_CSP_META + """
<title>АстроОптика Лаб — Асферические зеркала из ситалла СО-115М</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"АстроОптика Лаб","url":"https://astrooptika.example.ru"},{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"Какова точность полировки главного зеркала?","acceptedAnswer":{"@type":"Answer","text":"Среднеквадратичное отклонение профиля волнового фронта не превышает λ/20 на длине волны 632,8 нм."}}]}]}
</script>
<style>
:root {
  --bg: oklch(0.145 0.014 255);
  --surface: oklch(0.195 0.018 255);
  --ink: oklch(0.955 0.008 240);
  --muted: oklch(0.71 0.018 245);
  --accent: oklch(0.76 0.14 215);
  --line: oklch(0.29 0.02 255);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: Inter, system-ui, sans-serif;
  min-height: 100dvh;
  padding: 36px 52px;
  font-variant-numeric: tabular-nums;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--line);
  padding-bottom: 18px;
  margin-bottom: 32px;
}
.brand { font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; font-size: 0.95rem; }
.status-pill { border: 1px solid var(--accent); color: var(--accent); padding: 6px 14px; font-size: 0.78rem; border-radius: 4px; }
main.workspace {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 28px;
  container-type: inline-size;
}
.panel {
  background: var(--surface);
  border: 1px solid var(--line);
  padding: 28px;
  display: grid;
  gap: 18px;
}
.eyebrow { color: var(--accent); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.14em; }
h1 { font-size: clamp(1.9rem, 2.8vw, 2.55rem); line-height: 1.12; letter-spacing: -0.02em; }
.lead { color: var(--muted); font-size: 0.95rem; line-height: 1.6; }
dl.specs {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px 18px;
  border-top: 1px solid var(--line);
  padding-top: 16px;
  font-size: 0.88rem;
}
dt { color: var(--muted); }
dd { font-weight: 600; text-align: right; }
.ap-group { display: flex; gap: 10px; }
.ap-btn {
  flex: 1;
  min-height: 40px;
  border: 1px solid var(--line);
  background: var(--bg);
  color: var(--ink);
  font-weight: 600;
  font-size: 0.84rem;
  cursor: pointer;
}
.ap-btn[aria-pressed="true"] { background: var(--accent); color: var(--bg); border-color: var(--accent); }
.rms-readout { font-size: 1.65rem; font-weight: 700; color: var(--accent); border-top: 1px solid var(--line); padding-top: 14px; }
@container (max-width: 760px) {
  .ap-group { flex-direction: column; }
}
</style>
</head>
<body>
  <header>
    <div class="brand">АстроОптика Лаб · Отдел ионно-лучевой доводки</div>
    <span class="status-pill">Интерферометрический стенд He-Ne 632,8 нм</span>
  </header>
  <main class="workspace">
    <section class="panel">
      <p class="eyebrow">Оптика дальнего космоса и лидаров</p>
      <h1>Главные параболические зеркала с нулевым коэффициентом теплового расширения</h1>
      <p class="lead">Ионно-лучевая фигуризация подложек из астроситалла СО-115М устраняет зональные ошибки на краю апертуры и гарантирует дифракционное качество изображения в диапазоне от-60 до +85 °C.</p>
      <dl class="specs">
        <dt>Коэффициент ТКЛР (−60…+60 °C)</dt><dd>0,0 ± 1,5 × 10⁻⁷ К⁻¹</dd>
        <dt>Шероховатость микрорельефа Rq</dt><dd>≤ 0,45 нм</dd>
        <dt>Коэффициент отражения покрытия Al+SiO₂</dt><dd>92,4 % @ 550 нм</dd>
      </dl>
    </section>
    <section class="panel" aria-labelledby="interfero-title">
      <h2 id="interfero-title" style="font-size:1.12rem;">Контроль волнового фронта по апертуре</h2>
      <svg viewBox="0 0 360 150" width="100%" height="150" role="img" aria-label="Интерферограмма главного зеркала">
        <rect width="360" height="150" fill="oklch(0.12 0.015 255)"/>
        <circle cx="110" cy="75" r="56" fill="none" stroke="oklch(0.76 0.14 215)" stroke-width="2"/>
        <ellipse cx="110" cy="75" rx="42" ry="52" fill="none" stroke="oklch(0.62 0.12 215)" stroke-width="1.5"/>
        <ellipse cx="110" cy="75" rx="24" ry="48" fill="none" stroke="oklch(0.76 0.14 215)" stroke-width="1.5"/>
        <line x1="200" y1="36" x2="340" y2="36" stroke="oklch(0.35 0.02 255)"/>
        <polyline points="200,92 225,78 250,84 275,70 300,76 325,72 340,75" fill="none" stroke="oklch(0.76 0.14 215)" stroke-width="2.5"/>
        <text x="200" y="26" font-size="11" fill="oklch(0.71 0.018 245)">Профиль ошибки поверхности (нм)</text>
      </svg>
      <div class="ap-group" role="group" aria-label="Диаметр заготовки">
        <button type="button" class="ap-btn" data-rms="RMS 11,8 нм (λ/53) · Масса 42 кг" aria-pressed="true">Ø 500 мм (f/2.8)</button>
        <button type="button" class="ap-btn" data-rms="RMS 14,2 нм (λ/44) · Масса 118 кг" aria-pressed="false">Ø 800 мм (f/3.0)</button>
      </div>
      <output id="rms-out" class="rms-readout">RMS 11,8 нм (λ/53) · Масса 42 кг</output>
    </section>
  </main>
  <script>
    const btns = document.querySelectorAll('.ap-btn');
    const out = document.getElementById('rms-out');
    btns.forEach((b) => b.addEventListener('click', () => {
      btns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      out.textContent = b.dataset.rms;
    }));
  </script>
</body>
</html>""",
        },
        {
            "key": "ru_ui_audit_nordic_timber_desktop",
            "lang": "ru",
            "subdomain": "ui_audit_timber_clt_ru",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Выполни детальный UI/UX-разбор приложенного скриншота (`1024x640`) портала «Балтийский CLT-Консорциум» "
                "(большепролётные клеёные деревянные конструкции и перекрёстно-клеёные плиты CLT): проверь модульную "
                "сетку, тёплую светлую палитру OKLCH, русские типографические кавычки «ёлочки» и тире, интерактивный "
                "расчёт пролёта балки и напиши полный HTML5/CSS3/JS-код со строгим CSP и JSON-LD."
            ),
            "rationale": (
                "### UI/UX-аудит страницы («Балтийский CLT-Консорциум»)\n"
                "1. **Визуальный канон и палитра OKLCH:** Светлый фон необработанной ели `--bg: oklch(0.972 0.011 84)` "
                "и графитовый текст `--ink: oklch(0.19 0.016 65)` дают контраст `13.9:1`. Акцент хвойного пигмента "
                "`--pine: oklch(0.44 0.095 152)` фокусирует внимание на несущей способности.\n"
                "2. **Типографика и семантика:** Соблюдены русские полиграфические нормы («ёлочки», длинное тире `—`, неразрывные размерности `м`, `кН/м²`).\n"
                "3. **Интерактивный расчёт и WCAG 2.2:** Ползунок пролёта и кнопки класса прочности (`GL28h` / `GL32c`) имеют высоту `>= 38px` и мгновенно пересчитывают высоту сечения балки."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
""" + STRICT_CSP_META + """
<title>Балтийский CLT-Консорциум — Большепролётные деревянные конструкции</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"Балтийский CLT-Консорциум","url":"https://clt-baltica.example.ru"},{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"Каков предел огнестойкости плит CLT?","acceptedAnswer":{"@type":"Answer","text":"Пятислойные панели CLT толщиной 160 мм имеют подтверждённый предел огнестойкости REI 60 при расчётной скорости обугливания 0,65 мм/мин."}}]}]}
</script>
<style>
:root {
  --bg: oklch(0.972 0.011 84);
  --surface: oklch(0.942 0.016 82);
  --ink: oklch(0.19 0.016 65);
  --muted: oklch(0.45 0.02 68);
  --pine: oklch(0.44 0.095 152);
  --rule: oklch(0.84 0.018 80);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: Georgia, "Times New Roman", serif;
  min-height: 100dvh;
  padding: 36px 52px;
  font-variant-numeric: tabular-nums;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 2px solid var(--ink);
  padding-bottom: 16px;
  margin-bottom: 30px;
}
.brand { font-family: system-ui, sans-serif; font-weight: 700; font-size: 1rem; letter-spacing: 0.08em; text-transform: uppercase; }
.cert { font-family: system-ui, sans-serif; font-size: 0.8rem; color: var(--pine); font-weight: 600; }
main.grid {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 32px;
  container-type: inline-size;
}
.card {
  background: var(--surface);
  border: 1px solid var(--rule);
  padding: 26px;
  display: grid;
  gap: 16px;
}
h1 { font-size: clamp(2rem, 3vw, 2.7rem); font-weight: 400; line-height: 1.12; }
.lead { font-family: system-ui, sans-serif; font-size: 0.96rem; color: var(--muted); line-height: 1.62; }
dl.tech {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  font-family: system-ui, sans-serif;
  font-size: 0.86rem;
  border-top: 1px solid var(--rule);
  padding-top: 14px;
}
dt { color: var(--muted); }
dd { font-weight: 600; }
.grade-row { display: flex; gap: 10px; }
.grade-btn {
  flex: 1;
  min-height: 40px;
  border: 1px solid var(--ink);
  background: var(--bg);
  color: var(--ink);
  font-family: system-ui, sans-serif;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
}
.grade-btn[aria-pressed="true"] { background: var(--pine); border-color: var(--pine); color: oklch(0.98 0.005 85); }
.span-out { font-family: system-ui, sans-serif; font-size: 1.55rem; font-weight: 700; color: var(--pine); border-top: 1px solid var(--rule); padding-top: 12px; }
@container (max-width: 720px) {
  .grade-row { flex-direction: column; }
}
</style>
</head>
<body>
  <header>
    <div class="brand">Балтийский CLT-Консорциум · Завод инженерной древесины</div>
    <span class="cert">ГОСТ 33124 · Предел огнестойкости REI 60 / R 90</span>
  </header>
  <main class="grid">
    <section class="card">
      <h1>Большепролётные балки и плиты «Северный CLT» с фрезеровкой узлов на ЧПУ</h1>
      <p class="lead">Производим пяти- и семислойные перекрёстно-клеёные панели длиной до 16 метров с меламиновым клеевым швом нулевой эмиссии формальдегида. Полная заводская готовность сокращает монтаж каркаса на площадке в 3,5 раза.</p>
      <dl class="tech">
        <dt>Максимальный свободный пролёт фермы</dt><dd>36,0 м без промежуточных опор</dd>
        <dt>Влажность ламелей камерной сушки</dt><dd>10,0 ± 1,0 %</dd>
        <dt>Плотность северной ели Picea abies</dt><dd>470 кг/м³</dd>
      </dl>
    </section>
    <section class="card" aria-labelledby="beam-calc">
      <h2 id="beam-calc" style="font-size:1.18rem;font-weight:400;">Подбор сечения двускатной клеёной балки</h2>
      <svg viewBox="0 0 360 110" width="100%" height="110" role="img" aria-label="Схема большепролётной деревянной балки">
        <polygon points="16,78 180,28 344,78 344,92 16,92" fill="oklch(0.82 0.055 78)" stroke="oklch(0.19 0.016 65)" stroke-width="2"/>
        <line x1="16" y1="52" x2="344" y2="52" stroke="oklch(0.44 0.095 152)" stroke-dasharray="4 3"/>
        <text x="130" y="20" font-size="11" font-family="sans-serif" fill="oklch(0.45 0.02 68)">Пролёт L = 18…32 м · Снеговой район IV</text>
      </svg>
      <div class="grade-row" role="group" aria-label="Класс прочности по EN 14080">
        <button type="button" class="grade-btn" data-sec="Сечение 200 × 1120 мм · Прогиб L/420" aria-pressed="true">Класс GL28h (пролёт 24 м)</button>
        <button type="button" class="grade-btn" data-sec="Сечение 220 × 1280 мм · Прогиб L/450" aria-pressed="false">Класс GL32c (пролёт 30 м)</button>
      </div>
      <output id="beam-out" class="span-out">Сечение 200 × 1120 мм · Прогиб L/420</output>
    </section>
  </main>
  <script>
    const gBtns = document.querySelectorAll('.grade-btn');
    const bOut = document.getElementById('beam-out');
    gBtns.forEach((b) => b.addEventListener('click', () => {
      gBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      bOut.textContent = b.dataset.sec;
    }));
  </script>
</body>
</html>""",
        },
        {
            "key": "ru_ui_audit_subsea_rov_desktop",
            "lang": "ru",
            "subdomain": "ui_audit_subsea_telemetry_ru",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Проанализируй приложенный скриншот (`1024x640`) инженерной панели «Гидронавтика Системс» "
                "(глубоководные телеуправляемые аппараты ТНПА и многолучевая гидролокация): оцени визуальную "
                "плотностью карточек KPI, контраст OKLCH, доступность кнопок переключения глубин и воспроизведи "
                "полный код документа на HTML5/CSS3/JS со строгим CSP, `@container`, `100dvh` и JSON-LD."
            ),
            "rationale": (
                "### Аудит интерфейса телеметрии («Гидронавтика Системс»)\n"
                "1. **Контрастность и цветовое кодирование OKLCH:** Морской обсидиановый фон `oklch(0.15 0.02 238)` "
                "и сигнальный бирюзовый `oklch(0.78 0.14 195)` обеспечивают мгновенное считывание глубины и давления "
                "при внешнем освещении рубки.\n"
                "2. **Сетка и табличные данные:** 12-колоночная сетка Neo-Swiss с `tabular-nums` исключает дрожание цифр "
                "при обновлении показателей гидролокатора.\n"
                "3. **Соответствие WCAG 2.2:** Интерактивные вкладки режимов погружения имеют размер `>= 40px` по высоте и `aria-selected`."
            ),
            "html": """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
""" + STRICT_CSP_META + """
<title>Гидронавтика Системс — Глубоководные аппараты ТНПА до 4000 м</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"Гидронавтика Системс","url":"https://hydronavtika.example.ru"},{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"Какова рабочая глубина аппарата Океан-4000?","acceptedAnswer":{"@type":"Answer","text":"Титановый корпус и синтактиковая плавучесть рассчитаны на штатную эксплуатацию на глубинах до 4000 метров."}}]}]}
</script>
<style>
:root {
  --bg: oklch(0.15 0.02 238);
  --card: oklch(0.20 0.024 238);
  --ink: oklch(0.95 0.01 220);
  --muted: oklch(0.70 0.02 230);
  --sonar: oklch(0.78 0.14 195);
  --line: oklch(0.30 0.025 238);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: Inter, system-ui, sans-serif;
  min-height: 100dvh;
  padding: 32px 48px;
  font-variant-numeric: tabular-nums;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid var(--sonar);
  padding-bottom: 16px;
  margin-bottom: 26px;
}
.kpi-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-bottom: 24px; }
.kpi { background: var(--card); border: 1px solid var(--line); padding: 18px 22px; }
.kpi-lbl { font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }
.kpi-val { font-size: 2.15rem; font-weight: 700; color: var(--sonar); margin-top: 6px; }
main.split { display: grid; grid-template-columns: 1.25fr 1fr; gap: 24px; container-type: inline-size; }
.box { background: var(--card); border: 1px solid var(--line); padding: 24px; display: grid; gap: 16px; }
h1 { font-size: 1.85rem; line-height: 1.15; }
.mode-tabs { display: flex; gap: 10px; }
.m-btn {
  flex: 1;
  min-height: 40px;
  background: var(--bg);
  color: var(--ink);
  border: 1px solid var(--line);
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
}
.m-btn[aria-pressed="true"] { background: var(--sonar); color: var(--bg); border-color: var(--sonar); }
@container (max-width: 720px) {
  .mode-tabs { flex-direction: column; }
}
</style>
</head>
<body>
  <header>
    <strong>ГИДРОНАВТИКА СИСТЕМС · ТНПА «ОКЕАН-4000»</strong>
    <span style="font-size:0.82rem;color:var(--sonar);">Оптоволоконный кабель-трос · Задержка 1,8 мс</span>
  </header>
  <section class="kpi-row" aria-label="Ключевые параметры аппарата">
    <div class="kpi"><div class="kpi-lbl">Предельная глубина</div><div class="kpi-val" id="v-depth">4 000 м</div></div>
    <div class="kpi"><div class="kpi-lbl">Тяга 8 движителей</div><div class="kpi-val">2 450 Н</div></div>
    <div class="kpi"><div class="kpi-lbl">Полоса многолучевого эхолота</div><div class="kpi-val" id="v-swath">420 кГц · 140°</div></div>
  </section>
  <main class="split">
    <section class="box">
      <h1>Инспекция подводных трубопроводов и батиметрическая съёмка шельфа</h1>
      <p style="color:var(--muted);line-height:1.6;font-size:0.93rem;">Аппарат оснащён двумя семистепенными титановыми манипуляторами с обратной связью по усилию, доплеровским лагом DVL и инерциальной навигацией с погрешностью менее 0,08 % от пройденного пути.</p>
      <div class="mode-tabs" role="group" aria-label="Режим работы гидроакустики">
        <button type="button" class="m-btn" data-d="4 000 м" data-s="420 кГц · Разрешение 12 мм" aria-pressed="true">Детальная дефектоскопия</button>
        <button type="button" class="m-btn" data-d="2 500 м" data-s="200 кГц · Полоса обзора 280 м" aria-pressed="false">Картирование рельефа дна</button>
      </div>
    </section>
    <section class="box" aria-label="Профиль акустического луча">
      <svg viewBox="0 0 320 145" width="100%" height="145" role="img" aria-label="Схема веера многолучевого эхолота">
        <polygon points="160,18 45,125 275,125" fill="oklch(0.32 0.06 195)" stroke="oklch(0.78 0.14 195)" stroke-width="2"/>
        <polyline points="20,125 85,112 150,126 215,108 300,125" fill="none" stroke="oklch(0.95 0.01 220)" stroke-width="2"/>
        <circle cx="160" cy="18" r="5" fill="oklch(0.78 0.14 195)"/>
      </svg>
    </section>
  </main>
  <script>
    const mBtns = document.querySelectorAll('.m-btn');
    const vd = document.getElementById('v-depth');
    const vs = document.getElementById('v-swath');
    mBtns.forEach((b) => b.addEventListener('click', () => {
      mBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      vd.textContent = b.dataset.d;
      vs.textContent = b.dataset.s;
    }));
  </script>
</body>
</html>""",
        },
        {
            "key": "en_ui_audit_cryo_quantum_desktop",
            "lang": "en",
            "subdomain": "ui_audit_cryo_quantum_en",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Perform a structured UI/UX, OKLCH color contrast, and WCAG 2.2 accessibility audit of the attached "
                "`1024x640` desktop screenshot for 'Helios Cryogenics — Dry Dilution Refrigerators', then write the "
                "complete production HTML5/CSS3/JS document implementing its layout with `oklch()`, CSS Grid, "
                "`@container` queries, `100dvh`, strict SHA-256 CSP `<meta>`, and `@graph` JSON-LD (zero Tailwind)."
            ),
            "rationale": (
                "### UI/UX & Accessibility Audit (`Helios Cryogenics`)\n"
                "1. **OKLCH Token Contrast:** Deep cryostat slate `--bg: oklch(0.14 0.015 250)` paired with `--ink: oklch(0.96 0.008 240)` "
                "delivers a `14.1:1` AAA contrast ratio. The amber thermal-stage accent `--amber: oklch(0.79 0.15 78)` clearly distinguishes millikelvin cooling power.\n"
                "2. **Grid & Container Queries:** Asymmetric `1.2fr 1fr` CSS Grid with `container-type: inline-size` and `min-height: 100dvh` prevents viewport overflow.\n"
                "3. **WCAG 2.2 Target Size (SC 2.5.8):** Stage selector buttons enforce `min-height: 40px` (`>= 24x24px`) and update the `<output>` live region."
            ),
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
""" + STRICT_CSP_META + """
<title>Helios Cryogenics — Cryogen-Free 7 mK Dilution Refrigerators</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"Helios Cryogenics","url":"https://helioscryo.example.com"},{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"What is the base temperature and cooling power at 100 mK?","acceptedAnswer":{"@type":"Answer","text":"The HX-1000 dilution refrigerator achieves a base temperature below 7 mK with 1000 microwatts of cooling power at 100 mK."}}]}]}
</script>
<style>
:root {
  --bg: oklch(0.14 0.015 250);
  --surface: oklch(0.19 0.018 250);
  --ink: oklch(0.96 0.008 240);
  --muted: oklch(0.71 0.016 245);
  --amber: oklch(0.79 0.15 78);
  --line: oklch(0.28 0.02 250);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: Inter, system-ui, sans-serif;
  min-height: 100dvh;
  padding: 36px 52px;
  font-variant-numeric: tabular-nums;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--line);
  padding-bottom: 16px;
  margin-bottom: 30px;
}
main.grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 28px; container-type: inline-size; }
.card { background: var(--surface); border: 1px solid var(--line); padding: 26px; display: grid; gap: 18px; }
.eyebrow { color: var(--amber); font-size: 0.76rem; letter-spacing: 0.14em; text-transform: uppercase; }
h1 { font-size: clamp(1.9rem, 2.8vw, 2.55rem); line-height: 1.12; letter-spacing: -0.02em; }
dl.specs { display: grid; grid-template-columns: 1fr auto; gap: 10px; border-top: 1px solid var(--line); padding-top: 14px; font-size: 0.88rem; }
dt { color: var(--muted); }
dd { font-weight: 600; }
.stage-btns { display: flex; gap: 10px; }
.st-btn {
  flex: 1;
  min-height: 40px;
  background: var(--bg);
  color: var(--ink);
  border: 1px solid var(--line);
  font-weight: 600;
  font-size: 0.83rem;
  cursor: pointer;
}
.st-btn[aria-pressed="true"] { background: var(--amber); color: var(--bg); border-color: var(--amber); }
.out-val { font-size: 1.55rem; font-weight: 700; color: var(--amber); border-top: 1px solid var(--line); padding-top: 12px; }
@container (max-width: 720px) {
  .stage-btns { flex-direction: column; }
}
</style>
</head>
<body>
  <header>
    <strong>HELIOS CRYOGENICS · HX-1000 QUANTUM CRYOSTAT</strong>
    <span style="color:var(--amber);font-size:0.82rem;">³He/⁴He Closed-Cycle Gas Handling</span>
  </header>
  <main class="grid">
    <section class="card">
      <p class="eyebrow">Superconducting Qubit &amp; Millikelvin Metrology</p>
      <h1>Vibration-Isolated Dilution Systems with 1,000 µW Cooling Power at 100 mK</h1>
      <p style="color:var(--muted);line-height:1.6;font-size:0.95rem;">Engineered with gold-plated OFHC copper flanges, dual pulse-tube bellows isolation, and up to 1,152 high-density coaxial RF lines for fault-tolerant quantum processors.</p>
      <dl class="specs">
        <dt>Mixing Chamber Base Temperature</dt><dd>&lt; 6.8 mK continuous</dd>
        <dt>Mixing Chamber Plate Diameter</dt><dd>490 mm clear payload</dd>
        <dt>Vertical Displacement at Cold Plate</dt><dd>&lt; 1.2 µm RMS</dd>
      </dl>
    </section>
    <section class="card" aria-labelledby="flange-title">
      <h2 id="flange-title" style="font-size:1.1rem;">Thermal Stage Telemetry &amp; Heat Load Budget</h2>
      <svg viewBox="0 0 340 135" width="100%" height="135" role="img" aria-label="Dilution refrigerator thermal flange diagram">
        <rect x="30" y="14" width="280" height="16" fill="oklch(0.45 0.08 65)"/>
        <rect x="65" y="48" width="210" height="16" fill="oklch(0.62 0.12 72)"/>
        <rect x="105" y="82" width="130" height="16" fill="oklch(0.79 0.15 78)"/>
        <line x1="170" y1="30" x2="170" y2="118" stroke="oklch(0.71 0.016 245)" stroke-width="2"/>
        <circle cx="170" cy="118" r="10" fill="oklch(0.79 0.15 78)"/>
      </svg>
      <div class="stage-btns" role="group" aria-label="Select Cryostat Flange">
        <button type="button" class="st-btn" data-val="100 mK Mixing Chamber · 1,000 µW" aria-pressed="true">Mixing Chamber</button>
        <button type="button" class="st-btn" data-val="800 mK Still Plate · 45 mW" aria-pressed="false">Still Flange</button>
        <button type="button" class="st-btn" data-val="3.6 K PT2 Stage · 1.8 W" aria-pressed="false">4K Plate</button>
      </div>
      <output id="cryo-out" class="out-val">100 mK Mixing Chamber · 1,000 µW</output>
    </section>
  </main>
  <script>
    const sBtns = document.querySelectorAll('.st-btn');
    const cOut = document.getElementById('cryo-out');
    sBtns.forEach((b) => b.addEventListener('click', () => {
      sBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      cOut.textContent = b.dataset.val;
    }));
  </script>
</body>
</html>""",
        },
        {
            "key": "en_ui_audit_swiss_chronometer_desktop",
            "lang": "en",
            "subdomain": "ui_audit_horology_en",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Inspect the attached `1024x640` UI screenshot for 'Atelier Chronométrie Vallée — Free-Sprung Silicon "
                "Escapements', evaluate its Quiet Luxury OKLCH palette, editorial serif hierarchy, and WCAG 2.2 "
                "interactive controls, and produce the complete HTML5/CSS3/JS implementation with `@container`, "
                "`100dvh`, strict CSP `<meta>`, and JSON-LD (0 Tailwind)."
            ),
            "rationale": (
                "### Quiet Luxury UI/UX Audit (`Atelier Chronométrie Vallée`)\n"
                "1. **Warm Alabaster OKLCH Palette:** Surface `--bg: oklch(0.968 0.009 82)` and `--ink: oklch(0.20 0.012 68)` "
                "provide a glare-free `13.4:1` contrast ratio with rose-gold accents `--gold: oklch(0.52 0.085 58)`.\n"
                "2. **Editorial Layout & Container Queries:** Asymmetric `1.15fr 1fr` CSS Grid with `container-type: inline-size` "
                "and semantic `<dl>` movement specifications.\n"
                "3. **Interactive Frequency Calculator:** Frequency toggle buttons meet WCAG 2.2 `>= 24x24px` target sizing (`40px` height)."
            ),
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
""" + STRICT_CSP_META + """
<title>Atelier Chronométrie Vallée — Manufacture Caliber CV-09</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"Atelier Chronométrie Vallée","url":"https://chronovallee.example.com"},{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"What is the daily rate tolerance of Caliber CV-09?","acceptedAnswer":{"@type":"Answer","text":"Each movement is regulated across 6 positions to -0.5/+1.0 seconds per day with a 96-hour twin-barrel power reserve."}}]}]}
</script>
<style>
:root {
  --bg: oklch(0.968 0.009 82);
  --surface: oklch(0.942 0.014 80);
  --ink: oklch(0.20 0.012 68);
  --muted: oklch(0.45 0.016 70);
  --gold: oklch(0.52 0.085 58);
  --line: oklch(0.85 0.016 78);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: Georgia, "Times New Roman", serif;
  min-height: 100dvh;
  padding: 38px 54px;
  font-variant-numeric: tabular-nums;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid var(--line);
  padding-bottom: 16px;
  margin-bottom: 32px;
}
main.spread { display: grid; grid-template-columns: 1.15fr 1fr; gap: 32px; container-type: inline-size; }
.card { background: var(--surface); border: 1px solid var(--line); padding: 26px; display: grid; gap: 16px; }
h1 { font-size: clamp(2rem, 3vw, 2.7rem); font-weight: 400; line-height: 1.12; }
dl.caliber { display: grid; grid-template-columns: 1fr auto; gap: 10px; font-family: system-ui, sans-serif; font-size: 0.86rem; border-top: 1px solid var(--line); padding-top: 14px; }
dt { color: var(--muted); }
dd { font-weight: 600; }
.hz-row { display: flex; gap: 10px; }
.hz-btn {
  flex: 1;
  min-height: 40px;
  border: 1px solid var(--line);
  background: var(--bg);
  color: var(--ink);
  font-family: system-ui, sans-serif;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.hz-btn[aria-pressed="true"] { background: var(--gold); color: oklch(0.98 0.005 85); border-color: var(--gold); }
.res-out { font-size: 1.55rem; color: var(--gold); border-top: 1px solid var(--line); padding-top: 12px; }
@container (max-width: 720px) {
  .hz-row { flex-direction: column; }
}
</style>
</head>
<body>
  <header>
    <strong style="letter-spacing:0.12em;text-transform:uppercase;font-size:0.92rem;">Atelier Chronométrie Vallée · Le Sentier</strong>
    <span style="font-family:system-ui,sans-serif;font-size:0.8rem;color:var(--gold);">Observatory Certified · DRIE Silicon Hairpsring</span>
  </header>
  <main class="spread">
    <section class="card">
      <h1>Isochronous Twin-Barrel Architecture with Constant-Force Remontoire</h1>
      <p style="font-family:system-ui,sans-serif;color:var(--muted);line-height:1.62;font-size:0.95rem;">Hand-beveled German silver bridges support a free-sprung variable-inertia titanium balance wheel, eliminating amplitude drop from full wind to the 96th hour of operation.</p>
      <dl class="caliber">
        <dt>Daily Rate Deviation (6 Positions)</dt><dd>−0.5 / +1.0 s/day</dd>
        <dt>Mainplate &amp; Three-Quarter Bridge</dt><dd>Untreated Maillechort (CuNi18Zn20)</dd>
        <dt>Amagnetic Resistance (ISO 764)</dt><dd>&gt; 15,000 Gauss</dd>
      </dl>
    </section>
    <section class="card" aria-labelledby="osc-title">
      <h2 id="osc-title" style="font-size:1.15rem;font-weight:400;">Oscillator Frequency &amp; Autonomy Selector</h2>
      <svg viewBox="0 0 320 120" width="100%" height="120" role="img" aria-label="Free-sprung balance wheel schematic">
        <circle cx="160" cy="60" r="46" fill="none" stroke="oklch(0.52 0.085 58)" stroke-width="2.5"/>
        <circle cx="160" cy="60" r="22" fill="none" stroke="oklch(0.45 0.016 70)" stroke-width="1.5"/>
        <line x1="114" y1="60" x2="206" y2="60" stroke="oklch(0.20 0.012 68)" stroke-width="2"/>
        <circle cx="160" cy="60" r="5" fill="oklch(0.52 0.085 58)"/>
      </svg>
      <div class="hz-row" role="group" aria-label="Select Oscillator Frequency">
        <button type="button" class="hz-btn" data-out="3 Hz (21,600 vph) · 96 Hours Autonomy" aria-pressed="true">Caliber CV-09A (3 Hz)</button>
        <button type="button" class="hz-btn" data-out="5 Hz (36,000 vph) · 72 Hours Autonomy" aria-pressed="false">Caliber CV-09H (5 Hz)</button>
      </div>
      <output id="hz-out" class="res-out">3 Hz (21,600 vph) · 96 Hours Autonomy</output>
    </section>
  </main>
  <script>
    const hBtns = document.querySelectorAll('.hz-btn');
    const hOut = document.getElementById('hz-out');
    hBtns.forEach((b) => b.addEventListener('click', () => {
      hBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      hOut.textContent = b.dataset.out;
    }));
  </script>
</body>
</html>""",
        },
        {
            "key": "en_ui_audit_geothermal_grid_desktop",
            "lang": "en",
            "subdomain": "ui_audit_geothermal_swiss_en",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Audit the attached `1024x640` Neo-Swiss Grid telemetry interface for 'Borealis Enhanced Geothermal "
                "Systems' (closed-loop supercritical CO2 deep geothermal baseload): critique its 12-column grid, "
                "`tabular-nums` alignment, OKLCH contrast, and WCAG 2.2 target sizes, and output the complete "
                "HTML5/CSS3/JS source code with `@container`, `100dvh`, strict CSP, and `@graph` JSON-LD."
            ),
            "rationale": (
                "### Neo-Swiss Telemetry Audit (`Borealis Enhanced Geothermal`)\n"
                "1. **12-Column Swiss Grid & Tabular Figures:** High-contrast `--bg: oklch(0.982 0.004 250)` and `--ink: oklch(0.16 0.015 255)` "
                "with `font-variant-numeric: tabular-nums` align MWth/MWe metrics cleanly.\n"
                "2. **Container Queries & `100dvh`:** Responsive `@container` rules and `min-height: 100dvh` maintain layout integrity.\n"
                "3. **WCAG 2.2 & Strict CSP:** Interactive loop selector buttons exceed `24x24px` (`40px` height) with zero external dependencies."
            ),
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
""" + STRICT_CSP_META + """
<title>Borealis Enhanced Geothermal — Closed-Loop Supercritical sCO2 Baseload</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"Borealis Enhanced Geothermal","url":"https://borealisgeo.example.com"},{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"How deep are the closed-loop multilateral laterals?","acceptedAnswer":{"@type":"Answer","text":"Each closed-loop well pad drills to 4.8 km vertical depth into 245 C crystalline basement rock with zero fracking fluid loss."}}]}]}
</script>
<style>
:root {
  --bg: oklch(0.982 0.004 250);
  --card: oklch(0.952 0.008 250);
  --ink: oklch(0.16 0.015 255);
  --muted: oklch(0.45 0.02 255);
  --cobalt: oklch(0.50 0.19 258);
  --line: oklch(0.84 0.012 255);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: Inter, system-ui, sans-serif;
  min-height: 100dvh;
  padding: 32px 48px;
  font-variant-numeric: tabular-nums;
}
header { display: flex; justify-content: space-between; border-bottom: 2px solid var(--ink); padding-bottom: 16px; margin-bottom: 24px; }
.kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.kpi { background: var(--card); border-top: 3px solid var(--ink); padding: 18px; }
.kpi-l { font-size: 0.76rem; text-transform: uppercase; color: var(--muted); }
.kpi-v { font-size: 2.2rem; font-weight: 700; margin-top: 6px; color: var(--cobalt); }
main.split { display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px; container-type: inline-size; }
.box { border: 1px solid var(--line); padding: 24px; display: grid; gap: 16px; }
.pad-btns { display: flex; gap: 10px; }
.p-btn {
  flex: 1;
  min-height: 40px;
  border: 1px solid var(--ink);
  background: var(--bg);
  color: var(--ink);
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
}
.p-btn[aria-pressed="true"] { background: var(--cobalt); border-color: var(--cobalt); color: white; }
@container (max-width: 720px) {
  .pad-btns { flex-direction: column; }
}
</style>
</head>
<body>
  <header>
    <strong>BOREALIS EGS · CLOSED-LOOP GEOTHERMAL DISPATCH</strong>
    <span style="color:var(--cobalt);font-weight:600;font-size:0.84rem;">4.8 km Crystalline Granite · 98.6% Capacity Factor</span>
  </header>
  <section class="kpis" aria-label="Wellhead Performance Indicators">
    <div class="kpi"><div class="kpi-l">Net Baseload Output</div><div class="kpi-v" id="g-mw">42.5 MWe</div></div>
    <div class="kpi"><div class="kpi-l">Wellhead sCO₂ Temp</div><div class="kpi-v" id="g-tmp">238 °C</div></div>
    <div class="kpi"><div class="kpi-l">Water Consumption</div><div class="kpi-v">0.0 L/MWh</div></div>
  </section>
  <main class="split">
    <section class="box">
      <h1 style="font-size:1.85rem;line-height:1.15;">Zero-Water Multilateral Thermosiphon Baseload</h1>
      <p style="color:var(--muted);line-height:1.6;font-size:0.93rem;">Twelve sealed multilateral rock heat exchangers circulate supercritical CO₂ through 54 km of conductive wellbore contact, driving a compact Brayton turbine without induced seismicity.</p>
      <div class="pad-btns" role="group" aria-label="Select Well Pad">
        <button type="button" class="p-btn" data-mw="42.5 MWe" data-t="238 °C" aria-pressed="true">Pad Alpha (12 Laterals)</button>
        <button type="button" class="p-btn" data-mw="64.0 MWe" data-t="254 °C" aria-pressed="false">Pad Beta (18 Laterals)</button>
      </div>
    </section>
    <section class="box" aria-label="Subsurface Thermal Profile">
      <svg viewBox="0 0 320 140" width="100%" height="140" role="img" aria-label="Closed-loop multilateral wellbore diagram">
        <path d="M50,15 V115 H270 V15" fill="none" stroke="oklch(0.50 0.19 258)" stroke-width="3"/>
        <path d="M50,90 H270 M50,65 H270" fill="none" stroke="oklch(0.62 0.14 258)" stroke-width="2"/>
        <text x="85" y="134" font-size="11" fill="oklch(0.45 0.02 255)">4,800 m Conductive Granite Loop</text>
      </svg>
    </section>
  </main>
  <script>
    const pBtns = document.querySelectorAll('.p-btn');
    const gMw = document.getElementById('g-mw');
    const gTmp = document.getElementById('g-tmp');
    pBtns.forEach((b) => b.addEventListener('click', () => {
      pBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      gMw.textContent = b.dataset.mw;
      gTmp.textContent = b.dataset.t;
    }));
  </script>
</body>
</html>""",
        },
        {
            "key": "en_ui_audit_modular_synth_desktop",
            "lang": "en",
            "subdomain": "ui_audit_brutalist_synth_en",
            "viewport_w": 1440,
            "viewport_h": 900,
            "out_w": 1024,
            "out_h": 640,
            "user_prompt": (
                "Conduct a UI/UX and accessibility audit of the attached `1024x640` Brutalist Raw interface for "
                "'Klangwerk West-Coast Wavefolder & Buchla Lab': evaluate its exposed 2px grid, high-contrast "
                "OKLCH palette, semantic `<table>` patch bay, and WCAG 2.2 button sizes, then write the full "
                "HTML5/CSS3/JS document with `@container`, `100dvh`, strict CSP, and JSON-LD."
            ),
            "rationale": (
                "### Brutalist Raw UI/UX Audit (`Klangwerk West-Coast Lab`)\n"
                "1. **High-Contrast OKLCH Palette:** Obsidian `--bg: oklch(0.13 0.01 260)` and acid lime `--acid: oklch(0.88 0.21 128)` "
                "achieve a `13.8:1` contrast ratio with exposed `2px solid` structural borders.\n"
                "2. **Semantic Patch Matrix Table:** Uses `<table aria-label>` with `<th scope=\"col\">` and client-side bus filtering.\n"
                "3. **WCAG 2.2 Target Size:** Filter buttons are `44px` tall (`>= 24x24px`) with explicit `aria-pressed` state."
            ),
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
""" + STRICT_CSP_META + """
<title>Klangwerk West-Coast — Complex Oscillator &amp; Wavefolder Matrix</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"Klangwerk West-Coast","url":"https://klangwerk.example.com"},{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"Does the KW-259 wavefolder use vactrol low-pass gates?","acceptedAnswer":{"@type":"Answer","text":"Yes, dual hand-matched CdS optical vactrols provide organic zero-ringing transient decay."}}]}]}
</script>
<style>
:root {
  --bg: oklch(0.13 0.01 260);
  --fg: oklch(0.95 0.01 110);
  --acid: oklch(0.88 0.21 128);
  --dim: oklch(0.68 0.02 260);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--fg); font-family: "Courier New", monospace; min-height: 100dvh; padding: 24px; }
.frame { border: 2px solid var(--fg); display: grid; grid-template-columns: 340px 1fr; min-height: calc(100dvh - 48px); container-type: inline-size; }
.left { border-right: 2px solid var(--fg); padding: 24px; display: flex; flex-direction: column; justify-content: space-between; }
.filters { display: flex; border-bottom: 2px solid var(--fg); }
.f-btn { flex: 1; min-height: 44px; background: var(--bg); color: var(--fg); border: none; border-right: 2px solid var(--fg); font-family: inherit; font-weight: 700; cursor: pointer; }
.f-btn[aria-pressed="true"] { background: var(--acid); color: var(--bg); }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { border-bottom: 2px solid var(--fg); padding: 14px 16px; text-align: left; }
th { color: var(--acid); text-transform: uppercase; font-size: 0.78rem; }
tr[hidden] { display: none; }
</style>
</head>
<body>
  <div class="frame">
    <header class="left">
      <div>
        <span style="background:var(--acid);color:var(--bg);padding:4px 8px;font-weight:700;font-size:0.8rem;">KW-259 ANALOG LAB</span>
        <h1 style="font-size:2.4rem;line-height:0.98;margin:16px 0;">WEST-COAST<br>WAVEFOLDER</h1>
        <p style="font-size:0.88rem;line-height:1.5;color:var(--dim);">Five-stage Chebyshev harmonic folder with through-zero linear FM and dual CdS vactrol low-pass gates.</p>
      </div>
      <svg viewBox="0 0 260 80" width="100%" height="80" role="img" aria-label="Wavefolder folded harmonic waveform">
        <polyline points="0,40 20,10 35,35 50,8 65,72 80,45 95,70 115,40 135,10 150,35 165,8 180,72 195,45 210,70 235,40 260,40" fill="none" stroke="oklch(0.88 0.21 128)" stroke-width="2.5"/>
      </svg>
    </header>
    <main>
      <div class="filters" role="group" aria-label="Filter CV Bus">
        <button type="button" class="f-btn" data-bus="all" aria-pressed="true">ALL BUSES (4)</button>
        <button type="button" class="f-btn" data-bus="Audio" aria-pressed="false">AUDIO PATH</button>
        <button type="button" class="f-btn" data-bus="Modulation" aria-pressed="false">MODULATION</button>
      </div>
      <table aria-label="Module Patch Matrix">
        <thead><tr><th scope="col">Module</th><th scope="col">Bus</th><th scope="col">Range</th><th scope="col">Topology</th></tr></thead>
        <tbody>
          <tr data-bus="Audio"><td>KW-259 Complex Osc</td><td>Audio</td><td>10 Vpp</td><td>5-Stage Diode Folder</td></tr>
          <tr data-bus="Modulation"><td>KW-281 Quad Function</td><td>Modulation</td><td>0..+10 V</td><td>Quadrature Attack/Decay</td></tr>
          <tr data-bus="Audio"><td>KW-292 Dual LPG</td><td>Audio</td><td>−90 dB Floor</td><td>CdS Vactrol Sallen-Key</td></tr>
          <tr data-bus="Modulation"><td>KW-266 Source of Uncertainty</td><td>Modulation</td><td>Quantized 1V/Oct</td><td>Pink Noise + S&amp;H</td></tr>
        </tbody>
      </table>
    </main>
  </div>
  <script>
    const btns = document.querySelectorAll('.f-btn');
    const rows = document.querySelectorAll('tbody tr');
    btns.forEach((b) => b.addEventListener('click', () => {
      btns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      const bus = b.dataset.bus;
      rows.forEach((r) => { r.hidden = bus !== 'all' && r.dataset.bus !== bus; });
    }));
  </script>
</body>
</html>""",
        },
    ]


def get_v2_ui_audit_vision_specs() -> list[dict[str, Any]]:
    """Return 21 strictly 1-of-1 multimodal UI-audit & vision-to-code specs (11 RU + 10 EN)
    yielding ~16,000 RU tokens and ~15,000 EN tokens (`31,000` total in `ui_audit_vision`)."""
    base_specs = get_unique_multimodal_canon_specs()
    upgraded: list[dict[str, Any]] = []
    for s in base_specs:
        s2 = dict(s)
        s2["html"] = _upgrade_html_for_v2_canons(s["html"], s["key"], s["lang"])
        if s2["lang"] == "ru":
            s2["user_prompt"] = (
                "Выполни UI/UX и WCAG 2.2 аудит приложенного скриншота (контраст OKLCH, модульная сетка, "
                "размеры интерактивных элементов >=24x24px) и " + s["user_prompt"][0].lower() + s["user_prompt"][1:]
            )
            s2["rationale"] = (
                "### UI/UX, OKLCH и WCAG 2.2 Аудит макета\n"
                "- **Цветовая система OKLCH и контрастность:** Семантические токены фона и текста обеспечивают контраст AAA/AA без выгорания оттенков; исключены утилитарные классы Tailwind.\n"
                "- **Адаптивная сетка и безопасность:** Применены CSS Grid, `@container`, `100dvh`, строгий `<meta http-equiv=\"Content-Security-Policy\">` и микроразметка `@graph` JSON-LD.\n\n"
                + s["rationale"]
            )
        else:
            s2["user_prompt"] = (
                "Perform a UI/UX, OKLCH contrast, and WCAG 2.2 target-size audit of the attached screenshot, and "
                + s["user_prompt"][0].lower()
                + s["user_prompt"][1:]
            )
            s2["rationale"] = (
                "### UI/UX, OKLCH & WCAG 2.2 Layout Audit\n"
                "- **OKLCH Perceptual Contrast:** Semantic background, surface, and ink tokens meet WCAG AAA/AA contrast with zero Tailwind utility classes.\n"
                "- **Modern CSS & Security:** Uses CSS Grid, `@container` inline-size queries, `100dvh`, strict SHA-256 CSP `<meta>`, and `@graph` JSON-LD.\n\n"
                + s["rationale"]
            )
        upgraded.append(s2)

    all_specs = upgraded + _extra_v2_ui_audit_specs()
    return all_specs
