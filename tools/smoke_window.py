"""构建主窗口，确认骨架与两个动态区域都不报错。"""

import os
import sys

os.environ["TCL_LIBRARY"] = ""
os.environ["TK_LIBRARY"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from claude_launcher.config import Config  # noqa: E402
from claude_launcher.sessions import SessionStore  # noqa: E402
from claude_launcher.ui.window import MainWindow  # noqa: E402


def main():
    root = tk.Tk()
    root.withdraw()

    config = Config()
    config.load()
    store = SessionStore()

    window = MainWindow(root, config, store)
    window.set_status("冒烟测试", "success")
    root.update()

    print("主窗口构造通过")
    print("会话分组数:", len(store.get()))
    root.destroy()


if __name__ == "__main__":
    main()
