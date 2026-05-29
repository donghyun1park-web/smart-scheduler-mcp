from __future__ import annotations

from core.relationship_inference import (
    apply_relationship_suggestions,
    suggest_construction_relationships,
)


def suggest_activity_relationships(
    db_path: str,
    *,
    project_id: str | None = None,
    zone: str | None = None,
    discipline: str | None = None,
    limit: int = 200,
) -> dict[str, object]:
    """Return relationship candidates without mutating the DB."""
    suggestions = suggest_construction_relationships(
        db_path,
        project_id=project_id,
        zone=zone,
        discipline=discipline,
    )
    limited = suggestions[: max(limit, 0)]
    return {
        "ok": True,
        "dry_run": True,
        "db_path": db_path,
        "count": len(limited),
        "suggestions": limited,
        "warnings": [],
    }


def generate_activity_relationships(
    db_path: str,
    *,
    project_id: str | None = None,
    apply: bool = False,
    limit: int = 200,
    actor: str = "codex-v2.3",
) -> dict[str, object]:
    """Generate relationship candidates and persist only when apply=True."""
    suggestions = suggest_construction_relationships(db_path, project_id=project_id)
    limited = suggestions[: max(limit, 0)]
    if not apply:
        return {
            "ok": True,
            "apply": False,
            "dry_run": True,
            "db_path": db_path,
            "suggestion_count": len(limited),
            "applied_count": 0,
            "skipped_count": 0,
            "suggestions": limited,
            "warnings": [],
        }
    applied = apply_relationship_suggestions(db_path, limited, actor=actor)
    return {
        "ok": bool(applied["ok"]),
        "apply": True,
        "dry_run": False,
        "db_path": db_path,
        "suggestion_count": len(limited),
        "applied_count": applied["applied_count"],
        "skipped_count": applied["skipped_count"],
        "created_relationship_ids": applied["created_relationship_ids"],
        "warnings": applied["warnings"],
    }
