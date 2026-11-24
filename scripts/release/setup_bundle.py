#!/usr/bin/env python3
"""SmartLLM single-folder bundle setup (Linux + Windows 11, Python 3.11+, pure stdlib).

Downloads everything a new user needs into ONE portable folder on ANY drive:

    <dest>/studio/   SmartLLM Studio app (GitHub Release archive, or the tagged source archive)
    <dest>/models/   SmartLLM-v2-K320-V1.gguf (30 parts -> SHA-256 verified reassembly),
                     mmproj-Qwen3.8-Flash-Next-BF16.gguf,
                     z-image/{diffusion_models,text_encoders,vae}/*.safetensors
    <dest>/bin/      llama-server & sd-cli engine binaries (when published in the Release)

This script is the ONLY online step; the Studio runtime stays fully offline (127.0.0.1).
Downloads are resumable and SHA-256 verified. By default EVERYTHING comes from our GitHub
Releases (model parts from --model-tag, Studio/engines/Z-Image from --tag) — no HuggingFace
access required.

Z-Image sources (--zimage-source):
  release   Official Tongyi-MAI Z-Image-Turbo bf16 (Apache-2.0), re-hosted in our Release [default]
  hf        Same official weights directly from Comfy-Org/Z-Image-Turbo on Hugging Face

Text encoder (qwen_3_4b.safetensors) and VAE (ae.safetensors, Flux.1 AE, Apache-2.0)
are byte-identical to Comfy-Org/Z-Image-Turbo on Hugging Face in all modes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

DEFAULT_REPO = "VKVstudio/SmartLLM"
DEFAULT_TAG = "v0.0.7-beta"  # Studio version installed by default (Release asset, else the tagged source archive)
DEFAULT_MODEL_TAG = "v0.0.1-beta"  # 55 GiB GGUF parts + mmproj live in the first release (reused)
DEFAULT_ZIMAGE_TAG = "v0.0.3-beta"
DEFAULT_ENGINES_TAG = "v0.0.3-beta"
HF_BASE = "https://huggingface.co/Comfy-Org/Z-Image-Turbo/resolve/main/split_files"
HF_API_TREE = "https://huggingface.co/api/models/Comfy-Org/Z-Image-Turbo/tree/main/split_files"
USER_AGENT = "SmartLLM-Setup/0.0.4 (local bundle installer)"
CHUNK = 4 * 1024 * 1024
GB = 1000**3
_LINE_PROGRESS = False


def _space_plan(skip_model: bool, skip_zimage: bool, skip_binaries: bool, cleanup: bool) -> tuple[float, float, float]:
    """(download_gb, peak_disk_gb, final_disk_gb) from real release asset sizes.
    Peak accounts for parts + reassembled file coexisting during assembly."""
    steps = [(0.02, 0.0, 0.02)]  # studio: download, assemble-extra, keep-after
    if not skip_model:
        parts, final = 59.07 + 0.91, 59.07  # 30 GGUF parts + mmproj, reassembled GGUF
        steps.append((parts, final, final if cleanup else parts + final))
    if not skip_zimage:
        parts, final = 12.31 + 8.05 + 0.34, 12.31 + 8.05 + 0.34  # DiT + TE + VAE
        steps.append((parts, final, final if cleanup else parts + final))
    if not skip_binaries:
        steps.append((3.75, 0.0, 3.75))  # engine archive + extracted binaries
    download = kept = peak = 0.0
    for dl, extra, keep in steps:
        download += dl
        peak = max(peak, kept + dl + extra)
        kept += keep
    return download, peak, kept


def _check_free_space(dest: Path, skip_model: bool, skip_zimage: bool, skip_binaries: bool, cleanup: bool) -> bool:
    download, peak, final = _space_plan(skip_model, skip_zimage, skip_binaries, cleanup)
    free = shutil.disk_usage(dest).free
    need = peak * GB * 1.05  # 5% safety margin
    _log(f"Disk plan: download ~{download:.0f} GB, peak usage ~{peak:.0f} GB, after install ~{final:.0f} GB" + (" (--cleanup-parts)" if cleanup else " (parts kept)"))
    _log(f"Free space at {dest}: {free / GB:.1f} GB")
    if free < need:
        _log(f"ERROR: not enough free space (need ~{need / GB:.0f} GB with margin). Free up disk, pick another --dest, or use --cleanup-parts / --skip-model / --skip-zimage / --skip-binaries.")
        return False
    return True


def _log(msg: str) -> None:
    print(msg, flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _open(url: str, extra_headers: dict[str, str] | None = None):
    headers = {"User-Agent": USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)
    last_exc: Exception | None = None
    for attempt in range(5):
        req = urllib.request.Request(url, headers=headers)
        try:
            return urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (404, 429, 500, 502, 503, 504) and attempt < 4:
                import time

                time.sleep(3 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            last_exc = exc
            if attempt < 4:
                import time

                time.sleep(3 * (attempt + 1))
                continue
            raise
    raise last_exc  # type: ignore[misc]


def download(
    url: str,
    dest: Path,
    expected_sha256: str | None = None,
    expected_size: int | None = None,
    line_progress: bool | None = None,
) -> Path:
    """Resumable streaming download with SHA-256 / size verification and atomic promotion."""
    use_lines = _LINE_PROGRESS if line_progress is None else bool(line_progress)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if expected_sha256:
            if sha256_file(dest) == expected_sha256:
                _log(f"  OK (cached, sha256) {dest.name}")
                return dest
        elif expected_size and dest.stat().st_size == expected_size:
            _log(f"  OK (cached, size) {dest.name}")
            return dest
        else:
            _log(f"  re-download (verification mismatch): {dest.name}")
            dest.unlink()

    part = dest.with_suffix(dest.suffix + ".part")
    resume_from = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={resume_from}-"} if resume_from else {}
    try:
        resp = _open(url, headers)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and resume_from:
            part.unlink()
            resume_from = 0
            resp = _open(url)
        else:
            raise
    with resp:
        total = None
        cr = resp.headers.get("Content-Range")
        if cr and "/" in cr:
            total = int(cr.rsplit("/", 1)[1])
        elif resp.headers.get("Content-Length"):
            total = resume_from + int(resp.headers["Content-Length"])
        mode = "ab" if resume_from and resp.status == 206 else "wb"
        if mode == "wb":
            resume_from = 0
        done = resume_from
        last_step = int((100.0 * done / total) // 5) if (total and done) else -1
        with part.open(mode) as out:
            while True:
                block = resp.read(CHUNK)
                if not block:
                    break
                out.write(block)
                done += len(block)
                if total:
                    pct = 100.0 * done / total
                    if use_lines:
                        step = int(pct // 5)
                        if step > last_step or done >= total:
                            last_step = step
                            _log(f"  {dest.name}: {done / 1e6:.0f}/{total / 1e6:.0f} MB ({pct:.1f}%)")
                    else:
                        print(f"\r  {dest.name}: {done / 1e6:.0f}/{total / 1e6:.0f} MB ({pct:.1f}%)", end="", flush=True)
        if total and not use_lines:
            print()
    if expected_size and part.stat().st_size != expected_size:
        raise RuntimeError(f"{dest.name}: size mismatch ({part.stat().st_size} != {expected_size})")
    if expected_sha256:
        actual = sha256_file(part)
        if actual != expected_sha256:
            part.unlink()
            raise RuntimeError(f"{dest.name}: SHA-256 mismatch ({actual})")
    part.replace(dest)
    _log(f"  OK {dest.name}")
    return dest


def hf_file_meta() -> dict[str, dict]:
    """Fetch sizes + SHA-256 (LFS oid) for the official Comfy-Org split files."""
    meta: dict[str, dict] = {}
    for sub in ("diffusion_models", "text_encoders", "vae"):
        with _open(f"{HF_API_TREE}/{sub}") as resp:
            for entry in json.load(resp):
                lfs = entry.get("lfs") or {}
                meta[entry["path"]] = {"size": entry.get("size"), "sha256": lfs.get("oid") or lfs.get("sha256")}
    return meta


def _url_exists(url: str) -> bool:
    """Single quick probe (no retries) so a missing Release asset falls back fast."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def step_studio(dest: Path, repo: str, tag: str, cleanup_parts: bool = False, ref: str = "") -> None:
    """Install Studio into <dest>/studio.

    Order: the prebuilt Release asset for ``tag`` if it is published; otherwise the GitHub
    source archive of the same tag (or of ``ref``, e.g. ``main``), whose ``studio/`` folder is
    exactly what the Release archive contains. Either way the installed VERSION is logged.
    """
    studio_dir = dest / "studio"
    if (studio_dir / "smartllm_studio" / "cli.py").exists():
        ver = (studio_dir / "VERSION").read_text(encoding="utf-8").strip() if (studio_dir / "VERSION").exists() else "?"
        _log(f"[1/4] studio: already present (version {ver}), skip. Delete {studio_dir} to reinstall.")
        return
    win = os.name == "nt"
    downloads_dir = dest / "_downloads"
    name = f"SmartLLM-Studio-{tag}-windows11.zip" if win else f"SmartLLM-Studio-{tag}-linux.tar.gz"
    url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
    source_mode = bool(ref) or not _url_exists(url)
    if source_mode:
        kind, val = ("heads", ref) if ref else ("tags", tag)
        ext = "zip" if win else "tar.gz"
        name = f"SmartLLM-source-{val.replace('/', '_')}.{ext}"
        url = f"https://github.com/{repo}/archive/refs/{kind}/{val}.{ext}"
        _log(f"[1/4] studio: downloading source archive {kind[:-1]} '{val}'")
    else:
        _log(f"[1/4] studio: downloading app archive {name}")
    archive = download(url, downloads_dir / name)
    tmp_extract = downloads_dir / "studio_extract"
    if tmp_extract.exists():
        shutil.rmtree(tmp_extract)
    tmp_extract.mkdir(parents=True)
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(tmp_extract)
    else:
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(tmp_extract, filter="data")
    roots = [p for p in tmp_extract.iterdir() if p.is_dir()]
    if len(roots) != 1:
        raise RuntimeError(f"Unexpected archive layout: {roots}")
    src = roots[0] / "studio" if source_mode else roots[0]
    if not (src / "smartllm_studio" / "cli.py").exists():
        raise RuntimeError(f"Archive does not contain SmartLLM Studio: {src}")
    src.replace(studio_dir)
    shutil.rmtree(tmp_extract, ignore_errors=True)
    if cleanup_parts:
        archive.unlink(missing_ok=True)
        if downloads_dir.exists() and not any(downloads_dir.iterdir()):
            downloads_dir.rmdir()
    ver = (studio_dir / "VERSION").read_text(encoding="utf-8").strip() if (studio_dir / "VERSION").exists() else "?"
    _log(f"  OK studio {ver} -> {studio_dir}")


def step_model(dest: Path, repo: str, tag: str, cleanup_parts: bool) -> None:
    models_dir = dest / "models"
    final_gguf = models_dir / "SmartLLM-v2-K320-V1.gguf"
    mmproj = models_dir / "mmproj-Qwen3.8-Flash-Next-BF16.gguf"
    if final_gguf.exists() and mmproj.exists():
        _log("[2/4] model: already present, skip")
        return
    _log(f"[2/4] model: downloading manifest, mmproj and 30 GGUF parts (~55 GiB) from release {tag}")
    base = f"https://github.com/{repo}/releases/download/{tag}"
    download(f"{base}/MODEL_SHA256SUMS.txt", models_dir / "MODEL_SHA256SUMS.txt")
    download(f"{base}/reassemble_model.py", models_dir / "reassemble_model.py")
    sums: dict[str, str] = {}
    for line in (models_dir / "MODEL_SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and not line.startswith("#"):
            sums[parts[1]] = parts[0]
    download(f"{base}/mmproj-Qwen3.8-Flash-Next-BF16.gguf", mmproj, expected_sha256=sums.get(mmproj.name))
    part_names = sorted(n for n in sums if ".gguf.part" in n)
    if not part_names:
        raise RuntimeError("No partNN entries found in MODEL_SHA256SUMS.txt")
    for pname in part_names:
        download(f"{base}/{pname}", models_dir / pname, expected_sha256=sums[pname])
    _log("  reassembling + verifying final SHA-256 (streaming, bounded RAM)...")
    cmd = [sys.executable, str(models_dir / "reassemble_model.py"), "--dir", str(models_dir)]
    if cleanup_parts:
        cmd.append("--cleanup")
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0 or not final_gguf.exists():
        raise RuntimeError("Model reassembly failed; re-run setup to resume")
    _log(f"  OK model -> {final_gguf}")


def _parse_sums(path: Path) -> dict[str, str]:
    sums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and not line.startswith("#"):
            sums[parts[1]] = parts[0]
    return sums


def _reassemble(parts_dir: Path, final_name: str, sums: dict[str, str], target: Path, cleanup: bool) -> Path:
    """Streaming SHA-256-verified concatenation of <file>.partNN into target (bounded RAM)."""
    if target.exists() and sums.get(final_name) and sha256_file(target) == sums[final_name]:
        _log(f"  OK (cached, sha256) {target.name}")
        return target
    part_names = sorted(n for n in sums if n.startswith(final_name + ".part"))
    if not part_names:
        raise RuntimeError(f"No parts found for {final_name} in manifest")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".assembling")
    h = hashlib.sha256()
    with tmp.open("wb") as out:
        for pn in part_names:
            pp = parts_dir / pn
            if sha256_file(pp) != sums[pn]:
                raise RuntimeError(f"Part checksum mismatch: {pn}")
            with pp.open("rb") as f:
                while True:
                    block = f.read(CHUNK)
                    if not block:
                        break
                    out.write(block)
                    h.update(block)
    if sums.get(final_name) and h.hexdigest() != sums[final_name]:
        tmp.unlink()
        raise RuntimeError(f"Reassembled SHA-256 mismatch: {final_name}")
    tmp.replace(target)
    if cleanup:
        for pn in part_names:
            (parts_dir / pn).unlink(missing_ok=True)
    _log(f"  OK {target.name} (reassembled, sha256 verified)")
    return target


def step_zimage(dest: Path, repo: str, tag: str, source: str, cleanup_parts: bool) -> None:
    zdir = dest / "models" / "z-image"
    te = zdir / "text_encoders" / "qwen_3_4b.safetensors"
    vae = zdir / "vae" / "ae.safetensors"
    dit_dir = zdir / "diffusion_models"
    dit = dit_dir / "z_image_turbo_bf16.safetensors"
    if te.exists() and vae.exists() and dit.exists():
        _log("[3/4] z-image: already present, skip")
        return

    if source == "release":
        _log(f"[3/4] z-image: official Z-Image-Turbo (Apache-2.0) from our GitHub Release {tag}")
        base = f"https://github.com/{repo}/releases/download/{tag}"
        sums = _parse_sums(download(f"{base}/ZIMAGE_SHA256SUMS.txt", zdir / "ZIMAGE_SHA256SUMS.txt"))
        parts_dir = zdir / "_parts"
        parts_dir.mkdir(parents=True, exist_ok=True)
        download(f"{base}/ae.safetensors", vae, expected_sha256=sums.get("ae.safetensors"))
        for final_name, target in (("z_image_turbo_bf16.safetensors", dit), ("qwen_3_4b.safetensors", te)):
            for pn in sorted(n for n in sums if n.startswith(final_name + ".part")):
                download(f"{base}/{pn}", parts_dir / pn, expected_sha256=sums[pn])
            _reassemble(parts_dir, final_name, sums, target, cleanup_parts)
        if cleanup_parts and parts_dir.exists() and not any(parts_dir.iterdir()):
            parts_dir.rmdir()
        _log(f"  OK z-image -> {zdir}")
        return

    _log("[3/4] z-image: official Z-Image-Turbo bf16, text encoder, VAE from upstream (Comfy-Org)")
    meta = hf_file_meta()
    te_meta = meta.get("split_files/text_encoders/qwen_3_4b.safetensors", {})
    vae_meta = meta.get("split_files/vae/ae.safetensors", {})
    download(f"{HF_BASE}/text_encoders/qwen_3_4b.safetensors", te, expected_sha256=te_meta.get("sha256"), expected_size=te_meta.get("size"))
    download(f"{HF_BASE}/vae/ae.safetensors", vae, expected_sha256=vae_meta.get("sha256"), expected_size=vae_meta.get("size"))
    d_meta = meta.get("split_files/diffusion_models/z_image_turbo_bf16.safetensors", {})
    download(f"{HF_BASE}/diffusion_models/z_image_turbo_bf16.safetensors", dit, expected_sha256=d_meta.get("sha256"), expected_size=d_meta.get("size"))
    _log(f"  OK z-image -> {zdir}")


def step_binaries(dest: Path, repo: str, tag: str, cleanup_parts: bool = False) -> None:
    bin_dir = dest / "bin"
    exe = "llama-server.exe" if os.name == "nt" else "llama-server"
    sd_exe = "sd-cli.exe" if os.name == "nt" else "sd-cli"
    if (bin_dir / "llama" / exe).exists() and (bin_dir / "sd" / sd_exe).exists():
        _log("[4/4] binaries: already present, skip")
        return
    _log("[4/4] binaries: trying GitHub Release engine packages")
    name = f"SmartLLM-Engines-{tag}-windows11.zip" if os.name == "nt" else f"SmartLLM-Engines-{tag}-linux.tar.gz"
    url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
    downloads_dir = dest / "_downloads"
    archive = downloads_dir / name
    try:
        download(url, archive)
    except Exception as exc:
        _log(f"  NOT PUBLISHED YET ({exc}).")
        _log("  Build them from the SmartLLM forks (CUDA required):")
        _log("    llama.cpp:          smartllm-v2 branch (e24ccd7..2d8ec62) -> llama-server")
        _log("    stable-diffusion.cpp: -> sd-cli")
        _log(f"  Place engines into: {bin_dir / 'llama'} and {bin_dir / 'sd'} (exe + libs per engine)")
        return
    bin_dir.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(bin_dir)
    else:
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(bin_dir, filter="data")
    for tool in (bin_dir / "llama" / exe, bin_dir / "sd" / sd_exe):
        if tool.exists() and os.name != "nt":
            tool.chmod(0o755)
    if cleanup_parts:
        archive.unlink(missing_ok=True)
        if downloads_dir.exists() and not any(downloads_dir.iterdir()):
            downloads_dir.rmdir()
    _log(f"  OK binaries -> {bin_dir}")


def step_verify(dest: Path) -> None:
    _log("[verify] path discovery from the bundle (isolated from any user config):")
    studio_dir = dest / "studio"
    sys.path.insert(0, str(studio_dir))
    env = os.environ.copy()
    iso = tempfile.mkdtemp(prefix="smartllm_verify_")
    env["XDG_CONFIG_HOME"] = iso
    env["APPDATA"] = iso
    env["LOCALAPPDATA"] = iso
    for k in list(env):
        if k.startswith("SMARTLLM_"):
            del env[k]
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {repr(str(studio_dir))})\n"
        "from smartllm_studio.config import discover_studio_paths\n"
        f"p = discover_studio_paths(repo_root=__import__('pathlib').Path({repr(str(dest))}))\n"
        "keys = ['gguf_model_path','mmproj_path','llama_server_bin','sd_cli_bin','dit_model_path','te_model_path','vae_model_path']\n"
        "flags = {'gguf_model_path':'gguf_model_exists','mmproj_path':'mmproj_exists','llama_server_bin':'llama_server_exists','sd_cli_bin':'sd_cli_exists','dit_model_path':'dit_model_exists','te_model_path':'te_model_exists','vae_model_path':'vae_model_exists'}\n"
        "print(json.dumps({k: {'path': p[k], 'ok': p[flags[k]]} for k in keys}, ensure_ascii=False))\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, check=False)
    if proc.returncode != 0:
        _log(f"  verify failed: {proc.stderr.strip()[:400]}")
        return
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    for k, v in report.items():
        _log(f"  {'OK  ' if v['ok'] else 'MISS'} {k} = {v['path']}")
    missing = [k for k, v in report.items() if not v["ok"]]
    if missing:
        _log(f"  MISSING: {missing} — fix via Studio Settings or re-run setup.")
    else:
        _log("  ALL PATHS OK. Launch:")
        if os.name == "nt":
            _log(f"    {dest / 'studio' / 'smartllm-studio.bat'}")
        else:
            _log(f"    {dest / 'studio' / 'bin' / 'smartllm-studio'}")


def step_deps(dest: Path) -> None:
    """Create a bundle-local venv (.venv) and install Pillow so launchers work out of the box."""
    venv_dir = dest / ".venv"
    py = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        _log("Creating bundle Python venv (.venv) ...")
        res = subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        if res.returncode != 0 or not py.exists():
            _log("WARN: venv creation failed (" + (res.stderr or "").strip()[:200] + "). Install manually: python -m pip install Pillow")
            return
    _log("Installing Pillow into bundle venv ...")
    try:
        res = subprocess.run([str(py), "-m", "pip", "install", "--quiet", "Pillow"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    except subprocess.TimeoutExpired:
        _log("WARN: Pillow install timed out. Install manually: " + str(py) + " -m pip install Pillow")
        return
    if res.returncode != 0:
        _log("WARN: Pillow install failed: " + (res.stderr or "").strip()[:200])
    else:
        _log("Pillow OK (" + str(py) + ")")


def main(argv: list[str] | None = None) -> int:
    global _LINE_PROGRESS
    parser = argparse.ArgumentParser(description="Download the full SmartLLM bundle into ONE portable folder (any drive).")
    parser.add_argument("--dest", type=Path, default=Path("SmartLLM"), help="Target bundle folder (default: ./SmartLLM)")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--tag", default=DEFAULT_TAG, help="Studio version tag (Release asset if published, else the tagged source archive)")
    parser.add_argument("--studio-ref", default="", help="Install Studio from a branch source archive instead (e.g. main)")
    parser.add_argument("--model-tag", default=DEFAULT_MODEL_TAG, help="Release tag holding the 55 GiB GGUF parts + mmproj")
    parser.add_argument("--zimage-tag", default=DEFAULT_ZIMAGE_TAG, help="Release tag holding official Z-Image-Turbo weights")
    parser.add_argument("--engines-tag", default=DEFAULT_ENGINES_TAG, help="Release tag holding prebuilt CUDA engine binaries")
    parser.add_argument("--zimage-source", choices=["release", "hf"], default="release",
                        help="Z-Image weights source: our GitHub Release (default, official Apache-2.0 Turbo bf16) "
                             "or HuggingFace Comfy-Org (same official weights)")
    parser.add_argument("--skip-studio", action="store_true")
    parser.add_argument("--skip-model", action="store_true")
    parser.add_argument("--skip-zimage", action="store_true")
    parser.add_argument("--skip-binaries", action="store_true")
    parser.add_argument("--skip-deps", action="store_true", help="Skip bundle venv + Pillow install")
    parser.add_argument("--cleanup-parts", action="store_true", help="Delete .partNN files and downloaded archives after verified assembly (saves ~75 GiB)")
    parser.add_argument("--line-progress", action="store_true", help="Emit newline-terminated progress steps (~5%%) for HUD polling")
    args = parser.parse_args(argv)
    _LINE_PROGRESS = bool(args.line_progress)

    dest = args.dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    _log(f"SmartLLM bundle setup -> {dest}")
    if not _check_free_space(dest, args.skip_model, args.skip_zimage, args.skip_binaries, args.cleanup_parts):
        return 2
    if not args.skip_studio:
        step_studio(dest, args.repo, args.tag, args.cleanup_parts, args.studio_ref)
    if not args.skip_model:
        step_model(dest, args.repo, args.model_tag, args.cleanup_parts)
    if not args.skip_zimage:
        step_zimage(dest, args.repo, args.zimage_tag, args.zimage_source, args.cleanup_parts)
    if not args.skip_binaries:
        step_binaries(dest, args.repo, args.engines_tag, args.cleanup_parts)
    if not args.skip_deps:
        step_deps(dest)
    step_verify(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())