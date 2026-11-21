#!/usr/bin/env python3
"""CLI & Single-Instance 8090 Handoff Launcher for SmartLLM Studio v2 (Opus Spec Q6)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import sys
import threading
from typing import Any
import urllib.request

from . import __version__
from .config import DEFAULT_REPO_ROOT, discover_studio_paths, load_edition_config
from .os_compat import get_log_dir, open_chromeless_window
from .server import assert_studio_loopback, create_studio_server
from .tray import run_system_tray_or_wait


def _studio_log(msg: str) -> None:
    """Persistent launcher log (visible even when the Windows launcher runs hidden via VBS)."""
    try:
        from datetime import datetime, timezone

        line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}\n"
        with open(get_log_dir() / "studio.log", "a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        pass


def _probe_existing_studio(port: int, repo_root: Path | None = None) -> dict | None:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("product") == "SmartLLM Studio":
                    if repo_root is not None:
                        rem_root = data.get("repo_root")
                        if data.get("version") != __version__ or not rem_root or Path(str(rem_root)).resolve() != repo_root.resolve():
                            _studio_log(
                                f"existing studio mismatch on port={port}: remote_version={data.get('version')} "
                                f"local_version={__version__} remote_root={rem_root} local_root={repo_root}"
                            )
                            return None
                    return data
    except Exception:
        pass
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=f"SmartLLM Studio v{__version__} — Local Offline Multimodal Web & Design Atelier (127.0.0.1)."
    )
    parser.add_argument("--version", action="version", version=f"SmartLLM Studio v{__version__}")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host (MUST be 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8090, help="Bind port on 127.0.0.1 (default: 8090)")
    parser.add_argument("--model", type=str, default="", help="CLI override for GGUF model path")
    parser.add_argument("--no-browser", action="store_true", help="Do not launch browser/app window on startup")
    parser.add_argument("--no-tray", action="store_true", help="Run without system tray icon")
    parser.add_argument("--silent-launch", action="store_true", help="Launched silently via Windows VBS wrapper")
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT, help="Path to SmartLLM repository root")
    parser.add_argument("--check-config", action="store_true", help="Print discovered 5-tier paths and edition config as JSON")
    args = parser.parse_args(argv)

    try:
        assert_studio_loopback(args.host)
    except ValueError as exc:
        print(json.dumps({"error": "SECURITY_VIOLATION", "message": str(exc)}), file=sys.stderr)
        return 2

    cli_overrides = {"gguf_model_path": args.model} if args.model else None
    if args.check_config:
        print(
            json.dumps(
                {
                    "version": __version__,
                    "edition": load_edition_config(),
                    "paths": discover_studio_paths(repo_root=args.repo_root, cli_overrides=cli_overrides),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    _studio_log(f"launch host={args.host} port={args.port} repo_root={args.repo_root} no_browser={args.no_browser} no_tray={args.no_tray}")
    try:
        return _run_server(args)
    except Exception as exc:
        import traceback

        _studio_log(f"FATAL {type(exc).__name__}: {exc}\n{traceback.format_exc()}")
        print(json.dumps({"error": type(exc).__name__, "message": str(exc), "log": str(get_log_dir() / "studio.log")}), file=sys.stderr)
        return 1


def _run_server(args: argparse.Namespace) -> int:
    # Single-instance handoff (Q6): if args.port has our product running, open browser to it and exit 0; else try 8091..8099
    existing = _probe_existing_studio(args.port, repo_root=args.repo_root)
    if existing is not None:
        url = f"http://127.0.0.1:{args.port}/"
        if not args.no_browser:
            open_chromeless_window(url)
        _studio_log(f"attached_existing url={url} instance_id={existing.get('instance_id')}")
        print(json.dumps({"status": "attached_existing", "studio_url": url, "instance_id": existing.get("instance_id")}), flush=True)
        return 0

    candidates = [args.port] if args.port != 8090 else list(range(8090, 8100))
    cli_overrides = {"gguf_model_path": args.model} if args.model else None
    srv = None
    state = None
    import errno

    bind_retry_codes = (
        errno.EADDRINUSE,
        errno.EACCES,
        getattr(errno, "WSAEADDRINUSE", 10048),
        getattr(errno, "WSAEACCES", 10013),
    )

    for cand_port in candidates:
        try:
            srv, state = create_studio_server(
                host="127.0.0.1",
                port=cand_port,
                repo_root=args.repo_root,
                allow_lock_write=True,
                cli_overrides=cli_overrides,
            )
            break
        except OSError as exc:
            if exc.errno in bind_retry_codes or getattr(exc, "winerror", None) in bind_retry_codes:
                continue
            _studio_log(f"SERVER_CREATE_FAILED port={cand_port}: {type(exc).__name__}: {exc}")
            raise

    if srv is None or state is None:
        _studio_log(f"PORT_BIND_FAILED ports_tried={candidates}")
        print(json.dumps({"error": "PORT_BIND_FAILED", "ports_tried": candidates}), file=sys.stderr)
        return 1

    def _handle_termination(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle_termination)

    actual_port = srv.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/"
    startup = {"studio_url": url, "version": __version__, "host": "127.0.0.1", "port": actual_port, "instance_id": state.instance_id}
    _studio_log(f"started {json.dumps(startup)}")
    print(json.dumps(startup), flush=True)

    if not args.no_browser:
        open_chromeless_window(url)

    if args.no_tray:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            try:
                state.llm.stop()
            except Exception:
                pass
            state.gpu.cleanup_children()
            srv.server_close()
        _studio_log("stopped (no-tray)")
        return 0

    srv_thread = threading.Thread(target=srv.serve_forever, daemon=True)
    srv_thread.start()
    mode = run_system_tray_or_wait(url, state.projects_root, on_quit=srv.shutdown, no_tray=args.no_tray)
    _studio_log(f"tray_mode={mode}")
    if mode.startswith("headless") or mode.startswith("tray_unavailable"):
        try:
            srv_thread.join()
        except KeyboardInterrupt:
            srv.shutdown()
    try:
        state.llm.stop()
    except Exception:
        pass
    state.gpu.cleanup_children()
    srv.server_close()
    _studio_log("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
