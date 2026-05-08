import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import json
import os
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
    def __init__(self, parent, path, on_select, on_launch, on_open_explorer, on_toggle_favorite, is_favorite, colors):
        super().__init__(parent, bg=colors['card_bg'], height=52)
        self.path = path
        self.on_select = on_select
        self.on_launch = on_launch
        self.on_open_explorer = on_open_explorer
        self.on_toggle_favorite = on_toggle_favorite
        self.colors = colors
        self.is_favorite = is_favorite

        self.pack_propagate(False)

        content_frame = tk.Frame(self, bg=colors['card_bg'])
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=10)

        icon_label = tk.Label(content_frame, text="🕘", font=("Segoe UI", 14),
                             bg=colors['card_bg'], fg=colors['text_secondary'])
        icon_label.pack(side=tk.LEFT, padx=(0, 12))

        path_info = tk.Frame(content_frame, bg=colors['card_bg'])
        path_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        project_name = os.path.basename(path) or path
        name_label = tk.Label(path_info, text=project_name, font=("Segoe UI", 10, "bold"),
                             bg=colors['card_bg'], fg=colors['text'], anchor=tk.W)
        name_label.pack(fill=tk.X)

        path_label = tk.Label(path_info, text=path, font=("Segoe UI", 8),
                             bg=colors['card_bg'], fg=colors['text_secondary'], anchor=tk.W)
        path_label.pack(fill=tk.X)

        button_frame = tk.Frame(self, bg=colors['card_bg'])
        button_frame.pack(side=tk.RIGHT, padx=12)

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

        launch_btn = tk.Label(button_frame, text="启动", font=("Segoe UI", 9, "bold"),
                             bg=colors['accent'], fg='#ffffff', cursor="hand2", padx=16, pady=6)
        launch_btn.pack(side=tk.LEFT)
        launch_btn.bind("<Enter>", lambda e: launch_btn.config(bg=colors['accent_hover']))
        launch_btn.bind("<Leave>", lambda e: launch_btn.config(bg=colors['accent']))
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
                        if subchild.cget("text") not in ["📂", "★", "☆", "启动"]:
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
                        if subchild.cget("text") not in ["📂", "★", "☆", "启动"]:
                            subchild.config(bg=self.colors['card_bg'])
                    except:
                        pass

class ClaudeLauncher:
    def __init__(self, root, lock_socket=None):
        self.root = root
        self.lock_socket = lock_socket
        self.root.title("Claude Code Launcher")
        self.root.geometry("700x780")
        self.root.resizable(False, False)

        self.config_file = Path.home() / ".claude_launcher_config.json"
        self.load_config()

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

        self.setup_ui()

        # 绑定快捷键
        self.root.bind('<Return>', lambda e: self.launch_claude())
        self.root.bind('<Escape>', lambda e: self.minimize_to_tray())
        self.root.bind('<Control-o>', lambda e: self.browse_directory())

        self.validation_job = None
        self.path_status = None

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

        def on_quit(icon, item):
            self.root.after(0, self.quit_app)

        menu = Menu(
            MenuItem('显示窗口', on_show, default=True),
            MenuItem('退出', on_quit)
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

    def quit_app(self):
        """退出应用"""
        if self.tray_icon:
            self.tray_icon.stop()
        if self.lock_socket:
            self.lock_socket.close()
        self.root.quit()
        sys.exit(0)

    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "recent_dirs": [],
                "favorites": [],
                "last_mode": "normal",
                "auto_close": True,
                "theme": "auto"
            }

    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

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
        logo_label = tk.Label(header_content, text="⚡", font=("Segoe UI", 24),
                             bg=self.colors['card_bg'], fg=self.colors['accent'])
        logo_label.pack(side=tk.LEFT, padx=(0, 12))

        title_frame = tk.Frame(header_content, bg=self.colors['card_bg'])
        title_frame.pack(side=tk.LEFT)

        title_label = tk.Label(title_frame, text="Claude Code",
                              font=("Segoe UI", 16, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['text'])
        title_label.pack(anchor=tk.W)

        subtitle_label = tk.Label(title_frame, text="快速启动开发环境",
                                 font=("Segoe UI", 9),
                                 bg=self.colors['card_bg'], fg=self.colors['text_secondary'])
        subtitle_label.pack(anchor=tk.W)

        # 状态栏（移到顶部标题栏下方）
        self.status_var = tk.StringVar(value="准备就绪")
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

        self.current_mode_chip = tk.Label(current_meta, text="上次启动：普通模式",
                                         font=("Segoe UI", 8), padx=8, pady=3,
                                         bg=self.colors['border'], fg=self.colors['text_secondary'])
        self.current_mode_chip.pack(side=tk.LEFT)

        current_actions = tk.Frame(current_inner, bg=self.colors['card_bg'])
        current_actions.pack(fill=tk.X, pady=(12, 0))

        current_normal_btn = ModernButton(
            current_actions,
            "普通启动",
            lambda: self.launch_claude("normal"),
            self.colors['accent'],
            self.colors['accent_hover'],
            '#ffffff',
            width=220,
            height=40,
            icon="▶"
        )
        current_normal_btn.pack(side=tk.LEFT)

        current_skip_btn = ModernButton(
            current_actions,
            "跳过权限启动",
            lambda: self.launch_claude("skip"),
            '#9a3412',
            '#c2410c',
            '#ffffff',
            width=220,
            height=40,
            icon="⚠"
        )
        current_skip_btn.pack(side=tk.LEFT, padx=(10, 0))

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

        # 设置初始值
        if self.config.get("recent_dirs"):
            self.dir_var.set(self.config["recent_dirs"][0])

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

        # 最近目录
        if self.config.get("recent_dirs"):
            recent_section = tk.Frame(content_inner, bg=self.colors['bg'])
            recent_section.pack(fill=tk.X, pady=(0, 16))

            recent_header = tk.Frame(recent_section, bg=self.colors['bg'])
            recent_header.pack(fill=tk.X, pady=(0, 8))

            recent_label = tk.Label(recent_header, text="最近目录",
                                   font=("Segoe UI", 10, "bold"),
                                   bg=self.colors['bg'], fg=self.colors['text'])
            recent_label.pack(side=tk.LEFT)

            recent_count = tk.Label(recent_header, text=f"{min(len(self.config['recent_dirs']), 5)} 项",
                                   font=("Segoe UI", 9),
                                   bg=self.colors['bg'], fg=self.colors['text_secondary'])
            recent_count.pack(side=tk.LEFT, padx=(8, 0))

            recent_container = tk.Frame(recent_section, bg=self.colors['bg'])
            recent_container.pack(fill=tk.X)

            for i, recent_path in enumerate(self.config.get("recent_dirs", [])[:5]):
                recent_item = RecentItem(
                    recent_container,
                    recent_path,
                    self.select_recent,
                    self.launch_from_path,
                    self.open_path_in_explorer,
                    self.toggle_favorite,
                    recent_path in self.config.get("favorites", []),
                    self.colors,
                )
                recent_item.pack(fill=tk.X, pady=(0, 2) if i < 4 else 0)

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
                fav_item = RecentItem(
                    fav_container,
                    fav_path,
                    self.select_recent,
                    self.launch_from_path,
                    self.open_path_in_explorer,
                    self.toggle_favorite,
                    True,
                    self.colors,
                )
                fav_item.pack(fill=tk.X, pady=(0, 2) if i < 4 else 0)

        # 启动选项
        options_section = tk.Frame(content_inner, bg=self.colors['card_bg'])
        options_section.pack(fill=tk.X, pady=(0, 16))

        options_inner = tk.Frame(options_section, bg=self.colors['card_bg'])
        options_inner.pack(fill=tk.X, padx=16, pady=16)

        options_label = tk.Label(options_inner, text="启动选项",
                                font=("Segoe UI", 10, "bold"),
                                bg=self.colors['card_bg'], fg=self.colors['text'])
        options_label.pack(anchor=tk.W, pady=(0, 12))

        self.last_mode = self.config.get("last_mode", "normal")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.TRadiobutton',
                       background=self.colors['card_bg'],
                       foreground=self.colors['text'],
                       font=("Segoe UI", 9))

        self.auto_close_var = tk.BooleanVar(value=self.config.get("auto_close", True))

        style.configure('Custom.TCheckbutton',
                       background=self.colors['card_bg'],
                       foreground=self.colors['text'],
                       font=("Segoe UI", 9))

        auto_close_check = ttk.Checkbutton(options_inner,
                                          text="启动后自动关闭此窗口",
                                          variable=self.auto_close_var,
                                          style='Custom.TCheckbutton')
        auto_close_check.pack(anchor=tk.W)

        # 主题切换
        theme_frame = tk.Frame(options_inner, bg=self.colors['card_bg'])
        theme_frame.pack(anchor=tk.W, pady=(16, 0))

        theme_label = tk.Label(theme_frame, text="主题:",
                              font=("Segoe UI", 9, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['text'])
        theme_label.pack(side=tk.LEFT, padx=(0, 12))

        theme_buttons = [
            ("跟随系统", "auto"),
            ("浅色", "light"),
            ("深色", "dark")
        ]

        for text, theme in theme_buttons:
            is_active = self.current_theme == theme
            btn_bg = self.colors['accent'] if is_active else self.colors['border']
            btn_fg = '#ffffff' if is_active else self.colors['text']

            theme_btn = tk.Label(theme_frame, text=text,
                                font=("Segoe UI", 9),
                                bg=btn_bg, fg=btn_fg,
                                cursor="hand2", padx=16, pady=6)
            theme_btn.pack(side=tk.LEFT, padx=(0, 6))
            theme_btn.bind("<Button-1>", lambda e, t=theme: self.switch_theme(t))

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
            self.dir_var.set(directory)
            self.set_status(f"已选择目录: {directory}")

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
        path = self.dir_var.get().strip()
        mode_text = "上次启动：跳过权限" if getattr(self, 'last_mode', 'normal') == "skip" else "上次启动：普通模式"
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
        for child in self.root.winfo_children():
            child.destroy()
        self.setup_ui()
        self.update_current_directory_card()

    def on_path_change(self, *args):
        if self.validation_job:
            self.root.after_cancel(self.validation_job)
        self.validation_job = self.root.after(150, self.validate_path)

    def validate_path(self):
        path = self.dir_var.get().strip()
        self.validation_job = None

        if not path:
            self.path_status = None
            self.path_status_label.config(text="未输入", fg=self.colors['text_secondary'])
            self.update_current_directory_card()
            return

        if os.path.isdir(path):
            self.path_status = True
            self.path_status_label.config(text="✓ 可用", fg=self.colors['success'])
        else:
            self.path_status = False
            self.path_status_label.config(text="✕ 无效", fg=self.colors['danger'])

        self.update_current_directory_card()

    def open_in_explorer(self):
        self.open_path_in_explorer(self.dir_var.get().strip())

    def open_path_in_explorer(self, path):
        if not path:
            messagebox.showwarning("提示", "请先输入或选择一个目录")
            return

        if not os.path.exists(path):
            messagebox.showerror("错误", "目录不存在")
            return

        try:
            subprocess.Popen(f'explorer "{path}"')
            self.set_status(f"已在资源管理器中打开: {path}", "success")
        except Exception as e:
            messagebox.showerror("错误", f"打开失败: {str(e)}")
            self.set_status("打开资源管理器失败", "error")

    def launch_from_path(self, path):
        self.dir_var.set(path)
        self.launch_claude(self.last_mode)

    def toggle_favorite(self, path):
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
        self.dir_var.set(path)
        self.set_status(f"已选中目录: {path}")

    def select_favorite(self, path):
        self.dir_var.set(path)
        self.launch_claude(self.last_mode)

    def add_to_favorites(self):
        path = self.dir_var.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择一个目录")
            return

        if not os.path.exists(path):
            messagebox.showerror("错误", "目录不存在")
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

    def launch_claude(self, mode=None):
        work_dir = self.dir_var.get().strip()
        selected_mode = mode or self.last_mode

        if not work_dir:
            messagebox.showerror("错误", "请选择或输入工作目录")
            return

        if not os.path.exists(work_dir):
            messagebox.showerror("错误", f"目录不存在: {work_dir}")
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

        cmd = ["claude"]
        if selected_mode == "skip":
            cmd.append("--dangerously-skip-permissions")

        try:
            subprocess.Popen(
                cmd,
                cwd=work_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            mode_text = "跳过权限模式" if selected_mode == "skip" else "普通模式"
            self.set_status(f"Claude Code 已以{mode_text}启动: {work_dir}", "success")

            if self.auto_close_var.get():
                self.root.destroy()
            else:
                self.rebuild_ui()
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {str(e)}")
            self.set_status("启动 Claude Code 失败", "error")

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
