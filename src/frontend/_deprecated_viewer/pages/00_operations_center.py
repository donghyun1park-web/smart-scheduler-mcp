from __future__ import annotations

from datetime import date

import streamlit as st

from viewer.components import ui_kit
from viewer.components.operations_home import build_operations_home_state, render_operations_home


st.set_page_config(
    page_title="운영센터 · Smart Scheduler",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui_kit.inject_global_css()

ui_kit.hero(
    "운영센터",
    subtitle="현장 상태 한눈에 · 역할별 다음 행동 · EVM 쉬운 설명",
    icon="🎯",
)

# Sidebar — clean grouping
with st.sidebar:
    st.markdown("### 🔧 설정")
    db_path = st.text_input(".scheduler DB 경로", value="")
    st.markdown("---")
    profile_label_to_value = {
        "공무 (현장 사무)": "field_admin",
        "현장소장": "site_manager",
        "본사/관리": "hq",
        "관리자/개발자": "developer",
    }
    profile_label = st.selectbox("👤 사용자 모드", list(profile_label_to_value))
    as_of = st.date_input("📅 기준일", value=date.today())

if not db_path:
    ui_kit.callout(
        "info",
        "왼쪽 사이드바에 <code>.scheduler</code> DB 경로를 입력하면 진단·추천 행동·EVM 설명이 나타납니다.",
        title="DB 경로를 입력하세요",
    )
    with ui_kit.card("운영센터에서 할 수 있는 일", icon="✨"):
        st.markdown(
            """
            - **데이터 건강점수** — 누락된 공정·예산·일보 자동 진단
            - **다음 추천 행동** — 역할(공무/소장/본사/개발자)에 맞는 우선순위 3가지
            - **EVM 쉬운 설명** — PV/EV/AC, SPI/CPI를 한국어로 자동 해설
            - **워크플로우 상태** — 일일마감·주간보고 사전점검
            - **카톡/메일용 Markdown** — 보고서를 클릭 한 번에 복사
            """
        )
else:
    state = build_operations_home_state(
        db_path,
        profile=profile_label_to_value[str(profile_label)],
        as_of=as_of,
    )
    render_operations_home(state)
