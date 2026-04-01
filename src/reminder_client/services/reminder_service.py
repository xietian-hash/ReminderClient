from __future__ import annotations

from datetime import datetime

from reminder_client.domain.enums import ReminderRuntimeState
from reminder_client.domain.models import Reminder, normalize_reminder_name
from reminder_client.services.audio_service import AudioService
from reminder_client.services.notification_service import NotificationService
from reminder_client.services.scheduler import ReminderScheduler
from reminder_client.storage.reminder_repository import ReminderRepository


class ReminderService:
    def __init__(
        self,
        repository: ReminderRepository,
        scheduler: ReminderScheduler | None = None,
        notification_service: NotificationService | None = None,
        audio_service: AudioService | None = None,
    ) -> None:
        self.repository = repository
        self.scheduler = scheduler or ReminderScheduler()
        self.notification_service = notification_service
        self.audio_service = audio_service

    def list_reminders(self) -> list[Reminder]:
        return self.repository.list_all()

    def get_reminder(self, reminder_id: str) -> Reminder:
        return self._get_required(reminder_id)

    def create_reminder(
        self,
        *,
        name: str,
        reminder_interval_minutes: int,
        break_interval_minutes: int,
        music_path: str | None = None,
        enabled: bool = True,
    ) -> Reminder:
        reminder = Reminder(
            name=normalize_reminder_name(name),
            reminder_interval_minutes=int(reminder_interval_minutes),
            break_interval_minutes=int(break_interval_minutes),
            music_path=music_path or None,
            enabled=enabled,
        )
        return self.repository.add(reminder)

    def start(self, reminder_id: str) -> Reminder:
        reminder = self._get_required(reminder_id)
        reminder.runtime_state = ReminderRuntimeState.RUNNING
        reminder.updated_at = datetime.now()
        return self.repository.update(reminder)

    def pause(self, reminder_id: str) -> Reminder:
        reminder = self._get_required(reminder_id)
        reminder.runtime_state = ReminderRuntimeState.PAUSED
        reminder.updated_at = datetime.now()
        return self.repository.update(reminder)

    def reset(self, reminder_id: str) -> Reminder:
        reminder = self._get_required(reminder_id)
        reminder.reset_runtime()
        return self.repository.update(reminder)

    def delete_reminder(self, reminder_id: str) -> None:
        self._get_required(reminder_id)
        self.repository.delete(reminder_id)

    def update_reminder(self, reminder_id: str, **changes: object) -> Reminder:
        reminder = self._get_required(reminder_id)
        was_running = reminder.runtime_state == ReminderRuntimeState.RUNNING

        if 'name' in changes:
            reminder.name = normalize_reminder_name(str(changes['name']))
        if 'reminder_interval_minutes' in changes:
            reminder.reminder_interval_minutes = int(changes['reminder_interval_minutes'])
        if 'break_interval_minutes' in changes:
            reminder.break_interval_minutes = int(changes['break_interval_minutes'])
        if 'music_path' in changes:
            reminder.music_path = str(changes['music_path']) if changes['music_path'] else None
        if 'enabled' in changes:
            reminder.enabled = bool(changes['enabled'])

        reminder.__post_init__()
        if was_running:
            reminder.reset_runtime()
        reminder.updated_at = datetime.now()
        return self.repository.update(reminder)

    def start_all(self) -> list[Reminder]:
        return [self.start(reminder.id) for reminder in self.list_reminders() if reminder.enabled]

    def pause_all(self) -> list[Reminder]:
        return [
            self.pause(reminder.id)
            for reminder in self.list_reminders()
            if reminder.runtime_state == ReminderRuntimeState.RUNNING
        ]

    def reset_all(self) -> list[Reminder]:
        return [self.reset(reminder.id) for reminder in self.list_reminders()]

    def prepare_for_exit(self) -> list[Reminder]:
        reminders = self.reset_all()
        if self.audio_service is not None:
            self.audio_service.stop()
        return reminders

    def tick(self, reminder_id: str, seconds: int = 1) -> Reminder:
        reminder = self._get_required(reminder_id)
        result = self.scheduler.tick(reminder, seconds)

        if result.reminder_triggered and self.notification_service is not None:
            try:
                self.notification_service.notify_reminder_triggered(reminder)
            except Exception:
                pass
        if result.reminder_triggered and self.audio_service is not None:
            try:
                self.audio_service.play(reminder.music_path)
            except Exception:
                pass

        reminder.updated_at = datetime.now()
        return self.repository.update(reminder)

    def _get_required(self, reminder_id: str) -> Reminder:
        reminder = self.repository.get_by_id(reminder_id)
        if reminder is None:
            raise KeyError(f'未找到提醒: {reminder_id}')
        return reminder
