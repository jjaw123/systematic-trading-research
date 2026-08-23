"""Backtesting engine for the strategy-testing protocol.

Hard rules (see rules.py): TRAIN 2010-2022 only, TEST locked until UNLOCK;
costs always on; signals causal (decide at close t, execute at open t+1);
automated lookahead check on every run; absurd results withheld as bugs.
"""

from .backtester import BacktestResult, LookaheadError, run_backtest
from .data import TestDataViolation, load, load_many, risk_free_daily
from .metrics import pass_std_verdict

__all__ = [
    "BacktestResult", "LookaheadError", "run_backtest",
    "TestDataViolation", "load", "load_many", "risk_free_daily",
    "pass_std_verdict",
]
