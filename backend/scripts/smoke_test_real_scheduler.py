from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.importer import generate_weekly_report_from_db, import_field_input_to_db  # noqa: E402
from core.recovery import FORBIDDEN_FINAL_WORDS, suggest_recovery_plans  # noqa: E402
from viewer.components.site_manager_dashboard import load_site_dashboard_data_from_db  # noqa: E402


RECOVERY_REASON_CODES = [
    "material_delay",
    "manpower_shortage",
    "predecessor_incomplete",
    "equipment_delay",
    "inspection_delay",
    "design_change",
    "subcontractor_delay",
    "weather_delay",
]


def run_smoke_test(
    source_db: str | Path,
    *,
    excel_input: str | Path | None = None,
    out_dir: str | Path = "smoke_outputs",
    apply: bool = False,
) -> dict[str, Any]:
    source = Path(source_db)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_mtime = source.stat().st_mtime_ns
    working_copy = _copy_scheduler_db(source, output_dir)

    dashboard_data = load_site_dashboard_data_from_db(working_copy)
    dashboard_result = {
        "ok": True,
        "summary": dashboard_data["summary"],
        "delayed_top10_count": len(dashboard_data["delayed_top10"]),
        "cost_risk_count": len(dashboard_data["cost_risks"]),
    }

    dry_run_result: dict[str, Any]
    apply_result: dict[str, Any]
    if excel_input is not None:
        dry_run_result = import_field_input_to_db(working_copy, excel_input, dry_run=True)
        if apply:
            apply_result = import_field_input_to_db(working_copy, excel_input, conflict_policy="fail")
        else:
            apply_result = {"skipped": True, "reason": "apply flag was not provided"}
    else:
        dry_run_result = {"ok": True, "skipped": True, "reason": "excel input was not provided", "changed": False}
        apply_result = {"skipped": True, "reason": "excel input was not provided"}

    reports: dict[str, str] = {}
    for style in ("internal", "hq", "client"):
        report_path = output_dir / f"{working_copy.stem}_{style}_weekly.xlsx"
        report_result = generate_weekly_report_from_db(working_copy, report_path, report_style=style)
        if not report_result.get("ok"):
            raise RuntimeError(f"Report generation failed for style={style}: {report_result}")
        reports[style] = str(report_path)

    recovery_result = _check_recovery_templates()
    result = {
        "ok": bool(dashboard_result["ok"] and dry_run_result.get("ok", False) and recovery_result["ok"]),
        "source_db": str(source),
        "working_copy": str(working_copy),
        "excel_input": str(excel_input) if excel_input is not None else None,
        "dashboard": dashboard_result,
        "dry_run": dry_run_result,
        "import_apply": apply_result,
        "reports": reports,
        "recovery": recovery_result,
        "original_unchanged": source.stat().st_mtime_ns == source_mtime,
    }
    result_path = output_dir / f"{working_copy.stem}_smoke_result.json"
    result["result_json"] = str(result_path)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run v2.2 smoke test on a copied .scheduler DB.")
    parser.add_argument("--db", required=True, help="Source .scheduler DB. This file is copied before testing.")
    parser.add_argument("--excel", help="Optional field input workbook.")
    parser.add_argument("--out-dir", default="smoke_outputs", help="Output directory for DB copy, reports, and JSON.")
    parser.add_argument("--apply", action="store_true", help="Apply the Excel import to the copied DB after dry-run.")
    args = parser.parse_args()
    result = run_smoke_test(args.db, excel_input=args.excel, out_dir=args.out_dir, apply=args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["ok"] else 1


def _copy_scheduler_db(source: Path, output_dir: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    destination = output_dir / f"{source.stem}_smoke_{timestamp}{source.suffix}"
    shutil.copy2(source, destination)
    return destination


def _check_recovery_templates() -> dict[str, Any]:
    checked: dict[str, int] = {}
    violations: list[str] = []
    for reason_code in RECOVERY_REASON_CODES:
        plans = suggest_recovery_plans(reason_code)
        text = json.dumps(plans, ensure_ascii=False)
        checked[reason_code] = len(plans)
        violations.extend([word for word in FORBIDDEN_FINAL_WORDS if word in text])
    return {"ok": not violations, "checked": checked, "forbidden_word_violations": sorted(set(violations))}


if __name__ == "__main__":
    raise SystemExit(main())
