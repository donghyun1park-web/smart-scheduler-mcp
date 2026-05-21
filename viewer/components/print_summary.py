"""A4 1매 인쇄용 요약 컴포넌트 (A·E 페르소나).

회의에 들고 갈 한 장짜리 인쇄물:
- 프로젝트명 / 준공 예정일 / 데이터 건강점수
- 계획 vs 실적 진행률 / 부진공정 수 / 오늘 일정
- Critical Path TOP 10
- 공종별 비용 합계
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from core import db
from core.dashboard import generate_site_briefing
from core.data_health import check_data_health
from core.progress import get_today_schedule_summary


def build_one_page_summary(
    db_path: str | Path,
    *,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Aggregate the data needed for a single A4 page in one call."""
    today = as_of or date.today()
    try:
        briefing = generate_site_briefing(db_path, as_of=today)
    except Exception as exc:  # noqa: BLE001
        briefing = {"ok": False, "error": str(exc)}
    try:
        health = check_data_health(db_path, as_of=today).to_dict()
    except Exception as exc:  # noqa: BLE001
        health = {"score": 0, "status": "error", "summary_ko": str(exc)}
    try:
        today_schedule = get_today_schedule_summary(db_path, as_of=today)
    except Exception:  # noqa: BLE001
        today_schedule = {"starts_today_count": 0, "finishes_today_count": 0, "overdue_start_count": 0}

    # Critical Path TOP 10 from activities flagged is_critical, ordered by ES.
    activities = db.list_activities(db_path)
    critical = sorted(
        (a for a in activities if a.is_critical),
        key=lambda a: (a.es_workday if a.es_workday is not None else 0, a.code),
    )[:10]

    # Cost by discipline (one-pass aggregate).
    cost_by_disc: dict[str, float] = {}
    for a in activities:
        cost_by_disc[a.discipline] = cost_by_disc.get(a.discipline, 0.0) + float(a.cost or 0)
    cost_rows = sorted(cost_by_disc.items(), key=lambda kv: kv[1], reverse=True)

    return {
        "as_of": today.isoformat(),
        "briefing": briefing,
        "health": health,
        "today_schedule": today_schedule,
        "critical_top10": [
            {
                "code": a.code,
                "name": a.name,
                "discipline": a.discipline,
                "zone": a.zone,
                "duration": a.duration,
                "es_date": a.es_date.isoformat() if a.es_date else None,
                "ef_date": a.ef_date.isoformat() if a.ef_date else None,
            }
            for a in critical
        ],
        "cost_by_discipline": [{"discipline": d, "cost": c} for d, c in cost_rows],
        "total_cost": sum(cost_by_disc.values()),
        "activity_count": len(activities),
    }


def render_one_page_summary(state: dict[str, Any]) -> None:
    import streamlit as st

    # CSS: keep the whole panel within one A4 sheet when the user prints
    # via Ctrl+P. Hide Streamlit's sidebar / toolbar in print mode.
    st.markdown(
        """
        <style>
        @media print {
            section[data-testid="stSidebar"], header, footer, [data-testid="stToolbar"] { display: none !important; }
            .block-container { padding: 0 !important; max-width: 100% !important; }
            body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            h1, h2, h3 { page-break-after: avoid; }
            .one-page-card { font-size: 11px; }
        }
        .one-page-card { font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    briefing = dict(state.get("briefing") or {})
    health = dict(state.get("health") or {})
    today_sched = dict(state.get("today_schedule") or {})

    st.markdown(f"### 📄 {briefing.get('project_name', '프로젝트')} — 1매 요약")
    st.caption(f"기준일 {state.get('as_of')}  ·  활동 {state.get('activity_count', 0)}건")

    # Top KPI cards
    cols = st.columns(4)
    cols[0].metric("준공 (계획)", briefing.get("project_name") and "—" or "—")  # placeholder
    cols[0].metric("상태", briefing.get("status", "?"))
    cols[1].metric("계획 진행률", f"{briefing.get('overall_planned_pct', 0):.1f}%")
    cols[2].metric("실적 진행률", f"{briefing.get('overall_actual_pct', 0):.1f}%",
                   delta=f"{briefing.get('progress_gap_pct', 0):+.1f}%p")
    cols[3].metric("데이터 건강", f"{health.get('score', 0)}점", help=str(health.get("status", "")))

    cols = st.columns(3)
    cols[0].metric("오늘 착수", f"{today_sched.get('starts_today_count', 0)}건")
    cols[1].metric("오늘 완료", f"{today_sched.get('finishes_today_count', 0)}건")
    cols[2].metric("미착수 지연", f"{today_sched.get('overdue_start_count', 0)}건")

    st.markdown(f"**한 줄 요약**: {briefing.get('briefing', '데이터가 부족합니다.')}")

    # Critical Path table
    st.markdown("#### Critical Path TOP 10")
    cp_rows = state.get("critical_top10") or []
    if cp_rows:
        st.dataframe(cp_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Critical Path 정보가 없습니다. (calculate_cpm 실행 필요)")

    # Cost by discipline
    st.markdown("#### 공종별 비용 합계")
    rows = state.get("cost_by_discipline") or []
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption(f"총 비용 합계: {state.get('total_cost', 0):,.0f}원")
    else:
        st.info("비용 데이터가 없습니다.")

    st.caption("브라우저에서 Ctrl+P (또는 ⌘P)로 인쇄하면 사이드바·툴바가 자동으로 숨겨집니다.")
