# SmartLLM Studio `v0.0.7-beta`

**English** | [Русский](README.ru.md)

Local, offline multi-page website builder running on your own NVIDIA GPU (12 GB VRAM, 32 GB RAM). Studio runs on `127.0.0.1:8090` only.

> **Public beta for testing.** Generated images are sometimes flawed (anatomy, mismatched subjects). Please report bugs and feedback in [GitHub Issues](https://github.com/VKVstudio/SmartLLM/issues).

The full documentation (live demos, how it works, requirements, known limitations, roadmap) is in the [main README](https://github.com/VKVstudio/SmartLLM#readme).

## Run

**Windows 11:** `powershell -ExecutionPolicy Bypass -File .\install.ps1`, then `.\smartllm-studio.bat`

**Linux:** `./install.sh`, then `./bin/smartllm-studio`

Open http://127.0.0.1:8090. The installers set up a Python venv with Pillow and do not download model weights. If models or engines are missing, Studio offers a one-click download (it runs [`setup_bundle.py`](https://github.com/VKVstudio/SmartLLM/blob/main/scripts/release/setup_bundle.py)), or you can set the paths in **Settings**.

## License

[FSL-1.1-ALv2](LICENSE.md), which becomes Apache-2.0 after 2 years. You own your outputs: [OUTPUTS.md](OUTPUTS.md). See also [TRADEMARKS.md](TRADEMARKS.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
