# AI Usage Guide v2.5 — Operations Center

## 목적

v2.5 운영센터는 현장 사용자가 “지금 무엇부터 확인해야 하는지”를 빠르게 판단하도록 돕는 읽기 전용 진단 레이어다. DB 원본을 자동 변경하지 않으며, AI와 MCP 도구는 후보와 점검 순서를 제안한다.

## 기본 순서

1. `check_data_health`로 데이터 건강점수, 오류 수, 주의 수, 원인 메시지를 확인한다.
2. `suggest_next_actions`로 사용자 역할에 맞는 다음 행동 후보를 받는다.
3. `get_workflow_status`로 일일마감과 주간보고 사전점검 상태를 본다.
4. `explain_evm_from_db`로 PV/EV/AC, SPI/CPI를 쉬운 한국어 설명으로 변환한다.
5. 필요하면 기존 도구인 `get_site_briefing`, `generate_weekly_report_from_db`, `summarize_cost_by_discipline`로 상세 산출물을 만든다.

## 역할별 사용

| 역할 | 권장 시작 도구 | 확인 포인트 |
|---|---|---|
| 공무 | `check_data_health` | 공정표, 실행예산, 일보, 자재/검측 데이터 누락 |
| 현장소장 | `suggest_next_actions(profile="site_manager")` | 오늘 조치할 위험, 보고서 생성 준비 상태 |
| 본사/관리 | `explain_evm_from_db` | SPI/CPI, 원가 과투입, 기성 차이 |
| 관리자/개발자 | `get_workflow_status` | MCP 등록, smoke test, 데이터 상태 회귀 |

## 안전 원칙

- 운영센터는 조회와 설명이 기본이며 DB를 직접 수정하지 않는다.
- `suggest_next_actions` 결과는 다음 행동 후보이며 작업 지시는 아니다.
- 만회대책과 AI 문구는 “초안”, “후보”, “검토 필요” 표현을 사용한다.
- 실제 현장 DB에는 원본이 아니라 복사본으로 smoke test를 먼저 실행한다.
- 인증, 권한관리, 모바일 알림, 실시간 모니터링은 v2.5 범위가 아니며 후속 버전 후보로 둔다.

## Streamlit 실행

```powershell
.\.venv\Scripts\python.exe -m streamlit run viewer\pages\00_operations_center.py
```

사이드바에 `.scheduler` DB 경로, 기준일, 사용자 역할을 입력하면 건강점수, 추천 행동, EVM 설명, 워크플로우 상태를 한 화면에서 확인할 수 있다.
