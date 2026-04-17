from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer


class QtVisualDecisionScheduler:
    def __init__(self) -> None:
        self._timers: dict[str, QTimer] = {}

    def schedule(self, reminder_id: str, delay_ms: int, callback: Callable[[], None]) -> None:
        self.cancel(reminder_id)
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._fire(reminder_id, callback))
        self._timers[reminder_id] = timer
        timer.start(delay_ms)

    def cancel(self, reminder_id: str) -> None:
        timer = self._timers.pop(reminder_id, None)
        if timer is None:
            return
        timer.stop()
        timer.deleteLater()

    def _fire(self, reminder_id: str, callback: Callable[[], None]) -> None:
        timer = self._timers.pop(reminder_id, None)
        if timer is not None:
            timer.deleteLater()
        callback()
