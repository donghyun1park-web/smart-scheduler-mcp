from __future__ import annotations

import uuid
from pathlib import Path

from core import db
from core.models import WBS


def add_wbs_from_form(
    project_path: str | Path,
    *,
    code: str,
    name: str,
    parent_id: str | None,
    sort_order: int,
) -> WBS:
    return db.add_wbs(project_path, WBS(str(uuid.uuid4()), parent_id, code, name, sort_order))


def update_wbs_from_form(
    project_path: str | Path,
    wbs_id: str,
    *,
    code: str,
    name: str,
    parent_id: str | None,
    sort_order: int,
) -> WBS:
    return db.update_wbs(project_path, WBS(wbs_id, parent_id, code, name, sort_order))


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("WBS")
    items = db.list_wbs(project_path)
    st.dataframe([item.__dict__ for item in items], use_container_width=True)
    with st.form("add_wbs"):
        code = st.text_input("Code")
        name = st.text_input("Name")
        parent_id = st.text_input("Parent ID")
        sort_order = st.number_input("Sort order", min_value=0, step=1)
        if st.form_submit_button("Add WBS") and code and name:
            add_wbs_from_form(
                project_path,
                code=code,
                name=name,
                parent_id=parent_id or None,
                sort_order=int(sort_order),
            )
            st.rerun()
