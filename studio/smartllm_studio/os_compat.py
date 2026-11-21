"""Cross-platform (Linux + Windows 11) OS compatibility layer for SmartLLM Studio v2."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any
import webbrowser

_SMI_CACHE: dict[str, Any] = {"ts": 0.0, "gpu_info": None}
_SMI_CACHE_TTL_SEC = 1.5


def is_windows(platform_override: str | None = None) -> bool:
    plat = (platform_override or sys.platform).lower()
    return plat.startswith("win")


def is_linux(platform_override: str | None = None) -> bool:
    plat = (platform_override or sys.platform).lower()
    return plat.startswith("linux")


def subprocess_kwargs(new_session: bool = False) -> dict[str, Any]:
    """Return OS-appropriate subprocess keyword arguments (CREATE_NO_WINDOW on Windows)."""
    if is_windows():
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    if new_session:
        return {"start_new_session": True}
    return {}


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


def get_log_dir(platform_override: str | None = None) -> Path:
    """Persistent per-user log directory (works on any drive/folder, Linux + Windows)."""
    d = get_user_config_dir(platform_override) / "logs"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        import tempfile

        d = Path(tempfile.gettempdir()) / "smartllm-studio-logs"
        d.mkdir(parents=True, exist_ok=True)
    return d


def is_cpu_test_mode() -> bool:
    """True only for explicit headless CPU isolation (tests), never for a broken GPU setup."""
    return os.environ.get("CUDA_VISIBLE_DEVICES") == "" or os.environ.get("SMARTLLM_STUDIO_HEADLESS") == "1"


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
    mem_total_gib = 0.0
    mem_avail_gib = 0.0
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
    gpu_info = {"available": not cuda_masked, "vram_used_mib": 0.0, "vram_total_mib": 0.0, "mode": "cpu_isolated" if cuda_masked else "ready"}
    now_mono = time.monotonic()
    use_cache = (not cuda_masked) and (override_avail is None)
    if (
        use_cache
        and _SMI_CACHE.get("gpu_info") is not None
        and (now_mono - float(_SMI_CACHE.get("ts", 0.0))) < _SMI_CACHE_TTL_SEC
    ):
        gpu_info = dict(_SMI_CACHE["gpu_info"])
    elif not cuda_masked and (is_linux() or is_windows()) and shutil.which("nvidia-smi"):
        try:
            raw_smi = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                text=True, encoding="utf-8", errors="replace",
                timeout=2.5,
                **subprocess_kwargs(),
            ).strip().splitlines()[0]
            gpu_info["vram_total_mib"] = float(raw_smi.strip())
            compute_raw = subprocess.check_output(
                ["nvidia-smi", "--query-compute-apps=process_name,used_memory", "--format=csv,noheader,nounits"],
                text=True, encoding="utf-8", errors="replace",
                timeout=2.5,
                **subprocess_kwargs(),
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
            if not compute_values and not engine_active:
                if is_linux():
                    try:
                        pg = subprocess.run(
                            ["pgrep", "-f", "llama-server|sd-cli"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=0.8, check=False,
                            **subprocess_kwargs(),
                        )
                        engine_active = pg.returncode == 0 and bool(pg.stdout.strip())
                    except Exception:
                        pass
                elif is_windows():
                    for exe_name in ("llama-server.exe", "sd-cli.exe"):
                        try:
                            tl = subprocess.run(
                                ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=1.5, check=False,
                                **subprocess_kwargs(),
                            )
                            if tl.returncode == 0 and exe_name.lower() in (tl.stdout or "").lower():
                                engine_active = True
                                break
                        except Exception:
                            pass
            if compute_values:
                gpu_info["vram_used_mib"] = round(sum(compute_values), 1)
            elif engine_active:
                used_raw = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    text=True, encoding="utf-8", errors="replace",
                    timeout=2.5,
                    **subprocess_kwargs(),
                ).strip().splitlines()[0]
                if used_raw.strip().isdigit():
                    gpu_info["vram_used_mib"] = float(used_raw.strip())
            if use_cache:
                _SMI_CACHE["ts"] = now_mono
                _SMI_CACHE["gpu_info"] = dict(gpu_info)
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
            owner_setup = (
                "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
                "Add-Type -AssemblyName System.Windows.Forms; "
                "Add-Type -AssemblyName System.Drawing; "
                "$owner = New-Object System.Windows.Forms.Form; "
                "$owner.TopMost = $true; "
                "$owner.StartPosition = 'Manual'; "
                "$owner.Location = New-Object System.Drawing.Point(-32000,-32000); "
                "$owner.Size = New-Object System.Drawing.Size(1,1); "
            )
            if kind == "file":
                ps_cmd = (
                    owner_setup
                    + "try { "
                    "$f = New-Object System.Windows.Forms.OpenFileDialog; "
                    "$f.Filter = 'Brand Assets (*.svg;*.png;*.webp)|*.svg;*.png;*.webp'; "
                    "if ($f.ShowDialog($owner) -eq 'OK') { Write-Output $f.FileName } "
                    "} finally { $owner.Dispose() }"
                )
            else:
                ps_cmd = (
                    owner_setup
                    + "try { "
                    "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                    "if ($d.ShowDialog($owner) -eq 'OK') { Write-Output $d.SelectedPath } "
                    "} finally { $owner.Dispose() }"
                )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-STA", "-Command", ps_cmd],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=120.0, check=False,
                **subprocess_kwargs(),
            )
            return res.stdout.strip() or None

        # Linux: zenity -> kdialog -> None (UI fallback)
        if shutil.which("zenity"):
            cmd = ["zenity", "--file-selection"] + (["--directory"] if kind == "folder" else [f"--file-filter={filters}"])
            if initial_dir and Path(initial_dir).exists():
                cmd.append(f"--filename={initial_dir.rstrip('/')}/")
            res = subprocess.run(
                cmd,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=120.0, check=False,
                **subprocess_kwargs(),
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        if shutil.which("kdialog"):
            cmd = (
                ["kdialog", "--getexistingdirectory", initial_dir or str(Path.home())]
                if kind == "folder"
                else ["kdialog", "--getopenfilename", initial_dir or str(Path.home()), filters]
            )
            res = subprocess.run(
                cmd,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=120.0, check=False,
                **subprocess_kwargs(),
            )
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
        target_path = Path(target_path)
        if is_windows():
            if not target_path.suffix:
                target_path.mkdir(parents=True, exist_ok=True)
            norm_path = os.path.normpath(str(target_path))
            subprocess.Popen(["explorer.exe", norm_path])
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
    if is_windows():
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        explicit_paths = [
            Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(pf86) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(local_app) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(pf86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(pf) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ]
        win_candidates: list[str] = [str(p) for p in explicit_paths if p.is_file()]
        for name in ("chrome.exe", "msedge.exe"):
            found = shutil.which(name)
            if found and found not in win_candidates:
                win_candidates.append(found)
        for exe in win_candidates:
            try:
                subprocess.Popen([exe, f"--app={url}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"app_window:{exe}"
            except OSError:
                continue
    else:
        for b in ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser", "brave-browser"):
            exe = shutil.which(b)
            if exe:
                try:
                    subprocess.Popen(
                        [exe, f"--app={url}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    return f"app_window:{exe}"
                except OSError:
                    continue
    webbrowser.open(url)
    return "webbrowser"
