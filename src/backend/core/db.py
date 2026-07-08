from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from core.cost import calculate_billing_rate, calculate_cost_execution_rate
from core.disciplines import normalize_discipline
from core.models import (
    Activity,
    ActivityCpmResult,
    BaselineSnapshot,
    Calendar,
    ChangeLogEntry,
    ChangeOrder,
    ChangeOrderItem,
    CostItem,
    DailyRecord,
    DelayEvent,
    InspectionRecord,
    MaterialRecord,
    NotificationLog,
    Project,
    ProjectSettings,
    Relationship,
    WBS,
)
from core.progress import calculate_quantity_progress


SCHEMA_VERSION = 5


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
                progress_pct REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'PENDING',
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
            CREATE TABLE IF NOT EXISTS daily_records (
                record_id TEXT PRIMARY KEY,
                activity_id TEXT NOT NULL,
                work_date TEXT NOT NULL,
                planned_qty REAL NOT NULL DEFAULT 0,
                actual_qty REAL NOT NULL DEFAULT 0,
                workers INTEGER NOT NULL DEFAULT 0,
                equipment TEXT NOT NULL DEFAULT '',
                owner TEXT NOT NULL DEFAULT '',
                remarks TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
            );
            CREATE TABLE IF NOT EXISTS cost_items (
                cost_item_id TEXT PRIMARY KEY,
                activity_id TEXT NOT NULL,
                contract_amount REAL NOT NULL DEFAULT 0,
                execution_budget REAL NOT NULL DEFAULT 0,
                invested_cost REAL NOT NULL DEFAULT 0,
                billing_amount REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
            );
            CREATE TABLE IF NOT EXISTS baseline_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                baseline_id TEXT NOT NULL,
                project_id TEXT NOT NULL DEFAULT '',
                activity_id TEXT NOT NULL,
                start_date TEXT,
                finish_date TEXT,
                duration INTEGER NOT NULL DEFAULT 0,
                revision TEXT NOT NULL,
                approved_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
            );
            CREATE TABLE IF NOT EXISTS materials (
                material_id TEXT PRIMARY KEY,
                activity_id TEXT NOT NULL,
                material_name TEXT NOT NULL,
                order_date TEXT,
                expected_date TEXT,
                actual_date TEXT,
                status TEXT NOT NULL DEFAULT 'planned',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
            );
            CREATE TABLE IF NOT EXISTS inspections (
                inspection_id TEXT PRIMARY KEY,
                activity_id TEXT NOT NULL,
                inspection_type TEXT NOT NULL,
                planned_date TEXT,
                actual_date TEXT,
                status TEXT NOT NULL DEFAULT 'planned',
                approver TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
            );
            CREATE TABLE IF NOT EXISTS change_log (
                change_id TEXT PRIMARY KEY,
                target_table TEXT NOT NULL,
                target_id TEXT NOT NULL,
                before_value TEXT NOT NULL DEFAULT '',
                after_value TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                user TEXT NOT NULL DEFAULT '',
                approved_by TEXT NOT NULL DEFAULT '',
                changed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS project_settings (
                settings_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                disciplines TEXT NOT NULL DEFAULT '[]',
                thresholds TEXT NOT NULL DEFAULT '{}',
                report_style TEXT NOT NULL DEFAULT 'weekly_meeting',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            );
            CREATE TABLE IF NOT EXISTS change_orders (
                co_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                co_type TEXT NOT NULL DEFAULT 'scope_addition',
                status TEXT NOT NULL DEFAULT 'draft',
                requested_by TEXT NOT NULL DEFAULT '',
                approved_by TEXT NOT NULL DEFAULT '',
                request_date TEXT,
                approval_date TEXT,
                direct_cost REAL NOT NULL DEFAULT 0,
                markup_pct REAL NOT NULL DEFAULT 0,
                total_cost REAL NOT NULL DEFAULT 0,
                schedule_impact_days INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS change_order_items (
                co_item_id TEXT PRIMARY KEY,
                co_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                cost_change REAL NOT NULL DEFAULT 0,
                duration_change INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (co_id) REFERENCES change_orders(co_id),
                FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
            );
            CREATE TABLE IF NOT EXISTS delay_events (
                delay_event_id TEXT PRIMARY KEY,
                activity_id TEXT NOT NULL,
                delay_type TEXT NOT NULL DEFAULT 'non_excusable',
                cause_code TEXT NOT NULL DEFAULT 'other',
                responsible_party TEXT NOT NULL DEFAULT '',
                start_date TEXT,
                end_date TEXT,
                delay_days INTEGER NOT NULL DEFAULT 0,
                cost_impact REAL NOT NULL DEFAULT 0,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_cost_items_activity_unique
                ON cost_items(activity_id);
            CREATE INDEX IF NOT EXISTS idx_activities_wbs_id ON activities(wbs_id);
            CREATE INDEX IF NOT EXISTS idx_activities_discipline ON activities(discipline);
            CREATE INDEX IF NOT EXISTS idx_relationships_pred_id ON relationships(pred_id);
            CREATE INDEX IF NOT EXISTS idx_relationships_succ_id ON relationships(succ_id);
            CREATE INDEX IF NOT EXISTS idx_daily_records_activity_date
                ON daily_records(activity_id, work_date);
            CREATE INDEX IF NOT EXISTS idx_cost_items_activity_id
                ON cost_items(activity_id);
            CREATE INDEX IF NOT EXISTS idx_baseline_snapshots_baseline_id
                ON baseline_snapshots(baseline_id);
            CREATE INDEX IF NOT EXISTS idx_materials_activity_status
                ON materials(activity_id, status);
            CREATE INDEX IF NOT EXISTS idx_inspections_activity_status
                ON inspections(activity_id, status);
            CREATE INDEX IF NOT EXISTS idx_change_log_target
                ON change_log(target_table, target_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_project_settings_project_unique
                ON project_settings(project_id);
            CREATE INDEX IF NOT EXISTS idx_baseline_snapshots_project_id
                ON baseline_snapshots(project_id);
            CREATE INDEX IF NOT EXISTS idx_change_orders_status
                ON change_orders(status);
            CREATE INDEX IF NOT EXISTS idx_co_items_co_id
                ON change_order_items(co_id);
            CREATE INDEX IF NOT EXISTS idx_co_items_activity
                ON change_order_items(activity_id);
            CREATE INDEX IF NOT EXISTS idx_delay_events_activity
                ON delay_events(activity_id);
            CREATE INDEX IF NOT EXISTS idx_delay_events_type
                ON delay_events(delay_type);
            CREATE INDEX IF NOT EXISTS idx_delay_events_status
                ON delay_events(status);
            CREATE TABLE IF NOT EXISTS notification_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id TEXT NOT NULL,
                target_role TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                message TEXT NOT NULL,
                is_sent INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
            );
            CREATE INDEX IF NOT EXISTS idx_notification_logs_activity
                ON notification_logs(activity_id);
            CREATE INDEX IF NOT EXISTS idx_notification_logs_sent
                ON notification_logs(is_sent);
            CREATE TABLE IF NOT EXISTS kakao_users (
                bot_user_key TEXT PRIMARY KEY,
                owner_name TEXT NOT NULL DEFAULT '',
                discipline TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        current_version = int(row["version"]) if row else 0
        if current_version < 3:
            _migrate_add_progress_pct(conn)
        if current_version < 4:
            _migrate_add_activity_status(conn)
        if row is None:
            conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
        elif current_version < SCHEMA_VERSION:
            conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))


def _migrate_add_activity_status(conn: sqlite3.Connection) -> None:
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}
    if "status" not in cols:
        conn.execute("ALTER TABLE activities ADD COLUMN status TEXT NOT NULL DEFAULT 'PENDING'")


def _migrate_add_progress_pct(conn: sqlite3.Connection) -> None:
    """v2 → v3: add ``progress_pct REAL NOT NULL DEFAULT 0`` to activities.

    Safe to run on a freshly-created v3 DB — checks the column before adding.
    """
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}
    if "progress_pct" not in cols:
        conn.execute("ALTER TABLE activities ADD COLUMN progress_pct REAL NOT NULL DEFAULT 0")


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
                total_float, is_critical, progress_pct, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                progress_pct = ?,
                status = ?,
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
                float(stamped.progress_pct),
                stamped.status,
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


def list_tables(path: str | Path) -> set[str]:
    with _connect(path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def list_table_columns(path: str | Path, table_name: str) -> list[str]:
    with _connect(path) as conn:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row["name"] for row in rows]


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


def create_daily_record(path: str | Path, record: DailyRecord) -> DailyRecord:
    stamped = _stamp(record)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO daily_records(
                record_id, activity_id, work_date, planned_qty, actual_qty,
                workers, equipment, owner, remarks, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stamped.record_id,
                stamped.activity_id,
                stamped.work_date.isoformat(),
                stamped.planned_qty,
                stamped.actual_qty,
                stamped.workers,
                stamped.equipment,
                stamped.owner,
                stamped.remarks,
                stamped.created_at,
                stamped.updated_at,
            ),
        )
    return stamped


def list_daily_records(
    path: str | Path,
    *,
    activity_id: str | None = None,
    work_date: str | date | None = None,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> list[DailyRecord]:
    clauses: list[str] = []
    params: list[object] = []
    if activity_id is not None:
        clauses.append("activity_id = ?")
        params.append(activity_id)
    if work_date is not None:
        clauses.append("work_date = ?")
        params.append(_date_param(work_date))
    if start_date is not None:
        clauses.append("work_date >= ?")
        params.append(_date_param(start_date))
    if end_date is not None:
        clauses.append("work_date <= ?")
        params.append(_date_param(end_date))
    query = "SELECT * FROM daily_records"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY work_date, record_id"
    with _connect(path) as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_daily_record_from_row(row) for row in rows]


def delete_daily_records(
    path: str | Path,
    *,
    activity_id: str,
    work_date: str | date,
) -> int:
    with _connect(path) as conn:
        cursor = conn.execute(
            "DELETE FROM daily_records WHERE activity_id = ? AND work_date = ?",
            (activity_id, _date_param(work_date)),
        )
    return cursor.rowcount


def get_cumulative_qty(path: str | Path, activity_id: str) -> dict[str, float]:
    with _connect(path) as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(planned_qty), 0) AS planned_qty,
                   COALESCE(SUM(actual_qty), 0) AS actual_qty
            FROM daily_records
            WHERE activity_id = ?
            """,
            (activity_id,),
        ).fetchone()
    planned_qty = float(row["planned_qty"])
    actual_qty = float(row["actual_qty"])
    return {
        "planned_qty": planned_qty,
        "actual_qty": actual_qty,
        "progress_pct": calculate_quantity_progress(planned_qty, actual_qty),
    }


def upsert_cost_item(path: str | Path, item: CostItem) -> CostItem:
    stamped = _stamp(item)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO cost_items(
                cost_item_id, activity_id, contract_amount, execution_budget,
                invested_cost, billing_amount, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(activity_id) DO UPDATE SET
                cost_item_id = excluded.cost_item_id,
                contract_amount = excluded.contract_amount,
                execution_budget = excluded.execution_budget,
                invested_cost = excluded.invested_cost,
                billing_amount = excluded.billing_amount,
                updated_at = excluded.updated_at
            """,
            (
                stamped.cost_item_id,
                stamped.activity_id,
                stamped.contract_amount,
                stamped.execution_budget,
                stamped.invested_cost,
                stamped.billing_amount,
                stamped.created_at,
                stamped.updated_at,
            ),
        )
    return stamped


def list_cost_items(path: str | Path, *, activity_id: str | None = None) -> list[CostItem]:
    query = "SELECT * FROM cost_items"
    params: tuple[object, ...] = ()
    if activity_id is not None:
        query += " WHERE activity_id = ?"
        params = (activity_id,)
    query += " ORDER BY activity_id"
    with _connect(path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_cost_item_from_row(row) for row in rows]


def get_cost_summary(path: str | Path) -> dict[str, float]:
    with _connect(path) as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(contract_amount), 0) AS contract_amount,
                   COALESCE(SUM(execution_budget), 0) AS execution_budget,
                   COALESCE(SUM(invested_cost), 0) AS invested_cost,
                   COALESCE(SUM(billing_amount), 0) AS billing_amount
            FROM cost_items
            """
        ).fetchone()
    contract_amount = float(row["contract_amount"])
    execution_budget = float(row["execution_budget"])
    invested_cost = float(row["invested_cost"])
    billing_amount = float(row["billing_amount"])
    return {
        "contract_amount": contract_amount,
        "execution_budget": execution_budget,
        "invested_cost": invested_cost,
        "billing_amount": billing_amount,
        "cost_execution_rate": calculate_cost_execution_rate(execution_budget, invested_cost),
        "billing_rate": calculate_billing_rate(contract_amount, billing_amount),
    }


def create_material_record(path: str | Path, record: MaterialRecord) -> MaterialRecord:
    stamped = _stamp(record)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO materials(
                material_id, activity_id, material_name, order_date, expected_date,
                actual_date, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _material_values(stamped),
        )
    return stamped


def list_materials(
    path: str | Path,
    *,
    activity_id: str | None = None,
    status: str | None = None,
) -> list[MaterialRecord]:
    rows = _select_with_optional_filters(
        path,
        "materials",
        {"activity_id": activity_id, "status": status},
        "activity_id, material_id",
    )
    return [_material_from_row(row) for row in rows]


def update_material_status(
    path: str | Path,
    material_id: str,
    *,
    actual_date: str | date | None = None,
    status: str,
) -> MaterialRecord:
    timestamp = _now()
    with _connect(path) as conn:
        conn.execute(
            """
            UPDATE materials
            SET actual_date = ?, status = ?, updated_at = ?
            WHERE material_id = ?
            """,
            (_optional_date_param(actual_date), status, timestamp, material_id),
        )
        row = conn.execute("SELECT * FROM materials WHERE material_id = ?", (material_id,)).fetchone()
    if row is None:
        raise ValueError(f"Material not found: {material_id}")
    return _material_from_row(row)


def create_inspection_record(path: str | Path, record: InspectionRecord) -> InspectionRecord:
    stamped = _stamp(record)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO inspections(
                inspection_id, activity_id, inspection_type, planned_date,
                actual_date, status, approver, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _inspection_values(stamped),
        )
    return stamped


def list_inspections(
    path: str | Path,
    *,
    activity_id: str | None = None,
    status: str | None = None,
) -> list[InspectionRecord]:
    rows = _select_with_optional_filters(
        path,
        "inspections",
        {"activity_id": activity_id, "status": status},
        "activity_id, inspection_id",
    )
    return [_inspection_from_row(row) for row in rows]


def update_inspection_status(
    path: str | Path,
    inspection_id: str,
    *,
    actual_date: str | date | None = None,
    status: str,
    approver: str | None = None,
) -> InspectionRecord:
    timestamp = _now()
    with _connect(path) as conn:
        conn.execute(
            """
            UPDATE inspections
            SET actual_date = ?, status = ?, approver = COALESCE(?, approver), updated_at = ?
            WHERE inspection_id = ?
            """,
            (_optional_date_param(actual_date), status, approver, timestamp, inspection_id),
        )
        row = conn.execute("SELECT * FROM inspections WHERE inspection_id = ?", (inspection_id,)).fetchone()
    if row is None:
        raise ValueError(f"Inspection not found: {inspection_id}")
    return _inspection_from_row(row)


def log_change(path: str | Path, entry: ChangeLogEntry) -> ChangeLogEntry:
    stamped = _stamp(entry)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO change_log(
                change_id, target_table, target_id, before_value, after_value,
                reason, user, approved_by, changed_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stamped.change_id,
                stamped.target_table,
                stamped.target_id,
                stamped.before_value,
                stamped.after_value,
                stamped.reason,
                stamped.user,
                stamped.approved_by,
                stamped.changed_at.isoformat() if stamped.changed_at else None,
                stamped.created_at,
                stamped.updated_at,
            ),
        )
    return stamped


def list_change_log(
    path: str | Path,
    *,
    target_table: str | None = None,
    target_id: str | None = None,
) -> list[ChangeLogEntry]:
    rows = _select_with_optional_filters(
        path,
        "change_log",
        {"target_table": target_table, "target_id": target_id},
        "created_at, change_id",
    )
    return [_change_log_from_row(row) for row in rows]


def upsert_project_settings(path: str | Path, settings: ProjectSettings) -> ProjectSettings:
    stamped = _stamp(
        replace(
            settings,
            disciplines=tuple(normalize_discipline(value) for value in settings.disciplines),
        )
    )
    thresholds = json.dumps(stamped.thresholds or {}, ensure_ascii=False)
    disciplines = json.dumps(list(stamped.disciplines), ensure_ascii=False)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO project_settings(
                settings_id, project_id, disciplines, thresholds, report_style,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                settings_id = excluded.settings_id,
                disciplines = excluded.disciplines,
                thresholds = excluded.thresholds,
                report_style = excluded.report_style,
                updated_at = excluded.updated_at
            """,
            (
                stamped.settings_id,
                stamped.project_id,
                disciplines,
                thresholds,
                stamped.report_style,
                stamped.created_at,
                stamped.updated_at,
            ),
        )
    return stamped


def get_project_settings(path: str | Path, project_id: str) -> ProjectSettings | None:
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM project_settings WHERE project_id = ?",
            (project_id,),
        ).fetchone()
    return _project_settings_from_row(row) if row else None


def create_baseline_snapshot(path: str | Path, snapshot: BaselineSnapshot) -> BaselineSnapshot:
    stamped = _stamp(snapshot)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO baseline_snapshots(
                snapshot_id, baseline_id, project_id, activity_id, start_date,
                finish_date, duration, revision, approved_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stamped.snapshot_id,
                stamped.baseline_id,
                stamped.project_id,
                stamped.activity_id,
                stamped.start_date.isoformat() if stamped.start_date else None,
                stamped.finish_date.isoformat() if stamped.finish_date else None,
                stamped.duration,
                stamped.revision,
                stamped.approved_by,
                stamped.created_at,
                stamped.updated_at,
            ),
        )
    return stamped


def list_baseline_snapshots(
    path: str | Path,
    *,
    project_id: str | None = None,
    baseline_id: str | None = None,
) -> list[BaselineSnapshot]:
    rows = _select_with_optional_filters(
        path,
        "baseline_snapshots",
        {"project_id": project_id, "baseline_id": baseline_id},
        "created_at, snapshot_id",
    )
    return [_baseline_snapshot_from_row(row) for row in rows]


def get_latest_baseline_snapshot(path: str | Path, project_id: str) -> BaselineSnapshot | None:
    with _connect(path) as conn:
        row = conn.execute(
            """
            SELECT * FROM baseline_snapshots
            WHERE project_id = ?
            ORDER BY created_at DESC, snapshot_id DESC
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
    return _baseline_snapshot_from_row(row) if row else None


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


# ---------------------------------------------------------------------------
# Change orders CRUD
# ---------------------------------------------------------------------------


def create_change_order(path: str | Path, co: ChangeOrder) -> ChangeOrder:
    stamped = _stamp(co)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO change_orders(
                co_id, title, description, co_type, status,
                requested_by, approved_by, request_date, approval_date,
                direct_cost, markup_pct, total_cost, schedule_impact_days,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stamped.co_id, stamped.title, stamped.description,
                stamped.co_type, stamped.status,
                stamped.requested_by, stamped.approved_by,
                stamped.request_date.isoformat() if stamped.request_date else None,
                stamped.approval_date.isoformat() if stamped.approval_date else None,
                stamped.direct_cost, stamped.markup_pct, stamped.total_cost,
                stamped.schedule_impact_days,
                stamped.created_at, stamped.updated_at,
            ),
        )
    return stamped


def list_change_orders(
    path: str | Path,
    *,
    status: str | None = None,
    co_type: str | None = None,
) -> list[ChangeOrder]:
    rows = _select_with_optional_filters(
        path, "change_orders",
        {"status": status, "co_type": co_type},
        "created_at DESC",
    )
    return [_change_order_from_row(row) for row in rows]


def get_change_order(path: str | Path, co_id: str) -> ChangeOrder | None:
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM change_orders WHERE co_id = ?", (co_id,),
        ).fetchone()
    return _change_order_from_row(row) if row else None


def update_change_order_status(
    path: str | Path,
    co_id: str,
    *,
    status: str,
    approved_by: str = "",
    approval_date: date | None = None,
) -> ChangeOrder:
    timestamp = _now()
    with _connect(path) as conn:
        params: list[object] = [status, approved_by, timestamp, co_id]
        sql = "UPDATE change_orders SET status = ?, approved_by = ?, updated_at = ?"
        if approval_date:
            sql += ", approval_date = ?"
            params = [status, approved_by, timestamp, approval_date.isoformat(), co_id]
        sql += " WHERE co_id = ?"
        conn.execute(sql, tuple(params))
        row = conn.execute(
            "SELECT * FROM change_orders WHERE co_id = ?", (co_id,),
        ).fetchone()
    if not row:
        raise ValueError(f"Change order not found: {co_id}")
    return _change_order_from_row(row)


def create_change_order_item(path: str | Path, item: ChangeOrderItem) -> ChangeOrderItem:
    stamped = _stamp(item)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO change_order_items(
                co_item_id, co_id, activity_id, cost_change,
                duration_change, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stamped.co_item_id, stamped.co_id, stamped.activity_id,
                stamped.cost_change, stamped.duration_change, stamped.description,
                stamped.created_at, stamped.updated_at,
            ),
        )
    return stamped


def list_change_order_items(
    path: str | Path,
    co_id: str,
) -> list[ChangeOrderItem]:
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM change_order_items WHERE co_id = ? ORDER BY created_at",
            (co_id,),
        ).fetchall()
    return [_change_order_item_from_row(row) for row in rows]


# ---------------------------------------------------------------------------
# Delay events CRUD
# ---------------------------------------------------------------------------


def create_delay_event(path: str | Path, event: DelayEvent) -> DelayEvent:
    stamped = _stamp(event)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO delay_events(
                delay_event_id, activity_id, delay_type, cause_code,
                responsible_party, start_date, end_date, delay_days,
                cost_impact, description, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stamped.delay_event_id,
                stamped.activity_id,
                stamped.delay_type,
                stamped.cause_code,
                stamped.responsible_party,
                stamped.start_date.isoformat() if stamped.start_date else None,
                stamped.end_date.isoformat() if stamped.end_date else None,
                stamped.delay_days,
                stamped.cost_impact,
                stamped.description,
                stamped.status,
                stamped.created_at,
                stamped.updated_at,
            ),
        )
    return stamped


def list_delay_events(
    path: str | Path,
    *,
    activity_id: str | None = None,
    delay_type: str | None = None,
    status: str | None = None,
) -> list[DelayEvent]:
    rows = _select_with_optional_filters(
        path,
        "delay_events",
        {"activity_id": activity_id, "delay_type": delay_type, "status": status},
        "created_at DESC",
    )
    return [_delay_event_from_row(row) for row in rows]


def update_delay_event_status(
    path: str | Path,
    delay_event_id: str,
    *,
    status: str,
) -> DelayEvent:
    timestamp = _now()
    with _connect(path) as conn:
        conn.execute(
            "UPDATE delay_events SET status = ?, updated_at = ? WHERE delay_event_id = ?",
            (status, timestamp, delay_event_id),
        )
        row = conn.execute(
            "SELECT * FROM delay_events WHERE delay_event_id = ?",
            (delay_event_id,),
        ).fetchone()
    if not row:
        raise ValueError(f"Delay event not found: {delay_event_id}")
    return _delay_event_from_row(row)


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


def _date_param(value: str | date) -> str:
    return value.isoformat() if isinstance(value, date) else value


def _optional_date_param(value: str | date | None) -> str | None:
    if value is None:
        return None
    return _date_param(value)


def _select_with_optional_filters(
    path: str | Path,
    table_name: str,
    filters: dict[str, object | None],
    order_by: str,
) -> list[sqlite3.Row]:
    clauses: list[str] = []
    params: list[object] = []
    for column, value in filters.items():
        if value is None:
            continue
        clauses.append(f"{column} = ?")
        params.append(value)
    query = f"SELECT * FROM {table_name}"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += f" ORDER BY {order_by}"
    with _connect(path) as conn:
        return conn.execute(query, tuple(params)).fetchall()


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
        float(activity.progress_pct),
        activity.status,
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
        progress_pct=float(row["progress_pct"] if "progress_pct" in row.keys() else 0.0),
        status=row["status"] if "status" in row.keys() else "PENDING",
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


def _daily_record_from_row(row: sqlite3.Row) -> DailyRecord:
    return DailyRecord(
        record_id=row["record_id"],
        activity_id=row["activity_id"],
        work_date=date.fromisoformat(row["work_date"]),
        planned_qty=row["planned_qty"],
        actual_qty=row["actual_qty"],
        workers=row["workers"],
        equipment=row["equipment"],
        owner=row["owner"],
        remarks=row["remarks"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _cost_item_from_row(row: sqlite3.Row) -> CostItem:
    return CostItem(
        cost_item_id=row["cost_item_id"],
        activity_id=row["activity_id"],
        contract_amount=row["contract_amount"],
        execution_budget=row["execution_budget"],
        invested_cost=row["invested_cost"],
        billing_amount=row["billing_amount"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _material_values(record: MaterialRecord) -> tuple[object, ...]:
    return (
        record.material_id,
        record.activity_id,
        record.material_name,
        record.order_date.isoformat() if record.order_date else None,
        record.expected_date.isoformat() if record.expected_date else None,
        record.actual_date.isoformat() if record.actual_date else None,
        record.status,
        record.created_at,
        record.updated_at,
    )


def _material_from_row(row: sqlite3.Row) -> MaterialRecord:
    return MaterialRecord(
        material_id=row["material_id"],
        activity_id=row["activity_id"],
        material_name=row["material_name"],
        order_date=_parse_date(row["order_date"]),
        expected_date=_parse_date(row["expected_date"]),
        actual_date=_parse_date(row["actual_date"]),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _inspection_values(record: InspectionRecord) -> tuple[object, ...]:
    return (
        record.inspection_id,
        record.activity_id,
        record.inspection_type,
        record.planned_date.isoformat() if record.planned_date else None,
        record.actual_date.isoformat() if record.actual_date else None,
        record.status,
        record.approver,
        record.created_at,
        record.updated_at,
    )


def _inspection_from_row(row: sqlite3.Row) -> InspectionRecord:
    return InspectionRecord(
        inspection_id=row["inspection_id"],
        activity_id=row["activity_id"],
        inspection_type=row["inspection_type"],
        planned_date=_parse_date(row["planned_date"]),
        actual_date=_parse_date(row["actual_date"]),
        status=row["status"],
        approver=row["approver"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _change_log_from_row(row: sqlite3.Row) -> ChangeLogEntry:
    return ChangeLogEntry(
        change_id=row["change_id"],
        target_table=row["target_table"],
        target_id=row["target_id"],
        before_value=row["before_value"],
        after_value=row["after_value"],
        reason=row["reason"],
        user=row["user"],
        approved_by=row["approved_by"],
        changed_at=_parse_date(row["changed_at"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _project_settings_from_row(row: sqlite3.Row) -> ProjectSettings:
    return ProjectSettings(
        settings_id=row["settings_id"],
        project_id=row["project_id"],
        disciplines=tuple(json.loads(row["disciplines"])),
        thresholds=json.loads(row["thresholds"]),
        report_style=row["report_style"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _baseline_snapshot_from_row(row: sqlite3.Row) -> BaselineSnapshot:
    return BaselineSnapshot(
        snapshot_id=row["snapshot_id"],
        baseline_id=row["baseline_id"],
        activity_id=row["activity_id"],
        start_date=_parse_date(row["start_date"]),
        finish_date=_parse_date(row["finish_date"]),
        duration=row["duration"],
        revision=row["revision"],
        project_id=row["project_id"],
        approved_by=row["approved_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _change_order_from_row(row: sqlite3.Row) -> ChangeOrder:
    return ChangeOrder(
        co_id=row["co_id"],
        title=row["title"],
        description=row["description"],
        co_type=row["co_type"],
        status=row["status"],
        requested_by=row["requested_by"],
        approved_by=row["approved_by"],
        request_date=_parse_date(row["request_date"]),
        approval_date=_parse_date(row["approval_date"]),
        direct_cost=row["direct_cost"],
        markup_pct=row["markup_pct"],
        total_cost=row["total_cost"],
        schedule_impact_days=row["schedule_impact_days"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _change_order_item_from_row(row: sqlite3.Row) -> ChangeOrderItem:
    return ChangeOrderItem(
        co_item_id=row["co_item_id"],
        co_id=row["co_id"],
        activity_id=row["activity_id"],
        cost_change=row["cost_change"],
        duration_change=row["duration_change"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _delay_event_from_row(row: sqlite3.Row) -> DelayEvent:
    return DelayEvent(
        delay_event_id=row["delay_event_id"],
        activity_id=row["activity_id"],
        delay_type=row["delay_type"],
        cause_code=row["cause_code"],
        responsible_party=row["responsible_party"],
        start_date=_parse_date(row["start_date"]),
        end_date=_parse_date(row["end_date"]),
        delay_days=row["delay_days"],
        cost_impact=row["cost_impact"],
        description=row["description"],
        status=row["status"],
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


def create_notification_log(path: str | Path, log: NotificationLog) -> NotificationLog:
    timestamp = _now()
    with _connect(path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO notification_logs(
                activity_id, target_role, notification_type, message, is_sent, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                log.activity_id,
                log.target_role,
                log.notification_type,
                log.message,
                int(log.is_sent),
                timestamp if log.created_at is None else log.created_at,
            ),
        )
        log_id = cursor.lastrowid or 0
    return replace(log, log_id=log_id, created_at=timestamp if log.created_at is None else log.created_at)


def list_notification_logs(path: str | Path, *, limit: int = 100) -> list[NotificationLog]:
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM notification_logs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [_notification_log_from_row(row) for row in rows]


def _notification_log_from_row(row: sqlite3.Row) -> NotificationLog:
    return NotificationLog(
        log_id=row["log_id"],
        activity_id=row["activity_id"],
        target_role=row["target_role"],
        notification_type=row["notification_type"],
        message=row["message"],
        is_sent=bool(row["is_sent"]),
        created_at=row["created_at"],
    )


# ─── 카카오톡 챗봇 사용자 매핑 (v3.6) ────────────────────────────────────────

def upsert_kakao_user(
    path: str | Path,
    bot_user_key: str,
    owner_name: str,
    discipline: str,
) -> dict[str, str]:
    """카카오 botUserKey ↔ 담당자(이름·공종) 매핑을 저장/갱신한다."""
    now = _now()
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO kakao_users(bot_user_key, owner_name, discipline, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(bot_user_key) DO UPDATE SET
                owner_name = excluded.owner_name,
                discipline = excluded.discipline,
                updated_at = excluded.updated_at
            """,
            (bot_user_key, owner_name, discipline, now, now),
        )
    return {"bot_user_key": bot_user_key, "owner_name": owner_name, "discipline": discipline}


def get_kakao_user(path: str | Path, bot_user_key: str) -> dict[str, str] | None:
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM kakao_users WHERE bot_user_key = ?", (bot_user_key,)
        ).fetchone()
    if row is None:
        return None
    return {
        "bot_user_key": row["bot_user_key"],
        "owner_name": row["owner_name"],
        "discipline": row["discipline"],
    }


def list_kakao_users(path: str | Path) -> list[dict[str, str]]:
    with _connect(path) as conn:
        rows = conn.execute("SELECT * FROM kakao_users ORDER BY discipline").fetchall()
    return [
        {
            "bot_user_key": row["bot_user_key"],
            "owner_name": row["owner_name"],
            "discipline": row["discipline"],
        }
        for row in rows
    ]
