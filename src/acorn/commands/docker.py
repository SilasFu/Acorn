from __future__ import annotations

import argparse
from pathlib import Path

from acorn.analysis.insights import analyze
from acorn.detector import detect_project_type
from acorn.format import EXIT_ERROR, EXIT_SUCCESS, color
from acorn.generators.builtin import DOCKER_FILES, generate_file_content
from acorn.log import error as log_error, info as log_info
from acorn.models import ProjectType

CI_WORKFLOWS_DIR = ".github/workflows"


def cmd_dockerize(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        log_error(f"Directory '{args.dir}' does not exist")
        return EXIT_ERROR

    detection = detect_project_type(target_dir)
    if detection.project_type == ProjectType.UNKNOWN:
        log_error("Cannot detect project type in target directory")
        return EXIT_ERROR

    project_type = detection.project_type.value
    insights = analyze(target_dir)
    force = getattr(args, "force", False)
    dry_run = getattr(args, "dry_run", False)

    log_info(f"Generating Docker configuration for {project_type} project...")

    generated = 0
    for file_type in sorted(DOCKER_FILES):
        dest = target_dir / file_type
        if dest.exists() and not force:
            log_info(f"Skipping {file_type} (already exists)")
            continue

        content = generate_file_content(file_type, project_type, detection=detection, insights=insights)

        if dry_run:
            print(f"  {color('Would generate:', 'dim')} {file_type}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
            print(f"  {color('✓', 'green')} Generated: {file_type}")
        generated += 1

    if generated == 0:
        log_info("No Docker files generated (they may already exist)")
        return EXIT_ERROR
    log_info(f"Generated {generated} Docker file(s)")
    return EXIT_SUCCESS


def _ci_setup_action(project_type: str) -> str:
    setups = {
        "node": "actions/setup-node@v4\n      with:\n        node-version: '20'",
        "python": "actions/setup-python@v5\n      with:\n        python-version: '3.12'",
        "go": "actions/setup-go@v5\n      with:\n        go-version: '1.22'",
        "rust": "actions/setup-rust@v1\n      with:\n        toolchain: stable",
        "java": "actions/setup-java@v4\n      with:\n        java-version: '21'\n        distribution: temurin",
        "php": "actions/setup-php@v5\n      with:\n        php-version: '8.3'",
    }
    return setups.get(project_type, "actions/setup-node@v4\n      with:\n        node-version: '20'")


def _ci_run_command(project_type: str) -> str:
    commands = {
        "node": "npm ci\n    - run: npm test",
        "python": "pip install -r requirements.txt\n    - run: pytest",
        "go": "go mod download\n    - run: go test ./...",
        "rust": "cargo build\n    - run: cargo test",
        "java": "./mvnw verify",
        "php": "composer install\n    - run: phpunit",
    }
    return commands.get(project_type, "echo 'Run tests'")


def _generate_ci_yml(project_type: str) -> str:
    setup = _ci_setup_action(project_type)
    run = _ci_run_command(project_type)
    return f"""name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Setup
      uses: {setup}
    - name: Install dependencies
      run: {run.split(chr(10))[0]}
    - name: Test
      run: {run.split(chr(10))[-1].replace('- run: ', '') if chr(10) in run else run}
"""


def cmd_add_ci(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        log_error(f"Directory '{args.dir}' does not exist")
        return EXIT_ERROR

    result = detect_project_type(target_dir)
    if result.project_type == ProjectType.UNKNOWN:
        log_error("Cannot detect project type")
        return EXIT_ERROR

    project_type = result.project_type.value
    workflows_dir = target_dir / CI_WORKFLOWS_DIR
    workflows_dir.mkdir(parents=True, exist_ok=True)

    files_to_generate = ["ci.yml"]
    generated = []

    for fname in files_to_generate:
        dest = workflows_dir / fname
        if dest.exists() and not args.force:
            log_info(f"Skipping {CI_WORKFLOWS_DIR}/{fname} (already exists)")
            continue

        content = _generate_ci_yml(project_type)

        if args.dry_run:
            print(f"  🔍 Would generate: {CI_WORKFLOWS_DIR}/{fname}")
            continue

        dest.write_text(content)
        print(f"  ✓ Generated: {CI_WORKFLOWS_DIR}/{fname}")
        generated.append(dest)

    if not generated:
        log_info("No CI files generated")
        return EXIT_ERROR
    log_info(f"Generated {len(generated)} CI workflow file(s)")
    return EXIT_SUCCESS
