# Smart Scheduler v2.3 — 토공사 생산성 기반 자동 산정 (커밋 패키지)

홍은동 355번지 토공사 실데이터(발주내역·공정표·지하안전평가서)로 검증한
"BOQ → WBS·코스트 → 생산성 공기 → CPM·Critical Path → Gantt" 자동화 모듈.

## 구조
```
core/earthwork_estimator.py      # 수량+지층+장비 -> 공기 산출 (기능1/2)
tools/boq_wbs_parser.py          # BOQ 점-깊이 WBS 파서 + 코스트 로딩 + 지층 태깅 + 공기
tools/boq_sequencer.py           # 관계형 CPM(FS/SS/FF+lag) + 일정/Gantt 데이터
presets/earthwork_productivity.json   # 지층·공법·설치 생산성 원단위(현장/이론/보정계수)
presets/excavation_stage_model.json   # 단계별 굴착 모델(안전평가서 표5.23)
scripts/make_gantt.py            # Gantt PNG 렌더(Noto Sans CJK)
tests/test_earthwork.py          # 단위+통합 18 케이스
samples/                         # 발주내역 원본 + 자동생성 산출물(CSV/Gantt)
docs/V2.3_DEVELOPMENT_PLAN.md     # 기능1·2·5 + Open Items
```

## 실행
```bash
python -m pytest -q                 # 18 passed
python core/earthwork_estimator.py  # 단계별 굴착 공기 + 장비 what-if
python tools/boq_wbs_parser.py samples/발주내역__17_.xlsx --prod presets/earthwork_productivity.json --csv out.csv
python tools/boq_sequencer.py 242   # CPM (암반 242일=7대 가정; 390=5대 what-if)
python scripts/make_gantt.py        # samples/홍은동_CPM_gantt.png
```

## 검증된 결과 (홍은동)
- BOQ 144 Activity, 코스트 롤업 정확히 **7,000,000,000원**
- 암반 보정계수 **0.15** (이론 연암 200 → 현장 미진동 30 m³/대)
- 중첩 모델링 후 총 공기 **376 WD(≈17.9개월)**, 암반 굴착 완료 **2027-08** → 공정표 종료와 일치
- Critical Path: A1→A4→A5→A6→A9→A10→A11 (암반 굴착 long pole)

## 통합 시 조정 필요 (repo 정합)
- `core.cpm`(pyCritical)·한국 캘린더로 본 참조 CPM 교체 시 공휴일 반영
- `presets` 로더 스키마에 JSON 필드명 정렬
- `installation` 원단위는 needs_calibration=true (현장 실적 보정 전 템플릿)
- 잔여 gap(되메우기·성토 tail ~2개월)은 구조물 공정과의 중첩 모델링으로 해소

## core.cpm(pyCritical) 와이어링 — 검증 완료

`tools/cpm_adapter.py` 가 참조 네트워크를 repo `core.models.Activity`/`Relationship` 로
변환하고 실제 `core.cpm.run_cpm`(pyCritical)으로 실행한다.

- repo 엔진 vs 참조 CPM: **ES/EF·Critical Path·총 공기(376 WD) 완전 일치** 확인.
- 차이는 비임계 공종 A2의 여유(repo 29 / 참조 18) 한 곳뿐 — SS 관계 float 계산 관례
  차이이며, repo 채택 엔진인 pyCritical 값이 권위값.
- 실행: `PYTHONPATH=<repo>:<tools> python tools/cpm_adapter.py 242`
- 테스트: `test_repo_pycritical_schedule_matches_reference` (repo/pyCritical 없으면 자동 skip)

### 통합 시 남은 1건
- 참조 시퀀서의 외부 마일스톤(`fixed_es`, 구조물 완료 게이트)은 pyCritical 순수 선후행
  모델로 표현 불가. repo에 '제약일(constraint date)' 확장 또는 구조물 마일스톤을
  선행 Activity 로 모델링하면 해소.
