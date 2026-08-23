"""Download dividend/split-adjusted daily OHLCV for the shortlist universe via yfinance.

Saves one CSV per ticker to research/data/ (auto_adjust=True so Open/High/Low/
Close are all adjusted for dividends and splits), plus a manifest CSV recording
the date range and row count actually received.

HARD RULE: downloads are capped at end=2023-01-01. The TEST period (2023-01-01
onward) is locked in research/data/test_locked/ and must not be downloaded,
read, or touched by anything until the user says UNLOCK. Paid/manual data files
dropped in by hand must be split with scripts/split_train_test.py before use.

Re-running overwrites with a fresh train-period pull; the locked directory is
never touched by this script.
"""

from pathlib import Path

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "research" / "data"

TEST_START = "2023-01-01"  # never fetch at or past this date until UNLOCK

# Every ticker the shortlist (research/IDEA_LOG.md) needs from free data.
# S&P 500 constituent-level data (IDEA-004/013/027/033) awaits paid files.
TICKERS = {
    # Broad index / asset-class ETFs
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000 small-cap",
    "EFA": "Developed intl equity (dual momentum)",
    "VEU": "All-world ex-US equity (Ivy 5)",
    "AGG": "US aggregate bonds (dual momentum / cash proxy)",
    "IEF": "7-10yr Treasuries (dual momentum / risk parity)",
    "SHY": "1-3yr Treasuries (cash proxy / absolute momentum hurdle)",
    "BIL": "1-3mo T-bills (cash proxy)",
    "VNQ": "US REITs (200-day filter universe)",
    # Gold / metals
    "GLD": "Gold ETF",
    "SLV": "Silver ETF (GLD/SLV pair)",
    # Sector SPDRs (cross-sectional momentum, pairs, 1/N basket)
    "XLB": "Materials",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLP": "Consumer staples",
    "XLU": "Utilities",
    "XLV": "Health care",
    "XLY": "Consumer discretionary",
    # Liquid single names for illustration per the shortlist
    "AAPL": "Large-cap single name",
    "MSFT": "Large-cap single name",
    # Non-tradeable series (signals/rates only, never position weights)
    "^IRX": "13-week T-bill yield",
    "^VIX": "CBOE volatility index (VIX-based signals)",
}


def fetch_all() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for ticker, role in TICKERS.items():
        df = yf.download(
            ticker,
            start="1900-01-01",
            end=TEST_START,    # hard cap: TEST period is locked until UNLOCK
            interval="1d",
            auto_adjust=True,  # dividend + split adjusted OHLC
            actions=True,      # keep raw Dividends/Stock Splits columns for audit
            progress=False,
            multi_level_index=False,
        )
        if df is None or df.empty:
            print(f"{ticker}: NO DATA RETURNED")
            manifest.append({"ticker": ticker, "role": role, "rows": 0,
                             "start": None, "end": None})
            continue
        df = df[df.index < TEST_START]  # belt-and-suspenders
        df.index.name = "Date"
        out = DATA_DIR / f"{ticker.lstrip('^')}.csv"
        df.to_csv(out)
        manifest.append({
            "ticker": ticker,
            "role": role,
            "rows": len(df),
            "start": df.index.min().date().isoformat(),
            "end": df.index.max().date().isoformat(),
        })
        print(f"{ticker}: {len(df)} rows  {df.index.min().date()} -> {df.index.max().date()}")

    pd.DataFrame(manifest).to_csv(DATA_DIR / "_manifest.csv", index=False)
    print(f"\nSaved to {DATA_DIR}")


if __name__ == "__main__":
    fetch_all()
