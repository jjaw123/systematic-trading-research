"""Causal indicator library. Every function uses only data at or before each row.

Wilder-smoothed indicators use ewm(alpha=1/n, adjust=False) per the original
definitions. Nothing here shifts data forward.
"""

import numpy as np
import pandas as pd


def sma(s, n):
    return s.rolling(n).mean()


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def wilder(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def rsi(close, n):
    d = close.diff()
    up = wilder(d.clip(lower=0.0), n)
    dn = wilder((-d).clip(lower=0.0), n)
    rs = up / dn.replace(0.0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def true_range(df):
    pc = df["Close"].shift(1)
    return pd.concat([df["High"] - df["Low"], (df["High"] - pc).abs(),
                      (df["Low"] - pc).abs()], axis=1).max(axis=1)


def atr(df, n):
    return wilder(true_range(df), n)


def adx_di(df, n=14):
    up = df["High"].diff()
    dn = -df["Low"].diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr_n = wilder(true_range(df), n)
    plus_di = 100 * wilder(plus_dm, n) / tr_n
    minus_di = 100 * wilder(minus_dm, n) / tr_n
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return wilder(dx.fillna(0.0), n), plus_di, minus_di


def willr(df, n=14):
    hh = df["High"].rolling(n).max()
    ll = df["Low"].rolling(n).min()
    return -100 * (hh - df["Close"]) / (hh - ll)


def stoch_k(df, n=14):
    hh = df["High"].rolling(n).max()
    ll = df["Low"].rolling(n).min()
    return 100 * (df["Close"] - ll) / (hh - ll)


def macd(close, fast=12, slow=26, sig=9):
    line = ema(close, fast) - ema(close, slow)
    return line, ema(line, sig)


def boll(close, n=20, k=2.0):
    mid = sma(close, n)
    sd = close.rolling(n).std(ddof=0)
    return mid, mid + k * sd, mid - k * sd


def keltner(df, n_ema=20, n_atr=10, mult=2.0):
    mid = ema(df["Close"], n_ema)
    a = atr(df, n_atr)
    return mid, mid + mult * a, mid - mult * a


def aroon(df, n=25):
    hi = df["High"].rolling(n + 1).apply(lambda w: float(np.argmax(w)), raw=True)
    lo = df["Low"].rolling(n + 1).apply(lambda w: float(np.argmin(w)), raw=True)
    return 100 * hi / n, 100 * lo / n  # aroon_up, aroon_down


def linreg_slope(close, n=50):
    x = np.arange(n, dtype=float)
    xm = x.mean()
    denom = ((x - xm) ** 2).sum()
    return close.rolling(n).apply(
        lambda y: float(((x - xm) * (y - y.mean())).sum() / denom), raw=True)


def obv(df):
    sign = np.sign(df["Close"].diff()).fillna(0.0)
    return (sign * df["Volume"]).cumsum()


def ibs(df):
    rng = (df["High"] - df["Low"]).replace(0.0, np.nan)
    return ((df["Close"] - df["Low"]) / rng).fillna(0.5)


def pct_rank(close, n=100):
    return close.rolling(n).apply(lambda w: 100.0 * (w[-1] > w[:-1]).mean(), raw=True)


def realized_vol(close, n=20):
    return close.pct_change().rolling(n).std(ddof=0) * np.sqrt(252)


def psar(df, af0=0.02, step=0.02, af_max=0.20):
    """Wilder Parabolic SAR. Returns +1 (long) / -1 (short) direction series."""
    h, l = df["High"].values, df["Low"].values
    n = len(df)
    direction = np.zeros(n)
    if n < 3:
        return pd.Series(direction, index=df.index)
    long = True
    sar, ep, af = l[0], h[0], af0
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if long:
            sar = min(sar, l[i - 1], l[i - 2] if i >= 2 else l[i - 1])
            if l[i] < sar:
                long, sar, ep, af = False, ep, l[i], af0
            elif h[i] > ep:
                ep, af = h[i], min(af + step, af_max)
        else:
            sar = max(sar, h[i - 1], h[i - 2] if i >= 2 else h[i - 1])
            if h[i] > sar:
                long, sar, ep, af = True, ep, h[i], af0
            elif l[i] < ep:
                ep, af = l[i], min(af + step, af_max)
        direction[i] = 1.0 if long else -1.0
    return pd.Series(direction, index=df.index)


def supertrend_dir(df, n=10, mult=3.0):
    """SuperTrend direction: +1 while price above the line, -1 below."""
    a = atr(df, n).values
    mid = ((df["High"] + df["Low"]) / 2).values
    c = df["Close"].values
    m = len(df)
    ub, lb = mid + mult * a, mid - mult * a
    fub, flb = np.full(m, np.nan), np.full(m, np.nan)
    d = np.zeros(m)
    for i in range(1, m):
        fub[i] = ub[i] if (np.isnan(fub[i - 1]) or ub[i] < fub[i - 1]
                           or c[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = lb[i] if (np.isnan(flb[i - 1]) or lb[i] > flb[i - 1]
                           or c[i - 1] < flb[i - 1]) else flb[i - 1]
        if d[i - 1] == 1.0:
            d[i] = -1.0 if c[i] < flb[i] else 1.0
        elif d[i - 1] == -1.0:
            d[i] = 1.0 if c[i] > fub[i] else -1.0
        else:
            d[i] = 1.0 if c[i] > fub[i] else (-1.0 if c[i] < flb[i] else 0.0)
    return pd.Series(d, index=df.index)


def hysteresis(entry, exit_, short_entry=None, short_exit=None):
    """Stateful position from boolean entry/exit events. Long-only unless
    short legs are given. All inputs are causal boolean Series."""
    e = entry.fillna(False).values
    x = exit_.fillna(False).values
    se = short_entry.fillna(False).values if short_entry is not None else None
    sx = short_exit.fillna(False).values if short_exit is not None else None
    pos = np.zeros(len(e))
    p = 0.0
    for i in range(len(e)):
        if p == 1.0 and x[i]:
            p = 0.0
        elif p == -1.0 and sx is not None and sx[i]:
            p = 0.0
        if p == 0.0:
            if e[i]:
                p = 1.0
            elif se is not None and se[i]:
                p = -1.0
        elif p == 1.0 and se is not None and se[i]:
            p = -1.0
        elif p == -1.0 and e[i]:
            p = 1.0
        pos[i] = p
    return pd.Series(pos, index=entry.index)
