from __future__ import annotations

from typing import Any, Iterable, Mapping


def calculate_cost_execution_rate(execution_budget: float, invested_cost: float) -> float:
    """Return cost execution rate as a percentage."""
    if execution_budget <= 0:
        return 0.0
    return round((invested_cost / execution_budget) * 100, 2)


def calculate_billing_rate(contract_amount: float, billing_amount: float) -> float:
    """Return billing rate as a percentage."""
    if contract_amount <= 0:
        return 0.0
    return round((billing_amount / contract_amount) * 100, 2)


def detect_cost_overrun(
    progress_pct: float,
    cost_execution_rate: float,
    threshold: float = 10.0,
) -> bool:
    """Return true when cost rate is materially ahead of progress."""
    progress = _as_percent(progress_pct)
    cost_rate = _as_percent(cost_execution_rate)
    threshold_pct = threshold * 100 if 0 < threshold <= 1 else threshold
    return (cost_rate - progress) > threshold_pct


def forecast_completion_cost(items: Iterable[Mapping[str, Any]]) -> dict[str, float | bool]:
    execution_budget_total = 0.0
    invested_cost_total = 0.0
    forecast_total = 0.0
    for item in items:
        budget = _float_value(item.get("execution_budget"))
        invested = _float_value(item.get("invested_cost"))
        progress_pct = _as_percent(_float_value(item.get("progress_pct")))
        execution_budget_total += budget
        invested_cost_total += invested
        if progress_pct > 0:
            forecast_total += invested / (progress_pct / 100)
        else:
            forecast_total += budget
    forecast_total = round(forecast_total, 2)
    return {
        "execution_budget_total": round(execution_budget_total, 2),
        "invested_cost_total": round(invested_cost_total, 2),
        "forecast_completion_cost": forecast_total,
        "forecast_over_budget": forecast_total > execution_budget_total,
    }


def _as_percent(value: float) -> float:
    return value * 100 if 0 <= value <= 1 else value


def _float_value(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)
