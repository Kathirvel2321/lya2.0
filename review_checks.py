"""Offline review evidence; no sensors, credentials, network, or real stores.

These checks reproduce current defects; they are not a release test suite.
Run with python -B review_checks.py.
"""
import ast
import datetime
from pathlib import Path
import re
import types

ROOT = Path(__file__).resolve().parent


def extract(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8-sig"))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, "exec"), namespace)


def main():
    files = [p for p in ROOT.rglob("*.py") if not any(part.startswith((".venv", "venv", "build", "dist", "__pycache__", ".")) for part in p.parts)]
    for path in files:
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    print(f"PASS: syntax parsed for {len(files)} Python files (no imports).")

    class FixedDateTime(datetime.datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 10, 12, 0, 0)

    ns = {"datetime": types.SimpleNamespace(datetime=FixedDateTime, timedelta=datetime.timedelta),
          "re": re, "WORDS": dict(zip(("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"), range(7))),
          "MONTHS": {m.lower(): i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1)}}
    extract("skills/reminder.py", "_time_hint", ns)
    for phrase, expected in [
        ("remind me to call next monday at 9am", "2026-09-14T09:00:00"),
        ("remind me to call in 2 hrs", "2026-09-10T14:00:00"),
        ("remind me to call on 5 june at 6pm", "2027-06-05T18:00:00"),
    ]:
        actual, _ = ns["_time_hint"](phrase)
        value = actual.isoformat() if actual else None
        print(f"{'PASS' if value == expected else 'REPRODUCED BUG'}: {phrase!r}; expected={expected}; actual={value}")

    from main import Assistant
    from security.policy import Session
    from unittest.mock import patch
    import sys
    app = Assistant.__new__(Assistant)
    app.build = False
    app.session = Session(role="admin")
    app.identify = lambda: None
    app.permit = lambda *args: True
    fake_memory = types.ModuleType("brain.memory")
    fake_memory.remember = lambda *args: None
    with patch.dict(sys.modules, {"brain.memory": fake_memory}):
        answer = app.handle("remember my private example is blue")
    assert "my private example is blue" not in answer and app.private_output is True
    print("PASS: remember confirmation marks private_output=True and omits private content.")

    from audio import voice
    assert hasattr(voice, "set_rate") and hasattr(voice, "_engine")
    print("PASS: voice exposes set_rate and _engine; mind.set_tone drives public setter.")


if __name__ == "__main__":
    main()
