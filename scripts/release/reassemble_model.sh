#!/usr/bin/env bash
# Verify part checksums, reassemble SmartLLM-v2-K320-V1.gguf, and verify final SHA-256.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP=0
SKIP_PART_CHECK=0

for arg in "$@"; do
  case "${arg}" in
    --cleanup) CLEANUP=1 ;;
    --skip-part-check) SKIP_PART_CHECK=1 ;;
    *)
      echo "Usage: $0 [--skip-part-check] [--cleanup]" >&2
      exit 2
      ;;
  esac
done

MANIFEST="${DIR}/MODEL_SHA256SUMS.txt"
MODEL_NAME="SmartLLM-v2-K320-V1.gguf"
TMP_OUT="${DIR}/${MODEL_NAME}.assembling.tmp"
FINAL_OUT="${DIR}/${MODEL_NAME}"

if [[ ! -f "${MANIFEST}" ]]; then
  echo "ERROR: Manifest not found: ${MANIFEST}" >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  SHA_CMD=(sha256sum)
elif command -v shasum >/dev/null 2>&1; then
  SHA_CMD=(shasum -a 256)
else
  echo "ERROR: Neither sha256sum nor shasum found." >&2
  exit 1
fi

mapfile -t PARTS < <(find "${DIR}" -maxdepth 1 -type f -name "${MODEL_NAME}.part*" | LC_ALL=C sort)
if [[ "${#PARTS[@]}" -eq 0 ]]; then
  echo "ERROR: No ${MODEL_NAME}.part* files found in ${DIR}" >&2
  exit 1
fi

if [[ "${SKIP_PART_CHECK}" -eq 0 ]]; then
  echo "[1/3] Verifying ${#PARTS[@]} parts against ${MANIFEST}..."
  (
    cd "${DIR}"
    tr -d '\r' < "${MANIFEST}" | grep "\.part" | "${SHA_CMD[@]}" -c -
  )
fi

echo "[2/3] Streaming ${#PARTS[@]} parts into ${FINAL_OUT}..."
rm -f "${TMP_OUT}"
cat "${PARTS[@]}" > "${TMP_OUT}"
mv -f "${TMP_OUT}" "${FINAL_OUT}"

echo "[3/3] Verifying assembled ${MODEL_NAME} SHA-256..."
(
  cd "${DIR}"
  awk -v m="${MODEL_NAME}" '{gsub(/\r$/,""); if ($2 == m) print $1 "  " $2}' "${MANIFEST}" | "${SHA_CMD[@]}" -c -
)

if [[ "${CLEANUP}" -eq 1 ]]; then
  echo "Cleaning up verified part files..."
  rm -f "${PARTS[@]}"
fi

echo "PASS: ${FINAL_OUT} ready."
