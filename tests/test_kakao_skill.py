"""카카오 챗봇 통합 테스트 — payload 파싱, 응답 빌더, 발화 라우팅, 포매터."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from core import db
from core.kakao_format import format_briefing_for_kakao, format_reminder_for_kakao
from core.kakao_report import handle_utterance
from core.kakao_skill import (
    build_callback_waiting,
    build_simple_text,
    build_text_card,
    parse_skill_payload,
)
from core.models import Activity, Calendar, CostItem, DailyRecord, Project, WBS


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def site_db(tmp_path: Path) -> Path:
    """활동 2건(기계설비/건축) 있는 테스트 DB."""
    db_path = tmp_path / "kakao_test.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
    db.create_project(db_path, Project("proj-1", "홍은동 테스트", date(2026, 1, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "Root"))
    db.create_activity(
        db_path,
        Activity("act-mech", "M-001", "위생배관 설치", "wbs-root", "기계설비", "B1", 100,
                 es_date=date(2026, 1, 1), ef_date=date(2026, 6, 30)),
    )
    db.upsert_cost_item(db_path, CostItem("c-1", "act-mech", execution_budget=100_000_000))
    db.create_activity(
        db_path,
        Activity("act-arch", "A-001", "골조공사", "wbs-root", "건축", "", 200,
                 es_date=date(2026, 1, 1), ef_date=date(2026, 12, 31)),
    )
    db.upsert_cost_item(db_path, CostItem("c-2", "act-arch", execution_budget=500_000_000))
    return db_path


_SKILL_BODY = {
    "userRequest": {
        "user": {"id": "user-123", "properties": {"botUserKey": "user-123"}},
        "utterance": "위생배관 70% 8명",
        "callbackUrl": "https://bot-api.kakao.com/callback/xyz",
    },
    "action": {
        "params": {
            "secureimage": '{"secureUrls":"List(https://secure.kakao.com/img1.jpg, https://secure.kakao.com/img2.jpg)"}'
        }
    },
}


# ─── parse_skill_payload ──────────────────────────────────────────────────────

class TestParsePayload:
    def test_basic_fields(self):
        p = parse_skill_payload(_SKILL_BODY)
        assert p.bot_user_key == "user-123"
        assert p.utterance == "위생배관 70% 8명"
        assert p.callback_url.startswith("https://bot-api")

    def test_secure_image_urls(self):
        p = parse_skill_payload(_SKILL_BODY)
        assert len(p.image_urls) == 2
        assert p.image_urls[0] == "https://secure.kakao.com/img1.jpg"

    def test_empty_body(self):
        p = parse_skill_payload({})
        assert p.bot_user_key == ""
        assert p.image_urls == ()

    def test_plain_url_param(self):
        body = {"action": {"params": {"img": "https://x.com/a.png"}}}
        p = parse_skill_payload(body)
        assert p.image_urls == ("https://x.com/a.png",)


# ─── 응답 빌더 ─────────────────────────────────────────────────────────────────

class TestResponseBuilders:
    def test_simple_text(self):
        r = build_simple_text("안녕")
        assert r["version"] == "2.0"
        assert r["template"]["outputs"][0]["simpleText"]["text"] == "안녕"

    def test_text_card_with_buttons(self):
        r = build_text_card("제목", "본문", buttons=[
            {"label": "열기", "action": "webLink", "webLinkUrl": "https://x.com"}
        ])
        card = r["template"]["outputs"][0]["textCard"]
        assert card["title"] == "제목"
        assert card["buttons"][0]["label"] == "열기"

    def test_callback_waiting(self):
        r = build_callback_waiting()
        assert r["useCallback"] is True


# ─── handle_utterance 라우팅 ──────────────────────────────────────────────────

class TestHandleUtterance:
    def test_register(self, site_db):
        reply = handle_utterance(site_db, bot_user_key="u1", utterance="등록 기계설비 김기계")
        assert "등록 완료" in reply
        user = db.get_kakao_user(site_db, "u1")
        assert user["owner_name"] == "김기계"
        assert user["discipline"] == "기계설비"

    def test_briefing(self, site_db):
        reply = handle_utterance(site_db, bot_user_key="u1", utterance="현황")
        assert "브리핑" in reply or "공정률" in reply

    def test_text_report_saves_record(self, site_db):
        handle_utterance(site_db, bot_user_key="u1", utterance="등록 기계설비 김기계")
        reply = handle_utterance(
            site_db, bot_user_key="u1", utterance="위생배관 70% 8명 자재 도착",
            work_date=date(2026, 6, 1),
        )
        assert "저장 완료" in reply
        records = db.list_daily_records(site_db, activity_id="act-mech")
        assert len(records) == 1
        assert records[0].actual_qty == 70.0
        assert records[0].workers == 8
        assert "자재 도착" in records[0].remarks
        assert records[0].owner == "김기계"

    def test_text_report_unknown_activity(self, site_db):
        reply = handle_utterance(site_db, bot_user_key="u1", utterance="없는공정 50%")
        assert "찾지 못했" in reply

    def test_unregistered_help(self, site_db):
        reply = handle_utterance(site_db, bot_user_key="new-user", utterance="ㅎㅇ")
        assert "등록" in reply
        assert "사용법" in reply

    def test_pct_capped_at_100(self, site_db):
        handle_utterance(site_db, bot_user_key="u1", utterance="등록 기계설비 김기계")
        handle_utterance(site_db, bot_user_key="u1", utterance="위생배관 150% 3명",
                         work_date=date(2026, 6, 2))
        records = db.list_daily_records(site_db, activity_id="act-mech")
        assert records[0].actual_qty == 100.0

    def test_image_report_saves(self, site_db):
        """이미지 URL → (mock) 다운로드·파싱 → daily_record 저장."""
        handle_utterance(site_db, bot_user_key="u1", utterance="등록 기계설비 김기계")
        parsed = {
            "work_date": "2026-06-03",
            "team_name": "현대설비",
            "work_items": [{"no": 1, "category": "배관", "team": "협력", "description": "위생배관 B1층 설치"}],
            "equipment": [], "supplies": [],
            "summary": "위생배관 작업", "warnings": [],
        }
        with patch("core.kakao_report._download_image", return_value=b"\xff\xd8\xff"), \
             patch("core.kakao_report.parse_report_image", return_value=parsed):
            reply = handle_utterance(
                site_db, bot_user_key="u1", utterance="",
                image_urls=("https://secure.kakao.com/img1.jpg",),
            )
        assert "일보 저장 완료" in reply
        records = db.list_daily_records(site_db, activity_id="act-mech")
        assert len(records) == 1
        assert records[0].work_date == date(2026, 6, 3)


# ─── kakao_format ─────────────────────────────────────────────────────────────

class TestKakaoFormat:
    def test_briefing_text(self, site_db):
        text = format_briefing_for_kakao(site_db, as_of=date(2026, 3, 1))
        assert "브리핑" in text
        assert "공정률" in text
        assert len(text) <= 800

    def test_reminder_lists_missing(self, site_db):
        text = format_reminder_for_kakao(site_db, base_url="http://nas:8501", as_of=date(2026, 3, 2))
        assert "미제출" in text
        assert "기계설비" in text
        assert "http://nas:8501?discipline=기계설비" in text

    def test_reminder_all_submitted(self, site_db):
        for act_id in ("act-mech", "act-arch"):
            db.create_daily_record(site_db, DailyRecord(
                record_id=f"r-{act_id}", activity_id=act_id,
                work_date=date(2026, 3, 3), actual_qty=10.0,
            ))
        text = format_reminder_for_kakao(site_db, as_of=date(2026, 3, 3))
        assert "완료" in text


# ─── kakao_users CRUD ────────────────────────────────────────────────────────

class TestKakaoUsers:
    def test_upsert_and_get(self, site_db):
        db.upsert_kakao_user(site_db, "k1", "박전기", "전기설비")
        assert db.get_kakao_user(site_db, "k1")["owner_name"] == "박전기"

    def test_upsert_updates(self, site_db):
        db.upsert_kakao_user(site_db, "k1", "박전기", "전기설비")
        db.upsert_kakao_user(site_db, "k1", "박전기", "소방설비")
        assert db.get_kakao_user(site_db, "k1")["discipline"] == "소방설비"

    def test_get_missing_returns_none(self, site_db):
        assert db.get_kakao_user(site_db, "ghost") is None

    def test_list(self, site_db):
        db.upsert_kakao_user(site_db, "k1", "a", "건축")
        db.upsert_kakao_user(site_db, "k2", "b", "토목")
        assert len(db.list_kakao_users(site_db)) == 2
