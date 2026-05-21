from __future__ import annotations

from core.progress import (
    calculate_milestone_progress,
    calculate_quantity_progress,
    calculate_weighted_progress,
    summarize_progress,
)


def test_quantity_progress_handles_zero_plan_and_overrun():
    assert calculate_quantity_progress(0, 10) == 0.0
    assert calculate_quantity_progress(100, 125) == 125.0


def test_weighted_progress_uses_amount_weights():
    items = [
        {"progress_pct": 50.0, "weight": 1000.0},
        {"progress_pct": 100.0, "weight": 3000.0},
    ]

    assert calculate_weighted_progress(items) == 87.5


def test_milestone_progress_maps_common_statuses():
    assert calculate_milestone_progress("not_started") == 0.0
    assert calculate_milestone_progress("in_progress") == 50.0
    assert calculate_milestone_progress("completed") == 100.0


def test_summarize_progress_groups_by_discipline_and_zone():
    rows = [
        {
            "activity_id": "a1",
            "discipline": "architecture",
            "zone": "1F",
            "planned_qty": 100,
            "actual_qty": 50,
            "weight": 100,
        },
        {
            "activity_id": "a2",
            "discipline": "architecture",
            "zone": "2F",
            "planned_qty": 100,
            "actual_qty": 100,
            "weight": 100,
        },
    ]

    summary = summarize_progress(rows)

    assert summary["overall_progress_pct"] == 75.0
    assert summary["by_discipline"]["architecture"]["progress_pct"] == 75.0
    assert summary["by_zone"]["1F"]["progress_pct"] == 50.0
