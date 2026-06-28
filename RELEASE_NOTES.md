# AI Coding Launcher v2.0.0

> 重大更新！从单一 Claude Code 启动器升级为多工具 AI 编程启动器，支持 Claude Code、Codex CLI 和 MiMo Code。

## 🆕 v2.0.0 新增功能

### 多工具支持
- 🔀 **三工具切换**：支持 Claude Code、Codex CLI、MiMo Code
- 🎯 **工具选择器**：顶部工具栏一键切换，自动检测可用状态
- ⚙️ **独立配置**：每个工具独立的启动模式和环境变量检查

### 会话管理
- 📂 **会话浏览**：从实际会话目录读取，按项目/日期分组显示
- 📝 **会话预览**：显示提问内容、时间、文件大小
- 🔄 **会话恢复**：双击会话直接恢复对应 agent 的会话
- 🗑️ **会话删除**：支持删除 Claude/Codex 的会话文件

### 智能交互
- 🖱️ **双击文件夹**：弹出模式选择对话框，选择启动模式
- 🖱️ **双击会话**：直接恢复该会话
- ➕ **折叠/展开**：会话分组支持折叠展开
- 🚫 **路径验证**：只显示目录确实存在的会话

### 各工具启动模式

| 工具 | 模式 | 说明 |
|------|------|------|
| Claude Code | 普通启动 | 标准权限确认流程 |
| Claude Code | 跳过权限 | 快速启动，跳过权限提示 |
| Codex CLI | 沙箱启动 | 标准沙箱模式（推荐） |
| Codex CLI | YOLO 模式 | 跳过所有审批（仅限隔离环境） |
| MiMo Code | 交互模式 | 启动 TUI 交互界面（推荐） |
| MiMo Code | 单次执行 | 执行单个任务后退出 |

## 📦 下载安装

### EXE 版本（推荐）

**无需安装 Python，开箱即用！**

1. 下载 `ClaudeLauncher.exe`
2. 下载 `install_exe.bat`
3. 将两个文件放在同一目录
4. 双击 `install_exe.bat` 创建桌面快捷方式

### 从源码运行

需要 Python 3.7+ 环境：

```bash
git clone https://github.com/shuli66/claude-workspace-launcher.git
cd claude-workspace-launcher
pip install -r requirements.txt
python claude_launcher.py
```

## ⚙️ 系统要求

- Windows 10/11
- 至少安装以下一种 AI 编程工具：
  - Claude Code（`npm install -g @anthropic-ai/claude-code`）
  - Codex CLI（`npm install -g @openai/codex`，需要 OpenAI API Key）
  - MiMo Code（`npm install -g @mimo-ai/cli`，需要 MiMo API Key）

## 📝 更新日志

### v2.0.0 (2026-06-29)

**重大更新 - 多工具支持**
- ✅ 支持 Claude Code、Codex CLI、MiMo Code 三种工具
- ✅ 工具选择器 UI
- ✅ 从实际会话目录读取会话信息
- ✅ 双击文件夹弹出模式选择
- ✅ 双击会话恢复功能
- ✅ 会话删除功能
- ✅ 可折叠的会话分组
- ✅ 路径验证和存在性检查
- ✅ 环境变量预检查（防止闪退）
- ✅ 模式验证和回退机制

### v1.0.0 (2026-05-08)

**首次发布**
- ✅ Claude Code 快速启动
- ✅ 工作区管理
- ✅ 收藏夹系统
- ✅ 主题切换
- ✅ 系统托盘
- ✅ 设置对话框

## 🙏 致谢

感谢所有测试和反馈的用户！

## 📄 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

**如有问题或建议，欢迎提 [Issue](https://github.com/shuli66/claude-workspace-launcher/issues)！**
