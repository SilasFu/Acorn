from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from acorn.analyzer import (
    AnalyzeOptions,
    _build_prompt,
    _call_llm,
    _collect_file_metadata,
    _confirm,
    _get_ambiguous_matches,
    analyze,
)
from acorn.models import DetectionResult, ProjectType


def test_get_ambiguous_matches_empty():
    d = DetectionResult(project_type=ProjectType.NODE, confidence=0.9)
    assert _get_ambiguous_matches(d) == []


def test_get_ambiguous_matches_low_confidence():
    d = DetectionResult(
        project_type=ProjectType.NODE, confidence=0.4,
        all_matches=[
            (ProjectType.NODE, "package.json", 0.4),
            (ProjectType.PYTHON, "setup.py", 0.3),
        ],
    )
    matches = _get_ambiguous_matches(d)
    assert len(matches) >= 1
    types = [m[0] for m in matches]
    assert ProjectType.NODE in types


def test_build_prompt():
    ambiguous = [(ProjectType.NODE, "package.json", 0.5), (ProjectType.PYTHON, "setup.py", 0.3)]
    prompt = _build_prompt(ambiguous, "my-project")
    assert "my-project" in prompt
    assert "node" in prompt
    assert "python" in prompt
    assert "JSON" in prompt


def test_call_llm_no_api_key():
    with patch("acorn.analyzer.AI_API_KEY", ""):
        result = _call_llm("test prompt")
    assert result is None


def test_call_llm_api_error():
    with (
        patch("acorn.analyzer.AI_API_KEY", "test-key"),
        patch("acorn.analyzer.AI_ENDPOINT", "https://invalid.endpoint/test"),
    ):
        result = _call_llm("test prompt")
    assert result is None


def test_confirm_yes():
    with patch("builtins.input", return_value="y"):
        assert _confirm("test?") is True


def test_confirm_no():
    with patch("builtins.input", return_value="n"):
        assert _confirm("test?") is False


def test_confirm_default():
    with patch("builtins.input", return_value=""):
        assert _confirm("test?") is False


def test_collect_file_metadata(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "README.md").write_text("# Project")
    meta = _collect_file_metadata(tmp_path, max_files=10)
    paths = [m["path"] for m in meta]
    assert "main.py" in paths
    assert "README.md" in paths
    for m in meta:
        assert "path" in m
        assert "size" in m


def test_collect_file_metadata_ignores_dirs(tmp_path: Path):
    (tmp_path / "main.py").write_text("x")
    ignored = tmp_path / ".acorn" / "config.yaml"
    ignored.parent.mkdir()
    ignored.write_text("x")
    meta = _collect_file_metadata(tmp_path)
    paths = [m["path"] for m in meta]
    assert "main.py" in paths
    assert all(not p.startswith(".acorn") for p in paths)


def test_collect_file_metadata_respects_max(tmp_path: Path):
    for i in range(5):
        (tmp_path / f"file{i}.txt").write_text("x")
    meta = _collect_file_metadata(tmp_path, max_files=3)
    assert len(meta) <= 3


def test_analyze_rule_only(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    options = AnalyzeOptions(allow_ai=False)
    result = analyze(tmp_path, options)
    assert result.source == "rule"
    assert result.detection is not None


def test_analyze_ai_declined(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    options = AnalyzeOptions(allow_ai=True)
    with patch("acorn.analyzer._confirm", return_value=False):
        result = analyze(tmp_path, options)
    assert result.source == "rule"


def test_analyze_ai_dry_run(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    options = AnalyzeOptions(allow_ai=True, dry_run=True)
    result = analyze(tmp_path, options)
    assert result.source == "ai"


def test_analyze_ai_success(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "test", "dependencies": {"express": "^4.0.0"}}')
    options = AnalyzeOptions(allow_ai=True, dry_run=False)
    with (
        patch("acorn.analyzer._confirm", return_value=True),
        patch("acorn.analyzer._call_llm", return_value='{"project_type": "node"}'),
    ):
        result = analyze(tmp_path, options)
    assert result.source == "ai"
    assert result.ai_suggestion is not None
