from __future__ import annotations

from enum import StrEnum


class ReminderRuntimeState(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"


class ReminderPhase(StrEnum):
    REMINDER = "reminder"
    BREAK = "break"

