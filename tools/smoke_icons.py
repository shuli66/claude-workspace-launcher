"""在离屏窗口里把每个图标画一遍，确认没有绘制错误。不截图，只看是否抛异常。"""

import os
import sys

os.environ["TCL_LIBRARY"] = ""
os.environ["TK_LIBRARY"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from claude_launcher.ui import icons  # noqa: E402

NAMES = [
    "folder", "refresh", "gear", "play", "bolt", "star", "star_filled",
    "chevron_down", "chevron_right", "clock", "plus", "open_external", "close",
]


def main():
    root = tk.Tk()
    root.withdraw()
    canvas = tk.Canvas(root, width=400, height=200)
    canvas.pack()

    for index, name in enumerate(NAMES):
        icons.draw(canvas, name, "#d97757", 24, x=10 + (index % 7) * 32, y=10 + (index // 7) * 40)

    print("claude_mark:", icons.claude_mark() is not None)
    print("assets_dir:", icons.assets_dir())
    print("已绘制 %d 个图标，无异常" % len(NAMES))
    root.destroy()


if __name__ == "__main__":
    main()
