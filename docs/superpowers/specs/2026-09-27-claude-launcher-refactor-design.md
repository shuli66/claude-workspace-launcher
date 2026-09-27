# Claude Launcher 重构设计

日期：2026-09-27
状态：待实现

## 1. 背景与目标

当前项目是单文件应用 `claude_launcher.py`（2184 行），一个文件里同时承担 UI 组件、
设置对话框、工具配置、会话扫描、业务逻辑和程序入口。v2.0.0 为了支持三个 AI 编程工具
（Claude Code / Codex CLI / MiMo Code）引入了大量分支，其中两个工具已不再需要。

目标：

1. 去掉 Codex 和 MiMo 的全部代码，回归单一 Claude Code 启动器
2. 修复排查出的 5 个真 Bug
3. 按职责拆分为多个模块，让界面逻辑、会话扫描、配置读写可以各自独立理解和测试
4. 把界面重做成左右分栏布局，并统一到 Claude 品牌视觉
5. 统一三套并行的命名

## 2. 范围

### 2.1 删除

| 内容 | 原位置 |
|---|---|
| `AGENT_CONFIGS` 中的 codex / mimo 配置块 | `527-570` |
| `_scan_codex_sessions`、`_extract_cwd_from_codex_rollout`、`_extract_first_prompt_codex` | `929-1037` |
| `_scan_mimo_sessions`（含 sqlite3 查询、毫秒时间戳转换、编码修复） | `1039-1114` |
| 顶部「工具选择器」整条 UI | `1189-1219` |
| `switch_agent` | `1602-1610` |
| `_delete_session` 中的 MiMo 数据库提示分支 | `1977-1979` |
| `current_agent` 的读取与校验 | `584-587, 773-776, 1477` |
| `FavoriteItem` 死类（从未实例化） | `74-173` |
| `FolderGroup` 死类（从未实例化） | `274-358` |
| `env_key` 检查逻辑（Claude 无需 API Key 环境变量） | `2063-2067, 2071-2073` |
| 「最近目录」概念与「清除历史」按钮 | `744, 770, 1376-1380, 2039-2044` |
| `create_icon.py`、`download_icon.py`、`RELEASE_GUIDE.md` | 仓库根目录 |
| `.superpowers/`、`.playwright-mcp/` 加入 `.gitignore` | `.gitignore` |

### 2.2 修复

| 问题 | 根因 | 修法 |
|---|---|---|
| 设置里「自动关闭」开关无效 | `SettingsDialog.save_auto_close` 只改 `config`，而 `launch_agent` 读的是不同步的 `self.auto_close_var`，随后还用旧值覆盖回 config | 删除 `auto_close_var` 中间层，所有读写统一走 `config` |
| 切主题时设置对话框重复销毁 | `switch_theme` → `rebuild_ui` 已 destroy 全部子控件（含该 Toplevel），之后又 `dialog.destroy()` | 先关闭对话框，再切主题 |
| 「清除历史」点了没反应 | 界面从不渲染 `recent_dirs` | 功能与按钮一并删除 |
| 单实例锁导致程序静默打不开 | 硬编码端口 58432 被占用且连不上已有实例时直接 `sys.exit(0)`，无任何提示 | 弹窗告知失败原因，并允许用户直接启动一个新实例 |
| 单击会话项误启动 agent | 会话行 `<Button-1>` 绑定 `_launch_session` | 单击只选中路径并同步到输入框，双击才恢复会话 |
| 无异常兜底 | `pythonw` 无控制台，`setup_ui` 抛异常即静默退出 | `main()` 包裹顶层异常，弹出错误对话框并写明日志路径 |

### 2.3 新增

- 顶部「刷新」按钮：强制重扫会话目录
- 会话扫描内存缓存：切主题 / 加删收藏不再重扫磁盘
- 展开状态跨界面更新保留（存于 `set`，重建后恢复）
- 会话行选中态：单击高亮，右侧主区同步显示该项目
- 每项目最多显示 10 个会话（原 3），最多 20 个项目分组（原 5）

## 3. 架构

### 3.1 模块划分

```
claude_launcher/
├── __init__.py
├── app.py          应用装配、单实例锁、顶层异常处理、mainloop
├── config.py       配置读写、字段校验、旧版迁移
├── theme.py        auto/light/dark 三套配色 token
├── sessions.py     会话扫描 + 内存缓存
├── agent.py        命令解析、启动参数构建、进程启动
└── ui/
    ├── __init__.py
    ├── icons.py    Canvas 手绘图标 + Claude 标志位图加载
    ├── widgets.py  ModernButton / IconButton / SessionRow / FavoriteRow / GroupHeader
    ├── dialogs.py  SettingsDialog / ModeDialog
    └── window.py   MainWindow：骨架 + 动态区域编排
assets/
├── claude-mark.png   由 claude_icon.ico 抠出（新增）
└── claude_icon.ico   窗口与任务栏图标（沿用）
main.py               薄入口：调用 claude_launcher.app.main()
```

拆分依据：`ui/` 之下只依赖 `theme` 与传入的数据，不碰文件系统；`sessions` 和 `agent`
不 import tkinter。因此会话扫描与配置逻辑可以脱离界面单独运行和测试。

### 3.2 各模块职责与接口

| 模块 | 职责 | 对外接口 |
|---|---|---|
| `config.py` | 读写 `~/.claude_launcher_config.json`，校验字段、兜底损坏文件、迁移旧版字段 | `Config.load()` / `save()` / `get(k, d)` / `set(k, v)` |
| `theme.py` | 给定主题名返回配色字典 | `resolve(theme: str) -> dict` |
| `sessions.py` | 扫描 `~/.claude/projects`，解析 cwd 与首个用户提问，缓存结果 | `SessionStore.get(force_refresh=False) -> list[(project_path, [session])]` |
| `agent.py` | 解析 `claude` 可执行文件、构建启动命令、启动与恢复进程 | `resolve_command()` / `build_command(mode)` / `launch(dir, mode)` / `resume(dir, session_id)` |
| `ui/icons.py` | 在给定 Canvas 上绘制图标；加载 Claude 标志位图 | `draw(canvas, name, color, size)` / `claude_mark(size)` |
| `ui/widgets.py` | 无业务逻辑的展示控件 | 各类控件构造器 |
| `ui/dialogs.py` | 设置弹窗与启动模式选择弹窗 | `SettingsDialog(parent, app)` / `ModeDialog(parent, project, modes)` |
| `ui/window.py` | 组装骨架、编排两个动态区域、响应交互 | `MainWindow` |

## 4. 数据模型

### 4.1 配置文件

路径不变：`%USERPROFILE%\.claude_launcher_config.json`

```json
{
  "favorites": ["D:\\Projects\\my-app"],
  "last_mode": "normal",
  "auto_close": true,
  "theme": "auto"
}
```

字段变更：

- 删除 `recent_dirs`（界面不再使用）
- 删除 `agent`（只剩 Claude 一个工具，无意义）
- `last_mode` 取值收窄为 `normal` | `skip`

**迁移规则**：加载时忽略未在 schema 中的键；`last_mode` 若不在 `{normal, skip}`
内（旧配置里可能是 codex 的 `yolo` 或 mimo 的 `interactive`/`run`）则回落为 `normal`；
`theme` 若不在 `{auto, light, dark}` 内回落为 `auto`；`auto_close` 非布尔时回落为 `true`。
迁移后立即写回，使配置文件自愈。

### 4.2 会话数据

```python
{
  "id": str,        # 会话文件名（不含扩展名）
  "file": str,      # .jsonl 绝对路径
  "mtime": float,   # 文件修改时间
  "size": int,      # 字节数
  "prompt": str,    # 首个用户提问，截断至 80 字符
  "cwd": str,       # 从 jsonl 中提取的真实项目路径
}
```

分组键为真实 `cwd`（不是 `~/.claude/projects` 下的目录名，后者是路径的转义形式）。
`cwd` 不存在于磁盘上的会话会被跳过。

## 5. 界面设计

### 5.1 布局 B — 左右分栏

窗口 900 × 620，固定尺寸（与现状一致，本次不改可缩放）。

```
┌──────────────────────────────────────────────────────┐
│ [标志] Claude Launcher                 [刷新] [设置]  │ 顶栏 46px
├──────────────┬───────────────────────────────────────┤
│ 会话      5  │ [图标] D:\Projects\my-app    [浏览]   │ 路径栏
│              ├───────────────────────────────────────┤
│ ▾ my-app   3 │ ┌───────────────────────────────────┐ │
│   重构登录    │ │ my-app                  ● 可用     │ │ 当前项目卡片
│   SQL 优化    │ │ D:\Projects\my-app                │ │
│   批量重命名  │ │ [普通启动] [跳过权限]   [📂] [☆]  │ │
│ ▾ api-server2│ └───────────────────────────────────┘ │
│   分页组件    ├───────────────────────────────────────┤
│   加单元测试  │ 收藏夹                            2   │
│              │ ⭐ my-app          [打开] [启动]       │
│              │ ⭐ api-server      [打开] [启动]       │
│              │                                       │
│ 单击选中·双击恢复                     [＋ 添加当前目录] │
└──────────────┴───────────────────────────────────────┘
  侧栏 244px                        底部快捷键提示贴右
```

区域职责：

- **顶栏**：Claude 标志、标题、刷新按钮、设置按钮
- **左侧栏**（宽 244，底色调深）：会话列表，按项目分组、可折叠、可滚动。
  单击选中并同步到右侧，双击恢复会话
- **右侧主区**（底色为「面」色）：
  - 路径栏：输入框 + 浏览按钮，实时校验
  - 当前项目卡片：项目名、完整路径、可用状态徽标、两个启动按钮、打开目录、收藏
  - 收藏夹：列表，每行「打开」「启动」
  - 底部：添加当前目录按钮 + 快捷键提示

### 5.2 配色 token

取自 Claude 产品用色。强调色 `#d97757` 已由 `claude_icon.ico` 中心像素采样确认。
所有灰阶偏暖（带黄红底调），不使用中性灰。

| Token | 浅色 | 深色 | 用途 |
|---|---|---|---|
| `bg` | `#efede4` | `#262624` | 窗口底、侧栏、顶栏 |
| `surface` | `#faf9f5` | `#30302e` | 内容区、卡片 |
| `sunken` | `#e6e3d7` | `#3a3937` | 中性标签、键帽 |
| `line` | `rgba(31,30,27,.10)` | `rgba(245,244,239,.10)` | 分隔线、卡片描边 |
| `line_strong` | `rgba(31,30,27,.17)` | `rgba(245,244,239,.18)` | 次要按钮描边 |
| `ink` | `#1f1e1b` | `#f5f4ef` | 标题与正文 |
| `ink_2` | `#6b6862` | `#b0aca3` | 次要文字、路径、时间 |
| `ink_3` | `#9b978e` | `#7f7b73` | 弱化标签、分组标题 |
| `accent` | `#d97757` | `#d97757` | 主按钮、选中态、收藏星标 |
| `accent_hi` | `#c4633f` | `#e89075` | 主按钮悬停 |
| `accent_soft` | `rgba(217,119,87,.13)` | `rgba(217,119,87,.17)` | 次要按钮底、选中行底 |
| `ok` | `#4f7d5c` | `#7fa98a` | 目录可用 |
| `danger` | `#b5533f` | `#d97b65` | 目录无效、删除 |

强调色在深浅两套中保持不变（暖橙在深底上对比度足够，无需反色）。

### 5.3 两个启动按钮的区分

原来靠色相区分（蓝=普通、橙=跳过权限），单色系下没有第二个色相可用。
改为同色系深浅：**普通启动**用实心 `accent`，**跳过权限**用 `accent_soft` 浅底 + `accent` 文字。
靠视觉重量而非色相区分主次。

### 5.4 图标

**所有图标由 `ui/icons.py` 在 Canvas 上绘制**（线段、多边形、圆弧），不使用 emoji、
不打包图标字体。原因：emoji 在不同 Windows 版本渲染差异大且无法控制颜色；
图标字体需额外打包二进制字体文件。手绘约 12 个图标可完全控制颜色与描边，
且天然适配主题切换。

需要绘制的图标：`folder`、`refresh`、`gear`、`play`、`bolt`、`star`（实心/空心）、
`chevron`、`clock`、`plus`、`open-external`、`x`。

**Claude 标志**用位图 `assets/claude-mark.png`（tkinter `PhotoImage` 支持 PNG），
由 `claude_icon.ico` 抠底生成：原图标为暖橙星芒 + 不透明深青灰底 `#4c6971`，
按底色距离做带软边的抠图并裁到内容边界。深色模式共用同一张图。

### 5.5 tkinter 实现限制（诚实说明）

mockup 中 11px 圆角卡片在 tkinter 里**无法直接实现**。tkinter 没有原生圆角，
圆角只能用 Canvas 的平滑多边形伪造，而 Canvas 多边形内无法直接摆放子控件
（需走 `create_window`，布局与动态内容会严重复杂化）。

因此实际实现为：

- **按钮与徽标**：保留并改进现有的 Canvas 圆角方案（`ModernButton` 已用此法，可行）
- **卡片与容器**：直角 + 1px 细描边，不伪造圆角

这是本次改动中唯一明确偏离 mockup 的地方。视觉上仍有暖色底、细描边、层次对比，
但卡片是直角。若必须圆角，需改为 Canvas 承载所有子控件，代价是布局代码复杂度大幅上升，
不建议在本次范围内做。

## 6. 交互规格

| 操作 | 行为 |
|---|---|
| 单击会话行 | 选中（高亮），路径同步到右侧输入框与当前项目卡片 |
| 双击会话行 | 以 `claude --resume <session_id>` 在会话 cwd 恢复该会话 |
| 单击项目分组标题 | 折叠 / 展开该组 |
| 双击项目分组标题 | 弹出模式选择对话框，选完启动 |
| 单击收藏行 | 选中，路径同步到右侧 |
| 收藏行「启动」 | 切到该路径并以当前模式启动 |
| 收藏行「打开」 | 在资源管理器中打开 |
| 会话行 ✕ | 确认后删除该 `.jsonl` 文件，就地刷新列表 |
| 顶部刷新 | 强制重扫会话目录并重建侧栏 |
| `Enter` | 以当前模式启动 |
| `Ctrl+O` | 打开目录浏览器 |
| `Esc` | 最小化到托盘 |
| 窗口关闭按钮 | 最小化到托盘（沿用现有行为） |
| 设置中「退出程序」 | 完全退出 |

## 7. 性能策略

问题：`rebuild_ui` 会触发全量重扫。原实现中切主题、加收藏、删收藏、清历史、删会话、
以及「不自动关闭」时每次启动都会重建界面，每次对 `~/.claude/projects` 下每个项目目录
取前 5 个 `.jsonl`，每个文件读两遍。50 个项目约 250 次文件读取。

策略：**内存缓存 + 局部重建**

1. `SessionStore` 首次访问时扫描一次，结果存于内存；后续访问直接返回缓存
2. 只有两种情况触碰磁盘：点击刷新按钮（全量重扫）；删除会话（直接从缓存移除该项，
   不重扫）
3. 界面骨架（顶栏、路径栏、当前项目卡片、底部）只在启动时构建一次
4. 会话侧栏与收藏夹各自置于独立容器，需要更新时只重建对应容器，不重建整个窗口
5. 展开状态存于 `set[str]`，容器重建后按集合恢复

只有切换主题走全量重建——因为颜色写死在每个控件构造参数上，而切主题是低频操作。

## 8. 错误处理

- **配置损坏**：JSON 解析失败或顶层非 dict 时回落默认值，并在状态栏提示
- **会话扫描异常**：单个 `.jsonl` 读取失败跳过该文件，不影响其余
- **命令未找到**：启动前检查 `claude` 是否在 PATH，找不到时弹窗给出安装命令
- **目录无效**：启动前校验，无效时弹窗并高亮输入框
- **顶层异常**：`main()` 用 try/except 包裹，弹出错误对话框（`pythonw` 下无控制台，
  否则用户只会看到程序闪退）
- **单实例锁失败**：端口被占用且无法连接已有实例时，弹窗说明并允许继续启动新实例

## 9. 测试策略

项目目前零测试。本次为两个不依赖界面的模块补最小测试：

**`sessions.py`**
- 用临时目录构造假 `.jsonl`，验证 cwd 提取
- 验证首个用户提问提取（含 `content` 为字符串和为 block 列表两种情况）
- 验证按真实 cwd 分组
- 验证缓存命中时不再读盘（monkeypatch `os.listdir` 计数）
- 验证 cwd 不存在的会话被跳过

**`config.py`**
- 损坏 JSON → 回落默认值
- 缺失字段 → 补默认值
- 类型错误（`auto_close` 为字符串）→ 回落默认值
- 旧版 `last_mode` 值（`yolo` / `interactive` / `run`）→ 回落 `normal`
- `recent_dirs` 与 `agent` 键被丢弃

界面部分手工验证：启动、切主题、加删收藏、刷新、单击选中、双击恢复、删除会话、
无效目录提示、单实例重复启动、托盘最小化与退出。

## 10. 命名与产物

统一为 **Claude Launcher**（当前项目存在三套并行命名）：

| 项 | 统一后 |
|---|---|
| 窗口标题 | `Claude Launcher` |
| Python 包 | `claude_launcher/` |
| 入口脚本 | `main.py` |
| 可执行文件 | `ClaudeLauncher.exe` |
| 快捷方式 | `Claude Launcher.lnk` |
| 配置文件 | `~/.claude_launcher_config.json`（路径不变，无需迁移） |

`claude_icon.ico` 从仓库根目录移入 `assets/`，与新增的 `claude-mark.png` 并列。
需同步更新三处引用：`ui/window.py` 的窗口图标加载路径、`ui/icons.py` 的标志位图路径、
`build.py` 的 `--add-data` 与 `--icon` 参数。

安装脚本三个（`install.ps1`、`install.bat`、`install_exe.bat`）合并为一个
`install.bat`，只创建 `Claude Launcher.lnk`（当前 `install.ps1` 建的是旧名
"Claude Launcher"、`install_exe.bat` 建的是 "AI Coding Launcher"，两套并存互相矛盾）。

`build.py` 需以 `--add-data` 打包整个 `assets/` 目录（否则运行时会因找不到图标而报错）。

## 11. 不做的事

- 不实现可缩放窗口（沿用固定尺寸，改为可缩放需要重做全部布局约束）
- 不为卡片伪造圆角（见 5.5）
- 不保留与 Codex / MiMo 的任何兼容代码或配置字段
- 不做多语言、主题自定义色、项目分组（原 README 路线图中的未完成项，不在本次范围）
- 不引入第三方 UI 库（保持纯 tkinter，仅 pystray + Pillow 两个依赖）
