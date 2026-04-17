from __future__ import annotations

from enum import StrEnum


class ReminderRuntimeState(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"


class ReminderPhase(StrEnum):
    REMINDER = "reminder"
    BREAK = "break"


class VisionDecisionResult(StrEnum):
    USER_LEFT_DESK = "用户已离开电脑前"
    USER_STAYING = "用户未离开电脑前"
    FAILED = "识别失败"
