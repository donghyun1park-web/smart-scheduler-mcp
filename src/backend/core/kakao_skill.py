"""카카오 i 오픈빌더 스킬서버 요청/응답 처리 (v3.6).

오픈빌더 → 스킬서버 요청(payload)에서 필요한 정보를 추출하고,
SkillResponse v2.0 규격의 응답 JSON을 만든다.

참고: https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/make_skill
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# 이미지 보안전송 플러그인 URL 유효시간이 10분이므로 수신 즉시 다운로드해야 한다.
SECURE_IMAGE_TTL_MINUTES = 10


@dataclass(frozen=True)
class SkillPayload:
    """스킬 요청에서 추출한 핵심 필드."""

    bot_user_key: str = ""
    utterance: str = ""
    image_urls: tuple[str, ...] = ()
    callback_url: str = ""
    params: dict[str, Any] = field(default_factory=dict)


def parse_skill_payload(body: dict[str, Any]) -> SkillPayload:
    """오픈빌더 스킬 요청 JSON → SkillPayload.

    이미지 보안전송 플러그인(@sys.plugin.secureimage)의 값은
    ``"List(url1, url2)"`` 형태 문자열 또는 URL 문자열로 들어온다.
    """
    user_request = body.get("userRequest") or {}
    user = user_request.get("user") or {}
    action = body.get("action") or {}
    params: dict[str, Any] = action.get("params") or {}

    bot_user_key = str(user.get("id") or (user.get("properties") or {}).get("botUserKey") or "")
    utterance = str(user_request.get("utterance") or "").strip()
    callback_url = str(user_request.get("callbackUrl") or "")

    image_urls: list[str] = []
    for value in params.values():
        image_urls.extend(_extract_urls(value))

    return SkillPayload(
        bot_user_key=bot_user_key,
        utterance=utterance,
        image_urls=tuple(image_urls),
        callback_url=callback_url,
        params=params,
    )


def _extract_urls(value: Any) -> list[str]:
    """파라미터 값에서 http(s) URL을 모두 추출. List(...) 래퍼 지원."""
    if not isinstance(value, str):
        return []
    text = value.strip()
    # "List(url1, url2)" 래퍼 제거
    m = re.fullmatch(r"List\((.*)\)", text, re.DOTALL)
    if m:
        text = m.group(1)
    return re.findall(r"https?://[^\s,\"')]+", text)


# ─── SkillResponse v2.0 빌더 ─────────────────────────────────────────────────

def build_simple_text(text: str) -> dict[str, Any]:
    """단순 텍스트 응답."""
    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": text}}]},
    }


def build_text_card(
    title: str,
    description: str,
    *,
    buttons: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """텍스트 카드 응답 (제목/본문/버튼).

    buttons 예: [{"label": "웹앱 열기", "action": "webLink", "webLinkUrl": "https://..."}]
    """
    card: dict[str, Any] = {"title": title, "description": description}
    if buttons:
        card["buttons"] = buttons
    return {
        "version": "2.0",
        "template": {"outputs": [{"textCard": card}]},
    }


def build_callback_waiting(text: str = "확인 중입니다. 잠시만 기다려주세요...") -> dict[str, Any]:
    """AI 챗봇 콜백 응답 — 즉시 대기 문구를 보여주고 완료 후 callbackUrl로 결과 전송."""
    return {
        "version": "2.0",
        "useCallback": True,
        "data": {"text": text},
    }
