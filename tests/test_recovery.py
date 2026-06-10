from __future__ import annotations

from core.recovery import FORBIDDEN_FINAL_WORDS, format_recovery_report, suggest_recovery_plans


def test_suggest_recovery_plans_returns_candidates_only():
    plans = suggest_recovery_plans("material_delay")

    assert plans
    assert all(plan["status"] == "candidate" for plan in plans)
    joined = " ".join(str(plan) for plan in plans)
    assert "후보" in joined or "초안" in joined
    assert not any(word in joined for word in FORBIDDEN_FINAL_WORDS)


def test_format_recovery_report_uses_review_required_language():
    report = format_recovery_report(
        {"activity_name": "ceiling framing", "reason_code": "manpower_shortage"},
        suggest_recovery_plans("manpower_shortage"),
    )

    assert "ceiling framing" in report
    assert "검토 필요" in report
    assert not any(word in report for word in FORBIDDEN_FINAL_WORDS)
