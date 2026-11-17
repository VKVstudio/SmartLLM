#!/usr/bin/env python3
"""Zero-CuPy Wave 3 Stage C Runner (Quantize + GSQ Q2_0 Splice + Generation & KLD Gates).

Runs exclusively via CPU/GGUF helpers and native C++ llama.cpp subprocesses
(llama-server, llama-quantize, llama-perplexity) WITHOUT importing cupy or transformers,
eliminating CUDA allocator / CuPy teardown segfaults between Stage B and Stage C.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.v2.assemble_gguf import (  # noqa: E402
    VARIANT_SPECS,
    QuantVariantSpec,
    check_quantize_log_for_missing_imatrix,
    run_llama_quantize_variant,
    splice_gsq_q2_0_into_gguf,
    verify_bf16_gguf_complete_marker,
)
from scripts.v2.common_io import (  # noqa: E402
    REPO_ROOT,
    RUNS_DIR,
    SCRATCH_DIR,
    STAGE_DIR,
    assert_post_write_free_gib,
    assert_zero_swap_and_mem,
    capture_v2_swap_baseline,
    drop_file_page_cache,
    evict_stage_dir_page_cache,
)
from scripts.v2.prequant_gate import (  # noqa: E402
    audit_10prompt_generations,
    run_10prompt_batched_server_generation_gate,
    run_postquant_kld_gate_via_llama_perplexity,
)


def read_valid_kld_info(path: Path) -> Optional[Dict[str, Any]]:
    """Validate llama-perplexity _logits_ .kld header and exact file byte length."""
    if not path.is_file() or path.stat().st_size < 20:
        return None
    with open(path, "rb") as kf:
        hdr = kf.read(20)
    if len(hdr) < 20 or hdr[:8] != b"_logits_":
        return None
    n_ctx_i, n_vocab_i, n_chunk_i = struct.unpack("<Iii", hdr[8:20])
    if n_ctx_i < 8 or n_vocab_i <= 0 or n_chunk_i <= 0:
        return None
    n_eval = n_ctx_i - 1 - (n_ctx_i // 2)
    nv = 2 * ((n_vocab_i + 1) // 2) + 4
    expected_bytes = 20 + 4 * n_ctx_i * n_chunk_i + n_chunk_i * n_eval * nv * 2
    if int(path.stat().st_size) != expected_bytes:
        return None
    return {
        "kld_path": str(path),
        "n_ctx": int(n_ctx_i),
        "n_vocab": int(n_vocab_i),
        "n_chunk": int(n_chunk_i),
        "eval_tokens": int(n_chunk_i * n_eval),
        "bytes": int(expected_bytes),
    }


def _read_manifest_counts(stage_dir: Path) -> Dict[str, int]:
    """Load calibration/eval sequence and token counts from init_states_manifest_c640.json."""
    manifest_candidates = sorted(stage_dir.glob("init_states_manifest_c*.json"))
    if not manifest_candidates:
        raise FileNotFoundError(f"Missing init_states_manifest_c*.json in {stage_dir}")
    manifest_path = stage_dir / "init_states_manifest_c640.json"
    if not manifest_path.is_file():
        manifest_path = manifest_candidates[-1]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]
    c_shape = files["c_h0"]["shape"]
    e_shape = files["e_h0"]["shape"]
    return {
        "calib_sequences": int(c_shape[0]),
        "calib_tokens": int(c_shape[1]),
        "eval_sequences": int(e_shape[0]),
        "eval_tokens": int(e_shape[1]),
    }


def _is_valid_final_marker(marker_path: Path, final_gguf_path: Path) -> Optional[Dict[str, Any]]:
    """Return parsed completion marker if final GGUF and its exact byte length match."""
    if not marker_path.is_file() or not final_gguf_path.is_file():
        return None
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        expected_bytes = int(marker["final_gguf_bytes"])
        if expected_bytes <= 0:
            return None
        if int(final_gguf_path.stat().st_size) != expected_bytes:
            return None
        return marker
    except Exception:
        return None


def run_stage_c_only(
    *,
    selector_name: str,
    variant_id: str,
    out_dir: Path = RUNS_DIR / "wave3",
    stage_dir: Path = STAGE_DIR / "wave3",
    scratch_dir: Path = SCRATCH_DIR,
    models_out_dir: Path = REPO_ROOT / "models",
    run_generation_gates: bool = True,
    skip_bf16_gen_gate: bool = False,
    allow_resume: bool = True,
    min_post_write_free_gib: float = 10.0,
) -> Dict[str, Any]:
    """Execute Wave 3 Stage C directly from verified Stage A/B disk artifacts."""
    spec: QuantVariantSpec = VARIANT_SPECS[variant_id]
    target_k = spec.target_k
    total_blocks = 49
    n_layers = 48

    out_dir = Path(out_dir)
    stage_dir = Path(stage_dir)
    scratch_dir = Path(scratch_dir)
    models_out_dir = Path(models_out_dir)
    overlays_dir = stage_dir / "overlays"
    out_dir.mkdir(parents=True, exist_ok=True)
    models_out_dir.mkdir(parents=True, exist_ok=True)

    swap_baseline = capture_v2_swap_baseline()
    evict_stage_dir_page_cache(stage_dir)

    print(
        f"[WAVE3][STAGE_C_ONLY] Start selector={selector_name} variant={variant_id} "
        f"K={target_k} (zero-CuPy orchestrator)",
        flush=True,
    )

    cos_list: List[float] = []
    for bid in range(total_blocks):
        report_path = out_dir / f"layer_{bid:02d}_report.json"
        if not report_path.is_file():
            raise FileNotFoundError(f"Missing layer report: {report_path}")
        if bid < n_layers:
            rep = json.loads(report_path.read_text(encoding="utf-8"))
            cos_list.append(float(rep["eval_cosine"]))

    prequant_gate_path = out_dir / "bf16_prequant_gate.json"
    if not prequant_gate_path.is_file():
        raise FileNotFoundError(f"Missing BF16 pre-quant gate JSON: {prequant_gate_path}")
    prequant_eval = json.loads(prequant_gate_path.read_text(encoding="utf-8"))

    en_kld_info = read_valid_kld_info(scratch_dir / "donor_eval_en.kld")
    ru_kld_info = read_valid_kld_info(scratch_dir / "donor_eval_ru.kld")
    if run_generation_gates and (en_kld_info is None or ru_kld_info is None):
        raise FileNotFoundError(
            f"Missing or corrupt donor eval KLD files in {scratch_dir}: "
            f"en={en_kld_info is not None}, ru={ru_kld_info is not None}"
        )

    imat_gguf_path = stage_dir / f"imatrix_v2_K{target_k}.gguf"
    if not imat_gguf_path.is_file() or imat_gguf_path.stat().st_size <= 100_000_000:
        raise FileNotFoundError(f"Missing or undersized imatrix GGUF: {imat_gguf_path}")

    bf16_gguf_path = scratch_dir / f"SmartLLM-v2-K{target_k}-BF16.gguf"
    if not verify_bf16_gguf_complete_marker(bf16_gguf_path, expected_target_k=target_k):
        raise FileNotFoundError(f"BF16 GGUF completion check failed for {bf16_gguf_path}")

    q2_files: Dict[int, Path] = {}
    for bid in range(total_blocks):
        q2_path = overlays_dir / f"blk.{bid}.ffn_down_exps.q2_0.bin"
        if not q2_path.is_file() or q2_path.stat().st_size <= 0:
            raise FileNotFoundError(f"Missing GSQ Q2_0 overlay: {q2_path}")
        q2_files[bid] = q2_path

    counts = _read_manifest_counts(stage_dir)

    drop_file_page_cache(bf16_gguf_path)
    drop_file_page_cache(imat_gguf_path)
    if en_kld_info is not None:
        drop_file_page_cache(Path(en_kld_info["kld_path"]))
    if ru_kld_info is not None:
        drop_file_page_cache(Path(ru_kld_info["kld_path"]))

    bf16_gen_audit: Optional[Dict[str, Any]] = None
    bf16_gen_json = out_dir / "bf16_prequant_generation_gate.json"
    if skip_bf16_gen_gate:
        bf16_gen_audit = {
            "passed": None,
            "skipped_nonfatal_bf16_zram_guard": True,
            "reason": (
                "180 GiB BF16 GGUF holds 140.63 GiB CPU BF16 experts; task-2488 verified clean "
                "llama-server load (9.141 GiB VRAM <= 9.20 GiB, 0 disk swap, 0 PLE RSS, 23.043 GiB "
                "MemAvailable) before vm.swappiness=150 compressed 521.67 MiB into zram0 (>512 MiB cap). "
                "Skipped per OPUS 1.D2b.5 non-fatal BF16 rule & OPUS 4 single-breach guard; hard "
                "10-prompt gate runs on final V1 GGUF."
            ),
            "completed_prompts": 0,
            "expected_prompts": 10,
            "timed_out_partial": False,
            "task_2488_probe_telemetry": {
                "max_vram_gib": 9.141,
                "min_mem_avail_gib": 23.043,
                "disk_swap_used_kb": 0,
                "max_ple_rss_kb": 0,
                "max_proc_swap_kb": 108,
                "max_zram_orig_delta_mib": 521.668,
            },
        }
        with open(bf16_gen_json, "w", encoding="utf-8") as f:
            json.dump(bf16_gen_audit, f, indent=2, ensure_ascii=False)
        print("[WAVE3][BF16_GEN_GATE] skipped_nonfatal_bf16_zram_guard=True", flush=True)
    elif run_generation_gates:
        reuse_bf16_gen = False
        if allow_resume and bf16_gen_json.is_file():
            try:
                cached_bf16_gen = json.loads(bf16_gen_json.read_text(encoding="utf-8"))
                if int(cached_bf16_gen.get("completed_prompts") or 0) > 0:
                    bf16_gen_audit = cached_bf16_gen
                    reuse_bf16_gen = True
            except Exception:
                reuse_bf16_gen = False
        if not reuse_bf16_gen:
            bf16_gen_audit = run_10prompt_batched_server_generation_gate(
                gguf_path=bf16_gguf_path,
                max_new_tokens=128,
                n_parallel=10,
                n_gpu_layers=99,
                moe_cache_mib=0,
                moe_cache_cpu_share=0.0,
                ctx_per_slot=512,
                offload_output_to_cpu=True,
                auto_plan_bf16_vram=True,
                max_planned_vram_gib=9.20,
                soft_vram_cap_gib=9.85,
                wall_cap_sec=1800.0,
                allow_partial_on_timeout=True,
                non_fatal_on_server_error=True,
                server_log_path=out_dir / "bf16_prequant_server.log",
            )
            with open(bf16_gen_json, "w", encoding="utf-8") as f:
                json.dump(bf16_gen_audit, f, indent=2, ensure_ascii=False)
        print(
            f"[WAVE3][BF16_GEN_GATE] passed={bf16_gen_audit.get('passed')} "
            f"timed_out_partial={bf16_gen_audit.get('timed_out_partial')} "
            f"error={bf16_gen_audit.get('error')} "
            f"completed={bf16_gen_audit.get('completed_prompts')}/{bf16_gen_audit.get('expected_prompts')} "
            f"elapsed={bf16_gen_audit.get('elapsed_sec')}s",
            flush=True,
        )

    final_gguf_path = models_out_dir / f"SmartLLM-v2-K{target_k}-{spec.variant_id}.gguf"
    final_marker_path = out_dir / f"SmartLLM-v2-K{target_k}-{spec.variant_id}.gguf.complete.json"
    existing_marker = _is_valid_final_marker(final_marker_path, final_gguf_path) if allow_resume else None

    if existing_marker is not None:
        splice_info = existing_marker.get("gsq_splice_info")
        print(
            f"[WAVE3][FINAL_GGUF] Reusing verified complete {final_gguf_path} "
            f"({final_gguf_path.stat().st_size / (1024**3):.3f} GiB)",
            flush=True,
        )
    else:
        quant_log_path = final_gguf_path.with_suffix(final_gguf_path.suffix + ".quantize.log")
        reuse_quant_output = False
        if allow_resume and final_gguf_path.is_file() and final_gguf_path.stat().st_size > 50_000_000_000 and quant_log_path.is_file():
            try:
                qlog_txt = quant_log_path.read_text(encoding="utf-8", errors="replace")
                if "llama_quantize:    total time =" in qlog_txt:
                    check_quantize_log_for_missing_imatrix(qlog_txt)
                    reuse_quant_output = True
            except Exception:
                reuse_quant_output = False

        if reuse_quant_output:
            print(
                f"[WAVE3][QUANT_REUSE] Reusing completed pre-splice llama-quantize output "
                f"{final_gguf_path} ({final_gguf_path.stat().st_size / (1024**3):.3f} GiB)",
                flush=True,
            )
        else:
            expected_final_bytes = int(60_500_000_000)
            if min_post_write_free_gib > 0.0:
                assert_post_write_free_gib(
                    final_gguf_path,
                    expected_final_bytes,
                    min_free_gib=min_post_write_free_gib,
                    label="final_quantized_gguf",
                )
            run_llama_quantize_variant(bf16_gguf_path, final_gguf_path, imat_gguf_path, spec)

        splice_info = None
        if spec.use_gsq_q2_0_splice:
            splice_info = splice_gsq_q2_0_into_gguf(
                final_gguf_path,
                q2_files,
                verify_with_libggml=True,
                ref_bf16_gguf=bf16_gguf_path,
            )
        marker_payload = {
            "final_gguf_path": str(final_gguf_path),
            "final_gguf_bytes": int(final_gguf_path.stat().st_size),
            "gsq_splice_info": splice_info,
            "completed_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with open(final_marker_path, "w", encoding="utf-8") as f:
            json.dump(marker_payload, f, indent=2)
        print(
            f"[WAVE3][FINAL_GGUF] Ready at {final_gguf_path} "
            f"({final_gguf_path.stat().st_size / (1024**3):.3f} GiB)",
            flush=True,
        )

    final_gen_audit: Optional[Dict[str, Any]] = None
    postquant_kl_eval: Optional[Dict[str, Any]] = None
    final_n_cpu_moe = 43 if target_k == 320 else 48
    final_moe_cache_mib = 1536 if target_k == 320 else 4096
    kld_n_cpu_moe = 38 if target_k == 320 else 48
    kld_moe_cache_mib = 512 if target_k == 320 else 4096
    final_gen_json = out_dir / "final_postquant_generation_gate.json"
    if run_generation_gates:
        drop_file_page_cache(bf16_gguf_path)
        drop_file_page_cache(final_gguf_path)
        reused_final_gen = False
        if allow_resume and final_gen_json.is_file():
            try:
                cached_fg = json.loads(final_gen_json.read_text(encoding="utf-8"))
                if int(cached_fg.get("completed_prompts") or 0) == 10 and cached_fg.get("raw_outputs"):
                    re_audit = audit_10prompt_generations(cached_fg["raw_outputs"])
                    cached_fg["passed"] = re_audit["passed"]
                    cached_fg["total_8gram_x3_loops"] = re_audit["total_8gram_x3_loops"]
                    cached_fg["min_ru_cyrillic_ratio"] = re_audit["min_ru_cyrillic_ratio"]
                    cached_fg["prompts"] = re_audit["prompts"]
                    with open(final_gen_json, "w", encoding="utf-8") as f:
                        json.dump(cached_fg, f, indent=2, ensure_ascii=False)
                    final_gen_audit = cached_fg
                    reused_final_gen = True
                    print(
                        f"[WAVE3][FINAL_GEN_REUSE] Re-audited existing 10/10 outputs -> "
                        f"passed={final_gen_audit.get('passed')} "
                        f"loops={final_gen_audit.get('total_8gram_x3_loops')} "
                        f"min_ru_cyr={final_gen_audit.get('min_ru_cyrillic_ratio')}",
                        flush=True,
                    )
            except Exception:
                reused_final_gen = False
        if not reused_final_gen:
            final_gen_audit = run_10prompt_batched_server_generation_gate(
                gguf_path=final_gguf_path,
                max_new_tokens=256,
                n_parallel=10,
                n_gpu_layers=99,
                n_cpu_moe=final_n_cpu_moe,
                moe_cache_mib=final_moe_cache_mib,
                moe_cache_cpu_share=0.15,
                ctx_per_slot=512,
                offload_output_to_cpu=False,
                wall_cap_sec=1800.0,
                allow_partial_on_timeout=False,
                server_log_path=out_dir / "final_postquant_server.log",
            )
            with open(final_gen_json, "w", encoding="utf-8") as f:
                json.dump(final_gen_audit, f, indent=2, ensure_ascii=False)
            print(
                f"[WAVE3][FINAL_GEN_GATE] passed={final_gen_audit.get('passed')} "
                f"loops={final_gen_audit.get('total_8gram_x3_loops')} "
                f"min_ru_cyr={final_gen_audit.get('min_ru_cyrillic_ratio')} "
                f"elapsed={final_gen_audit.get('elapsed_sec')}s",
                flush=True,
            )

        drop_file_page_cache(bf16_gguf_path)
        drop_file_page_cache(final_gguf_path)
        if en_kld_info is not None and ru_kld_info is not None:
            postquant_kl_eval = run_postquant_kld_gate_via_llama_perplexity(
                gguf_path=final_gguf_path,
                en_kld_path=Path(en_kld_info["kld_path"]),
                en_n_ctx=int(en_kld_info["n_ctx"]),
                en_eval_tokens=int(en_kld_info["eval_tokens"]),
                ru_kld_path=Path(ru_kld_info["kld_path"]),
                ru_n_ctx=int(ru_kld_info["n_ctx"]),
                ru_eval_tokens=int(ru_kld_info["eval_tokens"]),
                layer_cosines=cos_list,
                n_cpu_moe=kld_n_cpu_moe,
                moe_cache_mib=kld_moe_cache_mib,
            )
            postquant_kl_eval["escalate_to_opus_postquant_miss"] = bool(not postquant_kl_eval["passed"])
            with open(out_dir / "final_postquant_kl_gate.json", "w", encoding="utf-8") as f:
                json.dump(postquant_kl_eval, f, indent=2)
            print(f"[WAVE3][FINAL_KL_GATE] {json.dumps(postquant_kl_eval, sort_keys=True)}", flush=True)

    tel_end = assert_zero_swap_and_mem(swap_baseline)
    result = {
        "selector": selector_name,
        "variant_id": variant_id,
        "target_k": target_k,
        "calib_sequences": int(counts["calib_sequences"]),
        "calib_tokens": int(counts["calib_tokens"]),
        "eval_sequences": int(counts["eval_sequences"]),
        "eval_tokens": int(counts["eval_tokens"]),
        "resume_info": {"mode": "stage_c_only_zero_cupy", "resumed_from_layer": total_blocks},
        "telemetry": {
            "baseline_pswpout": int(swap_baseline.pswpout),
            "pswpout_delta": int(max(0, tel_end.pswpout - swap_baseline.pswpout)),
            "disk_swap_used_kb": int(tel_end.disk_swap_used_kb),
            "disk_swap_write_sectors_delta": int(
                max(0, tel_end.disk_swap_write_sectors - swap_baseline.disk_swap_write_sectors)
            ),
            "zram_orig_mib": round(tel_end.zram_orig_mib, 3),
            "zram_orig_delta_mib": round(max(0.0, tel_end.zram_orig_mib - swap_baseline.zram_orig_mib), 3),
            "end_mem_avail_gib": round(tel_end.mem_available_gib, 3),
        },
        "escalate_to_opus_prequant_miss": bool(prequant_eval.get("escalate_to_opus_prequant_miss", False)),
        "bf16_prequant_gate": prequant_eval,
        "bf16_prequant_generation_passed": bf16_gen_audit.get("passed") if bf16_gen_audit else None,
        "bf16_prequant_generation_timed_out_partial": bf16_gen_audit.get("timed_out_partial") if bf16_gen_audit else None,
        "final_generation_passed": final_gen_audit.get("passed") if final_gen_audit else None,
        "final_postquant_kl_gate": postquant_kl_eval,
        "bf16_gguf_path": str(bf16_gguf_path),
        "bf16_gguf_bytes": int(bf16_gguf_path.stat().st_size),
        "final_gguf_path": str(final_gguf_path),
        "final_gguf_bytes": int(final_gguf_path.stat().st_size),
        "gsq_splice_info": splice_info,
    }
    with open(out_dir / "wave3_summary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    if final_gen_audit is not None and not final_gen_audit.get("passed", False):
        raise RuntimeError(f"Final Quantized Generation Gate FAILED (hard gate): {final_gen_audit}")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="SmartLLM v2 Wave 3 Stage C Only (Zero-CuPy)")
    parser.add_argument("--selector", choices=["A2", "A3", "A4_prime"], required=True)
    parser.add_argument("--variant", choices=["V1", "V2", "V3", "V4"], required=True)
    parser.add_argument("--out-dir", type=Path, default=RUNS_DIR / "wave3")
    parser.add_argument("--stage-dir", type=Path, default=STAGE_DIR / "wave3")
    parser.add_argument("--scratch-dir", type=Path, default=SCRATCH_DIR)
    parser.add_argument("--models-out-dir", type=Path, default=REPO_ROOT / "models")
    parser.add_argument("--min-post-write-free-gib", type=float, default=10.0)
    parser.add_argument("--skip-gen-gates", action="store_true")
    parser.add_argument("--skip-bf16-gen-gate", action="store_true")
    args, _ignored = parser.parse_known_args()

    res = run_stage_c_only(
        selector_name=args.selector,
        variant_id=args.variant,
        out_dir=args.out_dir,
        stage_dir=args.stage_dir,
        scratch_dir=args.scratch_dir,
        models_out_dir=args.models_out_dir,
        run_generation_gates=not args.skip_gen_gates,
        skip_bf16_gen_gate=args.skip_bf16_gen_gate,
        min_post_write_free_gib=args.min_post_write_free_gib,
    )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
