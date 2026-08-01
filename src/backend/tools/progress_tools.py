"""MCP tools for quick site-manager progress entry and lookup."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

from core import db
from core.progress import get_activity_progress_summary, get_today_schedule_summary


def set_activity_progress(
    project_path: str | Path,
    activity_id: str,
    progress_pct: float,
) -> dict[str, object]:
    """Quick-set ``Activity.progress_pct`` (0–100) for a single activity.

    For situations where daily-record quantity tracking is overkill — e.g.
    a site manager typing "1F 위생 70%" from the field. Daily records take
    precedence when present; this manual value is used only when no daily
    quantities exist for the activity.
    """
    if not 0.0 <= float(progress_pct) <= 100.0:
        return {
            "ok": False,
            "error_code": "INVALID_PROGRESS",
            "error_message": f"progress_pct must be between 0 and 100 (got {progress_pct})",
        }
    activities = {a.activity_id: a for a in db.list_activities(project_path)}
    activity = activities.get(activity_id)
    if activity is None:
        return {
            "ok": False,
            "error_code": "UNKNOWN_ACTIVITY",
            "error_message": f"Unknown activity_id: {activity_id}",
        }
    updated = db.update_activity(project_path, replace(activity, progress_pct=float(progress_pct)))
    return {
        "ok": True,
        "activity_id": updated.activity_id,
        "code": updated.code,
        "progress_pct": updated.progress_pct,
    }


def get_activity_progress(
    project_path: str | Path,
    activity_id: str,
) -> dict[str, object]:
    """Return aggregated progress for a single activity.

    Combines the manual ``progress_pct`` and the daily-record rollup so the
    caller sees both signals and can decide which to trust.
    """
    activities = {a.activity_id: a for a in db.list_activities(project_path)}
    activity = activities.get(activity_id)
    if activity is None:
        return {
            "ok": False,
            "error_code": "UNKNOWN_ACTIVITY",
            "error_message": f"Unknown activity_id: {activity_id}",
        }
    summary = get_activity_progress_summary(project_path, activity_id)
    return {
        "ok": True,
        "code": activity.code,
        "name": activity.name,
        "manual_progress_pct": float(activity.progress_pct),
        "daily_progress_pct": summary["progress_pct"],
        "actual_start_date": summary["actual_start_date"],
        "actual_finish_date": summary["actual_finish_date"],
        "daily_record_count": summary["daily_record_count"],
        "planned_qty_total": summary["planned_qty_total"],
        "actual_qty_total": summary["actual_qty_total"],
    }


def get_today_schedule(
    project_path: str | Path,
    as_of: str | None = None,
) -> dict[str, object]:
    """Return today's planned starts/finishes and overdue-start lists."""
    today = date.fromisoformat(as_of) if as_of else None
    return {"ok": True, **get_today_schedule_summary(project_path, as_of=today)}
