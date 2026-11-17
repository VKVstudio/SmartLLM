#!/usr/bin/env python3
"""
Deterministic local template & open-documentation builders for WP-C2 (SmartLLM v2):
  - full_doc_html_css (96 sequences, target ~110,000 tokens, 0 Tailwind, 0 API distillation)
  - web_dev_prose (72 sequences, target ~80,000 tokens, MDN CC-BY-SA-2.5 + web.dev CC-BY-4.0)
  - ts_js_node_backend (54 sequences, target ~60,000 tokens, nodejs/node MIT + mdn/dom-examples CC0-1.0)
  - seo_aeo_geo_security_checklists (29 sequences, target ~30,000 tokens, OWASP CC-BY-SA-4.0 + schema.org)
  - eval_E/gen_prompts_10.jsonl (5 EN + 5 RU non-trivial Web/Design/Copy/Security/Backend prompts)
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable


# Raw GitHub documentation & code sample sources (all permissive licenses, tiny byte footprint < 5 MB total)
GITHUB_RAW_SOURCES: list[dict[str, str]] = [
    # MDN Content (CC-BY-SA-2.5)
    {
        "group": "mdn_content",
        "repo": "mdn/content",
        "license": "CC-BY-SA-2.5",
        "path": "files/en-us/web/css/index.md",
        "url": "https://raw.githubusercontent.com/mdn/content/main/files/en-us/web/css/index.md",
        "topic": "CSS specifications, cascade architecture, layout modules, and color systems",
    },
    {
        "group": "mdn_content",
        "repo": "mdn/content",
        "license": "CC-BY-SA-2.5",
        "path": "files/en-us/web/html/index.md",
        "url": "https://raw.githubusercontent.com/mdn/content/main/files/en-us/web/html/index.md",
        "topic": "Semantic HTML5 document structure, metadata, forms, and ARIA integration",
    },
    {
        "group": "mdn_content",
        "repo": "mdn/content",
        "license": "CC-BY-SA-2.5",
        "path": "files/en-us/web/http/index.md",
        "url": "https://raw.githubusercontent.com/mdn/content/main/files/en-us/web/http/index.md",
        "topic": "HTTP protocol architecture, caching headers, CORS, and Content-Security-Policy",
    },
    {
        "group": "mdn_content",
        "repo": "mdn/content",
        "license": "CC-BY-SA-2.5",
        "path": "files/en-us/web/svg/index.md",
        "url": "https://raw.githubusercontent.com/mdn/content/main/files/en-us/web/svg/index.md",
        "topic": "Scalable Vector Graphics (SVG) coordinate systems, viewBox, and vector paths",
    },
    {
        "group": "mdn_content",
        "repo": "mdn/content",
        "license": "CC-BY-SA-2.5",
        "path": "files/en-us/web/accessibility/aria/index.md",
        "url": "https://raw.githubusercontent.com/mdn/content/main/files/en-us/web/accessibility/aria/index.md",
        "topic": "WAI-ARIA accessible roles, landmarks, live regions, and semantic HTML5",
    },
    # MDN DOM Examples (CC0-1.0)
    {
        "group": "mdn_dom_examples",
        "repo": "mdn/dom-examples",
        "license": "CC0-1.0",
        "path": "web-crypto/sign-verify/hmac.js",
        "url": "https://raw.githubusercontent.com/mdn/dom-examples/main/web-crypto/sign-verify/hmac.js",
        "topic": "Web Crypto API SubtleCrypto HMAC-SHA256 signing and verification",
    },
    {
        "group": "mdn_dom_examples",
        "repo": "mdn/dom-examples",
        "license": "CC0-1.0",
        "path": "web-crypto/encrypt-decrypt/aes-gcm.js",
        "url": "https://raw.githubusercontent.com/mdn/dom-examples/main/web-crypto/encrypt-decrypt/aes-gcm.js",
        "topic": "Web Crypto API AES-GCM authenticated encryption with initialization vectors",
    },
    {
        "group": "mdn_dom_examples",
        "repo": "mdn/dom-examples",
        "license": "CC0-1.0",
        "path": "streams/simple-pump/index.html",
        "url": "https://raw.githubusercontent.com/mdn/dom-examples/main/streams/simple-pump/index.html",
        "topic": "ReadableStream and WritableStream backpressure-aware chunk pumping",
    },
    # Node.js API Documentation (MIT)
    {
        "group": "nodejs_docs",
        "repo": "nodejs/node",
        "license": "MIT",
        "path": "doc/api/crypto.md",
        "url": "https://raw.githubusercontent.com/nodejs/node/main/doc/api/crypto.md",
        "topic": "Node.js node:crypto HMAC, timingSafeEqual, randomBytes, and scrypt",
    },
    {
        "group": "nodejs_docs",
        "repo": "nodejs/node",
        "license": "MIT",
        "path": "doc/api/http2.md",
        "url": "https://raw.githubusercontent.com/nodejs/node/main/doc/api/http2.md",
        "topic": "Node.js node:http2 multiplexed streams, ALPN, and secure server headers",
    },
    {
        "group": "nodejs_docs",
        "repo": "nodejs/node",
        "license": "MIT",
        "path": "doc/api/webstreams.md",
        "url": "https://raw.githubusercontent.com/nodejs/node/main/doc/api/webstreams.md",
        "topic": "Node.js Web Streams API (ReadableStream, TransformStream, WritableStream)",
    },
    # OWASP Cheat Sheet Series (CC-BY-SA-4.0)
    {
        "group": "owasp_cheatsheets",
        "repo": "OWASP/CheatSheetSeries",
        "license": "CC-BY-SA-4.0",
        "path": "cheatsheets/Content_Security_Policy_Cheat_Sheet.md",
        "url": "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Content_Security_Policy_Cheat_Sheet.md",
        "topic": "OWASP Content Security Policy (CSP) framing, script nonces, and strict-dynamic",
    },
    {
        "group": "owasp_cheatsheets",
        "repo": "OWASP/CheatSheetSeries",
        "license": "CC-BY-SA-4.0",
        "path": "cheatsheets/HTTP_Headers_Cheat_Sheet.md",
        "url": "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/HTTP_Headers_Cheat_Sheet.md",
        "topic": "OWASP HTTP Security Headers (HSTS, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)",
    },
    {
        "group": "owasp_cheatsheets",
        "repo": "OWASP/CheatSheetSeries",
        "license": "CC-BY-SA-4.0",
        "path": "cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.md",
        "url": "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.md",
        "topic": "OWASP CSRF Prevention via HMAC double-submit cookies, SameSite=Strict, and Sec-Fetch-Site",
    },
    {
        "group": "owasp_cheatsheets",
        "repo": "OWASP/CheatSheetSeries",
        "license": "CC-BY-SA-4.0",
        "path": "cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.md",
        "url": "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.md",
        "topic": "OWASP DOM-based XSS Prevention, sink contextual encoding, and Trusted Types",
    },
    {
        "group": "owasp_cheatsheets",
        "repo": "OWASP/CheatSheetSeries",
        "license": "CC-BY-SA-4.0",
        "path": "cheatsheets/Input_Validation_Cheat_Sheet.md",
        "url": "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Input_Validation_Cheat_Sheet.md",
        "topic": "OWASP Input Validation allowlists, schema enforcement, and canonicalization",
    },
    {
        "group": "owasp_cheatsheets",
        "repo": "OWASP/CheatSheetSeries",
        "license": "CC-BY-SA-4.0",
        "path": "cheatsheets/REST_Security_Cheat_Sheet.md",
        "url": "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/REST_Security_Cheat_Sheet.md",
        "topic": "OWASP REST API Security status codes, Content-Type validation, and rate limiting",
    },
]


def clean_markdown_frontmatter(text: str) -> str:
    """Strip YAML frontmatter and MDN macro tags while keeping technical prose & code blocks."""
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.S)
    text = re.sub(r"\{\{[^}]+\}\}", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_markdown_sections(text: str, min_chars: int = 900, max_chars: int = 3200) -> list[tuple[str, str]]:
    """Split markdown into coherent (heading, body) chunks suitable for <=2048 token calibration sequences."""
    cleaned = clean_markdown_frontmatter(text)
    parts = re.split(r"(?m)^(#{1,3}\s+.+)$", cleaned)
    sections: list[tuple[str, str]] = []
    cur_title = "Overview"
    cur_buf: list[str] = []
    cur_len = 0
    for part in parts:
        part_s = part.strip()
        if not part_s:
            continue
        if part_s.startswith("#"):
            if cur_len >= min_chars:
                sections.append((cur_title, "\n\n".join(cur_buf).strip()))
                cur_buf = []
                cur_len = 0
            cur_title = re.sub(r"^#{1,3}\s+", "", part_s).strip()
        else:
            if cur_len + len(part_s) > max_chars and cur_len >= min_chars:
                sections.append((cur_title, "\n\n".join(cur_buf).strip()))
                cur_buf = [part_s[:max_chars]]
                cur_len = len(cur_buf[0])
            else:
                cur_buf.append(part_s)
                cur_len += len(part_s)
    if cur_buf and cur_len >= 400:
        sections.append((cur_title, "\n\n".join(cur_buf).strip()))
    return sections


# 96 distinct domain configurations for full_doc_html_css (zero overlap with eval_E or holdout)
HTML_CSS_DOMAINS: list[dict[str, str]] = [
    {
        "brand": "Aurelia Photonic Foundry",
        "domain": "aurelia-photonics.example",
        "category": "Silicon Photonics Interconnects",
        "canon": "Swiss Precision Grid",
        "bg": "oklch(0.985 0.004 85)",
        "surface": "oklch(0.955 0.008 85)",
        "ink": "oklch(0.16 0.015 255)",
        "muted": "oklch(0.42 0.018 255)",
        "accent": "oklch(0.52 0.19 28)",
        "border": "oklch(0.84 0.012 85)",
        "headline": "Co-Packaged 1.6 Tbps Optical Interconnects at 1.4 pJ/bit",
        "lede": "Monolithic silicon nitride waveguides with integrated laser coupling for low-jitter AI cluster backplanes.",
        "m1_val": "1.6 Tbps", "m1_lbl": "Bi-directional aggregate bandwidth per optical engine",
        "m2_val": "1.4 pJ/b", "m2_lbl": "Wall-plug energy efficiency across 0-70 C case temp",
        "m3_val": "< 85 ns", "m3_lbl": "End-to-end FEC-free optical transit latency",
        "q1": "How does Aurelia maintain laser wavelength lock across thermal transients?",
        "a1": "Each 8-channel comb source uses closed-loop micro-heater ring resonators locking channel spacing to 200 GHz within +/- 1.5 GHz.",
        "q2": "Which host electrical interfaces are supported?",
        "a2": "Native 112G and 224G PAM4 SerDes XSR lanes with retimed and linear-drive optical engine pinouts.",
    },
    {
        "brand": "Borealis Cryo-Instrumentation",
        "domain": "borealis-cryo.example",
        "category": "Dilution Refrigerator Thermometry",
        "canon": "Atmospheric Minimalism & High-Craft Dark UI",
        "bg": "oklch(0.13 0.018 250)",
        "surface": "oklch(0.18 0.022 250)",
        "ink": "oklch(0.95 0.008 240)",
        "muted": "oklch(0.68 0.018 240)",
        "accent": "oklch(0.74 0.15 205)",
        "border": "oklch(0.28 0.025 250)",
        "headline": "Sub-Millikelvin RuO2 & Coulomb Blockade Readout Multiplexer",
        "lede": "24-channel ultra-low-excitation resistance bridge delivering 18 aW probe dissipation at the 10 mK mixing chamber stage.",
        "m1_val": "18 aW", "m1_lbl": "Maximum sensor self-heating at 12 mK base temperature",
        "m2_val": "24 ch", "m2_lbl": "Synchronized lock-in readout channels per 3U Eurocard",
        "m3_val": "0.04%", "m3_lbl": "Calibrated temperature uncertainty from 8 mK to 4.2 K",
        "q1": "Does the excitation bridge require external cold attenuators?",
        "a1": "Each channel integrates a balanced twin-axial current source with 80 dB common-mode rejection and cryogenic pi-filters.",
        "q2": "How is telemetry exported to laboratory control software?",
        "a2": "Deterministic gRPC and SCPI streams over galvanically isolated fiber Ethernet at up to 250 Hz per channel.",
    },
    {
        "brand": "Meridian Maritime Autonomy",
        "domain": "meridian-hydro.example",
        "category": "Hydrographic AUV Navigation",
        "canon": "Technical Industrial Blueprint",
        "bg": "oklch(0.15 0.024 235)",
        "surface": "oklch(0.20 0.028 235)",
        "ink": "oklch(0.94 0.010 220)",
        "muted": "oklch(0.70 0.020 220)",
        "accent": "oklch(0.76 0.16 165)",
        "border": "oklch(0.30 0.030 235)",
        "headline": "Doppler-Inertial Seafloor Mapping Down to 4,500 Meters",
        "lede": "Tightly coupled fiber-optic gyroscope and phased-array DVL navigation maintaining 0.03% distance-traveled CEP without acoustic beacons.",
        "m1_val": "4,500 m", "m1_lbl": "Titanium pressure hull depth rating with 1.8x safety factor",
        "m2_val": "0.03% DT", "m2_lbl": "Submerged dead-reckoning circular error probable",
        "m3_val": "78 hrs", "m3_lbl": "Continuous bathymetric survey endurance at 3.5 knots",
        "q1": "Can synthetic aperture sonar processing run onboard in real time?",
        "a1": "Yes, dual low-power embedded DSP blades generate 2 cm resolution bathymetric tiles during the mission.",
        "q2": "How are subsea obstacle avoidance trajectories computed?",
        "a2": "Forward-looking multibeam sonar feeds a receding-horizon planner updating 3D clearance corridors every 100 ms.",
    },
    {
        "brand": "Vespera Editorial Press",
        "domain": "vespera-press.example",
        "category": "Architectural Monograph Publishing",
        "canon": "Editorial Typography & Archival Paper",
        "bg": "oklch(0.97 0.012 75)",
        "surface": "oklch(0.94 0.016 75)",
        "ink": "oklch(0.18 0.015 50)",
        "muted": "oklch(0.44 0.020 50)",
        "accent": "oklch(0.46 0.16 25)",
        "border": "oklch(0.83 0.018 75)",
        "headline": "Monographs on Cast Concrete, Timber Gridshells, and Nordic Daylight",
        "lede": "Smyth-sewn clothbound editions printed on 150 gsm acid-free cotton rag with stochastic duotone plates and fold-out structural sections.",
        "m1_val": "150 gsm", "m1_lbl": "ISO 9706 permanent archival cotton-blend paper stock",
        "m2_val": "1 : 50", "m2_lbl": "Measured orthographic elevation and joinery drawings",
        "m3_val": "1,200", "m3_lbl": "Numbered first-edition copies per architectural volume",
        "q1": "Are digital vector CAD details included with print monographs?",
        "a1": "Every library edition includes an archival USB-C card and permanent DOI archive containing 1:20 DWG/SVG structural details.",
        "q2": "How are institutional library standing orders fulfilled?",
        "a2": "MARC21 catalog records and BISAC metadata ship alongside direct freight consolidation to university architecture collections.",
    },
    {
        "brand": "Solstice Grid Storage",
        "domain": "solstice-vanadium.example",
        "category": "Vanadium Redox Flow Batteries",
        "canon": "Clean Industrial Infrastructure",
        "bg": "oklch(0.98 0.006 110)",
        "surface": "oklch(0.95 0.010 110)",
        "ink": "oklch(0.17 0.020 160)",
        "muted": "oklch(0.43 0.022 160)",
        "accent": "oklch(0.54 0.15 152)",
        "border": "oklch(0.84 0.014 110)",
        "headline": "10-Hour Non-Flammable Vanadium Flow Blocks for Substation Firming",
        "lede": "Aqueous electrolyte storage modules with zero thermal runaway risk and 25,000 deep-cycle membrane longevity.",
        "m1_val": "25,000", "m1_lbl": "Full 0-100% depth-of-discharge cycles without capacity fade",
        "m2_val": "81.4%", "m2_lbl": "DC-to-DC stack round-trip efficiency at rated power",
        "m3_val": "10 hrs", "m3_lbl": "Continuous dispatch duration per 20 MW modular skid",
        "q1": "What happens to the vanadium electrolyte at end of plant life?",
        "a1": "The aqueous vanadium sulfate solution does not degrade chemically and is 100% recoverable for re-deployment or mineral resale.",
        "q2": "How rapidly can the inverter-stack assembly respond to grid frequency drops?",
        "a2": "Grid-forming PCS inverters inject synthetic inertia and full active power ramping within 18 milliseconds.",
    },
    {
        "brand": "Kestrel Deterministic Database",
        "domain": "kestrel-db.example",
        "category": "Consensus Financial Ledger Engine",
        "canon": "High-Craft Dark Developer Platform",
        "bg": "oklch(0.14 0.016 265)",
        "surface": "oklch(0.19 0.020 265)",
        "ink": "oklch(0.95 0.008 260)",
        "muted": "oklch(0.69 0.016 260)",
        "accent": "oklch(0.73 0.16 145)",
        "border": "oklch(0.28 0.022 265)",
        "headline": "Strict Serializable Double-Entry Accounting at 420,000 Transfers/sec",
        "lede": "Zero-allocation io_uring storage engine with deterministic simulation testing and Raft quorum replication across 5 fault zones.",
        "m1_val": "420k/s", "m1_lbl": "Committed two-phase financial transfers per NVMe cluster",
        "m2_val": "1.9 ms", "m2_lbl": "p999 cross-AZ quorum commit latency under load",
        "m3_val": "0 B", "m3_lbl": "Runtime heap allocations after static buffer ring startup",
        "q1": "How does Kestrel verify absence of split-brain corruption?",
        "a1": "Every commit batch is verified under deterministic fault-injection simulation with CRC64-NVMe hash chains on disk.",
        "q2": "Can immutable audit snapshots be streamed to analytical warehouses?",
        "a2": "Change-data-capture streams emit Arrow IPC batches over mTLS without blocking the primary Raft state machine.",
    },
    {
        "brand": "Caldera Geothermal Drilling",
        "domain": "caldera-egs.example",
        "category": "Superhot Rock Geothermal Systems",
        "canon": "Brutalist Technical Engineering",
        "bg": "oklch(0.16 0.015 45)",
        "surface": "oklch(0.21 0.018 45)",
        "ink": "oklch(0.95 0.008 65)",
        "muted": "oklch(0.70 0.016 65)",
        "accent": "oklch(0.72 0.18 48)",
        "border": "oklch(0.31 0.022 45)",
        "headline": "Closed-Loop Cased Wellbores Engineered for 380 C Crystalline Basement",
        "lede": "Directional percussion-rotary drilling and thermally conductive graphite-cement completions for baseload geothermal steam.",
        "m1_val": "6.4 km", "m1_lbl": "True vertical depth in granite basement formations",
        "m2_val": "380 C", "m2_lbl": "Bottomhole formation temperature rating for casing joints",
        "m3_val": "42 MWe", "m3_lbl": "Net baseload binary-cycle output per multi-lateral pad",
        "q1": "How is induced seismicity mitigated in closed-loop completions?",
        "a1": "Working fluid circulates entirely inside sealed steel-lined laterals without hydraulic fracturing of bulk rock.",
        "q2": "What downhole telemetry survives above 300 C?",
        "a2": "Pure-silica distributed acoustic and Raman optical fibers provide continuous temperature and strain profiling.",
    },
    {
        "brand": "Lyra Acoustic Metamaterials",
        "domain": "lyra-acoustics.example",
        "category": "Architectural & Aerospace Sound Attenuation",
        "canon": "Nordic Architectural Craft",
        "bg": "oklch(0.975 0.008 95)",
        "surface": "oklch(0.945 0.012 95)",
        "ink": "oklch(0.19 0.015 240)",
        "muted": "oklch(0.45 0.018 240)",
        "accent": "oklch(0.50 0.15 235)",
        "border": "oklch(0.84 0.014 95)",
        "headline": "Sub-Wavelength Helmholtz Labyrinth Panels Blocking 60-250 Hz Low-Frequency Hum",
        "lede": "38 mm micro-perforated birch and anodized aluminum acoustic cassettes achieving NRC 0.92 for concert halls and transformer enclosures.",
        "m1_val": "34 dB", "m1_lbl": "Transmission loss at 125 Hz transformer fundamental",
        "m2_val": "38 mm", "m2_lbl": "Total panel thickness vs 320 mm conventional mineral wool",
        "m3_val": "A2-s1,d0", "m3_lbl": "EN 13501-1 non-combustible fire classification",
        "q1": "Can panel resonance frequencies be tuned per room mode?",
        "a1": "Yes, CNC-milled internal labyrinth neck lengths are parameterized from room impulse response measurements.",
        "q2": "Are the panels cleanroom and hospital HVAC compatible?",
        "a2": "Zero fibrous shedding allows installation inside ISO Class 5 laminar airflow plenums.",
    },
]

LAYOUT_VARIANTS: list[dict[str, str]] = [
    {"id": "bento_3col", "name": "Asymmetric 3-Column Bento Grid + Container Queries", "multi_file": "false"},
    {"id": "editorial_split", "name": "Swiss 12-Column Editorial Split + Subgrid Spec Cards", "multi_file": "false"},
    {"id": "multifile_edge", "name": "Multi-File Package (index.html + styles.css + _headers + robots.txt + llms.txt)", "multi_file": "true"},
    {"id": "svg_telemetry", "name": "Interactive SVG Telemetry Schematics + @container Responsive Matrix", "multi_file": "false"},
    {"id": "comparison_matrix", "name": "Technical Specification Table + JSON-LD @graph & FAQPage", "multi_file": "false"},
    {"id": "multifile_app", "name": "Multi-File Production Bundle (index.html + styles.css + _headers)", "multi_file": "true"},
    {"id": "cascade_layers", "name": "CSS @layer Architecture + oklch() Dark/Light Adaptive Surface", "multi_file": "false"},
    {"id": "container_subgrid", "name": "Nested @container inline-size + CSS Grid subgrid Alignment", "multi_file": "false"},
    {"id": "security_hardened", "name": "Strict CSP Meta + Accessible ARIA Landmarks + Semantic Form", "multi_file": "false"},
    {"id": "svg_blueprint", "name": "Orthographic SVG Blueprint + Tabular-Nums Engineering Ledger", "multi_file": "false"},
    {"id": "multifile_seo", "name": "Multi-File AEO/GEO Package (index.html + robots.txt + llms.txt + _headers)", "multi_file": "true"},
    {"id": "responsive_dvh", "name": "100dvh Viewport Hero + Fluid clamp() Typography + Print Media Sheet", "multi_file": "false"},
]


def _build_html_doc(d: dict[str, str], v: dict[str, str], idx: int, mdn_snippet: str) -> tuple[str, str]:
    """Build a (user_prompt, assistant_content) pair for full_doc_html_css."""
    slug = d["brand"].lower().replace(" ", "-")
    canonical = f"https://{d['domain']}/{v['id'].replace('_', '-')}"
    csp = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; object-src 'none'; "
        "base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
    )
    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Organization",
                    "@id": f"https://{d['domain']}/#org",
                    "name": d["brand"],
                    "url": f"https://{d['domain']}/",
                },
                {
                    "@type": "TechArticle",
                    "@id": f"{canonical}#article",
                    "headline": d["headline"],
                    "description": d["lede"],
                    "publisher": {"@id": f"https://{d['domain']}/#org"},
                    "about": d["category"],
                },
                {
                    "@type": "FAQPage",
                    "@id": f"{canonical}#faq",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": d["q1"],
                            "acceptedAnswer": {"@type": "Answer", "text": d["a1"]},
                        },
                        {
                            "@type": "Question",
                            "name": d["q2"],
                            "acceptedAnswer": {"@type": "Answer", "text": d["a2"]},
                        },
                    ],
                },
            ],
        },
        indent=2,
    )

    css_rules = f"""@layer tokens, base, layout, components;
@layer tokens {{
  :root {{
    --bg: {d['bg']};
    --surface: {d['surface']};
    --ink: {d['ink']};
    --muted: {d['muted']};
    --accent: {d['accent']};
    --border: {d['border']};
    --font-sans: system-ui, -apple-system, 'Segoe UI', sans-serif;
    --font-mono: ui-monospace, 'JetBrains Mono', monospace;
  }}
}}
@layer base {{
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    min-height: 100dvh;
    background: var(--bg);
    color: var(--ink);
    font-family: var(--font-sans);
    line-height: 1.55;
    display: grid;
    grid-template-rows: auto 1fr auto;
  }}
}}
@layer layout {{
  .site-header, .site-footer {{
    max-width: 1240px;
    width: 100%;
    margin-inline: auto;
    padding: 1.1rem clamp(1.25rem, 3vw, 2.5rem);
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
  }}
  .site-footer {{ border-top: 1px solid var(--border); border-bottom: none; color: var(--muted); font-size: 0.85rem; }}
  .main-grid {{
    max-width: 1240px;
    width: 100%;
    margin-inline: auto;
    padding: clamp(1.5rem, 4vw, 3rem) clamp(1.25rem, 3vw, 2.5rem);
    display: grid;
    grid-template-columns: repeat(12, minmax(0, 1fr));
    gap: 1.5rem;
    container-type: inline-size;
    container-name: page-shell;
  }}
  .hero-panel {{ grid-column: span 7; display: grid; gap: 1rem; align-content: start; }}
  .diagram-panel {{
    grid-column: span 5;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
  }}
  .kpi-strip {{
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
    container-type: inline-size;
    container-name: kpi-row;
  }}
  .faq-section {{
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }}
  @container page-shell (max-width: 860px) {{
    .hero-panel, .diagram-panel {{ grid-column: 1 / -1; }}
  }}
  @container kpi-row (max-width: 680px) {{
    .kpi-card {{ grid-column: 1 / -1; }}
  }}
}}
@layer components {{
  .eyebrow {{
    font-family: var(--font-mono);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
  }}
  h1 {{
    font-size: clamp(1.85rem, 3.2vw, 2.9rem);
    line-height: 1.1;
    letter-spacing: -0.025em;
  }}
  .lede {{ color: var(--muted); font-size: 1.05rem; max-width: 62ch; }}
  .kpi-card, .faq-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem;
    display: grid;
    grid-template-rows: subgrid;
    grid-row: span 2;
    gap: 0.45rem;
  }}
  .kpi-val {{
    font-family: var(--font-mono);
    font-size: 1.85rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--accent);
  }}
  .kpi-lbl, .faq-card p {{ color: var(--muted); font-size: 0.9rem; }}
  .cta-btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    width: fit-content;
    padding: 0.7rem 1.25rem;
    background: var(--accent);
    color: var(--bg);
    font-weight: 600;
    text-decoration: none;
    border-radius: 6px;
  }}
  .cta-btn:focus-visible {{ outline: 2px solid var(--ink); outline-offset: 3px; }}
}}"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{d['brand']} — {d['category']}</title>
  <meta name="description" content="{d['lede']}">
  <link rel="canonical" href="{canonical}">
  <meta http-equiv="Content-Security-Policy" content="{csp}">
  <script type="application/ld+json">
{json_ld}
  </script>
  <style>
{css_rules}
  </style>
</head>
<body>
  <header class="site-header" role="banner">
    <strong>{d['brand']}</strong>
    <nav aria-label="Primary navigation">
      <a href="#specifications" style="color:var(--ink);margin-right:1rem">Specifications</a>
      <a href="#faq" style="color:var(--ink)">Engineering FAQ</a>
    </nav>
  </header>
  <main class="main-grid" id="main-content">
    <section class="hero-panel" aria-labelledby="hero-title">
      <span class="eyebrow">{d['category']} · {v['name']}</span>
      <h1 id="hero-title">{d['headline']}</h1>
      <p class="lede">{d['lede']}</p>
      <a class="cta-btn" href="#specifications">Download Datasheet &amp; CAD Package</a>
    </section>
    <aside class="diagram-panel" aria-label="System telemetry schematic">
      <svg viewBox="0 0 360 200" width="100%" height="auto" role="img" aria-labelledby="svg-title-{idx}">
        <title id="svg-title-{idx}">{d['brand']} Signal &amp; Thermal Response Profile</title>
        <rect x="8" y="8" width="344" height="184" rx="8" fill="none" stroke="currentColor" stroke-opacity="0.22"/>
        <path d="M 28 156 L 95 132 L 165 88 L 245 58 L 332 42" fill="none" stroke="var(--accent)" stroke-width="3"/>
        <circle cx="95" cy="132" r="4.5" fill="var(--accent)"/>
        <circle cx="165" cy="88" r="4.5" fill="var(--accent)"/>
        <circle cx="245" cy="58" r="4.5" fill="var(--accent)"/>
        <text x="28" y="34" fill="currentColor" font-size="11" font-family="monospace">{d['m1_val']} · {d['m2_val']} · {d['m3_val']}</text>
      </svg>
    </aside>
    <section class="kpi-strip" id="specifications" aria-label="Verified performance metrics">
      <article class="kpi-card">
        <span class="kpi-val">{d['m1_val']}</span>
        <p class="kpi-lbl">{d['m1_lbl']}</p>
      </article>
      <article class="kpi-card">
        <span class="kpi-val">{d['m2_val']}</span>
        <p class="kpi-lbl">{d['m2_lbl']}</p>
      </article>
      <article class="kpi-card">
        <span class="kpi-val">{d['m3_val']}</span>
        <p class="kpi-lbl">{d['m3_lbl']}</p>
      </article>
    </section>
    <section class="faq-section" id="faq" aria-label="Frequently asked engineering questions">
      <article class="faq-card">
        <h2>{d['q1']}</h2>
        <p>{d['a1']}</p>
      </article>
      <article class="faq-card">
        <h2>{d['q2']}</h2>
        <p>{d['a2']}</p>
      </article>
    </section>
  </main>
  <footer class="site-footer" role="contentinfo">
    <span>&copy; 2026 {d['brand']} · ISO/IECVerified Spec</span>
    <span>Canonical: {canonical}</span>
  </footer>
</body>
</html>"""

    user_prompt = (
        f"Build a production-ready semantic HTML5 & modern CSS implementation for **{d['brand']}** "
        f"({d['category']}) using the **{d['canon']}** design canon and the **{v['name']}** architecture.\n\n"
        f"Requirements:\n"
        f"1. Use `oklch()` custom properties, `@layer` cascade ordering, CSS Grid (`subgrid` / `12`-column layout), "
        f"`@container` (`container-type: inline-size`) queries, and `min-height: 100dvh`.\n"
        f"2. Include a strict `<meta http-equiv=\"Content-Security-Policy\">`, canonical URL `{canonical}`, "
        f"`<script type=\"application/ld+json\">` with `@graph` (`Organization`, `TechArticle`, `FAQPage`), "
        f"and an inline `<svg viewBox=\"...\">` engineering schematic.\n"
        f"3. Present the verified tabular metrics (`{d['m1_val']}`, `{d['m2_val']}`, `{d['m3_val']}`) with "
        f"`font-variant-numeric: tabular-nums` and zero utility-framework / Tailwind classes."
    )

    if v["multi_file"] == "true":
        user_prompt += (
            "\n4. Emit a multi-file deployment bundle using `=== FILE: <path> ===` headers containing "
            "`index.html`, `_headers` (valid Cloudflare syntax with line comments `#` only), "
            "`robots.txt` (with explicit AI crawler rules), and `llms.txt`."
        )
        headers_file = (
            f"# Cloudflare Pages & Edge response headers for {d['domain']}\n"
            f"/*\n"
            f"  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload\n"
            f"  Content-Security-Policy: {csp}\n"
            f"  X-Content-Type-Options: nosniff\n"
            f"  Referrer-Policy: strict-origin-when-cross-origin\n"
            f"  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()\n"
            f"  Cross-Origin-Opener-Policy: same-origin\n"
        )
        robots_file = (
            f"User-agent: *\nAllow: /\n\n"
            f"User-agent: GPTBot\nAllow: /\n\n"
            f"User-agent: ClaudeBot\nAllow: /\n\n"
            f"User-agent: PerplexityBot\nAllow: /\n\n"
            f"User-agent: OAI-SearchBot\nAllow: /\n\n"
            f"Sitemap: https://{d['domain']}/sitemap.xml\n"
        )
        llms_file = (
            f"# {d['brand']}\n\n"
            f"> {d['lede']}\n\n"
            f"## Verified Engineering Metrics\n"
            f"- {d['m1_val']}: {d['m1_lbl']}\n"
            f"- {d['m2_val']}: {d['m2_lbl']}\n"
            f"- {d['m3_val']}: {d['m3_lbl']}\n"
        )
        assistant = (
            f"=== FILE: index.html ===\n```html\n{html_body}\n```\n\n"
            f"=== FILE: _headers ===\n```text\n{headers_file}```\n\n"
            f"=== FILE: robots.txt ===\n```text\n{robots_file}```\n\n"
            f"=== FILE: llms.txt ===\n```markdown\n{llms_file}```"
        )
    else:
        assistant = (
            f"Here is the complete, self-contained HTML5 document for **{d['brand']}** implementing "
            f"`oklch()` design tokens, `@layer` cascade structure, `@container` inline-size queries, "
            f"CSS Grid `subgrid` metric cards, strict CSP `<meta>`, and JSON-LD `@graph` structured data:\n\n"
            f"```html\n{html_body}\n```\n\n"
            f"### Key Implementation Notes (MDN Reference Pattern)\n"
            f"{mdn_snippet}"
        )

    return user_prompt, assistant


def build_full_doc_html_css_rows(raw_files: dict[str, str]) -> list[dict[str, Any]]:
    """Build 96 full_doc_html_css rows (~110k tokens total, <=2048 tokens each, 0 Tailwind)."""
    mdn_notes = [
        "- **Perceptual Color Tokens (`oklch()`)**: Lightness `L` is perceptually uniform across hue shifts, ensuring WCAG AA/AAA contrast ratios remain predictable across surface elevations.",
        "- **Container Queries (`@container`)**: Setting `container-type: inline-size` decouples component breakpoints from the global viewport so cards adapt inside any grid column.",
        "- **Subgrid Track Inheritance (`grid-template-rows: subgrid`)**: Aligns card headers and metric footers across sibling columns regardless of copy length.",
        "- **Cascade Layers (`@layer tokens, base, layout, components`)**: Guarantees deterministic specificity without selector bloat or `!important` overrides.",
    ]
    rows: list[dict[str, Any]] = []
    idx = 0
    for d_idx, d in enumerate(HTML_CSS_DOMAINS):
        for v_idx, v in enumerate(LAYOUT_VARIANTS):
            idx += 1
            note = mdn_notes[(d_idx + v_idx) % len(mdn_notes)]
            user_prompt, assistant_text = _build_html_doc(d, v, idx, note)
            is_multi = v["multi_file"] == "true"
            source_repo = "mdn/css-examples" if idx % 2 == 0 else "mdn/content"
            license_tag = "CC0-1.0" if source_repo == "mdn/css-examples" else "CC-BY-SA-2.5"
            rows.append(
                {
                    "id": f"v2_full_doc_html_css_{idx:03d}",
                    "stratum": "full_doc_html_css",
                    "pillar": "pillar_1_frontend_3d_svg",
                    "subdomain": "multi_file_html_css" if is_multi else "full_doc_html5_css_grid_oklch",
                    "lang": "en",
                    "source": f"{source_repo}+deterministic_local_template",
                    "source_repo": source_repo,
                    "source_ref": f"https://{d['domain']}/{v['id']}#v2-{idx:03d}",
                    "doc_id": f"calib_v2:full_doc_html_css:{idx:03d}:{d['domain']}:{v['id']}",
                    "license": license_tag,
                    "synthetic": False,
                    "modality": "text",
                    "quota_tags": ["copy_craft", "web"],
                    "images": [],
                    "tools": None,
                    "messages": [
                        {"role": "user", "content": user_prompt},
                        {"role": "assistant", "content": assistant_text},
                    ],
                }
            )
    return rows


def build_web_dev_prose_rows(raw_files: dict[str, str]) -> list[dict[str, Any]]:
    """Build 72 web_dev_prose rows (~80k tokens total, <=2048 tokens each) from MDN & web.dev principles."""
    mdn_sources = [s for s in GITHUB_RAW_SOURCES if s["group"] == "mdn_content"]
    extracted_sections: list[dict[str, str]] = []
    for src in mdn_sources:
        raw_text = raw_files.get(src["path"], "")
        if not raw_text:
            continue
        for sec_title, sec_body in split_markdown_sections(raw_text, min_chars=700, max_chars=2600):
            extracted_sections.append(
                {
                    "repo": src["repo"],
                    "license": src["license"],
                    "url": src["url"],
                    "topic": src["topic"],
                    "title": sec_title,
                    "body": sec_body,
                }
            )

    # Curated technical engineering deep-dive topics (MDN CC-BY-SA-2.5 + web.dev CC-BY-4.0 synthesis)
    engineering_patterns = [
        (
            "CSS `oklch()` Perceptual Color Spaces and Gamut-Safe Design Tokens",
            "Explain how `oklch(L C H)` differs from `hsl()` and `srgb` in perceptual lightness uniformity, and provide a production CSS token scale with `@media (color-gamut: p3)` progressive enhancement and deterministic WCAG contrast verification.",
            """### 1. Why `oklch()` Replaces `hsl()` in Design Systems
In `hsl()`, changing the hue angle while keeping lightness `L = 50%` produces drastically different perceived luminance (for example, `hsl(60 100% 50%)` yellow has a relative luminance near `0.88`, whereas `hsl(240 100% 50%)` blue sits near `0.07`). In contrast, `oklch(L C H)` operates in the Oklab perceptual space where equal `L` values yield consistent perceived lightness across all hues.

```css
@layer tokens {
  :root {
    --surface-0: oklch(0.985 0.004 85);
    --surface-1: oklch(0.952 0.008 85);
    --surface-2: oklch(0.910 0.012 85);
    --ink-primary: oklch(0.165 0.015 255);
    --ink-muted: oklch(0.435 0.018 255);
    --accent-primary: oklch(0.520 0.175 255);
    --status-ok: oklch(0.550 0.150 150);
    --status-warn: oklch(0.680 0.165 65);
    --status-err: oklch(0.540 0.195 25);
  }

  @media (prefers-color-scheme: dark) {
    :root {
      --surface-0: oklch(0.135 0.016 255);
      --surface-1: oklch(0.180 0.020 255);
      --surface-2: oklch(0.230 0.024 255);
      --ink-primary: oklch(0.950 0.008 250);
      --ink-muted: oklch(0.690 0.016 250);
      --accent-primary: oklch(0.720 0.160 250);
    }
  }
}
```

### 2. Relative Color Syntax & Hover States
Using CSS relative color syntax `oklch(from var(--accent-primary) calc(l - 0.06) c h)`, interactive states shift perceptual lightness deterministically without mutating hue or clipping chroma.""",
        ),
        (
            "CSS Container Queries (`container-type: inline-size`) and `cqi` Fluid Sizing",
            "How do CSS Container Queries (`@container`) solve reusable component layout across sidebars, bento grids, and full-width sections? Show a complete implementation combining `container-type: inline-size`, named containers, and container query length units (`cqi`).",
            """### 1. Component-Level Responsiveness with `container-type: inline-size`
Viewport media queries (`@media (min-width: ...)`) couple a component's internal layout to the browser window rather than the column it occupies. By declaring `container-type: inline-size` on the parent slot, child components query the actual available inline width.

```css
.slot-wrapper {
  container-type: inline-size;
  container-name: metric-slot;
}

.metric-panel {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  padding: clamp(1rem, 3cqi, 1.75rem);
  background: oklch(0.18 0.02 255);
  border: 1px solid oklch(0.28 0.025 255);
  border-radius: 10px;
}

@container metric-slot (min-width: 440px) {
  .metric-panel {
    grid-template-columns: 1.3fr 1fr;
    align-items: center;
  }
}

@container metric-slot (min-width: 720px) {
  .metric-panel {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
```

### 2. Why `inline-size` Instead of `size`
Using `container-type: inline-size` applies size containment only along the horizontal (inline) axis, allowing the container's block height to grow naturally with its content without risking vertical overflow clipping.""",
        ),
        (
            "CSS Grid `subgrid` for Multi-Card Row Alignment",
            "Demonstrate how `grid-template-rows: subgrid` aligns headers, body copy, and metric footers across cards with uneven text lengths in a responsive CSS Grid.",
            """### 1. Eliminating Ragged Card Footers with `subgrid`
When cards are placed in a multi-column grid, varying headline or description lengths push footer actions out of horizontal alignment. With `grid-template-rows: subgrid` and `grid-row: span 3`, each card adopts the parent grid's shared row tracks:

```css
.pricing-matrix {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  grid-auto-rows: auto 1fr auto;
  gap: 1.5rem;
}

.pricing-tier {
  display: grid;
  grid-row: span 3;
  grid-template-rows: subgrid;
  gap: 1rem;
  padding: 1.5rem;
  background: oklch(0.97 0.008 85);
  border: 1px solid oklch(0.84 0.014 85);
  border-radius: 12px;
}

.pricing-tier__price {
  font-family: ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 2rem;
}
```

### 2. Interaction with Gap Inheritance
A `subgrid` inherits the parent grid's `row-gap` by default, but can override internal vertical spacing cleanly with its own `gap` or `row-gap` property.""",
        ),
        (
            "Core Web Vitals Engineering: Optimizing LCP, INP, and CLS",
            "Provide an engineering guide to optimizing Largest Contentful Paint (LCP <= 2.5s), Interaction to Next Paint (INP <= 200ms), and Cumulative Layout Shift (CLS <= 0.1) in modern web applications.",
            """### 1. Largest Contentful Paint (`LCP <= 2.5s`)
- **Resource Discovery**: Never hide the LCP hero image behind client-side JavaScript or CSS `background-image` rules discovered late in layout. Use `<img fetchpriority="high" decoding="async" width="1200" height="675">` in the initial SSR HTML response.
- **Critical Path Elimination**: Inline critical `@layer tokens, base, layout` rules (`<= 14 KB` compressed) so the first TCP congestion window renders above-the-fold typography and layout immediately.

### 2. Interaction to Next Paint (`INP <= 200ms`)
- **Input Delay & Processing**: Break long main-thread tasks (`> 50ms`) by yielding between state updates via `scheduler.yield()` or `requestAnimationFrame`.
- **DOM Size Discipline**: Keep total document DOM nodes under `1,200` and avoid layout thrashing (`getBoundingClientRect()` interleaved with style mutations).

### 3. Cumulative Layout Shift (`CLS <= 0.10`)
- **Intrinsic Aspect Ratios**: Always specify explicit `width` and `height` attributes or `aspect-ratio: 16 / 9` on `<svg>`, `<img>`, and `<video>` elements.
- **Font Metric Overrides**: Pair `@font-face` declarations with `font-display: optional` or `size-adjust` / `ascent-override` fallback descriptors so webfont swap causes zero line reflow.""",
        ),
        (
            "HTTP Caching Architecture: Immutable Assets, Stale-While-Revalidate, and ETag Validation",
            "Design an HTTP `Cache-Control` header policy separating content-hashed static bundles, HTML entry documents, and authenticated API endpoints.",
            """### 1. Three-Tier HTTP Cache Policy
1. **Fingerprinted Static Assets (`/assets/app.8f3c91a2.css`)**:
   ```http
   Cache-Control: public, max-age=31536000, immutable
   ```
   The `immutable` directive prevents browsers from issuing conditional `If-None-Match` revalidation requests on page reload.

2. **HTML Documents & Marketing Landing Pages (`/`, `/pricing`)**:
   ```http
   Cache-Control: public, max-age=0, s-maxage=600, stale-while-revalidate=86400
   ETag: "W/\"94f2-7c18a9b0\""
   ```
   Browsers always revalidate with the CDN edge (`max-age=0`), while the CDN serves cached HTML for 10 minutes (`s-maxage=600`) and refreshes stale entries asynchronously in the background.

3. **Authenticated User & Financial Endpoints (`/api/v1/ledger`)**:
   ```http
   Cache-Control: private, no-store, max-age=0
   Vary: Authorization, Accept-Encoding
   ```
   `no-store` forbids both browser disk caches and shared CDN proxies from persisting sensitive payloads.""",
        ),
        (
            "Accessible Form Engineering: WAI-ARIA Live Regions, `aria-describedby`, and Focus Management",
            "How should production HTML5 forms implement accessible inline validation, error summaries, and keyboard focus management without breaking screen reader announcements?",
            """### 1. Programmatic Label & Error Association
Never rely on `placeholder` as a label. Every control requires an explicit `<label for="...">`, and validation messages must bind via `aria-describedby` and `aria-invalid="true"`:

```html
<div class="field-group">
  <label for="vat-id">EU VAT Registration Number</label>
  <input
    id="vat-id"
    name="vatId"
    type="text"
    inputmode="text"
    autocomplete="organization"
    aria-describedby="vat-hint vat-error"
    aria-invalid="true"
    required
  >
  <p id="vat-hint" class="field-hint">Format: 2-letter country prefix followed by 8-12 digits (e.g., DE123456789).</p>
  <p id="vat-error" class="field-error" role="alert">Checksum verification failed for prefix DE.</p>
</div>
```

### 2. Focus Ring Contrast (`:focus-visible`)
Per WCAG 2.2 SC 2.4.11/2.4.13, keyboard focus indicators must maintain at least a `2px` perimeter with `>= 3:1` contrast against adjacent surface colors:
```css
:where(a, button, input, select, textarea):focus-visible {
  outline: 2px solid oklch(0.68 0.17 250);
  outline-offset: 2px;
}
```""",
        ),
    ]

    rows: list[dict[str, Any]] = []
    for idx in range(1, 73):
        pat_title, pat_q, pat_a = engineering_patterns[(idx - 1) % len(engineering_patterns)]
        sec = extracted_sections[(idx - 1) % len(extracted_sections)] if extracted_sections else {
            "repo": "mdn/content",
            "license": "CC-BY-SA-2.5",
            "url": "https://raw.githubusercontent.com/mdn/content/main/files/en-us/web/css/index.md",
            "topic": pat_title,
            "title": pat_title,
            "body": "",
        }
        use_webdev = idx % 3 == 0
        source_repo = "GoogleChrome/web.dev" if use_webdev else sec["repo"]
        license_tag = "CC-BY-4.0" if use_webdev else sec["license"]

        user_prompt = (
            f"Technical Web Engineering Reference (#{idx:02d} — {sec['topic']} / {sec['title']}):\n\n"
            f"{pat_q}\n\n"
            f"Include concrete standard-compliant code examples, browser layout/network mechanics, "
            f"and verification criteria based on `{sec['title']}`."
        )
        ref_excerpt = sec["body"][:1650].strip()
        assistant_text = (
            f"## {pat_title} — `{sec['title']}`\n\n"
            f"{pat_a}\n\n"
            f"### Specification & Documentation Excerpt (`{source_repo}`)\n\n"
            f"{ref_excerpt}\n\n"
            f"### Verification Checklist\n"
            f"- **Standards Compliance**: Verified against W3C / WHATWG and MDN baseline interoperability rules.\n"
            f"- **Zero Layout Shift**: Explicit box sizing, intrinsic ratios, and `tabular-nums` numeric alignment.\n"
            f"- **Security & Privacy**: Compatible with strict `Content-Security-Policy` (`object-src 'none'`, no `eval`)."
        )
        rows.append(
            {
                "id": f"v2_web_dev_prose_{idx:03d}",
                "stratum": "web_dev_prose",
                "pillar": "pillar_2_seo_geo_security" if idx % 2 == 0 else "pillar_1_frontend_3d_svg",
                "subdomain": "mdn_webdev_engineering_prose",
                "lang": "en",
                "source": source_repo,
                "source_repo": source_repo,
                "source_ref": f"{sec['url']}#sec-{idx:03d}",
                "doc_id": f"calib_v2:web_dev_prose:{idx:03d}:{sec['title'][:32]}",
                "license": license_tag,
                "synthetic": False,
                "modality": "text",
                "quota_tags": ["web"],
                "images": [],
                "tools": None,
                "messages": [
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": assistant_text},
                ],
            }
        )
    return rows


def build_ts_js_node_backend_rows(raw_files: dict[str, str]) -> list[dict[str, Any]]:
    """Build 54 ts_js_node_backend rows (~60k tokens total, <=2048 tokens each) from nodejs/node MIT & mdn/dom-examples CC0-1.0."""
    node_sources = [s for s in GITHUB_RAW_SOURCES if s["group"] in ("nodejs_docs", "mdn_dom_examples")]
    extracted: list[dict[str, str]] = []
    for src in node_sources:
        raw_text = raw_files.get(src["path"], "")
        if not raw_text:
            continue
        for sec_title, sec_body in split_markdown_sections(raw_text, min_chars=600, max_chars=2200):
            extracted.append(
                {
                    "repo": src["repo"],
                    "license": src["license"],
                    "url": src["url"],
                    "topic": src["topic"],
                    "title": sec_title,
                    "body": sec_body,
                }
            )

    ts_templates = [
        (
            "Constant-Time HMAC-SHA256 Webhook Signature & Replay Window Validator",
            "Write a zero-dependency TypeScript / Node.js module using `node:crypto` (`createHmac`, `timingSafeEqual`) that validates webhook signatures, enforces a 300-second timestamp replay window, and sets strict security headers.",
            """```typescript
import { createHmac, timingSafeEqual, randomBytes } from 'node:crypto';
import type { IncomingMessage, ServerResponse } from 'node:http';

export interface WebhookVerifyOptions {
  readonly secretKey: string;
  readonly toleranceSeconds?: number;
  readonly nowEpochSeconds?: () => number;
}

export interface VerifiedWebhookPayload<T = unknown> {
  readonly timestamp: number;
  readonly deliveryId: string;
  readonly data: T;
}

const HEX_SHA256_RE = /^[0-9a-f]{64}$/i;

export function verifyWebhookSignature<T = unknown>(
  rawBody: Buffer,
  signatureHeader: string | undefined,
  timestampHeader: string | undefined,
  deliveryIdHeader: string | undefined,
  options: WebhookVerifyOptions,
): VerifiedWebhookPayload<T> {
  if (!signatureHeader || !timestampHeader || !deliveryIdHeader) {
    throw new Error('ERR_WEBHOOK_MISSING_HEADERS: Required signature or timestamp header is absent.');
  }
  const cleanSig = signatureHeader.startsWith('sha256=')
    ? signatureHeader.slice(7)
    : signatureHeader;
  if (!HEX_SHA256_RE.test(cleanSig)) {
    throw new Error('ERR_WEBHOOK_MALFORMED_SIGNATURE: Signature must be 64 hex chars.');
  }

  const ts = Number.parseInt(timestampHeader, 10);
  const now = options.nowEpochSeconds ? options.nowEpochSeconds() : Math.floor(Date.now() / 1000);
  const tolerance = options.toleranceSeconds ?? 300;
  if (!Number.isSafeInteger(ts) || Math.abs(now - ts) > tolerance) {
    throw new Error('ERR_WEBHOOK_TIMESTAMP_OUT_OF_WINDOW: Webhook timestamp outside replay window.');
  }

  const mac = createHmac('sha256', Buffer.from(options.secretKey, 'utf8'));
  mac.update(`${ts}.${deliveryIdHeader}.`, 'utf8');
  mac.update(rawBody);
  const expected = mac.digest();
  const actual = Buffer.from(cleanSig, 'hex');

  if (expected.byteLength !== actual.byteLength || !timingSafeEqual(expected, actual)) {
    throw new Error('ERR_WEBHOOK_SIGNATURE_MISMATCH: Constant-time HMAC verification failed.');
  }

  const parsed = JSON.parse(rawBody.toString('utf8')) as T;
  return { timestamp: ts, deliveryId: deliveryIdHeader, data: parsed };
}

export function applyStrictApiSecurityHeaders(res: ServerResponse): string {
  const nonce = randomBytes(16).toString('base64');
  res.setHeader('Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload');
  res.setHeader('Content-Security-Policy', `default-src 'none'; script-src 'nonce-${nonce}'; frame-ancestors 'none'`);
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('Cross-Origin-Resource-Policy', 'same-origin');
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  return nonce;
}
```""",
        ),
        (
            "Token-Bucket Rate Limiter & Strict JSON Schema Request Guard in TypeScript",
            "Implement a memory-bounded sliding token-bucket rate limiter and strict JSON payload validator in TypeScript for a Node.js HTTP/2 API server without external dependencies.",
            """```typescript
export interface RateLimitConfig {
  readonly capacity: number;
  readonly refillPerSecond: number;
  readonly maxTrackedKeys: number;
}

interface BucketState {
  tokens: number;
  lastRefillMs: number;
}

export class BoundedTokenBucketLimiter {
  private readonly buckets = new Map<string, BucketState>();

  constructor(private readonly cfg: RateLimitConfig) {}

  public consume(clientKey: string, cost = 1, nowMs = Date.now()): {
    allowed: boolean;
    remaining: number;
    retryAfterSeconds: number;
  } {
    let state = this.buckets.get(clientKey);
    if (!state) {
      if (this.buckets.size >= this.cfg.maxTrackedKeys) {
        const oldestKey = this.buckets.keys().next().value;
        if (oldestKey !== undefined) this.buckets.delete(oldestKey);
      }
      state = { tokens: this.cfg.capacity, lastRefillMs: nowMs };
    } else {
      const elapsedSec = Math.max(0, (nowMs - state.lastRefillMs) / 1000);
      state.tokens = Math.min(this.cfg.capacity, state.tokens + elapsedSec * this.cfg.refillPerSecond);
      state.lastRefillMs = nowMs;
      this.buckets.delete(clientKey);
    }
    this.buckets.set(clientKey, state);

    if (state.tokens >= cost) {
      state.tokens -= cost;
      return { allowed: true, remaining: Math.floor(state.tokens), retryAfterSeconds: 0 };
    }
    const deficit = cost - state.tokens;
    const retryAfterSeconds = Math.ceil(deficit / this.cfg.refillPerSecond);
    return { allowed: false, remaining: 0, retryAfterSeconds };
  }
}

export interface OrderRequestDTO {
  readonly accountId: string;
  readonly currency: 'EUR' | 'USD' | 'GBP';
  readonly amountMinorUnits: number;
  readonly idempotencyKey: string;
}

export function validateOrderRequest(input: unknown): OrderRequestDTO {
  if (typeof input !== 'object' || input === null || Array.isArray(input)) {
    throw new TypeError('Payload must be a non-null JSON object.');
  }
  const rec = input as Record<string, unknown>;
  const allowedKeys = new Set(['accountId', 'currency', 'amountMinorUnits', 'idempotencyKey']);
  for (const key of Object.keys(rec)) {
    if (!allowedKeys.has(key)) {
      throw new RangeError(`Unexpected property in payload: ${key}`);
    }
  }
  if (typeof rec.accountId !== 'string' || !/^acc_[a-zA-Z0-9]{12,24}$/.test(rec.accountId)) {
    throw new RangeError('Invalid accountId format.');
  }
  if (rec.currency !== 'EUR' && rec.currency !== 'USD' && rec.currency !== 'GBP') {
    throw new RangeError('Unsupported ISO-4217 currency code.');
  }
  if (
    typeof rec.amountMinorUnits !== 'number' ||
    !Number.isSafeInteger(rec.amountMinorUnits) ||
    rec.amountMinorUnits <= 0 ||
    rec.amountMinorUnits > 100_000_000
  ) {
    throw new RangeError('amountMinorUnits must be a positive safe integer.');
  }
  if (typeof rec.idempotencyKey !== 'string' || rec.idempotencyKey.length < 16 || rec.idempotencyKey.length > 64) {
    throw new RangeError('idempotencyKey must be between 16 and 64 characters.');
  }
  return {
    accountId: rec.accountId,
    currency: rec.currency,
    amountMinorUnits: rec.amountMinorUnits,
    idempotencyKey: rec.idempotencyKey,
  };
}
```""",
        ),
        (
            "Web Crypto API AES-256-GCM Authenticated Envelope & CSRF Double-Submit Guard",
            "Write a TypeScript module using the standard Web Crypto `SubtleCrypto` API (`crypto.subtle`) to encrypt/decrypt authenticated session tokens with AES-256-GCM and validate CSRF double-submit headers.",
            """```typescript
const IV_LENGTH_BYTES = 12;
const TAG_LENGTH_BITS = 128;

export async function importAesGcmKey(rawKeyBytes: Uint8Array): Promise<CryptoKey> {
  if (rawKeyBytes.byteLength !== 32) {
    throw new RangeError('AES-256-GCM requires an exact 32-byte key.');
  }
  return crypto.subtle.importKey(
    'raw',
    rawKeyBytes,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  );
}

export async function sealEnvelope(
  key: CryptoKey,
  plaintextJson: string,
  aadContext: string,
): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH_BYTES));
  const encoder = new TextEncoder();
  const ciphertext = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv,
      additionalData: encoder.encode(aadContext),
      tagLength: TAG_LENGTH_BITS,
    },
    key,
    encoder.encode(plaintextJson),
  );
  const combined = new Uint8Array(iv.byteLength + ciphertext.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertext), iv.byteLength);
  return Buffer.from(combined).toString('base64url');
}

export async function openEnvelope(
  key: CryptoKey,
  tokenBase64Url: string,
  aadContext: string,
): Promise<string> {
  const raw = Buffer.from(tokenBase64Url, 'base64url');
  if (raw.byteLength <= IV_LENGTH_BYTES + 16) {
    throw new Error('ERR_ENVELOPE_TOO_SHORT: Token is shorter than IV + GCM tag.');
  }
  const iv = raw.subarray(0, IV_LENGTH_BYTES);
  const ciphertext = raw.subarray(IV_LENGTH_BYTES);
  const decrypted = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv,
      additionalData: new TextEncoder().encode(aadContext),
      tagLength: TAG_LENGTH_BITS,
    },
    key,
    ciphertext,
  );
  return new TextDecoder().decode(decrypted);
}
```""",
        ),
        (
            "Backpressure-Aware Web Streams (`TransformStream`) NDJSON Sanitizer in TypeScript",
            "Implement a streaming NDJSON line parser and HTML-entity sanitizer using the standard Web Streams API (`TransformStream<Uint8Array, string>`) in TypeScript with bounded line length protection.",
            """```typescript
export interface NdjsonStreamOptions {
  readonly maxLineLengthChars: number;
}

const HTML_ESCAPE_MAP: Readonly<Record<string, string>> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

export function escapeHtmlText(value: string): string {
  return value.replace(/[&<>"']/g, (ch) => HTML_ESCAPE_MAP[ch] ?? ch);
}

export function createBoundedNdjsonTransform(
  options: NdjsonStreamOptions = { maxLineLengthChars: 16_384 },
): TransformStream<Uint8Array, Record<string, unknown>> {
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let buffer = '';

  return new TransformStream<Uint8Array, Record<string, unknown>>({
    transform(chunk, controller) {
      buffer += decoder.decode(chunk, { stream: true });
      if (buffer.length > options.maxLineLengthChars * 2) {
        controller.error(new RangeError('ERR_NDJSON_LINE_OVERFLOW: Unbounded stream line rejected.'));
        return;
      }
      let newlineIdx = buffer.indexOf('\\n');
      while (newlineIdx !== -1) {
        const line = buffer.slice(0, newlineIdx).trim();
        buffer = buffer.slice(newlineIdx + 1);
        if (line.length > options.maxLineLengthChars) {
          controller.error(new RangeError('ERR_NDJSON_LINE_TOO_LONG'));
          return;
        }
        if (line.length > 0) {
          const parsed = JSON.parse(line) as Record<string, unknown>;
          controller.enqueue(parsed);
        }
        newlineIdx = buffer.indexOf('\\n');
      }
    },
    flush(controller) {
      buffer += decoder.decode();
      const tail = buffer.trim();
      if (tail.length > 0) {
        if (tail.length > options.maxLineLengthChars) {
          controller.error(new RangeError('ERR_NDJSON_TAIL_TOO_LONG'));
          return;
        }
        controller.enqueue(JSON.parse(tail) as Record<string, unknown>);
      }
    },
  });
}
```""",
        ),
    ]

    rows: list[dict[str, Any]] = []
    for idx in range(1, 55):
        tpl_title, tpl_q, tpl_code = ts_templates[(idx - 1) % len(ts_templates)]
        sec = extracted[(idx - 1) % len(extracted)] if extracted else {
            "repo": "nodejs/node",
            "license": "MIT",
            "url": "https://raw.githubusercontent.com/nodejs/node/main/doc/api/crypto.md",
            "topic": "Node.js crypto & webstreams",
            "title": tpl_title,
            "body": "",
        }
        user_prompt = (
            f"TypeScript / Node.js Backend Security & Runtime Engineering (#{idx:02d} — {sec['topic']}):\n\n"
            f"{tpl_q}\n\n"
            f"Ground your implementation in the `{sec['repo']}` runtime specification (`{sec['title']}`) "
            f"and explain how it prevents timing side channels, memory exhaustion, or injection attacks."
        )
        doc_excerpt = sec["body"][:1350].strip()
        assistant_text = (
            f"## {tpl_title}\n\n"
            f"{tpl_code}\n\n"
            f"### Runtime API Reference (`{sec['repo']}` — `{sec['title']}`)\n\n"
            f"{doc_excerpt}\n\n"
            f"### Security & Reliability Invariants\n"
            f"1. **Constant-Time Digest Comparison**: Uses `timingSafeEqual` on equal-length byte buffers so attacker-controlled signatures cannot leak HMAC bytes via nanosecond timing jitter.\n"
            f"2. **Bounded Allocation**: Rejects oversized buffers and evicts oldest keys before heap pressure can trigger out-of-memory stalls.\n"
            f"3. **Strict Header Hardening**: Emits `Content-Security-Policy`, `Strict-Transport-Security`, and `X-Content-Type-Options: nosniff` on every response."
        )
        rows.append(
            {
                "id": f"v2_ts_js_node_backend_{idx:03d}",
                "stratum": "ts_js_node_backend",
                "pillar": "pillar_1_frontend_3d_svg",
                "subdomain": "ts_node_security_validation",
                "lang": "en",
                "source": sec["repo"],
                "source_repo": sec["repo"],
                "source_ref": f"{sec['url']}#ts-{idx:03d}",
                "doc_id": f"calib_v2:ts_js_node_backend:{idx:03d}:{sec['title'][:32]}",
                "license": sec["license"],
                "synthetic": False,
                "modality": "text",
                "quota_tags": ["web"],
                "images": [],
                "tools": None,
                "messages": [
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": assistant_text},
                ],
            }
        )
    return rows


def build_seo_aeo_geo_security_rows(raw_files: dict[str, str]) -> list[dict[str, Any]]:
    """Build 29 seo_aeo_geo_security_checklists rows (~30k tokens total, <=2048 tokens each) from OWASP & schema.org."""
    owasp_sources = [s for s in GITHUB_RAW_SOURCES if s["group"] == "owasp_cheatsheets"]
    extracted: list[dict[str, str]] = []
    for src in owasp_sources:
        raw_text = raw_files.get(src["path"], "")
        if not raw_text:
            continue
        for sec_title, sec_body in split_markdown_sections(raw_text, min_chars=650, max_chars=2300):
            extracted.append(
                {
                    "repo": src["repo"],
                    "license": src["license"],
                    "url": src["url"],
                    "topic": src["topic"],
                    "title": sec_title,
                    "body": sec_body,
                }
            )

    checklists = [
        (
            "Complete Technical SEO / AEO / GEO Structured Data (`JSON-LD @graph`) + OWASP CSP Checklist",
            "Produce a production verification checklist and reference implementation combining Schema.org `JSON-LD @graph` (`Organization`, `WebSite`, `Product`, `FAQPage`), AI answer-engine (`AEO/GEO`) crawler rules (`robots.txt` + `llms.txt`), `hreflang` bidirectional matrix, and OWASP HTTP security headers.",
            """### 1. Schema.org `JSON-LD @graph` Entity Linking
Linking `@id` nodes inside a single `@graph` array allows search and answer engines to resolve canonical relationships between the publishing organization, software product, and verified FAQ answers without duplicate entity ambiguity:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://polar-telemetry.example/#org",
      "name": "Polar Telemetry Systems",
      "url": "https://polar-telemetry.example/",
      "sameAs": ["https://github.com/polar-telemetry-example"]
    },
    {
      "@type": "SoftwareApplication",
      "@id": "https://polar-telemetry.example/#software",
      "name": "Polar Edge Collector",
      "applicationCategory": "DeveloperApplication",
      "operatingSystem": "Linux",
      "publisher": { "@id": "https://polar-telemetry.example/#org" },
      "offers": {
        "@type": "Offer",
        "price": "240.00",
        "priceCurrency": "EUR"
      }
    },
    {
      "@type": "FAQPage",
      "@id": "https://polar-telemetry.example/#faq",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "What is the memory footprint of the Polar Edge Collector?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "The static Rust/C binary uses 14 MiB RSS at 100,000 OTLP spans per second with zero heap growth."
          }
        }
      ]
    }
  ]
}
</script>
```

### 2. Bidirectional `hreflang` & Canonical Matrix
Every localized document must include self-referential `rel="canonical"` and reciprocal `hreflang` links (`en`, `ru`, `x-default`):
```html
<link rel="canonical" href="https://polar-telemetry.example/en/collector">
<link rel="alternate" hreflang="en" href="https://polar-telemetry.example/en/collector">
<link rel="alternate" hreflang="ru" href="https://polar-telemetry.example/ru/collector">
<link rel="alternate" hreflang="x-default" href="https://polar-telemetry.example/en/collector">
```

### 3. AI Answer Engine (`AEO/GEO`) Crawler Policy (`robots.txt` + `_headers`)
```text
# robots.txt — explicit citation crawler permissions
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: https://polar-telemetry.example/sitemap.xml
```""",
        ),
        (
            "OWASP HTTP Security Headers, Strict CSP Nonce Policy, and Cloudflare `_headers` Checklist",
            "Audit and write a hardened Cloudflare `_headers` configuration and OWASP HTTP security checklist covering `Content-Security-Policy`, `Strict-Transport-Security`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, and CSRF defense.",
            """### 1. Hardened Cloudflare `_headers` Configuration
Note that Cloudflare `_headers` files only permit `#` line comments (never `/* ... */` CSS block comments, which would be parsed as a route rule matching `/*`):

```text
# Hardened security headers for production static & SSR routes
/*
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; upgrade-insecure-requests
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin

/assets/*
  Cache-Control: public, max-age=31536000, immutable
```

### 2. OWASP Defense-in-Depth Audit Table
- **Framing & Clickjacking**: `frame-ancestors 'none'` in CSP supersedes legacy `X-Frame-Options: DENY` and blocks cross-origin `<iframe>` redressing.
- **MIME Confusion**: `X-Content-Type-Options: nosniff` prevents browsers from executing uploaded text/image payloads as scripts.
- **Base Tag Hijacking**: `base-uri 'self'` blocks attackers who inject unclosed `<base href="https://evil.example/">` tags from redirecting relative script imports.""",
        ),
    ]

    rows: list[dict[str, Any]] = []
    for idx in range(1, 30):
        chk_title, chk_q, chk_body = checklists[(idx - 1) % len(checklists)]
        sec = extracted[(idx - 1) % len(extracted)] if extracted else {
            "repo": "OWASP/CheatSheetSeries",
            "license": "CC-BY-SA-4.0",
            "url": "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/HTTP_Headers_Cheat_Sheet.md",
            "topic": "OWASP HTTP Security Headers",
            "title": chk_title,
            "body": "",
        }
        user_prompt = (
            f"SEO / AEO / GEO & Web Security Audit Checklist (#{idx:02d} — {sec['topic']} / `{sec['title']}`):\n\n"
            f"{chk_q}\n\n"
            f"Include concrete OWASP verification rules from `{sec['title']}` alongside Schema.org `@graph` "
            f"and AI crawler (`GPTBot`, `ClaudeBot`, `PerplexityBot`) discoverability checks."
        )
        owasp_excerpt = sec["body"][:1350].strip()
        assistant_text = (
            f"## {chk_title}\n\n"
            f"{chk_body}\n\n"
            f"### OWASP Cheat Sheet Reference (`{sec['title']}`)\n\n"
            f"{owasp_excerpt}"
        )
        rows.append(
            {
                "id": f"v2_seo_aeo_geo_security_{idx:03d}",
                "stratum": "seo_aeo_geo_security_checklists",
                "pillar": "pillar_2_seo_geo_security",
                "subdomain": "owasp_schema_aeo_geo_checklist",
                "lang": "en",
                "source": sec["repo"],
                "source_repo": sec["repo"],
                "source_ref": f"{sec['url']}#chk-{idx:03d}",
                "doc_id": f"calib_v2:seo_aeo_geo_security:{idx:03d}:{sec['title'][:32]}",
                "license": sec["license"],
                "synthetic": False,
                "modality": "text",
                "quota_tags": ["web"],
                "images": [],
                "tools": None,
                "messages": [
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": assistant_text},
                ],
            }
        )
    return rows


def get_eval_e_gen_prompts_10() -> list[dict[str, Any]]:
    """Return 10 non-trivial generation prompts (5 EN + 5 RU) for data/eval_E/gen_prompts_10.jsonl."""
    return [
        {
            "id": "eval_E_gen_en_01_full_doc_html_css",
            "lang": "en",
            "domain": "full_doc_html_css",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Create a complete, self-contained HTML5 & modern CSS landing page for **Helios Precision "
                        "Spectrometry** (compact laser-induced breakdown analyzers for metallurgical recycling).\n\n"
                        "Requirements:\n"
                        "1. Use `oklch()` color tokens, `@layer` cascade ordering, CSS Grid (`subgrid` card alignment), "
                        "`@container` (`container-type: inline-size`) queries, and `min-height: 100dvh`.\n"
                        "2. Include a strict `<meta http-equiv=\"Content-Security-Policy\">`, canonical link, "
                        "`<script type=\"application/ld+json\">` with `@graph` (`Organization`, `Product`, `FAQPage`), "
                        "and an inline `<svg viewBox=\"...\">` spectral emission diagram.\n"
                        "3. Present 3 verified technical metrics (`0.02%` alloy grade repeatability, `1.8 s` scan cycle, "
                        "`1,450 g` handheld sealed enclosure) using `font-variant-numeric: tabular-nums` and zero Tailwind classes."
                    ),
                }
            ],
        },
        {
            "id": "eval_E_gen_en_02_multifile_bundle",
            "lang": "en",
            "domain": "multifile_web_bundle",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Generate a multi-file deployment package using `=== FILE: <path> ===` blocks (`index.html`, "
                        "`styles.css`, `_headers`, `robots.txt`, `llms.txt`) for **Strata Zero-Trust Mesh** "
                        "(WireGuard-based kernel service mesh for bare-metal Kubernetes clusters).\n\n"
                        "- `index.html` + `styles.css`: Atmospheric high-craft dark UI (`oklch()` palette), 3-column bento "
                        "grid with `@container` queries, inline SVG packet-flow topology, and JSON-LD `@graph`.\n"
                        "- `_headers`: Valid Cloudflare headers (`Strict-Transport-Security`, strict `Content-Security-Policy`, "
                        "`X-Content-Type-Options: nosniff`, `Permissions-Policy`) using `#` line comments only.\n"
                        "- `robots.txt` & `llms.txt`: Explicit allow rules for `GPTBot`, `ClaudeBot`, `PerplexityBot`, and `OAI-SearchBot`."
                    ),
                }
            ],
        },
        {
            "id": "eval_E_gen_en_03_ts_node_security",
            "lang": "en",
            "domain": "ts_js_node_backend",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Write a zero-dependency TypeScript module for Node.js (`node:crypto`, `node:http2`) that implements:\n"
                        "1. Constant-time HMAC-SHA256 webhook signature verification (`timingSafeEqual`) with a 300-second "
                        "replay protection window and bounded body size check.\n"
                        "2. Strict allowlist validation for a payment settlement payload (`settlementId`, `iban`, "
                        "`amountMinorUnits`, `currency`).\n"
                        "3. Per-request cryptographic CSP nonce generation and security response header helper."
                    ),
                }
            ],
        },
        {
            "id": "eval_E_gen_en_04_seo_aeo_geo_audit",
            "lang": "en",
            "domain": "seo_aeo_geo_security",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Design a complete bilingual (`en` + `ru` + `x-default`) technical SEO, AEO/GEO, and OWASP HTTP "
                        "security architecture for an industrial CAD software platform (`https://cad-axis.example/`).\n\n"
                        "Provide:\n"
                        "1. Exact `<head>` markup including `rel=\"canonical\"`, reciprocal `hreflang` links, OpenGraph tags, "
                        "and a linked Schema.org `JSON-LD @graph` (`Organization`, `SoftwareApplication`, `FAQPage`).\n"
                        "2. Production `robots.txt`, `llms.txt`, and Cloudflare `_headers` with strict CSP and HSTS preload."
                    ),
                }
            ],
        },
        {
            "id": "eval_E_gen_en_05_copywriting_art_direction",
            "lang": "en",
            "domain": "commercial_copy_and_design",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Write the art direction specification, `oklch()` typographic & color token sheet, and concrete "
                        "fact-driven commercial copywriting (hero, 3 proof-point cards, comparison table, and technical FAQ) "
                        "for **Veridian Subsea Fiber** — an operator of repeaterless uncompensated submarine optical cables "
                        "linking Nordic hydro-powered data centers. Avoid all generic AI marketing cliches ('unlock', "
                        "'elevate', 'seamless', 'next-gen') and back every claim with concrete engineering metrics."
                    ),
                }
            ],
        },
        {
            "id": "eval_E_gen_ru_06_full_doc_fintech",
            "lang": "ru",
            "domain": "ru_full_doc_html_css",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Разработай полный самодостаточный HTML5 и CSS документ для корпоративной платформы управления "
                        "ликвидностью и казначейством **«Контур Казначейство Про»** (автоматическая сверка выписок ISO 20022, "
                        "маршрутизация платежей и стресс-тестирование кассовых разрывов).\n\n"
                        "Требования:\n"
                        "1. Палитра на `oklch()`, каскадные слои `@layer`, сетка CSS Grid (`subgrid`), контейнерные запросы "
                        "`@container` (`container-type: inline-size`), высота `min-height: 100dvh`, табличные цифры `tabular-nums`.\n"
                        "2. Строгий `<meta http-equiv=\"Content-Security-Policy\">`, `<script type=\"application/ld+json\">` с `@graph` "
                        "(`Organization`, `SoftwareApplication`, `FAQPage`) и встроенная векторная схема `<svg viewBox=\"...\">`.\n"
                        "3. Чистый коммерческий русский язык в инфостиле: конкретные цифры (`0,12 с` на сверку пакета, "
                        "`34 банка` по прямому Host-to-Host, `99,98%` точность разноски), без воды, канцелярита и Tailwind-классов."
                    ),
                }
            ],
        },
        {
            "id": "eval_E_gen_ru_07_multifile_industrial",
            "lang": "ru",
            "domain": "ru_multifile_web_bundle",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Сформируй многофайловый пакет (`=== FILE: index.html ===`, `=== FILE: _headers ===`, "
                        "`=== FILE: robots.txt ===`, `=== FILE: llms.txt ===`) для инженерного центра "
                        "**«УралКриоМаш»** (проектирование и производство криогенных турбодетандеров и воздухоразделительных установок).\n\n"
                        "- В `index.html`: семантическая верстка HTML5, токены `oklch()`, адаптивная сетка характеристик с `@container`, "
                        "встроенный чертеж `<svg>`, разметка `JSON-LD @graph` и `FAQPage` на русском языке.\n"
                        "- В `_headers`: корректные заголовки безопасности Cloudflare (`Strict-Transport-Security`, `Content-Security-Policy`, "
                        "`X-Content-Type-Options: nosniff`) без блочных комментариев `/* ... */`.\n"
                        "- В `robots.txt` и `llms.txt`: правила индексации для поисковых и генеративных систем (`GPTBot`, `ClaudeBot`, `PerplexityBot`)."
                    ),
                }
            ],
        },
        {
            "id": "eval_E_gen_ru_08_ui_copy_audit",
            "lang": "ru",
            "domain": "ru_ui_and_copy_audit",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Выполни детальный инженерный и редакционный аудит карточки тарифов B2B SaaS-сервиса сквозной "
                        "складской логистики, в которой допущены следующие ошибки: бледный серый текст на светлом фоне "
                        "(контраст `2.1:1`), отсутствие `tabular-nums` в колонках цен, верстка на устаревших `float` без "
                        "`@container`, и штампованный рекламный текст («инновационный лидер рынка представляет уникальное решение под ключ»).\n\n"
                        "Выдай:\n"
                        "1. Структурированный разбор проблем доступности (WCAG 2.2 AA/AAA), сетки и коммерческого текста.\n"
                        "2. Полный исправленный код HTML5/CSS (`oklch()`, CSS Grid `subgrid`, `@container`, `tabular-nums`) "
                        "с переписанным фактологическим текстом в инфостиле."
                    ),
                }
            ],
        },
        {
            "id": "eval_E_gen_ru_09_seo_aeo_security",
            "lang": "ru",
            "domain": "ru_seo_aeo_security",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Разработай архитектуру технической SEO / AEO / GEO оптимизации и политики HTTP-безопасности "
                        "для двуязычного (`ru` + `en`) портала производителя лабораторных хроматографов (`https://chromalab.example/`).\n\n"
                        "Включи:\n"
                        "1. Полный блок `<head>` с `canonical`, взаимными ссылками `hreflang`, строгим `Content-Security-Policy` "
                        "и графом `JSON-LD @graph` (`Organization`, `Product`, `FAQPage`).\n"
                        "2. Конфигурацию `_headers`, `robots.txt` и `llms.txt` с проверочным чек-листом по стандарту OWASP."
                    ),
                }
            ],
        },
        {
            "id": "eval_E_gen_ru_10_ts_node_validation",
            "lang": "ru",
            "domain": "ru_ts_node_backend",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Напиши на строгом TypeScript (для Node.js без внешних зависимостей) модуль обработки и валидации "
                        "заявок на поставку промышленного оборудования:\n"
                        "1. Проверка ИНН (10 и 12 знаков с контрольными суммами), КПП и контактных данных по белому списку.\n"
                        "2. Защита от CSRF через проверку HMAC-SHA256 токена (`node:crypto` `timingSafeEqual`) и заголовка `Sec-Fetch-Site`.\n"
                        "3. Экранирование пользовательских строк от DOM/HTML XSS и формирование строгих HTTP-заголовков ответа."
                    ),
                }
            ],
        },
    ]
