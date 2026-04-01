from __future__ import annotations

from reminder_client.domain.enums import ReminderPhase, ReminderRuntimeState
from reminder_client.domain.models import Reminder
from reminder_client.services.scheduler import ReminderScheduler


def test_tick_moves_running_reminder_to_break() -> None:
    reminder = Reminder(
        name="久坐提醒",
        reminder_interval_minutes=1,
        break_interval_minutes=5,
        runtime_state=ReminderRuntimeState.RUNNING,
        current_phase=ReminderPhase.REMINDER,
        remaining_seconds=1,
    )

    result = ReminderScheduler().tick(reminder)

    assert result.reminder_triggered is True
    assert result.entered_break is True
    assert reminder.current_phase == ReminderPhase.BREAK
    assert reminder.remaining_seconds == 5 * 60


def test_break_completion_starts_next_cycle() -> None:
    reminder = Reminder(
        name="久坐提醒",
        reminder_interval_minutes=2,
        break_interval_minutes=1,
        runtime_state=ReminderRuntimeState.RUNNING,
        current_phase=ReminderPhase.BREAK,
        remaining_seconds=1,
    )

    result = ReminderScheduler().tick(reminder)

    assert result.entered_next_cycle is True
    assert reminder.current_phase == ReminderPhase.REMINDER
    assert reminder.remaining_seconds == 2 * 60


def test_zero_break_moves_directly_to_next_cycle() -> None:
    reminder = Reminder(
        name="久坐提醒",
        reminder_interval_minutes=2,
        break_interval_minutes=0,
        runtime_state=ReminderRuntimeState.RUNNING,
        current_phase=ReminderPhase.REMINDER,
        remaining_seconds=1,
    )

    result = ReminderScheduler().tick(reminder)

    assert result.reminder_triggered is True
    assert result.entered_next_cycle is True
    assert reminder.current_phase == ReminderPhase.REMINDER
    assert reminder.remaining_seconds == 2 * 60