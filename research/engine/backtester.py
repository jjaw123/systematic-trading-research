"""Core daily backtester enforcing the research protocol.

Causality is structural: a strategy returns, for every day t, the target
weight decided at day t's CLOSE using data up to and including t. The engine
itself shifts that decision one day — the position is entered at the NEXT
day's open and earns open-to-open returns. A strategy cannot express
same-day execution through this interface.

On top of the structural shift, every run performs an automated lookahead
check: the strategy is recomputed on data truncated at random dates and its
final decision must match the full-sample decision on that date. Any mismatch
raises LookaheadError and no results are produced.

Costs are always on (see costs.py). Results with absurd numbers are flagged
and the PASS/FAIL verdict is withheld until leakage has been ruled out.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import costs
from .data import _guard
from .metrics import (
    absurdity_flags,
    buy_and_hold,
    pass_std_verdict,
    summarize,
    trades_per_year,
)
from .rules import (
    COST_STRESS_MULTIPLIERS,
    LOOKAHEAD_CHECK_DATES,
    LOOKAHEAD_SEED,
    TRAIN_END,
    TRAIN_EVAL_START,
    WEEKLY_TRADES_PER_YEAR,
    WEIGHT_TOLERANCE,
)


class LookaheadError(RuntimeError):
    """Raised when a strategy's decision changes once future data is removed."""


@dataclass
class BacktestResult:
    name: str
    stats: dict
    benchmark_stats: dict
    verdict: str                      # PASS / FAIL / WITHHELD (absurd)
    absurd: list[str]
    trades_per_year: float
    stress: dict                      # cost multiplier -> stats dict
    returns: pd.Series = field(repr=False, default=None)
    positions: pd.DataFrame = field(repr=False, default=None)

    def report(self) -> str:
        lines = [f"=== {self.name} ==="]
        if self.absurd:
            lines.append("!!! ABSURD RESULT — TREAT AS BUG. Hunt for leakage before")
            lines.append("!!! showing or recording this. Verdict withheld. Flags:")
            lines += [f"!!!   - {f}" for f in self.absurd]
        for mult in sorted(self.stress):
            s = self.stress[mult]
            tag = f"{mult:.0f}x costs"
            lines.append(
                f"[{tag}] total {s['total_return']:+.1%} | CAGR {s['cagr']:+.2%} | "
                f"vol {s['ann_vol']:.2%} | Sharpe {s['sharpe']:.2f} | "
                f"maxDD {s['max_drawdown']:.1%} | hit {s['hit_rate']:.1%}"
            )
        b = self.benchmark_stats
        lines.append(
            f"[B&H  ] total {b['total_return']:+.1%} | CAGR {b['cagr']:+.2%} | "
            f"vol {b['ann_vol']:.2%} | Sharpe {b['sharpe']:.2f} | "
            f"maxDD {b['max_drawdown']:.1%}"
        )
        lines.append(f"trades/yr: {self.trades_per_year:.1f}")
        lines.append(f"verdict vs buy-and-hold (return AND drawdown): {self.verdict}")
        return "\n".join(lines)


def _normalize(data, weights):
    """Align data dict + weights DataFrame on a common inner-joined index."""
    if isinstance(data, pd.DataFrame):
        data = {"ASSET": data}
    for k, df in data.items():
        _guard(df, f"data[{k}]")
    if isinstance(weights, pd.Series):
        only = list(data)[0] if len(data) == 1 else None
        if only is None:
            raise ValueError("Series weights require single-asset data.")
        weights = weights.to_frame(only)
    idx = None
    for df in data.values():
        idx = df.index if idx is None else idx.intersection(df.index)
    weights = weights.reindex(idx).fillna(0.0)
    unknown = set(weights.columns) - set(data)
    if unknown:
        raise ValueError(f"Weights reference assets with no data: {unknown}")
    opens = pd.DataFrame({k: data[k]["Open"].reindex(idx) for k in weights.columns})
    return data, weights, opens, idx


def _pnl(positions, opens, side_rate, rf_daily, mult):
    """Net daily returns for positions held open(t) -> open(t+1)."""
    r_oo = opens.shift(-1) / opens - 1.0
    turnover = positions.diff().abs()
    turnover.iloc[0] = positions.iloc[0].abs()
    trade_costs = (turnover * side_rate * mult).sum(axis=1)
    gross_ret = (positions * r_oo).sum(axis=1)
    gross_expo = positions.abs().sum(axis=1)
    short_notional = positions.clip(upper=0.0).abs().sum(axis=1)
    carry = costs.daily_carry(gross_expo, short_notional, rf_daily, mult)
    net = gross_ret + carry - trade_costs
    return net.iloc[:-1], turnover.sum(axis=1).iloc[:-1]  # last day has no next open


def _lookahead_check(strategy, data, weights_full, eval_index):
    rng = np.random.default_rng(LOOKAHEAD_SEED)
    n = min(LOOKAHEAD_CHECK_DATES, max(len(eval_index) - 2, 0))
    if n == 0:
        return
    cut_dates = pd.DatetimeIndex(rng.choice(eval_index[1:-1], size=n, replace=False))
    for d in sorted(cut_dates):
        trunc = {k: df.loc[:d] for k, df in data.items()}
        w_t = strategy(trunc if len(trunc) > 1 else list(trunc.values())[0])
        if isinstance(w_t, pd.Series):
            w_t = w_t.to_frame(weights_full.columns[0])
        if d not in w_t.index or d not in weights_full.index:
            continue
        a = w_t.loc[d].reindex(weights_full.columns).fillna(0.0).astype(float)
        b = weights_full.loc[d].astype(float)
        if not np.allclose(a.values, b.values, atol=1e-8, equal_nan=True):
            raise LookaheadError(
                f"Lookahead detected: decision on {d.date()} changes when future "
                f"data is removed (truncated={a.to_dict()} vs full={b.to_dict()}). "
                f"The strategy is using same-day or future information."
            )


def run_backtest(strategy, data, name="unnamed",
                 start=TRAIN_EVAL_START, end=TRAIN_END,
                 benchmark_assets=None, rf_daily=None) -> BacktestResult:
    """Run a strategy under the full protocol and return a BacktestResult.

    strategy: callable(data) -> weight Series/DataFrame; value at day t is the
              target weight decided at t's close (engine executes at t+1 open).
    data:     DataFrame (single asset) or dict[ticker, DataFrame] of adjusted
              daily bars; must be loaded through engine.data.load (train only).
    """
    raw_weights = strategy(data)
    data_dict, weights, opens, idx = _normalize(data, raw_weights)

    end = min(pd.Timestamp(end), pd.Timestamp(TRAIN_END))
    start = pd.Timestamp(start)
    eval_index = idx[(idx >= start) & (idx <= end)]
    if len(eval_index) < 30:
        raise ValueError("Fewer than 30 evaluation days — check dates/universe.")

    _lookahead_check(strategy, data_dict, weights, eval_index)

    if rf_daily is None:
        from .data import risk_free_daily
        rf_daily = risk_free_daily(idx)
    else:
        rf_daily = rf_daily.reindex(idx).fillna(0.0)

    positions = weights.shift(1).fillna(0.0)  # decided close t-1, held from open t
    side_rate = costs.trade_cost_rate("etf")  # futures assets get their own path later

    stress = {}
    turnover_eval = None
    for mult in (1.0,) + COST_STRESS_MULTIPLIERS:
        net, turnover = _pnl(positions, opens, side_rate, rf_daily, mult)
        net_eval = net.loc[(net.index >= start) & (net.index <= end)]
        active = positions.abs().sum(axis=1).reindex(net_eval.index) > WEIGHT_TOLERANCE
        stress[mult] = summarize(net_eval, rf_daily, active_mask=active)
        if mult == 1.0:
            turnover_eval = turnover.loc[net_eval.index]
            base_returns = net_eval

    tpy = trades_per_year(turnover_eval)
    if tpy <= WEEKLY_TRADES_PER_YEAR:
        stress = {1.0: stress[1.0]}  # stress reporting required only if > weekly

    # A benchmark asset need not be tradeable by the strategy (e.g. a book that
    # only references SPY for its volatility is still measured against SPY).
    bench_cols = benchmark_assets or list(weights.columns)
    missing = [c for c in bench_cols if c not in opens.columns]
    if missing:
        extra = {c: data_dict[c]["Open"].reindex(idx) for c in missing}
        bench_opens = pd.concat([opens, pd.DataFrame(extra, index=idx)], axis=1)
    else:
        bench_opens = opens
    bench_opens = bench_opens[bench_cols].loc[eval_index]
    bench = buy_and_hold(bench_opens, rf_daily, side_rate)

    flags = absurdity_flags(stress[1.0], tpy)
    verdict = "WITHHELD (absurd — hunt leakage)" if flags else \
        pass_std_verdict(stress[1.0], bench)

    return BacktestResult(
        name=name, stats=stress[1.0], benchmark_stats=bench, verdict=verdict,
        absurd=flags, trades_per_year=tpy, stress=stress,
        returns=base_returns, positions=positions.loc[eval_index],
    )
