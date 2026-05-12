from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


ASSETS_DIR_NAME = 'assets'
APP_ICON_FILE_NAME = 'app_icon.png'
PACKAGE_ICON_FILE_NAME = 'app_icon.ico'
WECHAT_QR_FILE_NAME = 'wechat_qr.jpg'
WECHAT_OFFICIAL_QR_FILE_NAME = 'wechat_official_qr.jpg'


def resolve_project_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(getattr(sys, '_MEIPASS', Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[2]


def resolve_asset_path(*parts: str) -> Path:
    return resolve_project_root() / ASSETS_DIR_NAME / Path(*parts)


def resolve_app_icon_path() -> Path:
    return resolve_asset_path(APP_ICON_FILE_NAME)


def resolve_package_icon_path() -> Path:
    return resolve_asset_path(PACKAGE_ICON_FILE_NAME)


def resolve_wechat_qr_path() -> Path:
    return resolve_asset_path(WECHAT_QR_FILE_NAME)


def resolve_wechat_official_qr_path() -> Path:
    return resolve_asset_path(WECHAT_OFFICIAL_QR_FILE_NAME)


def load_app_icon() -> QIcon:
    icon_path = resolve_app_icon_path()
    return QIcon(str(icon_path)) if icon_path.exists() else QIcon()
