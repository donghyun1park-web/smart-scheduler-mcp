"""Create a complete sample .scheduler DB from real Excel data.

Imports:
1. Construction activities from 홍은동 공정표 Excel (bar-chart schedule)
2. MEP activities synthesized from 실행예산 budget categories
3. Budget cost items mapped to all activities

Usage:
    python -m scripts.create_sample_db [--output path/to/output.scheduler]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCHEDULE_PATH = r"C:/MirTalk/Download/홍은동 355번지 가로주택_전체공정표.xlsx"
SCHEDULE_SHEET = "전체예정공정표(홍은동 가로주택정비사업-BEST)REV01"

BUDGET_FILES = {
    "건축": r"C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서 (PC공사등).xlsx",
    "토목": r"C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서(가설,토목,파일공사).xlsx",
    "기계설비": r"C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서(기계설비).xlsx",
    "전기설비": r"C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서(전기,통신,전기소방).xlsx",
}

DEFAULT_OUTPUT = "sample_hongneundong.scheduler"

# ---------------------------------------------------------------------------
# MEP activity definitions derived from budget category analysis
# ---------------------------------------------------------------------------
# These are the major MEP work items extracted from 실행예산내역서.
# Dates are set relative to typical construction phasing:
#   - Project start: 2026-06-01
#   - Structure (골조) completion: ~2028-02 (month 20)
#   - MEP rough-in starts during structure phase (~month 14)
#   - MEP finishing during interior (세대마감) phase (~month 24-36)
#   - Project end: ~2029-06

MEP_ACTIVITIES: list[dict] = [
    # 기계설비 — major categories from budget
    {
        "name": "난방배관공사",
        "discipline": "기계설비",
        "es": date(2028, 2, 10),
        "ef": date(2028, 12, 30),
        "desc": "세대 난방배관 설치 (24.4억)",
    },
    {
        "name": "오배수배관공사",
        "discipline": "기계설비",
        "es": date(2027, 12, 10),
        "ef": date(2028, 10, 30),
        "desc": "오배수 수직/수평배관 (23.6억)",
    },
    {
        "name": "급수/급탕배관공사",
        "discipline": "기계설비",
        "es": date(2028, 3, 10),
        "ef": date(2029, 1, 30),
        "desc": "급수급탕배관 설치 (13.9억)",
    },
    {
        "name": "공조덕트/배관공사",
        "discipline": "기계설비",
        "es": date(2028, 4, 10),
        "ef": date(2029, 2, 28),
        "desc": "공조설비 덕트 및 냉매배관 (12.8억)",
    },
    {
        "name": "위생기구설치공사",
        "discipline": "기계설비",
        "es": date(2028, 10, 10),
        "ef": date(2029, 4, 30),
        "desc": "세대/공용부 위생기구 설치 (9.2억)",
    },
    {
        "name": "기계실 장비설치",
        "discipline": "기계설비",
        "es": date(2028, 8, 10),
        "ef": date(2029, 3, 30),
        "desc": "보일러, 펌프, 열교환기 등 (11.5억)",
    },
    # 소방설비 — from 기계설비 budget (소방설비공사 category)
    {
        "name": "스프링클러배관공사",
        "discipline": "소방설비",
        "es": date(2027, 10, 10),
        "ef": date(2029, 1, 30),
        "desc": "스프링클러 배관 설치 (73.0억)",
    },
    {
        "name": "옥내소화배관공사",
        "discipline": "소방설비",
        "es": date(2027, 10, 10),
        "ef": date(2028, 12, 30),
        "desc": "옥내소화전 배관 설치 (48.3억)",
    },
    {
        "name": "소방장비설치",
        "discipline": "소방설비",
        "es": date(2028, 8, 10),
        "ef": date(2029, 3, 30),
        "desc": "소방펌프, 제연설비 등",
    },
    # 전기설비 — major categories from budget
    {
        "name": "전등설비공사",
        "discipline": "전기설비",
        "es": date(2028, 3, 10),
        "ef": date(2029, 4, 30),
        "desc": "조명 배선 및 기구 설치 (104억)",
    },
    {
        "name": "전열설비공사",
        "discipline": "전기설비",
        "es": date(2028, 3, 10),
        "ef": date(2029, 4, 30),
        "desc": "콘센트/전열 배선 (69.4억)",
    },
    {
        "name": "옥외전력간선공사",
        "discipline": "전기설비",
        "es": date(2027, 8, 10),
        "ef": date(2028, 6, 30),
        "desc": "지중전선로 및 수전설비 (59.3억)",
    },
    {
        "name": "승강기설비공사",
        "discipline": "전기설비",
        "es": date(2028, 2, 10),
        "ef": date(2029, 3, 30),
        "desc": "승강기 설치 (78.0억)",
    },
    {
        "name": "통신설비공사",
        "discipline": "전기설비",
        "es": date(2028, 4, 10),
        "ef": date(2029, 4, 30),
        "desc": "통신/인터폰/CCTV 배선 (75.5억)",
    },
    {
        "name": "자탐/유도등공사",
        "discipline": "전기설비",
        "es": date(2028, 2, 10),
        "ef": date(2029, 2, 28),
        "desc": "자동화재탐지/유도등 설치 (51.2억)",
    },
    {
        "name": "수변전설비공사",
        "discipline": "전기설비",
        "es": date(2028, 6, 10),
        "ef": date(2029, 3, 30),
        "desc": "수변전실 장비 설치",
    },
]


def create_sample_db(output_path: str | Path) -> dict:
    """Create a complete sample .scheduler database.

    Steps:
    1. Import construction schedule from 홍은동 공정표
    2. Add MEP activities from budget category analysis
    3. Import all 4 budget files and map costs to activities
    """
    from core import db
    from core.budget_importer import parse_budget_excel
    from core.models import Activity, Calendar, CostItem, Project, ProjectSettings, WBS
    from core.schedule_importer import import_schedule_to_db

    output_path = Path(output_path)
    if output_path.exists():
        output_path.unlink()

    # ------------------------------------------------------------------
    # Step 1: Import construction schedule (creates project, WBS, activities)
    # ------------------------------------------------------------------
    schedule_exists = Path(SCHEDULE_PATH).exists()
    if schedule_exists:
        result = import_schedule_to_db(
            output_path,
            SCHEDULE_PATH,
            sheet_name=SCHEDULE_SHEET,
            project_id="proj-hongneundong",
        )
        pid = result["project_id"]
        construction_count = result["activity_count"]
        print(f"[1/3] Imported {construction_count} construction activities from schedule")
        if result.get("warnings"):
            for w in result["warnings"][:5]:
                print(f"  WARN: {w}")
    else:
        # Fallback: create project structure manually
        pid = "proj-hongneundong"
        db.initialize_database(output_path)
        db.create_calendar(output_path, Calendar("cal-default", "기본달력", "1111100"))
        db.create_project(
            output_path,
            Project(pid, "홍은동 355번지 가로주택정비사업", date(2026, 6, 1), "cal-default"),
        )
        db.create_wbs(output_path, WBS("wbs-root", None, "ROOT", "홍은동 가로주택정비사업"))
        construction_count = 0
        print("[1/3] Schedule file not available, created empty project structure")

    # ------------------------------------------------------------------
    # Step 2: Add MEP activities
    # ------------------------------------------------------------------
    # Ensure WBS nodes for MEP disciplines exist
    mep_disciplines = sorted({a["discipline"] for a in MEP_ACTIVITIES})
    existing_wbs = db.list_wbs(output_path)
    existing_wbs_names = {w.name for w in existing_wbs}
    root_wbs = next((w for w in existing_wbs if w.parent_id is None), None)
    root_wbs_id = root_wbs.wbs_id if root_wbs else "wbs-root"

    for disc in mep_disciplines:
        if disc not in existing_wbs_names:
            wbs_id = f"wbs-{pid}-{disc}"
            sort_order = 100 + mep_disciplines.index(disc)
            db.create_wbs(
                output_path,
                WBS(wbs_id, root_wbs_id, disc, disc, sort_order=sort_order),
            )

    # Refresh WBS list after adding MEP ones
    all_wbs = db.list_wbs(output_path)
    wbs_by_name = {w.name: w.wbs_id for w in all_wbs}

    # Get next activity index (after construction activities)
    existing_activities = db.list_activities(output_path)
    next_idx = len(existing_activities)

    mep_created = 0
    for mep in MEP_ACTIVITIES:
        idx = next_idx + mep_created
        activity_id = f"act-{pid}-{idx:03d}"
        code = f"A-{idx + 1:03d}"
        wbs_id = wbs_by_name.get(mep["discipline"], root_wbs_id)

        es = mep["es"]
        ef = mep["ef"]
        duration = (ef - es).days

        db.create_activity(
            output_path,
            Activity(
                activity_id=activity_id,
                code=code,
                name=mep["name"],
                wbs_id=wbs_id,
                discipline=mep["discipline"],
                zone="",
                duration=max(duration, 1),
                es_date=es,
                ef_date=ef,
            ),
        )
        mep_created += 1

    print(f"[2/3] Added {mep_created} MEP activities ({', '.join(mep_disciplines)})")

    # ------------------------------------------------------------------
    # Step 3: Import budget costs and map to activities
    # ------------------------------------------------------------------
    all_activities = db.list_activities(output_path)
    activity_by_discipline: dict[str, list[Activity]] = {}
    for act in all_activities:
        activity_by_discipline.setdefault(act.discipline, []).append(act)

    # Parse all budget files
    budget_results = {}
    total_budget_items = 0
    for disc, path in BUDGET_FILES.items():
        if not Path(path).exists():
            print(f"  SKIP: Budget file not available: {path}")
            continue
        bresult = parse_budget_excel(path, discipline=disc)
        budget_results[disc] = bresult
        total_budget_items += len(bresult.items)

    # Map budget totals to activities by discipline
    # Budget discipline → scheduler discipline mapping
    budget_to_scheduler_disc = {
        "건축": "건축",
        "토목": "토목",
        "기계설비": "기계설비",
        "전기설비": "전기설비",
    }

    cost_items_created = 0
    for budget_disc, bresult in budget_results.items():
        scheduler_disc = budget_to_scheduler_disc.get(budget_disc, budget_disc)
        matched_activities = activity_by_discipline.get(scheduler_disc, [])

        # For 기계설비 budget, also include 소방설비 activities
        if budget_disc == "기계설비":
            matched_activities = matched_activities + activity_by_discipline.get("소방설비", [])

        if not matched_activities:
            print(f"  WARN: No activities for discipline {scheduler_disc}")
            continue

        # Distribute total budget evenly across matching activities
        total_contract = bresult.total_contract_amount
        total_execution = bresult.total_execution_amount
        share = len(matched_activities)

        for act in matched_activities:
            cost_item_id = f"cost-{act.activity_id}"
            contract = total_contract / share
            execution = total_execution / share

            db.upsert_cost_item(
                output_path,
                CostItem(
                    cost_item_id=cost_item_id,
                    activity_id=act.activity_id,
                    contract_amount=round(contract, 0),
                    execution_budget=round(execution, 0),
                ),
            )
            cost_items_created += 1

    print(f"[3/3] Created {cost_items_created} cost items from {len(budget_results)} budget files")

    # ------------------------------------------------------------------
    # Step 4: Project settings
    # ------------------------------------------------------------------
    all_disciplines = sorted({a.discipline for a in db.list_activities(output_path)})
    db.upsert_project_settings(
        output_path,
        ProjectSettings(
            settings_id=f"settings-{pid}",
            project_id=pid,
            disciplines=tuple(all_disciplines),
            thresholds={"progress_warning": 0.1, "cost_warning": 0.05},
            report_style="weekly_meeting",
        ),
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    summary = db.load_project_summary(output_path)
    cost_summary = db.get_cost_summary(output_path)

    print("\n" + "=" * 60)
    print(f"Sample DB created: {output_path}")
    print(f"  Activities:  {summary['activity_count']}")
    print(f"    - Construction: {construction_count}")
    print(f"    - MEP:          {mep_created}")
    print(f"  Cost items:  {cost_items_created}")
    print(f"  Contract:    {cost_summary['contract_amount']:>15,.0f} won")
    print(f"  Execution:   {cost_summary['execution_budget']:>15,.0f} won")
    print(f"  Disciplines: {', '.join(all_disciplines)}")
    print("=" * 60)

    return {
        "ok": True,
        "output_path": str(output_path),
        "activity_count": summary["activity_count"],
        "construction_count": construction_count,
        "mep_count": mep_created,
        "cost_items": cost_items_created,
        "contract_total": cost_summary["contract_amount"],
        "execution_total": cost_summary["execution_budget"],
        "disciplines": all_disciplines,
    }


def main():
    parser = argparse.ArgumentParser(description="Create sample .scheduler DB")
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT,
        help=f"Output .scheduler file path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()
    create_sample_db(args.output)


if __name__ == "__main__":
    main()
