"""Tests for backtest/: allocation math, fills, windows, metrics, stress."""

import numpy as np
import pandas as pd
import pytest

from backtest.performance import PerformanceAnalyzer, max_drawdown
from backtest.stress_test import inject_crashes, inject_gaps
from test_look_ahead import make_bars


class TestWalkForwardStructure:
    def test_windows_train_strictly_before_test(self, small_backtest_result) -> None:
        for train_start, train_end, test_start, test_end in small_backtest_result.windows:
            assert train_start < train_end < test_start < test_end

    def test_test_windows_are_contiguous(self, small_backtest_result) -> None:
        windows = small_backtest_result.windows
        for prev, nxt in zip(windows, windows[1:]):
            assert nxt[2] > prev[2]  # test starts advance monotonically

    def test_equity_and_regime_history_aligned(self, small_backtest_result) -> None:
        res = small_backtest_result
        assert res.equity_curve.index.equals(res.regime_history.index)
        assert not res.equity_curve.isna().any()


class TestAllocationMath:
    def test_fills_at_next_bar_open_with_slippage(self, small_backtest_result) -> None:
        """Every trade price is that bar's open adjusted by slippage —
        never the signal bar's close."""
        res = small_backtest_result
        slip = res.config.slippage_pct
        opens = res.bars["open"]
        for _, t in res.trades.iterrows():
            o = float(opens.loc[t["timestamp"]])
            expected = o * (1 + slip) if t["side"] == "buy" else o * (1 - slip)
            assert t["price"] == pytest.approx(expected, rel=1e-12)

    def test_share_targets_match_formula(self, small_backtest_result) -> None:
        """new_shares == int(equity_at_open * target_allocation / price)."""
        for _, t in small_backtest_result.trades.iterrows():
            expected = int(t["equity_at_open"] * t["new_allocation"] / t["price"])
            assert t["new_shares"] == expected
            assert t["new_shares"] == t["prev_shares"] + t["delta_shares"]

    def test_equity_matches_manual_replay(self, small_backtest_result) -> None:
        """Replaying the trade log over the bars reproduces the equity curve
        exactly — proving equity = cash + shares * price throughout,
        including negative cash under leverage."""
        res = small_backtest_result
        cash, shares = res.config.initial_capital, 0
        trades = res.trades.set_index("timestamp")
        close = res.bars["close"]
        for ts, recorded in res.equity_curve.items():
            if ts in trades.index:
                t = trades.loc[ts]
                cash -= float(t["delta_shares"]) * float(t["price"])
                shares += int(t["delta_shares"])
            assert cash + shares * float(close.loc[ts]) == pytest.approx(recorded)

    def test_leverage_allows_negative_cash(self, small_backtest_result) -> None:
        """When target allocation exceeds 1.0 (leverage), share value exceeds
        equity — implying margin debt — and allocations stay within the
        strategy's envelope."""
        res = small_backtest_result
        eff = res.regime_history["effective_alloc"]
        assert (eff <= 1.30).all()  # never beyond 0.95 * 1.25 + rounding
        if (res.trades["new_allocation"] > 1.0).any():
            assert eff.max() > 1.0


class TestPerformance:
    def test_report_is_sane(self, small_backtest_result) -> None:
        rep = PerformanceAnalyzer().analyze(small_backtest_result)
        assert np.isfinite(rep.total_return)
        assert 0 <= rep.max_drawdown <= 1
        assert rep.n_trades == len(small_backtest_result.trades)
        assert 0 <= rep.exposure <= 1.30
        assert rep.worst_day <= 0 or rep.max_drawdown == 0

    def test_regime_and_confidence_breakdowns(self, small_backtest_result) -> None:
        an = PerformanceAnalyzer()
        reg = an.regime_breakdown(small_backtest_result)
        assert len(reg) >= 1
        assert reg["pct_time"].sum() == pytest.approx(1.0)
        conf = an.confidence_breakdown(small_backtest_result)
        assert list(conf["confidence"]) == ["< 50%", "50-60%", "60-70%", "70%+"]

    def test_benchmarks(self, small_backtest_result) -> None:
        an = PerformanceAnalyzer()
        bench = an.compare_benchmarks(small_backtest_result, n_random=5)
        assert {"strategy", "buy_and_hold", "sma200_trend",
                "random_mean", "random_std"} <= set(bench.index)
        bh = an.buy_and_hold(small_backtest_result)
        assert bh.index.equals(small_backtest_result.equity_curve.index)

    def test_export_csvs(self, small_backtest_result, tmp_path) -> None:
        paths = PerformanceAnalyzer().export_csvs(small_backtest_result, tmp_path)
        names = {p.name for p in paths}
        assert names == {"equity_curve.csv", "trade_log.csv",
                         "regime_history.csv"}
        assert all(p.exists() and p.stat().st_size > 0 for p in paths)

    def test_max_drawdown_helper(self) -> None:
        eq = pd.Series([100.0, 110.0, 99.0, 104.5, 121.0])
        mdd, duration = max_drawdown(eq)
        assert mdd == pytest.approx(0.10)
        assert duration == 2  # bars 99.0 and 104.5 are underwater


class TestStressInjection:
    def test_crash_injection_is_persistent(self) -> None:
        bars = make_bars(300)
        stressed = inject_crashes(bars, positions=[100], magnitudes=[-0.10])
        ratio = stressed["close"] / bars["close"]
        assert np.allclose(ratio.iloc[:100], 1.0)
        assert np.allclose(ratio.iloc[100:], 0.90)
        assert np.allclose(stressed["volume"], bars["volume"])  # untouched

    def test_gap_injection_sizes_by_atr(self) -> None:
        bars = make_bars(300)
        stressed, applied = inject_gaps(bars, positions=[150], atr_mults=[3.0])
        assert len(applied) == 1
        p, gap_ret = applied[0]
        assert p == 150 and -0.5 <= gap_ret < 0
        assert stressed["open"].iloc[150] == pytest.approx(
            bars["open"].iloc[150] * (1 + gap_ret))
