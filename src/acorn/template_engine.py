from __future__ import annotations

import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from tempfile import gettempdir
from typing import Any

import yaml

from acorn.config import (
    add_to_manifest,
    find_template_by_name,
    load_templates,
    resolve_template,
    save_project_lock,
    save_template_to_global,
)
from acorn.models import GenerationOptions, Hooks, Template, TemplateVariable
from acorn.progress import Spinner

VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")
IF_PATTERN = re.compile(r"\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}", re.DOTALL)
EACH_PATTERN = re.compile(r"\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}", re.DOTALL)
EACH_ITEM_PATTERN = re.compile(r"\{\{this\.(\w+)\}\}")
VARIABLE_DEFAULT_PATTERN = re.compile(r"\{\{(\w+)\|([^}]+)\}\}")


def get_builtin_variables(target_dir: Path | None = None) -> dict[str, str]:
    now = datetime.now()
    builtins = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "year": str(now.year),
        "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
        "cwd": str(Path.cwd()),
    }
    if target_dir:
        builtins["project_name"] = target_dir.name
    return builtins


def collect_variables(
    template: Template,
    cli_vars: dict[str, str] | None = None,
    interactive: bool = False,
    locked_vars: dict[str, str] | None = None,
    target_dir: Path | None = None,
) -> dict[str, str]:
    builtins = get_builtin_variables(target_dir)
    values: dict[str, str] = dict(builtins)
    values.update(dict(locked_vars) if locked_vars else {})

    for var in template.variables:
        if var.name in values:
            continue

        value = var.default

        if cli_vars and var.name in cli_vars:
            value = cli_vars[var.name]

        if interactive and not (cli_vars and var.name in cli_vars):
            if var.options:
                value = _select_from_options(var)
            else:
                value = _prompt_for_variable(var)

        values[var.name] = value

    return values


def _select_from_options(var: TemplateVariable) -> str:
    print(f"\n  {var.prompt or var.name}:")
    for i, opt in enumerate(var.options, 1):
        default_mark = " [default]" if opt == var.default else ""
        print(f"    [{i}] {opt}{default_mark}")
    try:
        choice = input(f"  Select (1-{len(var.options)}) [{var.default}]: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(var.options):
                return var.options[idx]
    except (EOFError, KeyboardInterrupt):
        pass
    return var.default


def _prompt_for_variable(var: TemplateVariable) -> str:
    prompt_text = var.prompt or f"Enter value for {var.name}"
    default_str = f" [{var.default}]" if var.default else ""
    try:
        user_input = input(f"  {prompt_text}{default_str}: ").strip()
        return user_input if user_input else var.default
    except (EOFError, KeyboardInterrupt):
        return var.default


def render_template(content: str, variables: dict[str, str]) -> str:
    def _replace_default(m: re.Match) -> str:
        key, default_val = m.group(1), m.group(2)
        return variables.get(key, default_val)

    content = VARIABLE_DEFAULT_PATTERN.sub(_replace_default, content)

    content = render_conditionals(content, variables)
    content = render_each(content, variables)

    def _replace(m: re.Match) -> str:
        key = m.group(1)
        return variables.get(key, m.group(0))

    content = VARIABLE_PATTERN.sub(_replace, content)
    return content


def render_conditionals(content: str, variables: dict[str, str]) -> str:
    def _replace_if(m: re.Match) -> str:
        var_name = m.group(1)
        inner = m.group(2)
        val = variables.get(var_name, "")
        truthy = val and val.lower() not in ("false", "0", "no", "")
        return inner if truthy else ""

    return IF_PATTERN.sub(_replace_if, content)


def render_each(content: str, variables: dict[str, str]) -> str:
    def _replace_each(m: re.Match) -> str:
        var_name = m.group(1)
        template_block = m.group(2)
        raw = variables.get(var_name, "")
        items = _parse_list(raw)
        if not items:
            return ""
        parts = []
        for item in items:
            if isinstance(item, dict):
                rendered = EACH_ITEM_PATTERN.sub(
                    lambda m2: str(item.get(m2.group(1), m2.group(0))),
                    template_block,
                )
                parts.append(rendered)
            else:
                parts.append(template_block.replace("{{this}}", str(item)))
        return "".join(parts)

    return EACH_PATTERN.sub(_replace_each, content)


def _parse_list(raw: str) -> list[Any]:
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = yaml.safe_load(raw)
            return parsed
        except Exception:
            pass
    return [item.strip() for item in raw.split(",") if item.strip()]


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(path, bak)
        return bak
    for i in range(1, 100):
        bak = path.with_suffix(f"{path.suffix}.bak{i}")
        if not bak.exists():
            shutil.copy2(path, bak)
            return bak
    return None


def generate_file(
    template_path: Path,
    relative_path: str,
    output_dir: Path,
    variables: dict[str, str],
    options: GenerationOptions,
) -> Path | None:
    src = template_path / relative_path
    if not src.exists():
        return None

    dest = output_dir / relative_path

    if dest.exists():
        if not options.force and not options.regenerate:
            print(f"  ⚠ Skipping {relative_path} (already exists, use --force or --regenerate)")
            return None
        if options.regenerate:
            bak = backup_file(dest)
            if bak:
                print(f"  💾 Backed up {relative_path} -> {bak.name}")

    content = src.read_text(encoding="utf-8")
    rendered = render_template(content, variables)

    if options.dry_run:
        print(f"  🔍 Would generate: {relative_path}")
        return None

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(rendered, encoding="utf-8")
    print(f"  ✓ Generated: {relative_path}")
    return dest


def run_hooks(hooks: Hooks, stage: str, **context: Any) -> None:
    script = getattr(hooks, f"{stage}_generate", None) or getattr(hooks, f"{stage}_detect", None)
    if not script:
        return
    try:
        subprocess.run(script, shell=True, check=True, timeout=30)
    except subprocess.CalledProcessError:
        print(f"  ⚠ Hook '{stage}' failed (non-zero exit)")
    except FileNotFoundError:  # pragma: no cover (shell=True makes this unreachable)
        print(f"  ⚠ Hook '{stage}' command not found")


def _generate_cursorrules(
    output_dir: Path,
    template: Template,
    variables: dict[str, str],
) -> Path | None:
    if not template.ai_context:
        return None
    rules = template.ai_context.cursor_rules
    if not rules.tech_stack and not rules.conventions:
        return None

    lines = ["You are an expert in the following technology stack.", ""]
    if rules.tech_stack:
        rendered_stack = render_template(rules.tech_stack, variables)
        lines.append(f"Tech Stack: {rendered_stack}")
        lines.append("")
    if rules.conventions:
        lines.append("Key Conventions:")
        for convention in rules.conventions:
            rendered = render_template(convention, variables)
            lines.append(f"- {rendered}")
        lines.append("")

    content = "\n".join(lines)
    dest = output_dir / ".cursorrules"

    if dest.exists():
        print("  ⚠ Skipping .cursorrules (already exists)")
        return None

    dest.write_text(content, encoding="utf-8")
    print("  ✓ Generated: .cursorrules")
    return dest


DOCKER_FILES = {"Dockerfile", "docker-compose.yml", ".dockerignore"}


def generate_from_template(
    template_name: str,
    output_dir: Path | str,
    options: GenerationOptions,
    only: set[str] | None = None,
    template: Template | None = None,
) -> list[Path]:
    if isinstance(output_dir, str):
        output_dir = Path(output_dir).resolve()

    if template is None:
        template = find_template_by_name(template_name)
        if not template:
            print(f"✗ Template '{template_name}' not found")
            return []
        resolved = resolve_template(template)
    else:
        resolved = template

    if not resolved.path:
        print(f"✗ Template '{template_name}' has no path")
        return []

    print(f"Using template: {resolved.name} ({resolved.description})")
    if resolved.min_tool_version:
        from acorn import __version__
        if __version__ < resolved.min_tool_version:
            print(f"  ⚠ Template requires acorn >= {resolved.min_tool_version} (current: {__version__})")

    locked_vars = {}
    variables = collect_variables(
        resolved, options.variables, options.interactive, locked_vars,
        target_dir=output_dir,
    )

    run_hooks(resolved.hooks, "before", variables=variables)

    spinner = Spinner(f"Generating from template '{resolved.name}'...")
    if not options.verbose and not options.debug:
        spinner.start()
    generated: list[Path] = []
    for rel_path in resolved.files:
        if only and rel_path not in only:
            continue
        result = generate_file(resolved.path, rel_path, output_dir, variables, options)
        if result:
            generated.append(result)

    files_dir = resolved.path / "files"
    if files_dir.exists():
        for item in files_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(files_dir)
                if only and rel.name not in only:
                    continue
                rendered_content = item.read_text(encoding="utf-8")
                rendered_content = render_template(rendered_content, variables)
                dest = output_dir / rel
                _write_generated_file(rel, dest, rendered_content, options, generated)

    run_hooks(resolved.hooks, "after", variables=variables)

    if resolved.ai_context and not options.dry_run:
        cursor_path = _generate_cursorrules(output_dir, resolved, variables)
        if cursor_path:
            generated.append(cursor_path)

    if not options.verbose and not options.debug:
        spinner.stop()
    summary = "Dry run" if options.dry_run else "Generated"
    rel_files = [str(g.relative_to(output_dir)) for g in generated]
    print(f"\n{summary} {len(generated)} file(s)")

    if not options.dry_run and generated:
        rel_files = [str(g.relative_to(output_dir)) for g in generated]
        lock_data = {
            "template": resolved.name,
            "version": resolved.version,
            "variables": variables,
            "files": rel_files,
        }
        save_project_lock(output_dir, lock_data)
        add_to_manifest(output_dir, rel_files, resolved.name)

    return generated


def _write_generated_file(
    rel: Path | str,
    dest: Path,
    content: str,
    options: GenerationOptions,
    generated: list[Path],
) -> None:
    if dest.exists():
        if not options.force and not options.regenerate:
            print(f"  ⚠ Skipping {rel} (already exists)")
            return
        if options.regenerate:
            bak = backup_file(dest)
            if bak:
                print(f"  💾 Backed up {rel} -> {bak.name}")

    if options.dry_run:
        print(f"  🔍 Would generate: {rel}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"  ✓ Generated: {rel}")
    generated.append(dest)


def save_as_template_from_project(
    output_dir: Path,
    name: str | None = None,
    description: str | None = None,
    dry_run: bool = False,
) -> Path | None:
    if name is None:
        name = output_dir.name

    if description is None:
        description = f"Template saved from {output_dir.name}"

    template_dir = Path(gettempdir()) / f".init-template-{name}"
    template_dir.mkdir(parents=True, exist_ok=True)

    template_yaml = template_dir / "template.yaml"
    template_yaml.write_text(
        yaml.dump(
            {
                "name": name,
                "description": description,
                "version": "1.0.0",
                "type": "unknown",
                "detectors": {"files": [], "keywords": []},
                "variables": [],
                "files": [],
            },
            default_flow_style=False,
        )
    )

    return save_template_to_global(
        Template(name=name, description=description, path=template_dir),
        dry_run=dry_run,
    )


def auto_generate(
    project_type: str,
    output_dir: Path,
    options: GenerationOptions,
) -> list[Path]:
    files_to_generate = _get_default_files(project_type)
    print(f"Auto-generating config for {project_type} project...")

    generated: list[Path] = []
    builtins = get_builtin_variables(output_dir)
    variables = {
        "port": options.variables.get("port", "3000"),
        "node_version": options.variables.get("node_version", "20"),
        **builtins,
    }

    for rel_path in files_to_generate:
        dest = output_dir / rel_path
        if dest.exists() and not options.force and not options.regenerate:
            continue

        content = _generate_default_content(rel_path, project_type, variables)
        if content is None:  # pragma: no cover (all paths return content)
            continue

        rendered = render_template(content, variables)

        if options.dry_run:
            print(f"  🔍 Would generate: {rel_path}")
            continue

        if dest.exists() and options.regenerate:
            bak = backup_file(dest)
            if bak:
                print(f"  💾 Backed up {rel_path} -> {bak.name}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered)
        print(f"  ✓ Generated: {rel_path}")
        generated.append(dest)

    return generated


def _get_default_files(project_type: str) -> list[str]:
    common = [".devcontainer/devcontainer.json", ".env.example"]
    type_files: dict[str, list[str]] = {
        "node": common + ["Dockerfile", "docker-compose.yml", ".nvmrc", ".gitignore"],
        "python": common + ["Dockerfile", "docker-compose.yml", ".python-version", ".gitignore"],
        "go": common + ["Dockerfile", "docker-compose.yml", ".gitignore", "Makefile"],
        "rust": common + ["Dockerfile", "docker-compose.yml", ".gitignore"],
        "java": common + ["Dockerfile", "docker-compose.yml", ".gitignore"],
        "ruby": common + ["Dockerfile", "docker-compose.yml", ".gitignore"],
        "php": common + ["Dockerfile", "docker-compose.yml", ".gitignore"],
        "deno": common + ["Dockerfile", "docker-compose.yml", ".gitignore"],
        "bun": common + ["Dockerfile", "docker-compose.yml", ".gitignore"],
    }
    return type_files.get(project_type, common)


def _generate_default_content(rel_path: str, project_type: str, variables: dict[str, str]) -> str | None:
    if rel_path == "Dockerfile":
        return _generate_dockerfile(project_type, variables)
    elif rel_path == "docker-compose.yml":
        return _generate_docker_compose(project_type, variables)
    elif rel_path == ".env.example":
        return "# Environment Variables\nPORT={{port}}\n# Generated: {{date}}\n"
    elif rel_path == ".nvmrc":
        return "{{node_version}}\n"
    elif rel_path == ".python-version":
        return "3.12\n"
    elif rel_path == ".gitignore":
        return _generate_gitignore(project_type)
    elif rel_path == "Makefile":
        return _generate_makefile(project_type)
    elif rel_path == ".devcontainer/devcontainer.json":
        return _generate_devcontainer(project_type)
    return None


def _generate_dockerfile(project_type: str, variables: dict[str, str]) -> str:
    dockerfiles = {
        "node": f"FROM node:{variables.get('node_version', '20')}-alpine\nWORKDIR /app\nCOPY package*.json ./\nRUN npm ci\nCOPY . .\nEXPOSE {variables.get('port', '3000')}\nCMD [\"node\", \"index.js\"]\n",
        "python": "FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt ./\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nEXPOSE 8000\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n",
        "go": "FROM golang:1.22-alpine AS builder\nWORKDIR /app\nCOPY go.mod go.sum ./\nRUN go mod download\nCOPY . .\nRUN CGO_ENABLED=0 go build -o /app/server\n\nFROM alpine:latest\nCOPY --from=builder /app/server /server\nEXPOSE 8080\nCMD [\"/server\"]\n",
        "rust": "FROM rust:1.77-slim AS builder\nWORKDIR /app\nCOPY . .\nRUN cargo build --release\n\nFROM debian:bookworm-slim\nCOPY --from=builder /app/target/release/app /app\nEXPOSE 8080\nCMD [\"/app\"]\n",
        "java": "FROM eclipse-temurin:21-jdk AS builder\nWORKDIR /app\nCOPY . .\nRUN ./mvnw package -DskipTests\n\nFROM eclipse-temurin:21-jre\nCOPY --from=builder /app/target/*.jar /app.jar\nEXPOSE 8080\nCMD [\"java\", \"-jar\", \"/app.jar\"]\n",
        "ruby": "FROM ruby:3.3-slim\nWORKDIR /app\nCOPY Gemfile Gemfile.lock ./\nRUN bundle install\nCOPY . .\nEXPOSE 3000\nCMD [\"ruby\", \"app.rb\"]\n",
        "php": "FROM php:8.3-cli\nWORKDIR /app\nCOPY . .\nEXPOSE 8000\nCMD [\"php\", \"-S\", \"0.0.0.0:8000\", \"-t\", \"public\"]\n",
    }
    return dockerfiles.get(project_type, f"FROM {project_type}:latest\nWORKDIR /app\nCOPY . .\nCMD [\"sh\"]\n")


def _generate_docker_compose(project_type: str, variables: dict[str, str]) -> str:
    port = variables.get("port", "3000")
    return f"""version: "3.8"
services:
  app:
    build: .
    ports:
      - "{port}:{port}"
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
"""


def _generate_gitignore(project_type: str) -> str:
    ignores = {
        "node": "node_modules/\ndist/\n.env\n*.log\n",
        "python": "__pycache__/\n*.pyc\n.venv/\nvenv/\n.env\n*.egg-info/\ndist/\n",
        "go": "vendor/\n*.exe\n*.exe~\n*.dll\n*.so\n*.dylib\n",
        "rust": "target/\nCargo.lock\n",
        "java": "target/\n*.class\n*.jar\n*.war\n.idea/\n",
    }
    return ignores.get(project_type, ".env\n__pycache__/\n*.log\ndist/\n")


def _generate_makefile(project_type: str) -> str:
    return """.PHONY: build run test clean

build:
\t@echo "Building..."

run:
\t@echo "Running..."

test:
\t@echo "Testing..."

clean:
\t@echo "Cleaning..."
"""


def _generate_devcontainer(project_type: str) -> str:
    return """{
  "name": "Development Container",
  "image": "mcr.microsoft.com/devcontainers/universal:2",
  "customizations": {
    "vscode": {
      "extensions": []
    }
  },
  "postCreateCommand": "",
  "forwardPorts": []
}
"""


def list_templates() -> list[dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "version": t.version,
            "type": t.project_type.value,
            "files": t.files,
        }
        for t in load_templates()
    ]
