from __future__ import annotations

from datetime import date

from core.models import Activity
from core.s_curve import build_s_curve_data


def test_s_curve_spreads_cost_across_activity_dates():
    activities = [
        _activity("a", cost=300.0, duration=3, es=date(2026, 1, 5), ef=date(2026, 1, 7)),
    ]

    rows = build_s_curve_data(activities)

    assert [row["planned_value"] for row in rows] == [100.0, 100.0, 100.0]
    assert [row["cumulative_value"] for row in rows] == [100.0, 200.0, 300.0]


def test_s_curve_places_milestone_cost_on_es_date():
    activities = [
        _activity("m", cost=500.0, duration=0, es=date(2026, 1, 5), ef=date(2026, 1, 5)),
    ]

    rows = build_s_curve_data(activities)

    assert rows == [
        {
            "date": date(2026, 1, 5),
            "planned_value": 500.0,
            "cumulative_value": 500.0,
        }
    ]


def _activity(activity_id: str, *, cost: float, duration: int, es: date, ef: date) -> Activity:
    return Activity(
        activity_id=activity_id,
        code=activity_id.upper(),
        name=activity_id,
        wbs_id="wbs",
        discipline="\uacf5\ud1b5",
        zone="1F",
        duration=duration,
        cost=cost,
        es_date=es,
        ef_date=ef,
        is_critical=True,
    )
