from __future__ import annotations

from pathlib import Path

from tools.report_tools import generate_report


def generate_report_from_viewer(project_path: str | Path, output_path: str | Path | None = None) -> dict[str, object]:
    return generate_report(project_path, output_path)


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("Report")
    if st.button("Generate Excel Report"):
        result = generate_report_from_viewer(project_path)
        if result["ok"]:
            st.success(str(result["output_path"]))
            with open(str(result["output_path"]), "rb") as handle:
                st.download_button(
                    "Download report",
                    handle,
                    file_name=Path(str(result["output_path"])).name,
                )
        else:
            st.error(str(result.get("error")))
