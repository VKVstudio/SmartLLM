#!/usr/bin/env bash
# SmartLLM portable Linux engine packager — runs INSIDE the nvidia/cuda devel build container.
# Collects llama-server + sd-cli with all non-glibc-core dependencies into a single
# RPATH-relative bundle that runs on any x86_64 Linux with glibc >= 2.35 and an
# NVIDIA driver >= 525 (CUDA 12 runtime bundled; libcuda.so.1 comes from the host driver).
#
# Layout (extracted into <bundle>/bin/ by setup_bundle.py), identical on Windows:
#   llama/   llama-server + ggml 0.28 libs + CPU-variant/CUDA backends (exe-dir backend search)
#   sd/      sd-cli + ggml 1.0 (leejet fork) libs + backends
#   shared/  CUDA 12 runtime (cudart/cublas/cublasLt) + libstdc++/libgcc_s/libgomp (Linux only)
# Per-engine dirs are REQUIRED: the two ggml versions ship same-named backend libs,
# and ggml's dynamic backend loader searches the EXECUTABLE directory.
set -euo pipefail

VERSION="${VERSION:-0.0.2-beta}"
OUT="/build/engines-linux"
LLAMA_BIN="/build/llama/bin"
SD_BIN="/build/sd/bin"
CUDA_LIB="/usr/local/cuda/targets/x86_64-linux/lib"

rm -rf "${OUT}"
mkdir -p "${OUT}/llama" "${OUT}/sd" "${OUT}/shared"

cp -a "${LLAMA_BIN}/llama-server" "${OUT}/llama/"
find "${LLAMA_BIN}" -maxdepth 1 -name 'lib*.so*' -exec cp -a {} "${OUT}/llama/" \;
cp -a "${SD_BIN}/sd-cli" "${OUT}/sd/"
find "${SD_BIN}" -maxdepth 1 -name 'lib*.so*' -exec cp -a {} "${OUT}/sd/" \;

for lib in libcudart.so.12 libcublas.so.12 libcublasLt.so.12 libnccl.so.2; do
    real="$(readlink -f "${CUDA_LIB}/${lib}")"
    if [[ ! -f "${real}" ]]; then
        real="$(readlink -f "$(ldconfig -p | awk -v l="${lib}" '$1 == l {print $NF; exit}')")"
    fi
    cp -a "${real}" "${OUT}/shared/"
    ln -sf "$(basename "${real}")" "${OUT}/shared/${lib}"
done

for lib in libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do
    real="$(readlink -f "$(gcc -print-file-name=${lib})")"
    cp -a "${real}" "${OUT}/shared/"
    ln -sf "$(basename "${real}")" "${OUT}/shared/${lib}"
done

patchelf --set-rpath '$ORIGIN:$ORIGIN/../shared' "${OUT}/llama/llama-server" "${OUT}/sd/sd-cli"
find "${OUT}/llama" "${OUT}/sd" -type f -name '*.so*' -exec patchelf --set-rpath '$ORIGIN:$ORIGIN/../shared' {} \;
find "${OUT}/shared" -type f -name '*.so*' -exec patchelf --set-rpath '$ORIGIN' {} \;

for tool in llama/llama-server sd/sd-cli; do
    missing="$(ldd "${OUT}/${tool}" | grep 'not found' | grep -v 'libcuda.so.1' || true)"
    if [[ -n "${missing}" ]]; then
        echo "UNRESOLVED DEPS for ${tool}:" >&2
        echo "${missing}" >&2
        exit 1
    fi
done

tar czf "/build/SmartLLM-Engines-v${VERSION}-linux.tar.gz" -C "${OUT}" .
sha256sum "/build/SmartLLM-Engines-v${VERSION}-linux.tar.gz"
du -sh "${OUT}"
echo PACKAGING_OK