from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from viewer.components.site_manager_dashboard import (
    build_site_manager_dashboard_summary,
    render_site_manager_dashboard,
)


st.set_page_config(page_title="Site Manager Dashboard", layout="wide")
st.sidebar.header("Site Manager Dashboard")

sample_path = Path("samples/ai_construction_site_sample.json")
uploaded = st.sidebar.file_uploader("site data JSON", type=["json"])

if uploaded is not None:
    site_data = json.loads(uploaded.getvalue().decode("utf-8"))
elif sample_path.exists():
    site_data = json.loads(sample_path.read_text(encoding="utf-8"))
else:
    site_data = {"project": {}, "activities": []}

summary = build_site_manager_dashboard_summary(site_data)
render_site_manager_dashboard(summary)
