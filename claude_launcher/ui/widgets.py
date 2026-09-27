"""无业务逻辑的展示控件。所有颜色经 colors 字典注入，不自行决定配色。"""

import tkinter as tk

from . import icons


class FlatButton(tk.Frame):
    """直角按钮：外框 Frame 承载 1px 描边，内层 Label 承载文字与点击。

    不用 Canvas 圆角是刻意的——直角描边在主题切换时只需重设两个控件的颜色，
    而 Canvas 需要重绘全部图元。
    """

    _PADDING_X = 12
    _PADDING_Y = 6

    def __init__(self, parent, text, command, colors, variant="primary", width=None):
        self.colors = colors
        self.variant = variant
        self.command = command
        self._enabled = True

        super().__init__(parent, bg=self._border_color(), padx=1, pady=1)

        self.label = tk.Label(
            self,
            text=text,
            font=("Segoe UI", 9, "bold" if variant in ("primary", "secondary") else "normal"),
            bg=self._bg_color(),
            fg=self._fg_color(),
            padx=self._PADDING_X,
            pady=self._PADDING_Y,
            cursor="hand2",
        )
        if width:
            self.label.config(width=width)
        self.label.pack(fill=tk.BOTH, expand=True)

        self.label.bind("<Enter>", self._on_enter)
        self.label.bind("<Leave>", self._on_leave)
        self.label.bind("<Button-1>", self._on_click)

    def _border_color(self):
        if self.variant == "ghost":
            return self.colors["line_strong"]
        return self.colors["accent"]

    def _bg_color(self):
        return {
            "primary": self.colors["accent"],
            "secondary": self.colors["accent_soft"],
            "ghost": self.colors["surface"],
            "danger": self.colors["danger"],
        }[self.variant]

    def _hover_bg(self):
        return {
            "primary": self.colors["accent_hi"],
            "secondary": self.colors["accent_soft"],
            "ghost": self.colors["hover"],
            "danger": self.colors["danger"],
        }[self.variant]

    def _fg_color(self):
        if self.variant in ("primary", "danger"):
            return "#ffffff"
        if self.variant == "secondary":
            return self.colors["accent"]
        return self.colors["ink_2"]

    def _on_enter(self, _event):
        if self._enabled:
            self.label.config(bg=self._hover_bg())

    def _on_leave(self, _event):
        if self._enabled:
            self.label.config(bg=self._bg_color())

    def _on_click(self, _event):
        if self._enabled and self.command:
            self.command()

    def set_text(self, text):
        self.label.config(text=text)


class IconButton(tk.Canvas):
    """正方形图标按钮。图标在 Canvas 上绘制，悬停时换底色。"""

    def __init__(self, parent, name, command, colors, size=28, tooltip=None):
        super().__init__(
            parent, width=size, height=size,
            bg=colors["surface"], highlightthickness=0, cursor="hand2",
        )
        self.colors = colors
        self.name = name
        self.command = command
        self.size = size
        self._tooltip = tooltip

        self._background = self.create_rectangle(0, 0, size, size, fill=colors["surface"], outline="")
        self._draw_icon(colors["ink_2"])

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda _event: self.command and self.command())

    def _draw_icon(self, color):
        inset = round(self.size * 0.22)
        icons.draw(self, self.name, color, self.size - inset * 2, x=inset, y=inset)

    def _on_enter(self, _event):
        self.itemconfig(self._background, fill=self.colors["hover"])
        self.delete("icon")
        self._draw_icon(self.colors["ink"])

    def _on_leave(self, _event):
        self.itemconfig(self._background, fill=self.colors["surface"])
        self.delete("icon")
        self._draw_icon(self.colors["ink_2"])

    def set_colors(self, colors):
        """主题切换后就地更新，避免重建控件树。"""
        self.colors = colors
        self.config(bg=colors["surface"])
        self.itemconfig(self._background, fill=colors["surface"])
        self.delete("icon")
        self._draw_icon(colors["ink_2"])

    def set_icon(self, name):
        """换图标（例如收藏星标在空心与实心之间切换）。"""
        self.name = name
        self.delete("icon")
        self._draw_icon(self.colors["ink_2"])


class Pill(tk.Frame):
    """状态徽标：小圆点 + 文字。"""

    def __init__(self, parent, text, colors, tone="neutral"):
        super().__init__(parent, bg=colors["surface"])
        self.colors = colors

        self.inner = tk.Frame(self, bg=self._bg(tone))
        self.inner.pack()

        self.dot = tk.Canvas(
            self.inner, width=10, height=10,
            bg=self._bg(tone), highlightthickness=0,
        )
        self.dot.pack(side=tk.LEFT, padx=(7, 0), pady=4)
        self._dot_id = self.dot.create_oval(3, 3, 7, 7, fill=self._fg(tone), outline="")

        self.label = tk.Label(
            self.inner, text=text, font=("Segoe UI", 8, "bold"),
            bg=self._bg(tone), fg=self._fg(tone), padx=3, pady=2,
        )
        self.label.pack(side=tk.LEFT, padx=(2, 8))

    def _bg(self, tone):
        return {
            "neutral": self.colors["sunken"],
            "ok": self.colors["ok_soft"],
            "danger": self.colors["danger_bg"],
        }[tone]

    def _fg(self, tone):
        return {
            "neutral": self.colors["ink_2"],
            "ok": self.colors["ok"],
            "danger": self.colors["danger"],
        }[tone]

    def set(self, text, tone):
        background = self._bg(tone)
        foreground = self._fg(tone)
        self.inner.config(bg=background)
        self.dot.config(bg=background)
        self.dot.itemconfig(self._dot_id, fill=foreground)
        self.label.config(text=text, bg=background, fg=foreground)


class SectionHeader(tk.Frame):
    """小节标题：左侧标题，右侧计数。"""

    def __init__(self, parent, title, colors):
        super().__init__(parent, bg=colors["bg"])
        self.colors = colors

        self.title_label = tk.Label(
            self, text=title, font=("Segoe UI", 8, "bold"),
            bg=colors["bg"], fg=colors["ink_3"], anchor=tk.W,
        )
        self.title_label.pack(side=tk.LEFT)

        self.count_label = tk.Label(
            self, text="", font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_3"], anchor=tk.E,
        )
        self.count_label.pack(side=tk.RIGHT)

    def set_count(self, count):
        self.count_label.config(text=str(count) if count else "")


class ScrollArea(tk.Frame):
    """带竖向滚动条的容器。子控件一律放进 self.content。"""

    def __init__(self, parent, colors):
        super().__init__(parent, bg=colors["bg"])
        self.colors = colors

        self.canvas = tk.Canvas(self, bg=colors["bg"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.content = tk.Frame(self.canvas, bg=colors["bg"])
        self._window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_content_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._window, width=event.width)

    def _bind_wheel(self, _event):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh_scrollregion(self):
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def clear(self):
        for child in self.content.winfo_children():
            child.destroy()

    def scroll_to_top(self):
        self.canvas.yview_moveto(0.0)
