from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    src = tmp_path / "project"
    src.mkdir()
    return src


def make_project(base: Path, files: dict[str, str]) -> None:
    for rel_path, content in files.items():
        f = base / rel_path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)


class InputSim:
    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)
        self.idx = 0

    def __call__(self, prompt: str = "") -> Any:
        val = self.answers[self.idx]
        self.idx += 1
        return val
