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

    from viewer.components import ui_kit

    ui_kit.inject_global_css()

    briefing = dict(state.get("briefing") or {})
    health = dict(state.get("health") or {})
    today_sched = dict(state.get("today_schedule") or {})

    project_name = briefing.get("project_name", "프로젝트")
    ui_kit.hero(
        project_name,
        subtitle=f"📅 {state.get('as_of')}  ·  🧱 활동 {state.get('activity_count', 0):,}건  ·  현장 1매 요약",
        icon="📄",
    )

    # ── 핵심 KPI 4개 ───────────────────────────────────────────────
    cols = st.columns(4)
    with cols[0]:
        st.markdown("**🚦 상태**")
        st.markdown(ui_kit.status_pill(briefing.get("status", "-")), unsafe_allow_html=True)
    cols[1].metric("📋 계획 진행률", f"{briefing.get('overall_planned_pct', 0):.1f}%")
    gap = briefing.get("progress_gap_pct", 0)
    cols[2].metric(
        "✅ 실적 진행률",
        f"{briefing.get('overall_actual_pct', 0):.1f}%",
        delta=f"{gap:+.1f}%p",
        delta_color="normal" if gap >= 0 else "inverse",
    )
    cols[3].metric("📊 데이터 건강", f"{health.get('score', 0)}점", str(health.get("status", "")))

    # ── 오늘 일정 3개 ──────────────────────────────────────────────
    cols = st.columns(3)
    cols[0].metric("🟢 오늘 착수", f"{today_sched.get('starts_today_count', 0)}건")
    cols[1].metric("✅ 오늘 완료", f"{today_sched.get('finishes_today_count', 0)}건")
    overdue = today_sched.get("overdue_start_count", 0)
    cols[2].metric(
        "🔴 미착수 지연",
        f"{overdue}건",
        delta="확인 필요" if overdue > 0 else "없음",
        delta_color="inverse" if overdue > 0 else "normal",
    )

    # ── 한 줄 요약 callout ─────────────────────────────────────────
    status_level = (briefing.get("status_level") or "blue").lower()
    callout_kind = {"green": "success", "yellow": "warning", "red": "danger"}.get(status_level, "info")
    ui_kit.callout(callout_kind, briefing.get("briefing", "데이터가 부족합니다."), title="한 줄 요약")

    # ── Critical Path TOP 10 ────────────────────────────────────────
    with ui_kit.card("Critical Path TOP 10", icon="🎯", subtitle="공기를 결정하는 핵심 활동"):
        cp_rows = state.get("critical_top10") or []
        if cp_rows:
            st.dataframe(cp_rows, use_container_width=True, hide_index=True)
        else:
            ui_kit.callout("warning", "Critical Path 정보가 없습니다. CPM 계산을 먼저 실행하세요.")

    # ── 공종별 비용 ────────────────────────────────────────────────
    with ui_kit.card("공종별 비용 합계", icon="💰", subtitle="MEP 공종 단위 직접공사비"):
        rows = state.get("cost_by_discipline") or []
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.markdown(
                f"<div style='text-align:right; font-weight:700; color:#1A2540; padding:6px 0;'>"
                f"총합 {state.get('total_cost', 0):,.0f} 원</div>",
                unsafe_allow_html=True,
            )
        else:
            ui_kit.callout("info", "비용 데이터가 없습니다. 실행예산 Excel을 가져오세요.")

    st.caption("💡 브라우저에서 `Ctrl+P` (또는 `⌘P`)로 인쇄하면 사이드바·툴바가 자동으로 숨겨집니다.")
