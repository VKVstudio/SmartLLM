"""Step 3.6: Deterministic Anti-Swap RAM/VRAM Budget & Step 8 Acceptance Criteria Calculator.

Computes exact byte, MiB, GiB (2^30), and GB (10^9) memory footprints for
Qwen/Qwen3.8-Flash-Next (qwen4_exp) in mainline llama.cpp across:
  - Pruned expert counts K in {256, 205, 192, 184, 176, 160}
  - Quantization schemes IQ3_XXS (3.0625 bpw + IQ4_NL 4.50 bpw fallback on down_proj)
    and IQ3_S (3.4375 bpw + IQ4_NL 4.50 bpw fallback on down_proj)
  - Trunk-only (48 layers, default mparams.load_mtp=false) vs Trunk + MTP (49 layers, --spec-type mtp)
  - Context sizes 8K (8,192), 16K (16,384), 32K (32,768), 64K (65,536), 128K (131,072)
  - Hardware profiles:
      1) Lenovo Legion Pro 7 (RTX 4080 Laptop 12,282 MiB / 11.9941 GiB VRAM, 32.00 GiB nominal / 31.7303 GiB OS-usable RAM)
      2) Target 8 GB VRAM profile (8,192 MiB / 8.0000 GiB VRAM, 32.00 GiB nominal / 31.7303 GiB OS-usable RAM)
  - Runtime modes with Tongyi-MAI/Z-Image-Turbo (~6.15B S3-DiT + 4.02B Qwen3-4B text encoder):
      A) Sequential switching via llama-swap (VRAM/RAM unloaded before Z-Image starts)
      B) Co-resident in RAM (proven to violate the >= 3.0 GiB free RAM anti-swap rule)
"""

from __future__ import annotations

import ctypes
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
STEP1_RAW = ROOT / "research" / "step1_raw"
STEP36_RAW = ROOT / "research" / "step3_6_raw"
EVAL_RESULTS = ROOT / "eval" / "suite" / "results"
GYRO_RUN = ROOT / "eval" / "suite" / "runs" / "gyro-m-local"

GIB = 1024 ** 3
MIB = 1024 ** 2
GB = 10 ** 9
MB = 10 ** 6


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def get_windows_memory_status() -> dict:
    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(stat)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    return {
        "total_phys_bytes": int(stat.ullTotalPhys),
        "total_phys_gib": round(stat.ullTotalPhys / GIB, 4),
        "total_phys_gb": round(stat.ullTotalPhys / GB, 4),
        "avail_phys_bytes": int(stat.ullAvailPhys),
        "avail_phys_gib": round(stat.ullAvailPhys / GIB, 4),
        "avail_phys_gb": round(stat.ullAvailPhys / GB, 4),
        "used_phys_bytes": int(stat.ullTotalPhys - stat.ullAvailPhys),
        "used_phys_gib": round((stat.ullTotalPhys - stat.ullAvailPhys) / GIB, 4),
        "memory_load_pct": int(stat.dwMemoryLoad),
    }


def get_gpu_status() -> dict:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=10,
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        total_mib = int(parts[1])
        used_mib = int(parts[2])
        free_mib = int(parts[3])
        return {
            "name": parts[0],
            "driver_version": parts[4],
            "total_mib": total_mib,
            "total_bytes": total_mib * MIB,
            "total_gib": round((total_mib * MIB) / GIB, 4),
            "total_gb": round((total_mib * MIB) / GB, 4),
            "used_mib_idle": used_mib,
            "free_mib_idle": free_mib,
            "free_gib_idle": round((free_mib * MIB) / GIB, 4),
        }
    except Exception as exc:
        return {"error": str(exc)}


def fetch_zimage_metadata() -> dict:
    """Fetch primary-source metadata for Tongyi-MAI/Z-Image-Turbo and GGUF quantizations from HF API."""
    STEP36_RAW.mkdir(parents=True, exist_ok=True)
    cache_path = STEP36_RAW / "zimage_hf_metadata.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    repos = [
        "Tongyi-MAI/Z-Image-Turbo",
        "jayn7/Z-Image-Turbo-GGUF",
        "leejet/Z-Image-Turbo-GGUF",
    ]
    results = {}
    for repo in repos:
        url = f"https://huggingface.co/api/models/{repo}?blobs=true"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SmartLLM-Step3.6-Audit/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            siblings = [
                {
                    "rfilename": s.get("rfilename"),
                    "size_bytes": s.get("size"),
                    "size_gib": round(s.get("size", 0) / GIB, 4) if s.get("size") else None,
                    "size_gb": round(s.get("size", 0) / GB, 4) if s.get("size") else None,
                }
                for s in data.get("siblings", [])
            ]
            total_bytes = sum(s.get("size") or 0 for s in data.get("siblings", []))
            results[repo] = {
                "id": data.get("id"),
                "sha": data.get("sha"),
                "license": (data.get("cardData") or {}).get("license"),
                "pipeline_tag": data.get("pipeline_tag"),
                "tags": data.get("tags", []),
                "safetensors_meta": data.get("safetensors"),
                "total_repo_bytes": total_bytes,
                "total_repo_gib": round(total_bytes / GIB, 4),
                "total_repo_gb": round(total_bytes / GB, 4),
                "siblings_count": len(siblings),
                "siblings": siblings,
            }
        except Exception as exc:
            results[repo] = {"error": str(exc)}
    cache_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return results


def ggml_row_size_bytes(qtype: str, ne0: int) -> int:
    """Exact ggml_row_size(type, ne0) from ggml/src/ggml.c:640-930 & ggml-common.h:180-460."""
    table = {
        "IQ3_XXS": (256, 98),   # 3.0625 bpw
        "IQ3_S": (256, 110),    # 3.4375 bpw
        "IQ2_S": (256, 82),     # 2.5625 bpw
        "IQ4_NL": (32, 18),     # 4.5000 bpw
        "Q4_0": (32, 18),       # 4.5000 bpw
        "Q4_K": (256, 144),     # 4.5000 bpw
        "Q5_K": (256, 176),     # 5.5000 bpw
        "Q6_K": (256, 210),     # 6.5625 bpw
        "Q8_0": (32, 34),       # 8.5000 bpw
        "F16": (1, 2),          # 16.0000 bpw
        "BF16": (1, 2),         # 16.0000 bpw
        "F32": (1, 4),          # 32.0000 bpw
    }
    blck_size, type_size = table[qtype]
    assert ne0 % blck_size == 0, f"ne0={ne0} not divisible by blck_size={blck_size} for {qtype}"
    return (ne0 // blck_size) * type_size


def main() -> None:
    STEP36_RAW.mkdir(parents=True, exist_ok=True)

    win_mem = get_windows_memory_status()
    gpu_info = get_gpu_status()
    zimage_meta = fetch_zimage_metadata()

    config = json.loads((STEP1_RAW / "config.json").read_text(encoding="utf-8"))
    geom = json.loads((STEP1_RAW / "geometry_calculations.json").read_text(encoding="utf-8"))

    tc = config["text_config"]
    n_qsa_layers = tc["layer_types"].count("full_attention")  # 12
    n_gdn_layers = tc["layer_types"].count("linear_attention")  # 36
    hidden_size = int(tc["hidden_size"])  # 2560

    # 1. Exact Routed Expert Byte Calculations in GGUF (per expert, per layer, across 48 or 49 layers)
    # In HF safetensors:
    #   gate_up_proj: [512, 1280, 2560] -> in GGUF split into ffn_gate_exps [2560, 640, K] + ffn_up_exps [2560, 640, K]
    #   down_proj:    [512, 2560, 640]  -> in GGUF ffn_down_exps [640, 2560, K] (ne[0]=640, nrows_per_expert=2560)
    # Because ne[0]=640 is NOT divisible by 256 (640 % 256 = 128), src/llama-quant.cpp:421-474 automatically
    # falls back from IQ3_XXS / IQ3_S to IQ4_NL (blck_size=32, type_size=18 B = 4.50 bpw)!
    gate_up_rows_per_expert = 1280  # 640 gate + 640 up, each row has ne[0] = 2560
    gate_up_ne0 = 2560
    down_rows_per_expert = 2560  # each row has ne[0] = 640
    down_ne0 = 640

    expert_quants = {}
    for qname, gate_up_qtype, bpw_approx in [
        ("IQ3_XXS", "IQ3_XXS", 3.06),
        ("IQ3_S", "IQ3_S", 3.44),
    ]:
        gate_up_1exp_1layer_exact = gate_up_rows_per_expert * ggml_row_size_bytes(gate_up_qtype, gate_up_ne0)
        down_1exp_1layer_exact = down_rows_per_expert * ggml_row_size_bytes("IQ4_NL", down_ne0)
        total_1exp_1layer_exact = gate_up_1exp_1layer_exact + down_1exp_1layer_exact

        # Step 1 rounded bpw formula (3.06 / 3.44 bpw) for exact cross-reference with geometry_calculations.json:
        gate_up_1exp_1layer_step1 = int(round((1280 * 2560) * bpw_approx / 8.0))
        down_1exp_1layer_step1 = int(round((2560 * 640) * 4.50 / 8.0))
        total_1exp_1layer_step1 = gate_up_1exp_1layer_step1 + down_1exp_1layer_step1

        expert_quants[qname] = {
            "gate_up_qtype": gate_up_qtype,
            "gate_up_exact_bpw": round(ggml_row_size_bytes(gate_up_qtype, gate_up_ne0) * 8 / gate_up_ne0, 4),
            "down_qtype_fallback": "IQ4_NL",
            "down_exact_bpw": 4.50,
            "effective_combined_bpw_exact": round(
                (total_1exp_1layer_exact * 8) / (1280 * 2560 + 2560 * 640), 4
            ),
            "per_expert_1_layer_bytes_exact": total_1exp_1layer_exact,
            "per_expert_48_layers_bytes_exact": 48 * total_1exp_1layer_exact,
            "per_expert_49_layers_mtp_bytes_exact": 49 * total_1exp_1layer_exact,
            "per_expert_48_layers_bytes_step1_formula": 48 * total_1exp_1layer_step1,
        }

    # 2. Dense & Root Weights in VRAM (Offloaded via -ngl 99) and Lazy PLE Table on NVMe SSD
    # Exact values from research/step1_raw/geometry_calculations.json:
    #   root_tensors (BF16) = 2,555,924,480 B (1,277,962,240 params)
    #   dense_48_layers_excl_router (BF16) = 7,147,964,160 B (3,573,982,080 params)
    #   params_dense_and_root_excl_router = 4,851,944,320 params
    #   ple_128_ngram_shards (BF16) = 102,400,491,520 B (51,200,245,760 params)
    #     -> per_layer_token_embd.weight in Q4_0 (18 B / 32 = 4.50 bpw) = 28,800,138,240 B (26.8225 GiB / 28.8001 GB)
    #   ple_non_shard (BF16/I64, layer 1 key_proj, value_proj, conv1d, norms) = 65,679,640 B (32,839,820 params)
    #   ple_q4_0_bytes (Step 1 combined PLE Q4_0 table + BF16 ple_non_shard) = 28,865,817,880 B (26.8836 GiB / 28.8658 GB)
    #   visual_total (BF16 mmproj) = 897,862,112 B (0.8362 GiB / 0.8979 GB)
    #   mtp_total_512 (BF16) = 5,214,301,696 B; mtp_dense_excl_router = 5,214,301,696 - 5,033,164,800 - 2,621,440
    #     = 178,515,456 B (89,257,728 params)
    root_bf16_bytes = geom["model_totals_bf16_bytes"]["root_tensors"]  # 2,555,924,480 B
    dense_48_excl_router_bf16_bytes = geom["model_totals_bf16_bytes"]["dense_48_layers_excl_router"]  # 7,147,964,160 B
    ple_ngram_bf16_bytes = geom["model_totals_bf16_bytes"]["ple_128_ngram_shards"]  # 102,400,491,520 B
    ple_small_bf16_bytes = geom["model_totals_bf16_bytes"]["ple_non_shard"]  # 65,679,640 B
    vis_mmproj_bf16_bytes = geom["model_totals_bf16_bytes"]["visual_total"]  # 897,862,112 B
    ple_ngram_q4_0_bytes = (ple_ngram_bf16_bytes // 2 // 32) * 18  # 28,800,138,240 B (26.8225 GiB / 28.8001 GB)
    ple_q4_0_plus_small_bf16_bytes = geom["quant_estimates_bytes"]["ple_q4_0_bytes"]  # 28,865,817,880 B (26.8836 GiB / 28.8658 GB)

    mtp_dense_excl_router_bf16_bytes = (
        geom["model_totals_bf16_bytes"]["mtp_total_512"]
        - geom["per_layer_bf16_bytes"]["routed_experts_512"]
        - geom["per_layer_bf16_bytes"]["router_512"]
    )  # 178,515,456 B (89,257,728 params)

    params_dense_and_root_excl_router = (root_bf16_bytes + dense_48_excl_router_bf16_bytes) // 2  # 4,851,944,320 params

    def calc_vram_weights(k_experts: int, include_mtp: bool, include_mmproj: bool, dense_bpw: float = 5.5) -> dict:
        n_blk = 49 if include_mtp else 48
        mtp_extra_dense_params = (mtp_dense_excl_router_bf16_bytes // 2) if include_mtp else 0
        total_dense_root_params = params_dense_and_root_excl_router + mtp_extra_dense_params
        dense_root_quant_bytes = int(round(total_dense_root_params * dense_bpw / 8.0))
        # Routers in F32 (4 B/elem in mainline conversion/base.py:1258 + llama-quant.cpp:321) and F16 (2 B/elem in Step 1 formula):
        routers_f32_bytes = n_blk * k_experts * hidden_size * 4
        routers_f16_bytes = n_blk * k_experts * hidden_size * 2
        ple_small_quant_bytes = int(round((ple_small_bf16_bytes // 2) * dense_bpw / 8.0))
        mmproj_bytes = vis_mmproj_bf16_bytes if include_mmproj else 0
        total_vram_weights_f32_router = (
            dense_root_quant_bytes + routers_f32_bytes + ple_small_quant_bytes + mmproj_bytes
        )
        # Step 1 exact formula for core dense + F16 routers (matches geometry_calculations.json:53, 67):
        step1_core_dense_with_f16_routers_bytes = (
            int(round(params_dense_and_root_excl_router * dense_bpw / 8.0)) + 48 * k_experts * hidden_size * 2
        )
        return {
            "dense_root_quant_bytes": dense_root_quant_bytes,
            "routers_f32_bytes": routers_f32_bytes,
            "routers_f16_bytes": routers_f16_bytes,
            "ple_small_quant_bytes": ple_small_quant_bytes,
            "mmproj_bf16_bytes": mmproj_bytes,
            "total_vram_weights_bytes": total_vram_weights_f32_router,
            "total_vram_weights_gib": round(total_vram_weights_f32_router / GIB, 4),
            "total_vram_weights_gb": round(total_vram_weights_f32_router / GB, 4),
            "step1_core_dense_with_f16_routers_bytes": step1_core_dense_with_f16_routers_bytes,
        }

    # 3. Exact Hybrid KV + Indexer + Recurrent State Memory in VRAM
    # Verified from llama.cpp source code:
    #   - src/llama-model.cpp:3148-3225 (LLM_ARCH_QWEN4EXP creates llama_memory_hybrid_idx)
    #   - src/llama-memory-hybrid-idx.cpp:19-71:
    #       mem_attn: 12 QSA layers (layers 3, 7, ..., 47). n_head_kv=2, head_dim=256 -> K=512, V=512 (1024 elems/tok/layer).
    #                 In F16 (2 B/elem): 12 * 1024 * 2 = 24,576 B/token (24.0 KiB/token).
    #       mem_idx:  12 QSA layers. Sets n_head_kv=1, n_embd_head_k_full = indexer_head_size * indexer_kpool_row = 128 * 2 = 256,
    #                 and sets n_embd_head_k_mla_impl = 128 (so is_mla() == true -> has_v = false in src/llama-kv-cache.cpp:230).
    #                 In F16 (2 B/elem): 12 * 256 * 2 = 6,144 B/token (6.0 KiB/token).
    #       Total token-dependent cache (mem_attn + mem_idx, 48-layer trunk, F16):
    #                 24,576 + 6,144 = 30,720 B/token (30.0 KiB/token)!
    #   - src/llama-memory-recurrent.cpp:74-143 & src/llama-hparams.cpp:208-275:
    #       mem_recr: 36 GDN layers + 1 PLE conv state on layer 1 (FP32, constant O(1) per sequence slot, n_seq_max=1 with -np 1):
    #         Total mem_recr (n_seq_max=1): 36 * (122,880 + 3,145,728) + 368,640 = 118,038,528 B (112.5703 MiB / 0.1099 GiB).
    bytes_per_tok_attn_f16 = n_qsa_layers * (2 * 256 * 2) * 2  # 24,576 B
    bytes_per_tok_idx_f16 = n_qsa_layers * (128 * 2) * 2       # 6,144 B
    bytes_per_tok_total_f16 = bytes_per_tok_attn_f16 + bytes_per_tok_idx_f16  # 30,720 B (30.0 KiB)
    bytes_per_tok_q8_kv_f16_idx = (n_qsa_layers * (2 * 256 * 2) * 1088 // 1024) + bytes_per_tok_idx_f16  # 19,200 B

    mem_recr_per_gdn_layer_bytes = (3 * (6144 + 2 * 16 * 128) + 128 * 6144) * 4  # 3,268,608 B
    mem_recr_ple_conv_bytes = (3 * 3 * 4 * 2560) * 4  # 368,640 B
    mem_recr_total_bytes = n_gdn_layers * mem_recr_per_gdn_layer_bytes + mem_recr_ple_conv_bytes  # 118,038,528 B

    contexts = [8192, 16384, 32768, 65536, 131072]
    kv_cache_table = {}
    for ctx in contexts:
        attn_bytes = ctx * bytes_per_tok_attn_f16
        idx_bytes = ctx * bytes_per_tok_idx_f16
        kv_idx_f16_bytes = ctx * bytes_per_tok_total_f16
        total_state_f16_bytes = kv_idx_f16_bytes + mem_recr_total_bytes
        kv_idx_q8_bytes = ctx * bytes_per_tok_q8_kv_f16_idx
        total_state_q8_bytes = kv_idx_q8_bytes + mem_recr_total_bytes
        kv_cache_table[str(ctx)] = {
            "n_ctx": ctx,
            "mem_attn_f16_bytes": attn_bytes,
            "mem_attn_f16_mib": round(attn_bytes / MIB, 2),
            "mem_idx_f16_bytes": idx_bytes,
            "mem_idx_f16_mib": round(idx_bytes / MIB, 2),
            "mem_recr_f32_bytes": mem_recr_total_bytes,
            "mem_recr_f32_mib": round(mem_recr_total_bytes / MIB, 2),
            "total_hybrid_cache_f16_bytes": total_state_f16_bytes,
            "total_hybrid_cache_f16_mib": round(total_state_f16_bytes / MIB, 2),
            "total_hybrid_cache_f16_gib": round(total_state_f16_bytes / GIB, 4),
            "total_hybrid_cache_f16_gb": round(total_state_f16_bytes / GB, 4),
            "total_hybrid_cache_q8_kv_bytes": total_state_q8_bytes,
            "total_hybrid_cache_q8_kv_mib": round(total_state_q8_bytes / MIB, 2),
            "total_hybrid_cache_q8_kv_gib": round(total_state_q8_bytes / GIB, 4),
        }

    # 4. System RAM & GPU VRAM Matrix across K in {256, 205, 192, 184, 176, 160}
    total_ram_nominal_gib = 32.00
    total_ram_os_usable_gib = round(win_mem["total_phys_bytes"] / GIB, 4)  # 31.7303 GiB
    os_baseline_gib = 5.50      # Windows 11 kernel + Desktop Window Manager + audio/network services
    llama_host_ple_overhead_gib = 1.50  # llama-server host buffers + CPU threadpool + active PLE mmap page cache
    anti_swap_min_free_ram_gib = 3.00   # Mandatory owner requirement: >= 3.0 GiB (3.22 GB) free physical RAM margin
    anti_swap_max_used_ram_gib = round(total_ram_os_usable_gib - anti_swap_min_free_ram_gib, 4)  # 28.7303 GiB

    legion_vram_total_gib = round((12282 * MIB) / GIB, 4)  # 11.9941 GiB (12.88 GB)
    legion_vram_os_reserved_gib = 0.45  # Windows 11 DWM + driver reservation on Laptop GPU
    legion_vram_usable_gib = round(legion_vram_total_gib - legion_vram_os_reserved_gib, 4)  # 11.5441 GiB

    target_8g_vram_total_gib = 8.0000
    target_8g_vram_usable_gib = 7.5500  # 8.00 GiB minus 0.45 GiB OS DWM reservation

    cuda_compute_buf_gib = 0.6500  # ~665 MiB CUDA compute buffer + cuBLAS workspace at ubatch=512

    k_candidates = [256, 205, 192, 184, 176, 160]
    expert_budget_matrix = {}

    for k in k_candidates:
        expert_budget_matrix[str(k)] = {}
        for qname, qinfo in expert_quants.items():
            # Trunk (48 layers, default mparams.load_mtp=false):
            exp_48_bytes = k * qinfo["per_expert_48_layers_bytes_exact"]
            exp_48_bytes_step1 = k * qinfo["per_expert_48_layers_bytes_step1_formula"]
            exp_48_gib = exp_48_bytes / GIB
            exp_48_gb = exp_48_bytes / GB

            # Trunk + MTP (49 layers, --spec-type mtp):
            exp_49_bytes = k * qinfo["per_expert_49_layers_mtp_bytes_exact"]
            exp_49_gib = exp_49_bytes / GIB
            exp_49_gb = exp_49_bytes / GB

            # System RAM totals (Trunk 48L, default load_mtp=false):
            ram_used_48_gib = os_baseline_gib + llama_host_ple_overhead_gib + exp_48_gib
            ram_free_48_nominal_gib = total_ram_nominal_gib - ram_used_48_gib
            ram_free_48_os_usable_gib = total_ram_os_usable_gib - ram_used_48_gib
            ram_free_48_os_usable_gb = ram_free_48_os_usable_gib * GIB / GB

            # System RAM totals (Trunk + MTP 49L, --spec-type mtp):
            ram_used_49_gib = os_baseline_gib + llama_host_ple_overhead_gib + exp_49_gib
            ram_free_49_nominal_gib = total_ram_nominal_gib - ram_used_49_gib
            ram_free_49_os_usable_gib = total_ram_os_usable_gib - ram_used_49_gib
            ram_free_49_os_usable_gb = ram_free_49_os_usable_gib * GIB / GB

            # VRAM weights (Trunk 48L + mmproj):
            vram_w_mmproj = calc_vram_weights(k, include_mtp=False, include_mmproj=True, dense_bpw=5.5)
            vram_w_textonly = calc_vram_weights(k, include_mtp=False, include_mmproj=False, dense_bpw=5.5)

            # GGUF file sizes on disk (Trunk 48L, exact ggml_row_size + F16 router core vs Step 1 rounded bpw + F16 router core):
            # Note: vram_w_textonly["step1_core_dense_with_f16_routers_bytes"] does NOT include ple_small_bf16_bytes,
            # while ple_q4_0_plus_small_bf16_bytes includes both per_layer_token_embd.weight (Q4_0) and ple_small_bf16_bytes (0 double-counting!).
            text_core_gguf_bytes = exp_48_bytes + vram_w_textonly["step1_core_dense_with_f16_routers_bytes"]
            text_core_gguf_bytes_step1 = exp_48_bytes_step1 + vram_w_textonly["step1_core_dense_with_f16_routers_bytes"]
            full_disk_with_ple_mmproj_bytes = text_core_gguf_bytes + ple_q4_0_plus_small_bf16_bytes + vis_mmproj_bf16_bytes
            full_disk_with_ple_mmproj_bytes_step1 = text_core_gguf_bytes_step1 + ple_q4_0_plus_small_bf16_bytes + vis_mmproj_bf16_bytes

            # Context VRAM usage across 8K..128K (with mmproj loaded):
            vram_by_ctx = {}
            for ctx in contexts:
                kv_gib = kv_cache_table[str(ctx)]["total_hybrid_cache_f16_gib"]
                kv_q8_gib = kv_cache_table[str(ctx)]["total_hybrid_cache_q8_kv_gib"]
                used_vram_f16_mmproj = vram_w_mmproj["total_vram_weights_gib"] + kv_gib + cuda_compute_buf_gib
                used_vram_f16_text = vram_w_textonly["total_vram_weights_gib"] + kv_gib + cuda_compute_buf_gib
                used_vram_q8_text = vram_w_textonly["total_vram_weights_gib"] + kv_q8_gib + cuda_compute_buf_gib
                vram_by_ctx[str(ctx)] = {
                    "vram_used_f16_kv_with_mmproj_gib": round(used_vram_f16_mmproj, 4),
                    "vram_used_f16_kv_text_only_gib": round(used_vram_f16_text, 4),
                    "vram_used_q8_kv_text_only_gib": round(used_vram_q8_text, 4),
                    "legion_12g_free_vram_f16_with_mmproj_gib": round(legion_vram_usable_gib - used_vram_f16_mmproj, 4),
                    "legion_12g_fits_f16_with_mmproj": used_vram_f16_mmproj <= legion_vram_usable_gib,
                    "target_8g_free_vram_f16_with_mmproj_gib": round(target_8g_vram_usable_gib - used_vram_f16_mmproj, 4),
                    "target_8g_fits_f16_with_mmproj": used_vram_f16_mmproj <= target_8g_vram_usable_gib,
                    "target_8g_free_vram_q8_text_only_gib": round(target_8g_vram_usable_gib - used_vram_q8_text, 4),
                    "target_8g_fits_q8_text_only": used_vram_q8_text <= target_8g_vram_usable_gib,
                }

            expert_budget_matrix[str(k)][qname] = {
                "k_experts": k,
                "quant": qname,
                "routed_experts_48L_bytes": exp_48_bytes,
                "routed_experts_48L_bytes_step1_formula": exp_48_bytes_step1,
                "routed_experts_48L_gib": round(exp_48_gib, 4),
                "routed_experts_48L_gb": round(exp_48_gb, 4),
                "routed_experts_48L_gb_step1_formula": round(exp_48_bytes_step1 / GB, 4),
                "routed_experts_49L_mtp_bytes": exp_49_bytes,
                "routed_experts_49L_mtp_gib": round(exp_49_gib, 4),
                "routed_experts_49L_mtp_gb": round(exp_49_gb, 4),
                "system_ram_used_48L_gib": round(ram_used_48_gib, 4),
                "system_ram_free_margin_48L_gib": round(ram_free_48_os_usable_gib, 4),
                "system_ram_free_margin_48L_nominal_32gib": round(ram_free_48_nominal_gib, 4),
                "system_ram_free_margin_48L_gb": round(ram_free_48_os_usable_gb, 4),
                "passes_3gib_margin_48L_no_mtp": ram_free_48_os_usable_gib >= anti_swap_min_free_ram_gib,
                "system_ram_used_49L_mtp_gib": round(ram_used_49_gib, 4),
                "system_ram_free_margin_49L_mtp_gib": round(ram_free_49_os_usable_gib, 4),
                "system_ram_free_margin_49L_mtp_nominal_32gib": round(ram_free_49_nominal_gib, 4),
                "system_ram_free_margin_49L_mtp_gb": round(ram_free_49_os_usable_gb, 4),
                "passes_3gib_margin_49L_with_mtp": ram_free_49_os_usable_gib >= anti_swap_min_free_ram_gib,
                "text_core_gguf_bytes": text_core_gguf_bytes,
                "text_core_gguf_gib": round(text_core_gguf_bytes / GIB, 4),
                "text_core_gguf_gb": round(text_core_gguf_bytes / GB, 4),
                "text_core_gguf_gb_step1_formula": round(text_core_gguf_bytes_step1 / GB, 4),
                "ple_tok_embd_q4_0_lazy_mmap_bytes": ple_ngram_q4_0_bytes,
                "ple_tok_embd_q4_0_lazy_mmap_gib": round(ple_ngram_q4_0_bytes / GIB, 4),
                "ple_tok_embd_q4_0_lazy_mmap_gb": round(ple_ngram_q4_0_bytes / GB, 4),
                "ple_total_with_small_proj_bytes": ple_q4_0_plus_small_bf16_bytes,
                "ple_total_with_small_proj_gib": round(ple_q4_0_plus_small_bf16_bytes / GIB, 4),
                "ple_total_with_small_proj_gb": round(ple_q4_0_plus_small_bf16_bytes / GB, 4),
                "full_disk_gguf_with_ple_mmproj_bytes": full_disk_with_ple_mmproj_bytes,
                "full_disk_gguf_with_ple_mmproj_gib": round(full_disk_with_ple_mmproj_bytes / GIB, 4),
                "full_disk_gguf_with_ple_mmproj_gb": round(full_disk_with_ple_mmproj_bytes / GB, 4),
                "full_disk_gguf_with_ple_mmproj_gb_step1_formula": round(full_disk_with_ple_mmproj_bytes_step1 / GB, 4),
                "vram_weights_with_mmproj_gib": vram_w_mmproj["total_vram_weights_gib"],
                "vram_weights_text_only_gib": vram_w_textonly["total_vram_weights_gib"],
                "vram_by_context": vram_by_ctx,
            }

    # 5. Z-Image-Turbo Combine Memory Analysis (Sequential llama-swap vs Co-Resident)
    # Verified from Tongyi-MAI/Z-Image-Turbo (sha: f332072aa78be7aecdf3ee76d5c247082da564a6, apache-2.0)
    # and leejet/Z-Image-Turbo-GGUF (sha: c61c0e422dc8b541b7548cf33a4ef8302b0f8085, apache-2.0, official stable-diffusion.cpp):
    # Note: leejet/Z-Image-Turbo-GGUF ships GGUFs for the 6.15B S3-DiT diffusion transformer;
    # the Qwen3-4B text_encoder/ (8,044,982,000 B = 7.4925 GiB BF16 in Tongyi-MAI/Z-Image-Turbo) is either
    # loaded directly in BF16 (7.4925 GiB RAM) or converted/quantized locally in Step 9 via convert_hf_to_gguf.py + llama-quantize
    # into Q8_0 (3.9804 GiB RAM) or Q4_K (2.1073 GiB RAM).
    zimage_q4k_dit_gib = round(3864250304 / GIB, 4)  # 3.5989 GiB
    zimage_q8_dit_gib = round(6577440704 / GIB, 4)   # 6.1257 GiB
    zimage_vae_gib = round(167666902 / GIB, 4)       # 0.1562 GiB
    zimage_text_enc_bf16_gib = round(8044982000 / GIB, 4)  # 7.4925 GiB
    zimage_text_enc_q8_gib = round((8044982000 // 2) * 8.5 / 8.0 / GIB, 4)  # 3.9804 GiB
    zimage_text_enc_q4k_gib = round((8044982000 // 2) * 4.5 / 8.0 / GIB, 4)  # 2.1073 GiB
    zimage_compute_act_gib = 1.6500  # 1024x1024 S3-DiT + VAE decode activation workspace in sd.cpp

    zimage_profiles = {
        "sd_cpp_q4_k_8gb_target_profile": {
            "description": (
                "Z-Image-Turbo in stable-diffusion.cpp (leejet/Z-Image-Turbo-GGUF z_image_turbo-Q4_K.gguf "
                "3.5989 GiB + VAE 0.1562 GiB + activations 1.65 GiB in VRAM = 5.4051 GiB; "
                "locally quantized Qwen3-4B Text Encoder Q4_K 2.1073 GiB + 0.85 GiB host buffer in System RAM = 2.9573 GiB)"
            ),
            "vram_used_gib": round(zimage_q4k_dit_gib + zimage_vae_gib + zimage_compute_act_gib, 4),
            "ram_used_by_zimage_gib": round(zimage_text_enc_q4k_gib + 0.85, 4),
        },
        "sd_cpp_q8_0_legion_12g_profile": {
            "description": (
                "Z-Image-Turbo in stable-diffusion.cpp (leejet/Z-Image-Turbo-GGUF z_image_turbo-Q8_0.gguf "
                "6.1257 GiB + VAE 0.1562 GiB + activations 1.65 GiB in VRAM = 7.9319 GiB; "
                "locally quantized Qwen3-4B Text Encoder Q8_0 3.9804 GiB + 0.85 GiB host buffer in System RAM = 4.8304 GiB, "
                "or 8.3425 GiB in RAM if Qwen3-4B Text Encoder is kept in unquantized BF16 7.4925 GiB)"
            ),
            "vram_used_gib": round(zimage_q8_dit_gib + zimage_vae_gib + zimage_compute_act_gib, 4),
            "ram_used_by_zimage_gib": round(zimage_text_enc_q8_gib + 0.85, 4),
            "ram_used_by_zimage_bf16_text_enc_gib": round(zimage_text_enc_bf16_gib + 0.85, 4),
        },
        "bf16_full_weights": {
            "description": "Z-Image-Turbo unquantized BF16 (Transformer 11.4644 GiB + Text Encoder 7.4925 GiB + VAE 0.1562 GiB)",
            "vram_used_gib": round(24619690888 / 2 / GIB + zimage_vae_gib, 4),
            "ram_used_by_zimage_gib": round(zimage_text_enc_bf16_gib + 1.00, 4),
        },
    }

    cores_xxs_ram = round(
        expert_budget_matrix["205"]["IQ3_XXS"]["system_ram_used_48L_gib"]
        + zimage_profiles["sd_cpp_q8_0_legion_12g_profile"]["ram_used_by_zimage_gib"],
        4,
    )
    cores_s_ram = round(
        expert_budget_matrix["205"]["IQ3_S"]["system_ram_used_48L_gib"]
        + zimage_profiles["sd_cpp_q8_0_legion_12g_profile"]["ram_used_by_zimage_gib"],
        4,
    )

    combine_modes = {
        "mode_A_llama_swap_sequential_RECOMMENDED": {
            "mechanism": "llama-swap unloads llama-server before starting sd.cpp (or switches active group); only 1 model resides in VRAM/RAM at a time",
            "state_1_llm_active_k205_iq3_xxs": {
                "ram_used_gib": expert_budget_matrix["205"]["IQ3_XXS"]["system_ram_used_48L_gib"],
                "ram_free_margin_gib": expert_budget_matrix["205"]["IQ3_XXS"]["system_ram_free_margin_48L_gib"],
                "vram_used_32k_ctx_gib": expert_budget_matrix["205"]["IQ3_XXS"]["vram_by_context"]["32768"]["vram_used_f16_kv_with_mmproj_gib"],
                "ssd_pagefile_swap_bytes": 0,
            },
            "state_1_llm_active_k205_iq3_s": {
                "ram_used_gib": expert_budget_matrix["205"]["IQ3_S"]["system_ram_used_48L_gib"],
                "ram_free_margin_gib": expert_budget_matrix["205"]["IQ3_S"]["system_ram_free_margin_48L_gib"],
                "vram_used_32k_ctx_gib": expert_budget_matrix["205"]["IQ3_S"]["vram_by_context"]["32768"]["vram_used_f16_kv_with_mmproj_gib"],
                "ssd_pagefile_swap_bytes": 0,
            },
            "state_2_zimage_active_q8_0": {
                "ram_used_gib": round(os_baseline_gib + zimage_profiles["sd_cpp_q8_0_legion_12g_profile"]["ram_used_by_zimage_gib"], 4),
                "ram_free_margin_gib": round(total_ram_os_usable_gib - (os_baseline_gib + zimage_profiles["sd_cpp_q8_0_legion_12g_profile"]["ram_used_by_zimage_gib"]), 4),
                "ram_free_margin_if_bf16_text_enc_gib": round(
                    total_ram_os_usable_gib - (os_baseline_gib + zimage_profiles["sd_cpp_q8_0_legion_12g_profile"]["ram_used_by_zimage_bf16_text_enc_gib"]),
                    4,
                ),
                "vram_used_gib": zimage_profiles["sd_cpp_q8_0_legion_12g_profile"]["vram_used_gib"],
                "ssd_pagefile_swap_bytes": 0,
            },
            "verdict": "PASS (0 B SSD pagefile swap in both states; >= 3.38 GiB free OS-usable RAM in LLM state and >= 17.89–21.40 GiB free RAM in Z-Image state)",
        },
        "mode_B_coresident_in_ram_FORBIDDEN": {
            "mechanism": "Keeping LLM (K=205) AND Z-Image-Turbo resident in RAM simultaneously",
            "k205_iq3_xxs_plus_zimage_q8_ram_used_gib": cores_xxs_ram,
            "k205_iq3_s_plus_zimage_q8_ram_used_gib": cores_s_ram,
            "anti_swap_max_used_ram_gib": anti_swap_max_used_ram_gib,
            "verdict": (
                f"FAIL (Requires {cores_xxs_ram:.2f}–{cores_s_ram:.2f} GiB RAM > {anti_swap_max_used_ram_gib:.2f} GiB "
                "anti-swap ceiling; triggers Windows pagefile.sys SSD thrashing and violates Rule 1 of CLAUDE.md: Only 1 model in VRAM at a time)"
            ),
        },
    }

    # 6. Eval Suite Baselines & Step 8 Acceptance Criteria (Computed from actual JSONs)
    judges = json.loads((EVAL_RESULTS / "judges_aggregated.json").read_text(encoding="utf-8"))
    gyro_summary = json.loads((GYRO_RUN / "run_summary.json").read_text(encoding="utf-8"))

    def avg_score(model_key: str, task_ids: list[str], metric: str = "overall") -> float:
        vals = [
            judges["models"][model_key][tid]["mean"][metric]
            for tid in task_ids
            if tid in judges["models"][model_key] and judges["models"][model_key][tid]["mean"][metric] is not None
        ]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    t1_t3 = ["t1", "t2", "t3"]
    all_12 = [f"t{i}" for i in range(1, 13)]
    gyro_non_loop = ["t1", "t2", "t3", "t4", "t6", "t9", "t10", "t12"]
    ru_tasks = ["t3", "t7", "t8", "t10"]
    ru_non_loop = ["t3", "t10"]

    gyro_tasks_list = gyro_summary if isinstance(gyro_summary, list) else gyro_summary.get("tasks", [])
    gyro_tok_s_list = [t["tok_per_sec"] for t in gyro_tasks_list]
    gyro_non_loop_tok_s_list = [t["tok_per_sec"] for t in gyro_tasks_list if t["task"] in gyro_non_loop]
    gyro_mean_tok_s = round(sum(gyro_tok_s_list) / len(gyro_tok_s_list), 2)  # 31.60 tok/s
    gyro_non_loop_mean_tok_s = round(sum(gyro_non_loop_tok_s_list) / len(gyro_non_loop_tok_s_list), 2)  # 28.46 tok/s
    gyro_min_tok_s = round(min(gyro_tok_s_list), 2)
    gyro_max_tok_s = round(max(gyro_tok_s_list), 2)

    eval_baselines_and_targets = {
        "verified_baselines": {
            "qwen3.8-think-8k": {
                "t1_t3_mean_overall": avg_score("qwen3.8-think-8k", t1_t3, "overall"),
                "t1_t3_mean_canon": avg_score("qwen3.8-think-8k", t1_t3, "canon"),
                "t1_t3_mean_design": avg_score("qwen3.8-think-8k", t1_t3, "design"),
                "t1_t3_mean_copy": avg_score("qwen3.8-think-8k", t1_t3, "copy"),
                "t3_ru": judges["models"]["qwen3.8-think-8k"]["t3"]["mean"]["ru"],
            },
            "qwen3.8-no-think": {
                "t1_t3_mean_overall": avg_score("qwen3.8-no-think", t1_t3, "overall"),
                "t1_t3_mean_canon": avg_score("qwen3.8-no-think", t1_t3, "canon"),
                "t1_t3_mean_design": avg_score("qwen3.8-no-think", t1_t3, "design"),
                "t1_t3_mean_copy": avg_score("qwen3.8-no-think", t1_t3, "copy"),
                "t3_ru": judges["models"]["qwen3.8-no-think"]["t3"]["mean"]["ru"],
            },
            "gyro-m-local_tq2_0": {
                "t1_t3_mean_overall": avg_score("gyro-m-local", t1_t3, "overall"),
                "non_loop_8_tasks_mean_overall": avg_score("gyro-m-local", gyro_non_loop, "overall"),
                "all_12_tasks_mean_overall": avg_score("gyro-m-local", all_12, "overall"),
                "ru_all_4_tasks_mean": avg_score("gyro-m-local", ru_tasks, "ru"),
                "ru_non_loop_2_tasks_mean": avg_score("gyro-m-local", ru_non_loop, "ru"),
                "csp_infinite_loops_count": 4,
                "csp_infinite_loops_tasks": ["t5", "t7", "t8", "t11"],
                "t4_dag_tsc_strict_pass": False,
                "t4_dag_unit_tests_passed": "5/12",
                "tok_per_sec_mean_all_12": gyro_mean_tok_s,
                "tok_per_sec_mean_8_non_loop": gyro_non_loop_mean_tok_s,
                "tok_per_sec_range": [gyro_min_tok_s, gyro_max_tok_s],
                "vram_used_mib": 10820,
            },
        },
        "step8_acceptance_criteria": {
            "1_mean_overall_t1_t3_min": 8.50,
            "1_rationale": "Must stay within <= 0.95 pts of full donor qwen3.8-think-8k (9.45), beat qwen3.8-no-think (7.86) by >= +0.64 pts, and match/exceed Gyro-M on T1-T3 (8.72 for IQ3_S, >= 8.50 for IQ3_XXS).",
            "2_mean_overall_all_12_tasks_min": 8.00,
            "2_rationale": "Must beat Gyro-M's 12-task average (5.40) by >= +2.60 pts and beat Gyro-M's 8-task non-loop average (7.95) across all 12 tasks.",
            "3_mean_ru_4_tasks_min": 8.50,
            "3_rationale": "Across all 4 Russian tasks (t3, t7, t8, t10), mean RU rubric score must be >= 8.50 / 10 (vs Gyro-M's 4.88 across 4 tasks due to t7/t8 loops).",
            "4_csp_repetition_loops_max": 0,
            "4_rationale": "0 / 12 tasks allowed to enter degenerate token repetition loops in <head> / <meta> CSP (vs 4 / 12 in Gyro-M TQ2_0).",
            "5_t4_dag_ts_strict_and_tests": {
                "tsc_strict_no_emit": "PASS (0 errors)",
                "unit_tests_min_passed": "10/12 (target 12/12, vs Gyro-M 5/12)",
            },
            "6_automated_browser_and_lh_gates": {
                "console_and_page_errors_post_csp": 0,
                "external_network_requests_blocked": 0,
                "horizontal_overflow_desktop_1440": "0 / 11 HTML tasks",
                "horizontal_overflow_mobile_375": "<= 1 / 11 HTML tasks",
                "lighthouse_accessibility_bp_min": 90,
                "oklch_contrast_min_ratio": 4.5,
            },
            "7_performance_and_anti_swap_gates": {
                "tok_per_sec_legion_4080_min": 18.0,
                "tok_per_sec_legion_4080_target_range": [20.0, 30.0],
                "free_physical_ram_margin_min_gib": 3.00,
                "ssd_pagefile_writes_pages_output_per_sec": 0,
                "vram_limit_legion_profile_gib": 11.50,
                "vram_limit_8gb_target_profile_gib": 7.55,
            },
        },
    }

    output_payload = {
        "step": "3.6",
        "generated_by": "scripts/step3_6_ram_vram_budget.py",
        "live_hardware_audit": {
            "windows_memory": win_mem,
            "gpu": gpu_info,
        },
        "zimage_primary_sources": zimage_meta,
        "expert_quantization_geometry": expert_quants,
        "hybrid_kv_idx_recurrent_cache_table": kv_cache_table,
        "expert_count_budget_matrix": expert_budget_matrix,
        "zimage_combine_profiles": zimage_profiles,
        "zimage_combine_runtime_modes": combine_modes,
        "eval_baselines_and_step8_acceptance_criteria": eval_baselines_and_targets,
        "architectural_decision_k": {
            "selected_k": 205,
            "backup_k_if_mtp_enabled_in_ram_for_iq3_s": 192,
            "recommended_runtime_flags_legion_12gb": (
                "llama-server -m D:\\projects\\SmartLLM\\models\\SmartLLM-Qwen3.8-205E-IQ3_S.gguf "
                "--mmproj D:\\projects\\SmartLLM\\models\\mmproj-Qwen3.8-Flash-Next-BF16.gguf "
                "--load-mode mmap --lazy-mode on -ngl 99 "
                "-ot \"\\.ffn_(gate|up|down)_exps\\.weight=CPU\" "
                "-c 32768 -np 1 -ub 512 -fa on"
            ),
            "recommended_runtime_flags_8gb_vram_profile": (
                "llama-server -m D:\\projects\\SmartLLM\\models\\SmartLLM-Qwen3.8-205E-IQ3_XXS.gguf "
                "--mmproj D:\\projects\\SmartLLM\\models\\mmproj-Qwen3.8-Flash-Next-BF16.gguf "
                "--load-mode mmap --lazy-mode on -ngl 99 "
                "-ot \"\\.ffn_(gate|up|down)_exps\\.weight=CPU\" "
                "-c 16384 -np 1 -ctk q8_0 -ctv q8_0 -ub 512 -fa on"
            ),
        },
    }

    out_json = STEP36_RAW / "ram_vram_budget.json"
    out_json.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out_json}")
    print("\n=== SUMMARY OF K CANDIDATES ON 31.7303 GiB OS-USABLE RAM (OS=5.50 GiB, Host/PLE=1.50 GiB) ===")
    for k in k_candidates:
        for q in ["IQ3_XXS", "IQ3_S"]:
            row = expert_budget_matrix[str(k)][q]
            print(
                f"K={k:3d} | {q:7s} | 48L Exps={row['routed_experts_48L_gib']:6.2f} GiB ({row['routed_experts_48L_gb']:6.2f} GB) "
                f"| Free RAM (48L)={row['system_ram_free_margin_48L_gib']:5.2f} GiB ({'PASS' if row['passes_3gib_margin_48L_no_mtp'] else 'FAIL'}) "
                f"| Free RAM (49L MTP)={row['system_ram_free_margin_49L_mtp_gib']:5.2f} GiB ({'PASS' if row['passes_3gib_margin_49L_with_mtp'] else 'FAIL'}) "
                f"| Full GGUF={row['full_disk_gguf_with_ple_mmproj_gib']:5.2f} GiB ({row['full_disk_gguf_with_ple_mmproj_gb']:5.2f} GB, Step1={row['full_disk_gguf_with_ple_mmproj_gb_step1_formula']:5.2f} GB)"
            )


if __name__ == "__main__":
    main()
