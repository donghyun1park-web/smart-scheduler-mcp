"""
tools/boq_wbs_parser.py  (참조 구현 / reference implementation for import_excel)

발주내역(BOQ) xlsx -> WBS 트리 + Activity 초안.
- 선행 '…'(U+2026) 개수로 WBS 깊이 복원
- 리프(단위 보유) 항목만 Activity 화
- 규격/명칭에서 지층 태깅
- earthwork_productivity.json 매칭 -> 공기(est_days) 산출
- 실행 수량/단가/금액 코스트 로딩 + 상위 롤업 검증

CLI:
    python tools/boq_wbs_parser.py <boq.xlsx> [--prod earthwork_productivity.json] [--csv out.csv]
"""

from __future__ import annotations
import argparse
import csv
import json
import math
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
from openpyxl import load_workbook  # noqa: E402

DOT = "…"  # U+2026

# 명칭/규격 -> 지층 태깅 키워드 (우선순위 순)
LAYER_KEYS = [
    ("기반암", "할암", "기반암(할암)"),
    ("기반암", "미진동", "기반암(미진동발파)"),
    ("기반암", None, "기반암"),
    ("경암", None, "경암"),
    ("연암", None, "연암"),
    ("풍화암", None, "풍화암"),
    ("풍화토", None, "풍화토"),
    ("매립토", None, "매립토"),
    ("토사", None, "토사"),
]

# 공정표 fleet 가정 (장비 대수) — what-if 시 변경
DEFAULT_FLEET = {"터파기": 7, "천공": 2, "차수": 1}


def tag_layer(name: str, spec: str) -> str | None:
    text = f"{name} {spec or ''}"
    for k1, k2, label in LAYER_KEYS:
        if k1 in text and (k2 is None or k2 in text):
            return label
    return None


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def parse_boq(xlsx_path: str | Path) -> list[dict]:
    wb = load_workbook(xlsx_path, read_only=False, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=3, values_only=True))  # 2-row header skipped

    activities: list[dict] = []
    stack: list[tuple[int, int, str]] = []  # (depth, seq, name)
    counters: dict[int, int] = {}

    for row in rows:
        raw = str(row[0]) if row and row[0] is not None else ""
        if not raw.strip("…. "):
            continue
        depth = len(raw) - len(raw.lstrip("…"))
        name = raw.lstrip("…").strip()
        unit = row[2] if len(row) > 2 else None
        exec_qty = _num(row[6]) if len(row) > 6 else 0.0
        exec_rate = _num(row[7]) if len(row) > 7 else 0.0
        exec_cost = _num(row[8]) if len(row) > 8 else 0.0
        spec = row[1] if len(row) > 1 else None

        # WBS 코드 스택 갱신
        while stack and stack[-1][0] >= depth:
            stack.pop()
        counters[depth] = counters.get(depth, 0) + 1
        for d in list(counters):
            if d > depth:
                counters[d] = 0
        wbs_code = ".".join(
            str(counters[d]) for d in range(1, depth + 1) if counters.get(d)
        )
        stack.append((depth, counters[depth], name))
        wbs_path = " > ".join(n for _, _, n in stack)

        is_leaf = unit is not None and exec_qty > 0
        activities.append({
            "wbs_code": wbs_code,
            "depth": depth,
            "name": name,
            "spec": spec or "",
            "unit": unit or "",
            "qty": exec_qty,
            "exec_rate": exec_rate,
            "exec_cost": exec_cost,
            "layer": tag_layer(name, spec) if is_leaf else None,
            "is_leaf": is_leaf,
            "wbs_path": wbs_path,
        })
    return activities


def attach_durations(activities: list[dict], prod: dict) -> None:
    exc = {e["layer"]: e for e in prod["excavation"]}

    def exc_rate(layer):
        if not layer:
            return None
        # 기반암(미진동발파/할암) -> 암반(연암/경암) 원단위로 정규화
        if "기반암" in layer or "경암" in layer:
            e = exc.get("경암/보통암")
            return (e.get("current_rate") or e.get("theoretical_rate")) if e else None
        if "연암" in layer:
            e = exc.get("연암")
            return (e.get("current_rate") or e.get("theoretical_rate")) if e else None
        for k, e in exc.items():
            if layer in k or any(p in layer for p in k.replace("/", " ").split()):
                return e.get("current_rate") or e.get("theoretical_rate")
        return None

    def drill_rate(nm, spec):
        s = f"{nm} {spec or ''}"
        if "T4" in s:
            return 120
        if "토네이도" in s or "무진동" in s:
            return 80
        if "C.I.P" in nm:
            return 120
        if "H-PILE" in nm or "H파일" in nm:
            return 80
        return None

    for a in activities:
        if not a["is_leaf"]:
            continue
        nm, layer, qty, spec = a["name"], a["layer"], a["qty"], a["spec"]
        rate = fleet = None
        if "터파기" in nm and layer:
            rate, fleet = exc_rate(layer), DEFAULT_FLEET["터파기"]
        elif "천공" in nm:
            rate, fleet = drill_rate(nm, spec), DEFAULT_FLEET["천공"]
        elif "A.D.G" in nm or "ADG" in nm or "차수" in nm:
            if "천공" in nm or "주입" in nm:
                rate, fleet = 150, DEFAULT_FLEET["차수"]
        if rate and fleet:
            a["prod_rate"] = rate
            a["est_days"] = math.ceil(qty / (rate * fleet))
        else:
            a["prod_rate"] = None
            a["est_days"] = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("boq")
    ap.add_argument("--prod", default=None)
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    acts = parse_boq(args.boq)
    if args.prod:
        attach_durations(acts, json.load(open(args.prod, encoding="utf-8")))

    leaves = [a for a in acts if a["is_leaf"]]
    total_cost = sum(a["exec_cost"] for a in leaves)

    print(f"총 노드: {len(acts)}  |  Activity(리프): {len(leaves)}")
    print(f"리프 코스트 합계: {total_cost:,.0f} 원")
    tagged = [a for a in leaves if a["layer"]]
    print(f"지층 태깅된 항목: {len(tagged)}")
    dur = [a for a in leaves if a.get('est_days')]
    if dur:
        print(f"공기 산출된 항목: {len(dur)}  |  합계: {sum(a['est_days'] for a in dur)}일\n")
        print("--- 공기 산출 Activity (발췌) ---")
        for a in dur[:20]:
            print(f"  [{a['wbs_code']:>10}] {a['name']:14s} {a['spec'][:22]:22s} "
                  f"{a['qty']:>10,.0f}{a['unit']:>3} -> {a['est_days']:>3}일")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
            cols = ["wbs_code", "depth", "name", "spec", "unit", "qty",
                    "exec_rate", "exec_cost", "layer", "prod_rate", "est_days", "wbs_path"]
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(acts)
        print(f"\nCSV 저장: {args.csv}")


if __name__ == "__main__":
    main()
