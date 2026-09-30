"""无业务逻辑的展示控件。所有颜色经 colors 字典注入，不自行决定配色。"""

import os
import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import icons


def rounded_points(x1, y1, x2, y2, radius):
    """生成圆角矩形的多边形顶点，配合 create_polygon(smooth=True) 使用。

    拐角处的四个顶点被紧邻的直边顶点「夹住」，smooth=True 会把每个拐角
    平滑成圆弧。radius 会被裁剪到不超过较短边的一半。
    """
    radius = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    return (
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    )


class RoundedFrame(tk.Canvas):
    """圆角卡片容器：Canvas 画圆角背景与描边，子控件放进 inner。

    尺寸双向传递：
    - 宽度自上而下 —— 外部 pack(fill=X) 拉伸 Canvas 时，同步给 inner；
    - 高度自下而上 —— inner 内容变高时，反向把 Canvas 拉高。
    """

    def __init__(self, parent, colors, fill=None, border=None, radius=10,
                 border_width=1, parent_bg=None):
        if fill is None:
            fill = colors["surface"]
        if parent_bg is None:
            try:
                parent_bg = parent.cget("bg")
            except tk.TclError:
                parent_bg = colors["bg"]

        self.colors = colors
        self._fill = fill
        self._border = border
        self._radius = radius
        self._bw = border_width

        super().__init__(
            parent, bg=parent_bg, highlightthickness=0, bd=0,
        )

        self.inner = tk.Frame(self, bg=fill)
        self._win = self.create_window(border_width, border_width, window=self.inner, anchor="nw")
        # 注意：tkinter 内部用 self._w 存控件路径名，这里绝不可占用 _w/_h，
        # 故用 _cur_w/_cur_h 记录 Configure 事件给的实际尺寸。
        self._cur_w = 0
        self._cur_h = 0
        self.inner.bind("<Configure>", self._on_inner_config)
        self.bind("<Configure>", self._on_canvas_config)

    def _is_stretched(self):
        """pack(fill=X/BOTH) 时宽度由父容器决定；否则应收缩到内容宽度。"""
        try:
            return self.pack_info().get("fill") in ("x", "both")
        except tk.TclError:
            return False

    def _on_canvas_config(self, event):
        """宽度自上而下：仅当被拉伸时强制 inner 宽度。"""
        self._cur_w = event.width
        if self._is_stretched():
            inner_w = max(1, event.width - 2 * self._bw)
            if int(self.itemcget(self._win, "width")) != inner_w:
                self.itemconfig(self._win, width=inner_w)
        self._redraw()

    def _on_inner_config(self, event):
        """高度自下而上；未被拉伸时宽度跟随内容请求宽度。

        Canvas 的默认请求宽度很大，pack(side=LEFT) 会照单全收 ——
        固定尺寸的用法（如顶栏标志）必须在这里把宽度收回内容实际所需。
        """
        h = event.height + 2 * self._bw
        self._cur_h = h
        if int(self.cget("height")) != h:
            self.config(height=h)
        if not self._is_stretched():
            req = self.inner.winfo_reqwidth() + 2 * self._bw
            if int(self.cget("width")) != req:
                self.config(width=req)
                self._cur_w = req
        self._redraw()

    def _redraw(self):
        # 必须用 Configure 事件记录的实际尺寸：cget("width") 返回的是配置值，
        # pack(fill=X) 拉伸后它仍是旧值，圆角背景就会画得比控件窄。
        w = self._cur_w or int(self.cget("width"))
        h = self._cur_h or int(self.cget("height"))
        if w <= 1 or h <= 1:
            return
        self.delete("bg")

        if self._border is not None:
            self.create_polygon(
                rounded_points(0, 0, w, h, self._radius),
                smooth=True, fill=self._border, outline="", tags="bg",
            )
            inset = self._bw
            r = max(1, self._radius - self._bw)
        else:
            inset = 0
            r = self._radius

        self.create_polygon(
            rounded_points(inset, inset, w - inset, h - inset, r),
            smooth=True, fill=self._fill, outline="", tags="bg",
        )
        self.tag_lower("bg", self._win)

    def set_fill(self, fill, border=None):
        """就地换色（主题切换或行选中态），并同步 inner 下所有 Frame/Label 背景。"""
        self._fill = fill
        if border is not None:
            self._border = border
        self.inner.config(bg=fill)
        self._recolor(self.inner, fill)
        self._redraw()

    @staticmethod
    def _recolor(widget, color):
        for child in widget.winfo_children():
            if child.winfo_class() in ("Frame", "Label"):
                try:
                    child.config(bg=color)
                except tk.TclError:
                    pass
                RoundedFrame._recolor(child, color)


class FlatButton(tk.Canvas):
    """圆角按钮：Canvas 画圆角背景，create_text 承载文字。

    Canvas 不随文字自动缩放，故用 tkfont 量取文字宽度、自行定尺寸。
    size 三档对应设计稿的 .mk-btn / .mk-btn.sm / .mk-btn.xs。
    """

    _SIZES = {
        "md": (14, 6, 8, 9),
        "sm": (10, 5, 7, 9),
        "xs": (10, 4, 6, 8),
    }

    def __init__(self, parent, text, command, colors, variant="primary",
                 width=None, size="md"):
        self.colors = colors
        self.variant = variant
        self.command = command
        self._enabled = True
        self._text = text
        pad_x, pad_y, self._radius, font_size = self._SIZES[size]
        self._pad_x = pad_x

        try:
            self._parent_bg = parent.cget("bg")
        except tk.TclError:
            self._parent_bg = colors["bg"]

        self._font = tkfont.Font(
            family="Segoe UI", size=font_size,
            weight="bold" if variant in ("primary", "secondary") else "normal",
        )
        text_w = self._font.measure(text)
        w = (width if width else text_w) + 2 * pad_x
        h = self._font.metrics("linespace") + 2 * pad_y

        super().__init__(
            parent, width=w, height=h,
            bg=self._parent_bg, highlightthickness=0, cursor="hand2",
        )
        self._draw()

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

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

    def _draw(self, fill=None):
        self.delete("all")
        w = int(self.cget("width"))
        h = int(self.cget("height"))
        fill = fill or self._bg_color()

        self.create_polygon(
            rounded_points(0, 0, w, h, self._radius),
            smooth=True, fill=self._border_color(), outline="",
        )
        self.create_polygon(
            rounded_points(1, 1, w - 1, h - 1, max(1, self._radius - 1)),
            smooth=True, fill=fill, outline="",
        )
        self.create_text(
            w // 2, h // 2, text=self._text,
            font=self._font, fill=self._fg_color(),
        )

    def _on_enter(self, _event):
        if self._enabled:
            self._draw(self._hover_bg())

    def _on_leave(self, _event):
        if self._enabled:
            self._draw(self._bg_color())

    def _on_click(self, _event):
        if self._enabled and self.command:
            self.command()

    def set_text(self, text):
        self._text = text
        w = self._font.measure(text) + 2 * self._pad_x
        self.config(width=w)
        self._draw()


class IconButton(tk.Canvas):
    """正方形图标按钮。图标在 Canvas 上绘制，悬停时换底色。

    底色取父容器背景而非硬编码 surface —— 否则放在顶栏（bg 色）或
    卡片上时会露出一块白色方角补丁。
    """

    def __init__(self, parent, name, command, colors, size=28, tooltip=None):
        try:
            parent_bg = parent.cget("bg")
        except tk.TclError:
            parent_bg = colors["surface"]
        self._parent_bg = parent_bg
        super().__init__(
            parent, width=size, height=size,
            bg=parent_bg, highlightthickness=0, cursor="hand2",
        )
        self.colors = colors
        self.name = name
        self.command = command
        self.size = size
        self._tooltip = tooltip

        self._background = self.create_rectangle(0, 0, size, size, fill=parent_bg, outline="")
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
        self.itemconfig(self._background, fill=self._parent_bg)
        self.delete("icon")
        self._draw_icon(self.colors["ink_2"])

    def set_colors(self, colors):
        """主题切换后就地更新，避免重建控件树。"""
        self.colors = colors
        self.config(bg=self._parent_bg)
        self.itemconfig(self._background, fill=self._parent_bg)
        self.delete("icon")
        self._draw_icon(colors["ink_2"])

    def set_icon(self, name):
        """换图标（例如收藏星标在空心与实心之间切换）。"""
        self.name = name
        self.delete("icon")
        self._draw_icon(self.colors["ink_2"])


class Pill(tk.Canvas):
    """胶囊状态徽标：圆角底 + 小圆点 + 文字。"""

    def __init__(self, parent, text, colors, tone="neutral"):
        try:
            self._parent_bg = parent.cget("bg")
        except tk.TclError:
            self._parent_bg = colors["bg"]
        self.colors = colors
        self._text = text
        self._tone = tone
        self._font = tkfont.Font(family="Segoe UI", size=8, weight="bold")

        w = self._measure(text)
        h = self._font.metrics("linespace") + 3
        super().__init__(
            parent, width=w, height=h,
            bg=self._parent_bg, highlightthickness=0,
        )
        self._draw()

    def _measure(self, text):
        return 16 + self._font.measure(text) + 14

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

    def _draw(self):
        self.delete("all")
        w = int(self.cget("width"))
        h = int(self.cget("height"))
        fill = self._bg(self._tone)
        fg = self._fg(self._tone)

        self.create_polygon(
            rounded_points(0, 0, w, h, h // 2),
            smooth=True, fill=fill, outline="",
        )
        self.create_oval(6, h // 2 - 3, 12, h // 2 + 3, fill=fg, outline="")
        self.create_text(
            17, h // 2, text=self._text, font=self._font, fill=fg, anchor="w",
        )

    def set(self, text, tone):
        self._text = text
        self._tone = tone
        self.config(width=self._measure(text))
        self._draw()


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
    """可滚动容器。设计稿不显示滚动条，仅响应鼠标滚轮。

    子控件一律放进 self.content。bg 可指定底色（会话侧栏用奶油底、
    收藏区用白底）。
    """

    def __init__(self, parent, colors, bg=None):
        bg = bg or colors["bg"]
        super().__init__(parent, bg=bg)
        self.colors = colors

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.content = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_content_configure(self, _event):
        # 只同步滚动区，不要给 window item 设高度：item 的高度必须跟随
        # content 的自然请求高度。若反过来用 content 的当前高度去设 item，
        # 会形成循环约束（item 高度压缩 content → content 再报更矮的高度），
        # 收敛到极小值，把列表行压成 1px。
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._window, width=event.width)

    def _bind_wheel(self, _event):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event):
        # 内容不比视口高时滚动无意义，且旧滚动区下会产生视图偏移空白。
        bbox = self.canvas.bbox("all")
        if not bbox or bbox[3] <= self.canvas.winfo_height():
            return
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh_scrollregion(self):
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # 内容变矮后旧的 yview 偏移会把内容顶到中间，上下留大片空白。
        # 重算滚动区后把视图夹回合法范围。
        try:
            top, _bottom = self.canvas.yview()
            if top > 0.0:
                self.canvas.yview_moveto(min(top, 1.0))
                top2, _b2 = self.canvas.yview()
                if top2 >= 1.0:
                    self.canvas.yview_moveto(0.0)
        except tk.TclError:
            pass

    def clear(self):
        for child in self.content.winfo_children():
            child.destroy()

    def scroll_to_top(self):
        self.canvas.yview_moveto(0.0)


def format_size(size):
    if size >= 1024 * 1024:
        return "%.1fMB" % (size / (1024 * 1024))
    if size >= 1024:
        return "%dKB" % (size / 1024)
    return "%dB" % size


def format_time(mtime):
    """设计稿的时间格式：今天 14:32、昨天「昨天」、更早 09-25。"""
    from datetime import datetime, timedelta

    try:
        dt = datetime.fromtimestamp(mtime)
    except (ValueError, OSError, OverflowError, TypeError):
        return ""

    today = datetime.now().date()
    if dt.date() == today:
        return dt.strftime("%H:%M")
    if dt.date() == today - timedelta(days=1):
        return "昨天"
    return dt.strftime("%m-%d")


def elide_path(path, limit=35):
    if len(path) <= limit:
        return path
    return "..." + path[-(limit - 3):]


def elide_text(text, font, max_width):
    """按像素宽度截断文本，超出时末尾补省略号。

    tkinter 的 Label 不随容器宽度截断文字——内容超宽时会按实际文字宽度
    请求空间，把右侧的删除按钮顶出可视区。必须用量出的像素宽度手动截断。
    """
    if font.measure(text) <= max_width:
        return text
    ellipsis = "…"
    for i in range(len(text), 0, -1):
        if font.measure(text[:i] + ellipsis) <= max_width:
            return text[:i] + ellipsis
    return ellipsis


class SessionRow(RoundedFrame):
    """会话列表的一行。单击选中，双击恢复。

    设计稿里行的选中/悬停背景是圆角 + 左侧 2px 强调色条，
    故整行用 RoundedFrame 承载。
    """

    _HEIGHT = 26
    # 右侧固定预留：时间标签 + 删除按钮 + 两侧留白。
    _RIGHT_RESERVE = 72

    def __init__(self, parent, session, colors, on_select, on_resume, on_delete):
        super().__init__(parent, colors, fill=colors["bg"], border=None,
                         radius=7, parent_bg=colors["bg"])
        self.inner.config(height=self._HEIGHT)
        self.inner.pack_propagate(False)

        self.session = session
        self.colors = colors
        self.on_select = on_select
        self.on_resume = on_resume
        self.on_delete = on_delete
        self._selected = False

        self.accent_bar = tk.Frame(self.inner, bg=colors["bg"], width=2)
        self.accent_bar.pack(side=tk.LEFT, fill=tk.Y)

        raw_title = session.get("prompt") or session.get("id", "")
        self._title_font = tkfont.Font(family="Segoe UI", size=9)
        self.title = tk.Label(
            self.inner,
            text=raw_title,
            font=self._title_font,
            bg=colors["bg"], fg=colors["ink_2"],
            anchor=tk.W, padx=14,
        )
        self.title.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._raw_title = raw_title
        # 等控件完成布局后再按实际可用宽度截断标题。
        self.title.bind("<Configure>", self._on_title_configure)

        self.time_label = tk.Label(
            self.inner, text=format_time(session.get("mtime", 0)),
            font=("Segoe UI", 8), bg=colors["bg"], fg=colors["ink_3"], padx=5,
        )
        self.time_label.pack(side=tk.RIGHT)

        self.delete_btn = tk.Label(
            self.inner, text="✕", font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["bg"], padx=4, cursor="hand2",
        )
        self.delete_btn.pack(side=tk.RIGHT)

        for widget in (self, self.inner, self.title, self.time_label):
            widget.bind("<Button-1>", self._click)
            widget.bind("<Double-Button-1>", self._double_click)
            widget.bind("<Enter>", self._hover_in)
            widget.bind("<Leave>", self._hover_out)

        self.delete_btn.bind("<Button-1>", lambda _event: self.on_delete(self.session))
        self.delete_btn.bind("<Enter>", lambda _event: self.delete_btn.config(fg=colors["danger"]))
        self.delete_btn.bind("<Leave>", lambda _event: self.delete_btn.config(
            fg=colors["danger"] if self._selected else self._background()))

    def _on_title_configure(self, event):
        """标题 Label 宽度确定后，按实际像素截断文字，给右侧按钮预留空间。"""
        available = event.width - self._RIGHT_RESERVE
        if available < 20:
            return
        self.title.config(text=elide_text(self._raw_title, self._title_font, available))

    def _background(self):
        return self.colors["accent_soft"] if self._selected else self.colors["bg"]

    def _paint(self, background):
        self.set_fill(background)
        self.accent_bar.config(
            bg=self.colors["accent"] if self._selected else background)
        self.delete_btn.config(
            fg=self.colors["danger"] if self._selected else background)

    def _click(self, _event):
        self.on_select(self.session)

    def _double_click(self, _event):
        self.on_resume(self.session)

    def _hover_in(self, _event):
        if not self._selected:
            self._paint(self.colors["hover"])
            self.delete_btn.config(fg=self.colors["ink_3"])

    def _hover_out(self, _event):
        if not self._selected:
            self._paint(self.colors["bg"])

    def set_selected(self, selected):
        self._selected = selected
        self._paint(self._background())
        self.title.config(fg=self.colors["ink"] if selected else self.colors["ink_2"])


class FolderGroupRow(tk.Frame):
    """可折叠的项目分组。标题行 + 子会话行容器。"""

    def __init__(self, parent, project_path, sessions, colors, on_select,
                 on_resume, on_delete, on_double_click, on_toggle,
                 expanded=True):
        super().__init__(parent, bg=colors["bg"])

        self.project_path = project_path
        self.sessions = sessions
        self.colors = colors
        self.expanded = expanded
        self.on_toggle = on_toggle

        # 设计稿 .mk-grp：7px 圆角色块，悬停整块变色
        header = RoundedFrame(
            self, colors, fill=colors["bg"], border=None, radius=7,
            parent_bg=colors["bg"],
        )
        header.pack(fill=tk.X, pady=(4, 0))
        self.header = header
        head = header.inner
        head.config(bg=colors["bg"])

        self.chevron = tk.Canvas(
            head, width=14, height=14, bg=colors["bg"], highlightthickness=0,
        )
        self.chevron.pack(side=tk.LEFT, padx=(6, 2), pady=6)
        self._draw_chevron()

        self.folder_icon = tk.Canvas(
            head, width=14, height=14, bg=colors["bg"], highlightthickness=0,
        )
        self.folder_icon.pack(side=tk.LEFT, padx=(0, 4), pady=6)
        icons.draw(self.folder_icon, "folder", colors["ink_3"], 13, x=1, y=1)

        self.name_label = tk.Label(
            head, text=os.path.basename(project_path) or project_path,
            font=("Segoe UI", 9, "bold"), bg=colors["bg"], fg=colors["ink"], anchor=tk.W,
        )
        self.name_label.pack(side=tk.LEFT, pady=6)

        self.count_label = tk.Label(
            head, text=str(len(sessions)), font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_3"], padx=6, pady=6,
        )
        self.count_label.pack(side=tk.RIGHT)

        self.rows = []
        self.children_frame = tk.Frame(self, bg=colors["bg"])

        for session in sessions:
            row = SessionRow(
                self.children_frame, session, colors, on_select, on_resume, on_delete,
            )
            row.pack(fill=tk.X)
            self.rows.append(row)

        if self.expanded:
            self.children_frame.pack(fill=tk.X)

        for widget in (header, self.name_label, self.count_label, self.chevron,
                       self.folder_icon):
            widget.bind("<Button-1>", self._toggle)
            widget.bind("<Double-Button-1>", lambda _event: on_double_click(project_path))
            widget.bind("<Enter>", self._hover_in)
            widget.bind("<Leave>", self._hover_out)

    def _draw_chevron(self):
        self.chevron.delete("icon")
        icons.draw(
            self.chevron,
            "chevron_down" if self.expanded else "chevron_right",
            self.colors["ink_3"], 12, x=1, y=1,
        )

    def _hover_in(self, _event):
        self.header.set_fill(self.colors["hover"])
        self.chevron.config(bg=self.colors["hover"])
        self.folder_icon.config(bg=self.colors["hover"])

    def _hover_out(self, _event):
        self.header.set_fill(self.colors["bg"])
        self.chevron.config(bg=self.colors["bg"])
        self.folder_icon.config(bg=self.colors["bg"])

    def _toggle(self, _event):
        self.expanded = not self.expanded
        if self.expanded:
            self.children_frame.pack(fill=tk.X)
        else:
            self.children_frame.pack_forget()
        self._draw_chevron()
        self.on_toggle(self.project_path, self.expanded)

    def set_child_selection(self, session_id):
        for row in self.rows:
            row.set_selected(row.session.get("id") == session_id)


class FavoriteRow(RoundedFrame):
    """收藏夹的一行：名称 + 路径 + 打开 + 启动 + 移除。"""

    def __init__(self, parent, path, colors, on_open, on_launch, on_remove):
        # 设计稿：收藏行是奶油色圆角卡片（白底收藏区上）
        super().__init__(parent, colors, fill=colors["bg"], border=colors["line"],
                         radius=9, parent_bg=colors["surface"])
        self.path = path

        body = self.inner
        body.config(bg=colors["bg"])

        icon = tk.Canvas(body, width=16, height=16, bg=colors["bg"], highlightthickness=0)
        icon.pack(side=tk.LEFT, padx=(9, 6), pady=7)
        icons.draw(icon, "star_filled", colors["accent"], 13, x=1, y=1)

        text = tk.Frame(body, bg=colors["bg"])
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(
            text, text=os.path.basename(path) or path, font=("Segoe UI", 9),
            bg=colors["bg"], fg=colors["ink"], anchor=tk.W,
        ).pack(fill=tk.X, pady=(3, 0))
        tk.Label(
            text, text=elide_path(path, 42), font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_3"], anchor=tk.W,
        ).pack(fill=tk.X)

        actions = tk.Frame(body, bg=colors["bg"])
        actions.pack(side=tk.RIGHT, padx=(4, 8))

        FlatButton(actions, "启动", lambda: on_launch(path), colors, size="xs").pack(side=tk.RIGHT)
        FlatButton(actions, "打开", lambda: on_open(path), colors, variant="ghost",
                   size="xs").pack(side=tk.RIGHT, padx=(0, 5))

        remove = tk.Label(
            actions, text="✕", font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["bg"], padx=6, cursor="hand2",
        )
        remove.pack(side=tk.RIGHT)
        remove.bind("<Button-1>", lambda _event: on_remove(path))
        remove.bind("<Enter>", lambda _event: remove.config(fg=colors["danger"]))
        remove.bind("<Leave>", lambda _event: remove.config(fg=colors["bg"]))

        # 设计稿里 ✕ 只在悬停整行时出现。逐控件绑定 Enter/Leave：
        # Tk 的 Enter/Leave 按最内层控件派发，祖先会收到 Leave，
        # 故需递归绑到每个子控件上（add="+" 保留 FlatButton 自身的悬停处理）。
        def _reveal(node):
            if node is not remove:
                node.bind("<Enter>", lambda _e: remove.config(fg=colors["ink_3"]), add="+")
                node.bind("<Leave>", lambda _e: remove.config(fg=colors["bg"]), add="+")
            for child in node.winfo_children():
                _reveal(child)
        _reveal(self.inner)
