"""Breakout catalog entries."""

import numpy as np
import pandas as pd

from strategies import indicators as I
from strategies.common import E


def _c(df):
    return df["Close"]


def donchian(n_in, n_out):
    def f(df):
        entry = _c(df) > df["High"].rolling(n_in).max().shift(1)
        exit_ = _c(df) < df["Low"].rolling(n_out).min().shift(1)
        return I.hysteresis(entry, exit_)
    return f


def high52_breakout(df):
    c = _c(df)
    entry = c > c.rolling(252).max().shift(1)
    exit_ = c < I.sma(c, 50)
    return I.hysteresis(entry, exit_)


def atr_breakout_ls(df):
    c = _c(df)
    a = I.atr(df, 14).shift(1)
    long_e = c > c.shift(1) + 1.5 * a
    short_e = c < c.shift(1) - 1.5 * a
    return I.hysteresis(long_e, short_e, short_e, long_e)


def bb_squeeze(df):
    c = _c(df)
    mid, up, lo = I.boll(c, 20, 2.0)
    bw = (up - lo) / mid
    squeeze = bw <= bw.rolling(126).min()
    armed = squeeze.shift(1).rolling(5).max().astype(bool)
    return I.hysteresis((c > up) & armed, c < mid)


def volume_breakout(df):
    c, v = _c(df), df["Volume"]
    entry = (c > c.rolling(20).max().shift(1)) & (v > 1.5 * I.sma(v, 50))
    exit_ = c < df["Low"].rolling(10).min().shift(1)
    return I.hysteresis(entry, exit_)


def donchian_4wk_ls(df):
    c = _c(df)
    long_e = c > df["High"].rolling(20).max().shift(1)
    short_e = c < df["Low"].rolling(20).min().shift(1)
    return I.hysteresis(long_e, short_e, short_e, long_e)


def williams_vol_breakout(df):
    rng = df["High"] - df["Low"]
    top_third = (df["Close"] - df["Low"]) / rng.replace(0.0, np.nan) > 2.0 / 3.0
    sig = (rng > 1.5 * I.atr(df, 10)) & top_third
    return sig.fillna(False).astype(float)  # 1-day hold


def atr_channel_chandelier(df):
    c = _c(df).values
    a20 = I.atr(df, 20).values
    entry = (_c(df) > _c(df).shift(1) + 2.0 * I.atr(df, 20).shift(1)).fillna(False).values
    pos, p, hh = np.zeros(len(c)), 0.0, 0.0
    for i in range(len(c)):
        if p == 1.0:
            hh = max(hh, c[i])
            if c[i] < hh - 2.0 * a20[i]:
                p = 0.0
        if p == 0.0 and entry[i]:
            p, hh = 1.0, c[i]
        pos[i] = p
    return pd.Series(pos, index=df.index)


def triangle_breakout(df):
    hi20 = df["High"].rolling(20).max()
    lo20 = df["Low"].rolling(20).min()
    rng20 = hi20 - lo20
    compressed = rng20 < 0.5 * rng20.shift(20)
    entry = compressed.shift(1).fillna(False) & (_c(df) > hi20.shift(1))
    exit_ = _c(df) < df["Low"].rolling(10).min().shift(1)
    return I.hysteresis(entry, exit_)


def flag_breakout(df):
    c, h, l = _c(df).values, df["High"].values, df["Low"].values
    n = len(c)
    pos = np.zeros(n)
    p, stop = 0.0, np.nan
    imp_end, imp_adr = -1, np.nan
    for i in range(11, n):
        if p == 1.0:
            if c[i] < stop:
                p = 0.0
            pos[i] = p
            continue
        r10 = c[i] / c[i - 10] - 1.0
        if r10 >= 0.08:
            imp_end = i
            imp_adr = np.mean(h[i - 9:i + 1] - l[i - 9:i + 1])
        if imp_end >= 0 and 3 <= i - imp_end <= 10:
            flag = slice(imp_end + 1, i + 1)
            tight = np.all((h[flag] - l[flag]) < 0.5 * imp_adr)
            if tight and i - imp_end >= 3 and c[i] > h[imp_end + 1:i].max():
                p, stop = 1.0, l[flag].min()
                imp_end = -1
        pos[i] = p
    return pd.Series(pos, index=df.index)


def obv_breakout(df):
    c = _c(df)
    o = I.obv(df)
    entry = (c > c.rolling(20).max().shift(1)) & (o > o.rolling(20).max().shift(1))
    exit_ = c < df["Low"].rolling(10).min().shift(1)
    return I.hysteresis(entry, exit_)


def swing_high_breakout(df):
    c, h, l = _c(df).values, df["High"].values, df["Low"].values
    n = len(c)
    pos = np.zeros(n)
    p = 0.0
    run_hi, run_hi_i = -np.inf, -1
    swing_hi, pull_lo, stop = np.nan, np.inf, np.nan
    for i in range(n):
        if p == 1.0:
            if c[i] < stop:
                p = 0.0
        if h[i] > run_hi:
            run_hi, run_hi_i = h[i], i
            pull_lo = np.inf
        else:
            pull_lo = min(pull_lo, l[i])
            if pull_lo <= run_hi * 0.97:            # >=3% pullback confirms swing
                swing_hi = run_hi
                if p == 0.0 and c[i] > swing_hi:    # breakout above swing high
                    p, stop = 1.0, pull_lo
                    run_hi, pull_lo = h[i], np.inf  # reset tracking
        pos[i] = p
    return pd.Series(pos, index=df.index)


def gold_base_breakout(df):
    c = _c(df)
    hi126 = c.rolling(126).max().shift(1)
    lo126 = c.rolling(126).min().shift(1)
    base = (hi126 - lo126) / c < 0.15
    entry = (c > hi126) & base
    exit_ = c < df["Low"].rolling(60).min().shift(1)
    return I.hysteresis(entry, exit_)


def prior_year_breakout(df):
    c = _c(df)
    yr_hi = c.groupby(c.index.year).max()
    yr_lo = c.groupby(c.index.year).min()
    phi = pd.Series(c.index.year - 1, index=c.index).map(yr_hi)
    plo = pd.Series(c.index.year - 1, index=c.index).map(yr_lo)
    return I.hysteresis(c > phi, c < plo)


def nr7_breakout(df):
    rng = df["High"] - df["Low"]
    nr7 = rng <= rng.rolling(7).min()
    c, h, l = _c(df).values, df["High"].values, df["Low"].values
    s = nr7.fillna(False).values
    pos, p = np.zeros(len(c)), 0.0
    level, stop = np.nan, np.nan
    for i in range(len(c)):
        if s[i]:
            level, stop = h[i], l[i]
        if p == 1.0 and c[i] < stop:
            p = 0.0
        if p == 0.0 and not np.isnan(level) and c[i] > level and not s[i]:
            p = 1.0
        pos[i] = p
    return pd.Series(pos, index=df.index)


def ross_hook(df):
    c = _c(df)
    sma200 = I.sma(c, 200)
    cv, hv, lv = c.values, df["High"].values, df["Low"].values
    gate = (c > sma200).fillna(False).values
    down = (c < c.shift(1)).fillna(False).values
    pos, p = np.zeros(len(cv)), 0.0
    anchor, stop = np.nan, np.nan
    streak = 0
    for i in range(1, len(cv)):
        if down[i]:
            streak += 1
        else:
            if 2 <= streak <= 3 and i - streak - 1 >= 0:
                anchor = hv[i - streak - 1]         # bar before the pullback
                stop = lv[i - streak:i].min()       # pullback low
            streak = 0
        if p == 1.0 and cv[i] < stop:
            p = 0.0
        if p == 0.0 and gate[i] and not np.isnan(anchor) and cv[i] > anchor:
            p = 1.0
            anchor = np.nan
        pos[i] = p
    return pd.Series(pos, index=df.index)


def entries():
    out = []
    for t in ("GLD", "SPY"):
        out.append(E("IDEA-020", "Donchian 20/10 (Turtle 1)", t, [t], donchian(20, 10),
                     "entry close>20d high; exit close<10d low"))
        out.append(E("IDEA-021", "Donchian 55/20 (Turtle 2)", t, [t], donchian(55, 20),
                     "entry close>55d high; exit close<20d low"))
    for t in ("AAPL", "XLK"):
        out.append(E("IDEA-022", "52wk-high breakout", t, [t], high52_breakout,
                     "new 252d close high entry; close<SMA50 exit"))
    out.append(E("IDEA-023", "ATR volatility breakout", "GLD", ["GLD"], atr_breakout_ls,
                 "close>prior close+1.5xATR14 long; mirror short; flip on opposite"))
    out.append(E("IDEA-024", "Bollinger squeeze breakout", "GLD", ["GLD"], bb_squeeze,
                 "bandwidth at 126d low arms 5d; entry close>upper; exit close<SMA20",
                 adapt="squeeze arms entries for 5 days after bandwidth low"))
    for t in ("AAPL", "MSFT"):
        out.append(E("IDEA-026", "Volume-confirmed breakout", t, [t], volume_breakout,
                     "20d high close & vol>1.5x50d avg; exit 10d low",
                     adapt="exit from 150-list #78 (source gave no exit)"))
    out.append(E("IDEA-061", "Donchian 4-week rule L/S", "GLD", ["GLD"], donchian_4wk_ls,
                 "long close>20d high; flip short close<20d low"))
    out.append(E("IDEA-080", "Williams vol breakout (daily)", "GLD", ["GLD"],
                 williams_vol_breakout,
                 "range>1.5xATR10 & close top third; 1-day hold"))
    out.append(E("IDEA-081", "ATR channel + chandelier", "GLD", ["GLD"],
                 atr_channel_chandelier,
                 "close>prior close+2xATR20; exit close<HH-2xATR20"))
    out.append(E("IDEA-082", "Range-compression breakout", "GLD", ["GLD"],
                 triangle_breakout,
                 "20d range<50% of 20d-ago range; entry close>20d high; exit 10d low"))
    out.append(E("IDEA-083", "Flag/pennant breakout", "GLD", ["GLD"], flag_breakout,
                 ">=8%/10d impulse; 3-10d tight flag (<50% impulse ADR); "
                 "entry close>flag high; stop flag low"))
    for t in ("AAPL", "MSFT"):
        out.append(E("IDEA-084", "OBV-confirmed breakout", t, [t], obv_breakout,
                     "20d close high & OBV 20d high; exit 10d low"))
    out.append(E("IDEA-085", "Swing-high breakout (3%)", "GLD", ["GLD"],
                 swing_high_breakout,
                 "swing = peak with >=3% pullback; entry close>swing high; stop pullback low"))
    out.append(E("IDEA-086", "Gold multi-month base breakout", "GLD", ["GLD"],
                 gold_base_breakout,
                 "close>126d high with prior range<15%; exit 60d low"))
    out.append(E("IDEA-087", "Prior-year-high breakout", "SPY", ["SPY"],
                 prior_year_breakout,
                 "close>prior year high close; exit close<prior year low close"))
    out.append(E("IDEA-088", "NR7 breakout (adapted)", "GLD", ["GLD"], nr7_breakout,
                 "close>NR7 high entry; exit close<NR7 low",
                 adapt="close-confirmation entry replaces intraday stop order"))
    out.append(E("IDEA-089", "Ross hook pullback breakout", "GLD", ["GLD"], ross_hook,
                 ">SMA200; 2-3 down-day pullback; entry close>pre-pullback high; "
                 "stop pullback low",
                 adapt="anchor = high of bar preceding the pullback streak"))
    return out
