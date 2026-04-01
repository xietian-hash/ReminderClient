from __future__ import annotations

from pathlib import Path

import reminder_client.app as app_module
from reminder_client.app import apply_startup_behavior, resolve_data_dir, resolve_launch_command
from reminder_client.domain.models import AppSettings
from reminder_client.resources import load_app_icon


class FakeSettingsRepository:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def get(self) -> AppSettings:
        return self.settings


class FakeTrayController:
    def __init__(self, available: bool) -> None:
        self.available = available

    def is_available(self) -> bool:
        return self.available


class FakeWindow:
    def __init__(self, settings: AppSettings, tray_available: bool = True) -> None:
        self.settings_repository = FakeSettingsRepository(settings)
        self.tray_controller = FakeTrayController(tray_available)
        self.auto_remind_applied = False
        self.start_all_called = False
        self.show_called = False

    def apply_auto_remind_on_launch(self) -> None:
        self.auto_remind_applied = True

    def handle_start_all(self) -> None:
        self.start_all_called = True

    def show(self) -> None:
        self.show_called = True


def test_apply_startup_behavior_hides_to_tray_when_auto_remind_enabled() -> None:
    window = FakeWindow(AppSettings(auto_remind_on_launch=True), tray_available=True)

    apply_startup_behavior(window)

    assert window.auto_remind_applied is True
    assert window.start_all_called is False
    assert window.show_called is False


def test_apply_startup_behavior_starts_all_and_shows_when_tray_unavailable() -> None:
    window = FakeWindow(AppSettings(auto_remind_on_launch=True), tray_available=False)

    apply_startup_behavior(window)

    assert window.auto_remind_applied is False
    assert window.start_all_called is True
    assert window.show_called is True


def test_apply_startup_behavior_shows_window_when_auto_remind_disabled() -> None:
    window = FakeWindow(AppSettings(auto_remind_on_launch=False), tray_available=True)

    apply_startup_behavior(window)

    assert window.auto_remind_applied is False
    assert window.start_all_called is False
    assert window.show_called is True


def test_resolve_launch_command_for_source_mode(monkeypatch) -> None:
    monkeypatch.setattr(app_module.sys, 'frozen', False, raising=False)
    monkeypatch.setattr(app_module.sys, 'executable', r'C:\Python311\python.exe')

    command = resolve_launch_command()

    assert command == '"C:\\Python311\\python.exe" -m reminder_client.main'


def test_resolve_launch_command_for_frozen_mode(monkeypatch) -> None:
    monkeypatch.setattr(app_module.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(app_module.sys, 'executable', r'D:\build\ReminderClient\ReminderClient.exe')

    command = resolve_launch_command()

    assert command == '"D:\\build\\ReminderClient\\ReminderClient.exe"'


def test_resolve_data_dir_uses_localappdata(monkeypatch) -> None:
    monkeypatch.setenv('LOCALAPPDATA', r'D:\Users\tester\AppData\Local')

    data_dir = resolve_data_dir()

    assert data_dir == Path(r'D:\Users\tester\AppData\Local') / 'ReminderClient'


def test_load_app_icon_returns_non_empty_icon(qapp) -> None:
    icon = load_app_icon()

    assert icon.isNull() is False
