# Real Scheduler DB Smoke Test

Use this v2.2 smoke test when checking a real `.scheduler` DB. The script never
works on the source DB directly; it copies the DB into the output directory and
runs dashboard, import dry-run, report, recovery, and result JSON checks on the
copy.

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_real_scheduler.py --db path\to\real.scheduler --excel path\to\field_input.xlsx --out-dir smoke_outputs
```

Use `--apply` only when you want the copied DB to receive the import after the
dry run succeeds.

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_real_scheduler.py --db path\to\real.scheduler --excel path\to\field_input.xlsx --out-dir smoke_outputs --apply
```

Outputs:

- Timestamped copied `.scheduler` DB
- `internal`, `hq`, and `client` weekly reports
- Smoke result JSON

Pass criteria:

- Original DB modification time is unchanged.
- Dashboard summary loads from the copied DB.
- Import dry-run returns `changed=False`.
- Reports are generated for all three report styles.
- Recovery templates return candidates for all eight supported reason codes.
- No forbidden final-decision wording appears in recovery output.
