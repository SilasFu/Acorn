from __future__ import annotations

from pathlib import Path

from acorn.models import (
    DetectionResult,
    DetectorCondition,
    DetectorRule,
    GenerationOptions,
    Hooks,
    ProjectType,
    Template,
    TemplateVariable,
)


def test_project_type_values():
    assert ProjectType.NODE.value == "node"
    assert ProjectType.PYTHON.value == "python"
    assert ProjectType.GO.value == "go"
    assert ProjectType.RUST.value == "rust"
    assert ProjectType.JAVA.value == "java"
    assert ProjectType.UNKNOWN.value == "unknown"


def test_detector_condition_defaults():
    dc = DetectorCondition()
    assert dc.files == []
    assert dc.content == []
    assert dc.keywords == []
    assert dc.dependencies == []
    assert dc.patterns == []


def test_detector_rule_from_dict():
    data = {
        "name": "node-test",
        "type": "node",
        "priority": 10,
        "conditions": {
            "files": ["package.json"],
            "content": ["express"],
            "dependencies": ["express"],
            "patterns": ["*.js"],
        },
        "indicators": {
            "express": "dependencies.express in package.json",
        },
    }
    rule = DetectorRule.from_dict(data)
    assert rule.name == "node-test"
    assert rule.type == ProjectType.NODE
    assert rule.priority == 10
    assert rule.conditions.files == ["package.json"]
    assert len(rule.indicators) == 1
    assert rule.indicators[0].name == "express"


def test_template_from_dict():
    data = {
        "name": "test-template",
        "description": "A test",
        "version": "2.0.0",
        "type": "python",
        "detectors": {"files": ["requirements.txt"], "keywords": ["fastapi"]},
        "variables": [{"name": "port", "default": "8000"}],
        "extends": "base",
        "files": ["Dockerfile", ".env"],
    }
    t = Template.from_dict(data, path=Path("/tmp/tpl"))
    assert t.name == "test-template"
    assert t.description == "A test"
    assert t.version == "2.0.0"
    assert t.project_type == ProjectType.PYTHON
    assert t.extends == "base"
    assert len(t.files) == 2
    assert len(t.variables) == 1
    assert t.variables[0].name == "port"
    assert t.variables[0].default == "8000"


def test_template_to_dict():
    t = Template(
        name="mytpl",
        description="desc",
        version="1.0.0",
        project_type=ProjectType.NODE,
        files=["Dockerfile"],
        variables=[TemplateVariable(name="port", default="3000")],
    )
    d = t.to_dict()
    assert d["name"] == "mytpl"
    assert d["type"] == "node"
    assert d["files"] == ["Dockerfile"]
    assert d["variables"][0]["name"] == "port"


def test_detection_result_defaults():
    r = DetectionResult()
    assert r.project_type == ProjectType.UNKNOWN
    assert r.framework is None
    assert r.matched_template is None
    assert r.confidence == 0.0
    assert r.details == {}


def test_generation_options_defaults():
    o = GenerationOptions()
    assert o.force is False
    assert o.dry_run is False
    assert o.interactive is False
    assert o.template_name is None
    assert o.save is False
    assert o.init is False
    assert o.regenerate is False
    assert o.verbose is False
    assert o.debug is False
    assert o.quiet is False
    assert o.offline is False
    assert o.lang is None
    assert o.search is None
    assert o.install is None
    assert o.variables == {}


def test_template_variable_defaults():
    v = TemplateVariable(name="port")
    assert v.default == ""
    assert v.description == ""
    assert v.prompt == ""
    assert v.options == []


def test_template_variable_with_options():
    v = TemplateVariable(name="pkg", default="npm", options=["npm", "yarn", "pnpm"])
    assert v.options == ["npm", "yarn", "pnpm"]


def test_template_from_dict_with_hooks():
    data = {
        "name": "with-hooks",
        "type": "node",
        "hooks": {
            "before_generate": "echo start",
            "after_generate": "echo done",
        },
        "files": ["Dockerfile"],
    }
    t = Template.from_dict(data)
    assert t.hooks.before_generate == "echo start"
    assert t.hooks.after_generate == "echo done"


def test_template_from_dict_with_min_tool_version():
    data = {
        "name": "versioned",
        "type": "node",
        "min_tool_version": "0.2.0",
        "files": [],
    }
    t = Template.from_dict(data)
    assert t.min_tool_version == "0.2.0"


def test_template_from_dict_with_variable_options():
    data = {
        "name": "options-test",
        "type": "node",
        "variables": [
            {"name": "pkg", "default": "npm", "options": ["npm", "yarn", "pnpm"]},
        ],
        "files": [],
    }
    t = Template.from_dict(data)
    assert t.variables[0].options == ["npm", "yarn", "pnpm"]


def test_hooks_defaults():
    h = Hooks()
    assert h.before_generate is None
    assert h.after_generate is None
    assert h.before_detect is None
    assert h.after_detect is None


def test_detection_result_all_matches():
    r = DetectionResult()
    assert r.all_matches == []


def test_generation_options_regenerate():
    o = GenerationOptions(regenerate=True)
    assert o.regenerate is True


def test_project_type_new_values():
    assert ProjectType.RUBY.value == "ruby"
    assert ProjectType.PHP.value == "php"
    assert ProjectType.DENO.value == "deno"
    assert ProjectType.BUN.value == "bun"


def test_template_locked_variables():
    t = Template(
        name="locked",
        project_type=ProjectType.NODE,
        locked_variables={"port": "8080"},
    )
    assert t.locked_variables["port"] == "8080"
