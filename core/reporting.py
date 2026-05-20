from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import xlsxwriter
from xlsxwriter.format import Format
from xlsxwriter.workbook import Workbook
from xlsxwriter.worksheet import Worksheet

from core import db
from core.models import Activity, Relationship, WBS
from core.s_curve import build_s_curve_data


REPORT_SHEETS = [
    "\uc694\uc57d",
    "WBS",
    "Activity \uc0c1\uc138",
    "\uad00\uacc4",
    "S-Curve \ub370\uc774\ud130",
]

FIELD_UAT_REPORT_SHEETS = [
    "Field UAT Summary",
    "Diagnostics Summary",
    "Calibration Summary",
    "Calibration Corrections",
    "Calibration Warnings",
    "Recommended Actions",
]

_WARNING_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def create_excel_report(
    project_path: str | Path,
    output_path: str | Path | None = None,
    field_uat_result: dict[str, object] | None = None,
) -> dict[str, object]:
    project_path = Path(project_path)
    output = Path(output_path) if output_path is not None else _default_output_path(project_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    summary = db.load_project_summary(project_path)
    wbs_items = db.list_wbs(project_path)
    activities = db.list_activities(project_path)
    relationships = db.list_relationships(project_path)
    s_curve = build_s_curve_data(activities)

    workbook = xlsxwriter.Workbook(str(output))
    critical_format = workbook.add_format({"bg_color": "#FFCCCC"})
    header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})
    date_format = workbook.add_format({"num_format": "yyyy-mm-dd"})

    _write_summary(workbook, summary, activities, relationships, header_format)
    _write_wbs(workbook, wbs_items, header_format)
    _write_activities(workbook, activities, header_format, critical_format, date_format)
    _write_relationships(workbook, relationships, activities, header_format)
    _write_s_curve(workbook, s_curve, header_format, date_format)
    sheets = list(REPORT_SHEETS)
    if field_uat_result is not None:
        _write_field_uat_summary_sheets(workbook, field_uat_result, header_format)
        sheets.extend(FIELD_UAT_REPORT_SHEETS)
    workbook.close()
    return {"ok": True, "output_path": str(output), "sheets": sheets}


def _default_output_path(project_path: Path) -> Path:
    return project_path.parent / "reports" / f"{project_path.stem}_report.xlsx"


def _write_summary(
    workbook: Workbook,
    summary: dict[str, Any],
    activities: list[Activity],
    relationships: list[Relationship],
    header_format: Format,
) -> None:
    sheet = workbook.add_worksheet(REPORT_SHEETS[0])
    project = summary["project"]
    rows = [
        ("Project", getattr(project, "name", "")),
        ("Start Date", getattr(project, "start_date", "")),
        ("Activity Count", len(activities)),
        ("Relationship Count", len(relationships)),
        ("Cost Total", sum(activity.cost for activity in activities)),
        ("Completion Workday", summary["completion_workday"]),
    ]
    for row_idx, (label, value) in enumerate(rows):
        sheet.write(row_idx, 0, label, header_format)
        sheet.write(row_idx, 1, str(value) if value is not None else "")


def _write_wbs(workbook: Workbook, wbs_items: list[WBS], header_format: Format) -> None:
    sheet = workbook.add_worksheet(REPORT_SHEETS[1])
    headers = ["wbs_id", "parent_id", "code", "name", "sort_order"]
    _write_headers(sheet, headers, header_format)
    for row_idx, item in enumerate(wbs_items, start=1):
        sheet.write_row(row_idx, 0, [item.wbs_id, item.parent_id, item.code, item.name, item.sort_order])


def _write_activities(
    workbook: Workbook,
    activities: list[Activity],
    header_format: Format,
    critical_format: Format,
    date_format: Format,
) -> None:
    sheet = workbook.add_worksheet(REPORT_SHEETS[2])
    headers = [
        "code",
        "name",
        "wbs_id",
        "discipline",
        "zone",
        "duration",
        "cost",
        "es_workday",
        "ef_workday",
        "ls_workday",
        "lf_workday",
        "es_date",
        "ef_date",
        "total_float",
        "is_critical",
    ]
    _write_headers(sheet, headers, header_format)
    for row_idx, activity in enumerate(activities, start=1):
        row = [
            activity.code,
            activity.name,
            activity.wbs_id,
            activity.discipline,
            activity.zone,
            activity.duration,
            activity.cost,
            activity.es_workday,
            activity.ef_workday,
            activity.ls_workday,
            activity.lf_workday,
            activity.es_date,
            activity.ef_date,
            activity.total_float,
            activity.is_critical,
        ]
        fmt = critical_format if activity.is_critical else None
        for col_idx, value in enumerate(row):
            if col_idx in {11, 12} and value is not None:
                sheet.write_datetime(row_idx, col_idx, _as_datetime(value), fmt or date_format)
            else:
                sheet.write(row_idx, col_idx, value, fmt)


def _write_relationships(
    workbook: Workbook,
    relationships: list[Relationship],
    activities: list[Activity],
    header_format: Format,
) -> None:
    sheet = workbook.add_worksheet(REPORT_SHEETS[3])
    by_id = {activity.activity_id: activity for activity in activities}
    headers = ["pred_code", "succ_code", "rel_type", "lag_days"]
    _write_headers(sheet, headers, header_format)
    for row_idx, rel in enumerate(relationships, start=1):
        pred = by_id.get(rel.pred_id)
        succ = by_id.get(rel.succ_id)
        sheet.write_row(
            row_idx,
            0,
            [
                pred.code if pred is not None else rel.pred_id,
                succ.code if succ is not None else rel.succ_id,
                rel.rel_type,
                rel.lag_days,
            ],
        )


def _write_s_curve(
    workbook: Workbook,
    rows: list[dict[str, date | float]],
    header_format: Format,
    date_format: Format,
) -> None:
    sheet = workbook.add_worksheet(REPORT_SHEETS[4])
    headers = ["date", "planned_value", "cumulative_value"]
    _write_headers(sheet, headers, header_format)
    for row_idx, row in enumerate(rows, start=1):
        sheet.write_datetime(row_idx, 0, _as_datetime(row["date"]), date_format)
        sheet.write(row_idx, 1, row["planned_value"])
        sheet.write(row_idx, 2, row["cumulative_value"])


def _write_field_uat_summary_sheets(
    workbook: Workbook,
    field_uat_result: dict[str, object],
    header_format: Format,
) -> None:
    _write_key_value_sheet(workbook, FIELD_UAT_REPORT_SHEETS[0], _field_uat_summary_rows(field_uat_result), header_format)
    _write_key_value_sheet(
        workbook,
        FIELD_UAT_REPORT_SHEETS[1],
        _diagnostics_summary_rows(field_uat_result),
        header_format,
        label_header="Metric",
    )
    _write_key_value_sheet(workbook, FIELD_UAT_REPORT_SHEETS[2], _calibration_summary_rows(field_uat_result), header_format)
    _write_table_sheet(
        workbook,
        FIELD_UAT_REPORT_SHEETS[3],
        ["applied_order", "task_id", "field", "old_value", "new_value", "reason", "source"],
        _sorted_correction_records(field_uat_result),
        header_format,
    )
    _write_table_sheet(
        workbook,
        FIELD_UAT_REPORT_SHEETS[4],
        ["severity", "code", "message", "task_id", "applied_order", "phase"],
        _sorted_warning_records(field_uat_result),
        header_format,
    )
    _write_recommended_actions(workbook, field_uat_result, header_format)


def _write_key_value_sheet(
    workbook: Workbook,
    sheet_name: str,
    rows: list[tuple[str, object]],
    header_format: Format,
    *,
    label_header: str = "Field",
) -> None:
    sheet = workbook.add_worksheet(sheet_name)
    _write_headers(sheet, [label_header, "Value"], header_format)
    sheet.set_column(0, 0, 34)
    sheet.set_column(1, 1, 48)
    for row_idx, (label, value) in enumerate(rows, start=1):
        sheet.write(row_idx, 0, label)
        sheet.write(row_idx, 1, _excel_value(value))


def _write_table_sheet(
    workbook: Workbook,
    sheet_name: str,
    headers: list[str],
    rows: list[dict[str, object]],
    header_format: Format,
) -> None:
    sheet = workbook.add_worksheet(sheet_name)
    _write_headers(sheet, headers, header_format)
    sheet.set_column(0, len(headers) - 1, 24)
    for row_idx, row in enumerate(rows, start=1):
        sheet.write_row(row_idx, 0, [_excel_value(row.get(header)) for header in headers])


def _write_recommended_actions(
    workbook: Workbook,
    field_uat_result: dict[str, object],
    header_format: Format,
) -> None:
    sheet = workbook.add_worksheet(FIELD_UAT_REPORT_SHEETS[5])
    headers = ["order", "action"]
    _write_headers(sheet, headers, header_format)
    sheet.set_column(0, 0, 10)
    sheet.set_column(1, 1, 88)
    actions = field_uat_result.get("recommended_next_actions")
    if not isinstance(actions, list):
        return
    for row_idx, action in enumerate(actions, start=1):
        sheet.write(row_idx, 0, row_idx)
        sheet.write(row_idx, 1, _excel_value(action))


def _field_uat_summary_rows(field_uat_result: dict[str, object]) -> list[tuple[str, object]]:
    input_summary = _dict_value(field_uat_result.get("input_summary"))
    diagnostics = _dict_value(field_uat_result.get("diagnostics_summary"))
    cpm = _dict_value(field_uat_result.get("cpm_summary"))
    calibration = _dict_value(field_uat_result.get("calibration_summary"))
    artifacts = _dict_value(field_uat_result.get("artifacts"))
    return [
        ("project_id", field_uat_result.get("project_id")),
        ("field_uat_status", field_uat_result.get("field_uat_status")),
        ("source_type", input_summary.get("source_type")),
        ("task_count", input_summary.get("task_count")),
        ("dependency_count", input_summary.get("dependency_count")),
        ("relationship_coverage_ratio", diagnostics.get("relationship_coverage_ratio")),
        ("cost_coverage_ratio", diagnostics.get("cost_coverage_ratio")),
        ("cycle_detected", diagnostics.get("cycle_detected")),
        ("before_finish_date", cpm.get("before_finish_date")),
        ("after_finish_date", calibration.get("after_finish_date")),
        ("target_finish_date", calibration.get("target_finish_date")),
        ("delta_days_before", calibration.get("delta_days_before")),
        ("delta_days_after", calibration.get("delta_days_after")),
        ("summary_json_path", artifacts.get("summary_json")),
        ("summary_markdown_path", artifacts.get("summary_markdown")),
    ]


def _diagnostics_summary_rows(field_uat_result: dict[str, object]) -> list[tuple[str, object]]:
    diagnostics = _dict_value(field_uat_result.get("diagnostics_summary"))
    input_summary = _dict_value(field_uat_result.get("input_summary"))
    keys = [
        "task_count",
        "dependency_count",
        "tasks_without_predecessor_count",
        "tasks_without_successor_count",
        "isolated_task_count",
        "missing_duration_count",
        "zero_or_negative_duration_count",
        "missing_cost_count",
        "duplicate_task_id_count",
        "cycle_detected",
        "disconnected_component_count",
        "relationship_coverage_ratio",
        "cost_coverage_ratio",
    ]
    rows: list[tuple[str, object]] = []
    for key in keys:
        value = diagnostics.get(key, input_summary.get(key))
        rows.append((key, value))
    return rows


def _calibration_summary_rows(field_uat_result: dict[str, object]) -> list[tuple[str, object]]:
    calibration = _dict_value(field_uat_result.get("calibration_summary"))
    cpm = _dict_value(field_uat_result.get("cpm_summary"))
    warnings = _list_value(field_uat_result.get("warnings"))
    critical_path_before = cpm.get("critical_path_task_count")
    return [
        ("target_finish_date", calibration.get("target_finish_date")),
        ("before_finish_date", cpm.get("before_finish_date")),
        ("after_finish_date", calibration.get("after_finish_date")),
        ("delta_days_before", calibration.get("delta_days_before")),
        ("delta_days_after", calibration.get("delta_days_after")),
        ("critical_path_before_count", critical_path_before),
        ("critical_path_after_count", calibration.get("critical_path_after_count", critical_path_before)),
        ("dependency_count_before", calibration.get("dependency_count_before")),
        ("dependency_count_after", calibration.get("dependency_count_after")),
        ("correction_count", calibration.get("correction_count")),
        ("warning_count", sum(1 for warning in warnings if _dict_value(warning).get("severity") == "warning")),
        ("error_count", sum(1 for warning in warnings if _dict_value(warning).get("severity") == "error")),
    ]


def _sorted_correction_records(field_uat_result: dict[str, object]) -> list[dict[str, object]]:
    records = [_dict_value(record) for record in _list_value(field_uat_result.get("correction_records"))]
    return sorted(records, key=lambda record: _int_sort_value(record.get("applied_order")))


def _sorted_warning_records(field_uat_result: dict[str, object]) -> list[dict[str, object]]:
    records = [_dict_value(record) for record in _list_value(field_uat_result.get("warnings"))]
    return sorted(
        records,
        key=lambda record: (
            _WARNING_SEVERITY_ORDER.get(str(record.get("severity") or "info"), 99),
            str(record.get("phase") or ""),
            _int_sort_value(record.get("applied_order")),
        ),
    )


def _dict_value(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _int_sort_value(value: object) -> int:
    if value is None:
        return 10**9
    if isinstance(value, int):
        return value
    return int(str(value))


def _excel_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, date | datetime):
        return value.isoformat()
    return str(value)


def _write_headers(sheet: Worksheet, headers: list[str], header_format: Format) -> None:
    for col_idx, header in enumerate(headers):
        sheet.write(0, col_idx, header, header_format)


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    raise TypeError(f"Expected date or datetime, got {type(value)!r}")
