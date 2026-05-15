from __future__ import annotations

import os
import re
from typing import Any

import yaml

from acorn._compat import resource_path

LOCALES_DIR = resource_path("locales")

_current_lang: str = "en"
_translations: dict[str, Any] = {}
VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def detect_language(args_lang: str | None = None) -> str:
    if args_lang:
        return args_lang

    env_lang = os.environ.get("INIT_PROJECT_LANG", "")
    if env_lang:
        return env_lang

    sys_lang = os.environ.get("LANG", "en_US")
    if sys_lang.startswith("zh"):
        return "zh"

    return "en"


def load_translations(lang: str) -> dict[str, Any]:
    lang_file = LOCALES_DIR / f"{lang}.yaml"
    if not lang_file.exists():
        lang_file = LOCALES_DIR / "en.yaml"
    if lang_file.exists():
        raw = lang_file.read_text()
        return yaml.safe_load(raw) or {}
    return {}


def set_language(lang: str) -> None:
    global _current_lang, _translations
    _current_lang = lang
    _translations = load_translations(lang)


def get_language() -> str:
    return _current_lang


def _lookup(key: str, data: dict[str, Any] | None = None) -> str | None:
    lookup = data or _translations
    parts = key.split(".")
    current: Any = lookup
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
            if current is None:
                return None
        else:
            return None
    if isinstance(current, str):
        return current
    return None


def t(key: str, **kwargs: str) -> str:
    template = _lookup(key)
    if template is None:
        return key

    def _replace(m: re.Match) -> str:
        return kwargs.get(m.group(1), m.group(0))

    return VARIABLE_PATTERN.sub(_replace, template)


def text(key: str, **kwargs: str) -> str:
    return t(f"messages.{key}", **kwargs)


def error(key: str, **kwargs: str) -> str:
    return t(f"errors.{key}", **kwargs)


def prompt(key: str, **kwargs: str) -> str:
    return t(f"prompts.{key}", **kwargs)


def cmd_text(key: str, **kwargs: str) -> str:
    return t(f"commands.{key}", **kwargs)
