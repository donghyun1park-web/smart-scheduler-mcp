from __future__ import annotations

import sqlite3

from core import db


def test_initialize_database_sets_new_database_schema_version_to_current(tmp_path):
    db_path = tmp_path / "new_v3.scheduler"

    db.initialize_database(db_path)

    assert _schema_version(db_path) == db.SCHEMA_VERSION


def test_initialize_database_migrates_existing_older_schema_version_to_current(tmp_path):
    db_path = tmp_path / "existing_old.scheduler"
    db.initialize_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_version SET version = 1")

    db.initialize_database(db_path)

    assert _schema_version(db_path) == db.SCHEMA_VERSION


def test_initialize_database_migration_adds_progress_pct_column(tmp_path):
    db_path = tmp_path / "pre_v3.scheduler"
    db.initialize_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_version SET version = 2")
        conn.execute("ALTER TABLE activities DROP COLUMN progress_pct")

    db.initialize_database(db_path)

    columns = db.list_table_columns(db_path, "activities")
    assert "progress_pct" in columns
    assert _schema_version(db_path) == db.SCHEMA_VERSION


def test_initialize_database_creates_v2_field_tables(tmp_path):
    db_path = tmp_path / "v2.scheduler"
    db.initialize_database(db_path)

    tables = db.list_tables(db_path)

    assert {
        "daily_records",
        "cost_items",
        "baseline_snapshots",
        "materials",
        "inspections",
        "change_log",
        "project_settings",
    }.issubset(tables)


def test_activity_table_stays_focused_after_v2_schema(tmp_path):
    db_path = tmp_path / "v2.scheduler"
    db.initialize_database(db_path)

    columns = db.list_table_columns(db_path, "activities")

    assert "planned_qty" not in columns
    assert "actual_qty" not in columns
    assert "invested_cost" not in columns
    assert "material_status" not in columns
    assert len(columns) < 30


def _schema_version(db_path) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(conn.execute("SELECT version FROM schema_version").fetchone()[0])
