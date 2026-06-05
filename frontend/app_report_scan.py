"""공사일보 스캔 → 자동 데이터 추출 앱 (Streamlit).

사용법:
  - 📷 탭: 핸드폰 카메라로 일보 직접 촬영
  - 📁 탭: Excel 또는 사진 파일 업로드
  → AI가 자동 인식 → 수정 가능 폼 → DB 저장

URL: http://NAS_IP:8502
"""
from __future__ import annotations

import json
import os
from datetime import date

import requests
import streamlit as st

st.set_page_config(
    page_title="공사일보 스캔",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

API_URL = os.environ.get("API_URL", "http://localhost:8000")
DEFAULT_DB = os.environ.get("DEFAULT_DB_PATH", "/data/현장.scheduler")

# ─── 사이드바: DB 경로 설정 ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    db_path = st.text_input(
        ".scheduler DB 경로",
        value=DEFAULT_DB,
        help="NAS 마운트 경로 또는 절대 경로",
    )

# ─── 헤더 ────────────────────────────────────────────────────────────────────
st.markdown("## 📋 공사일보 자동 스캔")
st.caption("협력업체 일보를 찍거나 업로드하면 AI가 자동으로 내용을 읽어드립니다.")
st.divider()

# ─── 파일 입력 탭 ─────────────────────────────────────────────────────────────
tab_cam, tab_file = st.tabs(["📷 카메라 촬영", "📁 파일 업로드"])

uploaded_file = None

with tab_cam:
    st.info("일보를 평평하게 놓고 찍어주세요. 글씨가 잘 보여야 합니다.")
    photo = st.camera_input("📷 일보 촬영")
    if photo:
        uploaded_file = photo

with tab_file:
    file_obj = st.file_uploader(
        "Excel 또는 사진 파일 선택",
        type=["xlsx", "jpg", "jpeg", "png", "webp"],
        help="★표준 출력일보 Excel 파일 또는 사진",
    )
    if file_obj:
        uploaded_file = file_obj

# ─── 파싱 실행 ────────────────────────────────────────────────────────────────
if uploaded_file is not None:
    st.divider()

    with st.spinner("🤖 AI가 일보를 읽는 중... (10~20초 소요)"):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data  = {"db_path": db_path}
            resp  = requests.post(f"{API_URL}/api/parse-daily-report", files=files, data=data, timeout=60)
            resp.raise_for_status()
            result = resp.json()
        except requests.exceptions.ConnectionError:
            st.error(f"❌ 서버 연결 실패 — API 서버가 켜져 있는지 확인하세요.\n`{API_URL}`")
            st.stop()
        except Exception as e:
            st.error(f"❌ 오류: {e}")
            st.stop()

    parsed = result.get("parsed", {})
    warnings = result.get("warnings", [])

    if warnings:
        for w in warnings:
            st.warning(f"⚠️ {w}")

    st.success("✅ 파싱 완료! 아래 내용을 확인·수정 후 저장하세요.")

    # ─── 수정 가능 폼 ─────────────────────────────────────────────────────────
    with st.form("confirm_form"):
        st.markdown("### 📝 파싱 결과 확인")

        col1, col2 = st.columns(2)
        with col1:
            work_date = st.date_input(
                "작업일",
                value=date.fromisoformat(parsed.get("work_date") or date.today().isoformat()),
            )
        with col2:
            team_name = st.text_input("협력사/팀명", value=parsed.get("team_name") or "")

        st.markdown("**작업 내용 요약**")
        summary = st.text_area(
            "요약 (수정 가능)",
            value=parsed.get("summary") or "",
            height=80,
        )

        # 작업현황
        work_items = parsed.get("work_items", [])
        if work_items:
            st.markdown("**작업현황**")
            work_text = "\n".join(
                f"{w.get('no','')}.  [{w.get('category','')}] {w.get('team','')} — {w.get('description','')}"
                for w in work_items if w.get("description")
            )
            st.text_area("작업 목록 (읽기용)", value=work_text, height=120, disabled=True)

        # 설비현황
        equipment = parsed.get("equipment", [])
        if equipment:
            st.markdown("**설비 현황**")
            eq_text = "\n".join(
                f"{e['name']}: 현황 {e.get('current_qty',0)} → 사용 {e.get('used_qty',0)} → 최종 {e.get('final_qty',0)}"
                for e in equipment if e.get("name")
            )
            st.text_area("설비 목록 (읽기용)", value=eq_text, height=100, disabled=True)

        # 물품현황
        supplies = parsed.get("supplies", [])
        if supplies:
            st.markdown("**물품 현황**")
            sup_text = "\n".join(
                f"{s['name']}: 현황 {s.get('current_qty',0)} → 사용 {s.get('used_qty',0)} → 최종 {s.get('final_qty',0)}"
                for s in supplies if s.get("name")
            )
            st.text_area("물품 목록 (읽기용)", value=sup_text, height=80, disabled=True)

        st.divider()

        # 연결 활동 선택 (DB에서 활동 목록 가져오기)
        st.markdown("**📌 연결할 공정 활동**")

        @st.cache_data(ttl=60)
        def fetch_all_activities(db: str) -> list[dict]:
            try:
                r = requests.get(f"{API_URL}/api/activities", params={"db_path": db}, timeout=5)
                r.raise_for_status()
                return r.json()
            except Exception:
                return []

        all_acts = fetch_all_activities(db_path)
        act_labels = ["(선택 안 함)"] + [f"[{a['discipline']}] {a['label']}" for a in all_acts]

        selected_label = st.selectbox(
            "이 일보의 데이터를 저장할 활동 선택",
            options=act_labels,
            help="선택하면 해당 활동의 daily_record에 저장됩니다.",
        )

        workers_input = st.number_input(
            "투입 인원 (명)",
            min_value=0,
            value=max(len(work_items), 0),
        )

        submitted = st.form_submit_button("✅ DB에 저장", use_container_width=True, type="primary")

    # ─── 저장 처리 ───────────────────────────────────────────────────────────
    if submitted:
        if selected_label == "(선택 안 함)":
            st.warning("저장할 활동을 선택해주세요.")
        else:
            # 선택된 활동 ID 찾기
            selected_act = next(
                (a for a in all_acts if f"[{a['discipline']}] {a['label']}" == selected_label),
                None,
            )
            if not selected_act:
                st.error("활동을 찾을 수 없습니다.")
            else:
                # remarks 구성 (팀명 + 요약 + 설비/물품 요약)
                remarks_parts = [f"[{team_name}]" if team_name else "", summary]
                if equipment:
                    eq_summary = ", ".join(
                        f"{e['name']}({e.get('used_qty',0)}사용)"
                        for e in equipment[:5] if e.get("name")
                    )
                    remarks_parts.append(f"설비: {eq_summary}")
                remarks = "\n".join(p for p in remarks_parts if p)

                payload = {
                    "db_path":      db_path,
                    "activity_id":  selected_act["activity_id"],
                    "work_date":    work_date.isoformat(),
                    "progress_pct": 0.0,   # 일보에서는 진행률 별도 미포함
                    "workers":      int(workers_input),
                    "remarks":      remarks[:500],   # DB 제한 내
                }
                try:
                    r = requests.post(f"{API_URL}/api/daily-record", json=payload, timeout=5)
                    r.raise_for_status()
                    data = r.json()
                    if data.get("ok"):
                        st.success(f"✅ 저장 완료! record_id: `{data.get('record_id','')[:8]}…`")
                        st.balloons()
                    else:
                        st.error("저장 실패. 다시 시도해주세요.")
                except Exception as e:
                    st.error(f"❌ 저장 오류: {e}")

    # ─── 원본 JSON 보기 (디버그) ─────────────────────────────────────────────
    with st.expander("🔍 원본 파싱 JSON 보기"):
        st.json(parsed)

# ─── 하단 안내 ────────────────────────────────────────────────────────────────
st.divider()
st.caption("📌 이 페이지 URL: `http://NAS_IP:8502`")
st.caption("💡 Tip: 일보를 밝은 곳에서 평평하게 찍으면 인식률이 높아집니다.")
