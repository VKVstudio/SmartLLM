#!/usr/bin/env python3
"""Autonomous offline Step 8 evaluator for SmartLLM (`IQ3_S` -> `IQ3_XXS`).

Runs sequentially on the local RTX 4080 via mainline `llama-server.exe` (`127.0.0.1:8080`):
1. `smartllm-205e-iq3-s` (`SmartLLM-205E-IQ3_S.gguf` + `mmproj-BF16`) -> `t1..t12`
2. `smartllm-205e-iq3-xxs` (`SmartLLM-205E-IQ3_XXS.gguf` + `mmproj-BF16`) -> `t1..t12`

Zero external network requests. Strictly one model in VRAM at a time with `0 MiB` cleanup
between runs and NO auto-retry if a GPU run fails. Runs incremental `audit_suite.py`
(CSP/OKLCH/JSON-LD/tsc+DAG tests) immediately after each completed task so saved sites open
with valid CSS & JS right away, and after each model exits VRAM runs `browser_and_lh_suite.mjs`
(Playwright screenshots + Lighthouse), updating `live_status.md`, `gallery.html`, and
`auto_benchmark_report.md` continuously.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_ROOT_CAND = _THIS_DIR.parent
if str(_ROOT_CAND) not in sys.path:
    sys.path.insert(0, str(_ROOT_CAND))

from scripts.platform_paths import (  # noqa: E402
    NODE_EXE,
    PYTHON_EXE,
    RAW_STEP8_DIR as RAW_OUT_DIR,
    RESULTS_DIR,
    ROOT,
    RUNS_DIR,
    SCRIPTS_DIR,
    SUITE_DIR,
)

AUDIT_PY = SUITE_DIR / "audit_suite.py"
BROWSER_LH_MJS = SUITE_DIR / "browser_and_lh_suite.mjs"
LIVE_STATUS_MD = RESULTS_DIR / "live_status.md"
GALLERY_HTML = RESULTS_DIR / "gallery.html"
REPORT_MD = RESULTS_DIR / "auto_benchmark_report.md"
LOG_PATH = RAW_OUT_DIR / "autonomous_eval.log"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(SUITE_DIR) not in sys.path:
    sys.path.insert(0, str(SUITE_DIR))

import run_suite  # noqa: E402
import step7_smoke_antiswap as s7  # noqa: E402

MODEL_QUEUE: list[tuple[str, Path]] = [
    ("smartllm-205e-iq3-s", s7.IQ3_S_PATH),
    ("smartllm-205e-iq3-xxs", s7.IQ3_XXS_PATH),
]
SKIP_TASKS_BY_SLUG: dict[str, set[str]] = {}

REASONING_BUDGET = 4000
MAX_TOKENS = 28000
TEMPERATURE = run_suite.DEFAULT_TEMPERATURE
TOP_K = run_suite.DEFAULT_TOP_K
TOP_P = run_suite.DEFAULT_TOP_P
MIN_P = run_suite.DEFAULT_MIN_P
DRY_MULTIPLIER = run_suite.DEFAULT_DRY_MULTIPLIER
DRY_BASE = run_suite.DEFAULT_DRY_BASE
DRY_ALLOWED_LENGTH = run_suite.DEFAULT_DRY_ALLOWED_LENGTH
DRY_PENALTY_LAST_N = run_suite.DEFAULT_DRY_PENALTY_LAST_N
DRY_SEQUENCE_BREAKERS = run_suite.DEFAULT_DRY_SEQUENCE_BREAKERS
REPEAT_LAST_N = run_suite.DEFAULT_REPEAT_LAST_N
REPEAT_PENALTY = run_suite.DEFAULT_REPEAT_PENALTY
FREQUENCY_PENALTY = run_suite.DEFAULT_FREQUENCY_PENALTY
PRESENCE_PENALTY = run_suite.DEFAULT_PRESENCE_PENALTY
LOGIT_BIAS_TOKENS = run_suite.DEFAULT_LOGIT_BIAS_TOKENS
EOS_TOKEN_ID = run_suite.DEFAULT_EOS_TOKEN_ID
EOS_LOGIT_BIAS = run_suite.DEFAULT_EOS_LOGIT_BIAS

# Hard SLA Watchdog invariants (Stage A CODE-04 fix: 3.0 GiB MemAvailable floor,
# pswpout_delta == 0, VRAM <= 10.5 GiB, PLE Rss == 0 kB; NO reclaimable RAM exemption).
WATCHDOG_MIN_AVAIL_MIB = 3072.0
WATCHDOG_CRIT_AVAIL_MIB = 2048.0
WATCHDOG_MAX_VRAM_MIB = 10752.0
WATCHDOG_MAX_PLE_RSS_KB = 0
WATCHDOG_MAX_CPU_PRIV_WS_GIB = 4.0
WATCHDOG_MAX_PAGEFILE_DELTA_PCT = 0.0


def evaluate_watchdog_sample(s: dict[str, Any], pf_start: float | None = None) -> tuple[bool, bool, float]:
    """Evaluate a TelemetryRecorder sample against hard Zero-Swap & SLA invariants (CODE-04 fix)."""
    avail_mib = s.get("avail_phys_mib")
    cpu_priv_ws = s.get("cpu_private_ws_gib")
    pf = s.get("pagefile_usage_pct")
    pf_delta = (float(pf) - pf_start) if (pf is not None and pf_start is not None) else 0.0
    pswpout_delta = int(s.get("pswpout_delta") or 0)
    gpu_used_mib = s.get("gpu_used_mib")
    ple_rss_kb = int(s.get("ple_rss_kb") or 0)

    avail_bad = avail_mib is not None and float(avail_mib) < WATCHDOG_MIN_AVAIL_MIB
    crit_avail_bad = avail_mib is not None and float(avail_mib) < WATCHDOG_CRIT_AVAIL_MIB
    pswpout_bad = pswpout_delta > 0
    vram_bad = gpu_used_mib is not None and float(gpu_used_mib) > WATCHDOG_MAX_VRAM_MIB
    ple_bad = ple_rss_kb > WATCHDOG_MAX_PLE_RSS_KB
    priv_ws_bad = cpu_priv_ws is not None and float(cpu_priv_ws) > WATCHDOG_MAX_CPU_PRIV_WS_GIB
    pf_bad = (pf is not None and pf_start is not None) and pf_delta > WATCHDOG_MAX_PAGEFILE_DELTA_PCT
    any_breach = avail_bad or pswpout_bad or vram_bad or ple_bad or priv_ws_bad or pf_bad
    crit_breach = crit_avail_bad or pswpout_bad or ple_bad
    return (any_breach, crit_breach, pf_delta)


def log(msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    RAW_OUT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8", errors="replace") as fh:
        fh.write(line + "\n")


def load_tasks() -> list[dict[str, Any]]:
    with open(run_suite.TASKS_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)["tasks"]


def read_json_safe(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def _extract_t4_summary(st: dict[str, Any] | None) -> str:
    """Format t4 TypeScript compiler & DAG unit test summary from static_audit.json."""
    if not isinstance(st, dict):
        return "-"
    ts_eval = st.get("typescript_eval") or {}
    if not ts_eval:
        return "-"
    tsc_ok = ts_eval.get("tsc_strict_passed")
    passed = ts_eval.get("tests_passed")
    total = ts_eval.get("tests_total")
    if passed is None:
        passed = ts_eval.get("passed_tests")
    if total is None:
        total = ts_eval.get("total_tests")
    if passed is None and isinstance(ts_eval.get("results"), list):
        passed = sum(1 for x in ts_eval["results"] if x.get("passed"))
        total = len(ts_eval["results"])
    elif passed is None and isinstance(ts_eval.get("tests"), list):
        passed = sum(1 for x in ts_eval["tests"] if x.get("passed"))
        total = len(ts_eval["tests"])
    return f"tsc={'PASS' if tsc_ok else 'FAIL'}, tests={passed}/{total}"


def _detect_trunc_or_loop(t: dict[str, Any], meta: dict[str, Any] | None, tdir: Path, st: dict[str, Any] | None) -> bool:
    """Return True if a task stopped on max length, truncated mid-file, or ended in a suffix loop."""
    if not isinstance(meta, dict) or meta.get("status") == "error":
        return False
    if meta.get("finish_reason") == "length":
        return True
    if t.get("category") != "typescript_coding":
        idx_path = tdir / "index.html"
        if not idx_path.exists():
            return True
        html_low = idx_path.read_text(encoding="utf-8", errors="replace").lower()
        if "</html>" not in html_low:
            return True
    if isinstance(st, dict) and st.get("all_required_files_present") is False:
        return True
    raw_path = tdir / "raw.md"
    if raw_path.exists():
        tail = raw_path.read_text(encoding="utf-8", errors="replace")[-512:]
        if re.search(r"(.{16,}?)\1{3,}$", tail, re.DOTALL):
            return True
    return False


def compute_model_stats(slug: str, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    mdir = RUNS_DIR / slug
    static_all = read_json_safe(mdir / "static_audit.json") or {}
    runtime_all = read_json_safe(mdir / "runtime_audit.json") or {}
    telemetry = read_json_safe(RAW_OUT_DIR / f"telemetry_{slug}.json") or {}

    rows: list[dict[str, Any]] = []
    completed = 0
    errors = 0
    speeds: list[float] = []
    perfs: list[float] = []
    a11ys: list[float] = []
    bps: list[float] = []
    seos: list[float] = []
    console_errs = 0
    ext_reqs = 0
    loop_count = 0
    all_files_ok = 0
    hdr_ok = 0
    hdr_total = 0
    faq_ok = 0
    faq_total = 0
    mob_overflow = 0
    t4_summary = "-"

    for t in tasks:
        tid = t["id"]
        tdir = mdir / tid
        meta = read_json_safe(tdir / "meta.json")
        st = static_all.get(tid) if isinstance(static_all, dict) else None
        rt = runtime_all.get(tid) if isinstance(runtime_all, dict) else None

        status = "PENDING"
        finish_reason = "-"
        tok_s = None
        elapsed = None
        comp_tok = None
        if isinstance(meta, dict):
            if meta.get("status") == "error":
                status = f"ERROR: {str(meta.get('error', ''))[:60]}"
                errors += 1
            else:
                status = "DONE"
                completed += 1
            finish_reason = str(meta.get("finish_reason") or "-")
            tok_s = meta.get("tok_per_sec")
            elapsed = meta.get("elapsed_sec")
            comp_tok = (meta.get("usage") or {}).get("completion_tokens")
            if isinstance(tok_s, (int, float)) and tok_s > 0:
                speeds.append(float(tok_s))

        lh = (rt or {}).get("lighthouse") if isinstance(rt, dict) else None
        if isinstance(lh, dict):
            if isinstance(lh.get("performance"), (int, float)):
                perfs.append(float(lh["performance"]))
            if isinstance(lh.get("accessibility"), (int, float)):
                a11ys.append(float(lh["accessibility"]))
            if isinstance(lh.get("bestPractices"), (int, float)):
                bps.append(float(lh["bestPractices"]))
            if isinstance(lh.get("seo"), (int, float)):
                seos.append(float(lh["seo"]))
        if isinstance(rt, dict):
            console_errs += len(rt.get("consoleErrors") or []) + len(rt.get("pageErrors") or [])
            ext_reqs += len(rt.get("externalRequests") or [])
            if (rt.get("mobile") or {}).get("overflowX"):
                mob_overflow += 1

        if isinstance(st, dict):
            if st.get("all_required_files_present"):
                all_files_ok += 1
            if isinstance(st.get("_headers"), dict):
                hdr_total += 1
                if st["_headers"].get("all_passed"):
                    hdr_ok += 1
            if isinstance(st.get("json_ld"), dict):
                faq_total += 1
                if st["json_ld"].get("faq_all_verbatim"):
                    faq_ok += 1
            if t["category"] == "typescript_coding":
                t4_summary = _extract_t4_summary(st)

        if _detect_trunc_or_loop(t, meta, tdir, st):
            loop_count += 1

        rows.append(
            {
                "task": t,
                "meta": meta,
                "static": st,
                "runtime": rt,
                "status": status,
                "finish_reason": finish_reason,
                "tok_s": tok_s,
                "elapsed": elapsed,
                "comp_tok": comp_tok,
                "has_index": (tdir / "index.html").exists(),
                "has_dag": (tdir / "dag.ts").exists(),
                "has_desk_png": (tdir / "shot-desktop.png").exists(),
                "has_mob_png": (tdir / "shot-mobile.png").exists(),
            }
        )

    def _avg(vals: list[float]) -> str:
        return f"{sum(vals) / len(vals):.2f}" if vals else "-"

    return {
        "slug": slug,
        "completed": completed,
        "errors": errors,
        "rows": rows,
        "mean_tok_s": _avg(speeds),
        "mean_perf": _avg(perfs),
        "mean_a11y": _avg(a11ys),
        "mean_bp": _avg(bps),
        "mean_seo": _avg(seos),
        "console_errs": console_errs,
        "ext_reqs": ext_reqs,
        "loop_count": loop_count,
        "all_files_ok": all_files_ok,
        "hdr_ok": hdr_ok,
        "hdr_total": hdr_total,
        "faq_ok": faq_ok,
        "faq_total": faq_total,
        "mob_overflow": mob_overflow,
        "t4_summary": t4_summary,
        "telemetry": telemetry,
        "has_static": bool(static_all),
        "has_runtime": bool(runtime_all),
    }


def write_live_status(
    state_line: str,
    tasks: list[dict[str, Any]],
    note: str = "",
    active_slugs: list[str] | None = None,
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slugs = active_slugs or [s for s, _ in MODEL_QUEUE]
    lines = [
        "# SmartLLM Step 8 — Живой статус локального бенчмарка (`eval/suite/`)",
        "",
        f"- **Обновлено:** `{now}` (UTC+4)",
        f"- **Состояние:** **{state_line}**",
        f"- **Визуальная витрина (открой в браузере):** [`eval/suite/results/gallery.html`](gallery.html)",
        f"- **Сводный отчёт сравнения:** [`eval/suite/results/auto_benchmark_report.md`](auto_benchmark_report.md)",
        f"- **Лог раннера:** [`research/step8_raw/autonomous_eval.log`](../../research/step8_raw/autonomous_eval.log)",
    ]
    if note:
        lines.append(f"- **Заметка:** {note}")
    lines.append("")

    for slug in slugs:
        st = compute_model_stats(slug, tasks)
        lines.append(
            f"## `{slug}` — `{st['completed']} / {len(tasks)}` задач"
            + (f" (mean `{st['mean_tok_s']} tok/s`)" if st["mean_tok_s"] != "-" else "")
        )
        lines.append("")
        lines.append("| Task | Тема | Статус | Finish | Tok/s | Время | Артефакт |")
        lines.append("|---|---|---|---|---:|---:|---|")
        for r in st["rows"]:
            t = r["task"]
            tid = t["id"]
            title = t.get("title", tid)
            if r["has_index"]:
                art = f"[index.html](../runs/{slug}/{tid}/index.html)"
                if r["has_desk_png"]:
                    art += f" · [desktop.png](../runs/{slug}/{tid}/shot-desktop.png)"
            elif r["has_dag"]:
                art = f"[dag.ts](../runs/{slug}/{tid}/dag.ts)"
            else:
                art = "—"
            tok_str = f"{r['tok_s']:.2f}" if isinstance(r["tok_s"], (int, float)) else "—"
            el_str = f"{r['elapsed']:.1f}s" if isinstance(r["elapsed"], (int, float)) else "—"
            lines.append(f"| `{tid}` | {title} | {r['status']} | `{r['finish_reason']}` | {tok_str} | {el_str} | {art} |")
        lines.append("")

    LIVE_STATUS_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_gallery_html(
    state_line: str,
    tasks: list[dict[str, Any]],
    active_slugs: list[str] | None = None,
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slugs = active_slugs or [s for s, _ in MODEL_QUEUE]
    stats_by_slug = {slug: compute_model_stats(slug, tasks) for slug in slugs}

    cards_html: list[str] = []
    for idx, t in enumerate(tasks):
        tid = t["id"]
        title = html.escape(t.get("title", tid))
        cat = html.escape(t.get("category", ""))
        mod = html.escape(t.get("modality", "text"))

        cols: list[str] = []
        for slug in slugs:
            row = stats_by_slug[slug]["rows"][idx]
            rt = row["runtime"] or {}
            lh = rt.get("lighthouse") or {}
            st = row["static"] or {}

            badge = "PENDING"
            badge_cls = "pending"
            if row["status"] == "DONE":
                badge = "DONE"
                badge_cls = "done"
            elif row["status"].startswith("ERROR"):
                badge = "ERROR"
                badge_cls = "err"

            metrics_parts: list[str] = []
            if isinstance(row["tok_s"], (int, float)):
                metrics_parts.append(f"{row['tok_s']:.1f} tok/s")
            if isinstance(row["elapsed"], (int, float)):
                metrics_parts.append(f"{row['elapsed']:.0f}s")
            if row["finish_reason"] != "-":
                metrics_parts.append(f"fin:{html.escape(row['finish_reason'])}")
            if lh:
                metrics_parts.append(
                    f"LH {lh.get('performance','-')}/{lh.get('accessibility','-')}/{lh.get('bestPractices','-')}/{lh.get('seo','-')}"
                )
            if t["category"] == "typescript_coding" and isinstance(st, dict) and st.get("typescript_eval"):
                metrics_parts.append(_extract_t4_summary(st))

            links_parts: list[str] = []
            if row["has_index"]:
                links_parts.append(f'<a class="btn" href="../runs/{slug}/{tid}/index.html" target="_blank">Открыть сайт</a>')
            if row["has_dag"]:
                links_parts.append(f'<a class="btn" href="../runs/{slug}/{tid}/dag.ts" target="_blank">dag.ts</a>')
            if (RUNS_DIR / slug / tid / "raw.md").exists():
                links_parts.append(f'<a href="../runs/{slug}/{tid}/raw.md" target="_blank">raw.md</a>')

            shot_html = ""
            if row["has_desk_png"]:
                shot_html = (
                    f'<div class="shots">'
                    f'<a href="../runs/{slug}/{tid}/shot-desktop-full.png" target="_blank">'
                    f'<img src="../runs/{slug}/{tid}/shot-desktop.png" loading="lazy" alt="{html.escape(slug)} {tid} desktop"></a>'
                    + (
                        f'<a href="../runs/{slug}/{tid}/shot-mobile-full.png" target="_blank">'
                        f'<img class="mob" src="../runs/{slug}/{tid}/shot-mobile.png" loading="lazy" alt="{html.escape(slug)} {tid} mobile"></a>'
                        if row["has_mob_png"]
                        else ""
                    )
                    + "</div>"
                )
            elif row["has_index"]:
                shot_html = '<div class="wait-shot">Скриншот Chromium/Lighthouse будет снят после завершения очереди модели.</div>'

            cols.append(
                f'<div class="col">'
                f'<div class="col-head"><strong>{html.escape(slug)}</strong>'
                f'<span class="badge {badge_cls}">{badge}</span></div>'
                f'<div class="meta">{" · ".join(metrics_parts) if metrics_parts else "Ожидает очереди"}</div>'
                f'<div class="links">{" ".join(links_parts)}</div>'
                f'{shot_html}'
                f'</div>'
            )

        cards_html.append(
            f'<article class="card">'
            f'<header><h3><code>{html.escape(tid)}</code> — {title}</h3>'
            f'<span class="tag">{cat} · {mod}</span></header>'
            f'<div class="cols">{"".join(cols)}</div>'
            f'</article>'
        )

    summary_rows: list[str] = []
    for slug in slugs:
        st = stats_by_slug[slug]
        tel = (st["telemetry"] or {}).get("summary") or {}
        pg_gen = tel.get("pages_output_per_sec_gen_mean", "—")
        pgf_d = tel.get("pagefile_usage_pct_delta", "—")
        vram_max = tel.get("max_gpu_used_mib", "—")
        summary_rows.append(
            f"<tr><td><code>{html.escape(slug)}</code></td>"
            f"<td>{st['completed']}/{len(tasks)}</td>"
            f"<td>{st['mean_tok_s']}</td>"
            f"<td>{st['mean_perf']} / {st['mean_a11y']} / {st['mean_bp']} / {st['mean_seo']}</td>"
            f"<td>{html.escape(st['t4_summary'])}</td>"
            f"<td>{st['loop_count']}</td>"
            f"<td>{st['console_errs']} / {st['ext_reqs']} (mobOF {st['mob_overflow']})</td>"
            f"<td>VRAM {vram_max} MiB · pg_gen {pg_gen} · pfΔ {pgf_d}%</td></tr>"
        )

    title_slugs = " vs ".join(slugs)
    doc = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SmartLLM Step 8 — Галерея 12 задач</title>
<style>
  :root {{ --bg:#0d1016; --panel:#161b24; --line:#293242; --fg:#edf2f7; --muted:#9aa5b5; --acc:#4ea1ff; --ok:#2ecc71; --err:#ff5c5c; --warn:#f6ad55; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:24px; background:var(--bg); color:var(--fg); font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  h1,h2,h3 {{ margin:0 0 8px; font-weight:600; }}
  a {{ color:var(--acc); text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .top {{ max-width:1400px; margin:0 auto 24px; background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:20px; }}
  .sub {{ color:var(--muted); margin-bottom:14px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); }}
  th {{ color:var(--muted); font-weight:500; }}
  .grid {{ max-width:1400px; margin:0 auto; display:grid; gap:18px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px; }}
  .card header {{ display:flex; justify-content:space-between; align-items:baseline; gap:12px; border-bottom:1px solid var(--line); padding-bottom:10px; margin-bottom:14px; }}
  .tag {{ color:var(--muted); font-size:12px; }}
  .cols {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)); gap:16px; }}
  .col {{ background:#11151d; border:1px solid var(--line); border-radius:10px; padding:12px; }}
  .col-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }}
  .badge {{ font-size:11px; padding:2px 8px; border-radius:999px; font-weight:600; }}
  .badge.done {{ background:#143824; color:var(--ok); }}
  .badge.pending {{ background:#2a2518; color:var(--warn); }}
  .badge.err {{ background:#3b181b; color:var(--err); }}
  .meta {{ font-size:12px; color:var(--muted); margin-bottom:8px; min-height:18px; }}
  .links {{ display:flex; gap:10px; align-items:center; margin-bottom:10px; flex-wrap:wrap; }}
  .btn {{ background:var(--acc); color:#07111f; padding:4px 10px; border-radius:6px; font-weight:600; font-size:12px; }}
  .shots {{ display:flex; gap:8px; align-items:flex-start; }}
  .shots img {{ max-height:180px; width:auto; max-width:74%; border:1px solid var(--line); border-radius:6px; display:block; }}
  .shots img.mob {{ max-width:24%; }}
  .wait-shot {{ font-size:12px; color:var(--muted); padding:10px; border:1px dashed var(--line); border-radius:6px; }}
</style>
</head>
<body>
<div class="top">
  <h1>SmartLLM Step 8 — Автономная витрина 12 задач (<code>{html.escape(title_slugs)}</code>)</h1>
  <div class="sub">Обновлено: <code>{html.escape(now)}</code> · Состояние: <strong>{html.escape(state_line)}</strong> · Офлайн локальная RTX 4080 (`127.0.0.1:8080`, `0` внешних API)</div>
  <table>
    <thead><tr><th>Модель</th><th>Готово</th><th>Mean tok/s</th><th>Lighthouse (P/A/BP/SEO)</th><th>t4 DAG</th><th>Trunc/Loop</th><th>Err/Ext/MobOF</th><th>Телеметрия RAM/VRAM</th></tr></thead>
    <tbody>{"".join(summary_rows)}</tbody>
  </table>
</div>
<div class="grid">
  {"".join(cards_html)}
</div>
</body>
</html>
"""
    GALLERY_HTML.write_text(doc, encoding="utf-8", newline="\n")


def write_auto_benchmark_report(
    tasks: list[dict[str, Any]],
    state_line: str,
    active_slugs: list[str] | None = None,
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slugs = list(active_slugs or [s for s, _ in MODEL_QUEUE])
    all_report_slugs = list(slugs)
    if "gyro-m-local" not in all_report_slugs and (RUNS_DIR / "gyro-m-local").is_dir():
        all_report_slugs.append("gyro-m-local")

    stats = [compute_model_stats(s, tasks) for s in all_report_slugs]
    active_stats = [st for st in stats if st["slug"] in slugs]

    lines = [
        "# SmartLLM Step 8 — Автоматический сводный отчёт (`eval/suite/`)",
        "",
        f"- **Дата:** `{now}` (UTC+4)",
        f"- **Состояние:** **{state_line}**",
        "- **Визуальная витрина:** [`eval/suite/results/gallery.html`](gallery.html)",
        "- **Исторический эталон (`Gyro-M` + `Qwen3.8`, v1 prompt era):** [`eval/suite/results/reference.md`](reference.md)",
        "",
        "## 1. Сводная таблица по моделям",
        "",
        "| Модель | Задач | Files / `_headers` / FAQ | MobOF | Mean `tok/s` | `t4` (`tsc` + unit tests) | Trunc / Loop | Console / ExtErr | Lighthouse mean (`P / A / BP / SEO`) | Anti-Swap (`max VRAM` / `pages_gen` / `pf_delta`) |",
        "|---|---:|---|---:|---:|---|---:|---:|---|---|",
    ]
    for st in stats:
        tel = (st["telemetry"] or {}).get("summary") or {}
        if tel:
            anti = f"{tel.get('max_gpu_used_mib', '—')} MiB / {tel.get('pages_output_per_sec_gen_mean', '—')} / {tel.get('pagefile_usage_pct_delta', '—')}%"
        elif st["slug"] == "gyro-m-local":
            anti = "нет телеметрии step8 (см. `reference.md`)"
        else:
            anti = "—"
        label = f"`{st['slug']}`" + (" *(ref v1)*" if st["slug"] == "gyro-m-local" else "")
        lh_str = f"{st['mean_perf']} / {st['mean_a11y']} / {st['mean_bp']} / {st['mean_seo']}"
        hygiene = f"{st['all_files_ok']}/{len(tasks)} · hdr {st['hdr_ok']}/{st['hdr_total']} · faq {st['faq_ok']}/{st['faq_total']}"
        lines.append(
            f"| {label} | `{st['completed']}/{len(tasks)}` | `{hygiene}` | `{st['mob_overflow']}` | `{st['mean_tok_s']}` | `{st['t4_summary']}` | `{st['loop_count']}` | `{st['console_errs']} / {st['ext_reqs']}` | `{lh_str}` | `{anti}` |"
        )
    lines.extend(["", "## 2. По-задачные артефакты и ссылки", ""])
    for idx, t in enumerate(tasks):
        tid = t["id"]
        lines.append(f"### `{tid}` — {t.get('title', tid)}")
        for st in active_stats:
            r = st["rows"][idx]
            target = (
                f"[`index.html`](../runs/{st['slug']}/{tid}/index.html)"
                if r["has_index"]
                else (f"[`dag.ts`](../runs/{st['slug']}/{tid}/dag.ts)" if r["has_dag"] else "—")
            )
            shots = (
                f", [`shot-desktop.png`](../runs/{st['slug']}/{tid}/shot-desktop.png)"
                if r["has_desk_png"]
                else ""
            )
            rt = r["runtime"] or {}
            lh = rt.get("lighthouse") or {}
            lh_txt = (
                f", LH `{lh.get('performance')}/{lh.get('accessibility')}/{lh.get('bestPractices')}/{lh.get('seo')}`"
                if lh
                else ""
            )
            lines.append(
                f"- `{st['slug']}`: {r['status']} (`fin={r['finish_reason']}`, `{r['tok_s']} tok/s`, `{r['elapsed']}s`{lh_txt}) -> {target}{shots}"
            )
        lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run_incremental_static_audit(slug: str, task_id: str | None = None) -> None:
    """Run CPU static/CSP/tsc audit for `slug` (optionally single task) and refresh static_audit_all.json."""
    cmd = [str(PYTHON_EXE), str(AUDIT_PY), slug]
    if task_id:
        cmd.extend(["--tasks", task_id])
    p_aud = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    log(f"incremental audit_suite.py ({slug}, task={task_id or 'all'}) rc={p_aud.returncode}")
    if p_aud.returncode != 0 and p_aud.stderr:
        log(f"  [audit-err] {p_aud.stderr[:400]}")


def run_post_model_audits(
    slug: str,
    tasks: list[dict[str, Any]],
    task_ids: list[str] | None = None,
    skip_browser: bool = False,
) -> None:
    log(f"Running audit_suite.py for {slug} (0 MiB VRAM)...")
    cmd_aud = [str(PYTHON_EXE), str(AUDIT_PY), slug]
    if task_ids:
        cmd_aud.extend(["--tasks", *task_ids])
    p_aud = subprocess.run(cmd_aud, capture_output=True, text=True, timeout=180, check=False)
    log(f"post audit_suite.py ({slug}) rc={p_aud.returncode}")

    if skip_browser:
        log(f"Skipping browser_and_lh_suite.mjs for {slug} (--skip-browser)")
        return

    log(f"Running browser_and_lh_suite.mjs for {slug} (Chromium 1440x900 + 375x812 + Lighthouse)...")
    cmd_br = [str(NODE_EXE), str(BROWSER_LH_MJS), slug]
    if task_ids:
        cmd_br.extend(["--tasks", *task_ids])
    p_br = subprocess.run(
        cmd_br,
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    log(f"browser_and_lh_suite.mjs ({slug}) rc={p_br.returncode}")
    if p_br.stdout:
        for ln in p_br.stdout.strip().splitlines()[-8:]:
            log(f"  [browser+lh] {ln}")
    if p_br.returncode != 0 and p_br.stderr:
        log(f"  [browser+lh-err] {p_br.stderr[:500]}")


def ensure_clean_vram_and_port() -> None:
    for _ in range(12):
        vram, apps = s7.query_nvidia_smi()
        port_open = s7.is_port_open(s7.HOST, s7.PORT)
        if vram <= 128 and not apps and not port_open:
            return
        time.sleep(1.5)
    vram, apps = s7.query_nvidia_smi()
    raise RuntimeError(f"Unsafe GPU/port state: vram={vram} MiB, apps={apps}, port_8080={s7.is_port_open(s7.HOST, s7.PORT)}")


def run_model_queue_item(
    slug: str,
    model_path: Path,
    all_tasks: list[dict[str, Any]],
    selected_tasks: list[dict[str, Any]],
    active_slugs: list[str],
    force: bool = False,
    skip_browser: bool = False,
    temperature: float = TEMPERATURE,
    dry_multiplier: float = DRY_MULTIPLIER,
    dry_allowed_length: int = DRY_ALLOWED_LENGTH,
    dry_penalty_last_n: int = DRY_PENALTY_LAST_N,
    repeat_last_n: int = REPEAT_LAST_N,
    repeat_penalty: float = REPEAT_PENALTY,
    frequency_penalty: float = FREQUENCY_PENALTY,
    presence_penalty: float = PRESENCE_PENALTY,
    min_p: float = MIN_P,
    eos_logit_bias: float = EOS_LOGIT_BIAS,
) -> bool:
    ensure_clean_vram_and_port()
    server_log = RAW_OUT_DIR / f"server_{slug}.log"
    # Keep repeated --logit-bias args despite arg.cpp:844's generic boilerplate warning:
    # server.cpp:791 -> common_params_parse_ex calls handler_string (arg.cpp:870-871) on EVERY
    # occurrence, pushing all 11 tokens (arg.cpp:2270). Comma-separating --logit-bias would hit
    # ss >> key >> sign && getline + std::stof (arg.cpp:2268-2269) and drop tokens 2..11.
    logit_bias_args: list[str] = []
    for tok_id in LOGIT_BIAS_TOKENS:
        logit_bias_args.extend(["--logit-bias", f"{tok_id}-1000"])
    if eos_logit_bias != 0.0:
        sign = "+" if eos_logit_bias >= 0 else "-"
        logit_bias_args.extend(["--logit-bias", f"{EOS_TOKEN_ID}{sign}{abs(eos_logit_bias)}"])

    cmd = [
        str(s7.SERVER_EXE),
        "-m",
        str(model_path),
        "--mmproj",
        str(s7.MMPROJ_PATH),
        "--image-min-tokens",
        "1024",
        "--load-mode",
        "mmap",
        "--lazy-mode",
        "direct",
        "--moe-cache-mib",
        "4096",
        "-ngl",
        "99",
        "--n-cpu-moe",
        "48",
        "-nr",
        "-fa",
        "on",
        "-fit",
        "off",
        "-np",
        "1",
        "-c",
        "32768",
        "-ctk",
        "q8_0",
        "-ctv",
        "q8_0",
        "--cache-ram",
        "0",
        "--ctx-checkpoints",
        "0",
        "--no-cache-prompt",
        "--reasoning-budget",
        str(REASONING_BUDGET),
        "--reasoning-effort",
        "medium",
        "--temp",
        str(temperature),
        "--top-k",
        str(TOP_K),
        "--top-p",
        str(TOP_P),
        "--min-p",
        str(min_p),
        *logit_bias_args,
        "--host",
        s7.HOST,
        "--port",
        str(s7.PORT),
    ]

    log(
        f"=== STARTING MODEL {slug}: {model_path.name} "
        f"(temp={temperature}, min_p={min_p}, dry={dry_multiplier}/len={dry_allowed_length}/n={dry_penalty_last_n}, "
        f"rep={repeat_penalty}/pres={presence_penalty}, eos_bias={eos_logit_bias}, tasks={[t['id'] for t in selected_tasks]}) ==="
    )
    proc: subprocess.Popen[Any] | None = None
    recorder: s7.TelemetryRecorder | None = None
    watcher_stop = threading.Event()
    watcher_thread: threading.Thread | None = None
    abort_lock = threading.Lock()
    abort_triggered = False
    ok_all = True
    fail_reason = ""
    cleanup_err: str | None = None
    results: list[dict[str, Any]] = []
    selected_ids = [t["id"] for t in selected_tasks] if len(selected_tasks) < len(all_tasks) else None

    with open(server_log, "w", encoding="utf-8", errors="replace") as log_fh:
        try:
            proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT, text=True)

            def _abort() -> None:
                nonlocal abort_triggered
                with abort_lock:
                    if abort_triggered:
                        return
                    abort_triggered = True
                    if proc is not None and proc.poll() is None:
                        proc.terminate()
                        try:
                            proc.wait(timeout=5.0)
                        except subprocess.TimeoutExpired:
                            if proc.poll() is None:
                                proc.kill()
                                try:
                                    proc.wait(timeout=5.0)
                                except subprocess.TimeoutExpired:
                                    pass

            # Disable TelemetryRecorder's unsynchronized 1-sample abort; _mmap_watchdog owns all aborts under abort_lock.
            recorder = s7.TelemetryRecorder(
                proc.pid,
                watchdog_min_avail_mib=0.0,
                on_watchdog=None,
                gguf_path=model_path,
            )
            recorder.start()

            def _mmap_watchdog() -> None:
                pf_start: float | None = None
                last_idx = 0
                breach_streak = 0
                crit_streak = 0
                while not watcher_stop.is_set() and proc is not None and proc.poll() is None:
                    samples = list(recorder.samples)
                    for s in samples[last_idx:]:
                        if pf_start is None and s.get("pagefile_usage_pct") is not None:
                            pf_start = float(s["pagefile_usage_pct"])
                        any_breach, crit_avail_bad, pf_delta = evaluate_watchdog_sample(s, pf_start)

                        crit_streak = (crit_streak + 1) if crit_avail_bad else 0
                        if any_breach:
                            breach_streak += 1
                            if breach_streak >= 4 or crit_streak >= 2:
                                recorder.aborted_due_to_ram_pressure = True
                                recorder.stop()
                                log(
                                    f"Mmap watchdog abort on {slug}: phase={s.get('phase')}, avail={s.get('avail_phys_mib')} MiB, "
                                    f"recl={s.get('reclaimable_ram_gib')} GiB, cpu_priv_ws={s.get('cpu_private_ws_gib')} GiB, "
                                    f"pf_delta={pf_delta:.3f}% (streak={breach_streak}, crit={crit_streak})"
                                )
                                _abort()
                                return
                        else:
                            breach_streak = 0
                    last_idx = len(samples)
                    watcher_stop.wait(0.25)

            watcher_thread = threading.Thread(target=_mmap_watchdog, daemon=True)
            watcher_thread.start()

            healthy, ready_sec = s7.wait_for_health(proc, timeout_sec=180.0)
            log(f"Health for {slug}: ok={healthy}, ready_sec={ready_sec}")
            if not healthy:
                ok_all = False
                fail_reason = "watchdog RAM abort" if recorder.aborted_due_to_ram_pressure else f"health check failed rc={proc.poll()}"
            else:
                recorder.mark_ready()
                for t in selected_tasks:
                    tid = t["id"]
                    if tid in SKIP_TASKS_BY_SLUG.get(slug, set()):
                        log(f"Skipping {slug} / {tid}")
                        continue
                    if recorder.aborted_due_to_ram_pressure or proc.poll() is not None:
                        ok_all = False
                        fail_reason = f"server exited or RAM watchdog tripped before {tid} (rc={proc.poll()})"
                        break
                    write_live_status(f"RUNNING `{slug}` -> задача `{tid}`", all_tasks, active_slugs=active_slugs)
                    write_gallery_html(f"RUNNING {slug} -> {tid}", all_tasks, active_slugs=active_slugs)

                    res = run_suite.run_task(
                        endpoint=f"{s7.BASE_URL}/v1/chat/completions",
                        model_slug=slug,
                        model_id=slug,
                        task_spec=t,
                        reasoning_budget=REASONING_BUDGET,
                        max_tokens=MAX_TOKENS,
                        temperature=temperature,
                        top_k=TOP_K,
                        top_p=TOP_P,
                        min_p=min_p,
                        dry_multiplier=dry_multiplier,
                        dry_base=DRY_BASE,
                        dry_allowed_length=dry_allowed_length,
                        dry_penalty_last_n=dry_penalty_last_n,
                        dry_sequence_breakers=DRY_SEQUENCE_BREAKERS,
                        repeat_last_n=repeat_last_n,
                        repeat_penalty=repeat_penalty,
                        frequency_penalty=frequency_penalty,
                        presence_penalty=presence_penalty,
                        logit_bias_tokens=None,
                        eos_logit_bias=eos_logit_bias,
                        force=force,
                    )
                    results.append(res)
                    run_suite.merge_run_summary(slug, results, all_tasks)
                    run_incremental_static_audit(slug, task_id=tid)
                    write_live_status(f"RUNNING `{slug}` (завершена `{tid}`)", all_tasks, active_slugs=active_slugs)
                    write_gallery_html(f"RUNNING {slug} (done {tid})", all_tasks, active_slugs=active_slugs)
                    write_auto_benchmark_report(all_tasks, f"RUNNING {slug} (done {tid})", active_slugs=active_slugs)

                    if res.get("status") == "error" or recorder.aborted_due_to_ram_pressure:
                        ok_all = False
                        fail_reason = f"task {tid} error={res.get('error')} watchdog={recorder.aborted_due_to_ram_pressure}"
                        break
        except Exception as exc:
            ok_all = False
            fail_reason = f"exception: {exc}"
        finally:
            watcher_stop.set()
            if watcher_thread is not None:
                watcher_thread.join(timeout=3)
            tel_summary = {}
            if recorder is not None:
                recorder.stop()
                tel_summary = recorder.summary()
            post: dict[str, Any] = {}
            try:
                post = s7.stop_server_and_verify(proc)
                if (
                    post.get("post_vram_used_mib", 0) > 128
                    or post.get("post_compute_apps")
                    or post.get("port_8080_open")
                ):
                    ensure_clean_vram_and_port()
                    vram_r, apps_r = s7.query_nvidia_smi()
                    post["post_vram_used_mib"] = vram_r
                    post["post_compute_apps"] = apps_r
                    post["port_8080_open"] = s7.is_port_open(s7.HOST, s7.PORT)
                    post["reverified_clean"] = True
            except Exception as cleanup_exc:
                cleanup_err = str(cleanup_exc)
                ok_all = False
                fail_reason = f"{fail_reason}; cleanup_error={cleanup_err}" if fail_reason else f"cleanup_error={cleanup_err}"

            (RAW_OUT_DIR / f"telemetry_{slug}.json").write_text(
                json.dumps(
                    {
                        "slug": slug,
                        "model": model_path.name,
                        "ok": ok_all,
                        "fail_reason": fail_reason,
                        "cleanup_error": cleanup_err,
                        "summary": tel_summary,
                        "post_cleanup": post,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            log(f"Stopped {slug}: ok={ok_all}, vram_post={post.get('post_vram_used_mib')} MiB, reason={fail_reason or 'clean'}")
            if cleanup_err:
                raise RuntimeError(f"Post-run GPU/port cleanup failed for {slug}: {cleanup_err}")

    # Run offline audits & Playwright screenshots at 0 MiB VRAM whenever at least 1 task exists
    if results:
        run_post_model_audits(slug, all_tasks, task_ids=selected_ids, skip_browser=skip_browser)
        write_auto_benchmark_report(all_tasks, f"IN_PROGRESS ({slug} audited)", active_slugs=active_slugs)
        write_gallery_html(f"AUDITED {slug}", all_tasks, active_slugs=active_slugs)
        write_live_status(f"AUDITED `{slug}`", all_tasks, note=fail_reason, active_slugs=active_slugs)

    return ok_all


def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomous Step 8 Local Eval Runner (v2.2.4)")
    parser.add_argument("--models", nargs="*", help="Subset of model slugs from MODEL_QUEUE (e.g. smartllm-205e-iq3-s)")
    parser.add_argument("--tasks", nargs="*", help="Subset of task IDs (e.g. t3 t9)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing completed tasks")
    parser.add_argument("--reextract", action="store_true", help="Offline re-extract + re-audit without GPU server")
    parser.add_argument("--skip-browser", action="store_true", help="Skip Playwright/Lighthouse browser audit")
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--min-p", type=float, default=MIN_P)
    parser.add_argument("--dry-multiplier", type=float, default=DRY_MULTIPLIER)
    parser.add_argument("--dry-allowed-length", type=int, default=DRY_ALLOWED_LENGTH)
    parser.add_argument("--dry-penalty-last-n", type=int, default=DRY_PENALTY_LAST_N)
    parser.add_argument("--repeat-last-n", type=int, default=REPEAT_LAST_N)
    parser.add_argument("--repeat-penalty", type=float, default=REPEAT_PENALTY)
    parser.add_argument("--frequency-penalty", type=float, default=FREQUENCY_PENALTY)
    parser.add_argument("--presence-penalty", type=float, default=PRESENCE_PENALTY)
    parser.add_argument("--eos-logit-bias", type=float, default=EOS_LOGIT_BIAS)
    args = parser.parse_args()

    RAW_OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    queue = [(s, p) for s, p in MODEL_QUEUE if not args.models or s in args.models]
    if not queue:
        raise ValueError(f"No models matched --models={args.models}")
    active_slugs = [s for s, _ in queue]
    for slug in active_slugs:
        (RUNS_DIR / slug).mkdir(parents=True, exist_ok=True)

    all_tasks = load_tasks()
    selected_tasks = [t for t in all_tasks if not args.tasks or t["id"] in args.tasks]
    if not selected_tasks:
        raise ValueError(f"No tasks matched --tasks={args.tasks}")
    task_ids = [t["id"] for t in selected_tasks] if args.tasks else None

    if args.reextract:
        log(f"Offline --reextract mode for models={active_slugs}, tasks={task_ids or 'all'}")
        for slug in active_slugs:
            re_res = []
            for t in selected_tasks:
                meta = run_suite.reextract_task(slug, t)
                if meta is not None:
                    re_res.append(meta)
            if re_res:
                run_suite.merge_run_summary(slug, re_res, all_tasks)
            run_post_model_audits(slug, all_tasks, task_ids=task_ids, skip_browser=args.skip_browser)
        write_auto_benchmark_report(all_tasks, f"REEXTRACTED ({', '.join(active_slugs)})", active_slugs=active_slugs)
        write_gallery_html("REEXTRACTED", all_tasks, active_slugs=active_slugs)
        write_live_status("REEXTRACTED (0 MiB VRAM)", all_tasks, active_slugs=active_slugs)
        return 0

    write_live_status("INITIALIZING (pre-flight check)", all_tasks, active_slugs=active_slugs)
    write_gallery_html("INITIALIZING", all_tasks, active_slugs=active_slugs)
    write_auto_benchmark_report(all_tasks, "INITIALIZING", active_slugs=active_slugs)
    log(f"Bootstrap OK: {len(selected_tasks)}/{len(all_tasks)} tasks queued across {active_slugs}")

    try:
        ensure_clean_vram_and_port()
    except Exception as exc:
        log(f"PRE-FLIGHT ABORT: {exc}")
        write_live_status("ABORTED (pre-flight VRAM/port busy)", all_tasks, note=str(exc), active_slugs=active_slugs)
        write_gallery_html("ABORTED PRE-FLIGHT", all_tasks, active_slugs=active_slugs)
        return 1

    for slug, model_path in queue:
        ok = run_model_queue_item(
            slug=slug,
            model_path=model_path,
            all_tasks=all_tasks,
            selected_tasks=selected_tasks,
            active_slugs=active_slugs,
            force=args.force,
            skip_browser=args.skip_browser,
            temperature=args.temperature,
            dry_multiplier=args.dry_multiplier,
            dry_allowed_length=args.dry_allowed_length,
            dry_penalty_last_n=args.dry_penalty_last_n,
            repeat_last_n=args.repeat_last_n,
            repeat_penalty=args.repeat_penalty,
            frequency_penalty=args.frequency_penalty,
            presence_penalty=args.presence_penalty,
            min_p=args.min_p,
            eos_logit_bias=args.eos_logit_bias,
        )
        if not ok:
            log(f"ABORTING QUEUE ON {slug} FAILURE (no auto-retry per rule).")
            write_live_status(f"STOPPED ON `{slug}` FAILURE (VRAM=0 MiB)", all_tasks, active_slugs=active_slugs)
            write_gallery_html(f"STOPPED ON {slug} FAILURE", all_tasks, active_slugs=active_slugs)
            write_auto_benchmark_report(all_tasks, f"STOPPED ON {slug} FAILURE", active_slugs=active_slugs)
            return 1

    label = " + ".join(active_slugs)
    write_auto_benchmark_report(all_tasks, f"COMPLETE ({label})", active_slugs=active_slugs)
    write_gallery_html(f"COMPLETE ({label})", all_tasks, active_slugs=active_slugs)
    write_live_status(f"COMPLETE ({label}, VRAM `0 MiB`)", all_tasks, active_slugs=active_slugs)
    log("=== ALL STEP 8 AUTONOMOUS BENCHMARKS & AUDITS COMPLETE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
