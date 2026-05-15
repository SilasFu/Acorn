from __future__ import annotations

import re
from pathlib import Path

SOURCE_EXTENSIONS_TS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
MAX_SCAN_FILES = 50


def _iter_source(dir_path: Path, max_files: int = MAX_SCAN_FILES) -> list[Path]:
    count = 0
    results = []
    for f in dir_path.rglob("*"):
        if f.suffix in SOURCE_EXTENSIONS_TS and f.is_file():
            results.append(f)
            count += 1
            if count >= max_files:
                break
    return results


def _read_safe(path: Path) -> str | None:
    try:
        return path.read_text("utf-8", errors="ignore")
    except OSError:
        return None


def detect_import_style(dir_path: Path) -> str:
    path_alias_patterns = [
        re.compile(r'from\s+["\']@/'),
        re.compile(r'from\s+["\']~/'),
        re.compile(r'from\s+["\']\$/'),
        re.compile(r'from\s+["\']@\w+/'),
    ]
    for f in _iter_source(dir_path):
        content = _read_safe(f)
        if not content:
            continue
        if any(p.search(content) for p in path_alias_patterns):
            return "path-alias"
        if re.search(r'from\s+["\']\.\.?/', content):
            return "relative"
    return "unknown"


def detect_module_system(dir_path: Path) -> str:
    has_esm_import = False
    has_cjs_require = False
    for f in _iter_source(dir_path):
        content = _read_safe(f)
        if not content:
            continue
        if re.search(r'^\s*import\s+', content, re.MULTILINE):
            has_esm_import = True
        if re.search(r'^\s*(?:const|let|var)\s+\w+\s*=\s*require\(', content, re.MULTILINE):
            has_cjs_require = True
        pkg = _find_nearest_package_json(f)
        if pkg and _read_safe(pkg):
            import json
            try:
                data = json.loads(_read_safe(pkg) or "{}")
                if data.get("type") == "module":
                    return "esm"
                if data.get("type") == "commonjs":
                    return "commonjs"
            except (json.JSONDecodeError, OSError):
                pass
    if has_esm_import and not has_cjs_require:
        return "esm"
    if has_cjs_require and not has_esm_import:
        return "commonjs"
    return "mixed" if has_esm_import and has_cjs_require else "unknown"


def _find_nearest_package_json(path: Path) -> Path | None:
    for parent in [path] + list(path.parents):
        candidate = parent / "package.json"
        if candidate.is_file():
            return candidate
    return None


def detect_naming_convention(dir_path: Path) -> str:
    scores = {"camelCase": 0, "snake_case": 0, "kebab-case": 0, "PascalCase": 0}
    for f in _iter_source(dir_path):
        name = f.stem
        if re.match(r'^[a-z]+[a-zA-Z0-9]*$', name):
            scores["camelCase"] += 1
        elif re.match(r'^[a-z]+(_[a-z0-9]+)*$', name):
            scores["snake_case"] += 1
        elif re.match(r'^[a-z]+(-[a-z0-9]+)*$', name):
            scores["kebab-case"] += 1
        elif re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
            scores["PascalCase"] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def detect_state_management(dir_path: Path) -> str | None:
    pkg_json = dir_path / "package.json"
    if not pkg_json.is_file():
        return None
    content = _read_safe(pkg_json)
    if not content:
        return None
    import json
    try:
        data = json.loads(content)
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    except json.JSONDecodeError:
        return None
    sm_map = {
        "zustand": "Zustand", "redux": "Redux", "@reduxjs/toolkit": "Redux Toolkit",
        "pinia": "Pinia", "valtio": "Valtio", "jotai": "Jotai",
        "recoil": "Recoil", "mobx": "MobX", "mobx-react": "MobX",
        "vuex": "Vuex", "ngrx": "NgRx",
    }
    for dep, label in sm_map.items():
        if dep in deps:
            return label
    return None


def detect_styling_approach(dir_path: Path) -> str | None:
    config_files = [
        "tailwind.config.js", "tailwind.config.ts", "tailwind.config.cjs",
        "unocss.config.ts", "unocss.config.js",
    ]
    for cf in config_files:
        if (dir_path / cf).is_file():
            return "tailwindcss" if cf.startswith("tailwind") else "unocss"
    pkg_json = dir_path / "package.json"
    if pkg_json.is_file():
        content = _read_safe(pkg_json)
        if content:
            import json
            try:
                data = json.loads(content)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            except json.JSONDecodeError:
                deps = {}
            style_map = {
                "tailwindcss": "tailwindcss", "unocss": "unocss",
                "styled-components": "styled-components",
                "@emotion/react": "emotion", "@emotion/styled": "emotion",
                "sass": "sass", "less": "less", "stylus": "stylus",
                "@stitches/react": "Stitches",
            }
            for dep, label in style_map.items():
                if dep in deps:
                    return label
    if list(dir_path.rglob("*.module.css")):
        return "css-modules"
    return None


def detect_api_style(dir_path: Path) -> str | None:
    pkg_json = dir_path / "package.json"
    if pkg_json.is_file():
        content = _read_safe(pkg_json)
        if content:
            import json
            try:
                data = json.loads(content)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            except json.JSONDecodeError:
                deps = {}
            if "@trpc/client" in deps or "@trpc/server" in deps or "trpc" in deps:
                return "tRPC"
            if "graphql" in deps or "@graphql-codegen" in deps:
                return "GraphQL"
            if "grpc" in deps or "@grpc/grpc-js" in deps:
                return "gRPC"
    for f in _iter_source(dir_path):
        content = _read_safe(f)
        if not content:
            continue
        if "tRPC" in content or "trpc" in content:
            return "tRPC"
    if list(dir_path.rglob("*.graphql")) or list(dir_path.rglob("*.gql")):
        return "GraphQL"
    if pkg_json.is_file():
        if list(dir_path.rglob("route.ts")) or list(dir_path.rglob("route.js")):
            return "REST (file-based)"
    return None


def detect_architecture_pattern(dir_path: str | Path, language: str) -> str | None:
    dir_path = Path(dir_path) if isinstance(dir_path, str) else dir_path
    if language == "node":
        if (dir_path / "app").is_dir() or (dir_path / "src/app").is_dir():
            return "app-router"
        if (dir_path / "pages").is_dir() or (dir_path / "src/pages").is_dir():
            return "pages-router"
        if (dir_path / "lerna.json").is_file() or (dir_path / "pnpm-workspace.yaml").is_file():
            return "monorepo"
        if (dir_path / "turbo.json").is_file():
            return "monorepo (turborepo)"
        if (dir_path / "nx.json").is_file():
            return "monorepo (nx)"
    if language == "python":
        if (dir_path / "apps").is_dir() and (dir_path / "pyproject.toml").is_file():
            return "monorepo"
    return None


def detect_entry_points(dir_path: Path, language: str) -> list[str]:
    patterns = {
        "node": ["index.js", "index.ts", "app.js", "app.ts", "server.js", "server.ts", "main.js", "main.ts"],
        "python": ["main.py", "app.py", "wsgi.py", "manage.py", "run.py"],
        "go": ["main.go", "cmd/server/main.go", "cmd/api/main.go"],
        "rust": ["src/main.rs"],
        "java": ["src/main/java/**/Application.java"],
        "ruby": ["app.rb", "config.ru", "bin/rails"],
        "php": ["public/index.php", "index.php", "artisan"],
    }
    found = []
    for pattern in patterns.get(language, []):
        if "*" in pattern:
            for f in dir_path.glob(pattern):
                found.append(str(f.relative_to(dir_path)))
        else:
            f = dir_path / pattern
            if f.is_file():
                found.append(pattern)
    return found


def detect_directory_purpose(structure: dict[str, list[str]], language: str) -> dict[str, str]:
    purposes: dict[str, str] = {}
    known: dict[str, dict[str, str]] = {
        "node": {
            "app": "Route handlers and pages",
            "pages": "Page components",
            "components": "Reusable React components",
            "lib": "Utility functions and shared logic",
            "utils": "Utility functions",
            "server": "Server-side code",
            "api": "API route handlers",
            "hooks": "Custom React hooks",
            "styles": "CSS/style files",
            "public": "Static assets",
            "types": "TypeScript type definitions",
            "db": "Database schema and queries",
            "config": "Configuration files",
            "middleware": "Express/Koa middleware",
            "routes": "Route definitions",
            "controllers": "Controller logic",
            "models": "Data models",
            "services": "Business logic layer",
            "validators": "Input validation",
            "tests": "Test files",
            "migrations": "Database migrations",
            "seeds": "Database seed data",
        },
        "python": {
            "app": "Application entry point",
            "api": "API route handlers",
            "routes": "Route definitions",
            "models": "SQLAlchemy/Django models",
            "schemas": "Pydantic/marshmallow schemas",
            "services": "Business logic layer",
            "utils": "Utility functions",
            "tests": "Test files",
            "migrations": "Database migrations",
            "config": "Configuration",
            "middleware": "Middleware",
            "templates": "Jinja2 templates",
        },
    }
    for top_dir, files in structure.items():
        for lang_key, mapping in known.items():
            if language == lang_key and top_dir in mapping:
                purposes[top_dir] = mapping[top_dir]
                break
        else:
            purposes[top_dir] = "Unknown"
    return purposes
