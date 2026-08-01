from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from core import db
from core.cost import calculate_billing_rate, calculate_cost_execution_rate
from core.delay_detection import generate_delay_report
from core.evm import calculate_evm_totals
from core.importer import generate_weekly_report_from_db
from core.models import Project
from core.number_utils import to_float
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
    as_of_date: date | None = None,
) -> dict[str, Any]:
    threshold_values = {**DEFAULT_DASHBOARD_THRESHOLDS, **dict(thresholds or {})}
    project = _mapping(site_data.get("project"))
    activities = [_mapping(activity) for activity in _list(site_data.get("activities"))]
    planned_progress = to_float(project.get("planned_progress_pct"))
    actual_progress = calculate_weighted_progress(
        [
            {
                "progress_pct": to_float(activity.get("actual_progress_pct")),
                "weight": to_float(activity.get("weight")),
            }
            for activity in activities
        ]
    )
    variance = round(actual_progress - planned_progress, 2)
    cost_rates = [
        calculate_cost_execution_rate(
            to_float(activity.get("execution_budget")),
            to_float(activity.get("invested_cost")),
        )
        for activity in activities
        if to_float(activity.get("execution_budget")) > 0
    ]
    billing_rates = [
        calculate_billing_rate(
            to_float(activity.get("contract_amount")),
            to_float(activity.get("billing_amount")),
        )
        for activity in activities
        if to_float(activity.get("contract_amount")) > 0
    ]
    delay_issues = generate_delay_report(activities, today=as_of_date, top_n=100)
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
        "evm": calculate_evm_totals([dict(activity) for activity in activities]),
        "status": _status_from_variance(variance, threshold_values),
        "thresholds": threshold_values,
    }


def load_site_dashboard_data_from_db(
    db_path: str | Path,
    *,
    project_id: str | None = None,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Load dashboard-ready site status directly from a SQLite scheduler DB."""
    as_of = as_of_date or date.today()
    project = db.get_project(db_path, project_id) if project_id else None
    if project is None:
        summary_project = db.load_project_summary(db_path).get("project")
        project = summary_project if isinstance(summary_project, Project) else None
    settings = db.get_project_settings(db_path, getattr(project, "project_id", "")) if project is not None else None
    activities = _db_activities(db_path, as_of)
    site_data = {
        "project": {
            "project_id": getattr(project, "project_id", ""),
            "name": getattr(project, "name", ""),
            "report_week": as_of.isoformat(),
            "planned_progress_pct": _average([to_float(activity.get("planned_progress_pct")) for activity in activities]),
        },
        "activities": activities,
    }
    threshold_values = settings.thresholds if settings is not None and settings.thresholds else None
    summary = build_site_manager_dashboard_summary(site_data, thresholds=threshold_values, as_of_date=as_of)
    delay_issues = generate_delay_report(activities, today=as_of, top_n=100)
    cost_risks = [activity for activity in activities if _cost_risk(activity)]
    materials = [material for activity in activities for material in _list(activity.get("materials"))]
    inspections = [inspection for activity in activities for inspection in _list(activity.get("inspections"))]
    material_delay_count = sum(1 for issue in delay_issues if issue.get("reason_code") == "material_delay")
    inspection_delay_count = sum(1 for issue in delay_issues if issue.get("reason_code") == "inspection_delay")
    serious_risk_count = sum(1 for issue in delay_issues if issue.get("severity") in {"danger", "critical"})
    summary_payload = {
        "planned_progress_pct": summary["planned_progress_pct"],
        "actual_progress_pct": summary["actual_progress_pct"],
        "progress_gap_pct": summary["progress_variance_pct"],
        "cost_execution_rate": summary["cost_execution_rate"],
        "billing_rate": summary["billing_rate"],
        "delayed_count": summary["delayed_activity_count"],
        "serious_risk_count": serious_risk_count,
        "material_delay_count": material_delay_count,
        "inspection_delay_count": inspection_delay_count,
        "evm": summary["evm"],
        "status": summary["status"],
        "risk_discipline": summary["risk_discipline"],
        "key_risks": summary["key_risks"],
    }
    return {
        "project": site_data["project"],
        "as_of_date": as_of.isoformat(),
        "summary": summary_payload,
        "disciplines": _group_activity_status(activities, "discipline"),
        "zones": _group_activity_status(activities, "zone"),
        "delayed_top10": delay_issues[:10],
        "cost_risks": cost_risks,
        "materials": materials,
        "inspections": inspections,
        "activities": activities,
    }


def build_dashboard_report_file(
    db_path: str | Path,
    out_dir: str | Path,
    *,
    project_id: str | None = None,
    report_style: str = "internal",
) -> dict[str, object]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{project_id}" if project_id else ""
    output_path = output_dir / f"dashboard_report{suffix}_{report_style}.xlsx"
    result = generate_weekly_report_from_db(db_path, output_path, report_style=report_style)
    return {**result, "report_style": report_style}





def _risk_discipline(activities: list[Mapping[str, Any]], issues: list[dict[str, Any]]) -> str:
    by_id = {activity.get("activity_id"): activity for activity in activities}
    scores: dict[str, float] = defaultdict(float)
    for issue in issues:
        activity = by_id.get(issue.get("activity_id"), {})
        discipline = str(activity.get("discipline") or "")
        scores[discipline] += to_float(issue.get("risk_score"))
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


def _db_activities(db_path: str | Path, as_of_date: date) -> list[dict[str, Any]]:
    cost_items = {item.activity_id: item for item in db.list_cost_items(db_path)}
    materials = _group_records(db.list_materials(db_path))
    inspections = _group_records(db.list_inspections(db_path))
    activities: list[dict[str, Any]] = []
    for activity in db.list_activities(db_path):
        cumulative = db.get_cumulative_qty(db_path, activity.activity_id)
        cost_item = cost_items.get(activity.activity_id)
        actual_progress = to_float(cumulative["progress_pct"])
        planned_progress = 100.0 if activity.ef_date is not None and activity.ef_date <= as_of_date else actual_progress
        activities.append(
            {
                "activity_id": activity.activity_id,
                "name": activity.name,
                "discipline": activity.discipline,
                "zone": activity.zone,
                "planned_qty": cumulative["planned_qty"],
                "actual_qty": cumulative["actual_qty"],
                "planned_progress_pct": planned_progress,
                "actual_progress_pct": actual_progress,
                "weight": activity.cost or 1.0,
                "start_date": activity.es_date.isoformat() if activity.es_date else "",
                "finish_date": activity.ef_date.isoformat() if activity.ef_date else "",
                "status": "completed" if actual_progress >= 100 else "in_progress",
                "owner": _latest_owner(db_path, activity.activity_id),
                "contract_amount": cost_item.contract_amount if cost_item else 0.0,
                "execution_budget": cost_item.execution_budget if cost_item else 0.0,
                "invested_cost": cost_item.invested_cost if cost_item else 0.0,
                "billing_amount": cost_item.billing_amount if cost_item else 0.0,
                "materials": materials.get(activity.activity_id, []),
                "inspections": inspections.get(activity.activity_id, []),
            }
        )
    return activities


def _latest_owner(db_path: str | Path, activity_id: str) -> str:
    records = db.list_daily_records(db_path, activity_id=activity_id)
    for record in reversed(records):
        if record.owner:
            return record.owner
    return ""


def _group_records(records: list[Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record.activity_id].append(
            {
                key: value.isoformat() if isinstance(value, date) else value
                for key, value in record.__dict__.items()
                if key not in {"created_at", "updated_at"}
            }
        )
    return dict(grouped)


def _cost_risk(activity: Mapping[str, Any]) -> bool:
    progress = to_float(activity.get("actual_progress_pct"))
    execution_budget = to_float(activity.get("execution_budget"))
    invested_cost = to_float(activity.get("invested_cost"))
    if execution_budget <= 0:
        return False
    return calculate_cost_execution_rate(execution_budget, invested_cost) - progress > 10


def _group_activity_status(activities: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for activity in activities:
        grouped[str(activity.get(key) or "")].append(activity)
    rows: list[dict[str, Any]] = []
    for name, items in sorted(grouped.items()):
        rows.append(
            {
                key: name,
                "activity_count": len(items),
                "actual_progress_pct": calculate_weighted_progress(
                    {
                        "progress_pct": to_float(item.get("actual_progress_pct")),
                        "weight": to_float(item.get("weight")),
                    }
                    for item in items
                ),
            }
        )
    return rows


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
