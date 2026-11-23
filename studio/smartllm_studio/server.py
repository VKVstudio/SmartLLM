"""Loopback-only HTTP & SSE Backend for SmartLLM Studio v2 (Opus Spec Q6)."""

from __future__ import annotations

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import subprocess
import sys
import threading
from typing import Any
import urllib.request
from urllib.parse import parse_qs, quote, unquote, urlparse
import uuid

from . import __version__
from .blueprint import _safe_project_dir, compile_project_blueprint, default_project_draft, export_project_bundle
from .catalog import load_studio_catalog
from .config import DEFAULT_REPO_ROOT, STUDIO_ROOT, discover_studio_paths, load_edition_config, load_user_settings, save_user_settings
from .engines import GPUEngineController, GPULockBusyError, ImageJobManager, LLMEngineClient, MemoryGuardError
from .orchestrator import AVAILABLE_BLOCKS, PRESET_PAGES, ProjectOrchestrator, autofill_blocks_smart, build_default_block_descriptions, generate_random_starter_template, generate_six_logo_variants_512
from .os_compat import create_directory_safe, get_system_telemetry, is_cpu_test_mode, is_interactive_win_desktop, is_linux, list_directory_entries, pick_os_dialog, reveal_in_file_manager, subprocess_kwargs
from .pages import DEFAULT_PAGE_SLUGS, build_default_company, clean_page_blocks, default_page_blocks
from .sanitizer import ingest_brand_logo

STATIC_DIR = Path(__file__).resolve().parent / "static"
ASSETS_DIR = STUDIO_ROOT / "assets"
STUDIO_CSP = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data: blob:; font-src 'self'; frame-src 'self'; connect-src 'self'"


def assert_studio_loopback(host: str) -> None:
    if host != "127.0.0.1":
        raise ValueError(f"Security violation: SmartLLM Studio must bind strictly to '127.0.0.1', got '{host}'")


def _setup_skip_flags(paths: dict[str, Any]) -> list[str]:
    """Which bundle components are already present and need no download."""
    skips: list[str] = []
    if paths.get("gguf_model_exists") and paths.get("mmproj_exists"):
        skips.append("--skip-model")
    if paths.get("dit_model_exists") and paths.get("te_model_exists") and paths.get("vae_model_exists"):
        skips.append("--skip-zimage")
    if paths.get("llama_server_exists") and paths.get("sd_cli_exists"):
        skips.append("--skip-binaries")
    return skips


class StudioState:
    """In-memory and on-disk state registry for projects, previews, and lock-aware engines."""

    def __init__(
        self,
        repo_root: Path | None = None,
        lock_path_override: Path | None = None,
        allow_lock_write: bool = False,
        llm_port: int = 18080,
        projects_root_override: Path | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> None:
        self.instance_id = f"studio_{uuid.uuid4().hex[:8]}"
        self.setup_progress: dict[str, Any] = {"running": False, "done": False, "error": "", "line": ""}
        self.repo_root = (repo_root or DEFAULT_REPO_ROOT).resolve()
        self.cli_overrides = cli_overrides
        paths = discover_studio_paths(repo_root=self.repo_root, cli_overrides=cli_overrides)
        self.projects_root = Path(projects_root_override or paths["projects_root"]).resolve()
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self.preview_dirs: dict[str, Path] = {}
        self.exported_zips: dict[str, Path] = {}
        self.exports_dir = (self.projects_root / "_exports").resolve()
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        lock_p = lock_path_override or Path(paths["gpu_lock_path"])
        self.gpu = GPUEngineController(lock_path=lock_p, allow_lock_write=allow_lock_write)
        self.llm = LLMEngineClient(
            gpu=self.gpu,
            host="127.0.0.1",
            port=llm_port,
            server_bin=Path(paths["llama_server_bin"]),
            model_path=Path(paths["gguf_model_path"]),
        )
        self.image_jobs = ImageJobManager(
            gpu=self.gpu,
            llm=self.llm,
            out_root=self.projects_root / "_zimage_jobs",
            sd_cli_bin=Path(paths["sd_cli_bin"]),
            dit_model_path=Path(paths["dit_model_path"]),
            te_model_path=Path(paths["te_model_path"]),
            vae_model_path=Path(paths["vae_model_path"]),
            art_dir=ASSETS_DIR / "art",
        )
        self.logo_batches_dir = self.projects_root / "_logo_variants"
        self.logo_batches_dir.mkdir(parents=True, exist_ok=True)
        self.orchestrator = ProjectOrchestrator(self)
        self._canon_selector = None
        self.operation_lock = threading.Lock()
        self.operation_name = ""

    def begin_operation(self, name: str) -> bool:
        if not self.operation_lock.acquire(blocking=False):
            return False
        self.operation_name = name
        return True

    def try_begin_operation(self, name: str) -> bool:
        return self.begin_operation(name)

    def end_operation(self) -> None:
        self.operation_name = ""
        try:
            self.operation_lock.release()
        except RuntimeError:
            pass

    def _migrate_draft(self, draft: dict[str, Any]) -> dict[str, Any]:
        """Normalize saved projects created before the 20-canon / per-page model."""
        from .rag import StudioRAGSelector

        if self._canon_selector is None:
            self._canon_selector = StudioRAGSelector()
        deleted_canon = str(draft.get("canon_id") or "")
        if deleted_canon not in self._canon_selector.canon_cards:
            from .kb_loader import resolve_canon_id
            resolved = None
            for cid, card in sorted(self._canon_selector.canon_cards.items()):
                if deleted_canon in (card.get("legacy_ids") or []):
                    resolved = cid
                    break
            draft["canon_id"] = resolved or (resolve_canon_id(deleted_canon) if deleted_canon else "01_bento_grid")
        valid_slugs = set(DEFAULT_PAGE_SLUGS) | {"blog", "team", "faq", "legal"}
        page_map = draft.get("page_blocks") if isinstance(draft.get("page_blocks"), dict) else {}
        valid_slugs |= set(str(k) for k in page_map.keys())
        routes = draft.get("routes") if isinstance(draft.get("routes"), list) else []
        route_slugs = [str(r.get("slug") or "") for r in routes if isinstance(r, dict)]
        selected = [s for s in (draft.get("selected_pages") or route_slugs) if s in valid_slugs and s != "specs"]
        if not selected:
            selected = list(DEFAULT_PAGE_SLUGS)
        if not draft.get("selected_pages") and len(selected) <= 1:
            selected = list(DEFAULT_PAGE_SLUGS)
        if "index" not in selected:
            selected.insert(0, "index")
        site_type = str(draft.get("site_type") or ("single" if len(selected) <= 1 else "multi"))
        if site_type == "single" and len(selected) > 1:
            site_type = "multi"
        draft["site_type"] = "single" if site_type == "single" else "multi"
        draft["selected_pages"] = selected
        draft["page_blocks"] = clean_page_blocks(draft.get("page_blocks") or default_page_blocks(selected), selected)
        draft["selected_blocks"] = [
            b for slug in selected for b in draft["page_blocks"].get(slug, []) if b != "footer"
        ]
        draft["selected_blocks"] = list(dict.fromkeys(draft["selected_blocks"])) or ["hero", "contact"]
        if not isinstance(draft.get("company"), dict) or not draft.get("company"):
            draft["company"] = build_default_company(
                str(draft.get("name") or "Проект"),
                str(draft.get("brief") or draft.get("goal") or ""),
                "en" if str(draft.get("languages") or "").lower() == "en" else "ru",
            )
        from .templates_engine import normalize_motion_id
        if draft.get("motion"):
            draft["motion"] = normalize_motion_id(str(draft.get("motion")))
        return draft

    def project_dir(self, project_id: str) -> Path:
        safe = "".join(c for c in project_id if c.isalnum() or c in ("-", "_")) or "default"
        d = (self.projects_root / safe).resolve()
        d.mkdir(parents=True, exist_ok=True)
        return d

    def load_project(self, project_id: str) -> dict[str, Any]:
        pdir = self.project_dir(project_id)
        pfile = pdir / "project.json"
        if pfile.exists():
            try:
                draft = self._migrate_draft(json.loads(pfile.read_text(encoding="utf-8")))
                safe_out = _safe_project_dir(draft.get("output_dir"), pdir)
                if str(draft.get("output_dir") or "") != str(safe_out):
                    draft["output_dir"] = str(safe_out)
                    pfile.write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                return draft
            except Exception:
                pass
        draft = default_project_draft(project_id=project_id, repo_root=self.repo_root)
        draft["output_dir"] = str(pdir)
        pfile.write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return draft

    def save_project(self, project_id: str, data: dict[str, Any]) -> dict[str, Any]:
        pdir = self.project_dir(project_id)
        current = self.load_project(project_id)
        current.update(data)
        current = self._migrate_draft(current)
        current["id"] = project_id
        current["revision"] = int(current.get("revision", 1)) + 1
        raw_out = data.get("output_dir") if str(data.get("output_dir") or "").strip() else current.get("output_dir")
        current["output_dir"] = str(_safe_project_dir(raw_out, pdir))
        (pdir / "project.json").write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return current

    def register_preview(self, project_id: str, project_dir: Path, rev: int = 1) -> str:
        safe = "".join(c for c in project_id if c.isalnum() or c in ("-", "_")) or project_dir.name or "default"
        self.preview_dirs[safe] = project_dir.resolve()
        return f"/preview/{safe}/index.html?rev={rev}"


def create_studio_server(
    host: str = "127.0.0.1",
    port: int = 8090,
    repo_root: Path | None = None,
    lock_path_override: Path | None = None,
    allow_lock_write: bool = False,
    llm_port: int = 18080,
    projects_root_override: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> tuple[ThreadingHTTPServer, StudioState]:
    assert_studio_loopback(host)
    state = StudioState(
        repo_root=repo_root,
        lock_path_override=lock_path_override,
        allow_lock_write=allow_lock_write,
        llm_port=llm_port,
        projects_root_override=projects_root_override,
        cli_overrides=cli_overrides,
    )
    # Pre-compile default project so Live Stage has an instant preview ready
    default_bp = compile_project_blueprint(state.load_project("default"), repo_root=state.repo_root)
    state.register_preview("default", Path(default_bp["project_dir"]), rev=1)

    class StudioHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            pass

        def _send_json(self, code: int, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", STUDIO_CSP)
            self.end_headers()
            self.wfile.write(raw)

        def _send_file(self, file_path: Path, base_dir: Path | None = None, is_preview: bool = False, no_store: bool = False) -> None:
            if base_dir is not None:
                try:
                    if not file_path.resolve().is_relative_to(base_dir.resolve()):
                        return self._send_json(403, {"error": "FORBIDDEN_PATH"})
                except (OSError, ValueError):
                    return self._send_json(403, {"error": "FORBIDDEN_PATH"})
            if not file_path.exists() or not file_path.is_file():
                return self._send_json(404, {"error": "NOT_FOUND", "path": str(file_path)})
            data = file_path.read_bytes()
            ctype, _ = mimetypes.guess_type(str(file_path))
            ext_map = {".svg": "image/svg+xml", ".ico": "image/x-icon", ".woff2": "font/woff2", ".webp": "image/webp", ".avif": "image/avif"}
            ctype = ext_map.get(file_path.suffix.lower(), ctype or "application/octet-stream")
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
                ctype += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            if is_preview or no_store:
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Pragma", "no-cache")
            if not is_preview:
                self.send_header("Content-Security-Policy", STUDIO_CSP)
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _send_sse(self, events: list[tuple[str, dict[str, Any]]]) -> None:
            chunks = [f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n" for ev, data in events]
            raw = "".join(chunks).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            path = unquote(urlparse(self.path).path)

            def _safe_parts(raw: str) -> list[str]:
                return [p for p in raw.split("/") if p and p not in ("..", ".") and ":" not in p and "\\" not in p]

            if path in ("/", "/index.html"):
                return self._send_file(STATIC_DIR / "index.html", base_dir=STATIC_DIR, no_store=True)
            if path.startswith("/static/"):
                target_static = (STATIC_DIR / path[len("/static/") :]).resolve()
                no_store_static = target_static.suffix.lower() in {".html", ".js", ".css", ".json"}
                return self._send_file(target_static, base_dir=STATIC_DIR, no_store=no_store_static)
            if path.startswith("/assets/"):
                return self._send_file((ASSETS_DIR / path[len("/assets/") :]).resolve(), base_dir=ASSETS_DIR)
            if path.startswith("/preview/"):
                parts = _safe_parts(path[len("/preview/") :])
                if parts:
                    base_dir = state.preview_dirs.get(parts[0]) or state.project_dir(parts[0])
                    rel_f = "/".join(parts[1:]) or "index.html"
                    return self._send_file((base_dir / rel_f).resolve(), base_dir=base_dir, is_preview=True)
                return self._send_json(404, {"error": "PREVIEW_NOT_FOUND"})
            if path.startswith("/api/image/files/"):
                parts = _safe_parts(path[len("/api/image/files/") :])
                if len(parts) == 2:
                    return self._send_file((state.image_jobs.out_root / parts[0] / parts[1]).resolve(), base_dir=state.image_jobs.out_root, no_store=True)
                return self._send_json(404, {"error": "IMAGE_NOT_FOUND"})
            if path.startswith("/api/logo/files/"):
                parts = _safe_parts(path[len("/api/logo/files/") :])
                if len(parts) == 2:
                    return self._send_file((state.logo_batches_dir / parts[0] / parts[1]).resolve(), base_dir=state.logo_batches_dir, no_store=True)
                return self._send_json(404, {"error": "LOGO_NOT_FOUND"})
            if path == "/api/orchestrator/progress":
                prog = dict(state.orchestrator.active_status)
                prog["operation"] = state.operation_name
                prog["busy"] = state.operation_lock.locked()
                return self._send_json(200, prog)
            if path.startswith("/api/orchestrator/memory/"):
                pid_m = path.split("/")[3] or "default"
                draft_m = state.load_project(pid_m)
                pdir_m = Path(str(draft_m.get("output_dir") or state.project_dir(pid_m)))
                state_f = pdir_m / ".smartllm" / "state.json"
                md_f = pdir_m / "smartllm.md"
                return self._send_json(200, {
                    "project_dir": str(pdir_m),
                    "state": json.loads(state_f.read_text(encoding="utf-8")) if state_f.exists() else None,
                    "smartllm_md": md_f.read_text(encoding="utf-8") if md_f.exists() else None,
                })
            if path.startswith("/api/image/jobs/") and path.endswith("/events"):
                job_id = path.split("/")[4]
                evs = [("progress", ev) for ev in state.image_jobs.stream_job_events(job_id)]
                return self._send_sse(evs)
            if path == "/api/health":
                return self._send_json(200, {"product": "SmartLLM Studio", "version": __version__, "instance_id": state.instance_id, "repo_root": str(state.repo_root)})
            if path == "/api/engine":
                return self._send_json(200, state.gpu.status_dict())
            if path == "/api/status":
                settings = load_user_settings(repo_root=state.repo_root)
                edition = load_edition_config()
                if "support_mode" in settings:
                    edition["support"]["mode"] = settings["support_mode"]
                return self._send_json(200, {"status": "ok", "version": __version__, "instance_id": state.instance_id, "host": "127.0.0.1", "edition": edition, "engine": state.gpu.status_dict(), "telemetry": get_system_telemetry(), "paths": settings["paths"], "settings": settings})
            if path == "/api/catalog":
                cat = load_studio_catalog(repo_root=state.repo_root)
                cat["available_blocks"] = AVAILABLE_BLOCKS
                cat["preset_pages"] = PRESET_PAGES
                return self._send_json(200, cat)
            if path == "/api/settings":
                return self._send_json(200, load_user_settings(repo_root=state.repo_root))
            if path == "/api/setup/progress":
                return self._send_json(200, state.setup_progress)
            if path.startswith("/api/export/") and path.endswith("/download"):
                parts_exp = [p for p in path.split("/") if p]
                pid_exp = parts_exp[2] if len(parts_exp) >= 4 else "default"
                zip_path = state.exported_zips.get(pid_exp)
                if zip_path is None or not zip_path.is_file():
                    draft_exp = state.load_project(pid_exp)
                    pdir_exp = Path(str(draft_exp.get("output_dir") or state.project_dir(pid_exp)))
                    for cand_exp in (
                        state.exports_dir / f"{pdir_exp.name}_bundle.zip",
                        pdir_exp / f"{pdir_exp.name}_bundle.zip",
                    ):
                        if cand_exp.is_file():
                            zip_path = cand_exp
                            break
                if zip_path is None or not zip_path.is_file() or zip_path.suffix.lower() != ".zip":
                    return self._send_json(404, {"error": "EXPORT_ZIP_NOT_FOUND", "project_id": pid_exp})
                safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", zip_path.name).strip("_") or "site_bundle.zip"
                data = zip_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            if path == "/api/fs/list":
                q_dir = parse_qs(urlparse(self.path).query).get("dir", [""])[0]
                return self._send_json(200, list_directory_entries(q_dir, fallback_dir=state.projects_root))
            if path.startswith("/api/projects/"):
                pid = path.split("/")[3] or "default"
                return self._send_json(200, state.load_project(pid))
            self._send_json(404, {"error": "UNKNOWN_ENDPOINT", "path": path})

        def _read_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            return json.loads(raw) if raw.strip() else {}

        def do_PUT(self) -> None:
            path = unquote(urlparse(self.path).path)
            try:
                body = self._read_body()
                if path.startswith("/api/projects/"):
                    pid = path.split("/")[3] or "default"
                    saved = state.save_project(pid, body)
                    return self._send_json(200, saved)
            except Exception as exc:
                return self._send_json(400, {"error": type(exc).__name__, "message": str(exc)})
            self._send_json(404, {"error": "UNKNOWN_PUT_ENDPOINT", "path": path})

        def do_POST(self) -> None:
            path = unquote(urlparse(self.path).path)
            try:
                body = self._read_body()
            except Exception as exc:
                return self._send_json(400, {"error": "INVALID_JSON", "message": str(exc)})

            def begin_operation(name: str) -> bool:
                if state.begin_operation(name):
                    return True
                self._send_json(409, {"error": "OPERATION_IN_PROGRESS", "operation": state.operation_name, "message": "Another operation is already running. Wait for it to finish."})
                return False

            try:
                if path == "/api/studio/shutdown":
                    try:
                        state.llm.stop()
                    except Exception:
                        pass
                    state.gpu.cleanup_children()
                    self._send_json(200, {"status": "shutting_down"})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                if path == "/api/setup/auto":
                    if state.setup_progress.get("running"):
                        return self._send_json(409, {"error": "SETUP_ALREADY_RUNNING"})
                    settings = load_user_settings(repo_root=state.repo_root)
                    skips = _setup_skip_flags(settings.get("paths") or {})
                    if len(skips) >= 3:
                        return self._send_json(200, {"status": "nothing_to_do"})
                    script = state.repo_root / "scripts" / "release" / "setup_bundle.py"
                    if not script.exists():
                        script = state.repo_root / "setup_bundle.py"
                        if not script.exists():
                            url = f"https://github.com/VKVstudio/SmartLLM/releases/download/v{__version__}/setup_bundle.py"
                            try:
                                with urllib.request.urlopen(url, timeout=60) as resp:
                                    script.write_bytes(resp.read())
                            except Exception as exc:
                                return self._send_json(502, {"error": "SETUP_SCRIPT_DOWNLOAD_FAILED", "message": str(exc)[:200]})
                    cmd = [sys.executable, str(script), "--dest", str(state.repo_root), "--skip-studio", "--cleanup-parts", "--skip-deps", "--line-progress", *skips]

                    def _setup_worker() -> None:
                        try:
                            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **subprocess_kwargs())
                            if proc.stdout is not None:
                                for line in proc.stdout:
                                    state.setup_progress["line"] = line.strip()[:300]
                            rc = proc.wait()
                            state.setup_progress["done"] = True
                            state.setup_progress["error"] = "" if rc == 0 else f"exit code {rc}"
                            if rc == 0:
                                fresh = discover_studio_paths(repo_root=state.repo_root)
                                state.llm.server_bin = Path(fresh["llama_server_bin"])
                                state.llm.model_path = Path(fresh["gguf_model_path"])
                                state.image_jobs.sd_cli_bin = Path(fresh["sd_cli_bin"])
                                state.image_jobs.dit_model_path = Path(fresh["dit_model_path"])
                                state.image_jobs.te_model_path = Path(fresh["te_model_path"])
                                state.image_jobs.vae_model_path = Path(fresh["vae_model_path"])
                        except Exception as exc:
                            state.setup_progress["done"] = True
                            state.setup_progress["error"] = str(exc)[:300]
                        finally:
                            state.setup_progress["running"] = False

                    state.setup_progress.update({"running": True, "done": False, "error": "", "line": "Starting download..."})
                    threading.Thread(target=_setup_worker, daemon=True).start()
                    return self._send_json(200, {"status": "started", "skips": skips})
                if path == "/api/settings":
                    saved = save_user_settings(body, repo_root=state.repo_root)
                    sp = saved.get("paths") or {}
                    if sp.get("llama_server_bin"):
                        state.llm.server_bin = Path(str(sp["llama_server_bin"]))
                    if sp.get("gguf_model_path"):
                        state.llm.model_path = Path(str(sp["gguf_model_path"]))
                    if sp.get("sd_cli_bin"):
                        state.image_jobs.sd_cli_bin = Path(str(sp["sd_cli_bin"]))
                    if sp.get("dit_model_path"):
                        state.image_jobs.dit_model_path = Path(str(sp["dit_model_path"]))
                    if sp.get("te_model_path"):
                        state.image_jobs.te_model_path = Path(str(sp["te_model_path"]))
                    if sp.get("vae_model_path"):
                        state.image_jobs.vae_model_path = Path(str(sp["vae_model_path"]))
                    return self._send_json(200, {"status": "saved", "settings": saved})
                if path == "/api/engine/llm/start":
                    req_bytes = int(body["model_host_bytes"]) if "model_host_bytes" in body else None
                    res = state.llm.start(model_host_bytes=req_bytes, mock_cmd=body.get("mock_cmd"))
                    return self._send_json(200, res)
                if path == "/api/engine/llm/stop":
                    return self._send_json(200, state.llm.stop())
                if path == "/api/gpu/control":
                    act = str(body.get("action") or "release")
                    res = state.llm.stop() if act in ("stop", "release") else state.llm.start()
                    return self._send_json(200, {"gpu_state": res["state"], "host": "127.0.0.1"})
                if path == "/api/chat/stream":
                    msgs = body.get("messages") or [{"role": "user", "content": str(body.get("prompt") or "")}]
                    evs = list(state.llm.stream_chat(msgs, max_tokens=int(body.get("max_tokens", 128))))
                    return self._send_sse(evs)
                if path == "/api/chat/completion":
                    prompt_txt = str(body.get("prompt") or "Design an Astro 5 + GSAP landing page")
                    evs = list(state.llm.stream_chat([{"role": "user", "content": prompt_txt}]))
                    text = "".join(d.get("text", "") for kind, d in evs if kind == "token")
                    return self._send_json(200, {"status": "ok", "reply": text})
                if path == "/api/image/jobs":
                    if not begin_operation("image"):
                        return
                    try:
                        pid_img = str(body.get("project_id") or "default")
                        hero_target = state.project_dir(pid_img) / "assets" / "hero_primary.png"
                        job = state.image_jobs.create_job(
                            prompt=str(body.get("prompt") or "Architectural prism"),
                            canon_id=str(body.get("canon_id") or "01_bento_grid"),
                            aspect_ratio=str(body.get("aspect_ratio") or "16:9"),
                            mock_sd_cmd=body.get("mock_sd_cmd"),
                            target_hero_path=hero_target,
                        )
                        return self._send_json(200, job)
                    finally:
                        state.end_operation()
                if path in ("/api/os/pick", "/api/fs/pick-folder"):
                    kind = str(body.get("kind") or "folder")
                    dry = bool(body.get("dry_run", False))
                    interactive = is_interactive_win_desktop()
                    chosen = pick_os_dialog(kind=kind, filters=str(body.get("filters") or "*.svg *.png *.webp"), initial_dir=str(body.get("initial_dir") or ""), dry_run=dry)
                    fb = "web_picker" if (chosen is None and not dry and (not interactive or is_linux())) else ""
                    return self._send_json(200, {"path": chosen, "selected_dir": chosen, "interactive_desktop": interactive, "fallback": fb})
                if path in ("/api/os/reveal", "/api/fs/open-folder"):
                    dry_rev = bool(body.get("dry_run", False))
                    target = Path(str(body.get("path") or state.projects_root))
                    opened = reveal_in_file_manager(target, dry_run=dry_rev)
                    fb_rev = "web_picker" if (not opened and not dry_rev) else ""
                    return self._send_json(200, {"opened": opened, "path": str(target), "fallback": fb_rev})
                if path == "/api/fs/mkdir":
                    parent_dir = str(body.get("parent_dir") or state.projects_root)
                    folder_name = str(body.get("name") or "")
                    return self._send_json(200, create_directory_safe(parent_dir, folder_name))
                if path == "/api/orchestrator/random-template":
                    req_lang = str(body.get("lang") or "ru").strip() or "ru"
                    req_use_llm = bool(body.get("use_llm", True))
                    excl = [str(x) for x in (body.get("exclude_names") or []) if str(x).strip()]
                    tpl: dict[str, Any] | None = None
                    if req_use_llm and not is_cpu_test_mode() and state.try_begin_operation("random_template"):
                        try:
                            tpl = generate_random_starter_template(state, lang=req_lang, use_llm=True, exclude_names=excl)
                        finally:
                            state.end_operation()
                    if tpl is None:
                        tpl = generate_random_starter_template(state, lang=req_lang, use_llm=False, exclude_names=excl)
                    starter_payload = {
                        "id": "starter",
                        "name": tpl["name"],
                        "brief": tpl["brief"],
                        "goal": tpl["brief"],
                        "logo_prompt": tpl["logo_prompt"],
                        "languages": tpl["languages"],
                        "canon_id": tpl["canon_id"],
                        "polarity": tpl["polarity"],
                        "landing_preset": tpl["landing_preset"],
                        "motion": tpl["motion"],
                        "site_type": tpl["site_type"],
                        "selected_pages": tpl["selected_pages"],
                        "page_blocks": tpl["page_blocks"],
                        "selected_blocks": tpl["selected_blocks"],
                        "company": tpl["company"],
                        "output_dir": tpl["output_dir"],
                        "revision": 1,
                    }
                    bp_starter = compile_project_blueprint(starter_payload, repo_root=state.repo_root)
                    prev_starter = state.register_preview("starter", Path(bp_starter["project_dir"]), rev=1)
                    return self._send_json(200, {
                        "template": tpl,
                        "source": tpl["source"],
                        "preview_url": prev_starter,
                        "project_dir": bp_starter["project_dir"],
                    })
                if path == "/api/logo/generate":
                    if not begin_operation("logo"):
                        return
                    try:
                        bname = str(body.get("name") or body.get("brand_name") or "SmartLLM").strip()
                        desc = str(body.get("description") or body.get("brief") or "").strip()
                        logo_brief = str(body.get("logo_prompt") or body.get("logo_description") or "").strip()
                        lng = str(body.get("lang") or body.get("language") or "ru")
                        res = generate_six_logo_variants_512(
                            bname,
                            desc,
                            state.logo_batches_dir,
                            state=state,
                            logo_prompt=logo_brief,
                            lang=lng,
                        )
                        return self._send_json(200, res)
                    finally:
                        state.end_operation()
                if path == "/api/logo/select":
                    pid_l = str(body.get("project_id") or "default")
                    raw_p = str(body.get("path") or "").strip()
                    if not raw_p:
                        return self._send_json(400, {"error": "MISSING_LOGO_PATH"})
                    src_p = Path(raw_p).resolve()
                    allowed_roots = (state.logo_batches_dir.resolve(), state.projects_root.resolve(), STUDIO_ROOT.resolve())
                    if not any(src_p.is_relative_to(r) for r in allowed_roots):
                        return self._send_json(403, {"error": "FORBIDDEN_LOGO_PATH"})
                    if not src_p.exists() or not src_p.is_file():
                        return self._send_json(404, {"error": "LOGO_VARIANT_NOT_FOUND"})
                    raw_out_dir = str(body.get("output_dir") or "").strip().strip("`\"'")
                    pdir = _safe_project_dir(raw_out_dir, state.project_dir(pid_l))
                    res_logo = ingest_brand_logo(src_p.name, src_p.read_bytes(), pdir / "assets")
                    if res_logo.get("format") != "svg":
                        (pdir / "assets" / "brand-logo.svg").unlink(missing_ok=True)
                        (pdir / "assets" / "favicon.svg").unlink(missing_ok=True)
                    draft = state.save_project(pid_l, {"logo": res_logo, "selected_logo_path": str(src_p)})
                    bp = compile_project_blueprint(draft, repo_root=state.repo_root)
                    prev_url = state.register_preview(pid_l, Path(bp["project_dir"]), rev=draft["revision"])
                    return self._send_json(200, {"status": "selected", "logo": res_logo, "preview_url": prev_url})
                if path == "/api/orchestrator/autofill-blocks":
                    if not begin_operation("autofill"):
                        return
                    try:
                        bname = str(body.get("name") or "Проект").strip()
                        brief_t = str(body.get("brief") or body.get("goal") or "").strip()
                        blks = list(body.get("selected_blocks") or ["hero", "features", "about", "pricing", "faq", "contact", "footer"])
                        lng = str(body.get("lang") or "ru")
                        p_blocks = body.get("page_blocks") if isinstance(body.get("page_blocks"), dict) else None
                        comp = body.get("company") if isinstance(body.get("company"), dict) else None
                        return self._send_json(200, autofill_blocks_smart(state, bname, brief_t, blks, lang=lng, page_blocks=p_blocks, company=comp))
                    finally:
                        state.end_operation()
                if path == "/api/orchestrator/run":
                    if not begin_operation("build"):
                        return
                    try:
                        res_orch = state.orchestrator.execute_pipeline(body)
                        return self._send_json(200, res_orch)
                    finally:
                        state.end_operation()
                if path in ("/api/assets", "/api/logo/upload"):
                    fname = str(body.get("filename") or "logo.svg")
                    b64 = str(body.get("data_b64") or "")
                    pid = str(body.get("project_id") or "default")
                    raw_proj_dir = str(body.get("project_dir") or "").strip().strip("`\"'")
                    pdir = _safe_project_dir(raw_proj_dir, state.project_dir(pid))
                    res = ingest_brand_logo(fname, base64.b64decode(b64), pdir / "assets")
                    if res.get("format") in ("png", "webp"):
                        (pdir / "assets" / "brand-logo.svg").unlink(missing_ok=True)
                        (pdir / "assets" / "favicon.svg").unlink(missing_ok=True)
                    elif res.get("format") == "svg":
                        (pdir / "assets" / "brand-logo.png").unlink(missing_ok=True)
                        (pdir / "assets" / "favicon.png").unlink(missing_ok=True)
                        (pdir / "assets" / "brand-logo.webp").unlink(missing_ok=True)
                    save_payload: dict[str, Any] = {"logo": res, "selected_logo_path": str(pdir / res["logo_relpath"])}
                    if raw_proj_dir:
                        save_payload["output_dir"] = str(pdir)
                    draft = state.save_project(pid, save_payload)
                    bp = compile_project_blueprint(draft, repo_root=state.repo_root)
                    prev_url = state.register_preview(pid, Path(bp["project_dir"]), rev=draft["revision"])
                    return self._send_json(200, {"status": "sanitized", "logo": res, "selected_logo_path": draft["selected_logo_path"], "preview_url": prev_url})
                if path.startswith("/api/preview/"):
                    pid = path.split("/")[3] or "default"
                    draft = state.save_project(pid, body) if body else state.load_project(pid)
                    bp = compile_project_blueprint(draft, repo_root=state.repo_root)
                    prev_url = state.register_preview(pid, Path(bp["project_dir"]), rev=draft["revision"])
                    bp["preview_url"] = prev_url
                    return self._send_json(200, bp)
                if path.startswith("/api/export/"):
                    pid = path.split("/")[3] or "default"
                    draft = state.load_project(pid)
                    fallback_dir = Path(str(draft.get("output_dir") or state.project_dir(pid))).resolve()
                    src_dir = _safe_project_dir(body.get("project_dir"), fallback_dir) if body.get("project_dir") else fallback_dir
                    bp_file = src_dir / "project_blueprint.json"
                    bp: dict[str, Any] = {}
                    if (src_dir / "index.html").is_file() and bp_file.is_file():
                        try:
                            cand_bp = json.loads(bp_file.read_text(encoding="utf-8"))
                            if isinstance(cand_bp, dict) and cand_bp.get("audit_scorecard"):
                                bp = cand_bp
                        except Exception:
                            bp = {}
                    if not bp:
                        if str(draft.get("output_dir") or "") != str(src_dir):
                            draft = {**draft, "output_dir": str(src_dir)}
                        bp = compile_project_blueprint(draft, repo_root=state.repo_root)
                        src_dir = Path(bp["project_dir"]).resolve()
                    as_zip = bool(body.get("as_zip", False))
                    if as_zip:
                        raw_target = str(body.get("target_dir") or "").strip().strip("`\"'")
                        cand_target = _safe_project_dir(raw_target, state.exports_dir) if raw_target else state.exports_dir
                        target = cand_target if cand_target.resolve() != src_dir.resolve() else state.exports_dir
                    else:
                        target = _safe_project_dir(body.get("target_dir"), src_dir) if body.get("target_dir") else src_dir
                    exp = export_project_bundle(src_dir, target_dir=target, as_zip=as_zip)
                    if exp.get("format") == "zip" and exp.get("path"):
                        zip_file = Path(exp["path"]).resolve()
                        state.exported_zips[pid] = zip_file
                        exp["filename"] = zip_file.name
                        exp["download_url"] = f"/api/export/{quote(pid, safe='')}/download"
                    settings = load_user_settings(repo_root=state.repo_root)
                    exports_cnt = int(settings.get("exports_completed", 0)) + 1
                    save_user_settings({"exports_completed": exports_cnt}, repo_root=state.repo_root)
                    edition = load_edition_config()
                    show_support_card = (edition.get("support", {}).get("mode") == "pwyw" or settings.get("support_mode") == "pwyw") and exports_cnt == 1 and not settings.get("support_card_dismissed", False)
                    return self._send_json(200, {**exp, "exports_completed": exports_cnt, "show_support_card": show_support_card, "audit_scorecard": bp.get("audit_scorecard") or {}})
                if path in ("/api/build/express", "/api/build/blueprint"):
                    pid = str(body.get("id") or "default")
                    bp = compile_project_blueprint(body, repo_root=state.repo_root)
                    bp["preview_url"] = state.register_preview(pid, Path(bp["project_dir"]), rev=int(bp.get("revision", 1)))
                    return self._send_json(200, bp)
            except (GPULockBusyError, MemoryGuardError) as exc:
                return self._send_json(409, {"error": type(exc).__name__, "message": str(exc)})
            except Exception as exc:
                return self._send_json(400, {"error": type(exc).__name__, "message": str(exc)})
            self._send_json(404, {"error": "UNKNOWN_POST_ENDPOINT", "path": path})

    srv = ThreadingHTTPServer((host, port), StudioHandler)
    return srv, state
