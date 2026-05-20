from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, replace
from datetime import date
from pathlib import Path

from core import db
from core.calendar_utils import KoreanCalendar, map_activity_dates
from core.cpm import run_cpm
from core.models import Activity, Calendar, CpmResult, Project, Relationship


RELATIONSHIP_COVERAGE_THRESHOLD = 0.5
COST_COVERAGE_THRESHOLD = 0.5
MAX_ABS_LAG_DAYS = 3650


@dataclass(frozen=True)
class DependencyOverride:
    predecessor_id: str
    successor_id: str
    dependency_type: str = "FS"
    lag_days: int = 0
    reason: str | None = None
    source: str = "user_calibration"


@dataclass(frozen=True)
class DurationOverride:
    task_id: str
    duration_days: int
    reason: str | None = None
    source: str = "user_calibration"


@dataclass(frozen=True)
class LagOverride:
    predecessor_id: str
    successor_id: str
    lag_days: int
    reason: str | None = None
    source: str = "user_calibration"


@dataclass(frozen=True)
class CalibrationPatch:
    project_id: str | None = None
    target_finish_date: date | None = None
    dependency_overrides: list[DependencyOverride] | None = None
    duration_overrides: list[DurationOverride] | None = None
    lag_overrides: list[LagOverride] | None = None
    notes: str | None = None


def calibrate_project_completion(project_path: str | Path, patch: CalibrationPatch) -> dict[str, object]:
    activities = db.list_activities(project_path)
    relationships = db.list_relationships(project_path)
    summary = db.load_project_summary(project_path)
    project = summary["project"]
    if not isinstance(project, Project):
        return {"ok": False, "warnings": [_warning("error", "PROJECT_NOT_FOUND", "Project not found")], "comparison": {}}
    calendar_model = db.get_calendar(project_path, project.calendar_id)
    if calendar_model is None:
        return {
            "ok": False,
            "warnings": [_warning("error", "PROJECT_CALENDAR_NOT_FOUND", "Project calendar not found")],
            "comparison": {},
        }

    before_cpm = _run_cpm_with_dates(activities, relationships, project, calendar_model)
    before_diagnostics = _schedule_diagnostics(activities, relationships, before_cpm)
    warnings = _diagnostic_warnings(before_diagnostics, "before")
    warnings.extend(_validate_patch(activities, relationships, patch))
    if _has_error(warnings):
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
    after_diagnostics = _schedule_diagnostics(calibrated_activities, calibrated_relationships, after_cpm)
    if after_cpm.cycles_detected:
        warnings.append(
            _warning(
                "error",
                "DEPENDENCY_CYCLE",
                f"Calibration creates dependency cycle: {after_cpm.cycles_detected}",
            )
        )
    warnings.extend(_diagnostic_warnings(after_diagnostics, "after"))

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


def _validate_patch(
    activities: list[Activity],
    relationships: list[Relationship],
    patch: CalibrationPatch,
) -> list[dict[str, object]]:
    activity_ids = {activity.activity_id for activity in activities}
    relationship_keys = {(rel.pred_id, rel.succ_id): rel for rel in relationships}
    warnings: list[dict[str, object]] = []
    dependency_seen: dict[tuple[str, str], int] = {}
    duration_seen: dict[str, int] = {}
    lag_seen: dict[tuple[str, str], int] = {}
    for applied_order, dependency_override in enumerate(patch.dependency_overrides or [], start=1):
        key = (dependency_override.predecessor_id, dependency_override.successor_id)
        if dependency_override.predecessor_id not in activity_ids:
            warnings.append(
                _warning(
                    "error",
                    "UNKNOWN_TASK_ID",
                    f"Unknown predecessor_id: {dependency_override.predecessor_id}",
                    task_id=dependency_override.predecessor_id,
                    applied_order=applied_order,
                )
            )
        if dependency_override.successor_id not in activity_ids:
            warnings.append(
                _warning(
                    "error",
                    "UNKNOWN_TASK_ID",
                    f"Unknown successor_id: {dependency_override.successor_id}",
                    task_id=dependency_override.successor_id,
                    applied_order=applied_order,
                )
            )
        if key in dependency_seen:
            warnings.append(
                _warning(
                    "error",
                    "DUPLICATE_DEPENDENCY_OVERRIDE",
                    f"Duplicate dependency override: {key[0]}->{key[1]}",
                    task_id=dependency_override.successor_id,
                    applied_order=applied_order,
                )
            )
        dependency_seen[key] = applied_order
        if dependency_override.dependency_type not in {"FS", "SS", "FF"}:
            warnings.append(
                _warning(
                    "error",
                    "UNSUPPORTED_DEPENDENCY_TYPE",
                    f"Unsupported dependency_type for v0.1: {dependency_override.dependency_type}",
                    task_id=dependency_override.successor_id,
                    applied_order=applied_order,
                )
            )
        if abs(dependency_override.lag_days) > MAX_ABS_LAG_DAYS:
            warnings.append(
                _warning(
                    "error",
                    "INVALID_LAG",
                    f"Invalid lag_days for {key[0]}->{key[1]}: {dependency_override.lag_days}",
                    task_id=dependency_override.successor_id,
                    applied_order=applied_order,
                )
            )
    for applied_order, duration_override in enumerate(patch.duration_overrides or [], start=1):
        if duration_override.task_id not in activity_ids:
            warnings.append(
                _warning(
                    "error",
                    "UNKNOWN_TASK_ID",
                    f"Unknown task_id: {duration_override.task_id}",
                    task_id=duration_override.task_id,
                    applied_order=applied_order,
                )
            )
        if duration_override.task_id in duration_seen:
            warnings.append(
                _warning(
                    "error",
                    "CONFLICTING_DURATION_OVERRIDE",
                    f"Multiple duration overrides for task_id: {duration_override.task_id}",
                    task_id=duration_override.task_id,
                    applied_order=applied_order,
                )
            )
        duration_seen[duration_override.task_id] = applied_order
        if duration_override.duration_days <= 0:
            warnings.append(
                _warning(
                    "error",
                    "INVALID_DURATION",
                    f"Invalid duration_days for {duration_override.task_id}: {duration_override.duration_days}",
                    task_id=duration_override.task_id,
                    applied_order=applied_order,
                )
            )
    for applied_order, lag_override in enumerate(patch.lag_overrides or [], start=1):
        key = (lag_override.predecessor_id, lag_override.successor_id)
        if lag_override.predecessor_id not in activity_ids:
            warnings.append(
                _warning(
                    "error",
                    "UNKNOWN_TASK_ID",
                    f"Unknown predecessor_id: {lag_override.predecessor_id}",
                    task_id=lag_override.predecessor_id,
                    applied_order=applied_order,
                )
            )
        if lag_override.successor_id not in activity_ids:
            warnings.append(
                _warning(
                    "error",
                    "UNKNOWN_TASK_ID",
                    f"Unknown successor_id: {lag_override.successor_id}",
                    task_id=lag_override.successor_id,
                    applied_order=applied_order,
                )
            )
        if key in lag_seen:
            warnings.append(
                _warning(
                    "error",
                    "CONFLICTING_LAG_OVERRIDE",
                    f"Multiple lag overrides for relationship: {key[0]}->{key[1]}",
                    task_id=lag_override.successor_id,
                    applied_order=applied_order,
                )
            )
        lag_seen[key] = applied_order
        if key not in relationship_keys:
            warnings.append(
                _warning(
                    "error",
                    "UNKNOWN_RELATIONSHIP",
                    f"Unknown relationship for lag override: {key[0]}->{key[1]}",
                    task_id=lag_override.successor_id,
                    applied_order=applied_order,
                )
            )
        if key in dependency_seen:
            warnings.append(
                _warning(
                    "warning",
                    "CONFLICTING_LAG_OVERRIDE",
                    f"Lag override duplicates dependency override lag field for relationship: {key[0]}->{key[1]}",
                    task_id=lag_override.successor_id,
                    applied_order=applied_order,
                )
            )
        if abs(lag_override.lag_days) > MAX_ABS_LAG_DAYS:
            warnings.append(
                _warning(
                    "error",
                    "INVALID_LAG",
                    f"Invalid lag_days for {key[0]}->{key[1]}: {lag_override.lag_days}",
                    task_id=lag_override.successor_id,
                    applied_order=applied_order,
                )
            )
    return warnings


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
        "field_uat_status": _field_uat_status(after_diagnostics, warnings),
        "warnings": warnings,
    }


def _schedule_diagnostics(
    activities: list[Activity],
    relationships: list[Relationship],
    cpm_result: CpmResult,
) -> dict[str, object]:
    task_count = len(activities)
    dependency_count = len(relationships)
    predecessor_ids = {relationship.succ_id for relationship in relationships}
    successor_ids = {relationship.pred_id for relationship in relationships}
    ids = [activity.activity_id for activity in activities]
    duplicate_count = len(ids) - len(set(ids))
    missing_cost_count = sum(1 for activity in activities if activity.cost == 0)
    zero_or_negative_duration_count = sum(1 for activity in activities if activity.duration <= 0)
    isolated_task_count = sum(
        1
        for activity in activities
        if activity.activity_id not in predecessor_ids and activity.activity_id not in successor_ids
    )
    return {
        "task_count": task_count,
        "dependency_count": dependency_count,
        "tasks_without_predecessor_count": sum(1 for activity in activities if activity.activity_id not in predecessor_ids),
        "tasks_without_successor_count": sum(1 for activity in activities if activity.activity_id not in successor_ids),
        "isolated_task_count": isolated_task_count,
        "missing_duration_count": 0,
        "zero_or_negative_duration_count": zero_or_negative_duration_count,
        "missing_cost_count": missing_cost_count,
        "duplicate_task_id_count": duplicate_count,
        "cycle_detected": bool(cpm_result.cycles_detected),
        "disconnected_component_count": _disconnected_component_count(activities, relationships),
        "relationship_coverage_ratio": _ratio(dependency_count, task_count),
        "cost_coverage_ratio": _ratio(task_count - missing_cost_count, task_count),
        "warnings": [],
    }


def _diagnostic_warnings(diagnostics: dict[str, object], phase: str) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    relationship_coverage = _float_diagnostic(diagnostics, "relationship_coverage_ratio")
    cost_coverage = _float_diagnostic(diagnostics, "cost_coverage_ratio")
    if relationship_coverage < RELATIONSHIP_COVERAGE_THRESHOLD:
        warnings.append(
            _warning(
                "warning",
                "LOW_RELATIONSHIP_COVERAGE",
                "Relationship coverage is below recommended threshold.",
                phase=phase,
            )
        )
    if cost_coverage < COST_COVERAGE_THRESHOLD:
        warnings.append(
            _warning(
                "warning",
                "LOW_COST_COVERAGE",
                "Cost coverage is below recommended threshold.",
                phase=phase,
            )
        )
    if diagnostics["zero_or_negative_duration_count"]:
        warnings.append(
            _warning(
                "warning",
                "INVALID_DURATION",
                "Schedule contains zero or negative duration activities.",
                phase=phase,
            )
        )
    if diagnostics["duplicate_task_id_count"]:
        warnings.append(
            _warning(
                "error",
                "DUPLICATE_TASK_ID",
                "Schedule contains duplicate task IDs.",
                phase=phase,
            )
        )
    if diagnostics["cycle_detected"]:
        warnings.append(
            _warning(
                "error",
                "DEPENDENCY_CYCLE",
                "Schedule contains a dependency cycle.",
                phase=phase,
            )
        )
    return warnings


def _field_uat_status(after_diagnostics: dict[str, object], warnings: list[dict[str, object]]) -> str:
    if after_diagnostics["cycle_detected"] or any(warning["code"] == "DEPENDENCY_CYCLE" for warning in warnings):
        return "blocked_by_cycle"
    if _has_error(warnings):
        return "blocked_by_invalid_patch"
    if _float_diagnostic(after_diagnostics, "relationship_coverage_ratio") < RELATIONSHIP_COVERAGE_THRESHOLD:
        return "needs_relationship_correction"
    if _float_diagnostic(after_diagnostics, "cost_coverage_ratio") < COST_COVERAGE_THRESHOLD:
        return "needs_cost_correction"
    return "ready_for_review"


def _warning(
    severity: str,
    code: str,
    message: str,
    *,
    task_id: str | None = None,
    applied_order: int | None = None,
    phase: str | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if task_id is not None:
        record["task_id"] = task_id
    if applied_order is not None:
        record["applied_order"] = applied_order
    if phase is not None:
        record["phase"] = phase
    return record


def _has_error(warnings: list[dict[str, object]]) -> bool:
    return any(warning["severity"] == "error" for warning in warnings)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 4)


def _float_diagnostic(diagnostics: dict[str, object], key: str) -> float:
    value = diagnostics[key]
    if isinstance(value, int | float):
        return float(value)
    return float(str(value))


def _disconnected_component_count(activities: list[Activity], relationships: list[Relationship]) -> int:
    activity_ids = {activity.activity_id for activity in activities}
    if not activity_ids:
        return 0
    adjacency = {activity_id: set[str]() for activity_id in activity_ids}
    for relationship in relationships:
        if relationship.pred_id in adjacency and relationship.succ_id in adjacency:
            adjacency[relationship.pred_id].add(relationship.succ_id)
            adjacency[relationship.succ_id].add(relationship.pred_id)
    seen: set[str] = set()
    count = 0
    for activity_id in activity_ids:
        if activity_id in seen:
            continue
        count += 1
        stack = [activity_id]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(adjacency[current] - seen)
    return count


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
