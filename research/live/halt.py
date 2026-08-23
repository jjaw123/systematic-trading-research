"""Kill switch: daily skill + drawdown checks, halt state, append-only log.

Design constraints that are not negotiable in code:
  * HALT_RULES.yaml is opened READ-ONLY. Nothing here may write it.
  * Its SHA-256 is recorded in every log line, so an edit is always visible.
  * A halt never clears itself; clearing requires a human token (see the
    rules file). There is deliberately no function to auto-resume.
  * If the rules file is missing, unreadable, or malformed, the system
    FAILS CLOSED: entries are blocked. A broken safety check is a halt.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .random_entry import null_distribution, percentile_of

LIVE_DIR = Path(__file__).resolve().parent
RULES_PATH = LIVE_DIR.parent / "HALT_RULES.yaml"
LOG_PATH = LIVE_DIR / "HALT_LOG.jsonl"
STATE_PATH = LIVE_DIR / "HALT_STATE.json"


class HaltRulesError(RuntimeError):
    """Rules unreadable/malformed. Always resolves to a halt, never a pass."""


@dataclass
class CheckResult:
    date: str
    checked_at: str
    rules_sha256: str
    rules_revision: int
    status: str                  # OK | WARN | HALT | ERROR
    reasons: list
    detail: dict

    def to_json(self):
        return json.dumps(asdict(self), default=str)


def load_rules(path=None):
    """Read the authority file. Read-only, always.

    The path is resolved at call time (not bound as a default) so the
    location can never be silently frozen to a stale value.
    """
    path = path or RULES_PATH
    try:
        raw = Path(path).read_bytes()
    except OSError as ex:
        raise HaltRulesError(f"cannot read {path}: {ex}") from ex
    sha = hashlib.sha256(raw).hexdigest()
    try:
        cfg = yaml.safe_load(raw.decode())
    except yaml.YAMLError as ex:
        raise HaltRulesError(f"malformed rules file: {ex}") from ex
    for section in ("skill_test", "drawdown_test", "halt_behaviour"):
        if section not in cfg:
            raise HaltRulesError(f"rules file missing section: {section}")
    return cfg, sha


def drawdown_check(equity, cfg):
    """Live drawdown from high-water mark vs the worst backtest drawdown."""
    d = cfg["drawdown_test"]
    if not d.get("enabled", True) or len(equity) == 0:
        return "OK", None, {}
    dd = float(equity.iloc[-1] / equity.cummax().iloc[-1] - 1.0)
    worst = float(d["worst_backtest_drawdown"])
    warn_at = -worst * float(d["warn_multiple"])
    halt_at = -worst * float(d["halt_multiple"])
    detail = {"live_drawdown": round(dd, 4),
              "worst_backtest_drawdown": -worst,
              "warn_threshold": round(warn_at, 4),
              "halt_threshold": round(halt_at, 4)}
    if dd <= halt_at:
        return "HALT", (f"live drawdown {dd:.1%} breached halt threshold "
                        f"{halt_at:.1%} ({d['halt_multiple']}x backtest worst "
                        f"{-worst:.1%})"), detail
    if dd <= warn_at:
        return "WARN", (f"live drawdown {dd:.1%} reached backtest worst "
                        f"{-worst:.1%}"), detail
    return "OK", None, detail


def skill_check(live, market, cfg):
    """Rolling live return vs matched random-entry null distribution."""
    s = cfg["skill_test"]
    if not s.get("enabled", True):
        return "OK", [], {}
    rng = np.random.default_rng(int(s["seed"]))
    reasons, detail = [], {}
    status = "OK"
    for win in s["windows"]:
        win = int(win)
        if len(live) < max(win, int(s["min_live_days"])):
            detail[f"w{win}"] = {"status": "insufficient_history",
                                 "have": len(live), "need": win}
            continue
        r = live["net_return"].iloc[-win:]
        expo = live["gross_exposure"].iloc[-win:]
        mkt = market.reindex(r.index).fillna(0.0)
        invested = (expo > 1e-9)
        days_in = int(invested.sum())
        switches = int((invested.astype(int).diff().fillna(0) != 0).sum())
        avg_expo = float(expo[invested].mean()) if days_in else 0.0
        live_ret = float(np.prod(1.0 + r.values) - 1.0)
        if days_in == 0:
            detail[f"w{win}"] = {"status": "flat_all_window"}
            continue
        null = null_distribution(mkt.values, days_in, switches, avg_expo,
                                 int(s["simulations"]), rng)
        pct = percentile_of(live_ret, null)
        floor = float(s["percentile_floor"])
        med = float(np.median(null))
        spread = float(np.std(null))
        shortfall = med - live_ret
        min_spread = float(s.get("min_null_spread", 0.0))
        min_shortfall = float(s.get("min_shortfall", 0.0))
        entry = {"live_return": round(live_ret, 4),
                 "random_median": round(med, 4),
                 "null_spread": round(spread, 4),
                 "shortfall_vs_median": round(shortfall, 4),
                 "percentile": round(pct, 1), "floor": floor,
                 "days_in_market": days_in, "switches": switches,
                 "exposure_fraction": round(days_in / win, 3)}

        # Guard 1: a hair below the random median is not decay. This is what
        # stops the false HALT the 2001-2009 dry run produced.
        if shortfall < min_shortfall:
            entry["status"] = "within_noise_of_random"
            detail[f"w{win}"] = entry
            continue

        # Guard 2: the shortfall IS material, but if the null collapsed there
        # was no entry timing to judge (an always-invested book). The gap is
        # then drag/cost/execution rather than timing - still actionable, so
        # halt on the shortfall itself rather than on a meaningless percentile.
        if spread < min_spread:
            entry["status"] = "halt_on_shortfall_null_too_tight"
            detail[f"w{win}"] = entry
            status = "HALT"
            reasons.append(f"{win}d return {live_ret:+.2%} trails a matched "
                           f"always-invested benchmark by {shortfall:.2%} "
                           f"(random median {med:+.2%}); null spread "
                           f"{spread:.2%} is too tight to attribute this to "
                           f"entry timing - check costs, slippage, tracking")
            continue

        entry["status"] = "evaluated"
        detail[f"w{win}"] = entry
        if pct < floor:
            status = "HALT"
            reasons.append(f"{win}d return {live_ret:+.2%} sits at the "
                           f"{pct:.1f}th percentile of matched random entries "
                           f"(floor {floor:.0f}th, random median {med:+.2%}, "
                           f"shortfall {shortfall:.2%}, null spread {spread:.2%})")
    return status, reasons, detail


def read_state():
    if not STATE_PATH.exists():
        return {"halted": False, "since": None, "reasons": [], "cleared_by": None}
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        # Unreadable state = assume halted. Fail closed.
        return {"halted": True, "since": None,
                "reasons": ["HALT_STATE.json unreadable - failing closed"],
                "cleared_by": None}


def _write_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))


def _log(result: CheckResult):
    with open(LOG_PATH, "a") as fh:      # append-only, never rewritten
        fh.write(result.to_json() + "\n")


def entries_allowed():
    """The single gate the live engine must consult before ANY new entry."""
    state = read_state()
    if not state.get("halted"):
        return True, "ok"
    return False, f"HALTED since {state.get('since')}: {'; '.join(state.get('reasons', []))}"


def run_daily_check(live: pd.DataFrame, market: pd.Series, as_of=None):
    """live: DataFrame indexed by date with columns net_return, gross_exposure.
       market: daily returns of the traded market over the same dates."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    as_of = str(as_of or (live.index[-1].date() if len(live) else "n/a"))
    try:
        cfg, sha = load_rules()
    except HaltRulesError as ex:
        res = CheckResult(as_of, now, "UNREADABLE", -1, "ERROR",
                          [f"rules file unusable ({ex}) - failing closed"], {})
        _log(res)
        _write_state({"halted": True, "since": as_of,
                      "reasons": res.reasons, "cleared_by": None})
        return res

    rev = int(cfg.get("meta", {}).get("revision", 0))
    equity = (1.0 + live["net_return"]).cumprod() if len(live) else pd.Series(dtype=float)
    dd_status, dd_reason, dd_detail = drawdown_check(equity, cfg)
    sk_status, sk_reasons, sk_detail = skill_check(live, market, cfg)

    reasons = ([dd_reason] if dd_reason else []) + sk_reasons
    status = "HALT" if "HALT" in (dd_status, sk_status) else \
             ("WARN" if "WARN" in (dd_status, sk_status) else "OK")

    res = CheckResult(as_of, now, sha, rev, status, reasons,
                      {"drawdown": dd_detail, "skill": sk_detail})
    _log(res)

    prior = read_state()
    if status == "HALT":
        if not prior.get("halted"):
            _write_state({"halted": True, "since": as_of, "reasons": reasons,
                          "cleared_by": None})
    elif prior.get("halted"):
        # Recovery does NOT clear a halt. Only a human token does.
        pass
    return res
