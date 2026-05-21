# PR Description - AI Construction Scheduler v2.x

## Summary

This branch upgrades `smart-scheduler-mcp` from the original Smart
Node-Scheduler v0.1 workflow into the AI Construction Scheduler v2 field MVP,
then stabilizes it through v2.2.

The v2.2 scope focuses on field-safety:

- Excel import conflict policies: `fail`, `skip`, `replace`, and explicit
  unsupported `merge`.
- Batch validation before import commit.
- Automatic backup before non-dry-run import.
- Change-log MCP access.
- Real `.scheduler` smoke-test script that works only on a copied DB.
- Excel template protection, filters, freeze panes, and data validation.
- Simple EVM summary for dashboard and headquarters reporting.

## Quality Gates

Run with the project virtual environment Python `>=3.11,<3.13`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
```

Python 3.14 and Python 2.7 results are not acceptance evidence for this repo.

## Breaking / Compatibility Notes

- Existing CPM, SQLite project storage, Streamlit viewer, MCP tools, and v0.1
  Excel report generation are preserved.
- `Activity` remains focused on schedule identity and CPM fields; field daily
  records, costs, materials, inspections, baselines, settings, and change logs
  are kept in separate tables.
- v2.2 import defaults to `conflict_policy="fail"` to prevent silent overwrite.
- `dry_run=True` validates and reports conflicts without changing the DB.
- Original real `.scheduler` files must not be smoke-tested directly; the
  smoke script copies the DB first.

## Schema Version

- Current `SCHEMA_VERSION`: `2`
- New v2.2 database schema migration: none required
- `initialize_database()` creates v2 tables for new databases and upgrades a v1
  `schema_version` row to version 2 automatically.

## v0.1 to v2 Feature Summary

| Area | v0.1 | v2.x |
|---|---|---|
| Schedule engine | CPM and critical path | Preserved |
| Storage | SQLite `.scheduler` | Preserved plus v2 field tables |
| Excel | Five-sheet CPM report | Field input, DB import, weekly construction report |
| Dashboard | Streamlit project review | DB-backed site-manager dashboard |
| MCP | Project/import/CPM/report tools | Construction field tools and change-log query |
| Recovery | Out of scope | Draft/candidate recovery templates only |
| Validation | Input helpers | Batch field import validation |
| Safety | Manual backups | Import pre-backup and smoke-test DB copy |

## Merge Recommendation

Use a merge commit for this branch so the v2 implementation checkpoints remain
visible. Avoid squash merge because the branch contains multiple validated
stabilization layers and checkpoint commits.
