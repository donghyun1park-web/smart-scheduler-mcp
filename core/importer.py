from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from core import db
from core.backup import create_backup
from core.cost import calculate_cost_execution_rate
from core.excel_io import read_field_input
from core.models import ChangeLogEntry, CostItem, DailyRecord, InspectionRecord, MaterialRecord
from core.progress import calculate_quantity_progress
from core.reporting import create_weekly_construction_report
from core.validation import validate_cost_progress_gap, validate_progress_quantities


CONFLICT_POLICIES = {"fail", "skip", "replace", "merge"}


def import_field_input_to_db(
    db_path: str | Path,
    input_path: str | Path,
    *,
    project_id: str | None = None,
    imported_by: str | None = None,
    conflict_policy: str = "fail",
    dry_run: bool = False,
    validate_before_commit: bool = True,
    backup_before_import: bool = True,
    actor: str = "system",
) -> dict[str, Any]:
    parsed = read_field_input(input_path)
    errors = list(parsed["errors"])
    warnings = list(parsed["warnings"])
    if conflict_policy not in CONFLICT_POLICIES:
        errors.append(f"Unsupported conflict_policy: {conflict_policy}")
    if conflict_policy == "merge":
        errors.append("conflict_policy='merge' is not implemented; use fail, skip, or replace.")
    activities = {activity.activity_id: activity for activity in db.list_activities(db_path)}
    if validate_before_commit:
        validation = _validate_import_rows(parsed, activities)
        errors.extend(validation["errors"])
        warnings.extend(validation["warnings"])

    conflicts = _detect_daily_conflicts(db_path, parsed["daily_records"])
    if conflicts and conflict_policy == "fail":
        errors.append(f"Duplicate daily records found for activity_id + work_date: {len(conflicts)} conflict(s).")

    if errors:
        return _import_result(
            db_path,
            errors=errors,
            warnings=warnings,
            conflicts=conflicts,
            dry_run=dry_run,
            project_id=project_id,
        )

    created = _empty_counters()
    updated = _empty_counters()
    skipped = _empty_counters()
    if dry_run:
        return _import_result(
            db_path,
            errors=errors,
            warnings=warnings,
            conflicts=conflicts,
            dry_run=True,
            project_id=project_id,
            created=created,
            updated=updated,
            skipped=skipped,
            changed=False,
        )

    backup_path: str | None = None
    if backup_before_import:
        try:
            backup = create_backup(db_path, reason="before_import")
            backup_path = str(backup.backup_path)
        except (OSError, FileNotFoundError) as exc:
            return _import_result(
                db_path,
                errors=[f"Backup before import failed: {exc}"],
                warnings=warnings,
                conflicts=conflicts,
                dry_run=dry_run,
                project_id=project_id,
            )

    daily_count = 0
    for row in parsed["daily_records"]:
        conflict_key = _daily_key(row)
        if conflict_key in conflicts:
            if conflict_policy == "skip":
                skipped["daily_records"] += 1
                continue
            if conflict_policy == "replace":
                existing_records = db.list_daily_records(
                    db_path,
                    activity_id=str(row["activity_id"]),
                    work_date=str(row["work_date"]),
                )
                db.delete_daily_records(db_path, activity_id=str(row["activity_id"]), work_date=str(row["work_date"]))
                db.log_change(
                    db_path,
                    ChangeLogEntry(
                        change_id=_new_id("chg"),
                        target_table="daily_records",
                        target_id=f"{row['activity_id']}:{row['work_date']}",
                        before_value=json.dumps([_record_dict(record) for record in existing_records], ensure_ascii=False),
                        after_value=json.dumps(row, ensure_ascii=False, default=str),
                        reason="excel_import_replace",
                        user=actor or imported_by or "system",
                        changed_at=date.today(),
                    ),
                )
                updated["daily_records"] += 1
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
        if conflict_key not in conflicts:
            created["daily_records"] += 1
        daily_count += 1

    cost_count = 0
    for row in parsed["cost_items"]:
        if db.list_cost_items(db_path, activity_id=str(row["activity_id"])):
            updated["cost_items"] += 1
        else:
            created["cost_items"] += 1
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
        created["materials"] += 1
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
        created["inspections"] += 1
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
            user=actor or imported_by or "codex",
            changed_at=date.today(),
        ),
    )
    if warnings:
        db.log_change(
            db_path,
            ChangeLogEntry(
                change_id=_new_id("chg"),
                target_table="field_input",
                target_id=str(input_path),
                before_value="",
                after_value=json.dumps(warnings, ensure_ascii=False),
                reason="excel_import_warnings",
                user=actor or imported_by or "codex",
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
        conflicts=conflicts,
        backup_path=backup_path,
        dry_run=dry_run,
        created=created,
        updated=updated,
        skipped=skipped,
        changed=True,
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
    conflicts: dict[tuple[str, str], dict[str, object]] | None = None,
    backup_path: str | None = None,
    dry_run: bool = False,
    created: dict[str, int] | None = None,
    updated: dict[str, int] | None = None,
    skipped: dict[str, int] | None = None,
    changed: bool = False,
    project_id: str | None = None,
) -> dict[str, Any]:
    conflict_rows = list((conflicts or {}).values())
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
        "conflicts": conflict_rows,
        "backup_path": backup_path,
        "dry_run": dry_run,
        "created": created or _empty_counters(),
        "updated": updated or _empty_counters(),
        "skipped": skipped or _empty_counters(),
        "changed": changed,
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


def _validate_import_rows(parsed: dict[str, Any], activities: dict[str, Any]) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    progress_by_activity: dict[str, tuple[float, float]] = {}
    for idx, row in enumerate(parsed["daily_records"], start=1):
        activity_id = str(row.get("activity_id") or "").strip()
        if not activity_id:
            errors.append(f"01_실적입력 row {idx} activity_id is required.")
            continue
        activity = activities.get(activity_id)
        if activity is None:
            errors.append(f"01_실적입력 row {idx} unknown activity_id: {activity_id}.")
            continue
        planned_qty = float(row.get("planned_qty") or 0.0)
        actual_qty = float(row.get("actual_qty") or 0.0)
        if planned_qty < 0:
            errors.append(f"{activity.name} ({activity_id}) planned_qty must be >= 0, got {planned_qty}.")
        if actual_qty < 0:
            errors.append(f"{activity.name} ({activity_id}) actual_qty must be >= 0, got {actual_qty}.")
        errors.extend(validate_progress_quantities(activity_id, activity.name, planned_qty, actual_qty))
        planned_total, actual_total = progress_by_activity.get(activity_id, (0.0, 0.0))
        progress_by_activity[activity_id] = (planned_total + planned_qty, actual_total + actual_qty)

    for idx, row in enumerate(parsed["cost_items"], start=1):
        activity_id = str(row.get("activity_id") or "").strip()
        activity = activities.get(activity_id)
        if activity is None:
            errors.append(f"02_원가입력 row {idx} unknown activity_id: {activity_id}.")
            continue
        execution_budget = float(row.get("execution_budget") or 0.0)
        invested_cost = float(row.get("invested_cost") or 0.0)
        progress_qty = progress_by_activity.get(activity_id, (0.0, 0.0))
        progress_pct = calculate_quantity_progress(progress_qty[0], progress_qty[1])
        cost_execution_rate = calculate_cost_execution_rate(execution_budget, invested_cost)
        warnings.extend(
            validate_cost_progress_gap(
                activity_id,
                activity.name,
                progress_pct=progress_pct,
                cost_execution_rate=cost_execution_rate,
            )
        )

    for sheet_name, rows in (("03_자재", parsed["materials"]), ("03_검측", parsed["inspections"])):
        for idx, row in enumerate(rows, start=1):
            activity_id = str(row.get("activity_id") or "").strip()
            if activity_id not in activities:
                errors.append(f"{sheet_name} row {idx} unknown activity_id: {activity_id}.")
    return {"errors": errors, "warnings": warnings}


def _detect_daily_conflicts(db_path: str | Path, rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, object]]:
    conflicts: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        activity_id, work_date = _daily_key(row)
        if not activity_id or not work_date:
            continue
        existing = db.list_daily_records(db_path, activity_id=activity_id, work_date=work_date)
        if existing:
            conflicts[(activity_id, work_date)] = {
                "activity_id": activity_id,
                "work_date": work_date,
                "existing_count": len(existing),
                "policy_scope": "daily_records",
            }
    return conflicts


def _daily_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("activity_id") or "").strip(), str(row.get("work_date") or "").strip()


def _empty_counters() -> dict[str, int]:
    return {"daily_records": 0, "cost_items": 0, "materials": 0, "inspections": 0}
