"""Kill-switch tests. A safety device that isn't tested is decoration."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live import halt  # noqa: E402


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    """Never touch the real log/state files during tests."""
    monkeypatch.setattr(halt, "LOG_PATH", tmp_path / "log.jsonl")
    monkeypatch.setattr(halt, "STATE_PATH", tmp_path / "state.json")
    return tmp_path


def stream(n, mu, seed=0, expo=1.0):
    idx = pd.bdate_range("2027-01-04", periods=n)
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"net_return": mu + 0.01 * rng.standard_normal(n),
                         "gross_exposure": expo}, index=idx)


def market_for(live, mu=0.0004, seed=99):
    rng = np.random.default_rng(seed)
    return pd.Series(mu + 0.01 * rng.standard_normal(len(live)), index=live.index)


# ---- Rule 2: drawdown ------------------------------------------------------

def test_halts_when_drawdown_breaches_multiple():
    live = stream(120, -0.006)                   # steady bleed past 1.2x worst
    res = halt.run_daily_check(live, market_for(live))
    assert res.status == "HALT"
    assert any("drawdown" in r for r in res.reasons)
    assert halt.read_state()["halted"] is True
    allowed, msg = halt.entries_allowed()
    assert allowed is False and "HALTED" in msg


def test_warns_at_backtest_worst_without_halting():
    cfg, _ = halt.load_rules()
    worst = cfg["drawdown_test"]["worst_backtest_drawdown"]
    n = 40
    live = stream(n, 0.0)
    # engineer a drawdown between 1.0x and 1.2x of backtest worst
    target = -(worst * 1.1)
    live["net_return"] = 0.0
    live.iloc[-1, live.columns.get_loc("net_return")] = target
    res = halt.run_daily_check(live, market_for(live))
    assert res.status == "WARN"
    assert halt.read_state()["halted"] is False   # warn does not block entries
    assert halt.entries_allowed()[0] is True


# ---- Rule 1: random-entry skill test ---------------------------------------

def test_halts_when_worse_than_random_entries():
    idx = pd.bdate_range("2027-01-04", periods=300)
    rng = np.random.default_rng(3)
    mkt = pd.Series(0.0006 + 0.01 * rng.standard_normal(300), index=idx)
    # Always invested but returning market MINUS a persistent drag. There is
    # no entry timing to judge here, so this must halt on the SHORTFALL path
    # (drag/cost/tracking), not on a percentile of a collapsed null.
    live = pd.DataFrame({"net_return": mkt.values - 0.0016,
                         "gross_exposure": 1.0}, index=idx)
    res = halt.run_daily_check(live, mkt)
    assert res.status == "HALT"
    assert any("trails a matched" in r for r in res.reasons)
    assert res.detail["skill"]["w252"]["status"] == "halt_on_shortfall_null_too_tight"


def test_normal_performance_passes():
    idx = pd.bdate_range("2027-01-04", periods=300)
    rng = np.random.default_rng(5)
    mkt = pd.Series(0.0005 + 0.01 * rng.standard_normal(300), index=idx)
    live = pd.DataFrame({"net_return": mkt.values + 0.0004,
                         "gross_exposure": 1.0}, index=idx)
    res = halt.run_daily_check(live, mkt)
    assert res.status == "OK"
    assert halt.entries_allowed()[0] is True


def test_short_history_does_not_trigger_skill_test():
    live = stream(30, -0.002)
    res = halt.run_daily_check(live, market_for(live))
    assert all("percentile" not in r for r in res.reasons)
    assert res.detail["skill"]["w63"]["status"] == "insufficient_history"


# ---- Immutability / fail-closed properties ---------------------------------

def test_halt_does_not_clear_itself_on_recovery():
    bad = stream(120, -0.006)
    assert halt.run_daily_check(bad, market_for(bad)).status == "HALT"
    idx = pd.bdate_range("2027-06-01", periods=300)
    rng = np.random.default_rng(11)
    mkt = pd.Series(0.0005 + 0.01 * rng.standard_normal(300), index=idx)
    good = pd.DataFrame({"net_return": mkt.values + 0.0006,
                         "gross_exposure": 1.0}, index=idx)
    res = halt.run_daily_check(good, mkt)          # strategy recovers fully
    assert res.status == "OK"                       # today's check is clean...
    assert halt.read_state()["halted"] is True      # ...but the halt STANDS
    assert halt.entries_allowed()[0] is False


def test_unreadable_rules_fail_closed(monkeypatch):
    monkeypatch.setattr(halt, "RULES_PATH", Path("/nonexistent/rules.yaml"))
    live = stream(100, 0.001)
    res = halt.run_daily_check(live, market_for(live))
    assert res.status == "ERROR"
    assert halt.read_state()["halted"] is True
    assert halt.entries_allowed()[0] is False


def test_malformed_rules_fail_closed(tmp_path, monkeypatch):
    bad = tmp_path / "bad.yaml"
    bad.write_text("skill_test: [this is not a mapping\n")
    monkeypatch.setattr(halt, "RULES_PATH", bad)
    live = stream(100, 0.001)
    res = halt.run_daily_check(live, market_for(live))
    assert res.status == "ERROR"
    assert halt.entries_allowed()[0] is False


def test_unreadable_state_fails_closed(sandbox):
    (sandbox / "state.json").write_text("{ this is not json")
    assert halt.entries_allowed()[0] is False


def test_every_check_logs_rules_hash_and_revision():
    live = stream(100, 0.0005)
    halt.run_daily_check(live, market_for(live))
    halt.run_daily_check(live, market_for(live))
    lines = [json.loads(x) for x in halt.LOG_PATH.read_text().splitlines()]
    assert len(lines) == 2                       # append-only: 2 checks, 2 lines
    for rec in lines:
        assert len(rec["rules_sha256"]) == 64
        assert rec["rules_revision"] >= 1


def test_checker_never_writes_rules_file():
    before = halt.RULES_PATH.read_bytes()
    live = stream(120, -0.006)
    halt.run_daily_check(live, market_for(live))   # a full HALT path
    assert halt.RULES_PATH.read_bytes() == before


def test_no_programmatic_resume_function_exists():
    # Clearing a halt must require editing HALT_STATE.json by hand with the
    # token from the rules file. If someone adds a resume helper, this fails.
    exported = {n for n in dir(halt) if not n.startswith("_")}
    for forbidden in ("resume", "clear_halt", "reset", "unhalt", "override"):
        assert forbidden not in exported


# ---- Power guards (rev 2): must not halt on a meaningless comparison -------

def test_no_halt_when_null_collapses(monkeypatch, tmp_path):
    """An always-invested book has no entry timing to judge. A 9bp shortfall
    against a point-mass null must never read as a 0th-percentile failure.
    This is the false HALT the 2001-2009 dry run produced before rev 2."""
    idx = pd.bdate_range("2027-01-04", periods=300)
    rng = np.random.default_rng(7)
    mkt = pd.Series(0.0006 + 0.01 * rng.standard_normal(300), index=idx)
    live = pd.DataFrame({"net_return": mkt.values - 0.000004,  # ~1bp/yr behind
                         "gross_exposure": 1.0}, index=idx)
    res = halt.run_daily_check(live, mkt)
    assert res.status != "HALT"
    assert res.detail["skill"]["w252"]["status"] == "within_noise_of_random"


def test_still_halts_on_a_material_shortfall():
    """The guards must not defang the rule: a real, large underperformance
    against a genuinely dispersed null still halts."""
    idx = pd.bdate_range("2027-01-04", periods=300)
    rng = np.random.default_rng(3)
    mkt = pd.Series(0.0006 + 0.01 * rng.standard_normal(300), index=idx)
    # in market ~55% of days (so the null has real spread), and badly timed
    expo = pd.Series((rng.random(300) < 0.55).astype(float), index=idx)
    live = pd.DataFrame({"net_return": expo.values * mkt.values - 0.0012,
                         "gross_exposure": expo.values}, index=idx)
    res = halt.run_daily_check(live, mkt)
    assert res.status == "HALT"
    assert any("percentile" in r for r in res.reasons)
