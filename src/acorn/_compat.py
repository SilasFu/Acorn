from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "acorn"
    else:
        base = Path(__file__).resolve().parent
    return base / relative


# ── tomllib compatibility (Python 3.10) ──
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

__all__ = ["resource_path", "tomllib"]
