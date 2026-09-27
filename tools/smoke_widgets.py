"""构造每个控件一次，确认无构造错误。"""

import os
import sys

os.environ["TCL_LIBRARY"] = ""
os.environ["TK_LIBRARY"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from claude_launcher import theme  # noqa: E402
from claude_launcher.ui import widgets  # noqa: E402


def main():
    root = tk.Tk()
    root.withdraw()
    colors = theme.resolve("light")

    frame = tk.Frame(root, bg=colors["surface"])
    frame.pack()

    for variant in ("primary", "secondary", "ghost", "danger"):
        widgets.FlatButton(frame, variant, None, colors, variant=variant).pack(pady=2)

    for name in ("refresh", "gear", "folder", "close"):
        widgets.IconButton(frame, name, None, colors).pack(side=tk.LEFT, padx=2)

    for tone in ("neutral", "ok", "danger"):
        widgets.Pill(frame, tone, colors, tone=tone).pack(pady=2)

    header = widgets.SectionHeader(frame, "会话", colors)
    header.pack()
    header.set_count(5)

    area = widgets.ScrollArea(frame, colors)
    area.pack()
    tk.Label(area.content, text="内容", bg=colors["bg"]).pack()
    area.refresh_scrollregion()

    print("控件构造全部通过")
    root.destroy()


if __name__ == "__main__":
    main()
