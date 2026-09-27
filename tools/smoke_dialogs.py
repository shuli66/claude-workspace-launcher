"""构造两个对话框并立即关闭，确认无构造错误。"""

import os
import sys

os.environ["TCL_LIBRARY"] = ""
os.environ["TK_LIBRARY"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from claude_launcher import theme  # noqa: E402
from claude_launcher.config import Config  # noqa: E402
from claude_launcher.ui import dialogs  # noqa: E402


def main():
    root = tk.Tk()
    root.geometry("900x620")
    colors = theme.resolve("light")
    config = Config()

    settings = dialogs.SettingsDialog(root, config, colors, lambda t: None, lambda: None)
    root.update()
    settings.close()
    settings.close()  # 二次关闭必须是安全的

    mode = dialogs.ModeDialog(root, "D:\\proj", colors, lambda m: None)
    root.update()
    mode.close()

    print("对话框构造与关闭全部通过")
    root.destroy()


if __name__ == "__main__":
    main()
