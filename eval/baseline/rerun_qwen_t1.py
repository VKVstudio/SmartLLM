import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request

from run_eval import BASE_DIR, MODELS, SYSTEM_PROMPT, T1_PROMPT, extract_files_from_raw

MODEL_CFG = MODELS[0]  # qwen/qwen3.8-flash


def main():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    out_dir = os.path.join(BASE_DIR, "qwen3.8-flash", "t1")
    os.makedirs(out_dir, exist_ok=True)

    # Backup attempt 1 artifacts without deleting anything
    for src_name, dst_name in [
        ("raw.md", "raw_attempt1_unbounded.md"),
        ("meta.json", "meta_attempt1_unbounded.json"),
        ("index.html", "index_attempt1_unbounded.html"),
    ]:
        src_p = os.path.join(out_dir, src_name)
        dst_p = os.path.join(out_dir, dst_name)
        if os.path.exists(src_p) and not os.path.exists(dst_p):
            shutil.copy2(src_p, dst_p)

    payload = {
        "model": MODEL_CFG["id"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": T1_PROMPT},
        ],
        "temperature": MODEL_CFG["temperature"],
        "max_tokens": 64000,
        "reasoning": {"effort": "low"},
        "include_reasoning": True,
        "usage": {"include": True},
    }

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://smartllm.local",
            "X-Title": "SmartLLM Donor Baseline Eval",
        },
        method="POST",
    )

    print(f"[START] {MODEL_CFG['id']} -> t1 (max_tokens=64000, reasoning.effort=low) ...", flush=True)
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as resp:
        resp_bytes = resp.read()
    elapsed = round(time.perf_counter() - t0, 2)
    data = json.loads(resp_bytes.decode("utf-8"))

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    reasoning_text = msg.get("reasoning") or ""
    finish_reason = choice.get("finish_reason")
    native_finish_reason = choice.get("native_finish_reason")
    usage = data.get("usage") or {}

    raw_path = os.path.join(out_dir, "raw.md")
    with open(raw_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)

    extracted_files = extract_files_from_raw(content, out_dir, "t1")

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
    reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
    calc_cost = round(
        (prompt_tokens / 1_000_000.0) * MODEL_CFG["price_input_per_1m"]
        + (completion_tokens / 1_000_000.0) * MODEL_CFG["price_output_per_1m"],
        6,
    )
    reported_cost = usage.get("cost", calc_cost)

    meta = {
        "model_id": MODEL_CFG["id"],
        "hugging_face_id": MODEL_CFG["hugging_face_id"],
        "model_slug": MODEL_CFG["slug"],
        "task": "t1",
        "provider": data.get("provider", MODEL_CFG["expected_provider"]),
        "precision": MODEL_CFG["precision"],
        "temperature": MODEL_CFG["temperature"],
        "max_tokens": 64000,
        "reasoning": {"effort": "low"},
        "price_input_per_1m_usd": MODEL_CFG["price_input_per_1m"],
        "price_output_per_1m_usd": MODEL_CFG["price_output_per_1m"],
        "finish_reason": finish_reason,
        "native_finish_reason": native_finish_reason,
        "truncated": finish_reason == "length",
        "elapsed_sec": elapsed,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": total_tokens,
            "cost_usd": reported_cost,
            "calculated_cost_usd": calc_cost,
            "raw_usage": usage,
        },
        "content_chars": len(content),
        "reasoning_chars": len(reasoning_text),
        "extracted_files": extracted_files,
        "openrouter_id": data.get("id"),
    }

    meta_path = os.path.join(out_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print(
        f"[DONE] {MODEL_CFG['id']} / t1 in {elapsed}s | "
        f"finish={finish_reason} | prompt={prompt_tokens} comp={completion_tokens} (reas={reasoning_tokens}) | "
        f"cost=${reported_cost} | files={extracted_files}",
        flush=True,
    )


if __name__ == "__main__":
    main()
