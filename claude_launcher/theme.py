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
