"""Tests for tools.progress_tools (manual progress entry + lookups)."""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from core import db
from core.models import Activity, WBS
from tools.progress_tools import (
    get_activity_progress,
    get_today_schedule,
    set_activity_progress,
)
from tools.project_tools import create_project


@pytest.fixture()
def project_with_one_activity(tmp_path):
    project = create_project(
        "수동 진행률 테스트",
        "2026-06-01",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    path = project["project_path"]
    wbs = db.add_wbs(path, WBS(str(uuid.uuid4()), None, "MEP", "MEP", 1))
    act = Activity(str(uuid.uuid4()), "A001", "위생 1F", wbs.wbs_id, "위생", "1F", 5, 1_000_000,
                   es_date=date(2026, 6, 1), ef_date=date(2026, 6, 8))
    db.add_activity(path, act)
    return path, act


def test_set_activity_progress_persists_value(project_with_one_activity):
    path, act = project_with_one_activity
    result = set_activity_progress(path, act.activity_id, 65.0)
    assert result["ok"] is True
    assert result["progress_pct"] == 65.0
    stored = next(a for a in db.list_activities(path) if a.activity_id == act.activity_id)
    assert stored.progress_pct == 65.0


def test_set_activity_progress_rejects_out_of_range(project_with_one_activity):
    path, act = project_with_one_activity
    result = set_activity_progress(path, act.activity_id, 120.0)
    assert result["ok"] is False
    assert result["error_code"] == "INVALID_PROGRESS"


def test_set_activity_progress_rejects_unknown_id(project_with_one_activity):
    path, _ = project_with_one_activity
    result = set_activity_progress(path, "ghost-id", 50.0)
    assert result["ok"] is False
    assert result["error_code"] == "UNKNOWN_ACTIVITY"


def test_get_activity_progress_returns_both_sources(project_with_one_activity):
    path, act = project_with_one_activity
    set_activity_progress(path, act.activity_id, 40.0)
    out = get_activity_progress(path, act.activity_id)
    assert out["ok"] is True
    assert out["manual_progress_pct"] == 40.0
    assert out["daily_progress_pct"] == 0.0  # no DailyRecord
    assert out["daily_record_count"] == 0


def test_get_today_schedule_smoke(project_with_one_activity):
    path, _act = project_with_one_activity
    out = get_today_schedule(path, as_of="2026-06-01")
    assert out["ok"] is True
    assert out["starts_today_count"] == 1
    assert "starts_today" in out
