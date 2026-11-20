#!/usr/bin/env python3
"""Opus Spec Q1–Q7 Acceptance Gate & 54-Shot Contact Sheet Builder for SmartLLM Studio v2."""

from __future__ import annotations

import base64
import json
import math
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["SMARTLLM_STUDIO_HEADLESS"] = "1"

STUDIO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = STUDIO_ROOT.parent
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from smartllm_studio import __version__  # noqa: E402
from smartllm_studio.blueprint import _safe_project_dir, compile_project_blueprint, default_project_draft  # noqa: E402
from smartllm_studio.config import discover_studio_paths, load_edition_config  # noqa: E402
from smartllm_studio.os_compat import CrossPlatformFileLock, get_user_config_path  # noqa: E402
from smartllm_studio.rag import StudioRAGSelector  # noqa: E402
from smartllm_studio.sanitizer import sanitize_svg_bytes, validate_png_bytes  # noqa: E402
from smartllm_studio.server import StudioState, assert_studio_loopback, create_studio_server  # noqa: E402


def _http_req(url: str, method: str = "GET", payload: dict | None = None) -> tuple[int, bytes]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _rel_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
    rgb = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def _contrast_ratio(c1: str, c2: str) -> float:
    l1, l2 = _rel_luminance(c1), _rel_luminance(c2)
    return round((max(l1, l2) + 0.05) / (min(l1, l2) + 0.05), 2)


def _build_contact_sheet(shots_dir: Path, out_png: Path) -> dict[str, object]:
    """Compile all 54 EN+RU screenshots into reports/studio_v2_contact_sheet.png and check gold pixel budget."""
    from PIL import Image, ImageDraw

    shot_paths = sorted(shots_dir.glob("*.png"))
    assert len(shot_paths) >= 54, f"Expected >= 54 screenshots, got {len(shot_paths)}"

    cols = 9
    rows = math.ceil(len(shot_paths) / cols)
    thumb_w, thumb_h = 320, 200
    pad = 12
    label_h = 22
    sheet_w = cols * (thumb_w + pad) + pad
    sheet_h = rows * (thumb_h + label_h + pad) + pad

    sheet = Image.new("RGB", (sheet_w, sheet_h), (11, 13, 18))
    draw = ImageDraw.Draw(sheet)

    gold_pixels = 0
    total_pixels = 0
    for idx, sp in enumerate(shot_paths):
        r = idx // cols
        c = idx % cols
        x = pad + c * (thumb_w + pad)
        y = pad + r * (thumb_h + label_h + pad)
        with Image.open(sp) as im:
            rgb = im.convert("RGB")
            # Sample pixels for champagne gold (#e5b869 -> 229, 184, 105) budget <= 5%
            raw = rgb.tobytes()
            step = 3 * 16
            for p in range(0, len(raw) - 3, step):
                total_pixels += 1
                if abs(raw[p] - 229) <= 18 and abs(raw[p + 1] - 184) <= 18 and abs(raw[p + 2] - 105) <= 18:
                    gold_pixels += 1
            thumb = rgb.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (x, y))
        draw.text((x + 4, y + thumb_h + 4), sp.stem[:36], fill=(236, 238, 243))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png, "PNG", optimize=True)
    gold_ratio = round(gold_pixels / max(1, total_pixels), 4)
    assert gold_ratio <= 0.05, f"Gold pixel ratio {gold_ratio} exceeded 5% budget"
    return {
        "contact_sheet": str(out_png),
        "shots_compiled": len(shot_paths),
        "dimensions": f"{sheet_w}x{sheet_h}",
        "gold_pixel_ratio": gold_ratio,
    }


def run_all_tests() -> dict[str, object]:
    results: dict[str, object] = {}

    # 1. Q1-Q2: FSL-1.1-ALv2 License, TRADEMARKS, OUTPUTS, THIRD_PARTY_NOTICES, edition.json v2 & Docs
    assert __version__ == "0.0.2-beta"
    lic_txt = (STUDIO_ROOT / "LICENSE.md").read_text(encoding="utf-8")
    assert "FSL-1.1-ALv2" in lic_txt and "Apache License, Version 2.0" in lic_txt
    assert "Краткое резюме" not in lic_txt, "Russian summary must be in README.ru.md, not LICENSE.md"
    for req_doc in ("TRADEMARKS.md", "OUTPUTS.md", "THIRD_PARTY_NOTICES.md"):
        assert (STUDIO_ROOT / req_doc).exists() and (STUDIO_ROOT / req_doc).stat().st_size > 200

    edition = load_edition_config()
    assert edition["schema"] == 2 and edition["license_spdx"] == "FSL-1.1-ALv2"
    assert edition["support"]["mode"] == "free_launch" and edition["telemetry"] is False

    # Verify README heading parity and zero external shields.io URLs
    for pair in ((STUDIO_ROOT / "README.md", STUDIO_ROOT / "README.ru.md"), (REPO_ROOT / "README.md", REPO_ROOT / "README.ru.md")):
        t_en = pair[0].read_text(encoding="utf-8")
        t_ru = pair[1].read_text(encoding="utf-8")
        assert "shields.io" not in t_en and "shields.io" not in t_ru
        h_en = re.findall(r"^#{1,3}\s+", t_en, flags=re.MULTILINE)
        h_ru = re.findall(r"^#{1,3}\s+", t_ru, flags=re.MULTILINE)
        assert len(h_en) == len(h_ru), f"Heading count mismatch in {pair[0].name}: {len(h_en)} vs {len(h_ru)}"

    # 2. Q3: Standalone boundary & 5-Tier Path Discovery
    sel = StudioRAGSelector()
    assert len(sel.canon_cards) == 20 and len(sel.copy_pairs) == 168 and len(sel.checklists) == 6
    with tempfile.TemporaryDirectory(prefix="smartllm_5tier_") as td:
        td_p = Path(td)
        os.environ["XDG_CONFIG_HOME"] = str(td_p / "xdg")
        # Tier 1: CLI
        p_cli = discover_studio_paths(cli_overrides={"gguf_model_path": "/custom/cli.gguf"})
        assert p_cli["sources"]["gguf_model_path"] == "cli"
        # Tier 2: ENV
        os.environ["SMARTLLM_MODEL_PATH"] = "/custom/env.gguf"
        p_env = discover_studio_paths()
        assert p_env["sources"]["gguf_model_path"] == "env"
        del os.environ["SMARTLLM_MODEL_PATH"]
        # Tier 3: User config
        cfg_f = get_user_config_path("linux")
        cfg_f.parent.mkdir(parents=True, exist_ok=True)
        cfg_f.write_text(json.dumps({"paths": {"gguf_model_path": "/custom/user.gguf"}}), encoding="utf-8")
        p_usr = discover_studio_paths()
        assert p_usr["sources"]["gguf_model_path"] == "user_config"
        cfg_f.unlink()
        # Tier 4: Monorepo
        p_mono = discover_studio_paths()
        assert p_mono["sources"]["gguf_model_path"] == "monorepo"

    # 2b. Cross-OS output_dir portability (dual-boot shared project.json must not leak foreign paths)
    from smartllm_studio import blueprint as bp_mod
    with tempfile.TemporaryDirectory(prefix="smartllm_paths_") as td:
        td_p = Path(td)
        default_dir = td_p / "projects" / "default"
        assert _safe_project_dir("D:\\foreign\\site", default_dir) == default_dir.resolve()
        assert _safe_project_dir("", default_dir) == default_dir.resolve()
        assert _safe_project_dir("my-site", default_dir) == (td_p / "projects" / "my-site").resolve()
        orig_os_name = bp_mod.os.name
        try:
            bp_mod.os.name = "nt"
            assert _safe_project_dir("/mnt/rescue/projects/x", default_dir) == default_dir.resolve()
            assert _safe_project_dir("\\mnt\\rescue\\projects\\x", default_dir) == default_dir.resolve()
        finally:
            bp_mod.os.name = orig_os_name
        st = StudioState(repo_root=REPO_ROOT, projects_root_override=td_p / "projects", lock_path_override=td_p / "gpu.lock")
        pj = st.project_dir("default") / "project.json"
        poisoned = default_project_draft("default", repo_root=REPO_ROOT)
        poisoned["output_dir"] = "D:\\mnt\\rescue\\foreign"
        pj.write_text(json.dumps(poisoned), encoding="utf-8")
        loaded = st.load_project("default")
        assert loaded["output_dir"] == str(st.project_dir("default").resolve())
        assert json.loads(pj.read_text(encoding="utf-8"))["output_dir"] == loaded["output_dir"]
        saved = st.save_project("default", {"output_dir": "D:\\mnt\\rescue\\foreign"})
        assert saved["output_dir"] == str(st.project_dir("default").resolve())

    # 3. Q4: Bundled Fonts (<= 650 KB, zero "Inter"), Artworks (<= 250 KB), and Token Contrast (>= 4.5:1)
    fonts_dir = STUDIO_ROOT / "smartllm_studio" / "static" / "fonts"
    woff2_files = list(fonts_dir.glob("*.woff2"))
    total_font_bytes = sum(f.stat().st_size for f in woff2_files)
    assert len(woff2_files) == 6 and 0 < total_font_bytes <= 650 * 1024
    css_txt = (STUDIO_ROOT / "smartllm_studio" / "static" / "styles.css").read_text(encoding="utf-8")
    assert '"Inter"' not in css_txt and "'Inter'" not in css_txt

    art_dir = STUDIO_ROOT / "smartllm_studio" / "static" / "art"
    for art_stem in ("atelier_hero_prism", "stage_empty_wireframe", "zimage_optical_core"):
        for ext in ("webp", "avif"):
            ap = art_dir / f"{art_stem}.{ext}"
            assert ap.exists() and 0 < ap.stat().st_size <= 250 * 1024

    for fg in ("#eceef3", "#a4a9b8", "#c084fc", "#e5b869", "#4ade80", "#fbbf24", "#f87171"):
        for bg in ("#0b0d12", "#10131a", "#151923", "#1b2030"):
            cr = _contrast_ratio(fg, bg)
            assert cr >= 4.5, f"Token contrast {fg} on {bg} is {cr} < 4.5:1"

    # 4. Q5: i18n Key Parity
    i18n_dir = STUDIO_ROOT / "smartllm_studio" / "static" / "i18n"
    en_dict = json.loads((i18n_dir / "en.json").read_text(encoding="utf-8"))
    ru_dict = json.loads((i18n_dir / "ru.json").read_text(encoding="utf-8"))
    assert set(en_dict.keys()) == set(ru_dict.keys()), f"i18n key mismatch: {set(en_dict) ^ set(ru_dict)}"

    # 5. Q6 & Q7: Ephemeral Server (18090-18099), Mocked Engines, Lock/Memory Refusal & Browser Gate
    with tempfile.TemporaryDirectory(prefix="smartllm_studio_v2_gate_") as tmp:
        tmp_dir = Path(tmp)
        os.environ["XDG_CONFIG_HOME"] = str(tmp_dir / "xdg")
        temp_lock = tmp_dir / "test_gpu.lock"

        # Find ephemeral port in 18090..18099 (NEVER touching 8090)
        chosen_port = 18090
        for p in range(18090, 18100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", p)) != 0:
                    chosen_port = p
                    break

        # Create mock llama-server for SSE replay
        mock_llama_port = chosen_port + 10
        mock_llama_script = tmp_dir / "mock_llama.py"
        mock_llama_script.write_text(
            f"""#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import json, signal, sys

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{{"status":"ok"}}')
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for tok in ("MOCK_SSE_TOKEN_1 ", "MOCK_SSE_TOKEN_2"):
            chunk = json.dumps({{"choices": [{{"delta": {{"content": tok}}}}]}})
            self.wfile.write(f"data: {{chunk}}\\n\\n".encode("utf-8"))
        self.wfile.write(b"data: [DONE]\\n\\n")

signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
HTTPServer(("127.0.0.1", {mock_llama_port}), H).serve_forever()
""",
            encoding="utf-8",
        )

        srv, state = create_studio_server(
            host="127.0.0.1",
            port=chosen_port,
            repo_root=REPO_ROOT,
            lock_path_override=temp_lock,
            allow_lock_write=True,
            llm_port=mock_llama_port,
            projects_root_override=tmp_dir / "studio_projects",
        )
        thr = threading.Thread(target=srv.serve_forever, daemon=True)
        thr.start()
        base = f"http://127.0.0.1:{chosen_port}"

        try:
            # Test held lock refusal (on temp_lock in /tmp, never .system/gpu.lock)
            ext_proc = subprocess.Popen(
                [sys.executable, "-c", f"import fcntl, time; f=open({repr(str(temp_lock))}, 'a+'); fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB); time.sleep(30)"]
            )
            try:
                import time
                time.sleep(0.15)
                code_lock, raw_lock = _http_req(f"{base}/api/engine/llm/start", method="POST", payload={})
                assert code_lock == 409 and b"GPULockBusyError" in raw_lock, f"Expected 409 lock busy, got {code_lock}: {raw_lock}"
            finally:
                ext_proc.terminate()
                ext_proc.wait(timeout=5)

            # Test memory guard refusal
            os.environ["SMARTLLM_TEST_MEM_AVAIL_GIB"] = "2.0"
            try:
                code_mem, raw_mem = _http_req(f"{base}/api/engine/llm/start", method="POST", payload={"model_host_bytes": 1024**3})
                assert code_mem == 409 and b"MemoryGuardError" in raw_mem, f"Expected 409 memory guard, got {code_mem}: {raw_mem}"
            finally:
                del os.environ["SMARTLLM_TEST_MEM_AVAIL_GIB"]

            # Test mocked llama-server start + SSE /api/chat/stream replay + stop
            code_st, _ = _http_req(
                f"{base}/api/engine/llm/start",
                method="POST",
                payload={"mock_cmd": [sys.executable, str(mock_llama_script)]},
            )
            assert code_st == 200
            code_sse, sse_bytes = _http_req(f"{base}/api/chat/stream", method="POST", payload={"prompt": "Test SSE"})
            assert code_sse == 200 and b"MOCK_SSE_TOKEN_1" in sse_bytes and b"event: done" in sse_bytes
            _http_req(f"{base}/api/engine/llm/stop", method="POST", payload={})

            # Test mocked sd-cli image job + SSE events
            code_img, img_raw = _http_req(
                f"{base}/api/image/jobs",
                method="POST",
                payload={"prompt": "Prism test", "mock_sd_cmd": [sys.executable, "-c", "pass"]},
            )
            img_doc = json.loads(img_raw.decode("utf-8"))
            assert code_img == 200 and img_doc["status"] == "completed" and len(img_doc["variants"]) == 4
            code_ev, ev_raw = _http_req(f"{base}/api/image/jobs/{img_doc['job_id']}/events")
            assert code_ev == 200 and b'"stage": "completed"' in ev_raw

            # Test 6-variant 512x512 logo generator + selection + Constructor & Auto Orchestrator
            code_lg, lg_raw = _http_req(
                f"{base}/api/logo/generate",
                method="POST",
                payload={"name": "Nordic Craft", "description": "Timber acoustics studio", "logo_prompt": "Minimal interlocking arcs, navy and warm gold, no text", "lang": "en"},
            )
            lg_doc = json.loads(lg_raw.decode("utf-8"))
            assert code_lg == 200 and len(lg_doc["variants"]) == 6 and lg_doc.get("prompt_source") in ("human", "llm")
            for v_item in lg_doc["variants"]:
                _, v_bytes = _http_req(f"{base}{v_item['url']}")
                v_info = validate_png_bytes(v_bytes)
                assert v_info["width"] == 512 and v_info["height"] == 512

            ctor_dir = tmp_dir / "ctor_site"
            code_ctor, ctor_raw = _http_req(
                f"{base}/api/orchestrator/run",
                method="POST",
                payload={
                    "orchestrator_mode": "constructor",
                    "output_dir": str(ctor_dir),
                    "languages": "ru",
                    "name": "Керамика Севера",
                    "brief": "Мастерская авторской керамики и фарфора ручной работы",
                    "selected_logo_path": lg_doc["variants"][1]["path"],
                    "canon_id": "09_visual_storytelling",
                    "site_type": "single",
                    "selected_blocks": ["hero", "manifesto", "priorities", "pricing", "locations", "contact"],
                    "block_prompts": {
                        "hero": "Керамика Севера — фарфор и каменная масса ручной формовки.",
                        "manifesto": "Ручная керамика с характером | Каждая вещь проходит дровяной обжиг.",
                        "priorities": "Качество | Ручная работа | Прозрачные сроки | Поддержка",
                        "pricing": "Чайная пара: 4 500 ₽ | Обеденный сет: 18 000 ₽ | Ресторанная серия: 85 000 ₽",
                        "locations": "Москва | Санкт-Петербург | Онлайн",
                        "contact": "Закажите индивидуальный сервиз с обжигом в дровяной печи.",
                    },
                },
            )
            ctor_doc = json.loads(ctor_raw.decode("utf-8"))
            assert code_ctor == 200 and len(ctor_doc["orchestrator"]["tasks"]) == 5
            ctor_html = (ctor_dir / "index.html").read_text(encoding="utf-8")
            assert 'id="hero"' in ctor_html and 'id="pricing"' in ctor_html and 'id="contact"' in ctor_html
            assert 'id="manifesto"' in ctor_html and 'id="priorities"' in ctor_html and 'id="locations"' in ctor_html
            assert 'id="gallery"' not in ctor_html and "18 000 ₽" in ctor_html
            assert "LocalBusiness" in ctor_html and '"telephone"' in ctor_html
            assert "Quartz" not in ctor_html

            # Sub-agent pipeline: disk memory, ledger, review, final audit, resume
            assert (ctor_dir / "smartllm.md").exists()
            ctor_state = json.loads((ctor_dir / ".smartllm" / "state.json").read_text(encoding="utf-8"))
            assert all(s["status"] in ("done", "skipped") for s in ctor_state["steps"])
            assert (ctor_dir / ".smartllm" / "memory" / "foundation.json").exists()
            assert (ctor_dir / ".smartllm" / "memory" / "architecture.json").exists()
            assert (ctor_dir / ".smartllm" / "memory" / "structure" / "index.json").exists()
            assert (ctor_dir / ".smartllm" / "memory" / "review" / "index.json").exists()
            assert ctor_doc["orchestrator"]["final_audit"]["passed"] is True
            assert ctor_doc["orchestrator"]["pipeline"]["review"]["index"]["score"] >= 5
            code_ctor2, ctor2_raw = _http_req(
                f"{base}/api/orchestrator/run",
                method="POST",
                payload={
                    "orchestrator_mode": "constructor",
                    "output_dir": str(ctor_dir),
                    "languages": "ru",
                    "name": "Керамика Севера",
                    "brief": "Мастерская авторской керамики и фарфора ручной работы",
                    "selected_logo_path": lg_doc["variants"][1]["path"],
                    "canon_id": "09_visual_storytelling",
                    "site_type": "single",
                    "selected_blocks": ["hero", "manifesto", "priorities", "pricing", "locations", "contact"],
                    "block_prompts": {
                        "hero": "Керамика Севера — фарфор и каменная масса ручной формовки.",
                        "manifesto": "Ручная керамика с характером | Каждая вещь проходит дровяной обжиг.",
                        "priorities": "Качество | Ручная работа | Прозрачные сроки | Поддержка",
                        "pricing": "Чайная пара: 4 500 ₽ | Обеденный сет: 18 000 ₽ | Ресторанная серия: 85 000 ₽",
                        "locations": "Москва | Санкт-Петербург | Онлайн",
                        "contact": "Закажите индивидуальный сервиз с обжигом в дровяной печи.",
                    },
                },
            )
            ctor2_doc = json.loads(ctor2_raw.decode("utf-8"))
            assert code_ctor2 == 200 and ctor2_doc["orchestrator"]["pipeline"]["agents_reused"] > 0
            assert ctor2_doc["orchestrator"]["pipeline"]["agents_run"] == 0
            code_mem_api, mem_raw = _http_req(f"{base}/api/orchestrator/memory/default")
            assert code_mem_api == 200 and b"smartllm_md" in mem_raw

            auto_dir = tmp_dir / "auto_site"
            code_auto, auto_raw = _http_req(
                f"{base}/api/orchestrator/run",
                method="POST",
                payload={
                    "orchestrator_mode": "auto",
                    "output_dir": str(auto_dir),
                    "auto_prompt": "Многостраничный портал бюро промышленного дизайна «Вектор»: каталог услуг, тарифы, портфолио и контакты",
                    "languages": "ru",
                },
            )
            auto_doc = json.loads(auto_raw.decode("utf-8"))
            assert code_auto == 200 and all(t["status"] == "done" for t in auto_doc["orchestrator"]["tasks"])
            assert (auto_dir / "index.html").exists() and (auto_dir / "services.html").exists()
            auto_services = (auto_dir / "services.html").read_text(encoding="utf-8")
            assert 'id="process"' in auto_services and 'id="pricing"' in auto_services
            assert 'id="manifesto"' in auto_services and 'id="priorities"' in auto_services
            assert (auto_dir / "smartllm.md").exists()
            assert auto_doc["orchestrator"]["final_audit"]["passed"] is True
            assert auto_doc["orchestrator"]["pipeline"]["review_avg"] >= 5
            auto_index = (auto_dir / "index.html").read_text(encoding="utf-8")
            title_idx = re.search(r"<title>(.*?)</title>", auto_index).group(1)
            title_svc = re.search(r"<title>(.*?)</title>", auto_services).group(1)
            assert title_idx != title_svc, "per-page SEO titles must differ"
            assert "Quartz" not in auto_index and "Dr. Viktor" not in auto_index

            # Verify Opus B1-B3 security & packaging gates (DONATE.md, logo path confinement, JSON-LD </script> escape)
            assert (STUDIO_ROOT / "DONATE.md").exists() and (REPO_ROOT / "DONATE.md").exists()
            code_forb, _ = _http_req(
                f"{base}/api/logo/select",
                method="POST",
                payload={"project_id": "default", "path": "/etc/hosts"},
            )
            assert code_forb == 403, f"Expected 403 for outside logo path, got {code_forb}"

            xss_dir = tmp_dir / "xss_site"
            code_xss, _ = _http_req(
                f"{base}/api/orchestrator/run",
                method="POST",
                payload={
                    "orchestrator_mode": "constructor",
                    "output_dir": str(xss_dir),
                    "name": "Тест</script>Бюро",
                    "brief": "Проверка экранирования </script> внутри JSON-LD",
                    "selected_blocks": ["hero", "contact"],
                },
            )
            assert code_xss == 200
            xss_html = (xss_dir / "index.html").read_text(encoding="utf-8")
            assert "Тест</script>Бюро" not in xss_html and r"Тест<\/script>Бюро" in xss_html

            # Test ProjectDraft PUT/GET, /api/preview/<id>, and /api/export/<id> (folder + zip + PWYW post-export trigger)
            _http_req(f"{base}/api/settings", method="POST", payload={"support_mode": "pwyw", "exports_completed": 0, "support_card_dismissed": False})
            _, exp_raw = _http_req(f"{base}/api/export/default", method="POST", payload={"target_dir": str(tmp_dir / "exp_out"), "as_zip": True})
            exp_doc = json.loads(exp_raw.decode("utf-8"))
            assert exp_doc["exported"] is True and exp_doc["format"] == "zip" and exp_doc["show_support_card"] is True
            _http_req(f"{base}/api/settings", method="POST", payload={"support_mode": "free_launch"})

            # Run Browser Q7 Gate (CDP dead-control test, RU Latin scan, Lighthouse, 54 screenshots)
            shots_dir = tmp_dir / "shots"
            q7_proc = subprocess.run(
                ["/usr/bin/node", str(STUDIO_ROOT / "tests" / "browser_q7_gate.mjs"), base, str(shots_dir)],
                capture_output=True,
                text=True,
                check=True,
            )
            q7_rep = json.loads(q7_proc.stdout)
            assert q7_rep["unbound_controls_count"] == 0, f"Unbound controls found: {q7_rep['unbound_controls']}"
            assert q7_rep["console_errors_count"] == 0, f"Console errors: {q7_rep['console_errors']}"
            assert q7_rep["page_errors_count"] == 0
            assert q7_rep["external_requests_count"] == 0, f"External requests: {q7_rep['external_requests']}"
            assert q7_rep["lighthouse_accessibility"] >= 95, f"LH a11y {q7_rep['lighthouse_accessibility']} < 95 (failed: {q7_rep['failed_a11y_audits']})"
            assert q7_rep["lighthouse_best_practices"] >= 95, f"LH best-practices {q7_rep['lighthouse_best_practices']} < 95"
            assert q7_rep["ru_unexpected_latin_count"] == 0, f"Unexpected Latin in RU mode: {q7_rep['ru_unexpected_latin']}"
            assert q7_rep["screenshots_count"] == 54

            contact_info = _build_contact_sheet(shots_dir, REPO_ROOT / "reports" / "studio_v2_contact_sheet.png")
            results["browser_q7_gate"] = q7_rep
            results["contact_sheet"] = contact_info
        finally:
            state.gpu.cleanup_children()
            srv.shutdown()
            srv.server_close()

    # 6. Verify validate_harvest.py and run_combine.sh --self-test still pass 100%
    val_res = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "v2_harvest" / "validate_harvest.py")], capture_output=True, text=True, check=False)
    if val_res.returncode != 0:
        print("VALIDATOR_STDOUT:", val_res.stdout)
        print("VALIDATOR_STDERR:", val_res.stderr)
    assert val_res.returncode == 0, "validate_harvest.py failed"
    assert json.loads(val_res.stdout)["status"] == "PASS"
    comb_res = subprocess.run(["bash", str(REPO_ROOT / "run_combine.sh"), "--self-test"], capture_output=True, text=True, check=True)
    assert json.loads(comb_res.stdout)["self_test"] == "PASSED"

    results["status"] = "ALL_STUDIO_V2_GATES_PASSED"
    return results


if __name__ == "__main__":
    out = run_all_tests()
    print(json.dumps(out, indent=2, ensure_ascii=False))
