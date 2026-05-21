from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from core.cost import calculate_billing_rate, calculate_cost_execution_rate
from core.delay_detection import generate_delay_report
from core.progress import calculate_weighted_progress


DEFAULT_DASHBOARD_THRESHOLDS = {
    "green_min": -3.0,
    "yellow_min": -7.0,
    "orange_min": -15.0,
}


def build_site_manager_dashboard_summary(
    site_data: Mapping[str, Any],
    *,
    thresholds: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    threshold_values = {**DEFAULT_DASHBOARD_THRESHOLDS, **dict(thresholds or {})}
    project = _mapping(site_data.get("project"))
    activities = [_mapping(activity) for activity in _list(site_data.get("activities"))]
    planned_progress = _float(project.get("planned_progress_pct"))
    actual_progress = calculate_weighted_progress(
        [
            {
                "progress_pct": _float(activity.get("actual_progress_pct")),
                "weight": _float(activity.get("weight")),
            }
            for activity in activities
        ]
    )
    variance = round(actual_progress - planned_progress, 2)
    cost_rates = [
        calculate_cost_execution_rate(
            _float(activity.get("execution_budget")),
            _float(activity.get("invested_cost")),
        )
        for activity in activities
        if _float(activity.get("execution_budget")) > 0
    ]
    billing_rates = [
        calculate_billing_rate(
            _float(activity.get("contract_amount")),
            _float(activity.get("billing_amount")),
        )
        for activity in activities
        if _float(activity.get("contract_amount")) > 0
    ]
    delay_issues = generate_delay_report(activities, top_n=100)
    risk_discipline = _risk_discipline(activities, delay_issues)
    key_risks = [str(issue.get("message")) for issue in delay_issues[:5]]
    return {
        "project_id": project.get("project_id", ""),
        "project_name": project.get("name", ""),
        "planned_progress_pct": planned_progress,
        "actual_progress_pct": actual_progress,
        "progress_variance_pct": variance,
        "cost_execution_rate": _average(cost_rates),
        "billing_rate": _average(billing_rates),
        "delayed_activity_count": len({issue.get("activity_id") for issue in delay_issues}),
        "risk_discipline": risk_discipline,
        "key_risks": key_risks,
        "status": _status_from_variance(variance, threshold_values),
        "thresholds": threshold_values,
    }


def render_site_manager_dashboard(summary: Mapping[str, Any]) -> None:
    import streamlit as st

    st.title("현장소장 대시보드")
    metric_cols = st.columns(4)
    metric_cols[0].metric("계획공정률", f"{_float(summary.get('planned_progress_pct')):.1f}%")
    metric_cols[1].metric(
        "실적공정률",
        f"{_float(summary.get('actual_progress_pct')):.1f}%",
        f"{_float(summary.get('progress_variance_pct')):.1f}%",
    )
    metric_cols[2].metric("원가집행률", f"{_float(summary.get('cost_execution_rate')):.1f}%")
    metric_cols[3].metric("기성률", f"{_float(summary.get('billing_rate')):.1f}%")
    st.write(
        {
            "status": summary.get("status"),
            "delayed_activity_count": summary.get("delayed_activity_count"),
            "risk_discipline": summary.get("risk_discipline"),
            "key_risks": summary.get("key_risks", []),
        }
    )


def _risk_discipline(activities: list[Mapping[str, Any]], issues: list[dict[str, Any]]) -> str:
    by_id = {activity.get("activity_id"): activity for activity in activities}
    scores: dict[str, float] = defaultdict(float)
    for issue in issues:
        activity = by_id.get(issue.get("activity_id"), {})
        discipline = str(activity.get("discipline") or "")
        scores[discipline] += _float(issue.get("risk_score"))
    if not scores:
        return ""
    return max(scores, key=lambda discipline: scores[discipline])


def _status_from_variance(variance: float, thresholds: Mapping[str, float]) -> str:
    if variance >= thresholds["green_min"]:
        return "green"
    if variance >= thresholds["yellow_min"]:
        return "yellow"
    if variance >= thresholds["orange_min"]:
        return "orange"
    return "red"


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def _float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
