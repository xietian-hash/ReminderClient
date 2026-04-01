from __future__ import annotations

from PySide6.QtWidgets import QSystemTrayIcon

from reminder_client.domain.models import Reminder


class NotificationService:
    def notify_reminder_triggered(self, reminder: Reminder) -> None:
        raise NotImplementedError


class NullNotificationService(NotificationService):
    def notify_reminder_triggered(self, reminder: Reminder) -> None:
        return None


class QtTrayNotificationService(NotificationService):
    def __init__(self, tray_icon=None) -> None:
        self.tray_icon = tray_icon

    def set_tray_icon(self, tray_icon) -> None:
        self.tray_icon = tray_icon

    def notify_reminder_triggered(self, reminder: Reminder) -> None:
        if self.tray_icon is None:
            return
        try:
            self.tray_icon.showMessage(
                '提醒时间到',
                f'{reminder.name} 到时间了，请及时处理。',
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )
        except Exception:
            return