"""Live trading orchestration: startup, main loop, shutdown, recovery.

Pipeline per cycle: market data -> features -> filtered HMM -> strategy
orchestrator -> risk veto -> execution, plus trailing stops, breakers,
retraining, alerts, and the state snapshot (crash recovery + dashboard).

Error posture: API calls retry in AlpacaClient; HMM failure holds the prior
regime; a stale feed pauses signals (stops stay live); unhandled cycle
errors log + snapshot + continue; shutdown never closes positions.
"""

from __future__ import annotations

import logging
import signal as os_signal
import time
import traceback
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from core.broker.alpaca_client import AlpacaClient
from core.broker.order_executor import OrderExecutor
from core.broker.position_tracker import PositionTracker
from core.data.feature_engineering import FeatureEngineer
from core.data.market_data import MarketData
from core.hmm_engine import HMMEngine, RegimeState
from core.live_snapshot import (
    build_snapshot, model_age_days, restore_snapshot, save_snapshot)
from core.regime_strategies import StrategyOrchestrator
from core.risk_manager import RiskManager, TradingStatus
from monitoring.alerts import AlertKind, AlertLevel, AlertManager
from monitoring.logger import set_context

logger = logging.getLogger("regime_trader.live")

MODEL_MAX_AGE_DAYS = 7          # retrain when the saved model is older
FEED_STALE_SECONDS = 300.0      # pause signals when no stream event for this
HISTORY_LOOKBACK_DAYS = 2000    # calendar days of daily bars to fetch


class TradingSystem:
    """The live (paper by default) trading loop; every component is
    constructed from settings but injectable for testing."""

    def __init__(
        self,
        settings: dict[str, Any],
        dry_run: bool = False,
        snapshot_path: str | Path = "state_snapshot.json",
        model_path: str | Path = "models/hmm_model.pkl",
        client: Any = None,
        market_data: Any = None,
        risk_manager: RiskManager | None = None,
        executor: OrderExecutor | None = None,
        tracker: PositionTracker | None = None,
        engine: HMMEngine | None = None,
        orchestrator: StrategyOrchestrator | None = None,
        dashboard: Any = None,
        alerts: AlertManager | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.dry_run = dry_run
        self.snapshot_path = Path(snapshot_path)
        self.model_path = Path(model_path)
        self.client = client
        self.market_data = market_data
        self.risk_manager = risk_manager
        self.executor = executor
        self.tracker = tracker
        self.engine = engine
        self.orchestrator = orchestrator
        self.dashboard = dashboard
        self.alerts = alerts
        self._sleep = sleep
        self._api_ok = True

        broker = settings["broker"]
        self.symbols: list[str] = list(broker["symbols"])
        self.regime_symbol: str = self.symbols[0]  # market proxy for the HMM
        self.timeframe: str = broker.get("timeframe", "1Day")
        self.cycle_seconds: float = float(broker.get("cycle_seconds", 300))

        self.feature_engineer = FeatureEngineer()
        self.running = False
        self.regime_state: RegimeState | None = None
        self.last_feed_event: float | None = None
        self.session_start_equity: float | None = None
        self._prev_breaker: TradingStatus | None = None
        self._last_cycle_date = None
        self._last_signals: list[dict[str, Any]] = []

    # ------------------------------------------------------------- startup

    def startup(self, wait_for_open: bool = True) -> None:
        """Bring the system online (steps 1-8 of the startup sequence)."""
        self._init_clients()
        if self.alerts is None:
            mon = self.settings.get("monitoring", {})
            self.alerts = AlertManager(
                rate_limit_minutes=mon.get("alert_rate_limit_minutes", 15),
                email_config=mon.get("email"),
                webhook_url=mon.get("webhook_url"))
        account = self.client.get_account()
        logger.info("account: equity=%s cash=%s buying_power=%s",
                    account.get("equity"), account.get("cash"),
                    account.get("buying_power"))
        self._wait_for_market(wait_for_open)
        self._load_or_train_model()
        s = self.settings
        if self.risk_manager is None:
            self.risk_manager = RiskManager(s["risk"])
        if self.orchestrator is None:
            self.orchestrator = StrategyOrchestrator(
                {**s["strategy"], "min_confidence": s["hmm"]["min_confidence"]},
                self.engine.get_regime_info())
        if self.executor is None:
            self.executor = OrderExecutor(self.client)
        if self.tracker is None:
            self.tracker = PositionTracker(self.client, self.risk_manager)
        self.tracker.sync()
        self._restore_snapshot()
        self._start_streams()
        self.session_start_equity = float(account.get("equity") or 0.0)
        self._prev_breaker = self.risk_manager.breaker.status
        logger.info(
            "System online — %s mode, %d symbols, regime proxy %s, "
            "%d positions, breaker=%s",
            "DRY-RUN" if self.dry_run else "LIVE-PAPER" if getattr(
                self.client, "paper", True) else "LIVE-REAL",
            len(self.symbols), self.regime_symbol,
            len(self.tracker.positions), self._prev_breaker.value,
        )

    def _init_clients(self) -> None:
        if self.client is None:
            self.client = AlpacaClient.from_env(
                paper=self.settings["broker"].get("paper_trading", True))
            self.client.connect()
        if self.market_data is None:
            self.market_data = MarketData(self.client, self.timeframe)

    def _wait_for_market(self, wait: bool) -> None:
        clock = self.client.get_clock()
        if clock["is_open"]:
            return
        if not wait:
            raise SystemExit(f"market closed (next open {clock['next_open']}) "
                             "— rerun without --no-wait to wait")
        while not self.client.get_clock()["is_open"]:
            logger.info("market closed; next open %s — waiting",
                        clock.get("next_open"))
            self._sleep(300)

    def _load_or_train_model(self) -> None:
        if self.engine is not None:
            return
        if self.model_path.exists():
            engine = HMMEngine.load(self.model_path)
            age = model_age_days(engine)
            if age is not None and age <= MODEL_MAX_AGE_DAYS:
                logger.info("loaded HMM (%.1f days old, n_regimes=%s)",
                            age, engine.metadata.get("n_regimes"))
                self.engine = engine
                return
            logger.info("saved HMM is %s days old (> %d) — retraining",
                        f"{age:.1f}" if age is not None else "?",
                        MODEL_MAX_AGE_DAYS)
        self.train_model()

    def train_model(self) -> None:
        """(Re)train the HMM on the regime proxy's daily history and save."""
        bars = self._fetch_bars_for(self.regime_symbol)
        features = self.feature_engineer.compute_features(bars)
        h = self.settings["hmm"]
        engine = HMMEngine(
            n_candidates=h["n_candidates"], n_init=h["n_init"],
            covariance_type=h.get("covariance_type", "full"),
            min_train_bars=h["min_train_bars"],
            stability_bars=h["stability_bars"],
            flicker_window=h["flicker_window"],
            flicker_threshold=h["flicker_threshold"],
            min_confidence=h["min_confidence"],
            retrain_interval=h.get("retrain_interval_bars", 63),
        )
        engine.fit(features)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        engine.save(self.model_path)
        self.engine = engine
        if self.orchestrator is not None:
            self.orchestrator.update_regime_infos(engine.get_regime_info())
        if self.alerts is not None:
            self.alerts.send(AlertKind.HMM_RETRAINED, AlertLevel.INFO,
                             f"HMM retrained: {engine.metadata['n_regimes']} "
                             f"regimes, BIC {engine.metadata['bic']:.0f}")

    def _fetch_bars_for(self, symbol: str) -> pd.DataFrame:
        start = datetime.now(timezone.utc) - timedelta(days=HISTORY_LOOKBACK_DAYS)
        return self.market_data.get_historical_bars(symbol, start=start)

    def _fetch_all_bars(self) -> dict[str, pd.DataFrame]:
        start = datetime.now(timezone.utc) - timedelta(days=HISTORY_LOOKBACK_DAYS)
        return self.market_data.get_historical_bars(self.symbols, start=start)

    def _start_streams(self) -> None:
        try:
            self.market_data.subscribe_bars(self.symbols, self._on_bar)
            self.market_data.start_stream()
            self.tracker.start_stream()
        except Exception:
            logger.warning("websocket streams unavailable — continuing in "
                           "polling mode", exc_info=True)

    def _on_bar(self, bar: dict[str, Any]) -> None:
        self.last_feed_event = time.time()
        self.tracker.update_price(bar["symbol"], bar["close"])

    def feed_ok(self) -> bool:
        """False when the stream has gone silent past the staleness limit."""
        if self.last_feed_event is None:
            return True  # polling mode / no events yet
        return time.time() - self.last_feed_event < FEED_STALE_SECONDS

    # ----------------------------------------------------------- main loop

    def run(self, wait_for_open: bool = True) -> None:
        """Startup, loop until stopped, then shutdown."""
        self._install_signal_handlers()
        self.startup(wait_for_open)
        self.running = True
        try:
            while self.running:
                try:
                    market_open = self.client.is_market_open()
                    self._api_ok = True
                except Exception:
                    logger.exception("clock check failed")
                    market_open = False
                    if self._api_ok and self.alerts is not None:
                        self.alerts.send(AlertKind.API_LOST,
                                         AlertLevel.CRITICAL,
                                         "Alpaca API unreachable — trading "
                                         "paused until it recovers")
                    self._api_ok = False
                if market_open:
                    self.cycle()
                if self.running:
                    self._sleep(self.cycle_seconds)
        finally:
            self.shutdown()

    def cycle(self) -> None:
        """One evaluation cycle; unhandled errors never kill the loop."""
        try:
            self._cycle_inner()
        except Exception:
            logger.critical("unhandled cycle error — state saved, loop "
                            "continues:\n%s", traceback.format_exc())
            self._save_snapshot(error=traceback.format_exc(limit=1))

    def _cycle_inner(self) -> None:
        self._roll_session_boundaries()
        bars_map = self._fetch_all_bars()
        features = self.feature_engineer.compute_features(
            bars_map[self.regime_symbol])
        self._maybe_retrain(features)

        flickering = True  # assume uncertain unless prediction succeeds
        try:
            self.regime_state = self.engine.predict(features)
            flickering = self.engine.is_flickering()
        except Exception:
            logger.exception("HMM prediction failed — holding previous "
                             "regime in uncertainty mode")
            if self.regime_state is None:
                return  # never had a regime; nothing safe to do
        self.tracker.set_regime(self.regime_state.label.value)
        self._send_regime_alerts(flickering)

        self._last_signals = []
        if self.feed_ok():
            self._evaluate_and_trade(bars_map, flickering)
        else:
            logger.warning("data feed stale — pausing new signals "
                           "(stops remain active at the broker)")
            if self.alerts is not None:
                self.alerts.send(AlertKind.DATA_FEED_DOWN, AlertLevel.WARNING,
                                 "market data feed stale — new signals "
                                 "paused, stops remain active")
        self._update_trailing_stops(bars_map)
        self._check_breakers()
        snap = self._snapshot_dict()
        set_context(regime=snap["regime"], probability=snap["regime_confidence"],
                    equity=snap["equity"], positions=len(self.tracker.positions),
                    daily_pnl=snap["daily_pnl"])
        self._maybe_pnl_alert(snap)
        self._save_snapshot(snap=snap)
        self._render_dashboard(snap)
        self._last_cycle_date = datetime.now(timezone.utc).date()

    def _send_regime_alerts(self, flickering: bool) -> None:
        if self.alerts is None:
            return
        try:
            changed = self.engine.detect_regime_change()
        except Exception:
            changed = False
        if changed:
            self.alerts.send(
                AlertKind.REGIME_CHANGE, AlertLevel.INFO,
                f"regime changed to {self.regime_state.label.value} "
                f"(p={self.regime_state.probability:.2f})")
        if flickering:
            self.alerts.send(
                AlertKind.FLICKER_EXCEEDED, AlertLevel.WARNING,
                "regime flicker threshold exceeded — uncertainty mode, "
                "sizes halved")

    def _maybe_pnl_alert(self, snap: dict[str, Any]) -> None:
        pct = snap.get("daily_pnl_pct")
        threshold = self.settings.get("monitoring", {}).get(
            "large_pnl_alert_pct", 0.02)
        if self.alerts is not None and pct is not None and abs(pct) >= threshold:
            self.alerts.send(
                AlertKind.LARGE_PNL,
                AlertLevel.WARNING if pct < 0 else AlertLevel.INFO,
                f"large daily P&L move: {pct:+.2%} "
                f"({snap.get('daily_pnl', 0):+,.0f})")

    def _evaluate_and_trade(self, bars_map: dict[str, pd.DataFrame],
                            flickering: bool) -> None:
        flicker_rate = self.engine.get_regime_flicker_rate()
        state = self.tracker.portfolio_state(flicker_rate=flicker_rate)
        weights = {s: p.market_value / state.equity
                   for s, p in self.tracker.positions.items()
                   if state.equity > 0}
        signals = self.orchestrator.generate_signals(
            self.symbols, bars_map, self.regime_state,
            is_flickering=flickering, current_allocations=weights)
        price_history = pd.DataFrame(
            {sym: b["close"] for sym, b in bars_map.items() if len(b)})
        regime_info = self.engine.get_regime_info(self.regime_state.state_id)

        for sig in signals:
            try:
                quote = self.market_data.get_latest_quote(sig.symbol)
            except Exception:
                quote = None
            decision = self.risk_manager.validate_signal(
                sig, state, regime_info=regime_info,
                price_history=price_history, quote=quote)
            entry = {"time": datetime.now(timezone.utc).strftime("%H:%M"),
                     "symbol": sig.symbol, "strategy": sig.strategy_name,
                     "approved": decision.approved,
                     "qty": decision.approved_qty,
                     "reason": decision.rejection_reason,
                     "modifications": decision.modifications}
            self._last_signals.append(entry)
            if not decision.approved:
                continue  # rejection already logged by the risk manager
            if self.dry_run:
                logger.info("DRY RUN — would submit %s x%d (%s)",
                            sig.symbol, decision.approved_qty,
                            "; ".join(decision.modifications) or "unmodified")
                continue
            self.executor.submit_order(decision.modified_signal,
                                       decision.approved_qty,
                                       risk_decision=decision)
            state = self.tracker.portfolio_state(flicker_rate=flicker_rate)

    def _update_trailing_stops(self, bars_map: dict[str, pd.DataFrame]) -> None:
        """Refresh stops from the current regime's formula (tighten only)."""
        if self.regime_state is None or self.dry_run:
            return
        strategy = self.orchestrator.strategy_for_regime(
            self.regime_state.state_id)
        for symbol, pos in list(self.tracker.positions.items()):
            bars = bars_map.get(symbol)
            if bars is None or not len(bars):
                continue
            sig = strategy.generate_signal(symbol, bars, self.regime_state)
            if sig is None or sig.stop_loss is None:
                continue
            if self.executor.modify_stop(symbol, sig.stop_loss) is not None:
                self.tracker.set_stop(symbol, sig.stop_loss)

    def _check_breakers(self) -> None:
        self.tracker.refresh_equity()  # feeds the breaker with real equity
        status = self.risk_manager.breaker.check()
        if status is not self._prev_breaker:
            logger.warning("circuit breaker status %s -> %s",
                           self._prev_breaker.value if self._prev_breaker
                           else "?", status.value)
            newly_halted = (status in (TradingStatus.HALTED,
                                       TradingStatus.STOPPED)
                            and self._prev_breaker not in
                            (TradingStatus.HALTED, TradingStatus.STOPPED))
            if self.alerts is not None:
                self.alerts.send(
                    AlertKind.CIRCUIT_BREAKER,
                    AlertLevel.CRITICAL if newly_halted else AlertLevel.WARNING,
                    f"circuit breaker now {status.value} "
                    f"(was {self._prev_breaker.value if self._prev_breaker else '?'})")
            if newly_halted:
                if self.dry_run:
                    logger.warning("DRY RUN — would close ALL positions")
                else:
                    self.executor.close_all_positions()
        self._prev_breaker = status

    def _maybe_retrain(self, features: pd.DataFrame) -> None:
        age = model_age_days(self.engine)
        stale = age is not None and age >= MODEL_MAX_AGE_DAYS
        grown = self.engine.needs_retrain(len(features))
        if not (stale or grown):
            return
        logger.info("retraining HMM (age=%s days, feature rows=%d)",
                    f"{age:.1f}" if age is not None else "?", len(features))
        try:
            self.train_model()
        except Exception:
            logger.exception("retrain failed — keeping the current model")

    def _roll_session_boundaries(self) -> None:
        today = datetime.now(timezone.utc).date()
        if self._last_cycle_date is None or today == self._last_cycle_date:
            return
        if today.isocalendar()[:2] != self._last_cycle_date.isocalendar()[:2]:
            logger.info("new week — rolling weekly risk anchors")
            self.tracker.mark_new_week()
        else:
            logger.info("new day — rolling daily risk anchors")
            self.tracker.mark_new_day()

    # ------------------------------------------------- snapshot / shutdown

    def _snapshot_dict(self, error: str | None = None) -> dict[str, Any]:
        return build_snapshot(self, error)

    def _save_snapshot(self, error: str | None = None,
                       snap: dict[str, Any] | None = None) -> None:
        save_snapshot(self.snapshot_path,
                      snap if snap is not None else self._snapshot_dict(error))

    def _restore_snapshot(self) -> None:
        restore_snapshot(self)

    def _render_dashboard(self, snap: dict[str, Any] | None = None) -> None:
        if self.dashboard is None:
            return
        try:
            self.dashboard.update(snap if snap is not None
                                  else self._snapshot_dict())
        except Exception:
            logger.exception("dashboard render failed")

    def _install_signal_handlers(self) -> None:
        def _handler(signum: int, _frame: Any) -> None:
            logger.warning("received signal %d — shutting down after this "
                           "cycle (positions stay open, stops in place)",
                           signum)
            self.running = False

        for sig in (os_signal.SIGINT, os_signal.SIGTERM):
            try:
                os_signal.signal(sig, _handler)
            except ValueError:
                pass  # not the main thread (tests)

    def shutdown(self) -> None:
        """Close streams, save state, print the session summary.
        Positions are intentionally left open — their stops are live."""
        self.running = False
        for stop in (getattr(self.market_data, "stop_stream", None),
                     getattr(self.tracker, "stop_stream", None)):
            if stop:
                try:
                    stop()
                except Exception:
                    logger.exception("stream shutdown failed")
        self._save_snapshot()
        equity = self._snapshot_dict().get("equity")
        if equity is not None and self.session_start_equity:
            pnl = equity - self.session_start_equity
            logger.info("session summary: equity %.0f (%+.0f, %+.2f%%), "
                        "%d trades today, %d breaker events, %d open "
                        "positions left with stops in place",
                        equity, pnl, 100 * pnl / self.session_start_equity,
                        self.tracker.trades_today if self.tracker else 0,
                        len(self.risk_manager.breaker.get_history())
                        if self.risk_manager else 0,
                        len(self.tracker.positions) if self.tracker else 0)
        logger.info("system offline")
