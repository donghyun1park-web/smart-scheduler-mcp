"""모바일 현장 실적 입력 폼 (Streamlit).

URL 파라미터:
  discipline : 공종 (건축 / 기계설비 / 전기설비 / 토목)  기본값 = 건축
  db         : .scheduler 파일 경로                       기본값 = /data/현장.scheduler

사용 예:
  http://NAS_IP:8501?discipline=건축&db=/data/홍은동.scheduler
"""
from __future__ import annotations

import os
from datetime import date

import requests
import streamlit as st

# ─── 기본 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="현장 실적 입력",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

API_URL = os.environ.get("API_URL", "http://localhost:8000")
DEFAULT_DB = os.environ.get("DEFAULT_DB_PATH", "/data/현장.scheduler")

# ─── URL 파라미터 수신 ────────────────────────────────────────────────────────
params = st.query_params
discipline = params.get("discipline", "건축")
db_path    = params.get("db", DEFAULT_DB)

DISCIPLINE_EMOJI = {
    "건축":   "🏗️",
    "기계설비": "⚙️",
    "전기설비": "⚡",
    "토목":   "🚜",
    "소방설비": "🔥",
}
emoji = DISCIPLINE_EMOJI.get(discipline, "📋")

# ─── 헤더 ────────────────────────────────────────────────────────────────────
st.markdown(f"## {emoji}  {discipline} 담당 — 오늘 실적 입력")
st.caption(f"📅 {date.today().strftime('%Y년 %m월 %d일')}  |  DB: `{db_path}`")
st.divider()


# ─── 활동 목록 가져오기 ────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_activities(disc: str, db: str) -> list[dict]:
    try:
        r = requests.get(
            f"{API_URL}/api/activities",
            params={"discipline": disc, "db_path": db},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return []


activities = fetch_activities(discipline, db_path)

if not activities:
    st.warning("⚠️  진행 중인 활동이 없거나 서버에 연결할 수 없습니다.")
    st.info(f"서버 주소: `{API_URL}`  |  DB: `{db_path}`")
    st.stop()

# ─── 활동 선택 ────────────────────────────────────────────────────────────────
labels      = [a["label"] for a in activities]
activity_id = None

selected_label = st.selectbox(
    "📌 오늘 작업한 활동 선택",
    options=labels,
    help="오늘 기준으로 진행 중인 활동만 표시됩니다.",
)

selected = next((a for a in activities if a["label"] == selected_label), None)
if selected:
    activity_id = selected["activity_id"]
    prev_pct    = int(selected.get("progress_pct") or 0)
    st.caption(f"코드: `{selected['code']}`  |  현재 진행률: **{prev_pct}%**")

st.divider()

# ─── 입력 폼 ──────────────────────────────────────────────────────────────────
with st.form("daily_input_form", clear_on_submit=True):
    progress = st.slider(
        "📊 오늘 기준 누적 진행률 (%)",
        min_value=0,
        max_value=100,
        value=max(prev_pct, 0) if selected else 0,
        step=5,
        help="오늘까지 누적 완료된 비율을 입력하세요.",
    )

    workers = st.number_input(
        "👷 오늘 투입 인원 (명)",
        min_value=0,
        max_value=500,
        value=0,
        step=1,
    )

    remarks = st.text_area(
        "📝 특이사항 (선택)",
        height=80,
        placeholder="예: 우천으로 오후 작업 중단, 자재 미도착 등",
        max_chars=300,
    )

    submitted = st.form_submit_button(
        "✅  오늘 실적 제출",
        use_container_width=True,
        type="primary",
    )

# ─── 제출 처리 ────────────────────────────────────────────────────────────────
if submitted:
    if not activity_id:
        st.error("활동을 선택해주세요.")
    else:
        payload = {
            "db_path":      db_path,
            "activity_id":  activity_id,
            "work_date":    date.today().isoformat(),
            "progress_pct": float(progress),
            "workers":      int(workers),
            "remarks":      remarks.strip(),
        }
        try:
            r = requests.post(f"{API_URL}/api/daily-record", json=payload, timeout=5)
            r.raise_for_status()
            data = r.json()
            if data.get("ok"):
                st.success(f"✅  제출 완료! (record_id: `{data.get('record_id', '')[:8]}…`)")
                st.balloons()
                # 캐시 초기화 → 다음 접속 시 최신 진행률 반영
                fetch_activities.clear()
            else:
                st.error("저장에 실패했습니다. 다시 시도해주세요.")
        except requests.exceptions.ConnectionError:
            st.error(f"❌  서버 연결 실패. NAS가 켜져 있는지 확인하세요.\n\n`{API_URL}`")
        except Exception as e:
            st.error(f"❌  오류: {e}")

# ─── 하단 안내 ────────────────────────────────────────────────────────────────
st.divider()
st.caption("📌 **북마크 저장 방법**: 브라우저 주소창 → 공유 → 홈 화면에 추가")
st.caption(f"공종 바꾸려면 URL에서 `discipline=건축` 부분을 변경하세요.")
