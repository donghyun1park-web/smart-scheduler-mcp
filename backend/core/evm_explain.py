from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.number_utils import to_float


def explain_evm_totals_ko(evm_totals: Mapping[str, object]) -> dict[str, object]:
    pv = _value(evm_totals, "pv", "planned_value")
    ev = _value(evm_totals, "ev", "earned_value")
    ac = _value(evm_totals, "ac", "actual_cost")
    spi = _optional_number(evm_totals.get("spi"))
    cpi = _optional_number(evm_totals.get("cpi"))
    return _explain(pv=pv, ev=ev, ac=ac, spi=spi, cpi=cpi, status_hint=str(evm_totals.get("status") or ""))


def explain_evm_snapshot_ko(evm_snapshot: Mapping[str, object]) -> dict[str, object]:
    pv = _value(evm_snapshot, "pv", "planned_value")
    ev = _value(evm_snapshot, "ev", "earned_value")
    ac = _value(evm_snapshot, "ac", "actual_cost")
    spi = _optional_number(evm_snapshot.get("spi"))
    cpi = _optional_number(evm_snapshot.get("cpi"))
    return _explain(pv=pv, ev=ev, ac=ac, spi=spi, cpi=cpi, status_hint=str(evm_snapshot.get("status") or ""))


def _explain(
    *,
    pv: float,
    ev: float,
    ac: float,
    spi: float | None,
    cpi: float | None,
    status_hint: str,
) -> dict[str, object]:
    if pv == 0 and ev == 0 and ac == 0 and spi is None and cpi is None:
        return {
            "status": "not_available",
            "headline_ko": "EVM 해석에 필요한 데이터가 부족합니다.",
            "summary_ko": "데이터 부족으로 계획가치, 완료가치, 실제투입 원가를 비교할 수 없습니다.",
            "metrics_ko": _metric_labels(),
            "recommended_actions_ko": ["공정별 실행예산과 실적 입력을 먼저 확인하세요."],
        }
    status = _status(status_hint, spi, cpi)
    headline = {
        "healthy": "공정과 원가 흐름이 현재 기준으로 양호합니다.",
        "watch": "공정 또는 원가 지표에 주의가 필요합니다.",
        "risk": "공정 지연 또는 원가 초과 위험이 큽니다.",
        "not_available": "EVM 해석에 필요한 데이터가 부족합니다.",
    }[status]
    summary = (
        f"계획가치(PV)는 {pv:,.0f}, 완료가치(EV)는 {ev:,.0f}, 실제투입원가(AC)는 {ac:,.0f}입니다. "
        f"일정효율(SPI)은 {_fmt(spi)}, 원가효율(CPI)은 {_fmt(cpi)}입니다."
    )
    actions = ["부진공정 TOP 항목과 원가 초과 공종을 함께 확인하세요."]
    if status == "risk":
        actions.insert(0, "SPI/CPI가 낮은 공종의 원인을 현장 입력 데이터와 대조하세요.")
    elif status == "watch":
        actions.insert(0, "주의 지표가 발생한 공종의 실행예산과 실적 입력을 검토하세요.")
    return {
        "status": status,
        "headline_ko": headline,
        "summary_ko": summary,
        "metrics_ko": _metric_labels(),
        "recommended_actions_ko": actions,
    }


def _metric_labels() -> dict[str, str]:
    return {
        "pv": "계획상 이번 기준일까지 완료되어야 할 공사 금액",
        "ev": "실제로 완료된 공사의 예산상 가치",
        "ac": "실제로 투입된 원가",
        "spi": "일정 효율",
        "cpi": "원가 효율",
    }


def _status(status_hint: str, spi: float | None, cpi: float | None) -> str:
    if status_hint in {"healthy", "watch", "risk", "not_available"}:
        return status_hint
    values = [value for value in (spi, cpi) if value is not None]
    if not values:
        return "not_available"
    if any(value < 0.9 for value in values):
        return "risk"
    if any(value < 1.0 for value in values):
        return "watch"
    return "healthy"


def _value(mapping: Mapping[str, object], *keys: str) -> float:
    for key in keys:
        if key in mapping:
            return to_float(mapping[key])
    return 0.0


def _optional_number(value: Any) -> float | None:
    if value is None:
        return None
    return to_float(value)


def _fmt(value: float | None) -> str:
    return "데이터 없음" if value is None else f"{value:.2f}"
