# Smart Node-Scheduler v0.1

Python-based MEP schedule assistant MVP.

Current scope:

- Core dataclasses
- SQLite `.scheduler` project storage
- CRUD tests
- pyCritical import smoke test
- NetworkX fallback CPM skeleton

## Environment Gate

This project must be developed and verified with Python `>=3.11,<3.13`.
Python 3.14 or Python 2.7 test results are not acceptance evidence for this
repository.

Windows setup:

```powershell
py -0p
where.exe python
where.exe py

py -3.12 --version
py -3.12 -m venv .venv

.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

If Python 3.12 is unavailable, install Python 3.12.10 64-bit or Python 3.11.9
64-bit, then recreate `.venv`.

Do not add `python>=3.11` to `requirements.txt`; runtime version limits belong
in `pyproject.toml` as `requires-python`.

## Next Gate

Before Week 1 development:

1. Install Python 3.12.10 64-bit or Python 3.11.9 64-bit.
2. Create `.venv` with `py -3.12 -m venv .venv`.
3. Install dependencies with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
4. Run `.\.venv\Scripts\python.exe -m pip check`.
5. Run `.\.venv\Scripts\python.exe -m pytest -q`.
6. Confirm the pyCritical smoke test is not skipped.
7. Add and pass pyCritical Golden Tests for FS, FS + Lag, SS, FF, parallel critical path, and cycle detection.

The current pyCritical smoke test may skip only while the acceptance `.venv` is
not yet available. After Python 3.12/3.11 and dependencies are installed, a
skip is a failed environment verification.
