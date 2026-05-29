from __future__ import annotations

from datetime import date

from core import db
from core.cpm import run_cpm_for_project
from core.models import Activity, Calendar, Project, Relationship, WBS


def test_sqlite_to_cpm_to_sqlite_persists_calendar_dates(tmp_path):
    db_path = tmp_path / "calendar.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal", "Korean 5-day", "1111100"))
    db.create_project(db_path, Project("project", "Pilot", date(2026, 1, 2), "cal"))
    db.add_wbs(db_path, WBS("wbs", None, "MEP", "MEP", 1))
    db.add_activity(db_path, _activity("a", "A", 1))
    db.add_activity(db_path, _activity("b", "B", 2))
    db.add_relationship(db_path, Relationship("r1", "a", "b", "FS", 0))

    run_cpm_for_project(db_path)
    stored = {activity.activity_id: activity for activity in db.list_activities(db_path)}

    assert stored["a"].es_date == date(2026, 1, 2)
    assert stored["a"].ef_date == date(2026, 1, 2)
    assert stored["b"].es_date == date(2026, 1, 5)
    assert stored["b"].ef_date == date(2026, 1, 6)


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
