"""Shared fixtures: one small walk-forward run reused across test files."""

import pytest


@pytest.fixture(scope="session")
def small_backtest_result():
    """A fast walk-forward run on synthetic bars (small windows, light HMM)."""
    from test_look_ahead import make_bars
    from backtest.backtester import BacktestConfig, WalkForwardBacktester

    cfg = BacktestConfig(train_window=150, test_window=60, step_size=60,
                         initial_capital=100_000)
    backtester = WalkForwardBacktester(
        cfg, hmm_params={"n_candidates": [3], "n_init": 2, "random_state": 0})
    return backtester.run(make_bars(1300), symbol="TEST")
