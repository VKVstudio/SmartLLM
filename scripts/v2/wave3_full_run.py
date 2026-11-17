#!/usr/bin/env python3
"""Wave 3 Full 48L+MTP Closed-Loop Prune + C3 Heal + GSQ Q2_0 + GGUF Assembly Orchestrator.

Implements OPUS_MASTER_PLAN_V2.md §1.D1-D4, §1.D2b (Wave 2 Sign-Off), §2 WP-C1, and §3 Wave 3:
1. Resumable 48-layer + 1-MTP closed-loop ping-pong (`H^(l)_pruned` vs `H^(l)_donor`) across
   multi-mount zero-deletion staging (`--stage-dir` + `--pruned-stage-dir`) with `>= 10.0 GiB`
   post-write free-space assertions before every large write (`OPUS §1.D2b.4`).
2. Layer-4 throughput guard (`projected_49L_hours > 10.0` -> single-factor switch to 448 seqs,
   `OPUS §1.D2b.3`).
3. Inline C3 healing (`C1` router gate + `C2` expert scalar & shared-expert ridge), post-heal
   imatrix, and inline clean-room Dual-Sign GSQ+GPTQ `Q2_0` `down_exps` `.bin` export.
4. Streamed BF16 Pre-Quant Gate (`KL_EN <= 0.10`, `KL_RU <= 0.15`, `top1 >= 88% / 84%`,
   `cos(pruned, donor) >= 0.98` across all 48 layers); per `OPUS §1.D2b.2`, a pre-quant KL miss
   records `escalate_to_opus_prequant_miss: true` and continues to assembly + quant + gen gates.
5. Zero-safetensors streaming BF16 intermediate GGUF on `/mnt/windows/smartllm_scratch/`,
   true pre-quant `-np 10` batched `T=0` (`<= 128` tok, `60-min` cap) generation check on
   `bf16_gguf` (`OPUS §1.D2b.5`, no 71 GiB proxy), final `SmartLLM-v2-*.gguf` quantization,
   in-place `blk.{0..48}.ffn_down_exps.weight` GSQ `Q2_0` splicing + `libggml` verification,
   hard 10-prompt greedy generation gate (`<= 256` tok), and native `llama-perplexity --kl-divergence`
   Post-Quant KL/top-1 evaluation against exact 512E donor `.kld` files.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import struct
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if __name__ == "__main__" and "--stage-c-only" in sys.argv:
    sys.argv = [a for a in sys.argv if a != "--stage-c-only"]
    from scripts.v2.wave3_stage_c import main as _stage_c_main

    raise SystemExit(_stage_c_main())

import numpy as np
import torch
import torch.nn as nn

from scripts.v2.assemble_gguf import (
    REF_205E_GGUF,
    VARIANT_SPECS,
    LayerPruneHealOverlay,
    QuantVariantSpec,
    assemble_bf16_intermediate_gguf,
    run_llama_quantize_variant,
    splice_gsq_q2_0_into_gguf,
    verify_bf16_gguf_complete_marker,
    verify_imatrix_coverage_against_gguf,
)
from scripts.v2.common_io import (
    DEFAULT_GPU_RUNS_LOG,
    DONOR_DIR,
    REPO_ROOT,
    RUNS_DIR,
    SCRATCH_DIR,
    STAGE_DIR,
    LayerImatrixCollector,
    ResumablePingPong,
    append_gpu_resume_log,
    assert_post_write_free_gib,
    assert_zero_swap_and_mem,
    capture_v2_swap_baseline,
    compute_file_sha256_streaming,
    drop_file_page_cache,
    evict_stage_dir_page_cache,
    free_submodule_to_meta,
    materialize_submodule,
    read_linux_mem_telemetry,
    write_imatrix_gguf,
)
from scripts.v2.cupy_moe_backend import (
    CuPyLinearPatch,
    MoELayerWeights,
    PostHealStatsCollector,
    ReapHopeRcoAccumulator,
    forward_moe_v2,
    free_cupy_pools,
)
from scripts.v2.expert_selectors import (
    build_quota_locks,
    select_a2_quota_reap,
    select_a3_quota_hope,
    select_a4_prime_greedy_rco,
)
from scripts.v2.gsq_q2_0 import gsq_quantize_layer_down_exps
from scripts.v2.healing_c3 import heal_layer_c3
from scripts.v2.model_runner import (
    PreparedSample,
    SingleLayerContext,
    attach_non_moe_imatrix_hooks,
    build_mtp_decoder_config,
    load_text_cfg_and_index,
    prepare_jsonl_samples_and_initial_states,
    run_layer_resume_determinism_probe,
)
from scripts.v2.prequant_gate import (
    BF16_PREQUANT_THRESHOLDS,
    compute_cosine_similarity_batch,
    compute_kl_and_top1_from_hidden,
    compute_per_doc_kl_bootstrap_ci,
    evaluate_teacher_forced_gate,
    run_10prompt_batched_server_generation_gate,
    run_postquant_kld_gate_via_llama_perplexity,
    upload_2d_fp16_chunked_cupy,
    write_llama_kld_file,
)


def check_layer4_throughput_guard(
    layer_timings_sec: List[float],
    total_layers: int = 49,
    max_projected_hours: float = 10.0,
) -> Dict[str, Any]:
    """OPUS §1.D2b.3 & §2 WP-C1 guard: after 4 layers, check projected 49-layer wall time (<= 10.0 h)."""
    if not layer_timings_sec:
        return {"triggered": False, "projected_hours": 0.0}
    mean_sec = float(np.mean(layer_timings_sec))
    proj_hours = (mean_sec * float(total_layers)) / 3600.0
    return {
        "n_measured_layers": len(layer_timings_sec),
        "mean_layer_sec": round(mean_sec, 2),
        "projected_hours": round(proj_hours, 3),
        "limit_hours": float(max_projected_hours),
        "triggered": proj_hours > float(max_projected_hours),
        "fallback_calib_seqs": 448,
    }


def _select_experts_for_layer(
    selector_name: str,
    score_dict: Dict[str, Any],
    reap_acc: ReapHopeRcoAccumulator,
    target_k: int,
) -> np.ndarray:
    locks = build_quota_locks(score_dict)
    if selector_name == "A2":
        return select_a2_quota_reap(score_dict, target_k, locks=locks)
    if selector_name == "A3":
        return select_a3_quota_hope(score_dict, reap_acc.coact_matrix, target_k, locks=locks)
    if selector_name in ("A4_prime", "A4'"):
        assert reap_acc.rco_cache is not None
        return select_a4_prime_greedy_rco(reap_acc.rco_cache, score_dict, target_k, locks=locks)
    raise ValueError(f"Unknown selector_name: {selector_name!r}")


def _save_layer_overlay_and_q2(
    overlays_dir: Path,
    bid: int,
    overlay: LayerPruneHealOverlay,
    q2_packed: Optional[np.ndarray],
    min_free_gib: float = 10.0,
) -> None:
    overlays_dir.mkdir(parents=True, exist_ok=True)
    q2_bytes = int(np.ascontiguousarray(q2_packed, dtype=np.uint8).nbytes) if q2_packed is not None else 0
    if min_free_gib > 0.0:
        assert_post_write_free_gib(
            overlays_dir / f"blk.{bid}.ffn_down_exps.q2_0.bin",
            q2_bytes + 12 * 1024 * 1024,
            min_free_gib=min_free_gib,
            label=f"overlay_q2_blk{bid:02d}",
        )

    npz_tmp = overlays_dir / f"layer_{bid:02d}_overlay.tmp.npz"
    npz_final = overlays_dir / f"layer_{bid:02d}_overlay.npz"
    np.savez(
        npz_tmp,
        bid=np.int32(bid),
        keep_indices=overlay.keep_indices,
        w_gate_f32=overlay.w_gate_f32 if overlay.w_gate_f32 is not None else np.empty(0, dtype=np.float32),
        alpha_scales=overlay.alpha_scales if overlay.alpha_scales is not None else np.empty(0, dtype=np.float32),
        w_down_shexp_f32=overlay.w_down_shexp_f32 if overlay.w_down_shexp_f32 is not None else np.empty(0, dtype=np.float32),
    )
    os.replace(npz_tmp, npz_final)

    if q2_packed is not None:
        q2_path = overlays_dir / f"blk.{bid}.ffn_down_exps.q2_0.bin"
        q2_tmp = overlays_dir / f"blk.{bid}.ffn_down_exps.q2_0.bin.tmp"
        with open(q2_tmp, "wb") as bf:
            bf.write(np.ascontiguousarray(q2_packed, dtype=np.uint8).tobytes())
        os.replace(q2_tmp, q2_path)
        drop_file_page_cache(q2_path)


def _load_layer_overlay(overlays_dir: Path, bid: int) -> LayerPruneHealOverlay:
    d = np.load(overlays_dir / f"layer_{bid:02d}_overlay.npz")
    wg = d["w_gate_f32"]
    al = d["alpha_scales"]
    ws = d["w_down_shexp_f32"]
    return LayerPruneHealOverlay(
        bid=int(d["bid"]),
        keep_indices=d["keep_indices"].astype(np.int64),
        w_gate_f32=wg if wg.size > 0 else None,
        alpha_scales=al if al.size > 0 else None,
        w_down_shexp_f32=ws if ws.size > 0 else None,
    )


def _compute_calib_manifest_sha(
    calib_jsonl: Path,
    calib_samples_limit: int,
    max_seq_len: int,
    eval_jsonl: Path,
    eval_samples_limit: int,
) -> str:
    h = hashlib.sha256()
    h.update(compute_file_sha256_streaming(calib_jsonl, drop_cache=False).encode("ascii"))
    h.update(f"|c_lim={int(calib_samples_limit)}|msl={int(max_seq_len)}|".encode("ascii"))
    h.update(compute_file_sha256_streaming(eval_jsonl, drop_cache=False).encode("ascii"))
    h.update(f"|e_lim={int(eval_samples_limit)}".encode("ascii"))
    return h.hexdigest()


def _verify_init_states_manifest(
    manifest_path: Path,
    expected_calib_manifest_sha: str,
    c_e0_path: Path,
    c_h0_path: Path,
    e_h0_path: Path,
) -> bool:
    """OPUS §1.D2b.4: Reuse e0/h0 only if sha256 + shape + calib-manifest sha all match."""
    if not (manifest_path.is_file() and c_e0_path.is_file() and c_h0_path.is_file() and e_h0_path.is_file()):
        return False
    try:
        meta = json.loads(manifest_path.read_text(encoding="utf-8"))
        if meta.get("calib_manifest_sha") != expected_calib_manifest_sha:
            return False
        files_meta = meta.get("files", {})
        for p_key, p_obj in (("c_e0", c_e0_path), ("c_h0", c_h0_path), ("e_h0", e_h0_path)):
            fm = files_meta.get(p_key)
            if not isinstance(fm, dict):
                return False
            if int(p_obj.stat().st_size) != int(fm.get("bytes", -1)):
                return False
            if compute_file_sha256_streaming(p_obj) != str(fm.get("sha256", "")):
                return False
        return True
    except (OSError, ValueError, KeyError):
        return False


def _write_init_states_manifest(
    manifest_path: Path,
    calib_manifest_sha: str,
    c_e0_store: Any,
    c_h0_store: Any,
    e_h0_store: Any,
) -> None:
    payload = {
        "calib_manifest_sha": str(calib_manifest_sha),
        "files": {
            "c_e0": {
                "path": str(c_e0_store.bin_path),
                "bytes": int(c_e0_store.total_bytes),
                "shape": [int(len(c_e0_store.seq_lengths)), int(sum(c_e0_store.seq_lengths)), 1, int(c_e0_store.hidden_size)],
                "sha256": compute_file_sha256_streaming(c_e0_store.bin_path),
            },
            "c_h0": {
                "path": str(c_h0_store.bin_path),
                "bytes": int(c_h0_store.total_bytes),
                "shape": [int(len(c_h0_store.seq_lengths)), int(sum(c_h0_store.seq_lengths)), int(c_h0_store.hc_count), int(c_h0_store.hidden_size)],
                "sha256": compute_file_sha256_streaming(c_h0_store.bin_path),
            },
            "e_h0": {
                "path": str(e_h0_store.bin_path),
                "bytes": int(e_h0_store.total_bytes),
                "shape": [int(len(e_h0_store.seq_lengths)), int(sum(e_h0_store.seq_lengths)), int(e_h0_store.hc_count), int(e_h0_store.hidden_size)],
                "sha256": compute_file_sha256_streaming(e_h0_store.bin_path),
            },
        },
    }
    tmp_p = manifest_path.with_suffix(".tmp.json")
    tmp_p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_p, manifest_path)


def _slot_marker_is_clean(marker_path: Path) -> bool:
    if not marker_path.exists():
        return True
    txt = marker_path.read_text(encoding="utf-8", errors="replace").strip()
    return txt.startswith("clean")


def run_wave3_pipeline(
    selector_name: str,
    variant_id: str,
    calib_jsonl: Path,
    eval_jsonl: Path,
    out_dir: Path = RUNS_DIR / "wave3",
    stage_dir: Path = STAGE_DIR / "wave3",
    pruned_stage_dir: Optional[Path] = None,
    scratch_dir: Path = SCRATCH_DIR,
    models_out_dir: Path = REPO_ROOT / "models",
    donor_dir: Path = DONOR_DIR,
    backend: str = "cupy",
    calib_samples_limit: int = 640,
    eval_samples_limit: int = 128,
    max_seq_len: int = 2048,
    run_generation_gates: bool = True,
    allow_resume: bool = True,
    min_post_write_free_gib: float = 10.0,
    throughput_guard_bid: int = 7,
    throughput_guard_hours: float = 20.0,
    gpu_log_path: Path = DEFAULT_GPU_RUNS_LOG,
) -> Dict[str, Any]:
    """Execute full Wave 3 closed-loop prune + C3 heal + pre-quant gate + GGUF build."""
    from transformers.models.qwen4_exp.modeling_qwen4_exp import (
        Qwen4ExpTextGatedResidual,
        Qwen4ExpTextRMSNorm,
        Qwen4ExpTextRotaryEmbedding,
    )

    spec: QuantVariantSpec = VARIANT_SPECS[variant_id]
    target_k = spec.target_k
    need_rco = selector_name in ("A4_prime", "A4'")

    out_dir = Path(out_dir)
    stage_dir = Path(stage_dir)
    eff_pruned_stage_dir = Path(pruned_stage_dir) if pruned_stage_dir is not None else stage_dir
    scratch_dir = Path(scratch_dir)
    models_out_dir = Path(models_out_dir)

    overlays_dir = stage_dir / "overlays"
    imat_parts_dir = stage_dir / "imatrix_parts"
    out_dir.mkdir(parents=True, exist_ok=True)
    stage_dir.mkdir(parents=True, exist_ok=True)
    eff_pruned_stage_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir.mkdir(parents=True, exist_ok=True)
    models_out_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)
    imat_parts_dir.mkdir(parents=True, exist_ok=True)

    evict_stage_dir_page_cache(stage_dir)
    if os.path.realpath(eff_pruned_stage_dir) != os.path.realpath(stage_dir):
        evict_stage_dir_page_cache(eff_pruned_stage_dir)

    swap_baseline = capture_v2_swap_baseline()
    _tel0 = read_linux_mem_telemetry()

    text_cfg, st_index = load_text_cfg_and_index(donor_dir)
    hc_count = int(text_cfg.hc_count)
    hidden_size = int(text_cfg.hidden_size)
    inter_dim = int(text_cfg.moe_intermediate_size)
    hc_width = hc_count * hidden_size
    n_layers = int(text_cfg.num_hidden_layers)
    has_mtp = any(k.startswith("mtp.") for k in st_index.weight_map)
    total_blocks = n_layers + (1 if has_mtp else 0)
    rotary_emb = Qwen4ExpTextRotaryEmbedding(config=text_cfg)

    n_calib_expected = 0
    with open(calib_jsonl, "r", encoding="utf-8") as cf:
        for ln in cf:
            if ln.strip():
                n_calib_expected += 1
                if calib_samples_limit > 0 and n_calib_expected >= calib_samples_limit:
                    break

    c_e0_path = stage_dir / f"calib_{calib_samples_limit}_e0.bin"
    c_h0_path = stage_dir / f"calib_{calib_samples_limit}_h0.bin"
    e_h0_path = stage_dir / "eval_h0.bin"
    init_manifest_path = stage_dir / f"init_states_manifest_c{n_calib_expected}.json"
    expected_ckpt_path = eff_pruned_stage_dir / f"c{n_calib_expected}_pruned_pingpong_state.json"

    calib_manifest_sha = _compute_calib_manifest_sha(
        calib_jsonl=Path(calib_jsonl),
        calib_samples_limit=calib_samples_limit,
        max_seq_len=max_seq_len,
        eval_jsonl=Path(eval_jsonl),
        eval_samples_limit=eval_samples_limit,
    )
    can_skip_emb = bool(
        allow_resume
        and _verify_init_states_manifest(
            manifest_path=init_manifest_path,
            expected_calib_manifest_sha=calib_manifest_sha,
            c_e0_path=c_e0_path,
            c_h0_path=c_h0_path,
            e_h0_path=e_h0_path,
        )
    )
    if can_skip_emb:
        print(
            f"[WAVE3][INIT_REUSE] Verified e0/h0 sha256 + shape + calib_manifest_sha ({calib_manifest_sha[:12]})",
            flush=True,
        )

    # Prepare datasets (supporting throughput guard restart at 448 seqs & OPUS §0.3a.4 / §1.D2b.4 resume)
    calib_samples, calib_e0, calib_h0 = prepare_jsonl_samples_and_initial_states(
        calib_jsonl,
        c_e0_path,
        c_h0_path,
        donor_dir=donor_dir,
        max_samples=calib_samples_limit,
        max_seq_len=max_seq_len,
        backend=backend,
        skip_embedding_init=can_skip_emb,
        min_post_write_free_gib=min_post_write_free_gib,
    )
    assert calib_e0 is not None
    eval_samples, _, eval_h0 = prepare_jsonl_samples_and_initial_states(
        eval_jsonl,
        None,
        e_h0_path,
        donor_dir=donor_dir,
        max_samples=eval_samples_limit,
        max_seq_len=max(max_seq_len, 4096),
        backend=backend,
        skip_embedding_init=can_skip_emb,
        min_post_write_free_gib=min_post_write_free_gib,
    )
    if not can_skip_emb:
        _write_init_states_manifest(init_manifest_path, calib_manifest_sha, calib_e0, calib_h0, eval_h0)

    c_lens = [s.seq_len for s in calib_samples]
    e_lens = [s.seq_len for s in eval_samples]

    donor_pp = ResumablePingPong(stage_dir, f"c{len(calib_samples)}_donor", c_lens, hc_count, hidden_size)
    ev_donor_pp = ResumablePingPong(stage_dir, "ev_donor", e_lens, hc_count, hidden_size)
    pruned_pp = ResumablePingPong(eff_pruned_stage_dir, f"c{len(calib_samples)}_pruned", c_lens, hc_count, hidden_size)
    ev_pruned_pp = ResumablePingPong(eff_pruned_stage_dir, "ev_pruned", e_lens, hc_count, hidden_size)

    ckpt_state = pruned_pp.load_state() if (allow_resume and expected_ckpt_path.is_file()) else None
    resume_metadata: Optional[Dict[str, Any]] = None
    if ckpt_state is None:
        start_layer = 0
        cur_slot = "A"

        if min_post_write_free_gib > 0.0:
            c_pair_bytes = 2 * sum(c_lens) * hc_count * hidden_size * 2
            e_pair_bytes = 2 * sum(e_lens) * hc_count * hidden_size * 2
            per_ov_bytes = (
                (target_k * hidden_size * inter_dim * 10) // 32 + 12 * 1024 * 1024
                if spec.use_gsq_q2_0_splice
                else 12 * 1024 * 1024
            )
            ov_imat_total = total_blocks * per_ov_bytes + 300 * 1024 * 1024
            same_stage_mount = os.path.realpath(stage_dir) == os.path.realpath(eff_pruned_stage_dir)
            if same_stage_mount:
                assert_post_write_free_gib(
                    stage_dir,
                    2 * (c_pair_bytes + e_pair_bytes) + ov_imat_total,
                    min_free_gib=min_post_write_free_gib,
                    label="wave3_unified_stage_preflight",
                )
            else:
                assert_post_write_free_gib(
                    stage_dir,
                    (c_pair_bytes + e_pair_bytes) + ov_imat_total,
                    min_free_gib=min_post_write_free_gib,
                    label="wave3_donor_stage_and_overlays_preflight",
                )
                assert_post_write_free_gib(
                    eff_pruned_stage_dir,
                    (c_pair_bytes + e_pair_bytes),
                    min_free_gib=min_post_write_free_gib,
                    label="wave3_pruned_stage_preflight",
                )

        for pp, h0_src, sm_list in (
            (donor_pp, calib_h0, calib_samples),
            (pruned_pp, calib_h0, calib_samples),
            (ev_donor_pp, eval_h0, eval_samples),
            (ev_pruned_pp, eval_h0, eval_samples),
        ):
            sa = pp.open_slot("A", create=True)
            _ = pp.open_slot("B", create=True)
            for s in sm_list:
                sa.write_seq(s.idx, h0_src.read_seq(s.idx))
        layer_cosines: Dict[str, float] = {}
        layer_timings: List[float] = []
    else:
        completed_layer = int(ckpt_state["completed_layer"])
        start_layer = completed_layer + 1
        cur_slot = str(ckpt_state["active_slot"])
        prev_slot = "B" if cur_slot == "A" else "A"
        layer_cosines = dict(ckpt_state.get("layer_cosines", {}))
        layer_timings = list(ckpt_state.get("layer_timings", []))

        cd_cur = donor_pp.open_slot(cur_slot, create=False)
        cp_cur = pruned_pp.open_slot(cur_slot, create=False)
        ed_cur = ev_donor_pp.open_slot(cur_slot, create=False)
        ep_cur = ev_pruned_pp.open_slot(cur_slot, create=False)

        prev_intact = _slot_marker_is_clean(stage_dir / f"w3_in_progress_slot_{prev_slot}.marker")
        if prev_intact:
            try:
                cd_prev = donor_pp.open_slot(prev_slot, create=False)
                _ = pruned_pp.open_slot(prev_slot, create=False)
                ed_prev = ev_donor_pp.open_slot(prev_slot, create=False)
                _ = ev_pruned_pp.open_slot(prev_slot, create=False)
            except (FileNotFoundError, ValueError):
                prev_intact = False

        if not prev_intact:
            cd_prev = donor_pp.open_slot(prev_slot, create=True)
            _ = pruned_pp.open_slot(prev_slot, create=True)
            ed_prev = ev_donor_pp.open_slot(prev_slot, create=True)
            _ = ev_pruned_pp.open_slot(prev_slot, create=True)

        if prev_intact and completed_layer >= 0:
            probe_res = run_layer_resume_determinism_probe(
                mode="prev_slot",
                probe_bid=completed_layer,
                text_cfg=text_cfg,
                st_index=st_index,
                rotary_emb=rotary_emb,
                backend=backend,
                calib_samples=calib_samples,
                eval_samples=eval_samples,
                c_in_store=cd_prev,
                e_in_store=ed_prev,
                c_expected_out_store=cd_cur,
                e_expected_out_store=ed_cur,
            )
        else:
            probe_res = run_layer_resume_determinism_probe(
                mode="double_recompute",
                probe_bid=min(start_layer, n_layers - 1),
                text_cfg=text_cfg,
                st_index=st_index,
                rotary_emb=rotary_emb,
                backend=backend,
                calib_samples=calib_samples,
                eval_samples=eval_samples,
                c_in_store=cd_cur,
                e_in_store=ed_cur,
            )

        verified_files = {
            calib_e0.bin_path.name: int(calib_e0.total_bytes),
            cd_cur.bin_path.name: int(cd_cur.total_bytes),
            cp_cur.bin_path.name: int(cp_cur.total_bytes),
            ed_cur.bin_path.name: int(ed_cur.total_bytes),
            ep_cur.bin_path.name: int(ep_cur.total_bytes),
        }
        append_gpu_resume_log(
            pipeline="wave3_closed_loop",
            resume_bid=start_layer,
            cur_slot=cur_slot,
            verified_files=verified_files,
            probe_mode=str(probe_res["mode"]),
            probe_max_rel_l2=float(probe_res["max_rel_l2"]),
            log_path=gpu_log_path,
        )
        resume_metadata = {
            "resume_bid": start_layer,
            "cur_slot": cur_slot,
            "verified_files_bytes": verified_files,
            "determinism_probe": probe_res,
        }

    # --- Stage A: 48 Trunk Layers Closed-Loop Ping-Pong ---
    for bid in range(start_layer, n_layers):
        t_l0 = time.perf_counter()
        nxt_slot = "B" if cur_slot == "A" else "A"
        w3_dirty_marker = stage_dir / f"w3_in_progress_slot_{nxt_slot}.marker"
        w3_dirty_marker.write_text(f"dirty:{bid}", encoding="utf-8")

        cd_in, cd_out = donor_pp.open_slot(cur_slot), donor_pp.open_slot(nxt_slot)
        cp_in, cp_out = pruned_pp.open_slot(cur_slot), pruned_pp.open_slot(nxt_slot)
        ed_in, ed_out = ev_donor_pp.open_slot(cur_slot), ev_donor_pp.open_slot(nxt_slot)
        ep_in, ep_out = ev_pruned_pp.open_slot(cur_slot), ev_pruned_pp.open_slot(nxt_slot)

        ple_in = [s.input_ids for s in calib_samples] + [s.input_ids for s in eval_samples]
        ctx = SingleLayerContext(
            bid=bid,
            text_cfg=text_cfg,
            st_index=st_index,
            rotary_emb=rotary_emb,
            backend=backend,
            is_mtp=False,
            preindex_ple_inputs=ple_in,
        )
        moe_donor = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend=backend)

        reap_acc = ReapHopeRcoAccumulator(
            num_experts=int(text_cfg.num_experts),
            top_k=int(text_cfg.num_experts_per_tok),
            collect_rco_cache=need_rco,
            rco_max_tokens=16384,
            rco_stride=max(1, sum(c_lens) // 16384),
        )

        # 1. Propagate donor calibration stream & observe closed-loop pruned MLP inputs
        y_donor_list: List[np.ndarray] = []
        h_pruned_mlp_list: List[np.ndarray] = []
        heal_stride = max(1, sum(c_lens) // 65536)

        for s in calib_samples:
            hd_mlp_in, hd_hyper, hd_inj = ctx.forward_pre_moe(cd_in.read_seq(s.idx), s)
            yd = forward_moe_v2(moe_donor, hd_mlp_in)
            cd_out.write_seq(s.idx, ctx.combine_post_moe(yd, hd_hyper, hd_inj, hc_count, hidden_size))

            reap_acc.set_sample_flags(s.flags)
            hp_mlp_in, _, _ = ctx.forward_pre_moe(cp_in.read_seq(s.idx), s)
            _ = forward_moe_v2(moe_donor, hp_mlp_in, flat_token_ids=s.input_ids, reap_acc=reap_acc)

            s_take = np.arange(0, s.seq_len, heal_stride)
            if s_take.size > 0:
                y_donor_list.append(yd.to(torch.float32).numpy().reshape(s.seq_len, hidden_size)[s_take])
                h_pruned_mlp_list.append(hp_mlp_in.to(torch.float32).numpy().reshape(s.seq_len, hidden_size)[s_take])

        # Propagate donor eval stream BEFORE freeing 4.69 GiB donor MoE VRAM
        hd_ev_next_list: List[np.ndarray] = []
        for s in eval_samples:
            ed_mlp, ed_hyp, ed_inj = ctx.forward_pre_moe(ed_in.read_seq(s.idx), s)
            yd_ev = forward_moe_v2(moe_donor, ed_mlp)
            hd_next = ctx.combine_post_moe(yd_ev, ed_hyp, ed_inj, hc_count, hidden_size)
            ed_out.write_seq(s.idx, hd_next)
            hd_ev_next_list.append(hd_next.to(torch.float32).numpy().reshape(s.seq_len, -1))

        moe_donor.close()
        free_cupy_pools()

        score_dict = reap_acc.finalize_score_dict()
        keep_idx = _select_experts_for_layer(selector_name, score_dict, reap_acc, target_k)

        h_cal_sub = np.concatenate(h_pruned_mlp_list, axis=0)
        y_cal_sub = np.concatenate(y_donor_list, axis=0)
        del h_pruned_mlp_list, y_donor_list

        moe_p_init = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend=backend, keep_indices=keep_idx)
        heal_res = heal_layer_c3(moe_p_init, h_cal_sub, y_cal_sub, max_heal_tokens=65536)
        moe_p_init.close()
        free_cupy_pools()
        del h_cal_sub, y_cal_sub

        moe_healed = MoELayerWeights.from_hf_moe_block(
            ctx.layer.mlp,
            backend=backend,
            keep_indices=keep_idx,
            gate_override_f32=heal_res.w_gate_f32,
            alpha_scales=heal_res.alpha_scales,
            sh_down_override=heal_res.w_down_shexp_f32,
        )

        # 2. Propagate closed-loop H^(l+1)_pruned & collect post-heal imatrix + down_proj Hessians
        imat_layer = LayerImatrixCollector()
        ph_stats = PostHealStatsCollector(
            bid=bid,
            num_experts=target_k,
            hidden_dim=hidden_size,
            inter_dim=inter_dim,
            imatrix=imat_layer,
            collect_hessian=spec.use_gsq_q2_0_splice,
        )
        hooks = attach_non_moe_imatrix_hooks(ctx.layer, text_cfg, bid=bid, imat=imat_layer)
        try:
            for s in calib_samples:
                hp_mlp_in, hp_hyper, hp_inj = ctx.forward_pre_moe(cp_in.read_seq(s.idx), s, imat=imat_layer)
                yp = forward_moe_v2(moe_healed, hp_mlp_in, post_heal=ph_stats)
                cp_out.write_seq(s.idx, ctx.combine_post_moe(yp, hp_hyper, hp_inj, hc_count, hidden_size))
        finally:
            for hk in hooks:
                hk.remove()

        # 3. Propagate pruned eval stream & measure per-layer cosine(H_pruned, H_donor)
        cos_vals: List[float] = []
        for s, hd_ev_np in zip(eval_samples, hd_ev_next_list):
            ep_mlp, ep_hyp, ep_inj = ctx.forward_pre_moe(ep_in.read_seq(s.idx), s)
            yp_ev = forward_moe_v2(moe_healed, ep_mlp)
            hp_next = ctx.combine_post_moe(yp_ev, ep_hyp, ep_inj, hc_count, hidden_size)
            ep_out.write_seq(s.idx, hp_next)

            cos_vals.append(
                compute_cosine_similarity_batch(
                    hp_next.to(torch.float32).numpy().reshape(s.seq_len, -1),
                    hd_ev_np,
                )
            )
        del hd_ev_next_list
        layer_cosines[str(bid)] = round(float(np.mean(cos_vals)), 6)

        # 4. Inline clean-room GSQ Q2_0 quantization of healed down_exps (streaming 1 expert at a time)
        q2_packed: Optional[np.ndarray] = None
        if spec.use_gsq_q2_0_splice:
            from scripts.v2.cupy_moe_backend import free_cupy_pinned_pool

            def _fetch_dn_exp_f32(k_i: int) -> np.ndarray:
                if moe_healed.backend == "cupy":
                    arr_k = moe_healed.down[int(k_i)].get().astype(np.float32)
                    free_cupy_pinned_pool()
                    return arr_k
                return moe_healed.down[int(k_i)].astype(np.float32)

            q2_packed, _ = gsq_quantize_layer_down_exps(
                _fetch_dn_exp_f32,
                hessians_fn=lambda k: ph_stats.get_damped_hessian_f64(k, damp_ratio=0.01),
                num_experts=target_k,
                return_dequant=False,
            )

        overlay = LayerPruneHealOverlay(
            bid=bid,
            keep_indices=keep_idx,
            w_gate_f32=heal_res.w_gate_f32,
            alpha_scales=heal_res.alpha_scales,
            w_down_shexp_f32=heal_res.w_down_shexp_f32,
        )
        _save_layer_overlay_and_q2(overlays_dir, bid, overlay, q2_packed, min_free_gib=min_post_write_free_gib)
        np.savez(
            imat_parts_dir / f"layer_{bid:02d}.npz",
            sum2_keys=np.array(sorted(imat_layer.sum2.keys())),
            **{f"s2_{i}": imat_layer.sum2[k] for i, k in enumerate(sorted(imat_layer.sum2.keys()))},
            **{f"cnt_{i}": imat_layer.counts[k] for i, k in enumerate(sorted(imat_layer.sum2.keys()))},
        )
        dt_l = time.perf_counter() - t_l0
        with open(out_dir / f"layer_{bid:02d}_report.json", "w", encoding="utf-8") as rf:
            json.dump(
                {
                    "bid": bid,
                    "selector": selector_name,
                    "target_k": target_k,
                    "c3_metrics": heal_res.metrics,
                    "eval_cosine": layer_cosines[str(bid)],
                    "wall_sec": round(dt_l, 2),
                },
                rf,
                indent=2,
            )

        moe_healed.close()
        ctx.close()
        del ph_stats, q2_packed
        tel_l = assert_zero_swap_and_mem(swap_baseline)

        layer_timings.append(dt_l)
        cur_slot = nxt_slot
        donor_pp.save_state(completed_layer=bid, active_slot=cur_slot)
        ev_donor_pp.save_state(completed_layer=bid, active_slot=cur_slot)
        ev_pruned_pp.save_state(completed_layer=bid, active_slot=cur_slot)
        pruned_pp.save_state(
            completed_layer=bid,
            active_slot=cur_slot,
            extra={"layer_cosines": layer_cosines, "layer_timings": layer_timings},
        )
        w3_dirty_marker.write_text(f"clean:{bid}", encoding="utf-8")

        print(
            f"[WAVE3][LAYER {bid:02d}/{n_layers - 1:02d}] dt={dt_l:.1f}s cos={layer_cosines[str(bid)]:.6f} "
            f"c3_rel_l2={heal_res.val_rel_l2_before:.4f}->{heal_res.val_rel_l2_after_c3:.4f} "
            f"(c1={heal_res.c1_accepted},c2a={heal_res.c2_alpha_accepted},c2b={heal_res.c2_shexp_accepted}) "
            f"MemAvail={tel_l.mem_available_gib:.2f}GiB zram_d={max(0.0, tel_l.zram_orig_mib - swap_baseline.zram_orig_mib):.1f}MiB",
            flush=True,
        )

        # Throughput guard — OPUS §1.D2c (after bid=7, ceiling <= 20.0 h; unchanged Stage A method)
        if bid == int(throughput_guard_bid) and calib_samples_limit > 448:
            guard = check_layer4_throughput_guard(
                layer_timings,
                total_layers=total_blocks,
                max_projected_hours=float(throughput_guard_hours),
            )
            guard["guard_bid"] = int(bid)
            guard["escalate_opus_throughput_exceeded"] = bool(guard["triggered"])
            with open(out_dir / f"throughput_guard_layer{bid + 1}.json", "w", encoding="utf-8") as gf:
                json.dump(guard, gf, indent=2)
            print(f"[WAVE3][THROUGHPUT_GUARD] {json.dumps(guard, sort_keys=True)}", flush=True)
            if guard["triggered"]:
                raise RuntimeError(
                    f"Wave 3 throughput guard at bid={bid} exceeded {throughput_guard_hours:.1f} h "
                    f"({guard['projected_hours']} h projected); stopping cleanly at bid={bid} checkpoint for Opus escalation."
                )

    # --- Stage A2: MTP Block (blk.48 on S - 1 causal pairs) ---
    mtp_bid = n_layers
    if has_mtp and not (overlays_dir / f"layer_{mtp_bid:02d}_overlay.npz").is_file():
        t_mtp0 = time.perf_counter()
        mtp_cfg = build_mtp_decoder_config(text_cfg)
        with torch.device("meta"):
            pre_enorm = Qwen4ExpTextRMSNorm(hidden_size, eps=float(text_cfg.rms_norm_eps))
            pre_hnorm = Qwen4ExpTextRMSNorm(hc_width, group_size=hidden_size, eps=float(text_cfg.rms_norm_eps))
            fc_emb = nn.Linear(hidden_size, hidden_size, bias=False)
            fc_hid = nn.Linear(hidden_size, hidden_size, bias=False)
            mtp_head_mixer = Qwen4ExpTextGatedResidual(mtp_cfg, use_combine=False)

        materialize_submodule(pre_enorm, "mtp.pre_fc_norm_embedding", st_index, device="cpu")
        materialize_submodule(pre_hnorm, "mtp.pre_fc_norm_hidden", st_index, device="cpu")
        materialize_submodule(fc_emb, "mtp.fc_embedding", st_index, device="cpu")
        materialize_submodule(fc_hid, "mtp.fc_hidden", st_index, device="cpu")
        materialize_submodule(mtp_head_mixer, "mtp.hyper_connection_mixer", st_index, device="cpu")
        mtp_patch_fc_e = CuPyLinearPatch(fc_emb, enabled=(backend == "cupy"))
        mtp_patch_fc_h = CuPyLinearPatch(fc_hid, enabled=(backend == "cupy"))
        mtp_patch_hmix = CuPyLinearPatch(mtp_head_mixer, enabled=(backend == "cupy"))

        ctx_mtp = SingleLayerContext(
            bid=mtp_bid,
            text_cfg=text_cfg,
            st_index=st_index,
            rotary_emb=rotary_emb,
            backend=backend,
            is_mtp=True,
        )
        moe_mtp_donor = MoELayerWeights.from_hf_moe_block(ctx_mtp.layer.mlp, backend=backend)
        reap_mtp = ReapHopeRcoAccumulator(
            num_experts=int(text_cfg.num_experts),
            top_k=int(text_cfg.num_experts_per_tok),
            collect_rco_cache=need_rco,
            rco_max_tokens=16384,
            rco_stride=max(1, sum(c_lens) // 16384),
        )

        cd_final = donor_pp.open_slot(cur_slot)
        cp_final = pruned_pp.open_slot(cur_slot)
        imat_mtp = LayerImatrixCollector()
        yd_mtp_list: List[np.ndarray] = []
        hp_mtp_list: List[np.ndarray] = []
        heal_stride_m = max(1, sum(c_lens) // 65536)

        with torch.no_grad():
            for s in calib_samples:
                if s.seq_len < 2:
                    continue
                e0_s = calib_e0.read_seq(s.idx).reshape(1, s.seq_len, hidden_size)[:, 1:, :]
                hd_47 = cd_final.read_seq(s.idx).reshape(1, s.seq_len, hc_width)[:, :-1, :]
                hp_47 = cp_final.read_seq(s.idx).reshape(1, s.seq_len, hc_width)[:, :-1, :]

                e_n = pre_enorm(e0_s)
                hd_n = pre_hnorm(hd_47).view(1, s.seq_len - 1, hc_count, hidden_size)
                hp_n = pre_hnorm(hp_47).view(1, s.seq_len - 1, hc_count, hidden_size)
                imat_mtp.record_mtp_eh_proj(f"blk.{mtp_bid}.nextn.eh_proj.weight", e_n, hp_n)

                res_d = (fc_emb(e_n).unsqueeze(2) + fc_hid(hd_n)).reshape(1, s.seq_len - 1, hc_count, hidden_size)
                res_p = (fc_emb(e_n).unsqueeze(2) + fc_hid(hp_n)).reshape(1, s.seq_len - 1, hc_count, hidden_size)

                sub_mrope = s.mrope_position_ids[:, :, :-1].contiguous() if s.mrope_position_ids is not None else None
                sub_s = PreparedSample(s.idx, s.sample_id, s.seq_len - 1, s.input_ids[:, 1:], sub_mrope, s.flags)
                hd_m_in, _, _ = ctx_mtp.forward_pre_moe(res_d, sub_s)
                yd_m = forward_moe_v2(moe_mtp_donor, hd_m_in)

                reap_mtp.set_sample_flags(s.flags)
                hp_m_in, _, _ = ctx_mtp.forward_pre_moe(res_p, sub_s)
                _ = forward_moe_v2(moe_mtp_donor, hp_m_in, flat_token_ids=sub_s.input_ids, reap_acc=reap_mtp)

                st_idx_arr = np.arange(0, sub_s.seq_len, heal_stride_m)
                if st_idx_arr.size > 0:
                    yd_mtp_list.append(yd_m.to(torch.float32).numpy().reshape(sub_s.seq_len, hidden_size)[st_idx_arr])
                    hp_mtp_list.append(hp_m_in.to(torch.float32).numpy().reshape(sub_s.seq_len, hidden_size)[st_idx_arr])

        moe_mtp_donor.close()
        free_cupy_pools()

        mtp_scores = reap_mtp.finalize_score_dict()
        mtp_keep = _select_experts_for_layer(selector_name, mtp_scores, reap_mtp, target_k)
        moe_mtp_p = MoELayerWeights.from_hf_moe_block(ctx_mtp.layer.mlp, backend=backend, keep_indices=mtp_keep)
        mtp_heal = heal_layer_c3(
            moe_mtp_p,
            np.concatenate(hp_mtp_list, axis=0),
            np.concatenate(yd_mtp_list, axis=0),
        )
        moe_mtp_p.close()
        free_cupy_pools()
        del hp_mtp_list, yd_mtp_list

        moe_mtp_h = MoELayerWeights.from_hf_moe_block(
            ctx_mtp.layer.mlp,
            backend=backend,
            keep_indices=mtp_keep,
            gate_override_f32=mtp_heal.w_gate_f32,
            alpha_scales=mtp_heal.alpha_scales,
            sh_down_override=mtp_heal.w_down_shexp_f32,
        )
        ph_mtp = PostHealStatsCollector(
            bid=mtp_bid,
            num_experts=target_k,
            hidden_dim=hidden_size,
            inter_dim=inter_dim,
            imatrix=imat_mtp,
            collect_hessian=spec.use_gsq_q2_0_splice,
        )
        hooks_m = attach_non_moe_imatrix_hooks(ctx_mtp.layer, mtp_cfg, bid=mtp_bid, imat=imat_mtp)
        hooks_m.append(
            mtp_head_mixer.input_mix_weight_down.register_forward_pre_hook(
                lambda _m, inp: imat_mtp.record_2d((f"blk.{mtp_bid}.nextn.hc_head_down.weight",), inp[0])
            )
        )
        hooks_m.append(
            mtp_head_mixer.input_mix_weight_up.register_forward_pre_hook(
                lambda _m, inp: imat_mtp.record_2d((f"blk.{mtp_bid}.nextn.hc_head_up.weight",), inp[0])
            )
        )
        try:
            with torch.no_grad():
                for s in calib_samples:
                    if s.seq_len < 2:
                        continue
                    e0_s = calib_e0.read_seq(s.idx).reshape(1, s.seq_len, hidden_size)[:, 1:, :]
                    hp_47 = cp_final.read_seq(s.idx).reshape(1, s.seq_len, hc_width)[:, :-1, :]
                    res_p = (
                        fc_emb(pre_enorm(e0_s)).unsqueeze(2)
                        + fc_hid(pre_hnorm(hp_47).view(1, s.seq_len - 1, hc_count, hidden_size))
                    ).reshape(1, s.seq_len - 1, hc_count, hidden_size)
                    sub_mrope = s.mrope_position_ids[:, :, :-1].contiguous() if s.mrope_position_ids is not None else None
                    sub_s = PreparedSample(s.idx, s.sample_id, s.seq_len - 1, s.input_ids[:, 1:], sub_mrope, s.flags)
                    hp_m_in, hp_hyp, hp_inj = ctx_mtp.forward_pre_moe(res_p, sub_s, imat=imat_mtp)
                    yp_m = forward_moe_v2(moe_mtp_h, hp_m_in, post_heal=ph_mtp)
                    hm_out = ctx_mtp.combine_post_moe(yp_m, hp_hyp, hp_inj, hc_count, hidden_size)
                    _ = mtp_head_mixer(hm_out.reshape(1, sub_s.seq_len, hc_width))
        finally:
            for hk in hooks_m:
                hk.remove()

        q2_mtp: Optional[np.ndarray] = None
        if spec.use_gsq_q2_0_splice:
            from scripts.v2.cupy_moe_backend import free_cupy_pinned_pool

            def _fetch_mtp_dn_exp_f32(k_i: int) -> np.ndarray:
                if moe_mtp_h.backend == "cupy":
                    arr_k = moe_mtp_h.down[int(k_i)].get().astype(np.float32)
                    free_cupy_pinned_pool()
                    return arr_k
                return moe_mtp_h.down[int(k_i)].astype(np.float32)

            q2_mtp, _ = gsq_quantize_layer_down_exps(
                _fetch_mtp_dn_exp_f32,
                hessians_fn=lambda k: ph_mtp.get_damped_hessian_f64(k, damp_ratio=0.01),
                num_experts=target_k,
                return_dequant=False,
            )

        ov_mtp = LayerPruneHealOverlay(
            bid=mtp_bid,
            keep_indices=mtp_keep,
            w_gate_f32=mtp_heal.w_gate_f32,
            alpha_scales=mtp_heal.alpha_scales,
            w_down_shexp_f32=mtp_heal.w_down_shexp_f32,
        )
        _save_layer_overlay_and_q2(overlays_dir, mtp_bid, ov_mtp, q2_mtp, min_free_gib=min_post_write_free_gib)
        np.savez(
            imat_parts_dir / f"layer_{mtp_bid:02d}.npz",
            sum2_keys=np.array(sorted(imat_mtp.sum2.keys())),
            **{f"s2_{i}": imat_mtp.sum2[k] for i, k in enumerate(sorted(imat_mtp.sum2.keys()))},
            **{f"cnt_{i}": imat_mtp.counts[k] for i, k in enumerate(sorted(imat_mtp.sum2.keys()))},
        )
        dt_mtp = time.perf_counter() - t_mtp0
        with open(out_dir / f"layer_{mtp_bid:02d}_report.json", "w", encoding="utf-8") as rf:
            json.dump(
                {
                    "bid": mtp_bid,
                    "is_mtp": True,
                    "selector": selector_name,
                    "target_k": target_k,
                    "c3_metrics": mtp_heal.metrics,
                    "wall_sec": round(dt_mtp, 2),
                },
                rf,
                indent=2,
            )

        moe_mtp_h.close()
        ctx_mtp.close()
        for mp_tmp in (mtp_patch_fc_e, mtp_patch_fc_h, mtp_patch_hmix):
            mp_tmp.close()
        for m_tmp in (pre_enorm, pre_hnorm, fc_emb, fc_hid, mtp_head_mixer):
            free_submodule_to_meta(m_tmp)
        del ph_mtp, q2_mtp
        gc.collect()
        tel_m = assert_zero_swap_and_mem(swap_baseline)
        print(
            f"[WAVE3][MTP blk.{mtp_bid:02d}] dt={dt_mtp:.1f}s "
            f"c3_rel_l2={mtp_heal.val_rel_l2_before:.4f}->{mtp_heal.val_rel_l2_after_c3:.4f} "
            f"MemAvail={tel_m.mem_available_gib:.2f}GiB",
            flush=True,
        )

    # --- Stage B: Output Mixer imatrix + BF16 Pre-Quant Gate over E + Donor .kld Export ---
    prequant_gate_path = out_dir / "bf16_prequant_gate.json"
    en_kld_path = scratch_dir / "donor_eval_en.kld"
    ru_kld_path = scratch_dir / "donor_eval_ru.kld"

    def _read_valid_kld_info(p: Path) -> Optional[Dict[str, Any]]:
        if not p.is_file() or p.stat().st_size < 20:
            return None
        with open(p, "rb") as kf:
            hdr = kf.read(20)
        if len(hdr) < 20 or hdr[:8] != b"_logits_":
            return None
        n_ctx_i, n_vocab_i, n_chunk_i = struct.unpack("<Iii", hdr[8:20])
        if n_ctx_i < 8 or n_vocab_i <= 0 or n_chunk_i <= 0:
            return None
        n_eval = n_ctx_i - 1 - (n_ctx_i // 2)
        nv = 2 * ((n_vocab_i + 1) // 2) + 4
        expected_bytes = 20 + 4 * n_ctx_i * n_chunk_i + n_chunk_i * n_eval * nv * 2
        if int(p.stat().st_size) != expected_bytes:
            return None
        return {
            "kld_path": str(p),
            "n_ctx": int(n_ctx_i),
            "n_vocab": int(n_vocab_i),
            "n_chunk": int(n_chunk_i),
            "eval_tokens": int(n_chunk_i * n_eval),
            "bytes": int(expected_bytes),
        }

    cached_en_kld = _read_valid_kld_info(en_kld_path) if allow_resume else None
    cached_ru_kld = _read_valid_kld_info(ru_kld_path) if allow_resume else None
    reuse_stage_b = bool(
        allow_resume
        and prequant_gate_path.is_file()
        and (not run_generation_gates or (cached_en_kld is not None and cached_ru_kld is not None))
    )

    with torch.device("meta"):
        out_mixer = Qwen4ExpTextGatedResidual(text_cfg, use_combine=False)
    materialize_submodule(out_mixer, "model.language_model.hyper_connection_mixer", st_index, device="cpu")

    lm_head_arg: Any = None
    if not reuse_stage_b:
        lm_head_t = st_index.load_tensors(["lm_head.weight"], device="cpu")["lm_head.weight"]
        lm_head_fp16 = lm_head_t.to(torch.float16).numpy()
        del lm_head_t
        lm_head_arg = (
            upload_2d_fp16_chunked_cupy(lm_head_fp16) if backend == "cupy" else lm_head_fp16
        )
        if backend == "cupy":
            del lm_head_fp16

    imat_head = LayerImatrixCollector()
    h_out_hooks = [
        out_mixer.input_mix_weight_down.register_forward_pre_hook(
            lambda _m, inp: imat_head.record_2d(("output_hc_down.weight",), inp[0])
        ),
        out_mixer.input_mix_weight_up.register_forward_pre_hook(
            lambda _m, inp: imat_head.record_2d(("output_hc_up.weight",), inp[0])
        ),
    ]
    patch_mix = CuPyLinearPatch(out_mixer, enabled=(backend == "cupy"))
    cp_final = pruned_pp.open_slot(cur_slot)
    ed_final = ev_donor_pp.open_slot(cur_slot)
    ep_final = ev_pruned_pp.open_slot(cur_slot)

    en_eval_samples = [s for s in eval_samples if not s.flags.is_ru]
    ru_eval_samples = [s for s in eval_samples if s.flags.is_ru]
    en_kld_n_ctx = min(1200, min((s.seq_len for s in en_eval_samples), default=0))
    ru_kld_n_ctx = min(320, min((s.seq_len for s in ru_eval_samples), default=0))
    en_kld_toks: List[np.ndarray] = []
    en_kld_hd: List[np.ndarray] = []
    ru_kld_toks: List[np.ndarray] = []
    ru_kld_hd: List[np.ndarray] = []

    en_kl, en_t1, en_n = 0.0, 0.0, 0
    ru_kl, ru_t1, ru_n = 0.0, 0.0, 0
    per_doc_eval_metrics: List[Dict[str, Any]] = []
    en_kld_info: Optional[Dict[str, Any]] = cached_en_kld if reuse_stage_b else None
    ru_kld_info: Optional[Dict[str, Any]] = cached_ru_kld if reuse_stage_b else None

    try:
        with torch.no_grad():
            for s in calib_samples:
                hp_raw = cp_final.read_seq(s.idx).reshape(1, s.seq_len, hc_width)
                hp_out = out_mixer(hp_raw)
                imat_head.record_2d(("output.weight", "token_embd.weight"), hp_out)

            for hk in h_out_hooks:
                hk.remove()
            h_out_hooks.clear()

            if not reuse_stage_b:
                for s in eval_samples:
                    hd_m = (
                        out_mixer(ed_final.read_seq(s.idx).reshape(1, s.seq_len, hc_width))[:, :-1, :]
                        .to(torch.float32)
                        .numpy()
                        .reshape(-1, hidden_size)
                    )
                    hp_m = (
                        out_mixer(ep_final.read_seq(s.idx).reshape(1, s.seq_len, hc_width))[:, :-1, :]
                        .to(torch.float32)
                        .numpy()
                        .reshape(-1, hidden_size)
                    )
                    ks, ts, nt = compute_kl_and_top1_from_hidden(hd_m, hp_m, lm_head_arg, backend=backend)
                    per_doc_eval_metrics.append(
                        {
                            "sample_id": str(s.sample_id),
                            "lang": "ru" if s.flags.is_ru else "en",
                            "tokens": int(nt),
                            "mean_kl": round(float(ks / max(nt, 1)), 6),
                            "top1_acc": round(float(ts / max(nt, 1)), 6),
                        }
                    )
                    tok_1d = s.input_ids.reshape(-1).to(torch.int32).numpy()
                    if s.flags.is_ru:
                        ru_kl += ks
                        ru_t1 += ts
                        ru_n += nt
                        if ru_kld_n_ctx >= 8 and s.seq_len >= ru_kld_n_ctx:
                            ru_kld_toks.append(tok_1d[:ru_kld_n_ctx].copy())
                            ru_kld_hd.append(hd_m[: ru_kld_n_ctx - 1].copy())
                    else:
                        en_kl += ks
                        en_t1 += ts
                        en_n += nt
                        if en_kld_n_ctx >= 8 and s.seq_len >= en_kld_n_ctx:
                            en_kld_toks.append(tok_1d[:en_kld_n_ctx].copy())
                            en_kld_hd.append(hd_m[: en_kld_n_ctx - 1].copy())

                if run_generation_gates and en_kld_toks and ru_kld_toks:
                    en_kld_info = write_llama_kld_file(
                        out_kld_path=en_kld_path,
                        token_chunks=en_kld_toks,
                        donor_hidden_chunks=en_kld_hd,
                        lm_head_weight_fp16=lm_head_arg,
                        n_ctx=en_kld_n_ctx,
                        backend=backend,
                        min_post_write_free_gib=min_post_write_free_gib,
                    )
                    ru_kld_info = write_llama_kld_file(
                        out_kld_path=ru_kld_path,
                        token_chunks=ru_kld_toks,
                        donor_hidden_chunks=ru_kld_hd,
                        lm_head_weight_fp16=lm_head_arg,
                        n_ctx=ru_kld_n_ctx,
                        backend=backend,
                        min_post_write_free_gib=min_post_write_free_gib,
                    )
    finally:
        for hk in h_out_hooks:
            hk.remove()
        del en_kld_toks, en_kld_hd, ru_kld_toks, ru_kld_hd
        patch_mix.close()
        free_submodule_to_meta(out_mixer)
        del lm_head_arg
        free_cupy_pools()
        gc.collect()

    cos_list = [float(layer_cosines[str(i)]) for i in range(n_layers)]
    if reuse_stage_b:
        prequant_eval = json.loads(prequant_gate_path.read_text(encoding="utf-8"))
        print(f"[WAVE3][BF16_PREQUANT_REUSE] Loaded existing {prequant_gate_path} + KLD files", flush=True)
    else:
        prequant_eval = evaluate_teacher_forced_gate(
            en_kl, en_t1, en_n, ru_kl, ru_t1, ru_n, cos_list, BF16_PREQUANT_THRESHOLDS
        )
        prequant_eval["per_doc_metrics"] = per_doc_eval_metrics
        prequant_eval["bootstrap_ci95"] = compute_per_doc_kl_bootstrap_ci(per_doc_eval_metrics)
        # OPUS §1.D2b.2: On pre-quant KL miss, do NOT abort and do NOT fall back to K288/V4;
        # record escalate_to_opus_prequant_miss and continue to assembly + quant + generation gates.
        prequant_eval["escalate_to_opus_prequant_miss"] = bool(not prequant_eval["passed"])
        with open(prequant_gate_path, "w", encoding="utf-8") as f:
            json.dump(prequant_eval, f, indent=2)
    print(f"[WAVE3][BF16_PREQUANT_GATE] {json.dumps(prequant_eval, sort_keys=True)}", flush=True)
    if prequant_eval["escalate_to_opus_prequant_miss"]:
        print(
            "[WAVE3][ESCALATE_NOTE] BF16 Pre-Quant Gate missed provisional threshold; continuing to "
            "GGUF assembly + quant + generation gates per OPUS §1.D2b.2 (no fallback to K288/V4).",
            flush=True,
        )

    # --- Stage C: Merge imatrix + Stream BF16 GGUF + BF16 Pre-Quant Gen + Final V1 GGUF + GSQ Splice + Post-Quant Gates ---
    full_imat = LayerImatrixCollector()
    for bid in range(total_blocks):
        part = np.load(imat_parts_dir / f"layer_{bid:02d}.npz")
        keys = [str(k) for k in part["sum2_keys"]]
        for idx_k, k_name in enumerate(keys):
            full_imat.sum2[k_name] = part[f"s2_{idx_k}"]
            full_imat.counts[k_name] = part[f"cnt_{idx_k}"]
    full_imat.merge_from(imat_head)

    if REF_205E_GGUF.is_file() and total_blocks == 49:
        imat_cov = verify_imatrix_coverage_against_gguf(
            imatrix_sum2_shapes={k: tuple(int(x) for x in v.shape) for k, v in full_imat.sum2.items()},
            imatrix_count_shapes={k: tuple(int(x) for x in v.shape) for k, v in full_imat.counts.items()},
            ref_gguf=REF_205E_GGUF,
            expected_k=target_k,
            check_completeness=True,
        )
        print(f"[WAVE3][IMATRIX_COVERAGE] {json.dumps(imat_cov, sort_keys=True)}", flush=True)

    imat_gguf_path = stage_dir / f"imatrix_v2_K{target_k}.gguf"
    if min_post_write_free_gib > 0.0:
        assert_post_write_free_gib(
            imat_gguf_path,
            300 * 1024 * 1024,
            min_free_gib=min_post_write_free_gib,
            label="imatrix_gguf",
        )
    write_imatrix_gguf(imat_gguf_path, full_imat, dataset_name=str(calib_jsonl))
    del full_imat, imat_head
    gc.collect()

    all_overlays = {bid: _load_layer_overlay(overlays_dir, bid) for bid in range(total_blocks)}
    bf16_gguf_path = scratch_dir / f"SmartLLM-v2-K{target_k}-BF16.gguf"
    expected_bf16_bytes = int(39_500_000_000 + total_blocks * 3 * target_k * hidden_size * inter_dim * 2)
    if not (allow_resume and verify_bf16_gguf_complete_marker(bf16_gguf_path, expected_target_k=target_k)):
        if min_post_write_free_gib > 0.0:
            assert_post_write_free_gib(
                bf16_gguf_path,
                expected_bf16_bytes,
                min_free_gib=min_post_write_free_gib,
                label="bf16_intermediate_gguf",
            )
        assemble_bf16_intermediate_gguf(
            out_gguf_path=bf16_gguf_path,
            target_k=target_k,
            overlays=all_overlays,
            donor_dir=donor_dir,
            reuse_ple_gguf=REF_205E_GGUF,
            reuse_vocab_gguf=REF_205E_GGUF,
        )
    print(f"[WAVE3][BF16_GGUF] Ready at {bf16_gguf_path} ({bf16_gguf_path.stat().st_size / (1024**3):.3f} GiB)", flush=True)

    # OPUS §1.D2b.5 & Audit #90 Item 4: Pre-quant generation check on bf16_gguf (--lazy-mode direct -nr
    # --n-cpu-moe 48, header-planned <=9.20 GiB VRAM, -np 10 batched, T=0, <=128 new tokens, 30-min cap;
    # non-fatal on load fail / OOM / crash / timeout — only final_gguf gen gate is hard).
    bf16_gen_audit: Optional[Dict[str, Any]] = None
    bf16_gen_json = out_dir / "bf16_prequant_generation_gate.json"
    if run_generation_gates:
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
    expected_final_bytes = int(60_500_000_000)
    if min_post_write_free_gib > 0.0:
        assert_post_write_free_gib(
            final_gguf_path,
            expected_final_bytes,
            min_free_gib=min_post_write_free_gib,
            label="final_quantized_gguf",
        )
    run_llama_quantize_variant(bf16_gguf_path, final_gguf_path, imat_gguf_path, spec)

    splice_info: Optional[Dict[str, Any]] = None
    if spec.use_gsq_q2_0_splice:
        q2_files = {
            bid: overlays_dir / f"blk.{bid}.ffn_down_exps.q2_0.bin"
            for bid in range(total_blocks)
        }
        splice_info = splice_gsq_q2_0_into_gguf(
            final_gguf_path,
            q2_files,
            verify_with_libggml=True,
            ref_bf16_gguf=bf16_gguf_path,
        )
    print(f"[WAVE3][FINAL_GGUF] Ready at {final_gguf_path} ({final_gguf_path.stat().st_size / (1024**3):.3f} GiB)", flush=True)

    final_gen_audit: Optional[Dict[str, Any]] = None
    postquant_kl_eval: Optional[Dict[str, Any]] = None
    if run_generation_gates:
        final_gen_audit = run_10prompt_batched_server_generation_gate(
            gguf_path=final_gguf_path,
            max_new_tokens=256,
            n_parallel=10,
            n_gpu_layers=99,
            moe_cache_mib=4096,
            moe_cache_cpu_share=0.15,
            ctx_per_slot=512,
            offload_output_to_cpu=False,
            wall_cap_sec=1800.0,
            allow_partial_on_timeout=False,
            server_log_path=out_dir / "final_postquant_server.log",
        )
        with open(out_dir / "final_postquant_generation_gate.json", "w", encoding="utf-8") as f:
            json.dump(final_gen_audit, f, indent=2, ensure_ascii=False)
        print(
            f"[WAVE3][FINAL_GEN_GATE] passed={final_gen_audit.get('passed')} "
            f"loops={final_gen_audit.get('total_8gram_x3_loops')} "
            f"min_ru_cyr={final_gen_audit.get('min_ru_cyrillic_ratio')} "
            f"elapsed={final_gen_audit.get('elapsed_sec')}s",
            flush=True,
        )

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
                moe_cache_mib=4096,
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
        "calib_sequences": len(calib_samples),
        "calib_tokens": int(sum(c_lens)),
        "eval_sequences": len(eval_samples),
        "eval_tokens": int(sum(e_lens)),
        "resume_info": resume_metadata,
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
    parser = argparse.ArgumentParser(description="SmartLLM v2 Wave 3 Closed-Loop Full Run")
    parser.add_argument("--selector", choices=["A2", "A3", "A4_prime"], required=True)
    parser.add_argument("--variant", choices=["V1", "V2", "V3", "V4"], required=True)
    parser.add_argument("--calib-jsonl", type=Path, default=Path("data/calib_v2/calib_v2.jsonl"))
    parser.add_argument("--eval-jsonl", type=Path, default=Path("data/eval_E/eval_E.jsonl"))
    parser.add_argument("--out-dir", type=Path, default=RUNS_DIR / "wave3")
    parser.add_argument("--stage-dir", type=Path, default=STAGE_DIR / "wave3")
    parser.add_argument("--pruned-stage-dir", type=Path, default=None)
    parser.add_argument("--scratch-dir", type=Path, default=SCRATCH_DIR)
    parser.add_argument("--backend", choices=["cupy", "cpu"], default="cupy")
    parser.add_argument("--calib-samples", type=int, default=640)
    parser.add_argument("--eval-samples", type=int, default=128)
    parser.add_argument("--max-seq-len", type=int, default=2048)
    parser.add_argument("--min-post-write-free-gib", type=float, default=10.0)
    parser.add_argument("--throughput-guard-bid", type=int, default=7)
    parser.add_argument("--throughput-guard-hours", type=float, default=20.0)
    parser.add_argument("--skip-gen-gates", action="store_true")
    parser.add_argument("--stage-c-only", action="store_true", help="Run zero-CuPy Stage C from disk artifacts only.")
    args = parser.parse_args()

    if args.stage_c_only:
        from scripts.v2.wave3_stage_c import run_stage_c_only

        res = run_stage_c_only(
            selector_name=args.selector,
            variant_id=args.variant,
            out_dir=args.out_dir,
            stage_dir=args.stage_dir,
            scratch_dir=args.scratch_dir,
            run_generation_gates=not args.skip_gen_gates,
            min_post_write_free_gib=args.min_post_write_free_gib,
        )
        print(json.dumps(res, indent=2))
        return 0

    res = run_wave3_pipeline(
        selector_name=args.selector,
        variant_id=args.variant,
        calib_jsonl=args.calib_jsonl,
        eval_jsonl=args.eval_jsonl,
        out_dir=args.out_dir,
        stage_dir=args.stage_dir,
        pruned_stage_dir=args.pruned_stage_dir,
        scratch_dir=args.scratch_dir,
        backend=args.backend,
        calib_samples_limit=args.calib_samples,
        eval_samples_limit=args.eval_samples,
        max_seq_len=args.max_seq_len,
        run_generation_gates=not args.skip_gen_gates,
        min_post_write_free_gib=args.min_post_write_free_gib,
        throughput_guard_bid=args.throughput_guard_bid,
        throughput_guard_hours=args.throughput_guard_hours,
    )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
