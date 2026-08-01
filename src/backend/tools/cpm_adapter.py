"""
tools/cpm_adapter.py

참조 시퀀서(boq_sequencer)의 토공사 네트워크를 repo의 core.models.Activity /
Relationship 으로 변환하고, 실제 core.cpm.run_cpm(pyCritical)으로 실행한다.
이로써 참조 CPM을 repo 엔진으로 교체(와이어링)한다.

전제: PYTHONPATH 에 repo 루트 포함(=core 패키지 import 가능),
      그리고 boq_sequencer 가 import 가능해야 한다.

주의: 참조 시퀀서의 외부 마일스톤(fixed_es)은 pyCritical 순수 선후행 모델로는
표현 불가 -> 해당 기능이 필요한 경우 repo에 '제약일(constraint date)' 확장 필요.
fixed_es 가 설정된 Task 는 변환 시 경고하고 선후행만 반영한다.
"""

from __future__ import annotations

from core.models import Activity, Relationship  # repo
from core.cpm import run_cpm as repo_run_cpm    # repo (pyCritical)


def to_repo_objects(tasks, discipline: str = "토목", wbs_id: str = "WBS-EARTH"):
    """참조 Task 리스트 -> (Activity[], Relationship[])."""
    activities, relationships = [], []
    rid = 0
    for t in tasks:
        if getattr(t, "fixed_es", None) is not None:
            print(f"[warn] {t.id} fixed_es={t.fixed_es} -> pyCritical 미지원, 선후행만 반영")
        activities.append(Activity(
            activity_id=t.id,
            code=t.id,
            name=t.name,
            wbs_id=wbs_id,
            discipline=discipline,
            zone="",
            duration=t.duration,
            cost=0.0,
        ))
        for pred, rtype, lag in t.rels:
            rid += 1
            relationships.append(Relationship(
                rel_id=f"R{rid:03d}",
                pred_id=pred,
                succ_id=t.id,
                rel_type=rtype,
                lag_days=lag,
            ))
    return activities, relationships


def run_via_repo(tasks):
    """repo의 core.cpm.run_cpm 실행 -> CpmResult."""
    activities, relationships = to_repo_objects(tasks)
    return repo_run_cpm(activities, relationships)


if __name__ == "__main__":
    import sys
    try:
        from tools.boq_sequencer import build_earthwork_network, run_cpm as ref_run_cpm
    except ImportError:
        from boq_sequencer import build_earthwork_network, run_cpm as ref_run_cpm

    rock = int(sys.argv[1]) if len(sys.argv) > 1 else 242

    # 1) repo 엔진(pyCritical)
    net = build_earthwork_network(rock_days=rock)  # 외부 마일스톤 없는 기본망
    repo_result = run_via_repo(net)
    repo_by = {a.activity_id: a for a in repo_result.activities}

    # 2) 참조 엔진
    ref = ref_run_cpm(build_earthwork_network(rock_days=rock))
    ref_by = {t.id: t for t in ref}

    print(f"\n{'ID':4} {'repo(ES/EF/TF/CP)':>22}   {'ref(ES/EF/TF/CP)':>22}   일치")
    sched_match = True  # ES/EF/임계 일치 여부(여유 관례차 제외)
    for tid in ref_by:
        r, f = repo_by[tid], ref_by[tid]
        sm = (r.es_workday == f.es and r.ef_workday == f.ef and r.is_critical == f.critical)
        sched_match &= sm
        print(f"{tid:4} {r.es_workday:>4}/{r.ef_workday:>4}/{r.total_float:>4}/"
              f"{'CP' if r.is_critical else '--':>2}   "
              f"{f.es:>4}/{f.ef:>4}/{f.tf:>4}/{'CP' if f.critical else '--':>2}   "
              f"{'OK' if sm else 'DIFF'}")
    print(f"\n총 공기 repo={repo_result.total_duration_days} / ref={max(t.ef for t in ref)}")
    print(f"임계공정 수 repo={repo_result.critical_count}")
    print(">>> 일정(ES/EF/임계) 일치:", sched_match)
    print("   (비임계 여유는 pyCritical 관례를 권위값으로 채택)")
