"""Canonical page-type and section-block taxonomy for SmartLLM Studio."""
from __future__ import annotations

from pathlib import Path
import re
import struct
from typing import Any

_ASPECT_DIMS: dict[str, tuple[int, int]] = {
    "16:9": (1024, 576),
    "4:3": (896, 672),
    "1:1": (768, 768),
    "4:5": (640, 800),
    "3:4": (576, 768),
    "9:16": (640, 800),
}


def resolve_slot_dimensions(slot: str, canon_aspect: str = "16:9", hero_variant: str = "split") -> tuple[int, int]:
    """Return exact Z-Image (width, height) multiples of 64 matching the layout container aspect ratio."""
    s = str(slot or "").lower()
    aspect = str(canon_aspect or "16:9").strip()
    if s == "team":
        return (576, 768)  # Vertical 3:4 portrait matching .team-photo card
    if s == "logo":
        return (512, 512)
    if s == "gallery":
        return _ASPECT_DIMS.get(aspect if aspect in ("1:1", "4:3", "16:9") else ("4:3" if aspect in ("4:5", "3:4") else "16:9"), (1024, 576))
    if s == "hero":
        if str(hero_variant or "split") in ("centered", "overlay"):
            return (1024, 576)
        return _ASPECT_DIMS.get(aspect, (1024, 576))
    return _ASPECT_DIMS.get(aspect, (1024, 576))


def read_png_dimensions(path: Path, default: tuple[int, int] = (1024, 576)) -> tuple[int, int]:
    """Read actual PNG (width, height) from IHDR header if available, else return default."""
    try:
        hdr = path.read_bytes()[:24]
        if len(hdr) >= 24 and hdr[:8] == b"\x89PNG\r\n\x1a\n" and hdr[12:16] == b"IHDR":
            w, h = struct.unpack(">II", hdr[16:24])
            if w > 0 and h > 0:
                return int(w), int(h)
    except Exception:
        pass
    return default

_FEMALE_NAMES = {
    "анна", "елена", "марина", "ольга", "наталья", "татьяна", "светлана", "мария",
    "дарья", "екатерина", "ирина", "юлия", "ксения", "виктория", "полина", "алина",
    "анастасия", "валерия", "вера", "надежда", "людмила", "галина", "лариса",
    "ингрид", "клара", "софия", "emma", "claire", "clara", "elena", "sarah", "amara",
    "maeve", "ingrid", "laura", "sophia", "anna", "hannah", "julia", "lisa", "maria",
    "rachel", "chloe", "natalie", "victoria", "olivia", "alice", "nina", "helen",
}
_MALE_NAMES = {
    "александр", "иван", "дмитрий", "сергей", "илья", "михаил", "алексей", "андрей",
    "николай", "виктор", "павел", "константин", "максим", "артём", "артем", "роман",
    "денис", "евгений", "владимир", "олег", "тимур", "егор", "антон", "кирилл",
    "markus", "david", "julian", "viktor", "victor", "kenji", "haruto", "lukas",
    "erik", "sven", "daniel", "thomas", "michael", "james", "robert", "john", "alex",
    "paul", "lucas", "martin", "peter", "henrik", "nikolai", "ilya",
}


def infer_gender(name: str, explicit: str = "", slot_idx: int = 0) -> str:
    """Resolve consistent 'male' or 'female' gender cue for team portrait parity."""
    exp = str(explicit or "").strip().lower()
    if exp in ("female", "woman", "f", "ж", "жен", "женский"):
        return "female"
    if exp in ("male", "man", "m", "м", "муж", "мужской"):
        return "male"
    tokens = [t.lower() for t in re.findall(r"[A-Za-zА-Яа-яЁё]+", str(name or ""))]
    first = tokens[0] if tokens else ""
    if first in _FEMALE_NAMES:
        return "female"
    if first in _MALE_NAMES:
        return "male"
    if len(tokens) >= 2:
        last = tokens[1]
        if re.search(r"(?:ова|ева|ина|ская|цкая)$", last):
            return "female"
        if re.search(r"(?:ов|ев|ин|ский|цкий)$", last) and not first.endswith(("а", "я")):
            return "male"
    if re.search(r"[А-Яа-яЁё]", first):
        if first.endswith(("а", "я")) and first not in ("илья", "никита", "данила", "фома", "лука", "савва"):
            return "female"
        return "male"
    if first.endswith(("a", "ia", "na", "ra", "la", "ette", "elle", "ine")):
        return "female"
    return "female" if (slot_idx % 2 == 1) else "male"

AVAILABLE_BLOCKS: list[dict[str, str]] = [
    {"id": "hero", "title_ru": "Первый экран и главный визуал", "title_en": "Hero & Primary Visual"},
    {"id": "manifesto", "title_ru": "Девиз, позиционирование и обещание", "title_en": "Tagline, Positioning & Promise"},
    {"id": "values", "title_ru": "Отношение к продукту, людям и клиентам", "title_en": "Product, People & Client Values"},
    {"id": "priorities", "title_ru": "Топ-приоритеты и ключевые фразы", "title_en": "Top Priorities & Key Phrases"},
    {"id": "locations", "title_ru": "География, офисы и адреса", "title_en": "Locations, Offices & Addresses"},
    {"id": "features", "title_ru": "Ключевые услуги и преимущества", "title_en": "Services & Key Features"},
    {"id": "about", "title_ru": "О компании и подход", "title_en": "About & Methodology"},
    {"id": "stats", "title_ru": "Цифры, метрики и факты", "title_en": "Metrics & Proof Points"},
    {"id": "gallery", "title_ru": "Галерея проектов и визуалов", "title_en": "Project Gallery"},
    {"id": "pricing", "title_ru": "Тарифы, пакеты и стоимость", "title_en": "Pricing & Packages"},
    {"id": "testimonials", "title_ru": "Отзывы и кейсы клиентов", "title_en": "Testimonials & Case Studies"},
    {"id": "process", "title_ru": "Этапы работы", "title_en": "Process & Timeline"},
    {"id": "team", "title_ru": "Команда и эксперты", "title_en": "Team & Experts"},
    {"id": "blog", "title_ru": "Статьи и материалы", "title_en": "Articles & Insights"},
    {"id": "faq", "title_ru": "Вопросы и ответы", "title_en": "FAQ"},
    {"id": "legal", "title_ru": "Правовые документы и реквизиты", "title_en": "Legal & Company Details"},
    {"id": "cta", "title_ru": "Призыв к действию", "title_en": "Call to Action"},
    {"id": "contact", "title_ru": "Контакты и форма заявки", "title_en": "Contact & Request Form"},
    {"id": "footer", "title_ru": "Подвал сайта", "title_en": "Footer & Colophon"},
]

BLOCK_IDS: list[str] = [b["id"] for b in AVAILABLE_BLOCKS]
BLOCK_MAP: dict[str, dict[str, str]] = {b["id"]: b for b in AVAILABLE_BLOCKS}

PRESET_PAGES: list[dict[str, Any]] = [
    {
        "slug": "index",
        "title_ru": "Главная",
        "title_en": "Home",
        "purpose_ru": "Первый экран, ключевые услуги, доказательства и заявка.",
        "purpose_en": "Hero, core services, proof and primary conversion.",
        "default_blocks": ["hero", "manifesto", "values", "priorities", "features", "about", "gallery", "testimonials", "pricing", "faq", "locations", "contact", "footer"],
        "available_blocks": ["hero", "manifesto", "values", "priorities", "features", "about", "stats", "gallery", "testimonials", "pricing", "process", "faq", "cta", "locations", "contact", "footer"],
    },
    {
        "slug": "about",
        "title_ru": "О компании",
        "title_en": "About",
        "purpose_ru": "История, подход, цифры и команда.",
        "purpose_en": "Story, methodology, proof metrics and team.",
        "default_blocks": ["hero", "manifesto", "values", "priorities", "about", "stats", "team", "testimonials", "contact", "footer"],
        "available_blocks": ["hero", "manifesto", "values", "priorities", "about", "stats", "team", "process", "testimonials", "gallery", "cta", "locations", "contact", "footer"],
    },
    {
        "slug": "services",
        "title_ru": "Услуги и решения",
        "title_en": "Services",
        "purpose_ru": "Направления, процесс работы, тарифы и ответы на вопросы.",
        "purpose_en": "Capabilities, delivery process, packages and objections.",
        "default_blocks": ["hero", "manifesto", "priorities", "features", "process", "pricing", "faq", "cta", "contact", "footer"],
        "available_blocks": ["hero", "manifesto", "values", "priorities", "features", "process", "pricing", "stats", "testimonials", "faq", "cta", "locations", "contact", "footer"],
    },
    {
        "slug": "portfolio",
        "title_ru": "Проекты и кейсы",
        "title_en": "Portfolio",
        "purpose_ru": "Визуальные работы, результаты и отзывы клиентов.",
        "purpose_en": "Visual work, measurable outcomes and client proof.",
        "default_blocks": ["hero", "manifesto", "gallery", "stats", "testimonials", "cta", "contact", "footer"],
        "available_blocks": ["hero", "manifesto", "values", "gallery", "stats", "testimonials", "features", "process", "cta", "locations", "contact", "footer"],
    },
    {
        "slug": "pricing",
        "title_ru": "Тарифы и стоимость",
        "title_en": "Pricing",
        "purpose_ru": "Пакеты, условия, сравнение и ответы на возражения.",
        "purpose_en": "Packages, terms, comparison and objection handling.",
        "default_blocks": ["hero", "manifesto", "priorities", "pricing", "faq", "testimonials", "cta", "contact", "footer"],
        "available_blocks": ["hero", "manifesto", "values", "priorities", "pricing", "faq", "testimonials", "process", "stats", "cta", "locations", "contact", "footer"],
    },
    {
        "slug": "blog",
        "title_ru": "Блог и статьи",
        "title_en": "Blog",
        "purpose_ru": "Материалы, экспертиза и подписка на обновления.",
        "purpose_en": "Insights, articles, expertise and newsletter CTA.",
        "default_blocks": ["hero", "manifesto", "blog", "cta", "contact", "footer"],
        "available_blocks": ["hero", "manifesto", "values", "blog", "features", "cta", "contact", "footer"],
    },
    {
        "slug": "team",
        "title_ru": "Команда",
        "title_en": "Team",
        "purpose_ru": "Люди, роли, опыт и контакты для связи.",
        "purpose_en": "People, roles, expertise and direct contact.",
        "default_blocks": ["hero", "manifesto", "values", "team", "about", "stats", "cta", "contact", "footer"],
        "available_blocks": ["hero", "manifesto", "values", "priorities", "team", "about", "stats", "testimonials", "cta", "contact", "footer"],
    },
    {
        "slug": "faq",
        "title_ru": "Вопросы и ответы",
        "title_en": "FAQ",
        "purpose_ru": "Подробные ответы на частые вопросы.",
        "purpose_en": "Detailed answers to recurring questions.",
        "default_blocks": ["hero", "manifesto", "faq", "locations", "contact", "footer"],
        "available_blocks": ["hero", "manifesto", "faq", "locations", "contact", "footer"],
    },
    {
        "slug": "contact",
        "title_ru": "Контакты",
        "title_en": "Contact",
        "purpose_ru": "Форма заявки, реквизиты и быстрый ответ.",
        "purpose_en": "Request form, company details and quick response.",
        "default_blocks": ["hero", "locations", "contact", "faq", "footer"],
        "available_blocks": ["hero", "manifesto", "locations", "contact", "faq", "stats", "footer"],
    },
    {
        "slug": "legal",
        "title_ru": "Документы",
        "title_en": "Legal",
        "purpose_ru": "Политика конфиденциальности, условия и реквизиты.",
        "purpose_en": "Privacy policy, terms and company details.",
        "default_blocks": ["hero", "legal", "contact", "footer"],
        "available_blocks": ["hero", "legal", "locations", "contact", "footer"],
    },
]

PAGE_MAP: dict[str, dict[str, Any]] = {p["slug"]: p for p in PRESET_PAGES}
DEFAULT_PAGE_SLUGS: list[str] = ["index", "about", "services", "portfolio", "pricing", "contact"]


def page_title(slug: str, lang: str = "ru") -> str:
    preset = PAGE_MAP.get(slug)
    if preset:
        return str(preset["title_ru"] if str(lang).startswith("ru") else preset["title_en"])
    return slug.replace("-", " ").title()


def page_default_blocks(slug: str) -> list[str]:
    preset = PAGE_MAP.get(slug)
    blocks = list(preset["default_blocks"]) if preset else ["hero", "contact", "footer"]
    if "footer" not in blocks:
        blocks.append("footer")
    return blocks


def page_available_blocks(slug: str) -> list[str]:
    preset = PAGE_MAP.get(slug)
    return list(preset["available_blocks"]) if preset else list(BLOCK_IDS)


def default_page_blocks(slugs: list[str] | None = None) -> dict[str, list[str]]:
    selected = list(slugs or DEFAULT_PAGE_SLUGS)
    if "index" not in selected:
        selected.insert(0, "index")
    return {slug: page_default_blocks(slug) for slug in selected}


def clean_page_blocks(raw: Any, slugs: list[str] | None = None) -> dict[str, list[str]]:
    """Validate a per-page block mapping against the catalog, preserving order."""
    selected = list(slugs or DEFAULT_PAGE_SLUGS)
    if "index" not in selected:
        selected.insert(0, "index")
    source = raw if isinstance(raw, dict) else {}
    out: dict[str, list[str]] = {}
    for slug in selected:
        allowed = [b for b in page_available_blocks(slug) if b != "footer"]
        given = [b for b in (source.get(slug) or []) if b in allowed]
        if not given:
            given = [b for b in page_default_blocks(slug) if b != "footer"]
        if "hero" not in given:
            given.insert(0, "hero")
        if "contact" not in given and "contact" in allowed:
            given.append("contact")
        out[slug] = given + ["footer"]
    return out


def build_routes_from_pages(
    selected_pages: list[str] | None,
    page_blocks: dict[str, list[str]] | None,
    lang: str = "ru",
) -> list[dict[str, Any]]:
    selected = [s for s in (selected_pages or DEFAULT_PAGE_SLUGS) if s]
    if "index" not in selected:
        selected.insert(0, "index")
    blocks = page_blocks or default_page_blocks(selected)
    routes: list[dict[str, Any]] = []
    for slug in dict.fromkeys(selected):
        bricks = list(blocks.get(slug) or page_default_blocks(slug))
        if "footer" not in bricks:
            bricks.append("footer")
        filename = "index.html" if slug == "index" else f"{slug}.html"
        routes.append(
            {
                "slug": slug,
                "filename": filename,
                "path": "/" if filename == "index.html" else f"/{filename}",
                "title": page_title(slug, lang),
                "bricks": bricks,
            }
        )
    return routes


def build_default_company(brand_name: str, brief: str, lang: str = "ru") -> dict[str, Any]:
    """Generate editable brand foundation and contact details used by blocks, JSON-LD and llms.txt."""
    clean = " ".join((brief or "").strip().split())
    label = (brand_name or ("Проект" if str(lang).startswith("ru") else "Project")).strip()
    short = clean[:90].rstrip(".,;:") if clean else ("Современная компания" if str(lang).startswith("ru") else "A modern company")
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in label).strip("-") or "studio"
    slug = "-".join(part for part in slug.split("-") if part)[:32]
    if str(lang).startswith("ru"):
        return {
            "tagline": f"{label} — {short}",
            "positioning": f"{label} помогает клиентам получить понятный результат: {short}. Работаем прозрачно, фиксируем этапы и сопровождаем после запуска.",
            "values": [
                "Продукт: качество, проверенные материалы и внимание к деталям важнее скорости.",
                "Команда: прозрачные роли, уважение к времени и постоянное обучение.",
                "Клиенты: понятный план, честные сроки и поддержка после сдачи проекта.",
            ],
            "priorities": ["Качество", "Сроки", "Прозрачность", "Сопровождение"],
            "cities": ["Москва", "Санкт-Петербург", "Онлайн"],
            "address": "Москва, ул. Тверская, 12, стр. 1",
            "phone": "+7 495 120-34-56",
            "email": f"hello@{slug}.ru",
            "hours": "Пн–Пт 10:00–19:00",
            "social": [],
            "products": [
                {"name": "Базовый пакет", "scope": "Консультация, концепция и смета", "price": "15 000 ₽"},
                {"name": "Под ключ", "scope": "Полный цикл: проект, реализация, запуск", "price": "80 000 ₽"},
                {"name": "Сопровождение", "scope": "Индивидуальное ведение и поддержка 12 месяцев", "price": "200 000 ₽"},
            ],
            "history": {"founded": 2016, "milestones": ["2016 — основание студии", "2020 — 100-й реализованный проект", "2024 — собственная система контроля качества"]},
            "features": [
                {"title": "Индивидуальное проектирование", "detail": f"Решения для задач «{label}» по согласованной спецификации"},
                {"title": "Проверенные технологии", "detail": "Надёжные материалы и контроль на каждом этапе работ"},
                {"title": "Прозрачная смета", "detail": "Фиксация бюджета и сроков до старта реализации"},
                {"title": "Сопровождение запуска", "detail": "Передача документации и поддержка после сдачи"},
            ],
            "stats": [
                {"value": "10+", "label": "лет профильной практики"},
                {"value": "120+", "label": "завершённых проектов"},
                {"value": "100%", "label": "соблюдение согласованной сметы"},
                {"value": "4.9/5", "label": "оценка постоянных клиентов"},
            ],
            "process": [
                {"step": "01 Запрос", "detail": "Сбор вводных, оценка задач и фиксирование требований"},
                {"step": "02 Архитектура", "detail": "Подготовка концепции, этапов и детальной сметы"},
                {"step": "03 Реализация", "detail": "Разработка, сборка и промежуточный контроль качества"},
                {"step": "04 Сдача", "detail": "Передача результата, документации и пост-поддержка"},
            ],
            "team": [
                {"name": "Андрей Смирнов", "role": "Руководитель практики, архитектура решений", "gender": "male"},
                {"name": "Ольга Кузнецова", "role": "Ведущий инженер, контроль качества и стандартов", "gender": "female"},
                {"name": "Павел Захаров", "role": "Руководитель проектов, координация сроков и сметы", "gender": "male"},
                {"name": "Наталья Белова", "role": "Ведущий методолог, клиентский сервис и сопровождение", "gender": "female"},
            ],
        }
    return {
        "tagline": f"{label} — {short}",
        "positioning": f"{label} helps clients reach a clear outcome: {short}. We work transparently, fix milestones, and stay involved after launch.",
        "values": [
            "Product: verified quality, honest materials, and detail over speed.",
            "Team: clear roles, respect for time, and continuous learning.",
            "Clients: a readable plan, realistic timelines, and support after handoff.",
        ],
        "priorities": ["Quality", "Timelines", "Transparency", "Support"],
        "cities": ["Berlin", "Amsterdam", "Remote"],
        "address": "Berlin, Torstraße 12",
        "phone": "+49 30 1203456",
        "email": f"hello@{slug}.com",
        "hours": "Mon–Fri 10:00–19:00",
        "social": [],
        "products": [
            {"name": "Starter Tier", "scope": "Audit, architecture brief, and fixed delivery plan", "price": "$490"},
            {"name": "Standard Turnkey", "scope": "Full implementation, QA validation, and handoff", "price": "$2,400"},
            {"name": "Enterprise Retainer", "scope": "Dedicated specialist capacity and ongoing SLA", "price": "$6,500"},
        ],
        "history": {"founded": 2018, "milestones": ["2018 — studio founded", "2021 — 100+ client engagements delivered", "2024 — expanded international delivery"]},
        "features": [
            {"title": "Tailored Specification", "detail": f"Scoped strictly around {label} objectives and constraints"},
            {"title": "Verified Engineering", "detail": "Audited materials, reproducible workflows, and QA gates"},
            {"title": "Fixed Milestones", "detail": "Clear deliverables, schedules, and upfront pricing"},
            {"title": "Post-Launch Support", "detail": "Complete documentation and responsive team continuity"},
        ],
        "stats": [
            {"value": "8+", "label": "years of domain experience"},
            {"value": "120+", "label": "verified client deliveries"},
            {"value": "100%", "label": "milestone predictability"},
            {"value": "4.9/5", "label": "client retention score"},
        ],
        "process": [
            {"step": "01 Scoping", "detail": "Requirements audit, technical constraints, and fixed proposal"},
            {"step": "02 Design", "detail": "System architecture, prototype validation, and bill of materials"},
            {"step": "03 Delivery", "detail": "Iterative production with transparent weekly verification"},
            {"step": "04 Handover", "detail": "Documentation transfer, team onboarding, and ongoing SLA"},
        ],
        "team": [
            {"name": "Daniel Weber", "role": "Managing Director, systems architecture and delivery", "gender": "male"},
            {"name": "Hannah Lindner", "role": "Principal Engineer, technical standards and QA", "gender": "female"},
            {"name": "Thomas Becker", "role": "Operations Lead, logistics and client onboarding", "gender": "male"},
            {"name": "Claire Laurent", "role": "Client Advisory Lead, scheduling and support", "gender": "female"},
        ],
    }


def company_block_prompt(company: dict[str, Any], block_id: str, lang: str = "ru") -> str:
    """Turn structured brand-foundation fields into editable block copy."""
    c = company or {}
    tagline = str(c.get("tagline") or "").strip()
    positioning = str(c.get("positioning") or "").strip()
    values = [str(x).strip() for x in (c.get("values") or []) if str(x).strip()]
    priorities = [str(x).strip() for x in (c.get("priorities") or []) if str(x).strip()]
    cities = [str(x).strip() for x in (c.get("cities") or []) if str(x).strip()]
    address = str(c.get("address") or "").strip()
    phone = str(c.get("phone") or "").strip()
    email = str(c.get("email") or "").strip()
    hours = str(c.get("hours") or "").strip()
    if block_id == "manifesto":
        return " | ".join(x for x in (tagline, positioning) if x)
    if block_id == "values":
        return " | ".join(values)
    if block_id == "priorities":
        return " | ".join(priorities)
    if block_id == "locations":
        locs = list(cities)
        if address:
            locs.append(address)
        if hours:
            locs.append(hours)
        return " | ".join(locs)
    if block_id == "contact":
        parts = [x for x in (phone, email, address, hours) if x]
        if str(lang).startswith("ru"):
            return "Свяжитесь с нами: " + " · ".join(parts) if parts else "Оставьте заявку — ответим с планом и сметой."
        return "Contact us: " + " · ".join(parts) if parts else "Leave a request and receive a tailored plan."
    if block_id == "pricing":
        prods = [pr for pr in (c.get("products") or []) if isinstance(pr, dict) and str(pr.get("name") or "").strip()]
        if prods:
            return " | ".join(
                " — ".join(x for x in (str(pr.get("name") or "").strip(), str(pr.get("scope") or "").strip(), str(pr.get("price") or "").strip()) if x)
                for pr in prods[:4]
            )
    if block_id == "team":
        tm = [m for m in (c.get("team") or []) if isinstance(m, dict) and str(m.get("name") or "").strip()]
        if tm:
            return " | ".join(
                f"{str(m.get('name')).strip()} — {str(m.get('role') or ('Эксперт' if str(lang).startswith('ru') else 'Specialist')).strip()}"
                for m in tm[:4]
            )
    if block_id == "stats":
        st = [s for s in (c.get("stats") or []) if isinstance(s, dict) and str(s.get("value") or "").strip()]
        if st:
            return " | ".join(f"{str(s.get('value')).strip()} — {str(s.get('label') or '').strip()}" for s in st[:4])
    if block_id == "features":
        ft = [f for f in (c.get("features") or []) if isinstance(f, dict) and str(f.get("title") or "").strip()]
        if ft:
            return " | ".join(f"{str(f.get('title')).strip()} — {str(f.get('detail') or '').strip()}" for f in ft[:4])
    if block_id == "process":
        pr_list = [p for p in (c.get("process") or []) if isinstance(p, dict) and str(p.get("step") or "").strip()]
        if pr_list:
            return " | ".join(f"{str(p.get('step')).strip()} — {str(p.get('detail') or '').strip()}" for p in pr_list[:4])
    return ""
