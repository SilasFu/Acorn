from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from acorn.detector import (
    _check_content_recursive,
    _check_dependencies,
    _check_patterns,
    _detect_by_manifest,
    _detect_port,
    _find_entry_files,
    _find_files_recursive,
    _has_files,
    _read_file_safe,
    detect_mixed_project,
    detect_project_type,
    evaluate_rule,
    evaluate_template_match,
)
from acorn.models import DetectorCondition, DetectorRule, ProjectType, Template


def test_read_file_safe(tmp_path: Path):
    f = tmp_path / "test.txt"
    f.write_text("hello")
    assert _read_file_safe(f) == "hello"
    assert _read_file_safe(tmp_path / "nonexistent") is None


def test_has_files(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}")
    assert _has_files(tmp_path, ["package.json"]) is True
    assert _has_files(tmp_path, ["nonexistent"]) is False


def test_check_content_recursive(tmp_path: Path):
    f = tmp_path / "app.js"
    f.write_text("const express = require('express')")
    assert _check_content_recursive(tmp_path, ["express"]) == 1
    assert _check_content_recursive(tmp_path, ["nonexistent"]) == 0


def test_check_dependencies(tmp_path: Path):
    f = tmp_path / "package.json"
    f.write_text('{"dependencies": {"express": "^4.0.0"}}')
    assert _check_dependencies(tmp_path, ["express"]) is True
    assert _check_dependencies(tmp_path, ["nonexistent"]) is False


def test_check_patterns(tmp_path: Path):
    (tmp_path / "app.js").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "test.js").write_text("")
    assert _check_patterns(tmp_path, ["*.js"]) >= 1
    assert _check_patterns(tmp_path, ["*.rs"]) == 0


def test_detect_by_manifest(tmp_path: Path):
    assert _detect_by_manifest(tmp_path) is None
    (tmp_path / "package.json").write_text("{}")
    assert _detect_by_manifest(tmp_path) == ProjectType.NODE
    (tmp_path / "Cargo.toml").write_text("")
    assert _detect_by_manifest(tmp_path) == ProjectType.NODE


def test_detect_by_manifest_java(tmp_path: Path):
    (tmp_path / "pom.xml").write_text("<project/>")
    assert _detect_by_manifest(tmp_path) == ProjectType.JAVA


def test_detect_by_manifest_ruby(tmp_path: Path):
    (tmp_path / "Gemfile").write_text("")
    assert _detect_by_manifest(tmp_path) == ProjectType.RUBY


def test_detect_by_manifest_php(tmp_path: Path):
    (tmp_path / "composer.json").write_text("{}")
    assert _detect_by_manifest(tmp_path) == ProjectType.PHP


def test_detect_by_manifest_deno(tmp_path: Path):
    (tmp_path / "deno.json").write_text("{}")
    assert _detect_by_manifest(tmp_path) == ProjectType.DENO


def test_detect_by_manifest_bun(tmp_path: Path):
    (tmp_path / "bun.lockb").write_text("")
    assert _detect_by_manifest(tmp_path) == ProjectType.BUN


def test_evaluate_rule(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"dependencies": {"express": "^4.0.0"}}')
    rule = DetectorRule(
        name="node",
        type=ProjectType.NODE,
        priority=10,
        conditions=DetectorCondition(
            files=["package.json"],
            content=["express"],
            dependencies=["express"],
        ),
    )
    score = evaluate_rule(rule, tmp_path)
    assert score > 0.5


def test_evaluate_rule_no_match(tmp_path: Path):
    rule = DetectorRule(
        name="rust",
        type=ProjectType.RUST,
        conditions=DetectorCondition(files=["Cargo.toml"]),
    )
    score = evaluate_rule(rule, tmp_path)
    assert score == 0.0


def test_evaluate_template_match(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}")
    t = Template(
        name="node-api",
        project_type=ProjectType.NODE,
        detectors=DetectorCondition(files=["package.json"], keywords=["express"]),
    )
    score = evaluate_template_match(t, tmp_path)
    assert score > 0


def test_evaluate_template_match_no_match(tmp_path: Path):
    t = Template(
        name="python",
        detectors=DetectorCondition(files=["requirements.txt"]),
    )
    score = evaluate_template_match(t, tmp_path)
    assert score == 0.0


def test_detect_project_type_node(tmp_path: Path):
    (tmp_path / "package.json").write_text(
        '{"name":"test","dependencies":{"express":"^4.0.0"}}'
    )
    result = detect_project_type(tmp_path)
    assert result.project_type == ProjectType.NODE
    assert result.confidence > 0


def test_detect_project_type_empty(tmp_path: Path):
    result = detect_project_type(tmp_path)
    assert result.project_type in (ProjectType.UNKNOWN, ProjectType.NODE)


def test_detect_project_type_invalid_path():
    result = detect_project_type("/nonexistent/path")
    assert result.project_type == ProjectType.UNKNOWN
    assert "error" in result.details


def test_detect_project_type_java(tmp_path: Path):
    (tmp_path / "pom.xml").write_text("<project><dependencies/></project>")
    (tmp_path / "App.java").write_text("class App {}")
    result = detect_project_type(tmp_path)
    assert result.project_type == ProjectType.JAVA


def test_detect_project_type_ruby(tmp_path: Path):
    (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'")
    result = detect_project_type(tmp_path)
    assert result.project_type == ProjectType.RUBY


def test_detect_project_type_php(tmp_path: Path):
    (tmp_path / "composer.json").write_text('{"require": {"laravel/framework": "^10.0"}}')
    result = detect_project_type(tmp_path)
    assert result.project_type == ProjectType.PHP


def test_find_entry_files_node(tmp_path: Path):
    (tmp_path / "index.js").write_text("")
    entries = _find_entry_files(tmp_path)
    assert any(e[0] == "index.js" for e in entries)


def test_find_entry_files_python(tmp_path: Path):
    (tmp_path / "main.py").write_text("")
    entries = _find_entry_files(tmp_path)
    assert any(e[0] == "main.py" for e in entries)


def test_find_entry_files_empty(tmp_path: Path):
    entries = _find_entry_files(tmp_path)
    assert entries == []


def test_detect_port_node(tmp_path: Path):
    (tmp_path / "server.js").write_text("const port = 3456; app.listen(port)")
    port = _detect_port(tmp_path, ProjectType.NODE)
    assert port == "3456"


def test_detect_port_node_listen(tmp_path: Path):
    (tmp_path / "app.js").write_text("app.listen(8080)")
    port = _detect_port(tmp_path, ProjectType.NODE)
    assert port == "8080"


def test_detect_port_python(tmp_path: Path):
    (tmp_path / "app.py").write_text("port = 8000")
    port = _detect_port(tmp_path, ProjectType.PYTHON)
    assert port == "8000"


def test_detect_port_no_match(tmp_path: Path):
    (tmp_path / "main.js").write_text("console.log('hello')")
    port = _detect_port(tmp_path, ProjectType.NODE)
    assert port is None


def test_detect_mixed_project(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "requirements.txt").write_text("")
    matches = detect_mixed_project(tmp_path)
    assert len(matches) >= 2


def test_detection_result_has_all_matches(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}")
    result = detect_project_type(tmp_path)
    assert hasattr(result, "all_matches")


def test_detection_result_has_entry_files(tmp_path: Path):
    (tmp_path / "index.js").write_text("")
    (tmp_path / "package.json").write_text("{}")
    result = detect_project_type(tmp_path)
    assert "entry_files" in result.details


def test_read_file_safe_oserror(tmp_path: Path):
    f = tmp_path / "locked.txt"
    f.write_text("data")
    f.chmod(0o000)
    content = _read_file_safe(f)
    assert content is None
    f.chmod(0o644)


def test_find_files_recursive_ignores_dirs(tmp_path: Path):
    (tmp_path / ".git").mkdir(parents=True)
    (tmp_path / ".git" / "config").write_text("")
    (tmp_path / "src").mkdir(parents=True)
    (tmp_path / "src" / "app.js").write_text("")
    files = _find_files_recursive(tmp_path, ["*.js"])
    assert len(files) == 1
    assert ".git" not in str(files[0])


def test_check_content_recursive_ignores_dirs(tmp_path: Path):
    (tmp_path / ".git").mkdir(parents=True)
    (tmp_path / ".git" / "secret").write_text("password=xyz")
    (tmp_path / "app.py").write_text("password=abc")
    count = _check_content_recursive(tmp_path, ["password"])
    assert count == 1


def test_check_dependencies_all_match(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"dependencies": {"express": "^4.0.0", "lodash": "^1.0.0"}}')
    assert _check_dependencies(tmp_path, ["express", "lodash"]) is True


def test_check_dependencies_no_manifest(tmp_path: Path):
    assert _check_dependencies(tmp_path, ["express"]) is False


def test_check_patterns_empty(tmp_path: Path):
    assert _check_patterns(tmp_path, []) == 0


def test_detect_by_manifest_go(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module test")
    assert _detect_by_manifest(tmp_path) == ProjectType.GO


def test_detect_by_manifest_rust(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text("[package]")
    assert _detect_by_manifest(tmp_path) == ProjectType.RUST


def test_find_entry_files_glob(tmp_path: Path):
    (tmp_path / "cmd" / "server").mkdir(parents=True)
    (tmp_path / "cmd" / "server" / "main.go").write_text("")
    entries = _find_entry_files(tmp_path)
    go_pattern = ("cmd/server/main.go", ProjectType.GO)
    assert go_pattern in entries


def test_detect_port_python_no_match(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('hello')")
    port = _detect_port(tmp_path, ProjectType.PYTHON)
    assert port is None


def test_detect_port_node_listen_direct(tmp_path: Path):
    (tmp_path / "server.ts").write_text("http.listen(4000)")
    port = _detect_port(tmp_path, ProjectType.NODE)
    assert port == "4000"


def test_evaluate_rule_with_patterns(tmp_path: Path):
    (tmp_path / "main.go").write_text("")
    rule = DetectorRule(
        name="go",
        type=ProjectType.GO,
        conditions=DetectorCondition(patterns=["*.go"]),
    )
    score = evaluate_rule(rule, tmp_path)
    assert score > 0


def test_evaluate_rule_with_deps(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("fastapi\nuvicorn\n")
    rule = DetectorRule(
        name="python",
        type=ProjectType.PYTHON,
        conditions=DetectorCondition(dependencies=["fastapi"]),
    )
    score = evaluate_rule(rule, tmp_path)
    assert score > 0


def test_evaluate_rule_with_content(tmp_path: Path):
    (tmp_path / "app.py").write_text("from fastapi import FastAPI\n")
    rule = DetectorRule(
        name="python",
        type=ProjectType.PYTHON,
        conditions=DetectorCondition(content=["fastapi"]),
    )
    score = evaluate_rule(rule, tmp_path)
    assert score > 0


def test_evaluate_rule_empty_conditions():
    rule = DetectorRule(name="empty", type=ProjectType.UNKNOWN, conditions=DetectorCondition())
    score = evaluate_rule(rule, Path("/tmp"))
    assert score == 0.0


def test_evaluate_template_match_with_keywords(tmp_path: Path):
    (tmp_path / "app.py").write_text("import fastapi\n")
    t = Template(
        name="fastapi",
        project_type=ProjectType.PYTHON,
        detectors=DetectorCondition(keywords=["fastapi"]),
    )
    score = evaluate_template_match(t, tmp_path)
    assert score > 0


def test_evaluate_template_match_keywords_no_match(tmp_path: Path):
    t = Template(
        name="fastapi",
        project_type=ProjectType.PYTHON,
        detectors=DetectorCondition(keywords=["django"]),
    )
    score = evaluate_template_match(t, tmp_path)
    assert score == 0.0


def test_detect_project_type_go(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module test\n")
    (tmp_path / "main.go").write_text("package main\n")
    result = detect_project_type(tmp_path)
    assert result.project_type == ProjectType.GO


def test_detect_project_type_string_path(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}")
    result = detect_project_type(str(tmp_path))
    assert result.project_type == ProjectType.NODE


def test_detect_project_type_with_detected_port(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "server.js").write_text("app.listen(9999)")
    result = detect_project_type(tmp_path)
    assert "detected_port" in result.details
    assert result.details["detected_port"] == "9999"


def test_detect_project_type_unknown_no_port(tmp_path: Path):
    result = detect_project_type(tmp_path)
    assert "detected_port" not in result.details


def test_find_files_recursive_skips_ignored_dirs(tmp_path: Path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / ".git" / "hooks" / "post-commit.js").touch()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.js").touch()
    files = _find_files_recursive(tmp_path, ["*.js"])
    assert len(files) == 1
    assert ".git" not in str(files[0])


def test_find_entry_files_glob_star_star(tmp_path: Path):
    (tmp_path / "src" / "main" / "java" / "com" / "app").mkdir(parents=True)
    (tmp_path / "src" / "main" / "java" / "com" / "app" / "Application.java").write_text("")
    entries = _find_entry_files(tmp_path)
    assert any("Application.java" in e[0] for e in entries)


def test_detect_port_python_empty_file(tmp_path: Path):
    (tmp_path / "app.py").write_text("")
    port = _detect_port(tmp_path, ProjectType.PYTHON)
    assert port is None


def test_detect_project_type_with_framework_indicator(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"dependencies": {"express": "^4.0.0"}}')
    (tmp_path / "index.js").write_text("const express = require('express')")
    result = detect_project_type(tmp_path)
    assert result.framework == "express"


def test_detect_mixed_project_string_path(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "requirements.txt").write_text("")
    matches = detect_mixed_project(str(tmp_path))
    assert len(matches) >= 2


def test_check_indicator_dependency_found(tmp_path: Path):
    from acorn.detector import _check_indicator
    (tmp_path / "package.json").write_text('{"dependencies": {"express": "^4.0.0"}}')
    assert _check_indicator("dependencies.express in package.json", tmp_path)


def test_check_indicator_dependency_not_found(tmp_path: Path):
    from acorn.detector import _check_indicator
    (tmp_path / "package.json").write_text('{"dependencies": {"koa": "^2.0.0"}}')
    assert not _check_indicator("dependencies.express in package.json", tmp_path)


def test_check_indicator_invalid_package_json(tmp_path: Path):
    from acorn.detector import _check_indicator
    (tmp_path / "package.json").write_text("not valid json")
    assert not _check_indicator("dependencies.express in package.json", tmp_path)


def test_check_indicator_non_dict_package_json(tmp_path: Path):
    from acorn.detector import _check_indicator
    (tmp_path / "package.json").write_text('["not a dict"]')
    assert not _check_indicator("dependencies.express in package.json", tmp_path)


def test_check_indicator_no_package_json(tmp_path: Path):
    from acorn.detector import _check_indicator
    assert not _check_indicator("dependencies.express in package.json", tmp_path)


def test_check_indicator_dot_path_not_found(tmp_path: Path):
    from acorn.detector import _check_indicator
    (tmp_path / "config.json").write_text('{"key": "value"}')
    assert not _check_indicator("'missing' in config.json", tmp_path)


def test_check_indicator_unknown_format(tmp_path: Path):
    from acorn.detector import _check_indicator
    assert not _check_indicator("just_a_file", tmp_path)


def test_check_indicator_file_not_found(tmp_path: Path):
    from acorn.detector import _check_indicator
    assert not _check_indicator("nonexistent.file", tmp_path)


def test_detect_project_type_entry_files_only(tmp_path: Path):
    (tmp_path / "index.js").write_text("")
    result = detect_project_type(tmp_path)
    assert len(result.details.get("entry_files", [])) > 0


def test_detect_project_type_dir_in_iterdir(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "node_modules").mkdir()
    result = detect_project_type(tmp_path)
    assert "files_found" in result.details
    assert "package.json" in result.details["files_found"]


def test_detect_project_type_manifest_fallback(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text("[package]\nname = \"test\"")
    result = detect_project_type(tmp_path)
    assert result.project_type == ProjectType.RUST


def test_detect_project_type_manifest_fallback_unknown(tmp_path: Path):
    (tmp_path / "unknown.txt").write_text("data")
    result = detect_project_type(tmp_path)
    assert result.project_type in (ProjectType.UNKNOWN,)


def test_detect_entry_files_sets_type_when_rules_miss(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "manage.py").write_text("from django.conf import settings\n")
    from acorn.detector import detect_project_type
    with patch("acorn.detector.load_detector_rules", return_value=[]):
        with patch("acorn.detector.load_templates", return_value=[]):
            result = detect_project_type(src)
    assert result.project_type == ProjectType.PYTHON
    assert result.confidence == 0.25


def test_detect_entry_files_no_override_when_manifest_higher(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "Cargo.toml").write_text("[package]\nname = \"test\"\n")
    (src / "manage.py").write_text("")
    with patch("acorn.detector.load_detector_rules", return_value=[]):
        with patch("acorn.detector.load_templates", return_value=[]):
            result = detect_project_type(src)
    assert result.project_type == ProjectType.RUST


def test_check_indicator_yaml_exception(tmp_path):
    from acorn.detector import _check_indicator
    (tmp_path / "package.json").write_text("{invalid: yaml content!!!\n")
    (tmp_path / "server.js").write_text("console.log('hi')")
    result = _check_indicator("dependencies.express in package.json", tmp_path)
    assert result is False


def test_check_indicator_no_dot_in_right(tmp_path):
    from acorn.detector import _check_indicator
    (tmp_path / "somefile").write_text("content")
    result = _check_indicator("keyword in somefile", tmp_path)
    assert result is False


def test_check_indicator_equals_op(tmp_path):
    from acorn.detector import _check_indicator
    result = _check_indicator("version == 1.0 && name contains test", tmp_path)
    assert result is True


def test_check_indicator_multiple_file_exists(tmp_path):
    from acorn.detector import _check_indicator
    (tmp_path / "f1.txt").write_text("a")
    (tmp_path / "f2.txt").write_text("b")
    result = _check_indicator("f1.txt && f2.txt", tmp_path)
    assert result is True


def test_check_indicator_file_not_exists(tmp_path):
    from acorn.detector import _check_indicator
    result = _check_indicator("nonexistent.file", tmp_path)
    assert result is False
