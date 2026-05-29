"""역할별 실무 사용성 시뮬레이션 테스트.

4개 역할의 실무 시나리오를 시뮬레이션하여 59개 MCP 도구의 사용성을 검증한다.

역할:
1. 공무 (Construction Admin) — 계약, 기성, 원가, 설계변경, 공기관리
2. 현장 건축담당자 (Site Architecture Manager) — 일일 시공관리, 자재, 검측, 일보
3. 소장 (Site Director) — 전체 현황 파악, 의사결정, 브리핑
4. 본사 공사관리 (HQ Construction Mgmt) — EVM, 현금흐름, 리스크, 보고

시나리오 설정:
- 프로젝트: 홍은동 355번지 가로주택정비사업
- 공사기간: 2028-01-01 ~ 2029-06-30 (18개월)
- 공종: 건축, 기계설비, 전기설비, 소방설비
- 현재 시점: 2028-06-15 (공사 5.5개월차, 약 30% 진행)
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core import db
from core.change_order import (
    add_co_item_to_db,
    calculate_co_impact,
    create_change_order_in_db,
    get_co_summary,
    list_change_orders_from_db,
    update_co_status_in_db,
)
from core.delay_analysis import (
    calculate_time_extension_entitlement,
    generate_delay_analysis,
    list_delay_events_from_db,
    record_delay_event_to_db,
)
from core.productivity import (
    analyze_activity_productivity,
    analyze_productivity_summary,
    classify_productivity_status,
    get_productivity_trend,
)
from core.models import (
    Activity,
    Calendar,
    CostItem,
    DailyRecord,
    MaterialRecord,
    InspectionRecord,
    Project,
    Relationship,
    WBS,
)


# ===========================================================================
# Fixture: 현실적인 현장 DB 구성
# ===========================================================================


@pytest.fixture
def site_db(tmp_path: Path) -> Path:
    """홍은동 가로주택 현장 시뮬레이션 DB."""
    db_path = tmp_path / "hongeun_site.scheduler"
    db.initialize_database(db_path)

    # Calendar: 주5일, 공휴일 포함
    db.create_calendar(
        db_path,
        Calendar(
            "cal-main", "현장달력", "1111100",
            holidays=(
                "2028-01-01", "2028-02-08", "2028-02-09", "2028-02-10",
                "2028-03-01", "2028-05-05", "2028-06-06",
            ),
        ),
    )

    # Project
    db.create_project(
        db_path,
        Project("proj-hongeun", "홍은동 355번지 가로주택정비사업",
                date(2028, 1, 1), "cal-main",
                description="지하2층 지상15층 공동주택 180세대"),
    )

    # WBS: 공종별
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "전체공사", 0))
    db.create_wbs(db_path, WBS("wbs-arch", "wbs-root", "ARCH", "건축공사", 1))
    db.create_wbs(db_path, WBS("wbs-mech", "wbs-root", "MECH", "기계설비공사", 2))
    db.create_wbs(db_path, WBS("wbs-elec", "wbs-root", "ELEC", "전기설비공사", 3))
    db.create_wbs(db_path, WBS("wbs-fire", "wbs-root", "FIRE", "소방설비공사", 4))

    # --- Activities ---
    all_activities = [
        # 건축
        ("act-a01", "A-0100", "가설공사", "wbs-arch", "건축", 60,
         date(2028, 1, 1), date(2028, 3, 15)),
        ("act-a02", "A-0200", "토공사", "wbs-arch", "건축", 45,
         date(2028, 1, 15), date(2028, 3, 15)),
        ("act-a03", "A-0300", "기초공사", "wbs-arch", "건축", 60,
         date(2028, 2, 15), date(2028, 5, 1)),
        ("act-a04", "A-0400", "골조공사(지하)", "wbs-arch", "건축", 90,
         date(2028, 3, 1), date(2028, 6, 30)),
        ("act-a05", "A-0500", "골조공사(지상)", "wbs-arch", "건축", 180,
         date(2028, 5, 1), date(2028, 12, 31)),
        ("act-a06", "A-0600", "방수공사", "wbs-arch", "건축", 30,
         date(2028, 7, 1), date(2028, 8, 15)),
        ("act-a07", "A-0700", "조적/미장공사", "wbs-arch", "건축", 120,
         date(2028, 7, 15), date(2029, 1, 15)),
        ("act-a08", "A-0800", "창호공사", "wbs-arch", "건축", 60,
         date(2028, 9, 1), date(2028, 11, 30)),
        ("act-a09", "A-0900", "도장공사", "wbs-arch", "건축", 45,
         date(2029, 1, 1), date(2029, 3, 15)),
        ("act-a10", "A-1000", "마감공사", "wbs-arch", "건축", 60,
         date(2029, 3, 1), date(2029, 5, 31)),
        # 기계설비
        ("act-m01", "M-0100", "기계설비 슬리브", "wbs-mech", "기계설비", 90,
         date(2028, 3, 15), date(2028, 7, 15)),
        ("act-m02", "M-0200", "위생배관공사", "wbs-mech", "기계설비", 150,
         date(2028, 5, 1), date(2028, 11, 30)),
        ("act-m03", "M-0300", "공조설비공사", "wbs-mech", "기계설비", 120,
         date(2028, 7, 1), date(2028, 12, 31)),
        ("act-m04", "M-0400", "기계설비 시운전", "wbs-mech", "기계설비", 30,
         date(2029, 4, 1), date(2029, 5, 15)),
        # 전기설비
        ("act-e01", "E-0100", "전기설비 슬리브/인입", "wbs-elec", "전기설비", 60,
         date(2028, 3, 1), date(2028, 5, 15)),
        ("act-e02", "E-0200", "전기배관/배선공사", "wbs-elec", "전기설비", 180,
         date(2028, 5, 1), date(2029, 1, 31)),
        ("act-e03", "E-0300", "수배전반/분전반", "wbs-elec", "전기설비", 45,
         date(2029, 1, 15), date(2029, 3, 31)),
        ("act-e04", "E-0400", "전기설비 시운전", "wbs-elec", "전기설비", 30,
         date(2029, 4, 1), date(2029, 5, 15)),
        # 소방설비
        ("act-f01", "F-0100", "소방배관공사", "wbs-fire", "소방설비", 120,
         date(2028, 5, 15), date(2028, 11, 15)),
        ("act-f02", "F-0200", "소방전기공사", "wbs-fire", "소방설비", 90,
         date(2028, 8, 1), date(2028, 12, 31)),
        ("act-f03", "F-0300", "소방 시운전/준공검사", "wbs-fire", "소방설비", 30,
         date(2029, 4, 15), date(2029, 5, 31)),
    ]

    for aid, code, name, wbs, disc, dur, es, ef in all_activities:
        db.create_activity(
            db_path,
            Activity(
                activity_id=aid, code=code, name=name,
                wbs_id=wbs, discipline=disc, zone="",
                duration=dur, es_date=es, ef_date=ef,
            ),
        )

    # --- Relationships ---
    rels = [
        ("rel-01", "act-a01", "act-a02", "SS", 10),
        ("rel-02", "act-a02", "act-a03", "FS", 0),
        ("rel-03", "act-a03", "act-a04", "FS", 0),
        ("rel-04", "act-a04", "act-a05", "FS", -15),
        ("rel-05", "act-a04", "act-m01", "SS", 10),
        ("rel-06", "act-a04", "act-e01", "SS", 0),
        ("rel-07", "act-a05", "act-a06", "SS", 30),
        ("rel-08", "act-a05", "act-a07", "SS", 45),
        ("rel-09", "act-a05", "act-a08", "SS", 90),
        ("rel-10", "act-m01", "act-m02", "FS", 0),
        ("rel-11", "act-e01", "act-e02", "FS", 0),
        ("rel-12", "act-a05", "act-f01", "SS", 15),
    ]
    for rid, pred, succ, rtype, lag in rels:
        db.create_relationship(
            db_path,
            Relationship(rid, pred, succ, rtype, lag),
        )

    # --- Cost Items ---
    cost_data = [
        ("act-a01", 450_000_000, 400_000_000, 380_000_000, 420_000_000),
        ("act-a02", 800_000_000, 720_000_000, 710_000_000, 750_000_000),
        ("act-a03", 1_200_000_000, 1_050_000_000, 1_080_000_000, 1_100_000_000),
        ("act-a04", 2_500_000_000, 2_200_000_000, 1_300_000_000, 1_200_000_000),
        ("act-a05", 4_500_000_000, 3_900_000_000, 200_000_000, 150_000_000),
        ("act-a06", 300_000_000, 260_000_000, 0, 0),
        ("act-a07", 1_800_000_000, 1_550_000_000, 0, 0),
        ("act-a08", 900_000_000, 800_000_000, 0, 0),
        ("act-a09", 350_000_000, 310_000_000, 0, 0),
        ("act-a10", 600_000_000, 520_000_000, 0, 0),
        ("act-m01", 250_000_000, 220_000_000, 150_000_000, 130_000_000),
        ("act-m02", 1_100_000_000, 950_000_000, 120_000_000, 100_000_000),
        ("act-m03", 850_000_000, 740_000_000, 0, 0),
        ("act-m04", 80_000_000, 70_000_000, 0, 0),
        ("act-e01", 180_000_000, 160_000_000, 155_000_000, 170_000_000),
        ("act-e02", 900_000_000, 780_000_000, 80_000_000, 60_000_000),
        ("act-e03", 350_000_000, 300_000_000, 0, 0),
        ("act-e04", 60_000_000, 55_000_000, 0, 0),
        ("act-f01", 400_000_000, 350_000_000, 30_000_000, 20_000_000),
        ("act-f02", 250_000_000, 220_000_000, 0, 0),
        ("act-f03", 50_000_000, 45_000_000, 0, 0),
    ]
    for aid, contract, budget, invested, billed in cost_data:
        db.upsert_cost_item(
            db_path,
            CostItem(
                f"cost-{aid}", aid,
                contract_amount=contract, execution_budget=budget,
                invested_cost=invested, billing_amount=billed,
            ),
        )

    # --- Daily Records ---
    # 골조공사(지하) - 마무리, 생산성 양호
    dr_idx = 0
    for i in range(25):
        d = date(2028, 5, 15 + i) if 15 + i <= 31 else date(2028, 6, 15 + i - 31)
        if d.weekday() >= 5:
            continue
        db.create_daily_record(
            db_path,
            DailyRecord(
                f"dr-a04-{dr_idx:03d}", "act-a04", d,
                planned_qty=100.0, actual_qty=90.0 + (dr_idx % 5) * 3,
                workers=12, equipment="타워크레인 1대, 콘크리트펌프 1대",
                owner="건축팀 김대리",
            ),
        )
        dr_idx += 1

    # 골조공사(지상) - 초기, 낮은 생산성
    dr_idx = 0
    for i in range(8):
        d = date(2028, 6, 3 + i)
        if d.weekday() >= 5:
            continue
        db.create_daily_record(
            db_path,
            DailyRecord(
                f"dr-a05-{dr_idx:03d}", "act-a05", d,
                planned_qty=80.0, actual_qty=40.0 + dr_idx * 5,
                workers=8, equipment="타워크레인 1대",
                owner="건축팀 박과장",
            ),
        )
        dr_idx += 1

    # 기계설비 슬리브 - 중간 진행, 보통
    dr_idx = 0
    for i in range(15):
        d = date(2028, 5, 20 + i) if 20 + i <= 31 else date(2028, 6, 20 + i - 31)
        if d.weekday() >= 5:
            continue
        db.create_daily_record(
            db_path,
            DailyRecord(
                f"dr-m01-{dr_idx:03d}", "act-m01", d,
                planned_qty=50.0, actual_qty=42.0 + (dr_idx % 3) * 2,
                workers=4,
                owner="기계팀 이대리",
            ),
        )
        dr_idx += 1

    # 위생배관 - 생산성 저조
    for i in range(5):
        d = date(2028, 6, 8 + i)
        if d.weekday() >= 5:
            continue
        db.create_daily_record(
            db_path,
            DailyRecord(
                f"dr-m02-{i:03d}", "act-m02", d,
                planned_qty=60.0, actual_qty=25.0,
                workers=3,
                owner="기계팀 이대리",
                remarks="자재 입고 지연으로 작업량 부족",
            ),
        )

    # --- Materials ---
    materials = [
        ("mat-001", "act-a05", "레미콘(25-24-15)", date(2028, 5, 1),
         date(2028, 5, 15), date(2028, 5, 14), "delivered"),
        ("mat-002", "act-a05", "철근(HD13~HD25)", date(2028, 5, 1),
         date(2028, 5, 10), date(2028, 5, 10), "delivered"),
        ("mat-003", "act-a08", "시스템창호(AL)", date(2028, 6, 1),
         date(2028, 8, 15), None, "ordered"),
        ("mat-004", "act-m02", "배관자재(STS)", date(2028, 4, 15),
         date(2028, 5, 30), None, "delayed"),
        ("mat-005", "act-m03", "공조기(AHU)", date(2028, 5, 15),
         date(2028, 9, 1), None, "ordered"),
        ("mat-006", "act-e02", "전선(HIV 2.5sq~)", date(2028, 5, 1),
         date(2028, 6, 15), date(2028, 6, 12), "delivered"),
    ]
    for mid, aid, name, od, ed, ad, status in materials:
        db.create_material_record(
            db_path,
            MaterialRecord(mid, aid, name,
                           order_date=od, expected_date=ed,
                           actual_date=ad, status=status),
        )

    # --- Inspections ---
    inspections = [
        ("insp-001", "act-a03", "기초 배근검사", date(2028, 4, 10),
         date(2028, 4, 10), "passed", "감리 홍팀장"),
        ("insp-002", "act-a04", "지하 골조 배근검사", date(2028, 5, 20),
         date(2028, 5, 21), "passed", "감리 홍팀장"),
        ("insp-003", "act-a04", "지하 골조 콘크리트 타설검사", date(2028, 6, 10),
         None, "planned", ""),
        ("insp-004", "act-a05", "1층 골조 배근검사", date(2028, 6, 20),
         None, "planned", ""),
        ("insp-005", "act-m01", "슬리브 설치검사", date(2028, 6, 5),
         date(2028, 6, 6), "passed", "감리 박부장"),
    ]
    for iid, aid, itype, pd, ad, status, approver in inspections:
        db.create_inspection_record(
            db_path,
            InspectionRecord(iid, aid, itype,
                             planned_date=pd, actual_date=ad,
                             status=status, approver=approver),
        )

    return db_path


# ===========================================================================
# 역할 1: 공무 (Construction Administration)
# ===========================================================================


class TestRole_공무:
    """공무 담당자의 일상 업무 시뮬레이션."""

    def test_scenario_billing_workflow(self, site_db):
        """6월 기성고 산출 → 요약 조회."""
        from core.billing import calculate_monthly_billing, get_billing_summary

        result = calculate_monthly_billing(site_db, "2028-06")
        assert result["ok"] is True
        assert len(result["rows"]) > 0

        summary = get_billing_summary(site_db)
        assert summary["ok"] is True
        assert summary["total_contract"] > 0

    def test_scenario_budget_variance(self, site_db):
        """공종별 예산 집행 현황 → 차이 분석 → 시나리오 예측."""
        from core.cost import analyze_budget_variance, forecast_scenarios

        result = analyze_budget_variance(site_db)
        assert result["ok"] is True
        assert len(result["items"]) > 0
        assert result["overall"]["status"] in ("절감", "정상", "초과", "위험")

        arch_result = analyze_budget_variance(site_db, discipline="건축")
        assert arch_result["ok"] is True

        scenarios = forecast_scenarios(site_db)
        assert scenarios["ok"] is True
        assert scenarios["scenarios"]["낙관"]["forecast"] <= scenarios["scenarios"]["비관"]["forecast"]

    def test_scenario_change_order_workflow(self, site_db):
        """설계변경 접수 → 항목 추가 → 검토 → 승인 전체 흐름."""
        result = create_change_order_in_db(
            site_db, "지하주차장 바닥구배 변경",
            description="지하2층 주차장 바닥 구배를 1/100에서 1/50으로 변경",
            co_type="owner_directed",
            requested_by="발주처 김부장",
            request_date=date(2028, 6, 10),
            direct_cost=45_000_000,
            markup_pct=12.0,
            schedule_impact_days=7,
            dry_run=False,
        )
        assert result["ok"] is True
        co_id = result["co_id"]

        item1 = add_co_item_to_db(
            site_db, co_id, "act-a04",
            cost_change=30_000_000, duration_change=5,
            description="골조 레벨 변경 및 재시공",
            dry_run=False,
        )
        assert item1["ok"] is True

        item2 = add_co_item_to_db(
            site_db, co_id, "act-m01",
            cost_change=15_000_000, duration_change=3,
            description="슬리브 위치 재조정",
            dry_run=False,
        )
        assert item2["ok"] is True

        impact = calculate_co_impact(site_db, co_id)
        assert impact["items_count"] == 2
        assert impact["items_total_cost_change"] == 45_000_000

        update_co_status_in_db(site_db, co_id, "pending", dry_run=False)
        approved = update_co_status_in_db(
            site_db, co_id, "approved",
            approved_by="현장소장 박상무",
            approval_date=date(2028, 6, 14),
            dry_run=False,
        )
        assert approved["ok"] is True
        assert approved["new_status_kr"] == "승인"

        summary = get_co_summary(site_db)
        assert summary["approved_count"] == 1

    def test_scenario_delay_claim(self, site_db):
        """지연 기록 → 분석 → 공기연장 클레임 산출."""
        r1 = record_delay_event_to_db(
            site_db, "act-a04", "excusable_compensable", "owner_change",
            responsible_party="발주처",
            start_date=date(2028, 5, 15), end_date=date(2028, 5, 30),
            cost_impact=25_000_000,
            description="발주처 설계변경(주차장 구배) 대기",
            dry_run=False,
        )
        assert r1["ok"] is True
        assert r1["delay_days"] == 15

        r2 = record_delay_event_to_db(
            site_db, "act-a04", "excusable_non_compensable", "weather",
            start_date=date(2028, 6, 1), end_date=date(2028, 6, 5),
            description="장마철 폭우 (일일 80mm 이상)",
            dry_run=False,
        )
        assert r2["ok"] is True

        r3 = record_delay_event_to_db(
            site_db, "act-m02", "non_excusable", "subcontractor",
            delay_days=10,
            description="배관 협력업체 인력 미투입",
            dry_run=False,
        )
        assert r3["ok"] is True

        analysis = generate_delay_analysis(site_db)
        assert analysis["total_events"] == 3
        assert analysis["total_delay_days"] == 29

        claim = calculate_time_extension_entitlement(site_db)
        assert claim["recommended_extension_days"] == 19
        assert claim["compensable_cost"] == 25_000_000
        assert "공기연장 권고: 19일" in claim["summary_kr"]

    def test_scenario_cashflow(self, site_db):
        """현금흐름 예측 → 자금소요."""
        from core.cashflow import forecast_cash_flow, calculate_funding_requirements

        cf = forecast_cash_flow(
            site_db, "2028-01-01", "2028-12-31",
            payment_terms="NET_30", retention_pct=10.0, interval="monthly",
        )
        assert cf["ok"] is True
        assert len(cf["periods"]) > 0

        funding = calculate_funding_requirements(
            site_db, start_date="2028-01-01", end_date="2028-12-31", buffer_pct=10.0,
        )
        assert funding["ok"] is True


# ===========================================================================
# 역할 2: 현장 건축담당자
# ===========================================================================


class TestRole_건축담당:
    """현장 건축담당자의 일일 업무 시뮬레이션."""

    def test_scenario_daily_record_input(self, site_db):
        """골조공사 일보 작성 (DB에 직접 기록)."""
        record = DailyRecord(
            "dr-new-001", "act-a04", date(2028, 6, 15),
            planned_qty=100.0, actual_qty=95.0,
            workers=14,
            equipment="타워크레인 1대, 콘크리트펌프카 1대",
            remarks="B2층 벽체 타설 완료. 양생 3일 필요.",
        )
        db.create_daily_record(site_db, record)

        records = db.list_daily_records(site_db, activity_id="act-a04")
        assert any(r.record_id == "dr-new-001" for r in records)

    def test_scenario_material_management(self, site_db):
        """자재 발주 현황 확인 → 지연 자재 업데이트."""
        materials = db.list_materials(site_db)
        assert len(materials) > 0

        delayed = [m for m in materials if m.status == "delayed"]
        assert len(delayed) > 0
        assert delayed[0].material_name == "배관자재(STS)"

        updated = db.update_material_status(
            site_db, delayed[0].material_id,
            status="delivered",
            actual_date=date(2028, 6, 15),
        )
        assert updated.status == "delivered"

    def test_scenario_inspection_workflow(self, site_db):
        """검측 일정 확인 → 예정 검측 확인."""
        inspections = db.list_inspections(site_db)
        planned = [i for i in inspections if i.status == "planned"]
        assert len(planned) >= 2

        names = [i.inspection_type for i in planned]
        assert "지하 골조 콘크리트 타설검사" in names
        assert "1층 골조 배근검사" in names

    def test_scenario_productivity_check(self, site_db):
        """담당 활동별 생산성 확인."""
        prod_a04 = analyze_activity_productivity(site_db, "act-a04")
        assert prod_a04["ok"] is True
        assert prod_a04["record_count"] > 0
        assert prod_a04["productivity_index"] > 80

        prod_a05 = analyze_activity_productivity(site_db, "act-a05")
        assert prod_a05["ok"] is True

        trend = get_productivity_trend(site_db, "act-a04")
        assert trend["ok"] is True
        assert trend["trend"] in ("개선", "유지", "하락", "정보 부족")

    def test_scenario_activity_logistics(self, site_db):
        """활동별 자재/검측 현황 한눈에 확인."""
        materials = db.list_materials(site_db, activity_id="act-a05")
        inspections = db.list_inspections(site_db, activity_id="act-a05")
        # 골조공사(지상): 레미콘+철근 delivered, 배근검사 planned
        assert len(materials) == 2
        assert all(m.status == "delivered" for m in materials)
        assert len(inspections) == 1


# ===========================================================================
# 역할 3: 소장 (Site Director)
# ===========================================================================


class TestRole_소장:
    """현장소장의 의사결정 지원 시뮬레이션."""

    def test_scenario_morning_briefing(self, site_db):
        """매일 아침 현장 현황 브리핑."""
        from core.dashboard import generate_site_briefing

        briefing = generate_site_briefing(site_db, as_of=date(2028, 6, 15))
        assert briefing["ok"] is True
        assert "project_name" in briefing or "project" in briefing

    def test_scenario_discipline_progress(self, site_db):
        """공종별 진도 확인."""
        from core.dashboard import get_progress_by_discipline

        progress = get_progress_by_discipline(site_db, as_of=date(2028, 6, 15))
        assert progress["ok"] is True
        assert "rows" in progress
        disc_names = [d["discipline"] for d in progress["rows"]]
        assert "건축" in disc_names

    def test_scenario_data_health(self, site_db):
        """시스템 신뢰성 확인."""
        from tools.diagnostic_tools import check_data_health

        health = check_data_health(str(site_db))
        assert health["ok"] is True
        assert "score" in health
        assert 0 <= health["score"] <= 100

    def test_scenario_delay_and_recovery(self, site_db):
        """지연 기록 후 분석."""
        record_delay_event_to_db(
            site_db, "act-a04", "excusable_compensable", "owner_change",
            delay_days=15, cost_impact=25_000_000, dry_run=False,
        )
        record_delay_event_to_db(
            site_db, "act-m02", "non_excusable", "material_delay",
            delay_days=10, dry_run=False,
        )

        analysis = generate_delay_analysis(site_db)
        assert analysis["total_events"] == 2
        assert analysis["total_delay_days"] == 25

    def test_scenario_productivity_overview(self, site_db):
        """전 공종 생산성 요약."""
        summary = analyze_productivity_summary(site_db)
        assert summary["ok"] is True
        assert summary["overall_productivity_index"] > 0
        assert len(summary["activities"]) > 0

    def test_scenario_co_overview(self, site_db):
        """설계변경 현황 파악."""
        create_change_order_in_db(
            site_db, "발주처 설계변경 #1",
            co_type="owner_directed",
            direct_cost=45_000_000, markup_pct=12.0,
            schedule_impact_days=7, dry_run=False,
        )
        create_change_order_in_db(
            site_db, "VE 제안 - 외벽 단열재",
            co_type="value_engineering",
            direct_cost=-20_000_000,
            dry_run=False,
        )

        summary = get_co_summary(site_db)
        assert summary["total_count"] == 2
        assert summary["total_direct_cost"] == 25_000_000

    def test_scenario_next_actions(self, site_db):
        """소장 관점 다음 행동 추천."""
        from tools.diagnostic_tools import suggest_next_actions

        actions = suggest_next_actions(str(site_db), profile="site_director")
        assert actions["ok"] is True
        assert len(actions["actions"]) > 0


# ===========================================================================
# 역할 4: 본사 공사관리 담당자
# ===========================================================================


class TestRole_본사공사관리:
    """본사 공사관리 담당자의 업무 시뮬레이션."""

    def test_scenario_evm_analysis(self, site_db):
        """EVM 분석."""
        from tools.cost_tools import analyze_evm_from_db

        evm = analyze_evm_from_db(str(site_db), as_of_date="2028-06-15")
        assert evm["ok"] is True

    def test_scenario_cost_by_discipline(self, site_db):
        """공종별 원가 현황."""
        from tools.cost_tools import summarize_cost_by_discipline

        result = summarize_cost_by_discipline(str(site_db))
        assert result["ok"] is True
        assert len(result["rows"]) > 0

    def test_scenario_cashflow_monthly(self, site_db):
        """본사 자금 계획용 월별 현금흐름."""
        from core.cashflow import forecast_cash_flow

        cf = forecast_cash_flow(
            site_db, "2028-01-01", "2029-06-30",
            payment_terms="NET_30", retention_pct=10.0, interval="monthly",
        )
        assert cf["ok"] is True
        assert len(cf["periods"]) >= 12

    def test_scenario_eac_scenarios(self, site_db):
        """완공 추정 비용 시나리오."""
        from core.cost import forecast_scenarios

        result = forecast_scenarios(site_db)
        assert result["ok"] is True
        assert result["scenarios"]["낙관"]["forecast"] > 0
        assert result["scenarios"]["비관"]["forecast"] > 0

    def test_scenario_budget_variance_hq(self, site_db):
        """본사 관점의 전체 예산 분석."""
        from core.cost import analyze_budget_variance

        result = analyze_budget_variance(site_db)
        assert result["ok"] is True
        assert result["overall"]["status"] in ("절감", "정상", "초과", "위험")
        assert len(result["discipline_summary"]) > 0

    def test_scenario_delay_risk_monitoring(self, site_db):
        """현장 지연 리스크를 모니터링."""
        record_delay_event_to_db(
            site_db, "act-a04", "excusable_compensable", "owner_change",
            delay_days=15, cost_impact=25_000_000, dry_run=False,
        )
        record_delay_event_to_db(
            site_db, "act-m02", "non_excusable", "material_delay",
            delay_days=10, dry_run=False,
        )
        record_delay_event_to_db(
            site_db, "act-a04", "concurrent", "weather",
            delay_days=3, dry_run=False,
        )

        analysis = generate_delay_analysis(site_db)
        assert analysis["total_events"] == 3
        assert "by_type" in analysis
        assert "by_cause" in analysis

        claim = calculate_time_extension_entitlement(site_db)
        assert claim["recommended_extension_days"] == 15
        assert claim["compensable_cost"] == 25_000_000

    def test_scenario_evm_explain(self, site_db):
        """EVM 지표 쉬운 한국어 설명."""
        from tools.diagnostic_tools import explain_evm_from_db

        explanation = explain_evm_from_db(str(site_db), as_of="2028-06-15")
        assert explanation["ok"] is True
        assert "explanation" in explanation


# ===========================================================================
# 통합 시나리오: 역할 간 연계
# ===========================================================================


class TestCrossRole:
    """역할 간 연계 시나리오."""

    def test_scenario_full_change_order_lifecycle(self, site_db):
        """건축담당 발견 → 공무 CO 생성 → 소장 승인 → 본사 영향 확인."""

        # Step 1: 건축담당 - 일보에 이슈 기록
        db.create_daily_record(
            site_db,
            DailyRecord(
                "dr-issue-001", "act-a03", date(2028, 6, 15),
                planned_qty=100.0, actual_qty=30.0,
                workers=8, equipment="굴착기 2대",
                remarks="기초 굴착 중 예상치 못한 암반 출현. 발파 검토 필요.",
            ),
        )

        # Step 2: 공무 - CO 생성
        co = create_change_order_in_db(
            site_db, "기초 암반 출현 - 발파공사 추가",
            co_type="field_condition",
            requested_by="건축팀 박과장",
            request_date=date(2028, 6, 15),
            direct_cost=180_000_000,
            markup_pct=15.0,
            schedule_impact_days=20,
            dry_run=False,
        )
        co_id = co["co_id"]

        # 공무 - 지연 기록
        record_delay_event_to_db(
            site_db, "act-a03", "excusable_compensable", "site_condition",
            start_date=date(2028, 6, 15), end_date=date(2028, 7, 5),
            cost_impact=180_000_000,
            description="예상치 못한 암반 출현으로 발파공사 추가",
            dry_run=False,
        )

        # Step 3: 소장 - 승인
        update_co_status_in_db(site_db, co_id, "pending", dry_run=False)
        approval = update_co_status_in_db(
            site_db, co_id, "approved",
            approved_by="소장 박상무",
            approval_date=date(2028, 6, 16),
            dry_run=False,
        )
        assert approval["ok"] is True

        # Step 4: 본사 - 영향 확인
        impact = calculate_co_impact(site_db, co_id)
        assert impact["header_total_cost"] == 207_000_000  # 180M * 1.15

        claim = calculate_time_extension_entitlement(site_db)
        assert claim["recommended_extension_days"] == 20

    def test_scenario_productivity_driven_recovery(self, site_db):
        """생산성 저조 포착 → 상세 분석 → 대응."""

        # Step 1: 본사 - 전체 생산성 요약
        summary = analyze_productivity_summary(site_db)
        assert summary["ok"] is True
        risky = [
            a for a in summary["activities"]
            if a["status"] in ("부진", "위험")
        ]
        assert len(risky) > 0  # 위생배관 위험

        # Step 2: 담당 - 문제 활동 상세 분석
        prod_m02 = analyze_activity_productivity(site_db, "act-m02")
        assert prod_m02["status"] == "위험"
        assert prod_m02["productivity_index"] < 50

        # Step 3: 소장 - 지연 기록 + 대응 지시
        record_delay_event_to_db(
            site_db, "act-m02", "non_excusable", "material_delay",
            delay_days=10,
            description="배관자재 STS 입고 지연으로 생산성 저하",
            dry_run=False,
        )
        events = list_delay_events_from_db(site_db, activity_id="act-m02")
        assert events["count"] == 1
