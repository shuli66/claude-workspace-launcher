# claude-workspace-launcher

> A polished Windows launcher for Claude Code with workspace selection, favorites, recent projects, dual launch modes, and a desktop-friendly workflow.
>
> 一个面向 Windows 的 Claude Code 启动器，支持工作区快速切换、收藏夹、最近项目、双启动模式，以及更顺手的桌面端工作流。

[![Platform](https://img.shields.io/badge/platform-Windows-0078D4?style=flat-square)](#)
[![Python](https://img.shields.io/badge/python-3.7%2B-3776AB?style=flat-square&logo=python&logoColor=white)](#requirements)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](./LICENSE)

## Why this project? | 为什么做这个项目

Claude Code 在 Windows PowerShell 里很好用，但每次手动切换目录、输入命令、决定启动模式，都会打断工作流。

`claude-workspace-launcher` 的目标很简单：

- **更快进入项目**：快速选择工作区、最近目录、收藏夹
- **更少重复操作**：一键普通启动或跳过权限启动
- **更像专业桌面工具**：当前工作区卡片、状态提示、资源管理器集成
- **更适合日常开发**：为频繁使用 Claude Code 的 Windows 用户优化

---

## Features | 功能特性

### Core workflow | 核心工作流
- Workspace selection with direct path input
- Real-time path validation
- Recent directories visualization
- Favorites management with instant refresh
- Current workspace action card
- Dual launch buttons:
  - **Normal Launch** / 普通启动
  - **Skip-Permissions Launch** / 跳过权限启动

### Desktop-friendly UX | 桌面体验优化
- Explorer integration (`📂`)
- System tray support (minimize to tray)
- Single instance (activate existing window)
- Status bar feedback
- Auto-close after launch
- Keyboard shortcuts
- Custom Claude icon for app window and shortcut
- Windows shortcut installer scripts
- No PowerShell window popup

### UI polish | 界面优化
- Theme switching (Light / Dark / Auto follow system)
- Modern themes inspired by VS Code / JetBrains tools
- Clear visual hierarchy
- Top action card for current workspace
- Interactive recent/favorite items
- Smooth window initialization (no flicker)

---

## Preview | 界面预览

```text
┌──────────────────────────────────────────────┐
│ Claude Code                                  │
│ Quick workspace launcher for Windows         │
├──────────────────────────────────────────────┤
│ Current Workspace                            │
│ project-name                                 │
│ D:\Projects\my-app                         │
│ [valid] [last launch: normal]                │
│ [Normal Launch] [Skip-Permissions Launch]    │
│ [📂] [★]                                     │
├──────────────────────────────────────────────┤
│ Workspace Path                               │
│ [input path____________________] [Browse][📂]│
├──────────────────────────────────────────────┤
│ Recent Directories                           │
│ Favorites                                    │
├──────────────────────────────────────────────┤
│ Launch Options                               │
│ [x] Auto-close after launch                  │
├──────────────────────────────────────────────┤
│ [Add to Favorites] [Clear History]           │
│ Enter = normal launch                        │
└──────────────────────────────────────────────┘
```

---

## Requirements

### For EXE version (推荐)
- Windows 10/11
- Claude Code installed and available in PATH

### For Python version (开发者)
- Windows 10/11
- Python 3.7+
- Claude Code installed and available in PATH

Dependencies (auto-installed):
- pystray (system tray support)
- Pillow (icon rendering)

---

## Installation | 安装方式

### Option 1: Download EXE (推荐 / Recommended)

**最简单的方式 - 无需安装 Python**

1. 从 [Releases](https://github.com/shuli66/claude-workspace-launcher/releases) 下载最新的 `ClaudeLauncher.exe`
2. 将 exe 文件放到任意目录（建议：`C:\Program Files\ClaudeLauncher\`）
3. 双击 `install_exe.bat` 创建桌面快捷方式
4. 或者直接双击 `ClaudeLauncher.exe` 运行

**优点**：
- ✅ 无需安装 Python
- ✅ 无需安装依赖
- ✅ 双击即用
- ✅ 适合所有 Windows 用户

### Option 2: Run from source (开发者)

**需要 Python 环境**

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python claude_launcher.py`

Or use the installer scripts:
- PowerShell: Right-click `install.ps1` and run
- Batch: Double-click `install.bat`

---

## Build from source | 从源码打包

If you want to build the exe yourself:

```bash
pip install pyinstaller
python build.py
```

The exe will be generated in `dist/ClaudeLauncher.exe`

---

## Usage | 使用方法

### Basic usage

1. Launch the app from the desktop shortcut
2. Type or browse a workspace path
3. Check the current workspace card
4. Choose one of the two launch buttons:
   - **普通启动 / Normal Launch**
   - **跳过权限启动 / Skip-Permissions Launch**

### Launch modes

#### Normal Launch
Runs:

```bash
claude
```

Use this when you want standard permission confirmation behavior.

#### Skip-Permissions Launch
Runs:

```bash
claude --dangerously-skip-permissions
```

Use this only when you understand the tradeoff and want a faster, less interruptive workflow.

---

## Keyboard shortcuts | 快捷键

- `Enter` → Normal Launch
- `Ctrl + O` → Browse directory
- `Esc` → Minimize to system tray

### System tray | 系统托盘

- Close window or press `Esc` to minimize to system tray
- Right-click tray icon to show window or quit
- Double-click desktop shortcut when running will activate existing window

### Theme switching | 主题切换

Choose from three theme options in Launch Options:
- **Auto** (跟随系统): Follows Windows system theme
- **Light** (浅色): Light theme
- **Dark** (深色): Dark theme

---

## Project structure

```text
claude-workspace-launcher/
├── claude_launcher.py
├── claude_icon.ico
├── requirements.txt
├── install.ps1
├── install.bat
├── run.bat
├── create_icon.py
├── download_icon.py
├── README.md
├── LICENSE
└── .gitignore
```

---

## Configuration | 配置文件

The launcher stores user preferences in:

```text
%USERPROFILE%\.claude_launcher_config.json
```

Example:

```json
{
  "recent_dirs": [
    "D:\\Projects\\my-app",
    "C:\\Work\\tooling"
  ],
  "favorites": [
    "D:\\Projects\\my-app"
  ],
  "last_mode": "normal",
  "auto_close": true
}
```

---

## Troubleshooting | 常见问题

### Shortcut icon looks wrong
- Re-run `install.ps1`
- Delete the old desktop shortcut first if needed
- Windows may cache shortcut icons; recreating the shortcut usually fixes it

### Launcher window opens but Claude does not start
- Make sure `claude` is installed and available in PATH
- Run `claude --version` in PowerShell to verify

### Path validation says invalid
- Confirm the input is a real directory
- Use the Browse button to avoid typo issues

---

## Roadmap

- [ ] Git branch / repository status in current workspace card
- [ ] Scrollable recent/favorites lists
- [ ] Theme switching
- [ ] Project grouping
- [ ] Better packaging for easier installation

---

## Contributing

Issues and pull requests are welcome.

If you have ideas to improve the Windows workflow for Claude Code, feel free to open an issue.

---

## License

MIT License

---

## Star this repo

If this launcher saves you time when using Claude Code on Windows, consider giving it a star.

如果这个项目让你在 Windows 上使用 Claude Code 更顺手，欢迎点一个 Star。