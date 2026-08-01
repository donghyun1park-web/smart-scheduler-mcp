from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from core import db

HealthSeverity = Literal["error", "warning", "info"]
HealthStatus = Literal["healthy", "watch", "risk"]


@dataclass(frozen=True)
class HealthIssue:
    severity: HealthSeverity
    category: str
    code: str
    message_ko: str
    suggestion_ko: str
    target_table: str | None = None
    target_id: str | None = None
    penalty: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "category": self.category,
            "code": self.code,
            "message_ko": self.message_ko,
            "suggestion_ko": self.suggestion_ko,
            "target_table": self.target_table,
            "target_id": self.target_id,
            "penalty": self.penalty,
        }


@dataclass(frozen=True)
class DataHealthReport:
    score: int
    status: HealthStatus
    summary_ko: str
    error_count: int
    warning_count: int
    info_count: int
    issues: tuple[HealthIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "status": self.status,
            "summary_ko": self.summary_ko,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def check_data_health(
    db_path: str | Path,
    *,
    project_id: str | None = None,
    as_of: date | None = None,
    max_issues: int = 50,
) -> DataHealthReport:
    """Inspect a .scheduler DB and return a read-only health score."""
    today = as_of or date.today()
    activities = _filtered_activities(db_path, project_id=project_id)
    issues: list[HealthIssue] = []

    if not activities:
        issues.append(
            HealthIssue(
                "error",
                "schedule",
                "no_activities",
                "공정 데이터가 없습니다.",
                "공정표 Excel을 먼저 가져온 뒤 다시 진단하세요.",
                "activities",
                penalty=40,
            )
        )
        return _report(issues, max_issues=max_issues)

    activity_ids = {activity.activity_id for activity in activities}
    cost_items = db.list_cost_items(db_path)
    relationships = db.list_relationships(db_path)
    daily_records = db.list_daily_records(db_path)

    _check_costs(issues, activities, activity_ids, cost_items)
    _check_relationships(issues, relationships)
    _check_activities(issues, activities)
    _check_daily_records(issues, activity_ids, daily_records, today)
    _check_materials(issues, db_path, today)
    _check_inspections(issues, db_path, today)
    return _report(issues, max_issues=max_issues)


def _filtered_activities(db_path: str | Path, *, project_id: str | None):
    summary = db.load_project_summary(db_path)
    project = summary.get("project")
    if project_id and getattr(project, "project_id", None) != project_id:
        return []
    return db.list_activities(db_path)


def _check_costs(issues, activities, activity_ids: set[str], cost_items) -> None:
    if not cost_items:
        issues.append(
            HealthIssue(
                "warning",
                "cost",
                "no_cost_items",
                "실행예산 데이터가 없습니다.",
                "실행예산 Excel을 가져오면 EVM과 원가 분석을 사용할 수 있습니다.",
                "cost_items",
                penalty=15,
            )
        )
    cost_activity_ids = {item.activity_id for item in cost_items}
    missing_cost = [activity for activity in activities if activity.activity_id not in cost_activity_ids]
    if missing_cost:
        sample = missing_cost[0]
        issues.append(
            HealthIssue(
                "warning",
                "cost",
                "activity_without_cost",
                f"{sample.code} {sample.name} 등 {len(missing_cost)}개 공정에 실행예산이 연결되어 있지 않습니다.",
                "공정별 실행예산을 연결한 뒤 원가/기성 분석을 다시 확인하세요.",
                "activities",
                sample.activity_id,
                penalty=min(20, max(5, len(missing_cost) * 2)),
            )
        )
    orphan_costs = [item for item in cost_items if item.activity_id not in activity_ids]
    if orphan_costs:
        issues.append(
            HealthIssue(
                "error",
                "cost",
                "cost_without_activity",
                f"존재하지 않는 공정에 연결된 원가 항목이 {len(orphan_costs)}개 있습니다.",
                "원가 항목의 activity_id를 실제 공정과 맞추세요.",
                "cost_items",
                orphan_costs[0].cost_item_id,
                penalty=min(25, max(10, len(orphan_costs) * 5)),
            )
        )


def _check_relationships(issues, relationships) -> None:
    if not relationships:
        issues.append(
            HealthIssue(
                "warning",
                "schedule",
                "no_relationships",
                "선후행 관계가 없습니다.",
                "관계 후보를 dry-run으로 검토한 뒤 필요한 관계만 적용하세요.",
                "relationships",
                penalty=10,
            )
        )


def _check_activities(issues, activities) -> None:
    invalid = [activity for activity in activities if activity.duration <= 0]
    if invalid:
        activity = invalid[0]
        issues.append(
            HealthIssue(
                "error",
                "schedule",
                "invalid_duration",
                f"{activity.code} {activity.name}의 기간 값이 부적절합니다: {activity.duration}.",
                "기간을 1일 이상으로 보정한 뒤 CPM을 다시 계산하세요.",
                "activities",
                activity.activity_id,
                penalty=min(20, len(invalid) * 10),
            )
        )


def _check_daily_records(issues, activity_ids: set[str], records, today: date) -> None:
    unknown = [record for record in records if record.activity_id not in activity_ids]
    if unknown:
        issues.append(
            HealthIssue(
                "error",
                "daily_record",
                "daily_record_unknown_activity",
                f"존재하지 않는 공정에 연결된 실적 입력이 {len(unknown)}개 있습니다.",
                "실적 입력의 activity_id를 실제 공정과 맞추세요.",
                "daily_records",
                unknown[0].record_id,
                penalty=min(25, max(10, len(unknown) * 5)),
            )
        )
    negative = [record for record in records if record.planned_qty < 0 or record.actual_qty < 0]
    if negative:
        issues.append(
            HealthIssue(
                "error",
                "daily_record",
                "negative_quantity",
                f"음수 물량이 입력된 실적 기록이 {len(negative)}개 있습니다.",
                "계획/실적 물량을 0 이상 값으로 수정하세요.",
                "daily_records",
                negative[0].record_id,
                penalty=min(20, max(10, len(negative) * 5)),
            )
        )
    over_100 = [record for record in records if record.planned_qty > 0 and record.actual_qty > record.planned_qty]
    if over_100:
        issues.append(
            HealthIssue(
                "warning",
                "daily_record",
                "progress_over_100",
                f"실적이 계획 물량을 초과한 기록이 {len(over_100)}개 있습니다.",
                "초과 실적이 실제 추가 물량인지 입력 오류인지 검토하세요.",
                "daily_records",
                over_100[0].record_id,
                penalty=min(10, len(over_100) * 2),
            )
        )
    recent_start = today - timedelta(days=3)
    has_recent = any(recent_start <= record.work_date <= today for record in records)
    if records and not has_recent:
        issues.append(
            HealthIssue(
                "warning",
                "daily_record",
                "missing_recent_daily_records",
                "최근 3일 이내 실적 입력이 없습니다.",
                "일일 마감 전에 최신 실적 입력 여부를 확인하세요.",
                "daily_records",
                penalty=10,
            )
        )


def _check_materials(issues, db_path: str | Path, today: date) -> None:
    late_statuses = {"planned", "ordered", "pending"}
    late = [
        item
        for item in db.list_materials(db_path)
        if item.expected_date is not None and item.expected_date < today and item.status in late_statuses
    ]
    if late:
        issues.append(
            HealthIssue(
                "warning",
                "material",
                "late_materials",
                f"입고 예정일이 지난 미입고 자재가 {len(late)}개 있습니다.",
                "자재 입고일과 현장 반입 가능 여부를 확인하세요.",
                "materials",
                late[0].material_id,
                penalty=min(10, len(late) * 2),
            )
        )


def _check_inspections(issues, db_path: str | Path, today: date) -> None:
    open_statuses = {"planned", "requested", "pending"}
    late = [
        item
        for item in db.list_inspections(db_path)
        if item.planned_date is not None and item.planned_date < today and item.status in open_statuses
    ]
    if late:
        issues.append(
            HealthIssue(
                "warning",
                "inspection",
                "late_inspections",
                f"검측 예정일이 지난 미완료 검측이 {len(late)}개 있습니다.",
                "검측 요청 상태와 승인 예정일을 확인하세요.",
                "inspections",
                late[0].inspection_id,
                penalty=min(10, len(late) * 2),
            )
        )


def _report(issues: list[HealthIssue], *, max_issues: int) -> DataHealthReport:
    score = max(0, min(100, 100 - sum(issue.penalty for issue in issues)))
    status: HealthStatus = "healthy" if score >= 85 else "watch" if score >= 60 else "risk"
    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    info_count = sum(1 for issue in issues if issue.severity == "info")
    summary = f"데이터 건강점수는 {score}점이며 상태는 {status}입니다. 오류 {error_count}건, 주의 {warning_count}건입니다."
    ordered = sorted(issues, key=lambda issue: {"error": 0, "warning": 1, "info": 2}[issue.severity])
    return DataHealthReport(
        score=score,
        status=status,
        summary_ko=summary,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        issues=tuple(ordered[: max(max_issues, 0)]),
    )
