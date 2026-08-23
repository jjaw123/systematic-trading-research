"""Performance analytics: core metrics, regime/confidence breakdowns,
benchmark comparisons, worst-case stats, rich rendering, and CSV export.

"Trades" in an allocation-based backtest are rebalance events; per-trade
P&L is measured over the segment from one rebalance to the next.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

from backtest.backtester import BacktestResult

TRADING_DAYS = 252
CONFIDENCE_BUCKETS = [(0.0, 0.50, "< 50%"), (0.50, 0.60, "50-60%"),
                      (0.60, 0.70, "60-70%"), (0.70, 1.01, "70%+")]


# ------------------------------------------------------------ metric helpers

def sharpe_ratio(returns: pd.Series, rf: float = 0.045,
                 ppy: int = TRADING_DAYS) -> float:
    """Annualized Sharpe of a period-return series."""
    if len(returns) < 2:
        return np.nan
    excess = returns - rf / ppy
    sd = excess.std()
    # Guard against numerically-zero volatility (e.g. a flat equity curve),
    # which would otherwise produce absurd +/-1e17 ratios.
    return float(excess.mean() / sd * np.sqrt(ppy)) if sd > 1e-12 else np.nan


def sortino_ratio(returns: pd.Series, rf: float = 0.045,
                  ppy: int = TRADING_DAYS) -> float:
    """Annualized Sortino (downside deviation denominator)."""
    if len(returns) < 2:
        return np.nan
    excess = returns - rf / ppy
    downside = excess[excess < 0]
    dd = np.sqrt((downside ** 2).mean()) if len(downside) else 0.0
    return float(excess.mean() / dd * np.sqrt(ppy)) if dd > 1e-12 else np.nan


def max_drawdown(equity: pd.Series) -> tuple[float, int]:
    """(max peak-to-trough drawdown as a positive fraction, longest
    underwater stretch in bars)."""
    peak = equity.cummax()
    dd = 1.0 - equity / peak
    underwater = dd > 0
    longest = run = 0
    for u in underwater:
        run = run + 1 if u else 0
        longest = max(longest, run)
    return float(dd.max()), int(longest)


def cagr(equity: pd.Series, ppy: int = TRADING_DAYS) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0 or equity.iloc[-1] <= 0:
        return np.nan
    years = (len(equity) - 1) / ppy
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) if years > 0 else np.nan


def _max_consecutive_losses(returns: pd.Series) -> int:
    longest = run = 0
    for r in returns:
        run = run + 1 if r < 0 else 0
        longest = max(longest, run)
    return longest


@dataclass(frozen=True)
class PerformanceReport:
    """Summary statistics for one backtest run."""

    total_return: float
    cagr: float
    volatility: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    max_drawdown_duration_days: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    n_trades: int
    avg_holding_bars: float
    exposure: float
    worst_day: float
    worst_week: float
    worst_month: float
    max_consecutive_losses: int


class PerformanceAnalyzer:
    """Computes performance statistics and benchmark comparisons."""

    def __init__(self, risk_free_rate: float = 0.045,
                 periods_per_year: int = TRADING_DAYS) -> None:
        self.rf = risk_free_rate
        self.ppy = periods_per_year

    # ------------------------------------------------------------- core

    def analyze(self, result: BacktestResult) -> PerformanceReport:
        """Compute the full report for a backtest result."""
        eq = result.equity_curve
        rets = eq.pct_change().dropna()
        mdd, dd_dur = max_drawdown(eq)
        segs = self.trade_segments(result)
        wins = segs[segs["pnl"] > 0] if len(segs) else segs
        losses = segs[segs["pnl"] < 0] if len(segs) else segs
        gross_win = float(wins["pnl"].sum()) if len(segs) else 0.0
        gross_loss = float(-losses["pnl"].sum()) if len(segs) else 0.0
        growth = cagr(eq, self.ppy)
        return PerformanceReport(
            total_return=float(eq.iloc[-1] / eq.iloc[0] - 1),
            cagr=growth,
            volatility=float(rets.std() * np.sqrt(self.ppy)),
            sharpe=sharpe_ratio(rets, self.rf, self.ppy),
            sortino=sortino_ratio(rets, self.rf, self.ppy),
            calmar=float(growth / mdd) if mdd > 0 and np.isfinite(growth) else np.nan,
            max_drawdown=mdd,
            max_drawdown_duration_days=dd_dur,
            win_rate=float(len(wins) / len(segs)) if len(segs) else np.nan,
            avg_win=float(wins["pnl"].mean()) if len(wins) else np.nan,
            avg_loss=float(losses["pnl"].mean()) if len(losses) else np.nan,
            profit_factor=float(gross_win / gross_loss) if gross_loss > 0 else np.inf,
            n_trades=len(result.trades),
            avg_holding_bars=float(segs["bars"].mean()) if len(segs) else np.nan,
            exposure=float(result.regime_history["effective_alloc"].mean())
            if len(result.regime_history) else np.nan,
            worst_day=float(rets.min()) if len(rets) else np.nan,
            worst_week=float(((1 + rets).rolling(5).apply(np.prod) - 1).min())
            if len(rets) >= 5 else np.nan,
            worst_month=float(((1 + rets).rolling(21).apply(np.prod) - 1).min())
            if len(rets) >= 21 else np.nan,
            max_consecutive_losses=_max_consecutive_losses(rets),
        )

    def trade_segments(self, result: BacktestResult) -> pd.DataFrame:
        """P&L per holding segment (one rebalance to the next)."""
        eq = result.equity_curve
        trades = result.trades
        if trades.empty:
            return pd.DataFrame(columns=["start", "end", "pnl", "ret", "bars",
                                         "regime_label", "confidence"])
        rows = []
        stamps = list(trades["timestamp"]) + [eq.index[-1]]
        for k in range(len(trades)):
            t0, t1 = stamps[k], stamps[k + 1]
            if t0 == t1:
                continue
            e0, e1 = float(eq.loc[t0]), float(eq.loc[t1])
            rows.append({
                "start": t0, "end": t1, "pnl": e1 - e0,
                "ret": e1 / e0 - 1,
                "bars": int(eq.index.get_loc(t1) - eq.index.get_loc(t0)),
                "regime_label": trades.iloc[k]["regime_label"],
                "confidence": trades.iloc[k]["confidence"],
            })
        return pd.DataFrame(rows)

    # ------------------------------------------------------- breakdowns

    def regime_breakdown(self, result: BacktestResult) -> pd.DataFrame:
        """Per-regime performance: time in regime, compounded return,
        Sharpe, and trade stats. Daily returns are attributed to the regime
        in force at that bar."""
        hist = result.regime_history
        rets = result.equity_curve.pct_change().dropna()
        segs = self.trade_segments(result)
        rows = []
        for label, grp in hist.groupby("label"):
            r = rets.reindex(grp.index).dropna()
            seg = segs[segs["regime_label"] == label] if len(segs) else segs
            wins = (seg["pnl"] > 0).sum() if len(seg) else 0
            rows.append({
                "regime": label,
                "pct_time": len(grp) / len(hist),
                "return_contribution": float((1 + r).prod() - 1) if len(r) else 0.0,
                "sharpe": sharpe_ratio(r, self.rf, self.ppy),
                "n_trades": len(seg),
                "win_rate": wins / len(seg) if len(seg) else np.nan,
                "avg_trade_pnl": float(seg["pnl"].mean()) if len(seg) else np.nan,
            })
        return pd.DataFrame(rows).sort_values("pct_time", ascending=False)

    def confidence_breakdown(self, result: BacktestResult) -> pd.DataFrame:
        """Trade stats bucketed by regime confidence at trade time. If
        high-confidence buckets outperform, the HMM is adding value."""
        segs = self.trade_segments(result)
        rows = []
        for lo, hi, name in CONFIDENCE_BUCKETS:
            seg = segs[(segs["confidence"] >= lo) & (segs["confidence"] < hi)] \
                if len(segs) else segs
            n = len(seg)
            sd = seg["ret"].std() if n > 1 else np.nan
            rows.append({
                "confidence": name, "trades": n,
                "sharpe_per_trade": float(seg["ret"].mean() / sd) if n > 1 and sd and sd > 0 else np.nan,
                "win_rate": float((seg["pnl"] > 0).mean()) if n else np.nan,
                "avg_pnl": float(seg["pnl"].mean()) if n else np.nan,
            })
        return pd.DataFrame(rows)

    # ------------------------------------------------------- benchmarks

    def buy_and_hold(self, result: BacktestResult) -> pd.Series:
        """Hold the asset for the whole out-of-sample period."""
        close = result.bars["close"].reindex(result.equity_curve.index)
        cap = result.config.initial_capital * (1 - result.config.slippage_pct)
        return cap * close / close.iloc[0]

    def sma200_trend(self, result: BacktestResult) -> pd.Series:
        """Long above the 200 SMA, cash below (signal shifts one bar)."""
        close = result.bars["close"]
        pos = (close > close.rolling(200).mean()).astype(float).shift(1).fillna(0.0)
        rets = close.pct_change().fillna(0.0) * pos
        costs = pos.diff().abs().fillna(0.0) * result.config.slippage_pct
        eq = result.config.initial_capital * (1 + rets - costs).cumprod()
        return eq.reindex(result.equity_curve.index)

    def random_baseline(self, result: BacktestResult, n_seeds: int = 100,
                        seed: int = 0) -> pd.DataFrame:
        """Random allocation changes at the strategy's own frequency, drawn
        from the strategy's own allocation levels — same sizing rules, no
        regime information. One row of stats per seed."""
        eq_index = result.equity_curve.index
        close = result.bars["close"].reindex(eq_index)
        rets = close.pct_change().fillna(0.0)
        n_changes = max(len(result.trades), 1)
        choices = result.trades["new_allocation"].dropna().unique() \
            if len(result.trades) else np.array([0.6, 0.95])
        rng = np.random.default_rng(seed)
        rows = []
        for _ in range(n_seeds):
            points = np.sort(rng.choice(len(eq_index), size=min(n_changes, len(eq_index) - 1), replace=False))
            alloc = np.zeros(len(eq_index))
            current = float(rng.choice(choices))
            k = 0
            for i in range(len(eq_index)):
                while k < len(points) and points[k] == i:
                    current = float(rng.choice(choices))
                    k += 1
                alloc[i] = current
            pos = pd.Series(alloc, index=eq_index).shift(1).fillna(0.0)
            costs = pos.diff().abs().fillna(0.0) * result.config.slippage_pct
            eq = result.config.initial_capital * (1 + rets * pos - costs).cumprod()
            mdd, _ = max_drawdown(eq)
            rows.append({"total_return": float(eq.iloc[-1] / eq.iloc[0] - 1),
                         "sharpe": sharpe_ratio(eq.pct_change().dropna(), self.rf, self.ppy),
                         "max_drawdown": mdd})
        return pd.DataFrame(rows)

    def compare_benchmarks(self, result: BacktestResult, n_random: int = 100,
                           seed: int = 0) -> pd.DataFrame:
        """Strategy vs buy-and-hold, 200-SMA trend, and the random baseline
        (mean ± std over ``n_random`` seeds)."""
        def _stats(eq: pd.Series) -> dict[str, float]:
            mdd, _ = max_drawdown(eq.dropna())
            return {"total_return": float(eq.iloc[-1] / eq.iloc[0] - 1),
                    "cagr": cagr(eq.dropna(), self.ppy),
                    "sharpe": sharpe_ratio(eq.pct_change().dropna(), self.rf, self.ppy),
                    "max_drawdown": mdd}

        rnd = self.random_baseline(result, n_seeds=n_random, seed=seed)
        rows = {
            "strategy": _stats(result.equity_curve),
            "buy_and_hold": _stats(self.buy_and_hold(result)),
            "sma200_trend": _stats(self.sma200_trend(result)),
            "random_mean": {"total_return": rnd["total_return"].mean(),
                            "cagr": np.nan,
                            "sharpe": rnd["sharpe"].mean(),
                            "max_drawdown": rnd["max_drawdown"].mean()},
            "random_std": {"total_return": rnd["total_return"].std(),
                           "cagr": np.nan,
                           "sharpe": rnd["sharpe"].std(),
                           "max_drawdown": rnd["max_drawdown"].std()},
        }
        return pd.DataFrame(rows).T

    # ------------------------------------------------------------ output

    def print_report(self, result: BacktestResult, report: PerformanceReport,
                     benchmark_df: pd.DataFrame | None = None,
                     console: Console | None = None) -> None:
        """Render the full report as rich tables."""
        con = console or Console()

        def pct(x: float) -> str:
            return f"{x:+.2%}" if np.isfinite(x) else "n/a"

        def num(x: float, fmt: str = "{:.2f}") -> str:
            return fmt.format(x) if np.isfinite(x) else "n/a"

        core = Table(title=f"{result.symbol} — walk-forward performance")
        core.add_column("metric")
        core.add_column("value", justify="right")
        for name, val in [
            ("Total return", pct(report.total_return)),
            ("CAGR", pct(report.cagr)),
            ("Volatility (ann.)", pct(report.volatility)),
            ("Sharpe", num(report.sharpe)),
            ("Sortino", num(report.sortino)),
            ("Calmar", num(report.calmar)),
            ("Max drawdown", pct(-report.max_drawdown)),
            ("Max DD duration", f"{report.max_drawdown_duration_days} days"),
            ("Trades", str(report.n_trades)),
            ("Win rate", num(report.win_rate, "{:.1%}")),
            ("Avg win / loss", f"{num(report.avg_win, '{:,.0f}')} / {num(report.avg_loss, '{:,.0f}')}"),
            ("Profit factor", num(report.profit_factor)),
            ("Avg holding", num(report.avg_holding_bars, "{:.1f} bars")),
            ("Exposure (avg)", num(report.exposure, "{:.1%}")),
            ("Worst day/week/month", f"{pct(report.worst_day)} / {pct(report.worst_week)} / {pct(report.worst_month)}"),
            ("Max consecutive down days", str(report.max_consecutive_losses)),
            ("Circuit breaker fires", str(result.circuit_breaker_fires)),
        ]:
            core.add_row(name, val)
        con.print(core)

        reg = Table(title="Regime breakdown")
        for col in ("Regime", "% Time", "Return", "Sharpe", "Trades",
                    "Win rate", "Avg P&L"):
            reg.add_column(col, justify="right")
        for _, r in self.regime_breakdown(result).iterrows():
            reg.add_row(str(r["regime"]), f"{r['pct_time']:.1%}",
                        pct(r["return_contribution"]), num(r["sharpe"]),
                        str(int(r["n_trades"])), num(r["win_rate"], "{:.1%}"),
                        num(r["avg_trade_pnl"], "{:,.0f}"))
        con.print(reg)

        confb = Table(title="Confidence buckets")
        for col in ("Confidence", "Trades", "Sharpe/trade", "Win rate", "Avg P&L"):
            confb.add_column(col, justify="right")
        for _, r in self.confidence_breakdown(result).iterrows():
            confb.add_row(str(r["confidence"]), str(int(r["trades"])),
                          num(r["sharpe_per_trade"]), num(r["win_rate"], "{:.1%}"),
                          num(r["avg_pnl"], "{:,.0f}"))
        con.print(confb)

        if benchmark_df is not None:
            bench = Table(title="Benchmark comparison")
            bench.add_column("series")
            for col in benchmark_df.columns:
                bench.add_column(col, justify="right")
            for name, r in benchmark_df.iterrows():
                bench.add_row(str(name), *[num(v, "{:.3f}") for v in r])
            con.print(bench)

    def export_csvs(self, result: BacktestResult, out_dir: str | Path,
                    benchmark_df: pd.DataFrame | None = None) -> list[Path]:
        """Write equity_curve.csv, trade_log.csv, regime_history.csv, and
        benchmark_comparison.csv (when provided). Returns written paths."""
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = []
        for name, obj in [("equity_curve.csv", result.equity_curve),
                          ("trade_log.csv", result.trades),
                          ("regime_history.csv", result.regime_history)]:
            p = out / name
            obj.to_csv(p)
            paths.append(p)
        if benchmark_df is not None:
            p = out / "benchmark_comparison.csv"
            benchmark_df.to_csv(p)
            paths.append(p)
        return paths
