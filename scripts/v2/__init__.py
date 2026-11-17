"""SmartLLM v2 Prune / Heal / Clean-Room GSQ Q2_0 / Streaming GGUF Pipeline (WP-C1).

Clean-room implementation for CachyOS Linux (<12 GiB VRAM, Zero-Swap invariant).
License attributions:
- REAP saliency & observer concepts: CerebrasResearch/reap (Apache-2.0)
- HOPE redundancy-penalized quadratic formulation: awslabs/HOPE, arXiv:2603.18916 (Apache-2.0)
- MoESQ Hessian-weighted MoE quantization math: MoESQ (Apache-2.0)
- GGUF / Q2_0 block layout & traits: ggml-org/llama.cpp & gguf-py (MIT)
Zero code derived from unlicensed gptq-gguf-toolkit.
"""

from __future__ import annotations

__all__ = [
    "common_io",
    "cupy_moe_backend",
    "expert_selectors",
    "healing_c3",
    "gsq_q2_0",
    "assemble_gguf",
    "prequant_gate",
    "model_runner",
    "wave2_shootout",
    "wave3_full_run",
]
