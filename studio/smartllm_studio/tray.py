"""Cross-platform system tray controller (PyQt6 Linux/Windows + WinForms + headless fallback)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from .config import STUDIO_ROOT
from .os_compat import open_chromeless_window, reveal_in_file_manager


def run_system_tray_or_wait(
    studio_url: str,
    projects_dir: Path,
    on_quit: Callable[[], None],
    no_tray: bool = False,
) -> str:
    """Start the PyQt6 system tray icon (smartllm-tray.svg) if available, or block cleanly."""
    if no_tray or os.environ.get("SMARTLLM_STUDIO_HEADLESS") == "1" or not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or os.name == "nt"):
        return "headless_no_tray"

    tray_svg = STUDIO_ROOT / "assets" / "smartllm-tray.svg"
    tray_png = STUDIO_ROOT / "assets" / "smartllm-studio.png"

    try:
        from PyQt6.QtGui import QAction, QIcon
        from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

        app = QApplication.instance() or QApplication([])
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return "tray_unavailable_fallback"

        icon_path = str(tray_svg if tray_svg.exists() else tray_png)
        tray = QSystemTrayIcon(QIcon(icon_path), app)
        tray.setToolTip("SmartLLM Studio v0.0.2-beta (127.0.0.1)")

        menu = QMenu()
        act_open = QAction("Open SmartLLM Studio (127.0.0.1)", menu)
        act_open.triggered.connect(lambda: open_chromeless_window(studio_url))
        menu.addAction(act_open)

        act_folder = QAction("Open Projects Folder", menu)
        act_folder.triggered.connect(lambda: reveal_in_file_manager(projects_dir))
        menu.addAction(act_folder)

        menu.addSeparator()
        act_quit = QAction("Quit SmartLLM Studio", menu)

        def _quit() -> None:
            on_quit()
            app.quit()

        act_quit.triggered.connect(_quit)
        menu.addAction(act_quit)

        tray.setContextMenu(menu)
        tray.show()
        app.exec()
        return "pyqt6_tray"
    except Exception:
        return "headless_fallback"
