"""Tests for core.productivity and tools.productivity_tools."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core import db
from core.productivity import (
    analyze_activity_productivity,
    analyze_productivity_summary,
    classify_productivity_status,
    get_productivity_trend,
)
from core.models import Activity, Calendar, CostItem, DailyRecord, Project, WBS


@pytest.fixture
def productivity_db(tmp_path: Path) -> Path:
    """Create a DB with activities and daily records."""
    db_path = tmp_path / "productivity_test.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
    db.create_project(db_path, Project("proj-1", "Test Project", date(2028, 1, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "Root"))

    # Activity 1: good productivity
    db.create_activity(
        db_path,
        Activity(
            activity_id="act-001", code="A-001", name="골조공사",
            wbs_id="wbs-root", discipline="건축", zone="", duration=180,
            es_date=date(2028, 1, 1), ef_date=date(2028, 6, 30),
        ),
    )
    # Daily records: good performance (actual ≈ planned)
    for i in range(10):
        db.create_daily_record(
            db_path,
            DailyRecord(
                f"rec-1-{i:02d}", "act-001", date(2028, 1, 10 + i),
                planned_qty=100, actual_qty=95 + i, workers=5,
            ),
        )

    # Activity 2: poor productivity
    db.create_activity(
        db_path,
        Activity(
            activity_id="act-002", code="A-002", name="배관공사",
            wbs_id="wbs-root", discipline="기계설비", zone="", duration=210,
            es_date=date(2028, 3, 1), ef_date=date(2028, 9, 30),
        ),
    )
    # Daily records: poor performance (actual ≈ 50% of planned)
    for i in range(5):
        db.create_daily_record(
            db_path,
            DailyRecord(
                f"rec-2-{i:02d}", "act-002", date(2028, 3, 5 + i),
                planned_qty=100, actual_qty=50, workers=3,
            ),
        )

    return db_path


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------


class TestClassifyProductivityStatus:
    def test_excellent(self):
        assert classify_productivity_status(115.0) == "우수"

    def test_on_target(self):
        assert classify_productivity_status(100.0) == "정상"

    def test_below_target(self):
        assert classify_productivity_status(80.0) == "부진"

    def test_critical(self):
        assert classify_productivity_status(60.0) == "위험"

    def test_boundary_110(self):
        assert classify_productivity_status(110.0) == "우수"

    def test_boundary_90(self):
        assert classify_productivity_status(90.0) == "정상"

    def test_boundary_70(self):
        assert classify_productivity_status(70.0) == "부진"


# ---------------------------------------------------------------------------
# Activity productivity
# ---------------------------------------------------------------------------


class TestActivityProductivity:
    def test_good_activity(self, productivity_db):
        result = analyze_activity_productivity(productivity_db, "act-001")
        assert result["ok"] is True
        assert result["record_count"] == 10
        assert result["status"] in ("우수", "정상")
        assert result["productivity_index"] > 90

    def test_poor_activity(self, productivity_db):
        result = analyze_activity_productivity(productivity_db, "act-002")
        assert result["ok"] is True
        assert result["record_count"] == 5
        assert result["productivity_index"] == pytest.approx(50.0, abs=1)
        assert result["status"] == "위험"

    def test_nonexistent_activity(self, productivity_db):
        result = analyze_activity_productivity(productivity_db, "nonexistent")
        assert result["ok"] is False

    def test_no_records(self, productivity_db):
        # Create activity without records
        db.create_activity(
            productivity_db,
            Activity(
                activity_id="act-003", code="A-003", name="도장공사",
                wbs_id="wbs-root", discipline="건축", zone="", duration=30,
                es_date=date(2028, 7, 1), ef_date=date(2028, 7, 30),
            ),
        )
        result = analyze_activity_productivity(productivity_db, "act-003")
        assert result["ok"] is True
        assert result["record_count"] == 0
        assert result["status"] == "정보 부족"

    def test_output_per_worker(self, productivity_db):
        result = analyze_activity_productivity(productivity_db, "act-001")
        assert result["output_per_worker"] > 0
        assert result["avg_workers_per_day"] > 0


# ---------------------------------------------------------------------------
# Productivity summary
# ---------------------------------------------------------------------------


class TestProductivitySummary:
    def test_all_disciplines(self, productivity_db):
        result = analyze_productivity_summary(productivity_db)
        assert result["ok"] is True
        assert len(result["discipline_summary"]) == 2  # 건축, 기계설비
        assert len(result["activities"]) == 2

    def test_discipline_filter(self, productivity_db):
        result = analyze_productivity_summary(productivity_db, discipline="건축")
        assert result["ok"] is True
        assert len(result["discipline_summary"]) == 1
        assert result["discipline_summary"][0]["discipline"] == "건축"

    def test_overall_index(self, productivity_db):
        result = analyze_productivity_summary(productivity_db)
        assert result["overall_productivity_index"] > 0
        assert result["overall_status"] in ("우수", "정상", "부진", "위험")


# ---------------------------------------------------------------------------
# Productivity trend
# ---------------------------------------------------------------------------


class TestProductivityTrend:
    def test_basic(self, productivity_db):
        result = get_productivity_trend(productivity_db, "act-001")
        assert result["ok"] is True
        assert len(result["data_points"]) > 0
        assert result["trend"] in ("개선", "유지", "하락", "정보 부족")

    def test_limited_periods(self, productivity_db):
        result = get_productivity_trend(productivity_db, "act-001", periods=3)
        assert result["ok"] is True
        assert len(result["data_points"]) == 3

    def test_nonexistent(self, productivity_db):
        result = get_productivity_trend(productivity_db, "nonexistent")
        assert result["ok"] is False

    def test_data_point_structure(self, productivity_db):
        result = get_productivity_trend(productivity_db, "act-001")
        point = result["data_points"][0]
        assert "date" in point
        assert "planned_qty" in point
        assert "actual_qty" in point
        assert "workers" in point
        assert "productivity_index" in point
