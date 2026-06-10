"""Tests for tools.material_tools (materials + inspections + logistics)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core import db
from core.models import Activity, Calendar, CostItem, Project, WBS
from tools.material_tools import (
    add_inspection,
    add_material,
    get_activity_logistics,
    list_inspections_tool,
    list_materials_tool,
    update_inspection,
    update_material,
)


@pytest.fixture
def mat_db(tmp_path: Path) -> Path:
    """Create a minimal .scheduler DB with one activity."""
    db_path = tmp_path / "material_test.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
    db.create_project(db_path, Project("proj-1", "Test", date(2028, 1, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "Root"))
    db.create_activity(
        db_path,
        Activity("act-001", "A-001", "배관공사", "wbs-root", "기계설비", "", 180,
                 es_date=date(2028, 3, 1), ef_date=date(2028, 8, 31)),
    )
    db.upsert_cost_item(
        db_path,
        CostItem("cost-001", "act-001", contract_amount=500_000_000, execution_budget=450_000_000),
    )
    return db_path


# ---------------------------------------------------------------------------
# Material tests
# ---------------------------------------------------------------------------


def test_add_material(mat_db: Path):
    result = add_material(str(mat_db), "act-001", "밸브 50A", order_date="2028-03-15")
    assert result["ok"] is True
    assert result["material_name"] == "밸브 50A"
    assert result["status"] == "planned"


def test_list_materials(mat_db: Path):
    add_material(str(mat_db), "act-001", "밸브 50A")
    add_material(str(mat_db), "act-001", "배관 100A")
    result = list_materials_tool(str(mat_db), activity_id="act-001")
    assert result["ok"] is True
    assert result["count"] == 2


def test_list_materials_filter_status(mat_db: Path):
    add_material(str(mat_db), "act-001", "밸브 50A", status="planned")
    add_material(str(mat_db), "act-001", "배관 100A", status="ordered")
    result = list_materials_tool(str(mat_db), status="ordered")
    assert result["count"] == 1
    assert result["materials"][0]["material_name"] == "배관 100A"


def test_update_material(mat_db: Path):
    added = add_material(str(mat_db), "act-001", "밸브 50A")
    result = update_material(
        str(mat_db), added["material_id"],
        status="delivered", actual_date="2028-04-10",
    )
    assert result["ok"] is True
    assert result["status"] == "delivered"
    assert result["actual_date"] == "2028-04-10"


# ---------------------------------------------------------------------------
# Inspection tests
# ---------------------------------------------------------------------------


def test_add_inspection(mat_db: Path):
    result = add_inspection(str(mat_db), "act-001", "배관수압시험", planned_date="2028-06-15")
    assert result["ok"] is True
    assert result["inspection_type"] == "배관수압시험"


def test_list_inspections(mat_db: Path):
    add_inspection(str(mat_db), "act-001", "배관수압시험")
    add_inspection(str(mat_db), "act-001", "절연저항측정")
    result = list_inspections_tool(str(mat_db), activity_id="act-001")
    assert result["ok"] is True
    assert result["count"] == 2


def test_update_inspection(mat_db: Path):
    added = add_inspection(str(mat_db), "act-001", "배관수압시험", planned_date="2028-06-15")
    result = update_inspection(
        str(mat_db), added["inspection_id"],
        status="passed", actual_date="2028-06-14", approver="홍길동",
    )
    assert result["ok"] is True
    assert result["status"] == "passed"
    assert result["approver"] == "홍길동"


# ---------------------------------------------------------------------------
# Logistics view tests
# ---------------------------------------------------------------------------


def test_get_activity_logistics_empty(mat_db: Path):
    result = get_activity_logistics(str(mat_db), "act-001")
    assert result["ok"] is True
    assert result["activity"]["name"] == "배관공사"
    assert result["materials"]["total"] == 0
    assert result["inspections"]["total"] == 0


def test_get_activity_logistics_with_data(mat_db: Path):
    add_material(str(mat_db), "act-001", "밸브 50A", expected_date="2028-04-01")
    add_material(str(mat_db), "act-001", "배관 100A", expected_date="2028-04-15", status="ordered")
    add_inspection(str(mat_db), "act-001", "수압시험", planned_date="2028-06-15")

    result = get_activity_logistics(str(mat_db), "act-001")
    assert result["ok"] is True
    assert result["materials"]["total"] == 2
    assert result["inspections"]["total"] == 1
    assert result["cost"]["contract_amount"] == 500_000_000


def test_get_activity_logistics_not_found(mat_db: Path):
    result = get_activity_logistics(str(mat_db), "act-999")
    assert result["ok"] is False
    assert "not found" in result["error"]
