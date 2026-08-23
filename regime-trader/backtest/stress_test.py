"""Stress testing: crash injection, gap simulation, regime misclassification.

Each test perturbs historical bars and re-runs the full walk-forward
backtest, verifying that drawdown control (the circuit breaker) contains
damage even under shocks the model has never seen — including deliberately
wrong regime classifications.

Shocks are applied persistently: scaling bar t and everything after it, so
a crash is a lasting repricing rather than a one-bar blip that instantly
mean-reverts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

from backtest.backtester import BacktestResult, WalkForwardBacktester
from backtest.performance import max_drawdown
from core.data.feature_engineering import true_range, wilder_smooth

logger = logging.getLogger("regime_trader.stress")

PRICE_COLUMNS = ("open", "high", "low", "close")


@dataclass(frozen=True)
class StressConfig:
    """Stress-suite parameters."""

    n_sims: int = 100                 # Monte Carlo runs for crash/gap tests
    n_crashes: int = 10               # single-day crashes injected per sim
    crash_range: tuple[float, float] = (-0.15, -0.05)  # gap magnitude range
    n_gaps: int = 10                  # overnight gaps injected per sim
    gap_atr_range: tuple[float, float] = (2.0, 5.0)    # gap size in ATRs
    n_shuffles: int = 10              # misclassification runs
    seed: int = 0


@dataclass
class CrashTestResult:
    """Monte Carlo crash-injection outcome."""

    per_sim: pd.DataFrame             # max_drawdown, total_return, fired
    mean_max_drawdown: float
    worst_max_drawdown: float
    pct_breaker_fired: float
    mean_total_return: float


@dataclass
class GapTestResult:
    """Overnight-gap outcome: expected loss (exposure x gap) vs actual."""

    per_gap: pd.DataFrame             # timestamp, gap_return, exposure,
                                      # expected_loss, actual_return
    mean_expected_loss: float
    mean_actual_loss: float


@dataclass
class MisclassificationResult:
    """Outcome of running with deliberately shuffled regime mappings."""

    baseline_max_drawdown: float
    shuffled: pd.DataFrame            # max_drawdown, total_return, fired
    worst_shuffled_drawdown: float
    pct_breaker_fired: float
    contained: bool                   # risk limits held despite wrong regimes


# ----------------------------------------------------------- shock injection

def inject_crashes(bars: pd.DataFrame, positions: list[int],
                   magnitudes: list[float]) -> pd.DataFrame:
    """Apply persistent single-day price gaps: every price column from
    position p onward is scaled by (1 + magnitude)."""
    scale = np.ones(len(bars))
    for p, mag in zip(positions, magnitudes):
        scale[p:] *= 1.0 + mag
    out = bars.copy()
    for col in PRICE_COLUMNS:
        out[col] = out[col] * scale
    return out


def inject_gaps(bars: pd.DataFrame, positions: list[int],
                atr_mults: list[float],
                atr_window: int = 14) -> tuple[pd.DataFrame, list[tuple[int, float]]]:
    """Apply persistent overnight down-gaps sized in ATRs of the prior bar.

    Returns the stressed bars and [(position, gap_return), ...].
    """
    atr = wilder_smooth(true_range(bars["high"], bars["low"], bars["close"]),
                        atr_window)
    scale = np.ones(len(bars))
    applied: list[tuple[int, float]] = []
    for p, k in zip(positions, atr_mults):
        prev_close = float(bars["close"].iloc[p - 1])
        prev_atr = float(atr.iloc[p - 1])
        if not np.isfinite(prev_atr) or prev_close <= 0:
            continue
        gap_ret = max(-0.5, -k * prev_atr / prev_close)  # sanity floor
        scale[p:] *= 1.0 + gap_ret
        applied.append((p, gap_ret))
    out = bars.copy()
    for col in PRICE_COLUMNS:
        out[col] = out[col] * scale
    return out, applied


class StressTester:
    """Runs the walk-forward backtester over shock-injected histories.

    Args:
        backtester: Configured backtester re-run per scenario. For Monte
            Carlo suites use light HMM params (few candidates/inits) —
            every simulation is a full walk-forward run.
        config: Stress-suite parameters.
    """

    def __init__(self, backtester: WalkForwardBacktester,
                 config: StressConfig | None = None) -> None:
        self.backtester = backtester
        self.config = config or StressConfig()

    def _shock_positions(self, n_bars: int, rng: np.random.Generator,
                         count: int) -> list[int]:
        """Random shock points in the later 60% of history, where they land
        inside (or near) the out-of-sample region."""
        lo = max(int(n_bars * 0.4), 2)
        return sorted(rng.choice(np.arange(lo, n_bars - 1), size=count,
                                 replace=False).tolist())

    # ------------------------------------------------------------- a) crash

    def crash_test(self, bars: pd.DataFrame,
                   symbol: str = "ASSET") -> CrashTestResult:
        """Monte Carlo crash injection: -5% to -15% single-day gaps at
        random points; reports drawdown stats and breaker-fire rate."""
        cfg = self.config
        rng = np.random.default_rng(cfg.seed)
        rows = []
        for sim in range(cfg.n_sims):
            pos = self._shock_positions(len(bars), rng, cfg.n_crashes)
            mags = rng.uniform(*cfg.crash_range, size=cfg.n_crashes).tolist()
            res = self.backtester.run(inject_crashes(bars, pos, mags), symbol)
            mdd, _ = max_drawdown(res.equity_curve)
            rows.append({"sim": sim, "max_drawdown": mdd,
                         "total_return": res.total_return,
                         "fired": res.circuit_breaker_fires > 0})
            logger.info("crash sim %d/%d: mdd=%.1f%% fired=%s", sim + 1,
                        cfg.n_sims, mdd * 100, rows[-1]["fired"])
        df = pd.DataFrame(rows)
        return CrashTestResult(
            per_sim=df,
            mean_max_drawdown=float(df["max_drawdown"].mean()),
            worst_max_drawdown=float(df["max_drawdown"].max()),
            pct_breaker_fired=float(df["fired"].mean()),
            mean_total_return=float(df["total_return"].mean()),
        )

    # --------------------------------------------------------------- b) gap

    def gap_test(self, bars: pd.DataFrame,
                 symbol: str = "ASSET") -> GapTestResult:
        """Overnight gaps of 2-5x ATR; compares the loss you'd expect from
        exposure x gap size against the realized equity hit."""
        cfg = self.config
        rng = np.random.default_rng(cfg.seed + 1)
        rows = []
        for sim in range(cfg.n_sims):
            pos = self._shock_positions(len(bars), rng, cfg.n_gaps)
            mults = rng.uniform(*cfg.gap_atr_range, size=cfg.n_gaps).tolist()
            stressed, applied = inject_gaps(bars, pos, mults)
            res = self.backtester.run(stressed, symbol)
            eq_rets = res.equity_curve.pct_change()
            exposure = res.regime_history["effective_alloc"].shift(1)
            for p, gap_ret in applied:
                ts = bars.index[p]
                if ts not in eq_rets.index:
                    continue  # gap landed outside the out-of-sample region
                expo = float(exposure.get(ts, np.nan))
                if not np.isfinite(expo):
                    continue
                rows.append({
                    "sim": sim, "timestamp": ts, "gap_return": gap_ret,
                    "exposure": expo,
                    "expected_loss": expo * gap_ret,
                    "actual_return": float(eq_rets.loc[ts]),
                })
            logger.info("gap sim %d/%d complete", sim + 1, cfg.n_sims)
        df = pd.DataFrame(rows)
        return GapTestResult(
            per_gap=df,
            mean_expected_loss=float(df["expected_loss"].mean()) if len(df) else np.nan,
            mean_actual_loss=float(df["actual_return"].mean()) if len(df) else np.nan,
        )

    # -------------------------------------------- c) regime misclassification

    def misclassification_test(self, bars: pd.DataFrame,
                               symbol: str = "ASSET") -> MisclassificationResult:
        """Deliberately shuffle the regime->strategy mapping each fold and
        verify risk management contains the damage. If drawdowns blow far
        past the circuit-breaker level, risk control isn't independent
        enough of the classifier."""
        cfg = self.config
        baseline = self.backtester.run(bars, symbol)
        base_mdd, _ = max_drawdown(baseline.equity_curve)
        rows = []
        for k in range(cfg.n_shuffles):
            shuffled_bt = WalkForwardBacktester(
                config=self.backtester.config,
                hmm_params=self.backtester.hmm_params,
                strategy_config=self.backtester.strategy_config,
                feature_engineer=self.backtester.feature_engineer,
                shuffle_regimes_seed=cfg.seed + 100 + k,
            )
            res = shuffled_bt.run(bars, symbol)
            mdd, _ = max_drawdown(res.equity_curve)
            rows.append({"shuffle": k, "max_drawdown": mdd,
                         "total_return": res.total_return,
                         "fired": res.circuit_breaker_fires > 0})
            logger.info("shuffle %d/%d: mdd=%.1f%%", k + 1, cfg.n_shuffles,
                        mdd * 100)
        df = pd.DataFrame(rows)
        halt = self.backtester.config.max_dd_halt or 1.0
        worst = float(df["max_drawdown"].max())
        # Contained: wrong regime classifications must not make drawdowns
        # meaningfully worse than the baseline run with the same circuit
        # breaker. (Cumulative drawdown can legitimately accumulate across
        # halt/restart cycles in both cases — what matters is that the
        # damage is bounded by the risk layer, not by classifier accuracy.)
        bound = max(halt + 0.10, base_mdd + 0.10)
        return MisclassificationResult(
            baseline_max_drawdown=base_mdd,
            shuffled=df,
            worst_shuffled_drawdown=worst,
            pct_breaker_fired=float(df["fired"].mean()),
            contained=worst <= bound,
        )

    # -------------------------------------------------------------- suite

    def run_suite(self, bars: pd.DataFrame, symbol: str = "ASSET"
                  ) -> dict[str, Any]:
        """Run all three stress tests and return their results."""
        return {
            "crash": self.crash_test(bars, symbol),
            "gap": self.gap_test(bars, symbol),
            "misclassification": self.misclassification_test(bars, symbol),
        }


def print_stress_results(results: dict[str, Any],
                         console: Console | None = None) -> None:
    """Render the stress-suite results as rich tables."""
    con = console or Console()
    crash: CrashTestResult = results["crash"]
    gap: GapTestResult = results["gap"]
    mis: MisclassificationResult = results["misclassification"]

    t = Table(title="Crash injection (Monte Carlo)")
    t.add_column("metric")
    t.add_column("value", justify="right")
    t.add_row("Simulations", str(len(crash.per_sim)))
    t.add_row("Mean max drawdown", f"{crash.mean_max_drawdown:.1%}")
    t.add_row("Worst max drawdown", f"{crash.worst_max_drawdown:.1%}")
    t.add_row("Circuit breaker fired", f"{crash.pct_breaker_fired:.0%} of sims")
    t.add_row("Mean total return", f"{crash.mean_total_return:+.1%}")
    con.print(t)

    t = Table(title="Overnight gap risk (2-5x ATR)")
    t.add_column("metric")
    t.add_column("value", justify="right")
    t.add_row("Gaps landing in OOS", str(len(gap.per_gap)))
    t.add_row("Mean expected loss (exposure x gap)",
              f"{gap.mean_expected_loss:.2%}" if np.isfinite(gap.mean_expected_loss) else "n/a")
    t.add_row("Mean actual equity move",
              f"{gap.mean_actual_loss:.2%}" if np.isfinite(gap.mean_actual_loss) else "n/a")
    con.print(t)

    t = Table(title="Regime misclassification (shuffled mappings)")
    t.add_column("metric")
    t.add_column("value", justify="right")
    t.add_row("Baseline max drawdown", f"{mis.baseline_max_drawdown:.1%}")
    t.add_row("Worst shuffled drawdown", f"{mis.worst_shuffled_drawdown:.1%}")
    t.add_row("Breaker fired", f"{mis.pct_breaker_fired:.0%} of runs")
    t.add_row("Risk containment", "PASS" if mis.contained else "FAIL — risk "
              "management is not independent of the classifier")
    con.print(t)
