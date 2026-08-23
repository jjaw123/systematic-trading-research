"""Streamlit control room for regime-trader.

Run from the regime-trader directory:
    streamlit run monitoring/streamlit_app.py

Near-black canvas, hairline cards, one electric-blue accent; green and red are
reserved for signed values so the accent never competes with P&L. Data comes
from three places, each optional: the Alpaca API (account, positions, orders),
``state_snapshot.json`` (what the engine believes right now) and
``state_history.jsonl`` (how it got there).

Every external call is guarded — a failing component degrades to an inline
empty state, never a stack trace. Live sections auto-refresh via st.fragment.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv                      # noqa: E402

from monitoring import history, strategies, ui      # noqa: E402
from monitoring.theme import TOKENS, regime_color, stylesheet  # noqa: E402

st.set_page_config(page_title="regime-trader", page_icon="◆",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(stylesheet(), unsafe_allow_html=True)

VIEWS = ["Overview", "Strategies", "Positions", "Signals", "Risk",
         "System"]


def w(markup: str) -> None:
    """Write a component's markup."""
    st.markdown(markup, unsafe_allow_html=True)


def panel(name: str):
    """A card that can contain real Streamlit widgets (see theme.py)."""
    return st.container(key=f"panel-{name}")


# ------------------------------------------------------------------- data

@st.cache_resource(show_spinner="Connecting to Alpaca…")
def get_client():
    load_dotenv(ROOT / ".env", override=True)
    from core.broker.alpaca_client import AlpacaClient

    # max_retries=2: the UI must never hang through long backoff loops
    client = AlpacaClient.from_env(max_retries=2)
    client.connect()
    return client


def load_snapshot() -> dict | None:
    """The engine's current state, or None if it isn't running / mid-write."""
    path = ROOT / "state_snapshot.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def broker_state() -> tuple[object | None, dict, bool | None, str]:
    """``(client, account, market_open, error)`` — never raises."""
    try:
        client = get_client()
    except ValueError:
        return None, {}, None, "credentials"
    except Exception as exc:
        return None, {}, None, str(exc)
    try:
        account = client.get_account()
    except Exception as exc:
        return client, {}, None, str(exc)
    try:
        market_open = client.get_clock()["is_open"]
    except Exception:
        market_open = None
    return client, account, market_open, ""


# ---------------------------------------------------------------- sidebar

with st.sidebar:
    w(ui.one_line(f"""
      <div class="rt-brand" style="margin-bottom:20px;">{ui.brand_mark()}
        <span>regime-trader</span></div>
      <div style="font-size:0.7rem;letter-spacing:0.12em;text-transform:
        uppercase;color:{TOKENS['text_3']};margin-bottom:8px;">View</div>"""))
    view = st.radio("View", VIEWS, label_visibility="collapsed")
    st.markdown(f"<div style='height:1px;background:{TOKENS['border']};"
                "margin:18px 0 14px;'></div>", unsafe_allow_html=True)
    interval = st.selectbox("Auto-refresh", ["10s", "30s", "60s", "off"],
                            index=1)
    if st.button("Reconnect to Alpaca"):
        get_client.clear()
        st.rerun()
    st.caption("Reconnect after editing `.env` credentials.")

RUN_EVERY = None if interval == "off" else interval


# --------------------------------------------------------------- sections

def status_pills(client, account: dict, market_open: bool | None,
                 snap: dict | None, error: str) -> list[str]:
    """The chip row in the top bar — connection, market, engine health."""
    pills = []
    if error == "credentials":
        pills.append(ui.pill("no credentials", "bad", dot=True))
    elif error or client is None:
        pills.append(ui.pill("broker offline", "bad", dot=True))
    else:
        mode = "paper" if getattr(client, "paper", True) else "live"
        pills.append(ui.pill(f"connected · {mode}",
                             "ok" if mode == "paper" else "bad",
                             dot=True, live=True))
        status = account.get("status")
        if status and status != "ACTIVE":
            pills.append(ui.pill(f"account {status}", "warn"))
    if market_open is not None:
        pills.append(ui.pill("market open" if market_open else "market closed",
                             "ok" if market_open else ""))
    if snap:
        breaker = str(snap.get("breaker_status") or "?").lower()
        pills.append(ui.pill(f"breaker {breaker}",
                             {"normal": "ok", "reduced": "warn"}.get(
                                 breaker, "bad")))
        if not snap.get("feed_ok", True):
            pills.append(ui.pill("feed stale", "bad", dot=True))
        if not snap.get("api_ok", True):
            pills.append(ui.pill("api down", "bad", dot=True))
        pills.append(ui.pill(str(snap.get("mode") or "?"), "info"))
    else:
        pills.append(ui.pill("engine idle", ""))
    return pills


def regime_hero(snap: dict | None) -> None:
    if not snap:
        w(ui.hero("Current regime", "NOT RUNNING", TOKENS["text_3"],
                  sub="start the loop to classify the market"))
        return
    label = snap.get("regime")
    accent = regime_color(label)
    confirmed = snap.get("regime_confirmed")
    conf = snap.get("regime_confidence")
    sub = ("confirmed" if confirmed else "unconfirmed — awaiting persistence")
    if isinstance(conf, (int, float)):
        sub = f"{conf:.0%} posterior · {sub}"
    stability = snap.get("regime_stability")
    flicker, window = snap.get("flicker_rate"), snap.get("flicker_window")
    meta = [
        ("Stability", f"{stability} bars" if stability is not None
         else ui.DASH),
        ("Flicker", f"{flicker:.0f}/{window}"
         if flicker is not None and window else ui.DASH),
        ("Model age", ui.num(snap.get("model_age_days"), "{:.0f}d")),
    ]
    w(ui.hero("Current regime", str(label or "unknown").upper(),
              accent if confirmed else TOKENS["warn"], sub=sub, meta=meta))


def kpi_row(account: dict, snap: dict | None) -> None:
    equity = account.get("equity") if account else (
        snap.get("equity") if snap else None)
    pnl = snap.get("daily_pnl") if snap else None
    pnl_pct = snap.get("daily_pnl_pct") if snap else None
    alloc = snap.get("allocation") if snap else None
    trades = snap.get("trades_today") if snap else None

    # keyed container so the stylesheet can reflow this row to two-up on
    # narrow windows instead of stacking all four tiles (see theme.py)
    with st.container(key="kpirow"):
        c1, c2, c3, c4 = st.columns(4)
    with c1:
        w(ui.stat("Equity", ui.money0(equity),
                  ui.money0(account.get("cash"), "") + " cash"
                  if account.get("cash") is not None else None))
    with c2:
        w(ui.stat("Day P&L", ui.signed_money(pnl),
                  ui.pct(pnl_pct) if pnl_pct is not None else None,
                  ui.sign_class(pnl), muted=pnl is None))
    with c3:
        w(ui.stat("Allocation", ui.ratio_pct(alloc),
                  ui.num(snap.get("leverage") if snap else None, "{:.2f}x lev")
                  if snap and snap.get("leverage") else None,
                  muted=alloc is None))
    with c4:
        w(ui.stat("Trades today",
                  ui.num(trades) if trades is not None else ui.DASH,
                  ui.num(account.get("buying_power"), "${:,.0f} buying power")
                  if account.get("buying_power") is not None else None,
                  muted=trades is None))


def equity_panel(frame: pd.DataFrame) -> None:
    with panel("equity"):
        w('<div class="rt-card-head"><span class="rt-card-title">'
          'Equity curve</span></div>')
        chart = ui.equity_chart(frame)
        if chart is None:
            w(ui.empty("Not enough history yet",
                       "Two or more recorded cycles draw the curve. Run "
                       "<code>python main.py</code> and it fills in live."))
            return
        # height must be explicit: with width="stretch" Vega autosizes both
        # axes, and a spec-only height collapses the plot area to zero.
        st.altair_chart(chart, width="stretch", height=240, theme=None)
        span = frame["timestamp"]
        w(ui.foot(f"{len(frame)} cycles · "
                  f"{span.iloc[0]:%b %d %H:%M} → {span.iloc[-1]:%H:%M} UTC"))


def risk_panel(snap: dict | None) -> None:
    with panel("risk"):
        w('<div class="rt-card-head"><span class="rt-card-title">'
          'Risk budget</span></div>')
        if not snap:
            w(ui.empty("No risk telemetry",
                       "Limits and utilization appear once the engine runs."))
            return
        w(ui.gauge("Daily drawdown", snap.get("daily_dd"),
                   snap.get("daily_dd_limit")))
        w('<div style="height:12px;"></div>')
        w(ui.gauge("Drawdown from peak", snap.get("peak_dd"),
                   snap.get("peak_dd_limit")))
        alloc = snap.get("allocation")
        if isinstance(alloc, (int, float)):
            w('<div style="height:14px;"></div>')
            w(ui.meter("Capital deployed", ui.ratio_pct(alloc),
                       ui.clamp01(alloc), TOKENS["accent"]))


def ribbon_panel(frame: pd.DataFrame) -> None:
    with panel("ribbon"):
        w('<div class="rt-card-head"><span class="rt-card-title">'
          'Regime timeline</span></div>')
        if frame.empty:
            w(ui.empty("No regime history yet",
                       "Each engine cycle appends one segment to the ribbon."))
            return
        stamps = frame["timestamp"]
        w(ui.ribbon(history.regime_runs(frame),
                    f"{stamps.iloc[0]:%b %d %H:%M}",
                    f"{stamps.iloc[-1]:%b %d %H:%M} UTC"))


def positions_panel(client, snap: dict | None) -> None:
    with panel("positions"):
        w('<div class="rt-card-head"><span class="rt-card-title">'
          'Open positions</span></div>')
        live: list[dict] = []
        if client is not None:
            try:
                live = client.get_positions()
            except Exception:
                live = []
        if live:
            w(ui.rows(
                ui.row(str(p.get("symbol", "?")),
                       f"{p.get('qty', '?')} @ {ui.money(p.get('avg_entry_price'))}",
                       f"mark {ui.money(p.get('current_price'))} · "
                       f"value {ui.money0(p.get('market_value'))}",
                       ui.signed_money(p.get("unrealized_pl")),
                       ui.sign_class(p.get("unrealized_pl")))
                for p in live))
            return
        held = (snap or {}).get("positions") or {}
        if held:
            w(ui.rows(
                ui.row(sym,
                       f"{p.get('qty', '?')} @ {ui.money(p.get('entry_price'))}",
                       f"stop {ui.money(p.get('stop'), 'none')} · "
                       f"held {ui.holding(p.get('holding_days'))} · "
                       f"entered in {p.get('regime_at_entry') or '?'}",
                       ui.pct(p.get("pnl_pct"), 1),
                       ui.sign_class(p.get("pnl_pct")))
                for sym, p in held.items()))
            return
        w(ui.empty("Flat", "No open positions. Entries appear here the "
                           "moment an order fills."))


def orders_panel(client) -> None:
    with panel("orders"):
        w('<div class="rt-card-head"><span class="rt-card-title">'
          'Open orders</span></div>')
        orders: list[dict] = []
        if client is not None:
            try:
                orders = client.list_orders("open")
            except Exception as exc:
                w(ui.empty("Orders unavailable", ui.esc(str(exc))))
                return
        if not orders:
            w(ui.empty("No working orders",
                       "Submitted orders show here until they fill or cancel."))
            return
        w(ui.rows(
            ui.row(str(o.get("symbol", "?")),
                   f"{str(o.get('side', '')).upper()} {o.get('qty', '')} "
                   f"· {o.get('type', '')}",
                   f"status {o.get('status', '?')} · "
                   f"filled {o.get('filled_qty', 0)}",
                   ui.money(o.get("limit_price") or o.get("stop_price"), ""))
            for o in orders))


def signals_panel(snap: dict | None, limit: int | None = 6) -> None:
    with panel("signals"):
        w('<div class="rt-card-head"><span class="rt-card-title">'
          'Last cycle signals</span></div>')
        signals = (snap or {}).get("last_signals") or []
        if not signals:
            w(ui.empty("No signals this cycle",
                       "Approved and rejected signals both land here, with "
                       "the risk manager's reasoning."))
            return
        shown = signals[-limit:] if limit else signals
        items = []
        for sig in reversed(shown):
            approved = bool(sig.get("approved"))
            mods = sig.get("modifications") or []
            detail = ("; ".join(mods) if isinstance(mods, list) else str(mods))
            items.append(ui.row(
                str(sig.get("symbol", "?")),
                f"{sig.get('strategy') or 'signal'} · "
                f"{sig.get('time') or ''}".strip(" ·"),
                detail if approved else
                f"rejected: {sig.get('reason') or 'no reason given'}",
                (f"x{sig.get('qty')}" if approved else "blocked"),
                "is-pos" if approved else "is-neg"))
        w(ui.rows(items))
        if limit and len(signals) > limit:
            w(ui.foot(f"showing {limit} of {len(signals)} — "
                      "open the Signals view for all"))


def system_panel(client, account: dict, snap: dict | None,
                 error: str) -> None:
    with panel("system"):
        w('<div class="rt-card-head"><span class="rt-card-title">'
          'System health</span></div>')
        items = []
        if error == "credentials":
            items.append(ui.row("BROKER", "no credentials",
                                "add ALPACA_API_KEY and ALPACA_SECRET_KEY to "
                                ".env, then Reconnect", "offline", "is-neg"))
        elif error:
            items.append(ui.row("BROKER", "connection failed", error,
                                "offline", "is-neg"))
        else:
            items.append(ui.row(
                "BROKER", "Alpaca " + ("paper" if getattr(
                    client, "paper", True) else "LIVE"),
                f"account {account.get('status', '?')}", "online", "is-pos"))
        if snap:
            items.append(ui.row(
                "FEED", "market data",
                f"last snapshot {snap.get('timestamp', '?')}",
                "ok" if snap.get("feed_ok", True) else "stale",
                "is-pos" if snap.get("feed_ok", True) else "is-neg"))
            latency = snap.get("api_latency_ms")
            items.append(ui.row(
                "API", "broker round-trip",
                ui.num(latency, "{:.0f} ms") if latency else "no reading",
                "ok" if snap.get("api_ok", True) else "down",
                "is-pos" if snap.get("api_ok", True) else "is-neg"))
            items.append(ui.row(
                "HMM", "regime model",
                f"trained {ui.num(snap.get('model_age_days'), '{:.0f}')} "
                "days ago",
                str(snap.get("mode") or "?")))
        else:
            items.append(ui.row("ENGINE", "not running",
                                "start with `python main.py --dry-run`",
                                "idle"))
        w(ui.rows(items))
        if snap and snap.get("error"):
            st.error(f"Last engine error: {snap['error']}")


def halt_banner() -> None:
    lock = ROOT / "trading_halted.lock"
    if not lock.exists():
        return
    try:
        detail = lock.read_text().strip()
    except OSError:
        detail = ""
    st.error("**Trading is STOPPED** — `trading_halted.lock` is present. "
             f"Delete the file to resume.\n\n{detail}")


# ------------------------------------------------------------------ views

def render(view: str) -> None:
    client, account, market_open, error = broker_state()
    snap = load_snapshot()
    frame = history.load(history.history_path(ROOT))

    w(ui.topbar(view.lower(),
                status_pills(client, account, market_open, snap, error)))
    halt_banner()

    if view == "Overview":
        regime_hero(snap)
        kpi_row(account, snap)
        left, right = st.columns([2, 1])
        with left:
            equity_panel(frame)
        with right:
            risk_panel(snap)
        ribbon_panel(frame)
        a, b = st.columns(2)
        with a:
            positions_panel(client, snap)
        with b:
            signals_panel(snap)
    elif view == "Strategies":
        left, right = st.columns([3, 2])
        with left:
            w(strategies.book_panel())
            w(strategies.rejected_panel())
        with right:
            w(strategies.expectation_panel())
            w(strategies.ledger_panel())
            w(strategies.shutoff_panel())
        w(strategies.funnel_panel())
    elif view == "Positions":
        kpi_row(account, snap)
        positions_panel(client, snap)
        orders_panel(client)
    elif view == "Signals":
        regime_hero(snap)
        signals_panel(snap, limit=None)
        ribbon_panel(frame)
    elif view == "Risk":
        kpi_row(account, snap)
        left, right = st.columns([1, 2])
        with left:
            risk_panel(snap)
        with right:
            equity_panel(frame)
        positions_panel(client, snap)
    else:                                    # System
        system_panel(client, account, snap, error)
        ribbon_panel(frame)

    w(ui.foot(f"snapshot {(snap or {}).get('timestamp', 'none')} · "
              f"{len(frame)} cycles recorded · refresh {interval}"))


@st.fragment(run_every=RUN_EVERY)
def live_view() -> None:
    render(view)


live_view()
