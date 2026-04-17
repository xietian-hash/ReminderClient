from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    reminder_interval_minutes INTEGER NOT NULL,
                    break_interval_minutes INTEGER NOT NULL,
                    music_path TEXT,
                    visual_reminder_enabled INTEGER NOT NULL DEFAULT 0,
                    visual_music_path TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    runtime_state TEXT NOT NULL,
                    current_phase TEXT NOT NULL,
                    remaining_seconds INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    settings_key INTEGER PRIMARY KEY CHECK (settings_key = 1),
                    launch_at_startup INTEGER NOT NULL DEFAULT 0,
                    auto_remind_on_launch INTEGER NOT NULL DEFAULT 0,
                    ark_base_url TEXT NOT NULL DEFAULT 'https://ark.cn-beijing.volces.com/api/v3/responses',
                    ark_api_key TEXT NOT NULL DEFAULT '',
                    ark_model_name TEXT NOT NULL DEFAULT 'doubao-seed-2-0-mini-260215',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS vision_decision_logs (
                    id TEXT PRIMARY KEY,
                    reminder_id TEXT NOT NULL,
                    reminder_name TEXT NOT NULL,
                    request_url TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    result TEXT NOT NULL,
                    raw_response_text TEXT,
                    error_message TEXT,
                    captured_at TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(
                connection,
                table_name='reminders',
                column_name='visual_reminder_enabled',
                column_definition='INTEGER NOT NULL DEFAULT 0',
            )
            self._ensure_column(
                connection,
                table_name='reminders',
                column_name='visual_music_path',
                column_definition='TEXT',
            )
            self._ensure_column(
                connection,
                table_name='app_settings',
                column_name='auto_remind_on_launch',
                column_definition='INTEGER NOT NULL DEFAULT 0',
            )
            self._ensure_column(
                connection,
                table_name='app_settings',
                column_name='ark_base_url',
                column_definition="TEXT NOT NULL DEFAULT 'https://ark.cn-beijing.volces.com/api/v3/responses'",
            )
            self._ensure_column(
                connection,
                table_name='app_settings',
                column_name='ark_api_key',
                column_definition="TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                connection,
                table_name='app_settings',
                column_name='ark_model_name',
                column_definition="TEXT NOT NULL DEFAULT 'doubao-seed-2-0-mini-260215'",
            )

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        *,
        table_name: str,
        column_name: str,
        column_definition: str,
    ) -> None:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing_columns = {row['name'] for row in rows}
        if column_name in existing_columns:
            return
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )
