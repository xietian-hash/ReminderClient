from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class VisionLogDialog(QDialog):
    def __init__(self, vision_log_repository, parent=None) -> None:
        super().__init__(parent)
        self.vision_log_repository = vision_log_repository
        self.logs = []
        self.setWindowTitle('视觉识别日志')
        self.resize(980, 560)
        self._build_ui()
        self.load_logs()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)

        self.summary_label = QLabel('这里显示最近的视觉识别调用记录。', self)
        self.summary_label.setWordWrap(True)

        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(['完成时间', '提醒名称', '结果', '请求地址', '模型', '错误信息'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._update_detail_panel)

        self.detail_label = QLabel('详情', self)
        self.detail_label.setObjectName('visionLogDetailLabel')

        self.detail_text = QPlainTextEdit(self)
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText('选择一条日志查看完整详情。')

        action_layout = QHBoxLayout()
        action_layout.addStretch(1)
        self.refresh_button = QPushButton('刷新', self)
        self.refresh_button.clicked.connect(self.load_logs)
        self.close_button = QPushButton('关闭', self)
        self.close_button.clicked.connect(self.reject)
        action_layout.addWidget(self.refresh_button)
        action_layout.addWidget(self.close_button)

        root_layout.addWidget(self.summary_label)
        root_layout.addWidget(self.table)
        root_layout.addWidget(self.detail_label)
        root_layout.addWidget(self.detail_text)
        root_layout.addLayout(action_layout)

    def load_logs(self) -> None:
        self.logs = list(reversed(self.vision_log_repository.list_all()))
        self.table.setRowCount(len(self.logs))
        for row, log in enumerate(self.logs):
            self.table.setItem(row, 0, QTableWidgetItem(log.completed_at.strftime('%Y-%m-%d %H:%M:%S')))
            self.table.setItem(row, 1, QTableWidgetItem(log.reminder_name))
            self.table.setItem(row, 2, QTableWidgetItem(log.result.value))
            self.table.setItem(row, 3, QTableWidgetItem(log.request_url))
            self.table.setItem(row, 4, QTableWidgetItem(log.model_name))
            self.table.setItem(row, 5, QTableWidgetItem(log.error_message or ''))

        if self.logs:
            self.table.selectRow(0)
            self._update_detail_panel()
        else:
            self.detail_text.setPlainText('暂无日志记录。')

    def _update_detail_panel(self) -> None:
        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            return

        row = selected_indexes[0].row()
        if row < 0 or row >= len(self.logs):
            return

        log = self.logs[row]
        detail_lines = [
            f'提醒名称：{log.reminder_name}',
            f'完成时间：{log.completed_at.strftime("%Y-%m-%d %H:%M:%S")}',
            f'抓拍时间：{log.captured_at.strftime("%Y-%m-%d %H:%M:%S")}',
            f'请求时间：{log.requested_at.strftime("%Y-%m-%d %H:%M:%S")}',
            f'请求地址：{log.request_url}',
            f'模型名称：{log.model_name}',
            f'识别结果：{log.result.value}',
            f'错误信息：{log.error_message or "无"}',
            '原始返回：',
            log.raw_response_text or '无',
        ]
        self.detail_text.setPlainText('\n'.join(detail_lines))
