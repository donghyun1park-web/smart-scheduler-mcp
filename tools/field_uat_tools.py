from __future__ import annotations

from pathlib import Path

from core.field_uat import FieldUATWorkflowInput, run_field_uat_workflow as run_core_field_uat_workflow


def run_field_uat_workflow(
    project_id: str,
    excel_path: str | Path | None = None,
    imported_schedule: dict[str, object] | None = None,
    calibration_patch: dict[str, object] | None = None,
    target_finish_date: str | None = None,
    output_dir: str | Path | None = None,
    generate_reports: bool = True,
) -> dict[str, object]:
    return run_core_field_uat_workflow(
        FieldUATWorkflowInput(
            project_id=project_id,
            excel_path=excel_path,
            imported_schedule=imported_schedule,
            calibration_patch=calibration_patch,
            target_finish_date=target_finish_date,
            output_dir=output_dir,
            generate_reports=generate_reports,
        )
    )
