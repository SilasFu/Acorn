from __future__ import annotations

from pathlib import Path

import yaml

ACTION_PATH = Path(__file__).parent.parent / ".github" / "actions" / "acorn" / "action.yml"


def test_action_yml_exists():
    assert ACTION_PATH.is_file()


def test_action_yml_valid():
    data = yaml.safe_load(ACTION_PATH.read_text())
    assert data is not None
    assert data["name"] == "Acorn AI Context Check"
    assert "inputs" in data
    assert "mode" in data["inputs"]
    assert "work-dir" in data["inputs"]
    assert data["runs"]["using"] == "composite"


def test_action_modes():
    data = yaml.safe_load(ACTION_PATH.read_text())
    modes = ["sync", "doctor", "fix"]
    for mode in modes:
        assert any(mode in str(step.get("if", "")) for step in data["runs"]["steps"]), f"Missing mode: {mode}"
