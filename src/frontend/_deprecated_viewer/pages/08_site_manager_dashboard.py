from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import streamlit as st

from core.dashboard import generate_dashboard_markdown
from viewer.components.site_manager_dashboard import (
    build_dashboard_report_file,
    build_site_manager_dashboard_summary,
    load_site_dashboard_data_from_db,
    render_site_manager_dashboard,
)


st.set_page_config(page_title="Site Manager Dashboard", layout="wide")
st.sidebar.header("Site Manager Dashboard")

sample_path = Path("samples/ai_construction_site_sample.json")
source_mode = st.sidebar.radio("data source", ["SQLite DB", "JSON/sample"], horizontal=True)

if source_mode == "SQLite DB":
    db_path_text = st.sidebar.text_input("scheduler DB path", value="")
    project_id = st.sidebar.text_input("project_id", value="")
    as_of_date = st.sidebar.date_input("as_of_date", value=date.today())
    if db_path_text:
        report_style = st.sidebar.selectbox("report_style", ["internal", "hq", "client"], index=0)
        dashboard_data = load_site_dashboard_data_from_db(
            db_path_text,
            project_id=project_id or None,
            as_of_date=as_of_date,
        )
        disciplines = sorted(
            {
                str(activity.get("discipline") or "")
                for activity in dashboard_data["activities"]
                if activity.get("discipline")
            }
        )
        zones = sorted(
            {
                str(activity.get("zone") or "")
                for activity in dashboard_data["activities"]
                if activity.get("zone")
            }
        )
        selected_disciplines = st.sidebar.multiselect("discipline", disciplines, default=disciplines)
        selected_zones = st.sidebar.multiselect("zone", zones, default=zones)
        selected_risks = st.sidebar.multiselect(
            "risk severity",
            ["warning", "danger", "critical"],
            default=["warning", "danger", "critical"],
        )
        dashboard_data["activities"] = [
            activity
            for activity in dashboard_data["activities"]
            if (not selected_disciplines or activity.get("discipline") in selected_disciplines)
            and (not selected_zones or activity.get("zone") in selected_zones)
        ]
        dashboard_data["delayed_top10"] = [
            issue for issue in dashboard_data["delayed_top10"] if issue.get("severity") in selected_risks
        ]
        render_site_manager_dashboard(dashboard_data)

        # Sprint-1 안건 3: Markdown 보고서 즉시 복사.
        with st.expander("📋 카톡/메일용 Markdown 보고서 (우측 상단 복사 아이콘)", expanded=False):
            try:
                md_result = generate_dashboard_markdown(db_path_text, as_of=as_of_date)
                md_text = (
                    md_result.get("markdown", "")
                    if isinstance(md_result, dict)
                    else str(md_result)
                )
                if md_text:
                    st.code(md_text, language="markdown")
                    st.caption("복사 후 카톡/메일에 붙여넣으세요.")
                else:
                    st.info("아직 보고서로 만들 데이터가 없습니다.")
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Markdown 보고서를 생성하지 못했습니다: {exc}")

        if st.button("보고서 생성"):
            result = build_dashboard_report_file(
                db_path_text,
                Path("reports"),
                project_id=project_id or None,
                report_style=str(report_style),
            )
            report_path = Path(str(result["output_path"]))
            st.download_button(
                "보고서 다운로드",
                data=report_path.read_bytes(),
                file_name=report_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    else:
        st.info("SQLite .scheduler DB path를 입력하세요.")
else:
    uploaded = st.sidebar.file_uploader("site data JSON", type=["json"])
    if uploaded is not None:
        site_data = json.loads(uploaded.getvalue().decode("utf-8"))
    elif sample_path.exists():
        site_data = json.loads(sample_path.read_text(encoding="utf-8"))
    else:
        site_data = {"project": {}, "activities": []}

    summary = build_site_manager_dashboard_summary(site_data)
    render_site_manager_dashboard(summary)
