# Third-Party Notices & Upstream Component Licenses

**SmartLLM Studio** ships with zero external Python runtime dependencies (`dependencies = []`) and zero vendored third-party JavaScript frameworks. It interacts with external local tools and bundles subsetted open-font-licensed (`.woff2`) typefaces as documented below.

---

## 1. Bundled Subsetted Typefaces (`SIL Open Font License 1.1`)
Located in `smartllm_studio/static/fonts/` (subsetted to Latin + Cyrillic via `pyftsubset` + `woff2_compress`, total `< 160 KB`):
- **Display Serif Role (`CormorantGaramond-500.woff2`, `CormorantGaramond-600.woff2`):** Subsetted from locally installed **Noto Serif** (`/usr/share/fonts/noto/NotoSerif-{Medium,Bold}.ttf`). Copyright Google LLC. Licensed under the **SIL Open Font License, Version 1.1 (`OFL-1.1`)**.
- **UI Sans Role (`Onest-400.woff2`, `Onest-600.woff2`):** Subsetted from locally installed **Fira Sans** (`/usr/share/fonts/TTF/FiraSans-{Regular,SemiBold}.ttf`). Copyright The Mozilla Foundation and Telefonica S.A. Licensed under the **SIL Open Font License, Version 1.1 (`OFL-1.1`)**.
- **Monospace Role (`JetBrainsMono-400.woff2`, `JetBrainsMono-600.woff2`):** Subsetted from locally installed **Adwaita Mono** (`/usr/share/fonts/Adwaita/AdwaitaMono-{Regular,Bold}.ttf`). Copyright GNOME Foundation / Red Hat, Inc. Licensed under the **SIL Open Font License, Version 1.1 (`OFL-1.1`)**.

Under the SIL Open Font License 1.1, these font subsets may be bundled, embedded, and redistributed freely alongside software provided they are not sold by themselves.

---

## 2. External Local Inference Engines (User-Built / User-Downloaded, Never Bundled)
- **`llama.cpp` (`ggml-org/llama.cpp`):** Licensed under the **MIT License**. Copyright (c) 2023-2026 Georgi Gerganov and contributors. Invoked over local `127.0.0.1` loopback HTTP.
- **`stable-diffusion.cpp` (`leejet/stable-diffusion.cpp`):** Licensed under the **MIT License**. Copyright (c) 2023-2026 leejet and contributors. Invoked as a local child process (`sd-cli`).

---

## 3. Separate Model Checkpoints (Never Bundled in Studio Repo or Installer)
- **`SmartLLM v2` GGUF (`Qwen/Qwen3.8-Flash-Next` derivative):** Distributed separately under the **Qwen Community License Agreement 1.0 (`qwen-community-1.0`)**. Built with Qwen.
- **`Z-Image` Diffusion / Text-Encoder / VAE Checkpoints:** User-supplied local `.safetensors` files. SmartLLM Studio never bundles or redistributes third-party diffusion checkpoints.
