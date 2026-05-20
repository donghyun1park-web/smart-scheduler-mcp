from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

from core import db
from core.calibration import (
    CalibrationPatch,
    DependencyOverride,
    DurationOverride,
    LagOverride,
    calibrate_project_completion,
)
from core.models import Activity, Calendar, Project, Relationship, WBS
from tools.import_tools import import_excel
from tools.report_tools import generate_report


@dataclass(frozen=True)
class FieldUATWorkflowInput:
    project_id: str
    excel_path: str | Path | None = None
    imported_schedule: dict[str, object] | None = None
    calibration_patch: dict[str, object] | None = None
    target_finish_date: str | date | None = None
    output_dir: str | Path | None = None
    generate_reports: bool = True
    language: str = "en"


def run_field_uat_workflow(request: FieldUATWorkflowInput) -> dict[str, object]:
    if request.excel_path is None and request.imported_schedule is None:
        raise ValueError("Either excel_path or imported_schedule is required")

    output_dir = Path(request.output_dir) if request.output_dir is not None else Path("reports") / request.project_id
    output_dir.mkdir(parents=True, exist_ok=True)
    project_path = output_dir / f"{request.project_id}.scheduler"
    _create_project_database(project_path, request)

    import_result: dict[str, object] | None = None
    source_type = "imported_schedule"
    if request.imported_schedule is not None:
        _load_imported_schedule(project_path, request.imported_schedule)
    else:
        source_type = "excel"
        import_result = import_excel(project_path, cast(str | Path, request.excel_path))

    patch = _calibration_patch(request)
    calibration_result = calibrate_project_completion(project_path, patch)
    comparison = cast(dict[str, object], calibration_result["comparison"])
    diagnostics = cast(dict[str, object], calibration_result["diagnostics"])
    before_diagnostics = cast(dict[str, object], diagnostics["before"])
    before_cpm = cast(dict[str, object], calibration_result["before_cpm"])
    correction_records = cast(list[dict[str, object]], calibration_result.get("correction_records") or [])

    result = {
        "project_id": request.project_id,
        "field_uat_status": comparison["field_uat_status"],
        "input_summary": _input_summary(source_type, before_diagnostics, import_result),
        "diagnostics_summary": _diagnostics_summary(before_diagnostics),
        "cpm_summary": _cpm_summary(before_cpm),
        "calibration_summary": _calibration_summary(comparison, correction_records, request),
        "correction_records": correction_records,
        "recommended_next_actions": _recommended_next_actions(comparison, before_diagnostics, calibration_result),
        "artifacts": {},
        "warnings": calibration_result["warnings"],
    }
    artifacts = _write_summary_artifacts(output_dir=output_dir, result=result)

    if request.generate_reports:
        report_path = output_dir / f"{request.project_id}_schedule_report.xlsx"
        artifacts["excel_report"] = str(report_path)
        result["artifacts"] = dict(artifacts)
        report = generate_report(project_path, report_path, field_uat_result=result)
        if report["ok"]:
            artifacts["excel_report"] = str(report["output_path"])

    result["artifacts"] = artifacts
    _rewrite_summary_artifacts(output_dir, result)
    return result


def _create_project_database(project_path: Path, request: FieldUATWorkflowInput) -> None:
    if project_path.exists():
        project_path.unlink()
    db.initialize_database(project_path)
    db.create_calendar(project_path, Calendar("cal", "Korean 5-day", "1111100"))
    start_date = _project_start_date(request.imported_schedule)
    db.create_project(project_path, Project(request.project_id, request.project_id, start_date, "cal"))
    db.add_wbs(project_path, WBS("wbs", None, "ROOT", "ROOT", 1))


def _project_start_date(imported_schedule: dict[str, object] | None) -> date:
    if imported_schedule is None:
        return date.today()
    project = imported_schedule.get("project")
    if isinstance(project, dict) and project.get("start_date"):
        return date.fromisoformat(str(project["start_date"]))
    return date.today()


def _load_imported_schedule(project_path: Path, imported_schedule: dict[str, object]) -> None:
    for item in cast(list[dict[str, object]], imported_schedule.get("activities") or []):
        db.add_activity(
            project_path,
            Activity(
                activity_id=str(item["activity_id"]),
                code=str(item["code"]),
                name=str(item["name"]),
                wbs_id="wbs",
                discipline=str(item.get("discipline") or "공통"),
                zone=str(item.get("zone") or ""),
                duration=_int_value(item["duration"]),
                cost=_float_value(item.get("cost") or 0),
            ),
        )
    for item in cast(list[dict[str, object]], imported_schedule.get("relationships") or []):
        db.add_relationship(
            project_path,
            Relationship(
                rel_id=str(item["rel_id"]),
                pred_id=str(item["pred_id"]),
                succ_id=str(item["succ_id"]),
                rel_type=str(item.get("rel_type") or "FS"),
                lag_days=_int_value(item.get("lag_days") or 0),
            ),
        )


def _calibration_patch(request: FieldUATWorkflowInput) -> CalibrationPatch:
    patch_data = request.calibration_patch or {}
    target = request.target_finish_date or patch_data.get("target_finish_date")
    return CalibrationPatch(
        project_id=request.project_id,
        target_finish_date=_date_value(target),
        dependency_overrides=[
            _dependency_override(item)
            for item in cast(list[dict[str, object]], patch_data.get("dependency_overrides") or [])
        ],
        duration_overrides=[
            _duration_override(item)
            for item in cast(list[dict[str, object]], patch_data.get("duration_overrides") or [])
        ],
        lag_overrides=[
            _lag_override(item)
            for item in cast(list[dict[str, object]], patch_data.get("lag_overrides") or [])
        ],
        notes=cast(str | None, patch_data.get("notes")),
    )


def _dependency_override(item: dict[str, object]) -> DependencyOverride:
    return DependencyOverride(
        predecessor_id=str(item["predecessor_id"]),
        successor_id=str(item["successor_id"]),
        dependency_type=str(item.get("dependency_type") or "FS"),
        lag_days=_int_value(item.get("lag_days") or 0),
        reason=_optional_str(item.get("reason")),
        source=str(item.get("source") or "user_calibration"),
    )


def _duration_override(item: dict[str, object]) -> DurationOverride:
    return DurationOverride(
        task_id=str(item["task_id"]),
        duration_days=_int_value(item["duration_days"]),
        reason=_optional_str(item.get("reason")),
        source=str(item.get("source") or "user_calibration"),
    )


def _lag_override(item: dict[str, object]) -> LagOverride:
    return LagOverride(
        predecessor_id=str(item["predecessor_id"]),
        successor_id=str(item["successor_id"]),
        lag_days=_int_value(item["lag_days"]),
        reason=_optional_str(item.get("reason")),
        source=str(item.get("source") or "user_calibration"),
    )


def _date_value(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _input_summary(
    source_type: str,
    diagnostics: dict[str, object],
    import_result: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "source_type": source_type,
        "task_count": diagnostics["task_count"],
        "dependency_count": diagnostics["dependency_count"],
        "import_result": import_result,
    }


def _diagnostics_summary(diagnostics: dict[str, object]) -> dict[str, object]:
    keys = [
        "task_count",
        "dependency_count",
        "tasks_without_predecessor_count",
        "tasks_without_successor_count",
        "isolated_task_count",
        "missing_duration_count",
        "zero_or_negative_duration_count",
        "missing_cost_count",
        "duplicate_task_id_count",
        "cycle_detected",
        "disconnected_component_count",
        "relationship_coverage_ratio",
        "cost_coverage_ratio",
    ]
    return {key: diagnostics[key] for key in keys}


def _cpm_summary(before_cpm: dict[str, object]) -> dict[str, object]:
    return {
        "before_finish_date": before_cpm["completion_date"],
        "critical_path_task_count": len(cast(list[object], before_cpm["critical_path"])),
    }


def _calibration_summary(
    comparison: dict[str, object],
    correction_records: list[dict[str, object]],
    request: FieldUATWorkflowInput,
) -> dict[str, object] | None:
    if request.calibration_patch is None and request.target_finish_date is None:
        return None
    return {
        "target_finish_date": comparison["target_finish_date"],
        "before_finish_date": comparison["before_finish_date"],
        "after_finish_date": comparison["after_finish_date"],
        "delta_days_before": comparison["delta_days_before"],
        "delta_days_after": comparison["delta_days_after"],
        "critical_path_before_count": len(cast(list[object], comparison["critical_path_before"])),
        "critical_path_after_count": len(cast(list[object], comparison["critical_path_after"])),
        "dependency_count_before": comparison["dependency_count_before"],
        "dependency_count_after": comparison["dependency_count_after"],
        "correction_count": len(correction_records),
    }


def _recommended_next_actions(
    comparison: dict[str, object],
    diagnostics: dict[str, object],
    calibration_result: dict[str, object],
) -> list[str]:
    warnings = cast(list[dict[str, object]], calibration_result["warnings"])
    codes = {str(warning["code"]) for warning in warnings}
    actions: list[str] = []
    if comparison["field_uat_status"] == "blocked_by_cycle" or "DEPENDENCY_CYCLE" in codes:
        actions.append("Resolve cycle warnings before generating a reliable CPM result.")
    if comparison["field_uat_status"] == "needs_relationship_correction" or _int_value(diagnostics["isolated_task_count"]) > 0:
        actions.append("Add dependencies for isolated tasks before trusting CPM finish date.")
        actions.append("Review tasks without predecessors or successors.")
    if comparison["field_uat_status"] == "needs_cost_correction" or "LOW_COST_COVERAGE" in codes:
        actions.append("Supplement missing cost values before using S-Curve.")
    if comparison.get("delta_days_after") not in {None, 0}:
        actions.append("Apply an explicit calibration patch if the target finish date delta remains high.")
    if not actions:
        actions.append("Review the CPM, Gantt, S-Curve, and Excel report artifacts with the field team.")
    return actions


def _write_summary_artifacts(output_dir: Path, result: dict[str, object]) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, object] = {
        "summary_json": str(output_dir / "field_uat_summary.json"),
        "summary_markdown": str(output_dir / "field_uat_summary.md"),
    }
    result["artifacts"] = dict(artifacts)
    _rewrite_summary_artifacts(output_dir, result)
    return artifacts


def _rewrite_summary_artifacts(output_dir: Path, result: dict[str, object]) -> None:
    json_path = output_dir / "field_uat_summary.json"
    markdown_path = output_dir / "field_uat_summary.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown_summary(result), encoding="utf-8")


def _markdown_summary(result: dict[str, object]) -> str:
    diagnostics = cast(dict[str, object], result["diagnostics_summary"])
    cpm = cast(dict[str, object], result["cpm_summary"])
    calibration = cast(dict[str, object] | None, result["calibration_summary"])
    actions = cast(list[str], result["recommended_next_actions"])
    artifacts = cast(dict[str, object], result["artifacts"])
    lines = [
        "# Field UAT Summary",
        "",
        "## Project",
        "",
        f"- Project ID: {result['project_id']}",
        f"- Field UAT Status: {result['field_uat_status']}",
        "",
        "## Diagnostics",
        "",
        f"- Relationship coverage: {diagnostics['relationship_coverage_ratio']}",
        f"- Cost coverage: {diagnostics['cost_coverage_ratio']}",
        f"- Isolated tasks: {diagnostics['isolated_task_count']}",
        f"- Cycle detected: {diagnostics['cycle_detected']}",
        "",
        "## CPM Result",
        "",
        f"- Before finish date: {cpm['before_finish_date']}",
        f"- Critical path task count: {cpm['critical_path_task_count']}",
        "",
        "## Calibration Result",
        "",
    ]
    if calibration is None:
        lines.append("- Calibration patch: not supplied")
    else:
        lines.extend(
            [
                f"- Target finish date: {calibration['target_finish_date']}",
                f"- After finish date: {calibration['after_finish_date']}",
                f"- Delta before: {calibration['delta_days_before']}",
                f"- Delta after: {calibration['delta_days_after']}",
            ]
        )
    lines.extend(["", "## Recommended Next Actions", ""])
    lines.extend(f"{idx}. {action}" for idx, action in enumerate(actions, start=1))
    lines.extend(["", "## Artifacts", ""])
    lines.extend(f"- {key}: {value}" for key, value in artifacts.items())
    lines.append("")
    return "\n".join(lines)


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(value)
    return int(str(value))


def _float_value(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    return float(str(value))
