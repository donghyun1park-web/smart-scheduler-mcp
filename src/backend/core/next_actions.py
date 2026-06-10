from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Mapping

from core.data_health import check_data_health

UserProfile = Literal["field_admin", "site_manager", "hq", "developer"]
ActionPriority = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class SuggestedAction:
    priority: ActionPriority
    title_ko: str
    reason_ko: str
    tool_name: str | None
    params_hint: dict[str, object]
    profile: UserProfile
    blocked_by: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "priority": self.priority,
            "title_ko": self.title_ko,
            "reason_ko": self.reason_ko,
            "tool_name": self.tool_name,
            "params_hint": self.params_hint,
            "profile": self.profile,
            "blocked_by": list(self.blocked_by),
        }


def suggest_next_actions(
    db_path: str | Path,
    *,
    profile: UserProfile = "field_admin",
    as_of: date | None = None,
    limit: int = 5,
) -> tuple[SuggestedAction, ...]:
    health = check_data_health(db_path, as_of=as_of)
    issue_codes = {issue.code for issue in health.issues}
    actions: list[SuggestedAction] = []
    common_params = {"db_path": str(db_path)}

    if "no_activities" in issue_codes:
        actions.append(
            _action(profile, "high", "공정표 Excel 가져오기", "공정 데이터가 없어 다음 분석을 시작할 수 없습니다.", "import_schedule_excel", common_params)
        )
        return tuple(actions[: max(limit, 0)])

    if {"no_cost_items", "activity_without_cost"} & issue_codes:
        actions.append(
            _action(profile, "high", "실행예산 Excel 가져오기", "공정과 원가가 연결되지 않아 EVM과 기성 분석이 제한됩니다.", "import_budget_excel", common_params)
        )
    if "no_relationships" in issue_codes:
        actions.append(
            _action(profile, "medium", "선후행 관계 후보 검토", "관계가 없어 CPM과 핵심경로 신뢰도가 낮습니다.", "suggest_activity_relationships", common_params)
        )
    if health.score < 60 or profile == "developer":
        actions.append(
            _action(profile, "high" if health.score < 60 else "medium", "데이터 건강점수 재점검", health.summary_ko, "check_data_health", common_params)
        )

    if profile == "site_manager":
        actions.extend(
            [
                _action(profile, "medium", "현장소장 브리핑 확인", "오늘 현장 상태를 공정, 원가, 리스크 기준으로 짧게 확인합니다.", "get_site_briefing", common_params),
                _action(profile, "medium", "주간보고서 생성 준비", "보고서 생성 전 데이터 상태와 부진공정을 함께 확인합니다.", "generate_weekly_report_from_db", common_params),
            ]
        )
    elif profile == "hq":
        actions.extend(
            [
                _action(profile, "high", "EVM 현황 분석", "본사 보고에는 PV/EV/AC와 SPI/CPI 기준의 공정-원가 해석이 필요합니다.", "analyze_evm_from_db", common_params),
                _action(profile, "medium", "공종별 원가 요약 확인", "공종별 예산, 투입, 기성 차이를 먼저 확인합니다.", "summarize_cost_by_discipline", common_params),
            ]
        )
    elif profile == "field_admin":
        actions.append(
            _action(profile, "low", "주간보고서 초안 생성", "입력 상태가 충분하면 회의용 보고서를 생성할 수 있습니다.", "generate_weekly_report_from_db", common_params)
        )
    elif profile == "developer":
        actions.append(
            _action(profile, "low", "MCP tool 목록 확인", "배포 전 서버 등록 상태와 smoke test 범위를 확인합니다.", None, {"command": "from server import build_server"})
        )

    return tuple(actions[: max(limit, 0)])


def _action(
    profile: UserProfile,
    priority: ActionPriority,
    title: str,
    reason: str,
    tool_name: str | None,
    params: Mapping[str, object],
) -> SuggestedAction:
    return SuggestedAction(priority, title, reason, tool_name, dict(params), profile)
