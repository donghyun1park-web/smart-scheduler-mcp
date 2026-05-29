"""MCP tool wrappers for active project context management."""
from __future__ import annotations

from typing import Any


def set_active_project(
    db_path: str,
    project_id: str = "",
    label: str = "",
) -> dict[str, Any]:
    """현재 작업할 프로젝트(.scheduler 파일)를 설정합니다.

    한 번 설정하면 이후 도구 호출 시 db_path를 생략할 수 있습니다.
    현장 담당자가 매번 파일 경로를 입력하지 않아도 되도록 합니다.

    예) "홍은동 현장 열어줘" → set_active_project("C:/.../hongneundong.scheduler",
        label="홍은동 가로주택")
    """
    from core.context import set_active_project as _set

    return _set(db_path, project_id, label=label)


def get_active_project() -> dict[str, Any]:
    """현재 설정된 활성 프로젝트 정보를 반환합니다.

    활성 프로젝트가 없으면 active=False를 반환합니다.
    """
    from core.context import get_active_project as _get

    return _get()


def clear_active_project() -> dict[str, Any]:
    """활성 프로젝트 설정을 해제합니다."""
    from core.context import clear_active_project as _clear

    return _clear()
