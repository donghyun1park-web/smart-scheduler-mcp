from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from core import db
from core.excel_io import create_field_input_template
from core.models import Activity, Calendar, Project, WBS
from scripts.smoke_test_real_scheduler import run_smoke_test


def test_smoke_test_uses_copy_and_leaves_source_db_unchanged(tmp_path):
    source_db = _project_db(tmp_path)
    excel_input = _field_input(tmp_path)
    source_mtime = Path(source_db).stat().st_mtime_ns

    result = run_smoke_test(source_db, excel_input=excel_input, out_dir=tmp_path / "smoke", apply=False)

    assert result["ok"] is True
    assert result["source_db"] == str(source_db)
    assert result["working_copy"] != str(source_db)
    assert Path(result["working_copy"]).is_file()
    assert Path(source_db).stat().st_mtime_ns == source_mtime
    assert result["original_unchanged"] is True
    assert result["dashboard"]["ok"] is True
    assert result["dry_run"]["ok"] is True
    assert result["dry_run"]["changed"] is False
    assert result["import_apply"]["skipped"] is True
    assert set(result["reports"]) == {"internal", "hq", "client"}
    assert all(Path(path).is_file() for path in result["reports"].values())
    assert result["recovery"]["ok"] is True
    assert Path(result["result_json"]).is_file()
    assert db.list_daily_records(source_db) == []


def _project_db(tmp_path):
    db_path = tmp_path / "real.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Calendar", "1111100"))
    db.create_project(db_path, Project("project-1", "Demo", date(2026, 5, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-1", None, "WBS", "Root"))
    db.create_activity(db_path, Activity("act-1", "A-100", "Activity", "wbs-1", "civil", "B1", 5))
    return db_path


def _field_input(tmp_path):
    input_path = tmp_path / "field.xlsx"
    create_field_input_template(input_path, project_name="Demo", activities=[{"activity_id": "act-1"}])
    workbook = load_workbook(input_path)
    daily = workbook["01_실적입력"]
    daily["B4"] = "2026-05-21"
    daily["C4"] = 10
    daily["D4"] = 5
    daily["G4"] = "Kim"
    workbook.save(input_path)
    workbook.close()
    return input_path
