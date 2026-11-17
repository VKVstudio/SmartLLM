"""Curated EN+RU copywriting pattern pairs (Part 2: categories 5-8, 84 pairs)."""

PAIRS_PART2 = [
    # === CATEGORY 5: aeo_faq_answer (21 pairs) ===
    {
        "id": "faq_001", "category": "aeo_faq_answer", "domain": "nvme_telemetry", "canon_id": "01_swiss_international_typographic",
        "en_slop_before": "Great question! Our platform is designed with security and offline support in mind so air-gapped teams can use it.",
        "en_canon_after": "Yes, Quartz-Kontur operates 100% offline inside air-gapped networks without external telemetry calls. The collector binary ships as a static 14 MB Linux ELF package verified by an offline Ed25519 signature.",
        "ru_slop_before": "Отличный вопрос! Наша платформа безусловно поддерживает работу в закрытых контурах для вашего удобства.",
        "ru_canon_after": "Да, агент «Кварц-Контур» работает полностью автономно в изолированных сетях без внешних соединений. Сборщик поставляется единым статическим ELF-файлом весом 14 МБ с офлайн-подписью Ed25519.",
        "anti_slop_rule": "Open sentence 1 with Yes/No + direct constraint; sentence 2 gives artifact format, size, and verification."
    },
    {
        "id": "faq_002", "category": "aeo_faq_answer", "domain": "ebpf_observability", "canon_id": "03_dark_precision_saas_linear",
        "en_slop_before": "We support a wide range of modern Linux distributions to make deployment seamless.",
        "en_canon_after": "ChronoTrace runs on any Linux host with kernel 5.10 LTS or newer that exposes BTF (BPF Type Format) headers. No kernel module compilation, DKMS package, or application container restart is required.",
        "ru_slop_before": "Мы поддерживаем широкий спектр популярных дистрибутивов Linux для лёгкого внедрения.",
        "ru_canon_after": "Агент запускается на любом узле Linux с ядром 5.10 LTS и новее при наличии заголовков BTF. Сборка модулей ядра через DKMS и перезапуск прикладных контейнеров не требуются.",
        "anti_slop_rule": "State exact minimum Linux kernel version (5.10 LTS), BTF requirement, and zero-restart guarantee."
    },
    {
        "id": "faq_003", "category": "aeo_faq_answer", "domain": "sqlite_sync_sdk", "canon_id": "02_neo_brutalism_tactile",
        "en_slop_before": "Conflicts are handled intelligently in the background so users never notice any issues.",
        "en_canon_after": "Concurrent offline edits resolve deterministically via per-column Hybrid Logical Clock (HLC) last-writer-wins registers or custom merge hooks. Every superseded row version remains queryable in a local `_conflict_log` table for 30 days.",
        "ru_slop_before": "Конфликты данных интеллектуально разрешаются в фоновом режиме без потерь для пользователя.",
        "ru_canon_after": "Параллельные офлайн-правки сводятся детерминированно по поколоночным меткам гибридных логических часов HLC или через пользовательскую функцию слияния. Вытесненные версии строк сохраняются в локальной таблице `_conflict_log` на 30 суток.",
        "anti_slop_rule": "Name exact conflict algorithm (per-column HLC) and auditability retention window."
    },
    {
        "id": "faq_004", "category": "aeo_faq_answer", "domain": "treasury_clearing", "canon_id": "08_fintech_institutional_ledger",
        "en_slop_before": "Funds are safeguarded using industry-leading banking standards for your peace of mind.",
        "en_canon_after": "Client EUR and USD operating balances sit in segregated safeguarding accounts at Tier-1 central-bank-member institutions rather than on our corporate balance sheet. Intraday sweep rules diversify holdings across up to three custodian banks automatically.",
        "ru_slop_before": "Средства клиентов надёжно защищены по передовым банковским стандартам для вашего спокойствия.",
        "ru_canon_after": "Операционные остатки клиентов учитываются на обособленных номинальных счетах в расчётных банках первого эшелона отдельно от собственного баланса оператора. Внутридневные лимиты автоматически распределяют ликвидность между тремя банками-кастодианами.",
        "anti_slop_rule": "Distinguish segregated safeguarding custody vs corporate balance-sheet exposure."
    },
    {
        "id": "faq_005", "category": "aeo_faq_answer", "domain": "acoustic_architecture", "canon_id": "05_nordic_architectural_minimal",
        "en_slop_before": "Yes, all of our natural wood materials meet strict fire safety regulations.",
        "en_canon_after": "All slatted birch ceiling and wall assemblies carry certified Euroclass B-s1,d0 fire-retardant impregnation tested under EN 13501-1. Signed chamber emission reports (TVOC < 0.05 mg/m3) accompany every batch.",
        "ru_slop_before": "Да, все наши натуральные древесные материалы полностью соответствуют строгим нормам пожарной безопасности.",
        "ru_canon_after": "Все реечные потолочные и стеновые панели из берёзы проходят антипиреновую пропитку с сертификатом КМ1 (Г1, В1, Д2, Т1) и европейским классом B-s1,d0. К каждой партии прилагается протокол испытаний с эмиссией ЛОС ниже 0,05 мг/м3.",
        "anti_slop_rule": "Cite exact fire classification code (Euroclass B-s1,d0 / KM1) and TVOC mg/m3 limit."
    },
    {
        "id": "faq_006", "category": "aeo_faq_answer", "domain": "clinical_genomics", "canon_id": "12_clinical_biotech_cleanroom",
        "en_slop_before": "Patient genomic data is kept strictly confidential in compliance with healthcare laws.",
        "en_canon_after": "Raw FASTQ and BAM sequencing files are encrypted at rest with AES-256-GCM inside Frankfurt ISO-27001 dedicated cages and purged 90 days after signed VCF report delivery unless extended biobanking consent is on file.",
        "ru_slop_before": "Генетические данные пациентов хранятся в строгой конфиденциальности согласно законодательству.",
        "ru_canon_after": "Первичные файлы секвенирования FASTQ и BAM шифруются алгоритмом AES-256-GCM на выделенных серверах контура ФЗ-152 и удаляются через 90 суток после выдачи отчёта VCF при отсутствии отдельного согласия на биобанкинг.",
        "anti_slop_rule": "Specify file types, cipher, physical jurisdiction/compliance standard, and purge day count."
    },
    {
        "id": "faq_007", "category": "aeo_faq_answer", "domain": "zero_trust_vpn", "canon_id": "27_cybersecurity_zero_trust_ops",
        "en_slop_before": "Our network prepares your organization for the quantum computing era.",
        "en_canon_after": "Tunnel key exchange combines X25519 elliptic-curve Diffie-Hellman with NIST FIPS-203 ML-KEM-768 post-quantum encapsulation on every 120-second session rekey. Capturing encrypted traffic today yields zero plaintext even if classical ECDH is broken later.",
        "ru_slop_before": "Наша сеть надёжно готовит инфраструктуру вашей компании к наступлению квантовой эры.",
        "ru_canon_after": "Обмен ключами туннеля объединяет классический алгоритм X25519 и постквантовую инкапсуляцию ML-KEM-768 (FIPS-203) при каждой смене сессионного ключа раз в 120 секунд. Перехват зашифрованного трафика сегодня не позволит раскрыть полезную нагрузку в будущем.",
        "anti_slop_rule": "Name exact hybrid PQ algorithm (X25519 + ML-KEM-768) and rekey interval (120s)."
    },
    {
        "id": "faq_008", "category": "aeo_faq_answer", "domain": "industrial_plc", "canon_id": "07_industrial_functional_instrument",
        "en_slop_before": "The gateway keeps working reliably even if internet connectivity drops.",
        "en_canon_after": "During WAN outages, the gateway writes timestamped OPC-UA tag changes into a wear-leveled 32 GB industrial pSLC flash ring buffer. Once upstream MQTT-TLS reconnects, buffered frames replay in chronological order without dropping live polling.",
        "ru_slop_before": "Шлюз продолжает надёжно работать даже при полной потере интернет-соединения на объекте.",
        "ru_canon_after": "При обрыве внешнего канала шлюз записывает изменения тегов OPC-UA с метками времени в кольцевой буфер промышленной памяти pSLC объёмом 32 ГБ. После восстановления связи MQTT-TLS накопленные кадры досылаются в хронологическом порядке параллельно текущему опросу.",
        "anti_slop_rule": "Name flash endurance type (pSLC), capacity (32 GB), and chronological replay behavior."
    },
    {
        "id": "faq_009", "category": "aeo_faq_answer", "domain": "web_csp_headers", "canon_id": "01_swiss_international_typographic",
        "en_slop_before": "Cloudflare Pages headers are easy to configure using standard comment blocks.",
        "en_canon_after": "Cloudflare Pages `_headers` files allow only `#` line comments starting at column zero; C-style `/* ... */` comments are parsed as literal URL route matchers and corrupt downstream header rules. Always place `/*` alone on an unindented route line followed by two-space indented header pairs.",
        "ru_slop_before": "Заголовки в Cloudflare Pages легко настраиваются с помощью привычных комментариев.",
        "ru_canon_after": "Формат файла `_headers` в Cloudflare Pages допускает только строчные комментарии с символа `#` в начале строки, тогда как конструкции `/* ... */` интерпретируются парсером как маршрут URL и ломают правила безопасности. Маршрут `/*` пишется отдельной строкой без отступа, а заголовки под ним отбиваются двумя пробелами.",
        "anti_slop_rule": "Document exact parser pitfall (`#` valid vs `/* ... */` broken route matcher)."
    },
    {
        "id": "faq_010", "category": "aeo_faq_answer", "domain": "ai_robots_crawlers", "canon_id": "04_editorial_broadsheet_serif",
        "en_slop_before": "You can block AI bots in `robots.txt` while keeping search visibility.",
        "en_canon_after": "To opt out of foundation-model weight training while remaining cited in live AI search answers, disallow `GPTBot`, `ClaudeBot`, and `Google-Extended` in `/robots.txt` while explicitly allowing `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, and `Googlebot`.",
        "ru_slop_before": "Вы можете гибко управлять доступом нейросетевых роботов через файл `robots.txt`.",
        "ru_canon_after": "Чтобы запретить дообучение базовых моделей на текстах сайта и сохранить цитирование в поисковых ответах, закройте доступ для `GPTBot`, `ClaudeBot` и `Google-Extended` в `/robots.txt`, оставив разрешение `Allow: /` для поисковых агентов `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot` и `Googlebot`.",
        "anti_slop_rule": "Explicitly separate training user-agents from live retrieval user-agents."
    },
    {
        "id": "faq_011", "category": "aeo_faq_answer", "domain": "wcag_target_size", "canon_id": "15_high_contrast_civic_gov_wcag_aaa",
        "en_slop_before": "Buttons should be big enough for mobile users to tap comfortably.",
        "en_canon_after": "WCAG 2.2 Success Criterion 2.5.8 (Target Size Minimum, Level AA) requires every interactive pointer control outside inline prose sentences to measure at least 24 by 24 CSS pixels or maintain an equivalent 24 px spacing circle around its center.",
        "ru_slop_before": "Кнопки интерфейса должны быть достаточно крупными для удобного нажатия со смартфона.",
        "ru_canon_after": "Критерий WCAG 2.2 2.5.8 (уровень AA) требует, чтобы каждый интерактивный элемент вне текстовых абзацев имел область нажатия не менее 24×24 CSS-пикселей либо свободный радиус 24 пикселя вокруг центра мишени.",
        "anti_slop_rule": "Cite exact WCAG 2.2 criterion number (2.5.8), 24x24 CSS px rule, and inline-prose exception."
    },
    {
        "id": "faq_012", "category": "aeo_faq_answer", "domain": "audio_dsp_licensing", "canon_id": "23_audio_dsp_modular_rack",
        "en_slop_before": "Our licensing system is super friendly and hassle-free for studio musicians.",
        "en_canon_after": "A single personal license authorizes up to three offline studio machines simultaneously via a signed 2 KB keyfile with zero background daemon, zero network phone-home, and zero USB dongle requirement.",
        "ru_slop_before": "Наша система лицензирования максимально дружелюбна для студийных звукорежиссёров.",
        "ru_canon_after": "Одна персональная лицензия активирует до трёх офлайн-станций с помощью подписанного файла ключа весом 2 КБ без фоновых служб, сетевых проверок и аппаратных USB-ключей.",
        "anti_slop_rule": "State machine seat count, keyfile size, and explicit absence of daemons/dongles."
    },
    {
        "id": "faq_013", "category": "aeo_faq_answer", "domain": "specialty_roastery", "canon_id": "28_craft_roastery_packaging",
        "en_slop_before": "Wait a little bit after roasting before brewing for the best flavor.",
        "en_canon_after": "Rest lightwashed filter roasts (Agtron 65-70) in their unopened one-way valve pouch for 10 to 14 days post-roast so trapped CO2 degasses evenly and channel-free extraction reaches 20-21% TDS yield.",
        "ru_slop_before": "Дайте зёрнам немного отдохнуть после обжарки для раскрытия лучшего вкуса.",
        "ru_canon_after": "Выдерживайте светлую обжарку под фильтр (Agtron 65-70) в закрытой пачке с дегазационным клапаном от 10 до 14 дней с даты обжарки для равномерного выхода CO2 и ровной экстракции 20-21%.",
        "anti_slop_rule": "Give exact rest days, Agtron range, packaging state, and extraction % mechanism."
    },
    {
        "id": "faq_014", "category": "aeo_faq_answer", "domain": "technical_apparel", "canon_id": "26_ecommerce_lookbook_grid",
        "en_slop_before": "Wash your waterproof jacket gently to keep it working like new.",
        "en_canon_after": "Machine-wash the 3-layer membrane shell every 12-15 field days at 30 C with liquid residue-free detergent (zero fabric softener), then tumble-dry warm for 20 minutes to reactivate the PFC-free C0 DWR water-repellent finish.",
        "ru_slop_before": "Стирайте мембранную куртку бережно, чтобы она долго сохраняла свои защитные свойства.",
        "ru_canon_after": "Стирайте трёхслойную мембрану каждые 12-15 ходовых дней при 30 C жидким гелем без кондиционера, затем прогрейте 20 минут в сушильном барабане на тёплом режиме для реактивации водоотталкивающей пропитки C0 DWR.",
        "anti_slop_rule": "Specify wash interval, Celsius temperature, banned additive (softener), and 20-min DWR heat step."
    },
    {
        "id": "faq_015", "category": "aeo_faq_answer", "domain": "server_hardware", "canon_id": "18_bento_hardware_showcase",
        "en_slop_before": "Firmware updates are open and secure on every compute sled.",
        "en_canon_after": "Every compute sled boots open-source coreboot + LinuxBoot firmware measured into discrete SPI Root-of-Trust silicon; operators can audit, compile, and sign their own firmware images offline.",
        "ru_slop_before": "Обновления прошивки на наших серверах полностью открыты и безопасны.",
        "ru_canon_after": "Каждый вычислительный модуль загружает открытую прошивку coreboot и LinuxBoot с криптографической сверкой через дискретный аппаратный корень доверия SPI, позволяя заказчику самостоятельно собирать и подписывать образы офлайн.",
        "anti_slop_rule": "Name firmware stack (coreboot + LinuxBoot), hardware RoT, and customer self-signing right."
    },
    {
        "id": "faq_016", "category": "aeo_faq_answer", "domain": "grid_storage", "canon_id": "17_sustainable_climate_botanical",
        "en_slop_before": "Our battery systems are built to last safely for many years.",
        "en_canon_after": "Prismatic lithium-iron-phosphate (LiFePO4) cells retain >= 80% nameplate energy capacity after 7,000 cycles at 0.5C and pass UL 9540A cell-to-cell thermal-runaway propagation testing without flaming ejection.",
        "ru_slop_before": "Наши аккумуляторные системы рассчитаны на долгие годы безопасной эксплуатации.",
        "ru_canon_after": "Призматические литий-железо-фосфатные ячейки LiFePO4 сохраняют не менее 80% номинальной ёмкости после 7000 циклов при токе 0,5C и проходят испытания UL 9540A на нераспространение теплового разгона.",
        "anti_slop_rule": "State cycle life (7,000), C-rate, state-of-health floor (80%), and UL 9540A test."
    },
    {
        "id": "faq_017", "category": "aeo_faq_answer", "domain": "geospatial_lidar", "canon_id": "24_cartographic_field_expedition",
        "en_slop_before": "Deliverables work smoothly with all major engineering CAD tools.",
        "en_canon_after": "Survey packages ship in non-proprietary LAZ 1.4 point clouds, Cloud-Optimized GeoTIFF (COG) 32-bit DEM rasters, and DXF breakline contours referenced to your specified EPSG vertical and horizontal datums.",
        "ru_slop_before": "Результаты съёмки легко открываются во всех популярных инженерных САПР.",
        "ru_canon_after": "Камеральный пакет сдаётся в открытых форматах облаков точек LAZ 1.4, высотных матриц Cloud-Optimized GeoTIFF 32-bit и структурных линий DXF в заданной системе координат и высот по коду EPSG.",
        "anti_slop_rule": "List exact open file formats (LAZ 1.4, COG 32-bit, DXF) and EPSG datum binding."
    },
    {
        "id": "faq_018", "category": "aeo_faq_answer", "domain": "legal_arbitration", "canon_id": "22_legal_advisory_chancery",
        "en_slop_before": "We offer transparent billing models tailored to client needs.",
        "en_canon_after": "Pre-filing merger-control assessments and standard SHA drafting are billed on capped fixed-phase fees agreed upfront in the engagement letter, while contested Phase-II proceedings follow itemized partner/associate hourly caps.",
        "ru_slop_before": "Мы предлагаем прозрачные условия оплаты с учётом потребностей каждого доверителя.",
        "ru_canon_after": "Предварительный антимонопольный анализ и подготовка акционерного соглашения тарифицируются по твёрдой поэтапной ставке в письме о поручении, а сопровождение углублённых разбирательств ограничено верхним потолком почасовых ставок.",
        "anti_slop_rule": "Distinguish fixed-fee phases from capped hourly phases explicitly."
    },
    {
        "id": "faq_019", "category": "aeo_faq_answer", "domain": "horology_service", "canon_id": "16_luxury_horology_atelier_dark",
        "en_slop_before": "Regular servicing keeps your mechanical timepiece running beautifully.",
        "en_canon_after": "Caliber K-04 requires full ultrasonic movement disassembly, synthetic epilame lubrication, and gasket replacement every 6 to 7 years at a published tariff of CHF 680 including 24-month service warranty.",
        "ru_slop_before": "Регулярное обслуживание позволит вашим механическим часам служить поколениями.",
        "ru_canon_after": "Калибр K-04 требует полной ультразвуковой мойки ангренажа, нанесения синтетической смазки с эпиламом и замены уплотнений раз в 6-7 лет по открытому прейскуранту с гарантией 24 месяца на работы.",
        "anti_slop_rule": "State year interval, exact horological operations, published price, and service warranty months."
    },
    {
        "id": "faq_020", "category": "aeo_faq_answer", "domain": "hospitality_allergens", "canon_id": "11_warm_artisan_hospitality",
        "en_slop_before": "Our kitchen is happy to accommodate dietary preferences whenever possible.",
        "en_canon_after": "The seven-course autumn tasting menu can be prepared celiac-safe gluten-free or pescatarian with 24 hours advance notice on your reservation; severe allium or dairy anaphylaxis cannot be accommodated due to shared stock reductions.",
        "ru_slop_before": "Наша кухня с радостью учтёт ваши вкусовые предпочтения и аллергии при визите.",
        "ru_canon_after": "Осенний дегустационный сет из семи подач готовится в безглютеновой или пескетарианской версии при предупреждении за 24 часа в форме бронирования, однако при тяжёлой анафилаксии на молочный белок и лук замена невозможна из-за базовых соусов.",
        "anti_slop_rule": "Be honest about both what CAN and CANNOT be safely accommodated, plus notice hours."
    },
    {
        "id": "faq_021", "category": "aeo_faq_answer", "domain": "quant_historical_ticks", "canon_id": "19_quant_analytics_dense_terminal",
        "en_slop_before": "Historical market data goes back many years with clean formatting.",
        "en_canon_after": "Full-depth ITCH/OUCH and CME MDP 3.0 PCAP-derived Parquet archives cover January 2018 through yesterday (T-1 23:59 UTC), adjusted for corporate splits and symbol Ticker-to-FIGI lineage.",
        "ru_slop_before": "Исторические биржевые данные доступны за много лет в удобном очищенном виде.",
        "ru_canon_after": "Полные архивы стакана из первичных дампов PCAP в формате Parquet охватывают период с января 2018 года по вчерашнюю сессию T-1 (23:59 UTC) со сквозной привязкой тикеров к идентификаторам FIGI и учётом дробления бумаг.",
        "anti_slop_rule": "State feed protocols, start month/year, T-1 cutoff, and FIGI corporate-action lineage."
    },

    # === CATEGORY 6: ux_microcopy_state (21 pairs) ===
    {
        "id": "ux_001", "category": "ux_microcopy_state", "domain": "form_validation", "canon_id": "15_high_contrast_civic_gov_wcag_aaa",
        "en_slop_before": "Oops! Invalid input. Please try again.",
        "en_canon_after": "Enter a 10-digit tax ID containing digits only (example: 7707083893). Spaces and hyphens are stripped automatically.",
        "ru_slop_before": "Ой! Поле заполнено неверно. Попробуйте ещё раз.",
        "ru_canon_after": "Введите 10 цифр ИНН организации без букв (пример: 7707083893). Пробелы и дефисы удаляются автоматически.",
        "anti_slop_rule": "Never blame the user with 'Invalid input'; state exact digit count, concrete example, and auto-formatting behavior."
    },
    {
        "id": "ux_002", "category": "ux_microcopy_state", "domain": "empty_state_traces", "canon_id": "03_dark_precision_saas_linear",
        "en_slop_before": "Nothing to see here yet! Start sending data to unlock magic.",
        "en_canon_after": "0 spans received in the last 15 minutes for environment `prod-eu`. Run `chronotrace doctor --endpoint localhost:4317` to verify OTLP gRPC connectivity.",
        "ru_slop_before": "Здесь пока пусто! Отправьте первые данные, чтобы увидеть аналитику.",
        "ru_canon_after": "За последние 15 минут из окружения `prod-eu` не поступило ни одного спана. Выполните `chronotrace doctor --endpoint localhost:4317` для проверки соединения OTLP gRPC.",
        "anti_slop_rule": "Turn empty states into diagnostic status + exact copy-paste verification command."
    },
    {
        "id": "ux_003", "category": "ux_microcopy_state", "domain": "rate_limit_429", "canon_id": "09_monospace_cli_devtools",
        "en_slop_before": "Whoa, slow down! Too many requests right now.",
        "en_canon_after": "HTTP 429: Token bucket exhausted (600 req/min limit for key `ak_live_9f2a`). Next slot opens in 4.2 seconds (`Retry-After: 5`).",
        "ru_slop_before": "Подождите немного! Слишком много запросов к серверу.",
        "ru_canon_after": "Код 429: исчерпан лимит 600 запросов/мин для ключа `ak_live_9f2a`. Следующее окно откроется через 4,2 с (заголовок `Retry-After: 5`).",
        "anti_slop_rule": "Report quota ceiling, masked key prefix, and exact seconds until retry."
    },
    {
        "id": "ux_004", "category": "ux_microcopy_state", "domain": "offline_sync_banner", "canon_id": "02_neo_brutalism_tactile",
        "en_slop_before": "You are offline. Some features might not work properly.",
        "en_canon_after": "Offline mode: 14 local edits saved to IndexedDB WAL. Changes will sync automatically when network reachability returns.",
        "ru_slop_before": "Нет подключения к сети. Часть функций может быть недоступна.",
        "ru_canon_after": "Автономный режим: 14 локальных правок записаны в журнал IndexedDB WAL и отправятся автоматически при появлении сети.",
        "anti_slop_rule": "Reassure with exact queued edit count and storage durability location."
    },
    {
        "id": "ux_005", "category": "ux_microcopy_state", "domain": "destructive_delete", "canon_id": "27_cybersecurity_zero_trust_ops",
        "en_slop_before": "Are you sure you want to delete this item?",
        "en_canon_after": "Revoke signing key `ed25519:4b81`? 3 active CI runners authenticating with this key will fail deploys immediately. This action cannot be undone.",
        "ru_slop_before": "Вы уверены, что хотите удалить этот элемент?",
        "ru_canon_after": "Отозвать ключ подписи `ed25519:4b81`? Три активных сборочных агента CI мгновенно потеряют доступ к выкладке. Отменить отзыв невозможно.",
        "anti_slop_rule": "Name the exact resource ID, blast-radius count (3 active CI runners), and irreversibility."
    },
    {
        "id": "ux_006", "category": "ux_microcopy_state", "domain": "password_passkey", "canon_id": "15_high_contrast_civic_gov_wcag_aaa",
        "en_slop_before": "Password does not meet complexity rules.",
        "en_canon_after": "Use at least 14 characters (paste from your password manager is enabled, and no special-symbol gymnastics are required), or register a hardware passkey.",
        "ru_slop_before": "Пароль не соответствует требованиям сложности системы.",
        "ru_canon_after": "Введите минимум 14 символов (вставка из менеджера паролей разрешена, обязательных спецсимволов нет) либо привяжите аппаратный ключ Passkey.",
        "anti_slop_rule": "Follow WCAG 2.2 3.3.8 + NIST SP 800-63B: allow paste, length >=14, passkeys."
    },
    {
        "id": "ux_007", "category": "ux_microcopy_state", "domain": "payment_wire_cutoff", "canon_id": "08_fintech_institutional_ledger",
        "en_slop_before": "Your transfer is being processed and will arrive soon.",
        "en_canon_after": "Submitted at 16:42 CET (past the 16:00 SEPA same-day cutoff). Settlement scheduled for Tuesday, 17 Nov at 08:30 CET; UETR reference `91f4-88c2`.",
        "ru_slop_before": "Ваш перевод успешно принят в обработку и скоро поступит получателю.",
        "ru_canon_after": "Платёж принят в 16:42 МСК после закрытия дневного рейса 16:00. Зачисление пройдёт во вторник, 17 ноября, в 08:30 МСК; код отслеживания `91f4-88c2`.",
        "anti_slop_rule": "State cutoff reason, exact next settlement date/time, and tracking reference."
    },
    {
        "id": "ux_008", "category": "ux_microcopy_state", "domain": "file_upload_dropzone", "canon_id": "24_cartographic_field_expedition",
        "en_slop_before": "Drop your files here to upload.",
        "en_canon_after": "Drop `.laz`, `.las`, or `.tif` survey files up to 4 GB each. SHA-256 checksum and EPSG header are verified locally in your browser before upload starts.",
        "ru_slop_before": "Перетащите файлы в эту область для загрузки на сервер.",
        "ru_canon_after": "Перетащите файлы съёмки `.laz`, `.las` или `.tif` объёмом до 4 ГБ. Контрольная сумма SHA-256 и заголовок EPSG проверяются локально в браузере до отправки.",
        "anti_slop_rule": "List extensions, max GB size, and client-side preflight check."
    },
    {
        "id": "ux_009", "category": "ux_microcopy_state", "domain": "pricing_annual_toggle", "canon_id": "01_swiss_international_typographic",
        "en_slop_before": "Save Big With Annual!",
        "en_canon_after": "Annual billing ($40/seat/mo billed $480 yearly, saves 2 months vs $48 monthly)",
        "ru_slop_before": "Выгодная годовая подписка!",
        "ru_canon_after": "Годовая оплата (3800 ₽ за место в месяц, счёт 45 600 ₽ на год, экономия 2 месяцев)",
        "anti_slop_rule": "Show exact monthly equivalent, total annual invoice charge, and exact savings math."
    },
    {
        "id": "ux_010", "category": "ux_microcopy_state", "domain": "honeypot_privacy_note", "canon_id": "22_legal_advisory_chancery",
        "en_slop_before": "We value your privacy and never spam.",
        "en_canon_after": "Protected without third-party CAPTCHA trackers. Your inquiry goes straight to our intake desk over TLS 1.3 and is purged after 90 days if no engagement is opened.",
        "ru_slop_before": "Мы бережно относимся к вашим персональным данным и не рассылаем спам.",
        "ru_canon_after": "Форма защищена без сторонних трекеров и капчи. Заявка поступает напрямую дежурному партнёру по TLS 1.3 и удаляется через 90 суток, если договор не заключён.",
        "anti_slop_rule": "Highlight zero-tracker anti-spam and concrete 90-day non-engagement purge."
    },
    {
        "id": "ux_011", "category": "ux_microcopy_state", "domain": "search_no_results", "canon_id": "10_scientific_documentation_tufte",
        "en_slop_before": "Sorry, we couldn't find anything matching your search.",
        "en_canon_after": "0 entries matched `\"eigenvalue clamp\"` across 284 monographs. Try stem query `eigenvalue` or browse §4 Numerical Stability (`19` notes).",
        "ru_slop_before": "К сожалению, по вашему запросу ничего не найдено.",
        "ru_canon_after": "По точной фразе `«ограничение спектра»` в 284 статьях совпадений нет. Снимите кавычки или откройте раздел §4 «Численная устойчивость» (19 заметок).",
        "anti_slop_rule": "Echo the exact query, corpus count, why it missed (exact phrase quotes), and a populated fallback section."
    },
    {
        "id": "ux_012", "category": "ux_microcopy_state", "domain": "export_csv_progress", "canon_id": "19_quant_analytics_dense_terminal",
        "en_slop_before": "Please wait while we prepare your download...",
        "en_canon_after": "Streaming partition 6 of 8 (1.42M rows, 68 MB Zstd Parquet). Keep this tab open (~3 seconds remaining).",
        "ru_slop_before": "Пожалуйста, подождите, идёт подготовка вашего файла...",
        "ru_canon_after": "Выгрузка партиции 6 из 8 (1,42 млн строк, 68 МБ Parquet Zstd). Не закрывайте вкладку, осталось около 3 секунд.",
        "anti_slop_rule": "Show partition counter, row count, MB size, and remaining seconds."
    },
    {
        "id": "ux_013", "category": "ux_microcopy_state", "domain": "cookie_zero_banner", "canon_id": "27_cybersecurity_zero_trust_ops",
        "en_slop_before": "We use cookies to enhance your browsing experience. Accept All.",
        "en_canon_after": "Zero tracking cookies, zero ad pixels, zero cross-site scripts: no consent banner required.",
        "ru_slop_before": "Мы используем файлы cookie для улучшения работы сайта.",
        "ru_canon_after": "Сайт работает без рекламных пикселей, сторонних скриптов и аналитических cookie.",
        "anti_slop_rule": "Eliminate cookie-banner bloat entirely by running zero tracking cookies."
    },
    {
        "id": "ux_014", "category": "ux_microcopy_state", "domain": "calibration_slider", "canon_id": "23_audio_dsp_modular_rack",
        "en_slop_before": "Adjust threshold setting.",
        "en_canon_after": "Limiter Ceiling: -1.0 dBTP (ITU-R BS.1770-4 streaming true-peak safe)",
        "ru_slop_before": "Настройте уровень порога срабатывания.",
        "ru_canon_after": "Потолок лимитера: -1,0 dBTP (запас истинного пика по стандарту ITU-R BS.1770-4)",
        "anti_slop_rule": "Include exact engineering unit (dBTP) and broadcast standard reference."
    },
    {
        "id": "ux_015", "category": "ux_microcopy_state", "domain": "stock_low_honest", "canon_id": "26_ecommerce_lookbook_grid",
        "en_slop_before": "Hurry! Selling fast! 14 people are looking at this right now!",
        "en_canon_after": "Size L: 3 jackets in Tallinn warehouse (ships today). Next production batch arrives 12 December.",
        "ru_slop_before": "Торопитесь! Сейчас этот товар смотрят ещё 14 человек!",
        "ru_canon_after": "Размер L: 3 куртки на складе в Твери (отгрузка сегодня). Следующая партия поступит из пошивочного цеха 12 декабря.",
        "anti_slop_rule": "Replace dark-pattern viewer counters with verifiable warehouse stock + restock date."
    },
    {
        "id": "ux_016", "category": "ux_microcopy_state", "domain": "specimen_rejection", "canon_id": "12_clinical_biotech_cleanroom",
        "en_slop_before": "Sample error detected.",
        "en_canon_after": "Accession #88412 flagged: hemolysis index H=4 exceeds assay ceiling (H<=2). Request redraw in lavender-top K2-EDTA 4 mL tube at zero repeat charge.",
        "ru_slop_before": "Обнаружена ошибка биоматериала.",
        "ru_canon_after": "Проба №88412 отклонена: индекс гемолиза H=4 превышает порог методики (H<=2). Оформите бесплатный перезабор в пробирку K2-ЭДТА 4 мл с сиреневой крышкой.",
        "anti_slop_rule": "Give quantitative rejection threshold, required tube cap/anticoagulant, and zero-fee redraw."
    },
    {
        "id": "ux_017", "category": "ux_microcopy_state", "domain": "keyboard_shortcut_hint", "canon_id": "20_spatial_glass_dark_instrument",
        "en_slop_before": "Pro tip: use shortcuts to navigate faster!",
        "en_canon_after": "Press `1`-`3` to switch latency percentiles, `/` to filter services, or `Esc` to clear selection.",
        "ru_slop_before": "Совет: используйте горячие клавиши для быстрой навигации!",
        "ru_canon_after": "Клавиши `1`-`3` переключают перцентили задержки, `/` фокусирует фильтр сервисов, `Esc` сбрасывает выбор.",
        "anti_slop_rule": "List exact bound keys and actions directly without 'Pro tip!' fluff."
    },
    {
        "id": "ux_018", "category": "ux_microcopy_state", "domain": "brew_calculator_out", "canon_id": "28_craft_roastery_packaging",
        "en_slop_before": "Recommended coffee recipe calculated.",
        "en_canon_after": "18.0 g dose -> 300 ml water at 94 C (1:16.7 ratio; pour 50 ml bloom at 0:00, two 125 ml pulses at 0:40 and 1:25, target drawdown 2:45).",
        "ru_slop_before": "Рекомендуемый рецепт заваривания рассчитан.",
        "ru_canon_after": "18,0 г зерна -> 300 мл воды при 94 C (пропорция 1:16,7: предсмачивание 50 мл на 0:00, два вливания по 125 мл на 0:40 и 1:25, общее время 2:45).",
        "anti_slop_rule": "Output actionable gram/ml/Celsius/timestamp steps."
    },
    {
        "id": "ux_019", "category": "ux_microcopy_state", "domain": "thermal_derating_warn", "canon_id": "07_industrial_functional_instrument",
        "en_slop_before": "Warning: High temperature.",
        "en_canon_after": "WARN [CH-03]: Enclosure ambient reached 68.4 C (derating threshold 65.0 C). PoE+ budget capped to 60 W until cabinet temperature drops below 60.0 C.",
        "ru_slop_before": "Внимание: превышена температура устройства.",
        "ru_canon_after": "ПРЕДУПРЕЖДЕНИЕ [CH-03]: температура в шкафу достигла 68,4 C (порог снижения мощности 65,0 C). Бюджет PoE+ ограничен до 60 Вт до остывания ниже 60,0 C.",
        "anti_slop_rule": "Include text severity prefix (`WARN`), sensor reading, threshold, automatic protective action, and hysteresis reset."
    },
    {
        "id": "ux_020", "category": "ux_microcopy_state", "domain": "reduced_motion_badge", "canon_id": "14_kinetic_cultural_exhibition",
        "en_slop_before": "Animations paused.",
        "en_canon_after": "OS Reduced Motion detected: kinetic gallery transitions disabled; static high-contrast floor index active.",
        "ru_slop_before": "Анимации отключены.",
        "ru_canon_after": "Обнаружена системная настройка снижения движения: переходы отключены, включён статический указатель залов.",
        "anti_slop_rule": "Acknowledge OS `prefers-reduced-motion` respectfully and confirm full functional parity."
    },
    {
        "id": "ux_021", "category": "ux_microcopy_state", "domain": "bibtex_copied", "canon_id": "25_academic_journal_monograph",
        "en_slop_before": "Copied!",
        "en_canon_after": "Copied BibTeX entry (`@article{kuznetsov2026rco}`, 8 lines) + artifact SHA-256 to clipboard.",
        "ru_slop_before": "Скопировано!",
        "ru_canon_after": "Карточка BibTeX (`@article{kuznetsov2026rco}`, 8 строк) и контрольная сумма SHA-256 скопированы в буфер.",
        "anti_slop_rule": "Confirm exact citation key and payload copied."
    },

    # === CATEGORY 7: editorial_lead (21 pairs) ===
    {
        "id": "ed_001", "category": "editorial_lead", "domain": "swiss_grid_history", "canon_id": "01_swiss_international_typographic",
        "en_slop_before": "In today's fast-paced digital world, typography plays a crucial role in creating seamless user experiences.",
        "en_canon_after": "When Josef Muller-Brockmann drafted the Zurich Tonhalle concert posters in 1955, every type size and column gutter derived from a single integer module of the sheet's short edge.",
        "ru_slop_before": "В современном динамично развивающемся цифровом мире типографика играет важнейшую роль в создании интерфейсов.",
        "ru_canon_after": "Когда Йозеф Мюллер-Брокман чертил афиши для цюрихского зала Тонхалле в 1955 году, каждый кегль и межколонник выводились из единого целочисленного модуля короткой стороны листа.",
        "anti_slop_rule": "Cut throat-clearing 'In today's world'; open on a dated historical scene and concrete geometric rule."
    },
    {
        "id": "ed_002", "category": "editorial_lead", "domain": "timber_acoustics", "canon_id": "05_nordic_architectural_minimal",
        "en_slop_before": "Let's delve into the fascinating intersection of architecture and sound design.",
        "en_canon_after": "Poured concrete and triple-glazed curtain walls give northern daylight halls crisp thermal envelopes while stretching mid-frequency speech decay past 1.9 seconds.",
        "ru_slop_before": "Давайте погрузимся в удивительный мир архитектурной акустики современных общественных зданий.",
        "ru_canon_after": "Монолитный бетон и трёхкамерное панорамное остекление берегут тепло в северных залах, но растягивают затухание речевых частот за отметку 1,9 секунды.",
        "anti_slop_rule": "Never write 'Let's delve / Погрузимся'; open directly with the physical tension and measured seconds."
    },
    {
        "id": "ed_003", "category": "editorial_lead", "domain": "flash_translation_layer", "canon_id": "09_monospace_cli_devtools",
        "en_slop_before": "Modern SSDs are marvels of engineering that power the cloud revolution.",
        "en_canon_after": "Every 4 KB random overwrite on a TLC NAND drive forces the flash translation layer to relocate valid pages before erasing a multi-megabyte block, turning steady sequential bandwidth into 18 ms tail-latency spikes.",
        "ru_slop_before": "Современные твердотельные накопители стали настоящим чудом инженерной мысли в эпоху облаков.",
        "ru_canon_after": "Каждая случайная перезапись блока 4 КБ на чипах TLC NAND заставляет транслятор адресов переносить живые страницы перед стиранием мегабайтного блока, превращая ровную полосу пропускания в пики задержки по 18 мс.",
        "anti_slop_rule": "Start directly inside the hardware mechanism causing tail latency."
    },
    {
        "id": "ed_004", "category": "editorial_lead", "domain": "broadsheet_economics", "canon_id": "04_editorial_broadsheet_serif",
        "en_slop_before": "Global supply chains are evolving rapidly amidst unprecedented transformation.",
        "en_canon_after": "Three transformer factories in Vaasa, Linz, and Changzhou now hold 38-month order backlogs for 400 kV grain-oriented silicon-steel cores, setting the hard ceiling on European grid interconnection.",
        "ru_slop_before": "Глобальные цепочки поставок стремительно меняются в условиях беспрецедентных вызовов.",
        "ru_canon_after": "Три трансформаторных завода в Ваасе, Линце и Чанчжоу расписали квоты на сердечники из анизотропной электротехнической стали 400 кВ на 38 месяцев вперёд, задав жёсткий предел ввода новых подстанций.",
        "anti_slop_rule": "Name the three cities, voltage rating, alloy, and month backlog in sentence one."
    },
    {
        "id": "ed_005", "category": "editorial_lead", "domain": "ma_ceramics", "canon_id": "06_japanese_ma_wabi_editorial",
        "en_slop_before": "Minimalism is more than just a style; it is a timeless philosophy of simplicity.",
        "en_canon_after": "Unwashed Shigaraki feldspar clay vitrifies unevenly at 1,280 C in a wood-fired anagama tunnel, leaving quartz grains proud of the rim where wood ash settles naturally.",
        "ru_slop_before": "Минимализм давно перестал быть просто стилем и превратился в вечную философию простоты.",
        "ru_canon_after": "Неотмученная полевошпатовая глина Сигараки спекается неравномерно при 1280 C в дровяной печи анагама, оставляя зёрна кварца на кромке там, где оседает летучая зола.",
        "anti_slop_rule": "Replace 'philosophy of simplicity' clichés with mineral, kiln temperature, and firing physics."
    },
    {
        "id": "ed_006", "category": "editorial_lead", "domain": "tufte_sparklines", "canon_id": "10_scientific_documentation_tufte",
        "en_slop_before": "Data visualization has become increasingly important for making smart decisions.",
        "en_canon_after": "An ICU bedside chart printing a single glucose number (`142 mg/dL`) without its 24-hour trajectory hides whether insulin resistance is stabilizing or accelerating at 18 mg/dL per hour.",
        "ru_slop_before": "Визуализация данных приобретает всё большее значение для принятия взвешенных решений.",
        "ru_canon_after": "Реанимационный лист с одиночной цифрой глюкозы `7,9 ммоль/л` без суточной кривой скрывает главное: стабилизируется ли пациент или показатель растёт со скоростью 1,0 ммоль/л в час.",
        "anti_slop_rule": "Demonstrate why visualization matters through a single high-stakes clinical number vs slope."
    },
    {
        "id": "ed_007", "category": "editorial_lead", "domain": "fermentation_terroir", "canon_id": "11_warm_artisan_hospitality",
        "en_slop_before": "At our restaurant, passion for local ingredients meets culinary innovation.",
        "en_canon_after": "Rye milled 40 kilometers east of Pskov carries wild *Kazachstania humilis* yeasts that stall below 24 C, requiring cast-iron proof boxes held at 27.5 C before dawn bake.",
        "ru_slop_before": "В нашем ресторане любовь к локальным фермерским продуктам встречается с кулинарными инновациями.",
        "ru_canon_after": "Озимая рожь помола из-под Пскова несёт дикие дрожжи *Kazachstania humilis*, которые засыпают ниже 24 C и требуют расстойки при 27,5 C за четыре часа до утренней выпечки.",
        "anti_slop_rule": "Ground culinary prose in grain origin, microbiology, and exact proofing temperature."
    },
    {
        "id": "ed_008", "category": "editorial_lead", "domain": "constructivist_truss", "canon_id": "21_constructivist_editorial_ru",
        "en_slop_before": "Russian engineering heritage is a rich tapestry of bold architectural achievements.",
        "en_canon_after": "Vladimir Shukhov covered the 1896 Nizhny Novgorod exhibition pavilions with doubly curved steel tension-strips 5 millimeters thick, cutting roof dead-weight per square meter to one-third of contemporary riveted arches.",
        "ru_slop_before": "Инженерное наследие представляет собой богатое полотно смелых архитектурных достижений.",
        "ru_canon_after": "В 1896 году Владимир Шухов перекрыл павильоны Всероссийской выставки в Нижнем Новгороде двояковыпуклой сеткой из стальных полос толщиной 5 мм, снизив металлоёмкость кровли втрое против клёпаных арок.",
        "anti_slop_rule": "Ban 'rich tapestry'; cite year, city, 5 mm strip geometry, and 3x weight ratio."
    },
    {
        "id": "ed_009", "category": "editorial_lead", "domain": "oklch_color_science", "canon_id": "03_dark_precision_saas_linear",
        "en_slop_before": "Choosing colors in web design used to be hard until modern CSS arrived.",
        "en_canon_after": "In legacy `hsl()`, setting `50%` lightness yields a glaring `0.88` relative luminance in yellow (`hsl(60 100% 50%)`) next to a murky `0.07` in royal blue (`hsl(240 100% 50%)`), breaking badge contrast whenever hues rotate.",
        "ru_slop_before": "Подбор цветовой палитры для интерфейсов долгое время оставался непростой задачей для дизайнеров.",
        "ru_canon_after": "В старом пространстве `hsl()` одинаковая светлота `50%` даёт слепящую относительную яркость `0,88` на жёлтом тоне и глухие `0,07` на синем, ломая контраст текста при любой смене оттенка.",
        "anti_slop_rule": "Show the exact mathematical bug in `hsl()` luminance (0.88 vs 0.07) that motivates `oklch()`."
    },
    {
        "id": "ed_010", "category": "editorial_lead", "domain": "horology_escapement", "canon_id": "16_luxury_horology_atelier_dark",
        "en_slop_before": "Every mechanical watch tells a story of passion and artistry.",
        "en_canon_after": "At 21,600 vibrations per hour, a Swiss lever pallet fork unlocks and locks the escape wheel 518,400 times every day, sliding synthetic corundum across a 0.14 mm oil film.",
        "ru_slop_before": "Каждые механические часы рассказывают удивительную историю страсти и высокого искусства.",
        "ru_canon_after": "На частоте 21 600 полуколебаний в час анкерная вилка освобождает и запирает спусковое колесо 518 400 раз за сутки, скользя синтетическим корундом по масляной плёнке толщиной 0,14 мм.",
        "anti_slop_rule": "Count the daily impulses (518,400) and film thickness (0.14 mm) instead of 'passion and artistry'."
    },
    {
        "id": "ed_011", "category": "editorial_lead", "domain": "zero_trust_perimeter", "canon_id": "27_cybersecurity_zero_trust_ops",
        "en_slop_before": "Traditional castle-and-moat security is dead in the era of hybrid work.",
        "en_canon_after": "Once a single developer laptop joins a flat `/16` corporate VPN subnet, any compromised npm postinstall script inherits lateral TCP reachability to staging databases and internal Jenkins runners.",
        "ru_slop_before": "Традиционная периметровая защита окончательно устарела в эпоху гибридной удалённой работы.",
        "ru_canon_after": "Как только ноутбук разработчика получает адрес в плоской корпоративной VPN-подсети `/16`, любой заражённый скрипт установки пакета обретает прямую TCP-видимость тестовых баз и сборочных узлов.",
        "anti_slop_rule": "Replace 'castle-and-moat is dead' cliche with concrete `/16` subnet lateral-movement vector."
    },
    {
        "id": "ed_012", "category": "editorial_lead", "domain": "civic_plain_language", "canon_id": "15_high_contrast_civic_gov_wcag_aaa",
        "en_slop_before": "Digital transformation in government starts with putting citizens first.",
        "en_canon_after": "Rewriting a four-page municipal housing-subsidy instruction from 38-word passive statutory clauses into eight numbered verb-led steps cut walk-in counter inquiries by 52% in one quarter.",
        "ru_slop_before": "Цифровая трансформация госуслуг начинается с заботы об удобстве каждого гражданина.",
        "ru_canon_after": "Перевод четырёхстраничной памятки о жилищной субсидии с канцелярских причастных оборотов по 38 слов на восемь глагольных шагов сократил очередь очных обращений в МФЦ на 52% за квартал.",
        "anti_slop_rule": "Prove plain-language impact with sentence word length and counter-visit reduction."
    },
    {
        "id": "ed_013", "category": "editorial_lead", "domain": "bauhaus_stage", "canon_id": "13_bauhaus_geometric_poster",
        "en_slop_before": "The Bauhaus school changed modern design forever with its bold vision.",
        "en_canon_after": "In Dessau's 1926 workshop wing, Herbert Bayer banished capital letters from studio syllabi on the grounds that printing two alphabets doubled typesetting case weight without adding a single phoneme.",
        "ru_slop_before": "Школа Баухаус навсегда изменила облик современного дизайна благодаря смелому видению.",
        "ru_canon_after": "В дессауских мастерских 1926 года Герберт Байер убрал прописные литеры из учебных бланков, доказав, что содержание двух касс удваивает расход свинца без добавления ни одной новой фонемы.",
        "anti_slop_rule": "Cite specific designer, year, physical typesetting constraint, and linguistic argument."
    },
    {
        "id": "ed_014", "category": "editorial_lead", "domain": "coffee_postharvest", "canon_id": "28_craft_roastery_packaging",
        "en_slop_before": "Great coffee begins its journey high in the misty mountain farms.",
        "en_canon_after": "Submerging depulped Caturra cherry in sealed 200-liter HDPE tanks at 18 C extends lactic mucilage breakdown to 48 hours without letting acetic bacteria sour the parchment.",
        "ru_slop_before": "Путь великолепного кофе начинается высоко на туманных горных плантациях.",
        "ru_canon_after": "Погружение депульпированной ягоды Катурры в герметичные 200-литровые ёмкости при 18 C растягивает молочнокислую ферментацию клейковины до 48 часов, не давая уксусным бактериям окислить зерно.",
        "anti_slop_rule": "Replace 'misty mountain journey' with fermentation vessel, Celsius control, and lactic vs acetic chemistry."
    },
    {
        "id": "ed_015", "category": "editorial_lead", "domain": "geodesy_elevation", "canon_id": "24_cartographic_field_expedition",
        "en_slop_before": "Maps have guided explorers for centuries, and today's digital maps are smarter than ever.",
        "en_canon_after": "Sea level at Kronstadt and sea level at Amsterdam differ from the WGS84 mathematical ellipsoid by locally varying gravity undulations of up to 29 meters, which is why raw GNSS heights flood storm drains if treated as orthometric elevation.",
        "ru_slop_before": "Карты веками вели первооткрывателей, а современные цифровые атласы стали умнее, чем когда-либо.",
        "ru_canon_after": "Балтийская система высот от Кронштадтского футштока расходится с математическим эллипсоидом WGS84 на величину гравитационной волны геоида до 29 метров, поэтому сырые спутниковые отметки разворачивают уклон ливневой канализации вспять.",
        "anti_slop_rule": "Open with geoid undulation physics (29 m) and engineering failure consequence."
    },
    {
        "id": "ed_016", "category": "editorial_lead", "domain": "moe_routing_physics", "canon_id": "25_academic_journal_monograph",
        "en_slop_before": "Mixture-of-Experts models are revolutionizing artificial intelligence scalability.",
        "en_canon_after": "Activating 10 routed experts out of 512 per token cuts FLOPs per forward pass by 28x, yet leaves all 512 expert weight tensors contending for PCIe and DRAM capacity unless inactive domain tails are pruned offline.",
        "ru_slop_before": "Архитектура разреженных экспертов совершает настоящую революцию в масштабировании нейросетей.",
        "ru_canon_after": "Активация 10 маршрутизируемых экспертов из 512 на каждый токен снижает число операций в 28 раз, однако все 512 матриц весов продолжают занимать объём ОЗУ и шину PCIe без офлайн-отсечения неиспользуемых ветвей.",
        "anti_slop_rule": "Contrast FLOP savings (28x) with static DRAM residency bottleneck."
    },
    {
        "id": "ed_017", "category": "editorial_lead", "domain": "bento_power_bus", "canon_id": "18_bento_hardware_showcase",
        "en_slop_before": "Modern data centers require innovative rack designs for peak performance.",
        "en_canon_after": "Delivering 36 kW down a server rack at 12 volts DC requires 3,000 amperes of copper busbar current and loses quadruple the resistive I2R heat of a 48-volt blind-mate backplane.",
        "ru_slop_before": "Современные дата-центры требуют инновационной конструкции стоек для максимальной отдачи.",
        "ru_canon_after": "Передача 36 кВт по серверной стойке на напряжении 12 В постоянного тока требует тока 3000 А в медной шине и даёт вчетверо больше омических потерь I2R, чем слепая стыковка на 48 В.",
        "anti_slop_rule": "Lead with Ohm/Joule heating math (36 kW, 3,000 A, 4x I2R loss)."
    },
    {
        "id": "ed_018", "category": "editorial_lead", "domain": "orderbook_queue", "canon_id": "19_quant_analytics_dense_terminal",
        "en_slop_before": "High-frequency financial markets move in the blink of an eye.",
        "en_canon_after": "On price-time priority matching engines, arriving 4 microseconds behind the top-of-book quote reload shifts fill probability on passive 1-tick maker orders from 64% to 11% due to adverse selection.",
        "ru_slop_before": "Современные финансовые рынки меняются буквально за доли мгновения.",
        "ru_canon_after": "В биржевом ядре с приоритетом цены и времени опоздание на 4 микросекунды к обновлению лучшей котировки роняет вероятность исполнения пассивной лимитной заявки без неблагоприятного отбора с 64% до 11%.",
        "anti_slop_rule": "Replace 'blink of an eye' with 4 microseconds and exact adverse-selection fill probabilities."
    },
    {
        "id": "ed_019", "category": "editorial_lead", "domain": "biennale_pavilion", "canon_id": "14_kinetic_cultural_exhibition",
        "en_slop_before": "This landmark exhibition invites visitors on an unforgettable journey through space.",
        "en_canon_after": "Fourteen dry-stacked limestone arches span Hall B without mortar, held in compression solely by a 1.8-ton tensioned steel tie-rod anchored to two reversible cast-iron floor shoes.",
        "ru_slop_before": "Эта знаковая выставка приглашает зрителей в незабываемое путешествие сквозь пространство.",
        "ru_canon_after": "Четырнадцать арок из сухой кладки известняка перекрывают Павильон Б без капли раствора, работая на чистое сжатие за счёт стальной затяжки усилием 1,8 тонны на двух съёмных башмаках.",
        "anti_slop_rule": "Ban 'unforgettable journey'; describe the physical structural installation directly."
    },
    {
        "id": "ed_020", "category": "editorial_lead", "domain": "membrane_breathability", "canon_id": "26_ecommerce_lookbook_grid",
        "en_slop_before": "Stay dry and comfortable in any weather with our ultimate rain shell.",
        "en_canon_after": "Microporous ePTFE membranes block wind-driven rain droplets above 100 micrometers while electrospun polyurethane nanofibers vent sweat vapor via continuous air permeability of 0.8 CFM before condensation wets out your base layer.",
        "ru_slop_before": "Оставайтесь в сухости и комфорте в любую непогоду с нашей универсальной штормовкой.",
        "ru_canon_after": "Электропряденая полиуретановая мембрана удерживает капли ветрового дождя крупнее 100 мкм и одновременно пропускает 0,8 куб. фута воздуха в минуту, отводя пар до образования конденсата на термобелье.",
        "anti_slop_rule": "Contrast droplet micrometer size with continuous CFM air permeability."
    },
    {
        "id": "ed_021", "category": "editorial_lead", "domain": "rams_switch_feel", "canon_id": "07_industrial_functional_instrument",
        "en_slop_before": "Great industrial design combines beauty and functionality in every detail.",
        "en_canon_after": "A phosphor-bronze snap dome calibrated to 2.6 Newtons of actuation force and 0.45 millimeters of travel tells a gloved technician's thumb that a relay circuit closed without glancing away from the oscilloscope.",
        "ru_slop_before": "Выдающийся промышленный дизайн гармонично сочетает красоту и функциональность в каждой детали.",
        "ru_canon_after": "Купольный контакт из фосфористой бронзы с усилием срабатывания 2,6 Н и ходом 0,45 мм сообщает пальцу инженера в перчатке о замыкании реле без отрыва взгляда от экрана осциллографа.",
        "anti_slop_rule": "Replace 'beauty and functionality' with Newtons, travel mm, and eyes-free operator ergonomics."
    },

    # === CATEGORY 8: objection_reframe (21 pairs) ===
    {
        "id": "obj_001", "category": "objection_reframe", "domain": "vendor_lockin", "canon_id": "02_neo_brutalism_tactile",
        "en_slop_before": "Don't worry about lock-in; we believe in open ecosystems and customer freedom.",
        "en_canon_after": "Zero proprietary storage format: every replica is a standard `.sqlite3` file readable by upstream `sqlite3` CLI, Python `sqlite3`, or DuckDB even if you uninstall our SDK tomorrow.",
        "ru_slop_before": "Не беспокойтесь о привязке к вендору, ведь мы верим в открытые экосистемы.",
        "ru_canon_after": "Никаких закрытых форматов хранения: каждая реплика представляет собой штатный файл `.sqlite3`, который открывается стандартной утилитой `sqlite3`, Python или DuckDB даже после полного удаления нашего SDK.",
        "anti_slop_rule": "Prove exit freedom by naming the exact upstream open file format and standard CLI readers."
    },
    {
        "id": "obj_002", "category": "objection_reframe", "domain": "ebpf_kernel_safety", "canon_id": "03_dark_precision_saas_linear",
        "en_slop_before": "Our agent is completely safe and will never crash your production servers.",
        "en_canon_after": "Unlike out-of-tree kernel modules (`insmod`), eBPF bytecode cannot dereference arbitrary pointers or loop infinitely: the in-kernel Linux verifier mathematically proves bounded termination and read-only memory safety before JIT load.",
        "ru_slop_before": "Наш агент абсолютно безопасен и никогда не вызовет сбоев на ваших боевых серверах.",
        "ru_canon_after": "В отличие от загружаемых модулей ядра `insmod`, байткод eBPF не может разыменовать произвольный указатель или уйти в бесконечный цикл: верификатор ядра Linux математически доказывает конечность исполнения до JIT-компиляции.",
        "anti_slop_rule": "Contrast `insmod` crash surface against the Linux kernel eBPF verifier's static guarantees."
    },
    {
        "id": "obj_003", "category": "objection_reframe", "domain": "migration_effort", "canon_id": "08_fintech_institutional_ledger",
        "en_slop_before": "Switching providers is quick and painless with our dedicated onboarding team.",
        "en_canon_after": "Keep your existing ERP export scripts unchanged: our SFTP/API bridge ingests standard ISO 20022 `pain.001.001.03` XML and legacy CSV payout batches in parallel with your incumbent bank during a 2-week shadow reconciliation run.",
        "ru_slop_before": "Переход на нашу платформу пройдёт быстро и безболезненно при поддержке команды внедрения.",
        "ru_canon_after": "Переписывать выгрузку из учётной системы не нужно: шлюз принимает штатные реестры ISO 20022 `pain.001.001.03` и файлы `1С` параллельно текущему банку в течение двухнедельной теневой сверки.",
        "anti_slop_rule": "Show schema compatibility (`pain.001.001.03` / 1C) and parallel shadow-run migration."
    },
    {
        "id": "obj_004", "category": "objection_reframe", "domain": "onprem_data_residency", "canon_id": "01_swiss_international_typographic",
        "en_slop_before": "We take enterprise data sovereignty seriously across all regions.",
        "en_canon_after": "Deploy the entire control plane and ClickHouse storage engine inside your own VPC or bare-metal perimeter via a single Helm chart; zero telemetry, license pings, or crash dumps ever cross your egress firewall.",
        "ru_slop_before": "Мы со всей серьёзностью относимся к цифровому суверенитету корпоративных данных.",
        "ru_canon_after": "Панель управления и хранилище ClickHouse разворачиваются целиком на ваших серверах одним Helm-чартом: ни метрики, ни проверки лицензий, ни дампы ошибок никогда не покидают ваш межсетевой экран.",
        "anti_slop_rule": "Guarantee zero outbound packets across the customer's egress firewall."
    },
    {
        "id": "obj_005", "category": "objection_reframe", "domain": "pricing_overage_fear", "canon_id": "09_monospace_cli_devtools",
        "en_slop_before": "Predictable pricing means no nasty billing surprises at month-end.",
        "en_canon_after": "Configure a hard monthly spend cap in USD/RUB per project: if traffic spikes during a logging loop, dynamic tail-sampling drops healthy HTTP 200 spans first while retaining 100% of 5xx errors at $0 unapproved overage.",
        "ru_slop_before": "Предсказуемая тарификация гарантирует отсутствие неприятных сюрпризов в конце месяца.",
        "ru_canon_after": "Задайте жёсткий денежный потолок на проект в рублях: при всплеске логов хвостовое сэмплирование отбросит штатные ответы HTTP 200, сохранив 100% ошибок 5xx и 0 ₽ несогласованных переплат.",
        "anti_slop_rule": "Explain graceful degradation under hard spend caps (drop 200s, keep 100% 5xx, $0 overage)."
    },
    {
        "id": "obj_006", "category": "objection_reframe", "domain": "timber_humidity", "canon_id": "05_nordic_architectural_minimal",
        "en_slop_before": "Our wood panels are durable and built to withstand changing indoor climates.",
        "en_canon_after": "Cross-laminated rotary-peeled birch cores kiln-stabilized to 7.5% moisture content keep seasonal dimensional movement below +/-0.4 mm per meter across 20% to 70% relative indoor humidity.",
        "ru_slop_before": "Наши деревянные панели долговечны и устойчивы к перепадам микроклимата в помещении.",
        "ru_canon_after": "Перекрёстно-клеёное основание из лущёного берёзового шпона камерной сушки 7,5% удерживает сезонную поводку в пределах +/-0,4 мм на погонный метр при колебаниях влажности воздуха от 20% до 70%.",
        "anti_slop_rule": "Answer warping objections with kiln moisture %, +/-mm/m tolerance, and RH corridor."
    },
    {
        "id": "obj_007", "category": "objection_reframe", "domain": "vanilla_no_tailwind", "canon_id": "01_swiss_international_typographic",
        "en_slop_before": "Modern CSS is clean and maintainable without heavy third-party frameworks.",
        "en_canon_after": "Native CSS custom properties (`oklch()`), `subgrid`, `@container`, and `clamp()` ship in 6 KB of zero-build stylesheet with zero Node dependency vulnerabilities and instant browser parse.",
        "ru_slop_before": "Современный чистый CSS легко поддерживать без громоздких сторонних фреймворков.",
        "ru_canon_after": "Нативные переменные `oklch()`, `subgrid`, `@container` и `clamp()` укладываются в 6 КБ таблицы стилей без этапа сборки, уязвимостей в `node_modules` и сетевых блокировок.",
        "anti_slop_rule": "Cite exact native CSS primitives, KB footprint, and zero `node_modules` attack surface."
    },
    {
        "id": "obj_008", "category": "objection_reframe", "domain": "offline_local_llm", "canon_id": "27_cybersecurity_zero_trust_ops",
        "en_slop_before": "Local AI keeps your proprietary source code private and secure.",
        "en_canon_after": "Binding `llama-server` strictly to `127.0.0.1` inside an unprivileged namespace without WAN routes ensures proprietary schematics, contracts, and source diffs never leave your NVMe drive.",
        "ru_slop_before": "Локальный ИИ надёжно защищает ваш проприетарный исходный код от утечек.",
        "ru_canon_after": "Привязка `llama-server` строго к петлевому интерфейсу `127.0.0.1` в изолированном пространстве имён без внешних маршрутов гарантирует, что чертежи, договоры и код не покинут локальный NVMe-накопитель.",
        "anti_slop_rule": "Specify `127.0.0.1` socket binding + network namespace isolation."
    },
    {
        "id": "obj_009", "category": "objection_reframe", "domain": "clinical_false_positives", "canon_id": "12_clinical_biotech_cleanroom",
        "en_slop_before": "Every test result is double-checked for maximum clinical confidence.",
        "en_canon_after": "Every reportable pathogenic SNV or indel flagged by NGS is orthogonally confirmed by bidirectional capillary Sanger sequencing from the primary tube before clinician sign-out.",
        "ru_slop_before": "Каждый результат анализа проходит двойную проверку для максимальной точности диагноза.",
        "ru_canon_after": "Каждый клинически значимый патогенный вариант после NGS проходит ортогональное подтверждение двунаправленным секвенированием по Сэнгеру из первичной пробирки до подписи врача-генетика.",
        "anti_slop_rule": "Name the exact orthogonal assay (bidirectional Sanger from primary tube)."
    },
    {
        "id": "obj_010", "category": "objection_reframe", "domain": "lfp_winter_cold", "canon_id": "17_sustainable_climate_botanical",
        "en_slop_before": "Our battery containers work reliably even in harsh northern winters.",
        "en_canon_after": "Insulated R-18 walls and closed-loop glycol plate heaters hold cell cores at +18 C during -38 C ambient blizzards while drawing less than 1.6% of stored daily energy.",
        "ru_slop_before": "Наши контейнерные накопители надёжно работают даже в суровые северные зимы.",
        "ru_canon_after": "Теплоизоляция корпуса R-18 и контур гликолевого подогрева пластин удерживают ядро ячеек при +18 C в мороз -38 C, расходуя на собственный обогрев менее 1,6% суточного запаса энергии.",
        "anti_slop_rule": "Give insulation rating, core temp vs -38 C ambient, and parasitic heating %."
    },
    {
        "id": "obj_011", "category": "objection_reframe", "domain": "industrial_legacy_plc", "canon_id": "07_industrial_functional_instrument",
        "en_slop_before": "Works seamlessly with older factory equipment without costly upgrades.",
        "en_canon_after": "Galvanically isolated RS-485 ports (2.5 kVrms) read 1990s Siemens S7-300 and Fanuc serial controllers passively in listen-only tap mode without writing a single register back to safety-certified PLC logic.",
        "ru_slop_before": "Легко подключается к старому заводскому оборудованию без дорогой модернизации.",
        "ru_canon_after": "Гальванически развязанные порты RS-485 (2,5 кВ) снимают регистры со стойки Siemens S7-300 и ЧПУ Fanuc в режиме пассивного прослушивания без права записи в аттестованную логику ПЛК.",
        "anti_slop_rule": "Address PLC engineer's #1 fear: galvanic isolation kV + hardware/protocol read-only tap guarantee."
    },
    {
        "id": "obj_012", "category": "objection_reframe", "domain": "dsp_latency_live", "canon_id": "23_audio_dsp_modular_rack",
        "en_slop_before": "Linear-phase processing usually adds latency, but our plugin handles both tracking and mastering.",
        "en_canon_after": "One click switches the filter topology between 4,096-tap linear-phase mastering (42.7 ms exact host-compensated delay) and minimum-phase live tracking (0 samples added latency) with matched gain curves.",
        "ru_slop_before": "Наш плагин одинаково отлично подходит как для записи без задержки, так и для мастеринга.",
        "ru_canon_after": "Одна кнопка переключает топологию между линейно-фазовым мастерингом на 4096 отводов (компенсируемая задержка 42,7 мс) и минимально-фазовым трекингом с нулевой задержкой 0 сэмплов при сохранении АЧХ.",
        "anti_slop_rule": "State exact FIR tap count, ms delay in mastering mode, and 0-sample tracking mode."
    },
    {
        "id": "obj_013", "category": "objection_reframe", "domain": "server_spare_parts", "canon_id": "18_bento_hardware_showcase",
        "en_slop_before": "Easy maintenance keeps your IT team productive and stress-free.",
        "en_canon_after": "Every sled component carries a QR link to its public repair manual, Torx T15 fastener map, and FRU spare part SKU stocked for 7 years with no technician certification paywall.",
        "ru_slop_before": "Простое сервисное обслуживание экономит время ваших системных администраторов.",
        "ru_canon_after": "На каждом узле нанесён код со ссылкой на открытое руководство по ремонту, карту крепежа Torx T15 и каталожный номер запчасти FRU со складским резервом на 7 лет без платной сертификации.",
        "anti_slop_rule": "Specify fastener standard (Torx T15), 7-year FRU spares guarantee, and open manuals."
    },
    {
        "id": "obj_014", "category": "objection_reframe", "domain": "editorial_paywall_trust", "canon_id": "04_editorial_broadsheet_serif",
        "en_slop_before": "Cancel your subscription anytime with no hassle.",
        "en_canon_after": "Cancel in two clicks inside Account -> Billing with zero retention phone calls; you retain full archive export (EPUB + HTML) for every issue published during your paid term.",
        "ru_slop_before": "Вы можете отменить подписку в любой момент без лишних сложностей.",
        "ru_canon_after": "Подписка отменяется в два клика в разделе «Оплата» без звонков менеджеров, а все вышедшие за оплаченный период выпуски остаются у вас в форматах EPUB и HTML.",
        "anti_slop_rule": "Ban dark-pattern retention calls and confirm permanent EPUB+HTML ownership of paid issues."
    },
    {
        "id": "obj_015", "category": "objection_reframe", "domain": "legal_conflict_speed", "canon_id": "22_legal_advisory_chancery",
        "en_slop_before": "Boutique law firms move faster than big slow corporate firms.",
        "en_canon_after": "Because we decline retainer panels for commercial clearing banks, corporate conflict clearance completes in under 4 hours instead of stalling 10 days on lender waivers.",
        "ru_slop_before": "Бутиковая юридическая практика работает гораздо оперативнее громоздких корпораций.",
        "ru_canon_after": "Поскольку практика не состоит на абонентском обслуживании расчётных госбанков, проверка конфликта интересов занимает до 4 часов вместо десятидневного ожидания согласий кредиторов.",
        "anti_slop_rule": "Explain the structural conflict-of-interest reason why clearance takes 4 hours vs 10 days."
    },
    {
        "id": "obj_016", "category": "objection_reframe", "domain": "decaf_specialty", "canon_id": "28_craft_roastery_packaging",
        "en_slop_before": "Our decaf tastes just as amazing as regular specialty coffee!",
        "en_canon_after": "Popayan ethyl-acetate sugarcane decaffeination removes 99.7% of caffeine using fermented local cane esters at 70 C rather than methylene chloride solvents, preserving malic red-apple acidity at cupping score 86.5.",
        "ru_slop_before": "Наш декофеинизированный кофе по вкусу ничем не уступает обычному спешелти-зерну!",
        "ru_canon_after": "Декофеинизация этилацетатом сахарного тростника в Попаяне при 70 C удаляет 99,7% кофеина без хлористого метилена, сохраняя яблочную кислотность лота с оценкой 86,5 балла SCA.",
        "anti_slop_rule": "Name extraction solvent (sugarcane ethyl acetate vs methylene chloride), % removed, and SCA cupping score."
    },
    {
        "id": "obj_017", "category": "objection_reframe", "domain": "civic_offline_fallback", "canon_id": "15_high_contrast_civic_gov_wcag_aaa",
        "en_slop_before": "Citizens who prefer offline channels are always supported too.",
        "en_canon_after": "Applicants without digital ID can print the pre-filled A4 form with 2D DataMatrix barcode and submit it at any of 42 municipal service desks without re-typing a single field.",
        "ru_slop_before": "Для граждан, предпочитающих личный визит, также предусмотрены удобные способы подачи.",
        "ru_canon_after": "Заявители без электронной подписи могут распечатать заполненный бланк А4 с двумерным кодом DataMatrix и сдать его в любом из 42 окон МФЦ без повторного ручного ввода анкеты.",
        "anti_slop_rule": "Provide concrete hybrid paper-barcode bridge + desk count."
    },
    {
        "id": "obj_018", "category": "objection_reframe", "domain": "quant_survivorship_bias", "canon_id": "19_quant_analytics_dense_terminal",
        "en_slop_before": "Backtest your strategies accurately on clean institutional datasets.",
        "en_canon_after": "Universe snapshots retain every delisted, bankrupt, halted, and merged ticker at exact point-in-time constituent dates, eliminating survivorship and look-ahead bias from historical backtests.",
        "ru_slop_before": "Тестируйте торговые стратегии с высокой точностью на выверенных исторических данных.",
        "ru_canon_after": "Исторические срезы индексов сохраняют все делистингованные, обанкротившиеся и поглощённые бумаги на точную дату вхождения, полностью исключая ошибку выжившего и заглядывание в будущее.",
        "anti_slop_rule": "Explicitly address delisted/bankrupt point-in-time constituents (survivorship bias)."
    },
    {
        "id": "obj_019", "category": "objection_reframe", "domain": "apparel_pfas_free", "canon_id": "26_ecommerce_lookbook_grid",
        "en_slop_before": "Eco-friendly waterproofing still performs great in heavy storms.",
        "en_canon_after": "While C0 fluorocarbon-free DWR sheds oil stains less aggressively than legacy C8 PFAS, pairing high-density 40D warp-knit face fabric with regular 30 C wash/heat reactivation holds ISO 4920 spray rating 4 after 30 washes.",
        "ru_slop_before": "Экологичная водоотталкивающая пропитка отлично защищает даже в сильный ливень.",
        "ru_canon_after": "Бесфторовая пропитка C0 DWR уступает старым фторуглеродам C8 по защите от масел, но в паре с плотным плетением 40D и тёплой сушкой после стирки удерживает 4 класс водоотталкивания по ISO 4920 после 30 стирок.",
        "anti_slop_rule": "Acknowledge the real physical tradeoff (oil resistance) honestly, then show ISO 4920 wash test proof."
    },
    {
        "id": "obj_020", "category": "objection_reframe", "domain": "lidar_rain_fog", "canon_id": "24_cartographic_field_expedition",
        "en_slop_before": "Fly missions confidently in challenging weather conditions.",
        "en_canon_after": "905 nm laser pulses scatter inside dense advection fog (<400 m visibility); pre-flight mission software flags cloud-base ceilings automatically and filters atmospheric backscatter via dual-return range gating.",
        "ru_slop_before": "Выполняйте аэросъёмку уверенно даже в сложных метеорологических условиях.",
        "ru_canon_after": "Лазерный импульс 905 нм рассеивается в плотном тумане при видимости ниже 400 м, поэтому планировщик полётов заранее блокирует вылет под низкой облачностью и отсекает аэрозольную засветку стробированием дальности.",
        "anti_slop_rule": "State exact optical physics limit (<400 m fog at 905 nm) and range-gate mitigation."
    },
    {
        "id": "obj_021", "category": "objection_reframe", "domain": "titanium_scratch_hardness", "canon_id": "16_luxury_horology_atelier_dark",
        "en_slop_before": "Titanium cases are super strong and lightweight on the wrist.",
        "en_canon_after": "Uncoated Grade-5 Ti-6Al-4V scuffs at 340 HV under desk clasps, so every case band undergoes carbon-diffusion surface hardening to 1,100 Vickers (5x 316L stainless steel) while weighing 42 grams.",
        "ru_slop_before": "Титановый корпус сочетает невероятную прочность и невесомость на запястье.",
        "ru_canon_after": "Необработанный титан Ti-6Al-4V царапается о застёжки при твёрдости 340 HV, поэтому боковина корпуса проходит диффузионное упрочнение до 1100 единиц Виккерса (впятеро твёрже стали 316L) при массе 42 грамма.",
        "anti_slop_rule": "Acknowledge raw titanium's scuffing weakness (340 HV) and prove hardening to 1,100 HV."
    }
]
