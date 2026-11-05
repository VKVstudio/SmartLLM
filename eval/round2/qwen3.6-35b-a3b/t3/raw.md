

FILE: index.html
```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Северная Мануфактура — Мебель из массива дуба</title>
<meta name="description" content="Бoutique-производство обеденных столов, шкафов и архитектурной столярки из массива дуба. Ручная работа, FSC, ГОСТ. Проектирование и монтаж по России.">
<link rel="canonical" href="https://example.com/">
<meta property="og:title" content="Северная Мануфактура — Мебель из массива дуба">
<meta property="og:description" content="Бoutique-производство обеденных столов, шкафов и архитектурной столярки из массива дуба. Ручная работа, FSC, ГОСТ.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://example.com/">
<meta property="og:image" content="https://example.com/og-image.jpg">
<meta name="robots" content="index, follow">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeR+/5FIPuQUmRBMd8='; script-src 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeR+/5FIPuQUmRBMd8='; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';">
<style>
:root{--bg:oklch(0.95 0.01 85);--text:oklch(0.25 0.02 85);--accent:oklch(0.65 0.08 85);--surface:oklch(0.90 0.01 85);--border:oklch(0.80 0.01 85);--font-serif:"Playfair Display","Cormorant Garamond",Georgia,serif;--font-sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;--space:clamp(4rem,10vw,12rem)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font-sans);color:var(--text);background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased}
h1,h2,h3{font-family:var(--font-serif);font-weight:400;line-height:1.2;margin-bottom:1rem}
h1{font-size:clamp(2.5rem,5vw,4.5rem)}
h2{font-size:clamp(1.8rem,3vw,2.5rem);margin-bottom:2rem}
section{padding:var(--space) clamp(1.5rem,5vw,4rem)}
.container{max-width:1200px;margin:0 auto}
.btn{display:inline-block;padding:1rem 2rem;background:var(--accent);color:#fff;text-decoration:none;border-radius:2px;font-weight:500;transition:opacity .2s}
.btn:focus-visible{outline:3px solid var(--text);outline-offset:4px}
table{width:100%;border-collapse:collapse;margin-top:2rem}
th,td{text-align:left;padding:1rem;border-bottom:1px solid var(--border)}
th{font-family:var(--font-serif);font-weight:400;letter-spacing:0.05em;text-transform:uppercase;font-size:0.9rem}
.svg-wrap{aspect-ratio:16/9;max-width:800px;margin:2rem auto;background:var(--surface);padding:2rem;border:1px solid var(--border)}
.faq-item{border-bottom:1px solid var(--border);padding:1.5rem 0}
.faq-q{font-family:var(--font-serif);font-size:1.2rem;margin-bottom:0.5rem;cursor:pointer;list-style:none}
.faq-a{display:none;padding-top:1rem}
.faq-item.open .faq-a{display:block}
.faq-item.open .faq-q::after{content:"−"}
.faq-q::after{content:"+";float:right}
form{display:grid;gap:1.5rem;max-width:600px}
label{display:block;margin-bottom:0.5rem;font-size:0.9rem}
input,textarea{width:100%;padding:1rem;border:1px solid var(--border);background:var(--surface);font-family:var(--font-sans);font-size:1rem}
input:focus,textarea:focus{outline:2px solid var(--accent);border-color:transparent}
.error{color:#c00;font-size:0.85rem;display:none}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
<script>
document.querySelectorAll('.faq-q').forEach(q=>{q.addEventListener('click',()=>{q.parentElement.classList.toggle('open')})});
document.getElementById('contact-form').addEventListener('submit',e=>{e.preventDefault();const name=document.getElementById('name');const email=document.getElementById('email');const msg=document.getElementById('message');let valid=true;[name,email,msg].forEach(f=>{const err=document.getElementById(f.id+'-err');if(!f.value.trim()){f.style.borderColor='#c00';err.style.display='block';valid=false}else{f.style.borderColor='var(--border)';err.style.display='none'}});if(!email.value.includes('@')){email.style.borderColor='#c00';document.getElementById('email-err').style.display='block';valid=false}if(valid)alert('Заявка отправлена. Мы свяжемся с вами в ближайшее время.');});
</script>
</head>
<body>
<header class="container" style="padding:2rem clamp(1.5rem,5vw,4rem);display:flex;justify-content:space-between;align-items:center;">
  <div style="font-family:var(--font-serif);font-size:1.5rem;letter-spacing:0.05em;">Северная Мануфактура</div>
  <nav aria-label="Основная навигация">
    <a href="#products" style="margin-left:2rem;text-decoration:none;color:var(--text);">Коллекция</a>
    <a href="#joinery" style="margin-left:2rem;text-decoration:none;color:var(--text);">Технология</a>
    <a href="#contact" style="margin-left:2rem;text-decoration:none;color:var(--text);">Контакты</a>
  </nav>
</header>
<main>
  <section id="hero" aria-labelledby="hero-title">
    <div class="container">
      <h1 id="hero-title">Массив дуба. Ручная работа. Вечная геометрия.</h1>
      <p style="max-width:600px;margin:1.5rem 0;font-size:1.1rem;">Создаём обеденные столы, шкафы и архитектурную столярку для пространств, где ценят тактильность и долговечность.</p>
      <a href="#contact" class="btn">Обсудить проект</a>
    </div>
  </section>

  <section id="products" aria-labelledby="prod-title">
    <div class="container">
      <h2 id="prod-title">Флагманские модели</h2>
      <table role="table" aria-label="Технические характеристики моделей">
        <thead><tr><th scope="col">Модель</th><th scope="col">Назначение</th><th scope="col">Материал / Обработка</th><th scope="col">Габариты (Д×Ш×В), мм</th></tr></thead>
        <tbody>
          <tr><td><strong>Скандия</strong></td><td>Обеденный стол</td><td>Дуб массив, масло Osmo 3K</td><td>2400 × 900 × 750</td></tr>
          <tr><td><strong>Архитектор</strong></td><td>Шкаф-витрина</td><td>Дуб массив, лак на водной основе</td><td>1800 × 450 × 2200</td></tr>
          <tr><td><strong>Мануфактура</strong></td><td>Стеновая панель / Балясины</td><td>Дуб массив, восковая пропитка</td><td>По проекту</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section id="joinery" aria-labelledby="join-title">
    <div class="container">
      <h2 id="join-title">Соединение шип-паз и ласточкин хвост</h2>
      <div class="svg-wrap" role="img" aria-label="Схема соединения шип-паз и ласточкин хвост">
        <svg viewBox="0 0 800 450" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="0" y="0" width="800" height="450" fill="none"/>
          <g stroke="var(--text)" stroke-width="2" fill="none">
            <path d="M100,150 L300,150 L300,250 L100,250 Z" />
            <path d="M300,180 L450,180 L450,220 L300,220 Z" />
            <path d="M450,150 L650,150 L650,250 L450,250 Z" />
            <path d="M300,150 L320,180 L320,220 L300,250" />
            <path d="M450,150 L470,180 L470,220 L450,250" />
            <path d="M300,180 L340,180 L340,220 L300,220" />
            <path d="M450,180 L490,180 L490,220 L450,220" />
            <line x1="100" y1="150" x2="100" y2="250" stroke-dasharray="4"/>
            <line x1="650" y1="150" x2="650" y2="250" stroke-dasharray="4"/>
            <text x="200" y="130" font-family="var(--font-sans)" font-size="14" fill="var(--text)">Шип</text>
            <text x="550" y="130" font-family="var(--font-sans)" font-size="14" fill="var(--text)">Паз</text>
            <text x="370" y="270" font-family="var(--font-sans)" font-size="14" fill="var(--text)">Ласточкин хвост</text>
          </g>
        </svg>
      </div>
    </div>
  </section>

  <section id="certifications" aria-labelledby="cert-title">
    <div class="container">
      <h2 id="cert-title">Сертификация</h2>
      <p style="max-width:700px;margin-bottom:1.5rem;">Вся древесина проходит контроль происхождения и обработки. Соответствуем международным и российским стандартам.</p>
      <div style="display:flex;gap:2rem;flex-wrap:wrap;">
        <div style="padding:1.5rem;border:1px solid var(--border);background:var(--surface);min-width:200px;">
          <h3 style="margin-bottom:0.5rem;">FSC®</h3>
          <p>Ответственное лесопользование. Цепочка поставок верифицирована.</p>
        </div>
        <div style="padding:1.5rem;border:1px solid var(--border);background:var(--surface);min-width:200px;">
          <h3 style="margin-bottom:0.5rem;">ГОСТ 30974-2014</h3>
          <p>Мебель из древесины. Общие технические условия. Контроль качества на каждом этапе.</p>
        </div>
      </div>
    </div>
  </section>

  <section id="faq" aria-labelledby="faq-title">
    <div class="container">
      <h2 id="faq-title">Вопросы и ответы</h2>
      <div role="list">
        <div class="faq-item" role="listitem">
          <h3 class="faq-q" tabindex="0" role="button" aria-expanded="false">Как ухаживать за дубовой мебелью?</h3>
          <div class="faq-a" role="region">Регулярно протирайте мягкой сухой тканью. Раз в полгода обрабатывайте поверхность воском или маслом, рекомендованным производителем. Избегайте абразивных средств и длительного воздействия прямых солнечных лучей.</div>
        </div>
        <div class="faq-item" role="listitem">
          <h3 class="faq-q" tabindex="0" role="button" aria-expanded="false">Сколько времени занимает изготовление?</h3>
          <div class="faq-a" role="region">Стандартные модели — 4–6 недель. Проекты архитектурной столярки и нестандартные габариты — от 8 до 12 недель в зависимости от сложности и загрузки мастерской.</div>
        </div>
        <div class="faq-item" role="listitem">
          <h3 class="faq-q" tabindex="0" role="button" aria-expanded="false">Можно ли заказать реставрацию?</h3>
          <div class="faq-a" role="region">Да, мы принимаем на реставрацию изделия любой столярной мастерской. Выполняем шлифовку, замену элементов, обновление покрытия с сохранением текстуры и патины.</div>
        </div>
        <div class="faq-item" role="listitem">
          <h3 class="faq-q" tabindex="0" role="button" aria-expanded="false">Доставляете ли вы в регионы?</h3>
          <div class="faq-a" role="region">Да. Доставка осуществляется специализированным транспортом с мягкой фиксацией. В стоимость входит страховка, разгрузка и подъем на этаж. Монтаж выполняем по всей территории России.</div>
        </div>
        <div class="faq-item" role="listitem">
          <h3 class="faq-q" tabindex="0" role="button" aria-expanded="false">Какие гарантии предоставляются?</h3>
          <div class="faq-a" role="region">5 лет на конструктивные элементы и соединения, 2 года на покрытия. Гарантия покрывает производственные дефекты, усушку и коробление при соблюдении условий эксплуатации.</div>
        </div>
      </div>
    </div>
  </section>

  <section id="contact" aria-labelledby="contact-title">
    <div class="container">
      <h2 id="contact-title">Связаться с мастерской</h2>
      <form id="contact-form" novalidate>
        <label for="name">Имя</label>
        <input type="text" id="name" name="name" required autocomplete="name">
        <div id="name-err" class="error" role="alert">Укажите имя</div>

        <label for="email">Электронная почта</label>
        <input type="email" id="email" name="email" required autocomplete="email">
        <div id="email-err" class="error" role="alert">Укажите корректный email</div>

        <label for="message">Сообщение / Параметры проекта</label>
        <textarea id="message" name="message" rows="5" required></textarea>
        <div id="message-err" class="error" role="alert">Введите сообщение</div>

        <button type="submit" class="btn">Отправить заявку</button>
      </form>
    </div>
  </section>
</main>

<footer style="padding:3rem clamp(1.5rem,5vw,4rem);border-top:1px solid var(--border);margin-top:var(--space);">
  <div class="container" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:2rem;">
    <div>
      <strong>Северная Мануфактура</strong><br>
      Санкт-Петербург, ул. Столярная, 12<br>
      info@northern-manufactory.ru
    </div>
    <div>
      <a href="#products" style="color:var(--text);text-decoration:none;margin-right:1.5rem;">Коллекция</a>
      <a href="#joinery" style="color:var(--text);text-decoration:none;margin-right:1.5rem;">Технология</a>
      <a href="#contact" style="color:var(--text);text-decoration:none;">Контакты</a>
    </div>
  </div>
  <div style="text-align:center;margin-top:2rem;font-size:0.85rem;opacity:0.8;">© 2024 Северная Мануфактура. Все права защищены.</div>
</footer>

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://example.com/#organization",
      "name": "Северная Мануфактура",
      "url": "https://example.com/",
      "logo": "https://example.com/logo.png",
      "contactPoint": {
        "@type": "ContactPoint",
        "telephone": "+7-812-000-00-00",
        "contactType": "customer service",
        "email": "info@northern-manufactory.ru"
      },
      "address": {
        "@type": "PostalAddress",
        "streetAddress": "ул. Столярная, 12",
        "addressLocality": "Санкт-Петербург",
        "addressCountry": "RU"
      }
    },
    {
      "@type": "BreadcrumbList",
      "@id": "https://example.com/#breadcrumb",
      "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Главная", "item": "https://example.com/"},
        {"@type": "ListItem", "position": 2, "name": "Коллекция", "item": "https://example.com/#products"},
        {"@type": "ListItem", "position": 3, "name": "Контакты", "item": "https://example.com/#contact"}
      ]
    },
    {
      "@type": "Product",
      "name": "Скандия",
      "description": "Обеденный стол из массива дуба с маслом Osmo 3K.",
      "brand": {"@type": "Brand", "name": "Северная Мануфактура"},
      "sku": "SKAND-2400",
      "offers": {"@type": "Offer", "priceCurrency": "RUB", "availability": "https://schema.org/InStock"}
    },
    {
      "@type": "Product",
      "name": "Архитектор",
      "description": "Шкаф-витрина из массива дуба с водным лаком.",
      "brand": {"@type": "Brand", "name": "Северная Мануфактура"},
      "sku": "ARCH-1800",
      "offers": {"@type": "Offer", "priceCurrency": "RUB", "availability": "https://schema.org/InStock"}
    },
    {
      "@type": "Product",
      "name": "Мануфактура",
      "description": "Стеновая панель и балясины из массива дуба.",
      "brand": {"@type": "Brand", "name": "Северная Мануфактура"},
      "sku": "MANU-CUSTOM",
      "offers": {"@type": "Offer", "priceCurrency": "RUB", "availability": "https://schema.org/InStock"}
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {"@type": "Question", "name": "Как ухаживать за дубовой мебелью?", "acceptedAnswer": {"@type": "Answer", "text": "Регулярно протирайте мягкой сухой тканью. Раз в полгода обрабатывайте поверхность воском или маслом, рекомендованным производителем. Избегайте абразивных средств и длительного воздействия прямых солнечных лучей."}},
        {"@type": "Question", "name": "Сколько времени занимает изготовление?", "acceptedAnswer": {"@type": "Answer", "text": "Стандартные модели — 4–6 недель. Проекты архитектурной столярки и нестандартные габариты — от 8 до 12 недель в зависимости от сложности и загрузки мастерской."}},
        {"@type": "Question", "name": "Можно ли заказать реставрацию?", "acceptedAnswer": {"@type": "Answer", "text": "Да, мы принимаем на реставрацию изделия любой столярной мастерской. Выполняем шлифовку, замену элементов, обновление покрытия с сохранением текстуры и патины."}},
        {"@type": "Question", "name": "Доставляете ли вы в регионы?", "acceptedAnswer": {"@type": "Answer", "text": "Да. Доставка осуществляется специализированным транспортом с мягкой фиксацией. В стоимость входит страховка, разгрузка и подъем на этаж. Монтаж выполняем по всей территории России."}},
        {"@type": "Question", "name": "Какие гарантии предоставляются?", "acceptedAnswer": {"@type": "Answer", "text": "5 лет на конструктивные элементы и соединения, 2 года на покрытия. Гарантия покрывает производственные дефекты, усушку и коробление при соблюдении условий эксплуатации."}}
      ]
    }
  ]
}
</script>
</body>
</html>
```

FILE: llms.txt
```
# LLMs.txt for Северная Мануфактура
# Per llmstxt.org specification

## Organization
Северная Мануфактура — boutique-производитель мебели из массива дуба. 
Локация: Санкт-Петербург, Россия.
Специализация: обеденные столы, шкафы-витрины, архитектурная столярка.
Стандарты: FSC, ГОСТ 30974-2014.

## Products
1. Скандия — обеденный стол. Массив дуба, масло Osmo 3K. 2400×900×750 мм.
2. Архитектор — шкаф-витрина. Массив дуба, водный лак. 1800×450×2200 мм.
3. Мануфактура — стеновые панели, балясины. Массив дуба, восковая пропитка. По проекту.

## Services
- Проектирование и 3D-визуализация.
- Производство в мастерской.
- Доставка и профессиональный монтаж по России.
- Реставрация и обслуживание дубовой мебели.

## Contact
Email: info@northern-manufactory.ru
Phone: +7-812-000-00-00
Address: ул. Столярная, 12, Санкт-Петербург, Россия.

## Content Policy
Все материалы защищены авторским правом. Копирование текста, схем и изображений без письменного разрешения запрещено.
```

FILE: robots.txt
```
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /private/
Disallow: /tmp/

Sitemap: https://example.com/sitemap.xml
```

FILE: _headers
```
/*
  Content-Security-Policy: default-src 'self'; style-src 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeR+/5FIPuQUmRBMd8='; script-src 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeR+/5FIPuQUmRBMd8='; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin
```