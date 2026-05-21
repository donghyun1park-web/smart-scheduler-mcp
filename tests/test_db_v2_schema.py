from __future__ import annotations

import sqlite3

from core import db


def test_initialize_database_sets_new_database_schema_version_to_2(tmp_path):
    db_path = tmp_path / "new_v2.scheduler"

    db.initialize_database(db_path)

    assert _schema_version(db_path) == 2


def test_initialize_database_migrates_existing_v1_schema_version_to_2(tmp_path):
    db_path = tmp_path / "existing_v1.scheduler"
    db.initialize_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_version SET version = 1")

    db.initialize_database(db_path)

    assert _schema_version(db_path) == 2


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
