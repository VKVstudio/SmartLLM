import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SUITE_DIR = r"D:\projects\SmartLLM\eval\suite"
TASKS_JSON = os.path.join(SUITE_DIR, "tasks.json")
RUNS_DIR = os.path.join(SUITE_DIR, "runs")


def assert_local_endpoint(url: str) -> None:
    if not (url.startswith("http://127.0.0.1") or url.startswith("http://localhost")):
        raise RuntimeError(
            f"EXTERNAL API FORBIDDEN BY PROJECT RULES (AGENTS.md Section 3): {url}. "
            "Only local 127.0.0.1 / localhost endpoints are permitted."
        )


def extract_files_from_raw(raw_text: str, out_dir: str, task_spec: dict) -> list[str]:
    """Extract files preceded by FILE: <name> (with or without fenced code blocks)."""
    # Strip <think>...</think> block if inline in content
    clean_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
    extracted = []

    # 1. Slice between consecutive FILE: <name> headers and strip only outer code fences
    # (prevents internal markdown code fences in DESIGN.md / llms.txt from truncating extraction)
    plain_headers = list(
        re.finditer(r"(?:^|\n)[ \t]*[`*#\-]*[ \t]*FILE:[ \t]*`?([A-Za-z0-9_.\-]+)`?[ `*:\t]*\r?\n", clean_text)
    )
    if plain_headers:
        for idx, m in enumerate(plain_headers):
            fname_clean = os.path.basename(m.group(1).strip())
            start_pos = m.end()
            end_pos = plain_headers[idx + 1].start() if idx + 1 < len(plain_headers) else len(clean_text)
            code = clean_text[start_pos:end_pos].strip("\r\n")
            code = re.sub(r"^```[^\r\n]*\r?\n", "", code)
            code = re.sub(r"\r?\n```\s*$", "", code)
            if not fname_clean:
                continue
            target_path = os.path.join(out_dir, fname_clean)
            with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(code)
            extracted.append(fname_clean)
        return extracted

    # 3. Single-file fallback for Vision-to-Code (index.html) or TypeScript (dag.ts)
    req_files = task_spec.get("required_files", [])
    if len(req_files) == 1:
        default_file = req_files[0]
        fallback = re.search(r"```(?:html|typescript|ts)?\r?\n(.*?)(?:\r?\n```|$)", clean_text, re.DOTALL)
        if fallback:
            target_path = os.path.join(out_dir, default_file)
            with open(target_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(fallback.group(1))
            extracted.append(f"{default_file} (fallback-fenced)")
    return extracted


def run_task(
    endpoint: str,
    model_slug: str,
    model_id: str,
    task_spec: dict,
    reasoning_budget: int = 4000,
    max_tokens: int = 20000,
    temperature: float = 0.6,
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
        print(f"[SKIP] {model_slug} / {tid} already exists.")
        with open(meta_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

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

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": task_spec["system_prompt"]},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "reasoning_budget_tokens": reasoning_budget,
        "reasoning_budget": reasoning_budget,
        "thinking_budget": reasoning_budget,
        "chat_template_kwargs": {
            "enable_thinking": reasoning_budget > 0,
            "thinking_budget": reasoning_budget,
        },
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    print(f"[START] {model_slug} ({model_id}) -> {tid} (reasoning_budget={reasoning_budget}) ...")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
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

    # If model emitted <think>...</think> inside content, split it cleanly
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
    usage = data.get("usage") or {}
    timings = data.get("timings") or {}
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
    tok_per_sec = timings.get("predicted_per_second") or (
        round(completion_tokens / elapsed, 2) if elapsed > 0 and completion_tokens > 0 else None
    )

    meta = {
        "model_slug": model_slug,
        "model_id": model_id,
        "task": tid,
        "endpoint": endpoint,
        "temperature": temperature,
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
            "cost_usd": 0.0,
        },
        "content_chars": len(content),
        "reasoning_chars": len(reasoning_text),
        "extracted_files": extracted_files,
    }
    with open(meta_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print(
        f"[DONE] {model_slug} / {tid} in {elapsed}s ({tok_per_sec} tok/s) | "
        f"comp={completion_tokens} | files={extracted_files}"
    )
    return meta


def main():
    parser = argparse.ArgumentParser(description="SmartLLM Offline Eval Suite Runner (Local Endpoints Only)")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument("--model-slug", required=True, help="Output folder slug under eval/suite/runs/")
    parser.add_argument("--model-id", default="local-model", help="Model identifier sent in JSON payload")
    parser.add_argument("--reasoning-budget", type=int, default=4000)
    parser.add_argument("--max-tokens", type=int, default=20000)
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--tasks", nargs="*", help="Optional subset of task IDs (e.g. t1 t2 t3)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    assert_local_endpoint(args.endpoint)
    with open(TASKS_JSON, "r", encoding="utf-8") as fh:
        all_tasks = json.load(fh)["tasks"]

    selected = [t for t in all_tasks if not args.tasks or t["id"] in args.tasks]
    results = []
    for t in selected:
        res = run_task(
            endpoint=args.endpoint,
            model_slug=args.model_slug,
            model_id=args.model_id,
            task_spec=t,
            reasoning_budget=args.reasoning_budget,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            force=args.force,
        )
        results.append(res)

    out_summary = os.path.join(RUNS_DIR, args.model_slug, "run_summary.json")
    with open(out_summary, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print(f"Saved run summary to {out_summary}")


if __name__ == "__main__":
    main()
