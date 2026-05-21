from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from openpyxl import load_workbook
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

DAILY_HEADER_ALIASES = {
    "activity_id": "activity_id",
    "작업ID": "activity_id",
    "work_date": "work_date",
    "날짜": "work_date",
    "planned_qty": "planned_qty",
    "계획물량": "planned_qty",
    "actual_qty": "actual_qty",
    "금일실적": "actual_qty",
    "workers": "workers",
    "투입인원": "workers",
    "equipment": "equipment",
    "장비": "equipment",
    "owner": "owner",
    "담당자": "owner",
    "remarks": "remarks",
    "특이사항": "remarks",
}

COST_HEADER_ALIASES = {
    "activity_id": "activity_id",
    "작업ID": "activity_id",
    "contract_amount": "contract_amount",
    "계약금액": "contract_amount",
    "execution_budget": "execution_budget",
    "실행예산": "execution_budget",
    "invested_cost": "invested_cost",
    "투입원가": "invested_cost",
    "billing_amount": "billing_amount",
    "기성금액": "billing_amount",
    "remarks": "remarks",
    "비고": "remarks",
}

MATERIAL_INSPECTION_HEADER_ALIASES = {
    "activity_id": "activity_id",
    "작업ID": "activity_id",
    "material_name": "material_name",
    "자재명": "material_name",
    "expected_date": "expected_date",
    "예정일": "expected_date",
    "actual_date": "actual_date",
    "실제일": "actual_date",
    "inspection_type": "inspection_type",
    "검측명": "inspection_type",
    "planned_date": "planned_date",
    "검측예정일": "planned_date",
    "approval_date": "approval_date",
    "승인일": "approval_date",
    "status": "status",
    "상태": "status",
}


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


def read_daily_input(input_path: str | Path) -> list[dict[str, Any]]:
    return _read_table(
        input_path,
        FIELD_WORKBOOK_SHEETS[0],
        DAILY_HEADER_ALIASES,
        numeric_fields={"planned_qty", "actual_qty", "workers"},
        date_fields={"work_date"},
    )


def read_cost_input(input_path: str | Path) -> list[dict[str, Any]]:
    return _read_table(
        input_path,
        FIELD_WORKBOOK_SHEETS[1],
        COST_HEADER_ALIASES,
        numeric_fields={"contract_amount", "execution_budget", "invested_cost", "billing_amount"},
        date_fields=set(),
    )


def read_material_inspection_input(input_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    rows = _read_table(
        input_path,
        FIELD_WORKBOOK_SHEETS[2],
        MATERIAL_INSPECTION_HEADER_ALIASES,
        numeric_fields=set(),
        date_fields={"expected_date", "actual_date", "planned_date", "approval_date"},
    )
    materials: list[dict[str, Any]] = []
    inspections: list[dict[str, Any]] = []
    for row in rows:
        if row.get("material_name"):
            materials.append(
                {
                    "activity_id": row.get("activity_id", ""),
                    "material_name": row.get("material_name", ""),
                    "expected_date": row.get("expected_date"),
                    "actual_date": row.get("actual_date"),
                    "status": row.get("status", ""),
                }
            )
        if row.get("inspection_type"):
            inspections.append(
                {
                    "activity_id": row.get("activity_id", ""),
                    "inspection_type": row.get("inspection_type", ""),
                    "planned_date": row.get("planned_date"),
                    "actual_date": row.get("approval_date") or row.get("actual_date"),
                    "status": row.get("status", ""),
                }
            )
    return {"materials": materials, "inspections": inspections}


def read_field_input(input_path: str | Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "daily_records": [],
        "cost_items": [],
        "materials": [],
        "inspections": [],
        "errors": [],
        "warnings": [],
    }
    try:
        result["daily_records"] = read_daily_input(input_path)
    except ValueError as exc:
        result["errors"].append(str(exc))
    try:
        result["cost_items"] = read_cost_input(input_path)
    except ValueError as exc:
        result["errors"].append(str(exc))
    try:
        material_inspection = read_material_inspection_input(input_path)
        result["materials"] = material_inspection["materials"]
        result["inspections"] = material_inspection["inspections"]
    except ValueError as exc:
        result["errors"].append(str(exc))
    return result


def _read_table(
    input_path: str | Path,
    sheet_name: str,
    header_aliases: dict[str, str],
    *,
    numeric_fields: set[str],
    date_fields: set[str],
) -> list[dict[str, Any]]:
    workbook = load_workbook(input_path, data_only=True)
    try:
        if sheet_name not in workbook.sheetnames:
            raise ValueError(f"Missing required sheet: {sheet_name}")
        sheet = workbook[sheet_name]
        header_map = _header_map(sheet, header_aliases)
        rows: list[dict[str, Any]] = []
        for row_idx in range(4, sheet.max_row + 1):
            row = _read_row(sheet, row_idx, header_map, numeric_fields, date_fields)
            if _has_payload(row):
                rows.append(row)
        return rows
    finally:
        workbook.close()


def _header_map(sheet: Any, header_aliases: dict[str, str]) -> dict[int, str]:
    header_map: dict[int, str] = {}
    for cell in sheet[3]:
        if cell.value is None:
            continue
        header = str(cell.value).strip()
        field = header_aliases.get(header)
        if field is not None:
            header_map[cell.column] = field
    required = "activity_id"
    if required not in set(header_map.values()):
        raise ValueError(f"Missing required header in {sheet.title}: activity_id")
    return header_map


def _read_row(
    sheet: Any,
    row_idx: int,
    header_map: dict[int, str],
    numeric_fields: set[str],
    date_fields: set[str],
) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for col_idx, field in header_map.items():
        value = sheet.cell(row=row_idx, column=col_idx).value
        if value is None or value == "":
            row[field] = ""
        elif field in numeric_fields:
            row[field] = _number_value(value, sheet.title, row_idx, field)
        elif field in date_fields:
            row[field] = _date_value(value, sheet.title, row_idx, field)
        else:
            row[field] = str(value).strip()
    return row


def _has_payload(row: dict[str, Any]) -> bool:
    return bool(row.get("activity_id")) and any(value not in {"", None} for key, value in row.items() if key != "activity_id")


def _number_value(value: Any, sheet_name: str, row_idx: int, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{sheet_name} row {row_idx} {field} must be numeric, got {value!r}") from exc


def _date_value(value: Any, sheet_name: str, row_idx: int, field: str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError(f"{sheet_name} row {row_idx} {field} must be ISO date, got {value!r}") from exc


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
