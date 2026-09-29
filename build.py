"""Claude Launcher 打包脚本：使用 PyInstaller 生成可分发目录（onedir）。"""

import os
import sys
import shutil
from pathlib import Path

import PyInstaller.__main__

PROJECT_DIR = Path(__file__).parent
ASSETS = PROJECT_DIR / "assets"
ENTRY = PROJECT_DIR / "main.py"
ICON = ASSETS / "claude_icon.ico"

# 分发目录：dist/ClaudeLauncher/（PyInstaller onedir 的默认输出）——
# 里面是 ClaudeLauncher.exe + _internal/（全部依赖与资源）。
DIST_DIR = PROJECT_DIR / "dist" / "ClaudeLauncher"
EXE_PATH = DIST_DIR / "ClaudeLauncher.exe"

# Python 3.12 的运行库拆成两个：python312.dll（解释器本体）与
# python3.dll（共享运行库，python312.dll 的导入表直接引用它）。
# PyInstaller 打包 python312.dll 却漏掉 python3.dll。本机 PATH 里有
# 系统 Python 时启动会碰巧成功，但换台没装 Python 的机器就报
# LoadLibrary 错误 126（"Failed to load Python DLL"），且发生在解释器
# 加载之前，Python 兜底都拦不住。故显式打包 python3.dll。
PYTHON3_DLL = Path(sys.base_prefix) / "python3.dll"

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
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--add-data=%s;assets" % ASSETS,
        "--add-binary=%s;." % PYTHON3_DLL,
        "--distpath=%s" % (PROJECT_DIR / "dist"),
        "--workpath=%s" % (PROJECT_DIR / "build"),
        "--specpath=%s" % PROJECT_DIR,
    ]

    # 本项目只依赖标准库 + pystray + Pillow。但 PyInstaller 的静态分析会
    # 被 site-packages 里的 .pth 污染（如 pywin32.pth 自动 import
    # pywin32_bootstrap、若干 editable 安装的 finder），把 numpy/scipy/
    # pygame/pywin32 等从不使用的巨型包卷进产物。故显式排除，只留实际依赖。
    for excluded in (
        "numpy", "scipy", "pygame", "win32api", "win32com", "win32con",
        "win32gui", "win32process", "pythoncom", "pywintypes", "setuptools",
        "pkg_resources", "matplotlib", "pandas", "cv2", "IPython",
    ):
        arguments.append("--exclude-module=%s" % excluded)

    if ICON.exists():
        arguments.append("--icon=%s" % ICON)

    pyi_run = PyInstaller.__main__.run(arguments)

    if not verify_bundle():
        sys.exit(1)

    copy_installer()

    print("\n" + "=" * 60)
    print("打包完成（onedir 目录模式）")
    print("=" * 60)
    print("分发目录: %s" % DIST_DIR)
    print("分发时把整个 ClaudeLauncher 文件夹复制走即可：")
    print("  - %s" % DIST_DIR)
    print("  - 再运行其中的 install.bat 创建桌面快捷方式")


def verify_bundle():
    """校验产物关键文件齐全。

    单文件模式（onefile）在这套 Python 3.12 环境下会因运行时解压
    python312.dll 的依赖 python3.dll 缺失而启动即弹 "Error"（错误发生在
    解释器加载之前，任何 Python 兜底都拦不住）。onedir 没有运行时解压，
    直接校验 _internal 里的文件即可。
    """
    internal = DIST_DIR / "_internal"

    if not EXE_PATH.exists():
        print("校验失败：未生成 %s" % EXE_PATH)
        return False

    required = {
        "python312.dll": "解释器本体",
        "python3.dll": "Python 3.12 共享运行库（缺失会导致 exe 启动即报 LoadLibrary 失败）",
        "_tkinter.pyd": "_tkinter 扩展",
        "tcl86t.dll": "Tcl 运行时 DLL",
        "tk86t.dll": "Tk 运行时 DLL",
    }
    for filename, desc in required.items():
        path = internal / filename
        if not path.exists():
            print("\n" + "!" * 60)
            print("打包校验失败：缺失 %s（%s）" % (filename, desc))
            print("!" * 60)
            return False

    # 资源（Claude 标志与窗口图标）应与 exe 同层
    for resource in ("assets",):
        if not (internal / resource).exists():
            print("\n" + "!" * 60)
            print("打包校验失败：缺失资源目录 %s" % resource)
            print("!" * 60)
            return False

    print("\n校验通过：产物关键组件齐全")
    return True


def copy_installer():
    """把 install.bat 复制进分发目录，方便直接分发整个文件夹。"""
    source = PROJECT_DIR / "install.bat"
    if source.exists():
        shutil.copy2(source, DIST_DIR / "install.bat")


if __name__ == "__main__":
    main()