from __future__ import annotations

import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

LOG_DIR = Path.home() / ".local" / "share" / "acorn" / "logs"
LOG_FILE = LOG_DIR / "acorn.log"
MAX_LOG_SIZE = 1024 * 1024
MAX_LOG_FILES = 3


class LogLevel(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


_current_level = LogLevel.INFO


def set_level(level: str | LogLevel) -> None:
    global _current_level
    if isinstance(level, str):
        try:
            _current_level = LogLevel(level.upper())
        except ValueError:
            _current_level = LogLevel.INFO
    else:
        _current_level = level


def get_level() -> LogLevel:
    return _current_level


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _rotate_logs() -> None:
    if not LOG_FILE.exists():
        return
    size = LOG_FILE.stat().st_size
    if size < MAX_LOG_SIZE:
        return

    for i in range(MAX_LOG_FILES - 1, 0, -1):
        older = LOG_FILE.with_suffix(f".log.{i}")
        newer = LOG_FILE.with_suffix(f".log.{i - 1}")
        if older.exists():
            older.unlink()
        if newer.exists():
            newer.rename(older)

    LOG_FILE.rename(LOG_FILE.with_suffix(".log.1"))


def _log(level: LogLevel, message: str, **kwargs: Any) -> None:
    levels_order = [LogLevel.ERROR, LogLevel.WARNING, LogLevel.INFO, LogLevel.DEBUG]
    if levels_order.index(level) > levels_order.index(_current_level):
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] [{level.value}] {message}"

    if level == LogLevel.ERROR:
        print(f"\033[31m{formatted}\033[0m", file=sys.stderr)
    elif level == LogLevel.WARNING:
        print(f"\033[33m{formatted}\033[0m")
    elif level == LogLevel.DEBUG:
        print(f"\033[2m{formatted}\033[0m")
    else:
        print(formatted)

    try:
        _ensure_log_dir()
        _rotate_logs()
        with open(LOG_FILE, "a") as f:
            f.write(formatted + "\n")
    except OSError:
        pass


def error(message: str, **kwargs: Any) -> None:
    _log(LogLevel.ERROR, message, **kwargs)


def warning(message: str, **kwargs: Any) -> None:
    _log(LogLevel.WARNING, message, **kwargs)


def info(message: str, **kwargs: Any) -> None:
    _log(LogLevel.INFO, message, **kwargs)


def debug(message: str, **kwargs: Any) -> None:
    _log(LogLevel.DEBUG, message, **kwargs)
