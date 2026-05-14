from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from acorn.models import DetectorRule, ProjectType, Template

GLOBAL_DIR = Path.home() / ".acorn"
TEMPLATES_DIR = GLOBAL_DIR / "templates"
DETECTORS_DIR = GLOBAL_DIR / "detectors"
CACHE_DIR = GLOBAL_DIR / "cache"
CONFIG_FILE = GLOBAL_DIR / "config.yaml"
PROJECT_CONFIG_DIR = Path(".acorn")
PROJECT_CONFIG_FILE = PROJECT_CONFIG_DIR / "config.yaml"
PROJECT_LOCK_FILE = PROJECT_CONFIG_DIR / "lock.yaml"

BUILTIN_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
BUILTIN_DETECTORS_DIR = Path(__file__).resolve().parent / "detectors"

DEFAULT_CONFIG: dict[str, Any] = {
    "templates_dir": str(TEMPLATES_DIR),
    "detectors_dir": str(DETECTORS_DIR),
    "cache_dir": str(CACHE_DIR),
    "prefer_global": True,
    "default_port": "3000",
    "interactive": False,
    "default_lang": "en",
    "verbose": False,
    "debug": False,
    "offline": False,
    "log_level": "INFO",
}


def ensure_dirs() -> None:
    for d in [TEMPLATES_DIR, DETECTORS_DIR, CACHE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    ensure_dirs()
    if CONFIG_FILE.exists():
        raw = CONFIG_FILE.read_text()
        return {**DEFAULT_CONFIG, **(yaml.safe_load(raw) or {})}
    save_config(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(config: dict[str, Any]) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(yaml.dump(config, default_flow_style=False))


def load_detector_rules() -> list[DetectorRule]:
    rules: list[DetectorRule] = []

    detector_dirs = [BUILTIN_DETECTORS_DIR]
    if DETECTORS_DIR.exists():
        detector_dirs.append(DETECTORS_DIR)

    for d in detector_dirs:
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix in (".yaml", ".yml"):
                raw = f.read_text()
                data = yaml.safe_load(raw)
                if data:
                    if isinstance(data, list):
                        for item in data:
                            rules.append(DetectorRule.from_dict(item))
                    else:
                        rules.append(DetectorRule.from_dict(data))

    rules.sort(key=lambda r: r.priority, reverse=True)
    return rules


def load_templates() -> list[Template]:
    templates: list[Template] = []

    template_dirs = [BUILTIN_TEMPLATES_DIR]
    if TEMPLATES_DIR.exists():
        template_dirs.append(TEMPLATES_DIR)

    for d in template_dirs:
        if not d.exists():
            continue
        for t_dir in d.iterdir():
            if t_dir.is_dir():
                t_file = t_dir / "template.yaml"
                if t_file.exists():
                    raw = t_file.read_text()
                    data = yaml.safe_load(raw)
                    if data:
                        templates.append(Template.from_dict(data, path=t_dir))

    return templates


def find_template_by_name(name: str) -> Template | None:
    for t in load_templates():
        if t.name == name:
            return t
    return None


def resolve_template(template: Template) -> Template:
    if not template.extends:
        return template

    parent = find_template_by_name(template.extends)
    if not parent:
        return template

    resolved = Template(
        name=template.name,
        description=template.description or parent.description,
        version=template.version,
        path=template.path,
        project_type=template.project_type if template.project_type != ProjectType.UNKNOWN else parent.project_type,
        extends=template.extends,
        files=template.files or parent.files,
        variables=template.variables or parent.variables,
        detectors=template.detectors,
    )

    if not resolved.detectors.files and parent.detectors.files:
        resolved.detectors.files = list(parent.detectors.files)
    if not resolved.detectors.keywords and parent.detectors.keywords:
        resolved.detectors.keywords = list(parent.detectors.keywords)

    return resolved


def save_template_to_global(template: Template, dry_run: bool = False) -> Path | None:
    if not template.path:
        return None

    dest = TEMPLATES_DIR / template.name
    if dest.exists():
        print(f"✗ Template '{template.name}' already exists at {dest}")
        return None

    if dry_run:
        print(f"  🔍 Would save template to: {dest}")
        return dest

    import shutil
    shutil.copytree(template.path, dest, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    print(f"✓ Template saved to {dest}")
    return dest


def init_project_config(dir_path: Path, template_name: str | None = None, dry_run: bool = False) -> dict[str, Any] | None:
    config_dir = dir_path / PROJECT_CONFIG_DIR
    config_file = config_dir / "config.yaml"

    if config_file.exists():
        print(f"  ⚠ Project config already exists at {config_file}")
        return None

    config: dict[str, Any] = {
        "init_version": "0.1.0",
    }
    if template_name:
        config["template"] = template_name

    if dry_run:
        print(f"  🔍 Would create: {config_file}")
        return config

    config_dir.mkdir(parents=True, exist_ok=True)
    config_file.write_text(yaml.dump(config, default_flow_style=False))
    print(f"✓ Created project config: {config_file}")
    return config


def load_project_config(path: Path) -> dict[str, Any]:
    config_file = path / PROJECT_CONFIG_FILE
    if config_file.exists():
        return yaml.safe_load(config_file.read_text()) or {}
    return {}


def load_project_lock(path: Path) -> dict[str, Any]:
    lock_file = path / PROJECT_LOCK_FILE
    if lock_file.exists():
        return yaml.safe_load(lock_file.read_text()) or {}
    return {}


def save_project_lock(path: Path, lock: dict[str, Any]) -> None:
    lock_dir = path / PROJECT_CONFIG_DIR
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / "lock.yaml"
    lock_file.write_text(yaml.dump(lock, default_flow_style=False))


def export_config(path: Path, output: Path | None = None) -> Path | None:
    config = load_project_config(path)
    lock = load_project_lock(path)
    full = {"config": config, "lock": lock}
    dest = output or (path / "acorn-export.yaml")
    dest.write_text(yaml.dump(full, default_flow_style=False))
    print(f"✓ Config exported to {dest}")
    return dest


def import_config(target: Path, source: Path) -> dict[str, Any] | None:
    if not source.exists():
        print(f"✗ Source file not found: {source}")
        return None
    raw = source.read_text()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        print(f"✗ Invalid config file: {source}")
        return None
    if not data:
        print(f"✗ Invalid config file: {source}")
        return None

    project_config = data.get("config", {})
    if project_config:
        config_dir = target / PROJECT_CONFIG_DIR
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.yaml").write_text(yaml.dump(project_config, default_flow_style=False))

    lock_data = data.get("lock", {})
    if lock_data:
        lock_dir = target / PROJECT_CONFIG_DIR
        lock_dir.mkdir(parents=True, exist_ok=True)
        (lock_dir / "lock.yaml").write_text(yaml.dump(lock_data, default_flow_style=False))

    print(f"✓ Config imported from {source} to {target}")
    return data
