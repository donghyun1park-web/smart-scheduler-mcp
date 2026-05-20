from __future__ import annotations

from core import db
from core.models import WBS
from tools.project_tools import create_project
from tools.sequence_tools import apply_sequences


def test_apply_sequence_creates_zone_activities_and_relationships(tmp_path):
    project = create_project(
        "Sequence Pilot",
        "2026-01-05",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    db.add_wbs(project["project_path"], WBS("wbs-hvac", None, "HVAC", "HVAC", 1))

    result = apply_sequences(
        project["project_path"],
        "공조",
        "hvac_duct_standard",
        ["1F", "2F"],
        "wbs-hvac",
    )

    activities = db.list_activities(project["project_path"])
    relationships = db.list_relationships(project["project_path"])
    assert result["ok"] is True
    assert result["added_activities"] == 10
    assert result["added_relationships"] == 8
    assert {activity.zone for activity in activities} == {"1F", "2F"}
    assert all(rel.rel_type == "FS" for rel in relationships)


def test_apply_sequence_does_not_create_inter_zone_relationships(tmp_path):
    project = create_project(
        "Sequence Pilot",
        "2026-01-05",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    db.add_wbs(project["project_path"], WBS("wbs-plumbing", None, "PL", "Plumbing", 1))

    apply_sequences(project["project_path"], "위생", "plumbing_sanitary_standard", ["1F", "2F"], "wbs-plumbing")
    relationships = db.list_relationships(project["project_path"])

    assert len(relationships) == 6
