from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import holidays

from core.models import ActivityCpmResult, Calendar


class KoreanCalendar:
    def __init__(self, calendar: Calendar) -> None:
        self.calendar = calendar
        self.user_holidays = {date.fromisoformat(value) for value in calendar.holidays}

    def workday_to_date(self, project_start: date, offset: int) -> date:
        if offset < 0:
            raise ValueError("Workday offset cannot be negative")
        current = project_start
        remaining = offset
        while True:
            if self.is_working_day(current):
                if remaining == 0:
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
        return value not in holidays.country_holidays("KR", years=[value.year])


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
