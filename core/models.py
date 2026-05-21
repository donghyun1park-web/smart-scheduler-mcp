from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Any, Literal


ALLOWED_DISCIPLINES = frozenset({"위생", "공조", "소방", "전기", "자동제어", "공통"})
ALLOWED_REL_TYPES = frozenset({"FS", "SS", "FF"})
RelType = Literal["FS", "SS", "FF"]
Discipline = Literal["위생", "공조", "소방", "전기", "자동제어", "공통"]


@dataclass(frozen=True)
class Project:
    project_id: str
    name: str
    start_date: date
    calendar_id: str
    description: str = ""
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class WBS:
    wbs_id: str
    parent_id: str | None
    code: str
    name: str
    sort_order: int = 0
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class Activity:
    activity_id: str
    code: str
    name: str
    wbs_id: str
    discipline: str
    zone: str
    duration: int
    cost: float = 0.0
    es_workday: int | None = None
    ef_workday: int | None = None
    ls_workday: int | None = None
    lf_workday: int | None = None
    es_date: date | None = None
    ef_date: date | None = None
    total_float: int | None = None
    is_critical: bool = False
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        if self.discipline not in ALLOWED_DISCIPLINES:
            raise ValueError(f"Unsupported discipline for v0.1: {self.discipline}")
        if self.duration < 0:
            raise ValueError("Activity duration cannot be negative")


@dataclass(frozen=True)
class ActivityCpmResult:
    activity_id: str
    code: str
    es_workday: int
    ef_workday: int
    ls_workday: int
    lf_workday: int
    total_float: int
    is_critical: bool
    es_date: date | None = None
    ef_date: date | None = None
    ls_date: date | None = None
    lf_date: date | None = None


@dataclass(frozen=True)
class CpmResult:
    activities: list[ActivityCpmResult]
    total_duration_days: int
    critical_count: int
    completion_date: date | None = None
    cycles_detected: list[list[str]] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "activities": [activity.__dict__ for activity in self.activities],
            "total_duration_days": self.total_duration_days,
            "critical_count": self.critical_count,
            "completion_date": self.completion_date.isoformat()
            if self.completion_date
            else None,
            "cycles_detected": self.cycles_detected or [],
        }


@dataclass(frozen=True)
class Relationship:
    rel_id: str
    pred_id: str
    succ_id: str
    rel_type: str
    lag_days: int = 0
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        if self.rel_type not in ALLOWED_REL_TYPES:
            raise ValueError(f"Unsupported relationship type for v0.1: {self.rel_type}")


@dataclass(frozen=True)
class Calendar:
    calendar_id: str
    name: str
    weekmask: str
    holidays: tuple[str, ...] = ()
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        if len(self.weekmask) != 7 or any(char not in {"0", "1"} for char in self.weekmask):
            raise ValueError("Calendar weekmask must be a 7-character 0/1 string")


@dataclass(frozen=True)
class DailyRecord:
    record_id: str
    activity_id: str
    work_date: date
    planned_qty: float = 0.0
    actual_qty: float = 0.0
    workers: int = 0
    equipment: str = ""
    owner: str = ""
    remarks: str = ""
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class CostItem:
    cost_item_id: str
    activity_id: str
    contract_amount: float = 0.0
    execution_budget: float = 0.0
    invested_cost: float = 0.0
    billing_amount: float = 0.0
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class BaselineSnapshot:
    snapshot_id: str
    baseline_id: str
    activity_id: str
    start_date: date | None
    finish_date: date | None
    duration: int
    revision: str
    approved_by: str = ""
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class MaterialRecord:
    material_id: str
    activity_id: str
    material_name: str
    order_date: date | None = None
    expected_date: date | None = None
    actual_date: date | None = None
    status: str = "planned"
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class InspectionRecord:
    inspection_id: str
    activity_id: str
    inspection_type: str
    planned_date: date | None = None
    actual_date: date | None = None
    status: str = "planned"
    approver: str = ""
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class ChangeLogEntry:
    change_id: str
    target_table: str
    target_id: str
    before_value: str
    after_value: str
    reason: str
    user: str
    approved_by: str = ""
    changed_at: date | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class ProjectSettings:
    settings_id: str
    project_id: str
    disciplines: tuple[str, ...] = ()
    thresholds: dict[str, Any] | None = None
    report_style: str = "weekly_meeting"
    created_at: str | None = None
    updated_at: str | None = None


def with_timestamps(model, created_at: str | None = None, updated_at: str | None = None):
    return replace(
        model,
        created_at=created_at if created_at is not None else model.created_at,
        updated_at=updated_at if updated_at is not None else model.updated_at,
    )
