from __future__ import annotations

from typing import Any

LANGUAGE_CONVENTIONS: dict[str, dict[str, Any]] = {
    "node": {
        "base_image": "node:20-alpine3.19",
        "run_cmd": "node",
        "build_cmd": "npm run build",
        "test_cmd": "npm test",
        "dev_port": "3000",
        "env_file": ".env",
        "install_cmd": "npm ci",
        "dev_cmd": "npm run dev",
        "healthcheck": "CMD curl --fail http://localhost:3000/health || exit 1",
    },
    "python": {
        "base_image": "python:3.12-alpine3.19",
        "run_cmd": "python",
        "build_cmd": "",
        "test_cmd": "pytest",
        "dev_port": "8000",
        "env_file": ".env",
        "install_cmd": "pip install --no-cache-dir -r requirements.txt",
        "dev_cmd": "uvicorn app.main:app --reload --host 0.0.0.0",
        "healthcheck": "CMD curl --fail http://localhost:8000/health || exit 1",
    },
    "go": {
        "base_image": "golang:1.22-alpine3.19",
        "run_cmd": "./server",
        "build_cmd": "CGO_ENABLED=0 go build -o /app/server .",
        "test_cmd": "go test ./...",
        "dev_port": "8080",
        "env_file": ".env",
        "install_cmd": "go mod download",
        "dev_cmd": "go run .",
        "healthcheck": "CMD curl --fail http://localhost:8080/health || exit 1",
    },
    "rust": {
        "base_image": "rust:1.78-alpine3.19",
        "run_cmd": "./server",
        "build_cmd": "cargo build --release",
        "test_cmd": "cargo test",
        "dev_port": "8080",
        "env_file": ".env",
        "install_cmd": "cargo build --release",
        "dev_cmd": "cargo run",
        "healthcheck": "CMD curl --fail http://localhost:8080/health || exit 1",
    },
    "java": {
        "base_image": "eclipse-temurin:21-jdk-alpine",
        "run_cmd": "java",
        "build_cmd": "./mvnw package -DskipTests",
        "test_cmd": "./mvnw test",
        "dev_port": "8080",
        "env_file": ".env",
        "install_cmd": "./mvnw dependency:resolve",
        "dev_cmd": "./mvnw spring-boot:run",
        "healthcheck": "CMD curl --fail http://localhost:8080/health || exit 1",
    },
    "ruby": {
        "base_image": "ruby:3.3-alpine3.19",
        "run_cmd": "ruby",
        "build_cmd": "",
        "test_cmd": "bundle exec rspec",
        "dev_port": "3000",
        "env_file": ".env",
        "install_cmd": "bundle install",
        "dev_cmd": "bundle exec rails server",
        "healthcheck": "CMD curl --fail http://localhost:3000/health || exit 1",
    },
    "php": {
        "base_image": "php:8.3-cli-alpine3.19",
        "run_cmd": "php",
        "build_cmd": "",
        "test_cmd": "phpunit",
        "dev_port": "8000",
        "env_file": ".env",
        "install_cmd": "composer install --no-dev",
        "dev_cmd": "php -S 0.0.0.0:8000 -t public",
        "healthcheck": "CMD curl --fail http://localhost:8000/health || exit 1",
    },
    "deno": {
        "base_image": "denoland/deno:alpine-1.44",
        "run_cmd": "deno",
        "build_cmd": "deno cache main.ts",
        "test_cmd": "deno test",
        "dev_port": "8000",
        "env_file": ".env",
        "install_cmd": "deno cache main.ts",
        "dev_cmd": "deno run --watch main.ts",
        "healthcheck": "CMD curl --fail http://localhost:8000/health || exit 1",
    },
    "bun": {
        "base_image": "oven/bun:1.1-alpine",
        "run_cmd": "bun",
        "build_cmd": "bun run build",
        "test_cmd": "bun test",
        "dev_port": "3000",
        "env_file": ".env",
        "install_cmd": "bun install",
        "dev_cmd": "bun run dev",
        "healthcheck": "CMD curl --fail http://localhost:3000/health || exit 1",
    },
}

ANTI_PATTERNS: dict[str, list[str]] = {
    "node": [
        "Do not use `var` — use `const` or `let`",
        "Avoid callback hell — prefer async/await",
        "Do not commit `node_modules` to version control",
    ],
    "python": [
        "Do not use wildcard imports (`from x import *`)",
        "Avoid mutable default arguments",
        "Do not commit `__pycache__` or `.pyc` files",
    ],
    "go": [
        "Do not use `golint` — use `staticcheck` instead",
        "Avoid `init()` functions when possible",
        "Do not use `interface{}` — use `any`",
    ],
    "rust": [
        "Avoid `unwrap()` — prefer pattern matching or `?`",
        "Do not use `unsafe` unless absolutely necessary",
        "Prefer `cargo clippy` over manual linting",
    ],
    "java": [
        "Avoid `System.out.println` — use a logger",
        "Do not catch generic `Exception`",
        "Prefer constructor injection over field injection",
    ],
    "ruby": [
        "Avoid global variables — prefer constants",
        "Do not use `eval` or `send` with user input",
        "Prefer `SafeNavigation` (`&.`) over nil checks",
    ],
    "php": [
        "Avoid `mysql_*` functions — use PDO or Eloquent",
        "Do not use `extract()` on user input",
        "Prefer type declarations in function signatures",
    ],
    "deno": [
        "Prefer web-standard APIs over Node.js compat",
        "Use `deno fmt` for consistent formatting",
        "Avoid `--allow-all` in production deployments",
    ],
    "bun": [
        "Prefer Bun-native APIs over Node.js polyfills",
        "Use `bun run` instead of `npm run`",
        "Avoid mixing Bun and npm lock files",
    ],
}

COMMON_COMMANDS: dict[str, list[str]] = {
    "node": ["npm run dev", "npm run build", "npm test", "npm run lint"],
    "python": ["python main.py", "pytest", "ruff check .", "mypy ."],
    "go": ["go run .", "go test ./...", "go build .", "go vet ./..."],
    "rust": ["cargo run", "cargo test", "cargo build --release", "cargo clippy"],
    "java": ["./mvnw spring-boot:run", "./mvnw test", "./mvnw clean package"],
    "ruby": ["bundle exec rails server", "bundle exec rspec", "bin/rails db:migrate"],
    "php": ["php -S 0.0.0.0:8000 -t public", "phpunit", "composer update"],
    "deno": ["deno run main.ts", "deno test", "deno fmt"],
    "bun": ["bun run dev", "bun test", "bun run build"],
}

ENV_VARS: dict[str, list[tuple[str, str]]] = {
    "node": [("NODE_ENV", "production"), ("PORT", "3000"), ("DATABASE_URL", "postgres://...")],
    "python": [("PYTHON_ENV", "production"), ("PORT", "8000"), ("DATABASE_URL", "postgres://...")],
    "go": [("GO_ENV", "production"), ("PORT", "8080"), ("DATABASE_URL", "postgres://...")],
    "rust": [("RUST_ENV", "production"), ("PORT", "8080"), ("DATABASE_URL", "postgres://...")],
    "java": [("SPRING_PROFILES_ACTIVE", "prod"), ("PORT", "8080"), ("DATABASE_URL", "postgres://...")],
    "ruby": [("RAILS_ENV", "production"), ("PORT", "3000"), ("DATABASE_URL", "postgres://...")],
    "php": [("APP_ENV", "production"), ("PORT", "8000"), ("DATABASE_URL", "postgres://...")],
    "deno": [("DENO_ENV", "production"), ("PORT", "8000"), ("DATABASE_URL", "postgres://...")],
    "bun": [("BUN_ENV", "production"), ("PORT", "3000"), ("DATABASE_URL", "postgres://...")],
}

DOCKER_IGNORES: dict[str, list[str]] = {
    "node": ["node_modules", "npm-debug.log", "yarn-debug.log"],
    "python": ["__pycache__", "*.pyc", ".venv", "*.egg-info"],
    "go": [],
    "rust": ["target"],
    "java": [".gradle", "build", "*.jar", "*.war"],
    "ruby": ["vendor/bundle", ".bundle"],
    "php": ["vendor"],
    "deno": [],
    "bun": ["node_modules"],
}

GIT_IGNORES: dict[str, list[str]] = {
    "node": ["node_modules/", "npm-debug.log*", "yarn-debug.log*", "yarn-error.log*", ".env", ".env.local"],
    "python": ["__pycache__/", "*.py[cod]", ".venv/", "venv/", ".env", "*.egg-info/", "dist/"],
    "go": ["*.exe", "*.exe~", "*.test", "*.out", "vendor/"],
    "rust": ["target/", "**/*.rs.bk", "Cargo.lock"],
    "java": [".gradle/", "build/", "!gradle/wrapper/gradle-wrapper.jar", "*.jar", "*.war"],
    "ruby": ["vendor/bundle/", ".bundle/", "*.gem", ".env"],
    "php": ["vendor/", "*.log", ".env"],
    "deno": ["deno.lock", ".env"],
    "bun": ["node_modules/", ".env", ".env.local", "bun.lockb"],
}


def _get_ptype(project_type: str) -> str:
    return project_type if project_type in LANGUAGE_CONVENTIONS else "node"


def _generate_dockerfile(project_type: str, variables: dict[str, str] | None = None, **kwargs) -> str:
    pt = _get_ptype(project_type)
    c = LANGUAGE_CONVENTIONS[pt]
    port = (variables or {}).get("port", c["dev_port"])
    install = c["install_cmd"]
    build = c["build_cmd"]
    run = c["run_cmd"]
    health = c["healthcheck"]

    lines = [f"FROM {c['base_image']} AS builder", ""]
    lines.append("WORKDIR /app")
    lines.append("")
    lines.append(f"# Install dependencies")
    lines.append(f"RUN {install}")
    lines.append("")

    if build:
        lines.append(f"# Build the application")
        lines.append(f"RUN {build}")
        lines.append("")

    lines.append(f"FROM {c['base_image']} AS runner")
    lines.append("")
    lines.append("WORKDIR /app")
    lines.append("")
    lines.append(f"# Copy built artifacts")
    lines.append("COPY --from=builder /app /app")
    lines.append("")

    for env_name, env_val in ENV_VARS.get(pt, []):
        lines.append(f"ENV {env_name}={env_val}")

    lines.append("")
    lines.append(f"EXPOSE {port}")
    lines.append("")
    lines.append(f"HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\")
    lines.append(f"  {health}")
    lines.append("")
    lines.append(f"CMD [\"{run}\"]")
    lines.append("")

    return "\n".join(lines)


def _generate_docker_compose(project_type: str, variables: dict[str, str] | None = None, **kwargs) -> str:
    pt = _get_ptype(project_type)
    c = LANGUAGE_CONVENTIONS[pt]
    port = (variables or {}).get("port", c["dev_port"])
    service_name = (variables or {}).get("service_name", "app")

    lines = ["services:"]
    lines.append(f"  {service_name}:")
    lines.append(f"    build: .")
    lines.append("")
    lines.append(f"    ports:")
    lines.append(f'      - "{port}:{port}"')
    lines.append("")
    lines.append("    environment:")
    for env_name, env_val in ENV_VARS.get(pt, []):
        lines.append(f"      {env_name}: {env_val}")
    lines.append("")
    lines.append("    volumes:")
    lines.append("      - .:/app")
    lines.append("")
    lines.append("    develop:")
    lines.append("      watch:")
    lines.append("        - action: sync")
    lines.append("          path: .")
    lines.append("          target: /app")
    lines.append("          ignore:")
    lines.append("            - node_modules/")
    lines.append("        - action: rebuild")
    lines.append("          path: package.json")
    lines.append("")

    return "\n".join(lines)


def _generate_dockerignore(project_type: str, variables: dict[str, str] | None = None, **kwargs) -> str:
    pt = _get_ptype(project_type)
    ignores = DOCKER_IGNORES.get(pt, [])

    lines = [
        ".git",
        ".gitignore",
        "Dockerfile",
        "docker-compose.yml",
        "README.md",
        ".env",
        "__pycache__",
        "*.pyc",
        ".DS_Store",
    ]

    seen = set(lines)
    for item in ignores:
        if item not in seen:
            lines.append(item)
            seen.add(item)

    lines.append("")
    return "\n".join(lines)


def _generate_gitignore(project_type: str, variables: dict[str, str] | None = None, **kwargs) -> str:
    pt = _get_ptype(project_type)
    ignores = GIT_IGNORES.get(pt, [])

    lines = [
        "# OS files",
        ".DS_Store",
        "Thumbs.db",
        "",
        "# IDE",
        ".idea/",
        ".vscode/",
        "*.swp",
        "*.swo",
        "",
    ]

    if ignores:
        lines.append(f"# Project-specific")
        for item in ignores:
            lines.append(item)
        lines.append("")

    return "\n".join(lines)


def _generate_cursorrules(
    project_type: str,
    variables: dict[str, str] | None = None,
    insights=None,
    detection=None,
) -> str:
    pt = _get_ptype(project_type)
    conventions = ANTI_PATTERNS.get(pt, [])
    commands = COMMON_COMMANDS.get(pt, [])
    dev_port = LANGUAGE_CONVENTIONS[pt]["dev_port"]

    lines = ["You are an expert AI coding assistant specialized in this project.", ""]

    lines.append("# Project Overview")
    fw = detection.framework if detection and hasattr(detection, "framework") and detection.framework else None
    if fw:
        lines.append(f"This is a {fw} ({pt}) project.")
    else:
        lines.append(f"This is a {pt} project.")
    lines.append("")

    if insights:
        arch = getattr(insights, "architecture_pattern", None)
        if arch:
            lines.append(f"This project uses the **{arch}** architecture pattern.")
            lines.append("")

    lines.append("## Tech Stack")
    lines.append(f"- **Language**: {pt}")
    if fw:
        lines.append(f"- **Framework**: {fw}")
    if insights:
        if insights.state_management:
            lines.append(f"- **State Management**: {insights.state_management}")
        if insights.styling_approach:
            lines.append(f"- **Styling**: {insights.styling_approach}")
        if insights.orm:
            lines.append(f"- **Database/ORM**: {insights.orm}")
        if insights.test_runner:
            lines.append(f"- **Testing**: {insights.test_runner}")
        if insights.bundler:
            lines.append(f"- **Bundler**: {insights.bundler}")
        if insights.api_style:
            lines.append(f"- **API Style**: {insights.api_style}")
        if insights.auth_lib:
            lines.append(f"- **Auth**: {insights.auth_lib}")
        if insights.package_manager:
            lines.append(f"- **Package Manager**: {insights.package_manager}")
    lines.append("")

    if insights:
        im = getattr(insights, "import_style", None)
        ms = getattr(insights, "module_system", None)
        nc = getattr(insights, "naming_convention", None)
        if im and im != "unknown":
            lines.append(f"- **Import Style**: {im}")
        if ms and ms != "unknown":
            lines.append(f"- **Module System**: {ms}")
        if nc and nc != "unknown":
            lines.append(f"- **Naming Convention**: {nc}")
        if im or ms or (nc and nc != "unknown"):
            lines.append("")

    if insights and hasattr(insights, "directory_purposes") and insights.directory_purposes:
        lines.append("## Project Structure")
        for d, purpose in sorted(insights.directory_purposes.items()):
            colored = f"**`{d}/`** — {purpose}"
            lines.append(f"- {colored}")
        lines.append("")

    if insights and hasattr(insights, "api_route_paths") and insights.api_route_paths:
        lines.append("## API Routes")
        for route in sorted(insights.api_route_paths):
            lines.append(f"- `{route}`")
        lines.append("")

    lines.append("## Conventions")
    for c in conventions:
        lines.append(f"- {c}")
    lines.append("")

    lines.append("## Common Commands")
    for cmd in commands:
        lines.append(f"- `{cmd}`")
    lines.append("")

    lines.append("## Environment")
    for env_name, env_val in ENV_VARS.get(pt, []):
        lines.append(f"- `{env_name}`: {env_val}")
    lines.append("")

    lines.append(f"The application runs on port {dev_port}")
    lines.append("")

    return "\n".join(lines)


def _generate_claude_md(
    project_type: str,
    variables: dict[str, str] | None = None,
    insights=None,
    detection=None,
) -> str:
    pt = _get_ptype(project_type)
    conventions = ANTI_PATTERNS.get(pt, [])
    commands = COMMON_COMMANDS.get(pt, [])

    lines = ["# Project", ""]
    fw = detection.framework if detection and hasattr(detection, "framework") and detection.framework else None
    lines.append(f"This is a {fw if fw else pt} ({pt}) project.")
    lines.append("")

    if insights:
        arch = getattr(insights, "architecture_pattern", None)
        if arch:
            lines.append(f"Architecture: {arch}")
            lines.append("")

    lines.append("## Tech Stack")
    lines.append(f"- **Language**: {pt}")
    if fw:
        lines.append(f"- **Framework**: {fw}")
    if insights:
        if insights.state_management:
            lines.append(f"- **State Management**: {insights.state_management}")
        if insights.styling_approach:
            lines.append(f"- **Styling**: {insights.styling_approach}")
        if insights.orm:
            lines.append(f"- **ORM**: {insights.orm}")
        if insights.test_runner:
            lines.append(f"- **Test Runner**: {insights.test_runner}")
        if insights.bundler:
            lines.append(f"- **Bundler**: {insights.bundler}")
        if insights.api_style:
            lines.append(f"- **API Style**: {insights.api_style}")
        if insights.auth_lib:
            lines.append(f"- **Auth**: {insights.auth_lib}")
        if insights.package_manager:
            lines.append(f"- **Package Manager**: {insights.package_manager}")
    lines.append("")

    if insights and hasattr(insights, "directory_purposes") and insights.directory_purposes:
        lines.append("## Project Structure")
        for d, purpose in sorted(insights.directory_purposes.items()):
            lines.append(f"- `{d}/` — {purpose}")
        lines.append("")

    lines.append("## Conventions")
    for c in conventions:
        lines.append(f"- {c}")
    lines.append("")

    lines.append("## Commands")
    for cmd in commands:
        lines.append(f"- `{cmd}`")
    lines.append("")

    return "\n".join(lines)


def _generate_copilot_instructions(
    project_type: str,
    variables: dict[str, str] | None = None,
    insights=None,
    detection=None,
) -> str:
    pt = _get_ptype(project_type)
    conventions = ANTI_PATTERNS.get(pt, [])

    lines = ["# Project Context", ""]
    fw = detection.framework if detection and hasattr(detection, "framework") and detection.framework else None
    lines.append(f"Language: {pt}")
    if fw:
        lines.append(f"Framework: {fw}")
    if insights:
        if insights.state_management:
            lines.append(f"State Management: {insights.state_management}")
        if insights.orm:
            lines.append(f"ORM: {insights.orm}")
        if insights.test_runner:
            lines.append(f"Test: {insights.test_runner}")
        if insights.api_style:
            lines.append(f"API Style: {insights.api_style}")
        if insights.bundler:
            lines.append(f"Bundler: {insights.bundler}")
        if insights.styling_approach:
            lines.append(f"Styling: {insights.styling_approach}")
        if insights.package_manager:
            lines.append(f"Package Manager: {insights.package_manager}")
        im = getattr(insights, "import_style", None)
        nc = getattr(insights, "naming_convention", None)
        if im and im != "unknown":
            lines.append(f"Import Style: {im}")
        if nc and nc != "unknown":
            lines.append(f"Naming Convention: {nc}")

    lines.append("")
    lines.append("## Conventions")
    for c in conventions:
        lines.append(f"- {c}")
    lines.append("")

    return "\n".join(lines)


GENERATORS = {
    "Dockerfile": _generate_dockerfile,
    "docker-compose.yml": _generate_docker_compose,
    ".dockerignore": _generate_dockerignore,
    ".gitignore": _generate_gitignore,
    ".cursorrules": _generate_cursorrules,
    "CLAUDE.md": _generate_claude_md,
    ".github/copilot-instructions.md": _generate_copilot_instructions,
}

DOCKER_FILES = {"Dockerfile", "docker-compose.yml", ".dockerignore"}
AI_FILES = {".cursorrules", "CLAUDE.md", ".github/copilot-instructions.md"}


def generate_file_content(
    file_type: str,
    project_type: str,
    variables: dict[str, str] | None = None,
    insights=None,
    detection=None,
) -> str:
    generator = GENERATORS.get(file_type)
    if generator is None:
        msg = f"Unknown file type: {file_type}"
        raise ValueError(msg)

    kw = {"variables": variables, "insights": insights, "detection": detection}
    return generator(project_type, **kw)
