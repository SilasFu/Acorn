from __future__ import annotations

import argparse
from pathlib import Path

from acorn.analysis.detector import detect_project_type
from acorn.analysis.insights import analyze
from acorn.detector import detect_project_type as detector_detect
from acorn.format import EXIT_ERROR, EXIT_SUCCESS, color, confirm_or_exit
from acorn.generators.builtin import DOCKER_FILES, generate_file_content
from acorn.i18n import text as i18n_text
from acorn.log import debug as log_debug, error as log_error, info as log_info

GENERATABLE_FILES = {
    "dockerfile": {"file_type": "Dockerfile", "dest_name": "Dockerfile"},
    "dockerignore": {"file_type": ".dockerignore", "dest_name": ".dockerignore"},
    "gitignore": {"file_type": ".gitignore", "dest_name": ".gitignore"},
    "cursorrules": {"file_type": ".cursorrules", "dest_name": ".cursorrules"},
    "claude-md": {"file_type": "CLAUDE.md", "dest_name": "CLAUDE.md"},
    "copilot": {"file_type": ".github/copilot-instructions.md", "dest_name": ".github/copilot-instructions.md"},
}

AI_TARGETS = {"cursorrules", "claude-md", "copilot"}
DOCKER_TARGETS = {"dockerfile", "dockerignore"}


def _write_file(dest: Path, content: str, force: bool = False, dry_run: bool = False) -> bool:
    if dest.exists() and not force:
        log_info(i18n_text("fix_skipped", name=str(dest)))
        return False

    if dry_run:
        print(f"  {color('Would generate:', 'dim')} {dest}")
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)
    print(f"  {color('✓', 'green')} {i18n_text('fix_generated', name=str(dest))}")
    return True


def cmd_fix_individual(target: str, cwd: Path, detection=None, insights=None, force: bool = False, dry_run: bool = False) -> int:
    info = GENERATABLE_FILES.get(target)
    if info is None:
        log_error(f"Unknown fix target: {target}")
        return EXIT_ERROR

    if detection is None:
        detection = detect_project_type(cwd)
    if insights is None:
        insights = analyze(cwd)

    project_type = detection.project_type.value if detection else "unknown"
    content = generate_file_content(info["file_type"], project_type, detection=detection, insights=insights)
    dest = cwd / info["dest_name"]

    _write_file(dest, content, force=force, dry_run=dry_run)
    return EXIT_SUCCESS


def fix_all(cwd: Path, detection=None, insights=None, scope: set[str] | None = None, force: bool = False, dry_run: bool = False) -> int:
    if detection is None:
        detection = detect_project_type(cwd)
    if insights is None:
        insights = analyze(cwd)

    targets = scope if scope is not None else set(GENERATABLE_FILES.keys())
    success = 0
    for target in sorted(targets):
        if target in GENERATABLE_FILES:
            rc = cmd_fix_individual(target, cwd, detection, insights, force=force, dry_run=dry_run)
            if rc == EXIT_SUCCESS:
                success += 1

    if not dry_run:
        log_info(f"Fixed {success}/{len(targets)} items")
    return EXIT_SUCCESS if success > 0 else EXIT_ERROR


def cmd_fix(args: argparse.Namespace) -> int:
    cwd = Path(args.dir).resolve() if hasattr(args, "dir") else Path.cwd()

    detection = None
    insights = None

    targets: set[str] = set()

    if hasattr(args, "fix_dockerfile") and args.fix_dockerfile:
        targets.add("dockerfile")
    if hasattr(args, "fix_dockerignore") and args.fix_dockerignore:
        targets.add("dockerignore")
    if hasattr(args, "fix_gitignore") and args.fix_gitignore:
        targets.add("gitignore")
    if hasattr(args, "fix_cursorrules") and args.fix_cursorrules:
        targets.add("cursorrules")
    if hasattr(args, "fix_claude_md") and args.fix_claude_md:
        targets.add("claude-md")
    if hasattr(args, "fix_copilot") and args.fix_copilot:
        targets.add("copilot")
    if hasattr(args, "fix_ai") and args.fix_ai:
        targets |= AI_TARGETS
    if hasattr(args, "fix_all") and args.fix_all:
        targets |= set(GENERATABLE_FILES.keys())

    force = getattr(args, "force", False)
    dry_run = getattr(args, "dry_run", False)

    if not targets:
        log_error("No fix targets specified. Use --dockerfile, --cursorrules, --ai, --all, etc.")
        return EXIT_ERROR

    detection = detect_project_type(cwd)
    insights = analyze(cwd)

    return fix_all(cwd, detection=detection, insights=insights, scope=targets, force=force, dry_run=dry_run)
