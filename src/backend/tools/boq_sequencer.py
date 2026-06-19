"""
tools/boq_sequencer.py  (참조 구현 / reference) — v2: FS/SS/FF + lag 중첩 지원

파서 산출 Activity -> 공종(sub-work) 집계 -> 관계형 선후행(FS/SS/FF+lag)
-> 일반화 CPM -> ES/EF/LS/LF/TF, Critical Path -> 일정/Gantt.

선후행/중첩은 홍은동 토공사 예정공정표의 실제 시공순서(굴착↔버팀보 인터리브,
차수·복공 병행)를 근거로 한다. duration_source 로 공기 출처를 명시한다.
repo의 core.cpm(pyCritical)로 대체 가능.
"""

from __future__ import annotations
import csv
from dataclasses import dataclass, field
from datetime import date, timedelta

# 관계: (pred_id, type, lag)  type in {FS, SS, FF}
Rel = tuple[str, str, int]


@dataclass
class Task:
    id: str
    name: str
    duration: int
    rels: list[Rel] = field(default_factory=list)
    dur_source: str = ""
    phase: str = "토공사"
    fixed_es: int | None = None  # 외부 마일스톤 등 강제 시작일
    es: int = 0
    ef: int = 0
    ls: int = 0
    lf: int = 0
    tf: int = 0
    critical: bool = False


def build_earthwork_network(rock_days: int = 242,
                            structure_done_day: int | None = None) -> list[Task]:
    """
    홍은동 공정표 순서 + 흙막이 표준 중첩.
    되메우기·성토·가시설 철거는 '구조물 의존' 별도 단계로 분리한다(측벽 되메우기는
    지하 골조 완성 후 진행). structure_done_day 가 주어지면 그 마일스톤에 FS로 물린다.
    """
    net = [
        Task("A1", "C.I.P+H-PILE 천공",   61, [],                          "공정표(61일)"),
        Task("A2", "차수 ADG 그라우팅",    18, [("A1", "SS", 30)],          "공정표(18일)"),
        Task("A3", "POST-PILE",            12, [("A1", "SS", 40)],          "공정표(12일)"),
        Task("A4", "복공판 설치",          14, [("A1", "FS", 0)],           "원단위(1,045/80)"),
        Task("A5", "1단 굴착(풍화토)",     30, [("A2", "FS", 0), ("A4", "SS", 5)], "공정표(30일)"),
        Task("A6", "띠장·버팀보/TLS 설치", 30, [("A5", "SS", 10)],          "원단위/공정표"),
        Task("A7", "어스앵커(1,2단)",      11, [("A5", "SS", 15)],          "공정표(11일)"),
        Task("A8", "숏크리트",             11, [("A9", "SS", 20)],          "원단위(3,152/300)"),
        Task("A9", "암반 굴착(미진동+할암)", rock_days, [("A6", "SS", 15)],  "파서 bottom-up(7대)"),
        Task("A10", "바닥면 고르기",        9, [("A9", "FS", 0)],           "원단위(4,841/600)"),
    ]
    # --- 구조물 의존 단계(토공사 본공정 임계경로 밖) ---
    gate: list[Rel] = [("MSTR", "FS", 0)] if structure_done_day is not None else [("A10", "FS", 0)]
    if structure_done_day is not None:
        net.append(Task("MSTR", "구조물 완료(외부 마일스톤)", 0, [], "외부 입력",
                        phase="마일스톤", fixed_es=structure_done_day))
    net += [
        Task("A11", "되메우기·성토", 34, gate, "원단위(5,083+5,649)", phase="구조물의존"),
        Task("A12", "잔여 가시설 철거", 13, [("A11", "SS", 10)], "파서/BOQ(13일)", phase="구조물의존"),
    ]
    return net


def _topo(tasks: list[Task]) -> list[Task]:
    by_id = {t.id: t for t in tasks}
    order, seen = [], set()

    def visit(t):
        if t.id in seen:
            return
        for p, _, _ in t.rels:
            visit(by_id[p])
        seen.add(t.id)
        order.append(t)

    for t in tasks:
        visit(t)
    return order


def run_cpm(tasks: list[Task]) -> list[Task]:
    by_id = {t.id: t for t in tasks}
    order = _topo(tasks)

    # Forward pass (FS/SS/FF + lag)
    for t in order:
        cands = [0]
        for p, rt, lag in t.rels:
            pr = by_id[p]
            if rt == "FS":
                cands.append(pr.ef + lag)
            elif rt == "SS":
                cands.append(pr.es + lag)
            elif rt == "FF":
                cands.append(pr.ef + lag - t.duration)
        if t.fixed_es is not None:
            cands.append(t.fixed_es)
        t.es = max(cands)
        t.ef = t.es + t.duration
    project_end = max(t.ef for t in tasks)

    # 후행 관계 인덱스
    succ: dict[str, list[Rel]] = {t.id: [] for t in tasks}
    for t in tasks:
        for p, rt, lag in t.rels:
            succ[p].append((t.id, rt, lag))

    # Backward pass
    for t in reversed(order):
        cands = [project_end]
        for s_id, rt, lag in succ[t.id]:
            s = by_id[s_id]
            if rt == "FS":
                cands.append(s.ls - lag)
            elif rt == "SS":
                cands.append(s.ls - lag + t.duration)
            elif rt == "FF":
                cands.append(s.lf - lag)
        t.lf = min(cands)
        t.ls = t.lf - t.duration
        t.tf = t.ls - t.es
        t.critical = (t.tf == 0)
    return tasks


def add_calendar(tasks: list[Task], start: date) -> dict[str, tuple[date, date]]:
    def wd(offset: int) -> date:
        d, n = start, 0
        while n < offset:
            d += timedelta(days=1)
            if d.weekday() < 5:
                n += 1
        return d
    return {t.id: (wd(t.es), wd(t.ef)) for t in tasks}


def export_csv(tasks, cal, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "duration", "rels", "ES", "EF", "LS", "LF",
                    "TF", "critical", "start_date", "finish_date", "dur_source"])
        for t in tasks:
            s, e = cal[t.id]
            rels = ";".join(f"{p}-{rt}+{lg}" for p, rt, lg in t.rels)
            w.writerow([t.id, t.name, t.duration, rels, t.es, t.ef, t.ls, t.lf,
                        t.tf, "CP" if t.critical else "", s.isoformat(),
                        e.isoformat(), t.dur_source])


if __name__ == "__main__":
    import sys
    rock = int(sys.argv[1]) if len(sys.argv) > 1 else 242
    tasks = run_cpm(build_earthwork_network(rock_days=rock))
    cal = add_calendar(tasks, date(2026, 5, 1))
    core_tasks = [t for t in tasks if t.phase == "토공사"]
    core_end = max(t.ef for t in core_tasks)
    project_end = max(t.ef for t in tasks)
    cp = [t.id for t in tasks if t.critical]

    print(f"토공사 본공정 완료: {core_end} WD (≈{core_end/21.0:.1f}개월)  "
          f"-> {add_calendar(tasks, date(2026,5,1))[max(core_tasks, key=lambda t:t.ef).id][1]}")
    print(f"(되메우기·철거 포함) 전체: {project_end} WD (≈{project_end/21.0:.1f}개월)")
    print(f"Critical Path: {' -> '.join(cp)}\n")
    print(f"{'ID':3} {'공종':20} {'공기':>4} {'시작':>11} {'종료':>11} {'TF':>4} {'CP':>3} 출처")
    for t in tasks:
        s, e = cal[t.id]
        print(f"{t.id:3} {t.name:20} {t.duration:>4} {s.isoformat():>11} "
              f"{e.isoformat():>11} {t.tf:>4} {'★' if t.critical else '':>3} {t.dur_source}")
    export_csv(tasks, cal, "/mnt/user-data/outputs/홍은동_CPM_schedule.csv")
    print("\nCSV 저장: 홍은동_CPM_schedule.csv")
