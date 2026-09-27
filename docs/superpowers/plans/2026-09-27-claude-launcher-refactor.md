# Claude Launcher 重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 2184 行单文件 `claude_launcher.py` 重构为 `claude_launcher/` 包，移除 Codex/MiMo 支持，修复 5 个 Bug，并把界面重做为 Claude 品牌配色的左右分栏布局。

**Architecture:** 按「是否依赖 tkinter / 是否碰文件系统」切分模块。`config.py`、`sessions.py`、`agent.py` 是纯逻辑层，不 import tkinter，可脱离界面单测；`theme.py` 只产出配色字典；`ui/` 之下只依赖 theme 与传入数据。界面骨架构建一次，会话侧栏与收藏夹各自独立容器、按需局部重建；会话扫描结果内存缓存。

**Tech Stack:** Python 3.7+、tkinter（标准库）、pystray + Pillow（仅托盘）、pytest（测试，新增）

**Spec:** `docs/superpowers/specs/2026-09-27-claude-launcher-refactor-design.md`

## Global Constraints

- Python 版本下限 3.7：不使用 walrus 以外的 3.8+ 语法糖中的 `match`、`X | Y` 类型联合、`dict |` 合并；类型标注用 `typing` 模块（`List`、`Dict`、`Optional`）
- 运行时依赖仅限标准库 + `pystray>=0.19.0` + `Pillow>=9.0.0`；不引入第三方 UI 库
- 不使用 emoji 作为界面图标（跨 Windows 版本渲染不一致、无法控色）；所有图标由 Canvas 手绘
- 配色一律取自 spec 第 5.2 节的 token 表，不新增色值；强调色固定 `#d97757`，深浅模式共用
- 卡片与容器使用直角 + 1px 描边；仅按钮与徽标可用 Canvas 圆角
- 所有界面文案为简体中文
- 配置文件路径不变：`%USERPROFILE%\.claude_launcher_config.json`
- 会话分组键必须是 jsonl 内提取的真实 `cwd`，不是 `~/.claude/projects` 下的目录名
- 测试运行前必须清空 `TCL_LIBRARY` 与 `TK_LIBRARY`（本机这两个变量被污染，指向失效的 PyInstaller 临时目录），否则 `tkinter.Tk()` 抛 `TclError`

---

## File Structure

| 文件 | 职责 |
|---|---|
| `main.py` | 薄入口，仅调用 `claude_launcher.app.main()` |
| `claude_launcher/__init__.py` | 版本号与包标记 |
| `claude_launcher/config.py` | 配置读写、schema 校验、旧版迁移 |
| `claude_launcher/theme.py` | `auto/light/dark` → 配色字典 |
| `claude_launcher/sessions.py` | 会话扫描 + 内存缓存 |
| `claude_launcher/agent.py` | 命令解析、启动命令构建、进程启动 |
| `claude_launcher/app.py` | 应用装配、单实例锁、顶层异常处理、mainloop |
| `claude_launcher/ui/__init__.py` | 包标记 |
| `claude_launcher/ui/icons.py` | Canvas 手绘图标 + Claude 标志位图 |
| `claude_launcher/ui/widgets.py` | `FlatButton`、`IconButton`、`Pill`、`SessionRow`、`FavoriteRow` |
| `claude_launcher/ui/dialogs.py` | `SettingsDialog`、`ModeDialog` |
| `claude_launcher/ui/window.py` | `MainWindow`：骨架 + 动态区域编排 |
| `assets/claude_icon.ico` | 窗口与任务栏图标（自根目录移入） |
| `assets/claude-mark.png` | Claude 标志（抠底版，新增） |
| `tests/test_config.py` | 配置层测试 |
| `tests/test_sessions.py` | 会话扫描测试 |
| `tests/test_agent.py` | 命令构建测试 |
| `tests/test_theme.py` | 配色 token 完整性测试 |

任务顺序：先建纯逻辑层（1-4，全部可单测），再建资源与图标（5），再建控件（6-7），再建对话框（8），最后组装窗口（9）与入口（10），收尾清理（11-12）。

---

### Task 1: 包骨架与入口

**Files:**
- Create: `main.py`
- Create: `claude_launcher/__init__.py`
- Create: `claude_launcher/ui/__init__.py`
- Create: `pytest.ini`
- Modify: `.gitignore` (添加 pytest 缓存)

**Interfaces:**
- Consumes: 无
- Produces: 包 `claude_launcher`，版本号 `claude_launcher.__version__`

- [ ] **Step 1: 创建包骨架**

`claude_launcher/__init__.py`:

```python
"""Claude Launcher —— Windows 上的 Claude Code 工作区启动器。"""

__version__ = "2.1.0"
```

`claude_launcher/ui/__init__.py`:

```python
"""界面层：只依赖 theme 与传入数据，不直接读写文件系统。"""
```

- [ ] **Step 2: 创建 pytest 配置**

`pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
```

- [ ] **Step 3: 添加 pytest 缓存到 .gitignore**

在 `.gitignore` 末尾追加：

```
# Test cache
.pytest_cache/
```

- [ ] **Step 4: 创建临时入口并验证包可导入**

`main.py` 先写最小可运行版本，Task 10 会替换为完整入口：

```python
"""Claude Launcher 启动入口。"""

from claude_launcher import __version__

if __name__ == "__main__":
    print("Claude Launcher", __version__)
```

Run: `python main.py`
Expected: 输出 `Claude Launcher 2.1.0`

- [ ] **Step 5: Commit**

```bash
git add main.py claude_launcher/ pytest.ini .gitignore
git commit -m "feat: 建立 claude_launcher 包骨架与测试配置"
```

---

### Task 2: 配置层

**Files:**
- Create: `claude_launcher/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `Config(path)` —— `path` 为 `Path` 对象
  - `Config.load() -> None` 读盘并校验，损坏时回落默认值并设 `self.warning`
  - `Config.save() -> None` 写盘
  - `Config.get(key, default=None)` / `Config.set(key, value)`
  - 属性 `Config.warning: Optional[str]`
  - 常量 `SCHEMA`、`DEFAULT_PATH`

- [ ] **Step 1: 写失败的测试**

`tests/test_config.py`:

```python
import json
from pathlib import Path

import pytest

from claude_launcher.config import Config, DEFAULT_PATH


def write_config(tmp_path, payload):
    path = tmp_path / "cfg.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_default_path_is_home_config():
    assert DEFAULT_PATH == Path.home() / ".claude_launcher_config.json"


def test_missing_file_yields_defaults(tmp_path):
    cfg = Config(tmp_path / "nope.json")
    cfg.load()
    assert cfg.get("favorites") == []
    assert cfg.get("last_mode") == "normal"
    assert cfg.get("auto_close") is True
    assert cfg.get("theme") == "auto"
    assert cfg.warning is None


def test_corrupt_json_falls_back_with_warning(tmp_path):
    cfg = Config(write_config(tmp_path, "{ this is not json"))
    cfg.load()
    assert cfg.get("last_mode") == "normal"
    assert cfg.warning is not None


def test_non_dict_top_level_falls_back_with_warning(tmp_path):
    cfg = Config(write_config(tmp_path, "[1, 2, 3]"))
    cfg.load()
    assert cfg.get("theme") == "auto"
    assert cfg.warning is not None


def test_unknown_keys_are_dropped(tmp_path):
    cfg = Config(write_config(tmp_path, {
        "recent_dirs": ["D:\\old"],
        "agent": "codex",
        "favorites": ["D:\\proj"],
        "last_mode": "normal",
        "auto_close": True,
        "theme": "light",
    }))
    cfg.load()
    assert "recent_dirs" not in cfg.data
    assert "agent" not in cfg.data
    assert cfg.get("favorites") == ["D:\\proj"]


@pytest.mark.parametrize("legacy", ["yolo", "interactive", "run", "bogus"])
def test_legacy_last_mode_falls_back(tmp_path, legacy):
    cfg = Config(write_config(tmp_path, {"last_mode": legacy}))
    cfg.load()
    assert cfg.get("last_mode") == "normal"


def test_valid_last_mode_is_kept(tmp_path):
    cfg = Config(write_config(tmp_path, {"last_mode": "skip"}))
    cfg.load()
    assert cfg.get("last_mode") == "skip"


def test_bad_types_fall_back(tmp_path):
    cfg = Config(write_config(tmp_path, {
        "auto_close": "yes",
        "theme": "neon",
        "favorites": "not-a-list",
    }))
    cfg.load()
    assert cfg.get("auto_close") is True
    assert cfg.get("theme") == "auto"
    assert cfg.get("favorites") == []


def test_favorites_are_normalized_and_capped(tmp_path):
    many = ["D:\\p%d" % i for i in range(15)]
    cfg = Config(write_config(tmp_path, {"favorites": many + many}))
    cfg.load()
    favs = cfg.get("favorites")
    assert len(favs) <= 10
    assert len(set(favs)) == len(favs)


def test_save_then_load_roundtrips(tmp_path):
    path = tmp_path / "cfg.json"
    cfg = Config(path)
    cfg.load()
    cfg.set("last_mode", "skip")
    cfg.set("favorites", ["D:\\proj"])
    cfg.save()

    again = Config(path)
    again.load()
    assert again.get("last_mode") == "skip"
    assert again.get("favorites") == ["D:\\proj"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest tests/test_config.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'claude_launcher.config'`

- [ ] **Step 3: 实现 config.py**

`claude_launcher/config.py`:

```python
"""配置读写：schema 校验、损坏兜底、旧版字段迁移。"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_PATH = Path.home() / ".claude_launcher_config.json"

VALID_MODES = ("normal", "skip")
VALID_THEMES = ("auto", "light", "dark")
MAX_FAVORITES = 10

SCHEMA: Dict[str, Any] = {
    "favorites": [],
    "last_mode": "normal",
    "auto_close": True,
    "theme": "auto",
}


def normalize_path(path: Any) -> str:
    """清理粘贴来的目录路径，兼容 Windows「复制为路径」的引号包裹。"""
    if not isinstance(path, str):
        return ""

    normalized = path.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in ("'", '"'):
        normalized = normalized[1:-1].strip()

    normalized = os.path.expandvars(os.path.expanduser(normalized))
    if not normalized:
        return ""

    return os.path.normpath(normalized)


class Config:
    """配置文件的门面。所有读写都经此对象，避免调用方各自处理异常。"""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path is not None else DEFAULT_PATH
        self.data: Dict[str, Any] = dict(SCHEMA)
        self.warning: Optional[str] = None

    def load(self) -> None:
        self.data = dict(SCHEMA)
        self.warning = None

        if not self.path.exists():
            return

        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except (OSError, json.JSONDecodeError):
            self.warning = "配置文件无法读取，已使用默认设置"
            return

        if not isinstance(loaded, dict):
            self.warning = "配置文件格式无效，已使用默认设置"
            return

        self._apply(loaded)
        self.save()

    def _apply(self, loaded: Dict[str, Any]) -> None:
        """只接受 schema 中已知的键，逐项做类型与取值校验。"""
        for key in SCHEMA:
            if key not in loaded:
                continue
            self.data[key] = loaded[key]

        self.data["favorites"] = self._clean_favorites(self.data.get("favorites"))

        if self.data.get("last_mode") not in VALID_MODES:
            self.data["last_mode"] = SCHEMA["last_mode"]
        if self.data.get("theme") not in VALID_THEMES:
            self.data["theme"] = SCHEMA["theme"]
        if not isinstance(self.data.get("auto_close"), bool):
            self.data["auto_close"] = SCHEMA["auto_close"]

    @staticmethod
    def _clean_favorites(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []

        cleaned: List[str] = []
        for item in value:
            normalized = normalize_path(item)
            if normalized and normalized not in cleaned:
                cleaned.append(normalized)

        return cleaned[:MAX_FAVORITES]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, ensure_ascii=False, indent=2)
        except OSError:
            self.warning = "配置无法写入，本次修改仅在内存中生效"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest tests/test_config.py -v`
Expected: 全部 PASS（13 个：10 个函数，其中 `test_legacy_last_mode_falls_back` 参数化展开为 4 个）

- [ ] **Step 5: Commit**

```bash
git add claude_launcher/config.py tests/test_config.py
git commit -m "feat: 配置层支持 schema 校验与旧版字段迁移"
```

---

### Task 3: 配色层

**Files:**
- Create: `claude_launcher/theme.py`
- Test: `tests/test_theme.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `resolve(theme: str, system_theme: Optional[str] = None) -> Dict[str, str]`
  - `detect_system_theme() -> str` —— 返回 `"light"` 或 `"dark"`，非 Windows 或失败时返回 `"dark"`
  - token 名称：`bg`、`surface`、`sunken`、`line`、`line_strong`、`ink`、`ink_2`、`ink_3`、`accent`、`accent_hi`、`accent_soft`、`ok`、`ok_soft`、`danger`、`danger_bg`、`hover`

- [ ] **Step 1: 写失败的测试**

`tests/test_theme.py`:

```python
import pytest

from claude_launcher.theme import detect_system_theme, resolve

REQUIRED_TOKENS = {
    "bg", "surface", "sunken", "line", "line_strong",
    "ink", "ink_2", "ink_3",
    "accent", "accent_hi", "accent_soft",
    "ok", "ok_soft", "danger", "danger_bg", "hover",
}


@pytest.mark.parametrize("name", ["light", "dark"])
def test_every_token_present(name):
    colors = resolve(name)
    assert REQUIRED_TOKENS <= set(colors)


def test_accent_is_claude_orange_in_both_themes():
    assert resolve("light")["accent"] == "#d97757"
    assert resolve("dark")["accent"] == "#d97757"


def test_light_and_dark_differ():
    assert resolve("light")["bg"] != resolve("dark")["bg"]


def test_auto_follows_system():
    assert resolve("auto", system_theme="light")["bg"] == resolve("light")["bg"]
    assert resolve("auto", system_theme="dark")["bg"] == resolve("dark")["bg"]


def test_unknown_theme_falls_back_to_dark():
    assert resolve("neon")["bg"] == resolve("dark")["bg"]


def test_detect_returns_valid_value():
    assert detect_system_theme() in ("light", "dark")


def test_all_values_are_strings():
    for name in ("light", "dark"):
        for token, value in resolve(name).items():
            assert isinstance(value, str), token
            assert value, token
```

- [ ] **Step 2: 运行测试确认失败**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest tests/test_theme.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'claude_launcher.theme'`

- [ ] **Step 3: 实现 theme.py**

`claude_launcher/theme.py`:

```python
"""配色 token。灰阶一律偏暖，强调色取自 Claude 品牌（#d97757）。"""

from typing import Dict, Optional

LIGHT: Dict[str, str] = {
    "bg": "#efede4",
    "surface": "#faf9f5",
    "sunken": "#e6e3d7",
    "hover": "#e6e3d7",
    "line": "#e0ddd2",
    "line_strong": "#cdc9bc",
    "ink": "#1f1e1b",
    "ink_2": "#6b6862",
    "ink_3": "#9b978e",
    "accent": "#d97757",
    "accent_hi": "#c4633f",
    "accent_soft": "#f4e4dd",
    "ok": "#4f7d5c",
    "ok_soft": "#e2eae2",
    "danger": "#b5533f",
    "danger_bg": "#f6e4df",
}

DARK: Dict[str, str] = {
    "bg": "#262624",
    "surface": "#30302e",
    "sunken": "#3a3937",
    "hover": "#3a3937",
    "line": "#3d3c39",
    "line_strong": "#52504b",
    "ink": "#f5f4ef",
    "ink_2": "#b0aca3",
    "ink_3": "#7f7b73",
    "accent": "#d97757",
    "accent_hi": "#e89075",
    "accent_soft": "#463029",
    "ok": "#7fa98a",
    "ok_soft": "#2f3b32",
    "danger": "#d97b65",
    "danger_bg": "#452b26",
}


def detect_system_theme() -> str:
    """读注册表判断 Windows 应用主题；非 Windows 或读取失败时按深色处理。"""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if value == 1 else "dark"
    except Exception:
        return "dark"


def resolve(theme: str, system_theme: Optional[str] = None) -> Dict[str, str]:
    if theme == "light":
        return dict(LIGHT)
    if theme == "dark":
        return dict(DARK)
    if theme == "auto":
        current = system_theme or detect_system_theme()
        return dict(LIGHT if current == "light" else DARK)

    return dict(DARK)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest tests/test_theme.py -v`
Expected: 全部 PASS（8 个：6 个函数，其中 `test_every_token_present` 参数化展开为 2 个）

- [ ] **Step 5: Commit**

```bash
git add claude_launcher/theme.py tests/test_theme.py
git commit -m "feat: 添加 Claude 品牌配色层"
```

---

### Task 4: 会话扫描层

**Files:**
- Create: `claude_launcher/sessions.py`
- Test: `tests/test_sessions.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `SessionStore(projects_dir: Optional[Path] = None)`
  - `SessionStore.get(force_refresh: bool = False) -> List[Tuple[str, List[dict]]]` —— 返回 `[(项目路径, [会话])]`，按最新会话时间倒序
  - `SessionStore.remove(session_file: str) -> bool` —— 从缓存移除并从磁盘删除
  - `SessionStore.projects_dir` 属性
  - 会话 dict 键：`id`、`file`、`mtime`、`size`、`prompt`、`cwd`
  - 常量 `MAX_SESSIONS_PER_PROJECT = 10`、`MAX_PROJECTS = 20`、`PROMPT_LIMIT = 80`

- [ ] **Step 1: 写失败的测试**

`tests/test_sessions.py`:

```python
import json
import os
from pathlib import Path

from claude_launcher.sessions import (
    MAX_PROJECTS,
    MAX_SESSIONS_PER_PROJECT,
    SessionStore,
    extract_cwd,
    extract_first_prompt,
)


def make_session(projects_dir, encoded_name, session_id, cwd, prompt, mtime=1000.0):
    """写出一个仿真的 Claude Code 会话文件。"""
    project_dir = projects_dir / encoded_name
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / (session_id + ".jsonl")

    lines = [
        json.dumps({"type": "summary", "cwd": cwd}),
        json.dumps({
            "type": "user",
            "cwd": cwd,
            "message": {"content": prompt},
        }),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path


def test_extract_cwd_reads_first_cwd_field(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        json.dumps({"type": "user", "cwd": "D:\\proj"}) + "\n",
        encoding="utf-8",
    )
    assert extract_cwd(str(path)) == "D:\\proj"


def test_extract_cwd_skips_corrupt_lines(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        "not json\n" + json.dumps({"cwd": "D:\\good"}) + "\n",
        encoding="utf-8",
    )
    assert extract_cwd(str(path)) == "D:\\good"


def test_extract_cwd_missing_file_returns_empty(tmp_path):
    assert extract_cwd(str(tmp_path / "gone.jsonl")) == ""


def test_extract_prompt_from_string_content(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        json.dumps({"type": "user", "message": {"content": "重构登录模块"}}) + "\n",
        encoding="utf-8",
    )
    assert extract_first_prompt(str(path)) == "重构登录模块"


def test_extract_prompt_from_block_list(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        json.dumps({
            "type": "user",
            "message": {"content": [{"type": "text", "text": "修复分页组件"}]},
        }) + "\n",
        encoding="utf-8",
    )
    assert extract_first_prompt(str(path)) == "修复分页组件"


def test_extract_prompt_is_truncated(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        json.dumps({"type": "user", "message": {"content": "x" * 500}}) + "\n",
        encoding="utf-8",
    )
    assert len(extract_first_prompt(str(path))) == 80


def test_extract_prompt_skips_non_user_entries(tmp_path):
    path = tmp_path / "s.jsonl"
    lines = [
        json.dumps({"type": "assistant", "message": {"content": "hi"}}),
        json.dumps({"type": "user", "message": {"content": "真正的问题"}}),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert extract_first_prompt(str(path)) == "真正的问题"


def test_scan_groups_by_real_cwd(tmp_path):
    projects = tmp_path / "projects"
    real = tmp_path / "real-project"
    real.mkdir()
    make_session(projects, "-D-real-project", "aaa", str(real), "第一个问题")

    store = SessionStore(projects_dir=projects)
    groups = store.get()

    assert len(groups) == 1
    project_path, sessions = groups[0]
    assert project_path == str(real)
    assert sessions[0]["id"] == "aaa"
    assert sessions[0]["prompt"] == "第一个问题"


def test_sessions_with_missing_cwd_are_skipped(tmp_path):
    projects = tmp_path / "projects"
    make_session(projects, "-D-gone", "bbb", str(tmp_path / "does-not-exist"), "问题")

    store = SessionStore(projects_dir=projects)
    assert store.get() == []


def test_sessions_sorted_newest_first(tmp_path):
    projects = tmp_path / "projects"
    real = tmp_path / "proj"
    real.mkdir()
    make_session(projects, "-D-proj", "old", str(real), "旧", mtime=1000.0)
    make_session(projects, "-D-proj", "new", str(real), "新", mtime=5000.0)

    store = SessionStore(projects_dir=projects)
    _, sessions = store.get()[0]
    assert sessions[0]["id"] == "new"


def test_per_project_session_cap(tmp_path):
    projects = tmp_path / "projects"
    real = tmp_path / "proj"
    real.mkdir()
    for i in range(MAX_SESSIONS_PER_PROJECT + 5):
        make_session(projects, "-D-proj", "s%02d" % i, str(real), "p%d" % i, mtime=1000.0 + i)

    store = SessionStore(projects_dir=projects)
    _, sessions = store.get()[0]
    assert len(sessions) == MAX_SESSIONS_PER_PROJECT


def test_project_cap(tmp_path):
    projects = tmp_path / "projects"
    for i in range(MAX_PROJECTS + 5):
        real = tmp_path / ("proj%02d" % i)
        real.mkdir()
        make_session(projects, "-D-proj%02d" % i, "s%d" % i, str(real), "p", mtime=1000.0 + i)

    store = SessionStore(projects_dir=projects)
    assert len(store.get()) == MAX_PROJECTS


def test_cache_avoids_rescanning(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    real = tmp_path / "proj"
    real.mkdir()
    make_session(projects, "-D-proj", "aaa", str(real), "问题")

    store = SessionStore(projects_dir=projects)
    store.get()

    calls = []
    real_listdir = os.listdir

    def counting_listdir(path):
        calls.append(path)
        return real_listdir(path)

    monkeypatch.setattr(os, "listdir", counting_listdir)
    store.get()
    assert calls == []


def test_force_refresh_rescans(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    real = tmp_path / "proj"
    real.mkdir()
    make_session(projects, "-D-proj", "aaa", str(real), "问题")

    store = SessionStore(projects_dir=projects)
    store.get()

    calls = []
    real_listdir = os.listdir

    def counting_listdir(path):
        calls.append(path)
        return real_listdir(path)

    monkeypatch.setattr(os, "listdir", counting_listdir)
    store.get(force_refresh=True)
    assert calls


def test_missing_projects_dir_returns_empty(tmp_path):
    store = SessionStore(projects_dir=tmp_path / "absent")
    assert store.get() == []


def test_remove_deletes_file_and_drops_from_cache(tmp_path):
    projects = tmp_path / "projects"
    real = tmp_path / "proj"
    real.mkdir()
    path = make_session(projects, "-D-proj", "aaa", str(real), "问题")

    store = SessionStore(projects_dir=projects)
    store.get()
    assert store.remove(str(path)) is True
    assert not path.exists()
    assert store.get() == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest tests/test_sessions.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'claude_launcher.sessions'`

- [ ] **Step 3: 实现 sessions.py**

`claude_launcher/sessions.py`:

```python
"""Claude Code 会话扫描。

会话文件位于 ~/.claude/projects/<路径转义目录>/<会话ID>.jsonl。
分组键取 jsonl 内记录的真实 cwd，而不是目录名——目录名是路径的转义形式，
不可逆且不便于展示。
"""

import json
import os
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"
MAX_SESSIONS_PER_PROJECT = 10
MAX_PROJECTS = 20
PROMPT_LIMIT = 80


def _read_json_lines(path: str):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def extract_cwd(jsonl_file: str) -> str:
    for obj in _read_json_lines(jsonl_file):
        if isinstance(obj, dict) and obj.get("cwd"):
            return obj["cwd"]
    return ""


def extract_first_prompt(jsonl_file: str) -> str:
    for obj in _read_json_lines(jsonl_file):
        if not isinstance(obj, dict) or obj.get("type") != "user":
            continue

        content = (obj.get("message") or {}).get("content", "")
        if isinstance(content, str) and content:
            return content[:PROMPT_LIMIT]

        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        return text[:PROMPT_LIMIT]
    return ""


class SessionStore:
    """会话列表的内存缓存。磁盘只在首次访问、强制刷新、删除时被触碰。"""

    def __init__(self, projects_dir: Optional[Path] = None):
        self.projects_dir = Path(projects_dir) if projects_dir else DEFAULT_PROJECTS_DIR
        self._cache: Optional[List[Tuple[str, List[Dict[str, Any]]]]] = None

    def get(self, force_refresh: bool = False) -> List[Tuple[str, List[Dict[str, Any]]]]:
        if self._cache is not None and not force_refresh:
            return self._cache

        self._cache = self._scan()
        return self._cache

    def remove(self, session_file: str) -> bool:
        """删除会话文件并从缓存摘除。缓存未建立时无需处理。"""
        try:
            os.remove(session_file)
        except OSError:
            return False

        if self._cache is None:
            return True

        groups: List[Tuple[str, List[Dict[str, Any]]]] = []
        for project_path, sessions in self._cache:
            remaining = [s for s in sessions if s.get("file") != session_file]
            if remaining:
                groups.append((project_path, remaining))

        self._cache = groups
        return True

    def _scan(self) -> List[Tuple[str, List[Dict[str, Any]]]]:
        groups: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()

        if not self.projects_dir.is_dir():
            return []

        try:
            entries = os.listdir(str(self.projects_dir))
        except OSError:
            return []

        candidates: List[Tuple[float, str, List[Dict[str, Any]]]] = []

        for entry in entries:
            project_dir = self.projects_dir / entry
            if not project_dir.is_dir():
                continue

            try:
                names = [n for n in os.listdir(str(project_dir)) if n.endswith(".jsonl")]
            except OSError:
                continue

            session_files = []
            for name in names:
                full = str(project_dir / name)
                try:
                    session_files.append((os.path.getmtime(full), full))
                except OSError:
                    continue

            session_files.sort(reverse=True)

            sessions: List[Dict[str, Any]] = []
            for mtime, full in session_files:
                if len(sessions) >= MAX_SESSIONS_PER_PROJECT:
                    break

                cwd = extract_cwd(full)
                if not cwd or not os.path.isdir(cwd):
                    continue

                try:
                    size = os.path.getsize(full)
                except OSError:
                    size = 0

                sessions.append({
                    "id": os.path.splitext(os.path.basename(full))[0],
                    "file": full,
                    "mtime": mtime,
                    "size": size,
                    "prompt": extract_first_prompt(full),
                    "cwd": cwd,
                })

            if sessions:
                candidates.append((sessions[0]["mtime"], sessions[0]["cwd"], sessions))

        candidates.sort(key=lambda item: item[0], reverse=True)

        for _, project_path, sessions in candidates[:MAX_PROJECTS]:
            groups[project_path] = sessions

        return list(groups.items())
```

- [ ] **Step 4: 运行测试确认通过**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest tests/test_sessions.py -v`
Expected: 全部 PASS（16 个测试）

- [ ] **Step 5: Commit**

```bash
git add claude_launcher/sessions.py tests/test_sessions.py
git commit -m "feat: 会话扫描支持真实 cwd 分组与内存缓存"
```

---

### Task 5: 命令解析与启动层

**Files:**
- Create: `claude_launcher/agent.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - 常量 `MODES: Dict[str, Dict[str, Any]]` —— 键为 `"normal"` / `"skip"`
  - `resolve_command() -> Optional[str]`
  - `build_command(mode: str, command: Optional[str] = None) -> Optional[List[str]]`
  - `launch(work_dir: str, mode: str) -> List[str]` —— 返回实际执行的命令，失败抛 `LaunchError`
  - `resume(work_dir: str, session_id: str) -> List[str]`
  - `is_valid_directory(path: str) -> bool`
  - 异常 `LaunchError(Exception)`，带 `message` 属性

- [ ] **Step 1: 写失败的测试**

`tests/test_agent.py`:

```python
import pytest

from claude_launcher import agent


def test_modes_has_exactly_two_entries():
    assert set(agent.MODES) == {"normal", "skip"}


def test_skip_mode_carries_permission_flag():
    assert agent.MODES["skip"]["args"] == ["--dangerously-skip-permissions"]


def test_normal_mode_has_no_extra_args():
    assert agent.MODES["normal"]["args"] == []


def test_build_command_returns_none_when_binary_missing(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: None)
    assert agent.build_command("normal") is None


def test_build_command_normal(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    assert agent.build_command("normal") == ["C:\\bin\\claude.exe"]


def test_build_command_skip_appends_flag(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    assert agent.build_command("skip") == [
        "C:\\bin\\claude.exe",
        "--dangerously-skip-permissions",
    ]


def test_build_command_unknown_mode_returns_none(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    assert agent.build_command("yolo") is None


def test_cmd_extension_is_wrapped_in_comspec(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.cmd")
    monkeypatch.setenv("COMSPEC", "C:\\Windows\\system32\\cmd.exe")
    cmd = agent.build_command("normal")
    assert cmd == ["C:\\Windows\\system32\\cmd.exe", "/c", "C:\\bin\\claude.cmd"]


def test_bat_extension_is_wrapped_in_comspec(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.bat")
    monkeypatch.setenv("COMSPEC", "C:\\Windows\\system32\\cmd.exe")
    assert agent.build_command("normal")[1] == "/c"


def test_is_valid_directory(tmp_path):
    assert agent.is_valid_directory(str(tmp_path)) is True
    assert agent.is_valid_directory(str(tmp_path / "absent")) is False
    assert agent.is_valid_directory("") is False


def test_launch_rejects_missing_directory(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    with pytest.raises(agent.LaunchError):
        agent.launch("D:\\definitely\\absent\\path", "normal")


def test_launch_rejects_missing_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: None)
    with pytest.raises(agent.LaunchError):
        agent.launch(str(tmp_path), "normal")


def test_launch_spawns_in_new_console(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    captured = {}

    def fake_popen(cmd, cwd=None, creationflags=0):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        return object()

    monkeypatch.setattr(agent.subprocess, "Popen", fake_popen)
    cmd = agent.launch(str(tmp_path), "normal")

    assert cmd == ["C:\\bin\\claude.exe"]
    assert captured["cwd"] == str(tmp_path)


def test_launch_falls_back_to_normal_for_unknown_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    monkeypatch.setattr(agent.subprocess, "Popen", lambda *a, **k: object())
    assert agent.launch(str(tmp_path), "yolo") == ["C:\\bin\\claude.exe"]


def test_resume_appends_session_id(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    captured = {}

    def fake_popen(cmd, cwd=None, creationflags=0):
        captured["cmd"] = cmd
        return object()

    monkeypatch.setattr(agent.subprocess, "Popen", fake_popen)
    cmd = agent.resume(str(tmp_path), "abc-123")

    assert cmd == ["C:\\bin\\claude.exe", "--resume", "abc-123"]
    assert captured["cmd"] == cmd


def test_resume_rejects_missing_directory(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    with pytest.raises(agent.LaunchError):
        agent.resume("D:\\absent\\nope", "abc")


def test_resume_without_session_id_omits_argument(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    monkeypatch.setattr(agent.subprocess, "Popen", lambda *a, **k: object())
    assert agent.resume(str(tmp_path), "") == ["C:\\bin\\claude.exe", "--resume"]


def test_launch_reports_install_hint_when_binary_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: None)
    with pytest.raises(agent.LaunchError) as excinfo:
        agent.launch(str(tmp_path), "normal")
    assert "npm install -g @anthropic-ai/claude-code" in excinfo.value.message
```

- [ ] **Step 2: 运行测试确认失败**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest tests/test_agent.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'claude_launcher.agent'`

- [ ] **Step 3: 实现 agent.py**

`claude_launcher/agent.py`:

```python
"""Claude Code 命令解析与进程启动。不依赖 tkinter。"""

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

COMMANDS = ["claude", "claude.exe", "claude.cmd"]

MODES: Dict[str, Dict[str, Any]] = {
    "normal": {
        "label": "普通启动",
        "desc": "标准权限确认流程",
        "args": [],
    },
    "skip": {
        "label": "跳过权限",
        "desc": "跳过权限提示，请仅在可信目录使用",
        "args": ["--dangerously-skip-permissions"],
    },
}

DEFAULT_MODE = "normal"
RESUME_ARGS = ["--resume"]
INSTALL_HINT = "npm install -g @anthropic-ai/claude-code"


class LaunchError(Exception):
    """启动前的校验失败。message 为面向用户的中文说明。"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def resolve_command() -> Optional[str]:
    for name in COMMANDS:
        found = shutil.which(name)
        if found:
            return found
    return None


def _wrap(command: str) -> List[str]:
    """.cmd/.bat 不能直接 Popen，需经 cmd.exe 解释。"""
    if command.lower().endswith((".cmd", ".bat")):
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", command]
    return [command]


def build_command(mode: str, command: Optional[str] = None) -> Optional[List[str]]:
    resolved = command or resolve_command()
    if not resolved:
        return None
    if mode not in MODES:
        return None

    return _wrap(resolved) + list(MODES[mode]["args"])


def is_valid_directory(path: str) -> bool:
    return bool(path) and os.path.isdir(path)


def _spawn(cmd: List[str], work_dir: str) -> None:
    try:
        subprocess.Popen(
            cmd,
            cwd=work_dir,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    except OSError as exc:
        raise LaunchError("启动失败：%s" % exc)


def _ensure_ready(work_dir: str) -> str:
    if not is_valid_directory(work_dir):
        raise LaunchError("目录不存在或不是文件夹：\n%s" % work_dir)

    if not resolve_command():
        raise LaunchError(
            "未找到 Claude Code 命令。\n\n请先安装：\n%s" % INSTALL_HINT
        )

    return work_dir


def launch(work_dir: str, mode: str) -> List[str]:
    _ensure_ready(work_dir)

    selected = mode if mode in MODES else DEFAULT_MODE
    cmd = build_command(selected)
    if not cmd:
        raise LaunchError("未找到 Claude Code 命令。\n\n请先安装：\n%s" % INSTALL_HINT)

    _spawn(cmd, work_dir)
    return cmd


def resume(work_dir: str, session_id: str) -> List[str]:
    _ensure_ready(work_dir)

    command = resolve_command()
    cmd = _wrap(command) + list(RESUME_ARGS)
    if session_id:
        cmd.append(session_id)

    _spawn(cmd, work_dir)
    return cmd
```

- [ ] **Step 4: 运行测试确认通过**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest tests/test_agent.py -v`
Expected: 全部 PASS（18 个测试）

- [ ] **Step 5: 全量测试确认无回归**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add claude_launcher/agent.py tests/test_agent.py
git commit -m "feat: 添加 Claude Code 命令解析与启动层"
```

---

### Task 6: 资源文件与图标绘制

**Files:**
- Create: `assets/claude-mark.png`（脚本生成）
- Move: `claude_icon.ico` → `assets/claude_icon.ico`
- Create: `claude_launcher/ui/icons.py`
- Create: `tools/make_mark.py`（一次性生成脚本，保留以便重跑）

**Interfaces:**
- Consumes: 无
- Produces:
  - `assets_dir() -> Path` —— 返回 `assets/` 绝对路径，兼容 PyInstaller 的 `sys._MEIPASS`
  - `claude_mark() -> Optional[tk.PhotoImage]` —— 懒加载并缓存，失败返回 `None`
  - `draw(canvas, name, color, size, x=0, y=0)` —— 在 Canvas 上绘制具名图标
  - 支持的 `name`：`folder`、`refresh`、`gear`、`play`、`bolt`、`star`、`star_filled`、`chevron_down`、`chevron_right`、`clock`、`plus`、`open_external`、`close`

- [ ] **Step 1: 生成抠底标志位图**

`tools/make_mark.py`:

```python
"""从 assets/claude_icon.ico 生成 assets/claude-mark.png。

原图标是暖橙星芒 + 不透明深青灰底。直接贴到奶油色界面上会出现色块，
因此按底色距离做带软边的抠图。Ray 边缘保留阿尔法渐变以免锯齿。
"""

import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "claude_icon.ico"
TARGET = ROOT / "assets" / "claude-mark.png"

SIZE = 256
BACKGROUND = (76, 105, 113)  # 源图标底色的实测值
HARD_CUTOFF = 40             # 距离小于此值视为纯背景
SOFT_CUTOFF = 110            # 介于两者之间做阿尔法渐变
OUTPUT_SIZE = 128


def main():
    image = Image.open(SOURCE)
    image.size = (SIZE, SIZE)
    image = image.convert("RGBA")

    source = image.load()
    result = Image.new("RGBA", image.size, (0, 0, 0, 0))
    target = result.load()

    for y in range(SIZE):
        for x in range(SIZE):
            r, g, b, _ = source[x, y]
            distance = math.sqrt(
                (r - BACKGROUND[0]) ** 2
                + (g - BACKGROUND[1]) ** 2
                + (b - BACKGROUND[2]) ** 2
            )

            if distance < HARD_CUTOFF:
                continue
            if distance < SOFT_CUTOFF:
                alpha = int(255 * (distance - HARD_CUTOFF) / (SOFT_CUTOFF - HARD_CUTOFF))
                target[x, y] = (r, g, b, alpha)
            else:
                target[x, y] = (r, g, b, 255)

    result = result.crop(result.getbbox())
    result = result.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)
    result.save(TARGET, "PNG", optimize=True)
    print("已写入 %s" % TARGET)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 移动图标并运行生成脚本**

```bash
mkdir -p assets
git mv claude_icon.ico assets/claude_icon.ico
python tools/make_mark.py
```

Expected: 输出 `已写入 .../assets/claude-mark.png`，且 `assets/claude-mark.png` 存在

- [ ] **Step 3: 验证位图有效**

```bash
python -c "from PIL import Image; im=Image.open('assets/claude-mark.png'); print(im.size, im.mode); print('corner alpha:', im.getpixel((0,0))[3])"
```

Expected: 尺寸约 128×128，mode 为 `RGBA`，左上角 alpha 为 0（背景已透明）

- [ ] **Step 4: 实现 icons.py**

`claude_launcher/ui/icons.py`:

```python
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
```

- [ ] **Step 5: 冒烟测试图标绘制**

`tools/smoke_icons.py`:

```python
"""在离屏窗口里把每个图标画一遍，确认没有绘制错误。不截图，只看是否抛异常。"""

import os
import sys

os.environ["TCL_LIBRARY"] = ""
os.environ["TK_LIBRARY"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from claude_launcher.ui import icons  # noqa: E402

NAMES = [
    "folder", "refresh", "gear", "play", "bolt", "star", "star_filled",
    "chevron_down", "chevron_right", "clock", "plus", "open_external", "close",
]


def main():
    root = tk.Tk()
    root.withdraw()
    canvas = tk.Canvas(root, width=400, height=200)
    canvas.pack()

    for index, name in enumerate(NAMES):
        icons.draw(canvas, name, "#d97757", 24, x=10 + (index % 7) * 32, y=10 + (index // 7) * 40)

    print("claude_mark:", icons.claude_mark() is not None)
    print("assets_dir:", icons.assets_dir())
    print("已绘制 %d 个图标，无异常" % len(NAMES))
    root.destroy()


if __name__ == "__main__":
    main()
```

Run: `python tools/smoke_icons.py`
Expected: 输出 `claude_mark: True`、`assets_dir: ...`、`已绘制 13 个图标，无异常`

- [ ] **Step 6: Commit**

```bash
git add assets/ tools/ claude_launcher/ui/icons.py
git commit -m "feat: 添加 Canvas 手绘图标与 Claude 标志位图"
```

---

### Task 7: 基础控件

**Files:**
- Create: `claude_launcher/ui/widgets.py`

**Interfaces:**
- Consumes: `claude_launcher.ui.icons.draw`
- Produces:
  - `FlatButton(parent, text, command, colors, variant="primary", width=None)`
    - `variant` 取值 `"primary"`（实心 accent）/ `"secondary"`（accent_soft 底）/ `"ghost"`（描边）/ `"danger"`
    - 方法 `set_text(text)`
  - `IconButton(parent, name, command, colors, size=28, tooltip=None)`
    - 方法 `set_icon(name)`、`set_colors(colors)`
  - `Pill(parent, text, colors, tone="neutral")` —— `tone` 取值 `"neutral"` / `"ok"` / `"danger"`
    - 方法 `set(text, tone)`
  - `SectionHeader(parent, title, colors)` —— 返回带 `set_count(n)` 方法的 Frame
  - `ScrollArea(parent, colors)` —— 返回带 `content` 属性与 `refresh_scrollregion()` 方法的 Frame

- [ ] **Step 1: 实现 widgets.py**

无独立单测（纯 tkinter 展示控件，手工验证）。直接实现：

`claude_launcher/ui/widgets.py`:

```python
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
```

- [ ] **Step 2: 冒烟测试控件构造**

`tools/smoke_widgets.py`:

```python
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
```

Run: `python tools/smoke_widgets.py`
Expected: 输出 `控件构造全部通过`

- [ ] **Step 3: Commit**

```bash
git add claude_launcher/ui/widgets.py tools/smoke_widgets.py
git commit -m "feat: 添加基础控件（直角按钮、图标按钮、状态徽标、滚动容器）"
```

---

### Task 8: 列表行控件

**Files:**
- Modify: `claude_launcher/ui/widgets.py`（追加 `SessionRow`、`FolderGroupRow`、`FavoriteRow`）

**Interfaces:**
- Consumes: `FlatButton`、`Pill`、`icons.draw`
- Produces:
  - `SessionRow(parent, session, colors, on_select, on_resume, on_delete)`
    - 方法 `set_selected(bool)`
    - 单击 → `on_select(session)`；双击 → `on_resume(session)`；点 ✕ → `on_delete(session)`
  - `FolderGroupRow(parent, project_path, sessions, colors, on_select, on_resume, on_delete, on_open, on_double_click, on_toggle, expanded=True)`
    - 属性 `expanded`、`project_path`、`sessions`
    - 单击标题切换 `expanded` 并显隐子行，随后调用 `on_toggle(project_path, expanded)` 让调用方持久化展开状态
    - 双击标题 → `on_double_click(project_path)`
    - 方法 `set_child_selection(session_id)`
  - `FavoriteRow(parent, path, colors, on_open, on_launch, on_remove)`
  - 工具函数 `format_size(bytes) -> str`、`format_time(mtime) -> str`、`elide_path(path, limit) -> str`

- [ ] **Step 1: 写失败的测试（纯函数部分）**

`tests/test_widgets_format.py`:

```python
from claude_launcher.ui.widgets import elide_path, format_size, format_time


def test_format_size_bytes():
    assert format_size(512) == "512B"


def test_format_size_kilobytes():
    assert format_size(2048) == "2KB"


def test_format_size_megabytes():
    assert format_size(3 * 1024 * 1024) == "3.0MB"


def test_format_size_zero():
    assert format_size(0) == "0B"


def test_elide_short_path_unchanged():
    assert elide_path("D:\\proj", 35) == "D:\\proj"


def test_elide_long_path_keeps_tail():
    long_path = "D:\\" + "\\".join(["verylongsegment%d" % i for i in range(10)])
    result = elide_path(long_path, 35)
    assert len(result) == 35
    assert result.startswith("...")
    assert long_path.endswith(result[3:])


def test_elide_exact_limit_unchanged():
    path = "x" * 35
    assert elide_path(path, 35) == path
```

- [ ] **Step 2: 运行测试确认失败**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest tests/test_widgets_format.py -v`
Expected: FAIL —— `ImportError: cannot import name 'elide_path'`

- [ ] **Step 3: 追加实现到 widgets.py**

在 `claude_launcher/ui/widgets.py` 末尾追加：

```python
def format_size(size):
    if size >= 1024 * 1024:
        return "%.1fMB" % (size / (1024 * 1024))
    if size >= 1024:
        return "%dKB" % (size / 1024)
    return "%dB" % size


def format_time(mtime):
    from datetime import datetime

    try:
        return datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")
    except (ValueError, OSError, OverflowError):
        return ""


def elide_path(path, limit=35):
    if len(path) <= limit:
        return path
    return "..." + path[-(limit - 3):]


class SessionRow(tk.Frame):
    """会话列表的一行。单击选中，双击恢复。"""

    def __init__(self, parent, session, colors, on_select, on_resume, on_delete):
        super().__init__(parent, bg=colors["bg"], height=26)
        self.pack_propagate(False)

        self.session = session
        self.colors = colors
        self.on_select = on_select
        self.on_resume = on_resume
        self.on_delete = on_delete
        self._selected = False

        self.accent_bar = tk.Frame(self, bg=colors["bg"], width=2)
        self.accent_bar.pack(side=tk.LEFT, fill=tk.Y)

        self.title = tk.Label(
            self,
            text=session.get("prompt") or session.get("id", ""),
            font=("Segoe UI", 9),
            bg=colors["bg"], fg=colors["ink_2"],
            anchor=tk.W, padx=12,
        )
        self.title.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.time_label = tk.Label(
            self, text=format_time(session.get("mtime", 0)),
            font=("Segoe UI", 8), bg=colors["bg"], fg=colors["ink_3"], padx=5,
        )
        self.time_label.pack(side=tk.RIGHT)

        self.delete_btn = tk.Label(
            self, text="✕", font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["bg"], padx=4, cursor="hand2",
        )
        self.delete_btn.pack(side=tk.RIGHT)

        for widget in (self, self.title, self.time_label):
            widget.bind("<Button-1>", self._click)
            widget.bind("<Double-Button-1>", self._double_click)
            widget.bind("<Enter>", self._hover_in)
            widget.bind("<Leave>", self._hover_out)

        self.delete_btn.bind("<Button-1>", lambda _event: self.on_delete(self.session))
        self.delete_btn.bind("<Enter>", lambda _event: self.delete_btn.config(fg=colors["danger"]))
        self.delete_btn.bind("<Leave>", lambda _event: self.delete_btn.config(
            fg=colors["danger"] if self._selected else colors["bg"]))

    def _background(self):
        return self.colors["accent_soft"] if self._selected else self.colors["bg"]

    def _paint(self, background):
        for widget in (self, self.title, self.time_label, self.delete_btn):
            widget.config(bg=background)
        self.accent_bar.config(bg=self.colors["accent"] if self._selected else background)
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
                 on_resume, on_delete, on_open, on_double_click, on_toggle,
                 expanded=True):
        super().__init__(parent, bg=colors["bg"])

        self.project_path = project_path
        self.sessions = sessions
        self.colors = colors
        self.expanded = expanded
        self.on_open = on_open
        self.on_toggle = on_toggle

        header = tk.Frame(self, bg=colors["bg"], height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        self.header = header

        self.chevron = tk.Canvas(
            header, width=14, height=14, bg=colors["bg"], highlightthickness=0,
        )
        self.chevron.pack(side=tk.LEFT, padx=(4, 2))
        self._draw_chevron()

        self.name_label = tk.Label(
            header, text=os.path.basename(project_path) or project_path,
            font=("Segoe UI", 9, "bold"), bg=colors["bg"], fg=colors["ink"], anchor=tk.W,
        )
        self.name_label.pack(side=tk.LEFT)

        self.count_label = tk.Label(
            header, text=str(len(sessions)), font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_3"], padx=6,
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

        for widget in (header, self.name_label, self.count_label, self.chevron):
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
        self.header.config(bg=self.colors["hover"])
        self.name_label.config(bg=self.colors["hover"])
        self.count_label.config(bg=self.colors["hover"])

    def _hover_out(self, _event):
        self.header.config(bg=self.colors["bg"])
        self.name_label.config(bg=self.colors["bg"])
        self.count_label.config(bg=self.colors["bg"])

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


class FavoriteRow(tk.Frame):
    """收藏夹的一行：名称 + 路径 + 打开 + 启动 + 移除。"""

    def __init__(self, parent, path, colors, on_open, on_launch, on_remove):
        super().__init__(parent, bg=colors["line"], padx=1, pady=1)

        body = tk.Frame(self, bg=colors["bg"], height=40)
        body.pack(fill=tk.BOTH, expand=True)
        body.pack_propagate(False)

        icon = tk.Canvas(body, width=20, height=20, bg=colors["bg"], highlightthickness=0)
        icon.pack(side=tk.LEFT, padx=(10, 6))
        icons.draw(icon, "star_filled", colors["accent"], 14, x=3, y=3)

        text = tk.Frame(body, bg=colors["bg"])
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(
            text, text=os.path.basename(path) or path, font=("Segoe UI", 9, "bold"),
            bg=colors["bg"], fg=colors["ink"], anchor=tk.W,
        ).pack(fill=tk.X, pady=(5, 0))
        tk.Label(
            text, text=elide_path(path, 42), font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_3"], anchor=tk.W,
        ).pack(fill=tk.X)

        actions = tk.Frame(body, bg=colors["bg"])
        actions.pack(side=tk.RIGHT, padx=(4, 8))

        FlatButton(actions, "启动", lambda: on_launch(path), colors).pack(side=tk.RIGHT)
        FlatButton(actions, "打开", lambda: on_open(path), colors, variant="ghost").pack(
            side=tk.RIGHT, padx=(0, 5))

        remove = tk.Label(
            actions, text="✕", font=("Segoe UI", 8),
            bg=colors["bg"], fg=colors["ink_3"], padx=6, cursor="hand2",
        )
        remove.pack(side=tk.RIGHT)
        remove.bind("<Button-1>", lambda _event: on_remove(path))
        remove.bind("<Enter>", lambda _event: remove.config(fg=colors["danger"]))
        remove.bind("<Leave>", lambda _event: remove.config(fg=colors["ink_3"]))
```

`widgets.py` 的 import 区需为本任务新增 `import os`（`FolderGroupRow` 与 `FavoriteRow`
用 `os.path.basename`）与 `from typing import Optional, Tuple, List, Dict, Any, Callable`。
最终 import 区应为：

```python
import os
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import icons
```

- [ ] **Step 4: 运行格式函数测试确认通过**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest tests/test_widgets_format.py -v`
Expected: 全部 PASS（7 个测试）

- [ ] **Step 5: 扩展冒烟脚本覆盖列表行**

在 `tools/smoke_widgets.py` 的 `main()` 中、`print` 之前插入：

```python
    sessions = [
        {"id": "a1b2c3d4", "file": "x", "mtime": 1700000000.0, "size": 4096,
         "prompt": "重构登录模块", "cwd": "D:\\proj"},
    ]
    widgets.SessionRow(frame, sessions[0], colors, lambda s: None, lambda s: None,
                       lambda s: None).pack()
    group = widgets.FolderGroupRow(frame, "D:\\proj", sessions, colors,
                                   lambda s: None, lambda s: None, lambda s: None,
                                   lambda p: None, lambda p: None, lambda p, e: None)
    group.pack()
    group.set_child_selection("a1b2c3d4")
    widgets.FavoriteRow(frame, "D:\\proj", colors, lambda p: None, lambda p: None,
                        lambda p: None).pack()
```

Run: `python tools/smoke_widgets.py`
Expected: 输出 `控件构造全部通过`

- [ ] **Step 6: Commit**

```bash
git add claude_launcher/ui/widgets.py tests/test_widgets_format.py tools/smoke_widgets.py
git commit -m "feat: 添加会话行、项目分组行与收藏行控件"
```

---

### Task 9: 对话框

**Files:**
- Create: `claude_launcher/ui/dialogs.py`

**Interfaces:**
- Consumes: `FlatButton`、`theme.resolve`、`agent.MODES`
- Produces:
  - `SettingsDialog(parent, config, colors, on_theme_change, on_quit)`
    - 主题切换调用 `on_theme_change(theme_id)`，然后自行 `close()` 再回调（避免父窗口重建时销毁本窗口）
    - 自动关闭勾选直接写 `config` 并 `config.save()`
  - `ModeDialog(parent, project_path, colors, on_choose)` —— `on_choose(mode_id)`
  - 两者均提供 `close()` 方法

- [ ] **Step 1: 实现 dialogs.py**

`claude_launcher/ui/dialogs.py`:

```python
"""模态对话框：设置与启动模式选择。

关键修复：主题切换必须先关闭本对话框再回调。父窗口重建时会 destroy 全部子控件，
其中包含本 Toplevel，之后再 destroy 一次会抛 TclError。
"""

import tkinter as tk
from typing import Callable, Dict, List

from .. import agent
from .widgets import FlatButton

DIALOG_BG_KEY = "bg"


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
```

- [ ] **Step 2: 冒烟测试对话框**

`tools/smoke_dialogs.py`:

```python
"""构造两个对话框并立即关闭，确认无构造错误。"""

import os
import sys

os.environ["TCL_LIBRARY"] = ""
os.environ["TK_LIBRARY"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from claude_launcher import theme  # noqa: E402
from claude_launcher.config import Config  # noqa: E402
from claude_launcher.ui import dialogs  # noqa: E402


def main():
    root = tk.Tk()
    root.geometry("900x620")
    colors = theme.resolve("light")
    config = Config()

    settings = dialogs.SettingsDialog(root, config, colors, lambda t: None, lambda: None)
    root.update()
    settings.close()
    settings.close()  # 二次关闭必须是安全的

    mode = dialogs.ModeDialog(root, "D:\\proj", colors, lambda m: None)
    root.update()
    mode.close()

    print("对话框构造与关闭全部通过")
    root.destroy()


if __name__ == "__main__":
    main()
```

Run: `python tools/smoke_dialogs.py`
Expected: 输出 `对话框构造与关闭全部通过`（不抛 TclError）

- [ ] **Step 3: Commit**

```bash
git add claude_launcher/ui/dialogs.py tools/smoke_dialogs.py
git commit -m "feat: 添加设置与启动模式对话框"
```

---

### Task 10: 主窗口

**Files:**
- Create: `claude_launcher/ui/window.py`

**Interfaces:**
- Consumes: `theme.resolve`、`sessions.SessionStore`、`agent`、`config.Config`、全部控件与对话框
- Produces:
  - `MainWindow(root, config, store)` —— 构建骨架并绑定快捷键
  - 方法：`refresh_sessions()`、`refresh_favorites()`、`rebuild_theme()`、`set_status(message, tone)`

- [ ] **Step 1: 实现 window.py**

`claude_launcher/ui/window.py`:

```python
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
                on_open=self.open_path_in_explorer,
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
        """主题切换是唯一走全量重建的路径——颜色写死在控件构造参数上。"""
        self.colors = theme.resolve(self.config.get("theme", "auto"))
        self.root.configure(bg=self.colors["bg"])
        for child in self.root.winfo_children():
            child.destroy()
        self._build_skeleton()
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
```

- [ ] **Step 2: 冒烟测试主窗口**

`tools/smoke_window.py`:

```python
"""构建主窗口，确认骨架与两个动态区域都不报错。"""

import os
import sys

os.environ["TCL_LIBRARY"] = ""
os.environ["TK_LIBRARY"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from claude_launcher.config import Config  # noqa: E402
from claude_launcher.sessions import SessionStore  # noqa: E402
from claude_launcher.ui.window import MainWindow  # noqa: E402


def main():
    root = tk.Tk()
    root.withdraw()

    config = Config()
    config.load()
    store = SessionStore()

    window = MainWindow(root, config, store)
    window.set_status("冒烟测试", "success")
    root.update()

    print("主窗口构造通过")
    print("会话分组数:", len(store.get()))
    root.destroy()


if __name__ == "__main__":
    main()
```

Run: `python tools/smoke_window.py`
Expected: 输出 `主窗口构造通过` 与分组数，无异常

- [ ] **Step 3: Commit**

```bash
git add claude_launcher/ui/window.py tools/smoke_window.py
git commit -m "feat: 添加左右分栏主窗口"
```

---

### Task 11: 应用装配层

**Files:**
- Create: `claude_launcher/app.py`
- Modify: `main.py`（替换为完整入口）

**Interfaces:**
- Consumes: `Config`、`SessionStore`、`MainWindow`、`theme`
- Produces:
  - `SingleInstance(port=58432)` —— `acquire() -> bool`、`release()`、`is_taken_by_another() -> bool`
  - `LauncherApp(root, lock)` —— 装配 config、store、window、托盘，注入各回调
  - `main()` —— 含顶层异常兜底

- [ ] **Step 1: 实现 app.py**

`claude_launcher/app.py`:

```python
"""应用装配：单实例锁、托盘、顶层异常兜底。"""

import socket
import sys
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
```

注意：`SingleInstance` 只保留 `acquire`、`is_taken_by_another`、`release` 三个方法。
监听激活请求由 `LauncherApp._start_activation_listener` 承担，不放在锁对象里——
它需要 `root.after` 做轮询，属于界面层职责。

- [ ] **Step 2: 替换 main.py**

`main.py`:

```python
"""Claude Launcher 启动入口。

单独一层薄入口是为了让 PyInstaller 有明确的入口脚本，同时保持包内可测试。
"""

from claude_launcher.app import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 冒烟测试完整启动路径**

`tools/smoke_app.py`:

```python
"""模拟启动：构建整个应用后立刻退出，确认装配无遗漏。"""

import os
import sys

os.environ["TCL_LIBRARY"] = ""
os.environ["TK_LIBRARY"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from claude_launcher.app import LauncherApp, SingleInstance  # noqa: E402


def main():
    lock = SingleInstance()
    lock.acquire()

    root = tk.Tk()
    app = LauncherApp(root, lock)
    root.update()

    print("应用装配通过")
    print("窗口标题:", root.title())
    print("窗口尺寸:", root.winfo_width(), "x", root.winfo_height())
    print("托盘可用:", app.tray is not None)
    print("会话缓存分组:", len(app.store.get()))

    app.quit()
    print("退出路径通过")


if __name__ == "__main__":
    main()
```

Run: `python tools/smoke_app.py`
Expected: 输出窗口标题 `Claude Launcher`、尺寸 `900 x 620`、退出路径通过

- [ ] **Step 4: 真实启动验证**

Run: `python main.py`
Expected: 窗口出现，标题为 `Claude Launcher`，左侧为会话列表，右侧为路径栏与当前项目卡片。确认后按 `Esc` 最小化到托盘，右键托盘图标选「退出程序」。

- [ ] **Step 5: Commit**

```bash
git add claude_launcher/app.py main.py tools/smoke_app.py
git commit -m "feat: 添加应用装配层与单实例锁容错"
```

---

### Task 12: 删除旧文件与更新分发配置

**Files:**
- Delete: `claude_launcher.py`（根目录旧单文件）
- Delete: `create_icon.py`、`download_icon.py`、`RELEASE_GUIDE.md`、`install.ps1`、`install.bat`、`install_exe.bat`
- Create: `install.bat`（合并版）
- Modify: `build.py`
- Modify: `requirements.txt`
- Rewrite: `README.md`、`RELEASE_NOTES.md`

**Interfaces:**
- Consumes: 无
- Produces: 无（收尾任务）

- [ ] **Step 1: 删除旧文件**

```bash
git rm claude_launcher.py create_icon.py download_icon.py RELEASE_GUIDE.md install.ps1 install.bat install_exe.bat
```

- [ ] **Step 2: 写合并版 install.bat**

`install.bat`:

```bat
@echo off
chcp 65001 >nul
echo ====================================
echo Claude Launcher - 创建桌面快捷方式
echo ====================================
echo.

if not exist "%~dp0ClaudeLauncher.exe" (
    echo [错误] 找不到 ClaudeLauncher.exe
    echo 请将此脚本与 ClaudeLauncher.exe 放在同一目录
    pause
    exit /b 1
)

echo [OK] 找到 ClaudeLauncher.exe
echo.

set SHORTCUT=%USERPROFILE%\Desktop\Claude Launcher.lnk
set EXE_PATH=%~dp0ClaudeLauncher.exe
set ICON_PATH=%~dp0assets\claude_icon.ico

if exist "%ICON_PATH%" (
    set ICON_ARG=-IconLocation '%ICON_PATH%,0'
) else (
    set ICON_ARG=
)

echo 正在创建桌面快捷方式...

powershell -Command "$shell = New-Object -ComObject WScript.Shell; if (Test-Path '%SHORTCUT%') { Remove-Item '%SHORTCUT%' -Force }; $s = $shell.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%EXE_PATH%'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Claude Launcher'; if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%,0' }; $s.Save()"

if %errorlevel% equ 0 (
    echo [OK] 桌面快捷方式创建成功
    echo.
    echo 快捷方式位置: %SHORTCUT%
    echo 现在可以双击桌面上的 "Claude Launcher" 启动程序
) else (
    echo [错误] 创建快捷方式失败
    echo 请手动创建，目标文件: "%EXE_PATH%"
)

echo.
pause
```

- [ ] **Step 3: 更新 build.py**

`build.py`:

```python
"""Claude Launcher 打包脚本：使用 PyInstaller 生成单文件 exe。"""

import sys
from pathlib import Path

import PyInstaller.__main__

PROJECT_DIR = Path(__file__).parent
ASSETS = PROJECT_DIR / "assets"
ENTRY = PROJECT_DIR / "main.py"
ICON = ASSETS / "claude_icon.ico"


def main():
    if not ENTRY.exists():
        print("找不到入口文件 %s" % ENTRY)
        sys.exit(1)

    if not ASSETS.exists():
        print("找不到资源目录 %s" % ASSETS)
        sys.exit(1)

    arguments = [
        str(ENTRY),
        "--name=ClaudeLauncher",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--add-data=%s;assets" % ASSETS,
        "--distpath=%s" % (PROJECT_DIR / "dist"),
        "--workpath=%s" % (PROJECT_DIR / "build"),
        "--specpath=%s" % PROJECT_DIR,
    ]

    if ICON.exists():
        arguments.append("--icon=%s" % ICON)

    PyInstaller.__main__.run(arguments)

    print("\n" + "=" * 60)
    print("打包完成")
    print("=" * 60)
    print("输出文件: %s" % (PROJECT_DIR / "dist" / "ClaudeLauncher.exe"))
    print("同时需要分发 install.bat 以便创建桌面快捷方式")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 更新 requirements.txt**

`requirements.txt`:

```
pystray>=0.19.0
Pillow>=9.0.0
```

（内容不变，运行时依赖本就只有这两个。pytest 为开发依赖，不列入。）

- [ ] **Step 5: 验证打包可用**

Run: `python build.py`
Expected: 打包成功，`dist/ClaudeLauncher.exe` 生成

Run: `dist/ClaudeLauncher.exe`
Expected: 窗口正常出现，且 `assets/claude-mark.png` 被正确解包（顶栏显示 Claude 标志而非回退的 ✳ 字符）

- [ ] **Step 6: 重写 README.md**

按单工具（仅 Claude Code）重写。需包含：项目简介、界面截图占位、功能列表、
两种安装方式（EXE / 源码）、使用指南、配置项说明（四个字段）、从源码打包、
项目结构、常见问题。

必须修正的过时内容：删除全部 Codex/MiMo 描述、修正仓库地址为
`shuli66/claude-launcher`、配置项从六个改为四个、项目结构改为包结构。

- [ ] **Step 7: 重写 RELEASE_NOTES.md**

写 v2.1.0 条目，说明这是一次重构版本：移除 Codex/MiMo、界面重做、
修复 5 个 Bug、拆分为包结构。

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "refactor: 移除旧单文件与冗余脚本，更新打包与文档

- 删除 claude_launcher.py 及三个重复的安装脚本
- 合并为单一 install.bat
- build.py 打包 assets 目录
- README 与 RELEASE_NOTES 重写为单工具版本"
```

---

### Task 13: 全量验证

**Files:**
- 无新增；纯验证任务

**Interfaces:**
- Consumes: 全部
- Produces: 无

- [ ] **Step 1: 全量单测**

Run: `TCL_LIBRARY= TK_LIBRARY= python -m pytest -v`
Expected: 全部 PASS

- [ ] **Step 2: 逐项手工验证界面**

启动 `python main.py`，依次确认：

| # | 操作 | 期望 |
|---|---|---|
| 1 | 启动 | 窗口 900×620，标题 `Claude Launcher`，顶栏有 Claude 标志 |
| 2 | 输入有效目录 | 路径栏显示 `✓ 可用`，当前项目卡片显示项目名与 `可用` 徽标 |
| 3 | 输入无效目录 | 显示 `✕ 无效`，卡片显示 `无效` 徽标 |
| 4 | 单击会话行 | 该行高亮，路径栏同步为该会话的项目路径，状态栏提示已选中 |
| 5 | 双击会话行 | 新控制台窗口以 `claude --resume <id>` 启动；若开了自动关闭，启动器退出 |
| 6 | 单击项目分组标题 | 该组折叠/展开，箭头方向同步变化 |
| 7 | 双击项目分组标题 | 弹出模式选择对话框；选一个模式后启动 |
| 8 | 点会话行 ✕ | 确认弹窗；确认后该行消失，分组计数减一 |
| 9 | 点顶部刷新 | 状态栏闪一下，列表重新渲染，展开状态保留 |
| 10 | 点 ☆ | 变实心 ★，收藏夹区块出现该目录且计数 +1 |
| 11 | 点收藏行「启动」 | 切到该路径并启动 |
| 12 | 点收藏行「打开」 | 资源管理器打开该目录 |
| 13 | 点收藏行 ✕ | 确认后从收藏夹移除 |
| 14 | 打开设置 → 切深色 | 界面立即变深色，对话框消失且无 TclError |
| 15 | 设置里取消勾选自动关闭 | 关闭设置，启动一次 agent → 启动器**留在原地不退出** |
| 16 | 重新勾选自动关闭 | 启动一次 agent → 启动器退出 |
| 17 | 按 Esc | 最小化到托盘 |
| 18 | 右键托盘 → 显示窗口 | 窗口恢复 |
| 19 | 右键托盘 → 退出程序 | 进程完全退出 |
| 20 | 关闭窗口按钮 | 最小化到托盘而非退出 |
| 21 | 第二次双击图标 | 已运行实例的窗口被激活到前台，不新开窗口 |
| 22 | 把 `~/.claude_launcher_config.json` 改坏再启动 | 程序正常启动，状态栏显示配置读取告警 |

- [ ] **Step 3: 验证配置迁移**

先写入一个含旧字段的配置，再启动程序，确认被自动清理：

```bash
python -c "
import json, pathlib
p = pathlib.Path.home() / '.claude_launcher_config.json'
p.write_text(json.dumps({
    'recent_dirs': ['D:\\\\old'],
    'agent': 'codex',
    'last_mode': 'yolo',
    'theme': 'neon',
    'auto_close': 'yes',
    'favorites': ['D:\\\\proj']
}), encoding='utf-8')
print('已写入旧版配置')
"
```

Run: `python main.py`，关闭后检查：

```bash
python -c "
import json, pathlib
p = pathlib.Path.home() / '.claude_launcher_config.json'
print(json.dumps(json.loads(p.read_text(encoding='utf-8')), ensure_ascii=False, indent=2))
"
```

Expected: 只剩 `favorites`、`last_mode`、`auto_close`、`theme` 四个键，
取值分别为 `["D:\\proj"]`、`"normal"`、`true`、`"auto"`。
`recent_dirs` 与 `agent` 消失；`yolo` 与 `neon` 与 `"yes"` 三个非法值都被回落。

- [ ] **Step 4: 确认无残留引用**

```bash
grep -rn "codex\|mimo\|Codex\|MiMo\|MIMO\|recent_dirs\|AI Coding" --include=*.py --include=*.md --include=*.bat --include=*.txt . | grep -v "^./docs/superpowers"
```

Expected: 无输出（设计文档与计划文档中保留历史说明是允许的，已被排除）

- [ ] **Step 5: 确认无 emoji 图标残留**

```bash
grep -rn "⚡\|🤖\|🧠\|📁\|📂\|★\|☆\|🕘\|⚠\|⚙" --include=*.py claude_launcher/ main.py
```

Expected: 无输出。例外：`✕`（U+2715）作为关闭按钮字符是刻意保留的，
`✓` 与 `✕` 作为路径校验提示也保留——它们不是 emoji，在各 Windows 版本渲染一致。

- [ ] **Step 6: 提交验证结果**

若前五步有任何修改：

```bash
git add -A
git commit -m "test: 全量验证并修复遗留问题"
```

若无修改，此任务无需提交。

---

## 附录：任务依赖关系

```
Task 1 (骨架)
  ├─ Task 2 (config) ──┐
  ├─ Task 3 (theme) ───┤
  ├─ Task 4 (sessions)─┤
  └─ Task 5 (agent) ───┤
                       ├─ Task 6 (icons) ─ Task 7 (widgets) ─ Task 8 (rows) ─ Task 9 (dialogs) ─ Task 10 (window) ─ Task 11 (app)
                       │
                       └──────────────────────────────────────────────────────────────── Task 12 (清理) ─ Task 13 (验证)
```

Task 2-5 互相独立，可并行。Task 6 起为串行依赖链（每个都用到前一个的接口）。
