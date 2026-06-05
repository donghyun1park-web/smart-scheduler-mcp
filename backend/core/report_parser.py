"""공사일보 자동 파싱 — 이미지(Vision AI) 또는 Excel.

두 가지 입력 경로:
  1. parse_report_image(bytes, mime)  → Claude Vision API
  2. parse_report_excel(bytes)        → openpyxl 직접 파싱 (양식 고정 위치 기반)

반환 형식 (ParsedReport dict):
  {
    "work_date":  "2024-04-25",
    "team_name":  "설비팀",
    "work_items": [{"no":1, "category":"호출", "team":"협력사", "description":"..."}],
    "equipment":  [{"no":1, "name":"엘리베이터", "current_qty":601, "used_qty":3, "final_qty":598}],
    "supplies":   [{"no":1, "name":"형광등6W",  "current_qty":80,  "used_qty":2, "final_qty":78}],
    "summary":    "작업현황 한줄 요약",
    "warnings":   []   # 파싱 중 문제 목록
  }
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
from datetime import date
from typing import Any

# ─── 추출 프롬프트 ─────────────────────────────────────────────────────────────
_EXTRACT_PROMPT = """\
이 공사일보(건설현장 일일 현황 보고서) 이미지에서 아래 JSON 형식으로 데이터를 추출하세요.

규칙:
- 날짜는 YYYY-MM-DD 형식
- 수량은 정수 (없으면 0)
- 빈 셀/읽을 수 없는 값은 null
- 설명·팀명·항목명은 한국어 그대로
- JSON 코드블록만 반환 (설명 없이)

```json
{
  "work_date": "YYYY-MM-DD",
  "team_name": "팀명 또는 협력사명",
  "work_items": [
    {"no": 1, "category": "카테고리", "team": "팀명", "description": "작업내용"}
  ],
  "equipment": [
    {"no": 1, "name": "장비명", "current_qty": 0, "used_qty": 0, "final_qty": 0}
  ],
  "supplies": [
    {"no": 1, "name": "물품명", "current_qty": 0, "used_qty": 0, "final_qty": 0}
  ],
  "summary": "전체 작업 한줄 요약"
}
```
"""

# ─── 이미지 파싱 — 프로바이더 디스패처 ──────────────────────────────────────────

# 환경변수로 선택 (기본값: gemini — 무료 티어 + 최저가)
_PROVIDER = os.environ.get("VISION_PROVIDER", "gemini").lower()


def parse_report_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> dict[str, Any]:
    """카메라 사진 → Vision AI → 구조화 dict.

    VISION_PROVIDER 환경변수로 프로바이더 선택:
      gemini (기본값) — GEMINI_API_KEY 필요, 무료 티어 제공
      claude          — ANTHROPIC_API_KEY 필요
    """
    provider = os.environ.get("VISION_PROVIDER", _PROVIDER)
    if provider == "gemini":
        return _call_gemini_vision(image_bytes, mime_type)
    elif provider == "claude":
        return _call_claude_vision(image_bytes, mime_type)
    else:
        raise RuntimeError(
            f"지원하지 않는 VISION_PROVIDER: '{provider}'. "
            "'gemini' 또는 'claude'로 설정하세요."
        )


def _call_gemini_vision(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    """Gemini Vision API 호출 (google-genai 신규 SDK).

    GEMINI_API_KEY 환경변수 필요.
    무료 티어: 15 RPM / 1,500 RPD (일 1,500장 무료).
    비용: ~$0.0003/장 (유료 전환 시).
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError as e:
        raise RuntimeError(
            "google-genai 패키지 필요: pip install google-genai"
        ) from e

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "https://aistudio.google.com 에서 무료 발급 가능."
        )

    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    client = genai.Client(api_key=api_key)

    image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    text_part  = genai_types.Part.from_text(text=_EXTRACT_PROMPT)

    response = client.models.generate_content(
        model=model_name,
        contents=[image_part, text_part],
    )
    return _parse_json_response(response.text)


def _call_claude_vision(
    image_bytes: bytes,
    mime_type: str,
    *,
    model: str = "claude-3-5-haiku-20241022",
) -> dict[str, Any]:
    """Claude Vision API 호출.

    ANTHROPIC_API_KEY 환경변수 필요.
    비용: ~$0.003/장.
    """
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("anthropic 패키지 필요: pip install anthropic") from e

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=api_key)
    b64 = base64.standard_b64encode(image_bytes).decode()

    msg = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": b64,
                    },
                },
                {"type": "text", "text": _EXTRACT_PROMPT},
            ],
        }],
    )

    raw = msg.content[0].text.strip()
    return _parse_json_response(raw)


# ─── Excel 파싱 (고정 위치 기반) ──────────────────────────────────────────────
# 양식: ★표준 출력일보 샘플_설비팀 구조에 맞춤
#   작업일: row 5, col 3 (C5)
#   팀체크: row 5, col 4 (D5)
#   작업현황 테이블: row 8~27, cols B-H
#   설비현황 테이블: row 20~40, cols I-N (NO, 장명, 현황, 사용, 최종)
#   물품현황 테이블: row 43~47

def parse_report_excel(file_bytes: bytes) -> dict[str, Any]:
    """Excel 공사일보 → 구조화 dict.

    openpyxl로 고정 위치 셀을 읽어 파싱한다.
    """
    try:
        import openpyxl
    except ImportError as e:
        raise RuntimeError("openpyxl 패키지 필요: pip install openpyxl") from e

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active
    warnings: list[str] = []

    def cell(row: int, col: int) -> Any:
        return ws.cell(row=row, column=col).value

    def safe_int(v: Any) -> int | None:
        if v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    def safe_str(v: Any) -> str:
        return str(v).strip() if v is not None else ""

    # ── 날짜 (row 5 cols 3~6 병합 셀 검색) ────────────────────────────────
    work_date_raw = None
    for col in range(1, 15):
        v = cell(5, col)
        if v and ("2024" in str(v) or "2025" in str(v) or "2026" in str(v)):
            work_date_raw = str(v)
            break

    work_date = _parse_date(work_date_raw)
    if not work_date:
        warnings.append(f"날짜 파싱 실패: {work_date_raw!r}")
        work_date = date.today().isoformat()

    # ── 팀명 ──────────────────────────────────────────────────────────────
    team_name = ""
    for col in range(1, 15):
        v = cell(4, col)
        if v and "팀" in str(v) and len(str(v)) < 20:
            team_name = safe_str(v).replace("팀 체 크 :", "").strip()
            break

    # ── 작업현황 테이블 (rows 8~27) ───────────────────────────────────────
    work_items: list[dict] = []
    for row in range(8, 28):
        no_val = safe_str(cell(row, 1))
        cat    = safe_str(cell(row, 2)) or safe_str(cell(row, 3))
        team   = safe_str(cell(row, 4))
        desc   = " ".join(
            safe_str(cell(row, c)) for c in range(5, 9)
        ).strip()
        if any([cat, team, desc]):
            work_items.append({
                "no": len(work_items) + 1,
                "category": cat,
                "team": team,
                "description": desc,
            })

    # ── 설비현황 테이블 (rows 20~40, cols 9~14) ────────────────────────────
    equipment: list[dict] = []
    for row in range(20, 41):
        name = safe_str(cell(row, 10)) or safe_str(cell(row, 11))
        c_q  = safe_int(cell(row, 12))
        u_q  = safe_int(cell(row, 13))
        f_q  = safe_int(cell(row, 14))
        if name:
            equipment.append({
                "no": len(equipment) + 1,
                "name": name,
                "current_qty": c_q or 0,
                "used_qty": u_q or 0,
                "final_qty": f_q or 0,
            })

    # ── 물품현황 테이블 (rows 43~47) ──────────────────────────────────────
    supplies: list[dict] = []
    for row in range(43, 48):
        name = safe_str(cell(row, 10)) or safe_str(cell(row, 11))
        c_q  = safe_int(cell(row, 12))
        u_q  = safe_int(cell(row, 13))
        f_q  = safe_int(cell(row, 14))
        if name:
            supplies.append({
                "no": len(supplies) + 1,
                "name": name,
                "current_qty": c_q or 0,
                "used_qty": u_q or 0,
                "final_qty": f_q or 0,
            })

    # ── 요약 ──────────────────────────────────────────────────────────────
    desc_texts = [w["description"] for w in work_items if w["description"]]
    summary = desc_texts[0] if desc_texts else "작업 상세 없음"

    return {
        "work_date": work_date,
        "team_name": team_name,
        "work_items": work_items,
        "equipment": equipment,
        "supplies": supplies,
        "summary": summary,
        "warnings": warnings,
    }


# ─── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _parse_json_response(raw: str) -> dict[str, Any]:
    """Claude 응답에서 JSON 추출 및 파싱."""
    warnings: list[str] = []

    # 코드 블록 제거
    text = raw
    if "```" in text:
        parts = text.split("```")
        # "```json ... ```" 패턴
        for part in parts[1::2]:
            cleaned = part.lstrip("json").strip()
            if cleaned.startswith("{"):
                text = cleaned
                break

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # 마지막 수단: 정규식으로 JSON 객체 찾기
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                result = {}
                warnings.append("JSON 파싱 실패 — 수동 입력 필요")
        else:
            result = {}
            warnings.append("JSON 파싱 실패 — 수동 입력 필요")

    result.setdefault("warnings", [])
    result["warnings"].extend(warnings)

    # 날짜 정규화
    if result.get("work_date"):
        parsed = _parse_date(result["work_date"])
        if parsed:
            result["work_date"] = parsed
        else:
            result["warnings"].append(f"날짜 형식 불명확: {result['work_date']!r}")
            result["work_date"] = date.today().isoformat()

    # 리스트 필드 기본값
    result.setdefault("work_items", [])
    result.setdefault("equipment", [])
    result.setdefault("supplies", [])
    result.setdefault("summary", "")

    return result


def _parse_date(raw: str | None) -> str | None:
    """다양한 날짜 형식 → YYYY-MM-DD."""
    if not raw:
        return None
    raw = str(raw).strip()

    # YYYY.MM.DD or YYYY-MM-DD
    m = re.search(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", raw)
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        return f"{y}-{mo}-{d}"

    # YYYY년 MM월 DD일
    m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", raw)
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        return f"{y}-{mo}-{d}"

    return None


def parsed_report_to_remarks(parsed: dict[str, Any]) -> str:
    """파싱 결과 → DailyRecord.remarks 문자열."""
    lines = []
    if parsed.get("team_name"):
        lines.append(f"[{parsed['team_name']}]")
    if parsed.get("summary"):
        lines.append(parsed["summary"])
    items = parsed.get("work_items", [])
    for item in items[:5]:  # 최대 5개
        desc = item.get("description", "")
        if desc:
            lines.append(f"  • {desc}")
    return "\n".join(lines)
