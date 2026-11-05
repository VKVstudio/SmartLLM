# SmartLLM Architecture (`docs/ARCHITECTURE.md`)

## 1. Donor Model (`Qwen/Qwen3.8-Flash-Next`, `qwen4_exp`)
Verified directly against `model.safetensors.index.json`, the 131 `.safetensors` headers, `transformers` `modeling_qwen4_exp.py`, and mainline `llama.cpp` (`research/step5_6_layer_shard_schedule.json`):
- **Core dims:** `num_hidden_layers = 48` (`36` GDN `linear_attention` + `12` QSA `full_attention`, interval `4`), `hidden_size = 2560`, `vocab_size = 248320`.
- **MoE & Shared Expert:** `num_experts = 512`, `num_experts_per_tok = 10`, `moe_intermediate_size = 640`, `shared_expert_intermediate_size = 640`.
- **Hyper-Connections (HC):** `hc_count = 4`, `hc_lowrank = 320`, wide residual stream `4 × 2560 = 10240` (`attn_hyper_connection`, `mlp_hyper_connection`, root `hyper_connection_mixer`; no standalone `model.norm`).
- **Per-Layer Embedding (PLE):** `ple_layer_ids = [2]` in `config.json` is **1-based** → maps to **0-based `model.language_model.layers.1.ple.*`** (`137` tensors, `102.47 GB` in shards `00005..00037`, `128` shards of `[2500012, 160]`).
- **Vision & MTP:** `model.visual.*` (`333` tensors, `0.898 GB` in shard `00001`); `mtp.*` (`31` tensors, `5.214 GB` across shards `00037..00124`, expert tensors in `00060` and `00062`).

## 2. Streaming REAP Surgery Pipeline (Steps 5–6)
- **Native Windows 11 Execution:** `transformers==5.20.2` has pure-PyTorch fallbacks for all 4 GDN kernels (`modeling_qwen4_exp.py:202-454`) and QSA (`_supports_flash_attn = False`); WSL2/Triton not needed.
- **204.8 GB RAM Trap (`modeling_qwen4_exp.py:1104`):** `Qwen4ExpTextNGramEmbedding.__init__` allocates `nn.Embedding(320001536, 160)` (`204.8 GB` FP32) on CPU. Always instantiate `layer_idx=1` inside `with torch.device("meta"):` and replace `ngram_embedding` with a streaming/cached lookup (`shard_idx = id // 2500012`, `row_idx = id % 2500012`).
- **Lexicographical Shard Graph:** `model.safetensors.index.json` orders layers lexicographically (`layers.0, 1, 10..19, 2...`). Each regular layer spans **3 adjacent shards** (`gate_up_proj` `3.36 GB` occupies a dedicated shard). Evacuate `mtp.*`/root/visual tensors first and delete raw shards strictly when `refcount == 0`.
- **REAP Pruning (`512 → 205` experts/layer):** Score saliency over top-10 routed experts per token, slice `gate_up_proj [205, 1280, 2560]`, `down_proj [205, 2560, 640]`, `mlp.gate.weight [205, 2560]`, and renormalize router weights.
- **MTP Constraint (`src/models/qwen4exp.cpp:275-292`):** Mainline `llama.cpp` loads `blk.0..47` and embedded `blk.48` (MTP) with the same `hparams.n_expert`. Either prune `mtp.layers.0` to `205` experts as well or pass `--no-mtp`.

## 3. Mainline `llama.cpp` GGUF & Quantization (Step 7)
- **Converter:** `tools/llama.cpp/convert_hf_to_gguf.py` (`conversion/qwen4exp.py`) streams PLE via `LazyChunkedTensor` into `Q4_0`/`IQ4_NL` (`28.87 GB`) without creating a 212 GB BF16 GGUF intermediate.
- **Automatic `down_proj` Fallback (`src/llama-quant.cpp:409-423`):** `ffn_down_exps` has `ne[0] = 640` (`640 % 256 != 0`), so `llama-quantize` automatically falls back from 256-superblock `IQ3_XXS`/`IQ3_S` to 32-block **`IQ4_NL` (`4.50 bpw`)**, while keeping routers in F16 (`+33.06 MB`). Pass `--quantize-output-tensor`.
- **Mandatory `--mmap`:** Total disk GGUF with PLE (`28.87 GB`) + `mmproj` (`0.90 GB`) is **`54.55 GB` (`IQ3_XXS`)** / **`56.08 GB` (`IQ3_S`)**, exceeding 32 GB RAM + 12 GB VRAM. Always run `llama-server`/`llama-cli` with `--mmap` (never `--no-mmap`).

## 4. Offline Evaluation & Combine Architecture (Steps 3, 8, 9)
- **CSP Postprocessor (`eval/suite/audit_suite.py`):** Models cannot compute SHA-256 hashes. `apply_csp_postprocessor` backs up raw files to `orig/`, strips empty `data:text/css,` links, hashes all inline `<style>`, `<script>`, and `style="..."` (`'unsafe-hashes'`), and patches `<meta>` and `_headers`.
- **Runtime & Judges:** `browser_and_lh_suite.mjs` runs headless Chromium (`1440×900` & `375×812`) + bundled Lighthouse (`file://` snapshot or `--http-nav`); `test_dag_runner.mjs` runs `tsc --strict` + 12 worker-isolated DAG tests (`3000ms` timeout); `aggregate_judges.py` aggregates 2 blind judges (`>2.0` point diff flagged).
