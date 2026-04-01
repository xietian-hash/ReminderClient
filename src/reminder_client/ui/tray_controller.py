from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class TrayController:
    def __init__(self, window, tray_icon: QIcon | None = None) -> None:
        self.window = window
        self.tray_icon = QSystemTrayIcon(window)
        icon = tray_icon if tray_icon is not None and not tray_icon.isNull() else window.windowIcon()
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip('Windows 定时提醒客户端')

        self.menu = QMenu(window)
        self.show_action = QAction('显示主窗口', self.menu)
        self.start_all_action = QAction('全部开始', self.menu)
        self.pause_all_action = QAction('全部暂停', self.menu)
        self.reset_all_action = QAction('全部重置', self.menu)
        self.exit_action = QAction('退出程序', self.menu)

        self.show_action.triggered.connect(self.window.show_normal)
        self.start_all_action.triggered.connect(self.window.handle_start_all)
        self.pause_all_action.triggered.connect(self.window.handle_pause_all)
        self.reset_all_action.triggered.connect(self.window.handle_reset_all)
        self.exit_action.triggered.connect(self.window.request_exit)

        self.menu.addAction(self.show_action)
        self.menu.addSeparator()
        self.menu.addAction(self.start_all_action)
        self.menu.addAction(self.pause_all_action)
        self.menu.addAction(self.reset_all_action)
        self.menu.addSeparator()
        self.menu.addAction(self.exit_action)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._handle_activated)

    def is_available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        if self.is_available():
            self.tray_icon.show()

    def hide(self) -> None:
        self.tray_icon.hide()

    def _handle_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.window.show_normal()
