#!/usr/bin/env python3
"""Centralized Cross-Platform Path & Toolchain Resolution for SmartLLM (Linux / Windows)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

IS_WINDOWS: bool = sys.platform == "win32"
IS_LINUX: bool = sys.platform.startswith("linux")

ROOT: Path = Path(os.environ.get("SMARTLLM_ROOT", Path(__file__).resolve().parents[1])).resolve()
SCRIPTS_DIR: Path = ROOT / "scripts"
EVAL_DIR: Path = ROOT / "eval"
SUITE_DIR: Path = EVAL_DIR / "suite"
HOLDOUT_DIR: Path = EVAL_DIR / "holdout"
TASKS_JSON: Path = SUITE_DIR / "tasks.json"
TASKS_DIR: Path = SUITE_DIR / "tasks"
RUNS_DIR: Path = SUITE_DIR / "runs"
RESULTS_DIR: Path = SUITE_DIR / "results"
EVAL_GATE_V1_YAML: Path = SUITE_DIR / "eval_gate_v1.yaml"

MODELS_DIR: Path = ROOT / "models"
DONOR_DIR: Path = MODELS_DIR / "Qwen3.8-Flash-Next"
MMPROJ_PATH: Path = MODELS_DIR / "mmproj-Qwen3.8-Flash-Next-BF16.gguf"
IQ3_S_PATH: Path = MODELS_DIR / "SmartLLM-205E-IQ3_S.gguf"
IQ3_XXS_PATH: Path = MODELS_DIR / "SmartLLM-205E-IQ3_XXS.gguf"
VISION_PNG: Path = ROOT / "data" / "calib" / "images" / "canon_en_canon_neoswiss_desktop.png"

STEP7_RAW_DIR: Path = ROOT / "research" / "step7_raw"
STEP8_RAW_DIR: Path = ROOT / "research" / "step8_raw"
RAW_STEP7_DIR: Path = STEP7_RAW_DIR
RAW_STEP8_DIR: Path = STEP8_RAW_DIR
SYSTEM_DIR: Path = ROOT / ".system"

LINUX_CACHE_DIR: Path = Path(os.environ.get("SMARTLLM_CACHE_DIR", str(Path.home() / ".cache" / "smartllm")))
WINDOWS_SCRATCH_DIR: Path = Path(os.environ.get("SMARTLLM_SCRATCH_DIR", "/mnt/windows/smartllm_scratch"))


def get_python_exe() -> Path:
    """Resolve active Python interpreter (.venv_linux on Linux, .venv on Windows, or sys.executable)."""
    env_py = os.environ.get("SMARTLLM_PYTHON_EXE")
    if env_py and os.path.exists(env_py):
        return Path(env_py)
    if IS_LINUX:
        candidates = [
            ROOT / ".venv_linux" / "bin" / "python",
            LINUX_CACHE_DIR / "venv_linux" / "bin" / "python",
        ]
    else:
        candidates = [
            ROOT / ".venv" / "Scripts" / "python.exe",
        ]
    for cand in candidates:
        if cand.exists():
            return cand
    return Path(sys.executable)


def get_node_exe() -> Path:
    """Resolve Node.js binary path across CachyOS Linux and Windows."""
    env_node = os.environ.get("SMARTLLM_NODE_EXE")
    if env_node and os.path.exists(env_node):
        return Path(env_node)
    which_node = shutil.which("node")
    if which_node:
        return Path(which_node)
    if IS_LINUX:
        return Path("/usr/bin/node")
    return Path(r"C:\Program Files\nodejs\node.exe")


def get_chrome_exe() -> Path:
    """Resolve Headless Chrome / Chromium binary path."""
    env_chrome = os.environ.get("SMARTLLM_CHROME_EXE")
    if env_chrome and os.path.exists(env_chrome):
        return Path(env_chrome)
    for name in ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return Path(found)
    if IS_LINUX:
        return Path("/usr/bin/google-chrome-stable")
    return Path(r"C:\Users\user\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe")


def get_llama_bin_dir() -> Path:
    """Resolve llama.cpp binary directory (`build_linux/bin` on Linux, `build/bin` on Windows)."""
    env_bin = os.environ.get("SMARTLLM_LLAMA_BIN_DIR")
    if env_bin and os.path.exists(env_bin):
        return Path(env_bin)
    if IS_LINUX:
        candidates = [
            ROOT / "tools" / "llama.cpp" / "build_linux" / "bin",
            LINUX_CACHE_DIR / "llama_build" / "bin",
            ROOT / "tools" / "llama.cpp" / "build" / "bin",
        ]
        for c in candidates:
            if c.exists():
                return c
        return candidates[0]
    return ROOT / "tools" / "llama.cpp" / "build" / "bin"


def get_llama_server_exe() -> Path:
    """Resolve llama-server executable path."""
    bin_dir = get_llama_bin_dir()
    return bin_dir / ("llama-server" if not IS_WINDOWS else "llama-server.exe")


PYTHON_EXE: Path = get_python_exe()
NODE_EXE: Path = get_node_exe()
CHROME_EXE: Path = get_chrome_exe()
LLAMA_BIN_DIR: Path = get_llama_bin_dir()
SERVER_EXE: Path = get_llama_server_exe()

TYPESCRIPT_DIR: Path = Path(
    os.environ.get(
        "SMARTLLM_TS_DIR",
        "/usr/lib/code/extensions/node_modules/typescript"
        if IS_LINUX
        else r"C:\projects\VKVstudio\node_modules\typescript",
    )
)
TYPESCRIPT_LIB_JS: Path = TYPESCRIPT_DIR / "lib" / "typescript.js"

def _default_mcp_third_party() -> str:
    if IS_LINUX:
        dl = Path.home() / "Downloads"
        if dl.is_dir():
            for child in sorted(dl.iterdir()):
                cand = child / "resources" / "app.asar.unpacked" / "node_modules" / "chrome-devtools-mcp" / "build" / "src" / "third_party" / "index.js"
                if cand.exists():
                    return str(cand)
        return str(Path.home() / ".cache" / "smartllm" / "chrome-devtools-mcp" / "index.js")
    return str(Path.home() / "AppData" / "Local" / "Programs" / "chrome-devtools-mcp" / "index.js")


MCP_THIRD_PARTY_INDEX: Path = Path(
    os.environ.get("SMARTLLM_MCP_THIRD_PARTY", _default_mcp_third_party())
)


def assert_local_endpoint(url: str) -> None:
    """Enforce strictly offline local inference invariant (127.0.0.1 / localhost only)."""
    if not (url.startswith("http://127.0.0.1") or url.startswith("http://localhost")):
        raise RuntimeError(
            f"EXTERNAL API FORBIDDEN BY PROJECT RULES (CLAUDE.md §4.3): {url}. "
            "Only local 127.0.0.1 / localhost endpoints are permitted."
        )
