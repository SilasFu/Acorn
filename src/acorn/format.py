from __future__ import annotations

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_NO_MATCH = 2

COLORS = {
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}


def color(text: str, code: str) -> str:
    c = COLORS.get(code, "")
    return f"{c}{text}{COLORS['reset']}"


def suggest_help() -> str:
    return color(" (use --help for usage)", "dim")


def confirm_or_exit(prompt_text: str, default_yes: bool = True) -> bool:
    default = "Y/n" if default_yes else "y/N"
    try:
        choice = input(f"{color('?', 'blue')} {prompt_text} [{default}]: ").strip().lower()
        if default_yes:
            return choice not in ("n", "no")
        return choice in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
