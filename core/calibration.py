"""Calibration orchestration: apply patches and compare before/after CPM.

Dataclasses live in :mod:`core.calibration_models`; validation, schedule
diagnostics, and warning helpers in :mod:`core.calibration_diagnostics`.
They are re-exported here for backward compatibility — existing imports
(``from core.calibration import CalibrationPatch`` etc.) keep working.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path

from core import db
from core.calendar_utils import KoreanCalendar, map_activity_dates
from core.calibration_diagnostics import (
    diagnostic_warnings,
    field_uat_status,
    has_error,
    make_warning,
    schedule_diagnostics,
    validate_patch,
)
from core.calibration_models import (
    COST_COVERAGE_THRESHOLD,
    MAX_ABS_LAG_DAYS,
    RELATIONSHIP_COVERAGE_THRESHOLD,
    CalibrationPatch,
    DependencyOverride,
    DurationOverride,
    LagOverride,
)
from core.cpm import run_cpm
from core.models import Activity, Calendar, CpmResult, Project, Relationship

__all__ = [
    "CalibrationPatch",
    "DependencyOverride",
    "DurationOverride",
    "LagOverride",
    "RELATIONSHIP_COVERAGE_THRESHOLD",
    "COST_COVERAGE_THRESHOLD",
    "MAX_ABS_LAG_DAYS",
    "calibrate_project_completion",
]


def calibrate_project_completion(project_path: str | Path, patch: CalibrationPatch) -> dict[str, object]:
    """Apply a calibration patch and return before/after comparison.

    Pipeline: load project → run baseline CPM → diagnose → validate patch.
    If validation fails, return early with the baseline. Otherwise apply
    duration/dependency/lag overrides, rerun CPM, and emit a comparison
    plus warnings (including any new dependency cycles introduced).
    """
    activities = db.list_activities(project_path)
    relationships = db.list_relationships(project_path)
    summary = db.load_project_summary(project_path)
    project = summary["project"]
    if not isinstance(project, Project):
        return {"ok": False, "warnings": [make_warning("error", "PROJECT_NOT_FOUND", "Project not found")], "comparison": {}}
    calendar_model = db.get_calendar(project_path, project.calendar_id)
    if calendar_model is None:
        return {
            "ok": False,
            "warnings": [make_warning("error", "PROJECT_CALENDAR_NOT_FOUND", "Project calendar not found")],
            "comparison": {},
        }

    before_cpm = _run_cpm_with_dates(activities, relationships, project, calendar_model)
    before_diagnostics = schedule_diagnostics(activities, relationships, before_cpm)
    warnings = diagnostic_warnings(before_diagnostics, "before")
    warnings.extend(validate_patch(activities, relationships, patch))
    if has_error(warnings):
        return _result(
            ok=False,
            project=project,
            patch=patch,
            imported_activities=activities,
            calibrated_activities=activities,
            before_cpm=before_cpm,
            after_cpm=None,
            before_relationships=relationships,
            after_relationships=relationships,
            warnings=warnings,
            before_diagnostics=before_diagnostics,
            after_diagnostics=before_diagnostics,
        )

    calibrated_activities, correction_records = _apply_duration_overrides(activities, patch)
    calibrated_relationships, dependency_records = _apply_relationship_overrides(relationships, patch)
    correction_records.extend(dependency_records)

    after_cpm = _run_cpm_with_dates(calibrated_activities, calibrated_relationships, project, calendar_model)
    after_diagnostics = schedule_diagnostics(calibrated_activities, calibrated_relationships, after_cpm)
    if after_cpm.cycles_detected:
        warnings.append(
            make_warning(
                "error",
                "DEPENDENCY_CYCLE",
                f"Calibration creates dependency cycle: {after_cpm.cycles_detected}",
            )
        )
    warnings.extend(diagnostic_warnings(after_diagnostics, "after"))

    result = _result(
        ok=not bool(after_cpm.cycles_detected),
        project=project,
        patch=patch,
        imported_activities=activities,
        calibrated_activities=calibrated_activities,
        before_cpm=before_cpm,
        after_cpm=after_cpm,
        before_relationships=relationships,
        after_relationships=calibrated_relationships,
        warnings=warnings,
        before_diagnostics=before_diagnostics,
        after_diagnostics=after_diagnostics,
    )
    result["correction_records"] = _with_applied_order(correction_records)
    return result


def _apply_duration_overrides(
    activities: list[Activity],
    patch: CalibrationPatch,
) -> tuple[list[Activity], list[dict[str, object]]]:
    by_id = {activity.activity_id: activity for activity in activities}
    records: list[dict[str, object]] = []
    for override in patch.duration_overrides or []:
        activity = by_id[override.task_id]
        by_id[override.task_id] = replace(activity, duration=override.duration_days)
        records.append(
            _correction_record(
                task_id=override.task_id,
                field="duration",
                old_value=activity.duration,
                new_value=override.duration_days,
                reason=override.reason,
                source=override.source,
            )
        )
    return [by_id[activity.activity_id] for activity in activities], records


def _apply_relationship_overrides(
    relationships: list[Relationship],
    patch: CalibrationPatch,
) -> tuple[list[Relationship], list[dict[str, object]]]:
    calibrated = list(relationships)
    records: list[dict[str, object]] = []
    for dependency_override in patch.dependency_overrides or []:
        rel = Relationship(
            rel_id=str(uuid.uuid4()),
            pred_id=dependency_override.predecessor_id,
            succ_id=dependency_override.successor_id,
            rel_type=dependency_override.dependency_type,
            lag_days=dependency_override.lag_days,
        )
        calibrated.append(rel)
        records.append(
            _correction_record(
                task_id=dependency_override.successor_id,
                field="dependency",
                old_value=None,
                new_value=(
                    f"{dependency_override.dependency_type} "
                    f"from {dependency_override.predecessor_id} + {dependency_override.lag_days}d"
                ),
                reason=dependency_override.reason,
                source=dependency_override.source,
            )
        )
    for lag_override in patch.lag_overrides or []:
        for idx, rel in enumerate(calibrated):
            if rel.pred_id == lag_override.predecessor_id and rel.succ_id == lag_override.successor_id:
                calibrated[idx] = replace(rel, lag_days=lag_override.lag_days)
                records.append(
                    _correction_record(
                        task_id=lag_override.successor_id,
                        field="lag",
                        old_value=rel.lag_days,
                        new_value=lag_override.lag_days,
                        reason=lag_override.reason,
                        source=lag_override.source,
                    )
                )
                break
    return calibrated, records


def _run_cpm_with_dates(
    activities: list[Activity],
    relationships: list[Relationship],
    project: Project,
    calendar_model: Calendar,
) -> CpmResult:
    result = run_cpm(activities, relationships)
    if result.cycles_detected:
        return result
    calendar = KoreanCalendar(calendar_model)
    duration_by_id = {activity.activity_id: activity.duration for activity in activities}
    mapped = [
        map_activity_dates(
            activity_result,
            project.start_date,
            calendar,
            duration=duration_by_id[activity_result.activity_id],
        )
        for activity_result in result.activities
    ]
    return CpmResult(
        activities=mapped,
        total_duration_days=result.total_duration_days,
        critical_count=result.critical_count,
        completion_date=max((activity.ef_date for activity in mapped if activity.ef_date), default=None),
        cycles_detected=result.cycles_detected,
    )


def _result(
    *,
    ok: bool,
    project: Project,
    patch: CalibrationPatch,
    imported_activities: list[Activity],
    calibrated_activities: list[Activity],
    before_cpm: CpmResult,
    after_cpm: CpmResult | None,
    before_relationships: list[Relationship],
    after_relationships: list[Relationship],
    warnings: list[dict[str, object]],
    before_diagnostics: dict[str, object],
    after_diagnostics: dict[str, object],
) -> dict[str, object]:
    after = after_cpm or before_cpm
    comparison = _comparison(
        project=project,
        patch=patch,
        imported_activities=imported_activities,
        calibrated_activities=calibrated_activities,
        before_cpm=before_cpm,
        after_cpm=after,
        before_relationships=before_relationships,
        after_relationships=after_relationships,
        warnings=warnings,
        before_diagnostics=before_diagnostics,
        after_diagnostics=after_diagnostics,
    )
    return {
        "ok": ok,
        "project_name": project.name,
        "imported_schedule": _schedule_dict(imported_activities, before_relationships),
        "calibrated_schedule": _schedule_dict(calibrated_activities, after_relationships),
        "calibration_patch": _patch_dict(patch),
        "before_cpm": _cpm_dict(before_cpm),
        "after_cpm": _cpm_dict(after),
        "comparison": comparison,
        "diagnostics": {
            "before": before_diagnostics,
            "after": after_diagnostics,
        },
        "warnings": warnings,
    }


def _comparison(
    *,
    project: Project,
    patch: CalibrationPatch,
    imported_activities: list[Activity],
    calibrated_activities: list[Activity],
    before_cpm: CpmResult,
    after_cpm: CpmResult,
    before_relationships: list[Relationship],
    after_relationships: list[Relationship],
    warnings: list[dict[str, object]],
    before_diagnostics: dict[str, object],
    after_diagnostics: dict[str, object],
) -> dict[str, object]:
    before_finish = before_cpm.completion_date
    after_finish = after_cpm.completion_date
    target = patch.target_finish_date
    return {
        "project_name": project.name,
        "target_finish_date": target.isoformat() if target else None,
        "before_finish_date": before_finish.isoformat() if before_finish else None,
        "after_finish_date": after_finish.isoformat() if after_finish else None,
        "delta_days_before": _delta_days(before_finish, target),
        "delta_days_after": _delta_days(after_finish, target),
        "critical_path_before": _critical_path(before_cpm),
        "critical_path_after": _critical_path(after_cpm),
        "dependency_count_before": len(before_relationships),
        "dependency_count_after": len(after_relationships),
        "relationship_coverage_before": before_diagnostics["relationship_coverage_ratio"],
        "relationship_coverage_after": after_diagnostics["relationship_coverage_ratio"],
        "cost_coverage_before": before_diagnostics["cost_coverage_ratio"],
        "cost_coverage_after": after_diagnostics["cost_coverage_ratio"],
        "duration_override_count": len(patch.duration_overrides or []),
        "lag_override_count": len([item for item in (patch.dependency_overrides or []) if item.lag_days != 0])
        + len(patch.lag_overrides or []),
        "imported_task_count": len(imported_activities),
        "calibrated_task_count": len(calibrated_activities),
        "missing_relationship_count_before": _missing_relationship_count(imported_activities, before_relationships),
        "missing_relationship_count_after": _missing_relationship_count(calibrated_activities, after_relationships),
        "missing_cost_count_before": sum(1 for activity in imported_activities if activity.cost == 0),
        "missing_cost_count_after": sum(1 for activity in calibrated_activities if activity.cost == 0),
        "cycles_detected_before": before_cpm.cycles_detected or [],
        "cycles_detected_after": after_cpm.cycles_detected or [],
        "field_uat_status": field_uat_status(after_diagnostics, warnings),
        "warnings": warnings,
    }


def _delta_days(finish: date | None, target: date | None) -> int | None:
    if finish is None or target is None:
        return None
    return (target - finish).days


def _critical_path(result: CpmResult) -> list[str]:
    return [activity.code for activity in result.activities if activity.is_critical]


def _missing_relationship_count(activities: list[Activity], relationships: list[Relationship]) -> int:
    if len(activities) <= 1:
        return 0
    return max(0, len(activities) - 1 - len(relationships))


def _schedule_dict(activities: list[Activity], relationships: list[Relationship]) -> dict[str, object]:
    return {
        "activity_count": len(activities),
        "relationship_count": len(relationships),
        "activities": [_activity_dict(activity) for activity in activities],
        "relationships": [asdict(relationship) for relationship in relationships],
    }


def _activity_dict(activity: Activity) -> dict[str, object]:
    data = asdict(activity)
    for key in ("es_date", "ef_date"):
        value = data[key]
        data[key] = value.isoformat() if isinstance(value, date) else value
    return data


def _cpm_dict(result: CpmResult) -> dict[str, object]:
    return {
        "total_duration_days": result.total_duration_days,
        "critical_count": result.critical_count,
        "completion_date": result.completion_date.isoformat() if result.completion_date else None,
        "critical_path": _critical_path(result),
        "cycles_detected": result.cycles_detected or [],
    }


def _patch_dict(patch: CalibrationPatch) -> dict[str, object]:
    data = asdict(patch)
    if patch.target_finish_date:
        data["target_finish_date"] = patch.target_finish_date.isoformat()
    return data


def _correction_record(
    *,
    task_id: str,
    field: str,
    old_value: object,
    new_value: object,
    reason: str | None,
    source: str,
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
        "source": source,
    }


def _with_applied_order(records: list[dict[str, object]]) -> list[dict[str, object]]:
    ordered_records: list[dict[str, object]] = []
    for applied_order, record in enumerate(records, start=1):
        ordered_record = dict(record)
        ordered_record["applied_order"] = applied_order
        ordered_records.append(ordered_record)
    return ordered_records
