from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from acorn._compat import tomllib
from acorn.analysis import ast_lite

SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".c", ".cpp", ".h", ".hpp"}
IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "target", "build", "dist", ".next", ".nuxt",
    ".idea", ".vscode", ".DS_Store", "vendor",
}


@dataclass
class ProjectInsights:
    language: str = "unknown"
    framework: str | None = None
    package_manager: str | None = None

    has_src_dir: bool = False
    has_app_router: bool = False
    src_structure: dict[str, list[str]] = field(default_factory=dict)
    api_route_paths: list[str] = field(default_factory=list)
    api_route_detection_method: str = "none"

    key_dependencies: dict[str, str] = field(default_factory=dict)

    bundler: str | None = None
    css_framework: str | None = None
    orm: str | None = None
    test_runner: str | None = None
    auth_lib: str | None = None

    entry_points: list[str] = field(default_factory=list)

    import_style: str = "unknown"
    module_system: str = "unknown"
    naming_convention: str = "unknown"
    state_management: str | None = None
    styling_approach: str | None = None
    api_style: str | None = None
    architecture_pattern: str | None = None
    directory_purposes: dict[str, str] = field(default_factory=dict)


_JS_FRAMEWORKS: dict[str, tuple[str | None, str | None, str | None]] = {
    "next": ("Next.js", None, None),
    "nuxt": ("Nuxt", None, None),
    "@remix-run/react": ("Remix", None, None),
    "gatsby": ("Gatsby", None, None),
    "express": ("Express", None, None),
    "fastify": ("Fastify", None, None),
    "@nestjs/core": ("NestJS", None, None),
    "@sveltejs/kit": ("SvelteKit", None, None),
    "vue": ("Vue", None, None),
    "react": ("React", None, None),
    "hono": ("Hono", None, None),
    "elysia": ("Elysia", None, None),
}

_JS_BUNDLERS = {"vite", "webpack", "rollup", "esbuild", "turbo", "parcel", "tsup", "unbuild"}
_JS_CSS = {"tailwindcss", "unocss", "styled-components", "@emotion/react", "sass", "less", "postcss"}
_JS_ORM = {"prisma", "drizzle-orm", "typeorm", "sequelize", "mongoose", "knex"}
_JS_TEST = {"vitest", "jest", "playwright", "cypress", "ava", "mocha", "jasmine"}
_JS_AUTH = {"next-auth", "@auth/core", "passport", "lucia-auth", "clerk-sdk-node"}


def _read_json_safe(path: Path) -> dict | None:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return None
    return None


def _read_toml_safe(path: Path) -> dict | None:
    try:
        if path.is_file() and tomllib is not None:
            return tomllib.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, Exception):
        return None
    return None


def _read_text_safe(path: Path) -> str | None:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    return None


def _get_deps(pkg: dict) -> dict[str, str]:
    return {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}


def _analyze_js_deps(ins: ProjectInsights, pkg: dict) -> None:
    deps = _get_deps(pkg)
    ins.key_dependencies = dict(sorted(deps.items()))
    ins.package_manager = pkg.get("packageManager", "").split("@")[0] or None
    if not ins.package_manager:
        if (Path(pkg.get("__path", "")) if "__path" in pkg else Path()).parent / "yarn.lock":
            ins.package_manager = "yarn"
        elif (Path(pkg.get("__path", "")) if "__path" in pkg else Path()).parent / "pnpm-lock.yaml":
            ins.package_manager = "pnpm"

    for dep_name, dep_version in deps.items():
        if dep_name in _JS_FRAMEWORKS:
            fw, _, _ = _JS_FRAMEWORKS[dep_name]
            if ins.framework is None:
                ins.framework = fw
        if dep_name in _JS_BUNDLERS and ins.bundler is None:
            ins.bundler = dep_name
        if dep_name in _JS_CSS and ins.css_framework is None:
            ins.css_framework = dep_name
        if dep_name in _JS_ORM and ins.orm is None:
            ins.orm = dep_name
        if dep_name in _JS_TEST and ins.test_runner is None:
            ins.test_runner = dep_name
        if dep_name in _JS_AUTH and ins.auth_lib is None:
            ins.auth_lib = dep_name


def _analyze_js_structure(ins: ProjectInsights, dir_path: Path, pkg: dict) -> None:
    if ins.framework == "Next.js":
        app_dir = dir_path / "app"
        if app_dir.is_dir():
            ins.has_app_router = True
            ins.api_route_detection_method = "nextjs-app-router"
            for route_file in app_dir.rglob("route.ts"):
                rel = route_file.relative_to(app_dir)
                route_path = "/" + str(rel.parent)
                ins.api_route_paths.append(route_path)
            for route_file in app_dir.rglob("route.js"):
                rel = route_file.relative_to(app_dir)
                route_path = "/" + str(rel.parent)
                ins.api_route_paths.append(route_path)

    src_dir = dir_path / "src"
    if src_dir.is_dir():
        ins.has_src_dir = True
        pages = sorted(str(f.relative_to(src_dir)) for f in src_dir.rglob("*") if f.is_file())
        by_top = {}
        for p in pages:
            top = p.split("/")[0]
            by_top.setdefault(top, []).append(p)
        ins.src_structure = by_top


def _analyze_py_deps(ins: ProjectInsights, pyproj: dict) -> None:
    project = pyproj.get("project", {})
    deps = project.get("dependencies", [])
    optional = project.get("optional-dependencies", {})

    all_deps = list(deps)
    for group in optional.values():
        all_deps.extend(group)

    fw_map = {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "starlette": "Starlette",
        "litestar": "Litestar",
        "aiohttp": "aiohttp",
        "tornado": "Tornado",
        "bottle": "Bottle",
        "sanic": "Sanic",
        "quart": "Quart",
    }
    for dep_line in all_deps:
        dep_name = dep_line.split("[")[0].split(">")[0].split("<")[0].split("=")[0].split("~")[0].strip()
        if dep_name in fw_map and ins.framework is None:
            ins.framework = fw_map[dep_name]

    tool = pyproj.get("tool", {})
    if ins.orm is None:
        if tool.get("sqlalchemy"):
            ins.orm = "sqlalchemy"
    if ins.test_runner is None:
        if tool.get("pytest"):
            ins.test_runner = "pytest"
        elif tool.get("unittest"):
            ins.test_runner = "unittest"


def _analyze_py_requirements(ins: ProjectInsights, dir_path: Path) -> None:
    req = _read_text_safe(dir_path / "requirements.txt")
    if req is None:
        return
    fw_map = {"fastapi": "FastAPI", "flask": "Flask", "django": "Django"}
    for line in req.splitlines():
        line = line.strip().lower()
        for key, val in fw_map.items():
            if line.startswith(key) and ins.framework is None:
                ins.framework = val


def _analyze_src_structure(ins: ProjectInsights, dir_path: Path) -> None:
    src_dir = dir_path / "src"
    if not src_dir.is_dir():
        return
    ins.has_src_dir = True
    pages = sorted(str(f.relative_to(src_dir)) for f in src_dir.rglob("*") if f.is_file())
    by_top = {}
    for p in pages:
        top = p.split("/")[0]
        by_top.setdefault(top, []).append(p)
    ins.src_structure = by_top

    app_dir = src_dir / "app"
    if app_dir.is_dir():
        for route_file in app_dir.rglob("route.ts"):
            rel = route_file.relative_to(app_dir)
            ins.api_route_paths.append("/" + str(rel.parent))
            ins.api_route_detection_method = "nextjs-app-router"
        for route_file in app_dir.rglob("route.js"):
            rel = route_file.relative_to(app_dir)
            ins.api_route_paths.append("/" + str(rel.parent))
            ins.api_route_detection_method = "nextjs-app-router"


def _find_entry_points(ins: ProjectInsights, dir_path: Path) -> None:
    entry_patterns = {
        "node": ["index.js", "index.ts", "app.js", "app.ts", "server.js", "server.ts", "main.js"],
        "python": ["main.py", "app.py", "wsgi.py", "manage.py"],
        "go": ["main.go"],
        "rust": ["src/main.rs"],
    }
    for fname in entry_patterns.get(ins.language, []):
        f = dir_path / fname
        if f.is_file():
            ins.entry_points.append(fname)
    if ins.language == "java":
        for f in dir_path.rglob("Application.java"):
            ins.entry_points.append(str(f.relative_to(dir_path)))
    if ins.language == "ruby":
        for fname in ["app.rb", "config.ru", "bin/rails"]:
            f = dir_path / fname
            if f.is_file():
                ins.entry_points.append(fname)
    if ins.language == "php":
        for fname in ["public/index.php", "index.php", "artisan"]:
            f = dir_path / fname
            if f.is_file():
                ins.entry_points.append(fname)


def analyze(dir_path: Path | str) -> ProjectInsights:
    if isinstance(dir_path, str):
        dir_path = Path(dir_path).resolve()
    if not dir_path.is_dir():
        return ProjectInsights()

    ins = ProjectInsights()

    pkg = _read_json_safe(dir_path / "package.json")
    if pkg:
        ins.language = "node"
        _analyze_js_deps(ins, pkg)
        _analyze_js_structure(ins, dir_path, pkg)

    pyproj = _read_toml_safe(dir_path / "pyproject.toml")
    if pyproj and ins.language == "unknown":
        ins.language = "python"
        _analyze_py_deps(ins, pyproj)
    elif (dir_path / "requirements.txt").exists() and ins.language == "unknown":
        ins.language = "python"
        _analyze_py_requirements(ins, dir_path)
    elif (dir_path / "setup.py").exists() and ins.language == "unknown":
        ins.language = "python"
    elif (dir_path / "setup.cfg").exists() and ins.language == "unknown":
        ins.language = "python"
    elif (dir_path / "Pipfile").exists() and ins.language == "unknown":
        ins.language = "python"

    if (dir_path / "go.mod").exists() and ins.language == "unknown":
        ins.language = "go"
        go_mod = _read_text_safe(dir_path / "go.mod")
        if go_mod:
            m = re.search(r"^module\s+(\S+)", go_mod, re.MULTILINE)
            if m:
                ins.key_dependencies["module"] = m.group(1)

    if (dir_path / "Cargo.toml").exists() and ins.language == "unknown":
        ins.language = "rust"
        cargo = _read_toml_safe(dir_path / "Cargo.toml")
        if cargo:
            deps = cargo.get("dependencies", {})
            if isinstance(deps, dict):
                ins.key_dependencies = {k: str(v) if not isinstance(v, dict) else (v.get("version", "*")) for k, v in deps.items()}
            fw_map = {"actix-web": "Actix Web", "axum": "Axum", "rocket": "Rocket", "tide": "Tide", "warp": "Warp"}
            for dep_name in deps if isinstance(deps, dict) else []:
                if dep_name in fw_map and ins.framework is None:
                    ins.framework = fw_map[dep_name]

    if (dir_path / "pom.xml").exists() and ins.language == "unknown":
        ins.language = "java"
    elif (dir_path / "build.gradle").exists() and ins.language == "unknown":
        ins.language = "java"
    elif (dir_path / "build.gradle.kts").exists() and ins.language == "unknown":
        ins.language = "java"

    if (dir_path / "Gemfile").exists() and ins.language == "unknown":
        ins.language = "ruby"
        gemfile = _read_text_safe(dir_path / "Gemfile")
        if gemfile:
            fw_map = {"rails": "Rails", "sinatra": "Sinatra", "hanami": "Hanami", "roda": "Roda"}
            for line in gemfile.splitlines():
                line = line.strip()
                for key, val in fw_map.items():
                    if re.match(rf'^\s*gem\s+["\']{key}["\']', line) and ins.framework is None:
                        ins.framework = val

    if (dir_path / "composer.json").exists() and ins.language == "unknown":
        ins.language = "php"
        composer = _read_json_safe(dir_path / "composer.json")
        if composer:
            deps = _get_deps(composer)
            ins.key_dependencies = dict(sorted(deps.items()))
            fw_map = {"laravel/framework": "Laravel", "symfony/symfony": "Symfony", "cakephp/cakephp": "CakePHP", "codeigniter/framework": "CodeIgniter"}
            for dep_name in deps:
                if dep_name in fw_map and ins.framework is None:
                    ins.framework = fw_map[dep_name]

    if (dir_path / "deno.json").exists() and ins.language == "unknown":
        ins.language = "deno"
    elif (dir_path / "deno.jsonc").exists() and ins.language == "unknown":
        ins.language = "deno"

    if (dir_path / "bun.lockb").exists() and ins.language == "unknown":
        ins.language = "bun"
    elif (dir_path / "bun.lock").exists() and ins.language == "unknown":
        ins.language = "bun"

    _analyze_src_structure(ins, dir_path)
    _find_entry_points(ins, dir_path)

    if ins.language == "node":
        ins.import_style = ast_lite.detect_import_style(dir_path)
        ins.module_system = ast_lite.detect_module_system(dir_path)
        ins.naming_convention = ast_lite.detect_naming_convention(dir_path)
        ins.state_management = ast_lite.detect_state_management(dir_path)
        ins.styling_approach = ast_lite.detect_styling_approach(dir_path)
        ins.api_style = ast_lite.detect_api_style(dir_path)
        ins.architecture_pattern = ast_lite.detect_architecture_pattern(dir_path, "node")
        ins.directory_purposes = ast_lite.detect_directory_purpose(ins.src_structure, "node")

    return ins


def has_source_code(dir_path: Path | str) -> bool:
    if isinstance(dir_path, str):
        dir_path = Path(dir_path).resolve()
    if not dir_path.is_dir():
        return False
    try:
        for f in dir_path.rglob("*"):
            if any(part in IGNORE_DIRS for part in f.relative_to(dir_path).parts):
                continue
            if f.is_file() and f.suffix in SOURCE_EXTENSIONS:
                return True
    except (PermissionError, OSError):
        return False
    return False
