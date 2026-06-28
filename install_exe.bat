@echo off
chcp 65001 >nul
echo ====================================
echo AI Coding Launcher - 安装快捷方式
echo ====================================
echo.

REM 检查 exe 文件
if not exist "%~dp0ClaudeLauncher.exe" (
    echo [错误] 找不到 ClaudeLauncher.exe
    echo 请确保此脚本与 ClaudeLauncher.exe 在同一目录
    pause
    exit /b 1
)

echo [OK] 找到 ClaudeLauncher.exe
echo.

REM 创建桌面快捷方式
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT=%DESKTOP%\AI Coding Launcher.lnk
set EXE_PATH=%~dp0ClaudeLauncher.exe

echo 正在创建桌面快捷方式...

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; if (Test-Path '%SHORTCUT%') { Remove-Item '%SHORTCUT%' -Force }; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%EXE_PATH%'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Description = 'AI Coding Launcher'; $Shortcut.Save()"

if %errorlevel% equ 0 (
    echo [OK] 桌面快捷方式创建成功
    echo.
    echo ====================================
    echo 安装完成！
    echo ====================================
    echo.
    echo 快捷方式位置: %DESKTOP%\AI Coding Launcher.lnk
    echo.
    echo 现在可以双击桌面上的 "AI Coding Launcher" 启动程序
    echo.
) else (
    echo [错误] 创建快捷方式失败
    echo 请手动创建快捷方式，目标文件:
    echo "%EXE_PATH%"
    echo.
)

pause
