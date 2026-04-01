from __future__ import annotations

from datetime import datetime

from reminder_client.domain.models import AppSettings
from reminder_client.storage.database import Database


class SettingsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self) -> AppSettings:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT launch_at_startup, auto_remind_on_launch, updated_at
                FROM app_settings
                WHERE settings_key = 1
                """
            ).fetchone()
        if row is None:
            settings = AppSettings()
            self.save(settings)
            return settings
        return AppSettings(
            launch_at_startup=bool(row['launch_at_startup']),
            auto_remind_on_launch=bool(row['auto_remind_on_launch']),
            updated_at=datetime.fromisoformat(row['updated_at']),
        )

    def save(self, settings: AppSettings) -> AppSettings:
        settings.updated_at = datetime.now()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO app_settings (settings_key, launch_at_startup, auto_remind_on_launch, updated_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(settings_key) DO UPDATE SET
                    launch_at_startup = excluded.launch_at_startup,
                    auto_remind_on_launch = excluded.auto_remind_on_launch,
                    updated_at = excluded.updated_at
                """,
                (
                    int(settings.launch_at_startup),
                    int(settings.auto_remind_on_launch),
                    settings.updated_at.isoformat(),
                ),
            )
        return settings