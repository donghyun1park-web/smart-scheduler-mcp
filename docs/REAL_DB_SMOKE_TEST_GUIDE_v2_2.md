# Real DB Smoke Test Guide — v2.2

Use this guide after the v2.2 PR is ready or merged. The source `.scheduler`
file must never be modified directly.

## Principle

```text
original .scheduler
-> timestamped copy under smoke_outputs
-> dashboard/import/report/recovery checks on copied DB only
-> original mtime/hash remains unchanged
```

## Dry Run Without Excel Apply

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_real_scheduler.py --db path\to\real.scheduler --out-dir smoke_outputs\real_v2_2_20260521
```

## Dry Run With Excel Input

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_real_scheduler.py --db path\to\real.scheduler --excel path\to\field_input.xlsx --out-dir smoke_outputs\real_v2_2_20260521
```

## Apply Mode On Copied DB Only

Use this only after dry-run succeeds.

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_real_scheduler.py --db path\to\real.scheduler --excel path\to\field_input.xlsx --out-dir smoke_outputs\real_v2_2_apply_20260521 --apply
```

`--apply` imports into the copied DB produced inside `--out-dir`; it does not
write to the original source DB.

## Expected Outputs

- Timestamped copied `.scheduler` DB
- `internal`, `hq`, and `client` weekly reports
- Smoke result JSON

## PASS Criteria

| Check | PASS Criteria |
|---|---|
| original_unchanged | source DB mtime unchanged |
| dashboard load | dashboard summary exists |
| dry_run import | `changed=false` |
| report styles | internal/hq/client files created |
| recovery templates | 8 reason codes checked |
| forbidden words | no final-decision wording |
| EVM | summary includes EVM status |

## Current Preparation Result

Real field DB path was not provided. Preparation used a generated demo DB and
Excel input in `C:\tmp\smart_scheduler_pr_smoke_v2_2`.

Result:

```text
ok=true
original_unchanged=true
reports=internal,hq,client
recovery_forbidden_word_violations=[]
result_json=C:\tmp\smart_scheduler_pr_smoke_v2_2\outputs\demo_smoke_20260521_031108_smoke_result.json
```

## Result Report Template

```markdown
# Real .scheduler Smoke Test Result — v2.2

## Input
- Original DB:
- Copied DB:
- Excel input:
- Apply mode:

## Checks
| Check | Result | Notes |
|---|---|---|
| original_unchanged |  |  |
| dashboard load |  |  |
| dry_run import |  |  |
| 3 report styles |  | internal/hq/client |
| recovery templates |  | 8 reason codes |
| forbidden final words |  |  |
| change_log query |  |  |
| EVM calculation |  |  |

## Findings

## Follow-up
```
