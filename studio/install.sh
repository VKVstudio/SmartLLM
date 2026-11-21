#!/usr/bin/env bash
# SmartLLM Studio v0.0.4-beta — Hardened Linux Installer (Opus Spec Q6)
# Verifies Python >= 3.11, creates venv in ~/.local/share/smartllm-studio, installs .desktop & icon. Never downloads models.
set -euo pipefail

DRY_RUN=0
WITH_TRAY=0
for arg in "$@"; do
    case "${arg}" in
        --dry-run|-n) DRY_RUN=1 ;;
        --with-tray) WITH_TRAY=1 ;;
        --help|-h)
            echo "Usage: ./install.sh [--dry-run] [--with-tray]"
            exit 0
            ;;
    esac
done

PYTHON_CMD=""
for candidate in python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1; then
        if "${candidate}" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            PYTHON_CMD="$(command -v "${candidate}")"
            break
        fi
    fi
done

if [[ -z "${PYTHON_CMD}" ]]; then
    echo "ERROR: Python >= 3.11 is required to install SmartLLM Studio." >&2
    exit 1
fi

STUDIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SHARE_DIR="${HOME}/.local/share/smartllm-studio"
VENV_DIR="${APP_SHARE_DIR}/venv"
LAUNCHER_PATH="${STUDIO_DIR}/bin/smartllm-studio"
ICON_PATH="${STUDIO_DIR}/assets/smartllm-logo.svg"
LOCAL_BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"
DESKTOP_FILE="${DESKTOP_DIR}/smartllm-studio.desktop"

read -r -d '' DESKTOP_CONTENT <<EOF || true
[Desktop Entry]
Version=1.0
Type=Application
Name=SmartLLM Studio
GenericName=Offline Multimodal Web & Design Atelier
Comment=SmartLLM Studio v0.0.4-beta — Local Offline Web, Design & Z-Image Atelier (127.0.0.1)
Exec="${LAUNCHER_PATH}"
Icon=${ICON_PATH}
Terminal=false
Categories=Development;WebDevelopment;Graphics;
StartupNotify=true
EOF

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[DRY-RUN] SmartLLM Studio v0.0.4-beta Linux Installer"
    echo "[DRY-RUN] Verified Python >= 3.11: ${PYTHON_CMD}"
    echo "[DRY-RUN] Would create venv at: ${VENV_DIR} (pip: Pillow$( [[ "${WITH_TRAY}" -eq 1 ]] && printf ' + PyQt6' ))"
    echo "[DRY-RUN] Would symlink ${LOCAL_BIN_DIR}/smartllm-studio -> ${LAUNCHER_PATH}"
    echo "[DRY-RUN] Would write ${DESKTOP_FILE}:"
    echo "${DESKTOP_CONTENT}"
    exit 0
fi

mkdir -p "${APP_SHARE_DIR}" "${LOCAL_BIN_DIR}" "${DESKTOP_DIR}"
if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    "${PYTHON_CMD}" -m venv --system-site-packages "${VENV_DIR}"
fi
if ! "${VENV_DIR}/bin/python" -c "import PIL" 2>/dev/null; then
    "${VENV_DIR}/bin/pip" install --upgrade pip >/dev/null
    "${VENV_DIR}/bin/pip" install Pillow
fi
if [[ "${WITH_TRAY}" -eq 1 ]]; then
    "${VENV_DIR}/bin/pip" install -e "${STUDIO_DIR}[tray]"
fi
chmod +x "${LAUNCHER_PATH}"
ln -sf "${LAUNCHER_PATH}" "${LOCAL_BIN_DIR}/smartllm-studio"
printf "%s\n" "${DESKTOP_CONTENT}" > "${DESKTOP_FILE}"
chmod 644 "${DESKTOP_FILE}"
echo "Installed SmartLLM Studio v0.0.4-beta (${VENV_DIR}, ${DESKTOP_FILE}). No model weights downloaded."
