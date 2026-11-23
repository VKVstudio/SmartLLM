"""Deterministic mathematical & cross-reference integrity verification for studio/smartllm_studio/kb/."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDIO_PKG = REPO_ROOT / "studio" / "smartllm_studio"
KB_ROOT = STUDIO_PKG / "kb"
if str(REPO_ROOT / "studio") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "studio"))

from smartllm_studio.pages import BLOCK_IDS  # noqa: E402

OKLCH_RE = re.compile(r"^oklch\(\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)(?:\s*/\s*([0-9.]+))?\s*\)$")

REJECTED_FONTS = {
    "Archivo Black", "Dela Gothic One", "Newsreader", "Space Grotesk",
    "Bodoni Moda", "Playfair Display", "Sofia Sans", "Sofia Sans Extra Condensed",
    "Russo One", "Jost", "Alegreya Sans", "Fredoka", "Atkinson Hyperlegible Next", "Soyuz Grotesk",
}
STATIC_ONLY_PKGS = {
    "@fontsource-variable/ibm-plex-mono", "@fontsource-variable/fira-sans",
    "@fontsource-variable/spectral", "@fontsource-variable/alegreya-sans",
    "@fontsource-variable/pt-mono", "@fontsource-variable/russo-one",
    "@fontsource-variable/dela-gothic-one",
}

FORBIDDEN_ZIMAGE_PATTERNS = [
    re.compile(r"(?i)\b(?:zero|no|without)\s+(?:readable\s+)?(?:text|words?|letters?|beige|outline)\b"),
    re.compile(r"#[0-9a-fA-F]{3,8}\b"),
    re.compile(r"(?i)\boklch\("),
    re.compile(r"(?i)\b(?:typography|letterforms?|glyph\s+grid|interface\s+cards?)\b"),
]


def _parse_oklch(s: str) -> tuple[float, float, float, float]:
    m = OKLCH_RE.match(str(s).strip())
    assert m, f"Invalid OKLCH token: {s!r}"
    return float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4) or 1.0)


def _oklch_to_lin_srgb(L: float, C: float, H: float) -> tuple[float, float, float]:
    hr = math.radians(H)
    a = C * math.cos(hr)
    b = C * math.sin(hr)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def _lin_to_gamma(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055


def _gamma_to_lin(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _resolve_lin(color_str: str, base_lin: tuple[float, float, float] | None = None) -> tuple[tuple[float, float, float], bool]:
    L, C, H, alpha = _parse_oklch(color_str)
    raw = _oklch_to_lin_srgb(L, C, H)
    in_gamut = all(-0.005 <= c <= 1.005 for c in raw)
    clamped = tuple(max(0.0, min(1.0, c)) for c in raw)
    if alpha < 1.0 and base_lin is not None:
        # Browser alpha compositing runs in gamma sRGB; test worst-case min contrast between linear & gamma blend
        g_fg = tuple(_lin_to_gamma(c) for c in clamped)
        g_bg = tuple(_lin_to_gamma(c) for c in base_lin)
        g_mix = tuple(alpha * f + (1.0 - alpha) * b for f, b in zip(g_fg, g_bg))
        clamped = tuple(_gamma_to_lin(c) for c in g_mix)
    return clamped, in_gamut  # type: ignore


def _contrast(c1: tuple[float, float, float], c2: tuple[float, float, float]) -> float:
    y1 = 0.2126 * c1[0] + 0.7152 * c1[1] + 0.0722 * c1[2]
    y2 = 0.2126 * c2[0] + 0.7152 * c2[1] + 0.0722 * c2[2]
    hi, lo = max(y1, y2), min(y1, y2)
    return round((hi + 0.05) / (lo + 0.05), 2)


def _est_tokens(path: Path) -> int:
    return math.ceil(len(path.read_text(encoding="utf-8")) / 3.5)


def test_gate_1_json_and_index_paths() -> tuple[dict, list[Path]]:
    json_files = sorted(KB_ROOT.rglob("*.json"))
    assert json_files, "No JSON files found in kb/"
    for jf in json_files:
        json.loads(jf.read_text(encoding="utf-8"))

    idx = json.loads((KB_ROOT / "00_INDEX.json").read_text(encoding="utf-8"))
    canon_files = sorted((KB_ROOT / "styles" / "canons").glob("*.json"))
    assert len(canon_files) == 20, f"Expected 20 canon JSONs, got {len(canon_files)}"
    expected_ids = [
        "01_bento_grid", "02_swiss_international", "03_editorial_magazine", "04_hyper_minimal_speed",
        "05_kinetic_typography", "06_neo_brutalism", "07_avant_garde_poster", "08_liquid_glass",
        "09_aurora_obsidian_mesh", "10_industrial_tactile", "11_soft_clay_playful", "12_quiet_luxury_minimal",
        "13_cinematic_documentary", "14_spatial_3d_showcase", "15_organic_biophilic_eco", "16_artisan_craft_zine",
        "17_fintech_institutional", "18_devtool_command_ui", "19_calm_human_accessible", "20_maximalist_collage_pop",
    ]
    assert [p.stem for p in canon_files] == expected_ids, f"Canon ID mismatch: {[p.stem for p in canon_files]}"

    stacks = ["html5_esm", "astro", "sveltekit", "nextjs", "vite_ts"]
    for ref in idx["orchestrator_lookup_tables"]["files"]:
        assert (KB_ROOT / ref).exists(), f"Missing lookup table: {ref}"
    for key, ref in idx["decision_routers"].items():
        assert (KB_ROOT / ref).exists(), f"Missing router {key}: {ref}"
    for stage, refs in idx["stage_loader"].items():
        for ref in refs:
            clean_ref = ref.split("#", 1)[0]
            if "{stack}" in clean_ref:
                for st in stacks:
                    assert (KB_ROOT / clean_ref.format(stack=st)).exists(), f"Missing stack leaf for {stage}: {st}"
            elif "{canon_id}" in clean_ref:
                for cid in expected_ids:
                    assert (KB_ROOT / clean_ref.format(canon_id=cid)).exists(), f"Missing canon leaf for {stage}: {cid}"
            else:
                assert (KB_ROOT / clean_ref).exists(), f"Missing file in stage_loader[{stage}]: {clean_ref}"
    return idx, canon_files


def test_gate_2_oklch_gamut_and_wcag(canon_files: list[Path]) -> None:
    color_keys = ("bg", "surface", "surface_elevated", "border", "border_control", "text", "muted", "accent", "accent_ink", "accent_2")
    checked = 0
    for cf in canon_files:
        doc = json.loads(cf.read_text(encoding="utf-8"))
        cid = doc["id"]
        assert set(doc["palettes"].keys()) == {"light", "dark"}, f"{cid} must define both light and dark"
        for pol in ("light", "dark"):
            pal = doc["palettes"][pol]
            for k in color_keys:
                assert k in pal, f"{cid}.{pol} missing {k}"
                _, ok = _resolve_lin(pal[k])
                assert ok, f"{cid}.{pol}.{k} out of sRGB gamut: {pal[k]}"
            bg_lin, _ = _resolve_lin(pal["bg"])
            surf_base = bg_lin
            if "aura_peak" in pal:
                surf_base, aura_ok = _resolve_lin(pal["aura_peak"])
                assert aura_ok, f"{cid}.{pol}.aura_peak out of gamut"
            sf_lin, _ = _resolve_lin(pal["surface"], surf_base)
            se_lin, _ = _resolve_lin(pal["surface_elevated"], surf_base)
            tx_lin, _ = _resolve_lin(pal["text"])
            mu_lin, _ = _resolve_lin(pal["muted"])
            ac_lin, _ = _resolve_lin(pal["accent"])
            ai_lin, _ = _resolve_lin(pal["accent_ink"])
            a2_lin, _ = _resolve_lin(pal["accent_2"])
            bc_lin, _ = _resolve_lin(pal["border_control"])

            c_tb = _contrast(tx_lin, bg_lin)
            c_ts = _contrast(tx_lin, sf_lin)
            c_te = _contrast(tx_lin, se_lin)
            c_mb = _contrast(mu_lin, bg_lin)
            c_ms = _contrast(mu_lin, sf_lin)
            c_me = _contrast(mu_lin, se_lin)
            c_ai = _contrast(ai_lin, ac_lin)
            c_ab = _contrast(ac_lin, bg_lin)
            c_as = _contrast(ac_lin, sf_lin)
            c_ae = _contrast(ac_lin, se_lin)
            c_bc = _contrast(bc_lin, sf_lin)
            c_bcb = _contrast(bc_lin, bg_lin)
            c_a2b = _contrast(a2_lin, bg_lin)

            req_t = 14.0 if cid == "19_calm_human_accessible" else 7.0
            req_m = 7.0 if cid == "19_calm_human_accessible" else 4.5
            req_a = 7.0 if cid == "19_calm_human_accessible" else 4.5
            assert c_tb >= req_t and c_ts >= req_t and c_te >= req_t, f"{cid}.{pol} text contrast {c_tb}/{c_ts}/{c_te} < {req_t}"
            assert c_mb >= req_m and c_ms >= req_m and c_me >= req_m, f"{cid}.{pol} muted contrast {c_mb}/{c_ms}/{c_me} < {req_m}"
            assert c_ai >= req_a, f"{cid}.{pol} accent_ink contrast {c_ai} < {req_a}"
            assert c_ab >= req_a and c_as >= req_a and c_ae >= req_a, f"{cid}.{pol} accent contrast {c_ab}/{c_as}/{c_ae} < {req_a}"
            assert c_bc >= 3.0 and c_bcb >= 3.0, f"{cid}.{pol} border_control contrast {c_bc}/{c_bcb} < 3.0 (WCAG 1.4.11)"

            saved = pal.get("contrast_verified") or {}
            expected_saved = {
                "text_bg": c_tb, "text_surface": c_ts, "muted_bg": c_mb, "muted_surface": c_ms,
                "accent_ink_accent": c_ai, "accent_bg": c_ab, "border_control_surface": c_bc, "accent_2_bg": c_a2b,
            }
            for ek, ev in expected_saved.items():
                assert ek in saved and abs(saved[ek] - ev) <= 0.02, f"{cid}.{pol} contrast_verified.{ek}={saved.get(ek)} vs {ev}"

            if "surface_opaque_fallback" in pal:
                fb_lin, fb_ok = _resolve_lin(pal["surface_opaque_fallback"])
                assert fb_ok and _contrast(tx_lin, fb_lin) >= req_t
            checked += 1
    assert checked == 40


def test_gate_3_fonts_and_licenses(canon_files: list[Path]) -> None:
    cids_set = {cf.stem for cf in canon_files}
    manifest = json.loads((KB_ROOT / "visual_prompting" / "phase2_vendor_manifest.json").read_text(encoding="utf-8"))
    for lib in manifest["js_libraries_approved_for_bundling"]:
        assert lib["license"] in {"MIT", "Apache-2.0"}, f"Disallowed JS license: {lib}"
        assert lib["builder_bundling_safe"] is True
        for cid in lib.get("recommended_canons") or []:
            assert cid in cids_set, f"Invalid recommended_canon {cid!r} in JS lib {lib['id']}"

    approved_pkgs = {}
    for fnt in manifest["fonts_verified_cyrillic_ruble_numero"]:
        assert fnt["family"] not in REJECTED_FONTS, f"Rejected font in manifest: {fnt['family']}"
        assert fnt["license"] == "SIL OFL-1.1"
        assert fnt["cyrillic_verified"] and fnt["ruble_verified"] and fnt["numero_verified"]
        assert fnt["pkg"] not in STATIC_ONLY_PKGS, f"Broken variable pkg: {fnt['pkg']}"
        approved_pkgs[fnt["pkg"]] = fnt

    used_pkgs: set[str] = set()
    for cf in canon_files:
        doc = json.loads(cf.read_text(encoding="utf-8"))
        f = doc["fonts"]
        assert f["license"] == "SIL OFL-1.1" and f["cyrillic_verified"] is True
        blob = " ".join(str(v) for k, v in f.items() if k != "packages")
        for rej in REJECTED_FONTS:
            assert rej not in blob, f"Rejected font {rej!r} found in {doc['id']}"
        for pkg in f["packages"]:
            assert pkg not in STATIC_ONLY_PKGS, f"Broken variable pkg {pkg} in {doc['id']}"
            assert pkg in approved_pkgs, f"Unverified font pkg {pkg} in {doc['id']}"
            used_pkgs.add(pkg)
    assert used_pkgs == set(approved_pkgs), f"Unused/missing manifest fonts: {set(approved_pkgs) ^ used_pkgs}"


def _walk_recipe_strings(obj: object, path: str, out: list[tuple[str, str]]) -> None:
    if isinstance(obj, str):
        out.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("post_sanitization_spec", "banned_phrases", "forbidden_triggers"):
                continue
            _walk_recipe_strings(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_recipe_strings(v, f"{path}[{i}]", out)


def test_gate_4_zimage_positive_only(canon_files: list[Path]) -> None:
    recipes = json.loads((KB_ROOT / "visual_prompting" / "slot_prompt_recipes.json").read_text(encoding="utf-8"))
    matrix_doc = json.loads((KB_ROOT / "styles" / "blocks" / "_matrix.json").read_text(encoding="utf-8"))
    assert recipes["engine"]["sd_cli_flags"]["cfg_scale"] == 1.0
    assert recipes["engine"]["sd_cli_flags"]["never_use_cfg_zero"] is True
    assert recipes["engine"]["negative_prompt_supported"] is False

    hero_variants = {v for blocks in matrix_doc["routing_matrix"].values() for v in blocks["hero"]}
    covered_hero = {
        v for sk, sv in recipes["slot_recipes"].items()
        if sk.startswith("hero") for v in (sv.get("target_variants") or [])
    }
    assert hero_variants <= covered_hero, f"Uncovered hero variants in slot_recipes: {sorted(hero_variants - covered_hero)}"

    strings_to_check: list[tuple[str, str]] = []
    for cf in canon_files:
        doc = json.loads(cf.read_text(encoding="utf-8"))
        for k, v in doc["zimage_direction"].items():
            strings_to_check.append((f"{doc['id']}.zimage.{k}", v))
    _walk_recipe_strings(recipes, "recipes", strings_to_check)

    for label, txt in strings_to_check:
        for rx in FORBIDDEN_ZIMAGE_PATTERNS:
            m = rx.search(txt)
            assert not m, f"Forbidden Z-Image trigger {m.group(0)!r} in {label}: {txt}"


def test_gate_5_cross_references(idx: dict, canon_files: list[Path]) -> None:
    cids = [p.stem for p in canon_files]
    matrix_doc = json.loads((KB_ROOT / "styles" / "blocks" / "_matrix.json").read_text(encoding="utf-8"))
    recipes = json.loads((KB_ROOT / "visual_prompting" / "slot_prompt_recipes.json").read_text(encoding="utf-8"))
    anatomy_txt = "\n".join(
        (KB_ROOT / "styles" / "blocks" / fn).read_text(encoding="utf-8")
        for fn in ("anatomy_19_blocks.md", "anatomy_core_blocks.md", "anatomy_supporting_blocks.md")
    )

    assert list(matrix_doc["canons_meta"].keys()) == cids
    assert list(matrix_doc["routing_matrix"].keys()) == cids
    assert list(recipes["canon_art_direction_overrides"].keys()) == cids

    v2f = matrix_doc["variant_to_family"]
    for cid, blocks in matrix_doc["routing_matrix"].items():
        assert set(blocks.keys()) == set(BLOCK_IDS), f"{cid} missing AVAILABLE_BLOCKS parity"
        for bid, variants in blocks.items():
            assert variants, f"{cid}.{bid} has empty variants"
            for v in variants:
                assert v in v2f, f"Unknown variant {v} in {cid}.{bid}"
                assert f"`{v}`" in anatomy_txt, f"Variant {v} missing from anatomy_19_blocks.md"

    old_cards = json.loads((STUDIO_PKG / "data" / "canon_cards.json").read_text(encoding="utf-8"))
    aliases = json.loads((KB_ROOT / "styles" / "legacy_aliases.json").read_text(encoding="utf-8"))
    cids_set = set(cids)
    for oc in old_cards:
        assert (oc["id"] in cids_set) or (oc["id"] in aliases), f"Canon ID {oc['id']} missing from KB / legacy_canon_aliases"
        target_cid = oc["id"] if oc["id"] in cids_set else aliases[oc["id"]]
        assert target_cid in cids_set, f"Target canon invalid for {oc['id']}"
        for leg in oc.get("legacy_ids") or []:
            assert leg in aliases and aliases[leg] in cids_set, f"Legacy ID {leg} missing/invalid"

    # Zero orphan files in kb/ and valid canon #slice(...) keys
    referenced = {"00_INDEX.json", "PHASE2_ROADMAP_AND_AUDIT_DELTAS.md"}
    referenced.update(idx["orchestrator_lookup_tables"]["files"])
    referenced.update(idx["decision_routers"].values())
    stacks = ("html5_esm", "astro", "sveltekit", "nextjs", "vite_ts")
    canon_docs = {cf.stem: json.loads(cf.read_text(encoding="utf-8")) for cf in canon_files}
    for stage, refs in idx["stage_loader"].items():
        for ref in refs:
            clean, *sl = ref.split("#", 1)
            if "{stack}" in clean:
                for st in stacks:
                    referenced.add(clean.format(stack=st))
            elif "{canon_id}" in clean:
                for cid in cids:
                    referenced.add(clean.format(canon_id=cid))
                if sl:
                    keys = sl[0].removeprefix("slice(").removesuffix(")").split(",")
                    for cid, doc in canon_docs.items():
                        missing = [k for k in keys if k not in doc]
                        assert not missing, f"stage_loader[{stage}] slice missing keys {missing} in {cid}"
            else:
                referenced.add(clean)
    actual_files = {p.relative_to(KB_ROOT).as_posix() for p in KB_ROOT.rglob("*") if p.is_file()}
    orphans = sorted(actual_files - referenced)
    assert not orphans, f"Orphan KB files unreachable from 00_INDEX.json: {orphans}"

    # Verify styles/_router.md table, _matrix.json canons_meta, legacy_ids, responsive clamp() math & MD json blocks
    clamp_re = re.compile(r"^clamp\(\s*([0-9.]+)rem\s*,\s*([0-9.]+)rem\s*\+\s*([0-9.]+)vw\s*,\s*([0-9.]+)rem\s*\)$")
    router_rows = [l for l in (KB_ROOT / "styles" / "_router.md").read_text(encoding="utf-8").splitlines() if l.startswith("| `")]
    assert len(router_rows) == 20, f"Expected 20 rows in styles/_router.md, got {len(router_rows)}"
    for cid, doc in canon_docs.items():
        matched = [l for l in router_rows if l.startswith(f"| `{cid}` |")]
        assert len(matched) == 1, f"Router row count mismatch for {cid}"
        row = matched[0]
        pol_exp = "L" if doc["default_polarity"] == "light" else "D"
        dials = doc["dials"]
        vmd = f"{dials['variance']}/{dials['motion']}/{dials['density']}"
        assert f"| {pol_exp} |" in row, f"Router polarity mismatch for {cid}: expected {pol_exp} in {row}"
        assert f"| {vmd} |" in row, f"Router V/M/D mismatch for {cid}: expected {vmd} in {row}"
        for fk in ("heading", "body", "mono"):
            fname = (doc["fonts"].get(fk) or "").split(",")[0].strip().strip("'\"").replace(" Variable", "")
            if fname and fname.lower() not in ("none", "n/a"):
                assert fname in row, f"Router font mismatch for {cid}.{fk}: {fname!r} missing in {row}"

        cm = matrix_doc["canons_meta"][cid]
        assert cm["default_polarity"] == doc["default_polarity"], f"_matrix polarity mismatch for {cid}"
        assert cm["marquee_allowed"] == doc["marquee_allowed"], f"_matrix marquee mismatch for {cid}"
        assert cm["dials"] == [dials["variance"], dials["motion"], dials["density"]], f"_matrix dials mismatch for {cid}"
        for leg in doc.get("legacy_ids") or []:
            assert aliases.get(leg) == cid, f"{cid}.legacy_ids {leg!r} missing/mismatched in legacy_aliases.json"

        resp = doc["responsive"]
        for tag in ("h1", "h2"):
            tp = resp["typography"][tag]
            m = clamp_re.match(tp["clamp"])
            assert m, f"Non-zoom-safe clamp in {cid}.{tag}: {tp['clamp']}"
            mn, base, _slope, mx = (float(m.group(i)) for i in range(1, 5))
            assert base > 0, f"WCAG 1.4.4 base_rem <= 0 in {cid}.{tag}: {tp['clamp']}"
            assert abs(mn * 16.0 - tp["mobile_px"]) <= 0.1, f"{cid}.{tag} min clamp != mobile_px"
            assert abs(mx * 16.0 - tp["desktop_px"]) <= 0.1, f"{cid}.{tag} max clamp != desktop_px"
            assert tp["mobile_px"] <= tp["tablet_px"] <= tp["desktop_px"], f"{cid}.{tag} breakpoint order invalid"
        assert resp["typography"]["body"]["mobile_px"] >= 16 and resp["typography"]["body"]["desktop_px"] >= 15
        min_touch = 48 if cid == "19_calm_human_accessible" else 44
        for fk in ("input_h_px", "cta_h_px"):
            assert resp["form"][fk]["tablet"] >= min_touch and resp["form"][fk]["mobile"] >= min_touch, f"{cid}.form.{fk} < {min_touch}px"

    for leg, target in aliases.items():
        if leg != target:
            assert leg in (canon_docs[target].get("legacy_ids") or []), f"Alias {leg}->{target} missing from canon legacy_ids"

    for mf in sorted(KB_ROOT.rglob("*.md")):
        txt = mf.read_text(encoding="utf-8")
        for m in re.finditer(r"```json\s*\n(.*?)```", txt, re.S):
            body = m.group(1).strip()
            try:
                json.loads(body)
            except ValueError:
                for line in body.splitlines():
                    if line.strip():
                        json.loads(line)


def test_gate_6_anti_ai_regexes() -> None:
    md = (KB_ROOT / "copy_marketing" / "anti_ai_writing_en_ru.md").read_text(encoding="utf-8")
    assert "anti_ai_regex_rules.json" in md
    rules_doc = json.loads((KB_ROOT / "copy_marketing" / "anti_ai_regex_rules.json").read_text(encoding="utf-8"))
    defs = {name: re.compile(pat) for name, pat in rules_doc["regexes"].items()}

    legit_en = [
        "5-axis titanium and 7075 aluminum parts held to ±0.015 mm, ensuring zero backlash.",
        "Same-day ceramic crowns milled in-house in 90 minutes on Oak Street.",
        "Washed Ethiopian Yirgacheffe craft coffee roasted in 12 kg batches every Tuesday.",
        "Landscape architecture for northern coastal campuses with native granite drainage.",
        "Seamless steel pipe ASTM A106 Grade B cut to 6-meter lengths with mill test certs.",
        "Not only ISO 9001 certified, but audited quarterly by TÜV Rheinland.",
        "South-facing glazing reflecting 62% of peak summer solar gain.",
        "Fragrance-free 10% azelaic acid serum, pH 4.8, full refund after 14 days.",
        "Private day school fostering independent chemistry lab research from grade 8.",
        "Commercial HVAC diagnostics in under 2 hours; $145 credited to repair.",
    ]
    for s in legit_en:
        assert not defs["EN_HARD_BAN"].search(s), f"EN_HARD_BAN false positive: {s}"
        assert not defs["EN_PARTICIPLE_SLOP"].search(s), f"EN_PARTICIPLE_SLOP false positive: {s}"

    legit_ru = [
        "Производим стальные детали ±0,01 мм на 5-осевых станках с проверкой КИМ.",
        "Ремонт квартир под ключ с фиксацией сметы в договоре и графиком работ.",
        "Энергоэффективность класса A++ и тихая работа инверторных сплит-систем.",
        "Проведём правовую проверку чистоты объекта перед подписанием сделки.",
        "Мебель из массива дуба по замерам помещения за 28 календарных дней.",
        "Возим сборные палеты Москва — Екатеринбург за 3 суток с GPS-треком.",
        "Устанавливаем керамические виниры за два визита по цифровому слепку.",
        "Обжариваем зерно категории спешелти каждый вторник партиями по 12 кг.",
        "Подключаем склад к 1С и МойСклад за 4 часа с обучением кладовщиков.",
        "Индивидуальный учебный план по физике и математике для 9–11 классов.",
    ]
    for s in legit_ru:
        assert not defs["RU_HARD_BAN"].search(s), f"RU_HARD_BAN false positive: {s}"
        assert not defs["RU_SPLIT_PRED_HARD"].search(s), f"RU_SPLIT_PRED_HARD false positive: {s}"
        assert not defs["RU_SOFT_WATCH"].search(s), f"RU_SOFT_WATCH false positive: {s}"

    slop_en = [
        "Let's delve into our revolutionary platform, a game-changer in today's fast-paced digital landscape.",
        "It's not just software — it's a transformative journey, underscoring our enduring legacy.",
    ]
    for s in slop_en:
        assert defs["EN_HARD_BAN"].search(s) or defs["EN_PARTICIPLE_SLOP"].search(s), f"Missed EN slop: {s}"

    slop_ru = [
        "В современном быстро меняющемся мире наша динамично развивающаяся компания выведет ваш бизнес на новый уровень.",
        "Мы осуществляем комплексную проверку и производим монтаж оборудования, раскрывая потенциал.",
    ]
    for s in slop_ru:
        assert defs["RU_HARD_BAN"].search(s) or defs["RU_SPLIT_PRED_HARD"].search(s), f"Missed RU slop: {s}"


def _harden_zimage_prompt(prompt: str, brand: str, member_names: list[str], spec: dict) -> str:
    protect = set(spec["visual_protect_words"])
    out = str(prompt or "")
    phrases = [p.strip() for p in ([brand] + list(member_names)) if p and len(p.strip()) >= 2]
    for ph in sorted(set(phrases), key=len, reverse=True):
        toks = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", ph)
        all_vis = bool(toks) and all(t.lower() in protect for t in toks)
        out = re.sub(rf"(?i)\b(?:for|by|brand|named|called|titled|portrait\s+of)\s+['\"«“]?{re.escape(ph)}['\"»”]?\b", "", out)
        out = re.sub(rf"(?i)['\"«“]{re.escape(ph)}['\"»”]", "", out)
        if all_vis:
            if any(c.isupper() for c in ph):
                out = re.sub(rf"(?<!\w){re.escape(ph)}(?!\w)", "", out)
        else:
            out = re.sub(rf"(?i)(?<!\w){re.escape(ph)}(?!\w)", "", out)
    for ph in phrases:
        for tok in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", ph):
            if len(tok) >= 4 and tok.lower() not in protect:
                out = re.sub(rf"(?<!\w){re.escape(tok)}(?!\w)", "", out, flags=re.I)
    out = re.sub(spec["hex_color_regex"], "", out)
    out = re.sub(spec["cyrillic_run_regex"], "", out)
    out = re.sub(spec["neg_clause_regex"], "", out)
    for rule in spec["text_replace_map"]:
        out = re.sub(rule["pattern"], rule["replace"], out)
    out = re.sub(r"(?i)\b(?:with|without|featuring|and|or|of)\s*(?=[,.;]|$)", "", out)
    out = re.sub(r"\s*,\s*(?:,\s*)+", ", ", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    return re.sub(r"\s+", " ", out).strip(" ,.;:-")


def test_gate_7_zimage_sanitizer() -> None:
    spec = json.loads((KB_ROOT / "visual_prompting" / "slot_prompt_recipes.json").read_text(encoding="utf-8"))["post_sanitization_spec"]
    p1 = _harden_zimage_prompt(
        "Oak joinery on warm stone for Stone & Oak (#F5F5F7), portrait of Elena White, dark brown eyes, off-white studio wall, David Brown, balanced negative space, zero text, zero beige",
        "Stone & Oak", ["Elena White", "David Brown"], spec,
    )
    for keep in ("oak joinery", "warm stone", "dark brown eyes", "off-white studio wall", "balanced negative space"):
        assert keep.lower() in p1.lower(), f"Sanitizer stripped protected phrase {keep!r}: {p1}"
    for drop in ("#F5F5F7", "Elena", "David", "zero text", "zero beige"):
        assert drop.lower() not in p1.lower(), f"Sanitizer leaked {drop!r}: {p1}"

    p2 = _harden_zimage_prompt(
        "Machined anodized aluminum tactile buttons on matte black steel for Black Steel, Viktor Sokolov, clean sign with no text on the wall, oklch(0.2 0.01 90)",
        "Black Steel", ["Viktor Sokolov"], spec,
    )
    assert "tactile buttons" in p2 and "matte black steel" in p2 and "an unmarked architectural surface" in p2
    for drop in ("Viktor", "Sokolov", "oklch", "no text", "clean sign"):
        assert drop.lower() not in p2.lower(), f"Sanitizer leaked {drop!r}: {p2}"

    p3 = _harden_zimage_prompt(
        "Warm white oak desk for White Oak Studio, Anna Stone, no visible text, without printed labels",
        "White Oak Studio", ["Anna Stone"], spec,
    )
    assert "warm white oak desk" in p3.lower()
    for drop in ("Anna", "visible text", "printed labels"):
        assert drop.lower() not in p3.lower(), f"Sanitizer leaked {drop!r}: {p3}"

    p4 = _harden_zimage_prompt(
        "Brushed dark steel enclosure for ООО «СтальПром», Сергей Волков, zero readable words",
        "ООО «СтальПром»", ["Сергей Волков"], spec,
    )
    assert "brushed dark steel enclosure" in p4.lower()
    for drop in ("СтальПром", "Сергей", "Волков", "readable words"):
        assert drop.lower() not in p4.lower(), f"Sanitizer leaked {drop!r}: {p4}"


def _json_tokens(obj: object) -> int:
    return math.ceil(len(json.dumps(obj, ensure_ascii=False)) / 3.5)


def test_gate_8_token_budgets(idx: dict, canon_files: list[Path]) -> None:
    lookup_set = {KB_ROOT / ref for ref in idx["orchestrator_lookup_tables"]["files"]}
    routers = [
        KB_ROOT / "00_INDEX.json",
        KB_ROOT / "architectures" / "_router.md",
        KB_ROOT / "styles" / "_router.md",
        KB_ROOT / "copy_marketing" / "_router.md",
    ]
    for r in routers:
        toks = _est_tokens(r)
        assert toks <= 1150, f"Router {r.name} exceeds budget: {toks} est. tokens"
        print(f"Router {r.relative_to(KB_ROOT)}: {toks} est. tokens")

    max_leaf = (0, "")
    for p in sorted(KB_ROOT.rglob("*")):
        if not p.is_file() or p in lookup_set or p in routers:
            continue
        toks = _est_tokens(p)
        if toks > max_leaf[0]:
            max_leaf = (toks, str(p.relative_to(KB_ROOT)))
        assert toks <= 2000, f"Leaf {p.relative_to(KB_ROOT)} exceeds 2000 est. tokens: {toks}"
    print(f"Token budget check PASS (largest LLM-loadable leaf: {max_leaf[1]} = {max_leaf[0]} est. tokens)")

    # Verify worst-case per-stage token sum AND exhaustive dry-run across all stage x stack x canon x profile combos
    stage_limit = int(idx["target_llm"]["recommended_prompt_kb_budget_tokens"])
    stacks = ("html5_esm", "astro", "sveltekit", "nextjs", "vite_ts")
    canon_docs = {cf.stem: json.loads(cf.read_text(encoding="utf-8")) for cf in canon_files}
    matrix_doc = json.loads((KB_ROOT / "styles" / "blocks" / "_matrix.json").read_text(encoding="utf-8"))
    recipes = json.loads((KB_ROOT / "visual_prompting" / "slot_prompt_recipes.json").read_text(encoding="utf-8"))
    rubrics = json.loads((KB_ROOT / "seo_perf_security" / "skeptic_rubrics.json").read_text(encoding="utf-8"))

    worst_stage = (0, "")
    combos = 0
    for stage, refs in idx["stage_loader"].items():
        st_list = stacks if any("{stack}" in r for r in refs) else ("none",)
        cn_list = list(canon_docs) if any("{canon_id}" in r or "#slice(canon_id)" in r for r in refs) else ("none",)
        pr_list = list(rubrics["profiles"]) if any("#slice(profile_id)" in r for r in refs) else ("none",)
        for st in st_list:
            for cn in cn_list:
                for pr in pr_list:
                    chunks = []
                    for ref in refs:
                        clean, *sl = ref.split("#", 1)
                        if "{stack}" in clean:
                            chunks.append((KB_ROOT / clean.format(stack=st)).read_text(encoding="utf-8"))
                        elif "{canon_id}" in clean:
                            doc = canon_docs[cn]
                            if sl:
                                keys = sl[0].removeprefix("slice(").removesuffix(")").split(",")
                                chunks.append(json.dumps({k: doc[k] for k in keys}, ensure_ascii=False))
                            else:
                                chunks.append((KB_ROOT / clean.format(canon_id=cn)).read_text(encoding="utf-8"))
                        elif sl and clean == "styles/blocks/_matrix.json":
                            chunks.append(json.dumps(matrix_doc["routing_matrix"][cn], ensure_ascii=False))
                        elif sl and clean == "visual_prompting/slot_prompt_recipes.json":
                            chunks.append(json.dumps({
                                "slot_recipes": recipes["slot_recipes"],
                                "override": recipes["canon_art_direction_overrides"][cn],
                            }, ensure_ascii=False))
                        elif sl and clean == "seo_perf_security/skeptic_rubrics.json":
                            chunks.append(json.dumps({
                                pr: rubrics["profiles"][pr],
                                "verdict_schema": rubrics["verdict_schema"],
                            }, ensure_ascii=False))
                        else:
                            chunks.append((KB_ROOT / clean).read_text(encoding="utf-8"))
                    payload = "\n\n".join(chunks)
                    assert len(payload) > 200, f"Empty dry-run payload for {stage}/{st}/{cn}/{pr}"
                    toks = math.ceil(len(payload) / 3.5)
                    assert toks <= stage_limit, f"Stage {stage} ({st}/{cn}/{pr}) exceeds prompt budget: {toks} > {stage_limit}"
                    if toks > worst_stage[0]:
                        worst_stage = (toks, f"{stage} ({cn})")
                    combos += 1
    print(f"Stage budget check PASS ({combos} combinations, worst: {worst_stage[1]} = {worst_stage[0]} / {stage_limit} est. tokens)")


def main() -> None:
    idx, canon_files = test_gate_1_json_and_index_paths()
    test_gate_2_oklch_gamut_and_wcag(canon_files)
    test_gate_3_fonts_and_licenses(canon_files)
    test_gate_4_zimage_positive_only(canon_files)
    test_gate_5_cross_references(idx, canon_files)
    test_gate_6_anti_ai_regexes()
    test_gate_7_zimage_sanitizer()
    test_gate_8_token_budgets(idx, canon_files)
    print("ALL_KB_INTEGRITY_GATES_PASSED")


if __name__ == "__main__":
    main()
