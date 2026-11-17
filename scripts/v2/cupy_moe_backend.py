#!/usr/bin/env python3
"""CuPy cuBLAS (fp16 inputs -> fp32 accumulate) + CPU fallback MoE backend for SmartLLM v2.

Replaces scripts/step6_prune_reap.py:forward_moe_reap_and_imatrix with:
1. Fast CuPy cuBLAS GEMM execution when backend='cupy' (under GPU_TOKEN) and zero-GPU
   pure CPU execution when backend='cpu' (Wave 1 unit tests & CPU verification).
2. Inline REAP + domain-specialist + 512x512 HOPE co-activation + 69 MB exact Gram-cached
   top-32 RCO (A4') observation in a single pass.
3. Inline post-heal imatrix + per-expert [K, 640, 640] down_proj Hessian accumulation
   for clean-room GSQ Q2_0 quantization.
4. Optional CuPyLinearPatch to offload single-layer dense nn.Linear projections on
   CPU-only PyTorch installs (i9-14900HX has AVX2, no AVX-512 BF16).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from scripts.v2.common_io import LayerImatrixCollector, SampleDomainFlags


def _get_cupy():
    os.environ.setdefault("CUDA_PATH", "/opt/cuda")
    import cupy as cp  # Lazy import so backend='cpu' never touches CUDA

    return cp


def free_cupy_pools() -> None:
    """Release all cached blocks in CuPy device and pinned memory pools."""
    if "cupy" not in os.sys.modules:
        return
    import cupy as cp

    cp.cuda.Stream.null.synchronize()
    cp.get_default_memory_pool().free_all_blocks()
    cp.get_default_pinned_memory_pool().free_all_blocks()


def free_cupy_pinned_pool() -> None:
    """Release cached host pinned DMA staging blocks without touching live GPU device pools."""
    if "cupy" not in os.sys.modules:
        return
    import cupy as cp

    cp.cuda.Stream.null.synchronize()
    cp.get_default_pinned_memory_pool().free_all_blocks()


def cupy_upload_3d_chunked(
    arr_3d: np.ndarray,
    dtype: Any = np.float16,
    chunk_experts: int = 16,
) -> Any:
    """Upload 3D [E, ...] host array to CuPy in <=16-expert slices (<=100 MiB pinned DMA)."""
    cp = _get_cupy()
    np_dt = np.dtype(dtype)
    cp_dt = cp.float16 if np_dt == np.float16 else cp.float32
    n_exp = int(arr_3d.shape[0])
    dst = cp.empty(arr_3d.shape, dtype=cp_dt)
    step = max(1, int(chunk_experts))
    for i0 in range(0, n_exp, step):
        i1 = min(i0 + step, n_exp)
        sub_np = np.ascontiguousarray(arr_3d[i0:i1], dtype=np_dt)
        dst[i0:i1].set(sub_np)
        del sub_np
        cp.cuda.Stream.null.synchronize()
        cp.get_default_pinned_memory_pool().free_all_blocks()
    return dst


def cupy_download_3d_chunked(
    gpu_3d: Any,
    out_dtype: Any = np.float16,
    chunk_experts: int = 16,
) -> np.ndarray:
    """Download 3D [E, ...] CuPy array to host NumPy in <=16-expert slices (0 multi-GiB DMA)."""
    cp = _get_cupy()
    np_dt = np.dtype(out_dtype)
    n_exp = int(gpu_3d.shape[0])
    out = np.empty(gpu_3d.shape, dtype=np_dt)
    step = max(1, int(chunk_experts))
    for i0 in range(0, n_exp, step):
        i1 = min(i0 + step, n_exp)
        chunk_host = gpu_3d[i0:i1].get()
        out[i0:i1] = chunk_host.astype(np_dt, copy=False)
        del chunk_host
        cp.cuda.Stream.null.synchronize()
        cp.get_default_pinned_memory_pool().free_all_blocks()
    return out


def _silu_np_f32(x: np.ndarray) -> np.ndarray:
    x32 = x.astype(np.float32, copy=False)
    return x32 / (1.0 + np.exp(-np.clip(x32, -80.0, 80.0)))


def _sigmoid_np_f32(x: np.ndarray) -> np.ndarray:
    x32 = x.astype(np.float32, copy=False)
    return 1.0 / (1.0 + np.exp(-np.clip(x32, -80.0, 80.0)))


class CuPyLinearPatch:
    """Context/helper patching materialized nn.Linear modules in a single layer to run
    FP16->FP32 cuBLAS GEMMs via CuPy, freeing VRAM immediately on close()."""

    def __init__(self, module: nn.Module, enabled: bool = False, min_features: int = 256) -> None:
        self.module = module
        self.enabled = bool(enabled)
        self.min_features = int(min_features)
        self._patched: List[Tuple[nn.Linear, Any]] = []
        self._gpu_weights: List[Any] = []
        if self.enabled:
            self._apply()

    def _apply(self) -> None:
        cp = _get_cupy()
        for sub in self.module.modules():
            if not isinstance(sub, nn.Linear):
                continue
            if sub.weight.device.type == "meta":
                continue
            if max(sub.in_features, sub.out_features) < self.min_features:
                continue
            orig_forward = sub.forward
            w_fp16_np = sub.weight.detach().to(torch.float16).cpu().contiguous().numpy()
            w_gpu = cp.asarray(w_fp16_np)
            b_gpu = (
                cp.asarray(sub.bias.detach().to(torch.float32).cpu().contiguous().numpy())
                if sub.bias is not None
                else None
            )
            self._gpu_weights.append((w_gpu, b_gpu))

            def _make_fwd(wg, bg):
                def _fwd(x: torch.Tensor) -> torch.Tensor:
                    orig_dtype = x.dtype
                    orig_shape = x.shape
                    x2d = x.detach().to(torch.float16).cpu().contiguous().view(-1, orig_shape[-1]).numpy()
                    xg = cp.asarray(x2d)
                    yg = cp.matmul(xg, wg.T, dtype=cp.float32)
                    if bg is not None:
                        yg = yg + bg
                    y_np = cp.asnumpy(yg)
                    del xg, yg
                    out = torch.from_numpy(y_np).view(*orig_shape[:-1], wg.shape[0])
                    return out.to(orig_dtype)

                return _fwd

            sub.forward = _make_fwd(w_gpu, b_gpu)  # type: ignore[method-assign]
            self._patched.append((sub, orig_forward))

    def close(self) -> None:
        for sub, orig_forward in self._patched:
            sub.forward = orig_forward  # type: ignore[method-assign]
        self._patched.clear()
        self._gpu_weights.clear()
        if self.enabled:
            free_cupy_pools()


@dataclass
class A4PrimeCache:
    """Compact 69 MB exact Gram-matrix representation of top-M donor expert outputs
    for gradient-free greedy RCO backward elimination (A4').

    For each subsampled token t and its top-M (M=32) sorted donor experts idx[t, :]:
      - gram[t, i, j] = <E_{t, i}, E_{t, j}>   (float32, [T_sub, M, M])
      - target_dot[t, i] = <E_{t, i}, Y_routed_donor[t]> (float32, [T_sub, M])
      - target_norm2[t] = ||Y_routed_donor[t]||_2^2      (float32, [T_sub])
    Because D=2560 is contracted analytically into M x M inner products, every step
    of 512 -> K backward elimination evaluates exact ||Y_donor - Y_pruned||_2^2 in O(T_sub * top_k).
    """

    num_experts: int
    top_k: int
    top_m: int
    max_tokens: int
    idx: np.ndarray  # [T_cap, M] int16
    probs: np.ndarray  # [T_cap, M] float32 (unnormalized softmax probs sorted desc)
    gram: np.ndarray  # [T_cap, M, M] float32
    target_dot: np.ndarray  # [T_cap, M] float32
    target_norm2: np.ndarray  # [T_cap] float32
    filled: int = 0

    @classmethod
    def create(
        cls,
        num_experts: int = 512,
        top_k: int = 10,
        top_m: int = 32,
        max_tokens: int = 16384,
    ) -> "A4PrimeCache":
        m = min(int(top_m), int(num_experts))
        return cls(
            num_experts=int(num_experts),
            top_k=int(top_k),
            top_m=m,
            max_tokens=int(max_tokens),
            idx=np.zeros((max_tokens, m), dtype=np.int16),
            probs=np.zeros((max_tokens, m), dtype=np.float32),
            gram=np.zeros((max_tokens, m, m), dtype=np.float32),
            target_dot=np.zeros((max_tokens, m), dtype=np.float32),
            target_norm2=np.zeros((max_tokens,), dtype=np.float32),
            filled=0,
        )


class ReapHopeRcoAccumulator:
    """Single-layer donor MoE observer collecting REAP, domain quotas, HOPE co-activation,
    and optional A4' top-32 exact Gram cache."""

    def __init__(
        self,
        num_experts: int = 512,
        top_k: int = 10,
        image_pad_token_id: int = 248056,
        collect_rco_cache: bool = False,
        rco_max_tokens: int = 16384,
        rco_top_m: int = 32,
        rco_stride: int = 1,
    ) -> None:
        self.num_experts = int(num_experts)
        self.top_k = int(top_k)
        self.image_pad_token_id = int(image_pad_token_id)
        self.rco_stride = max(1, int(rco_stride))

        self.total_tokens: int = 0
        self.visual_image_pad_tokens: int = 0
        self.expert_frequency = np.zeros(num_experts, dtype=np.int64)
        self.ean_sum = np.zeros(num_experts, dtype=np.float64)
        self.weighted_ean_sum = np.zeros(num_experts, dtype=np.float64)
        self.weighted_expert_frequency_sum = np.zeros(num_experts, dtype=np.float64)
        self.max_activations = np.zeros(num_experts, dtype=np.float32)
        self.max_activations_signed = np.full(num_experts, -np.inf, dtype=np.float32)

        # Domain specialist accumulators (for WH=64 + RU>=40 + Copy/Craft>=35 + Vision>=30)
        self.stratum_tokens: Dict[str, int] = {}
        self.stratum_freq: Dict[str, np.ndarray] = {}
        self.stratum_wean: Dict[str, np.ndarray] = {}

        self.ru_tokens: int = 0
        self.ru_freq = np.zeros(num_experts, dtype=np.int64)
        self.ru_wean = np.zeros(num_experts, dtype=np.float64)

        self.craft_tokens: int = 0
        self.craft_freq = np.zeros(num_experts, dtype=np.int64)
        self.craft_wean = np.zeros(num_experts, dtype=np.float64)

        self.vis_sample_tokens: int = 0
        self.vis_sample_freq = np.zeros(num_experts, dtype=np.int64)
        self.vis_sample_wean = np.zeros(num_experts, dtype=np.float64)

        self.vis_patch_freq = np.zeros(num_experts, dtype=np.int64)
        self.vis_patch_wean = np.zeros(num_experts, dtype=np.float64)

        # HOPE 512x512 co-activation matrix C = sum_t r_t r_t^T (normalized top-k weights)
        self.coact_matrix = np.zeros((num_experts, num_experts), dtype=np.float64)

        self.rco_cache: Optional[A4PrimeCache] = (
            A4PrimeCache.create(
                num_experts=num_experts,
                top_k=top_k,
                top_m=rco_top_m,
                max_tokens=rco_max_tokens,
            )
            if collect_rco_cache
            else None
        )
        self._current_flags = SampleDomainFlags("general", "", False, False, False)

    def set_sample_flags(self, flags: SampleDomainFlags) -> None:
        self._current_flags = flags
        st = flags.stratum
        if st not in self.stratum_tokens:
            self.stratum_tokens[st] = 0
            self.stratum_freq[st] = np.zeros(self.num_experts, dtype=np.int64)
            self.stratum_wean[st] = np.zeros(self.num_experts, dtype=np.float64)

    def finalize_score_dict(self, min_count_floor: int = 5) -> Dict[str, Any]:
        """Export standardized score dictionary compatible with all selectors (A1..A4')."""
        freq = self.expert_frequency
        reap_raw = np.where(freq > 0, self.weighted_ean_sum / np.maximum(freq, 1), 0.0)
        reap_guarded = np.where(freq >= min_count_floor, reap_raw, 0.0)

        wsum_balanced = np.zeros(self.num_experts, dtype=np.float64)
        n_active_strata = 0
        for st, wean in self.stratum_wean.items():
            tot = float(wean.sum())
            if tot > 0.0:
                wsum_balanced += wean / tot
                n_active_strata += 1
        if n_active_strata == 0:
            tot = float(self.weighted_ean_sum.sum())
            if tot > 0.0:
                wsum_balanced = self.weighted_ean_sum / tot

        # Vision specialist saliency prioritizes actual image_pad visual patches,
        # plus 0.25x multimodal context tokens when visual patches are sparse.
        vis_combined = self.vis_patch_wean + 0.25 * self.vis_sample_wean
        vis_freq_combined = np.maximum(self.vis_patch_freq, self.vis_sample_freq)

        return {
            "total_tokens": int(self.total_tokens),
            "visual_image_pad_tokens": int(self.visual_image_pad_tokens),
            "num_experts": int(self.num_experts),
            "min_count_floor": int(min_count_floor),
            "active_experts": int(np.sum(freq > 0)),
            "dead_experts": int(np.sum(freq == 0)),
            "domain_tokens": {
                "ru": int(self.ru_tokens),
                "copy_craft": int(self.craft_tokens),
                "vision_sample": int(self.vis_sample_tokens),
                "vision_patch": int(self.visual_image_pad_tokens),
            },
            "arrays": {
                "reap_raw": reap_raw.tolist(),
                "reap_guarded": reap_guarded.tolist(),
                "wsum_balanced": wsum_balanced.tolist(),
                "expert_frequency": freq.tolist(),
                "weighted_ean_sum": self.weighted_ean_sum.tolist(),
                "weighted_expert_frequency_sum": self.weighted_expert_frequency_sum.tolist(),
                "ru_freq": self.ru_freq.tolist(),
                "ru_wean": self.ru_wean.tolist(),
                "copy_craft_freq": self.craft_freq.tolist(),
                "copy_craft_wean": self.craft_wean.tolist(),
                "freq_visual_image_pad": vis_freq_combined.tolist(),
                "weighted_ean_visual_image_pad": vis_combined.tolist(),
            },
            "stratum_wean": {k: v.tolist() for k, v in self.stratum_wean.items()},
        }


class PostHealStatsCollector:
    """Collects post-heal imatrix and per-expert down_proj Hessians H_e = sum x x^T."""

    def __init__(
        self,
        bid: int,
        num_experts: int,
        hidden_dim: int = 2560,
        inter_dim: int = 640,
        imatrix: Optional[LayerImatrixCollector] = None,
        collect_hessian: bool = True,
    ) -> None:
        self.bid = int(bid)
        self.num_experts = int(num_experts)
        self.hidden_dim = int(hidden_dim)
        self.inter_dim = int(inter_dim)
        self.imatrix = imatrix if imatrix is not None else LayerImatrixCollector()
        self.collect_hessian = bool(collect_hessian)
        # Store H_e in float32 during streaming ([320, 640, 640] = 500 MiB) and upcast to fp64 in Cholesky
        self.down_hessians = (
            np.zeros((self.num_experts, self.inter_dim, self.inter_dim), dtype=np.float32)
            if self.collect_hessian
            else None
        )
        self.expert_token_counts = np.zeros(self.num_experts, dtype=np.int64)

        # Ensure 3D entries exist even if an expert gets 0 hits on small slices
        self.imatrix.ensure_3d(f"blk.{self.bid}.ffn_gate_exps.weight", self.num_experts, self.hidden_dim)
        self.imatrix.ensure_3d(f"blk.{self.bid}.ffn_up_exps.weight", self.num_experts, self.hidden_dim)
        self.imatrix.ensure_3d(f"blk.{self.bid}.ffn_down_exps.weight", self.num_experts, self.inter_dim)

    def get_damped_hessian_f64(self, expert_idx: int, damp_ratio: float = 0.01) -> np.ndarray:
        """Return normalized [640, 640] float64 Hessian with 1% relative diagonal damping."""
        if self.down_hessians is None:
            return np.eye(self.inter_dim, dtype=np.float64)
        cnt = int(self.expert_token_counts[expert_idx])
        if cnt <= 0:
            return np.eye(self.inter_dim, dtype=np.float64)
        h = self.down_hessians[expert_idx].astype(np.float64) / float(cnt)
        h = 0.5 * (h + h.T)
        diag_mean = float(np.trace(h)) / float(self.inter_dim)
        damp = max(damp_ratio * diag_mean, 1e-8)
        h[np.arange(self.inter_dim), np.arange(self.inter_dim)] += damp
        return h


class MoELayerWeights:
    """Unified CPU / CuPy-cuBLAS weight container for Qwen4ExpTextSparseMoeBlock."""

    def __init__(
        self,
        gate_weight_f32: np.ndarray,  # [E, D] float32
        gate_up_fp16: np.ndarray,  # [E, 2*I, D] float16
        down_fp16: np.ndarray,  # [E, D, I] float16
        sh_gate_fp16: np.ndarray,  # [I, D] float16
        sh_up_fp16: np.ndarray,  # [I, D] float16
        sh_down_fp16: np.ndarray,  # [D, I] float16
        sh_inp_gate_f32: np.ndarray,  # [1, D] or [D] float32
        top_k: int = 10,
        norm_topk_prob: bool = True,
        backend: str = "cpu",
    ) -> None:
        self.backend = str(backend).lower()
        if self.backend not in ("cpu", "cupy"):
            raise ValueError(f"Unsupported backend: {backend!r}")

        self._is_shallow_view = False
        self.num_experts, self.hidden_dim = gate_weight_f32.shape
        self.inter_dim = down_fp16.shape[2]
        self.top_k = min(int(top_k), int(self.num_experts))
        self.norm_topk_prob = bool(norm_topk_prob)

        sh_inp = np.asarray(sh_inp_gate_f32, dtype=np.float32).reshape(1, self.hidden_dim)

        if self.backend == "cupy":
            cp = _get_cupy()
            self.gate_w = cp.asarray(np.ascontiguousarray(gate_weight_f32, dtype=np.float32))
            self.gate_up = cupy_upload_3d_chunked(gate_up_fp16, dtype=np.float16, chunk_experts=16)
            self.down = cupy_upload_3d_chunked(down_fp16, dtype=np.float16, chunk_experts=16)
            self.sh_gate = cp.asarray(np.ascontiguousarray(sh_gate_fp16, dtype=np.float16))
            self.sh_up = cp.asarray(np.ascontiguousarray(sh_up_fp16, dtype=np.float16))
            self.sh_down = cp.asarray(np.ascontiguousarray(sh_down_fp16, dtype=np.float16))
            self.sh_inp_gate = cp.asarray(np.ascontiguousarray(sh_inp, dtype=np.float32))
            free_cupy_pinned_pool()
        else:
            self.gate_w = np.ascontiguousarray(gate_weight_f32, dtype=np.float32)
            self.gate_up = np.ascontiguousarray(gate_up_fp16, dtype=np.float16)
            self.down = np.ascontiguousarray(down_fp16, dtype=np.float16)
            self.sh_gate = np.ascontiguousarray(sh_gate_fp16, dtype=np.float16)
            self.sh_up = np.ascontiguousarray(sh_up_fp16, dtype=np.float16)
            self.sh_down = np.ascontiguousarray(sh_down_fp16, dtype=np.float16)
            self.sh_inp_gate = np.ascontiguousarray(sh_inp, dtype=np.float32)

    def shallow_view(
        self,
        gate_weight_f32: Optional[np.ndarray] = None,
        sh_down_fp16: Optional[np.ndarray] = None,
        down_override: Optional[Any] = None,
    ) -> "MoELayerWeights":
        """Create a zero-copy MoELayerWeights view reusing self.gate_up/down in VRAM/RAM."""
        obj = object.__new__(MoELayerWeights)
        obj._is_shallow_view = True
        obj.backend = self.backend
        obj.num_experts = self.num_experts
        obj.hidden_dim = self.hidden_dim
        obj.inter_dim = self.inter_dim
        obj.top_k = self.top_k
        obj.norm_topk_prob = self.norm_topk_prob
        obj.gate_up = self.gate_up
        obj.down = down_override if down_override is not None else self.down
        obj.sh_gate = self.sh_gate
        obj.sh_up = self.sh_up
        obj.sh_inp_gate = self.sh_inp_gate
        if self.backend == "cupy":
            cp = _get_cupy()
            obj.gate_w = (
                cp.asarray(np.ascontiguousarray(gate_weight_f32, dtype=np.float32))
                if gate_weight_f32 is not None
                else self.gate_w
            )
            obj.sh_down = (
                cp.asarray(np.ascontiguousarray(sh_down_fp16, dtype=np.float16))
                if sh_down_fp16 is not None
                else self.sh_down
            )
            free_cupy_pinned_pool()
        else:
            obj.gate_w = (
                np.ascontiguousarray(gate_weight_f32, dtype=np.float32)
                if gate_weight_f32 is not None
                else self.gate_w
            )
            obj.sh_down = (
                np.ascontiguousarray(sh_down_fp16, dtype=np.float16)
                if sh_down_fp16 is not None
                else self.sh_down
            )
        return obj

    @classmethod
    def from_st_index(
        cls,
        st_index: Any,
        mlp_prefix: str,
        moe_block: nn.Module,
        backend: str = "cupy",
        keep_indices: Optional[Sequence[int] | np.ndarray] = None,
        gate_override_f32: Optional[np.ndarray] = None,
        alpha_scales: Optional[np.ndarray] = None,
        sh_down_override: Optional[np.ndarray] = None,
        chunk_experts: int = 16,
    ) -> "MoELayerWeights":
        """Stream gate_up_proj and down_proj directly from SafetensorsIndex in 16-expert
        (<=100 MiB) slices without materializing 4.69 GiB BF16/FP16 full tensors in host RAM."""
        gu_key = f"{mlp_prefix}.experts.gate_up_proj"
        dn_key = f"{mlp_prefix}.experts.down_proj"
        _, _, _, gu_shape, _, _ = st_index.get_tensor_info(gu_key)
        _, _, _, dn_shape, _, _ = st_index.get_tensor_info(dn_key)

        idx = [int(i) for i in keep_indices] if keep_indices is not None else list(range(int(gu_shape[0])))
        k_exp = len(idx)
        two_inter, hidden_dim = int(gu_shape[1]), int(gu_shape[2])
        inter_dim = int(dn_shape[2])

        if gate_override_f32 is not None:
            gw = np.ascontiguousarray(gate_override_f32, dtype=np.float32)
        else:
            gw_t = moe_block.gate.weight.detach().to(torch.float32).cpu()
            gw = gw_t[idx].contiguous().numpy() if keep_indices is not None else gw_t.contiguous().numpy()

        sh_g = moe_block.shared_expert.gate_proj.weight.detach().to(torch.float16).cpu().contiguous().numpy()
        sh_u = moe_block.shared_expert.up_proj.weight.detach().to(torch.float16).cpu().contiguous().numpy()
        if sh_down_override is not None:
            sh_d = np.ascontiguousarray(sh_down_override, dtype=np.float16)
        else:
            sh_d = moe_block.shared_expert.down_proj.weight.detach().to(torch.float16).cpu().contiguous().numpy()
        sh_inp = moe_block.shared_expert_gate.weight.detach().to(torch.float32).cpu().contiguous().numpy().reshape(1, hidden_dim)

        alpha_np = np.asarray(alpha_scales, dtype=np.float32) if alpha_scales is not None else None
        step = max(1, int(chunk_experts))

        obj = object.__new__(cls)
        obj._is_shallow_view = False
        obj.backend = str(backend).lower()
        if obj.backend not in ("cpu", "cupy"):
            raise ValueError(f"Unsupported backend: {backend!r}")
        obj.num_experts = k_exp
        obj.hidden_dim = hidden_dim
        obj.inter_dim = inter_dim
        obj.top_k = min(int(moe_block.gate.top_k), k_exp)
        obj.norm_topk_prob = bool(moe_block.gate.norm_topk_prob)

        if obj.backend == "cupy":
            cp = _get_cupy()
            obj.gate_w = cp.asarray(gw)
            obj.sh_gate = cp.asarray(sh_g)
            obj.sh_up = cp.asarray(sh_u)
            obj.sh_down = cp.asarray(sh_d)
            obj.sh_inp_gate = cp.asarray(sh_inp)
            obj.gate_up = cp.empty((k_exp, two_inter, hidden_dim), dtype=cp.float16)
            obj.down = cp.empty((k_exp, hidden_dim, inter_dim), dtype=cp.float16)
            for i0 in range(0, k_exp, step):
                i1 = min(i0 + step, k_exp)
                sub_idx = idx[i0:i1]
                gu_sl = st_index.load_expert_slice(gu_key, sub_idx, dtype=torch.float16).contiguous().numpy()
                obj.gate_up[i0:i1].set(gu_sl)
                del gu_sl
                cp.cuda.Stream.null.synchronize()
                cp.get_default_pinned_memory_pool().free_all_blocks()

                if alpha_np is not None:
                    dn_sl_t = st_index.load_expert_slice(dn_key, sub_idx, dtype=torch.float32)
                    al_t = torch.from_numpy(alpha_np[i0:i1]).view(-1, 1, 1)
                    dn_sl = (dn_sl_t * al_t).to(torch.float16).contiguous().numpy()
                    del dn_sl_t
                else:
                    dn_sl = st_index.load_expert_slice(dn_key, sub_idx, dtype=torch.float16).contiguous().numpy()
                obj.down[i0:i1].set(dn_sl)
                del dn_sl
                cp.cuda.Stream.null.synchronize()
                cp.get_default_pinned_memory_pool().free_all_blocks()
        else:
            obj.gate_w = gw
            obj.sh_gate = sh_g
            obj.sh_up = sh_u
            obj.sh_down = sh_d
            obj.sh_inp_gate = sh_inp
            obj.gate_up = np.empty((k_exp, two_inter, hidden_dim), dtype=np.float16)
            obj.down = np.empty((k_exp, hidden_dim, inter_dim), dtype=np.float16)
            for i0 in range(0, k_exp, step):
                i1 = min(i0 + step, k_exp)
                sub_idx = idx[i0:i1]
                obj.gate_up[i0:i1] = st_index.load_expert_slice(gu_key, sub_idx, dtype=torch.float16).numpy()
                if alpha_np is not None:
                    dn_sl_t = st_index.load_expert_slice(dn_key, sub_idx, dtype=torch.float32)
                    al_t = torch.from_numpy(alpha_np[i0:i1]).view(-1, 1, 1)
                    obj.down[i0:i1] = (dn_sl_t * al_t).to(torch.float16).numpy()
                else:
                    obj.down[i0:i1] = st_index.load_expert_slice(dn_key, sub_idx, dtype=torch.float16).numpy()

        return obj

    @classmethod
    def from_hf_moe_block(
        cls,
        moe_block: nn.Module,
        backend: str = "cpu",
        keep_indices: Optional[Sequence[int] | np.ndarray] = None,
        gate_override_f32: Optional[np.ndarray] = None,
        alpha_scales: Optional[np.ndarray] = None,
        sh_down_override: Optional[np.ndarray] = None,
    ) -> "MoELayerWeights":
        """Extract weights from Qwen4ExpTextSparseMoeBlock with optional pruning/healing.
        Automatically streams in 16-expert slices via SafetensorsIndex when experts are on meta."""
        st_src = getattr(moe_block, "_v2_st_source", None)
        is_meta = getattr(moe_block.experts.gate_up_proj, "device", None) is not None and (
            moe_block.experts.gate_up_proj.device.type == "meta"
        )
        if st_src is not None and is_meta:
            st_idx, mlp_pfx = st_src
            return cls.from_st_index(
                st_index=st_idx,
                mlp_prefix=mlp_pfx,
                moe_block=moe_block,
                backend=backend,
                keep_indices=keep_indices,
                gate_override_f32=gate_override_f32,
                alpha_scales=alpha_scales,
                sh_down_override=sh_down_override,
            )

        idx = [int(i) for i in keep_indices] if keep_indices is not None else None

        if gate_override_f32 is not None:
            gw = np.asarray(gate_override_f32, dtype=np.float32)
        else:
            gw_t = moe_block.gate.weight.detach().to(torch.float32).cpu()
            if idx is not None:
                gw_t = gw_t[idx]
            gw = gw_t.numpy()

        gu_t = moe_block.experts.gate_up_proj.detach()
        dn_t = moe_block.experts.down_proj.detach()
        if idx is not None:
            gu_t = gu_t[idx]
            dn_t = dn_t[idx]
        gu_fp16 = gu_t.to(torch.float16).cpu().numpy()

        if alpha_scales is not None:
            alpha_t = torch.from_numpy(np.asarray(alpha_scales, dtype=np.float32)).view(-1, 1, 1)
            dn_fp16 = (dn_t.to(torch.float32).cpu() * alpha_t).to(torch.float16).numpy()
        else:
            dn_fp16 = dn_t.to(torch.float16).cpu().numpy()

        sh_g = moe_block.shared_expert.gate_proj.weight.detach().to(torch.float16).cpu().numpy()
        sh_u = moe_block.shared_expert.up_proj.weight.detach().to(torch.float16).cpu().numpy()
        if sh_down_override is not None:
            sh_d = np.asarray(sh_down_override, dtype=np.float16)
        else:
            sh_d = moe_block.shared_expert.down_proj.weight.detach().to(torch.float16).cpu().numpy()
        sh_inp = moe_block.shared_expert_gate.weight.detach().to(torch.float32).cpu().numpy()

        return cls(
            gate_weight_f32=gw,
            gate_up_fp16=gu_fp16,
            down_fp16=dn_fp16,
            sh_gate_fp16=sh_g,
            sh_up_fp16=sh_u,
            sh_down_fp16=sh_d,
            sh_inp_gate_f32=sh_inp,
            top_k=int(moe_block.gate.top_k),
            norm_topk_prob=bool(moe_block.gate.norm_topk_prob),
            backend=backend,
        )

    def close(self) -> None:
        is_view = getattr(self, "_is_shallow_view", False)
        self.gate_w = None
        self.gate_up = None
        self.down = None
        self.sh_gate = None
        self.sh_up = None
        self.sh_down = None
        self.sh_inp_gate = None
        if self.backend == "cupy":
            if is_view:
                free_cupy_pinned_pool()
            else:
                free_cupy_pools()


def route_topk_exact_np(
    logits_f32: np.ndarray,
    top_k: int = 10,
    norm_topk_prob: bool = True,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exact NumPy replica of Qwen4ExpTextTopKRouter.forward (softmax -> topk -> renorm).

    Returns (topk_weights_f32 [T, K], topk_indices_i64 [T, K], full_probs_f32 [T, E]).
    """
    shifted = logits_f32 - np.max(logits_f32, axis=-1, keepdims=True)
    exp_l = np.exp(shifted, dtype=np.float32)
    probs = exp_l / np.sum(exp_l, axis=-1, keepdims=True)

    k = min(int(top_k), probs.shape[-1])
    # argpartition + exact descending sort within top-k (tie-breaking lowest index first like torch.topk)
    part_idx = np.argpartition(-probs, kth=k - 1, axis=-1)[:, :k]
    part_vals = np.take_along_axis(probs, part_idx, axis=-1)
    # Sort descending by value, ascending by index on exact ties
    order = np.lexsort((part_idx, -part_vals), axis=-1)
    topk_idx = np.take_along_axis(part_idx, order, axis=-1).astype(np.int64)
    topk_w = np.take_along_axis(part_vals, order, axis=-1).astype(np.float32)
    if norm_topk_prob:
        denom = np.maximum(np.sum(topk_w, axis=-1, keepdims=True), 1e-20)
        topk_w = topk_w / denom
    return topk_w, topk_idx, probs


def forward_moe_v2(
    moe_w: MoELayerWeights,
    hidden_states: torch.Tensor | np.ndarray,
    flat_token_ids: Optional[torch.Tensor | np.ndarray] = None,
    reap_acc: Optional[ReapHopeRcoAccumulator] = None,
    post_heal: Optional[PostHealStatsCollector] = None,
    return_components: bool = False,
) -> torch.Tensor | Tuple[torch.Tensor, np.ndarray, np.ndarray, np.ndarray]:
    """Execute Qwen4ExpTextSparseMoeBlock forward via CuPy cuBLAS (fp16->fp32) or CPU.

    Matches Qwen4ExpTextSparseMoeBlock.forward bit-level math:
      shared_out = sigmoid(shared_expert_gate(h)) * shared_expert(h)
      routed_out = sum_{m=1..top_k} w_{t,m} * expert_{idx_{t,m}}(h_t)
      out = routed_out + shared_out
    """
    is_torch = isinstance(hidden_states, torch.Tensor)
    orig_shape = tuple(hidden_states.shape)
    orig_dtype = hidden_states.dtype if is_torch else None
    orig_device = hidden_states.device if is_torch else None

    if is_torch:
        x_f32_cpu = hidden_states.detach().to(torch.float32).cpu().contiguous().view(-1, moe_w.hidden_dim).numpy()
    else:
        x_f32_cpu = np.ascontiguousarray(hidden_states, dtype=np.float32).reshape(-1, moe_w.hidden_dim)

    n_tok = x_f32_cpu.shape[0]
    inter = moe_w.inter_dim

    if post_heal is not None:
        bid = post_heal.bid
        post_heal.imatrix.record_2d(
            (
                f"blk.{bid}.ffn_gate_inp.weight",
                f"blk.{bid}.ffn_gate_shexp.weight",
                f"blk.{bid}.ffn_up_shexp.weight",
                f"blk.{bid}.ffn_gate_inp_shexp.weight",
            ),
            x_f32_cpu,
        )

    if moe_w.backend == "cupy":
        if reap_acc is None and post_heal is None and n_tok > 4096:
            out_f32 = np.empty((n_tok, moe_w.hidden_dim), dtype=np.float32)
            routed_f32 = np.empty((n_tok, moe_w.hidden_dim), dtype=np.float32) if return_components else np.empty(0, dtype=np.float32)
            sh_inter_f32 = np.empty((n_tok, inter), dtype=np.float32) if return_components else np.empty(0, dtype=np.float32)
            sh_gate_sig_f32 = np.empty((n_tok, 1), dtype=np.float32) if return_components else np.empty(0, dtype=np.float32)
            for t0 in range(0, n_tok, 4096):
                t1 = min(n_tok, t0 + 4096)
                o_c, r_c, si_c, sg_c = _forward_moe_cupy(
                    moe_w, x_f32_cpu[t0:t1], None, None, None, return_components
                )
                out_f32[t0:t1] = o_c
                if return_components:
                    routed_f32[t0:t1] = r_c
                    sh_inter_f32[t0:t1] = si_c
                    sh_gate_sig_f32[t0:t1] = sg_c
            free_cupy_pinned_pool()
        else:
            out_f32, routed_f32, sh_inter_f32, sh_gate_sig_f32 = _forward_moe_cupy(
                moe_w, x_f32_cpu, flat_token_ids, reap_acc, post_heal, return_components
            )
    else:
        out_f32, routed_f32, sh_inter_f32, sh_gate_sig_f32 = _forward_moe_cpu(
            moe_w, x_f32_cpu, flat_token_ids, reap_acc, post_heal, return_components
        )

    if is_torch:
        out_t = torch.from_numpy(out_f32).view(*orig_shape).to(dtype=orig_dtype, device=orig_device)
    else:
        out_t = torch.from_numpy(out_f32.reshape(orig_shape))

    if return_components:
        return out_t, routed_f32, sh_inter_f32, sh_gate_sig_f32
    return out_t


def _forward_moe_cpu(
    moe_w: MoELayerWeights,
    x_f32: np.ndarray,
    flat_token_ids: Optional[torch.Tensor | np.ndarray],
    reap_acc: Optional[ReapHopeRcoAccumulator],
    post_heal: Optional[PostHealStatsCollector],
    need_components: bool,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_tok, hidden_dim = x_f32.shape
    inter = moe_w.inter_dim
    x_fp16 = x_f32.astype(np.float16)
    x_fp16_f32 = x_fp16.astype(np.float32)

    # Shared expert
    sh_g = x_fp16_f32 @ moe_w.sh_gate.astype(np.float32).T
    sh_u = x_fp16_f32 @ moe_w.sh_up.astype(np.float32).T
    sh_inter = _silu_np_f32(sh_g) * sh_u
    if post_heal is not None:
        post_heal.imatrix.record_2d(
            (f"blk.{post_heal.bid}.ffn_gate_shexp.weight", f"blk.{post_heal.bid}.ffn_up_shexp.weight"),
            x_f32,
        )
        post_heal.imatrix.record_2d((f"blk.{post_heal.bid}.ffn_down_shexp.weight",), sh_inter)
    sh_raw = sh_inter.astype(np.float16).astype(np.float32) @ moe_w.sh_down.astype(np.float32).T
    sh_sig = _sigmoid_np_f32(x_f32 @ moe_w.sh_inp_gate.T)  # [T, 1]
    sh_out = sh_raw * sh_sig

    # Router
    logits = x_f32 @ moe_w.gate_w.T
    topk_w, topk_idx, full_probs = route_topk_exact_np(
        logits, top_k=moe_w.top_k, norm_topk_prob=moe_w.norm_topk_prob
    )

    routed_out = np.zeros((n_tok, hidden_dim), dtype=np.float32)

    vis_mask: Optional[np.ndarray] = None
    if reap_acc is not None and flat_token_ids is not None:
        tids = (
            flat_token_ids.detach().cpu().numpy().reshape(-1)
            if isinstance(flat_token_ids, torch.Tensor)
            else np.asarray(flat_token_ids).reshape(-1)
        )
        vis_mask = tids == reap_acc.image_pad_token_id

    freq_loc = np.zeros(moe_w.num_experts, dtype=np.int64) if reap_acc is not None else None
    ean_loc = np.zeros(moe_w.num_experts, dtype=np.float64) if reap_acc is not None else None
    wean_loc = np.zeros(moe_w.num_experts, dtype=np.float64) if reap_acc is not None else None
    wfreq_loc = np.zeros(moe_w.num_experts, dtype=np.float64) if reap_acc is not None else None
    max_abs_loc = np.zeros(moe_w.num_experts, dtype=np.float32) if reap_acc is not None else None
    max_sig_loc = np.full(moe_w.num_experts, -np.inf, dtype=np.float32) if reap_acc is not None else None
    vp_freq_loc = np.zeros(moe_w.num_experts, dtype=np.int64) if (reap_acc is not None and vis_mask is not None) else None
    vp_wean_loc = np.zeros(moe_w.num_experts, dtype=np.float64) if (reap_acc is not None and vis_mask is not None) else None

    for e_idx in np.unique(topk_idx):
        tok_idx, slot_idx = np.where(topk_idx == e_idx)
        if tok_idx.size == 0:
            continue
        cur_x = x_fp16_f32[tok_idx]
        gu_w = moe_w.gate_up[e_idx].astype(np.float32)
        gu_out = cur_x @ gu_w.T
        gate_part = gu_out[:, :inter]
        up_part = gu_out[:, inter:]
        act = _silu_np_f32(gate_part) * up_part

        if post_heal is not None:
            bid = post_heal.bid
            post_heal.imatrix.record_3d_expert(
                (f"blk.{bid}.ffn_gate_exps.weight", f"blk.{bid}.ffn_up_exps.weight"),
                moe_w.num_experts,
                int(e_idx),
                cur_x,
            )
            post_heal.imatrix.record_3d_expert(
                (f"blk.{bid}.ffn_down_exps.weight",),
                moe_w.num_experts,
                int(e_idx),
                act,
            )
            post_heal.expert_token_counts[e_idx] += tok_idx.size
            if post_heal.down_hessians is not None:
                post_heal.down_hessians[e_idx] += act.T @ act

        dn_w = moe_w.down[e_idx].astype(np.float32)
        unweighted = act.astype(np.float16).astype(np.float32) @ dn_w.T
        w = topk_w[tok_idx, slot_idx][:, None]
        np.add.at(routed_out, tok_idx, unweighted * w)

        if reap_acc is not None:
            norms = np.linalg.norm(unweighted, ord=2, axis=-1).astype(np.float64)
            w64 = topk_w[tok_idx, slot_idx].astype(np.float64)
            wn = w64 * norms
            freq_loc[e_idx] += tok_idx.size  # type: ignore[index]
            ean_loc[e_idx] += float(norms.sum())  # type: ignore[index]
            wean_loc[e_idx] += float(wn.sum())  # type: ignore[index]
            wfreq_loc[e_idx] += float(w64.sum())  # type: ignore[index]
            max_abs_loc[e_idx] = max(max_abs_loc[e_idx], float(np.max(np.abs(unweighted))))  # type: ignore[index]
            max_sig_loc[e_idx] = max(max_sig_loc[e_idx], float(np.max(unweighted)))  # type: ignore[index]
            if vis_mask is not None and vp_freq_loc is not None and vp_wean_loc is not None:
                iv = vis_mask[tok_idx]
                if np.any(iv):
                    vp_freq_loc[e_idx] += int(iv.sum())
                    vp_wean_loc[e_idx] += float(wn[iv].sum())

    if reap_acc is not None:
        _commit_reap_hope_rco_cpu(
            reap_acc=reap_acc,
            n_tok=n_tok,
            x_fp16_f32=x_fp16_f32,
            moe_w=moe_w,
            topk_w=topk_w,
            topk_idx=topk_idx,
            full_probs=full_probs,
            routed_out=routed_out,
            vis_mask=vis_mask,
            freq_loc=freq_loc,  # type: ignore[arg-type]
            ean_loc=ean_loc,  # type: ignore[arg-type]
            wean_loc=wean_loc,  # type: ignore[arg-type]
            wfreq_loc=wfreq_loc,  # type: ignore[arg-type]
            max_abs_loc=max_abs_loc,  # type: ignore[arg-type]
            max_sig_loc=max_sig_loc,  # type: ignore[arg-type]
            vp_freq_loc=vp_freq_loc,
            vp_wean_loc=vp_wean_loc,
        )

    total_out = routed_out + sh_out
    if not need_components:
        return total_out, np.empty(0, dtype=np.float32), np.empty(0, dtype=np.float32), np.empty(0, dtype=np.float32)
    return total_out, routed_out, sh_inter, sh_sig


def _forward_moe_cupy(
    moe_w: MoELayerWeights,
    x_f32: np.ndarray,
    flat_token_ids: Optional[torch.Tensor | np.ndarray],
    reap_acc: Optional[ReapHopeRcoAccumulator],
    post_heal: Optional[PostHealStatsCollector],
    need_components: bool,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    cp = _get_cupy()
    n_tok, hidden_dim = x_f32.shape
    inter = moe_w.inter_dim

    xg_f32 = cp.asarray(x_f32)
    xg_fp16 = xg_f32.astype(cp.float16)

    # Shared expert via cuBLAS fp16->fp32
    sh_g = cp.matmul(xg_fp16, moe_w.sh_gate.T, dtype=cp.float32)
    sh_u = cp.matmul(xg_fp16, moe_w.sh_up.T, dtype=cp.float32)
    sh_inter_g = (sh_g / (1.0 + cp.exp(-sh_g))) * sh_u
    if post_heal is not None:
        post_heal.imatrix.record_2d(
            (f"blk.{post_heal.bid}.ffn_gate_shexp.weight", f"blk.{post_heal.bid}.ffn_up_shexp.weight"),
            x_f32,
        )
        post_heal.imatrix.record_2d((f"blk.{post_heal.bid}.ffn_down_shexp.weight",), cp.asnumpy(sh_inter_g))
    sh_raw_g = cp.matmul(sh_inter_g.astype(cp.float16), moe_w.sh_down.T, dtype=cp.float32)
    sh_sig_g = 1.0 / (1.0 + cp.exp(-cp.matmul(xg_f32, moe_w.sh_inp_gate.T)))
    sh_out_g = sh_raw_g * sh_sig_g

    # Router logits on GPU, exact top-k on CPU/GPU
    logits_np = cp.asnumpy(cp.matmul(xg_f32, moe_w.gate_w.T))
    topk_w, topk_idx, full_probs = route_topk_exact_np(
        logits_np, top_k=moe_w.top_k, norm_topk_prob=moe_w.norm_topk_prob
    )
    topk_idx_g = cp.asarray(topk_idx)
    topk_w_g = cp.asarray(topk_w)

    routed_g = cp.zeros((n_tok, hidden_dim), dtype=cp.float32)

    vis_mask: Optional[np.ndarray] = None
    if reap_acc is not None and flat_token_ids is not None:
        tids = (
            flat_token_ids.detach().cpu().numpy().reshape(-1)
            if isinstance(flat_token_ids, torch.Tensor)
            else np.asarray(flat_token_ids).reshape(-1)
        )
        vis_mask = tids == reap_acc.image_pad_token_id

    freq_loc = np.zeros(moe_w.num_experts, dtype=np.int64) if reap_acc is not None else None
    ean_loc = np.zeros(moe_w.num_experts, dtype=np.float64) if reap_acc is not None else None
    wean_loc = np.zeros(moe_w.num_experts, dtype=np.float64) if reap_acc is not None else None
    wfreq_loc = np.zeros(moe_w.num_experts, dtype=np.float64) if reap_acc is not None else None
    max_abs_loc = np.zeros(moe_w.num_experts, dtype=np.float32) if reap_acc is not None else None
    max_sig_loc = np.full(moe_w.num_experts, -np.inf, dtype=np.float32) if reap_acc is not None else None
    vp_freq_loc = np.zeros(moe_w.num_experts, dtype=np.int64) if (reap_acc is not None and vis_mask is not None) else None
    vp_wean_loc = np.zeros(moe_w.num_experts, dtype=np.float64) if (reap_acc is not None and vis_mask is not None) else None

    # Sort (expert, token) pairs once so the GPU loop uses contiguous zero-copy slices
    # with zero per-expert PCIe sync stalls.
    flat_e = topk_idx.ravel()
    perm = np.argsort(flat_e, kind="mergesort")
    e_sorted = flat_e[perm]
    tok_sorted = (perm // moe_w.top_k).astype(np.int32)
    w_sorted = topk_w.ravel()[perm].astype(np.float32)
    uniq_e, starts, counts = np.unique(e_sorted, return_index=True, return_counts=True)
    n_uniq = int(uniq_e.size)

    tok_sorted_g = cp.asarray(tok_sorted)
    w_sorted_g = cp.asarray(w_sorted)[:, None]
    xg_sorted = xg_fp16[tok_sorted_g]

    all_norms_g = cp.empty(tok_sorted.size, dtype=cp.float32) if reap_acc is not None else None
    uniq_max_abs_g = cp.empty(n_uniq, dtype=cp.float32) if reap_acc is not None else None
    uniq_max_sig_g = cp.empty(n_uniq, dtype=cp.float32) if reap_acc is not None else None

    for idx_u in range(n_uniq):
        e_idx = int(uniq_e[idx_u])
        s_off = int(starts[idx_u])
        e_off = s_off + int(counts[idx_u])
        cur_x_g = xg_sorted[s_off:e_off]
        gu_out = cp.matmul(cur_x_g, moe_w.gate_up[e_idx].T, dtype=cp.float32)
        gate_part = gu_out[:, :inter]
        up_part = gu_out[:, inter:]
        act_g = (gate_part / (1.0 + cp.exp(-gate_part))) * up_part

        if post_heal is not None:
            tok_slice_np = tok_sorted[s_off:e_off]
            bid = post_heal.bid
            post_heal.imatrix.record_3d_expert(
                (f"blk.{bid}.ffn_gate_exps.weight", f"blk.{bid}.ffn_up_exps.weight"),
                moe_w.num_experts,
                e_idx,
                x_f32[tok_slice_np],
            )
            act_np = cp.asnumpy(act_g)
            post_heal.imatrix.record_3d_expert(
                (f"blk.{bid}.ffn_down_exps.weight",),
                moe_w.num_experts,
                e_idx,
                act_np,
            )
            post_heal.expert_token_counts[e_idx] += tok_slice_np.size
            if post_heal.down_hessians is not None:
                hess_g = cp.matmul(act_g.T, act_g)
                post_heal.down_hessians[e_idx] += cp.asnumpy(hess_g)
                del hess_g

        unweighted_g = cp.matmul(act_g.astype(cp.float16), moe_w.down[e_idx].T, dtype=cp.float32)
        cp.add.at(routed_g, tok_sorted_g[s_off:e_off], unweighted_g * w_sorted_g[s_off:e_off])

        if reap_acc is not None and all_norms_g is not None and uniq_max_abs_g is not None and uniq_max_sig_g is not None:
            all_norms_g[s_off:e_off] = cp.linalg.norm(unweighted_g, axis=-1)
            uniq_max_abs_g[idx_u] = cp.max(cp.abs(unweighted_g))
            uniq_max_sig_g[idx_u] = cp.max(unweighted_g)

    if reap_acc is not None and all_norms_g is not None and uniq_max_abs_g is not None and uniq_max_sig_g is not None:
        all_norms_np = cp.asnumpy(all_norms_g).astype(np.float64)
        uniq_max_abs_np = cp.asnumpy(uniq_max_abs_g)
        uniq_max_sig_np = cp.asnumpy(uniq_max_sig_g)
        w64_all = w_sorted.astype(np.float64)
        wn_all = w64_all * all_norms_np
        for idx_u in range(n_uniq):
            e_idx = int(uniq_e[idx_u])
            s_off = int(starts[idx_u])
            e_off = s_off + int(counts[idx_u])
            freq_loc[e_idx] += e_off - s_off  # type: ignore[index]
            ean_loc[e_idx] += float(all_norms_np[s_off:e_off].sum())  # type: ignore[index]
            wean_loc[e_idx] += float(wn_all[s_off:e_off].sum())  # type: ignore[index]
            wfreq_loc[e_idx] += float(w64_all[s_off:e_off].sum())  # type: ignore[index]
            max_abs_loc[e_idx] = max(max_abs_loc[e_idx], float(uniq_max_abs_np[idx_u]))  # type: ignore[index]
            max_sig_loc[e_idx] = max(max_sig_loc[e_idx], float(uniq_max_sig_np[idx_u]))  # type: ignore[index]
            if vis_mask is not None and vp_freq_loc is not None and vp_wean_loc is not None:
                iv = vis_mask[tok_sorted[s_off:e_off]]
                if np.any(iv):
                    vp_freq_loc[e_idx] += int(iv.sum())
                    vp_wean_loc[e_idx] += float(wn_all[s_off:e_off][iv].sum())
        del all_norms_g, uniq_max_abs_g, uniq_max_sig_g

    del tok_sorted_g, w_sorted_g, xg_sorted

    routed_np = cp.asnumpy(routed_g) if (reap_acc is not None or need_components) else np.empty(0, dtype=np.float32)
    total_np = cp.asnumpy(routed_g + sh_out_g)
    sh_inter_np = cp.asnumpy(sh_inter_g) if need_components else np.empty(0, dtype=np.float32)
    sh_sig_np = cp.asnumpy(sh_sig_g) if need_components else np.empty(0, dtype=np.float32)

    if reap_acc is not None:
        _commit_reap_hope_rco_cupy_or_cpu(
            reap_acc=reap_acc,
            n_tok=n_tok,
            x_f32=x_f32,
            xg_fp16=xg_fp16,
            moe_w=moe_w,
            topk_w=topk_w,
            topk_idx=topk_idx,
            full_probs=full_probs,
            routed_out=routed_np,
            vis_mask=vis_mask,
            freq_loc=freq_loc,  # type: ignore[arg-type]
            ean_loc=ean_loc,  # type: ignore[arg-type]
            wean_loc=wean_loc,  # type: ignore[arg-type]
            wfreq_loc=wfreq_loc,  # type: ignore[arg-type]
            max_abs_loc=max_abs_loc,  # type: ignore[arg-type]
            max_sig_loc=max_sig_loc,  # type: ignore[arg-type]
            vp_freq_loc=vp_freq_loc,
            vp_wean_loc=vp_wean_loc,
        )

    del xg_f32, xg_fp16, sh_g, sh_u, sh_inter_g, sh_raw_g, sh_sig_g, sh_out_g, topk_idx_g, topk_w_g, routed_g
    if reap_acc is not None or post_heal is not None or need_components:
        free_cupy_pinned_pool()
    return total_np, routed_np, sh_inter_np, sh_sig_np


def _update_common_reap_hope_stats(
    reap_acc: ReapHopeRcoAccumulator,
    n_tok: int,
    topk_w: np.ndarray,
    topk_idx: np.ndarray,
    vis_mask: Optional[np.ndarray],
    freq_loc: np.ndarray,
    ean_loc: np.ndarray,
    wean_loc: np.ndarray,
    wfreq_loc: np.ndarray,
    max_abs_loc: np.ndarray,
    max_sig_loc: np.ndarray,
    vp_freq_loc: Optional[np.ndarray],
    vp_wean_loc: Optional[np.ndarray],
) -> None:
    reap_acc.total_tokens += n_tok
    reap_acc.expert_frequency += freq_loc
    reap_acc.ean_sum += ean_loc
    reap_acc.weighted_ean_sum += wean_loc
    reap_acc.weighted_expert_frequency_sum += wfreq_loc
    reap_acc.max_activations = np.maximum(reap_acc.max_activations, max_abs_loc)
    reap_acc.max_activations_signed = np.maximum(reap_acc.max_activations_signed, max_sig_loc)

    fl = reap_acc._current_flags
    st = fl.stratum
    reap_acc.stratum_tokens[st] = reap_acc.stratum_tokens.get(st, 0) + n_tok
    if st not in reap_acc.stratum_freq:
        reap_acc.stratum_freq[st] = np.zeros(reap_acc.num_experts, dtype=np.int64)
        reap_acc.stratum_wean[st] = np.zeros(reap_acc.num_experts, dtype=np.float64)
    reap_acc.stratum_freq[st] += freq_loc
    reap_acc.stratum_wean[st] += wean_loc

    if fl.is_ru:
        reap_acc.ru_tokens += n_tok
        reap_acc.ru_freq += freq_loc
        reap_acc.ru_wean += wean_loc
    if fl.is_copy_craft:
        reap_acc.craft_tokens += n_tok
        reap_acc.craft_freq += freq_loc
        reap_acc.craft_wean += wean_loc
    if fl.is_vision:
        reap_acc.vis_sample_tokens += n_tok
        reap_acc.vis_sample_freq += freq_loc
        reap_acc.vis_sample_wean += wean_loc

    if vis_mask is not None and vp_freq_loc is not None and vp_wean_loc is not None:
        reap_acc.visual_image_pad_tokens += int(vis_mask.sum())
        reap_acc.vis_patch_freq += vp_freq_loc
        reap_acc.vis_patch_wean += vp_wean_loc

    # Sparse top-k scatter into dense [n_tok, E] float32 chunk -> C += R^T R
    r_dense = np.zeros((n_tok, reap_acc.num_experts), dtype=np.float32)
    rows = np.arange(n_tok)[:, None]
    r_dense[rows, topk_idx] = topk_w
    reap_acc.coact_matrix += (r_dense.T @ r_dense).astype(np.float64)


def _commit_reap_hope_rco_cpu(
    reap_acc: ReapHopeRcoAccumulator,
    n_tok: int,
    x_fp16_f32: np.ndarray,
    moe_w: MoELayerWeights,
    topk_w: np.ndarray,
    topk_idx: np.ndarray,
    full_probs: np.ndarray,
    routed_out: np.ndarray,
    vis_mask: Optional[np.ndarray],
    freq_loc: np.ndarray,
    ean_loc: np.ndarray,
    wean_loc: np.ndarray,
    wfreq_loc: np.ndarray,
    max_abs_loc: np.ndarray,
    max_sig_loc: np.ndarray,
    vp_freq_loc: Optional[np.ndarray],
    vp_wean_loc: Optional[np.ndarray],
) -> None:
    _update_common_reap_hope_stats(
        reap_acc, n_tok, topk_w, topk_idx, vis_mask,
        freq_loc, ean_loc, wean_loc, wfreq_loc, max_abs_loc, max_sig_loc, vp_freq_loc, vp_wean_loc,
    )
    cache = reap_acc.rco_cache
    if cache is None or cache.filled >= cache.max_tokens:
        return

    sel = np.arange(0, n_tok, reap_acc.rco_stride)
    take = min(sel.size, cache.max_tokens - cache.filled)
    if take <= 0:
        return
    sel = sel[:take]
    m = cache.top_m
    probs_sub = full_probs[sel]
    part_i = np.argpartition(-probs_sub, kth=m - 1, axis=-1)[:, :m]
    part_v = np.take_along_axis(probs_sub, part_i, axis=-1)
    order = np.lexsort((part_i, -part_v), axis=-1)
    topm_idx = np.take_along_axis(part_i, order, axis=-1)
    topm_prob = np.take_along_axis(part_v, order, axis=-1)

    inter = moe_w.inter_dim
    e_outs = np.zeros((take, m, moe_w.hidden_dim), dtype=np.float32)
    x_sub = x_fp16_f32[sel]
    for e_id in np.unique(topm_idx):
        t_pos, m_pos = np.where(topm_idx == e_id)
        gu = x_sub[t_pos] @ moe_w.gate_up[e_id].astype(np.float32).T
        act = _silu_np_f32(gu[:, :inter]) * gu[:, inter:]
        dn = act.astype(np.float16).astype(np.float32) @ moe_w.down[e_id].astype(np.float32).T
        e_outs[t_pos, m_pos] = dn

    d_sub = routed_out[sel]
    c0, c1 = cache.filled, cache.filled + take
    cache.idx[c0:c1] = topm_idx.astype(np.int16)
    cache.probs[c0:c1] = topm_prob.astype(np.float32)
    cache.gram[c0:c1] = np.einsum("tmd,tnd->tmn", e_outs, e_outs, optimize=True).astype(np.float32)
    cache.target_dot[c0:c1] = np.einsum("tmd,td->tm", e_outs, d_sub, optimize=True).astype(np.float32)
    cache.target_norm2[c0:c1] = np.sum(d_sub * d_sub, axis=-1).astype(np.float32)
    cache.filled = c1


def _commit_reap_hope_rco_cupy_or_cpu(
    reap_acc: ReapHopeRcoAccumulator,
    n_tok: int,
    x_f32: np.ndarray,
    xg_fp16: Any,
    moe_w: MoELayerWeights,
    topk_w: np.ndarray,
    topk_idx: np.ndarray,
    full_probs: np.ndarray,
    routed_out: np.ndarray,
    vis_mask: Optional[np.ndarray],
    freq_loc: np.ndarray,
    ean_loc: np.ndarray,
    wean_loc: np.ndarray,
    wfreq_loc: np.ndarray,
    max_abs_loc: np.ndarray,
    max_sig_loc: np.ndarray,
    vp_freq_loc: Optional[np.ndarray],
    vp_wean_loc: Optional[np.ndarray],
) -> None:
    _update_common_reap_hope_stats(
        reap_acc, n_tok, topk_w, topk_idx, vis_mask,
        freq_loc, ean_loc, wean_loc, wfreq_loc, max_abs_loc, max_sig_loc, vp_freq_loc, vp_wean_loc,
    )
    cache = reap_acc.rco_cache
    if cache is None or cache.filled >= cache.max_tokens:
        return

    cp = _get_cupy()
    sel = np.arange(0, n_tok, reap_acc.rco_stride)
    take = min(sel.size, cache.max_tokens - cache.filled)
    if take <= 0:
        return
    sel = sel[:take]
    m = cache.top_m
    probs_sub = full_probs[sel]
    part_i = np.argpartition(-probs_sub, kth=m - 1, axis=-1)[:, :m]
    part_v = np.take_along_axis(probs_sub, part_i, axis=-1)
    order = np.lexsort((part_i, -part_v), axis=-1)
    topm_idx = np.take_along_axis(part_i, order, axis=-1)
    topm_prob = np.take_along_axis(part_v, order, axis=-1)

    inter = moe_w.inter_dim
    x_sub_g = xg_fp16[cp.asarray(sel)]
    e_outs_g = cp.zeros((take, m, moe_w.hidden_dim), dtype=cp.float32)
    flat_m = topm_idx.ravel()
    perm_m = np.argsort(flat_m, kind="mergesort")
    e_sorted_m = flat_m[perm_m]
    t_sorted_m = (perm_m // m).astype(np.int32)
    s_sorted_m = (perm_m % m).astype(np.int32)
    uniq_m, starts_m, counts_m = np.unique(e_sorted_m, return_index=True, return_counts=True)
    t_sorted_mg = cp.asarray(t_sorted_m)
    s_sorted_mg = cp.asarray(s_sorted_m)
    x_sub_sorted_g = x_sub_g[t_sorted_mg]
    for iu in range(uniq_m.size):
        e_id = int(uniq_m[iu])
        so = int(starts_m[iu])
        eo = so + int(counts_m[iu])
        gu = cp.matmul(x_sub_sorted_g[so:eo], moe_w.gate_up[e_id].T, dtype=cp.float32)
        gp = gu[:, :inter]
        up = gu[:, inter:]
        act = (gp / (1.0 + cp.exp(-gp))) * up
        dn = cp.matmul(act.astype(cp.float16), moe_w.down[e_id].T, dtype=cp.float32)
        e_outs_g[t_sorted_mg[so:eo], s_sorted_mg[so:eo]] = dn
    del t_sorted_mg, s_sorted_mg, x_sub_sorted_g

    d_sub_g = cp.asarray(routed_out[sel], dtype=cp.float32)
    gram_g = cp.matmul(e_outs_g, cp.swapaxes(e_outs_g, -1, -2))
    tdot_g = cp.sum(e_outs_g * d_sub_g[:, None, :], axis=-1)
    tnorm_g = cp.sum(d_sub_g * d_sub_g, axis=-1)

    c0, c1 = cache.filled, cache.filled + take
    cache.idx[c0:c1] = topm_idx.astype(np.int16)
    cache.probs[c0:c1] = topm_prob.astype(np.float32)
    cache.gram[c0:c1] = cp.asnumpy(gram_g)
    cache.target_dot[c0:c1] = cp.asnumpy(tdot_g)
    cache.target_norm2[c0:c1] = cp.asnumpy(tnorm_g)
    cache.filled = c1
    del x_sub_g, e_outs_g, d_sub_g, gram_g, tdot_g, tnorm_g


def verify_moe_backend_vs_fp64(
    backend: str = "cpu",
    n_tokens: int = 64,
    num_experts: int = 32,
    top_k: int = 4,
    hidden_dim: int = 128,
    inter_dim: int = 64,
    seed: int = 42,
) -> Dict[str, Any]:
    """Compare full routed+shared MoE forward against exact numpy.float64 reference."""
    rng = np.random.default_rng(seed)
    x_fp16 = (rng.standard_normal((n_tokens, hidden_dim)) * 0.1).astype(np.float16)
    gate_w = (rng.standard_normal((num_experts, hidden_dim)) * 0.05).astype(np.float32)
    gu_fp16 = (rng.standard_normal((num_experts, 2 * inter_dim, hidden_dim)) * 0.03).astype(np.float16)
    dn_fp16 = (rng.standard_normal((num_experts, hidden_dim, inter_dim)) * 0.03).astype(np.float16)
    sh_g = (rng.standard_normal((inter_dim, hidden_dim)) * 0.03).astype(np.float16)
    sh_u = (rng.standard_normal((inter_dim, hidden_dim)) * 0.03).astype(np.float16)
    sh_d = (rng.standard_normal((hidden_dim, inter_dim)) * 0.03).astype(np.float16)
    sh_inp = (rng.standard_normal((1, hidden_dim)) * 0.05).astype(np.float32)

    # Exact float64 reference
    x64 = x_fp16.astype(np.float64)
    logits64 = x64 @ gate_w.astype(np.float64).T
    logits64 -= logits64.max(axis=-1, keepdims=True)
    probs64 = np.exp(logits64) / np.exp(logits64).sum(axis=-1, keepdims=True)
    idx64 = np.argsort(-probs64, axis=-1)[:, :top_k]
    w64 = np.take_along_axis(probs64, idx64, axis=-1)
    w64 /= w64.sum(axis=-1, keepdims=True)

    routed64 = np.zeros((n_tokens, hidden_dim), dtype=np.float64)
    for t in range(n_tokens):
        for s in range(top_k):
            e = int(idx64[t, s])
            gu64 = x64[t] @ gu_fp16[e].astype(np.float64).T
            g64, u64 = gu64[:inter_dim], gu64[inter_dim:]
            act64 = (g64 / (1.0 + np.exp(-g64))) * u64
            routed64[t] += w64[t, s] * (act64 @ dn_fp16[e].astype(np.float64).T)

    sh_g64 = x64 @ sh_g.astype(np.float64).T
    sh_u64 = x64 @ sh_u.astype(np.float64).T
    sh_act64 = (sh_g64 / (1.0 + np.exp(-sh_g64))) * sh_u64
    sh_sig64 = 1.0 / (1.0 + np.exp(-(x64 @ sh_inp.astype(np.float64).T)))
    ref64 = routed64 + sh_sig64 * (sh_act64 @ sh_d.astype(np.float64).T)

    moe_w = MoELayerWeights(
        gate_weight_f32=gate_w,
        gate_up_fp16=gu_fp16,
        down_fp16=dn_fp16,
        sh_gate_fp16=sh_g,
        sh_up_fp16=sh_u,
        sh_down_fp16=sh_d,
        sh_inp_gate_f32=sh_inp,
        top_k=top_k,
        norm_topk_prob=True,
        backend=backend,
    )
    try:
        out_t = forward_moe_v2(moe_w, torch.from_numpy(x_fp16.astype(np.float32)))
        out64 = out_t.numpy().astype(np.float64)
    finally:
        moe_w.close()

    rel_err = float(np.linalg.norm(out64 - ref64) / np.linalg.norm(ref64))
    return {"backend": backend, "rel_l2_error": rel_err, "passed": rel_err < 1e-3}


_GDN_RECURRENT_KERNEL_SRC = r"""
extern "C" __global__ void gdn_recurrent_fwd_f32(
    const float* __restrict__ q,
    const float* __restrict__ k,
    const float* __restrict__ v,
    const float* __restrict__ g,
    const float* __restrict__ beta,
    float* __restrict__ out,
    const int S,
    const int H
) {
    const int h = blockIdx.x;
    const int dv = threadIdx.x;
    if (h >= H || dv >= 128) return;

    __shared__ float sh_q[128];
    __shared__ float sh_k[128];
    __shared__ float sh_gb[2];

    float state[128];
    #pragma unroll
    for (int dk = 0; dk < 128; ++dk) {
        state[dk] = 0.0f;
    }

    for (int t = 0; t < S; ++t) {
        const int base_vec = (t * H + h) * 128;
        sh_q[dv] = q[base_vec + dv];
        sh_k[dv] = k[base_vec + dv];
        if (dv == 0) {
            const int base_sc = t * H + h;
            sh_gb[0] = expf(g[base_sc]);
            sh_gb[1] = beta[base_sc];
        }
        __syncthreads();

        const float decay = sh_gb[0];
        const float b_val = sh_gb[1];
        const float v_val = v[base_vec + dv];

        float kv_mem = 0.0f;
        #pragma unroll 8
        for (int dk = 0; dk < 128; ++dk) {
            float s_dk = state[dk] * decay;
            state[dk] = s_dk;
            kv_mem += s_dk * sh_k[dk];
        }

        const float delta = (v_val - kv_mem) * b_val;

        float o_val = 0.0f;
        #pragma unroll 8
        for (int dk = 0; dk < 128; ++dk) {
            float s_dk = state[dk] + sh_k[dk] * delta;
            state[dk] = s_dk;
            o_val += s_dk * sh_q[dk];
        }

        out[base_vec + dv] = o_val;
        __syncthreads();
    }
}
"""

_GDN_KERNEL_CACHE: Any = None


def _get_gdn_raw_kernel() -> Any:
    global _GDN_KERNEL_CACHE
    if _GDN_KERNEL_CACHE is None:
        cp = _get_cupy()
        _GDN_KERNEL_CACHE = cp.RawKernel(_GDN_RECURRENT_KERNEL_SRC, "gdn_recurrent_fwd_f32")
    return _GDN_KERNEL_CACHE


class CuPyGatedDeltaNetWrapper(nn.Module):
    """Exact CuPy GPU accelerator for Qwen4ExpTextGatedDeltaNet (when dk == dv == 128).

    Keeps the entire linear-attention step (projections, causal conv1d+SiLU, L2 norm,
    FP32 recurrent DeltaNet state update, gated RMSNorm, and output projection) on GPU,
    while still honoring any forward pre-hooks attached to `orig.out_proj` (imatrix).
    """

    def __init__(self, orig: nn.Module, text_cfg: Any) -> None:
        super().__init__()
        self.orig = orig
        self.nk = int(text_cfg.linear_num_key_heads)
        self.nv = int(text_cfg.linear_num_value_heads)
        self.dk = int(text_cfg.linear_key_head_dim)
        self.dv = int(text_cfg.linear_value_head_dim)
        self.can_use_cuda = (self.dk == 128) and (self.dv == 128) and (self.nv % self.nk == 0)

        self._gpu_arrays: Dict[str, Any] = {}
        if self.can_use_cuda:
            cp = _get_cupy()
            self._gpu_arrays["w_qkv"] = cp.asarray(orig.in_proj_qkv.weight.detach().to(torch.float16).cpu().numpy())
            self._gpu_arrays["w_z"] = cp.asarray(orig.in_proj_z.weight.detach().to(torch.float16).cpu().numpy())
            self._gpu_arrays["w_b"] = cp.asarray(orig.in_proj_b.weight.detach().to(torch.float32).cpu().numpy())
            self._gpu_arrays["w_a"] = cp.asarray(orig.in_proj_a.weight.detach().to(torch.float32).cpu().numpy())
            self._gpu_arrays["w_out"] = cp.asarray(orig.out_proj.weight.detach().to(torch.float16).cpu().numpy())
            # conv1d.weight: [C, 1, K] -> [K, C] float32
            conv_w = orig.conv1d.weight.detach().to(torch.float32).cpu().numpy()[:, 0, :].T.copy()
            self._gpu_arrays["conv_w"] = cp.asarray(conv_w)
            self._gpu_arrays["conv_b"] = (
                cp.asarray(orig.conv1d.bias.detach().to(torch.float32).cpu().numpy())
                if orig.conv1d.bias is not None
                else None
            )
            self._gpu_arrays["neg_exp_a"] = cp.asarray(
                (-orig.A_log.detach().to(torch.float32).exp()).cpu().numpy()
            )
            self._gpu_arrays["dt_bias"] = cp.asarray(orig.dt_bias.detach().to(torch.float32).cpu().numpy())
            self._gpu_arrays["norm_w"] = cp.asarray(orig.norm.weight.detach().to(torch.float32).cpu().numpy())
            self.norm_eps = float(getattr(orig.norm, "variance_epsilon", 1e-6))
            self.conv_k = int(conv_w.shape[0])

    @torch.no_grad()
    def forward(
        self,
        hidden_states: torch.Tensor,
        cache_params: Any = None,
        attention_mask: Optional[torch.Tensor] = None,
        **kwargs: Any,
    ) -> torch.Tensor:
        if not self.can_use_cuda or cache_params is not None or attention_mask is not None or hidden_states.shape[0] != 1:
            return self.orig(hidden_states, cache_params=cache_params, attention_mask=attention_mask, **kwargs)

        cp = _get_cupy()
        in_dtype = hidden_states.dtype
        bsz, seq_len, h_dim = hidden_states.shape
        x_np = hidden_states.detach().to(torch.float32).cpu().numpy().reshape(seq_len, h_dim)
        xg_f32 = cp.asarray(x_np)
        xg_fp16 = xg_f32.astype(cp.float16)

        ga = self._gpu_arrays
        qkv = cp.matmul(xg_fp16, ga["w_qkv"].T, dtype=cp.float32)  # [S, C]
        z = cp.matmul(xg_fp16, ga["w_z"].T, dtype=cp.float32).reshape(seq_len, self.nv, self.dv)
        b_raw = cp.matmul(xg_f32, ga["w_b"].T)
        b = 1.0 / (1.0 + cp.exp(-cp.clip(b_raw, -80.0, 80.0)))  # [S, nv]
        a_biased = cp.matmul(xg_f32, ga["w_a"].T) + ga["dt_bias"][None, :]
        # Stable softplus(x) = max(x, 0) + log1p(exp(-|x|))
        sp = cp.maximum(a_biased, 0.0) + cp.log1p(cp.exp(-cp.abs(a_biased)))
        g = sp * ga["neg_exp_a"][None, :]  # [S, nv]

        # Depthwise causal conv1d + SiLU
        pad = self.conv_k - 1
        qkv_pad = cp.pad(qkv, ((pad, 0), (0, 0))) if pad > 0 else qkv
        conv_acc = cp.zeros_like(qkv)
        conv_w = ga["conv_w"]
        for tap in range(self.conv_k):
            conv_acc += qkv_pad[tap : tap + seq_len] * conv_w[tap][None, :]
        if ga["conv_b"] is not None:
            conv_acc += ga["conv_b"][None, :]
        conv_silu = conv_acc / (1.0 + cp.exp(-cp.clip(conv_acc, -80.0, 80.0)))

        qk_dim = self.nk * self.dk
        q = conv_silu[:, :qk_dim].reshape(seq_len, self.nk, self.dk)
        k = conv_silu[:, qk_dim : 2 * qk_dim].reshape(seq_len, self.nk, self.dk)
        v = conv_silu[:, 2 * qk_dim :].reshape(seq_len, self.nv, self.dv)

        q = (q / cp.sqrt(cp.sum(q * q, axis=-1, keepdims=True) + 1e-6)) * (self.dk**-0.5)
        k = k / cp.sqrt(cp.sum(k * k, axis=-1, keepdims=True) + 1e-6)

        rep = self.nv // self.nk
        if rep > 1:
            q = cp.broadcast_to(q[:, :, None, :], (seq_len, self.nk, rep, self.dk)).reshape(seq_len, self.nv, self.dk)
            k = cp.broadcast_to(k[:, :, None, :], (seq_len, self.nk, rep, self.dk)).reshape(seq_len, self.nv, self.dk)

        q_c = cp.ascontiguousarray(q, dtype=cp.float32)
        k_c = cp.ascontiguousarray(k, dtype=cp.float32)
        v_c = cp.ascontiguousarray(v, dtype=cp.float32)
        g_c = cp.ascontiguousarray(g, dtype=cp.float32)
        b_c = cp.ascontiguousarray(b, dtype=cp.float32)
        out_g = cp.empty((seq_len, self.nv, self.dv), dtype=cp.float32)

        kern = _get_gdn_raw_kernel()
        kern(
            (self.nv,),
            (128,),
            (q_c, k_c, v_c, g_c, b_c, out_g, np.int32(seq_len), np.int32(self.nv)),
        )

        # RMSNormGated: rmsnorm(out_g) * norm_w * sigmoid(z)
        rms = out_g / cp.sqrt(cp.mean(out_g * out_g, axis=-1, keepdims=True) + self.norm_eps)
        sig_z = 1.0 / (1.0 + cp.exp(-cp.clip(z, -80.0, 80.0)))
        normed_flat = (rms * ga["norm_w"][None, None, :] * sig_z).reshape(seq_len, self.nv * self.dv)

        if self.orig.out_proj._forward_pre_hooks or self.orig.out_proj._forward_hooks:
            t_mid = torch.from_numpy(cp.asnumpy(normed_flat)).view(bsz, seq_len, -1).to(in_dtype)
            res = self.orig.out_proj(t_mid)
        else:
            y_g = cp.matmul(normed_flat.astype(cp.float16), ga["w_out"].T, dtype=cp.float32)
            res = torch.from_numpy(cp.asnumpy(y_g)).view(bsz, seq_len, h_dim).to(in_dtype)

        del xg_f32, xg_fp16, qkv, z, b_raw, b, a_biased, sp, g, qkv_pad, conv_acc, conv_silu
        del q, k, v, q_c, k_c, v_c, g_c, b_c, out_g, rms, sig_z, normed_flat
        return res

    @property
    def out_proj(self) -> nn.Module:
        return self.orig.out_proj

    def close(self) -> None:
        self._gpu_arrays.clear()


class CuPyFastAttentionWrapper(nn.Module):
    """Exact CuPy GPU SDPA accelerator for Qwen4ExpTextAttention (QSA full_attention).

    Preserves HF `q_norm`, `k_norm`, `apply_rotary_pos_emb` (exact M-RoPE), `indexer`,
    and any `o_proj` forward pre-hooks, while executing the O(S^2) GQA attention matmul
    and softmax on GPU via CuPy cuBLAS.
    """

    def __init__(self, orig: nn.Module, text_cfg: Any) -> None:
        super().__init__()
        self.orig = orig
        self.nh = int(text_cfg.num_attention_heads)
        self.nkv = int(text_cfg.num_key_value_heads)
        self.hd = int(text_cfg.head_dim)
        self.scale = float(self.hd**-0.5)

    @property
    def o_proj(self) -> nn.Module:
        return self.orig.o_proj

    @torch.no_grad()
    def forward(
        self,
        hidden_states: torch.Tensor,
        position_embeddings: Tuple[torch.Tensor, torch.Tensor],
        attention_mask: Optional[torch.Tensor] = None,
        past_key_values: Any = None,
        **kwargs: Any,
    ) -> Tuple[torch.Tensor, None]:
        if past_key_values is not None or hidden_states.shape[0] != 1:
            return self.orig(
                hidden_states,
                position_embeddings,
                attention_mask=attention_mask,
                past_key_values=past_key_values,
                **kwargs,
            )

        from transformers.models.qwen4_exp.modeling_qwen4_exp import apply_rotary_pos_emb

        cp = _get_cupy()
        in_dtype = hidden_states.dtype
        bsz, seq_len, _ = hidden_states.shape

        qg = self.orig.q_proj(hidden_states).view(bsz, seq_len, self.nh, 2 * self.hd)
        q, gate = torch.chunk(qg, 2, dim=-1)
        q = self.orig.q_norm(q).transpose(1, 2)  # [1, nh, S, hd]
        k = self.orig.k_norm(self.orig.k_proj(hidden_states).view(bsz, seq_len, self.nkv, self.hd)).transpose(1, 2)
        v = self.orig.v_proj(hidden_states).view(bsz, seq_len, self.nkv, self.hd).transpose(1, 2)

        cos, sin = position_embeddings
        q, k = apply_rotary_pos_emb(q, k, cos, sin)

        if hasattr(self.orig, "indexer") and self.orig.indexer is not None:
            sel_mask = self.orig.indexer(hidden_states, position_embeddings, attention_mask=attention_mask)
        else:
            sel_mask = attention_mask

        # Upload Q, K, V to GPU for O(S^2) masked SDPA
        q_g = cp.asarray(q[0].to(torch.float16).cpu().numpy())  # [nh, S, hd]
        k_g = cp.asarray(k[0].to(torch.float16).cpu().numpy())  # [nkv, S, hd]
        v_g = cp.asarray(v[0].to(torch.float16).cpu().numpy())  # [nkv, S, hd]
        rep = self.nh // self.nkv
        if rep > 1:
            k_g = cp.ascontiguousarray(
                cp.broadcast_to(k_g[:, None, :, :], (self.nkv, rep, seq_len, self.hd)).reshape(self.nh, seq_len, self.hd)
            )
            v_g = cp.ascontiguousarray(
                cp.broadcast_to(v_g[:, None, :, :], (self.nkv, rep, seq_len, self.hd)).reshape(self.nh, seq_len, self.hd)
            )

        scores_g = cp.matmul(q_g, cp.swapaxes(k_g, -1, -2), dtype=cp.float32) * self.scale  # [nh, S, S]
        if sel_mask is not None:
            if sel_mask.dtype == torch.bool:
                m_np = sel_mask[0].cpu().numpy()  # [1 or nh, S, S]
                m_g = cp.asarray(m_np)
                scores_g = cp.where(m_g, scores_g, cp.float32(-3.4e38))
                del m_g
            else:
                m_g = cp.asarray(sel_mask[0].to(torch.float32).cpu().numpy())
                scores_g = scores_g + m_g
                del m_g

        s_max = cp.max(scores_g, axis=-1, keepdims=True)
        exp_s = cp.exp(scores_g - s_max)
        probs_g = (exp_s / cp.maximum(cp.sum(exp_s, axis=-1, keepdims=True), 1e-20)).astype(cp.float16)
        attn_g = cp.matmul(probs_g, v_g, dtype=cp.float32)  # [nh, S, hd]
        attn_np = cp.asnumpy(cp.transpose(attn_g, (1, 0, 2))).reshape(bsz, seq_len, self.nh * self.hd)
        del q_g, k_g, v_g, scores_g, s_max, exp_s, probs_g, attn_g

        attn_t = torch.from_numpy(attn_np).to(torch.float32) * torch.sigmoid(
            gate.to(torch.float32).reshape(bsz, seq_len, self.nh * self.hd)
        )
        out = self.orig.o_proj(attn_t.to(in_dtype))
        return out, None


def verify_cupy_gdn_and_attn_parity(text_cfg: Any, seq_len: int = 48) -> Dict[str, float]:
    """Self-test CuPyGatedDeltaNetWrapper and CuPyFastAttentionWrapper vs HF CPU reference."""
    from transformers.models.qwen4_exp.modeling_qwen4_exp import (
        Qwen4ExpTextAttention,
        Qwen4ExpTextGatedDeltaNet,
        Qwen4ExpTextRotaryEmbedding,
    )
    from scripts.v2.common_io import QSAIndexerWrapper

    torch.manual_seed(1234)
    gdn = Qwen4ExpTextGatedDeltaNet(text_cfg, layer_idx=0).to(torch.float32).eval()
    for p in gdn.parameters():
        torch.nn.init.normal_(p, mean=0.0, std=0.04)
    x = torch.randn(1, seq_len, int(text_cfg.hidden_size), dtype=torch.float16).to(torch.float32)
    with torch.no_grad():
        y_gdn_ref = gdn(x)
        wrap_gdn = CuPyGatedDeltaNetWrapper(gdn, text_cfg)
        y_gdn_cu = wrap_gdn(x)
        wrap_gdn.close()
    gdn_rel = float(torch.norm(y_gdn_ref - y_gdn_cu) / torch.norm(y_gdn_ref).clamp_min(1e-12))

    attn = Qwen4ExpTextAttention(text_cfg, layer_idx=3).to(torch.float32).eval()
    for p in attn.parameters():
        torch.nn.init.normal_(p, mean=0.0, std=0.04)
    attn.indexer = QSAIndexerWrapper(attn.indexer)
    rot = Qwen4ExpTextRotaryEmbedding(config=text_cfg)
    pos = torch.arange(seq_len).unsqueeze(0).expand(3, 1, -1)
    cos, sin = rot(x, pos)
    mask = torch.arange(seq_len)[None, None, None, :] <= torch.arange(seq_len)[None, None, :, None]
    with torch.no_grad():
        y_at_ref, _ = attn(x, (cos, sin), attention_mask=mask)
        patch_at = CuPyLinearPatch(attn, enabled=True)
        wrap_at = CuPyFastAttentionWrapper(attn, text_cfg)
        y_at_cu, _ = wrap_at(x, (cos, sin), attention_mask=mask)
        patch_at.close()
    attn_rel = float(
        torch.norm(y_at_ref.float() - y_at_cu.float()) / torch.norm(y_at_ref.float()).clamp_min(1e-12)
    )
    free_cupy_pools()
    if gdn_rel > 2e-3 or attn_rel > 2e-3:
        raise RuntimeError(f"CuPy layer kernel parity check failed: gdn_rel={gdn_rel:.4e}, attn_rel={attn_rel:.4e}")
    return {"gdn_rel_l2": round(gdn_rel, 6), "attn_rel_l2": round(attn_rel, 6)}
