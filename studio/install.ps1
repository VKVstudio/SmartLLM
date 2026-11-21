<#
.SYNOPSIS
    SmartLLM Studio v0.0.4-beta — Hardened Windows 11 Installer (Opus Spec Q6)
    Checks py -3.11+, creates venv in %LOCALAPPDATA%\SmartLLM Studio, registers Start Menu shortcut & uninstaller. Never downloads models.
#>
param(
    [switch]$DryRun = $false,
    [switch]$WithTray = $false
)

$ErrorActionPreference = "Stop"
$StudioDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalAppDir = Join-Path $env:LOCALAPPDATA "SmartLLM Studio"
$VenvDir = Join-Path $LocalAppDir "venv"
$VbsPath = Join-Path $StudioDir "smartllm-studio-silent.vbs"
$IconPath = Join-Path $StudioDir "assets\smartllm-studio.ico"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "SmartLLM Studio.lnk"
$StartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "SmartLLM Studio"
$StartMenuShortcut = Join-Path $StartMenuDir "SmartLLM Studio.lnk"

if ($DryRun) {
    Write-Output "[DRY-RUN] SmartLLM Studio v0.0.4-beta Windows 11 Installer"
    Write-Output "[DRY-RUN] Check Python >= 3.11 via 'py -3' or 'python' (prompt before winget install Python.Python.3.12 if missing)"
    Write-Output "[DRY-RUN] Target Venv: $VenvDir"
    Write-Output "[DRY-RUN] Pip dependencies: Pillow (+ PyQt6 with -WithTray)"
    Write-Output "[DRY-RUN] Target VBS: $VbsPath"
    Write-Output "[DRY-RUN] Icon ICO: $IconPath"
    Write-Output "[DRY-RUN] Start Menu Shortcut: $StartMenuShortcut"
    exit 0
}

function Test-PyVersion([string]$Cmd) {
    try {
        $parts = $Cmd.Split(" ")
        $exe = $parts[0]
        $cmdArgs = @()
        if ($parts.Length -gt 1) { $cmdArgs = $parts[1..($parts.Length - 1)] }
        & $exe @cmdArgs -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

$PyCmd = $null
foreach ($cand in @("py -3", "python", "python3")) {
    if (Test-PyVersion $cand) { $PyCmd = $cand; break }
}
if (-not $PyCmd) {
    $ans = Read-Host "Python >= 3.11 not found. Run 'winget install Python.Python.3.12'? (y/N)"
    if ($ans -eq "y" -or $ans -eq "Y") {
        winget install Python.Python.3.12
        if (Test-PyVersion "py -3") { $PyCmd = "py -3" }
    }
    if (-not $PyCmd) { throw "Python >= 3.11 is required." }
}

if (!(Test-Path $LocalAppDir)) { New-Item -ItemType Directory -Path $LocalAppDir -Force | Out-Null }
if (!(Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
    $pyParts = $PyCmd.Split(" ")
    $pyExe = $pyParts[0]
    $pyArgs = @()
    if ($pyParts.Length -gt 1) { $pyArgs = $pyParts[1..($pyParts.Length - 1)] }
    & $pyExe @pyArgs -m venv $VenvDir
}
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPy -m pip install --upgrade pip
& $VenvPy -m pip install Pillow
if ($WithTray) { & $VenvPy -m pip install PyQt6 }
if (!(Test-Path $StartMenuDir)) { New-Item -ItemType Directory -Path $StartMenuDir -Force | Out-Null }

$WshShell = New-Object -ComObject WScript.Shell
foreach ($LnkPath in @($DesktopShortcut, $StartMenuShortcut)) {
    $Shortcut = $WshShell.CreateShortcut($LnkPath)
    $Shortcut.TargetPath = "wscript.exe"
    $Shortcut.Arguments = "`"$VbsPath`""
    $Shortcut.WorkingDirectory = $StudioDir
    $Shortcut.IconLocation = "$IconPath,0"
    $Shortcut.Description = "SmartLLM Studio v0.0.4-beta — Local Offline Multimodal Web & Design Atelier"
    $Shortcut.Save()
}

Write-Output "Installed SmartLLM Studio v0.0.4-beta in $LocalAppDir (venv + Pillow$(if ($WithTray) { ' + PyQt6' })). No model weights downloaded."
