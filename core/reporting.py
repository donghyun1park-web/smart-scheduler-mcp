from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import xlsxwriter
from xlsxwriter.format import Format
from xlsxwriter.workbook import Workbook
from xlsxwriter.worksheet import Worksheet

from core import db
from core.cost import (
    calculate_billing_rate,
    calculate_cost_execution_rate,
    detect_cost_overrun,
)
from core.delay_detection import generate_delay_report
from core.models import Activity, Relationship, WBS
from core.number_utils import to_float
from core.progress import calculate_quantity_progress, calculate_weighted_progress
from core.report_styles import (
    ReportStyle,
    format_delay_issue,
    format_recovery_plan,
    format_report_summary,
    normalize_report_style,
)
from core.recovery import format_recovery_report, suggest_recovery_plans
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


def create_weekly_construction_report(
    site_data: dict[str, object],
    output_path: str | Path,
    *,
    report_style: str = "internal",
) -> dict[str, object]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    project = _dict_value(site_data.get("project"))
    activities = [_dict_value(activity) for activity in _list_value(site_data.get("activities"))]
    report_week = _date_from_value(project.get("report_week")) or date.today()
    style = normalize_report_style(report_style)

    progress_rows = [
        {
            **activity,
            "progress_pct": calculate_quantity_progress(
                to_float(activity.get("planned_qty")),
                to_float(activity.get("actual_qty")),
            ),
        }
        for activity in activities
    ]
    actual_progress = calculate_weighted_progress(
        [
            {
                "progress_pct": to_float(activity.get("actual_progress_pct", activity.get("progress_pct"))),
                "weight": to_float(activity.get("weight", 0.0)),
            }
            for activity in progress_rows
        ]
    )
    planned_progress = to_float(project.get("planned_progress_pct"))
    delay_rows = _activity_delay_rows(activities, report_week)
    cost_rows = _cost_rows(activities)
    recovery_rows = _recovery_rows(delay_rows)
    summary_data = _report_site_data(
        site_data,
        project,
        planned_progress,
        actual_progress,
        delay_rows,
        cost_rows,
    )

    workbook = xlsxwriter.Workbook(str(output))
    header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
    title_format = workbook.add_format({"bold": True, "font_size": 14})
    danger_format = workbook.add_format({"bg_color": "#F4CCCC", "border": 1})
    attention_format = workbook.add_format({"bg_color": "#FCE4D6", "border": 1})

    _write_v2_dashboard(
        workbook,
        project,
        planned_progress,
        actual_progress,
        delay_rows,
        cost_rows,
        header_format,
        title_format,
        summary_data,
        style,
    )
    _write_this_week_actuals(workbook, activities, header_format)
    _write_delay_top10(workbook, delay_rows, style, header_format, danger_format)
    _write_recovery_drafts(workbook, recovery_rows, style, header_format, attention_format)
    _write_cost_status(workbook, cost_rows, header_format, danger_format)
    _write_next_week_plan(workbook, activities, header_format)
    _write_gantt_data(workbook, activities, header_format)
    _write_report_narrative(workbook, style, summary_data, delay_rows, recovery_rows, header_format, title_format)
    workbook.close()

    return {
        "ok": True,
        "output_path": str(output),
        "sheets": [
            "05_대시보드",
            "금주 실적",
            "부진공정 TOP 10",
            "만회대책 초안",
            "원가현황",
            "다음 주 예정공정",
            "간트 데이터",
            "07_보고서",
        ],
        "delayed_count": len(delay_rows),
        "cost_overrun_count": sum(1 for row in cost_rows if row["overrun"]),
    }


def _activity_delay_rows(activities: list[dict[str, object]], report_week: date) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for activity in activities:
        issues = generate_delay_report([activity], today=report_week, top_n=20)
        if not issues:
            continue
        primary = issues[0]
        rows.append(
            {
                "activity_id": activity.get("activity_id"),
                "name": activity.get("name"),
                "discipline": activity.get("discipline", ""),
                "zone": activity.get("zone", ""),
                "owner": activity.get("owner", ""),
                "reason_code": primary.get("reason_code"),
                "reason": primary.get("message"),
                "risk_score": sum(to_float(issue.get("risk_score")) for issue in issues),
                "issues": issues,
            }
        )
    return sorted(rows, key=lambda row: str(row.get("activity_id") or ""))


def _cost_rows(activities: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for activity in activities:
        execution_budget = to_float(activity.get("execution_budget"))
        invested_cost = to_float(activity.get("invested_cost"))
        contract_amount = to_float(activity.get("contract_amount"))
        billing_amount = to_float(activity.get("billing_amount"))
        if execution_budget <= 0 and invested_cost <= 0 and contract_amount <= 0:
            continue
        progress_pct = to_float(activity.get("actual_progress_pct"))
        cost_rate = calculate_cost_execution_rate(execution_budget, invested_cost)
        billing_rate = calculate_billing_rate(contract_amount, billing_amount)
        rows.append(
            {
                "activity_id": activity.get("activity_id"),
                "name": activity.get("name"),
                "progress_pct": progress_pct,
                "execution_budget": execution_budget,
                "invested_cost": invested_cost,
                "cost_execution_rate": cost_rate,
                "contract_amount": contract_amount,
                "billing_amount": billing_amount,
                "billing_rate": billing_rate,
                "overrun": detect_cost_overrun(progress_pct, cost_rate),
            }
        )
    return rows


def _recovery_rows(delay_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for delay in delay_rows:
        reason_code = str(delay.get("reason_code") or "general")
        plans = suggest_recovery_plans(reason_code)
        rows.append(
            {
                "activity_id": delay.get("activity_id"),
                "name": delay.get("name"),
                "reason_code": reason_code,
                "candidate": plans[0]["title"] if plans else "현장 협의 후보",
                "review_note": "검토 필요",
                "style_sentence": "",
                "narrative": format_recovery_report(
                    {"activity_name": delay.get("name"), "reason_code": reason_code},
                    plans,
                ),
            }
        )
    return rows


def _write_v2_dashboard(
    workbook: Workbook,
    project: dict[str, object],
    planned_progress: float,
    actual_progress: float,
    delay_rows: list[dict[str, object]],
    cost_rows: list[dict[str, object]],
    header_format: Format,
    title_format: Format,
    summary_data: dict[str, object],
    report_style: ReportStyle,
) -> None:
    sheet = workbook.add_worksheet("05_대시보드")
    sheet.write("A1", "현장소장 대시보드", title_format)
    cost_execution = _average([to_float(row.get("cost_execution_rate")) for row in cost_rows])
    billing_rate = _average([to_float(row.get("billing_rate")) for row in cost_rows])
    risk_discipline = _risk_discipline(delay_rows)
    rows = [
        ("현장명", project.get("name", "")),
        ("전체 실적공정률", actual_progress),
        ("전체 계획공정률", planned_progress),
        ("공정 차이", round(actual_progress - planned_progress, 2)),
        ("원가집행률", cost_execution),
        ("기성률", billing_rate),
        ("부진공정 수", len(delay_rows)),
        ("위험공종", risk_discipline),
        ("핵심 리스크", _key_risk(delay_rows, cost_rows, report_style)),
        ("종합 의견", format_report_summary(summary_data, report_style)),
    ]
    for row_idx, (label, value) in enumerate(rows, start=2):
        sheet.write(row_idx - 1, 0, label, header_format)
        sheet.write(row_idx - 1, 1, value)


def _write_this_week_actuals(
    workbook: Workbook,
    activities: list[dict[str, object]],
    header_format: Format,
) -> None:
    sheet = workbook.add_worksheet("금주 실적")
    headers = ["activity_id", "name", "discipline", "zone", "this_week_actual", "actual_progress_pct"]
    _write_headers(sheet, headers, header_format)
    for row_idx, activity in enumerate(activities, start=1):
        sheet.write_row(row_idx, 0, [_excel_value(activity.get(header)) for header in headers])


def _write_delay_top10(
    workbook: Workbook,
    delay_rows: list[dict[str, object]],
    report_style: ReportStyle,
    header_format: Format,
    danger_format: Format,
) -> None:
    sheet = workbook.add_worksheet("부진공정 TOP 10")
    headers = ["activity_id", "name", "discipline", "zone", "reason_code", "owner", "risk_score", "reason"]
    _write_headers(sheet, headers, header_format)
    for row_idx, row in enumerate(delay_rows[:10], start=1):
        styled_row = {**row, "reason": format_delay_issue(row, report_style)}
        values = [_excel_value(styled_row.get(header)) for header in headers]
        for col_idx, value in enumerate(values):
            sheet.write(row_idx, col_idx, value, danger_format if col_idx < 7 else None)


def _write_recovery_drafts(
    workbook: Workbook,
    recovery_rows: list[dict[str, object]],
    report_style: ReportStyle,
    header_format: Format,
    attention_format: Format,
) -> None:
    sheet = workbook.add_worksheet("만회대책 초안")
    headers = ["activity_id", "name", "reason_code", "candidate", "review_note", "narrative"]
    _write_headers(sheet, headers, header_format)
    for row_idx, row in enumerate(recovery_rows, start=1):
        styled_row = {**row, "narrative": format_recovery_plan(row, report_style)}
        values = [_excel_value(styled_row.get(header)) for header in headers]
        for col_idx, value in enumerate(values):
            sheet.write(row_idx, col_idx, value, attention_format if col_idx in {3, 4} else None)


def _write_cost_status(
    workbook: Workbook,
    cost_rows: list[dict[str, object]],
    header_format: Format,
    danger_format: Format,
) -> None:
    sheet = workbook.add_worksheet("원가현황")
    headers = [
        "activity_id",
        "name",
        "progress_pct",
        "execution_budget",
        "invested_cost",
        "cost_execution_rate",
        "billing_rate",
        "overrun",
    ]
    _write_headers(sheet, headers, header_format)
    for row_idx, row in enumerate(cost_rows, start=1):
        fmt = danger_format if row.get("overrun") else None
        for col_idx, header in enumerate(headers):
            sheet.write(row_idx, col_idx, _excel_value(row.get(header)), fmt)


def _write_next_week_plan(
    workbook: Workbook,
    activities: list[dict[str, object]],
    header_format: Format,
) -> None:
    sheet = workbook.add_worksheet("다음 주 예정공정")
    headers = ["activity_id", "name", "discipline", "zone", "next_week_plan"]
    _write_headers(sheet, headers, header_format)
    for row_idx, activity in enumerate(activities, start=1):
        sheet.write_row(row_idx, 0, [_excel_value(activity.get(header)) for header in headers])


def _write_gantt_data(
    workbook: Workbook,
    activities: list[dict[str, object]],
    header_format: Format,
) -> None:
    sheet = workbook.add_worksheet("간트 데이터")
    headers = ["activity_id", "name", "start_date", "finish_date", "status", "actual_progress_pct"]
    _write_headers(sheet, headers, header_format)
    for row_idx, activity in enumerate(activities, start=1):
        sheet.write_row(row_idx, 0, [_excel_value(activity.get(header)) for header in headers])


def _write_report_narrative(
    workbook: Workbook,
    report_style: ReportStyle,
    summary_data: dict[str, object],
    delay_rows: list[dict[str, object]],
    recovery_rows: list[dict[str, object]],
    header_format: Format,
    title_format: Format,
) -> None:
    sheet = workbook.add_worksheet("07_보고서")
    sheet.write("A1", "주간 공정회의자료", title_format)
    rows = [
        ("report_style", report_style),
        ("종합 의견", format_report_summary(summary_data, report_style)),
        ("delayed_activity_count", len(delay_rows)),
        ("recovery_draft_count", len(recovery_rows)),
        ("language_policy", "만회대책은 초안/후보이며 현장 검토 필요"),
    ]
    _write_headers(sheet, ["section", "content"], header_format, row=1)
    for row_idx, (section, content) in enumerate(rows, start=2):
        sheet.write(row_idx, 0, section)
        sheet.write(row_idx, 1, content)


def _average(values: list[float]) -> float:
    filtered = [value for value in values if value > 0]
    if not filtered:
        return 0.0
    return round(sum(filtered) / len(filtered), 2)


def _risk_discipline(delay_rows: list[dict[str, object]]) -> str:
    scores: dict[str, float] = {}
    for row in delay_rows:
        discipline = str(row.get("discipline") or "")
        scores[discipline] = scores.get(discipline, 0.0) + to_float(row.get("risk_score"))
    if not scores:
        return ""
    return max(scores, key=lambda discipline: scores[discipline])


def _key_risk(
    delay_rows: list[dict[str, object]],
    cost_rows: list[dict[str, object]],
    report_style: ReportStyle,
) -> str:
    if cost_rows and any(row.get("overrun") for row in cost_rows):
        if report_style == "client":
            return "관련 비용 및 진행 현황 확인 필요"
        if report_style == "hq":
            return "원가 집행률과 실적공정률 차이 확인 필요"
        return "원가 과투입 검토 필요"
    if delay_rows:
        return str(delay_rows[0].get("reason") or "부진공정 검토 필요")
    return "특이 리스크 없음"


def _date_from_value(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _report_site_data(
    site_data: dict[str, object],
    project: dict[str, object],
    planned_progress: float,
    actual_progress: float,
    delay_rows: list[dict[str, object]],
    cost_rows: list[dict[str, object]],
) -> dict[str, object]:
    cost_execution = _average([to_float(row.get("cost_execution_rate")) for row in cost_rows])
    billing_rate = _average([to_float(row.get("billing_rate")) for row in cost_rows])
    summary = {
        "planned_progress_pct": planned_progress,
        "actual_progress_pct": actual_progress,
        "progress_gap_pct": round(actual_progress - planned_progress, 2),
        "cost_execution_rate": cost_execution,
        "billing_rate": billing_rate,
        "delayed_count": len(delay_rows),
    }
    return {**site_data, "project": project, "summary": summary}


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


def _write_headers(
    sheet: Worksheet,
    headers: list[str],
    header_format: Format,
    *,
    row: int = 0,
) -> None:
    for col_idx, header in enumerate(headers):
        sheet.write(row, col_idx, header, header_format)


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    raise TypeError(f"Expected date or datetime, got {type(value)!r}")
