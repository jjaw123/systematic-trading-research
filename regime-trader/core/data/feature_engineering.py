"""Feature engineering: causal technical indicators and HMM input features.

Every function here is a pure function of trailing data: the value at bar *t*
is computed strictly from bars ≤ *t* (rolling windows, causal ewm recursions).
This module is the primary defense against look-ahead bias and is covered by
tests/test_look_ahead.py.

All features are standardized with rolling z-scores (default 252-bar lookback)
before being fed to the HMM, so the model sees stationary, comparable inputs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")

#: Feature column the HMM engine uses to rank states by mean return.
RETURN_COLUMN = "log_ret_1"


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

def wilder_smooth(series: pd.Series, window: int) -> pd.Series:
    """Wilder's smoothing: causal ewm with alpha = 1/window."""
    return series.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


def rolling_slope(series: pd.Series, window: int) -> pd.Series:
    """Least-squares slope of the trailing ``window`` values (per bar)."""
    x = np.arange(window, dtype=float)
    x -= x.mean()
    denom = float((x ** 2).sum())

    def _slope(y: np.ndarray) -> float:
        return float(np.dot(x, y - y.mean()) / denom)

    return series.rolling(window).apply(_slope, raw=True)


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True range: max of (H-L, |H-prev C|, |L-prev C|)."""
    prev_close = close.shift(1)
    ranges = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    )
    return ranges.max(axis=1, skipna=False)


# ---------------------------------------------------------------------------
# Returns / volatility
# ---------------------------------------------------------------------------

def log_returns(close: pd.Series, period: int = 1) -> pd.Series:
    """Log returns over ``period`` bars."""
    return np.log(close / close.shift(period))


def realized_volatility(close: pd.Series, window: int = 20) -> pd.Series:
    """Rolling std of 1-bar log returns over ``window`` bars."""
    return log_returns(close, 1).rolling(window).std()


def vol_ratio(close: pd.Series, fast: int = 5, slow: int = 20) -> pd.Series:
    """Short-horizon vol relative to long-horizon vol (regime-shift signal)."""
    r = log_returns(close, 1)
    return r.rolling(fast).std() / r.rolling(slow).std()


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------

def volume_zscore(volume: pd.Series, window: int = 50) -> pd.Series:
    """Volume z-score vs. its trailing ``window``-bar mean/std."""
    mean = volume.rolling(window).mean()
    std = volume.rolling(window).std()
    return (volume - mean) / std


def volume_trend(volume: pd.Series, sma_window: int = 10,
                 slope_window: int = 10) -> pd.Series:
    """Slope of the ``sma_window``-bar volume SMA over ``slope_window`` bars."""
    return rolling_slope(volume.rolling(sma_window).mean(), slope_window)


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------

def adx(high: pd.Series, low: pd.Series, close: pd.Series,
        window: int = 14) -> pd.Series:
    """Average Directional Index (Wilder), fully causal."""
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=high.index)

    atr_w = wilder_smooth(true_range(high, low, close), window)
    plus_di = 100.0 * wilder_smooth(plus_dm, window) / atr_w
    minus_di = 100.0 * wilder_smooth(minus_dm, window) / atr_w
    di_sum = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum
    return wilder_smooth(dx, window)


def sma_slope(close: pd.Series, sma_window: int = 50,
              slope_window: int = 10) -> pd.Series:
    """Slope of the ``sma_window``-bar close SMA over ``slope_window`` bars."""
    return rolling_slope(close.rolling(sma_window).mean(), slope_window)


# ---------------------------------------------------------------------------
# Mean reversion / momentum / range
# ---------------------------------------------------------------------------

def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder smoothing)."""
    delta = close.diff()
    avg_gain = wilder_smooth(delta.clip(lower=0.0), window)
    avg_loss = wilder_smooth((-delta).clip(lower=0.0), window)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    # All-loss windows: avg_loss > 0, avg_gain 0 → rs 0 → rsi 0 (handled).
    # All-gain windows: avg_loss 0 → NaN above; true RSI is 100.
    return out.where(avg_loss > 0, np.where(avg_gain > 0, 100.0, np.nan))


def rsi_zscore(close: pd.Series, window: int = 14,
               z_window: int = 252) -> pd.Series:
    """RSI standardized against its own trailing distribution."""
    r = rsi(close, window)
    return (r - r.rolling(z_window).mean()) / r.rolling(z_window).std()


def distance_from_sma(close: pd.Series, window: int = 200) -> pd.Series:
    """Distance from the ``window``-bar SMA as a fraction of price."""
    return (close - close.rolling(window).mean()) / close


def roc(close: pd.Series, period: int) -> pd.Series:
    """Rate of change (simple return) over ``period`` bars."""
    return close.pct_change(period)


def normalized_atr(high: pd.Series, low: pd.Series, close: pd.Series,
                   window: int = 14) -> pd.Series:
    """ATR as a fraction of price."""
    return wilder_smooth(true_range(high, low, close), window) / close


# ---------------------------------------------------------------------------
# Assembly / standardization
# ---------------------------------------------------------------------------

def compute_raw_features(bars: pd.DataFrame) -> pd.DataFrame:
    """Compute all raw (unstandardized) features from OHLCV bars.

    Args:
        bars: Single-symbol OHLCV frame indexed by timestamp with columns
            open/high/low/close/volume.

    Returns:
        Feature matrix aligned to bar close times; warm-up rows contain NaN.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in bars.columns]
    if missing:
        raise ValueError(f"bars missing required columns: {missing}")

    c, h, low_, v = bars["close"], bars["high"], bars["low"], bars["volume"]
    return pd.DataFrame(
        {
            RETURN_COLUMN: log_returns(c, 1),
            "log_ret_5": log_returns(c, 5),
            "log_ret_20": log_returns(c, 20),
            "realized_vol_20": realized_volatility(c, 20),
            "vol_ratio_5_20": vol_ratio(c, 5, 20),
            "volume_z_50": volume_zscore(v, 50),
            "volume_trend_10": volume_trend(v, 10),
            "adx_14": adx(h, low_, c, 14),
            "sma_slope_50": sma_slope(c, 50),
            "rsi_z_14": rsi_zscore(c, 14),
            "dist_sma_200": distance_from_sma(c, 200),
            "roc_10": roc(c, 10),
            "roc_20": roc(c, 20),
            "atr_norm_14": normalized_atr(h, low_, c, 14),
        },
        index=bars.index,
    )


def rolling_zscore(features: pd.DataFrame, window: int = 252,
                   min_periods: int | None = None) -> pd.DataFrame:
    """Standardize each column against its trailing ``window``-bar mean/std."""
    mp = window if min_periods is None else min_periods
    mean = features.rolling(window, min_periods=mp).mean()
    std = features.rolling(window, min_periods=mp).std()
    return (features - mean) / std.replace(0.0, np.nan)


class FeatureEngineer:
    """Computes the standardized HMM feature matrix from OHLCV bars.

    Args:
        zscore_window: Lookback for the final rolling z-score standardization.

    Note:
        Total warm-up is roughly ``zscore_window`` + the longest indicator
        lookback (RSI z-score at 252 + 14), so ~520 bars of history are
        consumed before the first valid feature row.
    """

    def __init__(self, zscore_window: int = 252) -> None:
        self.zscore_window = zscore_window

    def compute_features(self, bars: pd.DataFrame) -> pd.DataFrame:
        """Build the standardized, causal feature matrix.

        Warm-up rows (any NaN) are dropped, never filled.

        Args:
            bars: Single-symbol OHLCV frame indexed by timestamp.

        Returns:
            Fully standardized feature matrix with no NaNs.
        """
        raw = compute_raw_features(bars)
        z = rolling_zscore(raw, self.zscore_window)
        return z.dropna()

    @staticmethod
    def assert_causal(bars: pd.DataFrame, engineer: "FeatureEngineer",
                      cut_points: list[int] | None = None) -> None:
        """Raise AssertionError if any feature depends on future bars.

        Recomputes features on right-truncated history: the last row of
        ``compute_features(bars[:t])`` must equal the corresponding row of
        ``compute_features(bars)`` exactly.
        """
        full = engineer.compute_features(bars)
        if cut_points is None:
            n = len(bars)
            first = n - max(1, len(full) // 2)
            cut_points = [first, (first + n) // 2, n - 1]
        for t in cut_points:
            trunc = engineer.compute_features(bars.iloc[:t])
            if trunc.empty:
                raise AssertionError(f"no valid feature rows at cut point {t}")
            ts = trunc.index[-1]
            if not np.allclose(trunc.iloc[-1].to_numpy(),
                               full.loc[ts].to_numpy(), atol=1e-10):
                raise AssertionError(
                    f"LOOK-AHEAD BIAS: features at {ts} change when future "
                    f"bars are appended (cut point {t})"
                )
