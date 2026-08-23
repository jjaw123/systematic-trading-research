"""Look-ahead bias tests.

The core invariant: any value computed for bar *t* must be identical whether
computed on history[0:t] or on the full history. These tests guard the
feature pipeline and the HMM's filtered (forward-algorithm) inference.
"""

import numpy as np
import pandas as pd
import pytest

from core.data.feature_engineering import FeatureEngineer
from core.hmm_engine import HMMEngine


def make_bars(n: int = 1600, seed: int = 7) -> pd.DataFrame:
    """Synthetic OHLCV with alternating calm/turbulent volatility blocks."""
    rng = np.random.default_rng(seed)
    vol = np.where((np.arange(n) // 200) % 2 == 0, 0.008, 0.025)
    rets = rng.normal(0.0003, vol)
    close = 100.0 * np.exp(np.cumsum(rets))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    spread = rng.uniform(0.0, 0.01, n)
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    volume = rng.lognormal(15, 0.4, n) * (1 + 4 * (vol > 0.01))
    index = pd.bdate_range("2015-01-02", periods=n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close,
         "volume": volume},
        index=index,
    )


@pytest.fixture(scope="module")
def bars() -> pd.DataFrame:
    return make_bars()


@pytest.fixture(scope="module")
def features(bars: pd.DataFrame) -> pd.DataFrame:
    return FeatureEngineer().compute_features(bars)


@pytest.fixture(scope="module")
def engine(features: pd.DataFrame) -> HMMEngine:
    # Small candidate list / few restarts to keep the test fast; the
    # causality property under test is independent of model size.
    eng = HMMEngine(n_candidates=[3], n_init=2, min_train_bars=300,
                    random_state=0)
    eng.fit(features.iloc[:600])
    return eng


class TestFeatureCausality:
    """Features at bar t depend only on bars <= t."""

    def test_truncated_history_reproduces_features(self, bars: pd.DataFrame) -> None:
        """compute_features(bars[:t]) last row must equal the same row of
        compute_features(bars) for several cut points."""
        fe = FeatureEngineer()
        full = fe.compute_features(bars)
        for t in (700, 900, 1200, 1599):
            trunc = fe.compute_features(bars.iloc[:t])
            ts = trunc.index[-1]
            np.testing.assert_allclose(
                trunc.iloc[-1].to_numpy(), full.loc[ts].to_numpy(),
                atol=1e-10,
                err_msg=f"LOOK-AHEAD BIAS DETECTED in features at cut {t}",
            )

    def test_assert_causal_helper(self, bars: pd.DataFrame) -> None:
        """The built-in causality check passes on its own output."""
        FeatureEngineer.assert_causal(bars, FeatureEngineer())

    def test_no_backward_fill(self, bars: pd.DataFrame,
                              features: pd.DataFrame) -> None:
        """Warm-up rows are dropped, never back-filled from the future."""
        assert not features.isna().any().any()
        assert features.index[0] > bars.index[0]


class TestRegimeCausality:
    """Regime inference never uses future bars."""

    def test_no_look_ahead_bias(self, engine: HMMEngine,
                                features: pd.DataFrame) -> None:
        """Regime at T must be identical with data[0:T] vs data[0:T+100]."""
        regime_short = engine.predict_regime_filtered(features.iloc[0:400])[-1]
        regime_long = engine.predict_regime_filtered(features.iloc[0:500])[399]
        assert regime_short == regime_long, "LOOK-AHEAD BIAS DETECTED"

        # Stronger form: entire filtered distributions must match, at every
        # overlapping bar, not just the MAP state at one bar.
        probs_short = engine.filter_probabilities(features.iloc[0:400])
        probs_long = engine.filter_probabilities(features.iloc[0:500])
        np.testing.assert_allclose(
            probs_short, probs_long[:400], atol=1e-12,
            err_msg="LOOK-AHEAD BIAS DETECTED in filtered probabilities",
        )

    def test_confirmation_stable_under_truncation(
        self, engine: HMMEngine, features: pd.DataFrame
    ) -> None:
        """The stability/flicker layer is causal too: predict_series rows
        must not change when future bars are appended."""
        short = engine.predict_series(features.iloc[0:400])
        long = engine.predict_series(features.iloc[0:500])
        pd.testing.assert_frame_equal(short, long.iloc[:400])

    def test_predict_matches_series_tail(self, engine: HMMEngine,
                                         features: pd.DataFrame) -> None:
        """predict() is exactly the last row of predict_series()."""
        state = engine.predict(features.iloc[0:450])
        tail = engine.predict_series(features.iloc[0:450]).iloc[-1]
        assert state.label.value == tail["label"]
        assert state.consecutive_bars == int(tail["consecutive_bars"])
        assert state.is_confirmed == bool(tail["is_confirmed"])

    def test_backtest_invariant_to_future_data(self) -> None:
        """The whole walk-forward pipeline is causal: running on the same
        history with a later end date must reproduce the earlier run
        bit-for-bit over the overlapping period."""
        import pandas as pd
        from backtest.backtester import BacktestConfig, WalkForwardBacktester

        bars_long = make_bars(1360)
        bars_short = bars_long.iloc[:1200]      # same data, earlier end date
        cfg = BacktestConfig(train_window=150, test_window=60, step_size=60)

        def run(bars):
            return WalkForwardBacktester(
                cfg, hmm_params={"n_candidates": [3], "n_init": 2,
                                 "random_state": 0}).run(bars, "TEST")

        short, long = run(bars_short), run(bars_long)
        overlap = short.equity_curve.index
        pd.testing.assert_series_equal(
            short.equity_curve, long.equity_curve.loc[overlap],
            obj="equity curve (LOOK-AHEAD BIAS if this differs)")
        short_trades = short.trades.set_index("timestamp")
        long_trades = long.trades.set_index("timestamp")
        common_trades = long_trades[long_trades.index.isin(overlap)]
        pd.testing.assert_frame_equal(
            short_trades, common_trades.loc[short_trades.index],
            obj="trade log (LOOK-AHEAD BIAS if this differs)")

    def test_model_never_fit_on_test_window(self, small_backtest_result) -> None:
        """Walk-forward folds fit strictly before their test window, and
        every fold trained on exactly train_window bars."""
        cfg = small_backtest_result.config
        for train_start, train_end, test_start, test_end in small_backtest_result.windows:
            assert train_end < test_start, "train window overlaps test window"
        for meta in small_backtest_result.fold_metadata:
            assert meta["train_bars"] == cfg.train_window


class TestExecutionTiming:
    """Backtest fills never occur at the signal bar's own close."""

    def test_signals_fill_next_bar(self, small_backtest_result) -> None:
        """A signal at bar t executes at bar t+1's OPEN plus slippage —
        every recorded fill price matches its bar's open, adjusted."""
        res = small_backtest_result
        slip = res.config.slippage_pct
        opens = res.bars["open"]
        assert len(res.trades) > 0
        for _, t in res.trades.iterrows():
            o = float(opens.loc[t["timestamp"]])
            expected = o * (1 + slip) if t["side"] == "buy" else o * (1 - slip)
            assert t["price"] == pytest.approx(expected, rel=1e-12)
