@echo off
echo ====================================
echo Claude Code Launcher - Install
echo ====================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found. Please install Python 3.7+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python installed
echo.

REM Get script directory
set SCRIPT_DIR=%~dp0
set LAUNCHER_PATH=%SCRIPT_DIR%claude_launcher.py
set RUN_BAT_PATH=%SCRIPT_DIR%run.bat

REM Check launcher file
if not exist "%LAUNCHER_PATH%" (
    echo [Error] claude_launcher.py not found
    pause
    exit /b 1
)

if not exist "%RUN_BAT_PATH%" (
    echo [Error] run.bat not found
    pause
    exit /b 1
)

echo [OK] Launcher file found
echo.

REM Create desktop shortcut
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT=%DESKTOP%\Claude Launcher.lnk

echo Creating desktop shortcut...

set ICON_PATH=%SCRIPT_DIR%claude_icon.ico

if exist "%ICON_PATH%" (
    powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; if (Test-Path '%SHORTCUT%') { Remove-Item '%SHORTCUT%' -Force }; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%RUN_BAT_PATH%'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.IconLocation = '%ICON_PATH%,0'; $Shortcut.Description = 'Claude Code Launcher'; $Shortcut.Save()"
) else (
    powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; if (Test-Path '%SHORTCUT%') { Remove-Item '%SHORTCUT%' -Force }; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%RUN_BAT_PATH%'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.IconLocation = 'C:\Windows\System32\shell32.dll,13'; $Shortcut.Description = 'Claude Code Launcher'; $Shortcut.Save()"
)

if %errorlevel% equ 0 (
    echo [OK] Desktop shortcut created
    echo.
    echo ====================================
    echo Installation Complete!
    echo ====================================
    echo.
    echo Shortcut location: %DESKTOP%\Claude Launcher.lnk
    echo.
    echo You can now double-click "Claude Launcher" on desktop
    echo.
) else (
    echo [Error] Failed to create shortcut
    echo Please create manually with target:
    echo "%RUN_BAT_PATH%"
    echo.
)

pause