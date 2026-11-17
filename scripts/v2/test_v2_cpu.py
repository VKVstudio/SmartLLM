#!/usr/bin/env python3
"""Comprehensive Pure-CPU Unit & Integration Test Suite for SmartLLM v2 (WP-C1 Wave 1 + OPUS §0.3a).

Strictly enforces Wave 1 & OPUS §0.3a constraints:
- Zero GPU execution (`'cupy' not in sys.modules`, zero CUDA context creation).
- Zero-Disk-Swap SLA §0.3a telemetry (`disk_swap_used_kb == 0`, `disk_swap_write_sectors_delta == 0`,
  `zram_orig_delta_mib <= 512.0`, `MemAvailable >= 3.0 GiB` via `scripts.infra.sla_watchdog`).
- Per-layer checkpoint resume & determinism probe (`OPUS §0.3a.4`).
- Clean `/tmp` scratch lifecycle (`0 B` left behind after suite exits).
"""

from __future__ import annotations

import glob
import importlib
import json
import os
import py_compile
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch

ROOT_DIR = Path("/mnt/rescue/projects/SmartLLM")
GGUF_PY_DIR = ROOT_DIR / "tools" / "llama.cpp" / "gguf-py"
for _p in (str(ROOT_DIR), str(GGUF_PY_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import gguf  # noqa: E402
from safetensors.torch import save_file  # noqa: E402


def test_01_syntax_and_zero_gpu_imports() -> Dict[str, Any]:
    v2_files = sorted(glob.glob(str(ROOT_DIR / "scripts" / "v2" / "*.py")))
    assert len(v2_files) >= 11, f"Expected >= 11 files in scripts/v2, found {len(v2_files)}"
    for fp in v2_files:
        py_compile.compile(fp, doraise=True)

    modules = [
        "scripts.v2",
        "scripts.v2.common_io",
        "scripts.v2.cupy_moe_backend",
        "scripts.v2.expert_selectors",
        "scripts.v2.healing_c3",
        "scripts.v2.gsq_q2_0",
        "scripts.v2.assemble_gguf",
        "scripts.v2.prequant_gate",
        "scripts.v2.model_runner",
        "scripts.v2.wave2_shootout",
        "scripts.v2.wave3_full_run",
    ]
    for mod_name in modules:
        importlib.import_module(mod_name)

    # Static symtable undefined-global scan across all scripts/v2/*.py files
    import builtins
    import symtable

    builtin_names = set(dir(builtins)) | {
        "__annotations__",
        "__conditional_annotations__",
        "__doc__",
        "__file__",
        "__name__",
        "__package__",
    }
    undef_errors: List[str] = []
    for p_raw in v2_files:
        p = Path(p_raw)
        src = p.read_text(encoding="utf-8")
        top = symtable.symtable(src, str(p), "exec")
        top_defs = {s.get_name() for s in top.get_symbols() if s.is_local() or s.is_imported()}

        def _walk_st(st: symtable.SymbolTable, enc_defs: set[str], fp: Path = p) -> None:
            cur_defs = enc_defs | {
                s.get_name() for s in st.get_symbols() if s.is_local() or s.is_imported() or s.is_parameter()
            }
            for sym in st.get_symbols():
                if sym.is_global() and not sym.is_declared_global():
                    nm = sym.get_name()
                    if nm not in cur_defs and nm not in builtin_names:
                        undef_errors.append(f"{fp.name}:{st.get_lineno()} ({st.get_name()}): {nm}")
            for ch in st.get_children():
                _walk_st(ch, cur_defs if st.get_type() != "class" else enc_defs, fp)

        _walk_st(top, top_defs)
    assert not undef_errors, f"Undefined global names found: {undef_errors}"

    assert "cupy" not in sys.modules, "cupy must NOT be imported eagerly on CPU path!"
    return {"compiled_files": len(v2_files), "imported_modules": len(modules), "cupy_loaded": False}


def test_02_common_io_and_zero_swap_telemetry() -> Dict[str, Any]:
    from scripts.v2.common_io import (
        LayerImatrixCollector,
        ResumablePingPong,
        assert_zero_swap_and_mem,
        capture_v2_swap_baseline,
        classify_sample_domains,
        read_linux_mem_telemetry,
        reorder_gdn_v_heads_activation,
        write_imatrix_gguf,
    )

    sw_base = capture_v2_swap_baseline()
    t0 = read_linux_mem_telemetry()
    t1 = assert_zero_swap_and_mem(sw_base, min_avail_gib=3.0)
    t2 = assert_zero_swap_and_mem(baseline_pswpout=t0.pswpout, min_avail_gib=3.0)
    assert t1.disk_swap_used_kb == 0 and t2.disk_swap_used_kb == 0
    assert (t1.disk_swap_write_sectors - sw_base.disk_swap_write_sectors) == 0
    assert (t1.zram_orig_mib - sw_base.zram_orig_mib) <= 512.0
    assert t1.mem_available_gib >= 3.0

    f_ru = classify_sample_domains({"id": "s1", "stratum": "ru_copy_editorial", "text": "Привет, это чистый русский текст для лендинга студии."})
    assert f_ru.is_ru and f_ru.is_copy_craft and not f_ru.is_vision
    f_vis = classify_sample_domains({"id": "s2", "stratum": "mm_ui_audit", "has_vision": True, "text": "Audit hero contrast."})
    assert f_vis.is_vision and not f_vis.is_ru

    # Verify live WP-C2 data/calib_v2/calib_v2.jsonl schema, domain classification, & vision paths
    from scripts.v2.common_io import MMPROJ_GGUF, REF_205E_GGUF
    from scripts.v2.model_runner import _extract_record_image_path

    assert REF_205E_GGUF.is_file(), f"Missing {REF_205E_GGUF}"
    assert MMPROJ_GGUF.is_file(), f"Missing {MMPROJ_GGUF}"

    calib_v2_path = ROOT_DIR / "data" / "calib_v2" / "calib_v2.jsonl"
    if calib_v2_path.is_file():
        with open(calib_v2_path, "r", encoding="utf-8") as cf:
            c_rows = [json.loads(ln) for ln in cf if ln.strip()]
        c_flags = [classify_sample_domains(r) for r in c_rows]
        vis_paths = [_extract_record_image_path(r) for r, fl in zip(c_rows, c_flags) if fl.is_vision]
        assert len(c_flags) == 640
        assert len(vis_paths) == 21 and all(vp is not None and vp.is_file() for vp in vis_paths)
        assert sum(1 for x in c_flags if x.is_ru) >= 200
        assert sum(1 for x in c_flags if x.is_copy_craft) >= 140

    # Verify GDN V-head permutation shape and invertibility check
    x_gdn = torch.arange(2 * 4 * 3 * 8, dtype=torch.float32).reshape(2, 4 * 3 * 8)
    y_gdn = reorder_gdn_v_heads_activation(x_gdn, num_k_heads=4, num_v_heads=12, head_v_dim=8)
    assert y_gdn.shape == x_gdn.shape
    assert not torch.equal(x_gdn, y_gdn)
    assert torch.isclose(x_gdn.sum(), y_gdn.sum())

    tmp = Path(tempfile.mkdtemp(prefix="test_v2_io_", dir="/tmp"))
    try:
        pp = ResumablePingPong(tmp / "pingpong", "test", seq_lengths=[5, 9], hc_count=4, hidden_size=32)
        sa = pp.open_slot("A", create=True)
        sb = pp.open_slot("B", create=True)
        v0 = torch.randn(1, 5, 4, 32, dtype=torch.bfloat16)
        v1 = torch.randn(1, 9, 4, 32, dtype=torch.bfloat16)
        sa.write_seq(0, v0)
        sa.write_seq(1, v1)
        sb.write_seq(0, sa.read_seq(0) * 2.0)
        assert torch.equal(sa.read_seq(0), v0)
        assert torch.equal(sa.read_seq(1), v1)
        assert torch.equal(sb.read_seq(0), v0 * 2.0)

        pp.save_state(completed_layer=3, active_slot="B", extra={"ok": True})
        st = pp.load_state()
        assert st is not None and st["completed_layer"] == 3 and st["active_slot"] == "B"

        imat = LayerImatrixCollector()
        act_2d = torch.tensor([[1.0, 2.0, 3.0, 4.0], [2.0, 0.0, 1.0, 2.0]], dtype=torch.float32)
        imat.record_2d(("blk.0.attn_q.weight",), act_2d)
        imat.record_3d_expert(("blk.0.ffn_down_exps.weight",), n_experts=3, expert_idx=1, x=act_2d)
        e_norm = torch.ones((1, 3, 4), dtype=torch.float32) * 2.0
        h_norm = torch.ones((1, 3, 2, 4), dtype=torch.float32) * 3.0
        imat.record_mtp_eh_proj("blk.2.nextn.eh_proj.weight", e_norm, h_norm)

        imat_path = tmp / "imatrix_test.gguf"
        n_ent = write_imatrix_gguf(imat_path, imat, dataset_name="unit_test")
        assert n_ent == 3
        reader = gguf.GGUFReader(str(imat_path), "r")
        t_names = {t.name: t for t in reader.tensors}
        assert "blk.0.attn_q.weight.in_sum2" in t_names
        assert t_names["blk.0.attn_q.weight.in_sum2"].tensor_type == gguf.GGMLQuantizationType.F32
        assert t_names["blk.0.attn_q.weight.counts"].tensor_type == gguf.GGMLQuantizationType.F32
        assert "blk.0.ffn_down_exps.weight.in_sum2" in t_names
        assert "blk.2.nextn.eh_proj.weight.in_sum2" in t_names
        q_sum2 = np.frombuffer(t_names["blk.0.attn_q.weight.in_sum2"].data.tobytes(), dtype=np.float32)
        np.testing.assert_allclose(q_sum2, np.array([5.0, 4.0, 10.0, 20.0], dtype=np.float32))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return {
        "mem_avail_gib": round(t1.mem_available_gib, 3),
        "disk_swap_used_kb": int(t1.disk_swap_used_kb),
        "disk_swap_write_sectors_delta": int(t1.disk_swap_write_sectors - sw_base.disk_swap_write_sectors),
        "zram_orig_delta_mib": round(max(0.0, t1.zram_orig_mib - sw_base.zram_orig_mib), 3),
        "pswpout_delta": int(max(0, t1.pswpout - t0.pswpout)),
        "imatrix_verified": True,
    }


def test_03_moe_backend_and_qwen4exp_3layer_parity() -> Dict[str, Any]:
    from transformers.models.qwen4_exp import Qwen4ExpForCausalLM, Qwen4ExpTextConfig

    from scripts.v2.common_io import (
        QSAIndexerWrapper,
        SafetensorsIndex,
        SafeStreamingPLENGramEmbedding,
        SampleDomainFlags,
    )
    from scripts.v2.cupy_moe_backend import (
        MoELayerWeights,
        forward_moe_v2,
        verify_moe_backend_vs_fp64,
    )
    from scripts.v2.model_runner import PreparedSample, SingleLayerContext

    fp64_chk = verify_moe_backend_vs_fp64(backend="cpu", n_tokens=32, num_experts=16, top_k=4, hidden_dim=64, inter_dim=32)
    assert fp64_chk["passed"], f"MoE FP64 parity failed: {fp64_chk}"

    torch.manual_seed(42)
    cfg = Qwen4ExpTextConfig(
        vocab_size=256,
        hidden_size=128,
        num_hidden_layers=3,
        num_attention_heads=4,
        num_key_value_heads=2,
        head_dim=32,
        linear_num_key_heads=2,
        linear_num_value_heads=4,
        linear_key_head_dim=32,
        linear_value_head_dim=32,
        linear_conv_kernel_dim=4,
        moe_intermediate_size=64,
        shared_expert_intermediate_size=64,
        num_experts=16,
        num_experts_per_tok=4,
        layer_types=["linear_attention", "linear_attention", "indexed_attention"],
        hc_count=4,
        hc_lowrank=16,
        ple_layer_ids=[2],
        ple_embed_dim=128,
        ple_conv_kernel_size=2,
        ngram_size=3,
        heads_per_ngram=2,
        ngram_vocab_size_base=256,
        split_ngram_parts=2,
        indexer_n_heads=2,
        indexer_kv_heads=1,
        indexer_head_dim=32,
        indexer_budget=8,
        indexer_compress_ratio=4,
        eos_token_id=2,
    )
    cfg._attn_implementation = "sdpa"
    model = Qwen4ExpForCausalLM(cfg).to(torch.bfloat16).eval()

    x_ids = torch.randint(3, 250, (1, 40), dtype=torch.long)
    x_ids[0, 11] = 2
    x_ids[0, 26] = 2

    with torch.no_grad():
        out_ref = model(input_ids=x_ids)

    orig_idx = model.model.layers[2].self_attn.indexer
    model.model.layers[2].self_attn.indexer = QSAIndexerWrapper(orig_idx)
    with torch.no_grad():
        out_qsa = model(input_ids=x_ids)
    model.model.layers[2].self_attn.indexer = orig_idx
    qsa_max_diff = float((out_ref.logits.float() - out_qsa.logits.float()).abs().max().item())
    assert qsa_max_diff == 0.0, f"QSAIndexerWrapper must be bit-exact vs HF, got diff={qsa_max_diff}"

    tmp = Path(tempfile.mkdtemp(prefix="test_v2_3layer_", dir="/tmp"))
    try:
        sd = model.state_dict()
        ple_w = sd.pop("model.layers.1.ple.ple_embedding.ngram_embedding.weight")
        half = ple_w.shape[0] // 2
        s0 = {"model.layers.1.ple.ple_embedding.ngram_embedding.shard_0.weight": ple_w[:half].contiguous()}
        s1 = {"model.layers.1.ple.ple_embedding.ngram_embedding.shard_1.weight": ple_w[half:].contiguous()}
        save_file(sd, str(tmp / "model-00001-of-00003.safetensors"))
        save_file(s0, str(tmp / "model-00002-of-00003.safetensors"))
        save_file(s1, str(tmp / "model-00003-of-00003.safetensors"))
        wmap = {k: "model-00001-of-00003.safetensors" for k in sd}
        wmap.update({k: "model-00002-of-00003.safetensors" for k in s0})
        wmap.update({k: "model-00003-of-00003.safetensors" for k in s1})
        (tmp / "model.safetensors.index.json").write_text(json.dumps({"metadata": {}, "weight_map": wmap}))

        st_idx = SafetensorsIndex(tmp, drop_cache=True)
        ple_stream = SafeStreamingPLENGramEmbedding(cfg, st_idx, "model.layers.1.ple.ple_embedding")
        with torch.no_grad():
            ref_ple = model.model.layers[1].ple.ple_embedding(x_ids, None)
            direct_ple = ple_stream(x_ids, None)
            ple_stream.preindex_for_sequences([x_ids])
            pre_ple = ple_stream(x_ids, None)
        assert torch.equal(ref_ple, direct_ple), "SafeStreamingPLENGramEmbedding direct mismatch"
        assert torch.equal(ref_ple, pre_ple), "SafeStreamingPLENGramEmbedding preindex mismatch"

        h = model.model.embed_tokens(x_ids).unsqueeze(2).expand(1, 40, 4, 128).contiguous()
        ps = PreparedSample(0, "s0", 40, x_ids, None, SampleDomainFlags("en", "", False, False, False))
        for bid in range(3):
            ctx = SingleLayerContext(
                bid=bid,
                text_cfg=cfg,
                st_index=st_idx,
                rotary_emb=model.model.rotary_emb,
                backend="cpu",
                is_mtp=False,
                preindex_ple_inputs=[x_ids] if bid == 1 else None,
                skip_moe_experts=True,
            )
            assert ctx.layer.mlp.experts.gate_up_proj.device.type == "meta"
            moe_w = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend="cpu")
            h_mlp_in, hyper_ffn, inj_ffn = ctx.forward_pre_moe(h, ps)
            y_moe = forward_moe_v2(moe_w, h_mlp_in)
            h = ctx.combine_post_moe(y_moe, hyper_ffn, inj_ffn, hc_count=4, hidden_size=128)
            moe_w.close()
            ctx.close()

        with torch.no_grad():
            logits_stream = model.lm_head(model.model.hyper_connection_mixer(h.reshape(1, 40, -1)))
        cos_logits = float(
            torch.nn.functional.cosine_similarity(
                logits_stream.float().reshape(40, -1), out_ref.logits.float().reshape(40, -1), dim=-1
            ).mean().item()
        )
        assert cos_logits > 0.9999, f"Expected > 0.9999 3-layer logit cosine, got {cos_logits}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return {
        "moe_rel_l2_vs_fp64": round(float(fp64_chk["rel_l2_error"]), 7),
        "qsa_max_diff": qsa_max_diff,
        "ple_bit_exact": True,
        "three_layer_logit_cosine": round(cos_logits, 7),
    }


def test_04_selectors_real_donor_scores_and_exact_a4_prime_gram() -> Dict[str, Any]:
    from scripts.v2.common_io import SampleDomainFlags
    from scripts.v2.cupy_moe_backend import MoELayerWeights, ReapHopeRcoAccumulator, forward_moe_v2
    from scripts.v2.expert_selectors import (
        build_quota_locks,
        select_a1_open_reap,
        select_a2_quota_reap,
        select_a3_quota_hope,
        select_a4_prime_greedy_rco,
        verify_quota_invariants,
    )

    score_path = ROOT_DIR / "research" / "step6_raw" / "scores" / "layer_02.json"
    with open(score_path, "r", encoding="utf-8") as f:
        real_score = json.load(f)

    locks = build_quota_locks(real_score)
    rng = np.random.default_rng(123)
    # Synthetic PSD co-activation for testing A3 SLSQP on real 512E score_dict
    r_mat = rng.uniform(0.0, 0.1, size=(128, 512))
    coact_512 = r_mat.T @ r_mat

    for k_target in (320, 288):
        k_a1 = select_a1_open_reap(real_score, k_target)
        k_a2 = select_a2_quota_reap(real_score, k_target, locks=locks)
        k_a3 = select_a3_quota_hope(real_score, coact_512, k_target, locks=locks, maxiter=50)
        verify_quota_invariants(k_a1, locks=None, target_k=k_target, num_experts=512)
        verify_quota_invariants(k_a2, locks=locks, target_k=k_target, num_experts=512)
        verify_quota_invariants(k_a3, locks=locks, target_k=k_target, num_experts=512)
        assert len(set(k_a2.tolist()) & set(locks.dead_indices)) == 0
        assert len(set(k_a3.tolist()) & set(locks.dead_indices)) == 0

    # Exact A4' Gram backward elimination vs brute-force D-dimensional recomputation!
    n_exp, top_k, top_m, d_hid, inter, n_tok, k_goal = 20, 4, 14, 48, 24, 64, 12
    moe_syn = MoELayerWeights(
        gate_weight_f32=rng.standard_normal((n_exp, d_hid)).astype(np.float32) * 0.25,
        gate_up_fp16=rng.standard_normal((n_exp, 2 * inter, d_hid)).astype(np.float16) * 0.15,
        down_fp16=rng.standard_normal((n_exp, d_hid, inter)).astype(np.float16) * 0.15,
        sh_gate_fp16=rng.standard_normal((inter, d_hid)).astype(np.float16) * 0.1,
        sh_up_fp16=rng.standard_normal((inter, d_hid)).astype(np.float16) * 0.1,
        sh_down_fp16=rng.standard_normal((d_hid, inter)).astype(np.float16) * 0.1,
        sh_inp_gate_f32=rng.standard_normal((d_hid,)).astype(np.float32) * 0.1,
        top_k=top_k,
        backend="cpu",
    )
    x_syn = torch.from_numpy((rng.standard_normal((1, n_tok, d_hid)) * 0.5).astype(np.float32)).to(torch.bfloat16)
    acc = ReapHopeRcoAccumulator(
        num_experts=n_exp,
        top_k=top_k,
        collect_rco_cache=True,
        rco_top_m=top_m,
        rco_max_tokens=n_tok,
        rco_stride=1,
    )
    acc.set_sample_flags(SampleDomainFlags("ru_copy", "vis", True, True, True))
    _ = forward_moe_v2(moe_syn, x_syn, flat_token_ids=torch.ones((1, n_tok), dtype=torch.long), reap_acc=acc)
    syn_scores = acc.finalize_score_dict()
    syn_locks = build_quota_locks(syn_scores, wh_quota=3, ru_quota=2, craft_quota=2, vis_quota=1)
    assert acc.rco_cache is not None and acc.rco_cache.filled == n_tok

    keep_gram = select_a4_prime_greedy_rco(acc.rco_cache, syn_scores, target_k=k_goal, locks=syn_locks)

    # Brute-force reference using explicit D-dimensional vectors on the exact cached top-M experts
    x_np = x_syn.to(torch.float32).numpy().reshape(n_tok, d_hid)
    x_fp16_f32 = x_np.astype(np.float16).astype(np.float32)
    idx_m = acc.rco_cache.idx[:n_tok].astype(np.int64)
    probs_m = acc.rco_cache.probs[:n_tok].astype(np.float64)

    e_vecs = np.zeros((n_tok, top_m, d_hid), dtype=np.float64)
    for t in range(n_tok):
        for m_i in range(top_m):
            eid = int(idx_m[t, m_i])
            gu = x_fp16_f32[t : t + 1] @ moe_syn.gate_up[eid].astype(np.float32).T
            g_part = gu[:, :inter]
            act = (g_part / (1.0 + np.exp(-g_part))) * gu[:, inter:]
            dn = act.astype(np.float16).astype(np.float32) @ moe_syn.down[eid].astype(np.float32).T
            e_vecs[t, m_i] = dn[0].astype(np.float64)

    d_target = np.sum(
        (probs_m[:, :top_k] / np.sum(probs_m[:, :top_k], axis=1, keepdims=True))[:, :, None] * e_vecs[:, :top_k, :],
        axis=1,
    )

    def _brute_mse(kept_set: set[int]) -> float:
        err = 0.0
        for t in range(n_tok):
            sel_slots = [m_i for m_i in range(top_m) if int(idx_m[t, m_i]) in kept_set][:top_k]
            if not sel_slots:
                err += float(np.sum(d_target[t] ** 2))
            else:
                w = probs_m[t, sel_slots]
                w = w / np.sum(w)
                pred = np.sum(w[:, None] * e_vecs[t, sel_slots], axis=0)
                err += float(np.sum((pred - d_target[t]) ** 2))
        return err

    kept_bf = set(range(n_exp)) - set(syn_locks.dead_indices)
    reap_arr = np.asarray(syn_scores["arrays"]["reap_raw"], dtype=np.float64)
    while len(kept_bf) > k_goal:
        cands = sorted(kept_bf - set(syn_locks.locked_indices))
        errs = np.array([_brute_mse(kept_bf - {c}) for c in cands], dtype=np.float64)
        best = int(np.lexsort((-np.array(cands), reap_arr[cands], errs))[0])
        kept_bf.remove(cands[best])

    keep_bf_arr = np.array(sorted(kept_bf), dtype=np.int64)
    assert np.array_equal(keep_gram, keep_bf_arr), f"A4' Gram != brute force: {keep_gram} vs {keep_bf_arr}"

    return {
        "layer_02_locked_union": len(locks.locked_indices),
        "layer_02_dead_excluded": len(locks.dead_indices),
        "a4_prime_exact_match_bruteforce": True,
    }


def test_05_healing_c3_router_alpha_shexp_and_rejection_guard() -> Dict[str, Any]:
    from scripts.v2.cupy_moe_backend import MoELayerWeights, forward_moe_v2
    from scripts.v2.healing_c3 import fit_c1_router_gate, heal_layer_c3

    rng = np.random.default_rng(77)
    n_donor, n_keep, top_k, d_hid, inter, n_tok = 24, 14, 4, 48, 24, 320
    donor = MoELayerWeights(
        gate_weight_f32=rng.standard_normal((n_donor, d_hid)).astype(np.float32) * 0.3,
        gate_up_fp16=rng.standard_normal((n_donor, 2 * inter, d_hid)).astype(np.float16) * 0.2,
        down_fp16=rng.standard_normal((n_donor, d_hid, inter)).astype(np.float16) * 0.2,
        sh_gate_fp16=rng.standard_normal((inter, d_hid)).astype(np.float16) * 0.2,
        sh_up_fp16=rng.standard_normal((inter, d_hid)).astype(np.float16) * 0.2,
        sh_down_fp16=rng.standard_normal((d_hid, inter)).astype(np.float16) * 0.2,
        sh_inp_gate_f32=rng.standard_normal((d_hid,)).astype(np.float32) * 0.2,
        top_k=top_k,
        backend="cpu",
    )
    keep = np.arange(n_keep, dtype=np.int64)
    pruned = MoELayerWeights(
        gate_weight_f32=donor.gate_w[keep].copy(),
        gate_up_fp16=donor.gate_up[keep].copy(),
        down_fp16=donor.down[keep].copy(),
        sh_gate_fp16=donor.sh_gate.copy(),
        sh_up_fp16=donor.sh_up.copy(),
        sh_down_fp16=donor.sh_down.copy(),
        sh_inp_gate_f32=donor.sh_inp_gate.copy(),
        top_k=top_k,
        backend="cpu",
    )

    h_in = (rng.standard_normal((n_tok, d_hid)) * 0.6).astype(np.float32)
    y_donor = (
        forward_moe_v2(donor, torch.from_numpy(h_in).unsqueeze(0).to(torch.bfloat16))
        .to(torch.float32)
        .numpy()
        .reshape(n_tok, d_hid)
    )

    res = heal_layer_c3(pruned, h_in, y_donor, max_heal_tokens=n_tok, c1_max_steps=80)
    assert res.val_rel_l2_after_c3 <= res.val_rel_l2_before + 1e-6
    assert res.val_rel_l2_after_c3 < res.val_rel_l2_before, (
        f"Expected C3 healing to reduce held-out error: {res.val_rel_l2_before} -> {res.val_rel_l2_after_c3}"
    )
    assert np.all(res.alpha_scales >= 0.7 - 1e-6) and np.all(res.alpha_scales <= 1.4 + 1e-6)
    assert np.all(np.isfinite(res.w_gate_f32)) and np.all(np.isfinite(res.w_down_shexp_f32))

    # Test strict C1 >= 2% held-out validation guard: pure orthogonal noise on val must be rejected!
    y_noise = rng.standard_normal((n_tok, d_hid)).astype(np.float32) * 50.0
    w_out, accepted, _ = fit_c1_router_gate(
        pruned,
        h_train=h_in[:240],
        y_donor_train=y_noise[:240],
        h_val=h_in[240:],
        y_donor_val=y_noise[240:],
        max_steps=40,
        min_rel_val_drop=0.02,
    )
    assert not accepted, "C1 must reject router gate updates that fail >=2% held-out drop on noise"
    assert np.array_equal(w_out, pruned.gate_w), "Rejected C1 must return exact original W_0"

    return {
        "val_rel_l2_before": round(res.val_rel_l2_before, 6),
        "val_rel_l2_after_c3": round(res.val_rel_l2_after_c3, 6),
        "c1_noise_rejection_verified": True,
    }


def test_06_cleanroom_gsq_q2_0_bit_exact_vs_libggml() -> Dict[str, Any]:
    from scripts.v2.gsq_q2_0 import verify_q2_0_bit_exact_and_gsq_gain

    rep = verify_q2_0_bit_exact_and_gsq_gain(seed=42)
    assert rep["passed"], f"GSQ Q2_0 verification failed: {rep}"
    assert rep["bit_exact_clean_vs_libggml"] is True
    assert rep["bit_exact_gguf_py_vs_libggml"] is True
    assert rep["bit_exact_gsq_pack_vs_libggml"] is True
    assert rep["rel_l2_err_gsq_q2_0"] < rep["rel_l2_err_stock_q2_0"]
    return rep


def test_07_streaming_gguf_assembly_ple_reuse_and_gsq_splice() -> Dict[str, Any]:
    from transformers.models.qwen4_exp import (
        Qwen4ExpConfig,
        Qwen4ExpForConditionalGeneration,
        Qwen4ExpTextConfig,
    )
    from transformers.models.qwen4_exp.modeling_qwen4_exp import (
        Qwen4ExpTextDecoderLayer,
        Qwen4ExpTextGatedResidual,
        Qwen4ExpTextRMSNorm,
    )

    from scripts.v2.assemble_gguf import (
        GGML_TYPE_Q2_0,
        LayerPruneHealOverlay,
        assemble_bf16_intermediate_gguf,
        splice_gsq_q2_0_into_gguf,
    )
    from scripts.v2.gsq_q2_0 import (
        LibGGMLQuantSimulator,
        dequantize_q2_0_cleanroom,
        gsq_quantize_layer_down_exps,
    )
    from scripts.v2.model_runner import build_mtp_decoder_config

    tmp = Path(tempfile.mkdtemp(prefix="test_v2_gguf_", dir="/tmp"))
    try:
        torch.manual_seed(99)
        tcfg = Qwen4ExpTextConfig(
            vocab_size=256,
            hidden_size=128,
            num_hidden_layers=2,
            num_attention_heads=4,
            num_key_value_heads=2,
            head_dim=32,
            linear_num_key_heads=2,
            linear_num_value_heads=4,
            linear_key_head_dim=32,
            linear_value_head_dim=32,
            linear_conv_kernel_dim=4,
            moe_intermediate_size=64,
            shared_expert_intermediate_size=64,
            num_experts=16,
            num_experts_per_tok=4,
            layer_types=["linear_attention", "indexed_attention"],
            hc_count=4,
            hc_lowrank=16,
            ple_layer_ids=[1],
            ple_embed_dim=128,
            ple_conv_kernel_size=2,
            ngram_size=2,
            heads_per_ngram=2,
            ngram_vocab_size_base=256,
            split_ngram_parts=2,
            indexer_n_heads=2,
            indexer_kv_heads=1,
            indexer_head_dim=32,
            indexer_budget=8,
            indexer_compress_ratio=4,
            eos_token_id=2,
        )
        full_cfg = Qwen4ExpConfig(text_config=tcfg)
        full_model = Qwen4ExpForConditionalGeneration(full_cfg).to(torch.bfloat16).eval()

        # Build miniature donor checkpoint directory (2 trunk layers + 1 MTP layer + 2 PLE shards)
        donor_dir = tmp / "mini_donor"
        donor_dir.mkdir(parents=True, exist_ok=True)
        sd: Dict[str, torch.Tensor] = {}
        for k, v in full_model.state_dict().items():
            if k.startswith("model.visual."):
                continue
            sd[k] = v.contiguous()

        ple_key = "model.language_model.layers.0.ple.ple_embedding.ngram_embedding.weight"
        ple_full = sd.pop(ple_key)
        ple_rows, ple_dim = int(ple_full.shape[0]), int(ple_full.shape[1])
        assert ple_dim == 64  # ple_embed_dim (128) // heads (2) == 64 (multiple of 32 for Q4_0!)
        half_r = ple_rows // 2
        ple_s0 = {f"model.language_model.layers.0.ple.ple_embedding.ngram_embedding.shard_0.weight": ple_full[:half_r].contiguous()}
        ple_s1 = {f"model.language_model.layers.0.ple.ple_embedding.ngram_embedding.shard_1.weight": ple_full[half_r:].contiguous()}

        # Add MTP block (blk.2) matching Qwen3.8-Flash-Next checkpoint schema
        mtp_cfg = build_mtp_decoder_config(tcfg)
        mtp_layer = Qwen4ExpTextDecoderLayer(mtp_cfg, layer_idx=0).to(torch.bfloat16)
        for mk, mv in mtp_layer.state_dict().items():
            sd[f"mtp.layers.0.{mk}"] = mv.contiguous()
        sd["mtp.pre_fc_norm_embedding.weight"] = Qwen4ExpTextRMSNorm(128).weight.detach().to(torch.bfloat16).clone()
        sd["mtp.pre_fc_norm_hidden.weight"] = Qwen4ExpTextRMSNorm(512, group_size=128).weight.detach().to(torch.bfloat16).clone()
        sd["mtp.fc_embedding.weight"] = torch.randn(128, 128, dtype=torch.bfloat16) * 0.02
        sd["mtp.fc_hidden.weight"] = torch.randn(128, 128, dtype=torch.bfloat16) * 0.02
        mtp_hm = Qwen4ExpTextGatedResidual(mtp_cfg, use_combine=False).to(torch.bfloat16)
        for mk, mv in mtp_hm.state_dict().items():
            sd[f"mtp.hyper_connection_mixer.{mk}"] = mv.contiguous()

        save_file(sd, str(donor_dir / "model-00001-of-00003.safetensors"))
        save_file(ple_s0, str(donor_dir / "model-00002-of-00003.safetensors"))
        save_file(ple_s1, str(donor_dir / "model-00003-of-00003.safetensors"))
        wmap = {k: "model-00001-of-00003.safetensors" for k in sd}
        wmap.update({k: "model-00002-of-00003.safetensors" for k in ple_s0})
        wmap.update({k: "model-00003-of-00003.safetensors" for k in ple_s1})
        (donor_dir / "model.safetensors.index.json").write_text(json.dumps({"metadata": {}, "weight_map": wmap}))

        cfg_dict = full_cfg.to_dict()
        cfg_dict["architectures"] = ["Qwen4ExpForConditionalGeneration"]
        cfg_dict["text_config"]["num_nextn_predict_layers"] = 1
        (donor_dir / "config.json").write_text(json.dumps(cfg_dict, indent=2))

        # Build miniature reference GGUF holding Q4_0 PLE + tokenizer.ggml.* KV metadata
        ref_gguf = tmp / "mini_ref_ple_vocab.gguf"
        gw_ref = gguf.GGUFWriter(str(ref_gguf), arch="qwen4exp")
        gw_ref.add_tokenizer_model("gpt2")
        gw_ref.add_token_list([f"tok_{i}" for i in range(256)])
        gw_ref.add_token_types([1] * 256)
        gw_ref.add_eos_token_id(2)
        rng_np = np.random.default_rng(314)
        q4_ple_bytes = rng_np.integers(0, 256, size=(ple_rows, (ple_dim // 32) * 18), dtype=np.uint8)
        gw_ref.add_tensor(
            "per_layer_token_embd.weight",
            q4_ple_bytes,
            raw_dtype=gguf.GGMLQuantizationType.Q4_0,
        )
        gw_ref.write_header_to_file()
        gw_ref.write_kv_data_to_file()
        gw_ref.write_tensors_to_file()
        gw_ref.close()

        # Create pruning + C3 heal overlays for trunk (0, 1) and MTP (2): 16 -> 8 experts
        target_k = 8
        keep_idx = np.array([0, 2, 4, 5, 7, 10, 12, 15], dtype=np.int64)
        custom_gate_0 = rng_np.standard_normal((target_k, 128)).astype(np.float32) * 0.11
        custom_alpha_0 = np.linspace(0.8, 1.3, target_k, dtype=np.float32)
        custom_shdown_0 = rng_np.standard_normal((128, 64)).astype(np.float32) * 0.07
        overlays = {
            0: LayerPruneHealOverlay(0, keep_idx, custom_gate_0, custom_alpha_0, custom_shdown_0),
            1: LayerPruneHealOverlay(1, keep_idx, None, np.ones(target_k, dtype=np.float32), None),
            2: LayerPruneHealOverlay(2, keep_idx, None, np.ones(target_k, dtype=np.float32), None),
        }

        bf16_gguf = assemble_bf16_intermediate_gguf(
            out_gguf_path=tmp / "mini_pruned_bf16.gguf",
            target_k=target_k,
            overlays=overlays,
            donor_dir=donor_dir,
            reuse_ple_gguf=ref_gguf,
            reuse_vocab_gguf=ref_gguf,
            model_name="Mini-SmartLLM-Test",
        )

        r_bf16 = gguf.GGUFReader(str(bf16_gguf), "r")
        exp_cnt = int(r_bf16.fields["qwen4exp.expert_count"].parts[r_bf16.fields["qwen4exp.expert_count"].data[0]][0])
        assert exp_cnt == target_k, f"Expected expert_count={target_k}, got {exp_cnt}"

        t_map = {t.name: t for t in r_bf16.tensors}
        for bid in (0, 1, 2):
            assert f"blk.{bid}.ffn_down_exps.weight" in t_map
            # GGUF shape order is [ne0=inter(64), ne1=hidden(128), ne2=K(8)] and BF16 dtype
            assert list(t_map[f"blk.{bid}.ffn_down_exps.weight"].shape) == [64, 128, target_k]
            assert t_map[f"blk.{bid}.ffn_down_exps.weight"].tensor_type == gguf.GGMLQuantizationType.BF16

        # Verify custom healed W_gate on blk.0
        gate_gguf = np.frombuffer(t_map["blk.0.ffn_gate_inp.weight"].data.tobytes(), dtype=np.float32).reshape(target_k, 128)
        np.testing.assert_allclose(gate_gguf, custom_gate_0, atol=1e-6)

        # Verify verbatim Q4_0 PLE byte-for-byte streaming reuse + real 205E GGUF <=2MB header check
        assert t_map["per_layer_token_embd.weight"].tensor_type == gguf.GGMLQuantizationType.Q4_0
        assert t_map["per_layer_token_embd.weight"].data.tobytes() == q4_ple_bytes.tobytes()
        from scripts.v2.assemble_gguf import locate_tensor_in_gguf
        from scripts.v2.common_io import REF_205E_GGUF

        if REF_205E_GGUF.is_file():
            ple_off, ple_ne, ple_qt, ple_nb = locate_tensor_in_gguf(REF_205E_GGUF, "per_layer_token_embd.weight")
            assert ple_off > 0 and ple_qt == gguf.GGMLQuantizationType.Q4_0
            assert ple_ne == (160, 320001536) and ple_nb == 28_800_138_240

        # Test BF16 .complete.json marker verification (OPUS Audit #90 Item 5)
        from scripts.v2.assemble_gguf import verify_bf16_gguf_complete_marker

        assert verify_bf16_gguf_complete_marker(bf16_gguf, expected_target_k=target_k) is True
        assert verify_bf16_gguf_complete_marker(bf16_gguf, expected_target_k=target_k + 1) is False

        # Test clean-room GSQ Q2_0 quantization + semantic splice check (OPUS Audit #90 Item 1) + libggml verification!
        sim = LibGGMLQuantSimulator()
        w_down_test = rng_np.standard_normal((target_k, 128, 64)).astype(np.float32) * 0.25
        stock_q2_bytes = sim.quantize_2d(w_down_test.reshape(target_k * 128, 64), GGML_TYPE_Q2_0).reshape(
            target_k, 128, (64 // 64) * 18
        )
        q2_gguf = tmp / "mini_q2_splice_target.gguf"
        gw_q2 = gguf.GGUFWriter(str(q2_gguf), arch="qwen4exp")
        gw_q2.add_tensor(
            "blk.0.ffn_down_exps.weight",
            stock_q2_bytes,
            raw_dtype=gguf.GGMLQuantizationType.Q2_0,
        )
        gw_q2.write_header_to_file()
        gw_q2.write_kv_data_to_file()
        gw_q2.write_tensors_to_file()
        gw_q2.close()

        packed_q2, dq_q2_all = gsq_quantize_layer_down_exps(w_down_test, hessians_fn=None)
        packed_q2_fn, dq_none = gsq_quantize_layer_down_exps(
            lambda k: w_down_test[k], hessians_fn=None, num_experts=target_k, return_dequant=False
        )
        assert dq_none is None and np.array_equal(packed_q2, packed_q2_fn)
        assert dq_q2_all is not None

        # Negative test 1a: Expert-misordered Q2_0 payload must be REJECTED BEFORE pwrite, leaving stock intact!
        misordered_rejected = False
        try:
            _ = splice_gsq_q2_0_into_gguf(q2_gguf, {0: packed_q2[::-1].copy()}, verify_with_libggml=True)
        except ValueError as exc:
            misordered_rejected = "Semantic splice check FAILED" in str(exc)
        assert misordered_rejected, "Expected reversed expert order to fail semantic splice check!"

        # Negative test 1b: Transposed [inter=64, hidden=128] Q2_0 payload (same byte count!) must ALSO be REJECTED!
        w_transposed = np.ascontiguousarray(w_down_test.transpose(0, 2, 1))  # [target_k, 64, 128]
        packed_q2_transposed, _ = gsq_quantize_layer_down_exps(w_transposed, hessians_fn=None)
        transposed_rejected = False
        try:
            _ = splice_gsq_q2_0_into_gguf(q2_gguf, {0: packed_q2_transposed}, verify_with_libggml=True)
        except ValueError as exc:
            transposed_rejected = "Semantic splice check FAILED" in str(exc)
        assert transposed_rejected, "Expected transposed [64x128] payload to fail semantic splice check!"

        # Verify stock bytes in q2_gguf are STILL 100% untouched after both rejected splices!
        r_untouched = gguf.GGUFReader(str(q2_gguf), "r")
        assert np.array_equal(
            np.frombuffer(r_untouched.tensors[0].data.tobytes(), dtype=np.uint8),
            stock_q2_bytes.reshape(-1),
        )

        # Positive splice check: properly oriented GSQ Q2_0 passes semantic cos vs stock (>= 0.55) AND vs BF16 (>= 0.90)!
        q2_bf16_ref = tmp / "mini_bf16_ref.gguf"
        gw_b16 = gguf.GGUFWriter(str(q2_bf16_ref), arch="qwen4exp")
        gw_b16.add_tensor(
            "blk.0.ffn_down_exps.weight",
            gguf.quants.quantize(w_down_test, gguf.GGMLQuantizationType.BF16),
            raw_dtype=gguf.GGMLQuantizationType.BF16,
        )
        gw_b16.write_header_to_file()
        gw_b16.write_kv_data_to_file()
        gw_b16.write_tensors_to_file()
        gw_b16.close()

        gsq_rel_l2 = float(np.linalg.norm(w_down_test - dq_q2_all) / max(np.linalg.norm(w_down_test), 1e-12))
        sp_res = splice_gsq_q2_0_into_gguf(
            q2_gguf,
            {0: packed_q2},
            verify_with_libggml=True,
            ref_bf16_gguf=q2_bf16_ref,
            min_bf16_cosine=0.90,
        )
        assert sp_res["spliced_layers"] == 1
        assert sp_res["min_semantic_expert_cosine"] >= 0.55
        assert sp_res["min_semantic_bf16_cosine"] >= 0.90

        r_q2 = gguf.GGUFReader(str(q2_gguf), "r")
        spliced_u8 = np.frombuffer(r_q2.tensors[0].data.tobytes(), dtype=np.uint8)
        assert np.array_equal(spliced_u8, packed_q2.reshape(-1))
        dq_c = sim.dequantize_bytes(spliced_u8, GGML_TYPE_Q2_0, n_elems=target_k * 128 * 64)
        dq_py = dequantize_q2_0_cleanroom(spliced_u8)
        assert np.array_equal(dq_c.view(np.uint32), dq_py.view(np.uint32))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return {
        "assembled_tensors": len(t_map),
        "ple_q4_0_verbatim_bytes": int(q4_ple_bytes.nbytes),
        "gsq_spliced_bytes": int(sp_res["total_bytes_written"]),
        "gsq_mean_rel_l2": round(gsq_rel_l2, 6),
    }


def test_08_shootout_decision_engines_and_prequant_gates() -> Dict[str, Any]:
    from scripts.v2.prequant_gate import (
        BF16_PREQUANT_THRESHOLDS,
        compute_kl_and_top1_from_hidden,
        compute_non_code_cyrillic_ratio,
        count_8gram_x3_loops,
        evaluate_teacher_forced_gate,
        load_sanity_prompts_10,
    )
    from scripts.v2.wave2_shootout import (
        check_r320_a2_overfitting_control,
        decide_stage_2a_winner,
        decide_stage_2b_winner,
    )
    from scripts.v2.wave3_full_run import check_layer4_throughput_guard

    # Stage 2a: A3 has only 2.0% gain (<3% threshold) -> A2 wins; at K=288 A4' has 6.0% gain & <=1.15 ratio -> A4' wins
    mock_2a = {}
    for k_val, a4_scale in ((320, 0.98), (288, 0.94)):
        mock_2a[k_val] = {
            "A1": {"per_layer": {str(l): {"r_en": 0.10, "r_ru": 0.16} for l in (2, 14, 28, 42)}, "quota_locked_100pct": False},
            "A2": {"per_layer": {str(l): {"r_en": 0.10, "r_ru": 0.12} for l in (2, 14, 28, 42)}, "quota_locked_100pct": True},
            "A3": {"per_layer": {str(l): {"r_en": 0.098, "r_ru": 0.118} for l in (2, 14, 28, 42)}, "quota_locked_100pct": True},
            "A4_prime": {"per_layer": {str(l): {"r_en": 0.10 * a4_scale, "r_ru": 0.12 * a4_scale} for l in (2, 14, 28, 42)}, "quota_locked_100pct": True},
        }
    d2a = decide_stage_2a_winner(mock_2a)
    assert d2a["by_k"][320]["winner_selector"] == "A2"
    assert d2a["by_k"][288]["winner_selector"] == "A4_prime"
    assert d2a["global_winner_selector"] == "A2" and not d2a["escalate_opus"]

    # OPUS §1.D2a Ruling test: A3 fails beats_a1_ru (disqualified), while A2 & A4_prime pass -> A4_prime wins without escalation!
    mock_2a_a3_disq = {}
    for k_val in (320, 288):
        mock_2a_a3_disq[k_val] = {
            "A1": {"per_layer": {str(l): {"r_en": 0.28, "r_ru": 0.30} for l in (2, 14, 28, 42)}, "quota_locked_100pct": True},
            "A2": {"per_layer": {str(l): {"r_en": 0.288, "r_ru": 0.298} for l in (2, 14, 28, 42)}, "quota_locked_100pct": True},
            "A3": {"per_layer": {str(l): {"r_en": 0.61, "r_ru": 0.48} for l in (2, 14, 28, 42)}, "quota_locked_100pct": True},
            "A4_prime": {"per_layer": {str(l): {"r_en": 0.26, "r_ru": 0.24} for l in (2, 14, 28, 42)}, "quota_locked_100pct": True},
        }
    d2a_disq = decide_stage_2a_winner(mock_2a_a3_disq)
    assert d2a_disq["by_k"][320]["arms"]["A3"]["eligible"] is False
    assert d2a_disq["by_k"][320]["a2_quota_locks_healthy"] is True
    assert d2a_disq["global_winner_selector"] == "A4_prime" and d2a_disq["escalate_opus"] is False

    # Conversely, if A2 itself fails beats_a1_ru, quota-lock health fails -> escalate_opus MUST be True!
    mock_2a_a2_broken = {
        320: {
            **mock_2a_a3_disq[320],
            "A2": {"per_layer": {str(l): {"r_en": 0.29, "r_ru": 0.32} for l in (2, 14, 28, 42)}, "quota_locked_100pct": True},
        },
        288: mock_2a_a3_disq[288],
    }
    d2a_broken = decide_stage_2a_winner(mock_2a_a2_broken)
    assert d2a_broken["escalate_opus"] is True and d2a_broken["global_winner_selector"] is None

    # OPUS §1.D2a Ruling R320_A2 overfitting control test:
    ctrl_ok = check_r320_a2_overfitting_control(
        {"kl_en": 0.008, "kl_ru": 0.011, "top1_en": 0.988, "top1_ru": 0.984},
        {"kl_en": 0.010, "kl_ru": 0.014, "top1_en": 0.985, "top1_ru": 0.980},
        primary_selector="A4_prime",
    )
    assert ctrl_ok["a4_prime_beats_a2_splice"] is True
    assert ctrl_ok["overfit_control_triggered"] is False
    assert ctrl_ok["effective_selector"] == "A4_prime"

    ctrl_trig = check_r320_a2_overfitting_control(
        {"kl_en": 0.011, "kl_ru": 0.015, "top1_en": 0.983, "top1_ru": 0.979},
        {"kl_en": 0.010, "kl_ru": 0.014, "top1_en": 0.985, "top1_ru": 0.980},
        primary_selector="A4_prime",
    )
    assert ctrl_trig["a4_prime_beats_a2_splice"] is False
    assert ctrl_trig["overfit_control_triggered"] is True
    assert ctrl_trig["effective_selector"] == "A2"

    # Stage 2b Case A: V1 has >2x V4's quant-added KL -> B1 rejects Q2_0 outright => V4 wins
    mock_2b_b1_fail = {
        "R320": {"kl_en": 0.010, "kl_ru": 0.015, "top1_en": 0.985, "top1_ru": 0.980},
        "R288": {"kl_en": 0.013, "kl_ru": 0.018, "top1_en": 0.980, "top1_ru": 0.975},
        "V4": {"kl_en": 0.025, "kl_ru": 0.035, "top1_en": 0.950, "top1_ru": 0.940},
        "V1": {"kl_en": 0.055, "kl_ru": 0.070, "top1_en": 0.910, "top1_ru": 0.890},
        "V2": {"kl_en": 0.020, "kl_ru": 0.028, "top1_en": 0.962, "top1_ru": 0.952},
        "V3": {"kl_en": 0.023, "kl_ru": 0.032, "top1_en": 0.955, "top1_ru": 0.945},
    }
    d2b_fail = decide_stage_2b_winner(mock_2b_b1_fail)
    assert d2b_fail["b1_q2_0_global_valid"] is False
    assert d2b_fail["winner_variant"] == "V4"

    # Stage 2b Case B: B1 Q2_0 valid; V1 (kl_mix=0.0202) within 5% of V2 (kl_mix=0.0196) -> 5% tie-break picks V1!
    mock_2b = {
        "R320": {"kl_en": 0.010, "kl_ru": 0.014, "top1_en": 0.986, "top1_ru": 0.981},
        "R288": {"kl_en": 0.013, "kl_ru": 0.018, "top1_en": 0.980, "top1_ru": 0.975},
        "V4": {"kl_en": 0.025, "kl_ru": 0.035, "top1_en": 0.950, "top1_ru": 0.940},
        "V1": {"kl_en": 0.018, "kl_ru": 0.0235, "top1_en": 0.975, "top1_ru": 0.968},
        "V2": {"kl_en": 0.0175, "kl_ru": 0.02275, "top1_en": 0.976, "top1_ru": 0.969},
        "V3": {"kl_en": 0.021, "kl_ru": 0.028, "top1_en": 0.970, "top1_ru": 0.960},
    }
    d2b = decide_stage_2b_winner(mock_2b)
    assert d2b["r320_splice_gate_passed"] is True
    assert d2b["b1_q2_0_global_valid"] is True
    assert d2b["winner_variant"] == "V1"

    # OPUS §1.D2b.1 Ruling test: R320 misses 97% top-1 slightly (0.946 >= 0.75 * 0.97 = 0.7275) & kl_mix <= 0.025
    mock_2b_r320_near = {
        **mock_2b,
        "R320": {"kl_en": 0.018616, "kl_ru": 0.027494, "top1_en": 0.951461, "top1_ru": 0.937763},
    }
    d2b_near = decide_stage_2b_winner(mock_2b_r320_near)
    assert d2b_near["r320_splice_gate_passed"] is False
    assert d2b_near["r320_within_25pct_band"] is True
    assert str(d2b_near["escalation_reason"]).startswith("MISS_LE_25PCT:")

    mock_2b_r320_far = {
        **mock_2b,
        "R320": {"kl_en": 0.018616, "kl_ru": 0.027494, "top1_en": 0.710, "top1_ru": 0.700},
    }
    d2b_far = decide_stage_2b_winner(mock_2b_r320_far)
    assert d2b_far["r320_within_25pct_band"] is False
    assert str(d2b_far["escalation_reason"]).startswith("MISS_GT_25PCT_STOP:")

    # Throughput guard check (OPUS §1.D2b.3: 10.0 h ceiling)
    g_fast = check_layer4_throughput_guard([600.0] * 5, total_layers=49)
    assert g_fast["limit_hours"] == 10.0 and not g_fast["triggered"] and g_fast["fallback_calib_seqs"] == 448
    g_slow = check_layer4_throughput_guard([800.0] * 5, total_layers=49)
    assert g_slow["limit_hours"] == 10.0 and g_slow["triggered"] and g_slow["fallback_calib_seqs"] == 448

    # KL from hidden + 8-gram loop + non-code Cyrillic checks
    rng = np.random.default_rng(11)
    h_d = rng.standard_normal((16, 32)).astype(np.float32)
    w_lm = rng.standard_normal((64, 32)).astype(np.float16)
    kl_zero, t1_id, n_t = compute_kl_and_top1_from_hidden(h_d, h_d, w_lm, backend="cpu")
    assert abs(kl_zero) < 1e-6 and t1_id == 16 and n_t == 16

    clean_ru = (
        "Чистая типографика строится на контрасте кегля и предсказуемом ритме отступов.\n"
        "```css\n.hero-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 1.5rem; }\n```\n"
        "Каждая карточка сохраняет воздух и не перегружает взгляд читателя."
    )
    cyr_ratio, alpha_cnt = compute_non_code_cyrillic_ratio(clean_ru)
    assert cyr_ratio >= 0.98 and alpha_cnt > 20
    assert count_8gram_x3_loops(clean_ru) == 0

    loop_txt = " ".join(["один два три четыре пять шесть семь восемь"] * 3)
    assert count_8gram_x3_loops(loop_txt) > 0

    gate_ev = evaluate_teacher_forced_gate(
        en_kl_sum=4.0,
        en_top1_hits=93.0,
        en_tokens=100,
        ru_kl_sum=6.0,
        ru_top1_hits=90.0,
        ru_tokens=100,
        layer_cosines=[0.996, 0.991],
        thresholds=BF16_PREQUANT_THRESHOLDS,
    )
    assert gate_ev["passed"] is True

    p10 = load_sanity_prompts_10()
    assert len(p10) == 10 and sum(1 for p in p10 if p["lang"] == "ru") == 5

    return {
        "stage2a_320": d2a["by_k"][320]["winner_selector"],
        "stage2a_288": d2a["by_k"][288]["winner_selector"],
        "stage2b_winner": d2b["winner_variant"],
        "ru_noncode_cyrillic_ratio": round(cyr_ratio, 4),
        "loaded_gen_prompts_10": len(p10),
    }


def test_09_per_layer_resume_and_determinism_probe() -> Dict[str, Any]:
    from transformers.models.qwen4_exp import Qwen4ExpForCausalLM, Qwen4ExpTextConfig

    from scripts.v2.common_io import (
        STAGE_DIR,
        ResumableFlatSequenceStore,
        ResumablePingPong,
        SafetensorsIndex,
        SampleDomainFlags,
        append_gpu_resume_log,
        compare_files_byte_equal,
    )
    from scripts.v2.cupy_moe_backend import MoELayerWeights, forward_moe_v2
    from scripts.v2.healing_c3 import C3HealResult
    from scripts.v2.model_runner import (
        PreparedSample,
        SingleLayerContext,
        run_layer_resume_determinism_probe,
    )
    from scripts.v2.wave2_shootout import (
        _load_wave2_pass1_checkpoint,
        _save_wave2_pass1_checkpoint,
    )

    tmp = Path(tempfile.mkdtemp(prefix="test_v2_resume_", dir="/tmp"))
    try:
        # 1. Exact byte-size guard on ResumableFlatSequenceStore (create=False)
        bin_ok = tmp / "store_exact.bin"
        st_create = ResumableFlatSequenceStore(bin_ok, [4, 6], hc_count=4, hidden_size=32, create=True)
        assert bin_ok.stat().st_size == st_create.total_bytes
        _ = ResumableFlatSequenceStore(bin_ok, [4, 6], hc_count=4, hidden_size=32, create=False)

        bin_bad = tmp / "store_truncated.bin"
        shutil.copyfile(bin_ok, bin_bad)
        with open(bin_bad, "r+b") as bf:
            bf.truncate(st_create.total_bytes - 16)
        size_guard_triggered = False
        try:
            _ = ResumableFlatSequenceStore(bin_bad, [4, 6], hc_count=4, hidden_size=32, create=False)
        except ValueError as exc:
            size_guard_triggered = "byte-size mismatch" in str(exc)
        assert size_guard_triggered, "Expected ValueError on truncated sequence store!"

        # 2. Byte-equality helper check
        bin_copy = tmp / "store_copy.bin"
        shutil.copyfile(bin_ok, bin_copy)
        assert compare_files_byte_equal(bin_ok, bin_copy) is True
        with open(bin_copy, "r+b") as cf:
            cf.seek(0)
            b0 = cf.read(1)
            cf.seek(0)
            cf.write(bytes([b0[0] ^ 0xFF]))
        assert compare_files_byte_equal(bin_ok, bin_copy) is False

        # 3. 3-layer miniature Qwen4Exp model: uninterrupted vs per-layer resume + determinism probes
        torch.manual_seed(2026)
        cfg = Qwen4ExpTextConfig(
            vocab_size=256,
            hidden_size=64,
            num_hidden_layers=3,
            num_attention_heads=4,
            num_key_value_heads=2,
            head_dim=16,
            linear_num_key_heads=2,
            linear_num_value_heads=4,
            linear_key_head_dim=16,
            linear_value_head_dim=16,
            linear_conv_kernel_dim=4,
            moe_intermediate_size=32,
            shared_expert_intermediate_size=32,
            num_experts=12,
            num_experts_per_tok=4,
            layer_types=["linear_attention", "linear_attention", "indexed_attention"],
            hc_count=4,
            hc_lowrank=8,
            ple_layer_ids=[2],
            ple_embed_dim=64,
            ple_conv_kernel_size=2,
            ngram_size=2,
            heads_per_ngram=2,
            ngram_vocab_size_base=256,
            split_ngram_parts=2,
            indexer_n_heads=2,
            indexer_kv_heads=1,
            indexer_head_dim=16,
            indexer_budget=8,
            indexer_compress_ratio=4,
            eos_token_id=2,
        )
        cfg._attn_implementation = "sdpa"
        model = Qwen4ExpForCausalLM(cfg).to(torch.bfloat16).eval()

        donor_dir = tmp / "donor"
        donor_dir.mkdir(parents=True, exist_ok=True)
        sd = model.state_dict()
        ple_w = sd.pop("model.layers.1.ple.ple_embedding.ngram_embedding.weight")
        half = ple_w.shape[0] // 2
        s0 = {"model.layers.1.ple.ple_embedding.ngram_embedding.shard_0.weight": ple_w[:half].contiguous()}
        s1 = {"model.layers.1.ple.ple_embedding.ngram_embedding.shard_1.weight": ple_w[half:].contiguous()}
        save_file(sd, str(donor_dir / "model-00001-of-00003.safetensors"))
        save_file(s0, str(donor_dir / "model-00002-of-00003.safetensors"))
        save_file(s1, str(donor_dir / "model-00003-of-00003.safetensors"))
        wmap = {k: "model-00001-of-00003.safetensors" for k in sd}
        wmap.update({k: "model-00002-of-00003.safetensors" for k in s0})
        wmap.update({k: "model-00003-of-00003.safetensors" for k in s1})
        (donor_dir / "model.safetensors.index.json").write_text(json.dumps({"metadata": {}, "weight_map": wmap}))
        st_idx = SafetensorsIndex(donor_dir, drop_cache=True)

        calib_samples = [
            PreparedSample(0, "c0", 12, torch.randint(3, 250, (1, 12)), None, SampleDomainFlags("en", "", False, False, False)),
            PreparedSample(1, "c1", 16, torch.randint(3, 250, (1, 16)), None, SampleDomainFlags("ru", "", True, True, False)),
        ]
        eval_samples = [
            PreparedSample(0, "e0", 14, torch.randint(3, 250, (1, 14)), None, SampleDomainFlags("ru", "", True, False, False)),
        ]

        def _forward_layer_all(bid: int, c_in: Any, c_out: Any, e_in: Any, e_out: Any) -> None:
            ple_in = [s.input_ids for s in calib_samples] + [s.input_ids for s in eval_samples]
            ctx = SingleLayerContext(
                bid=bid, text_cfg=cfg, st_index=st_idx, rotary_emb=model.model.rotary_emb,
                backend="cpu", is_mtp=False, preindex_ple_inputs=ple_in if bid == 1 else None,
            )
            moe_d = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend="cpu")
            for s in calib_samples:
                hm, hyp, inj = ctx.forward_pre_moe(c_in.read_seq(s.idx), s)
                yd = forward_moe_v2(moe_d, hm)
                c_out.write_seq(s.idx, ctx.combine_post_moe(yd, hyp, inj, hc_count=4, hidden_size=64))
            for s in eval_samples:
                hm, hyp, inj = ctx.forward_pre_moe(e_in.read_seq(s.idx), s)
                yd = forward_moe_v2(moe_d, hm)
                e_out.write_seq(s.idx, ctx.combine_post_moe(yd, hyp, inj, hc_count=4, hidden_size=64))
            moe_d.close()
            ctx.close()

        # Uninterrupted reference run (layers 0 -> 1 -> 2)
        ref_dir = tmp / "ref_stage"
        c_pp_ref = ResumablePingPong(ref_dir, "calib_donor", [12, 16], hc_count=4, hidden_size=64)
        e_pp_ref = ResumablePingPong(ref_dir, "eval_donor", [14], hc_count=4, hidden_size=64)
        ca_ref, cb_ref = c_pp_ref.open_slot("A", create=True), c_pp_ref.open_slot("B", create=True)
        ea_ref, eb_ref = e_pp_ref.open_slot("A", create=True), e_pp_ref.open_slot("B", create=True)
        with torch.no_grad():
            for s in calib_samples:
                ca_ref.write_seq(s.idx, model.model.embed_tokens(s.input_ids).unsqueeze(2).expand(1, s.seq_len, 4, 64).contiguous())
            for s in eval_samples:
                ea_ref.write_seq(s.idx, model.model.embed_tokens(s.input_ids).unsqueeze(2).expand(1, s.seq_len, 4, 64).contiguous())

        _forward_layer_all(0, ca_ref, cb_ref, ea_ref, eb_ref)
        _forward_layer_all(1, cb_ref, ca_ref, eb_ref, ea_ref)

        # Copy post-blk.01 state to resume_stage before running blk.02 on reference
        res_dir = tmp / "resume_stage"
        res_dir.mkdir(parents=True, exist_ok=True)
        for fn in ("calib_donor_slot_A.bin", "calib_donor_slot_B.bin", "eval_donor_slot_A.bin", "eval_donor_slot_B.bin"):
            shutil.copyfile(ref_dir / fn, res_dir / fn)
        shutil.copyfile(res_dir / "eval_donor_slot_A.bin", res_dir / "eval_pre_canon_slot_A.bin")

        # Finish layer 2 on reference (ca_ref -> cb_ref)
        _forward_layer_all(2, ca_ref, cb_ref, ea_ref, eb_ref)

        # Resume Stage Test 3a: 'prev_slot' determinism probe on completed_layer=1 (slot_B -> slot_A)
        c_pp_res = ResumablePingPong(res_dir, "calib_donor", [12, 16], hc_count=4, hidden_size=64)
        e_pp_res = ResumablePingPong(res_dir, "eval_donor", [14], hc_count=4, hidden_size=64)
        ca_res, cb_res = c_pp_res.open_slot("A", create=False), c_pp_res.open_slot("B", create=False)
        ea_res, eb_res = e_pp_res.open_slot("A", create=False), e_pp_res.open_slot("B", create=False)

        probe_prev = run_layer_resume_determinism_probe(
            mode="prev_slot",
            probe_bid=1,
            text_cfg=cfg,
            st_index=st_idx,
            rotary_emb=model.model.rotary_emb,
            backend="cpu",
            calib_samples=calib_samples,
            eval_samples=eval_samples,
            c_in_store=cb_res,
            e_in_store=eb_res,
            c_expected_out_store=ca_res,
            e_expected_out_store=ea_res,
        )
        assert probe_prev["passed"] and probe_prev["max_rel_l2"] <= 1e-3

        # Corrupting stored output in slot_A must fail 'prev_slot' probe!
        orig_e0 = ea_res.read_seq(0)
        ea_res.write_seq(0, orig_e0 + 5.0)
        corrupt_caught = False
        try:
            _ = run_layer_resume_determinism_probe(
                mode="prev_slot",
                probe_bid=1,
                text_cfg=cfg,
                st_index=st_idx,
                rotary_emb=model.model.rotary_emb,
                backend="cpu",
                calib_samples=calib_samples,
                eval_samples=eval_samples,
                c_in_store=cb_res,
                e_in_store=eb_res,
                c_expected_out_store=ca_res,
                e_expected_out_store=ea_res,
            )
        except RuntimeError as exc:
            corrupt_caught = "Resume determinism probe FAILED" in str(exc)
        assert corrupt_caught, "Expected corrupted slot_A to fail prev_slot determinism probe!"
        ea_res.write_seq(0, orig_e0)

        # Resume Stage Test 3b: Simulate Wave 2 bid=2 bootstrap (slot_B overwritten mid-layer, slot_A intact)
        cb_res.write_seq(0, torch.zeros_like(cb_res.read_seq(0)))
        assert compare_files_byte_equal(res_dir / "eval_donor_slot_A.bin", res_dir / "eval_pre_canon_slot_A.bin")
        probe_dbl = run_layer_resume_determinism_probe(
            mode="double_recompute",
            probe_bid=2,
            text_cfg=cfg,
            st_index=st_idx,
            rotary_emb=model.model.rotary_emb,
            backend="cpu",
            calib_samples=calib_samples,
            eval_samples=eval_samples,
            c_in_store=ca_res,
            e_in_store=ea_res,
        )
        assert probe_dbl["passed"] and probe_dbl["max_rel_l2"] <= 1e-4

        # Verify pass1_checkpoint.json + C3HealResult NPZ round-trip & structured [RESUME] log
        ckpt_path = res_dir / "pass1_checkpoint.json"
        heals_dir = res_dir / "saved_heals"
        dummy_hr = C3HealResult(
            w_gate_f32=np.ones((8, 64), dtype=np.float32) * 0.25,
            alpha_scales=np.linspace(0.8, 1.2, 8, dtype=np.float32),
            w_down_shexp_f32=np.ones((64, 32), dtype=np.float32) * 0.1,
            c1_accepted=True,
            c2_alpha_accepted=True,
            c2_shexp_accepted=False,
            val_rel_l2_before=0.15,
            val_rel_l2_after_c1=0.13,
            val_rel_l2_after_c2_alpha=0.12,
            val_rel_l2_after_c3=0.12,
            metrics={"unit_test": True},
        )
        _save_wave2_pass1_checkpoint(
            ckpt_path=ckpt_path,
            heals_dir=heals_dir,
            completed_layer=1,
            active_slot="A",
            e_pre_canon_ready=True,
            calib_seq_lengths=[12, 16],
            eval_seq_lengths=[14],
            stage2a_raw={320: {"A2": {"per_layer": {"2": {"r_en": 0.1, "r_ru": 0.11}}}}},
            saved_winner_heals={(320, "A2", 2): (np.arange(8, dtype=np.int64), dummy_hr)},
        )
        loaded_ckpt = _load_wave2_pass1_checkpoint(ckpt_path, heals_dir)
        assert loaded_ckpt["completed_layer"] == 1 and loaded_ckpt["active_slot"] == "A"
        loaded_keep, loaded_hr = loaded_ckpt["saved_winner_heals"][(320, "A2", 2)]
        assert np.array_equal(loaded_keep, np.arange(8, dtype=np.int64))
        np.testing.assert_allclose(loaded_hr.w_gate_f32, dummy_hr.w_gate_f32)
        np.testing.assert_allclose(loaded_hr.alpha_scales, dummy_hr.alpha_scales)

        test_log_path = tmp / "gpu_runs_test.log"
        log_line = append_gpu_resume_log(
            pipeline="unit_test_wave2",
            resume_bid=2,
            cur_slot="A",
            verified_files={"calib_donor_slot_A.bin": ca_res.total_bytes, "eval_donor_slot_A.bin": ea_res.total_bytes},
            probe_mode=probe_dbl["mode"],
            probe_max_rel_l2=probe_dbl["max_rel_l2"],
            log_path=test_log_path,
        )
        assert test_log_path.is_file() and log_line.startswith("[RESUME] ")

        # Resume layer 2 from slot_A -> slot_B and verify bit-exact match vs uninterrupted reference!
        _forward_layer_all(2, ca_res, cb_res, ea_res, eb_res)
        for s in calib_samples:
            assert torch.equal(cb_res.read_seq(s.idx), cb_ref.read_seq(s.idx))
        for s in eval_samples:
            assert torch.equal(eb_res.read_seq(s.idx), eb_ref.read_seq(s.idx))

        # 4. Read-only check on real Wave 2 stage files if present on host
        real_w2_stage = STAGE_DIR / "wave2"
        real_stage_checked = False
        if (real_w2_stage / "calib_donor_slot_A.bin").is_file() and (real_w2_stage / "eval_donor_slot_A.bin").is_file():
            c_sz = (real_w2_stage / "calib_donor_slot_A.bin").stat().st_size
            e_sz = (real_w2_stage / "eval_donor_slot_A.bin").stat().st_size
            assert c_sz == 14_743_797_760, f"Unexpected calib_donor_slot_A.bin size: {c_sz}"
            assert e_sz == 165_478_400, f"Unexpected eval_donor_slot_A.bin size: {e_sz}"
            if (real_w2_stage / "eval_pre_canon_slot_A.bin").is_file() and not (real_w2_stage / "pass1_checkpoint.json").is_file():
                assert compare_files_byte_equal(
                    real_w2_stage / "eval_donor_slot_A.bin",
                    real_w2_stage / "eval_pre_canon_slot_A.bin",
                )
            real_stage_checked = True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return {
        "size_guard_verified": True,
        "prev_slot_probe_max_rel_l2": round(float(probe_prev["max_rel_l2"]), 8),
        "double_recompute_probe_max_rel_l2": round(float(probe_dbl["max_rel_l2"]), 8),
        "resumed_bit_exact_vs_uninterrupted": True,
        "real_wave2_slot_a_verified": real_stage_checked,
    }


def test_10_opus_wave3_d2b_and_audit90_safeguards() -> Dict[str, Any]:
    import hashlib

    from scripts.v2.assemble_gguf import (
        VARIANT_SPECS,
        build_tensor_type_overrides,
        check_quantize_log_for_missing_imatrix,
        verify_imatrix_coverage_against_gguf,
        verify_streaming_gguf_dry_run_parity,
    )
    from scripts.v2.common_io import (
        DONOR_DIR,
        REF_205E_GGUF,
        REPO_ROOT,
        assert_post_write_free_gib,
        compute_file_sha256_streaming,
    )
    from scripts.v2.model_runner import load_text_cfg_and_index
    from scripts.v2.prequant_gate import (
        compute_kl_and_top1_from_hidden,
        compute_per_doc_kl_bootstrap_ci,
        decode_kld_and_score_logits,
        parse_llama_perplexity_kld_output,
        plan_bf16_server_vram_flags,
        write_llama_kld_file,
    )

    # 1. Zero .unlink() in wave2_shootout.py & wave3_full_run.py (OPUS §1.D2b.3/4)
    for fn in ("wave2_shootout.py", "wave3_full_run.py"):
        src_txt = (REPO_ROOT / "scripts" / "v2" / fn).read_text(encoding="utf-8")
        assert ".unlink(" not in src_txt, f"Forbidden .unlink( found in {fn}!"

    # 2. D1 non-routed tensor-type rules + Q4_0 PLE copy protection (OPUS Audit #90 Item 6)
    rules_v1 = build_tensor_type_overrides(VARIANT_SPECS["V1"])
    assert "per_layer_token_embd.weight=q4_0" in rules_v1
    assert r"blk\.\d+\.attn_q\.weight=q4_k" in rules_v1
    assert r"blk\.\d+\.attn_k\.weight=q4_k" in rules_v1
    assert r"blk\.\d+\.ffn_gate_shexp\.weight=q5_k" in rules_v1
    assert r"blk\.\d+\.ffn_up_shexp\.weight=q5_k" in rules_v1
    assert r"blk\.\d+\.ffn_down_shexp\.weight=q8_0" in rules_v1

    # 3. Missing-imatrix log detector (OPUS Audit #90 Item 2b)
    check_quantize_log_for_missing_imatrix("llama_model_quantize: have importance matrix data with 950 entries\n")
    caught_missing_imat = False
    try:
        check_quantize_log_for_missing_imatrix("====== llama_model_quantize_impl: did not find weights for blk.0.ffn_gate_shexp.weight\n")
    except RuntimeError:
        caught_missing_imat = True
    assert caught_missing_imat

    # 4. Real 205E GGUF + Donor dry-run parity + complete 49-layer imatrix key/shape coverage + BF16 VRAM plan
    dry_parity_res: Dict[str, Any] = {"skipped": True}
    imat_cov_res: Dict[str, Any] = {"skipped": True}
    vram_plan_res: Dict[str, Any] = {"skipped": True}
    if REF_205E_GGUF.is_file() and (DONOR_DIR / "config.json").is_file():
        dry_parity_res = verify_streaming_gguf_dry_run_parity(
            target_k=320,
            donor_dir=DONOR_DIR,
            ref_gguf=REF_205E_GGUF,
        )
        assert dry_parity_res["passed"] and dry_parity_res["tensor_count"] == 1086

        # Synthesize the exact 49-layer + head imatrix shape map produced by Wave 3 hooks and verify 100% 205E coverage!
        text_cfg, _ = load_text_cfg_and_index(DONOR_DIR)
        ltypes = list(text_cfg.layer_types) + ["indexed_attention"]
        ple_bids = {int(x) - 1 for x in getattr(text_cfg, "ple_layer_ids", [])}
        k_exp = 320
        s2_shapes: Dict[str, Tuple[int, ...]] = {
            "output.weight": (2560,),
            "token_embd.weight": (2560,),
            "output_hc_down.weight": (10240,),
            "output_hc_up.weight": (320,),
        }
        cnt_shapes: Dict[str, Tuple[int, ...]] = {k: (1,) for k in s2_shapes}
        for bid, lt in enumerate(ltypes):
            for nm, dm in (
                (f"blk.{bid}.hc_attn_down_inject.weight", 10240),
                (f"blk.{bid}.hc_attn_up.weight", 320),
                (f"blk.{bid}.hc_ffn_down_inject.weight", 10240),
                (f"blk.{bid}.hc_ffn_up.weight", 320),
                (f"blk.{bid}.ffn_gate_shexp.weight", 2560),
                (f"blk.{bid}.ffn_up_shexp.weight", 2560),
                (f"blk.{bid}.ffn_down_shexp.weight", 640),
            ):
                s2_shapes[nm] = (dm,)
                cnt_shapes[nm] = (1,)
            if bid in ple_bids:
                for nm in (f"blk.{bid}.ple_key.weight", f"blk.{bid}.ple_value.weight"):
                    s2_shapes[nm] = (2560,)
                    cnt_shapes[nm] = (1,)
            if lt == "linear_attention":
                for nm, dm in (
                    (f"blk.{bid}.attn_qkv_gate.weight", 2560),
                    (f"blk.{bid}.ssm_beta_alpha.weight", 2560),
                    (f"blk.{bid}.ssm_out.weight", 6144),
                ):
                    s2_shapes[nm] = (dm,)
                    cnt_shapes[nm] = (1,)
            else:
                for nm, dm in (
                    (f"blk.{bid}.attn_q.weight", 2560),
                    (f"blk.{bid}.attn_k.weight", 2560),
                    (f"blk.{bid}.attn_v.weight", 2560),
                    (f"blk.{bid}.attn_output.weight", 6144),
                    (f"blk.{bid}.indexer.q_proj.weight", 2560),
                    (f"blk.{bid}.indexer.k_proj.weight", 2560),
                ):
                    s2_shapes[nm] = (dm,)
                    cnt_shapes[nm] = (1,)
            if bid == 48:
                for nm, dm in (
                    ("blk.48.nextn.eh_proj.weight", 5120),
                    ("blk.48.nextn.hc_head_down.weight", 10240),
                    ("blk.48.nextn.hc_head_up.weight", 320),
                ):
                    s2_shapes[nm] = (dm,)
                    cnt_shapes[nm] = (1,)
            for nm, dm in (
                (f"blk.{bid}.ffn_gate_exps.weight", 2560),
                (f"blk.{bid}.ffn_up_exps.weight", 2560),
                (f"blk.{bid}.ffn_down_exps.weight", 640),
            ):
                s2_shapes[nm] = (k_exp, dm)
                cnt_shapes[nm] = (k_exp,)

        imat_cov_res = verify_imatrix_coverage_against_gguf(
            s2_shapes,
            cnt_shapes,
            ref_gguf=REF_205E_GGUF,
            expected_k=k_exp,
            check_completeness=True,
        )
        assert imat_cov_res["passed"] and imat_cov_res["missing_quantizable_count"] == 0

        vram_plan_res = plan_bf16_server_vram_flags(REF_205E_GGUF, n_parallel=10, max_vram_gib=9.20)
        assert vram_plan_res["projected_vram_gib"] <= 9.20

    # 5. Streaming SHA256 + >=10 GiB post-write free-space guard + .kld round-trip + bootstrap CI
    tmp = Path(tempfile.mkdtemp(prefix="test_v2_d2b_", dir="/tmp"))
    try:
        blob = b"smartllm_v2_sha_test_" * 1000
        bp = tmp / "sha_blob.bin"
        bp.write_bytes(blob)
        assert compute_file_sha256_streaming(bp) == hashlib.sha256(blob).hexdigest()

        _ = assert_post_write_free_gib(tmp / "ok.bin", 1024, min_free_gib=0.1, label="unit_ok")
        space_blocked = False
        try:
            _ = assert_post_write_free_gib(tmp / "huge.bin", 10**15, min_free_gib=10.0, label="unit_huge")
        except RuntimeError as exc:
            space_blocked = "storage guard FAILED" in str(exc)
        assert space_blocked

        rng = np.random.default_rng(77)
        n_ctx, d_hid, n_voc = 16, 32, 128
        w_lm = (rng.standard_normal((n_voc, d_hid)) * 0.2).astype(np.float16)
        toks = [rng.integers(1, n_voc, size=(n_ctx,), dtype=np.int32) for _ in range(2)]
        h_don = [(rng.standard_normal((n_ctx - 1, d_hid)) * 0.5).astype(np.float32) for _ in range(2)]
        h_mod = [hd + (rng.standard_normal(hd.shape) * 0.08).astype(np.float32) for hd in h_don]

        kld_p = tmp / "unit_donor.kld"
        kld_meta = write_llama_kld_file(
            out_kld_path=kld_p,
            token_chunks=toks,
            donor_hidden_chunks=h_don,
            lm_head_weight_fp16=w_lm,
            n_ctx=n_ctx,
            backend="cpu",
            min_post_write_free_gib=0.0,
        )
        first = n_ctx // 2
        mod_logits_chunks = [hm[first : n_ctx - 1] @ w_lm.astype(np.float32).T for hm in h_mod]
        kld_res = decode_kld_and_score_logits(kld_p, mod_logits_chunks)
        kld_mean, same_p, cnt = kld_res["mean_kld"], kld_res["same_top_p"], kld_res["count"]
        exact_kl, exact_t1, exact_n = compute_kl_and_top1_from_hidden(
            np.concatenate([hd[first : n_ctx - 1] for hd in h_don], axis=0),
            np.concatenate([hm[first : n_ctx - 1] for hm in h_mod], axis=0),
            w_lm,
            backend="cpu",
        )
        assert cnt == kld_meta["eval_tokens"] == exact_n
        assert abs(kld_mean - (exact_kl / exact_n)) < 5e-4
        assert abs(same_p - (exact_t1 / exact_n)) < 1e-6

        parsed_kld, parsed_t1 = parse_llama_perplexity_kld_output(
            "Final estimate: PPL = 6.1234 +/- 0.0500\nMean    KLD:     0.031250 +/- 0.001200\nSame top p:   94.50% +/-  0.40%\n"
        )
        assert abs(parsed_kld - 0.03125) < 1e-7 and abs(parsed_t1 - 0.945) < 1e-7

        boot = compute_per_doc_kl_bootstrap_ci(
            [
                {"sample_id": "e0", "lang": "en", "tokens": 1200, "mean_kl": 0.04},
                {"sample_id": "e1", "lang": "en", "tokens": 2800, "mean_kl": 0.06},
                {"sample_id": "r0", "lang": "ru", "tokens": 400, "mean_kl": 0.07},
                {"sample_id": "r1", "lang": "ru", "tokens": 600, "mean_kl": 0.09},
            ]
        )
        assert boot["en"]["ci95_kl"][0] <= boot["en"]["mean_kl"] <= boot["en"]["ci95_kl"][1]
        assert boot["ru"]["ci95_kl"][0] <= boot["ru"]["mean_kl"] <= boot["ru"]["ci95_kl"][1]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return {
        "dry_run_gguf_parity": dry_parity_res,
        "imatrix_coverage": imat_cov_res,
        "kld_roundtrip_abs_err": round(abs(kld_mean - (exact_kl / exact_n)), 7),
    }


def run_all_cpu_tests() -> Dict[str, Any]:
    t_start = time.perf_counter()
    tests = [
        ("test_01_syntax_and_zero_gpu_imports", test_01_syntax_and_zero_gpu_imports),
        ("test_02_common_io_and_zero_swap_telemetry", test_02_common_io_and_zero_swap_telemetry),
        ("test_03_moe_backend_and_qwen4exp_3layer_parity", test_03_moe_backend_and_qwen4exp_3layer_parity),
        ("test_04_selectors_real_donor_scores_and_exact_a4_prime_gram", test_04_selectors_real_donor_scores_and_exact_a4_prime_gram),
        ("test_05_healing_c3_router_alpha_shexp_and_rejection_guard", test_05_healing_c3_router_alpha_shexp_and_rejection_guard),
        ("test_06_cleanroom_gsq_q2_0_bit_exact_vs_libggml", test_06_cleanroom_gsq_q2_0_bit_exact_vs_libggml),
        ("test_07_streaming_gguf_assembly_ple_reuse_and_gsq_splice", test_07_streaming_gguf_assembly_ple_reuse_and_gsq_splice),
        ("test_08_shootout_decision_engines_and_prequant_gates", test_08_shootout_decision_engines_and_prequant_gates),
        ("test_09_per_layer_resume_and_determinism_probe", test_09_per_layer_resume_and_determinism_probe),
        ("test_10_opus_wave3_d2b_and_audit90_safeguards", test_10_opus_wave3_d2b_and_audit90_safeguards),
    ]
    summary: Dict[str, Any] = {}
    for name, fn in tests:
        t0 = time.perf_counter()
        res = fn()
        dt = time.perf_counter() - t0
        summary[name] = {"status": "PASS", "elapsed_sec": round(dt, 3), "details": res}
        print(f"[PASS] {name} ({dt:.2f}s)", flush=True)

    # Verify zero cupy import, zero CUDA initialization, and zero leftover /tmp/test_v2_* directories
    import torch

    assert "cupy" not in sys.modules, "cupy was imported during CPU test suite!"
    assert not torch.cuda.is_initialized(), "CUDA context was initialized during CPU test suite!"
    leftover = glob.glob("/tmp/test_v2_*")
    assert len(leftover) == 0, f"Leftover /tmp scratch dirs: {leftover}"

    summary["suite_status"] = "PASS"
    summary["total_tests"] = len(tests)
    summary["total_elapsed_sec"] = round(time.perf_counter() - t_start, 3)
    return summary


if __name__ == "__main__":
    out = run_all_cpu_tests()
    print(json.dumps(out, indent=2))
