from __future__ import annotations

from core.evm import calculate_evm_snapshot


def test_calculate_evm_snapshot_returns_core_indices():
    snapshot = calculate_evm_snapshot(
        execution_budget=1000,
        planned_progress_pct=60,
        actual_progress_pct=50,
        actual_cost=700,
    )

    assert snapshot["planned_value"] == 600.0
    assert snapshot["earned_value"] == 500.0
    assert snapshot["actual_cost"] == 700.0
    assert snapshot["schedule_variance"] == -100.0
    assert snapshot["cost_variance"] == -200.0
    assert snapshot["spi"] == 0.83
    assert snapshot["cpi"] == 0.71
    assert snapshot["status"] == "risk"


def test_calculate_evm_snapshot_handles_zero_denominators():
    snapshot = calculate_evm_snapshot(
        execution_budget=0,
        planned_progress_pct=0,
        actual_progress_pct=0,
        actual_cost=0,
    )

    assert snapshot["spi"] is None
    assert snapshot["cpi"] is None
    assert snapshot["status"] == "not_available"
