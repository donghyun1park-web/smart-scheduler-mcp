# Release Notes v0.2.0 MVP

## Summary

AI Construction Scheduler v2.0 MVP extends Smart Node-Scheduler v0.1 with
Excel-centered field workflows, progress/cost calculations, delay detection,
recovery-plan drafts, a site-manager dashboard summary, and MCP tool wrappers.

## Added

- v2 SQLite tables: `daily_records`, `cost_items`, `baseline_snapshots`,
  `materials`, `inspections`, `change_log`, and `project_settings`.
- Schema version 2 migration for new and existing v1 databases.
- Korean construction-discipline normalization with English alias support.
- v2 SQLite CRUD helpers for field records, costs, materials, inspections,
  change log, project settings, and baselines.
- openpyxl-based Excel input readers and Excel-to-DB import flow.
- DB-backed weekly report generation.
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
- Dashboard still uses normalized JSON for the direct Streamlit UI surface.
- Report style separation exists as an entry point but needs richer templates.
- Full EVM, BIM, weather API, photo workflow, cloud collaboration, and full user
  authentication are deferred.

See `docs/RELEASE_NOTES_v0.2.1.md` for the follow-up pass that adds DB-backed
dashboard loading, audience-specific report prose, shared number utilities, and
expanded recovery templates.

See `docs/RELEASE_NOTES_v0.2.2.md` for field-deployment stabilization:
conflict-safe import, dry-run validation, import pre-backup, change-log MCP,
real DB smoke testing, protected Excel templates, and simple EVM.
