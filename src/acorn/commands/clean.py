from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from acorn.config import load_manifest, load_project_lock, remove_from_manifest
from acorn.format import EXIT_ERROR, EXIT_SUCCESS
from acorn.log import error as log_error
from acorn.log import info as log_info


def cmd_clean(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        log_error(f"Directory '{args.dir}' does not exist")
        return EXIT_ERROR

    clean_all = args.all
    keep_templates = args.keep_templates

    if clean_all:
        acorn_dir = target_dir / ".acorn"
        if acorn_dir.exists():
            if args.dry_run:
                print(f"  🔍 Would remove: {acorn_dir}/")
            else:
                shutil.rmtree(acorn_dir)
                print(f"  ✓ Removed: {acorn_dir}/")
        if not keep_templates:
            manifest = load_manifest()
            key = str(target_dir.resolve())
            if key in manifest:
                if not args.dry_run:
                    remove_from_manifest(target_dir)
                    print("  ✓ Removed from manifest")
        log_info("Clean all complete")
        return EXIT_SUCCESS

    lock = load_project_lock(target_dir)
    if not lock or "files" not in lock:
        log_info("No lock file found — nothing to clean")
        return EXIT_ERROR

    files = lock.get("files", [])
    if not files:
        log_info("No generated files recorded in lock")
        return EXIT_ERROR

    removed = 0
    for rel_path in files:
        f = target_dir / rel_path
        if f.exists():
            if args.dry_run:
                print(f"  🔍 Would remove: {rel_path}")
            else:
                f.unlink()
                print(f"  ✓ Removed: {rel_path}")
            removed += 1

    if removed == 0 and not args.dry_run:
        log_info("No files to clean")
    else:
        log_info(f"Cleaned {removed} generated file(s)")
    return EXIT_SUCCESS
