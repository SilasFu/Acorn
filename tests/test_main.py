from __future__ import annotations

import sys
from unittest.mock import patch


def test_main_module_entry():
    import acorn.__main__ as main_module
    assert hasattr(main_module, "main")


def test_main_module_runs_via_exec():
    with patch.object(sys, "argv", ["acorn", "--list"]):
        exec(open("src/acorn/__main__.py").read())
