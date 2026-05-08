# Claude Code Launcher - Install Script

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Claude Code Launcher - Install Script" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python 3.7+ not found" -ForegroundColor Red
    Write-Host "Download: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherPath = Join-Path $scriptDir "claude_launcher.py"

if (-not (Test-Path $launcherPath)) {
    Write-Host "[ERROR] claude_launcher.py not found" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Launcher files found" -ForegroundColor Green
Write-Host ""

$pythonwPath = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonwPath) {
    Write-Host "[ERROR] pythonw.exe not found in PATH" -ForegroundColor Red
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Claude Launcher.lnk"
$iconPath = Join-Path $scriptDir "claude_icon.ico"

Write-Host "Creating desktop shortcut..." -ForegroundColor Yellow

try {
    if (Test-Path $shortcutPath) { Remove-Item $shortcutPath -Force }

    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = $pythonwPath
    $Shortcut.Arguments = "`"$launcherPath`""
    $Shortcut.WorkingDirectory = $scriptDir

    if (Test-Path $iconPath) {
        $Shortcut.IconLocation = "$iconPath,0"
    } else {
        $Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,13"
    }

    $Shortcut.Description = "Claude Code Launcher"
    $Shortcut.Save()

    Write-Host "[OK] Desktop shortcut created" -ForegroundColor Green
    Write-Host "Shortcut: $shortcutPath" -ForegroundColor White
} catch {
    Write-Host "[ERROR] Failed to create shortcut: $_" -ForegroundColor Red
    Write-Host "Create manually with target:" -ForegroundColor Yellow
    Write-Host "`"$pythonwPath`" `"$launcherPath`"" -ForegroundColor White
}