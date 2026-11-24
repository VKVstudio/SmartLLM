"""Bundled standalone RAG canon, copywriting & checklist selector for SmartLLM Studio."""

from __future__ import annotations

import json
from pathlib import Path
import re
import struct
from typing import Any
import zlib

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def detect_language(text: str, explicit_lang: str = "auto") -> str:
    if explicit_lang in ("en", "ru"):
        return explicit_lang
    cyr = len(re.findall(r"[А-Яа-яЁё]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    return "ru" if cyr > 0 and cyr >= lat * 0.25 else "en"


def make_synthetic_png(path: Path, width: int = 64, height: int = 64, seed_shift: int = 0) -> None:
    """Create a deterministic dark-obsidian architectural wireframe PNG using pure stdlib."""
    w = max(16, int(width))
    h = max(16, int(height))
    margin_x = max(4, w // 12)
    margin_y = max(4, h // 12)
    grid_step_x = max(12, w // 8)
    grid_step_y = max(12, h // 8)
    offset_x = (seed_shift * 7) % grid_step_x
    offset_y = (seed_shift * 5) % grid_step_y
    rows_list: list[bytes] = []
    for y in range(h):
        ny = y / max(1, h - 1)
        row = bytearray(1 + w * 3)
        row[0] = 0
        on_border_y = y in (margin_y, margin_y + 1, h - 1 - margin_y, h - 2 - margin_y)
        on_grid_y = ((y + offset_y) % grid_step_y == 0) and (margin_y <= y <= h - 1 - margin_y)
        base_g_row = int(17 + 14 * (1.0 - ny))
        base_b_row = int(24 + 18 * (1.0 - ny))
        for x in range(w):
            nx = x / max(1, w - 1)
            r = min(26, max(14, int(14 + 12 * (0.5 * nx + 0.5 * (1.0 - ny)))))
            g = min(31, max(17, int(base_g_row + 4 * nx)))
            b = min(42, max(24, int(base_b_row + 6 * nx)))
            on_border_x = x in (margin_x, margin_x + 1, w - 1 - margin_x, w - 2 - margin_x)
            on_grid_x = ((x + offset_x) % grid_step_x == 0) and (margin_x <= x <= w - 1 - margin_x)
            in_frame = (margin_x <= x <= w - 1 - margin_x) and (margin_y <= y <= h - 1 - margin_y)
            diag_diff = abs((x * h) - (y * w))
            on_diag = in_frame and (diag_diff <= max(w, h) // 2) and (seed_shift % 2 == 0 or (x + y) % 3 == 0)
            if (on_border_y and margin_x <= x <= w - 1 - margin_x) or (on_border_x and margin_y <= y <= h - 1 - margin_y):
                # Champagne gold architectural border (#c8a45d)
                r, g, b = 200, 164, 93
            elif on_grid_x or on_grid_y or on_diag:
                # Muted violet structural rule line (#8b6fc9 blended smoothly)
                r, g, b = 96, 82, 148
            pos = 1 + x * 3
            row[pos] = r
            row[pos + 1] = g
            row[pos + 2] = b
        rows_list.append(bytes(row))
    raw_data = b"".join(rows_list)

    def _chunk(ctype: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw_data, level=1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b""))


class StudioRAGSelector:
    """Standalone RAG selector backed by smartllm_studio/data/ (zero monorepo coupling)."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        cards_raw = json.loads((data_dir / "canon_cards.json").read_text(encoding="utf-8"))
        self.canon_cards: dict[str, dict[str, Any]] = {str(c["id"]): c for c in cards_raw}
        self.copy_pairs: list[dict[str, Any]] = json.loads((data_dir / "copy_pairs.json").read_text(encoding="utf-8"))
        self.checklists: dict[str, dict[str, Any]] = json.loads((data_dir / "checklists.json").read_text(encoding="utf-8"))

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {t for t in re.findall(r"[a-zа-яё0-9_+-]{2,}", text.lower()) if len(t) >= 2}

    def select(
        self,
        brief: str,
        lang: str = "auto",
        explicit_canon_id: str | None = None,
        top_k_copy: int = 4,
    ) -> dict[str, Any]:
        resolved_lang = detect_language(brief, explicit_lang=lang)
        tokens = self._tokenize(brief)
        lower = brief.lower()

        selected_cid = explicit_canon_id if explicit_canon_id in self.canon_cards else None
        if not selected_cid and explicit_canon_id:
            for cid, card in sorted(self.canon_cards.items()):
                if explicit_canon_id in (card.get("legacy_ids") or []):
                    selected_cid = cid
                    break
        if not selected_cid and explicit_canon_id:
            from ..kb_loader import resolve_canon_id
            kb_cid = resolve_canon_id(explicit_canon_id)
            if kb_cid in self.canon_cards and explicit_canon_id != "":
                selected_cid = kb_cid
        if not selected_cid and explicit_canon_id:
            matches = [cid for cid in self.canon_cards if cid.startswith(explicit_canon_id)]
            if matches:
                selected_cid = sorted(matches)[0]

        if not selected_cid:
            try:
                from ..kb_loader import route_canon_v2

                router_scores = dict(route_canon_v2(brief))
            except Exception:
                router_scores = {}
            scores: list[tuple[float, str]] = []
            for cid, card in sorted(self.canon_cards.items()):
                blob = " ".join(
                    [
                        cid,
                        str(card.get("name", "")),
                        str(card.get("name_ru", "")),
                        str(card.get("category", "")),
                        " ".join(card.get("best_for", [])),
                        " ".join(card.get("search_terms", [])),
                        " ".join(card.get("imagery", {}).get("style_tags", [])),
                    ]
                ).lower()
                sc = float(len(tokens & self._tokenize(blob))) * 2.5
                sc += float(router_scores.get(cid, 0))
                scores.append((sc, cid))
            scores.sort(key=lambda it: (-round(it[0], 4), it[1]))
            selected_cid = scores[0][1]

        card = self.canon_cards[selected_cid]
        scored_cp: list[tuple[float, str, dict[str, Any]]] = []
        for cp in self.copy_pairs:
            sc = 10.0 if cp.get("canon_id") == selected_cid else 0.0
            sc += float(len(tokens & self._tokenize(f"{cp.get('domain', '')} {cp.get('en_canon_after', '')} {cp.get('ru_canon_after', '')}"))) * 3.0
            scored_cp.append((sc, str(cp.get("id", "")), cp))
        scored_cp.sort(key=lambda it: (-round(it[0], 4), it[1]))

        copy_list = [
            {
                "id": it[2]["id"],
                "category": it[2]["category"],
                "domain": it[2]["domain"],
                "canon_id": it[2]["canon_id"],
                "slop_before": it[2]["ru_slop_before"] if resolved_lang == "ru" else it[2]["en_slop_before"],
                "canon_after": it[2]["ru_canon_after"] if resolved_lang == "ru" else it[2]["en_canon_after"],
                "anti_slop_rule": it[2]["anti_slop_rule"],
            }
            for it in scored_cp[:top_k_copy]
        ]

        stacks = [
            st
            for st, kws in (
                ("astro", ("astro", "island", "client:visible")),
                ("nextjs", ("next.js", "nextjs", "app router", "rsc")),
                ("sveltekit", ("svelte", "sveltekit")),
                ("vite_ts", ("vite", "typescript")),
            )
            if any(k in lower for k in kws)
        ] or ["astro", "nextjs", "sveltekit", "vite_ts"]
        motion_focused = any(k in lower for k in ("gsap", "scrolltrigger", "flip", "motion", "animation", "анимац"))

        return {
            "brief": brief,
            "lang": resolved_lang,
            "canon_id": selected_cid,
            "canon_card": card,
            "copy_pairs": copy_list,
            "skill_directives": {
                "detected_stacks": stacks,
                "motion_focused": motion_focused,
            },
        }


def build_studio_prompt(rag_bundle: dict[str, Any]) -> str:
    card = rag_bundle["canon_card"]
    pal = card.get("palette", {})
    copy_lines = "\n".join(f"- {cp['canon_after']}" for cp in rag_bundle["copy_pairs"])
    return (
        f"Canon: {card['id']} ({card['name']})\n"
        f"OKLCH Palette: bg={pal.get('bg')}, surface={pal.get('surface')}, text={pal.get('text')}, accent={pal.get('accent')}\n"
        f"Reference Copy:\n{copy_lines}\n"
        f"Brief: {rag_bundle['brief']}\n"
    )
