from __future__ import annotations

from datetime import date

import streamlit as st

from viewer.components.operations_home import build_operations_home_state, render_operations_home


st.set_page_config(page_title="Operations Center", layout="wide")
st.sidebar.header("Operations Center")

db_path = st.sidebar.text_input("scheduler DB path", value="")
profile_label_to_value = {
    "공무": "field_admin",
    "현장소장": "site_manager",
    "본사/관리": "hq",
    "관리자/개발자": "developer",
}
profile_label = st.sidebar.selectbox("사용자 모드", list(profile_label_to_value))
as_of = st.sidebar.date_input("기준일", value=date.today())

if db_path:
    state = build_operations_home_state(
        db_path,
        profile=profile_label_to_value[str(profile_label)],
        as_of=as_of,
    )
    render_operations_home(state)
else:
    st.info("SQLite .scheduler DB path를 입력하세요.")
