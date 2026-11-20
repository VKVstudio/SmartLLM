#!/usr/bin/env python3
"""SmartLLM single-folder bundle setup (Linux + Windows 11, Python 3.11+, pure stdlib).

Downloads everything a new user needs into ONE portable folder on ANY drive:

    <dest>/studio/   SmartLLM Studio app (GitHub Release archive)
    <dest>/models/   SmartLLM-v2-K320-V1.gguf (30 parts -> SHA-256 verified reassembly),
                     mmproj-Qwen3.8-Flash-Next-BF16.gguf,
                     z-image/{diffusion_models,text_encoders,vae}/*.safetensors
    <dest>/bin/      llama-server & sd-cli engine binaries (when published in the Release)

This script is the ONLY online step; the Studio runtime stays fully offline (127.0.0.1).
Downloads are resumable and SHA-256 verified. By default EVERYTHING comes from our GitHub
Releases (model parts from --model-tag, Studio/engines/Z-Image from --tag) — no HuggingFace
or CivitAI access required.

Z-Image sources (--zimage-source):
  release   Official Tongyi-MAI Z-Image-Turbo bf16 (Apache-2.0), re-hosted in our Release [default]
  hf        Same official weights directly from Comfy-Org/Z-Image-Turbo on Hugging Face
  civitai   "BEYOND REALITY 3.0 FP8" finetune by Nurburgring (showcase visuals; credit the author)

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
import urllib.request
import zipfile

DEFAULT_REPO = "VKVstudio/SmartLLM"
DEFAULT_TAG = "v0.0.2-beta"
DEFAULT_MODEL_TAG = "v0.0.1-beta"  # 55 GiB GGUF parts + mmproj live in the first release (reused)
HF_BASE = "https://huggingface.co/Comfy-Org/Z-Image-Turbo/resolve/main/split_files"
HF_API_TREE = "https://huggingface.co/api/models/Comfy-Org/Z-Image-Turbo/tree/main/split_files"
CIVITAI_DIT_URL = "https://civitai.com/api/download/models/2674158"
CIVITAI_DIT_NAME = "beyond_reality_z_image_3.0_fp8.safetensors"
CIVITAI_DIT_BYTES = 6154970792
USER_AGENT = "SmartLLM-Setup/0.0.1 (local bundle installer)"
CHUNK = 4 * 1024 * 1024


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


def download(url: str, dest: Path, expected_sha256: str | None = None, expected_size: int | None = None) -> Path:
    """Resumable streaming download with SHA-256 / size verification and atomic promotion."""
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
        with part.open(mode) as out:
            while True:
                block = resp.read(CHUNK)
                if not block:
                    break
                out.write(block)
                done += len(block)
                if total:
                    pct = 100.0 * done / total
                    print(f"\r  {dest.name}: {done / 1e6:.0f}/{total / 1e6:.0f} MB ({pct:.1f}%)", end="", flush=True)
        if total:
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


def step_studio(dest: Path, repo: str, tag: str) -> None:
    studio_dir = dest / "studio"
    if (studio_dir / "smartllm_studio" / "cli.py").exists():
        _log("[1/4] studio: already present, skip")
        return
    _log("[1/4] studio: downloading app archive")
    win = os.name == "nt"
    name = f"SmartLLM-Studio-{tag}-windows11.zip" if win else f"SmartLLM-Studio-{tag}-linux.tar.gz"
    url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
    archive = download(url, dest / "_downloads" / name)
    tmp_extract = dest / "_downloads" / "studio_extract"
    if tmp_extract.exists():
        shutil.rmtree(tmp_extract)
    tmp_extract.mkdir(parents=True)
    if win:
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(tmp_extract)
    else:
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(tmp_extract, filter="data")
    roots = [p for p in tmp_extract.iterdir() if p.is_dir()]
    if len(roots) != 1:
        raise RuntimeError(f"Unexpected archive layout: {roots}")
    roots[0].replace(studio_dir)
    shutil.rmtree(tmp_extract, ignore_errors=True)
    _log(f"  OK studio -> {studio_dir}")


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


def step_zimage(dest: Path, repo: str, tag: str, source: str, dit_choice: str, cleanup_parts: bool) -> None:
    zdir = dest / "models" / "z-image"
    te = zdir / "text_encoders" / "qwen_3_4b.safetensors"
    vae = zdir / "vae" / "ae.safetensors"
    dit_dir = zdir / "diffusion_models"
    dit_name = "z_image_turbo_bf16.safetensors" if source != "civitai" else CIVITAI_DIT_NAME
    dit = dit_dir / dit_name
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

    _log(f"[3/4] z-image: downloading DiT ({dit_choice}), text encoder, VAE from upstream")
    meta = hf_file_meta()
    te_meta = meta.get("split_files/text_encoders/qwen_3_4b.safetensors", {})
    vae_meta = meta.get("split_files/vae/ae.safetensors", {})
    download(f"{HF_BASE}/text_encoders/qwen_3_4b.safetensors", te, expected_sha256=te_meta.get("sha256"), expected_size=te_meta.get("size"))
    download(f"{HF_BASE}/vae/ae.safetensors", vae, expected_sha256=vae_meta.get("sha256"), expected_size=vae_meta.get("size"))
    if source == "civitai":
        _log("  source: CivitAI 'BEYOND REALITY 3.0 FP8' by Nurburgring (please credit the author)")
        download(CIVITAI_DIT_URL, dit, expected_size=CIVITAI_DIT_BYTES)
    else:
        d_meta = meta.get("split_files/diffusion_models/z_image_turbo_bf16.safetensors", {})
        download(f"{HF_BASE}/diffusion_models/z_image_turbo_bf16.safetensors", dit, expected_sha256=d_meta.get("sha256"), expected_size=d_meta.get("size"))
    _log(f"  OK z-image -> {zdir}")


def step_binaries(dest: Path, repo: str, tag: str) -> None:
    bin_dir = dest / "bin"
    exe = "llama-server.exe" if os.name == "nt" else "llama-server"
    sd_exe = "sd-cli.exe" if os.name == "nt" else "sd-cli"
    if (bin_dir / "llama" / exe).exists() and (bin_dir / "sd" / sd_exe).exists():
        _log("[4/4] binaries: already present, skip")
        return
    _log("[4/4] binaries: trying GitHub Release engine packages")
    name = f"SmartLLM-Engines-{tag}-windows11.zip" if os.name == "nt" else f"SmartLLM-Engines-{tag}-linux.tar.gz"
    url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
    archive = dest / "_downloads" / name
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
    _log(f"  OK binaries -> {bin_dir}")


def step_verify(dest: Path) -> None:
    _log("[verify] path discovery from the bundle:")
    studio_dir = dest / "studio"
    sys.path.insert(0, str(studio_dir))
    env = os.environ.copy()
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {repr(str(studio_dir))})\n"
        "from smartllm_studio.config import discover_studio_paths\n"
        f"p = discover_studio_paths(repo_root=__import__('pathlib').Path({repr(str(dest))}))\n"
        "keys = ['gguf_model_path','mmproj_path','llama_server_bin','sd_cli_bin','dit_model_path','te_model_path','vae_model_path']\n"
        "flags = {'gguf_model_path':'gguf_model_exists','mmproj_path':'mmproj_exists','llama_server_bin':'llama_server_exists','sd_cli_bin':'sd_cli_exists','dit_model_path':'dit_model_exists','te_model_path':'te_model_exists','vae_model_path':'vae_model_exists'}\n"
        "print(json.dumps({k: {'path': p[k], 'ok': p[flags[k]]} for k in keys}, ensure_ascii=False))\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=False)
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
    parser = argparse.ArgumentParser(description="Download the full SmartLLM bundle into ONE portable folder (any drive).")
    parser.add_argument("--dest", type=Path, default=Path("SmartLLM"), help="Target bundle folder (default: ./SmartLLM)")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--tag", default=DEFAULT_TAG, help="Release tag for Studio, engines and Z-Image weights")
    parser.add_argument("--model-tag", default=DEFAULT_MODEL_TAG, help="Release tag holding the 55 GiB GGUF parts + mmproj")
    parser.add_argument("--zimage-source", choices=["release", "hf", "civitai"], default="release",
                        help="Z-Image weights source: our GitHub Release (default, official Apache-2.0 Turbo), "
                             "HuggingFace Comfy-Org, or CivitAI 'Beyond Reality' finetune (credit author Nurburgring)")
    parser.add_argument("--dit", choices=["turbo-bf16", "beyond-reality-fp8"], default="turbo-bf16",
                        help="DiT variant for --zimage-source hf (civitai always uses beyond-reality-fp8)")
    parser.add_argument("--skip-studio", action="store_true")
    parser.add_argument("--skip-model", action="store_true")
    parser.add_argument("--skip-zimage", action="store_true")
    parser.add_argument("--skip-binaries", action="store_true")
    parser.add_argument("--skip-deps", action="store_true", help="Skip bundle venv + Pillow install")
    parser.add_argument("--cleanup-parts", action="store_true", help="Delete .partNN files after verified reassembly (saves ~75 GiB)")
    args = parser.parse_args(argv)

    dest = args.dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    _log(f"SmartLLM bundle setup -> {dest}")
    _log("Total download: ~55 GiB model + ~20 GiB Z-Image + ~3 GiB engines + ~7 MB app (all from GitHub Releases by default).")
    if not args.skip_studio:
        step_studio(dest, args.repo, args.tag)
    if not args.skip_model:
        step_model(dest, args.repo, args.model_tag, args.cleanup_parts)
    if not args.skip_zimage:
        step_zimage(dest, args.repo, args.tag, args.zimage_source, args.dit, args.cleanup_parts)
    if not args.skip_binaries:
        step_binaries(dest, args.repo, args.tag)
    if not args.skip_deps:
        step_deps(dest)
    step_verify(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())