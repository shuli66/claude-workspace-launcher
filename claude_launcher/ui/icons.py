"""Canvas 手绘图标与 Claude 标志位图。

不使用 emoji（跨 Windows 版本渲染不一致，且无法控制颜色），也不打包图标字体
（需要额外二进制文件）。手绘图标可以完全控制描边与颜色，天然适配主题切换。
"""

import sys
from pathlib import Path
from typing import Optional

import tkinter as tk

_mark_cache: Optional[tk.PhotoImage] = None
_mark_loaded = False


def assets_dir() -> Path:
    """PyInstaller 单文件模式解包到 sys._MEIPASS，源码运行则在仓库根目录。"""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "assets"
    return Path(__file__).resolve().parent.parent.parent / "assets"


def claude_mark() -> Optional[tk.PhotoImage]:
    """懒加载 Claude 标志位图。加载失败返回 None，调用方需处理空值。"""
    global _mark_cache, _mark_loaded
    if _mark_loaded:
        return _mark_cache

    _mark_loaded = True
    path = assets_dir() / "claude-mark.png"
    if not path.exists():
        return None

    try:
        _mark_cache = tk.PhotoImage(file=str(path))
    except tk.TclError:
        _mark_cache = None

    return _mark_cache


def _polyline(canvas, points, color, width):
    canvas.create_line(
        *points,
        fill=color,
        width=width,
        capstyle=tk.ROUND,
        joinstyle=tk.ROUND,
        smooth=False,
    )


def _draw_folder(canvas, ox, oy, s, color, w):
    _polyline(canvas, [
        ox + 0.06 * s, oy + 0.80 * s,
        ox + 0.06 * s, oy + 0.24 * s,
        ox + 0.36 * s, oy + 0.24 * s,
        ox + 0.45 * s, oy + 0.36 * s,
        ox + 0.94 * s, oy + 0.36 * s,
        ox + 0.94 * s, oy + 0.80 * s,
        ox + 0.06 * s, oy + 0.80 * s,
    ], color, w)


def _draw_refresh(canvas, ox, oy, s, color, w):
    canvas.create_arc(
        ox + 0.12 * s, oy + 0.12 * s, ox + 0.88 * s, oy + 0.88 * s,
        start=60, extent=280, style=tk.ARC, outline=color, width=w,
    )
    _polyline(canvas, [
        ox + 0.72 * s, oy + 0.10 * s,
        ox + 0.90 * s, oy + 0.24 * s,
        ox + 0.70 * s, oy + 0.32 * s,
    ], color, w)


def _draw_gear(canvas, ox, oy, s, color, w):
    canvas.create_oval(
        ox + 0.34 * s, oy + 0.34 * s, ox + 0.66 * s, oy + 0.66 * s,
        outline=color, width=w,
    )
    import math

    for index in range(8):
        angle = math.radians(index * 45)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        _polyline(canvas, [
            ox + (0.5 + 0.30 * cos_a) * s, oy + (0.5 + 0.30 * sin_a) * s,
            ox + (0.5 + 0.44 * cos_a) * s, oy + (0.5 + 0.44 * sin_a) * s,
        ], color, w)


def _draw_play(canvas, ox, oy, s, color, w):
    canvas.create_polygon(
        ox + 0.26 * s, oy + 0.16 * s,
        ox + 0.80 * s, oy + 0.50 * s,
        ox + 0.26 * s, oy + 0.84 * s,
        fill=color, outline=color, width=1,
    )


def _draw_bolt(canvas, ox, oy, s, color, w):
    _polyline(canvas, [
        ox + 0.56 * s, oy + 0.08 * s,
        ox + 0.24 * s, oy + 0.54 * s,
        ox + 0.46 * s, oy + 0.54 * s,
        ox + 0.40 * s, oy + 0.92 * s,
        ox + 0.76 * s, oy + 0.44 * s,
        ox + 0.53 * s, oy + 0.44 * s,
        ox + 0.56 * s, oy + 0.08 * s,
    ], color, w)


def _star_points(ox, oy, s):
    import math

    points = []
    for index in range(10):
        radius = 0.44 if index % 2 == 0 else 0.18
        angle = math.radians(-90 + index * 36)
        points.append(ox + (0.5 + radius * math.cos(angle)) * s)
        points.append(oy + (0.5 + radius * math.sin(angle)) * s)
    return points


def _draw_star(canvas, ox, oy, s, color, w, filled):
    points = _star_points(ox, oy, s)
    if filled:
        canvas.create_polygon(points, fill=color, outline=color, width=1)
    else:
        canvas.create_polygon(points, fill="", outline=color, width=w)


def _draw_chevron_down(canvas, ox, oy, s, color, w):
    _polyline(canvas, [
        ox + 0.26 * s, oy + 0.40 * s,
        ox + 0.50 * s, oy + 0.62 * s,
        ox + 0.74 * s, oy + 0.40 * s,
    ], color, w)


def _draw_chevron_right(canvas, ox, oy, s, color, w):
    _polyline(canvas, [
        ox + 0.40 * s, oy + 0.24 * s,
        ox + 0.62 * s, oy + 0.50 * s,
        ox + 0.40 * s, oy + 0.76 * s,
    ], color, w)


def _draw_clock(canvas, ox, oy, s, color, w):
    canvas.create_oval(
        ox + 0.10 * s, oy + 0.10 * s, ox + 0.90 * s, oy + 0.90 * s,
        outline=color, width=w,
    )
    _polyline(canvas, [
        ox + 0.50 * s, oy + 0.30 * s,
        ox + 0.50 * s, oy + 0.52 * s,
        ox + 0.68 * s, oy + 0.62 * s,
    ], color, w)


def _draw_plus(canvas, ox, oy, s, color, w):
    _polyline(canvas, [ox + 0.50 * s, oy + 0.18 * s, ox + 0.50 * s, oy + 0.82 * s], color, w)
    _polyline(canvas, [ox + 0.18 * s, oy + 0.50 * s, ox + 0.82 * s, oy + 0.50 * s], color, w)


def _draw_open_external(canvas, ox, oy, s, color, w):
    _polyline(canvas, [
        ox + 0.54 * s, oy + 0.14 * s,
        ox + 0.86 * s, oy + 0.14 * s,
        ox + 0.86 * s, oy + 0.46 * s,
    ], color, w)
    _polyline(canvas, [ox + 0.86 * s, oy + 0.14 * s, ox + 0.46 * s, oy + 0.54 * s], color, w)
    _polyline(canvas, [
        ox + 0.72 * s, oy + 0.58 * s,
        ox + 0.72 * s, oy + 0.84 * s,
        ox + 0.16 * s, oy + 0.84 * s,
        ox + 0.16 * s, oy + 0.28 * s,
        ox + 0.42 * s, oy + 0.28 * s,
    ], color, w)


def _draw_close(canvas, ox, oy, s, color, w):
    _polyline(canvas, [ox + 0.26 * s, oy + 0.26 * s, ox + 0.74 * s, oy + 0.74 * s], color, w)
    _polyline(canvas, [ox + 0.74 * s, oy + 0.26 * s, ox + 0.26 * s, oy + 0.74 * s], color, w)


_PAINTERS = {
    "folder": _draw_folder,
    "refresh": _draw_refresh,
    "gear": _draw_gear,
    "play": _draw_play,
    "bolt": _draw_bolt,
    "clock": _draw_clock,
    "plus": _draw_plus,
    "open_external": _draw_open_external,
    "close": _draw_close,
    "chevron_down": _draw_chevron_down,
    "chevron_right": _draw_chevron_right,
}


def draw(canvas, name, color, size, x=0, y=0):
    """在 canvas 的 (x, y) 处绘制边长为 size 的图标。未知名字静默忽略。"""
    width = max(1, round(size / 8))

    if name in ("star", "star_filled"):
        _draw_star(canvas, x, y, size, color, width, name == "star_filled")
        return

    painter = _PAINTERS.get(name)
    if painter:
        painter(canvas, x, y, size, color, width)
