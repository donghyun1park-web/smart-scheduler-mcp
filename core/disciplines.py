from __future__ import annotations


DEFAULT_MEP_DISCIPLINES = frozenset({"위생", "공조", "소방", "전기", "자동제어", "공통"})
DEFAULT_CONSTRUCTION_DISCIPLINES = frozenset({"토목", "건축", "기계설비", "소방설비", "전기설비", "공통"})
ALLOWED_DISCIPLINES = DEFAULT_MEP_DISCIPLINES | DEFAULT_CONSTRUCTION_DISCIPLINES

DISCIPLINE_ALIASES = {
    "civil": "토목",
    "architecture": "건축",
    "architectural": "건축",
    "building": "건축",
    "mechanical": "기계설비",
    "mep_mechanical": "기계설비",
    "fire": "소방설비",
    "fire_protection": "소방설비",
    "electrical": "전기설비",
    "electric": "전기설비",
    "common": "공통",
}


def normalize_discipline(value: str) -> str:
    normalized = value.strip()
    return DISCIPLINE_ALIASES.get(normalized.lower(), normalized)


def validate_discipline(value: str) -> str:
    normalized = normalize_discipline(value)
    if normalized not in ALLOWED_DISCIPLINES:
        allowed = ", ".join(sorted(ALLOWED_DISCIPLINES))
        raise ValueError(f"Unsupported discipline: {value}. Allowed: {allowed}")
    return normalized
