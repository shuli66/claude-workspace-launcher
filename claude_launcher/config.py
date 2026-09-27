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


def _defaults() -> Dict[str, Any]:
    """SCHEMA 的独立副本。

    必须逐键复制可变值：dict(SCHEMA) 是浅拷贝，会让所有实例共享
    SCHEMA["favorites"] 那同一个列表对象，调用方就地修改它就会污染
    进程级默认值——此后「配置文件不存在」也返回被污染的数据。
    """
    return {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in SCHEMA.items()
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
        self.data: Dict[str, Any] = _defaults()
        self.warning: Optional[str] = None

    def load(self) -> None:
        self.data = _defaults()
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
