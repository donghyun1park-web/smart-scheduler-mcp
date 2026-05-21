# PR #8 - v2.3 MCP Import + Cost Analysis + Relationship Inference

## Summary

This PR completes the next v2.3 step after the schedule/budget Excel importers
and sample DB generator.

It adds:

- MCP tools for schedule Excel and budget Excel import
- EVM snapshot, S-curve, and discipline-level cost-progress analysis tools
- Dry-run-first activity relationship inference for construction/MEP sequencing
- Sample DB smoke evidence for 46 activities and 45 cost items

## Current Baseline

- `core/schedule_importer.py`: schedule Excel to DB importer
- `core/budget_importer.py`: budget Excel to DB importer
- `scripts/create_sample_db.py`: sample DB generator
- v2.0-v2.2 CPM, SQLite, MCP, reporting, recovery wording, and field import
  behavior preserved

## New MCP Tools

Total MCP tools after this PR: `25`.

- `import_schedule_excel`
- `import_budget_excel`
- `analyze_evm_from_db`
- `get_evm_s_curve_data`
- `summarize_cost_by_discipline`
- `suggest_activity_relationships`
- `generate_activity_relationships`

## Safety Notes

- Import tools default to `dry_run=True`.
- Budget import requires an existing `.scheduler` DB for actual apply.
- Backups are created before non-dry-run import when the target DB exists.
- Relationship generation defaults to dry-run and does not persist unless
  `apply=True` is explicitly requested.
- Duplicate, self, unknown-activity, and cyclic relationship candidates are
  blocked before persistence.
- Relationship candidates include reasons and are marked as review-required
  candidates, not final construction decisions.

## Sample DB Smoke

- Sample DB command: `.\.venv\Scripts\python.exe scripts\create_sample_db.py --output samples\v2_3_sample.scheduler`
- Activities: `46`
- Cost items: `45`
- Relationships before inference: `0`
- Relationship suggestions: `45`
- Relationships after `apply=True` on sample copy: `45`
- Cycle validation: `pass`
- EVM smoke: `ok=true`
- S-curve smoke rows: `3`
- Discipline summary rows: `6`

## Quality Gates

- pytest: `193 passed, 16 warnings in 446.75s`
- ruff: `All checks passed!`
- mypy: `Success: no issues found in 127 source files`

## Known Warnings

- The 16 pytest warnings are openpyxl default-style warnings from real budget
  Excel workbooks.
- They are non-blocking and do not indicate test failure.

## Breaking Changes

None expected.

## Non-goals

- No schema version change.
- No merge into `main` in this step.
- No tracked `.scheduler` sample DB artifacts.

## Notes For Review

- Generated `.scheduler` sample files are ignored by `*.scheduler` and are not
  intended as committed artifacts.
- Direct script execution for `scripts/create_sample_db.py` now resolves the
  repository root before importing `core`, matching the documented CLI path.
