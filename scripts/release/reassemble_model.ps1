<#
.SYNOPSIS
Verifies GitHub Release GGUF parts and streams them into SmartLLM-v2-K320-V1.gguf on Windows 11.
.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\reassemble_model.ps1
powershell -ExecutionPolicy Bypass -File .\reassemble_model.ps1 -Cleanup
#>
param(
    [switch]$SkipPartCheck,
    [switch]$Cleanup
)

$ErrorActionPreference = "Stop"
$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Manifest = Join-Path $Dir "MODEL_SHA256SUMS.txt"
$ModelName = "SmartLLM-v2-K320-V1.gguf"
$TmpOut = Join-Path $Dir ($ModelName + ".assembling.tmp")
$FinalOut = Join-Path $Dir $ModelName

if (-not (Test-Path $Manifest)) {
    throw "Manifest not found: $Manifest"
}

$ExpectedHashes = @{}
$PartNames = New-Object System.Collections.Generic.List[string]
foreach ($RawLine in (Get-Content -Path $Manifest -Encoding UTF8)) {
    $Line = $RawLine.Trim()
    if (-not $Line -or $Line.StartsWith("#")) { continue }
    $Match = [regex]::Match($Line, '^([0-9a-fA-F]{64})\s+\*?(.+)$')
    if (-not $Match.Success) { throw "Malformed SHA256SUMS line: $Line" }
    $Hash = $Match.Groups[1].Value.ToLowerInvariant()
    $Name = $Match.Groups[2].Value.Trim()
    $ExpectedHashes[$Name] = $Hash
    if ($Name.Contains(".part")) {
        $PartNames.Add($Name)
    }
}

$PartNames.Sort([System.StringComparer]::Ordinal)
if ($PartNames.Count -eq 0) {
    throw "No part entries found in $Manifest"
}

if (-not $SkipPartCheck) {
    Write-Host "[1/3] Verifying $($PartNames.Count) parts..."
    foreach ($Name in $PartNames) {
        $PartPath = Join-Path $Dir $Name
        if (-not (Test-Path $PartPath)) { throw "Missing part file: $PartPath" }
        $Actual = (Get-FileHash -Path $PartPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($Actual -ne $ExpectedHashes[$Name]) {
            throw "Checksum mismatch on $Name (expected $($ExpectedHashes[$Name]), got $Actual)"
        }
    }
}

Write-Host "[2/3] Streaming $($PartNames.Count) parts into $FinalOut..."
if (Test-Path $TmpOut) { Remove-Item -Path $TmpOut -Force }
$Buffer = New-Object byte[] (16 * 1024 * 1024)
try {
    $OutStream = [System.IO.File]::Open($TmpOut, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    try {
        foreach ($Name in $PartNames) {
            $PartPath = Join-Path $Dir $Name
            if (-not (Test-Path $PartPath)) { throw "Missing part file: $PartPath" }
            $InStream = [System.IO.File]::OpenRead($PartPath)
            try {
                while (($Read = $InStream.Read($Buffer, 0, $Buffer.Length)) -gt 0) {
                    $OutStream.Write($Buffer, 0, $Read)
                }
            } finally {
                $InStream.Dispose()
            }
        }
        $OutStream.Flush()
    } finally {
        $OutStream.Dispose()
    }

    Write-Host "[3/3] Verifying assembled $ModelName SHA-256..."
    $FinalActual = (Get-FileHash -Path $TmpOut -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ExpectedHashes.ContainsKey($ModelName) -and $FinalActual -ne $ExpectedHashes[$ModelName]) {
        throw "Final SHA-256 mismatch for $ModelName (expected $($ExpectedHashes[$ModelName]), got $FinalActual)"
    }
    if (Test-Path $FinalOut) { Remove-Item -Path $FinalOut -Force }
    Move-Item -Path $TmpOut -Destination $FinalOut
} catch {
    if (Test-Path $TmpOut) { Remove-Item -Path $TmpOut -Force }
    throw
}

if ($Cleanup) {
    Write-Host "Cleaning up verified part files..."
    foreach ($Name in $PartNames) {
        $PartPath = Join-Path $Dir $Name
        if (Test-Path $PartPath) { Remove-Item -Path $PartPath -Force }
    }
}

Write-Host "PASS: $FinalOut ready."
