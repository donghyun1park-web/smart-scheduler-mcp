"""카카오톡 챗봇 발화 해석 → 실적 저장/브리핑 (v3.6).

라우팅:
  "등록 <공종> <이름>"       → 발신자(botUserKey)와 담당자 매핑 저장
  "현황" / "브리핑"          → 오늘 브리핑 텍스트
  일보 사진 첨부              → Vision AI 파싱(report_parser 재사용) → daily_record 저장
  "<활동키워드> NN% N명 ..."  → 텍스트 한 줄 실적 저장
  그 외                       → 도움말

기존 코드 재사용:
  core.report_parser.parse_report_image()  — 일보 사진 AI 파싱
  core.report_parser.parsed_report_to_remarks()
  core.db.create_daily_record()            — 저장
  core.kakao_format.format_briefing_for_kakao()
"""
from __future__ import annotations

import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import requests

from core import db
from core.kakao_format import format_briefing_for_kakao
from core.labor import save_parsed_labor
from core.models import DailyRecord
from core.report_parser import (
    parse_labor_report_image,
    parse_report_image,
    parsed_report_to_remarks,
)

HELP_TEXT = (
    "🤖 사용법 안내\n"
    "─────────\n"
    "📷 공사일보 사진 → AI가 읽어서 자동 저장\n"
    "👷 출역일보는 \"출역\" 붙여서 사진 전송 → 직종별 인원 저장\n"
    "✏️ 텍스트 보고: \"위생배관 70% 8명\"\n"
    "📊 \"현황\" → 오늘 브리핑\n"
    "🙋 최초 1회 등록: \"등록 기계설비 김기계\""
)

# "위생배관 70% 8명 자재 도착" — 활동키워드 + 진행률 + (인원) + (메모)
_TEXT_REPORT_RE = re.compile(
    r"^(?P<keyword>[가-힣A-Za-z0-9\s]+?)\s+(?P<pct>\d{1,3})\s*%(?:\s+(?P<workers>\d{1,3})\s*명)?(?:\s+(?P<remarks>.+))?$"
)

_REGISTER_RE = re.compile(r"^등록\s+(?P<discipline>\S+)\s+(?P<name>\S+)$")


def handle_utterance(
    db_path: str | Path,
    *,
    bot_user_key: str,
    utterance: str,
    image_urls: tuple[str, ...] = (),
    work_date: date | None = None,
) -> str:
    """발화 1건 처리 → 카톡 응답 텍스트 반환."""
    today = work_date or date.today()
    utterance = (utterance or "").strip()

    # 1) 등록
    m = _REGISTER_RE.match(utterance)
    if m:
        db.upsert_kakao_user(db_path, bot_user_key, m.group("name"), m.group("discipline"))
        return (
            f"✅ 등록 완료!\n{m.group('discipline')} 담당 {m.group('name')}님, 반갑습니다.\n\n"
            "이제 일보 사진을 보내거나 \"위생배관 70% 8명\" 처럼 보고하세요."
        )

    user = db.get_kakao_user(db_path, bot_user_key)

    # 2) 브리핑
    if utterance in ("현황", "브리핑", "오늘", "상황"):
        return format_briefing_for_kakao(db_path, as_of=today)

    # 3) 사진 — 출역일보(직종별 인원) vs 공사일보(작업) 분기
    if image_urls:
        if _is_labor_report(utterance):
            return _handle_labor_images(db_path, image_urls, user=user)
        return _handle_report_images(db_path, image_urls, user=user, today=today)

    # 4) 텍스트 한 줄 보고
    m = _TEXT_REPORT_RE.match(utterance)
    if m:
        return _handle_text_report(db_path, m, user=user, today=today)

    # 5) 도움말
    prefix = "" if user else "⚠️ 아직 미등록 사용자입니다.\n\"등록 <공종> <이름>\" 으로 먼저 등록하세요.\n\n"
    return prefix + HELP_TEXT


# ─── 내부 처리 ────────────────────────────────────────────────────────────────

_LABOR_KEYWORDS = ("출역", "인원", "출력인원", "노무")


def _is_labor_report(utterance: str) -> bool:
    return any(kw in utterance for kw in _LABOR_KEYWORDS)


def _handle_labor_images(
    db_path: str | Path,
    image_urls: tuple[str, ...],
    *,
    user: dict[str, str] | None,
) -> str:
    """출역일보 사진 → 직종별 인원 파싱 → labor_records 저장."""
    try:
        image_bytes = _download_image(image_urls[0])
    except Exception as e:
        return f"❌ 사진 다운로드 실패: {e}\n다시 보내주세요. (이미지 링크는 10분만 유효합니다)"

    try:
        parsed = parse_labor_report_image(image_bytes)
    except Exception as e:
        return f"❌ AI 파싱 실패: {e}"

    discipline = (user or {}).get("discipline", "")
    result = save_parsed_labor(db_path, parsed, discipline=discipline, dry_run=False)
    if not result.get("ok"):
        return (
            "⚠️ 출역일보는 읽었지만 직종별 인원을 인식하지 못했습니다.\n"
            f"사유: {result.get('error', '-')}\n웹앱에서 직접 입력해주세요."
        )

    top = sorted(parsed.get("labor", []), key=lambda x: -int(x.get("today") or 0))[:5]
    lines = "\n".join(f"  • {r['trade']} {r['today']}명" for r in top if int(r.get("today") or 0) > 0)
    foreign = parsed.get("foreign_count", 0)
    return (
        "✅ 출역일보 저장 완료!\n"
        "─────────\n"
        f"📅 {result['work_date']}\n"
        f"👷 금일 총 {result['total_headcount']}명 ({result['saved_count']}개 직종)\n"
        + (f"🌏 외국인 {foreign}명\n" if foreign else "")
        + lines
    )


def _handle_report_images(
    db_path: str | Path,
    image_urls: tuple[str, ...],
    *,
    user: dict[str, str] | None,
    today: date,
) -> str:
    """일보 사진 → Vision AI 파싱 → daily_record 저장 → 요약 응답."""
    try:
        image_bytes = _download_image(image_urls[0])
    except Exception as e:
        return f"❌ 사진 다운로드 실패: {e}\n다시 보내주세요. (이미지 링크는 10분만 유효합니다)"

    try:
        parsed = parse_report_image(image_bytes)
    except Exception as e:
        return f"❌ AI 파싱 실패: {e}"

    activity = _pick_activity(db_path, parsed.get("summary", ""), user)
    if activity is None:
        return (
            "⚠️ 일보는 읽었지만 연결할 공정 활동을 찾지 못했습니다.\n"
            f"팀: {parsed.get('team_name', '-')} / 요약: {parsed.get('summary', '-')}\n"
            "웹앱에서 활동을 지정해 저장해주세요."
        )

    workers = len(parsed.get("work_items") or [])
    record = DailyRecord(
        record_id=str(uuid.uuid4()),
        activity_id=activity.activity_id,
        work_date=date.fromisoformat(parsed.get("work_date") or today.isoformat()),
        planned_qty=100.0,
        actual_qty=0.0,  # 일보에는 진행률 미포함 — 텍스트 보고로 별도 갱신
        workers=workers,
        owner=(user or {}).get("owner_name", ""),
        remarks=parsed_report_to_remarks(parsed)[:500],
    )
    db.create_daily_record(db_path, record)

    warn = ""
    if parsed.get("warnings"):
        warn = "\n⚠️ " + " / ".join(str(w) for w in parsed["warnings"][:2])

    return (
        "✅ 공사일보 저장 완료!\n"
        "─────────\n"
        f"📅 작업일: {record.work_date.isoformat()}\n"
        f"🏷 활동: {activity.name}\n"
        f"👷 작업 {len(parsed.get('work_items') or [])}건 · 설비 {len(parsed.get('equipment') or [])}종\n"
        f"진행률은 \"{activity.name} 70%\" 처럼 별도 보고해주세요."
        + warn
    )


def _handle_text_report(
    db_path: str | Path,
    m: re.Match[str],
    *,
    user: dict[str, str] | None,
    today: date,
) -> str:
    """텍스트 한 줄 보고 → daily_record 저장."""
    keyword = m.group("keyword").strip()
    pct = min(int(m.group("pct")), 100)
    workers = int(m.group("workers") or 0)
    remarks = (m.group("remarks") or "").strip()

    activity = _pick_activity(db_path, keyword, user)
    if activity is None:
        return f"❌ '{keyword}' 와 일치하는 활동을 찾지 못했습니다.\n\"현황\" 으로 활동명을 확인하세요."

    record = DailyRecord(
        record_id=str(uuid.uuid4()),
        activity_id=activity.activity_id,
        work_date=today,
        planned_qty=100.0,
        actual_qty=float(pct),
        workers=workers,
        owner=(user or {}).get("owner_name", ""),
        remarks=remarks[:500],
    )
    db.create_daily_record(db_path, record)

    return (
        "✅ 실적 저장 완료!\n"
        "─────────\n"
        f"🏷 {activity.name}\n"
        f"📊 진행률 {pct}%"
        + (f" · 👷 {workers}명" if workers else "")
        + (f"\n📝 {remarks}" if remarks else "")
    )


def _pick_activity(db_path: str | Path, keyword: str, user: dict[str, str] | None):
    """키워드·담당 공종으로 활동 1건 매칭. 담당 공종 내 우선, 없으면 전체에서."""
    activities = db.list_activities(db_path)
    if not activities:
        return None

    discipline = (user or {}).get("discipline", "")
    tokens = [t for t in re.split(r"\s+", keyword) if t]

    def score(act) -> int:
        s = 0
        for t in tokens:
            if t and t in act.name:
                s += len(t)
        if discipline and act.discipline == discipline:
            s += 1
        return s

    best = max(activities, key=score)
    if score(best) <= (1 if discipline and best.discipline == discipline else 0):
        # 이름 매칭이 전혀 안 됐으면: 담당 공종의 진행중 활동 1건으로 폴백
        if discipline:
            mine = [a for a in activities if a.discipline == discipline]
            if len(mine) == 1:
                return mine[0]
        return None
    return best


def _download_image(url: str, *, timeout: int = 10) -> bytes:
    """보안전송 이미지 다운로드 (URL 10분 유효 — 즉시 호출)."""
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content
