"""Walk-forward allocation backtester.

ALLOCATION-BASED: no individual trade entries/exits. Each bar the detected
volatility regime sets a target portfolio allocation; the portfolio
rebalances only when the target drifts meaningfully from the current
allocation. Rolling in-sample windows retrain the HMM (BIC selection) and
every evaluation bar is strictly out-of-sample for the model that scores it.

Look-ahead hygiene:
- Features are computed once on full history — safe because the feature
  pipeline is causal (proven by tests/test_look_ahead.py): row t is
  identical with or without future bars.
- The HMM is fit on in-sample rows only; out-of-sample bars are classified
  with filtered (forward-algorithm) probabilities.
- A signal decided on bar t's close fills at bar t+1's OPEN, with slippage.

Allocation math (margin-correct):
    equity        = cash + shares * price
    target_shares = int(equity * target_allocation / price)
    cash         -= (target_shares - shares) * price
With leverage (target_allocation > 1.0) cash goes negative — that is margin
debt, and equity = cash + shares * price remains correct.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from core.data.feature_engineering import FeatureEngineer
from core.hmm_engine import HMMEngine, RegimeLabel, RegimeState
from core.regime_strategies import StrategyConfig, StrategyOrchestrator

logger = logging.getLogger("regime_trader.backtest")

TRADE_COLUMNS = [
    "timestamp", "symbol", "side", "delta_shares", "price", "prev_shares",
    "new_shares", "prev_allocation", "new_allocation", "equity_at_open",
    "regime_id", "regime_label", "confidence", "strategy", "reason", "fold",
]


@dataclass(frozen=True)
class BacktestConfig:
    """Walk-forward backtest parameters (mirrors the ``backtest`` settings)."""

    initial_capital: float = 100_000.0
    slippage_pct: float = 0.0005      # per-side, applied on every rebalance
    commission: float = 0.0           # Alpaca is commission-free
    train_window: int = 252           # in-sample bars per fold
    test_window: int = 126            # out-of-sample bars per fold
    step_size: int = 126              # roll-forward step
    risk_free_rate: float = 0.045
    rebalance_threshold: float = 0.10  # min allocation drift to trade
    max_dd_halt: float | None = 0.10   # circuit breaker: flat for the rest of
                                       # the fold when dd-from-peak exceeds this


@dataclass
class BacktestResult:
    """Output of one full walk-forward run."""

    symbol: str
    config: BacktestConfig
    equity_curve: pd.Series           # equity at each out-of-sample bar close
    trades: pd.DataFrame              # one row per executed rebalance
    regime_history: pd.DataFrame      # per-bar regime + allocation record
    windows: list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]
    fold_metadata: list[dict[str, Any]]
    circuit_breaker_fires: int
    bars: pd.DataFrame                # the OHLCV history backtested over

    @property
    def final_equity(self) -> float:
        return float(self.equity_curve.iloc[-1])

    @property
    def total_return(self) -> float:
        return self.final_equity / self.config.initial_capital - 1.0


class WalkForwardBacktester:
    """Runs walk-forward backtests of the regime allocation system.

    Args:
        config: Walk-forward parameters.
        hmm_params: Overrides for the per-fold :class:`HMMEngine`
            (``min_train_bars`` is always forced to ``train_window``).
        strategy_config: StrategyConfig or the ``strategy`` settings dict.
        feature_engineer: Feature pipeline (default: standard config).
        shuffle_regimes_seed: When set, each fold's regime->strategy mapping
            is randomly permuted — used by stress tests to verify risk
            containment under deliberate misclassification.
        quiet_hmm_logs: Suppress per-bar regime-change logs during the run.
    """

    def __init__(
        self,
        config: BacktestConfig | None = None,
        hmm_params: dict[str, Any] | None = None,
        strategy_config: StrategyConfig | dict[str, Any] | None = None,
        feature_engineer: FeatureEngineer | None = None,
        shuffle_regimes_seed: int | None = None,
        quiet_hmm_logs: bool = True,
    ) -> None:
        self.config = config or BacktestConfig()
        self.hmm_params = dict(hmm_params or {})
        self.strategy_config = strategy_config
        self.feature_engineer = feature_engineer or FeatureEngineer()
        self.shuffle_regimes_seed = shuffle_regimes_seed
        self.quiet_hmm_logs = quiet_hmm_logs

    def _engine_params(self) -> dict[str, Any]:
        params = {"n_candidates": [3, 4, 5, 6, 7], "n_init": 10}
        params.update(self.hmm_params)
        params["min_train_bars"] = self.config.train_window
        return params

    def run(self, bars: pd.DataFrame, symbol: str = "ASSET") -> BacktestResult:
        """Execute the full walk-forward loop over history."""
        cfg = self.config
        bars = bars.sort_index()
        features = self.feature_engineer.compute_features(bars)
        if len(features) < cfg.train_window + 10:
            raise ValueError(
                f"only {len(features)} feature rows after warm-up; need at "
                f"least train_window ({cfg.train_window}) + 10. Provide more "
                "history (feature warm-up consumes ~520 bars)."
            )
        bar_pos = {ts: i for i, ts in enumerate(bars.index)}
        open_, close = bars["open"], bars["close"]

        hmm_logger = logging.getLogger("regime_trader.hmm")
        hmmlearn_logger = logging.getLogger("hmmlearn.base")
        prior_levels = (hmm_logger.level, hmmlearn_logger.level)
        if self.quiet_hmm_logs:
            hmm_logger.setLevel(logging.ERROR)
            hmmlearn_logger.setLevel(logging.ERROR)

        cash, shares = cfg.initial_capital, 0
        peak = cfg.initial_capital
        pending: tuple[float, dict[str, Any]] | None = None
        fires = 0
        equity_idx: list[pd.Timestamp] = []
        equity_vals: list[float] = []
        trade_rows: list[dict[str, Any]] = []
        regime_rows: list[dict[str, Any]] = []
        windows: list[tuple] = []
        fold_meta: list[dict[str, Any]] = []
        engine: HMMEngine | None = None
        orch: StrategyOrchestrator | None = None

        try:
            fold = 0
            prev_fold_halted = False
            for tr0 in range(0, len(features) - cfg.train_window - 1, cfg.step_size):
                tr1 = tr0 + cfg.train_window
                te1 = min(tr1 + cfg.test_window, len(features))
                if te1 - tr1 < 5:
                    break
                engine, orch = self._fit_fold(features.iloc[tr0:tr1], fold,
                                              engine, orch)
                series = engine.predict_series(features.iloc[tr0:te1])
                probs = engine._last_probs  # filtered probs aligned to series
                windows.append((features.index[tr0], features.index[tr1 - 1],
                                features.index[tr1], features.index[te1 - 1]))
                fold_meta.append({
                    "fold": fold,
                    "n_regimes": engine.metadata.get("n_regimes"),
                    "bic": engine.metadata.get("bic"),
                    "train_bars": tr1 - tr0,
                })
                halted = False
                # After a halt, the next fold restarts with a fresh risk
                # budget: the peak resets to current equity. Otherwise the
                # old peak would re-trigger the breaker on the first bar of
                # every subsequent fold, leaving the portfolio flat forever.
                reset_peak = prev_fold_halted

                for j in range(tr1, te1):
                    ts = features.index[j]
                    b = bar_pos[ts]
                    # 1) execute the pending rebalance at this bar's open
                    if pending is not None:
                        cash, shares = self._execute(
                            pending, ts, float(open_.iloc[b]), cash, shares,
                            symbol, fold, trade_rows,
                        )
                        pending = None
                    # 2) mark to market at the close
                    price = float(close.iloc[b])
                    equity = cash + shares * price
                    if equity <= 0:
                        logger.error("equity wiped out at %s; stopping", ts)
                        equity_idx.append(ts)
                        equity_vals.append(equity)
                        raise _Bankrupt
                    if reset_peak:
                        peak = equity
                        reset_peak = False
                    peak = max(peak, equity)
                    eff_alloc = shares * price / equity
                    # 3) circuit breaker
                    if (cfg.max_dd_halt is not None and not halted
                            and equity < peak * (1 - cfg.max_dd_halt)):
                        halted = True
                        fires += 1
                        pending = (0.0, {"reason": "circuit_breaker",
                                         "strategy": "risk_halt"})
                        logger.warning(
                            "circuit breaker at %s: equity %.0f is %.1f%% off "
                            "peak %.0f — going flat for the fold",
                            ts, equity, 100 * (1 - equity / peak), peak,
                        )
                    # 4) decision from this bar's regime (fills next open)
                    row = series.iloc[j - tr0]
                    conf = float(probs[j - tr0][int(row["confirmed_state"])])
                    target_alloc = np.nan
                    if not halted and pending is None:
                        state = self._build_state(row, probs[j - tr0])
                        sigs = orch.generate_signals(
                            [symbol], {symbol: bars.iloc[:b + 1]}, state,
                            is_flickering=bool(row["is_flickering"]),
                        )
                        if sigs:
                            sig = sigs[0]
                            target_alloc = sig.position_size_pct * sig.leverage
                            if abs(target_alloc - eff_alloc) > cfg.rebalance_threshold:
                                pending = (target_alloc, {
                                    "reason": sig.reasoning,
                                    "strategy": sig.strategy_name,
                                    "regime_id": sig.regime_id,
                                    "regime_label": sig.regime_name,
                                    "confidence": conf,
                                })
                    equity_idx.append(ts)
                    equity_vals.append(equity)
                    regime_rows.append({
                        "timestamp": ts, "fold": fold,
                        "raw_state": int(row["raw_state"]),
                        "confirmed_state": int(row["confirmed_state"]),
                        "label": row["label"],
                        "probability": float(row["probability"]),
                        "confirmed_prob": conf,
                        "is_confirmed": bool(row["is_confirmed"]),
                        "is_flickering": bool(row["is_flickering"]),
                        "target_alloc": target_alloc,
                        "effective_alloc": eff_alloc,
                    })
                prev_fold_halted = halted
                fold += 1
        except _Bankrupt:
            pass
        finally:
            hmm_logger.setLevel(prior_levels[0])
            hmmlearn_logger.setLevel(prior_levels[1])

        if not equity_idx:
            raise RuntimeError("no out-of-sample bars were simulated")
        result = BacktestResult(
            symbol=symbol,
            config=cfg,
            equity_curve=pd.Series(equity_vals, index=pd.Index(equity_idx),
                                   name="equity"),
            trades=pd.DataFrame(trade_rows, columns=TRADE_COLUMNS),
            regime_history=pd.DataFrame(regime_rows).set_index("timestamp")
            if regime_rows else pd.DataFrame(),
            windows=windows,
            fold_metadata=fold_meta,
            circuit_breaker_fires=fires,
            bars=bars,
        )
        logger.info(
            "backtest %s: %d folds, %d oos bars, %d trades, final equity "
            "%.0f (%+.1f%%), breaker fired %dx",
            symbol, len(windows), len(result.equity_curve),
            len(result.trades), result.final_equity,
            100 * result.total_return, fires,
        )
        return result

    # ------------------------------------------------------------ internals

    def _fit_fold(self, train_feats: pd.DataFrame, fold: int,
                  prev_engine: HMMEngine | None,
                  prev_orch: StrategyOrchestrator | None
                  ) -> tuple[HMMEngine, StrategyOrchestrator]:
        """Fit a fresh engine on the fold's in-sample rows; on failure fall
        back to the previous fold's model rather than aborting the run."""
        try:
            engine = HMMEngine(**self._engine_params())
            engine.fit(train_feats)
            orch = StrategyOrchestrator(self.strategy_config,
                                        engine.get_regime_info())
            if self.shuffle_regimes_seed is not None:
                self._shuffle_mapping(orch, fold)
            return engine, orch
        except Exception:
            if prev_engine is None or prev_orch is None:
                raise
            logger.exception("fold %d training failed; reusing previous model",
                             fold)
            return prev_engine, prev_orch

    def _shuffle_mapping(self, orch: StrategyOrchestrator, fold: int) -> None:
        """Randomly permute regime->strategy for misclassification stress."""
        rng = np.random.default_rng(self.shuffle_regimes_seed + fold)
        ids = list(orch.regime_to_strategy)
        strategies = [orch.regime_to_strategy[r] for r in ids]
        rng.shuffle(strategies)
        orch.regime_to_strategy = dict(zip(ids, strategies))
        logger.info("fold %d: regime mapping deliberately shuffled", fold)

    @staticmethod
    def _build_state(row: pd.Series, prob_row: np.ndarray) -> RegimeState:
        state_id = int(row["confirmed_state"])
        return RegimeState(
            label=RegimeLabel(row["label"]),
            state_id=state_id,
            probability=float(prob_row[state_id]),
            state_probabilities={int(s): float(p)
                                 for s, p in enumerate(prob_row)},
            timestamp=None,
            is_confirmed=bool(row["is_confirmed"]),
            consecutive_bars=int(row["consecutive_bars"]),
        )

    def _execute(self, pending: tuple[float, dict[str, Any]],
                 ts: pd.Timestamp, open_price: float, cash: float,
                 shares: int, symbol: str, fold: int,
                 trade_rows: list[dict[str, Any]]) -> tuple[float, int]:
        """Apply a pending target allocation at this bar's open."""
        cfg = self.config
        target, info = pending
        equity_at_open = cash + shares * open_price
        if equity_at_open <= 0:
            return cash, shares
        prev_alloc = shares * open_price / equity_at_open
        raw_delta = int(equity_at_open * target / open_price) - shares
        if raw_delta == 0:
            return cash, shares
        px = open_price * (1 + cfg.slippage_pct) if raw_delta > 0 \
            else open_price * (1 - cfg.slippage_pct)
        target_shares = int(equity_at_open * target / px)
        delta = target_shares - shares
        if delta == 0:
            return cash, shares
        cash -= delta * px + cfg.commission
        trade_rows.append({
            "timestamp": ts, "symbol": symbol,
            "side": "buy" if delta > 0 else "sell",
            "delta_shares": delta, "price": px, "prev_shares": shares,
            "new_shares": target_shares, "prev_allocation": prev_alloc,
            "new_allocation": target, "equity_at_open": equity_at_open,
            "regime_id": info.get("regime_id", -1),
            "regime_label": info.get("regime_label", ""),
            "confidence": info.get("confidence", np.nan),
            "strategy": info.get("strategy", ""),
            "reason": info.get("reason", ""), "fold": fold,
        })
        return cash, target_shares


class _Bankrupt(Exception):
    """Internal: equity hit zero; stop the simulation cleanly."""
