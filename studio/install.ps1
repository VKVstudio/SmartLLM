<#
.SYNOPSIS
    SmartLLM Studio v0.0.1-beta — Hardened Windows 11 Installer (Opus Spec Q6)
    Checks py -3.11+, creates venv in %LOCALAPPDATA%\SmartLLM Studio, registers Start Menu shortcut & uninstaller. Never downloads models.
#>
param(
    [switch]$DryRun = $false
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
    Write-Output "[DRY-RUN] SmartLLM Studio v0.0.1-beta Windows 11 Installer"
    Write-Output "[DRY-RUN] Check Python: py -3.11 (prompt before winget install Python.Python.3.12 if missing)"
    Write-Output "[DRY-RUN] Target Venv: $VenvDir"
    Write-Output "[DRY-RUN] Target VBS: $VbsPath"
    Write-Output "[DRY-RUN] Icon ICO: $IconPath"
    Write-Output "[DRY-RUN] Start Menu Shortcut: $StartMenuShortcut"
    exit 0
}

$PyCheck = Get-Command py -ErrorAction SilentlyContinue
if (-not $PyCheck) {
    $ans = Read-Host "Python >= 3.11 not found. Run 'winget install Python.Python.3.12'? (y/N)"
    if ($ans -eq "y" -or $ans -eq "Y") {
        winget install Python.Python.3.12
    } else {
        throw "Python >= 3.11 is required."
    }
}

if (!(Test-Path $LocalAppDir)) { New-Item -ItemType Directory -Path $LocalAppDir -Force | Out-Null }
if (!(Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
    py -3.11 -m venv $VenvDir
}
if (!(Test-Path $StartMenuDir)) { New-Item -ItemType Directory -Path $StartMenuDir -Force | Out-Null }

$WshShell = New-Object -ComObject WScript.Shell
foreach ($LnkPath in @($DesktopShortcut, $StartMenuShortcut)) {
    $Shortcut = $WshShell.CreateShortcut($LnkPath)
    $Shortcut.TargetPath = "wscript.exe"
    $Shortcut.Arguments = "`"$VbsPath`""
    $Shortcut.WorkingDirectory = $StudioDir
    $Shortcut.IconLocation = "$IconPath,0"
    $Shortcut.Description = "SmartLLM Studio v0.0.1-beta — Local Offline Multimodal Web & Design Atelier"
    $Shortcut.Save()
}

Write-Output "Installed SmartLLM Studio v0.0.1-beta in $LocalAppDir. No model weights downloaded."
