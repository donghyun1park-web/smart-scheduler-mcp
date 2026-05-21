from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Mapping, cast

from core.data_health import check_data_health
from core.evm_explain import explain_evm_totals_ko
from core.next_actions import UserProfile, suggest_next_actions
from core.workflows import get_daily_close_status, get_weekly_report_precheck_status
from tools.cost_tools import analyze_evm_from_db

PROFILE_LABELS: dict[UserProfile, str] = {
    "field_admin": "공무",
    "site_manager": "현장소장",
    "hq": "본사/관리",
    "developer": "관리자/개발자",
}


def build_operations_home_state(
    db_path: str | Path,
    profile: str,
    as_of: date | None = None,
) -> dict[str, Any]:
    selected_profile = _profile(profile)
    today = as_of or date.today()
    health = check_data_health(db_path, as_of=today)
    actions = suggest_next_actions(db_path, profile=selected_profile, as_of=today)
    evm = analyze_evm_from_db(str(db_path), as_of_date=today.isoformat())
    totals = cast(Mapping[str, object], evm.get("totals", {}))
    explanation = explain_evm_totals_ko(totals)
    daily = get_daily_close_status(db_path, as_of=today)
    weekly = get_weekly_report_precheck_status(db_path, as_of=today)
    return {
        "db_path": str(db_path),
        "as_of": today.isoformat(),
        "profile": selected_profile,
        "profile_label_ko": PROFILE_LABELS[selected_profile],
        "health": health.to_dict(),
        "next_actions": [action.to_dict() for action in actions],
        "evm": evm,
        "evm_explanation": explanation,
        "workflows": {
            "daily_close": daily.to_dict(),
            "weekly_report_precheck": weekly.to_dict(),
        },
    }


def _profile(value: str) -> UserProfile:
    if value in PROFILE_LABELS:
        return cast(UserProfile, value)
    return "field_admin"


def render_operations_home(state: dict[str, Any]) -> None:
    import streamlit as st

    st.title("AI 건축공정표 운영센터")
    st.caption(f"DB: {state.get('db_path', '')}")
    health = dict(state.get("health") or {})
    cols = st.columns(4)
    cols[0].metric("데이터 건강점수", f"{health.get('score', 0)}점")
    cols[1].metric("상태", str(health.get("status", "")))
    cols[2].metric("오류", f"{health.get('error_count', 0)}건")
    cols[3].metric("주의", f"{health.get('warning_count', 0)}건")

    st.subheader("다음 추천 행동")
    for action in state.get("next_actions", []):
        st.write(f"**{action['title_ko']}** - {action['reason_ko']}")
        if action.get("tool_name"):
            st.code(str(action["tool_name"]), language="text")

    explanation = dict(state.get("evm_explanation") or {})
    st.subheader("EVM 쉬운 설명")
    st.write(explanation.get("headline_ko", ""))
    st.write(explanation.get("summary_ko", ""))

    workflows = dict(state.get("workflows") or {})
    st.subheader("워크플로우 상태")
    for workflow in workflows.values():
        st.write(f"**{workflow['title_ko']}**: {workflow['summary_ko']}")
        st.dataframe(workflow.get("steps", []), use_container_width=True)
