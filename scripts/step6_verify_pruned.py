#!/usr/bin/env python3
"""Step 6 Independent Acceptance Gate: 100% Byte-Exact Safetensors, Slicing, Hardlinks & imatrix Verification.

Runs strictly on CPU (`0` GPU VRAM, `CUDA_VISIBLE_DEVICES=""`) and verifies every Step 6 requirement from
`PLAN.md` and `research/step5_7_tz.md` with ZERO unverified bytes:
1. `config.json` (`text_config.num_experts == 205`, all other keys identical to donor) + metadata SHA-256 match.
2. `model.safetensors.index.json`: `1,658` tensors (`symmetric_difference == 0`), `82` physical files, exact
   single-byte parameter delta (`359,999,963,128 - 49 * 307 * 9,835,520 == 212,044,235,768`), `0` leftover `_work/*.bin`.
3. `31` pure PLE shards (`124` tensors): NTFS hardlink inode identity (`st_nlink >= 2`, `samefile == True`),
   `weight_map` shard-assignment identity (`p_wmap[k] == sf == d_wmap[k]`), and dtype/shape verification.
4. `1,387` non-sliced non-pure-PLE tensors (`visual`, `root`, `ple-boundary` `I64`, `attn`, `linear_attn`, `indexer`,
   `shared_expert`, `hyper_connection`, `mtp` dense): 100% bit-for-bit raw tensor byte equality vs donor + `isfinite`.
5. ALL `49 / 49` MoE blocks (`layers.0..47` + `mtp.layers.0` = `147 / 147` sliced tensors, `0 B` skipped):
   - Score JSON integrity (`total_tokens`: `947,424` on trunk, `946,740` = `S - 1` on MTP; `71,288` `<|image_pad|>`;
     `keep_k == 205`; sorted ascending; `workhorse_top64_retained == 64`; `0` NaN/Inf; `0` dead/fallback kept experts).
   - 100% bit-for-bit `tensor_raw_bytes` equality + `torch.isfinite` vs `donor[keep_indices]` on ALL `49 / 49`
     `mlp.gate.weight [205, 2560]`, ALL `49 / 49` `mlp.experts.gate_up_proj [205, 1280, 2560]`, and ALL `49 / 49`
     `mlp.experts.down_proj [205, 2560, 640]` (`98 / 98` expert weight tensors + `49 / 49` router gates).
6. `data/calib/imatrix_step6.gguf`: valid GGUF v3 (`general.type == 'imatrix'`, `ARRAY[STRING]` `imatrix.datasets`,
   `chunk_size == 512`, `chunk_count == 1851`, `n_layer_nextn == 1`), exact `782`-name canonical GGUF bijection
   (`2,346` `F32` 2D GGUF tensors: `.in_sum2`, `.counts`, `.in_sum`), exact `(ne0, ne1)` geometry per tensor,
   exact token counts (`947,424` trunk / `946,740` MTP / `3,786,960` `eh_proj`), per-row positive `in_sum2`,
   `0` NaN/Inf, and Cauchy-Schwarz `in_sum2 * counts >= in_sum^2`.
"""

from __future__ import annotations

import gc
import hashlib
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

os.environ["CUDA_VISIBLE_DEVICES"] = ""

import gguf
import numpy as np
import torch
from safetensors import safe_open

ROOT = Path(__file__).resolve().parent.parent
DONOR_DIR = ROOT / "models" / "Qwen3.8-Flash-Next"
PRUNED_DIR = ROOT / "models" / "pruned_safetensors"
SCORES_DIR = ROOT / "research" / "step6_raw" / "scores"
IMATRIX_PATH = ROOT / "data" / "calib" / "imatrix_step6.gguf"
OUT_REPORT = ROOT / "research" / "step6_raw" / "verify_pruned_report.json"

DONOR_TOTAL_PARAM_BYTES = 359_999_963_128
DONOR_EXPERTS = 512
KEEP_K = 205
NUM_MOE_BLOCKS = 49
BYTES_PER_EXPERT = (1280 * 2560 * 2) + (2560 * 640 * 2) + (2560 * 2)  # 9,835,520 B
EXPECTED_PRUNED_PARAM_BYTES = DONOR_TOTAL_PARAM_BYTES - NUM_MOE_BLOCKS * (DONOR_EXPERTS - KEEP_K) * BYTES_PER_EXPERT

EXPECTED_TRUNK_TOKENS = 947_424
EXPECTED_NUM_ROWS = 684
EXPECTED_MTP_TOKENS = EXPECTED_TRUNK_TOKENS - EXPECTED_NUM_ROWS  # 946,740
EXPECTED_VISUAL_PAD_TOKENS = 71_288

METADATA_FILES = (
    "tokenizer.json",
    "tokenizer_config.json",
    "preprocessor_config.json",
    "video_preprocessor_config.json",
    "generation_config.json",
    "chat_template.jinja",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "added_tokens.json",
    "LICENSE",
    "README.md",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def tensor_raw_bytes(t: torch.Tensor) -> bytes:
    tc = t.contiguous().view(torch.uint8)
    return tc.numpy().tobytes()


def build_expected_imatrix_shapes(text_cfg: dict[str, Any], keep_k: int) -> dict[str, tuple[int, int]]:
    """Build exact canonical 782-tensor GGUF v3 `(ne0, ne1)` shape map for `qwen4exp` (`b11954`)."""
    hidden = int(text_cfg["hidden_size"])  # 2560
    hc_mult = int(text_cfg["hc_count"])  # 4
    hc_dim = hidden * hc_mult  # 10240
    hc_low = int(text_cfg["hc_lowrank"])  # 320
    moe_inter = int(text_cfg["moe_intermediate_size"])  # 640
    sh_inter = int(text_cfg["shared_expert_intermediate_size"])  # 640
    q_heads = int(text_cfg["num_attention_heads"])  # 32
    head_dim = int(text_cfg["head_dim"])  # 128
    attn_out_in = q_heads * head_dim  # 4096
    lin_v_heads = int(text_cfg["linear_num_value_heads"])  # 48
    lin_v_dim = int(text_cfg["linear_value_head_dim"])  # 128
    ssm_out_in = lin_v_heads * lin_v_dim  # 6144
    n_layers = int(text_cfg["num_hidden_layers"])  # 48
    ple_zero_based = {int(pid) - 1 for pid in text_cfg.get("ple_layer_ids", [])}  # {1}
    layer_types = text_cfg["layer_types"]

    expected: dict[str, tuple[int, int]] = {}

    def add_block_common(bid: int, is_qsa: bool, has_ple: bool) -> None:
        expected[f"blk.{bid}.hc_attn_down_inject.weight"] = (hc_dim, 1)
        expected[f"blk.{bid}.hc_attn_up.weight"] = (hc_low, 1)
        expected[f"blk.{bid}.hc_ffn_down_inject.weight"] = (hc_dim, 1)
        expected[f"blk.{bid}.hc_ffn_up.weight"] = (hc_low, 1)
        expected[f"blk.{bid}.ffn_gate_inp.weight"] = (hidden, 1)
        expected[f"blk.{bid}.ffn_gate_inp_shexp.weight"] = (hidden, 1)
        expected[f"blk.{bid}.ffn_gate_shexp.weight"] = (hidden, 1)
        expected[f"blk.{bid}.ffn_up_shexp.weight"] = (hidden, 1)
        expected[f"blk.{bid}.ffn_down_shexp.weight"] = (sh_inter, 1)
        expected[f"blk.{bid}.ffn_gate_exps.weight"] = (hidden, keep_k)
        expected[f"blk.{bid}.ffn_up_exps.weight"] = (hidden, keep_k)
        expected[f"blk.{bid}.ffn_down_exps.weight"] = (moe_inter, keep_k)
        if has_ple:
            expected[f"blk.{bid}.ple_key.weight"] = (hidden, 1)
            expected[f"blk.{bid}.ple_value.weight"] = (hidden, 1)
        if is_qsa:
            expected[f"blk.{bid}.attn_q.weight"] = (hidden, 1)
            expected[f"blk.{bid}.attn_k.weight"] = (hidden, 1)
            expected[f"blk.{bid}.attn_v.weight"] = (hidden, 1)
            expected[f"blk.{bid}.attn_output.weight"] = (attn_out_in, 1)
            expected[f"blk.{bid}.indexer.q_proj.weight"] = (hidden, 1)
            expected[f"blk.{bid}.indexer.k_proj.weight"] = (hidden, 1)
        else:
            expected[f"blk.{bid}.attn_qkv_gate.weight"] = (hidden, 1)
            expected[f"blk.{bid}.ssm_beta_alpha.weight"] = (hidden, 1)
            expected[f"blk.{bid}.ssm_out.weight"] = (ssm_out_in, 1)

    for bid in range(n_layers):
        is_qsa = layer_types[bid] != "linear_attention"
        add_block_common(bid, is_qsa=is_qsa, has_ple=(bid in ple_zero_based))

    # Trunk output head (`3` weights)
    expected["output_hc_down.weight"] = (hc_dim, 1)
    expected["output_hc_up.weight"] = (hc_low, 1)
    expected["output.weight"] = (hidden, 1)

    # MTP NextN block (`blk.48`, `21` weights)
    mtp_bid = n_layers
    add_block_common(mtp_bid, is_qsa=True, has_ple=False)
    expected[f"blk.{mtp_bid}.nextn.eh_proj.weight"] = (2 * hidden, 1)
    expected[f"blk.{mtp_bid}.nextn.hc_head_down.weight"] = (hc_dim, 1)
    expected[f"blk.{mtp_bid}.nextn.hc_head_up.weight"] = (hc_low, 1)

    return expected


def decode_gguf_kv(rd: gguf.GGUFReader) -> dict[str, Any]:
    kv_dict: dict[str, Any] = {}
    for k, field in rd.fields.items():
        if k.startswith("GGUF."):
            continue
        if len(field.types) >= 2 and field.types[0] == gguf.GGUFValueType.ARRAY:
            elem_type = field.types[1]
            arr_vals: list[Any] = []
            for idx in field.data:
                part = field.parts[idx]
                if elem_type == gguf.GGUFValueType.STRING:
                    arr_vals.append(bytes(part).decode("utf-8", errors="replace"))
                elif isinstance(part, np.ndarray) and part.size == 1:
                    arr_vals.append(part.item())
                else:
                    arr_vals.append(part.tolist())
            kv_dict[k] = arr_vals
        else:
            val = field.parts[field.data[0]]
            if field.types[0] == gguf.GGUFValueType.STRING:
                kv_dict[k] = bytes(val).decode("utf-8", errors="replace")
            elif isinstance(val, np.ndarray) and val.size == 1:
                kv_dict[k] = val.item()
            else:
                kv_dict[k] = val.tolist()
    return kv_dict


def main() -> int:
    t0 = time.perf_counter()
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)
            print(f"[FAIL] {msg}", flush=True)

    print("=== Step 6 Independent Verification Gate (100% All-49-Block Byte-Exact, 0 GPU VRAM) ===", flush=True)

    # 1. Verify config.json & metadata files
    donor_cfg = json.loads((DONOR_DIR / "config.json").read_text(encoding="utf-8"))
    pruned_cfg = json.loads((PRUNED_DIR / "config.json").read_text(encoding="utf-8"))
    check(
        pruned_cfg["text_config"]["num_experts"] == KEEP_K,
        f"config num_experts={pruned_cfg['text_config']['num_experts']} != {KEEP_K}",
    )
    donor_cfg_cmp = json.loads(json.dumps(donor_cfg))
    donor_cfg_cmp["text_config"]["num_experts"] = KEEP_K
    check(pruned_cfg == donor_cfg_cmp, "pruned config.json differs from donor outside text_config.num_experts")

    metadata_hashes: dict[str, str] = {}
    for fn in METADATA_FILES:
        dp = DONOR_DIR / fn
        pp = PRUNED_DIR / fn
        if dp.exists():
            check(pp.exists(), f"Missing metadata file {fn}")
            if pp.exists():
                dh = sha256_file(dp)
                ph = sha256_file(pp)
                check(dh == ph, f"Metadata SHA-256 mismatch on {fn}: {dh} != {ph}")
                metadata_hashes[fn] = ph

    # 2. Verify model.safetensors.index.json, exact byte-delta formula & physical files
    donor_idx = json.loads((DONOR_DIR / "model.safetensors.index.json").read_text(encoding="utf-8"))
    pruned_idx = json.loads((PRUNED_DIR / "model.safetensors.index.json").read_text(encoding="utf-8"))
    d_wmap: dict[str, str] = donor_idx["weight_map"]
    p_wmap: dict[str, str] = pruned_idx["weight_map"]

    check(
        int(donor_idx["metadata"]["total_size"]) == DONOR_TOTAL_PARAM_BYTES,
        f"Donor metadata.total_size={donor_idx['metadata']['total_size']} != {DONOR_TOTAL_PARAM_BYTES}",
    )
    check(
        int(pruned_idx["metadata"]["total_size"]) == EXPECTED_PRUNED_PARAM_BYTES,
        f"Pruned metadata.total_size={pruned_idx['metadata']['total_size']} != {EXPECTED_PRUNED_PARAM_BYTES}",
    )

    sym_diff = set(d_wmap.keys()).symmetric_difference(set(p_wmap.keys()))
    check(len(d_wmap) == 1658, f"Donor weight_map len={len(d_wmap)} != 1658")
    check(len(p_wmap) == 1658, f"Pruned weight_map len={len(p_wmap)} != 1658")
    check(len(sym_diff) == 0, f"Key bijection symmetric_difference={len(sym_diff)}")

    ref_files = sorted(set(p_wmap.values()))
    disk_st_files = sorted(p.name for p in PRUNED_DIR.glob("*.safetensors"))
    check(
        ref_files == disk_st_files,
        f"Referenced safetensors ({len(ref_files)}) != disk safetensors ({len(disk_st_files)})",
    )
    check(len(ref_files) == 82, f"Expected 82 safetensors files, got {len(ref_files)}")

    # Verify scratch `_work/*.bin` were cleaned up and measure any remaining `_work` state files
    work_dir = PRUNED_DIR / "_work"
    leftover_bins = sorted(p.name for p in work_dir.glob("*.bin")) if work_dir.exists() else []
    check(len(leftover_bins) == 0, f"Leftover _work/*.bin files found: {leftover_bins}")
    work_residual_bytes = (
        sum(p.stat().st_size for p in work_dir.rglob("*") if p.is_file()) if work_dir.exists() else 0
    )

    # 3. Verify 31 pure PLE hardlinked shards + exact `weight_map` shard assignment
    hardlink_files = [sf for sf in ref_files if sf.startswith("model-00")]
    check(len(hardlink_files) == 31, f"Expected 31 hardlinked PLE shards, got {len(hardlink_files)}")
    pure_ple_tensors_count = 0
    total_computed_bytes = 0
    for sf in hardlink_files:
        dp = DONOR_DIR / sf
        pp = PRUNED_DIR / sf
        st_pp = os.stat(pp)
        check(os.path.samefile(dp, pp), f"PLE shard {sf} is NOT an NTFS hardlink to donor!")
        check(st_pp.st_nlink >= 2, f"PLE shard {sf} has st_nlink={st_pp.st_nlink} < 2")
        with safe_open(str(pp), framework="pt", device="cpu") as pf:
            for k in sorted(pf.keys()):
                check(p_wmap.get(k) == sf, f"PLE key {k} in {sf} does not match pruned weight_map ({p_wmap.get(k)})")
                check(d_wmap.get(k) == sf, f"PLE key {k} in {sf} does not match donor weight_map ({d_wmap.get(k)})")
                sl = pf.get_slice(k)
                check(sl.get_dtype() == "BF16", f"Expected BF16 on PLE shard {k}, got {sl.get_dtype()}")
                check(tuple(sl.get_shape()) == (2_500_012, 160), f"Bad PLE shard shape on {k}: {sl.get_shape()}")
                total_computed_bytes += 2_500_012 * 160 * 2
                pure_ple_tensors_count += 1
    check(pure_ple_tensors_count == 124, f"Expected 124 tensors in 31 pure PLE shards, got {pure_ple_tensors_count}")
    if not failures:
        print(f"[OK] Verified 31 pure PLE NTFS hardlinks ({pure_ple_tensors_count} tensors, st_nlink >= 2).", flush=True)

    # 4. Load all 49 score JSONs (`layer_00..47` + `mtp`) and verify invariants
    keep_map: dict[str, list[int]] = {}
    reap_stats_per_block: list[dict[str, Any]] = []
    block_names = [f"layer_{li:02d}" for li in range(48)] + ["mtp"]
    for bname in block_names:
        sp = SCORES_DIR / f"{bname}.json"
        check(sp.exists(), f"Missing score JSON {sp}")
        sj = json.loads(sp.read_text(encoding="utf-8"))
        exp_toks = EXPECTED_MTP_TOKENS if bname == "mtp" else EXPECTED_TRUNK_TOKENS
        check(sj["total_tokens"] == exp_toks, f"{bname}: total_tokens={sj['total_tokens']} != {exp_toks}")
        check(
            sj["visual_image_pad_tokens"] == EXPECTED_VISUAL_PAD_TOKENS,
            f"{bname}: visual_image_pad_tokens={sj['visual_image_pad_tokens']} != {EXPECTED_VISUAL_PAD_TOKENS}",
        )
        check(sj["keep_k"] == KEEP_K, f"{bname}: keep_k={sj['keep_k']} != {KEEP_K}")
        check(sj["nan_or_inf_count"] == 0, f"{bname}: nan_or_inf_count={sj['nan_or_inf_count']}")
        check(sj["gate_l2_fallback_used"] == 0, f"{bname}: gate_l2_fallback_used={sj['gate_l2_fallback_used']}")
        check(sj["selector_audit"]["workhorse_top64_retained"] == 64, f"{bname}: workhorse_top64 != 64")
        ki = sj["keep_indices_k205_sorted"]
        check(
            len(ki) == KEEP_K and ki == sorted(set(ki)) and ki[0] >= 0 and ki[-1] < DONOR_EXPERTS,
            f"{bname}: invalid keep_indices",
        )
        freqs = sj["arrays"]["expert_frequency"]
        min_kept_freq = min(int(freqs[idx]) for idx in ki)
        check(min_kept_freq > 0, f"{bname}: dead expert retained in keep_indices (min_kept_freq={min_kept_freq})")
        keep_map[bname] = ki

        ret = sj["retention_diagnostics_k205"]
        reap_stats_per_block.append(
            {
                "block": bname,
                "active_experts": sj["active_experts"],
                "min_kept_freq": min_kept_freq,
                "jaccard_vs_pure_reap": sj["selector_audit"]["jaccard_vs_pure_reap"],
                "ru_top50": ret["ru_top50_retained_in_k205"],
                "ru_cond_top50": ret["ru_cond_specialist_top50_retained_in_k205"],
                "vision_top50": ret["vision_top50_retained_in_k205"],
                "vision_cond_top50": ret["vision_cond_specialist_top50_retained_in_k205"],
                "p4_top50": ret["pillar4_top50_retained_in_k205"],
                "p4_cond_top50": ret["pillar4_cond_specialist_top50_retained_in_k205"],
                "p1_cond_top50": ret["by_stratum_all"]["pillar_1_frontend_3d_svg"][
                    "cond_specialist_top50_retained_in_k205"
                ],
                "p2_cond_top50": ret["by_stratum_all"]["pillar_2_seo_geo_security"][
                    "cond_specialist_top50_retained_in_k205"
                ],
                "agentic_cond_top50": ret["by_stratum_all"]["agentic_tool_calling"][
                    "cond_specialist_top50_retained_in_k205"
                ],
                "longctx_cond_top50": ret["by_stratum_all"]["long_context"][
                    "cond_specialist_top50_retained_in_k205"
                ],
                "retained_ean_share": ret["retained_share_of_total_weighted_ean"],
            }
        )
    if not failures:
        print("[OK] Verified all 49 REAP score JSONs (0 NaN/Inf, 0 dead/fallback experts, exact token counts).", flush=True)

    # 5. Byte-exact verification of ALL 1,387 immutable tensors + ALL 49/49 MoE blocks (`147/147` sliced tensors!)
    non_ple_files = [sf for sf in ref_files if not sf.startswith("model-00")]

    immutable_verified = 0
    sliced_shapes_verified = 0
    gate_exact_verified = 0
    expert_weights_exact_verified = 0

    for file_idx, sf in enumerate(non_ple_files, start=1):
        donor_handles: dict[str, Any] = {}
        try:
            with safe_open(str(PRUNED_DIR / sf), framework="pt", device="cpu") as pf:
                p_keys = sorted(pf.keys())
                for k in p_keys:
                    check(p_wmap.get(k) == sf, f"Key {k} in {sf} does not match index.json")
                    pt = pf.get_tensor(k)
                    total_computed_bytes += pt.numel() * pt.element_size()
                    if pt.is_floating_point():
                        check(bool(torch.isfinite(pt).all()), f"NaN/Inf detected in pruned tensor {k}!")

                    is_sliced = k.endswith((".mlp.gate.weight", ".mlp.experts.gate_up_proj", ".mlp.experts.down_proj"))
                    dsf = d_wmap[k]
                    if dsf not in donor_handles:
                        donor_handles[dsf] = safe_open(str(DONOR_DIR / dsf), framework="pt", device="cpu")
                    df = donor_handles[dsf]

                    if not is_sliced:
                        dt = df.get_tensor(k)
                        check(pt.dtype == dt.dtype and pt.shape == dt.shape, f"Shape/dtype mismatch on {k}")
                        check(tensor_raw_bytes(pt) == tensor_raw_bytes(dt), f"Byte mismatch on immutable tensor {k}!")
                        immutable_verified += 1
                        del dt
                    else:
                        if k.startswith("mtp."):
                            bname = "mtp"
                        else:
                            li = int(k.split(".")[3])
                            bname = f"layer_{li:02d}"
                        idx_t = torch.tensor(keep_map[bname], dtype=torch.long)
                        check(pt.dtype == torch.bfloat16, f"Expected BF16 on {k}, got {pt.dtype}")
                        if k.endswith(".mlp.gate.weight"):
                            check(tuple(pt.shape) == (KEEP_K, 2560), f"Bad gate shape on {k}: {tuple(pt.shape)}")
                            dt_slice = df.get_tensor(k).index_select(0, idx_t)
                            check(
                                tensor_raw_bytes(pt) == tensor_raw_bytes(dt_slice),
                                f"Gate slice raw byte mismatch on {k}!",
                            )
                            gate_exact_verified += 1
                            del dt_slice
                        elif k.endswith(".mlp.experts.gate_up_proj"):
                            check(
                                tuple(pt.shape) == (KEEP_K, 1280, 2560),
                                f"Bad gate_up shape on {k}: {tuple(pt.shape)}",
                            )
                            dt_slice = df.get_tensor(k).index_select(0, idx_t)
                            check(
                                tensor_raw_bytes(pt) == tensor_raw_bytes(dt_slice),
                                f"gate_up_proj raw byte mismatch on {k}!",
                            )
                            expert_weights_exact_verified += 1
                            del dt_slice
                        elif k.endswith(".mlp.experts.down_proj"):
                            check(
                                tuple(pt.shape) == (KEEP_K, 2560, 640),
                                f"Bad down_proj shape on {k}: {tuple(pt.shape)}",
                            )
                            dt_slice = df.get_tensor(k).index_select(0, idx_t)
                            check(
                                tensor_raw_bytes(pt) == tensor_raw_bytes(dt_slice),
                                f"down_proj raw byte mismatch on {k}!",
                            )
                            expert_weights_exact_verified += 1
                            del dt_slice
                        sliced_shapes_verified += 1
                    del pt
        finally:
            donor_handles.clear()
            gc.collect()
        if file_idx % 10 == 0 or file_idx == len(non_ple_files):
            print(f"  [Progress] Byte-verified {file_idx}/{len(non_ple_files)} non-pure-PLE safetensors files...", flush=True)

    check(immutable_verified == 1387, f"Expected 1387 immutable tensors verified, got {immutable_verified}")
    check(sliced_shapes_verified == 147, f"Expected 147 sliced tensors verified, got {sliced_shapes_verified}")
    check(gate_exact_verified == 49, f"Expected 49 gate slices verified, got {gate_exact_verified}")
    check(
        expert_weights_exact_verified == 98,
        f"Expected ALL 98 (49*2) full expert weight tensors verified bit-for-bit, got {expert_weights_exact_verified}",
    )
    check(
        total_computed_bytes == EXPECTED_PRUNED_PARAM_BYTES,
        f"total_computed_bytes={total_computed_bytes} != EXPECTED_PRUNED_PARAM_BYTES={EXPECTED_PRUNED_PARAM_BYTES}",
    )
    if not failures:
        print(
            f"[OK] Verified {immutable_verified}/1387 immutable tensors + {gate_exact_verified}/49 gates + "
            f"{expert_weights_exact_verified}/98 full expert tensors bit-for-bit (0 unverified bytes!).",
            flush=True,
        )

    # 6. Verify `imatrix_step6.gguf` (`782` canonical weights = `2,346` 2D F32 GGUF tensors)
    check(IMATRIX_PATH.exists(), f"Missing {IMATRIX_PATH}")
    expected_imat_shapes = build_expected_imatrix_shapes(pruned_cfg["text_config"], KEEP_K)
    check(
        len(expected_imat_shapes) == 782,
        f"Internal expected_imat_shapes count={len(expected_imat_shapes)} != 782",
    )

    rd = gguf.GGUFReader(str(IMATRIX_PATH))
    kv_dict = decode_gguf_kv(rd)

    check(kv_dict.get("general.type") == "imatrix", f"Bad general.type={kv_dict.get('general.type')}")
    check(
        kv_dict.get("imatrix.datasets") == ["data/calib/PremiumWebStudio-Calib.jsonl"],
        f"Bad imatrix.datasets={kv_dict.get('imatrix.datasets')}",
    )
    check(int(kv_dict.get("imatrix.chunk_size", -1)) == 512, f"Bad chunk_size={kv_dict.get('imatrix.chunk_size')}")
    check(int(kv_dict.get("imatrix.chunk_count", -1)) == 1851, f"Bad chunk_count={kv_dict.get('imatrix.chunk_count')}")
    check(
        int(kv_dict.get("imatrix.n_layer_nextn", -1)) == 1,
        f"Bad n_layer_nextn={kv_dict.get('imatrix.n_layer_nextn')}",
    )
    check(len(rd.tensors) == 782 * 3, f"Expected {782 * 3} GGUF tensors, got {len(rd.tensors)}")

    by_base: dict[str, dict[str, Any]] = {}
    for t in rd.tensors:
        base, suffix = t.name.rsplit(".", 1)
        by_base.setdefault(base, {})[suffix] = t

    imat_sym_diff = set(by_base.keys()).symmetric_difference(set(expected_imat_shapes.keys()))
    check(len(by_base) == 782, f"Expected 782 base weights in imatrix, got {len(by_base)}")
    check(
        len(imat_sym_diff) == 0,
        f"Canonical 782-name imatrix bijection mismatch ({len(imat_sym_diff)}): {sorted(imat_sym_diff)[:10]}",
    )

    zero_or_bad_imat = 0
    for base, exp_ne in sorted(expected_imat_shapes.items()):
        parts = by_base.get(base)
        if parts is None:
            zero_or_bad_imat += 1
            failures.append(f"Missing canonical imatrix weight: {base}")
            continue
        if set(parts.keys()) != {"in_sum2", "counts", "in_sum"}:
            zero_or_bad_imat += 1
            failures.append(f"Incomplete imatrix triplet for {base}: {sorted(parts.keys())}")
            continue

        for sfx in ("in_sum2", "counts", "in_sum"):
            if parts[sfx].tensor_type != gguf.GGMLQuantizationType.F32:
                zero_or_bad_imat += 1
                failures.append(f"Non-F32 imatrix tensor_type on {base}.{sfx}: {parts[sfx].tensor_type}")

        ne_s2 = tuple(int(x) for x in parts["in_sum2"].shape)
        ne_s1 = tuple(int(x) for x in parts["in_sum"].shape)
        ne_cnt = tuple(int(x) for x in parts["counts"].shape)
        if ne_s2 != exp_ne or ne_s1 != exp_ne or ne_cnt != (1, exp_ne[1]):
            zero_or_bad_imat += 1
            failures.append(
                f"Bad GGUF 2D imatrix shape on {base}: expected {exp_ne}/{(1, exp_ne[1])}, "
                f"got in_sum2={ne_s2}, in_sum={ne_s1}, counts={ne_cnt}"
            )
            continue

        # In `GGUFReader`, numpy C-order `data` has shape `(ne1, ne0)` = `(nmat, in_dim)`
        s2 = np.asarray(parts["in_sum2"].data, dtype=np.float64).reshape(exp_ne[1], exp_ne[0])
        s1 = np.asarray(parts["in_sum"].data, dtype=np.float64).reshape(exp_ne[1], exp_ne[0])
        cnt = np.asarray(parts["counts"].data, dtype=np.float64).reshape(exp_ne[1], 1)

        if not (np.all(np.isfinite(s2)) and np.all(np.isfinite(s1)) and np.all(np.isfinite(cnt))):
            zero_or_bad_imat += 1
            failures.append(f"NaN/Inf in imatrix for {base}")
            continue

        if not np.all(s2 >= 0.0):
            zero_or_bad_imat += 1
            failures.append(f"Negative in_sum2 entry in {base}: min={float(s2.min())}")
        if float(s2.sum(axis=1).min()) <= 0.0:
            zero_or_bad_imat += 1
            failures.append(f"Zero-energy expert/row in {base}: min_row_sum={float(s2.sum(axis=1).min())}")
        if float(cnt.min()) < 1.0:
            zero_or_bad_imat += 1
            failures.append(f"Non-positive count in {base}: min_cnt={float(cnt.min())}")

        # Exact token count invariants on all 2D non-expert weights (`ne1 == 1`)
        if exp_ne[1] == 1:
            c_val = int(round(float(cnt[0, 0])))
            if base == "blk.48.nextn.eh_proj.weight":
                exp_c = 4 * EXPECTED_MTP_TOKENS
            elif base.startswith("blk.48."):
                exp_c = EXPECTED_MTP_TOKENS
            else:
                exp_c = EXPECTED_TRUNK_TOKENS
            if c_val != exp_c:
                zero_or_bad_imat += 1
                failures.append(f"Unexpected token count on {base}: got {c_val}, expected {exp_c}")

        # Cauchy-Schwarz inequality: `(sum x^2) * N >= (sum x)^2` up to F32 storage rounding (`1e-4` rel tol)
        lhs = s2 * cnt
        rhs = s1 * s1
        if not np.all(lhs + 1e-6 >= rhs * (1.0 - 2e-4)):
            zero_or_bad_imat += 1
            failures.append(f"Cauchy-Schwarz violation in {base}")

    imat_sha = sha256_file(IMATRIX_PATH)
    imat_bytes = IMATRIX_PATH.stat().st_size
    del rd
    if zero_or_bad_imat == 0 and not failures:
        print(
            f"[OK] Verified imatrix_step6.gguf ({imat_bytes:,} B, 782 canonical weights, "
            "per-row energy > 0, Cauchy-Schwarz PASS, 0 NaN/Inf).",
            flush=True,
        )

    # Aggregate statistics across 48 trunk layers + MTP
    agg = {
        "ru_top50_min_median_max": [
            min(x["ru_top50"] for x in reap_stats_per_block),
            statistics.median(x["ru_top50"] for x in reap_stats_per_block),
            max(x["ru_top50"] for x in reap_stats_per_block),
        ],
        "ru_cond_top50_min_median_max": [
            min(x["ru_cond_top50"] for x in reap_stats_per_block),
            statistics.median(x["ru_cond_top50"] for x in reap_stats_per_block),
            max(x["ru_cond_top50"] for x in reap_stats_per_block),
        ],
        "p1_frontend_cond_top50_min_median_max": [
            min(x["p1_cond_top50"] for x in reap_stats_per_block),
            statistics.median(x["p1_cond_top50"] for x in reap_stats_per_block),
            max(x["p1_cond_top50"] for x in reap_stats_per_block),
        ],
        "p2_seogeo_cond_top50_min_median_max": [
            min(x["p2_cond_top50"] for x in reap_stats_per_block),
            statistics.median(x["p2_cond_top50"] for x in reap_stats_per_block),
            max(x["p2_cond_top50"] for x in reap_stats_per_block),
        ],
        "agentic_cond_top50_min_median_max": [
            min(x["agentic_cond_top50"] for x in reap_stats_per_block),
            statistics.median(x["agentic_cond_top50"] for x in reap_stats_per_block),
            max(x["agentic_cond_top50"] for x in reap_stats_per_block),
        ],
        "longctx_cond_top50_min_median_max": [
            min(x["longctx_cond_top50"] for x in reap_stats_per_block),
            statistics.median(x["longctx_cond_top50"] for x in reap_stats_per_block),
            max(x["longctx_cond_top50"] for x in reap_stats_per_block),
        ],
        "retained_weighted_ean_share_min_median_max": [
            round(min(x["retained_ean_share"] for x in reap_stats_per_block), 6),
            round(statistics.median(x["retained_ean_share"] for x in reap_stats_per_block), 6),
            round(max(x["retained_ean_share"] for x in reap_stats_per_block), 6),
        ],
        "vision_cond_top50_min_median_max": [
            min(x["vision_cond_top50"] for x in reap_stats_per_block),
            statistics.median(x["vision_cond_top50"] for x in reap_stats_per_block),
            max(x["vision_cond_top50"] for x in reap_stats_per_block),
        ],
        "p4_cond_top50_min_median_max": [
            min(x["p4_cond_top50"] for x in reap_stats_per_block),
            statistics.median(x["p4_cond_top50"] for x in reap_stats_per_block),
            max(x["p4_cond_top50"] for x in reap_stats_per_block),
        ],
        "jaccard_vs_pure_reap_min_median_max": [
            round(min(x["jaccard_vs_pure_reap"] for x in reap_stats_per_block), 6),
            round(statistics.median(x["jaccard_vs_pure_reap"] for x in reap_stats_per_block), 6),
            round(max(x["jaccard_vs_pure_reap"] for x in reap_stats_per_block), 6),
        ],
        "min_kept_expert_freq_across_all_49_blocks": min(x["min_kept_freq"] for x in reap_stats_per_block),
    }

    unverified_tensors_count = len(p_wmap) - (
        pure_ple_tensors_count + immutable_verified + gate_exact_verified + expert_weights_exact_verified
    )
    if unverified_tensors_count != 0:
        failures.append(f"unverified_tensors_count={unverified_tensors_count} != 0")

    elapsed = round(time.perf_counter() - t0, 2)
    report = {
        "status": "PASS" if not failures else "FAIL",
        "failures_count": len(failures),
        "failures": failures,
        "elapsed_sec": elapsed,
        "pruned_dir": str(PRUNED_DIR),
        "safetensors_files_count": len(ref_files),
        "hardlinked_ple_files_count": len(hardlink_files),
        "pure_ple_tensors_count": pure_ple_tensors_count,
        "immutable_non_expert_tensors_verified_bit_exact": immutable_verified,
        "sliced_expert_tensors_verified": sliced_shapes_verified,
        "gate_slices_verified_bit_exact": gate_exact_verified,
        "all_full_expert_tensors_verified_bit_exact": expert_weights_exact_verified,
        "unverified_tensors_count": unverified_tensors_count,
        "total_tensors_count": len(p_wmap),
        "donor_logical_param_bytes": DONOR_TOTAL_PARAM_BYTES,
        "pruned_expert_delta_bytes": NUM_MOE_BLOCKS * (DONOR_EXPERTS - KEEP_K) * BYTES_PER_EXPERT,
        "total_logical_param_bytes": total_computed_bytes,
        "new_physical_safetensors_bytes": sum((PRUNED_DIR / sf).stat().st_size for sf in non_ple_files),
        "hardlinked_ple_bytes_zero_extra_disk": sum((PRUNED_DIR / sf).stat().st_size for sf in hardlink_files),
        "work_residual_state_bytes": work_residual_bytes,
        "imatrix_gguf": {
            "path": str(IMATRIX_PATH),
            "bytes": imat_bytes,
            "sha256": imat_sha,
            "kv_header": kv_dict,
            "base_weights_count": len(by_base),
            "canonical_bijection_verified": len(imat_sym_diff) == 0,
            "gguf_tensors_count": len(by_base) * 3,
        },
        "metadata_sha256": metadata_hashes,
        "retention_aggregate_49_blocks": agg,
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"=== VERDICT: {report['status']} ({len(failures)} failures) in {elapsed}s -> {OUT_REPORT} ===", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
