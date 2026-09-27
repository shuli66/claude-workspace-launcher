"""模拟启动：构建整个应用后立刻退出，确认装配无遗漏。"""

import os
import sys

os.environ["TCL_LIBRARY"] = ""
os.environ["TK_LIBRARY"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from claude_launcher.app import LauncherApp, SingleInstance  # noqa: E402


def main():
    lock = SingleInstance()
    lock.acquire()

    root = tk.Tk()
    app = LauncherApp(root, lock)
    root.update()

    print("应用装配通过")
    print("窗口标题:", root.title())
    print("窗口尺寸:", root.winfo_width(), "x", root.winfo_height())
    print("托盘可用:", app.tray is not None)
    print("会话缓存分组:", len(app.store.get()))

    app.quit()
    print("退出路径通过")


if __name__ == "__main__":
    main()
