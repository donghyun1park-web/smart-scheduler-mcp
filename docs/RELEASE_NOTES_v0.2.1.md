# Release Notes v0.2.1

## Summary

v0.2.1 is a follow-up stabilization pass for the AI Construction Scheduler v2
MVP. It preserves the v2 SQLite schema and Excel-to-DB-to-report loop while
closing the DB dashboard, report style, number conversion, and recovery-template
gaps.

## Added

- DB-backed site-manager dashboard loader:
  `viewer.components.site_manager_dashboard.load_site_dashboard_data_from_db`.
- Streamlit dashboard source selection for SQLite DB or existing JSON/sample
  data.
- `core.report_styles` with `internal`, `hq`, and `client` audience wording.
- `core.number_utils` for safe float conversion, division, and percentage
  calculation.
- Recovery templates for equipment delay, inspection/approval delay, design
  change, subcontractor delay, and weather delay.
- Tests for DB-backed dashboard loading, report style variants, number utility
  behavior, and extended recovery templates.

## Preserved

- `SCHEMA_VERSION = 2`.
- Korean construction-discipline normalization.
- v2 CRUD for daily records, costs, baselines, materials, inspections, change
  log, and project settings.
- openpyxl Excel readers and Excel import flow.
- DB-backed weekly report generation and existing MCP wrappers.
- Existing v0.1 CPM, SQLite, Streamlit, MCP, and Excel report behavior.

## Verification

Latest v0.2.1 verification was run with the project `.venv` on Python 3.12:

- `.\.venv\Scripts\python.exe -m pytest -q`: `138 passed`
- `.\.venv\Scripts\python.exe -m ruff check .`: `All checks passed!`
- `.\.venv\Scripts\python.exe -m mypy .`: `Success: no issues found in 107 source files`

## Known Limitations

- DB dashboard project selection is file-scoped because the current v2 activity
  table does not store `project_id` directly.
- Excel chart and print formatting remain MVP-simple.
- Full EVM, BIM, weather API integration, photos, cloud collaboration, and full
  authentication remain deferred scope.
