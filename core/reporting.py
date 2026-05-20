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


def create_excel_report(project_path: str | Path, output_path: str | Path | None = None) -> dict[str, object]:
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
    workbook.close()
    return {"ok": True, "output_path": str(output), "sheets": REPORT_SHEETS}


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


def _write_headers(sheet: Worksheet, headers: list[str], header_format: Format) -> None:
    for col_idx, header in enumerate(headers):
        sheet.write(0, col_idx, header, header_format)


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    raise TypeError(f"Expected date or datetime, got {type(value)!r}")
