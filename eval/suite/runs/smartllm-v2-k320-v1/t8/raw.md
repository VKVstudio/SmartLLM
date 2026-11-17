FILE: index.html

```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Экстремальная ультрафиолетовая литография (EUV 13.5 нм) — АРХИВ ТЕХНОЛОГИЙ №14</title>
<meta name="description" content="Выпуск №14 инженерного альманаха «Архив технологий»: оптика Zeiss, оловянная плазма, зеркало Брэгга Mo/Si, High-NA 0.55, интерактивный калькулятор критерия Рэлея и сравнение поколений литографии.">
<link rel="canonical" href="https://example.com/arkhiv-tehnologiy/14">
<meta property="og:type" content="article">
<meta property="og:title" content="Экстремальная ультрафиолетовая литография (EUV 13.5 нм) — АРХИВ ТЕХНОЛОГИЙ №14">
<meta property="og:description" content="Оптика Zeiss, оловянная плазма, зеркало Брэгга Mo/Si, High-NA 0.55, калькулятор критерия Рэлея и сравнение поколений литографии.">
<meta property="og:url" content="https://example.com/arkhiv-tehnologiy/14">
<meta property="og:site_name" content="Архив технологий">
<meta property="og:locale" content="ru_RU">
<meta property="article:published_time" content="2025-06-12T09:00+03:00">
<meta name="twitter:card" content="summary_large_image">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; upgrade-insecure-requests; script-src 'self' 'sha256-__CSP_SCRIPT__'; style-src 'self' 'sha256-__CSP_STYLE__'; img-src 'self' data:; font-src 'self'; connect-src 'self'; manifest-src 'self'; worker-src 'none'; block-all-mixed-content">
<meta name="theme-color" content="oklch(0.96 0.015 80)">

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://example.com/#org",
      "name": "Архив технологий",
      "alternateName": "Arkhiv Tekhnologiy",
      "url": "https://example.com/",
      "logo": "https://example.com/logo.svg",
      "description": "Инженерный альманах о физике полупроводников, литографии и оптических системах.",
      "sameAs": ["https://example.com/llms.txt"]
    },
    {
      "@type": "WebSite",
      "@id": "https://example.com/#site",
      "name": "Архив технологий",
      "url": "https://example.com/",
      "publisher": {"@id": "https://example.com/#org"},
      "inLanguage": "ru"
    },
    {
      "@type": "BreadcrumbList",
      "@id": "https://example.com/arkhiv-tehnologiy/14#breadcrumbs",
      "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Архив технологий", "item": "https://example.com/"},
        {"@type": "ListItem", "position": 2, "name": "Выпуск №14", "item": "https://example.com/arkhiv-tehnologiy/14"},
        {"@type": "ListItem", "position": 3, "name": "Экстремальная ультрафиолетовая литография (EUV 13.5 нм)", "item": "https://example.com/arkhiv-tehnologiy/14#cover"}
      ]
    },
    {
      "@type": "Article",
      "@id": "https://example.com/arkhiv-tehnologiy/14#article",
      "headline": "Экстремальная ультрафиолетовая литография (EUV 13.5 нм): оптика Цейсса, оловянная плазма и предел кремниевых транзисторов",
      "name": "Экстремальная ультрафиолетовая литография (EUV 13.5 нм)",
      "articleSection": "Литография",
      "inLanguage": "ru",
      "datePublished": "2025-06-12T09:00+03:00",
      "dateModified": "2025-06-12T09:00+03:00",
      "author": {"@type": "Organization", "@id": "https://example.com/#org"},
      "publisher": {"@id": "https://example.com/#org"},
      "isPartOf": {"@type": "Periodical", "name": "Архив технологий", "issn": "2711-4028"},
      "mainEntityOfPage": {"@id": "https://example.com/arkhiv-tehnologiy/14#article"},
      "about": [
        {"@type": "Thing", "name": "Экстремальная ультрафиолетовая литография"},
        {"@type": "Thing", "name": "Оловянная плазма (LPP)"},
        {"@type": "Thing", "name": "Многослойное зеркало Mo/Si (Брэгг)"},
        {"@type": "Thing", "name": "Проекционная оптика High-NA 0.55"}
      ]
    },
    {
      "@type": "Product",
      "@id": "https://example.com/arkhiv-tehnologiy/14#duv",
      "name": "DUV ArFi 193 нм, иммерсионный сканер (NA 1.35)",
      "category": "Литографический сканер",
      "brand": {"@type": "Organization", "@id": "https://example.com/#org"},
      "description": "Иммерсионная литография ArFi 193 нм: λ=193 нм, NA=1.35, k1=0.25, k2=0.20, разрешение ~38 нм, плотность ~190 млн/мм², 40–60 масок.",
      "additionalProperty": [
        {"@type": "PropertyValue", "name": "Длина волны", "value": "193 нм"},
        {"@type": "PropertyValue", "name": "Числовая апертура", "value": "1.35"},
        {"@type": "PropertyValue", "name": "Разрешение", "value": "38 нм"},
        {"@type": "PropertyValue", "name": "Плотность транзисторов", "value": "190 млн/мм²"},
        {"@type": "PropertyValue", "name": "Число масок", "value": "40–60"}
      ]
    },
    {
      "@type": "Product",
      "@id": "https://example.com/arkhiv-tehnologiy/14#euv-lo",
      "name": "Low-NA EUV 13.5 нм, сканер NA 0.33",
      "category": "Литографический сканер",
      "brand": {"@type": "Organization", "@id": "https://example.com/#org"},
      "description": "EUV Low-NA 13.5 нм: λ=13.5 нм, NA=0.33, k1=0.25, k2=0.20, разрешение ~13 нм, плотность ~300 млн/мм², 35–50 масок.",
      "additionalProperty": [
        {"@type": "PropertyValue", "name": "Длина волны", "value": "13.5 нм"},
        {"@type": "PropertyValue", "name": "Числовая апертура", "value": "0.33"},
        {"@type": "PropertyValue", "name": "Разрешение", "value": "13 нм"},
        {"@type": "PropertyValue", "name": "Плотность транзисторов", "value": "300 млн/мм²"},
        {"@type": "PropertyValue", "name": "Число масок", "value": "35–50"}
      ]
    },
    {
      "@type": "Product",
      "@id": "https://example.com/arkhiv-tehnologiy/14#euv-hina",
      "name": "High-NA EUV 13.5 нм, сканер NA 0.55",
      "category": "Литографический сканер",
      "brand": {"@type": "Organization", "@id": "https://example.com/#org"},
      "description": "EUV High-NA 13.5 нм: λ=13.5 нм, NA=0.55, k1=0.25, k2=0.20, разрешение ~8 нм, плотность ~500 млн/мм², 25–35 масок.",
      "additionalProperty": [
        {"@type": "PropertyValue", "name": "Длина волны", "value": "13.5 нм"},
        {"@type": "PropertyValue", "name": "Числовая апертура", "value": "0.55"},
        {"@type": "PropertyValue", "name": "Разрешение", "value": "8 нм"},
        {"@type": "PropertyValue", "name": "Плотность транзисторов", "value": "500 млн/мм²"},
        {"@type": "PropertyValue", "name": "Число масок", "value": "25–35"}
      ]
    },
    {
      "@type": "FAQPage",
      "@id": "https://example.com/arkhiv-tehnologiy/14#faq",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "Почему в EUV вся оптика отражательная, а не преломляющая?",
          "acceptedAnswer": {"@type": "Answer", "text": "На длине волны 13.5 нм практически все материалы — стекло, кварц, воздух — поглощают излучение и не пропускают его на полезную толщину. Линза из стекла за несколько миллиметров поглотит почти весь свет. Поэтому тракт целиком отражательный: многослойные зеркала Mo/Si (молибден/кремний) работают как зеркало Брэгга. Отражательная схема требует нескольких зеркал и сложной геометрии, но без неё EUV невозможен."}
        },
        {
          "@type": "Question",
          "name": "Зачем оловянная плазма, если светить можно и другим материалом?",
          "acceptedAnswer": {"@type": "Answer", "text": "Олово (Sn) выбрано из-за высокой конверсии энергии в EUV и чистого спектра в окне 13.5 нм. Капли олова диаметром около 30 мкм выпускаются с частотой порядка 50 кГц и дважды облучаются CO₂-лазером: сначала пред-пульс формирует облако, основной импульс превращает его в плазму. Плазма — это источник, а не готовый луч: большая часть энергии теряется, а зеркало-коллектор Брэгга собирает лишь малую долю излучения. Именно эффективность сбора, а не мощность лазера, определяет светосилу всего сканера."}
        },
        {
          "@type": "Question",
          "name": "Что такое зеркало Брэгга и почему это Mo/Si?",
          "acceptedAnswer": {"@type": "Answer", "text": "Зеркало Брэгга — многослойная структура из чередующихся слоёв молибдена и кремния (Mo/Si), около 40–50 пар. Каждый слой настроен так, чтобы отражение складывалось конструктивно на длине волны 13.5 нм. Отражение одного слоя ничтожно, но сумма десятков слоёв даёт отражательную способность порядка 60–70 % — максимум, доступный для этой длины волны. Альтернативы (например, бор) дают меньшее отражение, поэтому Mo/Si остаётся стандартом для EUV."}
        },
        {
          "@type": "Question",
          "name": "Чем High-NA 0.55 лучше Low-NA 0.33 и что это меняет?",
          "acceptedAnswer": {"@type": "Answer", "text": "Числовая апертура (NA) определяет разрешающую способность по критерию Рэлея: чем больше NA, тем меньше минимальный размер элемента при той же длине волны. High-NA 0.55 против Low-NA 0.33 даёт примерно вдвое меньший критический размер, но одновременно вдвое меньшую глубину резкости. Это означает более строгие допуски по фокусу, более сложную оптику и более дорогое оборудование. High-NA позволяет уменьшить число маскирований (SAOP вместо SAQP) и удержать производство в пределах разумной стоимости."}
        },
        {
          "@type": "Question",
          "name": "Где физический предел кремниевых транзисторов?",
          "acceptedAnswer": {"@type": "Answer", "text": "Предел — не только литография. При уменьшении канала растёт утечка через диэлектрик, а физически минимальный размер элемента упирается в длину волны и дифракционный предел optics. Дальнейшее уменьшение требует новых материалов: высоко-k диэлектриков, новых структур канала, а в перспективе — переход к другим архитектурам (GAA-транзисторы, CFET, 2D-материалы). Литография здесь — инструмент, но физика материалов накладывает собственный потолок, который нельзя «пробить» одной лишь оптикой."}
        }
      ]
    }
  ]
}
</script>

<style>
/* ===== Дизайн-токены OKLCH ===== */
:root{
  --paper: oklch(0.96 0.015 80);
  --paper-2: oklch(0.93 0.012 80);
  --ink: oklch(0.16 0.02 50);
  --ink-2: oklch(0.35 0.02 50);
  --accent: oklch(0.48 0.18 25);
  --accent-soft: oklch(0.72 0.12 25);
  --rule: oklch(0.80 0.02 75);
  --rule-strong: oklch(0.62 0.03 60);
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia, "Times New Roman", serif;
  --sans: "Helvetica Neue", "Segoe UI", Roboto, system-ui, -apple-system, Arial, sans-serif;
  --mono: ui-monospace, "SFMono-Regular", "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  --max: 1160px;
  --gutter: clamp(1rem, 3vw, 2.25rem);
}

*, *::before, *::after{ box-sizing: border-box; }
html, body{ max-width: 100%; overflow-x: clip; }
html{ scroll-behavior: smooth; }
body{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--serif);
  font-size: 18px;
  line-height: 1.6;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}
img, svg, canvas{ max-width: 100%; height: auto; }
a{ color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }
a:hover{ color: var(--ink); }
:focus-visible{ outline: 2px solid var(--accent); outline-offset: 3px; }

/* ===== Прогресс чтения ===== */
.progress{
  position: fixed; inset: 0 auto auto 0; height: 3px; width: 100%;
  background: transparent; z-index: 50; pointer-events: none;
}
.progress span{
  display: block; height: 100%; width: 0;
  background: var(--accent);
  transition: width .12s linear;
}

/* ===== Шапка-обложка ===== */
.masthead{
  border-bottom: 1px solid var(--rule-strong);
  padding: 1.25rem var(--gutter) 1rem;
}
.masthead-inner{ max-width: var(--max); margin: 0 auto; }
.mast-top{
  display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem 1.25rem;
  font-family: var(--mono); font-size: .8rem; letter-spacing: .04em;
  color: var(--ink-2); text-transform: uppercase;
}
.mast-top .brand{ font-family: var(--serif); font-size: 1.15rem; letter-spacing: .12em; color: var(--ink); font-weight: 700; }
.mast-top .issue{ margin-left: auto; color: var(--accent); font-weight: 700; }

/* ===== Обложка ===== */
.cover{
  container-type: inline-size;
  max-width: var(--max);
  margin: 0 auto;
  padding: clamp(1.5rem, 4vw, 3.5rem) var(--gutter);
  display: grid;
  gap: 1.5rem;
  grid-template-columns: 1fr;
  grid-template-areas: "lead" "toc";
}
.cover .lead{ grid-area: lead; }
.cover .toc{ grid-area: toc; }
.cover h1{
  font-family: var(--serif);
  font-size: clamp(2rem, 6vw, 4rem);
  line-height: 1.05;
  margin: 0 0 .5rem;
  letter-spacing: -0.01em;
}
.cover .kicker{
  font-family: var(--mono); font-size: .85rem; letter-spacing: .18em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 1rem;
}
.cover .lead p{
  font-size: clamp(1.1rem, 2.2vw, 1.35rem);
  line-height: 1.5; color: var(--ink-2); max-width: 52ch;
}
.toc h2{
  font-family: var(--mono); font-size: .85rem; letter-spacing: .12em;
  text-transform: uppercase; color: var(--ink-2);
  border-top: 1px solid var(--rule); padding-top: 1rem; margin: 0 0 .75rem;
}
.toc ol{ margin: 0; padding: 0; list-style: none; counter-reset: toc; }
.toc ol li{ counter-increment: toc; }
.toc ol li a{
  display: flex; align-items: baseline; gap: .75rem;
  font-family: var(--sans); font-size: .95rem; padding: .35rem 0;
  border-bottom: 1px solid var(--rule); text-decoration: none; color: var(--ink);
}
.toc ol li a::before{
  content: counter(toc, decimal-leading-zero);
  font-family: var(--mono); color: var(--accent); font-size: .85rem;
}
.toc ol li a:hover{ color: var(--accent); }

@container (min-width: 720px){
  .cover{
    grid-template-columns: 1fr 1fr;
    grid-template-areas: "lead toc";
    align-items: end;
  }
  .cover .lead{ padding-right: 1.5rem; }
}

/* ===== Основной лонгрид ===== */
main{ max-width: var(--max); margin: 0 auto; padding: 0 var(--gutter); }
section{ padding: clamp(2rem, 5vw, 3.5rem) 0; border-bottom: 1px solid var(--rule); }
section:last-of-type{ border-bottom: 0; }

.section-head{
  display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem 1rem;
  margin-bottom: 1.5rem;
}
.section-head .num{
  font-family: var(--mono); font-size: .85rem; color: var(--accent);
  letter-spacing: .12em;
}
.section-head h2{
  font-family: var(--serif); font-size: clamp(1.6rem, 3.5vw, 2.4rem);
  margin: 0; line-height: 1.1;
}
.section-head .dek{ font-family: var(--sans); font-size: .95rem; color: var(--ink-2); max-width: 40ch; }

/* Многоколоночная статья */
.article{
  container-type: inline-size;
  columns: 1;
  column-gap: var(--gutter);
  font-family: var(--serif);
  font-size: 1.05rem;
}
.article p{ margin: 0 0 1rem; text-align: justify; hyphens: auto; }
.article p:first-of-type::first-letter{
  font-family: var(--serif);
  font-size: 4.2em;
  float: left;
  line-height: 0.8;
  margin: .05em .12em 0 0;
  color: var(--accent);
  font-weight: 700;
}
@container (min-width: 760px){
  .article{ columns: 2; column-rule: 1px solid var(--rule); }
}
@container (min-width: 1024px){
  .article{ columns: 3; }
}

/* Маргиналии */
.aside-note{
  break-inside: avoid;
  font-family: var(--sans);
  font-size: .9rem;
  color: var(--ink-2);
  border-top: 2px solid var(--accent);
  padding-top: .6rem;
  margin: 1.25rem 0;
}
.aside-note .label{
  font-family: var(--mono); font-size: .75rem; letter-spacing: .1em;
  text-transform: uppercase; color: var(--accent); display: block; margin-bottom: .4rem;
}

/* Формулы и выноски */
.formula{
  font-family: var(--mono);
  font-size: .95rem;
  background: var(--paper-2);
  border-left: 3px solid var(--accent);
  padding: .75rem 1rem;
  margin: 1.25rem 0;
  break-inside: avoid;
  white-space: nowrap;
  overflow-x: auto;
}
.pullquote{
  font-family: var(--serif);
  font-size: 1.4rem;
  line-height: 1.3;
  color: var(--ink);
  border-top: 1px solid var(--rule-strong);
  border-bottom: 1px solid var(--rule-strong);
  padding: 1rem 0;
  margin: 1.5rem 0;
  break-inside: avoid;
}

/* ===== Таблица ===== */
.table-wrap{ overflow-x: auto; -webkit-overflow-scrolling: touch; }
table{
  width: 100%;
  border-collapse: collapse;
  font-family: var(--sans);
  font-size: .95rem;
  min-width: 560px;
}
thead th{
  font-family: var(--mono); font-size: .78rem; letter-spacing: .08em;
  text-transform: uppercase; color: var(--ink-2);
  text-align: left; padding: .75rem .75rem; border-bottom: 2px solid var(--rule-strong);
}
tbody th, tbody td{ padding: .85rem .75rem; border-bottom: 1px solid var(--rule); }
tbody th{ font-family: var(--serif); font-weight: 600; color: var(--ink); }
tbody tr:nth-child(odd){ background: var(--paper-2); }
tbody tr:hover{ background: var(--accent-soft); }
td.num{ font-family: var(--mono); font-variant-numeric: tabular-nums; }
caption{
  font-family: var(--mono); font-size: .8rem; color: var(--ink-2);
  text-align: left; margin-bottom: .75rem; letter-spacing: .06em;
}

/* ===== Калькулятор ===== */
.calc{
  container-type: inline-size;
  display: grid;
  gap: 1.5rem;
  grid-template-columns: 1fr;
  align-items: start;
}
.calc-controls{
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}
.calc-field label{
  display: block; font-family: var(--mono); font-size: .75rem;
  letter-spacing: .08em; text-transform: uppercase; color: var(--ink-2); margin-bottom: .35rem;
}
.calc-field input[type="range"]{ width: 100%; accent-color: var(--accent); }
.calc-field .val{ font-family: var(--mono); font-size: .9rem; color: var(--accent); }
.calc-readout{
  font-family: var(--mono);
  display: grid;
  gap: .75rem;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
}
.calc-readout .stat{
  background: var(--paper-2);
  border: 1px solid var(--rule);
  padding: .85rem 1rem;
}
.calc-readout .stat b{ display: block; font-size: 1.5rem; color: var(--ink); }
.calc-readout .stat span{ font-size: .75rem; color: var(--ink-2); text-transform: uppercase; letter-spacing: .08em; }
.calc-svg{ container-type: inline-size; }
.calc-svg svg{ display: block; }

@container (min-width: 820px){
  .calc{ grid-template-columns: 1.1fr 1fr; }
}

/* ===== FAQ ===== */
.faq details{
  border-bottom: 1px solid var(--rule);
  padding: .25rem 0;
}
.faq summary{
  font-family: var(--serif);
  font-size: 1.15rem;
  cursor: pointer;
  padding: .9rem 0;
  list-style: none;
  display: flex; align-items: baseline; gap: .75rem;
}
.faq summary::-webkit-details-marker{ display: none; }
.faq summary .q{ font-family: var(--mono); color: var(--accent); font-size: .85rem; }
.faq details[open] summary{ color: var(--accent); }
.faq .answer{ padding: 0 0 1.25rem 0; font-family: var(--serif); color: var(--ink-2); }

/* ===== Форма ===== */
.subscribe{
  container-type: inline-size;
  display: grid;
  gap: 1rem;
  grid-template-columns: 1fr;
}
.subscribe .field{ display: flex; flex-direction: column; gap: .35rem; }
.subscribe label{ font-family: var(--mono); font-size: .75rem; text-transform: uppercase; letter-spacing: .08em; color: var(--ink-2); }
.subscribe input, .subscribe select{
  font-family: var(--sans); font-size: 1rem; color: var(--ink);
  background: var(--paper-2); border: 1px solid var(--rule);
  padding: .65rem .8rem; border-radius: 0;
}
.subscribe input:focus, .subscribe select:focus{ border-color: var(--accent); }
.subscribe input.invalid, .subscribe select.invalid{ border-color: var(--accent); background: oklch(0.9 0.05 25); }
.subscribe .error{ font-family: var(--mono); font-size: .75rem; color: var(--accent); min-height: 1em; }
.subscribe .row{ display: flex; flex-wrap: wrap; gap: 1rem; align-items: flex-end; }
.subscribe button{
  font-family: var(--mono); font-size: .9rem; letter-spacing: .08em; text-transform: uppercase;
  background: var(--ink); color: var(--paper); border: 1px solid var(--ink);
  padding: .8rem 1.4rem; cursor: pointer;
}
.subscribe button:hover{ background: var(--accent); border-color: var(--accent); }
.subscribe .success{ font-family: var(--sans); color: var(--accent); }

@container (min-width: 560px){
  .subscribe{ grid-template-columns: 1fr 1fr; }
}

/* ===== Подвал ===== */
.site-footer{
  border-top: 1px solid var(--rule-strong);
  padding: 2rem var(--gutter);
}
.footer-inner{ max-width: var(--max); margin: 0 auto; }
.footer-meta{
  display: flex; flex-wrap: wrap; gap: 1rem 2rem;
  font-family: var(--mono); font-size: .8rem; color: var(--ink-2);
}
.footer-meta .issn{ color: var(--ink); }

/* ===== Декоративные формы (в пределах вьюпорта) ===== */
.deco-rule{
  position: relative;
  height: 1px;
  background: var(--rule);
  margin: 1.5rem 0;
}
.deco-rule::before{
  content: ""; position: absolute; left: 0; top: 0; height: 100%; width: 30%;
  background: var(--accent);
}

/* ===== Адаптив под 480px ===== */
@media (max-width: 480px){
  body{ font-size: 16px; }
  .formula{ white-space: normal; }
  .badge, .tag, button{ white-space: normal; }
  .cover .kicker{ letter-spacing: .1em; }
}

/* ===== prefers-reduced-motion ===== */
@media (prefers-reduced-motion: reduce){
  html{ scroll-behavior: auto; }
  .progress span{ transition: none; }
  *{ scroll-behavior: auto !important; }
}
</style>
</head>
<body>

<div class="progress" aria-hidden="true"><span id="progress-bar"></span></div>

<header class="masthead">
  <div class="mast-top">
    <span class="brand">АРХИВ ТЕХНОЛОГИЙ</span>
    <span>Инженерный альманах</span>
    <span>ISSN 2711-4028</span>
    <span class="issue">Выпуск №14 · 12 июня 2025</span>
  </div>
</header>

<header class="cover" id="cover">
  <div class="lead">
    <p class="kicker">Спецвыпуск · Литография</p>
    <h1>Экстремальная ультрафиолетовая литография (EUV 13.5 нм): оптика Цейсса, оловянная плазма и предел кремниевых транзисторов</h1>
    <p>Как отражательный тракт, многослойные зеркала Брэгга и числовая апертура 0.55 удерживают производство на переднем крае — и где физика материалов накладывает потолок, который нельзя пробить одной лишь оптикой.</p>
  </div>
  <nav class="toc" aria-label="Оглавление выпуска">
    <h2>Оглавление</h2>
    <ol>
      <li><a href="#longread">Многоколоночный лонгрид: тракт EUV</a></li>
      <li><a href="#scheme">Схема оптического тракта EUV-сканера</a></li>
      <li><a href="#table">Сравнение поколений литографии</a></li>
      <li><a href="#calc">Калькулятор критерия Рэлея</a></li>
      <li><a href="#faq">FAQ: физика EUV и производства</a></li>
      <li><a href="#subscribe">Подписка и корпоративный дайджест</a></li>
    </ol>
  </nav>
</header>

<main>

  <!-- 1. Лонгрид -->
  <section id="longread" aria-labelledby="longread-h">
    <div class="section-head">
      <span class="num">§ 01</span>
      <h2 id="longread-h">Тракт EUV: от капли олова до маски</h2>
      <span class="dek">Пять отражений, одна длина волны и цена светосилы.</span>
    </div>
    <article class="article" aria-label="Лонгрид об оптическом тракте EUV">
      <p>Экстремальная ультрафиолетовая литография работает на длине волны 13.5 нм — в диапазоне, где стекло, кварц и даже воздух перестают быть прозрачными. Это не деталь конструкции, а фундаментальное ограничение: преломляющая оптика здесь невозможна, и весь тракт построен на отражении. Каждое зеркало — многослойная структура, а не просто полированная поверхность, и каждое отражение стоит потерь.</p>
      <p>Источник света — лазерно-произведённая плазма. Капли олова диаметром около 30 мкм выпускаются с частотой порядка 50 кГц и дважды облучаются CO₂-лазером: пред-пульс формирует облако, основной импульс превращает его в плазму. Плазма излучает в окне 13.5 нм, но большая часть энергии теряется. Именно эффективность сбора, а не мощность лазера, определяет светосилу всей системы.</p>
      <aside class="aside-note">
        <span class="label">Маргиналия</span>
        Олово выбрано не за яркость, а за конверсию энергии в EUV и чистый спектр. Альтернативные элементы (литий, ксенон) дают иные компромиссы, но Mo/Si-окно остаётся эталоном.
      </aside>
      <p>Коллекторное зеркало Брэгга собирает излучение плазмы. Это многослойная структура Mo/Si — чередование молибдена и кремния, около 40–50 пар слоёв. Отражение одного слоя ничтожно, но сумма десятков слоёв даёт отражательную способность порядка 60–70 % — максимум, доступный для этой длины волны. Ни один материал в этом диапазоне не отражает больше.</p>
      <div class="formula">CD = k1 · λ / NA &nbsp;·&nbsp; DOF = k2 · λ / NA²</div>
      <p>Дальше свет уходит на маску-ретикл — тоже отражательную, тоже многослойную. От неё излучение идёт через проекционную оптику: шесть зеркал для Low-NA 0.33, больше зеркал и сложная геометрия для High-NA 0.55. Оптику поставляет Carl Zeiss, и именно её точность — определяющий фактор разрешения.</p>
      <p class="pullquote">«На 13.5 нм оптика — это не линзы, а многослойные зеркала, и каждое отражение стоит потерь энергии.»</p>
      <p>Числовая апертура (NA) задаёт разрешающую способность по критерию Рэлея. Чем больше NA, тем меньше минимальный размер элемента при той же длине волны. Low-NA 0.33 даёт около 13 нм разрешения, High-NA 0.55 — около 8 нм, но одновременно вдвое меньшую глубину резкости. Это более строгие допуски по фокусу, более сложная оптика и более дорогое оборудование.</p>
      <aside class="aside-note">
        <span class="label">Маргиналия</span>
        High-NA позволяет перейти от SAQP (четырёхкратного маскирования) к SAOP, сокращая число масок и удерживая стоимость производства в разумных пределах.
      </aside>
      <p>Предел — не только литография. При уменьшении канала растёт утечка через диэлектрик, а минимальный размер элемента упирается в дифракционный предел. Дальнейшее уменьшение требует новых материалов: высоко-k диэлектриков, новых структур канала, GAA-транзисторов, а в перспективе — CFET и 2D-материалов. Литография — инструмент, но физика материалов накладывает собственный потолок.</p>
      <div class="deco-rule" aria-hidden="true"></div>
    </article>
  </section>

  <!-- 2. Схема -->
  <section id="scheme" aria-labelledby="scheme-h">
    <div class="section-head">
      <span class="num">§ 02</span>
      <h2 id="scheme-h">Оптический тракт EUV-сканера</h2>
      <span class="dek">От капли олова до пластины: пять отражений.</span>
    </div>
    <figure>
      <svg viewBox="0 0 1200 420" role="img" aria-labelledby="scheme-title scheme-desc" preserveAspectRatio="xMidYMid meet">
        <title id="scheme-title">Схема оптического тракта EUV-сканера</title>
        <desc id="scheme-desc">Источник оловянной плазмы, коллекторное зеркало Брэгга Mo/Si, маска-ретикл, проекционная оптика High-NA 0.55 и пластина.</desc>
        <style>
          .lbl{ font-family: var(--mono); font-size: 14px; fill: var(--ink-2); }
          .lbl-strong{ fill: var(--ink); font-weight: 700; }
          .accent{ fill: var(--accent); }
          .line{ stroke: var(--rule-strong); stroke-width: 1; }
          .beam{ stroke: var(--accent); stroke-width: 2; fill: none; }
          .mirror{ fill: var(--paper-2); stroke: var(--rule-strong); stroke-width: 1; }
        </style>
        <!-- Источник: капля олова + CO2 -->
        <g>
          <rect x="40" y="150" width="120" height="90" class="mirror" rx="4"/>
          <circle cx="100" cy="195" r="6" class="accent"/>
          <circle cx="100" cy="195" r="10" fill="none" class="beam"/>
          <text x="40" y="140" class="lbl lbl-strong">Источник LPP</text>
          <text x="40" y="262" class="lbl">Олово · 50 кГц · CO₂</text>
        </g>
        <!-- Коллекторное зеркало Брэгга -->
        <g>
          <path d="M200 200 L210 200 L230 210 L230 200 L240 210 L240 200" class="mirror" stroke-width="1"/>
          <polygon points="230,200 260,210 260,200 290,210 290,200" class="mirror"/>
          <text x="230" y="190" class="lbl lbl-strong">Коллектор Брэгга</text>
          <text x="230" y="262" class="lbl">Mo/Si · 40–50 пар</text>
        </g>
        <!-- Маска-ретикл -->
        <g>
          <rect x="430" y="150" width="140" height="90" class="mirror" rx="2"/>
          <rect x="445" y="165" width="18" height="18" class="accent"/>
          <rect x="470" y="165" width="18" height="18" class="accent"/>
          <rect x="495" y="165" width="18" height="18" class="accent"/>
          <text x="430" y="140" class="lbl lbl-strong">Маска-ретикл</text>
          <text x="430" y="262" class="lbl">Отражательная Mo/Si</text>
        </g>
        <!-- Проекционная оптика -->
        <g>
          <polygon points="620,160 650,180 680,200 710,220 740,240" class="mirror"/>
          <polygon points="740,240 770,250 800,260" class="mirror"/>
          <text x="620" y="150" class="lbl lbl-strong">Проекция High-NA 0.55</text>
          <text x="620" y="262" class="lbl">6+ зеркал · Zeiss</text>
        </g>
        <!-- Пластина -->
        <g>
          <rect x="900" y="180" width="180" height="60" class="mirror" rx="2"/>
          <rect x="915" y="195" width="14" height="14" class="accent"/>
          <rect x="940" y="195" width="14" height="14" class="accent"/>
          <rect x="965" y="195" width="14" height="14" class="accent"/>
          <text x="900" y="170" class="lbl lbl-strong">Пластина</text>
          <text x="900" y="262" class="lbl">Критический размер ~8 нм</text>
        </g>
        <!-- Лучи -->
        <polyline points="120,195 200,200 290,205 430,205 620,205 740,240 900,205" class="beam"/>
        <polyline points="120,180 200,190 290,195 430,195 620,195 740,230 900,190" class="beam" opacity="0.5"/>
      </svg>
      <figcaption class="formula">Тракт: плазма → коллектор Брэгга → маска → проекция → пластина. Все элементы отражательные.</figcaption>
    </figure>
  </section>

  <!-- 3. Таблица -->
  <section id="table" aria-labelledby="table-h">
    <div class="section-head">
      <span class="num">§ 03</span>
      <h2 id="table-h">Поколения литографии</h2>
      <span class="dek">Три процесса: разрешение, плотность, маски.</span>
    </div>
    <div class="table-wrap">
      <table>
        <caption>Сравнение поколений литографических сканеров (усреднённые производственные данные)</caption>
        <thead>
          <tr>
            <th scope="col">Поколение</th>
            <th scope="col">Длина волны</th>
            <th scope="col">NA</th>
            <th scope="col">Разрешение</th>
            <th scope="col">Плотность транзисторов</th>
            <th scope="col">Число масок</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">DUV ArFi 193 нм (иммерсион)</th>
            <td class="num">193 нм</td>
            <td class="num">1.35</td>
            <td class="num">~38 нм</td>
            <td class="num">~190 млн/мм²</td>
            <td class="num">40–60</td>
          </tr>
          <tr>
            <th scope="row">EUV Low-NA 13.5 нм</th>
            <td class="num">13.5 нм</td>
            <td class="num">0.33</td>
            <td class="num">~13 нм</td>
            <td class="num">~300 млн/мм²</td>
            <td class="num">35–50</td>
          </tr>
          <tr>
            <th scope="row">EUV High-NA 13.5 нм</th>
            <td class="num">13.5 нм</td>
            <td class="num">0.55</td>
            <td class="num">~8 нм</td>
            <td class="num">~500 млн/мм²</td>
            <td class="num">25–35</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <!-- 4. Калькулятор -->
  <section id="calc" aria-labelledby="calc-h">
    <div class="section-head">
      <span class="num">§ 04</span>
      <h2 id="calc-h">Калькулятор критерия Рэлея</h2>
      <span class="dek">CD = k1 · λ / NA и DOF = k2 · λ / NA²</span>
    </div>
    <div class="calc">
      <div class="calc-controls">
        <div class="calc-field">
          <label for="na">Числовая апертура (NA)</label>
          <input type="range" id="na" min="0.1" max="1.35" step="0.01" value="0.55">
          <span class="val" id="na-val">0.55</span>
        </div>
        <div class="calc-field">
          <label for="lambda">Длина волны (λ, нм)</label>
          <input type="range" id="lambda" min="13.5" max="193" step="1" value="13.5">
          <span class="val" id="lambda-val">13.5 нм</span>
        </div>
        <div class="calc-field">
          <label for="k1">Фактор k1</label>
          <input type="range" id="k1" min="0.25" max="1" step="0.01" value="0.25">
          <span class="val" id="k1-val">0.25</span>
        </div>
        <div class="calc-field">
          <label for="k2">Фактор k2</label>
          <input type="range" id="k2" min="0.25" max="1" step="0.01" value="0.20">
          <span class="val" id="k2-val">0.20</span>
        </div>
      </div>
      <div class="calc-readout" aria-live="polite">
        <div class="stat"><span>CD (крит. размер)</span><b id="cd-out">—</b></div>
        <div class="stat"><span>DOF (глубина резкости)</span><b id="dof-out">—</b></div>
        <div class="stat"><span>k1 / NA</span><b id="ratio-out">—</b></div>
      </div>
      <div class="calc-svg">
        <svg id="beam-svg" viewBox="0 0 600 240" role="img" aria-labelledby="beam-title beam-desc">
          <title id="beam-title">Профиль пучка</title>
          <desc id="beam-desc">SVG-профиль пучка перестраивается по NA, длине волны и факторам k1/k2.</desc>
          <style>
            .beam-fill{ fill: var(--accent); opacity: 0.35; }
            .beam-outline{ stroke: var(--accent); stroke-width: 2; fill: none; }
            .axis{ stroke: var(--rule-strong); stroke-width: 1; }
            .axis-label{ font-family: var(--mono); font-size: 12px; fill: var(--ink-2); }
          </style>
          <line class="axis" x1="40" y1="20" x2="40" y2="220"/>
          <line class="axis" x1="40" y1="220" x2="560" y2="220"/>
          <text class="axis-label" x="44" y="232">λ / NA</text>
          <polygon id="beam-profile" class="beam-fill" points="60,40 120,40 180,60 240,90 300,120 360,150 420,180 480,200 540,210 560,210 560,210 60,40"/>
          <polyline id="beam-line" class="beam-outline" points="60,40 120,40 180,60 240,90 300,120 360,150 420,180 480,200 540,210 560,210"/>
        </svg>
      </div>
    </div>
  </section>

  <!-- 5. FAQ -->
  <section id="faq" aria-labelledby="faq-h">
    <div class="section-head">
      <span class="