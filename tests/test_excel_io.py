from __future__ import annotations

from openpyxl import load_workbook

from core.excel_io import (
    FIELD_WORKBOOK_SHEETS,
    create_field_input_template,
    read_cost_input,
    read_daily_input,
    read_field_input,
    read_material_inspection_input,
)


def test_create_field_input_template_has_required_sheets_and_headers(tmp_path):
    output = tmp_path / "field_template.xlsx"

    result = create_field_input_template(output, project_name="Demo Site")

    workbook = load_workbook(result["output_path"])
    assert workbook.sheetnames == FIELD_WORKBOOK_SHEETS
    assert workbook["01_실적입력"]["A1"].value == "project_name"
    assert workbook["01_실적입력"]["B1"].value == "Demo Site"
    assert workbook["02_원가입력"]["A3"].value == "activity_id"
    assert workbook["03_자재검측"]["A3"].value == "activity_id"
    assert workbook["05_대시보드"]["A1"].value == "현장소장 대시보드"


def test_template_marks_input_and_auto_cells_with_distinct_fills(tmp_path):
    output = tmp_path / "field_template.xlsx"
    create_field_input_template(output, project_name="Demo Site")

    workbook = load_workbook(output)
    input_cell = workbook["01_실적입력"]["B4"]
    auto_cell = workbook["05_대시보드"]["B3"]

    assert input_cell.fill.fgColor.rgb == "FFFFEB9C"
    assert auto_cell.fill.fgColor.rgb == "FFD9EAD3"


def test_template_has_field_use_protection_and_validation(tmp_path):
    output = tmp_path / "field_template.xlsx"
    create_field_input_template(output, project_name="Demo Site", activities=[{"activity_id": "A-100"}])

    workbook = load_workbook(output)
    daily = workbook["01_실적입력"]
    material_inspection = workbook["03_자재검측"]

    assert daily.freeze_panes == "A4"
    assert daily.auto_filter.ref == "A3:H4"
    assert daily.protection.sheet is True
    assert daily["B4"].protection.locked is False
    assert daily["A4"].protection.locked is True
    assert len(daily.data_validations.dataValidation) >= 1
    assert len(material_inspection.data_validations.dataValidation) >= 1


def test_read_field_input_round_trips_template_rows(tmp_path):
    output = tmp_path / "현장입력.xlsx"
    create_field_input_template(
        output,
        project_name="Demo Site",
        activities=[{"activity_id": "A-100"}],
    )
    workbook = load_workbook(output)
    daily = workbook["01_실적입력"]
    daily["B4"] = "2026-05-21"
    daily["C4"] = 100
    daily["D4"] = 75
    daily["E4"] = 6
    daily["F4"] = "pump"
    daily["G4"] = "Kim"
    daily["H4"] = "ok"
    cost = workbook["02_원가입력"]
    cost["B4"] = 1000
    cost["C4"] = 900
    cost["D4"] = 450
    cost["E4"] = 300
    mi = workbook["03_자재검측"]
    mi["B4"] = "rebar"
    mi["C4"] = "2026-05-20"
    mi["D4"] = "2026-05-21"
    mi["E4"] = "rebar approval"
    mi["F4"] = "2026-05-22"
    mi["G4"] = "2026-05-23"
    mi["H4"] = "approved"
    workbook.save(output)
    workbook.close()

    result = read_field_input(output)

    assert result["daily_records"][0]["activity_id"] == "A-100"
    assert result["daily_records"][0]["work_date"] == "2026-05-21"
    assert result["cost_items"][0]["invested_cost"] == 450.0
    assert result["materials"][0]["material_name"] == "rebar"
    assert result["inspections"][0]["inspection_type"] == "rebar approval"
    assert result["errors"] == []


def test_read_helpers_ignore_empty_rows(tmp_path):
    output = tmp_path / "field_template.xlsx"
    create_field_input_template(output, project_name="Demo Site")

    assert read_daily_input(output) == []
    assert read_cost_input(output) == []
    assert read_material_inspection_input(output) == {"materials": [], "inspections": []}


def test_read_field_input_reports_missing_sheet(tmp_path):
    output = tmp_path / "broken.xlsx"
    create_field_input_template(output, project_name="Demo Site")
    workbook = load_workbook(output)
    del workbook["02_원가입력"]
    workbook.save(output)
    workbook.close()

    result = read_field_input(output)

    assert any("Missing required sheet: 02_원가입력" in error for error in result["errors"])
