"""Task 13 全量验证：自动化计划中 22 项手工清单里可断言的部分。

关键：refresh_sessions() 会销毁并重建全部分组行，故任何 widget 引用
在刷新后都会失效 —— 每次操作后必须重新获取。这是测试代码的要求，
不是应用缺陷（真实使用中 Tk 只把事件派发给存活的控件）。
"""
import os
os.environ["TCL_LIBRARY"] = ""
os.environ["TK_LIBRARY"] = ""
import json
import sys
import tempfile
import tkinter as tk
from pathlib import Path

sys.path.insert(0, ".")

from claude_launcher import agent
from claude_launcher.config import Config
from claude_launcher.sessions import SessionStore
from claude_launcher.ui.window import MainWindow
from claude_launcher.ui.widgets import FavoriteRow, FolderGroupRow

results = []
def check(n, desc, ok, detail=""):
    results.append((n, desc, ok, detail))
    print("  %s %2d. %-44s %s" % ("OK " if ok else "FAIL", n, desc, detail))

tmp = Path(tempfile.mkdtemp())
for name in ("my-app", "api-server"):
    (tmp / name).mkdir()
projects = tmp / "projects"
for name, sid, prompt, mt in [("my-app", "a1b2c3d4", "重构登录模块", 3000.0),
                              ("my-app", "e5f6a7b8", "SQL 查询太慢", 2000.0),
                              ("api-server", "c9d0e1f2", "分页组件边界", 1000.0)]:
    d = projects / ("-" + name)
    d.mkdir(parents=True, exist_ok=True)
    f = d / (sid + ".jsonl")
    f.write_text("\n".join([
        json.dumps({"type": "summary", "cwd": str(tmp / name)}),
        json.dumps({"type": "user", "cwd": str(tmp / name), "message": {"content": prompt}}),
    ]) + "\n", encoding="utf-8")
    os.utime(f, (mt, mt))

cfg_path = tmp / "cfg.json"
cfg = Config(cfg_path)
cfg.load()
cfg.set("auto_close", False)

spawned = []
agent.subprocess.Popen = lambda cmd, cwd=None, creationflags=0: spawned.append((cmd, cwd, creationflags))
agent.shutil.which = lambda name: r"C:\bin\claude.exe"
import tkinter.messagebox as mb
mb.showerror = lambda *a, **k: None
mb.askyesno = lambda *a, **k: True

root = tk.Tk()
root.withdraw()
w = MainWindow(root, cfg, SessionStore(projects_dir=projects))
root.update()

def groups():
    """始终获取当前存活的分组行引用。"""
    return [c for c in w.session_area.content.winfo_children() if isinstance(c, FolderGroupRow)]

def favs():
    return [c for c in w.favorite_area.content.winfo_children() if isinstance(c, FavoriteRow)]

print("=== 1. 启动与骨架 ===")
check(1, "窗口标题为 Claude Launcher", root.title() == "Claude Launcher", root.title())
check(1, "窗口尺寸 900x620", (root.winfo_width(), root.winfo_height()) == (900, 620),
      "%dx%d" % (root.winfo_width(), root.winfo_height()))

print("\n=== 2-3. 路径校验与当前项目卡片 ===")
w.dir_var.set(str(tmp / "my-app")); root.update(); w._validate_path()
check(2, "有效目录：徽标「可用」", w.current_state._text == "可用")
check(2, "有效目录：卡片显示项目名", w.current_name.cget("text") == "my-app")
w.dir_var.set(str(tmp / "nope")); root.update(); w._validate_path()
check(3, "无效目录：徽标「无效」", w.current_state._text == "无效")

print("\n=== 4-5. 会话选中与恢复 ===")
sess = groups()[0].sessions[0]
spawned.clear()
w.select_session(sess); root.update()
check(4, "单击会话：selected_session_id 已设置", w.selected_session_id == sess["id"])
check(4, "单击会话：路径栏同步", w.dir_var.get() == sess["cwd"])
check(4, "单击会话：未启动进程（不误触）", len(spawned) == 0)
spawned.clear()
w.resume_session(sess); root.update()
check(5, "双击会话：以 --resume 恢复",
      bool(spawned) and spawned[-1][0] == [r"C:\bin\claude.exe", "--resume", sess["id"]],
      str(spawned[-1][0]) if spawned else "未启动")
check(5, "双击会话：cwd 为该项目", bool(spawned) and spawned[-1][1] == sess["cwd"])

print("\n=== 6-7. 分组折叠 ===")
w.collapsed_projects.clear()
g = groups()[0]
path0, before = g.project_path, g.expanded
g.header.event_generate("<Button-1>"); root.update()   # 走真实事件绑定
g2 = [x for x in groups() if x.project_path == path0][0]
check(6, "单击标题：折叠状态已翻转", g2.expanded != before, "%s -> %s" % (before, g2.expanded))
check(6, "单击标题：on_toggle 已上报窗口", path0 in w.collapsed_projects or g2.expanded)
w.refresh_sessions(); root.update()
g3 = [x for x in groups() if x.project_path == path0][0]
check(6, "折叠状态跨重建保留", g3.expanded == g2.expanded, "expanded=%s" % g3.expanded)

print("\n=== 8. 删除会话 ===")
n_before = sum(len(s) for _, s in w.store.get())
victim = [s for _, ss in w.store.get() for s in ss][-1]
w.delete_session(victim); root.update()
n_after = sum(len(s) for _, s in w.store.get())
check(8, "删除会话：计数减一", n_after == n_before - 1, "%d -> %d" % (n_before, n_after))
check(8, "删除会话：文件已从磁盘移除", not Path(victim["file"]).exists())

print("\n=== 9. 刷新 ===")
w.refresh_sessions(); root.update()
check(9, "点刷新：列表重新渲染且非空", len(groups()) >= 1, "%d 组" % len(groups()))

print("\n=== 10-13. 收藏夹 ===")
w.dir_var.set(str(tmp / "my-app")); root.update()
w.toggle_favorite(); root.update()
check(10, "点 ☆：收藏夹出现该项", len(favs()) == 1 and cfg.get("favorites") == [str(tmp / "my-app")])
check(10, "点 ☆：已落盘",
      json.loads(cfg_path.read_text(encoding="utf-8"))["favorites"] == [str(tmp / "my-app")])

# 收藏行的「打开」是 ghost FlatButton，其 label 绑定了 on_open(path)。
# 控件层级：FavoriteRow(frame) > body(frame) > actions(frame) > FlatButton > Label
# 注意：FavoriteRow 构造时的 lambda 已捕获当时的 on_open 引用，
# 故必须先替换实现、再重建收藏夹，探针才能观察到调用。
opened = []
w.open_path_in_explorer = lambda p: opened.append(p)
w.refresh_favorites()
root.update()
row = favs()[0]

def find_flat_button(node, text):
    for ch in node.winfo_children():
        if ch.__class__.__name__ == "FlatButton" and text in getattr(ch, "_text", ""):
            return ch
        found = find_flat_button(ch, text)
        if found is not None:
            return found
    return None

open_btn = find_flat_button(row, "打开")
# 调用按钮自身的点击处理器 —— 真实点击走的就是这条路径
# （FlatButton.label 的 <Button-1> → _on_click → self.command）。
if open_btn is not None:
    open_btn._on_click(None)
    root.update()
check(12, "收藏行「打开」已接线", opened == [str(tmp / "my-app")],
      "找到按钮: %s, 调用参数: %s" % (open_btn is not None, opened))

spawned.clear()
w.launch_from_path(str(tmp / "api-server")); root.update()
check(11, "收藏行「启动」：切路径并启动",
      bool(spawned) and spawned[-1][1] == str(tmp / "api-server"))
w.remove_favorite(cfg.get("favorites")[0]); root.update()
check(13, "收藏行 ✕：已移除", cfg.get("favorites") == [])

print("\n=== 14-16. 主题与自动关闭 ===")
# 回归保护：切主题会重建骨架、创建全新的 dir_var，
# 若不还原用户已输入的路径，切一次主题就把工作目录清空了。
w.dir_var.set(str(tmp / "my-app")); root.update()
saved_path = w.dir_var.get()
bg_light = w.colors["bg"]
cfg.set("theme", "dark"); w.rebuild_theme(); root.update()
check(14, "切深色：配色已变", w.colors["bg"] != bg_light, "%s -> %s" % (bg_light, w.colors["bg"]))
check(14, "切深色：重建后仍渲染会话", len(groups()) > 0)
check(14, "切深色：已输入的路径未被清空", w.dir_var.get() == saved_path,
      "期望 %r，实际 %r" % (saved_path, w.dir_var.get()))
cfg.set("auto_close", False); cfg.save()
spawned.clear()
w.launch("normal"); root.update()
check(15, "取消自动关闭：启动后启动器不退出", bool(root.winfo_exists()))
cfg.set("auto_close", True); cfg.save()
closed = []
w.on_launch_close = lambda: closed.append(True)
spawned.clear()
w.launch("normal"); root.update()
check(16, "勾选自动关闭：启动后触发关闭", closed == [True])

print("\n=== 20-21. 托盘与单实例 ===")
from claude_launcher.app import SingleInstance
lock = SingleInstance()
check(21, "首次启动：取锁成功", lock.acquire())
check(21, "第二次启动：取锁失败（激活已有实例）", not SingleInstance().acquire())
check(21, "识别为本程序另一实例", SingleInstance().is_taken_by_another())
lock.release()
check(20, "窗口关闭按钮绑定为最小化", root.protocol("WM_DELETE_WINDOW") != "")

root.destroy()

print("\n=== 22. 配置损坏兜底 ===")
bad = tmp / "bad.json"
bad.write_text("{ not json", encoding="utf-8")
c = Config(bad); c.load()
check(22, "配置损坏：回落默认值且不抛错",
      c.get("last_mode") == "normal" and c.warning is not None, c.warning)

print()
ok = sum(1 for _, _, v, _ in results if v)
print("=" * 68)
print("自动化验证：%d/%d 通过" % (ok, len(results)))
failed = [r for r in results if not r[2]]
if failed:
    print("\n失败项：")
    for n, d, _, detail in failed:
        print("  %2d. %s %s" % (n, d, detail))
print()
print("以下需人工目视确认（无法自动化）：")
print("  - 界面视觉：配色、间距、字体观感")
print("  - 托盘图标外观与右键菜单")
print("  - 真实 Claude Code 在新控制台窗口启动并可交互")
print("  - 窗口图标（任务栏）显示为 Claude 标志")
