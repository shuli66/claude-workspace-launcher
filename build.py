"""Claude Launcher 打包脚本：使用 PyInstaller 生成单文件 exe。"""

import os
import sys
from pathlib import Path

import PyInstaller.__main__

PROJECT_DIR = Path(__file__).parent
ASSETS = PROJECT_DIR / "assets"
ENTRY = PROJECT_DIR / "main.py"
ICON = ASSETS / "claude_icon.ico"

# PyInstaller 的 Tcl/Tk 发现逻辑优先采信 TK_LIBRARY / TCL_LIBRARY 环境变量
# （见 PyInstaller/utils/hooks/tcl_tk.py）。若这两个变量指向失效路径 ——
# 例如某个 PyInstaller 打包程序泄漏出来的临时目录 —— 数据文件收集会得到
# 空列表，而钩子在列表为空时不报错，最终静默产出一个缺失 tkinter 的坏 exe。
# 故打包前必须真正删除它们（赋空串不算删除，Tcl 会把空串当作有效路径）。
for _var in ("TCL_LIBRARY", "TK_LIBRARY"):
    os.environ.pop(_var, None)


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

    if not verify_bundle():
        sys.exit(1)

    print("\n" + "=" * 60)
    print("打包完成")
    print("=" * 60)
    print("输出文件: %s" % (PROJECT_DIR / "dist" / "ClaudeLauncher.exe"))
    print("同时需要分发 install.bat 以便创建桌面快捷方式")


def verify_bundle():
    """校验产物真的包含 Tcl/Tk。

    tkinter 缺失时程序一启动就 ModuleNotFoundError 闪退，而打包过程本身
    不会报错 —— 故这里主动检查，宁可打包失败也不要交付坏产物。
    """
    exe = PROJECT_DIR / "dist" / "ClaudeLauncher.exe"
    if not exe.exists():
        print("校验失败：未生成 %s" % exe)
        return False

    payload = exe.read_bytes()
    required = {
        b"_tkinter": "_tkinter 扩展模块",
        b"tcl86t.dll": "Tcl 运行时 DLL",
        b"tk86t.dll": "Tk 运行时 DLL",
    }
    missing = [desc for marker, desc in required.items() if marker not in payload]

    if missing:
        print("\n" + "!" * 60)
        print("打包校验失败：产物缺失 Tcl/Tk 组件")
        for item in missing:
            print("  - %s" % item)
        print()
        print("该 exe 启动时会因 ModuleNotFoundError: No module named 'tkinter' 而闪退。")
        print("请确认 TCL_LIBRARY / TK_LIBRARY 未指向失效路径后重新打包。")
        print("!" * 60)
        return False

    print("\n校验通过：产物已包含 Tcl/Tk 运行时")
    return True


if __name__ == "__main__":
    main()
