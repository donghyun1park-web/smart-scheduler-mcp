from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Mapping, cast

from core.dashboard import generate_dashboard_markdown
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

    from viewer.components import ui_kit

    profile_label = state.get("profile_label_ko", "사용자")
    health = dict(state.get("health") or {})
    score = int(health.get("score", 0) or 0)
    status = str(health.get("status", "-"))

    st.caption(f"📁 `{state.get('db_path', '')}`  ·  👤 {profile_label}  ·  📅 {state.get('as_of', '')}")

    # ── 상단 KPI 카드 (4개) ───────────────────────────────────────────
    score_delta = None
    if score >= 80:
        score_delta = "양호"
    elif score >= 60:
        score_delta = "주의"
    else:
        score_delta = "위험"
    cols = st.columns(4)
    cols[0].metric("📊 데이터 건강점수", f"{score}점", score_delta)
    with cols[1]:
        st.markdown("**🚦 종합 상태**")
        st.markdown(ui_kit.status_pill(status), unsafe_allow_html=True)
    cols[2].metric("❌ 오류", f"{health.get('error_count', 0)}건")
    cols[3].metric("⚠ 주의", f"{health.get('warning_count', 0)}건")

    if health.get("summary_ko"):
        st.caption(f"💡 {health['summary_ko']}")

    ui_kit.divider()

    # ── 다음 추천 행동 카드 ──────────────────────────────────────────
    ui_kit.section("다음 추천 행동", icon="🎯", caption=f"{profile_label}의 우선순위 작업")
    actions = state.get("next_actions") or []
    if not actions:
        ui_kit.callout("success", "추천할 작업이 없습니다. 현재 상태가 양호합니다.")
    else:
        for idx, action in enumerate(actions, start=1):
            priority = str(action.get("priority", "medium"))
            badge_color = {"high": "red", "medium": "yellow", "low": "blue"}.get(priority, "gray")
            with ui_kit.card():
                head = (
                    f"<div style='display:flex; align-items:center; gap:8px;'>"
                    f"<strong style='font-size:1.05rem;'>{idx}. {action['title_ko']}</strong>"
                    f"{ui_kit.badge(priority.upper(), badge_color)}"
                    f"</div>"
                )
                st.markdown(head, unsafe_allow_html=True)
                st.markdown(f"<div style='color:#475569; margin:6px 0;'>{action['reason_ko']}</div>",
                            unsafe_allow_html=True)
                if action.get("tool_name"):
                    st.markdown(
                        f"<code style='background:#F1F5F9; padding:3px 8px; border-radius:6px; "
                        f"font-size:0.82rem;'>MCP · {action['tool_name']}</code>",
                        unsafe_allow_html=True,
                    )

    ui_kit.divider()

    # ── EVM 쉬운 설명 ────────────────────────────────────────────────
    explanation = dict(state.get("evm_explanation") or {})
    with ui_kit.card("EVM 쉬운 설명", icon="💰", subtitle="공기·원가 효율 한국어 해설"):
        headline = explanation.get("headline_ko", "")
        summary = explanation.get("summary_ko", "")
        if headline:
            st.markdown(f"**{headline}**")
        if summary:
            st.write(summary)
        if not headline and not summary:
            ui_kit.callout("warning", "EVM 해석에 필요한 데이터가 부족합니다. 실행예산을 먼저 가져오세요.")

    # ── 워크플로우 상태 ─────────────────────────────────────────────
    workflows = dict(state.get("workflows") or {})
    if workflows:
        ui_kit.section("워크플로우 상태", icon="🧭", caption="일일마감 · 주간보고 사전점검")
        for workflow in workflows.values():
            with ui_kit.card(workflow["title_ko"], icon="✅"):
                st.markdown(f"<div class='sns-card-sub'>{workflow['summary_ko']}</div>",
                            unsafe_allow_html=True)
                if workflow.get("steps"):
                    st.dataframe(workflow["steps"], use_container_width=True, hide_index=True)

    # ── Sprint-1 안건 3: Markdown 보고서 클립보드 ────────────────────
    db_path = state.get("db_path")
    if db_path:
        ui_kit.divider()
        with st.expander("📋 카톡/메일용 Markdown 보고서 (코드 박스 우측 상단 복사 아이콘)", expanded=False):
            try:
                md = generate_dashboard_markdown(db_path)
                content = md.get("markdown", "") if isinstance(md, dict) else str(md)
                if content:
                    st.code(content, language="markdown")
                    st.caption("복사 후 카톡/메일에 붙여넣으세요.")
                else:
                    st.info("아직 보고서로 만들 데이터가 없습니다.")
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Markdown 보고서를 생성하지 못했습니다: {exc}")

    # Sprint-1 안건 3: Markdown 보고서 클립보드 복사 섹션.
    db_path = state.get("db_path")
    if db_path:
        with st.expander("📋 카톡/메일용 Markdown 보고서 (우측 상단 복사 아이콘 클릭)", expanded=False):
            try:
                md = generate_dashboard_markdown(db_path)
                content = md.get("markdown", "") if isinstance(md, dict) else str(md)
                if content:
                    st.code(content, language="markdown")
                    st.caption("코드 블록 우측 상단 복사 아이콘으로 클립보드에 복사 후, 카톡/메일에 그대로 붙여넣으세요.")
                else:
                    st.info("아직 보고서로 만들 데이터가 없습니다.")
            except Exception as exc:  # noqa: BLE001 - viewer must not crash on missing data
                st.warning(f"Markdown 보고서를 생성하지 못했습니다: {exc}")
