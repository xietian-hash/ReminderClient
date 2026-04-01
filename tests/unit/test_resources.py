from __future__ import annotations

from pathlib import Path

import reminder_client.resources as resources_module
from reminder_client.resources import (
    resolve_app_icon_path,
    resolve_asset_path,
    resolve_package_icon_path,
    resolve_project_root,
)


def test_resolve_project_root_for_source_mode(monkeypatch) -> None:
    monkeypatch.setattr(resources_module.sys, 'frozen', False, raising=False)

    root = resolve_project_root()

    assert root == Path(__file__).resolve().parents[2]


def test_resolve_project_root_for_frozen_mode(monkeypatch) -> None:
    monkeypatch.setattr(resources_module.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(resources_module.sys, '_MEIPASS', r'D:\bundle-root', raising=False)

    root = resolve_project_root()

    assert root == Path(r'D:\bundle-root')


def test_resolve_asset_path_joins_assets_directory(monkeypatch) -> None:
    monkeypatch.setattr(resources_module.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(resources_module.sys, '_MEIPASS', r'D:\bundle-root', raising=False)

    path = resolve_asset_path('app_icon.png')

    assert path == Path(r'D:\bundle-root') / 'assets' / 'app_icon.png'


def test_resolve_app_icon_path_points_to_png(monkeypatch) -> None:
    monkeypatch.setattr(resources_module.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(resources_module.sys, '_MEIPASS', r'D:\bundle-root', raising=False)

    path = resolve_app_icon_path()

    assert path == Path(r'D:\bundle-root') / 'assets' / 'app_icon.png'


def test_resolve_package_icon_path_points_to_ico(monkeypatch) -> None:
    monkeypatch.setattr(resources_module.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(resources_module.sys, '_MEIPASS', r'D:\bundle-root', raising=False)

    path = resolve_package_icon_path()

    assert path == Path(r'D:\bundle-root') / 'assets' / 'app_icon.ico'
