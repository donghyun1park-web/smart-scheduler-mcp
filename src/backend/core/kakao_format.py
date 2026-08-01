"""카카오톡 공유용 텍스트 포매터 (v3.6).

챗봇 응답·대시보드 "카톡 복사" 버튼·MCP tool(get_kakao_briefing)이 공용으로 사용.
카톡 특성에 맞춰 이모지 불릿 + 짧은 줄 + ~800자 이내로 유지한다.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from core import db
from core.dashboard import generate_site_briefing

_STATUS_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}

MAX_KAKAO_LEN = 800


def format_briefing_for_kakao(db_path: str | Path, *, as_of: date | None = None) -> str:
    """오늘 현장 브리핑 → 카톡 붙여넣기용 텍스트."""
    b = generate_site_briefing(db_path, as_of=as_of)
    today = b.get("as_of", date.today().isoformat())
    emoji = _STATUS_EMOJI.get(b.get("status_level", ""), "⚪")

    lines = [
        f"📋 {b.get('project_name', '현장')} 일일 브리핑",
        f"📅 {today}",
        "─" * 12,
        f"{emoji} 상태: {b.get('status', '-')}",
        f"📐 공정률: 실적 {b.get('overall_actual_pct', 0):.1f}% / 계획 {b.get('overall_planned_pct', 0):.1f}% ({b.get('progress_gap_pct', 0):+.1f}%p)",
        f"💰 기성률: {b.get('billing_rate_pct', 0):.1f}%",
    ]

    delayed = b.get("delayed_activities") or []
    if delayed:
        lines.append(f"⚠️ 부진공정 {len(delayed)}건:")
        for d in delayed[:3]:
            lines.append(f"  • {d.get('name', '')} ({d.get('gap_pct', 0):.0f}%p 지연)")

    alerts = b.get("alerts") or []
    if alerts:
        lines.append(f"🔔 경고 {len(alerts)}건:")
        for a in alerts[:3]:
            message = a.get("message", "") if isinstance(a, dict) else str(a)
            lines.append(f"  • {message}")

    text = "\n".join(lines)
    return text[:MAX_KAKAO_LEN]


def format_reminder_for_kakao(
    db_path: str | Path,
    *,
    base_url: str = "",
    as_of: date | None = None,
) -> str:
    """오늘 실적 미제출 공종 리마인더 → 카톡 붙여넣기용 텍스트.

    base_url: 모바일 입력 앱 주소 (예: "http://192.168.0.10:8501"). 비우면 링크 생략.
    """
    today = as_of or date.today()
    activities = db.list_activities(db_path)
    disciplines = sorted({a.discipline for a in activities if a.discipline})

    # 오늘 제출된 공종 집합
    submitted: set[str] = set()
    act_disc = {a.activity_id: a.discipline for a in activities}
    for act in activities:
        for rec in db.list_daily_records(db_path, activity_id=act.activity_id):
            if rec.work_date == today:
                submitted.add(act_disc.get(rec.activity_id, ""))
                break

    missing = [d for d in disciplines if d not in submitted]
    if not missing:
        return f"✅ {today.isoformat()} 전 공종 실적 제출 완료! 수고하셨습니다."

    lines = [
        f"⏰ 오늘({today.strftime('%m/%d')}) 실적 미제출 알림",
        "아직 입력 안 된 공종입니다. 퇴근 전 입력 부탁드립니다 🙏",
        "─" * 12,
    ]
    for d in missing:
        if base_url:
            lines.append(f"• {d} → {base_url}?discipline={d}")
        else:
            lines.append(f"• {d}")
    text = "\n".join(lines)
    return text[:MAX_KAKAO_LEN]
