from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from acorn.commands.fix import cmd_fix, fix_all, GENERATABLE_FILES


def test_fix_dockerfile(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    with patch("acorn.commands.fix.detect_project_type") as mock_detect:
        from acorn.models import DetectionResult, ProjectType
        mock_detect.return_value = DetectionResult(
            project_type=ProjectType.NODE, matched_template="node-api",
            confidence=0.9,
        )
        with patch.object(type("args", (), {"dir": str(tmp_path), "fix_dockerfile": True, "fix_dockerignore": False, "fix_gitignore": False, "fix_cursorrules": False, "fix_claude_md": False, "fix_copilot": False, "fix_ai": False, "fix_all": False, "force": False, "dry_run": False})(), "dir", str(tmp_path)):
            from acorn.commands.fix import cmd_fix
            import argparse
            args = argparse.Namespace(
                dir=str(tmp_path), fix_dockerfile=True,
                fix_dockerignore=False, fix_gitignore=False,
                fix_cursorrules=False, fix_claude_md=False, fix_copilot=False,
                fix_ai=False, fix_all=False, force=False, dry_run=False,
            )
            rc = cmd_fix(args)
    assert rc == 0
    assert (tmp_path / "Dockerfile").exists()


def test_fix_ai_generates_three_files(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    with patch("acorn.commands.fix.detect_project_type") as mock_detect:
        from acorn.models import DetectionResult, ProjectType
        mock_detect.return_value = DetectionResult(
            project_type=ProjectType.NODE, matched_template="node-api",
            confidence=0.9,
        )
        args = type("args", (), {
            "dir": str(tmp_path), "fix_dockerfile": False, "fix_dockerignore": False,
            "fix_gitignore": False, "fix_cursorrules": False, "fix_claude_md": False,
            "fix_copilot": False, "fix_ai": True, "fix_all": False,
            "force": True, "dry_run": False,
        })()
        args.dir = str(tmp_path)
        rc = cmd_fix(args)
    assert rc == 0
    assert (tmp_path / ".cursorrules").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".github" / "copilot-instructions.md").exists()


def test_fix_force_overwrites(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    (tmp_path / "Dockerfile").write_text("old content")
    with patch("acorn.commands.fix.detect_project_type") as mock_detect:
        from acorn.models import DetectionResult, ProjectType
        mock_detect.return_value = DetectionResult(
            project_type=ProjectType.NODE, matched_template="node-api",
            confidence=0.9,
        )
        args = type("args", (), {
            "dir": str(tmp_path), "fix_dockerfile": True, "fix_dockerignore": False,
            "fix_gitignore": False, "fix_cursorrules": False, "fix_claude_md": False,
            "fix_copilot": False, "fix_ai": False, "fix_all": False,
            "force": True, "dry_run": False,
        })()
        args.dir = str(tmp_path)
        rc = cmd_fix(args)
    assert rc == 0
    content = (tmp_path / "Dockerfile").read_text()
    assert content != "old content"


def test_fix_skips_existing_without_force(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    (tmp_path / "Dockerfile").write_text("existing content")
    with patch("acorn.commands.fix.detect_project_type") as mock_detect:
        from acorn.models import DetectionResult, ProjectType
        mock_detect.return_value = DetectionResult(
            project_type=ProjectType.NODE, matched_template="node-api",
            confidence=0.9,
        )
        args = type("args", (), {
            "dir": str(tmp_path), "fix_dockerfile": True, "fix_dockerignore": False,
            "fix_gitignore": False, "fix_cursorrules": False, "fix_claude_md": False,
            "fix_copilot": False, "fix_ai": False, "fix_all": False,
            "force": False, "dry_run": False,
        })()
        args.dir = str(tmp_path)
        rc = cmd_fix(args)
    content = (tmp_path / "Dockerfile").read_text()
    assert content == "existing content"


def test_fix_dry_run_does_not_write(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    with patch("acorn.commands.fix.detect_project_type") as mock_detect:
        from acorn.models import DetectionResult, ProjectType
        mock_detect.return_value = DetectionResult(
            project_type=ProjectType.NODE, matched_template="node-api",
            confidence=0.9,
        )
        args = type("args", (), {
            "dir": str(tmp_path), "fix_dockerfile": True, "fix_dockerignore": False,
            "fix_gitignore": False, "fix_cursorrules": False, "fix_claude_md": False,
            "fix_copilot": False, "fix_ai": False, "fix_all": False,
            "force": False, "dry_run": True,
        })()
        args.dir = str(tmp_path)
        rc = cmd_fix(args)
    assert rc == 0
    assert not (tmp_path / "Dockerfile").exists()


def test_fix_all_generates_all(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    with patch("acorn.commands.fix.detect_project_type") as mock_detect:
        from acorn.models import DetectionResult, ProjectType
        mock_detect.return_value = DetectionResult(
            project_type=ProjectType.NODE, matched_template="node-api",
            confidence=0.9,
        )
        args = type("args", (), {
            "dir": str(tmp_path), "fix_dockerfile": False, "fix_dockerignore": False,
            "fix_gitignore": False, "fix_cursorrules": False, "fix_claude_md": False,
            "fix_copilot": False, "fix_ai": False, "fix_all": True,
            "force": True, "dry_run": False,
        })()
        args.dir = str(tmp_path)
        rc = cmd_fix(args)
    assert rc == 0
    for info in GENERATABLE_FILES.values():
        assert (tmp_path / info["dest_name"]).exists(), f"Missing {info['dest_name']}"


def test_fix_no_targets_returns_error(tmp_path):
    args = type("args", (), {
        "dir": str(tmp_path), "fix_dockerfile": False, "fix_dockerignore": False,
        "fix_gitignore": False, "fix_cursorrules": False, "fix_claude_md": False,
        "fix_copilot": False, "fix_ai": False, "fix_all": False,
        "force": False, "dry_run": False,
    })()
    args.dir = str(tmp_path)
    rc = cmd_fix(args)
    assert rc != 0


def test_fix_reuses_detection(tmp_path):
    from acorn.commands.fix import fix_all
    from acorn.models import DetectionResult, ProjectType
    (tmp_path / "package.json").write_text('{"name": "test"}')
    detection = DetectionResult(
        project_type=ProjectType.NODE, matched_template="node-api",
        confidence=0.9,
    )
    rc = fix_all(tmp_path, detection=detection, scope={"dockerfile"}, force=True)
    assert rc == 0
    assert (tmp_path / "Dockerfile").exists()
