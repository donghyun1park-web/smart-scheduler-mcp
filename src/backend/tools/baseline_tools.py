"""MCP tool wrappers for baseline schedule management."""
from __future__ import annotations

from typing import Any


def establish_baseline(
    db_path: str = "",
    label: str = "기준공정표",
    approved_by: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """현재 공정표를 기준선(Baseline)으로 고정합니다.

    각 활동의 계획 착수일·완료일·기간을 스냅샷으로 저장합니다.
    이후 compare_to_baseline으로 현재 일정과 비교해 지연/단축을 측정합니다.

    착공 시점에 한 번 수립하는 것이 일반적입니다.
    dry_run=True(기본값)이면 미리보기만 수행합니다.
    """
    from core.baseline import establish_baseline as _establish
    from core.context import resolve_db_path

    return _establish(
        resolve_db_path(db_path),
        label=label,
        approved_by=approved_by,
        dry_run=dry_run,
    )


def list_baselines(db_path: str = "") -> dict[str, Any]:
    """수립된 기준공정표 목록을 조회합니다."""
    from core.baseline import list_baselines as _list
    from core.context import resolve_db_path

    return _list(resolve_db_path(db_path))


def compare_to_baseline(
    db_path: str = "",
    baseline_id: str = "",
    top_n: int = 20,
) -> dict[str, Any]:
    """현재 공정표를 기준선과 비교합니다.

    활동별 완료일 변동(현재-기준, +면 지연)과 전체 공기 증감을 반환합니다.
    baseline_id를 생략하면 가장 최근 기준선과 비교합니다.
    """
    from core.baseline import compare_to_baseline as _compare
    from core.context import resolve_db_path

    return _compare(
        resolve_db_path(db_path),
        baseline_id=baseline_id or None,
        top_n=top_n,
    )
