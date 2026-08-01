from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from core import db
from core.data_health import check_data_health
from core.models import Activity, Calendar, CostItem, DailyRecord, MaterialRecord, Project, WBS


def test_empty_db_reports_no_activities(tmp_path: Path):
    db_path = tmp_path / "empty.scheduler"
    db.initialize_database(db_path)

    report = check_data_health(db_path)

    assert report.score == 60
    assert report.status == "watch"
    assert report.error_count == 1
    assert "no_activities" in {issue.code for issue in report.issues}
    json.dumps(report.to_dict(), ensure_ascii=False)


def test_activity_without_cost_and_relationships_is_flagged(tmp_path: Path):
    db_path = _health_db(tmp_path)

    report = check_data_health(db_path)

    codes = {issue.code for issue in report.issues}
    assert "activity_without_cost" in codes
    assert "no_cost_items" in codes
    assert "no_relationships" in codes
    assert report.warning_count >= 3
    assert report.score < 100


def test_orphans_bad_quantities_and_late_materials_are_flagged(tmp_path: Path):
    db_path = _health_db(tmp_path, with_cost=True)
    db.create_daily_record(db_path, DailyRecord("dr-good", "act-1", date(2026, 1, 5), 10, 20))
    db.create_material_record(
        db_path,
        MaterialRecord(
            "mat-1",
            "act-1",
            "Pump",
            expected_date=date(2026, 1, 3),
            status="ordered",
        ),
    )
    _insert_orphan_cost(db_path)
    _insert_bad_daily_record(db_path)

    report = check_data_health(db_path, as_of=date(2026, 1, 10))

    codes = {issue.code for issue in report.issues}
    assert "cost_without_activity" in codes
    assert "daily_record_unknown_activity" in codes
    assert "negative_quantity" in codes
    assert "progress_over_100" in codes
    assert "late_materials" in codes
    assert report.status == "risk"


def test_max_issues_limits_issue_payload(tmp_path: Path):
    db_path = _health_db(tmp_path, with_cost=True)
    _insert_orphan_cost(db_path)
    _insert_bad_daily_record(db_path)

    report = check_data_health(db_path, max_issues=2)

    assert len(report.issues) == 2
    assert report.error_count >= 1


def _health_db(tmp_path: Path, *, with_cost: bool = False):
    db_path = tmp_path / "health.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal", "Calendar", "1111100"))
    db.create_project(db_path, Project("proj", "Health Site", date(2026, 1, 1), "cal"))
    db.create_wbs(db_path, WBS("wbs", None, "ROOT", "ROOT"))
    db.create_activity(
        db_path,
        Activity(
            "act-1",
            "A-001",
            "Foundation",
            "wbs",
            "architecture",
            "1F",
            10,
            es_date=date(2026, 1, 1),
            ef_date=date(2026, 1, 10),
        ),
    )
    if with_cost:
        db.upsert_cost_item(db_path, CostItem("cost-1", "act-1", 1000, 900, 300, 100))
    return db_path


def _insert_orphan_cost(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO cost_items(
                cost_item_id, activity_id, contract_amount, execution_budget,
                invested_cost, billing_amount, created_at, updated_at
            )
            VALUES ('cost-orphan', 'missing-act', 100, 100, 0, 0, 'now', 'now')
            """
        )


def _insert_bad_daily_record(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO daily_records(
                record_id, activity_id, work_date, planned_qty, actual_qty,
                workers, equipment, owner, remarks, created_at, updated_at
            )
            VALUES ('dr-bad', 'missing-act', '2026-01-04', -1, 3, 0, '', '', '', 'now', 'now')
            """
        )
