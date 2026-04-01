from __future__ import annotations

from dataclasses import dataclass

from reminder_client.domain.enums import ReminderPhase, ReminderRuntimeState
from reminder_client.domain.models import Reminder


@dataclass(slots=True)
class TickResult:
    reminder_triggered: bool = False
    entered_break: bool = False
    entered_next_cycle: bool = False


class ReminderScheduler:
    def tick(self, reminder: Reminder, seconds: int = 1) -> TickResult:
        if reminder.runtime_state != ReminderRuntimeState.RUNNING or seconds <= 0:
            return TickResult()

        result = TickResult()
        remaining = seconds

        while remaining > 0 and reminder.runtime_state == ReminderRuntimeState.RUNNING:
            if reminder.remaining_seconds > remaining:
                reminder.remaining_seconds -= remaining
                break

            remaining -= reminder.remaining_seconds
            reminder.remaining_seconds = 0

            if reminder.current_phase == ReminderPhase.REMINDER:
                result.reminder_triggered = True
                if reminder.break_interval_minutes == 0:
                    reminder.current_phase = ReminderPhase.REMINDER
                    reminder.remaining_seconds = reminder.initial_seconds_for_phase(ReminderPhase.REMINDER)
                    result.entered_next_cycle = True
                else:
                    reminder.current_phase = ReminderPhase.BREAK
                    reminder.remaining_seconds = reminder.initial_seconds_for_phase(ReminderPhase.BREAK)
                    result.entered_break = True
            else:
                reminder.current_phase = ReminderPhase.REMINDER
                reminder.remaining_seconds = reminder.initial_seconds_for_phase(ReminderPhase.REMINDER)
                result.entered_next_cycle = True

        return result