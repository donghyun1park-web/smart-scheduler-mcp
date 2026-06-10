from __future__ import annotations

import pytest

from core.report_styles import (
    format_delay_issue,
    format_recovery_plan,
    format_report_summary,
    normalize_report_style,
)


def test_normalize_report_style_accepts_aliases():
    assert normalize_report_style("internal") == "internal"
    assert normalize_report_style("현장") == "internal"
    assert normalize_report_style("head_office") == "hq"
    assert normalize_report_style("본사") == "hq"
    assert normalize_report_style("owner") == "client"
    assert normalize_report_style("발주처") == "client"
    assert normalize_report_style(None) == "internal"


def test_normalize_report_style_rejects_unknown_style():
    with pytest.raises(ValueError, match="Unsupported report_style"):
        normalize_report_style("unknown")


def test_report_summary_differs_by_audience():
    site_data = {
        "project": {"name": "Demo"},
        "summary": {
            "planned_progress_pct": 70.0,
            "actual_progress_pct": 63.0,
            "progress_gap_pct": -7.0,
            "cost_execution_rate": 82.0,
            "billing_rate": 45.0,
            "delayed_count": 3,
        },
    }

    internal = format_report_summary(site_data, "internal")
    hq = format_report_summary(site_data, "hq")
    client = format_report_summary(site_data, "client")

    assert len({internal, hq, client}) == 3
    assert "담당자 확인" in internal
    assert "원가 집행률" in hq
    assert "검토 중입니다" in client


def test_client_style_avoids_internal_or_blame_language():
    issue = {"name": "A-100", "reason": "internal reason", "reason_code": "schedule_progress_delay"}
    plan = {"title": "협력업체 투입 후보", "action": "협력업체 작업반 조정 초안입니다."}

    client_issue = format_delay_issue(issue, "client")
    client_plan = format_recovery_plan(plan, "client")
    joined = f"{client_issue} {client_plan}"

    for forbidden in ["손실", "적자", "책임", "부실", "협력업체 문제", "내부 원가 과투입", "확정", "반드시"]:
        assert forbidden not in joined
    assert "검토" in joined
