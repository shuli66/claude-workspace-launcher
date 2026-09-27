"""主窗口：骨架构建一次，会话侧栏与收藏夹按需局部重建。"""

import os
import subprocess
import tkinter as tk

from .. import agent, theme
from . import dialogs, icons
from .widgets import (
    FlatButton,
    FolderGroupRow,
    FavoriteRow,
    IconButton,
    Pill,
    ScrollArea,
    SectionHeader,
    elide_path,
)

SIDEBAR_WIDTH = 244
MAX_FAVORITES = 10


class MainWindow:

    def __init__(self, root, config, store):
        self.root = root
        self.config = config
        self.store = store

        self.colors = theme.resolve(config.get("theme", "auto"))
        self.selected_session_id = None
        # 记录被手动折叠的项目。默认全展开，所以存「折叠集合」而不是「展开集合」——
        # 用展开集合的话，空集合会与「全部默认展开」冲突，导致刷新后全部收起。
        self.collapsed_projects = set()
        self.status_job = None
        self.validation_job = None

        root.title("Claude Launcher")
        root.geometry("900x620")
        root.resizable(False, False)
        root.configure(bg=self.colors["bg"])

        self._apply_window_icon()
        self._build_skeleton()
        self._bind_shortcuts()
        self.refresh_sessions()
        self.refresh_favorites()
        self._update_current_card()

        if config.warning:
            self.set_status(config.warning, "warning")

    # ---------- 骨架 ----------

    def _apply_window_icon(self):
        path = icons.assets_dir() / "claude_icon.ico"
        if path.exists():
            try:
                self.root.iconbitmap(str(path))
            except tk.TclError:
                pass

    def _build_skeleton(self):
        colors = self.colors

        self.topbar = tk.Frame(self.root, bg=colors["bg"], height=46)
        self.topbar.pack(fill=tk.X)
        self.topbar.pack_propagate(False)
        self._build_topbar(self.topbar)

        self.status_bar = tk.Frame(self.root, bg=colors["bg"], height=22)
        self.status_bar.pack(fill=tk.X)
        self.status_bar.pack_propagate(False)

        self.status_label = tk.Label(
            self.status_bar, text="", font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_3"], anchor=tk.W,
        )
        self.status_label.pack(fill=tk.BOTH, padx=14)

        separator = tk.Frame(self.root, bg=colors["line"], height=1)
        separator.pack(fill=tk.X)

        columns = tk.Frame(self.root, bg=colors["surface"])
        columns.pack(fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(columns, bg=colors["bg"], width=SIDEBAR_WIDTH)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        sidebar_header = tk.Frame(self.sidebar, bg=colors["bg"])
        sidebar_header.pack(fill=tk.X, padx=10, pady=(10, 6))
        self.session_header = SectionHeader(sidebar_header, "会话", colors)
        self.session_header.pack(fill=tk.X)

        self.session_area = ScrollArea(self.sidebar, colors)
        self.session_area.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 8))

        divider = tk.Frame(columns, bg=colors["line"], width=1)
        divider.pack(side=tk.LEFT, fill=tk.Y)

        self.main = tk.Frame(columns, bg=colors["surface"])
        self.main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_path_bar()
        self._build_current_card()
        self._build_favorites()
        self._build_footer()

    def _build_topbar(self, parent):
        colors = self.colors

        mark = icons.claude_mark()
        if mark is not None:
            holder = tk.Frame(parent, bg=colors["bg"])
            holder.pack(side=tk.LEFT, padx=(14, 9), pady=10)
            logo = tk.Label(holder, image=mark, bg=colors["bg"])
            logo.image = mark
            logo.pack()
        else:
            tk.Label(
                parent, text="✳", font=("Segoe UI", 15),
                bg=colors["bg"], fg=colors["accent"],
            ).pack(side=tk.LEFT, padx=(14, 9))

        tk.Label(
            parent, text="Claude Launcher", font=("Segoe UI", 10, "bold"),
            bg=colors["bg"], fg=colors["ink"],
        ).pack(side=tk.LEFT, pady=12)

        self.settings_button = IconButton(
            parent, "gear", self.open_settings, colors, tooltip="设置",
        )
        self.settings_button.pack(side=tk.RIGHT, padx=(0, 12), pady=9)

        self.refresh_button = IconButton(
            parent, "refresh", self.refresh_sessions, colors, tooltip="刷新会话",
        )
        self.refresh_button.pack(side=tk.RIGHT, padx=(0, 4), pady=9)

    def _build_path_bar(self):
        colors = self.colors
        bar = tk.Frame(self.main, bg=colors["line"], padx=1, pady=1)
        bar.pack(fill=tk.X, padx=16, pady=(16, 10))

        inner = tk.Frame(bar, bg=colors["surface"], height=36)
        inner.pack(fill=tk.X)
        inner.pack_propagate(False)

        icon = tk.Canvas(inner, width=18, height=18, bg=colors["surface"], highlightthickness=0)
        icon.pack(side=tk.LEFT, padx=(10, 6))
        icons.draw(icon, "folder", colors["ink_3"], 14, x=2, y=2)

        self.dir_var = tk.StringVar()
        self.dir_var.trace_add("write", self._on_path_change)
        self.dir_entry = tk.Entry(
            inner, textvariable=self.dir_var, font=("Segoe UI", 9),
            bg=colors["surface"], fg=colors["ink"], relief=tk.FLAT,
            insertbackground=colors["ink"], bd=0,
        )
        self.dir_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)

        self.path_state = tk.Label(
            inner, text="", font=("Segoe UI", 8),
            bg=colors["surface"], fg=colors["ink_3"], padx=6,
        )
        self.path_state.pack(side=tk.RIGHT)

        FlatButton(inner, "浏览", self.browse_directory, colors, variant="ghost").pack(
            side=tk.RIGHT, padx=(0, 6), pady=4)

    def _build_current_card(self):
        colors = self.colors
        self.current_card = tk.Frame(self.main, bg=colors["line"], padx=1, pady=1)
        self.current_card.pack(fill=tk.X, padx=16, pady=(0, 14))

        inner = tk.Frame(self.current_card, bg=colors["bg"])
        inner.pack(fill=tk.X, padx=14, pady=12)

        head = tk.Frame(inner, bg=colors["bg"])
        head.pack(fill=tk.X)

        text = tk.Frame(head, bg=colors["bg"])
        text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.current_name = tk.Label(
            text, text="未选择目录", font=("Segoe UI", 11, "bold"),
            bg=colors["bg"], fg=colors["ink"], anchor=tk.W,
        )
        self.current_name.pack(fill=tk.X)

        self.current_path = tk.Label(
            text, text="输入或浏览选择一个项目目录", font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_3"], anchor=tk.W,
        )
        self.current_path.pack(fill=tk.X)

        self.current_state = Pill(head, "未选择", colors, tone="neutral")
        self.current_state.pack(side=tk.RIGHT, anchor=tk.N)

        actions = tk.Frame(inner, bg=colors["bg"])
        actions.pack(fill=tk.X, pady=(12, 0))

        self.mode_buttons = []
        for mode_id, mode_config in agent.MODES.items():
            button = FlatButton(
                actions, mode_config["label"],
                lambda m=mode_id: self.launch(m),
                colors,
                variant="primary" if mode_id == agent.DEFAULT_MODE else "secondary",
            )
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.mode_buttons.append((mode_id, button))

        self.open_button = IconButton(
            actions, "open_external", self.open_in_explorer, colors, tooltip="在资源管理器中打开",
        )
        self.open_button.pack(side=tk.RIGHT)

        self.favorite_button = IconButton(
            actions, "star", self.toggle_favorite, colors, tooltip="加入收藏夹",
        )
        self.favorite_button.pack(side=tk.RIGHT, padx=(0, 4))

    def _build_favorites(self):
        colors = self.colors
        header = tk.Frame(self.main, bg=colors["surface"])
        header.pack(fill=tk.X, padx=16, pady=(0, 6))
        self.favorite_header = SectionHeader(header, "收藏夹", colors)
        self.favorite_header.pack(fill=tk.X)

        self.favorite_area = ScrollArea(self.main, colors)
        self.favorite_area.pack(fill=tk.BOTH, expand=True, padx=16)

    def _build_footer(self):
        colors = self.colors
        footer = tk.Frame(self.main, bg=colors["surface"])
        footer.pack(fill=tk.X, padx=16, pady=(10, 14))

        FlatButton(
            footer, "＋ 添加当前目录", self.add_to_favorites, colors, variant="ghost",
        ).pack(side=tk.LEFT)

        self.shortcut_label = tk.Label(
            footer,
            text="Enter 启动    Ctrl+O 浏览    Esc 最小化",
            font=("Segoe UI", 8), bg=colors["surface"], fg=colors["ink_3"],
        )
        self.shortcut_label.pack(side=tk.RIGHT)

    def _bind_shortcuts(self):
        self.root.bind("<Return>", lambda _event: self.launch())
        self.root.bind("<Control-o>", lambda _event: self.browse_directory())
        self.root.bind("<Escape>", lambda _event: self.on_escape())

    def on_escape(self):
        pass  # 由 app 层注入最小化行为，避免 window 直接依赖托盘

    # ---------- 会话侧栏 ----------

    def refresh_sessions(self):
        groups = self.store.get(force_refresh=True)
        self._render_sessions(groups)

    def _render_sessions(self, groups):
        self.session_area.clear()

        if not groups:
            tk.Label(
                self.session_area.content,
                text="还没有会话记录\n\n在任意目录启动 Claude Code 后会出现在这里",
                font=("Segoe UI", 8), bg=self.colors["bg"], fg=self.colors["ink_3"],
                justify=tk.LEFT, anchor=tk.W, wraplength=SIDEBAR_WIDTH - 30,
            ).pack(fill=tk.X, padx=10, pady=14)
            self.session_header.set_count(0)
            self.session_area.refresh_scrollregion()
            return

        total = sum(len(sessions) for _path, sessions in groups)
        self.session_header.set_count(total)

        for project_path, sessions in groups:
            group = FolderGroupRow(
                self.session_area.content,
                project_path,
                sessions,
                self.colors,
                on_select=self.select_session,
                on_resume=self.resume_session,
                on_delete=self.delete_session,
                on_double_click=self.open_mode_dialog,
                on_toggle=self._on_group_toggle,
                expanded=project_path not in self.collapsed_projects,
            )
            group.pack(fill=tk.X, pady=(2, 0))
            if self.selected_session_id:
                group.set_child_selection(self.selected_session_id)

        self.session_area.refresh_scrollregion()

    def _on_group_toggle(self, project_path, expanded):
        """把用户手动折叠/展开的状态记下来，供下次渲染复用。"""
        if expanded:
            self.collapsed_projects.discard(project_path)
        else:
            self.collapsed_projects.add(project_path)

    def select_session(self, session):
        self.selected_session_id = session.get("id")
        project_path = session.get("cwd", "")
        if project_path:
            self.dir_var.set(project_path)
        self._highlight_selected()
        self.set_status("已选中：%s" % (session.get("prompt") or session.get("id", "")), "info")

    def _highlight_selected(self):
        for group in self.session_area.content.winfo_children():
            if isinstance(group, FolderGroupRow):
                group.set_child_selection(self.selected_session_id)

    def resume_session(self, session):
        project_path = session.get("cwd", "")
        session_id = session.get("id", "")
        try:
            agent.resume(project_path, session_id)
        except agent.LaunchError as exc:
            self._error(exc.message)
            return

        self.set_status("已恢复会话 %s" % session_id[:12], "success")
        self._after_launch()

    def delete_session(self, session):
        session_id = session.get("id", "")
        path = session.get("file", "")
        if not self._confirm("确认删除", "确定要删除这个会话吗？\n\n%s\n\n此操作不可撤销。" % session_id):
            return

        if self.store.remove(path):
            self.selected_session_id = None
            self._render_sessions(self.store.get())
            self.set_status("已删除会话 %s" % session_id[:12], "success")
        else:
            self.set_status("删除失败：文件不存在", "error")

    def open_mode_dialog(self, project_path):
        def on_choose(mode_id):
            self.dir_var.set(project_path)
            self.launch(mode_id)

        dialogs.ModeDialog(self.root, project_path, self.colors, on_choose)

    # ---------- 收藏夹 ----------

    def refresh_favorites(self):
        self.favorite_area.clear()
        favorites = list(self.config.get("favorites", []))
        self.favorite_header.set_count(len(favorites))

        if not favorites:
            tk.Label(
                self.favorite_area.content,
                text="还没有收藏。选中目录后点 ☆ 添加。",
                font=("Segoe UI", 8), bg=self.colors["surface"],
                fg=self.colors["ink_3"], anchor=tk.W,
            ).pack(fill=tk.X, pady=6)
        else:
            for path in favorites:
                FavoriteRow(
                    self.favorite_area.content, path, self.colors,
                    on_open=self.open_path_in_explorer,
                    on_launch=self.launch_from_path,
                    on_remove=self.remove_favorite,
                ).pack(fill=tk.X, pady=(0, 4))

        self.favorite_area.refresh_scrollregion()

    def toggle_favorite(self):
        path = self.dir_var.get().strip()
        if not path:
            self.set_status("请先选择一个目录", "warning")
            return

        favorites = list(self.config.get("favorites", []))
        if path in favorites:
            favorites.remove(path)
            self.set_status("已取消收藏", "info")
        else:
            favorites.insert(0, path)
            favorites = favorites[:MAX_FAVORITES]
            self.set_status("已加入收藏夹", "success")

        self.config.set("favorites", favorites)
        self.config.save()
        self.refresh_favorites()
        self._update_current_card()

    def add_to_favorites(self):
        self.toggle_favorite()

    def remove_favorite(self, path):
        if not self._confirm("确认", "确定要从收藏夹移除吗？\n\n%s" % path):
            return
        favorites = [p for p in self.config.get("favorites", []) if p != path]
        self.config.set("favorites", favorites)
        self.config.save()
        self.refresh_favorites()
        self.set_status("已从收藏夹移除", "info")

    def launch_from_path(self, path):
        self.dir_var.set(path)
        self.launch()

    # ---------- 路径与卡片 ----------

    def browse_directory(self):
        from tkinter import filedialog

        chosen = filedialog.askdirectory(title="选择工作目录")
        if chosen:
            self.dir_var.set(os.path.normpath(chosen))

    def _on_path_change(self, *_args):
        if self.validation_job:
            self.root.after_cancel(self.validation_job)
        self.validation_job = self.root.after(150, self._validate_path)

    def _validate_path(self):
        self.validation_job = None
        path = self.dir_var.get().strip()

        if not path:
            self.path_state.config(text="")
            self._update_current_card()
            return

        if agent.is_valid_directory(path):
            self.path_state.config(text="✓ 可用", fg=self.colors["ok"])
        else:
            self.path_state.config(text="✕ 无效", fg=self.colors["danger"])

        self._update_current_card()

    def _update_current_card(self):
        path = self.dir_var.get().strip()
        favorites = self.config.get("favorites", [])
        self.favorite_button.set_icon("star_filled" if path in favorites else "star")

        if not path:
            self.current_name.config(text="未选择目录")
            self.current_path.config(text="输入或浏览选择一个项目目录")
            self.current_state.set("未选择", "neutral")
            return

        self.current_name.config(text=os.path.basename(path) or path)
        self.current_path.config(text=elide_path(path, 52))
        if agent.is_valid_directory(path):
            self.current_state.set("可用", "ok")
        else:
            self.current_state.set("无效", "danger")

    def open_in_explorer(self):
        self.open_path_in_explorer(self.dir_var.get().strip())

    def open_path_in_explorer(self, path):
        path = (path or "").strip()
        if not agent.is_valid_directory(path):
            self.set_status("目录不存在：%s" % path, "error")
            return
        try:
            subprocess.Popen(["explorer", path])
            self.set_status("已在资源管理器中打开", "success")
        except OSError as exc:
            self.set_status("打开资源管理器失败：%s" % exc, "error")

    # ---------- 启动 ----------

    def launch(self, mode=None):
        work_dir = self.dir_var.get().strip()
        selected = mode or self.config.get("last_mode", agent.DEFAULT_MODE)
        if selected not in agent.MODES:
            selected = agent.DEFAULT_MODE

        try:
            agent.launch(work_dir, selected)
        except agent.LaunchError as exc:
            self._error(exc.message)
            return

        self.config.set("last_mode", selected)
        self.config.save()
        self._update_current_card()
        self.set_status("已启动：%s" % work_dir, "success")
        self._after_launch()

    def _after_launch(self):
        if self.config.get("auto_close", True):
            self.on_launch_close()
        else:
            self.refresh_sessions()

    def on_launch_close(self):
        pass  # 由 app 层注入

    def open_settings(self):
        def on_theme_change(theme_id):
            self.config.set("theme", theme_id)
            self.config.save()
            self.rebuild_theme()

        def on_quit():
            self.on_quit_app()

        dialogs.SettingsDialog(
            self.root, self.config, self.colors, on_theme_change, on_quit,
        )

    def on_quit_app(self):
        pass  # 由 app 层注入

    def rebuild_theme(self):
        """主题切换是唯一走全量重建的路径——颜色写死在控件构造参数上。

        _build_path_bar 会创建全新的 dir_var，故必须先把用户已输入的路径
        存下来、重建后还原 —— 否则切一次主题就把用户的工作目录清空了。
        （collapsed_projects 只在 __init__ 里初始化，不经骨架重建，故不受影响。）
        """
        current_dir = self.dir_var.get()

        self.colors = theme.resolve(self.config.get("theme", "auto"))
        self.root.configure(bg=self.colors["bg"])
        for child in self.root.winfo_children():
            child.destroy()
        self._build_skeleton()

        if current_dir:
            self.dir_var.set(current_dir)
        self.refresh_sessions()
        self.refresh_favorites()
        self._update_current_card()

    # ---------- 状态与提示 ----------

    def set_status(self, message, tone="info"):
        color = {
            "info": self.colors["ink_3"],
            "success": self.colors["ok"],
            "error": self.colors["danger"],
            "warning": self.colors["accent"],
        }.get(tone, self.colors["ink_3"])
        self.status_label.config(text=message, fg=color)

    def _error(self, message):
        from tkinter import messagebox

        messagebox.showerror("Claude Launcher", message)
        self.set_status(message.split("\n")[0], "error")

    def _confirm(self, title, message):
        from tkinter import messagebox

        return messagebox.askyesno(title, message)
