from __future__ import annotations

import streamlit as st

from core import db
from core.notifications import update_activity_status

st.set_page_config(
    page_title="자동 알림 시뮬레이터 · Smart Scheduler",
    page_icon="🔔",
    layout="wide",
)

st.title("🔔 자동 알림 및 의존성 시뮬레이터")
st.markdown(
    """
    현장 담당자가 모바일 퀵폼에서 상태를 변경할 때, 
    백엔드의 `relationships` 구조를 타고 어떻게 후행 공정에게 알림 로그가 적재되는지 테스트하는 가상 대시보드입니다.
    """
)

with st.sidebar:
    st.markdown("### 🔧 설정")
    db_path = st.text_input(".scheduler DB 경로", value="")

if not db_path:
    st.info("왼쪽 사이드바에 `.scheduler` DB 경로를 입력해주세요.")
    st.stop()

# --- 1. Load Data ---
try:
    activities = db.list_activities(db_path)
    relationships = db.list_relationships(db_path)
    logs = db.list_notification_logs(db_path)
except Exception as e:
    st.error(f"DB 로드 중 오류가 발생했습니다: {e}")
    st.stop()

st.divider()

col1, col2 = st.columns([1, 1])

# --- 2. Action Area ---
with col1:
    st.subheader("1. 액티비티 상태 변경 (Micro-Input Simulation)")
    st.write("선행 공정(예: 건축 골조)의 상태를 [완료] 또는 [지연]으로 변경해보세요.")

    # Show only some activities for simulation
    for act in activities[:15]:
        with st.container():
            c_name, c_btn1, c_btn2, c_status = st.columns([4, 2, 2, 2])
            c_name.write(f"**[{act.discipline}]** {act.name}")
            
            if c_btn1.button("✅ 완료 처리", key=f"done_{act.activity_id}"):
                update_activity_status(db_path, act.activity_id, "DONE")
                st.rerun()
                
            if c_btn2.button("⚠️ 3일 지연", key=f"delay_{act.activity_id}"):
                update_activity_status(db_path, act.activity_id, "DELAYED", delayed_days=3)
                st.rerun()
                
            status_color = "green" if act.status == "DONE" else "red" if act.status == "DELAYED" else "gray"
            c_status.markdown(f":{status_color}[{act.status}]")

# --- 3. Log Area ---
with col2:
    st.subheader("2. 백엔드 알림 로그 (Notification Dispatcher)")
    st.write("위에서 상태를 변경하면 연관된 후행 공정에 자동으로 생성된 메시지가 나타납니다.")
    
    if not logs:
        st.info("아직 생성된 알림 로그가 없습니다.")
    else:
        for log in logs:
            if log.notification_type == "READY":
                st.success(f"**To: {log.target_role}**\n\n{log.message}")
            else:
                st.warning(f"**To: {log.target_role}**\n\n{log.message}")
                
st.divider()

# --- 4. Graph View ---
st.subheader("3. 의존성 매핑 (Dependency Table)")
st.write("시스템이 백엔드에서 참고하는 선후행 관계 테이블(`relationships`)입니다.")
rel_data = []
act_map = {a.activity_id: a.name for a in activities}

for r in relationships:
    pred_name = act_map.get(r.pred_id, r.pred_id)
    succ_name = act_map.get(r.succ_id, r.succ_id)
    rel_data.append({"선행 (Predecessor)": pred_name, "관계": r.rel_type, "후행 (Successor)": succ_name})

if rel_data:
    st.dataframe(rel_data, use_container_width=True)
else:
    st.info("의존성 데이터가 없습니다.")
