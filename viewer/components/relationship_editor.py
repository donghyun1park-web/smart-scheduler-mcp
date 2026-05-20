from __future__ import annotations

import uuid
from pathlib import Path

from core import db
from core.models import Relationship


def add_relationship_from_form(
    project_path: str | Path,
    pred_id: str,
    succ_id: str,
    rel_type: str,
    lag_days: int,
) -> Relationship:
    return db.add_relationship(
        project_path,
        Relationship(str(uuid.uuid4()), pred_id, succ_id, rel_type, lag_days),
    )


def delete_relationship(project_path: str | Path, rel_id: str) -> None:
    db.delete_relationship(project_path, rel_id)


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("Relationships")
    relationships = db.list_relationships(project_path)
    st.dataframe([relationship.__dict__ for relationship in relationships], use_container_width=True)
    activities = db.list_activities(project_path)
    activity_options = [activity.activity_id for activity in activities]
    with st.form("add_relationship"):
        pred_id = st.selectbox("Predecessor", activity_options) if activity_options else ""
        succ_id = st.selectbox("Successor", activity_options) if activity_options else ""
        rel_type = st.selectbox("Type", ["FS", "SS", "FF"])
        lag_days = st.number_input("Lag days", step=1)
        if st.form_submit_button("Add Relationship") and pred_id and succ_id:
            add_relationship_from_form(project_path, pred_id, succ_id, rel_type, int(lag_days))
            st.rerun()
