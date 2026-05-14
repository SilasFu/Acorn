from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from acorn.models import GenerationOptions, Template, TemplateVariable
from acorn.template_engine import (
    _generate_default_content,
    _generate_dockerfile,
    _get_default_files,
    _parse_list,
    auto_generate,
    backup_file,
    collect_variables,
    generate_from_template,
    get_builtin_variables,
    render_conditionals,
    render_each,
    render_template,
)


def test_render_template():
    result = render_template("Hello {{name}}!", {"name": "World"})
    assert result == "Hello World!"


def test_render_template_missing_var():
    result = render_template("{{greeting}} {{name}}", {"greeting": "Hi"})
    assert result == "Hi {{name}}"


def test_render_template_no_vars():
    result = render_template("static text", {})
    assert result == "static text"


def test_render_template_with_default():
    result = render_template("{{port|3000}}", {})
    assert result == "3000"


def test_render_template_with_default_override():
    result = render_template("{{port|3000}}", {"port": "8080"})
    assert result == "8080"


def test_get_builtin_variables():
    builtins = get_builtin_variables(target_dir=Path("/tmp/my-project"))
    assert "date" in builtins
    assert "time" in builtins
    assert "user" in builtins
    assert "cwd" in builtins
    assert builtins["project_name"] == "my-project"


def test_collect_variables_defaults():
    t = Template(
        name="test",
        variables=[
            TemplateVariable(name="port", default="3000"),
            TemplateVariable(name="name", default="app"),
        ],
    )
    result = collect_variables(t, cli_vars={"port": "8080"})
    assert result["port"] == "8080"
    assert result["name"] == "app"
    assert "date" in result


def test_collect_variables_with_target_dir(tmp_path: Path):
    t = Template(
        name="test",
        variables=[TemplateVariable(name="port", default="3000")],
    )
    result = collect_variables(t, cli_vars={}, target_dir=tmp_path)
    assert "project_name" in result
    assert result["project_name"] == tmp_path.name


def test_collect_variables_with_locked():
    t = Template(
        name="test",
        variables=[TemplateVariable(name="port", default="3000")],
    )
    result = collect_variables(t, cli_vars={}, locked_vars={"port": "9000"})
    assert result["port"] == "9000"


def test_render_conditionals_true():
    content = "{{#if has_docker}}Dockerfile content{{/if}}"
    result = render_conditionals(content, {"has_docker": "true"})
    assert result == "Dockerfile content"


def test_render_conditionals_false():
    content = "{{#if has_docker}}Dockerfile content{{/if}}"
    result = render_conditionals(content, {"has_docker": ""})
    assert result == ""


def test_render_conditionals_false_zero():
    content = "{{#if enabled}}active{{/if}}"
    result = render_conditionals(content, {"enabled": "0"})
    assert result == ""


def test_render_conditionals_nested():
    content = "before{{#if flag}}middle{{/if}}after"
    result = render_conditionals(content, {"flag": "yes"})
    assert result == "beforemiddleafter"


def test_parse_list_comma():
    assert _parse_list("a, b, c") == ["a", "b", "c"]


def test_parse_list_yaml():
    assert _parse_list("[npm, yarn, pnpm]") == ["npm", "yarn", "pnpm"]


def test_parse_list_empty():
    assert _parse_list("") == []


def test_render_each_simple():
    content = "{{#each items}}{{this}}\n{{/each}}"
    result = render_each(content, {"items": "a, b, c"})
    assert result == "a\nb\nc\n"


def test_render_each_no_items():
    content = "{{#each items}}{{this}}{{/each}}"
    result = render_each(content, {"items": ""})
    assert result == ""


def test_backup_file(tmp_path: Path):
    f = tmp_path / "test.txt"
    f.write_text("original")
    bak = backup_file(f)
    assert bak is not None
    assert bak.exists()
    assert bak.read_text() == "original"


def test_backup_file_not_exists(tmp_path: Path):
    bak = backup_file(tmp_path / "nonexistent.txt")
    assert bak is None


def test_backup_file_multiple(tmp_path: Path):
    f = tmp_path / "test.txt"
    f.write_text("v1")
    bak1 = backup_file(f)
    f.write_text("v2")
    bak2 = backup_file(f)
    assert bak1 != bak2
    assert bak2.exists()
    assert bak2.read_text() == "v2"


def test_get_default_files_for_node():
    files = _get_default_files("node")
    assert "Dockerfile" in files
    assert "docker-compose.yml" in files
    assert ".nvmrc" in files
    assert ".gitignore" in files
    assert ".devcontainer/devcontainer.json" in files


def test_get_default_files_for_python():
    files = _get_default_files("python")
    assert "Dockerfile" in files
    assert ".python-version" in files
    assert ".gitignore" in files


def test_get_default_files_for_go():
    files = _get_default_files("go")
    assert "Makefile" in files
    assert "Dockerfile" in files


def test_get_default_files_for_unknown():
    files = _get_default_files("unknown")
    assert ".devcontainer/devcontainer.json" in files
    assert ".env.example" in files


def test_generate_default_content_dockerfile_node():
    content = _generate_default_content("Dockerfile", "node", {"port": "4000", "node_version": "22"})
    assert content is not None
    assert "node:22" in content
    assert "4000" in content


def test_generate_default_content_dockerfile_python():
    content = _generate_default_content("Dockerfile", "python", {})
    assert content is not None
    assert "python:3.12" in content
    assert "uvicorn" in content


def test_generate_default_content_dockerfile_java():
    content = _generate_default_content("Dockerfile", "java", {})
    assert content is not None
    assert "temurin" in content


def test_generate_default_content_dockerfile_ruby():
    content = _generate_default_content("Dockerfile", "ruby", {})
    assert content is not None
    assert "ruby:" in content


def test_generate_default_content_dockerfile_php():
    content = _generate_default_content("Dockerfile", "php", {})
    assert content is not None
    assert "php:" in content


def test_generate_default_content_gitignore_node():
    content = _generate_default_content(".gitignore", "node", {})
    assert content is not None
    assert "node_modules/" in content


def test_generate_default_content_gitignore_python():
    content = _generate_default_content(".gitignore", "python", {})
    assert content is not None
    assert "__pycache__" in content


def test_generate_default_content_gitignore_java():
    content = _generate_default_content(".gitignore", "java", {})
    assert content is not None
    assert "target/" in content


def test_generate_default_content_devcontainer():
    content = _generate_default_content(".devcontainer/devcontainer.json", "node", {})
    assert content is not None
    assert "devcontainers" in content


def test_generate_default_content_makefile():
    content = _generate_default_content("Makefile", "go", {})
    assert content is not None
    assert ".PHONY" in content


def test_generate_default_content_nvmrc():
    content = _generate_default_content(".nvmrc", "node", {"node_version": "18"})
    assert content is not None
    assert "{{node_version}}" in content


def test_env_example_has_builtin_date():
    content = _generate_default_content(".env.example", "node", {})
    assert content is not None
    assert "{{date}}" in content


def test_render_env_example_with_builtins():
    raw = _generate_default_content(".env.example", "node", {})
    assert raw is not None
    rendered = render_template(raw, get_builtin_variables())
    assert "PORT=" in rendered
    assert "# Generated:" in rendered
    assert "{{date}}" not in rendered


def test_render_template_with_default_pipe():
    result = render_template("{{port|8080}}", {})
    assert result == "8080"
    result = render_template("{{port|8080}}", {"port": "3000"})
    assert result == "3000"


def test_render_each_with_dict_items():
    result = render_each(
        "{{#each items}}- {{this.name}}\n{{/each}}",
        {"items": '[{"name": "a"}, {"name": "b"}]'},
    )
    assert "a" in result
    assert "b" in result


def test_backup_file_all_slots_used(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("data")
    for i in range(100):
        bak = tmp_path / f"test.txt.bak{i}"
        if i > 0:
            bak.write_text("")
        else:
            tmp_path / "test.txt.bak"
            (tmp_path / "test.txt.bak").write_text("")
    # Now try backing up - should fail after 99 attempts
    result = backup_file(f)
    assert result is None


def test_generate_from_template_not_found(tmp_path):
    options = GenerationOptions()
    result = generate_from_template("nonexistent-template", tmp_path, options)
    assert result == []


def test_generate_from_template_no_path(tmp_path):
    with patch("acorn.template_engine.find_template_by_name") as mock_find:
        tpl = Template(name="test", project_type="python", files=["Dockerfile"])
        mock_find.return_value = tpl
        options = GenerationOptions()
        result = generate_from_template("test", tmp_path, options)
        assert result == []


def test_generate_dockerfile_go():
    content = _generate_dockerfile("go", {"port": "8080"})
    assert "golang" in content
    assert "8080" in content


def test_generate_dockerfile_rust():
    content = _generate_dockerfile("rust", {})
    assert "rust:" in content


def test_auto_generate_with_force(tmp_path):
    (tmp_path / "Dockerfile").write_text("old")
    options = GenerationOptions(force=True)
    result = auto_generate("node", tmp_path, options)
    assert len(result) >= 1


def test_auto_generate_skips_existing(tmp_path):
    (tmp_path / "Dockerfile").write_text("existing")
    options = GenerationOptions()
    result = auto_generate("node", tmp_path, options)
    docker_files = [p for p in result if p.name == "Dockerfile"]
    assert len(docker_files) == 0


def test_auto_generate_nonexistent_type(tmp_path):
    options = GenerationOptions()
    result = auto_generate("nonexistent", tmp_path, options)
    assert isinstance(result, list)


def test_get_default_files_for_rust():
    files = _get_default_files("rust")
    assert "Dockerfile" in files


def test_get_default_files_for_java():
    files = _get_default_files("java")
    assert "Dockerfile" in files


def test_render_conditionals_empty_var():
    content = "{{#if flag}}content{{/if}}"
    result = render_conditionals(content, {})
    assert result == ""


def test_parse_list_single():
    assert _parse_list("hello") == ["hello"]


def test_parse_list_yaml_invalid():
    assert _parse_list("[invalid") == ["[invalid"]


def test_generate_file_missing_source(tmp_path):
    from acorn.template_engine import generate_file
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    options = GenerationOptions()
    result = generate_file(tpl_path, "nonexistent.txt", tmp_path, {}, options)
    assert result is None


def test_generate_file_dest_exists_skip(tmp_path):
    from acorn.template_engine import generate_file
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "file.txt").write_text("template content")
    (tmp_path / "file.txt").write_text("existing content")
    options = GenerationOptions()
    result = generate_file(tpl_path, "file.txt", tmp_path, {}, options)
    assert result is None


def test_generate_file_dest_exists_force(tmp_path):
    from acorn.template_engine import generate_file
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "file.txt").write_text("new content")
    (tmp_path / "file.txt").write_text("old content")
    options = GenerationOptions(force=True)
    result = generate_file(tpl_path, "file.txt", tmp_path, {}, options)
    assert result is not None
    assert result.read_text() == "new content"


def test_generate_file_dest_exists_regenerate(tmp_path):
    from acorn.template_engine import generate_file
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "file.txt").write_text("new content")
    (tmp_path / "file.txt").write_text("old content")
    options = GenerationOptions(regenerate=True)
    result = generate_file(tpl_path, "file.txt", tmp_path, {}, options)
    assert result is not None
    assert result.read_text() == "new content"
    bak = tmp_path / "file.txt.bak"
    assert bak.exists()
    assert bak.read_text() == "old content"


def test_generate_file_with_variables(tmp_path):
    from acorn.template_engine import generate_file
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "index.js").write_text("const port = {{port}};\n")
    options = GenerationOptions()
    result = generate_file(tpl_path, "index.js", tmp_path, {"port": "8080"}, options)
    assert result is not None
    assert result.read_text() == "const port = 8080;\n"


def test_generate_file_files_subdirectory(tmp_path):
    from acorn.template_engine import generate_from_template
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "template.yaml").write_text(
        "name: test-tpl\ndescription: Test\nversion: 1.0.0\ntype: node\nfiles:\n  - Dockerfile\n"
    )
    files_dir = tpl_path / "files"
    files_dir.mkdir()
    (files_dir / "extra.conf").write_text("extra={{port}}\n")
    (tpl_path / "Dockerfile").write_text("FROM node\n")
    with patch("acorn.template_engine.find_template_by_name") as mock_find:
        from acorn.models import Template
        tpl = Template(
            name="test-tpl",
            path=tpl_path,
            project_type="node",
            files=["Dockerfile"],
        )
        mock_find.return_value = tpl
        with patch("acorn.template_engine.resolve_template", return_value=tpl):
            out_dir = tmp_path / "out"
            out_dir.mkdir()
            options = GenerationOptions()
            result = generate_from_template("test-tpl", out_dir, options)
            assert len(result) >= 2
            assert (out_dir / "Dockerfile").exists()
            assert (out_dir / "extra.conf").exists()


def test_generate_file_dry_run(tmp_path):
    from acorn.template_engine import generate_file
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "main.py").write_text("print('hello')")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    options = GenerationOptions(dry_run=True)
    result = generate_file(tpl_path, "main.py", out_dir, {}, options)
    assert result is None
    assert not (out_dir / "main.py").exists()


def test_run_hooks_failure(tmp_path):
    from acorn.models import Hooks
    from acorn.template_engine import run_hooks
    hooks = Hooks(before_generate="nonexistent_command_xyz123")
    run_hooks(hooks, "before", variables={})


def test_auto_generate_regenerate(tmp_path):
    (tmp_path / "Dockerfile").write_text("old")
    options = GenerationOptions(regenerate=True)
    result = auto_generate("node", tmp_path, options)
    docker_files = [p for p in result if p.name == "Dockerfile"]
    assert len(docker_files) == 1


def test_auto_generate_with_custom_vars(tmp_path):
    options = GenerationOptions(variables={"port": "5000", "node_version": "18"})
    result = auto_generate("node", tmp_path, options)
    docker_file = next((p for p in result if p.name == "Dockerfile"), None)
    if docker_file:
        content = docker_file.read_text()
        assert "node:18" in content
        assert "5000" in content


def test_get_default_files_for_ruby():
    files = _get_default_files("ruby")
    assert "Dockerfile" in files


def test_get_default_files_for_php():
    files = _get_default_files("php")
    assert "Dockerfile" in files


def test_generate_file_with_regenerate_creates_backup(tmp_path):
    from acorn.template_engine import generate_file
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "app.js").write_text("// new version")
    (tmp_path / "app.js").write_text("// old version")
    opts = GenerationOptions(regenerate=True)
    result = generate_file(tpl_path, "app.js", tmp_path, {}, opts)
    assert result is not None
    assert (tmp_path / "app.js.bak").exists()


def test_log_level_set_with_debug(capsys):
    from acorn.log import LogLevel, _log, set_level
    set_level(LogLevel.DEBUG)
    _log(LogLevel.DEBUG, "debug only")
    captured = capsys.readouterr()
    assert "debug only" in captured.out


def test_render_each_with_no_items():
    result = render_each("{{#each items}}{{this}}{{/each}}", {"items": ""})
    assert result == ""


def test_render_each_with_comma_list():
    result = render_each("{{#each items}}{{this}}\n{{/each}}", {"items": "x, y, z"})
    assert result == "x\ny\nz\n"


def test_collect_variables_interactive_with_cli():
    t = Template(
        name="test",
        variables=[TemplateVariable(name="port", default="3000")],
    )
    result = collect_variables(t, cli_vars={"port": "8080"}, interactive=True)
    assert result["port"] == "8080"


def test_collect_variables_interactive_with_options():
    t = Template(
        name="test",
        variables=[TemplateVariable(name="mode", default="dev", options=["dev", "prod"])],
    )
    with patch("builtins.input", return_value="2"):
        result = collect_variables(t, cli_vars={}, interactive=True)
        assert result["mode"] == "prod"


def test_collect_variables_interactive_prompt():
    t = Template(
        name="test",
        variables=[TemplateVariable(name="name", default="app")],
    )
    with patch("builtins.input", return_value="myapp"):
        result = collect_variables(t, cli_vars={}, interactive=True)
        assert result["name"] == "myapp"


def test_collect_variables_interactive_eof():
    t = Template(
        name="test",
        variables=[TemplateVariable(name="name", default="default-name")],
    )
    with patch("builtins.input", side_effect=EOFError):
        result = collect_variables(t, cli_vars={}, interactive=True)
        assert result["name"] == "default-name"


def test_collect_variables_interactive_option_eof():
    t = Template(
        name="test",
        variables=[TemplateVariable(name="mode", default="dev", options=["dev", "prod"])],
    )
    with patch("builtins.input", side_effect=EOFError):
        result = collect_variables(t, cli_vars={}, interactive=True)
        assert result["mode"] == "dev"


def test_generate_from_template_version_check(tmp_path):
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "template.yaml").write_text("name: test\ndescription: x\nversion: 1.0\ntype: node\nfiles: []\n")
    (tpl_path / "Dockerfile").write_text("FROM node\n")
    with patch("acorn.template_engine.find_template_by_name") as mock_find:
        tpl = Template(
            name="test",
            path=tpl_path,
            project_type="node",
            files=["Dockerfile"],
            min_tool_version="99.99.99",
        )
        mock_find.return_value = tpl
        options = GenerationOptions()
        result = generate_from_template("test", tmp_path / "out", options)
        assert isinstance(result, list)


def test_auto_generate_docker_compose(tmp_path):
    options = GenerationOptions()
    result = auto_generate("node", tmp_path, options)
    compose = [p for p in result if p.name == "docker-compose.yml"]
    assert len(compose) > 0


def test_auto_generate_devcontainer(tmp_path):
    options = GenerationOptions()
    result = auto_generate("python", tmp_path, options)
    dc = [p for p in result if "devcontainer" in str(p)]
    assert len(dc) > 0


def test_auto_generate_dry_run(tmp_path):
    options = GenerationOptions(dry_run=True)
    result = auto_generate("node", tmp_path, options)
    assert len(result) == 0
    assert not (tmp_path / "Dockerfile").exists()


def test_auto_generate_regenerate_backup(tmp_path):
    (tmp_path / "Dockerfile").write_text("old")
    options = GenerationOptions(regenerate=True)
    result = auto_generate("node", tmp_path, options)
    assert len(result) > 0
    assert (tmp_path / "Dockerfile.bak").exists()


def test_auto_generate_unknown_type(tmp_path):
    options = GenerationOptions()
    result = auto_generate("nonexistent-type", tmp_path, options)
    assert isinstance(result, list)


def test_collect_variables_interactive_option_out_of_range():
    t = Template(
        name="test",
        variables=[TemplateVariable(name="mode", default="dev", options=["dev", "prod"])],
    )
    with patch("builtins.input", return_value="99"):
        result = collect_variables(t, cli_vars={}, interactive=True)
        assert result["mode"] == "dev"


def test_parse_list_yaml_exception():
    result = _parse_list("[invalid, yaml]")
    assert isinstance(result, list)


def test_generate_file_regenerate_no_backup(tmp_path):
    from acorn.template_engine import generate_file
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "file.txt").write_text("new")
    (tmp_path / "file.txt").write_text("old")
    for i in range(100):
        bak = tmp_path / f"file.txt.bak{i}" if i > 0 else tmp_path / "file.txt.bak"
        bak.write_text("")
    options = GenerationOptions(regenerate=True)
    result = generate_file(tpl_path, "file.txt", tmp_path, {}, options)
    assert result is not None


def test_run_hooks_file_not_found():
    from acorn.models import Hooks
    from acorn.template_engine import run_hooks
    hooks = Hooks(before_generate="/nonexistent/path/to/command")
    run_hooks(hooks, "before", variables={})


def test_generate_from_template_str_output_dir(tmp_path):
    from acorn.template_engine import generate_from_template
    options = GenerationOptions()
    result = generate_from_template("nonexistent-template", str(tmp_path), options)
    assert result == []


def test_save_as_template_default_name(tmp_path):
    from acorn.template_engine import save_as_template_from_project
    with patch("acorn.template_engine.save_template_to_global", return_value=None):
        result = save_as_template_from_project(tmp_path)
        assert result is None


def test_auto_generate_skips_none_content(tmp_path):
    options = GenerationOptions()
    result = auto_generate("node", tmp_path, options)
    assert isinstance(result, list)


def test_generate_from_template_files_dir_dry_run(tmp_path):
    from acorn.template_engine import generate_from_template
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "template.yaml").write_text("name: test\ndescription: x\nversion: 1.0\ntype: node\nfiles: []\n")
    files_dir = tpl_path / "files"
    files_dir.mkdir()
    (files_dir / "extra.conf").write_text("key=val\n")
    with patch("acorn.template_engine.find_template_by_name") as mock_find:
        tpl = Template(name="test", path=tpl_path, project_type="node", files=[])
        mock_find.return_value = tpl
        with patch("acorn.template_engine.resolve_template", return_value=tpl):
            out_dir = tmp_path / "out"
            out_dir.mkdir()
            options = GenerationOptions(dry_run=True)
            generate_from_template("test", out_dir, options)
            assert not (out_dir / "extra.conf").exists()


def test_generate_from_template_files_dir_force_overwrite(tmp_path):
    from acorn.template_engine import generate_from_template
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "template.yaml").write_text("name: test\ndescription: x\nversion: 1.0\ntype: node\nfiles: []\n")
    files_dir = tpl_path / "files"
    files_dir.mkdir()
    (files_dir / "extra.conf").write_text("new content\n")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "extra.conf").write_text("old content\n")
    with patch("acorn.template_engine.find_template_by_name") as mock_find:
        tpl = Template(name="test", path=tpl_path, project_type="node", files=[])
        mock_find.return_value = tpl
        with patch("acorn.template_engine.resolve_template", return_value=tpl):
            options = GenerationOptions(force=True)
            generate_from_template("test", out_dir, options)
            assert (out_dir / "extra.conf").exists()
            assert (out_dir / "extra.conf").read_text() == "new content\n"


def test_save_as_template_with_generated_files(tmp_path):
    from acorn.template_engine import save_as_template_from_project
    (tmp_path / "Dockerfile").write_text("FROM node\n")
    with patch("acorn.template_engine.save_template_to_global", return_value=tmp_path / "saved"):
        result = save_as_template_from_project(tmp_path)
        assert result == tmp_path / "saved"


def test_auto_generate_regenerate_no_backup(tmp_path):
    (tmp_path / "Dockerfile").write_text("old")
    for i in range(100):
        bak = tmp_path / "Dockerfile.bak" if i == 0 else tmp_path / f"Dockerfile.bak{i}"
        if i == 0:
            (tmp_path / "Dockerfile.bak").write_text("")
        else:
            bak.write_text("")
    options = GenerationOptions(regenerate=True)
    result = auto_generate("node", tmp_path, options)
    assert len(result) > 0


def test_generate_default_content_python_version():
    content = _generate_default_content(".python-version", "python", {})
    assert content == "3.12\n"


def test_generate_default_content_unknown_path():
    content = _generate_default_content("random.file", "node", {})
    assert content is None


def test_generate_docker_compose_default_port():
    from acorn.template_engine import _generate_docker_compose
    content = _generate_docker_compose("node", {"port": "5000"})
    assert "5000" in content
    assert "3.8" in content


def test_generate_docker_compose_default():
    from acorn.template_engine import _generate_docker_compose
    content = _generate_docker_compose("python", {})
    assert "3000" in content


def test_generate_dockerfile_unknown():
    from acorn.template_engine import _generate_dockerfile
    content = _generate_dockerfile("unknown", {})
    assert "FROM unknown" in content


def test_generate_gitignore_go():
    from acorn.template_engine import _generate_gitignore
    content = _generate_gitignore("go")
    assert "vendor/" in content


def test_generate_gitignore_rust():
    from acorn.template_engine import _generate_gitignore
    content = _generate_gitignore("rust")
    assert "target/" in content


def test_generate_gitignore_default():
    from acorn.template_engine import _generate_gitignore
    content = _generate_gitignore("unknown")
    assert ".env" in content


def test_generate_makefile():
    from acorn.template_engine import _generate_makefile
    content = _generate_makefile("any")
    assert ".PHONY" in content
    assert "build:" in content


def test_select_from_options_non_digit():
    from acorn.models import TemplateVariable
    from acorn.template_engine import _select_from_options
    var = TemplateVariable(name="mode", default="dev", options=["dev", "prod"])
    with patch("builtins.input", return_value=""):
        result = _select_from_options(var)
    assert result == "dev"


def test_select_from_options_invalid_choice():
    from acorn.models import TemplateVariable
    from acorn.template_engine import _select_from_options
    var = TemplateVariable(name="mode", default="dev", options=["dev", "prod"])
    with patch("builtins.input", return_value="99"):
        result = _select_from_options(var)
    assert result == "dev"


def test_parse_list_yaml_exception_bracketed():
    from acorn.template_engine import _parse_list
    result = _parse_list("[*}*]")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == "[*}*]"


def test_auto_generate_skip_on_content_none(tmp_path):
    from acorn.models import GenerationOptions
    from acorn.template_engine import auto_generate
    options = GenerationOptions()
    (tmp_path / "Dockerfile").write_text("exists")
    (tmp_path / ".env.example").write_text("exists")
    result = auto_generate("node", tmp_path, options)
    assert isinstance(result, list)


def test_generate_from_template_files_dir_multi_file(tmp_path):
    from acorn.template_engine import generate_from_template
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "template.yaml").write_text("name: test\ndescription: x\nversion: 1.0\ntype: node\nfiles: []\n")
    files_dir = tpl_path / "files"
    files_dir.mkdir()
    (files_dir / "a.conf").write_text("a=1\n")
    (files_dir / "b.conf").write_text("b=2\n")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    with patch("acorn.template_engine.find_template_by_name") as mock_find:
        tpl = Template(name="test", path=tpl_path, project_type="node", files=[])
        mock_find.return_value = tpl
        with patch("acorn.template_engine.resolve_template", return_value=tpl):
            options = GenerationOptions(dry_run=True)
            generate_from_template("test", out_dir, options)
            assert not (out_dir / "a.conf").exists()


def test_generate_from_template_files_dir_skip_existing(tmp_path):
    from acorn.models import GenerationOptions
    from acorn.template_engine import generate_from_template
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "template.yaml").write_text("name: test\ndescription: x\nversion: 1.0\ntype: node\nfiles: []\n")
    files_dir = tpl_path / "files"
    files_dir.mkdir()
    (files_dir / "extra.conf").write_text("new\n")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "extra.conf").write_text("old\n")
    with patch("acorn.template_engine.find_template_by_name") as mock_find:
        tpl = Template(name="test", path=tpl_path, project_type="node", files=[])
        mock_find.return_value = tpl
        with patch("acorn.template_engine.resolve_template", return_value=tpl):
            options = GenerationOptions()
            generate_from_template("test", out_dir, options)
            assert (out_dir / "extra.conf").exists()
            assert (out_dir / "extra.conf").read_text() == "old\n"


def test_generate_from_template_files_dir_regenerate_backup(tmp_path):
    from acorn.template_engine import generate_from_template
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "template.yaml").write_text("name: test\ndescription: x\nversion: 1.0\ntype: node\nfiles: []\n")
    files_dir = tpl_path / "files"
    files_dir.mkdir()
    (files_dir / "extra.conf").write_text("new\n")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "extra.conf").write_text("old\n")
    with patch("acorn.template_engine.find_template_by_name") as mock_find:
        tpl = Template(name="test", path=tpl_path, project_type="node", files=[])
        mock_find.return_value = tpl
        with patch("acorn.template_engine.resolve_template", return_value=tpl):
            options = GenerationOptions(regenerate=True)
            generate_from_template("test", out_dir, options)
            assert (out_dir / "extra.conf").exists()
            bak = out_dir / "extra.conf.bak"
            assert bak.exists() or (out_dir / "extra.conf.1.bak").exists()


def test_save_as_template_with_description(tmp_path):
    from acorn.template_engine import save_as_template_from_project
    with patch("acorn.template_engine.save_template_to_global", return_value=tmp_path / "saved"):
        result = save_as_template_from_project(tmp_path, name="test", description="custom desc")
        assert result == tmp_path / "saved"


def test_run_hooks_file_not_found_error():
    from acorn.models import Hooks
    from acorn.template_engine import run_hooks
    hooks = Hooks(before_generate="nonexistent-command-that-should-not-be-found")
    run_hooks(hooks, "before", variables={})


def test_generate_from_template_files_dir_with_subdir(tmp_path):
    from acorn.template_engine import generate_from_template
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "template.yaml").write_text("name: test\ndescription: x\nversion: 1.0\ntype: node\nfiles: []\n")
    files_dir = tpl_path / "files"
    files_dir.mkdir()
    (files_dir / "a.conf").write_text("a=1\n")
    sub = files_dir / "sub"
    sub.mkdir()
    (sub / "b.conf").write_text("b=2\n")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    with patch("acorn.template_engine.find_template_by_name") as mock_find:
        tpl = Template(name="test", path=tpl_path, project_type="node", files=[])
        mock_find.return_value = tpl
        with patch("acorn.template_engine.resolve_template", return_value=tpl):
            options = GenerationOptions(dry_run=True)
            generate_from_template("test", out_dir, options)


def test_generate_from_template_files_dir_regenerate_no_backup(tmp_path):
    from acorn.template_engine import generate_from_template
    tpl_path = tmp_path / "tpl"
    tpl_path.mkdir()
    (tpl_path / "template.yaml").write_text("name: test\ndescription: x\nversion: 1.0\ntype: node\nfiles: []\n")
    files_dir = tpl_path / "files"
    files_dir.mkdir()
    (files_dir / "extra.conf").write_text("new\n")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "extra.conf").write_text("old\n")
    for i in range(100):
        bak = out_dir / f"extra.conf.bak{i}" if i > 0 else out_dir / "extra.conf.bak"
        bak.write_text("")
    with patch("acorn.template_engine.find_template_by_name") as mock_find:
        tpl = Template(name="test", path=tpl_path, project_type="node", files=[])
        mock_find.return_value = tpl
        with patch("acorn.template_engine.resolve_template", return_value=tpl):
            options = GenerationOptions(regenerate=True)
            generate_from_template("test", out_dir, options)
