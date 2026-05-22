"""Labor productivity analysis engine.

Analyzes worker productivity from daily records, identifies trends,
and classifies efficiency status per activity and discipline.

Uses existing daily_records table — no new DB tables needed.

Inspired by DDC Productivity Analyzer.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from core import db
from core.number_utils import percentage


# ---------------------------------------------------------------------------
# Status classification
# ---------------------------------------------------------------------------

PRODUCTIVITY_THRESHOLDS = {
    "우수": 110.0,   # Excellent: >110%
    "정상": 90.0,    # On target: 90-110%
    "부진": 70.0,    # Below: 70-90%
    # Below 70% → "위험" (Critical)
}


def classify_productivity_status(productivity_index: float) -> str:
    """Classify productivity index (actual/planned × 100) into status label."""
    if productivity_index >= PRODUCTIVITY_THRESHOLDS["우수"]:
        return "우수"
    if productivity_index >= PRODUCTIVITY_THRESHOLDS["정상"]:
        return "정상"
    if productivity_index >= PRODUCTIVITY_THRESHOLDS["부진"]:
        return "부진"
    return "위험"


# ---------------------------------------------------------------------------
# Activity-level productivity
# ---------------------------------------------------------------------------


def analyze_activity_productivity(
    db_path: str | Path,
    activity_id: str,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Analyze productivity for a single activity from daily records.

    Returns productivity index, output per worker, trend, and status.
    """
    activities = db.list_activities(db_path)
    act = next((a for a in activities if a.activity_id == activity_id), None)
    if not act:
        return {"ok": False, "error": f"활동을 찾을 수 없습니다: {activity_id}"}

    records = db.list_daily_records(db_path, activity_id=activity_id, end_date=end_date)
    if start_date:
        records = [r for r in records if r.work_date >= start_date]

    if not records:
        return {
            "ok": True,
            "activity_id": activity_id,
            "activity_name": act.name,
            "discipline": act.discipline,
            "record_count": 0,
            "productivity_index": 0.0,
            "status": "정보 부족",
            "message": "일일 기록이 없습니다.",
        }

    total_planned = sum(r.planned_qty for r in records)
    total_actual = sum(r.actual_qty for r in records)
    total_workers = sum(r.workers for r in records)
    total_days = len(records)

    productivity_index = percentage(total_actual, total_planned) if total_planned > 0 else 0.0
    output_per_worker = total_actual / total_workers if total_workers > 0 else 0.0
    avg_workers_per_day = total_workers / total_days if total_days > 0 else 0.0

    status = classify_productivity_status(productivity_index)
    trend = _detect_trend(records)

    return {
        "ok": True,
        "activity_id": activity_id,
        "activity_name": act.name,
        "discipline": act.discipline,
        "record_count": len(records),
        "total_planned_qty": round(total_planned, 2),
        "total_actual_qty": round(total_actual, 2),
        "total_workers": total_workers,
        "avg_workers_per_day": round(avg_workers_per_day, 1),
        "output_per_worker": round(output_per_worker, 2),
        "productivity_index": round(productivity_index, 1),
        "status": status,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# Summary across activities
# ---------------------------------------------------------------------------


def analyze_productivity_summary(
    db_path: str | Path,
    *,
    discipline: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Analyze productivity across all activities, grouped by discipline.

    Returns per-discipline summary and overall metrics.
    """
    activities = db.list_activities(db_path)
    if discipline:
        activities = [a for a in activities if a.discipline == discipline]

    disc_data: dict[str, dict[str, float]] = defaultdict(
        lambda: {"planned": 0, "actual": 0, "workers": 0, "days": 0, "count": 0}
    )

    activity_rows: list[dict[str, Any]] = []

    for act in activities:
        records = db.list_daily_records(db_path, activity_id=act.activity_id, end_date=end_date)
        if start_date:
            records = [r for r in records if r.work_date >= start_date]

        if not records:
            continue

        planned = sum(r.planned_qty for r in records)
        actual = sum(r.actual_qty for r in records)
        workers = sum(r.workers for r in records)
        days = len(records)

        pi = percentage(actual, planned) if planned > 0 else 0.0
        status = classify_productivity_status(pi)

        activity_rows.append({
            "activity_id": act.activity_id,
            "code": act.code,
            "name": act.name,
            "discipline": act.discipline,
            "record_count": days,
            "planned_qty": round(planned, 2),
            "actual_qty": round(actual, 2),
            "workers": workers,
            "productivity_index": round(pi, 1),
            "status": status,
        })

        d = disc_data[act.discipline]
        d["planned"] += planned
        d["actual"] += actual
        d["workers"] += workers
        d["days"] += days
        d["count"] += 1

    disc_rows: list[dict[str, Any]] = []
    for disc in sorted(disc_data.keys()):
        d = disc_data[disc]
        pi = percentage(d["actual"], d["planned"]) if d["planned"] > 0 else 0.0
        opw = d["actual"] / d["workers"] if d["workers"] > 0 else 0.0
        disc_rows.append({
            "discipline": disc,
            "activity_count": int(d["count"]),
            "total_planned": round(d["planned"], 2),
            "total_actual": round(d["actual"], 2),
            "total_workers": int(d["workers"]),
            "output_per_worker": round(opw, 2),
            "productivity_index": round(pi, 1),
            "status": classify_productivity_status(pi),
        })

    # Overall
    total_planned = sum(d["planned"] for d in disc_data.values())
    total_actual = sum(d["actual"] for d in disc_data.values())
    overall_pi = percentage(total_actual, total_planned) if total_planned > 0 else 0.0

    return {
        "ok": True,
        "filter_discipline": discipline,
        "overall_productivity_index": round(overall_pi, 1),
        "overall_status": classify_productivity_status(overall_pi),
        "discipline_summary": disc_rows,
        "activities": activity_rows,
    }


# ---------------------------------------------------------------------------
# Productivity trend
# ---------------------------------------------------------------------------


def get_productivity_trend(
    db_path: str | Path,
    activity_id: str,
    *,
    periods: int = 7,
) -> dict[str, Any]:
    """Get daily productivity trend for an activity.

    Returns per-day productivity index and overall trend direction.
    """
    activities = db.list_activities(db_path)
    act = next((a for a in activities if a.activity_id == activity_id), None)
    if not act:
        return {"ok": False, "error": f"활동을 찾을 수 없습니다: {activity_id}"}

    records = db.list_daily_records(db_path, activity_id=activity_id)
    records.sort(key=lambda r: r.work_date)

    # Take last N records
    recent = records[-periods:] if len(records) > periods else records

    if not recent:
        return {
            "ok": True,
            "activity_id": activity_id,
            "trend": "정보 부족",
            "data_points": [],
        }

    data_points: list[dict[str, Any]] = []
    for r in recent:
        pi = percentage(r.actual_qty, r.planned_qty) if r.planned_qty > 0 else 0.0
        opw = r.actual_qty / r.workers if r.workers > 0 else 0.0
        data_points.append({
            "date": r.work_date.isoformat(),
            "planned_qty": r.planned_qty,
            "actual_qty": r.actual_qty,
            "workers": r.workers,
            "productivity_index": round(pi, 1),
            "output_per_worker": round(opw, 2),
        })

    trend = _detect_trend(recent)

    return {
        "ok": True,
        "activity_id": activity_id,
        "activity_name": act.name,
        "trend": trend,
        "data_points": data_points,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_trend(records: list) -> str:
    """Detect productivity trend from daily records: 개선/유지/하락."""
    if len(records) < 3:
        return "정보 부족"

    # Split into first half and second half
    mid = len(records) // 2
    first_half = records[:mid]
    second_half = records[mid:]

    def _avg_pi(recs: list) -> float:
        planned = sum(r.planned_qty for r in recs)
        actual = sum(r.actual_qty for r in recs)
        return percentage(actual, planned) if planned > 0 else 0.0

    pi_first = _avg_pi(first_half)
    pi_second = _avg_pi(second_half)

    diff = pi_second - pi_first
    if diff > 5.0:
        return "개선"
    if diff < -5.0:
        return "하락"
    return "유지"
