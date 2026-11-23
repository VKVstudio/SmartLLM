"""Modular Block-Driven HTML5, CSS, JS, JSON-LD, GEO, Sitemap & CSP Renderer for SmartLLM Studio (v2: canon dossiers, layout variants, bilingual i18n, motion engine)."""

from __future__ import annotations

from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
from typing import Any

from . import __version__
from .kb_loader import resolve_canon_id
from .pages import resolve_slot_dimensions

STOCK_EN_HEADLINES = {"Deterministic Zero-Swap Edge Telemetry", "Modular Architectural Systems & Studio Craft"}
STOCK_RU_HEADLINES = {"Детерминированная телеметрия без подкачки", "Модульная архитектура и инженерный дизайн"}
STOCK_PROJECT_NAMES = {"Quartz-Field Atelier", "Кварц-Ателье"}

DATA_DIR = Path(__file__).resolve().parent / "data"

UI_STRINGS = {
    "ru": {
        "footer_nav": "Навигация", "footer_contacts": "Контакты", "rights": "Все права защищены.",
        "crumb_home": "Главная", "form_name": "Ваше имя", "form_email": "Email или телефон",
        "form_msg": "Кратко о задаче", "form_send": "Отправить заявку", "form_ok": "Заявка отправлена — мы свяжемся с вами.",
        "lang_label": "Язык сайта", "skip": "Перейти к основному содержанию", "select": "Выбрать",
        "legal_link": "Правовая информация", "status_nominal": "СТАТУС: АРХИТЕКТУРА И СТИЛЬ ПРОВЕРЕНЫ",
        "status_detail": "СТАТУС: АКТИВЕН РЕЖИМ ДЕТАЛЬНОГО ПРОСМОТРА", "inspect": "Детали архитектуры",
        "menu": "Меню", "pause_marquee": "Пауза ленты", "prev": "Назад", "next": "Вперёд",
        "gallery_region": "Галерея проектов", "pricing_region": "Таблица тарифов",
    },
    "en": {
        "footer_nav": "Navigation", "footer_contacts": "Contacts", "rights": "All rights reserved.",
        "crumb_home": "Home", "form_name": "Your Name", "form_email": "Work Email or Phone",
        "form_msg": "Project Details", "form_send": "Send Request", "form_ok": "Request sent — we will get back to you.",
        "lang_label": "Site language", "skip": "Skip to main content", "select": "Select Plan",
        "legal_link": "Legal Information", "status_nominal": "STATUS: VERIFIED STUDIO ARCHITECTURE",
        "status_detail": "STATUS: DETAILED SPECIFICATION VIEW", "inspect": "Inspect Architecture",
        "menu": "Menu", "pause_marquee": "Pause marquee", "prev": "Previous", "next": "Next",
        "gallery_region": "Project gallery", "pricing_region": "Pricing comparison table",
    },
}


def load_canon_dossier(canon_id: str) -> dict[str, Any]:
    cid = resolve_canon_id(canon_id)
    try:
        docs = json.loads((DATA_DIR / "canon_dossiers.json").read_text(encoding="utf-8"))
    except Exception:
        docs = {}
    default = {
        "motion": {"reveal": "rise", "stagger_ms": 40, "duration_ms": 240, "ease": "cubic-bezier(0.22, 1, 0.36, 1)", "scroll": "none", "marquee": False, "parallax": False},
        "micro": {"hover": "lift", "press_scale": 0.98, "press_ms": 120, "link": "underline", "card_hover": ""},
        "surface": "clean",
        "variants": {"hero": ["split"], "features": ["trio"], "gallery": ["grid"], "stats": ["cards"], "testimonials": ["cards"], "pricing": ["cards"], "team": ["cards"], "process": ["steps"]},
        "imagery": "editorial studio photography, crisp directional lighting",
        "team": "professional headshot, soft studio light, neutral backdrop",
    }
    d = dict(default)
    d.update(docs.get(cid) or docs.get(canon_id) or {})
    return d


def _parse_positive_price(price_raw: str) -> str:
    """Extract numeric price string strictly > 0; return '' when absent or non-numeric."""
    cleaned = str(price_raw or "").replace("\u00a0", " ")
    for m in re.finditer(r"\d[\d\s]*(?:[.,]\d{1,2})?", cleaned):
        tok = re.sub(r"\s+", "", m.group(0))
        if tok.count(",") == 1 and tok.count(".") == 0:
            left, right = tok.split(",", 1)
            tok = f"{left}.{right}" if len(right) <= 2 else f"{left}{right}"
        else:
            tok = tok.replace(",", "")
        try:
            if float(tok) > 0:
                return tok
        except ValueError:
            continue
    return ""


_SAFE_PAIR_RE = re.compile(r"\s*—\s*|\s+[–-]\s+|(?<!https)(?<!http)(?<!\d):\s+")


def _split_pair(item: str, default_right: str = "") -> tuple[str, str]:
    parts = [p.strip() for p in _SAFE_PAIR_RE.split(str(item or ""), maxsplit=1) if p.strip()]
    if not parts:
        return "", default_right
    if len(parts) == 1:
        return parts[0], default_right
    return parts[0], parts[1]


def _split_user_items(text: str, fallback: list[str], min_items: int = 3) -> list[str]:
    raw = [p.strip() for p in re.split(r"[\n|;]+", str(text or "")) if p.strip()]
    if len(raw) >= 2:
        return raw[:6]
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text or "")) if len(s.strip()) > 8]
    if len(sents) >= 2:
        return sents[:6]
    if text and text.strip():
        return [text.strip()] + fallback[: max(0, min_items - 1)]
    return fallback[:min_items]


def _build_tokens_css(
    pal: dict[str, Any],
    fonts: dict[str, str],
    layout: dict[str, Any],
    polarity: str = "light",
    canon_responsive: dict[str, Any] | None = None,
) -> str:
    typo = (canon_responsive or {}).get("typography") or {}
    h1_clamp = str((typo.get("h1") or {}).get("clamp") or "clamp(2rem, 3.6vw, 3.25rem)")
    h2_clamp = str((typo.get("h2") or {}).get("clamp") or "clamp(1.5rem, 2.5vw, 2.25rem)")
    radius_card = int(layout.get("radius_px", 8))
    radius_btn = int(layout.get("radius_button_px", min(radius_card, 12)))
    radius_in = int(layout.get("radius_input_px", min(radius_card, 10)))
    radius_badge = int(layout.get("radius_badge_px", 999))
    default_sh = "0 12px 32px rgba(0,0,0,0.34)" if polarity == "dark" else "0 8px 24px rgba(0,0,0,0.08)"
    return f""":root {{
  color-scheme: {polarity};
  --bg: {pal.get('bg', 'oklch(0.98 0.002 90)')};
  --surface: {pal.get('surface', 'oklch(0.945 0.003 90)')};
  --surface-elevated: {pal.get('surface_elevated', pal.get('surface', 'oklch(0.96 0.003 90)'))};
  --surface-fallback: {pal.get('surface_opaque_fallback', pal.get('surface', 'oklch(0.945 0.003 90)'))};
  --border: {pal.get('border', 'oklch(0.20 0.002 90)')};
  --border-control: {pal.get('border_control', pal.get('border', 'oklch(0.32 0.005 90)'))};
  --text: {pal.get('text', 'oklch(0.14 0.002 90)')};
  --text-muted: {pal.get('muted', 'oklch(0.42 0.005 90)')};
  --accent: {pal.get('accent', 'oklch(0.54 0.21 28)')};
  --accent-ink: {pal.get('accent_ink', 'oklch(0.99 0.002 90)')};
  --accent-2: {pal.get('accent_2', pal.get('accent', 'oklch(0.54 0.21 28)'))};
  --accent-3: {pal.get('accent_3', pal.get('muted', 'oklch(0.42 0.005 90)'))};
  --font-heading: {fonts.get('heading', "'Cormorant Garamond', Georgia, serif")};
  --font-sans: {fonts.get('body', "'Onest', system-ui, sans-serif")};
  --font-mono: {fonts.get('mono', "'JetBrains Mono', monospace")};
  --radius: {radius_card}px;
  --radius-card: {radius_card}px;
  --radius-button: {radius_btn}px;
  --radius-input: {radius_in}px;
  --radius-badge: {radius_badge}px;
  --pad-section: {layout.get('pad_clamp', 'clamp(2.5rem, 5vw, 5rem)')};
  --border-w: {int(layout.get('border_width_px', 1))}px;
  --shadow: {layout.get('shadow', default_sh)};
  --surface-blur: {int(layout.get('surface_blur_px', 0))}px;
  --heading-transform: {layout.get('heading_transform', 'none')};
  --heading-tracking: {layout.get('heading_tracking', 'normal')};
  --grid-gap: {layout.get('gap_clamp', 'clamp(1.25rem, 2.5vw, 2.5rem)')};
  --body-leading: {layout.get('body_leading', 1.6)};
  --h1-clamp: {h1_clamp};
  --h2-clamp: {h2_clamp};
  --bg-image: {layout.get('page_bg_image', 'none')};
}}
*, *::before, *::after {{ box-sizing: border-box; }}
html {{ scroll-padding-top: 4.75rem; font-size: 16px; scroll-behavior: smooth; }}
body {{ margin: 0; background-color: var(--bg); background-image: var(--bg-image); color: var(--text); font-family: var(--font-sans); line-height: var(--body-leading); font-variant-numeric: tabular-nums; max-width: 100%; overflow-x: clip; }}
main, .hero-shell, .section-block, .price-table-wrap {{ min-width: 0; max-width: 100%; }}
h1, h2, h3, p, li, figcaption, .spec-card, .price-card, .stat-card {{ overflow-wrap: break-word; hyphens: auto; }}
.skip-link {{ position: absolute; left: -9999px; top: 0.5rem; padding: 0.75rem 1rem; background: var(--accent); color: var(--accent-ink); min-height: 44px; min-width: 44px; display: inline-flex; align-items: center; text-decoration: none; }}
.skip-link:focus {{ left: 0.75rem; z-index: 100; }}
.site-header {{ position: sticky; top: 0; z-index: 40; background: var(--bg); border-bottom: var(--border-w) solid var(--border); backdrop-filter: blur(var(--surface-blur)); -webkit-backdrop-filter: blur(var(--surface-blur)); }}
.container {{ width: 100%; max-width: min(100%, var(--container-max, 82rem)); min-width: 0; margin-inline: auto; padding-inline: clamp(1rem, 4vw, 3.5rem); }}
.header-inner {{ display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; min-height: 4.5rem; gap: 0.75rem; }}
.brand-link {{ display: inline-flex; align-items: center; gap: 0.75rem; font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: var(--text); text-decoration: none; min-height: 44px; min-width: 44px; }}
.brand-link img {{ width: 36px; height: 36px; display: block; border-radius: var(--radius-badge); object-fit: cover; }}
.nav-list {{ display: flex; flex-wrap: wrap; gap: 0.5rem; list-style: none; margin: 0; padding: 0; }}
.nav-list a {{ color: var(--text); text-decoration: none; padding: 0.5rem 0.75rem; min-height: 44px; min-width: 44px; display: inline-flex; align-items: center; border-radius: var(--radius-button); font-size: 0.9375rem; }}
.nav-list a[aria-current="page"] {{ background: var(--surface); border: 1px solid var(--border); font-weight: 600; }}
.nav-list a:focus-visible, .btn:focus-visible, input:focus-visible, textarea:focus-visible, .lang-switch button:focus-visible, .price-table-wrap:focus-visible, .gal-filmstrip .canon-grid:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.hero-shell {{ min-height: min(86svh, 800px); display: flex; align-items: center; padding-block: var(--pad-section); border-bottom: 1px solid var(--border); container-type: inline-size; }}
.canon-grid {{ width: 100%; display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: var(--grid-gap); align-items: center; }}
.section-block .canon-grid {{ align-items: stretch; }}
.hero-lead {{ grid-column: span 7; min-width: 0; }}
.hero-figure {{ grid-column: span 5; min-width: 0; margin: 0; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 1rem; }}
.hero-figure img, .gallery-card img {{ width: 100%; height: auto; display: block; border-radius: var(--radius-card); object-fit: cover; }}
.eyebrow {{ font-family: var(--font-mono); font-size: 0.8125rem; color: var(--text-muted); margin: 0 0 0.75rem 0; letter-spacing: 0.03em; }}
h1 {{ font-family: var(--font-heading); font-size: var(--h1-clamp); line-height: 1.12; margin: 0 0 1.25rem 0; max-width: 24ch; text-transform: var(--heading-transform); letter-spacing: var(--heading-tracking); text-wrap: balance; }}
h2 {{ font-family: var(--font-heading); font-size: var(--h2-clamp); line-height: 1.18; margin: 0 0 1.25rem 0; text-transform: var(--heading-transform); letter-spacing: var(--heading-tracking); text-wrap: balance; }}
h3 {{ font-family: var(--font-heading); font-size: 1.25rem; margin: 0 0 0.5rem 0; letter-spacing: var(--heading-tracking); }}
.lead-copy {{ font-size: 1.125rem; max-width: 62ch; margin: 0 0 1.5rem 0; }}
.cta-row {{ display: flex; flex-wrap: wrap; gap: 0.875rem; margin-bottom: 1rem; align-items: center; }}
.btn {{ display: inline-flex; align-items: center; justify-content: center; min-height: 44px; min-width: 44px; padding: 0.65rem 1.25rem; font-family: var(--font-mono); font-size: 0.875rem; font-weight: 600; border: var(--border-w) solid var(--border-control); border-radius: var(--radius-button); cursor: pointer; text-decoration: none; background: var(--accent); color: var(--accent-ink); box-shadow: var(--shadow); }}
.btn-secondary {{ background: var(--surface-elevated); color: var(--text); }}
.btn.nav-toggle {{ display: none; min-height: 44px; min-width: 44px; }}
.section-block {{ padding-block: var(--pad-section); border-bottom: 1px solid var(--border); container-type: inline-size; }}
.section-block:not(#hero) {{ content-visibility: auto; contain-intrinsic-size: auto 600px; }}
.spec-card, .price-card, .review-card {{ grid-column: span 4; display: flex; flex-direction: column; justify-content: space-between; background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius-card); padding: 1.5rem; gap: 0.75rem; min-width: 0; box-shadow: var(--shadow); backdrop-filter: blur(var(--surface-blur)); -webkit-backdrop-filter: blur(var(--surface-blur)); }}
.stat-card, .team-card, .blog-card {{ grid-column: span 4; background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius-card); padding: 1.5rem; min-width: 0; box-shadow: var(--shadow); backdrop-filter: blur(var(--surface-blur)); -webkit-backdrop-filter: blur(var(--surface-blur)); }}
.stat-value {{ font-family: var(--font-heading); font-size: clamp(1.9rem, 3vw, 2.6rem); line-height: 1; margin: 0 0 0.5rem 0; color: var(--accent); }}
.process-step {{ grid-column: span 3; background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius-card); padding: 1.25rem; min-width: 0; box-shadow: var(--shadow); }}
.process-step .step-index {{ font-family: var(--font-mono); font-size: 0.8125rem; color: var(--accent); margin: 0 0 0.5rem 0; }}
.team-avatar {{ width: 52px; height: 52px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; background: var(--accent); color: var(--accent-ink); font-family: var(--font-heading); font-size: 1.1rem; font-weight: 700; margin-bottom: 0.75rem; }}
.team-photo {{ width: 100%; height: auto; aspect-ratio: 3 / 4; object-fit: cover; object-position: 50% 15%; border-radius: var(--radius-card); display: block; margin-bottom: 0.75rem; border: 1px solid var(--border); }}
.blog-card .blog-meta {{ font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted); margin: 0 0 0.5rem 0; }}
.cta-banner {{ grid-column: span 12; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 1.25rem; background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius-card); padding: clamp(1.5rem, 3vw, 2.5rem); box-shadow: var(--shadow); }}
.cta-banner h2 {{ margin: 0; }}
.legal-copy {{ max-width: 72ch; }}
.legal-copy p {{ margin: 0 0 1rem 0; }}
.manifesto {{ max-width: 76ch; }}
.manifesto-statement {{ font-family: var(--font-heading); font-size: clamp(1.8rem, 3.4vw, 3rem); line-height: 1.15; margin: 0 0 1.25rem 0; letter-spacing: var(--heading-tracking); }}
.priority-list {{ list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem; }}
.priority-item {{ display: flex; align-items: baseline; gap: 0.85rem; background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius-card); padding: 0.9rem 1.1rem; box-shadow: var(--shadow); }}
.priority-index {{ font-family: var(--font-mono); font-size: 0.8125rem; color: var(--accent); }}
.location-card {{ grid-column: span 4; background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius-card); padding: 1.5rem; box-shadow: var(--shadow); }}
.location-card address {{ font-style: normal; color: var(--text-muted); margin: 0.5rem 0; }}
.contact-layout {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.75fr); gap: clamp(1.5rem, 3vw, 2.5rem); align-items: start; }}
.contact-details {{ background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius-card); padding: 1.5rem; box-shadow: var(--shadow); }}
.contact-details a {{ color: var(--accent); }}
.contact-details address {{ font-style: normal; color: var(--text-muted); margin: 0.5rem 0; }}
.gallery-card {{ grid-column: span 6; background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius-card); padding: 1rem; margin: 0; min-width: 0; box-shadow: var(--shadow); backdrop-filter: blur(var(--surface-blur)); -webkit-backdrop-filter: blur(var(--surface-blur)); }}
.gallery-card figcaption {{ font-family: var(--font-mono); font-size: 0.8125rem; color: var(--text-muted); margin-top: 0.65rem; }}
.carousel-controls {{ display: flex; gap: 0.5rem; margin-bottom: 0.75rem; justify-content: flex-end; }}
.carousel-btn {{ min-height: 44px; min-width: 44px; padding: 0.45rem 0.9rem; }}
.faq-item {{ background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius-card); padding: 1.25rem 1.5rem; margin-bottom: 1rem; box-shadow: var(--shadow); }}
.intake-form {{ display: grid; gap: 1rem; max-width: 36rem; background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius-card); padding: 1.5rem; box-shadow: var(--shadow); }}
.intake-form input, .intake-form textarea {{ width: 100%; min-height: 44px; padding: 0.65rem 0.85rem; border: 1px solid var(--border-control); border-radius: var(--radius-input); background: var(--bg); color: var(--text); font-family: var(--font-sans); font-size: 1rem; }}
.form-status {{ margin: 0; min-height: 1.25em; font-family: var(--font-mono); font-size: 0.875rem; color: var(--accent); }}
.hp-trap {{ position: absolute; left: -9999px; opacity: 0; pointer-events: none; }}
.site-footer {{ padding-block: 2.25rem 1.5rem; font-family: var(--font-mono); font-size: 0.8125rem; color: var(--text-muted); border-top: var(--border-w) solid var(--border); }}
.footer-grid {{ display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 0.8fr) minmax(0, 1fr); gap: clamp(1.5rem, 3vw, 3rem); padding-bottom: 1.75rem; }}
.footer-brand p {{ margin: 0.75rem 0 0 0; max-width: 34ch; }}
.footer-h {{ font-family: var(--font-mono); font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text); margin: 0 0 0.75rem 0; }}
.footer-nav {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 0.4rem; }}
.footer-nav a {{ color: var(--text-muted); text-decoration: none; display: inline-flex; align-items: center; min-height: 36px; }}
.footer-nav a:hover {{ color: var(--accent); }}
.footer-contacts p, .footer-contacts address {{ margin: 0 0 0.4rem 0; font-style: normal; }}
.footer-contacts a {{ color: var(--accent); text-decoration: none; }}
.footer-bottom {{ display: flex; flex-wrap: wrap; gap: 0.75rem; justify-content: space-between; border-top: 1px solid var(--border); padding-top: 1.1rem; }}
.footer-bottom p {{ margin: 0; }}
.footer-bottom a {{ color: var(--text-muted); }}
.crumbs {{ padding-block: 1rem 0; font-family: var(--font-mono); font-size: 0.75rem; }}
.crumbs ol {{ list-style: none; display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0; padding: 0; }}
.crumbs li + li::before {{ content: "/"; margin-right: 0.5rem; color: var(--text-muted); }}
.crumbs a {{ color: var(--text-muted); text-decoration: none; }}
.crumbs a:hover {{ color: var(--accent); }}
.crumbs [aria-current] {{ color: var(--text); }}
.lang-switch {{ display: inline-flex; border: 1px solid var(--border-control); border-radius: var(--radius-button); overflow: hidden; }}
.lang-switch button {{ min-height: 44px; min-width: 44px; padding: 0.3rem 0.65rem; background: transparent; color: var(--text-muted); border: 0; font-family: var(--font-mono); font-size: 0.75rem; font-weight: 600; cursor: pointer; }}
.lang-switch button[aria-pressed="true"] {{ background: var(--accent); color: var(--accent-ink); }}
.scroll-progress {{ position: fixed; top: 0; left: 0; height: 3px; width: 100%; transform-origin: 0 50%; transform: scaleX(0); background: var(--accent); z-index: 60; pointer-events: none; }}
.marquee {{ overflow: hidden; border-bottom: 1px solid var(--border); padding-block: 0.45rem; padding-inline: 0.75rem; background: var(--surface); display: flex; align-items: center; gap: 0.75rem; }}
.marquee-track {{ display: flex; gap: 3rem; width: max-content; animation: slm-marquee 26s linear infinite; }}
.marquee:hover .marquee-track, .marquee:focus-within .marquee-track, .marquee[data-paused="true"] .marquee-track {{ animation-play-state: paused; }}
.marquee-toggle {{ min-height: 44px; min-width: 44px; padding: 0.25rem 0.6rem; flex-shrink: 0; z-index: 2; }}
.marquee-track span {{ font-family: var(--font-heading); font-size: 1.05rem; font-weight: 700; text-transform: var(--heading-transform); letter-spacing: var(--heading-tracking); white-space: nowrap; color: var(--text-muted); }}
@keyframes slm-marquee {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-50%); }} }}
@media (max-width: 900px) {{ .footer-grid {{ grid-template-columns: 1fr; }} }}
@container (max-width: 760px) {{ .hero-lead, .hero-figure, .spec-card, .price-card, .review-card, .gallery-card, .stat-card, .team-card, .blog-card, .process-step {{ grid-column: span 12; }} }}
@media (max-width: 900px) {{ .hero-lead, .hero-figure, .spec-card, .price-card, .review-card, .gallery-card, .stat-card, .team-card, .blog-card, .process-step, .location-card {{ grid-column: span 12; }} .contact-layout, .priority-list {{ grid-template-columns: 1fr; }} }}
@media (max-width: 767px) {{
  .header-inner {{ min-height: 3.75rem; }}
  .btn.nav-toggle {{ display: inline-flex; }}
  .site-header nav {{ width: 100%; order: 4; }}
  .nav-list[data-open="false"] {{ display: none; }}
  .nav-list[data-open="true"] {{ display: flex; flex-direction: column; width: 100%; padding-bottom: 0.5rem; }}
  .btn, .intake-form input, .intake-form textarea {{ min-height: 48px; }}
}}
@media (prefers-reduced-motion: reduce) {{ *, *::before, *::after {{ transition: none !important; animation: none !important; }} html {{ scroll-behavior: auto; }} }}
@media print {{ [data-reveal] {{ opacity: 1 !important; transform: none !important; clip-path: none !important; }} .scroll-progress, .marquee {{ display: none; }} }}
"""


def _build_canon_css(card: dict[str, Any], d: dict[str, Any], polarity: str = "light") -> str:
    motion = d.get("motion") or {}
    micro = d.get("micro") or {}
    surface = str(d.get("surface") or "clean")
    reveal = str(motion.get("reveal") or "rise")
    dur = int(motion.get("duration_ms", 240))
    ease = str(motion.get("ease") or "ease-out")
    stagger = int(motion.get("stagger_ms", 40))
    press = float(micro.get("press_scale", 0.98))
    press_ms = int(micro.get("press_ms", 120))
    hover = str(micro.get("hover") or "lift")
    reveal_from = {
        "rise": "translateY(26px)",
        "fade": "none",
        "scale": "scale(0.96)",
        "clip": "translateY(14px)",
        "skew": "translateY(18px) skewY(1.2deg)",
    }.get(reveal, "translateY(26px)")
    clip_extra = "clip-path: inset(0 0 12% 0);" if reveal == "clip" else ""
    clip_done = "clip-path: inset(0 0 0 0);" if reveal == "clip" else ""
    cards = ".spec-card, .price-card, .review-card, .stat-card, .team-card, .blog-card, .gallery-card, .location-card, .process-step, .priority-item, .faq-item"
    cards_is = f":is({cards})"
    hover_css = ""
    if hover == "lift":
        hover_css = f"{cards} {{ transition: transform {press_ms}ms {ease}, box-shadow {press_ms}ms {ease}, border-color {press_ms}ms {ease}; }} @media (hover: hover) {{ {cards_is}:hover {{ transform: translateY(-3px); box-shadow: var(--shadow); border-color: var(--accent); }} }}"
    elif hover == "invert":
        hover_css = f"{cards} {{ transition: background-color {max(press_ms, 100)}ms {ease}, color {max(press_ms, 100)}ms {ease}; }} @media (hover: hover) {{ {cards_is}:hover {{ background: var(--accent); color: var(--accent-ink); }} {cards_is}:hover :is(h3, p, .eyebrow, .stat-value, .step-index, .blog-meta) {{ color: inherit; }} }}"
    elif hover == "glow":
        hover_css = f"{cards} {{ transition: box-shadow {press_ms}ms {ease}, transform {press_ms}ms {ease}; }} @media (hover: hover) {{ {cards_is}:hover {{ box-shadow: 0 0 0 1px var(--accent), var(--shadow); transform: translateY(-2px); }} }}"
    elif hover == "underline":
        hover_css = f"{cards} {{ transition: border-color {press_ms}ms {ease}; }} @media (hover: hover) {{ {cards_is}:hover {{ border-color: var(--accent); }} }}"
    if surface == "brutal":
        press_css = f".btn:active, {cards_is}:active {{ transform: translate(4px, 4px); box-shadow: none; }}"
    else:
        press_css = f".btn:active, {cards_is}:active {{ transform: scale({press}); }}"
    surface_css = ""
    if surface in ("grain", "paper"):
        op = "0.05" if surface == "grain" else "0.035"
        surface_css = f"""body::after {{ content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 5; opacity: {op}; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E"); }}"""
    elif surface == "glass":
        surface_css = f"""{cards} {{ background: color-mix(in oklab, var(--surface) 78%, transparent); backdrop-filter: blur(20px) saturate(1.35); -webkit-backdrop-filter: blur(20px) saturate(1.35); border-color: var(--border); position: relative; }}
{cards_is}::before {{ content: ""; position: absolute; inset: 0 0 auto 0; height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent); border-radius: inherit; pointer-events: none; }}
[data-solid-ui="true"] {cards_is} {{ backdrop-filter: none; -webkit-backdrop-filter: none; background: var(--surface-fallback, var(--surface)); }}
@media (prefers-reduced-transparency: reduce) {{ {cards} {{ backdrop-filter: none; -webkit-backdrop-filter: none; background: var(--surface-fallback, var(--surface)); }} }}
@supports not (backdrop-filter: blur(1px)) {{ {cards} {{ backdrop-filter: none; -webkit-backdrop-filter: none; background: var(--surface-fallback, var(--surface)); }} }}"""
    elif surface == "mesh":
        surface_css = """body::before { content: ""; position: fixed; inset: -12%; z-index: -1; pointer-events: none; background: radial-gradient(42% 46% at 22% 28%, var(--accent-2), transparent 70%), radial-gradient(38% 42% at 78% 68%, var(--accent-3), transparent 72%); opacity: 0.14; animation: slm-drift 14s ease-in-out infinite alternate; }
@keyframes slm-drift { from { transform: translate3d(-2%, -1%, 0) scale(1); } to { transform: translate3d(2%, 2%, 0) scale(1.06); } }"""
    elif surface == "clay":
        surface_css = f"""{cards} {{ box-shadow: inset 0 2px 6px rgba(255,255,255,0.28), inset 0 -6px 12px rgba(0,0,0,0.12), var(--shadow); }}"""
    elif surface == "tactile":
        surface_css = f""".btn {{ background-image: linear-gradient(135deg, rgba(255,255,255,0.32), transparent 55%); }}
.btn:active {{ box-shadow: inset 0 3px 8px rgba(0,0,0,0.28); }}
{cards} {{ transition: transform 400ms cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow {press_ms}ms {ease}; }}
@media (hover: hover) {{ {cards_is}:hover {{ transform: scale(1.015); }} }}"""
    elif surface == "brutal":
        surface_css = f"""{cards} {{ border: 3px solid var(--text); box-shadow: 6px 6px 0 var(--border); }}
.btn {{ border: 3px solid var(--text); box-shadow: 5px 5px 0 var(--border); }}"""
    elif surface == "kinetic":
        surface_css = f"""{cards} {{ border-width: 2px; }}"""
    link_css = ""
    if str(micro.get("link") or "underline") == "underline":
        link_css = """.nav-list a, .footer-nav a, .crumbs a { background-image: linear-gradient(currentColor, currentColor); background-size: 0% 1px; background-repeat: no-repeat; background-position: 0 100%; transition: background-size 180ms ease-out; }
@media (hover: hover) { .nav-list a:hover, .footer-nav a:hover, .crumbs a:hover { background-size: 100% 1px; } }"""
    variant_css = """
.canon-grid[data-count="1"] > * { grid-column: span 12; }
.canon-grid[data-count="2"] > *, .canon-grid[data-count="4"] > * { grid-column: span 6; }
.canon-grid[data-count="3"] > *, .canon-grid[data-count="6"] > * { grid-column: span 4; }
.canon-grid[data-count="4"] > .process-step { grid-column: span 6; }
.hero-centered .canon-grid { display: flex; flex-direction: column; align-items: center; text-align: center; }
.hero-centered .hero-lead { grid-column: auto; max-width: 56rem; display: flex; flex-direction: column; align-items: center; }
.hero-centered h1 { max-width: 22ch; }
.hero-centered .hero-figure { grid-column: auto; width: 100%; max-width: 62rem; margin-top: 2rem; }
.hero-bento .hero-figure { padding: 1.25rem; }
.hero-overlay { position: relative; }
.hero-overlay .hero-figure { position: absolute; inset: 0; grid-column: auto; border: 0; padding: 0; border-radius: 0; background: none; }
.hero-overlay .hero-figure img { width: 100%; height: 100%; object-fit: cover; opacity: 0.34; border-radius: 0; }
.hero-overlay .hero-lead { position: relative; grid-column: span 12; max-width: 46rem; z-index: 2; }
.hero-overlay::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, color-mix(in oklab, var(--bg) 92%, transparent) 0%, color-mix(in oklab, var(--bg) 72%, transparent) 52%, transparent 100%); pointer-events: none; z-index: 1; }
.feat-asym .spec-card:first-child { grid-column: span 8; }
.feat-asym .canon-grid[data-count="3"] .spec-card:first-child { grid-column: span 6; }
.feat-asym .canon-grid[data-count="3"] .spec-card:nth-child(n+2) { grid-column: span 3; }
.feat-asym .canon-grid[data-count="4"] .spec-card:nth-child(1), .feat-asym .canon-grid[data-count="4"] .spec-card:nth-child(4) { grid-column: span 7; }
.feat-asym .canon-grid[data-count="4"] .spec-card:nth-child(2), .feat-asym .canon-grid[data-count="4"] .spec-card:nth-child(3) { grid-column: span 5; }
.feat-bento .spec-card:nth-child(1) { grid-column: span 6; }
.feat-bento .spec-card:nth-child(2) { grid-column: span 6; }
.feat-bento .spec-card:nth-child(n+3) { grid-column: span 4; }
.feat-bento .canon-grid[data-count="3"] .spec-card { grid-column: span 4; }
.feat-bento .canon-grid[data-count="4"] .spec-card:nth-child(1), .feat-bento .canon-grid[data-count="4"] .spec-card:nth-child(4) { grid-column: span 7; }
.feat-bento .canon-grid[data-count="4"] .spec-card:nth-child(2), .feat-bento .canon-grid[data-count="4"] .spec-card:nth-child(3) { grid-column: span 5; }
.feat-matrix .spec-card { border-radius: var(--radius-card); }
.gal-mosaic .gallery-card:first-child { grid-column: span 7; grid-row: span 2; }
.gal-mosaic .gallery-card:nth-child(n+2) { grid-column: span 5; }
.gal-mosaic .canon-grid[data-count="2"] .gallery-card, .gal-mosaic .canon-grid[data-count="4"] .gallery-card { grid-column: span 6; grid-row: auto; }
.gal-mosaic .gallery-card:first-child img { height: 100%; object-fit: cover; }
.gal-mosaic .canon-grid[data-count="2"] .gallery-card:first-child img, .gal-mosaic .canon-grid[data-count="4"] .gallery-card:first-child img { height: auto; }
.gal-filmstrip .canon-grid { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 1rem; padding-bottom: 0.75rem; }
.gal-filmstrip .gallery-card { min-width: min(340px, 82vw); scroll-snap-align: start; grid-column: auto; }
.stat-band .canon-grid { grid-template-columns: repeat(auto-fit, minmax(min(100%, 165px), 1fr)); }
.stat-band .stat-card { grid-column: auto !important; background: none; border: 0; box-shadow: none; padding: 0; backdrop-filter: none; }
.stat-band .stat-value { font-size: clamp(2.2rem, 4vw, 3.4rem); }
.review-quotes .review-card { grid-column: span 12 !important; background: none; border: 0; box-shadow: none; border-left: 3px solid var(--accent); border-radius: 0; padding: 0.25rem 0 0.25rem 1.5rem; backdrop-filter: none; }
.review-quotes .review-card p:first-child { font-family: var(--font-heading); font-size: clamp(1.2rem, 2vw, 1.6rem); line-height: 1.35; }
.price-table-wrap { grid-column: span 12; overflow-x: auto; border: var(--border-w) solid var(--border); border-radius: var(--radius-card); box-shadow: var(--shadow); }
.price-table { width: 100%; border-collapse: collapse; font-size: 0.9375rem; background: var(--surface); }
.price-table th, .price-table td { border: 1px solid var(--border); padding: 0.85rem 1rem; text-align: left; vertical-align: top; }
.price-table th { font-family: var(--font-heading); font-size: 1.05rem; background: var(--bg); }
.price-table td:first-child, .price-table th[scope="row"] { font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.timeline { list-style: none; margin: 0; padding: 0 0 0 1.75rem; position: relative; grid-column: span 12; }
.timeline::before { content: ""; position: absolute; left: 0.4rem; top: 0.4rem; bottom: 0.4rem; width: 2px; background: var(--border); }
.timeline li { position: relative; padding: 0 0 1.5rem 0.75rem; }
.timeline li::before { content: ""; position: absolute; left: -1.75rem; top: 0.35rem; width: 0.9rem; height: 0.9rem; border-radius: 50%; background: var(--accent); border: 2px solid var(--bg); }
.timeline .step-index { font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent); margin: 0 0 0.25rem 0; }
@media (max-width: 900px) { .canon-grid[data-count] > *, .feat-asym .spec-card, .feat-bento .spec-card, .gal-mosaic .gallery-card { grid-column: span 12 !important; grid-row: auto !important; } }
@media (max-width: 767px) { .hero-overlay .hero-figure { position: relative; inset: auto; margin-bottom: 1rem; } .hero-overlay .hero-figure img { opacity: 1; height: auto; } .hero-overlay::after { display: none; } }
"""
    return f""":root {{ --reveal-dur: {dur}ms; --reveal-ease: {ease}; --reveal-stagger: {stagger}ms; --press-scale: {press}; }}
.js .section-block [data-reveal] {{ opacity: 0; transform: {reveal_from}; {clip_extra} transition: opacity var(--reveal-dur) var(--reveal-ease), transform var(--reveal-dur) var(--reveal-ease), clip-path var(--reveal-dur) var(--reveal-ease); transition-delay: var(--rd, 0ms); }}
.js .section-block [data-reveal].is-revealed {{ opacity: 1; transform: none; {clip_done} }}
{hover_css}
{press_css}
{surface_css}
{link_css}
{variant_css}
"""


def _build_motion_and_ui_js(stack: str, motion: str, lang: str, d: dict[str, Any], i18n: dict[str, dict[str, str]], bilingual: bool) -> str:
    motion_cfg = d.get("motion") or {}
    stagger = int(motion_cfg.get("stagger_ms", 40))
    parallax = bool(motion_cfg.get("parallax"))
    progress = str(motion_cfg.get("scroll") or "none") == "progress"
    ui = UI_STRINGS.get(lang, UI_STRINGS["en"])
    i18n_json = json.dumps(i18n, ensure_ascii=False).replace("</", "<\\/") if bilingual else "{}"
    return f"""(function () {{
  "use strict";
  var root = document.documentElement;
  root.setAttribute("data-stack", "{stack}");
  root.setAttribute("data-motion", "{motion}");
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.setAttribute("data-reduced-motion", reduced ? "reduce" : "no-preference");
  var I18N = {i18n_json};
  var BILINGUAL = {"true" if bilingual else "false"};
  var PRIMARY = "{lang}";
  function applyLang(l) {{
    if (!BILINGUAL) return;
    root.lang = l;
    var nodes = document.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) {{
      var e = I18N[nodes[i].getAttribute("data-i18n")];
      if (e && e[l] && nodes[i].children.length === 0) nodes[i].textContent = e[l];
    }}
    var alts = document.querySelectorAll("[data-i18n-alt]");
    for (var j = 0; j < alts.length; j++) {{
      var ea = I18N[alts[j].getAttribute("data-i18n-alt")];
      if (ea && ea[l]) alts[j].setAttribute("alt", ea[l]);
    }}
    var arias = document.querySelectorAll("[data-i18n-aria]");
    for (var a = 0; a < arias.length; a++) {{
      var ear = I18N[arias[a].getAttribute("data-i18n-aria")];
      if (ear && ear[l]) arias[a].setAttribute("aria-label", ear[l]);
    }}
    var metas = document.querySelectorAll("[data-i18n-content]");
    for (var k = 0; k < metas.length; k++) {{
      var em = I18N[metas[k].getAttribute("data-i18n-content")];
      if (em && em[l]) metas[k].setAttribute("content", em[l]);
    }}
    var btns = document.querySelectorAll(".lang-switch button");
    for (var b = 0; b < btns.length; b++) btns[b].setAttribute("aria-pressed", btns[b].getAttribute("data-lang") === l ? "true" : "false");
    try {{ localStorage.setItem("slm-lang", l); }} catch (err) {{}}
  }}
  if (BILINGUAL) {{
    var saved = null;
    try {{ saved = localStorage.getItem("slm-lang"); }} catch (err) {{}}
    var switcher = document.querySelector(".lang-switch");
    if (switcher) switcher.addEventListener("click", function (ev) {{
      var btn = ev.target.closest("button[data-lang]");
      if (btn) applyLang(btn.getAttribute("data-lang"));
    }});
    if (saved && saved !== PRIMARY) applyLang(saved);
  }}
  var navToggle = document.getElementById("mobile-nav-toggle");
  var navList = document.getElementById("primary-nav-list");
  if (navToggle && navList) {{
    navToggle.addEventListener("click", function () {{
      var expanded = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", expanded ? "false" : "true");
      navList.setAttribute("data-open", expanded ? "false" : "true");
    }});
  }}
  var mqToggle = document.querySelector(".marquee-toggle");
  if (mqToggle) {{
    mqToggle.addEventListener("click", function () {{
      var wrap = mqToggle.closest(".marquee");
      if (!wrap) return;
      var paused = wrap.getAttribute("data-paused") === "true";
      wrap.setAttribute("data-paused", paused ? "false" : "true");
      mqToggle.setAttribute("aria-pressed", paused ? "false" : "true");
    }});
  }}
  document.querySelectorAll(".carousel-btn[data-dir]").forEach(function (cbtn) {{
    cbtn.addEventListener("click", function () {{
      var sec = cbtn.closest(".section-block");
      var grid = sec ? sec.querySelector(".canon-grid") : null;
      if (!grid) return;
      var dir = parseInt(cbtn.getAttribute("data-dir") || "1", 10) || 1;
      grid.scrollBy({{ left: dir * 340, behavior: reduced ? "auto" : "smooth" }});
    }});
  }});
  if (!reduced) {{
    var revealEls = Array.prototype.slice.call(document.querySelectorAll(".section-block [data-reveal]"));
    if (revealEls.length) {{
      var groups = {{}};
      revealEls.forEach(function (el) {{
        var sec = el.closest("section") || root;
        var key = sec.id || "root";
        groups[key] = groups[key] || 0;
        el.style.setProperty("--rd", (groups[key]++ * {stagger}) + "ms");
      }});
      var io = null;
      var cleanupReveal = function () {{
        window.removeEventListener("scroll", revealVisible);
        window.removeEventListener("resize", revealVisible);
      }};
      var revealVisible = function () {{
        var vh = window.innerHeight || root.clientHeight || 900;
        var remaining = 0;
        for (var idx = 0; idx < revealEls.length; idx++) {{
          var el = revealEls[idx];
          if (el.classList.contains("is-revealed")) continue;
          if (el.getBoundingClientRect().top <= vh + 160) {{
            el.classList.add("is-revealed");
            if (io) io.unobserve(el);
          }} else {{
            remaining++;
          }}
        }}
        if (remaining === 0) cleanupReveal();
      }};
      if ("IntersectionObserver" in window) {{
        revealVisible();
        root.classList.add("js");
        io = new IntersectionObserver(function (entries) {{
          entries.forEach(function (en) {{
            if (en.isIntersecting) {{
              en.target.classList.add("is-revealed");
              io.unobserve(en.target);
            }}
          }});
        }}, {{ threshold: 0.01, rootMargin: "0px 0px 80px 0px" }});
        var pendingReveal = 0;
        revealEls.forEach(function (el) {{
          if (!el.classList.contains("is-revealed")) {{
            io.observe(el);
            pendingReveal++;
          }}
        }});
        if (pendingReveal > 0) {{
          window.requestAnimationFrame(revealVisible);
          window.setTimeout(revealVisible, 450);
          window.addEventListener("scroll", revealVisible, {{ passive: true }});
          window.addEventListener("resize", revealVisible, {{ passive: true }});
        }}
      }} else {{
        revealEls.forEach(function (el) {{ el.classList.add("is-revealed"); }});
        root.classList.add("js");
      }}
    }} else {{
      root.classList.add("js");
    }}
    var bar = document.querySelector(".scroll-progress");
    var heroImg = document.querySelector(".hero-figure img");
    var ticking = false;
    var onScroll = function () {{
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {{
        ticking = false;
        var max = root.scrollHeight - window.innerHeight;
        if (bar) bar.style.transform = "scaleX(" + (max > 0 ? Math.min(1, window.scrollY / max) : 0) + ")";
        {"if (heroImg) { var r = heroImg.getBoundingClientRect(); if (r.bottom > 0 && r.top < window.innerHeight) heroImg.style.transform = \"translateY(\" + (window.scrollY * 0.06).toFixed(1) + \"px)\"; }" if parallax else ""}
      }});
    }};
    {"window.addEventListener(\"scroll\", onScroll, { passive: true }); onScroll();" if (progress or parallax) else ""}
  }} else {{
    document.querySelectorAll("[data-reveal]").forEach(function (el) {{ el.classList.add("is-revealed"); }});
    root.classList.add("js");
  }}
  var form = document.querySelector(".intake-form");
  if (form) form.addEventListener("submit", function (ev) {{
    ev.preventDefault();
    var trap = form.querySelector(".hp-trap input, input.hp-trap");
    if (trap && trap.value) return;
    var btn = form.querySelector("button[type=submit]");
    var status = form.querySelector(".form-status");
    if (btn) btn.disabled = true;
    if (status) status.textContent = {json.dumps(ui["form_ok"], ensure_ascii=False)};
    window.setTimeout(function () {{
      if (btn) btn.disabled = false;
      if (status) status.textContent = "";
      form.reset();
    }}, 4000);
  }});
}})();
"""


def _t(ctx: dict[str, Any], key: str, primary: str, secondary: str | None = None) -> tuple[str, str]:
    primary = str(primary or "")
    if ctx.get("bilingual"):
        ent = ctx["i18n"].setdefault(key, {})
        ent[ctx["lang"]] = primary
        if secondary:
            ent[ctx["alt_lang"]] = str(secondary)
        return html.escape(primary), f' data-i18n="{key}"'
    return html.escape(primary), ""


def _loc_get(loc: dict[str, Any] | None, *path: str) -> str:
    cur: Any = loc or {}
    for p in path:
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(p)
    return str(cur or "").strip() if isinstance(cur, str) else ""


def _loc_items(loc: dict[str, Any] | None, block: str) -> list[str]:
    txt = _loc_get(loc, "copy", block)
    return [p.strip() for p in re.split(r"[\n|;]+", txt) if p.strip()] if txt else []


def _variant(page_meta: dict[str, Any], d: dict[str, Any], block: str, page_idx: int) -> str:
    allowed = (d.get("variants") or {}).get(block) or ["default"]
    chosen = str((page_meta.get("variants") or {}).get(block) or "")
    if chosen in allowed:
        return chosen
    return allowed[page_idx % len(allowed)]


def _render_route_html(
    route: dict[str, Any],
    all_routes: list[dict[str, Any]],
    project_name: str,
    brief: str,
    lang: str,
    bilingual: bool,
    card: dict[str, Any],
    copy_pairs: list[dict[str, Any]],
    faqs: list[dict[str, str]],
    geo_cfg: dict[str, Any],
    seo_cfg: dict[str, Any],
    logo_relpath: str,
    favicon_relpath: str,
    base_url: str,
    csp_meta: str,
    css_text: str,
    js_text: str,
    stack: str,
    motion: str,
    audience: str = "",
    block_prompts: dict[str, str] | None = None,
    company: dict[str, Any] | None = None,
    asset_rev: int = 1,
    chrome: dict[str, Any] | None = None,
    page_meta: dict[str, Any] | None = None,
    gallery_images: list[str] | None = None,
    hero_dims: tuple[int, int] = (1024, 1024),
    dossier: dict[str, Any] | None = None,
    alt_lang: str = "en",
    loc: dict[str, Any] | None = None,
    loc_chrome: dict[str, Any] | None = None,
    page_images: dict[str, str] | None = None,
    team_images: list[str] | None = None,
    image_dims: dict[str, tuple[int, int]] | None = None,
    i18n: dict[str, dict[str, str]] | None = None,
    page_idx: int = 0,
    polarity: str = "light",
) -> str:
    d = dossier or load_canon_dossier(card.get("id", ""))
    ctx: dict[str, Any] = {"bilingual": bilingual, "lang": lang, "alt_lang": alt_lang, "i18n": i18n if i18n is not None else {}}
    pm = page_meta or {}
    hero_pm = pm.get("hero") if isinstance(pm.get("hero"), dict) else {}
    headings_pm = pm.get("headings") if isinstance(pm.get("headings"), dict) else {}
    seo_pm = pm.get("seo") if isinstance(pm.get("seo"), dict) else {}
    chrome_cfg = chrome or {}
    ui = UI_STRINGS.get(lang, UI_STRINGS["en"])
    ui_alt = UI_STRINGS.get(alt_lang, UI_STRINGS["en"])
    slug = route["slug"]
    page_url = f"{base_url}{route['path']}"
    bp_map = dict(block_prompts or {})
    bp_map.update(route.get("block_prompts") or {})
    company_cfg = company or {}
    copy_map = route.get("copy_ru" if lang == "ru" else "copy_en") or {}
    raw_hl = str(copy_map.get("headline") or "").strip()
    raw_sub = str(copy_map.get("subhead") or "").strip()
    is_custom_project = project_name not in STOCK_PROJECT_NAMES
    is_stock_hl = raw_hl in STOCK_EN_HEADLINES or raw_hl in STOCK_RU_HEADLINES

    hero_custom = str(bp_map.get("hero") or "").strip()
    if route["slug"] == "index":
        if raw_hl and not (is_custom_project and is_stock_hl):
            h1_text = raw_hl
        elif hero_custom:
            first_part = re.split(r"[.!?\n|;]", hero_custom)[0].strip()
            h1_text = first_part[:78] if len(first_part) >= 8 else f"{project_name}"
        elif seo_cfg.get("title"):
            h1_text = str(seo_cfg["title"])
        else:
            h1_text = f"{project_name} — {brief[:56]}" if brief else project_name
        if hero_custom:
            lead_copy = hero_custom
        elif raw_sub and not (is_custom_project and is_stock_hl):
            lead_copy = raw_sub
        elif brief:
            lead_copy = f"{brief} ({audience})" if audience else brief
        else:
            lead_copy = str(company_cfg.get("positioning") or company_cfg.get("tagline") or project_name)
    else:
        h1_text = raw_hl if (raw_hl and not is_stock_hl) else f"{project_name} — {route['title']}"
        lead_copy = raw_sub or hero_custom or brief or project_name
    if str(hero_pm.get("headline") or "").strip():
        h1_text = str(hero_pm["headline"]).strip()
    if str(hero_pm.get("subhead") or "").strip():
        lead_copy = str(hero_pm["subhead"]).strip()

    active_faqs = list(faqs)
    faq_prompt_txt = str(bp_map.get("faq") or "").strip()
    if faq_prompt_txt and ("?" in faq_prompt_txt or "|" in faq_prompt_txt):
        parsed_faqs: list[dict[str, str]] = []
        for chunk in re.split(r"[|\n]+", faq_prompt_txt):
            chunk = chunk.strip()
            if "?" in chunk:
                q_part, a_part = chunk.split("?", 1)
                parsed_faqs.append({"q": q_part.strip() + "?", "a": a_part.strip(" :-—") or lead_copy})
        if parsed_faqs:
            active_faqs = parsed_faqs
    loc_faqs = (loc or {}).get("faqs") or []

    schema_type = str(seo_cfg.get("schema_type") or "Organization")
    page_title = str(seo_pm.get("title") or seo_cfg.get("title") or f"{project_name} — {route['title']}")
    meta_desc = str(seo_pm.get("description") or seo_cfg.get("description") or lead_copy[:155])
    loc_title = _loc_get(loc, "seo", "title")
    loc_desc = _loc_get(loc, "seo", "description")

    bricks = [b.lower() if b != "FAQ" else "faq" for b in (route.get("bricks") or ["hero", "features", "about", "pricing", "faq", "contact", "footer"])]

    org_node: dict[str, Any] = {"@type": schema_type, "@id": f"{base_url}/#org", "name": project_name, "url": f"{base_url}/", "logo": f"{base_url}/{logo_relpath}"}
    c_phone = str(company_cfg.get("phone") or "").strip()
    c_email = str(company_cfg.get("email") or "").strip()
    c_address = str(company_cfg.get("address") or "").strip()
    c_cities = [str(x).strip() for x in (company_cfg.get("cities") or []) if str(x).strip()]
    c_hours = str(company_cfg.get("hours") or "").strip()
    c_social = [str(x).strip() for x in (company_cfg.get("social") or []) if str(x).strip()]
    if c_phone:
        org_node["telephone"] = c_phone
    if c_email:
        org_node["email"] = c_email
    if c_address:
        addr_obj: dict[str, Any] = {"@type": "PostalAddress", "streetAddress": c_address, "addressLocality": c_cities[0] if c_cities else ""}
        c_country = str(company_cfg.get("country") or ("RU" if lang == "ru" else "")).strip()
        if c_country:
            addr_obj["addressCountry"] = c_country
        org_node["address"] = addr_obj
    if c_cities:
        org_node["areaServed"] = c_cities
    if c_hours:
        org_node["openingHours"] = c_hours
    if c_social:
        org_node["sameAs"] = c_social
    if c_phone or c_email:
        org_node["contactPoint"] = {"@type": "ContactPoint", "contactType": "sales", "telephone": c_phone or "", "email": c_email or "", "availableLanguage": ["ru", "en"]}
    graph_nodes: list[dict[str, Any]] = [
        org_node,
        {"@type": "WebSite", "@id": f"{base_url}/#website", "url": f"{base_url}/", "name": project_name, "publisher": {"@id": f"{base_url}/#org"}, "inLanguage": lang},
        {"@type": "WebPage", "@id": f"{page_url}#webpage", "url": page_url, "name": page_title, "isPartOf": {"@id": f"{base_url}/#website"}, "description": meta_desc, "dateModified": str(geo_cfg.get("last_updated") or "2026-11-16")},
    ]
    if slug != "index":
        graph_nodes.append(
            {"@type": "BreadcrumbList", "@id": f"{page_url}#breadcrumbs", "itemListElement": [{"@type": "ListItem", "position": 1, "name": project_name, "item": f"{base_url}/"}, {"@type": "ListItem", "position": 2, "name": route["title"], "item": page_url}]}
        )
    if (c_phone or c_address) and route["slug"] in ("index", "contact"):
        graph_nodes.append({"@type": "LocalBusiness", "@id": f"{page_url}#localbusiness", "name": project_name, "url": page_url, "telephone": c_phone, "email": c_email, "address": {"@type": "PostalAddress", "streetAddress": c_address, "addressLocality": c_cities[0] if c_cities else ""}, "areaServed": c_cities, "openingHours": c_hours})
    catalog = [pr for pr in (company_cfg.get("products") or []) if isinstance(pr, dict) and str(pr.get("name") or "").strip()]
    if catalog and ("pricing" in bricks or "features" in bricks):
        offers = []
        services = []
        for pr in catalog[:6]:
            price_raw = str(pr.get("price") or "")
            pos_price = _parse_positive_price(price_raw)
            if pos_price:
                offers.append({
                    "@type": "Offer",
                    "name": str(pr.get("name")),
                    "description": str(pr.get("scope") or ""),
                    "price": pos_price,
                    "priceCurrency": "RUB" if ("₽" in price_raw or "руб" in price_raw.lower()) else ("EUR" if "€" in price_raw else "USD"),
                    "availability": "https://schema.org/InStock",
                })
            else:
                services.append({
                    "@type": "Service",
                    "name": str(pr.get("name")),
                    "description": str(pr.get("scope") or brief[:155]),
                    "provider": {"@id": f"{base_url}/#org"},
                })
        if offers:
            graph_nodes.append({"@type": "Product", "@id": f"{base_url}/#catalog", "name": f"{project_name} — catalog", "brand": {"@id": f"{base_url}/#org"}, "offers": offers})
        elif services:
            graph_nodes.extend(services)
    if "faq" in bricks and active_faqs:
        graph_nodes.append({"@type": "FAQPage", "@id": f"{page_url}#faq", "mainEntity": [{"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in active_faqs]})
    json_ld_graph = {"@context": "https://schema.org", "@graph": graph_nodes}
    safe_json_ld = json.dumps(json_ld_graph, ensure_ascii=False).replace("</", "<\\/")

    nav_labels = chrome_cfg.get("nav_labels") if isinstance(chrome_cfg.get("nav_labels"), dict) else {}
    loc_nav = (loc_chrome or {}).get("nav_labels") or {}
    nav_items = []
    for r in all_routes:
        label = str(nav_labels.get(r["slug"]) or r["title"])
        tx, at = _t(ctx, f"chrome:nav:{r['slug']}", label, str(loc_nav.get(r["slug"]) or ""))
        cur = ' aria-current="page"' if r["filename"] == route["filename"] else ""
        nav_items.append(f'          <li><a href="{r["filename"]}"{cur}{at}>{tx}</a></li>')
    nav_links = "\n".join(nav_items)

    # Single-URL JS-switched bilingual pages must not emit hreflang links to non-existent /en/ or /ru/ folders
    hreflang_block = ""
    lang_switch = ""
    if bilingual:
        lx, la = _t(ctx, "chrome:lang_label", ui["lang_label"], ui_alt["lang_label"])
        lang_switch = (
            f'<div class="lang-switch" role="group" aria-label="{lx}"{la.replace('data-i18n=', 'data-i18n-aria=')}>'
            f'<button type="button" data-lang="ru" aria-pressed="{"true" if lang == "ru" else "false"}">RU</button>'
            f'<button type="button" data-lang="en" aria-pressed="{"true" if lang == "en" else "false"}">EN</button></div>'
        )

    sections_html: list[str] = []
    c_fallbacks: list[str] = []
    for src in (
        list(company_cfg.get("priorities") or []),
        list(company_cfg.get("values") or []),
        [f"{f.get('title')} — {f.get('detail')}" for f in (company_cfg.get("features") or []) if isinstance(f, dict) and f.get("title")],
        list((company_cfg.get("history") or {}).get("milestones") or []),
    ):
        for entry in src:
            s_entry = str(entry or "").strip()
            if s_entry and s_entry not in c_fallbacks:
                c_fallbacks.append(s_entry)
    for extra in (str(company_cfg.get("positioning") or "").strip(), lead_copy, brief, project_name):
        if extra and extra not in c_fallbacks and len(c_fallbacks) < 4:
            c_fallbacks.append(extra)
    while len(c_fallbacks) < 3:
        c_fallbacks.append(lead_copy or project_name)

    hero_rel = (page_images or {}).get(slug) or "assets/hero_primary.png"
    route_dims = (image_dims or {}).get(hero_rel) or ((1024, 576) if (page_images or {}).get(slug) else hero_dims)
    hero_alt_meta = str(seo_pm.get("hero_alt") or "").strip() or f"{project_name} — {route['title']}"
    hero_variant = _variant(pm, d, "hero", page_idx)
    hero_cls = {
        "centered": " hero-centered",
        "editorial_poster": " hero-centered",
        "command_stage": " hero-centered",
        "overlay": " hero-overlay",
        "fullbleed_scrim": " hero-overlay",
        "bento_showcase": " hero-bento",
    }.get(hero_variant, "")
    marquee_html = ""
    if d.get("motion", {}).get("marquee"):
        mq_base = str(company_cfg.get("tagline") or project_name)
        mq = f"{mq_base} · {project_name} · "
        mtx, mat = _t(ctx, "chrome:marquee", mq, _loc_get(loc_chrome, "marquee") or mq)
        marquee_html = (
            f'    <div class="marquee" data-paused="false">'
            f'<button class="btn btn-secondary marquee-toggle" type="button" aria-pressed="false" aria-label="{html.escape(ui["pause_marquee"], quote=True)}">❚❚</button>'
            f'<div class="marquee-track" aria-hidden="true"><span{mat}>{mtx}</span><span{mat}>{mtx}</span></div></div>\n'
        )

    def h2_for(block_id: str, default: str) -> tuple[str, str]:
        custom = str(headings_pm.get(block_id) or "").strip() or default
        return _t(ctx, f"{slug}:{block_id}:h2", custom, _loc_get(loc, "headings", block_id))

    for brick in bricks:
        if brick == "hero":
            eyebrow_txt = str(hero_pm.get("eyebrow") or "").strip() or f"{card['name']} · {project_name.upper()}"
            cta_primary = str(hero_pm.get("cta_label") or "").strip() or ("Оставить заявку" if lang == "ru" else "Start a Project")
            cta_secondary = str(hero_pm.get("cta_secondary") or "").strip()
            hero_alt = hero_alt_meta
            contact_route = next((r for r in all_routes if r.get("slug") == "contact"), None)
            primary_href = "#contact" if "contact" in bricks else (contact_route["filename"] if contact_route else "#contact")
            if cta_secondary:
                sec_route = next((r for r in all_routes if r.get("slug") == "portfolio"), None) or contact_route
                sec_href = sec_route["filename"] if sec_route else "#contact"
                stx, sat = _t(ctx, f"{slug}:hero:cta2", cta_secondary, _loc_get(loc, "hero", "cta_secondary"))
                secondary_html = f'<a class="btn btn-secondary" href="{html.escape(sec_href, quote=True)}"{sat}>{stx}</a>'
            else:
                secondary_html = ""
            etx, eat = _t(ctx, f"{slug}:hero:eyebrow", eyebrow_txt, _loc_get(loc, "hero", "eyebrow"))
            htx, hat = _t(ctx, f"{slug}:hero:h1", h1_text, _loc_get(loc, "hero", "headline"))
            ltx, lat = _t(ctx, f"{slug}:hero:lead", lead_copy, _loc_get(loc, "hero", "subhead"))
            ctx1, cta1 = _t(ctx, f"{slug}:hero:cta1", cta_primary, _loc_get(loc, "hero", "cta_label"))
            altx, altat = _t(ctx, f"{slug}:hero:alt", hero_alt, _loc_get(loc, "seo", "hero_alt"))
            sections_html.append(
                f"""    <section class="hero-shell{hero_cls}" id="hero">
      <div class="container canon-grid">
        <div class="hero-lead">
          <p class="eyebrow"{eat}>{etx}</p>
          <h1{hat}>{htx}</h1>
          <p class="lead-copy"{lat}>{ltx}</p>
          <div class="cta-row">
            <a class="btn" href="{html.escape(primary_href, quote=True)}"{cta1}>{ctx1}</a>
            {secondary_html}
          </div>
        </div>
        <figure class="hero-figure">
          <img src="{html.escape(hero_rel, quote=True)}?v={asset_rev}" width="{route_dims[0]}" height="{route_dims[1]}" alt="{altx}"{altat.replace('data-i18n=', 'data-i18n-alt=')} fetchpriority="high" loading="eager" decoding="sync">
        </figure>
      </div>
    </section>"""
            )
        elif brick == "manifesto":
            mf_parts = _split_user_items(bp_map.get("manifesto", ""), [str(company_cfg.get("tagline") or project_name), str(company_cfg.get("positioning") or brief)], min_items=2)
            loc_mf = _loc_items(loc, "manifesto")
            statement = mf_parts[0] if mf_parts else project_name
            positioning = mf_parts[1] if len(mf_parts) > 1 else brief
            stx, sat = _t(ctx, f"{slug}:manifesto:statement", statement, loc_mf[0] if loc_mf else "")
            ptx, pat = _t(ctx, f"{slug}:manifesto:position", positioning, loc_mf[1] if len(loc_mf) > 1 else "")
            extra = []
            for i, x in enumerate(mf_parts[2:5]):
                xtx, xat = _t(ctx, f"{slug}:manifesto:item:{i}", x, loc_mf[i + 2] if len(loc_mf) > i + 2 else "")
                extra.append(f'          <article class="spec-card" data-reveal><p class="eyebrow">{"ПОЗИЦИЯ" if lang == "ru" else "POSITION"}</p><p{xat}>{xtx}</p></article>')
            sections_html.append(
                f"""    <section class="section-block manifesto-section" id="manifesto">
      <div class="container manifesto" data-reveal>
        <p class="eyebrow">{"ДЕВИЗ И ПОЗИЦИОНИРОВАНИЕ" if lang == "ru" else "TAGLINE & POSITIONING"}</p>
        <blockquote class="manifesto-statement"{sat}>{stx}</blockquote>
        <p class="lead-copy"{pat}>{ptx}</p>
        {f'<div class="canon-grid" data-count="{len(extra)}">{chr(10).join(extra)}</div>' if extra else ''}
      </div>
    </section>"""
            )
        elif brick == "values":
            val_items = _split_user_items(bp_map.get("values", ""), [str(x) for x in (company_cfg.get("values") or [])] or [lead_copy], min_items=3)
            loc_val = _loc_items(loc, "values")
            default_heads = ["ПРОДУКТ", "КОМАНДА", "КЛИЕНТЫ"] if lang == "ru" else ["PRODUCT", "TEAM", "CLIENTS"]
            val_cards = []
            for idx, item in enumerate(val_items[:4]):
                val_head, val_body = _split_pair(item, item)
                if val_body == item:
                    val_head = default_heads[idx % len(default_heads)]
                loc_item = loc_val[idx] if idx < len(loc_val) else ""
                _, loc_body = _split_pair(loc_item, loc_item) if loc_item else ("", "")
                btx, bat = _t(ctx, f"{slug}:values:body:{idx}", val_body, loc_body)
                val_cards.append(f'          <article class="spec-card" data-reveal><p class="eyebrow">{html.escape(val_head)}</p><p{bat}>{btx}</p></article>')
            htx, hat = h2_for("values", "Наши принципы и отношение" if lang == "ru" else "Our Values & Attitude")
            sections_html.append(
                f"""    <section class="section-block" id="values">
      <div class="container">
        <h2{hat}>{htx}</h2>
        <div class="canon-grid" data-count="{len(val_cards)}">
{chr(10).join(val_cards)}
        </div>
      </div>
    </section>"""
            )
        elif brick == "priorities":
            pri_items = _split_user_items(bp_map.get("priorities", ""), [str(x) for x in (company_cfg.get("priorities") or [])] or ["Качество", "Сроки", "Прозрачность"], min_items=3)
            loc_pri = _loc_items(loc, "priorities")
            pri_cards = []
            for idx, item in enumerate(pri_items[:6]):
                itx, iat = _t(ctx, f"{slug}:priorities:item:{idx}", item, loc_pri[idx] if idx < len(loc_pri) else "")
                pri_cards.append(f'          <li class="priority-item" data-reveal><span class="priority-index">{idx + 1:02d}</span><span{iat}>{itx}</span></li>')
            htx, hat = h2_for("priorities", "Топ-приоритеты компании" if lang == "ru" else "Company Priorities")
            sections_html.append(
                f"""    <section class="section-block" id="priorities">
      <div class="container">
        <h2{hat}>{htx}</h2>
        <ul class="priority-list">
{chr(10).join(pri_cards)}
        </ul>
      </div>
    </section>"""
            )
        elif brick == "locations":
            loc_cities = [str(x) for x in (company_cfg.get("cities") or []) if str(x).strip()]
            loc_address = str(company_cfg.get("address") or "").strip()
            loc_hours = str(company_cfg.get("hours") or "").strip()
            loc_prompt_items = _split_user_items(bp_map.get("locations", ""), loc_cities or [loc_address], min_items=1) if (bp_map.get("locations") or loc_cities or loc_address) else []
            loc_by_city: dict[str, str] = {}
            for lp in loc_prompt_items:
                l_city, l_addr = _split_pair(lp, "")
                if l_city and l_addr:
                    loc_by_city[l_city.lower()] = l_addr
            loc_cards = []
            for idx, city in enumerate(loc_cities or loc_prompt_items[:4]):
                city_name, city_fallback_addr = _split_pair(city, "")
                matched_addr = loc_by_city.get(city_name.lower(), "")
                if not matched_addr:
                    for lc_key, lc_val in loc_by_city.items():
                        if city_name.lower() in lc_key or lc_key in city_name.lower():
                            matched_addr = lc_val
                            break
                detail = matched_addr or city_fallback_addr or (loc_address if idx == 0 else "")
                ctx_, cat_ = _t(ctx, f"{slug}:locations:city:{idx}", city_name or city, "")
                loc_cards.append(
                    f"""          <article class="location-card" data-reveal>
            <p class="eyebrow">{"ОФИС" if lang == "ru" else "OFFICE"} {idx + 1:02d}</p>
            <h3{cat_}>{ctx_}</h3>
            {f'<address>{html.escape(detail)}</address>' if detail else ''}
            {f'<p class="eyebrow">{html.escape(loc_hours)}</p>' if loc_hours else ''}
          </article>"""
                )
            if not loc_cards:
                loc_cards.append(f'          <article class="location-card" data-reveal><h3>{html.escape(project_name)}</h3><p>{"Онлайн и выезд по согласованию" if lang == "ru" else "Remote and on-site by arrangement"}</p></article>')
            htx, hat = h2_for("locations", "География и адреса" if lang == "ru" else "Locations & Addresses")
            sections_html.append(
                f"""    <section class="section-block" id="locations">
      <div class="container">
        <h2{hat}>{htx}</h2>
        <div class="canon-grid" data-count="{len(loc_cards)}">
{chr(10).join(loc_cards)}
        </div>
      </div>
    </section>"""
            )
        elif brick == "features":
            f_default = [f"{f.get('title')} — {f.get('detail')}" for f in (company_cfg.get("features") or []) if isinstance(f, dict) and f.get("title")] or c_fallbacks
            f_items = _split_user_items(bp_map.get("features", ""), f_default, min_items=3)
            loc_f = _loc_items(loc, "features")
            fv = _variant(pm, d, "features", page_idx)
            f_cls = {
                "asym": " feat-asym",
                "editorial_rows": " feat-asym",
                "sticky_narrative": " feat-asym",
                "bento": " feat-bento",
                "bento_asymmetric": " feat-bento",
                "hairline_matrix": " feat-matrix",
            }.get(fv, "")
            cards = []
            for i, item in enumerate(f_items[:6]):
                itx, iat = _t(ctx, f"{slug}:features:item:{i}", item, loc_f[i] if i < len(loc_f) else "")
                cards.append(f'          <article class="spec-card" data-reveal><h3>0{i+1} / {"НАПРАВЛЕНИЕ" if lang == "ru" else "CAPABILITY"}</h3><p{iat}>{itx}</p></article>')
            htx, hat = h2_for("features", "Преимущества и ключевые направления" if lang == "ru" else "Key Capabilities & Services")
            sections_html.append(
                f"""    <section class="section-block{f_cls}" id="features">
      <div class="container">
        <h2{hat}>{htx}</h2>
        <div class="canon-grid" data-count="{len(cards)}">
{chr(10).join(cards)}
        </div>
      </div>
    </section>"""
            )
        elif brick == "about":
            ab_items = _split_user_items(bp_map.get("about", ""), c_fallbacks, min_items=3)
            loc_ab = _loc_items(loc, "about")
            abtx, abat = _t(ctx, f"{slug}:about:lead", str(bp_map.get("about") or brief), _loc_get(loc, "copy", "about"))
            geo_list = list(geo_cfg.get("facts", [])[:2])
            geo_cards = "\n".join(
                f'          <article class="spec-card" data-reveal><h3>{"ФАКТ" if lang == "ru" else "VERIFIED FACT"}</h3><p>{html.escape(str(fc.get("claim", "")))}</p></article>'
                for fc in geo_list
            )
            ab_limit = 2 if len(geo_list) >= 2 else 3
            ab_cards = []
            for i, item in enumerate(ab_items[:ab_limit]):
                itx, iat = _t(ctx, f"{slug}:about:item:{i}", item, loc_ab[i] if i < len(loc_ab) else "")
                ab_cards.append(f'          <article class="spec-card" data-reveal><h3>0{i+1} / {"О ПРОЕКТЕ" if lang == "ru" else "HIGHLIGHT"}</h3><p{iat}>{itx}</p></article>')
            ab_count = len(ab_cards) + len(geo_list)
            htx, hat = h2_for("about", "О проекте и ключевые показатели" if lang == "ru" else "About & Verified Specifications")
            sections_html.append(
                f"""    <section class="section-block" id="about">
      <div class="container">
        <h2{hat}>{htx}</h2>
        <p class="lead-copy"{abat}>{abtx}</p>
        <div class="canon-grid" data-count="{ab_count}">
{chr(10).join(ab_cards)}
{geo_cards}
        </div>
      </div>
    </section>"""
            )
        elif brick == "stats":
            st_default = [f"{s.get('value')} — {s.get('label')}" for s in (company_cfg.get("stats") or []) if isinstance(s, dict) and s.get("value")] or c_fallbacks
            st_items = _split_user_items(bp_map.get("stats", ""), st_default, min_items=3)
            loc_st = _loc_items(loc, "stats")
            sv = _variant(pm, d, "stats", page_idx)
            s_cls = " stat-band" if sv in ("band", "kpi_band", "ledger_strip") else ""
            st_cards = []
            for idx, item in enumerate(st_items[:4]):
                value, label = _split_pair(item, "Показатель" if lang == "ru" else "Metric")
                loc_item = loc_st[idx] if idx < len(loc_st) else ""
                _, loc_label = _split_pair(loc_item, "") if loc_item else ("", "")
                ltx, lat = _t(ctx, f"{slug}:stats:label:{idx}", label, loc_label)
                st_cards.append(f'          <article class="stat-card" data-reveal><p class="stat-value">{html.escape(value)}</p><p class="eyebrow"{lat}>{ltx}</p></article>')
            htx, hat = h2_for("stats", "Цифры и подтверждённые результаты" if lang == "ru" else "Metrics & Verified Outcomes")
            sections_html.append(
                f"""    <section class="section-block{s_cls}" id="stats">
      <div class="container">
        <h2{hat}>{htx}</h2>
        <div class="canon-grid" data-count="{len(st_cards)}">
{chr(10).join(st_cards)}
        </div>
      </div>
    </section>"""
            )
        elif brick == "process":
            pr_default = [f"{p.get('step')} — {p.get('detail')}" for p in (company_cfg.get("process") or []) if isinstance(p, dict) and p.get("step")] or ["01 — Бриф и аудит" if lang == "ru" else "01 — Brief & audit", "02 — Концепция и смета" if lang == "ru" else "02 — Concept & estimate", "03 — Производство" if lang == "ru" else "03 — Production", "04 — Запуск и поддержка" if lang == "ru" else "04 — Launch & support"]
            pr_items = _split_user_items(bp_map.get("process", ""), pr_default, min_items=4)
            loc_pr = _loc_items(loc, "process")
            pv = _variant(pm, d, "process", page_idx)
            htx, hat = h2_for("process", "Как мы работаем" if lang == "ru" else "How We Work")
            if pv in ("timeline", "vertical_timeline"):
                lis = []
                for idx, item in enumerate(pr_items[:5]):
                    step_name, step_desc = _split_pair(item, item)
                    loc_item = loc_pr[idx] if idx < len(loc_pr) else ""
                    loc_n, loc_d = _split_pair(loc_item, "") if loc_item else ("", "")
                    ntx, nat = _t(ctx, f"{slug}:process:name:{idx}", step_name, loc_n)
                    dtx, dat = _t(ctx, f"{slug}:process:desc:{idx}", step_desc, loc_d)
                    lis.append(f'          <li data-reveal><p class="step-index">{idx + 1:02d}</p><h3{nat}>{ntx}</h3><p{dat}>{dtx}</p></li>')
                body = f'        <ol class="timeline">\n{chr(10).join(lis)}\n        </ol>'
            else:
                cards = []
                for idx, item in enumerate(pr_items[:5]):
                    step_name, step_desc = _split_pair(item, item)
                    loc_item = loc_pr[idx] if idx < len(loc_pr) else ""
                    loc_n, loc_d = _split_pair(loc_item, "") if loc_item else ("", "")
                    ntx, nat = _t(ctx, f"{slug}:process:name:{idx}", step_name, loc_n)
                    dtx, dat = _t(ctx, f"{slug}:process:desc:{idx}", step_desc, loc_d)
                    cards.append(f'          <article class="process-step" data-reveal><p class="step-index">{idx + 1:02d}</p><h3{nat}>{ntx}</h3><p{dat}>{dtx}</p></article>')
                body = f'        <div class="canon-grid" data-count="{len(cards)}">\n{chr(10).join(cards)}\n        </div>'
            sections_html.append(
                f"""    <section class="section-block" id="process">
      <div class="container">
        <h2{hat}>{htx}</h2>
{body}
      </div>
    </section>"""
            )
        elif brick == "team":
            tm_default = [f"{m.get('name')} — {m.get('role')}" for m in (company_cfg.get("team") or []) if isinstance(m, dict) and m.get("name")] or c_fallbacks
            tm_items = _split_user_items(bp_map.get("team", ""), tm_default, min_items=3)
            loc_tm = _loc_items(loc, "team")
            tv = "portraits" if team_images else _variant(pm, d, "team", page_idx)
            tm_cards = []
            for idx, item in enumerate(tm_items[:4]):
                person, role = _split_pair(item, "Эксперт" if lang == "ru" else "Expert")
                loc_item = loc_tm[idx] if idx < len(loc_tm) else ""
                loc_p, loc_r = _split_pair(loc_item, "") if loc_item else ("", "")
                ptx, pat = _t(ctx, f"{slug}:team:name:{idx}", person, loc_p)
                rtx, rat = _t(ctx, f"{slug}:team:role:{idx}", role, loc_r)
                if tv == "portraits" and team_images and idx < len(team_images):
                    t_rel = team_images[idx]
                    tw, th = (image_dims or {}).get(t_rel, (576, 768))
                    visual = f'<img class="team-photo" src="{html.escape(t_rel, quote=True)}?v={asset_rev}" width="{tw}" height="{th}" alt="" loading="lazy">'
                else:
                    initials = "".join(w[0] for w in re.findall(r"[A-Za-zА-Яа-яЁё]+", person)[:2]).upper() or "SL"
                    visual = f'<span class="team-avatar" aria-hidden="true">{html.escape(initials)}</span>'
                tm_cards.append(f'          <article class="team-card" data-reveal>{visual}<h3{pat}>{ptx}</h3><p class="eyebrow"{rat}>{rtx}</p></article>')
            htx, hat = h2_for("team", "Команда и эксперты" if lang == "ru" else "Team & Principal Experts")
            sections_html.append(
                f"""    <section class="section-block" id="team">
      <div class="container">
        <h2{hat}>{htx}</h2>
        <div class="canon-grid" data-count="{len(tm_cards)}">
{chr(10).join(tm_cards)}
        </div>
      </div>
    </section>"""
            )
        elif brick == "blog":
            bl_items = _split_user_items(bp_map.get("blog", ""), c_fallbacks, min_items=3)
            loc_bl = _loc_items(loc, "blog")
            bl_cards = []
            for idx, item in enumerate(bl_items[:4]):
                title, summary = _split_pair(item, item)
                loc_item = loc_bl[idx] if idx < len(loc_bl) else ""
                loc_t, loc_s = _split_pair(loc_item, "") if loc_item else ("", "")
                ttx, tat = _t(ctx, f"{slug}:blog:title:{idx}", title, loc_t)
                stx, sat = _t(ctx, f"{slug}:blog:sum:{idx}", summary, loc_s)
                bl_cards.append(f'          <article class="blog-card" data-reveal><p class="blog-meta">{"МАТЕРИАЛ" if lang == "ru" else "INSIGHT"}</p><h3{tat}>{ttx}</h3><p{sat}>{stx}</p></article>')
            htx, hat = h2_for("blog", "Статьи и экспертные материалы" if lang == "ru" else "Insights & Editorial Articles")
            sections_html.append(
                f"""    <section class="section-block" id="blog">
      <div class="container">
        <h2{hat}>{htx}</h2>
        <div class="canon-grid" data-count="{len(bl_cards)}">
{chr(10).join(bl_cards)}
        </div>
      </div>
    </section>"""
            )
        elif brick == "legal":
            legal_items = _split_user_items(bp_map.get("legal", ""), ["Политика конфиденциальности: мы собираем только данные, необходимые для обработки заявки." if lang == "ru" else "Privacy policy: we collect only the data required to process your request.", "Условия использования: материалы сайта защищены авторским правом." if lang == "ru" else "Terms of use: all site materials are protected by copyright.", "Реквизиты компании доступны по запросу." if lang == "ru" else "Company details are available on request."], min_items=3)
            loc_lg = _loc_items(loc, "legal")
            legal_paras = []
            for idx, p in enumerate(legal_items[:6]):
                ptx, pat = _t(ctx, f"{slug}:legal:p:{idx}", p, loc_lg[idx] if idx < len(loc_lg) else "")
                legal_paras.append(f'        <p{pat}>{ptx}</p>')
            htx, hat = h2_for("legal", "Правовая информация" if lang == "ru" else "Legal Information")
            sections_html.append(
                f"""    <section class="section-block" id="legal">
      <div class="container legal-copy">
        <h2{hat}>{htx}</h2>
{chr(10).join(legal_paras)}
      </div>
    </section>"""
            )
        elif brick == "gallery":
            gal_items = _split_user_items(bp_map.get("gallery", ""), [lead_copy, c_fallbacks[0]], min_items=2)
            loc_gal = _loc_items(loc, "gallery")
            gv = _variant(pm, d, "gallery", page_idx)
            g_cls = {"mosaic": " gal-mosaic", "bento_mosaic": " gal-mosaic", "filmstrip": " gal-filmstrip", "horizontal_filmstrip": " gal-filmstrip"}.get(gv, "")
            gal_imgs = [str(x) for x in (gallery_images or [])]
            if gal_imgs:
                gal_cards = []
                for g_idx, g_rel in enumerate(gal_imgs[:4]):
                    cap = gal_items[g_idx] if g_idx < len(gal_items) else project_name
                    if len(cap) > 140:
                        cap = cap[:140].rsplit(" ", 1)[0].rstrip(" ,;:—-") + "…"
                    ctx_, cat_ = _t(ctx, f"{slug}:gallery:cap:{g_idx}", cap, loc_gal[g_idx] if g_idx < len(loc_gal) else "")
                    gw, gh = (image_dims or {}).get(g_rel, (1024, 576))
                    gal_cards.append(
                        f"""          <figure class="gallery-card" data-reveal>
            <img src="{html.escape(g_rel, quote=True)}?v={asset_rev}" width="{gw}" height="{gh}" alt="{ctx_}"{cat_.replace('data-i18n=', 'data-i18n-alt=')} loading="lazy">
            <figcaption{cat_}>{ctx_}</figcaption>
          </figure>"""
                    )
                gal_grid = "\n".join(gal_cards)
            else:
                c0tx, c0at = _t(ctx, f"{slug}:gallery:cap:0", gal_items[0], loc_gal[0] if loc_gal else "")
                c1tx, c1at = _t(ctx, f"{slug}:gallery:cap:1", gal_items[1] if len(gal_items) > 1 else project_name, loc_gal[1] if len(loc_gal) > 1 else "")
                gal_grid = f"""          <figure class="gallery-card" data-reveal>
            <img src="{html.escape(hero_rel, quote=True)}?v={asset_rev}" width="{route_dims[0]}" height="{route_dims[1]}" alt="{c0tx}"{c0at.replace('data-i18n=', 'data-i18n-alt=')} loading="lazy">
            <figcaption{c0at}>{c0tx}</figcaption>
          </figure>
          <figure class="gallery-card" data-reveal>
            <img src="{html.escape(logo_relpath, quote=True)}?v={asset_rev}" width="512" height="512" alt="{html.escape(project_name)} brand mark" loading="lazy">
            <figcaption{c1at}>{c1tx}</figcaption>
          </figure>"""
            htx, hat = h2_for("gallery", "Визуальная галерея и проекты" if lang == "ru" else "Visual Portfolio & Showcase")
            gal_controls = (
                f'        <div class="carousel-controls">'
                f'<button class="btn btn-secondary carousel-btn" type="button" data-dir="-1" aria-label="{html.escape(ui["prev"], quote=True)}">←</button>'
                f'<button class="btn btn-secondary carousel-btn" type="button" data-dir="1" aria-label="{html.escape(ui["next"], quote=True)}">→</button>'
                f'</div>\n'
                if g_cls == " gal-filmstrip"
                else ""
            )
            gal_region_attr = f' tabindex="0" role="region" aria-label="{html.escape(ui["gallery_region"], quote=True)}"' if g_cls == " gal-filmstrip" else ""
            sections_html.append(
                f"""    <section class="section-block{g_cls}" id="gallery">
      <div class="container">
        <h2{hat}>{htx}</h2>
{gal_controls}        <div class="canon-grid" data-count="{len(gal_cards) if gal_imgs else 2}"{gal_region_attr}>
{gal_grid}
        </div>
      </div>
    </section>"""
            )
        elif brick == "pricing":
            p_default = [
                f"{pr.get('name')} — {pr.get('scope') or ''} — {pr.get('price') or ''}".strip(" —")
                for pr in (company_cfg.get("products") or [])
                if isinstance(pr, dict) and pr.get("name")
            ] or c_fallbacks
            p_items = _split_user_items(bp_map.get("pricing", ""), p_default, min_items=3)
            loc_p = _loc_items(loc, "pricing")
            pv = _variant(pm, d, "pricing", page_idx)
            htx, hat = h2_for("pricing", "Тарифы и форматы работы" if lang == "ru" else "Pricing & Engagement Tiers")
            parsed = []
            for idx, item in enumerate(p_items[:4]):
                t_name, t_desc = _split_pair(item, item)
                if t_name == item and not t_desc:
                    t_name = f"Tier {idx + 1}"
                loc_item = loc_p[idx] if idx < len(loc_p) else ""
                ln, ls = _split_pair(loc_item, "") if loc_item else ("", "")
                parsed.append((t_name, t_desc, ln, ls))
            _price_curr_re = re.compile(
                r"(?:(?:\$|€|£)\s*\d[\d\s.,]*(?:\s*/\s*[A-Za-zА-Яа-яЁё.]+)?|\d[\d\s.,]*\s*(?:₽|руб\.?|р\.|USD|EUR|GBP|₸|USDT)(?:\s*/\s*[A-Za-zА-Яа-яЁё.]+)?)"
            )
            if pv in ("table", "spec_comparison_table"):
                head = "".join(f'<th scope="col"{_t(ctx, f"{slug}:pricing:name:{i}", n, ln)[1]}>{_t(ctx, f"{slug}:pricing:name:{i}", n, ln)[0]}</th>' for i, (n, _, ln, _) in enumerate(parsed))
                scope = "".join(f'<td{_t(ctx, f"{slug}:pricing:scope:{i}", s, ls)[1]}>{_t(ctx, f"{slug}:pricing:scope:{i}", s, ls)[0]}</td>' for i, (_, s, _, ls) in enumerate(parsed))
                prices = []
                for i, (_, s, _, ls) in enumerate(parsed):
                    m_cur = _price_curr_re.search(s) or re.search(r"\d[\d\s.,]*", s)
                    price = m_cur.group(0).strip() if m_cur else "—"
                    ml_cur = _price_curr_re.search(ls) or re.search(r"\d[\d\s.,]*", ls) if ls else None
                    loc_price = ml_cur.group(0).strip() if ml_cur else ""
                    ptx, pat = _t(ctx, f"{slug}:pricing:price:{i}", price, loc_price)
                    prices.append(f"<td{pat}>{ptx}</td>")
                sel = "".join(f'<td><a class="btn btn-secondary" href="#contact">{html.escape(ui["select"])}</a></td>' for _ in parsed)
                body = f"""        <div class="price-table-wrap" tabindex="0" role="region" aria-label="{html.escape(ui["pricing_region"], quote=True)}" data-reveal>
          <table class="price-table">
            <thead><tr><th scope="col">{"Параметр" if lang == "ru" else "Tier"}</th>{head}</tr></thead>
            <tbody>
              <tr><th scope="row">{"Состав" if lang == "ru" else "Scope"}</th>{scope}</tr>
              <tr><th scope="row">{"Стоимость" if lang == "ru" else "Price"}</th>{''.join(prices)}</tr>
              <tr><td></td>{sel}</tr>
            </tbody>
          </table>
        </div>"""
            else:
                cards = []
                for idx, (t_name, t_desc, ln, ls) in enumerate(parsed):
                    ntx, nat = _t(ctx, f"{slug}:pricing:name:{idx}", t_name, ln)
                    dtx, dat = _t(ctx, f"{slug}:pricing:scope:{idx}", t_desc, ls)
                    cards.append(
                        f"""          <article class="price-card" data-reveal>
            <div>
              <p class="eyebrow">0{idx + 1} / {"ТАРИФ" if lang == "ru" else "PACKAGE"}</p>
              <h3{nat}>{ntx}</h3>
              <p{dat}>{dtx}</p>
            </div>
            <a class="btn btn-secondary" href="#contact">{html.escape(ui["select"])}</a>
          </article>"""
                    )
                body = f'        <div class="canon-grid" data-count="{len(cards)}">\n{chr(10).join(cards)}\n        </div>'
            sections_html.append(
                f"""    <section class="section-block" id="pricing">
      <div class="container">
        <h2{hat}>{htx}</h2>
{body}
      </div>
    </section>"""
            )
        elif brick == "testimonials":
            t_items = _split_user_items(bp_map.get("testimonials", ""), c_fallbacks, min_items=3)
            loc_t = _loc_items(loc, "testimonials")
            tv = _variant(pm, d, "testimonials", page_idx)
            t_cls = " review-quotes" if tv in ("quotes", "editorial_pullquotes") else ""
            t_cards = []
            for i, item in enumerate(t_items[:4]):
                itx, iat = _t(ctx, f"{slug}:testimonials:item:{i}", item, loc_t[i] if i < len(loc_t) else "")
                t_cards.append(f'          <article class="review-card" data-reveal><p{iat}>“{itx}”</p><p class="eyebrow">{"Кейс #" if lang == "ru" else "Case Study #"}{i+1} · {html.escape(project_name)}</p></article>')
            htx, hat = h2_for("testimonials", "Отзывы и реализованные кейсы" if lang == "ru" else "Client Outcomes & Case Studies")
            sections_html.append(
                f"""    <section class="section-block{t_cls}" id="testimonials">
      <div class="container">
        <h2{hat}>{htx}</h2>
        <div class="canon-grid" data-count="{len(t_cards)}">
{chr(10).join(t_cards)}
        </div>
      </div>
    </section>"""
            )
        elif brick == "faq":
            faq_cards = []
            for i, f in enumerate(active_faqs):
                lf = loc_faqs[i] if i < len(loc_faqs) and isinstance(loc_faqs[i], dict) else {}
                qtx, qat = _t(ctx, f"{slug}:faq:q:{i}", f["q"], str(lf.get("q") or ""))
                atx, aat = _t(ctx, f"{slug}:faq:a:{i}", f["a"], str(lf.get("a") or ""))
                faq_cards.append(f'        <article class="faq-item" data-reveal><h3{qat}>{qtx}</h3><p{aat}>{atx}</p></article>')
            htx, hat = h2_for("faq", "Частые вопросы (FAQ)" if lang == "ru" else "Frequently Asked Questions")
            sections_html.append(
                f"""    <section class="section-block" id="faq">
      <div class="container">
        <h2{hat}>{htx}</h2>
{chr(10).join(faq_cards)}
      </div>
    </section>"""
            )
        elif brick == "cta":
            cta_text = str(bp_map.get("cta") or ("Обсудим ваш проект? Оставьте заявку — вернёмся с планом и сметой." if lang == "ru" else "Let's discuss your project — leave a request and receive a tailored plan."))
            contact_route = next((r for r in all_routes if r.get("slug") == "contact"), None)
            cta_href = contact_route["filename"] if contact_route else "#contact"
            ctx_, cat_ = _t(ctx, f"{slug}:cta:text", cta_text, _loc_get(loc, "copy", "cta"))
            btx, bat = _t(ctx, f"{slug}:cta:btn", "Оставить заявку" if lang == "ru" else "Start a Project", _loc_get(loc, "hero", "cta_label"))
            sections_html.append(
                f"""    <section class="section-block" id="cta">
      <div class="container">
        <div class="cta-banner" data-reveal>
          <h2{cat_}>{ctx_}</h2>
          <a class="btn" href="{html.escape(cta_href, quote=True)}"{bat}>{btx}</a>
        </div>
      </div>
    </section>"""
            )
        elif brick in ("contact", "contact-form"):
            contact_desc = str(bp_map.get("contact") or ("Оставьте контакты — мы свяжемся и подготовим предложение." if lang == "ru" else "Leave your details to receive a tailored project proposal."))
            dtx, dat = _t(ctx, f"{slug}:contact:lead", contact_desc, _loc_get(loc, "copy", "contact"))
            contact_bits = []
            if c_phone:
                contact_bits.append(f'<p><a href="tel:{html.escape(c_phone, quote=True)}">{html.escape(c_phone)}</a></p>')
            if c_email:
                contact_bits.append(f'<p><a href="mailto:{html.escape(c_email, quote=True)}">{html.escape(c_email)}</a></p>')
            if c_address:
                contact_bits.append(f'<address>{html.escape(c_address)}</address>')
            if c_hours:
                contact_bits.append(f'<p class="eyebrow">{html.escape(c_hours)}</p>')
            contact_details = "\n".join(contact_bits)
            htx, hat = h2_for("contact", "Связаться и обсудить задачу" if lang == "ru" else "Start a Conversation")
            fnx, fnat = _t(ctx, "chrome:form:name", ui["form_name"], ui_alt["form_name"])
            fex, feat = _t(ctx, "chrome:form:email", ui["form_email"], ui_alt["form_email"])
            fmx, fmat = _t(ctx, "chrome:form:msg", ui["form_msg"], ui_alt["form_msg"])
            fsx, fsat = _t(ctx, "chrome:form:send", ui["form_send"], ui_alt["form_send"])
            sections_html.append(
                f"""    <section class="section-block" id="contact">
      <div class="container contact-layout">
        <div data-reveal>
          <h2{hat}>{htx}</h2>
          <p class="lead-copy"{dat}>{dtx}</p>
          <form class="intake-form" action="#contact" method="get">
            <div>
              <label for="lead-name"{fnat}>{fnx}</label>
              <input id="lead-name" name="name" type="text" autocomplete="name" required>
            </div>
            <div>
              <label for="lead-email"{feat}>{fex}</label>
              <input id="lead-email" name="email" type="email" autocomplete="email" required>
            </div>
            <div>
              <label for="lead-msg"{fmat}>{fmx}</label>
              <textarea id="lead-msg" name="message" rows="3"></textarea>
            </div>
            <label class="hp-trap" for="hp-company" aria-hidden="true">Company</label>
            <input class="hp-trap" id="hp-company" name="company_hp" type="text" tabindex="-1" autocomplete="off" aria-hidden="true">
            <button class="btn" type="submit"{fsat}>{fsx}</button>
            <p class="form-status" role="status" aria-live="polite"></p>
          </form>
        </div>
        <aside class="contact-details" data-reveal>
          <h3>{html.escape(ui["footer_contacts"])}</h3>
          {contact_details}
        </aside>
      </div>
    </section>"""
            )

    if not sections_html:
        htx, hat = _t(ctx, f"{slug}:hero:h1", h1_text, _loc_get(loc, "hero", "headline"))
        ltx, lat = _t(ctx, f"{slug}:hero:lead", lead_copy, _loc_get(loc, "hero", "subhead"))
        sections_html.append(
            f"""    <section class="hero-shell" id="hero">
      <div class="container canon-grid">
        <div class="hero-lead"><h1{hat}>{htx}</h1><p class="lead-copy"{lat}>{ltx}</p></div>
      </div>
    </section>"""
        )

    footer_tag = str(chrome_cfg.get("footer_text") or "").strip() or str(bp_map.get("footer") or f"{project_name} · SmartLLM Studio v{__version__}")
    ftx, fat = _t(ctx, "chrome:footer:tag", footer_tag, _loc_get(loc_chrome, "footer_text"))
    fnhx, fnhat = _t(ctx, "chrome:footer:nav_h", ui["footer_nav"], ui_alt["footer_nav"])
    fchx, fchat = _t(ctx, "chrome:footer:contacts_h", ui["footer_contacts"], ui_alt["footer_contacts"])
    frx, frat = _t(ctx, "chrome:footer:rights", ui["rights"], ui_alt["rights"])
    flx, flat = _t(ctx, "chrome:footer:legal", ui["legal_link"], ui_alt["legal_link"])
    legal_route = next((r for r in all_routes if r.get("slug") == "legal"), None)
    legal_href = legal_route["filename"] if legal_route else "index.html#legal"
    footer_nav_items = "\n".join(
        f'            <li><a href="{r["filename"]}"{_t(ctx, f"chrome:nav:{r["slug"]}", str(nav_labels.get(r["slug"]) or r["title"]), str(loc_nav.get(r["slug"]) or ""))[1]}>{_t(ctx, f"chrome:nav:{r["slug"]}", str(nav_labels.get(r["slug"]) or r["title"]), str(loc_nav.get(r["slug"]) or ""))[0]}</a></li>'
        for r in all_routes
    )
    footer_contacts = []
    if c_phone:
        footer_contacts.append(f'<p><a href="tel:{html.escape(c_phone, quote=True)}">{html.escape(c_phone)}</a></p>')
    if c_email:
        footer_contacts.append(f'<p><a href="mailto:{html.escape(c_email, quote=True)}">{html.escape(c_email)}</a></p>')
    if c_address:
        footer_contacts.append(f"<address>{html.escape(c_address)}</address>")
    if c_hours:
        footer_contacts.append(f"<p>{html.escape(c_hours)}</p>")
    crumb_html = ""
    if slug != "index":
        chx, chat = _t(ctx, "chrome:crumb:home", ui["crumb_home"], ui_alt["crumb_home"])
        crx, crat = _t(ctx, f"chrome:crumb:{slug}", route["title"], str(loc_nav.get(slug) or ""))
        crumb_html = f'    <nav class="crumbs container" aria-label="Breadcrumb"><ol><li><a href="index.html"{chat}>{chx}</a></li><li aria-current="page"{crat}>{crx}</li></ol></nav>\n'
    progress_html = '<div class="scroll-progress" aria-hidden="true"></div>' if str((d.get("motion") or {}).get("scroll") or "") == "progress" else ""
    body_sections = "\n".join(sections_html)
    ttx, tat = _t(ctx, f"{slug}:meta:title", page_title, loc_title)
    mdx, mdat = _t(ctx, f"{slug}:meta:desc", meta_desc, loc_desc)
    skipx, skipat = _t(ctx, "chrome:skip", ui["skip"], ui_alt["skip"])

    return f"""<!DOCTYPE html>
<html lang="{lang}" data-theme="{polarity}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{csp_meta}">
  <title{tat}>{ttx}</title>
  <meta name="description" content="{mdx}"{mdat.replace('data-i18n=', 'data-i18n-content=')}>
  <link rel="canonical" href="{html.escape(page_url, quote=True)}">
  <link rel="icon" href="{html.escape(favicon_relpath, quote=True)}">
{hreflang_block}  <meta property="og:type" content="website">
  <meta property="og:title" content="{html.escape(page_title, quote=True)}">
  <meta property="og:description" content="{html.escape(meta_desc, quote=True)}">
  <meta property="og:url" content="{html.escape(page_url, quote=True)}">
  <meta property="og:image" content="{html.escape(base_url + '/' + hero_rel, quote=True)}">
  <meta property="og:image:width" content="{route_dims[0]}">
  <meta property="og:image:height" content="{route_dims[1]}">
  <meta property="og:image:alt" content="{html.escape(hero_alt_meta, quote=True)}">
  <meta property="og:locale" content="{"ru_RU" if lang == "ru" else "en_US"}">
  <meta name="twitter:card" content="summary_large_image">
  <script type="application/ld+json">{safe_json_ld}</script>
  <style>{css_text}</style>
</head>
<body>
  {progress_html}
  <a class="skip-link" href="#main-content"{skipat}>{skipx}</a>
  <header class="site-header">
    <div class="container header-inner">
      <a class="brand-link" href="index.html">
        <img src="{html.escape(logo_relpath, quote=True)}?v={asset_rev}" width="36" height="36" alt="{html.escape(project_name)} logo">
        <span>{html.escape(project_name)}</span>
      </a>
      <button class="btn btn-secondary nav-toggle" id="mobile-nav-toggle" type="button" aria-expanded="false" aria-controls="primary-nav-list">{html.escape(ui["menu"])}</button>
      <nav aria-label="Primary">
        <ul class="nav-list" id="primary-nav-list" data-open="false">
{nav_links}
        </ul>
      </nav>
      {lang_switch}
    </div>
  </header>
  <main id="main-content">
{crumb_html}{marquee_html}{body_sections}
  </main>
  <footer class="site-footer">
    <div class="container footer-grid">
      <div class="footer-brand">
        <a class="brand-link" href="index.html"><img src="{html.escape(logo_relpath, quote=True)}?v={asset_rev}" width="36" height="36" alt=""><span>{html.escape(project_name)}</span></a>
        <p{fat}>{ftx}</p>
      </div>
      <nav aria-label="Footer">
        <p class="footer-h"{fnhat}>{fnhx}</p>
        <ul class="footer-nav">
{footer_nav_items}
        </ul>
      </nav>
      <div class="footer-contacts">
        <p class="footer-h"{fchat}>{fchx}</p>
        {chr(10).join(footer_contacts) or f"<p>{html.escape(footer_tag)}</p>"}
      </div>
    </div>
    <div class="container footer-bottom">
      <p>© {datetime_year()} {html.escape(project_name)}. <span{frat}>{frx}</span></p>
      <a href="{html.escape(legal_href, quote=True)}"{flat}>{flx}</a>
    </div>
  </footer>
  <script>{js_text}</script>
</body>
</html>
"""


def datetime_year() -> int:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).year


def _write_seo_and_security_files(
    project_dir: Path,
    project_name: str,
    brief: str,
    card: dict[str, Any],
    routes: list[dict[str, Any]],
    base_url: str,
    csp_header: str,
    style_hash: str,
    script_hash: str,
    copy_pairs: list[dict[str, Any]],
    ai_crawlers: dict[str, bool],
    llms_txt_enabled: bool,
    zimage_dir: dict[str, Any],
    company: dict[str, Any] | None = None,
    page_seo: dict[str, dict[str, str]] | None = None,
    visuals: dict[str, Any] | None = None,
    hero_variant: str = "",
) -> None:
    headers_txt = (
        f"# Cloudflare Pages strict edge security headers generated by SmartLLM Studio v{__version__}\n"
        f"/*\n"
        f"  Content-Security-Policy: {csp_header}\n"
        f"  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload\n"
        f"  X-Content-Type-Options: nosniff\n"
        f"  X-Frame-Options: DENY\n"
        f"  Referrer-Policy: strict-origin-when-cross-origin\n"
        f"  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()\n"
        f"  Cross-Origin-Opener-Policy: same-origin\n"
        f"  Cross-Origin-Embedder-Policy: credentialless\n"
        f"  Cross-Origin-Resource-Policy: same-origin\n"
    )
    (project_dir / "_headers").write_text(headers_txt, encoding="utf-8")

    lead_copy = str((company or {}).get("positioning") or "").strip() or (copy_pairs[0]["canon_after"] if copy_pairs else brief)
    page_seo = page_seo or {}
    routes_md = "\n".join(
        f"- [{r['title']}]({base_url}{r['path']}): {str((page_seo.get(r['slug']) or {}).get('description') or '').strip() or ('Verified route `' + r['filename'] + '`')}"
        for r in routes
    )
    company = company or {}
    company_lines = []
    for key, label in (("phone", "Phone"), ("email", "Email"), ("address", "Address"), ("hours", "Hours")):
        val = str(company.get(key) or "").strip()
        if val:
            company_lines.append(f"- {label}: {val}")
    cities = [str(x).strip() for x in (company.get("cities") or []) if str(x).strip()]
    if cities:
        company_lines.append(f"- Locations: {', '.join(cities)}")
    company_md = ("\n## Contacts & Locations\n" + "\n".join(company_lines) + "\n") if company_lines else ""
    catalog = [pr for pr in (company.get("products") or []) if isinstance(pr, dict) and str(pr.get("name") or "").strip()]
    if catalog:
        company_md += "\n## Products & Prices (single source of truth)\n" + "\n".join(f"- {pr.get('name')}: {pr.get('scope') or ''} — {pr.get('price') or ''}" for pr in catalog[:6]) + "\n"
    hist = company.get("history") or {}
    if hist:
        company_md += f"\n## Brand History\n- Founded: {hist.get('founded') or ''}\n" + "\n".join(f"- {m}" for m in (hist.get("milestones") or [])[:4]) + "\n"
    if llms_txt_enabled:
        llms_txt = f"# {project_name}\n> {lead_copy}\n\n## Pages & Specifications\n{routes_md}\n{company_md}\n## Security & Design Canon\n- Canon: `{card['id']}` ({card['name']})\n- CSP SHA-256: `{style_hash}`, `{script_hash}`\n"
        (project_dir / "llms.txt").write_text(llms_txt, encoding="utf-8")

    bot_blocks = [f"User-agent: {bot}\n{'Allow' if allowed else 'Disallow'}: /\n" for bot, allowed in ai_crawlers.items()]
    robots_txt = "\n".join(bot_blocks) + f"\nUser-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n"
    (project_dir / "robots.txt").write_text(robots_txt, encoding="utf-8")

    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = "\n".join(f"  <url><loc>{html.escape(base_url + r['path'])}</loc><lastmod>{today_iso}</lastmod></url>" for r in routes)
    sitemap_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}\n</urlset>\n'
    (project_dir / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")

    imagery = card.get("imagery", {})
    style_chip = str(zimage_dir.get("style_chip") or "Architectural Orthographic")
    mood = str(zimage_dir.get("mood") or "Studio Daylight")
    aspect_ratio = str(zimage_dir.get("aspect_ratio") or imagery.get("aspect_ratio", "16:9"))
    visuals = visuals or {}
    if visuals.get("hero"):
        prompt_body = str(visuals["hero"])
        if visuals.get("style_suffix"):
            prompt_body = f"{prompt_body} {visuals['style_suffix']}".strip()
    else:
        prompt_body = str(imagery.get("prompt_tmpl", "Architectural studio photograph, subject: {subject}")).replace("{subject}", brief[:140])
        prompt_body = f"{prompt_body}, style: {style_chip}, mood: {mood}, high micro-contrast, museum-grade lighting."
    dossier = load_canon_dossier(card.get("id", ""))
    default_hero_var = hero_variant or str(((dossier.get("variants") or {}).get("hero") or ["split"])[0])
    hw, hh = resolve_slot_dimensions("hero", aspect_ratio, default_hero_var)
    gw, gh = resolve_slot_dimensions("gallery", aspect_ratio)
    hero_ar = "16:9" if default_hero_var in ("centered", "overlay", "editorial_poster", "command_stage", "fullbleed_scrim") else aspect_ratio
    gal_ar = aspect_ratio if aspect_ratio in ("1:1", "4:3", "16:9") else ("4:3" if aspect_ratio in ("4:5", "3:4") else "16:9")
    prompt_list = [
        {"id": "hero_primary", "slot": "hero_primary", "canon_id": card["id"], "aspect_ratio": hero_ar, "width": hw, "height": hh, "steps": 8, "cfg_scale": 1.0, "seed": 42, "prompt": prompt_body, "output_relpath": "assets/hero_primary.png"}
    ]
    if visuals.get("logo"):
        prompt_list.append({"id": "brand_logo", "slot": "brand_logo", "canon_id": card["id"], "aspect_ratio": "1:1", "width": 512, "height": 512, "steps": 8, "cfg_scale": 1.0, "seed": 101, "prompt": str(visuals["logo"]), "output_relpath": "assets/brand-logo.png"})
    for g_idx, g_prompt in enumerate(visuals.get("gallery") or []):
        prompt_list.append({"id": f"gallery_{g_idx + 1}", "slot": f"gallery_{g_idx + 1}", "canon_id": card["id"], "aspect_ratio": gal_ar, "width": gw, "height": gh, "steps": 8, "cfg_scale": 1.0, "seed": 43 + g_idx, "prompt": f"{g_prompt} {visuals.get('style_suffix') or ''}".strip(), "output_relpath": f"assets/gallery_{g_idx + 1}.png"})
    zimage_doc = {"canon_id": card["id"], "prompts": prompt_list}
    (project_dir / "zimage_prompts.json").write_text(json.dumps(zimage_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_stack_scaffold_files(project_dir: Path, stack: str, motion: str, project_name: str) -> list[str]:
    files: list[str] = ["app.ts"]
    (project_dir / "app.ts").write_text(
        f'// Strict TypeScript 6.0 entry for {project_name} ({stack} + {motion})\n'
        'const btn: HTMLElement | null = document.getElementById("node-calc-btn");\n'
        'if (btn !== null) { btn.setAttribute("data-hydrated", "true"); }\n',
        encoding="utf-8",
    )
    if stack == "astro":
        (project_dir / "astro.config.mjs").write_text(
            'import { defineConfig } from "astro/config";\nexport default defineConfig({ output: "static", build: { inlineStylesheets: "always" } });\n',
            encoding="utf-8",
        )
        files.append("astro.config.mjs")
    return files