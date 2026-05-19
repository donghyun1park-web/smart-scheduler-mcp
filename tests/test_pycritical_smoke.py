from __future__ import annotations

import importlib
import importlib.util

import pytest


def test_pycritical_package_is_importable_for_future_api_verification():
    # During the environment-gate phase this may skip because Python 3.12
    # and the venv are not installed yet. Once the acceptance venv exists,
    # pyCritical is a required v0.1 dependency and this test must pass.
    module_name = _find_pycritical_module_name()
    if module_name is None:
        pytest.skip("pycritical is not installed in this environment")

    module = importlib.import_module(module_name)

    assert module is not None


def _find_pycritical_module_name() -> str | None:
    for module_name in ("pyCritical", "pycritical"):
        if importlib.util.find_spec(module_name) is not None:
            return module_name
    return None
