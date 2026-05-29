from __future__ import annotations

import pytest

from core.disciplines import (
    DEFAULT_CONSTRUCTION_DISCIPLINES,
    DEFAULT_MEP_DISCIPLINES,
    normalize_discipline,
    validate_discipline,
)
from core.models import Activity


def test_existing_mep_and_v2_construction_disciplines_are_allowed():
    for value in DEFAULT_MEP_DISCIPLINES | DEFAULT_CONSTRUCTION_DISCIPLINES:
        assert validate_discipline(value) == value


def test_english_aliases_normalize_to_korean_standard_disciplines():
    assert normalize_discipline("civil") == "토목"
    assert normalize_discipline("architecture") == "건축"
    assert normalize_discipline("mechanical") == "기계설비"
    assert normalize_discipline("fire_protection") == "소방설비"
    assert normalize_discipline("electrical") == "전기설비"
    assert normalize_discipline("common") == "공통"


def test_activity_normalizes_discipline_alias_on_creation():
    activity = Activity("a", "A", "Activity", "wbs", "civil", "B1", 1)

    assert activity.discipline == "토목"


def test_unsupported_discipline_raises_clear_error():
    with pytest.raises(ValueError, match="Unsupported discipline"):
        validate_discipline("landscape")
