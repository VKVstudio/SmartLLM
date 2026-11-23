#!/usr/bin/env python3
"""Convert the 9 Nano Banana cards and render the 11 remaining 16:10 Canon cards via Headless Chrome."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any

from PIL import Image, ImageDraw

STUDIO_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = STUDIO_ROOT / "smartllm_studio"
CANONS_KB_DIR = PKG_ROOT / "kb" / "styles" / "canons"
VENDOR_FONTS_DIR = PKG_ROOT / "templates" / "vendor" / "fonts"
VENDOR_MANIFEST = PKG_ROOT / "templates" / "vendor" / "MANIFEST.json"
OUT_DIR = PKG_ROOT / "static" / "art" / "canons"

BRAIN_DIR = Path(r"C:\Users\user\.gemini\antigravity\brain\2fff9198-2931-408f-bb0c-4f46fad59b56")
CONTACT_SHEET = BRAIN_DIR / "scratch" / "canons_20_contact_sheet.png"

NANO_BANANA_SOURCES: dict[str, Path] = {
    "01_bento_grid": BRAIN_DIR / "smartllm_bento_hero_ui_v2_1795374885781.jpg",
    "02_swiss_international": BRAIN_DIR / "smartllm_swiss_hero_ui_v2_1795374887918.jpg",
    "03_editorial_magazine": BRAIN_DIR / "smartllm_editorial_magazine_hero_v2_1795374898955.jpg",
    "04_hyper_minimal_speed": BRAIN_DIR / "smartllm_hero_hyper_minimal_speed_v2_1795374884267.jpg",
    "05_kinetic_typography": BRAIN_DIR / "smartllm_kinetic_typography_hero_v2_1795374898842.jpg",
    "06_neo_brutalism": BRAIN_DIR / "smartllm_hero_neo_brutalism_1795374948538.jpg",
    "08_liquid_glass": BRAIN_DIR / "smartllm_liquid_glass_hero_v2_1795374961989.jpg",
    "09_aurora_obsidian_mesh": BRAIN_DIR / "smartllm_hero_aurora_obsidian_1795374948820.jpg",
    "10_industrial_tactile": BRAIN_DIR / "smartllm_industrial_tactile_hero_1795374953170.jpg",
}


def _find_chrome() -> str:
    for cand in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
    ):
        if Path(cand).exists():
            return cand
    raise FileNotFoundError("Chrome/Edge binary not found for headless rendering")


def _crop_to_webp(src_path: Path, dst_webp: Path, width: int = 640, height: int = 400, quality: int = 84) -> int:
    dst_webp.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src_path) as im:
        rgb = im.convert("RGB")
        sw, sh = rgb.size
        target_ratio = width / height
        src_ratio = sw / max(1, sh)
        if abs(src_ratio - target_ratio) <= 0.02:
            out = rgb.resize((width, height), Image.Resampling.LANCZOS)
        elif src_ratio > target_ratio:
            # Preserve 100% horizontal width of 16:9 screenshots (no clipped headlines) and extend top/bottom edge rows cleanly
            scaled_h = int(round(width / src_ratio))
            fit = rgb.resize((width, scaled_h), Image.Resampling.LANCZOS)
            out = Image.new("RGB", (width, height))
            pad_top = (height - scaled_h) // 2
            top_row = fit.crop((0, 0, width, 1))
            bot_row = fit.crop((0, scaled_h - 1, width, scaled_h))
            for y in range(pad_top):
                out.paste(top_row, (0, y))
            out.paste(fit, (0, pad_top))
            for y in range(pad_top + scaled_h, height):
                out.paste(bot_row, (0, y))
        else:
            crop_h = int(round(sw / target_ratio))
            y0 = (sh - crop_h) // 2
            out = rgb.crop((0, y0, sw, y0 + crop_h)).resize((width, height), Image.Resampling.LANCZOS)
        q = quality
        while q >= 68:
            out.save(dst_webp, "WEBP", quality=q, method=6)
            if dst_webp.stat().st_size <= 95 * 1024:
                break
            q -= 4
    return dst_webp.stat().st_size


def _canon_font_css(canon: dict[str, Any], manifest: dict[str, Any]) -> str:
    pkg_to_id = {f["pkg"]: f["id"] for f in manifest["fonts"]}
    blocks: list[str] = []
    for pkg in canon["fonts"]["packages"]:
        fid = pkg_to_id[pkg]
        raw_css = (VENDOR_FONTS_DIR / fid / "font.css").read_text(encoding="utf-8")
        # Rewrite relative ./assets/fonts/<fid>/ URL to /fonts/<fid>/ for local HTTP server
        rewritten = raw_css.replace(f"./assets/fonts/{fid}/", f"/fonts/{fid}/")
        blocks.append(rewritten)
    return "\n".join(blocks)


def _bespoke_body(cid: str, pal: dict[str, str], fonts: dict[str, Any]) -> tuple[str, str]:
    """Return (extra_css, html_body) tailored specifically to each of the 11 remaining canons."""
    hd = fonts["heading"]
    bd = fonts["body"]
    mn = fonts.get("mono") or bd
    base_vars = f"""
    :root {{
      --bg: {pal['bg']}; --surface: {pal['surface']}; --elev: {pal['surface_elevated']};
      --border: {pal['border']}; --bc: {pal['border_control']};
      --text: {pal['text']}; --muted: {pal['muted']};
      --accent: {pal['accent']}; --accent-ink: {pal['accent_ink']}; --accent2: {pal['accent_2']};
      --hd: {hd}; --bd: {bd}; --mn: {mn};
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ width: 1280px; height: 800px; overflow: hidden; background: var(--bg); color: var(--text); font-family: var(--bd); }}
    """

    if cid == "07_avant_garde_poster":
        css = base_vars + """
        .wrap { padding: 36px 48px; height: 100%; display: grid; grid-template-rows: auto 1fr; gap: 28px; }
        .top { display: flex; justify-content: space-between; align-items: center; border-top: 4px solid var(--accent); border-bottom: 2px solid var(--text); padding: 14px 0; font-family: var(--mn); font-size: 14px; letter-spacing: 0.08em; text-transform: uppercase; }
        .grid { display: grid; grid-template-columns: 7fr 5fr; gap: 36px; align-items: stretch; }
        .left { display: flex; flex-direction: column; justify-content: space-between; border-top: 4px solid var(--text); padding-top: 24px; }
        h1 { font-family: var(--hd); font-size: 148px; line-height: 0.86; font-weight: 800; letter-spacing: -0.02em; text-transform: uppercase; }
        .lead { font-size: 22px; line-height: 1.35; max-width: 440px; color: var(--muted); }
        .cta { display: inline-block; background: var(--accent); color: var(--accent-ink); padding: 18px 34px; font-family: var(--hd); font-size: 24px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; border: 2px solid var(--text); }
        .right { border-top: 4px solid var(--accent); border-left: 2px solid var(--text); background: var(--surface); display: flex; align-items: center; justify-content: center; padding: 24px; }
        """
        html = """<div class="wrap">
          <div class="top"><span>NO. 07 / AVANT-GARDE POSTER</span><span>ARCHIVE EDITION 2026</span><span>4PX SCARLET RULE</span></div>
          <div class="grid">
            <div class="left">
              <div><h1>SmartLLM</h1><p class="lead" style="margin-top:20px;">Constructivist editorial clarity. Sharp rectilinear geometry with zero shadows.</p></div>
              <div style="display:flex;align-items:center;gap:24px;"><span class="cta">OPEN EXHIBITION →</span><span style="font-family:var(--mn);font-size:13px;">GRID 12 / 0PX RADIUS</span></div>
            </div>
            <div class="right">
              <svg viewBox="0 0 360 440" width="360" height="440">
                <rect x="20" y="20" width="320" height="400" fill="none" stroke="currentColor" stroke-width="3"/>
                <polygon points="40,400 220,40 310,40 130,400" fill="var(--accent)"/>
                <circle cx="240" cy="280" r="84" fill="var(--text)"/>
                <rect x="36" y="70" width="180" height="16" fill="var(--text)"/>
                <line x1="20" y1="220" x2="340" y2="220" stroke="var(--text)" stroke-width="2"/>
              </svg>
            </div>
          </div>
        </div>"""
        return css, html

    if cid == "11_soft_clay_playful":
        css = base_vars + """
        body { background: radial-gradient(circle at 18% 20%, rgba(255,255,255,0.9), transparent 55%), var(--bg); }
        .wrap { padding: 40px 56px; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
        .nav { display: flex; justify-content: space-between; align-items: center; }
        .pill-badge { padding: 10px 20px; border-radius: 999px; background: var(--surface); box-shadow: inset 0 4px 10px rgba(255,255,255,0.9), 0 12px 24px rgba(55,60,110,0.08); font-weight: 700; font-size: 14px; color: var(--accent); }
        .grid { display: grid; grid-template-columns: 7fr 5fr; gap: 36px; align-items: center; }
        .clay-card { background: var(--surface); border-radius: 28px; padding: 44px; box-shadow: inset 0 6px 14px rgba(255,255,255,0.95), inset 0 -10px 18px rgba(70,65,120,0.10), 0 24px 48px rgba(55,60,110,0.12); border: 1px solid var(--border); }
        h1 { font-family: var(--hd); font-size: 76px; font-weight: 800; line-height: 1.02; letter-spacing: -0.02em; }
        .lead { font-size: 20px; color: var(--muted); line-height: 1.5; margin: 18px 0 30px; }
        .btns { display: flex; gap: 16px; }
        .btn1 { padding: 18px 32px; border-radius: 999px; background: var(--accent); color: var(--accent-ink); font-family: var(--hd); font-weight: 700; font-size: 18px; box-shadow: inset 0 4px 8px rgba(255,255,255,0.35), 0 12px 24px rgba(40,60,180,0.22); }
        .btn2 { padding: 18px 28px; border-radius: 999px; background: var(--elev); color: var(--text); font-family: var(--hd); font-weight: 700; font-size: 18px; border: 2px solid var(--bc); }
        .side { display: grid; gap: 20px; }
        .mini { background: var(--elev); border-radius: 28px; padding: 28px; display: flex; align-items: center; gap: 20px; box-shadow: inset 0 5px 12px rgba(255,255,255,0.9), inset 0 -8px 14px rgba(70,65,120,0.08), 0 18px 36px rgba(55,60,110,0.10); }
        """
        html = """<div class="wrap">
          <div class="nav"><span class="pill-badge">SOFT CLAY · CANON 11</span><span style="font-weight:700;color:var(--muted);">Interactive Playground</span></div>
          <div class="grid">
            <div class="clay-card">
              <h1>SmartLLM</h1>
              <p class="lead">Friendly sculpted 3D bevel surfaces crafted for modern learning apps and tactile tools.</p>
              <div class="btns"><span class="btn1">Start Building</span><span class="btn2">Explore Kit</span></div>
            </div>
            <div class="side">
              <div class="mini"><svg width="68" height="68" viewBox="0 0 80 80"><defs><radialGradient id="g1" cx="35%" cy="30%"><stop offset="0%" stop-color="#fff"/><stop offset="65%" stop-color="var(--accent)"/><stop offset="100%" stop-color="#1e295b"/></radialGradient></defs><circle cx="40" cy="40" r="34" fill="url(#g1)"/></svg><div><strong style="font-family:var(--hd);font-size:22px;">28px Pill Clay</strong><p style="color:var(--muted);font-size:15px;">Double inset ceramic highlight</p></div></div>
              <div class="mini"><svg width="68" height="68" viewBox="0 0 80 80"><defs><radialGradient id="g2" cx="35%" cy="30%"><stop offset="0%" stop-color="#fff"/><stop offset="65%" stop-color="var(--accent2)"/><stop offset="100%" stop-color="#7c2d12"/></radialGradient></defs><rect x="8" y="8" width="64" height="64" rx="22" fill="url(#g2)"/></svg><div><strong style="font-family:var(--hd);font-size:22px;">Tactile Physics</strong><p style="color:var(--muted);font-size:15px;">Spring bounce + WCAG AAA ink</p></div></div>
            </div>
          </div>
          <div style="font-size:14px;color:var(--muted);font-family:var(--mn);">DOUBLE BEVEL · 04 / 08 / 12 RESPONSIVE CLAMP</div>
        </div>"""
        return css, html

    if cid == "12_quiet_luxury_minimal":
        css = base_vars + """
        .wrap { padding: 54px 80px; height: 100%; display: grid; grid-template-rows: auto 1fr auto; }
        .top { display: flex; justify-content: space-between; font-size: 12px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--border); padding-bottom: 18px; }
        .grid { display: grid; grid-template-columns: 7fr 5fr; gap: 64px; align-items: center; }
        h1 { font-family: var(--hd); font-size: 98px; font-weight: 300; line-height: 0.96; letter-spacing: -0.02em; }
        .sub { font-size: 18px; line-height: 1.7; color: var(--muted); max-width: 440px; margin: 28px 0 36px; }
        .cta { display: inline-block; padding: 14px 30px; background: var(--accent); color: var(--accent-ink); font-size: 13px; letter-spacing: 0.16em; text-transform: uppercase; border-radius: 2px; }
        .art { display: flex; justify-content: flex-end; }
        """
        html = """<div class="wrap">
          <div class="top"><span>ATELIER EDITION</span><span>ZÜRICH · KYOTO</span><span>COLD PLATINUM PALETTE</span></div>
          <div class="grid">
            <div>
              <h1>SmartLLM</h1>
              <p class="sub">Whispered Nordic proportion, airy cold-platinum stone tones, and delicate high-contrast serif poise.</p>
              <span class="cta">REQUEST PRIVATE VIEWING</span>
            </div>
            <div class="art">
              <svg width="360" height="440" viewBox="0 0 360 440">
                <rect x="40" y="30" width="280" height="380" fill="var(--surface)"/>
                <rect x="95" y="90" width="170" height="240" fill="var(--elev)" stroke="var(--border)" stroke-width="1"/>
                <circle cx="180" cy="185" r="46" fill="none" stroke="var(--accent)" stroke-width="1.5"/>
                <line x1="180" y1="90" x2="180" y2="330" stroke="var(--border)" stroke-width="1"/>
                <rect x="70" y="350" width="220" height="1" fill="var(--accent)"/>
              </svg>
            </div>
          </div>
          <div style="font-size:12px;letter-spacing:0.16em;color:var(--muted);">NO BOX SHADOWS · NO MONOSPACE · 2X ARCHITECTURAL AIR</div>
        </div>"""
        return css, html

    if cid == "13_cinematic_documentary":
        css = base_vars + """
        body { background: radial-gradient(60% 70% at 74% 48%, rgba(215,155,75,0.22), transparent 68%), var(--bg); }
        .wrap { padding: 48px 68px; height: 100%; display: grid; grid-template-rows: auto 1fr auto; }
        .top { display: flex; justify-content: space-between; font-family: var(--mn); font-size: 12px; letter-spacing: 0.14em; color: var(--muted); border-bottom: 1px solid var(--border); padding-bottom: 14px; }
        .grid { display: grid; grid-template-columns: 7fr 5fr; gap: 44px; align-items: center; }
        h1 { font-family: var(--hd); font-size: 86px; font-weight: 500; line-height: 1.02; letter-spacing: -0.02em; }
        .lead { font-size: 19px; line-height: 1.6; color: var(--muted); max-width: 480px; margin: 20px 0 32px; }
        .cta { display: inline-block; background: var(--accent); color: var(--accent-ink); padding: 15px 30px; border-radius: 4px; font-weight: 700; font-size: 15px; letter-spacing: 0.04em; }
        .frame { border: 1px solid var(--border); border-radius: 4px; background: var(--surface); padding: 16px; }
        """
        html = """<div class="wrap">
          <div class="top"><span>REEL 01 · 35MM DARKROOM</span><span>ISO 800 SELENIUM</span><span>CHAPTER IV</span></div>
          <div class="grid">
            <div>
              <h1>SmartLLM</h1>
              <p class="lead">Warm tungsten key light across matte selenium obsidian, pairing literary serif gravity with cinema pacing.</p>
              <span class="cta">Watch Field Film →</span>
            </div>
            <div class="frame">
              <svg viewBox="0 0 400 320" width="100%" height="320">
                <defs><linearGradient id="amb" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="var(--accent)" stop-opacity="0.7"/><stop offset="100%" stop-color="#141210" stop-opacity="0.95"/></linearGradient></defs>
                <rect width="400" height="320" fill="#121110"/>
                <polygon points="120,0 320,0 260,320 60,320" fill="url(#amb)" opacity="0.55"/>
                <rect x="44" y="190" width="312" height="90" fill="var(--elev)" opacity="0.85"/>
                <circle cx="230" cy="128" r="46" fill="none" stroke="var(--accent)" stroke-width="2"/>
                <text x="58" y="242" fill="var(--text)" font-size="11" font-family="monospace">F/2.0 · 35MM ANAMORPHIC · 2900K</text>
              </svg>
            </div>
          </div>
          <div style="font-family:var(--mn);font-size:12px;color:var(--muted);">ONLY DARK SERIF CANON · SCRIM DIRECTIONAL DEPTH</div>
        </div>"""
        return css, html

    if cid == "14_spatial_3d_showcase":
        css = base_vars + """
        body { background: radial-gradient(48% 54% at 68% 50%, rgba(56,189,248,0.16), transparent 66%), radial-gradient(36% 42% at 24% 25%, rgba(168,85,247,0.14), transparent 65%), var(--bg); }
        .wrap { padding: 44px 60px; height: 100%; display: grid; grid-template-rows: auto 1fr auto; }
        .top { display: flex; justify-content: space-between; font-family: var(--mn); font-size: 12px; color: var(--muted); }
        .grid { display: grid; grid-template-columns: 6fr 6fr; gap: 36px; align-items: center; }
        h1 { font-family: var(--hd); font-size: 74px; font-weight: 700; line-height: 1.02; letter-spacing: 0.02em; text-transform: uppercase; }
        .lead { font-size: 18px; color: var(--muted); line-height: 1.55; margin: 18px 0 28px; }
        .cta { display: inline-block; padding: 15px 28px; border-radius: 10px; background: var(--accent); color: var(--accent-ink); font-family: var(--mn); font-weight: 700; font-size: 14px; }
        .stage { border: 1px solid var(--border); border-radius: 16px; background: radial-gradient(circle at 50% 45%, rgba(255,255,255,0.06), rgba(0,0,0,0.4)); padding: 20px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.18); }
        """
        html = """<div class="wrap">
          <div class="top"><span>SPATIAL 3D · WEBGL STAGE</span><span>THREE.JS MIT · 60 FPS</span></div>
          <div class="grid">
            <div>
              <h1>SmartLLM</h1>
              <p class="lead">Interactive optical-sapphire and brushed-titanium viewport with crisp specular HDRI rim physics.</p>
              <span class="cta">INITIALIZE 3D VIEW →</span>
            </div>
            <div class="stage">
              <svg viewBox="0 0 420 340" width="100%" height="340">
                <defs><linearGradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="var(--accent)"/><stop offset="100%" stop-color="var(--accent2)"/></linearGradient></defs>
                <ellipse cx="210" cy="175" rx="165" ry="62" fill="none" stroke="var(--accent)" stroke-width="1.2" opacity="0.45" transform="rotate(-14 210 175)"/>
                <polygon points="210,36 320,130 278,270 142,270 100,130" fill="var(--elev)" stroke="url(#rim)" stroke-width="2.5"/>
                <polygon points="210,36 278,270 142,270" fill="rgba(255,255,255,0.06)" stroke="var(--accent)" stroke-width="1"/>
                <circle cx="210" cy="175" r="24" fill="var(--accent)" opacity="0.85"/>
              </svg>
            </div>
          </div>
          <div style="font-family:var(--mn);font-size:12px;color:var(--muted);">SINGLE LAZY CANVAS · STATIC Z-IMAGE REDUCED-MOTION FALLBACK</div>
        </div>"""
        return css, html

    if cid == "15_organic_biophilic_eco":
        css = base_vars + """
        .wrap { padding: 48px 64px; height: 100%; display: grid; grid-template-rows: auto 1fr auto; }
        .top { display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: var(--muted); }
        .grid { display: grid; grid-template-columns: 7fr 5fr; gap: 40px; align-items: center; }
        h1 { font-family: var(--hd); font-size: 72px; font-weight: 600; line-height: 1.05; letter-spacing: -0.02em; }
        .lead { font-size: 19px; line-height: 1.6; color: var(--muted); margin: 18px 0 30px; max-width: 470px; }
        .cta { display: inline-block; padding: 15px 30px; border-radius: 999px; background: var(--accent); color: var(--accent-ink); font-weight: 700; font-size: 15px; }
        .card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 28px; }
        """
        html = """<div class="wrap">
          <div class="top"><span style="font-weight:700;color:var(--accent);">BIOPHILIC · LOW-CARBON <= 400KB</span><span>SAGE-MIST + NORDIC PINE</span></div>
          <div class="grid">
            <div>
              <h1>SmartLLM</h1>
              <p class="lead">Honest Nordic timber and sage-mist stillness with strict sub-400KB transfer weight and zero heavy grain filters.</p>
              <span class="cta">Explore Low-Energy Stack</span>
            </div>
            <div class="card">
              <svg viewBox="0 0 360 320" width="100%" height="320">
                <rect width="360" height="320" rx="14" fill="var(--elev)"/>
                <path d="M90 270 C90 150, 210 70, 280 50 C270 160, 195 250, 90 270 Z" fill="var(--accent)" opacity="0.88"/>
                <path d="M90 270 L245 85" stroke="var(--bg)" stroke-width="3"/>
                <rect x="34" y="230" width="150" height="58" rx="10" fill="var(--surface)" stroke="var(--border)"/>
                <text x="48" y="264" fill="var(--text)" font-size="12" font-family="monospace">0.12g CO2 / view</text>
              </svg>
            </div>
          </div>
          <div style="font-family:var(--mn);font-size:12px;color:var(--muted);">NO YELLOW BEIGE · CLEAR NATURAL DAYLIGHT</div>
        </div>"""
        return css, html

    if cid == "16_artisan_craft_zine":
        css = base_vars + """
        .wrap { padding: 44px 60px; height: 100%; display: grid; grid-template-rows: auto 1fr auto; }
        .top { display: flex; justify-content: space-between; font-family: var(--mn); font-size: 13px; border-bottom: 2px solid var(--border); padding-bottom: 12px; }
        .grid { display: grid; grid-template-columns: 7fr 5fr; gap: 36px; align-items: center; }
        h1 { font-family: var(--hd); font-size: 78px; font-weight: 700; line-height: 1.02; letter-spacing: -0.02em; }
        .lead { font-size: 19px; line-height: 1.6; color: var(--muted); margin: 18px 0 28px; }
        .btn { display: inline-block; padding: 15px 28px; background: var(--accent); color: var(--accent-ink); border: 2px solid var(--text); border-radius: 6px; font-weight: 700; box-shadow: 4px 4px 0 var(--text); }
        .riso { background: var(--surface); border: 2px solid var(--text); border-radius: 8px; padding: 24px; box-shadow: 7px 7px 0 var(--accent2); }
        """
        html = """<div class="wrap">
          <div class="top"><span>ISSUE 16 · RISOGRAPH ZINE</span><span>COTTON SLATE + TERRACOTTA</span><span>STAMPED 4/4</span></div>
          <div class="grid">
            <div>
              <h1>SmartLLM</h1>
              <p class="lead">Tactile kiln terracotta ink pressed onto cool cotton-slate paper with crisp risograph print offset.</p>
              <span class="btn">Read Craft Monograph →</span>
            </div>
            <div class="riso">
              <svg viewBox="0 0 340 300" width="100%" height="300">
                <circle cx="135" cy="145" r="88" fill="var(--accent)" opacity="0.88"/>
                <rect x="150" y="75" width="145" height="145" fill="var(--accent2)" opacity="0.82"/>
                <rect x="24" y="235" width="290" height="40" fill="var(--bg)" stroke="var(--text)" stroke-width="2"/>
                <text x="42" y="261" fill="var(--text)" font-size="14" font-family="monospace">PRESS PROOF · KILN STONEWARE</text>
              </svg>
            </div>
          </div>
          <div style="font-family:var(--mn);font-size:12px;color:var(--muted);">VOLLKORN SERIF · PRUSSIAN INDIGO OVERPRINT</div>
        </div>"""
        return css, html

    if cid == "17_fintech_institutional":
        css = base_vars + """
        .wrap { padding: 38px 56px; height: 100%; display: grid; grid-template-rows: auto 1fr auto; gap: 24px; }
        .top { display: flex; justify-content: space-between; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px 24px; }
        .grid { display: grid; grid-template-columns: 6fr 6fr; gap: 28px; align-items: stretch; }
        .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 36px; box-shadow: 0 4px 16px rgba(15,23,42,0.06); display: flex; flex-direction: column; justify-content: space-between; }
        h1 { font-family: var(--hd); font-size: 64px; font-weight: 700; line-height: 1.05; letter-spacing: -0.02em; }
        .lead { font-size: 18px; line-height: 1.55; color: var(--muted); margin: 16px 0 24px; }
        .cta { display: inline-block; padding: 14px 26px; border-radius: 6px; background: var(--accent); color: var(--accent-ink); font-weight: 600; font-size: 15px; }
        table { width: 100%; border-collapse: collapse; font-family: var(--mn); font-size: 13px; }
        th, td { padding: 12px 10px; border-bottom: 1px solid var(--border); text-align: left; }
        th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; }
        """
        html = """<div class="wrap">
          <div class="top"><strong style="font-family:var(--hd);font-size:18px;">SmartLLM INSTITUTIONAL</strong><span style="font-family:var(--mn);font-size:12px;color:var(--accent2);font-weight:700;">SLA 99.995% · AUDIT GRADE</span></div>
          <div class="grid">
            <div class="card">
              <div><span style="font-family:var(--mn);font-size:12px;color:var(--accent2);font-weight:700;">TREASURY ROUTING LEDGER</span><h1 style="margin-top:10px;">SmartLLM</h1><p class="lead">Audited deterministic execution with midnight-navy clarity, tabular numerals, and strict capital compliance.</p></div>
              <div><span class="cta">Schedule Compliance Review</span></div>
            </div>
            <div class="card">
              <table>
                <thead><tr><th>Execution Node</th><th>P99</th><th>Status</th></tr></thead>
                <tbody>
                  <tr><td>Zürich Sovereign-01</td><td>4.1 ms</td><td style="color:var(--accent2);font-weight:700;">PASS</td></tr>
                  <tr><td>Frankfurt Vault-02</td><td>4.8 ms</td><td style="color:var(--accent2);font-weight:700;">PASS</td></tr>
                  <tr><td>Tokyo Ledger-04</td><td>6.2 ms</td><td style="color:var(--accent2);font-weight:700;">PASS</td></tr>
                </tbody>
              </table>
              <svg viewBox="0 0 420 120" width="100%" height="120" style="margin-top:16px;">
                <polyline points="10,95 85,78 155,82 225,52 300,44 375,20 410,18" fill="none" stroke="var(--accent2)" stroke-width="3"/>
                <polyline points="10,95 85,78 155,82 225,52 300,44 375,20 410,18 410,115 10,115" fill="var(--accent2)" opacity="0.12"/>
              </svg>
            </div>
          </div>
          <div style="font-family:var(--mn);font-size:12px;color:var(--muted);">NAVY + EMERALD · 8PX ELEVATED LEDGER SURFACES</div>
        </div>"""
        return css, html

    if cid == "18_devtool_command_ui":
        css = base_vars + """
        body { background-color: var(--bg); background-image: radial-gradient(rgba(255,255,255,0.11) 1px, transparent 1px); background-size: 24px 24px; }
        .wrap { padding: 38px 56px; height: 100%; display: grid; grid-template-rows: auto 1fr auto; gap: 24px; }
        .cmdbar { display: flex; justify-content: space-between; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 20px; font-family: var(--mn); font-size: 13px; }
        .kbd { border: 1px solid var(--bc); background: var(--elev); border-radius: 4px; padding: 3px 8px; font-size: 12px; }
        .grid { display: grid; grid-template-columns: 7fr 5fr; gap: 28px; align-items: center; }
        h1 { font-family: var(--hd); font-size: 74px; font-weight: 700; line-height: 1.02; letter-spacing: -0.03em; }
        .lead { font-size: 18px; line-height: 1.55; color: var(--muted); margin: 16px 0 28px; max-width: 480px; }
        .cta { display: inline-block; padding: 14px 26px; border-radius: 6px; background: var(--accent); color: var(--accent-ink); font-family: var(--mn); font-weight: 700; font-size: 14px; }
        .term { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 24px; font-family: var(--mn); font-size: 14px; line-height: 1.8; }
        """
        html = """<div class="wrap">
          <div class="cmdbar"><span>$ smartllm route --strict --offline</span><span><span class="kbd">Ctrl</span> + <span class="kbd">K</span></span></div>
          <div class="grid">
            <div>
              <span style="font-family:var(--mn);font-size:12px;color:var(--accent);">GEIST SYSTEM · 24PX DOT-GRID · ZERO PURPLE</span>
              <h1 style="margin-top:8px;">SmartLLM</h1>
              <p class="lead">Flat carbon IDE aesthetic with crisp 1px borders, emerald telemetry signals, and zero gradient clutter.</p>
              <span class="cta">npx create-smartllm@latest</span>
            </div>
            <div class="term">
              <div style="color:var(--muted);">// 127.0.0.1:8090 local runtime</div>
              <div>engine: <span style="color:var(--accent);">SmartLLM-v2-K320</span></div>
              <div>swap_bytes: <span style="color:var(--accent);">0 B</span></div>
              <div>throughput: <span style="color:var(--accent);">21.14 tok/s</span></div>
              <div>csp_policy: <span style="color:var(--accent);">strict-sha256 PASS</span></div>
              <div>status: <span style="color:var(--accent2);">READY</span></div>
            </div>
          </div>
          <div style="font-family:var(--mn);font-size:12px;color:var(--muted);">GEIST MONO · EMERALD IDE ACCENT</div>
        </div>"""
        return css, html

    if cid == "19_calm_human_accessible":
        css = base_vars + """
        .wrap { padding: 48px 64px; height: 100%; display: grid; grid-template-rows: auto 1fr auto; gap: 24px; }
        .top { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--bc); padding-bottom: 16px; font-weight: 600; font-size: 16px; }
        .grid { display: grid; grid-template-columns: 7fr 5fr; gap: 36px; align-items: center; }
        h1 { font-family: var(--hd); font-size: 70px; font-weight: 700; line-height: 1.08; }
        .lead { font-size: 20px; line-height: 1.65; color: var(--muted); margin: 18px 0 30px; }
        .cta { display: inline-block; padding: 18px 34px; min-height: 56px; border-radius: 10px; background: var(--accent); color: var(--accent-ink); font-size: 18px; font-weight: 700; outline: 3px solid var(--accent); outline-offset: 4px; }
        .box { background: var(--surface); border: 2px solid var(--bc); border-radius: 14px; padding: 32px; display: grid; gap: 18px; }
        .row { display: flex; justify-content: space-between; font-size: 18px; font-weight: 600; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
        """
        html = """<div class="wrap">
          <div class="top"><span>CALM ACCESSIBLE · WCAG 2.2 AAA</span><span>TEXT CONTRAST >= 14:1</span></div>
          <div class="grid">
            <div>
              <h1>SmartLLM</h1>
              <p class="lead">Glare-free warm ivory reading surface, zero distracting motion, and generous 48px+ focus-clear controls.</p>
              <span class="cta">Get Clear Guide</span>
            </div>
            <div class="box">
              <div class="row"><span>Text / Background</span><span>16.4 : 1 AAA</span></div>
              <div class="row"><span>Control Border</span><span>7.1 : 1 PASS</span></div>
              <div class="row"><span>Touch Targets</span><span>48px - 56px</span></div>
              <div class="row" style="border-bottom:0;padding-bottom:0;"><span>Motion Mode</span><span>0ms Calm</span></div>
            </div>
          </div>
          <div style="font-family:var(--mn);font-size:13px;color:var(--muted);">SEA-GLASS TEAL · CIVIC / HEALTHCARE / EDU CANON</div>
        </div>"""
        return css, html

    if cid == "20_maximalist_collage_pop":
        css = base_vars + """
        .wrap { padding: 38px 56px; height: 100%; display: grid; grid-template-rows: auto 1fr auto; gap: 22px; }
        .top { display: flex; justify-content: space-between; align-items: center; }
        .tag { background: var(--accent2); color: var(--text); border: 2px solid var(--text); padding: 8px 16px; border-radius: 10px; font-family: var(--mn); font-weight: 700; font-size: 13px; box-shadow: 4px 4px 0 var(--text); }
        .grid { display: grid; grid-template-columns: 7fr 5fr; gap: 30px; align-items: center; }
        .hero-box { background: var(--surface); border: 3px solid var(--text); border-radius: 16px; padding: 36px; box-shadow: 7px 7px 0 var(--accent2); }
        h1 { font-family: var(--hd); font-size: 74px; font-weight: 800; line-height: 1.02; }
        .lead { font-size: 19px; line-height: 1.5; color: var(--muted); margin: 16px 0 26px; }
        .cta { display: inline-block; padding: 16px 30px; background: var(--accent); color: var(--accent-ink); border: 2px solid var(--text); border-radius: 12px; font-family: var(--hd); font-weight: 700; font-size: 18px; box-shadow: 5px 5px 0 var(--text); }
        .collage { display: grid; gap: 18px; }
        .pop1 { background: var(--accent2); color: var(--text); border: 3px solid var(--text); border-radius: 16px; padding: 24px; box-shadow: 6px 6px 0 var(--accent); }
        .pop2 { background: var(--elev); color: var(--text); border: 3px solid var(--text); border-radius: 16px; padding: 24px; box-shadow: 6px 6px 0 var(--accent2); }
        """
        html = """<div class="wrap">
          <div class="top"><span class="tag">CANON 20 · MAXIMALIST POP</span><span style="font-family:var(--mn);font-weight:700;">ULTRAMARINE + MARIGOLD</span></div>
          <div class="grid">
            <div class="hero-box">
              <h1>SmartLLM</h1>
              <p class="lead">Multi-hue editorial energy with crisp 5px colored offset print shadows and expressive geometric hierarchy.</p>
              <span class="cta">Launch Festival Kit ★</span>
            </div>
            <div class="collage">
              <div class="pop1"><strong style="font-family:var(--hd);font-size:24px;">Playful Contrast</strong><p style="margin-top:6px;font-size:15px;">Layered exhibition cards with tactile inked outlines.</p></div>
              <div class="pop2"><strong style="font-family:var(--hd);font-size:24px;">Creative Pop 2027</strong><p style="margin-top:6px;font-size:15px;">Zero muddled overlap, high readability at 16px+.</p></div>
            </div>
          </div>
          <div style="font-family:var(--mn);font-size:12px;color:var(--muted);">RUBIK + SHANTELL ACCENT · COLORED OFFSET SHADOWS</div>
        </div>"""
        return css, html

    raise KeyError(f"Unexpected canon {cid}")


def _make_contact_sheet(out_png: Path) -> None:
    files = sorted(OUT_DIR.glob("*.webp"))
    assert len(files) == 20, f"Expected 20 webp cards, found {len(files)}"
    cols, rows = 4, 5
    tw, th = 320, 200
    pad, lbl = 10, 22
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + lbl + pad) + pad), (11, 13, 18))
    draw = ImageDraw.Draw(sheet)
    for idx, fp in enumerate(files):
        r, c = idx // cols, idx % cols
        x, y = pad + c * (tw + pad), pad + r * (th + lbl + pad)
        with Image.open(fp) as im:
            tile = im.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
            sheet.paste(tile, (x, y))
        src_tag = "NB" if fp.stem in NANO_BANANA_SOURCES else "CHR"
        draw.text((x + 4, y + th + 4), f"{fp.stem[:26]} [{src_tag}]", fill=(236, 238, 243))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png, "PNG", optimize=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # 1. Convert 9 Nano Banana cards
    sizes: dict[str, int] = {}
    for cid, src in NANO_BANANA_SOURCES.items():
        if not src.exists():
            raise FileNotFoundError(f"Missing Nano Banana card: {src}")
        sizes[cid] = _crop_to_webp(src, OUT_DIR / f"{cid}.webp", quality=84)

    # 2. Render 11 remaining cards with headless Chrome + vendored WOFF2 fonts
    manifest = json.loads(VENDOR_MANIFEST.read_text(encoding="utf-8"))
    chrome_bin = _find_chrome()
    remaining = sorted(p for p in CANONS_KB_DIR.glob("*.json") if p.stem not in NANO_BANANA_SOURCES)

    with tempfile.TemporaryDirectory(prefix="smartllm_cards_chrome_") as td:
        td_p = Path(td)
        pages_dir = td_p / "site"
        (pages_dir / "fonts").mkdir(parents=True, exist_ok=True)
        # Copy/junction fonts inside temp HTTP root cleanly or serve via custom handler
        import shutil
        shutil.copytree(VENDOR_FONTS_DIR, pages_dir / "fonts", dirs_exist_ok=True)

        handler = partial(SimpleHTTPRequestHandler, directory=str(pages_dir))
        srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = srv.server_address[1]
        thr = threading.Thread(target=srv.serve_forever, daemon=True)
        thr.start()
        try:
            for cf in remaining:
                canon = json.loads(cf.read_text(encoding="utf-8"))
                cid = canon["id"]
                pol = canon["default_polarity"]
                pal = canon["palettes"][pol]
                font_css = _canon_font_css(canon, manifest)
                extra_css, body_html = _bespoke_body(cid, pal, canon["fonts"])
                html_doc = (
                    "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                    f"<style>{font_css}\n{extra_css}</style></head>"
                    f"<body>{body_html}</body></html>"
                )
                (pages_dir / f"{cid}.html").write_text(html_doc, encoding="utf-8")
                png_out = td_p / f"{cid}.png"
                url = f"http://127.0.0.1:{port}/{cid}.html"
                cmd = [
                    chrome_bin,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--hide-scrollbars",
                    "--window-size=1280,800",
                    "--force-device-scale-factor=1",
                    "--virtual-time-budget=2500",
                    f"--screenshot={png_out}",
                    url,
                ]
                subprocess.run(cmd, check=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
                sizes[cid] = _crop_to_webp(png_out, OUT_DIR / f"{cid}.webp", quality=86)
        finally:
            srv.shutdown()
            srv.server_close()

    _make_contact_sheet(CONTACT_SHEET)
    print(f"CANON_CARDS_READY: count={len(sizes)}, max_kb={max(sizes.values()) / 1024:.1f}, contact_sheet={CONTACT_SHEET}")


if __name__ == "__main__":
    main()
