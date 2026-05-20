from __future__ import annotations

from pathlib import Path

from core import db
from core.models import Calendar, Project


def update_calendar_from_form(
    project_path: str | Path,
    calendar_id: str,
    name: str,
    weekmask: str,
    holidays: list[str],
) -> Calendar:
    return db.update_calendar(project_path, Calendar(calendar_id, name, weekmask, tuple(holidays)))


def render(project_path: str | Path) -> None:
    import streamlit as st

    summary = db.load_project_summary(project_path)
    project = summary["project"]
    if not isinstance(project, Project):
        st.warning("No project loaded")
        return
    calendar = db.get_calendar(project_path, project.calendar_id)
    if calendar is None:
        st.warning("Calendar not found")
        return
    st.subheader("Calendar")
    week_mode = st.radio("Weekmask", ["5-day", "6-day"], index=0 if calendar.weekmask == "1111100" else 1)
    holidays_text = st.text_area("User holidays", "\n".join(calendar.holidays))
    st.caption("ES/LS are working-day offsets. EF/LF dates use finish offset - 1 for non-milestone activities.")
    if st.button("Save Calendar"):
        update_calendar_from_form(
            project_path,
            calendar.calendar_id,
            calendar.name,
            "1111100" if week_mode == "5-day" else "1111110",
            [line.strip() for line in holidays_text.splitlines() if line.strip()],
        )
        st.rerun()
