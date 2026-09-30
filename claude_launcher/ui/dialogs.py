"""模态对话框：设置与启动模式选择。

关键修复：主题切换必须先关闭本对话框再回调。父窗口重建时会 destroy 全部子控件，
其中包含本 Toplevel，之后再 destroy 一次会抛 TclError。
"""

import tkinter as tk

from .. import agent
from .widgets import FlatButton


def _center_on_parent(window, parent, width, height):
    window.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - width) // 2
    y = parent.winfo_y() + (parent.winfo_height() - height) // 2
    window.geometry("%dx%d+%d+%d" % (width, height, x, y))


class _BaseDialog:
    """共用的窗口搭建。子类只需实现 build(body)。"""

    width = 420
    height = 300
    title = "对话框"

    def __init__(self, parent, colors):
        self.parent = parent
        self.colors = colors
        self.closed = False

        self.window = tk.Toplevel(parent)
        self.window.title(self.title)
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.configure(bg=colors["bg"])
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        body = tk.Frame(self.window, bg=colors["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=18)
        self.build(body)

        _center_on_parent(self.window, parent, self.width, self.height)
        self.window.grab_set()

    def build(self, body):
        raise NotImplementedError

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.window.grab_release()
        except tk.TclError:
            pass
        self.window.destroy()


class SettingsDialog(_BaseDialog):

    width = 420
    height = 340
    title = "设置"

    def __init__(self, parent, config, colors, on_theme_change, on_quit):
        self.config = config
        self.on_theme_change = on_theme_change
        self.on_quit = on_quit
        super().__init__(parent, colors)

    def build(self, body):
        colors = self.colors

        tk.Label(
            body, text="外观主题", font=("Segoe UI", 10, "bold"),
            bg=colors["bg"], fg=colors["ink"], anchor=tk.W,
        ).pack(fill=tk.X)

        tk.Label(
            body, text="选择界面的配色方案", font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_2"], anchor=tk.W,
        ).pack(fill=tk.X, pady=(0, 10))

        current = self.config.get("theme", "auto")
        for theme_id, label, desc in (
            ("auto", "跟随系统", "随 Windows 应用主题自动切换"),
            ("light", "浅色模式", "奶油米底，适合白天"),
            ("dark", "深色模式", "暖炭灰底，适合夜间"),
        ):
            self._theme_option(body, theme_id, label, desc, theme_id == current)

        separator = tk.Frame(body, bg=colors["line"], height=1)
        separator.pack(fill=tk.X, pady=14)

        tk.Label(
            body, text="启动选项", font=("Segoe UI", 10, "bold"),
            bg=colors["bg"], fg=colors["ink"], anchor=tk.W,
        ).pack(fill=tk.X, pady=(0, 8))

        self.auto_close_var = tk.BooleanVar(value=bool(self.config.get("auto_close", True)))
        checkbox = tk.Checkbutton(
            body, text="启动 Claude Code 后自动关闭启动器",
            variable=self.auto_close_var,
            font=("Segoe UI", 9),
            bg=colors["bg"], fg=colors["ink"],
            activebackground=colors["bg"], activeforeground=colors["ink"],
            selectcolor=colors["surface"],
            anchor=tk.W, relief=tk.FLAT, highlightthickness=0,
            command=self._save_auto_close,
        )
        checkbox.pack(fill=tk.X)

        self.skip_perms_var = tk.BooleanVar(
            value=bool(self.config.get("default_skip_permissions", False)))
        skip_checkbox = tk.Checkbutton(
            body, text="默认使用跳过权限模式启动会话",
            variable=self.skip_perms_var,
            font=("Segoe UI", 9),
            bg=colors["bg"], fg=colors["ink"],
            activebackground=colors["bg"], activeforeground=colors["ink"],
            selectcolor=colors["surface"],
            anchor=tk.W, relief=tk.FLAT, highlightthickness=0,
            command=self._save_skip_permissions,
        )
        skip_checkbox.pack(fill=tk.X, pady=(4, 0))

        footer = tk.Frame(body, bg=colors["bg"])
        footer.pack(fill=tk.X, side=tk.BOTTOM, pady=(16, 0))

        FlatButton(footer, "关闭", self.close, colors, variant="ghost").pack(side=tk.RIGHT)
        FlatButton(footer, "退出程序", self._quit, colors, variant="danger").pack(
            side=tk.RIGHT, padx=(0, 8))

    def _theme_option(self, parent, theme_id, label, desc, active):
        colors = self.colors
        row = tk.Frame(parent, bg=colors["bg"])
        row.pack(fill=tk.X, pady=2)

        marker = tk.Canvas(row, width=18, height=18, bg=colors["bg"], highlightthickness=0)
        marker.pack(side=tk.LEFT, padx=(0, 8), pady=2)
        if active:
            marker.create_oval(3, 3, 15, 15, fill=colors["accent"], outline="")
            marker.create_oval(7, 7, 11, 11, fill=colors["bg"], outline="")
        else:
            marker.create_oval(3, 3, 15, 15, outline=colors["ink_3"], width=1)

        text = tk.Frame(row, bg=colors["bg"])
        text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        title = tk.Label(
            text, text=label,
            font=("Segoe UI", 9, "bold" if active else "normal"),
            bg=colors["bg"], fg=colors["ink"], anchor=tk.W, cursor="hand2",
        )
        title.pack(fill=tk.X)
        subtitle = tk.Label(
            text, text=desc, font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_3"], anchor=tk.W, cursor="hand2",
        )
        subtitle.pack(fill=tk.X)

        handler = lambda _event: self._change_theme(theme_id)
        for widget in (row, marker, text, title, subtitle):
            widget.bind("<Button-1>", handler)

    def _change_theme(self, theme_id):
        # 先关闭自身：父窗口重建会连带销毁本窗口，之后再 destroy 会抛 TclError。
        self.close()
        self.on_theme_change(theme_id)

    def _save_auto_close(self):
        self.config.set("auto_close", bool(self.auto_close_var.get()))
        self.config.save()

    def _save_skip_permissions(self):
        self.config.set("default_skip_permissions", bool(self.skip_perms_var.get()))
        self.config.save()

    def _quit(self):
        self.close()
        self.on_quit()


class ModeDialog(_BaseDialog):

    width = 400
    height = 300
    title = "选择启动模式"

    def __init__(self, parent, project_path, colors, on_choose):
        self.project_path = project_path
        self.on_choose = on_choose
        super().__init__(parent, colors)

    def build(self, body):
        colors = self.colors
        self.window.title("选择启动模式")

        tk.Label(
            body, text="选择启动模式", font=("Segoe UI", 12, "bold"),
            bg=colors["bg"], fg=colors["ink"], anchor=tk.W,
        ).pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            body, text="项目：%s" % self.project_path, font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_3"], anchor=tk.W,
            wraplength=self.width - 50, justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(0, 14))

        for mode_id, config in agent.MODES.items():
            block = tk.Frame(body, bg=colors["bg"])
            block.pack(fill=tk.X, pady=(0, 6))

            FlatButton(
                block, config["label"],
                lambda m=mode_id: self._choose(m),
                colors,
                variant="primary" if mode_id == agent.DEFAULT_MODE else "ghost",
            ).pack(fill=tk.X)

            tk.Label(
                block, text=config["desc"], font=("Segoe UI", 8),
                bg=colors["bg"], fg=colors["ink_3"], anchor=tk.W,
            ).pack(fill=tk.X, pady=(3, 0))

        FlatButton(body, "取消", self.close, colors, variant="ghost").pack(
            fill=tk.X, pady=(10, 0))

    def _choose(self, mode_id):
        self.close()
        self.on_choose(mode_id)
