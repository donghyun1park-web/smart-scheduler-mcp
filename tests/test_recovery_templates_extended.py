from __future__ import annotations

from core.recovery import FORBIDDEN_FINAL_WORDS, format_recovery_report, suggest_recovery_plans


def test_extended_recovery_templates_cover_field_delay_reasons():
    reason_codes = [
        "equipment_delay",
        "inspection_delay",
        "design_change",
        "subcontractor_delay",
        "weather_delay",
    ]

    for reason_code in reason_codes:
        plans = suggest_recovery_plans(reason_code)
        assert plans, reason_code
        assert all(len(plan["actions"]) >= 3 for plan in plans)
        joined = " ".join(str(plan) for plan in plans)
        assert any(keyword in joined for keyword in ["초안", "검토 필요", "승인 필요"])
        assert "human_decision_required" in plans[0]
        assert plans[0]["human_decision_required"] is True
        assert not any(word in joined for word in FORBIDDEN_FINAL_WORDS)


def test_recovery_aliases_and_report_support_extended_reasons():
    plans = suggest_recovery_plans("approval_delay")
    report = format_recovery_report(
        {"activity_name": "Mock-up inspection", "reason_code": "approval_delay"},
        plans,
    )

    assert plans[0]["reason_code"] == "approval_delay"
    assert "검측" in plans[0]["reason_label_ko"] or "승인" in plans[0]["reason_label_ko"]
    assert "Mock-up inspection" in report
    assert "초안" in report
    assert "검토 필요" in report
    assert not any(word in report for word in FORBIDDEN_FINAL_WORDS)


def test_existing_recovery_templates_still_return_candidates():
    for reason_code in ("material_delay", "manpower_shortage", "predecessor_incomplete"):
        plans = suggest_recovery_plans(reason_code)
        assert plans
        assert all(plan["status"] == "candidate" for plan in plans)
