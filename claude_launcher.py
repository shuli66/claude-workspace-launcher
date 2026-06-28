import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import json
import os
import shutil
import sys
from pathlib import Path
import socket
import struct
import winreg

# 可选依赖：系统托盘支持
try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, bg_color, hover_color, text_color, width=200, height=45, icon=None, border_radius=8):
        super().__init__(parent, width=width, height=height, bg=parent['bg'], highlightthickness=0)
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.text = text
        self.icon = icon
        self.border_radius = border_radius

        # 创建圆角矩形
        self.rect = self._create_rounded_rect(0, 0, width, height, border_radius, fill=bg_color)

        if icon:
            self.text_id = self.create_text(width/2, height/2, text=f"{icon}  {text}",
                                           fill=text_color, font=("Segoe UI", 10, "bold"), tags="button")
        else:
            self.text_id = self.create_text(width/2, height/2, text=text,
                                           fill=text_color, font=("Segoe UI", 10, "bold"), tags="button")

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def _create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def on_enter(self, e):
        self.itemconfig(self.rect, fill=self.hover_color)
        self.config(cursor="hand2")

    def on_leave(self, e):
        self.itemconfig(self.rect, fill=self.bg_color)
        self.config(cursor="")

    def on_click(self, e):
        self.command()

class FavoriteItem(tk.Frame):
    def __init__(self, parent, path, on_select, on_delete, colors):
        super().__init__(parent, bg=colors['card_bg'], height=56)
        self.path = path
        self.on_select = on_select
        self.on_delete = on_delete
        self.colors = colors

        self.pack_propagate(False)

        # 左侧内容区域
        content_frame = tk.Frame(self, bg=colors['card_bg'])
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=12)

        # 图标和路径
        icon_label = tk.Label(content_frame, text="📁", font=("Segoe UI", 16),
                             bg=colors['card_bg'], fg=colors['accent'])
        icon_label.pack(side=tk.LEFT, padx=(0, 12))

        # 路径信息
        path_info = tk.Frame(content_frame, bg=colors['card_bg'])
        path_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 项目名称
        project_name = os.path.basename(path) or path
        name_label = tk.Label(path_info, text=project_name, font=("Segoe UI", 10, "bold"),
                             bg=colors['card_bg'], fg=colors['text'], anchor=tk.W)
        name_label.pack(fill=tk.X)

        # 完整路径
        path_label = tk.Label(path_info, text=path, font=("Segoe UI", 8),
                             bg=colors['card_bg'], fg=colors['text_secondary'], anchor=tk.W)
        path_label.pack(fill=tk.X)

        # 右侧按钮区域
        button_frame = tk.Frame(self, bg=colors['card_bg'])
        button_frame.pack(side=tk.RIGHT, padx=12)

        # 打开资源管理器按钮
        open_explorer_btn = tk.Label(button_frame, text="📂", font=("Segoe UI", 12),
                                     bg=colors['card_bg'], fg=colors['text'],
                                     cursor="hand2", padx=8)
        open_explorer_btn.pack(side=tk.LEFT, padx=(0, 8))
        open_explorer_btn.bind("<Enter>", lambda e: open_explorer_btn.config(bg=colors['hover_bg']))
        open_explorer_btn.bind("<Leave>", lambda e: open_explorer_btn.config(bg=colors['card_bg']))
        open_explorer_btn.bind("<Button-1>", lambda e: self.open_in_explorer(path))

        # 启动按钮
        open_btn = tk.Label(button_frame, text="启动", font=("Segoe UI", 9, "bold"),
                           bg=colors['accent'], fg='#ffffff',
                           cursor="hand2", padx=16, pady=6)
        open_btn.pack(side=tk.LEFT, padx=(0, 8))
        open_btn.bind("<Enter>", lambda e: open_btn.config(bg=colors['accent_hover']))
        open_btn.bind("<Leave>", lambda e: open_btn.config(bg=colors['accent']))
        open_btn.bind("<Button-1>", lambda e: self.on_select(path))

        # 删除按钮
        delete_btn = tk.Label(button_frame, text="✕", font=("Segoe UI", 12),
                             bg=colors['card_bg'], fg=colors['text_secondary'],
                             cursor="hand2", width=2)
        delete_btn.pack(side=tk.LEFT)
        delete_btn.bind("<Enter>", lambda e: delete_btn.config(fg=colors['danger'], bg=colors['danger_bg']))
        delete_btn.bind("<Leave>", lambda e: delete_btn.config(fg=colors['text_secondary'], bg=colors['card_bg']))
        delete_btn.bind("<Button-1>", lambda e: self.on_delete(path))

        # 整个区域悬停效果
        for widget in [self, content_frame, icon_label, path_info, name_label, path_label]:
            widget.bind("<Enter>", self.on_hover_enter)
            widget.bind("<Leave>", self.on_hover_leave)

    def open_in_explorer(self, path):
        """在资源管理器中打开目录"""
        try:
            subprocess.Popen(f'explorer "{path}"')
        except Exception as e:
            messagebox.showerror("错误", f"打开失败: {str(e)}")

    def on_hover_enter(self, e):
        self.config(bg=self.colors['hover_bg'])
        for child in self.winfo_children():
            if child.winfo_class() == "Frame":
                child.config(bg=self.colors['hover_bg'])
                for subchild in child.winfo_children():
                    if subchild.winfo_class() in ["Label", "Frame"] and subchild.cget("text") not in ["打开", "✕"]:
                        try:
                            subchild.config(bg=self.colors['hover_bg'])
                        except:
                            pass

    def on_hover_leave(self, e):
        self.config(bg=self.colors['card_bg'])
        for child in self.winfo_children():
            if child.winfo_class() == "Frame":
                child.config(bg=self.colors['card_bg'])
                for subchild in child.winfo_children():
                    if subchild.winfo_class() in ["Label", "Frame"] and subchild.cget("text") not in ["打开", "✕"]:
                        try:
                            subchild.config(bg=self.colors['card_bg'])
                        except:
                            pass

class RecentItem(tk.Frame):
    def __init__(self, parent, path, on_select, on_launch, on_open_explorer, on_toggle_favorite, is_favorite, colors, is_available=True):
        super().__init__(parent, bg=colors['card_bg'], height=52)
        self.path = path
        self.on_select = on_select
        self.on_launch = on_launch
        self.on_open_explorer = on_open_explorer
        self.on_toggle_favorite = on_toggle_favorite
        self.colors = colors
        self.is_favorite = is_favorite
        self.is_available = is_available

        self.pack_propagate(False)

        content_frame = tk.Frame(self, bg=colors['card_bg'])
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=10)

        icon_label = tk.Label(content_frame, text="🕘" if is_available else "⚠",
                             font=("Segoe UI", 14),
                             bg=colors['card_bg'],
                             fg=colors['text_secondary'] if is_available else colors['warning'])
        icon_label.pack(side=tk.LEFT, padx=(0, 12))

        path_info = tk.Frame(content_frame, bg=colors['card_bg'])
        path_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        project_name = os.path.basename(path) or path
        name_label = tk.Label(path_info, text=project_name, font=("Segoe UI", 10, "bold"),
                             bg=colors['card_bg'], fg=colors['text'], anchor=tk.W)
        name_label.pack(fill=tk.X)

        path_label = tk.Label(path_info, text=path, font=("Segoe UI", 8),
                             bg=colors['card_bg'],
                             fg=colors['text_secondary'] if is_available else colors['danger'],
                             anchor=tk.W)
        path_label.pack(fill=tk.X)

        button_frame = tk.Frame(self, bg=colors['card_bg'])
        button_frame.pack(side=tk.RIGHT, padx=12)

        if not is_available:
            status_label = tk.Label(button_frame, text="无效", font=("Segoe UI", 8),
                                    bg=colors['danger_bg'], fg=colors['danger'],
                                    padx=8, pady=3)
            status_label.pack(side=tk.LEFT, padx=(0, 6))

        open_btn = tk.Label(button_frame, text="📂", font=("Segoe UI", 11),
                           bg=colors['card_bg'], fg=colors['text'], cursor="hand2", padx=8)
        open_btn.pack(side=tk.LEFT, padx=(0, 6))
        open_btn.bind("<Enter>", lambda e: open_btn.config(bg=colors['hover_bg']))
        open_btn.bind("<Leave>", lambda e: open_btn.config(bg=colors['card_bg']))
        open_btn.bind("<Button-1>", lambda e: self.on_open_explorer(path))

        favorite_text = "★" if is_favorite else "☆"
        favorite_btn = tk.Label(button_frame, text=favorite_text, font=("Segoe UI", 11),
                               bg=colors['card_bg'], fg=colors['warning'], cursor="hand2", padx=8)
        favorite_btn.pack(side=tk.LEFT, padx=(0, 6))
        favorite_btn.bind("<Enter>", lambda e: favorite_btn.config(bg=colors['hover_bg']))
        favorite_btn.bind("<Leave>", lambda e: favorite_btn.config(bg=colors['card_bg']))
        favorite_btn.bind("<Button-1>", lambda e: self.on_toggle_favorite(path))

        launch_bg = colors['accent'] if is_available else colors['border']
        launch_fg = '#ffffff' if is_available else colors['text_secondary']
        launch_btn = tk.Label(button_frame, text="启动", font=("Segoe UI", 9, "bold"),
                             bg=launch_bg, fg=launch_fg, cursor="hand2", padx=16, pady=6)
        launch_btn.pack(side=tk.LEFT)
        launch_btn.bind("<Enter>", lambda e: launch_btn.config(bg=colors['accent_hover'] if is_available else colors['hover_bg']))
        launch_btn.bind("<Leave>", lambda e: launch_btn.config(bg=launch_bg))
        launch_btn.bind("<Button-1>", lambda e: self.on_launch(path))

        for widget in [self, content_frame, icon_label, path_info, name_label, path_label]:
            widget.bind("<Enter>", self.on_hover_enter)
            widget.bind("<Leave>", self.on_hover_leave)
            widget.bind("<Button-1>", lambda e: self.on_select(path))

    def on_hover_enter(self, e):
        self.config(bg=self.colors['hover_bg'])
        for child in self.winfo_children():
            if child.winfo_class() == "Frame":
                child.config(bg=self.colors['hover_bg'])
                for subchild in child.winfo_children():
                    try:
                        if subchild.cget("text") not in ["📂", "★", "☆", "启动", "无效"]:
                            subchild.config(bg=self.colors['hover_bg'])
                    except:
                        pass

    def on_hover_leave(self, e):
        self.config(bg=self.colors['card_bg'])
        for child in self.winfo_children():
            if child.winfo_class() == "Frame":
                child.config(bg=self.colors['card_bg'])
                for subchild in child.winfo_children():
                    try:
                        if subchild.cget("text") not in ["📂", "★", "☆", "启动", "无效"]:
                            subchild.config(bg=self.colors['card_bg'])
                    except:
                        pass

class FolderGroup(tk.Frame):
    """可折叠的文件夹分组控件，按父目录分组显示子目录"""
    def __init__(self, parent, folder_path, children, on_select, on_launch,
                 on_open_explorer, on_toggle_favorite, favorites, colors):
        super().__init__(parent, bg=colors['bg'])
        self.folder_path = folder_path
        self.children = children
        self.colors = colors
        self.is_expanded = True

        # 分组标题栏
        header = tk.Frame(self, bg=colors['card_bg'], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # 展开/折叠箭头
        self.arrow_label = tk.Label(header, text="▾", font=("Segoe UI", 10),
                                   bg=colors['card_bg'], fg=colors['text_secondary'],
                                   cursor="hand2", padx=4)
        self.arrow_label.pack(side=tk.LEFT, padx=(12, 0))

        # 文件夹图标和名称
        folder_name = os.path.basename(folder_path) or folder_path
        icon_label = tk.Label(header, text="📂", font=("Segoe UI", 12),
                             bg=colors['card_bg'], fg=colors['accent'])
        icon_label.pack(side=tk.LEFT, padx=(4, 8))

        name_label = tk.Label(header, text=folder_name, font=("Segoe UI", 10, "bold"),
                             bg=colors['card_bg'], fg=colors['text'])
        name_label.pack(side=tk.LEFT)

        # 完整路径
        path_label = tk.Label(header, text=folder_path, font=("Segoe UI", 8),
                             bg=colors['card_bg'], fg=colors['text_secondary'])
        path_label.pack(side=tk.LEFT, padx=(8, 0))

        # 子项数量
        count_label = tk.Label(header, text=f"{len(children)} 个项目",
                              font=("Segoe UI", 8),
                              bg=colors['card_bg'], fg=colors['text_secondary'])
        count_label.pack(side=tk.RIGHT, padx=12)

        # 在资源管理器中打开父目录
        open_parent_btn = tk.Label(header, text="📂", font=("Segoe UI", 11),
                                  bg=colors['card_bg'], fg=colors['text'],
                                  cursor="hand2", padx=6)
        open_parent_btn.pack(side=tk.RIGHT, padx=(0, 4))
        open_parent_btn.bind("<Enter>", lambda e: open_parent_btn.config(bg=colors['hover_bg']))
        open_parent_btn.bind("<Leave>", lambda e: open_parent_btn.config(bg=colors['card_bg']))
        open_parent_btn.bind("<Button-1>", lambda e: on_open_explorer(folder_path))

        # 绑定点击事件（折叠/展开）
        for widget in [header, self.arrow_label, icon_label, name_label, path_label]:
            widget.bind("<Button-1>", lambda e: self.toggle_expand())
            widget.bind("<Enter>", lambda e: header.config(bg=colors['hover_bg']))
            widget.bind("<Leave>", lambda e: header.config(bg=colors['card_bg']))

        # 子项容器
        self.children_frame = tk.Frame(self, bg=colors['bg'])
        self.children_frame.pack(fill=tk.X)

        # 渲染子项
        for i, child_path in enumerate(children):
            child_available = os.path.isdir(child_path)
            item = RecentItem(
                self.children_frame,
                child_path,
                on_select,
                on_launch,
                on_open_explorer,
                on_toggle_favorite,
                child_path in favorites,
                colors,
                child_available,
            )
            item.pack(fill=tk.X, pady=(0, 1))

    def toggle_expand(self):
        if self.is_expanded:
            self.children_frame.pack_forget()
            self.arrow_label.config(text="▸")
        else:
            self.children_frame.pack(fill=tk.X, after=self.winfo_children()[0])
            self.arrow_label.config(text="▾")
        self.is_expanded = not self.is_expanded

class SettingsDialog:
    """设置对话框"""
    def __init__(self, parent, launcher):
        self.parent = parent
        self.launcher = launcher
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("设置")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 400) // 2
        self.dialog.geometry(f"500x400+{x}+{y}")

        self.setup_ui()

    def setup_ui(self):
        colors = self.launcher.colors
        self.dialog.configure(bg=colors['bg'])

        # 标题
        header = tk.Frame(self.dialog, bg=colors['card_bg'], height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title_label = tk.Label(header, text="⚙️ 设置",
                              font=("Segoe UI", 14, "bold"),
                              bg=colors['card_bg'], fg=colors['text'])
        title_label.pack(pady=16, padx=20, anchor=tk.W)

        # 内容区域
        content = tk.Frame(self.dialog, bg=colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        # 主题设置
        theme_section = tk.Frame(content, bg=colors['card_bg'])
        theme_section.pack(fill=tk.X, pady=(0, 16))

        theme_inner = tk.Frame(theme_section, bg=colors['card_bg'])
        theme_inner.pack(fill=tk.X, padx=20, pady=20)

        theme_title = tk.Label(theme_inner, text="外观主题",
                              font=("Segoe UI", 11, "bold"),
                              bg=colors['card_bg'], fg=colors['text'])
        theme_title.pack(anchor=tk.W, pady=(0, 12))

        theme_desc = tk.Label(theme_inner, text="选择应用的外观主题",
                             font=("Segoe UI", 9),
                             bg=colors['card_bg'], fg=colors['text_secondary'])
        theme_desc.pack(anchor=tk.W, pady=(0, 16))

        # 主题选项
        theme_buttons_frame = tk.Frame(theme_inner, bg=colors['card_bg'])
        theme_buttons_frame.pack(fill=tk.X)

        themes = [
            ("🌓 跟随系统", "auto", "自动跟随 Windows 系统主题"),
            ("☀️ 浅色模式", "light", "使用浅色主题"),
            ("🌙 深色模式", "dark", "使用深色主题")
        ]

        for text, theme_id, desc in themes:
            is_active = self.launcher.current_theme == theme_id

            theme_option = tk.Frame(theme_buttons_frame, bg=colors['card_bg'])
            theme_option.pack(fill=tk.X, pady=(0, 8))

            # 单选按钮样式
            radio_frame = tk.Frame(theme_option, bg=colors['card_bg'])
            radio_frame.pack(side=tk.LEFT, fill=tk.Y)

            radio_indicator = tk.Label(radio_frame,
                                      text="●" if is_active else "○",
                                      font=("Segoe UI", 14),
                                      bg=colors['card_bg'],
                                      fg=colors['accent'] if is_active else colors['text_secondary'],
                                      cursor="hand2")
            radio_indicator.pack(padx=(0, 12))

            # 文本区域
            text_frame = tk.Frame(theme_option, bg=colors['card_bg'])
            text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            theme_label = tk.Label(text_frame, text=text,
                                  font=("Segoe UI", 10, "bold" if is_active else "normal"),
                                  bg=colors['card_bg'],
                                  fg=colors['text'],
                                  cursor="hand2")
            theme_label.pack(anchor=tk.W)

            theme_desc_label = tk.Label(text_frame, text=desc,
                                       font=("Segoe UI", 8),
                                       bg=colors['card_bg'],
                                       fg=colors['text_secondary'])
            theme_desc_label.pack(anchor=tk.W)

            # 绑定点击事件
            for widget in [theme_option, radio_indicator, text_frame, theme_label, theme_desc_label]:
                widget.bind("<Button-1>", lambda e, t=theme_id: self.change_theme(t))

        # 启动选项
        launch_section = tk.Frame(content, bg=colors['card_bg'])
        launch_section.pack(fill=tk.X, pady=(0, 16))

        launch_inner = tk.Frame(launch_section, bg=colors['card_bg'])
        launch_inner.pack(fill=tk.X, padx=20, pady=20)

        launch_title = tk.Label(launch_inner, text="启动选项",
                               font=("Segoe UI", 11, "bold"),
                               bg=colors['card_bg'], fg=colors['text'])
        launch_title.pack(anchor=tk.W, pady=(0, 12))

        # 自动关闭选项
        auto_close_var = tk.BooleanVar(value=self.launcher.config.get("auto_close", True))

        style = ttk.Style()
        style.configure('Settings.TCheckbutton',
                       background=colors['card_bg'],
                       foreground=colors['text'],
                       font=("Segoe UI", 10))

        auto_close_check = ttk.Checkbutton(launch_inner,
                                          text="启动 Claude Code 后自动关闭启动器",
                                          variable=auto_close_var,
                                          style='Settings.TCheckbutton',
                                          command=lambda: self.save_auto_close(auto_close_var.get()))
        auto_close_check.pack(anchor=tk.W)

        # 底部按钮
        footer = tk.Frame(self.dialog, bg=colors['bg'], height=60)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)

        button_frame = tk.Frame(footer, bg=colors['bg'])
        button_frame.pack(pady=12, padx=24)

        # 退出程序按钮
        quit_btn = ModernButton(button_frame, "退出程序", self.quit_app,
                               colors['danger'], '#c2410c',
                               '#ffffff', width=120, height=40)
        quit_btn.pack(side=tk.LEFT, padx=(0, 8))

        # 关闭按钮
        close_btn = ModernButton(button_frame, "关闭", self.dialog.destroy,
                                colors['accent'], colors['accent_hover'],
                                '#ffffff', width=120, height=40)
        close_btn.pack(side=tk.LEFT)

    def change_theme(self, theme):
        """切换主题"""
        self.launcher.switch_theme(theme)
        self.dialog.destroy()

    def save_auto_close(self, value):
        """保存自动关闭设置"""
        self.launcher.config["auto_close"] = value
        self.launcher.save_config()

    def quit_app(self):
        """退出程序"""
        self.dialog.destroy()
        self.launcher.quit_app()

AGENT_CONFIGS = {
    "claude": {
        "name": "Claude Code",
        "icon": "⚡",
        "commands": ["claude", "claude.exe", "claude.cmd"],
        "modes": {
            "normal": {"label": "普通启动", "desc": "标准权限确认流程", "args": []},
            "skip": {"label": "跳过权限启动", "desc": "快速启动，跳过权限提示", "args": ["--dangerously-skip-permissions"]},
        },
        "resume_args": ["--resume"],
        "default_mode": "normal",
        "env_key": None,
        "session_dir": os.path.join(Path.home(), ".claude", "projects"),
        "session_pattern": "*.jsonl",
    },
    "codex": {
        "name": "Codex CLI",
        "icon": "🤖",
        "commands": ["codex", "codex.exe"],
        "modes": {
            "normal": {"label": "沙箱启动", "desc": "标准沙箱模式（推荐日常使用）", "args": ["--sandbox", "workspace-write"]},
            "yolo": {"label": "YOLO 模式", "desc": "跳过所有审批和沙箱（仅限隔离环境）", "args": ["--dangerously-bypass-approvals-and-sandbox"]},
        },
        "resume_args": ["resume"],
        "default_mode": "normal",
        "env_key": "OPENAI_API_KEY",
        "session_dir": os.path.join(Path.home(), ".codex", "sessions"),
        "session_pattern": "rollout-*.jsonl",
    },
    "mimo": {
        "name": "MiMo Code",
        "icon": "🧠",
        "commands": ["mimo", "mimo.exe", "mimo.cmd"],
        "modes": {
            "interactive": {"label": "交互模式", "desc": "启动 TUI 交互界面（推荐）", "args": []},
            "run": {"label": "单次执行", "desc": "执行单个任务后退出（适合脚本/CI）", "args": ["run"]},
        },
        "resume_args": ["--continue"],
        "default_mode": "interactive",
        "env_key": "MIMO_API_KEY",
        "session_dir": os.path.join(Path.home(), ".local", "share", "mimocode"),
        "session_pattern": "mimocode.db",
    },
}


class ClaudeLauncher:
    def __init__(self, root, lock_socket=None):
        self.root = root
        self.lock_socket = lock_socket
        self.root.title("AI Coding Launcher")
        self.root.geometry("700x820")
        self.root.resizable(False, False)

        self.config_file = Path.home() / ".claude_launcher_config.json"
        self.config_warning = None
        self.load_config()
        self.current_agent = self.config.get("agent", "claude")
        if self.current_agent not in AGENT_CONFIGS:
            self.current_agent = "claude"
        self.last_mode = self.config.get("last_mode", AGENT_CONFIGS[self.current_agent]["default_mode"])

        # 初始化主题
        self.current_theme = self.config.get("theme", "auto")
        self.setup_theme()

        self.root.configure(bg=self.colors['bg'])

        # 设置窗口图标
        self.icon_path = Path(__file__).parent / "claude_icon.ico"
        if self.icon_path.exists():
            try:
                self.root.iconbitmap(str(self.icon_path))
            except:
                pass

        # 系统托盘
        self.tray_icon = None
        self.setup_tray()

        self.validation_job = None
        self.path_status = None

        self.setup_ui()

        # 绑定快捷键
        self.root.bind('<Return>', lambda e: self.launch_agent())
        self.root.bind('<Escape>', lambda e: self.minimize_to_tray())
        self.root.bind('<Control-o>', lambda e: self.browse_directory())

    def get_system_theme(self):
        """检测 Windows 系统主题"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
        except:
            return "dark"

    def setup_theme(self):
        """设置主题配色"""
        if self.current_theme == "auto":
            theme = self.get_system_theme()
        else:
            theme = self.current_theme

        if theme == "light":
            self.colors = {
                'bg': '#f3f3f3',
                'card_bg': '#ffffff',
                'hover_bg': '#e8e8e8',
                'accent': '#0078d4',
                'accent_hover': '#106ebe',
                'text': '#1f1f1f',
                'text_secondary': '#616161',
                'border': '#d1d1d1',
                'input_bg': '#ffffff',
                'input_border': '#8a8a8a',
                'success': '#107c10',
                'danger': '#d13438',
                'danger_bg': '#fde7e9',
                'warning': '#ca5010'
            }
        else:
            self.colors = {
                'bg': '#1e1e1e',
                'card_bg': '#252526',
                'hover_bg': '#2a2d2e',
                'accent': '#007acc',
                'accent_hover': '#1e8ad6',
                'text': '#cccccc',
                'text_secondary': '#858585',
                'border': '#3e3e42',
                'input_bg': '#3c3c3c',
                'input_border': '#555555',
                'success': '#4ec9b0',
                'danger': '#f48771',
                'danger_bg': '#5a1d1d',
                'warning': '#dcdcaa'
            }

    def switch_theme(self, theme):
        """切换主题"""
        self.current_theme = theme
        self.config["theme"] = theme
        self.save_config()
        self.setup_theme()
        self.rebuild_ui()

    def setup_tray(self):
        """设置系统托盘"""
        if not TRAY_AVAILABLE:
            self.tray_icon = None
            return

        def create_tray_image():
            # 创建托盘图标
            width = 64
            height = 64
            image = Image.new('RGB', (width, height), color='#007acc')
            dc = ImageDraw.Draw(image)
            dc.ellipse([16, 16, 48, 48], fill='#ffffff')
            return image

        def on_show(icon, item):
            self.root.after(0, self.show_window)

        def on_settings(icon, item):
            self.root.after(0, self.show_and_open_settings)

        def on_quit(icon, item):
            self.root.after(0, self.quit_app)

        menu = Menu(
            MenuItem('显示窗口', on_show, default=True),
            MenuItem('设置', on_settings),
            Menu.SEPARATOR,
            MenuItem('退出程序', on_quit)
        )

        self.tray_icon = Icon("Claude Launcher", create_tray_image(), "Claude Launcher", menu)

    def minimize_to_tray(self):
        """最小化到系统托盘"""
        if not TRAY_AVAILABLE or not self.tray_icon:
            # 如果没有托盘支持，直接最小化窗口
            self.root.iconify()
            return

        self.root.withdraw()
        if not self.tray_icon.visible:
            import threading
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self):
        """从托盘恢复窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def show_and_open_settings(self):
        """显示窗口并打开设置"""
        self.show_window()
        self.open_settings()

    def quit_app(self):
        """退出应用"""
        if self.tray_icon:
            self.tray_icon.stop()
        if self.lock_socket:
            self.lock_socket.close()
        self.root.quit()
        sys.exit(0)

    def load_config(self):
        default_config = {
            "recent_dirs": [],
            "favorites": [],
            "agent": "claude",
            "last_mode": "normal",
            "auto_close": True,
            "theme": "auto"
        }

        self.config = default_config.copy()

        if not self.config_file.exists():
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
        except (OSError, json.JSONDecodeError):
            self.config_warning = "配置文件无法读取，已使用默认设置"
            return

        if not isinstance(loaded_config, dict):
            self.config_warning = "配置文件格式无效，已使用默认设置"
            return

        self.config.update(loaded_config)
        self.config["recent_dirs"] = self.normalize_path_list(self.config.get("recent_dirs", []))
        self.config["favorites"] = self.normalize_path_list(self.config.get("favorites", []))

        if self.config.get("agent") not in AGENT_CONFIGS:
            self.config["agent"] = "claude"
        if self.config.get("last_mode") not in AGENT_CONFIGS.get(self.config.get("agent", "claude"), {}).get("modes", {}):
            self.config["last_mode"] = AGENT_CONFIGS[self.config["agent"]]["default_mode"]
        if self.config.get("theme") not in ("auto", "light", "dark"):
            self.config["theme"] = "auto"
        if not isinstance(self.config.get("auto_close"), bool):
            self.config["auto_close"] = True

    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def normalize_path(self, path):
        """清理用户粘贴的目录路径，兼容 Windows 的“复制为路径”格式。"""
        if not path:
            return ""

        normalized = str(path).strip()
        if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in ("'", '"'):
            normalized = normalized[1:-1].strip()

        normalized = os.path.expandvars(os.path.expanduser(normalized))
        if not normalized:
            return ""

        return os.path.normpath(normalized)

    def normalize_path_list(self, paths):
        if not isinstance(paths, list):
            return []

        normalized_paths = []
        for path in paths:
            normalized = self.normalize_path(path)
            if normalized and normalized not in normalized_paths:
                normalized_paths.append(normalized)

        return normalized_paths[:10]

    def is_valid_directory(self, path):
        return bool(path) and os.path.isdir(self.normalize_path(path))

    def first_available_directory(self, paths):
        for path in paths:
            normalized = self.normalize_path(path)
            if os.path.isdir(normalized):
                return normalized
        return ""

    def scan_agent_sessions(self, agent=None):
        """扫描指定 agent 的会话目录，返回按项目分组的会话列表"""
        agent = agent or self.current_agent
        config = AGENT_CONFIGS[agent]
        session_dir = config.get("session_dir", "")
        if not session_dir or not os.path.isdir(session_dir):
            return []

        if agent == "claude":
            return self._scan_claude_sessions(session_dir)
        elif agent == "codex":
            return self._scan_codex_sessions(session_dir)
        elif agent == "mimo":
            return self._scan_mimo_sessions(session_dir)
        return []

    def _scan_claude_sessions(self, session_dir):
        """扫描 Claude Code 会话：~/.claude/projects/<project>/<session>.jsonl"""
        from collections import OrderedDict
        import glob as globmod

        groups = OrderedDict()
        if not os.path.isdir(session_dir):
            return list(groups.items())

        for project_dir in os.listdir(session_dir):
            project_path = os.path.join(session_dir, project_dir)
            if not os.path.isdir(project_path):
                continue

            session_files = globmod.glob(os.path.join(project_path, "*.jsonl"))
            if not session_files:
                continue

            sessions = []
            for sf in sorted(session_files, key=os.path.getmtime, reverse=True)[:5]:
                session_id = os.path.splitext(os.path.basename(sf))[0]
                mtime = os.path.getmtime(sf)
                # 从 JSONL 读取真实 cwd 路径
                real_cwd = self._extract_cwd_from_claude_jsonl(sf)
                if not real_cwd or not os.path.isdir(real_cwd):
                    continue
                prompt = self._extract_first_prompt_claude(sf)
                sessions.append({
                    "id": session_id,
                    "file": sf,
                    "mtime": mtime,
                    "size": os.path.getsize(sf),
                    "prompt": prompt,
                    "cwd": real_cwd,
                })

            # 使用真实路径作为分组键（取第一个会话的 cwd）
            if sessions:
                real_path = sessions[0].get("cwd", project_dir)
                if real_path not in groups:
                    groups[real_path] = []
                groups[real_path].extend(sessions)

        return list(groups.items())

    def _extract_cwd_from_claude_jsonl(self, jsonl_file):
        """从 Claude Code JSONL 文件提取 cwd 字段"""
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if "cwd" in obj:
                            return obj["cwd"]
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return ""

    def _extract_first_prompt_claude(self, jsonl_file):
        """从 Claude Code JSONL 文件提取第一个用户消息"""
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if obj.get("type") == "user":
                            msg = obj.get("message", {})
                            content = msg.get("content", "")
                            if isinstance(content, str) and content:
                                return content[:80]
                            elif isinstance(content, list):
                                for block in content:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        text = block.get("text", "")
                                        if text:
                                            return text[:80]
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return ""

    def _scan_codex_sessions(self, session_dir):
        """扫描 Codex CLI 会话：~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl"""
        from collections import OrderedDict
        import glob as globmod

        groups = OrderedDict()
        if not os.path.isdir(session_dir):
            return list(groups.items())

        all_sessions = []
        for date_dir in sorted(os.listdir(session_dir), reverse=True)[:30]:
            date_path = os.path.join(session_dir, date_dir)
            if not os.path.isdir(date_path):
                continue

            for month_dir in os.listdir(date_path):
                month_path = os.path.join(date_path, month_dir)
                if not os.path.isdir(month_path):
                    continue

                for day_dir in os.listdir(month_path):
                    day_path = os.path.join(month_path, day_dir)
                    if not os.path.isdir(day_path):
                        continue

                    rollout_files = globmod.glob(os.path.join(day_path, "rollout-*.jsonl"))
                    for rf in sorted(rollout_files, key=os.path.getmtime, reverse=True):
                        session_id = os.path.splitext(os.path.basename(rf))[0]
                        mtime = os.path.getmtime(rf)
                        date_str = f"{date_dir}/{month_dir}/{day_dir}"
                        # 从 rollout 文件提取 cwd
                        real_cwd = self._extract_cwd_from_codex_rollout(rf)
                        prompt = self._extract_first_prompt_codex(rf)
                        all_sessions.append({
                            "id": session_id,
                            "file": rf,
                            "mtime": mtime,
                            "date": date_str,
                            "size": os.path.getsize(rf),
                            "prompt": prompt,
                            "cwd": real_cwd or "",
                        })

        # 按日期分组，过滤无 cwd 的会话
        for session in all_sessions[:20]:
            date_str = session.get("date", "未知日期")
            if date_str not in groups:
                groups[date_str] = []
            groups[date_str].append(session)

        return list(groups.items())

    def _extract_cwd_from_codex_rollout(self, jsonl_file):
        """从 Codex rollout JSONL 提取 cwd"""
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        # 尝试多种可能的字段
                        for key in ["cwd", "working_directory", "workdir", "directory"]:
                            if key in obj:
                                return obj[key]
                        # 检查 payload 中的 cwd
                        payload = obj.get("payload", {})
                        if isinstance(payload, dict):
                            for key in ["cwd", "working_directory", "workdir", "directory"]:
                                if key in payload:
                                    return payload[key]
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return ""

    def _extract_first_prompt_codex(self, jsonl_file):
        """从 Codex CLI rollout JSONL 提取第一个用户消息"""
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        # Codex rollout 格式可能有不同结构
                        role = obj.get("role", "")
                        if role == "user":
                            content = obj.get("content", obj.get("message", ""))
                            if isinstance(content, str) and content:
                                return content[:80]
                            elif isinstance(content, list):
                                for block in content:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        text = block.get("text", "")
                                        if text:
                                            return text[:80]
                        # 尝试其他可能的字段
                        prompt = obj.get("prompt", obj.get("input", ""))
                        if isinstance(prompt, str) and prompt:
                            return prompt[:80]
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return ""

    def _scan_mimo_sessions(self, session_dir):
        """扫描 MiMo Code 会话：从 ~/.local/share/mimocode/mimocode.db 读取"""
        from collections import OrderedDict

        groups = OrderedDict()
        db_file = os.path.join(session_dir, "mimocode.db")

        if not os.path.isfile(db_file):
            return list(groups.items())

        try:
            import sqlite3
            conn = sqlite3.connect(db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询会话表，关联项目表获取工作目录
            cursor.execute("""
                SELECT
                    s.id,
                    s.directory,
                    s.title,
                    s.time_created,
                    s.time_updated,
                    p.worktree
                FROM session s
                LEFT JOIN project p ON s.project_id = p.id
                ORDER BY s.time_updated DESC
                LIMIT 30
            """)

            rows = cursor.fetchall()
            for row in rows:
                # 优先使用 session 的 directory，否则用 project 的 worktree
                cwd = row["directory"] or row["worktree"] or ""
                if not cwd or not os.path.isdir(cwd):
                    continue

                session_id = row["id"] or "unknown"
                title = row["title"] or ""
                time_created = row["time_created"] or 0

                # 将时间戳转换为可读格式
                created_str = ""
                if time_created:
                    from datetime import datetime
                    try:
                        # MiMo 使用毫秒时间戳
                        dt = datetime.fromtimestamp(time_created / 1000 if time_created > 1e12 else time_created)
                        created_str = dt.strftime("%m-%d %H:%M")
                    except (ValueError, OSError):
                        pass

                # 处理标题编码问题（尝试修复乱码）
                if title:
                    try:
                        # 尝试用不同编码解码
                        title = title.encode('latin1').decode('utf-8', errors='replace')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        pass

                if cwd not in groups:
                    groups[cwd] = []
                groups[cwd].append({
                    "id": session_id[:12],
                    "cwd": cwd,
                    "title": title[:50] if title else "",
                    "created": created_str,
                    "prompt": title[:50] if title else "",
                })

            conn.close()
        except Exception:
            pass

        return list(groups.items())

    def resolve_agent_command(self, agent=None):
        agent = agent or self.current_agent
        config = AGENT_CONFIGS[agent]
        for cmd in config["commands"]:
            found = shutil.which(cmd)
            if found:
                return found
        return None

    def build_agent_command(self, mode, agent=None):
        agent = agent or self.current_agent
        config = AGENT_CONFIGS[agent]
        cmd_path = self.resolve_agent_command(agent)
        if not cmd_path:
            return None

        if mode not in config["modes"]:
            return None

        if cmd_path.lower().endswith((".cmd", ".bat")):
            cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", cmd_path]
        else:
            cmd = [cmd_path]

        mode_args = config["modes"][mode]["args"]
        cmd.extend(mode_args)

        return cmd

    def setup_ui(self):
        # 主容器
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部标题栏
        header = tk.Frame(main_frame, bg=self.colors['card_bg'], height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        header_content = tk.Frame(header, bg=self.colors['card_bg'])
        header_content.pack(expand=True)

        # Logo 和标题
        agent_config = AGENT_CONFIGS[self.current_agent]
        logo_label = tk.Label(header_content, text=agent_config["icon"], font=("Segoe UI", 24),
                             bg=self.colors['card_bg'], fg=self.colors['accent'])
        logo_label.pack(side=tk.LEFT, padx=(0, 12))

        title_frame = tk.Frame(header_content, bg=self.colors['card_bg'])
        title_frame.pack(side=tk.LEFT)

        title_label = tk.Label(title_frame, text=agent_config["name"],
                              font=("Segoe UI", 16, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['text'])
        title_label.pack(anchor=tk.W)

        subtitle_label = tk.Label(title_frame, text="快速启动开发环境",
                                 font=("Segoe UI", 9),
                                 bg=self.colors['card_bg'], fg=self.colors['text_secondary'])
        subtitle_label.pack(anchor=tk.W)

        # 设置按钮（右上角）
        settings_btn = tk.Label(header_content, text="⚙️",
                               font=("Segoe UI", 20),
                               bg=self.colors['card_bg'],
                               fg=self.colors['text_secondary'],
                               cursor="hand2",
                               padx=12)
        settings_btn.pack(side=tk.RIGHT)
        settings_btn.bind("<Enter>", lambda e: settings_btn.config(fg=self.colors['accent']))
        settings_btn.bind("<Leave>", lambda e: settings_btn.config(fg=self.colors['text_secondary']))
        settings_btn.bind("<Button-1>", lambda e: self.open_settings())

        # Agent 选择器
        agent_bar = tk.Frame(main_frame, bg=self.colors['card_bg'], height=44)
        agent_bar.pack(fill=tk.X)
        agent_bar.pack_propagate(False)

        agent_inner = tk.Frame(agent_bar, bg=self.colors['card_bg'])
        agent_inner.pack(expand=True, padx=16)

        agent_label = tk.Label(agent_inner, text="工具:",
                              font=("Segoe UI", 9),
                              bg=self.colors['card_bg'], fg=self.colors['text_secondary'])
        agent_label.pack(side=tk.LEFT, padx=(0, 8))

        self.agent_buttons = {}
        for agent_id, cfg in AGENT_CONFIGS.items():
            is_active = (agent_id == self.current_agent)
            btn_bg = self.colors['accent'] if is_active else self.colors['border']
            btn_fg = '#ffffff' if is_active else self.colors['text']

            btn = tk.Label(agent_inner, text=f" {cfg['icon']} {cfg['name']} ",
                          font=("Segoe UI", 9, "bold" if is_active else "normal"),
                          bg=btn_bg, fg=btn_fg, cursor="hand2", padx=10, pady=4)
            btn.pack(side=tk.LEFT, padx=(0, 6))
            btn.bind("<Button-1>", lambda e, a=agent_id: self.switch_agent(a))

            # 检测可用状态
            available = self.resolve_agent_command(agent_id) is not None
            if not available:
                btn.config(fg=self.colors['danger'] if not is_active else btn_fg)

            self.agent_buttons[agent_id] = btn

        # 状态栏（移到顶部标题栏下方）
        initial_status = self.config_warning or "准备就绪"
        if not self.config_warning and not self.resolve_agent_command():
            env_key = AGENT_CONFIGS[self.current_agent].get("env_key")
            hint = f"，并确认 {env_key} 已设置" if env_key else ""
            initial_status = f"未找到 {AGENT_CONFIGS[self.current_agent]['name']} 命令，请先安装{hint}"
        self.status_var = tk.StringVar(value=initial_status)
        status_bar = tk.Frame(main_frame, bg=self.colors['card_bg'], height=28)
        status_bar.pack(fill=tk.X)
        status_bar.pack_propagate(False)

        status_label = tk.Label(status_bar, textvariable=self.status_var,
                               font=("Segoe UI", 8), bg=self.colors['card_bg'],
                               fg=self.colors['text_secondary'], anchor=tk.W)
        status_label.pack(fill=tk.BOTH, padx=12)
        self.status_label = status_label

        # 可滚动内容区域
        scroll_container = tk.Frame(main_frame, bg=self.colors['bg'])
        scroll_container.pack(fill=tk.BOTH, expand=True)

        # 创建 Canvas 和 Scrollbar
        canvas = tk.Canvas(scroll_container, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)

        # 创建可滚动的 Frame
        content = tk.Frame(canvas, bg=self.colors['bg'])

        # 配置 Canvas
        canvas.configure(yscrollcommand=scrollbar.set)

        # 布局
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 将 content frame 添加到 canvas
        canvas_frame = canvas.create_window((0, 0), window=content, anchor="nw")

        # 绑定配置事件以更新滚动区域
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_frame, width=event.width)

        content.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        # 鼠标滚轮支持
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # 添加内边距
        content_inner = tk.Frame(content, bg=self.colors['bg'])
        content_inner.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        # 当前目录卡片
        current_section = tk.Frame(content_inner, bg=self.colors['card_bg'])
        current_section.pack(fill=tk.X, pady=(0, 16))

        current_inner = tk.Frame(current_section, bg=self.colors['card_bg'])
        current_inner.pack(fill=tk.X, padx=16, pady=14)

        current_title = tk.Label(current_inner, text="当前目录",
                                font=("Segoe UI", 10, "bold"),
                                bg=self.colors['card_bg'], fg=self.colors['text'])
        current_title.pack(anchor=tk.W, pady=(0, 10))

        self.current_name_label = tk.Label(current_inner, text="未选择目录",
                                          font=("Segoe UI", 10, "bold"),
                                          bg=self.colors['card_bg'], fg=self.colors['text'], anchor=tk.W)
        self.current_name_label.pack(fill=tk.X)

        self.current_path_label = tk.Label(current_inner, text="等待输入路径",
                                          font=("Segoe UI", 8),
                                          bg=self.colors['card_bg'], fg=self.colors['text_secondary'], anchor=tk.W)
        self.current_path_label.pack(fill=tk.X, pady=(2, 8))

        current_meta = tk.Frame(current_inner, bg=self.colors['card_bg'])
        current_meta.pack(fill=tk.X)

        self.current_status_chip = tk.Label(current_meta, text="未输入",
                                           font=("Segoe UI", 8), padx=8, pady=3,
                                           bg=self.colors['border'], fg=self.colors['text_secondary'])
        self.current_status_chip.pack(side=tk.LEFT, padx=(0, 8))

        self.current_mode_chip = tk.Label(current_meta, text="",
                                          font=("Segoe UI", 8), padx=8, pady=3,
                                          bg=self.colors['border'], fg=self.colors['text_secondary'])
        self.current_mode_chip.pack(side=tk.LEFT)

        current_actions = tk.Frame(current_inner, bg=self.colors['card_bg'])
        current_actions.pack(fill=tk.X, pady=(12, 0))

        # 根据当前 agent 动态生成启动按钮
        self.launch_buttons_frame = current_actions
        self.rebuild_launch_buttons()

        current_icon_actions = tk.Frame(current_actions, bg=self.colors['card_bg'])
        current_icon_actions.pack(side=tk.RIGHT)

        self.current_explorer_btn = tk.Label(current_icon_actions, text="📂",
                                            font=("Segoe UI", 11), bg=self.colors['border'],
                                            fg=self.colors['text'], cursor="hand2", padx=10, pady=8)
        self.current_explorer_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.current_explorer_btn.bind("<Enter>", lambda e: self.current_explorer_btn.config(bg=self.colors['hover_bg']))
        self.current_explorer_btn.bind("<Leave>", lambda e: self.current_explorer_btn.config(bg=self.colors['border']))
        self.current_explorer_btn.bind("<Button-1>", lambda e: self.open_in_explorer())

        self.current_favorite_btn = tk.Label(current_icon_actions, text="☆",
                                            font=("Segoe UI", 11), bg=self.colors['border'],
                                            fg=self.colors['warning'], cursor="hand2", padx=10, pady=8)
        self.current_favorite_btn.pack(side=tk.LEFT)
        self.current_favorite_btn.bind("<Enter>", lambda e: self.current_favorite_btn.config(bg=self.colors['hover_bg']))
        self.current_favorite_btn.bind("<Leave>", lambda e: self.current_favorite_btn.config(bg=self.colors['border']))
        self.current_favorite_btn.bind("<Button-1>", lambda e: self.toggle_favorite(self.dir_var.get().strip()))

        # 工作目录选择
        dir_section = tk.Frame(content_inner, bg=self.colors['bg'])
        dir_section.pack(fill=tk.X, pady=(0, 16))

        dir_label = tk.Label(dir_section, text="工作目录",
                            font=("Segoe UI", 10, "bold"),
                            bg=self.colors['bg'], fg=self.colors['text'])
        dir_label.pack(anchor=tk.W, pady=(0, 8))

        # 输入框和按钮容器
        dir_input_container = tk.Frame(dir_section, bg=self.colors['input_bg'], height=44)
        dir_input_container.pack(fill=tk.X)
        dir_input_container.pack_propagate(False)

        # 输入框
        input_frame = tk.Frame(dir_input_container, bg=self.colors['input_bg'])
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 8), pady=8)

        self.dir_var = tk.StringVar()
        self.dir_var.trace_add("write", self.on_path_change)
        dir_entry = tk.Entry(input_frame, textvariable=self.dir_var,
                            font=("Segoe UI", 10),
                            bg=self.colors['input_bg'],
                            fg=self.colors['text'],
                            insertbackground=self.colors['text'],
                            relief=tk.FLAT,
                            bd=0)
        dir_entry.pack(fill=tk.BOTH, expand=True)

        self.path_status_label = tk.Label(dir_input_container, text="未输入",
                                         font=("Segoe UI", 8),
                                         bg=self.colors['input_bg'], fg=self.colors['text_secondary'],
                                         padx=6)
        self.path_status_label.pack(side=tk.RIGHT, padx=(0, 4))

        # 设置初始值：只自动选中本机真实存在的目录
        initial_dir = self.first_available_directory(self.config.get("recent_dirs", []))
        if initial_dir:
            self.dir_var.set(initial_dir)
        elif self.config.get("recent_dirs"):
            self.set_status("最近目录不在这台电脑上，请点击浏览选择本机目录", "warning")

        # 按钮容器
        button_container = tk.Frame(dir_input_container, bg=self.colors['input_bg'])
        button_container.pack(side=tk.RIGHT, padx=8, pady=6)

        # 浏览按钮
        browse_btn = tk.Label(button_container, text="浏览",
                             font=("Segoe UI", 9),
                             bg=self.colors['border'],
                             fg=self.colors['text'],
                             cursor="hand2",
                             padx=16, pady=6)
        browse_btn.pack(side=tk.LEFT, padx=(0, 6))
        browse_btn.bind("<Enter>", lambda e: browse_btn.config(bg=self.colors['hover_bg']))
        browse_btn.bind("<Leave>", lambda e: browse_btn.config(bg=self.colors['border']))
        browse_btn.bind("<Button-1>", lambda e: self.browse_directory())

        # 打开资源管理器按钮
        open_btn = tk.Label(button_container, text="📂",
                           font=("Segoe UI", 11),
                           bg=self.colors['border'],
                           fg=self.colors['text'],
                           cursor="hand2",
                           padx=10, pady=6)
        open_btn.pack(side=tk.LEFT)
        open_btn.bind("<Enter>", lambda e: open_btn.config(bg=self.colors['hover_bg']))
        open_btn.bind("<Leave>", lambda e: open_btn.config(bg=self.colors['border']))
        open_btn.bind("<Button-1>", lambda e: self.open_in_explorer())

        # Agent 会话列表（从实际会话目录读取）
        agent_config = AGENT_CONFIGS[self.current_agent]
        session_groups = self.scan_agent_sessions()

        if session_groups:
            session_section = tk.Frame(content_inner, bg=self.colors['bg'])
            session_section.pack(fill=tk.X, pady=(0, 16))

            session_header = tk.Frame(session_section, bg=self.colors['bg'])
            session_header.pack(fill=tk.X, pady=(0, 8))

            session_label = tk.Label(session_header,
                                    text=f"{agent_config['name']} 会话",
                                    font=("Segoe UI", 10, "bold"),
                                    bg=self.colors['bg'], fg=self.colors['text'])
            session_label.pack(side=tk.LEFT)

            total_sessions = sum(len(sessions) for _, sessions in session_groups)
            session_count = tk.Label(session_header,
                                    text=f"{len(session_groups)} 个项目, {total_sessions} 个会话",
                                    font=("Segoe UI", 9),
                                    bg=self.colors['bg'], fg=self.colors['text_secondary'])
            session_count.pack(side=tk.LEFT, padx=(8, 0))

            session_container = tk.Frame(session_section, bg=self.colors['bg'])
            session_container.pack(fill=tk.X)

            for group_key, sessions in session_groups[:5]:
                self._create_session_group(session_container, group_key, sessions)

        # 收藏夹
        if self.config.get("favorites"):
            fav_section = tk.Frame(content_inner, bg=self.colors['bg'])
            fav_section.pack(fill=tk.X, pady=(0, 16))

            fav_header = tk.Frame(fav_section, bg=self.colors['bg'])
            fav_header.pack(fill=tk.X, pady=(0, 8))

            fav_label = tk.Label(fav_header, text="收藏夹",
                                font=("Segoe UI", 10, "bold"),
                                bg=self.colors['bg'], fg=self.colors['text'])
            fav_label.pack(side=tk.LEFT)

            fav_count = tk.Label(fav_header, text=f"{len(self.config['favorites'])} 项",
                                font=("Segoe UI", 9),
                                bg=self.colors['bg'], fg=self.colors['text_secondary'])
            fav_count.pack(side=tk.LEFT, padx=(8, 0))

            fav_container = tk.Frame(fav_section, bg=self.colors['bg'])
            fav_container.pack(fill=tk.X)

            for i, fav_path in enumerate(self.config.get("favorites", [])[:5]):
                fav_available = os.path.isdir(fav_path)
                fav_item = RecentItem(
                    fav_container,
                    fav_path,
                    self.select_recent,
                    self.launch_from_path,
                    self.open_path_in_explorer,
                    self.toggle_favorite,
                    True,
                    self.colors,
                    fav_available,
                )
                fav_item.pack(fill=tk.X, pady=(0, 2) if i < 4 else 0)

        # 初始化 last_mode 和 auto_close_var
        self.last_mode = self.config.get("last_mode", AGENT_CONFIGS[self.current_agent]["default_mode"])
        self.auto_close_var = tk.BooleanVar(value=self.config.get("auto_close", True))

        # 底部操作栏
        footer = tk.Frame(content_inner, bg=self.colors['bg'])
        footer.pack(fill=tk.X, pady=(16, 0))

        # 次要操作按钮
        secondary_actions = tk.Frame(footer, bg=self.colors['bg'])
        secondary_actions.pack(fill=tk.X)

        add_fav_btn = ModernButton(secondary_actions, "添加到收藏夹", self.add_to_favorites,
                                   self.colors['border'], self.colors['hover_bg'],
                                   self.colors['text'], width=200, height=36)
        add_fav_btn.pack(side=tk.LEFT)

        clear_btn = ModernButton(secondary_actions, "清除历史", self.clear_history,
                                self.colors['border'], self.colors['hover_bg'],
                                self.colors['text'], width=200, height=36)
        clear_btn.pack(side=tk.LEFT, padx=(8, 0))

        # 快捷键提示
        shortcuts_frame = tk.Frame(secondary_actions, bg=self.colors['bg'])
        shortcuts_frame.pack(side=tk.RIGHT)

        shortcuts = [
            ("Enter", "普通启动"),
            ("Ctrl+O", "浏览"),
            ("Esc", "最小化")
        ]

        for key, desc in shortcuts:
            shortcut_item = tk.Frame(shortcuts_frame, bg=self.colors['bg'])
            shortcut_item.pack(side=tk.LEFT, padx=(0, 12))

            key_label = tk.Label(shortcut_item, text=key,
                                font=("Segoe UI", 8),
                                bg=self.colors['border'],
                                fg=self.colors['text_secondary'],
                                padx=6, pady=2)
            key_label.pack(side=tk.LEFT, padx=(0, 4))

            desc_label = tk.Label(shortcut_item, text=desc,
                                 font=("Segoe UI", 8),
                                 bg=self.colors['bg'],
                                 fg=self.colors['text_secondary'])
            desc_label.pack(side=tk.LEFT)

    def browse_directory(self):
        directory = filedialog.askdirectory(title="选择工作目录")
        if directory:
            normalized = self.normalize_path(directory)
            self.dir_var.set(normalized)
            self.set_status(f"已选择目录: {normalized}")

    def open_settings(self):
        """打开设置对话框"""
        SettingsDialog(self.root, self)

    def set_status(self, message, tone="info"):
        color_map = {
            "info": self.colors['text_secondary'],
            "success": self.colors['success'],
            "error": self.colors['danger'],
            "warning": self.colors['warning'],
        }
        self.status_var.set(message)
        self.status_label.config(fg=color_map.get(tone, self.colors['text_secondary']))

    def update_current_directory_card(self):
        path = self.normalize_path(self.dir_var.get())
        agent_config = AGENT_CONFIGS[self.current_agent]
        mode_cfg = agent_config["modes"].get(self.last_mode, {})
        mode_text = f"上次启动：{mode_cfg.get('label', self.last_mode)}"
        self.current_mode_chip.config(text=mode_text)

        if not path:
            self.current_name_label.config(text="未选择目录")
            self.current_path_label.config(text="等待输入路径")
            self.current_status_chip.config(text="未输入", bg=self.colors['border'], fg=self.colors['text_secondary'])
            self.current_favorite_btn.config(text="☆")
            return

        self.current_name_label.config(text=os.path.basename(path) or path)
        self.current_path_label.config(text=path)
        self.current_favorite_btn.config(text="★" if path in self.config.get("favorites", []) else "☆")

        if os.path.isdir(path):
            self.current_status_chip.config(text="可用目录", bg=self.colors['success'], fg=self.colors['bg'])
        else:
            self.current_status_chip.config(text="目录无效", bg=self.colors['danger'], fg="#ffffff")

    def rebuild_ui(self):
        if self.validation_job:
            self.root.after_cancel(self.validation_job)
            self.validation_job = None
        for child in self.root.winfo_children():
            child.destroy()
        self.setup_ui()
        self.update_current_directory_card()

    def rebuild_launch_buttons(self):
        for child in self.launch_buttons_frame.winfo_children():
            child.destroy()

        agent_config = AGENT_CONFIGS[self.current_agent]
        modes = agent_config["modes"]

        for i, (mode_id, mode_cfg) in enumerate(modes.items()):
            colors_list = [
                (self.colors['accent'], self.colors['accent_hover']),
                ('#9a3412', '#c2410c'),
                ('#065f46', '#047857'),
            ]
            bg, hover = colors_list[i % len(colors_list)]
            btn = ModernButton(
                self.launch_buttons_frame,
                mode_cfg["label"],
                lambda m=mode_id: self.launch_agent(m),
                bg, hover, '#ffffff',
                width=220, height=40,
                icon="▶" if i == 0 else "⚡"
            )
            btn.pack(side=tk.LEFT, padx=(0, 10) if i < len(modes) - 1 else (0, 0))

    def switch_agent(self, agent_id):
        if agent_id == self.current_agent:
            return
        self.current_agent = agent_id
        self.config["agent"] = agent_id
        self.last_mode = AGENT_CONFIGS[agent_id]["default_mode"]
        self.config["last_mode"] = self.last_mode
        self.save_config()
        self.rebuild_ui()

    def on_path_change(self, *args):
        if self.validation_job:
            self.root.after_cancel(self.validation_job)
        self.validation_job = self.root.after(150, self.validate_path)

    def validate_path(self):
        raw_path = self.dir_var.get()
        path = self.normalize_path(raw_path)
        self.validation_job = None

        if not path:
            self.path_status = None
            self.path_status_label.config(text="未输入", fg=self.colors['text_secondary'])
            self.update_current_directory_card()
            return

        if path != raw_path.strip():
            self.dir_var.set(path)
            return

        if os.path.isdir(path):
            self.path_status = True
            self.path_status_label.config(text="✓ 可用", fg=self.colors['success'])
        else:
            self.path_status = False
            self.path_status_label.config(text="✕ 无效", fg=self.colors['danger'])

        self.update_current_directory_card()

    def open_in_explorer(self):
        self.open_path_in_explorer(self.dir_var.get())

    def open_path_in_explorer(self, path):
        path = self.normalize_path(path)
        if not path:
            messagebox.showwarning("提示", "请先输入或选择一个目录")
            return

        if not os.path.isdir(path):
            messagebox.showerror("错误", f"目录不存在或不是文件夹:\n{path}")
            return

        try:
            subprocess.Popen(["explorer", path])
            self.set_status(f"已在资源管理器中打开: {path}", "success")
        except Exception as e:
            messagebox.showerror("错误", f"打开失败: {str(e)}")
            self.set_status("打开资源管理器失败", "error")

    def launch_from_path(self, path):
        self.dir_var.set(self.normalize_path(path))
        self.launch_agent(self.last_mode)

    def _create_session_group(self, parent, group_key, sessions):
        """创建可折叠的会话分组"""
        # 外层容器
        group_frame = tk.Frame(parent, bg=self.colors['bg'])
        group_frame.pack(fill=tk.X, pady=(0, 4))

        # 分组标题（可点击折叠）— 必须先 pack
        group_header = tk.Frame(group_frame, bg=self.colors['card_bg'], height=36)
        group_header.pack(fill=tk.X)
        group_header.pack_propagate(False)

        # 折叠箭头
        arrow_var = tk.StringVar(value="▾")
        arrow_label = tk.Label(group_header, textvariable=arrow_var,
                              font=("Segoe UI", 9),
                              bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
                              cursor="hand2", padx=4)
        arrow_label.pack(side=tk.LEFT, padx=(8, 0))

        # 项目名称
        project_name = os.path.basename(group_key) or group_key
        project_icon = tk.Label(group_header, text="📁",
                               font=("Segoe UI", 11),
                               bg=self.colors['card_bg'], fg=self.colors['accent'],
                               cursor="hand2")
        project_icon.pack(side=tk.LEFT, padx=(4, 6))

        project_label = tk.Label(group_header, text=project_name,
                                font=("Segoe UI", 9, "bold"),
                                bg=self.colors['card_bg'], fg=self.colors['text'],
                                cursor="hand2")
        project_label.pack(side=tk.LEFT)

        # 完整路径（截断）
        max_path_len = 35
        display_path = group_key if len(group_key) <= max_path_len else "..." + group_key[-(max_path_len-3):]
        path_hint = tk.Label(group_header, text=display_path,
                            font=("Segoe UI", 8),
                            bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
                            cursor="hand2")
        path_hint.pack(side=tk.LEFT, padx=(8, 0))

        # 会话数量
        count_label = tk.Label(group_header, text=f"{len(sessions)} 个会话",
                              font=("Segoe UI", 8),
                              bg=self.colors['card_bg'], fg=self.colors['text_secondary'])
        count_label.pack(side=tk.RIGHT, padx=12)

        # 打开目录按钮
        open_dir_btn = tk.Label(group_header, text="📂",
                               font=("Segoe UI", 10),
                               bg=self.colors['card_bg'], fg=self.colors['text'],
                               cursor="hand2", padx=6)
        open_dir_btn.pack(side=tk.RIGHT, padx=(0, 4))
        open_dir_btn.bind("<Enter>", lambda e: open_dir_btn.config(bg=self.colors['hover_bg']))
        open_dir_btn.bind("<Leave>", lambda e: open_dir_btn.config(bg=self.colors['card_bg']))
        open_dir_btn.bind("<Button-1>", lambda e, p=group_key: self.open_path_in_explorer(p))

        # 子项容器（可折叠）— 在标题之后 pack
        children_frame = tk.Frame(group_frame, bg=self.colors['bg'])
        children_frame.pack(fill=tk.X)

        # 折叠/展开状态
        is_expanded = [True]

        def toggle_expand(e=None):
            if is_expanded[0]:
                children_frame.pack_forget()
                arrow_var.set("▸")
            else:
                children_frame.pack(fill=tk.X, after=group_header)
                arrow_var.set("▾")
            is_expanded[0] = not is_expanded[0]

        def on_folder_double_click(e=None):
            """双击文件夹：弹出模式选择对话框"""
            self._on_folder_double_click(group_key)

        # 绑定标题栏事件
        for widget in [group_header, arrow_label, project_icon, project_label, path_hint, count_label]:
            widget.bind("<Button-1>", toggle_expand)
            widget.bind("<Double-Button-1>", on_folder_double_click)
            widget.bind("<Enter>", lambda e: group_header.config(bg=self.colors['hover_bg']))
            widget.bind("<Leave>", lambda e: group_header.config(bg=self.colors['card_bg']))

        # 渲染会话子项
        for i, session in enumerate(sessions[:3]):
            session_item = tk.Frame(children_frame, bg=self.colors['bg'], height=40)
            session_item.pack(fill=tk.X)
            session_item.pack_propagate(False)

            # 会话 ID
            sid = session.get("id", "unknown")
            sid_display = sid[:12] + "..." if len(sid) > 12 else sid
            sid_label = tk.Label(session_item, text=sid_display,
                                font=("Consolas", 8),
                                bg=self.colors['bg'], fg=self.colors['text_secondary'],
                                cursor="hand2")
            sid_label.pack(side=tk.LEFT, padx=(28, 0), pady=8)

            # 提示文本（第一个问题）
            prompt = session.get("prompt", "")
            if prompt:
                prompt_display = prompt[:50] + "..." if len(prompt) > 50 else prompt
                prompt_label = tk.Label(session_item, text=prompt_display,
                                       font=("Segoe UI", 8),
                                       bg=self.colors['bg'], fg=self.colors['text'],
                                       anchor=tk.W, cursor="hand2")
                prompt_label.pack(side=tk.LEFT, padx=(12, 0), fill=tk.X, expand=True, pady=8)

            # 时间信息
            if "mtime" in session:
                from datetime import datetime
                dt = datetime.fromtimestamp(session["mtime"])
                time_str = dt.strftime("%m-%d %H:%M")
            elif "date" in session:
                time_str = session["date"]
            elif "created" in session:
                time_str = session["created"][:16]
            else:
                time_str = ""

            if time_str:
                time_label = tk.Label(session_item, text=time_str,
                                    font=("Segoe UI", 8),
                                    bg=self.colors['bg'], fg=self.colors['text_secondary'],
                                    cursor="hand2")
                time_label.pack(side=tk.RIGHT, padx=4, pady=8)

            # 文件大小
            if "size" in session:
                size = session["size"]
                if size > 1024 * 1024:
                    size_str = f"{size / (1024*1024):.1f}MB"
                elif size > 1024:
                    size_str = f"{size / 1024:.0f}KB"
                else:
                    size_str = f"{size}B"
                size_label = tk.Label(session_item, text=size_str,
                                    font=("Segoe UI", 8),
                                    bg=self.colors['bg'], fg=self.colors['text_secondary'],
                                    cursor="hand2")
                size_label.pack(side=tk.RIGHT, padx=(0, 4), pady=8)

            # 删除按钮
            delete_btn = tk.Label(session_item, text="✕",
                                 font=("Segoe UI", 9),
                                 bg=self.colors['bg'], fg=self.colors['text_secondary'],
                                 cursor="hand2", padx=4)
            delete_btn.pack(side=tk.RIGHT, padx=(0, 8), pady=8)
            delete_btn.bind("<Enter>", lambda e, d=delete_btn: d.config(fg=self.colors['danger']))
            delete_btn.bind("<Leave>", lambda e, d=delete_btn: d.config(fg=self.colors['text_secondary']))
            delete_btn.bind("<Button-1>", lambda e, s=session, g=group_key: self._delete_session(s, g))

            # 绑定双击事件 — 恢复会话
            def on_session_double_click(e, s=session):
                self._on_session_double_click(s)

            session_item.bind("<Double-Button-1>", on_session_double_click)
            for child in session_item.winfo_children():
                if child != delete_btn:
                    child.bind("<Double-Button-1>", on_session_double_click)

            # 单击启动项目
            session_item.bind("<Button-1>", lambda e, p=group_key: self._launch_session(p))
            for child in session_item.winfo_children():
                if child != delete_btn:
                    child.bind("<Button-1>", lambda e, p=group_key: self._launch_session(p))
                child.bind("<Enter>", lambda e, si=session_item: si.config(bg=self.colors['hover_bg']))
                child.bind("<Leave>", lambda e, si=session_item: si.config(bg=self.colors['bg']))

            session_item.bind("<Enter>", lambda e, si=session_item: si.config(bg=self.colors['hover_bg']))
            session_item.bind("<Leave>", lambda e, si=session_item: si.config(bg=self.colors['bg']))

    def _launch_session(self, project_path):
        """点击会话项时，设置项目路径并启动"""
        normalized = self.normalize_path(project_path)
        if os.path.isdir(normalized):
            self.dir_var.set(normalized)
            self.launch_agent(self.last_mode)
        else:
            self.set_status(f"项目目录不存在: {normalized}", "warning")

    def _on_folder_double_click(self, project_path):
        """双击文件夹：弹出模式选择对话框，然后启动 agent"""
        normalized = self.normalize_path(project_path)
        if not os.path.isdir(normalized):
            self.set_status(f"目录不存在: {normalized}", "warning")
            return

        agent_config = AGENT_CONFIGS[self.current_agent]
        modes = agent_config["modes"]

        # 创建模式选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("选择启动模式")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 300) // 2
        dialog.geometry(f"400x300+{x}+{y}")

        colors = self.colors
        dialog.configure(bg=colors['bg'])

        # 标题
        header = tk.Frame(dialog, bg=colors['card_bg'], height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title_label = tk.Label(header, text=f"{agent_config['name']} - 选择模式",
                              font=("Segoe UI", 12, "bold"),
                              bg=colors['card_bg'], fg=colors['text'])
        title_label.pack(pady=16)

        # 项目路径
        path_label = tk.Label(dialog, text=f"项目: {normalized}",
                             font=("Segoe UI", 9),
                             bg=colors['bg'], fg=colors['text_secondary'],
                             wraplength=360)
        path_label.pack(pady=(16, 8), padx=20)

        # 模式按钮
        selected_mode = [None]

        def on_select(mode):
            selected_mode[0] = mode
            dialog.destroy()
            # 启动 agent
            self.dir_var.set(normalized)
            self.launch_agent(mode)

        modes_frame = tk.Frame(dialog, bg=colors['bg'])
        modes_frame.pack(fill=tk.X, padx=20, pady=8)

        for mode_id, mode_cfg in modes.items():
            btn = tk.Button(modes_frame, text=f"{mode_cfg['label']}\n{mode_cfg['desc']}",
                           font=("Segoe UI", 10),
                           bg=colors['accent'], fg='#ffffff',
                           activebackground=colors['accent_hover'],
                           relief=tk.FLAT, padx=20, pady=10,
                           command=lambda m=mode_id: on_select(m))
            btn.pack(fill=tk.X, pady=4)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=colors['accent_hover']))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=colors['accent']))

        # 取消按钮
        cancel_btn = tk.Button(dialog, text="取消",
                              font=("Segoe UI", 9),
                              bg=colors['border'], fg=colors['text'],
                              relief=tk.FLAT, padx=20, pady=6,
                              command=dialog.destroy)
        cancel_btn.pack(pady=8)

    def _on_session_double_click(self, session):
        """双击会话：恢复该会话"""
        agent_config = AGENT_CONFIGS[self.current_agent]
        cwd = session.get("cwd", "")
        session_id = session.get("id", "")

        if not cwd or not os.path.isdir(cwd):
            self.set_status(f"会话目录不存在: {cwd}", "warning")
            return

        # 构建恢复命令
        cmd_path = self.resolve_agent_command()
        if not cmd_path:
            messagebox.showerror("错误", f"找不到 {agent_config['name']} 命令")
            return

        resume_args = agent_config.get("resume_args", [])
        if cmd_path.lower().endswith((".cmd", ".bat")):
            cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", cmd_path]
        else:
            cmd = [cmd_path]

        cmd.extend(resume_args)
        if session_id:
            cmd.append(session_id)

        try:
            subprocess.Popen(cmd, cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            self.set_status(f"已恢复会话: {session_id[:12]}...", "success")
        except Exception as e:
            messagebox.showerror("错误", f"恢复会话失败: {str(e)}")

    def _delete_session(self, session, group_key):
        """删除指定会话"""
        agent_config = AGENT_CONFIGS[self.current_agent]
        session_id = session.get("id", "")
        session_file = session.get("file", "")

        # 确认删除
        confirm = messagebox.askyesno("确认删除",
                                     f"确定要删除这个会话吗？\n\n会话 ID: {session_id}\n项目: {group_key}\n\n此操作不可撤销。")
        if not confirm:
            return

        # 删除文件
        if session_file and os.path.isfile(session_file):
            try:
                os.remove(session_file)
                self.set_status(f"已删除会话: {session_id[:12]}", "success")
                self.rebuild_ui()
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {str(e)}")
        else:
            # 对于 MiMo 数据库中的会话，只提示不支持删除
            if self.current_agent == "mimo":
                messagebox.showinfo("提示", "MiMo Code 会话存储在数据库中，暂不支持单独删除。\n\n可以在 MiMo Code 中使用 /clear 清除会话。")
            else:
                self.set_status(f"会话文件不存在: {session_file}", "warning")

    def toggle_favorite(self, path):
        path = self.normalize_path(path)
        if not path:
            messagebox.showwarning("提示", "请先选择一个目录")
            return

        favorites = self.config.setdefault("favorites", [])
        if path in favorites:
            favorites.remove(path)
            self.set_status(f"已取消收藏: {path}", "info")
        else:
            favorites.insert(0, path)
            self.config["favorites"] = favorites[:10]
            self.set_status(f"已加入收藏夹: {path}", "success")
        self.save_config()
        self.rebuild_ui()

    def select_recent(self, path):
        normalized = self.normalize_path(path)
        self.dir_var.set(normalized)
        if os.path.isdir(normalized):
            self.set_status(f"已选中目录: {normalized}")
        else:
            self.set_status("该历史目录在这台电脑上不存在，请重新选择目录", "warning")

    def select_favorite(self, path):
        self.dir_var.set(self.normalize_path(path))
        self.launch_agent(self.last_mode)

    def add_to_favorites(self):
        path = self.normalize_path(self.dir_var.get())
        if not path:
            messagebox.showwarning("提示", "请先选择一个目录")
            return

        if not os.path.isdir(path):
            messagebox.showerror("错误", f"目录不存在或不是文件夹:\n{path}")
            return

        if path in self.config.setdefault("favorites", []):
            self.set_status("该目录已在收藏夹中", "warning")
            return

        self.config["favorites"].insert(0, path)
        self.config["favorites"] = self.config["favorites"][:10]
        self.save_config()
        self.rebuild_ui()
        self.set_status(f"已添加到收藏夹: {path}", "success")

    def remove_favorite(self, path):
        if messagebox.askyesno("确认", f"确定要从收藏夹移除吗？\n\n{path}"):
            self.config["favorites"].remove(path)
            self.save_config()
            self.rebuild_ui()
            self.set_status(f"已从收藏夹移除: {path}", "info")

    def clear_history(self):
        if messagebox.askyesno("确认", "确定要清除所有历史记录吗？\n\n注意：收藏夹不会被清除"):
            self.config["recent_dirs"] = []
            self.save_config()
            self.rebuild_ui()
            self.set_status("历史记录已清除", "info")

    def launch_agent(self, mode=None):
        work_dir = self.normalize_path(self.dir_var.get())
        agent_config = AGENT_CONFIGS[self.current_agent]

        if not work_dir:
            messagebox.showerror("错误", "请选择或输入工作目录")
            return

        if not os.path.isdir(work_dir):
            messagebox.showerror("错误", f"目录不存在或不是文件夹:\n{work_dir}\n\n请点击 浏览 选择这台电脑上的项目目录。")
            self.set_status("目录无效，请选择本机存在的项目目录", "error")
            return

        selected_mode = mode or self.last_mode
        if selected_mode not in agent_config["modes"]:
            selected_mode = agent_config["default_mode"]

        env_key = agent_config.get("env_key")
        if env_key and not os.environ.get(env_key):
            messagebox.showerror("错误", f"未找到环境变量 {env_key}\n\n{agent_config['name']} 需要有效的 API Key 才能运行。\n\n请先设置 {env_key} 后重试。")
            self.set_status(f"缺少环境变量 {env_key}", "error")
            return

        cmd = self.build_agent_command(selected_mode)
        if not cmd:
            env_hint = ""
            if env_key:
                env_hint = f"\n\n并确认 {env_key} 环境变量已设置"
            messagebox.showerror("错误", f"找不到 {agent_config['name']} 命令。\n\n请先安装 {agent_config['name']}{env_hint}")
            self.set_status(f"未找到 {agent_config['name']} 命令", "error")
            return

        if work_dir not in self.config["recent_dirs"]:
            self.config["recent_dirs"].insert(0, work_dir)
            self.config["recent_dirs"] = self.config["recent_dirs"][:10]
        else:
            self.config["recent_dirs"].remove(work_dir)
            self.config["recent_dirs"].insert(0, work_dir)

        self.last_mode = selected_mode
        self.config["last_mode"] = selected_mode
        self.config["auto_close"] = self.auto_close_var.get()
        self.save_config()
        self.update_current_directory_card()

        try:
            subprocess.Popen(
                cmd,
                cwd=work_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            mode_label = agent_config["modes"][selected_mode]["label"]
            self.set_status(f"{agent_config['name']} 已以{mode_label}启动: {work_dir}", "success")

            if self.auto_close_var.get():
                self.root.destroy()
            else:
                self.rebuild_ui()
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {str(e)}")
            self.set_status(f"启动 {agent_config['name']} 失败", "error")

def bring_to_front():
    """激活已运行的实例窗口"""
    try:
        # 连接到已运行实例的 socket
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', 58432))
        client.send(b'SHOW')  # 发送显示命令
        client.close()
    except:
        pass

def main():
    # 单实例检测 - 使用 socket 端口锁
    lock_socket = None
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.bind(('127.0.0.1', 58432))
        lock_socket.listen(1)
    except socket.error:
        # 端口已被占用，激活已有实例
        bring_to_front()
        sys.exit(0)

    root = tk.Tk()

    # 减少窗口闪烁：先隐藏窗口，初始化完成后再显示
    root.withdraw()

    app = ClaudeLauncher(root, lock_socket)
    app.update_current_directory_card()

    # 窗口居中
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    # 显示窗口
    root.deiconify()

    # 监听激活请求
    def check_activation():
        try:
            lock_socket.settimeout(0.01)
            conn, addr = lock_socket.accept()
            data = conn.recv(1024)
            conn.close()
            if data == b'SHOW':
                root.deiconify()
                root.lift()
                root.focus_force()
        except socket.timeout:
            pass
        except:
            pass
        root.after(100, check_activation)

    check_activation()

    # 保持 socket 锁直到程序退出
    def on_closing():
        # 最小化到托盘而不是关闭
        app.minimize_to_tray()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

    # 清理
    if app.tray_icon:
        app.tray_icon.stop()
    if lock_socket:
        lock_socket.close()

if __name__ == "__main__":
    main()
