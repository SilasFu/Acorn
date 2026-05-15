from __future__ import annotations

import json
import sys
from typing import Any


def print_json(data: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
