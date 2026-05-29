"""Unit tests for core.progress activity-summary and today-schedule helpers."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from core import db
from core.models import Activity, DailyRecord, WBS
from core.progress import get_activity_progress_summary, get_today_schedule_summary
from tools.project_tools import create_project


@pytest.fixture()
def seeded_project(tmp_path):
    project = create_project(
        "진행률 테스트",
        "2026-06-01",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    path = project["project_path"]
    wbs = db.add_wbs(path, WBS(str(uuid.uuid4()), None, "MEP", "MEP", 1))

    today = date(2026, 6, 10)
    # Activity A: scheduled to start today, no daily records yet
    act_a = Activity(
        str(uuid.uuid4()), "A001", "오늘 시작", wbs.wbs_id, "위생", "1F", 3, 1_000_000,
        es_date=today, ef_date=today + timedelta(days=2),
    )
    db.add_activity(path, act_a)

    # Activity B: should have started 5 days ago, no daily records → overdue
    act_b = Activity(
        str(uuid.uuid4()), "A002", "5일 지연", wbs.wbs_id, "공조", "1F", 2, 500_000,
        es_date=today - timedelta(days=5), ef_date=today - timedelta(days=3),
    )
    db.add_activity(path, act_b)

    # Activity C: started on time with daily records; finishes today
    act_c = Activity(
        str(uuid.uuid4()), "A003", "오늘 완료", wbs.wbs_id, "공조", "1F", 3, 300_000,
        es_date=today - timedelta(days=2), ef_date=today,
    )
    db.add_activity(path, act_c)
    for i, d in enumerate([today - timedelta(days=2), today - timedelta(days=1), today]):
        db.create_daily_record(
            path,
            DailyRecord(
                record_id=str(uuid.uuid4()),
                activity_id=act_c.activity_id,
                work_date=d,
                planned_qty=10.0,
                actual_qty=10.0 if i < 2 else 5.0,
            ),
        )

    return path, today, (act_a, act_b, act_c)


def test_get_activity_progress_summary_no_records(seeded_project):
    path, _today, (act_a, _b, _c) = seeded_project
    summary = get_activity_progress_summary(path, act_a.activity_id)
    assert summary["progress_pct"] == 0.0
    assert summary["actual_start_date"] is None
    assert summary["actual_finish_date"] is None
    assert summary["daily_record_count"] == 0


def test_get_activity_progress_summary_with_records(seeded_project):
    path, today, (_a, _b, act_c) = seeded_project
    summary = get_activity_progress_summary(path, act_c.activity_id)
    assert summary["daily_record_count"] == 3
    assert summary["planned_qty_total"] == 30.0
    assert summary["actual_qty_total"] == 25.0
    assert summary["progress_pct"] == pytest.approx(83.33, abs=0.1)
    assert summary["actual_start_date"] == (today - timedelta(days=2)).isoformat()
    assert summary["actual_finish_date"] == today.isoformat()


def test_get_today_schedule_summary_counts(seeded_project):
    path, today, _ = seeded_project
    out = get_today_schedule_summary(path, as_of=today)
    assert out["starts_today_count"] == 1
    assert out["finishes_today_count"] == 1
    assert out["overdue_start_count"] == 1
    overdue = out["overdue_starts"][0]
    assert overdue["code"] == "A002"
    assert overdue["days_overdue"] == 5
