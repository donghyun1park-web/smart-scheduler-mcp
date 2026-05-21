# Release Notes v0.2.0 MVP

## Summary

AI Construction Scheduler v2.0 MVP extends Smart Node-Scheduler v0.1 with
Excel-centered field workflows, progress/cost calculations, delay detection,
recovery-plan drafts, a site-manager dashboard summary, and MCP tool wrappers.

## Added

- v2 SQLite tables: `daily_records`, `cost_items`, `baseline_snapshots`,
  `materials`, `inspections`, `change_log`, and `project_settings`.
- Progress calculations in `core.progress`.
- Cost calculations and overrun detection in `core.cost`.
- Delay detection in `core.delay_detection`.
- Recovery-plan draft candidates in `core.recovery`.
- Backup and restore helpers in `core.backup`.
- Field-specific validation helpers in `core.validation`.
- Excel field input template writer in `core.excel_io`.
- Weekly construction report writer in `core.reporting`.
- Sample site data at `samples/ai_construction_site_sample.json`.
- Site-manager dashboard summary and Streamlit page.
- MCP tools: `input_daily_record`, `detect_delays`, `suggest_recovery`,
  `generate_weekly_report`, and `summarize_site_status`.

## Preserved

- Existing CPM behavior and tests.
- Existing SQLite project storage behavior.
- Existing v0.1 MCP tools.
- Existing Streamlit viewer pages.
- Existing v0.1 Excel report writer.

## Verification

Latest verification was run with the project `.venv` on Python 3.12.10:

- `.\.venv\Scripts\python.exe -m pytest -q`
- `.\.venv\Scripts\python.exe -m ruff check .`
- `.\.venv\Scripts\python.exe -m mypy .`

See `CHECKPOINT_LOG.md` for exact results by phase.

## Known Limitations

- v2 field records are not yet persisted by MCP tool wrappers.
- Dashboard and weekly report use normalized JSON sample data as the MVP
  integration shape.
- Report style separation exists as an entry point but needs richer templates.
- Full EVM, BIM, weather API, photo workflow, cloud collaboration, and full user
  authentication are deferred.
