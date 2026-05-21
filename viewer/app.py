from __future__ import annotations

from viewer.components import (
    activity_editor,
    analysis_panel,
    calendar_editor,
    gantt_panel,
    import_panel,
    project_panel,
    report_panel,
    relationship_editor,
    sequence_panel,
    s_curve_panel,
    wbs_editor,
)
from viewer.components import ui_kit


def main() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="Smart Node-Scheduler",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    ui_kit.inject_global_css()
    ui_kit.hero(
        "Smart Node-Scheduler",
        subtitle="MEP 특화 공정관리 · CPM 자동 계산 · 현장 운영 한눈에",
        icon="🏗️",
    )

    project_panel.render()
    project_path = st.session_state.get("project_path")
    if not project_path:
        ui_kit.callout(
            "info",
            "왼쪽 사이드바에서 <b>프로젝트를 생성하거나 불러오면</b> 모든 기능이 활성화됩니다.",
            title="시작하기",
        )
        with ui_kit.card("🚀 다음 단계 가이드", subtitle="처음 사용하시나요? 순서대로 따라오세요."):
            st.markdown(
                """
                1. **프로젝트 만들기** — 사이드바에서 이름·시작일·캘린더 입력
                2. **개략공정표 가져오기** — `📥 Import` 탭에서 엑셀 업로드
                3. **MEP 표준 시퀀스 적용** — `⚡ Sequences` 탭에서 zone 일괄 적용
                4. **CPM 계산** — `🧮 CPM` 탭에서 한 번 클릭 → Critical Path · 준공일 즉시 산출
                5. **보고서 출력** — `📤 Report` 탭에서 Excel 다운로드, `1매 요약` 페이지에서 인쇄
                """
            )
        return

    tabs = st.tabs([
        "📊 WBS",
        "🧱 Activities",
        "🔗 Relationships",
        "📅 Calendar",
        "📥 Import",
        "⚡ Sequences",
        "🧮 CPM",
        "📈 Gantt",
        "💰 S-Curve",
        "📤 Report",
    ])
    with tabs[0]:
        wbs_editor.render(project_path)
    with tabs[1]:
        activity_editor.render(project_path)
    with tabs[2]:
        relationship_editor.render(project_path)
    with tabs[3]:
        calendar_editor.render(project_path)
    with tabs[4]:
        import_panel.render(project_path)
    with tabs[5]:
        sequence_panel.render(project_path)
    with tabs[6]:
        analysis_panel.render(project_path)
    with tabs[7]:
        gantt_panel.render(project_path)
    with tabs[8]:
        s_curve_panel.render(project_path)
    with tabs[9]:
        report_panel.render(project_path)


if __name__ == "__main__":
    main()
