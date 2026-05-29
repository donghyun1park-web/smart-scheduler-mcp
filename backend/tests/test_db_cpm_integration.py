from __future__ import annotations

from datetime import date

from core import db
from core.cpm import run_cpm_for_project
from core.models import Activity, Calendar, Project, Relationship, WBS


def test_sqlite_to_cpm_to_sqlite_round_trip(tmp_path):
    db_path = tmp_path / "integration.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal", "Korean 5-day", "1111100"))
    db.create_project(db_path, Project("project", "Pilot", date(2026, 1, 5), "cal"))
    db.add_wbs(db_path, WBS("wbs", None, "MEP", "MEP", 1))
    db.add_activity(db_path, _activity("a", "A", 3))
    db.add_activity(db_path, _activity("b", "B", 2))
    db.add_activity(db_path, _activity("c", "C", 4))
    db.add_relationship(db_path, Relationship("r1", "a", "b", "FS", 0))
    db.add_relationship(db_path, Relationship("r2", "b", "c", "FS", 1))

    result = run_cpm_for_project(db_path)
    stored = {activity.activity_id: activity for activity in db.list_activities(db_path)}
    summary = db.load_project_summary(db_path)

    assert result.total_duration_days == 10
    assert stored["a"].es_workday == 0
    assert stored["b"].es_workday == 3
    assert stored["c"].es_workday == 6
    assert stored["c"].ef_workday == 10
    assert stored["c"].is_critical
    assert summary["activity_count"] == 3
    assert summary["relationship_count"] == 2


def _activity(activity_id: str, code: str, duration: int) -> Activity:
    return Activity(
        activity_id=activity_id,
        code=code,
        name=code,
        wbs_id="wbs",
        discipline="공조",
        zone="1F",
        duration=duration,
    )
