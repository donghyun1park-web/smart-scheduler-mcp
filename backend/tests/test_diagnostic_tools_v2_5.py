from __future__ import annotations

from datetime import date
from pathlib import Path

from core import db
from core.models import Activity, Calendar, CostItem, DailyRecord, Project, Relationship, WBS
from tools.diagnostic_tools import (
    check_data_health,
    explain_evm_from_db,
    get_workflow_status,
    suggest_next_actions,
)


def test_diagnostic_tools_return_json_ready_dicts(tmp_path):
    db_path = _workflow_db(tmp_path, with_daily=True)

    health = check_data_health(str(db_path), as_of="2026-01-10")
    actions = suggest_next_actions(str(db_path), profile="developer", as_of="2026-01-10")
    evm = explain_evm_from_db(str(db_path), as_of="2026-01-10")
    workflow = get_workflow_status(str(db_path), as_of="2026-01-10")

    assert health["ok"] is True
    assert "score" in health
    assert actions["ok"] is True
    assert actions["actions"]
    assert evm["ok"] is True
    assert evm["explanation"]["status"]
    assert workflow["ok"] is True
    assert workflow["daily_close"]["steps"]


def _workflow_db(tmp_path: Path, *, with_daily: bool):
    db_path = tmp_path / "diagnostic-tools.scheduler"
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
