from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from core.models import Activity


def build_s_curve_data(
    activities: list[Activity],
    *,
    discipline: str | None = None,
    zone: str | None = None,
) -> list[dict[str, date | float]]:
    daily: dict[date, float] = defaultdict(float)
    for activity in activities:
        if discipline is not None and activity.discipline != discipline:
            continue
        if zone is not None and activity.zone != zone:
            continue
        if activity.es_date is None or activity.ef_date is None or activity.cost == 0:
            continue
        dates = _spread_dates(activity)
        if not dates:
            continue
        value = activity.cost / len(dates)
        for work_date in dates:
            daily[work_date] += value

    cumulative = 0.0
    rows: list[dict[str, date | float]] = []
    for work_date in sorted(daily):
        planned = round(daily[work_date], 2)
        cumulative = round(cumulative + planned, 2)
        rows.append(
            {
                "date": work_date,
                "planned_value": planned,
                "cumulative_value": cumulative,
            }
        )
    return rows


def _spread_dates(activity: Activity) -> list[date]:
    assert activity.es_date is not None
    assert activity.ef_date is not None
    if activity.duration == 0:
        return [activity.es_date]
    dates: list[date] = []
    current = activity.es_date
    while current <= activity.ef_date:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    if len(dates) >= activity.duration:
        return dates[: activity.duration]
    return dates or [activity.es_date]
