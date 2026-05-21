# AGENTS.md - AI Construction Schedule Development Rules

## Project Goal

Extend the current `smart-scheduler-mcp` repository into the AI Construction
Schedule v2.0 MVP: Excel-centered input and reporting, Python calculations,
SQLite storage, Streamlit dashboard views, and MCP tools for AI-assisted
drafts.

## Environment Gate

- Acceptance environment is Python `>=3.11,<3.13`.
- Test results from Python 3.14 or Python 2.7 are not acceptance evidence.
- All installs and tests must run through the project virtual environment
  Python, for example `.\.venv\Scripts\python.exe`.
- Do not add runtime entries such as `python>=3.11` to `requirements.txt`.
- Python runtime limits belong only in `pyproject.toml` as `requires-python`.
- If Python 3.11 or 3.12 is unavailable, stop environment verification and
  report the missing runtime instead of installing dependencies into another
  Python version.

## Core Principles

- Do not break the existing CPM, SQLite, MCP, Streamlit, Plotly, or Excel report
  behavior.
- The v2 operating loop is Excel input -> SQLite v2 tables -> validation and
  calculation -> Excel weekly report.
- Treat Excel as the field input and review surface; keep calculations,
  validation, aggregation, and report generation in Python.
- Do not turn `Activity` into a catch-all table. Add separate tables for
  `daily_records`, `cost_items`, `baseline_snapshots`, `materials`,
  `inspections`, `change_log`, and `project_settings`.
- Support both existing MEP disciplines and v2 Korean construction disciplines:
  `토목`, `건축`, `기계설비`, `소방설비`, `전기설비`, `공통`.
- AI-assisted recovery output must remain a draft or candidate. Never present it
  as a final decision.
- Data validation and backup behavior have priority over convenience features.
- Keep external APIs, cloud dependencies, BIM integration, full EVM, and full
  authentication outside the MVP unless they are documented as extension points.
- Keep every change small, testable, and commit-ready.

## Development Order

1. Analyze the current structure and run the existing acceptance checks.
2. Extend the SQLite/data model without bloating `Activity`.
3. Implement `core.progress`, `core.cost`, `core.delay_detection`,
   `core.recovery`, `core.backup`, and focused `core.validation` extensions.
4. Implement Excel templates, import/export, and weekly report generation.
5. Add the site-manager dashboard and MCP tools.
6. Stabilize tests, sample data, docs, and release notes.

## Forbidden Moves

- Do not continue feature work while existing CPM, DB, MCP, or report tests are
  failing without first analyzing the failure.
- Do not add 30 or more new fields directly to `Activity`.
- Do not use final-decision phrases such as "confirmed plan" or "must execute"
  in AI recovery suggestions. Use "draft", "candidate", "review required", or
  equivalent Korean wording such as "초안", "후보", "검토 필요".
- Do not make Excel VBA the default implementation path.
- Do not implement photo upload, weather APIs, BIM integration, full EVM, or
  full user authentication as MVP scope.

## Validation Commands

Run these through the project virtual environment Python:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
```

If `.venv` is broken or Python 3.11/3.12 is unavailable, record the blocker in
`CHECKPOINT_LOG.md` and do not substitute Python 3.14 or Python 2.7 results.

## Checkpoint Log

After each phase, update `CHECKPOINT_LOG.md` with:

- Changed files
- Implemented behavior
- Commands run
- Failures and fixes
- Remaining risks
