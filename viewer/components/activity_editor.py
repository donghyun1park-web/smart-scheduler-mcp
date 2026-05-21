from __future__ import annotations

import uuid
from dataclasses import replace
from pathlib import Path

from core import db
from core.models import ALLOWED_DISCIPLINES, Activity


def add_activity_from_form(
    project_path: str | Path,
    code: str,
    name: str,
    wbs_id: str,
    discipline: str,
    zone: str,
    duration: int,
    cost: float,
) -> Activity:
    return db.add_activity(
        project_path,
        Activity(str(uuid.uuid4()), code, name, wbs_id, discipline, zone, duration, cost),
    )


def update_activity_from_form(
    project_path: str | Path,
    activity_id: str,
    code: str,
    name: str,
    wbs_id: str,
    discipline: str,
    zone: str,
    duration: int,
    cost: float,
) -> Activity:
    existing = {activity.activity_id: activity for activity in db.list_activities(project_path)}
    current = existing[activity_id]
    return db.update_activity(
        project_path,
        replace(
            current,
            code=code,
            name=name,
            wbs_id=wbs_id,
            discipline=discipline,
            zone=zone,
            duration=duration,
            cost=cost,
        ),
    )


def update_activity_progress(
    project_path: str | Path,
    activity_id: str,
    progress_pct: float,
) -> Activity:
    """Quick-set a single activity's progress percentage (0–100)."""
    existing = {activity.activity_id: activity for activity in db.list_activities(project_path)}
    return db.update_activity(
        project_path,
        replace(existing[activity_id], progress_pct=float(progress_pct)),
    )


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("Activities")
    activities = db.list_activities(project_path)
    st.data_editor([activity.__dict__ for activity in activities], use_container_width=True)

    if activities:
        with st.expander("⚡ 진행률 빠른 입력 (현장 보고)", expanded=False):
            options = {f"{a.code} — {a.name} ({a.progress_pct:.0f}%)": a for a in activities}
            label = st.selectbox("작업 선택", list(options.keys()), key="quick_prog_select")
            target = options[label]
            new_pct = st.slider(
                "진행률 %",
                min_value=0,
                max_value=100,
                value=int(round(target.progress_pct)),
                step=5,
                key="quick_prog_slider",
            )
            if st.button("저장", type="primary", key="quick_prog_save"):
                update_activity_progress(project_path, target.activity_id, float(new_pct))
                st.success(f"{target.code} 진행률을 {new_pct}%로 저장했습니다.")
                st.rerun()
            st.caption("일일 보고(DailyRecord)가 있으면 그 값이 우선됩니다. "
                       "이 슬라이더는 일보가 없을 때 현장소장이 감으로 입력하는 용도입니다.")

    wbs_items = db.list_wbs(project_path)
    wbs_options = [item.wbs_id for item in wbs_items]
    with st.form("add_activity"):
        code = st.text_input("Code")
        name = st.text_input("Name")
        wbs_id = st.selectbox("WBS", wbs_options) if wbs_options else st.text_input("WBS ID")
        discipline = st.selectbox("Discipline", sorted(ALLOWED_DISCIPLINES))
        zone = st.text_input("Zone")
        duration = st.number_input("Duration", min_value=0, step=1)
        cost = st.number_input("Cost", min_value=0.0, step=1000.0)
        if st.form_submit_button("Add Activity") and code and name and wbs_id:
            add_activity_from_form(
                project_path,
                code,
                name,
                str(wbs_id),
                discipline,
                zone,
                int(duration),
                float(cost),
            )
            st.rerun()
