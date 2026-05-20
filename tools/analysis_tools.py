from __future__ import annotations

from pathlib import Path

from core import db
from core.cpm import run_cpm_for_project


def calculate_cpm(project_path: str | Path) -> dict[str, object]:
    """Run CPM on the project and persist computed dates back to activities.

    Returns ``ok=False`` only when dependency cycles are detected
    (``cycles_detected`` lists them); other failure modes raise.
    """
    result = run_cpm_for_project(project_path)
    return {
        "ok": not bool(result.cycles_detected),
        "total_duration_days": result.total_duration_days,
        "critical_count": result.critical_count,
        "completion_date": result.completion_date.isoformat()
        if result.completion_date
        else None,
        "cycles_detected": result.cycles_detected or [],
    }


def get_critical_path(project_path: str | Path) -> dict[str, object]:
    """Return activities flagged ``is_critical`` ordered by ES workday then code.

    Assumes ``calculate_cpm`` has been run previously; otherwise the list is empty.
    """
    activities = [
        activity
        for activity in db.list_activities(project_path)
        if activity.is_critical
    ]
    activities.sort(key=lambda activity: (activity.es_workday or 0, activity.code))
    return {
        "ok": True,
        "critical_path": [
            {
                "code": activity.code,
                "name": activity.name,
                "duration": activity.duration,
                "discipline": activity.discipline,
                "zone": activity.zone,
                "es_date": activity.es_date.isoformat() if activity.es_date else None,
                "ef_date": activity.ef_date.isoformat() if activity.ef_date else None,
                "total_float": activity.total_float,
            }
            for activity in activities
        ],
    }
