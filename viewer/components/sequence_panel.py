from __future__ import annotations

from pathlib import Path

from tools.sequence_tools import apply_sequences


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("Apply Sequence")
    discipline = st.selectbox("Discipline", ["위생", "공조"])
    sequence_key = st.text_input("Sequence key", "hvac_duct_standard" if discipline == "공조" else "plumbing_sanitary_standard")
    zones = st.text_input("Zones", "1F,2F")
    wbs_id = st.text_input("WBS ID")
    if st.button("Apply Sequence") and wbs_id:
        result = apply_sequences(
            project_path,
            discipline,
            sequence_key,
            [zone.strip() for zone in zones.split(",") if zone.strip()],
            wbs_id,
        )
        st.json(result)
        st.rerun()
