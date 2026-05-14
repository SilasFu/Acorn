from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

from acorn.check_update import PYPI_API, check_pypi_version


@patch("acorn.check_update.urllib.request.urlopen")
def test_check_update_upgrade_available(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "info": {"version": "99.99.99"}
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    result = check_pypi_version(offline=False)
    assert result is not None
    assert result["upgrade_available"] is True
    assert result["latest"] == "99.99.99"
    assert "pypi.org" in result["url"]


@patch("acorn.check_update.urllib.request.urlopen")
def test_check_update_current(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "info": {"version": "0.1.0"}
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    result = check_pypi_version(offline=False)
    assert result is not None
    assert result["upgrade_available"] is False
    assert result["latest"] == "0.1.0"


@patch("acorn.check_update.urllib.request.urlopen")
def test_check_update_network_error(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

    result = check_pypi_version(offline=False)
    assert result is None


@patch("acorn.check_update.urllib.request.urlopen")
def test_check_update_http_error(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.HTTPError(
        PYPI_API, 404, "Not Found", {}, None
    )

    result = check_pypi_version(offline=False)
    assert result is None


@patch("acorn.check_update.urllib.request.urlopen")
def test_check_update_bad_json(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"not json"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    result = check_pypi_version(offline=False)
    assert result is None


def test_check_update_offline():
    result = check_pypi_version(offline=True)
    assert result is None


@patch("acorn.check_update.urllib.request.urlopen")
def test_check_update_missing_version(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "info": {}
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    result = check_pypi_version(offline=False)
    assert result is None
