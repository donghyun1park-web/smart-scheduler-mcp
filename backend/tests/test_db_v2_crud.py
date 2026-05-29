from __future__ import annotations

from datetime import date

from core import db
from core.models import (
    Activity,
    BaselineSnapshot,
    Calendar,
    ChangeLogEntry,
    CostItem,
    DailyRecord,
    InspectionRecord,
    MaterialRecord,
    Project,
    ProjectSettings,
    WBS,
)


def test_daily_record_create_filter_and_cumulative_quantity(tmp_path):
    db_path = _project_db(tmp_path)
    db.create_daily_record(db_path, DailyRecord("dr-1", "act-1", date(2026, 5, 20), 100, 40, workers=5))
    db.create_daily_record(db_path, DailyRecord("dr-2", "act-1", date(2026, 5, 21), 50, 35, workers=6))

    records = db.list_daily_records(db_path, activity_id="act-1", start_date="2026-05-21")
    cumulative = db.get_cumulative_qty(db_path, "act-1")

    assert [record.record_id for record in records] == ["dr-2"]
    assert cumulative == {"planned_qty": 150.0, "actual_qty": 75.0, "progress_pct": 50.0}
    assert db.get_cumulative_qty(db_path, "missing") == {"planned_qty": 0.0, "actual_qty": 0.0, "progress_pct": 0.0}


def test_cost_item_upsert_and_summary(tmp_path):
    db_path = _project_db(tmp_path)
    db.upsert_cost_item(db_path, CostItem("cost-1", "act-1", 1000, 900, 450, 300))
    db.upsert_cost_item(db_path, CostItem("cost-1b", "act-1", 1000, 900, 540, 400))

    items = db.list_cost_items(db_path, activity_id="act-1")
    summary = db.get_cost_summary(db_path)

    assert len(items) == 1
    assert items[0].cost_item_id == "cost-1b"
    assert summary["execution_budget"] == 900.0
    assert summary["invested_cost"] == 540.0
    assert summary["cost_execution_rate"] == 60.0
    assert summary["billing_rate"] == 40.0


def test_material_and_inspection_create_update_filter(tmp_path):
    db_path = _project_db(tmp_path)
    material = db.create_material_record(
        db_path,
        MaterialRecord("mat-1", "act-1", "rebar", expected_date=date(2026, 5, 20), status="ordered"),
    )
    inspection = db.create_inspection_record(
        db_path,
        InspectionRecord("ins-1", "act-1", "rebar approval", planned_date=date(2026, 5, 21), status="pending"),
    )

    updated_material = db.update_material_status(db_path, material.material_id, actual_date="2026-05-22", status="delivered")
    updated_inspection = db.update_inspection_status(
        db_path,
        inspection.inspection_id,
        actual_date=date(2026, 5, 23),
        status="approved",
        approver="Kim",
    )

    assert updated_material.actual_date == date(2026, 5, 22)
    assert db.list_materials(db_path, status="delivered")[0].material_name == "rebar"
    assert updated_inspection.approver == "Kim"
    assert db.list_inspections(db_path, status="approved")[0].actual_date == date(2026, 5, 23)


def test_change_log_project_settings_and_baseline_snapshot(tmp_path):
    db_path = _project_db(tmp_path)
    change = db.log_change(
        db_path,
        ChangeLogEntry(
            "chg-1",
            "baseline_snapshots",
            "snap-1",
            "old",
            "new",
            "field revision",
            "Lee",
            changed_at=date(2026, 5, 21),
        ),
    )
    settings = db.upsert_project_settings(
        db_path,
        ProjectSettings(
            "settings-1",
            "project-1",
            disciplines=("civil", "architecture", "mechanical"),
            thresholds={"green_min": -3},
            report_style="internal",
        ),
    )
    snapshot = db.create_baseline_snapshot(
        db_path,
        BaselineSnapshot(
            "snap-1",
            "baseline-1",
            "act-1",
            date(2026, 5, 20),
            date(2026, 5, 25),
            5,
            "R1",
            project_id="project-1",
            approved_by="Kim",
        ),
    )

    assert db.list_change_log(db_path, target_table="baseline_snapshots")[0] == change
    assert settings.disciplines == ("토목", "건축", "기계설비")
    assert db.get_project_settings(db_path, "project-1") == settings
    assert db.list_baseline_snapshots(db_path, project_id="project-1") == [snapshot]
    assert db.get_latest_baseline_snapshot(db_path, "project-1") == snapshot
    assert db.get_project_settings(db_path, "missing") is None


def _project_db(tmp_path):
    db_path = tmp_path / "project.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Calendar", "1111100"))
    db.create_project(db_path, Project("project-1", "Demo", date(2026, 5, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-1", None, "WBS", "Root"))
    db.create_activity(db_path, Activity("act-1", "A-100", "Activity", "wbs-1", "civil", "B1", 5, cost=1000))
    return db_path
