# Release Notes v0.2.2

## Summary

v0.2.2 is the field-deployment stabilization pass. It keeps v2.1 behavior
intact and hardens real `.scheduler` and Excel field-input workflows.

## Added

- Import conflict policies for field input:
  - `fail`: stop without DB changes when duplicate daily records exist.
  - `skip`: keep existing daily records and count skipped rows.
  - `replace`: replace duplicate daily records and write row-level change log.
  - `merge`: explicit unsupported response.
- Import dry-run mode with validation and no DB changes.
- Batch validation before import commit for missing/unknown activity IDs,
  negative quantities, progress errors, and cost/progress gap warnings.
- Automatic backup before non-dry-run import.
- `list_change_log_tool` MCP tool and server registration.
- Real DB smoke-test script:
  `scripts/smoke_test_real_scheduler.py`.
- Field Excel template freeze panes, filters, protected sheets, unlocked input
  cells, and data validations.
- Simple EVM snapshot/totals in `core.evm`, dashboard summaries, HQ report
  wording, and Excel cost status columns.
- Streamlit dashboard report generation/download helper.

## Verification

Use the project `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
```

## Compatibility

- `SCHEMA_VERSION` remains `2`; no v3 migration is required for v0.2.2.
- v1-to-v2 schema version upgrade remains automatic.
- Existing v0.1 CPM, SQLite, Streamlit, MCP, and Excel report behavior is
  preserved.
- Real DB smoke tests must run on copied DB files only.
