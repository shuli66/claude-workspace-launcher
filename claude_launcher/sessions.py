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

# 会话 jsonl 里 type 为 user 的条目不一定是用户真的输入：harness 会注入
# 包装消息（<local-command-caveat>、<command-name>、system-reminder 等），
# 它们若被当作「首个提问」展示，列表里就会出现无意义的标签文本。
_NOISE_MARKERS = (
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<command-name>",
    "<command-message>",
    "<command-args>",
    "<system-reminder>",
    "<task-notification>",
)


def _is_noise(text):
    stripped = text.strip()
    if not stripped:
        return True
    return stripped.startswith(_NOISE_MARKERS)


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


def _one_line(text):
    """会话行高固定，多行文本会被垂直居中裁剪成半截字——压成单行。"""
    return " ".join(text.split())


def extract_first_prompt(jsonl_file: str) -> str:
    for obj in _read_json_lines(jsonl_file):
        if not isinstance(obj, dict) or obj.get("type") != "user":
            continue

        content = (obj.get("message") or {}).get("content", "")
        if isinstance(content, str) and content:
            if not _is_noise(content):
                return _one_line(content)[:PROMPT_LIMIT]
            continue

        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text and not _is_noise(text):
                        return _one_line(text)[:PROMPT_LIMIT]
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
