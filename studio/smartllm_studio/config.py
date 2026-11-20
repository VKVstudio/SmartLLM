"""5-Tier Path Discovery, Edition Schema v2, and Config Management for SmartLLM Studio (Opus Spec Q2, Q3)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
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
        "version": "0.0.2-beta",
        "license_spdx": "FSL-1.1-ALv2",
        "license_change_date": "2028-11-19",
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
    """Walk up from start_dir; accept monorepo markers or a release layout with models/SmartLLM*.gguf."""
    cur = start_dir.resolve()
    for candidate in (cur, *cur.parents):
        models_dir = candidate / "models"
        if not models_dir.is_dir():
            continue
        if (candidate / "CLAUDE.md").exists() or (candidate / "AGENTS.md").exists():
            return candidate
        if any(models_dir.glob("SmartLLM*.gguf")):
            return candidate
    return None


def _resolve_repo_root(explicit: Path | None) -> tuple[Path, bool]:
    """Portable root resolution: explicit flag -> SMARTLLM_REPO_ROOT env -> walk up from package dir."""
    starts: list[Path] = []
    if explicit is not None:
        starts.append(explicit)
    env_root = os.environ.get("SMARTLLM_REPO_ROOT")
    if env_root:
        starts.append(Path(env_root))
    starts.append(STUDIO_ROOT)
    for start in starts:
        found = _find_monorepo_root(start)
        if found is not None:
            return found, True
    return (explicit.resolve() if explicit is not None else DEFAULT_REPO_ROOT.resolve()), False


def _newest_existing(candidates: list[Path]) -> Path | None:
    """Pick the most recently built existing binary: stale stubs in older build dirs
    (e.g. an outdated build/bin/llama-server.exe) must not shadow fresh builds."""
    best: Path | None = None
    best_mtime = -1.0
    for cand in candidates:
        try:
            if cand.is_file():
                mt = cand.stat().st_mtime
                if mt > best_mtime:
                    best, best_mtime = cand, mt
        except OSError:
            continue
    return best


def _binary_candidates(root: Path, win: bool, tool_dir_name: str, exe_name: str) -> list[Path]:
    """All common build layouts (Ninja/MSBuild/Release), any drive or folder, plus PATH lookup."""
    names = [f"{exe_name}.exe"] if win else [exe_name]
    build_dirs = ["build", "build_win", "build_linux"] if win else ["build_linux", "build", "build_win"]
    sub_dirs = ["bin", "bin/Release", "bin/Debug", "bin/RelWithDebInfo"]
    tool_dir = root / "tools" / tool_dir_name
    bundle_sub = "llama" if tool_dir_name == "llama.cpp" else "sd"
    cands: list[Path] = []
    for bd in build_dirs:
        for sub in sub_dirs:
            for n in names:
                cands.append(tool_dir / bd / sub / n)
    for n in names:
        cands.append(root / "bin" / n)
        cands.append(root / "bin" / bundle_sub / n)
        cands.append(tool_dir / n)
    for n in names:
        cands.extend(sorted(tool_dir.glob(f"build*/bin/**/{n}")))
    which = shutil.which(exe_name)
    if which:
        cands.append(Path(which))
    return cands


def _discover_model(models_dir: Path, fallback_dirs: list[Path] | None = None) -> Path:
    preferred = models_dir / "SmartLLM-v2-K320-V1.gguf"
    if preferred.exists():
        return preferred
    v2 = sorted(p for p in models_dir.glob("SmartLLM-v2-*.gguf") if "BF16" not in p.name.upper())
    if v2:
        return v2[0]
    any_smart = sorted(models_dir.glob("SmartLLM*.gguf"))
    if any_smart:
        return any_smart[0]
    for fb in fallback_dirs or []:
        try:
            hits = sorted(p for p in fb.glob("SmartLLM*.gguf") if p.is_file() and "BF16" not in p.name.upper())
            if hits:
                return hits[0]
        except OSError:
            continue
    return preferred


def _discover_mmproj(models_dir: Path, hint_dir: Path | None = None, fallback_dirs: list[Path] | None = None) -> Path:
    search = ([hint_dir] if hint_dir and hint_dir != models_dir else []) + [models_dir] + list(fallback_dirs or [])
    for d in search:
        try:
            cands = sorted(d.glob("mmproj*.gguf"))
        except OSError:
            continue
        for cand in cands:
            if "BF16" in cand.name.upper() or "F16" in cand.name.upper():
                return cand
        if cands:
            return cands[0]
    return models_dir / "mmproj-Qwen3.8-Flash-Next-BF16.gguf"


def _drive_roots() -> list[Path]:
    """Existing drive roots (Windows letters) or common mount points (Linux/macOS)."""
    roots: list[Path] = []
    if is_windows():
        import string
        for letter in string.ascii_uppercase:
            dr = Path(f"{letter}:\\")
            try:
                if dr.exists():
                    roots.append(dr)
            except OSError:
                continue
    else:
        for mount in ("/mnt", "/media", "/Volumes"):
            mp = Path(mount)
            try:
                if mp.is_dir():
                    roots.extend(sorted(p for p in mp.iterdir() if p.is_dir())[:16])
            except OSError:
                continue
        roots.append(Path.home())
    return roots


def _extra_weight_bases(root: Path) -> list[Path]:
    """Bounded cross-drive candidate folders for weights (no deep recursion)."""
    bases: list[Path] = []
    seen: set[Path] = set()
    home = Path.home()
    for dr in _drive_roots():
        for cand in (
            dr / "models",
            dr / "ComfyUI_windows_portable" / "ComfyUI" / "models",
            dr / "ComfyUI" / "models",
            dr / "SmartLLM" / "models",
            home / "models",
            home / "ComfyUI" / "models",
            home / "Documents" / "ComfyUI" / "models",
        ):
            if cand not in seen:
                seen.add(cand)
                bases.append(cand)
        try:
            for pat in ("ComfyUI*", "SmartLLM*"):
                for hit in sorted(dr.glob(pat))[:8]:
                    if hit.is_dir():
                        for sub in (hit / "models", hit / "ComfyUI" / "models"):
                            if sub not in seen:
                                seen.add(sub)
                                bases.append(sub)
            for hit in sorted(dr.glob("projects/*"))[:16]:
                if hit.is_dir():
                    sub = hit / "models"
                    if sub not in seen:
                        seen.add(sub)
                        bases.append(sub)
        except OSError:
            continue
    return bases


def _find_zimage_models_dir(root: Path, extra: list[Path] | None = None) -> Path | None:
    """Search ComfyUI-style weight folders relative to the repo, then across all drives."""
    bases: list[Path] = []
    ancestors = [root, *list(root.parents)[:3]]
    for anc in ancestors:
        bases.append(anc / "ComfyUI_windows_portable" / "ComfyUI" / "models")
        bases.append(anc / "ComfyUI" / "models")
        try:
            for cand in sorted(anc.glob("ComfyUI*")):
                if cand.is_dir():
                    bases.append(cand / "ComfyUI" / "models")
                    bases.append(cand / "models")
        except OSError:
            pass
        bases.append(anc / "models" / "z-image")
        bases.append(anc / "models")
    bases.extend(extra if extra is not None else _extra_weight_bases(root))
    for base in bases:
        try:
            if (base / "diffusion_models").is_dir() or (base / "text_encoders").is_dir():
                return base
        except OSError:
            continue
    return None


def _pick_weight(models_base: Path, sub_dir: str, preferred: str, patterns: list[str]) -> Path:
    d = models_base / sub_dir
    pref = d / preferred
    if pref.exists():
        return pref
    for pat in patterns:
        hits = sorted(p for p in d.glob(pat) if p.is_file())
        if hits:
            return hits[0]
    return pref


def refresh_path_flags(paths: dict[str, Any]) -> dict[str, Any]:
    """Recompute *_exists and missing_* diagnostics after any path merge/update."""
    for key, flag in (
        ("gguf_model_path", "gguf_model_exists"),
        ("mmproj_path", "mmproj_exists"),
        ("llama_server_bin", "llama_server_exists"),
        ("sd_cli_bin", "sd_cli_exists"),
        ("dit_model_path", "dit_model_exists"),
        ("te_model_path", "te_model_exists"),
        ("vae_model_path", "vae_model_exists"),
    ):
        paths[flag] = Path(str(paths.get(key) or "")).exists()
    paths["missing_required"] = [
        k for k, flag in (
            ("gguf_model_path", "gguf_model_exists"),
            ("llama_server_bin", "llama_server_exists"),
        ) if not paths.get(flag)
    ]
    paths["missing_visuals"] = [
        k for k, flag in (
            ("sd_cli_bin", "sd_cli_exists"),
            ("dit_model_path", "dit_model_exists"),
            ("te_model_path", "te_model_exists"),
            ("vae_model_path", "vae_model_exists"),
        ) if not paths.get(flag)
    ]
    return paths


def discover_studio_paths(
    repo_root: Path | None = None,
    platform_override: str | None = None,
    cli_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """5-Tier Path Discovery (1. CLI flag -> 2. env -> 3. user config -> 4. monorepo/release auto -> 5. wizard).

    Fully portable: every candidate is derived from the package location, an explicit
    root, or the user config/env — never from a hardcoded drive letter or mount point.
    """
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

    root, mono_detected = _resolve_repo_root(repo_root)

    models_dir = root / "models"
    llama_cands = _binary_candidates(root, win, "llama.cpp", "llama-server")
    sd_cands = _binary_candidates(root, win, "stable-diffusion.cpp", "sd-cli")
    llama_mono = _newest_existing(llama_cands) or llama_cands[0]
    sd_mono = _newest_existing(sd_cands) or sd_cands[0]

    extra_bases = _extra_weight_bases(root)
    zimage_base = _find_zimage_models_dir(root, extra_bases)
    if zimage_base is None:
        zimage_base = models_dir / "z-image"
    model_found = _discover_model(models_dir, extra_bases)
    mono_map = {
        "gguf_model_path": model_found,
        "mmproj_path": _discover_mmproj(models_dir, model_found.parent, extra_bases),
        "llama_server_bin": llama_mono,
        "sd_cli_bin": sd_mono,
        "dit_model_path": _pick_weight(zimage_base, "diffusion_models", "beyond_reality_z_image_3.0_fp8.safetensors", ["*z_image*.safetensors", "*z-image*.safetensors", "*.safetensors"]),
        "te_model_path": _pick_weight(zimage_base, "text_encoders", "qwen_3_4b.safetensors", ["qwen*.safetensors", "*.safetensors"]),
        "vae_model_path": _pick_weight(zimage_base, "vae", "ae.safetensors", ["ae*.safetensors", "*.safetensors"]),
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
        elif mono_detected and (mono_map[key].exists() or key in ("gguf_model_path", "llama_server_bin", "sd_cli_bin")):
            resolved[key] = str(mono_map[key])
            sources[key] = "monorepo"
        else:
            resolved[key] = str(mono_map[key])
            sources[key] = "wizard"

    lock_path = (root / ".system" / "gpu.lock") if (mono_detected and (root / ".system").exists()) else (cfg_path.parent / "gpu.lock")
    projects_root = (root / "eval" / "studio_projects") if mono_detected else (root / "studio_projects")

    paths = {
        "os": current_platform_tag(platform_override),
        "monorepo_detected": mono_detected,
        "repo_root": str(root),
        "studio_root": str(STUDIO_ROOT),
        "projects_root": str(projects_root),
        "gpu_lock_path": str(lock_path),
        "config_path": str(cfg_path),
        "sources": sources,
        **resolved,
    }
    return refresh_path_flags(paths)


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
                    for key in ENV_KEY_MAP:
                        val = saved["paths"].get(key)
                        if val:
                            base["paths"][key] = str(val)
                            base["paths"]["sources"][key] = "user_config"
                    refresh_path_flags(base["paths"])
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
            for key in ENV_KEY_MAP:
                if v.get(key):
                    current["paths"][key] = str(v[key])
                    current["paths"]["sources"][key] = "user_config"
        elif k != "host":
            current[k] = v
    current["host"] = "127.0.0.1"
    refresh_path_flags(current["paths"])
    persisted = {k: v for k, v in current.items() if k != "paths"}
    persisted["paths"] = {key: current["paths"][key] for key in ENV_KEY_MAP}
    cpath = get_user_config_path(platform_override)
    cpath.parent.mkdir(parents=True, exist_ok=True)
    cpath.write_text(json.dumps(persisted, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return current
