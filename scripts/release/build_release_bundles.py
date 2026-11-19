#!/usr/bin/env python3
"""SmartLLM v0.0.2-beta Release Bundler & Git Staging Safety Auditor.

Responsibilities:
1. Audits `.gitignore` and `git ls-files` in the monorepo to guarantee ZERO
   secrets (`.env*`, `.secrets/**`, `tokens.env`, `bank_docs/**`), ZERO virtualenvs
   (`.venv*/**`), ZERO model weights (`models/**`), ZERO C++ build trees
   (`tools/*/build*/**`), ZERO `eval/**/lighthouse.json`, and ZERO `research/step1_raw/**`
   are tracked or stageable.
2. Stages the standalone `SmartLLM-Studio` repository directory at
   `dist/SmartLLM-Studio-repo/` with `studio/` contents promoted cleanly to repo root
   (`LICENSE.md` FSL-1.1-ALv2, `TRADEMARKS.md`, `OUTPUTS.md`, `THIRD_PARTY_NOTICES.md`,
   `README.md`, `README.ru.md`, `VERSION`, `pyproject.toml`, `config/edition.json`,
   `assets/`, `bin/`, `smartllm_studio/`, `tests/`, `install.{sh,ps1}`,
   `uninstall.{sh,ps1}`, `smartllm-studio.bat`, `smartllm-studio-silent.vbs`,
   and a strict standalone `.gitignore`), containing 0 weights and 0 compiled binaries.
3. Packages deterministic release archives:
   - `dist/releases/SmartLLM-Studio-v0.0.2-beta-linux.tar.gz`
   - `dist/releases/SmartLLM-Studio-v0.0.2-beta-windows11.zip`
   - `dist/releases/SHA256SUMS.txt`
4. Runs an isolated extraction + standalone import/health smoke in `/tmp/rel_smoke`
   and cleans `/tmp/rel_smoke` immediately afterward.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
STUDIO_SRC = ROOT / "studio"
DIST_DIR = ROOT / "dist"
STAGE_REPO_DIR = DIST_DIR / "SmartLLM-Studio-repo"
RELEASES_DIR = DIST_DIR / "releases"

FORBIDDEN_GIT_PATTERNS = (
    ".env",
    ".env.*",
    "*/.env*",
    ".secrets/*",
    "tokens.env",
    "*/tokens.env",
    "bank_docs/*",
    ".venv/*",
    ".venv_linux/*",
    ".venv*/*",
    "models/*",
    "tools/*/build/*",
    "tools/*/build_*/*",
    "eval/**/lighthouse.json",
    "eval/*/lighthouse.json",
    "eval/*/*/lighthouse.json",
    "research/step1_raw/*",
    "research/recon*.json",
    ".system/history_v1_205e.md",
)

FORBIDDEN_STUDIO_EXTENSIONS = (
    ".gguf",
    ".safetensors",
    ".pt",
    ".pth",
    ".bin",
    ".onnx",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".o",
    ".a",
)

REQUIRED_STUDIO_ROOT_ITEMS = (
    ".github/FUNDING.yml",
    "DONATE.md",
    "LICENSE.md",
    "TRADEMARKS.md",
    "OUTPUTS.md",
    "THIRD_PARTY_NOTICES.md",
    "README.md",
    "README.ru.md",
    "VERSION",
    "pyproject.toml",
    "config/edition.json",
    "assets",
    "assets/badges/support-button.svg",
    "bin",
    "smartllm_studio",
    "tests",
    "install.sh",
    "install.ps1",
    "uninstall.sh",
    "uninstall.ps1",
    "smartllm-studio.bat",
    "smartllm-studio-silent.vbs",
)

STANDALONE_GITIGNORE = """# SmartLLM Studio standalone repository .gitignore
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/
build/
dist/
.venv/
.venv_*/
venv/
ENV/

# Never commit model weights, compiled engine binaries, or runtime caches
*.gguf
*.safetensors
*.pt
*.pth
*.bin
*.onnx
*.so
*.dll
*.exe
models/
engines_bin/
slot_cache/
sd_outputs/

# User project drafts, exports & local logs
projects/
exports/
*.log
.DS_Store
Thumbs.db

# Secrets & local environment overrides
.env
.env.*
.secrets/
tokens.env
"""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def audit_monorepo_git_safety(repo_root: Path = ROOT) -> dict:
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        raise RuntimeError(f"Missing .gitignore at {gitignore_path}")
    gitignore_text = gitignore_path.read_text(encoding="utf-8")

    required_ignore_tokens = (
        ".env*",
        ".secrets/",
        "tokens.env",
        "bank_docs/",
        ".venv",
        "models/",
        "eval/**/lighthouse.json",
        "research/step*_raw/",
    )
    missing_tokens = [tok for tok in required_ignore_tokens if tok not in gitignore_text]
    if missing_tokens:
        raise RuntimeError(f".gitignore is missing required ignore rules: {missing_tokens}")

    proc = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    violations: list[str] = []
    for rel_path in tracked_files:
        for pat in FORBIDDEN_GIT_PATTERNS:
            if fnmatch.fnmatch(rel_path, pat):
                violations.append(f"{rel_path} (matched {pat})")
                break
        if rel_path.endswith((".gguf", ".safetensors", ".pt", ".pth")):
            violations.append(f"{rel_path} (forbidden weight binary extension)")

    if violations:
        raise RuntimeError(f"Forbidden tracked files detected in git ls-files: {violations}")

    # Also verify git check-ignore on sensitive probe paths
    probe_paths = [
        ".env",
        ".secrets/key.txt",
        "tokens.env",
        "bank_docs/doc.pdf",
        "models/SmartLLM-v2-K320-V1.gguf",
        "tools/llama.cpp",
        "tools/stable-diffusion.cpp",
        "eval/suite/runs/test/lighthouse.json",
        "research/step1_raw/dump.json",
    ]
    proc_ign = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "--", *probe_paths],
        capture_output=True,
        text=True,
        check=False,
    )
    ignored_set = {line.strip() for line in proc_ign.stdout.splitlines() if line.strip()}
    unignored = [p for p in probe_paths if p not in ignored_set]
    if unignored:
        raise RuntimeError(f"Sensitive paths not ignored by .gitignore: {unignored}")

    return {
        "gitignore_audit": "PASS",
        "tracked_files_checked": len(tracked_files),
        "violations": 0,
        "sensitive_probes_ignored": len(probe_paths),
    }


def _should_skip_copy(path: Path) -> bool:
    name = path.name
    if name in ("__pycache__", ".pytest_cache", ".mypy_cache", ".DS_Store"):
        return True
    if name.lower().endswith((".pyc", ".pyo", ".pyd", ".egg-info", ".mp4", ".mov", ".mkv", ".avi", ".webm")):
        return True
    return False


def _copy_tree_clean(src: Path, dst: Path) -> None:
    if _should_skip_copy(src):
        return
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for child in sorted(src.iterdir()):
            _copy_tree_clean(child, dst / child.name)
    elif src.is_file():
        if src.suffix.lower() in FORBIDDEN_STUDIO_EXTENSIONS:
            raise RuntimeError(f"Forbidden binary/weight file in studio source: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def stage_standalone_studio_repo(
    studio_src: Path = STUDIO_SRC,
    stage_dir: Path = STAGE_REPO_DIR,
) -> dict:
    if not studio_src.is_dir():
        raise RuntimeError(f"Studio source directory not found: {studio_src}")

    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)

    for child in sorted(studio_src.iterdir()):
        if _should_skip_copy(child):
            continue
        _copy_tree_clean(child, stage_dir / child.name)

    # Also copy root brand SVG logo into assets/brand/ if not already inside studio/assets/brand/
    root_brand_dir = ROOT / "assets" / "brand"
    if root_brand_dir.is_dir():
        _copy_tree_clean(root_brand_dir, stage_dir / "assets" / "brand")

    (stage_dir / ".gitignore").write_text(STANDALONE_GITIGNORE, encoding="utf-8")

    # Verify all required items exist at root of staged repo
    missing = [item for item in REQUIRED_STUDIO_ROOT_ITEMS if not (stage_dir / item).exists()]
    if missing:
        raise RuntimeError(f"Staged SmartLLM-Studio-repo is missing required items: {missing}")

    # Verify license & version metadata
    lic_text = (stage_dir / "LICENSE.md").read_text(encoding="utf-8")
    if "FSL-1.1-ALv2" not in lic_text or "2028-11-16" not in lic_text:
        raise RuntimeError("Staged LICENSE.md failed FSL-1.1-ALv2 / 2028-11-16 check")

    version_str = (stage_dir / "VERSION").read_text(encoding="utf-8").strip()
    if version_str != "0.0.2-beta":
        raise RuntimeError(f"Expected VERSION '0.0.2-beta', got '{version_str}'")

    edition = json.loads((stage_dir / "config" / "edition.json").read_text(encoding="utf-8"))
    if edition.get("telemetry") is not False or edition.get("update_check") is not False:
        raise RuntimeError(f"Invalid edition.json privacy flags: {edition}")

    # Count staged files and total bytes, asserting 0 forbidden extensions
    file_count = 0
    total_bytes = 0
    for fpath in sorted(stage_dir.rglob("*")):
        if fpath.is_file():
            if fpath.suffix.lower() in FORBIDDEN_STUDIO_EXTENSIONS:
                raise RuntimeError(f"Forbidden binary/weight file staged: {fpath}")
            file_count += 1
            total_bytes += fpath.stat().st_size

    return {
        "stage_dir": str(stage_dir),
        "version": version_str,
        "license": "FSL-1.1-ALv2",
        "staged_file_count": file_count,
        "staged_total_bytes": total_bytes,
        "staged_total_kb": round(total_bytes / 1024.0, 2),
    }


def build_release_archives(
    stage_dir: Path = STAGE_REPO_DIR,
    releases_dir: Path = RELEASES_DIR,
    version: str = "0.0.2-beta",
) -> dict:
    releases_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"SmartLLM-Studio-v{version}"
    linux_tar_path = releases_dir / f"{prefix}-linux.tar.gz"
    win_zip_path = releases_dir / f"{prefix}-windows11.zip"
    sums_path = releases_dir / "SHA256SUMS.txt"

    all_files = sorted(p for p in stage_dir.rglob("*") if p.is_file())

    # 1. Deterministic Linux .tar.gz
    with tarfile.open(linux_tar_path, "w:gz", format=tarfile.PAX_FORMAT) as tf:
        for fpath in all_files:
            rel = fpath.relative_to(stage_dir).as_posix()
            arcname = f"{prefix}/{rel}"
            ti = tf.gettarinfo(str(fpath), arcname=arcname)
            ti.uid = 0
            ti.gid = 0
            ti.uname = "root"
            ti.gname = "root"
            ti.mtime = 1794830400  # Fixed deterministic timestamp (2026-11-16T12:00:00Z)
            if fpath.name.endswith(".sh") or fpath.parent.name == "bin":
                ti.mode = 0o755
            else:
                ti.mode = 0o644
            with fpath.open("rb") as rf:
                tf.addfile(ti, rf)

    # 2. Deterministic Windows 11 .zip
    with zipfile.ZipFile(win_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for fpath in all_files:
            rel = fpath.relative_to(stage_dir).as_posix()
            arcname = f"{prefix}/{rel}"
            zi = zipfile.ZipInfo(arcname, date_time=(2026, 11, 16, 12, 0, 0))
            if fpath.name.endswith(".sh") or fpath.parent.name == "bin":
                zi.external_attr = 0o755 << 16
            else:
                zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, fpath.read_bytes())

    linux_sha = sha256_file(linux_tar_path)
    win_sha = sha256_file(win_zip_path)
    sums_content = (
        f"{linux_sha}  {linux_tar_path.name}\n"
        f"{win_sha}  {win_zip_path.name}\n"
    )
    sums_path.write_text(sums_content, encoding="utf-8")

    return {
        "linux_tar_gz": {
            "path": str(linux_tar_path),
            "bytes": linux_tar_path.stat().st_size,
            "sha256": linux_sha,
        },
        "windows11_zip": {
            "path": str(win_zip_path),
            "bytes": win_zip_path.stat().st_size,
            "sha256": win_sha,
        },
        "sha256sums_path": str(sums_path),
    }


def verify_extracted_archive_in_tmp(linux_tar_path: Path, version: str = "0.0.2-beta") -> dict:
    smoke_root = Path("/tmp/rel_smoke")
    if smoke_root.exists():
        shutil.rmtree(smoke_root)
    smoke_root.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(linux_tar_path, "r:gz") as tf:
            tf.extractall(smoke_root, filter="data")

        extracted_dir = smoke_root / f"SmartLLM-Studio-v{version}"
        if not extracted_dir.is_dir():
            raise RuntimeError(f"Expected extracted directory {extracted_dir} missing")

        # Run standalone import & RAG/blueprint check completely outside monorepo
        check_code = (
            "import json, sys\n"
            f"sys.path.insert(0, {repr(str(extracted_dir))})\n"
            "from smartllm_studio.config import discover_studio_paths\n"
            "from smartllm_studio.rag import StudioRAGSelector\n"
            "from smartllm_studio.blueprint import compile_project_blueprint, default_project_draft\n"
            "paths = discover_studio_paths()\n"
            "assert paths['monorepo_detected'] is False, f'Expected standalone mode: {paths}'\n"
            "rag = StudioRAGSelector()\n"
            f"draft = default_project_draft('smoke_rel', repo_root=__import__('pathlib').Path({repr(str(smoke_root))}))\n"
            f"bp = compile_project_blueprint(draft, repo_root=__import__('pathlib').Path({repr(str(smoke_root))}))\n"
            "assert 'index.html' in bp['files'] and '_headers' in bp['files']\n"
            "print(json.dumps({'standalone_import_ok': True, 'monorepo_detected': paths['monorepo_detected'], 'canons': len(rag.canon_cards), 'copy_pairs': len(rag.copy_pairs), 'files_generated': len(bp['files'])}))\n"
        )
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = ""
        proc = subprocess.run(
            [sys.executable, "-c", check_code],
            cwd="/tmp",
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        smoke_res = json.loads(proc.stdout.strip().splitlines()[-1])
    finally:
        if smoke_root.exists():
            shutil.rmtree(smoke_root)

    assert not smoke_root.exists(), "/tmp/rel_smoke was not cleaned up!"
    return {
        "tmp_rel_smoke": "PASS",
        "tmp_rel_smoke_cleaned": not smoke_root.exists(),
        "details": smoke_res,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build & verify SmartLLM Studio v0.0.2-beta release bundles.")
    parser.add_argument("--verify", action="store_true", help="Run full git audit, staging, packaging & /tmp/rel_smoke verification")
    args = parser.parse_args(argv)

    git_audit = audit_monorepo_git_safety(ROOT)
    staged = stage_standalone_studio_repo(STUDIO_SRC, STAGE_REPO_DIR)
    archives = build_release_archives(STAGE_REPO_DIR, RELEASES_DIR, version=staged["version"])
    smoke = verify_extracted_archive_in_tmp(Path(archives["linux_tar_gz"]["path"]), version=staged["version"])

    out = {
        "status": "PASS",
        "git_safety": git_audit,
        "staged_repo": staged,
        "archives": archives,
        "extraction_smoke": smoke,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
