from __future__ import annotations

from pathlib import Path

from core.reporting import create_excel_report


def generate_report(
    project_path: str | Path,
    output_path: str | Path | None = None,
    field_uat_result: dict[str, object] | None = None,
) -> dict[str, object]:
    """Write a multi-sheet Excel report (schedule, CPM, S-curve, calibration).

    ``output_path`` defaults next to the project file. If ``field_uat_result``
    is supplied, calibration-summary sheets are appended.
    """
    return create_excel_report(project_path, output_path, field_uat_result=field_uat_result)
