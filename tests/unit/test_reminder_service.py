from __future__ import annotations

import pytest

from reminder_client.domain.enums import ReminderPhase, ReminderRuntimeState, VisionDecisionResult
from reminder_client.domain.models import AppSettings, Reminder, ensure_unique_name, normalize_reminder_name
from reminder_client.services.audio_service import AudioService
from reminder_client.services.notification_service import NotificationService
from reminder_client.services.reminder_service import ReminderService
from reminder_client.storage.database import Database
from reminder_client.storage.reminder_repository import ReminderRepository


def test_reminder_name_is_required() -> None:
    with pytest.raises(ValueError, match='提醒名称不能为空'):
        Reminder(name='   ', reminder_interval_minutes=30, break_interval_minutes=5)


def test_normalize_reminder_name_trims_whitespace() -> None:
    assert normalize_reminder_name(' 久坐提醒 ') == '久坐提醒'


def test_reminder_name_must_be_unique_after_trimming() -> None:
    with pytest.raises(ValueError, match='提醒名称已存在'):
        ensure_unique_name(' 久坐提醒 ', ['久坐提醒'])


def test_reminder_interval_must_be_greater_than_zero() -> None:
    with pytest.raises(ValueError, match='提醒间隔必须大于0'):
        Reminder(name='久坐提醒', reminder_interval_minutes=0, break_interval_minutes=5)


def test_break_interval_cannot_be_negative() -> None:
    with pytest.raises(ValueError, match='休息间隔不能小于0'):
        Reminder(name='久坐提醒', reminder_interval_minutes=30, break_interval_minutes=-1)


def test_reset_runtime_sets_not_started_and_reminder_initial_seconds() -> None:
    reminder = Reminder(
        name='久坐提醒',
        reminder_interval_minutes=45,
        break_interval_minutes=5,
        current_phase=ReminderPhase.BREAK,
        runtime_state=ReminderRuntimeState.RUNNING,
        remaining_seconds=10,
    )

    reminder.reset_runtime()

    assert reminder.runtime_state == ReminderRuntimeState.NOT_STARTED
    assert reminder.current_phase == ReminderPhase.REMINDER
    assert reminder.remaining_seconds == 45 * 60


class DummyNotificationService(NotificationService):
    def __init__(self) -> None:
        self.triggered_for: list[str] = []

    def notify_reminder_triggered(self, reminder: Reminder) -> None:
        self.triggered_for.append(reminder.id)


class DummyAudioService(AudioService):
    def __init__(self) -> None:
        super().__init__(default_sound_path='default.wav')
        self.played: list[str | None] = []
        self.stopped = False

    def play(self, custom_sound_path: str | None) -> str | None:
        resolved = super().play(custom_sound_path)
        self.played.append(resolved)
        return resolved

    def stop(self) -> None:
        self.stopped = True


@pytest.fixture()
def reminder_service(tmp_path):
    database = Database(tmp_path / 'reminder.db')
    database.initialize()
    repository = ReminderRepository(database)
    notification_service = DummyNotificationService()
    audio_service = DummyAudioService()
    service = ReminderService(
        repository=repository,
        notification_service=notification_service,
        audio_service=audio_service,
    )
    return service, repository, notification_service, audio_service


def test_start_sets_reminder_to_running(reminder_service) -> None:
    service, repository, _, _ = reminder_service
    reminder = repository.add(
        Reminder(name='久坐提醒', reminder_interval_minutes=45, break_interval_minutes=5)
    )

    updated = service.start(reminder.id)

    assert updated.runtime_state == ReminderRuntimeState.RUNNING


def test_pause_preserves_remaining_seconds(reminder_service) -> None:
    service, repository, _, _ = reminder_service
    reminder = repository.add(
        Reminder(
            name='久坐提醒',
            reminder_interval_minutes=45,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.RUNNING,
            remaining_seconds=100,
        )
    )

    updated = service.pause(reminder.id)

    assert updated.runtime_state == ReminderRuntimeState.PAUSED
    assert updated.remaining_seconds == 100


def test_reset_returns_current_phase_initial_seconds(reminder_service) -> None:
    service, repository, _, _ = reminder_service
    reminder = repository.add(
        Reminder(
            name='久坐提醒',
            reminder_interval_minutes=45,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.RUNNING,
            current_phase=ReminderPhase.BREAK,
            remaining_seconds=12,
        )
    )

    updated = service.reset(reminder.id)

    assert updated.runtime_state == ReminderRuntimeState.NOT_STARTED
    assert updated.current_phase == ReminderPhase.REMINDER
    assert updated.remaining_seconds == 45 * 60


def test_edit_running_reminder_resets_to_not_started(reminder_service) -> None:
    service, repository, _, _ = reminder_service
    reminder = repository.add(
        Reminder(
            name='久坐提醒',
            reminder_interval_minutes=45,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.RUNNING,
            remaining_seconds=10,
        )
    )

    updated = service.update_reminder(
        reminder.id,
        name='滴眼药水',
        reminder_interval_minutes=120,
        break_interval_minutes=1,
    )

    assert updated.name == '滴眼药水'
    assert updated.runtime_state == ReminderRuntimeState.NOT_STARTED
    assert updated.remaining_seconds == 120 * 60


def test_tick_triggers_notification_and_audio(reminder_service) -> None:
    service, repository, notification_service, audio_service = reminder_service
    reminder = repository.add(
        Reminder(
            name='久坐提醒',
            reminder_interval_minutes=1,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.RUNNING,
            remaining_seconds=1,
            notification_enabled=True,
            audio_enabled=True,
        )
    )

    updated = service.tick(reminder.id)

    assert updated.current_phase == ReminderPhase.BREAK
    assert reminder.id in notification_service.triggered_for
    assert audio_service.played == [None]


def test_batch_start_pause_and_reset(reminder_service) -> None:
    service, repository, _, _ = reminder_service
    repository.add(Reminder(name='久坐提醒', reminder_interval_minutes=45, break_interval_minutes=5))
    repository.add(Reminder(name='滴眼药水', reminder_interval_minutes=120, break_interval_minutes=1))

    started = service.start_all()
    paused = service.pause_all()
    reset = service.reset_all()

    assert {item.runtime_state for item in started} == {ReminderRuntimeState.RUNNING}
    assert len(paused) == 2
    assert {item.runtime_state for item in reset} == {ReminderRuntimeState.NOT_STARTED}


def test_prepare_for_exit_resets_all_and_stops_audio(reminder_service) -> None:
    service, repository, _, audio_service = reminder_service
    repository.add(
        Reminder(name='久坐提醒', reminder_interval_minutes=45, break_interval_minutes=5, runtime_state=ReminderRuntimeState.RUNNING)
    )
    repository.add(
        Reminder(name='滴眼药水', reminder_interval_minutes=120, break_interval_minutes=1, runtime_state=ReminderRuntimeState.RUNNING)
    )

    reminders = service.prepare_for_exit()

    assert len(reminders) == 2
    assert {item.runtime_state for item in reminders} == {ReminderRuntimeState.NOT_STARTED}
    assert audio_service.stopped is True
class FailingNotificationService(NotificationService):
    def notify_reminder_triggered(self, reminder: Reminder) -> None:
        raise RuntimeError('通知失败')


def test_tick_still_plays_audio_when_notification_fails(tmp_path) -> None:
    database = Database(tmp_path / 'reminder.db')
    database.initialize()
    repository = ReminderRepository(database)
    audio_service = DummyAudioService()
    service = ReminderService(
        repository=repository,
        notification_service=FailingNotificationService(),
        audio_service=audio_service,
    )
    sound = tmp_path / 'sound.wav'
    sound.write_text('sound', encoding='utf-8')
    reminder = repository.add(
        Reminder(
            name='久坐提醒',
            reminder_interval_minutes=1,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.RUNNING,
            remaining_seconds=1,
            music_path=str(sound),
            notification_enabled=True,
            audio_enabled=True,
        )
    )

    updated = service.tick(reminder.id)

    assert updated.current_phase == ReminderPhase.BREAK
    assert audio_service.played == [str(sound)]

def test_delete_reminder_removes_existing_record(reminder_service) -> None:
    service, repository, _, _ = reminder_service
    reminder = repository.add(
        Reminder(name='delete-service', reminder_interval_minutes=45, break_interval_minutes=5)
    )

    service.delete_reminder(reminder.id)

    assert repository.get_by_id(reminder.id) is None


def test_delete_reminder_raises_for_missing_id(reminder_service) -> None:
    service, _, _, _ = reminder_service

    with pytest.raises(KeyError):
        service.delete_reminder('missing-id')


class FakeVisualDecisionScheduler:
    def __init__(self) -> None:
        self.scheduled: list[tuple[str, int]] = []
        self.cancelled: list[str] = []

    def schedule(self, reminder_id: str, delay_ms: int, callback) -> None:
        self.scheduled.append((reminder_id, delay_ms))

    def cancel(self, reminder_id: str) -> None:
        self.cancelled.append(reminder_id)


class FakeSettingsRepository:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings()

    def get(self) -> AppSettings:
        return self.settings


class FakeVisionDecisionService:
    def __init__(self, result=VisionDecisionResult.USER_STAYING) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def evaluate(self, reminder: Reminder, settings: AppSettings, *, play_audio: bool = True):
        self.calls.append((reminder.id, settings.ark_base_url))
        return self.result


@pytest.fixture()
def visual_reminder_service(tmp_path):
    database = Database(tmp_path / 'visual-reminder.db')
    database.initialize()
    repository = ReminderRepository(database)
    scheduler = FakeVisualDecisionScheduler()
    settings_repository = FakeSettingsRepository(
        AppSettings(
            ark_base_url='https://ark.cn-beijing.volces.com/api/v3',
            ark_api_key='test-key',
            ark_model_name='doubao-seed-2-0-mini-260215',
        )
    )
    vision_service = FakeVisionDecisionService()
    audio_service = DummyAudioService()
    service = ReminderService(
        repository=repository,
        settings_repository=settings_repository,
        vision_decision_service=vision_service,
        visual_decision_scheduler=scheduler,
        audio_service=audio_service,
    )
    return service, repository, scheduler, settings_repository, vision_service, audio_service


def test_tick_schedules_visual_decision_when_enabled(visual_reminder_service) -> None:
    service, repository, scheduler, _, _, _ = visual_reminder_service
    reminder = repository.add(
        Reminder(
            name='视觉提醒',
            reminder_interval_minutes=1,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.RUNNING,
            remaining_seconds=1,
            visual_reminder_enabled=True,
        )
    )

    service.tick(reminder.id)

    assert scheduler.scheduled == [(reminder.id, 60_000)]


def test_reset_cancels_pending_visual_decision(visual_reminder_service) -> None:
    service, repository, scheduler, _, _, _ = visual_reminder_service
    reminder = repository.add(
        Reminder(
            name='视觉提醒',
            reminder_interval_minutes=1,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.RUNNING,
            remaining_seconds=1,
            visual_reminder_enabled=True,
        )
    )

    service.tick(reminder.id)
    service.reset(reminder.id)

    assert reminder.id in scheduler.cancelled


def test_test_visual_decision_uses_current_settings(visual_reminder_service) -> None:
    service, _, _, _, vision_service, _ = visual_reminder_service

    result = service.test_visual_decision(
        {
            'name': '视觉提醒',
            'reminder_interval_minutes': 1,
            'break_interval_minutes': 5,
            'visual_reminder_enabled': True,
            'visual_music_path': r'C:\audio\visual.mp3',
            'enabled': True,
        }
    )

    assert result == VisionDecisionResult.USER_STAYING
    assert len(vision_service.calls) == 1
