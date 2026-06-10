from __future__ import annotations

from core import db
from core.models import Activity, WBS
from tools.calibration_tools import calibrate_completion_date
from tools.project_tools import create_project


def test_calibrate_completion_date_tool_reports_delta(tmp_path):
    project = create_project(
        "Calibration Tool Pilot",
        "2026-06-01",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    path = project["project_path"]
    db.add_wbs(path, WBS("wbs", None, "ROOT", "ROOT", 1))
    db.add_activity(path, Activity("a", "A", "A", "wbs", "공통", "", 5))
    db.add_activity(path, Activity("b", "B", "B", "wbs", "공통", "", 2))
    db.add_activity(path, Activity("c", "C", "C", "wbs", "공통", "", 2))

    result = calibrate_completion_date(
        path,
        target_finish_date="2026-06-12",
        dependency_overrides=[
            {"predecessor_id": "a", "successor_id": "b", "reason": "field order"},
            {"predecessor_id": "b", "successor_id": "c", "reason": "field order"},
        ],
        notes="tool smoke",
    )

    assert result["ok"] is True
    assert result["comparison"]["delta_days_before"] == 4
    assert result["comparison"]["delta_days_after"] == 0
    assert result["calibration_patch"]["notes"] == "tool smoke"
