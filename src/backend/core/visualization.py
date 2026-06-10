from __future__ import annotations

import plotly.graph_objects as go

from core.models import Activity


CRITICAL_COLOR = "#d62728"
NORMAL_COLOR = "#1f77b4"


def build_gantt_figure(
    activities: list[Activity],
    *,
    wbs_id: str | None = None,
    discipline: str | None = None,
    zone: str | None = None,
    critical_only: bool = False,
) -> go.Figure:
    filtered = [
        activity
        for activity in activities
        if _matches(activity, wbs_id, discipline, zone, critical_only)
        and activity.es_date is not None
        and activity.ef_date is not None
    ]
    fig = go.Figure()
    for activity in filtered:
        assert activity.es_date is not None
        assert activity.ef_date is not None
        fig.add_trace(
            go.Bar(
                x=[max((activity.ef_date - activity.es_date).days + 1, 1)],
                y=[activity.code],
                base=[activity.es_date],
                orientation="h",
                name=activity.code,
                marker={"color": CRITICAL_COLOR if activity.is_critical else NORMAL_COLOR},
                customdata=[
                    [
                        activity.name,
                        activity.duration,
                        activity.discipline,
                        activity.zone,
                        activity.es_workday,
                        activity.ef_workday,
                        activity.ls_workday,
                        activity.lf_workday,
                        activity.total_float,
                    ]
                ],
                hovertemplate=(
                    "code=%{y}<br>"
                    "name=%{customdata[0]}<br>"
                    "duration=%{customdata[1]}<br>"
                    "discipline=%{customdata[2]}<br>"
                    "zone=%{customdata[3]}<br>"
                    "ES/EF=%{customdata[4]}/%{customdata[5]}<br>"
                    "LS/LF=%{customdata[6]}/%{customdata[7]}<br>"
                    "total_float=%{customdata[8]}<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        title="Gantt",
        barmode="stack",
        xaxis_title="Date",
        yaxis_title="Activity",
        showlegend=False,
        height=max(400, min(1200, 28 * len(filtered) + 120)),
    )
    return fig


def _matches(
    activity: Activity,
    wbs_id: str | None,
    discipline: str | None,
    zone: str | None,
    critical_only: bool,
) -> bool:
    return (
        (wbs_id is None or activity.wbs_id == wbs_id)
        and (discipline is None or activity.discipline == discipline)
        and (zone is None or activity.zone == zone)
        and (not critical_only or activity.is_critical)
    )
