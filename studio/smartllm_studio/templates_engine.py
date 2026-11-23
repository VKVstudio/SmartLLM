"""4-Layer Orthogonal Template Engine (Vendor Fonts/MIT JS, 5 Stacks, 20 L+D Themes, Page Model JSON)."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

from .kb_loader import get_blocks_matrix, list_canon_ids, load_canon_kb, resolve_canon_id

PKG_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = PKG_ROOT / "templates"
VENDOR_DIR = TEMPLATES_DIR / "vendor"
THEMES_DIR = TEMPLATES_DIR / "themes"
STACKS_DIR = TEMPLATES_DIR / "stacks"
BLOCKS_DIR = TEMPLATES_DIR / "blocks"

_PKG_TO_FONT_ID: dict[str, str] | None = None


def _pkg_font_map() -> dict[str, str]:
    global _PKG_TO_FONT_ID
    if _PKG_TO_FONT_ID is None:
        manifest = json.loads((VENDOR_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
        _PKG_TO_FONT_ID = {str(f["pkg"]): str(f["id"]) for f in manifest["fonts"]}
    return _PKG_TO_FONT_ID


def _palette_vars_css(pal: dict[str, Any], shadow_card: str, glass_bg: str = "") -> str:
    lines = [
        f"  --bg: {pal['bg']};",
        f"  --surface: {pal['surface']};",
        f"  --surface-elevated: {pal['surface_elevated']};",
        f"  --border: {pal['border']};",
        f"  --border-control: {pal['border_control']};",
        f"  --text: {pal['text']};",
        f"  --text-muted: {pal['muted']};",
        f"  --accent: {pal['accent']};",
        f"  --accent-ink: {pal['accent_ink']};",
        f"  --accent-2: {pal['accent_2']};",
        f"  --accent-3: {pal['muted']};",
        f"  --shadow: {shadow_card};",
    ]
    if pal.get("surface_opaque_fallback"):
        lines.append(f"  --surface-fallback: {pal['surface_opaque_fallback']};")
    if pal.get("aura_peak"):
        lines.append(f"  --aura-peak: {pal['aura_peak']};")
    if glass_bg:
        lines.append(f"  --surface-glass: {glass_bg};")
    return "\n".join(lines)


def build_canon_theme_css(canon_id: str, default_polarity: str | None = None) -> str:
    """Build dual-polarity (Light + Dark) CSS theme layer from verified KB canon JSON."""
    c = load_canon_kb(canon_id)
    cid = c["id"]
    pol_def = default_polarity if default_polarity in ("light", "dark") else c["default_polarity"]
    pol_alt = "dark" if pol_def == "light" else "light"
    g = c["geometry"]
    r = c["responsive"]
    t = r["typography"]
    f = c["fonts"]
    m = c["motion"]
    grid = r["grid"]
    form = r["form"]

    sh_light = str(g["shadow_light"])
    sh_dark = str(g["shadow_dark"])
    sh_def = sh_light if pol_def == "light" else sh_dark
    sh_alt = sh_dark if pol_def == "light" else sh_light
    pal_def = c["palettes"][pol_def]
    pal_alt = c["palettes"][pol_alt]

    h1 = t["h1"]
    h2 = t["h2"]
    body = t["body"]
    small = t["small"]

    root_vars = "\n".join([
        f"  color-scheme: {pol_def};",
        _palette_vars_css(pal_def, sh_def),
        f"  --font-heading: {f['heading']};",
        f"  --font-sans: {f['body']};",
        f"  --font-mono: {f['mono'] if f.get('mono') and f['mono'] != 'none' else f['body']};",
        f"  --radius: {int(g['radius_card_px'])}px;",
        f"  --radius-card: {int(g['radius_card_px'])}px;",
        f"  --radius-button: {int(g['radius_button_px'])}px;",
        f"  --radius-input: {int(g['radius_input_px'])}px;",
        f"  --radius-badge: {int(g['radius_badge_px'])}px;",
        f"  --border-w: {int(g['border_width_px'])}px;",
        f"  --container-max: {int(r['container_max_px'])}px;",
        f"  --h1-clamp: {h1['clamp']};",
        f"  --h2-clamp: {h2['clamp']};",
        f"  --h1-lh: {h1['lh']};",
        f"  --h1-ls: {h1['ls']};",
        f"  --h1-weight: {h1['weight']};",
        f"  --heading-transform: {h1.get('transform', 'none')};",
        f"  --heading-tracking: {h1['ls']};",
        f"  --body-leading: {body['lh']};",
        f"  --small-ls: {small['ls']};",
        f"  --pad-section: clamp({grid['mobile']['section_py_px']}px, 5vw, {grid['desktop']['section_py_px']}px);",
        f"  --grid-gap: clamp({grid['mobile']['gutter_px']}px, 2vw, {grid['desktop']['gutter_px']}px);",
        f"  --card-pad: clamp({grid['mobile']['card_pad_px']}px, 2.2vw, {grid['desktop']['card_pad_px']}px);",
        f"  --input-h-desk: {form['input_h_px']['desktop']}px;",
        f"  --input-h-mob: {form['input_h_px']['mobile']}px;",
        f"  --cta-h-desk: {form['cta_h_px']['desktop']}px;",
        f"  --cta-h-mob: {form['cta_h_px']['mobile']}px;",
        f"  --motion-dur: {int(m['duration_ms'])}ms;",
        f"  --motion-ease: {m['ease']};",
    ])
    alt_vars = "\n".join([
        f"  color-scheme: {pol_alt};",
        _palette_vars_css(pal_alt, sh_alt),
    ])
    return (
        f"/* SmartLLM Layer 3 Theme: {cid} ({c['name']}) — default {pol_def} */\n"
        f":root, [data-theme=\"{pol_def}\"] {{\n{root_vars}\n}}\n"
        f"[data-theme=\"{pol_alt}\"] {{\n{alt_vars}\n}}\n"
    )


def materialize_all_themes_and_stack_docs() -> list[str]:
    """Generate all 20 Layer-3 CSS themes and 5 Layer-2 Stack Blueprint specs."""
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for cid in list_canon_ids():
        css = build_canon_theme_css(cid)
        out = THEMES_DIR / f"{cid}.css"
        out.write_text(css, encoding="utf-8")
        written.append(out.relative_to(PKG_ROOT).as_posix())

    stack_specs = {
        "html5_esm": {"name": "Zero-Build Semantic HTML5 + OKLCH CSS + Native ESM", "runtime_kb": 0, "notes": "Native <dialog>, Popover, Anchor Positioning, offline-first."},
        "astro": {"name": "Astro 7.4.13 Islands + Content Layer (Zod v4)", "runtime_kb": 0, "notes": "strict HTML Rust compiler; NO <ClientRouter /> when security.csp: true; actions/index.ts + content.config.ts."},
        "sveltekit": {"name": "SvelteKit 3.4.0 + Svelte 5.59.1 Runes", "runtime_kb": 18, "notes": "svelte.config.js REMOVED (use vite.config.ts); $lib REMOVED (use package.json #imports #lib/* with explicit extensions); csrf.trustedOrigins."},
        "nextjs": {"name": "Next.js 16.4.6 Active LTS + React 19.3.1 App Router", "runtime_kb": 42, "notes": "src/proxy.ts Node runtime only (replaces middleware.ts); src/lib/dal.ts import 'server-only'; isolate tenant keys outside 'use cache'."},
        "vite_ts": {"name": "Vite 8.3.8 (Rolldown) + TS 7.x + Same-Origin BFF", "runtime_kb": 14, "notes": "build.rolldownOptions; TypeScript 7.x Go compiler; same-origin /api/* BFF with Zod 4.6.7 + Sec-Fetch-Site/Origin CSRF check."},
    }
    for sid, spec in stack_specs.items():
        sdir = STACKS_DIR / sid
        sdir.mkdir(parents=True, exist_ok=True)
        out = sdir / "stack_spec.json"
        out.write_text(json.dumps({"id": sid, **spec}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(out.relative_to(PKG_ROOT).as_posix())
    return written


def bundle_vendor_assets_for_canon(canon_id: str, project_dir: Path, motion_mode: str = "css_scroll_driven") -> dict[str, Any]:
    """Copy verified SIL OFL-1.1 .woff2 fonts + optional MIT JS motion library into <project>/assets/."""
    manifest_file = VENDOR_DIR / "MANIFEST.json"
    if not manifest_file.exists():
        return {"font_css": "", "files": [], "js_relpath": ""}

    c = load_canon_kb(canon_id)
    pmap = _pkg_font_map()
    fonts_dest = project_dir / "assets" / "fonts"
    fonts_dest.mkdir(parents=True, exist_ok=True)

    css_parts: list[str] = []
    rel_files: list[str] = []
    for pkg in c["fonts"]["packages"]:
        fid = pmap.get(pkg)
        if not fid:
            continue
        src_dir = VENDOR_DIR / "fonts" / fid
        if not src_dir.is_dir():
            continue
        dst_dir = fonts_dest / fid
        dst_dir.mkdir(parents=True, exist_ok=True)
        for wf in sorted(src_dir.glob("*.woff2")):
            shutil.copy2(wf, dst_dir / wf.name)
            rel_files.append(f"assets/fonts/{fid}/{wf.name}")
        font_css_path = src_dir / "font.css"
        if font_css_path.exists():
            txt = font_css_path.read_text(encoding="utf-8")
            # Ensure url('assets/fonts/...') resolves both from root HTML and styles/
            css_parts.append(txt.replace(f"./assets/fonts/{fid}/", f"assets/fonts/{fid}/"))

    js_rel = ""
    motion_map = {
        "motion": ("motion", "motion.js"),
        "animejs": ("animejs", "anime.esm.min.js"),
        "lenis": ("lenis", "lenis.mjs"),
        "three": ("three", "three.module.js"),
    }
    if motion_mode in motion_map:
        lib_id, entry = motion_map[motion_mode]
        src_js_dir = VENDOR_DIR / "js" / lib_id
        if src_js_dir.is_dir():
            dst_js_dir = project_dir / "assets" / "vendor" / lib_id
            dst_js_dir.mkdir(parents=True, exist_ok=True)
            for jf in sorted(src_js_dir.iterdir()):
                if jf.is_file():
                    shutil.copy2(jf, dst_js_dir / jf.name)
                    rel_files.append(f"assets/vendor/{lib_id}/{jf.name}")
            if (dst_js_dir / entry).exists():
                js_rel = f"assets/vendor/{lib_id}/{entry}"

    return {"font_css": "\n".join(css_parts), "files": rel_files, "js_relpath": js_rel}


def normalize_stack_id(stack: str) -> str:
    low = str(stack or "html5_esm").strip().lower()
    if low in ("html5", "html5_esm", "html"):
        return "html5_esm"
    if low in ("astro", "sveltekit", "nextjs", "vite_ts"):
        return low
    return "html5_esm"


def emit_stack_scaffold(
    project_dir: Path,
    stack: str,
    motion: str,
    project_name: str,
    canon_id: str,
    routes: list[dict[str, Any]],
) -> list[str]:
    """Emit authentic late-2026 stack scaffold files tailored to the selected framework."""
    st = normalize_stack_id(stack)
    files: list[str] = ["app.ts"]
    (project_dir / "app.ts").write_text(
        f"// Strict TypeScript 7 entry for {project_name} ({st} + {motion} + {canon_id})\n"
        "export const initSmartLLMSite = (): void => {\n"
        "  document.documentElement.dataset.stack = " + json.dumps(st) + ";\n"
        "};\n"
        "initSmartLLMSite();\n",
        encoding="utf-8",
    )

    scaff_dir = project_dir / "scaffold"
    if st == "astro":
        # Compatible with existing check expecting astro.config.mjs at root OR scaffold
        astro_cfg = (
            'import { defineConfig } from "astro/config";\n'
            "// Astro 7.4.13 (Vite 8 Rolldown + Rust compiler). NOTE: Omit <ClientRouter /> when security.csp is true.\n"
            "export default defineConfig({\n"
            '  output: "static",\n'
            "  security: { checkOrigin: true, csp: true },\n"
            '  build: { inlineStylesheets: "always" },\n'
            "});\n"
        )
        (project_dir / "astro.config.mjs").write_text(astro_cfg, encoding="utf-8")
        files.append("astro.config.mjs")
        (scaff_dir / "src").mkdir(parents=True, exist_ok=True)
        (scaff_dir / "src" / "content.config.ts").write_text(
            'import { defineCollection } from "astro:content";\n'
            'import { z } from "astro/zod";\n'
            "const pages = defineCollection({ schema: z.object({ title: z.string(), description: z.string() }) });\n"
            "export const collections = { pages };\n",
            encoding="utf-8",
        )
        (scaff_dir / "src" / "actions.ts").write_text(
            'import { defineAction } from "astro:actions";\n'
            'import { z } from "astro/zod";\n'
            "export const server = {\n"
            "  contact: defineAction({\n"
            '    accept: "form",\n'
            "    input: z.object({ name: z.string().min(2), email: z.string().email(), message: z.string().max(2000) }),\n"
            "    handler: async (input) => ({ ok: true, receivedAt: new Date().toISOString(), name: input.name }),\n"
            "  }),\n"
            "};\n",
            encoding="utf-8",
        )
        files.extend(["scaffold/src/content.config.ts", "scaffold/src/actions.ts"])
    elif st == "sveltekit":
        # SvelteKit 3.4.0: NO svelte.config.js, NO $lib alias -> use package.json #lib/* & vite.config.ts
        (scaff_dir / "src" / "lib").mkdir(parents=True, exist_ok=True)
        (scaff_dir / "src" / "routes").mkdir(parents=True, exist_ok=True)
        (scaff_dir / "package.json").write_text(
            json.dumps({
                "name": "smartllm-sveltekit-app",
                "private": True,
                "type": "module",
                "imports": {"#lib/*": "./src/lib/*"},
                "dependencies": {"@sveltejs/kit": "^3.4.0", "svelte": "^5.59.1", "zod": "^4.6.7"},
                "devDependencies": {"@sveltejs/adapter-node": "^5.0.0", "vite": "^8.3.8"},
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        (scaff_dir / "vite.config.ts").write_text(
            'import adapter from "@sveltejs/adapter-node";\n'
            'import { sveltekit } from "@sveltejs/kit/vite";\n'
            'import { defineConfig } from "vite";\n'
            "export default defineConfig({\n"
            '  plugins: [sveltekit({ adapter: adapter(), csrf: { trustedOrigins: [] }, csp: { mode: "auto" } })],\n'
            "});\n",
            encoding="utf-8",
        )
        (scaff_dir / "src" / "lib" / "schema.ts").write_text(
            'import { z } from "zod";\n'
            "export const LeadSchema = z.object({ name: z.string().min(2), email: z.string().email(), message: z.string().max(2000) });\n",
            encoding="utf-8",
        )
        (scaff_dir / "src" / "routes" / "+page.server.ts").write_text(
            'import { fail } from "@sveltejs/kit";\n'
            'import { LeadSchema } from "#lib/schema.ts";\n'
            "export const actions = {\n"
            "  default: async ({ request }) => {\n"
            "    const fd = Object.fromEntries(await request.formData());\n"
            "    const parsed = LeadSchema.safeParse(fd);\n"
            "    if (!parsed.success) return fail(400, { invalid: true });\n"
            "    return { ok: true };\n"
            "  },\n"
            "};\n",
            encoding="utf-8",
        )
        files.extend(["scaffold/package.json", "scaffold/vite.config.ts", "scaffold/src/lib/schema.ts", "scaffold/src/routes/+page.server.ts"])
    elif st == "nextjs":
        # Next.js 16.4.6 Active LTS + React 19.3.1: proxy.ts (Node runtime) + server-only DAL
        (scaff_dir / "src" / "lib").mkdir(parents=True, exist_ok=True)
        (scaff_dir / "package.json").write_text(
            json.dumps({
                "name": "smartllm-nextjs-app",
                "private": True,
                "dependencies": {"next": "^16.4.6", "react": "^19.3.1", "react-dom": "^19.3.1", "server-only": "^0.0.1", "zod": "^4.6.7"},
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        (scaff_dir / "src" / "proxy.ts").write_text(
            'import { NextResponse, type NextRequest } from "next/server";\n'
            "// Next.js 16 proxy.ts (runs on Node runtime; replaces deprecated middleware.ts).\n"
            "export function proxy(request: NextRequest) {\n"
            "  const res = NextResponse.next();\n"
            '  res.headers.set("X-Content-Type-Options", "nosniff");\n'
            "  return res;\n"
            "}\n",
            encoding="utf-8",
        )
        (scaff_dir / "src" / "lib" / "dal.ts").write_text(
            'import "server-only";\n'
            'import { z } from "zod";\n'
            "export const LeadInput = z.object({ name: z.string().min(2), email: z.string().email(), message: z.string().max(2000) });\n"
            "export async function submitLead(raw: unknown) {\n"
            "  const data = LeadInput.parse(raw);\n"
            "  return { accepted: true, name: data.name };\n"
            "}\n",
            encoding="utf-8",
        )
        files.extend(["scaffold/package.json", "scaffold/src/proxy.ts", "scaffold/src/lib/dal.ts"])
    elif st == "vite_ts":
        # Vite 8.3.8 (build.rolldownOptions) + TS 7.x + Same-Origin /api/* BFF
        (scaff_dir / "bff").mkdir(parents=True, exist_ok=True)
        (scaff_dir / "vite.config.ts").write_text(
            'import { defineConfig } from "vite";\n'
            "export default defineConfig({\n"
            "  build: { rolldownOptions: { input: { main: \"../index.html\" } } },\n"
            '  server: { proxy: { "/api": "http://127.0.0.1:8787" } },\n'
            "});\n",
            encoding="utf-8",
        )
        (scaff_dir / "bff" / "server.ts").write_text(
            'import { z } from "zod";\n'
            "export const ContactPayload = z.object({ name: z.string().min(2), email: z.string().email() });\n"
            "export function verifyCsrfHeaders(secFetchSite: string | null, origin: string | null, expectedOrigin: string): boolean {\n"
            '  if (secFetchSite && secFetchSite !== "same-origin" && secFetchSite !== "none") return false;\n'
            "  if (origin && origin !== expectedOrigin) return false;\n"
            "  return true;\n"
            "}\n",
            encoding="utf-8",
        )
        files.extend(["scaffold/vite.config.ts", "scaffold/bff/server.ts"])
    else:
        # html5_esm native ESM
        (scaff_dir / "functions" / "api").mkdir(parents=True, exist_ok=True)
        (scaff_dir / "functions" / "api" / "contact.ts").write_text(
            "// Zero-build html5_esm edge webhook contract (same-origin /api/contact)\n"
            "export async function onRequestPost(context: { request: Request }): Promise<Response> {\n"
            '  const sfs = context.request.headers.get("Sec-Fetch-Site");\n'
            '  if (sfs && sfs !== "same-origin" && sfs !== "none") return new Response("Forbidden", { status: 403 });\n'
            '  return Response.json({ ok: true });\n'
            "}\n",
            encoding="utf-8",
        )
        files.append("scaffold/functions/api/contact.ts")
    return files


def write_page_model_json(
    project_dir: Path,
    *,
    canon_id: str,
    polarity: str,
    stack: str,
    motion: str,
    routes: list[dict[str, Any]],
    block_variants: dict[str, dict[str, str]],
    page_block_prompts: dict[str, dict[str, str]],
) -> str:
    """Emit Tab 3 Pro Editor compatible page_model.json inside the built project."""
    pages_arr: list[dict[str, Any]] = []
    for r in routes:
        slug = str(r["slug"])
        bmap = page_block_prompts.get(slug) or r.get("block_prompts") or {}
        vmap = block_variants.get(slug) or {}
        blocks_arr = [
            {
                "id": f"{slug}_{bid}_{idx}",
                "block": bid,
                "variant": vmap.get(bid, "default"),
                "overrides": {},
                "copy": bmap.get(bid, ""),
                "media": [],
            }
            for idx, bid in enumerate(r.get("bricks") or [])
        ]
        pages_arr.append({
            "slug": slug,
            "filename": r["filename"],
            "title": r["title"],
            "blocks": blocks_arr,
        })
    doc = {
        "schema_version": "2026.11.1",
        "canon_id": resolve_canon_id(canon_id),
        "polarity": polarity if polarity in ("light", "dark") else "light",
        "stack": normalize_stack_id(stack),
        "motion": str(motion or "css_scroll_driven"),
        "pages": pages_arr,
    }
    (project_dir / "page_model.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return "page_model.json"
