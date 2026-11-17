"""Cross-platform (Linux + Windows 11) OS compatibility layer for SmartLLM Studio v2."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
import webbrowser


def is_windows(platform_override: str | None = None) -> bool:
    plat = (platform_override or sys.platform).lower()
    return plat.startswith("win")


def is_linux(platform_override: str | None = None) -> bool:
    plat = (platform_override or sys.platform).lower()
    return plat.startswith("linux")


def current_platform_tag(platform_override: str | None = None) -> str:
    return "windows" if is_windows(platform_override) else "linux"


def get_user_config_dir(platform_override: str | None = None) -> Path:
    """Return per-OS user config directory (~/.config/smartllm-studio or %APPDATA%\\SmartLLM Studio)."""
    if is_windows(platform_override):
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "SmartLLM Studio"
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(xdg) / "smartllm-studio"


def get_user_config_path(platform_override: str | None = None) -> Path:
    return get_user_config_dir(platform_override) / "config.json"


def get_user_settings_path(platform_override: str | None = None) -> Path:
    """Alias for config.json (keeps backward compatibility)."""
    return get_user_config_path(platform_override)


class CrossPlatformFileLock:
    """Non-blocking exclusive file lock supporting Linux (fcntl) and Windows (msvcrt)."""

    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        self._fh: Any = None

    def acquire(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "a+", encoding="utf-8")
        try:
            if is_windows():
                import msvcrt  # type: ignore

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            self.release()
            return False

    def release(self) -> None:
        if self._fh is not None:
            try:
                if is_windows():
                    import msvcrt  # type: ignore

                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None


def get_system_telemetry() -> dict[str, Any]:
    """Read host RAM, Zero-Swap status, and GPU status without touching CUDA when masked."""
    mem_total_gib = 31.06
    mem_avail_gib = 24.0
    disk_swap_used_mib = 0.0
    zram_used_mib = 0.0

    if is_linux() and Path("/proc/meminfo").exists():
        info: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                info[parts[0].rstrip(":")] = int(parts[1])
        mem_total_gib = round(info.get("MemTotal", 0) / (1024.0 * 1024.0), 2)
        mem_avail_gib = round(info.get("MemAvailable", 0) / (1024.0 * 1024.0), 2)
        if Path("/proc/swaps").exists():
            for sline in Path("/proc/swaps").read_text(encoding="utf-8").splitlines()[1:]:
                sp = sline.split()
                if len(sp) >= 4 and sp[3].isdigit():
                    used_mib = int(sp[3]) / 1024.0
                    if "zram" in sp[0]:
                        zram_used_mib += round(used_mib, 1)
                    else:
                        disk_swap_used_mib += round(used_mib, 1)
    elif is_windows():
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
            mem_total_gib = round(stat.ullTotalPhys / (1024.0**3), 2)
            mem_avail_gib = round(stat.ullAvailPhys / (1024.0**3), 2)
        except Exception:
            pass

    override_avail = os.environ.get("SMARTLLM_TEST_MEM_AVAIL_GIB")
    if override_avail is not None:
        mem_avail_gib = float(override_avail)

    cuda_masked = os.environ.get("CUDA_VISIBLE_DEVICES", None) == ""
    gpu_info = {"available": not cuda_masked, "vram_used_mib": 0.0, "vram_total_mib": 12282.0, "mode": "cpu_isolated" if cuda_masked else "ready"}
    if not cuda_masked and is_linux():
        try:
            raw_smi = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                text=True,
                timeout=2.5,
            ).strip().splitlines()[0]
            gpu_info["vram_total_mib"] = float(raw_smi.strip())
            compute_raw = subprocess.check_output(
                ["nvidia-smi", "--query-compute-apps=process_name,used_memory", "--format=csv,noheader,nounits"],
                text=True,
                timeout=2.5,
            ).strip()
            compute_values = []
            engine_active = False
            for line in compute_raw.splitlines():
                parts = [part.strip() for part in line.split(",")]
                if len(parts) < 2:
                    continue
                name, mem = parts[0], parts[1]
                if "llama-server" in name or "sd-cli" in name:
                    engine_active = True
                    if mem.isdigit():
                        compute_values.append(float(mem))
            if not engine_active:
                try:
                    pg = subprocess.run(["pgrep", "-f", "llama-server|sd-cli"], capture_output=True, text=True, timeout=0.8, check=False)
                    engine_active = pg.returncode == 0 and bool(pg.stdout.strip())
                except Exception:
                    pass
            if compute_values:
                gpu_info["vram_used_mib"] = round(sum(compute_values), 1)
            elif engine_active:
                used_raw = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    text=True,
                    timeout=2.5,
                ).strip().splitlines()[0]
                if used_raw.strip().isdigit():
                    gpu_info["vram_used_mib"] = float(used_raw.strip())
        except Exception:
            pass
    return {
        "os": current_platform_tag(),
        "mem_total_gib": mem_total_gib,
        "mem_avail_gib": mem_avail_gib,
        "disk_swap_used_mib": disk_swap_used_mib,
        "zram_used_mib": zram_used_mib,
        "zero_swap_ok": disk_swap_used_mib == 0.0 and mem_avail_gib >= 3.0,
        "gpu": gpu_info,
    }


def pick_os_dialog(
    kind: str = "folder",
    filters: str = "*.svg *.png *.webp",
    initial_dir: str = "",
    dry_run: bool = False,
) -> str | None:
    """Open native OS folder/file dialog (Linux zenity->kdialog, Windows PowerShell STA, 120s timeout)."""
    if dry_run or os.environ.get("SMARTLLM_STUDIO_HEADLESS") == "1":
        if kind == "file":
            return str(Path(initial_dir or Path.home()) / "brand-logo.svg")
        return initial_dir or str(Path.home() / "SmartLLMProjects")

    try:
        if is_windows():
            if kind == "file":
                ps_cmd = (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "$f = New-Object System.Windows.Forms.OpenFileDialog; "
                    "$f.Filter = 'Brand Assets (*.svg;*.png;*.webp)|*.svg;*.png;*.webp'; "
                    "if ($f.ShowDialog() -eq 'OK') { Write-Output $f.FileName }"
                )
            else:
                ps_cmd = (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                    "if ($d.ShowDialog() -eq 'OK') { Write-Output $d.SelectedPath }"
                )
            res = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps_cmd], capture_output=True, text=True, timeout=120.0, check=False)
            return res.stdout.strip() or None

        # Linux: zenity -> kdialog -> None (UI fallback)
        if shutil.which("zenity"):
            cmd = ["zenity", "--file-selection"] + (["--directory"] if kind == "folder" else [f"--file-filter={filters}"])
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120.0, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        if shutil.which("kdialog"):
            cmd = (
                ["kdialog", "--getexistingdirectory", initial_dir or str(Path.home())]
                if kind == "folder"
                else ["kdialog", "--getopenfilename", initial_dir or str(Path.home()), filters]
            )
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120.0, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
    except Exception:
        pass
    return None


def pick_folder_native(initial_dir: str = "", dry_run: bool = False) -> str | None:
    return pick_os_dialog(kind="folder", initial_dir=initial_dir, dry_run=dry_run)


def reveal_in_file_manager(target_path: Path, dry_run: bool = False) -> bool:
    """Open target directory in OS file manager (xdg-open on Linux, explorer.exe on Windows)."""
    if dry_run or os.environ.get("SMARTLLM_STUDIO_HEADLESS") == "1":
        return True
    try:
        if is_windows():
            subprocess.Popen(["explorer.exe", str(target_path)])
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", str(target_path)])
        return True
    except Exception:
        return False


def open_chromeless_window(url: str, dry_run: bool = False) -> str:
    """Launch chromeless --app= window in Chrome/Chromium/Edge or fallback to webbrowser."""
    if not url.startswith("http://127.0.0.1"):
        raise ValueError(f"Refusing non-loopback URL: {url}")
    if dry_run or os.environ.get("SMARTLLM_STUDIO_HEADLESS") == "1":
        return f"dry_run:{url}"
    candidates = ["msedge.exe", "chrome.exe"] if is_windows() else ["google-chrome-stable", "chromium", "google-chrome"]
    for b in candidates:
        exe = shutil.which(b)
        if exe:
            subprocess.Popen([exe, f"--app={url}"])
            return f"app_window:{exe}"
    webbrowser.open(url)
    return "webbrowser"
