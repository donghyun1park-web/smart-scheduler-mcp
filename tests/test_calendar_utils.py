from __future__ import annotations

from datetime import date

from core.calendar_utils import KoreanCalendar, map_activity_dates
from core.models import ActivityCpmResult, Calendar


def test_five_day_weekmask_skips_weekends():
    calendar = KoreanCalendar(Calendar("cal", "5-day", "1111100"))

    assert calendar.workday_to_date(date(2026, 1, 2), 0) == date(2026, 1, 2)
    assert calendar.workday_to_date(date(2026, 1, 2), 1) == date(2026, 1, 5)


def test_korean_public_holiday_is_non_working_day():
    calendar = KoreanCalendar(Calendar("cal", "5-day", "1111100"))

    assert calendar.workday_to_date(date(2026, 3, 2), 0) == date(2026, 3, 3)


def test_user_defined_holiday_is_non_working_day():
    calendar = KoreanCalendar(Calendar("cal", "5-day", "1111100", ("2026-01-05",)))

    assert calendar.workday_to_date(date(2026, 1, 2), 1) == date(2026, 1, 6)


def test_six_day_weekmask_allows_saturday():
    calendar = KoreanCalendar(Calendar("cal", "6-day", "1111110"))

    assert calendar.workday_to_date(date(2026, 1, 2), 1) == date(2026, 1, 3)


def test_duration_one_activity_starts_and_finishes_on_same_date():
    calendar = KoreanCalendar(Calendar("cal", "5-day", "1111100"))
    result = _result("a", "A", es=0, ef=1, ls=0, lf=1)

    mapped = map_activity_dates(result, date(2026, 1, 5), calendar, duration=1)

    assert mapped.es_date == date(2026, 1, 5)
    assert mapped.ef_date == date(2026, 1, 5)


def test_zero_duration_milestone_uses_same_start_and_finish_date():
    calendar = KoreanCalendar(Calendar("cal", "5-day", "1111100"))
    result = _result("m", "M", es=2, ef=2, ls=2, lf=2)

    mapped = map_activity_dates(result, date(2026, 1, 5), calendar, duration=0)

    assert mapped.es_date == date(2026, 1, 7)
    assert mapped.ef_date == date(2026, 1, 7)


def _result(
    activity_id: str,
    code: str,
    *,
    es: int,
    ef: int,
    ls: int,
    lf: int,
) -> ActivityCpmResult:
    return ActivityCpmResult(
        activity_id=activity_id,
        code=code,
        es_workday=es,
        ef_workday=ef,
        ls_workday=ls,
        lf_workday=lf,
        total_float=0,
        is_critical=True,
    )
