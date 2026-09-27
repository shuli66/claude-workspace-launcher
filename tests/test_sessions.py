import json
import os
from pathlib import Path

from claude_launcher.sessions import (
    MAX_PROJECTS,
    MAX_SESSIONS_PER_PROJECT,
    SessionStore,
    extract_cwd,
    extract_first_prompt,
)


def make_session(projects_dir, encoded_name, session_id, cwd, prompt, mtime=1000.0):
    """写出一个仿真的 Claude Code 会话文件。"""
    project_dir = projects_dir / encoded_name
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / (session_id + ".jsonl")

    lines = [
        json.dumps({"type": "summary", "cwd": cwd}),
        json.dumps({
            "type": "user",
            "cwd": cwd,
            "message": {"content": prompt},
        }),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path


def test_extract_cwd_reads_first_cwd_field(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        json.dumps({"type": "user", "cwd": "D:\\proj"}) + "\n",
        encoding="utf-8",
    )
    assert extract_cwd(str(path)) == "D:\\proj"


def test_extract_cwd_skips_corrupt_lines(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        "not json\n" + json.dumps({"cwd": "D:\\good"}) + "\n",
        encoding="utf-8",
    )
    assert extract_cwd(str(path)) == "D:\\good"


def test_extract_cwd_missing_file_returns_empty(tmp_path):
    assert extract_cwd(str(tmp_path / "gone.jsonl")) == ""


def test_extract_prompt_from_string_content(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        json.dumps({"type": "user", "message": {"content": "重构登录模块"}}) + "\n",
        encoding="utf-8",
    )
    assert extract_first_prompt(str(path)) == "重构登录模块"


def test_extract_prompt_from_block_list(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        json.dumps({
            "type": "user",
            "message": {"content": [{"type": "text", "text": "修复分页组件"}]},
        }) + "\n",
        encoding="utf-8",
    )
    assert extract_first_prompt(str(path)) == "修复分页组件"


def test_extract_prompt_is_truncated(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        json.dumps({"type": "user", "message": {"content": "x" * 500}}) + "\n",
        encoding="utf-8",
    )
    assert len(extract_first_prompt(str(path))) == 80


def test_extract_prompt_skips_non_user_entries(tmp_path):
    path = tmp_path / "s.jsonl"
    lines = [
        json.dumps({"type": "assistant", "message": {"content": "hi"}}),
        json.dumps({"type": "user", "message": {"content": "真正的问题"}}),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert extract_first_prompt(str(path)) == "真正的问题"


def test_scan_groups_by_real_cwd(tmp_path):
    projects = tmp_path / "projects"
    real = tmp_path / "real-project"
    real.mkdir()
    make_session(projects, "-D-real-project", "aaa", str(real), "第一个问题")

    store = SessionStore(projects_dir=projects)
    groups = store.get()

    assert len(groups) == 1
    project_path, sessions = groups[0]
    assert project_path == str(real)
    assert sessions[0]["id"] == "aaa"
    assert sessions[0]["prompt"] == "第一个问题"


def test_sessions_with_missing_cwd_are_skipped(tmp_path):
    projects = tmp_path / "projects"
    make_session(projects, "-D-gone", "bbb", str(tmp_path / "does-not-exist"), "问题")

    store = SessionStore(projects_dir=projects)
    assert store.get() == []


def test_sessions_sorted_newest_first(tmp_path):
    projects = tmp_path / "projects"
    real = tmp_path / "proj"
    real.mkdir()
    make_session(projects, "-D-proj", "old", str(real), "旧", mtime=1000.0)
    make_session(projects, "-D-proj", "new", str(real), "新", mtime=5000.0)

    store = SessionStore(projects_dir=projects)
    _, sessions = store.get()[0]
    assert sessions[0]["id"] == "new"


def test_per_project_session_cap(tmp_path):
    projects = tmp_path / "projects"
    real = tmp_path / "proj"
    real.mkdir()
    for i in range(MAX_SESSIONS_PER_PROJECT + 5):
        make_session(projects, "-D-proj", "s%02d" % i, str(real), "p%d" % i, mtime=1000.0 + i)

    store = SessionStore(projects_dir=projects)
    _, sessions = store.get()[0]
    assert len(sessions) == MAX_SESSIONS_PER_PROJECT


def test_project_cap(tmp_path):
    projects = tmp_path / "projects"
    for i in range(MAX_PROJECTS + 5):
        real = tmp_path / ("proj%02d" % i)
        real.mkdir()
        make_session(projects, "-D-proj%02d" % i, "s%d" % i, str(real), "p", mtime=1000.0 + i)

    store = SessionStore(projects_dir=projects)
    assert len(store.get()) == MAX_PROJECTS


def test_cache_avoids_rescanning(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    real = tmp_path / "proj"
    real.mkdir()
    make_session(projects, "-D-proj", "aaa", str(real), "问题")

    store = SessionStore(projects_dir=projects)
    store.get()

    calls = []
    real_listdir = os.listdir

    def counting_listdir(path):
        calls.append(path)
        return real_listdir(path)

    monkeypatch.setattr(os, "listdir", counting_listdir)
    store.get()
    assert calls == []


def test_force_refresh_rescans(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    real = tmp_path / "proj"
    real.mkdir()
    make_session(projects, "-D-proj", "aaa", str(real), "问题")

    store = SessionStore(projects_dir=projects)
    store.get()

    calls = []
    real_listdir = os.listdir

    def counting_listdir(path):
        calls.append(path)
        return real_listdir(path)

    monkeypatch.setattr(os, "listdir", counting_listdir)
    store.get(force_refresh=True)
    assert calls


def test_missing_projects_dir_returns_empty(tmp_path):
    store = SessionStore(projects_dir=tmp_path / "absent")
    assert store.get() == []


def test_remove_deletes_file_and_drops_from_cache(tmp_path):
    projects = tmp_path / "projects"
    real = tmp_path / "proj"
    real.mkdir()
    path = make_session(projects, "-D-proj", "aaa", str(real), "问题")

    store = SessionStore(projects_dir=projects)
    store.get()
    assert store.remove(str(path)) is True
    assert not path.exists()
    assert store.get() == []
