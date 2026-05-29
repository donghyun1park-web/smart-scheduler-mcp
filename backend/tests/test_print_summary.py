"""Tests for the A4 one-page summary builder (no Streamlit rendering)."""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from core import db
from core.models import Activity, WBS
from tools.project_tools import create_project
from viewer.components.print_summary import build_one_page_summary


@pytest.fixture()
def small_project(tmp_path):
    project = create_project(
        "1매 요약 테스트",
        "2026-06-01",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    path = project["project_path"]
    wbs = db.add_wbs(path, WBS(str(uuid.uuid4()), None, "MEP", "MEP", 1))
    db.add_activity(path, Activity(str(uuid.uuid4()), "A1", "위생", wbs.wbs_id, "위생", "1F", 3, 1_000_000,
                                   es_date=date(2026, 6, 1), ef_date=date(2026, 6, 3), is_critical=True, es_workday=0))
    db.add_activity(path, Activity(str(uuid.uuid4()), "A2", "공조", wbs.wbs_id, "공조", "1F", 5, 2_000_000,
                                   es_date=date(2026, 6, 4), ef_date=date(2026, 6, 10), is_critical=True, es_workday=3))
    db.add_activity(path, Activity(str(uuid.uuid4()), "A3", "비임계", wbs.wbs_id, "전기", "1F", 2, 500_000,
                                   es_date=date(2026, 6, 4), ef_date=date(2026, 6, 5), is_critical=False, es_workday=3))
    return path


def test_build_one_page_summary_has_all_sections(small_project):
    state = build_one_page_summary(small_project, as_of=date(2026, 6, 1))
    assert state["activity_count"] == 3
    assert state["total_cost"] == pytest.approx(3_500_000)
    # Critical path: only A1, A2 — sorted by ES workday
    cp_codes = [r["code"] for r in state["critical_top10"]]
    assert cp_codes == ["A1", "A2"]
    # Cost rows sorted desc
    cost_disciplines = [r["discipline"] for r in state["cost_by_discipline"]]
    assert cost_disciplines[0] == "공조"  # highest cost
    # Briefing + today_schedule + health populated
    assert state["briefing"]["ok"] is True
    assert "starts_today_count" in state["today_schedule"]
    assert "score" in state["health"]
