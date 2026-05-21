"""Mobile quick-progress page (B persona: site supervisor on phone)."""
from __future__ import annotations

from datetime import date

import streamlit as st

from core import db
from tools.progress_tools import set_activity_progress
from viewer.components import ui_kit


st.set_page_config(
    page_title="진행률 빠른 입력",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed",
)
ui_kit.inject_global_css()
ui_kit.hero("진행률 빠른 입력", subtitle="폰 한 손 · 슬라이더 · 카톡 복사", icon="📱")

db_path = st.text_input("📁 .scheduler DB 경로", value=st.session_state.get("m_db_path", ""))
if db_path:
    st.session_state["m_db_path"] = db_path

if not db_path:
    ui_kit.callout("info", "DB 경로를 입력하세요. 예: <code>~/.smart-scheduler/projects/광명병원.scheduler</code>")
    st.stop()

try:
    activities = db.list_activities(db_path)
except Exception as exc:  # noqa: BLE001
    ui_kit.callout("danger", f"DB를 열지 못했습니다: {exc}")
    st.stop()

if not activities:
    ui_kit.callout("warning", "아직 등록된 활동(Activity)이 없습니다. 메인 페이지에서 먼저 가져오세요.")
    st.stop()

# 공종 필터
all_disciplines = sorted({a.discipline for a in activities if a.discipline})
selected_disc = st.selectbox("🔍 공종 필터", ["전체"] + all_disciplines)
visible = [a for a in activities if selected_disc == "전체" or a.discipline == selected_disc]

if not visible:
    ui_kit.callout("info", "해당 공종에 활동이 없습니다.")
    st.stop()

options = {f"{a.code} · {a.name} ({a.zone or '-'}) · {a.progress_pct:.0f}%": a for a in visible}
label = st.selectbox("📝 작업 선택", list(options.keys()))
target = options[label]

with ui_kit.card(f"{target.code} · {target.name}", icon="🧱"):
    meta_html = (
        f"<div style='color:#64748B; font-size:0.88rem; margin:4px 0;'>"
        f"공종 <strong>{target.discipline}</strong>  ·  Zone <strong>{target.zone or '-'}</strong>  ·  "
        f"계획 {target.es_date or '?'} ~ {target.ef_date or '?'}</div>"
    )
    st.markdown(meta_html, unsafe_allow_html=True)
    st.markdown(
        f"<div style='display:flex; align-items:center; gap:10px; margin:6px 0;'>"
        f"<strong>현재 진행률</strong>  {ui_kit.badge(f'{target.progress_pct:.0f}%', 'blue')}</div>",
        unsafe_allow_html=True,
    )

    new_pct = st.slider("📊 새 진행률 (%)", min_value=0, max_value=100, value=int(round(target.progress_pct)), step=5)

    col_save, col_copy = st.columns(2)
    with col_save:
        if st.button("💾 저장", type="primary", use_container_width=True):
            result = set_activity_progress(db_path, target.activity_id, float(new_pct))
            if result.get("ok"):
                st.success(f"✅ {target.code} → {new_pct}% 저장 완료")
                st.rerun()
            else:
                st.error(result.get("error_message", "저장에 실패했습니다."))

    with col_copy:
        msg = (
            f"[{date.today().isoformat()}] {target.discipline}/{target.zone or '-'} "
            f"{target.code} {target.name} — 진행률 {new_pct}%"
        )
        if st.button("📋 카톡 메시지 만들기", use_container_width=True):
            st.session_state["m_copy_msg"] = msg

if st.session_state.get("m_copy_msg"):
    with ui_kit.card("카톡 메시지", icon="💬", subtitle="박스 우측 상단 복사 아이콘 → 카톡에 붙여넣기"):
        st.code(st.session_state["m_copy_msg"], language="text")
