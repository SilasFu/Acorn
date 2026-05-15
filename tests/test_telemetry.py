from __future__ import annotations

from unittest.mock import patch

from acorn.telemetry import (
    _get_instance_id,
    _get_version,
    is_enabled,
    maybe_prompt,
    set_enabled,
    track,
)


def test_is_enabled_default():
    with patch("acorn.telemetry.load_config", return_value={}):
        assert is_enabled() is False


def test_set_enabled():
    mock_config = {"telemetry_enabled": False}
    with (
        patch("acorn.telemetry.load_config", return_value=mock_config),
        patch("acorn.telemetry.save_config") as mock_save,
    ):
        set_enabled(True)
        assert mock_config["telemetry_enabled"] is True
        mock_save.assert_called_once_with(mock_config)


def test_get_instance_id_creates():
    with (
        patch("acorn.telemetry._INSTANCE_ID_FILE") as mock_file,
        patch("acorn.telemetry.uuid.uuid4", return_value="test-uuid"),
    ):
        mock_file.exists.return_value = False
        mock_file.parent.mkdir.return_value = None
        iid = _get_instance_id()
        assert iid == "test-uuid"


def test_get_instance_id_existing():
    with patch("acorn.telemetry._INSTANCE_ID_FILE") as mock_file:
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "existing-id\n"
        iid = _get_instance_id()
        assert iid == "existing-id"


def test_get_version():
    v = _get_version()
    assert v is not None


def test_track_disabled():
    with patch("acorn.telemetry.is_enabled", return_value=False):
        with patch("acorn.telemetry._send") as mock_send:
            track("test_event")
            mock_send.assert_not_called()


def test_track_enabled():
    with (
        patch("acorn.telemetry.is_enabled", return_value=True),
        patch("acorn.telemetry._send") as mock_send,
    ):
        track("test_event", key="value")
        mock_send.assert_called_once()
        data = mock_send.call_args[0][0]
        assert data["event"] == "test_event"
        assert "instance_id" in data
        assert "properties" in data


def test_maybe_prompt_already_prompted():
    with (
        patch("acorn.telemetry.load_config", return_value={"telemetry_enabled": False}),
        patch("builtins.input") as mock_input,
        patch.dict("os.environ", {}, clear=True),
    ):
        maybe_prompt()
        mock_input.assert_not_called()


def test_maybe_prompt_yes():
    with (
        patch("acorn.telemetry.load_config", return_value={}),
        patch("acorn.telemetry.set_enabled") as mock_set,
        patch("builtins.input", return_value="y"),
        patch.dict("os.environ", {}, clear=True),
    ):
        maybe_prompt()
        mock_set.assert_called_once_with(True)


def test_maybe_prompt_no():
    with (
        patch("acorn.telemetry.load_config", return_value={}),
        patch("acorn.telemetry.set_enabled") as mock_set,
        patch("builtins.input", return_value="n"),
        patch.dict("os.environ", {}, clear=True),
    ):
        maybe_prompt()
        mock_set.assert_called_once_with(False)
