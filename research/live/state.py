"""Small runtime-state store (consecutive API errors, last run, etc.).

Every writer here does read-modify-write on the file so that concurrent
concerns within one run do not clobber each other: `reset_api_errors` /
`bump_api_errors` own `consecutive_api_errors`, while the daily loop owns
`last_run` / `last_equity`. A writer that rebuilt the whole dict from a copy
it read earlier in the run would silently revert the others' updates -- which
is exactly the bug this module is shaped to avoid.
"""

import json
from pathlib import Path

RUNTIME_PATH = Path(__file__).resolve().parent / "RUNTIME_STATE.json"


def read_runtime(path: Path = None):
    p = Path(path or RUNTIME_PATH)
    if not p.exists():
        return {"consecutive_api_errors": 0}
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {"consecutive_api_errors": 0}


def write_runtime(state, path: Path = None):
    Path(path or RUNTIME_PATH).write_text(
        json.dumps(state, indent=2, default=str))


def update_runtime(path: Path = None, **fields):
    """Merge `fields` into the persisted state, leaving every other key as it
    is on disk right now. Use this instead of write_runtime() whenever the run
    has only computed some of the keys -- it picks up whatever
    reset_api_errors / bump_api_errors wrote during the same run.
    """
    s = read_runtime(path)
    s.update(fields)
    write_runtime(s, path)
    return s


def bump_api_errors(path: Path = None):
    s = read_runtime(path)
    s["consecutive_api_errors"] = int(s.get("consecutive_api_errors", 0)) + 1
    write_runtime(s, path)
    return s["consecutive_api_errors"]


def reset_api_errors(path: Path = None):
    s = read_runtime(path)
    s["consecutive_api_errors"] = 0
    write_runtime(s, path)
