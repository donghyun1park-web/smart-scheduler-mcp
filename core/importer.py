from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from typing import Any

from core import db
from core.excel_io import read_field_input
from core.models import ChangeLogEntry, CostItem, DailyRecord, InspectionRecord, MaterialRecord
from core.reporting import create_weekly_construction_report


def import_field_input_to_db(
    db_path: str | Path,
    input_path: str | Path,
    *,
    project_id: str | None = None,
    imported_by: str | None = None,
) -> dict[str, Any]:
    parsed = read_field_input(input_path)
    errors = list(parsed["errors"])
    warnings = list(parsed["warnings"])
    if errors:
        return _import_result(db_path, errors=errors, warnings=warnings)

    daily_count = 0
    for row in parsed["daily_records"]:
        db.create_daily_record(
            db_path,
            DailyRecord(
                record_id=_new_id("dr"),
                activity_id=str(row["activity_id"]),
                work_date=date.fromisoformat(str(row["work_date"])),
                planned_qty=float(row.get("planned_qty") or 0.0),
                actual_qty=float(row.get("actual_qty") or 0.0),
                workers=int(float(row.get("workers") or 0)),
                equipment=str(row.get("equipment") or ""),
                owner=str(row.get("owner") or ""),
                remarks=str(row.get("remarks") or ""),
            ),
        )
        daily_count += 1

    cost_count = 0
    for row in parsed["cost_items"]:
        db.upsert_cost_item(
            db_path,
            CostItem(
                cost_item_id=f"cost-{row['activity_id']}",
                activity_id=str(row["activity_id"]),
                contract_amount=float(row.get("contract_amount") or 0.0),
                execution_budget=float(row.get("execution_budget") or 0.0),
                invested_cost=float(row.get("invested_cost") or 0.0),
                billing_amount=float(row.get("billing_amount") or 0.0),
            ),
        )
        cost_count += 1

    material_count = 0
    for row in parsed["materials"]:
        db.create_material_record(
            db_path,
            MaterialRecord(
                material_id=_new_id("mat"),
                activity_id=str(row["activity_id"]),
                material_name=str(row["material_name"]),
                expected_date=_optional_date(row.get("expected_date")),
                actual_date=_optional_date(row.get("actual_date")),
                status=str(row.get("status") or "planned"),
            ),
        )
        material_count += 1

    inspection_count = 0
    for row in parsed["inspections"]:
        db.create_inspection_record(
            db_path,
            InspectionRecord(
                inspection_id=_new_id("ins"),
                activity_id=str(row["activity_id"]),
                inspection_type=str(row["inspection_type"]),
                planned_date=_optional_date(row.get("planned_date")),
                actual_date=_optional_date(row.get("actual_date")),
                status=str(row.get("status") or "planned"),
            ),
        )
        inspection_count += 1

    db.log_change(
        db_path,
        ChangeLogEntry(
            change_id=_new_id("chg"),
            target_table="field_input",
            target_id=str(input_path),
            before_value="",
            after_value=f"daily={daily_count}, cost={cost_count}, materials={material_count}, inspections={inspection_count}",
            reason="excel_import",
            user=imported_by or "codex",
            changed_at=date.today(),
        ),
    )
    return _import_result(
        db_path,
        daily=daily_count,
        cost=cost_count,
        materials=material_count,
        inspections=inspection_count,
        errors=errors,
        warnings=warnings,
        project_id=project_id,
    )


def generate_weekly_report_from_db(
    db_path: str | Path,
    output_path: str | Path,
    *,
    report_style: str = "internal",
) -> dict[str, object]:
    site_data = build_site_data_from_db(db_path)
    return create_weekly_construction_report(site_data, output_path, report_style=report_style)


def build_site_data_from_db(db_path: str | Path) -> dict[str, object]:
    summary = db.load_project_summary(db_path)
    project = summary.get("project")
    cost_items = {item.activity_id: item for item in db.list_cost_items(db_path)}
    materials_by_activity = _group_by_activity(db.list_materials(db_path))
    inspections_by_activity = _group_by_activity(db.list_inspections(db_path))
    activities: list[dict[str, object]] = []
    planned_progress_values: list[float] = []
    today = date.today()
    for activity in db.list_activities(db_path):
        cumulative = db.get_cumulative_qty(db_path, activity.activity_id)
        actual_progress = cumulative["progress_pct"]
        planned_progress = _planned_progress(activity.ef_date, today, actual_progress)
        planned_progress_values.append(planned_progress)
        cost_item = cost_items.get(activity.activity_id)
        activities.append(
            {
                "activity_id": activity.activity_id,
                "name": activity.name,
                "discipline": activity.discipline,
                "zone": activity.zone,
                "planned_qty": cumulative["planned_qty"],
                "actual_qty": cumulative["actual_qty"],
                "planned_progress_pct": planned_progress,
                "actual_progress_pct": actual_progress,
                "weight": activity.cost or 1.0,
                "start_date": activity.es_date.isoformat() if activity.es_date else "",
                "finish_date": activity.ef_date.isoformat() if activity.ef_date else "",
                "status": "completed" if actual_progress >= 100 else "in_progress",
                "owner": _latest_owner(db_path, activity.activity_id),
                "this_week_actual": f"Actual progress {actual_progress:.1f}%",
                "next_week_plan": "Review next work package",
                "contract_amount": cost_item.contract_amount if cost_item else 0.0,
                "execution_budget": cost_item.execution_budget if cost_item else 0.0,
                "invested_cost": cost_item.invested_cost if cost_item else 0.0,
                "billing_amount": cost_item.billing_amount if cost_item else 0.0,
                "materials": materials_by_activity.get(activity.activity_id, []),
                "inspections": inspections_by_activity.get(activity.activity_id, []),
            }
        )
    planned_progress = round(sum(planned_progress_values) / len(planned_progress_values), 2) if planned_progress_values else 0.0
    return {
        "project": {
            "project_id": getattr(project, "project_id", ""),
            "name": getattr(project, "name", ""),
            "report_week": today.isoformat(),
            "planned_progress_pct": planned_progress,
        },
        "activities": activities,
    }


def _import_result(
    db_path: str | Path,
    *,
    daily: int = 0,
    cost: int = 0,
    materials: int = 0,
    inspections: int = 0,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": not errors,
        "db_path": str(db_path),
        "project_id": project_id,
        "daily_records_inserted": daily,
        "cost_items_upserted": cost,
        "materials_inserted": materials,
        "inspections_inserted": inspections,
        "errors": errors or [],
        "warnings": warnings or [],
    }


def _group_by_activity(records: list[Any]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for record in records:
        grouped.setdefault(record.activity_id, []).append(_record_dict(record))
    return grouped


def _record_dict(record: Any) -> dict[str, object]:
    return {
        key: value.isoformat() if isinstance(value, date) else value
        for key, value in record.__dict__.items()
        if key not in {"created_at", "updated_at"}
    }


def _latest_owner(db_path: str | Path, activity_id: str) -> str:
    records = db.list_daily_records(db_path, activity_id=activity_id)
    for record in reversed(records):
        if record.owner:
            return record.owner
    return ""


def _planned_progress(finish_date: date | None, today: date, actual_progress: float) -> float:
    if finish_date is not None and finish_date <= today:
        return 100.0
    return max(actual_progress, 0.0)


def _optional_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"
