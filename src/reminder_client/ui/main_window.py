from __future__ import annotations

from functools import partial

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from reminder_client.domain.enums import ReminderPhase, ReminderRuntimeState
from reminder_client.ui.reminder_dialog import ReminderDialog
from reminder_client.ui.vision_log_dialog import VisionLogDialog
from reminder_client.ui.settings_dialog import SettingsDialog


STATE_LABELS = {
    ReminderRuntimeState.NOT_STARTED: '未启动',
    ReminderRuntimeState.RUNNING: '运行中',
    ReminderRuntimeState.PAUSED: '已暂停',
}


class MainWindow(QMainWindow):
    def __init__(
        self,
        reminder_service,
        settings_repository=None,
        autostart_service=None,
        vision_log_repository=None,
        tick_interval_ms: int = 1000,
    ) -> None:
        super().__init__()
        self.reminder_service = reminder_service
        self.settings_repository = settings_repository
        self.autostart_service = autostart_service
        self.vision_log_repository = vision_log_repository
        self.tray_controller = None
        self._force_exit = False
        self._tick_interval_ms = tick_interval_ms
        self.setWindowTitle('Windows 定时提醒客户端')
        self.resize(1080, 560)
        self._build_ui()
        self._setup_runtime_timer()
        self.load_reminders()

    def set_tray_controller(self, tray_controller) -> None:
        self.tray_controller = tray_controller

    def _build_ui(self) -> None:
        central = QWidget(self)
        root_layout = QVBoxLayout(central)

        toolbar_layout = QHBoxLayout()
        self.new_button = QPushButton('新建提醒')
        self.new_button.setObjectName('newReminderButton')
        self.start_all_button = QPushButton('全部开始')
        self.start_all_button.setObjectName('startAllButton')
        self.pause_all_button = QPushButton('全部暂停')
        self.pause_all_button.setObjectName('pauseAllButton')
        self.reset_all_button = QPushButton('全部重置')
        self.reset_all_button.setObjectName('resetAllButton')
        self.logs_button = QPushButton('日志')
        self.logs_button.setObjectName('logsButton')
        self.settings_button = QPushButton('设置')
        self.settings_button.setObjectName('settingsButton')

        self.new_button.clicked.connect(self.show_create_dialog)
        self.start_all_button.clicked.connect(self.handle_start_all)
        self.pause_all_button.clicked.connect(self.handle_pause_all)
        self.reset_all_button.clicked.connect(self.handle_reset_all)
        self.logs_button.clicked.connect(self.show_logs_dialog)
        self.settings_button.clicked.connect(self.show_settings_dialog)

        toolbar_layout.addWidget(self.new_button)
        toolbar_layout.addWidget(self.start_all_button)
        toolbar_layout.addWidget(self.pause_all_button)
        toolbar_layout.addWidget(self.reset_all_button)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.logs_button)
        toolbar_layout.addWidget(self.settings_button)

        self.table = QTableWidget(0, 6, self)
        self.table.setObjectName('reminderTable')
        self.table.setHorizontalHeaderLabels(['名称', '提醒间隔', '休息间隔', '状态', '剩余时间', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.status_label = QLabel('关闭窗口后将最小化到系统托盘继续运行')
        self.status_label.setObjectName('trayHintLabel')

        root_layout.addLayout(toolbar_layout)
        root_layout.addWidget(self.table)
        root_layout.addWidget(self.status_label)

        self.setCentralWidget(central)

    def _setup_runtime_timer(self) -> None:
        self.runtime_timer = QTimer(self)
        self.runtime_timer.setInterval(max(10, self._tick_interval_ms))
        self.runtime_timer.timeout.connect(self._handle_runtime_tick)
        self.runtime_timer.start()

    def _handle_runtime_tick(self) -> None:
        reminders = self.reminder_service.list_reminders()
        running_reminders = [
            reminder for reminder in reminders if reminder.runtime_state == ReminderRuntimeState.RUNNING
        ]
        if not running_reminders:
            return

        for reminder in running_reminders:
            self.reminder_service.tick(reminder.id)
        self.load_reminders()

    def apply_auto_remind_on_launch(self) -> None:
        self.reminder_service.start_all()
        self.load_reminders()
        self.hide()

    def load_reminders(self) -> None:
        reminders = self.reminder_service.list_reminders()
        self.table.setRowCount(len(reminders))

        for row, reminder in enumerate(reminders):
            self.table.setItem(row, 0, QTableWidgetItem(reminder.name))
            self.table.setItem(row, 1, QTableWidgetItem(f'{reminder.reminder_interval_minutes}分钟'))
            self.table.setItem(row, 2, QTableWidgetItem(f'{reminder.break_interval_minutes}分钟'))
            self.table.setItem(
                row,
                3,
                QTableWidgetItem(self._state_text(reminder.runtime_state, reminder.current_phase)),
            )
            self.table.setItem(row, 4, QTableWidgetItem(self._format_seconds(reminder.remaining_seconds)))
            self.table.setCellWidget(row, 5, self._build_action_widget(reminder.id, reminder.runtime_state))

    def _build_action_widget(self, reminder_id: str, runtime_state: ReminderRuntimeState) -> QWidget:
        container = QWidget(self.table)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        start_pause_text = '暂停' if runtime_state == ReminderRuntimeState.RUNNING else '开始'
        start_pause_button = QPushButton(start_pause_text, container)
        start_pause_button.clicked.connect(partial(self.handle_toggle_reminder, reminder_id, runtime_state))

        reset_button = QPushButton('重置', container)
        reset_button.clicked.connect(partial(self.handle_reset_reminder, reminder_id))

        edit_button = QPushButton('编辑', container)
        edit_button.clicked.connect(partial(self.show_edit_dialog, reminder_id))

        delete_button = QPushButton('删除', container)
        delete_button.clicked.connect(partial(self.handle_delete_reminder, reminder_id))

        layout.addWidget(start_pause_button)
        layout.addWidget(reset_button)
        layout.addWidget(edit_button)
        layout.addWidget(delete_button)
        return container

    def show_create_dialog(self) -> None:
        dialog = ReminderDialog(self.reminder_service, parent=self)
        if dialog.exec():
            self.load_reminders()

    def show_edit_dialog(self, reminder_id: str) -> None:
        dialog = ReminderDialog(self.reminder_service, reminder_id=reminder_id, parent=self)
        if dialog.exec():
            self.load_reminders()

    def show_settings_dialog(self) -> None:
        if self.settings_repository is None or self.autostart_service is None:
            QMessageBox.information(self, '提示', '当前未配置系统设置服务。')
            return
        dialog = SettingsDialog(self.settings_repository, self.autostart_service, parent=self)
        dialog.exec()

    def show_logs_dialog(self) -> None:
        if self.vision_log_repository is None:
            QMessageBox.information(self, '提示', '当前没有可用的视觉日志服务。')
            return
        dialog = VisionLogDialog(self.vision_log_repository, parent=self)
        dialog.exec()

    def handle_toggle_reminder(self, reminder_id: str, runtime_state: ReminderRuntimeState) -> None:
        if runtime_state == ReminderRuntimeState.RUNNING:
            self.reminder_service.pause(reminder_id)
        else:
            self.reminder_service.start(reminder_id)
        self.load_reminders()

    def handle_reset_reminder(self, reminder_id: str) -> None:
        self.reminder_service.reset(reminder_id)
        self.load_reminders()

    def handle_delete_reminder(self, reminder_id: str) -> None:
        answer = QMessageBox.question(
            self,
            '确认删除',
            '删除后不可恢复，是否继续？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.reminder_service.delete_reminder(reminder_id)
        self.load_reminders()

    def handle_start_all(self) -> None:
        self.reminder_service.start_all()
        self.load_reminders()

    def handle_pause_all(self) -> None:
        self.reminder_service.pause_all()
        self.load_reminders()

    def handle_reset_all(self) -> None:
        self.reminder_service.reset_all()
        self.load_reminders()

    def show_normal(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def request_exit(self) -> None:
        self._force_exit = True
        self.reminder_service.prepare_for_exit()
        if self.tray_controller is not None:
            self.tray_controller.hide()
        self.close()
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        if (
            not self._force_exit
            and self.tray_controller is not None
            and self.tray_controller.is_available()
        ):
            self.hide()
            event.ignore()
            return
        super().closeEvent(event)

    def _state_text(self, runtime_state: ReminderRuntimeState, current_phase: ReminderPhase) -> str:
        if runtime_state == ReminderRuntimeState.RUNNING and current_phase == ReminderPhase.BREAK:
            return '休息中'
        return STATE_LABELS[runtime_state]

    def _format_seconds(self, total_seconds: int) -> str:
        hours, remainder = divmod(max(total_seconds, 0), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
