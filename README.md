# Claude Launcher v3.0.0

> Windows 桌面启动器：管理 Claude Code 工作目录、启动模式与历史会话。

[![平台](https://img.shields.io/badge/平台-Windows%2010%2F11-0078D4?style=flat-square)](#系统要求)
[![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB?style=flat-square&logo=python&logoColor=white)](#从源码运行)
[![许可证](https://img.shields.io/badge/许可证-MIT-green?style=flat-square)](LICENSE)
[![Release](https://img.shields.io/github/v/release/shuli66/claude-workspace-launcher?style=flat-square)](https://github.com/shuli66/claude-workspace-launcher/releases/latest)

Claude Launcher 是 Claude Code 的轻量 Windows 图形启动器。它提供项目目录管理、普通或跳过权限启动、历史会话浏览与恢复，以及收藏夹和系统托盘功能。

> **权限提醒：**“跳过权限”启动会使用 Claude Code 的 `--dangerously-skip-permissions` 参数，跳过工具操作的权限确认。只在你信任且了解风险的工作目录中启用；不确定时请使用普通启动。

## 下载与安装

### Windows 预编译版本（推荐）

从 [GitHub Releases](https://github.com/shuli66/claude-workspace-launcher/releases/latest) 下载 `ClaudeLauncher-v3.0.0-win-x64.zip`。

1. 将 ZIP 解压到一个固定位置（例如 `%LOCALAPPDATA%\Programs\ClaudeLauncher`）。请保留解压后的整个 `ClaudeLauncher` 文件夹及其 `_internal` 子目录。
2. 双击文件夹内的 `install.bat`，创建或更新桌面快捷方式。
3. 启动器需要本机已安装 Claude Code，且 `claude` 命令能从 PATH 找到。

这是 **onedir** 分发包，不是单文件 exe；不要只复制 `ClaudeLauncher.exe`。首次运行前请确认你信任下载来源。若 Windows SmartScreen 显示提示，请先核对 Release 来源及文件信息，再自行决定是否运行。

### 从源码运行

需要 Windows 10/11、Python 3.7 或更新版本，以及 Git。

```powershell
git clone https://github.com/shuli66/claude-workspace-launcher.git
cd claude-workspace-launcher
py -m pip install -r requirements.txt
py main.py
```

也可以在项目目录运行 `run.bat`。

## 功能

### 项目与启动

- 输入或浏览选择工作目录，自动检查目录是否存在。
- 普通启动使用 Claude Code 标准权限流程；跳过权限启动添加 `--dangerously-skip-permissions`。
- 设置里可选择启动 Claude Code 后自动关闭启动器。
- 可选择“默认使用跳过权限模式启动会话”，启用后双击历史会话会以跳过权限参数恢复。
- 收藏常用项目，直接打开项目目录或启动 Claude Code。

### 会话管理

- 扫描 Claude Code 本地会话文件，按项目目录分组。
- 单击会话选中并同步项目路径；双击会话恢复；双击项目分组可选择启动模式。
- 项目分组可折叠，会话行显示首条有效提问及时间。
- 会话标题在可用宽度内截断，删除按钮保持在行尾；删除会话会移除对应本地会话文件，操作前会再次确认。
- 会话列表使用内存缓存；点刷新按钮可重新扫描。

### 界面与系统集成

- Claude 品牌风格的浅色、深色和跟随系统主题。
- 系统托盘、单实例检测、快捷键和启动错误提示。
- 900 × 620 固定窗口，左右分栏布局。

## 使用说明

### 启动项目

1. 在右侧路径栏输入工作目录，或点“浏览”选择目录。
2. 选择“普通启动”或“跳过权限”。
3. Claude Code 会在所选目录的新控制台窗口中启动。

### 恢复历史会话

- **单击**左侧会话：选中会话，并将其项目目录同步到右侧路径栏。
- **双击**左侧会话：使用 `claude --resume <会话ID>` 恢复。
- 在**设置 → 启动选项**中勾选“默认使用跳过权限模式启动会话”，双击恢复时会额外添加 `--dangerously-skip-permissions`。
- **双击**项目分组标题：打开启动模式选择对话框。
- 点击会话行末尾的 **✕**：确认后删除对应会话文件。

### 设置与快捷键

点击窗口右上角齿轮打开设置，可配置界面主题、启动后自动关闭，以及恢复会话时是否默认跳过权限。关闭主窗口会最小化到系统托盘；从设置面板可完全退出。

| 快捷键 | 功能 |
|---|---|
| `Enter` | 按当前启动模式启动所选目录 |
| `Ctrl+O` | 浏览并选择目录 |
| `Esc` | 最小化到系统托盘 |

## 系统要求

- Windows 10 或 Windows 11。
- Claude Code 已安装并可通过 PATH 运行。可按 Claude Code 官方安装说明安装；npm 安装方式为：

  ```powershell
  npm install -g @anthropic-ai/claude-code
  ```

- 使用预编译 Release 无需另外安装 Python。
- 从源码运行或自行构建需要 Python 3.7+。

## 配置与数据

配置文件位置：`%USERPROFILE%\.claude_launcher_config.json`。收藏夹、上次启动模式、关闭行为、默认恢复权限模式与界面主题保存在此处。

历史会话直接读取 Claude Code 用户目录下的 `~/.claude/projects/`。删除会话会删除相应的本地 JSONL 文件；若要保留记录，请勿执行删除。

## 自行打包

在 Windows 开发环境中安装项目依赖和 PyInstaller 后运行：

```powershell
py -m pip install -r requirements.txt
py -m pip install pyinstaller
py build.py
```

完整 onedir 产物位于 `dist/ClaudeLauncher/`。分发时应保留整个目录，并在同一目录中附带 `install.bat`；本仓库的构建脚本会复制该安装脚本。

## 开发与测试

```powershell
py -m pip install -r requirements.txt
py -m pip install pytest
py -m pytest -q
```

项目结构：

```text
main.py                 应用入口
claude_launcher/
  app.py                应用装配、托盘、单实例与异常处理
  config.py             配置读写、校验
  agent.py              Claude Code 命令构建与启动
  sessions.py           会话扫描、解析与缓存
  theme.py              主题色配置
  ui/
    window.py           主窗口
    widgets.py          界面控件
    dialogs.py          设置与启动模式对话框
    icons.py            图标绘制与资源加载
assets/                 Claude 标志与 Windows 图标
 tests/                 单元测试
tools/                  冒烟与交互验证脚本
build.py                PyInstaller onedir 构建脚本
install.bat             创建桌面快捷方式
run.bat                 从源码启动
```

## 问题排查

- **提示找不到 Claude Code：**在 PowerShell 中运行 `claude --version`；若命令无法识别，请先安装 Claude Code，或将其安装目录加入 PATH，然后重新打开启动器。
- **会话列表为空：**确认当前 Windows 用户曾在 Claude Code 中创建过会话，然后点顶部刷新按钮。只会列出项目目录仍然存在的会话。
- **快捷方式无法启动：**确认 ZIP 已完整解压且 `_internal` 目录仍与 exe 同级；在解压目录中重新运行 `install.bat`。
- **设置或收藏未保存：**检查 `%USERPROFILE%\.claude_launcher_config.json` 是否可写。损坏的配置会回落到默认值。
- **从源码运行时 Tk 初始化失败：**检查环境变量 `TCL_LIBRARY` / `TK_LIBRARY` 是否指向有效 Tcl/Tk 安装；打包脚本会在启动 PyInstaller 前清理这两个变量。

## 许可证

[MIT License](LICENSE)
