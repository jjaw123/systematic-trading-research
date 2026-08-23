"""Daily kill-switch runner. Schedule this after every close.

    python research/live/daily_check.py [--live-file PATH] [--market SPY]

Reads the live return stream, runs both checks, appends to HALT_LOG.jsonl,
updates HALT_STATE.json, alerts on WARN/HALT. Exit codes: 0 OK, 1 WARN,
2 HALT, 3 ERROR (rules unreadable - treated as a halt).
"""

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import load  # noqa: E402
from live.halt import LOG_PATH, load_rules, run_daily_check  # noqa: E402

LIVE_FILE = Path(__file__).resolve().parent / "live_returns.csv"


def alert(res, cfg):
    line = f"[{res.status}] kill-switch {res.date}: " + \
           ("; ".join(res.reasons) if res.reasons else "all checks passed")
    if cfg.get("alerting", {}).get("stdout", True):
        print(line)
    if res.status in ("WARN", "HALT", "ERROR") and \
            cfg.get("alerting", {}).get("desktop_notification"):
        try:
            subprocess.run(
                ["osascript", "-e",
                 f'display notification {line[:200]!r} with title "TRADING KILL SWITCH"'],
                check=False, capture_output=True, timeout=10)
        except Exception:  # noqa: BLE001 - alerting must never block the halt
            pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--live-file", default=str(LIVE_FILE))
    p.add_argument("--market", default="SPY",
                   help="ticker whose returns form the random-entry null")
    args = p.parse_args()

    path = Path(args.live_file)
    if not path.exists():
        print(f"No live return file at {path}. Nothing to check yet.\n"
              f"Expected columns: Date,net_return,gross_exposure")
        return 0

    live = pd.read_csv(path, index_col=0, parse_dates=True).sort_index()
    missing = {"net_return", "gross_exposure"} - set(live.columns)
    if missing:
        print(f"live file missing columns: {missing}")
        return 3

    mkt_df = load(args.market)
    market = mkt_df["Close"].pct_change()

    res = run_daily_check(live, market)
    try:
        cfg, _ = load_rules()
    except Exception:  # noqa: BLE001
        cfg = {}
    alert(res, cfg)
    print(f"logged -> {LOG_PATH}")
    return {"OK": 0, "WARN": 1, "HALT": 2, "ERROR": 3}[res.status]


if __name__ == "__main__":
    sys.exit(main())
