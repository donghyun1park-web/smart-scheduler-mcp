from __future__ import annotations

from datetime import date
from pathlib import Path

from core import db
from core.models import Activity, Calendar, CostItem, DailyRecord, Project, Relationship, WBS
from core.workflows import get_daily_close_status, get_weekly_report_precheck_status


def test_daily_close_status_fails_without_activities(tmp_path: Path):
    db_path = tmp_path / "workflow.scheduler"
    db.initialize_database(db_path)

    status = get_daily_close_status(db_path, as_of=date(2026, 1, 10))

    assert status.ready is False
    assert any(step.state == "failed" for step in status.steps if step.required)


def test_daily_close_status_passes_with_today_record_and_core_data(tmp_path: Path):
    db_path = _workflow_db(tmp_path, with_daily=True)

    status = get_daily_close_status(db_path, as_of=date(2026, 1, 10))

    assert status.ready is True
    assert status.to_dict()["steps"]


def test_weekly_report_precheck_allows_warning_only_state(tmp_path: Path):
    db_path = _workflow_db(tmp_path, with_daily=False)

    status = get_weekly_report_precheck_status(db_path, as_of=date(2026, 1, 10))

    assert status.ready is True
    assert any(step.state == "warning" for step in status.steps)


def _workflow_db(tmp_path: Path, *, with_daily: bool):
    db_path = tmp_path / "workflow.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal", "Calendar", "1111100"))
    db.create_project(db_path, Project("proj", "Workflow Site", date(2026, 1, 1), "cal"))
    db.create_wbs(db_path, WBS("wbs", None, "ROOT", "ROOT"))
    db.create_activity(db_path, Activity("act-1", "A-001", "Foundation", "wbs", "architecture", "1F", 10))
    db.create_activity(db_path, Activity("act-2", "A-002", "Rough-in", "wbs", "mechanical", "1F", 5))
    db.upsert_cost_item(db_path, CostItem("cost-1", "act-1", 1000, 900, 200, 100))
    db.upsert_cost_item(db_path, CostItem("cost-2", "act-2", 500, 450, 100, 50))
    db.add_relationship(db_path, Relationship("rel-1", "act-1", "act-2", "FS", 0))
    if with_daily:
        db.create_daily_record(db_path, DailyRecord("dr-1", "act-1", date(2026, 1, 10), 10, 8))
    return db_path
