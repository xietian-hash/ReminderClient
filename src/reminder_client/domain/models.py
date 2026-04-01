from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable
from uuid import uuid4

from reminder_client.domain.enums import ReminderPhase, ReminderRuntimeState


def normalize_reminder_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValueError('提醒名称不能为空')
    if len(normalized) > 50:
        raise ValueError('提醒名称长度不能超过50个字符')
    return normalized


def ensure_unique_name(name: str, existing_names: Iterable[str]) -> None:
    normalized = normalize_reminder_name(name)
    normalized_existing = {normalize_reminder_name(item) for item in existing_names}
    if normalized in normalized_existing:
        raise ValueError('提醒名称已存在，请重新输入')


def _now() -> datetime:
    return datetime.now()


@dataclass(slots=True)
class Reminder:
    name: str
    reminder_interval_minutes: int
    break_interval_minutes: int
    music_path: str | None = None
    enabled: bool = True
    runtime_state: ReminderRuntimeState = ReminderRuntimeState.NOT_STARTED
    current_phase: ReminderPhase = ReminderPhase.REMINDER
    remaining_seconds: int | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.name = normalize_reminder_name(self.name)
        if self.reminder_interval_minutes <= 0:
            raise ValueError('提醒间隔必须大于0')
        if self.break_interval_minutes < 0:
            raise ValueError('休息间隔不能小于0')
        if self.remaining_seconds is None:
            self.remaining_seconds = self.initial_seconds_for_phase(self.current_phase)

    def initial_seconds_for_phase(self, phase: ReminderPhase) -> int:
        if phase == ReminderPhase.REMINDER:
            return self.reminder_interval_minutes * 60
        return self.break_interval_minutes * 60

    def reset_runtime(self) -> None:
        self.current_phase = ReminderPhase.REMINDER
        self.remaining_seconds = self.initial_seconds_for_phase(ReminderPhase.REMINDER)
        self.runtime_state = ReminderRuntimeState.NOT_STARTED
        self.updated_at = _now()


@dataclass(slots=True)
class AppSettings:
    launch_at_startup: bool = False
    auto_remind_on_launch: bool = False
    updated_at: datetime = field(default_factory=_now)