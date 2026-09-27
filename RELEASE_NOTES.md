# Claude Launcher v2.1.0

> 重构版本。从「支持三个 AI 工具的单文件程序」回归为专注 Claude Code 的模块化应用。

## 为什么会有这次重构

v2.0.0 为支持 Claude Code / Codex CLI / MiMo Code 三个工具引入了大量分支。实际使用中只用到 Claude Code，另两个工具的判断逻辑、会话扫描器与配置项都成了纯粹的负担。

同时排查出 5 个影响使用的缺陷，一并在本次修复。

## 移除

- **Codex CLI 支持** —— 配置块、会话扫描器（rollout JSONL 解析）、YOLO 模式
- **MiMo Code 支持** —— 配置块、SQLite 会话扫描、交互/单次执行模式
- **工具选择器** —— 顶部整条工具栏，窗口高度因此减少 44px
- **「最近目录」与「清除历史」** —— 该功能在界面上从未被渲染过，「清除历史」按钮点了没有任何反应
- **两处死代码** —— `FavoriteItem` 与 `FolderGroup` 两个类从未被实例化
- **三套并行的安装脚本与命名** —— 原先窗口标题叫「AI Coding Launcher」、类名与文件名是「ClaudeLauncher」、三个安装脚本各自创建的快捷方式名还都不一样（`Claude Launcher.lnk` 与 `AI Coding Launcher.lnk`）。现合并为单一 `install.bat`，创建的快捷方式名统一为 `ClaudeLauncher.exe.lnk`；窗口标题、包名、可执行文件名统一为 **Claude Launcher / ClaudeLauncher**

## 修复的缺陷

| 缺陷 | 原因 | 现状 |
|---|---|---|
| 设置里「自动关闭」开关无效 | 设置写入 config，但启动时读的是另一个不同步的变量，还用旧值把设置覆盖回去 | 统一走 config |
| 切换主题时对话框重复销毁 | 父窗口重建会销毁全部子控件（含设置对话框），之后再销毁一次会抛 `TclError` | 改为先关闭对话框再切换 |
| 「清除历史」按钮点了没反应 | 界面从不渲染最近目录列表 | 功能与按钮一并移除 |
| 端口被占用时双击图标毫无反应 | 单实例检测失败后直接静默退出，无任何提示 | 弹窗说明并继续启动 |
| 单击会话项会直接启动 agent | 会话行的单击事件绑定了启动 | 改为单击选中、双击恢复 |

## 界面重做

- **左右分栏布局**：会话列表常驻左侧，右侧为当前项目的路径、状态与启动操作。窗口 900×620，内容不再溢出高度
- **配色取自 Claude 品牌**：奶油米底 `#efede4`、珊瑚橙 `#d97757`（该色值由 `claude_icon.ico` 中心像素采样确认）、暖炭灰深色底 `#262624`。全部灰阶偏暖，不使用中性灰
- **图标改为 Canvas 手绘**：原先用 emoji（⚡🤖🧠📂★🕘），在不同 Windows 版本渲染不一致且无法跟随主题换色
- **布局状态保留**：折叠状态在列表刷新后不再丢失

## 性能

原先每次界面重建都会重扫磁盘 —— 切换主题、加删收藏、删除会话、以及关闭自动关闭时每次启动，都会对 `~/.claude/projects` 下每个项目读取前 5 个会话文件两遍。50 个项目约 250 次文件读取。

现在扫描结果缓存在内存中，只有启动时、点刷新按钮、以及删除会话时才会触碰磁盘。界面骨架只构建一次，会话列表与收藏夹各自独立更新。

## 架构

从单文件 2184 行拆分为按职责分层的包：

```
main.py              入口
claude_launcher/
  app.py             装配、单实例锁、托盘、异常兜底
  config.py          配置读写与校验
  theme.py           配色 token
  sessions.py        会话扫描与缓存
  agent.py           命令构建与启动
  ui/                界面层
```

`config` / `theme` / `sessions` / `agent` 四个模块不依赖 tkinter，可脱离界面单独测试。测试从 0 增加到 63 个。

## 升级须知

配置文件会**自动迁移**，无需手动处理：

- `agent` 字段被丢弃（只剩 Claude 一个工具）
- `last_mode` 若为旧值（`yolo` / `interactive` / `run`）会回落到 `normal`
- `recent_dirs` 字段被丢弃

## 系统要求

- Windows 10 / 11
- Claude Code 已安装且在 PATH 中：`npm install -g @anthropic-ai/claude-code`

## 许可证

MIT License —— 详见 [LICENSE](./LICENSE)
