from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from reminder_client.domain.enums import ReminderRuntimeState
from reminder_client.domain.models import Reminder
from reminder_client.services.reminder_service import ReminderService
from reminder_client.storage.database import Database
from reminder_client.storage.reminder_repository import ReminderRepository
from reminder_client.storage.settings_repository import SettingsRepository
from reminder_client.ui.reminder_dialog import ReminderDialog
from reminder_client.ui.settings_dialog import SettingsDialog


class FakeAutostartService:
    def __init__(self) -> None:
        self.enabled = False
        self.enable_calls = 0
        self.disable_calls = 0

    def enable(self) -> None:
        self.enabled = True
        self.enable_calls += 1

    def disable(self) -> None:
        self.enabled = False
        self.disable_calls += 1


def build_reminder_service(tmp_path):
    database = Database(tmp_path / 'reminder.db')
    database.initialize()
    repository = ReminderRepository(database)
    service = ReminderService(repository=repository)
    return service, repository, database


def test_reminder_dialog_blocks_empty_name(qtbot, tmp_path) -> None:
    service, repository, _ = build_reminder_service(tmp_path)
    dialog = ReminderDialog(service)
    qtbot.addWidget(dialog)

    dialog.name_input.setText('   ')
    qtbot.mouseClick(dialog.save_button, Qt.LeftButton)

    assert '提醒名称不能为空' in dialog.error_label.text()
    assert repository.list_all() == []


def test_reminder_dialog_creates_reminder(qtbot, tmp_path) -> None:
    service, repository, _ = build_reminder_service(tmp_path)
    dialog = ReminderDialog(service)
    qtbot.addWidget(dialog)

    dialog.name_input.setText('久坐提醒')
    dialog.reminder_interval_input.setValue(45)
    dialog.break_interval_input.setValue(5)
    qtbot.mouseClick(dialog.save_button, Qt.LeftButton)

    saved = repository.list_all()
    assert dialog.result() == int(QDialog.DialogCode.Accepted)
    assert len(saved) == 1
    assert saved[0].name == '久坐提醒'


def test_edit_running_reminder_resets_to_not_started(qtbot, tmp_path) -> None:
    service, repository, _ = build_reminder_service(tmp_path)
    reminder = repository.add(
        Reminder(
            name='久坐提醒',
            reminder_interval_minutes=45,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.RUNNING,
            remaining_seconds=10,
        )
    )
    dialog = ReminderDialog(service, reminder_id=reminder.id)
    qtbot.addWidget(dialog)

    dialog.name_input.setText('滴眼药水')
    dialog.reminder_interval_input.setValue(120)
    dialog.break_interval_input.setValue(1)
    qtbot.mouseClick(dialog.save_button, Qt.LeftButton)

    updated = repository.get_by_id(reminder.id)
    assert updated is not None
    assert updated.name == '滴眼药水'
    assert updated.runtime_state == ReminderRuntimeState.NOT_STARTED
    assert updated.remaining_seconds == 120 * 60


def test_settings_dialog_updates_autostart(qtbot, tmp_path) -> None:
    _, _, database = build_reminder_service(tmp_path)
    settings_repository = SettingsRepository(database)
    autostart_service = FakeAutostartService()
    dialog = SettingsDialog(settings_repository, autostart_service)
    qtbot.addWidget(dialog)

    dialog.autostart_checkbox.setChecked(True)
    qtbot.mouseClick(dialog.save_button, Qt.LeftButton)

    settings = settings_repository.get()
    assert dialog.result() == int(QDialog.DialogCode.Accepted)
    assert settings.launch_at_startup is True
    assert autostart_service.enabled is True
    assert autostart_service.enable_calls == 1