from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date


ALLOWED_DISCIPLINES = frozenset({"위생", "공조", "소방", "전기", "자동제어", "공통"})
ALLOWED_REL_TYPES = frozenset({"FS", "SS", "FF"})


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


def with_timestamps(model, created_at: str | None = None, updated_at: str | None = None):
    return replace(
        model,
        created_at=created_at if created_at is not None else model.created_at,
        updated_at=updated_at if updated_at is not None else model.updated_at,
    )
