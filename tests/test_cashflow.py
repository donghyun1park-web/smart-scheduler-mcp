"""Tests for core.cashflow and tools.cashflow_tools."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core import db
from core.cashflow import (
    _distribute_amount,
    calculate_funding_requirements,
    forecast_cash_flow,
    get_retention_schedule,
)
from core.models import Activity, Calendar, CostItem, Project, WBS


@pytest.fixture
def cashflow_db(tmp_path: Path) -> Path:
    """Create a minimal .scheduler DB with activities and cost items."""
    db_path = tmp_path / "cashflow_test.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
    db.create_project(db_path, Project("proj-1", "Test Project", date(2028, 1, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "Root"))

    # Activity 1: Jan-Jun 2028, 건축
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
        ),
    )

    # Activity 2: Mar-Sep 2028, 기계설비
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
        ),
    )

    return db_path


# ---------------------------------------------------------------------------
# Distribution method tests
# ---------------------------------------------------------------------------


class TestDistributionMethods:
    def test_linear_distribution(self):
        result = _distribute_amount(1000, 4, "linear")
        assert len(result) == 4
        assert sum(result) == pytest.approx(1000)
        assert all(v == pytest.approx(250) for v in result)

    def test_front_loaded_distribution(self):
        result = _distribute_amount(1000, 4, "front_loaded")
        assert len(result) == 4
        assert sum(result) == pytest.approx(1000)
        # First period should be larger than last
        assert result[0] > result[-1]

    def test_back_loaded_distribution(self):
        result = _distribute_amount(1000, 4, "back_loaded")
        assert len(result) == 4
        assert sum(result) == pytest.approx(1000)
        # Last period should be larger than first
        assert result[-1] > result[0]

    def test_s_curve_distribution(self):
        result = _distribute_amount(1000, 10, "s_curve")
        assert len(result) == 10
        assert sum(result) == pytest.approx(1000)
        # Middle periods should be larger than edges
        assert result[4] > result[0]
        assert result[5] > result[-1]

    def test_single_period(self):
        result = _distribute_amount(1000, 1, "linear")
        assert result == [1000]

    def test_zero_periods(self):
        result = _distribute_amount(1000, 0, "linear")
        assert result == [1000]


# ---------------------------------------------------------------------------
# Cash flow forecast tests
# ---------------------------------------------------------------------------


class TestForecastCashFlow:
    def test_basic_forecast(self, cashflow_db):
        result = forecast_cash_flow(cashflow_db)
        assert result["ok"] is True
        assert len(result["periods"]) > 0
        assert result["summary"]["total_outflow"] > 0
        assert result["summary"]["total_inflow"] > 0

    def test_monthly_periods(self, cashflow_db):
        result = forecast_cash_flow(cashflow_db, interval="monthly")
        assert result["ok"] is True
        periods = result["periods"]
        # Should have months from Jan to Sep 2028
        assert len(periods) >= 9

    def test_quarterly_periods(self, cashflow_db):
        result = forecast_cash_flow(cashflow_db, interval="quarterly")
        assert result["ok"] is True
        periods = result["periods"]
        assert len(periods) >= 3

    def test_discipline_filter(self, cashflow_db):
        result = forecast_cash_flow(cashflow_db, discipline="건축")
        assert result["ok"] is True
        # Should only include 건축 activity (1B contract)
        total_inflow = result["summary"]["total_inflow"]
        # Inflow should be less than total of both activities
        full = forecast_cash_flow(cashflow_db)
        assert total_inflow < full["summary"]["total_inflow"]

    def test_payment_terms_delay(self, cashflow_db):
        """NET_60 should delay inflows relative to NET_30."""
        r30 = forecast_cash_flow(cashflow_db, payment_terms="NET_30")
        r60 = forecast_cash_flow(cashflow_db, payment_terms="NET_60")
        # With longer payment terms, early period inflows should be smaller
        if r30["periods"] and r60["periods"]:
            assert r60["periods"][0]["inflow"] <= r30["periods"][0]["inflow"]

    def test_retention_effect(self, cashflow_db):
        """Higher retention should reduce net inflows."""
        r0 = forecast_cash_flow(cashflow_db, retention_pct=0.0)
        r20 = forecast_cash_flow(cashflow_db, retention_pct=20.0)
        assert r0["summary"]["total_inflow"] > r20["summary"]["total_inflow"]

    def test_invalid_distribution(self, cashflow_db):
        result = forecast_cash_flow(cashflow_db, distribution="unknown")
        assert result["ok"] is False
        assert "지원하지 않는 분배 방식" in result["error"]

    def test_invalid_payment_terms(self, cashflow_db):
        result = forecast_cash_flow(cashflow_db, payment_terms="NET_999")
        assert result["ok"] is False
        assert "지원하지 않는 지불조건" in result["error"]

    def test_empty_db(self, tmp_path):
        db_path = tmp_path / "empty.scheduler"
        db.initialize_database(db_path)
        db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
        db.create_project(db_path, Project("proj-1", "Empty", date(2028, 1, 1), "cal-1"))
        result = forecast_cash_flow(db_path)
        assert result["ok"] is True
        assert len(result["periods"]) == 0

    def test_period_structure(self, cashflow_db):
        result = forecast_cash_flow(cashflow_db)
        period = result["periods"][0]
        assert "period" in period
        assert "inflow" in period
        assert "outflow" in period
        assert "net" in period
        assert "cumulative_net" in period

    def test_summary_status(self, cashflow_db):
        result = forecast_cash_flow(cashflow_db)
        summary = result["summary"]
        assert summary["status"] in ("자금 여유", "자금 주의", "자금 부족")
        assert summary["status_level"] in ("green", "yellow", "red")

    def test_date_range_override(self, cashflow_db):
        result = forecast_cash_flow(
            cashflow_db,
            start_date="2028-03-01",
            end_date="2028-06-30",
        )
        assert result["ok"] is True
        # Should have ~4 monthly periods
        assert 3 <= len(result["periods"]) <= 5


# ---------------------------------------------------------------------------
# Funding requirements tests
# ---------------------------------------------------------------------------


class TestFundingRequirements:
    def test_basic(self, cashflow_db):
        result = calculate_funding_requirements(cashflow_db)
        assert result["ok"] is True
        assert "peak_funding_required" in result
        assert "monthly_needs" in result
        assert result["buffer_pct"] == 10.0

    def test_buffer_increases_requirement(self, cashflow_db):
        r0 = calculate_funding_requirements(cashflow_db, buffer_pct=0.0)
        r20 = calculate_funding_requirements(cashflow_db, buffer_pct=20.0)
        assert r20["peak_funding_required"] >= r0["peak_funding_required"]


# ---------------------------------------------------------------------------
# Retention schedule tests
# ---------------------------------------------------------------------------


class TestRetentionSchedule:
    def test_basic(self, cashflow_db):
        result = get_retention_schedule(cashflow_db)
        assert result["ok"] is True
        assert result["total_retention"] > 0
        assert result["retention_release_date"] is not None
        assert len(result["rows"]) == 2  # 건축, 기계설비

    def test_discipline_filter(self, cashflow_db):
        result = get_retention_schedule(cashflow_db, discipline="건축")
        assert result["ok"] is True
        assert len(result["rows"]) == 1
        assert result["rows"][0]["discipline"] == "건축"

    def test_retention_amount(self, cashflow_db):
        result = get_retention_schedule(cashflow_db, retention_pct=10.0)
        # Total contract = 1B + 500M = 1.5B, retention = 150M
        assert result["total_retention"] == 150_000_000

    def test_release_days(self, cashflow_db):
        r60 = get_retention_schedule(cashflow_db, release_days=60)
        r90 = get_retention_schedule(cashflow_db, release_days=90)
        # 90-day release should be later
        assert r90["retention_release_date"] > r60["retention_release_date"]
