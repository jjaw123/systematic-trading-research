"""Strategy research panels for the dashboard.

Reads the research artefacts — the append-only idea log and variant ledger,
the sweep results, the live journal and shutoff state — and renders what the
book is actually made of, what it is expected to do, and why almost
everything was rejected.

Every reader is guarded: a missing or malformed file degrades to an empty
state, never a stack trace.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from monitoring import ui
from monitoring.theme import TOKENS

RESEARCH = Path(__file__).resolve().parents[2] / "research"

# The deployed book and its recorded backtest expectations.
DEPLOYED = {
    "name": "IDEA-109 — risk-layered book (unlevered)",
    "risk_per_trade": "0.75% of equity per trade",
    "components": [
        ("IDEA-066", "Sector rotation, top 3 by 6-month return",
         "9 SPDR sectors, monthly", "[0225]"),
        ("IDEA-107", "Volatility-targeted QQQ, 20% target",
         "daily rescale, cap 2x", "[0193]"),
    ],
    "sizing": "position = 0.75% / (2 x ATR20 / price), then caps, then a 20% "
              "book volatility target",
    "eras": {
        "2001-2009 (worst era)": {"cagr": 0.0287, "sharpe": 0.11, "dd": -0.333},
        "2010-2022 (train)": {"cagr": 0.1094, "sharpe": 0.80, "dd": -0.156},
    },
}

FUNNEL = [
    ("Published rules reviewed", 150,
     "from two candidate lists, deduplicated"),
    ("Logged as testable ideas", 108,
     "the rest were blocked: no data, vague rules, or protocol-incompatible"),
    ("Variants registered and run", 225,
     "every one written down and counted before it executed"),
    ("Passed on the train window", 5,
     "beat buy-and-hold on BOTH return and drawdown"),
    ("Survived scrutiny", 3,
     "two were disqualified as engine artefacts on inspection"),
    ("Survived the worst-era retest", 1,
     "and its parameter ranking across eras is statistically noise"),
]


# ----------------------------------------------------------------- readers

def _read_text(path: Path) -> str:
    try:
        return path.read_text()
    except OSError:
        return ""


def ledger_stats() -> dict:
    """Counts straight from the append-only variant ledger."""
    text = _read_text(RESEARCH / "VARIANT_LEDGER.md")
    if not text:
        return {}
    ids = set(re.findall(r"^\[(\d{4})\]", text, flags=re.M))
    results = re.findall(r"\| RESULT \|.*?\| (PASS|FAIL|WITHHELD[^|]*)", text)
    verdicts = {"PASS": 0, "FAIL": 0, "WITHHELD": 0}
    for v in results:
        key = "WITHHELD" if v.startswith("WITHHELD") else v
        verdicts[key] = verdicts.get(key, 0) + 1
    return {"variants": len(ids), "results": len(results),
            "notes": text.count("| NOTE |"), **verdicts}


def idea_count() -> int:
    text = _read_text(RESEARCH / "IDEA_LOG.md")
    return len(set(re.findall(r"^## (IDEA-\d+)", text, flags=re.M)))


def sweep_frame() -> pd.DataFrame:
    path = RESEARCH / "results" / "train_sweep_by_idea.csv"
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def live_targets() -> tuple[dict, str]:
    """Most recent target weights the loop computed, from the journal."""
    path = RESEARCH / "live" / "JOURNAL.jsonl"
    text = _read_text(path)
    if not text:
        return {}, ""
    latest, as_of = {}, ""
    for line in text.splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("kind") == "event" and rec.get("what") == "signals_computed":
            latest = rec.get("detail", {}).get("targets", {}) or {}
            as_of = rec.get("detail", {}).get("signal_date", "")
    return latest, as_of


def shutoff_state() -> dict:
    live = RESEARCH / "live"
    out = {"tier1": None, "tier2": None, "revision": None}
    try:
        out["tier1"] = json.loads((live / "HALT_STATE.json").read_text())
    except (OSError, json.JSONDecodeError):
        out["tier1"] = {"halted": False}
    try:
        out["tier2"] = json.loads((live / "EMERGENCY_HALT.json").read_text())
    except (OSError, json.JSONDecodeError):
        out["tier2"] = {"halted": False}
    m = re.search(r"revision:\s*(\d+)", _read_text(RESEARCH / "HALT_RULES.yaml"))
    out["revision"] = m.group(1) if m else None
    return out


# ------------------------------------------------------------------ panels

def book_panel() -> str:
    targets, as_of = live_targets()
    items = []
    for idea, name, detail, variant in DEPLOYED["components"]:
        items.append(ui.row(idea, name, f"{detail} · ledger {variant}"))
    body = ui.rows(items)
    if targets:
        live_rows = [
            ui.row(sym, f"target weight {w:.1%}", "",
                   right=f"{w:.1%}",
                   right_kind=ui.sign_class(w))
            for sym, w in sorted(targets.items(), key=lambda kv: -abs(kv[1]))]
        body += ui.section(f"Latest targets · signal from {as_of or 'n/a'}")
        body += ui.rows(live_rows)
    else:
        body += ui.empty("No live targets yet",
                         "Run <code>python research/live/daily_loop.py</code>")
    return ui.card(DEPLOYED["name"], body)


def expectation_panel() -> str:
    items = []
    for era, e in DEPLOYED["eras"].items():
        items.append(ui.row(
            era, f"CAGR {e['cagr']:+.2%} · Sharpe {e['sharpe']:.2f}",
            f"max drawdown {e['dd']:.1%}",
            right=f"{e['cagr']:+.1%}",
            right_kind=ui.sign_class(e["cagr"])))
    note = (f'<div class="rt-row-sub" style="padding:10px 14px;">'
            f'Sizing: {ui.esc(DEPLOYED["sizing"])}. These are the recorded '
            f'backtest figures the live book is measured against — not a '
            f'forecast.</div>')
    return ui.card("Backtest expectation", ui.rows(items) + note)


def funnel_panel() -> str:
    top = FUNNEL[0][1]
    items = []
    for label, n, detail in FUNNEL:
        ratio = n / top if top else 0
        colour = TOKENS["accent"] if n > 5 else TOKENS["warn"]
        items.append(ui.meter(label, f"{n}", ratio, colour))
        items.append(f'<div class="rt-row-sub" style="margin:-6px 0 12px;">'
                     f'{ui.esc(detail)}</div>')
    return ui.card("How many survived", "".join(items))


def ledger_panel() -> str:
    s = ledger_stats()
    if not s:
        return ui.card("Research ledger",
                       ui.empty("Ledger not found",
                                "Expected <code>research/VARIANT_LEDGER.md</code>"))
    items = [
        ui.row("Variants", "registered before running", "append-only, never edited",
               right=str(s.get("variants", 0))),
        ui.row("Pass verdicts", "across ALL runs, incl. era and parameter sweeps",
               "not 62 working strategies — most are settings of one mechanism, "
               "many judged against a weak benchmark",
               right=str(s.get("PASS", 0)), right_kind="is-pos"),
        ui.row("Fail verdicts", "did not clear both bars", "",
               right=str(s.get("FAIL", 0)), right_kind="is-neg"),
        ui.row("Deployed", "distinct mechanisms actually traded", "",
               right="1", right_kind="is-pos"),
        ui.row("Ideas logged", "each with rule, settings, pass criteria", "",
               right=str(idea_count())),
        ui.row("Audit notes", "corrections and disqualifications, appended", "",
               right=str(s.get("notes", 0))),
    ]
    return ui.card("Research ledger", ui.rows(items))


def rejected_panel(limit: int = 12) -> str:
    frame = sweep_frame()
    if frame.empty:
        return ui.card("Rejected strategies",
                       ui.empty("No sweep results found",
                                "Run <code>python scripts/run_sweep.py</code>"))
    failed = frame[frame["verdict"].astype(str).str.startswith("FAIL")]
    failed = failed.head(limit)
    items = [ui.row(str(r["idea"]).replace("IDEA-", ""),
                    str(r["name"]),
                    f"{r['asset']} · vs buy-and-hold {r['bh']}",
                    right=str(r["ret"]).split(" ")[0],
                    right_kind=ui.sign_class(
                        -1 if str(r["ret"]).startswith("-") else 1))
             for _, r in failed.iterrows()]
    more = len(frame) - len(failed)
    foot = (f'<div class="rt-row-sub" style="padding:10px 14px;">'
            f'and {more} more — the full record is in '
            f'<code>VARIANT_LEDGER.md</code>.</div>' if more > 0 else "")
    return ui.card("Rejected — kept on the record", ui.rows(items) + foot)


def shutoff_panel() -> str:
    s = shutoff_state()
    t1, t2 = s["tier1"] or {}, s["tier2"] or {}
    def state_row(label, blob, detail):
        halted = bool(blob.get("halted"))
        return ui.row(label,
                      "HALTED" if halted else "armed, not triggered",
                      detail if not halted else
                      "; ".join(str(x) for x in (blob.get("reasons")
                                                 or blob.get("problems") or []))[:120],
                      right="HALT" if halted else "OK",
                      right_kind="is-neg" if halted else "is-pos")
    items = [
        state_row("Tier 1", t1,
                  "blocks new entries; existing positions still exit"),
        state_row("Tier 2", t2,
                  "flattens everything on an integrity failure"),
        ui.row("Rules file", f"revision {s['revision'] or '?'}",
               "owner-edited only; hash logged daily"),
    ]
    return ui.card("Shutoff rules", ui.rows(items))
