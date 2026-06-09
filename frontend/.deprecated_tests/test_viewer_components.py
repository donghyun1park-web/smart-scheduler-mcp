from __future__ import annotations

from datetime import date

from core import db
from core.models import Calendar, Project
from tools.analysis_tools import calculate_cpm, get_critical_path
from viewer.components.activity_editor import add_activity_from_form, update_activity_from_form
from viewer.components.calendar_editor import update_calendar_from_form
from viewer.components.relationship_editor import add_relationship_from_form, delete_relationship
from viewer.components.wbs_editor import add_wbs_from_form, update_wbs_from_form


def test_viewer_helpers_persist_wbs_activity_relationship_and_calendar(tmp_path):
    db_path = _project_db(tmp_path)
    add_wbs_from_form(db_path, code="MEP", name="MEP Works", parent_id=None, sort_order=1)
    wbs = db.list_wbs(db_path)[0]
    update_wbs_from_form(db_path, wbs.wbs_id, code="MEP-01", name="MEP Updated", parent_id=None, sort_order=2)

    activity = add_activity_from_form(
        db_path,
        code="A100",
        name="Duct",
        wbs_id=wbs.wbs_id,
        discipline="공조",
        zone="1F",
        duration=3,
        cost=100.0,
    )
    update_activity_from_form(
        db_path,
        activity.activity_id,
        code="A101",
        name="Duct Updated",
        wbs_id=wbs.wbs_id,
        discipline="공조",
        zone="2F",
        duration=4,
        cost=200.0,
    )
    relationship = add_relationship_from_form(db_path, activity.activity_id, activity.activity_id, "FS", 0)
    delete_relationship(db_path, relationship.rel_id)
    update_calendar_from_form(db_path, "cal", "Korean 6-day", "1111110", ["2026-01-06"])

    stored_wbs = db.list_wbs(db_path)[0]
    stored_activity = db.list_activities(db_path)[0]
    stored_calendar = db.get_calendar(db_path, "cal")
    assert stored_wbs.code == "MEP-01"
    assert stored_activity.code == "A101"
    assert stored_activity.duration == 4
    assert stored_activity.cost == 200.0
    assert db.list_relationships(db_path) == []
    assert stored_calendar is not None
    assert stored_calendar.weekmask == "1111110"
    assert stored_calendar.holidays == ("2026-01-06",)


def test_streamlit_helpers_and_mcp_tools_share_same_sqlite(tmp_path):
    db_path = _project_db(tmp_path)
    wbs = add_wbs_from_form(db_path, code="MEP", name="MEP", parent_id=None, sort_order=1)
    first = add_activity_from_form(db_path, "A100", "Sleeve", wbs.wbs_id, "공조", "1F", 1, 10.0)
    second = add_activity_from_form(db_path, "A200", "Duct", wbs.wbs_id, "공조", "1F", 2, 20.0)
    add_relationship_from_form(db_path, first.activity_id, second.activity_id, "FS", 0)

    cpm = calculate_cpm(db_path)
    critical = get_critical_path(db_path)

    assert cpm["ok"] is True
    assert cpm["total_duration_days"] == 3
    assert [item["code"] for item in critical["critical_path"]] == ["A100", "A200"]


def _project_db(tmp_path):
    db_path = tmp_path / "viewer.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal", "Korean 5-day", "1111100"))
    db.create_project(db_path, Project("project", "Viewer", date(2026, 1, 5), "cal"))
    return db_path
