from __future__ import annotations

from typing import Any, Literal, Mapping

from core.number_utils import to_float


ReportStyle = Literal["internal", "hq", "client"]

_STYLE_ALIASES: dict[str, ReportStyle] = {
    "internal": "internal",
    "weekly_meeting": "internal",
    "site": "internal",
    "field": "internal",
    "현장": "internal",
    "내부": "internal",
    "hq": "hq",
    "head_office": "hq",
    "management": "hq",
    "본사": "hq",
    "임원": "hq",
    "client": "client",
    "owner": "client",
    "official": "client",
    "발주처": "client",
    "감리": "client",
}


def normalize_report_style(style: str | None) -> ReportStyle:
    if style is None or not str(style).strip():
        return "internal"
    normalized = str(style).strip().lower()
    if normalized in _STYLE_ALIASES:
        return _STYLE_ALIASES[normalized]
    raise ValueError(f"Unsupported report_style: {style!r}. Expected internal, hq, or client.")


def format_report_summary(site_data: Mapping[str, Any], style: ReportStyle) -> str:
    summary = _mapping(site_data.get("summary"))
    planned = to_float(summary.get("planned_progress_pct"))
    actual = to_float(summary.get("actual_progress_pct"))
    gap = to_float(summary.get("progress_gap_pct"), default=actual - planned)
    delayed_count = int(to_float(summary.get("delayed_count")))
    cost_execution = to_float(summary.get("cost_execution_rate"))
    billing_rate = to_float(summary.get("billing_rate"))
    evm = _mapping(summary.get("evm"))
    spi = evm.get("spi")
    cpi = evm.get("cpi")
    if style == "internal":
        return (
            f"계획 {planned:.1f}% 대비 실적 {actual:.1f}%로 차이 {gap:.1f}%입니다. "
            f"부진공정 {delayed_count}건은 즉시 조치 필요하며 담당자 확인 필요."
        )
    if style == "hq":
        evm_text = f" SPI {spi}, CPI {cpi}," if spi is not None or cpi is not None else ""
        return (
            f"실적공정률 {actual:.1f}%, 계획 대비 차이 {gap:.1f}%,{evm_text} "
            f"원가 집행률 {cost_execution:.1f}%, 기성률 {billing_rate:.1f}%입니다. "
            "공정 리스크 관리 필요."
        )
    return (
        f"계획 대비 실적공정률 차이 {gap:.1f}%가 확인되어 만회계획을 검토 중입니다. "
        "관련 공정은 금주 중 조정계획을 수립하여 관리 예정입니다."
    )


def format_delay_issue(issue: Mapping[str, Any], style: ReportStyle) -> str:
    name = str(issue.get("name") or issue.get("activity_name") or issue.get("activity_id") or "해당 공정")
    reason = str(issue.get("reason") or issue.get("message") or issue.get("reason_code") or "지연 검토 필요")
    if style == "internal":
        return f"{name}: {reason} 담당자 확인 필요."
    if style == "hq":
        return f"{name}: 공정 리스크 관리 필요. 원인과 영향도 확인 필요."
    return f"{name}: 계획 대비 일부 지연이 확인되어 조정계획을 검토 중입니다."


def format_recovery_plan(plan: Mapping[str, Any], style: ReportStyle) -> str:
    title = str(plan.get("title") or plan.get("candidate") or "만회대책 후보")
    action = str(plan.get("report_sentence") or plan.get("action") or "검토 필요")
    if style == "internal":
        return f"{title}: {action} 현장소장 승인 후 시행 검토 필요."
    if style == "hq":
        return f"{title}: 공정 리스크 완화를 위한 후보입니다. 원가 집행률과 실적공정률 간 차이 확인 필요."
    return "관련 공정은 조정계획 초안을 검토 중이며, 승인 절차와 현장 여건 확인 후 관리 예정입니다."


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
