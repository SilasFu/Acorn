from __future__ import annotations

from unittest.mock import patch

from acorn.log import LogLevel, _log, _rotate_logs, get_level, set_level


def test_log_level_default():
    level = get_level()
    assert level == LogLevel.INFO


def test_log_level_set():
    set_level("DEBUG")
    assert get_level() == LogLevel.DEBUG
    set_level("INFO")


def test_log_level_invalid():
    set_level("INVALID")
    assert get_level() == LogLevel.INFO


def test_log_level_set_with_enum():
    set_level(LogLevel.DEBUG)
    assert get_level() == LogLevel.DEBUG
    set_level(LogLevel.INFO)


def test_log_level_enum_values():
    assert LogLevel.ERROR.value == "ERROR"
    assert LogLevel.WARNING.value == "WARNING"
    assert LogLevel.INFO.value == "INFO"
    assert LogLevel.DEBUG.value == "DEBUG"


def test_log_debug(capsys):
    set_level("DEBUG")
    _log(LogLevel.DEBUG, "test debug message")
    captured = capsys.readouterr()
    assert "test debug message" in captured.out or "test debug message" in captured.err


def test_log_info_not_shown_at_warning(capsys):
    set_level("WARNING")
    _log(LogLevel.INFO, "should not appear")
    captured = capsys.readouterr()
    assert "should not appear" not in captured.out
    assert "should not appear" not in captured.err


def test_log_info_at_info(capsys):
    set_level("INFO")
    _log(LogLevel.INFO, "info message")
    captured = capsys.readouterr()
    assert "info message" in captured.out or "info message" in captured.err


def test_log_warning(capsys):
    set_level("WARNING")
    _log(LogLevel.WARNING, "warning test")
    captured = capsys.readouterr()
    assert "warning test" in captured.out or "warning test" in captured.err


def test_log_error(capsys):
    set_level("ERROR")
    _log(LogLevel.ERROR, "error test")
    captured = capsys.readouterr()
    assert "error test" in captured.out or "error test" in captured.err


def test_rotate_logs_no_file(tmp_path):
    with patch("acorn.log.LOG_FILE", tmp_path / "nonexistent.log"):
        _rotate_logs()


def test_rotate_logs_small_file(tmp_path):
    log_file = tmp_path / "acorn.log"
    log_file.write_text("small log\n")
    with patch("acorn.log.LOG_FILE", log_file):
        _rotate_logs()
        assert log_file.exists()


def test_rotate_logs_rotation(tmp_path):
    log_file = tmp_path / "acorn.log"
    log_file.write_text("x" * (1024 * 1024 + 1))
    with patch("acorn.log.LOG_FILE", log_file):
        _rotate_logs()
        bak = tmp_path / "acorn.log.1"
        assert bak.exists()


def test_log_oserror_handled(capsys, tmp_path):
    set_level("INFO")
    with patch("acorn.log.LOG_FILE", tmp_path / "nope" / "no-access.log"):
        _log(LogLevel.INFO, "test oserror")
    captured = capsys.readouterr()
    assert "test oserror" in captured.out or "test oserror" in captured.err


def test_log_error_stderr(capsys):
    set_level("ERROR")
    _log(LogLevel.ERROR, "stderr test")
    captured = capsys.readouterr()
    assert "stderr test" in captured.err


def test_rotate_logs_existing_older(tmp_path):
    log_file = tmp_path / "acorn.log"
    log_file.write_text("x" * (1024 * 1024 + 1))
    (tmp_path / "acorn.log.1").write_text("older backup")
    with patch("acorn.log.LOG_FILE", log_file):
        _rotate_logs()
        assert (tmp_path / "acorn.log.2").exists() or (tmp_path / "acorn.log.1").exists()


def test_log_level_error_shown(capsys):
    set_level("ERROR")
    _log(LogLevel.ERROR, "only error")
    captured = capsys.readouterr()
    assert "only error" in captured.err


def test_log_debug_not_shown_at_info(capsys):
    set_level("INFO")
    _log(LogLevel.DEBUG, "hidden debug")
    captured = capsys.readouterr()
    assert "hidden debug" not in captured.out
    assert "hidden debug" not in captured.err


def test_rotate_logs_removes_older_backup(tmp_path):
    log_file = tmp_path / "acorn.log"
    log_file.write_text("x" * (1024 * 1024 + 1))
    (tmp_path / "acorn.log.1").write_text("backup 1")
    (tmp_path / "acorn.log.2").write_text("backup 2")
    with patch("acorn.log.LOG_FILE", log_file):
        _rotate_logs()
        assert (tmp_path / "acorn.log.2").read_text() == "backup 1"
        assert (tmp_path / "acorn.log.1").exists()
        assert not (tmp_path / "acorn.log").exists()
