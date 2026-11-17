"""Curated EN+RU copywriting pattern pairs (Part 1: categories 1-4, 84 pairs)."""

PAIRS_PART1 = [
    # === CATEGORY 1: value_prop (21 pairs) ===
    {
        "id": "vp_001", "category": "value_prop", "domain": "nvme_telemetry", "canon_id": "01_swiss_international_typographic",
        "en_slop_before": "Unleash the future of seamless cloud-scale storage monitoring with our revolutionary AI-powered platform.",
        "en_canon_after": "Sample SMART and queue-depth telemetry across 10,000 NVMe drives every 100 ms with zero kernel modules.",
        "ru_slop_before": "Откройте будущее бесшовного мониторинга хранилищ в современном мире с нашей революционной платформой.",
        "ru_canon_after": "Снимайте телеметрию SMART и глубину очередей с 10 000 NVMe-дисков каждые 100 мс без установки ядерных модулей.",
        "anti_slop_rule": "Replace abstract future-tense hype with sampling interval, fleet scale, and deployment constraint."
    },
    {
        "id": "vp_002", "category": "value_prop", "domain": "ebpf_observability", "canon_id": "03_dark_precision_saas_linear",
        "en_slop_before": "Elevate your engineering team's observability journey and unlock actionable insights effortlessly.",
        "en_canon_after": "Pinpoint p99 syscall and TLS handshake stalls across Kubernetes pods in under 1.2% CPU overhead.",
        "ru_slop_before": "Выведите наблюдаемость вашей команды на новый уровень и раскройте потенциал инсайтов без усилий.",
        "ru_canon_after": "Находите задержки p99 в системных вызовах и TLS-рукопожатиях внутри кластеров Kubernetes при нагрузке на CPU ниже 1,2%.",
        "anti_slop_rule": "Name the exact fault class (p99 syscall/TLS stalls) and resource ceiling (<1.2% CPU)."
    },
    {
        "id": "vp_003", "category": "value_prop", "domain": "sqlite_sync_sdk", "canon_id": "02_neo_brutalism_tactile",
        "en_slop_before": "A game-changer for modern app developers seeking seamless offline-first database synchronization.",
        "en_canon_after": "Embed deterministic SQLite WAL replication in 42 KB of WebAssembly with sub-millisecond local reads.",
        "ru_slop_before": "Настоящий прорыв для разработчиков, которым нужна бесшовная синхронизация баз данных нового поколения.",
        "ru_canon_after": "Встройте детерминированную репликацию SQLite WAL весом 42 КБ на WebAssembly с локальным чтением быстрее 1 мс.",
        "anti_slop_rule": "State binary footprint (42 KB), replication mechanism (WAL), and local read latency (<1 ms)."
    },
    {
        "id": "vp_004", "category": "value_prop", "domain": "treasury_clearing", "canon_id": "08_fintech_institutional_ledger",
        "en_slop_before": "Empowering global enterprises to reimagine cross-border liquidity and treasury management.",
        "en_canon_after": "Settle multi-currency EUR, USD, and KZT vendor payouts via direct SEPA and SWIFT rails with T+0 ledger reconciliation.",
        "ru_slop_before": "Помогаем глобальному бизнесу переосмыслить управление ликвидностью и казначейскими потоками под ключ.",
        "ru_canon_after": "Проводите мультивалютные выплаты поставщикам в EUR, USD и KZT со сверкой главной книги в день расчёта T+0.",
        "anti_slop_rule": "Specify supported currencies, payment rails, and exact settlement window (T+0)."
    },
    {
        "id": "vp_005", "category": "value_prop", "domain": "acoustic_architecture", "canon_id": "05_nordic_architectural_minimal",
        "en_slop_before": "Crafting harmonious, breathtaking architectural spaces that elevate human connection and well-being.",
        "en_canon_after": "Timber acoustic interiors engineered to hold speech reverberation (RT60) between 0.45 and 0.60 seconds.",
        "ru_slop_before": "Создаём уникальные гармоничные пространства, которые вдохновляют людей и дарят незабываемый комфорт.",
        "ru_canon_after": "Проектируем акустические интерьеры из массива берёзы со временем реверберации речи RT60 в коридоре 0,45-0,60 с.",
        "anti_slop_rule": "Anchor spatial design in physical material and measurable reverberation corridor (RT60)."
    },
    {
        "id": "vp_006", "category": "value_prop", "domain": "clinical_genomics", "canon_id": "12_clinical_biotech_cleanroom",
        "en_slop_before": "Revolutionizing precision medicine with cutting-edge genomic diagnostics for a healthier tomorrow.",
        "en_canon_after": "Whole-exome variant calling from 2 mL EDTA blood in 36 hours at 99.6% analytical sensitivity.",
        "ru_slop_before": "Революционный подход к прецизионной медицине и генетической диагностике будущего.",
        "ru_canon_after": "Полноэкзомное выявление вариантов из 2 мл венозной крови с ЭДТА за 36 часов при аналитической чувствительности 99,6%.",
        "anti_slop_rule": "State specimen volume, turnaround hours, and validated analytical sensitivity."
    },
    {
        "id": "vp_007", "category": "value_prop", "domain": "zero_trust_vpn", "canon_id": "27_cybersecurity_zero_trust_ops",
        "en_slop_before": "Military-grade unhackable cybersecurity that keeps your remote workforce completely safe anywhere.",
        "en_canon_after": "Point-to-point WireGuard mesh authenticated by hardware FIDO2 keys with zero central relay decryption.",
        "ru_slop_before": "Непробиваемая защита военного уровня для абсолютной безопасности удалённых сотрудников в любой точке.",
        "ru_canon_after": "Прямая ячеистая сеть WireGuard с проверкой аппаратных FIDO2-ключей без расшифровки трафика на промежуточных узлах.",
        "anti_slop_rule": "Replace 'military-grade unhackable' with exact protocol, hardware auth factor, and trust boundary."
    },
    {
        "id": "vp_008", "category": "value_prop", "domain": "industrial_plc", "canon_id": "07_industrial_functional_instrument",
        "en_slop_before": "Unlocking Industry 4.0 smart factory transformation through seamless IoT connectivity.",
        "en_canon_after": "DIN-rail Modbus-TCP and OPC-UA gateway rated from -40 C to +75 C with 72-hour local ring-buffer retention.",
        "ru_slop_before": "Инновационный подход к цифровой трансформации умного производства в эпоху Индустрии 4.0.",
        "ru_canon_after": "Промышленный шлюз Modbus-TCP и OPC-UA на DIN-рейку для диапазона от -40 до +75 C с локальным кольцевым буфером на 72 часа.",
        "anti_slop_rule": "Give mounting standard, fieldbus protocols, thermal rating, and offline buffer hours."
    },
    {
        "id": "vp_009", "category": "value_prop", "domain": "grid_storage", "canon_id": "17_sustainable_climate_botanical",
        "en_slop_before": "Pioneering eco-friendly green energy solutions to build a sustainable planet for future generations.",
        "en_canon_after": "Containerized 4 MWh LFP grid battery blocks delivering 140 ms frequency response and audited ISO-14064 lifecycle reports.",
        "ru_slop_before": "Создаём экологичные зелёные технологии ради устойчивого будущего нашей планеты.",
        "ru_canon_after": "Контейнерные LFP-накопители ёмкостью 4 МВт·ч с откликом по частоте за 140 мс и верифицированным расчётом по ISO-14064.",
        "anti_slop_rule": "State chemistry (LFP), MWh capacity, grid response time, and LCA audit standard."
    },
    {
        "id": "vp_010", "category": "value_prop", "domain": "cli_build_system", "canon_id": "09_monospace_cli_devtools",
        "en_slop_before": "Supercharge developer velocity with our blazingly fast next-gen build orchestration tool.",
        "en_canon_after": "Content-addressed C++ and Rust monorepo builds cached over local NVMe and S3, cutting clean CI runs from 28 min to 4.1 min.",
        "ru_slop_before": "Ускорьте разработку до предела с помощью нашего ультрасовременного инструмента сборки проектов.",
        "ru_canon_after": "Контентно-адресуемая сборка монорепозиториев C++ и Rust с кэшем на NVMe и S3 сокращает прогон CI с 28 до 4,1 минуты.",
        "anti_slop_rule": "Replace 'blazingly fast' with content-addressing mechanism and before/after minutes."
    },
    {
        "id": "vp_011", "category": "value_prop", "domain": "regulatory_legal", "canon_id": "22_legal_advisory_chancery",
        "en_slop_before": "Your trusted legal partner navigating the ever-evolving landscape of complex international regulations.",
        "en_canon_after": "Cross-border M&A antitrust filings, sanctions screening, and English-law shareholder agreements led by Chambers-ranked partners.",
        "ru_slop_before": "Ваш надёжный юридический партнёр в динамично меняющемся мире международного права.",
        "ru_canon_after": "Согласование трансграничных сделок M&A, санкционный комплаенс и акционерные соглашения по английскому праву силами партнёров практики.",
        "anti_slop_rule": "List exact legal instruments and partner-led execution instead of 'navigating landscapes'."
    },
    {
        "id": "vp_012", "category": "value_prop", "domain": "audio_dsp_plugin", "canon_id": "23_audio_dsp_modular_rack",
        "en_slop_before": "Unleash studio magic and elevate your mixes with warm analog soul.",
        "en_canon_after": "32-band linear-phase mastering equalizer in CLAP and VST3 formats with 0.8 ms zero-latency tracking mode.",
        "ru_slop_before": "Раскройте магию студийного звука и подарите вашим миксам тёплую аналоговую душу.",
        "ru_canon_after": "32-полосный линейно-фазовый мастеринговый эквалайзер в форматах CLAP и VST3 с режимом мониторинга 0,8 мс.",
        "anti_slop_rule": "Specify band count, phase topology, plugin formats, and lookahead latency."
    },
    {
        "id": "vp_013", "category": "value_prop", "domain": "geospatial_lidar", "canon_id": "24_cartographic_field_expedition",
        "en_slop_before": "Transforming spatial intelligence with cutting-edge drone mapping solutions.",
        "en_canon_after": "Drone RTK-LiDAR corridor surveys delivering 40 pts/m2 classified LAS point clouds at +/-2.5 cm vertical RMSE.",
        "ru_slop_before": "Трансформируем геопространственную аналитику с помощью передовых беспилотных технологий.",
        "ru_canon_after": "Коридорная съёмка с БПЛА RTK-LiDAR выдаёт классифицированное облако 40 точек/м2 с вертикальной точностью +/-2,5 см RMSE.",
        "anti_slop_rule": "State point density, file standard (LAS), and vertical root-mean-square error."
    },
    {
        "id": "vp_014", "category": "value_prop", "domain": "specialty_roastery", "canon_id": "28_craft_roastery_packaging",
        "en_slop_before": "Experience artisanal coffee perfection crafted with passion in every unforgettable sip.",
        "en_canon_after": "Single-producer washed Pink Bourbon from Huila (1,920 masl), roasted every Tuesday to Agtron 68 and shipped within 18 hours.",
        "ru_slop_before": "Окунитесь в мир безупречного авторского кофе, созданного со страстью в каждом глотке.",
        "ru_canon_after": "Фермерский мытый Розовый Бурбон из Уила (1920 м), обжаренный по вторникам до Agtron 68 и отправленный за 18 часов.",
        "anti_slop_rule": "Replace sensory cliches with varietal, altitude, roast curve reading, and dispatch SLA."
    },
    {
        "id": "vp_015", "category": "value_prop", "domain": "civic_permits", "canon_id": "15_high_contrast_civic_gov_wcag_aaa",
        "en_slop_before": "Welcome to our modern digital citizen portal designed to make municipal services better.",
        "en_canon_after": "Submit residential building modification permits online in 12 minutes and track statutory 10-business-day review status.",
        "ru_slop_before": "Добро пожаловать на современный цифровой портал, созданный для повышения качества городских услуг.",
        "ru_canon_after": "Подайте заявление на перепланировку жилья за 12 минут и отслеживайте решение по регламенту 10 рабочих дней.",
        "anti_slop_rule": "Lead civic portals with exact service action, completion minutes, and statutory turnaround."
    },
    {
        "id": "vp_016", "category": "value_prop", "domain": "server_hardware", "canon_id": "18_bento_hardware_showcase",
        "en_slop_before": "Redefining on-premise cloud computing with groundbreaking modular server architecture.",
        "en_canon_after": "Blind-mate 2U NVMe compute sleds with cableless 48V busbars and tool-free hot-swap fan cassettes.",
        "ru_slop_before": "Меняем представление о локальной облачной инфраструктуре благодаря инновационной серверной архитектуре.",
        "ru_canon_after": "Вычислительные модули 2U NVMe со слепой стыковкой к шине 48 В без кабелей и горячей заменой вентиляторов без инструмента.",
        "anti_slop_rule": "Describe mechanical/electrical differentiators (blind-mate 48V busbar, tool-free hot-swap)."
    },
    {
        "id": "vp_017", "category": "value_prop", "domain": "quant_market_data", "canon_id": "19_quant_analytics_dense_terminal",
        "en_slop_before": "Unlock institutional-grade market alpha with real-time financial intelligence.",
        "en_canon_after": "Nanosecond-timestamped L3 orderbook replay and tick-by-tick Parquet exports across 18 equity and futures venues.",
        "ru_slop_before": "Откройте доступ к рыночной аналитике институционального уровня в режиме реального времени.",
        "ru_canon_after": "Воспроизведение стакана заявок L3 с наносекундными метками и выгрузка тиков в Parquet с 18 фондовых и срочных площадок.",
        "anti_slop_rule": "Specify orderbook depth (L3), timestamp precision, export format, and venue count."
    },
    {
        "id": "vp_018", "category": "value_prop", "domain": "technical_apparel", "canon_id": "26_ecommerce_lookbook_grid",
        "en_slop_before": "Elevate your everyday wardrobe with timeless luxury outerwear built for modern explorers.",
        "en_canon_after": "3-layer 165 gsm high-tenacity nylon shell with 28,000 mm hydrostatic head, taped 8 mm micro-seams, and lifetime seam repair.",
        "ru_slop_before": "Обновите повседневный гардероб стильной верхней одеждой премиум-класса для современных исследователей.",
        "ru_canon_after": "Трёхслойная мембранная куртка из нейлона 165 г/м2 с водостойкостью 28 000 мм, проклейкой швов 8 мм и пожизненным ремонтом.",
        "anti_slop_rule": "Replace lifestyle fluff with fabric GSM, hydrostatic column mm, seam tape width, and repair guarantee."
    },
    {
        "id": "vp_019", "category": "value_prop", "domain": "mechanical_horology", "canon_id": "16_luxury_horology_atelier_dark",
        "en_canon_after": "In-house manual-wind Caliber K-04 regulated in six positions to -1/+2 seconds per day inside a 38.5 mm Grade-5 titanium case.",
        "en_slop_before": "A timeless testament to uncompromising craftsmanship and luxury watchmaking heritage.",
        "ru_slop_before": "Вечное воплощение бескомпромиссного мастерства и богатого часового наследия.",
        "ru_canon_after": "Мануфактурный калибр K-04 с ручным заводом, отрегулированный в шести положениях до -1/+2 с/сутки в корпусе 38,5 мм из титана Grade-5.",
        "anti_slop_rule": "Eliminate 'timeless testament' and state caliber ID, positional regulation accuracy, and case alloy/mm."
    },
    {
        "id": "vp_020", "category": "value_prop", "domain": "desktop_editor", "canon_id": "20_spatial_glass_dark_instrument",
        "en_slop_before": "Meet the AI-first code editor that transforms how teams collaborate seamlessly.",
        "en_canon_after": "GPU-rasterized code editor opening 2 GB log files in 40 ms at 120 fps with CRDT peer-to-peer co-editing.",
        "ru_slop_before": "Встречайте редактор кода нового поколения для бесшовной командной работы.",
        "ru_canon_after": "Редактор кода с GPU-растеризацией открывает лог-файлы на 2 ГБ за 40 мс при 120 кадрах/с и совместном редактировании через CRDT.",
        "anti_slop_rule": "Cite rendering pipeline, max file size/open latency, frame rate, and sync data structure."
    },
    {
        "id": "vp_021", "category": "value_prop", "domain": "constructivist_cad", "canon_id": "21_constructivist_editorial_ru",
        "en_slop_before": "Comprehensive BIM engineering services delivering innovative turnkey construction designs.",
        "en_canon_after": "Finite-element steel truss verification and LOD-400 fabrication drawings compliant with Eurocode 3 and SP 16.13330.",
        "ru_slop_before": "Комплексное проектирование металлоконструкций под ключ с применением инновационных BIM-технологий.",
        "ru_canon_after": "Расчёт стальных ферм методом конечных элементов и рабочие чертежи КМД детализации LOD-400 по СП 16.13330 и Eurocode 3.",
        "anti_slop_rule": "Replace 'innovative turnkey BIM' with calculation method, LOD level, and structural codes."
    },

    # === CATEGORY 2: pain_mechanism_proof (21 pairs) ===
    {
        "id": "pmp_001", "category": "pain_mechanism_proof", "domain": "postgres_failover", "canon_id": "03_dark_precision_saas_linear",
        "en_slop_before": "Database downtime hurts revenue. Our smart cloud failover seamlessly keeps your business online 24/7.",
        "en_canon_after": "DNS-based Postgres failovers stall clients for 45-90 seconds on stale TTLs. Our connection proxy holds client sockets in memory while promoting the Raft standby via WAL replay. Across 1,400 production switchovers, median write pause measured 310 ms with zero dropped transactions.",
        "ru_slop_before": "Простои базы данных ведут к убыткам, но наше умное облачное решение обеспечит бесперебойную работу 24/7.",
        "ru_canon_after": "Переключение Postgres через DNS замораживает клиентов на 45-90 секунд из-за кэша TTL. Наш прокси удерживает клиентские сокеты в памяти, пока резервная реплика Raft догоняет журнал WAL. На выборке из 1400 переключений медианная пауза записи составила 310 мс без потери транзакций.",
        "anti_slop_rule": "Quantify failure duration (45-90s TTL), explain socket-holding mechanism, prove with N=1,400 median ms."
    },
    {
        "id": "pmp_002", "category": "pain_mechanism_proof", "domain": "cold_chain_pharma", "canon_id": "12_clinical_biotech_cleanroom",
        "en_slop_before": "Stop losing valuable vaccine shipments with our innovative end-to-end IoT tracking ecosystem.",
        "en_canon_after": "Biologic pallets spoil silently when dry-ice sublimation breaches -65 C inside customs warehouses without cellular signal. Dual-probe platinum RTD loggers buffer 90 days of 1-minute readings over sub-GHz LoRaWAN to pallet-door gateways. Validated across 8,200 cold-chain lanes, excursion write-offs fell from 3.4% to 0.18%.",
        "ru_slop_before": "Забудьте о потерях ценных фармпрепаратов благодаря нашей комплексной экосистеме мониторинга.",
        "ru_canon_after": "Биопрепараты теряют активность при сублимации сухого льда выше -65 C на таможенных складах без сотовой связи. Двухзондовые платиновые регистраторы RTD хранят 90 суток минутных замеров и передают их по LoRaWAN на ворота склада. На 8200 рейсах доля списаний снизилась с 3,4% до 0,18%.",
        "anti_slop_rule": "Name physical failure mode (-65 C sublimation + RF dead zone), sensor hardware, and write-off delta."
    },
    {
        "id": "pmp_003", "category": "pain_mechanism_proof", "domain": "invoice_ap_automation", "canon_id": "08_fintech_institutional_ledger",
        "en_slop_before": "Manual invoice processing is slow and error-prone. Automate AP effortlessly with AI.",
        "en_canon_after": "Three-way matching breaks when freight surcharges or partial deliveries split a single PO across four vendor PDFs. Line-item SKU tolerances match purchase orders, signed receiving slips, and tax IDs before queuing net-30 SEPA batches. Finance teams processing 12,000 monthly invoices cut manual exception review from 19 minutes to 95 seconds per voucher.",
        "ru_slop_before": "Ручная сверка счетов отнимает массу времени, поэтому автоматизируйте бухгалтерию с помощью ИИ.",
        "ru_canon_after": "Трёхсторонняя сверка даёт сбой, когда транспортные надбавки и частичные отгрузки дробят один заказ на четыре закрывающих акта. Алгоритм сопоставляет строки номенклатуры, приходные ордера и ИНН в пределах заданного допуска перед формированием платёжного реестра. В командах с потоком 12 000 счетов в месяц разбор расхождений сократился с 19 минут до 95 секунд.",
        "anti_slop_rule": "Explain why 3-way matching fails in reality, show SKU tolerance mechanism, give time per voucher."
    },
    {
        "id": "pmp_004", "category": "pain_mechanism_proof", "domain": "cnc_spindle_vibration", "canon_id": "07_industrial_functional_instrument",
        "en_slop_before": "Prevent unexpected machine breakdowns with our revolutionary predictive maintenance solution.",
        "en_canon_after": "Unplanned CNC spindle bearing seizure scraps titanium workpieces worth $18,000 per incident. Triaxial MEMS accelerometers mounted on the spindle housing compute 20 kHz FFT envelope spectra locally on an STM32H7 edge node. Across 64 five-axis mills over 14 months, 11 bearing spalls were flagged 96+ hours before surface finish exceeded Ra 0.8 um.",
        "ru_slop_before": "Предотвращайте внезапные поломки оборудования с нашей инновационной системой предиктивной аналитики.",
        "ru_canon_after": "Клин подшипника шпинделя ЧПУ отправляет в брак титановую заготовку стоимостью 1,6 млн рублей. Трёхосевой MEMS-акселерометр на корпусе шпинделя считает спектр огибающей БПФ в полосе 20 кГц прямо на контроллере STM32H7. На парке из 64 пятикоординатных станков за 14 месяцев все 11 питтингов выявлены минимум за 96 часов до выхода шероховатости за Ra 0,8 мкм.",
        "anti_slop_rule": "State scrap cost, FFT bandwidth + MCU, fleet size, observation months, and surface roughness threshold."
    },
    {
        "id": "pmp_005", "category": "pain_mechanism_proof", "domain": "web_cls_fonts", "canon_id": "01_swiss_international_typographic",
        "en_slop_before": "Slow websites lose visitors. Optimize your frontend experience seamlessly for maximum conversions.",
        "en_canon_after": "External webfont waterfalls trigger late layout reflows (CLS > 0.22) and block LCP on 4G mobile links. Subsetting SIL OFL variable WOFF2 files locally with metric-matched `size-adjust` fallbacks eliminates layout shift completely. Audited across 50 pages on throttled Moto G4 profiles, p75 LCP dropped from 3.4s to 1.1s at CLS 0.00.",
        "ru_slop_before": "Медленные сайты теряют клиентов, поэтому оптимизируйте интерфейс для максимальной конверсии.",
        "ru_canon_after": "Внешние шрифтовые CDN вызывают скачки вёрстки CLS выше 0,22 и задерживают отрисовку первого экрана в сетях 4G. Локальная нарезка WOFF2 со шрифтами SIL OFL и выравниванием метрик через `size-adjust` полностью убирает сдвиг строк. На тесте из 50 страниц в профиле Moto G4 показатель p75 LCP снизился с 3,4 до 1,1 с при CLS 0,00.",
        "anti_slop_rule": "Connect network waterfall -> CSS `size-adjust` + WOFF2 subsetting -> exact p75 LCP & CLS."
    },
    {
        "id": "pmp_006", "category": "pain_mechanism_proof", "domain": "llm_swap_oom", "canon_id": "09_monospace_cli_devtools",
        "en_slop_before": "Run massive AI models smoothly on consumer laptops with our groundbreaking memory technology.",
        "en_canon_after": "Mapping 28 GB embedding tables via OS `mmap` evicts active KV-cache pages and triggers Linux swap storms on 32 GB hosts. Keeping transformer layers locked in RAM while issuing 24 KB `pread` syscalls to NVMe only for the active token ID bounds embedding RAM to 0 bytes. Sustained generation holds 42 tok/s with `pswpout = 0`.",
        "ru_slop_before": "Запускайте огромные нейросети на обычных ноутбуках благодаря нашей уникальной технологии памяти.",
        "ru_canon_after": "Отображение таблиц эмбеддингов весом 28 ГБ через `mmap` вытесняет KV-кэш и вызывает лавинный свопинг на машинах с 32 ГБ ОЗУ. Прямое чтение нужных 24 КБ с NVMe через `pread` только для текущего токена удерживает расход ОЗУ под таблицу на уровне 0 байт. Генерация идёт со скоростью 42 ток/с при `pswpout = 0`.",
        "anti_slop_rule": "Explain OS page-cache eviction vs direct `pread` byte math and `pswpout = 0` proof."
    },
    {
        "id": "pmp_007", "category": "pain_mechanism_proof", "domain": "ci_flaky_browser", "canon_id": "02_neo_brutalism_tactile",
        "en_slop_before": "Say goodbye to frustrating flaky tests forever with intelligent test automation.",
        "en_canon_after": "Playwright E2E suites fail randomly when animations, network timers, and wall-clock dates race DOM assertions. Freezing virtual clock ticks, stubbing outbound sockets at loopback, and enforcing `prefers-reduced-motion: reduce` turns UI runs deterministic. Across 10,000 consecutive CI runs on 120 specs, false-red failures dropped from 6.8% to 0.0%.",
        "ru_slop_before": "Навсегда забудьте о нестабильных автотестах благодаря интеллектуальной платформе тестирования.",
        "ru_canon_after": "Браузерные тесты Playwright случайно падают, когда CSS-анимации и сетевые таймеры обгоняют проверки DOM. Заморозка виртуальных часов, замыкание сокетов на `127.0.0.1` и режим `prefers-reduced-motion: reduce` делают рендер детерминированным. На серии из 10 000 прогонов CI по 120 сценариям доля ложных падений снизилась с 6,8% до 0,0%.",
        "anti_slop_rule": "Identify race conditions, name deterministic harness controls, prove over 10,000 CI runs."
    },
    {
        "id": "pmp_008", "category": "pain_mechanism_proof", "domain": "xss_csp_security", "canon_id": "27_cybersecurity_zero_trust_ops",
        "en_slop_before": "Protect your web applications from sophisticated cyber threats with comprehensive frontend defense.",
        "en_canon_after": "Allowlisting `'unsafe-inline'` in Content-Security-Policy lets any reflected markup bug execute arbitrary session-stealing scripts. Computing exact SHA-256 digests for static `<script>` blocks and enforcing `require-trusted-types-for 'script'` blocks DOM sink injection at the browser parser. Penetration audits across 14 releases recorded zero exploitable XSS sinks.",
        "ru_slop_before": "Защитите веб-приложения от современных киберугроз с помощью комплексной системы безопасности.",
        "ru_canon_after": "Директива `'unsafe-inline'` в заголовке CSP позволяет любой инъекции разметки выполнить произвольный скрипт и украсть сессию. Расчёт точных хэшей SHA-256 для встроенных блоков `<script>` вместе с `require-trusted-types-for 'script'` блокирует DOM-XSS на уровне парсера браузера. В ходе 14 пентестов релизов не выявлено ни одного эксплуатируемого стока XSS.",
        "anti_slop_rule": "Contrast `'unsafe-inline'` failure with SHA-256 + Trusted Types parser enforcement."
    },
    {
        "id": "pmp_009", "category": "pain_mechanism_proof", "domain": "editorial_aeo_traffic", "canon_id": "04_editorial_broadsheet_serif",
        "en_slop_before": "Boost your brand visibility in AI search engines with next-generation GEO content strategies.",
        "en_canon_after": "Retrieval crawlers skip pages that bury factual answers beneath 400 words of narrative preamble or mismatch JSON-LD FAQ strings. Placing a 45-word metric-backed answer right below semantic H2 question headers with character-exact `FAQPage` `@graph` parity enables lossless citation extraction. Technical docs adopting this layout raised verified search citations by 2.4x over 90 days.",
        "ru_slop_before": "Повысьте узнаваемость бренда в нейросетевом поиске с помощью передовых GEO-стратегий.",
        "ru_canon_after": "Поисковые краулеры пропускают страницы, где ответ спрятан за четырьмя абзацами вступления или расходится с разметкой JSON-LD. Прямой ответ из 45 слов с цифрами сразу под вопросительным заголовком H2 и посимвольным совпадением в `FAQPage` `@graph` даёт чистое извлечение цитат. В технической документации частота цитирования выросла в 2,4 раза за 90 дней.",
        "anti_slop_rule": "Specify inverted-pyramid word count, H2 structure, and verbatim JSON-LD parity."
    },
    {
        "id": "pmp_010", "category": "pain_mechanism_proof", "domain": "district_heating", "canon_id": "17_sustainable_climate_botanical",
        "en_slop_before": "Smart AI heating optimization helps buildings save energy effortlessly.",
        "en_canon_after": "Fixed return-water curves overheat south-facing apartments by +3.2 C during sunny winter afternoons while wasting megawatt-hours. Model-predictive valve controllers blend 15-minute solar irradiance forecasts with thermal mass decay constants per riser. Across 48 municipal housing blocks in Helsinki, seasonal district-heat MWh consumption dropped 16.4% without comfort complaints.",
        "ru_slop_before": "Умная оптимизация отопления на базе ИИ помогает зданиям легко экономить теплоэнергию.",
        "ru_canon_after": "Жёсткий температурный график перегревает южные секции зданий на +3,2 C в солнечные зимние часы и сжигает лишние гигакалории. Предиктивный контроллер клапанов учитывает 15-минутный прогноз инсоляции и тепловую инерцию каждого стояка. На выборке из 48 жилых корпусов сезонный расход тепла снизился на 16,4% без жалоб жильцов.",
        "anti_slop_rule": "Detail physical thermal mechanism (solar irradiance + riser thermal mass) and seasonal MWh delta."
    },
    {
        "id": "pmp_011", "category": "pain_mechanism_proof", "domain": "scientific_repro", "canon_id": "25_academic_journal_monograph",
        "en_slop_before": "Make your scientific research more accessible and impactful with modern publishing tools.",
        "en_canon_after": "Static two-column PDFs sever equations from parameter sweeps and rot when external repository links die. Self-contained HTML monographs bundle SVG plots, pinned dataset SHA-256 manifests, and inline parameter sensitivity tables with zero external CDN requests. Reviewers reproduced all 19 benchmark figures offline in under 6 minutes.",
        "ru_slop_before": "Сделайте научные публикации нагляднее и эффективнее с помощью современных инструментов вёрстки.",
        "ru_canon_after": "Двухколоночные PDF-файлы отрывают формулы от таблиц чувствительности и теряют воспроизводимость при поломке внешних ссылок. Автономная HTML-монография хранит векторные графики SVG, манифесты SHA-256 датасетов и интерактивные срезы параметров без обращений к CDN. Рецензенты воспроизвели все 19 графиков офлайн быстрее чем за 6 минут.",
        "anti_slop_rule": "Contrast dead PDF links with self-contained HTML+SVG+SHA-256 offline reproducibility."
    },
    {
        "id": "pmp_012", "category": "pain_mechanism_proof", "domain": "mobile_viewport_checkout", "canon_id": "26_ecommerce_lookbook_grid",
        "en_slop_before": "Deliver a frictionless mobile shopping experience that delights customers everywhere.",
        "en_canon_after": "Sizing mobile drawers with `100vh` pushes sticky checkout buttons underneath Safari and Chrome dynamic address bars on 375 px viewports. Switching sheet containers to `100dvh` with `min-height: 44px` tap targets and `autocomplete='shipping street-address'` keeps the submit button visible above the keyboard. Mobile checkout completion rose from 61.2% to 74.8% across 22,000 sessions.",
        "ru_slop_before": "Подарите покупателям безупречный мобильный шопинг и увеличьте продажи с любого устройства.",
        "ru_canon_after": "Высота корзины в `100vh` прячет кнопку оплаты под динамическую адресную строку мобильных браузеров на экранах 375 px. Переход на `100dvh`, зоны нажатия не менее 44 px и разметку `autocomplete` удерживает кнопку заказа над экранной клавиатурой. На выборке из 22 000 сессий доля завершённых мобильных заказов выросла с 61,2% до 74,8%.",
        "anti_slop_rule": "Name exact CSS viewport bug (`100vh` vs `100dvh`), tap target px, and session conversion delta."
    },
    {
        "id": "pmp_013", "category": "pain_mechanism_proof", "domain": "audio_aliasing", "canon_id": "23_audio_dsp_modular_rack",
        "en_slop_before": "Eliminate harsh digital distortion and experience crystal-clear analog warmth.",
        "en_canon_after": "Non-linear waveshapers operating at 48 kHz fold harmonic partials back into the audible 2-8 kHz band as metallic intermodulation aliasing. Polyphase 8x oversampling with Kaiser-windowed FIR anti-imaging filters suppresses foldback below -118 dBFS. Measured on a 1 kHz + 7.3 kHz twin-tone test, alias spurs sit 34 dB cleaner than standard 2x saturators.",
        "ru_slop_before": "Избавьтесь от неприятных цифровых искажений и наслаждайтесь кристально чистым аналоговым звуком.",
        "ru_canon_after": "Нелинейные сатураторы на частоте 48 кГц отражают высшие гармоники обратно в слышимый диапазон 2-8 кГц в виде металлического алиасинга. Полифазная восьмикратная передискретизация с КИХ-фильтром Кайзера подавляет зеркальные составляющие ниже -118 dBFS. На двухтональном тесте 1 кГц + 7,3 кГц побочные гармоники на 34 дБ тише двухкратных схем.",
        "anti_slop_rule": "Explain Nyquist foldback, FIR filter architecture, and dBFS measurement on twin-tone test."
    },
    {
        "id": "pmp_014", "category": "pain_mechanism_proof", "domain": "sanctions_kyc", "canon_id": "22_legal_advisory_chancery",
        "en_slop_before": "Streamline compliance workflows and mitigate global risk with intelligent screening.",
        "en_canon_after": "Exact-string watchlist checks miss transliterated Cyrillic, Arabic, and Latin corporate beneficial owners while drowning analysts in phonetic false positives. Morphological stem normalization paired with LEI ownership-graph traversal resolves 50%-rule indirect control chains deterministically. Compliance teams cut false-positive alert queues by 63% while passing external OFAC/EU audit sampling at 100% recall.",
        "ru_slop_before": "Упростите процедуры комплаенса и минимизируйте риски с помощью интеллектуального скрининга.",
        "ru_canon_after": "Строгий поиск по подстрокам пропускает транслитерацию ФИО бенефициаров между кириллицей и латиницей, перегружая аналитиков ложными совпадениями. Морфологическая нормализация в связке с обходом графа владения по кодам LEI автоматически проверяет правило косвенного контроля 50%. Очередь ложных срабатываний сократилась на 63% при 100% полноте на внешнем аудите.",
        "anti_slop_rule": "Detail transliteration + 50%-rule ownership graph mechanism and recall/false-positive stats."
    },
    {
        "id": "pmp_015", "category": "pain_mechanism_proof", "domain": "hospitality_direct_booking", "canon_id": "11_warm_artisan_hospitality",
        "en_slop_before": "Grow direct hotel bookings and delight guests with a captivating digital storefront.",
        "en_canon_after": "Aggregator commissions consume 18-22% of room margin when guests cannot compare room square footage, quiet courtyard orientation, and cancellation cutoffs on your site. Publishing floor-plan SVGs, transparent tax-inclusive rates, and a 3-field no-account booking sheet removes comparison uncertainty. Direct web share across 14 boutique properties climbed from 29% to 54% in two seasons.",
        "ru_slop_before": "Увеличьте прямые бронирования отеля с помощью привлекательного современного сайта.",
        "ru_canon_after": "Комиссии агрегаторов забирают 18-22% выручки номерного фонда, если гость не видит на сайте площадь комнаты, сторону света и точный срок бесплатной отмены. Схемы этажей в SVG, конечная цена со всеми сборами и форма бронирования из трёх полей без регистрации снимают барьер выбора. Доля прямых броней в 14 камерных отелях выросла с 29% до 54% за два сезона.",
        "anti_slop_rule": "Quantify OTA commission drag, show transparent room metadata, prove direct booking share."
    },
    {
        "id": "pmp_016", "category": "pain_mechanism_proof", "domain": "geodetic_datum", "canon_id": "24_cartographic_field_expedition",
        "en_slop_before": "Eliminate costly construction rework with seamless GIS data integration.",
        "en_canon_after": "Mixing local municipal grid coordinates with unprojected WGS84 drone orthophotos shifts trench alignments by up to 1.4 meters on linear utility corridors. Locking project ingestion to explicit EPSG Helmert 7-parameter grid-shift matrices catches datum mismatches at upload time. Across 310 km of fiber and water trenching, survey stakeout rework dropped to zero.",
        "ru_slop_before": "Исключите дорогостоящие строительные переделки благодаря бесшовной интеграции ГИС-данных.",
        "ru_canon_after": "Смешение местных систем координат МСК с непересчитанными ортофотопланами WGS84 сдвигает ось траншеи до 1,4 метра на линейных объектах. Принудительная проверка ключей перехода Гельмерта по кодам EPSG при загрузке файлов отсекает ошибки датума до выхода геодезистов в поле. На 310 км трасс связи и водопровода число повторных разбивок снизилось до нуля.",
        "anti_slop_rule": "Cite exact meter offset error, 7-parameter Helmert EPSG check, and linear km verified."
    },
    {
        "id": "pmp_017", "category": "pain_mechanism_proof", "domain": "command_palette_latency", "canon_id": "20_spatial_glass_dark_instrument",
        "en_slop_before": "Work faster than ever before with lightning-fast search across all your tools.",
        "en_canon_after": "Electron wrapper apps stall keystrokes for 180-300 ms while marshaling IPC JSON payloads to remote search APIs. Indexing local SQLite FTS5 trigram tables in memory-mapped Rust threads renders ranked results inside a single 8.3 ms 120 Hz frame. Measured across 250,000 indexed local documents, p99 keystroke-to-paint latency holds at 4.6 ms.",
        "ru_slop_before": "Работайте быстрее, чем когда-либо, с молниеносным поиском по всем вашим рабочим инструментам.",
        "ru_canon_after": "Оболочки на Electron задерживают отклик клавиш на 180-300 мс из-за сериализации JSON между процессами и сетевых запросов. Локальный триграммный индекс SQLite FTS5 в потоке Rust укладывает ранжирование и отрисовку в один кадр 8,3 мс при 120 Гц. На базе из 250 000 документов задержка p99 от нажатия до пикселя составляет 4,6 мс.",
        "anti_slop_rule": "Contrast IPC/network stall with FTS5 trigram index inside 8.3 ms 120 Hz frame budget."
    },
    {
        "id": "pmp_018", "category": "pain_mechanism_proof", "domain": "bento_thermal_rack", "canon_id": "18_bento_hardware_showcase",
        "en_slop_before": "Next-gen liquid cooling maximizes data center efficiency and AI density.",
        "en_canon_after": "Air-cooled 700W GPU racks throttle clocks by 18% when hot-aisle recirculation pushes inlet temperatures past 32 C. Direct-to-chip microchannel copper coldplates operating at 40 C supply water capture 88% of rack heat into closed-loop dry coolers without chillers. Measured in a 32-rack deployment, annualized facility PUE fell from 1.48 to 1.11.",
        "ru_slop_before": "Жидкостное охлаждение нового поколения максимизирует энергоэффективность современных ЦОД.",
        "ru_canon_after": "Воздушное охлаждение стоек с ускорителями по 700 Вт сбрасывает частоты на 18% при рециркуляции горячего коридора выше 32 C. Медные микроканальные водоблоки с подачей теплоносителя 40 C отводят 88% тепла на сухие градирни без фреоновых чиллеров. В зале на 32 стойки среднегодовой коэффициент PUE снизился с 1,48 до 1,11.",
        "anti_slop_rule": "Give TDP watts, supply water temp, heat capture %, chiller elimination, and measured PUE."
    },
    {
        "id": "pmp_019", "category": "pain_mechanism_proof", "domain": "civic_form_drop", "canon_id": "15_high_contrast_civic_gov_wcag_aaa",
        "en_slop_before": "Making public benefit applications easier and more inclusive for every citizen.",
        "en_canon_after": "Applicants abandon multi-page municipal benefit forms when session timeouts wipe 25 minutes of typed household records or reject scanned PDFs over 2 MB. Auto-saving draft fields in encrypted server sessions and accepting smartphone JPEG photos up to 15 MB preserves progress across interrupted visits. First-attempt completion among applicants aged 65+ rose from 48% to 86%.",
        "ru_slop_before": "Делаем получение социальных выплат удобнее и доступнее для каждого жителя региона.",
        "ru_canon_after": "Заявители бросают многошаговые анкеты на субсидию, когда тайм-аут сессии стирает 25 минут ввода или форма отвергает скан тяжелее 2 МБ. Автосохранение черновика на сервере и приём фотографий со смартфона до 15 МБ сохраняют прогресс при повторном входе. Доля успешной подачи с первой попытки среди граждан старше 65 лет выросла с 48% до 86%.",
        "anti_slop_rule": "Pinpoint real UX blocker (timeout + 2 MB upload cap), fix mechanism, and demographic completion gain."
    },
    {
        "id": "pmp_020", "category": "pain_mechanism_proof", "domain": "coffee_water_chemistry", "canon_id": "28_craft_roastery_packaging",
        "en_slop_before": "Brew cafe-quality specialty coffee at home every single morning effortlessly.",
        "en_canon_after": "High-bicarbonate tap water (>180 ppm CaCO3) neutralizes fruit acids and flattens washed Ethiopian and Colombian filter roasts into chalky bitterness. Dosing distilled water with measured MgSO4 and KHCO3 mineral sachets locks total hardness at 65 ppm and alkalinity at 25 ppm. Blind triangle cuppings across 90 home brewers achieved 84% preference over carbon-filtered municipal water.",
        "ru_slop_before": "Готовьте идеальный спешелти-кофе как в любимой кофейне каждое утро без лишних усилий.",
        "ru_canon_after": "Водопроводная вода с гидрокарбонатами выше 180 мг/л гасит ягодную кислотность мытой Эфиопии и Колумбии, оставляя меловой привкус. Минеральные саше MgSO4 и KHCO3 для дистиллята фиксируют общую жёсткость на уровне 65 мг/л и щёлочность 25 мг/л. На слепых триангуляционных каппингах 84% из 90 участников выбрали эту воду против бытового угольного фильтра.",
        "anti_slop_rule": "State ppm carbonate chemistry, mineral salt buffer, and blind triangle cupping score."
    },
    {
        "id": "pmp_021", "category": "pain_mechanism_proof", "domain": "structural_bim_clash", "canon_id": "21_constructivist_editorial_ru",
        "en_slop_before": "Avoid construction delays with our collaborative 3D coordination workflow.",
        "en_canon_after": "Unresolved intersections between HV cable trays, fire-sprinkler mains, and steel gusset plates stall site erection for weeks of field torch-cutting. Automated boolean solid-collision checks run nightly across IFC4 discipline models with +/-5 mm clearance rules before shop fabrication starts. Across 140,000 m2 of industrial hall steelwork, on-site MEP penetration rework fell by 91%.",
        "ru_slop_before": "Избегайте срывов сроков строительства с помощью нашей системы 3D-координации проектов.",
        "ru_canon_after": "Неучтённые пересечения кабельных лотков, магистралей пожаротушения и фасонок стальных ферм останавливают монтаж на недели ради резки по месту. Ежедневная булева проверка твёрдых тел в моделях IFC4 с допуском +/-5 мм выявляет коллизии до запуска чертежей КМД в цех. На объектах площадью 140 000 м2 объём переделок проходок на площадке сократился на 91%.",
        "anti_slop_rule": "Name physical clash components, IFC4 +/-5 mm boolean check, and m2 rework reduction."
    },

    # === CATEGORY 3: cta_transform (21 pairs) ===
    {
        "id": "cta_001", "category": "cta_transform", "domain": "cli_devtools", "canon_id": "09_monospace_cli_devtools",
        "en_slop_before": "Get Started Free Today!",
        "en_canon_after": "Copy single-binary install command (Linux x86_64, 14 MB, no signup)",
        "ru_slop_before": "Начать бесплатно прямо сейчас!",
        "ru_canon_after": "Скопировать команду установки бинарника (Linux x86_64, 14 МБ, без регистрации)",
        "anti_slop_rule": "Name exact artifact, OS, file size, and zero-account guarantee."
    },
    {
        "id": "cta_002", "category": "cta_transform", "domain": "b2b_enterprise_demo", "canon_id": "01_swiss_international_typographic",
        "en_slop_before": "Book a Revolutionary Demo",
        "en_canon_after": "Schedule a 25-minute live architecture review with a principal engineer",
        "ru_slop_before": "Заказать уникальную демонстрацию",
        "ru_canon_after": "Назначить 25-минутный разбор архитектуры с ведущим инженером",
        "anti_slop_rule": "Specify call duration (25 min) and interlocutor role (principal engineer, not SDR)."
    },
    {
        "id": "cta_003", "category": "cta_transform", "domain": "saas_sandbox", "canon_id": "03_dark_precision_saas_linear",
        "en_slop_before": "Unlock Your Trial Now",
        "en_canon_after": "Open live read-only trace sandbox (preloaded 50M spans, zero card required)",
        "ru_slop_before": "Разблокировать пробный период",
        "ru_canon_after": "Открыть интерактивный стенд трассировок (50 млн спанов, без привязки карты)",
        "anti_slop_rule": "Offer immediate preloaded interactive sandbox without credit card friction."
    },
    {
        "id": "cta_004", "category": "cta_transform", "domain": "fintech_pricing", "canon_id": "08_fintech_institutional_ledger",
        "en_slop_before": "Contact Us to Learn More",
        "en_canon_after": "Download 2026 SEPA & SWIFT fee schedule (CSV + signed PDF, 180 KB)",
        "ru_slop_before": "Свяжитесь с нами, чтобы узнать больше",
        "ru_canon_after": "Скачать тарифную сетку расчётов 2026 (CSV и подписанный PDF, 180 КБ)",
        "anti_slop_rule": "Deliver transparent fee schedule immediately instead of forcing an opaque sales inquiry."
    },
    {
        "id": "cta_005", "category": "cta_transform", "domain": "security_audit", "canon_id": "27_cybersecurity_zero_trust_ops",
        "en_slop_before": "Discover Our Security",
        "en_canon_after": "Read unredacted Cure53 penetration test report (42 pages, SHA-256 verified)",
        "ru_slop_before": "Узнать всё о нашей безопасности",
        "ru_canon_after": "Прочитать полный отчёт пентеста без купюр (42 страницы, сверка SHA-256)",
        "anti_slop_rule": "Point to unredacted third-party audit report with page count."
    },
    {
        "id": "cta_006", "category": "cta_transform", "domain": "industrial_datasheet", "canon_id": "07_industrial_functional_instrument",
        "en_slop_before": "Explore Technical Capabilities",
        "en_canon_after": "Download STEP 3D CAD model & pinout datasheet (Rev 3.2, 2.4 MB)",
        "ru_slop_before": "Изучить технические возможности",
        "ru_canon_after": "Скачать 3D-модель STEP и схему распиновки (редакция 3.2, 2,4 МБ)",
        "anti_slop_rule": "Provide exact CAD STEP + pinout revision engineers actually need."
    },
    {
        "id": "cta_007", "category": "cta_transform", "domain": "hospitality_table", "canon_id": "11_warm_artisan_hospitality",
        "en_slop_before": "Reserve Your Unforgettable Experience",
        "en_canon_after": "Check dinner availability for 2-6 guests (instant confirmation, free changes up to 24h)",
        "ru_slop_before": "Забронировать незабываемый вечер",
        "ru_canon_after": "Проверить свободные столы на 2-6 гостей (мгновенное подтверждение, отмена за 24 ч)",
        "anti_slop_rule": "State party size range, instant confirmation, and cancellation cutoff."
    },
    {
        "id": "cta_008", "category": "cta_transform", "domain": "architectural_consult", "canon_id": "05_nordic_architectural_minimal",
        "en_slop_before": "Start Your Dream Project",
        "en_canon_after": "Send room dimensions & floor plan for preliminary RT60 acoustic calculation",
        "ru_slop_before": "Начать проект вашей мечты",
        "ru_canon_after": "Отправить габариты зала и план БТИ для предварительного расчёта RT60",
        "anti_slop_rule": "Ask for concrete engineering inputs and promise a concrete preliminary calculation."
    },
    {
        "id": "cta_009", "category": "cta_transform", "domain": "clinical_requisition", "canon_id": "12_clinical_biotech_cleanroom",
        "en_slop_before": "Partner With Our Lab",
        "en_canon_after": "Order validated blood collection kits (dispatch within 24h to licensed clinics)",
        "ru_slop_before": "Стать партнёром лаборатории",
        "ru_canon_after": "Заказать вакуумные наборы пробирок (отгрузка в клиники за 24 часа)",
        "anti_slop_rule": "Specify physical kit dispatch SLA and clinical eligibility."
    },
    {
        "id": "cta_010", "category": "cta_transform", "domain": "newsletter_digest", "canon_id": "04_editorial_broadsheet_serif",
        "en_slop_before": "Subscribe to Stay Ahead of the Curve!",
        "en_canon_after": "Receive one Sunday Systems Essay per week (zero sponsors, 1-click unsubscribe)",
        "ru_slop_before": "Подпишитесь, чтобы всегда быть в тренде!",
        "ru_canon_after": "Получать один инженерный разбор по воскресеньям (без рекламы, отписка в 1 клик)",
        "anti_slop_rule": "State exact cadence, day of week, ad policy, and 1-click exit."
    },
    {
        "id": "cta_011", "category": "cta_transform", "domain": "devtools_pricing_calc", "canon_id": "02_neo_brutalism_tactile",
        "en_slop_before": "See Flexible Plans",
        "en_canon_after": "Calculate exact monthly bill from daily row writes ($0 idle floor)",
        "ru_slop_before": "Посмотреть гибкие тарифы",
        "ru_canon_after": "Рассчитать точный счёт за месяц по числу записей (база 0 ₽ в простое)",
        "anti_slop_rule": "Point to deterministic unit-cost calculator and $0/0 RUB idle guarantee."
    },
    {
        "id": "cta_012", "category": "cta_transform", "domain": "legal_intake", "canon_id": "22_legal_advisory_chancery",
        "en_slop_before": "Speak With an Attorney Today",
        "en_canon_after": "Submit encrypted conflict-check inquiry (response within 4 business hours)",
        "ru_slop_before": "Получить консультацию юриста",
        "ru_canon_after": "Направить запрос на проверку конфликта интересов (ответ за 4 рабочих часа)",
        "anti_slop_rule": "Use accurate legal intake step (conflict check) + 4-business-hour SLA."
    },
    {
        "id": "cta_013", "category": "cta_transform", "domain": "audio_demo_plugin", "canon_id": "23_audio_dsp_modular_rack",
        "en_slop_before": "Try the Magic Free",
        "en_canon_after": "Download 14-day unrestricted CLAP/VST3 installer (offline, no iLok dongle)",
        "ru_slop_before": "Попробовать магию звука бесплатно",
        "ru_canon_after": "Скачать полную 14-дневную версию CLAP/VST3 (работает офлайн, без USB-ключа)",
        "anti_slop_rule": "Address the #1 audio engineer fear (iLok/dongles/online DRM) directly in the CTA."
    },
    {
        "id": "cta_014", "category": "cta_transform", "domain": "academic_repro", "canon_id": "25_academic_journal_monograph",
        "en_slop_before": "Learn More About Our Research",
        "en_canon_after": "Clone reproducible evaluation harness & seed manifests (Apache-2.0, 3.8 MB)",
        "ru_slop_before": "Подробнее о нашем исследовании",
        "ru_canon_after": "Клонировать стенд воспроизводимости и манифесты сидов (Apache-2.0, 3,8 МБ)",
        "anti_slop_rule": "Give license and exact reproducibility artifact size."
    },
    {
        "id": "cta_015", "category": "cta_transform", "domain": "civic_status", "canon_id": "15_high_contrast_civic_gov_wcag_aaa",
        "en_slop_before": "Click Here to Continue",
        "en_canon_after": "Look up application status by 10-digit registration number",
        "ru_slop_before": "Нажмите здесь для продолжения",
        "ru_canon_after": "Проверить статус заявления по 10-значному входящему номеру",
        "anti_slop_rule": "Never write 'Click Here'; state exact lookup action and required identifier."
    },
    {
        "id": "cta_016", "category": "cta_transform", "domain": "ecommerce_cart", "canon_id": "26_ecommerce_lookbook_grid",
        "en_slop_before": "Grab Yours Before It's Gone!",
        "en_canon_after": "Add Size M Field Shell to bag ($340, ships today from Tallinn, 30-day returns)",
        "ru_slop_before": "Успейте забрать со скидкой!",
        "ru_canon_after": "Добавить куртку размера M в корзину (32 000 ₽, отгрузка сегодня, возврат 30 дней)",
        "anti_slop_rule": "Replace fake scarcity with SKU size, exact price, dispatch day, and return window."
    },
    {
        "id": "cta_017", "category": "cta_transform", "domain": "climate_lca", "canon_id": "17_sustainable_climate_botanical",
        "en_slop_before": "Join Our Green Mission",
        "en_canon_after": "Inspect third-party DNV lifecycle verification dossier (ISO-14064-3)",
        "ru_slop_before": "Присоединяйтесь к зелёной миссии",
        "ru_canon_after": "Открыть заключение верификатора по жизненному циклу ISO-14064-3",
        "anti_slop_rule": "Direct skeptical buyers straight to independent verification dossiers."
    },
    {
        "id": "cta_018", "category": "cta_transform", "domain": "exhibition_tickets", "canon_id": "14_kinetic_cultural_exhibition",
        "en_slop_before": "Experience the Exhibition",
        "en_canon_after": "Book timed-entry ticket for Hall B (600 RUB, wheelchair step-free route included)",
        "ru_slop_before": "Погрузиться в мир искусства",
        "ru_canon_after": "Купить билет по сеансам в Павильон Б (600 ₽, безбарьерный вход с пандусом)",
        "anti_slop_rule": "Include hall name, exact ticket price, and physical accessibility route note."
    },
    {
        "id": "cta_019", "category": "cta_transform", "domain": "horology_appointment", "canon_id": "16_luxury_horology_atelier_dark",
        "en_slop_before": "Inquire About Exclusivity",
        "en_canon_after": "Reserve private movement inspection at Glashutte or Zurich salon",
        "ru_slop_before": "Узнать об эксклюзивной коллекции",
        "ru_canon_after": "Записаться на личный осмотр калибра в ателье с часовщиком-мастером",
        "anti_slop_rule": "Replace pretentious 'exclusivity' talk with concrete salon inspection."
    },
    {
        "id": "cta_020", "category": "cta_transform", "domain": "roastery_subscription", "canon_id": "28_craft_roastery_packaging",
        "en_slop_before": "Join the Coffee Club!",
        "ru_slop_before": "Вступить в закрытый кофейный клуб!",
        "en_canon_after": "Start bi-weekly 2x250g filter dispatch (pause or cancel in 1 click anytime)",
        "ru_canon_after": "Оформить доставку 2×250 г под фильтр раз в 2 недели (пауза в 1 клик без звонков)",
        "anti_slop_rule": "Specify gram weight, dispatch frequency, and zero-friction cancellation."
    },
    {
        "id": "cta_021", "category": "cta_transform", "domain": "quant_historical_sample", "canon_id": "19_quant_analytics_dense_terminal",
        "en_slop_before": "Request Data Access",
        "en_canon_after": "Download 24-hour NASDAQ ITCH 5.0 sample Parquet (410 MB, schema included)",
        "ru_slop_before": "Запросить доступ к витрине данных",
        "ru_canon_after": "Скачать суточный срез стакана в формате Parquet (410 МБ со схемой полей)",
        "anti_slop_rule": "Provide immediate sample dataset format and byte size."
    },

    # === CATEGORY 4: b2b_metric_proof (21 pairs) ===
    {
        "id": "bmp_001", "category": "b2b_metric_proof", "domain": "cdn_edge_tls", "canon_id": "03_dark_precision_saas_linear",
        "en_slop_before": "Customers love how dramatically faster their APIs run on our global edge network.",
        "en_canon_after": "Migrating 420M daily checkout requests from single-region Frankfurt ALBs to TLS 1.3 0-RTT edge PoPs cut p95 round-trip latency from 184 ms to 29 ms (measured over 30 days via Catchpoint synthetic probes).",
        "ru_slop_before": "Клиенты в восторге от невероятного ускорения работы своих сервисов в нашей глобальной сети.",
        "ru_canon_after": "Перенос 420 млн ежедневных запросов корзины с балансировщиков во Франкфурте на узлы TLS 1.3 снизил задержку p95 со 184 до 29 мс по данным 30-дневного внешнего мониторинга.",
        "anti_slop_rule": "Include request volume, baseline topology, target topology, p95 delta, and measurement window."
    },
    {
        "id": "bmp_002", "category": "b2b_metric_proof", "domain": "warehouse_pick", "canon_id": "07_industrial_functional_instrument",
        "en_slop_before": "Warehouse productivity skyrocketed after implementing our smart picking system.",
        "en_canon_after": "Batching multi-aisle grocery orders via wave-zone pathing reduced picker walking distance from 14.2 km to 8.1 km per 8-hour shift and raised verified lines-per-hour from 92 to 146 across 3 fulfillment centers.",
        "ru_slop_before": "Производительность склада взлетела до небес после внедрения нашей умной системы сборки.",
        "ru_canon_after": "Волновая маршрутизация заказов сократила пробег комплектовщика за 8-часовую смену с 14,2 до 8,1 км и подняла выработку с 92 до 146 строк в час на трёх распределительных центрах.",
        "anti_slop_rule": "Replace 'skyrocketed' with km walked per shift, lines/hour, and facility count."
    },
    {
        "id": "bmp_003", "category": "b2b_metric_proof", "domain": "chargeback_fraud", "canon_id": "08_fintech_institutional_ledger",
        "en_slop_before": "Our AI fraud engine slashes chargebacks while boosting approval rates seamlessly.",
        "en_canon_after": "Selective 3DS2 step-up triggered only on ASN/BIN velocity anomalies lowered Visa chargeback ratio from 0.84% to 0.19% while lifting legitimate card authorization rate by +2.1 percentage points ($14.6M annualized recovered GMV).",
        "ru_slop_before": "Наш антифрод-движок радикально снижает чарджбэки и одновременно повышает конверсию оплат.",
        "ru_canon_after": "Выборочный запрос 3DS2 только при аномалиях подсети ASN и BIN снизил долю чарджбэков с 0,84% до 0,19% и одновременно повысил успешную авторизацию карт на +2,1 п.п.",
        "anti_slop_rule": "Report both error directions (chargeback % AND card authorization lift in percentage points)."
    },
    {
        "id": "bmp_004", "category": "b2b_metric_proof", "domain": "log_compression", "canon_id": "09_monospace_cli_devtools",
        "en_slop_before": "Save massive cloud storage costs with next-level log compression.",
        "en_canon_after": "Columnar dictionary encoding + Zstandard level-6 packed 48 TB/day of Envoy access logs into 3.1 TB on S3 (15.4:1 ratio), cutting monthly AWS storage + egress spend from $68,400 to $9,200.",
        "ru_slop_before": "Экономьте огромные бюджеты на облачном хранении логов благодаря инновационному сжатию.",
        "ru_canon_after": "Колоночное словарное кодирование со сжатием Zstandard уровня 6 упаковало 48 ТБ/сутки логов Envoy в 3,1 ТБ (коэффициент 15,4:1), снизив ежемесячный счёт за объектное хранилище с 6,1 млн до 820 тыс. рублей.",
        "anti_slop_rule": "Show raw TB/day -> compressed TB, exact codec, compression ratio, and currency delta."
    },
    {
        "id": "bmp_005", "category": "b2b_metric_proof", "domain": "clinical_triage", "canon_id": "12_clinical_biotech_cleanroom",
        "en_slop_before": "Faster lab turnaround empowers doctors to deliver better patient outcomes.",
        "en_canon_after": "Direct bedside barcode accessioning eliminated manual tube relabeling across 4 emergency departments (N=31,400 blood cultures), cutting median collection-to-Gram-stain reporting from 4h 12m to 1h 48m with zero mislabeled specimens.",
        "ru_slop_before": "Ускорение лабораторной диагностики помогает врачам спасать пациентов гораздо быстрее.",
        "ru_canon_after": "Штрихкодирование пробирок прямо у постели пациента в четырёх приёмных отделениях (N=31 400 посевов крови) сократило медиану выдачи окраски по Граму с 4 ч 12 мин до 1 ч 48 мин при нуле ошибок маркировки.",
        "anti_slop_rule": "Report sample N, clinical workflow step removed, median hours/minutes, and error count."
    },
    {
        "id": "bmp_006", "category": "b2b_metric_proof", "domain": "compiler_upgrade", "canon_id": "02_neo_brutalism_tactile",
        "en_slop_before": "Migrating to our SDK makes mobile apps way smaller and faster.",
        "en_canon_after": "Replacing three legacy analytics frameworks with our zero-dependency C99 core shrank iOS IPA download size by 11.4 MB and reduced cold `application:didFinishLaunching` time on iPhone 13 Mini from 640 ms to 190 ms.",
        "ru_slop_before": "Переход на наш SDK делает мобильные приложения заметно легче и быстрее.",
        "ru_canon_after": "Замена трёх сторонних аналитических библиотек нашим ядром на C99 без зависимостей уменьшила размер сборки IPA на 11,4 МБ и сократила холодный старт на iPhone 13 Mini с 640 до 190 мс.",
        "anti_slop_rule": "Name reference test hardware (iPhone 13 Mini), binary MB saved, and lifecycle hook ms."
    },
    {
        "id": "bmp_007", "category": "b2b_metric_proof", "domain": "acoustic_office", "canon_id": "05_nordic_architectural_minimal",
        "en_slop_before": "Our acoustic panels transformed a noisy open office into a calm workspace.",
        "en_canon_after": "Installing 180 m2 of perforated birch Helmholtz ceiling baffles (NRC 0.85) across a 60-desk trading floor reduced speech transmission index (STI) at 4 meters from 0.64 to 0.31 and ambient peak SPL by 7.5 dBA.",
        "ru_slop_before": "Наши акустические панели превратили шумный опенспейс в тихое и уютное рабочее пространство.",
        "ru_canon_after": "Монтаж 180 м2 перфорированных берёзовых потолочных экранов Гельмгольца (NRC 0,85) в зале на 60 рабочих мест снизил индекс разборчивости фоновой речи STI на дистанции 4 м с 0,64 до 0,31, а пиковый шум на 7,5 дБА.",
        "anti_slop_rule": "Cite installed m2, NRC rating, STI speech privacy drop at 4 m, and dBA reduction."
    },
    {
        "id": "bmp_008", "category": "b2b_metric_proof", "domain": "solar_soiling", "canon_id": "17_sustainable_climate_botanical",
        "en_slop_before": "Smart cleaning schedules maximize solar farm output all year round.",
        "en_canon_after": "Scheduling waterless robotic brush passes by real-time short-circuit current (`Isc`) soiling-ratio thresholds instead of fixed monthly calendars recovered +4.7% annual GWh yield across a 120 MWp Atacama PV array.",
        "ru_slop_before": "Умное планирование очистки солнечных панелей максимизирует выработку круглый год.",
        "ru_canon_after": "Запуск безводных роботов-щёток по порогу падения тока короткого замыкания `Isc` вместо календарного графика вернул +4,7% годовой выработки ГВт·ч на солнечной станции мощностью 120 МВт.",
        "anti_slop_rule": "State trigger metric (`Isc` soiling ratio), array MWp scale, and annual GWh yield recovery."
    },
    {
        "id": "bmp_009", "category": "b2b_metric_proof", "domain": "ddos_scrubbing", "canon_id": "27_cybersecurity_zero_trust_ops",
        "en_slop_before": "Unmatched DDoS protection that stops even the biggest attacks instantly.",
        "en_canon_after": "XDP/eBPF packet filters at NIC driver ingress dropped a 1.8 Tbps / 410 Mpps UDP amplification flood in 1.4 seconds while keeping legitimate BGP customer sessions below 0.01% packet loss.",
        "ru_slop_before": "Непревзойдённая защита от DDoS-атак мгновенно отражает угрозы любой мощности.",
        "ru_canon_after": "Пакетные фильтры XDP/eBPF на входе сетевой карты отсекли UDP-флуд мощностью 1,8 Тбит/с (410 млн пакетов/с) за 1,4 секунды, удержав потери легитимного трафика ниже 0,01%.",
        "anti_slop_rule": "Specify Tbps + Mpps flood volume, kernel ingress layer (XDP), time to mitigate, and clean traffic loss."
    },
    {
        "id": "bmp_010", "category": "b2b_metric_proof", "domain": "contract_redline", "canon_id": "22_legal_advisory_chancery",
        "en_slop_before": "Accelerate legal deal velocity and close enterprise contracts faster.",
        "en_canon_after": "Standardizing pre-approved fallback clauses for limitation-of-liability and GDPR DPA schedules shortened median SaaS enterprise procurement legal review from 26 calendar days to 7 calendar days across 190 deals.",
        "ru_slop_before": "Ускорьте согласование договоров и закрывайте крупные корпоративные сделки быстрее.",
        "ru_canon_after": "Библиотека предсогласованных резервных формулировок об ограничении ответственности и поручении обработки ПДн сократила медиану юридического согласования корпоративных контрактов с 26 до 7 календарных дней на выборке из 190 сделок.",
        "anti_slop_rule": "Name exact legal bottleneck clauses, deal sample size (190), and median calendar days."
    },
    {
        "id": "bmp_011", "category": "b2b_metric_proof", "domain": "editorial_retention", "canon_id": "04_editorial_broadsheet_serif",
        "en_slop_before": "Readers stay engaged much longer on our redesigned content experience.",
        "en_canon_after": "Removing mid-article sticky video ads, tightening body measure to 62ch, and adding a sticky section outline raised scroll-to-end completion on 4,000-word technical essays from 28% to 51% (N=180,000 readers).",
        "ru_slop_before": "Читатели гораздо дольше остаются вовлечёнными благодаря нашему обновлённому дизайну статей.",
        "ru_canon_after": "Отказ от плавающих видеовставок, сужение текстовой колонки до 62 знаков и боковое оглавление подняли долю дочитывания лонгридов на 4000 слов с 28% до 51% (выборка 180 000 чтений).",
        "anti_slop_rule": "Attribute scroll completion gain to specific typographic & layout interventions + sample N."
    },
    {
        "id": "bmp_012", "category": "b2b_metric_proof", "domain": "sqlite_edge_latency", "canon_id": "19_quant_analytics_dense_terminal",
        "en_slop_before": "Experience ultra-low latency analytics queries at any scale.",
        "en_canon_after": "SIMD AVX2 vectorized scans over Zstd-compressed Parquet partitions evaluated 12-month cohort retention across 1.1 billion event rows in 380 ms on a single 16-core bare-metal node.",
        "ru_slop_before": "Оцените сверхнизкую задержку аналитических запросов при любых объёмах данных.",
        "ru_canon_after": "Векторизованное сканирование AVX2 по партициям Parquet рассчитало 12-месячное удержание когорт на 1,1 млрд событий за 380 мс на одном 16-ядерном выделенном сервере.",
        "anti_slop_rule": "Always anchor query latency to row count, compression format, and core count."
    },
    {
        "id": "bmp_013", "category": "b2b_metric_proof", "domain": "accessibility_remediation", "canon_id": "15_high_contrast_civic_gov_wcag_aaa",
        "en_slop_before": "Our accessible redesign ensures everyone can use the portal seamlessly.",
        "en_canon_after": "Remediating 42 low-contrast tokens to >= 7.2:1 OKLCH AAA, adding `<label for>` bindings, and fixing focus-trap modals eliminated 100% of axe-core critical/serious violations and cut NVDA screen-reader task time by 44%.",
        "ru_slop_before": "Наш инклюзивный редизайн сделал портал максимально удобным для всех категорий пользователей.",
        "ru_canon_after": "Доведение 42 цветовых токенов OKLCH до контраста >= 7,2:1 AAA, явная привязка `<label for>` и устранение ловушек фокуса убрали 100% критических ошибок axe-core и ускорили прохождение сценария через экранный диктор NVDA на 44%.",
        "anti_slop_rule": "Verify accessibility via axe-core defect count AND assistive-technology task completion time."
    },
    {
        "id": "bmp_014", "category": "b2b_metric_proof", "domain": "hardware_rma_rate", "canon_id": "18_bento_hardware_showcase",
        "en_slop_before": "Built with uncompromising reliability for mission-critical deployments.",
        "en_canon_after": "Replacing soldered electrolytic capacitors with automotive-grade polymer tantalums and potting RJ45 magnetics lowered 36-month field RMA rates across 19,500 deployed industrial switches from 2.1% to 0.24%.",
        "ru_slop_before": "Оборудование создано с бескомпромиссной надёжностью для критически важных объектов.",
        "ru_canon_after": "Замена электролитических конденсаторов на полимерные танталовые и компаундирование трансформаторов RJ45 снизили долю гарантийных возвратов RMA за 36 месяцев с 2,1% до 0,24% на партии из 19 500 коммутаторов.",
        "anti_slop_rule": "Back reliability claims with component changes, deployed fleet size, and 36-month RMA %."
    },
    {
        "id": "bmp_015", "category": "b2b_metric_proof", "domain": "garment_return_rate", "canon_id": "26_ecommerce_lookbook_grid",
        "en_slop_before": "Customers find their perfect fit effortlessly with our sizing guide.",
        "en_canon_after": "Publishing flat-lay garment chest, shoulder, and sleeve measurements in millimeters alongside model height/weight specs reduced size-exchange returns on technical shells from 24.5% to 9.8% year-over-year.",
        "ru_slop_before": "Покупатели легко подбирают идеальную посадку благодаря нашей размерной сетке.",
        "ru_canon_after": "Публикация обмеров готового изделия в миллиметрах по груди, плечам и рукаву вместе с параметрами модели снизила долю возвратов из-за непопадания в размер с 24,5% до 9,8% год к году.",
        "anti_slop_rule": "Connect exact garment measurement table to return-rate percentage drop."
    },
    {
        "id": "bmp_016", "category": "b2b_metric_proof", "domain": "moe_expert_pruning", "canon_id": "25_academic_journal_monograph",
        "en_slop_before": "Our compressed AI model keeps almost all quality while using way less memory.",
        "en_canon_after": "Domain-calibrated expert pruning (512 -> 256 experts per layer) with router bias healing cut GGUF checkpoint size by 46.8% while retaining 99.1% HumanEval+ pass@1 and 98.7% bilingual RU/EN rubric parity.",
        "ru_slop_before": "Наша сжатая языковая модель сохраняет почти всё качество при минимальном расходе памяти.",
        "ru_canon_after": "Доменно-калиброванный прунинг экспертов (512 -> 256 на слой) с коррекцией смещений роутера уменьшил размер чекпойнта GGUF на 46,8%, сохранив 99,1% результата на HumanEval+ и 98,7% паритета на двуязычном бенчмарке RU/EN.",
        "anti_slop_rule": "Replace 'almost all quality' with exact expert counts, checkpoint %, and benchmark retention %."
    },
    {
        "id": "bmp_017", "category": "b2b_metric_proof", "domain": "lidar_vegetative_canopy", "canon_id": "24_cartographic_field_expedition",
        "en_slop_before": "See right through dense forests with unmatched aerial mapping accuracy.",
        "en_canon_after": "5-echo waveform LiDAR at 120 m AGL penetrated closed boreal spruce canopy (LAI 4.6) to yield 6.8 bare-earth ground returns per m2, verified against 142 total-station ground control monuments (+/-3.1 cm RMSE).",
        "ru_slop_before": "Просвечивайте густые лесные массивы с непревзойдённой точностью воздушного сканирования.",
        "ru_canon_after": "Пятикратное отражение импульса LiDAR с высоты 120 м пробило сомкнутый еловый полог (LAI 4,6), обеспечив 6,8 точек рельефа на м2 по сверке со 142 тахеометрическими реперами (+/-3,1 см RMSE).",
        "anti_slop_rule": "State echo count, flight altitude, leaf-area index, ground returns/m2, and monument check count."
    },
    {
        "id": "bmp_018", "category": "b2b_metric_proof", "domain": "horology_isochronism", "canon_id": "16_luxury_horology_atelier_dark",
        "en_slop_before": "Engineered for extraordinary timekeeping precision across every moment.",
        "en_canon_after": "Free-sprung Breguet overcoil hairspring paired with twin series-coupled mainspring barrels holds amplitude between 275 and 292 degrees across the first 60 hours of its 72-hour reserve (chronometer certificate attached per serial).",
        "ru_slop_before": "Механизм спроектирован для исключительной точности хода в любой ситуации.",
        "ru_canon_after": "Свободная спираль со взведённым концевым витком Бреге и два последовательных заводных барабана удерживают амплитуду баланса в коридоре 275-292 градуса на протяжении первых 60 часов из 72-часового запаса хода.",
        "anti_slop_rule": "Provide balance amplitude degrees over hours of power reserve instead of generic praise."
    },
    {
        "id": "bmp_019", "category": "b2b_metric_proof", "domain": "museum_ticketing_queue", "canon_id": "14_kinetic_cultural_exhibition",
        "en_slop_before": "Visitors enjoy a smooth, hassle-free entry experience at major exhibitions.",
        "en_canon_after": "15-minute QR timed-entry cohorts with offline-capable Apple/Google Wallet passes cut Saturday atrium queue wait times from 42 minutes to under 4 minutes across 118,000 biennale admissions.",
        "ru_slop_before": "Посетители проходят на крупные выставки быстро и без очередей благодаря новой системе билетов.",
        "ru_canon_after": "Сеансы входа с шагом 15 минут и офлайн-билеты с QR-кодом сократили субботнее ожидание в атриуме с 42 до 4 минут на потоке 118 000 посетителей биеннале.",
        "anti_slop_rule": "Report slot interval, peak-day wait-time drop, and total admission volume."
    },
    {
        "id": "bmp_020", "category": "b2b_metric_proof", "domain": "steel_preassembly", "canon_id": "21_constructivist_editorial_ru",
        "en_slop_before": "High-precision fabrication accelerates industrial roof installation.",
        "en_canon_after": "CNC plasma-drilled bolt groups held to +/-0.5 mm hole-pitch tolerance allowed 48-meter span roof trusses to bolt up on crane hooks without reaming, cutting bay erection cycle from 4.5 shifts to 1.5 shifts.",
        "ru_slop_before": "Высокоточное заводское изготовление значительно ускоряет монтаж большепролётных кровель.",
        "ru_canon_after": "Сверловка болтовых групп на станках ЧПУ с допуском межцентрового шага +/-0,5 мм позволила собирать 48-метровые стропильные фермы без рассверловки на весу, сократив цикл монтажа пролёта с 4,5 до 1,5 смены.",
        "anti_slop_rule": "Give machining tolerance (+/-0.5 mm), span meters, eliminated field operation, and shift count."
    },
    {
        "id": "bmp_021", "category": "b2b_metric_proof", "domain": "dsp_cpu_headroom", "canon_id": "23_audio_dsp_modular_rack",
        "en_slop_before": "Run hundreds of plugin instances without slowing down your DAW.",
        "en_canon_after": "Hand-tuned NEON and AVX2 biquad filter cascades process 128 stereo tracks at 96 kHz / 64-sample buffer while consuming 6.4% single-core DSP load on Apple M2 Pro and Intel i7-13700K.",
        "ru_slop_before": "Запускайте сотни плагинов одновременно без тормозов и перегрузки процессора.",
        "ru_canon_after": "Векторизованные на NEON и AVX2 каскады биквадратных фильтров обрабатывают 128 стереодорожек при 96 кГц и буфере 64 сэмпла, занимая 6,4% ресурса на чипах M2 Pro и i7-13700K.",
        "anti_slop_rule": "Specify track count, sample rate, buffer size, % DSP load, and exact test CPUs."
    }
]
