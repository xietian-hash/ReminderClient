from __future__ import annotations

import sqlite3

import pytest

from reminder_client.domain.models import AppSettings, Reminder
from reminder_client.storage.database import Database
from reminder_client.storage.reminder_repository import ReminderRepository
from reminder_client.storage.settings_repository import SettingsRepository


@pytest.fixture()
def database(tmp_path):
    db = Database(tmp_path / "reminder.db")
    db.initialize()
    return db


def test_database_initializes_tables(database: Database) -> None:
    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

    assert {row["name"] for row in rows} >= {"app_settings", "reminders"}


def test_add_reminder_succeeds(database: Database) -> None:
    repository = ReminderRepository(database)
    reminder = Reminder(name="久坐提醒", reminder_interval_minutes=45, break_interval_minutes=5)

    repository.add(reminder)
    saved = repository.get_by_id(reminder.id)

    assert saved is not None
    assert saved.name == "久坐提醒"


def test_duplicate_name_is_rejected(database: Database) -> None:
    repository = ReminderRepository(database)
    repository.add(Reminder(name="久坐提醒", reminder_interval_minutes=45, break_interval_minutes=5))

    with pytest.raises(ValueError, match="提醒名称已存在"):
        repository.add(Reminder(name=" 久坐提醒 ", reminder_interval_minutes=60, break_interval_minutes=10))


def test_update_reminder_succeeds(database: Database) -> None:
    repository = ReminderRepository(database)
    reminder = repository.add(
        Reminder(name="久坐提醒", reminder_interval_minutes=45, break_interval_minutes=5)
    )
    reminder.name = "滴眼药水"
    reminder.reminder_interval_minutes = 120

    repository.update(reminder)
    saved = repository.get_by_id(reminder.id)

    assert saved is not None
    assert saved.name == "滴眼药水"
    assert saved.reminder_interval_minutes == 120


def test_save_and_load_app_settings(database: Database) -> None:
    repository = SettingsRepository(database)
    repository.save(AppSettings(launch_at_startup=True, auto_remind_on_launch=True))

    settings = repository.get()

    assert settings.launch_at_startup is True
    assert settings.auto_remind_on_launch is True


def test_get_app_settings_defaults_to_auto_remind_disabled(database: Database) -> None:
    repository = SettingsRepository(database)

    settings = repository.get()

    assert settings.launch_at_startup is False
    assert settings.auto_remind_on_launch is False


def test_database_initialize_migrates_app_settings_for_auto_remind(tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE app_settings (
            settings_key INTEGER PRIMARY KEY CHECK (settings_key = 1),
            launch_at_startup INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "INSERT INTO app_settings (settings_key, launch_at_startup, updated_at) VALUES (1, 1, '2026-04-01T00:00:00')"
    )
    connection.commit()
    connection.close()

    database = Database(db_path)
    database.initialize()
    repository = SettingsRepository(database)

    settings = repository.get()

    assert settings.launch_at_startup is True
    assert settings.auto_remind_on_launch is False

def test_delete_reminder_removes_record(database: Database) -> None:
    repository = ReminderRepository(database)
    reminder = repository.add(
        Reminder(name="delete-target", reminder_interval_minutes=120, break_interval_minutes=1)
    )

    repository.delete(reminder.id)

    assert repository.get_by_id(reminder.id) is None
