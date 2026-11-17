#!/usr/bin/env python3
"""Step 7 Verification Gate (Phase 1): Staging GGUF (`128.15 GiB`) & C++ `imatrix` Bijection.

Verifies on CPU (`0` GPU VRAM):
1. `C:\\SmartLLM_staging\\SmartLLM-205E-BF16-Q4PLE.gguf` exists, is valid GGUF v3, has exact `1,086` tensors,
   `qwen4exp.expert_count == 205`, `per_layer_token_embd.weight` stored as `Q4_0` with GGML shape `(160, 320001536)`,
   exact 45-bit `ple_layer_multipliers`, `ple_head_offsets`, and `ple_head_vocab_sizes` vs donor `pruned_safetensors`.
2. Direct GGUF-to-GGUF bijection between `SmartLLM-205E-BF16-Q4PLE.gguf` and `data/calib/imatrix_step6.gguf`:
   every quantizable 2D/3D `MUL_MAT` / `MUL_MAT_ID` tensor in the converted model GGUF matches one of the `782`
   canonical weights in `imatrix_step6.gguf` with exact `(ne0, n_experts_or_1)` shape (`0` missing, `0` extra).
3. Direct comparison against 1-chunk C++ `llama-imatrix.exe` output (`--cpp-imatrix` optional path), verifying
   key set & shape identity across all emitted C++ weights.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from safetensors import safe_open

ROOT = Path(r"D:\projects\SmartLLM")
sys.path.insert(0, str(ROOT / "tools" / "llama.cpp" / "gguf-py"))
import gguf  # noqa: E402

DEFAULT_STAGING_GGUF = Path(r"C:\SmartLLM_staging\SmartLLM-205E-BF16-Q4PLE.gguf")
DEFAULT_IMATRIX_GGUF = ROOT / "data" / "calib" / "imatrix_step6.gguf"
PRUNED_PLE_BOUNDARY = ROOT / "models" / "pruned_safetensors" / "model-ple-boundary.safetensors"
DONOR_PLE_SHARD_05 = ROOT / "models" / "Qwen3.8-Flash-Next" / "model-00005-of-00131.safetensors"
DONOR_PLE_SHARD_37 = ROOT / "models" / "Qwen3.8-Flash-Next" / "model-00037-of-00131.safetensors"
OUT_JSON = ROOT / "research" / "step7_raw" / "verify_staging_gguf.json"


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


def is_non_mulmat_model_tensor(name: str, shape: tuple[int, ...]) -> bool:
    """Identify GGUF model tensors that do not consume `imatrix` in `qwen4exp`."""
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


def _norm_imat_shape(shp: tuple[int, ...]) -> tuple[int, int]:
    """Normalize GGUF 1D `(N,)` and 2D `(N, 1)` shapes to `(N, ne1)`."""
    if len(shp) == 1:
        return (shp[0], 1)
    if len(shp) == 2:
        return (shp[0], shp[1])
    raise ValueError(f"Unexpected imatrix tensor shape rank {len(shp)}: {shp}")


def load_cpp_imatrix_audit(
    path: Path,
) -> tuple[dict[str, dict[str, tuple[int, ...]]], list[str], list[str], int]:
    """Load shapes and audit finiteness, non-negativity, and positive energy on core imatrix tensors."""
    rd = gguf.GGUFReader(str(path), mode="r")
    grouped: dict[str, dict[str, tuple[int, ...]]] = {}
    nonfinite: list[str] = []
    negative: list[str] = []
    positive_energy_weights = 0
    for t in rd.tensors:
        for suf in (".in_sum2", ".counts", ".in_sum"):
            if t.name.endswith(suf):
                arr = np.asarray(t.data)
                if not bool(np.all(np.isfinite(arr))):
                    nonfinite.append(t.name)
                base = t.name[: -len(suf)]
                grouped.setdefault(base, {})[suf[1:]] = tuple(int(x) for x in t.shape)
                if suf in (".in_sum2", ".counts") and bool(np.any(arr < 0)):
                    negative.append(t.name)
                if suf == ".in_sum2" and float(np.sum(arr, dtype=np.float64)) > 0.0:
                    positive_energy_weights += 1
                break
    return grouped, nonfinite, negative, positive_energy_weights


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging-gguf", type=Path, default=DEFAULT_STAGING_GGUF)
    ap.add_argument("--imatrix-gguf", type=Path, default=DEFAULT_IMATRIX_GGUF)
    ap.add_argument("--cpp-imatrix", type=Path, nargs="*", default=[])
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    t0 = time.perf_counter()
    failures: list[str] = []

    if not args.staging_gguf.exists():
        print(f"FATAL: Missing staging GGUF: {args.staging_gguf}", flush=True)
        return 1

    st_bytes = args.staging_gguf.stat().st_size
    rd_model = gguf.GGUFReader(str(args.staging_gguf), mode="r")
    kv = decode_kv(rd_model)

    arch = kv.get("general.architecture")
    if arch != "qwen4exp":
        failures.append(f"general.architecture={arch!r} != 'qwen4exp'")
    if kv.get("qwen4exp.expert_count") != 205:
        failures.append(f"qwen4exp.expert_count={kv.get('qwen4exp.expert_count')} != 205")
    if kv.get("qwen4exp.expert_used_count") != 10:
        failures.append(f"qwen4exp.expert_used_count={kv.get('qwen4exp.expert_used_count')} != 10")
    if kv.get("qwen4exp.block_count") != 49:
        failures.append(f"qwen4exp.block_count={kv.get('qwen4exp.block_count')} != 49")
    if kv.get("qwen4exp.nextn_predict_layers") != 1:
        failures.append(f"qwen4exp.nextn_predict_layers={kv.get('qwen4exp.nextn_predict_layers')} != 1")
    if kv.get("qwen4exp.hyper_connection.count") != 4:
        failures.append(f"qwen4exp.hyper_connection.count={kv.get('qwen4exp.hyper_connection.count')} != 4")
    if kv.get("qwen4exp.hyper_connection.low_rank") != 320:
        failures.append(f"qwen4exp.hyper_connection.low_rank={kv.get('qwen4exp.hyper_connection.low_rank')} != 320")
    expected_compress = [0, 0, 0, 4] * 12 + [4]
    if kv.get("qwen4exp.attention.compress_ratios") != expected_compress:
        failures.append(f"qwen4exp.attention.compress_ratios={kv.get('qwen4exp.attention.compress_ratios')} != {expected_compress}")
    if kv.get("qwen4exp.ple.layers") != [1] and kv.get("qwen4exp.ple_layers") != [1]:
        ple_kv = {k: v for k, v in kv.items() if "ple" in k}
        if [1] not in ple_kv.values():
            failures.append(f"Missing 0-based PLE layer [1] in KV: {ple_kv}")

    # Verify exact int64 PLE hash constants against model-ple-boundary.safetensors or donor shards
    if PRUNED_PLE_BOUNDARY.exists():
        with safe_open(str(PRUNED_PLE_BOUNDARY), framework="pt", device="cpu") as f:
            ref_mult = [int(x) for x in f.get_tensor("model.language_model.layers.1.ple.ple_embedding.layer_multipliers").tolist()]
            ref_off = [int(x) for x in f.get_tensor("model.language_model.layers.1.ple.ple_embedding.ngram_heads_offsets").tolist()]
            ref_voc = [int(x) for x in f.get_tensor("model.language_model.layers.1.ple.ple_embedding.ngram_heads_vocab_sizes").tolist()]
    else:
        with safe_open(str(DONOR_PLE_SHARD_05), framework="pt", device="cpu") as f5:
            ref_mult = [int(x) for x in f5.get_tensor("model.language_model.layers.1.ple.ple_embedding.layer_multipliers").tolist()]
        with safe_open(str(DONOR_PLE_SHARD_37), framework="pt", device="cpu") as f37:
            ref_off = [int(x) for x in f37.get_tensor("model.language_model.layers.1.ple.ple_embedding.ngram_heads_offsets").tolist()]
            ref_voc = [int(x) for x in f37.get_tensor("model.language_model.layers.1.ple.ple_embedding.ngram_heads_vocab_sizes").tolist()]

    kv_mult = next((v for k, v in kv.items() if k.endswith("layer_multipliers")), None)
    kv_off = next((v for k, v in kv.items() if k.endswith("head_offsets")), None)
    kv_voc = next((v for k, v in kv.items() if k.endswith("head_vocab_sizes")), None)
    if kv_mult != ref_mult:
        failures.append(f"PLE layer_multipliers mismatch: {kv_mult} != {ref_mult}")
    if kv_off != ref_off:
        failures.append(f"PLE head_offsets mismatch: {kv_off} != {ref_off}")
    if kv_voc != ref_voc:
        failures.append(f"PLE head_vocab_sizes mismatch: {kv_voc} != {ref_voc}")

    model_tensors: dict[str, tuple[tuple[int, ...], str, int]] = {}
    qtype_counts: dict[str, int] = {}
    for t in rd_model.tensors:
        shp = tuple(int(x) for x in t.shape)
        qname = t.tensor_type.name
        qtype_counts[qname] = qtype_counts.get(qname, 0) + 1
        model_tensors[t.name] = (shp, qname, int(t.n_bytes))

    if len(model_tensors) != 1086:
        failures.append(f"model n_tensors={len(model_tensors)} != 1086")

    ple_emb = model_tensors.get("per_layer_token_embd.weight")
    if ple_emb is None:
        failures.append("Missing per_layer_token_embd.weight in staging GGUF")
    else:
        if ple_emb[1] != "Q4_0":
            failures.append(f"per_layer_token_embd.weight type={ple_emb[1]} != Q4_0")
        if ple_emb[0] != (160, 320_001_536):
            failures.append(f"per_layer_token_embd.weight shape={ple_emb[0]} != (160, 320001536)")

    # Direct GGUF-to-GGUF bijection against data/calib/imatrix_step6.gguf
    step6_imat = load_imatrix_shapes(args.imatrix_gguf)
    expected_from_model: dict[str, tuple[int, int]] = {}
    for name, (shp, _qname, _nbytes) in model_tensors.items():
        if is_non_mulmat_model_tensor(name, shp):
            continue
        if len(shp) == 2:
            expected_from_model[name] = (shp[0], 1)
        elif len(shp) == 3:
            expected_from_model[name] = (shp[0], shp[2])
        else:
            failures.append(f"Unexpected tensor rank {len(shp)} on {name}: {shp}")

    missing_in_imat = sorted(set(expected_from_model) - set(step6_imat))
    extra_in_imat = sorted(set(step6_imat) - set(expected_from_model))
    if missing_in_imat:
        failures.append(f"Model MUL_MAT weights missing in imatrix_step6.gguf ({len(missing_in_imat)}): {missing_in_imat[:10]}")
    if extra_in_imat:
        failures.append(f"Extra weights in imatrix_step6.gguf not in model ({len(extra_in_imat)}): {extra_in_imat[:10]}")

    shape_mismatches: list[str] = []
    for name, exp_s2 in expected_from_model.items():
        if name not in step6_imat:
            continue
        got_s2 = step6_imat[name].get("in_sum2")
        got_cnt = step6_imat[name].get("counts")
        exp_cnt = (1, exp_s2[1])
        if got_s2 != exp_s2 or got_cnt != exp_cnt:
            shape_mismatches.append(f"{name}: model expects {exp_s2}/{exp_cnt}, imatrix has {got_s2}/{got_cnt}")
    if shape_mismatches:
        failures.append(f"GGUF-to-GGUF imatrix shape mismatches ({len(shape_mismatches)}): {shape_mismatches[:10]}")

    cpp_reports: list[dict[str, Any]] = []
    for cpp_path in args.cpp_imatrix:
        if not cpp_path.exists():
            failures.append(f"Missing C++ imatrix file: {cpp_path}")
            continue
        cpp_imat, cpp_nonfinite, cpp_negative, pos_energy_cnt = load_cpp_imatrix_audit(cpp_path)
        cpp_only = sorted(set(cpp_imat) - set(step6_imat))
        step6_only = sorted(set(step6_imat) - set(cpp_imat))
        cpp_shape_bad: list[str] = []
        for k in sorted(set(cpp_imat) & set(step6_imat)):
            if (
                _norm_imat_shape(cpp_imat[k]["in_sum2"]) != _norm_imat_shape(step6_imat[k]["in_sum2"])
                or _norm_imat_shape(cpp_imat[k]["counts"]) != _norm_imat_shape(step6_imat[k]["counts"])
            ):
                cpp_shape_bad.append(f"{k}: cpp={cpp_imat[k]} vs step6={step6_imat[k]}")
        if cpp_nonfinite:
            failures.append(f"C++ imatrix {cpp_path.name} has non-finite tensors ({len(cpp_nonfinite)}): {cpp_nonfinite[:5]}")
        if cpp_negative:
            failures.append(f"C++ imatrix {cpp_path.name} has negative tensors ({len(cpp_negative)}): {cpp_negative[:5]}")
        if cpp_only or cpp_shape_bad:
            failures.append(f"C++ imatrix {cpp_path.name} mismatch: cpp_only={cpp_only}, shape_bad={cpp_shape_bad[:5]}")
        if "782" in cpp_path.name and (len(cpp_imat) != 781 or step6_only != ["blk.48.nextn.eh_proj.weight"]):
            failures.append(
                f"C++ imatrix {cpp_path.name} expected 781 C++ weights (all except eh_proj ne1=hc=4<16), got {len(cpp_imat)} weights, missing={step6_only}"
            )
        if "b11954" in cpp_path.name:
            expected_omitted = {"output_hc_down.weight", "output_hc_up.weight"} | {
                k for k in step6_imat if k.startswith("blk.48.")
            }
            if set(step6_only) != expected_omitted:
                failures.append(
                    f"C++ imatrix {cpp_path.name} trunk diff mismatch: unexpected={sorted(set(step6_only) ^ expected_omitted)}"
                )
        cpp_reports.append(
            {
                "path": str(cpp_path),
                "bytes": cpp_path.stat().st_size,
                "cpp_weights_count": len(cpp_imat),
                "positive_energy_weights_count": pos_energy_cnt,
                "nonfinite_tensors_count": len(cpp_nonfinite),
                "negative_tensors_count": len(cpp_negative),
                "intersection_with_step6_count": len(set(cpp_imat) & set(step6_imat)),
                "cpp_only_keys": cpp_only,
                "step6_only_keys": step6_only,
                "shape_mismatches": cpp_shape_bad,
            }
        )

    elapsed = round(time.perf_counter() - t0, 2)
    summary_kv = {
        k: v
        for k, v in kv.items()
        if not k.startswith("tokenizer.ggml.tokens") and not k.startswith("tokenizer.ggml.merges") and not k.startswith("tokenizer.ggml.token_type")
    }
    report = {
        "status": "PASS" if not failures else "FAIL",
        "failures_count": len(failures),
        "failures": failures,
        "elapsed_sec": elapsed,
        "staging_gguf": {
            "path": str(args.staging_gguf),
            "bytes": st_bytes,
            "gib": round(st_bytes / (1024**3), 4),
            "n_tensors": len(model_tensors),
            "qtype_counts": qtype_counts,
            "per_layer_token_embd": ple_emb,
            "kv_summary": summary_kv,
        },
        "direct_model_vs_imatrix_step6": {
            "model_mulmat_weights_count": len(expected_from_model),
            "imatrix_step6_weights_count": len(step6_imat),
            "exact_bijection": not missing_in_imat and not extra_in_imat and not shape_mismatches,
            "missing_in_imatrix": missing_in_imat,
            "extra_in_imatrix": extra_in_imat,
            "shape_mismatches": shape_mismatches,
        },
        "cpp_imatrix_comparisons": cpp_reports,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"=== STEP 7 STAGING GATE: {report['status']} ({len(failures)} failures) in {elapsed}s -> {args.out_json} ===", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
