from __future__ import annotations

from datetime import datetime
from datetime import time as Time

from reminder_client.domain.models import AppSettings


class DndService:
    def is_active(self, settings: AppSettings) -> bool:
        if not settings.dnd_enabled:
            return False

        no_days = not settings.dnd_days
        no_time = not settings.dnd_start_time or not settings.dnd_end_time
        if no_days and no_time:
            return False

        now = datetime.now()

        if settings.dnd_days and now.weekday() in settings.dnd_days:
            return True

        if settings.dnd_start_time and settings.dnd_end_time:
            return self._is_time_in_range(
                settings.dnd_start_time, settings.dnd_end_time, now.time()
            )

        return False

    def _is_time_in_range(self, start_str: str, end_str: str, current: Time) -> bool:
        try:
            sh, sm = map(int, start_str.split(':'))
            eh, em = map(int, end_str.split(':'))
            start = Time(sh, sm)
            end = Time(eh, em)
        except (ValueError, AttributeError):
            return False

        current_hm = Time(current.hour, current.minute)
        if start == end:
            return False
        if start < end:
            return start <= current_hm < end
        # 跨午夜，如 22:00 – 08:00
        return current_hm >= start or current_hm < end
