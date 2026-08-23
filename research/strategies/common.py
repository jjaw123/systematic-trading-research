"""Shared scaffolding for the strategy catalog.

A catalog entry is a dict:
    idea      IDEA-ID(s) from research/IDEA_LOG.md (must exist there)
    name      short human name
    asset     label of the traded asset/universe for the report table
    tickers   data tickers to load (signal-only series like VIX included)
    build     callable(data) -> weight Series/DataFrame (decided at close t;
              the engine executes at open t+1)
    settings  exact settings string for the variant ledger
    bench     benchmark asset list (None = all weight columns)
    adapt     protocol adaptations vs the published rule ("" if none)

The master exchange calendar is built once from SPY's TRAIN index (exogenous,
known ex-ante — see calendars.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import load  # noqa: E402
from strategies import calendars  # noqa: E402

CAL = calendars.build(load("SPY").index)


def E(idea, name, asset, tickers, build, settings, bench=None, adapt=""):
    return dict(idea=idea, name=name, asset=asset, tickers=tickers,
                build=build, settings=settings, bench=bench, adapt=adapt)


def month_flags(df_index):
    return calendars.month_end_flags(df_index)


def week_flags(df_index):
    return calendars.week_end_flags(df_index)


def monthly_hold(sig, df_index):
    """Sample a signal on month-end closes; hold the value until next month-end."""
    f = month_flags(df_index)
    return sig.where(f).ffill().fillna(0.0)
