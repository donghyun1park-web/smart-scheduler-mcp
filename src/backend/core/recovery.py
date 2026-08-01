from __future__ import annotations

from typing import Any


FORBIDDEN_FINAL_WORDS = (
    "확정",
    "반드시",
    "반드시 시행",
    "최종 결정",
    "자동 결정",
    "무조건",
    "confirmed",
    "must execute",
)


_REASON_ALIASES = {
    "equipment_shortage": "equipment_delay",
    "approval_delay": "inspection_delay",
    "subcontractor_underperformance": "subcontractor_delay",
}


_RECOVERY_CANDIDATES: dict[str, list[dict[str, Any]]] = {
    "material_delay": [
        {
            "title": "자재 반입 일정 재확인 후보",
            "action": "협력사 납기와 대체 조달 가능성을 같은 날 확인하는 초안입니다.",
            "assumptions": ["대체 자재가 설계/감리 기준을 만족해야 함", "발주처 승인 필요 여부 검토"],
            "actions": ["납기 재확인", "대체 조달 가능성 검토", "발주처 승인 필요 여부 검토"],
            "required_checks": ["대체 자재 승인 기준 확인", "현장소장 승인 필요"],
            "human_decision_required": True,
            "reason_label_ko": "자재 지연",
            "expected_effect": "자재 대기 리스크 완화 후보",
            "report_sentence": "자재 반입 일정과 대체 조달 가능성을 검토하는 초안입니다.",
            "expected_recovery_days": 2,
        },
        {
            "title": "선행 가능 작업 전환 후보",
            "action": "자재 도착 전 수행 가능한 먹매, 준비, 주변 공정을 우선 배치하는 초안입니다.",
            "assumptions": ["간섭 공종과 작업구역 충돌이 없어야 함"],
            "actions": ["선행 가능 작업 식별", "작업구역 간섭 확인", "주변 공정 우선 배치 검토"],
            "required_checks": ["안전 동선 확인", "현장소장 승인 필요"],
            "human_decision_required": True,
            "reason_label_ko": "자재 지연",
            "expected_effect": "대기시간 일부 흡수 후보",
            "report_sentence": "자재 도착 전 선행 가능 작업 전환을 검토하는 초안입니다.",
            "expected_recovery_days": 1,
        },
    ],
    "manpower_shortage": [
        {
            "title": "인력 재배치 후보",
            "action": "동일 공종 내 여유 작업조를 위험 작업에 단기 배치하는 초안입니다.",
            "assumptions": ["안전관리자와 협력사 투입 가능 여부 검토"],
            "actions": ["작업조 재배치 검토", "추가 작업조 투입 가능성 확인", "일일 목표물량 재설정"],
            "required_checks": ["안전관리자 검토", "현장소장 승인 필요"],
            "human_decision_required": True,
            "reason_label_ko": "인력 부족",
            "expected_effect": "단기 작업량 보완 후보",
            "report_sentence": "작업조 재배치와 추가 투입 가능성을 검토하는 초안입니다.",
            "expected_recovery_days": 2,
        }
    ],
    "predecessor_incomplete": [
        {
            "title": "작업구역 분할 착수 후보",
            "action": "완료된 구역부터 후속공정을 부분 착수하는 초안입니다.",
            "assumptions": ["품질검측과 동선 분리가 가능해야 함"],
            "actions": ["완료 구역 분리", "후속공정 부분 착수 검토", "품질검측 가능 구간 확인"],
            "required_checks": ["동선 분리 가능 여부 확인", "현장소장 승인 필요"],
            "human_decision_required": True,
            "reason_label_ko": "선행공정 미완료",
            "expected_effect": "후속공정 대기시간 완화 후보",
            "report_sentence": "완료 구역부터 부분 착수 가능성을 검토하는 초안입니다.",
            "expected_recovery_days": 1,
        }
    ],
    "equipment_delay": [
        {
            "title": "장비 투입 재조정 후보",
            "action": "장비 추가 투입, 사용 순서 조정, 대체 장비 확보 가능성을 검토하는 초안입니다.",
            "assumptions": ["장비 반입 동선과 작업구역 간섭 확인 필요", "현장소장 승인 필요"],
            "actions": [
                "장비 추가 투입 가능 여부 검토",
                "장비 사용 순서 재조정",
                "동일 장비 필요 작업 간 시간대 분리",
                "대체 또는 임대 장비 확보 가능성 확인",
                "장비 반입 동선 및 작업구역 간섭 확인",
            ],
            "required_checks": ["장비 반입 동선 확인", "안전관리 검토", "현장소장 승인 필요"],
            "human_decision_required": True,
            "reason_label_ko": "장비 지연",
            "expected_effect": "장비 대기와 작업 간섭 완화 후보",
            "report_sentence": "장비 투입계획 조정과 대체 장비 확보 가능성을 검토하는 초안입니다.",
            "expected_recovery_days": 2,
        }
    ],
    "inspection_delay": [
        {
            "title": "검측 및 승인 일정 선조율 후보",
            "action": "검측 일정 예약, 서류 선제 준비, 부분 검측 가능 구간 분리를 검토하는 초안입니다.",
            "assumptions": ["감리 협의 필요", "후속공정 착수 가능 구간 확인 필요"],
            "actions": [
                "감리/검측 일정 사전 예약",
                "검측 서류와 사진대지 선제 준비",
                "부분 검측 가능 구간 분리",
                "후속공정 착수 가능 구간 사전 협의",
                "승인 지연 영향 공정과 만회 가능 구간 보고",
            ],
            "required_checks": ["감리 협의 필요", "검측 서류 완결성 확인", "현장소장 승인 필요"],
            "human_decision_required": True,
            "reason_label_ko": "검측·승인 지연",
            "expected_effect": "승인 대기와 후속공정 지연 완화 후보",
            "report_sentence": "검측·승인 일정 선조율과 부분 검측 가능성을 검토하는 초안입니다.",
            "expected_recovery_days": 1,
        }
    ],
    "design_change": [
        {
            "title": "설계변경 구간 분리 관리 후보",
            "action": "변경구간과 미변경구간을 분리하고 선시공 가능 범위를 검토하는 초안입니다.",
            "assumptions": ["변경 도면 및 시공상세도 승인 일정 확인 필요", "비용 영향 별도 기록 필요"],
            "actions": [
                "변경구간과 미변경구간 분리 관리",
                "미변경구간 선시공 가능 여부 검토",
                "변경 도면/시공상세도 승인 일정 확인",
                "자재 변경 여부와 납기 영향 확인",
                "공정 영향일수와 비용 영향 별도 기록",
            ],
            "required_checks": ["설계 승인 일정 확인", "자재 변경 영향 확인", "현장소장 승인 필요"],
            "human_decision_required": True,
            "reason_label_ko": "설계변경",
            "expected_effect": "설계 변경 검토 구간으로 인한 전체 지연 완화 후보",
            "report_sentence": "설계변경 구간 분리와 미변경구간 선시공 가능성을 검토하는 초안입니다.",
            "expected_recovery_days": 3,
        }
    ],
    "subcontractor_delay": [
        {
            "title": "협력업체 투입계획 재협의 후보",
            "action": "작업반 재편성, 추가 작업조 투입, 작업구역 재배분을 검토하는 초안입니다.",
            "assumptions": ["협력업체 협의 필요", "지원업체 투입 가능성은 현장소장 승인 필요"],
            "actions": [
                "협력업체 작업반 재편성 협의",
                "추가 작업조 투입 가능 여부 확인",
                "작업구역 재배분 검토",
                "일일 목표물량 재설정",
                "지원업체 투입 가능성 검토",
            ],
            "required_checks": ["협력업체 협의 필요", "안전 및 품질관리 영향 확인", "현장소장 승인 필요"],
            "human_decision_required": True,
            "reason_label_ko": "협력업체 부진",
            "expected_effect": "투입량 부족과 구역 병목 완화 후보",
            "report_sentence": "작업반 재편성과 추가 투입 가능성을 검토하는 초안입니다.",
            "expected_recovery_days": 2,
        }
    ],
    "weather_delay": [
        {
            "title": "날씨 민감 공정 재배치 후보",
            "action": "외부작업을 내부작업으로 전환하고 날씨 민감 공정의 예비일 반영을 검토하는 초안입니다.",
            "assumptions": ["기상 영향일수 별도 기록 필요", "우천 후 재착수 조건 확인 필요"],
            "actions": [
                "외부작업을 내부작업으로 전환 가능한지 검토",
                "양생/방수/토공 등 날씨 민감 공정 재배치",
                "우천 후 재착수 조건 사전 확인",
                "기상 영향일수 별도 기록",
                "주간 예정공정에서 외부작업 예비일 반영",
            ],
            "required_checks": ["기상 영향일수 기록", "품질 재착수 조건 확인", "현장소장 승인 필요"],
            "human_decision_required": True,
            "reason_label_ko": "날씨 영향",
            "expected_effect": "외부작업 지연의 일정 영향 완화 후보",
            "report_sentence": "날씨 민감 공정 재배치와 예비일 반영을 검토하는 초안입니다.",
            "expected_recovery_days": 1,
        }
    ],
}


def suggest_recovery_plans(delay_reason_code: str) -> list[dict[str, Any]]:
    template_key = _REASON_ALIASES.get(delay_reason_code, delay_reason_code)
    candidates = _RECOVERY_CANDIDATES.get(
        template_key,
        [
            {
                "title": "현장 협의 후보",
                "action": "담당자, 협력사, 감리와 원인 및 만회 가능 조건을 검토하는 초안입니다.",
                "assumptions": ["현장소장 검토 후 적용 여부 결정"],
                "actions": ["원인 확인", "만회 가능 조건 검토", "현장소장 승인 필요"],
                "required_checks": ["담당자 협의 필요", "현장소장 승인 필요"],
                "human_decision_required": True,
                "reason_label_ko": "일반 지연",
                "expected_effect": "지연 원인과 대응 가능 범위 확인 후보",
                "report_sentence": "담당자 및 관련 주체와 만회 가능 조건을 검토하는 초안입니다.",
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
            "human_decision_required": True,
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
        checks = ", ".join(str(check) for check in plan.get("required_checks", [])[:2])
        check_text = f" 필요 확인: {checks}." if checks else ""
        lines.append(f"{idx}. {plan.get('title')}: {plan.get('report_sentence', plan.get('action'))} 검토 필요.{check_text}")
    report = "\n".join(lines)
    _assert_no_final_words(report)
    return report


def _assert_no_final_words(text: str) -> None:
    found = [word for word in FORBIDDEN_FINAL_WORDS if word in text]
    if found:
        raise ValueError(f"Recovery text contains final-decision wording: {found}")
