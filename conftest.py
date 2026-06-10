"""Pytest root config — src/backend을 import 경로에 추가.

v3.4 폴더 재구성 후:
  tests/ 가 루트에 있고 src/backend/{core,tools}/ 가 비스니스 코드.
  conftest.py로 sys.path에 src/backend을 추가하여 `from core.X import Y` 사용 가능.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "src" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
