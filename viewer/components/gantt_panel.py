from __future__ import annotations

from pathlib import Path

from core import db
from core.visualization import build_gantt_figure


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("Gantt")
    activities = db.list_activities(project_path)
    disciplines = sorted({activity.discipline for activity in activities})
    zones = sorted({activity.zone for activity in activities if activity.zone})
    discipline = st.selectbox("Gantt discipline", ["All"] + disciplines)
    zone = st.selectbox("Gantt zone", ["All"] + zones)
    critical_only = st.checkbox("Critical only")
    filtered = activities[:1000]
    fig = build_gantt_figure(
        filtered,
        discipline=None if discipline == "All" else discipline,
        zone=None if zone == "All" else zone,
        critical_only=critical_only,
    )
    st.plotly_chart(fig, use_container_width=True)
