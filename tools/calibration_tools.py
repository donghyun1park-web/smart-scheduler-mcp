from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from core.calibration import (
    CalibrationPatch,
    DependencyOverride,
    DurationOverride,
    LagOverride,
    calibrate_project_completion,
)


def calibrate_completion_date(
    project_path: str | Path,
    target_finish_date: str | None = None,
    dependency_overrides: list[dict[str, object]] | None = None,
    duration_overrides: list[dict[str, object]] | None = None,
    lag_overrides: list[dict[str, object]] | None = None,
    notes: str | None = None,
) -> dict[str, object]:
    patch = CalibrationPatch(
        target_finish_date=date.fromisoformat(target_finish_date) if target_finish_date else None,
        dependency_overrides=[
            _dependency_override(item) for item in dependency_overrides or []
        ],
        duration_overrides=[
            _duration_override(item) for item in duration_overrides or []
        ],
        lag_overrides=[
            _lag_override(item) for item in lag_overrides or []
        ],
        notes=notes,
    )
    return calibrate_project_completion(project_path, patch)


def _dependency_override(item: dict[str, object]) -> DependencyOverride:
    return DependencyOverride(
        predecessor_id=str(item["predecessor_id"]),
        successor_id=str(item["successor_id"]),
        dependency_type=str(item.get("dependency_type") or "FS"),
        lag_days=_int_value(item.get("lag_days") or 0),
        reason=_optional_str(item.get("reason")),
        source=str(item.get("source") or "user_calibration"),
    )


def _duration_override(item: dict[str, object]) -> DurationOverride:
    return DurationOverride(
        task_id=str(item["task_id"]),
        duration_days=_int_value(item["duration_days"]),
        reason=_optional_str(item.get("reason")),
        source=str(item.get("source") or "user_calibration"),
    )


def _lag_override(item: dict[str, object]) -> LagOverride:
    return LagOverride(
        predecessor_id=str(item["predecessor_id"]),
        successor_id=str(item["successor_id"]),
        lag_days=_int_value(item["lag_days"]),
        reason=_optional_str(item.get("reason")),
        source=str(item.get("source") or "user_calibration"),
    )


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(value)
    return int(str(value))
