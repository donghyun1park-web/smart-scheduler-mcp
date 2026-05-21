# Smart Scheduler MCP

건설현장 공정/원가/기성 관리 MCP 서버. Claude가 현장소장의 AI 비서 역할.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[test]"
pytest --ignore=tests/test_budget_importer.py   # 빠른 테스트 (200개, ~1분)
pytest                                          # 전체 테스트 (실행예산 파일 필요, ~6분)
```

## Architecture

```
server.py              ← MCP 서버 진입점 (40 tools)
core/                  ← 비즈니스 로직
  db.py                  SQLite .scheduler 파일 (SCHEMA_VERSION=2)
  models.py              dataclass: Project, Activity, CostItem, etc.
  billing.py             기성고 산출/S-curve
  dashboard.py           현장 대시보드/브리핑
  budget_importer.py     실행예산 Excel → DB (Type A/B 자동감지)
  schedule_importer.py   공정표 바차트 Excel → DB
  relationship_inference.py  Activity 간 관계 자동추론
  evm.py / cost.py / s_curve.py / cpm.py  원가/공정 분석
tools/                 ← MCP tool 래퍼 (server.py에서 등록)
  billing_tools.py       기성고 4개 도구
  dashboard_tools.py     대시보드 4개 도구
  material_tools.py      자재/검측 7개 도구
  cost_tools.py          EVM/원가 3개 도구
  import_tools.py        Excel 임포트 3개 도구
  relationship_tools.py  관계추론 2개 도구
  construction_tools.py  일보/지연/만회/주간보고 7개 도구
tests/                 ← pytest (200+ tests)
scripts/
  create_sample_db.py   샘플 .scheduler DB 생성 (실제 Excel 필요)
```

## Current State (2026-05-21)

- **Branch**: `feature/v2.4-billing-dashboard-materials`
- **PR**: #9 (OPEN) — v2.4 기성/대시보드/자재 도구
- **PR**: #8 (OPEN) — v2.3 Excel 임포터/EVM/관계추론
- **Main**: v2.2 merged (PR #7)
- **Quality**: ruff OK, mypy OK, 200 tests passed

### Version History

| Version | Branch | PR | Status | Features |
|---------|--------|----|--------|----------|
| v2.2 | main | #7 merged | complete | Field import hardening |
| v2.3 | feature/v2.3-importers | #8 open | review | Excel importers, EVM, relationships |
| v2.4 | feature/v2.4-billing-dashboard-materials | #9 open | review | Billing, dashboard, materials |

### MCP Tools (40 total)

**Project**: list_projects, load_project, create_project
**Import**: import_excel, import_schedule_excel, import_budget_excel
**Analysis**: calculate_cpm, get_critical_path, analyze_evm_from_db, get_evm_s_curve_data, summarize_cost_by_discipline
**Relationships**: suggest_activity_relationships, generate_activity_relationships
**Billing**: calculate_billing, apply_billing, billing_summary, billing_s_curve
**Dashboard**: get_site_briefing, get_dashboard_report, get_discipline_progress, get_delayed_activities
**Materials**: add_material, list_materials_tool, update_material, add_inspection, list_inspections_tool, update_inspection, get_activity_logistics
**Construction**: input_daily_record, detect_delays, suggest_recovery, generate_weekly_report, import_excel_input_to_db, generate_weekly_report_from_db, list_change_log_tool, summarize_site_status
**Other**: apply_sequences, generate_report, calibrate_completion_date, run_field_uat_workflow

## Conventions

- Python 3.12, Windows 환경
- DB: SQLite `.scheduler` 파일 (PRAGMA foreign_keys=ON)
- Discipline: 건축, 토목, 기계설비, 전기설비, 소방설비, 공통 + MEP(위생, 공조, 소방, 전기, 자동제어)
- apply/update 계열 도구는 `dry_run=True` 기본값 (안전)
- 테스트: `tmp_path` fixture 사용, 실제 Excel 테스트는 파일 없으면 `pytest.skip`
- Korean in code: 변수명은 영어, 사용자 facing 문자열은 한국어

## Real Data Files (not in repo)

- 공정표: `C:/MirTalk/Download/홍은동 355번지 가로주택_전체공정표.xlsx`
- 실행예산(건축): `C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서 (PC공사등).xlsx`
- 실행예산(토목): `C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서(가설,토목,파일공사).xlsx`
- 실행예산(기계): `C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서(기계설비).xlsx`
- 실행예산(전기): `C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서(전기,통신,전기소방).xlsx`
