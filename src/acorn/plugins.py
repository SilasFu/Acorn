from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

PLUGINS_DIR = Path.home() / ".config" / "acorn" / "plugins"
COMMANDS_DIR = Path.home() / ".config" / "acorn" / "commands"


def ensure_plugin_dirs() -> None:
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)


def load_plugin(path: Path) -> ModuleType | None:
    if not path.exists():
        return None

    module_name = f"acorn_plugin_{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
    except Exception:
        return None
    return None


def load_all_plugins() -> list[ModuleType]:
    ensure_plugin_dirs()
    plugins: list[ModuleType] = []
    for f in sorted(PLUGINS_DIR.glob("*.py")):
        module = load_plugin(f)
        if module:
            plugins.append(module)
    return plugins


def run_hook(hook_name: str, **context: Any) -> Any:
    result = context.get("context")
    for plugin in load_all_plugins():
        hook_fn = getattr(plugin, hook_name, None)
        if hook_fn:
            try:
                if result is not None:
                    result = hook_fn(result)
                else:
                    result = hook_fn(**context)
            except Exception as e:
                print(f"  ⚠ Plugin hook '{hook_name}' error: {e}")
    return result


def find_custom_command(name: str) -> Path | None:
    ensure_plugin_dirs()
    for ext in (".py", "", ".sh"):
        cmd = COMMANDS_DIR / f"{name}{ext}"
        if cmd.exists():
            return cmd
    return None


def list_custom_commands() -> list[str]:
    ensure_plugin_dirs()
    commands: list[str] = []
    for f in COMMANDS_DIR.iterdir():
        if f.is_file() and not f.name.startswith("_"):
            commands.append(f.stem)
    return sorted(set(commands))
