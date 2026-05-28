from __future__ import annotations

from datetime import datetime
from datetime import time as Time

from reminder_client.domain.models import AppSettings


class DndService:
    def is_active(self, settings: AppSettings) -> bool:
        if not settings.dnd_enabled:
            return False

        now = datetime.now()
        is_weekend = now.weekday() >= 5  # 5=Saturday, 6=Sunday

        if is_weekend:
            start = settings.dnd_weekend_start_time
            end = settings.dnd_weekend_end_time
        else:
            start = settings.dnd_weekday_start_time
            end = settings.dnd_weekday_end_time

        if not start or not end:
            return False

        return self._is_time_in_range(start, end, now.time())

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
