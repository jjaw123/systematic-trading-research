"""Runtime-state store: concurrent writers within one run must not clobber
each other.

Regression: daily_loop used to end with write_runtime({**rt, ...}), rebuilding
the file from the dict it read at the top of the run. That silently reverted
reset_api_errors() and every mid-run bump_api_errors(), so a clean run left
yesterday's error count on disk and order-failure bumps never survived.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live import state  # noqa: E402


def test_update_runtime_merges_and_leaves_other_keys_alone(tmp_path):
    p = tmp_path / "RUNTIME_STATE.json"
    state.write_runtime({"consecutive_api_errors": 3, "last_equity": 100.0}, p)

    state.update_runtime(p, last_run="2026-08-27", last_equity=101.0)

    s = state.read_runtime(p)
    assert s["consecutive_api_errors"] == 3          # untouched
    assert s["last_run"] == "2026-08-27"
    assert s["last_equity"] == 101.0


def test_mid_run_bump_survives_the_end_of_run_write(tmp_path):
    p = tmp_path / "RUNTIME_STATE.json"
    # start of run: loop reads state
    state.write_runtime({"consecutive_api_errors": 0}, p)
    _ = state.read_runtime(p)                        # the stale copy `rt`
    # ... data fetch ok -> reset ...
    state.reset_api_errors(p)
    # ... two order submissions fail mid-loop ...
    state.bump_api_errors(p)
    n = state.bump_api_errors(p)
    assert n == 2
    # end of run: loop persists last_run / last_equity
    state.update_runtime(p, last_run="2026-08-27", last_equity=99_000.0)

    s = state.read_runtime(p)
    assert s["consecutive_api_errors"] == 2          # NOT reverted to the stale 0
    assert s["last_equity"] == 99_000.0


def test_clean_run_keeps_the_reset(tmp_path):
    p = tmp_path / "RUNTIME_STATE.json"
    state.write_runtime({"consecutive_api_errors": 4, "last_equity": 1.0}, p)
    _ = state.read_runtime(p)                        # stale copy with 4
    state.reset_api_errors(p)                        # data fetch succeeded
    state.update_runtime(p, last_run="2026-08-27", last_equity=2.0)

    assert state.read_runtime(p)["consecutive_api_errors"] == 0


def test_read_runtime_tolerates_missing_and_corrupt_files(tmp_path):
    p = tmp_path / "RUNTIME_STATE.json"
    assert state.read_runtime(p) == {"consecutive_api_errors": 0}
    p.write_text("{ not json")
    assert state.read_runtime(p) == {"consecutive_api_errors": 0}
