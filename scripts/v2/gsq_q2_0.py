#!/usr/bin/env python3
"""100% Clean-Room GSQ + Cholesky-GPTQ Q2_0 Quantizer & libggml-base.so Simulator (OPUS §1.D2c).

Provenance & Licensing:
- block_q2_0 binary layout & dequantization math: ggml-org/llama.cpp
  (ggml/src/ggml-common.h:187-192, ggml/src/ggml-quants.c:439-457) and gguf-py (MIT).
- Per-expert Hessian H_e = sum x x^T + damped Cholesky GPTQ error feedback:
  Frantar et al. (GPTQ) & MoESQ (Apache-2.0).
- ZERO code derived from or referencing unlicensed gptq-gguf-toolkit.

Key Q2_0 Mathematical Feature (Dual-Sign FP16 Scale Search):
  Each 64-weight block has 1 FP16 scale `d` (2 B) and 64 2-bit codes `q in {0, 1, 2, 3}` (16 B),
  reconstructing `w_hat = (q - 1) * FP32(d) in {-d, 0, +d, +2d}`.
  Because IEEE-754 FP16 `d` is signed:
    - d > 0 yields asymmetric grid {-|d|, 0, +|d|, +2|d|} (captures positive heavy tail)
    - d < 0 yields asymmetric grid {+|d|, 0, -|d|, -2|d|} (captures negative heavy tail)
  Searching BOTH positive and negative `FP16(d)` per 64-weight group + closed-form Hessian-optimal
  scale refinement + Cholesky-GPTQ column error feedback strictly beats single-sign stock Q2_0.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import ctypes
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
from scipy.linalg import cho_factor, cho_solve, cholesky

from scripts.v2.common_io import GGUF_PY_PATH, LLAMA_CPU_GGML_SO

if str(GGUF_PY_PATH) not in sys.path:
    sys.path.insert(0, str(GGUF_PY_PATH))

import gguf  # noqa: E402

QK2_0 = 64
BLOCK_Q2_0_BYTES = 18  # 2B fp16 d + 16B qs

# ggml_type enum values verified against ggml.h & live libggml-base.so
GGML_TYPE_F32 = 0
GGML_TYPE_F16 = 1
GGML_TYPE_Q4_0 = 2
GGML_TYPE_Q8_0 = 8
GGML_TYPE_Q4_K = 12
GGML_TYPE_Q6_K = 14
GGML_TYPE_IQ2_XXS = 16
GGML_TYPE_IQ2_XS = 17
GGML_TYPE_IQ3_XXS = 18
GGML_TYPE_IQ1_S = 19
GGML_TYPE_IQ4_NL = 20
GGML_TYPE_IQ3_S = 21
GGML_TYPE_IQ2_S = 22
GGML_TYPE_BF16 = 30
GGML_TYPE_Q2_0 = 42

QTYPE_NAME_TO_ID: Dict[str, int] = {
    "F32": GGML_TYPE_F32,
    "F16": GGML_TYPE_F16,
    "BF16": GGML_TYPE_BF16,
    "Q4_0": GGML_TYPE_Q4_0,
    "Q8_0": GGML_TYPE_Q8_0,
    "Q4_K": GGML_TYPE_Q4_K,
    "Q6_K": GGML_TYPE_Q6_K,
    "IQ2_XXS": GGML_TYPE_IQ2_XXS,
    "IQ2_XS": GGML_TYPE_IQ2_XS,
    "IQ3_XXS": GGML_TYPE_IQ3_XXS,
    "IQ1_S": GGML_TYPE_IQ1_S,
    "IQ4_NL": GGML_TYPE_IQ4_NL,
    "IQ3_S": GGML_TYPE_IQ3_S,
    "IQ2_S": GGML_TYPE_IQ2_S,
    "Q2_0": GGML_TYPE_Q2_0,
}


def pack_q2_0_blocks(d_fp16: np.ndarray, codes_u8: np.ndarray) -> np.ndarray:
    """Pack FP16 scales [..., n_blocks] and 2-bit codes [..., n_blocks, 64] in {0,1,2,3}
    into exact ggml block_q2_0 byte layout [..., n_blocks * 18] uint8.

    Matches ggml-quants.c:449-455:
      byte_index = j // 4, bit_offset = (j % 4) * 2
    """
    d_arr = np.ascontiguousarray(d_fp16, dtype="<f2")
    q_arr = np.ascontiguousarray(codes_u8, dtype=np.uint8)
    lead_shape = d_arr.shape[:-1]
    n_blocks = d_arr.shape[-1]
    if q_arr.shape != (*lead_shape, n_blocks, QK2_0):
        raise ValueError(f"codes shape {q_arr.shape} != expected {(*lead_shape, n_blocks, QK2_0)}")

    q4 = q_arr.reshape(*lead_shape, n_blocks, 16, 4)
    qs = (
        (q4[..., 0] & 0x03)
        | ((q4[..., 1] & 0x03) << 2)
        | ((q4[..., 2] & 0x03) << 4)
        | ((q4[..., 3] & 0x03) << 6)
    ).astype(np.uint8)

    d_bytes = d_arr.view(np.uint8).reshape(*lead_shape, n_blocks, 2)
    packed = np.concatenate([d_bytes, qs], axis=-1)
    return np.ascontiguousarray(packed.reshape(*lead_shape, n_blocks * BLOCK_Q2_0_BYTES))


def dequantize_q2_0_cleanroom(packed_u8: np.ndarray) -> np.ndarray:
    """Clean-room NumPy dequantizer matching ggml-quants.c:dequantize_row_q2_0 bit-for-bit."""
    raw = np.ascontiguousarray(packed_u8, dtype=np.uint8)
    if raw.shape[-1] % BLOCK_Q2_0_BYTES != 0:
        raise ValueError(f"Last dim {raw.shape[-1]} not divisible by {BLOCK_Q2_0_BYTES}")
    lead_shape = raw.shape[:-1]
    n_blocks = raw.shape[-1] // BLOCK_Q2_0_BYTES
    blk = raw.reshape(*lead_shape, n_blocks, BLOCK_Q2_0_BYTES)

    d_f32 = np.ascontiguousarray(blk[..., :2]).view("<f2")[..., 0].astype(np.float32)
    qs = blk[..., 2:]  # [..., n_blocks, 16]
    q0 = (qs & 0x03).astype(np.int32) - 1
    q1 = ((qs >> 2) & 0x03).astype(np.int32) - 1
    q2 = ((qs >> 4) & 0x03).astype(np.int32) - 1
    q3 = ((qs >> 6) & 0x03).astype(np.int32) - 1
    mult = np.stack([q0, q1, q2, q3], axis=-1).reshape(*lead_shape, n_blocks, QK2_0).astype(np.float32)
    out = mult * d_f32[..., None]
    return np.ascontiguousarray(out.reshape(*lead_shape, n_blocks * QK2_0), dtype=np.float32)


def _quantize_codes_given_scale(x: np.ndarray, d_f32: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Nearest 2-bit code q in {0,1,2,3} for w_hat = (q - 1) * d_f32 (supports d > 0 and d < 0)."""
    # Avoid division by zero when d == 0
    nonzero = np.abs(d_f32) > 0.0
    safe_d = np.where(nonzero, d_f32, 1.0)
    # m = q - 1 in {-1, 0, 1, 2} minimizes (x - m * d)^2 <=> m = round(x / d) clipped to [-1, 2]
    m = np.where(nonzero, np.rint(x / safe_d), 0.0)
    codes = (np.clip(m, -1.0, 2.0) + 1.0).astype(np.uint8)
    recon = (codes.astype(np.int32) - 1).astype(np.float32) * d_f32
    return codes, recon


def _gptq_block_given_scale(
    w_blk: np.ndarray,  # [R, 64] float32
    d_fp16: np.ndarray,  # [R] float16
    u_blk: np.ndarray,  # [64, 64] float32 upper-triangular inverse Cholesky factor
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run exact 64-column Cholesky-GPTQ inside one block for fixed signed FP16 scales d_fp16.

    Returns (codes_u8 [R, 64], q_recon_f32 [R, 64], err_scaled_f32 [R, 64]).
    """
    n_rows, qk = w_blk.shape
    w_work = w_blk.astype(np.float32).copy()
    d_f32 = d_fp16.astype(np.float32)  # [R]
    nonzero = np.abs(d_f32) > 0.0
    safe_d = np.where(nonzero, d_f32, 1.0)

    codes = np.empty((n_rows, qk), dtype=np.uint8)
    q_recon = np.empty((n_rows, qk), dtype=np.float32)
    err_scaled = np.empty((n_rows, qk), dtype=np.float32)

    for j in range(qk):
        wj = w_work[:, j]
        mj = np.where(nonzero, np.clip(np.rint(wj / safe_d), -1.0, 2.0), 0.0)
        cj = (mj + 1.0).astype(np.uint8)
        qj = (cj.astype(np.int32) - 1).astype(np.float32) * d_f32
        codes[:, j] = cj
        q_recon[:, j] = qj

        ujj = max(float(u_blk[j, j]), 1e-12)
        ej = (wj - qj) / ujj
        err_scaled[:, j] = ej
        if j + 1 < qk:
            w_work[:, j + 1 :] -= ej[:, None] * u_blk[j, j + 1 :][None, :]

    return codes, q_recon, err_scaled


def gsq_quantize_expert_q2_0(
    weight_f32: np.ndarray,  # [out_features=2560, in_features=640] float32
    hessian_f64: Optional[np.ndarray] = None,  # [640, 640] float64
    damp_ratio: float = 0.01,
    n_scale_grid: int = 17,
) -> Tuple[np.ndarray, np.ndarray]:
    """Clean-room Dual-Sign GSQ + Cholesky-GPTQ Q2_0 quantizer for a single 2D matrix.

    Args:
        weight_f32: [out_features, in_features] float32 (in_features divisible by 64).
        hessian_f64: [in_features, in_features] float64 input Hessian H = E[x x^T].
            If None, defaults to identity (pure dual-sign Lloyd-Max MSE optimal Q2_0).
        damp_ratio: relative diagonal damping on H before Cholesky inversion (default 1%).
        n_scale_grid: number of grid ratios per sign (searches 2 * n_scale_grid scales).

    Returns:
        (packed_u8 [out_features, in_features // 64 * 18], dequant_f32 [out_features, in_features])
    """
    w_orig = np.ascontiguousarray(weight_f32, dtype=np.float32)
    n_rows, n_cols = w_orig.shape
    if n_cols % QK2_0 != 0:
        raise ValueError(f"in_features={n_cols} must be divisible by QK2_0={QK2_0}")
    n_blocks = n_cols // QK2_0

    if hessian_f64 is None:
        h_damped = np.eye(n_cols, dtype=np.float64)
    else:
        h = np.asarray(hessian_f64, dtype=np.float64)
        h = 0.5 * (h + h.T)
        tr_mean = float(np.trace(h)) / float(n_cols)
        if tr_mean <= 0.0 or not np.all(np.isfinite(h)):
            h_damped = np.eye(n_cols, dtype=np.float64)
        else:
            damp = max(float(damp_ratio) * tr_mean, 1e-8)
            h_damped = h.copy()
            h_damped[np.arange(n_cols), np.arange(n_cols)] += damp

    # GPTQ upper-triangular inverse Cholesky factor U s.t. U^T U = H_damped^{-1}
    c_low = cho_factor(h_damped, lower=True, check_finite=False)
    h_inv = cho_solve(c_low, np.eye(n_cols, dtype=np.float64), check_finite=False)
    h_inv = 0.5 * (h_inv + h_inv.T)
    # Guard tiny numerical eigenvalues before upper Cholesky
    min_diag = float(np.min(np.diag(h_inv)))
    if min_diag <= 0.0:
        h_inv[np.arange(n_cols), np.arange(n_cols)] += abs(min_diag) + 1e-12
    u_inv = cholesky(h_inv, lower=False, check_finite=False).astype(np.float32)

    w_work = w_orig.copy()
    all_scales = np.empty((n_rows, n_blocks), dtype=np.float16)
    all_codes = np.empty((n_rows, n_blocks, QK2_0), dtype=np.uint8)
    dequant_out = np.empty((n_rows, n_cols), dtype=np.float32)

    ratios = np.linspace(0.45, 1.05, int(n_scale_grid), dtype=np.float32)

    for b in range(n_blocks):
        c0 = b * QK2_0
        c1 = c0 + QK2_0
        w_blk = w_work[:, c0:c1]  # [R, 64]
        h_bb = h_damped[c0:c1, c0:c1].astype(np.float32)  # [64, 64]
        # Lower Cholesky of H_bb for fast exact block quadratic loss ||(w - q) L_bb||_2^2
        l_bb = cholesky(h_damped[c0:c1, c0:c1], lower=True, check_finite=False).astype(np.float32)
        u_bb = u_inv[c0:c1, c0:c1]

        w_max = np.maximum(np.max(w_blk, axis=1), 0.0)
        w_min_abs = np.maximum(np.max(-w_blk, axis=1), 0.0)

        # Base full-range scales for positive d (+2 slot on +max, -1 slot on -min)
        # and negative d (-2 slot on -min, +1 slot on +max)
        s_pos_base = np.maximum(0.5 * w_max, w_min_abs)
        s_neg_base = np.maximum(0.5 * w_min_abs, w_max)

        # Vectorized dual-sign grid search under exact block Hessian metric (1 batched SGEMM!)
        d_p_grid16 = (s_pos_base[None, :] * ratios[:, None]).astype(np.float16)  # [G, R]
        _, q_p_all = _quantize_codes_given_scale(w_blk[None, :, :], d_p_grid16.astype(np.float32)[:, :, None])
        diff_p_all = ((w_blk[None, :, :] - q_p_all).reshape(-1, QK2_0) @ l_bb).reshape(ratios.size, n_rows, QK2_0)
        loss_p_all = np.sum(diff_p_all * diff_p_all, axis=2)  # [G, R]
        best_p_idx = np.argmin(loss_p_all, axis=0)
        best_pos_d = d_p_grid16[best_p_idx, np.arange(n_rows)]

        d_n_grid16 = (-s_neg_base[None, :] * ratios[:, None]).astype(np.float16)  # [G, R]
        _, q_n_all = _quantize_codes_given_scale(w_blk[None, :, :], d_n_grid16.astype(np.float32)[:, :, None])
        diff_n_all = ((w_blk[None, :, :] - q_n_all).reshape(-1, QK2_0) @ l_bb).reshape(ratios.size, n_rows, QK2_0)
        loss_n_all = np.sum(diff_n_all * diff_n_all, axis=2)  # [G, R]
        best_n_idx = np.argmin(loss_n_all, axis=0)
        best_neg_d = d_n_grid16[best_n_idx, np.arange(n_rows)]

        # Batched intra-block Cholesky-GPTQ for both signs simultaneously ([2*R, 64])
        hw_blk = w_blk @ h_bb  # [R, 64]
        w_blk_2 = np.concatenate([w_blk, w_blk], axis=0)
        d_init_2 = np.concatenate([best_pos_d, best_neg_d], axis=0)
        codes1_2, q1_2, err1_2 = _gptq_block_given_scale(w_blk_2, d_init_2, u_bb)

        m1_2 = codes1_2.astype(np.float32) - 1.0
        hm1_2 = m1_2 @ h_bb
        hw_2 = np.concatenate([hw_blk, hw_blk], axis=0)
        num_2 = np.sum(hw_2 * m1_2, axis=1)
        den_2 = np.sum(hm1_2 * m1_2, axis=1)
        d_ref_2 = np.where(den_2 > 1e-20, num_2 / np.maximum(den_2, 1e-20), 0.0).astype(np.float16)
        codes2_2, q2_2, err2_2 = _gptq_block_given_scale(w_blk_2, d_ref_2, u_bb)

        codes_r_2, q_r_2 = _quantize_codes_given_scale(w_blk_2, d_ref_2.astype(np.float32)[:, None])
        err_r_2 = np.linalg.solve(u_bb.T, (w_blk_2 - q_r_2).T).T.astype(np.float32)

        cand_list = [
            (d_init_2[:n_rows], codes1_2[:n_rows], q1_2[:n_rows], err1_2[:n_rows]),
            (d_ref_2[:n_rows], codes2_2[:n_rows], q2_2[:n_rows], err2_2[:n_rows]),
            (d_ref_2[:n_rows], codes_r_2[:n_rows], q_r_2[:n_rows], err_r_2[:n_rows]),
            (d_init_2[n_rows:], codes1_2[n_rows:], q1_2[n_rows:], err1_2[n_rows:]),
            (d_ref_2[n_rows:], codes2_2[n_rows:], q2_2[n_rows:], err2_2[n_rows:]),
            (d_ref_2[n_rows:], codes_r_2[n_rows:], q_r_2[n_rows:], err_r_2[n_rows:]),
        ]

        win_loss = np.full(n_rows, np.inf, dtype=np.float32)
        win_d = best_pos_d.copy()
        win_codes = np.zeros((n_rows, QK2_0), dtype=np.uint8)
        win_q = np.zeros((n_rows, QK2_0), dtype=np.float32)
        win_err = np.zeros((n_rows, QK2_0), dtype=np.float32)

        for d_c, codes_c, q_c, err_c in cand_list:
            diff_c = (w_blk - q_c) @ l_bb
            loss_c = np.sum(diff_c * diff_c, axis=1)
            better = loss_c < win_loss
            win_loss = np.where(better, loss_c, win_loss)
            win_d = np.where(better, d_c, win_d)
            win_codes = np.where(better[:, None], codes_c, win_codes)
            win_q = np.where(better[:, None], q_c, win_q)
            win_err = np.where(better[:, None], err_c, win_err)

        all_scales[:, b] = win_d
        all_codes[:, b, :] = win_codes
        dequant_out[:, c0:c1] = win_q

        # Cross-block GPTQ error feedback into remaining columns c1:n_cols
        if c1 < n_cols:
            w_work[:, c1:n_cols] -= win_err @ u_inv[c0:c1, c1:n_cols]

    packed = pack_q2_0_blocks(all_scales, all_codes)
    return packed, dequant_out


def gsq_quantize_layer_down_exps(
    down_exps_or_fn: Any,  # [K, 2560, 640] np.ndarray (f16/f32) OR Callable[[int], np.ndarray]
    hessians_fn: Any,  # Callable[[int], np.ndarray] returning [640, 640] float64 for expert k
    num_experts: Optional[int] = None,
    out_dim: int = 2560,
    in_dim: int = 640,
    out_dtype: Any = np.float32,
    return_dequant: bool = True,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Quantize all K experts' down_proj [K, out_dim, in_dim] into contiguous Q2_0 bytes
    streaming 1 expert at a time (<= 6.25 MiB F32 scratch)."""
    if callable(down_exps_or_fn):
        if num_experts is None:
            raise ValueError("num_experts is required when down_exps_or_fn is a callable")
        k_exp = int(num_experts)
        first_w: Optional[np.ndarray] = None
        if k_exp > 0:
            first_w = np.ascontiguousarray(down_exps_or_fn(0), dtype=np.float32)
            out_dim, in_dim = int(first_w.shape[0]), int(first_w.shape[1])
    else:
        arr = down_exps_or_fn
        k_exp, out_dim, in_dim = int(arr.shape[0]), int(arr.shape[1]), int(arr.shape[2])
        first_w = None

    row_bytes = (in_dim // QK2_0) * BLOCK_Q2_0_BYTES
    packed_all = np.empty((k_exp, out_dim, row_bytes), dtype=np.uint8)
    dequant_all = (
        np.empty((k_exp, out_dim, in_dim), dtype=np.dtype(out_dtype)) if return_dequant else None
    )

    for k in range(k_exp):
        if callable(down_exps_or_fn):
            w_k = first_w if (k == 0 and first_w is not None) else np.ascontiguousarray(down_exps_or_fn(k), dtype=np.float32)
        else:
            w_k = np.ascontiguousarray(down_exps_or_fn[k], dtype=np.float32)
        h_k = hessians_fn(k) if hessians_fn is not None else None
        p_k, dq_k = gsq_quantize_expert_q2_0(w_k, hessian_f64=h_k)
        packed_all[k] = p_k
        if dequant_all is not None:
            dequant_all[k] = dq_k.astype(dequant_all.dtype, copy=False)
        del w_k, dq_k

    return packed_all, dequant_all


class _GGMLTypeTraitsC(ctypes.Structure):
    _fields_ = [
        ("type_name", ctypes.c_char_p),
        ("blck_size", ctypes.c_int64),
        ("blck_size_interleave", ctypes.c_int64),
        ("type_size", ctypes.c_size_t),
        ("is_quantized", ctypes.c_bool),
        ("to_float", ctypes.c_void_p),
        ("from_float_ref", ctypes.c_void_p),
    ]


_TO_FLOAT_FN = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.c_int64)


class LibGGMLQuantSimulator:
    """ctypes wrapper around native libggml-base.so for exact Stage 2b quant simulation
    (IQ3_XXS, IQ2_S, IQ3_S, IQ4_NL, Q2_0) and bit-exact dequant verification."""

    def __init__(self, so_path: Path | str = LLAMA_CPU_GGML_SO) -> None:
        self.so_path = Path(so_path)
        if not self.so_path.is_file():
            raise FileNotFoundError(f"libggml-base.so not found at {self.so_path}")
        self.lib = ctypes.CDLL(str(self.so_path))

        self.lib.ggml_get_type_traits.argtypes = [ctypes.c_int]
        self.lib.ggml_get_type_traits.restype = ctypes.POINTER(_GGMLTypeTraitsC)

        self.lib.ggml_quantize_init.argtypes = [ctypes.c_int]
        self.lib.ggml_quantize_init.restype = None

        self.lib.ggml_quantize_chunk.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_void_p,
            ctypes.c_int64,
            ctypes.c_int64,
            ctypes.c_int64,
            ctypes.POINTER(ctypes.c_float),
        ]
        self.lib.ggml_quantize_chunk.restype = ctypes.c_size_t

    def resolve_qtype(self, qtype: int | str) -> int:
        if isinstance(qtype, str):
            return QTYPE_NAME_TO_ID[qtype.upper()]
        return int(qtype)

    def traits(self, qtype: int | str) -> Tuple[str, int, int, Any]:
        qid = self.resolve_qtype(qtype)
        t_ptr = self.lib.ggml_get_type_traits(qid)
        if not t_ptr:
            raise ValueError(f"Null ggml_type_traits for qtype={qtype}")
        tr = t_ptr.contents
        name = tr.type_name.decode("utf-8") if tr.type_name else str(qid)
        to_f = ctypes.cast(tr.to_float, _TO_FLOAT_FN) if tr.to_float else None
        return name, int(tr.blck_size), int(tr.type_size), to_f

    def quantize_2d(
        self,
        weight_f32: np.ndarray,
        qtype: int | str,
        imatrix_row_f32: Optional[np.ndarray] = None,
        init_tables: bool = True,
    ) -> np.ndarray:
        """Quantize a 2D [nrows, n_per_row] float32 matrix using ggml_quantize_chunk."""
        qid = self.resolve_qtype(qtype)
        _, blck_size, type_size, _ = self.traits(qid)
        src = np.ascontiguousarray(weight_f32, dtype=np.float32)
        if src.ndim != 2 or src.shape[1] % blck_size != 0:
            raise ValueError(f"Shape {src.shape} incompatible with blck_size={blck_size}")
        nrows, n_per_row = src.shape
        row_bytes = (n_per_row // blck_size) * type_size
        dst = np.empty((nrows, row_bytes), dtype=np.uint8)

        imat_ptr = None
        if imatrix_row_f32 is not None:
            imat = np.ascontiguousarray(imatrix_row_f32, dtype=np.float32).reshape(n_per_row)
            imat_ptr = imat.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        elif qid in (GGML_TYPE_IQ2_XXS, GGML_TYPE_IQ2_XS, GGML_TYPE_IQ2_S, GGML_TYPE_IQ1_S):
            # IQ2_* requires non-null imatrix in ggml_quantize_chunk
            imat = np.ones(n_per_row, dtype=np.float32)
            imat_ptr = imat.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

        if init_tables:
            self.lib.ggml_quantize_init(qid)
        n_written = self.lib.ggml_quantize_chunk(
            qid,
            src.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            dst.ctypes.data_as(ctypes.c_void_p),
            0,
            nrows,
            n_per_row,
            imat_ptr,
        )
        if int(n_written) != dst.nbytes:
            raise RuntimeError(f"ggml_quantize_chunk wrote {n_written} B, expected {dst.nbytes} B")
        return dst

    def dequantize_bytes(self, packed_u8: np.ndarray, qtype: int | str, n_elems: int) -> np.ndarray:
        """Dequantize raw quantized bytes to float32 using libggml-base.so to_float."""
        qid = self.resolve_qtype(qtype)
        name, _, _, to_f = self.traits(qid)
        if to_f is None:
            raise RuntimeError(f"ggml type {name} has no to_float callback")
        raw = np.ascontiguousarray(packed_u8, dtype=np.uint8)
        out = np.empty(int(n_elems), dtype=np.float32)
        to_f(raw.ctypes.data_as(ctypes.c_void_p), out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), int(n_elems))
        return out

    def quantize_dequantize_3d_experts(
        self,
        experts_arr: np.ndarray,  # [K, rows, cols] float16 or float32
        qtype: int | str,
        per_expert_imatrix: Optional[np.ndarray] = None,  # [K, cols] float32
        out_dtype: Any = np.float32,
        chunk_experts: int = 16,
    ) -> np.ndarray:
        """Quantize & dequantize 3D MoE tensor in <=16-expert F32 chunks (<=160 MiB scratch)
        into preallocated `out_dtype` (respecting llama-quant.cpp:820-840)."""
        qid = self.resolve_qtype(qtype)
        self.lib.ggml_quantize_init(qid)
        k_exp, rows, cols = experts_arr.shape
        out_dt = np.dtype(out_dtype)
        out = np.empty((k_exp, rows, cols), dtype=out_dt)
        step = max(1, int(chunk_experts))

        def _q_one(w_2d: np.ndarray, im_row: Optional[np.ndarray]) -> np.ndarray:
            packed = self.quantize_2d(w_2d, qtype=qid, imatrix_row_f32=im_row, init_tables=False)
            return self.dequantize_bytes(packed, qtype=qid, n_elems=rows * cols).reshape(rows, cols)

        with ThreadPoolExecutor(max_workers=8) as pool:
            for i0 in range(0, k_exp, step):
                i1 = min(i0 + step, k_exp)
                chunk_f32 = np.ascontiguousarray(experts_arr[i0:i1], dtype=np.float32)
                futs = [
                    (
                        i0 + rel_k,
                        pool.submit(
                            _q_one,
                            chunk_f32[rel_k],
                            per_expert_imatrix[i0 + rel_k] if per_expert_imatrix is not None else None,
                        ),
                    )
                    for rel_k in range(i1 - i0)
                ]
                for k, fut in futs:
                    out[k] = fut.result().astype(out_dt, copy=False)
                del chunk_f32
        return out


def verify_q2_0_bit_exact_and_gsq_gain(
    so_path: Path | str = LLAMA_CPU_GGML_SO,
    seed: int = 1234,
) -> Dict[str, object]:
    """Mandatory Wave 1 CPU test (OPUS §1.D2c):
    1. Verify clean-room Q2_0 dequantizer == gguf-py dequantizer == libggml-base.so to_float
       BIT-EXACT (uint32 view equality) across both positive and negative FP16 scales d.
    2. Verify clean-room Dual-Sign GSQ + GPTQ Q2_0 strictly beats stock quantize_q2_0
       (ggml_quantize_chunk(42)) on activation-weighted MoE down_proj reconstruction error.
    """
    sim = LibGGMLQuantSimulator(so_path)
    rng = np.random.default_rng(seed)

    # 1. Bit-exactness across 256 blocks (128 positive d, 128 negative d, including subnormals & zero)
    d_pos = (rng.uniform(1e-4, 2.5, size=(64,))).astype(np.float16)
    d_neg = (-rng.uniform(1e-4, 2.5, size=(64,))).astype(np.float16)
    d_edge = np.array([0.0, -0.0, 6e-8, -6e-8] * 32, dtype=np.float16)
    d_all = np.concatenate([d_pos, d_neg, d_edge]).reshape(16, 16)
    codes = rng.integers(0, 4, size=(16, 16, QK2_0), dtype=np.uint8)
    packed = pack_q2_0_blocks(d_all, codes)

    dq_clean = dequantize_q2_0_cleanroom(packed)
    dq_gguf = gguf.quants.dequantize(packed, gguf.GGMLQuantizationType.Q2_0)
    dq_c = sim.dequantize_bytes(packed, GGML_TYPE_Q2_0, n_elems=dq_clean.size).reshape(dq_clean.shape)

    bit_exact_clean_vs_c = bool(np.array_equal(dq_clean.view(np.uint32), dq_c.view(np.uint32)))
    bit_exact_gguf_vs_c = bool(np.array_equal(dq_gguf.view(np.uint32), dq_c.view(np.uint32)))

    # 2. Skewed SwiGLU MoE down_proj test: realistic heavy-tailed channel activations + signed outliers
    n_tok = 512
    out_dim = 256
    in_dim = 640
    # SwiGLU intermediate activations have strong channel-wise variance skew
    chan_scales = np.exp(rng.normal(0.0, 0.9, size=(1, in_dim))).astype(np.float32)
    raw_g = rng.standard_normal((n_tok, in_dim)).astype(np.float32)
    raw_u = rng.standard_normal((n_tok, in_dim)).astype(np.float32)
    x_act = (raw_g / (1.0 + np.exp(-raw_g))) * raw_u * chan_scales

    # MoE down_proj weights with realistic negative and positive outlier spikes per group
    w_true = (rng.standard_normal((out_dim, in_dim)) * 0.025).astype(np.float32)
    outlier_rows = rng.integers(0, out_dim, size=120)
    outlier_cols = rng.integers(0, in_dim, size=120)
    outlier_signs = rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=120)
    w_true[outlier_rows, outlier_cols] += outlier_signs * rng.uniform(0.09, 0.16, size=120).astype(np.float32)

    y_ref = x_act @ w_true.T
    ref_norm = float(np.linalg.norm(y_ref))

    # Stock ggml Q2_0 (even with imatrix passed)
    imat_vec = np.mean(x_act * x_act, axis=0).astype(np.float32)
    packed_stock = sim.quantize_2d(w_true, GGML_TYPE_Q2_0, imatrix_row_f32=imat_vec)
    w_stock = sim.dequantize_bytes(packed_stock, GGML_TYPE_Q2_0, n_elems=w_true.size).reshape(out_dim, in_dim)
    rel_err_stock = float(np.linalg.norm(y_ref - (x_act @ w_stock.T)) / ref_norm)

    # Clean-room Dual-Sign GSQ + Cholesky-GPTQ Q2_0
    h_mat = (x_act.astype(np.float64).T @ x_act.astype(np.float64)) / float(n_tok)
    packed_gsq, w_gsq_clean = gsq_quantize_expert_q2_0(w_true, hessian_f64=h_mat, damp_ratio=0.01)
    w_gsq_c = sim.dequantize_bytes(packed_gsq, GGML_TYPE_Q2_0, n_elems=w_true.size).reshape(out_dim, in_dim)

    bit_exact_gsq_roundtrip = bool(np.array_equal(w_gsq_clean.view(np.uint32), w_gsq_c.view(np.uint32)))
    rel_err_gsq = float(np.linalg.norm(y_ref - (x_act @ w_gsq_c.T)) / ref_norm)

    # Verify negative FP16 scales were actively chosen by GSQ on negative-skewed blocks
    blk_view = packed_gsq.reshape(out_dim, in_dim // QK2_0, BLOCK_Q2_0_BYTES)
    scales_chosen = np.ascontiguousarray(blk_view[:, :, :2]).view("<f2")[..., 0]
    neg_scale_frac = float(np.mean(scales_chosen < 0.0))

    passed = (
        bit_exact_clean_vs_c
        and bit_exact_gguf_vs_c
        and bit_exact_gsq_roundtrip
        and (rel_err_gsq < rel_err_stock)
        and (neg_scale_frac > 0.05)
    )
    return {
        "passed": passed,
        "bit_exact_clean_vs_libggml": bit_exact_clean_vs_c,
        "bit_exact_gguf_py_vs_libggml": bit_exact_gguf_vs_c,
        "bit_exact_gsq_pack_vs_libggml": bit_exact_gsq_roundtrip,
        "rel_l2_err_stock_q2_0": rel_err_stock,
        "rel_l2_err_gsq_q2_0": rel_err_gsq,
        "relative_error_reduction_pct": round((1.0 - rel_err_gsq / rel_err_stock) * 100.0, 2),
        "negative_scale_fraction": round(neg_scale_frac, 4),
    }
