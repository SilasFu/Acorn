from __future__ import annotations

from acorn.progress import Spinner


def test_spinner_start_stop():
    s = Spinner("testing")
    s.start()
    assert s._running is True
    s.stop()
    assert s._running is False


def test_spinner_context_manager():
    with Spinner("test") as s:
        assert s._running is True
    assert s._running is False
