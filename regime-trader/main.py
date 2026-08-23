"""regime-trader entry point.

Default (no mode flag) runs the live trading loop (paper by default).

Usage:
    python main.py                       # live loop (paper trading)
    python main.py --dry-run             # full pipeline, no orders
    python main.py --train-only          # train the HMM and exit
    python main.py --dashboard           # attach to a running instance
    python main.py --backtest --symbols SPY --start 2019-01-01 --compare
    python main.py --backtest --stress-test
    python main.py --backtest --symbols DEMO --synthetic

Backtest bars come from data/<SYMBOL>.csv or --synthetic; the live loop
fetches data from Alpaca (credentials in .env).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from dotenv import load_dotenv

CONFIG_PATH = Path(__file__).parent / "config" / "settings.yaml"
DATA_DIR = Path(__file__).parent / "data"

logger = logging.getLogger("regime_trader.main")


def load_settings(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load and validate settings.yaml."""
    if not path.exists():
        raise FileNotFoundError(f"settings file not found: {path}")
    with open(path) as f:
        settings = yaml.safe_load(f)
    missing = [s for s in ("broker", "hmm", "strategy", "risk", "backtest",
                           "monitoring") if s not in settings]
    if missing:
        raise ValueError(f"settings.yaml missing sections: {missing}")
    return settings


def _synthetic_bars(n: int = 2200, seed: int = 7) -> pd.DataFrame:
    """Demo OHLCV series with alternating calm/turbulent volatility blocks."""
    rng = np.random.default_rng(seed)
    vol = np.where((np.arange(n) // 200) % 2 == 0, 0.008, 0.025)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0003, vol)))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    spread = rng.uniform(0.0, 0.01, n)
    return pd.DataFrame(
        {"open": open_, "high": np.maximum(open_, close) * (1 + spread),
         "low": np.minimum(open_, close) * (1 - spread), "close": close,
         "volume": rng.lognormal(15, 0.4, n) * (1 + 4 * (vol > 0.01))},
        index=pd.bdate_range("2016-01-04", periods=n),
    )


def load_bars(symbol: str, start: str | None, end: str | None,
              synthetic: bool) -> pd.DataFrame:
    """Load OHLCV bars from data/<SYMBOL>.csv, or synthesize with --synthetic."""
    if synthetic:
        logger.warning("using SYNTHETIC bars for %s — results are a pipeline "
                       "demo, not market performance", symbol)
        bars = _synthetic_bars()
    else:
        csv = DATA_DIR / f"{symbol}.csv"
        if not csv.exists():
            raise FileNotFoundError(
                f"{csv} not found. Provide daily OHLCV as CSV (columns: "
                "date,open,high,low,close,volume), or run with --synthetic "
                "for a demo. Live data fetching arrives with the broker layer."
            )
        bars = pd.read_csv(csv, parse_dates=[0], index_col=0)
        bars.columns = [c.lower() for c in bars.columns]
    if start:
        bars = bars.loc[bars.index >= pd.Timestamp(start)]
    if end:
        bars = bars.loc[bars.index <= pd.Timestamp(end)]
    return bars.sort_index()


def _backtest_config(settings: dict[str, Any]) -> "BacktestConfig":
    from backtest.backtester import BacktestConfig

    bt, strat, risk = settings["backtest"], settings["strategy"], settings["risk"]
    return BacktestConfig(
        initial_capital=bt["initial_capital"],
        slippage_pct=bt["slippage_pct"],
        train_window=bt["train_window"],
        test_window=bt["test_window"],
        step_size=bt["step_size"],
        risk_free_rate=bt["risk_free_rate"],
        rebalance_threshold=strat["rebalance_threshold"],
        max_dd_halt=risk["max_dd_from_peak"],
    )


def _hmm_params(settings: dict[str, Any], light: bool = False) -> dict[str, Any]:
    h = settings["hmm"]
    params = {
        "n_candidates": h["n_candidates"], "n_init": h["n_init"],
        "covariance_type": h["covariance_type"],
        "stability_bars": h["stability_bars"],
        "flicker_window": h["flicker_window"],
        "flicker_threshold": h["flicker_threshold"],
        "min_confidence": h["min_confidence"],
    }
    if light:  # Monte Carlo stress runs a full walk-forward per simulation
        params.update({"n_candidates": [3], "n_init": 2})
    return params


def _strategy_config(settings: dict[str, Any]) -> dict[str, Any]:
    return {**settings["strategy"],
            "min_confidence": settings["hmm"]["min_confidence"]}


def run_backtest(settings: dict[str, Any], args: argparse.Namespace) -> None:
    """Run the walk-forward backtest for each requested symbol."""
    from backtest.backtester import WalkForwardBacktester
    from backtest.performance import PerformanceAnalyzer

    symbols = args.symbols or settings["broker"]["symbols"][:1]
    analyzer = PerformanceAnalyzer(
        risk_free_rate=settings["backtest"]["risk_free_rate"])
    for symbol in symbols:
        bars = load_bars(symbol, args.start, args.end, args.synthetic)
        backtester = WalkForwardBacktester(
            config=_backtest_config(settings),
            hmm_params=_hmm_params(settings),
            strategy_config=_strategy_config(settings),
        )
        result = backtester.run(bars, symbol)
        report = analyzer.analyze(result)
        bench = analyzer.compare_benchmarks(result) if args.compare else None
        analyzer.print_report(result, report, benchmark_df=bench)
        out_dir = Path(args.output) / symbol
        paths = analyzer.export_csvs(result, out_dir, benchmark_df=bench)
        logger.info("wrote %s", ", ".join(str(p) for p in paths))


def run_stress(settings: dict[str, Any], args: argparse.Namespace) -> None:
    """Run the stress-test suite (crash / gap / misclassification)."""
    from backtest.backtester import WalkForwardBacktester
    from backtest.stress_test import StressConfig, StressTester, print_stress_results

    symbol = (args.symbols or settings["broker"]["symbols"][:1])[0]
    bars = load_bars(symbol, args.start, args.end, args.synthetic)
    backtester = WalkForwardBacktester(
        config=_backtest_config(settings),
        hmm_params=_hmm_params(settings, light=True),
        strategy_config=_strategy_config(settings),
    )
    tester = StressTester(backtester, StressConfig(n_sims=args.sims))
    logger.warning("stress suite runs %d full walk-forward simulations per "
                   "test — this can take a while (tune with --sims)", args.sims)
    results = tester.run_suite(bars, symbol)
    print_stress_results(results)


SNAPSHOT_PATH = Path("state_snapshot.json")


def run_live(settings: dict[str, Any], args: argparse.Namespace) -> None:
    """Run the live trading loop (paper by default)."""
    from core.live_engine import TradingSystem
    from monitoring.dashboard import Dashboard

    system = TradingSystem(
        settings,
        dry_run=args.dry_run,
        snapshot_path=SNAPSHOT_PATH,
        dashboard=Dashboard(
            settings["monitoring"]["dashboard_refresh_seconds"]),
    )
    system.run(wait_for_open=not args.no_wait)


def run_train_only(settings: dict[str, Any]) -> None:
    """Train the HMM from live data, save it, and exit."""
    from core.live_engine import TradingSystem

    system = TradingSystem(settings)
    system._init_clients()
    system.train_model()
    diag = system.engine.get_diagnostics()
    logger.info("model trained and saved to %s: n_regimes=%s bic=%.1f "
                "labels=%s", system.model_path, diag["n_regimes"],
                diag["bic"], diag["labels"])


def run_dashboard(settings: dict[str, Any]) -> None:
    """Attach a dashboard to a running instance via its state snapshot."""
    from monitoring.dashboard import Dashboard

    Dashboard.watch(SNAPSHOT_PATH,
                    settings["monitoring"]["dashboard_refresh_seconds"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HMM regime-based trading bot")
    mode = parser.add_argument_group("modes (default: live trading loop)")
    mode.add_argument("--backtest", action="store_true",
                      help="Run the walk-forward backtester")
    mode.add_argument("--stress-test", action="store_true",
                      help="Run the stress-test suite")
    mode.add_argument("--train-only", action="store_true",
                      help="Train the HMM and exit")
    mode.add_argument("--dashboard", action="store_true",
                      help="Show the dashboard for a running instance")
    parser.add_argument("--dry-run", action="store_true",
                        help="Live loop: full pipeline, no orders")
    parser.add_argument("--no-wait", action="store_true",
                        help="Live loop: exit instead of waiting when the "
                             "market is closed")
    parser.add_argument("--compare", action="store_true",
                        help="Backtest: add benchmark comparisons")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="Backtest symbols (default: first from settings)")
    parser.add_argument("--start", default=None, help="History start (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="History end (YYYY-MM-DD)")
    parser.add_argument("--sims", type=int, default=100,
                        help="Monte Carlo simulations per stress test")
    parser.add_argument("--synthetic", action="store_true",
                        help="Backtest: generated demo bars instead of CSVs")
    parser.add_argument("--output", default="backtest_results",
                        help="Backtest: directory for CSV outputs")
    return parser.parse_args()


def main() -> None:
    from monitoring.logger import setup_logging

    setup_logging(level=logging.INFO)
    load_dotenv()
    args = parse_args()
    settings = load_settings()

    if args.stress_test:
        run_stress(settings, args)
    elif args.backtest:
        run_backtest(settings, args)
    elif args.train_only:
        run_train_only(settings)
    elif args.dashboard:
        run_dashboard(settings)
    else:
        run_live(settings, args)


if __name__ == "__main__":
    main()
