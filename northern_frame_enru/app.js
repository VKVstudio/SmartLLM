(function () {
  "use strict";
  var root = document.documentElement;
  root.setAttribute("data-stack", "html5_esm");
  root.setAttribute("data-motion", "motion");
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.setAttribute("data-reduced-motion", reduced ? "reduce" : "no-preference");
  var I18N = {"chrome:nav:index": {"en": "Home", "ru": "Главная"}, "chrome:nav:services": {"en": "Production Services", "ru": "Услуги"}, "chrome:nav:portfolio": {"en": "Our Films", "ru": "Фильмы"}, "chrome:nav:about": {"en": "The Studio", "ru": "Студия"}, "chrome:nav:contact": {"en": "Get a Quote", "ru": "Запрос"}, "chrome:lang_label": {"en": "Site language", "ru": "Язык сайта"}, "index:hero:cta2": {"en": "See our film archive", "ru": "Посмотреть архив фильмов"}, "index:hero:eyebrow": {"en": "Arctic Documentary", "ru": "Арктическая документалистика"}, "index:hero:h1": {"en": "Expedition-grade Arctic documentaries, delivered in 10 days", "ru": "Документальные фильмы для экспедиций в Арктике, снятые и доставленные за 10 дней"}, "index:hero:lead": {"en": "We film, edit, and deliver bilingual 4K narratives for outdoor brands — with cold-weather certified crews and full logistics coordination.", "ru": "Мы снимаем, монтируем и поставляем двуязычные 4K-нарративы для брендов outdoor — с командами, сертифицированными для работы в условиях холода, и полным координационным сопровождением логистики."}, "index:hero:cta1": {"en": "Request a production quote", "ru": "Запросить смету на производство"}, "index:hero:alt": {"en": "Cinematographer operating a camera in snowy Arctic conditions with a crew member checking equipment", "ru": "Оператор работает с камерой в заснеженных арктических условиях, пока член экипажа проверяет оборудование"}, "index:manifesto:statement": {"en": "Arctic documentaries for outdoor brands", "ru": "Арктические документальные фильмы для брендов outdoor"}, "index:manifesto:position": {"en": "We film, edit, and deliver bilingual 4K narratives for outdoor brands — with cold-weather certified crews and full logistics coordination.", "ru": "Мы снимаем, монтируем и поставляем двуязычные 4K-нарративы для брендов outdoor — с командами, сертифицированными для работы в условиях холода, и полным координационным сопровождением логистики."}, "index:features:h2": {"en": "How we deliver Arctic stories", "ru": "Как мы доставляем арктические истории"}, "index:features:item:0": {"en": "Manages permits, transport, and crew safety for remote Arctic locations.", "ru": "Управление разрешениями, транспортом и безопасностью экипажа для удаленных арктических локаций."}, "index:features:item:1": {"en": "Develops dual-language narratives optimized for international and local audiences.", "ru": "Разработка двуязычных нарративов, оптимизированных для международной и локальной аудитории."}, "index:features:item:2": {"en": "Utilizes specialized camera and lighting gear rated for sub-zero temperatures.", "ru": "Использование специализированной камеры и осветительного оборудования, рассчитанного на отрицательные температуры."}, "index:features:item:3": {"en": "Delivers calibrated color grades for consistent visual identity across platforms.", "ru": "Поставка калиброванных цветовых градаций для обеспечения единообразного визуального стиля на разных платформах."}, "index:gallery:cap:0": {"en": "Kirovsk expedition team setting up base camp at dawn", "ru": "Экспедиционная команда в Кировске устанавливает базовый лагерь на рассвете"}, "index:gallery:cap:1": {"en": "Murmansk coastline establishing shot with raw 4K footage", "ru": "Установочный кадр побережья Мурманска с исходным материалом в формате 4K"}, "index:gallery:cap:2": {"en": "Post-production color grading session in the studio", "ru": "Сессия цветокоррекции на этапе пост-продакшена в студии"}, "index:gallery:cap:3": {"en": "Northern Frame / Северный кадр"}, "index:gallery:cap:4": {"en": "Northern Frame / Северный кадр"}, "index:gallery:h2": {"en": "Frames from the field", "ru": "Кадров из полевых условий"}, "index:cta:text": {"en": "Request a quote to start your 10-day pre-production planning.", "ru": "Запросите смету, чтобы начать планирование 10-дневного пре-продакшена."}, "index:cta:btn": {"en": "Start a Project", "ru": "Запросить смету на производство"}, "index:contact:lead": {"en": "+7 8152 45-12-88 | hello@northernframe.ru | Lenina Prospekt 45, Murmansk | Mon-Fri 10:00-19:00", "ru": "+7 8152 45-12-88 | hello@northernframe.ru | Проспект Ленина 45, Мурманск | Пн-Пт 10:00-19:00"}, "index:contact:h2": {"en": "Talk to the Murmansk team", "ru": "Поговорить с командой в Мурманске"}, "chrome:form:name": {"en": "Your Name", "ru": "Ваше имя"}, "chrome:form:email": {"en": "Work Email or Phone", "ru": "Эл. почта или телефон"}, "chrome:form:msg": {"en": "Project Details", "ru": "Кратко о задаче"}, "chrome:form:send": {"en": "Send Request", "ru": "Отправить заявку"}, "chrome:footer:tag": {"en": "Northern Frame / Северный кадр — Arctic documentaries for outdoor brands. Murmansk & Kirovsk.", "ru": "Northern Frame / Северный кадр — Арктические документальные фильмы для брендов outdoor. Мурманск и Кировск."}, "chrome:footer:nav_h": {"en": "Navigation", "ru": "Навигация"}, "chrome:footer:contacts_h": {"en": "Contacts", "ru": "Контакты"}, "chrome:footer:rights": {"en": "All rights reserved.", "ru": "Все права защищены."}, "chrome:footer:legal": {"en": "Legal Information", "ru": "Правовая информация"}, "index:meta:title": {"en": "Northern Frame | Arctic Documentary Studio", "ru": "Northern Frame | Студия арктической документалистики"}, "index:meta:desc": {"en": "Expedition-grade Arctic documentaries for outdoor brands. Bilingual storytelling, 4K capture, and 10-day pre-production turnaround.", "ru": "Документальные фильмы для экспедиций в Арктике для брендов outdoor. Двуязычный сторителлинг, съемка в 4K и 10-дневный цикл пре-продакшена."}, "chrome:skip": {"en": "Skip to main content", "ru": "Перейти к основному содержанию"}, "services:hero:cta2": {"en": "View 2024 Expedition Reels", "ru": "Посмотреть ролики экспедиций 2024 года"}, "services:hero:eyebrow": {"en": "Arctic Production", "ru": "Арктическое производство"}, "services:hero:h1": {"en": "Expedition-grade documentary production in sub-zero conditions", "ru": "Документальное производство экспедиционного уровня в условиях суб-zero температур"}, "services:hero:lead": {"en": "We coordinate permits, cold-rated equipment, and bilingual narratives to deliver 4K footage from remote Arctic locations within 10 business days.", "ru": "Мы координируем разрешения, оборудование, рассчитанное на холод, и двуязычные нарративы, чтобы предоставить 4K-видео из удаленных арктических локаций в течение 10 рабочих дней."}, "services:hero:cta1": {"en": "Request a Production Quote", "ru": "Запросить смету на производство"}, "services:hero:alt": {"en": "Team members setting up cold-weather camera equipment on a snowy mountain slope", "ru": "Члены команды устанавливают оборудование для холодной погоды на заснеженном горном склоне"}, "services:features:h2": {"en": "Cold-Weather Equipment & Logistics", "ru": "Оборудование для холодной погоды и логистика"}, "services:features:item:0": {"en": "Arctic Logistics Coordination — Manages permits, transport, and crew safety for remote Arctic locations.", "ru": "Координация арктической логистики — Управляет разрешениями, транспортом и безопасностью экипажа для удаленных арктических локаций."}, "services:features:item:1": {"en": "Bilingual Scripting — Develops dual-language narratives optimized for international and local audiences.", "ru": "Двуязычное сценарное планирование — Разрабатывает двуязычные нарративы, оптимизированные для международной и местной аудитории."}, "services:features:item:2": {"en": "Cold-Weather Equipment — Utilizes specialized camera and lighting gear rated for sub-zero temperatures.", "ru": "Оборудование для холодной погоды — Использует специализированные камеры и осветительное оборудование, рассчитанное на суб-zero температуры."}, "services:features:item:3": {"en": "Post-Production Color Grading — Delivers calibrated color grades for consistent visual identity across platforms.", "ru": "Цветокоррекция на этапе пост-продакшена — Предоставляет калиброванные цветовые коррекции для обеспечения единого визуального стиля на всех платформах."}, "services:process:h2": {"en": "Pre-Production to Delivery Timeline", "ru": "Таймлайн от пре-продакшена до доставки"}, "services:process:name:0": {"en": "Pre-Production Planning", "ru": "Планирование пре-продакшена"}, "services:process:desc:0": {"en": "Deliverables include a finalized shot list, permit applications, and bilingual script drafts within 10 business days.", "ru": "Результат включает финальный список кадров, заявки на разрешения и черновики двуязычных сценариев в течение 10 рабочих дней."}, "services:process:name:1": {"en": "Expedition Execution", "ru": "Выполнение экспедиции"}, "services:process:desc:1": {"en": "Crew captures 4K RAW footage on location using cold-rated equipment, with daily backups and safety monitoring.", "ru": "Экипаж снимает 4K RAW-видео на месте с использованием оборудования, рассчитанного на холод, с ежедневным резервным копированием и мониторингом безопасности."}, "services:process:name:2": {"en": "Post-Production Editing", "ru": "Монтаж на этапе пост-продакшена"}, "services:process:desc:2": {"en": "Editors assemble the narrative structure, apply color grading, and prepare bilingual subtitles for delivery.", "ru": "Редакторы собирают структуру нарратива, применяют цветокоррекцию и готовят двуязычные субтитры для доставки."}, "services:process:name:3": {"en": "Final Delivery", "ru": "Финальная доставка"}, "services:process:desc:3": {"en": "Client receives the final film files, raw footage archive, and a complete project report within the agreed timeline.", "ru": "Клиент получает финальные файлы фильма, архив исходного материала и полный отчет по проекту в согласованные сроки."}, "services:faq:q:0": {"en": "Do you handle all permits for filming in restricted Arctic zones?", "ru": "Вы получаете все разрешения для съемок в ограниченных арктических зонах?"}, "services:faq:a:0": {"en": "Yes. We manage all permit applications, coordinate transport, and ensure crew safety compliance for remote locations.", "ru": "Да. Мы управляем всеми заявками на разрешения, координируем транспорт и обеспечиваем соблюдение мер безопасности экипажа для удаленных локаций."}, "services:faq:q:1": {"en": "How long does the pre-production phase take?", "ru": "Сколько времени занимает этап пре-продакшена?"}, "services:faq:a:1": {"en": "Pre-production planning, including script development and logistics coordination, is completed within 10 business days.", "ru": "Планирование пре-продакшена, включая разработку сценария и координацию логистики, завершается в течение 10 рабочих дней."}, "services:faq:q:2": {"en": "Is the footage available in both English and Russian?", "ru": "Доступно ли видео на английском и русском языках?"}, "services:faq:a:2": {"en": "Yes. All projects are delivered with bilingual narrative structures, ensuring accessibility for international and local audiences.", "ru": "Да. Все проекты доставляются с двуязычной структурой нарратива, обеспечивая доступность для международной и местной аудитории."}, "services:faq:q:3": {"en": "What happens if the weather conditions become unsafe during the shoot?", "ru": "Что происходит, если погодные условия становятся небезопасными во время съемок?"}, "services:faq:a:3": {"en": "We prioritize crew safety above all. If conditions become unsafe, we pause filming and reschedule to ensure the integrity of the project and the safety of the team.", "ru": "Мы ставим безопасность экипажа выше всего. Если условия становятся небезопасными, мы приостанавливаем съемки и переносим график, чтобы обеспечить целостность проекта и безопасность команды."}, "services:faq:h2": {"en": "Operational Constraints & Safety", "ru": "Операционные ограничения и безопасность"}, "services:cta:text": {"en": "Request a quote to start your Arctic documentary project. We respond within 24 hours.", "ru": "Запросите смету, чтобы начать ваш арктический документальный проект. Мы отвечаем в течение 24 часов."}, "services:cta:btn": {"en": "Start a Project", "ru": "Запросить смету на производство"}, "services:contact:lead": {"en": "+7 8152 45-12-88 | hello@northernframe.ru | Lenina Prospekt 45, Murmansk | Mon-Fri 10:00-19:00", "ru": "+7 8152 45-12-88 | hello@northernframe.ru | Проспект Ленина 45, Мурманск | Пн-Пт 10:00-19:00"}, "services:contact:h2": {"en": "Direct Line to Murmansk Studio", "ru": "Прямая линия студии в Мурманске"}, "chrome:crumb:home": {"en": "Home", "ru": "Главная"}, "chrome:crumb:services": {"en": "Services", "ru": "Услуги"}, "services:meta:title": {"en": "Services | Northern Frame Arctic Studios", "ru": "Услуги | Студии Northern Frame Arctic Studios"}, "services:meta:desc": {"en": "Expedition documentaries, brand films, and short promos. Cold-weather certified teams, bilingual scripting, and Arctic logistics coordination.", "ru": "Документальные фильмы экспедиций, бренд-фильмы и короткие промо. Команды, сертифицированные для работы в холодную погоду, двуязычное сценарное планирование и координация арктической логистики."}, "portfolio:hero:cta2": {"en": "View Completed Expeditions", "ru": "Посмотреть завершенные экспедиции"}, "portfolio:hero:eyebrow": {"en": "Murmansk Productions", "ru": "Murmansk Productions"}, "portfolio:hero:h1": {"en": "Arctic Documentary Films Delivered in 10 Days", "ru": "Арктические документальные фильмы, доставленные за 10 дней"}, "portfolio:hero:lead": {"en": "We produce bilingual 4K narratives for outdoor brands, managing cold-weather logistics and permits from Murmansk to Kirovsk.", "ru": "Мы создаем двуязычные 4K-нарративы для брендов outdoor, управляя логистикой в условиях холода и получением разрешений от Мурманска до Кировска."}, "portfolio:hero:cta1": {"en": "Request Production Quote", "ru": "Запросить смету на производство"}, "portfolio:hero:alt": {"en": "Aerial shot of a frozen lake surrounded by snow-covered mountains with a film crew visible", "ru": "Воздушный снимок замерзшего озера, окруженного покрытыми снегом горами, с видимой съемочной группой"}, "portfolio:gallery:cap:0": {"en": "Murmansk Coastline, 2019", "ru": "Побережье Мурманска, 2019"}, "portfolio:gallery:cap:1": {"en": "Kirovsk Expedition, 2021", "ru": "Экспедиция в Кировск, 2021"}, "portfolio:gallery:cap:2": {"en": "Norwegian Co-production, 2019", "ru": "Совместное производство с Норвегией, 2019"}, "portfolio:gallery:cap:3": {"en": "Arctic Winter Shoot, 2021", "ru": "Арктическая зимняя съемка, 2021"}, "portfolio:gallery:cap:4": {"en": "Murmansk Studio Review, 2017", "ru": "Обзор студии в Мурманске, 2017"}, "portfolio:gallery:h2": {"en": "Visual Proof from 12 Expeditions", "ru": "Визуальные доказательства из 12 экспедиций"}, "portfolio:features:h2": {"en": "Cold-Weather Logistics and Bilingual Scripting", "ru": "Логистика в условиях холода и двуязычное сценарное планирование"}, "portfolio:features:item:0": {"en": "Arctic Logistics Coordination — Manages permits, transport, and crew safety for remote Arctic locations.", "ru": "Координация арктической логистики — Управляет разрешениями, транспортом и безопасностью экипажа для удаленных арктических локаций."}, "portfolio:features:item:1": {"en": "Bilingual Scripting — Develops dual-language narratives optimized for international and local audiences.", "ru": "Двуязычное сценарное планирование — Разрабатывает двуязычные нарративы, оптимизированные для международной и локальной аудитории."}, "portfolio:features:item:2": {"en": "Cold-Weather Equipment — Utilizes specialized camera and lighting gear rated for sub-zero temperatures.", "ru": "Оборудование для холодной погоды — Использует специализированные камеры и осветительное оборудование, рассчитанное на температуры ниже нуля."}, "portfolio:features:item:3": {"en": "Post-Production Color Grading — Delivers calibrated color grades for consistent visual identity across platforms.", "ru": "Цветокоррекция на этапе пост-продакшена — Предоставляет калиброванные цветовые градации для обеспечения единообразного визуального стиля на всех платформах."}, "portfolio:testimonials:quote:0": {"en": "Delivered bilingual 4K campaign assets in 10 days, increasing web traffic by 40%.", "ru": "Поставили двуязычные 4K-материалы для кампании за 10 дней, увеличив веб-трафик на 40%."}, "portfolio:testimonials:author:0": {"en": "Nordic Outdoor Gear", "ru": "Nordic Outdoor Gear"}, "portfolio:testimonials:quote:1": {"en": "Co-produced a 4K documentary in 2 languages, resulting in a 25% increase in visitor inquiries.", "ru": "Совместно произвели 4K-документальный фильм на 2 языках, что привело к увеличению запросов посетителей на 25%."}, "portfolio:testimonials:author:1": {"en": "Murmansk Tourism Board", "ru": "Туристический совет Мурманска"}, "portfolio:testimonials:quote:2": {"en": "Secured a 4K brand film with color-graded deliverables, boosting booking conversions by 15%.", "ru": "Обеспечили 4K-бренд-фильм с цветокорректированными материалами, повысив конверсию бронирований на 15%."}, "portfolio:testimonials:author:2": {"en": "Kirovsk Ski Resort", "ru": "Горнолыжный курорт Кировск"}, "portfolio:testimonials:h2": {"en": "Client Results and Measurable Outcomes", "ru": "Результаты клиентов и измеримые показатели"}, "portfolio:cta:text": {"en": "Book a 10-day pre-production consultation to plan your next Arctic documentary.", "ru": "Забронируйте 10-дневную консультацию по пре-продакшену, чтобы спланировать ваш следующий арктический документальный фильм."}, "portfolio:cta:btn": {"en": "Start a Project", "ru": "Запросить смету на производство"}, "portfolio:contact:lead": {"en": "+7 8152 45-12-88 | hello@northernframe.ru | Lenina Prospekt 45, Murmansk | Mon-Fri 10:00-19:00", "ru": "+7 8152 45-12-88 | hello@northernframe.ru | Проспект Ленина 45, Мурманск | Пн-Пт 10:00-19:00"}, "portfolio:contact:h2": {"en": "Direct Line to Murmansk Studio", "ru": "Прямая линия студии в Мурманске"}, "chrome:crumb:portfolio": {"en": "Portfolio", "ru": "Фильмы"}, "portfolio:meta:title": {"en": "Portfolio | Northern Frame Documentary Films", "ru": "Портфолио | Документальные фильмы Northern Frame"}, "portfolio:meta:desc": {"en": "View our Arctic documentary projects for tourism and outdoor brands. 4K RAW footage, color-graded deliverables, and bilingual narratives.", "ru": "Посмотрите наши арктические документальные проекты для туристических и outdoor-брендов. 4K RAW-материалы, цветокорректированные материалы и двуязычные нарративы."}, "about:hero:cta2": {"en": "View Expedition Safety Protocols", "ru": "Посмотреть протоколы безопасности экспедиций"}, "about:hero:eyebrow": {"en": "Arctic Production", "ru": "Арктическое производство"}, "about:hero:h1": {"en": "Expedition-Safe Arctic Documentaries", "ru": "Экспедиционно-безопасные арктические документальные фильмы"}, "about:hero:lead": {"en": "We coordinate permits, transport, and safety protocols so you can focus on the narrative. Full pre-production planning delivered within 10 business days.", "ru": "Мы координируем разрешения, транспорт и протоколы безопасности, чтобы вы могли сосредоточиться на повествовании. Полное планирование пре-продакшена предоставляется в течение 10 рабочих дней."}, "about:hero:cta1": {"en": "Request Pre-Production Quote", "ru": "Запросить смету на пре-продакшен"}, "about:hero:alt": {"en": "Portrait of the Northern Frame team members in winter gear at the Murmansk studio", "ru": "Портрет членов команды «Северного кадра» в зимней экипировке в студии в Мурманске"}, "about:team:name:0": {"en": "Ivan Petrov", "ru": "Иван Петров"}, "about:team:role:0": {"en": "Director of Photography specializing in Arctic lighting conditions", "ru": "Оператор, специализирующийся на арктическом освещении"}, "about:team:name:1": {"en": "Anna Volkova", "ru": "Анна Волкова"}, "about:team:role:1": {"en": "Producer managing expedition logistics and permits", "ru": "Продюсер, управляющий логистикой экспедиций и разрешениями"}, "about:team:name:2": {"en": "Dmitry Smirnov", "ru": "Дмитрий Смирнов"}, "about:team:role:2": {"en": "Sound Engineer for on-location audio capture", "ru": "Звукоинженер для записи звука на месте"}, "about:team:name:3": {"en": "Elena Kuznetsova", "ru": "Елена Кузнецова"}, "about:team:role:3": {"en": "Post-Production Editor for bilingual narrative structure", "ru": "Редактор пост-продакшена для двуязычной структуры повествования"}, "about:team:h2": {"en": "Certified Crews for Sub-Zero Environments", "ru": "Сертифицированные экипажи для суб-нулевых условий"}, "about:about:lead": {"en": "Founded in Murmansk in 2017, Northern Frame established itself as a specialist in cold-weather documentary production. In 2019, we completed our first international co-production with the Norwegian tourism board, proving our logistical reliability. By 2021, we expanded operations to Kirovsk, ensuring rapid response for projects in the central Arctic.", "ru": "Основанная в Мурманске в 2017 году, компания «Северный кадр» зарекомендовала себя как специалист в области документального производства в условиях холодной погоды. В 2019 году мы завершили наше первое международное совместное производство с Норвежским туристическим советом, доказав нашу логистическую надежность. К 2021 году мы расширили операции на Кировск, обеспечивая быстрое реагирование на проекты в центральной части Арктики."}, "about:about:item:0": {"en": "Expedition safety and logistics coordination", "ru": "Основанная в Мурманске в 2017 году, компания «Северный кадр» зарекомендовала себя как специалист в области документального производства в условиях холодной погоды. В 2019 году мы завершили наше первое международное совместное производство с Норвежским туристическим советом, доказав нашу логистическую надежность. К 2021 году мы расширили операции на Кировск, обеспечивая быстрое реагирование на проекты в центральной части Арктики."}, "about:about:item:1": {"en": "Bilingual English/Russian narrative structure"}, "about:about:h2": {"en": "Logistics, Permits, and Cold-Weather Infrastructure", "ru": "Логистика, разрешения и инфраструктура для холодной погоды"}, "about:cta:text": {"en": "Request a pre-production plan to secure your permits and crew safety within 10 business days.", "ru": "Запросите план пре-продакшена, чтобы обеспечить получение разрешений и безопасность экипажа в течение 10 рабочих дней."}, "about:cta:btn": {"en": "Start a Project", "ru": "Запросить смету на пре-продакшен"}, "about:contact:lead": {"en": "+7 8152 45-12-88 | hello@northernframe.ru | Lenina Prospekt 45, Murmansk | Mon-Fri 10:00-19:00", "ru": "+7 8152 45-12-88 | hello@northernframe.ru | Проспект Ленина 45, Мурманск | Пн-Пт 10:00-19:00"}, "about:contact:h2": {"en": "Direct Line to Murmansk Operations", "ru": "Прямая линия к операциям в Мурманске"}, "chrome:crumb:about": {"en": "About", "ru": "Студия"}, "about:meta:title": {"en": "About | Northern Frame Team & History", "ru": "О нас | Команда и история «Северного кадра»"}, "about:meta:desc": {"en": "Meet our cold-weather certified cinematographers, producers, and sound engineers. Founded in 2017 in Murmansk with a Kirovsk office.", "ru": "Познакомьтесь с нашими сертифицированными операторами, продюсерами и звукоинженерами, работающими в условиях холодной погоды. Основана в 2017 году в Мурманске с офисом в Кировске."}, "contact:hero:cta2": {"en": "View Contact Details", "ru": "Посмотреть контактные данные"}, "contact:hero:eyebrow": {"en": "Murmansk Studio", "ru": "Студия Мурманск"}, "contact:hero:h1": {"en": "Expedition Films Delivered in 10 Days", "ru": "Экспедиционные фильмы за 10 дней"}, "contact:hero:lead": {"en": "Secure your slot for the next Arctic season. We provide full logistics coordination, 4K RAW capture, and bilingual narrative structure for outdoor brands.", "ru": "Забронируйте слот на следующий арктический сезон. Мы обеспечиваем полную координацию логистики, съемку в 4K RAW и двуязычную структуру повествования для брендов на открытом воздухе."}, "contact:hero:cta1": {"en": "Request Quote", "ru": "Запросить смету"}, "contact:hero:alt": {"en": "Office interior with a desk, laptop, and contact information displayed on the wall", "ru": "Интерьер офиса с рабочим столом, ноутбуком и контактной информацией на стене"}, "contact:stats:label:0": {"en": "Expeditions filmed in the Arctic", "ru": "Экспедиций снято в Арктике"}, "contact:stats:label:1": {"en": "Native resolution capture", "ru": "Съемка в нативном разрешении"}, "contact:stats:label:2": {"en": "Business days pre-production turnaround", "ru": "Рабочих дней на пре-продакшн"}, "contact:stats:label:3": {"en": "Languages delivered per project", "ru": "Языков на проект"}, "contact:stats:h2": {"en": "The Ledger", "ru": "Журнал"}, "contact:locations:city:0": {"en": "Murmansk"}, "contact:locations:city:1": {"en": "Kirovsk"}, "contact:locations:h2": {"en": "Base Camps", "ru": "Базовые лагеря"}, "contact:faq:q:0": {"en": "How quickly can we start a project?", "ru": "Как быстро мы можем начать проект?"}, "contact:faq:a:0": {"en": "You get full pre-production planning within 10 business days.", "ru": "Вы получите полный план пре-продакшна в течение 10 рабочих дней."}, "contact:faq:q:1": {"en": "What are the pricing tiers?", "ru": "Каковы ценовые категории?"}, "contact:faq:a:1": {"en": "Expedition Documentary is 1,200,000 RUB, Brand Film is 450,000 RUB, and Short Promo is 150,000 RUB.", "ru": "Экспедиционный документальный фильм стоит 1 200 000 рублей, бренд-фильм — 450 000 рублей, а короткий промо-ролик — 150 000 рублей."}, "contact:faq:q:2": {"en": "Do you handle remote logistics?", "ru": "Вы занимаетесь удаленной логистикой?"}, "contact:faq:a:2": {"en": "Yes, we manage permits, transport, and crew safety for remote Arctic locations.", "ru": "Да, мы управляем разрешениями, транспортом и безопасностью экипажа для удаленных арктических локаций."}, "contact:faq:q:3": {"en": "Is the footage bilingual?", "ru": "Является ли отснятый материал двуязычным?"}, "contact:faq:a:3": {"en": "We deliver dual-language narratives optimized for international and local audiences.", "ru": "Мы поставляем двуязычные повествования, оптимизированные для международной и местной аудитории."}, "contact:faq:h2": {"en": "Field Notes", "ru": "Полевые заметки"}, "contact:cta:text": {"en": "Book a call to secure your slot for the next Arctic season and receive a quote within 10 business days.", "ru": "Запишитесь на звонок, чтобы забронировать слот на следующий арктический сезон и получить смету в течение 10 рабочих дней."}, "contact:cta:btn": {"en": "Start a Project", "ru": "Запросить смету"}, "contact:contact:lead": {"en": "+7 8152 45-12-88 | hello@northernframe.ru | Lenina Prospekt 45, Murmansk | Mon-Fri 10:00-19:00", "ru": "+7 8152 45-12-88 | hello@northernframe.ru | Проспект Ленина 45, Мурманск | Пн-Пт 10:00-19:00"}, "contact:contact:h2": {"en": "Direct Line", "ru": "Прямая линия"}, "chrome:crumb:contact": {"en": "Contact", "ru": "Запрос"}, "contact:meta:title": {"en": "Contact | Request a Quote | Northern Frame", "ru": "Контакты | Запросить смету | Северный кадр"}, "contact:meta:desc": {"en": "Contact Northern Frame for expedition film quotes. Based in Murmansk, open Mon-Fri 10:00-19:00. Email hello@northernframe.ru.", "ru": "Свяжитесь с Северным кадром для получения сметы на съемку экспедиционных фильмов. Базируется в Мурманске, работает Пн-Пт 10:00-19:00. Email hello@northernframe.ru."}};
  var BILINGUAL = true;
  var PRIMARY = "en";
  var MOTION_MODE = "motion";
  var STAGGER_MS = 65;
  var PARALLAX_ON = true;
  var MAGNETIC_ON = true;
  var TILT_ON = false;
  function applyLang(l) {
    if (!BILINGUAL) return;
    root.lang = l;
    var nodes = document.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) {
      var e = I18N[nodes[i].getAttribute("data-i18n")];
      if (e && e[l] && nodes[i].children.length === 0) nodes[i].textContent = e[l];
    }
    var alts = document.querySelectorAll("[data-i18n-alt]");
    for (var j = 0; j < alts.length; j++) {
      var ea = I18N[alts[j].getAttribute("data-i18n-alt")];
      if (ea && ea[l]) alts[j].setAttribute("alt", ea[l]);
    }
    var arias = document.querySelectorAll("[data-i18n-aria]");
    for (var a = 0; a < arias.length; a++) {
      var ear = I18N[arias[a].getAttribute("data-i18n-aria")];
      if (ear && ear[l]) arias[a].setAttribute("aria-label", ear[l]);
    }
    var metas = document.querySelectorAll("[data-i18n-content]");
    for (var k = 0; k < metas.length; k++) {
      var em = I18N[metas[k].getAttribute("data-i18n-content")];
      if (em && em[l]) metas[k].setAttribute("content", em[l]);
    }
    var btns = document.querySelectorAll(".lang-switch button");
    for (var b = 0; b < btns.length; b++) btns[b].setAttribute("aria-pressed", btns[b].getAttribute("data-lang") === l ? "true" : "false");
    try { localStorage.setItem("slm-lang", l); } catch (err) {}
  }
  if (BILINGUAL) {
    var saved = null;
    try { saved = localStorage.getItem("slm-lang"); } catch (err) {}
    var switcher = document.querySelector(".lang-switch");
    if (switcher) switcher.addEventListener("click", function (ev) {
      var btn = ev.target.closest("button[data-lang]");
      if (btn) applyLang(btn.getAttribute("data-lang"));
    });
    if (saved && saved !== PRIMARY) applyLang(saved);
  }
  var navToggle = document.getElementById("mobile-nav-toggle");
  var navList = document.getElementById("primary-nav-list");
  if (navToggle && navList) {
    navToggle.addEventListener("click", function () {
      var expanded = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", expanded ? "false" : "true");
      navList.setAttribute("data-open", expanded ? "false" : "true");
    });
  }
  var mqToggle = document.querySelector(".marquee-toggle");
  if (mqToggle) {
    mqToggle.addEventListener("click", function () {
      var wrap = mqToggle.closest(".marquee");
      if (!wrap) return;
      var paused = wrap.getAttribute("data-paused") === "true";
      wrap.setAttribute("data-paused", paused ? "false" : "true");
      mqToggle.setAttribute("aria-pressed", paused ? "false" : "true");
    });
  }
  document.querySelectorAll(".carousel-btn[data-dir]").forEach(function (cbtn) {
    cbtn.addEventListener("click", function () {
      var sec = cbtn.closest(".section-block");
      var grid = sec ? sec.querySelector(".canon-grid") : null;
      if (!grid) return;
      var dir = parseInt(cbtn.getAttribute("data-dir") || "1", 10) || 1;
      grid.scrollBy({ left: dir * 340, behavior: reduced ? "auto" : "smooth" });
    });
  });
  function animateStatCounters() {
    if (reduced || MOTION_MODE === "reduced_motion_instant") return;
    var stats = Array.prototype.slice.call(document.querySelectorAll(".stat-value"));
    if (!stats.length) return;
    function runCounter(el) {
      if (el.getAttribute("data-counted") === "1") return;
      el.setAttribute("data-counted", "1");
      var raw = (el.textContent || "").trim();
      var m = raw.match(/^([^0-9-]*)(-?[0-9][0-9., ]*)(.*)$/);
      if (!m || /^[/:-]/.test(m[3]) || (/[-/:.]/.test(m[2]) && !/[.,][0-9]{1,2}$/.test(m[2]))) return;
      var numStr = m[2].replace(/\s+/g, "").replace(",", ".");
      var target = parseFloat(numStr);
      if (!isFinite(target) || target <= 0 || (target >= 1900 && target <= 2100 && !m[3])) return;
      var decimals = (numStr.split(".")[1] || "").length;
      var prefix = m[1] || "";
      var suffix = m[3] || "";
      var start = null;
      var dur = 760;
      function step(ts) {
        if (!start) start = ts;
        var p = Math.min(1, (ts - start) / dur);
        var eased = 1 - Math.pow(1 - p, 3);
        var val = (target * eased).toFixed(decimals);
        if (decimals === 0 && target >= 1000 && m[2].indexOf(" ") !== -1) {
          val = val.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
        }
        el.textContent = prefix + val + suffix;
        if (p < 1) window.requestAnimationFrame(step);
        else el.textContent = raw;
      }
      window.requestAnimationFrame(step);
    }
    if ("IntersectionObserver" in window) {
      var so = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) {
            runCounter(en.target);
            so.unobserve(en.target);
          }
        });
      }, { threshold: 0.2 });
      stats.forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.top <= (window.innerHeight || 900)) runCounter(el);
        else so.observe(el);
      });
    }
  }
  function setupPointerInteractions() {
    if (reduced || !window.matchMedia || !window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    if (MAGNETIC_ON) {
      document.querySelectorAll(".hero-shell .cta-row .btn, .cta-banner .btn").forEach(function (btn) {
        btn.addEventListener("pointermove", function (ev) {
          var r = btn.getBoundingClientRect();
          var dx = ((ev.clientX - r.left) / Math.max(1, r.width) - 0.5) * 10;
          var dy = ((ev.clientY - r.top) / Math.max(1, r.height) - 0.5) * 7;
          btn.style.transform = "translate3d(" + dx.toFixed(1) + "px," + dy.toFixed(1) + "px,0)";
        });
        btn.addEventListener("pointerleave", function () {
          btn.style.transform = "";
        });
      });
    }
    if (TILT_ON) {
      var heroFig = document.querySelector(".hero-shell .hero-figure");
      if (heroFig) {
        heroFig.addEventListener("pointermove", function (ev) {
          var r = heroFig.getBoundingClientRect();
          var rx = ((ev.clientY - r.top) / Math.max(1, r.height) - 0.5) * -4;
          var ry = ((ev.clientX - r.left) / Math.max(1, r.width) - 0.5) * 5;
          heroFig.style.transform = "perspective(1100px) rotateX(" + rx.toFixed(2) + "deg) rotateY(" + ry.toFixed(2) + "deg)";
        });
        heroFig.addEventListener("pointerleave", function () {
          heroFig.style.transform = "";
        });
      }
    }
  }
  if (!reduced && MOTION_MODE !== "reduced_motion_instant") {
    var revealEls = Array.prototype.slice.call(document.querySelectorAll(".section-block [data-reveal]"));
    var markRevealed = function (el) {
      el.classList.remove("slm-pending");
      el.classList.add("is-revealed");
    };
    if (revealEls.length) {
      var groups = {};
      var vhInit = window.innerHeight || root.clientHeight || 900;
      revealEls.forEach(function (el) {
        var sec = el.closest("section") || root;
        var key = sec.id || "root";
        groups[key] = groups[key] || 0;
        el.style.setProperty("--rd", (groups[key]++ * 65) + "ms");
        if (el.getBoundingClientRect().top <= vhInit * 0.92) {
          markRevealed(el);
        } else {
          el.classList.add("slm-pending");
        }
      });
      var io = null;
      var cleanupReveal = function () {
        window.removeEventListener("scroll", revealVisible);
        window.removeEventListener("resize", revealVisible);
      };
      var revealVisible = function () {
        var vh = window.innerHeight || root.clientHeight || 900;
        var remaining = 0;
        for (var idx = 0; idx < revealEls.length; idx++) {
          var el = revealEls[idx];
          if (el.classList.contains("is-revealed")) continue;
          if (el.getBoundingClientRect().top <= vh + 80) {
            markRevealed(el);
            if (io) io.unobserve(el);
          } else {
            remaining++;
          }
        }
        if (remaining === 0) cleanupReveal();
      };
      if ("IntersectionObserver" in window) {
        revealVisible();
        root.classList.add("js");
        io = new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            if (en.isIntersecting) {
              markRevealed(en.target);
              io.unobserve(en.target);
            }
          });
        }, { threshold: 0.01, rootMargin: "0px 0px 40px 0px" });
        var pendingReveal = 0;
        revealEls.forEach(function (el) {
          if (!el.classList.contains("is-revealed")) {
            io.observe(el);
            pendingReveal++;
          }
        });
        if (pendingReveal > 0) {
          window.requestAnimationFrame(revealVisible);
          window.setTimeout(revealVisible, 550);
          window.addEventListener("scroll", revealVisible, { passive: true });
          window.addEventListener("resize", revealVisible, { passive: true });
        }
      } else {
        revealEls.forEach(function (el) { markRevealed(el); });
        root.classList.add("js");
      }
    } else {
      root.classList.add("js");
    }
    var scrollySteps = Array.prototype.slice.call(document.querySelectorAll(".scrolly-stage .scrolly-step"));
    if (scrollySteps.length) {
      var scCounter = document.getElementById("scrolly-counter");
      var scCaption = document.getElementById("scrolly-caption");
      var scPinImg = document.querySelector(".scrolly-pin img");
      var activateStep = function (stepEl, idx) {
        scrollySteps.forEach(function (st, j) {
          st.classList.toggle("is-active", j === idx);
        });
        var total = String(scrollySteps.length).padStart(2, "0");
        var curNum = String(idx + 1).padStart(2, "0");
        if (scCounter) scCounter.textContent = curNum + " / " + total;
        var ttl = stepEl.getAttribute("data-step-title");
        if (scCaption && ttl) scCaption.textContent = ttl;
        if (scPinImg) {
          var scScale = 1 + (idx * 0.018);
          if (window.Motion && typeof window.Motion.animate === "function") {
            window.Motion.animate(scPinImg, { scale: scScale }, { duration: 0.45, ease: [0.22, 1, 0.36, 1] });
          } else {
            scPinImg.style.transform = "scale(" + scScale.toFixed(3) + ")";
          }
        }
      };
      if ("IntersectionObserver" in window) {
        var stepIo = new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            if (!en.isIntersecting) return;
            var idx = scrollySteps.indexOf(en.target);
            if (idx >= 0) activateStep(en.target, idx);
          });
        }, { rootMargin: "-30% 0px -30% 0px", threshold: 0.05 });
        scrollySteps.forEach(function (st) { stepIo.observe(st); });
      }
      scrollySteps.forEach(function (st, idx) {
        st.addEventListener("pointerenter", function () { activateStep(st, idx); });
      });
    }
    var bar = document.querySelector(".scroll-progress");
    var heroImg = document.querySelector(".hero-figure img");
    var ticking = false;
    var onScroll = function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        ticking = false;
        var max = root.scrollHeight - window.innerHeight;
        if (bar && MOTION_MODE !== "css_scroll_driven") bar.style.transform = "scaleX(" + (max > 0 ? Math.min(1, window.scrollY / max) : 0) + ")";
        if (PARALLAX_ON && heroImg) {
          var r = heroImg.getBoundingClientRect();
          if (r.bottom > 0 && r.top < window.innerHeight) heroImg.style.transform = "translateY(" + Math.min(28, window.scrollY * 0.055).toFixed(1) + "px) scale(1.03)";
        }
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    animateStatCounters();
    setupPointerInteractions();
  } else {
    document.querySelectorAll("[data-reveal]").forEach(function (el) { el.classList.remove("slm-pending"); el.classList.add("is-revealed"); });
    root.classList.add("js");
    root.setAttribute("data-motion-active", "reduced");
  }
  function bootVendorMotion() {
    if (reduced || MOTION_MODE === "reduced_motion_instant") return;
    var activeParts = [];
    if (typeof window.Lenis === "function" && (MOTION_MODE === "motion" || MOTION_MODE === "animejs" || MOTION_MODE === "lenis" || MOTION_MODE === "three")) {
      try {
        window.__slmLenis = new window.Lenis({
          autoRaf: true,
          lerp: 0.088,
          wheelMultiplier: 1.0,
          smoothWheel: true,
          anchors: true,
          respectReducedMotion: true
        });
        activeParts.push("lenis");
      } catch (err) {}
    }
    var M = window.Motion;
    if (MOTION_MODE === "motion" && M && typeof M.animate === "function") {
      activeParts.unshift("motion");
      try {
        var heroNodes = Array.prototype.slice.call(document.querySelectorAll(".hero-shell .eyebrow, .hero-shell h1, .hero-shell .lead-copy, .hero-shell .cta-row"));
        if (heroNodes.length && typeof M.stagger === "function") {
          M.animate(heroNodes, { opacity: [0.001, 1], y: [22, 0] }, { duration: 0.56, delay: M.stagger(0.065), ease: [0.22, 1, 0.36, 1] });
        }
        var hFig = document.querySelector(".hero-shell .hero-figure");
        if (hFig) {
          M.animate(hFig, { opacity: [0.001, 1], scale: [0.96, 1] }, { duration: 0.68, ease: [0.16, 1, 0.3, 1] });
        }
        var barEl = document.querySelector(".scroll-progress");
        if (barEl && typeof M.scroll === "function") {
          M.scroll(function (prog) {
            if (typeof prog === "number") barEl.style.transform = "scaleX(" + Math.max(0, Math.min(1, prog)).toFixed(4) + ")";
          });
        }
        if (typeof M.inView === "function" && typeof M.stagger === "function") {
          document.querySelectorAll(".section-block").forEach(function (sec) {
            var pendingCards = Array.prototype.slice.call(sec.querySelectorAll("[data-reveal].slm-pending"));
            if (!pendingCards.length) return;
            M.inView(sec, function () {
              var allCards = Array.prototype.slice.call(sec.querySelectorAll("[data-reveal]"));
              allCards.forEach(function (c) {
                c.classList.remove("slm-pending");
                c.classList.add("is-revealed");
              });
              M.animate(allCards, { opacity: [0.001, 1], y: [32, 0], scale: [0.975, 1] }, { duration: 0.56, delay: M.stagger(Math.max(0.035, STAGGER_MS / 1000)), ease: [0.22, 1, 0.36, 1] });
            }, { amount: 0.12 });
          });
        }
        if (PARALLAX_ON) {
          document.querySelectorAll(".gallery-card").forEach(function (card) {
            var img = card.querySelector("img");
            if (!img || typeof M.scroll !== "function") return;
            try {
              M.scroll(M.animate(img, { y: [-14, 14], scale: [1.06, 1.01] }, { ease: "linear" }), { target: card, offset: ["start end", "end start"] });
            } catch (e1) {}
          });
        }
      } catch (err) {}
    } else if (MOTION_MODE === "animejs" && window.anime && typeof window.anime.animate === "function") {
      activeParts.unshift("animejs");
      try {
        var A = window.anime;
        var aHero = document.querySelectorAll(".hero-shell .eyebrow, .hero-shell h1, .hero-shell .lead-copy, .hero-shell .cta-row, .hero-shell .hero-figure");
        if (aHero.length && typeof A.createTimeline === "function") {
          var tl = A.createTimeline({ defaults: { ease: "outExpo", duration: 640 } });
          tl.add(aHero, { opacity: [0.001, 1], translateY: [22, 0], delay: typeof A.stagger === "function" ? A.stagger(65) : 0 });
        } else if (aHero.length) {
          A.animate(aHero, { opacity: [0.001, 1], translateY: [22, 0], duration: 640, delay: typeof A.stagger === "function" ? A.stagger(65) : 0, ease: "outExpo" });
        }
        if ("IntersectionObserver" in window) {
          var aio = new IntersectionObserver(function (entries) {
            entries.forEach(function (en) {
              if (!en.isIntersecting) return;
              var items = en.target.querySelectorAll("[data-reveal]");
              if (items.length) {
                items.forEach(function (it) {
                  it.classList.remove("slm-pending");
                  it.classList.add("is-revealed");
                });
                A.animate(items, { opacity: [0.001, 1], translateY: [32, 0], scale: [0.975, 1], duration: 560, delay: typeof A.stagger === "function" ? A.stagger(Math.max(35, STAGGER_MS)) : 0, ease: "outExpo" });
              }
              aio.unobserve(en.target);
            });
          }, { threshold: 0.12 });
          document.querySelectorAll(".section-block").forEach(function (sec) { aio.observe(sec); });
        }
      } catch (err) {}
    } else if (activeParts.length === 0) {
      activeParts.push(MOTION_MODE);
    }
    root.setAttribute("data-motion-active", activeParts.join("+"));
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootVendorMotion, { once: true });
  } else {
    window.setTimeout(bootVendorMotion, 0);
  }
  var form = document.querySelector(".intake-form");
  if (form) form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var trap = form.querySelector(".hp-trap input, input.hp-trap");
    if (trap && trap.value) return;
    var btn = form.querySelector("button[type=submit]");
    var status = form.querySelector(".form-status");
    if (btn) btn.disabled = true;
    if (status) status.textContent = "Request sent — we will get back to you.";
    window.setTimeout(function () {
      if (btn) btn.disabled = false;
      if (status) status.textContent = "";
      form.reset();
    }, 4000);
  });
})();
