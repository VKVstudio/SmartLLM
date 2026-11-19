<#
.SYNOPSIS
    SmartLLM Studio v0.0.2-beta — Windows 11 Uninstaller (Opus Spec Q6)
#>
param(
    [switch]$DryRun = $false
)

$LocalAppDir = Join-Path $env:LOCALAPPDATA "SmartLLM Studio"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "SmartLLM Studio.lnk"
$StartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "SmartLLM Studio"

if ($DryRun) {
    Write-Output "[DRY-RUN] Would remove $LocalAppDir, $DesktopShortcut, and $StartMenuDir"
    exit 0
}

if (Test-Path $LocalAppDir) { Remove-Item $LocalAppDir -Recurse -Force }
if (Test-Path $DesktopShortcut) { Remove-Item $DesktopShortcut -Force }
if (Test-Path $StartMenuDir) { Remove-Item $StartMenuDir -Recurse -Force }
Write-Output "Removed SmartLLM Studio Windows 11 installation and shortcuts."
