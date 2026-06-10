"""Active project context management.

Allows users (especially non-technical site staff) to set a "current project"
once, so subsequent tool calls can omit the db_path argument. Solves the UX
barrier where every one of the 60 MCP tools required an explicit file path.

The context is stored as a small JSON file under the user's home directory:
    ~/.smart_scheduler/active_context.json

Design notes
------------
- Single active context per machine for now (multi-user separation can be
  layered later by keying on an env var or user id).
- ``resolve_db_path`` is the integration point: tools call it with whatever the
  caller passed (possibly empty), and it falls back to the stored context.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_CONTEXT_DIR = Path.home() / ".smart_scheduler"
_CONTEXT_FILE = _CONTEXT_DIR / "active_context.json"


def _context_path() -> Path:
    return _CONTEXT_FILE


def set_active_project(
    db_path: str | Path,
    project_id: str = "",
    *,
    label: str = "",
) -> dict[str, Any]:
    """Persist the active project context.

    Parameters
    ----------
    db_path : path to the .scheduler file to make active
    project_id : optional project id within that DB
    label : optional human-friendly label (e.g. '홍은동 가로주택')
    """
    resolved = str(Path(db_path))
    if not Path(resolved).exists():
        return {
            "ok": False,
            "error": f"파일을 찾을 수 없습니다: {resolved}",
        }

    payload = {
        "db_path": resolved,
        "project_id": project_id,
        "label": label,
        "set_at": datetime.now(timezone.utc).isoformat(),
    }
    _CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    _context_path().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"ok": True, **payload}


def get_active_project() -> dict[str, Any]:
    """Return the stored active project context, if any."""
    path = _context_path()
    if not path.exists():
        return {"ok": False, "active": False, "error": "활성 프로젝트가 설정되지 않았습니다."}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "active": False, "error": f"컨텍스트 읽기 실패: {exc}"}

    db_path = payload.get("db_path", "")
    exists = bool(db_path) and Path(db_path).exists()
    return {
        "ok": True,
        "active": True,
        "db_path": db_path,
        "project_id": payload.get("project_id", ""),
        "label": payload.get("label", ""),
        "set_at": payload.get("set_at", ""),
        "file_exists": exists,
    }


def clear_active_project() -> dict[str, Any]:
    """Remove the stored active project context."""
    path = _context_path()
    existed = path.exists()
    if existed:
        path.unlink()
    return {"ok": True, "cleared": existed}


def resolve_db_path(db_path: str | Path | None = None) -> str:
    """Resolve a usable db_path, falling back to the active context.

    Tools should call this with whatever the caller supplied. If the caller
    passed a non-empty path, it wins; otherwise the active context is used.

    Raises
    ------
    ValueError
        If no path was given and no active context is set.
    """
    if db_path is not None and str(db_path).strip():
        return str(db_path)

    ctx = get_active_project()
    if ctx.get("active") and ctx.get("db_path"):
        return str(ctx["db_path"])

    raise ValueError(
        "db_path가 지정되지 않았고 활성 프로젝트도 없습니다. "
        "먼저 set_active_project로 현재 프로젝트를 설정하세요."
    )
