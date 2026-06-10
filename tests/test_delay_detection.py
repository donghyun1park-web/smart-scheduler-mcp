from __future__ import annotations

from datetime import date

from core.delay_detection import (
    detect_inspection_delays,
    detect_manpower_shortage,
    detect_material_delays,
    detect_overdue_activity,
    detect_predecessor_blocks,
    detect_schedule_delay,
    generate_delay_report,
)


def test_detect_schedule_delay_includes_activity_values_and_cause():
    issues = detect_schedule_delay(
        {
            "activity_id": "A100",
            "name": "1F slab formwork",
            "planned_progress_pct": 70.0,
            "actual_progress_pct": 55.0,
            "owner": "Kim",
        }
    )

    assert issues[0]["reason_code"] == "schedule_progress_delay"
    assert "1F slab formwork" in issues[0]["message"]
    assert "70.0" in issues[0]["message"]
    assert "55.0" in issues[0]["message"]


def test_detect_overdue_and_predecessor_blocks():
    overdue = detect_overdue_activity(
        {"activity_id": "A200", "name": "rebar inspection", "finish_date": date(2026, 5, 1), "status": "in_progress"},
        today=date(2026, 5, 5),
    )
    blocked = detect_predecessor_blocks(
        {
            "activity_id": "A210",
            "name": "concrete pour",
            "predecessors": [{"activity_id": "A200", "name": "rebar inspection", "status": "in_progress"}],
        }
    )

    assert overdue[0]["delay_days"] == 4
    assert blocked[0]["reason_code"] == "predecessor_incomplete"
    assert "rebar inspection" in blocked[0]["message"]


def test_detect_material_inspection_and_manpower_delays():
    activity = {
        "activity_id": "A300",
        "name": "ceiling framing",
        "planned_workers": 8,
        "actual_workers": 5,
        "materials": [
            {"material_name": "stud runner", "expected_date": date(2026, 5, 3), "actual_date": None, "status": "ordered"}
        ],
        "inspections": [
            {"inspection_type": "anchor approval", "planned_date": date(2026, 5, 2), "actual_date": None, "status": "pending"}
        ],
    }

    material = detect_material_delays(activity, today=date(2026, 5, 5))
    inspection = detect_inspection_delays(activity, today=date(2026, 5, 5))
    manpower = detect_manpower_shortage(activity)

    assert material[0]["reason_code"] == "material_delay"
    assert inspection[0]["reason_code"] == "inspection_delay"
    assert manpower[0]["reason_code"] == "manpower_shortage"


def test_generate_delay_report_sorts_top_risks():
    report = generate_delay_report(
        [
            {
                "activity_id": "A1",
                "name": "normal",
                "planned_progress_pct": 50,
                "actual_progress_pct": 50,
                "finish_date": date(2026, 5, 10),
            },
            {
                "activity_id": "A2",
                "name": "late material",
                "planned_progress_pct": 80,
                "actual_progress_pct": 50,
                "finish_date": date(2026, 5, 1),
                "materials": [{"material_name": "pump", "expected_date": date(2026, 5, 1), "status": "ordered"}],
            },
        ],
        today=date(2026, 5, 5),
        top_n=1,
    )

    assert len(report) == 1
    assert report[0]["activity_id"] == "A2"
    assert report[0]["risk_score"] > 0
