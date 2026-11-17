#!/usr/bin/env python3
"""Post-Pruning Layer-by-Layer Healing C3 = C1 + C2 (OPUS_MASTER_PLAN_V2.md §1.D3).

Components:
1. C1 — Router Gate Recalibration (W_gate [K, 2560] F32):
   Analytic softmax Jacobian + Adam (<= 200 steps on <= 64k subsampled tokens, L2 anchor
   mu * ||W - W_0||_F^2) minimizing ||Y_donor(H_donor) - Y_pruned(H_pruned)||_2^2 through
   normalized top-10 weights (top-k set fixed per token during Adam via exact 10x10 Gram
   contraction). Accepted ONLY if live unfixed top-10 MoE L2 error on the 20% held-out
   validation slice drops by >= 2% relative; otherwise keeps original sliced W_0.
2. C2a — Per-Expert Coupled LS Scalar alpha_k in [0.7, 1.4]:
   Bounded K x K Gram quadratic least-squares accounting for top-10 co-activation cross-terms,
   validated on the 20% held-out slice and folded into experts.down_proj[k].
3. C2b — Shared-Expert down_proj Ridge Compensation (640 x 640 FP64 Cholesky):
   Folds systematic residual (Y_donor - Y_pruned) into shared_expert.down_proj via gated
   intermediate features Z_tilde = sigmoid(shared_expert_gate(h)) * Z_sh(h), sweeping ridge
   lambda on the 20% held-out validation slice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

from scripts.v2.cupy_moe_backend import (
    MoELayerWeights,
    _forward_moe_cpu,
    _silu_np_f32,
    _sigmoid_np_f32,
    forward_moe_v2,
    route_topk_exact_np,
)


@dataclass
class C3HealResult:
    w_gate_f32: np.ndarray  # [K, D] float32
    alpha_scales: np.ndarray  # [K] float32 in [0.7, 1.4]
    w_down_shexp_f32: np.ndarray  # [D, I] float32
    c1_accepted: bool
    c2_alpha_accepted: bool
    c2_shexp_accepted: bool
    val_rel_l2_before: float
    val_rel_l2_after_c1: float
    val_rel_l2_after_c2_alpha: float
    val_rel_l2_after_c3: float
    metrics: Dict[str, Any]


def _compute_active_gram_and_rhs(
    moe_w: MoELayerWeights,
    x_f32: np.ndarray,
    target_f32: np.ndarray,
    topk_idx: np.ndarray,
    scale_w: Optional[np.ndarray] = None,
    out_dtype: Any = np.float32,
    chunk_tokens: int = 2048,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute exact per-token [T, top_k, top_k] Gram matrix and [T, top_k] target inner products
    in 2048-token (<=200 MiB) slices without ever materializing a 5 GiB [T, top_k, D] tensor!"""
    t_n, k_top = topk_idx.shape
    d_hid = moe_w.hidden_dim
    inter = moe_w.inter_dim
    out_dt = np.dtype(out_dtype)

    gram_all = np.empty((t_n, k_top, k_top), dtype=out_dt)
    rhs_all = np.empty((t_n, k_top), dtype=out_dt)
    step = max(1, int(chunk_tokens))

    if moe_w.backend == "cupy":
        from scripts.v2.cupy_moe_backend import _get_cupy, free_cupy_pinned_pool

        cp = _get_cupy()
        for t0 in range(0, t_n, step):
            t1 = min(t_n, t0 + step)
            cur_t = t1 - t0
            idx_sub = topk_idx[t0:t1]
            xg_fp16 = cp.asarray(np.ascontiguousarray(x_f32[t0:t1], dtype=np.float16))
            tgt_g = cp.asarray(np.ascontiguousarray(target_f32[t0:t1], dtype=np.float32))
            e_outs_g = cp.zeros((cur_t, k_top, d_hid), dtype=cp.float32)

            flat_e = idx_sub.ravel()
            perm = np.argsort(flat_e, kind="mergesort")
            e_sorted = flat_e[perm]
            tok_sorted = (perm // k_top).astype(np.int32)
            slot_sorted = (perm % k_top).astype(np.int32)
            uniq_e, starts, counts = np.unique(e_sorted, return_index=True, return_counts=True)
            tg_all = cp.asarray(tok_sorted)
            sg_all = cp.asarray(slot_sorted)
            xg_sorted = xg_fp16[tg_all]

            for u_i in range(int(uniq_e.size)):
                e_id = int(uniq_e[u_i])
                s0 = int(starts[u_i])
                s1 = s0 + int(counts[u_i])
                gu = cp.matmul(xg_sorted[s0:s1], moe_w.gate_up[e_id].T, dtype=cp.float32)
                gp, up = gu[:, :inter], gu[:, inter:]
                act = (gp / (1.0 + cp.exp(-gp))) * up
                dn = cp.matmul(act.astype(cp.float16), moe_w.down[e_id].T, dtype=cp.float32)
                e_outs_g[tg_all[s0:s1], sg_all[s0:s1]] = dn

            if scale_w is not None:
                sw_g = cp.asarray(np.ascontiguousarray(scale_w[t0:t1], dtype=np.float32))[:, :, None]
                e_outs_g = e_outs_g * sw_g
                del sw_g

            if out_dt == np.float64:
                eo64 = e_outs_g.astype(cp.float64)
                gram_g = cp.matmul(eo64, eo64.transpose(0, 2, 1))
                rhs_g = cp.sum(eo64 * tgt_g.astype(cp.float64)[:, None, :], axis=-1)
                del eo64
            else:
                gram_g = cp.matmul(e_outs_g, e_outs_g.transpose(0, 2, 1))
                rhs_g = cp.sum(e_outs_g * tgt_g[:, None, :], axis=-1)

            gram_all[t0:t1] = gram_g.get().astype(out_dt, copy=False)
            rhs_all[t0:t1] = rhs_g.get().astype(out_dt, copy=False)
            del xg_fp16, tgt_g, e_outs_g, tg_all, sg_all, xg_sorted, gram_g, rhs_g
            free_cupy_pinned_pool()
    else:
        for t0 in range(0, t_n, step):
            t1 = min(t_n, t0 + step)
            cur_t = t1 - t0
            idx_sub = topk_idx[t0:t1]
            x_fp16_f32 = x_f32[t0:t1].astype(np.float16).astype(np.float32)
            e_outs = np.zeros((cur_t, k_top, d_hid), dtype=np.float32)
            for e_id in np.unique(idx_sub):
                t_pos, s_pos = np.where(idx_sub == e_id)
                if t_pos.size == 0:
                    continue
                gu = x_fp16_f32[t_pos] @ moe_w.gate_up[int(e_id)].astype(np.float32).T
                act = _silu_np_f32(gu[:, :inter]) * gu[:, inter:]
                dn = act.astype(np.float16).astype(np.float32) @ moe_w.down[int(e_id)].astype(np.float32).T
                e_outs[t_pos, s_pos] = dn
            if scale_w is not None:
                e_outs = e_outs * scale_w[t0:t1, :, None].astype(np.float32)
            gram_all[t0:t1] = np.einsum("tkd,tnd->tkn", e_outs, e_outs, optimize=True).astype(out_dt)
            rhs_all[t0:t1] = np.einsum("tkd,td->tk", e_outs, target_f32[t0:t1], optimize=True).astype(out_dt)
            del e_outs

    return gram_all, rhs_all


def _eval_live_moe_np(
    moe_base: MoELayerWeights,
    x_f32: np.ndarray,
    w_gate_f32: np.ndarray,
    alpha_scales: Optional[np.ndarray] = None,
    w_down_shexp_f32: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Run live unfixed top-k routing MoE forward with candidate healed parameters.
    Reuses moe_base.gate_up in VRAM via shallow_view (0 B 3D host<->GPU transfers!)."""
    dn_override = None
    if alpha_scales is not None:
        if moe_base.backend == "cupy":
            from scripts.v2.cupy_moe_backend import _get_cupy, free_cupy_pinned_pool

            cp = _get_cupy()
            alpha_g = cp.asarray(np.ascontiguousarray(alpha_scales, dtype=np.float32)).reshape(-1, 1, 1)
            free_cupy_pinned_pool()
            dn_override = cp.empty_like(moe_base.down)
            k_exp = int(moe_base.num_experts)
            for i0 in range(0, k_exp, 16):
                i1 = min(k_exp, i0 + 16)
                dn_override[i0:i1] = (moe_base.down[i0:i1].astype(cp.float32) * alpha_g[i0:i1]).astype(cp.float16)
            del alpha_g
        else:
            dn_override = np.empty_like(moe_base.down)
            k_exp = int(moe_base.num_experts)
            al_np = np.asarray(alpha_scales, dtype=np.float32).reshape(-1, 1, 1)
            for i0 in range(0, k_exp, 16):
                i1 = min(k_exp, i0 + 16)
                dn_override[i0:i1] = (moe_base.down[i0:i1].astype(np.float32) * al_np[i0:i1]).astype(np.float16)

    sh_d_use = w_down_shexp_f32.astype(np.float16) if w_down_shexp_f32 is not None else None
    tmp_moe = moe_base.shallow_view(
        gate_weight_f32=w_gate_f32,
        sh_down_fp16=sh_d_use,
        down_override=dn_override,
    )
    try:
        out_t, routed_f32, sh_inter_f32, sh_sig_f32 = forward_moe_v2(
            tmp_moe, x_f32, return_components=True
        )
        return out_t.numpy(), routed_f32, sh_inter_f32, sh_sig_f32
    finally:
        tmp_moe.close()
        del dn_override


def fit_c1_router_gate(
    moe_pruned: MoELayerWeights,
    h_train: np.ndarray,  # [T_tr, D] float32
    y_donor_train: np.ndarray,  # [T_tr, D] float32
    h_val: np.ndarray,  # [T_val, D] float32
    y_donor_val: np.ndarray,  # [T_val, D] float32
    max_steps: int = 200,
    lr: float = 3e-3,
    l2_pull: float = 1e-3,
    min_rel_val_drop: float = 0.02,
) -> Tuple[np.ndarray, bool, Dict[str, float]]:
    """C1: Analytic softmax gradient + Adam on W_gate [K, D] F32 with >=2% val drop gate."""
    if moe_pruned.backend == "cupy":
        from scripts.v2.cupy_moe_backend import _get_cupy

        cp = _get_cupy()
        w0 = cp.asnumpy(moe_pruned.gate_w).astype(np.float32).copy()
    else:
        w0 = moe_pruned.gate_w.astype(np.float32).copy()

    k_exp, d_hid = w0.shape
    t_tr = h_train.shape[0]
    top_k = moe_pruned.top_k

    # Baseline live validation error under W_0
    y_val_0, _, _, _ = _eval_live_moe_np(moe_pruned, h_val, w0)
    donor_val_norm = max(float(np.linalg.norm(y_donor_val)), 1e-12)
    val_l2_0 = float(np.linalg.norm(y_donor_val - y_val_0))
    val_rel_0 = val_l2_0 / donor_val_norm

    if t_tr == 0 or max_steps <= 0:
        return w0, False, {"val_rel_before": val_rel_0, "val_rel_after": val_rel_0, "rel_drop": 0.0}

    # Precompute fixed top-k set S_t and shared-expert output on train split
    y_tr_0, routed_tr_0, _, _ = _eval_live_moe_np(moe_pruned, h_train, w0)
    y_sh_tr = y_tr_0 - routed_tr_0
    delta_tr = y_donor_train - y_sh_tr  # Target routed output [T_tr, D]

    logits_0 = h_train @ w0.T
    _, topk_idx_tr, _ = route_topk_exact_np(logits_0, top_k=top_k, norm_topk_prob=True)

    # Precompute exact 10x10 Gram matrix G_t and target inner products b_t (28 MB for 64k tokens!)
    gram_tr, b_tr = _compute_active_gram_and_rhs(
        moe_pruned, h_train, delta_tr, topk_idx_tr, scale_w=None, out_dtype=np.float32, chunk_tokens=2048
    )

    # Adam state in float32
    w = w0.copy()
    m_state = np.zeros_like(w, dtype=np.float32)
    v_state = np.zeros_like(w, dtype=np.float32)
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    inv_td = 1.0 / max(float(t_tr) * float(d_hid), 1.0)
    flat_idx = topk_idx_tr.reshape(-1)

    for step in range(1, int(max_steps) + 1):
        # Gather active logits z_{t, m} = h_t . w_{S_{t, m}}
        # Fast computation via dense GEMM (T_tr x D @ D x K -> gather top_k)
        logits_all = h_train @ w.T
        z = np.take_along_axis(logits_all, topk_idx_tr, axis=1)  # [T_tr, top_k]
        z_shift = z - np.max(z, axis=1, keepdims=True)
        exp_z = np.exp(z_shift, dtype=np.float32)
        p = exp_z / np.maximum(np.sum(exp_z, axis=1, keepdims=True), 1e-20)  # [T_tr, top_k]

        # Analytic gradient w.r.t. p: g = (G_t @ p - b_t) / (T_tr * D)
        gp = np.einsum("tkn,tn->tk", gram_tr, p, optimize=True)
        g_p = (gp - b_tr) * inv_td  # [T_tr, top_k]

        # Exact softmax Jacobian-vector product: dL/dz = p * (g_p - sum_n p_n g_n)
        pg_sum = np.sum(p * g_p, axis=1, keepdims=True)
        grad_z = p * (g_p - pg_sum)  # [T_tr, top_k]

        # Scatter-accumulate dL/dW_k = sum_{t, m: S_{t,m}==k} grad_z[t,m] * h_train[t]
        grad_w = np.zeros((k_exp, d_hid), dtype=np.float32)
        # Group via sparse [K, T_tr] indicator matrix multiplication for fast BLAS GEMM
        s_mat = np.zeros((k_exp, t_tr), dtype=np.float32)
        np.add.at(s_mat, (flat_idx, np.repeat(np.arange(t_tr), top_k)), grad_z.reshape(-1))
        grad_w = s_mat @ h_train + float(l2_pull) * (w - w0)

        # Cosine LR schedule
        cos_factor = 0.5 * (1.0 + np.cos(np.pi * float(step - 1) / float(max_steps)))
        cur_lr = float(lr) * max(0.1, cos_factor)

        m_state = beta1 * m_state + (1.0 - beta1) * grad_w
        v_state = beta2 * v_state + (1.0 - beta2) * (grad_w * grad_w)
        m_hat = m_state / (1.0 - beta1**step)
        v_hat = v_state / (1.0 - beta2**step)
        w -= cur_lr * m_hat / (np.sqrt(v_hat) + eps)

    # Evaluate LIVE unfixed top-10 routing on the 20% held-out validation slice
    y_val_new, _, _, _ = _eval_live_moe_np(moe_pruned, h_val, w)
    val_l2_new = float(np.linalg.norm(y_donor_val - y_val_new))
    val_rel_new = val_l2_new / donor_val_norm
    rel_drop = (val_l2_0 - val_l2_new) / max(val_l2_0, 1e-12)

    accepted = bool(rel_drop >= float(min_rel_val_drop))
    w_final = w if accepted else w0
    return w_final, accepted, {
        "val_rel_before": val_rel_0,
        "val_rel_candidate": val_rel_new,
        "val_rel_after": val_rel_new if accepted else val_rel_0,
        "rel_drop": rel_drop,
    }


def fit_c2_alpha_and_shexp_ridge(
    moe_pruned: MoELayerWeights,
    w_gate_f32: np.ndarray,
    h_train: np.ndarray,
    y_donor_train: np.ndarray,
    h_val: np.ndarray,
    y_donor_val: np.ndarray,
    alpha_bounds: Tuple[float, float] = (0.7, 1.4),
    alpha_ridge_rel: float = 1e-2,
    shexp_ridge_grid: Sequence[float] = (1e-3, 1e-2, 1e-1, 1.0),
) -> Tuple[np.ndarray, bool, np.ndarray, bool, Dict[str, Any]]:
    """C2: Coupled per-expert LS scalar alpha_k in [0.7, 1.4] + 640x640 FP64 Cholesky ridge
    on shared_expert.down_proj (accounting for sigmoid(shared_expert_gate(h)))."""
    k_exp = w_gate_f32.shape[0]
    top_k = moe_pruned.top_k

    if moe_pruned.backend == "cupy":
        from scripts.v2.cupy_moe_backend import _get_cupy

        cp = _get_cupy()
        sh_down_0 = cp.asnumpy(moe_pruned.sh_down).astype(np.float32).copy()
    else:
        sh_down_0 = moe_pruned.sh_down.astype(np.float32).copy()

    donor_val_norm = max(float(np.linalg.norm(y_donor_val)), 1e-12)
    y_val_base, routed_val_base, sh_inter_val, sh_sig_val = _eval_live_moe_np(
        moe_pruned, h_val, w_gate_f32
    )
    val_l2_base = float(np.linalg.norm(y_donor_val - y_val_base))

    # --- Part C2a: Coupled K x K bounded least squares for alpha in [0.7, 1.4]^K ---
    alpha_ones = np.ones(k_exp, dtype=np.float32)
    alpha_accepted = False
    alpha_final = alpha_ones.copy()
    val_l2_after_alpha = val_l2_base

    if h_train.shape[0] > 0:
        y_tr_base, routed_tr_base, sh_inter_tr, sh_sig_tr = _eval_live_moe_np(
            moe_pruned, h_train, w_gate_f32
        )
        y_sh_tr = y_tr_base - routed_tr_base
        target_routed_tr = y_donor_train - y_sh_tr

        logits_tr = h_train @ w_gate_f32.T
        topk_w_tr, topk_idx_tr, _ = route_topk_exact_np(
            logits_tr, top_k=top_k, norm_topk_prob=moe_pruned.norm_topk_prob
        )
        vv_gram, vy_dot = _compute_active_gram_and_rhs(
            moe_pruned,
            h_train,
            target_routed_tr,
            topk_idx_tr,
            scale_w=topk_w_tr,
            out_dtype=np.float64,
            chunk_tokens=2048,
        )

        m_mat = np.zeros((k_exp, k_exp), dtype=np.float64)
        rhs_vec = np.zeros(k_exp, dtype=np.float64)

        # Accumulate exact K x K coupled Gram matrix
        for s1 in range(top_k):
            i1 = topk_idx_tr[:, s1]
            np.add.at(rhs_vec, i1, vy_dot[:, s1])
            for s2 in range(top_k):
                i2 = topk_idx_tr[:, s2]
                np.add.at(m_mat, (i1, i2), vv_gram[:, s1, s2])

        m_mat = 0.5 * (m_mat + m_mat.T)
        gamma = max(float(alpha_ridge_rel) * (float(np.trace(m_mat)) / max(1, k_exp)), 1e-8)
        m_reg = m_mat + gamma * np.eye(k_exp, dtype=np.float64)
        rhs_reg = rhs_vec + gamma * np.ones(k_exp, dtype=np.float64)

        lo_b, hi_b = float(alpha_bounds[0]), float(alpha_bounds[1])
        opt_a = minimize(
            fun=lambda a: 0.5 * float(a @ (m_reg @ a)) - float(rhs_reg @ a),
            x0=np.ones(k_exp, dtype=np.float64),
            jac=lambda a: m_reg @ a - rhs_reg,
            method="L-BFGS-B",
            bounds=[(lo_b, hi_b)] * k_exp,
            options={"maxiter": 200, "ftol": 1e-10},
        )
        alpha_cand = np.clip(opt_a.x, lo_b, hi_b).astype(np.float32)

        y_val_alpha, _, _, _ = _eval_live_moe_np(
            moe_pruned, h_val, w_gate_f32, alpha_scales=alpha_cand
        )
        val_l2_cand = float(np.linalg.norm(y_donor_val - y_val_alpha))
        if val_l2_cand < val_l2_base * 0.9999:
            alpha_final = alpha_cand
            alpha_accepted = True
            val_l2_after_alpha = val_l2_cand
            y_val_cur = y_val_alpha
        else:
            y_val_cur = y_val_base
    else:
        y_val_cur = y_val_base
        sh_inter_tr = np.empty((0, moe_pruned.inter_dim), dtype=np.float32)
        sh_sig_tr = np.empty((0, 1), dtype=np.float32)

    # --- Part C2b: 640 x 640 FP64 Cholesky Ridge on shared_expert.down_proj ---
    shexp_accepted = False
    sh_down_final = sh_down_0.copy()
    val_l2_final = val_l2_after_alpha
    best_lambda_rel = 0.0

    if h_train.shape[0] > 0:
        if alpha_accepted:
            y_tr_cur, _, sh_inter_tr, sh_sig_tr = _eval_live_moe_np(
                moe_pruned, h_train, w_gate_f32, alpha_scales=alpha_final
            )
        else:
            y_tr_cur = y_tr_base  # type: ignore[possibly-unbound]

        res_tr = (y_donor_train - y_tr_cur).astype(np.float64)  # [T_tr, D]
        z_tilde_tr = (sh_inter_tr * sh_sig_tr).astype(np.float64)  # [T_tr, 640]

        res_val = (y_donor_val - y_val_cur).astype(np.float64)  # [T_val, D]
        z_tilde_val = (sh_inter_val * sh_sig_val).astype(np.float64)  # [T_val, 640]

        g_sh = z_tilde_tr.T @ z_tilde_tr  # [640, 640] FP64
        g_sh = 0.5 * (g_sh + g_sh.T)
        b_sh = z_tilde_tr.T @ res_tr  # [640, 2560] FP64
        tr_mean = float(np.trace(g_sh)) / max(1, g_sh.shape[0])

        best_val_l2 = val_l2_after_alpha
        for lam_rel in shexp_ridge_grid:
            lam = max(float(lam_rel) * tr_mean, 1e-8)
            g_reg = g_sh + lam * np.eye(g_sh.shape[0], dtype=np.float64)
            c_fac = cho_factor(g_reg, lower=True, check_finite=False)
            delta_w_t = cho_solve(c_fac, b_sh, check_finite=False)  # [640, 2560] FP64
            cand_sh_down = (sh_down_0.astype(np.float64) + delta_w_t.T).astype(np.float32)

            # Exact validation check through FP16 weight cast
            pred_corr_val = z_tilde_val @ (cand_sh_down.astype(np.float16).astype(np.float64) - sh_down_0.astype(np.float64)).T
            cand_val_l2 = float(np.linalg.norm(res_val - pred_corr_val))
            if cand_val_l2 < best_val_l2 * 0.9995:
                best_val_l2 = cand_val_l2
                sh_down_final = cand_sh_down
                shexp_accepted = True
                best_lambda_rel = float(lam_rel)

        if shexp_accepted:
            y_val_chk, _, _, _ = _eval_live_moe_np(
                moe_pruned,
                h_val,
                w_gate_f32,
                alpha_scales=alpha_final if alpha_accepted else None,
                w_down_shexp_f32=sh_down_final,
            )
            val_l2_final = float(np.linalg.norm(y_donor_val - y_val_chk))
            if val_l2_final >= val_l2_after_alpha:
                sh_down_final = sh_down_0.copy()
                shexp_accepted = False
                val_l2_final = val_l2_after_alpha

    return (
        alpha_final,
        alpha_accepted,
        sh_down_final,
        shexp_accepted,
        {
            "val_rel_before_c2": val_l2_base / donor_val_norm,
            "val_rel_after_alpha": val_l2_after_alpha / donor_val_norm,
            "val_rel_after_c2": val_l2_final / donor_val_norm,
            "alpha_min": float(alpha_final.min()),
            "alpha_max": float(alpha_final.max()),
            "alpha_mean": float(alpha_final.mean()),
            "shexp_best_lambda_rel": best_lambda_rel,
        },
    )


def heal_layer_c3(
    moe_pruned_init: MoELayerWeights,
    h_pruned_all: np.ndarray,  # [T_all, D] float32
    y_donor_all: np.ndarray,  # [T_all, D] float32 (Y_donor(H_donor))
    max_heal_tokens: int = 65536,
    val_fraction: float = 0.20,
    c1_max_steps: int = 200,
    c1_lr: float = 3e-3,
    c1_l2_pull: float = 1e-3,
    c1_min_rel_val_drop: float = 0.02,
    seed: int = 42,
) -> C3HealResult:
    """Run complete C3 = C1 + C2 healing on a single MoE layer with held-out validation."""
    n_total = h_pruned_all.shape[0]
    if n_total > max_heal_tokens:
        stride_idx = np.linspace(0, n_total - 1, num=max_heal_tokens, dtype=np.int64)
        h_sub = np.ascontiguousarray(h_pruned_all[stride_idx], dtype=np.float32)
        y_sub = np.ascontiguousarray(y_donor_all[stride_idx], dtype=np.float32)
    else:
        h_sub = np.ascontiguousarray(h_pruned_all, dtype=np.float32)
        y_sub = np.ascontiguousarray(y_donor_all, dtype=np.float32)

    # Deterministic interleaved train/val split (every 5th chunk in validation to preserve stratum balance)
    rng = np.random.default_rng(seed)
    n_sub = h_sub.shape[0]
    perm = rng.permutation(n_sub)
    n_val = max(1, int(round(n_sub * float(val_fraction))))
    if n_val >= n_sub:
        n_val = max(1, n_sub // 5)
    val_idx = np.sort(perm[:n_val])
    tr_idx = np.sort(perm[n_val:])

    h_tr, y_tr = h_sub[tr_idx], y_sub[tr_idx]
    h_val, y_val = h_sub[val_idx], y_sub[val_idx]

    w_gate_healed, c1_ok, c1_meta = fit_c1_router_gate(
        moe_pruned=moe_pruned_init,
        h_train=h_tr,
        y_donor_train=y_tr,
        h_val=h_val,
        y_donor_val=y_val,
        max_steps=c1_max_steps,
        lr=c1_lr,
        l2_pull=c1_l2_pull,
        min_rel_val_drop=c1_min_rel_val_drop,
    )

    alpha_scales, c2a_ok, sh_down_healed, c2b_ok, c2_meta = fit_c2_alpha_and_shexp_ridge(
        moe_pruned=moe_pruned_init,
        w_gate_f32=w_gate_healed,
        h_train=h_tr,
        y_donor_train=y_tr,
        h_val=h_val,
        y_donor_val=y_val,
    )

    return C3HealResult(
        w_gate_f32=w_gate_healed,
        alpha_scales=alpha_scales,
        w_down_shexp_f32=sh_down_healed,
        c1_accepted=c1_ok,
        c2_alpha_accepted=c2a_ok,
        c2_shexp_accepted=c2b_ok,
        val_rel_l2_before=float(c1_meta["val_rel_before"]),
        val_rel_l2_after_c1=float(c1_meta["val_rel_after"]),
        val_rel_l2_after_c2_alpha=float(c2_meta["val_rel_after_alpha"]),
        val_rel_l2_after_c3=float(c2_meta["val_rel_after_c2"]),
        metrics={"c1": c1_meta, "c2": c2_meta, "n_train": int(tr_idx.size), "n_val": int(val_idx.size)},
    )
