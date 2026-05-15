from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from acorn.detector import detect_project_type
from acorn.log import info as log_info
from acorn.log import warning as log_warning
from acorn.models import DetectionResult, ProjectType

AI_ENDPOINT = os.environ.get("ACORN_AI_ENDPOINT", "https://api.openai.com/v1/chat/completions")
AI_API_KEY = os.environ.get("ACORN_AI_API_KEY", "")
AI_MAX_FILES = int(os.environ.get("ACORN_AI_MAX_FILES", "20"))


@dataclass
class AnalyzeOptions:
    allow_ai: bool = False
    dry_run: bool = False


@dataclass
class AnalysisResult:
    detection: DetectionResult | None = None
    source: str = "rule"
    ai_suggestion: str | None = None
    ambiguous_matches: list[tuple[ProjectType, str, float]] = field(default_factory=list)


def _get_ambiguous_matches(detection: DetectionResult) -> list[tuple[ProjectType, str, float]]:
    matches = []
    seen = set()
    for ptype, src, score in detection.all_matches:
        key = (ptype.value, src)
        if key not in seen and score < 0.6:
            matches.append((ptype, src, score))
            seen.add(key)
    if detection.project_type != ProjectType.UNKNOWN and detection.confidence < 0.6:
        match_key = (detection.project_type.value, "detected")
        if match_key not in seen:
            matches.append((detection.project_type, "detected", detection.confidence))
    return matches


def _build_prompt(ambiguous: list[tuple[ProjectType, str, float]], project_name: str) -> str:
    lines = [
        f"Analyze the following project: {project_name}",
        "",
        "Ambiguous detection results (project_type, source, confidence):",
    ]
    for ptype, src, score in ambiguous:
        lines.append(f"- {ptype.value} (from {src}, confidence {score:.0%})")
    lines.extend([
        "",
        "Based on the project name and these ambiguous signals, determine the most likely",
        "project type and recommended tech stack. Reply with a single JSON object:",
        '{"project_type": "...", "framework": "...", "reasoning": "..."}',
    ])
    return "\n".join(lines)


def _call_llm(prompt: str) -> str | None:
    if not AI_API_KEY:
        log_warning("ACORN_AI_API_KEY not set — cannot call LLM")
        return None

    import urllib.error as uerr
    import urllib.request as req

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 300,
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}",
    }

    try:
        r = req.Request(AI_ENDPOINT, data=payload, headers=headers, method="POST")
        with req.urlopen(r, timeout=30) as resp:
            body = json.loads(resp.read())
        return body.get("choices", [{}])[0].get("message", {}).get("content", "")
    except (uerr.URLError, OSError, json.JSONDecodeError, KeyError) as e:
        log_warning(f"AI analysis failed: {e}")
        return None


def _confirm(message: str) -> bool:
    try:
        answer = input(f"{message} (y/N): ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def _collect_file_metadata(dir_path: Path, max_files: int = AI_MAX_FILES) -> list[dict[str, Any]]:
    metadata = []
    for f in dir_path.rglob("*"):
        if f.is_file():
            try:
                rel = f.relative_to(dir_path)
            except ValueError:
                continue
            if str(rel).startswith(".acorn") or str(rel).startswith(".git") or str(rel).startswith("__pycache__") or str(rel).startswith("node_modules") or str(rel).startswith("venv") or str(rel).startswith(".venv"):
                continue
            metadata.append({"path": str(rel), "size": f.stat().st_size})
            if len(metadata) >= max_files:
                break
    return metadata


def analyze(dir_path: Path, options: AnalyzeOptions) -> AnalysisResult:
    detection = detect_project_type(dir_path)

    if not options.allow_ai:
        log_info("Rule-based analysis only (use --allow-ai for AI assistance)")
        return AnalysisResult(detection=detection, source="rule")

    ambiguous = _get_ambiguous_matches(detection)
    if not ambiguous:
        log_info("No ambiguous matches — AI analysis not needed")
        return AnalysisResult(detection=detection, source="rule")

    project_name = dir_path.name

    if options.dry_run:
        print(f"\nAI Analysis dry-run for: {project_name}")
        print(f"Would send metadata for files in: {dir_path}")
        print(f"Ambiguous matches: {len(ambiguous)}")
        for ptype, src, score in ambiguous:
            print(f"  - {ptype.value} ({src}, {score:.0%})")
        metadata = _collect_file_metadata(dir_path)
        print(f"Would send metadata for {len(metadata)} file(s):")
        for m in metadata[:5]:
            print(f"  - {m['path']} ({m['size']} bytes)")
        if len(metadata) > 5:
            print(f"  ... and {len(metadata) - 5} more")
        return AnalysisResult(
            detection=detection, source="ai", ambiguous_matches=ambiguous,
        )

    if not _confirm("Use AI to analyze project? File metadata (paths and sizes) will be sent to LLM."):
        log_info("AI analysis declined — falling back to rule-based")
        return AnalysisResult(detection=detection, source="rule")

    metadata = _collect_file_metadata(dir_path)
    prompt = _build_prompt(ambiguous, project_name)
    suggestion = _call_llm(prompt)

    if suggestion:
        print("\nAI Suggestion:")
        print(f"  {suggestion}")
        return AnalysisResult(
            detection=detection, source="ai", ai_suggestion=suggestion,
            ambiguous_matches=ambiguous,
        )

    log_warning("AI analysis failed — falling back to rule-based")
    return AnalysisResult(detection=detection, source="rule")
