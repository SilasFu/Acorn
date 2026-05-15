from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CheckCategory(str, Enum):
    AI_READINESS = "ai_readiness"
    DEVOPS = "devops"
    CODE_QUALITY = "code_quality"


class CheckPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CheckRule:
    category: CheckCategory
    rel_path: str
    fix_target: str | None
    priority: CheckPriority
    auto_fixable: bool
    friendly_name: str = ""


AI_CHECKS: list[CheckRule] = [
    CheckRule(CheckCategory.AI_READINESS, ".cursorrules", "cursorrules", CheckPriority.HIGH, True, ".cursorrules"),
    CheckRule(CheckCategory.AI_READINESS, "CLAUDE.md", "claude-md", CheckPriority.HIGH, True, "CLAUDE.md"),
    CheckRule(CheckCategory.AI_READINESS, ".github/copilot-instructions.md", "copilot", CheckPriority.MEDIUM, True, ".github/copilot-instructions.md"),
]

DEVOPS_CHECKS: list[CheckRule] = [
    CheckRule(CheckCategory.DEVOPS, "Dockerfile", "dockerfile", CheckPriority.MEDIUM, True, "Dockerfile"),
    CheckRule(CheckCategory.DEVOPS, ".dockerignore", "dockerignore", CheckPriority.MEDIUM, True, ".dockerignore"),
    CheckRule(CheckCategory.DEVOPS, ".github/workflows/ci.yml", None, CheckPriority.LOW, False, ".github/workflows/ci.yml"),
]

QUALITY_CHECKS: list[CheckRule] = [
    CheckRule(CheckCategory.CODE_QUALITY, ".gitignore", "gitignore", CheckPriority.HIGH, True, ".gitignore"),
]

ALL_RULES: list[CheckRule] = AI_CHECKS + DEVOPS_CHECKS + QUALITY_CHECKS
