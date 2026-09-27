import subprocess

import pytest

from claude_launcher import agent


def test_modes_has_exactly_two_entries():
    assert set(agent.MODES) == {"normal", "skip"}


def test_skip_mode_carries_permission_flag():
    assert agent.MODES["skip"]["args"] == ["--dangerously-skip-permissions"]


def test_normal_mode_has_no_extra_args():
    assert agent.MODES["normal"]["args"] == []


def test_build_command_returns_none_when_binary_missing(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: None)
    assert agent.build_command("normal") is None


def test_build_command_normal(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    assert agent.build_command("normal") == ["C:\\bin\\claude.exe"]


def test_build_command_skip_appends_flag(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    assert agent.build_command("skip") == [
        "C:\\bin\\claude.exe",
        "--dangerously-skip-permissions",
    ]


def test_build_command_unknown_mode_returns_none(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    assert agent.build_command("yolo") is None


def test_cmd_extension_is_wrapped_in_comspec(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.cmd")
    monkeypatch.setenv("COMSPEC", "C:\\Windows\\system32\\cmd.exe")
    cmd = agent.build_command("normal")
    assert cmd == ["C:\\Windows\\system32\\cmd.exe", "/c", "C:\\bin\\claude.cmd"]


def test_bat_extension_is_wrapped_in_comspec(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.bat")
    monkeypatch.setenv("COMSPEC", "C:\\Windows\\system32\\cmd.exe")
    assert agent.build_command("normal")[1] == "/c"


def test_is_valid_directory(tmp_path):
    assert agent.is_valid_directory(str(tmp_path)) is True
    assert agent.is_valid_directory(str(tmp_path / "absent")) is False
    assert agent.is_valid_directory("") is False


def test_launch_rejects_missing_directory(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    with pytest.raises(agent.LaunchError):
        agent.launch("D:\\definitely\\absent\\path", "normal")


def test_launch_rejects_missing_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: None)
    with pytest.raises(agent.LaunchError):
        agent.launch(str(tmp_path), "normal")


def test_launch_spawns_in_new_console(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    captured = {}

    def fake_popen(cmd, cwd=None, creationflags=0):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["creationflags"] = creationflags
        return object()

    monkeypatch.setattr(agent.subprocess, "Popen", fake_popen)
    cmd = agent.launch(str(tmp_path), "normal")

    assert cmd == ["C:\\bin\\claude.exe"]
    assert captured["cwd"] == str(tmp_path)
    # agent 必须在独立控制台里启动，否则用户看不到 Claude Code 的交互界面
    assert captured["creationflags"] == subprocess.CREATE_NEW_CONSOLE


def test_launch_falls_back_to_normal_for_unknown_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    monkeypatch.setattr(agent.subprocess, "Popen", lambda *a, **k: object())
    assert agent.launch(str(tmp_path), "yolo") == ["C:\\bin\\claude.exe"]


def test_resume_appends_session_id(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    captured = {}

    def fake_popen(cmd, cwd=None, creationflags=0):
        captured["cmd"] = cmd
        return object()

    monkeypatch.setattr(agent.subprocess, "Popen", fake_popen)
    cmd = agent.resume(str(tmp_path), "abc-123")

    assert cmd == ["C:\\bin\\claude.exe", "--resume", "abc-123"]
    assert captured["cmd"] == cmd


def test_resume_rejects_missing_directory(monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    with pytest.raises(agent.LaunchError):
        agent.resume("D:\\absent\\nope", "abc")


def test_resume_without_session_id_omits_argument(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: "C:\\bin\\claude.exe")
    monkeypatch.setattr(agent.subprocess, "Popen", lambda *a, **k: object())
    assert agent.resume(str(tmp_path), "") == ["C:\\bin\\claude.exe", "--resume"]


def test_launch_reports_install_hint_when_binary_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.shutil, "which", lambda name: None)
    with pytest.raises(agent.LaunchError) as excinfo:
        agent.launch(str(tmp_path), "normal")
    assert "npm install -g @anthropic-ai/claude-code" in excinfo.value.message
