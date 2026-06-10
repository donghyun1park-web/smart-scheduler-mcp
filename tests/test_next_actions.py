from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from core import db
from core.models import Activity, Calendar, CostItem, Project, Relationship, WBS
from core.next_actions import suggest_next_actions


def test_empty_db_recommends_schedule_import_first(tmp_path: Path):
    db_path = tmp_path / "empty.scheduler"
    db.initialize_database(db_path)

    actions = suggest_next_actions(db_path, profile="field_admin")

    assert actions[0].tool_name == "import_schedule_excel"
    assert actions[0].priority == "high"
    json.dumps([action.to_dict() for action in actions], ensure_ascii=False)


def test_activity_without_cost_recommends_budget_import(tmp_path: Path):
    db_path = _action_db(tmp_path)

    actions = suggest_next_actions(db_path, profile="field_admin")
    tool_names = [action.tool_name for action in actions]

    assert "import_budget_excel" in tool_names
    assert "suggest_activity_relationships" in tool_names


def test_hq_and_developer_profiles_prioritize_different_actions(tmp_path: Path):
    db_path = _action_db(tmp_path, with_cost=True, with_relationship=True)

    hq = suggest_next_actions(db_path, profile="hq", limit=3)
    developer = suggest_next_actions(db_path, profile="developer", limit=3)

    assert len(hq) <= 3
    assert any(action.tool_name == "analyze_evm_from_db" for action in hq)
    assert any(action.tool_name == "check_data_health" for action in developer)
    assert all(action.profile in {"hq", "developer"} for action in (*hq, *developer))


def _action_db(tmp_path: Path, *, with_cost: bool = False, with_relationship: bool = False):
    db_path = tmp_path / "actions.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal", "Calendar", "1111100"))
    db.create_project(db_path, Project("proj", "Action Site", date(2026, 1, 1), "cal"))
    db.create_wbs(db_path, WBS("wbs", None, "ROOT", "ROOT"))
    db.create_activity(
        db_path,
        Activity("act-1", "A-001", "Foundation", "wbs", "architecture", "1F", 10),
    )
    db.create_activity(
        db_path,
        Activity("act-2", "A-002", "Rough-in", "wbs", "mechanical", "1F", 8),
    )
    if with_cost:
        db.upsert_cost_item(db_path, CostItem("cost-1", "act-1", 1000, 900, 300, 100))
        db.upsert_cost_item(db_path, CostItem("cost-2", "act-2", 500, 450, 100, 50))
    if with_relationship:
        db.add_relationship(db_path, Relationship("rel-1", "act-1", "act-2", "FS", 0))
    return db_path
