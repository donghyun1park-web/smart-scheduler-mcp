from __future__ import annotations

from viewer.components import (
    activity_editor,
    analysis_panel,
    calendar_editor,
    import_panel,
    project_panel,
    relationship_editor,
    sequence_panel,
    wbs_editor,
)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Smart Node-Scheduler", layout="wide")
    st.title("Smart Node-Scheduler")
    project_panel.render()
    project_path = st.session_state.get("project_path")
    if not project_path:
        st.info("Create or load a project from the sidebar.")
        return

    tabs = st.tabs(["WBS", "Activities", "Relationships", "Calendar", "Import", "Sequences", "CPM"])
    with tabs[0]:
        wbs_editor.render(project_path)
    with tabs[1]:
        activity_editor.render(project_path)
    with tabs[2]:
        relationship_editor.render(project_path)
    with tabs[3]:
        calendar_editor.render(project_path)
    with tabs[4]:
        import_panel.render(project_path)
    with tabs[5]:
        sequence_panel.render(project_path)
    with tabs[6]:
        analysis_panel.render(project_path)


if __name__ == "__main__":
    main()
