#!/bin/bash
# Daily paper-trading loop wrapper. Invoked by cron after the close.
# Runs the loop, then on Fridays also builds the weekly report.
# All output is appended to live/cron.log; exit codes are recorded.

set -uo pipefail

PROJECT="/Users/Jainithin/Documents/PersonalProjects/Trading Bot"
PY="$PROJECT/regime-trader/.venv/bin/python"
RESEARCH="$PROJECT/research"
LOG="$RESEARCH/live/cron.log"

cd "$RESEARCH" || exit 1

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
