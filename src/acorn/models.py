from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ProjectType(str, Enum):
    NODE = "node"
    PYTHON = "python"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    RUBY = "ruby"
    PHP = "php"
    DENO = "deno"
    BUN = "bun"
    UNKNOWN = "unknown"


@dataclass
class DetectorCondition:
    files: list[str] = field(default_factory=list)
    content: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)


@dataclass
class FrameworkIndicator:
    name: str
    check_expression: str


@dataclass
class DetectorRule:
    name: str
    type: ProjectType
    priority: int = 0
    conditions: DetectorCondition = field(default_factory=DetectorCondition)
    indicators: list[FrameworkIndicator] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> DetectorRule:
        conditions = DetectorCondition(
            files=data.get("conditions", {}).get("files", []),
            content=data.get("conditions", {}).get("content", []),
            dependencies=data.get("conditions", {}).get("dependencies", []),
            patterns=data.get("conditions", {}).get("patterns", []),
        )
        indicators = [
            FrameworkIndicator(name=k, check_expression=v)
            for k, v in data.get("indicators", {}).items()
        ]
        return cls(
            name=data["name"],
            type=ProjectType(data["type"]),
            priority=data.get("priority", 0),
            conditions=conditions,
            indicators=indicators,
        )


@dataclass
class TemplateVariable:
    name: str
    default: str = ""
    description: str = ""
    prompt: str = ""
    options: list[str] = field(default_factory=list)


@dataclass
class TemplateFile:
    source: str
    target: str | None = None
    condition: str | None = None


@dataclass
class Hooks:
    before_generate: str | None = None
    after_generate: str | None = None
    before_detect: str | None = None
    after_detect: str | None = None


@dataclass
class CursorRules:
    tech_stack: str = ""
    conventions: list[str] = field(default_factory=list)


@dataclass
class AIContext:
    cursor_rules: CursorRules = field(default_factory=CursorRules)


@dataclass
class Template:
    name: str
    description: str = ""
    version: str = "1.0.0"
    path: Path | None = None
    detectors: DetectorCondition = field(default_factory=DetectorCondition)
    variables: list[TemplateVariable] = field(default_factory=list)
    extends: str | None = None
    files: list[str] = field(default_factory=list)
    project_type: ProjectType = ProjectType.UNKNOWN
    locked_files: list[str] = field(default_factory=list)
    locked_variables: dict[str, str] = field(default_factory=dict)
    hooks: Hooks = field(default_factory=Hooks)
    min_tool_version: str | None = None
    ai_context: AIContext | None = None
    provides: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict, path: Path | None = None) -> Template:
        detectors = DetectorCondition(
            files=data.get("detectors", {}).get("files", []),
            keywords=data.get("detectors", {}).get("keywords", []),
        )
        variables = [
            TemplateVariable(
                name=v.get("name", ""),
                default=v.get("default", ""),
                description=v.get("description", ""),
                prompt=v.get("prompt", v.get("name", "")),
                options=v.get("options", []),
            )
            for v in data.get("variables", [])
        ]
        hooks_data = data.get("hooks", {})
        hooks = Hooks(
            before_generate=hooks_data.get("before_generate"),
            after_generate=hooks_data.get("after_generate"),
            before_detect=hooks_data.get("before_detect"),
            after_detect=hooks_data.get("after_detect"),
        )
        ai_data = data.get("ai_context", {})
        cursor_data = ai_data.get("cursor_rules", {}) if ai_data else {}
        ai_context = None
        if cursor_data:
            ai_context = AIContext(
                cursor_rules=CursorRules(
                    tech_stack=cursor_data.get("tech_stack", ""),
                    conventions=cursor_data.get("conventions", []),
                )
            )
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            path=path,
            detectors=detectors,
            variables=variables,
            extends=data.get("extends"),
            files=data.get("files", []),
            project_type=ProjectType(data.get("type", "unknown")),
            locked_files=data.get("locked_files", []),
            locked_variables=data.get("locked_variables", {}),
            hooks=hooks,
            min_tool_version=data.get("min_tool_version"),
            ai_context=ai_context,
            provides=data.get("provides", []),
            requires=data.get("requires", []),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "type": self.project_type.value,
            "detectors": {
                "files": self.detectors.files,
                "keywords": self.detectors.keywords,
            },
            "variables": [
                {
                    "name": v.name,
                    "default": v.default,
                    "description": v.description,
                    "prompt": v.prompt,
                }
                for v in self.variables
            ],
            "extends": self.extends,
            "files": self.files,
        }
        if self.ai_context and (self.ai_context.cursor_rules.tech_stack or self.ai_context.cursor_rules.conventions):
            result["ai_context"] = {
                "cursor_rules": {
                    "tech_stack": self.ai_context.cursor_rules.tech_stack,
                    "conventions": self.ai_context.cursor_rules.conventions,
                }
            }
        if self.provides:
            result["provides"] = self.provides
        if self.requires:
            result["requires"] = self.requires
        return result


@dataclass
class DetectionResult:
    project_type: ProjectType = ProjectType.UNKNOWN
    framework: str | None = None
    matched_template: str | None = None
    confidence: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    all_matches: list[tuple[ProjectType, str, float]] = field(default_factory=list)


@dataclass
class GenerationOptions:
    force: bool = False
    dry_run: bool = False
    interactive: bool = False
    template_name: str | None = None
    save: bool = False
    init: bool = False
    regenerate: bool = False
    search: str | None = None
    install: str | None = None
    verbose: bool = False
    debug: bool = False
    quiet: bool = False
    offline: bool = False
    lang: str | None = None
    variables: dict[str, str] = field(default_factory=dict)
