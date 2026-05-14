from __future__ import annotations

import re
from pathlib import Path

import yaml

from acorn.config import (
    load_detector_rules,
    load_templates,
    resolve_template,
)
from acorn.models import (
    DetectionResult,
    DetectorRule,
    ProjectType,
    Template,
)

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "target", "build", "dist", ".next", ".nuxt",
    ".idea", ".vscode", ".DS_Store",
}

MANIFEST_MAP: dict[str, ProjectType] = {
    "package.json": ProjectType.NODE,
    "pyproject.toml": ProjectType.PYTHON,
    "requirements.txt": ProjectType.PYTHON,
    "setup.py": ProjectType.PYTHON,
    "setup.cfg": ProjectType.PYTHON,
    "Pipfile": ProjectType.PYTHON,
    "go.mod": ProjectType.GO,
    "Cargo.toml": ProjectType.RUST,
    "pom.xml": ProjectType.JAVA,
    "build.gradle": ProjectType.JAVA,
    "build.gradle.kts": ProjectType.JAVA,
    "Gemfile": ProjectType.RUBY,
    "composer.json": ProjectType.PHP,
    "deno.json": ProjectType.DENO,
    "deno.jsonc": ProjectType.DENO,
    "bun.lockb": ProjectType.BUN,
    "bun.lock": ProjectType.BUN,
}

ENTRY_FILE_PATTERNS: dict[ProjectType, list[str]] = {
    ProjectType.NODE: ["index.js", "index.ts", "app.js", "app.ts", "server.js", "server.ts", "main.js"],
    ProjectType.PYTHON: ["main.py", "app.py", "wsgi.py", "manage.py"],
    ProjectType.GO: ["main.go", "cmd/server/main.go"],
    ProjectType.RUST: ["src/main.rs"],
    ProjectType.JAVA: ["src/main/java/**/Application.java", "src/main/java/**/App.java"],
    ProjectType.RUBY: ["app.rb", "config.ru", "bin/rails"],
    ProjectType.PHP: ["public/index.php", "index.php", "artisan"],
}


def _read_file_safe(path: Path) -> str | None:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    return None


def _find_files_recursive(dir_path: Path, patterns: list[str]) -> list[Path]:
    results: list[Path] = []
    for pattern in patterns:
        for f in dir_path.rglob(pattern):
            parts = f.relative_to(dir_path).parts
            if any(part in IGNORE_DIRS for part in parts):
                continue
            results.append(f)
    return results


def _has_files(dir_path: Path, filenames: list[str]) -> bool:
    return any((dir_path / f).exists() for f in filenames)


def _check_content_recursive(dir_path: Path, keywords: list[str]) -> int:
    found = 0
    for f in dir_path.rglob("*"):
        if not f.is_file():
            continue
        parts = f.relative_to(dir_path).parts
        if any(part in IGNORE_DIRS for part in parts):
            continue
        content = _read_file_safe(f)
        if content:
            found += sum(1 for kw in keywords if kw in content)
    return found


def _check_dependencies(dir_path: Path, deps: list[str]) -> bool:
    for manifest_name in MANIFEST_MAP:
        manifest = dir_path / manifest_name
        content = _read_file_safe(manifest)
        if content:
            if all(d in content for d in deps):
                return True
    return False


def _check_patterns(dir_path: Path, patterns: list[str]) -> int:
    matched = 0
    for pattern in patterns:
        if _find_files_recursive(dir_path, [pattern]):
            matched += 1
    return matched


def _detect_by_manifest(dir_path: Path) -> ProjectType | None:
    for manifest, ptype in MANIFEST_MAP.items():
        if (dir_path / manifest).exists():
            return ptype
    return None


def _find_entry_files(dir_path: Path) -> list[tuple[str, ProjectType]]:
    found: list[tuple[str, ProjectType]] = []
    for ptype, patterns in ENTRY_FILE_PATTERNS.items():
        for pattern in patterns:
            if "**" in pattern:
                matches = list(dir_path.glob(pattern))
                if matches:
                    found.append((matches[0].name, ptype))
            else:
                f = dir_path / pattern
                if f.exists():
                    found.append((pattern, ptype))
    return found


def _detect_port(dir_path: Path, project_type: ProjectType) -> str | None:
    if project_type == ProjectType.NODE:
        for pattern in ["*.js", "*.ts"]:
            for f in _find_files_recursive(dir_path, [pattern]):
                content = _read_file_safe(f)
                if content:
                    m = re.search(r'(?:listen|port)\s*[=:(]\s*(\d{4,5})', content)
                    if m:
                        return m.group(1)
    elif project_type == ProjectType.PYTHON:
        for pattern in ["*.py"]:
            for f in _find_files_recursive(dir_path, [pattern]):
                content = _read_file_safe(f)
                if content:
                    m = re.search(r'port\s*=\s*(\d{4,5})', content)
                    if m:
                        return m.group(1)
    return None


def evaluate_rule(rule: DetectorRule, dir_path: Path) -> float:
    score = 0.0
    max_score = 0.0

    c = rule.conditions

    if c.files:
        max_score += 35.0
        found_files = sum(1 for f in c.files if (dir_path / f).exists())
        if found_files > 0:
            score += 35.0 * (found_files / len(c.files))

    if c.content:
        max_score += 30.0
        found_count = _check_content_recursive(dir_path, c.content)
        if found_count > 0:
            score += 30.0 * min(found_count / len(c.content), 1.0)

    if c.dependencies:
        max_score += 20.0
        if _check_dependencies(dir_path, c.dependencies):
            score += 20.0

    if c.patterns:
        max_score += 15.0
        matched = _check_patterns(dir_path, c.patterns)
        if matched > 0:
            score += 15.0 * min(matched / len(c.patterns), 1.0)

    return score / max_score if max_score > 0 else 0.0


def detect_project_type(dir_path: Path | str) -> DetectionResult:
    if isinstance(dir_path, str):
        dir_path = Path(dir_path).resolve()
    if not dir_path.is_dir():
        return DetectionResult(project_type=ProjectType.UNKNOWN, details={"error": "path is not a directory"})

    manifest_type = _detect_by_manifest(dir_path)

    rules = load_detector_rules()
    templates = load_templates()

    all_matches: list[tuple[ProjectType, str, float]] = []
    best_score = 0.0
    result = DetectionResult()

    if manifest_type:
        all_matches.append((manifest_type, "manifest", 0.3))
        result.project_type = manifest_type
        result.confidence = 0.3
        best_score = 0.3

    for rule in rules:
        score = evaluate_rule(rule, dir_path)
        if score > 0:
            all_matches.append((rule.type, f"rule:{rule.name}", score))
        if score > best_score:
            best_score = score
            result.project_type = rule.type
            result.confidence = score
            result.framework = None
            result.matched_template = None
            if rule.indicators:
                for indicator in rule.indicators:
                    if _check_indicator(indicator.check_expression, dir_path):
                        result.framework = indicator.name
                        break

    for template in templates:
        resolved = resolve_template(template)
        score = evaluate_template_match(resolved, dir_path)
        if score > 0:
            all_matches.append((resolved.project_type, f"template:{template.name}", score))
        if score > best_score:
            best_score = score
            result.project_type = resolved.project_type
            result.matched_template = template.name
            result.confidence = score

    entry_files = _find_entry_files(dir_path)
    for entry_name, etype in entry_files:
        if etype not in [m[0] for m in all_matches]:
            all_matches.append((etype, f"entry:{entry_name}", 0.25))
            if 0.25 > best_score:
                best_score = 0.25
                result.project_type = etype

    detected_port = _detect_port(dir_path, result.project_type)

    result.confidence = round(best_score, 2)
    all_matches.sort(key=lambda m: m[2], reverse=True)
    result.all_matches = [(pt, src, round(sc, 2)) for pt, src, sc in all_matches]

    files_found = []
    for f in sorted(dir_path.iterdir())[:20]:
        if f.is_file():
            files_found.append(f.name)
    result.details["files_found"] = files_found
    result.details["entry_files"] = [e[0] for e in entry_files]
    if detected_port:
        result.details["detected_port"] = detected_port

    return result


def detect_mixed_project(dir_path: Path | str) -> list[tuple[ProjectType, str, float]]:
    if isinstance(dir_path, str):
        dir_path = Path(dir_path).resolve()
    result = detect_project_type(dir_path)
    return result.all_matches[:5]


def _check_indicator(expression: str, dir_path: Path) -> bool:
    parts = expression.split("&&")
    for part in parts:
        part = part.strip()
        if " in " in part:
            left, right = part.split(" in ", 1)
            left = left.strip()
            right = right.strip().strip("'\"")
            if left.startswith("dependencies."):
                dep_name = left[len("dependencies.") :]
                pkg_file = dir_path / right
                content = _read_file_safe(pkg_file)
                if content:
                    try:
                        pkg = yaml.safe_load(content)
                        if isinstance(pkg, dict):
                            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                            if dep_name not in deps:
                                return False
                        else:
                            return False
                    except Exception:
                        return False
                else:
                    return False
            elif "." in right:
                target_file = dir_path / right
                content = _read_file_safe(target_file)
                if content is None or left.strip("'\"") not in content:
                    return False
            else:
                return False
        elif "==" in part or "contains" in part:
            pass
        else:
            content = _read_file_safe(dir_path / part.strip())
            if content is None:
                return False
    return True


def evaluate_template_match(template: Template, dir_path: Path) -> float:
    score = 0.0
    max_score = 0.0

    d = template.detectors

    if d.files:
        max_score += 50.0
        found = sum(1 for f in d.files if (dir_path / f).exists())
        if found > 0:
            score += 50.0 * (found / len(d.files))

    if d.keywords:
        max_score += 50.0
        found = _check_content_recursive(dir_path, d.keywords)
        if found > 0:
            score += 50.0 * min(found / len(d.keywords), 1.0)

    return score / max_score if max_score > 0 else 0.0
