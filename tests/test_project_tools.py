from __future__ import annotations

from tools.project_tools import create_project, list_projects, load_project


def test_create_load_and_list_project(tmp_path):
    created = create_project(
        "Pilot",
        "2026-01-05",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        description="Week 2 test",
        projects_dir=tmp_path,
    )

    loaded = load_project(created["project_path"])
    listed = list_projects(projects_dir=tmp_path)

    assert created["ok"] is True
    assert created["project"]["name"] == "Pilot"
    assert created["project_path"].endswith(".scheduler")
    assert loaded["project"]["name"] == "Pilot"
    assert listed["projects"][0]["name"] == "Pilot"
