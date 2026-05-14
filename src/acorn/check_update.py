from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from acorn import __version__

PYPI_API = "https://pypi.org/pypi/acorn/json"
TIMEOUT = 5


def check_pypi_version(offline: bool = False) -> dict[str, Any] | None:
    if offline:
        return None

    req = urllib.request.Request(PYPI_API, headers={"User-Agent": "acorn", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):
        return None

    latest = data.get("info", {}).get("version", "")
    if not latest:
        return None

    return {
        "current": __version__,
        "latest": latest,
        "upgrade_available": latest != __version__,
        "url": "https://pypi.org/project/acorn/",
    }
