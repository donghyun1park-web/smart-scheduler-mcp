from __future__ import annotations

import importlib


def test_viewer_app_imports_without_side_effects():
    module = importlib.import_module("viewer.app")

    assert hasattr(module, "main")
