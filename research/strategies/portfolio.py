"""Seasonal, position-sizing, and portfolio-construction catalog entries."""

import numpy as np
import pandas as pd

from strategies import indicators as I
from strategies.breakout import donchian
from strategies.calendars import position_weight
from strategies.common import CAL, E

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]


def _cal_weight(pos_days_full):
    def f(df):
        w = position_weight(pos_days_full)
        return w.reindex(df.index).fillna(0.0)
    return f


def _months(mset):
    return CAL["month"].isin(mset)


def window_dressing_sectors(data):
    closes = pd.DataFrame({t: data[t]["Close"] for t in SECTORS}).dropna()
    r63 = closes / closes.shift(63) - 1
    best = r63.fillna(-np.inf).idxmax(axis=1)  # warmup rows masked below
    # Shift on the FULL exchange calendar first (tomorrow-is-window-day is
    # ex-ante calendar knowledge), then align to the data index.
    hold_tomorrow = CAL["qtr_last5"].shift(-1).fillna(False) \
        .reindex(closes.index).fillna(False)
    w = pd.DataFrame(0.0, index=closes.index, columns=SECTORS)
    for t in SECTORS:
        w[t] = (hold_tomorrow & (best == t) & r63.notna().all(axis=1)).astype(float)
    return w


def month_seasonality_walkforward(df):
    c = df["Close"]
    f = CAL["month_end"].reindex(df.index).fillna(False)
    m_close = c.where(f).dropna()
    m_ret = m_close.pct_change()
    w = pd.Series(np.nan, index=df.index)
    hist_by_month = {m: [] for m in range(1, 13)}
    count = 0
    for d, r in m_ret.items():
        nxt_month = d.month % 12 + 1
        if count >= 240:  # >= 20 years of monthly history required by the rule
            means = {m: np.mean(v) for m, v in hist_by_month.items() if len(v) >= 10}
            top6 = sorted(means, key=means.get, reverse=True)[:6]
            w.loc[d] = 1.0 if nxt_month in top6 else 0.0
        else:
            w.loc[d] = 0.0
        if not np.isnan(r):
            hist_by_month[d.month].append(r)
            count += 1
    return w.ffill().fillna(0.0)


def atr_sized_donchian(with_stop):
    base = donchian(20, 10)

    def f(df):
        pos = base(df).values
        c = df["Close"].values
        a = I.atr(df, 20).values
        w = np.zeros(len(c))
        p, entry_px, entry_atr, stopped = 0.0, np.nan, np.nan, False
        for i in range(len(c)):
            if pos[i] == 1.0 and p == 0.0:
                p, entry_px, entry_atr, stopped = 1.0, c[i], a[i], False
            elif pos[i] == 0.0:
                p, stopped = 0.0, False
            if p == 1.0 and with_stop and not stopped:
                if c[i] < entry_px - 2.0 * entry_atr:
                    stopped = True
            if p == 1.0 and not stopped:
                size = 0.01 / (2.0 * a[i] / c[i]) if a[i] > 0 else 0.0
                w[i] = min(size, 1.0)
            else:
                w[i] = 0.0
        return pd.Series(w, index=df.index)
    return f


def half_kelly_donchian(df):
    base = donchian(20, 10)(df).values
    c = df["Close"].values
    w = np.zeros(len(c))
    trades, entry_px = [], np.nan
    scale, p = 1.0, 0.0
    for i in range(len(c)):
        if base[i] == 1.0 and p == 0.0:
            p, entry_px = 1.0, c[i]
            if len(trades) >= 30:
                wins = [t for t in trades if t > 0]
                losses = [-t for t in trades if t <= 0]
                W = len(wins) / len(trades)
                R = (np.mean(wins) / np.mean(losses)) if wins and losses and np.mean(losses) > 0 else np.nan
                f_star = W - (1 - W) / R if R and not np.isnan(R) and R > 0 else 0.0
                scale = float(np.clip(0.5 * f_star, 0.0, 1.0))
            else:
                scale = 1.0
        elif base[i] == 0.0 and p == 1.0:
            p = 0.0
            trades.append(c[i] / entry_px - 1.0)
        w[i] = scale if p == 1.0 else 0.0
    return pd.Series(w, index=df.index)


def vol_target_spy(df):
    c = df["Close"]
    vol = I.realized_vol(c, 20)
    w = (0.10 / vol).clip(0.25, 2.0)
    f = CAL["week_end"].reindex(df.index).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def one_over_n(data):
    assets = ["SPY", "GLD", "XLE", "XLK", "XLV"]
    idx = None
    for t in assets:
        idx = data[t].index if idx is None else idx.intersection(data[t].index)
    w = pd.DataFrame(0.2, index=idx, columns=assets)
    f = CAL["month_end"].reindex(idx).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def pyramiding_donchian(df):
    c = df["Close"].values
    a = I.atr(df, 20).values
    entry = (df["Close"] > df["High"].rolling(20).max().shift(1)).fillna(False).values
    exit_ = (df["Close"] < df["Low"].rolling(10).min().shift(1)).fillna(False).values
    w = np.zeros(len(c))
    units = []  # entry prices of open units (each unit = 0.25 weight)
    for i in range(len(c)):
        if units and exit_[i]:
            units = []
        elif units:
            units = [u for u in units if c[i] >= u - 2.0 * a[i]]  # per-unit 2N stop
            if units and len(units) < 4 and c[i] >= units[-1] + 0.5 * a[i]:
                units.append(c[i])
        elif entry[i]:
            units = [c[i]]
        w[i] = 0.25 * len(units)
    return pd.Series(w, index=df.index)


def _book_signals(data):
    idx = None
    for t in ("GLD", "SPY", "QQQ"):
        idx = data[t].index if idx is None else idx.intersection(data[t].index)
    sig, atr_pct = {}, {}
    for t in ("GLD", "SPY", "QQQ"):
        d = data[t].reindex(idx)
        sig[t] = donchian(20, 10)(d)
        atr_pct[t] = (2.0 * I.atr(d, 20) / d["Close"])
    return idx, pd.DataFrame(sig), pd.DataFrame(atr_pct)


def corr_capped_book(data):
    idx, sig, _ = _book_signals(data)
    rets = pd.DataFrame({t: data[t]["Close"].reindex(idx).pct_change()
                         for t in sig.columns})
    w = (sig / 3.0).clip(upper=0.25)  # single-position cap 25%
    corr_sq = rets["SPY"].rolling(60).corr(rets["QQQ"])
    corr_sg = rets["SPY"].rolling(60).corr(rets["GLD"])
    corr_qg = rets["QQQ"].rolling(60).corr(rets["GLD"])
    for (x, y, cs) in (("SPY", "QQQ", corr_sq), ("SPY", "GLD", corr_sg),
                       ("QQQ", "GLD", corr_qg)):
        pair_sum = w[x] + w[y]
        over = (cs > 0.7) & (pair_sum > 0.6)
        scale = (0.6 / pair_sum).where(over, 1.0).fillna(1.0)
        w[x] = w[x] * scale
        w[y] = w[y] * scale
    return w.fillna(0.0)


def heat_capped_book(data):
    idx, sig, atr_pct = _book_signals(data)
    w = sig / 3.0
    heat = (w * atr_pct).sum(axis=1)
    scale = (0.06 / heat).clip(upper=1.0).replace([np.inf, -np.inf], 1.0).fillna(1.0)
    return w.mul(scale, axis=0).fillna(0.0)


def risk_parity_3(data):
    assets = ["SPY", "GLD", "IEF"]
    closes = pd.DataFrame({t: data[t]["Close"] for t in assets}).dropna()
    iv = 1.0 / closes.pct_change().rolling(60).std(ddof=0)
    w = iv.div(iv.sum(axis=1), axis=0)
    f = CAL["month_end"].reindex(closes.index).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def cppi_spy(df):
    c = df["Close"]
    ret = c.pct_change().fillna(0.0).values
    f = CAL["week_end"].reindex(df.index).fillna(False).values
    n = len(c)
    w = np.zeros(n)
    V, floor, alloc = 1.0, 0.9, 0.0
    for i in range(n):
        V *= 1.0 + alloc * ret[i]          # pre-cost approximation of equity path
        if f[i] or i == 0:
            alloc = min(1.0, max(0.0, 3.0 * (V - floor) / V)) if V > floor else 0.0
        w[i] = alloc
    return pd.Series(w, index=df.index)


def dd_derisk_donchian(df):
    base = donchian(20, 10)(df)
    strat_ret = (df["Close"].pct_change() * base.shift(1)).fillna(0.0)
    eq = (1.0 + strat_ret).cumprod().values  # pre-cost approximation
    b = base.values
    w = np.zeros(len(eq))
    peak = 1.0
    half = False
    for i in range(len(eq)):
        peak = max(peak, eq[i])
        if eq[i] < 0.9 * peak:
            half = True
        elif eq[i] >= peak:
            half = False
        w[i] = b[i] * (0.5 if half else 1.0)
    return pd.Series(w, index=df.index)


def vix_scaled_spy(data):
    spy, vix = data["SPY"]["Close"], data["VIX"]["Close"]
    idx = spy.index.intersection(vix.index)
    w = (20.0 / vix.reindex(idx)).clip(0.25, 1.0)
    f = CAL["week_end"].reindex(idx).fillna(False)
    return pd.DataFrame({"SPY": w.where(f).ffill().fillna(0.0)}, index=idx)


def barbell(data):
    idx = data["BIL"].index.intersection(data["GLD"].index)
    gld_sig = donchian(20, 10)(data["GLD"].reindex(idx))
    return pd.DataFrame({"BIL": 0.9, "GLD": 0.1 * gld_sig}, index=idx)


def rebalance_bands(data):
    idx = data["SPY"].index.intersection(data["GLD"].index)
    rs = data["SPY"]["Close"].reindex(idx).pct_change().fillna(0.0).values
    rg = data["GLD"]["Close"].reindex(idx).pct_change().fillna(0.0).values
    n = len(idx)
    ws, wg = np.zeros(n), np.zeros(n)
    s, g = 0.6, 0.4
    for i in range(n):
        vs, vg = s * (1 + rs[i]), g * (1 + rg[i])
        tot = vs + vg
        s, g = vs / tot, vg / tot
        if s < 0.55 or s > 0.65:
            s, g = 0.6, 0.4
        ws[i], wg[i] = s, g
    return pd.DataFrame({"SPY": ws, "GLD": wg}, index=idx)


def entries():
    out = []
    # --- Seasonal ---
    out.append(E("IDEA-028", "Sell in May", "SPY", ["SPY"],
                 _cal_weight(_months({11, 12, 1, 2, 3, 4})),
                 "long Nov1-Apr30, flat May-Oct"))
    for t in ("SPY", "QQQ"):
        out.append(E("IDEA-029", "Turn-of-month", t, [t], _cal_weight(CAL["tom"]),
                     "long last trading day through 3rd of next month"))
    out.append(E("IDEA-030", "Santa Claus rally", "SPY", ["SPY"],
                 _cal_weight(CAL["santa"]),
                 "long last 5 days of Dec + first 2 of Jan"))
    out.append(E("IDEA-031", "Gold seasonal Sep-Feb", "GLD", ["GLD"],
                 _cal_weight(_months({9, 10, 11, 12, 1, 2})),
                 "long Sep 1 - end Feb"))
    out.append(E("IDEA-090", "Gold seasonal Aug25-Oct31", "GLD", ["GLD"],
                 _cal_weight((CAL["month"].eq(8) & CAL["day"].ge(25))
                             | CAL["month"].isin({9, 10})),
                 "long Aug 25 - Oct 31"))
    out.append(E("IDEA-032", "Pre-holiday effect", "SPY", ["SPY"],
                 _cal_weight(CAL["pre_holiday"]),
                 "long the trading day before each market holiday",
                 adapt="holidays derived from exchange calendar; holds through "
                       "the holiday-overnight to next open"))
    out.append(E("IDEA-091", "Triple-witching drift", "SPY", ["SPY"],
                 _cal_weight(CAL["witch_pos"]),
                 "long witching Friday open through following Tuesday open",
                 adapt="published Thu-close->Mon-close shifted to open execution"))
    out.append(E("IDEA-033", "Window dressing (sectors)", "9 SPDR sectors", SECTORS,
                 window_dressing_sectors,
                 "last 5 days of quarter, hold top trailing-63d sector",
                 adapt="sector universe stands in for S&P500 stocks (no "
                       "constituent data); top pick refreshed daily in window"))
    out.append(E("IDEA-034", "Month-of-year seasonality (walk-fwd)", "SPY", ["SPY"],
                 month_seasonality_walkforward,
                 "expanding >=240-month history; hold top-6 months",
                 adapt="GLD ineligible (needs 20y history; GLD data starts 2004)"))
    # --- Sizing / portfolio ---
    out.append(E("IDEA-035+IDEA-041", "Fixed-frac 1% w/ 2N stop", "GLD (Donchian 20/10)",
                 ["GLD"], atr_sized_donchian(True),
                 "w=1%/(2xATR20/px) cap 1.0; hard stop entry-2xATR20"))
    out.append(E("IDEA-036", "ATR 'N' sizing", "GLD (Donchian 20/10)", ["GLD"],
                 atr_sized_donchian(False),
                 "w=1%/(2xATR20/px) cap 1.0; Donchian exits only"))
    out.append(E("IDEA-037", "Half-Kelly sizing", "GLD (Donchian 20/10)", ["GLD"],
                 half_kelly_donchian,
                 "0.5x Kelly from own closed trades (>=30), else full size"))
    out.append(E("IDEA-038", "Vol targeting 10%", "SPY", ["SPY"], vol_target_spy,
                 "w=10%/realized20 ann., weekly, clip [0.25,2]"))
    out.append(E("IDEA-039", "1/N rebalancing", "SPY/GLD/XLE/XLK/XLV",
                 ["SPY", "GLD", "XLE", "XLK", "XLV"], one_over_n,
                 "20% each, monthly rebalance; benchmark = same basket unrebalanced"))
    out.append(E("IDEA-040", "Pyramiding (Turtle adds)", "GLD (Donchian 20/10)",
                 ["GLD"], pyramiding_donchian,
                 "add 0.25 unit per 0.5xATR20 favorable, max 4; per-unit 2N stop"))
    out.append(E("IDEA-042", "Position/correlation caps", "GLD/SPY/QQQ Donchian book",
                 ["GLD", "SPY", "QQQ"], corr_capped_book,
                 "1/3 base, single cap 25%, corr>0.7 pair sum cap 60%"))
    out.append(E("IDEA-044", "Portfolio heat cap 6%", "GLD/SPY/QQQ Donchian book",
                 ["GLD", "SPY", "QQQ"], heat_capped_book,
                 "scale book so sum(w x 2xATR20/px) <= 6%"))
    out.append(E("IDEA-093", "Risk parity SPY/GLD/IEF", "SPY/GLD/IEF",
                 ["SPY", "GLD", "IEF"], risk_parity_3,
                 "1/vol60 normalized, monthly"))
    out.append(E("IDEA-094", "CPPI floor 90 / mult 3", "SPY", ["SPY"], cppi_spy,
                 "alloc=min(1,3x(V-0.9)/V), weekly",
                 adapt="equity path approximated pre-cost for the allocation state"))
    out.append(E("IDEA-095", "Drawdown de-risking", "GLD (Donchian 20/10)", ["GLD"],
                 dd_derisk_donchian,
                 "halve size after 10% strategy DD; restore at new high",
                 adapt="strategy equity approximated pre-cost for the DD state"))
    out.append(E("IDEA-096", "VIX-scaled exposure", "SPY (VIX signal)",
                 ["SPY", "VIX"], vix_scaled_spy,
                 "w=20/VIX clip [0.25,1], weekly", bench=["SPY"]))
    out.append(E("IDEA-097", "Barbell 90/10", "BIL + GLD sleeve", ["BIL", "GLD"],
                 barbell, "90% BIL; 10% sleeve on Donchian 20/10 GLD"))
    out.append(E("IDEA-098", "Rebalancing bands 60/40", "SPY/GLD", ["SPY", "GLD"],
                 rebalance_bands,
                 "60/40 target; rebalance when SPY weight exits [55%,65%]"))
    return out
