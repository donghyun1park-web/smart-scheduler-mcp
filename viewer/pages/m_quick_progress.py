"""Mobile quick-progress page (B persona: site supervisor on phone).

Single-screen Streamlit page sized for a phone browser. The supervisor:
  1. picks a .scheduler DB and an activity from a dropdown,
  2. drags the progress slider to the eyeball value (e.g. 70%),
  3. taps Save — the value lands in Activity.progress_pct via
     tools.progress_tools.set_activity_progress,
  4. taps "카톡 메시지 복사" to grab a one-line Korean status string
     they can paste into 카톡 / 메일.

No PWA / offline / push for now (deliberately out of scope per the
30-round review). Polished mobile UI lives in the Sprint-2 backlog.
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from core import db
from tools.progress_tools import set_activity_progress


st.set_page_config(page_title="진행률 빠른 입력", layout="centered")

st.title("📱 진행률 빠른 입력")
st.caption("폰에서 한 손으로 입력 → 저장 → 카톡 메시지 복사")

db_path = st.text_input(".scheduler DB 경로", value=st.session_state.get("m_db_path", ""))
if db_path:
    st.session_state["m_db_path"] = db_path

if not db_path:
    st.info("DB 경로를 입력하세요. 예: ~/.smart-scheduler/projects/광명병원.scheduler")
    st.stop()

try:
    activities = db.list_activities(db_path)
except Exception as exc:  # noqa: BLE001 - mobile UI must not crash
    st.error(f"DB를 열지 못했습니다: {exc}")
    st.stop()

if not activities:
    st.warning("아직 등록된 활동(Activity)이 없습니다.")
    st.stop()

# Discipline filter — keeps the dropdown short on phones with many activities.
all_disciplines = sorted({a.discipline for a in activities if a.discipline})
selected_disc = st.selectbox("공종 필터", ["전체"] + all_disciplines)
visible = [a for a in activities if selected_disc == "전체" or a.discipline == selected_disc]

if not visible:
    st.info("해당 공종에 활동이 없습니다.")
    st.stop()

options = {f"{a.code} — {a.name} ({a.zone or '-'}) · {a.progress_pct:.0f}%": a for a in visible}
label = st.selectbox("작업 선택", list(options.keys()))
target = options[label]

st.markdown(f"**선택**: `{target.code}` {target.name}")
if target.es_date or target.ef_date:
    st.caption(f"계획 {target.es_date or '?'} ~ {target.ef_date or '?'}  ·  공종 {target.discipline}  ·  Zone {target.zone or '-'}")

new_pct = st.slider("진행률 (%)", min_value=0, max_value=100, value=int(round(target.progress_pct)), step=5)

col_save, col_copy = st.columns(2)
with col_save:
    if st.button("💾 저장", type="primary", use_container_width=True):
        result = set_activity_progress(db_path, target.activity_id, float(new_pct))
        if result.get("ok"):
            st.success(f"저장 완료 — {target.code} {new_pct}%")
            st.rerun()
        else:
            st.error(result.get("error_message", "저장에 실패했습니다."))

with col_copy:
    msg = (
        f"[{date.today().isoformat()}] {target.discipline}/{target.zone or '-'} "
        f"{target.code} {target.name} — 진행률 {new_pct}%"
    )
    if st.button("📋 카톡 메시지 복사", use_container_width=True):
        st.code(msg, language="text")
        st.caption("위 박스 우측 상단 복사 아이콘으로 클립보드 복사 → 카톡에 붙여넣기")
