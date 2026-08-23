"""Exogenous calendar features for seasonal/monthly/weekly strategies.

These features are functions of the exchange calendar only — never of prices.
Exchange trading calendars (month ends, week ends, holidays, witching dates)
are published years in advance, so a strategy may legitimately know at today's
close that tomorrow is, e.g., the last trading day of the month or a
pre-holiday session. Features are therefore precomputed once from the full
TRAIN index and captured in strategy closures; the automated lookahead check
truncates price data, and these calendar features rightly remain constant.
"""

import numpy as np
import pandas as pd


def build(idx: pd.DatetimeIndex) -> dict:
    nxt = pd.Series(idx[1:].append(pd.DatetimeIndex([pd.NaT])), index=idx)
    prv = pd.Series(pd.DatetimeIndex([pd.NaT]).append(idx[:-1]), index=idx)

    month_end = pd.Series((nxt.dt.month != idx.month) | nxt.isna(), index=idx)
    week_end = pd.Series(
        nxt.isna() | ((nxt - pd.Series(idx, index=idx)).dt.days > 2)
        | (nxt.dt.dayofweek < pd.Series(idx.dayofweek, index=idx)), index=idx)

    # Trading day number within month (1-based) counted forward
    tdom = pd.Series(0, index=idx)
    count, cur = 0, None
    vals = []
    for d in idx:
        if cur != (d.year, d.month):
            cur, count = (d.year, d.month), 0
        count += 1
        vals.append(count)
    tdom = pd.Series(vals, index=idx)

    # Trading days remaining in month (1 = last trading day)
    rem = []
    for i, d in enumerate(idx):
        j = i
        while j + 1 < len(idx) and (idx[j + 1].year, idx[j + 1].month) == (d.year, d.month):
            j += 1
        rem.append(j - i + 1)
    rem = pd.Series(rem, index=idx)

    # Pre-holiday day: a weekday gap of >= 2 calendar weekdays to the next session
    def weekday_gap(a, b):
        if pd.isna(b):
            return 0
        return int(np.busday_count(a.date(), b.date()))
    gaps = pd.Series([weekday_gap(a, b) for a, b in zip(idx, nxt)], index=idx)
    pre_holiday = gaps >= 2  # next weekday is a market holiday

    # Turn-of-month position days: last trading day .. 3rd trading day of next month
    tom = (rem == 1) | (tdom <= 3)
    # Santa: last 5 trading days of Dec + first 2 trading days of Jan
    santa = ((pd.Series(idx.month, index=idx) == 12) & (rem <= 5)) | \
            ((pd.Series(idx.month, index=idx) == 1) & (tdom <= 2))
    # Quarter-end window: last 5 trading days of Mar/Jun/Sep/Dec
    qtr_last5 = (pd.Series(idx.month, index=idx).isin([3, 6, 9, 12])) & (rem <= 5)

    # Quarterly triple-witching Friday (3rd Friday of Mar/Jun/Sep/Dec) + following Monday
    third_fri = set()
    for y in range(idx[0].year, idx[-1].year + 1):
        for m in (3, 6, 9, 12):
            fridays = pd.date_range(f"{y}-{m:02d}-01", periods=31, freq="D")
            fridays = [d for d in fridays if d.month == m and d.dayofweek == 4]
            third_fri.add(fridays[2])
    is_witch_fri = pd.Series([d.normalize() in third_fri for d in idx], index=idx)
    witch_pos = is_witch_fri | is_witch_fri.shift(1).fillna(False)  # Fri + next session

    return {
        "index": idx, "month_end": month_end, "week_end": week_end,
        "tdom": tdom, "rem": rem, "pre_holiday": pre_holiday, "tom": tom,
        "santa": santa, "qtr_last5": qtr_last5, "witch_pos": witch_pos,
        "month": pd.Series(idx.month, index=idx),
        "day": pd.Series(idx.day, index=idx),
    }


def position_weight(pos_days: pd.Series) -> pd.Series:
    """Convert desired POSITION-day flags into decision-day weights.

    The engine holds w(t) from open(t+1); to hold on day D we set w(D-1)=1.
    Shifting a calendar flag backward uses only ex-ante calendar knowledge.
    """
    return pos_days.shift(-1).fillna(False).astype(float)


def flag_signal(values: pd.Series, flags: pd.Series) -> pd.Series:
    """Sample `values` on flag days (decided at that day's close) and hold the
    decision until the next flag day."""
    out = values.where(flags.reindex(values.index).fillna(False))
    return out.ffill()


def _next_business_day(idx: pd.DatetimeIndex) -> np.ndarray:
    """The next weekday after each date, from the calendar alone."""
    days = idx.values.astype("datetime64[D]")
    return np.busday_offset(days, 1, roll="forward")


def month_end_flags(idx: pd.DatetimeIndex) -> pd.Series:
    """True on the last trading day of each month.

    Derived from the CALENDAR (is the next weekday in a new month?), never
    from "is there a later bar in my data". That distinction matters twice:
      * under truncation, a data-derived rule marks the final row as a
        month-end and silently changes past decisions - the automated
        lookahead check catches this;
      * on live bars, a fixed research-window calendar yields all-False and
        reads as "never rebalance".
    Exchange calendars are published years ahead, so this is legitimately
    ex-ante information.
    """
    idx = pd.DatetimeIndex(idx)
    nxt = _next_business_day(idx)
    return pd.Series(pd.DatetimeIndex(nxt).month != idx.month, index=idx)


def week_end_flags(idx: pd.DatetimeIndex) -> pd.Series:
    """True on the last trading day of each week (calendar-derived)."""
    idx = pd.DatetimeIndex(idx)
    nxt = pd.DatetimeIndex(_next_business_day(idx))
    return pd.Series(nxt.isocalendar().week.values != idx.isocalendar().week.values,
                     index=idx)
