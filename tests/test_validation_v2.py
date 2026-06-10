from __future__ import annotations

from datetime import date

from core.validation import (
    validate_change_approval,
    validate_cost_progress_gap,
    validate_date_order,
    validate_owner_present,
    validate_progress_quantities,
)


def test_validate_date_order_message_contains_activity_values_and_cause():
    issues = validate_date_order("A100", "1F slab", date(2026, 5, 10), date(2026, 5, 9))

    assert len(issues) == 1
    assert "1F slab" in issues[0]
    assert "2026-05-10" in issues[0]
    assert "2026-05-09" in issues[0]
    assert "finish date is before start date" in issues[0]


def test_validate_progress_quantities_reports_zero_plan_and_over_100():
    issues = validate_progress_quantities("A200", "ceiling framing", 0, 5)
    issues.extend(validate_progress_quantities("A201", "wall paint", 100, 125))

    assert any("planned quantity is 0" in issue for issue in issues)
    assert any("125.0%" in issue for issue in issues)
    assert all("ceiling framing" in issues[0] or "wall paint" in issue for issue in issues[1:])


def test_validate_cost_owner_and_change_approval_messages_are_specific():
    cost_issues = validate_cost_progress_gap("A300", "duct install", progress_pct=40.0, cost_execution_rate=58.0)
    owner_issues = validate_owner_present("A301", "pipe install", discipline="mechanical", zone="B1", owner="")
    change_issues = validate_change_approval(
        "baseline_snapshots",
        "B-001",
        changed_at=date(2026, 5, 20),
        approved_by="",
    )

    assert "duct install" in cost_issues[0]
    assert "40.0" in cost_issues[0]
    assert "58.0" in cost_issues[0]
    assert "mechanical" in owner_issues[0]
    assert "B1" in owner_issues[0]
    assert "baseline_snapshots" in change_issues[0]
    assert "2026-05-20" in change_issues[0]
