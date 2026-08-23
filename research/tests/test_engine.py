"""Protocol-enforcement tests for the research backtesting engine."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import LookaheadError, TestDataViolation, run_backtest  # noqa: E402
from engine.data import _guard  # noqa: E402
from engine.metrics import pass_std_verdict  # noqa: E402
from engine.rules import ETF_BPS_PER_SIDE  # noqa: E402

SIDE = ETF_BPS_PER_SIDE / 1e4


def make_df(n=400, start="2010-01-04", drift=0.0002, seed=7, base=100.0):
    idx = pd.bdate_range(start, periods=n)
    rng = np.random.default_rng(seed)
    close = base * np.exp(np.cumsum(drift + 0.01 * rng.standard_normal(n)))
    open_ = np.concatenate([[base], close[:-1]]) * (1 + 0.001 * rng.standard_normal(n))
    return pd.DataFrame({
        "Open": open_, "High": np.maximum(open_, close) * 1.001,
        "Low": np.minimum(open_, close) * 0.999, "Close": close,
        "Volume": 1_000_000,
    }, index=idx)


def zero_rf(idx=None):
    return pd.Series(0.0, index=idx if idx is not None else pd.bdate_range("2009-01-01", "2023-01-01"))


# ---- Rule 1: TEST data is locked -------------------------------------------

def test_guard_rejects_test_period_rows():
    df = make_df(n=50, start="2022-12-01")  # runs into 2023
    assert df.index.max() >= pd.Timestamp("2023-01-01")
    with pytest.raises(TestDataViolation):
        _guard(df, "synthetic")


def test_guard_rejects_locked_directory_path():
    with pytest.raises(TestDataViolation):
        _guard(make_df(50), "research/data/test_locked/SPY.csv")


def test_engine_rejects_data_touching_2023():
    df = make_df(n=800, start="2020-01-01")
    with pytest.raises(TestDataViolation):
        run_backtest(lambda d: pd.Series(1.0, index=d.index), df, rf_daily=zero_rf())


# ---- Rule 3: causality — decide at close t, execute at open t+1 ------------

def test_position_lags_decision_by_one_day():
    df = make_df(200)
    res = run_backtest(lambda d: pd.Series(1.0, index=d.index), df,
                       start=df.index[5], end=df.index[-1], rf_daily=zero_rf(df.index))
    w = pd.Series(1.0, index=df.index)
    expected = w.shift(1).fillna(0.0).loc[res.positions.index]
    assert np.allclose(res.positions.iloc[:, 0].values, expected.values)


def test_constant_long_equity_matches_hand_calc():
    df = make_df(120)
    res = run_backtest(lambda d: pd.Series(1.0, index=d.index), df,
                       start=df.index[0], end=df.index[-1], rf_daily=zero_rf(df.index))
    o = df["Open"].values
    r_oo = o[1:] / o[:-1] - 1.0          # day t forward open-to-open return
    daily = np.zeros(len(df) - 1)
    daily[1:] = r_oo[1:]                  # position active from day 1
    daily[1] -= 1.0 * SIDE                # entry cost when position goes 0 -> 1
    expected_total = np.prod(1.0 + daily) - 1.0
    assert res.stats["total_return"] == pytest.approx(expected_total, abs=1e-12)


def test_lookahead_detector_catches_future_peeking():
    df = make_df(300)

    def leaky(d):  # buys ahead of tomorrow's up-move: blatant future data
        return (d["Close"].shift(-1) > d["Close"]).astype(float)

    with pytest.raises(LookaheadError):
        run_backtest(leaky, df, start=df.index[10], end=df.index[-1],
                     rf_daily=zero_rf(df.index))


def test_lookahead_detector_catches_full_sample_statistic():
    df = make_df(300)

    def leaky(d):  # threshold uses the full-sample mean — future info
        return (d["Close"] > d["Close"].mean()).astype(float)

    with pytest.raises(LookaheadError):
        run_backtest(leaky, df, start=df.index[10], end=df.index[-1],
                     rf_daily=zero_rf(df.index))


def test_causal_strategy_passes_lookahead_check():
    df = make_df(300)

    def sma(d):
        return (d["Close"] > d["Close"].rolling(20).mean()).astype(float)

    res = run_backtest(sma, df, start=df.index[30], end=df.index[-1],
                       rf_daily=zero_rf(df.index))
    assert res.verdict in ("PASS", "FAIL")


# ---- Rule 2: costs always on ------------------------------------------------

def test_costs_reduce_returns_and_stress_reported_for_frequent_trader():
    df = make_df(400, drift=0.0)

    def churner(d):  # deterministic causal daily flip-flop
        return pd.Series((np.arange(len(d)) % 2).astype(float), index=d.index)

    res = run_backtest(churner, df, start=df.index[5], end=df.index[-1],
                       rf_daily=zero_rf(df.index))
    assert res.trades_per_year > 52
    assert set(res.stress) == {1.0, 2.0, 3.0}
    assert res.stress[3.0]["total_return"] < res.stress[2.0]["total_return"] \
        < res.stress[1.0]["total_return"]


def test_infrequent_trader_reports_base_costs_only():
    df = make_df(300)
    res = run_backtest(lambda d: pd.Series(1.0, index=d.index), df,
                       start=df.index[5], end=df.index[-1], rf_daily=zero_rf(df.index))
    assert set(res.stress) == {1.0}


def test_leverage_pays_financing():
    idx = pd.bdate_range("2010-01-04", periods=300)
    flat = pd.DataFrame({"Open": 100.0, "High": 100.0, "Low": 100.0,
                         "Close": 100.0, "Volume": 1}, index=idx)
    rf = pd.Series(0.04 / 252, index=idx)  # 4% bills
    res = run_backtest(lambda d: pd.Series(2.0, index=d.index), flat,
                       start=idx[0], end=idx[-1], rf_daily=rf)
    # prices never move; 2x leverage must bleed financing on the borrowed 1x
    assert res.stats["total_return"] < -0.005


# ---- Standing rule: absurd numbers are withheld -----------------------------

def test_absurd_result_withholds_verdict():
    idx = pd.bdate_range("2010-01-04", periods=300)
    px = 100.0 * 1.005 ** np.arange(300)  # 0.5%/day, ~250% annualized
    df = pd.DataFrame({"Open": px, "High": px, "Low": px, "Close": px,
                       "Volume": 1}, index=idx)
    res = run_backtest(lambda d: pd.Series(1.0, index=d.index), df,
                       start=idx[0], end=idx[-1], rf_daily=zero_rf(idx))
    assert res.absurd
    assert res.verdict.startswith("WITHHELD")
    assert "ABSURD" in res.report()


# ---- PASS-STD verdict -------------------------------------------------------

def test_pass_requires_beating_both_return_and_drawdown():
    strat = {"total_return": 0.5, "max_drawdown": -0.10}
    bench = {"total_return": 0.4, "max_drawdown": -0.20}
    assert pass_std_verdict(strat, bench) == "PASS"
    assert pass_std_verdict({"total_return": 0.3, "max_drawdown": -0.10}, bench) == "FAIL"
    assert pass_std_verdict({"total_return": 0.5, "max_drawdown": -0.30}, bench) == "FAIL"
    assert pass_std_verdict({"total_return": 0.4, "max_drawdown": -0.10}, bench) == "FAIL"  # tie fails
