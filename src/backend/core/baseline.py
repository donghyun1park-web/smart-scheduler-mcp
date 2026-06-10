"""Baseline schedule management.

Establishes a frozen snapshot of the current schedule (start/finish/duration
per activity) so that later progress can be measured against an agreed plan.

Built entirely on the existing ``BaselineSnapshot`` model and the
``create_baseline_snapshot`` / ``list_baseline_snapshots`` DB functions — no
new tables or models required.

A "baseline" is a set of ``BaselineSnapshot`` rows that share one
``baseline_id``. The human-friendly label is stored in the ``revision`` field.
"""
from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from typing import Any

from core import db
from core.models import BaselineSnapshot


def establish_baseline(
    db_path: str | Path,
    *,
    label: str = "기준공정표",
    approved_by: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Freeze the current schedule as a new baseline.

    Captures each activity's planned start (es_date), finish (ef_date) and
    duration into ``BaselineSnapshot`` rows sharing a fresh ``baseline_id``.

    Parameters
    ----------
    label : human-friendly name stored in ``revision`` (e.g. '착공 기준공정표')
    approved_by : who approved this baseline
    dry_run : if True, validates and previews but does not persist
    """
    activities = db.list_activities(db_path)
    if not activities:
        return {"ok": False, "error": "활동이 없습니다. 먼저 공정표를 등록하세요."}

    project_info = db.load_project_summary(db_path)
    project = project_info.get("project")
    project_id = getattr(project, "project_id", "") if project else ""

    baseline_id = f"bl-{uuid.uuid4().hex[:8]}"

    snapshots: list[BaselineSnapshot] = []
    for act in activities:
        snapshots.append(
            BaselineSnapshot(
                snapshot_id=f"bls-{uuid.uuid4().hex[:8]}",
                baseline_id=baseline_id,
                project_id=project_id,
                activity_id=act.activity_id,
                start_date=act.es_date,
                finish_date=act.ef_date,
                duration=act.duration,
                revision=label,
                approved_by=approved_by,
            )
        )

    if not dry_run:
        for snap in snapshots:
            db.create_baseline_snapshot(db_path, snap)

    finishes = [s.finish_date for s in snapshots if s.finish_date]
    starts = [s.start_date for s in snapshots if s.start_date]
    return {
        "ok": True,
        "dry_run": dry_run,
        "baseline_id": baseline_id,
        "label": label,
        "approved_by": approved_by,
        "activity_count": len(snapshots),
        "project_start": min(starts).isoformat() if starts else None,
        "project_finish": max(finishes).isoformat() if finishes else None,
    }


def list_baselines(db_path: str | Path) -> dict[str, Any]:
    """List available baselines (grouped by baseline_id)."""
    snapshots = db.list_baseline_snapshots(db_path)

    grouped: dict[str, dict[str, Any]] = {}
    for snap in snapshots:
        g = grouped.setdefault(
            snap.baseline_id,
            {
                "baseline_id": snap.baseline_id,
                "label": snap.revision,
                "approved_by": snap.approved_by,
                "created_at": snap.created_at,
                "activity_count": 0,
            },
        )
        g["activity_count"] += 1

    baselines = sorted(
        grouped.values(),
        key=lambda b: b.get("created_at") or "",
        reverse=True,
    )
    return {"ok": True, "count": len(baselines), "baselines": baselines}


def compare_to_baseline(
    db_path: str | Path,
    *,
    baseline_id: str | None = None,
    top_n: int = 20,
) -> dict[str, Any]:
    """Compare the current schedule against a baseline.

    Reports per-activity finish-date drift (현재 - 기준, +면 지연) and the
    overall project finish shift. If ``baseline_id`` is omitted, uses the most
    recent baseline.
    """
    snapshots = db.list_baseline_snapshots(db_path, baseline_id=baseline_id)
    if not snapshots:
        if baseline_id:
            return {"ok": False, "error": f"기준선을 찾을 수 없습니다: {baseline_id}"}
        return {"ok": False, "error": "수립된 기준공정표가 없습니다. establish_baseline을 먼저 실행하세요."}

    # If no baseline_id given, snapshots may span multiple baselines — pick latest.
    if baseline_id is None:
        latest_id = max(
            snapshots,
            key=lambda s: s.created_at or "",
        ).baseline_id
        snapshots = [s for s in snapshots if s.baseline_id == latest_id]
        baseline_id = latest_id

    label = snapshots[0].revision
    current = {a.activity_id: a for a in db.list_activities(db_path)}

    rows: list[dict[str, Any]] = []
    base_finishes: list[date] = []
    curr_finishes: list[date] = []

    for snap in snapshots:
        act = current.get(snap.activity_id)
        if not act:
            continue  # activity removed since baseline

        finish_drift = None
        if snap.finish_date and act.ef_date:
            finish_drift = (act.ef_date - snap.finish_date).days
        duration_drift = act.duration - snap.duration

        if snap.finish_date:
            base_finishes.append(snap.finish_date)
        if act.ef_date:
            curr_finishes.append(act.ef_date)

        rows.append({
            "activity_id": snap.activity_id,
            "name": act.name,
            "discipline": act.discipline,
            "baseline_finish": snap.finish_date.isoformat() if snap.finish_date else None,
            "current_finish": act.ef_date.isoformat() if act.ef_date else None,
            "finish_drift_days": finish_drift,
            "baseline_duration": snap.duration,
            "current_duration": act.duration,
            "duration_drift_days": duration_drift,
        })

    # Sort by largest delay first (None drift sinks to bottom)
    rows.sort(key=lambda r: (r["finish_drift_days"] is None, -(r["finish_drift_days"] or 0)))

    base_finish = max(base_finishes).isoformat() if base_finishes else None
    curr_finish = max(curr_finishes).isoformat() if curr_finishes else None
    project_drift = None
    if base_finishes and curr_finishes:
        project_drift = (max(curr_finishes) - max(base_finishes)).days

    delayed = [r for r in rows if (r["finish_drift_days"] or 0) > 0]
    ahead = [r for r in rows if (r["finish_drift_days"] or 0) < 0]

    return {
        "ok": True,
        "baseline_id": baseline_id,
        "label": label,
        "compared_activities": len(rows),
        "baseline_project_finish": base_finish,
        "current_project_finish": curr_finish,
        "project_finish_drift_days": project_drift,
        "delayed_count": len(delayed),
        "ahead_count": len(ahead),
        "activities": rows[:top_n],
    }
