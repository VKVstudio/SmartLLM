#!/usr/bin/env python3
"""Deterministic builder for 28 RAG-only SmartLLM v2 Style Canon Cards."""

import json
import math
import os
import re

HARVEST_DIR = "/mnt/rescue/projects/SmartLLM/data/harvest"
CARDS_DIR = os.path.join(HARVEST_DIR, "canon_cards")
CURATED_DATE = "2026-11-15"

OKLCH_RE = re.compile(r"^oklch\(([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\)$")


def oklch_to_srgb(L: float, C: float, H_deg: float) -> tuple[float, float, float]:
    """Convert OKLCH (L in 0..1, C, H in degrees) to linear sRGB (0..1)."""
    if L > 1.0:
        L = L / 100.0
    h_rad = math.radians(H_deg)
    a = C * math.cos(h_rad)
    b = C * math.sin(h_rad)

    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    l3 = l_ * l_ * l_
    m3 = m_ * m_ * m_
    s3 = s_ * s_ * s_

    r_lin = +4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3
    g_lin = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3
    b_lin = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3

    return (
        max(0.0, min(1.0, r_lin)),
        max(0.0, min(1.0, g_lin)),
        max(0.0, min(1.0, b_lin)),
    )


def luminance(oklch_str: str) -> float:
    m = OKLCH_RE.match(oklch_str.strip())
    if not m:
        raise ValueError(f"Invalid OKLCH token: {oklch_str}")
    r_l, g_l, b_l = oklch_to_srgb(float(m.group(1)), float(m.group(2)), float(m.group(3)))
    return 0.2126 * r_l + 0.7152 * g_l + 0.0722 * b_l


def contrast_ratio(c1: str, c2: str) -> float:
    l1 = luminance(c1)
    l2 = luminance(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return round((hi + 0.05) / (lo + 0.05), 2)


RAW_CARDS = [
    {
        "id": "01_swiss_international_typographic",
        "name": "Swiss International Typographic Grid",
        "category": "editorial_typography",
        "languages": ["en", "ru"],
        "source": "Josef Muller-Brockmann Grid Systems canon + research/replan/design_eval_and_canons.md#1",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0, "line_height_body": 1.5, "line_height_heading": 1.08, "measure_ch": "62ch", "tabular_nums": True},
        "fonts": {"heading": "'Inter', 'Helvetica Neue', Arial, sans-serif", "body": "'Inter', 'Helvetica Neue', Arial, sans-serif", "mono": "'JetBrains Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.98 0.002 90)",
            "surface": "oklch(0.945 0.003 90)",
            "border": "oklch(0.20 0.002 90)",
            "text": "oklch(0.14 0.002 90)",
            "muted": "oklch(0.42 0.005 90)",
            "accent": "oklch(0.54 0.21 28)",
            "accent_ink": "oklch(0.99 0.002 90)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 0, "shadow": "none", "pad_clamp": "clamp(2rem, 5vw, 6rem)", "container_query_bp": "640px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 140, "reduced_motion_policy": "Instant opacity state swap; disable all transform transitions"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Architectural brutalist raw board-formed concrete pavilion, strict geometric composition, crisp morning directional shadow, Leica Summicron 35mm f/8, neutral monochrome silver gelatin tonal range, zero clutter, subject: {subject}",
            "negative_prompt": "purple neon glow, floating 3d blobs, stock office handshake, lens flare, oversaturated HDR, cartoon, watermark",
            "aspect_ratio": "16:9",
            "style_tags": ["swiss-grid", "architectural-monochrome", "orthographic", "leica-35mm"],
        },
        "rules": {
            "do": [
                "Align every heading, rule, and data column to an explicit 12-column asymmetric CSS Grid with visible 1px hairlines",
                "Set body copy flush-left ragged-right within 58ch-65ch measure and enforce tabular-nums on numeric indices",
                "Use high-chroma Signal Vermilion strictly for primary focal action or active section markers",
                "Expose section numbers (01, 02, 03) in monospace above structural hairline dividers"
            ],
            "dont": [
                "Never apply drop shadows, glassmorphism blur, or rounded pill buttons",
                "Never center-align multi-line paragraphs or feature card descriptions",
                "Never introduce multi-stop decorative gradients or purple-blue SaaS glows",
                "Never stack equal-width 3-card icon rows without asymmetric lead hierarchy"
            ],
        },
        "ref_sites": ["standards.site", "swissted.com", "vitsoe.com"],
    },
    {
        "id": "02_neo_brutalism_tactile",
        "name": "Tactile Technical Neo-Brutalism",
        "category": "devtools_cli",
        "languages": ["en", "ru"],
        "source": "Gumroad / Neobrutalism UI mechanics + research/replan/design_eval_and_canons.md#2",
        "type_scale": {"ratio": 1.333, "base_rem": 1.0, "line_height_body": 1.5, "line_height_heading": 1.06, "measure_ch": "60ch", "tabular_nums": True},
        "fonts": {"heading": "'Space Grotesk', system-ui, sans-serif", "body": "'Inter', system-ui, sans-serif", "mono": "'JetBrains Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.96 0.028 95)",
            "surface": "oklch(0.995 0.004 95)",
            "border": "oklch(0.12 0.005 95)",
            "text": "oklch(0.12 0.005 95)",
            "muted": "oklch(0.38 0.015 95)",
            "accent": "oklch(0.86 0.18 118)",
            "accent_ink": "oklch(0.12 0.01 118)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 4, "shadow": "4px 4px 0px oklch(0.12 0.005 95)", "pad_clamp": "clamp(1.5rem, 4vw, 4.5rem)", "container_query_bp": "560px", "viewport_unit": "100svh"},
        "motion": {"ease": "steps(3, end)", "duration_ms": 100, "reduced_motion_policy": "Disable translate press-offset; keep crisp border-color feedback"},
        "scroll_padding_top_px": 76,
        "imagery": {
            "prompt_tmpl": "Isometric cutaway mechanical assembly diagram on warm cream drafting paper, bold 2.5pt ink outlines, flat screenprint electric lime and matte charcoal fills, technical callout ticks, clean studio lighting, subject: {subject}",
            "negative_prompt": "soft airbrush gradient, photorealistic stock portrait, blurry bokeh, dark purple cyberpunk fog, low contrast",
            "aspect_ratio": "4:3",
            "style_tags": ["risograph-ink", "isometric-blueprint", "hard-outline", "flat-spot-color"],
        },
        "rules": {
            "do": [
                "Use 2px-2.5px solid dark ink borders paired with crisp unblurred 4px 4px 0px offset shadows",
                "Translate interactive buttons by +2px/+2px while reducing offset shadow to 2px 2px 0px on active press",
                "Pair warm cream drafting-paper background with pure crisp card surfaces and dark ink text on lime accents",
                "Label controls and metrics with bordered monospace stamp tags"
            ],
            "dont": [
                "Never combine hard offset shadows with Gaussian blur shadows on the same page",
                "Never put white text on high-lightness lime or yellow accent fills",
                "Never use hairline low-contrast gray borders that vanish against cream backgrounds",
                "Never exceed two high-chroma spot colors per viewport"
            ],
        },
        "ref_sites": ["gumroad.com", "motherduck.com", "posthog.com"],
    },
    {
        "id": "03_dark_precision_saas_linear",
        "name": "Dark Precision SaaS Instrument",
        "category": "saas_product",
        "languages": ["en", "ru"],
        "source": "Linear / Raycast dark UI craft + research/replan/design_eval_and_canons.md#3",
        "type_scale": {"ratio": 1.2, "base_rem": 1.0, "line_height_body": 1.55, "line_height_heading": 1.12, "measure_ch": "64ch", "tabular_nums": True},
        "fonts": {"heading": "'Geist', 'Inter', system-ui, sans-serif", "body": "'Geist', 'Inter', system-ui, sans-serif", "mono": "'Geist Mono', 'JetBrains Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.14 0.012 260)",
            "surface": "oklch(0.185 0.016 260)",
            "border": "oklch(0.28 0.02 260)",
            "text": "oklch(0.93 0.008 260)",
            "muted": "oklch(0.69 0.018 260)",
            "accent": "oklch(0.56 0.19 258)",
            "accent_ink": "oklch(0.98 0.005 260)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 10, "shadow": "0 12px 32px -8px oklch(0.06 0.01 260)", "pad_clamp": "clamp(2rem, 5.5vw, 7rem)", "container_query_bp": "600px", "viewport_unit": "100dvh"},
        "motion": {"ease": "cubic-bezier(0.16, 1, 0.3, 1)", "duration_ms": 220, "reduced_motion_policy": "Replace spring transforms with 120ms opacity transitions"},
        "scroll_padding_top_px": 68,
        "imagery": {
            "prompt_tmpl": "Precision anodized dark slate aluminum hardware module resting on matte obsidian surface, subtle indigo optical fiber edge illumination, macro product photography 90mm tilt-shift, crisp specular micro-bevel, subject: {subject}",
            "negative_prompt": "cartoon robot, glowing purple brain, messy lens flare, stock business team, washed-out gray fog",
            "aspect_ratio": "16:9",
            "style_tags": ["dark-anodized", "macro-hardware", "bento-instrument", "precision-optics"],
        },
        "rules": {
            "do": [
                "Build depth via stepped OKLCH lightness surfaces (L=0.14 canvas, L=0.185 card, L=0.28 crisp 1px border)",
                "Embed real interactive telemetry tables, keyboard shortcut kbd caps, and SVG sparklines inside bento cells",
                "Keep primary body copy at L=0.93 off-white (never glaring L=1.0 on pure L=0.0 black)",
                "Align multi-card bento rows with CSS subgrid so headers, charts, and footers lock horizontally"
            ],
            "dont": [
                "Never use pure #000000 canvas or pure #FFFFFF body paragraphs that cause halation",
                "Never plaster giant blurred purple/magenta radial blobs behind unreadable headings",
                "Never fake product screenshots with empty gray skeleton boxes",
                "Never drop muted secondary labels below 4.5:1 WCAG AA contrast against dark surfaces"
            ],
        },
        "ref_sites": ["linear.app", "raycast.com", "resend.com"],
    },
    {
        "id": "04_editorial_broadsheet_serif",
        "name": "Modern Editorial Broadsheet",
        "category": "editorial_typography",
        "languages": ["en", "ru"],
        "source": "Financial Times / Works in Progress longform print-to-web canon",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0625, "line_height_body": 1.62, "line_height_heading": 1.1, "measure_ch": "65ch", "tabular_nums": True},
        "fonts": {"heading": "'Source Serif 4', 'PT Serif', Georgia, serif", "body": "'Source Serif 4', 'PT Serif', Georgia, serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.965 0.016 78)",
            "surface": "oklch(0.935 0.02 78)",
            "border": "oklch(0.32 0.018 78)",
            "text": "oklch(0.17 0.012 65)",
            "muted": "oklch(0.42 0.018 65)",
            "accent": "oklch(0.44 0.14 25)",
            "accent_ink": "oklch(0.98 0.008 78)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 2, "shadow": "none", "pad_clamp": "clamp(2rem, 5vw, 6.5rem)", "container_query_bp": "680px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.25, 0.1, 0.25, 1)", "duration_ms": 180, "reduced_motion_policy": "Static layout transitions; preserve underline thickness hover cue"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Editorial copperplate engraving and stipple ink illustration on warm rag cotton paper, archival claret and sepia ink accents, classical architectural cross-section detail, crisp linework, subject: {subject}",
            "negative_prompt": "3d glossy plastic, neon lighting, stock corporate smiling people, digital glitch, oversaturated cyan",
            "aspect_ratio": "3:2",
            "style_tags": ["archival-engraving", "warm-newsprint", "editorial-serif", "stipple-ink"],
        },
        "rules": {
            "do": [
                "Separate major editorial sections with double-rule top borders (3px + 1px) and dateline metadata",
                "Use optical serif display sizing with ::first-letter lead dropcap on flagship essays",
                "Place sidenotes and source citations in an explicit 4-column margin rail next to an 8-column prose track",
                "Format data tables with horizontal hairline rules only and right-aligned tabular numerals"
            ],
            "dont": [
                "Never put serif longform text inside rounded shadowed SaaS cards",
                "Never exceed 68ch line length on main reading columns",
                "Never use generic sans-serif uppercase pill badges in bright neon colors",
                "Never omit publication date, reading duration, or primary-source attribution"
            ],
        },
        "ref_sites": ["worksinprogress.co", "ft.com", "press.stripe.com"],
    },
    {
        "id": "05_nordic_architectural_minimal",
        "name": "Nordic Architectural Timber & Stone",
        "category": "architectural_spatial",
        "languages": ["en", "ru"],
        "source": "Nordic architectural monograph & acoustic studio digital canon",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0, "line_height_body": 1.58, "line_height_heading": 1.12, "measure_ch": "60ch", "tabular_nums": True},
        "fonts": {"heading": "'Newsreader', 'Source Serif 4', Georgia, serif", "body": "'Plus Jakarta Sans', 'Inter', sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.97 0.008 85)",
            "surface": "oklch(0.935 0.012 85)",
            "border": "oklch(0.76 0.014 85)",
            "text": "oklch(0.19 0.012 80)",
            "muted": "oklch(0.44 0.015 80)",
            "accent": "oklch(0.38 0.065 155)",
            "accent_ink": "oklch(0.98 0.005 85)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 2, "shadow": "none", "pad_clamp": "clamp(2.25rem, 6vw, 7.5rem)", "container_query_bp": "640px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.22, 1, 0.36, 1)", "duration_ms": 280, "reduced_motion_policy": "Disable image scale reveals; preserve instant focus rings"},
        "scroll_padding_top_px": 80,
        "imagery": {
            "prompt_tmpl": "Nordic architectural interior crafted from untreated birch acoustic slats and honed limestone floor, soft diffused high-latitude daylight through tall timber mullions, Hasselblad 50mm medium format, serene natural textures, subject: {subject}",
            "negative_prompt": "artificial neon LED strips, cluttered furniture, HDR halo, glossy plastic, stock model posing",
            "aspect_ratio": "16:9",
            "style_tags": ["nordic-timber", "medium-format-daylight", "honed-limestone", "architectural-calm"],
        },
        "rules": {
            "do": [
                "Preserve generous structural negative space (at least 35% open limestone canvas per section)",
                "Pair understated serif spatial headings with clean geometric sans technical specifications",
                "Present project dossiers with exact floor area (m2), material provenance, and acoustic metrics",
                "Use muted pine-slate green accent exclusively for primary actions and dimension callouts"
            ],
            "dont": [
                "Never crowd hero sections with floating promo banners, countdown timers, or chat popups",
                "Never apply heavy black borders or glossy elevation shadows",
                "Never mix warm natural stone backgrounds with cold electric cyan accents",
                "Never truncate architectural specifications behind vague marketing slogans"
            ],
        },
        "ref_sites": ["snohetta.com", "normcph.com", "menu.as"],
    },
    {
        "id": "06_japanese_ma_wabi_editorial",
        "name": "Ma Spatial Quietude & Craft",
        "category": "cultural_exhibition",
        "languages": ["en", "ru"],
        "source": "Kenya Hara / Nippon Design Center spatial interval (Ma) web typography",
        "type_scale": {"ratio": 1.2, "base_rem": 1.0, "line_height_body": 1.68, "line_height_heading": 1.18, "measure_ch": "54ch", "tabular_nums": True},
        "fonts": {"heading": "'Fraunces', 'Source Serif 4', serif", "body": "'Inter', system-ui, sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.965 0.011 72)",
            "surface": "oklch(0.93 0.015 72)",
            "border": "oklch(0.78 0.016 70)",
            "text": "oklch(0.18 0.01 60)",
            "muted": "oklch(0.43 0.014 60)",
            "accent": "oklch(0.41 0.11 32)",
            "accent_ink": "oklch(0.98 0.006 72)",
        },
        "layout": {"grid_cols": 8, "subgrid": True, "radius_px": 0, "shadow": "none", "pad_clamp": "clamp(2.5rem, 7vw, 8rem)", "container_query_bp": "600px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.33, 1, 0.68, 1)", "duration_ms": 320, "reduced_motion_policy": "Zero motion; rely solely on spatial rhythm and crisp focus borders"},
        "scroll_padding_top_px": 76,
        "imagery": {
            "prompt_tmpl": "Handmade ceramic vessel and raw linen textile resting on charred sugi cedar plinth, raking side window light casting soft shadow on textured plaster wall, 85mm prime lens f/4, tranquil tonal restraint, subject: {subject}",
            "negative_prompt": "busy collage, bright neon colors, shiny chrome, text watermark, wide-angle distortion",
            "aspect_ratio": "4:5",
            "style_tags": ["wabi-tactile", "raking-light", "washi-linen", "spatial-ma"],
        },
        "rules": {
            "do": [
                "Use an 8-column asymmetric layout where 2-3 columns remain intentionally empty as breathing interval",
                "Anchor exhibition or craft entries with concise provenance tables (material, kiln/origin, dimensions)",
                "Restrict accent color to iron-oxide terracotta seals and primary reservation triggers",
                "Maintain 1.65+ body line-height and narrow 52ch-56ch prose measure"
            ],
            "dont": [
                "Never use bouncy spring animations, marquee tickers, or badge clutter",
                "Never fill every grid track edge-to-edge without quiet margin columns",
                "Never use synthetic stock mockups or rounded SaaS pricing cards",
                "Never insert CJK decorative characters into English or Russian UI copy"
            ],
        },
        "ref_sites": ["ndc.co.jp", "aesop.com", "kinto-usa.com"],
    },
    {
        "id": "07_industrial_functional_instrument",
        "name": "Braun / Rams Functional Instrument",
        "category": "b2b_industrial",
        "languages": ["en", "ru"],
        "source": "Dieter Rams 10 Principles / Teenage Engineering industrial panel interface",
        "type_scale": {"ratio": 1.2, "base_rem": 1.0, "line_height_body": 1.5, "line_height_heading": 1.1, "measure_ch": "60ch", "tabular_nums": True},
        "fonts": {"heading": "'IBM Plex Sans', 'Inter', sans-serif", "body": "'IBM Plex Sans', 'Inter', sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1"},
        "palette": {
            "bg": "oklch(0.94 0.006 88)",
            "surface": "oklch(0.98 0.003 88)",
            "border": "oklch(0.68 0.008 88)",
            "text": "oklch(0.16 0.006 88)",
            "muted": "oklch(0.41 0.008 88)",
            "accent": "oklch(0.53 0.19 38)",
            "accent_ink": "oklch(0.99 0.002 88)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 6, "shadow": "0 1px 2px oklch(0.16 0.006 88 / 0.12)", "pad_clamp": "clamp(1.5rem, 4vw, 4.5rem)", "container_query_bp": "580px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 120, "reduced_motion_policy": "Immediate state toggle; zero transition delay"},
        "scroll_padding_top_px": 64,
        "imagery": {
            "prompt_tmpl": "Precision bead-blasted light gray aluminum industrial control module, recessed matte orange physical toggle switch, laser-etched metric scale markings, overhead studio softbox orthographic shot, 100mm macro lens, subject: {subject}",
            "negative_prompt": "sci-fi hologram, purple glow, messy cables, dramatic smoke, cartoon style",
            "aspect_ratio": "4:3",
            "style_tags": ["industrial-design", "bead-blasted-aluminum", "orthographic-macro", "rams-functional"],
        },
        "rules": {
            "do": [
                "Group controls and specifications into recessed chassis panels with 1px machined borders and 6px corner radii",
                "Pair every numeric readout with explicit SI engineering units (ms, kHz, W, GiB/s) in IBM Plex Mono",
                "Reserve international safety orange-red strictly for primary power/commit actions and active indicators",
                "Expose hardware compatibility, tolerances, and thermal envelopes in structured specification matrices"
            ],
            "dont": [
                "Never use ornamental illustrations that do not explain physical or software mechanism",
                "Never obscure tolerances or pricing behind vague contact-sales gates when standard tiers exist",
                "Never apply colorful gradients to chassis backgrounds",
                "Never use italicized or script display typography"
            ],
        },
        "ref_sites": ["teenage.engineering", "framework.computer", "play.date"],
    },
    {
        "id": "08_fintech_institutional_ledger",
        "name": "Institutional Treasury & Clearing Ledger",
        "category": "fintech_institutional",
        "languages": ["en", "ru"],
        "source": "Stripe Treasury / Column Bank / Mercury institutional financial design",
        "type_scale": {"ratio": 1.2, "base_rem": 1.0, "line_height_body": 1.52, "line_height_heading": 1.12, "measure_ch": "64ch", "tabular_nums": True},
        "fonts": {"heading": "'Plus Jakarta Sans', 'Inter', sans-serif", "body": "'Inter', system-ui, sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.98 0.004 245)",
            "surface": "oklch(0.95 0.007 245)",
            "border": "oklch(0.80 0.012 245)",
            "text": "oklch(0.17 0.02 250)",
            "muted": "oklch(0.43 0.022 250)",
            "accent": "oklch(0.39 0.11 250)",
            "accent_ink": "oklch(0.99 0.003 245)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 8, "shadow": "0 2px 8px -2px oklch(0.17 0.02 250 / 0.08)", "pad_clamp": "clamp(2rem, 5vw, 6rem)", "container_query_bp": "620px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 160, "reduced_motion_policy": "Disable number roll animations; render final ledger balances immediately"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Architectural limestone bank vault facade detail with brushed stainless steel Louver geometry, crisp daylight, clean institutional minimalism, 50mm architectural tilt-shift lens, deep navy and cool stone palette, subject: {subject}",
            "negative_prompt": "golden bitcoin coins, stacks of cash, green matrix code, cartoon piggy bank, neon stock chart",
            "aspect_ratio": "16:9",
            "style_tags": ["institutional-trust", "cool-slate", "architectural-steel", "precision-ledger"],
        },
        "rules": {
            "do": [
                "Enforce font-variant-numeric: tabular-nums lining-nums on every basis-point, fee, settlement window, and balance",
                "Display regulatory disclosures, custody architecture, and settlement SLA cutoffs directly in body tables",
                "Use deep sovereign navy on crisp cool-white ledger surfaces with >= 12:1 primary contrast",
                "Provide interactive fee or yield calculators with deterministic formula disclosure"
            ],
            "dont": [
                "Never use floating 3D crypto coins, rocket emojis, or gamified confetti",
                "Never hide fee schedules or settlement latency behind marketing hyperbole",
                "Never use low-contrast pastel mint text on white backgrounds",
                "Never animate financial figures with distracting slot-machine counters"
            ],
        },
        "ref_sites": ["column.com", "mercury.com", "stripe.com"],
    },
    {
        "id": "09_monospace_cli_devtools",
        "name": "Terminal-Native CLI & Systems Infrastructure",
        "category": "devtools_cli",
        "languages": ["en", "ru"],
        "source": "Charm.sh / Tailscale / Zig / Fly.io engineering-first documentation & landing canon",
        "type_scale": {"ratio": 1.2, "base_rem": 0.96875, "line_height_body": 1.55, "line_height_heading": 1.15, "measure_ch": "66ch", "tabular_nums": True},
        "fonts": {"heading": "'JetBrains Mono', 'Fira Code', monospace", "body": "'IBM Plex Sans', 'Inter', sans-serif", "mono": "'JetBrains Mono', 'Fira Code', monospace", "license": "SIL OFL-1.1"},
        "palette": {
            "bg": "oklch(0.15 0.01 235)",
            "surface": "oklch(0.20 0.014 235)",
            "border": "oklch(0.32 0.02 235)",
            "text": "oklch(0.92 0.01 220)",
            "muted": "oklch(0.70 0.018 220)",
            "accent": "oklch(0.78 0.14 165)",
            "accent_ink": "oklch(0.15 0.02 165)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 4, "shadow": "none", "pad_clamp": "clamp(1.5rem, 4.5vw, 5rem)", "container_query_bp": "600px", "viewport_unit": "100dvh"},
        "motion": {"ease": "linear", "duration_ms": 90, "reduced_motion_policy": "Disable cursor blink and transition delays"},
        "scroll_padding_top_px": 64,
        "imagery": {
            "prompt_tmpl": "Macro photograph of custom matte black mechanical PCB backplane with gold-plated PCIe traces and single phosphor-mint diagnostic LED, sharp focus stacking, 105mm macro lens, clean studio darkroom lighting, subject: {subject}",
            "negative_prompt": "hooded hacker, green matrix rain, glowing blue globe, blurry bokeh, cartoon terminal",
            "aspect_ratio": "16:9",
            "style_tags": ["pcb-macro", "phosphor-mint", "systems-engineering", "matte-solder-mask"],
        },
        "rules": {
            "do": [
                "Place copyable single-line install command and reproducible benchmark table above the fold",
                "Use dark ink text on high-lightness phosphor-mint accent buttons for crisp AAA readability",
                "Show real CLI stdout, exit codes, memory footprint (MiB), and p99 latency numbers",
                "Structure architecture diagrams with clean inline SVG box-and-wire schematics"
            ],
            "dont": [
                "Never gate technical documentation or CLI flags behind newsletter modals",
                "Never put white text on bright mint or cyan buttons (fails WCAG contrast)",
                "Never use vague enterprise buzzwords instead of concrete protocol and syscall names",
                "Never auto-play looping terminal typing animations that shift page height"
            ],
        },
        "ref_sites": ["tailscale.com", "ziglang.org", "duckdb.org"],
    },
    {
        "id": "10_scientific_documentation_tufte",
        "name": "Tufte Analytical Monograph & Research Note",
        "category": "scientific_documentation",
        "languages": ["en", "ru"],
        "source": "Edward Tufte Visual Display of Quantitative Information / Distill.pub web layout",
        "type_scale": {"ratio": 1.2, "base_rem": 1.0625, "line_height_body": 1.6, "line_height_heading": 1.15, "measure_ch": "60ch", "tabular_nums": True},
        "fonts": {"heading": "'Newsreader', 'Source Serif 4', Georgia, serif", "body": "'Newsreader', 'Source Serif 4', Georgia, serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.985 0.01 92)",
            "surface": "oklch(0.95 0.012 92)",
            "border": "oklch(0.75 0.014 92)",
            "text": "oklch(0.16 0.008 85)",
            "muted": "oklch(0.43 0.012 85)",
            "accent": "oklch(0.44 0.13 245)",
            "accent_ink": "oklch(0.99 0.004 92)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 0, "shadow": "none", "pad_clamp": "clamp(2rem, 5vw, 6rem)", "container_query_bp": "680px", "viewport_unit": "100svh"},
        "motion": {"ease": "linear", "duration_ms": 100, "reduced_motion_policy": "Static charts with instant hover inspection"},
        "scroll_padding_top_px": 64,
        "imagery": {
            "prompt_tmpl": "Precision scientific optical bench diagram with glass prism refraction paths on warm ivory vellum, fine technical pen linework and muted cobalt annotation ink, natural flat archival lighting, subject: {subject}",
            "negative_prompt": "glowing sci-fi DNA helix, futuristic HUD, purple galaxy background, 3d render bloom",
            "aspect_ratio": "16:9",
            "style_tags": ["tufte-analytical", "data-ink-ratio", "archival-vellum", "scientific-diagram"],
        },
        "rules": {
            "do": [
                "Maximize data-ink ratio: strip heavy chart gridlines, 3D bars, and decorative chart frames",
                "Pair 8-column analytical prose with 4-column margin notes, inline sparklines, and direct figure labels",
                "Label curves and series directly on SVG plots instead of forcing eye movement to distant legends",
                "Report sample size (N), confidence intervals, and measurement methodology alongside every claim"
            ],
            "dont": [
                "Never use pie charts, donut gauges, or uncalibrated decorative progress bars",
                "Never interrupt empirical text with full-bleed promotional hero banners",
                "Never hide methodology caveats in tiny low-contrast footnotes",
                "Never use rainbow colormaps that fail grayscale and deuteranopia legibility"
            ],
        },
        "ref_sites": ["distill.pub", "edwardtufte.github.io", "ourworldindata.org"],
    },
    {
        "id": "11_warm_artisan_hospitality",
        "name": "Terroir Gastronomy & Boutique Hospitality",
        "category": "commerce_craft",
        "languages": ["en", "ru"],
        "source": "Noma / Kinfolk / Michelin-starred regional hospitality web editorial",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0, "line_height_body": 1.6, "line_height_heading": 1.12, "measure_ch": "58ch", "tabular_nums": True},
        "fonts": {"heading": "'Fraunces', 'PT Serif', Georgia, serif", "body": "'Plus Jakarta Sans', 'Inter', sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.96 0.02 75)",
            "surface": "oklch(0.925 0.024 75)",
            "border": "oklch(0.74 0.026 70)",
            "text": "oklch(0.19 0.02 50)",
            "muted": "oklch(0.43 0.025 50)",
            "accent": "oklch(0.43 0.12 42)",
            "accent_ink": "oklch(0.98 0.008 75)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 4, "shadow": "none", "pad_clamp": "clamp(2rem, 5.5vw, 6.5rem)", "container_query_bp": "600px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.25, 1, 0.5, 1)", "duration_ms": 240, "reduced_motion_policy": "Static photography frames; instant tab switching on seasonal menus"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Overhead natural-light editorial photograph of artisanal sourdough, stoneware ceramics, and cast-iron service on weathered oak table, soft morning window light, Kodak Portra 400 natural grain, warm ochre and umber palette, subject: {subject}",
            "negative_prompt": "oversaturated fast food commercial, harsh flash, neon bar sign, plastic tableware, AI distorted hands",
            "aspect_ratio": "4:5",
            "style_tags": ["natural-daylight", "stoneware-terroir", "editorial-gastronomy", "warm-ochre"],
        },
        "rules": {
            "do": [
                "Publish complete menu pricing, allergen tags, opening hours, and exact street address directly in HTML text (never PDF-only)",
                "Use warm parchment surfaces with deep roasted-umber typography and burnt-sienna reservation actions",
                "Keep reservation forms to <= 4 labeled inputs with explicit date/time/party-size semantics",
                "Align menu items and prices cleanly via CSS Grid with right-aligned tabular figures"
            ],
            "dont": [
                "Never lock menus, wine lists, or room rates inside downloadable PDFs",
                "Never auto-play background video or audio on hospitality pages",
                "Never use cold SaaS blue buttons or generic star-rating carousels",
                "Never hide cancellation policy or service-charge percentage until checkout"
            ],
        },
        "ref_sites": ["noma.dk", "bluebottlecoffee.com", "aesop.com"],
    },
    {
        "id": "12_clinical_biotech_cleanroom",
        "name": "Clinical Diagnostics & Biotech Cleanroom",
        "category": "scientific_documentation",
        "languages": ["en", "ru"],
        "source": "ISO-13485 medical device & clinical genomics portal interface canon",
        "type_scale": {"ratio": 1.2, "base_rem": 1.0, "line_height_body": 1.55, "line_height_heading": 1.14, "measure_ch": "64ch", "tabular_nums": True},
        "fonts": {"heading": "'Public Sans', 'Inter', sans-serif", "body": "'Public Sans', 'Inter', sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.985 0.005 210)",
            "surface": "oklch(0.95 0.01 210)",
            "border": "oklch(0.78 0.016 210)",
            "text": "oklch(0.17 0.018 220)",
            "muted": "oklch(0.43 0.02 220)",
            "accent": "oklch(0.44 0.11 205)",
            "accent_ink": "oklch(0.99 0.003 210)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 6, "shadow": "0 1px 3px oklch(0.17 0.018 220 / 0.08)", "pad_clamp": "clamp(2rem, 5vw, 5.5rem)", "container_query_bp": "620px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 140, "reduced_motion_policy": "Zero motion on clinical thresholds and diagnostic tables"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Sterile ISO-5 laboratory microfluidic quartz chip in brushed stainless fixture, crisp neutral daylight balanced 5600K studio illumination, 100mm macro apochromatic lens, clean teal and optical glass clarity, subject: {subject}",
            "negative_prompt": "glowing mutant DNA, stock doctor pointing at floating hologram, dramatic dark blue vignette, lens flare",
            "aspect_ratio": "16:9",
            "style_tags": ["iso-cleanroom", "microfluidic-glass", "clinical-precision", "neutral-5600k"],
        },
        "rules": {
            "do": [
                "State sensitivity, specificity, limit of detection (LoD), turnaround hours, and validation cohort size upfront",
                "Use sterile high-lightness cool white surfaces with deep slate-teal AAA text and clear regulatory status badges",
                "Separate validated clinical claims from investigational research-use-only (RUO) modules with explicit borders",
                "Ensure every assay parameter table supports keyboard navigation and >= 24px filter controls"
            ],
            "dont": [
                "Never use sci-fi holographic tropes or stock photos of actors in stethoscopes",
                "Never present sensitivity percentages without denominator sample counts and confidence bounds",
                "Never rely on color alone (red vs green) to indicate normal vs abnormal clinical ranges",
                "Never use playful display fonts or informal marketing slang in clinical copy"
            ],
        },
        "ref_sites": ["color.com", "nanoporetech.com", "10xgenomics.com"],
    },
    {
        "id": "13_bauhaus_geometric_poster",
        "name": "Bauhaus Constructive Geometry",
        "category": "cultural_exhibition",
        "languages": ["en", "ru"],
        "source": "Dessau Bauhaus exhibition & architectural symposium poster grid",
        "type_scale": {"ratio": 1.333, "base_rem": 1.0, "line_height_body": 1.5, "line_height_heading": 1.04, "measure_ch": "58ch", "tabular_nums": True},
        "fonts": {"heading": "'Space Grotesk', 'Inter', sans-serif", "body": "'Inter', system-ui, sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.96 0.018 88)",
            "surface": "oklch(0.99 0.006 88)",
            "border": "oklch(0.14 0.005 88)",
            "text": "oklch(0.14 0.005 88)",
            "muted": "oklch(0.40 0.01 88)",
            "accent": "oklch(0.46 0.17 255)",
            "accent_ink": "oklch(0.99 0.004 88)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 0, "shadow": "none", "pad_clamp": "clamp(1.75rem, 4.5vw, 5rem)", "container_query_bp": "600px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 150, "reduced_motion_policy": "Static geometric blocks; instant color invert on focus"},
        "scroll_padding_top_px": 68,
        "imagery": {
            "prompt_tmpl": "Dessau modernist white stucco architectural corner with primary cobalt steel window frame and crisp geometric afternoon shadow, medium format architectural photography, sharp verticals, warm archival paper cast, subject: {subject}",
            "negative_prompt": "pastel vaporwave, soft blur, 3d cartoon character, neon purple, cluttered street",
            "aspect_ratio": "1:1",
            "style_tags": ["bauhaus-dessau", "constructive-geometry", "primary-cobalt", "thick-rule"],
        },
        "rules": {
            "do": [
                "Divide layout zones using visible 2px-4px black structural rules and orthogonal geometric SVG primitives",
                "Structure event schedules, speaker rosters, and ticket tiers in strict asymmetric tabular blocks",
                "Use pure geometric primitives (circle, square, diagonal rule) strictly as functional wayfinding anchors",
                "Keep primary ink contrast >= 14:1 against warm archival off-white"
            ],
            "dont": [
                "Never add drop shadows, frosted glass blur, or skeuomorphic textures",
                "Never overload all three primary colors simultaneously on adjacent text blocks",
                "Never use rounded 16px SaaS card corners",
                "Never sacrifice timetable readability for tilted unreadable body paragraphs"
            ],
        },
        "ref_sites": ["bauhaus-dessau.de", "stedelijk.nl", "cca.qc.ca"],
    },
    {
        "id": "14_kinetic_cultural_exhibition",
        "name": "Contemporary Museum & Architecture Biennale",
        "category": "cultural_exhibition",
        "languages": ["en", "ru"],
        "source": "Kunsthalle / Venice Architecture Biennale curatorial catalog web system",
        "type_scale": {"ratio": 1.333, "base_rem": 1.0, "line_height_body": 1.55, "line_height_heading": 1.05, "measure_ch": "60ch", "tabular_nums": True},
        "fonts": {"heading": "'Golos Text', 'Space Grotesk', sans-serif", "body": "'Golos Text', 'Inter', sans-serif", "mono": "'JetBrains Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.15 0.006 280)",
            "surface": "oklch(0.20 0.008 280)",
            "border": "oklch(0.35 0.01 280)",
            "text": "oklch(0.95 0.005 90)",
            "muted": "oklch(0.72 0.008 90)",
            "accent": "oklch(0.84 0.16 88)",
            "accent_ink": "oklch(0.15 0.01 88)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 0, "shadow": "none", "pad_clamp": "clamp(2rem, 5vw, 6rem)", "container_query_bp": "640px", "viewport_unit": "100dvh"},
        "motion": {"ease": "cubic-bezier(0.19, 1, 0.22, 1)", "duration_ms": 240, "reduced_motion_policy": "Disable all scroll-linked or hover transforms; preserve static curatorial index"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Large-scale architectural steel and tensioned translucent fabric installation inside raw industrial gallery hall, dramatic museum track spotlighting, wide architectural 24mm tilt-shift lens, high tonal contrast, subject: {subject}",
            "negative_prompt": "stock museum crowd with smartphones, neon cyberpunk, AI garbled poster text, oversaturated HDR",
            "aspect_ratio": "16:9",
            "style_tags": ["gallery-installation", "curatorial-dark", "ochre-signal", "architectural-scale"],
        },
        "rules": {
            "do": [
                "Lead with exhibition dates, venue hall coordinates, curatorial thesis, and direct timed-entry ticketing",
                "Use high-contrast warm alabaster type on matte gallery charcoal with warm signal-amber index accents",
                "Organize exhibited works and public lectures into filterable index rows with room numbers",
                "Ensure dark ink (`accent_ink`) on amber buttons exceeds 10:1 luminance contrast"
            ],
            "dont": [
                "Never hijack native browser scroll (`scroll-jacking`) or replace the system cursor",
                "Never hide visitor hours, accessibility ramp info, or admission prices inside hamburger submenus",
                "Never set white text on yellow/amber buttons",
                "Never leave exhibition artwork images without descriptive curatorial alt text"
            ],
        },
        "ref_sites": ["labiennale.org", "kw-berlin.de", "garagemca.org"],
    },
    {
        "id": "15_high_contrast_civic_gov_wcag_aaa",
        "name": "Civic Public Service & WCAG AAA Portal",
        "category": "civic_accessible",
        "languages": ["en", "ru"],
        "source": "GOV.UK Design System / USWDS public digital service standard",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0625, "line_height_body": 1.6, "line_height_heading": 1.15, "measure_ch": "64ch", "tabular_nums": True},
        "fonts": {"heading": "'Public Sans', 'Golos Text', system-ui, sans-serif", "body": "'Public Sans', 'Golos Text', system-ui, sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.99 0.002 250)",
            "surface": "oklch(0.945 0.006 250)",
            "border": "oklch(0.25 0.01 250)",
            "text": "oklch(0.13 0.008 250)",
            "muted": "oklch(0.36 0.012 250)",
            "accent": "oklch(0.38 0.14 252)",
            "accent_ink": "oklch(0.99 0.002 250)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 2, "shadow": "none", "pad_clamp": "clamp(1.5rem, 4vw, 4rem)", "container_query_bp": "560px", "viewport_unit": "100svh"},
        "motion": {"ease": "linear", "duration_ms": 80, "reduced_motion_policy": "Zero decorative transitions across all viewports"},
        "scroll_padding_top_px": 80,
        "imagery": {
            "prompt_tmpl": "Clean flat isometric civic wayfinding diagram showing municipal transit hub and accessible pedestrian ramp, crisp dark navy linework on pure white ground, high-legibility public signage aesthetic, subject: {subject}",
            "negative_prompt": "decorative stock photography, low-contrast pastel icons, blurry background, dramatic shadows",
            "aspect_ratio": "16:9",
            "style_tags": ["civic-wayfinding", "wcag-aaa", "plain-language", "public-service"],
        },
        "rules": {
            "do": [
                "Maintain >= 14:1 AAA primary contrast and >= 7:1 AAA contrast even on secondary helper copy",
                "Enforce >= 44px height on primary form inputs/buttons (strictly >= 24px minimum on all inline links) with 3px high-visibility focus outlines",
                "Lead every service page with eligibility criteria, required documents list, processing time, and fee",
                "Use explicit <label>, <fieldset>/<legend>, and plain-language inline error summaries linked by href"
            ],
            "dont": [
                "Never use placeholder attributes as a substitute for persistent visible <label> elements",
                "Never use promotional hero imagery where task links and status lookup belong",
                "Never require JavaScript for reading statutory instructions, fees, or deadlines",
                "Never use jargon, passive bureaucratic syntax, or ambiguous 'Click here' anchor text"
            ],
        },
        "ref_sites": ["gov.uk", "designsystem.digital.gov", "service.gov.uk"],
    },
    {
        "id": "16_luxury_horology_atelier_dark",
        "name": "Haute Horlogerie & Precision Atelier",
        "category": "commerce_craft",
        "languages": ["en", "ru"],
        "source": "A. Lange & Sohne / Nomos Glashutte / Leica precision mechanical craft canon",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0, "line_height_body": 1.6, "line_height_heading": 1.12, "measure_ch": "58ch", "tabular_nums": True},
        "fonts": {"heading": "'Fraunces', 'Source Serif 4', Georgia, serif", "body": "'Inter', system-ui, sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.14 0.008 65)",
            "surface": "oklch(0.19 0.01 65)",
            "border": "oklch(0.33 0.02 70)",
            "text": "oklch(0.93 0.01 80)",
            "muted": "oklch(0.70 0.018 75)",
            "accent": "oklch(0.80 0.11 78)",
            "accent_ink": "oklch(0.15 0.015 65)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 2, "shadow": "0 16px 40px -12px oklch(0.05 0.005 65)", "pad_clamp": "clamp(2.5rem, 6vw, 7.5rem)", "container_query_bp": "640px", "viewport_unit": "100dvh"},
        "motion": {"ease": "cubic-bezier(0.22, 1, 0.36, 1)", "duration_ms": 280, "reduced_motion_policy": "Disable parallax or zoom; retain crisp caliper specification tab switches"},
        "scroll_padding_top_px": 76,
        "imagery": {
            "prompt_tmpl": "Extreme macro focus-stacked studio photograph of German-silver mechanical watch movement bridge with hand-beveled anglage, blued steel screws, and ruby jewel bearings, controlled dark rim lighting, 120mm macro lens, subject: {subject}",
            "negative_prompt": "gaudy diamond bling, lens flare explosion, stock businessman in suit, purple neon, plastic render",
            "aspect_ratio": "3:2",
            "style_tags": ["horology-macro", "german-silver", "warm-obsidian", "mechanical-caliber"],
        },
        "rules": {
            "do": [
                "Pair warm obsidian surfaces with champagne-brass accents and dark espresso ink inside primary buttons",
                "Present exact mechanical specifications (caliber number, frequency Hz/vph, power reserve hours, case mm, water resistance bar)",
                "Use crisp hairline borders and generous vertical cadence rather than e-commerce discount badges",
                "Enforce tabular numerals across reference numbers, dimensions, and pricing"
            ],
            "dont": [
                "Never display fake urgency timers, strike-through discount tags, or 'spin-to-win' popups",
                "Never put white text on pale gold or champagne fills",
                "Never use ultra-thin hairline body fonts below 400 weight on dark backgrounds",
                "Never obscure service intervals or warranty terms"
            ],
        },
        "ref_sites": ["alange-soehne.com", "nomos-glashuette.com", "leica-camera.com"],
    },
    {
        "id": "17_sustainable_climate_botanical",
        "name": "Climate Infrastructure & Grid Ecology",
        "category": "b2b_industrial",
        "languages": ["en", "ru"],
        "source": "Watershed / Patch / Charm Industrial empirical climate engineering canon",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0, "line_height_body": 1.56, "line_height_heading": 1.1, "measure_ch": "62ch", "tabular_nums": True},
        "fonts": {"heading": "'Manrope', 'Inter', sans-serif", "body": "'Inter', system-ui, sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.97 0.012 135)",
            "surface": "oklch(0.935 0.018 135)",
            "border": "oklch(0.75 0.025 138)",
            "text": "oklch(0.18 0.025 148)",
            "muted": "oklch(0.42 0.03 148)",
            "accent": "oklch(0.40 0.10 152)",
            "accent_ink": "oklch(0.985 0.006 135)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 8, "shadow": "none", "pad_clamp": "clamp(2rem, 5vw, 6rem)", "container_query_bp": "620px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 180, "reduced_motion_policy": "Instant SVG chart updates without path stroke animation"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Aerial architectural photograph of utility-scale grid battery storage enclosure beside native boreal pine forest, crisp overcast daylight, Hasselblad medium format, natural mineral green and slate tones, subject: {subject}",
            "negative_prompt": "hands holding tiny globe with sprout, stock wind turbine sunset lens flare, cartoon green leaf icon",
            "aspect_ratio": "16:9",
            "style_tags": ["empirical-climate", "grid-ecology", "mineral-pine", "verified-lca"],
        },
        "rules": {
            "do": [
                "Substantiate every sustainability claim with tCO2e, MWh, ISO-14064 lifecycle boundaries, and verification registry IDs",
                "Use deep boreal forest ink on pale lichen-mineral surfaces for >= 11:1 AAA legibility",
                "Present Scope 1/2/3 abatement breakdowns via clean accessible SVG stacked bar or Sankey diagrams",
                "Provide downloadable methodology summaries and transparent permanence/additionality criteria"
            ],
            "dont": [
                "Never use greenwashing stock cliches (hands cupping a seedling or glowing green earth)",
                "Never claim vague '100% eco-friendly' slogans without lifecycle mass-balance numbers",
                "Never use bright lime text on white backgrounds",
                "Never omit system boundary definitions on carbon or energy calculators"
            ],
        },
        "ref_sites": ["watershed.com", "charmindustrial.com", "stripe.com/climate"],
    },
    {
        "id": "18_bento_hardware_showcase",
        "name": "Modular Silicon & Hardware Bento Spec",
        "category": "b2b_industrial",
        "languages": ["en", "ru"],
        "source": "Apple Silicon / Oxide Computer / Framework modular hardware specification grid",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0, "line_height_body": 1.5, "line_height_heading": 1.08, "measure_ch": "62ch", "tabular_nums": True},
        "fonts": {"heading": "'Plus Jakarta Sans', 'Inter', sans-serif", "body": "'Inter', system-ui, sans-serif", "mono": "'JetBrains Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.13 0.006 250)",
            "surface": "oklch(0.18 0.008 250)",
            "border": "oklch(0.30 0.012 250)",
            "text": "oklch(0.94 0.005 250)",
            "muted": "oklch(0.71 0.01 250)",
            "accent": "oklch(0.78 0.14 148)",
            "accent_ink": "oklch(0.14 0.02 148)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 14, "shadow": "0 8px 24px -6px oklch(0.05 0.005 250)", "pad_clamp": "clamp(2rem, 5vw, 6rem)", "container_query_bp": "640px", "viewport_unit": "100dvh"},
        "motion": {"ease": "cubic-bezier(0.16, 1, 0.3, 1)", "duration_ms": 200, "reduced_motion_policy": "Static bento cards; instant workload selector updates"},
        "scroll_padding_top_px": 68,
        "imagery": {
            "prompt_tmpl": "Orthographic top-down macro photograph of custom server compute sled with CNC copper coldplate, blind-mate backplane connector, and matte black silicon package, studio precision lighting, 90mm macro lens, subject: {subject}",
            "negative_prompt": "glowing blue brain chip, sci-fi laser beams, messy server cables, purple haze",
            "aspect_ratio": "16:9",
            "style_tags": ["oxide-rack", "silicon-bento", "cnc-copper", "orthographic-hardware"],
        },
        "rules": {
            "do": [
                "Compose unequal bento spans (7+5, 4+4+4, 8+4) on a 12-column CSS Grid with subgrid vertical alignment",
                "Anchor each bento cell with one verified engineering metric (GB/s bandwidth, TOPS/W, MTBF hours, acoustic dBA)",
                "Collapse bento spans cleanly at @container (max-width: 640px) without horizontal clipping",
                "Pair Oxide-emerald accent controls with dark charcoal button ink (>= 10:1 contrast)"
            ],
            "dont": [
                "Never create 12 identical small square bento tiles with zero visual hierarchy",
                "Never show unlabelled benchmark bars without baseline hardware, batch size, and precision notes",
                "Never rely on 100vh hero sections that clip specifications on mobile browsers",
                "Never use external font CDNs or giant unoptimized PNG renders"
            ],
        },
        "ref_sites": ["oxide.computer", "framework.computer", "panic.com"],
    },
    {
        "id": "19_quant_analytics_dense_terminal",
        "name": "High-Density Quantitative Telemetry Workstation",
        "category": "fintech_institutional",
        "languages": ["en", "ru"],
        "source": "OpenBB / Datadog / Grafana high-density observability & market microstructure UI",
        "type_scale": {"ratio": 1.15, "base_rem": 0.9375, "line_height_body": 1.45, "line_height_heading": 1.15, "measure_ch": "68ch", "tabular_nums": True},
        "fonts": {"heading": "'IBM Plex Sans', 'Inter', sans-serif", "body": "'IBM Plex Sans', 'Inter', sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1"},
        "palette": {
            "bg": "oklch(0.14 0.01 245)",
            "surface": "oklch(0.185 0.014 245)",
            "border": "oklch(0.29 0.018 245)",
            "text": "oklch(0.92 0.008 240)",
            "muted": "oklch(0.69 0.015 240)",
            "accent": "oklch(0.80 0.13 210)",
            "accent_ink": "oklch(0.14 0.02 220)",
        },
        "layout": {"grid_cols": 16, "subgrid": True, "radius_px": 4, "shadow": "none", "pad_clamp": "clamp(1.25rem, 3vw, 3rem)", "container_query_bp": "560px", "viewport_unit": "100dvh"},
        "motion": {"ease": "linear", "duration_ms": 80, "reduced_motion_policy": "Instant state updates; zero chart interpolation lag"},
        "scroll_padding_top_px": 60,
        "imagery": {
            "prompt_tmpl": "Precision fiber-optic patch transceiver bulkhead in low-key dark data hall, clean cyan diagnostic status LEDs, sharp technical depth of field, 85mm prime lens, dark slate aesthetic, subject: {subject}",
            "negative_prompt": "3d bull and bear statues, glowing red crash arrows, stock trader screaming, matrix code",
            "aspect_ratio": "21:9",
            "style_tags": ["quant-workstation", "microstructure-grid", "tabular-density", "low-latency"],
        },
        "rules": {
            "do": [
                "Use compact 15px base type with strict tabular-nums and crisp 1px cell dividers for multi-column orderbook/trace tables",
                "Pair every status color indicator with an explicit text token or shape glyph (OK / WARN / CRIT) for colorblind safety",
                "Keep interactive filter buttons >= 24x24px with keyboard focus rings and ARIA sort states",
                "Render sparklines and p50/p95/p99 histograms via deterministic inline SVG"
            ],
            "dont": [
                "Never waste half the viewport on oversized hero marketing slogans when presenting analytical workstations",
                "Never mutate element `.style.*` attributes from JS; toggle semantic data attributes or SVG geometry attributes",
                "Never mix proportional numerals inside aligned numeric columns",
                "Never use blurred glass overlays that degrade dense numeric legibility"
            ],
        },
        "ref_sites": ["openbb.co", "questdb.io", "clickhouse.com"],
    },
    {
        "id": "20_spatial_glass_dark_instrument",
        "name": "Layered Dark Optical Slate & Hairline Specular",
        "category": "saas_product",
        "languages": ["en", "ru"],
        "source": "Raycast / Arc / Zed low-glare layered dark desktop tool aesthetic",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0, "line_height_body": 1.54, "line_height_heading": 1.1, "measure_ch": "62ch", "tabular_nums": True},
        "fonts": {"heading": "'Plus Jakarta Sans', 'Inter', sans-serif", "body": "'Inter', system-ui, sans-serif", "mono": "'JetBrains Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.15 0.015 270)",
            "surface": "oklch(0.20 0.018 270)",
            "border": "oklch(0.32 0.024 270)",
            "text": "oklch(0.93 0.008 270)",
            "muted": "oklch(0.70 0.016 270)",
            "accent": "oklch(0.81 0.12 195)",
            "accent_ink": "oklch(0.15 0.02 200)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 12, "shadow": "0 16px 36px -10px oklch(0.06 0.01 270)", "pad_clamp": "clamp(2rem, 5vw, 6rem)", "container_query_bp": "600px", "viewport_unit": "100dvh"},
        "motion": {"ease": "cubic-bezier(0.16, 1, 0.3, 1)", "duration_ms": 200, "reduced_motion_policy": "Disable backdrop transitions and scale transforms"},
        "scroll_padding_top_px": 68,
        "imagery": {
            "prompt_tmpl": "Precision optical smoked-quartz prism resting on dark brushed titanium plate, single crisp ice-cyan refracted light beam, studio macro product photography, clean minimal geometry, subject: {subject}",
            "negative_prompt": "busy rainbow lens flare, vaporwave statue, purple neon blob, low-res noise",
            "aspect_ratio": "16:9",
            "style_tags": ["optical-quartz", "smoked-slate", "command-palette", "desktop-craft"],
        },
        "rules": {
            "do": [
                "Guarantee solid opaque fallback contrast (>= 11:1) on `--surface` and `--bg` tokens without relying on backdrop-filter for readability",
                "Showcase concrete command-palette workflows, latency benchmarks (ms), and offline privacy guarantees",
                "Use crisp 1px top-edge specular borders and ice-cyan accent buttons with dark ink",
                "Structure feature comparisons as scannable capability matrices"
            ],
            "dont": [
                "Never place body text over high-frequency gradients or busy background images",
                "Never abuse heavy `backdrop-filter: blur(40px)` across multiple scrolling cards (destroys GPU frame budget)",
                "Never use purple-pink-orange AI gradient text fills on headings",
                "Never omit keyboard navigation and ARIA roles on command-bar tabs"
            ],
        },
        "ref_sites": ["zed.dev", "raycast.com", "cron.com"],
    },
    {
        "id": "21_constructivist_editorial_ru",
        "name": "Russian Constructivist Technical Editorial",
        "category": "editorial_typography",
        "languages": ["ru", "en"],
        "source": "VKhUTEMAS / Rodchenko / modern Russian engineering bureau typographic heritage",
        "type_scale": {"ratio": 1.333, "base_rem": 1.0, "line_height_body": 1.52, "line_height_heading": 1.06, "measure_ch": "62ch", "tabular_nums": True},
        "fonts": {"heading": "'Golos Text', 'PT Sans', system-ui, sans-serif", "body": "'Golos Text', 'Inter', system-ui, sans-serif", "mono": "'JetBrains Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.955 0.02 84)",
            "surface": "oklch(0.985 0.008 84)",
            "border": "oklch(0.15 0.008 40)",
            "text": "oklch(0.15 0.008 40)",
            "muted": "oklch(0.40 0.015 40)",
            "accent": "oklch(0.49 0.19 27)",
            "accent_ink": "oklch(0.985 0.006 84)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 0, "shadow": "none", "pad_clamp": "clamp(1.75rem, 4.5vw, 5.5rem)", "container_query_bp": "620px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 130, "reduced_motion_policy": "Static typographic bars; instant border inversion on focus"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Constructivist hyperboloid steel lattice tower photographed from crisp geometric angle against pale overcast sky, archival monochrome silver-gelatin contrast with single vermilion structural girder accent, Leica 50mm, subject: {subject}",
            "negative_prompt": "soviet kitsch clipart, weathered grunge scratches, distressed unreadable text, neon cyberpunk",
            "aspect_ratio": "4:3",
            "style_tags": ["vkhutemas-grid", "shukhov-lattice", "vermilion-black-ivory", "cyrillic-grotesk"],
        },
        "rules": {
            "do": [
                "Set Cyrillic headings in native Cyrillic-proportioned grotesk ('Golos Text') with tight tracking and heavy 3px horizontal overlines",
                "Use «ёлочки» quotation marks, hyphenated Latin-Cyrillic compounds (`B2B-контур`, `API-шлюз`), and active finite Russian verbs",
                "Organize engineering deliverables into numbered passport blocks (Паспорт узла 01..04) using CSS subgrid",
                "Restrict palette strictly to unbleached paper, deep carbon ink, and structural vermilion"
            ],
            "dont": [
                "Never glue Latin acronyms directly to Cyrillic case endings without a hyphen (causes mixed-script token defects)",
                "Never use fake Cyrillic display fonts or distressed grunge textures",
                "Never write Russian copy with English calques ('инновационный опыт', 'бесшовное путешествие')",
                "Never center-align Russian specification lists"
            ],
        },
        "ref_sites": ["paratype.ru", "shukhov.org", "v-a-c.org"],
    },
    {
        "id": "22_legal_advisory_chancery",
        "name": "Chancery Legal, Compliance & Audit Practice",
        "category": "fintech_institutional",
        "languages": ["en", "ru"],
        "source": "Appellate brief typography (Butterick Typography for Lawyers) & regulatory advisory portals",
        "type_scale": {"ratio": 1.2, "base_rem": 1.0625, "line_height_body": 1.6, "line_height_heading": 1.15, "measure_ch": "62ch", "tabular_nums": True},
        "fonts": {"heading": "'Source Serif 4', 'PT Serif', Georgia, serif", "body": "'Source Serif 4', 'PT Serif', Georgia, serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.98 0.008 85)",
            "surface": "oklch(0.945 0.012 85)",
            "border": "oklch(0.76 0.015 85)",
            "text": "oklch(0.16 0.015 255)",
            "muted": "oklch(0.42 0.018 255)",
            "accent": "oklch(0.36 0.09 255)",
            "accent_ink": "oklch(0.99 0.004 85)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 2, "shadow": "none", "pad_clamp": "clamp(2rem, 5vw, 6rem)", "container_query_bp": "640px", "viewport_unit": "100svh"},
        "motion": {"ease": "linear", "duration_ms": 110, "reduced_motion_policy": "Static accordion and citation anchor jumps"},
        "scroll_padding_top_px": 76,
        "imagery": {
            "prompt_tmpl": "Architectural detail of travertine stone colonnade and bronze reading lamp inside quiet modernist law library, balanced natural daylight, medium format 65mm lens, dignified slate and warm parchment tones, subject: {subject}",
            "negative_prompt": "wooden gavel clipart, golden scales of justice 3d render, stock handshake, dramatic courtroom spotlight",
            "aspect_ratio": "16:9",
            "style_tags": ["butterick-legal", "oxford-slate", "statutory-clarity", "archival-bond"],
        },
        "rules": {
            "do": [
                "Number practice areas, statutory citations, and engagement stages with § / clause markers and hanging indents",
                "Publish partner credentials, bar admissions, representative matter metrics, and conflict-check intake rules clearly",
                "Keep reading measure strictly between 55ch and 65ch with generous 1.6 line-height",
                "Include explicit confidentiality notice and honeypot protection on conflict-check forms"
            ],
            "dont": [
                "Never use wooden gavels, Lady Justice statues, or handshake stock photos",
                "Never set entire paragraphs in ALL CAPS or bold italic legalese",
                "Never use chat widgets or aggressive lead-capture popups on advisory pages",
                "Never obscure jurisdiction boundaries or regulatory disclaimers"
            ],
        },
        "ref_sites": ["typographyforlawyers.com", "cravath.com", "icj-cij.org"],
    },
    {
        "id": "23_audio_dsp_modular_rack",
        "name": "Studio DSP & Acoustic Synthesis Hardware",
        "category": "devtools_cli",
        "languages": ["en", "ru"],
        "source": "FabFilter / Ableton / Elektron precision audio engineering UI canon",
        "type_scale": {"ratio": 1.2, "base_rem": 1.0, "line_height_body": 1.5, "line_height_heading": 1.1, "measure_ch": "62ch", "tabular_nums": True},
        "fonts": {"heading": "'Space Grotesk', 'Inter', sans-serif", "body": "'IBM Plex Sans', 'Inter', sans-serif", "mono": "'JetBrains Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.16 0.008 250)",
            "surface": "oklch(0.21 0.01 250)",
            "border": "oklch(0.33 0.014 250)",
            "text": "oklch(0.93 0.006 250)",
            "muted": "oklch(0.70 0.012 250)",
            "accent": "oklch(0.80 0.16 72)",
            "accent_ink": "oklch(0.15 0.02 65)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 6, "shadow": "0 4px 16px oklch(0.06 0.005 250)", "pad_clamp": "clamp(1.75rem, 4.5vw, 5rem)", "container_query_bp": "600px", "viewport_unit": "100dvh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 110, "reduced_motion_policy": "Freeze spectrum animations; render static transfer-function curve"},
        "scroll_padding_top_px": 64,
        "imagery": {
            "prompt_tmpl": "Anodized brushed charcoal 500-series studio rack module with machined aluminum stepped attenuator knobs and warm amber OLED dB meter, 90mm studio macro photography, crisp engraved decibel scale markings, subject: {subject}",
            "negative_prompt": "dj concert crowd lasers, neon purple headphones clipart, blurry club lights",
            "aspect_ratio": "16:9",
            "style_tags": ["eurorack-anodized", "amber-meter", "dsp-transfer-curve", "precision-audio"],
        },
        "rules": {
            "do": [
                "Display calibrated frequency response / THD+N SVG transfer plots with labelled Hz and dBFS axes",
                "State plugin formats (CLAP, VST3, AU, LV2), sample-rate support, lookahead latency (samples/ms), and OS compatibility",
                "Use warm studio-amber accents with dark ink labels on matte charcoal rack panels",
                "Provide keyboard-accessible parameter sliders (`<input type='range'>`) with live `<output>` dB/Hz readouts"
            ],
            "dont": [
                "Never auto-play audio without explicit user interaction",
                "Never use unreadable photorealistic chrome bevel knobs in web UI controls",
                "Never omit CPU usage, zero-latency mode availability, or offline license activation policy",
                "Never use low-contrast dark gray labels on dark rack panels"
            ],
        },
        "ref_sites": ["fabfilter.com", "ableton.com", "elektron.se"],
    },
    {
        "id": "24_cartographic_field_expedition",
        "name": "Topographic Survey & Geospatial Atlas",
        "category": "scientific_documentation",
        "languages": ["en", "ru"],
        "source": "Swisstopo / USGS / Felt cartographic & geospatial engineering web canon",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0, "line_height_body": 1.55, "line_height_heading": 1.1, "measure_ch": "62ch", "tabular_nums": True},
        "fonts": {"heading": "'IBM Plex Sans', 'Inter', sans-serif", "body": "'IBM Plex Sans', 'Inter', sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1"},
        "palette": {
            "bg": "oklch(0.965 0.016 95)",
            "surface": "oklch(0.935 0.02 95)",
            "border": "oklch(0.72 0.025 95)",
            "text": "oklch(0.18 0.018 130)",
            "muted": "oklch(0.42 0.022 130)",
            "accent": "oklch(0.46 0.15 35)",
            "accent_ink": "oklch(0.985 0.006 95)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 4, "shadow": "none", "pad_clamp": "clamp(1.75rem, 4.5vw, 5.5rem)", "container_query_bp": "620px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 150, "reduced_motion_policy": "Static contour SVG overlays; instant coordinate readout"},
        "scroll_padding_top_px": 68,
        "imagery": {
            "prompt_tmpl": "Detailed Swiss topographic relief map sheet printed on matte cotton survey paper with fine ochre elevation contours, shaded glacier hachures, and brass surveyor Vernier compass edge, overhead flat-lay 50mm macro, subject: {subject}",
            "negative_prompt": "3d cartoon map pin, glowing blue sci-fi globe, cluttered satellite UI, purple neon",
            "aspect_ratio": "16:9",
            "style_tags": ["swisstopo-contour", "geodetic-grid", "survey-paper", "datum-coordinates"],
        },
        "rules": {
            "do": [
                "Frame sections with subtle graticule coordinate ticks (WGS84 / EPSG codes, scale bar, elevation m)",
                "Use Swisstopo-inspired survey paper canvas, deep forest-slate ink, and benchmark survey-vermilion markers",
                "Render elevation profiles, LiDAR point-density specs, and CRS support in crisp inline SVG & tabular tables",
                "Enforce tabular numerals on all latitude/longitude, resolution (cm/px), and area metrics"
            ],
            "dont": [
                "Never embed third-party Google/Mapbox iframe tiles that violate offline zero-external-URL CSP rules",
                "Never put body text directly over dense contour lines without an opaque surface backing",
                "Never omit spatial resolution, coordinate reference system, or update cadence",
                "Never use generic red drop-pin clipart"
            ],
        },
        "ref_sites": ["swisstopo.admin.ch", "felt.com", "protomaps.com"],
    },
    {
        "id": "25_academic_journal_monograph",
        "name": "Peer-Reviewed Open-Access Monograph",
        "category": "scientific_documentation",
        "languages": ["en", "ru"],
        "source": "eLife / ACL Anthology / JMLR open-science HTML article specification",
        "type_scale": {"ratio": 1.2, "base_rem": 1.0625, "line_height_body": 1.62, "line_height_heading": 1.16, "measure_ch": "64ch", "tabular_nums": True},
        "fonts": {"heading": "'IBM Plex Serif', 'PT Serif', Georgia, serif", "body": "'IBM Plex Sans', 'Inter', sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.99 0.003 90)",
            "surface": "oklch(0.955 0.006 240)",
            "border": "oklch(0.80 0.01 240)",
            "text": "oklch(0.15 0.01 245)",
            "muted": "oklch(0.41 0.015 245)",
            "accent": "oklch(0.41 0.13 248)",
            "accent_ink": "oklch(0.99 0.002 90)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 2, "shadow": "none", "pad_clamp": "clamp(1.75rem, 4.5vw, 5rem)", "container_query_bp": "660px", "viewport_unit": "100svh"},
        "motion": {"ease": "linear", "duration_ms": 80, "reduced_motion_policy": "Zero motion; instant anchor navigation to equations and references"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Clean vector-like architectural block schematic of neural sparse expert routing on crisp white journal paper, slate-blue and charcoal geometric blocks, publication-grade figure clarity, zero decorative shading, subject: {subject}",
            "negative_prompt": "glowing blue brain synapses, robot hand touching human finger, dark purple matrix",
            "aspect_ratio": "16:9",
            "style_tags": ["open-science", "booktabs-table", "journal-monograph", "reproducible-artifact"],
        },
        "rules": {
            "do": [
                "Open with structured Abstract, DOI/artifact identifier, author affiliations, and sticky section outline",
                "Format quantitative tables in strict LaTeX booktabs style (top rule, header rule, bottom rule, zero vertical bars, bold best results)",
                "Provide BibTeX citation block and checksummed artifact reproduction instructions",
                "Link inline `[1]` reference markers bidirectionally to the bibliography list"
            ],
            "dont": [
                "Never wrap academic papers in SaaS pricing tiers or marketing hero slogans",
                "Never use zebra-striped colorful table backgrounds that obscure numeric comparisons",
                "Never present benchmark gains without baseline version, hardware spec, and seed count",
                "Never use external MathJax/KaTeX CDN scripts when native HTML/SVG math suffices offline"
            ],
        },
        "ref_sites": ["elifesciences.org", "jmlr.org", "aclanthology.org"],
    },
    {
        "id": "26_ecommerce_lookbook_grid",
        "name": "Editorial Object & Apparel Lookbook",
        "category": "commerce_craft",
        "languages": ["en", "ru"],
        "source": "Vitsoe / Outlier / Snow Peak functional object & technical apparel catalog",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0, "line_height_body": 1.54, "line_height_heading": 1.1, "measure_ch": "58ch", "tabular_nums": True},
        "fonts": {"heading": "'Manrope', 'Inter', sans-serif", "body": "'Inter', system-ui, sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1 / System Stack"},
        "palette": {
            "bg": "oklch(0.98 0.004 80)",
            "surface": "oklch(0.945 0.006 80)",
            "border": "oklch(0.82 0.008 80)",
            "text": "oklch(0.15 0.005 80)",
            "muted": "oklch(0.42 0.008 80)",
            "accent": "oklch(0.22 0.01 80)",
            "accent_ink": "oklch(0.99 0.002 80)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 0, "shadow": "none", "pad_clamp": "clamp(1.5rem, 4vw, 5rem)", "container_query_bp": "580px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 160, "reduced_motion_policy": "Instant swatch and size-matrix updates"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Technical 3-layer weatherproof ripstop field jacket photographed flat on matte neutral light-gray studio seamless backdrop, crisp weave texture detail, diffused overhead softbox, 85mm prime lens, color-accurate neutral profile, subject: {subject}",
            "negative_prompt": "fake discount sticker, neon shopping cart icon, distorted AI garment seams, oversaturated street bokeh",
            "aspect_ratio": "4:5",
            "style_tags": ["technical-apparel", "lookbook-grid", "material-gsm", "neutral-studio"],
        },
        "rules": {
            "do": [
                "Use CSS subgrid across product cards so aspect-ratio frame, SKU title, fabric GSM spec, and price align horizontally",
                "Include an explicit garment/object measurement table in millimeters/centimeters alongside stock status",
                "State fabric composition, GSM weight, country of origin, repair warranty, and shipping cost upfront",
                "Include Schema.org Product + Offer JSON-LD matching visible price and currency verbatim"
            ],
            "dont": [
                "Never show 'Someone in London just bought this!' social-proof toast spam",
                "Never hide shipping costs or return restocking fees until final checkout",
                "Never use star-rating widgets without verified review counts",
                "Never distort product aspect ratios across responsive breakpoints"
            ],
        },
        "ref_sites": ["vitsoe.com", "snowpeak.com", "outlier.nyc"],
    },
    {
        "id": "27_cybersecurity_zero_trust_ops",
        "name": "Zero-Trust Cryptography & Security Engineering",
        "category": "security_operations",
        "languages": ["en", "ru"],
        "source": "Trail of Bits / WireGuard / Mullvad verifiable security & audit engineering canon",
        "type_scale": {"ratio": 1.2, "base_rem": 1.0, "line_height_body": 1.55, "line_height_heading": 1.12, "measure_ch": "64ch", "tabular_nums": True},
        "fonts": {"heading": "'Space Grotesk', 'IBM Plex Sans', sans-serif", "body": "'IBM Plex Sans', 'Inter', sans-serif", "mono": "'Fira Code', 'JetBrains Mono', monospace", "license": "SIL OFL-1.1"},
        "palette": {
            "bg": "oklch(0.14 0.012 240)",
            "surface": "oklch(0.19 0.015 240)",
            "border": "oklch(0.31 0.02 240)",
            "text": "oklch(0.93 0.008 230)",
            "muted": "oklch(0.70 0.015 230)",
            "accent": "oklch(0.82 0.14 145)",
            "accent_ink": "oklch(0.14 0.02 145)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 4, "shadow": "none", "pad_clamp": "clamp(1.75rem, 4.5vw, 5.5rem)", "container_query_bp": "600px", "viewport_unit": "100dvh"},
        "motion": {"ease": "linear", "duration_ms": 90, "reduced_motion_policy": "Zero decorative motion; static threat-model diagrams"},
        "scroll_padding_top_px": 68,
        "imagery": {
            "prompt_tmpl": "Tamper-evident CNC milled titanium hardware security module (HSM) smartcard reader on dark anti-static workbench, crisp studio key light, sharp laser-engraved SHA-256 fingerprint detail, 100mm macro lens, subject: {subject}",
            "negative_prompt": "man in black hoodie at laptop, glowing green padlock, binary code rain, skull icon",
            "aspect_ratio": "16:9",
            "style_tags": ["cryptographic-assurance", "hsm-titanium", "threat-model", "verifiable-security"],
        },
        "rules": {
            "do": [
                "State exact cryptographic primitives (ChaCha20-Poly1305, Ed25519, ML-KEM-768), audit firm names, and CVE/advisory history",
                "Include an explicit Threat Model section separating what the system protects against vs out-of-scope assumptions",
                "Ship strict zero-external-request pages (`default-src 'none'`, SHA-256 CSP, COOP/COEP/CORP) that practice what the copy claims",
                "Publish PGP/minisign public keys and reproducible build hashes in monospace blocks"
            ],
            "dont": [
                "Never claim 'military-grade unhackable security'—security engineers immediately distrust superlative claims",
                "Never use hooded-hacker stock photos or glowing 3D padlocks",
                "Never embed third-party analytics trackers on security or privacy product pages",
                "Never obscure key custody or telemetry retention defaults"
            ],
        },
        "ref_sites": ["mullvad.net", "wireguard.com", "trailofbits.com"],
    },
    {
        "id": "28_craft_roastery_packaging",
        "name": "Specialty Roastery & Apothecary Label System",
        "category": "commerce_craft",
        "languages": ["en", "ru"],
        "source": "Tim Wendelboe / Sey Coffee / apothecary batch-card packaging typography",
        "type_scale": {"ratio": 1.25, "base_rem": 1.0, "line_height_body": 1.56, "line_height_heading": 1.1, "measure_ch": "58ch", "tabular_nums": True},
        "fonts": {"heading": "'Fraunces', 'Source Serif 4', serif", "body": "'IBM Plex Sans', 'Inter', sans-serif", "mono": "'IBM Plex Mono', monospace", "license": "SIL OFL-1.1"},
        "palette": {
            "bg": "oklch(0.97 0.015 82)",
            "surface": "oklch(0.99 0.006 82)",
            "border": "oklch(0.24 0.015 55)",
            "text": "oklch(0.17 0.015 55)",
            "muted": "oklch(0.42 0.018 55)",
            "accent": "oklch(0.42 0.12 28)",
            "accent_ink": "oklch(0.99 0.005 82)",
        },
        "layout": {"grid_cols": 12, "subgrid": True, "radius_px": 2, "shadow": "none", "pad_clamp": "clamp(1.75rem, 4.5vw, 5.5rem)", "container_query_bp": "580px", "viewport_unit": "100svh"},
        "motion": {"ease": "cubic-bezier(0.2, 0, 0, 1)", "duration_ms": 150, "reduced_motion_policy": "Static batch cards; instant grind/weight selector updates"},
        "scroll_padding_top_px": 72,
        "imagery": {
            "prompt_tmpl": "Letterpress-printed cotton batch card and matte kraft gusseted coffee pouch beside brass laboratory cupping spoon on travertine counter, soft diffused north-window daylight, 65mm macro lens, crisp tactile paper fibers, subject: {subject}",
            "negative_prompt": "steaming cartoon coffee cup clipart, dark grunge chalkboard menu, oversaturated stock barista",
            "aspect_ratio": "4:5",
            "style_tags": ["apothecary-batch-card", "letterpress-cotton", "traceable-origin", "cupping-spec"],
        },
        "rules": {
            "do": [
                "Design product cards as structured apothecary batch labels with tabular rows (Producer, Varietal, Process, Altitude masl, Harvest month, Farmgate price paid)",
                "Use crisp 1px espresso-ink borders dividing label cells on warm cotton-paper surfaces",
                "Provide interactive brew-ratio calculators (dose grams -> water ml + temperature C) with zero JS style mutations",
                "Keep primary text contrast >= 12:1 AAA and roast/subscribe actions in deep berry-terracotta"
            ],
            "dont": [
                "Never use chalkboard fonts, coffee-bean border clipart, or burlap grunge backgrounds",
                "Never hide bag weight (g) or roast dispatch schedule below the fold",
                "Never force subscription lock-in as the only purchase option without a clear one-off toggle",
                "Never use vague tasting adjectives without concrete origin and processing metadata"
            ],
        },
        "ref_sites": ["timwendelboe.no", "seycoffee.com", "squaremilecoffee.com"],
    },
]


def main() -> None:
    os.makedirs(CARDS_DIR, exist_ok=True)
    written = 0
    for item in RAW_CARDS:
        pal = item["palette"]
        cr_text_bg = contrast_ratio(pal["text"], pal["bg"])
        cr_text_surf = contrast_ratio(pal["text"], pal["surface"])
        cr_muted_bg = contrast_ratio(pal["muted"], pal["bg"])
        cr_muted_surf = contrast_ratio(pal["muted"], pal["surface"])
        cr_accent = contrast_ratio(pal["accent_ink"], pal["accent"])

        eff_text_cr = min(cr_text_bg, cr_text_surf)
        eff_muted_cr = min(cr_muted_bg, cr_muted_surf)

        if eff_text_cr < 7.0:
            raise AssertionError(f"{item['id']}: text contrast {eff_text_cr} < 7.0 AAA")
        if eff_muted_cr < 4.5:
            raise AssertionError(f"{item['id']}: muted contrast {eff_muted_cr} < 4.5 AA")
        if cr_accent < 4.5:
            raise AssertionError(f"{item['id']}: accent contrast {cr_accent} < 4.5 AA")

        card = {
            "id": item["id"],
            "name": item["name"],
            "category": item["category"],
            "languages": item["languages"],
            "provenance": {
                "source": item["source"],
                "curated_date": CURATED_DATE,
                "license": "CC0-1.0 / Internal RAG Canon",
                "rag_only": True,
            },
            "type_scale": item["type_scale"],
            "fonts": item["fonts"],
            "palette": pal,
            "layout": item["layout"],
            "motion": item["motion"],
            "a11y": {
                "wcag_level": "AAA" if (eff_text_cr >= 7.0 and cr_accent >= 7.0) else "AA",
                "min_target_px": 24,
                "scroll_padding_top_px": item["scroll_padding_top_px"],
                "text_bg_contrast_ratio": eff_text_cr,
                "muted_bg_contrast_ratio": eff_muted_cr,
                "accent_contrast_ratio": cr_accent,
            },
            "imagery": item["imagery"],
            "rules": item["rules"],
            "ref_sites": item["ref_sites"],
        }

        out_path = os.path.join(CARDS_DIR, f"{item['id']}.json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(card, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1

    print(f"Built {written} verified canon cards in {CARDS_DIR}")


if __name__ == "__main__":
    main()
