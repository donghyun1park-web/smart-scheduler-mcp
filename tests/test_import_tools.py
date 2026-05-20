from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook

from core import db
from tools.import_tools import import_excel, load_column_mapping_preset, save_column_mapping_preset
from tools.project_tools import create_project


FIXTURES = Path(__file__).parent / "fixtures"


def test_column_mapping_preset_save_and_load(tmp_path):
    preset = {
        "name": "sample",
        "columns": {
            "code": "Activity Code",
            "name": "Activity Name",
            "wbs_code": "WBS",
            "duration": "Duration",
        },
    }

    saved = save_column_mapping_preset("sample", preset["columns"], presets_dir=tmp_path)
    loaded = load_column_mapping_preset("sample", presets_dir=tmp_path)

    assert saved["ok"] is True
    assert loaded == preset


def test_import_excel_minimal_sample(tmp_path):
    project = create_project(
        "Import Pilot",
        "2026-01-05",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    sample_xlsx = FIXTURES / "sample_schedule.xlsx"
    preset = json.loads((FIXTURES / "column_mapping_sample.json").read_text(encoding="utf-8"))
    save_column_mapping_preset("sample", preset["columns"], presets_dir=tmp_path)

    result = import_excel(
        project["project_path"],
        sample_xlsx,
        preset_name="sample",
        presets_dir=tmp_path,
    )

    activities = db.list_activities(project["project_path"])
    relationships = db.list_relationships(project["project_path"])
    assert result["ok"] is True
    assert result["added_activities"] == 3
    assert result["added_relationships"] == 2
    assert result["failed_rows"] == []
    assert [activity.code for activity in activities] == ["A100", "A200", "A300"]
    assert [relationship.rel_type for relationship in relationships] == ["FS", "FS"]


def test_import_excel_detects_korean_timeline_schedule(tmp_path):
    project = create_project(
        "Timeline Pilot",
        "2026-06-01",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    sample_xlsx = tmp_path / "timeline.xlsx"
    _write_korean_timeline_fixture(sample_xlsx)

    result = import_excel(project["project_path"], sample_xlsx)

    activities = db.list_activities(project["project_path"])
    relationships = db.list_relationships(project["project_path"])
    assert result["ok"] is True
    assert result["added_activities"] == 2
    assert result["added_relationships"] == 0
    assert result["failed_rows"] == []
    assert "timeline schedule" in str(result["warnings"][0])
    assert [activity.code for activity in activities] == ["G012", "G013"]
    assert [activity.name for activity in activities] == ["가설휀스설치", "C.I.P+차수공사"]
    assert [activity.duration for activity in activities] == [30, 10]
    assert [activity.discipline for activity in activities] == ["공통", "공통"]
    assert relationships == []


def _write_korean_timeline_fixture(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet["A5"] = "공 종"
    sheet["B5"] = "항 목"
    sheet["C5"] = "구 분"
    sheet["D8"] = 10
    sheet["E8"] = 20
    sheet["F8"] = 30
    sheet["A12"] = "공통가설"
    sheet["B12"] = "가설휀스설치"
    sheet["C12"] = "RPP 휀스"
    sheet["D12"] = "착수"
    sheet["F12"] = "완료"
    sheet["A13"] = "토공사"
    sheet["B13"] = "C.I.P+차수공사"
    sheet["C13"] = "C.I.P천공"
    sheet["E13"] = "천공"
    workbook.save(path)
