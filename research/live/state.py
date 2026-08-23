"""Small runtime-state store (consecutive API errors, last run, etc.)."""

import json
from pathlib import Path

RUNTIME_PATH = Path(__file__).resolve().parent / "RUNTIME_STATE.json"


def read_runtime():
    if not RUNTIME_PATH.exists():
        return {"consecutive_api_errors": 0}
    try:
        return json.loads(RUNTIME_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {"consecutive_api_errors": 0}


def write_runtime(state):
    RUNTIME_PATH.write_text(json.dumps(state, indent=2, default=str))


def bump_api_errors():
    s = read_runtime()
    s["consecutive_api_errors"] = int(s.get("consecutive_api_errors", 0)) + 1
    write_runtime(s)
    return s["consecutive_api_errors"]


def reset_api_errors():
    s = read_runtime()
    s["consecutive_api_errors"] = 0
    write_runtime(s)
