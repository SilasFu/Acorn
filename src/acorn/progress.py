from __future__ import annotations

import itertools
import sys
import threading
import time


class Spinner:
    def __init__(self, message: str = "", delay: float = 0.1) -> None:
        self.spinner = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
        self.delay = delay
        self.message = message
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        while self._running:
            sys.stdout.write(f"\r{next(self.spinner)} {self.message}")
            sys.stdout.flush()
            time.sleep(self.delay)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()

    def __enter__(self) -> Spinner:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
