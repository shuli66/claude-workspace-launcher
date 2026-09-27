import json
from pathlib import Path

import pytest

from claude_launcher.config import Config, DEFAULT_PATH


def write_config(tmp_path, payload):
    path = tmp_path / "cfg.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_default_path_is_home_config():
    assert DEFAULT_PATH == Path.home() / ".claude_launcher_config.json"


def test_missing_file_yields_defaults(tmp_path):
    cfg = Config(tmp_path / "nope.json")
    cfg.load()
    assert cfg.get("favorites") == []
    assert cfg.get("last_mode") == "normal"
    assert cfg.get("auto_close") is True
    assert cfg.get("theme") == "auto"
    assert cfg.warning is None


def test_corrupt_json_falls_back_with_warning(tmp_path):
    cfg = Config(write_config(tmp_path, "{ this is not json"))
    cfg.load()
    assert cfg.get("last_mode") == "normal"
    assert cfg.warning is not None


def test_non_dict_top_level_falls_back_with_warning(tmp_path):
    cfg = Config(write_config(tmp_path, "[1, 2, 3]"))
    cfg.load()
    assert cfg.get("theme") == "auto"
    assert cfg.warning is not None


def test_unknown_keys_are_dropped(tmp_path):
    cfg = Config(write_config(tmp_path, {
        "recent_dirs": ["D:\\old"],
        "agent": "codex",
        "favorites": ["D:\\proj"],
        "last_mode": "normal",
        "auto_close": True,
        "theme": "light",
    }))
    cfg.load()
    assert "recent_dirs" not in cfg.data
    assert "agent" not in cfg.data
    assert cfg.get("favorites") == ["D:\\proj"]


@pytest.mark.parametrize("legacy", ["yolo", "interactive", "run", "bogus"])
def test_legacy_last_mode_falls_back(tmp_path, legacy):
    cfg = Config(write_config(tmp_path, {"last_mode": legacy}))
    cfg.load()
    assert cfg.get("last_mode") == "normal"


def test_valid_last_mode_is_kept(tmp_path):
    cfg = Config(write_config(tmp_path, {"last_mode": "skip"}))
    cfg.load()
    assert cfg.get("last_mode") == "skip"


def test_bad_types_fall_back(tmp_path):
    cfg = Config(write_config(tmp_path, {
        "auto_close": "yes",
        "theme": "neon",
        "favorites": "not-a-list",
    }))
    cfg.load()
    assert cfg.get("auto_close") is True
    assert cfg.get("theme") == "auto"
    assert cfg.get("favorites") == []


def test_favorites_are_normalized_and_capped(tmp_path):
    many = ["D:\\p%d" % i for i in range(15)]
    cfg = Config(write_config(tmp_path, {"favorites": many + many}))
    cfg.load()
    favs = cfg.get("favorites")
    assert len(favs) <= 10
    assert len(set(favs)) == len(favs)


def test_save_then_load_roundtrips(tmp_path):
    path = tmp_path / "cfg.json"
    cfg = Config(path)
    cfg.load()
    cfg.set("last_mode", "skip")
    cfg.set("favorites", ["D:\\proj"])
    cfg.save()

    again = Config(path)
    again.load()
    assert again.get("last_mode") == "skip"
    assert again.get("favorites") == ["D:\\proj"]
