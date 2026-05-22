"""Tests for budget variance analysis in core.cost."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core import db
from core.cost import (
    analyze_budget_variance,
    classify_variance_status,
    forecast_scenarios,
)
from core.models import Activity, Calendar, CostItem, DailyRecord, Project, WBS


@pytest.fixture
def variance_db(tmp_path: Path) -> Path:
    """Create a DB with activities, cost items, and some daily records."""
    db_path = tmp_path / "variance_test.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
    db.create_project(db_path, Project("proj-1", "Test Project", date(2028, 1, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "Root"))

    # Activity 1: on budget
    db.create_activity(
        db_path,
        Activity(
            activity_id="act-001", code="A-001", name="골조공사",
            wbs_id="wbs-root", discipline="건축", zone="", duration=180,
            es_date=date(2028, 1, 1), ef_date=date(2028, 6, 30),
        ),
    )
    db.upsert_cost_item(
        db_path,
        CostItem(
            cost_item_id="cost-001", activity_id="act-001",
            contract_amount=1_000_000_000, execution_budget=900_000_000,
            invested_cost=200_000_000,
        ),
    )

    # Activity 2: over budget (high invested cost, low progress)
    db.create_activity(
        db_path,
        Activity(
            activity_id="act-002", code="A-002", name="배관공사",
            wbs_id="wbs-root", discipline="기계설비", zone="", duration=210,
            es_date=date(2028, 3, 1), ef_date=date(2028, 9, 30),
        ),
    )
    db.upsert_cost_item(
        db_path,
        CostItem(
            cost_item_id="cost-002", activity_id="act-002",
            contract_amount=500_000_000, execution_budget=450_000_000,
            invested_cost=300_000_000,  # high invested vs low progress
        ),
    )
    # Add daily records showing 30% progress for act-002
    db.create_daily_record(
        db_path,
        DailyRecord("rec-001", "act-002", date(2028, 3, 15), planned_qty=100, actual_qty=30, workers=5),
    )

    return db_path


# ---------------------------------------------------------------------------
# classify_variance_status tests
# ---------------------------------------------------------------------------


class TestClassifyVarianceStatus:
    def test_under_budget(self):
        assert classify_variance_status(10.0) == "절감"

    def test_on_budget_positive(self):
        assert classify_variance_status(3.0) == "정상"

    def test_on_budget_negative(self):
        assert classify_variance_status(-3.0) == "정상"

    def test_over_budget(self):
        assert classify_variance_status(-10.0) == "초과"

    def test_critical(self):
        assert classify_variance_status(-20.0) == "위험"

    def test_boundary_5(self):
        # Exactly +5% boundary → "정상" (not "절감" which requires >5)
        assert classify_variance_status(5.0) == "정상"

    def test_boundary_minus_5(self):
        # Exactly -5% boundary → "정상" (>= -5)
        assert classify_variance_status(-5.0) == "정상"

    def test_boundary_minus_15(self):
        # Exactly -15% → "초과" (>= -15)
        assert classify_variance_status(-15.0) == "초과"

    def test_zero(self):
        assert classify_variance_status(0.0) == "정상"


# ---------------------------------------------------------------------------
# analyze_budget_variance tests
# ---------------------------------------------------------------------------


class TestAnalyzeBudgetVariance:
    def test_basic(self, variance_db):
        result = analyze_budget_variance(variance_db, as_of_date=date(2028, 4, 1))
        assert result["ok"] is True
        assert result["activity_count"] == 2
        assert len(result["items"]) == 2
        assert len(result["discipline_summary"]) == 2

    def test_overall_summary(self, variance_db):
        result = analyze_budget_variance(variance_db, as_of_date=date(2028, 4, 1))
        overall = result["overall"]
        assert "execution_budget" in overall
        assert "invested_cost" in overall
        assert "forecast_cost" in overall
        assert "variance_pct" in overall
        assert overall["status"] in ("절감", "정상", "초과", "위험")

    def test_discipline_filter(self, variance_db):
        result = analyze_budget_variance(variance_db, discipline="건축", as_of_date=date(2028, 4, 1))
        assert result["ok"] is True
        assert result["activity_count"] == 1
        assert result["items"][0]["discipline"] == "건축"

    def test_item_structure(self, variance_db):
        result = analyze_budget_variance(variance_db, as_of_date=date(2028, 4, 1))
        item = result["items"][0]
        expected_keys = {
            "activity_id", "code", "name", "discipline",
            "execution_budget", "invested_cost", "forecast_cost",
            "progress_pct", "variance_amount", "variance_pct", "status",
        }
        assert expected_keys.issubset(set(item.keys()))

    def test_overbudget_detection(self, variance_db):
        """act-002 has 300M invested with 30% progress → forecast 1B vs budget 450M → over."""
        result = analyze_budget_variance(variance_db, as_of_date=date(2028, 4, 1))
        act002 = next(i for i in result["items"] if i["activity_id"] == "act-002")
        assert act002["status"] in ("초과", "위험")
        assert act002["variance_pct"] < 0

    def test_empty_db(self, tmp_path):
        db_path = tmp_path / "empty.scheduler"
        db.initialize_database(db_path)
        db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
        db.create_project(db_path, Project("proj-1", "Empty", date(2028, 1, 1), "cal-1"))
        result = analyze_budget_variance(db_path)
        assert result["ok"] is True
        assert result["activity_count"] == 0


# ---------------------------------------------------------------------------
# forecast_scenarios tests
# ---------------------------------------------------------------------------


class TestForecastScenarios:
    def test_basic(self, variance_db):
        result = forecast_scenarios(variance_db)
        assert result["ok"] is True
        assert "낙관" in result["scenarios"]
        assert "현실" in result["scenarios"]
        assert "비관" in result["scenarios"]

    def test_scenario_ordering(self, variance_db):
        result = forecast_scenarios(variance_db)
        s = result["scenarios"]
        assert s["낙관"]["forecast"] <= s["현실"]["forecast"] <= s["비관"]["forecast"]

    def test_custom_factors(self, variance_db):
        result = forecast_scenarios(
            variance_db,
            optimistic_factor=0.80,
            pessimistic_factor=1.30,
        )
        s = result["scenarios"]
        # Wider spread with extreme factors
        spread = s["비관"]["forecast"] - s["낙관"]["forecast"]
        assert spread > 0

    def test_discipline_filter(self, variance_db):
        full = forecast_scenarios(variance_db)
        filtered = forecast_scenarios(variance_db, discipline="건축")
        assert filtered["ok"] is True
        assert filtered["scenarios"]["현실"]["forecast"] < full["scenarios"]["현실"]["forecast"]
