from __future__ import annotations

from datetime import date

import pytest

from core.validation import (
    ValidationError,
    optional_float,
    optional_text,
    require_choice,
    require_int,
    require_iso_date,
    require_text,
)


def test_require_text_strips_and_rejects_empty():
    assert require_text("  hi  ", "f") == "hi"
    with pytest.raises(ValidationError):
        require_text(None, "f")
    with pytest.raises(ValidationError):
        require_text("   ", "f")


def test_require_text_enforces_max_length():
    with pytest.raises(ValidationError):
        require_text("abcdef", "f", max_length=3)


def test_optional_text_defaults():
    assert optional_text(None) == ""
    assert optional_text("  ", default="x") == "x"
    assert optional_text(" foo ") == "foo"


def test_require_int_accepts_strings_and_numbers():
    assert require_int("3", "f") == 3
    assert require_int(3.0, "f") == 3
    with pytest.raises(ValidationError):
        require_int("not a number", "f")
    with pytest.raises(ValidationError):
        require_int(None, "f")
    with pytest.raises(ValidationError):
        require_int(True, "f")


def test_require_int_bounds():
    with pytest.raises(ValidationError):
        require_int(-1, "f", minimum=0)
    with pytest.raises(ValidationError):
        require_int(10, "f", maximum=5)


def test_optional_float():
    assert optional_float(None, "f") == 0.0
    assert optional_float("", "f", default=1.5) == 1.5
    assert optional_float("2.5", "f") == 2.5
    with pytest.raises(ValidationError):
        optional_float("bad", "f")


def test_require_iso_date():
    assert require_iso_date("2026-05-20", "f") == date(2026, 5, 20)
    assert require_iso_date(date(2026, 5, 20), "f") == date(2026, 5, 20)
    with pytest.raises(ValidationError):
        require_iso_date("2026/05/20", "f")
    with pytest.raises(ValidationError):
        require_iso_date(None, "f")


def test_require_choice():
    assert require_choice("FS", "rel", ["FS", "SS", "FF"]) == "FS"
    with pytest.raises(ValidationError):
        require_choice("SF", "rel", ["FS", "SS", "FF"])
