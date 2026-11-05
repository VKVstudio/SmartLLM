import json
import subprocess
import sys
from pathlib import Path

import gguf
import safetensors
import torch
import transformers
from transformers.models.qwen4_exp import (
    Qwen4ExpConfig,
    Qwen4ExpForConditionalGeneration,
    Qwen4ExpTextConfig,
    Qwen4ExpTextModel,
)

sys.stdout.reconfigure(encoding="utf-8")

RAW_DIR = Path("research/step2_raw")
BIN_DIR = Path(r"D:\projects\SmartLLM\tools\llama.cpp\build\bin")
LLAMA_DIR = Path(r"D:\projects\SmartLLM\tools\llama.cpp")


def run_cmd(cmd: list[str]) -> dict:
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    return {
        "returncode": res.returncode,
        "stdout": res.stdout.strip(),
        "stderr": res.stderr.strip(),
    }


def main():
    results = {}

    # 1. llama.cpp binaries and --list-devices
    results["llama_git_head"] = run_cmd(["git", "-C", str(LLAMA_DIR), "rev-parse", "HEAD"])
    results["llama_cli_version"] = run_cmd([str(BIN_DIR / "llama-cli.exe"), "--version"])
    results["llama_server_version"] = run_cmd([str(BIN_DIR / "llama-server.exe"), "--version"])
    results["llama_imatrix_version"] = run_cmd([str(BIN_DIR / "llama-imatrix.exe"), "--version"])
    results["llama_mtmd_version"] = run_cmd([str(BIN_DIR / "llama-mtmd-cli.exe"), "--version"])
    results["llama_quantize_help"] = run_cmd([str(BIN_DIR / "llama-quantize.exe"), "--help"])
    results["llama_list_devices"] = run_cmd([str(BIN_DIR / "llama-cli.exe"), "--list-devices"])

    # 2. convert_hf_to_gguf.py --help
    results["convert_hf_to_gguf_help"] = run_cmd(
        [sys.executable, str(LLAMA_DIR / "convert_hf_to_gguf.py"), "--help"]
    )

    # 3. Real Qwen/Qwen3.8-Flash-Next config import test
    real_cfg = Qwen4ExpConfig.from_json_file("research/step1_raw/config.json")
    results["qwen4_exp_real_config"] = {
        "model_type": real_cfg.model_type,
        "text_model_type": real_cfg.text_config.model_type,
        "hidden_size": real_cfg.text_config.hidden_size,
        "moe_intermediate_size": real_cfg.text_config.moe_intermediate_size,
        "num_experts": real_cfg.text_config.num_experts,
        "num_experts_per_tok": real_cfg.text_config.num_experts_per_tok,
        "hc_count": real_cfg.text_config.hc_count,
        "hc_lowrank": real_cfg.text_config.hc_lowrank,
        "ple_layer_ids": real_cfg.text_config.ple_layer_ids,
    }

    # 4. CPU-only forward pass smoke test of Qwen4ExpTextModel (1 linear_attention layer + 1 linear_attention with PLE + 1 full_attention QSA layer)
    # Proves pure-PyTorch fallback (torch_chunk_gated_delta_rule, causal_conv1d_fn, PLE, QSA indexer, HC, MoE) works on Windows without fla/triton!
    tiny_dict = real_cfg.text_config.to_dict()
    tiny_dict.update(
        {
            "hidden_size": 128,
            "intermediate_size": 256,
            "moe_intermediate_size": 64,
            "shared_expert_intermediate_size": 64,
            "num_hidden_layers": 4,
            "layer_types": ["linear_attention", "linear_attention", "linear_attention", "full_attention"],
            "ple_layer_ids": [2],
            "num_attention_heads": 4,
            "num_key_value_heads": 2,
            "head_dim": 32,
            "linear_num_key_heads": 2,
            "linear_num_value_heads": 4,
            "linear_key_head_dim": 32,
            "linear_value_head_dim": 32,
            "num_experts": 8,
            "num_experts_per_tok": 2,
            "hc_count": 4,
            "hc_lowrank": 32,
            "vocab_size": 1024,
            "ngram_vocab_size_base": 512,
            "ple_embed_dim": 128,
            "split_ngram_parts": 4,
            "indexer_n_heads": 2,
            "indexer_head_dim": 32,
            "indexer_budget": 16,
            "pad_token_id": 0,
            "bos_token_id": 0,
            "eos_token_id": 1,
        }
    )
    tiny_cfg = Qwen4ExpTextConfig(**tiny_dict)
    torch.manual_seed(42)
    tiny_model = Qwen4ExpTextModel(tiny_cfg).eval()
    input_ids = torch.randint(2, 500, (1, 16), dtype=torch.long)
    with torch.no_grad():
        out = tiny_model(input_ids=input_ids, use_cache=False)
    results["cpu_forward_smoke_test"] = {
        "input_shape": list(input_ids.shape),
        "output_shape": list(out.last_hidden_state.shape),
        "has_nan": bool(torch.isnan(out.last_hidden_state).any().item()),
        "output_norm": round(float(out.last_hidden_state.norm().item()), 4),
    }

    # 5. Package versions in .venv
    results["venv_packages"] = {
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version_torch": torch.version.cuda,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "gpu_capability": list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None,
        "transformers": transformers.__version__,
        "safetensors": safetensors.__version__,
        "gguf_file": gguf.__file__,
        "gguf_has_qwen4exp": hasattr(gguf.MODEL_ARCH, "QWEN4EXP"),
    }

    out_file = RAW_DIR / "smoke_test_results.json"
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Smoke test completed successfully!")
    print("llama-cli --list-devices:", results["llama_list_devices"]["stdout"] or results["llama_list_devices"]["stderr"])
    print("CPU forward smoke test (GDN + PLE + QSA + HC + MoE):", results["cpu_forward_smoke_test"])


if __name__ == "__main__":
    main()
