from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Sequence

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QApplication

from reminder_client.resources import load_app_icon
from reminder_client.services.ark_vision_client import ArkVisionClient
from reminder_client.services.audio_service import AudioService
from reminder_client.services.autostart_service import AutostartService
from reminder_client.services.lock_screen_service import LockScreenService
from reminder_client.services.notification_service import QtTrayNotificationService
from reminder_client.services.reminder_service import ReminderService
from reminder_client.services.camera_service import CameraService
from reminder_client.services.vision_decision_service import VisionDecisionService
from reminder_client.storage.database import Database
from reminder_client.storage.reminder_repository import ReminderRepository
from reminder_client.storage.vision_log_repository import VisionLogRepository
from reminder_client.storage.settings_repository import SettingsRepository
from reminder_client.ui.main_window import MainWindow
from reminder_client.ui.tray_controller import TrayController


APP_NAME = 'Windows 定时提醒客户端'
APP_ORGANIZATION = 'Reminder Client'
APP_DB_DIR_NAME = 'ReminderClient'
APP_DB_FILE_NAME = 'reminder-client.db'


def create_application(argv: Sequence[str] | None = None):
    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORGANIZATION)
    app.setWindowIcon(load_app_icon())
    return app


def resolve_data_dir() -> Path:
    local_app_data = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    return local_app_data / APP_DB_DIR_NAME


def resolve_launch_command() -> str:
    if getattr(sys, 'frozen', False):
        return f'"{Path(sys.executable)}"'
    return f'"{sys.executable}" -m reminder_client.main'


def build_main_window() -> MainWindow:
    data_dir = resolve_data_dir()
    database = Database(data_dir / APP_DB_FILE_NAME)
    database.initialize()
    reminder_repository = ReminderRepository(database)
    settings_repository = SettingsRepository(database)
    vision_log_repository = VisionLogRepository(database)
    player = QMediaPlayer()
    audio_output = QAudioOutput()
    notification_service = QtTrayNotificationService()
    audio_service = AudioService(
        player=player,
        audio_output=audio_output,
        beep_callback=QApplication.beep,
    )
    vision_decision_service = VisionDecisionService(
        camera_service=CameraService(),
        ark_client=ArkVisionClient(),
        log_repository=vision_log_repository,
        audio_service=audio_service,
    )
    reminder_service = ReminderService(
        repository=reminder_repository,
        notification_service=notification_service,
        audio_service=audio_service,
        settings_repository=settings_repository,
        vision_decision_service=vision_decision_service,
        lock_screen_service=LockScreenService(),
    )
    autostart_service = AutostartService('ReminderClient', resolve_launch_command())
    window = MainWindow(
        reminder_service,
        settings_repository=settings_repository,
        autostart_service=autostart_service,
        vision_log_repository=vision_log_repository,
    )
    app_icon = load_app_icon()
    window.setWindowIcon(app_icon)
    tray_controller = TrayController(window, app_icon)
    window.set_tray_controller(tray_controller)
    notification_service.set_tray_icon(tray_controller.tray_icon)
    return window


def apply_startup_behavior(window: MainWindow) -> None:
    auto_remind_on_launch = False
    if window.settings_repository is not None:
        auto_remind_on_launch = window.settings_repository.get().auto_remind_on_launch

    tray_available = window.tray_controller is not None and window.tray_controller.is_available()
    if auto_remind_on_launch and tray_available:
        window.apply_auto_remind_on_launch()
        return

    if auto_remind_on_launch:
        window.handle_start_all()
    window.show()


def run(argv: Sequence[str] | None = None) -> int:
    app = create_application(argv)
    window = build_main_window()
    window.tray_controller.show()
    apply_startup_behavior(window)
    return app.exec()
