from __future__ import annotations

from acorn.generators.builtin import (
    AI_FILES,
    DOCKER_FILES,
    LANGUAGE_CONVENTIONS,
    generate_file_content,
)


def test_dockerfile_all_languages():
    for lang in LANGUAGE_CONVENTIONS:
        content = generate_file_content("Dockerfile", lang)
        assert "FROM" in content
        assert "WORKDIR /app" in content
        assert "EXPOSE" in content or "HEALTHCHECK" in content


def test_dockerfile_multi_stage():
    content = generate_file_content("Dockerfile", "go")
    assert "AS builder" in content
    assert "AS runner" in content


def test_dockerfile_python_has_pip():
    content = generate_file_content("Dockerfile", "python")
    assert "pip install" in content


def test_dockerfile_rust_release_build():
    content = generate_file_content("Dockerfile", "rust")
    assert "--release" in content


def test_docker_compose_no_version():
    for lang in ("node", "python", "go"):
        content = generate_file_content("docker-compose.yml", lang)
        assert "version:" not in content
        assert "services:" in content


def test_docker_compose_has_watch():
    content = generate_file_content("docker-compose.yml", "node")
    assert "watch:" in content
    assert "action: sync" in content


def test_docker_compose_port():
    content = generate_file_content("docker-compose.yml", "node", {"port": "9999"})
    assert "9999:9999" in content


def test_dockerignore_common_items():
    content = generate_file_content(".dockerignore", "node")
    assert ".git" in content
    assert "Dockerfile" in content
    assert "node_modules" in content


def test_dockerignore_python():
    content = generate_file_content(".dockerignore", "python")
    assert "__pycache__" in content


def test_gitignore_node():
    content = generate_file_content(".gitignore", "node")
    assert "node_modules/" in content
    assert ".env" in content


def test_gitignore_python():
    content = generate_file_content(".gitignore", "python")
    assert "__pycache__" in content


def test_gitignore_go():
    content = generate_file_content(".gitignore", "go")
    assert "*.exe" in content


def test_cursorrules_has_sections():
    content = generate_file_content(".cursorrules", "node")
    assert "## Tech Stack" in content
    assert "## Conventions" in content
    assert "## Common Commands" in content


def test_cursorrules_with_insights_has_rich_content():
    class FakeInsights:
        orm = "prisma"
        test_runner = "vitest"
        bundler = "vite"
        state_management = "Zustand"
        styling_approach = "tailwindcss"
        api_style = "REST"
        auth_lib = "next-auth"
        package_manager = "pnpm"
        import_style = "path-alias"
        module_system = "esm"
        naming_convention = "camelCase"
        architecture_pattern = "app-router"
        api_route_paths = ["/api/users", "/api/posts"]
        directory_purposes = {
            "components": "Reusable React components",
            "lib": "Utility functions",
            "app": "Route handlers and pages",
        }
        src_structure = {}

    class FakeDetection:
        project_type = type("pt", (), {"value": "node"})()
        framework = "Next.js"
        matched_template = "node-api"
        confidence = 0.95

    content = generate_file_content(".cursorrules", "node", insights=FakeInsights(), detection=FakeDetection())
    assert "Zustand" in content
    assert "tailwindcss" in content
    assert "app-router" in content
    assert "path-alias" in content
    assert "## Project Structure" in content
    assert "## API Routes" in content
    assert "/api/users" in content
    assert "Reusable React components" in content


def test_claude_md_has_sections():
    content = generate_file_content("CLAUDE.md", "python")
    assert "# Project" in content
    assert "## Tech Stack" in content
    assert "## Conventions" in content


def test_claude_md_with_insights():
    class FakeInsights:
        orm = "sqlalchemy"
        test_runner = "pytest"
        bundler = None
        state_management = None
        styling_approach = None
        api_style = None
        auth_lib = None
        package_manager = "pip"
        import_style = "unknown"
        module_system = "unknown"
        naming_convention = "snake_case"
        architecture_pattern = None
        api_route_paths = []
        directory_purposes = {"api": "API route handlers", "models": "Data models"}
        src_structure = {}

    class FakeDetection:
        project_type = type("pt", (), {"value": "python"})()
        framework = "FastAPI"
        matched_template = "python-fastapi"
        confidence = 0.95

    content = generate_file_content("CLAUDE.md", "python", insights=FakeInsights(), detection=FakeDetection())
    assert "Project Structure" in content
    assert "API route handlers" in content


def test_copilot_instructions():
    content = generate_file_content(".github/copilot-instructions.md", "go")
    assert "# Project Context" in content
    assert "Language:" in content


def test_copilot_instructions_with_insights():
    class FakeInsights:
        orm = "prisma"
        test_runner = "vitest"
        bundler = "vite"
        state_management = "Zustand"
        styling_approach = "tailwindcss"
        api_style = "tRPC"
        auth_lib = "next-auth"
        package_manager = "pnpm"
        import_style = "path-alias"
        module_system = "esm"
        naming_convention = "camelCase"
        architecture_pattern = None
        api_route_paths = []
        directory_purposes = {}
        src_structure = {}

    class FakeDetection:
        project_type = type("pt", (), {"value": "node"})()
        framework = "Next.js"
        matched_template = "node-api"
        confidence = 0.95

    content = generate_file_content(".github/copilot-instructions.md", "node", insights=FakeInsights(), detection=FakeDetection())
    assert "tRPC" in content
    assert "path-alias" in content
    assert "camelCase" in content
    assert "Import Style:" in content


def test_unknown_file_type_raises():
    try:
        generate_file_content("nonexistent", "node")
        assert False
    except ValueError:
        pass


def test_docker_files_set():
    assert "Dockerfile" in DOCKER_FILES
    assert "docker-compose.yml" in DOCKER_FILES
    assert ".dockerignore" in DOCKER_FILES
    assert len(DOCKER_FILES) == 3


def test_ai_files_set():
    assert ".cursorrules" in AI_FILES
    assert "CLAUDE.md" in AI_FILES
    assert ".github/copilot-instructions.md" in AI_FILES
    assert len(AI_FILES) == 3


def test_language_conventions_all_have_keys():
    required = {"base_image", "run_cmd", "dev_port", "install_cmd", "healthcheck"}
    for lang, cfg in LANGUAGE_CONVENTIONS.items():
        missing = required - set(cfg.keys())
        assert not missing, f"{lang} missing: {missing}"


def test_generate_file_content_with_detection():
    class FakeDetection:
        project_type = type("pt", (), {"value": "node"})()
        framework = "Express"
        matched_template = "node-api"
        confidence = 0.95

    content = generate_file_content(".cursorrules", "node", detection=FakeDetection())
    assert "Express" in content


def test_generate_file_content_with_insights():
    class FakeInsights:
        orm = "prisma"
        test_runner = "vitest"
        bundler = "vite"
        state_management = None
        styling_approach = None
        api_style = None
        auth_lib = None
        package_manager = "pnpm"
        import_style = "path-alias"
        module_system = "esm"
        naming_convention = "camelCase"
        architecture_pattern = None
        api_route_paths = []
        directory_purposes = {}
        src_structure = {}

    content = generate_file_content(".cursorrules", "node", insights=FakeInsights())
    assert "prisma" in content
    assert "vitest" in content
