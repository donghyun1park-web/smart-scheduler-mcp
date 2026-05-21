# AI Construction Scheduler v2.0 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Smart Node-Scheduler v0.1 into an AI Construction Schedule
v2.0 MVP that preserves existing CPM, SQLite, MCP, Streamlit, and Excel report
features while adding field-ready progress, cost, delay, recovery-draft,
validation, backup, Excel, dashboard, and MCP workflows.

**Architecture:** Keep `activities` focused on schedule identity and CPM fields.
Store daily progress, costs, baselines, materials, inspections, change history,
and project settings in separate SQLite tables and focused dataclasses. Use
Python for calculations and openpyxl/xlsxwriter for Excel artifacts; expose
AI-facing actions through MCP tools that return draft/candidate language only.

**Tech Stack:** Python 3.11/3.12, SQLite, dataclasses, xlsxwriter/openpyxl,
Streamlit, Plotly, MCP FastMCP, pytest, ruff, mypy.

---

## Current Repository Map

- `core/models.py`: Project, WBS, Activity, Relationship, Calendar, CPM result
  dataclasses. Keep `Activity` lean.
- `core/db.py`: SQLite schema creation and CRUD helpers. Add new tables here in
  compatible migrations.
- `core/cpm.py`, `core/cpm_networkx.py`, `core/cpm_pycritical.py`: CPM wrapper
  and engines. Preserve behavior and tests.
- `core/reporting.py`: xlsxwriter Excel report writer. Extend with MVP workbook
  sheets without removing the base sheets.
- `core/validation.py`: reusable validation helpers. Extend with field-data
  validators that include activity name, value, and cause in messages.
- `server.py`: MCP tool registration. Add v2.0 tools after tool functions are
  implemented.
- `tools/`: MCP-facing function wrappers. Add thin wrappers that call `core`
  modules.
- `viewer/`: Streamlit UI. Add site-manager dashboard page/component without
  disrupting existing pages.
- `tests/`: regression and unit tests. Add tests before implementation for each
  new behavior.
- `presets/`: existing column-mapping presets. Add sample site data and report
  presets under a separate folder if needed.

## Phase 0 - Baseline And Work Rules

**Files:**
- Modify: `AGENTS.md`
- Create: `PLAN.md`
- Create: `CHECKPOINT_LOG.md`

- [x] **Step 1: Read the user development plan**

  Read `C:\Users\User\Downloads\AI건축공정표_프로그램_개발계획서.md` as UTF-8 and
  use it as the MVP scope source.

- [x] **Step 2: Confirm branch isolation**

  Use branch `feature/ai-construction-scheduler-v2` for this work.

- [x] **Step 3: Record acceptance environment**

  Run:

  ```powershell
  .\.venv\Scripts\python.exe --version
  py -0p
  ```

  Expected acceptance evidence is Python 3.11 or 3.12 from `.venv`. If missing,
  record the blocker and do not run acceptance checks with Python 3.14 or 2.7.

- [x] **Step 4: Write repository rules**

  Update `AGENTS.md` with v2.0 MVP rules while preserving the Python acceptance
  gate.

- [x] **Step 5: Create this plan and checkpoint log**

  Add `PLAN.md` and `CHECKPOINT_LOG.md`.

## Phase 1 - Data Model And Core Engines

**Files:**
- Modify: `core/models.py`
- Modify: `core/db.py`
- Modify: `core/validation.py`
- Create: `core/progress.py`
- Create: `core/cost.py`
- Create: `core/delay_detection.py`
- Create: `core/recovery.py`
- Create: `core/backup.py`
- Test: `tests/test_db_v2_schema.py`
- Test: `tests/test_progress.py`
- Test: `tests/test_cost.py`
- Test: `tests/test_delay_detection.py`
- Test: `tests/test_recovery.py`
- Test: `tests/test_backup.py`
- Test: `tests/test_validation_v2.py`

- [x] **Task 1: Add failing schema tests**

  Verify `initialize_database()` creates these tables without adding columns to
  `activities`: `daily_records`, `cost_items`, `baseline_snapshots`,
  `materials`, `inspections`, `change_log`, `project_settings`.

- [x] **Task 2: Implement schema additions and indexes**

  Add compatible `CREATE TABLE IF NOT EXISTS` statements and indexes for
  activity/date lookups.

- [x] **Task 3: Add failing progress tests**

  Cover planned quantity zero, actual greater than planned, weighted progress,
  and milestone status mapping.

- [x] **Task 4: Implement progress calculations**

  Implement quantity, weighted, milestone, and aggregate progress helpers with
  deterministic outputs.

- [x] **Task 5: Add failing cost tests**

  Cover execution rate, billing rate, overrun detection, and completion-cost
  forecast.

- [x] **Task 6: Implement cost calculations**

  Keep division-by-zero behavior explicit and return safe numeric summaries.

- [x] **Task 7: Add failing delay and recovery tests**

  Cover schedule delay, overdue finish, predecessor block, material delay,
  inspection delay, manpower shortage, missing owner, and candidate recovery
  language.

- [x] **Task 8: Implement delay detection and recovery drafts**

  Return structured dictionaries with reason codes, severity, responsible
  person, delay days, and Korean/English-safe draft wording.

- [x] **Task 9: Add failing validation and backup tests**

  Ensure validation errors include activity name, value, and cause. Ensure
  backups are created before report/baseline-sensitive operations and rotate at
  the configured limit.

- [x] **Task 10: Implement validation extensions and backup helpers**

  Add focused validators and copy-based backup/restore path helpers.

## Phase 2 - Excel Input And Weekly Reports

**Files:**
- Create: `core/excel_io.py`
- Modify: `core/reporting.py`
- Modify: `tools/report_tools.py`
- Create: `samples/ai_construction_site_sample.json`
- Create: `tests/test_excel_io.py`
- Create: `tests/test_weekly_report_v2.py`

- [x] **Task 1: Write failing workbook template tests**

  Require sheets `01_실적입력`, `02_원가입력`, `03_자재검측`, `04_공정표`,
  `05_대시보드`, `06_부진공정`, and `07_보고서`.

- [x] **Task 2: Implement Excel template writer**

  Use openpyxl or xlsxwriter with input cells styled yellow, auto-calculated
  cells grey, and error/attention cells red or orange.

- [x] **Task 3: Write failing weekly report tests**

  Verify dashboard metrics, current-week actuals, delayed TOP 10, recovery
  draft candidates, cost status, next-week work, and Gantt data are present.

- [x] **Task 4: Implement weekly report generation**

  Extend report creation without removing the existing v0.1 sheets.

## Phase 3 - Site Manager Dashboard

**Files:**
- Create: `viewer/components/site_manager_dashboard.py`
- Create: `viewer/pages/08_site_manager_dashboard.py`
- Create: `tests/test_site_manager_dashboard.py`

- [x] **Task 1: Write failing dashboard metric tests**

  Require planned progress, actual progress, progress variance, cost execution,
  billing rate, delayed count, risk discipline, and key risk summary.

- [x] **Task 2: Implement dashboard summary builder**

  Keep calculation logic in `core` and make Streamlit rendering a thin view.

- [x] **Task 3: Add configurable green/yellow/orange/red thresholds**

  Store defaults in `project_settings` and allow a caller override.

## Phase 4 - MCP Tool Expansion

**Files:**
- Create: `tools/construction_tools.py`
- Modify: `server.py`
- Create: `tests/test_construction_tools.py`
- Modify: `tests/test_server.py`

- [x] **Task 1: Add failing MCP wrapper tests**

  Cover `input_daily_record`, `detect_delays`, `suggest_recovery`,
  `generate_weekly_report`, and `summarize_site_status`.

- [x] **Task 2: Implement thin tool wrappers**

  Validate input, call `core` modules, and return JSON-serializable results.

- [x] **Task 3: Register MCP tools**

  Add the new tools to `build_server()` and assert they are discoverable.

- [x] **Task 4: Guard recovery wording**

  Tests must fail if output contains final-decision wording such as `확정`,
  `반드시 시행`, `confirmed`, or `must execute`.

## Phase 5 - Stabilization, Samples, And Docs

**Files:**
- Modify: `README.md`
- Create: `docs/AI_CONSTRUCTION_SCHEDULER_V2_USER_GUIDE.md`
- Create: `docs/AI_CONSTRUCTION_SCHEDULER_V2_DATA_MODEL.md`
- Create: `docs/RELEASE_NOTES_v0.2.0-MVP.md`
- Modify: `CHECKPOINT_LOG.md`

- [x] **Task 1: Add sample scenario tests**

  Sample data must include normal work, delayed work, predecessor block, cost
  overrun, material delay, inspection delay, missing owner, and baseline change.

- [x] **Task 2: Generate sample artifacts**

  Produce a weekly Excel report and dashboard-ready summary from the sample
  project.

- [x] **Task 3: Run acceptance checks**

  Run:

  ```powershell
  .\.venv\Scripts\python.exe -m pip check
  .\.venv\Scripts\python.exe -m pytest -q
  .\.venv\Scripts\python.exe -m ruff check .
  .\.venv\Scripts\python.exe -m mypy .
  ```

- [x] **Task 4: Document usage and limitations**

  README and docs must explain setup, Excel workflow, dashboard workflow, MCP
  tools, sample data reproduction, known limitations, and deferred 2차 scope.

## Completion Criteria

- Existing CPM, SQLite, MCP, Streamlit, and v0.1 Excel tests pass.
- New tests exist for progress, cost, delay detection, validation, backup,
  Excel I/O, reporting, dashboard, and MCP construction tools.
- Sample site data can generate an Excel weekly report and site-manager
  dashboard summary.
- AI recovery output uses only draft/candidate/review-required language.
- `CHECKPOINT_LOG.md` records implementation, test results, failures/fixes, and
  remaining risks for every phase.
