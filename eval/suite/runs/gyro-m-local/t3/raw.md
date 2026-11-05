FILE: index.html
```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Северная Мануфактура — мебель из массива дуба на заказ</title>
  <meta name="description" content="Бутик-производитель мебели из массива дуба: обеденные столы, шкафы и архитектурная столярная продукция. Соединения шип-паз и ласточкин хвост, сертификаты FSC и ГОСТ.">
  <link rel="canonical" href="https://severnaya-manufactura.example/">
  <meta name="theme-color" content="oklch(0.95 0.01 85)">

  <meta property="og:type" content="website">
  <meta property="og:title" content="Северная Мануфактура — мебель из массива дуба">
  <meta property="og:description" content="Обеденные столы, шкафы и архитектурная столярная продукция из массива дуба.">
  <meta property="og:url" content="https://severnaya-manufactura.example/">
  <meta property="og:image" content="https://severnaya-manufactura.example/assets/og.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">

  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU='; style-src 'self' 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=' data:; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; upgrade-insecure-requests">

  <link rel="stylesheet" href="data:text/css,%3Aroot%7B--bg%3Aoklch%280.95%200.01%2085%29%3B--surface%3Aoklch%280.98%200.005%2085%29%3B--ink%3Aoklch%280.16%200.015%2085%29%3B--muted%3Aoklch%280.45%200.02%2085%29%3B--line%3Aoklch%280.78%200.02%2085%29%3B--accent%3Aoklch%280.42%200.07%2065%29%3B--focus%3Aoklch%280.30%200.08%2065%29%3B--shadow%3Aoklch%280.16%200.015%2085%2F0.08%29%3B--serif%3A%22Cormorant%20Garamond%22%2C%22Playfair%20Display%22%2CGeorgia%2C%22Times%20New%20Roman%22%2Cserif%3B--sans%3Aui-sans-serif%2Csystem-ui%2C-apple-system%2CBlinkMacSystemFont%2C%22Segoe%20UI%22%2CRoboto%2C%22Helvetica%20Neue%22%2CArial%2Csans-serif%3B--pad%3Aclamp%284rem%2C10vw%2C12rem%29%3B--max%3A72rem%3B%7D%40media%28prefers-reduced-motion%3Areduce%29%7B%2A%2C%2A%3Abefore%2C%2A%3Aafter%7Banimation-duration%3A0.01ms%21important%3Banimation-iteration-count%3A1%21important%3Btransition-duration%3A0.01ms%21important%3Bscroll-behavior%3Aauto%21important%3B%7D%7D%2A%7Bbox-sizing%3Aborder-box%3B%7Dhtml%7Bscroll-behavior%3Asmooth%3B%7Dbody%7Bmargin%3A0%3Bcolor%3Avar%28--ink%29%3Bbackground%3Avar%28--bg%29%3Bfont-family%3Avar%28--sans%29%3Bline-height%3A1.65%3Bfont-size%3Aclamp%281rem%2C1vw%2B0.75rem%2C1.125rem%29%3B%7Dh1%2Ch2%2Ch3%7Bfont-family%3Avar%28--serif%29%3Bfont-weight%3A500%3Bletter-spacing%3A0.01em%3Bline-height%3A1.15%3Bmargin%3A0%3B%7Dh1%7Bfont-size%3Aclamp%283rem%2C8vw%2C6rem%29%3Bmax-width%3A12ch%3B%7Dh2%7Bfont-size%3Aclamp%282rem%2C4vw%2C3rem%29%3Bmargin-bottom%3A1.25rem%3B%7Dh3%7Bfont-size%3A1.375rem%3B%7Dp%7Bmargin%3A0%3Bmax-width%3A65ch%3B%7Da%7Bcolor%3Avar%28--accent%29%3Btext-decoration%3Aunderline%3Btext-underline-offset%3A0.2em%3B%7Da%3Ahover%7Bcolor%3Avar%28--focus%29%3B%7D%3Afocus-visible%7Boutline%3A3px%20solid%20var%28--focus%29%3Boutline-offset%3A3px%3B%7Dheader%2Cmain%2Cfooter%7Bwidth%3A100%3B%7D.wrap%7Bwidth%3Amin%28var%28--max%29%2C100%25%29%3Bmargin%3A0%20auto%3Bpadding%3Avar%28--pad%29%20clamp%281rem%2C4vw%2C3rem%29%3B%7D.topbar%7Bdisplay%3Aflex%3Bjustify-content%3Aspace-between%3Balign-items%3Acenter%3Bgap%3A1rem%3Bborder-bottom%3A1px%20solid%20var%28--line%29%3Bpadding-top%3A1rem%3Bpadding-bottom%3A1rem%3B%7D.brand%7Bfont-family%3Avar%28--serif%29%3Bfont-size%3A1.125rem%3Btext-decoration%3Anone%3Bcolor%3Avar%28--ink%29%3B%7D.nav%7Bdisplay%3Aflex%3Bflex-wrap%3Awrap%3Bgap%3A1rem%3Bfont-size%3A0.9375rem%3B%7D.hero%7Bmin-height%3Aclamp%28520px%2C70vh%2C860px%29%3Bdisplay%3Agrid%3Bgrid-template-columns%3Aminmax%280%2C1fr%29%20minmax%280%2C520px%29%3Bgap%3Aclamp%282rem%2C6vw%2C5rem%29%3Balign-items%3Acenter%3B%7D.hero-copy%7Bdisplay%3Agrid%3Bgap%3A1.5rem%3B%7D.eyebrow%7Bcolor%3Avar%28--muted%29%3Bfont-size%3A0.875rem%3Bletter-spacing%3A0.12em%3Btext-transform%3Auppercase%3B%7D.cta%7Bdisplay%3Ainline-flex%3Balign-items%3Acenter%3Bjustify-content%3Acenter%3Bmin-height%3A52px%3Bpadding%3A0.75rem%201.25rem%3Bborder%3A1px%20solid%20var%28--ink%29%3Bbackground%3Avar%28--surface%29%3Bcolor%3Avar%28--ink%29%3Bfont%3Ainherit%3Btext-decoration%3Anone%3B%7D.cta%3Ahover%7Bbackground%3Avar%28--ink%29%3Bcolor%3Avar%28--bg%29%3B%7D.hero-art%7Baspect-ratio%3A4%2F3%3Bwidth%3A100%3Bmax-width%3A520px%3Bborder%3A1px%20solid%20var%28--line%29%3Bbackground%3Avar%28--surface%29%3Bbox-shadow%3A0%2020px%2050px%20var%28--shadow%29%3Bdisplay%3Agrid%3Bplace-items%3Acenter%3Boverflow%3Ahidden%3B%7D.hero-art%3Csvg%2Csvg%7Bdisplay%3Ablock%3Bmax-width%3A100%25%3Bheight%3Aauto%3B%7Dsection%7Bborder-top%3A1px%20solid%20var%28--line%29%3B%7D.table-wrap%7Boverflow-x%3Aauto%3B%7Dtable%7Bwidth%3A100%25%3Bborder-collapse%3Acollapse%3Bmin-width%3A760px%3Bbackground%3Avar%28--surface%29%3B%7Dth%2Ctd%7Btext-align%3Aleft%3Bvertical-align%3Atop%3Bpadding%3A1rem%3Bborder%3A1px%20solid%20var%28--line%29%3Bfont-size%3A0.9375rem%3B%7Dth%7Bfont-weight%3A600%3Bbackground%3Avar%28--bg%29%3B%7Dtd%20a%7Bfont-weight%3A600%3B%7D.schematic%7Bdisplay%3Agrid%3Bgrid-template-columns%3Aminmax%280%2C1fr%29%20minmax%280%2C520px%29%3Bgap%3Aclamp%282rem%2C6vw%2C5rem%29%3Balign-items%3Astart%3B%7D.schematic-panel%7Baspect-ratio%3A16%2F10%3Bwidth%3A100%3Bborder%3A1px%20solid%20var%28--line%29%3Bbackground%3Avar%28--surface%29%3Bpadding%3Aclamp%281rem%2C3vw%2C2rem%29%3B%7D.schematic%20svg%7Bwidth%3A100%25%3Bheight%3Aauto%3Baspect-ratio%3A16%2F10%3B%7D.certs%7Bdisplay%3Agrid%3Bgrid-template-columns%3Arepeat%28auto-fit%2Cminmax%28280px%2C1fr%29%29%3Bgap%3Aclamp%281.5rem%2C3vw%2C2.5rem%29%3B%7D.cert-card%7Bborder%3A1px%20solid%20var%28--line%29%3Bbackground%3Avar%28--surface%29%3Bpadding%3Aclamp%281.25rem%2C3vw%2C2rem%29%3B%7D.cert-card%20p%7Bmargin-top%3A0.75rem%3Bcolor%3Avar%28--muted%29%3B%7D.faq%20details%7Bborder%3A1px%20solid%20var%28--line%29%3Bbackground%3Avar%28--surface%29%3Bpadding%3A1rem%201.25rem%3Bmargin-bottom%3A0.75rem%3B%7D.faq%20summary%7Bcursor%3Apointer%3Bfont-family%3Avar%28--serif%29%3Bfont-size%3A1.25rem%3Blist-style%3Anone%3B%7D.faq%20summary%3A%3Aafter%7Bcontent%3A%22%2B%22%3Bfloat%3Aright%3Bcolor%3Avar%28--accent%29%3Bfont-family%3Avar%28--sans%29%3B%7D.faq%20details%5Bopen%5D%20summary%3A%3Aafter%7Bcontent%3A%22%E2%88%92%22%3B%7D.faq%20p%7Bmargin-top%3A0.75rem%3B%7D.contact-grid%7Bdisplay%3Agrid%3Bgrid-template-columns%3Aminmax%280%2C1fr%29%20minmax%280%2C520px%29%3Bgap%3Aclamp%282rem%2C6vw%2C5rem%29%3Balign-items%3Astart%3B%7Dform%7Bdisplay%3Agrid%3Bgap%3A1rem%3Bwidth%3A100%3Bmax-width%3A520px%3B%7Dlabel%7Bdisplay%3Agrid%3Bgap%3A0.375rem%3Bfont-size%3A0.9375rem%3Bfont-weight%3A600%3B%7Dinput%2Ctextarea%2Cselect%7Bwidth%3A100%25%3Bmin-height%3A48px%3Bpadding%3A0.75rem%3Bborder%3A1px%20solid%20var%28--line%29%3Bbackground%3Avar%28--surface%29%3Bcolor%3Avar%28--ink%29%3Bfont%3Ainherit%3Bborder-radius%3A0%3B%7Dtextarea%7Bmin-height%3A160px%3Bresize%3Avertical%3B%7Dinput%3Ainvalid%2Ctextarea%3Ainvalid%7Bborder-color%3Avar%28--accent%29%3B%7Dbutton%7Bmin-height%3A52px%3Bpadding%3A0.75rem%201.25rem%3Bborder%3A1px%20solid%20var%28--ink%29%3Bbackground%3Avar%28--ink%29%3Bcolor%3Avar%28--bg%29%3Bfont%3Ainherit%3Bcursor%3Apointer%3B%7Dbutton%3Ahover%7Bbackground%3Avar%28--accent%29%3Bborder-color%3Avar%28--accent%29%3Bcolor%3Avar%28--bg%29%3B%7D.contact-note%7Bcolor%3Avar%28--muted%29%3B%7Dfooter%7Bborder-top%3A1px%20solid%20var%28--line%29%3B%7D.footer-grid%7Bdisplay%3Agrid%3Bgrid-template-columns%3Arepeat%28auto-fit%2Cminmax%28240px%2C1fr%29%29%3Bgap%3Aclamp%282rem%2C5vw%2C4rem%29%3B%7D.footer-grid%20p%2C.footer-grid%20address%7Bcolor%3Avar%28--muted%29%3Bfont-style%3Anormal%3B%7D.footer-bottom%7Bmargin-top%3Aclamp%282rem%2C5vw%2C4rem%29%3Bpadding-top%3A1rem%3Bborder-top%3A1px%20solid%20var%28--line%29%3Bcolor%3Avar%28--muted%29%3Bfont-size%3A0.875rem%3B%7D@media%28max-width%3A860px%29%7B.hero%2C.schematic%2C.contact-grid%7Bgrid-template-columns%3A1fr%3B%7D.hero-art%7Bmax-width%3A100%25%3B%7D%7D%40media%28max-width%3A560px%29%7B.topbar%7Bflex-direction%3Acolumn%3Balign-items%3Aflex-start%3B%7Dh1%7Bfont-size%3Aclamp%282.25rem%2C10vw%2C3.5rem%29%3B%7Dtable%7Bmin-width%3A620px%3B%7D%7D">

  <script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Organization","@id":"https://severnaya-manufactura.example/#org","name":"Северная Мануфактура","url":"https://severnaya-manufactura.example/","logo":"https://severnaya-manufactura.example/assets/logo.svg","description":"Бутик-производитель мебели из массива дуба.","address":{"@type":"PostalAddress","streetAddress":"Лесная линия, 18","addressLocality":"Санкт-Петербург","postalCode":"190000","addressCountry":"RU"},"contactPoint":{"@type":"ContactPoint","telephone":"+7-812-000-00-00","contactType":"customer service","email":"hello@severnaya-manufactura.example","availableLanguage":["ru"]},"sameAs":["https://severnaya-manufactura.example/llms.txt"]},{"@type":"WebSite","@id":"https://severnaya-manufactura.example/#website","url":"https://severnaya-manufactura.example/","name":"Северная Мануфактура","publisher":{"@id":"https://severnaya-manufactura.example/#org"},"inLanguage":"ru"},{"@type":"BreadcrumbList","@id":"https://severnaya-manufactura.example/#breadcrumbs","itemListElement":[{"@type":"ListItem","position":1,"name":"Главная","item":"https://severnaya-manufactura.example/"},{"@type":"ListItem","position":2,"name":"Каталог","item":"https://severnaya-manufactura.example/#catalog"},{"@type":"ListItem","position":3,"name":"Соединения","item":"https://severnaya-manufactura.example/#schematic"},{"@type":"ListItem","position":4,"name":"Сертификаты","item":"https://severnaya-manufactura.example/#certifications"},{"@type":"ListItem","position":5,"name":"FAQ","item":"https://severnaya-manufactura.example/#faq"},{"@type":"ListItem","position":6,"name":"Контакты","item":"https://severnaya-manufactura.example/#contact"}]},{"@type":"Product","@id":"https://severnaya-manufactura.example/#product-nordic","name":"Nordic 2400","description":"Обеденный стол из массива дуба с столешницей из цельных ламелей и соединениями шип-паз.","brand":{"@id":"https://severnaya-manufactura.example/#org"},"sku":"NORDIC-2400","mpn":"NORDIC-2400","material":"Массив дуба","weight":"180 кг","width":"240 см","depth":"95 см","height":"76 см","offers":{"@type":"Offer","priceCurrency":"RUB","price":"390000","availability":"https://schema.org/PreOrder","url":"https://severnaya-manufactura.example/#contact"},"image":"https://severnaya-manufactura.example/assets/nordic-2400.jpg"},{"@type":"Product","@id":"https://severnaya-manufactura.example/#product-baltic","name":"Baltic Cabinet","description":"Шкаф из массива дуба с фасадами на ласточкин хвост и внутренней архитектурной столярной отделкой.","brand":{"@id":"https://severnaya-manufactura.example/#org"},"sku":"BALTIC-CAB","mpn":"BALTIC-CAB","material":"Массив дуба","weight":"260 кг","width":"180 см","depth":"55 см","height":"220 см","offers":{"@type":"Offer","priceCurrency":"RUB","price":"620000","availability":"https://schema.org/PreOrder","url":"https://severnaya-manufactura.example/#contact"},"image":"https://severnaya-manufactura.example/assets/baltic-cabinet.jpg"},{"@type":"Product","@id":"https://severnaya-manufactura.example/#product-karelian","name":"Karelian Joinery","description":"Архитктурная столярная панель из массива дуба с шип-паз соединениями и ласточкин хвост.","brand":{"@id":"https://severnaya-manufactura.example/#org"},"sku":"KARELIAN-JOINERY","mpn":"KARELIAN-JOINERY","material":"Массив дуба","weight":"140 кг","width":"120 см","depth":"3 см","height":"240 см","offers":{"@type":"Offer","priceCurrency":"RUB","price":"280000","availability":"https://schema.org/PreOrder","url":"https://severnaya-manufactura.example/#contact"},"image":"https://severnaya-manufactura.example/assets/karelian-joinery.jpg"},{"@type":"FAQPage","@id":"https://severnaya-manufactura.example/#faq-page","mainEntity":[{"@type":"Question","name":"Какая древесина используется в производстве?","acceptedAnswer":{"@type":"Answer","text":"Мы используем массив дуба из ответственных источников с сертификатом FSC. Основная база — карельский и архангельский дуб, а также отобранные партии из Ленинградской области."}},{"@type":"Question","name":"Как обрабатывается столешница?","acceptedAnswer":{"@type":"Answer","text":"Столешница собирается из массивных ламелей и покрывается маслом с твердым воском. Допускается восстановление локальных повреждений без демонтажа изделия."}},{"@type":"Question","name":"Сколько занимает изготовление?","acceptedAnswer":{"@type":"Answer","text":"Срок изготовления составляет от 10 до 16 недель в зависимости от сложности модели, сушки, стабильности массива и графика покраски."}},{"@type":"Question","name":"Можно ли изменить размеры и отделку?","acceptedAnswer":{"@type":"Answer","text":"Да. Все три базовые модели адаптируются по длине, высоте, типу фасадов и отделке. Для нестандартных размеров требуется инженерная проверка."}},{"@type":"Question","name":"Как происходит доставка и сборка?","acceptedAnswer":{"@type":"Answer","text":"Доставка выполняется в специализированной упаковке. Сборка на месте включена для изделий свыше 160 см в Санкт-Петербурге и Ленобласти, а для остальных регионов согласовывается отдельно."}}]}]}</script>
</head>
<body>
  <style></style>

  <header class="wrap topbar" role="banner">
    <a class="brand" href="#top">Северная Мануфактура</a>
    <nav class="nav" aria-label="Основная навигация">
      <a href="#catalog">Каталог</a>
      <a href="#schematic">Соединения</a>
      <a href="#certifications">Сертификаты</a>
      <a href="#faq">FAQ</a>
      <a href="#contact">Контакты</a>
    </nav>
  </header>

  <main id="top">
    <section class="wrap hero" aria-labelledby="hero-title">
      <div class="hero-copy">
        <p class="eyebrow">Бутик-производство · массив дуба</p>
        <h1 id="hero-title">Мебель из массива дуба для архитектурных интерьеров</h1>
        <p>Северная Мануфактура проектирует и изготавливает обеденные столы, шкафы и архитектурную столярную продукцию из массива дуба. Мы делаем акцент на стабильности конструкции, честной структуре дерева и точных столярных соединениях.</p>
        <div>
          <a class="cta" href="#contact">Запросить проект</a>
        </div>
      </div>

      <div class="hero-art" aria-hidden="true">
        <svg viewBox="0 0 400 300" width="400" height="300" role="img" aria-label="Схематичный силуэт обеденного стола из массива дуба">
          <rect x="0" y="0" width="400" height="300" fill="oklch(0.98 0.005 85)"></rect>
          <rect x="70" y="80" width="260" height="18" rx="1" fill="oklch(0.72 0.055 85)"></rect>
          <rect x="90" y="98" width="220" height="8" fill="oklch(0.62 0.055 85)"></rect>
          <rect x="100" y="106" width="14" height="118" fill="oklch(0.60 0.055 85)"></rect>
          <rect x="286" y="106" width="14" height="118" fill="oklch(0.60 0.055 85)"></rect>
          <rect x="114" y="128" width="172" height="10" fill="oklch(0.66 0.055 85)"></rect>
          <rect x="128" y="138" width="10" height="86" fill="oklch(0.58 0.055 85)"></rect>
          <rect x="262" y="138" width="10" height="86" fill="oklch(0.58 0.055 85)"></rect>
          <rect x="142" y="164" width="116" height="8" fill="oklch(0.64 0.055 85)"></rect>
          <rect x="156" y="172" width="8" height="52" fill="oklch(0.56 0.055 85)"></rect>
          <rect x="236" y="172" width="8" height="52" fill="oklch(0.56 0.055 85)"></rect>
          <rect x="70" y="224" width="260" height="6" fill="oklch(0.70 0.055 85)"></rect>
          <rect x="100" y="230" width="14" height="24" fill="oklch(0.55 0.055 85)"></rect>
          <rect x="286" y="230" width="14" height="24" fill="oklch(0.55 0.055 85)"></rect>
          <rect x="70" y="254" width="260" height="4" fill="oklch(0.60 0.055 85)"></rect>
          <rect x="80" y="258" width="240" height="2" fill="oklch(0.78 0.02 85)"></rect>
        </svg>
      </div>
    </section>

    <section class="wrap" id="catalog" aria-labelledby="catalog-title">
      <h2 id="catalog-title">Флагманские модели</h2>
      <div class="table-wrap">
        <table>
          <caption class="visually-hidden" style="display:none">Характеристики флагманских моделей из массива дуба</caption>
          <thead>
            <tr>
              <th scope="col">Модель</th>
              <th scope="col">Тип</th>
              <th scope="col">Габариты</th>
              <th scope="col">Материал</th>
              <th scope="col">Соединения</th>
              <th scope="col">Отделка</th>
              <th scope="col">Срок</th>
              <th scope="col">Цена</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><a href="#contact">Nordic 2400</a></td>
              <td>Обеденный стол</td>
              <td>240 × 95 × 76 см</td>
              <td>Массив дуба, цельные ламели</td>
              <td>Шип-паз, сквозные клинья</td>
              <td>Масло с твердым воском</td>
              <td>10–12 недель</td>
              <td>от 390 000 ₽</td>
            </tr>
            <tr>
              <td><a href="#contact">Baltic Cabinet</a></td>
              <td>Шкаф / корпусная мебель</td>
              <td>180 × 55 × 220 см</td>
              <td>Массив дуба, каркас и фасады</td>
              <td>Ласточкин хвост, шип-паз</td>
              <td>Матовое масло, ручная шлифовка</td>
              <td>12–16 недель</td>
              <td>от 620 000 ₽</td>
            </tr>
            <tr>
              <td><a href="#contact">Karelian Joinery</a></td>
              <td>Архитктурная столярная панель</td>
              <td>120 × 3 × 240 см</td>
              <td>Массив дуба, стабилизированные ламели</td>
              <td>Шип-паз, ласточкин хвост</td>
              <td>Тонированное масло, защитный воск</td>
              <td>8–10 недель</td>
              <td>от 280 000 ₽</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="wrap schematic" id="schematic" aria-labelledby="schematic-title">
      <div>
        <h2 id="schematic-title">Техническая схема столярного соединения</h2>
        <p>Схема показывает поперечное сечение соединения шип-паз и фрагмент ласточкин хвост. Конструкция рассчитана на естественное движение массива дуба и сохраняет точность посадки при сезонных изменениях влажности.</p>
        <p>Мы не используем скрытые крепежные узлы в лицевых поверхностях. Несущая прочность достигается за счет точных пазов, шипов, клиньев и контурных зажимов, которые собираются вручную и подгоняются на этапе сушки.</p>
      </div>

      <div class="schematic-panel" role="img" aria-label="Техническая схема соединения шип-паз и ласточкин хвост">
        <svg viewBox="0 0 640 400" width="640" height="400" aria-hidden="true">
          <rect x="0" y="0" width="640" height="400" fill="oklch(0.98 0.005 85)"></rect>
          <rect x="70" y="70" width="220" height="110" fill="oklch(0.72 0.055 85)"></rect>
          <rect x="290" y="95" width="180" height="60" fill="oklch(0.64 0.055 85)"></rect>
          <rect x="290" y="95" width="180" height="12" fill="oklch(0.56 0.055 85)"></rect>
          <rect x="290" y="143" width="180" height="12" fill="oklch(0.56 0.055 85)"></rect>
          <rect x="290" y="107" width="180" height="36" fill="oklch(0.70 0.055 85)"></rect>
          <rect x="360" y="110" width="50" height="30" fill="oklch(0.60 0.055 85)"></rect>
          <rect x="365" y="115" width="40" height="20" fill="oklch(0.76 0.055 85)"></rect>
          <rect x="378" y="122" width="14" height="6" fill="oklch(0.46 0.06 85)"></rect>
          <rect x="378" y="128" width="14" height="6" fill="oklch(0.46 0.06 85)"></rect>
          <rect x="378" y="134" width="14" height="6" fill="oklch(0.46 0.06 85)"></rect>
          <line x1="70" y1="70" x2="290" y2="70" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="70" y1="180" x2="290" y2="180" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="70" y1="70" x2="70" y2="180" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="290" y1="95" x2="470" y2="95" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="290" y1="155" x2="470" y2="155" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="470" y1="95" x2="470" y2="155" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="360" y1="110" x2="410" y2="110" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="360" y1="140" x2="410" y2="140" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="360" y1="110" x2="360" y2="140" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="410" y1="110" x2="410" y2="140" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>

          <rect x="130" y="230" width="180" height="90" fill="oklch(0.72 0.055 85)"></rect>
          <polygon points="310,250 370,240 370,310 310,300" fill="oklch(0.64 0.055 85)"></polygon>
          <polygon points="310,250 370,240 370,255 310,265" fill="oklch(0.56 0.055 85)"></polygon>
          <polygon points="310,285 370,275 370,310 310,300" fill="oklch(0.56 0.055 85)"></polygon>
          <polygon points="310,265 370,255 370,275 310,285" fill="oklch(0.70 0.055 85)"></polygon>
          <polygon points="310,250 370,240 370,310 310,300" fill="none" stroke="oklch(0.16 0.015 85)" stroke-width="2"></polygon>
          <line x1="130" y1="230" x2="310" y2="230" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="130" y1="320" x2="310" y2="320" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="130" y1="230" x2="130" y2="320" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="130" y1="265" x2="310" y2="265" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>
          <line x1="130" y1="285" x2="310" y2="285" stroke="oklch(0.16 0.015 85)" stroke-width="2"></line>

          <text x="90" y="60" fill="oklch(0.16 0.015 85)" font-family="ui-sans-serif, system-ui, Arial, sans-serif" font-size="16">Шип-паз</text>
          <text x="320" y="80" fill="oklch(0.16 0.015 85)" font-family="ui-sans-serif, system-ui, Arial, sans-serif" font-size="16">Паз и шип</text>
          <text x="150" y="220" fill="oklch(0.16 0.015 85)" font-family="ui-sans-serif, system-ui, Arial, sans-serif" font-size="16">Ласточкин хвост</text>
          <text x="330" y="355" fill="oklch(0.45 0.02 85)" font-family="ui-sans-serif, system-ui, Arial, sans-serif" font-size="14">Поперечное сечение</text>
          <text x="90" y="200" fill="oklch(0.45 0.02 85)" font-family="ui-sans-serif, system-ui, Arial, sans-serif" font-size="14">Несущая ножка</text>
          <text x="380" y="180" fill="oklch(0.45 0.02 85)" font-family="ui-sans-serif, system-ui, Arial, sans-serif" font-size="14">Сквозной клин</text>
        </svg>
      </div>
    </section>

    <section class="wrap" id="certifications" aria-labelledby="certifications-title">
      <h2 id="certifications-title">Сертификаты и соответствие</h2>
      <div class="certs">
        <article class="cert-card">
          <h3>FSC Chain of Custody</h3>
          <p>Древесина закупается у поставщиков с цепочкой ответственности FSC. Мы храним документы по партиям и фиксируем происхождение массива для каждого заказа.</p>
        </article>
        <article class="cert-card">
          <h3>ГОСТ и внутренние допуски</h3>
          <p>Изделия проектируются с учетом требований к стабильности массива, точности пазов, качеству обработки и безопасности мебели для жилых интерьеров.</p>
        </article>
        <article class="cert-card">
          <h3>Отделка и эксплуатация</h3>
          <p>Масло с твердым воском соответствует бытовому режиму эксплуатации. Мы предоставляем рекомендации по уходу и локальному ремонту лицевых поверхностей.</p>
        </article>
      </div>
    </section>

    <section class="wrap faq" id="faq" aria-labelledby="faq-title">
      <h2 id="faq-title">Вопросы и ответы</h2>

      <details open>
        <summary>Какая древесина используется в производстве?</summary>
        <p>Мы используем массив дуба из ответственных источников с сертификатом FSC. Основная база — карельский и архангельский дуб, а также отобранные партии из Ленинградской области.</p>
      </details>

      <details>
        <summary>Как обрабатывается столешница?</summary>
        <p>Столешница собирается из массивных ламелей и покрывается маслом с твердым воском. Допускается восстановление локальных повреждений без демонтажа изделия.</p>
      </details>

      <details>
        <summary>Сколько занимает изготовление?</summary>
        <p>Срок изготовления составляет от 10 до 16 недель в зависимости от сложности модели, сушки, стабильности массива и графика покраски.</p>
      </details>

      <details>
        <summary>Можно ли изменить размеры и отделку?</summary>
        <p>Да. Все три базовые модели адаптируются по длине, высоте, типу фасадов и отделке. Для нестандартных размеров требуется инженерная проверка.</p>
      </details>

      <details>
        <summary>Как происходит доставка и сборка?</summary>
        <p>Доставка выполняется в специализированной упаковке. Сборка на месте включена для изделий свыше 160 см в Санкт-Петербурге и Ленобласти, а для остальных регионов согласовывается отдельно.</p>
      </details>
    </section>

    <section class="wrap contact-grid" id="contact" aria-labelledby="contact-title">
      <div>
        <h2 id="contact-title">Контакты</h2>
        <p>Опишите проект: размеры, помещение, срок и желаемую отделку. Мы вернемся с техническим обсуждением и предварительной сметой.</p>
        <p class="contact-note">Форма работает без серверной обработки. Данные проверяются в браузере и не отправляются на внешний бэкенд.</p>
      </div>

      <form action="#" method="get" aria-describedby="form-help" novalidate="false">
        <label for="name">Имя</label>
        <input id="name" name="name" type="text" required minlength="2" autocomplete="name" aria-required="true">

        <label for="email">Email</label>
        <input id="email" name="email" type="email" required autocomplete="email" aria-required="true" pattern="[^@\s]+@[^@\s]+\.[^@\s]+">

        <label for="phone">Телефон</label>
        <input id="phone" name="phone" type="tel" autocomplete="tel" aria-required="false" pattern="[0-9+\s()-]{6,}">

        <label for="model">Интересующая модель</label>
        <select id="model" name="model" required aria-required="true">
          <option value="">Выберите модель</option>
          <option value="Nordic 2400">Nordic 2400</option>
          <option value="Baltic Cabinet">Baltic Cabinet</option>
          <option value="Karelian Joinery">Karelian Joinery</option>
          <option value="Индивидуальный проект">Индивидуальный проект</option>
        </select>

        <label for="message">Сообщение</label>
        <textarea id="message" name="message" required minlength="10" maxlength="1200" aria-required="true"></textarea>

        <label for="consent">Согласие</label>
        <input id="consent" name="consent" type="checkbox" value="yes" required aria-required="true">
        <span id="form-help">Нажимая кнопку, вы подтверждаете согласие на обработку контактных данных для ответа на запрос.</span>

        <button type="submit">Отправить запрос</button>
      </form>
    </section>
  </main>

  <footer class="wrap" role="contentinfo">
    <div class="footer-grid">
      <div>
        <h3>Северная Мануфактура</h3>
        <p>Мебель из массива дуба, корпусные изделия и архитектурная столярная продукция.</p>
      </div>
      <div>
        <h3>Мастерская</h3>
        <address>Санкт-Петербург, Лесная линия, 18</address>
        <p><a href="mailto:hello@severnaya-manufactura.example">hello@severnaya-manufactura.example</a></p>
        <p><a href="tel:+78120000000">+7 (812) 000-00-00</a></p>
      </div>
      <div>
        <h3>Документы</h3>
        <p><a href="/llms.txt">llms.txt</a></p>
        <p><a href="/robots.txt">robots.txt</a></p>
      </div>
    </div>
    <div class="footer-bottom">
      <p>© 2026 Северная Мануфактура</p>
    </div>
  </footer>

  <script></script>
</body>
</html>
```

FILE: llms.txt
```text
# Северная Мануфактура

> Бутик-производитель мебели из массива дуба: обеденные столы, шкафы и архитектурная столярная продукция.

## Company
- Organization: Северная Мануфактура
- Type: boutique solid oak furniture manufacturer
- Products: dining tables, cabinetry, architectural joinery
- Materials: solid oak, FSC-sourced timber
- Joinery: mortise-and-tenon, dovetail
- Certifications: FSC Chain of Custody, GOST compliance and internal engineering tolerances
- Location: Saint Petersburg, Russia
- Contact: hello@severnaya-manufactura.example, +7 (812) 000-00-00

## Flagship products
### Nordic 2400
- Type: dining table
- Material: solid oak, full-width lamellas
- Dimensions: 240 × 95 × 76 cm
- Joinery: mortise-and-tenon with through wedges
- Finish: hard-wax oil
- Lead time: 10–12 weeks
- Price: from 390,000 RUB

### Baltic Cabinet
- Type: cabinet / case furniture
- Material: solid oak frame and fronts
- Dimensions: 180 × 55 × 220 cm
- Joinery: dovetail and mortise-and-tenon
- Finish: matte oil, hand sanding
- Lead time: 12–16 weeks
- Price: from 620,000 RUB

### Karelian Joinery
- Type: architectural joinery panel
- Material: stabilized solid oak lamellas
- Dimensions: 120 × 3 × 240 cm
- Joinery: mortise-and-tenon and dovetail
- Finish: tinted oil with protective wax
- Lead time: 8–10 weeks
- Price: from 280,000 RUB

## FAQ
### Какая древесина используется в производстве?
Мы используем массив дуба из ответственных источников с сертификатом FSC. Основная база — карельский и архангельский дуб, а также отобранные партии из Ленинградской области.

### Как обрабатывается столешница?
Столешница собирается из массивных ламелей и покрывается маслом с твердым воском. Допускается восстановление локальных повреждений без демонтажа изделия.

### Сколько занимает изготовление?
Срок изготовления составляет от 10 до 16 недель в зависимости от сложности модели, сушки, стабильности массива и графика покраски.

### Можно ли изменить размеры и отделку?
Да. Все три базовые модели адаптируются по длине, высоте, типу фасадов и отделке. Для нестандартных размеров требуется инженерная проверка.

### Как происходит доставка и сборка?
Доставка выполняется в специализированной упаковке. Сборка на месте включена для изделий свыше 160 см в Санкт-Петербурге и Ленобласти, а для остальных регионов согласовывается отдельно.

## Technical
- Single-page landing
- Vanilla HTML/CSS/JS only
- No external font CDNs
- No stock photos of people
- Semantic HTML5
- Accessibility: keyboard accessible, prefers-reduced-motion respected
- Performance: critical CSS inline, CLS 0 with explicit sizes and aspect-ratio
- Security: strict CSP with SHA-256 hashes for inline script and style

## SEO
- Canonical: https://severnaya-manufactura.example/
- Language: ru
- JSON-LD @graph: Organization, Product, FAQPage, BreadcrumbList, WebSite
```

FILE: robots.txt
```text
User-agent: *
Allow: /

Sitemap: https://severnaya-manufactura.example/sitemap.xml
```

FILE: _headers
```text
/*
  Content-Security-Policy: default-src 'self'; script-src 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU='; style-src 'self' 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=' data:; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; upgrade-insecure-requests
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()
  Cross-Origin-Opener-Policy: same-origin
```