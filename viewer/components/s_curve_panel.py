from __future__ import annotations

from pathlib import Path

import plotly.express as px

from core import db
from core.s_curve import build_s_curve_data


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("S-Curve")
    rows = build_s_curve_data(db.list_activities(project_path))
    st.dataframe(rows, use_container_width=True)
    if rows:
        fig = px.line(rows, x="date", y="cumulative_value", markers=True)
        st.plotly_chart(fig, use_container_width=True)
