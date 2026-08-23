"""Mean-reversion catalog entries."""

import numpy as np
import pandas as pd

from strategies import indicators as I
from strategies.common import E


def _c(df):
    return df["Close"]


def rsi_reversion(period):
    def f(df):
        c = _c(df)
        r = I.rsi(c, period)
        entry = (r < 10) & (c > I.sma(c, 200))
        exit_ = (r > 70) | (c > I.sma(c, 5))
        return I.hysteresis(entry, exit_)
    return f


def bollinger_reversion(df):
    c = _c(df)
    mid, _, lo = I.boll(c, 20, 2.0)
    return I.hysteresis(c < lo, c >= mid)


def ibs_reversion(df):
    return (I.ibs(df) < 0.2).astype(float)


def willr_bounce(df):
    w = I.willr(df, 14)
    return I.hysteresis(w < -90, w > -50)


def envelope_short(df):
    c = _c(df)
    s = I.sma(c, 20)
    return -I.hysteresis(c > 1.05 * s, c <= s)


def stochastic_reversion(df):
    k = I.stoch_k(df, 14)
    d = I.sma(k, 3)
    entry = (k > d) & (k.shift(1) <= d.shift(1)) & (k.shift(1) < 20)
    exit_ = (k < d) & (k.shift(1) >= d.shift(1)) & (k.shift(1) > 80)
    return I.hysteresis(entry, exit_)


def pairs(a, b):
    def f(data):
        ca, cb = data[a]["Close"], data[b]["Close"]
        idx = ca.index.intersection(cb.index)
        ratio = ca.reindex(idx) / cb.reindex(idx)
        z = (ratio - ratio.rolling(60).mean()) / ratio.rolling(60).std(ddof=0)
        zv = z.values
        wa = np.zeros(len(idx))
        state = 0  # +1: long a/short b, -1: short a/long b
        for i in range(len(idx)):
            if np.isnan(zv[i]):
                state = 0
            elif state == 0:
                if zv[i] < -2:
                    state = 1
                elif zv[i] > 2:
                    state = -1
            elif state == 1 and zv[i] >= 0:
                state = 0
            elif state == -1 and zv[i] <= 0:
                state = 0
            wa[i] = state * 0.5
        return pd.DataFrame({a: wa, b: -wa}, index=idx)
    return f


def double_7s(df):
    c = _c(df)
    entry = (c <= c.rolling(7).min()) & (c > I.sma(c, 200))
    exit_ = c >= c.rolling(7).max()
    return I.hysteresis(entry, exit_)


def tps_percentrank(df):
    c = _c(df)
    pr = I.sma(I.pct_rank(c, 100), 3)
    entry = (pr < 15) & (c > I.sma(c, 200))
    return I.hysteresis(entry, pr > 70)


def willr_gated(df):
    c = _c(df)
    w = I.willr(df, 14)
    return I.hysteresis((w < -90) & (c > I.sma(c, 200)), w > -20)


def stoch_gated(df):
    c = _c(df)
    k = I.sma(I.stoch_k(df, 14), 3)
    entry = (k > 20) & (k.shift(1) <= 20) & (c > I.sma(c, 200))
    exit_ = (k < 80) & (k.shift(1) >= 80)
    return I.hysteresis(entry, exit_)


def pct_below_ma(df):
    c = _c(df)
    s20, s200 = I.sma(c, 20), I.sma(c, 200)
    return I.hysteresis((c <= 0.95 * s20) & (c > s200), c >= s20)


def adx_gated_rsi2(df):
    c = _c(df)
    r = I.rsi(c, 2)
    adx, _, _ = I.adx_di(df, 14)
    entry = (r < 10) & (c > I.sma(c, 200)) & (adx < 20)
    exit_ = (r > 70) | (c > I.sma(c, 5))
    return I.hysteresis(entry, exit_)


def consec_down(df):
    c = _c(df)
    down = c < c.shift(1)
    up = c > c.shift(1)
    entry = down & down.shift(1) & down.shift(2) & (c > I.sma(c, 200))
    exit_ = up & up.shift(1)
    return I.hysteresis(entry, exit_)


def low52_bounce(df):
    lo252 = df["Low"].rolling(252).min().shift(1)
    sig = (df["Low"] < lo252) & (df["Close"] > lo252)
    c, l, lv = df["Close"].values, df["Low"].values, lo252.values
    s = sig.fillna(False).values
    pos, p, held, level = np.zeros(len(c)), 0.0, 0, np.nan
    for i in range(len(c)):
        if p == 1.0:
            held += 1
            if held >= 5 or l[i] < level:
                p = 0.0
        if p == 0.0 and s[i]:
            p, held, level = 1.0, 0, l[i]
        pos[i] = p
    return pd.Series(pos, index=df.index)


def keltner_fade(df):
    c = _c(df)
    mid, _, lo = I.keltner(df, 20, 10, 2.0)
    adx, _, _ = I.adx_di(df, 14)
    return I.hysteresis((c < lo) & (adx < 20), c >= mid)


def donchian_fade(df):
    hi = df["High"].rolling(20).max().shift(1)
    lo = df["Low"].rolling(20).min().shift(1)
    mid = (hi + lo) / 2
    adx, _, _ = I.adx_di(df, 14)
    long_e = (df["Low"] <= lo) & (adx < 20)
    long_x = _c(df) >= mid
    short_e = (df["High"] >= hi) & (adx < 20)
    short_x = _c(df) <= mid
    return I.hysteresis(long_e, long_x, short_e, short_x)


def vix_spike(data):
    spy, vix = data["SPY"]["Close"], data["VIX"]["Close"]
    idx = spy.index.intersection(vix.index)
    v = vix.reindex(idx)
    s10 = I.sma(v, 10)
    w = I.hysteresis((v > 1.2 * s10), v < s10)
    return pd.DataFrame({"SPY": w}, index=idx)


def entries():
    out = []
    for t in ("SPY", "QQQ"):
        out.append(E("IDEA-011", "RSI(2) reversion (Connors)", t, [t], rsi_reversion(2),
                     "RSI2<10 & close>SMA200 entry; RSI2>70 or close>SMA5 exit"))
    out.append(E("IDEA-012", "Bollinger reversion", "SPY", ["SPY"], bollinger_reversion,
                 "close<lower BB(20,2) entry; close>=SMA20 exit"))
    for t in ("SPY", "GLD"):
        out.append(E("IDEA-014", "IBS reversion", t, [t], ibs_reversion,
                     "IBS<0.2 entry, 1-day hold (re-signal extends)",
                     adapt="exit at next open instead of next close per protocol"))
    out.append(E("IDEA-015", "Williams %R bounce", "SPY", ["SPY"], willr_bounce,
                 "%R14<-90 entry; %R14>-50 exit"))
    out.append(E("IDEA-016", "MA envelope fade (short)", "SPY", ["SPY"], envelope_short,
                 "short when close>SMA20+5%; cover at SMA20"))
    out.append(E("IDEA-018", "Stochastic reversion", "SPY", ["SPY"], stochastic_reversion,
                 "%K(14)x%D(3) below 20 entry; cross below above 80 exit"))
    out.append(E("IDEA-019", "Pairs z-score reversion", "GLD/SLV", ["GLD", "SLV"],
                 pairs("GLD", "SLV"),
                 "60d ratio z; enter |z|>2 (0.5/-0.5); exit z=0"))
    out.append(E("IDEA-019", "Pairs z-score reversion", "XLE/XLB", ["XLE", "XLB"],
                 pairs("XLE", "XLB"),
                 "60d ratio z; enter |z|>2 (0.5/-0.5); exit z=0"))
    out.append(E("IDEA-068", "Double 7's", "SPY", ["SPY"], double_7s,
                 "7d low close & >SMA200 entry; 7d high close exit"))
    out.append(E("IDEA-069", "TPS PercentRank", "SPY", ["SPY"], tps_percentrank,
                 "3d avg PctRank(100)<15 & >SMA200; exit >70"))
    out.append(E("IDEA-070", "Williams %R gated", "SPY", ["SPY"], willr_gated,
                 "%R14<-90 & >SMA200; exit %R>-20"))
    out.append(E("IDEA-071", "Stochastic gated", "SPY", ["SPY"], stoch_gated,
                 "%K(14,3) x-above 20 & >SMA200; exit x-below 80"))
    for p in (3, 4):
        out.append(E("IDEA-072", f"RSI({p}) reversion variant", "SPY", ["SPY"],
                     rsi_reversion(p),
                     f"RSI{p}<10 & close>SMA200; exit RSI{p}>70 or close>SMA5"))
    out.append(E("IDEA-073", "Pct-below-MA reversion", "SPY", ["SPY"], pct_below_ma,
                 "close<=0.95xSMA20 & >SMA200; exit at SMA20"))
    out.append(E("IDEA-074", "ADX-low gated RSI(2)", "SPY", ["SPY"], adx_gated_rsi2,
                 "RSI2 entries only while ADX14<20"))
    out.append(E("IDEA-075", "3 consecutive down days", "SPY", ["SPY"], consec_down,
                 "3 lower closes & >SMA200; exit 2 higher closes"))
    for t in ("AAPL", "MSFT"):
        out.append(E("IDEA-076", "52-week low bounce", t, [t], low52_bounce,
                     "new 252d intraday low, close back above prior low; hold 5d "
                     "or exit on fresh low"))
    out.append(E("IDEA-077", "Keltner fade (ADX<20)", "SPY", ["SPY"], keltner_fade,
                 "close<EMA20-2xATR10 & ADX<20; exit EMA20"))
    out.append(E("IDEA-078", "Donchian fade (ADX<20)", "SPY", ["SPY"], donchian_fade,
                 "fade 20d channel touches toward midline while ADX<20"))
    out.append(E("IDEA-079", "VIX spike reversion", "SPY (VIX signal)",
                 ["SPY", "VIX"], vix_spike,
                 "VIX close>1.2x its SMA10 entry; exit VIX<SMA10", bench=["SPY"]))
    return out
