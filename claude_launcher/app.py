"""应用装配：单实例锁、托盘、顶层异常兜底。"""

import socket
import threading
import tkinter as tk
from tkinter import messagebox

from . import theme
from .config import Config
from .sessions import SessionStore
from .ui.window import MainWindow

LOCK_PORT = 58432
ACTIVATE_MESSAGE = b"SHOW"


class SingleInstance:
    """用回环端口做互斥锁。

    若端口被占用，先尝试唤醒已有实例；唤醒失败说明占用者不是本程序，
    此时返回 False 但由调用方决定是否继续——静默退出会让用户双击无反应。
    """

    def __init__(self, port=LOCK_PORT):
        self.port = port
        self.socket = None
        self.owns_lock = False

    def acquire(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(("127.0.0.1", self.port))
            self.socket.listen(1)
            self.owns_lock = True
            return True
        except socket.error:
            self.socket = None
            self.owns_lock = False
            return False

    def is_taken_by_another(self):
        """尝试连接已占端口的进程。连上并收到响应说明是本程序的另一个实例。"""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(0.5)
            client.connect(("127.0.0.1", self.port))
            client.send(ACTIVATE_MESSAGE)
            client.close()
            return True
        except (socket.error, OSError):
            return False

    def release(self):
        self.owns_lock = False
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
            self.socket = None


class LauncherApp:
    """把纯逻辑层与界面层组装在一起，所有跨界回调在此注入。"""

    def __init__(self, root, single_instance):
        self.root = root
        self.single_instance = single_instance

        self.config = Config()
        self.config.load()
        self.store = SessionStore()
        self.tray = None

        root.withdraw()
        self.window = MainWindow(root, self.config, self.store)

        self.window.on_escape = self.minimize_to_tray
        self.window.on_launch_close = self.quit
        self.window.on_quit_app = self.quit

        self._center()
        self._setup_tray()
        self._start_activation_listener()

        root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        root.deiconify()

    def _center(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry("%dx%d+%d+%d" % (width, height, x, y))

    def _setup_tray(self):
        try:
            from PIL import Image, ImageDraw
            from pystray import Icon, Menu, MenuItem
        except ImportError:
            return

        def tray_image():
            size = 64
            image = Image.new("RGB", (size, size), theme.resolve("dark")["bg"])
            draw = ImageDraw.Draw(image)
            accent = theme.resolve("dark")["accent"]
            draw.ellipse([14, 14, 50, 50], fill=accent)
            return image

        menu = Menu(
            MenuItem("显示窗口", lambda _icon, _item: self.root.after(0, self.show_window), default=True),
            MenuItem("设置", lambda _icon, _item: self.root.after(0, self.window.open_settings)),
            Menu.SEPARATOR,
            MenuItem("退出程序", lambda _icon, _item: self.root.after(0, self.quit)),
        )

        try:
            self.tray = Icon("Claude Launcher", tray_image(), "Claude Launcher", menu)
        except Exception:
            self.tray = None

    def _start_activation_listener(self):
        if not self.single_instance.owns_lock:
            return

        def poll():
            try:
                self.single_instance.socket.settimeout(0.05)
                connection, _address = self.single_instance.socket.accept()
                connection.recv(1024)
                connection.close()
                self.show_window()
            except socket.timeout:
                pass
            except OSError:
                return
            except Exception:
                pass

            self.root.after(100, poll)

        self.root.after(100, poll)

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def minimize_to_tray(self):
        if self.tray is None:
            self.root.iconify()
            return

        self.root.withdraw()
        if not self.tray.visible:
            threading.Thread(target=self.tray.run, daemon=True).start()

    def quit(self):
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.single_instance.release()
        self.root.quit()
        self.root.destroy()


def main():
    single_instance = SingleInstance()

    if not single_instance.acquire():
        if single_instance.is_taken_by_another():
            return
        # 端口被别的程序占用，无法做互斥——告知用户后仍继续启动，
        # 静默退出会让双击图标看起来毫无反应。
        try:
            probe = tk.Tk()
            probe.withdraw()
            messagebox.showwarning(
                "Claude Launcher",
                "端口 %d 被其他程序占用，无法限制单实例。\n\n"
                "程序会继续启动，但可能同时运行多个窗口。" % LOCK_PORT,
            )
            probe.destroy()
        except tk.TclError:
            pass

    root = tk.Tk()
    app = None

    try:
        app = LauncherApp(root, single_instance)
        root.mainloop()
    except Exception as exc:
        import traceback

        traceback.print_exc()
        try:
            messagebox.showerror(
                "Claude Launcher 启动失败",
                "程序遇到未处理的错误：\n\n%s\n\n详情已输出到标准错误。" % exc,
            )
        except Exception:
            pass
        raise
    finally:
        if app is not None:
            try:
                app.quit()
            except Exception:
                pass
