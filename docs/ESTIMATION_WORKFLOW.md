# 견적 단계 워크플로우 (C 페르소나용)

본사 견적 담당자가 일정(공정표) 없이 **예산 데이터만으로** 공종별 합계·BOQ
검토·차기 입찰 단가 보정까지 도달하는 최소 경로입니다. 신규 기능 없이 기존
MCP 도구만 조합해서 사용합니다.

## 가정
- 일정은 아직 확정 전 (`activities` 비어 있어도 OK)
- 한 개 이상의 `실행예산내역서.xlsx` 보유
- `.scheduler` 신규 DB

## 단계

### 1. 빈 프로젝트 생성
```python
create_project(
    name="○○현장 견적",
    start_date="2026-06-01",
    calendar={"calendar_id": "default", "name": "Korean 5-day", "weekmask": "1111100"},
)
```
일정이 없어도 캘린더는 임시로 5일제를 넣어두면 됩니다.

### 2. 실행예산 Excel 가져오기 (dry-run 권장)
```python
import_budget_excel(
    db_path="…/○○현장견적.scheduler",
    excel_path="실행예산내역서(기계설비).xlsx",
    dry_run=True,
)
```
- `dry_run=True`이면 실제 DB에는 쓰지 않고 어떤 카테고리가 잡혔는지 보여 줍니다.
- 결과의 `warnings`/`failed_rows`를 먼저 검토하세요.
- 문제 없으면 `dry_run=False`로 다시 호출해 반영.

### 3. 공종별 합계 즉시 확인
```python
summarize_cost_by_discipline(db_path="…/○○현장견적.scheduler")
```
각 공종(위생/공조/소방/전기/자동제어/공통)별 계약·실행 예산 합계가 JSON으로
반환됩니다. 그대로 엑셀에 붙여넣어 비교표 작성 가능.

### 4. EVM 사전 확인 (선택)
실제 활동(Activity)이 없어 SPI/CPI는 의미 없지만, **PV(계획 누적비)**만이라도
확인하려면:
```python
analyze_evm_from_db(db_path="…/○○현장견적.scheduler", as_of_date="2026-06-01")
```
모두 0이 나오면 정상 — "EVM 데이터가 부족합니다" 친절 메시지가 나옵니다.

### 5. 차기 입찰 단가 보정 (반복 사용)
유사한 과거 견적 DB가 있으면 `summarize_cost_by_discipline`을 양쪽 다 돌려
공종별 비율 변화를 단순 비교. 별도 코드 변경 없이 엑셀에서 처리.

## 자주 묻는 질문

**Q. 활동(Activity)이 없는데 EVM이 돌아가나요?**
→ 그래도 오류는 안 납니다. `analyze_evm_from_db`가 빈 데이터에 대해
"데이터 부족" 응답을 줍니다.

**Q. 추정 공기를 같이 보고 싶어요.**
→ 견적 후 일정이 확정되면 그때 `import_schedule_excel`로 공정표를 임포트하면
같은 DB가 일정+예산을 모두 갖습니다. 즉, 견적 DB가 그대로 시공 DB로 승격됩니다.

**Q. dry-run 결과를 어떻게 저장하나요?**
→ `import_budget_excel`이 반환하는 JSON을 그대로 보관하면 됩니다. 별도 저장
기능은 없지만 JSON은 그대로 첨부/검토 가능합니다.
