from __future__ import annotations

from pathlib import Path
from typing import cast

from tools.project_tools import create_project, list_projects, load_project


def render(projects_dir: str | Path | None = None) -> None:
    import streamlit as st

    st.sidebar.markdown("### 📁 프로젝트")
    projects = cast(list[dict[str, object]], list_projects(projects_dir=projects_dir)["projects"])
    paths = [str(project["project_path"]) for project in projects]
    name_by_path = {str(p["project_path"]): str(p.get("name", "")) for p in projects}

    def _format(path: str) -> str:
        if not path:
            return "— 프로젝트 선택 —"
        name = name_by_path.get(path) or Path(path).stem
        return f"📂 {name}"

    selected = st.sidebar.selectbox("불러오기", [""] + paths, format_func=_format)
    if selected:
        st.session_state["project_path"] = selected
        loaded = load_project(selected)
        project = cast(dict[str, object], loaded.get("project", {}))
        st.sidebar.success(f"📌 {project.get('name', '')}")
        st.sidebar.caption(f"시작일 {project.get('start_date', '')}")

    st.sidebar.markdown("---")
    with st.sidebar.expander("➕ 새 프로젝트 만들기"):
        name = st.text_input("프로젝트 이름")
        start_date = st.date_input("시작일")
        week_mode = st.radio("근무일", ["주 5일", "주 6일"], horizontal=True, index=0)
        weekmask = "1111100" if week_mode == "주 5일" else "1111110"
        if st.button("✨ 생성", type="primary", use_container_width=True) and name:
            created = create_project(
                name,
                start_date.isoformat(),
                {"calendar_id": "cal", "name": f"Korean {'5' if week_mode == '주 5일' else '6'}-day", "weekmask": weekmask},
                projects_dir=projects_dir,
            )
            st.session_state["project_path"] = created["project_path"]
            st.rerun()
