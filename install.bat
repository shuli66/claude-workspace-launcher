@echo off
chcp 65001 >nul
echo ====================================
echo Claude Launcher - 创建桌面快捷方式
echo ====================================
echo.

if not exist "%~dp0ClaudeLauncher.exe" (
    echo [错误] 找不到 ClaudeLauncher.exe
    echo 请将此脚本与 ClaudeLauncher.exe 放在同一目录
    pause
    exit /b 1
)

echo [OK] 找到 ClaudeLauncher.exe
echo.

set SHORTCUT=%USERPROFILE%\Desktop\ClaudeLauncher.exe.lnk
set EXE_PATH=%~dp0ClaudeLauncher.exe
set ICON_PATH=%~dp0assets\claude_icon.ico

echo 正在创建桌面快捷方式...

powershell -Command "$shell = New-Object -ComObject WScript.Shell; if (Test-Path '%SHORTCUT%') { Remove-Item '%SHORTCUT%' -Force }; $s = $shell.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%EXE_PATH%'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Claude Launcher'; if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%,0' }; $s.Save()"

if %errorlevel% equ 0 (
    echo [OK] 桌面快捷方式创建成功
    echo.
    echo 快捷方式位置: %SHORTCUT%
    echo 现在可以双击桌面上的 "ClaudeLauncher.exe" 启动程序
) else (
    echo [错误] 创建快捷方式失败
    echo 请手动创建，目标文件: "%EXE_PATH%"
)

echo.
pause
