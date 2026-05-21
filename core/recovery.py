from __future__ import annotations

from typing import Any


FORBIDDEN_FINAL_WORDS = (
    "확정",
    "반드시 시행",
    "최종 결정",
    "confirmed",
    "must execute",
)


_RECOVERY_CANDIDATES: dict[str, list[dict[str, Any]]] = {
    "material_delay": [
        {
            "title": "자재 반입 일정 재확인 후보",
            "action": "협력사 납기와 대체 조달 가능성을 같은 날 확인하는 초안입니다.",
            "assumptions": ["대체 자재가 설계/감리 기준을 만족해야 함", "발주처 승인 필요 여부 검토"],
            "expected_recovery_days": 2,
        },
        {
            "title": "선행 가능 작업 전환 후보",
            "action": "자재 도착 전 수행 가능한 먹매, 준비, 주변 공정을 우선 배치하는 초안입니다.",
            "assumptions": ["간섭 공종과 작업구역 충돌이 없어야 함"],
            "expected_recovery_days": 1,
        },
    ],
    "manpower_shortage": [
        {
            "title": "인력 재배치 후보",
            "action": "동일 공종 내 여유 작업조를 위험 작업에 단기 배치하는 초안입니다.",
            "assumptions": ["안전관리자와 협력사 투입 가능 여부 검토"],
            "expected_recovery_days": 2,
        }
    ],
    "predecessor_incomplete": [
        {
            "title": "작업구역 분할 착수 후보",
            "action": "완료된 구역부터 후속공정을 부분 착수하는 초안입니다.",
            "assumptions": ["품질검측과 동선 분리가 가능해야 함"],
            "expected_recovery_days": 1,
        }
    ],
}


def suggest_recovery_plans(delay_reason_code: str) -> list[dict[str, Any]]:
    candidates = _RECOVERY_CANDIDATES.get(
        delay_reason_code,
        [
            {
                "title": "현장 협의 후보",
                "action": "담당자, 협력사, 감리와 원인 및 만회 가능 조건을 검토하는 초안입니다.",
                "assumptions": ["현장소장 검토 후 적용 여부 결정"],
                "expected_recovery_days": 0,
            }
        ],
    )
    return [
        {
            **candidate,
            "reason_code": delay_reason_code,
            "status": "candidate",
            "review_required": True,
        }
        for candidate in candidates
    ]


def estimate_recovery_effect(plan: dict[str, Any], activity: dict[str, Any]) -> dict[str, Any]:
    return {
        "activity_id": activity.get("activity_id"),
        "activity_name": activity.get("name") or activity.get("activity_name"),
        "candidate_title": plan.get("title"),
        "estimated_recovery_days": plan.get("expected_recovery_days", 0),
        "assumptions": plan.get("assumptions", []),
        "review_required": True,
    }


def format_recovery_report(delay_item: dict[str, Any], recovery_plans: list[dict[str, Any]]) -> str:
    activity_name = delay_item.get("activity_name") or delay_item.get("name") or "activity"
    reason_code = delay_item.get("reason_code") or "unknown"
    lines = [f"{activity_name} 지연 원인({reason_code})에 대한 만회대책 초안입니다. 검토 필요."]
    for idx, plan in enumerate(recovery_plans, start=1):
        lines.append(f"{idx}. {plan.get('title')}: {plan.get('action')} 검토 필요.")
    report = "\n".join(lines)
    _assert_no_final_words(report)
    return report


def _assert_no_final_words(text: str) -> None:
    found = [word for word in FORBIDDEN_FINAL_WORDS if word in text]
    if found:
        raise ValueError(f"Recovery text contains final-decision wording: {found}")
