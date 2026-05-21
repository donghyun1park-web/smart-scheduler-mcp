from __future__ import annotations

from datetime import date

from core import db
from core.models import Activity, Calendar, CostItem, DailyRecord, InspectionRecord, MaterialRecord, Project, WBS
from viewer.components.site_manager_dashboard import load_site_dashboard_data_from_db


def test_load_site_dashboard_data_from_db_builds_required_sections(tmp_path):
    db_path = _project_db(tmp_path)

    dashboard = load_site_dashboard_data_from_db(db_path, project_id="project-1", as_of_date=date(2026, 5, 25))

    assert dashboard["project"]["project_id"] == "project-1"
    assert dashboard["as_of_date"] == "2026-05-25"
    summary = dashboard["summary"]
    assert summary["planned_progress_pct"] >= summary["actual_progress_pct"]
    assert summary["progress_gap_pct"] == round(summary["actual_progress_pct"] - summary["planned_progress_pct"], 2)
    assert summary["cost_execution_rate"] > 0
    assert summary["billing_rate"] > 0
    assert summary["delayed_count"] >= 1
    assert summary["serious_risk_count"] >= 1
    assert summary["material_delay_count"] == 1
    assert summary["inspection_delay_count"] == 1
    assert summary["evm"]["status"] == "risk"
    assert summary["evm"]["earned_value"] > 0
    assert dashboard["disciplines"][0]["discipline"] == "토목"
    assert dashboard["zones"][0]["zone"] == "B1"
    assert dashboard["delayed_top10"]
    assert dashboard["cost_risks"]
    assert dashboard["materials"]
    assert dashboard["inspections"]
    assert dashboard["activities"]


def test_load_site_dashboard_data_from_db_handles_empty_db(tmp_path):
    db_path = tmp_path / "empty.scheduler"
    db.initialize_database(db_path)

    dashboard = load_site_dashboard_data_from_db(db_path, as_of_date=date(2026, 5, 25))

    assert dashboard["project"]["project_id"] == ""
    assert dashboard["summary"]["actual_progress_pct"] == 0.0
    assert dashboard["summary"]["delayed_count"] == 0
    assert dashboard["activities"] == []


def _project_db(tmp_path):
    db_path = tmp_path / "project.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Calendar", "1111100"))
    db.create_project(db_path, Project("project-1", "Demo Site", date(2026, 5, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-1", None, "WBS", "Root"))
    db.create_activity(
        db_path,
        Activity(
            "act-1",
            "A-100",
            "Excavation",
            "wbs-1",
            "civil",
            "B1",
            5,
            cost=1000,
            es_date=date(2026, 5, 10),
            ef_date=date(2026, 5, 20),
        ),
    )
    db.create_daily_record(db_path, DailyRecord("dr-1", "act-1", date(2026, 5, 20), 100, 40, workers=5, owner="Kim"))
    db.upsert_cost_item(db_path, CostItem("cost-1", "act-1", 1000, 900, 800, 300))
    db.create_material_record(
        db_path,
        MaterialRecord("mat-1", "act-1", "rebar", expected_date=date(2026, 5, 18), status="ordered"),
    )
    db.create_inspection_record(
        db_path,
        InspectionRecord("ins-1", "act-1", "rebar approval", planned_date=date(2026, 5, 19), status="pending"),
    )
    return db_path
