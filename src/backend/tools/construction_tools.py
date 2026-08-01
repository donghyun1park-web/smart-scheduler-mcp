from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from core.delay_detection import generate_delay_report
from core import db
from core.importer import (
    generate_weekly_report_from_db as generate_weekly_report_from_db_core,
    import_field_input_to_db,
)
from core.number_utils import to_float
from core.reporting import create_weekly_construction_report
from core.recovery import format_recovery_report, suggest_recovery_plans
from core.validation import validate_progress_quantities
from core.dashboard_logic import build_site_manager_dashboard_summary


def input_daily_record(record: dict[str, object]) -> dict[str, object]:
    """Validate and normalize one field daily-progress record."""
    activity_id = str(record.get("activity_id") or "").strip()
    work_date = str(record.get("work_date") or "").strip()
    planned_qty = to_float(record.get("planned_qty"))
    actual_qty = to_float(record.get("actual_qty"))
    normalized = {
        "activity_id": activity_id,
        "work_date": work_date,
        "planned_qty": planned_qty,
        "actual_qty": actual_qty,
        "workers": int(to_float(record.get("workers"))),
        "equipment": str(record.get("equipment") or "").strip(),
        "owner": str(record.get("owner") or "").strip(),
        "remarks": str(record.get("remarks") or "").strip(),
    }
    validation_issues = validate_progress_quantities(
        activity_id,
        activity_id,
        planned_qty,
        actual_qty,
    )
    if not normalized["activity_id"]:
        validation_issues.append("activity_id is required for daily record.")
    if not normalized["work_date"]:
        validation_issues.append(f"{normalized['activity_id']} work_date is required.")
    else:
        date.fromisoformat(str(normalized["work_date"]))
    return {
        "ok": not validation_issues,
        "record": normalized,
        "validation_issues": validation_issues,
    }


def detect_delays(
    site_data: dict[str, object],
    *,
    today: str | None = None,
    top_n: int = 10,
) -> dict[str, object]:
    activities = _activities(site_data)
    today_date = date.fromisoformat(today) if today else None
    delays = generate_delay_report(activities, today=today_date, top_n=top_n)
    return {"ok": True, "delays": delays, "count": len(delays)}


def suggest_recovery(delay_reason_code: str, delay_item: dict[str, object] | None = None) -> dict[str, object]:
    plans = suggest_recovery_plans(delay_reason_code)
    narrative = format_recovery_report(
        delay_item or {"activity_name": "selected activity", "reason_code": delay_reason_code},
        plans,
    )
    return {
        "ok": True,
        "reason_code": delay_reason_code,
        "plans": plans,
        "narrative": narrative,
        "policy": "draft_candidate_review_required",
    }


def generate_weekly_report(
    site_data: dict[str, object],
    output_path: str | Path,
    *,
    report_style: str = "weekly_meeting",
) -> dict[str, object]:
    return create_weekly_construction_report(site_data, output_path, report_style=report_style)


def import_excel_input_to_db(
    db_path: str | Path,
    input_path: str | Path,
    project_id: str | None = None,
) -> dict[str, object]:
    return import_field_input_to_db(db_path, input_path, project_id=project_id)


def generate_weekly_report_from_db(
    db_path: str | Path,
    output_path: str | Path,
    report_style: str = "internal",
) -> dict[str, object]:
    return generate_weekly_report_from_db_core(db_path, output_path, report_style=report_style)


def list_change_log_tool(
    db_path: str,
    target_table: str | None = None,
    target_id: str | None = None,
    limit: int = 100,
) -> dict[str, object]:
    changes = db.list_change_log(db_path, target_table=target_table, target_id=target_id)
    limited = changes[: max(limit, 0)]
    return {
        "ok": True,
        "db_path": str(db_path),
        "count": len(limited),
        "changes": [
            {
                key: value.isoformat() if isinstance(value, date) else value
                for key, value in change.__dict__.items()
            }
            for change in limited
        ],
    }


def summarize_site_status(
    site_data: dict[str, object],
    thresholds: dict[str, float] | None = None,
) -> dict[str, object]:
    summary = build_site_manager_dashboard_summary(site_data, thresholds=thresholds)
    return {"ok": True, "summary": summary}


def _activities(site_data: dict[str, object]) -> list[dict[str, Any]]:
    activities = site_data.get("activities")
    if not isinstance(activities, list):
        return []
    return [activity for activity in activities if isinstance(activity, dict)]
