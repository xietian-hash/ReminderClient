from __future__ import annotations

from dataclasses import dataclass


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


class RegistryProvider:
    def set_value(self, key_path: str, name: str, value: str) -> None:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

    def delete_value(self, key_path: str, name: str) -> None:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                return None

    def get_value(self, key_path: str, name: str) -> str | None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                value, _ = winreg.QueryValueEx(key, name)
                return str(value)
        except FileNotFoundError:
            return None


@dataclass(slots=True)
class AutostartService:
    app_name: str
    executable_path: str
    registry: RegistryProvider | None = None

    def __post_init__(self) -> None:
        if self.registry is None:
            self.registry = RegistryProvider()

    def enable(self) -> None:
        self.registry.set_value(RUN_KEY_PATH, self.app_name, self.executable_path)

    def disable(self) -> None:
        self.registry.delete_value(RUN_KEY_PATH, self.app_name)

    def is_enabled(self) -> bool:
        return self.registry.get_value(RUN_KEY_PATH, self.app_name) == self.executable_path