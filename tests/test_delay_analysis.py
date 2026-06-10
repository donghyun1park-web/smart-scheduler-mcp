"""Tests for core.delay_analysis and tools.delay_tools."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core import db
from core.delay_analysis import (
    calculate_time_extension_entitlement,
    generate_delay_analysis,
    list_delay_events_from_db,
    record_delay_event_to_db,
)
from core.models import Activity, Calendar, Project, WBS


@pytest.fixture
def delay_db(tmp_path: Path) -> Path:
    """Create a DB with activities for delay testing."""
    db_path = tmp_path / "delay_test.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
    db.create_project(db_path, Project("proj-1", "Test Project", date(2028, 1, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "Root"))

    db.create_activity(
        db_path,
        Activity(
            activity_id="act-001", code="A-001", name="골조공사",
            wbs_id="wbs-root", discipline="건축", zone="", duration=180,
            es_date=date(2028, 1, 1), ef_date=date(2028, 6, 30),
        ),
    )
    db.create_activity(
        db_path,
        Activity(
            activity_id="act-002", code="A-002", name="배관공사",
            wbs_id="wbs-root", discipline="기계설비", zone="", duration=210,
            es_date=date(2028, 3, 1), ef_date=date(2028, 9, 30),
        ),
    )
    return db_path


# ---------------------------------------------------------------------------
# Record delay event
# ---------------------------------------------------------------------------


class TestRecordDelayEvent:
    def test_dry_run(self, delay_db):
        result = record_delay_event_to_db(
            delay_db, "act-001", "excusable_compensable", "owner_change",
            delay_days=15, description="발주처 설계변경",
            dry_run=True,
        )
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["delay_days"] == 15
        # Should NOT be in DB
        events = db.list_delay_events(delay_db)
        assert len(events) == 0

    def test_persist(self, delay_db):
        result = record_delay_event_to_db(
            delay_db, "act-001", "excusable_compensable", "owner_change",
            delay_days=15, cost_impact=50_000_000,
            dry_run=False,
        )
        assert result["ok"] is True
        assert result["dry_run"] is False
        events = db.list_delay_events(delay_db)
        assert len(events) == 1
        assert events[0].delay_days == 15

    def test_auto_calc_days(self, delay_db):
        result = record_delay_event_to_db(
            delay_db, "act-001", "non_excusable", "contractor_issue",
            start_date=date(2028, 3, 1), end_date=date(2028, 3, 11),
            dry_run=True,
        )
        # cause_code "contractor_issue" is invalid → should fail
        assert result["ok"] is False

    def test_auto_calc_days_valid(self, delay_db):
        result = record_delay_event_to_db(
            delay_db, "act-001", "non_excusable", "subcontractor",
            start_date=date(2028, 3, 1), end_date=date(2028, 3, 11),
            dry_run=True,
        )
        assert result["ok"] is True
        assert result["delay_days"] == 10

    def test_invalid_delay_type(self, delay_db):
        result = record_delay_event_to_db(
            delay_db, "act-001", "invalid_type", "weather",
            dry_run=True,
        )
        assert result["ok"] is False
        assert "유효하지 않은 지연유형" in result["error"]

    def test_invalid_cause(self, delay_db):
        result = record_delay_event_to_db(
            delay_db, "act-001", "non_excusable", "invalid_cause",
            dry_run=True,
        )
        assert result["ok"] is False
        assert "유효하지 않은 원인코드" in result["error"]

    def test_invalid_activity(self, delay_db):
        result = record_delay_event_to_db(
            delay_db, "nonexistent", "non_excusable", "weather",
            dry_run=True,
        )
        assert result["ok"] is False
        assert "활동을 찾을 수 없습니다" in result["error"]

    def test_korean_labels(self, delay_db):
        result = record_delay_event_to_db(
            delay_db, "act-001", "excusable_compensable", "owner_change",
            delay_days=5, dry_run=True,
        )
        assert result["delay_type_kr"] == "면책보상가능"
        assert result["cause_kr"] == "발주처 변경"


# ---------------------------------------------------------------------------
# List delay events
# ---------------------------------------------------------------------------


class TestListDelayEvents:
    def test_empty(self, delay_db):
        result = list_delay_events_from_db(delay_db)
        assert result["ok"] is True
        assert result["count"] == 0

    def test_with_events(self, delay_db):
        # Add two events
        record_delay_event_to_db(
            delay_db, "act-001", "excusable_compensable", "owner_change",
            delay_days=10, dry_run=False,
        )
        record_delay_event_to_db(
            delay_db, "act-002", "non_excusable", "subcontractor",
            delay_days=5, dry_run=False,
        )
        result = list_delay_events_from_db(delay_db)
        assert result["count"] == 2

    def test_filter_by_type(self, delay_db):
        record_delay_event_to_db(
            delay_db, "act-001", "excusable_compensable", "owner_change",
            delay_days=10, dry_run=False,
        )
        record_delay_event_to_db(
            delay_db, "act-002", "non_excusable", "subcontractor",
            delay_days=5, dry_run=False,
        )
        result = list_delay_events_from_db(delay_db, delay_type="excusable_compensable")
        assert result["count"] == 1

    def test_filter_by_activity(self, delay_db):
        record_delay_event_to_db(
            delay_db, "act-001", "non_excusable", "weather",
            delay_days=3, dry_run=False,
        )
        result = list_delay_events_from_db(delay_db, activity_id="act-001")
        assert result["count"] == 1


# ---------------------------------------------------------------------------
# Delay analysis
# ---------------------------------------------------------------------------


class TestDelayAnalysis:
    def test_empty(self, delay_db):
        result = generate_delay_analysis(delay_db)
        assert result["ok"] is True
        assert result["total_events"] == 0

    def test_with_events(self, delay_db):
        record_delay_event_to_db(
            delay_db, "act-001", "excusable_compensable", "owner_change",
            delay_days=10, cost_impact=50_000_000, dry_run=False,
        )
        record_delay_event_to_db(
            delay_db, "act-002", "non_excusable", "weather",
            delay_days=5, cost_impact=10_000_000, dry_run=False,
        )
        result = generate_delay_analysis(delay_db)
        assert result["total_events"] == 2
        assert result["total_delay_days"] == 15
        assert result["total_cost_impact"] == 60_000_000
        assert "excusable_compensable" in result["by_type"]
        assert "non_excusable" in result["by_type"]


# ---------------------------------------------------------------------------
# Time extension claim
# ---------------------------------------------------------------------------


class TestTimeExtension:
    def test_empty(self, delay_db):
        result = calculate_time_extension_entitlement(delay_db)
        assert result["ok"] is True
        assert result["recommended_extension_days"] == 0

    def test_excusable_only(self, delay_db):
        # Add 2 excusable + 1 non-excusable
        record_delay_event_to_db(
            delay_db, "act-001", "excusable_compensable", "owner_change",
            delay_days=10, cost_impact=50_000_000, dry_run=False,
        )
        record_delay_event_to_db(
            delay_db, "act-001", "excusable_non_compensable", "weather",
            delay_days=7, dry_run=False,
        )
        record_delay_event_to_db(
            delay_db, "act-002", "non_excusable", "subcontractor",
            delay_days=15, dry_run=False,
        )
        result = calculate_time_extension_entitlement(delay_db)
        # Only excusable delays count
        assert result["recommended_extension_days"] == 17  # 10 + 7
        assert result["compensable_days"] == 10
        assert result["compensable_cost"] == 50_000_000
        assert result["non_excusable_days"] == 15

    def test_summary_kr(self, delay_db):
        record_delay_event_to_db(
            delay_db, "act-001", "excusable_compensable", "design_error",
            delay_days=10, cost_impact=30_000_000, dry_run=False,
        )
        result = calculate_time_extension_entitlement(delay_db)
        assert "공기연장 권고" in result["summary_kr"]
        assert "10일" in result["summary_kr"]
