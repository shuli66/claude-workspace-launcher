import pytest

from claude_launcher.theme import detect_system_theme, resolve

REQUIRED_TOKENS = {
    "bg", "surface", "sunken", "line", "line_strong",
    "ink", "ink_2", "ink_3",
    "accent", "accent_hi", "accent_soft",
    "ok", "ok_soft", "danger", "danger_bg", "hover",
}


@pytest.mark.parametrize("name", ["light", "dark"])
def test_every_token_present(name):
    colors = resolve(name)
    assert REQUIRED_TOKENS <= set(colors)


def test_accent_is_claude_orange_in_both_themes():
    assert resolve("light")["accent"] == "#d97757"
    assert resolve("dark")["accent"] == "#d97757"


def test_light_and_dark_differ():
    assert resolve("light")["bg"] != resolve("dark")["bg"]


def test_auto_follows_system():
    assert resolve("auto", system_theme="light")["bg"] == resolve("light")["bg"]
    assert resolve("auto", system_theme="dark")["bg"] == resolve("dark")["bg"]


def test_unknown_theme_falls_back_to_dark():
    assert resolve("neon")["bg"] == resolve("dark")["bg"]


def test_detect_returns_valid_value():
    assert detect_system_theme() in ("light", "dark")


def test_all_values_are_strings():
    for name in ("light", "dark"):
        for token, value in resolve(name).items():
            assert isinstance(value, str), token
            assert value, token
