"""Presentational components for the Streamlit dashboard.

Streamlit's stock widgets can't express the card language this dashboard
wants, so the visual surface is hand-rolled HTML built here and handed to
``st.markdown``. Two rules keep that safe and predictable:

1. Every builder returns a *single-line* string. Streamlit runs markup through
   a Markdown renderer first, where a blank line starts a new paragraph and a
   four-space indent starts a code block — both would shred the layout.
2. Every value is escaped and every colour comes from :mod:`monitoring.theme`.
"""

from __future__ import annotations

import html as _html
import re
from typing import Any, Iterable, Sequence

import pandas as pd

from monitoring.theme import TOKENS, regime_color

DASH = "—"


# --------------------------------------------------------------- formatting

def money(value: Any, fallback: str = DASH) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return fallback


def money0(value: Any, fallback: str = DASH) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return fallback


def signed_money(value: Any, fallback: str = DASH) -> str:
    try:
        return f"{'+' if float(value) >= 0 else '-'}${abs(float(value)):,.0f}"
    except (TypeError, ValueError):
        return fallback


def pct(value: Any, digits: int = 2, fallback: str = DASH) -> str:
    try:
        return f"{float(value):+.{digits}%}"
    except (TypeError, ValueError):
        return fallback


def ratio_pct(value: Any, digits: int = 0, fallback: str = DASH) -> str:
    try:
        return f"{float(value):.{digits}%}"
    except (TypeError, ValueError):
        return fallback


def num(value: Any, fmt: str = "{:,.0f}", fallback: str = DASH) -> str:
    try:
        return fmt.format(float(value))
    except (TypeError, ValueError):
        return fallback


def clamp01(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def sign_class(value: Any) -> str:
    """``is-pos`` / ``is-neg`` / ``is-flat`` for a possibly-missing number."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "is-flat"
    return "is-pos" if number > 0 else "is-neg" if number < 0 else "is-flat"


def holding(days: Any) -> str:
    try:
        value = float(days)
    except (TypeError, ValueError):
        return DASH
    return f"{value * 24:.0f}h" if value < 1 else f"{value:.1f}d"


def esc(value: Any) -> str:
    """HTML-escape any value for interpolation into markup."""
    return _html.escape(str(value if value is not None else ""))


# ------------------------------------------------------------------ markup

def one_line(markup: str) -> str:
    """Collapse markup to one line so Markdown can't reinterpret it."""
    return re.sub(r"\s*\n\s*", "", markup).strip()


def _arrow(direction: str) -> str:
    """Inline caret. Pairs with colour so meaning never rests on hue alone."""
    path = ("M1 5.5 L4.5 1.5 L8 5.5" if direction == "up"
            else "M1 1.5 L4.5 5.5 L8 1.5")
    return (f'<svg width="9" height="7" viewBox="0 0 9 7" fill="none" '
            f'aria-hidden="true"><path d="{path}" stroke="currentColor" '
            f'stroke-width="1.6" stroke-linecap="round" '
            f'stroke-linejoin="round"/></svg>')


def brand_mark() -> str:
    return ('<span class="rt-mark"><svg width="11" height="11" '
            'viewBox="0 0 12 12" fill="none" aria-hidden="true">'
            '<path d="M6 1 L11 6 L6 11 L1 6 Z" fill="#08090A"/></svg></span>')


def pill(text: str, kind: str = "", dot: bool = False,
         live: bool = False) -> str:
    """A status chip. ``kind`` is one of ok / warn / bad / info, or blank."""
    classes = ["rt-pill"]
    if kind:
        classes.append(f"is-{kind}")
    if live:
        classes.append("is-live")
    marker = '<span class="rt-dot"></span>' if dot else ""
    return (f'<span class="{" ".join(classes)}">{marker}'
            f'{esc(text)}</span>')


def topbar(subtitle: str, pills: Sequence[str]) -> str:
    return one_line(f"""
      <div class="rt-topbar">
        <div class="rt-brand">{brand_mark()}<span>regime-trader</span>
          <span style="color:{TOKENS['text_3']};font-weight:400;
            font-size:0.82rem;margin-left:2px;">{esc(subtitle)}</span></div>
        <div class="rt-pills">{"".join(pills)}</div>
      </div>""")


def section(title: str) -> str:
    return f'<div class="rt-section">{esc(title)}</div>'


def hero(label: str, value: str, accent: str, sub: str = "",
         meta: Sequence[tuple[str, str]] = ()) -> str:
    """The regime band — the one thing worth reading from across the room."""
    meta_html = "".join(
        f'<div><div class="rt-hero-label">{esc(name)}</div>'
        f'<div style="font-family:{TOKENS["font_mono"]};font-size:1.05rem;'
        f'color:{TOKENS["text"]};font-variant-numeric:tabular-nums;">'
        f'{esc(text)}</div></div>'
        for name, text in meta)
    sub_html = f'<div class="rt-hero-sub">{esc(sub)}</div>' if sub else ""
    return one_line(f"""
      <div class="rt-hero" style="border-color:{accent};">
        <div class="rt-hero-in">
          <div>
            <div class="rt-hero-label">{esc(label)}</div>
            <div class="rt-hero-value" style="color:{accent};">{esc(value)}</div>
            {sub_html}
          </div>
          <div class="rt-hero-meta">{meta_html}</div>
        </div>
      </div>""")


def stat(label: str, value: str, delta: str | None = None,
         delta_kind: str = "is-flat", muted: bool = False) -> str:
    """A KPI tile: tiny uppercase label, large tabular value, delta chip."""
    chip = ""
    if delta:
        icon = (_arrow("up") if delta_kind == "is-pos"
                else _arrow("down") if delta_kind == "is-neg" else "")
        chip = f'<span class="rt-delta {delta_kind}">{icon}{esc(delta)}</span>'
    muted_cls = " is-muted" if muted else ""
    return one_line(f"""
      <div class="rt-card"><div class="rt-stat">
        <div class="rt-stat-label">{esc(label)}</div>
        <div class="rt-stat-value{muted_cls}">{esc(value)}</div>
        {chip}
      </div></div>""")


def card(title: str, body: str, action: str = "") -> str:
    head = ""
    if title or action:
        head = (f'<div class="rt-card-head">'
                f'<span class="rt-card-title">{esc(title)}</span>'
                f'{action}</div>')
    return one_line(f'<div class="rt-card">{head}{body}</div>')


def row(key: str, primary: str, secondary: str = "",
        right: str = "", right_kind: str = "") -> str:
    sub = f'<div class="rt-row-sub">{esc(secondary)}</div>' if secondary else ""
    right_html = (f'<div class="rt-row-num {right_kind}">{esc(right)}</div>'
                  if right else "")
    return one_line(f"""
      <div class="rt-row">
        <div class="rt-row-key">{esc(key)}</div>
        <div class="rt-row-main"><div style="font-size:0.82rem;
          color:{TOKENS['text_2']};">{esc(primary)}</div>{sub}</div>
        {right_html}
      </div>""")


def rows(items: Iterable[str]) -> str:
    body = "".join(items)
    return f'<div class="rt-rows">{body}</div>'


def meter(name: str, value_text: str, ratio: float, color: str) -> str:
    width = clamp01(ratio) * 100
    return one_line(f"""
      <div class="rt-meter">
        <div class="rt-meter-head">
          <span class="rt-meter-name">{esc(name)}</span>
          <span class="rt-meter-val">{esc(value_text)}</span>
        </div>
        <div class="rt-meter-track"><div class="rt-meter-fill"
          style="width:{width:.1f}%;background:{color};"></div></div>
      </div>""")


def risk_color(ratio: float) -> tuple[str, str]:
    """Utilization colour plus a word, so the state isn't colour-only."""
    if ratio < 0.5:
        return TOKENS["pos"], "Safe"
    if ratio < 0.8:
        return TOKENS["warn"], "Elevated"
    return TOKENS["neg"], "Critical"


def gauge(name: str, used: Any, limit: Any, unit: str = "%") -> str:
    """Radial utilization dial with the exact figures spelled out beside it.

    Renders ``used`` as a share of ``limit``; the numeric value and the limit
    are always visible as text (WCAG: never rely on the arc alone).
    """
    try:
        used_f, limit_f = float(used), float(limit)
        ratio = clamp01(used_f / limit_f) if limit_f else 0.0
        centre = f"{ratio * 100:.0f}%"
        note = f"{used_f:.2%} of {limit_f:.1%} limit"
    except (TypeError, ValueError, ZeroDivisionError):
        ratio, centre, note = 0.0, DASH, "not reported yet"
    color, word = risk_color(ratio)
    if centre == DASH:
        color, word = TOKENS["text_3"], "No data"
    radius, circumference = 26.0, 2 * 3.14159265 * 26.0
    dash = circumference * ratio
    # A rounded cap on a zero-length arc still paints a dot, which reads as
    # "a little used" when the true answer is "none". Omit the arc entirely.
    arc = "" if dash < 0.5 else (
        f'<circle cx="32" cy="32" r="{radius}" fill="none" stroke="{color}" '
        f'stroke-width="6" stroke-linecap="round" '
        f'stroke-dasharray="{dash:.2f} {circumference:.2f}" '
        f'transform="rotate(-90 32 32)"/>')
    return one_line(f"""
      <div class="rt-gauge-wrap">
        <svg width="64" height="64" viewBox="0 0 64 64" role="img"
          aria-label="{esc(name)}: {esc(centre)} of limit, {esc(word)}">
          <circle cx="32" cy="32" r="{radius}" fill="none"
            stroke="rgba(255,255,255,0.07)" stroke-width="6"/>
          {arc}
          <text x="32" y="36" text-anchor="middle" fill="{TOKENS['text']}"
            font-family="{TOKENS['font_mono']}" font-size="13"
            font-weight="600">{esc(centre)}</text>
        </svg>
        <div class="rt-gauge-txt">
          <span class="rt-gauge-name">{esc(name)}</span>
          <span class="rt-gauge-note">{esc(note)}</span>
          <span class="rt-gauge-note" style="color:{color};">{esc(word)}</span>
        </div>
      </div>""")


def ribbon(runs: Sequence[tuple[str, int]], first: str, last: str) -> str:
    """Regime timeline: one flex segment per run, sized by its length."""
    if not runs:
        return empty("No regime history yet",
                     "The ribbon fills in as the live loop records cycles.")
    total = sum(length for _, length in runs) or 1
    spans = "".join(
        f'<span style="flex-grow:{length};background:{regime_color(label)};" '
        f'title="{esc(label)} · {length} cycles"></span>'
        for label, length in runs)
    seen: list[str] = []
    for label, _ in runs:
        if label not in seen:
            seen.append(label)
    legend = "".join(
        f'<span><i style="background:{regime_color(label)};"></i>'
        f'{esc(label)} '
        f'{sum(n for l, n in runs if l == label) / total:.0%}</span>'
        for label in seen)
    return one_line(f"""
      <div><div class="rt-ribbon" role="img"
        aria-label="Regime timeline across {total} cycles">{spans}</div>
      <div class="rt-ribbon-axis"><span>{esc(first)}</span>
        <span>{esc(last)}</span></div>
      <div class="rt-legend">{legend}</div></div>""")


def empty(title: str, hint: str = "") -> str:
    """Empty state. ``hint`` may contain ``<code>`` for commands to run."""
    hint_html = f'<div class="rt-empty-hint">{hint}</div>' if hint else ""
    return one_line(f"""
      <div class="rt-empty">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
          aria-hidden="true"><circle cx="12" cy="12" r="9"
          stroke="{TOKENS['text_3']}" stroke-width="1.5"/>
          <path d="M12 8v5M12 16h.01" stroke="{TOKENS['text_3']}"
          stroke-width="1.5" stroke-linecap="round"/></svg>
        <div class="rt-empty-title">{esc(title)}</div>
        {hint_html}
      </div>""")


def foot(text: str) -> str:
    return f'<div class="rt-foot">{esc(text)}</div>'


# ------------------------------------------------------------------- chart

def equity_chart(frame: pd.DataFrame, height: int = 230):
    """Themed Altair area chart of equity over time, or ``None`` if it can't
    be built (too few points, or an Altair version without gradients)."""
    if frame.empty or frame["equity"].dropna().shape[0] < 2:
        return None
    try:
        import altair as alt

        data = frame[["timestamp", "equity", "regime"]].dropna(
            subset=["equity"]).copy()
        data["regime"] = data["regime"].fillna("unknown")
        low = float(data["equity"].min())
        high = float(data["equity"].max())
        spread = max(high - low, high * 0.002, 1.0)
        # Two quirks force this shape, both verified in the browser:
        #  - a bounded scale (`domain=`, or domainMin/domainMax) breaks Vega's
        #    autosize:fit height solve and collapses the plot to zero height;
        #  - `zero=False` is ignored for area marks unless y2 is a real field.
        # So the baseline and the headroom live in the data instead, and the
        # scale stays data-driven.
        data["floor"] = low - spread * 0.30
        data["ceiling"] = high + spread * 0.12

        base = alt.Chart(data).encode(
            x=alt.X("timestamp:T", title=None,
                    axis=alt.Axis(format="%H:%M", tickCount=6)),
            y=alt.Y("equity:Q", title=None,
                    scale=alt.Scale(zero=False, nice=False),
                    axis=alt.Axis(format="$,.0f", tickCount=5)),
            y2=alt.Y2("floor:Q"),
        )
        area = base.mark_area(
            interpolate="monotone",
            line={"color": TOKENS["accent"], "strokeWidth": 2},
            color=alt.Gradient(
                gradient="linear", x1=1, x2=1, y1=1, y2=0,
                stops=[alt.GradientStop(color=TOKENS["accent"], offset=0.0),
                       alt.GradientStop(color=TOKENS["accent_hi"],
                                        offset=1.0)]),
            opacity=0.22,
        )
        points = alt.Chart(data).mark_circle(size=52, opacity=0).encode(
            x=alt.X("timestamp:T", title=None),
            y=alt.Y("equity:Q", title=None),
            tooltip=[alt.Tooltip("timestamp:T", title="Time",
                                 format="%b %d %H:%M"),
                     alt.Tooltip("equity:Q", title="Equity", format="$,.2f"),
                     alt.Tooltip("regime:N", title="Regime")])
        # Invisible rule at the ceiling: the only way to buy top headroom
        # while leaving the scale data-driven (see the note above).
        headroom = alt.Chart(data).mark_rule(opacity=0).encode(
            y=alt.Y("ceiling:Q", title=None))
        # NB: chart.configure(...) *replaces* the config object, so background
        # goes through properties() — chaining it after configure_axis would
        # silently drop the axis theming.
        return (area + headroom + points).properties(
            height=height, background=TOKENS["card"],
        ).configure_view(
            strokeWidth=0, fill=TOKENS["card"],
        ).configure_axis(
            grid=True, gridColor=TOKENS["border"], gridDash=[2, 3],
            domain=False, tickColor=TOKENS["border"], tickSize=4,
            labelColor=TOKENS["text_3"], labelFont="JetBrains Mono",
            labelFontSize=10, labelPadding=6,
        )
    except Exception:
        return None
