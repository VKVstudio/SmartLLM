#!/usr/bin/env python3
"""Step 7 Verification Gate (Quantized GGUF & mmproj — 100% Closed-Form 1,086/1,086 Audit):

Verifies on CPU (`0` GPU VRAM):
1. Target quantized GGUF (`IQ3_S` or `IQ3_XXS`) is valid GGUF v3 with exact `1,086` tensors,
   exact `qwen4exp` KV metadata (`block_count=49`, `nextn_predict_layers=1`, `expert_count=205`,
   `hyper_connection.count=4`, `hyper_connection.low_rank=320`, `compress_ratios=[0,0,0,4]*12+[4]`),
   exact PLE `int64` constants vs donor shards `00005` & `00037`, and `quantize.imatrix.entries_count == 782`.
2. Direct `782/782` GGUF-to-GGUF bijection against `data/calib/imatrix_step6.gguf` (`0` missing, `0` extra, `0` shape mismatches).
3. Exhaustive closed-form qtype & shape partition across ALL `1,086 / 1,086` tensors (`unclassified_tensors_count == 0`):
   - `399` `F32`, `1` `F16`, `26` `BF16`, `1` `Q4_0`, `103` `Q8_0`, `101` `Q6_K`, `49` `Q4_K`, `98` `IQ4_NL`,
     `40` `IQ3_S`, and `268` `<expected-ftype>` (`IQ3_S` or `IQ3_XXS`).
4. Quantization log (`--quant-log`) contains `"have importance matrix data with 782 entries"`,
   only expected non-MUL_MAT entries (`token_embd.weight`, `blk.1.ple_conv1d.weight`) in
   `"did not find weights"`, and `0` occurrences of `"imatrix size"`.
5. Vision projector (`--mmproj-gguf`) exists, has `334` tensors, and `clip.projector_type == "qwen3vl_merger"`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from safetensors import safe_open

ROOT = Path(r"D:\projects\SmartLLM")
sys.path.insert(0, str(ROOT / "tools" / "llama.cpp" / "gguf-py"))
import gguf  # noqa: E402

DEFAULT_MODEL = ROOT / "models" / "SmartLLM-205E-IQ3_S.gguf"
DEFAULT_LOG = ROOT / "research" / "step7_raw" / "quantize_iq3_s.log"
DEFAULT_MMPROJ = ROOT / "models" / "mmproj-Qwen3.8-Flash-Next-BF16.gguf"
DEFAULT_IMATRIX = ROOT / "data" / "calib" / "imatrix_step6.gguf"
DONOR_PLE_SHARD_05 = ROOT / "models" / "Qwen3.8-Flash-Next" / "model-00005-of-00131.safetensors"
DONOR_PLE_SHARD_37 = ROOT / "models" / "Qwen3.8-Flash-Next" / "model-00037-of-00131.safetensors"
DEFAULT_OUT = ROOT / "research" / "step7_raw" / "verify_iq3_s_gguf.json"


def is_non_mulmat_model_tensor(name: str, shape: tuple[int, ...]) -> bool:
    if name.endswith(".ffn_gate_inp_shexp.weight"):
        return False
    if len(shape) <= 1 or name.endswith("_norm.weight"):
        return True
    if name in ("token_embd.weight", "per_layer_token_embd.weight"):
        return True
    if name.endswith((".ssm_conv1d.weight", ".ple_conv1d.weight")):
        return True
    return False


def load_imatrix_shapes(path: Path) -> dict[str, dict[str, tuple[int, ...]]]:
    rd = gguf.GGUFReader(str(path), mode="r")
    grouped: dict[str, dict[str, tuple[int, ...]]] = {}
    for t in rd.tensors:
        for suf in (".in_sum2", ".counts", ".in_sum"):
            if t.name.endswith(suf):
                base = t.name[: -len(suf)]
                grouped.setdefault(base, {})[suf[1:]] = tuple(int(x) for x in t.shape)
                break
    return grouped


def decode_kv(rd: gguf.GGUFReader) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, field in rd.fields.items():
        if k.startswith("GGUF."):
            continue
        if len(field.types) >= 2 and field.types[0] == gguf.GGUFValueType.ARRAY:
            elem_type = field.types[1]
            vals: list[Any] = []
            for idx in field.data:
                part = field.parts[idx]
                if elem_type == gguf.GGUFValueType.STRING:
                    vals.append(bytes(part).decode("utf-8", errors="replace"))
                elif isinstance(part, np.ndarray) and part.size == 1:
                    vals.append(part.item())
                else:
                    vals.append(part.tolist())
            out[k] = vals
        elif len(field.types) == 1 and field.types[0] == gguf.GGUFValueType.STRING:
            out[k] = bytes(field.parts[field.data[0]]).decode("utf-8", errors="replace")
        elif field.data:
            p = field.parts[field.data[0]]
            out[k] = p.item() if isinstance(p, np.ndarray) and p.size == 1 else p.tolist()
    return out


def expected_shape_for_tensor(name: str) -> tuple[int, ...] | None:
    """Return exact expected GGUF shape for every quantized/retained SmartLLM tensor."""
    if name == "per_layer_token_embd.weight":
        return (160, 320_001_536)
    if name == "blk.1.ple_conv1d.weight" or re.match(r"^blk\.\d+\.ssm_conv1d\.weight$", name):
        return (4, 10240)
    if re.match(r"^blk\.\d+\.indexer\.k_proj\.weight$", name):
        return (2560, 128)
    if re.match(r"^blk\.\d+\.indexer\.q_proj\.weight$", name):
        return (2560, 512)
    if re.match(r"^blk\.\d+\.ffn_down_exps\.weight$", name):
        return (640, 2560, 205)
    if re.match(r"^blk\.\d+\.ffn_down_shexp\.weight$", name):
        return (640, 2560)
    if re.match(r"^blk\.\d+\.ffn_(gate|up)_exps\.weight$", name):
        return (2560, 640, 205)
    if re.match(r"^blk\.\d+\.ffn_(gate|up)_shexp\.weight$", name):
        return (2560, 640)
    if re.match(r"^blk\.\d+\.ssm_beta_alpha\.weight$", name):
        return (2560, 96)
    if re.match(r"^blk\.\d+\.(ssm_out|attn_output)\.weight$", name):
        return (6144, 2560)
    if name in ("token_embd.weight", "output.weight"):
        return (2560, 248320)
    if re.match(r"^blk\.\d+\.(attn_k|attn_v)\.weight$", name):
        return (2560, 512)
    if re.match(r"^blk\.\d+\.attn_q\.weight$", name):
        return (2560, 12288)
    if re.match(r"^blk\.\d+\.attn_qkv_gate\.weight$", name):
        return (2560, 16384)
    if name in ("output_hc_down.weight", "blk.48.nextn.hc_head_down.weight"):
        return (10240, 320)
    if re.match(r"^blk\.\d+\.hc_(attn|ffn)_down_inject\.weight$", name):
        return (10240, 324)
    if name == "blk.1.ple_value.weight":
        return (2560, 2560)
    if name == "blk.1.ple_key.weight":
        return (2560, 10240)
    if name == "blk.48.nextn.eh_proj.weight":
        return (5120, 2560)
    if re.match(r"^(output_hc_up|blk\.48\.nextn\.hc_head_up|blk\.\d+\.hc_(attn|ffn)_up)\.weight$", name):
        return (320, 10240)
    if re.match(r"^blk\.\d+\.attn_[qk]_norm\.weight$", name):
        return (256,)
    if re.match(r"^blk\.\d+\.ffn_gate_inp_shexp\.weight$", name) or name == "blk.48.nextn.enorm.weight":
        return (2560,)
    if re.match(r"^blk\.\d+\.ffn_gate_inp\.weight$", name):
        return (2560, 205)
    if re.match(
        r"^(blk\.\d+\.(hc_attn|hc_ffn)_norm|output_hc_norm|blk\.48\.nextn\.(hnorm|hc_head_norm)|blk\.1\.ple_norm_(conv|key|query))\.weight$",
        name,
    ):
        return (10240,)
    if re.match(r"^(blk\.\d+\.indexer\.[qk]_norm|blk\.\d+\.ssm_norm)\.weight$", name):
        return (128,)
    if re.match(r"^blk\.\d+\.ssm_(a|dt\.bias)$", name):
        return (48,)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-gguf", type=Path, default=DEFAULT_MODEL)
    ap.add_argument("--quant-log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--mmproj-gguf", type=Path, default=DEFAULT_MMPROJ)
    ap.add_argument("--imatrix-gguf", type=Path, default=DEFAULT_IMATRIX)
    ap.add_argument("--expected-ftype", type=str, default="IQ3_S", choices=["IQ3_S", "IQ3_XXS"])
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    t0 = time.perf_counter()
    failures: list[str] = []

    if not args.model_gguf.exists():
        print(f"FATAL: Missing quantized model GGUF: {args.model_gguf}", flush=True)
        return 1

    model_bytes = args.model_gguf.stat().st_size
    rd_model = gguf.GGUFReader(str(args.model_gguf), mode="r")
    kv = decode_kv(rd_model)

    expected_kv = {
        "general.architecture": "qwen4exp",
        "qwen4exp.block_count": 49,
        "qwen4exp.nextn_predict_layers": 1,
        "qwen4exp.expert_count": 205,
        "qwen4exp.expert_used_count": 10,
        "qwen4exp.hyper_connection.count": 4,
        "qwen4exp.hyper_connection.low_rank": 320,
        "qwen4exp.attention.compress_ratios": [0, 0, 0, 4] * 12 + [4],
        "quantize.imatrix.entries_count": 782,
    }
    for k, exp_v in expected_kv.items():
        got_v = kv.get(k)
        if got_v != exp_v:
            failures.append(f"KV {k}={got_v!r} != {exp_v!r}")

    with safe_open(str(DONOR_PLE_SHARD_05), framework="pt", device="cpu") as f5:
        ref_mult = [int(x) for x in f5.get_tensor("model.language_model.layers.1.ple.ple_embedding.layer_multipliers").tolist()]
    with safe_open(str(DONOR_PLE_SHARD_37), framework="pt", device="cpu") as f37:
        ref_off = [int(x) for x in f37.get_tensor("model.language_model.layers.1.ple.ple_embedding.ngram_heads_offsets").tolist()]
        ref_voc = [int(x) for x in f37.get_tensor("model.language_model.layers.1.ple.ple_embedding.ngram_heads_vocab_sizes").tolist()]
    ple_constants_ok = (
        kv.get("qwen4exp.ple.layer_multipliers") == ref_mult
        and kv.get("qwen4exp.ple.head_offsets") == ref_off
        and kv.get("qwen4exp.ple.head_vocab_sizes") == ref_voc
    )
    if not ple_constants_ok:
        failures.append("PLE int64 hash constants in GGUF KV do not match donor shards 00005/00037")

    tensors: dict[str, tuple[tuple[int, ...], str, int]] = {}
    qtype_counts: dict[str, int] = {}
    for t in rd_model.tensors:
        shp = tuple(int(x) for x in t.shape)
        qname = t.tensor_type.name
        qtype_counts[qname] = qtype_counts.get(qname, 0) + 1
        tensors[t.name] = (shp, qname, int(t.n_bytes))

    if len(tensors) != 1086:
        failures.append(f"n_tensors={len(tensors)} != 1086")

    # Direct 782/782 GGUF-to-GGUF bijection vs data/calib/imatrix_step6.gguf
    imatrix_bijection_782 = False
    if not args.imatrix_gguf.exists():
        failures.append(f"Missing imatrix GGUF: {args.imatrix_gguf}")
    else:
        step6_imat = load_imatrix_shapes(args.imatrix_gguf)
        expected_from_model: dict[str, tuple[int, int]] = {}
        for name, (shp, _qname, _nbytes) in tensors.items():
            if is_non_mulmat_model_tensor(name, shp):
                continue
            expected_from_model[name] = (shp[0], 1) if len(shp) <= 2 else (shp[0], shp[2])
        miss_im = sorted(set(expected_from_model) - set(step6_imat))
        extra_im = sorted(set(step6_imat) - set(expected_from_model))
        bad_im_shp = [
            name
            for name, exp_s2 in expected_from_model.items()
            if name in step6_imat
            and (
                step6_imat[name].get("in_sum2") != exp_s2
                or step6_imat[name].get("counts") != (1, exp_s2[1])
            )
        ]
        if miss_im or extra_im or bad_im_shp or len(expected_from_model) != 782:
            failures.append(
                f"imatrix 782 bijection failed: count={len(expected_from_model)}, miss={miss_im[:5]}, extra={extra_im[:5]}, shp={bad_im_shp[:5]}"
            )
        else:
            imatrix_bijection_782 = True

    ple_emb = tensors.get("per_layer_token_embd.weight")
    if ple_emb is None:
        failures.append("Missing per_layer_token_embd.weight")
    else:
        if ple_emb[0] != (160, 320_001_536):
            failures.append(f"per_layer_token_embd.weight shape={ple_emb[0]} != (160, 320001536)")
        if ple_emb[1] != "Q4_0":
            failures.append(f"per_layer_token_embd.weight qtype={ple_emb[1]} != Q4_0")
        if ple_emb[2] != 28_800_138_240:
            failures.append(f"per_layer_token_embd.weight bytes={ple_emb[2]} != 28800138240")

    closed_rules: list[tuple[str, re.Pattern[str], str, int, tuple[int, ...] | None]] = [
        ("ple_embd", re.compile(r"^per_layer_token_embd\.weight$"), "Q4_0", 1, (160, 320_001_536)),
        ("ple_conv1d", re.compile(r"^blk\.1\.ple_conv1d\.weight$"), "F16", 1, None),
        ("indexer_qk_proj", re.compile(r"^blk\.\d+\.indexer\.[qk]_proj\.weight$"), "BF16", 26, None),
        ("ffn_down_exps", re.compile(r"^blk\.\d+\.ffn_down_exps\.weight$"), "IQ4_NL", 49, (640, 2560, 205)),
        ("ffn_down_shexp", re.compile(r"^blk\.\d+\.ffn_down_shexp\.weight$"), "IQ4_NL", 49, (640, 2560)),
        ("ffn_gate_up_exps", re.compile(r"^blk\.\d+\.ffn_(gate|up)_exps\.weight$"), args.expected_ftype, 98, (2560, 640, 205)),
        ("ffn_gate_up_shexp", re.compile(r"^blk\.\d+\.ffn_(gate|up)_shexp\.weight$"), args.expected_ftype, 98, None),
        ("ssm_weights_quant", re.compile(r"^blk\.\d+\.ssm_(beta_alpha|out)\.weight$"), args.expected_ftype, 72, None),
        ("token_and_attn_out", re.compile(r"^(token_embd|blk\.\d+\.attn_output)\.weight$"), "IQ3_S", 14, None),
        ("attn_qk", re.compile(r"^blk\.\d+\.attn_[qk]\.weight$"), "IQ3_S", 26, None),
        ("attn_qkv_gate_and_v", re.compile(r"^blk\.\d+\.(attn_qkv_gate|attn_v)\.weight$"), "Q4_K", 49, None),
        ("output_weight", re.compile(r"^output\.weight$"), "Q6_K", 1, None),
        ("hc_down", re.compile(r"^(output_hc_down|blk\.48\.nextn\.hc_head_down|blk\.\d+\.hc_(attn|ffn)_down_inject)\.weight$"), "Q6_K", 100, None),
        ("ple_kv", re.compile(r"^blk\.1\.ple_(key|value)\.weight$"), "Q8_0", 2, None),
        ("nextn_eh_proj", re.compile(r"^blk\.48\.nextn\.eh_proj\.weight$"), "Q8_0", 1, None),
        ("hc_up", re.compile(r"^(output_hc_up|blk\.48\.nextn\.hc_head_up|blk\.\d+\.hc_(attn|ffn)_up)\.weight$"), "Q8_0", 100, None),
        ("f32_attn_norms", re.compile(r"^blk\.\d+\.attn_[qk]_norm\.weight$"), "F32", 26, None),
        ("f32_moe_routers", re.compile(r"^blk\.\d+\.ffn_gate_inp(_shexp)?\.weight$"), "F32", 98, None),
        ("f32_hc_and_nextn_norms", re.compile(r"^(blk\.\d+\.(hc_attn|hc_ffn)_norm|output_hc_norm|blk\.48\.nextn\.(enorm|hnorm|hc_head_norm))\.weight$"), "F32", 102, None),
        ("f32_indexer_norms", re.compile(r"^blk\.\d+\.indexer\.[qk]_norm\.weight$"), "F32", 26, None),
        ("f32_ple_norms", re.compile(r"^blk\.1\.ple_norm_(conv|key|query)\.weight$"), "F32", 3, None),
        ("f32_ssm_state", re.compile(r"^blk\.\d+\.ssm_(a|conv1d\.weight|dt\.bias|norm\.weight)$"), "F32", 144, None),
    ]

    rule_counts: dict[str, int] = {r[0]: 0 for r in closed_rules}
    unclassified: list[str] = []
    bad_qtypes: list[str] = []
    bad_shapes: list[str] = []

    for name, (shp, qt, _nb) in tensors.items():
        matched = [r for r in closed_rules if r[1].search(name)]
        if len(matched) != 1:
            unclassified.append(f"{name} (matches={len(matched)}, qtype={qt})")
            continue
        rname, _pat, exp_qt, _exp_cnt, exp_shp = matched[0]
        rule_counts[rname] += 1
        if qt != exp_qt:
            bad_qtypes.append(f"{name}={qt} (expected {exp_qt})")
        strict_shp = exp_shp if exp_shp is not None else expected_shape_for_tensor(name)
        if strict_shp is None or shp != strict_shp:
            bad_shapes.append(f"{name}={shp} (expected {strict_shp})")

    for rname, _pat, _exp_qt, exp_cnt, _exp_shp in closed_rules:
        if rule_counts[rname] != exp_cnt:
            failures.append(f"Rule {rname} count={rule_counts[rname]} != {exp_cnt}")
    if unclassified:
        failures.append(f"Unclassified/ambiguous tensors ({len(unclassified)}): {unclassified[:10]}")
    if bad_qtypes:
        failures.append(f"Mismatched qtypes ({len(bad_qtypes)}): {bad_qtypes[:10]}")
    if bad_shapes:
        failures.append(f"Mismatched shapes ({len(bad_shapes)}): {bad_shapes[:10]}")

    counts = {
        "hc_down": rule_counts["hc_down"],
        "hc_up": rule_counts["hc_up"],
        "ffn_down_exps": rule_counts["ffn_down_exps"],
        "ffn_gate_up_exps": rule_counts["ffn_gate_up_exps"],
        "indexer_qk_proj": rule_counts["indexer_qk_proj"],
        "attn_qk": rule_counts["attn_qk"],
    }

    log_summary: dict[str, Any] = {"path": str(args.quant_log), "exists": args.quant_log.exists()}
    if not args.quant_log.exists():
        failures.append(f"Missing quant log: {args.quant_log}")
    else:
        raw_log = args.quant_log.read_bytes()
        if raw_log.startswith((b"\xff\xfe", b"\xfe\xff")):
            log_text = raw_log.decode("utf-16", errors="replace")
        else:
            log_text = raw_log.decode("utf-8-sig", errors="replace")
        has_782 = "have importance matrix data with 782 entries" in log_text
        missing_imatrix_tensors = re.findall(r"did not find weights for (\S+)", log_text)
        allowed_missing = {"token_embd.weight", "blk.1.ple_conv1d.weight"}
        unexpected_missing = sorted(set(missing_imatrix_tensors) - allowed_missing)
        cnt_did_not_find = len(missing_imatrix_tensors)
        cnt_imatrix_size = log_text.count("imatrix size")
        log_summary.update(
            {
                "has_782_entries_line": has_782,
                "did_not_find_weights_count": cnt_did_not_find,
                "missing_imatrix_tensors": missing_imatrix_tensors,
                "unexpected_missing_imatrix_tensors": unexpected_missing,
                "imatrix_size_warning_count": cnt_imatrix_size,
            }
        )
        if not has_782:
            failures.append("Quant log missing 'have importance matrix data with 782 entries'")
        if unexpected_missing:
            failures.append(f"Quant log has unexpected 'did not find weights' tensors: {unexpected_missing}")
        if cnt_imatrix_size != 0:
            failures.append(f"Quant log has {cnt_imatrix_size} 'imatrix size' occurrences")

    mmproj_summary: dict[str, Any] = {"path": str(args.mmproj_gguf), "exists": args.mmproj_gguf.exists()}
    if not args.mmproj_gguf.exists():
        failures.append(f"Missing mmproj GGUF: {args.mmproj_gguf}")
    else:
        rd_mm = gguf.GGUFReader(str(args.mmproj_gguf), mode="r")
        mm_kv = decode_kv(rd_mm)
        mm_n = len(rd_mm.tensors)
        proj_type = mm_kv.get("clip.projector_type")
        mmproj_summary.update(
            {
                "bytes": args.mmproj_gguf.stat().st_size,
                "gib": round(args.mmproj_gguf.stat().st_size / (1024**3), 4),
                "n_tensors": mm_n,
                "clip.projector_type": proj_type,
            }
        )
        if mm_n != 334:
            failures.append(f"mmproj n_tensors={mm_n} != 334")
        if proj_type != "qwen3vl_merger":
            failures.append(f"mmproj clip.projector_type={proj_type!r} != 'qwen3vl_merger'")

    elapsed = round(time.perf_counter() - t0, 2)
    report = {
        "status": "PASS" if not failures else "FAIL",
        "failures_count": len(failures),
        "failures": failures,
        "elapsed_sec": elapsed,
        "model_gguf": {
            "path": str(args.model_gguf),
            "expected_ftype": args.expected_ftype,
            "bytes": model_bytes,
            "gib": round(model_bytes / (1024**3), 4),
            "n_tensors": len(tensors),
            "ple_constants_match_donor": ple_constants_ok,
            "imatrix_bijection_782": imatrix_bijection_782,
            "all_1086_shapes_verified": len(bad_shapes) == 0 and len(unclassified) == 0 and len(tensors) == 1086,
            "unclassified_tensors_count": len(unclassified),
            "qtype_counts": qtype_counts,
            "group_counts": counts,
            "closed_rule_counts": rule_counts,
            "per_layer_token_embd": ple_emb,
        },
        "quant_log": log_summary,
        "mmproj_gguf": mmproj_summary,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"=== STEP 7 QUANT GATE: {report['status']} ({len(failures)} failures) in {elapsed}s -> {args.out_json} ===", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
