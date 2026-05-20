from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from core.models import Activity, ActivityCpmResult, Calendar, Project, Relationship, WBS


SCHEMA_VERSION = 1


def initialize_database(path: str | Path) -> None:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS calendars (
                calendar_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                weekmask TEXT NOT NULL,
                holidays TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                calendar_id TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (calendar_id) REFERENCES calendars(calendar_id)
            );
            CREATE TABLE IF NOT EXISTS wbs (
                wbs_id TEXT PRIMARY KEY,
                parent_id TEXT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES wbs(wbs_id)
            );
            CREATE TABLE IF NOT EXISTS activities (
                activity_id TEXT PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                wbs_id TEXT NOT NULL,
                discipline TEXT NOT NULL,
                zone TEXT NOT NULL,
                duration INTEGER NOT NULL,
                cost REAL NOT NULL DEFAULT 0,
                es_workday INTEGER,
                ef_workday INTEGER,
                ls_workday INTEGER,
                lf_workday INTEGER,
                es_date TEXT,
                ef_date TEXT,
                total_float INTEGER,
                is_critical INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (wbs_id) REFERENCES wbs(wbs_id)
            );
            CREATE TABLE IF NOT EXISTS relationships (
                rel_id TEXT PRIMARY KEY,
                pred_id TEXT NOT NULL,
                succ_id TEXT NOT NULL,
                rel_type TEXT NOT NULL,
                lag_days INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (pred_id) REFERENCES activities(activity_id),
                FOREIGN KEY (succ_id) REFERENCES activities(activity_id)
            );
            CREATE INDEX IF NOT EXISTS idx_activities_wbs_id ON activities(wbs_id);
            CREATE INDEX IF NOT EXISTS idx_activities_discipline ON activities(discipline);
            CREATE INDEX IF NOT EXISTS idx_relationships_pred_id ON relationships(pred_id);
            CREATE INDEX IF NOT EXISTS idx_relationships_succ_id ON relationships(succ_id);
            """
        )
        existing = conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
        if existing == 0:
            conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))


def create_calendar(path: str | Path, calendar: Calendar) -> Calendar:
    stamped = _stamp(calendar)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO calendars(calendar_id, name, weekmask, holidays, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                stamped.calendar_id,
                stamped.name,
                stamped.weekmask,
                json.dumps(list(stamped.holidays), ensure_ascii=False),
                stamped.created_at,
                stamped.updated_at,
            ),
        )
    return stamped


def get_calendar(path: str | Path, calendar_id: str) -> Calendar | None:
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM calendars WHERE calendar_id = ?",
            (calendar_id,),
        ).fetchone()
    return _calendar_from_row(row) if row else None


def create_project(path: str | Path, project: Project) -> Project:
    stamped = _stamp(project)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO projects(project_id, name, start_date, calendar_id, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stamped.project_id,
                stamped.name,
                stamped.start_date.isoformat(),
                stamped.calendar_id,
                stamped.description,
                stamped.created_at,
                stamped.updated_at,
            ),
        )
    return stamped


def get_project(path: str | Path, project_id: str) -> Project | None:
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,),
        ).fetchone()
    return _project_from_row(row) if row else None


def create_wbs(path: str | Path, wbs: WBS) -> WBS:
    stamped = _stamp(wbs)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO wbs(wbs_id, parent_id, code, name, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stamped.wbs_id,
                stamped.parent_id,
                stamped.code,
                stamped.name,
                stamped.sort_order,
                stamped.created_at,
                stamped.updated_at,
            ),
        )
    return stamped


def add_wbs(path: str | Path, wbs: WBS) -> WBS:
    return create_wbs(path, wbs)


def list_wbs(path: str | Path) -> list[WBS]:
    with _connect(path) as conn:
        rows = conn.execute("SELECT * FROM wbs ORDER BY sort_order, code").fetchall()
    return [_wbs_from_row(row) for row in rows]


def update_wbs(path: str | Path, wbs: WBS) -> WBS:
    stamped = _stamp(wbs)
    with _connect(path) as conn:
        conn.execute(
            """
            UPDATE wbs
            SET parent_id = ?, code = ?, name = ?, sort_order = ?, updated_at = ?
            WHERE wbs_id = ?
            """,
            (
                stamped.parent_id,
                stamped.code,
                stamped.name,
                stamped.sort_order,
                stamped.updated_at,
                stamped.wbs_id,
            ),
        )
    return stamped


def create_activity(path: str | Path, activity: Activity) -> Activity:
    stamped = _stamp(activity)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO activities(
                activity_id, code, name, wbs_id, discipline, zone, duration, cost,
                es_workday, ef_workday, ls_workday, lf_workday, es_date, ef_date,
                total_float, is_critical, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _activity_values(stamped),
        )
    return stamped


def add_activity(path: str | Path, activity: Activity) -> Activity:
    return create_activity(path, activity)


def list_activities(path: str | Path) -> list[Activity]:
    with _connect(path) as conn:
        rows = conn.execute("SELECT * FROM activities ORDER BY code").fetchall()
    return [_activity_from_row(row) for row in rows]


def update_activity(path: str | Path, activity: Activity) -> Activity:
    stamped = _stamp(activity)
    with _connect(path) as conn:
        conn.execute(
            """
            UPDATE activities
            SET code = ?,
                name = ?,
                wbs_id = ?,
                discipline = ?,
                zone = ?,
                duration = ?,
                cost = ?,
                es_workday = ?,
                ef_workday = ?,
                ls_workday = ?,
                lf_workday = ?,
                es_date = ?,
                ef_date = ?,
                total_float = ?,
                is_critical = ?,
                updated_at = ?
            WHERE activity_id = ?
            """,
            (
                stamped.code,
                stamped.name,
                stamped.wbs_id,
                stamped.discipline,
                stamped.zone,
                stamped.duration,
                stamped.cost,
                stamped.es_workday,
                stamped.ef_workday,
                stamped.ls_workday,
                stamped.lf_workday,
                stamped.es_date.isoformat() if stamped.es_date else None,
                stamped.ef_date.isoformat() if stamped.ef_date else None,
                stamped.total_float,
                int(stamped.is_critical),
                stamped.updated_at,
                stamped.activity_id,
            ),
        )
    return stamped


def create_relationship(path: str | Path, relationship: Relationship) -> Relationship:
    stamped = _stamp(relationship)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO relationships(rel_id, pred_id, succ_id, rel_type, lag_days, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stamped.rel_id,
                stamped.pred_id,
                stamped.succ_id,
                stamped.rel_type,
                stamped.lag_days,
                stamped.created_at,
                stamped.updated_at,
            ),
        )
    return stamped


def add_relationship(path: str | Path, relationship: Relationship) -> Relationship:
    return create_relationship(path, relationship)


def list_relationships(path: str | Path) -> list[Relationship]:
    with _connect(path) as conn:
        rows = conn.execute("SELECT * FROM relationships ORDER BY rel_id").fetchall()
    return [_relationship_from_row(row) for row in rows]


def delete_relationship(path: str | Path, rel_id: str) -> None:
    with _connect(path) as conn:
        conn.execute("DELETE FROM relationships WHERE rel_id = ?", (rel_id,))


def update_calendar(path: str | Path, calendar: Calendar) -> Calendar:
    stamped = _stamp(calendar)
    with _connect(path) as conn:
        conn.execute(
            """
            UPDATE calendars
            SET name = ?, weekmask = ?, holidays = ?, updated_at = ?
            WHERE calendar_id = ?
            """,
            (
                stamped.name,
                stamped.weekmask,
                json.dumps(list(stamped.holidays), ensure_ascii=False),
                stamped.updated_at,
                stamped.calendar_id,
            ),
        )
    return stamped


def list_indexes(path: str | Path) -> set[str]:
    with _connect(path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
    return {row["name"] for row in rows}


def update_cpm_results(path: str | Path, results: list[ActivityCpmResult]) -> None:
    timestamp = _now()
    with _connect(path) as conn:
        conn.executemany(
            """
            UPDATE activities
            SET es_workday = ?,
                ef_workday = ?,
                ls_workday = ?,
                lf_workday = ?,
                es_date = ?,
                ef_date = ?,
                total_float = ?,
                is_critical = ?,
                updated_at = ?
            WHERE activity_id = ?
            """,
            [
                (
                    result.es_workday,
                    result.ef_workday,
                    result.ls_workday,
                    result.lf_workday,
                    result.es_date.isoformat() if result.es_date else None,
                    result.ef_date.isoformat() if result.ef_date else None,
                    result.total_float,
                    int(result.is_critical),
                    timestamp,
                    result.activity_id,
                )
                for result in results
            ],
        )


def load_project_summary(path: str | Path) -> dict[str, object]:
    with _connect(path) as conn:
        project_row = conn.execute("SELECT * FROM projects ORDER BY created_at LIMIT 1").fetchone()
        activity_count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
        relationship_count = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        cost_total = conn.execute("SELECT COALESCE(SUM(cost), 0) FROM activities").fetchone()[0]
        completion_workday = conn.execute("SELECT MAX(ef_workday) FROM activities").fetchone()[0]

    return {
        "project": _project_from_row(project_row) if project_row else None,
        "activity_count": activity_count,
        "relationship_count": relationship_count,
        "cost_total": cost_total,
        "completion_workday": completion_workday,
    }


def _connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stamp(model):
    timestamp = _now()
    return replace(
        model,
        created_at=model.created_at or timestamp,
        updated_at=model.updated_at or timestamp,
    )


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _activity_values(activity: Activity) -> tuple[object, ...]:
    return (
        activity.activity_id,
        activity.code,
        activity.name,
        activity.wbs_id,
        activity.discipline,
        activity.zone,
        activity.duration,
        activity.cost,
        activity.es_workday,
        activity.ef_workday,
        activity.ls_workday,
        activity.lf_workday,
        activity.es_date.isoformat() if activity.es_date else None,
        activity.ef_date.isoformat() if activity.ef_date else None,
        activity.total_float,
        int(activity.is_critical),
        activity.created_at,
        activity.updated_at,
    )


def _project_from_row(row: sqlite3.Row) -> Project:
    return Project(
        project_id=row["project_id"],
        name=row["name"],
        start_date=date.fromisoformat(row["start_date"]),
        calendar_id=row["calendar_id"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _wbs_from_row(row: sqlite3.Row) -> WBS:
    return WBS(
        wbs_id=row["wbs_id"],
        parent_id=row["parent_id"],
        code=row["code"],
        name=row["name"],
        sort_order=row["sort_order"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _activity_from_row(row: sqlite3.Row) -> Activity:
    return Activity(
        activity_id=row["activity_id"],
        code=row["code"],
        name=row["name"],
        wbs_id=row["wbs_id"],
        discipline=row["discipline"],
        zone=row["zone"],
        duration=row["duration"],
        cost=row["cost"],
        es_workday=row["es_workday"],
        ef_workday=row["ef_workday"],
        ls_workday=row["ls_workday"],
        lf_workday=row["lf_workday"],
        es_date=_parse_date(row["es_date"]),
        ef_date=_parse_date(row["ef_date"]),
        total_float=row["total_float"],
        is_critical=bool(row["is_critical"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _relationship_from_row(row: sqlite3.Row) -> Relationship:
    return Relationship(
        rel_id=row["rel_id"],
        pred_id=row["pred_id"],
        succ_id=row["succ_id"],
        rel_type=row["rel_type"],
        lag_days=row["lag_days"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _calendar_from_row(row: sqlite3.Row) -> Calendar:
    holidays: Iterable[str] = json.loads(row["holidays"])
    return Calendar(
        calendar_id=row["calendar_id"],
        name=row["name"],
        weekmask=row["weekmask"],
        holidays=tuple(holidays),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
