from __future__ import annotations

import pytest

from core.cpm_pycritical import calculate_with_pycritical


def test_pycritical_fs_linear_chain():
    result = calculate_with_pycritical(
        [
            ("A", [], 3),
            ("B", [("A", "FS", 0)], 2),
            ("C", [("B", "FS", 0)], 4),
        ]
    )

    assert result.cycles_detected == []
    assert result.table.loc["A"].to_dict() == {
        "ES": 0.0,
        "EF": 3.0,
        "LS": 0.0,
        "LF": 3.0,
        "Slack": 0.0,
    }
    assert result.table.loc["B", "ES"] == 3.0
    assert result.table.loc["C", "EF"] == 9.0


def test_pycritical_fs_lag():
    result = calculate_with_pycritical(
        [
            ("A", [], 3),
            ("B", [("A", "FS", 2)], 2),
        ]
    )

    assert result.table.loc["B", "ES"] == 5.0
    assert result.table.loc["B", "EF"] == 7.0


def test_pycritical_ss_relationship():
    result = calculate_with_pycritical(
        [
            ("A", [], 4),
            ("B", [("A", "SS", 1)], 3),
        ]
    )

    assert result.table.loc["B", "ES"] == 1.0
    assert result.table.loc["B", "EF"] == 4.0


def test_pycritical_ff_relationship():
    result = calculate_with_pycritical(
        [
            ("A", [], 4),
            ("B", [("A", "FF", 1)], 2),
        ]
    )

    assert result.table.loc["B", "ES"] == 3.0
    assert result.table.loc["B", "EF"] == 5.0


def test_pycritical_parallel_path_identifies_float():
    result = calculate_with_pycritical(
        [
            ("A", [], 3),
            ("B", [("A", "FS", 0)], 3),
            ("C", [("A", "FS", 0)], 2),
            ("D", [("B", "FS", 0), ("C", "FS", 0)], 1),
        ]
    )

    assert result.table.loc["D", "EF"] == 7.0
    assert result.table.loc["A", "Slack"] == 0.0
    assert result.table.loc["B", "Slack"] == 0.0
    assert result.table.loc["C", "Slack"] == 1.0
    assert result.table.loc["D", "Slack"] == 0.0


def test_pycritical_adapter_detects_cycle_before_calling_pycritical():
    result = calculate_with_pycritical(
        [
            ("A", [("C", "FS", 0)], 1),
            ("B", [("A", "FS", 0)], 1),
            ("C", [("B", "FS", 0)], 1),
        ]
    )

    assert result.table is None
    assert result.cycles_detected == [["A", "B", "C", "A"]]


def test_pycritical_adapter_rejects_sf_for_v01():
    with pytest.raises(ValueError, match="Unsupported relationship type"):
        calculate_with_pycritical(
            [
                ("A", [], 1),
                ("B", [("A", "SF", 0)], 1),
            ]
        )
