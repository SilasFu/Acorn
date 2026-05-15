from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from shutil import copytree, ignore_patterns

import yaml

from acorn.config import (
    TEMPLATES_DIR,
    ensure_dirs,
    init_project_config,
    load_templates,
)
from acorn.format import color, EXIT_SUCCESS, EXIT_ERROR
from acorn.i18n import cmd_text
from acorn.log import error as log_error, info as log_info
from acorn.models import ProjectType
from acorn.template_engine import list_templates


def cmd_list(json_mode: bool = False) -> int:
    templates = list_templates()
    if not templates:
        log_info("No templates found.")
        return EXIT_SUCCESS

    if json_mode:
        from acorn.json_output import print_json
        print_json({"templates": templates, "count": len(templates)})
        return EXIT_SUCCESS

    title = cmd_text("list_title", count=str(len(templates)))
    print(f"\n{color(title, 'bold')}")
    print("-" * 60)
    for t in templates:
        name = color(t["name"], "cyan")
        print(f"  {name:<20} {t['description']:<30} v{t['version']}")
        if t["files"]:
            print(f"  {'':>20} files: {', '.join(t['files'])}")
        print()
    return EXIT_SUCCESS


def cmd_add(path: str) -> int:
    src = Path(path).resolve()
    if not src.is_dir():
        log_error(f"'{path}' is not a valid directory")
        return EXIT_ERROR

    template_yaml = src / "template.yaml"
    if not template_yaml.exists():
        log_error(f"No template.yaml found at {path}")
        return EXIT_ERROR

    dest = TEMPLATES_DIR / src.name
    if dest.exists():
        log_error(f"Template '{src.name}' already exists")
        return EXIT_ERROR

    ensure_dirs()
    copytree(src, dest, ignore=ignore_patterns("__pycache__", ".git"))
    log_info(f"Template '{src.name}' added to {dest}")
    print(f"{color('✓', 'green')} Template '{src.name}' added")
    return EXIT_SUCCESS


def cmd_remove(name: str) -> int:
    dest = TEMPLATES_DIR / name
    if not dest.exists():
        log_error(f"Template '{name}' not found")
        return EXIT_ERROR

    shutil.rmtree(dest)
    log_info(f"Template '{name}' removed")
    print(f"{color('✓', 'green')} Template '{name}' removed")
    return EXIT_SUCCESS


def cmd_init(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        log_error(f"Directory '{args.dir}' does not exist")
        return EXIT_ERROR

    config = init_project_config(target_dir, template_name=args.template, dry_run=args.dry_run)
    return EXIT_SUCCESS if config else EXIT_ERROR


def cmd_validate(path: str) -> int:
    tpl_path = Path(path).resolve()
    if not tpl_path.exists():
        log_error(f"Path not found: {path}")
        return EXIT_ERROR

    errors = []

    if tpl_path.is_dir():
        tpl_file = tpl_path / "template.yaml"
        if not tpl_file.exists():
            log_error(f"No template.yaml found in {path}")
            return EXIT_ERROR
    elif tpl_path.suffix in (".yaml", ".yml"):
        tpl_file = tpl_path
    else:
        log_error(f"Invalid template path: {path}")
        return EXIT_ERROR

    try:
        data = yaml.safe_load(tpl_file.read_text())
    except yaml.YAMLError as e:
        log_error(f"Invalid YAML: {e}")
        return EXIT_ERROR

    if not isinstance(data, dict):
        log_error("Template must be a YAML mapping")
        return EXIT_ERROR

    if "name" not in data:
        errors.append("Missing required field: 'name'")

    ttype = data.get("type", "unknown")
    try:
        ProjectType(ttype)
    except ValueError:
        errors.append(f"Invalid project type: '{ttype}'")

    ai_ctx = data.get("ai_context", {})
    if ai_ctx:
        cursor = ai_ctx.get("cursor_rules", {})
        if not cursor.get("tech_stack"):
            errors.append("ai_context.cursor_rules.tech_stack is recommended")
        if not cursor.get("conventions"):
            errors.append("ai_context.cursor_rules.conventions is recommended")

    provides = data.get("provides", [])
    requires = data.get("requires", [])
    overlap = set(provides) & set(requires)
    if overlap:
        errors.append(f"Capabilities in both provides and requires: {overlap}")

    if errors:
        for e in errors:
            print(f"  ⚠ {e}")
        return EXIT_ERROR

    print(f"  ✓ Template '{data.get('name', '?')}' is valid")
    return EXIT_SUCCESS


def cmd_validate_ai_context() -> int:
    templates = load_templates()
    errors = []
    for tpl in templates:
        if not tpl.ai_context:
            errors.append(f"[{tpl.name}] Missing ai_context")
            continue
        cr = tpl.ai_context.cursor_rules
        if not cr.tech_stack:
            errors.append(f"[{tpl.name}] ai_context.cursor_rules.tech_stack is empty")
        if not cr.conventions:
            errors.append(f"[{tpl.name}] ai_context.cursor_rules.conventions is empty")
    if not errors:
        print(f"All {len(templates)} templates have valid AI context")
        return EXIT_SUCCESS
    for e in errors:
        print(f"  ! {e}")
    return EXIT_ERROR
