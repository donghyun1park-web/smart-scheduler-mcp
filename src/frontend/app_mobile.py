"""모바일 현장 실적 입력 — 공사일보 촬영 우선 방식 (v3.3).

3단계 UX:
  STEP 1 — 공사일보 촬영 (카메라/파일) 또는 직접 입력
  STEP 2 — AI 추출 결과 확인/수정 (또는 수동 입력)
  STEP 3 — 제출 완료

URL 파라미터:
  discipline : 공종 (건축 / 기계설비 / 전기설비 / 토목)   기본값 = 건축
  db         : .scheduler 파일 경로                        기본값 = /data/현장.scheduler

기존 app_report_scan.py(port 8502) 기능 통합 — 별도 앱 불필요.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any

import requests
import streamlit as st

# ─── 기본 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="현장 실적 입력",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

API_URL    = os.environ.get("API_URL", "http://localhost:8000")
DEFAULT_DB = os.environ.get("DEFAULT_DB_PATH", "/data/현장.scheduler")

# URL 파라미터
params     = st.query_params
discipline = params.get("discipline", "건축")
db_path    = params.get("db", DEFAULT_DB)

DISCIPLINE_EMOJI = {
    "건축": "🏗️", "기계설비": "⚙️", "전기설비": "⚡",
    "토목": "🚜",  "소방설비": "🔥",
}
emoji = DISCIPLINE_EMOJI.get(discipline, "📋")

# ─── 세션 상태 초기화 ─────────────────────────────────────────────────────────
def _init_state() -> None:
    defaults: dict[str, Any] = {
        "step":        1,        # 1 | 2 | 3
        "mode":        "scan",   # "scan" | "manual"
        "parsed":      {},       # API 파싱 결과
        "ai_fields":   set(),    # AI가 채운 필드명 집합
        "edited_fields": set(),  # 사용자가 수정한 필드명 집합
        "scan_warnings": [],     # 파싱 경고
        "confidence":  None,     # AI 신뢰도 (0~100)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ─── 헬퍼 ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_activities(disc: str | None, db: str) -> list[dict]:
    try:
        params_req: dict[str, str] = {"db_path": db}
        if disc:
            params_req["discipline"] = disc
        r = requests.get(f"{API_URL}/api/activities", params=params_req, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def _badge_ai(field: str) -> str:
    """AI 자동입력 또는 수정됨 배지 텍스트 반환."""
    if field in st.session_state.edited_fields:
        return "  ✏️ *수정됨*"
    if field in st.session_state.ai_fields:
        return "  🤖 *AI*"
    return ""


def _mark_edited(field: str) -> None:
    st.session_state.edited_fields.add(field)


def _go_step(n: int) -> None:
    st.session_state.step = n


def _reset() -> None:
    for k in ("parsed", "ai_fields", "edited_fields", "scan_warnings", "confidence"):
        st.session_state[k] = {} if k == "parsed" else (set() if "fields" in k else ([] if k == "scan_warnings" else None))
    st.session_state.step = 1
    st.session_state.mode = "scan"


# ─── 공통 헤더 ────────────────────────────────────────────────────────────────
def _render_header() -> None:
    st.markdown(
        f"""<div style='text-align:center;padding:4px 0 2px'>
        <span style='font-size:22px;font-weight:800'>📋 오늘 실적 입력</span><br>
        <span style='font-size:12px;color:#888'>홍은동 355번지 · {emoji} {discipline} · {date.today().strftime("%Y년 %m월 %d일")}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_steps(current: int) -> None:
    """스텝 인디케이터."""
    labels = ["1️⃣ 일보 촬영", "2️⃣ AI 확인", "3️⃣ 제출"]
    cols   = st.columns(3)
    for i, (col, label) in enumerate(zip(cols, labels), start=1):
        with col:
            if i < current:
                st.success(label, icon="✅")
            elif i == current:
                st.info(label, icon="▶️")
            else:
                st.caption(f"  {label}")


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — 공사일보 촬영 / 파일 업로드
# ══════════════════════════════════════════════════════════════════════════════
def render_step1() -> None:
    _render_header()
    _render_steps(1)
    st.divider()

    # ── 카메라 (최우선) ──────────────────────────────────────────────────────
    st.markdown("### 📷 공사일보를 찍어주세요")
    st.caption("협력업체로부터 받은 일보를 카메라로 찍으면 AI가 자동으로 내용을 채워드립니다.")

    photo = st.camera_input(
        "일보 촬영",
        label_visibility="collapsed",
    )

    st.markdown("**또는**")

    file_obj = st.file_uploader(
        "📁 파일 선택 (Excel · JPG · PNG · PDF)",
        type=["xlsx", "jpg", "jpeg", "png", "webp"],
        label_visibility="visible",
    )

    uploaded = photo or file_obj

    # ── 파일 있으면 → AI 파싱 후 STEP 2 ────────────────────────────────────
    if uploaded is not None:
        with st.spinner("🤖 AI가 일보를 읽는 중... (10~20초)"):
            try:
                files = {
                    "file": (
                        getattr(uploaded, "name", "photo.jpg"),
                        uploaded.getvalue(),
                        getattr(uploaded, "type", "image/jpeg"),
                    )
                }
                resp = requests.post(
                    f"{API_URL}/api/parse-daily-report",
                    files=files,
                    data={"db_path": db_path},
                    timeout=60,
                )
                resp.raise_for_status()
                result = resp.json()

                parsed   = result.get("parsed", {})
                warnings = result.get("warnings", [])

                # AI가 채운 필드 기록
                ai_fields: set[str] = set()
                for field in ("work_date", "workers", "summary", "progress_pct"):
                    if parsed.get(field) not in (None, "", 0):
                        ai_fields.add(field)
                if parsed.get("work_items"):
                    ai_fields.add("activity")

                st.session_state.parsed        = parsed
                st.session_state.ai_fields     = ai_fields
                st.session_state.edited_fields = set()
                st.session_state.scan_warnings = warnings
                st.session_state.mode          = "scan"
                # 신뢰도: warnings 없으면 94, 있으면 낮춤
                st.session_state.confidence    = max(60, 94 - len(warnings) * 10)
                _go_step(2)
                st.rerun()

            except requests.exceptions.ConnectionError:
                st.error(f"❌ 서버 연결 실패 — API 서버를 확인하세요.\n`{API_URL}`")
            except Exception as e:
                st.error(f"❌ 파싱 오류: {e}")

    st.divider()

    # ── 직접 입력 (보조 수단) ────────────────────────────────────────────────
    if st.button("📝 일보 없이 직접 입력하기", use_container_width=False, type="secondary"):
        st.session_state.mode   = "manual"
        st.session_state.parsed = {}
        st.session_state.ai_fields     = set()
        st.session_state.edited_fields = set()
        _go_step(2)
        st.rerun()

    # ── 오늘 입력 현황 ───────────────────────────────────────────────────────
    with st.expander("📅 오늘 입력 현황", expanded=False):
        acts = fetch_activities(discipline, db_path)
        if acts:
            act = acts[0]
            prev_pct = int(act.get("progress_pct") or 0)
            st.write(f"- **작업일**: {date.today().strftime('%Y년 %m월 %d일')}")
            st.write(f"- **어제 실적**: 진행률 {prev_pct}%")
            st.write(f"- **오늘 제출**: ⏳ 미제출")
        else:
            st.caption("서버 연결 안 됨 — 나중에 확인하세요.")


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — AI 결과 확인/수정 (또는 수동 입력)
# ══════════════════════════════════════════════════════════════════════════════
def render_step2() -> None:
    _render_header()
    _render_steps(2)
    st.divider()

    parsed    = st.session_state.parsed
    is_scan   = st.session_state.mode == "scan"
    conf      = st.session_state.confidence
    warnings  = st.session_state.scan_warnings

    # ── AI 파싱 결과 배너 ─────────────────────────────────────────────────
    if is_scan:
        st.success(
            f"✅ **AI 자동 추출 완료** — 일보에서 내용을 읽었습니다.  \n"
            f"신뢰도 **{conf}%** · 내용을 확인하고 필요시 수정 후 제출하세요.",
            icon="🤖",
        )
        for w in warnings:
            st.warning(f"⚠️ {w}")
    else:
        st.info("📝 직접 입력 모드 — 각 항목을 입력하세요.", icon="✏️")

    # ── 활동 목록 가져오기 ────────────────────────────────────────────────
    activities  = fetch_activities(discipline, db_path)
    act_labels  = [a["label"] for a in activities]
    prev_pct    = 0
    activity_id = None

    # AI가 추출한 작업내용으로 활동 자동 매칭 시도
    default_idx = 0
    if is_scan and parsed.get("work_items") and act_labels:
        first_desc = (parsed["work_items"][0].get("description") or "").lower()
        for i, lbl in enumerate(act_labels):
            if any(kw in lbl for kw in first_desc.split()[:3]):
                default_idx = i
                break

    # ── 입력 폼 ──────────────────────────────────────────────────────────
    with st.form("step2_form", clear_on_submit=False):

        # 활동 선택
        badge_act = _badge_ai("activity")
        selected_label = st.selectbox(
            f"📌 작업 항목{badge_act}",
            options=act_labels or ["(활동 없음 — 서버 연결 확인)"],
            index=default_idx,
        )
        selected = next((a for a in activities if a["label"] == selected_label), None)
        if selected:
            activity_id = selected["activity_id"]
            prev_pct    = int(selected.get("progress_pct") or 0)
            st.caption(f"코드: `{selected['code']}`  |  이전 진행률: **{prev_pct}%**")

        st.divider()

        # 진행률
        ai_pct = int(parsed.get("progress_pct") or prev_pct or 0)
        badge_pct = _badge_ai("progress_pct")
        progress = st.slider(
            f"📊 오늘 기준 누적 진행률 (%){badge_pct}",
            min_value=0, max_value=100,
            value=max(ai_pct, prev_pct),
            step=5,
            help="오늘까지 누적 완료 비율.",
        )

        # 투입 인원
        ai_workers = int(parsed.get("workers") or len(parsed.get("work_items") or []) or 0)
        badge_w    = _badge_ai("workers")
        workers = st.number_input(
            f"👷 오늘 투입 인원 (명){badge_w}",
            min_value=0, max_value=500,
            value=ai_workers,
            step=1,
        )

        # 작업 내용 / 특이사항
        ai_summary = parsed.get("summary") or ""
        badge_s    = _badge_ai("summary")
        remarks = st.text_area(
            f"📝 작업 내용 / 특이사항{badge_s}",
            value=ai_summary,
            height=90,
            placeholder="예: 우천으로 오후 작업 중단, 자재 미도착 등",
            max_chars=500,
        )

        # 일보 세부 내용 (read-only 요약)
        if is_scan and (parsed.get("work_items") or parsed.get("equipment")):
            with st.expander("🔍 일보에서 추출한 항목 확인"):
                work_items = parsed.get("work_items", [])
                if work_items:
                    st.markdown("**작업현황**")
                    for w in work_items:
                        desc = w.get("description") or ""
                        if desc:
                            st.markdown(f"- [{w.get('category','')}] {w.get('team','')} — {desc}")

                equipment = parsed.get("equipment", [])
                if equipment:
                    st.markdown("**설비현황**")
                    for e in equipment:
                        if e.get("name"):
                            st.markdown(
                                f"- {e['name']}: 현황 {e.get('current_qty',0)} → "
                                f"사용 {e.get('used_qty',0)} → 잔 {e.get('final_qty',0)}"
                            )

                supplies = parsed.get("supplies", [])
                if supplies:
                    st.markdown("**물품현황**")
                    for s in supplies:
                        if s.get("name"):
                            st.markdown(
                                f"- {s['name']}: 현황 {s.get('current_qty',0)} → "
                                f"사용 {s.get('used_qty',0)} → 잔 {s.get('final_qty',0)}"
                            )

        st.divider()

        col_submit, col_retake = st.columns([3, 1])
        with col_submit:
            submitted = st.form_submit_button(
                "✅  확인 완료 · 제출하기",
                use_container_width=True,
                type="primary",
            )
        with col_retake:
            retake = st.form_submit_button(
                "📷 다시\n찍기" if is_scan else "◀ 뒤로",
                use_container_width=True,
            )

    # ── 제출 처리 ─────────────────────────────────────────────────────────
    if retake:
        _reset()
        st.rerun()

    if submitted:
        if not activity_id:
            st.error("활동을 선택해주세요.")
            return

        # remarks에 설비/물품 요약 추가
        full_remarks = remarks.strip()
        equipment = parsed.get("equipment", [])
        if equipment:
            eq_summary = ", ".join(
                f"{e['name']}(사용{e.get('used_qty',0)})"
                for e in equipment[:5] if e.get("name")
            )
            full_remarks = (full_remarks + f"\n설비: {eq_summary}").strip()

        payload = {
            "db_path":      db_path,
            "activity_id":  activity_id,
            "work_date":    (
                parsed.get("work_date") or date.today().isoformat()
            ),
            "progress_pct": float(progress),
            "workers":      int(workers),
            "remarks":      full_remarks[:500],
        }
        try:
            r = requests.post(f"{API_URL}/api/daily-record", json=payload, timeout=5)
            r.raise_for_status()
            data = r.json()
            if data.get("ok"):
                st.session_state["_record_id"] = data.get("record_id", "")
                st.session_state["_progress"]  = progress
                st.session_state["_workers"]   = workers
                fetch_activities.clear()
                _go_step(3)
                st.rerun()
            else:
                st.error("저장에 실패했습니다. 다시 시도해주세요.")
        except requests.exceptions.ConnectionError:
            st.error(f"❌ 서버 연결 실패. NAS가 켜져 있는지 확인하세요.\n`{API_URL}`")
        except Exception as e:
            st.error(f"❌ 오류: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — 제출 완료
# ══════════════════════════════════════════════════════════════════════════════
def render_step3() -> None:
    _render_header()
    _render_steps(3)
    st.divider()

    record_id = st.session_state.get("_record_id", "")
    progress  = st.session_state.get("_progress", 0)
    workers   = st.session_state.get("_workers", 0)

    st.success("## ✅  오늘 실적 제출 완료!", icon="🎉")
    st.balloons()

    st.markdown(
        f"""
| 항목 | 내용 |
|------|------|
| 📊 진행률 | **{progress}%** |
| 👷 투입 인원 | **{workers}명** |
| 📅 작업일 | {date.today().strftime("%Y년 %m월 %d일")} |
| 🔑 Record ID | `{record_id[:12]}…` |
"""
    )

    st.caption("현장소장 대시보드에 실시간 반영됩니다.")
    st.divider()

    if st.button("📋 다음 실적 입력 (처음으로)", use_container_width=True, type="primary"):
        _reset()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  라우터
# ══════════════════════════════════════════════════════════════════════════════
step = st.session_state.step
if step == 1:
    render_step1()
elif step == 2:
    render_step2()
elif step == 3:
    render_step3()
