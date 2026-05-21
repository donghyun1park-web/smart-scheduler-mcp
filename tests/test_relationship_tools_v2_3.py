from __future__ import annotations

from datetime import date

from core import db
from core.models import Activity, Calendar, Project, WBS
from tools.relationship_tools import generate_activity_relationships, suggest_activity_relationships


def test_relationship_tools_default_to_dry_run(tmp_path):
    db_path = _relationship_db(tmp_path)

    result = generate_activity_relationships(str(db_path))

    assert result["ok"] is True
    assert result["apply"] is False
    assert result["applied_count"] == 0
    assert result["suggestion_count"] > 0
    assert len(db.list_relationships(db_path)) == 0


def test_relationship_tools_apply_only_when_explicit(tmp_path):
    db_path = _relationship_db(tmp_path)

    preview = suggest_activity_relationships(str(db_path))
    applied = generate_activity_relationships(str(db_path), apply=True)

    assert preview["ok"] is True
    assert applied["ok"] is True
    assert applied["apply"] is True
    assert applied["applied_count"] == preview["count"]
    assert len(db.list_relationships(db_path)) == preview["count"]


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
