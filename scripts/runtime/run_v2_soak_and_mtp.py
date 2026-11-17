#!/usr/bin/env python3
"""WP-B1 Wave 3 Step 3b: 5-Prompt MTP Gate & 20-Minute 32K Soak Runner.

Must ONLY be invoked under:
  scripts/infra/gpu_run.py --wp WP-B1 --check-ple --max-proc-swap-mib 128.0

Enforces all isolation and Zero-Swap rules (OPUS_MASTER_PLAN_V2 §0.3a, §1.D4):
- Binds strictly to 127.0.0.1:18089 (never touches port 8090).
- Never uses gguf.GGUFReader or numpy.memmap; reads PLE offset via plain open("rb").
- Evicts VFS file cache (POSIX_FADV_DONTNEED) on target GGUF before each server
  lifecycle and on exit.
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
    read_vram_used_gib,
)
from scripts.runtime.verify_ple_smaps import (  # noqa: E402
    parse_smaps_text,
    read_gguf_ple_range,
    read_host_mem_swap,
    read_smaps_rollup,
)

DEFAULT_SERVER_BIN = ROOT / "tools" / "llama.cpp" / "build_linux" / "bin" / "llama-server"
DEFAULT_MODEL = ROOT / "models" / "SmartLLM-v2-K320-V1.gguf"
FORBIDDEN_PORT = 8090


def chat_wrap(user_prompt: str) -> str:
    return (
        f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
        "<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )


WARMUP_PROMPT = chat_wrap(
    "Give two CSS rules for fluid responsive headings with clamp()."
)

MTP_GATE_PROMPTS: list[dict[str, str]] = [
    {
        "id": "en_1_oklch_css",
        "lang": "en",
        "prompt": chat_wrap(
            "Write a production CSS snippet for an accessible primary button using OKLCH colors, "
            ":focus-visible outline, hover state, and prefers-reduced-motion support. No Tailwind."
        ),
    },
    {
        "id": "en_2_ts_csp_headers",
        "lang": "en",
        "prompt": chat_wrap(
            "Write a TypeScript helper function buildSecurityHeaders(nonce: string) returning strict "
            "HTTP response headers (Content-Security-Policy with nonce, HSTS, X-Content-Type-Options, "
            "Referrer-Policy, Permissions-Policy) for a modern web app."
        ),
    },
    {
        "id": "en_3_jsonld_seo",
        "lang": "en",
        "prompt": chat_wrap(
            "Create a valid Schema.org SoftwareApplication JSON-LD script block and 4 technical SEO "
            "checklist items for a self-hosted design studio web application."
        ),
    },
    {
        "id": "ru_1_landing_copy",
        "lang": "ru",
        "prompt": chat_wrap(
            "Напиши сильный главный экран (заголовок H1, подзаголовок, три конкретных преимущества "
            "без штампов и текст кнопки CTA) для русскоязычного лендинга инженерной дизайн-студии."
        ),
    },
    {
        "id": "ru_2_ui_typography_audit",
        "lang": "ru",
        "prompt": chat_wrap(
            "Сформулируй пять строгих критериев аудита веб-типографики и визуальной иерархии для "
            "интерфейса аналитической панели на русском языке (размеры, интерлиньяж, контраст, сетка)."
        ),
    },
]


def _build_long_context_audit_prompt(target_words: int, lang: str, cycle: int) -> str:
    """Build deterministic multi-section web spec context to exercise 32K KV + DSA indexer."""
    sections: list[str] = []
    idx = 0
    cur_words = 0
    while cur_words < target_words:
        idx += 1
        hue = (idx * 37 + cycle * 13) % 360
        if lang == "en":
            block = (
                f"/* Component Spec #{idx} (cycle {cycle}) */\n"
                f".card-module-{idx} {{\n"
                f"  container-type: inline-size;\n"
                f"  display: grid;\n"
                f"  grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));\n"
                f"  gap: clamp(1rem, 2.5cqi, 2rem);\n"
                f"  background: oklch(0.97 0.015 {hue});\n"
                f"  color: oklch(0.21 0.02 {hue});\n"
                f"  border: 1px solid oklch(0.84 0.03 {hue});\n"
                f"  padding-block: clamp(1.25rem, 3cqi, 2.5rem);\n"
                f"}}\n"
                f"// Audit note {idx}: verify WCAG AA contrast >= 4.5, zero horizontal overflow at 320px, "
                f"semantic landmark hierarchy, and strict nonce-based CSP compliance.\n"
            )
        else:
            block = (
                f"/* Модуль дизайн-системы №{idx} (цикл {cycle}) */\n"
                f"Раздел спецификации {idx}: карточка продукта использует сетку CSS Grid, "
                f"контейнерные запросы inline-size, палитру oklch(0.96 0.02 {hue}) для светлого фона "
                f"и oklch(0.20 0.02 {hue}) для основного наборного текста. "
                f"Проверка доступности: контраст текста не ниже 4.5:1, видимый контур :focus-visible, "
                f"отсутствие горизонтальной прокрутки на мобильном экране 360px, корректная микроразметка.\n"
            )
        sections.append(block)
        cur_words += len(block.split())

    body = "\n".join(sections)
    if lang == "en":
        question = (
            f"\nBased on Component Spec #1 and Component Spec #{idx} above, summarize in 4 concise "
            f"bullet points the layout architecture, OKLCH token pattern, and accessibility invariants."
        )
    else:
        question = (
            f"\nОпираясь на Модуль №1 и Модуль №{idx} выше, кратко перечисли в 4 пунктах правила "
            f"сетки, цветовой схемы OKLCH и контроля доступности интерфейса."
        )
    return chat_wrap(body + question)


def evict_file_page_cache(path: Path) -> None:
    rp = os.path.realpath(path)
    if not os.path.isfile(rp):
        return
    fd = os.open(rp, os.O_RDONLY)
    try:
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    finally:
        os.close(fd)


def _http_json(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 300.0,
) -> tuple[int, dict[str, Any]]:
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


def take_telemetry_snapshot(
    pid: int,
    gguf_real: str,
    ple_range: dict[str, Any],
    baseline: SwapBaseline,
) -> dict[str, Any]:
    smaps_text = Path(f"/proc/{pid}/smaps").read_text(encoding="utf-8", errors="replace")
    smaps_parsed = parse_smaps_text(smaps_text, gguf_realpath=gguf_real, ple_range=ple_range)
    rollup = read_smaps_rollup(pid)
    sla = evaluate_swap_and_mem_sla(
        baseline=baseline,
        root_pid=pid,
        max_proc_swap_mib=DEFAULT_RUNTIME_MAX_PROC_SWAP_MIB,
        check_ple=True,
    )
    vram_gib = round(read_vram_used_gib(), 3)
    return {
        "ts_epoch": round(time.time(), 3),
        "vram_gib": vram_gib,
        "smaps": smaps_parsed,
        "smaps_rollup_rss_kb": rollup.get("Rss", 0),
        "smaps_rollup_anon_kb": rollup.get("Anonymous", 0),
        "smaps_rollup_swap_kb": rollup.get("Swap", 0),
        "host": read_host_mem_swap(),
        "sla_passed": bool(sla["passed"] and vram_gib <= 10.5),
        "sla_breach_reason": sla.get("breach_reason") or (f"vram_gib={vram_gib} > 10.5" if vram_gib > 10.5 else None),
        "zram_orig_delta_mib": round(float(sla.get("zram_orig_delta_mib", 0.0)), 3),
        "proc_swap_mib": round(float(sla.get("proc_swap_mib", 0.0)), 3),
        "disk_swap_used_kb": int(sla.get("disk_swap_used_kb", 0)),
        "disk_swap_write_sectors_delta": int(sla.get("disk_swap_write_sectors_delta", 0)),
    }


def build_server_cmd(
    *,
    server_bin: Path,
    model: Path,
    port: int,
    ctx_size: int,
    n_cpu_moe: int,
    moe_cache_mib: int,
    moe_cache_cpu_share: float,
    enable_mtp: bool,
) -> list[str]:
    if port == FORBIDDEN_PORT:
        raise ValueError(f"Port {FORBIDDEN_PORT} is strictly forbidden (reserved for live SmartLLM Studio)")
    cmd = [
        str(server_bin),
        "-m",
        str(model),
        "--host",
        "127.0.0.1",
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
        str(ctx_size),
        "-ub",
        "512",
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
    if enable_mtp:
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
    else:
        cmd.extend(["-ot", r"blk\.48\..*=CPU"])
    return cmd


def parse_server_log_metrics(log_text: str) -> dict[str, Any]:
    ple_lines = [ln for ln in log_text.splitlines() if "PLE-DIRECT" in ln]
    moe_lines = [ln for ln in log_text.splitlines() if "llama_moe_cache:" in ln or "MoE cache size" in ln or "slots +" in ln]
    mtp_lines = [ln for ln in log_text.splitlines() if "draft-mtp" in ln]

    moe_small: dict[str, Any] = {}
    for ln in moe_lines:
        m = re.search(
            r"ubatch <= 8:\s*hits = (\d+),\s*misses = (\d+)\s*\(cpu_bypass = (\d+)\),\s*hit rate = ([0-9.]+)%,\s*uploaded = ([0-9.]+) MiB",
            ln,
        )
        if m:
            moe_small = {
                "hits": int(m.group(1)),
                "misses": int(m.group(2)),
                "cpu_bypass": int(m.group(3)),
                "hit_rate_pct": float(m.group(4)),
                "uploaded_mib": float(m.group(5)),
            }
    return {
        "ple_log_lines": ple_lines,
        "moe_log_lines": moe_lines[-8:],
        "mtp_log_lines": mtp_lines[-8:],
        "moe_ubatch_le_8": moe_small,
    }


def wait_server_healthy(proc: subprocess.Popen[str], port: int, timeout_sec: float = 180.0) -> None:
    health_url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited early with rc={proc.returncode}")
        code, body = _http_json(health_url, method="GET", timeout=2.0)
        if code == 200 and body.get("status") == "ok":
            return
        time.sleep(0.5)
    raise RuntimeError(f"llama-server did not become healthy within {timeout_sec}s")


def stop_server_cleanly(proc: subprocess.Popen[str]) -> int:
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            rc = proc.wait(timeout=20.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = proc.wait(timeout=5.0)
    else:
        rc = int(proc.returncode or 0)
    time.sleep(1.5)
    return rc


def run_prompt_suite(
    *,
    label: str,
    server_bin: Path,
    model: Path,
    port: int,
    ctx_size: int,
    n_cpu_moe: int,
    moe_cache_mib: int,
    moe_cache_cpu_share: float,
    enable_mtp: bool,
    n_predict: int,
    log_path: Path,
    ple_range: dict[str, Any],
    gguf_real: str,
    baseline: SwapBaseline,
) -> dict[str, Any]:
    evict_file_page_cache(model)
    cmd = build_server_cmd(
        server_bin=server_bin,
        model=model,
        port=port,
        ctx_size=ctx_size,
        n_cpu_moe=n_cpu_moe,
        moe_cache_mib=moe_cache_mib,
        moe_cache_cpu_share=moe_cache_cpu_share,
        enable_mtp=enable_mtp,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_f = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, text=True)

    snapshots: list[dict[str, Any]] = []
    results: dict[str, Any] = {}
    warmup_res: dict[str, Any] = {}
    rc = -1

    try:
        wait_server_healthy(proc, port=port, timeout_sec=180.0)
        snapshots.append(take_telemetry_snapshot(proc.pid, gguf_real, ple_range, baseline))

        comp_url = f"http://127.0.0.1:{port}/completion"
        w_code, w_body = _http_json(
            comp_url,
            method="POST",
            payload={
                "prompt": WARMUP_PROMPT,
                "n_predict": 64,
                "temperature": 0.0,
                "seed": 42,
                "cache_prompt": False,
            },
            timeout=240.0,
        )
        if w_code != 200:
            raise RuntimeError(f"[{label}] warmup HTTP {w_code}: {w_body}")
        warmup_res = {
            "predicted_per_second": w_body.get("timings", {}).get("predicted_per_second"),
            "draft_n": w_body.get("timings", {}).get("draft_n", 0),
            "draft_n_accepted": w_body.get("timings", {}).get("draft_n_accepted", 0),
        }

        for item in MTP_GATE_PROMPTS:
            pid_key = item["id"]
            code, body = _http_json(
                comp_url,
                method="POST",
                payload={
                    "prompt": item["prompt"],
                    "n_predict": n_predict,
                    "temperature": 0.0,
                    "seed": 42,
                    "cache_prompt": False,
                },
                timeout=300.0,
            )
            if code != 200:
                raise RuntimeError(f"[{label}] prompt {pid_key} failed HTTP {code}: {body}")
            t = body.get("timings", {})
            results[pid_key] = {
                "lang": item["lang"],
                "content": body.get("content", ""),
                "tokens_evaluated": body.get("tokens_evaluated"),
                "tokens_predicted": body.get("tokens_predicted"),
                "prompt_per_second": t.get("prompt_per_second"),
                "predicted_per_second": t.get("predicted_per_second"),
                "predicted_ms": t.get("predicted_ms"),
                "draft_n": int(t.get("draft_n", 0) or 0),
                "draft_n_accepted": int(t.get("draft_n_accepted", 0) or 0),
            }
            snapshots.append(take_telemetry_snapshot(proc.pid, gguf_real, ple_range, baseline))
    finally:
        rc = stop_server_cleanly(proc)
        log_f.close()
        evict_file_page_cache(model)

    log_metrics = parse_server_log_metrics(log_path.read_text(encoding="utf-8", errors="replace"))
    total_pred_tokens = sum(int(r["tokens_predicted"] or 0) for r in results.values())
    total_pred_ms = sum(float(r["predicted_ms"] or 0.0) for r in results.values())
    agg_tok_s = (1000.0 * total_pred_tokens / total_pred_ms) if total_pred_ms > 0 else 0.0
    mean_tok_s = (
        sum(float(r["predicted_per_second"] or 0.0) for r in results.values()) / len(results)
        if results else 0.0
    )
    total_draft = sum(int(r["draft_n"]) for r in results.values())
    total_acc = sum(int(r["draft_n_accepted"]) for r in results.values())
    acc_rate = (total_acc / total_draft) if total_draft > 0 else 0.0

    max_vram = max((s["vram_gib"] for s in snapshots), default=0.0)
    min_mem = min((s["host"]["mem_available_gib"] for s in snapshots), default=0.0)
    max_ple_rss = max(
        (max(s["smaps"]["ple_overlap_rss_kb"], s["smaps"]["watchdog_ple_rss_kb"]) for s in snapshots),
        default=0,
    )
    max_ple_mapped = max((s["smaps"]["ple_overlap_mapped_bytes"] for s in snapshots), default=0)
    max_zram_delta = max((s["zram_orig_delta_mib"] for s in snapshots), default=0.0)
    max_proc_swap = max((s["proc_swap_mib"] for s in snapshots), default=0.0)
    max_disk_swap = max((s["disk_swap_used_kb"] for s in snapshots), default=0)
    all_sla_ok = all(s["sla_passed"] for s in snapshots) and max_ple_rss == 0 and max_ple_mapped == 0

    return {
        "label": label,
        "enable_mtp": enable_mtp,
        "n_cpu_moe": n_cpu_moe,
        "moe_cache_mib": moe_cache_mib,
        "moe_cache_cpu_share": moe_cache_cpu_share,
        "cmd": cmd,
        "server_exit_code": rc,
        "aggregate_decode_tok_s": round(agg_tok_s, 3),
        "mean_prompt_decode_tok_s": round(mean_tok_s, 3),
        "total_draft_n": total_draft,
        "total_draft_accepted": total_acc,
        "draft_acceptance_rate": round(acc_rate, 4),
        "max_vram_gib": round(max_vram, 3),
        "min_mem_avail_gib": round(min_mem, 3),
        "max_ple_rss_kb": max_ple_rss,
        "max_ple_mapped_bytes": max_ple_mapped,
        "max_zram_orig_delta_mib": round(max_zram_delta, 3),
        "max_proc_swap_mib": round(max_proc_swap, 3),
        "max_disk_swap_used_kb": max_disk_swap,
        "sla_ok": all_sla_ok,
        "warmup": warmup_res,
        "log_metrics": log_metrics,
        "snapshots": snapshots,
        "prompts": results,
    }


def run_mtp_gate_mode(args: argparse.Namespace) -> int:
    ple_range = read_gguf_ple_range(args.model)
    gguf_real = os.path.realpath(args.model)
    baseline = capture_swap_baseline()
    out_dir = args.out_json.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Deterministic parity runs (--moe-cache-cpu-share 0.0 per wp_b1.md §4.2)
    no_mtp_det = run_prompt_suite(
        label="no_mtp_cpu_share_0.0",
        server_bin=args.server_bin,
        model=args.model,
        port=args.port,
        ctx_size=args.ctx_size,
        n_cpu_moe=args.n_cpu_moe,
        moe_cache_mib=args.moe_cache_mib,
        moe_cache_cpu_share=0.0,
        enable_mtp=False,
        n_predict=args.n_predict,
        log_path=out_dir / "mtp_gate_nomtp_det_server.log",
        ple_range=ple_range,
        gguf_real=gguf_real,
        baseline=baseline,
    )
    mtp_det = run_prompt_suite(
        label="mtp_cpu_share_0.0",
        server_bin=args.server_bin,
        model=args.model,
        port=args.port,
        ctx_size=args.ctx_size,
        n_cpu_moe=args.n_cpu_moe,
        moe_cache_mib=args.moe_cache_mib,
        moe_cache_cpu_share=0.0,
        enable_mtp=True,
        n_predict=args.n_predict,
        log_path=out_dir / "mtp_gate_mtp_det_server.log",
        ple_range=ple_range,
        gguf_real=gguf_real,
        baseline=baseline,
    )

    # 2. Practical cpu_share=0.15 throughput comparison
    no_mtp_practical = run_prompt_suite(
        label="no_mtp_cpu_share_0.15",
        server_bin=args.server_bin,
        model=args.model,
        port=args.port,
        ctx_size=args.ctx_size,
        n_cpu_moe=args.n_cpu_moe,
        moe_cache_mib=args.moe_cache_mib,
        moe_cache_cpu_share=0.15,
        enable_mtp=False,
        n_predict=args.n_predict,
        log_path=out_dir / "mtp_gate_nomtp_cpushare_server.log",
        ple_range=ple_range,
        gguf_real=gguf_real,
        baseline=baseline,
    )
    mtp_practical = run_prompt_suite(
        label="mtp_cpu_share_0.15",
        server_bin=args.server_bin,
        model=args.model,
        port=args.port,
        ctx_size=args.ctx_size,
        n_cpu_moe=args.n_cpu_moe,
        moe_cache_mib=args.moe_cache_mib,
        moe_cache_cpu_share=0.15,
        enable_mtp=True,
        n_predict=args.n_predict,
        log_path=out_dir / "mtp_gate_mtp_cpushare_server.log",
        ple_range=ple_range,
        gguf_real=gguf_real,
        baseline=baseline,
    )

    prompt_parity: dict[str, Any] = {}
    exact_matches = 0
    for item in MTP_GATE_PROMPTS:
        pid_key = item["id"]
        c_no = no_mtp_det["prompts"][pid_key]["content"]
        c_mtp = mtp_det["prompts"][pid_key]["content"]
        is_eq = c_no == c_mtp
        if is_eq:
            exact_matches += 1
        first_diff = None
        if not is_eq:
            min_len = min(len(c_no), len(c_mtp))
            first_diff = next((i for i in range(min_len) if c_no[i] != c_mtp[i]), min_len)
        prompt_parity[pid_key] = {
            "byte_identical": is_eq,
            "first_diff_char_idx": first_diff,
            "no_mtp_tok_s_det": no_mtp_det["prompts"][pid_key]["predicted_per_second"],
            "mtp_tok_s_det": mtp_det["prompts"][pid_key]["predicted_per_second"],
            "no_mtp_tok_s_practical": no_mtp_practical["prompts"][pid_key]["predicted_per_second"],
            "mtp_tok_s_practical": mtp_practical["prompts"][pid_key]["predicted_per_second"],
            "mtp_draft_n": mtp_practical["prompts"][pid_key]["draft_n"],
            "mtp_draft_accepted": mtp_practical["prompts"][pid_key]["draft_n_accepted"],
        }

    speedup_det_pct = (
        100.0 * (mtp_det["aggregate_decode_tok_s"] - no_mtp_det["aggregate_decode_tok_s"])
        / max(1e-9, no_mtp_det["aggregate_decode_tok_s"])
    )
    speedup_practical_pct = (
        100.0 * (mtp_practical["aggregate_decode_tok_s"] - no_mtp_practical["aggregate_decode_tok_s"])
        / max(1e-9, no_mtp_practical["aggregate_decode_tok_s"])
    )
    acc_rate_det = mtp_det["draft_acceptance_rate"]
    acc_rate_practical = mtp_practical["draft_acceptance_rate"]

    gate_1_acceptance = acc_rate_practical >= 0.50 and acc_rate_det >= 0.50
    gate_2_speedup = speedup_practical_pct >= 15.0
    gate_3_byte_identical = exact_matches == len(MTP_GATE_PROMPTS)
    gate_4_sla = all(
        r["sla_ok"]
        and r["max_vram_gib"] <= 10.5
        and r["min_mem_avail_gib"] >= 3.0
        and r["max_ple_rss_kb"] == 0
        and r["max_disk_swap_used_kb"] == 0
        and r["max_zram_orig_delta_mib"] <= 512.0
        and r["max_proc_swap_mib"] <= 128.0
        for r in (no_mtp_det, mtp_det, no_mtp_practical, mtp_practical)
    )

    all_4_mtp_gates_passed = gate_1_acceptance and gate_2_speedup and gate_3_byte_identical and gate_4_sla
    locked_soak_config = (
        {
            "enable_mtp": True,
            "n_cpu_moe": args.n_cpu_moe,
            "moe_cache_mib": args.moe_cache_mib,
            "moe_cache_cpu_share": 0.15,
            "reason": "All 4 OPUS §1.D4 MTP gates passed; keeping MTP enabled on GPU.",
        }
        if all_4_mtp_gates_passed
        else {
            "enable_mtp": False,
            "n_cpu_moe": args.n_cpu_moe,
            "moe_cache_mib": args.fallback_moe_cache_mib,
            "moe_cache_cpu_share": 0.15,
            "reason": (
                "One or more OPUS §1.D4 MTP gates failed "
                f"(acc={gate_1_acceptance}, speedup={gate_2_speedup}, "
                f"byte_identical={gate_3_byte_identical} [{exact_matches}/5], sla={gate_4_sla}); "
                f"dropping blk.48 to CPU and shifting budget to --moe-cache-mib {args.fallback_moe_cache_mib}."
            ),
        }
    )

    summary = {
        "model": str(args.model),
        "port": args.port,
        "ctx_size": args.ctx_size,
        "n_predict": args.n_predict,
        "gates": {
            "gate_1_acceptance_ge_50pct": gate_1_acceptance,
            "gate_2_net_decode_speedup_ge_15pct": gate_2_speedup,
            "gate_3_greedy_byte_identical_5_of_5": gate_3_byte_identical,
            "gate_4_runtime_sla": gate_4_sla,
            "all_4_passed": all_4_mtp_gates_passed,
        },
        "metrics": {
            "exact_greedy_matches": f"{exact_matches}/{len(MTP_GATE_PROMPTS)}",
            "acceptance_rate_det": acc_rate_det,
            "acceptance_rate_practical": acc_rate_practical,
            "no_mtp_det_tok_s": no_mtp_det["aggregate_decode_tok_s"],
            "mtp_det_tok_s": mtp_det["aggregate_decode_tok_s"],
            "speedup_det_pct": round(speedup_det_pct, 2),
            "no_mtp_practical_tok_s": no_mtp_practical["aggregate_decode_tok_s"],
            "mtp_practical_tok_s": mtp_practical["aggregate_decode_tok_s"],
            "speedup_practical_pct": round(speedup_practical_pct, 2),
            "peak_vram_gib": max(
                no_mtp_det["max_vram_gib"],
                mtp_det["max_vram_gib"],
                no_mtp_practical["max_vram_gib"],
                mtp_practical["max_vram_gib"],
            ),
            "min_mem_avail_gib": min(
                no_mtp_det["min_mem_avail_gib"],
                mtp_det["min_mem_avail_gib"],
                no_mtp_practical["min_mem_avail_gib"],
                mtp_practical["min_mem_avail_gib"],
            ),
        },
        "locked_soak_config": locked_soak_config,
        "prompt_parity": prompt_parity,
        "runs": {
            "no_mtp_det": no_mtp_det,
            "mtp_det": mtp_det,
            "no_mtp_practical": no_mtp_practical,
            "mtp_practical": mtp_practical,
        },
    }
    args.out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "gate_4_runtime_sla": gate_4_sla,
                "gates": summary["gates"],
                "metrics": summary["metrics"],
                "locked_soak_config": locked_soak_config,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if gate_4_sla else 1


def run_soak_mode(args: argparse.Namespace) -> int:
    ple_range = read_gguf_ple_range(args.model)
    gguf_real = os.path.realpath(args.model)
    baseline = capture_swap_baseline()

    enable_mtp = args.enable_mtp
    n_cpu_moe = args.n_cpu_moe
    moe_cache_mib = args.moe_cache_mib
    cpu_share = args.moe_cache_cpu_share

    if args.from_gate_json and args.from_gate_json.exists():
        gate_data = json.loads(args.from_gate_json.read_text(encoding="utf-8"))
        locked = gate_data.get("locked_soak_config", {})
        enable_mtp = bool(locked.get("enable_mtp", enable_mtp))
        n_cpu_moe = int(locked.get("n_cpu_moe", n_cpu_moe))
        moe_cache_mib = int(locked.get("moe_cache_mib", moe_cache_mib))
        cpu_share = float(locked.get("moe_cache_cpu_share", cpu_share))

    evict_file_page_cache(args.model)
    cmd = build_server_cmd(
        server_bin=args.server_bin,
        model=args.model,
        port=args.port,
        ctx_size=args.ctx_size,
        n_cpu_moe=n_cpu_moe,
        moe_cache_mib=moe_cache_mib,
        moe_cache_cpu_share=cpu_share,
        enable_mtp=enable_mtp,
    )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.log_out or (args.out_json.parent / "soak_20m_server.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_f = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, text=True)

    snapshots: list[dict[str, Any]] = []
    iterations: list[dict[str, Any]] = []
    rc = -1
    t_soak_start = 0.0
    t_soak_end = 0.0

    try:
        wait_server_healthy(proc, port=args.port, timeout_sec=180.0)
        t_soak_start = time.monotonic()
        snapshots.append(take_telemetry_snapshot(proc.pid, gguf_real, ple_range, baseline))

        comp_url = f"http://127.0.0.1:{args.port}/completion"
        step_idx = 0
        long_word_targets = [1200, 2400, 4200, 6500]  # ~2.3K..12.5K BPE tokens (exercises >2048 DSA top-k indexer & 32K KV)

        while (time.monotonic() - t_soak_start) < args.duration_sec:
            if step_idx % 6 == 5:
                lw = long_word_targets[(step_idx // 6) % len(long_word_targets)]
                lang = "en" if (step_idx // 6) % 2 == 0 else "ru"
                prompt_text = _build_long_context_audit_prompt(lw, lang=lang, cycle=step_idx)
                prompt_id = f"long_ctx_{lang}_{lw}w_step{step_idx}"
                n_pred = 192
            else:
                base_item = MTP_GATE_PROMPTS[step_idx % len(MTP_GATE_PROMPTS)]
                prompt_text = base_item["prompt"]
                lang = base_item["lang"]
                prompt_id = f"{base_item['id']}_step{step_idx}"
                n_pred = 256

            code, body = _http_json(
                comp_url,
                method="POST",
                payload={
                    "prompt": prompt_text,
                    "n_predict": n_pred,
                    "temperature": 0.0,
                    "seed": 42,
                    "cache_prompt": False,
                },
                timeout=360.0,
            )
            if code != 200:
                raise RuntimeError(f"[soak step {step_idx}] HTTP {code}: {body}")

            t = body.get("timings", {})
            content = body.get("content", "")
            snap = take_telemetry_snapshot(proc.pid, gguf_real, ple_range, baseline)
            snapshots.append(snap)
            if not snap["sla_passed"]:
                raise RuntimeError(f"[soak step {step_idx}] SLA breach detected: {snap['sla_breach_reason']}")

            iterations.append({
                "step": step_idx,
                "elapsed_soak_sec": round(time.monotonic() - t_soak_start, 2),
                "prompt_id": prompt_id,
                "lang": lang,
                "tokens_evaluated": body.get("tokens_evaluated"),
                "tokens_predicted": body.get("tokens_predicted"),
                "prompt_per_second": round(float(t.get("prompt_per_second") or 0.0), 3),
                "predicted_per_second": round(float(t.get("predicted_per_second") or 0.0), 3),
                "predicted_ms": round(float(t.get("predicted_ms") or 0.0), 2),
                "draft_n": int(t.get("draft_n", 0) or 0),
                "draft_n_accepted": int(t.get("draft_n_accepted", 0) or 0),
                "vram_gib": snap["vram_gib"],
                "mem_avail_gib": snap["host"]["mem_available_gib"],
                "ple_rss_kb": snap["smaps"]["ple_overlap_rss_kb"],
                "zram_delta_mib": snap["zram_orig_delta_mib"],
                "proc_swap_mib": snap["proc_swap_mib"],
                "output_preview": content[:140],
            })
            step_idx += 1

        t_soak_end = time.monotonic()
    finally:
        if t_soak_end == 0.0 and t_soak_start > 0.0:
            t_soak_end = time.monotonic()
        rc = stop_server_cleanly(proc)
        log_f.close()
        evict_file_page_cache(args.model)

    soak_elapsed = t_soak_end - t_soak_start if t_soak_start > 0.0 else 0.0
    log_metrics = parse_server_log_metrics(log_path.read_text(encoding="utf-8", errors="replace"))

    warm_iters = iterations[1:] if len(iterations) > 1 else iterations
    total_pred_tok = sum(int(it["tokens_predicted"] or 0) for it in warm_iters)
    total_pred_ms = sum(float(it["predicted_ms"] or 0.0) for it in warm_iters)
    steady_decode_tok_s = (1000.0 * total_pred_tok / total_pred_ms) if total_pred_ms > 0 else 0.0
    mean_decode_tok_s = (
        sum(float(it["predicted_per_second"]) for it in warm_iters) / len(warm_iters)
        if warm_iters else 0.0
    )
    max_ctx_evaluated = max((int(it["tokens_evaluated"] or 0) + int(it["tokens_predicted"] or 0) for it in iterations), default=0)
    total_draft = sum(int(it["draft_n"]) for it in iterations)
    total_acc = sum(int(it["draft_n_accepted"]) for it in iterations)
    acc_rate = (total_acc / total_draft) if total_draft > 0 else 0.0

    max_vram = max((s["vram_gib"] for s in snapshots), default=0.0)
    min_mem = min((s["host"]["mem_available_gib"] for s in snapshots), default=0.0)
    max_ple_rss = max(
        (max(s["smaps"]["ple_overlap_rss_kb"], s["smaps"]["watchdog_ple_rss_kb"]) for s in snapshots),
        default=0,
    )
    max_ple_mapped = max((s["smaps"]["ple_overlap_mapped_bytes"] for s in snapshots), default=0)
    max_zram_delta = max((s["zram_orig_delta_mib"] for s in snapshots), default=0.0)
    max_proc_swap = max((s["proc_swap_mib"] for s in snapshots), default=0.0)
    max_disk_swap = max((s["disk_swap_used_kb"] for s in snapshots), default=0)
    max_rss_kb = max((s["smaps_rollup_rss_kb"] for s in snapshots), default=0)

    passed = (
        soak_elapsed >= 1205.0
        and steady_decode_tok_s >= 15.0
        and max_ple_rss == 0
        and max_ple_mapped == 0
        and max_disk_swap == 0
        and max_zram_delta <= 512.0
        and max_proc_swap <= 128.0
        and min_mem >= 3.0
        and max_vram <= 10.5
        and all(s["sla_passed"] for s in snapshots)
    )

    summary = {
        "passed": passed,
        "model": str(args.model),
        "port": args.port,
        "ctx_size": args.ctx_size,
        "enable_mtp": enable_mtp,
        "n_cpu_moe": n_cpu_moe,
        "moe_cache_mib": moe_cache_mib,
        "moe_cache_cpu_share": cpu_share,
        "cmd": cmd,
        "server_exit_code": rc,
        "soak_elapsed_sec": round(soak_elapsed, 3),
        "completed_requests": len(iterations),
        "total_tokens_evaluated": sum(int(it["tokens_evaluated"] or 0) for it in iterations),
        "total_tokens_predicted": sum(int(it["tokens_predicted"] or 0) for it in iterations),
        "max_seq_tokens_exercised": max_ctx_evaluated,
        "steady_decode_tok_s": round(steady_decode_tok_s, 3),
        "mean_decode_tok_s": round(mean_decode_tok_s, 3),
        "total_draft_n": total_draft,
        "total_draft_accepted": total_acc,
        "draft_acceptance_rate": round(acc_rate, 4),
        "sla_telemetry": {
            "max_vram_gib": round(max_vram, 3),
            "min_mem_avail_gib": round(min_mem, 3),
            "max_ple_rss_kb": max_ple_rss,
            "max_ple_overlap_mapped_bytes": max_ple_mapped,
            "max_proc_rss_kb": max_rss_kb,
            "max_zram_orig_delta_mib": round(max_zram_delta, 3),
            "max_proc_swap_mib": round(max_proc_swap, 3),
            "max_disk_swap_used_kb": max_disk_swap,
        },
        "log_metrics": log_metrics,
        "iterations": iterations,
    }
    args.out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": passed,
                "enable_mtp": enable_mtp,
                "soak_elapsed_sec": summary["soak_elapsed_sec"],
                "completed_requests": summary["completed_requests"],
                "max_seq_tokens_exercised": max_ctx_evaluated,
                "steady_decode_tok_s": summary["steady_decode_tok_s"],
                "draft_acceptance_rate": summary["draft_acceptance_rate"],
                "sla_telemetry": summary["sla_telemetry"],
                "moe_ubatch_le_8": log_metrics.get("moe_ubatch_le_8"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="WP-B1 Wave 3 MTP Gate + 20-min 32K Soak Runner")
    ap.add_argument("--mode", choices=["mtp-gate", "soak"], required=True)
    ap.add_argument("--server-bin", type=Path, default=DEFAULT_SERVER_BIN)
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    ap.add_argument("--port", type=int, default=18089)
    ap.add_argument("--ctx-size", type=int, default=32768)
    ap.add_argument("--n-cpu-moe", type=int, default=42)
    ap.add_argument("--moe-cache-mib", type=int, default=1472)
    ap.add_argument("--fallback-moe-cache-mib", type=int, default=2048)
    ap.add_argument("--moe-cache-cpu-share", type=float, default=0.15)
    ap.add_argument("--enable-mtp", action="store_true")
    ap.add_argument("--n-predict", type=int, default=256)
    ap.add_argument("--duration-sec", type=float, default=1215.0)
    ap.add_argument("--from-gate-json", type=Path)
    ap.add_argument("--log-out", type=Path)
    ap.add_argument("--out-json", type=Path, required=True)
    args = ap.parse_args()

    if args.port == FORBIDDEN_PORT:
        ap.error(f"Port {FORBIDDEN_PORT} is strictly forbidden (live SmartLLM Studio)")

    if args.mode == "mtp-gate":
        return run_mtp_gate_mode(args)
    return run_soak_mode(args)


if __name__ == "__main__":
    sys.exit(main())
