from __future__ import annotations

import json
import os
import platform
import uuid
from typing import Any

from acorn.config import GLOBAL_DIR, load_config, save_config
from acorn.log import info as log_info

TELEMETRY_ENDPOINT = os.environ.get("ACORN_TELEMETRY_ENDPOINT", "https://telemetry.opencode.ai/v1/event")
_INSTANCE_ID_FILE = GLOBAL_DIR / "instance-id"


def _get_instance_id() -> str:
    _INSTANCE_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _INSTANCE_ID_FILE.exists():
        return _INSTANCE_ID_FILE.read_text().strip()
    iid = str(uuid.uuid4())
    _INSTANCE_ID_FILE.write_text(iid)
    return iid


def is_enabled() -> bool:
    return load_config().get("telemetry_enabled", False)


def set_enabled(enabled: bool) -> None:
    config = load_config()
    config["telemetry_enabled"] = enabled
    save_config(config)
    status = "enabled" if enabled else "disabled"
    log_info(f"Telemetry {status}")


def _collect_event(event: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "event": event,
        "instance_id": _get_instance_id(),
        "properties": {
            "acorn_version": _get_version(),
            "os": platform.system().lower(),
            "arch": platform.machine(),
            "python_version": platform.python_version(),
            **(properties or {}),
        },
    }


def _get_version() -> str:
    try:
        from acorn import __version__
        return __version__
    except ImportError:
        return "unknown"


def _send(event_data: dict[str, Any]) -> None:
    try:
        import urllib.request as req
        payload = json.dumps(event_data).encode()
        r = req.Request(
            TELEMETRY_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        req.urlopen(r, timeout=5)
    except Exception:
        pass


def track(event: str, **properties: Any) -> None:
    if not is_enabled():
        return
    data = _collect_event(event, properties)
    _send(data)


def maybe_prompt() -> None:
    if "ACORN_TELEMETRY_PROMPTED" in os.environ:
        return
    config = load_config()
    if "telemetry_enabled" in config:
        return
    try:
        answer = input("\nHelp improve Acorn? Share anonymous usage data (y/N): ").strip().lower()
        set_enabled(answer in ("y", "yes"))
    except (EOFError, KeyboardInterrupt):
        set_enabled(False)
    os.environ["ACORN_TELEMETRY_PROMPTED"] = "1"
