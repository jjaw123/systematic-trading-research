"""Trend-following catalog entries (long/flat unless the log says otherwise)."""

import numpy as np
import pandas as pd

from strategies import indicators as I
from strategies.common import CAL, E, month_flags, monthly_hold

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]


def _c(df):
    return df["Close"]


def gc(df):
    c = _c(df)
    return (I.sma(c, 50) > I.sma(c, 200)).astype(float)


def filt200(df):
    c = _c(df)
    return (c > I.sma(c, 200)).astype(float)


def tsmom(df):
    c = _c(df)
    return monthly_hold((c / c.shift(252) - 1 > 0).astype(float), df.index)


def sector_xs_momentum(data):
    closes = pd.DataFrame({t: data[t]["Close"] for t in SECTORS}).dropna()
    r = closes.shift(21) / closes.shift(252) - 1  # 12-1 formation
    best = r.fillna(-np.inf).idxmax(axis=1)  # warmup rows masked to 0 below
    w = pd.DataFrame(0.0, index=closes.index, columns=SECTORS)
    for t in SECTORS:
        w[t] = (best == t).astype(float)
    w[r.isna().all(axis=1)] = 0.0
    f = CAL["month_end"].reindex(closes.index).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def dual_momentum(data):
    c = pd.DataFrame({t: data[t]["Close"] for t in ["SPY", "EFA", "AGG"]}).dropna()
    r = c / c.shift(252) - 1
    w = pd.DataFrame(0.0, index=c.index, columns=c.columns)
    winner = (r["SPY"] >= r["EFA"]).map({True: "SPY", False: "EFA"})
    for i, t in enumerate(c.index):
        if np.isnan(r.iloc[i]["SPY"]) or np.isnan(r.iloc[i]["EFA"]):
            continue
        pick = winner.iloc[i]
        w.iloc[i, w.columns.get_loc(pick if r.iloc[i][pick] > 0 else "AGG")] = 1.0
    f = CAL["month_end"].reindex(c.index).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def macd_trend(df):
    line, sig = I.macd(_c(df))
    return (line > sig).astype(float)


def psar_ls(df):
    return I.psar(df)


def triple_ema(df):
    c = _c(df)
    return ((I.ema(c, 4) > I.ema(c, 9)) & (I.ema(c, 9) > I.ema(c, 18))).astype(float)


def high52_sector_rotation(data):
    closes = pd.DataFrame({t: data[t]["Close"] for t in SECTORS}).dropna()
    near_high = closes >= 0.95 * closes.rolling(252).max()
    w = near_high.astype(float)
    w = w.div(w.sum(axis=1).replace(0.0, np.nan), axis=0).fillna(0.0)
    f = CAL["month_end"].reindex(closes.index).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def adx_dmi(df):
    adx, pdi, mdi = I.adx_di(df, 14)
    entry = (pdi > mdi) & (pdi.shift(1) <= mdi.shift(1)) & (adx > 25)
    exit_ = (mdi > pdi) & (mdi.shift(1) <= pdi.shift(1))
    return I.hysteresis(entry, exit_)


def sma_10_30(df):
    c = _c(df)
    return (I.sma(c, 10) > I.sma(c, 30)).astype(float)


def sma_5_20_50(df):
    c = _c(df)
    return ((I.sma(c, 5) > I.sma(c, 20)) & (I.sma(c, 20) > I.sma(c, 50))).astype(float)


def abs_momentum(data):
    spy, shy = data["SPY"]["Close"], data["SHY"]["Close"]
    idx = spy.index.intersection(shy.index)
    rs, rh = spy.reindex(idx), shy.reindex(idx)
    hold_spy = (rs / rs.shift(252) - 1) > (rh / rh.shift(252) - 1)
    w = pd.DataFrame({"SPY": hold_spy.astype(float),
                      "SHY": (~hold_spy).astype(float)}, index=idx)
    w[(rs / rs.shift(252) - 1).isna()] = 0.0
    f = CAL["month_end"].reindex(idx).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def dual_momentum_4(data):
    risky = ["SPY", "EFA", "GLD", "IEF"]
    c = pd.DataFrame({t: data[t]["Close"] for t in risky + ["SHY"]}).dropna()
    r = c / c.shift(252) - 1
    w = pd.DataFrame(0.0, index=c.index, columns=risky + ["SHY"])
    top = r[risky].fillna(-np.inf).idxmax(axis=1)  # warmup rows skipped in loop
    for i in range(len(c)):
        if r[risky].iloc[i].isna().any():
            continue
        t = top.iloc[i]
        w.iloc[i, w.columns.get_loc(t if r.iloc[i][t] > r.iloc[i]["SHY"] else "SHY")] = 1.0
    f = CAL["month_end"].reindex(c.index).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def ivy5(data):
    assets = ["SPY", "VEU", "AGG", "VNQ", "GLD"]
    c = pd.DataFrame({t: data[t]["Close"] for t in assets}).dropna()
    above = c.gt(c.rolling(200).mean())
    w = above.astype(float) * 0.20
    f = CAL["month_end"].reindex(c.index).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def adx_gated_gc(df):
    adx, _, _ = I.adx_di(df, 14)
    return (gc(df).astype(bool) & (adx >= 25)).astype(float)


def keltner_breakout(df):
    mid, up, _ = I.keltner(df, 20, 10, 2.0)
    c = _c(df)
    return I.hysteresis(c > up, c < mid)


def aroon_trend(df):
    up, dn = I.aroon(df, 25)
    return I.hysteresis((up > 70) & (dn < 30), up < 50)


def roc125(df):
    c = _c(df)
    return (c / c.shift(125) - 1 > 0).astype(float)


def sma_10_month(df):
    c = _c(df)
    f = CAL["month_end"].reindex(df.index).fillna(False)
    m_close = c.where(f).dropna()
    sig = (m_close > m_close.rolling(10).mean()).astype(float)
    return sig.reindex(df.index).ffill().fillna(0.0)


def weekly_gc_10_40(df):
    c = _c(df)
    f = CAL["week_end"].reindex(df.index).fillna(False)
    wk = c.where(f).dropna()
    sig = (wk.rolling(10).mean() > wk.rolling(40).mean()).astype(float)
    return sig.reindex(df.index).ffill().fillna(0.0)


def ema_12_26(df):
    c = _c(df)
    return (I.ema(c, 12) > I.ema(c, 26)).astype(float)


def elder_triple_screen(df):
    c = _c(df)
    f = CAL["week_end"].reindex(df.index).fillna(False)
    wk = c.where(f).dropna()
    line, sig = I.macd(wk)
    gate = (line > sig).reindex(df.index).ffill().fillna(False)
    r2 = I.rsi(c, 2)
    return I.hysteresis((r2 < 10) & gate, r2 > 70)


def chandelier_donchian(df):
    c, h = _c(df).values, df["High"].values
    entry = (_c(df) > df["High"].rolling(20).max().shift(1)).fillna(False).values
    a = I.atr(df, 22).values
    pos, p, hh = np.zeros(len(c)), 0.0, 0.0
    for i in range(len(c)):
        if p == 1.0:
            hh = max(hh, c[i])
            if c[i] < hh - 3.0 * a[i]:
                p = 0.0
        if p == 0.0 and entry[i]:
            p, hh = 1.0, c[i]
        pos[i] = p
    return pd.Series(pos, index=df.index)


def supertrend(df):
    return (I.supertrend_dir(df, 10, 3.0) > 0).astype(float)


def linreg_trend(df):
    return (I.linreg_slope(_c(df), 50) > 0).astype(float)


def atr_trailing_gc(df):
    c = _c(df).values
    g = gc(df).values
    a = I.atr(df, 14).values
    pos, p, hh = np.zeros(len(c)), 0.0, 0.0
    for i in range(len(c)):
        fresh_cross = g[i] == 1.0 and (i == 0 or g[i - 1] == 0.0)
        if g[i] == 0.0:
            p = 0.0
        elif p == 1.0:
            hh = max(hh, c[i])
            if c[i] < hh - 2.0 * a[i]:
                p = 0.0  # stopped out; stays flat until the next fresh cross
        if p == 0.0 and fresh_cross:
            p, hh = 1.0, c[i]
        pos[i] = p
    return pd.Series(pos, index=df.index)


def ma_ribbon(df):
    c = _c(df)
    s = [I.sma(c, n) for n in (10, 20, 30, 40, 50)]
    ok = pd.Series(True, index=df.index)
    for a, b in zip(s[:-1], s[1:]):
        ok &= a > b
    return ok.astype(float)


def ride_upper_band(df):
    _, up, _ = I.boll(_c(df), 20, 2.0)
    return (_c(df) >= up).astype(float)


def high52_trailing(df):
    c = _c(df)
    hi = c.rolling(252).max()
    entry = (c >= 0.95 * hi) & (c / c.shift(63) - 1 > 0)
    exit_ = c < 0.90 * hi
    return I.hysteresis(entry, exit_)


def sector_rotation_6m(data):
    closes = pd.DataFrame({t: data[t]["Close"] for t in SECTORS}).dropna()
    r = closes / closes.shift(126) - 1
    rank = r.rank(axis=1, ascending=False)
    w = (rank <= 3).astype(float) / 3.0
    w[r.isna().any(axis=1)] = 0.0
    # Month-ends derived from the data index so this runs unchanged on live
    # bars; a fixed research-window calendar yields all-False on live dates.
    f = month_flags(closes.index)
    return w.where(f).ffill().fillna(0.0)


def sector_rotation_invvol(data):
    closes = pd.DataFrame({t: data[t]["Close"] for t in SECTORS}).dropna()
    r = closes / closes.shift(126) - 1
    rank = r.rank(axis=1, ascending=False)
    iv = 1.0 / closes.pct_change().rolling(20).std(ddof=0)
    w = (rank <= 3).astype(float) * iv
    w = w.div(w.sum(axis=1).replace(0.0, np.nan), axis=0).fillna(0.0)
    w[r.isna().any(axis=1)] = 0.0
    f = CAL["month_end"].reindex(closes.index).fillna(False)
    return w.where(f).ffill().fillna(0.0)


def vol_adjusted_trend(df):
    c = _c(df)
    ret12 = c / c.shift(252) - 1
    vol12 = c.pct_change().rolling(252).std(ddof=0) * np.sqrt(252)
    return monthly_hold((ret12 / vol12 > 0.3).astype(float), df.index)


def entries():
    out = []
    for t in ("SPY", "QQQ", "GLD"):
        out.append(E("IDEA-001", "Golden Cross 50/200", t, [t], gc,
                     "SMA50>SMA200 long/flat, daily"))
    for t in ("SPY", "EFA", "GLD", "VNQ"):
        out.append(E("IDEA-002", "200-day SMA filter", t, [t], filt200,
                     "close>SMA200 long/cash, daily"))
    for t in ("SPY", "GLD"):
        out.append(E("IDEA-003", "12-mo TS momentum", t, [t], tsmom,
                     "12m return>0 at month-end, hold 1 month"))
    out.append(E("IDEA-004", "XS momentum 12-1 top decile", "9 SPDR sectors",
                 SECTORS, sector_xs_momentum,
                 "rank t-12..t-1 return monthly, top 1 of 9 (=top decile), EW"))
    out.append(E("IDEA-005", "Dual momentum (Antonacci)", "SPY/EFA/AGG",
                 ["SPY", "EFA", "AGG"], dual_momentum,
                 "12m relative SPY vs EFA + absolute>0 else AGG, monthly"))
    for t in ("SPY", "GLD"):
        out.append(E("IDEA-006", "MACD trend 12/26/9", t, [t], macd_trend,
                     "MACD>signal long/flat, daily"))
    out.append(E("IDEA-007", "Parabolic SAR", "GLD", ["GLD"], psar_ls,
                 "AF 0.02/0.02/0.20, long/short flip"))
    for t in ("GLD", "SPY"):
        out.append(E("IDEA-008", "Triple EMA 4/9/18", t, [t], triple_ema,
                     "EMA4>EMA9>EMA18 long/flat"))
    out.append(E("IDEA-009", "52wk-high momentum rotation", "9 SPDR sectors",
                 SECTORS, high52_sector_rotation,
                 "EW sectors within 5% of 252d high, monthly rebalance",
                 adapt="monthly rebalance instead of 6-mo tranche holding"))
    out.append(E("IDEA-010", "ADX/DMI system", "GLD", ["GLD"], adx_dmi,
                 "+DI x-above -DI & ADX14>25 entry; opposite DI cross exit"))
    for t in ("GLD", "SPY"):
        out.append(E("IDEA-045", "Dual SMA 10/30", t, [t], sma_10_30,
                     "SMA10>SMA30 long/flat"))
    out.append(E("IDEA-046", "Triple SMA 5/20/50", "SPY", ["SPY"], sma_5_20_50,
                 "SMA5>SMA20>SMA50 long/flat"))
    out.append(E("IDEA-047", "Absolute momentum vs T-bill", "SPY (SHY cash)",
                 ["SPY", "SHY"], abs_momentum,
                 "12m SPY return > 12m SHY return else SHY, monthly",
                 bench=["SPY"]))
    out.append(E("IDEA-048", "Dual momentum 4-asset", "SPY/EFA/GLD/IEF (SHY cash)",
                 ["SPY", "EFA", "GLD", "IEF", "SHY"], dual_momentum_4,
                 "top 12m of 4 if > SHY 12m else SHY, monthly",
                 bench=["SPY", "EFA", "GLD", "IEF"]))
    out.append(E("IDEA-049", "Ivy 5 tactical allocation", "SPY/VEU/AGG/VNQ/GLD",
                 ["SPY", "VEU", "AGG", "VNQ", "GLD"], ivy5,
                 "20% sleeves, each on only if close>SMA200, monthly"))
    out.append(E("IDEA-050", "ADX-gated Golden Cross", "SPY", ["SPY"], adx_gated_gc,
                 "GC long only while ADX14>=25"))
    out.append(E("IDEA-051", "Keltner breakout", "GLD", ["GLD"], keltner_breakout,
                 "close>EMA20+2xATR10 entry; close<EMA20 exit"))
    out.append(E("IDEA-052", "Aroon 25 trend", "GLD", ["GLD"], aroon_trend,
                 "Up>70 & Down<30 entry; Up<50 exit"))
    out.append(E("IDEA-053", "ROC 125-day filter", "SPY", ["SPY"], roc125,
                 "125d ROC>0 long/flat"))
    for t in ("SPY", "GLD"):
        out.append(E("IDEA-054", "10-month SMA timing", t, [t], sma_10_month,
                     "month-end close > SMA10 of month-end closes"))
    out.append(E("IDEA-055", "Weekly GC 10/40wk", "SPY", ["SPY"], weekly_gc_10_40,
                 "SMA10w>SMA40w of completed weekly closes"))
    out.append(E("IDEA-056", "EMA crossover 12/26", "GLD", ["GLD"], ema_12_26,
                 "EMA12>EMA26 long/flat"))
    out.append(E("IDEA-057", "Elder triple screen", "SPY", ["SPY"], elder_triple_screen,
                 "weekly MACD gate; enter RSI2<10; exit RSI2>70"))
    out.append(E("IDEA-058", "Chandelier exit + Donchian entry", "GLD", ["GLD"],
                 chandelier_donchian, "20d-high entry; exit close<HH-3xATR22"))
    out.append(E("IDEA-059", "SuperTrend 10/3", "GLD", ["GLD"], supertrend,
                 "ATR10 mult 3, long/flat"))
    out.append(E("IDEA-060", "LinReg slope 50d", "SPY", ["SPY"], linreg_trend,
                 "50d regression slope>0 long/flat"))
    out.append(E("IDEA-062", "ATR trailing stop on GC", "SPY", ["SPY"], atr_trailing_gc,
                 "GC entry; exit close<HH-2xATR14; re-enter on fresh cross"))
    out.append(E("IDEA-063", "MA ribbon 10-50", "GLD", ["GLD"], ma_ribbon,
                 "SMA10>20>30>40>50 long/flat"))
    out.append(E("IDEA-064", "Ride upper Bollinger", "GLD", ["GLD"], ride_upper_band,
                 "hold while close>=upper BB(20,2)"))
    for t in ("SPY", "AAPL"):
        out.append(E("IDEA-065", "52wk-high momentum, 10% trail", t, [t], high52_trailing,
                     "within 5% of 252d high & 3m ret>0; exit 10% off high"))
    out.append(E("IDEA-066", "Sector rotation top-3 (6m)", "9 SPDR sectors",
                 SECTORS, sector_rotation_6m, "6m return rank, top 3 EW, monthly"))
    out.append(E("IDEA-102", "Sector rotation top-3, inv-vol wts", "9 SPDR sectors",
                 SECTORS, sector_rotation_invvol,
                 "top 3 by 6m return, weights 1/vol20 normalized, monthly"))
    out.append(E("IDEA-067", "Vol-adjusted trend (Sharpe>0.3)", "SPY", ["SPY"],
                 vol_adjusted_trend, "12m ret/12m vol > 0.3 at month-end"))
    return out
