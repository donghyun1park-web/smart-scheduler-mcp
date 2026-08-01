"""Schedule diagnostics, patch validation, and warning helpers."""

from __future__ import annotations

from core.calibration_models import (
    COST_COVERAGE_THRESHOLD,
    MAX_ABS_LAG_DAYS,
    RELATIONSHIP_COVERAGE_THRESHOLD,
    CalibrationPatch,
)
from core.models import Activity, CpmResult, Relationship


def make_warning(
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


def has_error(warnings: list[dict[str, object]]) -> bool:
    return any(warning["severity"] == "error" for warning in warnings)


def validate_patch(
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
                make_warning(
                    "error",
                    "UNKNOWN_TASK_ID",
                    f"Unknown predecessor_id: {dependency_override.predecessor_id}",
                    task_id=dependency_override.predecessor_id,
                    applied_order=applied_order,
                )
            )
        if dependency_override.successor_id not in activity_ids:
            warnings.append(
                make_warning(
                    "error",
                    "UNKNOWN_TASK_ID",
                    f"Unknown successor_id: {dependency_override.successor_id}",
                    task_id=dependency_override.successor_id,
                    applied_order=applied_order,
                )
            )
        if key in dependency_seen:
            warnings.append(
                make_warning(
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
                make_warning(
                    "error",
                    "UNSUPPORTED_DEPENDENCY_TYPE",
                    f"Unsupported dependency_type for v0.1: {dependency_override.dependency_type}",
                    task_id=dependency_override.successor_id,
                    applied_order=applied_order,
                )
            )
        if abs(dependency_override.lag_days) > MAX_ABS_LAG_DAYS:
            warnings.append(
                make_warning(
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
                make_warning(
                    "error",
                    "UNKNOWN_TASK_ID",
                    f"Unknown task_id: {duration_override.task_id}",
                    task_id=duration_override.task_id,
                    applied_order=applied_order,
                )
            )
        if duration_override.task_id in duration_seen:
            warnings.append(
                make_warning(
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
                make_warning(
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
                make_warning(
                    "error",
                    "UNKNOWN_TASK_ID",
                    f"Unknown predecessor_id: {lag_override.predecessor_id}",
                    task_id=lag_override.predecessor_id,
                    applied_order=applied_order,
                )
            )
        if lag_override.successor_id not in activity_ids:
            warnings.append(
                make_warning(
                    "error",
                    "UNKNOWN_TASK_ID",
                    f"Unknown successor_id: {lag_override.successor_id}",
                    task_id=lag_override.successor_id,
                    applied_order=applied_order,
                )
            )
        if key in lag_seen:
            warnings.append(
                make_warning(
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
                make_warning(
                    "error",
                    "UNKNOWN_RELATIONSHIP",
                    f"Unknown relationship for lag override: {key[0]}->{key[1]}",
                    task_id=lag_override.successor_id,
                    applied_order=applied_order,
                )
            )
        if key in dependency_seen:
            warnings.append(
                make_warning(
                    "warning",
                    "CONFLICTING_LAG_OVERRIDE",
                    f"Lag override duplicates dependency override lag field for relationship: {key[0]}->{key[1]}",
                    task_id=lag_override.successor_id,
                    applied_order=applied_order,
                )
            )
        if abs(lag_override.lag_days) > MAX_ABS_LAG_DAYS:
            warnings.append(
                make_warning(
                    "error",
                    "INVALID_LAG",
                    f"Invalid lag_days for {key[0]}->{key[1]}: {lag_override.lag_days}",
                    task_id=lag_override.successor_id,
                    applied_order=applied_order,
                )
            )
    return warnings


def schedule_diagnostics(
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


def diagnostic_warnings(diagnostics: dict[str, object], phase: str) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    relationship_coverage = float_diagnostic(diagnostics, "relationship_coverage_ratio")
    cost_coverage = float_diagnostic(diagnostics, "cost_coverage_ratio")
    if relationship_coverage < RELATIONSHIP_COVERAGE_THRESHOLD:
        warnings.append(
            make_warning(
                "warning",
                "LOW_RELATIONSHIP_COVERAGE",
                "Relationship coverage is below recommended threshold.",
                phase=phase,
            )
        )
    if cost_coverage < COST_COVERAGE_THRESHOLD:
        warnings.append(
            make_warning(
                "warning",
                "LOW_COST_COVERAGE",
                "Cost coverage is below recommended threshold.",
                phase=phase,
            )
        )
    if diagnostics["zero_or_negative_duration_count"]:
        warnings.append(
            make_warning(
                "warning",
                "INVALID_DURATION",
                "Schedule contains zero or negative duration activities.",
                phase=phase,
            )
        )
    if diagnostics["duplicate_task_id_count"]:
        warnings.append(
            make_warning(
                "error",
                "DUPLICATE_TASK_ID",
                "Schedule contains duplicate task IDs.",
                phase=phase,
            )
        )
    if diagnostics["cycle_detected"]:
        warnings.append(
            make_warning(
                "error",
                "DEPENDENCY_CYCLE",
                "Schedule contains a dependency cycle.",
                phase=phase,
            )
        )
    return warnings


def field_uat_status(after_diagnostics: dict[str, object], warnings: list[dict[str, object]]) -> str:
    if after_diagnostics["cycle_detected"] or any(warning["code"] == "DEPENDENCY_CYCLE" for warning in warnings):
        return "blocked_by_cycle"
    if has_error(warnings):
        return "blocked_by_invalid_patch"
    if float_diagnostic(after_diagnostics, "relationship_coverage_ratio") < RELATIONSHIP_COVERAGE_THRESHOLD:
        return "needs_relationship_correction"
    if float_diagnostic(after_diagnostics, "cost_coverage_ratio") < COST_COVERAGE_THRESHOLD:
        return "needs_cost_correction"
    return "ready_for_review"


def float_diagnostic(diagnostics: dict[str, object], key: str) -> float:
    value = diagnostics[key]
    if isinstance(value, int | float):
        return float(value)
    return float(str(value))


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 4)


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
