# PR Description v2.5 — Operations Center

## Summary

v2.5 adds an Operations Center layer on top of the existing scheduler DB, MCP tools, EVM, dashboard, billing, material, and inspection workflows. The new layer is read-only by default and helps field users decide what to check next before daily close or weekly reporting.

## What Changed

- Added `core/data_health.py` with a 0-100 health score, Korean issue messages, severity counts, and read-only DB diagnostics.
- Added `core/next_actions.py` with profile-based next action candidates for `field_admin`, `site_manager`, `hq`, and `developer`.
- Added `core/evm_explain.py` to convert EVM totals into Korean plain-language explanations.
- Added `core/workflows.py` for daily close and weekly report precheck statuses.
- Added `tools/diagnostic_tools.py` and registered four new MCP tools:
  - `check_data_health`
  - `suggest_next_actions`
  - `explain_evm_from_db`
  - `get_workflow_status`
- Added Streamlit Operations Center home state/rendering helpers and page:
  - `viewer/components/operations_home.py`
  - `viewer/pages/00_operations_center.py`
- Added v2.5 tests for data health, next actions, EVM explanation, workflows, operations home, MCP diagnostic tools, and server registration.
- Added a one-page AI usage guide for Operations Center workflows.

## Safety Notes

- The new diagnostics do not mutate `.scheduler` DB files.
- AI suggestions are candidates only; final operational decisions stay with the field team.
- Import rollback, auth/permissions, multi-project portfolio, mobile notifications, and real-time monitoring remain out of scope for v2.5.

## Verification

Latest local verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
git diff --check
```

- `pytest -q`: `235 passed, 16 warnings in 515.61s`
- `ruff check .`: `All checks passed!`
- `mypy .`: `Success: no issues found in 148 source files`
- `git diff --check`: exit 0; only expected LF-to-CRLF working-copy warnings
- Sample Operations Center smoke: `health=healthy`, `score=85`, `actions=4`, `evm=not_available`, workflow prechecks blocked by missing recent daily record in sample DB
- MCP tool count: `44`
