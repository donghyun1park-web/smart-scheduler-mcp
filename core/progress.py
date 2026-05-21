from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

from core.number_utils import to_float


MILESTONE_PROGRESS = {
    "not_started": 0.0,
    "planned": 0.0,
    "ready": 0.0,
    "in_progress": 50.0,
    "started": 50.0,
    "completed": 100.0,
    "complete": 100.0,
    "done": 100.0,
}


def calculate_quantity_progress(planned_qty: float, actual_qty: float) -> float:
    """Return quantity progress as a percentage."""
    if planned_qty <= 0:
        return 0.0
    return round((actual_qty / planned_qty) * 100, 2)


def calculate_weighted_progress(items: Iterable[Mapping[str, Any]]) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for item in items:
        weight = to_float(item.get("weight", item.get("amount", 0.0)))
        progress_pct = to_float(item.get("progress_pct", 0.0))
        if weight <= 0:
            continue
        weighted_sum += progress_pct * weight
        total_weight += weight
    if total_weight <= 0:
        return 0.0
    return round(weighted_sum / total_weight, 2)


def calculate_milestone_progress(status: str) -> float:
    return MILESTONE_PROGRESS.get(status.strip().lower(), 0.0)


def summarize_progress(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    prepared: list[dict[str, Any]] = []
    for row in rows:
        progress_pct = calculate_quantity_progress(
            to_float(row.get("planned_qty")),
            to_float(row.get("actual_qty")),
        )
        prepared.append({**dict(row), "progress_pct": progress_pct})

    return {
        "overall_progress_pct": calculate_weighted_progress(prepared),
        "by_discipline": _group_progress(prepared, "discipline"),
        "by_zone": _group_progress(prepared, "zone"),
    }


def _group_progress(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key) or "")].append(row)
    return {
        name: {
            "progress_pct": calculate_weighted_progress(items),
            "weight": sum(to_float(item.get("weight", item.get("amount", 0.0))) for item in items),
        }
        for name, items in grouped.items()
    }
