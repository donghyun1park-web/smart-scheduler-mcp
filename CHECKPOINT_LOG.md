# CHECKPOINT_LOG

## Phase 0 - Baseline And Work Rules

Date: 2026-05-21

### Changed Files

- `AGENTS.md`
- `PLAN.md`
- `CHECKPOINT_LOG.md`
- `core/calendar_utils.py`

### Implemented

- Read the UTF-8 development plan from
  `C:\Users\User\Downloads\AI건축공정표_프로그램_개발계획서.md`.
- Created branch `feature/ai-construction-scheduler-v2`.
- Documented AI Construction Schedule v2.0 MVP rules while preserving the
  Python 3.11/3.12 acceptance gate.
- Added a phase-by-phase implementation plan that keeps CPM, SQLite, MCP,
  Streamlit, Plotly, and existing Excel reporting intact.
- Fixed a baseline `mypy` failure in the Korean holiday cache by typing cached
  holidays as `set[date]`.

### Commands Run

```powershell
git status --short --branch
git branch --show-current
git switch -c feature/ai-construction-scheduler-v2
Get-Content -Raw -Encoding UTF8 C:\Users\User\Downloads\AI건축공정표_프로그램_개발계획서.md
.\.venv\Scripts\python.exe --version
py -0p
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
```

### Test And Environment Result

- Initial sandboxed `.\.venv\Scripts\python.exe --version`: failed because the
  sandbox could not access the AppData-hosted base interpreter.
- Escalated `.\.venv\Scripts\python.exe --version`: `Python 3.12.10`.
- Escalated `py -0p`: Python 3.12 and 3.11 are available alongside 3.14 and
  2.7.
- `.\.venv\Scripts\python.exe -m pip check`: `No broken requirements found.`
- `.\.venv\Scripts\python.exe -m pytest -q`: `78 passed`.
- `.\.venv\Scripts\python.exe -m ruff check .`: `All checks passed!`
- `.\.venv\Scripts\python.exe -m mypy .`: `Success: no issues found in 75 source files`.

### Failures And Fixes

- Initial sandboxed venv check reported
  `No Python at '"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe'`.
  Escalated verification showed the interpreter is available and `.venv` is
  valid.
- First `mypy` run failed at `core/calendar_utils.py:98` with
  `Unsupported right operand type for in ("object")`.
- Fixed by changing the Korean holiday cache from `dict[int, object]` to
  `dict[int, set[date]]` and storing a concrete `set(...)` of holiday dates.

### Remaining Risks

- The current repository contains Korean display mojibake in some older strings;
  avoid broad encoding rewrites unless a focused test requires it.
- Any future recovery-suggestion text must be checked for final-decision wording
  before release.
- Phase 1 should begin with failing tests for the new schema and calculation
  modules before production code is added.

## Phase 1 - Data Model And Core Engines

Date: 2026-05-21

### Changed Files

- `core/models.py`
- `core/db.py`
- `core/progress.py`
- `core/cost.py`
- `core/delay_detection.py`
- `core/recovery.py`
- `core/backup.py`
- `core/validation.py`
- `tests/test_db_v2_schema.py`
- `tests/test_progress.py`
- `tests/test_cost.py`
- `tests/test_delay_detection.py`
- `tests/test_recovery.py`
- `tests/test_backup.py`
- `tests/test_validation_v2.py`
- `PLAN.md`
- `CHECKPOINT_LOG.md`

### Implemented

- Added separate v2 schema tables for `daily_records`, `cost_items`,
  `baseline_snapshots`, `materials`, `inspections`, `change_log`, and
  `project_settings`.
- Kept the `activities` table focused and verified it has fewer than 30 columns
  with no daily-progress, cost-execution, or material-status fields added.
- Added focused dataclasses for daily records, cost items, baselines, material
  records, inspections, change log entries, and project settings.
- Implemented quantity, weighted, milestone, discipline, and zone progress
  calculations.
- Implemented cost execution rate, billing rate, cost-overrun detection, and
  forecast completion cost calculation.
- Implemented schedule-delay, overdue, predecessor-block, material-delay,
  inspection-delay, and manpower-shortage detection.
- Implemented recovery-plan candidates with draft/review-required wording only.
- Implemented backup creation, backup rotation, and restore helpers.
- Extended validation with specific messages for date reversal, quantity/progress
  issues, cost-progress gaps, missing owners, and missing change approvals.

### Commands Run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_db_v2_schema.py tests\test_progress.py tests\test_cost.py tests\test_delay_detection.py tests\test_recovery.py tests\test_backup.py tests\test_validation_v2.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
```

### Test Result

- New Phase 1 test bundle before implementation: failed as expected with missing
  `core.progress`, `core.cost`, `core.delay_detection`, `core.recovery`,
  `core.backup`, and validation extension imports.
- New Phase 1 test bundle after implementation: `20 passed`.
- Full test suite: `98 passed`.
- `ruff check .`: `All checks passed!`
- `mypy .`: `Success: no issues found in 87 source files`.

### Failures And Fixes

- Failure: new tests initially failed during collection because Phase 1 modules
  and validation functions did not exist.
- Fix: added the requested modules and focused functions, then reran the Phase 1
  bundle and full checks.

### Remaining Risks

- The new DB tables currently have schema and index coverage but not full CRUD
  helper coverage.
- Delay detection operates on normalized dictionaries; later Excel/MCP work must
  map workbook and database rows into that shape consistently.
- Recovery candidates are intentionally simple MVP drafts and should be expanded
  only after field review.

## Phase 2 - Excel Input And Weekly Reports

Date: 2026-05-21

### Changed Files

- `core/excel_io.py`
- `core/reporting.py`
- `samples/ai_construction_site_sample.json`
- `tests/test_excel_io.py`
- `tests/test_weekly_report_v2.py`
- `PLAN.md`
- `CHECKPOINT_LOG.md`

### Implemented

- Added an xlsxwriter-based field input template with sheets for daily progress,
  cost input, material/inspection input, schedule, dashboard, delays, and report.
- Added sample site data covering normal work, schedule delay, predecessor
  blocking, cost overrun, material delay, inspection delay, missing owner, and
  baseline change.
- Added a v2 weekly construction report writer with dashboard, current-week
  actuals, delayed TOP 10, recovery drafts, cost status, next-week plan, Gantt
  data, and narrative report sheets.
- Kept v0.1 `create_excel_report(...)` intact and added
  `create_weekly_construction_report(...)` as a separate v2 entry point.

### Commands Run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_excel_io.py tests\test_weekly_report_v2.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
```

### Test Result

- New Phase 2 test bundle before implementation: failed as expected with missing
  `core.excel_io` and `create_weekly_construction_report`.
- New Phase 2 test bundle after implementation: `4 passed`.
- Full test suite after Phase 2 before type fix: `102 passed`, `ruff` passed,
  `mypy` found two `core/reporting.py` type narrowing issues.
- Type fix verification: `tests/test_weekly_report_v2.py` `2 passed`, `mypy`
  `Success: no issues found in 90 source files`.

### Failures And Fixes

- Failure: dashboard row order did not match the site-manager-focused test.
  Fix: moved overall actual progress ahead of planned progress in the v2
  dashboard sheet.
- Failure: `mypy` rejected `max(..., key=scores.get)` and generic `float(object)`.
  Fix: used a lambda key and narrowed numeric conversion inputs.

### Remaining Risks

- Excel reading/import of edited field templates is not implemented yet.
- The generated workbook is intentionally simple; charts and print layouts need
  a later visual/reporting pass.
- Report-style differences are recorded but not yet deeply templated by audience.

## Phase 3 - Site Manager Dashboard

Date: 2026-05-21

### Changed Files

- `viewer/components/site_manager_dashboard.py`
- `viewer/pages/08_site_manager_dashboard.py`
- `tests/test_site_manager_dashboard.py`
- `PLAN.md`
- `CHECKPOINT_LOG.md`

### Implemented

- Added a site-manager dashboard summary builder that returns planned progress,
  actual progress, variance, cost execution rate, billing rate, delayed activity
  count, risk discipline, key risks, status, and thresholds.
- Added configurable green/yellow/orange/red progress-variance thresholds.
- Added a thin Streamlit page that loads the sample site JSON or an uploaded
  JSON file and renders the dashboard summary.

### Commands Run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_site_manager_dashboard.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
```

### Test Result

- New Phase 3 test before implementation: failed as expected with missing
  `viewer.components.site_manager_dashboard`.
- New Phase 3 test after implementation: `2 passed`.
- Full test suite: `104 passed`.
- `ruff check .`: `All checks passed!`
- `mypy .`: `Success: no issues found in 93 source files`.

### Failures And Fixes

- Failure: dashboard component did not exist.
- Fix: added the summary builder and Streamlit page.

### Remaining Risks

- Streamlit rendering is intentionally minimal and should receive a usability
  pass after field users confirm the metrics.
- Dashboard currently reads normalized JSON data; direct SQLite-backed dashboard
  loading remains a follow-up.

## Phase 4 - MCP Tool Expansion

Date: 2026-05-21

### Changed Files

- `tools/construction_tools.py`
- `server.py`
- `tests/test_construction_tools.py`
- `tests/test_server.py`
- `PLAN.md`
- `CHECKPOINT_LOG.md`

### Implemented

- Added `input_daily_record`, `detect_delays`, `suggest_recovery`,
  `generate_weekly_report`, and `summarize_site_status` tool wrappers.
- Registered the new v2 construction tools in the MCP server.
- Ensured `suggest_recovery` returns candidate/draft/review-required language
  and tests reject final-decision wording.

### Commands Run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_construction_tools.py tests\test_server.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
```

### Test Result

- New Phase 4 test before implementation: failed as expected with missing
  `tools.construction_tools`.
- New Phase 4 test after implementation: `8 passed`.
- Full test suite after Phase 4 before type fix: `109 passed`, `ruff` passed,
  `mypy` found four input-normalization type issues.
- Type fix verification: `tests/test_construction_tools.py` `4 passed`, `mypy`
  `Success: no issues found in 95 source files`.

### Failures And Fixes

- Failure: `tools.construction_tools` did not exist.
- Fix: added thin wrappers and MCP registration.
- Failure: `mypy` treated normalized daily-record dictionary values as `object`.
- Fix: introduced typed local variables before building the JSON-serializable
  record dictionary.

### Remaining Risks

- `input_daily_record` validates and normalizes one record but does not yet
  persist it into SQLite.
- MCP tools currently accept normalized site JSON; direct project-file backed
  versions can be added after field workflow shape is confirmed.

## Phase 5 - Stabilization, Samples, And Docs

Date: 2026-05-21

### Changed Files

- `README.md`
- `docs/AI_CONSTRUCTION_SCHEDULER_V2_USER_GUIDE.md`
- `docs/AI_CONSTRUCTION_SCHEDULER_V2_DATA_MODEL.md`
- `docs/RELEASE_NOTES_v0.2.0-MVP.md`
- `samples/field_input_template.xlsx`
- `samples/ai_construction_weekly_report.xlsx`
- `PLAN.md`
- `CHECKPOINT_LOG.md`

### Implemented

- Documented v2.0 MVP setup, Excel workflow, dashboard workflow, MCP tools,
  sample-data reproduction, data model, release notes, and known limitations.
- Generated sample Excel artifacts from `samples/ai_construction_site_sample.json`.
- Confirmed the generated weekly report detects 5 delayed activities and 1 cost
  overrun from the sample scenario.

### Commands Run

```powershell
.\.venv\Scripts\python.exe -c "import json; from core.excel_io import create_field_input_template; from core.reporting import create_weekly_construction_report; data=json.load(open('samples\\ai_construction_site_sample.json', encoding='utf-8')); print(create_field_input_template('samples\\field_input_template.xlsx', project_name=data['project']['name'], activities=data['activities'])); print(create_weekly_construction_report(data, 'samples\\ai_construction_weekly_report.xlsx'))"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
git grep -nP "[\x{202A}-\x{202E}\x{2066}-\x{2069}]"
```

### Test Result

- Sample field template generation: succeeded.
- Sample weekly report generation: succeeded with `delayed_count=5` and
  `cost_overrun_count=1`.
- Full test suite: `109 passed`.
- `ruff check .`: `All checks passed!`
- `mypy .`: `Success: no issues found in 95 source files`.
- bidi Unicode control-character grep: no matches.

### Failures And Fixes

- No Phase 5 verification failures.

### Remaining Risks

- Generated Excel files are sample artifacts, not final visual report templates.
- SQLite persistence for v2 daily/cost/material/inspection records still needs
  CRUD and migration coverage.
- Audience-specific report prose is basic and should be expanded after field
  review.

## Stabilization Pass - Excel Input To DB Loop

Date: 2026-05-21

### Changed Files

- `core/db.py`
- `core/models.py`
- `core/disciplines.py`
- `core/excel_io.py`
- `core/importer.py`
- `tools/construction_tools.py`
- `server.py`
- `samples/ai_construction_site_sample.json`
- `samples/field_input_template.xlsx`
- `samples/ai_construction_weekly_report.xlsx`
- `tests/test_db_v2_schema.py`
- `tests/test_disciplines.py`
- `tests/test_db_v2_crud.py`
- `tests/test_excel_io.py`
- `tests/test_excel_import_flow.py`
- `tests/test_construction_tools.py`
- `tests/test_server.py`
- `README.md`
- `AGENTS.md`
- `PLAN.md`
- `docs/AI_CONSTRUCTION_SCHEDULER_V2_USER_GUIDE.md`
- `docs/AI_CONSTRUCTION_SCHEDULER_V2_DATA_MODEL.md`
- `docs/RELEASE_NOTES_v0.2.0-MVP.md`

### Implemented

- Created safety checkpoint commit `b37edfb` before stabilization work.
- Added checkpoint files under `.codex_checkpoints/`.
- Changed `SCHEMA_VERSION` to 2 and added v1-to-v2 schema version upgrade
  behavior.
- Added `core.disciplines` with MEP and Korean construction-discipline support
  plus English alias normalization.
- Added v2 SQLite CRUD for daily records, cost items, materials, inspections,
  change log, project settings, and baseline snapshots.
- Added openpyxl Excel readers for field input sheets.
- Added `core.importer.import_field_input_to_db()` and
  `generate_weekly_report_from_db()`.
- Added MCP wrappers `import_excel_input_to_db` and
  `generate_weekly_report_from_db`.
- Converted sample site disciplines to Korean standard values and regenerated
  sample Excel artifacts.

### Commands Run

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -c "import json; from core.excel_io import create_field_input_template; from core.reporting import create_weekly_construction_report; data=json.load(open('samples\\ai_construction_site_sample.json', encoding='utf-8')); print(create_field_input_template('samples\\field_input_template.xlsx', project_name=data['project']['name'], activities=data['activities'])); print(create_weekly_construction_report(data, 'samples\\ai_construction_weekly_report.xlsx'))"
```

### Test Result

- Current focused tests:
  - `tests/test_db_v2_schema.py tests/test_disciplines.py tests/test_db_v2_crud.py`: `12 passed`
  - `tests/test_excel_io.py`: `5 passed`
  - `tests/test_excel_import_flow.py tests/test_construction_tools.py tests/test_server.py`: `10 passed`
- Full suite before final doc update: `124 passed`.
- `ruff check .`: fixed one unused import and then passed.
- `mypy .`: fixed openpyxl worksheet typing and compatibility export, then
  passed.

### Failures And Fixes

- Failure: schema version tests initially failed because `SCHEMA_VERSION` was 1.
  Fix: set version to 2 and update existing lower versions.
- Failure: discipline tests failed because `core.disciplines` did not exist.
  Fix: added discipline normalization and preserved `core.models.ALLOWED_DISCIPLINES`.
- Failure: v2 CRUD tests failed because DB functions did not exist.
  Fix: added CRUD, summaries, filters, and row converters.
- Failure: Excel reader tests failed because read functions did not exist.
  Fix: added openpyxl read helpers with sheet/header validation.
- Failure: import flow tests failed because `core.importer` and DB-backed MCP
  functions did not exist.
  Fix: added importer and registered tools.

### Remaining Risks

- DB-backed Streamlit dashboard loading is still a UI follow-up.
- Report style templates are still simple.
- Excel import conflict handling is intentionally MVP-simple.

## v2.1 Follow-Up Stabilization

Date: 2026-05-21

### Changed Files

- `core/number_utils.py`
- `core/report_styles.py`
- `core/progress.py`
- `core/cost.py`
- `core/delay_detection.py`
- `core/field_uat.py`
- `core/reporting.py`
- `core/recovery.py`
- `viewer/components/site_manager_dashboard.py`
- `viewer/pages/08_site_manager_dashboard.py`
- `tools/construction_tools.py`
- `tests/test_number_utils.py`
- `tests/test_report_styles.py`
- `tests/test_weekly_report_styles.py`
- `tests/test_site_manager_dashboard_db.py`
- `tests/test_recovery_templates_extended.py`
- `README.md`
- `PLAN.md`
- `docs/AI_CONSTRUCTION_SCHEDULER_V2_USER_GUIDE.md`
- `docs/AI_CONSTRUCTION_SCHEDULER_V2_DATA_MODEL.md`
- `docs/RELEASE_NOTES_v0.2.0-MVP.md`
- `docs/RELEASE_NOTES_v0.2.1.md`
- `samples/field_input_template.xlsx`
- `samples/ai_construction_weekly_report.xlsx`

### Implemented

- Confirmed pre-work baseline on branch `feature/ai-construction-scheduler-v2`:
  `pytest -q` had `124 passed`; `ruff check .` and `mypy .` passed.
- Added DB-backed site-manager dashboard loading from `.scheduler` SQLite files
  with project, as-of date, summary KPI, discipline, zone, delayed TOP 10,
  cost-risk, material, inspection, and activity sections.
- Kept the existing JSON/sample dashboard path and added Streamlit source
  selection plus discipline, zone, and risk filters for DB-backed use.
- Added `report_style` variants for `internal`, `hq`, and `client`, and applied
  them to weekly workbook dashboard opinion, delay descriptions, recovery text,
  and report narrative.
- Added `core.number_utils` and removed duplicated `_float_value` style helpers
  from progress, cost, delay detection, reporting, dashboard, tools, and field
  UAT code.
- Expanded recovery templates with equipment, inspection/approval, design
  change, subcontractor, and weather delay reasons while preserving draft,
  review-required, and human-approval wording.
- Regenerated sample field input and weekly construction report workbooks.

### Commands Run

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -m pytest tests\test_number_utils.py tests\test_report_styles.py tests\test_weekly_report_styles.py tests\test_site_manager_dashboard_db.py tests\test_recovery_templates_extended.py -q
.\.venv\Scripts\python.exe -c "import json; from core.excel_io import create_field_input_template; from core.reporting import create_weekly_construction_report; data=json.load(open('samples\\ai_construction_site_sample.json', encoding='utf-8')); print(create_field_input_template('samples\\field_input_template.xlsx', project_name=data['project']['name'], activities=data['activities'])); print(create_weekly_construction_report(data, 'samples\\ai_construction_weekly_report.xlsx', report_style='internal'))"
```

### Test Result

- Pre-work full suite: `124 passed`.
- New v2.1 test bundle before implementation: failed as expected with missing
  `core.number_utils`, `core.report_styles`, and DB dashboard loader imports.
- New v2.1 test bundle after implementation: `14 passed`.
- Final full suite: `138 passed`.
- `ruff check .`: `All checks passed!`
- `mypy .`: `Success: no issues found in 107 source files`.
- Sample weekly report generation: succeeded with `delayed_count=5` and
  `cost_overrun_count=1`.

### Failures And Fixes

- Failure: extended recovery-template test caught forbidden final-decision text
  because "설계 미확정" contained "확정".
- Fix: rewrote the phrase to "설계 변경 검토 구간" and reran the focused test
  bundle.
- Failure: first `mypy` run found an object-to-`Project | None` assignment in
  DB dashboard loading.
- Fix: explicitly narrowed the loaded project object with `isinstance(...,
  Project)`.

### Remaining Risks

- DB dashboard project selection remains project-file scoped because the current
  v2 `activities` table does not store `project_id` directly.
- Excel chart/print formatting remains MVP-simple.
- Full EVM, BIM, weather API integration, photos, cloud collaboration, and full
  authentication remain deferred scope.

## v2.2 Field Stabilization

Date: 2026-05-21

### Changed Files

- `core/db.py`
- `core/importer.py`
- `core/excel_io.py`
- `core/evm.py`
- `core/reporting.py`
- `core/report_styles.py`
- `scripts/__init__.py`
- `scripts/smoke_test_real_scheduler.py`
- `server.py`
- `tools/construction_tools.py`
- `viewer/components/site_manager_dashboard.py`
- `viewer/pages/08_site_manager_dashboard.py`
- `tests/test_importer_v2_2.py`
- `tests/test_smoke_script_contract.py`
- `tests/test_excel_io.py`
- `tests/test_evm.py`
- `tests/test_dashboard_report_helper.py`
- `tests/test_construction_tools.py`
- `tests/test_server.py`
- `tests/test_site_manager_dashboard_db.py`
- `tests/test_weekly_report_styles.py`
- `README.md`
- `PLAN.md`
- `docs/AI_CONSTRUCTION_SCHEDULER_V2_USER_GUIDE.md`
- `docs/PR_DESCRIPTION_v2.md`
- `docs/RELEASE_NOTES_v0.2.0-MVP.md`
- `docs/RELEASE_NOTES_v0.2.2.md`
- `docs/SMOKE_TEST_REAL_SCHEDULER.md`
- `samples/field_input_template.xlsx`
- `samples/ai_construction_weekly_report.xlsx`

### Implemented

- Confirmed v2.2 baseline on branch `feature/ai-construction-scheduler-v2`:
  `pytest -q` had `138 passed`; `ruff check .` and `mypy .` passed.
- Added import `conflict_policy`, `dry_run`, `validate_before_commit`,
  `backup_before_import`, and `actor` options.
- Added conflict-safe daily-record import handling for `fail`, `skip`, and
  `replace`; `merge` returns a clear unsupported message.
- Added batch validation before import commit for missing/unknown activity IDs,
  negative quantities, progress issues, and cost/progress warnings.
- Added import pre-backup using `core.backup.create_backup()` and exposed
  `backup_path` in the import result.
- Added row-level change-log entries for replace imports and a
  `list_change_log_tool` MCP wrapper.
- Added a real DB smoke-test script that copies source `.scheduler` DB files
  before dashboard, dry-run import, report generation, and recovery checks.
- Improved Excel field templates with freeze panes, autofilter, protected
  sheets, unlocked input cells, data validations, print layout, and regenerated
  sample workbooks.
- Added simple EVM snapshots/totals and surfaced them in dashboard summaries,
  HQ report wording, and Excel cost-status columns.
- Added dashboard report generation/download helper and Streamlit button.
- Added PR description and v0.2.2 release notes.

### Commands Run

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -m pytest tests\test_importer_v2_2.py tests\test_excel_import_flow.py tests\test_db_v2_crud.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_construction_tools.py tests\test_server.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_smoke_script_contract.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_excel_io.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_evm.py tests\test_dashboard_report_helper.py tests\test_site_manager_dashboard_db.py tests\test_weekly_report_styles.py -q
.\.venv\Scripts\python.exe -c "import json; from core.excel_io import create_field_input_template; from core.reporting import create_weekly_construction_report; data=json.load(open('samples\\ai_construction_site_sample.json', encoding='utf-8')); print(create_field_input_template('samples\\field_input_template.xlsx', project_name=data['project']['name'], activities=data['activities'])); print(create_weekly_construction_report(data, 'samples\\ai_construction_weekly_report.xlsx', report_style='internal'))"
.\.venv\Scripts\python.exe scripts\smoke_test_real_scheduler.py --db C:\tmp\smart_scheduler_v2_2_smoke\demo.scheduler --excel C:\tmp\smart_scheduler_v2_2_smoke\field.xlsx --out-dir C:\tmp\smart_scheduler_v2_2_smoke\outputs
```

### Test Result

- New v2.2 importer tests before implementation: failed as expected with
  missing `conflict_policy`, `dry_run`, validation, and unknown-activity
  handling.
- New smoke script contract before implementation: failed as expected with
  missing `scripts.smoke_test_real_scheduler`.
- New Excel protection test before implementation: failed as expected because
  `freeze_panes` and sheet protection were absent.
- New EVM/dashboard helper tests before implementation: failed as expected with
  missing `core.evm` and `build_dashboard_report_file`.
- v2.2 focused bundle: `33 passed`.
- Full suite: `153 passed`.
- `ruff check .`: `All checks passed!`.
- `mypy .`: `Success: no issues found in 114 source files`.
- Demo smoke script: passed on a copied DB with `original_unchanged=true`.

### Failures And Fixes

- Failure: direct `python scripts\smoke_test_real_scheduler.py` could not import
  `core`.
- Fix: inserted repo root into `sys.path` for direct script execution and marked
  the subsequent imports with `# noqa: E402`.
- Failure: first post-implementation `ruff` run flagged the intentional import
  order in the smoke script.
- Fix: added the explicit `E402` exceptions above and reran ruff.

### Remaining Risks

- `merge` conflict policy is intentionally unsupported until a field-approved
  merge rule exists.
- Import validation is conservative and focused on v2.2 field-safety checks;
  richer row-level material/inspection validation can be expanded later.
- Smoke testing against the user's actual field DB still needs the real
  `.scheduler` and Excel input files; current smoke evidence uses a generated
  demo DB copy.
