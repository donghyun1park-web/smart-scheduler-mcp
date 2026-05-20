"""Data classes and thresholds shared by calibration modules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


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
