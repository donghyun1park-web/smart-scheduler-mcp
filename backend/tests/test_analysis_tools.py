from __future__ import annotations

from core import db
from core.models import Activity, Relationship, WBS
from tools.analysis_tools import calculate_cpm, get_critical_path
from tools.project_tools import create_project


def test_calculate_cpm_tool_saves_results_and_critical_path(tmp_path):
    project = create_project(
        "Analysis Pilot",
        "2026-01-05",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    path = project["project_path"]
    db.add_wbs(path, WBS("wbs", None, "MEP", "MEP", 1))
    db.add_activity(path, _activity("a", "A100", "Sleeve", 2))
    db.add_activity(path, _activity("b", "A200", "Duct", 3))
    db.add_relationship(path, Relationship("r1", "a", "b", "FS", 0))

    result = calculate_cpm(path)
    critical = get_critical_path(path)

    assert result["ok"] is True
    assert result["total_duration_days"] == 5
    assert result["critical_count"] == 2
    assert result["cycles_detected"] == []
    assert [item["code"] for item in critical["critical_path"]] == ["A100", "A200"]
    assert critical["critical_path"][0]["es_date"] == "2026-01-05"


def _activity(activity_id: str, code: str, name: str, duration: int) -> Activity:
    return Activity(
        activity_id=activity_id,
        code=code,
        name=name,
        wbs_id="wbs",
        discipline="공조",
        zone="1F",
        duration=duration,
    )
