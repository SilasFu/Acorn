from __future__ import annotations

from unittest.mock import patch

from acorn.wizard import WizardOption, WizardStep, _ask, _detect_editor


def test_detect_editor_found():
    with patch("shutil.which", return_value="/usr/bin/cursor"):
        assert _detect_editor() == "cursor"


def test_detect_editor_not_found():
    with patch("shutil.which", return_value=None):
        assert _detect_editor() is None


def test_detect_editor_prefers_order():
    calls = []

    def _which(cmd):
        calls.append(cmd)
        return None

    with patch("shutil.which", side_effect=_which):
        _detect_editor()
    assert calls == ["cursor", "code", "vscode", "idea"]


def test_ask_select_with_default(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    step = WizardStep(key="t", prompt="Pick", input_type="select", options=[WizardOption("A", "a"), WizardOption("B", "b")], default="auto")
    assert _ask(step, "en") == "auto"


def test_ask_confirm_default_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    step = WizardStep(key="t", prompt="?", input_type="confirm", default=True)
    assert _ask(step, "en") is True


def test_ask_confirm_default_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    step = WizardStep(key="t", prompt="?", input_type="confirm", default=False)
    assert _ask(step, "en") is False


def test_ask_text_with_default(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    step = WizardStep(key="t", prompt="Name?", default="my-app")
    assert _ask(step, "en") == "my-app"


def test_ask_text_validator_retry(monkeypatch):
    inputs = iter(["", "valid"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    step = WizardStep(key="t", prompt="Name?", validator=lambda v: len(v) > 0)
    assert _ask(step, "en") == "valid"


def test_ask_zh_prompt(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "val")
    step = WizardStep(key="t", prompt="Name", prompt_zh="名称")
    assert _ask(step, "zh") == "val"


def test_ask_select_invalid_then_valid(monkeypatch):
    inputs = iter(["99", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    step = WizardStep(key="t", prompt="Pick", input_type="select", options=[WizardOption("A", "a")])
    assert _ask(step, "en") == "a"


def test_ask_confirm_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    step = WizardStep(key="t", prompt="?", input_type="confirm")
    assert _ask(step, "en") is True


def test_ask_confirm_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    step = WizardStep(key="t", prompt="?", input_type="confirm", default=True)
    assert _ask(step, "en") is False
