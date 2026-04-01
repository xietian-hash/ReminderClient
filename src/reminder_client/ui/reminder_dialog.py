from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ReminderDialog(QDialog):
    def __init__(self, reminder_service, reminder_id: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self.reminder_service = reminder_service
        self.reminder_id = reminder_id
        self.saved_reminder = None
        self.setWindowTitle('编辑提醒' if reminder_id else '新建提醒')
        self.resize(420, 260)
        self._build_ui()
        if reminder_id is not None:
            self._load_existing_data()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit(self)
        self.name_input.setObjectName('nameInput')

        self.reminder_interval_input = QSpinBox(self)
        self.reminder_interval_input.setObjectName('reminderIntervalInput')
        self.reminder_interval_input.setRange(1, 24 * 60)
        self.reminder_interval_input.setValue(45)
        self.reminder_interval_input.setSuffix(' 分钟')

        self.break_interval_input = QSpinBox(self)
        self.break_interval_input.setObjectName('breakIntervalInput')
        self.break_interval_input.setRange(0, 24 * 60)
        self.break_interval_input.setValue(5)
        self.break_interval_input.setSuffix(' 分钟')

        self.music_path_input = QLineEdit(self)
        self.music_path_input.setObjectName('musicPathInput')
        browse_button = QPushButton('选择文件', self)
        browse_button.setObjectName('browseMusicButton')
        browse_button.clicked.connect(self._choose_music_file)
        clear_button = QPushButton('清空', self)
        clear_button.setObjectName('clearMusicButton')
        clear_button.clicked.connect(lambda: self.music_path_input.setText(''))

        music_layout = QHBoxLayout()
        music_layout.addWidget(self.music_path_input)
        music_layout.addWidget(browse_button)
        music_layout.addWidget(clear_button)
        music_container = QWidget(self)
        music_container.setLayout(music_layout)

        self.enabled_checkbox = QCheckBox('启用提醒', self)
        self.enabled_checkbox.setObjectName('enabledCheckbox')
        self.enabled_checkbox.setChecked(True)

        form_layout.addRow('名称', self.name_input)
        form_layout.addRow('提醒间隔', self.reminder_interval_input)
        form_layout.addRow('休息间隔', self.break_interval_input)
        form_layout.addRow('休息提醒', music_container)
        form_layout.addRow('', self.enabled_checkbox)

        self.error_label = QLabel('', self)
        self.error_label.setObjectName('errorLabel')
        self.error_label.setStyleSheet('color: #b42318;')

        action_layout = QHBoxLayout()
        action_layout.addStretch(1)
        self.cancel_button = QPushButton('取消', self)
        self.cancel_button.setObjectName('cancelButton')
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton('保存', self)
        self.save_button.setObjectName('saveButton')
        self.save_button.clicked.connect(self._save)
        action_layout.addWidget(self.cancel_button)
        action_layout.addWidget(self.save_button)

        root_layout.addLayout(form_layout)
        root_layout.addWidget(self.error_label)
        root_layout.addLayout(action_layout)

    def _load_existing_data(self) -> None:
        reminder = self.reminder_service.get_reminder(self.reminder_id)
        self.name_input.setText(reminder.name)
        self.reminder_interval_input.setValue(reminder.reminder_interval_minutes)
        self.break_interval_input.setValue(reminder.break_interval_minutes)
        self.music_path_input.setText(reminder.music_path or '')
        self.enabled_checkbox.setChecked(reminder.enabled)

    def _choose_music_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择休息提醒',
            '',
            '音频文件 (*.mp3 *.wav *.ogg);;所有文件 (*.*)',
        )
        if file_path:
            self.music_path_input.setText(file_path)

    def _save(self) -> None:
        self.error_label.setText('')
        try:
            payload = {
                'name': self.name_input.text(),
                'reminder_interval_minutes': self.reminder_interval_input.value(),
                'break_interval_minutes': self.break_interval_input.value(),
                'music_path': self.music_path_input.text().strip() or None,
                'enabled': self.enabled_checkbox.isChecked(),
            }
            if self.reminder_id is None:
                self.saved_reminder = self.reminder_service.create_reminder(**payload)
            else:
                self.saved_reminder = self.reminder_service.update_reminder(self.reminder_id, **payload)
        except Exception as error:
            self.error_label.setText(str(error))
            return
        self.accept()