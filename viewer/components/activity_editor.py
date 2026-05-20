from __future__ import annotations

import uuid
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
        Activity(
            activity_id,
            code,
            name,
            wbs_id,
            discipline,
            zone,
            duration,
            cost,
            current.es_workday,
            current.ef_workday,
            current.ls_workday,
            current.lf_workday,
            current.es_date,
            current.ef_date,
            current.total_float,
            current.is_critical,
        ),
    )


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("Activities")
    activities = db.list_activities(project_path)
    st.data_editor([activity.__dict__ for activity in activities], use_container_width=True)
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
