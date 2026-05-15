from __future__ import annotations

import sys
from pathlib import Path

from acorn.analysis.detector import detect_project_type
from acorn.analysis.insights import analyze, has_source_code
from acorn.format import EXIT_ERROR, EXIT_SUCCESS, color, confirm_or_exit
from acorn.generators.builtin import AI_FILES, GENERATORS, generate_file_content
from acorn.log import debug as log_debug, error as log_error, info as log_info

SYNC_TARGETS = {
    "cursorrules": ".cursorrules",
    "claude-md": "CLAUDE.md",
    "copilot": ".github/copilot-instructions.md",
}

HOOK_TEMPLATE = """#!/bin/sh
# Acorn sync hook — keep AI context files up to date
exec acorn sync
"""


def _detect_drift(cwd: Path, detection, insights) -> list[dict]:
    drifted: list[dict] = []
    project_type = detection.project_type.value if detection else "unknown"

    for target_name, dest_name in SYNC_TARGETS.items():
        dest = cwd / dest_name
        if not dest.exists():
            continue

        current = dest.read_text(encoding="utf-8", errors="ignore")
        expected = generate_file_content(dest_name, project_type, detection=detection, insights=insights)

        if current.strip() != expected.strip():
            drifted.append({
                "target": target_name,
                "dest": dest_name,
                "dest_path": dest,
                "expected": expected,
            })

    return drifted


def _print_drift(drifted: list[dict]) -> None:
    for item in drifted:
        dest = item["dest"]
        print(f"  {color('⚠', 'yellow')} {dest} — stale, needs update")


def _regenerate(drifted: list[dict], force: bool = False, dry_run: bool = False) -> int:
    updated = 0
    for item in drifted:
        dest = item["dest_path"]
        expected = item["expected"]
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dry_run:
            print(f"  {color('Would update:', 'dim')} {item['dest']}")
            updated += 1
            continue

        dest.write_text(expected)
        print(f"  {color('✓', 'green')} Updated {item['dest']}")
        updated += 1

    return updated


def cmd_sync(
    cwd: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
    hook_install: bool = False,
) -> int:
    if cwd is None:
        cwd = Path.cwd()

    if hook_install:
        return _install_hook(cwd, dry_run=dry_run)

    if not has_source_code(cwd):
        log_error("No source code found in current directory")
        return EXIT_ERROR

    detection = detect_project_type(cwd)
    insights = analyze(cwd)
    project_type = detection.project_type.value if detection else "unknown"

    print(f"{color('⟳', 'blue')} Checking AI context freshness...")
    print(f"  Project: {cwd.name} ({project_type})")
    print()

    drifted = _detect_drift(cwd, detection, insights)

    if not drifted:
        print(f"  {color('✓', 'green')} All AI context files are up to date.")
        return EXIT_SUCCESS

    _print_drift(drifted)
    print()

    if not force:
        count = len(drifted)
        msg = f"Update {count} stale file(s)? "
        if not confirm_or_exit(msg):
            print("Cancelled.")
            return EXIT_ERROR

    updated = _regenerate(drifted, force=force, dry_run=dry_run)
    if not dry_run:
        log_info(f"Updated {updated}/{len(drifted)} file(s)")
    else:
        print(f"  Would update {updated}/{len(drifted)} file(s)")

    return EXIT_SUCCESS


def _install_hook(cwd: Path, dry_run: bool = False) -> int:
    git_hooks = cwd / ".git" / "hooks"
    hook_path = git_hooks / "pre-commit"

    if not git_hooks.exists():
        log_error("Not a git repository (no .git/hooks directory)")
        return EXIT_ERROR

    if hook_path.exists() and not dry_run:
        msg = f"Overwrite existing {hook_path}?"
        if not confirm_or_exit(msg):
            print("Cancelled.")
            return EXIT_ERROR

    if dry_run:
        print(f"  {color('Would install:', 'dim')} {hook_path}")
        return EXIT_SUCCESS

    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(HOOK_TEMPLATE)
    hook_path.chmod(0o755)
    print(f"  {color('✓', 'green')} Installed pre-commit hook: {hook_path}")
    return EXIT_SUCCESS
