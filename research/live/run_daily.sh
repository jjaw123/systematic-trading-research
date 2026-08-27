#!/bin/bash
# Paper-trading cron wrapper. Two modes, two cron entries:
#
#   run_daily.sh            after the close  - daily_loop.py (+ Friday report)
#   run_daily.sh reconcile  after the open   - reconcile_open.py, which
#                           replaces OPG orders the opening auction expired
#                           unfilled with DAY market orders.
#
# All output is appended to live/cron.log; exit codes are recorded.

set -uo pipefail

# Resolve the project root from this script's own location, so the file is
# portable and contains no absolute home path.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$HERE/../.." && pwd)"
PY="${TRADING_PY:-$PROJECT/regime-trader/.venv/bin/python}"
RESEARCH="$PROJECT/research"
LOG="$RESEARCH/live/cron.log"

MODE="${1:-daily}"

cd "$RESEARCH" || exit 1

if [ "$MODE" = "reconcile" ]; then
  {
    echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') post-open reconcile ==="
    "$PY" live/reconcile_open.py
    rc=$?
    echo "--- reconcile_open exit=$rc"
    case $rc in
      3) echo "!!! ERROR - broker/data failure, no replacements submitted" ;;
      4) echo "!!! TIER-2 EMERGENCY active - no replacements" ;;
    esac
    echo
  } >> "$LOG" 2>&1
  exit 0
fi

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') daily loop ==="
  "$PY" live/daily_loop.py
  rc=$?
  echo "--- daily_loop exit=$rc"
  case $rc in
    0) : ;;
    2) echo "!!! TIER-1 HALT active (new entries blocked)" ;;
    3) echo "!!! ERROR — broker/data failure, no orders submitted" ;;
    4) echo "!!! TIER-2 EMERGENCY — book flattened, manual clear required" ;;
  esac

  # Friday: weekly report
  if [ "$(date +%u)" -eq 5 ]; then
    echo "--- weekly report ---"
    "$PY" live/weekly_report.py >/dev/null 2>&1 && \
      echo "weekly report written to live/reports/" || \
      echo "!!! weekly report FAILED"
  fi
  echo
} >> "$LOG" 2>&1
