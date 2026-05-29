from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from core import db
from core.models import Activity, Calendar, CostItem, DailyRecord, Project, Relationship, WBS
from viewer.components.operations_home import build_operations_home_state


def test_build_operations_home_state_returns_profile_specific_payload(tmp_path: Path):
    db_path = _workflow_db(tmp_path, with_daily=True)

    state = build_operations_home_state(db_path, profile="site_manager", as_of=date(2026, 1, 10))

    assert state["profile"] == "site_manager"
    assert "health" in state
    assert "next_actions" in state
    assert "evm_explanation" in state
    assert "workflows" in state
    assert state["workflows"]["daily_close"]["ready"] is True
    json.dumps(state, ensure_ascii=False)


def test_build_operations_home_state_hq_uses_hq_actions(tmp_path: Path):
    db_path = _workflow_db(tmp_path, with_daily=True)

    state = build_operations_home_state(db_path, profile="hq", as_of=date(2026, 1, 10))

    assert state["profile_label_ko"]
    assert any(action["profile"] == "hq" for action in state["next_actions"])


def _workflow_db(tmp_path: Path, *, with_daily: bool):
    db_path = tmp_path / "operations-home.scheduler"
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
