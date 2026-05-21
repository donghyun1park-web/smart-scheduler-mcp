from __future__ import annotations

from typing import Any

from core.number_utils import safe_divide, to_float


def calculate_evm_snapshot(
    *,
    execution_budget: Any,
    planned_progress_pct: Any,
    actual_progress_pct: Any,
    actual_cost: Any,
) -> dict[str, float | str | None]:
    budget = to_float(execution_budget)
    planned_pct = _as_percent(to_float(planned_progress_pct))
    actual_pct = _as_percent(to_float(actual_progress_pct))
    ac = to_float(actual_cost)
    planned_value = round(budget * planned_pct / 100, 2)
    earned_value = round(budget * actual_pct / 100, 2)
    schedule_variance = round(earned_value - planned_value, 2)
    cost_variance = round(earned_value - ac, 2)
    spi = _ratio_or_none(earned_value, planned_value)
    cpi = _ratio_or_none(earned_value, ac)
    return {
        "planned_value": planned_value,
        "earned_value": earned_value,
        "actual_cost": round(ac, 2),
        "schedule_variance": schedule_variance,
        "cost_variance": cost_variance,
        "spi": spi,
        "cpi": cpi,
        "status": _status(spi, cpi),
    }


def calculate_evm_totals(rows: list[dict[str, Any]]) -> dict[str, float | str | None]:
    planned_value = 0.0
    earned_value = 0.0
    actual_cost = 0.0
    for row in rows:
        snapshot = calculate_evm_snapshot(
            execution_budget=row.get("execution_budget"),
            planned_progress_pct=row.get("planned_progress_pct"),
            actual_progress_pct=row.get("actual_progress_pct"),
            actual_cost=row.get("invested_cost", row.get("actual_cost")),
        )
        planned_value += to_float(snapshot["planned_value"])
        earned_value += to_float(snapshot["earned_value"])
        actual_cost += to_float(snapshot["actual_cost"])
    spi = _ratio_or_none(earned_value, planned_value)
    cpi = _ratio_or_none(earned_value, actual_cost)
    return {
        "planned_value": round(planned_value, 2),
        "earned_value": round(earned_value, 2),
        "actual_cost": round(actual_cost, 2),
        "schedule_variance": round(earned_value - planned_value, 2),
        "cost_variance": round(earned_value - actual_cost, 2),
        "spi": spi,
        "cpi": cpi,
        "status": _status(spi, cpi),
    }


def _ratio_or_none(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(safe_divide(numerator, denominator), 2)


def _as_percent(value: float) -> float:
    return value * 100 if 0 <= value <= 1 else value


def _status(spi: float | None, cpi: float | None) -> str:
    if spi is None and cpi is None:
        return "not_available"
    values = [value for value in (spi, cpi) if value is not None]
    if any(value < 0.9 for value in values):
        return "risk"
    if any(value < 1.0 for value in values):
        return "watch"
    return "healthy"
