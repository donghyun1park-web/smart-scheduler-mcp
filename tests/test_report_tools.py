from __future__ import annotations

from datetime import date

from core import db
from core.models import Activity, Calendar, Project, WBS
from tools.report_tools import generate_report


def test_generate_report_creates_week4_excel_report(tmp_path):
    project_path = tmp_path / "sample.scheduler"
    db.initialize_database(project_path)
    db.create_calendar(project_path, Calendar("cal", "Korean 5-day", "1111100"))
    db.create_project(project_path, Project("project", "Sample", date(2026, 1, 5), "cal"))
    db.add_wbs(project_path, WBS("wbs", None, "MEP", "MEP", 1))
    db.add_activity(
        project_path,
        Activity("a", "A100", "Activity", "wbs", "\uacf5\ud1b5", "1F", 1, 100.0),
    )

    result = generate_report(project_path)

    assert result["ok"] is True
    assert result["output_path"]
    assert result["sheets"] == [
        "\uc694\uc57d",
        "WBS",
        "Activity \uc0c1\uc138",
        "\uad00\uacc4",
        "S-Curve \ub370\uc774\ud130",
    ]
