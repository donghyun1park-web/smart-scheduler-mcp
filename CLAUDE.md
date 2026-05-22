# Smart Scheduler MCP

건설현장 공정/원가/기성 관리 MCP 서버. Claude가 현장소장의 AI 비서 역할.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[test]"
pytest --ignore=tests/test_budget_importer.py   # 빠른 테스트 (322개, ~1분)
pytest                                          # 전체 테스트 (실행예산 파일 필요, ~6분)
```

## Architecture

```
server.py              ← MCP 서버 진입점 (59 tools)
core/                  ← 비즈니스 로직
  db.py                  SQLite .scheduler 파일 (SCHEMA_VERSION=2, 3 new tables)
  models.py              dataclass: Project, Activity, CostItem, DelayEvent, ChangeOrder, etc.
  billing.py             기성고 산출/S-curve
  cashflow.py            현금흐름 예측 (v2.6)
  cost.py                원가 분석/예산 차이/EAC 시나리오 (v2.6 확장)
  delay_analysis.py      공기지연 분류/클레임 (v2.7)
  productivity.py        생산성 분석/추세 (v2.7)
  change_order.py        설계변경 관리 (v2.8)
  dashboard.py           현장 대시보드/브리핑
  data_health.py         읽기 전용 데이터 건강점수/오류 진단
  next_actions.py        사용자 역할별 다음 행동 추천
  evm_explain.py         EVM 지표 한국어 쉬운 설명
  workflows.py           일일마감/주간보고 사전점검 상태
  budget_importer.py     실행예산 Excel → DB (Type A/B 자동감지)
  schedule_importer.py   공정표 바차트 Excel → DB
  relationship_inference.py  Activity 간 관계 자동추론
  evm.py / s_curve.py / cpm.py  EVM/S-curve/CPM 분석
tools/                 ← MCP tool 래퍼 (server.py에서 등록)
  billing_tools.py       기성고 4개 도구
  dashboard_tools.py     대시보드 4개 도구
  material_tools.py      자재/검측 7개 도구
  cost_tools.py          EVM/원가 5개 도구 (v2.6: +2)
  cashflow_tools.py      현금흐름 3개 도구 (v2.6)
  delay_tools.py         지연분석 4개 도구 (v2.7)
  productivity_tools.py  생산성 2개 도구 (v2.7)
  change_order_tools.py  설계변경 6개 도구 (v2.8)
  import_tools.py        Excel 임포트 3개 도구
  relationship_tools.py  관계추론 2개 도구
  construction_tools.py  일보/지연/만회/주간보고 7개 도구
  diagnostic_tools.py    운영센터/진단 4개 도구
viewer/
  pages/00_operations_center.py  Streamlit 운영센터 홈
tests/                 ← pytest (322 tests)
scripts/
  create_sample_db.py   샘플 .scheduler DB 생성 (실제 Excel 필요)
```

## Current State (2026-05-22)

- **Branch**: `feature/v2.5-operations-center`
- **Local work**: v2.8 DDC Skills 통합 완료 (현금흐름, 예산차이, 지연분석, 생산성, 설계변경)
- **PR**: #9 (OPEN) — v2.4 기성/대시보드/자재 도구
- **PR**: #8 (OPEN) — v2.3 Excel 임포터/EVM/관계추론
- **Main**: v2.2 merged (PR #7)
- **Quality**: pytest 322 passed, ruff OK, mypy OK

### Version History

| Version | Branch | PR | Status | Features |
|---------|--------|----|--------|----------|
| v2.2 | main | #7 merged | complete | Field import hardening |
| v2.3 | feature/v2.3-importers | #8 open | review | Excel importers, EVM, relationships |
| v2.4 | feature/v2.4-billing-dashboard-materials | #9 open | review | Billing, dashboard, materials |
| v2.5 | feature/v2.5-operations-center | not opened | local ready | Operations Center, data health, next actions |
| v2.6 | (local) | — | complete | Cash flow forecaster, budget variance analyzer |
| v2.7 | (local) | — | complete | Schedule delay analyzer, productivity analyzer |
| v2.8 | (local) | — | complete | Change order processor |

### MCP Tools (59 total)

**Project**: list_projects, load_project, create_project
**Import**: import_excel, import_schedule_excel, import_budget_excel
**Analysis**: calculate_cpm, get_critical_path, analyze_evm_from_db, get_evm_s_curve_data, summarize_cost_by_discipline
**Relationships**: suggest_activity_relationships, generate_activity_relationships
**Billing**: calculate_billing, apply_billing, billing_summary, billing_s_curve
**Dashboard**: get_site_briefing, get_dashboard_report, get_discipline_progress, get_delayed_activities
**Materials**: add_material, list_materials_tool, update_material, add_inspection, list_inspections_tool, update_inspection, get_activity_logistics
**Construction**: input_daily_record, detect_delays, suggest_recovery, generate_weekly_report, import_excel_input_to_db, generate_weekly_report_from_db, list_change_log_tool, summarize_site_status
**Operations**: check_data_health, suggest_next_actions, explain_evm_from_db, get_workflow_status
**Cash Flow (v2.6)**: forecast_project_cash_flow, get_funding_requirements, get_retention_release_schedule
**Budget Variance (v2.6)**: analyze_budget_variance, forecast_cost_scenarios
**Delay Analysis (v2.7)**: record_delay_event, list_delay_events_tool, analyze_delays, calculate_time_extension_claim
**Productivity (v2.7)**: analyze_productivity, get_productivity_trend
**Change Orders (v2.8)**: create_change_order, add_change_order_item, update_change_order_status, list_change_orders_tool, get_change_order_impact, get_change_order_summary
**Other**: apply_sequences, generate_report, calibrate_completion_date, run_field_uat_workflow

### AI Usage Guide

- 운영자는 먼저 `check_data_health`로 데이터 건강점수와 오류 원인을 확인한다.
- 다음 행동은 `suggest_next_actions`로 역할별 후보를 받되, 적용 전 사람이 검토한다.
- 본사용 설명은 `explain_evm_from_db`를 사용해 PV/EV/AC, SPI/CPI를 쉬운 한국어로 요약한다.
- 일일마감과 주간보고 전에는 `get_workflow_status`로 필수 단계와 경고를 확인한다.
- 현금흐름은 `forecast_project_cash_flow`로 월별 inflow/outflow를 예측하고, `get_funding_requirements`로 자금 소요를 확인한다.
- 예산관리는 `analyze_budget_variance`로 공종별 차이를 분석하고, `forecast_cost_scenarios`로 EAC 시나리오를 본다.
- 공기지연은 `record_delay_event`로 기록 후, `analyze_delays`로 유형/원인별 집계, `calculate_time_extension_claim`으로 클레임을 산출한다.
- 생산성은 `analyze_productivity`로 활동별/공종별 지수를 확인하고, `get_productivity_trend`로 추세를 본다.
- 설계변경은 `create_change_order` → `add_change_order_item` → `update_change_order_status` 순서로 처리하고, `get_change_order_summary`로 전체 현황을 본다.
- 만회대책/다음 행동 문구는 초안, 후보, 검토 필요 표현을 사용하며 최종 판단은 현장 책임자가 한다.

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
