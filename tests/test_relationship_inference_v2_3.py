from __future__ import annotations

from datetime import date

from core import db
from core.cpm import run_cpm
from core.models import Activity, Calendar, Project, WBS
from core.relationship_inference import (
    apply_relationship_suggestions,
    suggest_construction_relationships,
)


def test_suggest_construction_relationships_returns_safe_unique_candidates(tmp_path):
    db_path = _relationship_db(tmp_path)

    suggestions = suggest_construction_relationships(str(db_path))

    assert len(suggestions) >= 2
    pairs = {(item["pred_id"], item["succ_id"]) for item in suggestions}
    assert len(pairs) == len(suggestions)
    assert all(item["pred_id"] != item["succ_id"] for item in suggestions)
    assert all(item["rel_type"] == "FS" for item in suggestions)


def test_apply_relationship_suggestions_persists_without_cycles_and_is_idempotent(tmp_path):
    db_path = _relationship_db(tmp_path)
    suggestions = suggest_construction_relationships(str(db_path))

    first = apply_relationship_suggestions(str(db_path), suggestions, actor="test")
    second = apply_relationship_suggestions(str(db_path), suggestions, actor="test")

    relationships = db.list_relationships(db_path)
    result = run_cpm(db.list_activities(db_path), relationships)
    assert first["ok"] is True
    assert first["applied_count"] == len(suggestions)
    assert second["applied_count"] == 0
    assert len(relationships) == len(suggestions)
    assert result.cycles_detected == []


def _relationship_db(tmp_path):
    path = tmp_path / "relationships.scheduler"
    db.initialize_database(path)
    db.create_calendar(path, Calendar("cal", "Calendar", "1111100"))
    db.create_project(path, Project("proj", "Relationship Pilot", date(2026, 1, 1), "cal"))
    db.create_wbs(path, WBS("wbs", None, "ROOT", "ROOT"))
    rows = [
        ("a1", "A001", "Structure", "architecture", date(2026, 1, 1), date(2026, 1, 10)),
        ("a2", "A002", "Duct rough-in", "mechanical", date(2026, 1, 11), date(2026, 1, 20)),
        ("a3", "A003", "Ceiling finish", "architecture", date(2026, 1, 21), date(2026, 1, 30)),
    ]
    for activity_id, code, name, discipline, start, finish in rows:
        db.create_activity(
            path,
            Activity(
                activity_id,
                code,
                name,
                "wbs",
                discipline,
                "1F",
                max((finish - start).days, 1),
                es_date=start,
                ef_date=finish,
            ),
        )
    return path
