# SmartLLM Data & Schemas (`docs/DATA.md`)

## 1. Donor Checkpoint Layout (`Qwen/Qwen3.8-Flash-Next`)
Verified against `model.safetensors.index.json` (`1,658` tensors across `131` shards, exact total `359,999,963,128` B = `360.00 GB` / `335.28 GiB`, 0-byte discrepancy):

| Component | Tensor Names & Shapes (`BF16` unless noted) | Tensors | Exact Size | Shards |
|---|---|---:|---:|---|
| Root | `embed_tokens [248320,2560]`, `lm_head [248320,2560]`, `hc_mixer.{hc_norm [10240], down [320,10240], up [10240,320]}` | 5 | `2.5559 GB` | `00001, 00130, 00131` |
| Visual (`mmproj`) | `model.visual.*` (`patch_embed`, `pos_embed [2304,1152]`, `blocks.0..26`, `merger`) | 333 | `0.8979 GB` | `00001` |
| Routed Experts (×48) | `layers.{0..47}.mlp.experts.gate_up_proj [512,1280,2560]` (`3.3554 GB`) + `down_proj [512,2560,640]` (`1.6777 GB`) | 96 | `241.5919 GB` | `00001..00130` (3 shards/layer) |
| Dense per Layer (×48) | Router `[512,2560]`, `shared_expert` (`3×[640,2560]`+gate), `2×HC` (`26.42 MB`), GDN (`115.92 MB`, ×36) / QSA (`102.89 MB`, ×12) | 1,056 | `7.2738 GB` | `00001..00130` |
| PLE (`layers.1.ple.*`) | `shard_{0..127}.weight [2500012,160]` (`102.40 GB`), `key_proj [10240,2560]`, `value_proj [2560,2560]`, `conv1d`, `I64` offsets | 137 | `102.4662 GB` | `00005..00037` |
| MTP (`mtp.*`) | `fc_embedding`, `fc_hidden`, `hc_mixer`, `mtp.layers.0.*` (QSA + 512 experts) | 31 | `5.2143 GB` | `00037..00124` (`00060, 00062`) |

## 2. Pruned (`205/512`) & Quantized Size Budgets
- **BF16 Pruned (205 experts/layer = `2.0152 GB/layer`, `96.7311 GB` across 48 layers):**
  - Text Core (Root + 48 layers, no PLE/Visual/MTP): **`106.49 GB` (`99.17 GiB`)**.
  - Core + Visual + MTP(205), no PLE: **`109.58 GB` (`102.05 GiB`)**.
- **Mainline `llama-quantize` GGUF (with `down_proj` `ne[0]=640` → `IQ4_NL` `4.50 bpw` fallback & F16 routers):**
  - `IQ3_XXS`: Text Core = **`24.79 GB` (`23.09 GiB`)**; Full on disk (+ PLE `Q4_0` `28.87 GB` + `mmproj` `0.90 GB`) = **`54.55 GB` (`50.81 GiB`)**.
  - `IQ3_S`: Text Core = **`26.32 GB` (`24.51 GiB`)**; Full on disk (+ PLE `28.87 GB` + `mmproj` `0.90 GB`) = **`56.08 GB` (`52.23 GiB`)**.

## 3. Evaluation Suite Datasets & JSON Schemas (`eval/suite/`)
- `eval/suite/tasks.json`: 12 offline tasks (`t1, t4, t5, t6, t9, t11` EN; `t3, t7, t8, t10` RU; `t2, t12` Vision-to-Code with `eval/suite/ref/t2.png` & `t12.png`). Covers 6 OKLCH design canons, WebGL/GLSL (`t6`), 3D/Canvas (`t11`), CSS Subgrid/`@container` (`t5, t8`), 7-file agentic build with `zimage_prompts.json` (`t9`), and strict TypeScript `dag.ts` (`t4`).
- `eval/suite/runs/<model_slug>/<task_id>/`: `raw.md`, `reasoning.md`, `meta.json` (`elapsed_sec`, `tok_per_sec`, `usage`, `extracted_files`), `orig/` (pre-CSP backups), extracted artifacts (`index.html`, `llms.txt`, `robots.txt`, `_headers`, `dag.ts`, etc.), `lighthouse.json`, and 4 Playwright PNGs (`shot-desktop.png`, `shot-desktop-full.png`, `shot-mobile.png`, `shot-mobile-full.png`).
- `eval/suite/results/static_audit_all.json` & `runs/<slug>/runtime_audit.json`: deterministic outputs of `audit_suite.py` and `browser_and_lh_suite.mjs`.
- `eval/suite/results/judge_1.json`, `judge_2.json`, `judges_aggregated.json`: blind scores (`0–10`) on 4 rubric axes (`canon`, `design`, `copy`, `ru` + `overall`) aggregated by `aggregate_judges.py` (`discrepancy_threshold = 2.0`).

## 4. Calibration Dataset Spec (`data/calib/`)
- Note on upstream datasets: `ilabai/3dcodeverse` is an empty repository (`1` file `README.md`, `0` downloads) and `Tesslate/UIGEN-T1.5` returns `401`; use `TozAI/mihenk-3d`, `smirki/UIGEN-T1.1-TAILWIND`, `Tesslate/UIGEN-T2`, `NousResearch/hermes-function-calling-v1` / `Team-ACE/ToolACE` (10% tool-calling), and `THUDM/LongBench-v2` (5% long-context).
- Target: `data/calib/PremiumWebStudio-Calib.jsonl` + `stats.md` (`0.5–1.0M` Qwen3.8 tokens; `70% EN / 30% RU`; Pillars 1–4 + `10%` multi-file tool-calling agentic traces + `5%` long-context + real multimodal image+text pairs; every source dataset verified for existence and commercial/open license).
