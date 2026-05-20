from __future__ import annotations

from pathlib import Path

from tools.import_tools import import_excel


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("Excel Import")
    file_path = st.text_input("Excel file path")
    preset_name = st.text_input("Preset name", "sample")
    if st.button("Import Excel") and file_path:
        result = import_excel(project_path, file_path, preset_name=preset_name)
        st.json(result)
