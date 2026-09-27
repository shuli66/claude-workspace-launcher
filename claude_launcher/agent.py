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
