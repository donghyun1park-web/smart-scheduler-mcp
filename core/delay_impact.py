"""What-if delay-impact analysis.

Given an activity that slips by ``delay_days``, walk forward through the
relationship graph and compute the maximum knock-on delay reaching each
successor. Returns a tree (BFS order) plus the project-completion delta.

Uses the ES/EF dates already stored on Activity rows from the last CPM
run, so this is a fast estimate that does not re-invoke pyCritical. The
result is an *upper bound* on impact: a successor whose other independent
predecessors give it more slack may finish earlier than reported. Call
out as "예상 영향" / "estimate" in user-facing copy.
"""

from __future__ import annotations

from collections import deque
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from core import db
from core.models import Activity, Relationship


def analyze_delay_impact(
    db_path: str | Path,
    activity_id: str,
    delay_days: int,
) -> dict[str, Any]:
    """Return a successor-cascade impact estimate for ``activity_id`` slipping by ``delay_days``.

    Output shape::

        {
          "ok": True,
          "source": {"activity_id", "code", "name", ...},
          "delay_days": int,
          "impacted_count": int,
          "completion_delta_days": int,
          "original_completion_date": "YYYY-MM-DD" | None,
          "projected_completion_date": "YYYY-MM-DD" | None,
          "tree": [
            {
              "activity_id", "code", "name", "discipline", "zone",
              "depth": int,
              "is_critical": bool,
              "original_start": "YYYY-MM-DD" | None,
              "projected_start": "YYYY-MM-DD" | None,
              "original_finish": "YYYY-MM-DD" | None,
              "projected_finish": "YYYY-MM-DD" | None,
              "shift_days": int,
              "via": "FS|SS|FF",
              "predecessor_code": str
            },
            ...
          ]
        }
    """
    if delay_days <= 0:
        return {
            "ok": False,
            "error_code": "INVALID_DELAY",
            "error_message": f"delay_days must be > 0 (got {delay_days})",
        }

    activities = db.list_activities(db_path)
    by_id = {a.activity_id: a for a in activities}
    target = by_id.get(activity_id)
    if target is None:
        return {
            "ok": False,
            "error_code": "UNKNOWN_ACTIVITY",
            "error_message": f"Unknown activity_id: {activity_id}",
        }

    relationships = db.list_relationships(db_path)
    # Successor adjacency: pred_id -> [(succ_id, rel_type, lag), ...]
    succ_map: dict[str, list[tuple[str, str, int]]] = {}
    for rel in relationships:
        succ_map.setdefault(rel.pred_id, []).append((rel.succ_id, rel.rel_type, rel.lag_days))

    # Per-activity shift in calendar days, plus how each shift was reached.
    shift: dict[str, int] = {activity_id: delay_days}
    via: dict[str, tuple[str, str]] = {}  # succ_id -> (rel_type, pred_code)
    depth: dict[str, int] = {activity_id: 0}
    order: list[str] = []  # BFS traversal order

    queue: deque[str] = deque([activity_id])
    while queue:
        current = queue.popleft()
        current_shift = shift[current]
        for succ_id, rel_type, _lag in succ_map.get(current, []):
            propagated = _propagate(rel_type, current_shift)
            if propagated <= 0:
                continue
            existing = shift.get(succ_id, 0)
            if propagated > existing:
                shift[succ_id] = propagated
                via[succ_id] = (rel_type, by_id[current].code)
                depth[succ_id] = depth.get(current, 0) + 1
                if succ_id not in order:
                    order.append(succ_id)
                queue.append(succ_id)

    # Build tree entries (excluding the source itself)
    tree: list[dict[str, Any]] = []
    for succ_id in order:
        act = by_id.get(succ_id)
        if act is None:
            continue
        shift_days = shift[succ_id]
        rel_type, pred_code = via.get(succ_id, ("?", "?"))
        tree.append({
            "activity_id": succ_id,
            "code": act.code,
            "name": act.name,
            "discipline": act.discipline,
            "zone": act.zone,
            "depth": depth.get(succ_id, 1),
            "is_critical": bool(act.is_critical),
            "original_start": act.es_date.isoformat() if act.es_date else None,
            "projected_start": _shift_iso(act.es_date, shift_days),
            "original_finish": act.ef_date.isoformat() if act.ef_date else None,
            "projected_finish": _shift_iso(act.ef_date, shift_days),
            "shift_days": shift_days,
            "via": rel_type,
            "predecessor_code": pred_code,
        })

    # Project completion delta: among impacted activities, find the largest
    # projected finish vs original max finish.
    original_completion = _max_ef(activities)
    projected_completion = original_completion
    if original_completion is not None:
        # Re-compute the new max finish considering shifts.
        candidates = []
        for act in activities:
            if act.ef_date is None:
                continue
            s = shift.get(act.activity_id, 0)
            candidates.append(act.ef_date + timedelta(days=s))
        if candidates:
            projected_completion = max(candidates)
    completion_delta = (
        (projected_completion - original_completion).days
        if original_completion and projected_completion
        else 0
    )

    return {
        "ok": True,
        "source": {
            "activity_id": target.activity_id,
            "code": target.code,
            "name": target.name,
            "discipline": target.discipline,
            "zone": target.zone,
            "is_critical": bool(target.is_critical),
            "original_start": target.es_date.isoformat() if target.es_date else None,
            "original_finish": target.ef_date.isoformat() if target.ef_date else None,
        },
        "delay_days": delay_days,
        "impacted_count": len(tree),
        "completion_delta_days": completion_delta,
        "original_completion_date": original_completion.isoformat() if original_completion else None,
        "projected_completion_date": projected_completion.isoformat() if projected_completion else None,
        "tree": tree,
    }


def _propagate(rel_type: str, pred_shift: int) -> int:
    """Days a successor moves given its predecessor moved by ``pred_shift``.

    Upper bound — assumes this predecessor is the binding constraint.
    """
    # Both FS and SS push the successor start by the same amount the
    # predecessor's anchor moves. FF only constrains the successor's finish
    # but in practice (no early start constraint) the start can move by the
    # same delta to maintain duration. Treat all three the same here as an
    # upper-bound estimate.
    if rel_type in {"FS", "SS", "FF"}:
        return pred_shift
    return 0


def _shift_iso(d: date | None, shift_days: int) -> str | None:
    if d is None:
        return None
    return (d + timedelta(days=shift_days)).isoformat()


def _max_ef(activities: list[Activity]) -> date | None:
    return max((a.ef_date for a in activities if a.ef_date), default=None)
