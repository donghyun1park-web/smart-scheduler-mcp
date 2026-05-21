from __future__ import annotations

from datetime import date
from pathlib import Path

from core import db
from core.models import Activity, Calendar, Project, WBS
from viewer.components.site_manager_dashboard import build_dashboard_report_file


def test_build_dashboard_report_file_generates_requested_style(tmp_path):
    db_path = tmp_path / "project.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Calendar", "1111100"))
    db.create_project(db_path, Project("project-1", "Demo", date(2026, 5, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-1", None, "WBS", "Root"))
    db.create_activity(db_path, Activity("act-1", "A-100", "Activity", "wbs-1", "civil", "B1", 5))

    result = build_dashboard_report_file(db_path, tmp_path, report_style="client")

    assert result["ok"] is True
    assert result["report_style"] == "client"
    assert Path(result["output_path"]).is_file()
