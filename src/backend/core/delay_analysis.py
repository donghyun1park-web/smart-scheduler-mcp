"""Schedule delay analysis engine.

Provides formal delay classification (excusable/non-excusable/concurrent),
delay event recording, time extension claim calculation, and delay reports.

Inspired by DDC Schedule Delay Analyzer, adapted to function-based pattern.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from core import db
from core.models import (
    DELAY_CAUSE_KR,
    DELAY_CAUSES,
    DELAY_TYPE_KR,
    DELAY_TYPES,
    DelayEvent,
)


# ---------------------------------------------------------------------------
# Record delay event
# ---------------------------------------------------------------------------


def record_delay_event_to_db(
    db_path: str | Path,
    activity_id: str,
    delay_type: str,
    cause_code: str,
    *,
    responsible_party: str = "",
    start_date: date | None = None,
    end_date: date | None = None,
    delay_days: int = 0,
    cost_impact: float = 0.0,
    description: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Record a classified delay event for an activity.

    Parameters
    ----------
    delay_type : 'excusable_compensable', 'excusable_non_compensable',
                 'non_excusable', 'concurrent'
    cause_code : 'owner_change', 'design_error', 'weather', 'material_delay',
                 'labor_shortage', 'permit_delay', 'site_condition', 'subcontractor', 'other'
    delay_days : number of calendar days delayed (auto-calculated from dates if 0)
    dry_run : if True, validates but does not persist
    """
    # Validate
    if delay_type not in DELAY_TYPES:
        return {"ok": False, "error": f"유효하지 않은 지연유형: {delay_type}. 가능: {sorted(DELAY_TYPES)}"}
    if cause_code not in DELAY_CAUSES:
        return {"ok": False, "error": f"유효하지 않은 원인코드: {cause_code}. 가능: {sorted(DELAY_CAUSES)}"}

    # Verify activity exists
    activities = db.list_activities(db_path)
    act = next((a for a in activities if a.activity_id == activity_id), None)
    if not act:
        return {"ok": False, "error": f"활동을 찾을 수 없습니다: {activity_id}"}

    # Auto-calc delay_days if dates provided
    actual_delay_days = delay_days
    if start_date and end_date and delay_days == 0:
        actual_delay_days = (end_date - start_date).days

    delay_event_id = f"dly-{uuid.uuid4().hex[:8]}"
    event = DelayEvent(
        delay_event_id=delay_event_id,
        activity_id=activity_id,
        delay_type=delay_type,
        cause_code=cause_code,
        responsible_party=responsible_party,
        start_date=start_date,
        end_date=end_date,
        delay_days=actual_delay_days,
        cost_impact=cost_impact,
        description=description,
        status="open",
    )

    if not dry_run:
        db.create_delay_event(db_path, event)

    return {
        "ok": True,
        "dry_run": dry_run,
        "delay_event_id": delay_event_id,
        "activity_id": activity_id,
        "activity_name": act.name,
        "delay_type": delay_type,
        "delay_type_kr": DELAY_TYPE_KR.get(delay_type, delay_type),
        "cause_code": cause_code,
        "cause_kr": DELAY_CAUSE_KR.get(cause_code, cause_code),
        "delay_days": actual_delay_days,
        "cost_impact": cost_impact,
    }


# ---------------------------------------------------------------------------
# List delay events
# ---------------------------------------------------------------------------


def list_delay_events_from_db(
    db_path: str | Path,
    *,
    activity_id: str | None = None,
    delay_type: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """List delay events with optional filters."""
    events = db.list_delay_events(
        db_path,
        activity_id=activity_id,
        delay_type=delay_type,
        status=status,
    )
    return {
        "ok": True,
        "count": len(events),
        "events": [
            {
                "delay_event_id": e.delay_event_id,
                "activity_id": e.activity_id,
                "delay_type": e.delay_type,
                "delay_type_kr": DELAY_TYPE_KR.get(e.delay_type, e.delay_type),
                "cause_code": e.cause_code,
                "cause_kr": DELAY_CAUSE_KR.get(e.cause_code, e.cause_code),
                "responsible_party": e.responsible_party,
                "start_date": e.start_date.isoformat() if e.start_date else None,
                "end_date": e.end_date.isoformat() if e.end_date else None,
                "delay_days": e.delay_days,
                "cost_impact": e.cost_impact,
                "description": e.description,
                "status": e.status,
            }
            for e in events
        ],
    }


# ---------------------------------------------------------------------------
# Delay analysis report
# ---------------------------------------------------------------------------


def generate_delay_analysis(
    db_path: str | Path,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Generate comprehensive delay analysis report.

    Returns summary by type, by cause, critical path impact, and total delay days.
    """
    events = db.list_delay_events(db_path)

    # Filter by date range if provided
    if start_date:
        events = [e for e in events if e.start_date and e.start_date >= start_date]
    if end_date:
        events = [e for e in events if e.start_date and e.start_date <= end_date]

    if not events:
        return {
            "ok": True,
            "total_events": 0,
            "total_delay_days": 0,
            "total_cost_impact": 0,
            "by_type": {},
            "by_cause": {},
            "events": [],
        }

    # Aggregate by type
    by_type: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "days": 0, "cost": 0.0}
    )
    for e in events:
        t = by_type[e.delay_type]
        t["count"] += 1
        t["days"] += e.delay_days
        t["cost"] += e.cost_impact

    by_type_rows = {
        dtype: {
            "type_kr": DELAY_TYPE_KR.get(dtype, dtype),
            "count": d["count"],
            "delay_days": d["days"],
            "cost_impact": round(d["cost"], 0),
        }
        for dtype, d in sorted(by_type.items())
    }

    # Aggregate by cause
    by_cause: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "days": 0, "cost": 0.0}
    )
    for e in events:
        c = by_cause[e.cause_code]
        c["count"] += 1
        c["days"] += e.delay_days
        c["cost"] += e.cost_impact

    by_cause_rows = {
        cause: {
            "cause_kr": DELAY_CAUSE_KR.get(cause, cause),
            "count": d["count"],
            "delay_days": d["days"],
            "cost_impact": round(d["cost"], 0),
        }
        for cause, d in sorted(by_cause.items())
    }

    total_days = sum(e.delay_days for e in events)
    total_cost = sum(e.cost_impact for e in events)

    return {
        "ok": True,
        "total_events": len(events),
        "total_delay_days": total_days,
        "total_cost_impact": round(total_cost, 0),
        "by_type": by_type_rows,
        "by_cause": by_cause_rows,
    }


# ---------------------------------------------------------------------------
# Time extension claim
# ---------------------------------------------------------------------------


def calculate_time_extension_entitlement(
    db_path: str | Path,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Calculate time extension entitlement from excusable delays.

    Only excusable delays (compensable + non-compensable) qualify for
    time extension. Compensable delays also qualify for cost compensation.
    """
    events = db.list_delay_events(db_path)

    if start_date:
        events = [e for e in events if e.start_date and e.start_date >= start_date]
    if end_date:
        events = [e for e in events if e.start_date and e.start_date <= end_date]

    # Excusable delays
    excusable = [
        e for e in events
        if e.delay_type in ("excusable_compensable", "excusable_non_compensable")
    ]
    compensable = [e for e in events if e.delay_type == "excusable_compensable"]
    non_excusable = [e for e in events if e.delay_type == "non_excusable"]
    concurrent = [e for e in events if e.delay_type == "concurrent"]

    excusable_days = sum(e.delay_days for e in excusable)
    compensable_days = sum(e.delay_days for e in compensable)
    compensable_cost = sum(e.cost_impact for e in compensable)

    return {
        "ok": True,
        "recommended_extension_days": excusable_days,
        "excusable_events": len(excusable),
        "excusable_days": excusable_days,
        "compensable_events": len(compensable),
        "compensable_days": compensable_days,
        "compensable_cost": round(compensable_cost, 0),
        "non_excusable_events": len(non_excusable),
        "non_excusable_days": sum(e.delay_days for e in non_excusable),
        "concurrent_events": len(concurrent),
        "concurrent_days": sum(e.delay_days for e in concurrent),
        "summary_kr": (
            f"공기연장 권고: {excusable_days}일 "
            f"(면책보상가능 {compensable_days}일, "
            f"면책보상불가 {excusable_days - compensable_days}일), "
            f"보상금액 {compensable_cost:,.0f}원"
        ),
    }
