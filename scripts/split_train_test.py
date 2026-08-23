"""One-time sequestration of TEST-period rows (>= 2023-01-01) out of research/data/.

Rows before 2023-01-01 stay in research/data/<ticker>.csv (TRAIN + warmup).
Rows from 2023-01-01 onward move to research/data/test_locked/<ticker>.csv,
which is then chmod 000. Nothing from the test period is printed or summarized.

The locked directory must not be read by any engine code until the user says
UNLOCK. The loader in research/engine/data.py independently enforces this.
"""

import os
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "research" / "data"
LOCKED_DIR = DATA_DIR / "test_locked"
TEST_START = "2023-01-01"


def main() -> None:
    LOCKED_DIR.mkdir(exist_ok=True)
    os.chmod(LOCKED_DIR, 0o700)
    for csv in sorted(DATA_DIR.glob("*.csv")):
        if csv.name.startswith("_"):
            continue
        df = pd.read_csv(csv, index_col="Date", parse_dates=True)
        train = df[df.index < TEST_START]
        test = df[df.index >= TEST_START]
        if not test.empty:
            locked_path = LOCKED_DIR / csv.name
            if locked_path.exists():
                os.chmod(locked_path, 0o600)
            test.to_csv(locked_path)
            os.chmod(locked_path, 0o000)
        train.to_csv(csv)
        print(f"{csv.stem}: train {train.index.min().date()} -> {train.index.max().date()}"
              f" ({len(train)} rows); test rows sequestered, not displayed")
    os.chmod(LOCKED_DIR, 0o000)
    print(f"\nLocked: {LOCKED_DIR} (chmod 000 — do not open until UNLOCK)")


if __name__ == "__main__":
    main()
