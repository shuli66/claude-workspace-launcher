"""
Claude Launcher - Build Script
使用 PyInstaller 打包成单文件 exe
"""

import PyInstaller.__main__
import os
from pathlib import Path

# 获取项目目录
project_dir = Path(__file__).parent

# PyInstaller 参数
PyInstaller.__main__.run([
    str(project_dir / 'claude_launcher.py'),  # 主程序
    '--name=ClaudeLauncher',                   # 输出文件名
    '--onefile',                               # 打包成单文件
    '--windowed',                              # 无控制台窗口
    '--icon=' + str(project_dir / 'claude_icon.ico'),  # 图标
    '--add-data=' + str(project_dir / 'claude_icon.ico') + ';.',  # 包含图标文件
    '--clean',                                 # 清理临时文件
    '--noconfirm',                            # 覆盖输出目录
    '--distpath=' + str(project_dir / 'dist'),  # 输出目录
    '--workpath=' + str(project_dir / 'build'),  # 临时目录
    '--specpath=' + str(project_dir),          # spec 文件位置
])

print("\n" + "="*60)
print("打包完成！")
print("="*60)
print(f"输出文件: {project_dir / 'dist' / 'ClaudeLauncher.exe'}")
print("\n使用方法:")
print("1. 将 ClaudeLauncher.exe 复制到任意目录")
print("2. 双击运行即可")
print("3. 可选：创建桌面快捷方式")
