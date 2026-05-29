from __future__ import annotations

from core.cost import (
    calculate_billing_rate,
    calculate_cost_execution_rate,
    detect_cost_overrun,
    forecast_completion_cost,
)


def test_cost_and_billing_rates_are_percentages():
    assert calculate_cost_execution_rate(1000, 250) == 25.0
    assert calculate_cost_execution_rate(0, 250) == 0.0
    assert calculate_billing_rate(2000, 500) == 25.0
    assert calculate_billing_rate(0, 500) == 0.0


def test_detect_cost_overrun_compares_cost_to_progress():
    assert detect_cost_overrun(progress_pct=40.0, cost_execution_rate=55.1)
    assert not detect_cost_overrun(progress_pct=40.0, cost_execution_rate=49.0)
    assert detect_cost_overrun(progress_pct=0.4, cost_execution_rate=0.56)


def test_forecast_completion_cost_uses_current_cost_trend():
    forecast = forecast_completion_cost(
        [
            {"execution_budget": 1000, "invested_cost": 600, "progress_pct": 50},
            {"execution_budget": 2000, "invested_cost": 800, "progress_pct": 100},
        ]
    )

    assert forecast["execution_budget_total"] == 3000.0
    assert forecast["invested_cost_total"] == 1400.0
    assert forecast["forecast_completion_cost"] == 2000.0
    assert forecast["forecast_over_budget"] is False
