from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from core import db
from core.data_health import check_data_health

WorkflowStepState = Literal["passed", "warning", "failed", "pending"]


@dataclass(frozen=True)
class WorkflowStepStatus:
    key: str
    title_ko: str
    state: WorkflowStepState
    message_ko: str
    tool_name: str | None = None
    required: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title_ko": self.title_ko,
            "state": self.state,
            "message_ko": self.message_ko,
            "tool_name": self.tool_name,
            "required": self.required,
        }


@dataclass(frozen=True)
class WorkflowStatus:
    key: str
    title_ko: str
    ready: bool
    steps: tuple[WorkflowStepStatus, ...]
    summary_ko: str

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title_ko": self.title_ko,
            "ready": self.ready,
            "summary_ko": self.summary_ko,
            "steps": [step.to_dict() for step in self.steps],
        }


def get_daily_close_status(db_path: str | Path, *, as_of: date | None = None) -> WorkflowStatus:
    today = as_of or date.today()
    activities = db.list_activities(db_path)
    cost_items = db.list_cost_items(db_path)
    relationships = db.list_relationships(db_path)
    today_records = db.list_daily_records(db_path, work_date=today)
    health = check_data_health(db_path, as_of=today)
    steps = (
        _step("activities", "공정 데이터", bool(activities), "공정 데이터가 준비되었습니다.", "공정 데이터가 없습니다.", "import_schedule_excel"),
        _step("daily_records", "오늘 실적 입력", bool(today_records), "오늘 실적 입력이 있습니다.", "오늘 실적 입력이 없습니다.", "import_excel_input_to_db"),
        _step("cost_items", "원가 데이터", bool(cost_items), "원가 데이터가 연결되었습니다.", "원가 데이터가 부족합니다.", "import_budget_excel", required=False),
        _step("relationships", "선후행 관계", bool(relationships), "선후행 관계가 있습니다.", "선후행 관계가 부족합니다.", "suggest_activity_relationships", required=False),
        WorkflowStepStatus(
            "data_health",
            "데이터 건강점수",
            "failed" if health.error_count else "warning" if health.warning_count else "passed",
            health.summary_ko,
            "check_data_health",
            required=True,
        ),
    )
    return _workflow("daily_close", "일일마감 상태", steps)


def get_weekly_report_precheck_status(db_path: str | Path, *, as_of: date | None = None) -> WorkflowStatus:
    today = as_of or date.today()
    activities = db.list_activities(db_path)
    cost_items = db.list_cost_items(db_path)
    relationships = db.list_relationships(db_path)
    recent = db.list_daily_records(db_path, start_date=today - timedelta(days=7), end_date=today)
    steps = (
        _step("activities", "공정 데이터", bool(activities), "공정 데이터가 있습니다.", "공정 데이터가 없습니다.", "import_schedule_excel"),
        _step("cost_items", "실행예산", bool(cost_items), "실행예산 데이터가 있습니다.", "실행예산 데이터가 없습니다.", "import_budget_excel"),
        _step("relationships", "선후행 관계", bool(relationships), "선후행 관계가 있습니다.", "선후행 관계가 없습니다.", "suggest_activity_relationships"),
        WorkflowStepStatus(
            "recent_daily_records",
            "최근 실적",
            "passed" if recent else "warning",
            "최근 7일 실적이 있습니다." if recent else "최근 7일 실적이 없어 보고서 해석에 주의가 필요합니다.",
            "import_excel_input_to_db",
            required=False,
        ),
        WorkflowStepStatus(
            "report_style",
            "보고서 문체",
            "passed",
            "내부용, 본사용, 발주처용 문체를 선택할 수 있습니다.",
            "generate_weekly_report_from_db",
            required=False,
        ),
    )
    return _workflow("weekly_report_precheck", "주간보고서 사전점검", steps)


def _step(
    key: str,
    title: str,
    ok: bool,
    passed_message: str,
    failed_message: str,
    tool_name: str,
    *,
    required: bool = True,
) -> WorkflowStepStatus:
    return WorkflowStepStatus(
        key,
        title,
        "passed" if ok else "failed",
        passed_message if ok else failed_message,
        tool_name,
        required,
    )


def _workflow(key: str, title: str, steps: tuple[WorkflowStepStatus, ...]) -> WorkflowStatus:
    ready = all(step.state != "failed" for step in steps if step.required)
    failed_count = sum(1 for step in steps if step.state == "failed")
    warning_count = sum(1 for step in steps if step.state == "warning")
    summary = "진행 가능합니다." if ready else f"필수 단계 {failed_count}건을 먼저 처리해야 합니다."
    if ready and warning_count:
        summary = f"진행 가능하지만 주의 단계 {warning_count}건이 있습니다."
    return WorkflowStatus(key, title, ready, steps, summary)
