"""Performance metrics, buy-and-hold benchmark, PASS-STD verdict, absurdity gate."""

import numpy as np
import pandas as pd

from .rules import (
    ABSURD_CAGR,
    ABSURD_HIT_RATE,
    ABSURD_SHALLOW_DD,
    ABSURD_SHALLOW_DD_CAGR,
    ABSURD_SHARPE,
    TRADING_DAYS_PER_YEAR,
    WEIGHT_TOLERANCE,
)


def summarize(daily_returns: pd.Series, rf_daily: pd.Series,
              active_mask: pd.Series | None = None) -> dict:
    r = daily_returns.dropna()
    if r.empty:
        return {"total_return": 0.0, "cagr": 0.0, "ann_vol": 0.0, "sharpe": 0.0,
                "max_drawdown": 0.0, "hit_rate": np.nan, "n_days": 0}
    equity = (1.0 + r).cumprod()
    years = len(r) / TRADING_DAYS_PER_YEAR
    total = equity.iloc[-1] - 1.0
    cagr = equity.iloc[-1] ** (1.0 / years) - 1.0 if years > 0 else 0.0
    vol = r.std(ddof=0) * np.sqrt(TRADING_DAYS_PER_YEAR)
    excess = r - rf_daily.reindex(r.index).fillna(0.0)
    sharpe = 0.0
    if excess.std(ddof=0) > 0:
        sharpe = excess.mean() / excess.std(ddof=0) * np.sqrt(TRADING_DAYS_PER_YEAR)
    max_dd = (equity / equity.cummax() - 1.0).min()
    if active_mask is not None:
        active = r[active_mask.reindex(r.index).fillna(False)]
    else:
        active = r[r.abs() > 0]
    hit = float((active > 0).mean()) if len(active) else np.nan
    return {"total_return": float(total), "cagr": float(cagr), "ann_vol": float(vol),
            "sharpe": float(sharpe), "max_drawdown": float(max_dd),
            "hit_rate": hit, "n_days": int(len(r))}


def buy_and_hold(opens: pd.DataFrame, rf_daily: pd.Series,
                 cost_rate_per_side: float) -> dict:
    """Equal-weight buy-and-hold of the benchmark assets, open-to-open, with
    one round trip of costs (entry + exit). Dividend-adjusted by construction."""
    r_oo = opens.shift(-1) / opens - 1.0
    bh = r_oo.mean(axis=1).dropna()
    if len(bh):
        bh.iloc[0] = (1.0 + bh.iloc[0]) * (1.0 - cost_rate_per_side) - 1.0
        bh.iloc[-1] = (1.0 + bh.iloc[-1]) * (1.0 - cost_rate_per_side) - 1.0
    return summarize(bh, rf_daily)


def absurdity_flags(stats: dict, trades_per_year: float) -> list[str]:
    flags = []
    if stats["sharpe"] > ABSURD_SHARPE:
        flags.append(f"Sharpe {stats['sharpe']:.2f} > {ABSURD_SHARPE}")
    if stats["cagr"] > ABSURD_CAGR:
        flags.append(f"CAGR {stats['cagr']:.1%} > {ABSURD_CAGR:.0%}")
    if not np.isnan(stats["hit_rate"]) and stats["hit_rate"] > ABSURD_HIT_RATE \
            and trades_per_year > 5:
        flags.append(f"hit rate {stats['hit_rate']:.1%} > {ABSURD_HIT_RATE:.0%}")
    if stats["cagr"] > ABSURD_SHALLOW_DD_CAGR and stats["max_drawdown"] > -ABSURD_SHALLOW_DD:
        flags.append(
            f"CAGR {stats['cagr']:.1%} with max DD {stats['max_drawdown']:.1%} "
            f"(implausibly shallow)"
        )
    return flags


def pass_std_verdict(strategy_stats: dict, benchmark_stats: dict) -> str:
    """PASS only if it beats buy-and-hold on BOTH total return and max drawdown."""
    beats_return = strategy_stats["total_return"] > benchmark_stats["total_return"]
    beats_dd = strategy_stats["max_drawdown"] > benchmark_stats["max_drawdown"]
    return "PASS" if (beats_return and beats_dd) else "FAIL"


def trades_per_year(turnover: pd.Series) -> float:
    trade_days = (turnover > WEIGHT_TOLERANCE).sum()
    years = len(turnover) / TRADING_DAYS_PER_YEAR
    return float(trade_days / years) if years > 0 else 0.0
