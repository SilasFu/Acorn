from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from acorn.commands.sync import SYNC_TARGETS, _detect_drift, _install_hook, cmd_sync


def test_sync_detects_drift(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    (tmp_path / ".cursorrules").write_text("old stale content")
    detection_cls = type("Detection", (), {
        "project_type": type("PT", (), {"value": "node"})(),
        "framework": "Express",
        "matched_template": "node-api",
        "confidence": 0.9,
    })
    insights_cls = type("Insights", (), {
        "orm": None, "test_runner": None, "bundler": None,
        "state_management": None, "styling_approach": None,
        "api_style": None, "auth_lib": None,
        "package_manager": None,
        "import_style": "unknown", "module_system": "unknown",
        "naming_convention": "unknown",
        "architecture_pattern": None,
        "api_route_paths": [], "directory_purposes": {},
        "src_structure": {},
    })
    detection = detection_cls()
    insights = insights_cls()
    drifted = _detect_drift(tmp_path, detection, insights)
    assert len(drifted) >= 1


def test_sync_no_drift(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    detection_cls = type("Detection", (), {
        "project_type": type("PT", (), {"value": "node"})(),
        "framework": "Express",
        "matched_template": "node-api",
        "confidence": 0.9,
    })
    insights_cls = type("Insights", (), {
        "orm": None, "test_runner": None, "bundler": None,
        "state_management": None, "styling_approach": None,
        "api_style": None, "auth_lib": None,
        "package_manager": None,
        "import_style": "unknown", "module_system": "unknown",
        "naming_convention": "unknown",
        "architecture_pattern": None,
        "api_route_paths": [], "directory_purposes": {},
        "src_structure": {},
    })
    detection = detection_cls()
    insights = insights_cls()

    from acorn.generators.builtin import generate_file_content
    expected = generate_file_content(".cursorrules", "node", detection=detection, insights=insights)
    (tmp_path / ".cursorrules").write_text(expected)

    drifted = _detect_drift(tmp_path, detection, insights)
    assert len(drifted) == 0


def test_sync_regenerates_stale(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    (tmp_path / ".cursorrules").write_text("stale")

    with patch("acorn.commands.sync.detect_project_type") as mock_detect:
        from acorn.models import DetectionResult, ProjectType
        mock_detect.return_value = DetectionResult(
            project_type=ProjectType.NODE, matched_template="node-api",
            confidence=0.9,
        )
        with patch("acorn.commands.sync.analyze") as mock_analyze:
            mock_analyze.return_value = type("Insights", (), {
                "orm": None, "test_runner": None, "bundler": None,
                "state_management": None, "styling_approach": None,
                "api_style": None, "auth_lib": None,
                "package_manager": None,
                "import_style": "unknown", "module_system": "unknown",
                "naming_convention": "unknown",
                "architecture_pattern": None,
                "api_route_paths": [], "directory_purposes": {},
                "src_structure": {},
            })()
            with patch("acorn.commands.sync.has_source_code", return_value=True):
                rc = cmd_sync(cwd=tmp_path, force=True)
    assert rc == 0
    content = (tmp_path / ".cursorrules").read_text()
    assert content != "stale"


def test_sync_all_up_to_date(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    from acorn.generators.builtin import generate_file_content
    detection_cls = type("Detection", (), {
        "project_type": type("PT", (), {"value": "node"})(),
        "framework": "Express",
        "matched_template": "node-api",
        "confidence": 0.9,
    })
    insights_cls = type("Insights", (), {
        "orm": None, "test_runner": None, "bundler": None,
        "state_management": None, "styling_approach": None,
        "api_style": None, "auth_lib": None,
        "package_manager": None,
        "import_style": "unknown", "module_system": "unknown",
        "naming_convention": "unknown",
        "architecture_pattern": None,
        "api_route_paths": [], "directory_purposes": {},
        "src_structure": {},
    })
    detection = detection_cls()
    insights = insights_cls()
    expected = generate_file_content(".cursorrules", "node", detection=detection, insights=insights)
    (tmp_path / ".cursorrules").write_text(expected)

    with patch("acorn.commands.sync.detect_project_type", return_value=detection):
        with patch("acorn.commands.sync.analyze", return_value=insights):
            with patch("acorn.commands.sync.has_source_code", return_value=True):
                rc = cmd_sync(cwd=tmp_path, force=True)
    assert rc == 0


def test_sync_no_source_code(tmp_path):
    rc = cmd_sync(cwd=tmp_path, force=True)
    assert rc != 0


def test_sync_dry_run(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    (tmp_path / ".cursorrules").write_text("stale")

    with patch("acorn.commands.sync.detect_project_type") as mock_detect:
        from acorn.models import DetectionResult, ProjectType
        mock_detect.return_value = DetectionResult(
            project_type=ProjectType.NODE, matched_template="node-api",
            confidence=0.9,
        )
        with patch("acorn.commands.sync.analyze") as mock_analyze:
            mock_analyze.return_value = type("Insights", (), {
                "orm": None, "test_runner": None, "bundler": None,
                "state_management": None, "styling_approach": None,
                "api_style": None, "auth_lib": None,
                "package_manager": None,
                "import_style": "unknown", "module_system": "unknown",
                "naming_convention": "unknown",
                "architecture_pattern": None,
                "api_route_paths": [], "directory_purposes": {},
                "src_structure": {},
            })()
            with patch("acorn.commands.sync.has_source_code", return_value=True):
                rc = cmd_sync(cwd=tmp_path, force=True, dry_run=True)
    assert rc == 0
    content = (tmp_path / ".cursorrules").read_text()
    assert content == "stale"


def test_install_hook(tmp_path):
    git_hooks = tmp_path / ".git" / "hooks"
    git_hooks.mkdir(parents=True)
    rc = _install_hook(tmp_path)
    assert rc == 0
    hook = git_hooks / "pre-commit"
    assert hook.exists()
    assert hook.stat().st_mode & 0o111


def test_install_hook_no_git(tmp_path):
    rc = _install_hook(tmp_path)
    assert rc != 0


def test_install_hook_dry_run(tmp_path):
    git_hooks = tmp_path / ".git" / "hooks"
    git_hooks.mkdir(parents=True)
    rc = _install_hook(tmp_path, dry_run=True)
    assert rc == 0
    hook = git_hooks / "pre-commit"
    assert not hook.exists()


def test_sync_detects_multiple_drift(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    (tmp_path / ".cursorrules").write_text("stale cursor")
    (tmp_path / "CLAUDE.md").write_text("stale claude")
    (tmp_path / ".github" / "copilot-instructions.md").parent.mkdir(parents=True)
    (tmp_path / ".github" / "copilot-instructions.md").write_text("stale copilot")

    detection_cls = type("Detection", (), {
        "project_type": type("PT", (), {"value": "node"})(),
        "framework": "Express",
        "matched_template": "node-api",
        "confidence": 0.9,
    })
    insights_cls = type("Insights", (), {
        "orm": None, "test_runner": None, "bundler": None,
        "state_management": None, "styling_approach": None,
        "api_style": None, "auth_lib": None,
        "package_manager": None,
        "import_style": "unknown", "module_system": "unknown",
        "naming_convention": "unknown",
        "architecture_pattern": None,
        "api_route_paths": [], "directory_purposes": {},
        "src_structure": {},
    })
    drifted = _detect_drift(tmp_path, detection_cls(), insights_cls())
    assert len(drifted) == 3
