from __future__ import annotations

import sqlite3
from datetime import datetime

from reminder_client.domain.enums import VisionDecisionResult
from reminder_client.domain.models import VisionDecisionLog
from reminder_client.storage.database import Database


class VisionLogRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def add(self, log: VisionDecisionLog) -> VisionDecisionLog:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO vision_decision_logs (
                    id, reminder_id, reminder_name, request_url, model_name,
                    result, raw_response_text, error_message,
                    captured_at, requested_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._to_row(log),
            )
        return log

    def list_all(self) -> list[VisionDecisionLog]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM vision_decision_logs ORDER BY completed_at ASC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def _to_row(self, log: VisionDecisionLog) -> tuple[object, ...]:
        return (
            log.id,
            log.reminder_id,
            log.reminder_name,
            log.request_url,
            log.model_name,
            log.result.value,
            log.raw_response_text,
            log.error_message,
            log.captured_at.isoformat(),
            log.requested_at.isoformat(),
            log.completed_at.isoformat(),
        )

    def _from_row(self, row: sqlite3.Row) -> VisionDecisionLog:
        return VisionDecisionLog(
            id=row["id"],
            reminder_id=row["reminder_id"],
            reminder_name=row["reminder_name"],
            request_url=row["request_url"],
            model_name=row["model_name"],
            result=VisionDecisionResult(row["result"]),
            raw_response_text=row["raw_response_text"],
            error_message=row["error_message"],
            captured_at=datetime.fromisoformat(row["captured_at"]),
            requested_at=datetime.fromisoformat(row["requested_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]),
        )
