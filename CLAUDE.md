# Smart Scheduler MCP

건설현장 공정/원가/기성 관리 MCP 서버. Claude가 현장소장의 AI 비서 역할.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[test]"
pytest --ignore=tests/test_budget_importer.py   # 빠른 테스트 (406개 통과, ~3분)
pytest                                          # 전체 테스트 (실행예산 파일 필요, ~6분)

# MCP 서버 (Claude Desktop 연결)
python src/backend/server.py

# 모바일 입력 앱 (Streamlit)
streamlit run src/frontend/app_mobile.py

# NAS 배포
docker-compose -f infrastructure/docker/docker-compose.yml up -d
```

## Architecture (v3.4 폴더 재구성)

```
smart-scheduler-mcp/
├── src/
│   ├── backend/                 ← MCP 서버 + FastAPI (Python 진입점)
│   │   ├── server.py              MCP 서버 진입점 (67 tools)
│   │   ├── main.py                FastAPI 모바일 백엔드
│   │   ├── core/                  비즈니스 로직 (db, models, billing, cost, ...)
│   │   ├── tools/                 MCP tool 래퍼 (server.py에서 등록)
│   │   ├── scripts/               유틸 스크립트 (create_sample_db, smoke_test)
│   │   └── requirements.txt       백엔드 의존성
│   └── frontend/                ← Streamlit 앱들
│       ├── app_mobile.py          모바일 실적 입력 (v3.3 통합 UX)
│       ├── app_dashboard.py       PC 현장소장 대시보드
│       ├── requirements.txt
│       └── _deprecated_viewer/    구 viewer 코드 (참조용)
├── tests/                       ← pytest 통합 테스트 (~406 passed)
├── infrastructure/              ← 배포/인프라
│   ├── docker/                    Dockerfile.api, Dockerfile.streamlit, docker-compose.yml
│   └── presets/                   기본 설정 프리셋
├── docs/                        ← 모든 문서 (사용설명서 docx 포함)
├── mockups/                     ← UI 목업 HTML (개발 참조용)
├── mep/                         ← MEP 시퀀스 데이터 (sequences.json)
├── samples/                     ← 샘플 데이터 (.scheduler, json, xlsx)
├── conftest.py                  ← pytest sys.path 설정 (src/backend 노출)
├── pyproject.toml               ← package-dir = src/backend
├── .gitignore
└── CLAUDE.md
```

### Import 규칙

- 모든 backend 코드는 `from core.X` / `from tools.X` 형태 사용
- `pythonpath = ["src/backend"]` (pyproject.toml) + `conftest.py` 가 자동 설정
- 외부에서 import 시: `pip install -e .` 후 `from core.X` 사용 가능
- mep/, samples/는 데이터 폴더 — 코드 import 대상 아님

### Core 모듈 (src/backend/core/)

  db.py / models.py / billing.py / cashflow.py / cost.py / delay_analysis.py
  productivity.py / change_order.py / dashboard.py / dashboard_logic.py
  data_health.py / next_actions.py / evm_explain.py / workflows.py
  budget_importer.py / schedule_importer.py / relationship_inference.py
  evm.py / s_curve.py / cpm.py / report_parser.py (v3.1: Vision AI)

### Tools 모듈 (src/backend/tools/)

  billing_tools / dashboard_tools / material_tools / cost_tools / cashflow_tools
  delay_tools / productivity_tools / change_order_tools / import_tools
  relationship_tools / construction_tools / diagnostic_tools / analysis_tools
  calibration_tools / sequence_tools

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
| v2.8 | (local) | — | complete | Change order processor (+ apply_change_order 실반영) |
| v2.9 | (local) | — | complete | Quick Wins: 활성 프로젝트 컨텍스트, 기준공정표(Baseline), 능동 경고 |
| v3.0 | (local) | — | complete | 모바일 현장 입력 시스템 (NAS Docker 배포) |
| v3.1 | (local) | — | complete | 공사일보 사진→데이터 자동 추출 (Vision AI + Excel 파서) |
| v3.2 | (local) | — | complete | 멀티 Vision 프로바이더 (Gemini 기본값, Claude 옵션) |
| v3.3 | (local) | — | complete | 카메라 우선 3단계 UX, app_mobile.py + app_report_scan.py 통합 |
| v3.4 | (local) | — | complete | **폴더 재구성**: src/{backend,frontend}/, tests/ 루트로, infrastructure/ 도입 |

### MCP Tools (67 total)

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
**Change Orders (v2.8)**: create_change_order, add_change_order_item, update_change_order_status, apply_change_order, list_change_orders_tool, get_change_order_impact, get_change_order_summary
**Context (v2.9)**: set_active_project, get_active_project, clear_active_project (db_path 자동 해결)
**Baseline (v2.9)**: establish_baseline, list_baselines, compare_to_baseline (기준공정표 대비 지연 측정)
**Alerts (v2.9)**: get_site_alerts (자재납기/CO/공정 능동 경고; get_site_briefing에도 자동 포함)
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
- 설계변경은 `create_change_order` → `add_change_order_item` → `update_change_order_status`(pending→approved) → `apply_change_order`(dry_run=False) 순서로 처리하고, `get_change_order_summary`로 전체 현황을 본다.
- `apply_change_order`는 승인(approved) 상태의 CO만 실반영하며, 각 세부항목의 공기·원가 변동이 activities와 cost_items에 직접 반영된다. 반영 후 상태는 '실반영완료(applied)'로 변경된다.
- 활성 프로젝트 컨텍스트(v2.9): `set_active_project`로 db_path를 한 번 등록하면 이후 모든 도구에서 db_path를 생략할 수 있다. 비기술 사용자(건축담당, 공무과장 등)에게 유용하다.
- 기준공정표(v2.9): 착공 시 `establish_baseline`(dry_run=False)으로 기준을 확정하고, 이후 `compare_to_baseline`으로 현재 공정 대비 지연일수(finish_drift_days)를 확인한다. 여러 기준선을 등록해 revision별 비교가 가능하다.
- 능동 경고(v2.9): `get_site_alerts`로 자재 납기 초과·CO 승인 대기·미반영 CO·공정 부진을 🔴/🟡 수준으로 확인한다. `get_site_briefing`에도 경고가 자동 포함되므로 아침 브리핑 한 번으로 당일 조치 항목을 파악할 수 있다.
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
