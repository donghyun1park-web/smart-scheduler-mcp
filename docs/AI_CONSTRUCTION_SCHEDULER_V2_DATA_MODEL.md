# AI Construction Scheduler v2.0 MVP Data Model

## Principle

`activities` remains focused on schedule identity and CPM outputs. Field daily
progress, cost, baseline, material, inspection, change history, and settings
data live in separate tables.

`SCHEMA_VERSION` is `2`. `initialize_database()` creates v2 tables for new
databases and upgrades a v1 `schema_version` row to version 2 when an existing
database is opened.

## Tables

### `activities`

Existing v0.1 table. It keeps core fields such as activity id, code, name, WBS,
discipline, zone, duration, cost, CPM dates, float, and critical-path flag.

### `daily_records`

Daily field progress.

- `record_id`
- `activity_id`
- `work_date`
- `planned_qty`
- `actual_qty`
- `workers`
- `equipment`
- `owner`
- `remarks`
- `created_at`
- `updated_at`

### `cost_items`

Cost and billing status.

- `cost_item_id`
- `activity_id`
- `contract_amount`
- `execution_budget`
- `invested_cost`
- `billing_amount`
- `created_at`
- `updated_at`

### `baseline_snapshots`

Baseline schedule revisions.

- `snapshot_id`
- `baseline_id`
- `activity_id`
- `start_date`
- `finish_date`
- `duration`
- `revision`
- `approved_by`
- `created_at`
- `updated_at`

### `materials`

Material delivery status.

- `material_id`
- `activity_id`
- `material_name`
- `order_date`
- `expected_date`
- `actual_date`
- `status`
- `created_at`
- `updated_at`

### `inspections`

Inspection, approval, and test status.

- `inspection_id`
- `activity_id`
- `inspection_type`
- `planned_date`
- `actual_date`
- `status`
- `approver`
- `created_at`
- `updated_at`

### `change_log`

Change history.

- `change_id`
- `target_table`
- `target_id`
- `before_value`
- `after_value`
- `reason`
- `user`
- `approved_by`
- `changed_at`
- `created_at`
- `updated_at`

### `project_settings`

Project-specific settings such as disciplines, dashboard thresholds, and report
style.

- `settings_id`
- `project_id`
- `disciplines`
- `thresholds`
- `report_style`
- `created_at`
- `updated_at`

## MVP Notes

- v2 CRUD helpers exist for daily records, cost items, materials, inspections,
  change log, project settings, and baseline snapshots.
- Excel input can be read and imported into the v2 tables.
- DB-backed weekly report generation builds normalized report data from these
  tables.
- Activity table bloat is explicitly guarded by tests.
