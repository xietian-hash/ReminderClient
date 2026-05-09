from __future__ import annotations

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
)

from reminder_client.domain.models import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, settings_repository, autostart_service, parent=None) -> None:
        super().__init__(parent)
        self.settings_repository = settings_repository
        self.autostart_service = autostart_service
        self.setWindowTitle('系统设置')
        self.resize(520, 560)
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

        # 勿扰设置
        dnd_separator = QLabel('── 勿扰设置 ──────────────────────────', self)

        self.dnd_enabled_checkbox = QCheckBox('启用勿扰', self)
        self.dnd_enabled_checkbox.setObjectName('dndEnabledCheckbox')

        day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        self.dnd_day_checkboxes: list[QCheckBox] = []
        days_layout = QHBoxLayout()
        for i, name in enumerate(day_names):
            cb = QCheckBox(name, self)
            cb.setObjectName(f'dndDayCheckbox{i}')
            self.dnd_day_checkboxes.append(cb)
            days_layout.addWidget(cb)
        days_layout.addStretch(1)

        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel('勿扰时间：', self))
        self.dnd_start_time_edit = QTimeEdit(self)
        self.dnd_start_time_edit.setObjectName('dndStartTimeEdit')
        self.dnd_start_time_edit.setDisplayFormat('HH:mm')
        time_layout.addWidget(self.dnd_start_time_edit)
        time_layout.addWidget(QLabel('至', self))
        self.dnd_end_time_edit = QTimeEdit(self)
        self.dnd_end_time_edit.setObjectName('dndEndTimeEdit')
        self.dnd_end_time_edit.setDisplayFormat('HH:mm')
        time_layout.addWidget(self.dnd_end_time_edit)
        time_layout.addStretch(1)

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
        root_layout.addSpacing(8)
        root_layout.addWidget(dnd_separator)
        root_layout.addSpacing(4)
        root_layout.addWidget(self.dnd_enabled_checkbox)
        root_layout.addLayout(days_layout)
        root_layout.addLayout(time_layout)
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
        for i, cb in enumerate(self.dnd_day_checkboxes):
            cb.setChecked(i in settings.dnd_days)
        try:
            sh, sm = map(int, settings.dnd_start_time.split(':'))
            eh, em = map(int, settings.dnd_end_time.split(':'))
        except (ValueError, AttributeError):
            sh, sm, eh, em = 22, 0, 8, 0
        self.dnd_start_time_edit.setTime(QTime(sh, sm))
        self.dnd_end_time_edit.setTime(QTime(eh, em))

    def _save(self) -> None:
        self.error_label.setText('')
        try:
            launch_at_startup = self.autostart_checkbox.isChecked()
            auto_remind_on_launch = self.auto_remind_checkbox.isChecked()
            dnd_enabled = self.dnd_enabled_checkbox.isChecked()
            dnd_days = [i for i, cb in enumerate(self.dnd_day_checkboxes) if cb.isChecked()]
            dnd_start_time = self.dnd_start_time_edit.time().toString('HH:mm')
            dnd_end_time = self.dnd_end_time_edit.time().toString('HH:mm')
            self.settings_repository.save(
                AppSettings(
                    launch_at_startup=launch_at_startup,
                    auto_remind_on_launch=auto_remind_on_launch,
                    ark_base_url=self.ark_base_url_input.text().strip(),
                    ark_api_key=self.ark_api_key_input.text().strip(),
                    ark_model_name=self.ark_model_name_input.text().strip(),
                    dnd_enabled=dnd_enabled,
                    dnd_days=dnd_days,
                    dnd_start_time=dnd_start_time,
                    dnd_end_time=dnd_end_time,
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
