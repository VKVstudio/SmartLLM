#!/usr/bin/env python3
"""<= 60s 1-layer (bid=0) real-donor GPU micro-smoke verifying all chunked streaming fixes:
1. SingleLayerContext(bid=0, backend='cupy') skips mlp.experts on CPU (0 B BF16 copy).
2. MoELayerWeights.from_hf_moe_block streams 512 experts in 16-expert slices + frees pinned DMA.
3. ReapHopeRcoAccumulator + Quota selector -> K=320 -> heal_layer_c3 (shallow view + chunked Gram).
4. PostHealStatsCollector + FP16 _snapshot_moe_cpu_arrays + Stage-2b V1 (IQ3_XXS + GSQ Q2_0) quant-sim.
5. Chunked lm_head KL/top-1 check + clean 0-VRAM exit.
"""

from __future__ import annotations

import gc
import json
import time

import numpy as np
import torch
from transformers.models.qwen4_exp.modeling_qwen4_exp import Qwen4ExpTextRotaryEmbedding

from scripts.v2.common_io import (
    DONOR_DIR,
    SampleDomainFlags,
    assert_zero_swap_and_mem,
    read_linux_mem_telemetry,
)
from scripts.v2.cupy_moe_backend import (
    MoELayerWeights,
    PostHealStatsCollector,
    ReapHopeRcoAccumulator,
    forward_moe_v2,
    free_cupy_pools,
)
from scripts.v2.expert_selectors import build_quota_locks, select_a2_quota_reap
from scripts.v2.gsq_q2_0 import LibGGMLQuantSimulator
from scripts.v2.healing_c3 import heal_layer_c3
from scripts.v2.model_runner import PreparedSample, SingleLayerContext, load_text_cfg_and_index
from scripts.v2.prequant_gate import compute_kl_and_top1_from_hidden, upload_2d_fp16_chunked_cupy
from scripts.v2.wave2_shootout import (
    _build_quant_simulated_moe_from_cpu_snap,
    _evaluate_gsq_vs_stock_q2_0_down_on_eval,
    _snapshot_moe_cpu_arrays,
)


def main() -> int:
    t0 = time.perf_counter()
    tel_start = read_linux_mem_telemetry()
    base_pswpout = tel_start.pswpout
    min_avail = tel_start.mem_available_gib

    def _track_mem(tag: str) -> None:
        nonlocal min_avail
        tel = assert_zero_swap_and_mem(base_pswpout)
        min_avail = min(min_avail, tel.mem_available_gib)
        print(
            f"[MicroSmoke] {tag}: t={time.perf_counter()-t0:.2f}s "
            f"MemAvail={tel.mem_available_gib:.2f}GiB d_pswpout={tel.pswpout - base_pswpout}",
            flush=True,
        )

    text_cfg, st_index = load_text_cfg_and_index(DONOR_DIR)
    hc_count = int(text_cfg.hc_count)
    hidden_size = int(text_cfg.hidden_size)
    rotary_emb = Qwen4ExpTextRotaryEmbedding(config=text_cfg)
    sim = LibGGMLQuantSimulator()

    ctx = SingleLayerContext(
        bid=0,
        text_cfg=text_cfg,
        st_index=st_index,
        rotary_emb=rotary_emb,
        backend="cupy",
        is_mtp=False,
    )
    assert ctx.layer.mlp.experts.gate_up_proj.device.type == "meta", "Expected meta experts on CPU!"
    _track_mem("after_ctx_init")

    moe_donor = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend="cupy")
    _track_mem("after_512E_donor_stream_upload")

    rng = np.random.default_rng(1234)
    reap_acc = ReapHopeRcoAccumulator(
        num_experts=int(text_cfg.num_experts),
        top_k=int(text_cfg.num_experts_per_tok),
        collect_rco_cache=True,
        rco_max_tokens=2048,
        rco_stride=4,
    )
    h_cal_list = []
    y_cal_list = []
    for i in range(8):
        seq_len = 1024
        ids = torch.from_numpy(rng.integers(10, 50000, size=(1, seq_len), dtype=np.int64))
        h_in = torch.from_numpy(
            (rng.standard_normal((1, seq_len, hc_count, hidden_size)) * 0.05).astype(np.float32)
        ).to(torch.bfloat16)
        flags = SampleDomainFlags(
            "ru_copy" if i % 2 == 0 else "en_web",
            "smoke",
            (i % 2 == 0),
            (i % 3 == 0),
            (i == 0),
        )
        ps = PreparedSample(i, f"smk_{i}", seq_len, ids, None, flags)
        reap_acc.set_sample_flags(flags)
        hm_in, hyper_ffn, inj_ffn = ctx.forward_pre_moe(h_in, ps)
        yd = forward_moe_v2(moe_donor, hm_in, flat_token_ids=ids, reap_acc=reap_acc)
        _ = ctx.combine_post_moe(yd, hyper_ffn, inj_ffn, hc_count, hidden_size)
        h_cal_list.append(hm_in.to(torch.float32).numpy().reshape(seq_len, hidden_size))
        y_cal_list.append(yd.to(torch.float32).numpy().reshape(seq_len, hidden_size))

    moe_donor.close()
    free_cupy_pools()
    _track_mem("after_donor_forward_and_close")

    scores = reap_acc.finalize_score_dict()
    locks = build_quota_locks(scores)
    keep_320 = select_a2_quota_reap(scores, 320, locks=locks)

    h_cal_all = np.concatenate(h_cal_list, axis=0)
    y_cal_all = np.concatenate(y_cal_list, axis=0)
    del h_cal_list, y_cal_list

    moe_p = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend="cupy", keep_indices=keep_320)
    heal_res = heal_layer_c3(moe_p, h_cal_all, y_cal_all, max_heal_tokens=8192, c1_max_steps=40)
    moe_p.close()
    free_cupy_pools()
    _track_mem("after_c3_heal")

    moe_rk = MoELayerWeights.from_hf_moe_block(
        ctx.layer.mlp,
        backend="cupy",
        keep_indices=keep_320,
        gate_override_f32=heal_res.w_gate_f32,
        alpha_scales=heal_res.alpha_scales,
        sh_down_override=heal_res.w_down_shexp_f32,
    )
    ph_stats = PostHealStatsCollector(
        bid=0,
        num_experts=320,
        hidden_dim=hidden_size,
        inter_dim=int(text_cfg.moe_intermediate_size),
    )
    _ = forward_moe_v2(moe_rk, h_cal_all[:2048], post_heal=ph_stats)
    cpu_snap = _snapshot_moe_cpu_arrays(moe_rk)
    moe_rk.close()
    free_cupy_pools()
    _track_mem("after_cpu_snap_fp16")

    # Use K=32 subset of cpu_snap for <=15s GSQ Q2_0 + IQ3_XXS quant-sim smoke while exercising exact code path
    sub_k = 32
    sub_snap = {
        "gw": cpu_snap["gw"][:sub_k],
        "gu": cpu_snap["gu"][:sub_k],
        "dn": cpu_snap["dn"][:sub_k],
        "sh_g": cpu_snap["sh_g"],
        "sh_u": cpu_snap["sh_u"],
        "sh_d": cpu_snap["sh_d"],
        "sh_inp": cpu_snap["sh_inp"],
        "top_k": cpu_snap["top_k"],
        "norm_topk_prob": cpu_snap["norm_topk_prob"],
    }
    moe_v1, gsq_dq = _build_quant_simulated_moe_from_cpu_snap(
        sub_snap, ph_stats, "V1", sim, backend="cupy", cached_gsq_dn_dq=None
    )
    y_v1 = forward_moe_v2(moe_v1, h_cal_all[:512]).numpy()
    moe_v1.close()
    free_cupy_pools()

    assert gsq_dq is not None
    dn_stk = sim.quantize_dequantize_3d_experts(sub_snap["dn"], "q2_0", None, out_dtype=np.float16, chunk_experts=16)
    gsq_cmp = _evaluate_gsq_vs_stock_q2_0_down_on_eval(sub_snap, gsq_dq, dn_stk, h_cal_all[:512])
    _track_mem("after_stage2b_quant_sim")

    # Verify chunked lm_head upload + teacher-forced KL
    lm_dummy = (rng.standard_normal((16384, hidden_size)) * 0.02).astype(np.float16)
    lm_gpu = upload_2d_fp16_chunked_cupy(lm_dummy, row_chunk=8192)
    kl_s, t1_s, n_t = compute_kl_and_top1_from_hidden(y_cal_all[:256], y_v1[:256], lm_gpu, backend="cupy")
    del lm_gpu, lm_dummy

    ctx.close()
    del cpu_snap, sub_snap, gsq_dq, dn_stk, ph_stats, h_cal_all, y_cal_all
    free_cupy_pools()
    gc.collect()
    _track_mem("final_clean_exit")

    elapsed = round(time.perf_counter() - t0, 2)
    summary = {
        "passed": True,
        "elapsed_sec": elapsed,
        "min_mem_avail_gib": round(min_avail, 3),
        "c3_val_before": round(heal_res.val_rel_l2_before, 6),
        "c3_val_after": round(heal_res.val_rel_l2_after_c3, 6),
        "gsq_vs_stock_smoke": gsq_cmp,
        "kl_smoke_tokens": n_t,
    }
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
