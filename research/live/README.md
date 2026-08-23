# Kill Switch — operator notes

**Authority file:** `research/HALT_RULES.yaml`. It is the only place thresholds
live. Nothing in this codebase writes to it (enforced by
`test_checker_never_writes_rules_file`). Its SHA-256 and revision are stamped
into every log line, so an edit is permanently visible in the audit trail.

## Daily operation
Run after every close:

    python research/live/daily_check.py --live-file research/live/live_returns.csv --market SPY

`live_returns.csv` needs: `Date,net_return,gross_exposure` (net_return = the
book's realized daily return after costs; gross_exposure = summed absolute
position weights that day).

Exit codes: `0` OK · `1` WARN · `2` HALT · `3` ERROR (rules unreadable → halt).
Every run appends one JSON line to `HALT_LOG.jsonl` and updates `HALT_STATE.json`.

## Wiring it into the live engine
Before opening ANY new position:

    from live.halt import entries_allowed
    ok, why = entries_allowed()
    if not ok:
        log.warning("entry blocked: %s", why)
        return          # existing positions still follow their normal exits

## Clearing a halt
There is deliberately no function that does this — verified by
`test_no_programmatic_resume_function_exists`. To resume, edit
`HALT_STATE.json` by hand:

    "halted": false,
    "cleared_by": "I-REVIEWED-THE-HALT-AND-ACCEPT-THE-RISK — <date> — <reason>"

Do it while flat, or having deliberately decided to carry the position, and
never during the session that triggered it. Recovery does NOT auto-clear a
halt: a clean day after a breach leaves the halt standing
(`test_halt_does_not_clear_itself_on_recovery`).

## Fail-closed behaviour
Missing rules file, malformed YAML, or unreadable state all resolve to
"entries blocked". A safety check that cannot run is a halt, not a pass.
