# v2.3 Candidate Plan

This is a planning document only. Do not start v2.3 implementation until the
v2.2 PR is merged and a real `.scheduler` DB smoke test has been reviewed.

## Entry Conditions

- v2.2 PR merged into `main`.
- Real DB smoke-test dry-run completed on a copied `.scheduler` DB.
- Main branch quality gates re-run.
- Smoke-test findings reviewed and prioritized.

## Priority Table

| Priority | Candidate | Reason | Expected Files |
|---:|---|---|---|
| 1 | Change Log 날짜 범위 필터 | Change history grows quickly during field use; date filtering improves operation and review speed. | `core/db.py`, `tools/construction_tools.py`, `server.py`, `tests/` |
| 2 | EVM dashboard/Excel visualization | v2.2 calculates EVM but users need better visual review surfaces. | `core/reporting.py`, `viewer/components/site_manager_dashboard.py`, `core/evm.py`, `tests/` |
| 3 | `progress_pct` unit ambiguity guard | Values like `0.5` can mean 0.5% or 50%; import/report warnings should make assumptions explicit. | `core/evm.py`, `core/number_utils.py`, `core/validation.py`, `tests/` |
| 4 | Multi-project comparison view | Headquarters users need read-only comparison across several `.scheduler` files. | `viewer/`, `tools/`, `tests/` |
| 5 | Smoke-test findings | Real data should drive the next fixes before speculative features. | finding-specific |

## Candidate 1 — Change Log Date Range Filter

Add optional `start_changed_at`, `end_changed_at`, `limit`, and `offset` support
to DB and MCP change-log queries.

Tests:

- date range returns only matching rows
- `target_table` plus date range
- `target_id` plus date range
- `limit` and `offset`
- invalid date message is specific

## Candidate 2 — EVM Dashboard and Excel Visualization

Expose PV, EV, AC, SV, CV, SPI, CPI, and status more clearly.

Streamlit:

- KPI cards for PV/EV/AC
- SPI/CPI status indicator
- risk list where `status == "risk"`

Excel:

- New `EVM` sheet
- overall EVM summary
- discipline EVM summary
- SPI/CPI conditional formatting

## Candidate 3 — `progress_pct` Unit Ambiguity Guard

Keep current 0..1 auto-normalization for compatibility, but warn when external
data contains ambiguous fractional progress values.

Recommended first step:

- import warning when `0 < progress_pct < 1`
- docs state `progress_pct` is 0..100 by default
- future optional `progress_unit` field can be considered later

## Candidate 4 — Multi-Project Comparison View

Read several `.scheduler` files and show a read-only headquarters comparison.

MVP fields:

- project name
- planned progress
- actual progress
- progress gap
- cost execution rate
- delayed count
- cost risk count
- SPI/CPI where available

Out of scope:

- central server sync
- authentication
- project data merging
- real-time collaboration

## v2.3 Guardrails

Do not do these during PR/smoke preparation:

- `SCHEMA_VERSION = 3`
- large EVM calculation rewrite
- Streamlit architecture rewrite
- DB schema additions
- large MCP tool expansion
