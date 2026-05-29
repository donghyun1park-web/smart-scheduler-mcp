from __future__ import annotations

import re
import uuid
from datetime import date
from pathlib import Path
from typing import cast

from core import db
from core.models import Calendar, Project


DEFAULT_PROJECTS_DIR = Path.home() / ".smart-scheduler" / "projects"


def list_projects(projects_dir: str | Path | None = None) -> dict[str, object]:
    """List ``.scheduler`` projects under ``projects_dir`` (default ~/.smart-scheduler/projects).

    Returns ``{"ok": True, "projects": [{"project_path", "name", "start_date"}, ...]}``.
    Unreadable projects are silently skipped.
    """
    root = _projects_dir(projects_dir)
    root.mkdir(parents=True, exist_ok=True)
    projects = []
    for path in sorted(root.glob("*.scheduler")):
        loaded = load_project(path)
        if loaded["ok"]:
            project = cast(dict[str, object], loaded["project"])
            projects.append(
                {
                    "project_path": str(path),
                    "name": project["name"],
                    "start_date": project["start_date"],
                }
            )
    return {"ok": True, "projects": projects}


def load_project(project_path: str | Path) -> dict[str, object]:
    """Load project metadata and summary counts from a ``.scheduler`` file.

    On success returns ``{"ok": True, "project": {...}, "summary": {activity_count, ...}}``.
    On failure returns ``{"ok": False, "error_code": ..., "error_message": ...}``.
    """
    path = Path(project_path)
    summary = db.load_project_summary(path)
    project = summary["project"]
    if project is None:
        return {
            "ok": False,
            "error_code": "PROJECT_NOT_FOUND",
            "error_message": "Project not found",
            "error": "Project not found",
            "project_path": str(path),
        }
    if not isinstance(project, Project):
        return {
            "ok": False,
            "error_code": "INVALID_PROJECT_SUMMARY",
            "error_message": "Invalid project summary",
            "error": "Invalid project summary",
            "project_path": str(path),
        }
    return {
        "ok": True,
        "project_path": str(path),
        "project": _project_dict(project),
        "summary": {
            "activity_count": summary["activity_count"],
            "relationship_count": summary["relationship_count"],
            "cost_total": summary["cost_total"],
            "completion_workday": summary["completion_workday"],
        },
    }


def create_project(
    name: str,
    start_date: str,
    calendar: dict[str, object],
    description: str = "",
    projects_dir: str | Path | None = None,
) -> dict[str, object]:
    """Create a new ``.scheduler`` SQLite project with the given calendar.

    Args:
        name: Display name; also slugified into the filename.
        start_date: ISO date (``YYYY-MM-DD``) used as project workday 0.
        calendar: ``{"calendar_id", "name", "weekmask", "holidays"}``;
            ``weekmask`` is 7 chars of ``1``/``0`` (Mon→Sun, e.g. ``1111100`` = 5-day).
    """
    root = _projects_dir(projects_dir)
    root.mkdir(parents=True, exist_ok=True)
    project_id = str(uuid.uuid4())
    calendar_id = str(calendar.get("calendar_id") or "default")
    path = root / f"{_slug(name)}-{project_id[:8]}.scheduler"
    db.initialize_database(path)
    db.create_calendar(
        path,
        Calendar(
            calendar_id=calendar_id,
            name=str(calendar.get("name") or "Korean 5-day"),
            weekmask=str(calendar.get("weekmask") or "1111100"),
            holidays=tuple(cast(list[str] | tuple[str, ...], calendar.get("holidays") or ())),
        ),
    )
    project = db.create_project(
        path,
        Project(
            project_id=project_id,
            name=name,
            start_date=date.fromisoformat(start_date),
            calendar_id=calendar_id,
            description=description,
        ),
    )
    return {"ok": True, "project_path": str(path), "project": _project_dict(project)}


def _projects_dir(projects_dir: str | Path | None) -> Path:
    return Path(projects_dir) if projects_dir is not None else DEFAULT_PROJECTS_DIR


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9가-힣_-]+", "-", value.strip()).strip("-")
    return slug.lower() or "project"


def _project_dict(project: Project) -> dict[str, object]:
    return {
        "project_id": project.project_id,
        "name": project.name,
        "start_date": project.start_date.isoformat(),
        "calendar_id": project.calendar_id,
        "description": project.description,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }
