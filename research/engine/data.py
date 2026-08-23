"""Data loading with hard enforcement of the TRAIN/TEST lock.

Every DataFrame that enters the engine passes through `_guard`, which raises
TestDataViolation if any row falls on or after TEST_START (2023-01-01) or if
the source path points inside the locked directory. There is deliberately no
function in this module capable of loading test-period data.
"""

from pathlib import Path

import pandas as pd

from .rules import LOCKED_DIR_NAME, TEST_START, TRADING_DAYS_PER_YEAR

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class TestDataViolation(RuntimeError):
    """Raised on any attempt to touch TEST-period (locked) data."""


def _guard(df: pd.DataFrame, source: str) -> pd.DataFrame:
    if LOCKED_DIR_NAME in str(source):
        raise TestDataViolation(
            f"Refusing to read from locked directory: {source}. "
            f"TEST data stays untouched until the user says UNLOCK."
        )
    if "market_cache" in str(source):
        raise TestDataViolation(
            f"Refusing to read the LIVE market cache into research: {source}. "
            f"Live bars are current-dated (inside the locked TEST range) and "
            f"exist only to compute live signals. Backtests must use "
            f"research/data/."
        )
    if len(df) and df.index.max() >= pd.Timestamp(TEST_START):
        raise TestDataViolation(
            f"{source} contains rows on/after {TEST_START}. TEST data is "
            f"locked until the user says UNLOCK. Re-run scripts/split_train_test.py."
        )
    return df


def load(ticker: str) -> pd.DataFrame:
    """Load one ticker's dividend/split-adjusted daily bars (train period only)."""
    path = DATA_DIR / f"{ticker}.csv"
    df = pd.read_csv(path, index_col="Date", parse_dates=True).sort_index()
    if df.index.has_duplicates:
        df = df[~df.index.duplicated(keep="last")]
    return _guard(df, str(path))


def load_many(tickers: list[str]) -> dict[str, pd.DataFrame]:
    return {t: load(t) for t in tickers}


def risk_free_daily(index: pd.DatetimeIndex) -> pd.Series:
    """Daily risk-free rate aligned to `index`, from the 13-week T-bill yield.

    ^IRX quotes an annualized percent; converted to a simple per-trading-day
    rate. Forward-filled across gaps; zero before the series begins.
    """
    path = DATA_DIR / "IRX.csv"
    if not path.exists():
        return pd.Series(0.0, index=index)
    irx = pd.read_csv(path, index_col="Date", parse_dates=True)["Close"].sort_index()
    _guard(irx.to_frame(), str(path))
    daily = irx / 100.0 / TRADING_DAYS_PER_YEAR
    return daily.reindex(index).ffill().fillna(0.0)
