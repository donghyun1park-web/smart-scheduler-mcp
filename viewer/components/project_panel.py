from __future__ import annotations

from pathlib import Path
from typing import cast

from tools.project_tools import create_project, list_projects, load_project


def render(projects_dir: str | Path | None = None) -> None:
    import streamlit as st

    st.sidebar.header("Project")
    projects = cast(list[dict[str, object]], list_projects(projects_dir=projects_dir)["projects"])
    paths = [str(project["project_path"]) for project in projects]
    selected = st.sidebar.selectbox("Load project", [""] + paths)
    if selected:
        st.session_state["project_path"] = selected
        loaded = load_project(selected)
        project = cast(dict[str, object], loaded.get("project", {}))
        st.sidebar.caption(str(project.get("name", "")))

    with st.sidebar.expander("Create project"):
        name = st.text_input("Project name")
        start_date = st.date_input("Start date")
        if st.button("Create Project") and name:
            created = create_project(
                name,
                start_date.isoformat(),
                {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
                projects_dir=projects_dir,
            )
            st.session_state["project_path"] = created["project_path"]
            st.rerun()
