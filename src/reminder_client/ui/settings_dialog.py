from __future__ import annotations

from PySide6.QtCore import QObject, QThread, QTime, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
)

from reminder_client.domain.models import AppSettings
from reminder_client.services.ark_vision_client import ArkVisionClient
from reminder_client.services.vision_decision_service import VISION_DECISION_PROMPT


class _ImageTestWorker(QObject):
    """在后台线程中执行图片识别测试，完成后通过信号通知 UI。"""

    finished: Signal = Signal(str, bool)  # message, success

    def __init__(self, base_url: str, api_key: str, model_name: str, image_bytes: bytes) -> None:
        super().__init__()
        self._base_url = base_url
        self._api_key = api_key
        self._model_name = model_name
        self._image_bytes = image_bytes

    def run(self) -> None:
        try:
            client = ArkVisionClient(timeout_seconds=30)
            result = client.analyze_image(
                image_bytes=self._image_bytes,
                prompt=VISION_DECISION_PROMPT,
                base_url=self._base_url,
                api_key=self._api_key,
                model_name=self._model_name,
            )
            self.finished.emit(f'✓ {result}', True)
        except Exception as exc:
            self.finished.emit(f'✗ 识别失败：{exc}', False)


class SettingsDialog(QDialog):
    def __init__(self, settings_repository, autostart_service, parent=None) -> None:
        super().__init__(parent)
        self.settings_repository = settings_repository
        self.autostart_service = autostart_service
        self._test_thread: QThread | None = None
        self._test_worker: _ImageTestWorker | None = None
        self.setWindowTitle('系统设置')
        self.resize(520, 600)
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.autostart_checkbox = QCheckBox('开机自启', self)
        self.autostart_checkbox.setObjectName('autostartCheckbox')
        self.autostart_description_label = QLabel(
            '启用后程序随 Windows 启动，并默认最小化到托盘。',
            self,
        )
        self.autostart_description_label.setWordWrap(True)

        self.auto_remind_checkbox = QCheckBox('自动提醒', self)
        self.auto_remind_checkbox.setObjectName('autoRemindCheckbox')
        self.auto_remind_description_label = QLabel(
            '启动后自动开始全部提醒并缩到托盘。',
            self,
        )
        self.auto_remind_description_label.setWordWrap(True)

        self.ark_base_url_input = QLineEdit(self)
        self.ark_base_url_input.setObjectName('arkBaseUrlInput')

        self.ark_api_key_input = QLineEdit(self)
        self.ark_api_key_input.setObjectName('arkApiKeyInput')
        self.ark_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.ark_model_name_input = QLineEdit(self)
        self.ark_model_name_input.setObjectName('arkModelNameInput')

        form_layout.addRow('Ark 调用地址', self.ark_base_url_input)
        form_layout.addRow('Ark API Key', self.ark_api_key_input)
        form_layout.addRow('Ark 模型名', self.ark_model_name_input)

        # 大模型图片识别测试
        test_layout = QHBoxLayout()
        self._test_button = QPushButton('选图测试', self)
        self._test_button.setObjectName('modelTestButton')
        self._test_button.clicked.connect(self._run_image_test)
        self._test_status_label = QLabel('', self)
        self._test_status_label.setObjectName('modelTestStatusLabel')
        self._test_status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        test_layout.addWidget(self._test_button)
        test_layout.addWidget(self._test_status_label, 1)

        # 勿扰设置
        dnd_separator = QLabel('── 勿扰设置 ──────────────────────────', self)

        self.dnd_enabled_checkbox = QCheckBox('启用勿扰', self)
        self.dnd_enabled_checkbox.setObjectName('dndEnabledCheckbox')

        weekday_layout = QHBoxLayout()
        weekday_layout.addWidget(QLabel('工作日（周一至周五）', self))
        self.dnd_weekday_start_edit = QTimeEdit(self)
        self.dnd_weekday_start_edit.setObjectName('dndWeekdayStartEdit')
        self.dnd_weekday_start_edit.setDisplayFormat('HH:mm')
        weekday_layout.addWidget(self.dnd_weekday_start_edit)
        weekday_layout.addWidget(QLabel('至', self))
        self.dnd_weekday_end_edit = QTimeEdit(self)
        self.dnd_weekday_end_edit.setObjectName('dndWeekdayEndEdit')
        self.dnd_weekday_end_edit.setDisplayFormat('HH:mm')
        weekday_layout.addWidget(self.dnd_weekday_end_edit)
        weekday_layout.addStretch(1)

        weekend_layout = QHBoxLayout()
        weekend_layout.addWidget(QLabel('周末（周六至周日）', self))
        self.dnd_weekend_start_edit = QTimeEdit(self)
        self.dnd_weekend_start_edit.setObjectName('dndWeekendStartEdit')
        self.dnd_weekend_start_edit.setDisplayFormat('HH:mm')
        weekend_layout.addWidget(self.dnd_weekend_start_edit)
        weekend_layout.addWidget(QLabel('至', self))
        self.dnd_weekend_end_edit = QTimeEdit(self)
        self.dnd_weekend_end_edit.setObjectName('dndWeekendEndEdit')
        self.dnd_weekend_end_edit.setDisplayFormat('HH:mm')
        weekend_layout.addWidget(self.dnd_weekend_end_edit)
        weekend_layout.addStretch(1)

        dnd_desc_label = QLabel(
            '在勿扰时段内，运行中的提醒将自动重置；退出后自动恢复。', self
        )
        dnd_desc_label.setWordWrap(True)

        self.error_label = QLabel('', self)
        self.error_label.setObjectName('settingsErrorLabel')
        self.error_label.setStyleSheet('color: #b42318;')

        action_layout = QHBoxLayout()
        action_layout.addStretch(1)
        self.close_button = QPushButton('关闭', self)
        self.close_button.setObjectName('closeButton')
        self.close_button.clicked.connect(self.reject)
        self.save_button = QPushButton('保存', self)
        self.save_button.setObjectName('saveButton')
        self.save_button.clicked.connect(self._save)
        action_layout.addWidget(self.close_button)
        action_layout.addWidget(self.save_button)

        root_layout.addWidget(self.autostart_checkbox)
        root_layout.addWidget(self.autostart_description_label)
        root_layout.addSpacing(8)
        root_layout.addWidget(self.auto_remind_checkbox)
        root_layout.addWidget(self.auto_remind_description_label)
        root_layout.addSpacing(8)
        root_layout.addLayout(form_layout)
        root_layout.addSpacing(4)
        root_layout.addLayout(test_layout)
        root_layout.addSpacing(8)
        root_layout.addWidget(dnd_separator)
        root_layout.addSpacing(4)
        root_layout.addWidget(self.dnd_enabled_checkbox)
        root_layout.addLayout(weekday_layout)
        root_layout.addLayout(weekend_layout)
        root_layout.addWidget(dnd_desc_label)
        root_layout.addWidget(self.error_label)
        root_layout.addStretch(1)
        root_layout.addLayout(action_layout)

    def _load_settings(self) -> None:
        settings = self.settings_repository.get()
        self.autostart_checkbox.setChecked(settings.launch_at_startup)
        self.auto_remind_checkbox.setChecked(settings.auto_remind_on_launch)
        self.ark_base_url_input.setText(settings.ark_base_url)
        self.ark_api_key_input.setText(settings.ark_api_key)
        self.ark_model_name_input.setText(settings.ark_model_name)
        self.dnd_enabled_checkbox.setChecked(settings.dnd_enabled)
        try:
            wdsh, wdsm = map(int, settings.dnd_weekday_start_time.split(':'))
            wdeh, wdem = map(int, settings.dnd_weekday_end_time.split(':'))
            wesh, wesm = map(int, settings.dnd_weekend_start_time.split(':'))
            weeh, weem = map(int, settings.dnd_weekend_end_time.split(':'))
        except (ValueError, AttributeError):
            wdsh, wdsm, wdeh, wdem = 23, 0, 19, 0
            wesh, wesm, weeh, weem = 23, 0, 9, 0
        self.dnd_weekday_start_edit.setTime(QTime(wdsh, wdsm))
        self.dnd_weekday_end_edit.setTime(QTime(wdeh, wdem))
        self.dnd_weekend_start_edit.setTime(QTime(wesh, wesm))
        self.dnd_weekend_end_edit.setTime(QTime(weeh, weem))

    def _run_image_test(self) -> None:
        base_url = self.ark_base_url_input.text().strip()
        api_key = self.ark_api_key_input.text().strip()
        model_name = self.ark_model_name_input.text().strip()

        if not base_url or not api_key or not model_name:
            self._test_status_label.setStyleSheet('color: #b42318;')
            self._test_status_label.setText('请先填写调用地址、API Key 和模型名')
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            '选择测试图片',
            '',
            '图片文件 (*.png *.jpg *.jpeg *.bmp)',
        )
        if not path:
            return

        try:
            with open(path, 'rb') as f:
                image_bytes = f.read()
        except OSError as exc:
            self._test_status_label.setStyleSheet('color: #b42318;')
            self._test_status_label.setText(f'✗ 读取图片失败：{exc}')
            return

        self._test_button.setEnabled(False)
        self._test_status_label.setStyleSheet('color: #666666;')
        self._test_status_label.setText('识别中…')

        self._test_thread = QThread(self)
        self._test_worker = _ImageTestWorker(base_url, api_key, model_name, image_bytes)
        self._test_worker.moveToThread(self._test_thread)
        self._test_thread.started.connect(self._test_worker.run)
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.finished.connect(self._test_thread.quit)
        self._test_thread.finished.connect(self._test_thread.deleteLater)
        self._test_thread.start()

    def _on_test_finished(self, message: str, success: bool) -> None:
        self._test_button.setEnabled(True)
        color = '#2e7d32' if success else '#b42318'
        self._test_status_label.setStyleSheet(f'color: {color};')
        self._test_status_label.setText(message)

    def closeEvent(self, event) -> None:
        """对话框关闭时等待测试线程结束，避免线程悬空。"""
        if self._test_thread is not None and self._test_thread.isRunning():
            self._test_thread.quit()
            self._test_thread.wait(3000)
        super().closeEvent(event)

    def _save(self) -> None:
        self.error_label.setText('')
        try:
            launch_at_startup = self.autostart_checkbox.isChecked()
            auto_remind_on_launch = self.auto_remind_checkbox.isChecked()
            dnd_enabled = self.dnd_enabled_checkbox.isChecked()
            self.settings_repository.save(
                AppSettings(
                    launch_at_startup=launch_at_startup,
                    auto_remind_on_launch=auto_remind_on_launch,
                    ark_base_url=self.ark_base_url_input.text().strip(),
                    ark_api_key=self.ark_api_key_input.text().strip(),
                    ark_model_name=self.ark_model_name_input.text().strip(),
                    dnd_enabled=dnd_enabled,
                    dnd_weekday_start_time=self.dnd_weekday_start_edit.time().toString('HH:mm'),
                    dnd_weekday_end_time=self.dnd_weekday_end_edit.time().toString('HH:mm'),
                    dnd_weekend_start_time=self.dnd_weekend_start_edit.time().toString('HH:mm'),
                    dnd_weekend_end_time=self.dnd_weekend_end_edit.time().toString('HH:mm'),
                )
            )
            if launch_at_startup:
                self.autostart_service.enable()
            else:
                self.autostart_service.disable()
        except Exception as error:
            self.error_label.setText(str(error))
            return
        self.accept()
