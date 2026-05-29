from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from core import db
from core.models import ChangeLogEntry, Relationship


def suggest_construction_relationships(
    db_path: str,
    *,
    project_id: str | None = None,
    zone: str | None = None,
    discipline: str | None = None,
    relationship_type: str = "FS",
    default_lag: int = 0,
) -> list[dict[str, object]]:
    """Suggest dry-run construction relationships without writing to the DB."""
    if relationship_type != "FS":
        raise ValueError("v2.3 relationship inference only supports FS relationships.")
    activities = _filtered_activities(db_path, project_id=project_id, zone=zone, discipline=discipline)
    relationships = db.list_relationships(db_path)
    existing_pairs = {(rel.pred_id, rel.succ_id) for rel in relationships}
    accepted_pairs = set(existing_pairs)
    suggestions: list[dict[str, object]] = []

    grouped: dict[str, list[Any]] = {}
    for activity in activities:
        key = activity.zone or "__site__"
        grouped.setdefault(key, []).append(activity)

    for group_activities in grouped.values():
        ordered = sorted(
            group_activities,
            key=lambda item: (
                item.es_date or date.max,
                item.ef_date or date.max,
                item.code,
            ),
        )
        for index, successor in enumerate(ordered[1:], start=1):
            predecessor = _nearest_predecessor(ordered[:index], successor)
            if predecessor is None:
                continue
            pair = (predecessor.activity_id, successor.activity_id)
            if predecessor.activity_id == successor.activity_id or pair in accepted_pairs:
                continue
            candidate = _suggestion(predecessor, successor, relationship_type, default_lag)
            candidate_relationships = relationships + [
                Relationship(
                    rel_id=str(candidate["rel_id"]),
                    pred_id=predecessor.activity_id,
                    succ_id=successor.activity_id,
                    rel_type=relationship_type,
                    lag_days=default_lag,
                )
            ]
            if relationship_graph_has_cycle({activity.activity_id for activity in activities}, candidate_relationships):
                continue
            suggestions.append(candidate)
            accepted_pairs.add(pair)
            relationships = candidate_relationships

    return suggestions


def apply_relationship_suggestions(
    db_path: str,
    suggestions: list[dict[str, object]],
    *,
    actor: str = "codex-v2.3",
) -> dict[str, object]:
    """Validate and persist relationship suggestions, skipping unsafe rows."""
    activities = db.list_activities(db_path)
    activity_ids = {activity.activity_id for activity in activities}
    relationships = db.list_relationships(db_path)
    existing_pairs = {(rel.pred_id, rel.succ_id) for rel in relationships}
    applied_ids: list[str] = []
    warnings: list[str] = []

    for suggestion in suggestions:
        pred_id = str(suggestion.get("pred_id") or "")
        succ_id = str(suggestion.get("succ_id") or "")
        rel_type = str(suggestion.get("rel_type") or "FS")
        lag_days = _int_value(suggestion.get("lag_days"), default=0)
        pair = (pred_id, succ_id)
        if not pred_id or not succ_id:
            warnings.append(f"관계 후보에 작업 ID가 없습니다: pred={pred_id}, succ={succ_id}")
            continue
        if pred_id == succ_id:
            warnings.append(f"self relationship 후보는 제외했습니다: {pred_id}")
            continue
        if pred_id not in activity_ids or succ_id not in activity_ids:
            warnings.append(f"존재하지 않는 작업 관계 후보는 제외했습니다: {pred_id}->{succ_id}")
            continue
        if pair in existing_pairs:
            warnings.append(f"이미 존재하는 relationship 후보는 제외했습니다: {pred_id}->{succ_id}")
            continue
        rel_id = str(suggestion.get("rel_id") or _relationship_id(pred_id, succ_id, rel_type, lag_days))
        candidate = Relationship(rel_id, pred_id, succ_id, rel_type, lag_days)
        if relationship_graph_has_cycle(activity_ids, relationships + [candidate]):
            warnings.append(f"cycle을 만들 수 있는 relationship 후보는 제외했습니다: {pred_id}->{succ_id}")
            continue
        db.add_relationship(db_path, candidate)
        db.log_change(
            db_path,
            ChangeLogEntry(
                change_id=f"chg-{rel_id}",
                target_table="relationships",
                target_id=rel_id,
                before_value="",
                after_value=json.dumps(
                    {
                        "pred_id": pred_id,
                        "succ_id": succ_id,
                        "rel_type": rel_type,
                        "lag_days": lag_days,
                    },
                    ensure_ascii=False,
                ),
                reason=str(suggestion.get("reason") or "v2.3 relationship inference candidate"),
                user=actor,
            ),
        )
        relationships.append(candidate)
        existing_pairs.add(pair)
        applied_ids.append(rel_id)

    return {
        "ok": True,
        "applied_count": len(applied_ids),
        "skipped_count": len(suggestions) - len(applied_ids),
        "created_relationship_ids": applied_ids,
        "warnings": warnings,
    }


def relationship_graph_has_cycle(activity_ids: set[str], relationships: list[Relationship]) -> bool:
    adjacency: dict[str, set[str]] = {activity_id: set() for activity_id in activity_ids}
    for relationship in relationships:
        if relationship.pred_id in adjacency and relationship.succ_id in adjacency:
            adjacency[relationship.pred_id].add(relationship.succ_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for neighbor in adjacency[node]:
            if visit(neighbor):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(activity_id) for activity_id in activity_ids)


def _filtered_activities(
    path: str | Path,
    *,
    project_id: str | None,
    zone: str | None,
    discipline: str | None,
):
    summary = db.load_project_summary(path)
    project = summary.get("project")
    if project_id and getattr(project, "project_id", None) != project_id:
        return []
    activities = db.list_activities(path)
    if zone:
        activities = [activity for activity in activities if activity.zone == zone]
    if discipline:
        activities = [activity for activity in activities if activity.discipline == discipline]
    return activities


def _nearest_predecessor(candidates, successor):
    dated = [
        activity
        for activity in candidates
        if activity.ef_date is not None
        and successor.es_date is not None
        and activity.ef_date <= successor.es_date
    ]
    if dated:
        return max(dated, key=lambda activity: (activity.ef_date, activity.code))
    return candidates[-1] if candidates else None


def _suggestion(predecessor, successor, rel_type: str, lag_days: int) -> dict[str, object]:
    reason = (
        "v2.3 초기 rule-based 후보: 선행 작업의 종료일이 후속 작업 시작일보다 빠릅니다. "
        "현장 검토 후 적용 필요."
    )
    return {
        "rel_id": _relationship_id(predecessor.activity_id, successor.activity_id, rel_type, lag_days),
        "pred_id": predecessor.activity_id,
        "succ_id": successor.activity_id,
        "pred_code": predecessor.code,
        "succ_code": successor.code,
        "pred_name": predecessor.name,
        "succ_name": successor.name,
        "rel_type": rel_type,
        "lag_days": lag_days,
        "reason": reason,
    }


def _relationship_id(pred_id: str, succ_id: str, rel_type: str, lag_days: int) -> str:
    raw = f"rel-auto-{pred_id}-{succ_id}-{rel_type}-{lag_days}"
    return re.sub(r"[^A-Za-z0-9_-]+", "-", raw)[:180]


def _int_value(value: object, *, default: int) -> int:
    if value is None:
        return default
    if not isinstance(value, str | bytes | bytearray | int | float):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
