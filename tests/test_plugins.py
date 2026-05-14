from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from acorn.plugins import (
    ensure_plugin_dirs,
    find_custom_command,
    list_custom_commands,
    load_all_plugins,
    load_plugin,
    run_hook,
)


def test_ensure_plugin_dirs():
    ensure_plugin_dirs()
    from acorn.plugins import COMMANDS_DIR, PLUGINS_DIR
    assert PLUGINS_DIR.exists()
    assert COMMANDS_DIR.exists()


def test_load_plugin_nonexistent():
    module = load_plugin(Path("/nonexistent/plugin.py"))
    assert module is None


def test_list_custom_commands_empty():
    cmds = list_custom_commands()
    assert isinstance(cmds, list)


def test_list_custom_commands_with_scripts(tmp_path):
    script = tmp_path / "hello.sh"
    script.write_text("#!/bin/sh\necho hello\n")
    script.chmod(0o755)
    with patch("acorn.plugins.COMMANDS_DIR", tmp_path):
        cmds = list_custom_commands()
        assert "hello" in cmds


def test_load_plugin_valid(tmp_path):
    plugin_file = tmp_path / "test_plugin.py"
    plugin_file.write_text(
        "def before_detect(ctx):\n"
        '    ctx["plugins_run"] = ctx.get("plugins_run", []) + ["before_detect"]\n'
        "def after_detect(ctx):\n"
        '    ctx["plugins_run"] = ctx.get("plugins_run", []) + ["after_detect"]\n'
    )
    module = load_plugin(plugin_file)
    assert module is not None
    ctx: dict = {}
    module.before_detect(ctx)
    assert ctx["plugins_run"] == ["before_detect"]


def test_run_hook_before_detect(tmp_path):
    plugin_file = tmp_path / "hook_plugin.py"
    plugin_file.write_text(
        "def before_detect(ctx):\n"
        '    ctx["hook_run"] = True\n'
        "    return ctx\n"
    )
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        result = run_hook("before_detect", context={"hook_run": False})
        assert result is not None
        assert result.get("hook_run") is True


def test_run_hook_after_detect(tmp_path):
    plugin_file = tmp_path / "hook_plugin.py"
    plugin_file.write_text(
        "def after_detect(ctx):\n"
        '    ctx["hook_run"] = True\n'
        "    return ctx\n"
    )
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        result = run_hook("after_detect", context={"hook_run": False})
        assert result is not None
        assert result.get("hook_run") is True


def test_run_hook_before_generate(tmp_path):
    plugin_file = tmp_path / "gen_plugin.py"
    plugin_file.write_text(
        "def before_generate(ctx):\n"
        '    ctx["hook_run"] = True\n'
        "    return ctx\n"
    )
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        result = run_hook("before_generate", context={"hook_run": False})
        assert result is not None
        assert result.get("hook_run") is True


def test_run_hook_after_generate(tmp_path):
    plugin_file = tmp_path / "gen_plugin.py"
    plugin_file.write_text(
        "def after_generate(ctx):\n"
        '    ctx["hook_run"] = True\n'
        "    return ctx\n"
    )
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        result = run_hook("after_generate", context={"hook_run": False})
        assert result is not None
        assert result.get("hook_run") is True


def test_run_hook_no_plugins(tmp_path):
    empty_dir = tmp_path / "empty_plugins"
    empty_dir.mkdir()
    with patch("acorn.plugins.PLUGINS_DIR", empty_dir):
        result = run_hook("before_detect", context={"foo": "bar"})
        assert result == {"foo": "bar"}


def test_load_plugin_syntax_error(tmp_path):
    plugin_file = tmp_path / "bad_plugin.py"
    plugin_file.write_text("def broken(\n")
    module = load_plugin(plugin_file)
    assert module is None


def test_run_hook_error_isolation(tmp_path):
    plugin_file = tmp_path / "error_plugin.py"
    plugin_file.write_text(
        "def before_detect(ctx):\n"
        "    raise RuntimeError('plugin error')\n"
    )
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        result = run_hook("before_detect", context={"foo": "bar"})
        assert result == {"foo": "bar"}


def test_run_hook_multiple_plugins(tmp_path):
    p1 = tmp_path / "plugin1.py"
    p1.write_text(
        "def before_detect(ctx):\n"
        '    ctx.setdefault("order", []).append("p1")\n'
        "    return ctx\n"
    )
    p2 = tmp_path / "plugin2.py"
    p2.write_text(
        "def before_detect(ctx):\n"
        '    ctx.setdefault("order", []).append("p2")\n'
        "    return ctx\n"
    )
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        result = run_hook("before_detect", context={"order": []})
        assert result is not None


def test_load_all_plugins(tmp_path):
    p1 = tmp_path / "p1.py"
    p1.write_text("def before_detect(ctx): return ctx\n")
    p2 = tmp_path / "p2.py"
    p2.write_text("def after_detect(ctx): return ctx\n")
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        plugins = load_all_plugins()
        assert len(plugins) == 2


def test_find_custom_command(tmp_path):
    cmd = tmp_path / "hello.sh"
    cmd.write_text("#!/bin/sh\necho hello\n")
    cmd.chmod(0o755)
    with patch("acorn.plugins.COMMANDS_DIR", tmp_path):
        found = find_custom_command("hello")
        assert found is not None
        assert found.name == "hello.sh"


def test_find_custom_command_nonexistent(tmp_path):
    with patch("acorn.plugins.COMMANDS_DIR", tmp_path):
        found = find_custom_command("nonexistent")
        assert found is None


def test_load_all_plugins_with_failure(tmp_path):
    p1 = tmp_path / "good.py"
    p1.write_text("def before_detect(ctx): return ctx\n")
    p2 = tmp_path / "bad.py"
    p2.write_text("def broken(\n")
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        plugins = load_all_plugins()
        assert len(plugins) == 1


def test_run_hook_missing_hook_on_plugin(tmp_path):
    p1 = tmp_path / "nohook.py"
    p1.write_text("x = 1\n")
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        result = run_hook("before_detect", context={"foo": "bar"})
        assert result == {"foo": "bar"}


def test_list_custom_commands_skips_underscore(tmp_path):
    (tmp_path / "_private.py").write_text("")
    (tmp_path / "public.py").write_text("")
    with patch("acorn.plugins.COMMANDS_DIR", tmp_path):
        cmds = list_custom_commands()
        assert "public" in cmds
        assert "_private" not in cmds


def test_find_custom_command_py_extension(tmp_path):
    cmd = tmp_path / "serve.py"
    cmd.write_text("#!/usr/bin/env python\nprint('serve')\n")
    cmd.chmod(0o755)
    with patch("acorn.plugins.COMMANDS_DIR", tmp_path):
        found = find_custom_command("serve")
        assert found is not None
        assert found.name == "serve.py"


def test_run_hook_with_context_not_none(tmp_path):
    plugin_file = tmp_path / "ctx_plugin.py"
    plugin_file.write_text(
        "def before_detect(ctx):\n"
        "    return 'processed:' + str(ctx)\n"
    )
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        result = run_hook("before_detect", context={"start": True})
        assert result == "processed:{'start': True}"


def test_load_plugin_spec_fails(tmp_path):
    plugin_file = tmp_path / "empty.py"
    plugin_file.write_text("x = 1\n")
    from acorn.plugins import load_plugin
    module = load_plugin(plugin_file)
    assert module is not None
    assert hasattr(module, "x")
    assert module.x == 1


def test_load_plugin_no_loader(tmp_path):
    plugin_file = tmp_path / "nope.py"
    plugin_file.write_text("x = 1\n")
    with patch("importlib.util.spec_from_file_location") as mock_spec:
        mock_spec.return_value.loader = None
        module = load_plugin(plugin_file)
    assert module is None


def test_run_hook_without_context(tmp_path):
    plugin_file = tmp_path / "simple.py"
    plugin_file.write_text("def before_detect():\n    return 'called'\n")
    with patch("acorn.plugins.PLUGINS_DIR", tmp_path):
        result = run_hook("before_detect")
        assert result == 'called'
