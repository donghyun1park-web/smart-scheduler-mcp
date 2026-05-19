from __future__ import annotations

from tools.report_tools import generate_report


def test_generate_report_is_explicitly_not_implemented_for_week2(tmp_path):
    result = generate_report(tmp_path / "sample.scheduler")

    assert result["ok"] is False
    assert "Week 2" in result["error"]
