from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from acorn.config import (
    PROJECT_CONFIG_DIR,
    export_config,
    import_config,
    init_project_config,
    load_config,
    load_detector_rules,
    load_project_config,
    load_project_lock,
    load_templates,
    resolve_template,
    save_config,
    save_project_lock,
    save_template_to_global,
)
from acorn.models import DetectorCondition, ProjectType, Template, TemplateVariable


def test_init_project_config(tmp_path: Path):
    result = init_project_config(tmp_path, template_name="node-api", dry_run=False)
    assert result is not None
    assert result["template"] == "node-api"
    config_file = tmp_path / PROJECT_CONFIG_DIR / "config.yaml"
    assert config_file.exists()


def test_init_project_config_dry_run(tmp_path: Path):
    result = init_project_config(tmp_path, template_name="test", dry_run=True)
    assert result is not None
    config_file = tmp_path / PROJECT_CONFIG_DIR / "config.yaml"
    assert not config_file.exists()


def test_init_project_config_already_exists(tmp_path: Path):
    (tmp_path / PROJECT_CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    (tmp_path / PROJECT_CONFIG_DIR / "config.yaml").write_text("key: val\n")
    result = init_project_config(tmp_path, template_name="test")
    assert result is None


def test_load_project_config(tmp_path: Path):
    config_dir = tmp_path / PROJECT_CONFIG_DIR
    config_dir.mkdir(parents=True)
    (config_dir / "config.yaml").write_text("template: node-api\n")
    config = load_project_config(tmp_path)
    assert config["template"] == "node-api"


def test_load_project_config_not_exists(tmp_path: Path):
    config = load_project_config(tmp_path)
    assert config == {}


def test_resolve_template_no_extends():
    t = Template(name="base", project_type=ProjectType.NODE, files=["Dockerfile"])
    resolved = resolve_template(t)
    assert resolved.name == "base"
    assert resolved.files == ["Dockerfile"]


def test_resolve_template_with_extends():
    parent = Template(
        name="base",
        project_type=ProjectType.NODE,
        files=["Dockerfile", ".env"],
        variables=[],
    )
    child = Template(
        name="child",
        extends="base",
        project_type=ProjectType.UNKNOWN,
        files=[],
    )

    with patch("acorn.config.find_template_by_name", return_value=parent):
        resolved = resolve_template(child)
        assert resolved.name == "child"
        assert resolved.project_type == ProjectType.NODE
        assert resolved.files == ["Dockerfile", ".env"]


def test_resolve_template_keeps_child_files():
    parent = Template(
        name="base",
        project_type=ProjectType.NODE,
        files=["Dockerfile", ".env"],
    )
    child = Template(
        name="child",
        extends="base",
        project_type=ProjectType.PYTHON,
        files=["Dockerfile"],
    )

    with patch("acorn.config.find_template_by_name", return_value=parent):
        resolved = resolve_template(child)
        assert resolved.project_type == ProjectType.PYTHON
        assert resolved.files == ["Dockerfile"]


def test_resolve_template_without_extends():
    t = Template(name="alone", project_type=ProjectType.GO, files=["main.go"])
    resolved = resolve_template(t)
    assert resolved.name == "alone"
    assert resolved.project_type == ProjectType.GO


def test_resolve_template_parent_not_found():
    child = Template(name="orphan", extends="nonexistent", project_type=ProjectType.UNKNOWN)
    resolved = resolve_template(child)
    assert resolved.name == "orphan"
    assert resolved.project_type == ProjectType.UNKNOWN


def test_save_template_to_global(tmp_path):
    t = Template(name="test-tpl", path=tmp_path / "src", project_type=ProjectType.PYTHON)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Dockerfile").write_text("FROM python\n")
    with patch("acorn.config.TEMPLATES_DIR", tmp_path / "global"):
        result = save_template_to_global(t)
        assert result is not None
        assert (tmp_path / "global" / "test-tpl").exists()


def test_save_template_to_global_dry_run(tmp_path):
    t = Template(name="test-tpl", path=tmp_path / "src", project_type=ProjectType.PYTHON)
    with patch("acorn.config.TEMPLATES_DIR", tmp_path / "global"):
        result = save_template_to_global(t, dry_run=True)
        assert result is not None
        assert not (tmp_path / "global" / "test-tpl").exists()


def test_save_template_to_global_no_path():
    t = Template(name="test-tpl", project_type=ProjectType.PYTHON)
    result = save_template_to_global(t)
    assert result is None


def test_save_template_to_global_already_exists(tmp_path):
    t = Template(name="exists", path=tmp_path / "src", project_type=ProjectType.PYTHON)
    (tmp_path / "src").mkdir()
    (tmp_path / "global" / "exists").mkdir(parents=True)
    with patch("acorn.config.TEMPLATES_DIR", tmp_path / "global"):
        result = save_template_to_global(t)
        assert result is None


def test_load_project_lock_exists(tmp_path):
    lock_dir = tmp_path / PROJECT_CONFIG_DIR
    lock_dir.mkdir(parents=True)
    (lock_dir / "lock.yaml").write_text("template: test\nversion: 1.0\n")
    lock = load_project_lock(tmp_path)
    assert lock["template"] == "test"


def test_load_project_lock_not_exists(tmp_path):
    lock = load_project_lock(tmp_path)
    assert lock == {}


def test_save_project_lock(tmp_path):
    save_project_lock(tmp_path, {"template": "test"})
    lock_file = tmp_path / PROJECT_CONFIG_DIR / "lock.yaml"
    assert lock_file.exists()
    data = yaml.safe_load(lock_file.read_text())
    assert data["template"] == "test"


def test_export_config_custom_output(tmp_path):
    config_dir = tmp_path / PROJECT_CONFIG_DIR
    config_dir.mkdir(parents=True)
    (config_dir / "config.yaml").write_text("template: python-fastapi\n")
    out = tmp_path / "my-export.yaml"
    result = export_config(tmp_path, output=out)
    assert result == out
    assert out.exists()


def test_import_config(tmp_path):
    src = tmp_path / "export.yaml"
    src.write_text("config:\n  template: python-fastapi\nlock: {}\n")
    result = import_config(tmp_path, src)
    assert result is not None
    assert (tmp_path / PROJECT_CONFIG_DIR / "config.yaml").exists()


def test_import_config_missing_source(tmp_path):
    result = import_config(tmp_path, tmp_path / "nope.yaml")
    assert result is None


def test_import_config_invalid_yaml(tmp_path):
    src = tmp_path / "bad.yaml"
    src.write_text("\tinvalid: yaml: [[\n")
    result = import_config(tmp_path, src)
    assert result is None


def test_import_config_empty_data(tmp_path):
    src = tmp_path / "empty.yaml"
    src.write_text("null\n")
    result = import_config(tmp_path, src)
    assert result is None


def test_load_config_creates_default(tmp_path):
    with patch("acorn.config.CONFIG_FILE", tmp_path / "config.yaml"):
        config = load_config()
        assert config["default_lang"] == "en"
        assert config["log_level"] == "INFO"


def test_save_and_load_config(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    with patch("acorn.config.CONFIG_FILE", cfg_path):
        save_config({"default_lang": "zh", "log_level": "DEBUG"})
        loaded = load_config()
        assert loaded["default_lang"] == "zh"
        assert loaded["log_level"] == "DEBUG"


def test_load_detector_rules_empty(tmp_path):
    with patch("acorn.config.DETECTORS_DIR", tmp_path / "nonexistent"):
        with patch("acorn.config.BUILTIN_DETECTORS_DIR", tmp_path / "nonexistent-builtin"):
            rules = load_detector_rules()
            assert isinstance(rules, list)


def test_load_detector_rules_with_list(tmp_path):
    rules_dir = tmp_path / "detectors"
    rules_dir.mkdir(parents=True)
    rule_file = rules_dir / "multi.yaml"
    rule_file.write_text(
        "- name: rule1\n"
        "  type: node\n"
        "  conditions:\n"
        "    files:\n"
        "      - package.json\n"
        "- name: rule2\n"
        "  type: python\n"
        "  conditions:\n"
        "    files:\n"
        "      - requirements.txt\n"
    )
    with patch("acorn.config.BUILTIN_DETECTORS_DIR", tmp_path / "nonexistent"):
        with patch("acorn.config.DETECTORS_DIR", rules_dir):
            rules = load_detector_rules()
            assert len(rules) == 2
            assert rules[0].name == "rule1"
            assert rules[1].name == "rule2"


def test_load_detector_rules_with_global(tmp_path):
    rules_dir = tmp_path / "detectors"
    rules_dir.mkdir(parents=True)
    rule_file = rules_dir / "custom.yaml"
    rule_file.write_text(
        "name: custom\n"
        "type: python\n"
        "priority: 50\n"
        "conditions:\n"
        "  files:\n"
        "    - custom.py\n"
    )
    with patch("acorn.config.DETECTORS_DIR", rules_dir):
        rules = load_detector_rules()
        custom_rules = [r for r in rules if r.name == "custom"]
        assert len(custom_rules) >= 1


def test_load_templates_with_global(tmp_path):
    tpl_dir = tmp_path / "templates" / "custom-tpl"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "template.yaml").write_text(
        "name: custom-tpl\ndescription: Custom\ntype: python\nversion: 1.0\n"
    )
    with patch("acorn.config.TEMPLATES_DIR", tmp_path / "templates"):
        templates = load_templates()
        custom = [t for t in templates if t.name == "custom-tpl"]
        assert len(custom) == 1


def test_resolve_template_inherits_empty_fields():
    parent = Template(
        name="base",
        project_type=ProjectType.NODE,
        files=["Dockerfile"],
        detectors=DetectorCondition(files=["package.json"], keywords=["node"]),
    )
    child = Template(
        name="child",
        extends="base",
        project_type=ProjectType.UNKNOWN,
        files=[],
    )
    with patch("acorn.config.find_template_by_name", return_value=parent):
        resolved = resolve_template(child)
        assert resolved.files == ["Dockerfile"]
        assert resolved.detectors.files == ["package.json"]


def test_find_template_by_name_not_found():
    from acorn.config import find_template_by_name
    t = find_template_by_name("nonexistent-template-name")
    assert t is None


def test_load_detector_rules_global_not_exists(tmp_path):
    with patch("acorn.config.DETECTORS_DIR", tmp_path / "nonexistent"):
        rules = load_detector_rules()
        assert isinstance(rules, list)


def test_load_templates_global_not_exists(tmp_path):
    with patch("acorn.config.TEMPLATES_DIR", tmp_path / "nonexistent"):
        with patch("acorn.config.BUILTIN_TEMPLATES_DIR", tmp_path / "nonexistent-builtin"):
            templates = load_templates()
            assert isinstance(templates, list)


def test_load_templates_skip_non_dirs_and_missing_yaml(tmp_path):
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "not-a-dir.txt").write_text("hello")
    empty_dir = tpl_dir / "empty-tpl"
    empty_dir.mkdir()
    bad_dir = tpl_dir / "bad-tpl"
    bad_dir.mkdir()
    (bad_dir / "template.yaml").write_text("null\n")
    with patch("acorn.config.BUILTIN_TEMPLATES_DIR", tmp_path / "nonexistent"):
        with patch("acorn.config.TEMPLATES_DIR", tpl_dir):
            templates = load_templates()
            assert isinstance(templates, list)


def test_load_templates_global_empty(tmp_path):
    (tmp_path / "templates").mkdir()
    with patch("acorn.config.TEMPLATES_DIR", tmp_path / "templates"):
        templates = load_templates()
        assert isinstance(templates, list)


def test_resolve_template_inherits_detectors():
    parent = Template(
        name="base",
        project_type=ProjectType.NODE,
        files=["Dockerfile"],
        variables=[TemplateVariable(name="port", default="3000")],
        detectors=DetectorCondition(files=["package.json"], keywords=["node"]),
    )
    child = Template(
        name="child",
        extends="base",
        project_type=ProjectType.UNKNOWN,
        files=[],
    )
    with patch("acorn.config.find_template_by_name", return_value=parent):
        resolved = resolve_template(child)
        assert resolved.variables is not None
        assert len(resolved.variables) > 0
        assert resolved.variables[0].name == "port"


def test_load_config_with_existing_file(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("default_lang: fr\nlog_level: DEBUG\n")
    with patch("acorn.config.CONFIG_FILE", cfg_file):
        config = load_config()
        assert config["default_lang"] == "fr"
        assert config["log_level"] == "DEBUG"


def test_import_config_with_lock(tmp_path):
    src = tmp_path / "export.yaml"
    src.write_text(
        "config:\n  template: node-api\nlock:\n  version: 1.0\n  files:\n    - Dockerfile\n"
    )
    result = import_config(tmp_path, src)
    assert result is not None
    assert (tmp_path / ".acorn" / "lock.yaml").exists()
    assert (tmp_path / ".acorn" / "config.yaml").exists()


def test_import_config_lock_only(tmp_path):
    src = tmp_path / "export.yaml"
    src.write_text("lock:\n  version: 1.0\n  files:\n    - Dockerfile\n")
    result = import_config(tmp_path, src)
    assert result is not None
    assert not (tmp_path / ".acorn" / "config.yaml").exists()
    assert (tmp_path / ".acorn" / "lock.yaml").exists()


def test_export_config_default_path(tmp_path):
    config_dir = tmp_path / PROJECT_CONFIG_DIR
    config_dir.mkdir(parents=True)
    (config_dir / "config.yaml").write_text("template: go-api\n")
    result = export_config(tmp_path)
    assert result == tmp_path / "acorn-export.yaml"


def test_init_project_config_no_template(tmp_path):
    result = init_project_config(tmp_path, dry_run=False)
    assert result is not None
    assert result["init_version"] == "0.1.0"


def test_save_project_lock_existing(tmp_path):
    lock_dir = tmp_path / PROJECT_CONFIG_DIR
    lock_dir.mkdir(parents=True)
    save_project_lock(tmp_path, {"template": "test", "version": "2.0"})
    data = load_project_lock(tmp_path)
    assert data["template"] == "test"
    assert data["version"] == "2.0"


def test_load_detector_rules_with_mixed_files(tmp_path):
    (tmp_path / "rule1.yaml").write_text("name: test1\ntype: node\nconditions: {}\n")
    (tmp_path / "README.md").write_text("not a rule")
    (tmp_path / "empty.yaml").write_text("")
    (tmp_path / "null.yaml").write_text("~\n")
    with patch("acorn.config.BUILTIN_DETECTORS_DIR", tmp_path):
        with patch("acorn.config.DETECTORS_DIR", tmp_path / "nonexistent"):
            rules = load_detector_rules()
    assert len(rules) >= 1
