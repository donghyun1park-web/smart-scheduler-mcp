"""Tests for core.dashboard and tools.dashboard_tools."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core import db
from core.dashboard import (
    generate_dashboard_markdown,
    generate_site_briefing,
    get_delayed_with_recovery,
    get_progress_by_discipline,
)
from core.models import Activity, Calendar, CostItem, Project, WBS


@pytest.fixture
def dashboard_db(tmp_path: Path) -> Path:
    """Create a .scheduler DB with diverse activities for dashboard testing."""
    db_path = tmp_path / "dashboard_test.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
    db.create_project(db_path, Project("proj-1", "홍은동 테스트현장", date(2027, 1, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "Root"))

    # On-track activity (건축)
    db.create_activity(
        db_path,
        Activity("act-001", "A-001", "골조공사", "wbs-root", "건축", "", 365,
                 es_date=date(2027, 1, 1), ef_date=date(2027, 12, 31)),
    )
    db.upsert_cost_item(
        db_path,
        CostItem("cost-001", "act-001", contract_amount=2_000_000_000, execution_budget=1_800_000_000),
    )

    # Delayed activity (기계설비) — started early but "slow"
    db.create_activity(
        db_path,
        Activity("act-002", "A-002", "배관공사", "wbs-root", "기계설비", "", 180,
                 es_date=date(2027, 1, 1), ef_date=date(2027, 6, 30)),
    )
    db.upsert_cost_item(
        db_path,
        CostItem("cost-002", "act-002", contract_amount=500_000_000, execution_budget=450_000_000),
    )

    # Future activity (전기설비)
    db.create_activity(
        db_path,
        Activity("act-003", "A-003", "전등설비", "wbs-root", "전기설비", "", 120,
                 es_date=date(2027, 7, 1), ef_date=date(2027, 10, 31)),
    )
    db.upsert_cost_item(
        db_path,
        CostItem("cost-003", "act-003", contract_amount=300_000_000, execution_budget=270_000_000),
    )

    return db_path


def test_site_briefing(dashboard_db: Path):
    result = generate_site_briefing(dashboard_db, as_of=date(2027, 4, 1))
    assert result["ok"] is True
    assert "홍은동" in result["project_name"]
    assert result["overall_planned_pct"] > 0
    assert result["status"] in ("정상", "주의", "부진")
    assert "briefing" in result
    assert isinstance(result["briefing"], str)


def test_site_briefing_before_start(dashboard_db: Path):
    result = generate_site_briefing(dashboard_db, as_of=date(2026, 12, 1))
    assert result["ok"] is True
    assert result["overall_planned_pct"] == 0


def test_progress_by_discipline(dashboard_db: Path):
    result = get_progress_by_discipline(dashboard_db, as_of=date(2027, 4, 1))
    assert result["ok"] is True
    disciplines = {r["discipline"] for r in result["rows"]}
    assert "건축" in disciplines
    assert "기계설비" in disciplines


def test_delayed_with_recovery(dashboard_db: Path):
    # At mid-project, with no daily records, all should appear on-track (time-based)
    result = get_delayed_with_recovery(dashboard_db, as_of=date(2027, 4, 1), threshold_pct=5.0)
    assert result["ok"] is True
    assert isinstance(result["rows"], list)
    # With time-based progress and no actuals, there should be no delayed activities
    assert result["delayed_count"] == 0


def test_delayed_with_recovery_high_threshold(dashboard_db: Path):
    result = get_delayed_with_recovery(dashboard_db, as_of=date(2027, 4, 1), threshold_pct=0.0)
    assert result["ok"] is True


def test_dashboard_markdown(dashboard_db: Path):
    result = generate_dashboard_markdown(dashboard_db, as_of=date(2027, 4, 1))
    assert result["ok"] is True
    md = result["markdown"]
    assert "# 홍은동" in md
    assert "## 종합 현황" in md
    assert "## 공종별 공정률" in md
    assert "건축" in md
    assert isinstance(result["briefing"], str)


def test_dashboard_markdown_has_billing_section(dashboard_db: Path):
    result = generate_dashboard_markdown(dashboard_db, as_of=date(2027, 4, 1))
    assert "## 기성 현황" in result["markdown"]
