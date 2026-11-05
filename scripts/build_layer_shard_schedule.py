import json
import pathlib
from collections import defaultdict

ROOT = pathlib.Path(r"D:\projects\SmartLLM")


def main():
    idx_path = ROOT / "research" / "step1_raw" / "model.safetensors.index.json"
    idx_data = json.loads(idx_path.read_text(encoding="utf-8"))
    wm = idx_data["weight_map"]
    total_size = idx_data["metadata"]["total_size"]

    # Map every shard -> list of tensor names
    shard_to_tensors = defaultdict(list)
    for tensor_name, shard_name in wm.items():
        shard_to_tensors[shard_name].append(tensor_name)

    # Classify every tensor into logical step units:
    # - root: embed_tokens, lm_head, model.language_model.hyper_connection_mixer.*
    # - visual: model.visual.*
    # - ple: model.language_model.layers.1.ple.*
    # - mtp: mtp.*
    # - layer_0 .. layer_47: model.language_model.layers.{i}.* (excluding ple)
    unit_to_tensors = defaultdict(list)
    unit_to_shards = defaultdict(set)
    shard_to_units = defaultdict(set)

    for tname, sname in wm.items():
        if tname.startswith("model.visual."):
            unit = "visual"
        elif tname.startswith("model.language_model.layers.1.ple."):
            unit = "ple_layer_1"
        elif tname.startswith("mtp."):
            unit = "mtp"
        elif tname.startswith("model.language_model.layers."):
            parts = tname.split(".")
            layer_idx = int(parts[3])
            unit = f"layer_{layer_idx:02d}"
        else:
            unit = "root"
        unit_to_tensors[unit].append((tname, sname))
        unit_to_shards[unit].add(sname)
        shard_to_units[sname].add(unit)

    # Simulate streaming execution order:
    # Phase 0 (Pre-loop): Evacuate/copy non-layer tensors (root, visual, mtp non-expert or full mtp) OR track refcounts across:
    # Let's compute two refcount schedules:
    # Schedule A: If root + visual + mtp are evacuated/processed first (or mtp is processed at the end after layer_47),
    # which exact layer (0..47) is the LAST consumer of each shard?
    # Schedule B: Pure layer-by-layer (0..47) last-layer consumer of each shard (ignoring PLE shards 00005..00037 which only hold PLE + layer_1/layer_10 boundary).
    layers_table = []
    for i in range(48):
        u = f"layer_{i:02d}"
        prefix = f"model.language_model.layers.{i}."
        shards = sorted(unit_to_shards[u])
        t_map = {t: s for t, s in unit_to_tensors[u]}
        attn_type = (
            "full_attention (QSA)"
            if f"{prefix}self_attn.q_proj.weight" in t_map
            else "linear_attention (GDN)"
        )
        # Find shared shards with other units
        shared_with = {}
        for s in shards:
            others = sorted(shard_to_units[s] - {u})
            if others:
                shared_with[s] = others
        layers_table.append(
            {
                "layer_idx": i,
                "attn_type": attn_type,
                "has_ple": (i == 1),
                "tensor_count": len(t_map),
                "shards": shards,
                "gate_up_proj_shard": t_map[f"{prefix}mlp.experts.gate_up_proj"],
                "down_proj_shard": t_map[f"{prefix}mlp.experts.down_proj"],
                "router_gate_shard": t_map[f"{prefix}mlp.gate.weight"],
                "shared_expert_shards": sorted(
                    {
                        t_map[f"{prefix}mlp.shared_expert.gate_proj.weight"],
                        t_map[f"{prefix}mlp.shared_expert.up_proj.weight"],
                        t_map[f"{prefix}mlp.shared_expert.down_proj.weight"],
                        t_map[f"{prefix}mlp.shared_expert_gate.weight"],
                    }
                ),
                "shared_shards_with_other_units": shared_with,
            }
        )

    # Simulate exact shard lifecycle during sequential traversal:
    # Order: [root, visual] -> layer_00 .. layer_47 -> mtp
    # Wait: if we evacuate `mtp.*` tensors (or prune `mtp.layers.0` as soon as its shards `00037..00124` are downloaded during layers 0..47!),
    # let's see what happens if we evacuate/save `mtp.*` tensors when their shard is first opened, vs keeping the shard until `mtp` at the end!
    # Look! `mtp.*` has 31 tensors spread across 28 shards (`00037..00124`) because in `model.safetensors.index.json`, every shard boundary had a small `mtp.*` tensor packed into it (or lexicographically at the end)!
    # Let's check WHICH shards contain `mtp.*` tensors!
    mtp_shards = sorted(unit_to_shards["mtp"])
    mtp_tensors_by_shard = defaultdict(list)
    for t, s in unit_to_tensors["mtp"]:
        mtp_tensors_by_shard[s].append(t)

    # Check if we evacuate any `mtp.*` / `root` / `visual` tensor on-the-fly when a shard is opened:
    # Then each shard is ONLY needed by `layer_00..layer_47` (plus `ple_layer_1` for shards 00005..00037)!
    # Let's compute for every shard 00001..00131:
    # 1) All units present in that shard
    # 2) Last layer in 0..47 that uses that shard (so once that layer finishes and any root/visual/mtp tensor in that shard is evacuated, refcount == 0 and the shard can be deleted immediately!)
    shard_summary = {}
    for s_idx in range(1, 132):
        sname = f"model-{s_idx:05d}-of-00131.safetensors"
        units = sorted(shard_to_units[sname])
        layer_nums = [
            int(u.split("_")[1]) for u in units if u.startswith("layer_")
        ]
        last_layer = max(layer_nums) if layer_nums else None
        first_layer = min(layer_nums) if layer_nums else None
        shard_summary[sname] = {
            "units": units,
            "tensor_count": len(shard_to_tensors[sname]),
            "first_layer_in_0_47": first_layer,
            "last_layer_in_0_47": last_layer,
            "has_mtp": "mtp" in units,
            "has_ple": "ple_layer_1" in units,
            "has_visual": "visual" in units,
            "has_root": "root" in units,
            "tensors": sorted(shard_to_tensors[sname]),
        }

    # For each layer i in 0..47, which shards reach last_layer_in_0_47 == i?
    for entry in layers_table:
        i = entry["layer_idx"]
        releasable = [
            s
            for s in entry["shards"]
            if shard_summary[s]["last_layer_in_0_47"] == i
        ]
        entry["shards_reaching_refcount_zero_after_layer"] = releasable

    out = {
        "source_url": "https://huggingface.co/Qwen/Qwen3.8-Flash-Next/resolve/main/model.safetensors.index.json",
        "total_size_bytes": total_size,
        "total_shards": 131,
        "total_tensors": len(wm),
        "unit_tensor_counts": {k: len(v) for k, v in sorted(unit_to_tensors.items())},
        "mtp_shards_count": len(mtp_shards),
        "mtp_tensors_by_shard": dict(sorted(mtp_tensors_by_shard.items())),
        "layers_0_to_47": layers_table,
        "shards_00001_to_00131": shard_summary,
    }
    out_path = ROOT / "research" / "step5_6_layer_shard_schedule.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
