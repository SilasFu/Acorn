from __future__ import annotations

import subprocess
import sys
from pathlib import Path

NPX_INDEX = Path(__file__).parent.parent / "packages" / "acorn-cli" / "index.js"


def _node():
    import shutil
    return shutil.which("node") or "node"


def test_npx_wrapper_finds_acorn(tmp_path: Path):
    result = subprocess.run(
        [_node(), str(NPX_INDEX), "--version"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env={"PATH": "/nonexistent"},
        timeout=10,
    )
    assert result.returncode != 0
    assert "Acorn CLI is not installed" in result.stderr


def test_npx_wrapper_proxies_version():
    bin_dir = Path(__file__).parent.parent / ".venv" / "bin"
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin"}
    result = subprocess.run(
        [_node(), str(NPX_INDEX), "--version"],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "acorn" in result.stdout
