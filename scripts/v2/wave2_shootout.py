#!/usr/bin/env python3
"""Wave 2 Single-Factor Pruning + Quant Shootout (OPUS_MASTER_PLAN_V2.md §1.D2, §2 WP-C1, §3 Wave 2).

Stage 2a (Selector Shootout on canonical layers blk [2, 14, 28, 42] at K=320 & K=288):
  - Evaluates A1 (open REAP, no quotas), A2 (Quota-REAP), A3 (Quota-HOPE), A4' (Greedy RCO)
    on donor input H_donor over held-out eval E (plus informational top-k router-mass coverage
    and post-C3 diagnostic r_l).
  - Scores on held-out eval E: `S = 0.6 * mean_l r_EN + 0.4 * mean_l r_RU`.
  - Hard eligibility: 100% quota lock retention AND EVERY quota method must beat A1 on `mean_l r_RU`
    (else STOP & escalate to Opus).
  - Complexity guard: A3/A4' replaces A2 only if `S` drops by >= 3.0% relative AND no single
    layer has `r_l > 1.15 * r_l(A2)`; otherwise A2 wins.

Stage 2b (Quant Shootout on 48-layer donor trunk with [2, 14, 28, 42] spliced + C3 healed over E):
  - Evaluates BF16 references `R320`, `R288` plus quantized candidates `V1`, `V2`, `V3`, `V4`
    using live `libggml-base.so` + clean-room GSQ `Q2_0` (with post-heal imatrix & down Hessians
    collected strictly on Calib v2, zero eval E leakage).
  - Verifies OPUS §1.D2c (iii): per-layer `down` output rel-L2 of GSQ `Q2_0` < stock `quantize_q2_0` on E.
  - Escalation check: `KL_mix(R320) <= 0.020` and `top1_mix(R320) >= 0.97`, else STOP & escalate.
  - B1 (Q2_0) validity check: `KL_mix(V1) - KL_mix(R320) <= 2.0 * (KL_mix(V4) - KL_mix(R288))`
    else Q2_0 is rejected outright => V4.
  - Picks min `KL_mix = 0.6 * KL_EN + 0.4 * KL_RU` among valid {V1..V4}; ties within 5% broken by
    larger K, then higher-bit gate_up (`V1 > V2 > V3 > V4`).
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from scripts.v2.assemble_gguf import VARIANT_SPECS
from scripts.v2.common_io import (
    DEFAULT_GPU_RUNS_LOG,
    DONOR_DIR,
    RUNS_DIR,
    STAGE_DIR,
    ResumablePingPong,
    append_gpu_resume_log,
    assert_zero_swap_and_mem,
    capture_v2_swap_baseline,
    compare_files_byte_equal,
    evict_stage_dir_page_cache,
    read_linux_mem_telemetry,
)
from scripts.v2.cupy_moe_backend import (
    MoELayerWeights,
    PostHealStatsCollector,
    ReapHopeRcoAccumulator,
    forward_moe_v2,
    free_cupy_pools,
    route_topk_exact_np,
    verify_cupy_gdn_and_attn_parity,
    verify_moe_backend_vs_fp64,
)
from scripts.v2.expert_selectors import (
    build_quota_locks,
    select_a1_open_reap,
    select_a2_quota_reap,
    select_a3_quota_hope,
    select_a4_prime_greedy_rco,
)
from scripts.v2.gsq_q2_0 import LibGGMLQuantSimulator, gsq_quantize_layer_down_exps
from scripts.v2.healing_c3 import C3HealResult, heal_layer_c3
from scripts.v2.model_runner import (
    SingleLayerContext,
    load_text_cfg_and_index,
    prepare_jsonl_samples_and_initial_states,
    run_layer_resume_determinism_probe,
)
from scripts.v2.prequant_gate import compute_kl_and_top1_from_hidden

CANONICAL_LAYERS = (2, 14, 28, 42)
TARGET_KS = (320, 288)
# Tie-break preference within 5% KL_mix: larger K (320 > 288), then higher-bit gate_up (IQ3_S > IQ3_XXS > IQ2_S)
VARIANT_TIEBREAK_PRIORITY = {"V1": 0, "V2": 1, "V3": 2, "V4": 3}


def decide_stage_2a_winner(
    results_by_k: Dict[int, Dict[str, Dict[str, Any]]],
    canonical_layers: Sequence[int] = CANONICAL_LAYERS,
) -> Dict[str, Any]:
    """Deterministic Stage 2a decision engine implementing OPUS §1.D2a rules verbatim."""
    decisions: Dict[int, Dict[str, Any]] = {}
    for k_val, arm_map in results_by_k.items():
        a1 = arm_map["A1"]
        a1_ru_mean = float(np.mean([a1["per_layer"][str(l)]["r_ru"] for l in canonical_layers]))

        scored_arms: Dict[str, Dict[str, Any]] = {}
        for arm in ("A1", "A2", "A3", "A4_prime"):
            if arm not in arm_map:
                continue
            d = arm_map[arm]
            r_en_list = [float(d["per_layer"][str(l)]["r_en"]) for l in canonical_layers]
            r_ru_list = [float(d["per_layer"][str(l)]["r_ru"]) for l in canonical_layers]
            s_per_layer = [0.6 * en + 0.4 * ru for en, ru in zip(r_en_list, r_ru_list)]
            mean_en = float(np.mean(r_en_list))
            mean_ru = float(np.mean(r_ru_list))
            s_comp = 0.6 * mean_en + 0.4 * mean_ru
            quota_ok = bool(d.get("quota_locked_100pct", arm != "A1"))
            beats_a1_ru = bool(mean_ru < a1_ru_mean) if arm != "A1" else False
            cov_en_vals = [
                float(d["per_layer"][str(l)].get("router_cov_en", 0.0)) for l in canonical_layers
            ]
            cov_ru_vals = [
                float(d["per_layer"][str(l)].get("router_cov_ru", 0.0)) for l in canonical_layers
            ]
            scored_arms[arm] = {
                "mean_r_en": round(mean_en, 6),
                "mean_r_ru": round(mean_ru, 6),
                "composite_S": round(s_comp, 6),
                "per_layer_S": [round(x, 6) for x in s_per_layer],
                "mean_router_cov_en": round(float(np.mean(cov_en_vals)), 6),
                "mean_router_cov_ru": round(float(np.mean(cov_ru_vals)), 6),
                "quota_locked_100pct": quota_ok,
                "beats_a1_ru": beats_a1_ru,
                "eligible": (arm != "A1") and quota_ok and beats_a1_ru,
            }

        # OPUS §1.D2a Ruling (2026-11-15): quota-lock health check is judged strictly on A2
        # (which differs from A1 solely by locks). Non-A2 arms failing beats_a1_ru (e.g. A3)
        # are disqualified (eligible=False), NOT an escalation STOP.
        quota_arms_present = [q for q in ("A2", "A3", "A4_prime") if q in scored_arms]
        all_quota_beat_a1_ru = all(scored_arms[q]["beats_a1_ru"] for q in quota_arms_present)
        all_quota_locks_ok = all(scored_arms[q]["quota_locked_100pct"] for q in quota_arms_present)

        a2_info = scored_arms["A2"]
        a2_locks_healthy = bool(a2_info["beats_a1_ru"] and a2_info["quota_locked_100pct"])
        a2_s = float(a2_info["composite_S"])
        a2_layer_s = a2_info["per_layer_S"]

        best_arm: Optional[str] = "A2" if a2_locks_healthy else None
        best_s = a2_s if best_arm == "A2" else float("inf")

        for challenger in ("A3", "A4_prime"):
            if challenger not in scored_arms:
                continue
            ch = scored_arms[challenger]
            if not ch["eligible"]:
                ch["beats_a2_rule"] = False
                continue
            rel_gain_vs_a2 = (a2_s - float(ch["composite_S"])) / max(a2_s, 1e-12)
            worst_layer_ratio = max(
                float(cs) / max(float(a2s), 1e-12)
                for cs, a2s in zip(ch["per_layer_S"], a2_layer_s)
            )
            ch["rel_gain_vs_a2"] = round(rel_gain_vs_a2, 6)
            ch["worst_layer_ratio_vs_a2"] = round(worst_layer_ratio, 6)
            passes_tiebreak = (rel_gain_vs_a2 >= 0.03) and (worst_layer_ratio <= 1.15)
            ch["beats_a2_rule"] = passes_tiebreak

            if best_arm is not None and passes_tiebreak and float(ch["composite_S"]) < best_s:
                best_arm = challenger
                best_s = float(ch["composite_S"])

        decisions[int(k_val)] = {
            "winner_selector": best_arm,
            "a2_quota_locks_healthy": a2_locks_healthy,
            "all_quota_beat_a1_ru": all_quota_beat_a1_ru,
            "all_quota_locks_100pct": all_quota_locks_ok,
            "escalate_opus": best_arm is None,
            "a1_mean_r_ru": round(a1_ru_mean, 6),
            "arms": scored_arms,
        }

    any_escalate = any(decisions[k]["escalate_opus"] for k in decisions)
    w320 = decisions[320]["winner_selector"]
    w288 = decisions[288]["winner_selector"]
    global_winner = None if any_escalate else (w320 or w288)
    return {
        "global_winner_selector": global_winner,
        "escalate_opus": any_escalate or (global_winner is None),
        "by_k": decisions,
    }


def check_r320_a2_overfitting_control(
    r320_primary_stats: Dict[str, float],
    r320_a2_stats: Dict[str, float],
    primary_selector: str,
) -> Dict[str, Any]:
    """OPUS §1.D2a Ruling overfitting control: compare R320(primary_selector) vs R320(A2) on splice KL_mix.

    If `primary_selector != 'A2'` and `KL_mix(R320_primary) >= KL_mix(R320_A2)`, overfitting control
    triggers and switches `effective_selector` to `'A2'`.
    """
    kl_p = 0.6 * float(r320_primary_stats["kl_en"]) + 0.4 * float(r320_primary_stats["kl_ru"])
    t1_p = 0.6 * float(r320_primary_stats["top1_en"]) + 0.4 * float(r320_primary_stats["top1_ru"])
    kl_a2 = 0.6 * float(r320_a2_stats["kl_en"]) + 0.4 * float(r320_a2_stats["kl_ru"])
    t1_a2 = 0.6 * float(r320_a2_stats["top1_en"]) + 0.4 * float(r320_a2_stats["top1_ru"])

    if primary_selector == "A2":
        beats_a2: Optional[bool] = None
        triggered = False
        effective = "A2"
    else:
        beats_a2 = bool(kl_p < kl_a2)
        triggered = not beats_a2
        effective = primary_selector if beats_a2 else "A2"

    return {
        "primary_selector": str(primary_selector),
        "effective_selector": str(effective),
        "overfit_control_triggered": bool(triggered),
        "a4_prime_beats_a2_splice": beats_a2,
        "r320_primary": {
            **r320_primary_stats,
            "kl_mix": round(kl_p, 6),
            "top1_mix": round(t1_p, 6),
        },
        "r320_a2_control": {
            **r320_a2_stats,
            "kl_mix": round(kl_a2, 6),
            "top1_mix": round(t1_a2, 6),
        },
    }


def decide_stage_2b_winner(stage2b_metrics: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """Deterministic Stage 2b decision engine implementing OPUS §1.D2b & §1.D2c rules verbatim."""
    enriched: Dict[str, Dict[str, Any]] = {}
    for k, m in stage2b_metrics.items():
        kl_mix = 0.6 * float(m["kl_en"]) + 0.4 * float(m["kl_ru"])
        top1_mix = 0.6 * float(m["top1_en"]) + 0.4 * float(m["top1_ru"])
        enriched[k] = {
            **m,
            "kl_mix": round(kl_mix, 6),
            "top1_mix": round(top1_mix, 6),
        }

    r320 = enriched["R320"]
    r288 = enriched["R288"]

    # OPUS §1.D2b provisional absolute 4-layer go/no-go: KL_mix(R320) <= 0.020, top-1 >= 97%
    r320_kl = float(r320["kl_mix"])
    r320_t1 = float(r320["top1_mix"])
    r320_pass = (r320_kl <= 0.020) and (r320_t1 >= 0.97)
    # Classify miss severity per OPUS §1.D2b.1 (<=25% miss compares top-1 directly: >= 0.75 * 0.97)
    r320_within_25pct = (r320_kl <= (1.25 * 0.020)) and (r320_t1 >= (0.75 * 0.97))

    delta_v4 = max(float(enriched["V4"]["kl_mix"]) - float(r288["kl_mix"]), 1e-6)
    enriched["V4"]["added_quant_kl"] = round(delta_v4, 6)
    enriched["V4"]["q2_0_valid"] = True
    enriched["V4"]["eligible"] = True

    added_v1 = max(0.0, float(enriched["V1"]["kl_mix"]) - float(r320["kl_mix"]))
    # OPUS §1.D2b B1 (Q2_0) validity: KL(V1)-KL(R320) <= 2.0 * (KL(V4)-KL(R288)) else Q2_0 rejected outright => V4
    b1_q2_0_global_valid = added_v1 <= (2.0 * delta_v4)

    for vid, ref_key in (("V1", "R320"), ("V2", "R320"), ("V3", "R288")):
        if vid not in enriched:
            continue
        added = max(0.0, float(enriched[vid]["kl_mix"]) - float(enriched[ref_key]["kl_mix"]))
        indiv_ok = added <= (2.0 * delta_v4)
        q2_ok = bool(b1_q2_0_global_valid and indiv_ok)
        enriched[vid]["added_quant_kl"] = round(added, 6)
        enriched[vid]["added_kl_ratio_vs_v4"] = round(added / delta_v4, 4)
        enriched[vid]["q2_0_valid"] = q2_ok
        enriched[vid]["eligible"] = q2_ok

    if not b1_q2_0_global_valid:
        valid_variants = ["V4"]
        min_kl = float(enriched["V4"]["kl_mix"])
        tied_within_5pct = ["V4"]
        selected_candidate = "V4"
    else:
        valid_variants = [v for v in ("V1", "V2", "V3", "V4") if v in enriched and enriched[v]["eligible"]]
        min_kl = min(float(enriched[v]["kl_mix"]) for v in valid_variants)
        # OPUS §1.D2b: "Pick min KL_mix among V1..V4; ties within 5% => larger K, then higher-bit gate_up."
        tied_within_5pct = [
            v for v in valid_variants if float(enriched[v]["kl_mix"]) <= (1.05 * min_kl + 1e-12)
        ]
        tied_within_5pct.sort(key=lambda v: (VARIANT_TIEBREAK_PRIORITY[v], float(enriched[v]["kl_mix"])))
        selected_candidate = tied_within_5pct[0]

    winner = selected_candidate if r320_pass else None
    esc_reason = None
    if not r320_pass:
        sev = "MISS_LE_25PCT" if r320_within_25pct else "MISS_GT_25PCT_STOP"
        esc_reason = (
            f"{sev}: R320 kl_mix={r320['kl_mix']} (limit <=0.020), "
            f"top1_mix={r320['top1_mix']} (limit >=0.97)"
        )

    return {
        "winner_variant": winner,
        "provisional_best_variant_if_approved": selected_candidate,
        "b1_q2_0_global_valid": b1_q2_0_global_valid,
        "min_eligible_kl_mix": round(min_kl, 6),
        "tied_within_5pct": tied_within_5pct,
        "winner_spec": (
            {
                "variant_id": VARIANT_SPECS[winner].variant_id,
                "target_k": VARIANT_SPECS[winner].target_k,
                "gate_up_exps_qtype": VARIANT_SPECS[winner].gate_up_exps_qtype,
                "down_exps_qtype": VARIANT_SPECS[winner].down_exps_qtype,
                "use_gsq_q2_0_splice": VARIANT_SPECS[winner].use_gsq_q2_0_splice,
            }
            if winner is not None
            else None
        ),
        "r320_splice_gate_passed": r320_pass,
        "r320_within_25pct_band": r320_within_25pct,
        "escalate_opus": not r320_pass or (winner is None),
        "escalation_reason": esc_reason,
        "variants": enriched,
    }


def _compute_donor_topk_mass_coverage(
    gate_donor_f32: np.ndarray,
    x_eval_f32: np.ndarray,
    keep_idx: np.ndarray,
    top_k: int = 10,
) -> float:
    """Compute fraction of donor top-k router probability mass retained by `keep_idx`."""
    logits = x_eval_f32 @ gate_donor_f32.T
    topk_w, topk_i, _ = route_topk_exact_np(logits, top_k=top_k, norm_topk_prob=True)
    kept_mask = np.zeros(gate_donor_f32.shape[0], dtype=bool)
    kept_mask[keep_idx] = True
    in_kept = kept_mask[topk_i]
    cov_per_tok = np.sum(np.where(in_kept, topk_w, 0.0), axis=-1)
    return float(np.mean(cov_per_tok))


def _snapshot_moe_cpu_arrays(moe_w: MoELayerWeights) -> Dict[str, Any]:
    """Copy a healed MoELayerWeights onto compact FP16 CPU NumPy arrays in 16-expert slices
    (0 multi-GiB pinned DMA, saving ~3 GiB host RAM vs FP32) so VRAM can be freed immediately."""
    if moe_w.backend == "cupy":
        from scripts.v2.cupy_moe_backend import (
            _get_cupy,
            cupy_download_3d_chunked,
            free_cupy_pinned_pool,
        )

        cp = _get_cupy()
        gw_np = cp.asnumpy(moe_w.gate_w)
        sh_g_np = cp.asnumpy(moe_w.sh_gate).astype(np.float16)
        sh_u_np = cp.asnumpy(moe_w.sh_up).astype(np.float16)
        sh_d_np = cp.asnumpy(moe_w.sh_down).astype(np.float16)
        sh_inp_np = cp.asnumpy(moe_w.sh_inp_gate)
        free_cupy_pinned_pool()
        gu_np = cupy_download_3d_chunked(moe_w.gate_up, out_dtype=np.float16, chunk_experts=16)
        dn_np = cupy_download_3d_chunked(moe_w.down, out_dtype=np.float16, chunk_experts=16)
        return {
            "gw": gw_np,
            "gu": gu_np,
            "dn": dn_np,
            "sh_g": sh_g_np,
            "sh_u": sh_u_np,
            "sh_d": sh_d_np,
            "sh_inp": sh_inp_np,
            "top_k": int(moe_w.top_k),
            "norm_topk_prob": bool(moe_w.norm_topk_prob),
        }
    return {
        "gw": moe_w.gate_w.copy(),
        "gu": moe_w.gate_up.astype(np.float16, copy=True),
        "dn": moe_w.down.astype(np.float16, copy=True),
        "sh_g": moe_w.sh_gate.astype(np.float16, copy=True),
        "sh_u": moe_w.sh_up.astype(np.float16, copy=True),
        "sh_d": moe_w.sh_down.astype(np.float16, copy=True),
        "sh_inp": moe_w.sh_inp_gate.copy(),
        "top_k": int(moe_w.top_k),
        "norm_topk_prob": bool(moe_w.norm_topk_prob),
    }


def _evaluate_gsq_vs_stock_q2_0_down_on_eval(
    cpu_snap: Dict[str, Any],
    dn_gsq_dq: np.ndarray,
    dn_stock_dq: np.ndarray,
    h_ev_all_f32: np.ndarray,
) -> Dict[str, float]:
    """OPUS §1.D2c (iii): verify per-layer `down` output rel-L2 of GSQ < stock quantize_q2_0 on E."""
    gw = cpu_snap["gw"]
    gu = cpu_snap["gu"]
    dn_ref = cpu_snap["dn"]

    n_tok, h_dim = h_ev_all_f32.shape
    inter = dn_ref.shape[2]
    logits = h_ev_all_f32 @ gw.T
    topk_w, topk_i, _ = route_topk_exact_np(logits, top_k=int(cpu_snap["top_k"]), norm_topk_prob=True)

    y_ref = np.zeros((n_tok, h_dim), dtype=np.float32)
    y_gsq = np.zeros((n_tok, h_dim), dtype=np.float32)
    y_stk = np.zeros((n_tok, h_dim), dtype=np.float32)

    x16 = h_ev_all_f32.astype(np.float16).astype(np.float32)
    for e_id in np.unique(topk_i):
        t_pos, s_pos = np.where(topk_i == e_id)
        eid = int(e_id)
        gu_o = x16[t_pos] @ gu[eid].astype(np.float32).T
        gp, up = gu_o[:, :inter], gu_o[:, inter:]
        act = ((gp / (1.0 + np.exp(-np.clip(gp, -80.0, 80.0)))) * up).astype(np.float16).astype(np.float32)
        w = topk_w[t_pos, s_pos][:, None]
        np.add.at(y_ref, t_pos, w * (act @ dn_ref[eid].astype(np.float32).T))
        np.add.at(y_gsq, t_pos, w * (act @ dn_gsq_dq[eid].astype(np.float32).T))
        np.add.at(y_stk, t_pos, w * (act @ dn_stock_dq[eid].astype(np.float32).T))

    denom = max(float(np.linalg.norm(y_ref)), 1e-12)
    rel_gsq = float(np.linalg.norm(y_ref - y_gsq) / denom)
    rel_stk = float(np.linalg.norm(y_ref - y_stk) / denom)
    return {
        "down_rel_l2_gsq_q2_0": round(rel_gsq, 6),
        "down_rel_l2_stock_q2_0": round(rel_stk, 6),
        "gsq_beats_stock": bool(rel_gsq < rel_stk),
    }


def _build_quant_simulated_moe_from_cpu_snap(
    cpu_snap: Dict[str, Any],
    post_heal_stats: PostHealStatsCollector,
    variant_id: str,
    sim: LibGGMLQuantSimulator,
    backend: str,
    cached_gsq_dn_dq: Optional[np.ndarray] = None,
) -> Tuple[MoELayerWeights, Optional[np.ndarray]]:
    """Build a quantized-and-dequantized MoELayerWeights from FP16 CPU arrays in 16-expert slices."""
    spec = VARIANT_SPECS[variant_id]
    gw = cpu_snap["gw"]
    gu = cpu_snap["gu"]
    dn = cpu_snap["dn"]
    sh_g = cpu_snap["sh_g"]
    sh_u = cpu_snap["sh_u"]
    sh_d = cpu_snap["sh_d"]
    sh_inp = cpu_snap["sh_inp"]

    k_exp = gw.shape[0]
    inter = dn.shape[2]
    bid = post_heal_stats.bid

    imat_gu = np.stack(
        [
            post_heal_stats.imatrix.normalized_vector_for_expert(
                f"blk.{bid}.ffn_gate_exps.weight", k
            )
            for k in range(k_exp)
        ],
        axis=0,
    )
    gu_dq_fp16 = np.empty_like(gu, dtype=np.float16)
    gu_dq_fp16[:, :inter, :] = sim.quantize_dequantize_3d_experts(
        gu[:, :inter, :], spec.gate_up_exps_qtype, imat_gu, out_dtype=np.float16, chunk_experts=16
    )
    gu_dq_fp16[:, inter:, :] = sim.quantize_dequantize_3d_experts(
        gu[:, inter:, :], spec.gate_up_exps_qtype, imat_gu, out_dtype=np.float16, chunk_experts=16
    )

    gsq_out: Optional[np.ndarray] = cached_gsq_dn_dq
    if spec.use_gsq_q2_0_splice:
        if gsq_out is None:
            _, gsq_out = gsq_quantize_layer_down_exps(
                dn,
                hessians_fn=lambda k: post_heal_stats.get_damped_hessian_f64(k, damp_ratio=0.01),
                out_dtype=np.float16,
                return_dequant=True,
            )
        assert gsq_out is not None
        dn_dq_fp16 = gsq_out
    else:
        imat_dn = np.stack(
            [
                post_heal_stats.imatrix.normalized_vector_for_expert(
                    f"blk.{bid}.ffn_down_exps.weight", k
                )
                for k in range(k_exp)
            ],
            axis=0,
        )
        dn_dq_fp16 = sim.quantize_dequantize_3d_experts(
            dn, spec.down_exps_qtype, imat_dn, out_dtype=np.float16, chunk_experts=16
        )

    moe_q = MoELayerWeights(
        gate_weight_f32=gw,
        gate_up_fp16=gu_dq_fp16,
        down_fp16=dn_dq_fp16,
        sh_gate_fp16=sh_g.astype(np.float16, copy=False),
        sh_up_fp16=sh_u.astype(np.float16, copy=False),
        sh_down_fp16=sh_d.astype(np.float16, copy=False),
        sh_inp_gate_f32=sh_inp,
        top_k=int(cpu_snap["top_k"]),
        norm_topk_prob=bool(cpu_snap["norm_topk_prob"]),
        backend=backend,
    )
    del gu_dq_fp16
    return moe_q, gsq_out


def _run_eval_arm_through_layer(
    ctx: SingleLayerContext,
    moe_obj: MoELayerWeights,
    in_store: Any,
    out_store: Any,
    eval_samples: Sequence[Any],
    hc_count: int,
    hidden_size: int,
) -> None:
    for s in eval_samples:
        hm_in, hyper_ffn, inj_ffn = ctx.forward_pre_moe(in_store.read_seq(s.idx), s)
        y_m = forward_moe_v2(moe_obj, hm_in)
        out_store.write_seq(s.idx, ctx.combine_post_moe(y_m, hyper_ffn, inj_ffn, hc_count, hidden_size))


def _save_wave2_pass1_checkpoint(
    ckpt_path: Path,
    heals_dir: Path,
    completed_layer: int,
    active_slot: str,
    e_pre_canon_ready: bool,
    calib_seq_lengths: Sequence[int],
    eval_seq_lengths: Sequence[int],
    stage2a_raw: Dict[int, Dict[str, Dict[str, Any]]],
    saved_winner_heals: Dict[Tuple[int, str, int], Tuple[np.ndarray, C3HealResult]],
) -> None:
    """Persist atomic Pass-1 checkpoint JSON + compressed NPZ heal results."""
    heals_dir.mkdir(parents=True, exist_ok=True)
    heal_entries: List[Dict[str, Any]] = []
    for (k_val, arm_name, bid), (keep_idx, hr) in sorted(saved_winner_heals.items()):
        fname = f"heal_k{int(k_val)}_{arm_name}_l{int(bid):02d}.npz"
        fpath = heals_dir / fname
        if not fpath.is_file():
            tmp_npz = heals_dir / f"heal_k{int(k_val)}_{arm_name}_l{int(bid):02d}.tmp.npz"
            np.savez(
                tmp_npz,
                keep_idx=np.asarray(keep_idx, dtype=np.int64),
                w_gate_f32=np.asarray(hr.w_gate_f32, dtype=np.float32),
                alpha_scales=np.asarray(hr.alpha_scales, dtype=np.float32),
                w_down_shexp_f32=np.asarray(hr.w_down_shexp_f32, dtype=np.float32),
            )
            os.replace(tmp_npz, fpath)
        heal_entries.append(
            {
                "k_val": int(k_val),
                "arm_name": str(arm_name),
                "bid": int(bid),
                "npz_file": fname,
                "c1_accepted": bool(hr.c1_accepted),
                "c2_alpha_accepted": bool(hr.c2_alpha_accepted),
                "c2_shexp_accepted": bool(hr.c2_shexp_accepted),
                "val_rel_l2_before": float(hr.val_rel_l2_before),
                "val_rel_l2_after_c1": float(hr.val_rel_l2_after_c1),
                "val_rel_l2_after_c2_alpha": float(hr.val_rel_l2_after_c2_alpha),
                "val_rel_l2_after_c3": float(hr.val_rel_l2_after_c3),
                "metrics": hr.metrics,
            }
        )

    payload = {
        "completed_layer": int(completed_layer),
        "active_slot": str(active_slot),
        "e_pre_canon_ready": bool(e_pre_canon_ready),
        "calib_seq_lengths": [int(x) for x in calib_seq_lengths],
        "eval_seq_lengths": [int(x) for x in eval_seq_lengths],
        "stage2a_raw": {str(k): v for k, v in stage2a_raw.items()},
        "saved_heals_index": heal_entries,
    }
    tmp_json = ckpt_path.with_suffix(".json.tmp")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp_json, ckpt_path)


def _load_wave2_pass1_checkpoint(ckpt_path: Path, heals_dir: Path) -> Dict[str, Any]:
    with open(ckpt_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    stage2a_raw: Dict[int, Dict[str, Dict[str, Any]]] = {
        int(k): v for k, v in raw.get("stage2a_raw", {}).items()
    }
    saved_heals: Dict[Tuple[int, str, int], Tuple[np.ndarray, C3HealResult]] = {}
    for item in raw.get("saved_heals_index", []):
        npz_path = heals_dir / str(item["npz_file"])
        with np.load(npz_path) as d:
            keep_idx = d["keep_idx"].astype(np.int64)
            hr = C3HealResult(
                w_gate_f32=d["w_gate_f32"].astype(np.float32),
                alpha_scales=d["alpha_scales"].astype(np.float32),
                w_down_shexp_f32=d["w_down_shexp_f32"].astype(np.float32),
                c1_accepted=bool(item["c1_accepted"]),
                c2_alpha_accepted=bool(item["c2_alpha_accepted"]),
                c2_shexp_accepted=bool(item["c2_shexp_accepted"]),
                val_rel_l2_before=float(item["val_rel_l2_before"]),
                val_rel_l2_after_c1=float(item["val_rel_l2_after_c1"]),
                val_rel_l2_after_c2_alpha=float(item["val_rel_l2_after_c2_alpha"]),
                val_rel_l2_after_c3=float(item["val_rel_l2_after_c3"]),
                metrics=dict(item.get("metrics", {})),
            )
        saved_heals[(int(item["k_val"]), str(item["arm_name"]), int(item["bid"]))] = (keep_idx, hr)
    raw["stage2a_raw"] = stage2a_raw
    raw["saved_winner_heals"] = saved_heals
    return raw


def run_wave2_pipeline(
    calib_jsonl: Path,
    eval_jsonl: Path,
    out_dir: Path = RUNS_DIR / "wave2",
    summary_json_path: Path = RUNS_DIR / "wave2_shootout_summary.json",
    stage_dir: Path = STAGE_DIR / "wave2",
    donor_dir: Path = DONOR_DIR,
    backend: str = "cupy",
    max_calib_samples: int = 640,
    max_eval_samples: int = 128,
    calib_max_seq_len: int = 2048,
    eval_max_seq_len: int = 4096,
    noncanon_batch_seqs: int = 16,
    canonical_layers: Sequence[int] = CANONICAL_LAYERS,
    allow_resume: bool = True,
    gpu_log_path: Path = DEFAULT_GPU_RUNS_LOG,
) -> Dict[str, Any]:
    """Execute full Wave 2 Stage 2a + Stage 2b shootout under OPUS §0.3a Zero-Disk-Swap SLA."""
    from transformers.models.qwen4_exp.modeling_qwen4_exp import (
        Qwen4ExpTextGatedResidual,
        Qwen4ExpTextRotaryEmbedding,
    )
    from scripts.v2.common_io import free_submodule_to_meta, materialize_submodule
    from scripts.v2.cupy_moe_backend import CuPyLinearPatch

    t_start = time.perf_counter()
    out_dir = Path(out_dir)
    stage_dir = Path(stage_dir)
    heals_dir = stage_dir / "saved_heals"
    out_dir.mkdir(parents=True, exist_ok=True)
    stage_dir.mkdir(parents=True, exist_ok=True)
    summary_json_path = Path(summary_json_path)
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)

    canon_tuple = tuple(int(x) for x in canonical_layers)
    canon_set = set(canon_tuple)
    min_canon = min(canon_tuple)
    max_canon = max(canon_tuple)

    evict_stage_dir_page_cache(stage_dir)
    swap_baseline = capture_v2_swap_baseline()
    tel0 = read_linux_mem_telemetry()

    text_cfg, st_index = load_text_cfg_and_index(donor_dir)
    hc_count = int(text_cfg.hc_count)
    hidden_size = int(text_cfg.hidden_size)
    n_layers = int(text_cfg.num_hidden_layers)
    rotary_emb = Qwen4ExpTextRotaryEmbedding(config=text_cfg)
    sim = LibGGMLQuantSimulator()

    # Startup kernel & MoE parity self-verification
    moe_parity = verify_moe_backend_vs_fp64(backend=backend)
    if not moe_parity["passed"]:
        raise RuntimeError(f"MoE parity check failed: {moe_parity}")
    layer_kernel_parity = verify_cupy_gdn_and_attn_parity(text_cfg) if backend == "cupy" else {}
    print(
        f"[Wave2] Startup parity OK: moe_rel_l2={moe_parity['rel_l2_error']:.2e} "
        f"kernels={layer_kernel_parity} MemAvail={tel0.mem_available_gib:.2f}GiB",
        flush=True,
    )

    pass1_ckpt_path = stage_dir / "pass1_checkpoint.json"
    c_slot_a_path = stage_dir / "calib_donor_slot_A.bin"
    e_slot_a_path = stage_dir / "eval_donor_slot_A.bin"
    e_pre_canon_a_path = stage_dir / "eval_pre_canon_slot_A.bin"

    has_ckpt = allow_resume and pass1_ckpt_path.is_file() and c_slot_a_path.is_file() and e_slot_a_path.is_file()
    has_bootstrap_bid2 = (
        allow_resume
        and (not has_ckpt)
        and (min_canon == 2)
        and c_slot_a_path.is_file()
        and e_slot_a_path.is_file()
        and e_pre_canon_a_path.is_file()
    )
    skip_emb = bool(has_ckpt or has_bootstrap_bid2)

    calib_samples, _, c_slot_a = prepare_jsonl_samples_and_initial_states(
        calib_jsonl,
        None,
        c_slot_a_path,
        donor_dir=donor_dir,
        max_samples=max_calib_samples,
        max_seq_len=calib_max_seq_len,
        backend=backend,
        skip_embedding_init=skip_emb,
    )
    eval_samples, _, e_slot_a = prepare_jsonl_samples_and_initial_states(
        eval_jsonl,
        None,
        e_slot_a_path,
        donor_dir=donor_dir,
        max_samples=max_eval_samples,
        max_seq_len=eval_max_seq_len,
        backend=backend,
        skip_embedding_init=skip_emb,
    )

    c_seq_lens = [s.seq_len for s in calib_samples]
    e_seq_lens = [s.seq_len for s in eval_samples]
    total_calib_tokens = sum(c_seq_lens)
    total_eval_tokens = sum(e_seq_lens)
    print(
        f"[Wave2] Prepared calib={len(calib_samples)} seqs ({total_calib_tokens} tok), "
        f"eval_E={len(eval_samples)} seqs ({total_eval_tokens} tok) [skip_embedding_init={skip_emb}]",
        flush=True,
    )

    calib_pp = ResumablePingPong(stage_dir, "calib_donor", c_seq_lens, hc_count, hidden_size)
    eval_donor_pp = ResumablePingPong(stage_dir, "eval_donor", e_seq_lens, hc_count, hidden_size)
    eval_pre_canon_pp = ResumablePingPong(stage_dir, "eval_pre_canon", e_seq_lens, hc_count, hidden_size)

    stage2a_raw: Dict[int, Dict[str, Dict[str, Any]]] = {
        320: {a: {"per_layer": {}, "quota_locked_100pct": True} for a in ("A1", "A2", "A3", "A4_prime")},
        288: {a: {"per_layer": {}, "quota_locked_100pct": True} for a in ("A1", "A2", "A3", "A4_prime")},
    }
    saved_winner_heals: Dict[Tuple[int, str, int], Tuple[np.ndarray, C3HealResult]] = {}
    resume_metadata: Optional[Dict[str, Any]] = None

    if has_ckpt:
        ckpt = _load_wave2_pass1_checkpoint(pass1_ckpt_path, heals_dir)
        if ckpt.get("calib_seq_lengths") != c_seq_lens or ckpt.get("eval_seq_lengths") != e_seq_lens:
            raise ValueError("Wave 2 pass1_checkpoint.json seq_lengths mismatch against dataset!")
        completed_layer = int(ckpt["completed_layer"])
        start_bid = completed_layer + 1
        cur_slot = str(ckpt["active_slot"])
        prev_slot = "B" if cur_slot == "A" else "A"
        stage2a_raw = ckpt["stage2a_raw"]
        saved_winner_heals = ckpt["saved_winner_heals"]

        def _slot_marker_clean(slot_name: str) -> bool:
            mf = stage_dir / f"in_progress_slot_{slot_name}.marker"
            if not mf.exists():
                return True
            return mf.read_text(encoding="utf-8", errors="replace").strip().startswith("clean")

        if cur_slot == "B":
            c_slot_b = calib_pp.open_slot("B", create=False)
            e_slot_b = eval_donor_pp.open_slot("B", create=False)
            prev_intact = _slot_marker_clean("A")
            if not prev_intact:
                c_slot_a = calib_pp.open_slot("A", create=True)
                e_slot_a = eval_donor_pp.open_slot("A", create=True)
        else:
            prev_intact = (
                (stage_dir / "calib_donor_slot_B.bin").is_file()
                and (stage_dir / "eval_donor_slot_B.bin").is_file()
                and _slot_marker_clean("B")
            )
            if prev_intact:
                try:
                    c_slot_b = calib_pp.open_slot("B", create=False)
                    e_slot_b = eval_donor_pp.open_slot("B", create=False)
                except ValueError:
                    prev_intact = False
            if not prev_intact:
                c_slot_b = calib_pp.open_slot("B", create=True)
                e_slot_b = eval_donor_pp.open_slot("B", create=True)

        if bool(ckpt.get("e_pre_canon_ready", False)) and e_pre_canon_a_path.is_file():
            e_pre_canon_slot = eval_pre_canon_pp.open_slot("A", create=False)
            e_pre_canon_ready = True
        else:
            e_pre_canon_slot = eval_pre_canon_pp.open_slot("A", create=True)
            e_pre_canon_ready = False

        c_cur = c_slot_a if cur_slot == "A" else c_slot_b
        e_cur = e_slot_a if cur_slot == "A" else e_slot_b
        c_prev = c_slot_b if cur_slot == "A" else c_slot_a
        e_prev = e_slot_b if cur_slot == "A" else e_slot_a

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
                c_in_store=c_prev,
                e_in_store=e_prev,
                c_expected_out_store=c_cur,
                e_expected_out_store=e_cur,
            )
        else:
            probe_res = run_layer_resume_determinism_probe(
                mode="double_recompute",
                probe_bid=min(start_bid, max_canon),
                text_cfg=text_cfg,
                st_index=st_index,
                rotary_emb=rotary_emb,
                backend=backend,
                calib_samples=calib_samples,
                eval_samples=eval_samples,
                c_in_store=c_cur,
                e_in_store=e_cur,
            )

        verified_files = {
            c_cur.bin_path.name: int(c_cur.total_bytes),
            e_cur.bin_path.name: int(e_cur.total_bytes),
        }
        if e_pre_canon_ready:
            verified_files[e_pre_canon_slot.bin_path.name] = int(e_pre_canon_slot.total_bytes)
        append_gpu_resume_log(
            pipeline="wave2_pass1",
            resume_bid=start_bid,
            cur_slot=cur_slot,
            verified_files=verified_files,
            probe_mode=str(probe_res["mode"]),
            probe_max_rel_l2=float(probe_res["max_rel_l2"]),
            log_path=gpu_log_path,
        )
        resume_metadata = {
            "source": "pass1_checkpoint",
            "resume_bid": start_bid,
            "cur_slot": cur_slot,
            "verified_files_bytes": verified_files,
            "determinism_probe": probe_res,
        }
    elif has_bootstrap_bid2:
        # OPUS §0.3a.4 exact bootstrap resume at bid=2, cur_slot="A" from intact post-blk.01 slot_A files
        e_pre_canon_slot = eval_pre_canon_pp.open_slot("A", create=False)
        if not compare_files_byte_equal(e_slot_a.bin_path, e_pre_canon_slot.bin_path):
            raise RuntimeError(
                f"OPUS §0.3a.4 bootstrap rejected: {e_pre_canon_slot.bin_path} != {e_slot_a.bin_path}"
            )
        c_slot_b = calib_pp.open_slot("B", create=True)
        e_slot_b = eval_donor_pp.open_slot("B", create=True)
        start_bid = 2
        cur_slot = "A"
        e_pre_canon_ready = True

        probe_res = run_layer_resume_determinism_probe(
            mode="double_recompute",
            probe_bid=start_bid,
            text_cfg=text_cfg,
            st_index=st_index,
            rotary_emb=rotary_emb,
            backend=backend,
            calib_samples=calib_samples,
            eval_samples=eval_samples,
            c_in_store=c_slot_a,
            e_in_store=e_slot_a,
        )
        verified_files = {
            c_slot_a.bin_path.name: int(c_slot_a.total_bytes),
            e_slot_a.bin_path.name: int(e_slot_a.total_bytes),
            e_pre_canon_slot.bin_path.name: int(e_pre_canon_slot.total_bytes),
        }
        _save_wave2_pass1_checkpoint(
            ckpt_path=pass1_ckpt_path,
            heals_dir=heals_dir,
            completed_layer=1,
            active_slot="A",
            e_pre_canon_ready=True,
            calib_seq_lengths=c_seq_lens,
            eval_seq_lengths=e_seq_lens,
            stage2a_raw=stage2a_raw,
            saved_winner_heals=saved_winner_heals,
        )
        append_gpu_resume_log(
            pipeline="wave2_pass1_bootstrap",
            resume_bid=start_bid,
            cur_slot=cur_slot,
            verified_files=verified_files,
            probe_mode=str(probe_res["mode"]),
            probe_max_rel_l2=float(probe_res["max_rel_l2"]),
            log_path=gpu_log_path,
        )
        resume_metadata = {
            "source": "bootstrap_bid2_slotA",
            "resume_bid": start_bid,
            "cur_slot": cur_slot,
            "verified_files_bytes": verified_files,
            "determinism_probe": probe_res,
        }
    else:
        c_slot_b = calib_pp.open_slot("B", create=True)
        e_slot_b = eval_donor_pp.open_slot("B", create=True)
        e_pre_canon_slot = eval_pre_canon_pp.open_slot("A", create=True)
        start_bid = 0
        cur_slot = "A"
        e_pre_canon_ready = False

    c3_heal_stride = max(1, total_calib_tokens // 65536)

    # Pass 1: Propagate donor through layer max_canon (42), executing Stage 2a at canonical_layers
    for bid in range(start_bid, max_canon + 1):
        t_l0 = time.perf_counter()
        nxt_slot = "B" if cur_slot == "A" else "A"
        dirty_marker = stage_dir / f"in_progress_slot_{nxt_slot}.marker"
        dirty_marker.write_text(f"dirty:{bid}", encoding="utf-8")

        c_in = c_slot_a if cur_slot == "A" else c_slot_b
        c_out = c_slot_a if nxt_slot == "A" else c_slot_b
        e_in = e_slot_a if cur_slot == "A" else e_slot_b
        e_out = e_slot_a if nxt_slot == "A" else e_slot_b

        if bid == min_canon and not e_pre_canon_ready:
            for s in eval_samples:
                e_pre_canon_slot.write_seq(s.idx, e_in.read_seq(s.idx))
            e_pre_canon_ready = True

        ple_in = [s.input_ids for s in calib_samples] + [s.input_ids for s in eval_samples]
        ctx = SingleLayerContext(
            bid=bid, text_cfg=text_cfg, st_index=st_index, rotary_emb=rotary_emb,
            backend=backend, is_mtp=False, preindex_ple_inputs=ple_in,
        )
        moe_donor = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend=backend)

        is_canon = bid in canon_set
        reap_acc = (
            ReapHopeRcoAccumulator(
                num_experts=int(text_cfg.num_experts),
                top_k=int(text_cfg.num_experts_per_tok),
                collect_rco_cache=True,
                rco_max_tokens=16384,
                rco_stride=max(1, total_calib_tokens // 16384),
            )
            if is_canon
            else None
        )

        calib_mlp_sub: List[np.ndarray] = []
        calib_donor_sub: List[np.ndarray] = []

        if is_canon and reap_acc is not None:
            for s in calib_samples:
                reap_acc.set_sample_flags(s.flags)
                h_mlp_in, hyper_ffn, inj_ffn = ctx.forward_pre_moe(c_in.read_seq(s.idx), s)
                y_d = forward_moe_v2(moe_donor, h_mlp_in, flat_token_ids=s.input_ids, reap_acc=reap_acc)
                take_idx = np.arange(0, s.seq_len, c3_heal_stride)
                if take_idx.size > 0:
                    calib_mlp_sub.append(h_mlp_in.to(torch.float32).numpy().reshape(s.seq_len, hidden_size)[take_idx])
                    calib_donor_sub.append(y_d.to(torch.float32).numpy().reshape(s.seq_len, hidden_size)[take_idx])
                c_out.write_seq(s.idx, ctx.combine_post_moe(y_d, hyper_ffn, inj_ffn, hc_count, hidden_size))
        else:
            # Chunked MoE dispatch across noncanon_batch_seqs sequences for high GPU utilization
            for c_start in range(0, len(calib_samples), noncanon_batch_seqs):
                chunk = calib_samples[c_start : c_start + noncanon_batch_seqs]
                pre_list = [ctx.forward_pre_moe(c_in.read_seq(s.idx), s) for s in chunk]
                cat_in = torch.cat([p[0].reshape(-1, hidden_size) for p in pre_list], dim=0)
                cat_yd = forward_moe_v2(moe_donor, cat_in)
                off = 0
                for s, (_, hyper_ffn, inj_ffn) in zip(chunk, pre_list):
                    yd_s = cat_yd[off : off + s.seq_len].view(1, s.seq_len, hidden_size)
                    off += s.seq_len
                    c_out.write_seq(s.idx, ctx.combine_post_moe(yd_s, hyper_ffn, inj_ffn, hc_count, hidden_size))
                del pre_list, cat_in, cat_yd

        eval_mlp_inputs: List[Tuple[bool, np.ndarray, np.ndarray]] = []
        for s in eval_samples:
            h_mlp_in, hyper_ffn, inj_ffn = ctx.forward_pre_moe(e_in.read_seq(s.idx), s)
            y_d = forward_moe_v2(moe_donor, h_mlp_in)
            if is_canon:
                eval_mlp_inputs.append(
                    (
                        s.flags.is_ru,
                        h_mlp_in.to(torch.float32).numpy().reshape(-1, hidden_size),
                        y_d.to(torch.float32).numpy().reshape(-1, hidden_size),
                    )
                )
            e_out.write_seq(s.idx, ctx.combine_post_moe(y_d, hyper_ffn, inj_ffn, hc_count, hidden_size))

        donor_top_k = int(moe_donor.top_k)
        # Release 4.69 GiB donor MoE VRAM immediately before Stage 2a selector/C3 builds
        moe_donor.close()
        free_cupy_pools()

        if is_canon and reap_acc is not None:
            score_dict = reap_acc.finalize_score_dict()
            with open(out_dir / f"layer_{bid:02d}_scores.json", "w", encoding="utf-8") as sf:
                json.dump(score_dict, sf, indent=2)

            locks = build_quota_locks(score_dict)
            h_cal_all = np.concatenate(calib_mlp_sub, axis=0)
            y_cal_all = np.concatenate(calib_donor_sub, axis=0)
            # Persist fp16 calibration MLP inputs so Stage 2b collects post-heal imatrix/Hessians on Calib v2 only
            np.save(stage_dir / f"canon_h_cal_{bid}.npy", h_cal_all.astype(np.float16))

            h_ev_en = np.concatenate([x[1] for x in eval_mlp_inputs if not x[0]], axis=0)
            y_ev_en = np.concatenate([x[2] for x in eval_mlp_inputs if not x[0]], axis=0)
            h_ev_ru = np.concatenate([x[1] for x in eval_mlp_inputs if x[0]], axis=0)
            y_ev_ru = np.concatenate([x[2] for x in eval_mlp_inputs if x[0]], axis=0)

            # Save eval I/O for independent Skeptic Gate W3 r_l recomputation
            np.savez_compressed(
                out_dir / f"canon_eval_io_{bid:02d}.npz",
                h_ev_en=h_ev_en.astype(np.float16),
                y_ev_en=y_ev_en.astype(np.float32),
                h_ev_ru=h_ev_ru.astype(np.float16),
                y_ev_ru=y_ev_ru.astype(np.float32),
            )

            donor_gate_f32 = ctx.layer.mlp.gate.weight.detach().to(torch.float32).cpu().numpy()

            for k_val in TARGET_KS:
                sel_map = {
                    "A1": select_a1_open_reap(score_dict, k_val),
                    "A2": select_a2_quota_reap(score_dict, k_val, locks=locks),
                    "A3": select_a3_quota_hope(score_dict, reap_acc.coact_matrix, k_val, locks=locks),
                    "A4_prime": select_a4_prime_greedy_rco(reap_acc.rco_cache, score_dict, k_val, locks=locks),  # type: ignore[arg-type]
                }
                for arm_name, keep_idx in sel_map.items():
                    np.save(out_dir / f"keep_k{k_val}_{arm_name}_l{bid:02d}.npy", keep_idx)
                    # Stage 2a raw unhealed selector scoring on H_donor over E (OPUS §1.D2a)
                    moe_p = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend=backend, keep_indices=keep_idx)
                    yp_en_raw = forward_moe_v2(moe_p, h_ev_en).numpy()
                    yp_ru_raw = forward_moe_v2(moe_p, h_ev_ru).numpy()

                    r_en = float(np.linalg.norm(y_ev_en - yp_en_raw) / max(np.linalg.norm(y_ev_en), 1e-12))
                    r_ru = float(np.linalg.norm(y_ev_ru - yp_ru_raw) / max(np.linalg.norm(y_ev_ru), 1e-12))
                    cov_en = _compute_donor_topk_mass_coverage(
                        donor_gate_f32, h_ev_en, keep_idx, top_k=donor_top_k
                    )
                    cov_ru = _compute_donor_topk_mass_coverage(
                        donor_gate_f32, h_ev_ru, keep_idx, top_k=donor_top_k
                    )

                    entry: Dict[str, Any] = {
                        "r_en": round(r_en, 6),
                        "r_ru": round(r_ru, 6),
                        "router_cov_en": round(cov_en, 6),
                        "router_cov_ru": round(cov_ru, 6),
                    }

                    # Fit C3 healing on quota selectors (reused in Stage 2b for the Stage 2a winner)
                    if arm_name != "A1":
                        heal_res = heal_layer_c3(moe_p, h_cal_all, y_cal_all)
                        moe_p.close()
                        free_cupy_pools()
                        moe_h = MoELayerWeights.from_hf_moe_block(
                            ctx.layer.mlp,
                            backend=backend,
                            keep_indices=keep_idx,
                            gate_override_f32=heal_res.w_gate_f32,
                            alpha_scales=heal_res.alpha_scales,
                            sh_down_override=heal_res.w_down_shexp_f32,
                        )
                        yp_en_c3 = forward_moe_v2(moe_h, h_ev_en).numpy()
                        yp_ru_c3 = forward_moe_v2(moe_h, h_ev_ru).numpy()
                        moe_h.close()
                        free_cupy_pools()
                        entry["r_en_post_c3"] = round(
                            float(np.linalg.norm(y_ev_en - yp_en_c3) / max(np.linalg.norm(y_ev_en), 1e-12)), 6
                        )
                        entry["r_ru_post_c3"] = round(
                            float(np.linalg.norm(y_ev_ru - yp_ru_c3) / max(np.linalg.norm(y_ev_ru), 1e-12)), 6
                        )
                        entry["c1_accepted"] = heal_res.c1_accepted
                        entry["c2_alpha_accepted"] = heal_res.c2_alpha_accepted
                        entry["c2_shexp_accepted"] = heal_res.c2_shexp_accepted
                        saved_winner_heals[(k_val, arm_name, bid)] = (keep_idx, heal_res)
                    else:
                        moe_p.close()
                        free_cupy_pools()

                    stage2a_raw[k_val][arm_name]["per_layer"][str(bid)] = entry

            del h_cal_all, y_cal_all, h_ev_en, y_ev_en, h_ev_ru, y_ev_ru, calib_mlp_sub, calib_donor_sub

        ctx.close()
        tel_l = assert_zero_swap_and_mem(swap_baseline)
        cur_slot = nxt_slot
        _save_wave2_pass1_checkpoint(
            ckpt_path=pass1_ckpt_path,
            heals_dir=heals_dir,
            completed_layer=bid,
            active_slot=cur_slot,
            e_pre_canon_ready=e_pre_canon_ready,
            calib_seq_lengths=c_seq_lens,
            eval_seq_lengths=e_seq_lens,
            stage2a_raw=stage2a_raw,
            saved_winner_heals=saved_winner_heals,
        )
        dirty_marker.write_text(f"clean:{bid}", encoding="utf-8")
        print(
            f"[Wave2][Pass1] blk.{bid:02d}/{max_canon:02d} {'(CANON)' if is_canon else ''} "
            f"dt={time.perf_counter()-t_l0:.1f}s MemAvail={tel_l.mem_available_gib:.2f}GiB "
            f"disk_swap_kb={tel_l.disk_swap_used_kb} "
            f"zram_d_mib={max(0.0, tel_l.zram_orig_mib - swap_baseline.zram_orig_mib):.1f} "
            f"d_pswpout={tel_l.pswpout - swap_baseline.pswpout}",
            flush=True,
        )

    decision_2a = decide_stage_2a_winner(stage2a_raw, canon_tuple)
    decision_2a["raw_per_layer"] = stage2a_raw
    with open(out_dir / "stage2a_selector_shootout.json", "w", encoding="utf-8") as f:
        json.dump(decision_2a, f, indent=2)

    if decision_2a["escalate_opus"]:
        early_summary = {
            "elapsed_sec": round(time.perf_counter() - t_start, 2),
            "parity_checks": {"moe": moe_parity, "layer_kernels": layer_kernel_parity},
            "resume_info": resume_metadata,
            "stage2a": decision_2a,
            "stage2b": None,
            "escalated": True,
            "escalation_stage": "stage2a",
        }
        for p_out in (out_dir / "wave2_decision_summary.json", summary_json_path):
            with open(p_out, "w", encoding="utf-8") as f:
                json.dump(early_summary, f, indent=2)
        free_cupy_pools()
        return early_summary

    win_sel = str(decision_2a["global_winner_selector"])
    print(f"[Wave2] Stage 2a WINNER selector = {win_sel}", flush=True)

    # Stage 2b: Stream from min_canon (2) to n_layers-1 (47) on eval_E across DONOR + spliced arms
    # Includes R320_A2 overfitting control per OPUS §1.D2a Ruling whenever win_sel != 'A2'
    from scripts.v2.prequant_gate import upload_2d_fp16_chunked_cupy

    s2b_ckpt_path = stage_dir / "stage2b_checkpoint.json"

    def _run_stage_2b_for_selector(
        eval_selector: str,
        include_r320_a2_control: bool,
        reset_checkpoint: bool = False,
    ) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Any]]:
        arm_names: Tuple[str, ...] = (
            ("DONOR", "R320", "R320_A2", "R288", "V1", "V2", "V3", "V4")
            if include_r320_a2_control
            else ("DONOR", "R320", "R288", "V1", "V2", "V3", "V4")
        )
        pps = {
            arm: ResumablePingPong(stage_dir, f"s2b_{arm}", e_seq_lens, hc_count, hidden_size)
            for arm in arm_names
        }
        s2b_ckpt: Optional[Dict[str, Any]] = None
        if (not reset_checkpoint) and allow_resume and s2b_ckpt_path.is_file():
            with open(s2b_ckpt_path, "r", encoding="utf-8") as sf:
                cand_ckpt = json.load(sf)
            if (
                cand_ckpt.get("eval_seq_lengths") == e_seq_lens
                and cand_ckpt.get("win_sel") == eval_selector
                and tuple(cand_ckpt.get("arm_names", ())) == arm_names
            ):
                s2b_ckpt = cand_ckpt

        if s2b_ckpt is not None:
            s2b_start_bid = int(s2b_ckpt["completed_layer"]) + 1
            cur_s = str(s2b_ckpt["active_slot"])
            gsq_by_l: Dict[str, Any] = dict(s2b_ckpt.get("gsq_vs_stock_by_layer", {}))
            slots_a = {arm: pps[arm].open_slot("A", create=(cur_s != "A")) for arm in arm_names}
            slots_b = {arm: pps[arm].open_slot("B", create=(cur_s != "B")) for arm in arm_names}
            print(
                f"[Wave2][Stage2b] Resuming Stage 2b ({eval_selector}) at bid={s2b_start_bid}, slot={cur_s}",
                flush=True,
            )
        else:
            slots_a = {arm: pps[arm].open_slot("A", create=True) for arm in arm_names}
            slots_b = {arm: pps[arm].open_slot("B", create=True) for arm in arm_names}
            for arm in arm_names:
                for s in eval_samples:
                    slots_a[arm].write_seq(s.idx, e_pre_canon_slot.read_seq(s.idx))
            gsq_by_l = {}
            s2b_start_bid = min_canon
            cur_s = "A"

        for bid in range(s2b_start_bid, n_layers):
            t_s2b = time.perf_counter()
            nxt_s = "B" if cur_s == "A" else "A"
            in_map = slots_a if cur_s == "A" else slots_b
            out_map = slots_a if nxt_s == "A" else slots_b

            ple_in = [s.input_ids for s in eval_samples]
            ctx = SingleLayerContext(
                bid=bid,
                text_cfg=text_cfg,
                st_index=st_index,
                rotary_emb=rotary_emb,
                backend=backend,
                is_mtp=False,
                preindex_ple_inputs=ple_in,
            )

            if bid in canon_set:
                # 1. Propagate DONOR arm first, then immediately release 4.69 GiB donor MoE VRAM
                moe_d = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend=backend)
                _run_eval_arm_through_layer(
                    ctx, moe_d, in_map["DONOR"], out_map["DONOR"], eval_samples, hc_count, hidden_size
                )
                moe_d.close()
                free_cupy_pools()

                # 2. Propagate R320_A2 overfitting control (if enabled), keeping max 1 MoE in VRAM
                if include_r320_a2_control:
                    keep_a2, heal_a2 = saved_winner_heals[(320, "A2", bid)]
                    moe_r320_a2 = MoELayerWeights.from_hf_moe_block(
                        ctx.layer.mlp,
                        backend=backend,
                        keep_indices=keep_a2,
                        gate_override_f32=heal_a2.w_gate_f32,
                        alpha_scales=heal_a2.alpha_scales,
                        sh_down_override=heal_a2.w_down_shexp_f32,
                    )
                    _run_eval_arm_through_layer(
                        ctx,
                        moe_r320_a2,
                        in_map["R320_A2"],
                        out_map["R320_A2"],
                        eval_samples,
                        hc_count,
                        hidden_size,
                    )
                    moe_r320_a2.close()
                    free_cupy_pools()

                h_cal_saved = np.load(stage_dir / f"canon_h_cal_{bid}.npy").astype(np.float32)
                ev_io = np.load(out_dir / f"canon_eval_io_{bid:02d}.npz")
                h_ev_all = np.concatenate(
                    [ev_io["h_ev_en"].astype(np.float32), ev_io["h_ev_ru"].astype(np.float32)], axis=0
                )

                # 3. Propagate each healed reference & quantized arm sequentially (max 1 MoE in VRAM <= 5.2 GiB)
                for k_val, r_name, v_list in ((320, "R320", ("V1", "V2")), (288, "R288", ("V3", "V4"))):
                    keep_idx, heal_res = saved_winner_heals[(k_val, eval_selector, bid)]
                    moe_rk = MoELayerWeights.from_hf_moe_block(
                        ctx.layer.mlp,
                        backend=backend,
                        keep_indices=keep_idx,
                        gate_override_f32=heal_res.w_gate_f32,
                        alpha_scales=heal_res.alpha_scales,
                        sh_down_override=heal_res.w_down_shexp_f32,
                    )
                    _run_eval_arm_through_layer(
                        ctx, moe_rk, in_map[r_name], out_map[r_name], eval_samples, hc_count, hidden_size
                    )

                    ph_stats = PostHealStatsCollector(
                        bid=bid,
                        num_experts=k_val,
                        hidden_dim=hidden_size,
                        inter_dim=int(text_cfg.moe_intermediate_size),
                    )
                    # Collect post-heal imatrix & Hessians strictly on Calib v2 subsample (in 8k-token slices)
                    for off in range(0, h_cal_saved.shape[0], 8192):
                        _ = forward_moe_v2(moe_rk, h_cal_saved[off : off + 8192], post_heal=ph_stats)

                    cpu_snap = _snapshot_moe_cpu_arrays(moe_rk)
                    moe_rk.close()
                    free_cupy_pools()

                    cached_gsq_dq: Optional[np.ndarray] = None
                    for vid in v_list:
                        moe_v, cached_gsq_dq = _build_quant_simulated_moe_from_cpu_snap(
                            cpu_snap, ph_stats, vid, sim, backend=backend, cached_gsq_dn_dq=cached_gsq_dq
                        )
                        _run_eval_arm_through_layer(
                            ctx, moe_v, in_map[vid], out_map[vid], eval_samples, hc_count, hidden_size
                        )
                        moe_v.close()
                        free_cupy_pools()

                    if k_val == 320 and cached_gsq_dq is not None:
                        dn_stock_q2 = sim.quantize_dequantize_3d_experts(
                            cpu_snap["dn"], "q2_0", None, out_dtype=np.float16, chunk_experts=16
                        )
                        gsq_by_l[str(bid)] = _evaluate_gsq_vs_stock_q2_0_down_on_eval(
                            cpu_snap, cached_gsq_dq, dn_stock_q2, h_ev_all
                        )
                        del dn_stock_q2

                    del ph_stats, cpu_snap, cached_gsq_dq
                    gc.collect()

                del h_cal_saved, h_ev_all
            else:
                moe_d = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend=backend)
                for arm in arm_names:
                    _run_eval_arm_through_layer(
                        ctx, moe_d, in_map[arm], out_map[arm], eval_samples, hc_count, hidden_size
                    )
                moe_d.close()
                free_cupy_pools()

            ctx.close()
            tel_2b = assert_zero_swap_and_mem(swap_baseline)
            cur_s = nxt_s
            s2b_tmp = s2b_ckpt_path.with_suffix(".json.tmp")
            with open(s2b_tmp, "w", encoding="utf-8") as sf:
                json.dump(
                    {
                        "completed_layer": int(bid),
                        "active_slot": str(cur_s),
                        "win_sel": str(eval_selector),
                        "arm_names": list(arm_names),
                        "eval_seq_lengths": e_seq_lens,
                        "gsq_vs_stock_by_layer": gsq_by_l,
                    },
                    sf,
                    indent=2,
                )
            os.replace(s2b_tmp, s2b_ckpt_path)
            if bid in canon_set or bid % 8 == 0 or bid == n_layers - 1:
                print(
                    f"[Wave2][Stage2b:{eval_selector}] blk.{bid:02d}/{n_layers - 1:02d} "
                    f"dt={time.perf_counter()-t_s2b:.1f}s MemAvail={tel_2b.mem_available_gib:.2f}GiB "
                    f"disk_swap_kb={tel_2b.disk_swap_used_kb} "
                    f"zram_d_mib={max(0.0, tel_2b.zram_orig_mib - swap_baseline.zram_orig_mib):.1f} "
                    f"d_pswpout={tel_2b.pswpout - swap_baseline.pswpout}",
                    flush=True,
                )

        # Final output mixer + lm_head teacher-forced KL & top-1 evaluation
        final_map = slots_a if cur_s == "A" else slots_b
        with torch.device("meta"):
            out_mixer = Qwen4ExpTextGatedResidual(text_cfg, use_combine=False)
        materialize_submodule(out_mixer, "model.language_model.hyper_connection_mixer", st_index, device="cpu")
        lm_head_t = st_index.load_tensors(["lm_head.weight"], device="cpu")["lm_head.weight"]
        lm_head_fp16 = lm_head_t.to(torch.float16).numpy()
        del lm_head_t

        lm_head_arg: Any = (
            upload_2d_fp16_chunked_cupy(lm_head_fp16) if backend == "cupy" else lm_head_fp16
        )
        if backend == "cupy":
            del lm_head_fp16

        patch_mix = CuPyLinearPatch(out_mixer, enabled=(backend == "cupy"))
        cand_arms = tuple(a for a in arm_names if a != "DONOR")
        agg = {
            a: {"en_kl": 0.0, "en_t1": 0.0, "en_n": 0, "ru_kl": 0.0, "ru_t1": 0.0, "ru_n": 0}
            for a in cand_arms
        }
        try:
            with torch.no_grad():
                for s in eval_samples:
                    hd_raw = final_map["DONOR"].read_seq(s.idx).reshape(1, s.seq_len, -1)
                    hd_mix = out_mixer(hd_raw)[:, :-1, :].to(torch.float32).numpy().reshape(-1, hidden_size)
                    for a in cand_arms:
                        hc_raw = final_map[a].read_seq(s.idx).reshape(1, s.seq_len, -1)
                        hc_mix = out_mixer(hc_raw)[:, :-1, :].to(torch.float32).numpy().reshape(-1, hidden_size)
                        kl_s, t1_s, n_t = compute_kl_and_top1_from_hidden(
                            hd_mix, hc_mix, lm_head_arg, backend=backend
                        )
                        if s.flags.is_ru:
                            agg[a]["ru_kl"] += kl_s
                            agg[a]["ru_t1"] += t1_s
                            agg[a]["ru_n"] += n_t
                        else:
                            agg[a]["en_kl"] += kl_s
                            agg[a]["en_t1"] += t1_s
                            agg[a]["en_n"] += n_t
        finally:
            patch_mix.close()
            free_submodule_to_meta(out_mixer)
            del lm_head_arg
            free_cupy_pools()
            gc.collect()

        stats_out: Dict[str, Dict[str, float]] = {}
        for a in cand_arms:
            d = agg[a]
            stats_out[a] = {
                "kl_en": round(d["en_kl"] / max(1, d["en_n"]), 6),
                "kl_ru": round(d["ru_kl"] / max(1, d["ru_n"]), 6),
                "top1_en": round(d["en_t1"] / max(1, d["en_n"]), 6),
                "top1_ru": round(d["ru_t1"] / max(1, d["ru_n"]), 6),
                "en_eval_tokens": int(d["en_n"]),
                "ru_eval_tokens": int(d["ru_n"]),
            }
        return stats_out, gsq_by_l

    need_a2_ctrl = win_sel != "A2"
    s2b_stats, gsq_vs_stock_by_layer = _run_stage_2b_for_selector(
        eval_selector=win_sel,
        include_r320_a2_control=need_a2_ctrl,
        reset_checkpoint=False,
    )
    if need_a2_ctrl:
        r320_a2_raw = s2b_stats.pop("R320_A2")
        overfit_ctrl = check_r320_a2_overfitting_control(s2b_stats["R320"], r320_a2_raw, win_sel)
        effective_selector = str(overfit_ctrl["effective_selector"])
        if overfit_ctrl["overfit_control_triggered"]:
            print(
                f"[Wave2][Stage2b] OVERFITTING CONTROL TRIGGERED: {win_sel} R320 kl_mix="
                f"{overfit_ctrl['r320_primary']['kl_mix']} >= R320_A2 kl_mix="
                f"{overfit_ctrl['r320_a2_control']['kl_mix']} -> re-evaluating Stage 2b under A2!",
                flush=True,
            )
            s2b_stats, gsq_vs_stock_by_layer = _run_stage_2b_for_selector(
                eval_selector="A2",
                include_r320_a2_control=False,
                reset_checkpoint=True,
            )
    else:
        overfit_ctrl = check_r320_a2_overfitting_control(s2b_stats["R320"], s2b_stats["R320"], "A2")
        effective_selector = "A2"

    decision_2a["effective_winner_selector_after_2b_control"] = effective_selector
    with open(out_dir / "stage2a_selector_shootout.json", "w", encoding="utf-8") as f:
        json.dump(decision_2a, f, indent=2)

    decision_2b = decide_stage_2b_winner(s2b_stats)
    decision_2b["effective_selector"] = effective_selector
    decision_2b["R320_A2"] = overfit_ctrl["r320_a2_control"]
    decision_2b["a4_prime_beats_a2_splice"] = overfit_ctrl["a4_prime_beats_a2_splice"]
    decision_2b["overfitting_control"] = overfit_ctrl
    decision_2b["gsq_vs_stock_q2_0_by_layer"] = gsq_vs_stock_by_layer
    decision_2b["all_layers_gsq_beats_stock_q2_0"] = all(
        bool(v["gsq_beats_stock"]) for v in gsq_vs_stock_by_layer.values()
    )

    tel_end = assert_zero_swap_and_mem(swap_baseline)
    summary = {
        "elapsed_sec": round(time.perf_counter() - t_start, 2),
        "calib_sequences": len(calib_samples),
        "calib_tokens": total_calib_tokens,
        "eval_sequences": len(eval_samples),
        "eval_tokens": total_eval_tokens,
        "canonical_layers": list(canon_tuple),
        "resume_info": resume_metadata,
        "parity_checks": {"moe": moe_parity, "layer_kernels": layer_kernel_parity},
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
        "stage2a": decision_2a,
        "stage2b": decision_2b,
        "escalated": bool(decision_2b["escalate_opus"]),
    }
    for p_out in (out_dir / "wave2_decision_summary.json", summary_json_path):
        with open(p_out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="SmartLLM v2 Wave 2 Shootout")
    parser.add_argument("--calib-jsonl", type=Path, default=Path("data/calib_v2/calib_v2.jsonl"))
    parser.add_argument("--eval-jsonl", type=Path, default=Path("data/eval_E/eval_E.jsonl"))
    parser.add_argument("--out-dir", type=Path, default=RUNS_DIR / "wave2")
    parser.add_argument("--summary-json", type=Path, default=RUNS_DIR / "wave2_shootout_summary.json")
    parser.add_argument("--stage-dir", type=Path, default=STAGE_DIR / "wave2")
    parser.add_argument("--backend", choices=["cupy", "cpu"], default="cupy")
    parser.add_argument("--max-calib-samples", type=int, default=640)
    parser.add_argument("--max-eval-samples", type=int, default=128)
    args = parser.parse_args()

    res = run_wave2_pipeline(
        calib_jsonl=args.calib_jsonl,
        eval_jsonl=args.eval_jsonl,
        out_dir=args.out_dir,
        summary_json_path=args.summary_json,
        stage_dir=args.stage_dir,
        backend=args.backend,
        max_calib_samples=args.max_calib_samples,
        max_eval_samples=args.max_eval_samples,
    )
    print(json.dumps({"stage2a_winner": res["stage2a"]["global_winner_selector"], "stage2b": res["stage2b"]}, indent=2))
    # Note: return 0 on clean completion even if Opus escalation clause triggered (escalate_opus=True in JSON),
    # so gpu_run.py completes exit check cleanly and we report [WAVE 2 ESCALATE] vs [WAVE 2 DONE] per JSON.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
