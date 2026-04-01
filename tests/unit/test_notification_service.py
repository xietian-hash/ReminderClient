from __future__ import annotations

from PySide6.QtWidgets import QSystemTrayIcon

from reminder_client.domain.models import Reminder
from reminder_client.services.notification_service import QtTrayNotificationService


class FakeTrayIcon:
    class MessageIcon:
        Information = 1

    def __init__(self) -> None:
        self.messages: list[tuple[str, str, object, int]] = []

    def showMessage(self, title: str, message: str, icon: object, timeout: int) -> None:
        self.messages.append((title, message, icon, timeout))


def test_qt_tray_notification_service_uses_qt_message_icon_enum() -> None:
    tray_icon = FakeTrayIcon()
    service = QtTrayNotificationService(tray_icon)
    reminder = Reminder(name='久坐提醒', reminder_interval_minutes=45, break_interval_minutes=5)

    service.notify_reminder_triggered(reminder)

    assert tray_icon.messages == [
        ('提醒时间到', '久坐提醒 到时间了，请及时处理。', QSystemTrayIcon.MessageIcon.Information, 5000)
    ]