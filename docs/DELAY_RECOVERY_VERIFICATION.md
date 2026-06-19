# 지연 감지·회복안 검증 (이벤트 ②③④)

`samples/daily_records_events.json` 의 일일 실적을 repo 실제 모듈
(`core.progress` · `core.delay_detection` · `core.recovery`)로 돌린 결과.

## 검증 결과 (실측)

| 이벤트 | 대상 | 진척 | detect_delays | suggest_recovery |
|---|---|---|---|---|
| ② 계측 경보 | A5 1단굴착 | 54.4% | CRITICAL `schedule_progress_delay` (gap 45.6%) | `instrumentation_alert` → **전용 템플릿 없음**, 일반 협의 폴백 |
| ③ 발파 민원 | A9 암반굴착 | 72.5% | CRITICAL `schedule_progress_delay` (gap 27.5%) | `equipment_delay` → 장비 투입 재조정 후보 ✓ |
| ④ 동절기·지하수 | A8 숏크리트 | 49.3% | CRITICAL `schedule_progress_delay` + WARNING `inspection_delay` | `weather_delay` → 날씨 민감 공정 재배치 후보 ✓ |

## 결론
- detect_delays는 일일 실적 진척 갭 기반으로 경보를 **실제 발생**시킨다(③④ 정상, ④는 검측 detector도 동시 발화).
- suggest_recovery는 근본원인 코드(equipment/weather 등)에 대해 전용 회복 초안을 정상 반환한다(확정 표현 없는 draft).

## 발견된 통합 갭 (개선 권고)
1. **계측(instrumentation) detector 부재**: ②(지중경사계 변위)는 굴착 중단에 따른 진척 갭으로만 간접 포착. → `detect_instrumentation_alert` 추가 권장(관리기준 초과 직접 경보).
2. **detector 코드 ↔ 회복 템플릿 키 분리**: detect_delays는 `schedule_progress_delay`만 내고, 회복 템플릿은 근본원인 코드(equipment/weather/...)로 키잉됨. 공무의 근본원인 분류가 선행돼야 전용 회복안이 나온다. → 분류 보조 또는 매핑 레이어 권장.
3. **민원/규제 사유 템플릿 부재**: 발파 민원은 equipment_delay로 우회 분류. → `regulation_delay`(민원·인허가) 템플릿 추가 권장.

실행: `PYTHONPATH=<repo> python scripts/verify_delay_recovery.py samples/daily_records_events.json`
