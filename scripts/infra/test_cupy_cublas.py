#!/usr/bin/env python3
"""CuPy cuBLAS fp16->fp32 MoE expert forward test vs NumPy fp64 reference (OPUS §1.D6).

Must ONLY be executed under scripts/infra/gpu_run.py AFTER @coordinator grants GPU_TOKEN.
Verifies relative L2 error < 1e-3 on a Qwen3.8-Flash-Next single-expert MLP block
(hidden=2560, intermediate=640, SwiGLU gate/up/down).
"""

from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("CUDA_PATH", "/opt/cuda")

import cupy as cp  # noqa: E402
import numpy as np  # noqa: E402


def silu_fp64(x: np.ndarray) -> np.ndarray:
    return x / (1.0 + np.exp(-x))


def main() -> int:
    t0 = time.perf_counter()
    rng = np.random.default_rng(42)
    n_tokens = 256
    d_model = 2560
    d_inter = 640

    # Generate realistic-scale activations & weights in fp16, then cast to fp64 for exact reference
    x_fp16 = (rng.standard_normal((n_tokens, d_model)) * 0.1).astype(np.float16)
    w_gate_fp16 = (rng.standard_normal((d_inter, d_model)) * 0.02).astype(np.float16)
    w_up_fp16 = (rng.standard_normal((d_inter, d_model)) * 0.02).astype(np.float16)
    w_down_fp16 = (rng.standard_normal((d_model, d_inter)) * 0.02).astype(np.float16)

    # NumPy fp64 reference
    x_64 = x_fp16.astype(np.float64)
    gate_64 = x_64 @ w_gate_fp16.astype(np.float64).T
    up_64 = x_64 @ w_up_fp16.astype(np.float64).T
    act_64 = silu_fp64(gate_64) * up_64
    out_64 = act_64 @ w_down_fp16.astype(np.float64).T

    # CuPy GPU fp16 inputs with fp32 accumulation (cuBLAS GEMMEx / float32 output)
    x_gpu = cp.asarray(x_fp16)
    wg_gpu = cp.asarray(w_gate_fp16)
    wu_gpu = cp.asarray(w_up_fp16)
    wd_gpu = cp.asarray(w_down_fp16)

    gate_gpu = cp.matmul(x_gpu, wg_gpu.T, dtype=cp.float32)
    up_gpu = cp.matmul(x_gpu, wu_gpu.T, dtype=cp.float32)
    act_gpu = (gate_gpu / (1.0 + cp.exp(-gate_gpu))) * up_gpu
    out_gpu = cp.matmul(act_gpu.astype(cp.float16), wd_gpu.T, dtype=cp.float32)
    cp.cuda.Stream.null.synchronize()

    out_32 = cp.asnumpy(out_gpu).astype(np.float64)
    rel_l2 = float(np.linalg.norm(out_32 - out_64) / np.linalg.norm(out_64))
    max_abs = float(np.max(np.abs(out_32 - out_64)))
    elapsed = round(time.perf_counter() - t0, 4)

    passed = rel_l2 < 1e-3
    result = {
        "passed": passed,
        "rel_l2_error": rel_l2,
        "threshold": 1e-3,
        "max_abs_error": max_abs,
        "shapes": {"x": [n_tokens, d_model], "inter": d_inter},
        "cupy_version": cp.__version__,
        "cuda_runtime_version": int(cp.cuda.runtime.runtimeGetVersion()),
        "elapsed_sec": elapsed,
    }
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
