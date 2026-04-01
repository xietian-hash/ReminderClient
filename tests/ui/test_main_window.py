from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QPushButton

from reminder_client.domain.enums import ReminderPhase, ReminderRuntimeState
from reminder_client.domain.models import Reminder
from reminder_client.ui.main_window import MainWindow
from reminder_client.ui.tray_controller import TrayController


class FakeReminderService:
    def __init__(self, reminders) -> None:
        self._reminders = reminders
        self.started_all = False
        self.paused_all = False
        self.reset_all_called = False
        self.prepare_for_exit_called = False
        self.tick_calls = 0

    def list_reminders(self):
        return self._reminders

    def start_all(self):
        self.started_all = True
        for reminder in self._reminders:
            if reminder.enabled:
                reminder.runtime_state = ReminderRuntimeState.RUNNING
        return self._reminders

    def pause_all(self):
        self.paused_all = True
        for reminder in self._reminders:
            reminder.runtime_state = ReminderRuntimeState.PAUSED
        return self._reminders

    def reset_all(self):
        self.reset_all_called = True
        return self._reminders

    def prepare_for_exit(self):
        self.prepare_for_exit_called = True
        return self._reminders

    def start(self, reminder_id: str):
        for reminder in self._reminders:
            if reminder.id == reminder_id:
                reminder.runtime_state = ReminderRuntimeState.RUNNING
        return reminder_id

    def pause(self, reminder_id: str):
        for reminder in self._reminders:
            if reminder.id == reminder_id:
                reminder.runtime_state = ReminderRuntimeState.PAUSED
        return reminder_id

    def reset(self, reminder_id: str):
        for reminder in self._reminders:
            if reminder.id == reminder_id:
                reminder.runtime_state = ReminderRuntimeState.NOT_STARTED
                reminder.current_phase = ReminderPhase.REMINDER
                reminder.remaining_seconds = reminder.reminder_interval_minutes * 60
        return reminder_id

    def delete_reminder(self, reminder_id: str):
        self._reminders = [reminder for reminder in self._reminders if reminder.id != reminder_id]

    def tick(self, reminder_id: str):
        self.tick_calls += 1
        for reminder in self._reminders:
            if reminder.id == reminder_id and reminder.runtime_state == ReminderRuntimeState.RUNNING:
                reminder.remaining_seconds = max(0, reminder.remaining_seconds - 1)
        return reminder_id


class FakeSettingsRepository:
    def get(self):
        raise AssertionError('本测试不需要调用设置仓储')


class FakeAutostartService:
    def enable(self):
        raise AssertionError('本测试不需要调用开机自启')

    def disable(self):
        raise AssertionError('本测试不需要调用开机自启')


def test_main_window_shows_toolbar_buttons(qtbot) -> None:
    window = MainWindow(FakeReminderService([]))
    qtbot.addWidget(window)

    assert window.new_button.text() == '新建提醒'
    assert window.start_all_button.text() == '全部开始'
    assert window.pause_all_button.text() == '全部暂停'
    assert window.reset_all_button.text() == '全部重置'
    assert window.settings_button.text() == '设置'


def test_main_window_loads_reminder_rows(qtbot) -> None:
    reminders = [
        Reminder(name='久坐提醒', reminder_interval_minutes=45, break_interval_minutes=5),
        Reminder(
            name='滴眼药水',
            reminder_interval_minutes=120,
            break_interval_minutes=1,
            runtime_state=ReminderRuntimeState.RUNNING,
            current_phase=ReminderPhase.BREAK,
            remaining_seconds=30,
        ),
    ]
    window = MainWindow(FakeReminderService(reminders))
    qtbot.addWidget(window)

    assert window.table.rowCount() == 2
    assert window.table.item(0, 0).text() == '久坐提醒'
    assert window.table.item(0, 1).text() == '45分钟'
    assert window.table.item(1, 3).text() == '休息中'
    assert window.table.item(1, 4).text() == '00:00:30'


def test_runtime_timer_counts_down_after_start(qtbot) -> None:
    reminders = [
        Reminder(
            name='久坐提醒',
            reminder_interval_minutes=45,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.RUNNING,
            remaining_seconds=3,
        )
    ]
    service = FakeReminderService(reminders)
    window = MainWindow(service, tick_interval_ms=20)
    qtbot.addWidget(window)

    qtbot.waitUntil(lambda: window.table.item(0, 4).text() == '00:00:02', timeout=1000)

    assert service.tick_calls >= 1


def test_close_window_hides_to_tray_and_timer_keeps_running(qtbot) -> None:
    reminders = [
        Reminder(
            name='久坐提醒',
            reminder_interval_minutes=45,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.RUNNING,
            remaining_seconds=3,
        )
    ]
    service = FakeReminderService(reminders)
    window = MainWindow(service, FakeSettingsRepository(), FakeAutostartService(), tick_interval_ms=20)
    qtbot.addWidget(window)
    tray_controller = TrayController(window, window.windowIcon())
    window.set_tray_controller(tray_controller)
    window.show()

    window.close()
    qtbot.waitUntil(lambda: reminders[0].remaining_seconds <= 2, timeout=1000)

    assert window.isHidden() is True
    assert service.tick_calls >= 1


def test_tray_menu_contains_expected_actions(qtbot) -> None:
    window = MainWindow(FakeReminderService([]))
    qtbot.addWidget(window)
    tray_controller = TrayController(window, window.windowIcon())

    texts = [action.text() for action in tray_controller.menu.actions() if action.text()]

    assert texts == ['显示主窗口', '全部开始', '全部暂停', '全部重置', '退出程序']


def test_request_exit_resets_all_before_quit(qtbot) -> None:
    service = FakeReminderService([])
    window = MainWindow(service)
    qtbot.addWidget(window)

    window.request_exit()

    assert service.prepare_for_exit_called is True


def test_reset_action_returns_to_not_started(qtbot) -> None:
    reminders = [
        Reminder(
            name='久坐提醒',
            reminder_interval_minutes=45,
            break_interval_minutes=5,
            runtime_state=ReminderRuntimeState.NOT_STARTED,
            remaining_seconds=45 * 60,
        )
    ]
    service = FakeReminderService(reminders)
    window = MainWindow(service)
    qtbot.addWidget(window)

    reminders[0].runtime_state = ReminderRuntimeState.RUNNING
    reminders[0].current_phase = ReminderPhase.BREAK
    reminders[0].remaining_seconds = 10
    service.reset(reminders[0].id)
    window.load_reminders()

    assert window.table.item(0, 3).text() == '未启动'
    assert window.table.item(0, 4).text() == '00:45:00'


def test_apply_auto_remind_on_launch_starts_all_and_hides_window(qtbot) -> None:
    reminders = [
        Reminder(name='久坐提醒', reminder_interval_minutes=45, break_interval_minutes=5),
        Reminder(name='滴眼药水', reminder_interval_minutes=120, break_interval_minutes=1, enabled=False),
    ]
    service = FakeReminderService(reminders)
    window = MainWindow(service)
    qtbot.addWidget(window)
    window.show()

    window.apply_auto_remind_on_launch()

    assert service.started_all is True
    assert reminders[0].runtime_state == ReminderRuntimeState.RUNNING
    assert reminders[1].runtime_state == ReminderRuntimeState.NOT_STARTED
    assert window.isHidden() is True


def test_delete_action_exists_in_row_actions(qtbot) -> None:
    reminders = [Reminder(name='delete-ui', reminder_interval_minutes=45, break_interval_minutes=5)]
    window = MainWindow(FakeReminderService(reminders))
    qtbot.addWidget(window)

    action_widget = window.table.cellWidget(0, 5)
    button_texts = [button.text() for button in action_widget.findChildren(QPushButton)]

    assert '删除' in button_texts


def test_delete_action_removes_row_after_confirmation(qtbot, monkeypatch) -> None:
    reminders = [
        Reminder(name='delete-ui-confirm', reminder_interval_minutes=45, break_interval_minutes=5)
    ]
    service = FakeReminderService(reminders)
    window = MainWindow(service)
    qtbot.addWidget(window)

    monkeypatch.setattr(
        QMessageBox,
        'question',
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    window.handle_delete_reminder(reminders[0].id)

    assert window.table.rowCount() == 0
    assert len(service._reminders) == 0
