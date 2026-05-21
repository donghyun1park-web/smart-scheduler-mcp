"""A4 1매 인쇄용 요약 페이지."""
from __future__ import annotations

from datetime import date

import streamlit as st

from viewer.components.print_summary import build_one_page_summary, render_one_page_summary


st.set_page_config(page_title="1매 요약", layout="wide")
st.sidebar.header("1매 요약")

db_path = st.sidebar.text_input(".scheduler DB 경로", value="")
as_of = st.sidebar.date_input("기준일", value=date.today())

if not db_path:
    st.info("사이드바에 .scheduler DB 경로를 입력하세요.")
else:
    state = build_one_page_summary(db_path, as_of=as_of)
    render_one_page_summary(state)
