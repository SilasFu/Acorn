from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from acorn.commands.clean import cmd_clean


def test_clean_nonexistent_dir():
    args = type("args", (), {"dir": "/nonexistent", "all": False, "keep_templates": False, "dry_run": False})()
    rc = cmd_clean(args)
    assert rc != 0


def test_clean_no_lock(tmp_path):
    args = type("args", (), {"dir": str(tmp_path), "all": False, "keep_templates": False, "dry_run": False})()
    rc = cmd_clean(args)
    assert rc != 0


def _save_lock(path: Path, files: list[str]) -> None:
    from acorn.config import save_project_lock
    lock_dir = path / ".acorn"
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / "lock.yaml").write_text(f"files:\n" + "\n".join(f"  - {f}" for f in files))


def test_clean_with_lock(tmp_path):
    _save_lock(tmp_path, ["Dockerfile", ".gitignore"])
    (tmp_path / "Dockerfile").write_text("content")
    (tmp_path / ".gitignore").write_text("content")
    args = type("args", (), {"dir": str(tmp_path), "all": False, "keep_templates": False, "dry_run": False})()
    rc = cmd_clean(args)
    assert rc == 0
    assert not (tmp_path / "Dockerfile").exists()


def test_clean_dry_run(tmp_path):
    _save_lock(tmp_path, ["Dockerfile"])
    (tmp_path / "Dockerfile").write_text("content")
    args = type("args", (), {"dir": str(tmp_path), "all": False, "keep_templates": False, "dry_run": True})()
    rc = cmd_clean(args)
    assert rc == 0
    assert (tmp_path / "Dockerfile").exists()


def test_clean_all(tmp_path):
    (tmp_path / ".acorn").mkdir()
    (tmp_path / ".acorn" / "config.yaml").write_text("key: val")
    args = type("args", (), {"dir": str(tmp_path), "all": True, "keep_templates": False, "dry_run": False})()
    rc = cmd_clean(args)
    assert rc == 0
    assert not (tmp_path / ".acorn").exists()


def test_clean_all_dry_run(tmp_path):
    (tmp_path / ".acorn").mkdir()
    args = type("args", (), {"dir": str(tmp_path), "all": True, "keep_templates": False, "dry_run": True})()
    rc = cmd_clean(args)
    assert rc == 0
    assert (tmp_path / ".acorn").exists()


def test_clean_all_keep_templates(tmp_path):
    (tmp_path / ".acorn").mkdir()
    (tmp_path / ".acorn" / "config.yaml").write_text("key: val")
    args = type("args", (), {"dir": str(tmp_path), "all": True, "keep_templates": True, "dry_run": False})()
    rc = cmd_clean(args)
    assert rc == 0


def test_clean_with_lock_partial_removal(tmp_path):
    _save_lock(tmp_path, ["Dockerfile", ".gitignore"])
    (tmp_path / "Dockerfile").write_text("content")
    args = type("args", (), {"dir": str(tmp_path), "all": False, "keep_templates": False, "dry_run": False})()
    rc = cmd_clean(args)
    assert rc == 0
    assert not (tmp_path / "Dockerfile").exists()
