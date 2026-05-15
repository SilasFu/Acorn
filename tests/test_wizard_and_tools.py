from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

from acorn.cli import cmd_completion, cmd_validate, cmd_validate_ai_context
from acorn.wizard import CHECKPOINT_FILE, _clear_checkpoint, _save_checkpoint, cmd_wizard


class TestWizard:
    def test_wizard_completes_with_defaults(self, tmp_path: Path) -> None:
        _clear_checkpoint()
        # Simulate all default selections: 7 steps → 7 inputs
        # 1: name (text) → Enter (default "my-app")
        # 2: project_type (select) → 1 (api)
        # 3: language (select) → Enter (default Auto-detect)
        # 4: docker (confirm) → Enter (default True)
        # 5: ci (confirm) → Enter (default True)
        # 6: devcontainer (confirm) → n
        # 7: open_editor (confirm) → n
        inputs = iter(["", "1", "", "", "", "n", "n"])

        with (
            patch("builtins.input", lambda _="": next(inputs)),
            patch("acorn.commands.generate.cmd_generate", return_value=0),
            patch("acorn.wizard.Path.cwd", return_value=tmp_path),
        ):
            rc = cmd_wizard()
        assert rc == 0

    def test_wizard_resume_from_checkpoint(self, tmp_path: Path) -> None:
        _clear_checkpoint()
        # Save checkpoint at step 3 (after name, project_type completed)
        _save_checkpoint({"name": "my-app", "project_type": "api"}, 2)

        # Should resume at step 3 (language), so only 5 inputs needed
        inputs = iter(["1", "", "", "n", "n"])  # language + docker + ci + devcontainer + open_editor

        with (
            patch("builtins.input", lambda _="": next(inputs)),
            patch("acorn.commands.generate.cmd_generate", return_value=0),
            patch("acorn.wizard.Path.cwd", return_value=tmp_path),
        ):
            rc = cmd_wizard()
        assert rc == 0
        assert not CHECKPOINT_FILE.exists()

    def test_wizard_reset_flag(self) -> None:
        _clear_checkpoint()
        _save_checkpoint({"name": "test"}, 1)
        assert CHECKPOINT_FILE.exists()

        inputs = iter(["", "1", "", "", "", "n", "n"])
        with (
            patch("builtins.input", lambda _="": next(inputs)),
            patch("acorn.commands.generate.cmd_generate", return_value=0),
        ):
            rc = cmd_wizard(reset=True)
        assert rc == 0
        # Checkpoint should be cleared at start, then recreated during flow, then cleared at end
        assert not CHECKPOINT_FILE.exists()


class TestDockerize:
    def test_dockerize_node_project(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test", "dependencies": {"express": "^4.0.0"}}')
        args = argparse.Namespace(dir=str(tmp_path), force=False, dry_run=False, regenerate=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None)
        with patch("acorn.commands.docker.detect_project_type") as mock_detect:
            from acorn.models import DetectionResult, ProjectType
            mock_detect.return_value = DetectionResult(
                project_type=ProjectType.NODE, matched_template="node-api",
                confidence=0.9, framework="Express",
            )
            from acorn.cli import cmd_dockerize
            rc = cmd_dockerize(args)
        assert rc == 0
        assert (tmp_path / "Dockerfile").exists()
        assert (tmp_path / "docker-compose.yml").exists()

    def test_dockerize_unknown_project(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("hello")
        from acorn.cli import cmd_dockerize
        args = argparse.Namespace(dir=str(tmp_path), force=False, dry_run=False, regenerate=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None)
        rc = cmd_dockerize(args)
        assert rc != 0
        assert not (tmp_path / "Dockerfile").exists()

    def test_dockerize_skips_existing(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "Dockerfile").write_text("existing content")
        args = argparse.Namespace(dir=str(tmp_path), force=False, dry_run=False, regenerate=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None)
        with patch("acorn.commands.docker.detect_project_type") as mock_detect:
            from acorn.models import DetectionResult, ProjectType
            mock_detect.return_value = DetectionResult(
                project_type=ProjectType.NODE, matched_template="node-api",
                confidence=0.9,
            )
            from acorn.cli import cmd_dockerize
            rc = cmd_dockerize(args)
        assert rc == 0
        # Dockerfile should NOT be overwritten
        assert (tmp_path / "Dockerfile").read_text() == "existing content"
        # docker-compose.yml should be newly created
        assert (tmp_path / "docker-compose.yml").exists()

    def test_dockerize_force(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "Dockerfile").write_text("old content")
        args = argparse.Namespace(dir=str(tmp_path), force=True, dry_run=False, regenerate=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None)
        with patch("acorn.commands.docker.detect_project_type") as mock_detect:
            from acorn.models import DetectionResult, ProjectType
            mock_detect.return_value = DetectionResult(
                project_type=ProjectType.NODE, matched_template="node-api",
                confidence=0.9,
            )
            from acorn.cli import cmd_dockerize
            rc = cmd_dockerize(args)
        assert rc == 0
        content = (tmp_path / "Dockerfile").read_text()
        assert content != "old content"
        assert "FROM node" in content


class TestAddCI:
    def test_add_ci_github_actions(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        args = argparse.Namespace(dir=str(tmp_path), force=False, dry_run=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None)
        with patch("acorn.commands.docker.detect_project_type") as mock_detect:
            from acorn.models import DetectionResult, ProjectType
            mock_detect.return_value = DetectionResult(
                project_type=ProjectType.NODE, matched_template="node-api",
                confidence=0.9,
            )
            from acorn.cli import cmd_add_ci
            rc = cmd_add_ci(args)
        assert rc == 0
        ci_file = tmp_path / ".github" / "workflows" / "ci.yml"
        assert ci_file.exists()
        content = ci_file.read_text()
        assert "actions/checkout@v4" in content
        assert "actions/setup-node@v4" in content

    def test_add_ci_unknown_provider(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("hello")
        from acorn.cli import cmd_add_ci
        args = argparse.Namespace(dir=str(tmp_path), force=False, dry_run=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None)
        rc = cmd_add_ci(args)
        assert rc != 0


class TestAnalyze:
    def test_analyze_rule_only(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test", "dependencies": {"express": "^4.0.0"}}')
        args = argparse.Namespace(dir=str(tmp_path), analyze=True, allow_ai=False, json=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None, force=False, dry_run=False, regenerate=False)
        from acorn.cli import cmd_analyze
        rc = cmd_analyze(args)
        assert rc == 0

    def test_analyze_ai_disabled(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("hello")
        args = argparse.Namespace(dir=str(tmp_path), analyze=True, allow_ai=False, json=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None, force=False, dry_run=False, regenerate=False)
        from acorn.cli import cmd_analyze
        rc = cmd_analyze(args)
        assert rc == 0

    def test_analyze_ai_fallback_on_error(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test", "dependencies": {"express": "^4.0.0"}}')
        args = argparse.Namespace(dir=str(tmp_path), analyze=True, allow_ai=True, dry_run=False, json=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None, force=False, regenerate=False)
        with patch("acorn.analyzer._confirm", return_value=False):
            from acorn.cli import cmd_analyze
            rc = cmd_analyze(args)
        assert rc == 0

    def test_analyze_ai_dry_run(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        args = argparse.Namespace(dir=str(tmp_path), analyze=True, allow_ai=True, dry_run=True, json=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None, force=False, regenerate=False)
        from acorn.cli import cmd_analyze
        rc = cmd_analyze(args)
        assert rc == 0

    def test_analyze_ai_success(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test", "dependencies": {"express": "^4.0.0"}}')
        args = argparse.Namespace(dir=str(tmp_path), analyze=True, allow_ai=True, dry_run=False, json=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None, force=False, regenerate=False)
        with (
            patch("acorn.analyzer._confirm", return_value=True),
            patch("acorn.analyzer._call_llm", return_value='{"project_type": "node", "framework": "Express", "reasoning": "package.json with express dependency"}'),
        ):
            from acorn.cli import cmd_analyze
            rc = cmd_analyze(args)
        assert rc == 0


class TestClean:
    def test_clean_generated_files(self, tmp_path: Path) -> None:
        acorn_dir = tmp_path / ".acorn"
        acorn_dir.mkdir()
        (acorn_dir / "lock.yaml").write_text("files:\n  - Dockerfile\n  - docker-compose.yml\n")
        (tmp_path / "Dockerfile").write_text("content")
        (tmp_path / "docker-compose.yml").write_text("content")
        args = argparse.Namespace(dir=str(tmp_path), clean=True, dry_run=False, all=False,
                                  keep_templates=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None, force=False, regenerate=False)
        from acorn.cli import cmd_clean
        rc = cmd_clean(args)
        assert rc == 0
        assert not (tmp_path / "Dockerfile").exists()
        assert not (tmp_path / "docker-compose.yml").exists()

    def test_clean_no_manifest(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("content")
        args = argparse.Namespace(dir=str(tmp_path), clean=True, dry_run=False, all=False,
                                  keep_templates=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None, force=False, regenerate=False)
        from acorn.cli import cmd_clean
        rc = cmd_clean(args)
        assert rc != 0
        assert (tmp_path / "Dockerfile").exists()

    def test_clean_all_removes_acorn_dir(self, tmp_path: Path) -> None:
        acorn_dir = tmp_path / ".acorn"
        acorn_dir.mkdir()
        (acorn_dir / "lock.yaml").write_text("files:\n  - test.txt\n")
        args = argparse.Namespace(dir=str(tmp_path), clean=True, dry_run=False, all=True,
                                  keep_templates=False,
                                  verbose=False, debug=False, quiet=False, offline=False, lang="en",
                                  config=None, force=False, regenerate=False)
        from acorn.cli import cmd_clean
        rc = cmd_clean(args)
        assert rc == 0
        assert not acorn_dir.exists()


def test_cmd_completion_bash():
    rc = cmd_completion("bash")
    assert rc == 0


def test_cmd_completion_zsh():
    rc = cmd_completion("zsh")
    assert rc == 0


def test_cmd_completion_fish():
    rc = cmd_completion("fish")
    assert rc == 0


def test_cmd_completion_invalid():
    rc = cmd_completion("invalid")
    assert rc != 0


def test_cmd_validate_valid(tmp_path: Path):
    tpl = tmp_path / "template.yaml"
    tpl.write_text("name: test\ntype: node\nfiles: []\n")
    rc = cmd_validate(str(tpl))
    assert rc == 0


def test_cmd_validate_missing_name(tmp_path: Path):
    tpl = tmp_path / "template.yaml"
    tpl.write_text("type: node\n")
    rc = cmd_validate(str(tpl))
    assert rc != 0


def test_cmd_validate_invalid_type(tmp_path: Path):
    tpl = tmp_path / "template.yaml"
    tpl.write_text("name: test\ntype: invalid-type\n")
    rc = cmd_validate(str(tpl))
    assert rc != 0


def test_cmd_validate_not_found():
    rc = cmd_validate("/nonexistent/path")
    assert rc != 0


def test_cmd_validate_ai_context_all_valid():
    from acorn.models import AIContext, CursorRules, Template
    templates = [
        Template(
            name="good",
            path=Path("/tmp/good"),
            project_type="node",
            ai_context=AIContext(
                cursor_rules=CursorRules(tech_stack="Node.js", conventions=["Use async"]),
            ),
        ),
    ]
    with patch("acorn.commands.template_cmd.load_templates", return_value=templates):
        rc = cmd_validate_ai_context()
    assert rc == 0


def test_cmd_validate_ai_context_missing_field():
    from acorn.models import AIContext, CursorRules, Template
    templates = [
        Template(
            name="bad",
            path=Path("/tmp/bad"),
            project_type="node",
            ai_context=AIContext(
                cursor_rules=CursorRules(tech_stack="", conventions=[]),
            ),
        ),
    ]
    with patch("acorn.commands.template_cmd.load_templates", return_value=templates):
        rc = cmd_validate_ai_context()
    assert rc != 0


def test_cmd_validate_ai_context_no_ai_context():
    from acorn.models import Template
    templates = [
        Template(
            name="no-ai",
            path=Path("/tmp/no-ai"),
            project_type="node",
            ai_context=None,
        ),
    ]
    with patch("acorn.commands.template_cmd.load_templates", return_value=templates):
        rc = cmd_validate_ai_context()
    assert rc != 0


def test_main_wizard_subcommand():
    import sys

    from acorn.cli import main
    orig_argv = sys.argv
    try:
        sys.argv = ["acorn", "wizard"]
        with patch("acorn.cli.cmd_wizard", return_value=0):
            rc = main()
        assert rc == 0
    finally:
        sys.argv = orig_argv
