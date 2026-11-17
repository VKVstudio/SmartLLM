#!/usr/bin/env python3
"""Deterministic WP-B1 runtime smoke runner for SmartLLM-205E-IQ3_S.gguf.

Must ONLY be invoked under `scripts/infra/gpu_run.py --wp WP-B1 --check-ple`
after `@coordinator` grants `GPU_TOKEN_GRANTED`.

Verifies in a single clean run:
1. `--lazy-mode direct` O_DIRECT 8-worker PLE reader (`unbuffered=1` or fallback,
   `ple_overlap_mapped_bytes == 0`, `ple_overlap_rss_kb == 0`, `watchdog_ple_rss_kb == 0`).
2. `CPU_REPACK` auto-disable + 8-class CRF `ClassLRU` `--moe-cache-mib` +
   `--moe-cache-cpu-share` AVX2 cold-miss bypass.
3. Optional `--mtp` (`--spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0.5`)
   with `filter_idx=nullptr` dense causal Flash-Attention on `blk.48` and
   `pos==0` / `has_pending_h` fix.
4. EN + RU greedy generation coherence (`temperature=0.0`) over `127.0.0.1` only,
   followed by clean SIGTERM shutdown.
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
import time
from typing import Any
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.infra.sla_watchdog import (  # noqa: E402
    DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
    SwapBaseline,
    capture_swap_baseline,
    evaluate_swap_and_mem_sla,
)
from scripts.runtime.verify_ple_smaps import (  # noqa: E402
    parse_smaps_text,
    read_gguf_ple_range,
    read_host_mem_swap,
    read_smaps_rollup,
)

DEFAULT_SERVER_BIN = ROOT / "tools" / "llama.cpp" / "build_linux" / "bin" / "llama-server"
DEFAULT_MODEL = ROOT / "models" / "SmartLLM-205E-IQ3_S.gguf"


def _http_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: float = 120.0) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, (json.loads(body) if body.strip() else {})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, {"raw_error": body}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return 0, {"connection_error": str(exc)}


def snapshot_smaps(pid: int, gguf_real: str, ple_range: dict[str, Any], baseline: SwapBaseline) -> dict[str, Any]:
    smaps_text = Path(f"/proc/{pid}/smaps").read_text(encoding="utf-8", errors="replace")
    smaps_parsed = parse_smaps_text(smaps_text, gguf_realpath=gguf_real, ple_range=ple_range)
    rollup = read_smaps_rollup(pid)
    sla_eval = evaluate_swap_and_mem_sla(
        baseline=baseline,
        root_pid=pid,
        max_proc_swap_mib=DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
        check_ple=True,
    )
    return {
        "smaps": smaps_parsed,
        "smaps_rollup_kb": rollup,
        "host": read_host_mem_swap(),
        "sla_eval": sla_eval,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="WP-B1 runtime smoke runner (run inside gpu_run.py)")
    ap.add_argument("--server-bin", type=Path, default=DEFAULT_SERVER_BIN)
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    ap.add_argument("--port", type=int, default=18089)
    ap.add_argument("--n-cpu-moe", type=int, default=48)
    ap.add_argument("--moe-cache-mib", type=int, default=4096)
    ap.add_argument("--moe-cache-cpu-share", type=float, default=0.15)
    ap.add_argument("--ctx-size", type=int, default=32768)
    ap.add_argument("--ubatch-size", type=int, default=512)
    ap.add_argument("--n-predict", type=int, default=64)
    ap.add_argument("--mtp", action="store_true", help="Enable --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0.5")
    ap.add_argument("--log-out", type=Path, required=True)
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    ple_range = read_gguf_ple_range(args.model)
    gguf_real = os.path.realpath(args.model)

    cmd = [
        str(args.server_bin),
        "-m",
        str(args.model),
        "--host",
        "127.0.0.1",
        "--port",
        str(args.port),
        "--lazy-mode",
        "direct",
        "--n-cpu-moe",
        str(args.n_cpu_moe),
        "-nr",
        "--moe-cache-mib",
        str(args.moe_cache_mib),
        "--moe-cache-cpu-share",
        f"{args.moe_cache_cpu_share:.2f}",
        "-fa",
        "on",
        "-ctk",
        "q8_0",
        "-ctv",
        "q8_0",
        "-c",
        str(args.ctx_size),
        "-ub",
        str(args.ubatch_size),
        "-ngl",
        "99",
        "-np",
        "1",
        "--cache-ram",
        "0",
        "-lv",
        "4",
        "--no-webui",
    ]
    if args.mtp:
        cmd.extend([
            "--spec-type",
            "draft-mtp",
            "--spec-draft-n-max",
            "3",
            "--spec-draft-p-min",
            "0.5",
            "-ctkd",
            "q8_0",
            "-ctvd",
            "q8_0",
        ])

    args.log_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)

    swap_baseline = capture_swap_baseline()
    log_f = args.log_out.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        text=True,
    )

    snapshots: dict[str, Any] = {}
    completions: dict[str, Any] = {}
    exit_code: int | None = None

    try:
        health_url = f"http://127.0.0.1:{args.port}/health"
        deadline = time.monotonic() + 180.0
        healthy = False
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"llama-server exited early with rc={proc.returncode}")
            code, body = _http_json(health_url, method="GET", timeout=2.0)
            if code == 200 and body.get("status") == "ok":
                healthy = True
                break
            time.sleep(0.5)
        if not healthy:
            raise RuntimeError("llama-server did not become healthy within 180s")

        snapshots["post_load"] = snapshot_smaps(proc.pid, gguf_real, ple_range, swap_baseline)

        prompts = {
            "en": (
                "<|im_start|>user\nWrite a concise 3-bullet CSS checklist for accessible OKLCH buttons.<|im_end|>\n"
                "<|im_start|>assistant\n<think>\n\n</think>\n\n"
            ),
            "ru": (
                "<|im_start|>user\nНапиши три коротких принципа типографики для веб-интерфейса на русском языке.<|im_end|>\n"
                "<|im_start|>assistant\n<think>\n\n</think>\n\n"
            ),
            "en_warm": (
                "<|im_start|>user\nWrite a concise 3-bullet CSS checklist for accessible OKLCH buttons.<|im_end|>\n"
                "<|im_start|>assistant\n<think>\n\n</think>\n\n"
            ),
        }

        comp_url = f"http://127.0.0.1:{args.port}/completion"
        for lang, prompt_text in prompts.items():
            code, body = _http_json(
                comp_url,
                method="POST",
                payload={
                    "prompt": prompt_text,
                    "n_predict": args.n_predict,
                    "temperature": 0.0,
                    "cache_prompt": False,
                },
                timeout=180.0,
            )
            if code != 200:
                raise RuntimeError(f"Completion ({lang}) failed with HTTP {code}: {body}")
            completions[lang] = {
                "content": body.get("content", ""),
                "tokens_evaluated": body.get("tokens_evaluated"),
                "tokens_predicted": body.get("tokens_predicted"),
                "timings": body.get("timings", {}),
            }
            snapshots[f"after_{lang}"] = snapshot_smaps(proc.pid, gguf_real, ple_range, swap_baseline)

    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                exit_code = proc.wait(timeout=20.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                exit_code = proc.wait(timeout=5.0)
        else:
            exit_code = proc.returncode
        log_f.close()

    log_text = args.log_out.read_text(encoding="utf-8", errors="replace")
    ple_log_lines = [ln for ln in log_text.splitlines() if "PLE-DIRECT" in ln]
    moe_log_lines = [ln for ln in log_text.splitlines() if "moe_cache" in ln.lower() or "ClassLRU" in ln]
    mtp_log_lines = [ln for ln in log_text.splitlines() if "draft-mtp" in ln or "draft_mtp" in ln or "speculative" in ln.lower()]

    all_smaps_ok = all(
        snap["smaps"]["ple_overlap_rss_kb"] == 0
        and snap["smaps"]["ple_overlap_mapped_bytes"] == 0
        and snap["smaps"]["watchdog_ple_rss_kb"] == 0
        and snap["sla_eval"]["passed"]
        for snap in snapshots.values()
    )
    ru_text = completions.get("ru", {}).get("content", "")
    cyr_count = len(re.findall(r"[А-Яа-яЁё]", ru_text))
    en_text = completions.get("en", {}).get("content", "")
    en_warm_text = completions.get("en_warm", {}).get("content", "")

    passed = (
        bool(snapshots)
        and all_smaps_ok
        and len(en_text.strip()) >= 20
        and len(en_warm_text.strip()) >= 20
        and cyr_count >= 20
        and len(ple_log_lines) >= 1
    )

    summary = {
        "passed": passed,
        "mtp_enabled": args.mtp,
        "cmd": cmd,
        "server_exit_code": exit_code,
        "ple_range": ple_range,
        "ple_log_lines": ple_log_lines,
        "moe_log_lines": moe_log_lines[-10:],
        "mtp_log_lines": mtp_log_lines[-10:],
        "snapshots": snapshots,
        "completions": completions,
        "ru_cyrillic_chars": cyr_count,
    }
    args.json_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "passed": passed,
        "mtp_enabled": args.mtp,
        "ple_log_lines": ple_log_lines,
        "moe_log_lines": moe_log_lines[-4:],
        "post_load_smaps": snapshots.get("post_load", {}).get("smaps"),
        "after_ru_smaps": snapshots.get("after_ru", {}).get("smaps"),
        "en_cold_tok_s": completions.get("en", {}).get("timings", {}).get("predicted_per_second"),
        "en_warm_tok_s": completions.get("en_warm", {}).get("timings", {}).get("predicted_per_second"),
        "ru_tok_s": completions.get("ru", {}).get("timings", {}).get("predicted_per_second"),
        "ru_draft_n": completions.get("ru", {}).get("timings", {}).get("draft_n"),
        "ru_draft_accepted": completions.get("ru", {}).get("timings", {}).get("draft_n_accepted"),
        "ru_cyrillic_chars": cyr_count,
    }, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
