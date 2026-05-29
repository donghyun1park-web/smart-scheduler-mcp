from __future__ import annotations

from pathlib import Path

from core import db
from core.calendar_utils import korean_rainy_season_dates, korean_winter_break_dates
from core.models import Calendar, Project


def update_calendar_from_form(
    project_path: str | Path,
    calendar_id: str,
    name: str,
    weekmask: str,
    holidays: list[str],
) -> Calendar:
    return db.update_calendar(project_path, Calendar(calendar_id, name, weekmask, tuple(holidays)))


def _merge_dates(existing: list[str], added: list[str]) -> list[str]:
    return sorted({*existing, *added})


def render(project_path: str | Path) -> None:
    import streamlit as st

    summary = db.load_project_summary(project_path)
    project = summary["project"]
    if not isinstance(project, Project):
        st.warning("프로젝트가 로드되지 않았습니다.")
        return
    calendar = db.get_calendar(project_path, project.calendar_id)
    if calendar is None:
        st.warning("캘린더를 찾을 수 없습니다.")
        return

    st.subheader("📅 캘린더")
    st.caption("주 5일/6일제, 한국 공휴일은 자동 반영됩니다. 우기·동절기는 아래 버튼으로 한 번에 추가하세요.")

    week_mode = st.radio(
        "근무일",
        ["주 5일", "주 6일"],
        index=0 if calendar.weekmask == "1111100" else 1,
        horizontal=True,
    )
    weekmask = "1111100" if week_mode == "주 5일" else "1111110"

    default_year = project.start_date.year
    col1, col2 = st.columns(2)
    with col1:
        rainy_year = st.number_input("우기 적용 연도", min_value=2000, max_value=2100, value=default_year, step=1, key="cal_rainy_year")
        add_rainy = st.button("☔ 우기(6/25~7/25) 추가", use_container_width=True)
    with col2:
        winter_year = st.number_input("동절기 시작 연도", min_value=2000, max_value=2100, value=default_year, step=1, key="cal_winter_year")
        add_winter = st.button("❄️ 동절기(12/20~익년 2/10) 추가", use_container_width=True)

    holidays_text = st.text_area(
        "추가 휴일 목록 (YYYY-MM-DD, 한 줄에 하나)",
        "\n".join(calendar.holidays),
        height=180,
    )
    st.caption("기간(영업일)은 ES/LS는 워크데이 오프셋이며, EF/LF는 비-마일스톤 활동의 경우 종료 오프셋-1 위치의 날짜를 사용합니다.")

    if add_rainy:
        new_dates = [d.isoformat() for d in korean_rainy_season_dates(int(rainy_year))]
        merged = _merge_dates(holidays_text.splitlines(), new_dates)
        update_calendar_from_form(project_path, calendar.calendar_id, calendar.name, weekmask, merged)
        st.success(f"{rainy_year}년 우기 {len(new_dates)}일 추가됨")
        st.rerun()
    if add_winter:
        new_dates = [d.isoformat() for d in korean_winter_break_dates(int(winter_year))]
        merged = _merge_dates(holidays_text.splitlines(), new_dates)
        update_calendar_from_form(project_path, calendar.calendar_id, calendar.name, weekmask, merged)
        st.success(f"{winter_year}~{winter_year + 1} 동절기 {len(new_dates)}일 추가됨")
        st.rerun()

    if st.button("💾 저장", type="primary"):
        update_calendar_from_form(
            project_path,
            calendar.calendar_id,
            calendar.name,
            weekmask,
            [line.strip() for line in holidays_text.splitlines() if line.strip()],
        )
        st.rerun()
