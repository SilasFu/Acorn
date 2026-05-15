from __future__ import annotations

from pathlib import Path

from acorn.analysis import ast_lite
from acorn.analysis.insights import ProjectInsights, analyze


def test_detect_import_style_relative(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.ts").write_text('import { bar } from "../bar"')
    result = ast_lite.detect_import_style(tmp_path)
    assert result == "relative"


def test_detect_import_style_path_alias(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.ts").write_text('import { Button } from "@/components/button"')
    result = ast_lite.detect_import_style(tmp_path)
    assert result == "path-alias"


def test_detect_import_style_empty(tmp_path):
    (tmp_path / "index.js").write_text("const x = 1")
    result = ast_lite.detect_import_style(tmp_path)
    assert result == "unknown"


def test_detect_module_system_esm(tmp_path):
    (tmp_path / "app.js").write_text("import express from 'express'\nconst app = express()")
    result = ast_lite.detect_module_system(tmp_path)
    assert result == "esm"


def test_detect_module_system_commonjs(tmp_path):
    (tmp_path / "app.js").write_text("const express = require('express')")
    result = ast_lite.detect_module_system(tmp_path)
    assert result == "commonjs"


def test_detect_module_system_package_json(tmp_path):
    (tmp_path / "app.js").write_text("const x = 1")
    (tmp_path / "package.json").write_text('{"type": "module"}')
    result = ast_lite.detect_module_system(tmp_path)
    assert result == "esm"


def test_detect_naming_convention_camelCase(tmp_path):
    (tmp_path / "myComponent.ts").write_text("const x = 1")
    (tmp_path / "useFoo.ts").write_text("const x = 1")
    result = ast_lite.detect_naming_convention(tmp_path)
    assert result == "camelCase"


def test_detect_naming_convention_kebab(tmp_path):
    (tmp_path / "my-component.ts").write_text("const x = 1")
    (tmp_path / "use-foo.ts").write_text("const x = 1")
    result = ast_lite.detect_naming_convention(tmp_path)
    assert result == "kebab-case"


def test_detect_state_management_zustand(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies": {"zustand": "^4.0.0"}}')
    result = ast_lite.detect_state_management(tmp_path)
    assert result == "Zustand"


def test_detect_state_management_redux(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies": {"@reduxjs/toolkit": "^2.0.0"}}')
    result = ast_lite.detect_state_management(tmp_path)
    assert result == "Redux Toolkit"


def test_detect_styling_tailwind(tmp_path):
    (tmp_path / "tailwind.config.js").write_text("module.exports = {}")
    result = ast_lite.detect_styling_approach(tmp_path)
    assert result == "tailwindcss"


def test_detect_styling_css_modules(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "style.module.css").write_text(".foo {}")
    result = ast_lite.detect_styling_approach(tmp_path)
    assert result == "css-modules"


def test_detect_api_style_trpc(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "router.ts").write_text("trpc stuff")
    (tmp_path / "package.json").write_text('{"dependencies": {"@trpc/server": "^10.0.0"}}')
    result = ast_lite.detect_api_style(tmp_path)
    assert result == "tRPC"


def test_detect_api_style_graphql(tmp_path):
    (tmp_path / "schema.graphql").write_text("type Query { hello: String }")
    result = ast_lite.detect_api_style(tmp_path)
    assert result == "GraphQL"


def test_detect_api_style_rest(tmp_path):
    route_file = tmp_path / "app" / "api" / "users" / "route.ts"
    route_file.parent.mkdir(parents=True)
    route_file.write_text("export function GET() {}")
    (tmp_path / "package.json").write_text('{"name": "test"}')
    result = ast_lite.detect_api_style(tmp_path)
    assert result == "REST (file-based)"


def test_detect_architecture_app_router(tmp_path):
    (tmp_path / "app").mkdir()
    result = ast_lite.detect_architecture_pattern(tmp_path, "node")
    assert result == "app-router"


def test_detect_architecture_monorepo(tmp_path):
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - apps/*")
    result = ast_lite.detect_architecture_pattern(tmp_path, "node")
    assert result == "monorepo"


def test_detect_directory_purpose(tmp_path):
    structure = {
        "components": ["Button.tsx"],
        "lib": ["utils.ts"],
        "pages": ["index.tsx"],
    }
    result = ast_lite.detect_directory_purpose(structure, "node")
    assert result["components"] == "Reusable React components"
    assert result["lib"] == "Utility functions and shared logic"


def test_insights_new_fields(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"next": "^14.0.0", "zustand": "^4.0.0", "tailwindcss": "^3.0.0", "vitest": "^1.0.0", "prisma": "^5.0.0", "@trpc/server": "^10.0.0"}}'
    )
    route_file = tmp_path / "app" / "api" / "users" / "route.ts"
    route_file.parent.mkdir(parents=True)
    route_file.write_text("import prisma from '@/lib/prisma'")
    src_comp = tmp_path / "src" / "components"
    src_comp.mkdir(parents=True)
    (src_comp / "Button.tsx").write_text("export const Button = () => null")
    src_lib = tmp_path / "src" / "lib"
    src_lib.mkdir()
    (src_lib / "utils.ts").write_text("export const x = 1")
    result = analyze(tmp_path)
    assert result.language == "node"
    assert result.framework == "Next.js"
    assert result.state_management == "Zustand"
    assert result.test_runner == "vitest"
    assert result.orm == "prisma"
    assert result.api_style is not None
    assert result.architecture_pattern is not None
    assert result.directory_purposes
