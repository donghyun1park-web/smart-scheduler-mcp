from __future__ import annotations

from datetime import date

from core import db
from core.calibration import (
    CalibrationPatch,
    DependencyOverride,
    DurationOverride,
    calibrate_project_completion,
)
from core.models import Activity, Calendar, Project, Relationship, WBS
from tools.calibration_tools import calibrate_completion_date


def test_schedule_diagnostics_reports_relationship_and_cost_coverage(tmp_path):
    project_path = _diagnostic_project(tmp_path)

    result = calibrate_project_completion(project_path, CalibrationPatch())

    before = result["diagnostics"]["before"]
    assert before["task_count"] == 4
    assert before["dependency_count"] == 1
    assert before["relationship_coverage_ratio"] == 0.25
    assert before["cost_coverage_ratio"] == 0.25
    assert before["tasks_without_predecessor_count"] == 3
    assert before["tasks_without_successor_count"] == 3
    assert before["isolated_task_count"] == 2
    assert before["missing_cost_count"] == 3
    assert before["cycle_detected"] is False


def test_low_relationship_and_cost_coverage_add_warnings(tmp_path):
    project_path = _diagnostic_project(tmp_path)

    result = calibrate_project_completion(project_path, CalibrationPatch())

    warning_codes = {warning["code"] for warning in result["warnings"]}
    assert "LOW_RELATIONSHIP_COVERAGE" in warning_codes
    assert "LOW_COST_COVERAGE" in warning_codes
    assert result["comparison"]["relationship_coverage_before"] == 0.25
    assert result["comparison"]["cost_coverage_before"] == 0.25
    assert result["comparison"]["field_uat_status"] == "needs_relationship_correction"


def test_duplicate_dependency_override_is_reported(tmp_path):
    project_path = _diagnostic_project(tmp_path)

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(
            dependency_overrides=[
                DependencyOverride("a", "b"),
                DependencyOverride("a", "b"),
            ],
        ),
    )

    assert result["ok"] is False
    assert "DUPLICATE_DEPENDENCY_OVERRIDE" in _warning_codes(result)
    assert result["comparison"]["field_uat_status"] == "blocked_by_invalid_patch"


def test_conflicting_duration_override_is_reported(tmp_path):
    project_path = _diagnostic_project(tmp_path)

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(
            duration_overrides=[
                DurationOverride("a", 3),
                DurationOverride("a", 5),
            ],
        ),
    )

    assert result["ok"] is False
    assert "CONFLICTING_DURATION_OVERRIDE" in _warning_codes(result)
    assert result["comparison"]["field_uat_status"] == "blocked_by_invalid_patch"


def test_invalid_duration_override_is_rejected(tmp_path):
    project_path = _diagnostic_project(tmp_path)

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(duration_overrides=[DurationOverride("a", 0)]),
    )

    assert result["ok"] is False
    assert "INVALID_DURATION" in _warning_codes(result)


def test_cycle_sets_field_uat_status_blocked_by_cycle(tmp_path):
    project_path = _diagnostic_project(tmp_path)

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(
            dependency_overrides=[
                DependencyOverride("b", "c"),
                DependencyOverride("c", "a"),
            ],
        ),
    )

    assert result["ok"] is False
    assert result["comparison"]["field_uat_status"] == "blocked_by_cycle"
    assert "DEPENDENCY_CYCLE" in _warning_codes(result)


def test_target_finish_date_is_not_used_as_constraint(tmp_path):
    project_path = _diagnostic_project(tmp_path)

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(target_finish_date=date(2026, 7, 31)),
    )

    assert result["comparison"]["after_finish_date"] != "2026-07-31"
    assert result["comparison"]["delta_days_after"] is not None
    assert "MISSING_TARGET_FINISH_DATE" not in _warning_codes(result)


def test_correction_records_keep_applied_order_with_diagnostics(tmp_path):
    project_path = _diagnostic_project(tmp_path)

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(
            dependency_overrides=[
                DependencyOverride("b", "c"),
                DependencyOverride("c", "d"),
            ],
        ),
    )

    assert [record["applied_order"] for record in result["correction_records"]] == [1, 2]


def test_calibrate_completion_date_returns_diagnostics(tmp_path):
    project_path = _diagnostic_project(tmp_path)

    result = calibrate_completion_date(
        project_path,
        target_finish_date="2026-06-30",
        dependency_overrides=[
            {"predecessor_id": "b", "successor_id": "c", "dependency_type": "FS", "lag_days": 1},
        ],
    )

    assert "diagnostics" in result
    assert "field_uat_status" in result["comparison"]
    assert "relationship_coverage_before" in result["comparison"]
    assert "cost_coverage_after" in result["comparison"]


def _warning_codes(result: dict[str, object]) -> set[str]:
    warnings = result["warnings"]
    assert isinstance(warnings, list)
    return {str(warning["code"]) for warning in warnings if isinstance(warning, dict)}


def _diagnostic_project(tmp_path):
    project_path = tmp_path / "diagnostics.scheduler"
    db.initialize_database(project_path)
    db.create_calendar(project_path, Calendar("cal", "Korean 5-day", "1111100"))
    db.create_project(project_path, Project("project", "Diagnostics Pilot", date(2026, 6, 1), "cal"))
    db.add_wbs(project_path, WBS("wbs", None, "ROOT", "ROOT", 1))
    db.add_activity(project_path, Activity("a", "A", "Imported A", "wbs", "공통", "", 5, cost=1000))
    db.add_activity(project_path, Activity("b", "B", "Imported B", "wbs", "공통", "", 2))
    db.add_activity(project_path, Activity("c", "C", "Imported C", "wbs", "공통", "", 3))
    db.add_activity(project_path, Activity("d", "D", "Imported D", "wbs", "공통", "", 4))
    db.add_relationship(project_path, Relationship("rel-ab", "a", "b", "FS", 0))
    return project_path
