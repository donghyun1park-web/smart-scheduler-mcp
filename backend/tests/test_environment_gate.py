from __future__ import annotations

import sys


def test_python_version_is_supported() -> None:
    assert (3, 11) <= sys.version_info[:2] < (3, 13), (
        "Smart Node-Scheduler acceptance tests must run on "
        "Python >=3.11,<3.13. "
        f"Current version: {sys.version}"
    )
