from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from reminder_client.resources import resolve_wechat_official_qr_path, resolve_wechat_qr_path


_CHANGELOG = """
v0.1.7（2026-05-09）
  · 新增提醒方式：通知提醒、音频提醒、锁屏提醒，支持多选
  · 音频提醒勾选后才显示音频文件选择组件
  · 移除「启用提醒」复选框，简化提醒编辑界面

v0.1.6（2026-05-09）
  · 新增勿扰功能：可按星期与时段自动重置运行中的提醒
  · 退出勿扰时自动恢复被勿扰重置的提醒
  · 勿扰检查对齐到 5 分钟整点边界

v0.1.5（2026-04-01）
  · 新增统一应用图标

v0.1.4（2026-04-01）
  · 新增 PyInstaller 单目录打包支持

v0.1.3（2026-04-01）
  · 新增提醒删除功能与删除二次确认

v0.1.2（2026-04-01）
  · 新增自动提醒设置：启动后自动开始全部提醒并缩到托盘

v0.1.1（2026-03-31）
  · 新增视觉识别提醒：截图发送大模型判断是否需要提醒
  · 新增视觉识别日志弹窗

v0.1.0（2026-03-31）
  · 首次发布
  · 支持创建多条循环提醒，含提醒间隔与休息间隔
  · 支持单条/全部提醒的开始、暂停、重置
  · 支持桌面通知与音频提醒
  · 支持关闭窗口后缩到系统托盘继续运行
  · 支持开机自启
""".strip()

_QR_SIZE = 150


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('关于')
        self.resize(520, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(12)

        # 更新日志
        log_label = QLabel('版本更新日志', self)
        log_label.setStyleSheet('font-weight: bold;')
        root_layout.addWidget(log_label)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(240)
        content = QLabel(_CHANGELOG, scroll)
        content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        content.setWordWrap(True)
        content.setContentsMargins(6, 6, 6, 6)
        scroll.setWidget(content)
        root_layout.addWidget(scroll)

        # 分隔
        sep = QLabel(self)
        sep.setFixedHeight(1)
        sep.setStyleSheet('background: #e0e0e0;')
        root_layout.addWidget(sep)

        # 二维码区域：个人微信 + 公众号并排
        qr_section = QHBoxLayout()
        qr_section.setSpacing(24)
        qr_section.addStretch(1)
        qr_section.addLayout(self._build_qr_block(
            resolve_wechat_qr_path(),
            '个人微信\n扫码添加好友',
        ))
        qr_section.addStretch(1)
        qr_section.addLayout(self._build_qr_block(
            resolve_wechat_official_qr_path(),
            '微信公众号\n扫码关注',
        ))
        qr_section.addStretch(1)
        root_layout.addLayout(qr_section)

        root_layout.addStretch(1)

        # 关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        close_btn = QPushButton('关闭', self)
        close_btn.setObjectName('closeButton')
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        root_layout.addLayout(btn_layout)

    def _build_qr_block(self, qr_path, caption: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(6)

        qr_label = QLabel(self)
        if qr_path.exists():
            pixmap = QPixmap(str(qr_path)).scaled(
                _QR_SIZE, _QR_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            qr_label.setPixmap(pixmap)
        else:
            qr_label.setText('[图片未找到]')
        qr_label.setFixedSize(_QR_SIZE, _QR_SIZE)
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        caption_label = QLabel(caption, self)
        caption_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(qr_label)
        layout.addWidget(caption_label)
        return layout
