from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt

from reminder_client.domain.enums import VisionDecisionResult
from reminder_client.domain.models import VisionDecisionLog
from reminder_client.ui.vision_log_dialog import VisionLogDialog


class FakeVisionLogRepository:
    def __init__(self, logs) -> None:
        self._logs = logs

    def list_all(self):
        return self._logs


def test_vision_log_dialog_loads_recent_logs(qtbot) -> None:
    logs = [
        VisionDecisionLog(
            reminder_id='1',
            reminder_name='久坐提醒',
            request_url='https://example.com/api',
            model_name='demo-model',
            result=VisionDecisionResult.USER_LEFT_DESK,
            raw_response_text='用户已离开电脑前',
            captured_at=datetime(2026, 4, 17, 11, 50, 0),
            requested_at=datetime(2026, 4, 17, 11, 50, 1),
            completed_at=datetime(2026, 4, 17, 11, 50, 2),
        ),
        VisionDecisionLog(
            reminder_id='2',
            reminder_name='滴眼药水',
            request_url='https://example.com/api',
            model_name='demo-model',
            result=VisionDecisionResult.FAILED,
            error_message='请求失败',
            captured_at=datetime(2026, 4, 17, 11, 51, 0),
            requested_at=datetime(2026, 4, 17, 11, 51, 1),
            completed_at=datetime(2026, 4, 17, 11, 51, 2),
        ),
    ]
    dialog = VisionLogDialog(FakeVisionLogRepository(logs))
    qtbot.addWidget(dialog)

    assert dialog.table.rowCount() == 2
    assert dialog.table.item(0, 1).text() == '滴眼药水'
    assert dialog.table.item(0, 2).text() == '识别失败'
    assert '请求失败' in dialog.detail_text.toPlainText()


def test_vision_log_dialog_refreshes_details_on_selection(qtbot) -> None:
    logs = [
        VisionDecisionLog(
            reminder_id='1',
            reminder_name='久坐提醒',
            request_url='https://example.com/api',
            model_name='demo-model',
            result=VisionDecisionResult.USER_LEFT_DESK,
            raw_response_text='用户已离开电脑前',
            captured_at=datetime(2026, 4, 17, 11, 50, 0),
            requested_at=datetime(2026, 4, 17, 11, 50, 1),
            completed_at=datetime(2026, 4, 17, 11, 50, 2),
        ),
    ]
    dialog = VisionLogDialog(FakeVisionLogRepository(logs))
    qtbot.addWidget(dialog)

    dialog.table.clearSelection()
    dialog.table.selectRow(0)
    qtbot.waitUntil(lambda: '用户已离开电脑前' in dialog.detail_text.toPlainText(), timeout=1000)

    assert '久坐提醒' in dialog.detail_text.toPlainText()
