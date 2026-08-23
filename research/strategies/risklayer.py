"""Portfolio risk layer (IDEA-109 unlevered / IDEA-110 SPY-vol levered).

Construction, all causal (every quantity at row t uses data through t only;
the engine then applies its own one-day execution lag on top):

  1. component signals  -> per-instrument live/flat (or fractional) exposure
  2. per-trade risk size -> w_i = risk_pct / (2*ATR20_i / price_i)
  3. caps                -> single position <= 25%, <= 6 open, gross <= 100%
  4. book vol scale      -> unlevered: min(20% / book_vol, 1.0)
                            levered:   clip(SPY_vol / book_vol, 0.25, 3.0)

The 2*ATR(20) exit distance is OUR proxy (neither component publishes a hard
stop) and is disclosed as an adaptation in IDEA_LOG.md.
"""

import numpy as np
import pandas as pd

from strategies import indicators as I
from strategies.external import vol_target_qqq
from strategies.trend import SECTORS, sector_rotation_6m

SINGLE_CAP = 0.25
MAX_OPEN = 6
GROSS_CAP = 1.0
ATR_N = 20
STOP_MULT = 2.0
VOL_WIN = 20
LEV_CAP = 3.0
LEV_FLOOR = 0.25
BOOK_VOL_TARGET = 0.20


def _components(data):
    """Per-instrument signal exposure from the two surviving strategies."""
    sec = sector_rotation_6m({t: data[t] for t in SECTORS})
    qqq = vol_target_qqq(data["QQQ"]).clip(upper=1.0)  # signal only; risk layer resizes
    idx = sec.index.intersection(qqq.index)
    sig = sec.reindex(idx).copy()
    sig["QQQ"] = qqq.reindex(idx)
    return sig.fillna(0.0)


def _risk_sized(data, sig, risk_pct):
    """Step 2+3: risk-based sizing by exit distance, then caps."""
    stop_frac = pd.DataFrame(
        {c: (STOP_MULT * I.atr(data[c], ATR_N) / data[c]["Close"]).reindex(sig.index)
         for c in sig.columns})
    live = (sig.abs() > 1e-12)
    w = pd.DataFrame(np.where(live, risk_pct / stop_frac.replace(0.0, np.nan), 0.0),
                     index=sig.index, columns=sig.columns).fillna(0.0)
    w = w * np.sign(sig)

    w = w.clip(upper=SINGLE_CAP, lower=-SINGLE_CAP)          # single-position cap

    # cap on number of concurrent open positions: keep the largest MAX_OPEN
    rank = w.abs().rank(axis=1, ascending=False, method="first")
    w = w.where(rank <= MAX_OPEN, 0.0)

    gross = w.abs().sum(axis=1)                               # gross exposure cap
    scale = (GROSS_CAP / gross).clip(upper=1.0).replace([np.inf, -np.inf], 1.0)
    return w.mul(scale.fillna(1.0), axis=0)


def _book_vol(data, w):
    """Trailing annualized realized vol of the unscaled book (causal)."""
    rets = pd.DataFrame({c: data[c]["Close"].pct_change().reindex(w.index)
                         for c in w.columns})
    book = (w.shift(1) * rets).sum(axis=1)
    return book.rolling(VOL_WIN).std(ddof=0) * np.sqrt(252)


def make(risk_pct, levered):
    def f(data):
        sig = _components(data)
        w = _risk_sized(data, sig, risk_pct)
        bv = _book_vol(data, w).replace(0.0, np.nan)
        if levered:
            spy = data["SPY"]["Close"].reindex(w.index)
            target = spy.pct_change().rolling(VOL_WIN).std(ddof=0) * np.sqrt(252)
            k = (target / bv).clip(LEV_FLOOR, LEV_CAP)
        else:
            k = (BOOK_VOL_TARGET / bv).clip(upper=1.0)
        return w.mul(k.fillna(0.0), axis=0)
    return f
