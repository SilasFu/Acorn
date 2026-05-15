from __future__ import annotations

from acorn.json_output import print_json


def test_print_json(capsys):
    print_json({"a": 1, "b": [2, 3]})
    captured = capsys.readouterr()
    import json
    assert json.loads(captured.out) == {"a": 1, "b": [2, 3]}


def test_print_json_ensure_ascii_false(capsys):
    print_json({"msg": "你好"})
    captured = capsys.readouterr()
    assert "你好" in captured.out
