from __future__ import annotations

import sqlite3
from datetime import datetime

from reminder_client.domain.enums import ReminderPhase, ReminderRuntimeState
from reminder_client.domain.models import Reminder, normalize_reminder_name
from reminder_client.storage.database import Database


class ReminderRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def add(self, reminder: Reminder) -> Reminder:
        reminder.name = normalize_reminder_name(reminder.name)
        reminder.created_at = datetime.now()
        reminder.updated_at = reminder.created_at
        try:
            with self.database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO reminders (
                        id, name, reminder_interval_minutes, break_interval_minutes,
                        music_path, enabled, runtime_state, current_phase,
                        remaining_seconds, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._to_row(reminder),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("提醒名称已存在，请重新输入") from error
        return reminder

    def update(self, reminder: Reminder) -> Reminder:
        reminder.name = normalize_reminder_name(reminder.name)
        reminder.updated_at = datetime.now()
        try:
            with self.database.connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE reminders
                    SET name = ?, reminder_interval_minutes = ?, break_interval_minutes = ?,
                        music_path = ?, enabled = ?, runtime_state = ?, current_phase = ?,
                        remaining_seconds = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        reminder.name,
                        reminder.reminder_interval_minutes,
                        reminder.break_interval_minutes,
                        reminder.music_path,
                        int(reminder.enabled),
                        reminder.runtime_state.value,
                        reminder.current_phase.value,
                        reminder.remaining_seconds,
                        reminder.updated_at.isoformat(),
                        reminder.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise KeyError(f"未找到提醒: {reminder.id}")
        except sqlite3.IntegrityError as error:
            raise ValueError("提醒名称已存在，请重新输入") from error
        return reminder

    def delete(self, reminder_id: str) -> None:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM reminders WHERE id = ?",
                (reminder_id,),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"未找到提醒: {reminder_id}")

    def get_by_id(self, reminder_id: str) -> Reminder | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM reminders WHERE id = ?",
                (reminder_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[Reminder]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM reminders ORDER BY created_at ASC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def _to_row(self, reminder: Reminder) -> tuple[object, ...]:
        return (
            reminder.id,
            reminder.name,
            reminder.reminder_interval_minutes,
            reminder.break_interval_minutes,
            reminder.music_path,
            int(reminder.enabled),
            reminder.runtime_state.value,
            reminder.current_phase.value,
            reminder.remaining_seconds,
            reminder.created_at.isoformat(),
            reminder.updated_at.isoformat(),
        )

    def _from_row(self, row: sqlite3.Row) -> Reminder:
        return Reminder(
            id=row["id"],
            name=row["name"],
            reminder_interval_minutes=row["reminder_interval_minutes"],
            break_interval_minutes=row["break_interval_minutes"],
            music_path=row["music_path"],
            enabled=bool(row["enabled"]),
            runtime_state=ReminderRuntimeState(row["runtime_state"]),
            current_phase=ReminderPhase(row["current_phase"]),
            remaining_seconds=row["remaining_seconds"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
