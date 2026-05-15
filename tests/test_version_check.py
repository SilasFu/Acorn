from __future__ import annotations

import json
import time
from unittest.mock import patch

from acorn.commands.doctor import VERSION_CHECK_FILE, _check_version


def test_check_version_skips_if_recent():
    VERSION_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
    VERSION_CHECK_FILE.write_text(json.dumps({"checked": time.time()}))
    with patch("acorn.check_update.check_pypi_version") as mock_check:
        _check_version()
    mock_check.assert_not_called()


def test_check_version_checks_if_old():
    VERSION_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
    VERSION_CHECK_FILE.write_text(json.dumps({"checked": 0}))
    with patch("acorn.check_update.check_pypi_version", return_value=None):
        _check_version()


def test_check_version_no_cache():
    if VERSION_CHECK_FILE.exists():
        VERSION_CHECK_FILE.unlink()
    with patch("acorn.check_update.check_pypi_version", return_value=None):
        _check_version()


def test_check_version_shows_update(capsys):
    if VERSION_CHECK_FILE.exists():
        VERSION_CHECK_FILE.unlink()
    result = {"upgrade_available": True, "latest": "99.99.99", "url": "https://pypi.org/project/acorn/"}
    with patch("acorn.check_update.check_pypi_version", return_value=result):
        _check_version()
    captured = capsys.readouterr()
    assert "99.99.99" in captured.out
