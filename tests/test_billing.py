"""Tests for core.billing and tools.billing_tools."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core import db
from core.billing import (
    calculate_monthly_billing,
    get_billing_s_curve,
    get_billing_summary,
    update_billing_amounts,
)
from core.models import Activity, Calendar, CostItem, Project, WBS


@pytest.fixture
def billing_db(tmp_path: Path) -> Path:
    """Create a minimal .scheduler DB with activities and cost items."""
    db_path = tmp_path / "billing_test.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
    db.create_project(db_path, Project("proj-1", "Test Project", date(2028, 1, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "Root"))

    # Activity 1: Jan-Jun 2028, 건축
    db.create_activity(
        db_path,
        Activity(
            activity_id="act-001",
            code="A-001",
            name="골조공사",
            wbs_id="wbs-root",
            discipline="건축",
            zone="",
            duration=180,
            es_date=date(2028, 1, 1),
            ef_date=date(2028, 6, 30),
        ),
    )
    db.upsert_cost_item(
        db_path,
        CostItem(
            cost_item_id="cost-001",
            activity_id="act-001",
            contract_amount=1_000_000_000,
            execution_budget=900_000_000,
        ),
    )

    # Activity 2: Mar-Sep 2028, 기계설비
    db.create_activity(
        db_path,
        Activity(
            activity_id="act-002",
            code="A-002",
            name="배관공사",
            wbs_id="wbs-root",
            discipline="기계설비",
            zone="",
            duration=210,
            es_date=date(2028, 3, 1),
            ef_date=date(2028, 9, 30),
        ),
    )
    db.upsert_cost_item(
        db_path,
        CostItem(
            cost_item_id="cost-002",
            activity_id="act-002",
            contract_amount=500_000_000,
            execution_budget=450_000_000,
        ),
    )

    return db_path


def test_calculate_monthly_billing(billing_db: Path):
    result = calculate_monthly_billing(billing_db, "2028-03")
    assert result["ok"] is True
    assert result["year_month"] == "2028-03"
    assert result["activity_count"] >= 1
    assert result["total_contract_billing"] > 0


def test_calculate_monthly_billing_with_discipline_filter(billing_db: Path):
    result = calculate_monthly_billing(billing_db, "2028-04", discipline="기계설비")
    assert result["ok"] is True
    for row in result["rows"]:
        assert row["discipline"] == "기계설비"


def test_calculate_monthly_billing_before_activity_start(billing_db: Path):
    result = calculate_monthly_billing(billing_db, "2027-12")
    assert result["ok"] is True
    assert result["total_contract_billing"] == 0


def test_update_billing_dry_run(billing_db: Path):
    result = update_billing_amounts(billing_db, "2028-04", dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["updated_count"] == 0
    # Billing should not change
    costs = db.list_cost_items(billing_db)
    for c in costs:
        assert c.billing_amount == 0


def test_update_billing_apply(billing_db: Path):
    result = update_billing_amounts(billing_db, "2028-04", dry_run=False)
    assert result["ok"] is True
    assert result["dry_run"] is False
    assert result["updated_count"] > 0
    # Billing should be non-zero now
    costs = db.list_cost_items(billing_db)
    billed = [c for c in costs if c.billing_amount > 0]
    assert len(billed) > 0


def test_get_billing_summary(billing_db: Path):
    result = get_billing_summary(billing_db)
    assert result["ok"] is True
    assert len(result["rows"]) == 2  # 건축, 기계설비
    assert result["total_contract"] == 1_500_000_000
    assert result["total_execution"] == 1_350_000_000


def test_get_billing_s_curve(billing_db: Path):
    result = get_billing_s_curve(
        billing_db,
        start_date="2028-01-01",
        end_date="2028-06-30",
        interval="monthly",
    )
    assert result["ok"] is True
    assert len(result["series"]) == 6  # Jan-Jun
    # Cumulative should be monotonically increasing
    for i in range(1, len(result["series"])):
        assert result["series"][i]["cumulative_planned"] >= result["series"][i - 1]["cumulative_planned"]


def test_get_billing_s_curve_quarterly(billing_db: Path):
    result = get_billing_s_curve(
        billing_db,
        start_date="2028-01-01",
        end_date="2028-09-30",
        interval="quarterly",
    )
    assert result["ok"] is True
    assert result["interval"] == "quarterly"
    assert len(result["series"]) == 3  # Q1, Q2, Q3


def test_discipline_totals_in_monthly_billing(billing_db: Path):
    result = calculate_monthly_billing(billing_db, "2028-04")
    disc_totals = result["discipline_totals"]
    total_from_discs = sum(d["contract_billing"] for d in disc_totals)
    assert total_from_discs == result["total_contract_billing"]
