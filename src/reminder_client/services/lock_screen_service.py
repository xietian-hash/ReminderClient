from __future__ import annotations

import ctypes


class LockScreenService:
    def lock(self) -> None:
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception:
            pass
