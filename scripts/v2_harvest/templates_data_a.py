"""Golden production starter templates 01 (RU Swiss B2B) and 02 (EN Dark SaaS)."""

SHARED_ROBOTS_TXT_TEMPLATE = """# AI Corpus Training Crawlers (Opt-out of weight training)
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: CCBot
Disallow: /

# Live Search & AI Citation Retrieval Crawlers (Explicitly permitted)
User-agent: OAI-SearchBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Googlebot
Allow: /

User-agent: *
Allow: /
Sitemap: {base_url}/sitemap.xml
"""

TEMPLATE_01_RU_SWISS = {
    "slug": "01_swiss_b2b_industrial_ru",
    "canon_id": "01_swiss_international_typographic",
    "lang": "ru",
    "base_url": "https://kvartz-kontur.example.ru",
    "title": "Кварц-Контур: промышленная телеметрия NVMe и узлов хранения",
    "description": "Автономный сбор телеметрии SMART и очередей с 10 000 NVMe-дисков каждые 100 мс без ядерных модулей и внешних облаков.",
    "og_locale": "ru_RU",
    "hreflangs": {
        "ru": "https://kvartz-kontur.example.ru/",
        "en": "https://kvartz-kontur.example.ru/en/",
        "x-default": "https://kvartz-kontur.example.ru/",
    },
    "css": """:root {
  --bg: oklch(0.98 0.002 90);
  --surface: oklch(0.945 0.003 90);
  --border: oklch(0.20 0.002 90);
  --text: oklch(0.14 0.002 90);
  --text-muted: oklch(0.42 0.005 90);
  --accent: oklch(0.54 0.21 28);
  --accent-ink: oklch(0.99 0.002 90);
  --font-sans: 'Inter', 'Helvetica Neue', Arial, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-padding-top: 4.75rem; font-size: 16px; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  line-height: 1.5;
  overflow-x: hidden;
}
.skip-link {
  position: absolute;
  left: -9999px;
  top: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--accent);
  color: var(--accent-ink);
  min-height: 24px;
  min-width: 24px;
}
.skip-link:focus { left: 0.75rem; z-index: 100; }
.site-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}
.header-inner, .container {
  max-width: 82rem;
  margin: 0 auto;
  padding-inline: clamp(1.25rem, 4vw, 3.5rem);
}
.header-inner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  min-height: 4.25rem;
  gap: 1rem;
}
.brand-mark {
  font-weight: 700;
  letter-spacing: -0.02em;
  text-decoration: none;
  color: var(--text);
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 28px;
}
.nav-list {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.nav-list a {
  color: var(--text);
  text-decoration: none;
  font-size: 0.9375rem;
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  min-width: 28px;
  padding: 0.25rem 0.35rem;
}
.nav-list a:hover, .nav-list a:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.hero-shell {
  min-height: 100svh;
  display: grid;
  align-items: center;
  padding-block: clamp(2rem, 5vw, 5.5rem);
  border-bottom: 1px solid var(--border);
}
.swiss-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 1.5rem;
}
.hero-lead { grid-column: span 7; }
.hero-diagram {
  grid-column: span 5;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 1.5rem;
}
.index-tag {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  display: block;
  margin-bottom: 0.75rem;
}
h1 {
  font-size: clamp(2rem, 3.8vw, 3.25rem);
  line-height: 1.08;
  letter-spacing: -0.03em;
  margin: 0 0 1.25rem;
  max-width: 18ch;
}
.lead-copy {
  font-size: 1.0625rem;
  max-width: 62ch;
  color: var(--text);
  margin: 0 0 1.75rem;
}
.cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
}
.btn-primary, .btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  min-width: 44px;
  padding: 0.65rem 1.25rem;
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: opacity 140ms cubic-bezier(0.2, 0, 0, 1);
}
.btn-primary {
  background: var(--accent);
  color: var(--accent-ink);
  border-color: var(--accent);
}
.btn-secondary {
  background: var(--surface);
  color: var(--text);
}
.btn-primary:focus-visible, .btn-secondary:focus-visible, input:focus-visible, select:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.section-block {
  padding-block: clamp(2.5rem, 5vw, 5rem);
  border-bottom: 1px solid var(--border);
}
h2 {
  font-size: clamp(1.5rem, 2.5vw, 2.125rem);
  line-height: 1.12;
  margin: 0 0 1.5rem;
}
.passport-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
}
.passport-card {
  display: grid;
  grid-template-rows: subgrid;
  grid-row: span 3;
  border: 1px solid var(--border);
  background: var(--surface);
  padding: 1.5rem;
  gap: 0.75rem;
}
.passport-card h3 { margin: 0; font-size: 1.125rem; }
.passport-card p { margin: 0; color: var(--text-muted); max-width: 58ch; }
.metric-num, table td, output {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.calc-wrapper {
  container-type: inline-size;
  border: 1px solid var(--border);
  background: var(--surface);
  padding: 1.5rem;
}
.calc-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  align-items: start;
}
@container (max-width: 640px) {
  .calc-grid { grid-template-columns: 1fr; }
}
.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 1rem;
}
.field-group label { font-weight: 600; font-size: 0.9375rem; }
.field-group input, .field-group select {
  min-height: 40px;
  min-width: 40px;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 0.9375rem;
}
.spec-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}
.spec-table th, .spec-table td {
  text-align: left;
  padding: 0.65rem 0.5rem;
  border-bottom: 1px solid var(--border);
}
.faq-list { display: grid; gap: 1.25rem; max-width: 65ch; }
.faq-item {
  border-top: 1px solid var(--border);
  padding-top: 1rem;
}
.faq-item h3 { margin: 0 0 0.5rem; font-size: 1.0625rem; }
.faq-item p { margin: 0; color: var(--text); }
.hp-trap { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
.site-footer {
  padding-block: 2rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}
@media (max-width: 900px) {
  .hero-lead, .hero-diagram { grid-column: span 12; }
  .passport-grid { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
""",
    "json_ld": {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": "https://kvartz-kontur.example.ru/#org",
                "name": "Кварц-Контур Инжиниринг",
                "url": "https://kvartz-kontur.example.ru/",
            },
            {
                "@type": "WebSite",
                "@id": "https://kvartz-kontur.example.ru/#website",
                "url": "https://kvartz-kontur.example.ru/",
                "name": "Кварц-Контур",
                "inLanguage": "ru",
                "publisher": {"@id": "https://kvartz-kontur.example.ru/#org"},
            },
            {
                "@type": "WebPage",
                "@id": "https://kvartz-kontur.example.ru/#webpage",
                "url": "https://kvartz-kontur.example.ru/",
                "name": "Кварц-Контур: промышленная телеметрия NVMe и узлов хранения",
                "isPartOf": {"@id": "https://kvartz-kontur.example.ru/#website"},
            },
            {
                "@type": "Product",
                "@id": "https://kvartz-kontur.example.ru/#product",
                "name": "Агент телеметрии Кварц-Контур v4.2",
                "brand": {"@id": "https://kvartz-kontur.example.ru/#org"},
                "description": "Статический ELF-агент сбора метрик SMART и очередей NVMe-накопителей без ядерных модулей.",
                "offers": {
                    "@type": "Offer",
                    "price": "4800",
                    "priceCurrency": "RUB",
                    "availability": "https://schema.org/InStock",
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": "https://kvartz-kontur.example.ru/#breadcrumbs",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Главная", "item": "https://kvartz-kontur.example.ru/"},
                    {"@type": "ListItem", "position": 2, "name": "Телеметрия NVMe", "item": "https://kvartz-kontur.example.ru/#specs"},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": "https://kvartz-kontur.example.ru/#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "Работает ли агент Кварц-Контур в полностью изолированном контуре без интернета?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Да, агент «Кварц-Контур» работает полностью автономно в изолированных сетях без внешних соединений. Сборщик поставляется единым статическим ELF-файлом весом 14 МБ с офлайн-подписью Ed25519.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Требуется ли установка сторонних ядерных модулей или перезагрузка хранилища?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Нет, опрос очередей и регистров износа выполняется через штатные административные команды io_uring и интерфейс nvme-ioctl ядра Linux 5.15 LTS и новее без перезагрузки узла.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Какова нагрузка на процессор при опросе каждые 100 миллисекунд?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "На полке из 24 накопителей U.3 NVMe при интервале съёма 100 мс агент потребляет менее 0,4% одного физического ядра Xeon и до 18 МБ оперативной памяти.",
                        },
                    },
                ],
            },
        ],
    },
    "body_html": """<a class="skip-link" href="#main-content">Перейти к основному содержимому</a>
<header class="site-header">
  <div class="header-inner">
    <a class="brand-mark" href="#main-content">
      <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="2" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"/><rect x="7" y="7" width="10" height="10" fill="currentColor"/></svg>
      <span>КВАРЦ-КОНТУР</span>
    </a>
    <nav aria-label="Основная навигация">
      <ul class="nav-list">
        <li><a href="#specs">Паспорта узлов</a></li>
        <li><a href="#calculator">Расчёт потока</a></li>
        <li><a href="#faq">Частые вопросы</a></li>
        <li><a href="#intake">Запрос стенда</a></li>
      </ul>
    </nav>
  </div>
</header>

<main id="main-content">
  <section class="hero-shell">
    <div class="container swiss-grid">
      <div class="hero-lead">
        <span class="index-tag">Индекс 01 / Промышленная эксплуатация СХД</span>
        <h1>Снимайте телеметрию SMART и очередей с 10 000 NVMe-дисков каждые 100 мс</h1>
        <p class="lead-copy">Статический агент на Linux опрашивает температуру кристалла, счётчики коррекции ошибок и хвосты задержек записи без установки ядерных модулей и передачи пакетов за периметр ЦОД.</p>
        <div class="cta-row">
          <a class="btn-primary" href="#calculator">Рассчитать битрейт и объём архива</a>
          <a class="btn-secondary" href="#intake">Скачать эталонный стенд (ELF, 14 МБ)</a>
        </div>
      </div>
      <div class="hero-diagram" aria-label="Схема задержек чтения NVMe">
        <span class="index-tag">Профиль p99 задержки по 24 дискам</span>
        <svg width="420" height="210" viewBox="0 0 420 210" role="img" aria-labelledby="nvmeChartTitle">
          <title id="nvmeChartTitle">Гистограмма задержки чтения и записи NVMe в микросекундах</title>
          <line x1="36" y1="20" x2="36" y2="176" stroke="currentColor" stroke-width="1.5"/>
          <line x1="36" y1="176" x2="400" y2="176" stroke="currentColor" stroke-width="1.5"/>
          <rect x="64" y="96" width="56" height="80" fill="currentColor"/>
          <rect x="152" y="72" width="56" height="104" fill="currentColor"/>
          <rect x="240" y="114" width="56" height="62" fill="currentColor"/>
          <rect id="alertBarRect" x="328" y="44" width="56" height="132" fill="currentColor"/>
          <text x="64" y="196" font-size="12" fill="currentColor">p50: 85мкс</text>
          <text x="152" y="196" font-size="12" fill="currentColor">p95: 190мкс</text>
          <text x="240" y="196" font-size="12" fill="currentColor">Запись</text>
          <text x="328" y="196" font-size="12" fill="currentColor">Пик GC</text>
        </svg>
      </div>
    </div>
  </section>

  <section id="specs" class="section-block">
    <div class="container">
      <span class="index-tag">Индекс 02 / Архитектурные гарантии</span>
      <h2>Паспорта подсистем сбора и хранения</h2>
      <div class="passport-grid">
        <article class="passport-card">
          <span class="index-tag">Паспорт 01</span>
          <h3>Прямой опрос через nvme-ioctl</h3>
          <p>Считывание лог-страниц износа, резервных блоков и перегрева контроллера за 180 микросекунд без блокировки очередей ввода-вывода.</p>
        </article>
        <article class="passport-card">
          <span class="index-tag">Паспорт 02</span>
          <h3>Кольцевой буфер при обрыве сети</h3>
          <p>Локальный журнал объёмом до 4 ГБ сохраняет посекундные срезы на системном разделе и досылает кадры после восстановления коллектора.</p>
        </article>
        <article class="passport-card">
          <span class="index-tag">Паспорт 03</span>
          <h3>Сжатие Zstandard в ClickHouse</h3>
          <p>Дельта-кодирование счётчиков упаковывает суточный поток с тысячи накопителей в 1,4 ГБ дискового пространства с выборкой за 90 мс.</p>
        </article>
      </div>
    </div>
  </section>

  <section id="calculator" class="section-block">
    <div class="container">
      <span class="index-tag">Индекс 03 / Инженерный калькулятор ёмкости</span>
      <h2>Расчёт сетевого потока и архива на 30 суток</h2>
      <div class="calc-wrapper">
        <div class="calc-grid">
          <div>
            <div class="field-group">
              <label for="driveCountInput">Число накопителей NVMe в контуре (шт.)</label>
              <input id="driveCountInput" name="drive_count" type="number" min="24" max="50000" step="24" value="1200" autocomplete="off"/>
            </div>
            <div class="field-group">
              <label for="pollIntervalSelect">Интервал опроса телеметрии (мс)</label>
              <select id="pollIntervalSelect" name="poll_interval">
                <option value="100" selected>100 мс (режим раннего перехвата GC)</option>
                <option value="500">500 мс (штатный промышленный профиль)</option>
                <option value="1000">1000 мс (долгосрочный аудит ресурса)</option>
              </select>
            </div>
          </div>
          <div>
            <table class="spec-table" aria-label="Результаты расчёта нагрузки">
              <tbody>
                <tr>
                  <th scope="row">Сетевой поток от агентов</th>
                  <td><output id="netMbpsOut" for="driveCountInput pollIntervalSelect">19.2 Мбит/с</output></td>
                </tr>
                <tr>
                  <th scope="row">Архив ClickHouse за 30 суток</th>
                  <td><output id="storageGbOut" for="driveCountInput pollIntervalSelect">51.8 ГБ</output></td>
                </tr>
                <tr>
                  <th scope="row">Лицензия узлов хранения (4800 ₽/полка)</th>
                  <td><output id="costRubOut" for="driveCountInput pollIntervalSelect">240 000 ₽/мес</output></td>
                </tr>
              </tbody>
            </table>
            <svg width="320" height="36" viewBox="0 0 320 36" aria-label="Индикатор заполнения полосы 1 Гбит/с">
              <rect x="0" y="10" width="300" height="16" fill="none" stroke="currentColor" stroke-width="1.5"/>
              <rect id="loadFillRect" x="2" y="12" width="48" height="12" fill="currentColor"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="faq" class="section-block">
    <div class="container">
      <span class="index-tag">Индекс 04 / Ответы для службы эксплуатации и ИБ</span>
      <h2>Частые вопросы по внедрению</h2>
      <div class="faq-list">
        <article class="faq-item">
          <h3>Работает ли агент Кварц-Контур в полностью изолированном контуре без интернета?</h3>
          <p>Да, агент «Кварц-Контур» работает полностью автономно в изолированных сетях без внешних соединений. Сборщик поставляется единым статическим ELF-файлом весом 14 МБ с офлайн-подписью Ed25519.</p>
        </article>
        <article class="faq-item">
          <h3>Требуется ли установка сторонних ядерных модулей или перезагрузка хранилища?</h3>
          <p>Нет, опрос очередей и регистров износа выполняется через штатные административные команды io_uring и интерфейс nvme-ioctl ядра Linux 5.15 LTS и новее без перезагрузки узла.</p>
        </article>
        <article class="faq-item">
          <h3>Какова нагрузка на процессор при опросе каждые 100 миллисекунд?</h3>
          <p>На полке из 24 накопителей U.3 NVMe при интервале съёма 100 мс агент потребляет менее 0,4% одного физического ядра Xeon и до 18 МБ оперативной памяти.</p>
        </article>
      </div>
    </div>
  </section>

  <section id="intake" class="section-block">
    <div class="container">
      <span class="index-tag">Индекс 05 / Запрос дистрибутива</span>
      <h2>Получить подписанный архив для стендовых испытаний</h2>
      <form id="auditIntakeForm" action="#intake" method="post" novalidate>
        <div class="calc-grid">
          <div class="field-group">
            <label for="engNameInput">Имя и должность ведущего инженера</label>
            <input id="engNameInput" name="name" type="text" required autocomplete="name"/>
          </div>
          <div class="field-group">
            <label for="engEmailInput">Рабочая почта на домене организации</label>
            <input id="engEmailInput" name="email" type="email" required autocomplete="email"/>
          </div>
        </div>
        <div class="hp-trap" aria-hidden="true">
          <label for="companyFaxTrap">Оставьте это служебное поле пустым</label>
          <input id="companyFaxTrap" name="company_fax_hp" type="text" tabindex="-1" autocomplete="off"/>
        </div>
        <button class="btn-primary" type="submit">Сформировать ключ проверки Ed25519 и ссылку</button>
        <p id="formStatusMsg" role="status" aria-live="polite">Форма защищена без сторонних трекеров; ответ инженера за 4 рабочих часа.</p>
      </form>
    </div>
  </section>
</main>

<footer class="site-footer">
  <div class="container">
    <p>Кварц-Контур Инжиниринг, 2026. Нулевые внешние скрипты, проверка целостности SHA-256 CSP, лицензия шрифтов SIL OFL-1.1.</p>
  </div>
</footer>""",
    "ts_code": """interface TelemetryEstimate {
  netMbps: number;
  storageGb: number;
  shelves: number;
  monthlyRub: number;
  barWidthPx: number;
}

function registerTrustedTypesGuard(): void {
  const w = window as unknown as {
    trustedTypes?: { createPolicy: (name: string, rules: { createHTML: (s: string) => string }) => unknown };
  };
  if (w.trustedTypes && typeof w.trustedTypes.createPolicy === "function") {
    try {
      w.trustedTypes.createPolicy("default", {
        createHTML: (input: string): string => input.replace(/[<>]/g, ""),
      });
    } catch {
      // Policy already registered by host frame
    }
  }
}

function computeTelemetry(drives: number, intervalMs: number): TelemetryEstimate {
  const clampedDrives = Math.max(24, Math.min(50000, Math.round(drives)));
  const samplesPerSec = 1000 / Math.max(100, intervalMs);
  const bytesPerSample = 200;
  const netMbps = (clampedDrives * samplesPerSec * bytesPerSample * 8) / 1_000_000;
  const storageGb = (clampedDrives * samplesPerSec * 18 * 86400 * 30) / 1_000_000_000;
  const shelves = Math.ceil(clampedDrives / 24);
  const monthlyRub = shelves * 4800;
  const barWidthPx = Math.max(8, Math.min(296, Math.round((netMbps / 250) * 296)));
  return { netMbps, storageGb, shelves, monthlyRub, barWidthPx };
}

function initKvartzKontur(): void {
  registerTrustedTypesGuard();

  const driveInput = document.getElementById("driveCountInput") as HTMLInputElement | null;
  const intervalSelect = document.getElementById("pollIntervalSelect") as HTMLSelectElement | null;
  const netOut = document.getElementById("netMbpsOut") as HTMLOutputElement | null;
  const storageOut = document.getElementById("storageGbOut") as HTMLOutputElement | null;
  const costOut = document.getElementById("costRubOut") as HTMLOutputElement | null;
  const barRect = document.getElementById("loadFillRect") as SVGRectElement | null;

  const renderEstimate = (): void => {
    if (!driveInput || !intervalSelect || !netOut || !storageOut || !costOut) {
      return;
    }
    const drives = Number.parseInt(driveInput.value || "1200", 10) || 1200;
    const intervalMs = Number.parseInt(intervalSelect.value || "100", 10) || 100;
    const est = computeTelemetry(drives, intervalMs);
    netOut.textContent = `${est.netMbps.toFixed(1)} Мбит/с`;
    storageOut.textContent = `${est.storageGb.toFixed(1)} ГБ`;
    costOut.textContent = `${est.monthlyRub.toLocaleString("ru-RU")} ₽/мес`;
    if (barRect) {
      barRect.setAttribute("width", String(est.barWidthPx));
    }
  };

  if (driveInput && intervalSelect) {
    driveInput.addEventListener("input", renderEstimate);
    intervalSelect.addEventListener("change", renderEstimate);
    renderEstimate();
  }

  const form = document.getElementById("auditIntakeForm") as HTMLFormElement | null;
  const statusMsg = document.getElementById("formStatusMsg") as HTMLElement | null;
  const hpInput = document.getElementById("companyFaxTrap") as HTMLInputElement | null;
  const emailInput = document.getElementById("engEmailInput") as HTMLInputElement | null;

  if (form && statusMsg) {
    form.addEventListener("submit", (ev: Event): void => {
      ev.preventDefault();
      if (hpInput && hpInput.value.trim().length > 0) {
        statusMsg.textContent = "Запрос отклонён защитным фильтром формы.";
        return;
      }
      const emailVal = emailInput ? emailInput.value.trim() : "";
      if (!emailVal.includes("@") || !emailVal.includes(".")) {
        statusMsg.textContent = "Укажите корректный рабочий адрес электронной почты на домене организации.";
        return;
      }
      statusMsg.textContent = "Заявка принята локально: проверочный отпечаток стенда Ed25519 готов к отправке.";
    });
  }
}

initKvartzKontur();
export {};
""",
    "llms_txt": """# Кварц-Контур (Kvartz-Kontur NVMe Telemetry)

> Автономная промышленная платформа сбора метрик SMART, температуры и очередей с 10 000 NVMe-накопителей каждые 100 мс без установки ядерных модулей и внешних сетевых вызовов.

## Техническая документация
- [Паспорта подсистем](https://kvartz-kontur.example.ru/#specs): Опрос через nvme-ioctl, локальный кольцевой буфер 4 ГБ и сжатие ClickHouse Zstandard.
- [Калькулятор потока](https://kvartz-kontur.example.ru/#calculator): Детерминированный расчёт полосы пропускания и 30-дневного архива.

## Эксплуатация и безопасность
- [Вопросы ИБ и интеграции](https://kvartz-kontur.example.ru/#faq): Работа в закрытых контурах, статический ELF 14 МБ с подписью Ed25519, нагрузка ниже 0,4% ядра.
""",
    "zimage_prompts": [
        {
            "id": "kvartz_hero_bay",
            "slot": "hero_primary",
            "canon_id": "01_swiss_international_typographic",
            "aspect_ratio": "16:9",
            "exact_text_in_frame": "BAY 01",
            "prompt": "Architectural brutalist raw concrete data hall interior with precision brushed steel 2U NVMe storage rack bay stenciled in crisp Helvetica industrial lettering 'BAY 01', directional morning key light casting sharp 45-degree geometric shadow, Leica Summicron 35mm f/8 orthographic perspective, silver-gelatin neutral monochrome palette with single vermilion status LED.",
            "negative_prompt": "purple neon glow, cyberpunk cables, floating 3d spheres, lens flare, stock technician smiling, watermark",
        },
        {
            "id": "kvartz_sled_macro",
            "slot": "passport_01",
            "canon_id": "01_swiss_international_typographic",
            "aspect_ratio": "4:3",
            "exact_text_in_frame": "U.3 NVME",
            "prompt": "Orthographic top-down studio macro photograph of anodized aluminum enterprise solid-state drive carrier with clean laser-engraved label reading 'U.3 NVME', bead-blasted machined chamfers on matte off-white architectural drafting board, neutral 5600K softbox illumination, 90mm apochromatic macro lens, crisp detail.",
            "negative_prompt": "glowing blue circuits, sci-fi hologram, blurry bokeh, rainbow reflections, plastic texture",
        },
        {
            "id": "kvartz_ring_buffer",
            "slot": "passport_02",
            "canon_id": "01_swiss_international_typographic",
            "aspect_ratio": "4:3",
            "exact_text_in_frame": "SYNC OK",
            "prompt": "Swiss typographic industrial control panel detail in matte light-gray powder-coated steel featuring recessed monochrome e-ink diagnostic window reading 'SYNC OK' beside machined rotary selector, raking side daylight, strict horizontal and vertical grid alignment, medium-format 80mm planar lens.",
            "negative_prompt": "neon purple gradient, glossy touchscreen smudges, cartoon UI, cluttered wires, lens flare",
        },
    ],
}


TEMPLATE_02_EN_DARK_SAAS = {
    "slug": "02_dark_saas_observability_en",
    "canon_id": "03_dark_precision_saas_linear",
    "lang": "en",
    "base_url": "https://chronotrace.example.io",
    "title": "ChronoTrace: Zero-Instrumentation eBPF Tail-Latency Observability",
    "description": "Pinpoint p99 syscall and TLS handshake stalls across Kubernetes pods under 1.2% CPU overhead with zero code changes.",
    "og_locale": "en_US",
    "hreflangs": {
        "en": "https://chronotrace.example.io/",
        "ru": "https://chronotrace.example.io/ru/",
        "x-default": "https://chronotrace.example.io/",
    },
    "css": """:root {
  --bg: oklch(0.14 0.012 260);
  --surface: oklch(0.185 0.016 260);
  --border: oklch(0.28 0.02 260);
  --text: oklch(0.93 0.008 260);
  --text-muted: oklch(0.69 0.018 260);
  --accent: oklch(0.56 0.19 258);
  --accent-ink: oklch(0.98 0.005 260);
  --font-sans: 'Geist', 'Inter', system-ui, sans-serif;
  --font-mono: 'Geist Mono', 'JetBrains Mono', ui-monospace, monospace;
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-padding-top: 4.5rem; font-size: 16px; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  line-height: 1.55;
  overflow-x: hidden;
}
.skip-link {
  position: absolute;
  left: -9999px;
  top: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--accent);
  color: var(--accent-ink);
  min-width: 24px;
  min-height: 24px;
}
.skip-link:focus { left: 0.75rem; z-index: 100; }
.site-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}
.header-inner, .container {
  max-width: 80rem;
  margin: 0 auto;
  padding-inline: clamp(1.25rem, 4vw, 3rem);
}
.header-inner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  min-height: 4rem;
  gap: 1rem;
}
.brand-link {
  color: var(--text);
  text-decoration: none;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 28px;
}
.nav-links {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.nav-links a {
  color: var(--text-muted);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  min-width: 28px;
  padding: 0.25rem 0.4rem;
}
.nav-links a:hover, .nav-links a:focus-visible {
  color: var(--text);
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.hero-stage {
  min-height: 100dvh;
  display: grid;
  align-items: center;
  padding-block: clamp(2rem, 5.5vw, 6rem);
  border-bottom: 1px solid var(--border);
}
.bento-macro {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 1.25rem;
}
.hero-copy { grid-column: span 7; }
.hero-waterfall {
  grid-column: span 5;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.25rem;
  box-shadow: 0 12px 32px -8px oklch(0.06 0.01 260);
}
.eyebrow {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text-muted);
  display: inline-block;
  margin-bottom: 0.75rem;
}
h1 {
  font-size: clamp(2rem, 3.8vw, 3.1rem);
  line-height: 1.12;
  letter-spacing: -0.025em;
  margin: 0 0 1.25rem;
  max-width: 20ch;
}
.hero-lead {
  color: var(--text-muted);
  max-width: 62ch;
  font-size: 1.0625rem;
  margin: 0 0 1.75rem;
}
.action-group { display: flex; flex-wrap: wrap; gap: 0.85rem; }
.btn-accent, .btn-ghost, .pct-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  min-width: 40px;
  padding: 0.55rem 1.15rem;
  border-radius: 8px;
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  border: 1px solid var(--border);
  transition: opacity 180ms cubic-bezier(0.16, 1, 0.3, 1);
}
.btn-accent {
  background: var(--accent);
  color: var(--accent-ink);
  border-color: var(--accent);
}
.btn-ghost, .pct-btn {
  background: var(--surface);
  color: var(--text);
}
.pct-btn[aria-pressed="true"] {
  background: var(--accent);
  color: var(--accent-ink);
  border-color: var(--accent);
}
.btn-accent:focus-visible, .btn-ghost:focus-visible, .pct-btn:focus-visible, input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.pct-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
kbd {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  padding: 0.1rem 0.35rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  margin-left: 0.35rem;
}
.section-band {
  padding-block: clamp(2.5rem, 5vw, 5rem);
  border-bottom: 1px solid var(--border);
}
.bento-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.25rem;
}
.bento-card {
  display: grid;
  grid-template-rows: subgrid;
  grid-row: span 3;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.5rem;
  gap: 0.75rem;
}
.bento-card h3 { margin: 0; font-size: 1.125rem; }
.bento-card p { margin: 0; color: var(--text-muted); }
.mono-stat, output, table td {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.estimator-box {
  container-type: inline-size;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.5rem;
}
.estimator-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}
@container (max-width: 600px) {
  .estimator-cols { grid-template-columns: 1fr; }
}
.input-row {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 1rem;
}
.input-row label { font-weight: 600; font-size: 0.9375rem; }
.input-row input {
  min-height: 40px;
  min-width: 40px;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
}
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td {
  text-align: left;
  padding: 0.6rem 0.5rem;
  border-bottom: 1px solid var(--border);
}
.faq-stack { display: grid; gap: 1.25rem; max-width: 64ch; }
.faq-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.25rem;
}
.faq-card h3 { margin: 0 0 0.5rem; font-size: 1.0625rem; }
.faq-card p { margin: 0; color: var(--text-muted); }
.hp-field { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
.site-footer { padding-block: 2rem; color: var(--text-muted); font-size: 0.875rem; }
@media (max-width: 900px) {
  .hero-copy, .hero-waterfall { grid-column: span 12; }
  .bento-cards { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
""",
    "json_ld": {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": "https://chronotrace.example.io/#org",
                "name": "ChronoTrace Systems Inc.",
                "url": "https://chronotrace.example.io/",
            },
            {
                "@type": "WebSite",
                "@id": "https://chronotrace.example.io/#website",
                "url": "https://chronotrace.example.io/",
                "name": "ChronoTrace",
                "inLanguage": "en",
                "publisher": {"@id": "https://chronotrace.example.io/#org"},
            },
            {
                "@type": "WebPage",
                "@id": "https://chronotrace.example.io/#webpage",
                "url": "https://chronotrace.example.io/",
                "name": "ChronoTrace: Zero-Instrumentation eBPF Tail-Latency Observability",
                "isPartOf": {"@id": "https://chronotrace.example.io/#website"},
            },
            {
                "@type": "Product",
                "@id": "https://chronotrace.example.io/#product",
                "name": "ChronoTrace eBPF Collector & ClickHouse Span Engine",
                "brand": {"@id": "https://chronotrace.example.io/#org"},
                "description": "Kernel-verified eBPF distributed trace and syscall stall profiler under 1.2% CPU overhead.",
                "offers": {
                    "@type": "Offer",
                    "price": "29",
                    "priceCurrency": "USD",
                    "availability": "https://schema.org/InStock",
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": "https://chronotrace.example.io/#breadcrumbs",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://chronotrace.example.io/"},
                    {"@type": "ListItem", "position": 2, "name": "Architecture", "item": "https://chronotrace.example.io/#architecture"},
                ],
            },
            {
                "@type": "FAQPage",
                "@id": "https://chronotrace.example.io/#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "Which Linux kernel versions does ChronoTrace support out of the box?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "ChronoTrace runs on any Linux host with kernel 5.10 LTS or newer that exposes BTF (BPF Type Format) headers. No kernel module compilation, DKMS package, or application container restart is required.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Can an eBPF probe crash or hang our production Kubernetes nodes?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Unlike out-of-tree kernel modules, eBPF bytecode cannot dereference arbitrary pointers or loop infinitely: the in-kernel Linux verifier mathematically proves bounded termination and read-only memory safety before JIT load.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "How does ChronoTrace prevent surprise overage bills during traffic spikes?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Operators set a hard monthly USD spend cap per cluster: if logging loops spike span volume, dynamic tail-sampling drops healthy HTTP 200 traces first while retaining 100% of 5xx errors and slow p99 outliers at $0 unapproved overage.",
                        },
                    },
                ],
            },
        ],
    },
    "body_html": """<a class="skip-link" href="#main-content">Skip to main content</a>
<header class="site-header">
  <div class="header-inner">
    <a class="brand-link" href="#main-content">
      <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 7v5l3 3" fill="none" stroke="currentColor" stroke-width="2"/></svg>
      <span>ChronoTrace</span>
    </a>
    <nav aria-label="Primary navigation">
      <ul class="nav-links">
        <li><a href="#architecture">Bento Specs</a></li>
        <li><a href="#estimator">Span Estimator</a></li>
        <li><a href="#faq">FAQ</a></li>
        <li><a href="#sandbox">Sandbox Access</a></li>
      </ul>
    </nav>
  </div>
</header>

<main id="main-content">
  <section class="hero-stage">
    <div class="container bento-macro">
      <div class="hero-copy">
        <span class="eyebrow">KERNEL 5.10+ CO-RE eBPF // ZERO SDK REBUILDS</span>
        <h1>Pinpoint p99 syscall and TLS stalls under 1.2% CPU overhead</h1>
        <p class="hero-lead">Attach verified eBPF socket and scheduler probes across Kubernetes pods in 15 seconds. Correlate DNS retries, TLS 1.3 handshakes, and Postgres wire waits without touching application containers.</p>
        <div class="action-group">
          <a class="btn-accent" href="#sandbox">Open live trace sandbox (50M spans, no card)</a>
          <a class="btn-ghost" href="#estimator">Calculate monthly ingest cost</a>
        </div>
      </div>
      <div class="hero-waterfall" aria-label="Interactive span latency inspector">
        <div class="pct-toolbar" role="group" aria-label="Latency percentile selector">
          <button type="button" class="pct-btn" data-pct="p50" aria-pressed="false">p50 <kbd>1</kbd></button>
          <button type="button" class="pct-btn" data-pct="p95" aria-pressed="false">p95 <kbd>2</kbd></button>
          <button type="button" class="pct-btn" data-pct="p99" aria-pressed="true">p99 <kbd>3</kbd></button>
        </div>
        <p class="mono-stat" id="traceSummaryReadout">checkout.grpc -> p99 total: 42.8 ms (TLS stall: 26.4 ms)</p>
        <svg width="380" height="148" viewBox="0 0 380 148" role="img" aria-labelledby="wfTitle">
          <title id="wfTitle">Span waterfall timeline across DNS, TLS, and Postgres</title>
          <text x="4" y="28" font-size="12" fill="currentColor">1. tcp_connect</text>
          <rect id="spanTcpRect" x="120" y="16" width="44" height="14" rx="3" fill="currentColor"/>
          <text x="4" y="68" font-size="12" fill="currentColor">2. tls_handshake</text>
          <rect id="spanTlsRect" x="164" y="56" width="142" height="14" rx="3" fill="currentColor"/>
          <text x="4" y="108" font-size="12" fill="currentColor">3. pg_query_exec</text>
          <rect id="spanPgRect" x="306" y="96" width="58" height="14" rx="3" fill="currentColor"/>
        </svg>
      </div>
    </div>
  </section>

  <section id="architecture" class="section-band">
    <div class="container">
      <h2>Engineered for deterministic production overhead</h2>
      <div class="bento-cards">
        <article class="bento-card">
          <span class="mono-stat">0.9% MEDIAN CPU</span>
          <h3>Ring-buffer batching in kernel space</h3>
          <p>Per-core BPF ring buffers aggregate socket events before waking userspace collectors, avoiding context-switch storms under 100k RPS bursts.</p>
        </article>
        <article class="bento-card">
          <span class="mono-stat">15.4 : 1 ZSTD</span>
          <h3>Columnar ClickHouse span storage</h3>
          <p>Dictionary-encoded service graphs compress 10 TB of raw OTLP traces down to 650 GB on local NVMe with sub-second percentile histograms.</p>
        </article>
        <article class="bento-card">
          <span class="mono-stat">100% 5XX KEPT</span>
          <h3>Head-free tail anomaly sampling</h3>
          <p>Drop routine sub-10ms healthchecks automatically while locking every HTTP 5xx, gRPC deadline-exceeded, and p99 outlier trace to disk.</p>
        </article>
      </div>
    </div>
  </section>

  <section id="estimator" class="section-band">
    <div class="container">
      <h2>Deterministic cluster &amp; span bill estimator</h2>
      <div class="estimator-box">
        <div class="estimator-cols">
          <div>
            <div class="input-row">
              <label for="nodeCountInput">Kubernetes worker nodes</label>
              <input id="nodeCountInput" name="nodes" type="number" min="1" max="2000" value="18" autocomplete="off"/>
            </div>
            <div class="input-row">
              <label for="rpsInput">Sustained cluster HTTP/gRPC requests per second</label>
              <input id="rpsInput" name="rps" type="number" min="100" max="500000" step="100" value="4500" autocomplete="off"/>
            </div>
          </div>
          <div>
            <table class="data-table" aria-label="Estimated monthly telemetry footprint">
              <tbody>
                <tr>
                  <th scope="row">Retained tail-sampled spans / mo</th>
                  <td><output id="spansMillionOut" for="nodeCountInput rpsInput">583M spans</output></td>
                </tr>
                <tr>
                  <th scope="row">Compressed ClickHouse NVMe</th>
                  <td><output id="nvmeGbOut" for="nodeCountInput rpsInput">94.5 GB</output></td>
                </tr>
                <tr>
                  <th scope="row">Transparent monthly total ($29/node + $0.18/GB)</th>
                  <td><output id="billUsdOut" for="nodeCountInput rpsInput">$539 / mo</output></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="faq" class="section-band">
    <div class="container">
      <h2>Frequently asked engineering questions</h2>
      <div class="faq-stack">
        <article class="faq-card">
          <h3>Which Linux kernel versions does ChronoTrace support out of the box?</h3>
          <p>ChronoTrace runs on any Linux host with kernel 5.10 LTS or newer that exposes BTF (BPF Type Format) headers. No kernel module compilation, DKMS package, or application container restart is required.</p>
        </article>
        <article class="faq-card">
          <h3>Can an eBPF probe crash or hang our production Kubernetes nodes?</h3>
          <p>Unlike out-of-tree kernel modules, eBPF bytecode cannot dereference arbitrary pointers or loop infinitely: the in-kernel Linux verifier mathematically proves bounded termination and read-only memory safety before JIT load.</p>
        </article>
        <article class="faq-card">
          <h3>How does ChronoTrace prevent surprise overage bills during traffic spikes?</h3>
          <p>Operators set a hard monthly USD spend cap per cluster: if logging loops spike span volume, dynamic tail-sampling drops healthy HTTP 200 traces first while retaining 100% of 5xx errors and slow p99 outliers at $0 unapproved overage.</p>
        </article>
      </div>
    </div>
  </section>

  <section id="sandbox" class="section-band">
    <div class="container">
      <h2>Request an isolated Helm chart or sandbox token</h2>
      <form id="sandboxForm" action="#sandbox" method="post" novalidate>
        <div class="estimator-cols">
          <div class="input-row">
            <label for="devNameInput">Engineering lead name</label>
            <input id="devNameInput" name="name" type="text" required autocomplete="name"/>
          </div>
          <div class="input-row">
            <label for="devEmailInput">Work email address</label>
            <input id="devEmailInput" name="email" type="email" required autocomplete="email"/>
          </div>
        </div>
        <div class="hp-field" aria-hidden="true">
          <label for="botUrlTrap">Leave this internal URL field blank</label>
          <input id="botUrlTrap" name="website_hp" type="text" tabindex="-1" autocomplete="off"/>
        </div>
        <button class="btn-accent" type="submit">Issue read-only sandbox token (no card required)</button>
        <p id="sandboxStatus" class="mono-stat" role="status" aria-live="polite">Zero tracking cookies. Sandbox credentials expire automatically after 14 days.</p>
      </form>
    </div>
  </section>
</main>

<footer class="site-footer">
  <div class="container">
    <p>ChronoTrace Systems Inc., 2026. Zero external scripts, SHA-256 CSP + Trusted Types enforced, SIL OFL-1.1 typography.</p>
  </div>
</footer>""",
    "ts_code": """interface PercentileProfile {
  summary: string;
  tcpW: number;
  tlsX: number;
  tlsW: number;
  pgX: number;
  pgW: number;
}

const PROFILES: Record<string, PercentileProfile> = {
  p50: {
    summary: "checkout.grpc -> p50 total: 6.4 ms (TLS session resumed: 1.8 ms)",
    tcpW: 20,
    tlsX: 140,
    tlsW: 28,
    pgX: 168,
    pgW: 36,
  },
  p95: {
    summary: "checkout.grpc -> p95 total: 18.2 ms (TLS handshake: 8.6 ms)",
    tcpW: 32,
    tlsX: 152,
    tlsW: 78,
    pgX: 230,
    pgW: 48,
  },
  p99: {
    summary: "checkout.grpc -> p99 total: 42.8 ms (TLS stall: 26.4 ms)",
    tcpW: 44,
    tlsX: 164,
    tlsW: 142,
    pgX: 306,
    pgW: 58,
  },
};

function setupTrustedTypes(): void {
  const w = window as unknown as {
    trustedTypes?: { createPolicy: (name: string, rules: { createHTML: (s: string) => string }) => unknown };
  };
  if (w.trustedTypes && typeof w.trustedTypes.createPolicy === "function") {
    try {
      w.trustedTypes.createPolicy("default", {
        createHTML: (s: string): string => s.replace(/[<>]/g, ""),
      });
    } catch {
      // Policy already active
    }
  }
}

function initChronoTrace(): void {
  setupTrustedTypes();

  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>(".pct-btn"));
  const readout = document.getElementById("traceSummaryReadout");
  const tcpRect = document.getElementById("spanTcpRect");
  const tlsRect = document.getElementById("spanTlsRect");
  const pgRect = document.getElementById("spanPgRect");

  const selectPercentile = (key: string): void => {
    const prof = PROFILES[key] || PROFILES.p99;
    buttons.forEach((btn) => {
      const active = btn.dataset.pct === key;
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
    if (readout) {
      readout.textContent = prof.summary;
    }
    if (tcpRect && tlsRect && pgRect) {
      tcpRect.setAttribute("width", String(prof.tcpW));
      tlsRect.setAttribute("x", String(prof.tlsX));
      tlsRect.setAttribute("width", String(prof.tlsW));
      pgRect.setAttribute("x", String(prof.pgX));
      pgRect.setAttribute("width", String(prof.pgW));
    }
  };

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      selectPercentile(btn.dataset.pct || "p99");
    });
  });

  document.addEventListener("keydown", (ev: KeyboardEvent): void => {
    const target = ev.target as HTMLElement | null;
    if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) {
      return;
    }
    if (ev.key === "1") selectPercentile("p50");
    if (ev.key === "2") selectPercentile("p95");
    if (ev.key === "3") selectPercentile("p99");
  });

  const nodeInput = document.getElementById("nodeCountInput") as HTMLInputElement | null;
  const rpsInput = document.getElementById("rpsInput") as HTMLInputElement | null;
  const spansOut = document.getElementById("spansMillionOut") as HTMLOutputElement | null;
  const nvmeOut = document.getElementById("nvmeGbOut") as HTMLOutputElement | null;
  const billOut = document.getElementById("billUsdOut") as HTMLOutputElement | null;

  const updateBill = (): void => {
    if (!nodeInput || !rpsInput || !spansOut || !nvmeOut || !billOut) {
      return;
    }
    const nodes = Math.max(1, Math.min(2000, Number.parseInt(nodeInput.value || "18", 10) || 18));
    const rps = Math.max(100, Math.min(500000, Number.parseInt(rpsInput.value || "4500", 10) || 4500));
    const retainedSpansMillions = Math.round((rps * 86400 * 30 * 0.05) / 1_000_000);
    const nvmeGb = +(retainedSpansMillions * 0.162).toFixed(1);
    const totalUsd = Math.round(nodes * 29 + nvmeGb * 0.18);
    spansOut.textContent = `${retainedSpansMillions.toLocaleString("en-US")}M spans`;
    nvmeOut.textContent = `${nvmeGb.toFixed(1)} GB`;
    billOut.textContent = `$${totalUsd.toLocaleString("en-US")} / mo`;
  };

  if (nodeInput && rpsInput) {
    nodeInput.addEventListener("input", updateBill);
    rpsInput.addEventListener("input", updateBill);
    updateBill();
  }

  const form = document.getElementById("sandboxForm") as HTMLFormElement | null;
  const hp = document.getElementById("botUrlTrap") as HTMLInputElement | null;
  const email = document.getElementById("devEmailInput") as HTMLInputElement | null;
  const status = document.getElementById("sandboxStatus");

  if (form && status) {
    form.addEventListener("submit", (ev: Event): void => {
      ev.preventDefault();
      if (hp && hp.value.trim().length > 0) {
        status.textContent = "Submission blocked by automated honeypot check.";
        return;
      }
      const addr = email ? email.value.trim() : "";
      if (!addr.includes("@") || !addr.includes(".")) {
        status.textContent = "Enter a valid engineering email address (example: sasha@company.io).";
        return;
      }
      status.textContent = "Sandbox token staged locally: read-only ClickHouse trace link ready.";
    });
  }
}

initChronoTrace();
export {};
""",
    "llms_txt": """# ChronoTrace (Zero-Instrumentation eBPF Observability)

> Kernel-verified CO-RE eBPF distributed tracing and tail-latency profiler pinpointing p99 syscall, DNS, TLS, and Postgres stalls across Kubernetes pods under 1.2% CPU overhead.

## Core Architecture
- [Bento Specifications](https://chronotrace.example.io/#architecture): Per-core BPF ring buffers, 15.4:1 Zstandard ClickHouse span storage, and 100% 5xx tail sampling.
- [Cluster Cost Estimator](https://chronotrace.example.io/#estimator): Deterministic pricing at $29 per worker node plus $0.18 per compressed GB.

## Security & Kernel Compatibility
- [Engineering FAQ](https://chronotrace.example.io/#faq): Linux 5.10+ BTF support without DKMS, in-kernel verifier safety guarantees, and hard monthly spend caps.
""",
    "zimage_prompts": [
        {
            "id": "chrono_tap_chassis",
            "slot": "hero_primary",
            "canon_id": "03_dark_precision_saas_linear",
            "aspect_ratio": "16:9",
            "exact_text_in_frame": "EBPF RING",
            "prompt": "Macro studio product photograph of CNC-machined dark slate anodized aluminum rack telemetry module resting on matte obsidian stone, crisp laser-etched bezel reading 'EBPF RING', subtle indigo optical fiber edge light, 90mm apochromatic macro lens f/5.6, controlled specular micro-bevel highlights, clean dark studio.",
            "negative_prompt": "glowing purple brain, cartoon robot, lens flare explosion, stock office handshake, blurry fog",
        },
        {
            "id": "chrono_nic_transceiver",
            "slot": "bento_01",
            "canon_id": "03_dark_precision_saas_linear",
            "aspect_ratio": "4:3",
            "exact_text_in_frame": "100G QSFP",
            "prompt": "Precision 100G optical network transceiver cage in brushed gunmetal steel with engraved port marker '100G QSFP' and single sapphire status indicator, low-key studio rim lighting, focus-stacked 105mm macro photography, crisp machined geometry, dark neutral slate background.",
            "negative_prompt": "green matrix rain, hooded hacker, neon pink glow, messy ethernet cables, watermark",
        },
        {
            "id": "chrono_nvme_coldplate",
            "slot": "bento_02",
            "canon_id": "03_dark_precision_saas_linear",
            "aspect_ratio": "4:3",
            "exact_text_in_frame": "ZSTD 15X",
            "prompt": "Orthographic macro detail of matte black anodized copper heat-spreader block on enterprise storage card stamped 'ZSTD 15X', subtle cool slate directional key light, razor-sharp milled fin edges, medium-format studio technical photography.",
            "negative_prompt": "fire flames, glowing lava, cartoon lightning bolt, oversaturated cyan, blurry noise",
        },
    ],
}
