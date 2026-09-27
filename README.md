# Claude Launcher

> 一个专为 Windows 设计的 Claude Code 启动器。可视化管理工作区、一键启动、浏览并恢复历史会话。

[![Platform](https://img.shields.io/badge/平台-Windows-0078D4?style=flat-square)](#)
[![Python](https://img.shields.io/badge/python-3.7%2B-3776AB?style=flat-square&logo=python&logoColor=white)](#系统要求)
[![License](https://img.shields.io/badge/许可证-MIT-green?style=flat-square)](./LICENSE)

## 为什么需要这个工具

Claude Code 在终端里很好用，但在 Windows 上每次都要：

- 手动 `cd` 到项目目录
- 输入 `claude` 命令
- 记住各个项目的路径
- 想恢复上次的会话时，还得翻找会话 ID

**Claude Launcher 把这四步变成一次点击。**

- 一键启动，无需命令行
- 可视化管理工作区，收藏常用项目
- 浏览历史会话并一键恢复
- 界面配色取自 Claude 品牌

---

## 界面预览

> 截图待更新为新版左右分栏界面。运行 `python main.py` 可查看当前界面。

---

## 功能

### 启动
- **两种启动模式**：普通启动 / 跳过权限
- **自动记忆**：记住上次使用的模式
- **快捷键**：`Enter` 启动、`Ctrl+O` 浏览目录、`Esc` 最小化到托盘

### 工作区
- **路径输入**：直接输入或粘贴目录路径（自动清理「复制为路径」带来的引号）
- **实时校验**：输入时即显示「✓ 可用」或「✕ 无效」
- **资源管理器集成**：一键在资源管理器中打开

### 会话
- **自动扫描**：读取 `~/.claude/projects` 下的历史会话
- **按项目分组**：可折叠，显示每个会话的首个提问、时间与大小
- **单击选中**：同步路径到输入框
- **双击恢复**：以 `claude --resume <会话ID>` 直接恢复
- **删除会话**：在列表内直接删除
- **内存缓存**：切换主题、加删收藏不会重扫磁盘；点顶部刷新按钮可强制重扫

### 收藏夹
- **一键收藏**：点 ☆ 加入收藏夹
- **直接启动**：从收藏夹启动项目或打开目录

### 外观与体验
- **主题**：浅色 / 深色 / 跟随系统（配色取自 Claude 品牌）
- **系统托盘**：关闭窗口最小化到托盘，不占任务栏
- **单实例**：重复启动会激活已有窗口
- **异常兜底**：出错时弹窗提示，不会静默闪退

---

## 安装

### 方式一：下载 EXE（推荐）

**无需安装 Python。**

1. 前往 [Releases](https://github.com/shuli66/claude-workspace-launcher/releases/latest) 下载 `ClaudeLauncher.exe`
2. 同时下载 `install.bat`
3. 将两个文件放在同一目录（推荐 `C:\Program Files\ClaudeLauncher\`）
4. 双击 `install.bat` 创建桌面快捷方式
5. 双击桌面上的 **ClaudeLauncher.exe** 启动

### 方式二：从源码运行

需要 Python 3.7 或更高版本。

```bash
git clone https://github.com/shuli66/claude-workspace-launcher.git
cd claude-workspace-launcher
pip install -r requirements.txt
python main.py
```

或直接双击 `run.bat`。

---

## 使用指南

### 基本流程

1. **选择工作目录** —— 在路径栏输入，或点「浏览」选择。路径会实时校验。
2. **选择启动模式** —— 点「普通启动」或「跳过权限」。
3. **开始工作** —— 启动后在 Claude Code 里正常操作。

### 会话列表（左侧栏）

- **单击**会话行：选中，并把该项目路径同步到右侧
- **双击**会话行：以 `--resume` 恢复该会话
- **单击**项目分组标题：折叠 / 展开
- **双击**项目分组标题：弹出启动模式选择对话框
- 点会话行右侧的 **✕**：删除该会话（不可撤销）

### 设置（右上角 ⚙）

- **外观主题**：浅色 / 深色 / 跟随系统（切换后界面立即重建）
- **启动选项**：是否在启动 Claude Code 后自动关闭启动器
- **退出程序**：完全退出（关窗口只是最小化到托盘）

### 快捷键

| 按键 | 作用 |
|---|---|
| `Enter` | 以当前模式启动 |
| `Ctrl+O` | 打开目录浏览器 |
| `Esc` | 最小化到托盘 |

---

## 系统要求

- Windows 10 或 Windows 11
- 已安装 Claude Code，且 `claude` 命令在 PATH 中
  ```bash
  npm install -g @anthropic-ai/claude-code
  ```
- 源码运行另需 Python 3.7+，依赖 `pystray` 与 `Pillow`

---

## 配置文件

配置文件位于用户目录：

```
%USERPROFILE%\.claude_launcher_config.json
```

```json
{
  "favorites": [
    "D:\\Projects\\my-app"
  ],
  "last_mode": "normal",
  "auto_close": true,
  "theme": "auto"
}
```

| 字段 | 说明 |
|---|---|
| `favorites` | 收藏的项目目录，最多 10 个 |
| `last_mode` | 上次使用的启动模式：`normal` 或 `skip` |
| `auto_close` | 启动 Claude Code 后是否自动关闭启动器 |
| `theme` | 主题：`auto` / `light` / `dark` |

配置会在启动时自动校验：无效的取值会回落到默认值，未知字段会被丢弃，文件随即被重写为干净版本。若文件损坏，程序会使用默认设置并在状态栏提示，不会崩溃。

---

## 从源码打包

```bash
pip install pyinstaller
python build.py
```

产物为 `dist/ClaudeLauncher.exe`（约 27 MB）。分发时需同时提供 `assets/` 目录之外的 `install.bat` 用于创建快捷方式。

---

## 项目结构

```
claude-launcher/
├── main.py                     # 入口
├── claude_launcher/
│   ├── app.py                  # 应用装配、单实例锁、托盘、异常兜底
│   ├── config.py               # 配置读写、校验与迁移
│   ├── theme.py                # 配色 token（Claude 品牌）
│   ├── sessions.py             # 会话扫描与内存缓存
│   ├── agent.py                # Claude Code 命令构建与启动
│   └── ui/
│       ├── window.py           # 主窗口（左右分栏）
│       ├── widgets.py          # 按钮、徽标、列表行等控件
│       ├── dialogs.py          # 设置与启动模式对话框
│       └── icons.py            # Canvas 手绘图标
├── assets/
│   ├── claude-mark.png         # Claude 标志（已去底）
│   └── claude_icon.ico         # 窗口与任务栏图标
├── tests/                      # 单元测试
├── tools/                      # 冒烟脚本与资源生成脚本
├── build.py                    # PyInstaller 打包脚本
├── install.bat                 # 创建桌面快捷方式
└── requirements.txt
```

---

## 常见问题

**快捷方式图标显示异常**
重新运行 `install.bat`。图标取自 exe 自身的内嵌资源，不依赖 `assets/` 目录。若仍不显示，是 Windows 缓存了旧图标——删除桌面快捷方式后重新运行 `install.bat` 即可。

**窗口打开了但 Claude Code 没启动**
确认 `claude` 命令在 PATH 中：在 PowerShell 里运行 `claude --version`。也确认所选目录真实存在。

**路径校验显示无效**
确认输入的是真实存在的目录。从资源管理器「复制为路径」带来的引号会被自动清理；若仍无效，用「浏览」按钮重新选择。

**想完全退出程序**
关窗口只会最小化到托盘。右键托盘图标选「退出程序」，或在设置面板点「退出程序」。

**提示端口被其他程序占用**
启动器用本地端口做单实例检测。若该端口被别的程序占用，会提示你并继续启动（旧版本此时会静默退出、双击无反应）。

**会话列表是空的**
在任意目录用 Claude Code 工作过之后，会话才会出现。也可点顶部刷新按钮重扫。

---

## 开发

```bash
# 运行测试（63 个）
python -m pytest -q

# 冒烟检查
python tools/smoke_app.py
python tools/smoke_window.py
python tools/smoke_dialogs.py
python tools/smoke_widgets.py
python tools/smoke_icons.py
```

> 注：若本机 `TCL_LIBRARY` / `TK_LIBRARY` 环境变量指向失效路径，tkinter 初始化会失败。冒烟脚本已在导入 tkinter 前自行置空这两个变量。

---

## 许可证

MIT License —— 详见 [LICENSE](./LICENSE)
