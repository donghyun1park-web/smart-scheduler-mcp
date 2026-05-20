from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import holidays

from core.models import ActivityCpmResult, Calendar


class KoreanCalendar:
    def __init__(self, calendar: Calendar) -> None:
        self.calendar = calendar
        self.user_holidays = {date.fromisoformat(value) for value in calendar.holidays}
        # Cache KR holidays per year so we don't rebuild the lookup on every call.
        self._kr_holidays_cache: dict[int, object] = {}
        # Memoize (project_start, offset) -> date so repeated lookups across
        # activities (each calls 4x) don't re-scan from the project start.
        self._workday_cache: dict[tuple[date, int], date] = {}

    def workday_to_date(self, project_start: date, offset: int) -> date:
        if offset < 0:
            raise ValueError("Workday offset cannot be negative")
        cache_key = (project_start, offset)
        cached = self._workday_cache.get(cache_key)
        if cached is not None:
            return cached
        # Resume from the nearest cached lower offset to avoid rescanning.
        start_offset = 0
        current = project_start
        for cached_offset in range(offset - 1, -1, -1):
            prev = self._workday_cache.get((project_start, cached_offset))
            if prev is not None:
                start_offset = cached_offset + 1
                current = prev + timedelta(days=1)
                break
        remaining = offset - start_offset
        while True:
            if self.is_working_day(current):
                if remaining == 0:
                    self._workday_cache[cache_key] = current
                    return current
                remaining -= 1
            current += timedelta(days=1)

    def finish_offset_to_date(self, project_start: date, finish_offset: int, duration: int) -> date:
        if duration < 0:
            raise ValueError("Activity duration cannot be negative")
        if duration == 0:
            return self.workday_to_date(project_start, finish_offset)
        return self.workday_to_date(project_start, finish_offset - 1)

    def add_workdays(self, start: date, workdays: int) -> date:
        return self.workday_to_date(start, workdays)

    def is_working_day(self, value: date) -> bool:
        weekday = value.weekday()
        if self.calendar.weekmask[weekday] != "1":
            return False
        if value in self.user_holidays:
            return False
        return value not in self._kr_holidays_for(value.year)

    def _kr_holidays_for(self, year: int) -> object:
        cached = self._kr_holidays_cache.get(year)
        if cached is None:
            cached = holidays.country_holidays("KR", years=[year])
            self._kr_holidays_cache[year] = cached
        return cached


def map_activity_dates(
    result: ActivityCpmResult,
    project_start: date,
    calendar: KoreanCalendar,
    *,
    duration: int,
) -> ActivityCpmResult:
    es_date = calendar.workday_to_date(project_start, result.es_workday)
    ef_date = calendar.finish_offset_to_date(project_start, result.ef_workday, duration)
    ls_date = calendar.workday_to_date(project_start, result.ls_workday)
    lf_date = calendar.finish_offset_to_date(project_start, result.lf_workday, duration)
    return replace(
        result,
        es_date=es_date,
        ef_date=ef_date,
        ls_date=ls_date,
        lf_date=lf_date,
    )
