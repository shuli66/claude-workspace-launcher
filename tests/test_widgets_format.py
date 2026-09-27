from claude_launcher.ui.widgets import elide_path, format_size, format_time


def test_format_size_bytes():
    assert format_size(512) == "512B"


def test_format_size_kilobytes():
    assert format_size(2048) == "2KB"


def test_format_size_megabytes():
    assert format_size(3 * 1024 * 1024) == "3.0MB"


def test_format_size_zero():
    assert format_size(0) == "0B"


def test_elide_short_path_unchanged():
    assert elide_path("D:\\proj", 35) == "D:\\proj"


def test_elide_long_path_keeps_tail():
    long_path = "D:\\" + "\\".join(["verylongsegment%d" % i for i in range(10)])
    result = elide_path(long_path, 35)
    assert len(result) == 35
    assert result.startswith("...")
    assert long_path.endswith(result[3:])


def test_elide_exact_limit_unchanged():
    path = "x" * 35
    assert elide_path(path, 35) == path
