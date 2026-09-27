"""Claude Launcher 打包脚本：使用 PyInstaller 生成单文件 exe。"""

import sys
from pathlib import Path

import PyInstaller.__main__

PROJECT_DIR = Path(__file__).parent
ASSETS = PROJECT_DIR / "assets"
ENTRY = PROJECT_DIR / "main.py"
ICON = ASSETS / "claude_icon.ico"


def main():
    if not ENTRY.exists():
        print("找不到入口文件 %s" % ENTRY)
        sys.exit(1)

    if not ASSETS.exists():
        print("找不到资源目录 %s" % ASSETS)
        sys.exit(1)

    arguments = [
        str(ENTRY),
        "--name=ClaudeLauncher",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--add-data=%s;assets" % ASSETS,
        "--distpath=%s" % (PROJECT_DIR / "dist"),
        "--workpath=%s" % (PROJECT_DIR / "build"),
        "--specpath=%s" % PROJECT_DIR,
    ]

    if ICON.exists():
        arguments.append("--icon=%s" % ICON)

    PyInstaller.__main__.run(arguments)

    print("\n" + "=" * 60)
    print("打包完成")
    print("=" * 60)
    print("输出文件: %s" % (PROJECT_DIR / "dist" / "ClaudeLauncher.exe"))
    print("同时需要分发 install.bat 以便创建桌面快捷方式")


if __name__ == "__main__":
    main()
