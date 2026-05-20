from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from core import db
from core.calibration import (
    CalibrationPatch,
    DependencyOverride,
    DurationOverride,
    calibrate_project_completion,
)
from core.models import Activity, Calendar, Project, WBS


FIXTURES = Path(__file__).parent / "fixtures"


def test_apply_calibration_adds_dependencies_without_mutating_imported_schedule(tmp_path):
    project_path = _calibration_project(tmp_path)
    before_relationships = db.list_relationships(project_path)
    before_durations = {activity.activity_id: activity.duration for activity in db.list_activities(project_path)}

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(
            dependency_overrides=[
                DependencyOverride("a", "b", reason="field sequence"),
                DependencyOverride("b", "c", lag_days=1, reason="handover lag"),
            ],
        ),
    )

    after_relationships = db.list_relationships(project_path)
    after_durations = {activity.activity_id: activity.duration for activity in db.list_activities(project_path)}
    assert result["comparison"]["dependency_count_before"] == 0
    assert result["comparison"]["dependency_count_after"] == 2
    assert result["comparison"]["lag_override_count"] == 1
    assert before_relationships == after_relationships
    assert before_durations == after_durations
    assert [record["applied_order"] for record in result["correction_records"]] == [1, 2]


def test_completion_date_delta_is_reported_before_and_after_calibration(tmp_path):
    project_path = _calibration_project(tmp_path)

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(
            target_finish_date=date(2026, 6, 12),
            dependency_overrides=[
                DependencyOverride("a", "b"),
                DependencyOverride("b", "c"),
            ],
        ),
    )

    comparison = result["comparison"]
    assert comparison["before_finish_date"] == "2026-06-08"
    assert comparison["after_finish_date"] == "2026-06-12"
    assert comparison["target_finish_date"] == "2026-06-12"
    assert comparison["delta_days_before"] == 4
    assert comparison["delta_days_after"] == 0


def test_calibration_patch_rejects_unknown_task_id(tmp_path):
    project_path = _calibration_project(tmp_path)

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(dependency_overrides=[DependencyOverride("missing", "b")]),
    )

    assert result["ok"] is False
    assert "Unknown predecessor_id" in result["warnings"][0]


def test_calibration_detects_dependency_cycle(tmp_path):
    project_path = _calibration_project(tmp_path)

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(
            dependency_overrides=[
                DependencyOverride("a", "b"),
                DependencyOverride("b", "a"),
            ],
        ),
    )

    assert result["ok"] is False
    assert result["comparison"]["cycles_detected_after"]
    assert "cycle" in result["warnings"][0].lower()


def test_hongeundong_minimal_fixture_improves_finish_date_delta(tmp_path):
    project_path = _calibration_project_from_fixture(tmp_path)
    patch_data = json.loads((FIXTURES / "hongeundong_calibration_patch.json").read_text(encoding="utf-8"))

    result = calibrate_project_completion(
        project_path,
        CalibrationPatch(
            target_finish_date=date.fromisoformat(patch_data["target_finish_date"]),
            dependency_overrides=[
                DependencyOverride(**item) for item in patch_data["dependency_overrides"]
            ],
            duration_overrides=[
                DurationOverride(**item) for item in patch_data["duration_overrides"]
            ],
            notes=patch_data["notes"],
        ),
    )

    comparison = result["comparison"]
    assert result["ok"] is True
    assert comparison["dependency_count_before"] == 0
    assert comparison["dependency_count_after"] == 2
    assert comparison["duration_override_count"] == 1
    assert abs(comparison["delta_days_after"]) < abs(comparison["delta_days_before"])
    assert result["calibration_patch"]["notes"] == "HongEundong minimal calibration fixture"


def _calibration_project(tmp_path):
    project_path = tmp_path / "calibration.scheduler"
    db.initialize_database(project_path)
    db.create_calendar(project_path, Calendar("cal", "Korean 5-day", "1111100"))
    db.create_project(project_path, Project("project", "Calibration Pilot", date(2026, 6, 1), "cal"))
    db.add_wbs(project_path, WBS("wbs", None, "ROOT", "ROOT", 1))
    db.add_activity(project_path, Activity("a", "A", "Imported A", "wbs", "공통", "", 5))
    db.add_activity(project_path, Activity("b", "B", "Imported B", "wbs", "공통", "", 2))
    db.add_activity(project_path, Activity("c", "C", "Imported C", "wbs", "공통", "", 2))
    return project_path


def _calibration_project_from_fixture(tmp_path):
    data = json.loads((FIXTURES / "hongeundong_minimal_import.json").read_text(encoding="utf-8"))
    project_path = tmp_path / "hongeundong_minimal.scheduler"
    db.initialize_database(project_path)
    db.create_calendar(project_path, Calendar("cal", "Korean 5-day", "1111100"))
    db.create_project(
        project_path,
        Project("project", data["project"]["name"], date.fromisoformat(data["project"]["start_date"]), "cal"),
    )
    db.add_wbs(project_path, WBS("wbs", None, "ROOT", "ROOT", 1))
    for item in data["activities"]:
        db.add_activity(
            project_path,
            Activity(
                item["activity_id"],
                item["code"],
                item["name"],
                "wbs",
                "공통",
                "",
                item["duration"],
            ),
        )
    return project_path
