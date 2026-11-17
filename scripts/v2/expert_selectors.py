#!/usr/bin/env python3
"""Expert Pruning Selectors A1, A2, A3 (Quota-HOPE), and A4' (Greedy RCO) for SmartLLM v2.

Enforces OPUS_MASTER_PLAN_V2.md §1.D2 hard domain quota locks identically across A2/A3/A4':
  1. Dead experts (expert_frequency == 0) strictly excluded first.
  2. Workhorse lock: WH = 64 stratum-balanced experts (wsum_balanced).
  3. Specialist locks: RU >= 40, Copy/Craft >= 35, Vision >= 30.
  4. Hard assertions: 100% locked experts retained, strictly ascending keep_indices, exact K.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from scipy.optimize import minimize

from scripts.v2.cupy_moe_backend import A4PrimeCache


@dataclass
class QuotaLockResult:
    num_experts: int
    dead_indices: List[int]
    wh_indices: List[int]
    ru_indices: List[int]
    craft_indices: List[int]
    vis_indices: List[int]
    locked_indices: List[int]  # Sorted union of (wh | ru | craft | vis) \ dead

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "num_experts": self.num_experts,
            "n_dead": len(self.dead_indices),
            "n_wh": len(self.wh_indices),
            "n_ru": len(self.ru_indices),
            "n_craft": len(self.craft_indices),
            "n_vis": len(self.vis_indices),
            "n_locked_union": len(self.locked_indices),
        }


def _top_non_dead(
    scores: np.ndarray,
    active_mask: np.ndarray,
    quota: int,
    tie_break: np.ndarray,
) -> List[int]:
    if quota <= 0:
        return []
    cand = np.flatnonzero(active_mask)
    if cand.size == 0:
        return []
    k = min(int(quota), int(cand.size))
    # Sort descending by primary score, then tie_break, then ascending expert id
    order = np.lexsort((cand, -tie_break[cand], -scores[cand]))
    return [int(cand[i]) for i in order[:k]]


def build_quota_locks(
    score_dict: Dict[str, Any],
    wh_quota: int = 64,
    ru_quota: int = 40,
    craft_quota: int = 35,
    vis_quota: int = 30,
) -> QuotaLockResult:
    """Build deterministic hard domain-quota lock sets from a layer score dictionary."""
    arr = score_dict["arrays"]
    freq = np.asarray(arr["expert_frequency"], dtype=np.int64)
    num_experts = int(freq.size)

    reap_raw = np.asarray(arr.get("reap_raw", np.zeros(num_experts)), dtype=np.float64)
    wsum_bal = np.asarray(arr.get("wsum_balanced", reap_raw), dtype=np.float64)

    ru_wean = np.asarray(arr.get("ru_wean", np.zeros(num_experts)), dtype=np.float64)
    ru_freq = np.asarray(arr.get("ru_freq", np.zeros(num_experts)), dtype=np.int64)

    craft_wean = np.asarray(arr.get("copy_craft_wean", np.zeros(num_experts)), dtype=np.float64)
    craft_freq = np.asarray(arr.get("copy_craft_freq", np.zeros(num_experts)), dtype=np.int64)

    vis_wean = np.asarray(arr.get("weighted_ean_visual_image_pad", np.zeros(num_experts)), dtype=np.float64)
    vis_freq = np.asarray(arr.get("freq_visual_image_pad", np.zeros(num_experts)), dtype=np.int64)

    non_dead = freq > 0
    dead_indices = [int(i) for i in np.flatnonzero(~non_dead)]

    wh_idx = _top_non_dead(wsum_bal, non_dead, wh_quota, tie_break=reap_raw)
    ru_idx = _top_non_dead(ru_wean, non_dead & (ru_freq > 0), ru_quota, tie_break=wsum_bal)
    craft_idx = _top_non_dead(craft_wean, non_dead & (craft_freq > 0), craft_quota, tie_break=wsum_bal)
    vis_idx = _top_non_dead(vis_wean, non_dead & (vis_freq > 0), vis_quota, tie_break=wsum_bal)

    locked = sorted(set(wh_idx) | set(ru_idx) | set(craft_idx) | set(vis_idx))
    assert len(set(locked) & set(dead_indices)) == 0, "Dead expert leaked into quota locks"

    return QuotaLockResult(
        num_experts=num_experts,
        dead_indices=dead_indices,
        wh_indices=wh_idx,
        ru_indices=ru_idx,
        craft_indices=craft_idx,
        vis_indices=vis_idx,
        locked_indices=locked,
    )


def verify_quota_invariants(
    keep_indices: Sequence[int] | np.ndarray,
    locks: Optional[QuotaLockResult],
    target_k: int,
    num_experts: int,
) -> np.ndarray:
    """Hard invariant check required by OPUS_MASTER_PLAN_V2.md §1.D2."""
    idx = np.asarray(keep_indices, dtype=np.int64)
    if idx.ndim != 1 or idx.size != int(target_k):
        raise AssertionError(f"Expected 1D keep_indices of length {target_k}, got shape {idx.shape}")
    if np.any(idx < 0) or np.any(idx >= num_experts):
        raise AssertionError(f"keep_indices out of bounds [0, {num_experts})")
    if idx.size > 1 and not np.all(np.diff(idx) > 0):
        raise AssertionError("keep_indices must be strictly ascending without duplicates")

    if locks is not None:
        keep_set = set(int(i) for i in idx)
        missing = set(locks.locked_indices) - keep_set
        if missing:
            raise AssertionError(f"Quota lock violation: {len(missing)} locked experts missing: {sorted(missing)[:10]}")
        n_alive = num_experts - len(locks.dead_indices)
        if n_alive >= target_k:
            leaked_dead = set(locks.dead_indices) & keep_set
            if leaked_dead:
                raise AssertionError(f"Dead expert violation: kept dead experts {sorted(leaked_dead)[:10]}")
    return idx


def _fill_if_fewer_alive_than_k(
    chosen: Set[int],
    dead_indices: Sequence[int],
    gate_l2_tiebreak: Optional[np.ndarray],
    target_k: int,
) -> List[int]:
    if len(chosen) >= target_k:
        return sorted(chosen)[:target_k]
    rem = [i for i in dead_indices if i not in chosen]
    if gate_l2_tiebreak is not None:
        rem.sort(key=lambda i: (-float(gate_l2_tiebreak[i]), i))
    else:
        rem.sort()
    need = target_k - len(chosen)
    chosen.update(rem[:need])
    return sorted(chosen)


def select_a1_open_reap(
    score_dict: Dict[str, Any],
    target_k: int,
    min_count_floor: int = 5,
    gate_l2_norms: Optional[np.ndarray] = None,
) -> np.ndarray:
    """A1: Reference REAP without domain quotas (dead experts excluded first)."""
    arr = score_dict["arrays"]
    freq = np.asarray(arr["expert_frequency"], dtype=np.int64)
    num_experts = int(freq.size)
    reap_raw = np.asarray(arr["reap_raw"], dtype=np.float64)
    reap_guarded = np.where(freq >= min_count_floor, reap_raw, 0.0)
    wsum = np.asarray(arr.get("wsum_balanced", reap_raw), dtype=np.float64)

    alive = np.flatnonzero(freq > 0)
    order = np.lexsort((alive, -reap_raw[alive], -wsum[alive], -reap_guarded[alive]))
    take = [int(alive[i]) for i in order[: min(target_k, alive.size)]]
    dead = [int(i) for i in np.flatnonzero(freq == 0)]
    res = _fill_if_fewer_alive_than_k(set(take), dead, gate_l2_norms, target_k)
    return verify_quota_invariants(res, locks=None, target_k=target_k, num_experts=num_experts)


def select_a2_quota_reap(
    score_dict: Dict[str, Any],
    target_k: int,
    locks: Optional[QuotaLockResult] = None,
    min_count_floor: int = 5,
    gate_l2_norms: Optional[np.ndarray] = None,
) -> np.ndarray:
    """A2: Hard domain quotas + outlier-guarded REAP ranking on remaining slots."""
    arr = score_dict["arrays"]
    freq = np.asarray(arr["expert_frequency"], dtype=np.int64)
    num_experts = int(freq.size)
    if locks is None:
        locks = build_quota_locks(score_dict)
    if len(locks.locked_indices) > target_k:
        raise ValueError(f"Locked union ({len(locks.locked_indices)}) exceeds target_k ({target_k})")

    reap_raw = np.asarray(arr["reap_raw"], dtype=np.float64)
    reap_guarded = np.where(freq >= min_count_floor, reap_raw, 0.0)
    wsum = np.asarray(arr.get("wsum_balanced", reap_raw), dtype=np.float64)

    chosen = set(locks.locked_indices)
    dead_set = set(locks.dead_indices)
    free = np.array([i for i in range(num_experts) if i not in chosen and i not in dead_set], dtype=np.int64)

    need = target_k - len(chosen)
    if need > 0 and free.size > 0:
        order = np.lexsort((free, -reap_raw[free], -wsum[free], -reap_guarded[free]))
        for pos in order[: min(need, free.size)]:
            chosen.add(int(free[pos]))

    res = _fill_if_fewer_alive_than_k(chosen, locks.dead_indices, gate_l2_norms, target_k)
    return verify_quota_invariants(res, locks=locks, target_k=target_k, num_experts=num_experts)


def build_normalized_coactivation_matrix(coact_raw: np.ndarray) -> np.ndarray:
    """Normalize C = R^T R to zero-diagonal cosine co-activation similarity F_tilde in [0, 1]."""
    c = np.asarray(coact_raw, dtype=np.float64)
    diag = np.maximum(np.diag(c), 0.0)
    denom = np.sqrt(np.outer(diag, diag))
    f_mat = np.where(denom > 1e-15, c / np.maximum(denom, 1e-15), 0.0)
    f_mat = 0.5 * (f_mat + f_mat.T)
    np.fill_diagonal(f_mat, 0.0)
    return np.clip(f_mat, 0.0, 1.0)


def select_a3_quota_hope(
    score_dict: Dict[str, Any],
    coact_raw: np.ndarray,
    target_k: int,
    locks: Optional[QuotaLockResult] = None,
    hope_lambda: float = 1.0,
    min_count_floor: int = 5,
    maxiter: int = 150,
    gate_l2_norms: Optional[np.ndarray] = None,
) -> np.ndarray:
    """A3: Quota-HOPE (awslabs/HOPE arXiv:2603.18916, Apache-2.0).

    Minimizes continuous quadratic objective over z in [0, 1]^E:
        J(z) = (1 / (2 * K)) * z^T F_tilde z - hope_lambda * s_norm^T z
    subject to:
        sum(z) == K,  z_i == 1 for i in locked_set,  z_i == 0 for i in dead_set.
    Substituting z_L = 1, z_D = 0 yields an exact reduced SLSQP over u = z_U in [0, 1]^|U|
    that penalizes both redundancy among free candidates (u^T F_UU u) AND redundancy with
    already-locked specialists/workhorses ((F_UL 1)^T u).
    """
    arr = score_dict["arrays"]
    freq = np.asarray(arr["expert_frequency"], dtype=np.int64)
    num_experts = int(freq.size)
    if locks is None:
        locks = build_quota_locks(score_dict)
    if len(locks.locked_indices) > target_k:
        raise ValueError(f"Locked union ({len(locks.locked_indices)}) exceeds target_k ({target_k})")

    chosen = set(locks.locked_indices)
    dead_set = set(locks.dead_indices)
    free_idx = np.array([i for i in range(num_experts) if i not in chosen and i not in dead_set], dtype=np.int64)
    k_rem = target_k - len(chosen)

    if k_rem <= 0 or free_idx.size <= k_rem:
        chosen.update(int(i) for i in free_idx[: max(0, k_rem)])
        res = _fill_if_fewer_alive_than_k(chosen, locks.dead_indices, gate_l2_norms, target_k)
        return verify_quota_invariants(res, locks=locks, target_k=target_k, num_experts=num_experts)

    reap_raw = np.asarray(arr["reap_raw"], dtype=np.float64)
    reap_guarded = np.where(freq >= min_count_floor, reap_raw, 0.0)
    s_base = np.where(reap_guarded > 0.0, reap_guarded, 0.1 * reap_raw)
    s_u = s_base[free_idx]
    s_max = float(np.max(s_base)) if np.max(s_base) > 0.0 else 1.0
    s_norm_u = s_u / s_max

    f_tilde = build_normalized_coactivation_matrix(coact_raw)
    # Scale F_tilde by mean row coupling so quadratic & linear terms have matched O(1) scale
    row_scale = float(np.mean(np.sum(f_tilde, axis=1))) / max(1.0, float(num_experts))
    inv_scale = 1.0 / max(row_scale * float(target_k), 1e-8)

    f_uu = f_tilde[np.ix_(free_idx, free_idx)] * inv_scale
    if len(locks.locked_indices) > 0:
        locked_arr = np.asarray(locks.locked_indices, dtype=np.int64)
        cross_ul = np.sum(f_tilde[np.ix_(free_idx, locked_arr)], axis=1) * inv_scale
    else:
        cross_ul = np.zeros(free_idx.size, dtype=np.float64)

    lin_vec = cross_ul - float(hope_lambda) * s_norm_u

    def obj_and_grad(u: np.ndarray) -> Tuple[float, np.ndarray]:
        fu = f_uu @ u
        val = 0.5 * float(u @ fu) + float(lin_vec @ u)
        grad = fu + lin_vec
        return val, grad

    u0 = np.full(free_idx.size, float(k_rem) / float(free_idx.size), dtype=np.float64)
    ones = np.ones(free_idx.size, dtype=np.float64)
    opt = minimize(
        fun=lambda u: obj_and_grad(u)[0],
        x0=u0,
        jac=lambda u: obj_and_grad(u)[1],
        method="SLSQP",
        bounds=[(0.0, 1.0)] * int(free_idx.size),
        constraints=[{"type": "eq", "fun": lambda u: float(np.sum(u) - k_rem), "jac": lambda _u: ones}],
        options={"maxiter": int(maxiter), "ftol": 1e-7, "disp": False},
    )
    u_sol = np.clip(opt.x, 0.0, 1.0)
    order = np.lexsort((free_idx, -s_norm_u, -u_sol))
    for pos in order[:k_rem]:
        chosen.add(int(free_idx[pos]))

    res = _fill_if_fewer_alive_than_k(chosen, locks.dead_indices, gate_l2_norms, target_k)
    return verify_quota_invariants(res, locks=locks, target_k=target_k, num_experts=num_experts)


def select_a4_prime_greedy_rco(
    rco_cache: A4PrimeCache,
    score_dict: Dict[str, Any],
    target_k: int,
    locks: Optional[QuotaLockResult] = None,
    gate_l2_norms: Optional[np.ndarray] = None,
) -> np.ndarray:
    """A4': Gradient-free greedy backward elimination (E -> K) minimizing exact
    ||Y_donor - Y_pruned||_2^2 with exact top-k renormalization on cached top-M Gram data.

    Mathematical exactness:
    On each token t, let idx[t, 0..M-1] be the sorted top-M donor experts. For any kept set S,
    the active kept experts A_t(S) are the first top_k kept entries of idx[t], and removing
    ANY one of those top_k kept experts promotes the exact same (top_k + 1)-th kept expert b_t!
    Using precomputed Gram[t, i, j] = <E_{t,i}, E_{t,j}> and target_dot[t, i] = <E_{t,i}, D_t>,
    we evaluate the exact delta MSE of dropping every candidate expert simultaneously in O(T * top_k).
    """
    arr = score_dict["arrays"]
    freq = np.asarray(arr["expert_frequency"], dtype=np.int64)
    num_experts = int(freq.size)
    if locks is None:
        locks = build_quota_locks(score_dict)
    if len(locks.locked_indices) > target_k:
        raise ValueError(f"Locked union ({len(locks.locked_indices)}) exceeds target_k ({target_k})")

    t_n = int(rco_cache.filled)
    if t_n == 0:
        return select_a2_quota_reap(score_dict, target_k, locks=locks, gate_l2_norms=gate_l2_norms)

    top_k = int(rco_cache.top_k)
    top_m = int(rco_cache.top_m)
    idx_m = rco_cache.idx[:t_n].astype(np.int64)  # [T, M]
    probs_m = rco_cache.probs[:t_n].astype(np.float64)  # [T, M]
    gram_m = rco_cache.gram[:t_n].astype(np.float64)  # [T, M, M]
    tdot_m = rco_cache.target_dot[:t_n].astype(np.float64)  # [T, M]
    tnorm2 = rco_cache.target_norm2[:t_n].astype(np.float64)  # [T]

    reap_raw = np.asarray(arr["reap_raw"], dtype=np.float64)

    kept_mask = np.ones(num_experts, dtype=bool)
    for d_id in locks.dead_indices:
        kept_mask[d_id] = False
    if int(kept_mask.sum()) <= target_k:
        chosen = set(int(i) for i in np.flatnonzero(kept_mask)) | set(locks.locked_indices)
        res = _fill_if_fewer_alive_than_k(chosen, locks.dead_indices, gate_l2_norms, target_k)
        return verify_quota_invariants(res, locks=locks, target_k=target_k, num_experts=num_experts)

    locked_mask = np.zeros(num_experts, dtype=bool)
    for l_id in locks.locked_indices:
        locked_mask[l_id] = True

    tok_arange = np.arange(t_n, dtype=np.int64)

    while int(kept_mask.sum()) > target_k:
        in_s = kept_mask[idx_m]  # [T, M] bool
        csum = np.cumsum(in_s, axis=1)
        n_avail = csum[:, -1]  # [T]

        # Active mask: kept and rank <= top_k
        active_mask = in_s & (csum <= top_k)  # [T, M]
        # Backup mask: kept and rank == top_k + 1 (at most one True per row)
        backup_mask = in_s & (csum == (top_k + 1))  # [T, M]

        w_act = np.where(active_mask, probs_m, 0.0)  # [T, M]
        s_sum = np.sum(w_act, axis=1)  # [T]

        # Current MSE per token: || U_t / s_sum - D_t ||^2
        # where U_t = sum_j w_act[t, j] E_{t, j}
        gu = np.einsum("tm,tmn->tn", w_act, gram_m, optimize=True)  # [T, M] = <U_t, E_{t, n}>
        u_norm2 = np.sum(w_act * gu, axis=1)  # [T] = ||U_t||^2
        u_dot_d = np.sum(w_act * tdot_m, axis=1)  # [T] = <U_t, D_t>

        inv_s = np.where(s_sum > 1e-20, 1.0 / np.maximum(s_sum, 1e-20), 0.0)
        cur_err = np.where(
            s_sum > 1e-20,
            (inv_s * inv_s) * u_norm2 - 2.0 * inv_s * u_dot_d + tnorm2,
            tnorm2,
        )

        # Backup expert terms (if n_avail >= top_k + 1)
        has_b = n_avail > top_k
        b_pos = np.argmax(backup_mask, axis=1)  # [T]
        p_b = np.where(has_b, probs_m[tok_arange, b_pos], 0.0)  # [T]
        u_dot_eb = np.where(has_b, gu[tok_arange, b_pos], 0.0)  # [T]
        eb_norm2 = np.where(has_b, gram_m[tok_arange, b_pos, b_pos], 0.0)  # [T]
        eb_dot_d = np.where(has_b, tdot_m[tok_arange, b_pos], 0.0)  # [T]

        # W_t = U_t + p_b * E_{t, b}
        w_norm2 = u_norm2 + 2.0 * p_b * u_dot_eb + (p_b * p_b) * eb_norm2  # [T]
        w_dot_d = u_dot_d + p_b * eb_dot_d  # [T]
        # <W_t, E_{t, m}> = <U_t, E_{t, m}> + p_b * <E_{t, b}, E_{t, m}>
        gb_row = gram_m[tok_arange, b_pos, :]  # [T, M]
        w_dot_em = gu + p_b[:, None] * gb_row  # [T, M]
        em_norm2 = np.diagonal(gram_m, axis1=1, axis2=2)  # [T, M]

        # When active slot m is dropped: U'_{t,m} = W_t - p_{t,m} E_{t,m}, S'_{t,m} = s_sum + p_b - p_{t,m}
        s_new = s_sum[:, None] + p_b[:, None] - probs_m  # [T, M]
        u_new_norm2 = w_norm2[:, None] - 2.0 * probs_m * w_dot_em + (probs_m * probs_m) * em_norm2
        u_new_dot_d = w_dot_d[:, None] - probs_m * tdot_m

        inv_s_new = np.where(s_new > 1e-20, 1.0 / np.maximum(s_new, 1e-20), 0.0)
        new_err = np.where(
            s_new > 1e-20,
            (inv_s_new * inv_s_new) * u_new_norm2 - 2.0 * inv_s_new * u_new_dot_d + tnorm2[:, None],
            tnorm2[:, None],
        )
        delta_err = np.where(active_mask, new_err - cur_err[:, None], 0.0)  # [T, M]

        delta_by_expert = np.zeros(num_experts, dtype=np.float64)
        np.add.at(delta_by_expert, idx_m[active_mask], delta_err[active_mask])

        # Mask out already-dropped and quota-locked experts
        eligible = kept_mask & (~locked_mask)
        cand_ids = np.flatnonzero(eligible)
        # Drop expert with smallest increase in ||Y_donor - Y_pruned||^2 (tie-break: lowest REAP)
        best_pos = int(np.lexsort((-cand_ids, reap_raw[cand_ids], delta_by_expert[cand_ids]))[0])
        drop_expert = int(cand_ids[best_pos])
        kept_mask[drop_expert] = False

    keep_indices = np.flatnonzero(kept_mask).astype(np.int64)
    return verify_quota_invariants(keep_indices, locks=locks, target_k=target_k, num_experts=num_experts)
