#!/usr/bin/env bash
# SmartLLM Studio v0.0.3-beta — Linux Uninstaller (Opus Spec Q6)
set -euo pipefail

DRY_RUN=0
for arg in "$@"; do
    case "${arg}" in
        --dry-run|-n) DRY_RUN=1 ;;
    esac
done

APP_SHARE_DIR="${HOME}/.local/share/smartllm-studio"
LOCAL_BIN="${HOME}/.local/bin/smartllm-studio"
DESKTOP_FILE="${HOME}/.local/share/applications/smartllm-studio.desktop"

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[DRY-RUN] Would remove ${APP_SHARE_DIR}, ${LOCAL_BIN}, and ${DESKTOP_FILE}"
    exit 0
fi

rm -rf "${APP_SHARE_DIR}"
rm -f "${LOCAL_BIN}" "${DESKTOP_FILE}"
echo "Uninstalled SmartLLM Studio (${APP_SHARE_DIR}, ${LOCAL_BIN}, ${DESKTOP_FILE})."
