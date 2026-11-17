"""5-Tier Path Discovery, Edition Schema v2, and Config Management for SmartLLM Studio (Opus Spec Q2, Q3)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .os_compat import current_platform_tag, get_user_config_path, is_windows

STUDIO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_ROOT = STUDIO_ROOT.parent
EDITION_CONFIG_PATH = STUDIO_ROOT / "config" / "edition.json"

ENV_KEY_MAP = {
    "gguf_model_path": "SMARTLLM_MODEL_PATH",
    "mmproj_path": "SMARTLLM_MMPROJ_PATH",
    "llama_server_bin": "LLAMA_SERVER_BIN",
    "sd_cli_bin": "SD_CLI_BIN",
    "dit_model_path": "ZIMAGE_DIT_PATH",
    "te_model_path": "ZIMAGE_TE_PATH",
    "vae_model_path": "ZIMAGE_VAE_PATH",
}


def load_edition_config(edition_path: Path = EDITION_CONFIG_PATH) -> dict[str, Any]:
    """Load studio/config/edition.json (schema v2)."""
    if edition_path.exists():
        return json.loads(edition_path.read_text(encoding="utf-8"))
    return {
        "schema": 2,
        "product": "SmartLLM Studio",
        "version": "0.0.1-beta",
        "license_spdx": "FSL-1.1-ALv2",
        "license_change_date": "2028-11-16",
        "telemetry": False,
        "update_check": False,
        "author": {
            "name": "VKVstudio",
            "url": "https://vkvstudio.com",
            "github": "https://github.com/VKVstudio",
        },
        "support": {
            "mode": "free_launch",
            "default_usd": 0,
            "suggested_usd": [0, 5, 15, 40],
            "donate_url": "https://github.com/VKVstudio/.github/blob/main/DONATE.md",
            "links": [
                {"id": "vkvstudio_donate", "lang": "en", "url": "https://github.com/VKVstudio/.github/blob/main/DONATE.md"},
                {"id": "vkvstudio_github", "lang": "en", "url": "https://github.com/VKVstudio"},
                {"id": "vkvstudio_web", "lang": "en", "url": "https://vkvstudio.com"},
            ],
            "crypto_wallets": [
                {"id": "trc20", "network": "USDT · TRX (Tron TRC-20, Recommended)", "address": "TCe57bLA4KBqcPc3ApKauE4VHLd3WqW1WT"},
                {"id": "ton", "network": "USDT · TON (TON network, Recommended)", "address": "UQAEvC5puI21Z5OtPTo6SilVWtElgyZXvH8VIHLLKGxRL4AO"},
                {"id": "evm", "network": "USDT · USDC · ETH (EVM: Ethereum, Arbitrum, Base, Optimism, Polygon, BSC)", "address": "0xdcE037bdF1c580A98D58815C508F7B4d7f7c4603"},
                {"id": "btc", "network": "BTC (Bitcoin Native SegWit)", "address": "bc1q6nvqcw53r36w9gsjw429d6v3reshjr0pn8frrm"},
            ],
            "prompt": {"first_run_card": False, "max_cards_per_version": 1, "dismiss_forever": True},
        },
    }


def _find_monorepo_root(start_dir: Path) -> Path | None:
    cur = start_dir.resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "CLAUDE.md").exists() and (candidate / "models").is_dir():
            return candidate
    return None


def discover_studio_paths(
    repo_root: Path | None = None,
    platform_override: str | None = None,
    cli_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """5-Tier Path Discovery (1. CLI flag -> 2. env -> 3. user config -> 4. monorepo -> 5. wizard)."""
    win = is_windows(platform_override)
    cli = cli_overrides or {}
    cfg_path = get_user_config_path(platform_override)
    user_cfg: dict[str, Any] = {}
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                user_cfg = raw.get("paths", raw)
        except Exception:
            pass

    mono_root = repo_root.resolve() if repo_root else _find_monorepo_root(STUDIO_ROOT)
    root = mono_root or DEFAULT_REPO_ROOT.resolve()

    # Monorepo candidate map
    models_dir = root / "models"
    v2_candidates = sorted(
        (p for p in models_dir.glob("SmartLLM-v2-*.gguf") if "BF16" not in p.name.upper()),
        key=lambda p: p.name,
    ) if models_dir.exists() else []
    mono_model = (models_dir / "SmartLLM-v2-K320-V1.gguf") if (models_dir / "SmartLLM-v2-K320-V1.gguf").exists() else (v2_candidates[0] if v2_candidates else (models_dir / "SmartLLM-205E-IQ3_S.gguf"))

    llama_mono = (
        root / "tools" / "llama.cpp" / "build" / "bin" / "Release" / "llama-server.exe"
        if win
        else root / "tools" / "llama.cpp" / "build_linux" / "bin" / "llama-server"
    )
    sd_mono = (
        root / "tools" / "stable-diffusion.cpp" / "build" / "bin" / "Release" / "sd-cli.exe"
        if win
        else root / "tools" / "stable-diffusion.cpp" / "build_linux" / "bin" / "sd-cli"
    )
    comfy_base = Path("D:/ComfyUI_windows_portable/ComfyUI/models") if win else Path("/mnt/rescue/ComfyUI_windows_portable/ComfyUI/models")
    mono_map = {
        "gguf_model_path": mono_model,
        "mmproj_path": models_dir / "mmproj-SmartLLM-v2-f16.gguf",
        "llama_server_bin": llama_mono,
        "sd_cli_bin": sd_mono,
        "dit_model_path": comfy_base / "diffusion_models" / "beyond_reality_z_image_3.0_fp8.safetensors",
        "te_model_path": comfy_base / "text_encoders" / "qwen_3_4b.safetensors",
        "vae_model_path": comfy_base / "vae" / "ae.safetensors",
    }

    resolved: dict[str, Any] = {}
    sources: dict[str, str] = {}

    for key, env_name in ENV_KEY_MAP.items():
        if cli.get(key):
            resolved[key] = str(cli[key])
            sources[key] = "cli"
        elif os.environ.get(env_name):
            resolved[key] = str(os.environ[env_name])
            sources[key] = "env"
        elif user_cfg.get(key):
            resolved[key] = str(user_cfg[key])
            sources[key] = "user_config"
        elif mono_root is not None and (mono_map[key].exists() or key in ("gguf_model_path", "llama_server_bin", "sd_cli_bin")):
            resolved[key] = str(mono_map[key])
            sources[key] = "monorepo"
        else:
            resolved[key] = str(mono_map[key])
            sources[key] = "wizard"

    lock_path = (mono_root / ".system" / "gpu.lock") if (mono_root and (mono_root / ".system").exists()) else (cfg_path.parent / "gpu.lock")

    return {
        "os": current_platform_tag(platform_override),
        "monorepo_detected": mono_root is not None,
        "repo_root": str(root),
        "studio_root": str(STUDIO_ROOT),
        "projects_root": str(root / "eval" / "studio_projects"),
        "gpu_lock_path": str(lock_path),
        "config_path": str(cfg_path),
        "sources": sources,
        **resolved,
        "llama_server_exists": Path(resolved["llama_server_bin"]).exists(),
        "sd_cli_exists": Path(resolved["sd_cli_bin"]).exists(),
        "gguf_model_exists": Path(resolved["gguf_model_path"]).exists(),
    }


def load_user_settings(
    repo_root: Path | None = None,
    platform_override: str | None = None,
    cli_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    paths = discover_studio_paths(repo_root=repo_root, platform_override=platform_override, cli_overrides=cli_overrides)
    edition = load_edition_config()
    base: dict[str, Any] = {
        "language": "en",
        "host": "127.0.0.1",
        "port": 8090,
        "llm_port": 18080,
        "support_mode": edition.get("support", {}).get("mode", "free_launch"),
        "support_card_dismissed": False,
        "exports_completed": 0,
        "paths": paths,
    }
    cpath = get_user_config_path(platform_override)
    if cpath.exists():
        try:
            saved = json.loads(cpath.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                base.update({k: v for k, v in saved.items() if k != "paths"})
                if isinstance(saved.get("paths"), dict):
                    base["paths"].update(saved["paths"])
        except Exception:
            pass
    return base


def save_user_settings(
    updates: dict[str, Any],
    repo_root: Path | None = None,
    platform_override: str | None = None,
) -> dict[str, Any]:
    current = load_user_settings(repo_root=repo_root, platform_override=platform_override)
    for k, v in updates.items():
        if k == "paths" and isinstance(v, dict):
            current["paths"].update(v)
        elif k != "host":
            current[k] = v
    current["host"] = "127.0.0.1"
    cpath = get_user_config_path(platform_override)
    cpath.parent.mkdir(parents=True, exist_ok=True)
    cpath.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return current
