from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import xlsxwriter


FIELD_WORKBOOK_SHEETS = [
    "01_실적입력",
    "02_원가입력",
    "03_자재검측",
    "04_공정표",
    "05_대시보드",
    "06_부진공정",
    "07_보고서",
]


def create_field_input_template(
    output_path: str | Path,
    *,
    project_name: str = "",
    activities: list[Mapping[str, Any]] | None = None,
) -> dict[str, object]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook = xlsxwriter.Workbook(str(output))
    formats = _formats(workbook)

    _write_daily_sheet(workbook, project_name, activities or [], formats)
    _write_cost_sheet(workbook, project_name, activities or [], formats)
    _write_material_inspection_sheet(workbook, project_name, activities or [], formats)
    _write_schedule_sheet(workbook, activities or [], formats)
    _write_dashboard_sheet(workbook, project_name, formats)
    _write_delay_sheet(workbook, formats)
    _write_report_sheet(workbook, formats)

    workbook.close()
    return {"ok": True, "output_path": str(output), "sheets": FIELD_WORKBOOK_SHEETS}


def _formats(workbook: xlsxwriter.Workbook) -> dict[str, xlsxwriter.format.Format]:
    return {
        "title": workbook.add_format({"bold": True, "font_size": 14}),
        "header": workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1}),
        "input": workbook.add_format({"bg_color": "#FFEB9C", "border": 1}),
        "auto": workbook.add_format({"bg_color": "#D9EAD3", "border": 1}),
        "error": workbook.add_format({"bg_color": "#F4CCCC", "border": 1}),
        "attention": workbook.add_format({"bg_color": "#FCE4D6", "border": 1}),
    }


def _write_daily_sheet(
    workbook: xlsxwriter.Workbook,
    project_name: str,
    activities: list[Mapping[str, Any]],
    formats: dict[str, xlsxwriter.format.Format],
) -> None:
    sheet = workbook.add_worksheet(FIELD_WORKBOOK_SHEETS[0])
    sheet.write("A1", "project_name", formats["header"])
    sheet.write("B1", project_name, formats["input"])
    headers = ["activity_id", "work_date", "planned_qty", "actual_qty", "workers", "equipment", "owner", "remarks"]
    _write_headers(sheet, headers, formats["header"], row=2)
    for row_idx, activity in enumerate(activities, start=3):
        sheet.write(row_idx, 0, activity.get("activity_id"))
        for col_idx in range(1, len(headers)):
            sheet.write_blank(row_idx, col_idx, None, formats["input"])
    if not activities:
        sheet.write_blank(3, 1, None, formats["input"])


def _write_cost_sheet(
    workbook: xlsxwriter.Workbook,
    project_name: str,
    activities: list[Mapping[str, Any]],
    formats: dict[str, xlsxwriter.format.Format],
) -> None:
    sheet = workbook.add_worksheet(FIELD_WORKBOOK_SHEETS[1])
    sheet.write("A1", "project_name", formats["header"])
    sheet.write("B1", project_name, formats["input"])
    headers = ["activity_id", "contract_amount", "execution_budget", "invested_cost", "billing_amount", "remarks"]
    _write_headers(sheet, headers, formats["header"], row=2)
    for row_idx, activity in enumerate(activities, start=3):
        sheet.write(row_idx, 0, activity.get("activity_id"))
        for col_idx in range(1, len(headers)):
            sheet.write_blank(row_idx, col_idx, None, formats["input"])


def _write_material_inspection_sheet(
    workbook: xlsxwriter.Workbook,
    project_name: str,
    activities: list[Mapping[str, Any]],
    formats: dict[str, xlsxwriter.format.Format],
) -> None:
    sheet = workbook.add_worksheet(FIELD_WORKBOOK_SHEETS[2])
    sheet.write("A1", "project_name", formats["header"])
    sheet.write("B1", project_name, formats["input"])
    headers = [
        "activity_id",
        "material_name",
        "expected_date",
        "actual_date",
        "inspection_type",
        "planned_date",
        "approval_date",
        "status",
    ]
    _write_headers(sheet, headers, formats["header"], row=2)
    for row_idx, activity in enumerate(activities, start=3):
        sheet.write(row_idx, 0, activity.get("activity_id"))
        for col_idx in range(1, len(headers)):
            sheet.write_blank(row_idx, col_idx, None, formats["input"])


def _write_schedule_sheet(
    workbook: xlsxwriter.Workbook,
    activities: list[Mapping[str, Any]],
    formats: dict[str, xlsxwriter.format.Format],
) -> None:
    sheet = workbook.add_worksheet(FIELD_WORKBOOK_SHEETS[3])
    headers = ["activity_id", "name", "discipline", "zone", "start_date", "finish_date", "status"]
    _write_headers(sheet, headers, formats["header"])
    for row_idx, activity in enumerate(activities, start=1):
        sheet.write_row(row_idx, 0, [activity.get(header, "") for header in headers])


def _write_dashboard_sheet(
    workbook: xlsxwriter.Workbook,
    project_name: str,
    formats: dict[str, xlsxwriter.format.Format],
) -> None:
    sheet = workbook.add_worksheet(FIELD_WORKBOOK_SHEETS[4])
    sheet.write("A1", "현장소장 대시보드", formats["title"])
    rows = [
        ("현장명", project_name),
        ("전체 계획공정률", ""),
        ("전체 실적공정률", ""),
        ("공정 차이", ""),
        ("원가집행률", ""),
        ("기성률", ""),
        ("부진공정 수", ""),
    ]
    for row_idx, (label, value) in enumerate(rows, start=2):
        sheet.write(row_idx - 1, 0, label, formats["header"])
        sheet.write(row_idx - 1, 1, value, formats["auto"])


def _write_delay_sheet(workbook: xlsxwriter.Workbook, formats: dict[str, xlsxwriter.format.Format]) -> None:
    sheet = workbook.add_worksheet(FIELD_WORKBOOK_SHEETS[5])
    _write_headers(sheet, ["activity_id", "name", "reason", "owner", "risk"], formats["header"])


def _write_report_sheet(workbook: xlsxwriter.Workbook, formats: dict[str, xlsxwriter.format.Format]) -> None:
    sheet = workbook.add_worksheet(FIELD_WORKBOOK_SHEETS[6])
    sheet.write("A1", "주간 공정회의자료", formats["title"])
    _write_headers(sheet, ["section", "content"], formats["header"], row=2)


def _write_headers(
    sheet: xlsxwriter.worksheet.Worksheet,
    headers: list[str],
    header_format: xlsxwriter.format.Format,
    *,
    row: int = 0,
) -> None:
    for col_idx, header in enumerate(headers):
        sheet.write(row, col_idx, header, header_format)
