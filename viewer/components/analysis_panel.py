from __future__ import annotations

from pathlib import Path

from tools.analysis_tools import calculate_cpm, get_critical_path


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("CPM")
    if st.button("Calculate CPM"):
        st.json(calculate_cpm(project_path))
    critical = get_critical_path(project_path)
    st.dataframe(critical["critical_path"], use_container_width=True)
