from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

from core.number_utils import to_float


MILESTONE_PROGRESS = {
    "not_started": 0.0,
    "planned": 0.0,
    "ready": 0.0,
    "in_progress": 50.0,
    "started": 50.0,
    "completed": 100.0,
    "complete": 100.0,
    "done": 100.0,
}


def calculate_quantity_progress(planned_qty: float, actual_qty: float) -> float:
    """Return quantity progress as a percentage."""
    if planned_qty <= 0:
        return 0.0
    return round((actual_qty / planned_qty) * 100, 2)


def calculate_weighted_progress(items: Iterable[Mapping[str, Any]]) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for item in items:
        weight = to_float(item.get("weight", item.get("amount", 0.0)))
        progress_pct = to_float(item.get("progress_pct", 0.0))
        if weight <= 0:
            continue
        weighted_sum += progress_pct * weight
        total_weight += weight
    if total_weight <= 0:
        return 0.0
    return round(weighted_sum / total_weight, 2)


def calculate_milestone_progress(status: str) -> float:
    return MILESTONE_PROGRESS.get(status.strip().lower(), 0.0)


def summarize_progress(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    prepared: list[dict[str, Any]] = []
    for row in rows:
        progress_pct = calculate_quantity_progress(
            to_float(row.get("planned_qty")),
            to_float(row.get("actual_qty")),
        )
        prepared.append({**dict(row), "progress_pct": progress_pct})

    return {
        "overall_progress_pct": calculate_weighted_progress(prepared),
        "by_discipline": _group_progress(prepared, "discipline"),
        "by_zone": _group_progress(prepared, "zone"),
    }


def get_activity_progress_summary(
    db_path: str | Path,
    activity_id: str,
) -> dict[str, Any]:
    """Return a one-shot progress summary for a single activity.

    Aggregates DailyRecord rows for ``activity_id`` and returns:
      - ``actual_start_date`` / ``actual_finish_date`` (min/max work_date, or None)
      - ``planned_qty_total`` / ``actual_qty_total`` (sums across records)
      - ``progress_pct`` (qty-based; 0.0 when no daily records or planned=0)
      - ``daily_record_count``

    Designed for "이 작업 실제로 언제 시작/끝났고 진척률 몇 %?" lookups
    without forcing callers to load and aggregate DailyRecord lists.
    """
    # Import locally to avoid a circular import (core.db imports core.progress).
    from core import db as _db

    records = _db.list_daily_records(db_path, activity_id=activity_id)
    if not records:
        return {
            "activity_id": activity_id,
            "actual_start_date": None,
            "actual_finish_date": None,
            "planned_qty_total": 0.0,
            "actual_qty_total": 0.0,
            "progress_pct": 0.0,
            "daily_record_count": 0,
        }
    # records sorted by work_date by list_daily_records
    work_dates = [r.work_date for r in records if r.work_date]
    actual_started = [r.work_date for r in records if r.actual_qty > 0 and r.work_date]
    planned_total = sum(r.planned_qty for r in records)
    actual_total = sum(r.actual_qty for r in records)
    return {
        "activity_id": activity_id,
        "actual_start_date": (min(actual_started).isoformat() if actual_started else None),
        "actual_finish_date": (max(actual_started).isoformat() if actual_started else None),
        "planned_qty_total": float(planned_total),
        "actual_qty_total": float(actual_total),
        "progress_pct": calculate_quantity_progress(planned_total, actual_total),
        "daily_record_count": len(records),
        "first_log_date": min(work_dates).isoformat() if work_dates else None,
        "last_log_date": max(work_dates).isoformat() if work_dates else None,
    }


def get_today_schedule_summary(
    db_path: str | Path,
    *,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Return today's planned start / planned finish / overdue counts.

    Useful for site-manager briefings: "오늘 시작 예정 N건, 완료 예정 M건,
    지연(시작 예정일이 지났는데 아직 착수 기록 없는) K건".

    Activities without scheduled ``es_date`` / ``ef_date`` are ignored.
    """
    from core import db as _db

    today = as_of or date.today()
    activities = _db.list_activities(db_path)

    starts_today: list[dict[str, Any]] = []
    finishes_today: list[dict[str, Any]] = []
    overdue_starts: list[dict[str, Any]] = []

    for act in activities:
        if act.es_date == today:
            starts_today.append({"activity_id": act.activity_id, "code": act.code, "name": act.name, "discipline": act.discipline, "zone": act.zone})
        if act.ef_date == today:
            finishes_today.append({"activity_id": act.activity_id, "code": act.code, "name": act.name, "discipline": act.discipline, "zone": act.zone})
        if act.es_date and act.es_date < today:
            summary = get_activity_progress_summary(db_path, act.activity_id)
            if summary["actual_start_date"] is None and summary["progress_pct"] == 0.0:
                overdue_starts.append({
                    "activity_id": act.activity_id,
                    "code": act.code,
                    "name": act.name,
                    "discipline": act.discipline,
                    "zone": act.zone,
                    "es_date": act.es_date.isoformat(),
                    "days_overdue": (today - act.es_date).days,
                })

    return {
        "as_of": today.isoformat(),
        "starts_today_count": len(starts_today),
        "finishes_today_count": len(finishes_today),
        "overdue_start_count": len(overdue_starts),
        "starts_today": starts_today,
        "finishes_today": finishes_today,
        "overdue_starts": sorted(overdue_starts, key=lambda r: r["days_overdue"], reverse=True),
    }


def _group_progress(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key) or "")].append(row)
    return {
        name: {
            "progress_pct": calculate_weighted_progress(items),
            "weight": sum(to_float(item.get("weight", item.get("amount", 0.0))) for item in items),
        }
        for name, items in grouped.items()
    }
