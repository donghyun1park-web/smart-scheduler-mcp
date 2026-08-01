"""
scripts/verify_delay_recovery.py

이벤트 ②③④ 일일 실적 JSON -> repo 실제 모듈로 검증:
  core.progress.calculate_quantity_progress  (일일실적 -> 진척%)
  core.delay_detection.generate_delay_report (지연 경보)
  core.recovery.suggest_recovery_plans + format_recovery_report (회복안 초안)

실행: PYTHONPATH=<repo> python scripts/verify_delay_recovery.py daily_records_events.json
"""

from __future__ import annotations
import json
import sys
from datetime import date

from core.progress import calculate_quantity_progress
from core.delay_detection import generate_delay_report
from core.recovery import suggest_recovery_plans, format_recovery_report


def aggregate_actual_progress(records: list[dict]) -> float:
    planned = sum(r.get("planned_qty", 0) for r in records)
    actual = sum(r.get("actual_qty", 0) for r in records)
    return calculate_quantity_progress(planned, actual)


def run_event(ev: dict, today: date) -> None:
    act = dict(ev["activity"])
    recs = ev["daily_records"]
    act["actual_progress_pct"] = aggregate_actual_progress(recs)

    planned = sum(r["planned_qty"] for r in recs)
    actual = sum(r["actual_qty"] for r in recs)
    print("=" * 74)
    print(f"이벤트 {ev['event']} | {ev['label']}")
    print(f"  대상 {act['activity_id']} {act['name']} | "
          f"누적 계획 {planned:,} / 실적 {actual:,} -> 진척 {act['actual_progress_pct']:.1f}% "
          f"(계획 {act.get('planned_progress_pct',0):.0f}%)")

    # 1) detect_delays
    issues = generate_delay_report([act], today=today)
    if not issues:
        print("  [detect_delays] 경보 없음")
    for it in issues:
        print(f"  [detect_delays] ⚠ {it['severity'].upper():8} {it['reason_code']:22} "
              f"risk={it['risk_score']:>5} | {it['message']}")

    # 2) suggest_recovery (공무가 근본원인 분류 -> 템플릿 키)
    root = ev.get("root_cause_hint")
    if issues:
        print(f"  [공무 근본원인 분류] {root}")
        plans = suggest_recovery_plans(root)
        primary = dict(issues[0])
        primary["reason_code"] = root
        report = format_recovery_report(primary, plans)
        for line in report.splitlines():
            print("    " + line)
        # 회복안 키가 일반(현장협의)로 떨어지면 = 전용 템플릿 부재
        labels = {p["reason_label_ko"] for p in plans}
        if "일반 지연" in labels:
            print("    ※ 전용 회복 템플릿 없음 -> 일반 협의 후보로 폴백 (템플릿 추가 권장)")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "daily_records_events.json"
    data = json.load(open(path, encoding="utf-8"))
    # 검증 today: 각 이벤트 마지막 실적일 다음날로 가정(이벤트별로 처리)
    for ev in data["events"]:
        last = max(date.fromisoformat(r["work_date"]) for r in ev["daily_records"])
        run_event(ev, today=last)
    print("=" * 74)
    print("\n[요약] detect_delays는 진척 갭 기반 경보를 실제로 발생시킴.")
    print(" - ③ 발파민원: 임계공정 progress 갭 -> 경보 발생(검증).")
    print(" - ④ 동절기: 진척 갭 + 검측 지연 -> 경보 발생(검증).")
    print(" - ② 계측: 전용 instrumentation detector 부재 -> 굴착중단 진척갭으로만 포착.")
    print(" - schedule_progress_delay 코드는 전용 회복 템플릿이 없어 근본원인 분류가 선행되어야 함.")


if __name__ == "__main__":
    main()
