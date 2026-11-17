#!/usr/bin/env python3
"""Wave 4 Evaluation Runner for SmartLLM v2 (`SmartLLM-v2-K320-V1.gguf`).

Supports resumable GPU and offline CPU stages:
1. `--mode text-and-holdout`: Runs all 12 text/code suite tasks (`t1, t3, t4, t_backend_form,
   t_zimage_site, t5..t11`) + 6 blind holdout tasks (`h1..h6`) in one `llama-server` session on
   `127.0.0.1:18089` (`--n-cpu-moe 42 --moe-cache-mib 2048 --moe-cache-cpu-share 0.00 -ot blk\\.48\\..*=CPU`).
2. `--mode render-zimage`: Renders model-generated `zimage_prompts.json` for `t_zimage_site`
   and `h1` via `sd-cli --batch-json` (`beyond_reality_z_image_3.0_fp8.safetensors` `q8_0`).
3. `--mode vision`: Runs the 2 vision suite tasks (`t2, t12`) with `mmproj-Qwen3.8-Flash-Next-BF16.gguf`
   (`--image-min-tokens 1024 --n-cpu-moe 43 --moe-cache-mib 1408 --moe-cache-cpu-share 0.00 -ot blk\\.48\\..*=CPU`).
4. `--mode audit-holdout`: Offline CPU validation + headless Chrome 148 / Lighthouse audit on
   `eval/holdout/runs/<slug>/` (strictly keeping holdout prompt text isolated).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.holdout import validate_holdout as vh  # noqa: E402
from eval.suite import code_checks as cc, run_suite  # noqa: E402
from scripts import platform_paths as pp  # noqa: E402
from scripts.combine.gpu_switch import (  # noqa: E402
    DEFAULT_DIT_FP8,
    DEFAULT_LLAMA_SERVER,
    DEFAULT_QWEN_TE,
    DEFAULT_SD_CLI,
    DEFAULT_VAE,
    parse_aspect_ratio_dims,
    verify_png_artifact,
)

DEFAULT_MODEL_V2 = ROOT / "models" / "SmartLLM-v2-K320-V1.gguf"
DEFAULT_MMPROJ = ROOT / "models" / "mmproj-Qwen3.8-Flash-Next-BF16.gguf"
HOLDOUT_TASKS_JSON = ROOT / "eval" / "holdout" / "tasks_holdout.json"
HOLDOUT_RUNS_DIR = ROOT / "eval" / "holdout" / "runs"
WAVE4_OUT_DIR = ROOT / "research" / "v2_runs" / "wave4"

TEXT_SUITE_ORDER: tuple[str, ...] = (
    "t1",
    "t3",
    "t4",
    "t_backend_form",
    "t_zimage_site",
    "t5",
    "t6",
    "t7",
    "t8",
    "t9",
    "t10",
    "t11",
)
VISION_SUITE_ORDER: tuple[str, ...] = ("t2", "t12")


def evict_page_cache(paths: list[Path]) -> None:
    """Drop VFS page cache via POSIX_FADV_DONTNEED immediately after GPU/file use."""
    if not hasattr(os, "posix_fadvise") or not hasattr(os, "POSIX_FADV_DONTNEED"):
        return
    for p in paths:
        if not p.exists() or not p.is_file():
            continue
        try:
            fd = os.open(str(p), os.O_RDONLY)
            try:
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            finally:
                os.close(fd)
        except Exception:
            pass


class PeriodicPageCacheTrimmer:
    """Periodically evict cold GGUF file page-cache pages (POSIX_FADV_DONTNEED) during generation.

    Prevents 22 GiB RssFile accumulation from waking CachyOS kswapd (vm.swappiness=150)
    and compressing background desktop pages into zram0 (`zram_orig_delta_mib <= 512 MiB`).
    """

    def __init__(self, paths: list[Path], interval_sec: float = 12.0) -> None:
        self.paths = list(paths)
        self.interval_sec = interval_sec
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        evict_page_cache(self.paths)
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_sec):
            evict_page_cache(self.paths)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        evict_page_cache(self.paths)


def wait_for_llama_health(proc: subprocess.Popen[Any], host: str, port: int, timeout_sec: float = 240.0) -> float:
    t0 = time.perf_counter()
    url = f"http://{host}:{port}/health"
    while time.perf_counter() - t0 < timeout_sec:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited prematurely with rc={proc.poll()}")
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == "ok":
                        return round(time.perf_counter() - t0, 2)
        except Exception:
            pass
        time.sleep(0.5)
    raise TimeoutError(f"llama-server health check timed out after {timeout_sec}s on {url}")


def stop_llama_server(proc: subprocess.Popen[Any] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=15.0)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=5.0)
        except Exception:
            pass


def build_llama_server_cmd(
    model_path: Path,
    host: str,
    port: int,
    n_cpu_moe: int,
    moe_cache_mib: int,
    moe_cache_cpu_share: float = 0.00,
    mmproj_path: Path | None = None,
    reasoning_budget: int = 4000,
) -> list[str]:
    pp.assert_local_endpoint(f"http://{host}:{port}")
    cmd = [
        str(DEFAULT_LLAMA_SERVER),
        "-m",
        str(model_path),
        "--host",
        host,
        "--port",
        str(port),
        "-fit",
        "off",
        "--lazy-mode",
        "direct",
        "--n-cpu-moe",
        str(n_cpu_moe),
        "-nr",
        "--moe-cache-mib",
        str(moe_cache_mib),
        "--moe-cache-cpu-share",
        f"{moe_cache_cpu_share:.2f}",
        "-fa",
        "on",
        "-ctk",
        "q8_0",
        "-ctv",
        "q8_0",
        "-c",
        "32768",
        "-ub",
        "512",
        "-ngl",
        "99",
        "-np",
        "1",
        "--cache-ram",
        "0",
        "--ctx-checkpoints",
        "0",
        "--no-cache-prompt",
        "--reasoning-budget",
        str(reasoning_budget),
        "--reasoning-effort",
        "medium",
        "--temp",
        str(run_suite.DEFAULT_TEMPERATURE),
        "--top-k",
        str(run_suite.DEFAULT_TOP_K),
        "--top-p",
        str(run_suite.DEFAULT_TOP_P),
        "--min-p",
        str(run_suite.DEFAULT_MIN_P),
        "-ot",
        r"blk\.48\..*=CPU",
        "--no-webui",
    ]
    if mmproj_path is not None:
        cmd.extend(["--mmproj", str(mmproj_path), "--image-min-tokens", "1024"])
    return cmd


def run_holdout_task(
    endpoint: str,
    model_slug: str,
    task_spec: dict[str, Any],
    reasoning_budget: int = 4000,
    max_tokens: int = 16384,
    force: bool = False,
) -> dict[str, Any]:
    """Run a single blind holdout task and save ONLY inside eval/holdout/runs/<model_slug>/<tid>/."""
    pp.assert_local_endpoint(endpoint)
    tid = task_spec["id"]
    out_dir = HOLDOUT_RUNS_DIR / model_slug / tid
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out_dir / "meta.json"
    raw_path = out_dir / "raw.md"

    if not force and raw_path.exists() and raw_path.stat().st_size > 0 and meta_path.exists():
        try:
            prev_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if prev_meta.get("status") != "error" and prev_meta.get("deliverable_complete"):
                print(f"[SKIP-HOLDOUT] {model_slug} / {tid} already complete.", flush=True)
                return prev_meta
        except Exception:
            pass

    payload: dict[str, Any] = {
        "model": model_slug,
        "messages": [
            {"role": "system", "content": task_spec["system_prompt"]},
            {"role": "user", "content": task_spec["prompt"]},
        ],
        "temperature": run_suite.DEFAULT_TEMPERATURE,
        "top_k": run_suite.DEFAULT_TOP_K,
        "top_p": run_suite.DEFAULT_TOP_P,
        "min_p": run_suite.DEFAULT_MIN_P,
        "max_tokens": max_tokens,
        "cache_prompt": False,
        "reasoning_budget_tokens": reasoning_budget,
        "reasoning_budget": reasoning_budget,
        "thinking_budget": reasoning_budget,
        "chat_template_kwargs": {
            "enable_thinking": reasoning_budget > 0,
            "reasoning_effort": "medium" if reasoning_budget > 0 else "none",
        },
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer local", "Content-Type": "application/json"},
        method="POST",
    )
    print(f"[START-HOLDOUT] {model_slug} -> {tid} (lang={task_spec.get('language')}, cat={task_spec.get('category')}) ...", flush=True)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=2700) as resp:
            resp_bytes = resp.read()
        elapsed = round(time.perf_counter() - t0, 2)
        data = json.loads(resp_bytes.decode("utf-8"))
    except Exception as exc:
        elapsed = round(time.perf_counter() - t0, 2)
        meta = {
            "model_slug": model_slug,
            "task": tid,
            "status": "error",
            "error": str(exc),
            "elapsed_sec": elapsed,
        }
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[ERROR-HOLDOUT] {model_slug} / {tid}: {exc} in {elapsed}s", flush=True)
        return meta

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    reasoning_text = msg.get("reasoning_content") or msg.get("reasoning") or ""

    raw_path.write_text(content, encoding="utf-8")
    if reasoning_text:
        (out_dir / "reasoning.md").write_text(reasoning_text, encoding="utf-8")

    # Preserve raw extracted files in orig/ before any later postprocessing
    extracted_files = run_suite.extract_files_from_raw(content, str(out_dir), task_spec)
    orig_dir = out_dir / "orig"
    orig_dir.mkdir(parents=True, exist_ok=True)
    for req_f in task_spec.get("required_files", []):
        fp = out_dir / req_f
        if fp.exists():
            (orig_dir / req_f).write_text(fp.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

    completeness = run_suite.check_extraction_completeness(str(out_dir), task_spec, extracted_files)
    usage = data.get("usage") or {}
    timings = data.get("timings") or {}
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
    raw_tps = timings.get("predicted_per_second")
    tok_per_sec = (
        round(float(raw_tps), 2)
        if isinstance(raw_tps, (int, float)) and raw_tps > 0
        else (round(completion_tokens / elapsed, 2) if elapsed > 0 and completion_tokens > 0 else None)
    )

    meta = {
        "model_slug": model_slug,
        "task": tid,
        "category": task_spec.get("category"),
        "language": task_spec.get("language"),
        "temperature": run_suite.DEFAULT_TEMPERATURE,
        "top_k": run_suite.DEFAULT_TOP_K,
        "top_p": run_suite.DEFAULT_TOP_P,
        "min_p": run_suite.DEFAULT_MIN_P,
        "eos_logit_bias": run_suite.DEFAULT_EOS_LOGIT_BIAS,
        "max_tokens": max_tokens,
        "reasoning_budget": reasoning_budget,
        "finish_reason": choice.get("finish_reason"),
        "elapsed_sec": elapsed,
        "tok_per_sec": tok_per_sec,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": usage.get("total_tokens", prompt_tokens + completion_tokens),
        },
        "extracted_files": extracted_files,
        **completeness,
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"[DONE-HOLDOUT] {model_slug} / {tid} in {elapsed}s ({tok_per_sec} tok/s) | "
        f"comp={completion_tokens} | files={extracted_files} | complete={completeness['deliverable_complete']}",
        flush=True,
    )
    return meta


def run_text_and_holdout_stage(args: argparse.Namespace) -> int:
    WAVE4_OUT_DIR.mkdir(parents=True, exist_ok=True)
    suite_tasks = json.loads(pp.TASKS_JSON.read_text(encoding="utf-8"))["tasks"]
    suite_by_id = {t["id"]: t for t in suite_tasks}
    holdout_tasks = json.loads(HOLDOUT_TASKS_JSON.read_text(encoding="utf-8"))["tasks"]
    holdout_by_id = {t["id"]: t for t in holdout_tasks}

    target_suite_ids = [tid for tid in TEXT_SUITE_ORDER if not args.tasks or tid in args.tasks]
    target_holdout_ids = [
        t["id"]
        for t in holdout_tasks
        if not args.skip_holdout and (not args.tasks or t["id"] in args.tasks)
    ]

    cmd = build_llama_server_cmd(
        model_path=args.gguf,
        host=args.host,
        port=args.port,
        n_cpu_moe=args.n_cpu_moe,
        moe_cache_mib=args.moe_cache_mib,
        moe_cache_cpu_share=args.moe_cache_cpu_share,
        mmproj_path=None,
        reasoning_budget=args.reasoning_budget,
    )
    server_log = WAVE4_OUT_DIR / f"server_text_{args.model_slug}.log"
    endpoint = f"http://{args.host}:{args.port}/v1/chat/completions"

    proc: subprocess.Popen[Any] | None = None
    active_run_count = 0
    restart_limit = max(1, int(getattr(args, "restart_every_n_tasks", 4)))
    trimmer = PeriodicPageCacheTrimmer([args.gguf], interval_sec=12.0)
    trimmer.start()
    try:
        with server_log.open("a", encoding="utf-8") as log_fh:
            def _ensure_server() -> None:
                nonlocal proc
                if proc is not None and proc.poll() is None:
                    return
                proc = subprocess.Popen(
                    cmd,
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                ready_sec = wait_for_llama_health(proc, args.host, args.port, timeout_sec=240.0)
                print(f"[SERVER-READY] text-and-holdout healthy in {ready_sec}s (pid={proc.pid})", flush=True)

            def _maybe_cycle_server() -> None:
                nonlocal proc, active_run_count
                if active_run_count >= restart_limit:
                    print(f"[SERVER-CYCLE] Cycling llama-server after {active_run_count} active tasks to reset zram proc_swap ...", flush=True)
                    stop_llama_server(proc)
                    proc = None
                    evict_page_cache([args.gguf])
                    time.sleep(2.0)
                    active_run_count = 0

            force_set = set(getattr(args, "force_tasks", None) or [])
            suite_results: list[dict[str, Any]] = []
            for tid in target_suite_ids:
                t_spec = suite_by_id[tid]
                t_out_dir = pp.RUNS_DIR / args.model_slug / tid
                force_this = bool(args.force or tid in force_set)
                already_done = (
                    not force_this
                    and (t_out_dir / "raw.md").exists()
                    and (t_out_dir / "raw.md").stat().st_size > 0
                    and (t_out_dir / "meta.json").exists()
                )
                if not already_done:
                    _maybe_cycle_server()
                    _ensure_server()
                    active_run_count += 1
                res = run_suite.run_task(
                    endpoint=endpoint,
                    model_slug=args.model_slug,
                    model_id=args.model_slug,
                    task_spec=t_spec,
                    reasoning_budget=args.reasoning_budget,
                    max_tokens=args.max_tokens,
                    temperature=run_suite.DEFAULT_TEMPERATURE,
                    top_k=run_suite.DEFAULT_TOP_K,
                    top_p=run_suite.DEFAULT_TOP_P,
                    min_p=run_suite.DEFAULT_MIN_P,
                    dry_multiplier=0.0,
                    eos_logit_bias=0.0,
                    force=force_this,
                )
                # Snapshot raw extracted files into orig/ before any CSP packaging
                orig_dir = t_out_dir / "orig"
                orig_dir.mkdir(parents=True, exist_ok=True)
                for req_f in t_spec.get("required_files", []):
                    fp = t_out_dir / req_f
                    if fp.exists() and (force_this or not (orig_dir / req_f).exists()):
                        (orig_dir / req_f).write_text(fp.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
                suite_results.append(res)
                run_suite.merge_run_summary(args.model_slug, suite_results, suite_tasks)
                if res.get("status") == "error":
                    raise RuntimeError(f"Suite task {tid} failed: {res.get('error')}")

            holdout_results: list[dict[str, Any]] = []
            for hid in target_holdout_ids:
                h_spec = holdout_by_id[hid]
                h_out_dir = HOLDOUT_RUNS_DIR / args.model_slug / hid
                force_h = bool(args.force or hid in force_set)
                h_already_done = (
                    not force_h
                    and (h_out_dir / "raw.md").exists()
                    and (h_out_dir / "raw.md").stat().st_size > 0
                    and (h_out_dir / "meta.json").exists()
                )
                if not h_already_done:
                    _maybe_cycle_server()
                    _ensure_server()
                    active_run_count += 1
                h_res = run_holdout_task(
                    endpoint=endpoint,
                    model_slug=args.model_slug,
                    task_spec=h_spec,
                    reasoning_budget=args.reasoning_budget,
                    max_tokens=args.max_tokens,
                    force=force_h,
                )
                holdout_results.append(h_res)
                h_summary_path = HOLDOUT_RUNS_DIR / args.model_slug / "holdout_run_summary.json"
                h_summary_path.write_text(
                    json.dumps(holdout_results, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                if h_res.get("status") == "error":
                    raise RuntimeError(f"Holdout task {hid} failed: {h_res.get('error')}")
    finally:
        trimmer.stop()
        stop_llama_server(proc)
        evict_page_cache([args.gguf])
    return 0


def _collect_zimage_jobs_from_task_dir(task_dir: Path, max_jobs: int = 3) -> list[dict[str, Any]]:
    z_path = task_dir / "zimage_prompts.json"
    if not z_path.exists():
        return []
    z_txt = z_path.read_text(encoding="utf-8", errors="replace")
    raw_items: list[Any] = []
    try:
        z_data = json.loads(z_txt)
        if isinstance(z_data, dict):
            for k in ("prompts", "images", "assets", "items"):
                if isinstance(z_data.get(k), list):
                    raw_items = z_data[k]
                    break
        elif isinstance(z_data, list):
            raw_items = z_data
    except Exception:
        # Fallback regex extraction if model emitted an unescaped inner quote inside prompt text
        for m in re.finditer(r"\{[^{}]*\"prompt\"\s*:\s*\"(.*?)\"\s*,\s*\"negative_prompt\"\s*:\s*\"(.*?)\"[^{}]*\}", z_txt, re.DOTALL):
            block = m.group(0)
            id_m = re.search(r"\"id\"\s*:\s*\"([^\"]+)\"", block)
            out_m = re.search(r"\"(?:output_relpath|output_path|filename)\"\s*:\s*\"([^\"]+)\"", block)
            raw_items.append(
                {
                    "id": id_m.group(1) if id_m else f"asset_{len(raw_items) + 1}",
                    "output_path": out_m.group(1) if out_m else f"assets/zimage_{len(raw_items) + 1:02d}.png",
                    "prompt": m.group(1).replace('\\"', '"'),
                    "negative_prompt": m.group(2).replace('\\"', '"'),
                    "width": 1024,
                    "height": 1024,
                }
            )

    jobs: list[dict[str, Any]] = []
    assets_dir = task_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    for idx, item in enumerate(raw_items[:max_jobs]):
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or item.get("positive_prompt") or item.get("description") or "").strip()
        if not prompt:
            continue
        neg_prompt = str(
            item.get("negative_prompt")
            or "blurry, low quality, watermark, oversaturated neon, malformed hands, deformed text"
        ).strip()
        rel_out = str(
            item.get("output_relpath")
            or item.get("output_path")
            or item.get("filename")
            or item.get("path")
            or item.get("id")
            or f"assets/zimage_{idx + 1}.png"
        ).strip()
        orig_rel_clean = rel_out.lstrip("/\\")
        if not rel_out.lower().endswith(".png"):
            rel_out += ".png"
        rel_clean = rel_out.lstrip("/\\")
        out_path = task_dir / rel_clean
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if "width" in item and "height" in item and isinstance(item["width"], int) and isinstance(item["height"], int):
            w, h = int(item["width"]), int(item["height"])
        else:
            w, h = parse_aspect_ratio_dims(
                str(item.get("aspect_ratio") or "1:1"),
                default_w=1024,
                default_h=1024,
            )
        # Keep resolution at 1024x1024 or <= 1024 max side for fast, deterministic VRAM budget
        w = min(1024, max(512, (w // 64) * 64))
        h = min(1024, max(512, (h // 64) * 64))

        jobs.append(
            {
                "id": str(item.get("id") or f"asset_{idx + 1}"),
                "prompt": prompt,
                "negative_prompt": neg_prompt,
                "width": w,
                "height": h,
                "steps": 8,
                "cfg_scale": 1.0,
                "seed": int(item.get("seed") or (42 + idx)),
                "output_path": str(out_path),
                "alias_output_path": str(task_dir / orig_rel_clean) if orig_rel_clean != rel_clean else None,
            }
        )
    return jobs


def run_render_zimage_stage(args: argparse.Namespace) -> int:
    WAVE4_OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_dirs = [
        pp.RUNS_DIR / args.model_slug / "t_zimage_site",
        HOLDOUT_RUNS_DIR / args.model_slug / "h1",
    ]
    all_jobs: list[dict[str, Any]] = []
    for tdir in target_dirs:
        if tdir.exists():
            all_jobs.extend(_collect_zimage_jobs_from_task_dir(tdir, max_jobs=args.max_zimages_per_task))

    if not all_jobs:
        print("[ZIMAGE] No zimage_prompts.json jobs found to render.", flush=True)
        return 0

    batch_json_path = WAVE4_OUT_DIR / f"zimage_batch_{args.model_slug}.json"
    batch_json_path.write_text(json.dumps(all_jobs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"[ZIMAGE] Rendering {len(all_jobs)} Z-Image asset(s) sequentially with --params-backend te=disk ...", flush=True)
    trimmer = PeriodicPageCacheTrimmer(
        [DEFAULT_DIT_FP8, DEFAULT_QWEN_TE, DEFAULT_VAE, DEFAULT_MODEL_V2],
        interval_sec=0.25,
    )
    trimmer.start()
    try:
        verified: list[dict[str, Any]] = []
        for idx, job in enumerate(all_jobs):
            out_p = Path(job["output_path"])
            if not args.force and out_p.exists() and out_p.stat().st_size > 1024:
                v_prev = verify_png_artifact(out_p, expected_width=int(job["width"]), expected_height=int(job["height"]))
                if v_prev.get("valid"):
                    print(f"[ZIMAGE-SKIP] {out_p} already rendered and valid.", flush=True)
                    verified.append(v_prev)
                    continue
            cmd = [
                str(DEFAULT_SD_CLI),
                "--diffusion-model",
                str(DEFAULT_DIT_FP8),
                "--llm",
                str(DEFAULT_QWEN_TE),
                "--vae",
                str(DEFAULT_VAE),
                "--type",
                "q8_0",
                "--clip-on-cpu",
                "--params-backend",
                "te=disk",
                "--vae-tiling",
                "--steps",
                "8",
                "--cfg-scale",
                "1.0",
                "--flow-shift",
                "3.0",
                "--sampling-method",
                "euler",
                "-W",
                str(job["width"]),
                "-H",
                str(job["height"]),
                "-s",
                str(job["seed"]),
                "-p",
                job["prompt"],
                "-o",
                job["output_path"],
            ]
            print(f"[ZIMAGE-ITEM {idx + 1}/{len(all_jobs)}] -> {job['output_path']} ...", flush=True)
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
            evict_page_cache([DEFAULT_DIT_FP8, DEFAULT_QWEN_TE, DEFAULT_VAE])
            if proc.returncode != 0:
                raise RuntimeError(f"sd-cli failed on item {idx + 1} (rc={proc.returncode}): {proc.stderr[-1000:]}")
            v = verify_png_artifact(out_p, expected_width=int(job["width"]), expected_height=int(job["height"]))
            if not v.get("valid"):
                raise RuntimeError(f"Rendered PNG failed verification: {v}")
            alias_p = job.get("alias_output_path")
            if alias_p and not Path(alias_p).exists():
                Path(alias_p).parent.mkdir(parents=True, exist_ok=True)
                Path(alias_p).write_bytes(out_p.read_bytes())
            verified.append(v)
        summary_path = WAVE4_OUT_DIR / f"zimage_render_{args.model_slug}_summary.json"
        summary_path.write_text(json.dumps({"rendered": verified}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[ZIMAGE] Verified {len(verified)} non-blank PNG(s) -> {summary_path}", flush=True)
    finally:
        trimmer.stop()
        evict_page_cache([DEFAULT_DIT_FP8, DEFAULT_QWEN_TE, DEFAULT_VAE])
    return 0


def run_vision_stage(args: argparse.Namespace) -> int:
    WAVE4_OUT_DIR.mkdir(parents=True, exist_ok=True)
    suite_tasks = json.loads(pp.TASKS_JSON.read_text(encoding="utf-8"))["tasks"]
    suite_by_id = {t["id"]: t for t in suite_tasks}
    target_vision_ids = [tid for tid in VISION_SUITE_ORDER if not args.tasks or tid in args.tasks]

    cmd = build_llama_server_cmd(
        model_path=args.gguf,
        host=args.host,
        port=args.port,
        n_cpu_moe=args.n_cpu_moe,
        moe_cache_mib=args.moe_cache_mib,
        moe_cache_cpu_share=args.moe_cache_cpu_share,
        mmproj_path=args.mmproj,
        reasoning_budget=args.reasoning_budget,
    )
    server_log = WAVE4_OUT_DIR / f"server_vision_{args.model_slug}.log"
    endpoint = f"http://{args.host}:{args.port}/v1/chat/completions"

    proc: subprocess.Popen[Any] | None = None
    trimmer = PeriodicPageCacheTrimmer([args.gguf, args.mmproj], interval_sec=2.0)
    trimmer.start()
    try:
        with server_log.open("w", encoding="utf-8") as log_fh:
            proc = subprocess.Popen(
                cmd,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                text=True,
            )
            ready_sec = wait_for_llama_health(proc, args.host, args.port, timeout_sec=240.0)
            print(f"[SERVER-READY] vision healthy in {ready_sec}s (pid={proc.pid})", flush=True)

            vision_results: list[dict[str, Any]] = []
            for tid in target_vision_ids:
                t_spec = suite_by_id[tid]
                res = run_suite.run_task(
                    endpoint=endpoint,
                    model_slug=args.model_slug,
                    model_id=args.model_slug,
                    task_spec=t_spec,
                    reasoning_budget=args.reasoning_budget,
                    max_tokens=args.max_tokens,
                    temperature=run_suite.DEFAULT_TEMPERATURE,
                    top_k=run_suite.DEFAULT_TOP_K,
                    top_p=run_suite.DEFAULT_TOP_P,
                    min_p=run_suite.DEFAULT_MIN_P,
                    dry_multiplier=0.0,
                    eos_logit_bias=0.0,
                    force=args.force,
                )
                t_out_dir = pp.RUNS_DIR / args.model_slug / tid
                orig_dir = t_out_dir / "orig"
                orig_dir.mkdir(parents=True, exist_ok=True)
                for req_f in t_spec.get("required_files", []):
                    fp = t_out_dir / req_f
                    if fp.exists() and not (orig_dir / req_f).exists():
                        (orig_dir / req_f).write_text(fp.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
                vision_results.append(res)
                run_suite.merge_run_summary(args.model_slug, vision_results, suite_tasks)
                if res.get("status") == "error":
                    raise RuntimeError(f"Vision task {tid} failed: {res.get('error')}")
    finally:
        trimmer.stop()
        stop_llama_server(proc)
        evict_page_cache([args.gguf, args.mmproj])
    return 0


def run_audit_holdout_stage(args: argparse.Namespace) -> int:
    holdout_tasks = json.loads(HOLDOUT_TASKS_JSON.read_text(encoding="utf-8"))["tasks"]
    model_holdout_dir = HOLDOUT_RUNS_DIR / args.model_slug
    if not model_holdout_dir.exists():
        raise FileNotFoundError(f"Holdout run directory not found: {model_holdout_dir}")

    report: dict[str, Any] = {
        "model_slug": args.model_slug,
        "tasks": {},
    }

    for t_spec in holdout_tasks:
        tid = t_spec["id"]
        tdir = model_holdout_dir / tid
        if not tdir.exists():
            report["tasks"][tid] = {"passed": False, "error": "task_directory_missing"}
            continue

        # 1. Read raw pre-postprocessor files from orig/ (if present) or tdir
        orig_dir = tdir / "orig"
        files_map: dict[str, str] = {}
        for req_f in t_spec.get("required_files", []):
            src_p = (orig_dir / req_f) if (orig_dir / req_f).exists() else (tdir / req_f)
            if src_p.exists():
                files_map[req_f] = src_p.read_text(encoding="utf-8", errors="replace")

        val_res = vh.validate_holdout_submission(t_spec, files_map)

        # 2. Also run Stage A static auditor + packaging postprocessor + headless Chrome/Lighthouse for web tasks
        browser_res = None
        static_res = None
        if t_spec.get("category") != "typescript_coding" and (tdir / "index.html").exists():
            cc.apply_csp_postprocessor(str(tdir))
            if not args.skip_browser:
                proc_br = subprocess.run(
                    [
                        str(pp.NODE_EXE),
                        str(pp.SUITE_DIR / "browser_and_lh_suite.mjs"),
                        "--single-folder",
                        str(tdir),
                        "--http-nav",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                if proc_br.returncode == 0 and proc_br.stdout.strip():
                    try:
                        browser_res = json.loads(proc_br.stdout)
                    except Exception:
                        browser_res = {"parse_error": proc_br.stdout[:500]}

        report["tasks"][tid] = {
            "task_id": tid,
            "language": t_spec.get("language"),
            "category": t_spec.get("category"),
            "validator_result": val_res,
            "static_summary": static_res,
            "browser_lh": browser_res,
        }

    out_audit = model_holdout_dir / "holdout_audit.json"
    out_audit.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[HOLDOUT-AUDIT] Saved holdout audit to {out_audit}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wave 4 Full Suite (14) + Blind Holdout (6) Runner")
    parser.add_argument(
        "--mode",
        choices=("text-and-holdout", "render-zimage", "vision", "audit-holdout"),
        required=True,
    )
    parser.add_argument("--model-slug", default="smartllm-v2-k320-v1")
    parser.add_argument("--gguf", type=Path, default=DEFAULT_MODEL_V2)
    parser.add_argument("--mmproj", type=Path, default=DEFAULT_MMPROJ)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18089)
    parser.add_argument("--n-cpu-moe", type=int, default=42)
    parser.add_argument("--moe-cache-mib", type=int, default=2048)
    parser.add_argument("--moe-cache-cpu-share", type=float, default=0.00)
    parser.add_argument("--reasoning-budget", type=int, default=4000)
    parser.add_argument("--max-tokens", type=int, default=16384)
    parser.add_argument("--restart-every-n-tasks", type=int, default=4)
    parser.add_argument("--max-zimages-per-task", type=int, default=2)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--force-tasks", nargs="*", default=None)
    parser.add_argument("--skip-holdout", action="store_true")
    parser.add_argument("--skip-browser", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.mode == "text-and-holdout":
        return run_text_and_holdout_stage(args)
    if args.mode == "render-zimage":
        return run_render_zimage_stage(args)
    if args.mode == "vision":
        return run_vision_stage(args)
    if args.mode == "audit-holdout":
        return run_audit_holdout_stage(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
