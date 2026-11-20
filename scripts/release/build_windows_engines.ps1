<#
.SYNOPSIS
    SmartLLM v0.0.3-beta — Windows 11 engine builder (llama-server.exe + sd-cli.exe, CUDA 12).
    Run from "x64 Native Tools Command Prompt for VS 2022" (or Developer PowerShell) so cl.exe is on PATH.
    Prerequisites: VS 2022 Build Tools (C++), CUDA Toolkit 12.x, CMake >= 3.22, Ninja, Git.
    Output: dist\engines-windows\llama\ and ...\sd\ (exe + all DLLs per engine; the two ggml
    versions ship same-named DLLs, so per-engine folders are REQUIRED), plus a release zip.
#>
param(
    [string]$RepoRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [string]$CudaArchs = "75;80;86;89;90;120",
    [int]$Jobs = 12
)
$ErrorActionPreference = "Stop"

foreach ($tool in @("cmake", "ninja", "nvcc", "cl", "git")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "$tool not found on PATH. Use the VS 2022 x64 Native Tools prompt with CUDA 12 installed."
    }
}

$LlamaSrc = Join-Path $RepoRoot "tools\llama.cpp"
$SdSrc    = Join-Path $RepoRoot "tools\stable-diffusion.cpp"
$BuildDir = Join-Path $RepoRoot "tools"
$OutRoot  = Join-Path $RepoRoot "dist\engines-windows"

if (-not (Test-Path (Join-Path $SdSrc "ggml\CMakeLists.txt"))) {
    git -C $SdSrc submodule update --init ggml
}

Write-Output "=== configuring llama.cpp (CUDA $CudaArchs) ==="
cmake -S $LlamaSrc -B (Join-Path $BuildDir "llama.cpp\build_win") -G Ninja `
    -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON "-DCMAKE_CUDA_ARCHITECTURES=$CudaArchs" `
    -DGGML_NATIVE=OFF -DGGML_BACKEND_DL=ON -DGGML_CPU_ALL_VARIANTS=ON `
    -DBUILD_SHARED_LIBS=ON -DLLAMA_OPENSSL=OFF
cmake --build (Join-Path $BuildDir "llama.cpp\build_win") --target llama-server -j $Jobs

Write-Output "=== configuring stable-diffusion.cpp ==="
cmake -S $SdSrc -B (Join-Path $BuildDir "stable-diffusion.cpp\build_win") -G Ninja `
    -DCMAKE_BUILD_TYPE=Release -DSD_CUDA=ON "-DCMAKE_CUDA_ARCHITECTURES=$CudaArchs" `
    -DGGML_NATIVE=OFF -DGGML_BACKEND_DL=ON -DGGML_CPU_ALL_VARIANTS=ON `
    -DSD_BUILD_SHARED_LIBS=ON -DSD_BUILD_SHARED_GGML_LIB=ON -DBUILD_SHARED_LIBS=ON `
    -DSD_CUDA_CUTLASS_PATH=""
cmake --build (Join-Path $BuildDir "stable-diffusion.cpp\build_win") --target sd-cli -j $Jobs

Write-Output "=== packaging ==="
if (Test-Path $OutRoot) { Remove-Item -Recurse -Force $OutRoot }
New-Item -ItemType Directory -Path "$OutRoot\llama", "$OutRoot\sd" | Out-Null
$LlamaBin = Join-Path $BuildDir "llama.cpp\build_win\bin"
$SdBin = Join-Path $BuildDir "stable-diffusion.cpp\build_win\bin"
Copy-Item "$LlamaBin\llama-server.exe" "$OutRoot\llama\" -Force
Copy-Item "$LlamaBin\*.dll" "$OutRoot\llama\" -Force
Copy-Item "$SdBin\sd-cli.exe" "$OutRoot\sd\" -Force
Copy-Item "$SdBin\*.dll" "$OutRoot\sd\" -Force

$CudaBin = Join-Path $env:CUDA_PATH "bin"
foreach ($dll in @("cudart64_12.dll", "cublas64_12.dll", "cublasLt64_12.dll")) {
    $src = Join-Path $CudaBin $dll
    if (Test-Path $src) {
        Copy-Item $src "$OutRoot\llama\" -Force
        Copy-Item $src "$OutRoot\sd\" -Force
    }
}

$Zip = Join-Path $RepoRoot "dist\SmartLLM-Engines-v0.0.3-beta-windows11.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }
# Compress-Archive (PS 5.1) writes backslash entry names (non-standard ZIP);
# use .NET ZipFile with explicit forward-slash entry names instead.
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open($Zip, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($folder in @("llama", "sd")) {
        Get-ChildItem (Join-Path $OutRoot $folder) -File | ForEach-Object {
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive, $_.FullName, "$folder/$($_.Name)",
                [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
        }
    }
} finally {
    $archive.Dispose()
}
Get-FileHash $Zip -Algorithm SHA256 | Format-List
Write-Output "WINDOWS_ENGINES_OK -> $Zip"