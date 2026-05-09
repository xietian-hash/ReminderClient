from __future__ import annotations

from datetime import datetime

from reminder_client.domain.enums import ReminderRuntimeState, VisionDecisionResult
from reminder_client.domain.models import Reminder, normalize_reminder_name
from reminder_client.services.audio_service import AudioService
from reminder_client.services.notification_service import NotificationService
from reminder_client.services.scheduler import ReminderScheduler
from reminder_client.services.visual_decision_scheduler import QtVisualDecisionScheduler
from reminder_client.services.vision_decision_service import VisionDecisionService
from reminder_client.storage.reminder_repository import ReminderRepository
from reminder_client.storage.settings_repository import SettingsRepository


class ReminderService:
    def __init__(
        self,
        repository: ReminderRepository,
        scheduler: ReminderScheduler | None = None,
        notification_service: NotificationService | None = None,
        audio_service: AudioService | None = None,
        settings_repository: SettingsRepository | None = None,
        vision_decision_service: VisionDecisionService | None = None,
        visual_decision_scheduler: QtVisualDecisionScheduler | None = None,
    ) -> None:
        self.repository = repository
        self.scheduler = scheduler or ReminderScheduler()
        self.notification_service = notification_service
        self.audio_service = audio_service
        self.settings_repository = settings_repository
        self.vision_decision_service = vision_decision_service
        self.visual_decision_scheduler = visual_decision_scheduler or QtVisualDecisionScheduler()
        self._pending_visual_decisions: set[str] = set()

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
        visual_reminder_enabled: bool = False,
        visual_music_path: str | None = None,
        enabled: bool = True,
    ) -> Reminder:
        reminder = Reminder(
            name=normalize_reminder_name(name),
            reminder_interval_minutes=int(reminder_interval_minutes),
            break_interval_minutes=int(break_interval_minutes),
            music_path=music_path or None,
            visual_reminder_enabled=bool(visual_reminder_enabled),
            visual_music_path=visual_music_path or None,
            enabled=enabled,
        )
        return self.repository.add(reminder)

    def start(self, reminder_id: str) -> Reminder:
        reminder = self._get_required(reminder_id)
        reminder.runtime_state = ReminderRuntimeState.RUNNING
        reminder.updated_at = datetime.now()
        return self.repository.update(reminder)

    def pause(self, reminder_id: str) -> Reminder:
        self.cancel_visual_decision(reminder_id)
        reminder = self._get_required(reminder_id)
        reminder.runtime_state = ReminderRuntimeState.PAUSED
        reminder.updated_at = datetime.now()
        return self.repository.update(reminder)

    def reset(self, reminder_id: str) -> Reminder:
        self.cancel_visual_decision(reminder_id)
        reminder = self._get_required(reminder_id)
        reminder.reset_runtime()
        reminder.dnd_paused = False
        return self.repository.update(reminder)

    def reset_for_dnd(self, reminder_id: str) -> Reminder:
        """重置运行中的提醒并标记为由勿扰触发，退出勿扰时可精确恢复。"""
        self.cancel_visual_decision(reminder_id)
        reminder = self._get_required(reminder_id)
        reminder.reset_runtime()
        reminder.dnd_paused = True
        return self.repository.update(reminder)

    def start_from_dnd(self, reminder_id: str) -> Reminder:
        """启动被勿扰标记的提醒并清除标记；若已运行则仅清除标记。"""
        reminder = self._get_required(reminder_id)
        reminder.dnd_paused = False
        if reminder.runtime_state != ReminderRuntimeState.RUNNING:
            reminder.runtime_state = ReminderRuntimeState.RUNNING
        reminder.updated_at = datetime.now()
        return self.repository.update(reminder)

    def delete_reminder(self, reminder_id: str) -> None:
        self.cancel_visual_decision(reminder_id)
        self._get_required(reminder_id)
        self.repository.delete(reminder_id)

    def update_reminder(self, reminder_id: str, **changes: object) -> Reminder:
        self.cancel_visual_decision(reminder_id)
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
        if 'visual_reminder_enabled' in changes:
            reminder.visual_reminder_enabled = bool(changes['visual_reminder_enabled'])
        if 'visual_music_path' in changes:
            reminder.visual_music_path = (
                str(changes['visual_music_path']) if changes['visual_music_path'] else None
            )
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
        self._pending_visual_decisions.clear()
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
        if (
            result.reminder_triggered
            and reminder.visual_reminder_enabled
            and self.settings_repository is not None
            and self.vision_decision_service is not None
        ):
            self.schedule_visual_decision(reminder.id)

        reminder.updated_at = datetime.now()
        return self.repository.update(reminder)

    def schedule_visual_decision(self, reminder_id: str, delay_ms: int = 60_000) -> None:
        reminder = self._get_required(reminder_id)
        if not reminder.visual_reminder_enabled:
            return
        if self.settings_repository is None or self.vision_decision_service is None:
            return

        self.cancel_visual_decision(reminder_id)
        self._pending_visual_decisions.add(reminder_id)
        self.visual_decision_scheduler.schedule(
            reminder_id,
            delay_ms,
            lambda: self._run_visual_decision(reminder_id),
        )

    def cancel_visual_decision(self, reminder_id: str) -> None:
        self._pending_visual_decisions.discard(reminder_id)
        if self.visual_decision_scheduler is not None:
            try:
                self.visual_decision_scheduler.cancel(reminder_id)
            except Exception:
                pass

    def has_pending_visual_decision(self, reminder_id: str) -> bool:
        return reminder_id in self._pending_visual_decisions

    def test_visual_decision(self, payload: dict[str, object]) -> VisionDecisionResult:
        if self.settings_repository is None or self.vision_decision_service is None:
            raise RuntimeError('当前未配置视觉识别服务')

        reminder = Reminder(
            name=str(payload.get('name', '视觉提醒测试')),
            reminder_interval_minutes=int(payload.get('reminder_interval_minutes', 1)),
            break_interval_minutes=int(payload.get('break_interval_minutes', 0)),
            music_path=str(payload['music_path']) if payload.get('music_path') else None,
            visual_reminder_enabled=bool(payload.get('visual_reminder_enabled', True)),
            visual_music_path=str(payload['visual_music_path']) if payload.get('visual_music_path') else None,
            enabled=bool(payload.get('enabled', True)),
        )
        settings = self.settings_repository.get()
        return self.vision_decision_service.evaluate(reminder, settings, play_audio=True)

    def _run_visual_decision(self, reminder_id: str) -> None:
        self._pending_visual_decisions.discard(reminder_id)
        if self.settings_repository is None or self.vision_decision_service is None:
            return

        reminder = self.repository.get_by_id(reminder_id)
        if reminder is None or not reminder.visual_reminder_enabled:
            return

        try:
            settings = self.settings_repository.get()
            self.vision_decision_service.evaluate(reminder, settings, play_audio=True)
        except Exception:
            return

    def _get_required(self, reminder_id: str) -> Reminder:
        reminder = self.repository.get_by_id(reminder_id)
        if reminder is None:
            raise KeyError(f'未找到提醒 {reminder_id}')
        return reminder
