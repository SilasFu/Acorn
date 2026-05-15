from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from acorn.analysis.detector import detect_project_type
from acorn.analysis.health_rules import ALL_RULES, CheckCategory, CheckPriority
from acorn.analysis.insights import ProjectInsights, analyze
from acorn.models import DetectionResult


@dataclass
class HealthCheck:
    category: CheckCategory
    name: str
    status: bool
    message_key: str
    fix_target: str | None
    priority: CheckPriority
    auto_fixable: bool
    detail: str | None = None


@dataclass
class HealthReport:
    project_path: Path
    project_type: str
    framework: str | None
    confidence: float
    checks: list[HealthCheck] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=lambda: {"passed": 0, "failed": 0, "total": 0})

    def to_dict(self) -> dict:
        return {
            "project": str(self.project_path),
            "type": self.project_type,
            "framework": self.framework,
            "confidence": self.confidence,
            "summary": self.summary,
            "checks": [
                {
                    "category": c.category.value,
                    "name": c.name,
                    "status": c.status,
                    "message_key": c.message_key,
                    "auto_fixable": c.auto_fixable,
                }
                for c in self.checks
            ],
        }


def diagnose(
    dir_path: Path | str,
    detection: DetectionResult | None = None,
    insights: ProjectInsights | None = None,
) -> HealthReport:
    if isinstance(dir_path, str):
        dir_path = Path(dir_path).resolve()

    if detection is None:
        detection = detect_project_type(dir_path)
    if insights is None:
        insights = analyze(dir_path)

    checks: list[HealthCheck] = []

    for rule in ALL_RULES:
        full_path = dir_path / rule.rel_path
        exists = full_path.exists()
        status = exists

        if exists:
            message_key = f"check_{rule.rel_path}_present"
        else:
            message_key = f"check_{rule.rel_path}_absent"

        checks.append(
            HealthCheck(
                category=rule.category,
                name=rule.rel_path,
                status=status,
                message_key=message_key,
                fix_target=rule.fix_target,
                priority=rule.priority,
                auto_fixable=rule.auto_fixable,
                detail=None,
            )
        )

    passed = sum(1 for c in checks if c.status)
    failed = len(checks) - passed

    return HealthReport(
        project_path=dir_path,
        project_type=detection.project_type.value if detection else "unknown",
        framework=detection.framework if detection else None,
        confidence=detection.confidence if detection else 0.0,
        checks=checks,
        summary={"passed": passed, "failed": failed, "total": len(checks)},
    )
