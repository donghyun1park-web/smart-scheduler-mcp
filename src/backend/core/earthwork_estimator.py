"""
core/earthwork_estimator.py  (참조 구현 / reference implementation)

기능1+2 핵심 루프: BOQ 수량 + 지층 + 장비대수 -> 공기(일) 자동 산출.
- 단일 공종 산출: estimate_activity_days()
- 단계별 굴착 합산: estimate_excavation_stages()
- 장비 대수 변경 what-if 지원.

주의: 생산성 원단위는 earthwork_productivity.json / excavation_stage_model.json
에서 로드. 필드명은 기존 presets 로더 스키마에 맞춰 조정 필요.
"""

from __future__ import annotations
import json
import math
from pathlib import Path


def load_productivity(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _pick_rate(entry: dict, prefer_current: bool = True) -> float | None:
    """현장 적용 생산성 우선, 없으면 이론치."""
    if prefer_current and entry.get("current_rate"):
        return float(entry["current_rate"])
    if entry.get("theoretical_rate"):
        return float(entry["theoretical_rate"])
    if entry.get("rate"):
        return float(entry["rate"])
    return None


def estimate_activity_days(
    quantity: float,
    rate_per_unit_per_day: float,
    equipment_count: int = 1,
) -> float:
    """수량 / (생산성 x 장비대수) = 소요일수 (올림)."""
    if rate_per_unit_per_day <= 0 or equipment_count <= 0:
        raise ValueError("rate와 equipment_count는 0보다 커야 합니다.")
    daily_output = rate_per_unit_per_day * equipment_count
    return math.ceil(quantity / daily_output)


def estimate_excavation_stages(
    stage_model: dict,
    productivity: dict,
    fleet_override: int | None = None,
    use_applied: bool = True,
) -> list[dict]:
    """
    단계별 굴착 공기 산출.
    use_applied=True  -> 안전평가서 적용기간(현장 보정치) 사용.
    use_applied=False -> 생산성 원단위로 재계산(장비 what-if 가능).
    """
    exc_rates = {e["layer"]: e for e in productivity["excavation"]}
    fleet = fleet_override or stage_model["site"]["fleet"]["backhoe"]
    results = []
    for st in stage_model["stages"]:
        volume = round(st["area_m2"] * st["depth_m"], 1)
        if use_applied:
            days = st["applied_days"]
            basis = "안전평가서 적용기간"
        else:
            layer = st["layer"]
            entry = _match_layer(exc_rates, layer)
            rate = _pick_rate(entry) if entry else None
            days = estimate_activity_days(volume, rate, fleet) if rate else None
            basis = f"원단위 재계산(fleet={fleet})"
        results.append(
            {"stage": st["stage"], "layer": st["layer"],
             "volume_m3": volume, "days": days, "basis": basis}
        )
    return results


def _match_layer(exc_rates: dict, layer: str) -> dict | None:
    """지층명 부분일치 정규화: '토사' <-> '토사/매립토', '경암' <-> '경암/보통암' 등."""
    if layer in exc_rates:
        return exc_rates[layer]
    for key, entry in exc_rates.items():
        parts = key.replace("/", " ").split()
        if layer in parts or any(p in layer for p in parts):
            return entry
    return None


def _fallback_rock(exc_rates: dict, layer: str) -> dict | None:
    return _match_layer(exc_rates, layer)


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1] / "presets"
    prod = load_productivity(base / "earthwork_productivity.json")
    stages = load_productivity(base / "excavation_stage_model.json")

    print("== 적용기간(현장 보정) ==")
    for r in estimate_excavation_stages(stages, prod, use_applied=True):
        print(f"  {r['stage']}단계 {r['layer']:4s} {r['volume_m3']:>10.1f}m3  {r['days']}일")

    print("\n== 원단위 재계산: 백호 7대 ==")
    for r in estimate_excavation_stages(stages, prod, fleet_override=7, use_applied=False):
        print(f"  {r['stage']}단계 {r['layer']:4s} {r['volume_m3']:>10.1f}m3  {r['days']}일")

    print("\n== what-if: 백호 14대 ==")
    for r in estimate_excavation_stages(stages, prod, fleet_override=14, use_applied=False):
        print(f"  {r['stage']}단계 {r['layer']:4s} {r['volume_m3']:>10.1f}m3  {r['days']}일")
