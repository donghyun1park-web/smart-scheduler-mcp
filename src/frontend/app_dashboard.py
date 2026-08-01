import streamlit as st
import requests

st.set_page_config(page_title="현장소장 대시보드", layout="wide")

API_URL = "http://localhost:8000"

st.title("🏗️ 현장소장 종합 대시보드 (Macro-View)")
st.write("FastAPI 백엔드에서 집계된 현장 요약 데이터를 실시간으로 보여줍니다.")

with st.sidebar:
    st.markdown("### 🔧 설정")
    db_path = st.text_input(".scheduler DB 경로", value="demo.scheduler")
    if st.button("새로고침"):
        st.rerun()

try:
    response = requests.get(f"{API_URL}/api/dashboard-data", params={"db_path": db_path})
    if response.status_code == 200:
        data = response.json()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("계획 공정률", f"{data['planned_progress']}%")
        col2.metric("실제 공정률", f"{data['overall_progress']}%", f"{data['overall_progress'] - data['planned_progress']}%")
        col3.metric("현장 상태", data['status'])
        
        st.subheader("⚠️ 최근 알림 및 지연 경고")
        for alert in data.get("recent_alerts", []):
            st.warning(alert)
            
    else:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {response.text}")
except Exception as e:
    st.error(f"백엔드 서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인하세요.\n\n오류: {e}")
