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
        self.resize(520, 360)
        self._build_ui()
        if reminder_id is not None:
            self._load_existing_data()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.form_layout = form_layout

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

        self.music_path_input, self.music_browse_button, self.music_clear_button = self._create_file_picker(
            title='选择定时提醒音频',
            browse_text='选择文件',
            clear_text='清空',
            object_prefix='music',
        )

        self.enabled_checkbox = QCheckBox('启用提醒', self)
        self.enabled_checkbox.setObjectName('enabledCheckbox')
        self.enabled_checkbox.setChecked(True)

        self.visual_enabled_checkbox = QCheckBox('启用视觉提醒', self)
        self.visual_enabled_checkbox.setObjectName('visualEnabledCheckbox')

        self.visual_music_path_input, self.visual_music_browse_button, self.visual_music_clear_button = (
            self._create_file_picker(
                title='选择视觉提醒音频',
                browse_text='选择文件',
                clear_text='清空',
                object_prefix='visualMusic',
            )
        )

        self.visual_test_button = QPushButton('测试视觉提醒', self)
        self.visual_test_button.setObjectName('visualTestButton')
        self.visual_test_button.clicked.connect(self._test_visual_reminder)

        form_layout.addRow('名称', self.name_input)
        form_layout.addRow('定时提醒间隔', self.reminder_interval_input)
        form_layout.addRow('休息间隔', self.break_interval_input)
        form_layout.addRow('定时提醒音频', self._build_picker_row(
            self.music_path_input,
            self.music_browse_button,
            self.music_clear_button,
        ))
        form_layout.addRow('', self.enabled_checkbox)
        form_layout.addRow('', self.visual_enabled_checkbox)
        form_layout.addRow('视觉提醒音频', self._build_picker_row(
            self.visual_music_path_input,
            self.visual_music_browse_button,
            self.visual_music_clear_button,
        ))
        form_layout.addRow('', self.visual_test_button)

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

    def _create_file_picker(
        self,
        *,
        title: str,
        browse_text: str,
        clear_text: str,
        object_prefix: str,
    ) -> tuple[QLineEdit, QPushButton, QPushButton]:
        path_input = QLineEdit(self)
        path_input.setObjectName(f'{object_prefix}PathInput')

        browse_button = QPushButton(browse_text, self)
        browse_button.setObjectName(f'{object_prefix}BrowseButton')
        browse_button.clicked.connect(
            lambda: self._choose_music_file(path_input, title)
        )

        clear_button = QPushButton(clear_text, self)
        clear_button.setObjectName(f'{object_prefix}ClearButton')
        clear_button.clicked.connect(lambda: path_input.setText(''))

        return path_input, browse_button, clear_button

    def _build_picker_row(
        self,
        path_input: QLineEdit,
        browse_button: QPushButton,
        clear_button: QPushButton,
    ) -> QWidget:
        layout = QHBoxLayout()
        layout.addWidget(path_input)
        layout.addWidget(browse_button)
        layout.addWidget(clear_button)
        container = QWidget(self)
        container.setLayout(layout)
        return container

    def _load_existing_data(self) -> None:
        reminder = self.reminder_service.get_reminder(self.reminder_id)
        self.name_input.setText(reminder.name)
        self.reminder_interval_input.setValue(reminder.reminder_interval_minutes)
        self.break_interval_input.setValue(reminder.break_interval_minutes)
        self.music_path_input.setText(reminder.music_path or '')
        self.visual_enabled_checkbox.setChecked(reminder.visual_reminder_enabled)
        self.visual_music_path_input.setText(reminder.visual_music_path or '')
        self.enabled_checkbox.setChecked(reminder.enabled)

    def _choose_music_file(self, path_input: QLineEdit, title: str) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            '',
            '音频文件 (*.mp3 *.wav *.ogg);;所有文件 (*.*)',
        )
        if file_path:
            path_input.setText(file_path)

    def _build_payload(self) -> dict[str, object]:
        return {
            'name': self.name_input.text(),
            'reminder_interval_minutes': self.reminder_interval_input.value(),
            'break_interval_minutes': self.break_interval_input.value(),
            'music_path': self.music_path_input.text().strip() or None,
            'visual_reminder_enabled': self.visual_enabled_checkbox.isChecked(),
            'visual_music_path': self.visual_music_path_input.text().strip() or None,
            'enabled': self.enabled_checkbox.isChecked(),
        }

    def _test_visual_reminder(self) -> None:
        self.error_label.setText('')
        try:
            payload = self._build_payload()
            tester = getattr(self.reminder_service, 'test_visual_decision')
            tester(payload)
        except Exception as error:
            self.error_label.setText(str(error))

    def _save(self) -> None:
        self.error_label.setText('')
        try:
            payload = self._build_payload()
            if self.reminder_id is None:
                self.saved_reminder = self.reminder_service.create_reminder(**payload)
            else:
                self.saved_reminder = self.reminder_service.update_reminder(self.reminder_id, **payload)
        except Exception as error:
            self.error_label.setText(str(error))
            return
        self.accept()
