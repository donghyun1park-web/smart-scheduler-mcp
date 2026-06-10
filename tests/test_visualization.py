from __future__ import annotations

from datetime import date, timedelta

from core.models import Activity
from core.visualization import build_gantt_figure


def test_gantt_figure_contains_critical_path_highlight_and_hover_data():
    activities = [
        _activity("a", "A100", "Critical", True, 0),
        _activity("b", "A200", "Float", False, 1),
    ]

    fig = build_gantt_figure(activities)

    assert len(fig.data) == 2
    marker_colors = {trace.marker.color for trace in fig.data}
    assert "#d62728" in marker_colors
    assert any("total_float" in str(trace.hovertemplate) for trace in fig.data)


def test_gantt_filters_by_discipline_zone_and_critical():
    activities = [
        _activity("a", "A100", "Critical", True, 0, discipline="\uacf5\ud1b5", zone="1F"),
        _activity("b", "P100", "Other", False, 1, discipline="\uc704\uc0dd", zone="2F"),
    ]

    fig = build_gantt_figure(
        activities,
        discipline="\uacf5\ud1b5",
        zone="1F",
        critical_only=True,
    )

    assert len(fig.data) == 1
    assert fig.data[0].name == "A100"


def test_gantt_can_build_1000_activity_smoke():
    activities = [
        _activity(str(i), f"A{i:04d}", f"Activity {i}", i % 7 == 0, i)
        for i in range(1000)
    ]

    fig = build_gantt_figure(activities)

    assert len(fig.data) == 1000


def _activity(
    activity_id: str,
    code: str,
    name: str,
    critical: bool,
    offset: int,
    *,
    discipline: str = "\uacf5\ud1b5",
    zone: str = "1F",
) -> Activity:
    start = date(2026, 1, 5) + timedelta(days=offset)
    return Activity(
        activity_id=activity_id,
        code=code,
        name=name,
        wbs_id="wbs",
        discipline=discipline,
        zone=zone,
        duration=1,
        cost=100.0,
        es_workday=offset,
        ef_workday=offset + 1,
        ls_workday=offset,
        lf_workday=offset + 1,
        es_date=start,
        ef_date=start,
        total_float=0 if critical else 2,
        is_critical=critical,
    )
