#!/usr/bin/env bash
# SmartLLM v2 — 1-Command Offline Multimodal Web / Design / Copywriting Combine
# Strictly local (127.0.0.1 only). Zero external network calls.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${REPO_ROOT}/.venv_linux/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="/usr/bin/python3"
fi

export PYTHONPATH="${REPO_ROOT}/tools/llama.cpp/gguf-py:${REPO_ROOT}:${PYTHONPATH:-}"

CPU_ONLY_MODE=0
SHOW_HELP=0
HAS_UI=0
HAS_BRIEF=0
HAS_REPL=0

for arg in "$@"; do
    case "${arg}" in
        -h|--help)
            SHOW_HELP=1
            CPU_ONLY_MODE=1
            ;;
        --self-test|--dry-run)
            CPU_ONLY_MODE=1
            ;;
        --serve-ui)
            HAS_UI=1
            ;;
        --brief|--brief=*)
            HAS_BRIEF=1
            ;;
        --repl)
            HAS_REPL=1
            ;;
    esac
done

# Pure UI server without an immediate brief or REPL runs on CPU until a brief is triggered
if [[ "${HAS_UI}" -eq 1 && "${HAS_BRIEF}" -eq 0 && "${HAS_REPL}" -eq 0 ]]; then
    CPU_ONLY_MODE=1
fi

if [[ "${SHOW_HELP}" -eq 1 ]]; then
    cat <<'EOF'
================================================================================
SmartLLM v2 — Offline Multimodal Web / Design / Copywriting Combine (EN + RU)
================================================================================
Quick Examples:
  1. Generate a complete RU or EN landing page + Z-Image assets (1 command):
     ./run_combine.sh --brief "Премиальный лендинг для студии промышленного дизайна в Москве" --out eval/combine_out/design_ru
     ./run_combine.sh --brief "High-craft landing page for an offline Rust database engine" --lang en --out eval/combine_out/db_en

  2. CPU-only preview (RAG + deterministic bundle + prompts, 0 GPU / 0 VRAM):
     ./run_combine.sh --dry-run --brief "Инженерный лендинг для платежного API" --out eval/combine_out/preview_ru

  3. Interactive CLI REPL or Local Browser Workbench (127.0.0.1 only):
     ./run_combine.sh --repl
     ./run_combine.sh --serve-ui --ui-port 8090

  4. Run CPU self-test suite (<250 MiB RAM, 0 GPU):
     ./run_combine.sh --self-test
================================================================================
EOF
    exec "${PYTHON_BIN}" "${REPO_ROOT}/scripts/combine/run_offline_combine.py" --help
fi

if [[ "${CPU_ONLY_MODE}" -eq 1 ]]; then
    exec "${PYTHON_BIN}" "${REPO_ROOT}/scripts/combine/run_offline_combine.py" "$@"
else
    # Live GPU execution: wrap in gpu_run.py (flock .system/gpu.lock + sla_watchdog + gpu_exit_check)
    exec "${PYTHON_BIN}" "${REPO_ROOT}/scripts/infra/gpu_run.py" \
        --wp WP-A3 \
        --max-proc-swap-mib 128.0 \
        --check-ple \
        --hypothesis "Sequential offline SmartLLM v2 + Z-Image combine executes under OPUS §0.3a" \
        --expected "exit 0, 0 disk swap, MemAvail >= 3.0 GiB, PLE RSS == 0 kB, <= 95 MiB VRAM exit" \
        --factor "One-command offline combine wrapper" \
        -- "${PYTHON_BIN}" "${REPO_ROOT}/scripts/combine/run_offline_combine.py" "$@"
fi
