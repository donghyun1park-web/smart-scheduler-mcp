"""A4 1매 인쇄용 요약 페이지."""
from __future__ import annotations

from datetime import date

import streamlit as st

from viewer.components import ui_kit
from viewer.components.print_summary import build_one_page_summary, render_one_page_summary


st.set_page_config(
    page_title="1매 요약 · Smart Scheduler",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui_kit.inject_global_css()

with st.sidebar:
    st.markdown("### 📄 1매 요약")
    st.caption("회의에 들고 갈 A4 한 장")
    db_path = st.text_input(".scheduler DB 경로", value="")
    as_of = st.date_input("기준일", value=date.today())
    st.markdown("---")
    st.caption("💡 `Ctrl+P`로 인쇄하면 사이드바·툴바가 자동으로 숨겨집니다.")

if not db_path:
    ui_kit.hero("A4 1매 요약", subtitle="회의 들고 갈 한 장, 클릭 한 번에", icon="📄")
    ui_kit.callout("info", "왼쪽 사이드바에 <code>.scheduler</code> DB 경로를 입력하세요.")
else:
    state = build_one_page_summary(db_path, as_of=as_of)
    render_one_page_summary(state)
