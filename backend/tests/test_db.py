from __future__ import annotations

from datetime import date

from core import db
from core.models import Activity, Calendar, Project, Relationship, WBS


def test_project_wbs_activity_relationship_calendar_crud_round_trip(tmp_path):
    db_path = tmp_path / "sample.scheduler"
    db.initialize_database(db_path)

    calendar = db.create_calendar(
        db_path,
        Calendar(
            calendar_id="cal-1",
            name="Korean 5-day",
            weekmask="1111100",
            holidays=("2026-01-01",),
        ),
    )
    project = db.create_project(
        db_path,
        Project(
            project_id="project-1",
            name="MEP Pilot",
            start_date=date(2026, 1, 5),
            calendar_id=calendar.calendar_id,
            description="Core skeleton test",
        ),
    )
    parent = db.create_wbs(
        db_path,
        WBS(
            wbs_id="wbs-1",
            parent_id=None,
            code="MEP",
            name="MEP Works",
            sort_order=1,
        ),
    )
    child = db.create_wbs(
        db_path,
        WBS(
            wbs_id="wbs-2",
            parent_id=parent.wbs_id,
            code="MEP-HVAC",
            name="HVAC",
            sort_order=2,
        ),
    )
    first = db.create_activity(
        db_path,
        Activity(
            activity_id="act-1",
            code="A1000",
            name="Duct install",
            wbs_id=child.wbs_id,
            discipline="공조",
            zone="1F",
            duration=3,
            cost=1000.0,
        ),
    )
    second = db.create_activity(
        db_path,
        Activity(
            activity_id="act-2",
            code="A1010",
            name="Diffuser install",
            wbs_id=child.wbs_id,
            discipline="공조",
            zone="1F",
            duration=2,
            cost=500.0,
        ),
    )
    relationship = db.create_relationship(
        db_path,
        Relationship(
            rel_id="rel-1",
            pred_id=first.activity_id,
            succ_id=second.activity_id,
            rel_type="FS",
            lag_days=1,
        ),
    )

    assert db.get_project(db_path, project.project_id) == project
    assert db.get_calendar(db_path, calendar.calendar_id) == calendar
    assert db.list_wbs(db_path) == [parent, child]
    assert db.list_activities(db_path) == [first, second]
    assert db.list_relationships(db_path) == [relationship]


def test_initialize_database_creates_required_indexes(tmp_path):
    db_path = tmp_path / "indexed.scheduler"
    db.initialize_database(db_path)

    index_names = db.list_indexes(db_path)

    assert "idx_activities_wbs_id" in index_names
    assert "idx_activities_discipline" in index_names
    assert "idx_relationships_pred_id" in index_names
    assert "idx_relationships_succ_id" in index_names
