"""Sequential Project Task Orchestrator & 6-Variant 512x512 Logo Generator for SmartLLM Studio."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Callable
import uuid

from .adapters import get_rag_selector
from .catalog import AI_CRAWLERS_DEFAULT
from .config import DEFAULT_REPO_ROOT, STUDIO_ROOT
from .engines.llm import _PageCacheTrimmer
from .kb_loader import harden_zimage_prompt, palette_to_material_summary
from .os_compat import get_log_dir, is_cpu_test_mode, subprocess_kwargs
from .pages import (
    AVAILABLE_BLOCKS,
    DEFAULT_PAGE_SLUGS,
    PAGE_MAP,
    PRESET_PAGES,
    build_default_company,
    build_routes_from_pages,
    clean_page_blocks,
    company_block_prompt,
    default_page_blocks,
    infer_gender,
    page_available_blocks,
    page_default_blocks,
    page_title,
    resolve_primary_lang,
    resolve_slot_dimensions,
)
from .rag import detect_language, make_synthetic_png


def _clean(text: Any) -> str:
    return " ".join(str(text or "").split()).strip()


def _can_use_gpu(state: Any | None) -> bool:
    """Return True when real GPU LLM / sd-cli execution is allowed and binaries exist."""
    if state is None:
        return False
    if is_cpu_test_mode():
        return False
    return bool(
        getattr(state, "llm", None)
        and state.llm.server_bin
        and state.llm.server_bin.exists()
        and state.llm.model_path
        and state.llm.model_path.exists()
    )


def _gpu_unavailable_message(state: Any | None) -> str:
    """Actionable diagnosis instead of a silent CPU-template fallback in interactive mode."""
    if state is None:
        return "GPU engine unavailable: Studio state is not initialized."
    missing: list[str] = []
    llm = getattr(state, "llm", None)
    if llm is None or not getattr(llm, "server_bin", None) or not llm.server_bin.exists():
        missing.append(f"llama-server binary not found ({getattr(llm, 'server_bin', None) or 'not configured'})")
    if llm is None or not getattr(llm, "model_path", None) or not llm.model_path.exists():
        missing.append(f"GGUF model not found ({getattr(llm, 'model_path', None) or 'not configured'})")
    img = getattr(state, "image_jobs", None)
    if img is not None and not img._has_real_sd_weights():
        missing.append("sd-cli binary or Z-Image weights not found (GPU visuals would be skipped)")
    return (
        "GPU engine unavailable: " + "; ".join(missing or ["unknown reason"])
        + ". Fix the paths in Settings (or env LLAMA_SERVER_BIN / SMARTLLM_MODEL_PATH / SD_CLI_BIN / ZIMAGE_DIT_PATH / ZIMAGE_TE_PATH / ZIMAGE_VAE_PATH)."
        + " For deliberate CPU-only mode set SMARTLLM_STUDIO_HEADLESS=1."
    )


LOGO_STYLES_RU = [
    "01 · Пиктограмма",
    "02 · Негативное пространство",
    "03 · Геометрическая абстракция",
    "04 · Круглая печать",
    "05 · Жирный силуэт",
    "06 · Контурная линия",
]
LOGO_STYLES_EN = [
    "01 · Pictogram",
    "02 · Negative Space",
    "03 · Geometric Abstraction",
    "04 · Circular Seal",
    "05 · Bold Silhouette",
    "06 · Line Art",
]
LOGO_FINISHERS = [
    "single centered pictogram, flat two-color vector mark, solid neutral backdrop, crisp edges, balanced negative space",
    "clever negative-space mark, one continuous silhouette, flat two-color vector, solid neutral backdrop, crisp edges",
    "geometric abstraction built from circles and diagonal cuts, flat three-color vector, solid neutral backdrop, precise alignment",
    "circular badge seal, bold monoline ring, flat two-color vector, solid neutral backdrop, symmetrical composition",
    "bold flat silhouette with confident mass, high-contrast two-color vector, solid neutral backdrop, sharp borderless edges",
    "fine contour line art, one uniform stroke weight, flat two-color vector, solid neutral backdrop, elegant negative space",
]
LOGO_NEGATIVE = (
    "text, letters, typography, watermark, signature, mockup, photo of a person, busy scene, "
    "gradient mesh, fuzzy edges, illegible micro-detail, lens flare, 3D bevel, drop shadow, "
    "multiple objects, frame, border, sticker sheet, collage"
)
ZIMAGE_LOGO_CANON_2026 = (
    "November 2026 Z-Image-Turbo logo canon: one scalable centered symbol, strong silhouette at 32px, "
    "2-4 flat colors, vector-clean geometry, balanced negative space, crisp anti-aliased edges, "
    "solid neutral backdrop, symbol-only composition."
)


def _extract_initials(name: str) -> str:
    words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", name or "SL") if w]
    if not words:
        return "SL"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def _logo_font_candidates() -> list[Path]:
    """Cross-OS TTF candidates for the CPU logo fallback (PIL cannot read bundled WOFF2)."""
    cands: list[Path] = []
    win_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if win_root:
        fonts = Path(win_root) / "Fonts"
        cands += [fonts / "arialbd.ttf", fonts / "segoeuib.ttf", fonts / "calibrib.ttf", fonts / "arial.ttf"]
    cands += [
        Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/noto/NotoSans-Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ]
    return cands


def _seed_colors_from_text(text: str, variant_idx: int) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    h = hashlib.sha256(f"{text}:{variant_idx}".encode("utf-8")).digest()
    palettes = [
        ((14, 17, 24), (192, 132, 252), (229, 184, 105)),   # Obsidian + Violet + Gold
        ((16, 24, 32), (52, 211, 153), (236, 253, 245)),    # Deep Slate + Emerald + Mint
        ((24, 20, 18), (229, 184, 105), (245, 240, 230)),   # Warm Espresso + Brass + Cream
        ((12, 19, 36), (96, 165, 250), (226, 232, 240)),    # Midnight Navy + Cobalt + Silver
        ((22, 22, 26), (244, 114, 182), (250, 245, 255)),   # Graphite + Rose Quartz + Ice
        ((18, 26, 22), (163, 230, 53), (240, 253, 244)),    # Forest Carbon + Lime + Ivory
    ]
    base_bg, accent1, accent2 = palettes[variant_idx % len(palettes)]
    shift = (h[0] % 15) - 7
    bg = (max(8, min(40, base_bg[0] + shift)), max(8, min(40, base_bg[1] + shift)), max(8, min(45, base_bg[2] + shift)))
    return bg, accent1, accent2


_LOGO_LITERAL_STOPWORDS_RE = re.compile(
    r"(?i)\b(?:no\s+text|without\s+text|no\s+letters|without\s+letters|no\s+words|without\s+words|"
    r"text-free|typography|letterforms?|monograms?|initials?|words?|letters?|slogan|wordmark)\b"
)

_LOGO_FALLBACK_SPECS = [
    (
        "Pictogram",
        "Flat geometric vector pictogram of twin arched bridge spans crowned by a sunlit amber keystone, flat terracotta brick and deep charcoal matte on a warm cream paper solid backdrop",
    ),
    (
        "Negative Space",
        "Clever negative-space silhouette emblem carving an ascending folded prism inside a solid stepped gateway form, warm champagne gold on a deep obsidian matte solid backdrop",
    ),
    (
        "Geometric Abstraction",
        "Constructivist Bauhaus geometric abstraction built from three overlapping precision circles and a sharp 45-degree diagonal light beam, deep Prussian blue and burnt copper on a soft stone-ivory solid backdrop",
    ),
    (
        "Circular Seal",
        "Symmetrical circular heritage crest formed by a crisp heavy ring enclosing a stylized Nordic spruce leaf and horizon arc, deep forest pine and burnished brass on a warm alabaster solid backdrop",
    ),
    (
        "Bold Silhouette",
        "Confident monolithic sculptural silhouette formed from two interlocking tilted stone slabs framing a diamond spark, crisp alabaster ivory and amber gold on a midnight slate solid backdrop",
    ),
    (
        "Line Art",
        "Uniform monoline continuous-stroke infinity knot twisted around a Gothic pointed arch diamond, deep crimson vermilion and warm graphite on a light parchment solid backdrop",
    ),
]


def _strip_brand_tokens_for_logo(text: str, brand_name: str, logo_prompt: str = "") -> str:
    """Sanitize logo prompt via Z-Image KB hardening while protecting visual material words."""
    out = harden_zimage_prompt(str(text or ""), brand=brand_name)
    out = _LOGO_LITERAL_STOPWORDS_RE.sub("", out)
    out = re.sub(r"\s*['\"]\s*['\"]\s*", " ", out)
    out = re.sub(r"\s*,\s*(?:,\s*)+", ", ", out)
    return re.sub(r"\s+", " ", out).strip(" ,.;:-")


def _default_logo_base_prompt(brand_name: str, description: str, logo_prompt: str, lang: str) -> str:
    raw_mood = _strip_brand_tokens_for_logo(logo_prompt or description or "", brand_name)
    raw_mood = re.sub(r"[^A-Za-z0-9 ,.-]+", " ", raw_mood)
    mood = " ".join(raw_mood.split())[:160].strip(" ,.-")
    if not mood:
        mood = "architectural precision arch, Baltic heritage geometry, minimalist balanced negative space"
    return (
        f"Flat vector graphic symbol inspired by {mood}: one clean centered pictorial emblem on a solid matte backdrop, "
        "bold Swiss Bauhaus geometry, two crisp high-contrast colors, pure iconographic silhouette, balanced negative space."
    )


def _default_logo_variant_prompts(
    brand_name: str,
    description: str,
    logo_prompt: str,
    lang: str,
) -> list[str]:
    """Six structurally & chromatographically distinct symbol-only fallback prompts for Z-Image-Turbo."""
    ctx_words = _strip_brand_tokens_for_logo(f"{logo_prompt} {description}", brand_name)
    ascii_cue = " ".join(re.findall(r"[A-Za-z0-9-]+", ctx_words))[:90].strip()
    cue_tail = f" Subtle thematic inspiration: {ascii_cue}." if len(ascii_cue) >= 6 else ""
    out: list[str] = []
    for _style, lead in _LOGO_FALLBACK_SPECS:
        p = (
            f"{lead}.{cue_tail} Pure iconographic graphic symbol, sharp anti-aliased vector edges, "
            "generous breathing room around the central mark, unmistakable silhouette at 32px, minimalist Swiss design."
        )
        out.append(_strip_brand_tokens_for_logo(p, brand_name, logo_prompt))
    return out


def _expand_logo_prompt_with_llm(
    state: Any,
    brand_name: str,
    description: str,
    logo_prompt: str,
    lang: str,
) -> tuple[list[str], str]:
    """Ask SmartLLM-v2 for 6 truly different visual logo concepts in a single structured call."""
    if not (logo_prompt.strip() or description.strip() or brand_name.strip()) or not _can_use_gpu(state):
        return [], "human"
    target_lang = "Russian" if str(lang).lower().startswith("ru") else "English"
    sys_msg = (
        "You are an acclaimed Senior Brand Identity Director (Pentagram / Chermayeff & Geismar / Saul Bass studio). "
        "Create SIX genuinely different flat vector graphic symbol concepts for Z-Image-Turbo (8 NFEs, --cfg-scale 1.0 positive-only). "
        "Z-Image-Turbo renders whatever words appear inside the prompt and ignores negatives, so describe ONLY pure visual forms "
        "and NEVER mention the words 'text', 'letter', 'initial', 'word', 'font', 'typography', or the client's literal name. "
        "Return ONLY valid JSON."
    )
    user_msg = (
        f"Industry / Project brief ({target_lang}): {description or brand_name}\n"
        f"Visual & Cultural Direction from User ({target_lang}): {logo_prompt or 'timeless architectural brand mark'}\n\n"
        "Translate any geographic, historical, or cultural mood (such as Koenigsberg red-brick Baltic heritage, Prussian Gothic arches, "
        "twin-river bridge geometry, amber, architectural rhythm, acoustic waves, craft tools) into PURE VISUAL SHAPES & METAPHORS.\n\n"
        "Produce EXACTLY 6 completely different graphic concepts matching these 6 styles in order:\n"
        "01 Pictogram: crisp single recognizable object / architectural symbol\n"
        "02 Negative Space: clever figure-ground illusion carved out of one bold shape\n"
        "03 Geometric Abstraction: overlapping Bauhaus circles, arcs, triangles, or angled ribs\n"
        "04 Circular Seal: symmetrical badge ring enclosing an emblem inside\n"
        "05 Bold Silhouette: heavy dark sculptural mass on light stone or luminous gold mark on deep obsidian\n"
        "06 Line Art: continuous uniform-weight monoline geometric emblem\n\n"
        "MANDATORY DIVERSITY RULES:\n"
        "- Each of the 6 prompts MUST use a DIFFERENT concrete visual subject and a DIFFERENT color palette + background polarity (mix cream/ivory, deep obsidian/slate with brass, terracotta/navy, emerald/alabaster — NEVER repeat navy-on-white!).\n"
        "- Put the physical visual object, geometry, and exact colors in the VERY FIRST 15 WORDS of each prompt.\n"
        "- NEVER spell out the client brand name, initials, letter shapes (like 'letter K'), or write 'no text'/'without letters'.\n"
        f"- Follow this canon: {ZIMAGE_LOGO_CANON_2026}\n"
        "- Length: 55-85 words per prompt in vivid natural English.\n\n"
        'Return JSON: {"concepts": [{"style": "01 Pictogram", "prompt": "..."}, {"style": "02 Negative Space", "prompt": "..."}, '
        '{"style": "03 Geometric Abstraction", "prompt": "..."}, {"style": "04 Circular Seal", "prompt": "..."}, '
        '{"style": "05 Bold Silhouette", "prompt": "..."}, {"style": "06 Line Art", "prompt": "..."}]}'
    )
    try:
        raw = state.llm.generate_structured_json(sys_msg, user_msg, max_tokens=1600)
        concepts = raw.get("concepts") if isinstance(raw, dict) else None
        if isinstance(concepts, list):
            parsed: list[str] = []
            for item in concepts:
                raw_p = item.get("prompt") if isinstance(item, dict) else (item if isinstance(item, str) else "")
                clean_p = _strip_brand_tokens_for_logo(" ".join(str(raw_p or "").split()), brand_name, logo_prompt)
                if len(clean_p) >= 40:
                    parsed.append(clean_p)
            if len(parsed) >= 3:
                return parsed[:6], "llm"
    except Exception as exc:
        try:
            (get_log_dir() / "logo-prompt-debug.log").write_text(f"logo_prompt_exc: {exc!r}\n", encoding="utf-8")
        except Exception:
            pass
    finally:
        try:
            state.llm.stop()
        except Exception:
            pass
    return [], "human"


def _prepare_logo_prompts(
    state: Any | None,
    brand_name: str,
    description: str,
    logo_prompt: str,
    lang: str,
) -> tuple[list[str], list[str], list[str], str]:
    llm_prompts, source = (
        _expand_logo_prompt_with_llm(state, brand_name, description, logo_prompt, lang)
        if state is not None
        else ([], "human")
    )
    fallback_prompts = _default_logo_variant_prompts(brand_name, description, logo_prompt, lang)
    final_prompts: list[str] = []
    seen_prefixes: set[str] = set()
    for idx in range(6):
        cand = llm_prompts[idx] if idx < len(llm_prompts) else ""
        cand = _strip_brand_tokens_for_logo(cand, brand_name, logo_prompt)
        prefix = cand[:45].lower()
        if not cand or len(cand) < 40 or prefix in seen_prefixes:
            cand = fallback_prompts[idx]
            prefix = cand[:45].lower()
        seen_prefixes.add(prefix)
        final_prompts.append(cand)
    return final_prompts, list(LOGO_STYLES_RU), list(LOGO_STYLES_EN), source


def _set_logo_progress(state: Any | None, percent: int, msg_ru: str, msg_en: str) -> None:
    if state is None or not hasattr(state, "orchestrator"):
        return
    state.orchestrator.active_status.update(
        {
            "running": True,
            "stage": "3_visuals",
            "progress": max(0, min(100, int(percent))),
            "message_ru": msg_ru,
            "message_en": msg_en,
        }
    )


def generate_six_logo_variants_512(
    brand_name: str,
    description: str,
    out_dir: Path,
    batch_id: str | None = None,
    state: Any | None = None,
    logo_prompt: str = "",
    lang: str = "ru",
) -> dict[str, Any]:
    """Generate 6 distinct 512x512 brand logo variants (real Z-Image sd-cli on GPU, Pillow fallback in CPU tests)."""
    if state is not None and not _can_use_gpu(state) and not is_cpu_test_mode() and not state.llm.is_healthy():
        raise RuntimeError(_gpu_unavailable_message(state))
    bid = batch_id or f"lbatch_{uuid.uuid4().hex[:8]}"
    batch_dir = out_dir / bid
    batch_dir.mkdir(parents=True, exist_ok=True)
    initials = _extract_initials(brand_name)

    variants: list[dict[str, Any]] = []
    used_zimage = False
    gpu_error: str | None = None
    _set_logo_progress(state, 5, "Анализ бренда и подготовка логотипа...", "Analyzing the brand and preparing the logo...")
    prompts, style_labels_ru, style_labels_en, prompt_source = _prepare_logo_prompts(state, brand_name, description, logo_prompt, lang)
    _set_logo_progress(state, 35, "Промпт готов. Освобождаем GPU под Z-Image...", "Prompt ready. Releasing the GPU for Z-Image...")
    if _can_use_gpu(state):
        try:
            state.llm.stop()
        except Exception:
            pass

    if _can_use_gpu(state) and hasattr(state, "image_jobs") and state.image_jobs._has_real_sd_weights():
        sd_trimmer: _PageCacheTrimmer | None = None
        try:
            _set_logo_progress(state, 45, "Выгрузка LLM и захват GPU...", "Unloading the LLM and acquiring the GPU...")
            state.llm.stop()
            state.gpu.acquire_or_raise()
            state.gpu.transition(state.image_jobs.gpu.state.__class__.IMAGE_RUNNING)
            _set_logo_progress(state, 55, "Z-Image рендерит 6 вариантов 512×512...", "Z-Image is rendering 6 variants at 512x512...")
            base_seed = (int(uuid.uuid4().hex[:6], 16) % 900000) + 1000
            batch_items = [
                {
                    "id": f"logo_{idx + 1}",
                    "prompt": prompts[idx],
                    "width": 512,
                    "height": 512,
                    "steps": 8,
                    "cfg_scale": 1.0,
                    "seed": base_seed + idx * 7919,
                    "output_path": str(batch_dir / f"logo_{idx + 1}.png"),
                }
                for idx in range(6)
            ]
            manifest_path = batch_dir / "logo_batch_manifest.json"
            manifest_path.write_text(json.dumps(batch_items, indent=2), encoding="utf-8")

            img_mgr = state.image_jobs
            sd_trimmer = _PageCacheTrimmer(
                [p for p in (img_mgr.dit_model_path, img_mgr.te_model_path, img_mgr.vae_model_path) if p],
                interval_sec=0.25,
            )
            sd_trimmer.start()
            cmd = [
                str(img_mgr.sd_cli_bin),
                "--diffusion-model",
                str(img_mgr.dit_model_path),
                "--llm",
                str(img_mgr.te_model_path),
                "--vae",
                str(img_mgr.vae_model_path),
                "--type",
                "q8_0",
                "--clip-on-cpu",
                "--vae-tiling",
                "--sampling-method",
                "euler",
                "--flow-shift",
                "3.0",
                "--steps",
                "8",
                "--cfg-scale",
                "1.0",
                "-W",
                "512",
                "-H",
                "512",
                "-p",
                batch_items[0]["prompt"],
                "-o",
                batch_items[0]["output_path"],
                "--batch-json",
                str(manifest_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900.0, check=False, **subprocess_kwargs())
            if res.returncode == 0 and all((batch_dir / f"logo_{i + 1}.png").exists() for i in range(6)):
                used_zimage = True
                _set_logo_progress(state, 92, "Сохраняем 6 вариантов логотипа...", "Saving 6 logo variants...")
                for idx in range(6):
                    fname = f"logo_{idx + 1}.png"
                    fpath = batch_dir / fname
                    variants.append(
                        {
                            "index": idx,
                            "filename": fname,
                            "path": str(fpath),
                            "url": f"/api/logo/files/{bid}/{fname}",
                            "width": 512,
                            "height": 512,
                            "label_ru": style_labels_ru[idx],
                            "label_en": style_labels_en[idx],
                            "engine": "zimage",
                        }
                    )
        except Exception as exc:
            variants = []
            gpu_error = "Z-Image sd-cli timed out after 900s" if isinstance(exc, subprocess.TimeoutExpired) else f"Z-Image sd-cli failed: {exc}"
            if hasattr(state, "orchestrator"):
                state.orchestrator.active_status["last_error"] = gpu_error
        finally:
            if sd_trimmer is not None:
                sd_trimmer.stop()
            try:
                state.gpu.release_lock()
                from .engines.gpu import GPUState
                state.gpu.transition(GPUState.IDLE)
                if hasattr(state, "orchestrator"):
                    state.orchestrator.active_status.update(
                        {
                            "running": False,
                            "stage": "idle",
                            "progress": 100,
                            "message_ru": "Логотипы готовы",
                            "message_en": "Logos ready",
                            "tasks": [],
                            "last_error": None,
                        }
                    )
            except Exception:
                pass

    if used_zimage and len(variants) == 6:
        return {
            "batch_id": bid,
            "brand_name": brand_name,
            "dimensions": "512x512",
            "engine": "zimage_sd_cli",
            "prompt_source": prompt_source,
            "base_prompt": prompts[0],
            "variants": variants,
        }

    if _can_use_gpu(state) and hasattr(state, "image_jobs") and state.image_jobs._has_real_sd_weights() and not used_zimage:
        msg = gpu_error or "Z-Image did not return 6 variants"
        if hasattr(state, "orchestrator"):
            state.orchestrator.active_status.update(
                {
                    "running": False,
                    "stage": "idle",
                    "progress": 100,
                    "message_ru": "Ошибка рендера логотипов",
                    "message_en": "Logo render failed",
                    "tasks": [],
                    "last_error": msg,
                }
            )
        return {
            "batch_id": bid,
            "brand_name": brand_name,
            "dimensions": "512x512",
            "prompt_source": prompt_source,
            "base_prompt": prompts[0],
            "variants": [],
            "error": msg,
        }

    variants = []
    _set_logo_progress(state, 75, "GPU недоступен: готовим локальный предпросмотр...", "GPU unavailable: preparing a local preview...")
    try:
        from PIL import Image, ImageDraw, ImageFont

        font_paths = _logo_font_candidates()
        ttf_file: Path | None = None
        for fp in font_paths:
            if fp.is_file():
                ttf_file = fp
                break

        for idx in range(6):
            bg, acc1, acc2 = _seed_colors_from_text(f"{brand_name} {description}", idx)
            im = Image.new("RGB", (512, 512), bg)
            draw = ImageDraw.Draw(im)

            # Subtle background architectural grid
            grid_col = (min(255, bg[0] + 14), min(255, bg[1] + 16), min(255, bg[2] + 20))
            for g in range(64, 512, 64):
                draw.line([(g, 32), (g, 480)], fill=grid_col, width=1)
                draw.line([(32, g), (480, g)], fill=grid_col, width=1)

            # Outer precision frame
            draw.rounded_rectangle([28, 28, 484, 484], radius=48, outline=acc1, width=4)
            draw.rounded_rectangle([42, 42, 470, 470], radius=38, outline=grid_col, width=2)

            cx, cy = 256, 232
            if idx == 0:
                # Swiss square & offset frame
                draw.rectangle([126, 102, 386, 362], outline=acc2, width=6)
                draw.rectangle([146, 122, 366, 342], outline=acc1, width=3)
                draw.line([(126, 102), (170, 146)], fill=acc2, width=4)
                draw.line([(386, 102), (342, 146)], fill=acc2, width=4)
            elif idx == 1:
                # Isometric diamond prism
                pts_outer = [(cx, 84), (404, cy), (cx, 380), (108, cy)]
                pts_inner = [(cx, 124), (364, cy), (cx, 340), (148, cy)]
                draw.polygon(pts_outer, outline=acc1, width=6)
                draw.polygon(pts_inner, outline=acc2, width=3)
            elif idx == 2:
                # Bauhaus concentric circles & diagonal bar
                draw.ellipse([108, 84, 404, 380], outline=acc1, width=6)
                draw.ellipse([148, 124, 364, 340], outline=acc2, width=4)
                draw.line([(136, 348), (376, 116)], fill=acc1, width=4)
            elif idx == 3:
                # Radial orbital rings
                for r, col, w in ((148, acc1, 5), (118, acc2, 3), (88, acc1, 2)):
                    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=w)
                for ang in range(0, 360, 45):
                    rad = math.radians(ang)
                    x1, y1 = cx + int(118 * math.cos(rad)), cy + int(118 * math.sin(rad))
                    x2, y2 = cx + int(148 * math.cos(rad)), cy + int(148 * math.sin(rad))
                    draw.line([(x1, y1), (x2, y2)], fill=acc2, width=3)
            elif idx == 4:
                # Heraldic crest shield
                shield = [(136, 96), (376, 96), (376, 248), (cx, 384), (136, 248)]
                draw.polygon(shield, outline=acc2, width=6)
                shield_in = [(156, 114), (356, 114), (356, 240), (cx, 358), (156, 240)]
                draw.polygon(shield_in, outline=acc1, width=3)
            else:
                # Hexagonal matrix
                for radius, col, w in ((148, acc1, 6), (112, acc2, 3)):
                    hex_pts = [
                        (cx + int(radius * math.cos(math.radians(60 * k - 30))), cy + int(radius * math.sin(math.radians(60 * k - 30))))
                        for k in range(6)
                    ]
                    draw.polygon(hex_pts, outline=col, width=w)

            # Draw crisp monogram initials in centre and brand name caption at bottom
            try:
                f_big = ImageFont.truetype(str(ttf_file), 96) if ttf_file else ImageFont.load_default()
                f_sub = ImageFont.truetype(str(ttf_file), 22) if ttf_file else ImageFont.load_default()
            except Exception:
                f_big = ImageFont.load_default()
                f_sub = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), initials, font=f_big)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((cx - tw // 2, cy - th // 2 - 8), initials, fill=acc2, font=f_big)

            short_brand = (brand_name or "SMARTLLM").strip().upper()[:22]
            bbox_b = draw.textbbox((0, 0), short_brand, font=f_sub)
            bw = bbox_b[2] - bbox_b[0]
            draw.text((256 - bw // 2, 418), short_brand, fill=(236, 238, 243), font=f_sub)

            fname = f"logo_{idx + 1}.png"
            fpath = batch_dir / fname
            im.save(fpath, "PNG", optimize=True)
            variants.append(
                {
                    "index": idx,
                    "filename": fname,
                    "path": str(fpath),
                    "url": f"/api/logo/files/{bid}/{fname}",
                    "width": 512,
                    "height": 512,
                    "label_ru": style_labels_ru[idx],
                    "label_en": style_labels_en[idx],
                }
            )
    except Exception:
        for idx in range(6):
            fname = f"logo_{idx + 1}.png"
            fpath = batch_dir / fname
            make_synthetic_png(fpath, width=512, height=512, seed_shift=idx + 1)
            variants.append(
                {
                    "index": idx,
                    "filename": fname,
                    "path": str(fpath),
                    "url": f"/api/logo/files/{bid}/{fname}",
                    "width": 512,
                    "height": 512,
                    "label_ru": style_labels_ru[idx],
                    "label_en": style_labels_en[idx],
                }
            )

    if state is not None and hasattr(state, "orchestrator"):
        state.orchestrator.active_status.update(
            {
                "running": False,
                "stage": "idle",
                "progress": 100,
                "message_ru": "Логотипы готовы",
                "message_en": "Logos ready",
                "tasks": [],
                "last_error": None,
            }
        )
    return {
        "batch_id": bid,
        "brand_name": brand_name,
        "dimensions": "512x512",
        "prompt_source": prompt_source,
        "base_prompt": prompts[0],
        "variants": variants,
    }


def auto_plan_from_prompt(prompt: str, lang_pref: str = "auto", repo_root: Path | None = None) -> dict[str, Any]:
    """Orchestrator Stage 1: Analyze user prompt and auto-plan style, pages, blocks, and block descriptions."""
    root = (repo_root or DEFAULT_REPO_ROOT).resolve()
    selector = get_rag_selector(repo_root=root)
    clean_prompt = " ".join((prompt or "").strip().split()) or "Современная цифровая платформа и студия разработки"
    resolved_lang = detect_language(clean_prompt, explicit_lang=lang_pref)
    rag = selector.select(brief=clean_prompt, lang=resolved_lang)
    card = rag["canon_card"]

    # Extract or synthesize brand name from quotes or leading words
    q_match = re.search(r"[«\"']([^«»\"']{2,36})[»\"']", clean_prompt)
    if q_match:
        brand_name = q_match.group(1).strip()
    else:
        words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9-]+", clean_prompt) if len(w) > 2]
        brand_name = " ".join(words[:3]).title() if words else ("Ателье Проектов" if resolved_lang == "ru" else "Atelier Studio")

    lower = clean_prompt.lower()
    is_multi = any(w in lower for w in ("многостранич", "несколько страниц", "каталог", "портал", "multi-page", "multipage", "pages", "корпоративн"))

    # Select page types typical for a corporate multi-page site, then page-specific blocks.
    selected_pages: list[str] = ["index", "about", "services", "portfolio"]
    if any(w in lower for w in ("цен", "тариф", "стоимост", "пакет", "купить", "price", "pricing", "tier", "cost", "plan")):
        selected_pages.append("pricing")
    if any(w in lower for w in ("блог", "стат", "новост", "материал", "blog", "article", "news", "insight")):
        selected_pages.append("blog")
    if any(w in lower for w in ("команд", "эксперт", "специалист", "team", "expert", "people", "specialist", "engineer", "architect")):
        selected_pages.append("team")
    if any(w in lower for w in ("вопрос", "faq", "q&a")):
        selected_pages.append("faq")
    selected_pages.append("contact")
    if any(w in lower for w in ("политик", "документ", "условия", "legal", "privacy", "terms")):
        selected_pages.append("legal")
    selected_pages = list(dict.fromkeys(selected_pages))

    blocks = ["hero", "features"]
    if any(w in lower for w in ("показател", "метрик", "статист", "цифр", "sla", "latency", "metric", "stat", "uptime", "%")):
        blocks.append("stats")
    if any(w in lower for w in ("галере", "фото", "портфолио", "визуал", "интерьер", "дизайн", "резиденц", "gallery", "portfolio", "photo", "visual")):
        blocks.append("gallery")
    else:
        blocks.append("about")
    if any(w in lower for w in ("цен", "тариф", "стоимост", "пакет", "price", "pricing", "tier", "cost", "$", "₽")):
        blocks.append("pricing")
    if any(w in lower for w in ("отзыв", "кейс", "клиент", "review", "case", "testimonial")):
        blocks.append("testimonials")
    if any(w in lower for w in ("команд", "эксперт", "team", "expert")):
        blocks.append("team")
    if any(w in lower for w in ("блог", "стат", "новост", "blog", "article", "news")):
        blocks.append("blog")
    if any(w in lower for w in ("этап", "процесс", "process", "step", "timeline")):
        blocks.append("process")
    blocks.extend(["faq", "contact", "footer"])
    dedup_blocks: list[str] = []
    for b in blocks:
        if b not in dedup_blocks:
            dedup_blocks.append(b)

    page_blocks = default_page_blocks(selected_pages)
    page_blocks["index"] = [b for b in dedup_blocks if b != "footer"]
    for slug in selected_pages:
        page_blocks[slug] = [b for b in page_blocks.get(slug, []) if b in page_available_blocks(slug)]
        if "footer" not in page_blocks[slug]:
            page_blocks[slug].append("footer")
    page_blocks = clean_page_blocks(page_blocks, selected_pages)
    if not is_multi:
        selected_pages = ["index"]
        page_blocks = clean_page_blocks({"index": [b for b in dedup_blocks if b != "footer"]}, selected_pages)

    all_blocks: list[str] = []
    for slug in selected_pages:
        for bid in page_blocks.get(slug, []):
            if bid != "footer" and bid not in all_blocks:
                all_blocks.append(bid)
    company = build_default_company(brand_name, clean_prompt, resolved_lang)
    page_block_prompts = build_page_block_prompts(brand_name, clean_prompt, page_blocks, resolved_lang, company)
    block_prompts = build_default_block_descriptions(brand_name, clean_prompt, all_blocks, resolved_lang, company)
    routes = build_routes_from_pages(selected_pages, page_blocks, resolved_lang)

    return {
        "name": brand_name,
        "brief": clean_prompt,
        "goal": clean_prompt,
        "languages": resolved_lang,
        "canon_id": card["id"],
        "canon_name": card["name"],
        "site_type": "multi" if is_multi else "single",
        "selected_pages": selected_pages,
        "page_blocks": page_blocks,
        "selected_blocks": all_blocks,
        "company": company,
        "page_block_prompts": page_block_prompts,
        "block_prompts": block_prompts,
        "routes": routes,
        "ai_crawlers": dict(AI_CRAWLERS_DEFAULT),
    }


def build_default_block_descriptions(
    brand_name: str,
    brief: str,
    blocks: list[str],
    lang: str = "ru",
    company: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Generate sensible, editable per-block content descriptions from the site brief."""
    clean_b = " ".join((brief or "").strip().split()).rstrip(".,;:")
    company = company or build_default_company(brand_name, brief, lang)
    if lang == "ru":
        defaults = {
            "hero": f"{brand_name} — {clean_b}. Главный акцент на качестве, точных сроках и понятном результате для клиента.",
            "manifesto": company_block_prompt(company, "manifesto", lang) or f"{brand_name} — {clean_b}.",
            "values": company_block_prompt(company, "values", lang),
            "priorities": company_block_prompt(company, "priorities", lang),
            "locations": company_block_prompt(company, "locations", lang),
            "features": company_block_prompt(company, "features", lang) or f"Ключевые направления «{brand_name}»: индивидуальное проектирование под задачу | проверенные материалы и технологии | прозрачный контроль каждого этапа | сопровождение после запуска",
            "about": f"О проекте «{brand_name}»: {clean_b}. Прозрачная архитектура проекта | предметная документация | прямая связь с рабочей группой.",
            "stats": company_block_prompt(company, "stats", lang) or "10+ — лет практики | 120+ — реализованных проектов | 100% — контроль сметы | 4.9/5 — средняя оценка",
            "gallery": f"Визуальная витрина проектов «{brand_name}» | Крупные планы деталей, материалы и готовые решения",
            "pricing": company_block_prompt(company, "pricing", lang) or "Базовый пакет — старт и консультация — 15 000 ₽ | Под ключ — полная разработка и внедрение — 80 000 ₽ | Сопровождение — индивидуальное ведение — 200 000 ₽",
            "testimonials": f"Кейс «{brand_name}»: запуск по согласованному ТЗ без доплат | Повторный проект: авторский надзор и точные сроки | Сдача документации и пост-поддержка",
            "process": company_block_prompt(company, "process", lang) or "01 Запрос — бриф и аудит | 02 Архитектура — концепция и смета | 03 Реализация — производство и сборка | 04 Сдача — запуск и поддержка",
            "team": company_block_prompt(company, "team", lang) or "Андрей Смирнов — руководитель практики | Ольга Кузнецова — ведущий инженер | Павел Захаров — руководитель проектов | Наталья Белова — ведущий методолог",
            "blog": "Как выбрать формат проекта — разбираем критерии и бюджет | 5 ошибок на старте — чек-лист для заказчика | Материалы и сроки — что важно учесть",
            "faq": f"Как строится работа с «{brand_name}»? Работаем по прозрачному плану от брифа до готового результата. | Какие сроки выполнения? Сроки фиксируются перед стартом каждого этапа. | Что входит в итоговую сдачу? Полный комплект готовых материалов и поддержка.",
            "cta": f"Обсудим проект «{brand_name}»? Оставьте заявку — вернёмся с планом и сметой.",
            "contact": company_block_prompt(company, "contact", lang) or f"Оставьте заявку на расчёт проекта в «{brand_name}» — ответим с предметным планом и сметой.",
            "legal": "Политика конфиденциальности: собираем только данные, необходимые для обработки заявки. | Условия использования: материалы сайта защищены авторским правом. | Реквизиты: полные данные компании доступны по запросу.",
            "footer": f"© {brand_name}. Все права защищены. Автоматическая сборка с проверенной разметкой SEO / AEO / GEO.",
        }
    else:
        defaults = {
            "hero": f"{brand_name} — {clean_b}. Engineered for measurable quality, clarity, and reliable delivery.",
            "manifesto": company_block_prompt(company, "manifesto", lang) or f"{brand_name} — {clean_b}.",
            "values": company_block_prompt(company, "values", lang),
            "priorities": company_block_prompt(company, "priorities", lang),
            "locations": company_block_prompt(company, "locations", lang),
            "features": company_block_prompt(company, "features", lang) or f"Tailored Architecture — scoped for {brand_name} | Verified Engineering — audited workflows | Fixed Milestones — transparent pricing | Post-Launch Support — complete documentation",
            "about": f"About {brand_name}: {clean_b} | Structured specification workflow | High-contrast visual craft and direct principal oversight",
            "stats": company_block_prompt(company, "stats", lang) or "8+ — years of practice | 120+ — delivered projects | 100% — schedule predictability | 4.9/5 — average rating",
            "gallery": f"Architectural overview of {brand_name} flagship delivery | Close-up hardware and engineering craft details",
            "pricing": company_block_prompt(company, "pricing", lang) or "Starter Tier — Initial audit & blueprint — $490 | Standard Turnkey — Full implementation — $2,400 | Enterprise Retainer — Custom engineering & SLA — $6,500",
            "testimonials": f"Enterprise delivery for {brand_name}: verified architecture handoff | Multi-stage rollout with zero unscheduled downtime | Documented production transfer and SLA",
            "process": company_block_prompt(company, "process", lang) or "01 Scoping — brief & audit | 02 Design — architecture & estimate | 03 Delivery — production & QA | 04 Handover — launch & SLA",
            "team": company_block_prompt(company, "team", lang) or "Daniel Weber — Managing Director | Hannah Lindner — Principal Engineer | Thomas Becker — Operations Lead | Claire Laurent — Client Advisory Lead",
            "blog": "How to choose the right project format — criteria and budget | Five mistakes at kickoff — a client checklist | Materials and timelines — what to plan for",
            "faq": f"How does {brand_name} structure projects? Every engagement follows a clear stage-gate plan. | What is delivered at handoff? Complete production assets and documentation. | Can we customize modules? Yes, every section and route is modular.",
            "cta": f"Let's discuss your {brand_name} project — leave a request and receive a tailored plan and estimate.",
            "contact": company_block_prompt(company, "contact", lang) or f"Request a project consultation with {brand_name} — receive a tailored scope and timeline.",
            "legal": "Privacy policy: we collect only the data required to process your request. | Terms of use: all site materials are protected by copyright. | Company details are available on request.",
            "footer": f"© {brand_name}. All rights reserved. Built with automated SEO / AEO / GEO & strict CSP.",
        }
    return {b: defaults.get(b, clean_b) for b in blocks}


def build_page_block_prompts(
    brand_name: str,
    brief: str,
    page_blocks: dict[str, list[str]],
    lang: str = "ru",
    company: dict[str, Any] | None = None,
) -> dict[str, dict[str, str]]:
    """Build editable per-page block copy; foundational blocks use the company foundation."""
    company = company or build_default_company(brand_name, brief, lang)
    out: dict[str, dict[str, str]] = {}
    for slug, blocks in page_blocks.items():
        defaults = build_default_block_descriptions(brand_name, brief, [b for b in blocks if b != "footer"], lang, company)
        out[slug] = {b: defaults.get(b, brief) for b in blocks if b != "footer"}
    return out


def _generate_site_plan_with_llm(
    state: Any,
    brand_name: str,
    brief: str,
    blocks: list[str],
    lang: str,
) -> dict[str, str]:
    """Use real SmartLLM-v2 llama-server to author bespoke website copy + Z-Image prompt."""
    if not _can_use_gpu(state) and not (state and state.llm.is_healthy()):
        if is_cpu_test_mode():
            return {}
        raise RuntimeError(_gpu_unavailable_message(state))
    target_lang = "Russian" if str(lang).startswith("ru") else "English"
    sys_msg = (
        f"You are SmartLLM v2 Web Architect & Copywriter. Write crisp, specific, authentic {target_lang} copy "
        "tailored strictly to the user's project brief. Avoid generic clichés. Return ONLY valid JSON."
    )
    examples = {
        "features": "Feature 1 — detail | Feature 2 — detail | Feature 3 — detail",
        "about": "Brief company story and methodology | Metric/fact 1 | Metric/fact 2",
        "stats": "Value 1 — label | Value 2 — label | Value 3 — label",
        "gallery": "Caption for primary project visual | Caption for craft/brand visual",
        "pricing": "Tier 1: scope & price | Tier 2: scope & price | Tier 3: scope & price",
        "testimonials": "Client case 1 outcome | Client case 2 outcome | Client case 3 outcome",
        "process": "01 Step name — outcome | 02 Step name — outcome | 03 Step name — outcome | 04 Step name — outcome",
        "team": "Name — role | Name — role | Name — role",
        "blog": "Article title — one-line summary | Article title — one-line summary | Article title — one-line summary",
        "faq": "Question 1? Detailed answer 1 | Question 2? Detailed answer 2 | Question 3? Detailed answer 3",
        "cta": "Short conversion sentence with a clear next step",
        "contact": "Brief call to action for contact form",
        "legal": "Policy paragraph 1 | Terms paragraph 2 | Company details paragraph 3",
    }
    best = str(brief or "").strip()
    lines = [
        f"Brand name: {brand_name}",
        f"Brief: {best}",
        f"Requested sections: {', '.join(blocks)}",
        "",
        "Return a single JSON object with exact string keys:",
        "{",
        '  "brand_name": "concise brand name",',
        '  "headline": "punchy editorial H1 headline (6-12 words)",',
        '  "hero": "compelling 1-2 sentence hero subtitle",',
    ]
    for bid in blocks:
        if bid in examples:
            lines.append(f'  "{bid}": "{examples[bid]}",')
    lines.extend(
        [
            '  "hero_zimage_prompt": "Photorealistic studio photography prompt IN ENGLISH (40-70 words) visually depicting the exact business theme, physical materials, crisp directional lighting, 35mm architectural lens, clean visual composition"',
            "}",
            f"Remember: write all user-facing values in {target_lang}, and keep hero_zimage_prompt strictly in English.",
        ]
    )
    user_msg = "\n".join(lines)
    try:
        raw_obj = state.llm.generate_structured_json(sys_msg, user_msg, max_tokens=2048)
    except Exception as exc:
        try:
            (get_log_dir() / "llm-debug.log").write_text(f"site_plan_exc: {exc!r}\n", encoding="utf-8")
        except Exception:
            pass
        return {}
    out: dict[str, str] = {}
    keys = ["brand_name", "headline", *blocks, "hero_zimage_prompt"]
    for k in dict.fromkeys(keys):
        v = str(raw_obj.get(k) or "").strip()
        if v:
            out[k] = v
    return out


def _coerce_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    raw = str(value or "").strip()
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[|;\n]+", raw) if p.strip()]


def _sanitize_company(company: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    """Replace bracketed / placeholder contact values with valid-looking editable defaults."""
    out = dict(company)
    bad_markers = ("xxx", "placeholder", "плейсхолдер", "[", "]", "todo", "tbd")
    def is_bad(value: Any) -> bool:
        text = str(value or "").strip().lower()
        return (not text) or any(m in text for m in bad_markers)
    for key in ("phone", "address", "email"):
        if is_bad(out.get(key)):
            out[key] = fallback.get(key, "")
    if is_bad(out.get("phone")) or sum(ch.isdigit() for ch in str(out.get("phone") or "")) < 10:
        out["phone"] = fallback.get("phone", "")
    if is_bad(out.get("address")):
        out["address"] = fallback.get("address", "")
    if "@" not in str(out.get("email") or ""):
        out["email"] = fallback.get("email", "")
    cities = [str(x).strip() for x in (out.get("cities") or []) if str(x).strip() and not is_bad(x)]
    out["cities"] = cities or fallback.get("cities", [])
    return out


_TEMPLATE_FAKE_NAMES = ("анна воронова", "илья соколов", "elena kova", "markus thorne", "anna voronova", "ilya sokolov")
_URL_STRIP_RE = re.compile(r"(?:,\s*)?https?://\S+", re.I)


def _strip_urls(text: Any) -> str:
    return " ".join(_URL_STRIP_RE.sub("", str(text or "")).split()).strip(" ,;")


def _generate_company_with_llm(
    state: Any,
    brand_name: str,
    brief: str,
    lang: str,
) -> dict[str, Any]:
    """Generate the brand foundation, canonical team/features/stats, and contact details (single source of truth)."""
    if not _can_use_gpu(state) and not (state and state.llm.is_healthy()):
        if is_cpu_test_mode():
            return {}
        raise RuntimeError(_gpu_unavailable_message(state))
    target_lang = "Russian" if str(lang).lower().startswith("ru") else "English"
    sys_msg = (
        "You are SmartLLM v2 Brand Strategist. Establish the SINGLE SOURCE OF TRUTH for this brand: "
        "contacts, exact products/pricing tiers, core capabilities, verified metrics, workflow steps, and a fixed canonical team roster. "
        "Return ONLY valid JSON."
    )
    user_msg = (
        f"Brand name: {brand_name}\nBrief: {brief}\n\n"
        f"Write all user-facing text in {target_lang}. Be specific, no clichés.\n"
        "Rules:\n"
        "1. Extract ALL 3 or 4 products/pricing tiers (with exact currency prices) and the founding year/milestones directly from the brief when provided.\n"
        "2. Extract ALL 4 core capabilities ('features', strictly capabilities/services, NO prices here) and ALL 4 verified metrics ('stats') from the brief when provided.\n"
        "3. Create the canonical 'team' roster (4 distinct realistic specialists matching the brief count if specified; realistic First + Last names appropriate to the brand's country; explicit 'gender': 'male' or 'female'; NO URLs, NO template names).\n"
        "4. If contact details are not in the brief, invent plausible realistic local ones for the brand's city; never use 'Примерная', 'Example Street', '000-00-00', 'placeholder' or 'xxx'.\n"
        "Return JSON with exact keys:\n"
        "{\n"
        '  "tagline": "6-12 word tagline",\n'
        '  "positioning": "1-2 sentence positioning",\n'
        '  "values": ["Product: concrete standard", "Team: concrete standard", "Clients: concrete standard"],\n'
        '  "priorities": ["priority 1", "priority 2", "priority 3", "priority 4"],\n'
        '  "cities": ["city 1", "city 2"],\n'
        '  "address": "street address",\n'
        '  "phone": "+7 ... or +1 ...",\n'
        '  "email": "hello@brand-domain.tld",\n'
        '  "hours": "Mon-Fri 10:00-19:00",\n'
        '  "social": ["https://..."],\n'
        '  "products": [{"name": "tier name", "scope": "what is included", "price": "exact price with currency"}],\n'
        '  "features": [{"title": "capability name", "detail": "1 sentence technical benefit without price"}],\n'
        '  "stats": [{"value": "numeric or metric anchor", "label": "concise verified label"}],\n'
        '  "process": [{"step": "01 Step", "detail": "domain action and outcome"}],\n'
        '  "team": [{"name": "First Last", "role": "Title and 1-sentence specialty (no URLs)", "gender": "male or female"}],\n'
        '  "history": {"founded": 2017, "milestones": ["year — event", "year — event"]}\n'
        "}"
    )
    try:
        raw = state.llm.generate_structured_json(sys_msg, user_msg, max_tokens=2800)
    except Exception as exc:
        try:
            (get_log_dir() / "company-debug.log").write_text(f"company_exc: {exc!r}\n", encoding="utf-8")
        except Exception:
            pass
        return {}
    base = build_default_company(brand_name, brief, lang)
    out = dict(base)
    for key in ("tagline", "positioning", "address", "phone", "email", "hours"):
        val = str(raw.get(key) or "").strip()
        if val:
            out[key] = val
    for key in ("values", "priorities", "cities", "social"):
        vals = _coerce_str_list(raw.get(key))
        if vals:
            out[key] = vals
    products = []
    for pr in (raw.get("products") or [])[:6]:
        if isinstance(pr, dict) and _clean(pr.get("name")):
            products.append({"name": _strip_urls(_clean(pr.get("name"))), "scope": _strip_urls(_clean(pr.get("scope"))), "price": _clean(pr.get("price"))})
    if products:
        out["products"] = products
    features = []
    for ft in (raw.get("features") or [])[:4]:
        if isinstance(ft, dict) and _clean(ft.get("title")):
            features.append({"title": _strip_urls(_clean(ft.get("title"))), "detail": _strip_urls(_clean(ft.get("detail") or ft.get("scope") or ft.get("description")))})
    if len(features) >= 3:
        out["features"] = features
    stats = []
    for st in (raw.get("stats") or [])[:4]:
        if isinstance(st, dict) and _clean(st.get("value")):
            stats.append({"value": _strip_urls(_clean(st.get("value"))), "label": _strip_urls(_clean(st.get("label")))})
    if len(stats) >= 3:
        out["stats"] = stats
    proc = []
    for pr_it in (raw.get("process") or [])[:4]:
        if isinstance(pr_it, dict) and _clean(pr_it.get("step")):
            proc.append({"step": _strip_urls(_clean(pr_it.get("step"))), "detail": _strip_urls(_clean(pr_it.get("detail")))})
    if len(proc) >= 3:
        out["process"] = proc
    team = []
    seen_names: set[str] = set()
    for tm in (raw.get("team") or [])[:4]:
        if isinstance(tm, dict) and _clean(tm.get("name")):
            t_name = _strip_urls(_clean(tm.get("name")))
            low_n = t_name.lower()
            if not t_name or low_n in seen_names or any(fn in low_n for fn in _TEMPLATE_FAKE_NAMES):
                continue
            seen_names.add(low_n)
            t_role = _strip_urls(_clean(tm.get("role") or tm.get("bio") or tm.get("description")))
            team.append({"name": t_name, "role": t_role, "gender": infer_gender(t_name, str(tm.get("gender") or ""), len(team))})
    if len(team) >= 3:
        out["team"] = team
    hist = raw.get("history") or {}
    if isinstance(hist, dict):
        founded = hist.get("founded")
        miles = _coerce_str_list(hist.get("milestones"))
        if founded or miles:
            out["history"] = {"founded": int(founded) if str(founded).isdigit() else base.get("history", {}).get("founded"), "milestones": miles[:4]}
    return _sanitize_company(out, base)


def _generate_page_prompts_with_llm(
    state: Any,
    brand_name: str,
    brief: str,
    page_blocks: dict[str, list[str]],
    lang: str,
    company: dict[str, Any],
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    """Generate per-page block copy one page at a time using flat keys slug::block for reliable local-model parsing."""
    if not _can_use_gpu(state) and not (state and state.llm.is_healthy()):
        if is_cpu_test_mode():
            return {}, {"_failed_pages": []}
        raise RuntimeError(_gpu_unavailable_message(state))
    target_lang = "Russian" if str(lang).lower().startswith("ru") else "English"
    active_pages: list[tuple[str, list[str]]] = [
        (slug, [bid for bid in blocks if bid != "footer"])
        for slug, blocks in page_blocks.items()
    ]
    active_pages = [(slug, blks) for slug, blks in active_pages if blks]
    if not active_pages:
        return {}, {"_failed_pages": []}
    hints = {
        "manifesto": "Tagline | one positioning sentence",
        "values": "Product: ... | Team: ... | Clients: ...",
        "priorities": "Priority | Priority | Priority | Priority",
        "locations": "City | City | full street address | working hours",
        "contact": "phone | email | address | working hours",
        "faq": "Question? Answer | Question? Answer | Question? Answer",
        "process": "01 Step — outcome | 02 Step — outcome | 03 Step — outcome",
        "team": "Name — role | Name — role | Name — role",
        "blog": "Article title — one-line summary | Article title — one-line summary",
        "stats": "Value — label | Value — label | Value — label",
        "pricing": "Tier: scope & price | Tier: scope & price | Tier: scope & price",
        "features": "Feature | Feature | Feature",
        "testimonials": "Client outcome | Client outcome | Client outcome",
        "hero": "1-2 sentences",
        "cta": "one conversion sentence",
        "legal": "Paragraph | Paragraph | Paragraph",
    }
    sys_msg = (
        "You are SmartLLM v2 Web Copywriter. Write page-specific website copy for every requested key. "
        "Return ONLY valid JSON."
    )
    from .pipeline import _norm_block_value
    out: dict[str, dict[str, str]] = {}
    meta: dict[str, Any] = {}
    failed_pages: list[str] = []
    company_json = json.dumps(company, ensure_ascii=False)
    total_pages = len(active_pages)

    for idx, (slug, page_bids) in enumerate(active_pages, start=1):
        if progress_cb is not None:
            try:
                progress_cb(idx, total_pages, slug)
            except Exception:
                pass
        flat_keys: list[str] = []
        if slug == "index":
            flat_keys.extend(["headline", "hero_zimage_prompt"])
        for bid in page_bids:
            flat_keys.append(f"{slug}::{bid}")
        format_lines = "\n".join(f"- {bid}: {hints[bid]}" for bid in dict.fromkeys(page_bids) if bid in hints)
        extra_meta = (
            "\nAdd a punchy editorial headline and an English Z-Image hero photography prompt (40-70 words, positive visual photography framing)."
            if slug == "index"
            else ""
        )
        user_msg = (
            f"Brand name: {brand_name}\nBrief: {brief}\n"
            f"Page: {page_title(slug, lang)} ({slug})\n"
            f"Brand foundation (single source of truth — keep team, products/prices, capabilities, metrics, and contacts 100% consistent across ALL pages): "
            f"{company_json}\n\n"
            f"Write all values in {target_lang}. Keep each value concise and specific to the '{slug}' page. "
            "Use the brand foundation for manifesto, values, priorities, locations, team, pricing, and contact. "
            "Never put pricing tiers into 'features'; put pricing ONLY in 'pricing'. Separate list items with ' | '. Every value MUST be a plain string.\n"
            "Required format per block type:\n"
            f"{format_lines}\n"
            "FAQ must always be 'Question? Answer' pairs, never questions alone.\n"
            "Return one JSON object with exactly these keys (flat slug::block):\n"
            + "\n".join(f'- "{k}"' for k in flat_keys)
            + extra_meta
        )
        try:
            raw = state.llm.generate_structured_json(sys_msg, user_msg, max_tokens=2048)
        except Exception as exc:
            failed_pages.append(slug)
            try:
                log_path = get_log_dir() / "page-prompts-debug.log"
                with log_path.open("a", encoding="utf-8") as fh:
                    fh.write(f"page_prompts_exc[{slug}]: {exc!r}\n")
            except Exception:
                pass
            continue
        if not isinstance(raw, dict) or not raw:
            failed_pages.append(slug)
            continue
        parsed_count = 0
        for key, value in raw.items():
            if key in ("headline", "hero_zimage_prompt"):
                text = _clean(value)
                if text:
                    meta[key] = text
                continue
            k_str = str(key)
            if "::" in k_str:
                k_slug, bid = k_str.split("::", 1)
            elif k_str in page_bids:
                k_slug, bid = slug, k_str
            else:
                continue
            if k_slug == slug and bid in page_bids:
                text = _norm_block_value(bid, value)
                if text:
                    out.setdefault(slug, {})[bid] = text
                    parsed_count += 1
        if parsed_count == 0:
            failed_pages.append(slug)

    meta["_failed_pages"] = failed_pages
    return out, meta


def autofill_blocks_smart(
    state: Any,
    brand_name: str,
    brief: str,
    blocks: list[str],
    lang: str = "ru",
    page_blocks: dict[str, list[str]] | None = None,
    company: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate block descriptions using SmartLLM-v2 when GPU is available, else deterministic template."""
    norm_lang = resolve_primary_lang(lang, f"{brand_name} {brief}")
    if hasattr(state, "orchestrator"):
        state.orchestrator.active_status = {
            "running": True,
            "stage": "2_blocks",
            "message_ru": "Запуск текстовой нейросети для описания блоков...",
            "message_en": "Running SmartLLM to author block descriptions...",
            "tasks": [{"id": "2_blocks", "status": "running"}],
        }
    page_blocks = page_blocks or {"index": list(blocks)}
    company = dict(company or build_default_company(brand_name, brief, norm_lang))

    def set_progress(pct: int, msg_ru: str, msg_en: str) -> None:
        if hasattr(state, "orchestrator"):
            state.orchestrator.active_status.update(
                {"running": True, "stage": "2_blocks", "progress": pct, "message_ru": msg_ru, "message_en": msg_en, "tasks": [{"id": "2_blocks", "status": "running"}]}
            )

    try:
        set_progress(10, "Анализ бренда и подготовка бренд-основы...", "Analyzing the brand and preparing the foundation...")
        fallback_company = build_default_company(brand_name, brief, norm_lang)
        llm_company = _generate_company_with_llm(state, brand_name, brief, norm_lang)
        if llm_company:
            company = {**fallback_company, **llm_company}
        set_progress(45, "Бренд-основа готова. Генерируем блоки по страницам...", "Brand foundation ready. Generating page-specific blocks...")
        fallback_pages = build_page_block_prompts(brand_name, brief, page_blocks, norm_lang, company)

        def on_page_progress(idx: int, total: int, slug: str) -> None:
            pct = 45 + int(47 * idx / max(1, total))
            set_progress(
                pct,
                f"Генерируем страницу {idx}/{total}: {page_title(slug, 'ru')}...",
                f"Generating page {idx}/{total}: {page_title(slug, 'en')}...",
            )

        llm_pages, llm_meta = _generate_page_prompts_with_llm(
            state, brand_name, brief, page_blocks, norm_lang, company, progress_cb=on_page_progress
        )
        failed_pages = list(llm_meta.get("_failed_pages") or []) if isinstance(llm_meta, dict) else []
        warnings: list[str] = []
        if not is_cpu_test_mode():
            if not llm_company:
                warnings.append(
                    "ИИ не смог сгенерировать бренд-основу — подставлен шаблон."
                    if norm_lang == "ru"
                    else "AI could not generate the brand foundation — template fallback applied."
                )
            if failed_pages:
                pages_str = ", ".join(failed_pages)
                warnings.append(
                    f"ИИ не заполнил страницы ({pages_str}) — подставлены шаблонные тексты."
                    if norm_lang == "ru"
                    else f"AI could not fill pages ({pages_str}) — template fallback applied."
                )
        from .pipeline import _sync_page_copy_to_foundation
        page_prompts: dict[str, dict[str, str]] = {}
        for slug, page_map in fallback_pages.items():
            merged_page = {bid: llm_pages.get(slug, {}).get(bid) or text for bid, text in page_map.items()}
            page_prompts[slug] = _sync_page_copy_to_foundation(slug, merged_page, company, norm_lang, set())
        flat: dict[str, str] = {}
        for slug, page_map in page_prompts.items():
            for bid, text in page_map.items():
                if bid not in flat:
                    flat[bid] = text
        set_progress(95, "Собираем и проверяем описания...", "Merging and validating the copy...")
        return {"company": company, "page_block_prompts": page_prompts, "block_prompts": flat, "warnings": warnings}
    finally:
        if hasattr(state, "orchestrator"):
            state.orchestrator.active_status = {
                "running": False,
                "stage": "idle",
                "progress": 100,
                "message_ru": "Готово",
                "message_en": "Done",
                "tasks": [],
            }


class ProjectOrchestrator:
    """Decomposes website creation into a multi-stage sequential task pipeline with live progress."""

    def __init__(self, state: Any) -> None:
        self.state = state
        self.runs: dict[str, dict[str, Any]] = {}
        self.active_status: dict[str, Any] = {
            "running": False,
            "stage": "idle",
            "message_ru": "Готов к запуску",
            "message_en": "Ready",
            "tasks": [],
        }

    def _set_stage(self, tasks: list[dict[str, Any]], idx: int, msg_ru: str, msg_en: str, detail: str = "") -> None:
        for i, t in enumerate(tasks):
            if i < idx:
                t["status"] = "done"
            elif i == idx:
                t["status"] = "running"
                if detail:
                    t["detail"] = detail
            else:
                t["status"] = "queued"
        self.active_status = {
            "running": True,
            "stage": tasks[idx]["id"],
            "message_ru": msg_ru,
            "message_en": msg_en,
            "tasks": [dict(x) for x in tasks],
        }

    def execute_pipeline(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run the sequential sub-agent pipeline: disk memory -> isolated agents -> Z-Image -> deterministic compile -> audit."""
        from .blueprint import _safe_project_dir
        from .pipeline import _sanitize_zimage_prompt, mark_external_step, run_content_pipeline, run_final_audit

        def _clean_path_str(val: Any) -> str:
            s = str(val or "").strip()
            while len(s) >= 2 and s[0] == s[-1] and s[0] in ("`", '"', "'"):
                s = s[1:-1].strip()
            return s.strip("`\"'")

        run_id = f"orch_{uuid.uuid4().hex[:8]}"
        mode = str(payload.get("orchestrator_mode") or "constructor")
        render_images = bool(payload.get("render_images", True))
        started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        tasks: list[dict[str, Any]] = [
            {"id": "1_architect", "title_ru": "1. Оркестратор: память, архитектура, каркас", "title_en": "1. Orchestrator: Memory, Architecture, Skeleton", "status": "running", "detail": ""},
            {"id": "2_blocks", "title_ru": "2. Субагенты: hero, блоки, SEO, промпты, ревизия", "title_en": "2. Sub-agents: Hero, Blocks, SEO, Prompts, Review", "status": "queued", "detail": ""},
            {"id": "3_visuals", "title_ru": "3. Z-Image: рендер визуалов на GPU", "title_en": "3. Z-Image GPU Visual Render", "status": "queued", "detail": ""},
            {"id": "4_seo_geo", "title_ru": "4. Детерминированная сборка SEO / AEO / GEO и CSP", "title_en": "4. Deterministic SEO / AEO / GEO & CSP Compile", "status": "queued", "detail": ""},
            {"id": "5_bundle", "title_ru": "5. Запись бандла и финальный аудит", "title_en": "5. Bundle Output & Final Audit", "status": "queued", "detail": ""},
        ]

        try:
            self._set_stage(
                tasks, 0,
                "1/5: Определение структуры страниц, блоков и стиля...",
                "1/5: Planning routes, section blocks, and visual canon...",
            )
            if mode == "auto":
                raw_prompt = str(payload.get("auto_prompt") or payload.get("brief") or payload.get("goal") or "").strip()
                lang_pref = str(payload.get("languages") or "auto")
                planned = auto_plan_from_prompt(raw_prompt, lang_pref=lang_pref, repo_root=self.state.repo_root)
                merged = {**self.state.load_project("default"), **planned}
                for stale_logo_key in ("logo", "selected_logo_path", "logo_bytes_b64", "logo_filename", "logo_path"):
                    if stale_logo_key not in payload:
                        merged.pop(stale_logo_key, None)
                if payload.get("languages"):
                    merged["languages"] = str(payload["languages"])
                if payload.get("output_dir"):
                    merged["output_dir"] = _clean_path_str(payload["output_dir"])
                if payload.get("canon_id"):
                    merged["canon_id"] = str(payload["canon_id"])
                if payload.get("polarity") in ("light", "dark", "auto"):
                    merged["polarity"] = str(payload["polarity"])
                if payload.get("stack"):
                    merged["stack"] = str(payload["stack"])
                if payload.get("motion"):
                    merged["motion"] = str(payload["motion"])
            else:
                saved_def = self.state.load_project("default")
                merged = {**saved_def, **payload}
                if merged.get("output_dir"):
                    merged["output_dir"] = _clean_path_str(merged["output_dir"])
                if not any(payload.get(k) for k in ("selected_logo_path", "logo_bytes_b64", "logo_path")):
                    if _clean_path_str(saved_def.get("output_dir")) != _clean_path_str(merged.get("output_dir")):
                        for stale_logo_key in ("logo", "selected_logo_path", "logo_bytes_b64", "logo_filename", "logo_path"):
                            merged.pop(stale_logo_key, None)
                lang_pref = str(merged.get("languages") or "ru")
                default_blocks = list(merged.get("selected_blocks") or ["hero", "features", "about", "pricing", "faq", "contact"])
                site_type = str(merged.get("site_type") or "single")
                sel_pages = list(merged.get("selected_pages") or (["index"] if site_type == "single" else ["index", "about", "services", "portfolio", "pricing", "contact"]))
                if "index" not in sel_pages:
                    sel_pages.insert(0, "index")
                raw_page_blocks = merged.get("page_blocks") if isinstance(merged.get("page_blocks"), dict) else {}
                if site_type == "single":
                    page_blocks = clean_page_blocks({"index": default_blocks}, ["index"])
                else:
                    page_blocks = clean_page_blocks(raw_page_blocks or default_page_blocks(sel_pages), sel_pages)
                merged["site_type"] = "single" if site_type == "single" else "multi"
                merged["selected_pages"] = sel_pages if merged["site_type"] == "multi" else ["index"]
                merged["page_blocks"] = page_blocks
                route_lang = detect_language(str(merged.get("brief") or merged.get("goal") or merged.get("name") or ""), explicit_lang=lang_pref)
                merged["routes"] = build_routes_from_pages(merged["selected_pages"], page_blocks, route_lang)
                all_blocks: list[str] = []
                for p_slug in merged["selected_pages"]:
                    for bid in page_blocks.get(p_slug, []):
                        if bid != "footer" and bid not in all_blocks:
                            all_blocks.append(bid)
                if not all_blocks:
                    all_blocks = [b for b in default_blocks if b != "footer"]
                merged["selected_blocks"] = all_blocks
                merged["block_prompts"] = dict(payload.get("block_prompts") or {})
                merged["page_block_prompts"] = dict(payload.get("page_block_prompts") or {})
                merged["company"] = dict(payload.get("company") or {})

            seo_prev = merged.get("seo") if isinstance(merged.get("seo"), dict) else {}
            seo_keep = {k: seo_prev[k] for k in ("base_url", "llms_txt_enabled", "schema_type") if k in seo_prev}
            if isinstance(payload.get("seo"), dict):
                seo_keep.update(payload["seo"])
            merged["seo"] = seo_keep
            if "geo" in payload:
                merged["geo"] = payload["geo"]
            else:
                geo_prev = merged.get("geo") if isinstance(merged.get("geo"), dict) else {}
                merged["geo"] = {} if str(geo_prev.get("author") or "").startswith("Dr. Viktor") else geo_prev
            if "company" not in payload:
                comp_prev = merged.get("company") if isinstance(merged.get("company"), dict) else {}
                if "Quartz-Field" in str(comp_prev.get("tagline") or ""):
                    merged["company"] = {}
            if "goal" not in payload and str(merged.get("goal") or "").startswith("High-craft Astro"):
                merged["goal"] = str(merged.get("brief") or merged.get("name") or "")
            if "audience" not in payload and str(merged.get("audience") or "").startswith("Principal systems"):
                merged["audience"] = ""

            brief_for_llm = str(merged.get("brief") or merged.get("goal") or merged.get("name") or "").strip()
            norm_lang = resolve_primary_lang(str(merged.get("languages") or "ru"), brief_for_llm)
            clean_out = _clean_path_str(merged.get("output_dir"))
            out_dir = _safe_project_dir(clean_out, self.state.project_dir(str(merged.get("id") or "default")))
            merged["output_dir"] = str(out_dir)
            selector = get_rag_selector(repo_root=self.state.repo_root)
            canon_bundle = selector.select(brief=brief_for_llm, lang=norm_lang, explicit_canon_id=str(merged.get("canon_id") or ""))
            canon_card = canon_bundle.get("canon_card") or {}
            gpu_ok = _can_use_gpu(self.state)
            if not gpu_ok and not is_cpu_test_mode():
                if self.state.llm.is_healthy():
                    gpu_ok = True
                else:
                    raise RuntimeError(_gpu_unavailable_message(self.state))

            def report(_idx: int, pct: int, msg_ru: str, msg_en: str, detail: str = "") -> None:
                idx = 0 if pct < 16 else 1
                self._set_stage(tasks, idx, msg_ru, msg_en, detail)
                self.active_status["progress"] = max(0, min(100, int(pct)))

            summary = run_content_pipeline(
                self.state, merged, mode, render_images, gpu_ok, canon_card, report, stage_idx=1,
            )
            merged["company"] = summary["company"]
            merged["page_block_prompts"] = summary["page_block_prompts"]
            merged["block_prompts"] = summary["block_prompts"]
            merged["pipeline"] = summary
            merged["hero_zimage_prompt"] = summary["visuals"].get("hero")
            summary_lang = str(summary.get("lang") or norm_lang)
            primary_copy_key = "copy_ru" if summary_lang == "ru" else "copy_en"
            alt_copy_key = "copy_en" if summary_lang == "ru" else "copy_ru"
            index_page = summary["pages"].get("index") or {}
            index_hero = index_page.get("hero") or {}
            loc_index_hero = (index_page.get("loc") or {}).get("hero") or {}
            if merged.get("routes"):
                r0 = merged["routes"][0]
                if index_hero.get("headline"):
                    r0.setdefault(primary_copy_key, {})["headline"] = index_hero["headline"]
                    if index_hero.get("subhead"):
                        r0[primary_copy_key]["subhead"] = index_hero["subhead"]
                if loc_index_hero.get("headline"):
                    r0.setdefault(alt_copy_key, {})["headline"] = loc_index_hero["headline"]
                    if loc_index_hero.get("subhead"):
                        r0[alt_copy_key]["subhead"] = loc_index_hero["subhead"]
            ai_used = bool(summary["ai_used"])
            tasks[0]["status"] = "done"
            tasks[0]["detail"] = f"{merged.get('name')} · {merged.get('canon_id')} · {len(merged.get('routes', []))} стр. · smartllm.md"
            tasks[1]["status"] = "done"
            speed_suffix = f" · {self.state.gpu.tok_per_sec} tok/s" if self.state.gpu.tok_per_sec else ""
            tasks[1]["detail"] = (
                f"{summary['agents_run']} агентов · ревизия {summary['review_avg']}/6{speed_suffix}"
                if ai_used
                else f"CPU шаблон · {len(summary['page_block_prompts'])} стр. · ревизия {summary['review_avg']}/6"
            )

            self._set_stage(
                tasks, 2,
                "3/5: Освобождение GPU и рендер визуалов в Z-Image...",
                "3/5: Releasing LLM from VRAM & rendering visuals via Z-Image...",
            )
            assets_dir = out_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            selected_logo_path = merged.get("selected_logo_path")
            if selected_logo_path:
                cand_logo = Path(str(selected_logo_path)).resolve()
                allowed_roots = (self.state.projects_root.resolve(), STUDIO_ROOT.resolve())
                if cand_logo.exists() and any(cand_logo.is_relative_to(r) for r in allowed_roots):
                    from .sanitizer import ingest_brand_logo
                    logo_info = ingest_brand_logo(cand_logo.name, cand_logo.read_bytes(), assets_dir)
                    merged["logo"] = logo_info
            has_custom_logo = bool(merged.get("logo_bytes_b64") or merged.get("selected_logo_path") or merged.get("logo_path"))

            zimage_rendered = False
            auto_logo_generated = False
            gallery_images: list[str] = []
            if not render_images:
                tasks[2]["title_ru"] = "3. Дизайн блоков и визуальный план"
                tasks[2]["title_en"] = "3. Block Design & Visual Plan"
                try:
                    self.state.llm.stop()
                except Exception:
                    pass
            if render_images and gpu_ok and self.state.image_jobs._has_real_sd_weights():
                sd_trimmer: _PageCacheTrimmer | None = None
                try:
                    self.state.llm.stop()
                    self.state.gpu.acquire_or_raise()
                    from .engines.gpu import GPUState
                    self.state.gpu.transition(GPUState.IMAGE_RUNNING)
                    img_mgr = self.state.image_jobs
                    sd_trimmer = _PageCacheTrimmer(
                        [p for p in (img_mgr.dit_model_path, img_mgr.te_model_path, img_mgr.vae_model_path) if p],
                        interval_sec=0.25,
                    )
                    sd_trimmer.start()
                    visuals = summary["visuals"]
                    from .blueprint_render import _variant, load_canon_dossier
                    dossier = load_canon_dossier(str(canon_card.get("id") or merged.get("canon_id") or ""))
                    canon_aspect = str(
                        ((merged.get("zimage_direction") or {}).get("aspect_ratio"))
                        or ((canon_card.get("imagery") or {}).get("aspect_ratio"))
                        or "16:9"
                    )
                    summary_pages = summary.get("pages") if isinstance(summary.get("pages"), dict) else {}
                    team_names: list[str] = []
                    for pg_map in (summary.get("page_block_prompts") or {}).values():
                        if isinstance(pg_map, dict) and pg_map.get("team"):
                            for item_s in re.split(r"[|\n]+", str(pg_map["team"])):
                                n_part = item_s.split("—")[0].strip()
                                if n_part:
                                    team_names.append(n_part)
                    style_suffix = _sanitize_zimage_prompt(str(visuals.get("style_suffix") or ""), team_names)
                    heroes = visuals.get("heroes") or {"index": visuals.get("hero") or ""}
                    batch_items = []
                    def _join_prompt_suffix(base_p: str, suf: str) -> str:
                        clean_b = harden_zimage_prompt(str(base_p or "").strip(), brand=str(merged.get("name") or ""), member_names=team_names)
                        clean_s = str(suf or "").strip()
                        if not clean_s or re.search(r"(?i)\b(?:\d{2,3}mm|lens|softbox|daylight|shadows)\b", clean_b):
                            return clean_b
                        if clean_s[:32].lower() in clean_b.lower():
                            return clean_b
                        return harden_zimage_prompt(f"{clean_b}, {clean_s}", brand=str(merged.get("name") or ""), member_names=team_names)

                    for p_idx, h_slug in enumerate(merged.get("selected_pages") or ["index"]):
                        raw_hp = str(heroes.get(h_slug) or heroes.get("index") or f"Editorial photograph of {brief_for_llm[:140]}, crisp directional lighting, 35mm lens")
                        h_prompt = _sanitize_zimage_prompt(raw_hp, team_names)
                        h_id = "hero_primary" if h_slug == "index" else f"hero_{h_slug}"
                        pm = summary_pages.get(h_slug) if isinstance(summary_pages.get(h_slug), dict) else {}
                        hero_var = _variant(pm, dossier, "hero", p_idx)
                        hw, hh = resolve_slot_dimensions("hero", canon_aspect, hero_var)
                        batch_items.append(
                            {
                                "id": h_id,
                                "prompt": _join_prompt_suffix(h_prompt, style_suffix),
                                "width": hw,
                                "height": hh,
                                "steps": 8,
                                "cfg_scale": 1.0,
                                "seed": 42 + len(batch_items),
                                "output_path": str(assets_dir / f"{h_id}.png"),
                            }
                        )
                    gw, gh = resolve_slot_dimensions("gallery", canon_aspect)
                    for g_idx, g_prompt in enumerate(visuals.get("gallery") or []):
                        g_clean = _sanitize_zimage_prompt(str(g_prompt), team_names)
                        batch_items.append(
                            {
                                "id": f"gallery_{g_idx + 1}",
                                "prompt": _join_prompt_suffix(g_clean, style_suffix),
                                "width": gw,
                                "height": gh,
                                "steps": 8,
                                "cfg_scale": 1.0,
                                "seed": 60 + g_idx,
                                "output_path": str(assets_dir / f"gallery_{g_idx + 1}.png"),
                            }
                        )
                    tw, th = resolve_slot_dimensions("team")
                    brand_seed_offset = sum(ord(c) for c in str(merged.get("name") or "s")) % 997
                    for t_idx, t_prompt in enumerate(visuals.get("team") or []):
                        t_clean = _sanitize_zimage_prompt(str(t_prompt), team_names)
                        batch_items.append(
                            {
                                "id": f"team_{t_idx + 1}",
                                "prompt": t_clean,
                                "width": tw,
                                "height": th,
                                "steps": 8,
                                "cfg_scale": 1.0,
                                "seed": 1703 + t_idx * 977 + brand_seed_offset,
                                "output_path": str(assets_dir / f"team_{t_idx + 1}.png"),
                            }
                        )
                    tmp_auto_logo = assets_dir / "_auto_brand_logo.png"
                    if not has_custom_logo:
                        raw_lp = str(visuals.get("logo") or _default_logo_base_prompt(str(merged.get("name") or ""), brief_for_llm, "", norm_lang))
                        l_clean = _sanitize_zimage_prompt(raw_lp, team_names + [str(merged.get("name") or "")])
                        batch_items.append(
                            {
                                "id": "brand_logo",
                                "prompt": f"{l_clean}, flat vector symbol on solid neutral backdrop, symbol-only composition".strip(", "),
                                "width": 512,
                                "height": 512,
                                "steps": 8,
                                "cfg_scale": 1.0,
                                "seed": 101,
                                "output_path": str(tmp_auto_logo),
                            }
                        )
                    # Prune stale assets from earlier runs that exceed current counts
                    for stale_t in assets_dir.glob("team_*.png"):
                        m_num = re.search(r"team_(\d+)\.png$", stale_t.name)
                        if m_num and int(m_num.group(1)) > len(visuals.get("team") or []):
                            stale_t.unlink(missing_ok=True)
                    manifest_path = out_dir / ".smartllm" / "render_batch.json"
                    manifest_path.parent.mkdir(parents=True, exist_ok=True)
                    manifest_path.write_text(json.dumps(batch_items, indent=2), encoding="utf-8")
                    cmd = [
                        str(img_mgr.sd_cli_bin),
                        "--diffusion-model", str(img_mgr.dit_model_path),
                        "--llm", str(img_mgr.te_model_path),
                        "--vae", str(img_mgr.vae_model_path),
                        "--type", "q8_0",
                        "--clip-on-cpu",
                        "--vae-tiling",
                        "--sampling-method", "euler",
                        "--flow-shift", "3.0",
                        "--steps", "8",
                        "--cfg-scale", "1.0",
                        "-p", batch_items[0]["prompt"],
                        "-o", batch_items[0]["output_path"],
                        "--batch-json", str(manifest_path),
                    ]
                    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900.0, check=False, **subprocess_kwargs())
                    if res.returncode == 0 and (assets_dir / "hero_primary.png").exists():
                        zimage_rendered = True
                        gallery_images = [
                            f"assets/{item['id']}.png" for item in batch_items
                            if item["id"].startswith("gallery_") and (assets_dir / f"{item['id']}.png").exists()
                        ]
                        if not has_custom_logo and tmp_auto_logo.exists():
                            from .sanitizer import ingest_brand_logo
                            logo_info = ingest_brand_logo("brand-logo.png", tmp_auto_logo.read_bytes(), assets_dir)
                            tmp_auto_logo.unlink(missing_ok=True)
                            (assets_dir / "brand-logo.svg").unlink(missing_ok=True)
                            (assets_dir / "favicon.svg").unlink(missing_ok=True)
                            merged["logo"] = logo_info
                            merged["selected_logo_path"] = str(assets_dir / "brand-logo.png")
                            auto_logo_generated = True
                finally:
                    if sd_trimmer is not None:
                        sd_trimmer.stop()
                    try:
                        self.state.gpu.release_lock()
                        from .engines.gpu import GPUState
                        self.state.gpu.transition(GPUState.IDLE)
                    except Exception:
                        pass
            summary["gallery_images"] = gallery_images
            mark_external_step(out_dir, "render", "done" if zimage_rendered else "skipped", f"{len(batch_items) if zimage_rendered else 0} visuals" if zimage_rendered else "visual plan only")
            tasks[2]["status"] = "done"
            dim_preview = ", ".join(f"{it['id']}:{it['width']}x{it['height']}" for it in batch_items[:3]) if zimage_rendered else ""
            tasks[2]["detail"] = (
                f"Z-Image {len(batch_items)} visuals ({dim_preview}): heroes + gallery + team{' + logo' if auto_logo_generated else ''} (GPU)"
                if zimage_rendered
                else ("Дизайн и визуальный план (без рендера)" if not render_images else "Предпросмотр (без GPU рендера)")
            )

            self._set_stage(
                tasks, 3,
                "4/5: Детерминированная сборка SEO / AEO / GEO, JSON-LD и CSP...",
                "4/5: Deterministic SEO / AEO / GEO, JSON-LD & SHA-256 CSP compile...",
            )
            from .blueprint import compile_project_blueprint

            saved_draft = self.state.save_project(str(merged.get("id") or "default"), merged)
            bp = compile_project_blueprint(saved_draft, repo_root=self.state.repo_root)
            mark_external_step(out_dir, "compile", "done", f"{len(bp['files'])} files, CSP {bp['style_sha256'][:15]}")
            tasks[3]["status"] = "done"
            tasks[3]["detail"] = f"JSON-LD + llms.txt + CSP ({bp['style_sha256'][:15]}...)"

            self._set_stage(
                tasks, 4,
                "5/5: Запись бандла и финальный аудит PageSpeed / целостности...",
                "5/5: Writing bundle & running final PageSpeed / integrity audit...",
            )
            base_url = str((saved_draft.get("seo") or {}).get("base_url") or "https://smartllm-studio.example.org").rstrip("/")
            final_audit = run_final_audit(Path(bp["project_dir"]), bp["routes"], base_url)
            mark_external_step(out_dir, "audit", "done" if final_audit["passed"] else "failed", f"{'PASS' if final_audit['passed'] else 'FAIL'} · {final_audit['total_html_weight_bytes']} B HTML")
            tasks[4]["status"] = "done"
            tasks[4]["detail"] = f"{len(bp['files'])} файлов -> {bp['project_dir']} · аудит {'PASS' if final_audit['passed'] else 'FAIL'}"

            prev_url = self.state.register_preview(str(saved_draft.get("id") or "default"), Path(bp["project_dir"]), rev=saved_draft["revision"])
            bp["preview_url"] = prev_url
            bp["orchestrator"] = {
                "run_id": run_id,
                "mode": mode,
                "started_at": started_at,
                "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ai_used": bool(ai_used),
                "zimage_used": zimage_rendered,
                "tasks": tasks,
                "draft": saved_draft,
                "pipeline": {
                    "agents_run": summary["agents_run"],
                    "agents_reused": summary["agents_reused"],
                    "review_avg": summary["review_avg"],
                    "review": summary["review"],
                    "memory_dir": summary["memory_dir"],
                    "fingerprint": summary["fingerprint"],
                },
                "final_audit": final_audit,
            }
            self.runs[run_id] = bp["orchestrator"]
            self.active_status = {
                "running": False,
                "stage": "done",
                "progress": 100,
                "message_ru": (
                    f"Готово! Сайт собран пайплайном субагентов (ревизия {summary['review_avg']}/6) -> {bp['project_dir']}"
                ),
                "message_en": f"Done! Sub-agent pipeline build (review {summary['review_avg']}/6) -> {bp['project_dir']}",
                "tasks": [dict(x) for x in tasks],
            }
            return bp
        except Exception as exc:
            self.active_status = {
                "running": False,
                "stage": "error",
                "message_ru": f"Ошибка сборки: {exc}",
                "message_en": f"Build error: {exc}",
                "tasks": [dict(x) for x in tasks],
            }
            raise
