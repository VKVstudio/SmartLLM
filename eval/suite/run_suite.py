import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_ROOT_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from scripts.platform_paths import (
    RUNS_DIR as _RUNS_PATH,
    SUITE_DIR as _SUITE_PATH,
    TASKS_JSON as _TASKS_PATH,
    assert_local_endpoint,
)

SUITE_DIR = str(_SUITE_PATH)
TASKS_JSON = str(_TASKS_PATH)
RUNS_DIR = str(_RUNS_PATH)

# Frozen Qwen3.8 donor-recommended sampler settings (Stage A CODE-03 fix):
# No --eos-logit-bias (-3.0 removed) and no -1000 logit-bias token suppression by default.
DEFAULT_TEMPERATURE = 0.6
DEFAULT_MIN_P = 0.0
DEFAULT_TOP_K = 20
DEFAULT_TOP_P = 0.95
DEFAULT_DRY_MULTIPLIER = 0.0
DEFAULT_DRY_BASE = 1.75
DEFAULT_DRY_ALLOWED_LENGTH = 24
DEFAULT_DRY_PENALTY_LAST_N = 0
DEFAULT_DRY_SEQUENCE_BREAKERS: tuple[str, ...] = ("\n", "<", ">", "{", "}", ";", "=")
DEFAULT_REPEAT_LAST_N = 64
DEFAULT_REPEAT_PENALTY = 1.0
DEFAULT_FREQUENCY_PENALTY = 0.0
DEFAULT_PRESENCE_PENALTY = 0.0
DEFAULT_LOGIT_BIAS_TOKENS: tuple[int, ...] = ()
DEFAULT_EOS_TOKEN_ID = 248046
DEFAULT_EOS_LOGIT_BIAS = 0.0

FROZEN_SAMPLER_CONFIG: dict[str, object] = {
    "temperature": DEFAULT_TEMPERATURE,
    "top_p": DEFAULT_TOP_P,
    "top_k": DEFAULT_TOP_K,
    "min_p": DEFAULT_MIN_P,
    "dry_multiplier": DEFAULT_DRY_MULTIPLIER,
    "repeat_penalty": DEFAULT_REPEAT_PENALTY,
    "frequency_penalty": DEFAULT_FREQUENCY_PENALTY,
    "presence_penalty": DEFAULT_PRESENCE_PENALTY,
    "eos_logit_bias": DEFAULT_EOS_LOGIT_BIAS,
    "logit_bias_tokens": list(DEFAULT_LOGIT_BIAS_TOKENS),
}

_FILE_HEADER_RE = re.compile(
    r"^[ \t]*(?:[#*`>\-]+[ \t]*)*\*?\*?FILE\*?\*?:\s*[`'\"]?([A-Za-z0-9_./\\\-]+)[`'\"]?(?:\*\*|[`*:\t ])*$",
    re.IGNORECASE,
)
_INLINE_FENCE_FILE_RE = re.compile(
    r"^[ \t]*(`{3,}|~{3,})([A-Za-z0-9_+\-]*)[ \t]*:?[ \t]+((?:\./|[A-Za-z0-9_.\-]+/)*(?:_headers|[A-Za-z0-9_.\-]+\.[A-Za-z0-9]+))[ \t]*$"
)
_DELIVERABLE_START_RE = re.compile(
    r"(?:^[ \t]*(?:[#*`>\-]+[ \t]*)*\*?\*?FILE\*?\*?:|^[ \t]*(?:`{3,}|~{3,})|<!DOCTYPE\s+html\b)",
    re.IGNORECASE | re.MULTILINE,
)


def clean_model_text(raw_text: str) -> str:
    """Strip reasoning <think> blocks and <tool_call> blocks without eating deliverables (CODE-02 fix).

    - Closed <think>...</think> blocks are stripped.
    - An unclosed leading <think> at the start of raw_text is stripped ONLY up to the first
      deliverable boundary (FILE: header, code fence, or <!DOCTYPE html>), never across
      already-started code or literal '<think>' mentions inside HTML/JS/prose.
    """
    if not raw_text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
    lead_think = re.match(r"^\s*<think>", cleaned, flags=re.IGNORECASE)
    if lead_think:
        rest = cleaned[lead_think.end() :]
        boundary = _DELIVERABLE_START_RE.search(rest)
        if boundary:
            cleaned = rest[boundary.start() :]
        else:
            cleaned = ""
    cleaned = re.sub(r"<tool_call>.*?</tool_call>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


def _sanitize_basename(raw_name: str) -> str:
    """Return safe single-segment filename, or empty string if invalid."""
    norm = raw_name.strip().replace("\\", "/").strip("`*'\": ")
    if not norm or ".." in norm.split("/"):
        return ""
    base = os.path.basename(norm)
    if not base or base in (".", ".."):
        return ""
    return base


def _strip_section_fences(raw_section: str, is_markdown: bool) -> str:
    """Remove outer code fence and any post-fence commentary/tool junk (NEW-BUG-03 fix)."""
    text = raw_section.strip("\r\n")
    lines = text.splitlines()
    if not lines:
        return ""

    open_m = re.match(r"^[ \t]*(`{3,}|~{3,})([^\r\n]*)$", lines[0])
    if open_m:
        fence_char = open_m.group(1)[0]
        fence_len = len(open_m.group(1))
        closing_re = re.compile(rf"^[ \t]*{re.escape(fence_char)}{{{fence_len},}}[ \t]*$")
        if is_markdown:
            # For .md outputs, strip outer fence if a matching closing fence wraps the end.
            if len(lines) >= 2 and closing_re.match(lines[-1]):
                lines = lines[1:-1]
            else:
                for idx in range(len(lines) - 1, 0, -1):
                    if closing_re.match(lines[idx]):
                        tail = "\n".join(lines[idx + 1 :]).strip()
                        if not tail or not re.search(r"^#", tail, re.MULTILINE):
                            lines = lines[1:idx]
                        break
        else:
            lines = lines[1:]
            # Find the last </html> line if present so inner fences inside <pre>/<code> before </html> are ignored.
            last_html_close = -1
            for idx, ln in enumerate(lines):
                if "</html" in ln.lower():
                    last_html_close = idx
            search_start = last_html_close + 1 if last_html_close >= 0 else 0
            close_idx = None
            for idx in range(search_start, len(lines)):
                if closing_re.match(lines[idx]):
                    close_idx = idx
                    break
            if close_idx is None and search_start > 0:
                for idx in range(len(lines) - 1, -1, -1):
                    if closing_re.match(lines[idx]):
                        close_idx = idx
                        break
            if close_idx is not None:
                lines = lines[:close_idx]

    result = "\n".join(lines).strip("\r\n")
    result = re.sub(r"\r?\n</tool_call>\s*$", "", result)
    return result


def extract_files_from_raw(raw_text: str, out_dir: str, task_spec: dict) -> list[str]:
    """Extract files preceded by FILE: <name> (fence-aware) with truncated-output fallbacks."""
    clean_text = clean_model_text(raw_text)
    req_files = task_spec.get("required_files", [])
    req_set = {os.path.basename(f) for f in req_files}

    lines = clean_text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    cur_name: str | None = None
    cur_lines: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in lines:
        hdr_m = _FILE_HEADER_RE.match(line)
        inl_m = None if hdr_m else _INLINE_FENCE_FILE_RE.match(line)

        if hdr_m:
            cand = _sanitize_basename(hdr_m.group(1))
            if cand and (
                not in_fence
                or cand in req_set
                or (len(cand) <= 48 and "." in cand and line.lstrip().upper().startswith("FILE:"))
            ):
                if cur_name is not None:
                    sections.append((cur_name, cur_lines))
                cur_name = cand
                cur_lines = []
                in_fence = False
                fence_char = ""
                fence_len = 0
                continue

        if inl_m and not in_fence:
            cand = _sanitize_basename(inl_m.group(3))
            if cand:
                if cur_name is not None:
                    sections.append((cur_name, cur_lines))
                cur_name = cand
                f_str = inl_m.group(1)
                lang = inl_m.group(2)
                cur_lines = [f"{f_str}{lang}"]
                in_fence = True
                fence_char = f_str[0]
                fence_len = len(f_str)
                continue

        fence_m = re.match(r"^[ \t]*(`{3,}|~{3,})(.*)$", line)
        if fence_m:
            f_str = fence_m.group(1)
            info = fence_m.group(2).strip()
            if not in_fence:
                in_fence = True
                fence_char = f_str[0]
                fence_len = len(f_str)
            elif f_str[0] == fence_char and len(f_str) >= fence_len and not info:
                in_fence = False
                fence_char = ""
                fence_len = 0

        if cur_name is not None:
            cur_lines.append(line)

    if cur_name is not None:
        sections.append((cur_name, cur_lines))

    extracted: list[str] = []
    seen: set[str] = set()
    for fname_clean, sec_lines in sections:
        code = _strip_section_fences("\n".join(sec_lines), is_markdown=fname_clean.lower().endswith(".md"))
        if not code:
            continue
        target_path = os.path.join(out_dir, fname_clean)
        with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(code)
        if fname_clean not in seen:
            seen.add(fname_clean)
            extracted.append(fname_clean)

    # 2. Single-file fallback (e.g. Vision index.html or TypeScript dag.ts, including truncated)
    if not extracted and len(req_files) == 1:
        default_file = req_files[0]
        fallback = re.search(
            r"```(?:html|typescript|ts|markdown|md)?[ \t]*\r?\n(.*?)(?:\r?\n```[ \t]*(?:\r?\n|$)|$)",
            clean_text,
            re.DOTALL | re.IGNORECASE,
        )
        if fallback and fallback.group(1).strip():
            target_path = os.path.join(out_dir, default_file)
            with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(fallback.group(1).rstrip())
            extracted.append(f"{default_file} (fallback-fenced)")

    # 3. Safety net for index.html even on multi-file tasks (handles truncated output lacking </html> or closing fence)
    extracted_base = {f.split(" ")[0] for f in extracted}
    if "index.html" in req_files and "index.html" not in extracted_base:
        m_doc = re.search(r"(<!DOCTYPE\s+html\b.*?</html>)", clean_text, re.IGNORECASE | re.DOTALL)
        if m_doc:
            target_path = os.path.join(out_dir, "index.html")
            with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(m_doc.group(1).strip())
            extracted.append("index.html (doctype-fallback)")
        else:
            m_fenced = re.search(r"```html[ \t]*\r?\n(<!DOCTYPE\s+html\b.*)$", clean_text, re.IGNORECASE | re.DOTALL)
            if m_fenced:
                html_body = re.sub(r"\r?\n```\s*$", "", m_fenced.group(1)).strip()
            else:
                m_raw_doc = re.search(r"(<!DOCTYPE\s+html\b.*)$", clean_text, re.IGNORECASE | re.DOTALL)
                html_body = re.sub(r"\r?\n```\s*$", "", m_raw_doc.group(1)).strip() if m_raw_doc else ""
            if html_body:
                target_path = os.path.join(out_dir, "index.html")
                with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(html_body)
                extracted.append("index.html (fallback-truncated-html)")

    return extracted


def check_extraction_completeness(out_dir: str, task_spec: dict, extracted_files: list[str]) -> dict[str, object]:
    """Verify required file completeness and structural HTML closure (catches truncated deliverables)."""
    req_files = [os.path.basename(f) for f in task_spec.get("required_files", [])]
    missing_files: list[str] = []
    for rf in req_files:
        p = os.path.join(out_dir, rf)
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            missing_files.append(rf)

    html_structurally_complete = True
    if "index.html" in req_files:
        idx_path = os.path.join(out_dir, "index.html")
        if os.path.exists(idx_path):
            try:
                with open(idx_path, "r", encoding="utf-8", errors="replace") as fh:
                    html_txt = fh.read()
                html_lower = html_txt.lower()
                html_structurally_complete = ("</html>" in html_lower) and ("</body>" in html_lower)
            except Exception:
                html_structurally_complete = False
        else:
            html_structurally_complete = False

    used_truncated_fallback = any("truncated" in f or "fallback" in f for f in extracted_files)
    return {
        "all_required_files_present": len(missing_files) == 0,
        "missing_required_files": missing_files,
        "html_structurally_complete": html_structurally_complete,
        "used_truncated_fallback": used_truncated_fallback,
        "deliverable_complete": (len(missing_files) == 0) and html_structurally_complete,
    }


def reextract_task(model_slug: str, task_spec: dict) -> dict | None:
    """Re-run file extraction offline on an existing raw.md and refresh meta.json."""
    tid = task_spec["id"]
    out_dir = os.path.join(RUNS_DIR, model_slug, tid)
    raw_path = os.path.join(out_dir, "raw.md")
    meta_path = os.path.join(out_dir, "meta.json")
    if not os.path.exists(raw_path) or os.path.getsize(raw_path) == 0:
        return None
    with open(raw_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    extracted = extract_files_from_raw(content, out_dir, task_spec)
    completeness = check_extraction_completeness(out_dir, task_spec, extracted)
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
    meta["extracted_files"] = extracted
    meta.update(completeness)
    with open(meta_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
    print(
        f"[REEXTRACT] {model_slug} / {tid} -> files={extracted} "
        f"complete={completeness['deliverable_complete']}"
    )
    return meta


def merge_run_summary(model_slug: str, new_results: list[dict], all_tasks: list[dict]) -> str:
    """Merge new task meta dicts into run_summary.json ordered by tasks.json."""
    out_summary = os.path.join(RUNS_DIR, model_slug, "run_summary.json")
    by_tid: dict[str, dict] = {}
    if os.path.exists(out_summary):
        try:
            with open(out_summary, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
            if isinstance(existing, list):
                for item in existing:
                    if isinstance(item, dict) and item.get("task"):
                        by_tid[str(item["task"])] = item
        except Exception:
            pass
    for item in new_results:
        if isinstance(item, dict) and item.get("task"):
            by_tid[str(item["task"])] = item
    ordered = [by_tid[t["id"]] for t in all_tasks if t["id"] in by_tid]
    with open(out_summary, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ordered, fh, indent=2, ensure_ascii=False)
    return out_summary


def run_task(
    endpoint: str,
    model_slug: str,
    model_id: str,
    task_spec: dict,
    reasoning_budget: int = 4000,
    max_tokens: int = 28000,
    temperature: float = DEFAULT_TEMPERATURE,
    top_k: int = DEFAULT_TOP_K,
    top_p: float = DEFAULT_TOP_P,
    min_p: float = DEFAULT_MIN_P,
    dry_multiplier: float = DEFAULT_DRY_MULTIPLIER,
    dry_base: float = DEFAULT_DRY_BASE,
    dry_allowed_length: int = DEFAULT_DRY_ALLOWED_LENGTH,
    dry_penalty_last_n: int = DEFAULT_DRY_PENALTY_LAST_N,
    dry_sequence_breakers: list[str] | tuple[str, ...] | None = DEFAULT_DRY_SEQUENCE_BREAKERS,
    repeat_last_n: int = DEFAULT_REPEAT_LAST_N,
    repeat_penalty: float = DEFAULT_REPEAT_PENALTY,
    frequency_penalty: float = DEFAULT_FREQUENCY_PENALTY,
    presence_penalty: float = DEFAULT_PRESENCE_PENALTY,
    logit_bias_tokens: list[int] | tuple[int, ...] | None = None,
    eos_logit_bias: float = DEFAULT_EOS_LOGIT_BIAS,
    api_key: str = "local",
    force: bool = False,
) -> dict:
    assert_local_endpoint(endpoint)
    tid = task_spec["id"]
    out_dir = os.path.join(RUNS_DIR, model_slug, tid)
    os.makedirs(out_dir, exist_ok=True)
    meta_path = os.path.join(out_dir, "meta.json")
    raw_path = os.path.join(out_dir, "raw.md")

    if not force and os.path.exists(raw_path) and os.path.getsize(raw_path) > 0 and os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as fh:
            prev_meta = json.load(fh)
        if prev_meta.get("status") != "error":
            print(f"[SKIP] {model_slug} / {tid} already exists.")
            return prev_meta

    if task_spec["modality"] == "vision":
        ref_rel = task_spec["ref_image"]
        ref_abs = os.path.join(SUITE_DIR, ref_rel)
        with open(ref_abs, "rb") as img_f:
            b64_img = base64.b64encode(img_f.read()).decode("ascii")
        user_content = [
            {"type": "text", "text": task_spec["prompt"]},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
        ]
    else:
        user_content = task_spec["prompt"]

    payload: dict = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": task_spec["system_prompt"]},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
        "top_k": top_k,
        "top_p": top_p,
        "min_p": min_p,
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
    bias_list = [int(x) for x in logit_bias_tokens] if logit_bias_tokens else []
    if bias_list:
        payload["logit_bias"] = [[tid_tok, False] for tid_tok in bias_list]
        if eos_logit_bias != 0.0 and DEFAULT_EOS_TOKEN_ID not in bias_list:
            payload["logit_bias"].append([DEFAULT_EOS_TOKEN_ID, eos_logit_bias])
    if dry_multiplier > 0.0 and dry_penalty_last_n > 0:
        payload["dry_multiplier"] = dry_multiplier
        payload["dry_base"] = dry_base
        payload["dry_allowed_length"] = dry_allowed_length
        payload["dry_penalty_last_n"] = dry_penalty_last_n
        if dry_sequence_breakers:
            payload["dry_sequence_breakers"] = list(dry_sequence_breakers)
    if repeat_last_n > 0 and (
        repeat_penalty != 1.0 or frequency_penalty != 0.0 or presence_penalty != 0.0
    ):
        payload["repeat_last_n"] = repeat_last_n
        payload["repeat_penalty"] = repeat_penalty
        payload["frequency_penalty"] = frequency_penalty
        payload["presence_penalty"] = presence_penalty

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    print(
        f"[START] {model_slug} ({model_id}) -> {tid} "
        f"(reasoning_budget={reasoning_budget}, temp={temperature}, min_p={min_p}, "
        f"dry={dry_multiplier}/len={dry_allowed_length}/n={dry_penalty_last_n}, "
        f"rep={repeat_penalty}/pres={presence_penalty}, eos_bias={eos_logit_bias}) ..."
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=2700) as resp:
            resp_bytes = resp.read()
        elapsed = round(time.perf_counter() - t0, 2)
        data = json.loads(resp_bytes.decode("utf-8"))
    except Exception as e:
        elapsed = round(time.perf_counter() - t0, 2)
        meta = {
            "model_slug": model_slug,
            "model_id": model_id,
            "task": tid,
            "status": "error",
            "error": str(e),
            "elapsed_sec": elapsed,
        }
        with open(meta_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
        print(f"[ERROR] {model_slug} / {tid}: {e} in {elapsed}s")
        return meta

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    reasoning_text = msg.get("reasoning_content") or msg.get("reasoning") or ""

    if not reasoning_text and "<think>" in content and "</think>" in content:
        m_th = re.search(r"<think>(.*?)</think>", content, flags=re.DOTALL)
        if m_th:
            reasoning_text = m_th.group(1).strip()
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    with open(raw_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    if reasoning_text:
        with open(os.path.join(out_dir, "reasoning.md"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(reasoning_text)

    extracted_files = extract_files_from_raw(content, out_dir, task_spec)
    orig_dir = os.path.join(out_dir, "orig")
    os.makedirs(orig_dir, exist_ok=True)
    for req_f in task_spec.get("required_files", []):
        bname = os.path.basename(req_f)
        src_p = os.path.join(out_dir, bname)
        dst_p = os.path.join(orig_dir, bname)
        if os.path.exists(src_p):
            with open(src_p, "r", encoding="utf-8", errors="replace") as rf_in:
                raw_f_txt = rf_in.read()
            with open(dst_p, "w", encoding="utf-8", newline="\n") as rf_out:
                rf_out.write(raw_f_txt)
    completeness = check_extraction_completeness(out_dir, task_spec, extracted_files)
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
        "model_id": model_id,
        "task": tid,
        "endpoint": endpoint,
        "temperature": temperature,
        "top_k": top_k,
        "top_p": top_p,
        "min_p": min_p,
        "dry_multiplier": dry_multiplier,
        "dry_base": dry_base,
        "dry_allowed_length": dry_allowed_length,
        "dry_penalty_last_n": dry_penalty_last_n,
        "dry_sequence_breakers": list(dry_sequence_breakers)
        if (dry_multiplier > 0.0 and dry_penalty_last_n > 0 and dry_sequence_breakers)
        else [],
        "repeat_last_n": repeat_last_n,
        "repeat_penalty": repeat_penalty,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
        "max_tokens": max_tokens,
        "reasoning_budget": reasoning_budget,
        "logit_bias_tokens": bias_list,
        "eos_logit_bias": eos_logit_bias,
        "server_cli_logit_bias_preserved": not bool(bias_list),
        "finish_reason": choice.get("finish_reason"),
        "elapsed_sec": elapsed,
        "tok_per_sec": tok_per_sec,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": usage.get("total_tokens", prompt_tokens + completion_tokens),
            "cost_usd": 0.0,
        },
        "content_chars": len(content),
        "reasoning_chars": len(reasoning_text),
        "extracted_files": extracted_files,
        **completeness,
    }
    with open(meta_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print(
        f"[DONE] {model_slug} / {tid} in {elapsed}s ({tok_per_sec} tok/s) | "
        f"comp={completion_tokens} | files={extracted_files} | complete={completeness['deliverable_complete']}"
    )
    return meta


def main():
    parser = argparse.ArgumentParser(description="SmartLLM Offline Eval Suite Runner (Local Endpoints Only)")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument("--model-slug", required=True, help="Output folder slug under eval/suite/runs/")
    parser.add_argument("--model-id", default="local-model", help="Model identifier sent in JSON payload")
    parser.add_argument("--reasoning-budget", type=int, default=4000)
    parser.add_argument("--max-tokens", type=int, default=28000)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P)
    parser.add_argument("--min-p", type=float, default=DEFAULT_MIN_P)
    parser.add_argument("--dry-multiplier", type=float, default=DEFAULT_DRY_MULTIPLIER)
    parser.add_argument("--dry-base", type=float, default=DEFAULT_DRY_BASE)
    parser.add_argument("--dry-allowed-length", type=int, default=DEFAULT_DRY_ALLOWED_LENGTH)
    parser.add_argument("--dry-penalty-last-n", type=int, default=DEFAULT_DRY_PENALTY_LAST_N)
    parser.add_argument("--repeat-last-n", type=int, default=DEFAULT_REPEAT_LAST_N)
    parser.add_argument("--repeat-penalty", type=float, default=DEFAULT_REPEAT_PENALTY)
    parser.add_argument("--frequency-penalty", type=float, default=DEFAULT_FREQUENCY_PENALTY)
    parser.add_argument("--presence-penalty", type=float, default=DEFAULT_PRESENCE_PENALTY)
    parser.add_argument("--eos-logit-bias", type=float, default=DEFAULT_EOS_LOGIT_BIAS)
    parser.add_argument(
        "--logit-bias-tokens",
        type=int,
        nargs="*",
        default=None,
        help="Optional HTTP logit_bias token IDs (default: empty/omitted per frozen donor sampler config)",
    )
    parser.add_argument("--reextract", action="store_true", help="Re-run offline extraction on existing raw.md files")
    parser.add_argument("--tasks", nargs="*", help="Optional subset of task IDs (e.g. t1 t2 t3)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    with open(TASKS_JSON, "r", encoding="utf-8") as fh:
        all_tasks = json.load(fh)["tasks"]

    selected = [t for t in all_tasks if not args.tasks or t["id"] in args.tasks]
    results = []
    if args.reextract:
        for t in selected:
            res = reextract_task(args.model_slug, t)
            if res is not None:
                results.append(res)
    else:
        assert_local_endpoint(args.endpoint)
        bias_toks = args.logit_bias_tokens if args.logit_bias_tokens is not None else None
        for t in selected:
            res = run_task(
                endpoint=args.endpoint,
                model_slug=args.model_slug,
                model_id=args.model_id,
                task_spec=t,
                reasoning_budget=args.reasoning_budget,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                top_k=args.top_k,
                top_p=args.top_p,
                min_p=args.min_p,
                dry_multiplier=args.dry_multiplier,
                dry_base=args.dry_base,
                dry_allowed_length=args.dry_allowed_length,
                dry_penalty_last_n=args.dry_penalty_last_n,
                dry_sequence_breakers=DEFAULT_DRY_SEQUENCE_BREAKERS,
                repeat_last_n=args.repeat_last_n,
                repeat_penalty=args.repeat_penalty,
                frequency_penalty=args.frequency_penalty,
                presence_penalty=args.presence_penalty,
                logit_bias_tokens=bias_toks,
                eos_logit_bias=args.eos_logit_bias,
                force=args.force,
            )
            results.append(res)

    out_summary = merge_run_summary(args.model_slug, results, all_tasks)
    print(f"Saved run summary to {out_summary}")


if __name__ == "__main__":
    main()
