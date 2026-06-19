"""
tests/test_earthwork.py

토공사 생산성/파서/CPM 참조 구현 단위·통합 테스트.
실행: python -m pytest tests/test_earthwork.py -q
"""

import json
import math
from datetime import date
from pathlib import Path

import pytest

from core import earthwork_estimator as est
from tools import boq_wbs_parser as parser
from tools import boq_sequencer as seq

ROOT = Path(__file__).resolve().parents[1]
# v3.4: presets는 infrastructure/presets/로 이동
PROD = ROOT / "infrastructure" / "presets" / "earthwork_productivity.json"
STAGE = ROOT / "infrastructure" / "presets" / "excavation_stage_model.json"
BOQ = ROOT / "samples" / "발주내역__17_.xlsx"


# ---------- earthwork_estimator ----------

def test_estimate_days_ceil():
    # 1000 / (300*1) = 3.33 -> 올림 4
    assert est.estimate_activity_days(1000, 300, 1) == 4


def test_estimate_days_fleet_scaling():
    one = est.estimate_activity_days(1400, 200, 1)
    seven = est.estimate_activity_days(1400, 200, 7)
    assert seven < one
    assert seven == math.ceil(1400 / (200 * 7))


@pytest.mark.parametrize("rate,fleet", [(0, 1), (200, 0), (-1, 1)])
def test_estimate_days_invalid(rate, fleet):
    with pytest.raises(ValueError):
        est.estimate_activity_days(100, rate, fleet)


def test_rock_calibration_factor_present():
    prod = json.load(open(PROD, encoding="utf-8"))
    rock = next(e for e in prod["excavation"] if e["layer"] == "연암")
    # 현장 미진동 원단위가 이론치보다 크게 낮아야 함(보정계수 < 0.3)
    assert rock["calibration_factor"] is not None
    assert rock["calibration_factor"] < 0.3


def test_stage_depth_sums_to_max():
    stage = json.load(open(STAGE, encoding="utf-8"))
    total = sum(s["depth_m"] for s in stage["stages"])
    assert total == pytest.approx(stage["site"]["max_excavation_depth_m"], abs=0.01)


# ---------- boq_wbs_parser (통합: 실제 BOQ) ----------

@pytest.fixture(scope="module")
def acts():
    a = parser.parse_boq(BOQ)
    parser.attach_durations(a, json.load(open(PROD, encoding="utf-8")))
    return a


def test_boq_cost_rollup_exact(acts):
    leaves = [a for a in acts if a["is_leaf"]]
    total = sum(a["exec_cost"] for a in leaves)
    assert total == pytest.approx(7_000_000_000, abs=1)


def test_boq_wbs_codes_well_formed(acts):
    for a in acts:
        # 코드는 점 구분 정수, 깊이와 토큰 수 일치
        tokens = a["wbs_code"].split(".")
        assert all(t.isdigit() for t in tokens)
        assert len(tokens) == a["depth"]


def test_boq_layer_tagging(acts):
    tagged = {a["layer"] for a in acts if a["layer"]}
    assert "기반암(미진동발파)" in tagged
    assert "풍화토" in tagged


def test_boq_rock_excavation_has_duration(acts):
    rock = [a for a in acts if a["is_leaf"] and "터파기" in a["name"]
            and a["layer"] and "기반암" in a["layer"]]
    assert rock, "암반 터파기 항목이 있어야 함"
    assert all(a.get("est_days") and a["est_days"] > 0 for a in rock)


# ---------- boq_sequencer (CPM) ----------

@pytest.fixture
def cpm_tasks():
    return seq.run_cpm(seq.build_earthwork_network(rock_days=242))


def test_cpm_critical_path_zero_float(cpm_tasks):
    for t in cpm_tasks:
        if t.critical:
            assert t.tf == 0


def test_cpm_forward_backward_consistency(cpm_tasks):
    project_end = max(t.ef for t in cpm_tasks)
    # 임계공정 종료가 프로젝트 종료와 일치
    assert max(t.lf for t in cpm_tasks) == project_end
    for t in cpm_tasks:
        assert t.ef == t.es + t.duration
        assert t.tf >= 0


def test_cpm_rock_is_critical(cpm_tasks):
    a9 = next(t for t in cpm_tasks if t.id == "A9")
    assert a9.critical, "암반 굴착이 임계공정이어야 함"


def test_cpm_rock_whatif_extends_schedule():
    short = max(t.ef for t in seq.run_cpm(seq.build_earthwork_network(242)))
    long = max(t.ef for t in seq.run_cpm(seq.build_earthwork_network(390)))
    assert long > short
    assert long - short == 390 - 242


def test_calendar_skips_weekends(cpm_tasks):
    cal = seq.add_calendar(cpm_tasks, date(2026, 5, 1))
    for s, e in cal.values():
        assert s.weekday() < 5  # 월~금


# ---------- 일반화 CPM 관계유형(FS/SS/FF) 직접 검증 ----------

def test_relationship_types_fs_ss_ff():
    tasks = [
        seq.Task("X", "x", 10, []),
        seq.Task("FS", "fs", 5, [("X", "FS", 2)]),   # es = 10+2 = 12
        seq.Task("SS", "ss", 5, [("X", "SS", 3)]),   # es = 0+3 = 3
        seq.Task("FF", "ff", 4, [("X", "FF", 1)]),   # ef = 10+1=11 -> es = 7
    ]
    seq.run_cpm(tasks)
    by = {t.id: t for t in tasks}
    assert by["FS"].es == 12
    assert by["SS"].es == 3
    assert by["FF"].es == 7
    assert by["FF"].ef == 11


def test_ss_overlap_shortens_vs_serial():
    serial = [seq.Task("P", "p", 20, []), seq.Task("Q", "q", 20, [("P", "FS", 0)])]
    overlap = [seq.Task("P", "p", 20, []), seq.Task("Q", "q", 20, [("P", "SS", 5)])]
    end_serial = max(t.ef for t in seq.run_cpm(serial))
    end_overlap = max(t.ef for t in seq.run_cpm(overlap))
    assert end_overlap < end_serial
    assert end_overlap == 25  # SS+5 -> Q es=5, ef=25


# ---------- 단계 분리 / 외부 마일스톤 ----------

def test_core_phase_completion_matches_field():
    tasks = seq.run_cpm(seq.build_earthwork_network(rock_days=242))
    core_end = max(t.ef for t in tasks if t.phase == "토공사")
    # 토공사 본공정 완료 ~16개월(공정표 수준): 320~360 WD 범위
    assert 320 <= core_end <= 360


def test_structure_dependent_phase_tagged():
    tasks = seq.build_earthwork_network(rock_days=242)
    dep = {t.id for t in tasks if t.phase == "구조물의존"}
    assert {"A11", "A12"} <= dep


def test_external_milestone_gates_backfill():
    tasks = seq.run_cpm(seq.build_earthwork_network(rock_days=242, structure_done_day=500))
    by = {t.id: t for t in tasks}
    assert "MSTR" in by
    # 되메우기는 구조물 완료(500) 이후 시작
    assert by["A11"].es >= 500


# ---------- repo core.cpm(pyCritical) 와이어링 (repo 가용 시에만) ----------

def test_repo_pycritical_schedule_matches_reference():
    pytest.importorskip("core.cpm", reason="repo core.cpm/pyCritical 미설치 환경 -> skip")
    from tools import cpm_adapter
    net = seq.build_earthwork_network(rock_days=242)
    repo_result = cpm_adapter.run_via_repo(net)
    repo_by = {a.activity_id: a for a in repo_result.activities}
    ref_by = {t.id: t for t in seq.run_cpm(seq.build_earthwork_network(242))}
    # ES/EF/임계공정은 엔진 간 완전 일치(여유는 관례차 허용)
    for tid, f in ref_by.items():
        r = repo_by[tid]
        assert (r.es_workday, r.ef_workday, r.is_critical) == (f.es, f.ef, f.critical)
    assert repo_result.total_duration_days == max(t.ef for t in ref_by.values())


# ---------- 지연감지·회복안 검증 (repo 모듈 가용 시) ----------

def _load_events():
    ROOT = Path(__file__).resolve().parents[1]
    return json.load(open(ROOT / "samples" / "daily_records_events.json", encoding="utf-8"))["events"]


def test_event3_blasting_fires_critical_delay():
    dd = pytest.importorskip("core.delay_detection", reason="repo 모듈 미설치 -> skip")
    from core.progress import calculate_quantity_progress
    ev = next(e for e in _load_events() if e["event"] == "③")
    act = dict(ev["activity"])
    recs = ev["daily_records"]
    act["actual_progress_pct"] = calculate_quantity_progress(
        sum(r["planned_qty"] for r in recs), sum(r["actual_qty"] for r in recs))
    issues = dd.generate_delay_report([act])
    codes = {i["reason_code"] for i in issues}
    assert "schedule_progress_delay" in codes
    assert any(i["severity"] == "critical" for i in issues)


def test_event4_winter_fires_inspection_and_weather_recovery():
    dd = pytest.importorskip("core.delay_detection", reason="repo 모듈 미설치 -> skip")
    rec = pytest.importorskip("core.recovery")
    from core.progress import calculate_quantity_progress
    ev = next(e for e in _load_events() if e["event"] == "④")
    act = dict(ev["activity"])
    recs = ev["daily_records"]
    act["actual_progress_pct"] = calculate_quantity_progress(
        sum(r["planned_qty"] for r in recs), sum(r["actual_qty"] for r in recs))
    issues = dd.generate_delay_report([act], today=date(2027, 1, 16))
    assert "inspection_delay" in {i["reason_code"] for i in issues}
    plans = rec.suggest_recovery_plans("weather_delay")
    assert any(p["reason_label_ko"] == "날씨 영향" for p in plans)


def test_event2_instrumentation_has_no_dedicated_template():
    rec = pytest.importorskip("core.recovery", reason="repo 모듈 미설치 -> skip")
    # 계측 경보 전용 회복 템플릿 부재 -> 일반 협의 폴백 (확인된 갭)
    plans = rec.suggest_recovery_plans("instrumentation_alert")
    assert all(p["reason_label_ko"] == "일반 지연" for p in plans)
