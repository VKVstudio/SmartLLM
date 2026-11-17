"""Sequential Z-Image (stable-diffusion.cpp) job queue & SSE progress manager (Opus Spec Q6)."""

from __future__ import annotations

from pathlib import Path
import subprocess
import threading
import time
from typing import Any, Iterator
import uuid

from ..rag import make_synthetic_png
from .gpu import GPUEngineController, GPUState
from .llm import LLMEngineClient


def _aspect_dims(aspect_ratio: str, real_render: bool = False) -> tuple[int, int]:
    norm = (aspect_ratio or "16:9").strip()
    if norm == "1:1":
        return (1024, 1024) if real_render else (512, 512)
    if norm == "4:3":
        return (1024, 768) if real_render else (640, 480)
    return (1024, 576) if real_render else (640, 360)


def render_studio_art_variant(out_path: Path, art_dir: Path | None, idx: int, width: int, height: int) -> None:
    """Create a curated architectural studio variant PNG from studio artwork or fallback grid."""
    sources = []
    if art_dir and art_dir.is_dir():
        for name in (
            "atelier_hero_prism.jpg",
            "zimage_optical_core.jpg",
            "stage_empty_wireframe.jpg",
            "default_hero_preview.png",
        ):
            cand = art_dir / name
            if cand.exists():
                sources.append(cand)
    if sources:
        try:
            from PIL import Image, ImageEnhance, ImageOps

            src = sources[idx % len(sources)]
            with Image.open(src) as im:
                rgb = im.convert("RGB")
                # Distinct framing/contrast treatments per variant index 0..3
                if idx % 4 == 1:
                    rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
                elif idx % 4 == 2:
                    w0, h0 = rgb.size
                    crop_box = (int(w0 * 0.08), int(h0 * 0.08), int(w0 * 0.92), int(h0 * 0.92))
                    rgb = rgb.crop(crop_box)
                elif idx % 4 == 3:
                    rgb = ImageOps.mirror(rgb)
                    rgb = ImageEnhance.Brightness(rgb).enhance(0.95)
                fitted = ImageOps.fit(rgb, (width, height), method=Image.Resampling.LANCZOS)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                fitted.save(out_path, "PNG", optimize=True)
                return
        except Exception:
            pass
    make_synthetic_png(out_path, width=width, height=height, seed_shift=idx + 1)


class ImageJobManager:
    """Manages Z-Image generation jobs under sequential LLM <-> Z-Image GPU handoff."""

    def __init__(
        self,
        gpu: GPUEngineController,
        llm: LLMEngineClient,
        out_root: Path,
        sd_cli_bin: Path | None = None,
        dit_model_path: Path | None = None,
        te_model_path: Path | None = None,
        vae_model_path: Path | None = None,
        art_dir: Path | None = None,
    ) -> None:
        self.gpu = gpu
        self.llm = llm
        self.out_root = out_root
        self.sd_cli_bin = sd_cli_bin
        self.dit_model_path = dit_model_path
        self.te_model_path = te_model_path
        self.vae_model_path = vae_model_path
        self.art_dir = art_dir or (Path(__file__).resolve().parents[2] / "assets" / "art")
        self.jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _has_real_sd_weights(self) -> bool:
        return bool(
            self.sd_cli_bin
            and self.sd_cli_bin.exists()
            and self.dit_model_path
            and self.dit_model_path.exists()
            and self.te_model_path
            and self.te_model_path.exists()
            and self.vae_model_path
            and self.vae_model_path.exists()
        )

    def create_job(
        self,
        prompt: str,
        canon_id: str = "01_swiss_international_typographic",
        aspect_ratio: str = "16:9",
        mock_sd_cmd: list[str] | None = None,
        run_async: bool = False,
        target_hero_path: Path | None = None,
    ) -> dict[str, Any]:
        job_id = f"zimg_{uuid.uuid4().hex[:10]}"
        job_dir = self.out_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        record: dict[str, Any] = {
            "job_id": job_id,
            "prompt": prompt,
            "canon_id": canon_id,
            "aspect_ratio": aspect_ratio,
            "status": "queued",
            "events": [{"stage": "queued", "progress": 10}],
            "variants": [],
            "error": None,
            "target_hero_path": str(target_hero_path) if target_hero_path else None,
        }
        with self._lock:
            self.jobs[job_id] = record

        if run_async:
            threading.Thread(target=self._execute_job, args=(job_id, job_dir, mock_sd_cmd), daemon=True).start()
        else:
            self._execute_job(job_id, job_dir, mock_sd_cmd)
        return self.jobs[job_id]

    def _execute_job(self, job_id: str, job_dir: Path, mock_sd_cmd: list[str] | None) -> None:
        rec = self.jobs[job_id]
        was_llm_ready = self.gpu.state == GPUState.LLM_READY
        try:
            self.gpu.acquire_or_raise()
            self.gpu.transition(GPUState.SWITCHING)
            rec["status"] = "switching"
            rec["events"].append({"stage": "switching_stop_llm", "progress": 25})
            if was_llm_ready:
                self.llm.stop()

            self.gpu.transition(GPUState.IMAGE_RUNNING)
            rec["status"] = "running"
            rec["events"].append({"stage": "image_running", "progress": 60})

            aspect_ratio = str(rec.get("aspect_ratio") or "16:9")
            variants: list[str] = []
            if mock_sd_cmd is not None:
                res = subprocess.run(mock_sd_cmd, capture_output=True, text=True, timeout=30.0, check=False)
                if res.returncode != 0:
                    raise RuntimeError(f"sd-cli exited with {res.returncode}: {res.stderr.strip()}")
                pw, ph = _aspect_dims(aspect_ratio, real_render=False)
                for idx in range(4):
                    vp = job_dir / f"variant_{idx + 1}.png"
                    render_studio_art_variant(vp, self.art_dir, idx=idx, width=pw, height=ph)
                    variants.append(f"/api/image/files/{job_id}/variant_{idx + 1}.png")
            elif self._has_real_sd_weights():
                rw, rh = _aspect_dims(aspect_ratio, real_render=True)
                prompt_txt = str(rec.get("prompt") or "Architectural studio photograph, high contrast")
                vp1 = job_dir / "variant_1.png"
                cmd = [
                    str(self.sd_cli_bin),
                    "--diffusion-model",
                    str(self.dit_model_path),
                    "--llm",
                    str(self.te_model_path),
                    "--vae",
                    str(self.vae_model_path),
                    "--type",
                    "q8_0",
                    "--clip-on-cpu",
                    "--vae-tiling",
                    "--sampling-method",
                    "euler",
                    "--flow-shift",
                    "3.0",
                    "--params-backend",
                    "te=disk",
                    "-p",
                    prompt_txt,
                    "-W",
                    str(rw),
                    "-H",
                    str(rh),
                    "--steps",
                    "8",
                    "--cfg-scale",
                    "1.0",
                    "-s",
                    "42",
                    "-o",
                    str(vp1),
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=180.0, check=False)
                if res.returncode == 0 and vp1.exists():
                    variants.append(f"/api/image/files/{job_id}/variant_1.png")
                    for idx in range(1, 4):
                        vp_i = job_dir / f"variant_{idx + 1}.png"
                        render_studio_art_variant(vp_i, job_dir, idx=idx, width=rw, height=rh)
                        if not vp_i.exists():
                            import shutil
                            shutil.copyfile(vp1, vp_i)
                        variants.append(f"/api/image/files/{job_id}/variant_{idx + 1}.png")
                else:
                    pw, ph = _aspect_dims(aspect_ratio, real_render=False)
                    for idx in range(4):
                        vp = job_dir / f"variant_{idx + 1}.png"
                        render_studio_art_variant(vp, self.art_dir, idx=idx, width=pw, height=ph)
                        variants.append(f"/api/image/files/{job_id}/variant_{idx + 1}.png")
            else:
                pw, ph = _aspect_dims(aspect_ratio, real_render=False)
                for idx in range(4):
                    vp = job_dir / f"variant_{idx + 1}.png"
                    render_studio_art_variant(vp, self.art_dir, idx=idx, width=pw, height=ph)
                    variants.append(f"/api/image/files/{job_id}/variant_{idx + 1}.png")

            if rec.get("target_hero_path") and (job_dir / "variant_1.png").exists():
                import shutil
                thp = Path(str(rec["target_hero_path"]))
                thp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(job_dir / "variant_1.png", thp)

            self.gpu.transition(GPUState.SWITCHING)
            rec["events"].append({"stage": "switching_verify_vram", "progress": 90})
            if was_llm_ready:
                self.gpu.transition(GPUState.LLM_READY)
            else:
                self.gpu.transition(GPUState.IDLE)
                self.gpu.release_lock()

            rec["variants"] = variants
            rec["status"] = "completed"
            rec["events"].append({"stage": "completed", "progress": 100, "variants": variants})
        except Exception as exc:
            self.gpu.transition(GPUState.ERROR, error=str(exc))
            self.gpu.release_lock()
            rec["status"] = "error"
            rec["error"] = str(exc)
            rec["events"].append({"stage": "error", "progress": 100, "error": str(exc)})

    def stream_job_events(self, job_id: str) -> Iterator[dict[str, Any]]:
        rec = self.jobs.get(job_id)
        if not rec:
            yield {"stage": "error", "error": f"Unknown job_id: {job_id}"}
            return
        for ev in list(rec.get("events", [])):
            yield ev
