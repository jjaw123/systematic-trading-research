"""Externally-sourced strategy cards (IDEA-103..107). Rules only; the cards'
claimed performance is not evidence and was not used here."""

import numpy as np
import pandas as pd

from strategies import indicators as I
from strategies.common import CAL, E

ROT_UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "VEU", "AGG", "IEF", "SHY", "VNQ",
                "GLD", "SLV", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU",
                "XLV", "XLY"]
ROT_UNIVERSE = [t for t in ROT_UNIVERSE]  # 20 incl. SHY; BIL excluded (cash-like)


def trend_core(data):
    q, g = data["QQQ"]["Close"], data["GLD"]["Close"]
    idx = q.index.intersection(g.index)
    sig = (q.reindex(idx) > q.reindex(idx).rolling(200).mean())
    valid = q.reindex(idx).rolling(200).mean().notna()
    return pd.DataFrame({"QQQ": (sig & valid).astype(float),
                         "GLD": ((~sig) & valid).astype(float)}, index=idx)


def high52_rotation(data):
    closes = pd.DataFrame({t: data[t]["Close"] for t in ROT_UNIVERSE}).dropna()
    prox = closes / closes.rolling(252).max()
    rank = prox.rank(axis=1, ascending=False)
    w = (rank <= 5).astype(float) / 5.0
    w[prox.isna().any(axis=1)] = 0.0
    spy_gate = closes["SPY"] > closes["SPY"].rolling(200).mean()
    w = w.mul(spy_gate.astype(float), axis=0)
    f = CAL["month_end"].reindex(closes.index).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def ibs_sniper(df):
    c = df["Close"]
    ibs = I.ibs(df)
    gate = (c > I.sma(c, 200)).fillna(False).values
    e = (ibs <= 0.1).fillna(False).values
    x = (ibs >= 0.9).fillna(False).values
    pos, p, held = np.zeros(len(c)), 0.0, 0
    for i in range(len(c)):
        if p == 1.0:
            held += 1
            if x[i] or held >= 3:
                p = 0.0
        if p == 0.0 and e[i] and gate[i]:
            p, held = 1.0, 0
        pos[i] = p
    return pd.Series(pos, index=df.index)


def vol_target_qqq(df):
    vol = I.realized_vol(df["Close"], 20)
    return (0.20 / vol).clip(upper=2.0).fillna(0.0)


def entries():
    return [
        E("IDEA-103", "Trend core QQQ/GLD (200dMA)", "QQQ/GLD", ["QQQ", "GLD"],
          trend_core, "QQQ while close>SMA200 else GLD; daily signal"),
        E("IDEA-104", "52wk-high ETF rotation, SPY gate", "20-ETF universe",
          ROT_UNIVERSE, high52_rotation,
          "monthly top-5 by close/252d-high; cash when SPY<SMA200",
          adapt="20-ETF universe substitutes for published '50 ETFs'"),
        E("IDEA-105", "IBS dip-sniper 0.1/0.9", "SPY", ["SPY"], ibs_sniper,
          "IBS<=0.1 & >SMA200 entry; exit IBS>=0.9 or 3 days"),
        E("IDEA-107", "Vol targeting 20% cap 2x", "QQQ", ["QQQ"], vol_target_qqq,
          "w=20%/realized20, cap 2.0, daily; financing on leverage"),
    ]
