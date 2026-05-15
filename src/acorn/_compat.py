from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "acorn"
    else:
        base = Path(__file__).resolve().parent
    return base / relative
