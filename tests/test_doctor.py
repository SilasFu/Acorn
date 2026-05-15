from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from acorn.analysis.health import diagnose
from acorn.analysis.health_rules import ALL_RULES
from acorn.commands.doctor import _display_report, cmd_doctor


def test_diagnose_empty_dir(tmp_path):
    report = diagnose(tmp_path)
    assert report.project_path == tmp_path
    assert report.summary["total"] == len(ALL_RULES)
    assert report.summary["failed"] == report.summary["total"]


def test_diagnose_with_all_files(tmp_path):
    for rule in ALL_RULES:
        f = tmp_path / rule.rel_path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("content")

    report = diagnose(tmp_path)
    assert report.summary["passed"] == report.summary["total"]
    assert report.summary["failed"] == 0


def test_diagnose_partial(tmp_path):
    (tmp_path / ".gitignore").write_text("content")
    (tmp_path / "Dockerfile").write_text("content")

    report = diagnose(tmp_path)
    passed = report.summary["passed"]
    failed = report.summary["failed"]
    assert passed >= 2
    assert failed >= 1


def test_diagnose_reuses_detection(tmp_path):
    from acorn.models import DetectionResult, ProjectType
    detection = DetectionResult(
        project_type=ProjectType.PYTHON, matched_template="python-fastapi",
        confidence=0.9,
    )
    report = diagnose(tmp_path, detection=detection)
    assert report.project_type == "python"
    assert report.framework is None


def test_diagnose_json_output(tmp_path):
    report = diagnose(tmp_path)
    data = report.to_dict()
    assert "project" in data
    assert "type" in data
    assert "checks" in data
    assert "summary" in data
    assert isinstance(data["checks"], list)


def test_doctor_falls_back_to_wizard(tmp_path):
    with patch("acorn.commands.doctor.has_source_code", return_value=False):
        with patch("acorn.wizard.cmd_wizard", return_value=0) as mock_wizard:
            with patch("pathlib.Path.cwd", return_value=tmp_path):
                rc = cmd_doctor()
    assert rc == 0
    mock_wizard.assert_called_once()


def test_doctor_with_source_code(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    monkeypatch.setenv("ACORN_TELEMETRY_PROMPTED", "1")
    with (
        patch("acorn.commands.doctor.has_source_code", return_value=True),
        patch("acorn.config.load_config", return_value={"default_lang": "en"}),
        patch("acorn.commands.doctor.diagnose") as mock_diagnose,
        patch("pathlib.Path.cwd", return_value=tmp_path),
        patch("acorn.commands.doctor.confirm_or_exit", return_value=False),
    ):
        from acorn.analysis.health import HealthCheck, HealthReport
        from acorn.analysis.health_rules import CheckCategory, CheckPriority
        mock_diagnose.return_value = HealthReport(
            project_path=tmp_path, project_type="node", framework="Express",
            confidence=0.95,
            checks=[
                HealthCheck(
                    category=CheckCategory.DEVOPS, name="Dockerfile",
                    status=False, message_key="check_Dockerfile_absent",
                    fix_target="dockerfile", priority=CheckPriority.MEDIUM,
                    auto_fixable=True,
                ),
            ],
            summary={"passed": 0, "failed": 1, "total": 1},
        )
        rc = cmd_doctor()
    assert rc == 0


def test_doctor_with_source_code_fix_prompt(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    monkeypatch.setenv("ACORN_TELEMETRY_PROMPTED", "1")
    with (
        patch("acorn.commands.doctor.has_source_code", return_value=True),
        patch("acorn.config.load_config", return_value={"default_lang": "en"}),
        patch("acorn.commands.doctor.diagnose") as mock_diagnose,
        patch("pathlib.Path.cwd", return_value=tmp_path),
        patch("acorn.commands.doctor.confirm_or_exit", return_value=True),
        patch("acorn.commands.fix.fix_all", return_value=0) as mock_fix,
    ):
        from acorn.analysis.health import HealthCheck, HealthReport
        from acorn.analysis.health_rules import CheckCategory, CheckPriority
        mock_diagnose.return_value = HealthReport(
            project_path=tmp_path, project_type="node", framework="Express",
            confidence=0.95,
            checks=[
                HealthCheck(
                    category=CheckCategory.DEVOPS, name="Dockerfile",
                    status=False, message_key="check_Dockerfile_absent",
                    fix_target="dockerfile", priority=CheckPriority.MEDIUM,
                    auto_fixable=True,
                ),
            ],
            summary={"passed": 0, "failed": 1, "total": 1},
        )
        rc = cmd_doctor()
    assert rc == 0
    mock_fix.assert_called_once()


def test_doctor_display_report(capsys):
    from acorn.analysis.health import HealthCheck, HealthReport
    from acorn.analysis.health_rules import CheckCategory, CheckPriority
    report = HealthReport(
        project_path=Path("/test"),
        project_type="node",
        framework="Express",
        confidence=0.95,
        checks=[
            HealthCheck(
                category=CheckCategory.AI_READINESS,
                name=".cursorrules",
                status=True,
                message_key="check_.cursorrules_present",
                fix_target="cursorrules",
                priority=CheckPriority.HIGH,
                auto_fixable=True,
            ),
            HealthCheck(
                category=CheckCategory.DEVOPS,
                name="Dockerfile",
                status=False,
                message_key="check_Dockerfile_absent",
                fix_target="dockerfile",
                priority=CheckPriority.MEDIUM,
                auto_fixable=True,
            ),
        ],
        summary={"passed": 1, "failed": 1, "total": 2},
    )
    _display_report(report)
    captured = capsys.readouterr()
    assert "Express" in captured.out
    assert "node" in captured.out
