"""MCP tools for cash flow forecasting.

Provides cash flow forecast, funding requirement analysis,
and retention release schedule.
"""
from __future__ import annotations

from typing import Any

from core.cashflow import (
    calculate_funding_requirements,
    forecast_cash_flow,
    get_retention_schedule,
)


def forecast_project_cash_flow(
    db_path: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    payment_terms: str = "NET_30",
    retention_pct: float = 10.0,
    distribution: str = "linear",
    interval: str = "monthly",
    discipline: str | None = None,
) -> dict[str, Any]:
    """Forecast project cash flow with inflows (기성수입) and outflows (원가투입).

    Parameters
    ----------
    db_path : path to the .scheduler file
    start_date / end_date : forecast range (YYYY-MM-DD), auto-detected if omitted
    payment_terms : 지불조건 — 'NET_30', 'NET_45', 'NET_60', 'NET_90', 'MILESTONE'
    retention_pct : 하자보증금 비율 (0~100), 준공 시 정산
    distribution : 비용 분배 방식 — 'linear', 'front_loaded', 'back_loaded', 's_curve'
    interval : 집계 단위 — 'monthly' or 'quarterly'
    discipline : 공종 필터 (optional)

    Returns period-by-period cash flow with inflow, outflow, net, cumulative values.
    """
    return forecast_cash_flow(
        db_path, start_date, end_date,
        payment_terms=payment_terms,
        retention_pct=retention_pct,
        distribution=distribution,
        interval=interval,
        discipline=discipline,
    )


def get_funding_requirements(
    db_path: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    payment_terms: str = "NET_30",
    retention_pct: float = 10.0,
    distribution: str = "linear",
    buffer_pct: float = 10.0,
) -> dict[str, Any]:
    """Calculate project funding requirements — peak deficit, monthly needs, buffer.

    Parameters
    ----------
    db_path : path to the .scheduler file
    buffer_pct : 추가 여유율 (%) — peak funding에 가산
    """
    return calculate_funding_requirements(
        db_path,
        start_date=start_date,
        end_date=end_date,
        payment_terms=payment_terms,
        retention_pct=retention_pct,
        distribution=distribution,
        buffer_pct=buffer_pct,
    )


def get_retention_release_schedule(
    db_path: str,
    *,
    retention_pct: float = 10.0,
    release_days: int = 60,
    discipline: str | None = None,
) -> dict[str, Any]:
    """Get retention (하자보증금) held per discipline and release date.

    Parameters
    ----------
    db_path : path to the .scheduler file
    retention_pct : 하자보증금 비율 (0~100)
    release_days : 준공 후 정산까지 일수
    discipline : 공종 필터 (optional)
    """
    return get_retention_schedule(
        db_path,
        retention_pct=retention_pct,
        release_days=release_days,
        discipline=discipline,
    )
