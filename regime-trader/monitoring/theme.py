"""Design tokens and the injected stylesheet for the Streamlit dashboard.

Single source of truth for colour, type, spacing and radius. Nothing else in
the ``monitoring`` package hardcodes a hex value — components read ``TOKENS``
or the CSS custom properties this module emits.

Direction: near-black canvas with hairline borders and one electric-blue
accent. Green and red are reserved for signed values (P&L, drawdown) so the
accent never competes with the numbers that matter.
"""

from __future__ import annotations

TOKENS: dict[str, str] = {
    # surfaces — four steps of elevation, all within 8% lightness
    "bg": "#08090A",
    "bg_elev": "#0C0D0F",
    "card": "#101113",
    "card_hi": "#15171A",
    # hairlines
    "border": "#1E2024",
    "border_hi": "#2A2D33",
    # text — 4.5:1+ for body, 3:1+ for the muted tier
    "text": "#F5F6F7",
    "text_2": "#A2A9B2",
    "text_3": "#6E757E",
    # single accent
    "accent": "#3B82F6",
    "accent_hi": "#60A5FA",
    "accent_wash": "rgba(59,130,246,0.10)",
    # semantic — signed values only
    "pos": "#22C55E",
    "pos_wash": "rgba(34,197,94,0.12)",
    "neg": "#EF4444",
    "neg_wash": "rgba(239,68,68,0.12)",
    "warn": "#F5A524",
    "warn_wash": "rgba(245,165,36,0.12)",
    # type
    "font_sans": "'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif",
    "font_mono": "'JetBrains Mono', ui-monospace, SFMono-Regular, monospace",
}

#: Regime label -> colour token key. Unknown labels fall back to ``text_3``.
REGIME_COLORS: dict[str, str] = {
    "bull": "pos",
    "low_vol_bull": "pos",
    "high_vol_bull": "warn",
    "chop": "warn",
    "neutral": "warn",
    "sideways": "warn",
    "bear": "neg",
    "crash": "neg",
}

FONT_URL = ("https://fonts.googleapis.com/css2?"
            "family=IBM+Plex+Sans:wght@400;500;600;700"
            "&family=JetBrains+Mono:wght@400;500;600;700&display=swap")


def regime_color(label: str | None) -> str:
    """Resolve a regime label to a hex colour."""
    key = REGIME_COLORS.get(str(label or "").lower(), "text_3")
    return TOKENS[key]


def _vars() -> str:
    """Emit the token map as CSS custom properties."""
    return "\n".join(f"  --{k.replace('_', '-')}: {v};"
                     for k, v in TOKENS.items())


def stylesheet() -> str:
    """The full stylesheet: token vars, Streamlit chrome, component classes."""
    return f"""<style>
@import url('{FONT_URL}');

:root {{
{_vars()}
  --r-sm: 6px; --r-md: 10px; --r-lg: 14px; --r-xl: 18px;
  --ease: cubic-bezier(0.4, 0, 0.2, 1);
}}

/* ---------------------------------------------------- streamlit chrome */

.stApp {{ background: var(--bg); }}
html, body, [class*="st-"], button, input, select, textarea {{
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}}
/* Streamlit draws its icons as ligatures in a Material font. The blanket
   font-family above would match those spans too and leak the raw ligature
   name ("keyboard_double_arrow_left") into the UI — restore their font. */
[data-testid="stIconMaterial"], .material-icons, .material-icons-outlined,
span[class*="material-symbols"], [class*="material-symbols"] {{
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stToolbar"] {{ right: 8px; top: 8px; }}
[data-testid="stMainBlockContainer"] {{
  padding: 1.75rem 2.25rem 4rem; max-width: 1600px;
}}
[data-testid="stDecoration"], footer {{ display: none; }}
/* Streamlit's default 1rem gap is too airy for a monitoring grid */
[data-testid="stVerticalBlock"] {{ gap: 0.85rem; }}
[data-testid="stHorizontalBlock"] {{ gap: 0.85rem; }}

/* sidebar */
[data-testid="stSidebar"] {{
  background: var(--bg-elev);
  border-right: 1px solid var(--border);
}}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
  padding: 1.5rem 1.1rem;
}}

/* sidebar radio rendered as a nav rail */
[data-testid="stSidebar"] [role="radiogroup"] {{ gap: 2px; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {{
  padding: 8px 11px; border-radius: var(--r-sm); cursor: pointer;
  transition: background 160ms var(--ease), box-shadow 160ms var(--ease);
  min-height: 38px; align-items: center;
}}
[data-testid="stSidebar"] [data-testid="stRadioOption"] p {{
  font-size: 0.86rem; font-weight: 500; color: var(--text-2);
  transition: color 160ms var(--ease);
}}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {{
  background: var(--card);
}}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover p {{
  color: var(--text);
}}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {{
  background: var(--accent-wash); box-shadow: inset 2px 0 0 var(--accent);
}}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {{
  color: var(--text); font-weight: 600;
}}
/* keyboard focus only — :focus-within would ring on every mouse click */
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(:focus-visible) {{
  outline: 2px solid var(--accent); outline-offset: 1px;
}}
/* the radio dot is redundant once the row reads as a nav item — it is the
   div immediately preceding the option's label text */
[data-testid="stSidebar"] [data-testid="stRadioOption"]
  div:has(+ [data-testid="stMarkdownContainer"]) {{
  display: none;
}}

/* controls */
.stButton > button {{
  background: var(--card); color: var(--text);
  border: 1px solid var(--border-hi); border-radius: var(--r-sm);
  font-size: 0.84rem; font-weight: 500; padding: 0.42rem 0.9rem;
  width: 100%; cursor: pointer;
  transition: border-color 160ms var(--ease), background 160ms var(--ease);
}}
.stButton > button:hover {{
  border-color: var(--accent); background: var(--card-hi); color: var(--text);
}}
.stButton > button:focus-visible {{
  outline: 2px solid var(--accent); outline-offset: 2px;
}}
[data-baseweb="select"] > div {{
  background: var(--card) !important; border-color: var(--border-hi) !important;
  border-radius: var(--r-sm) !important; font-size: 0.84rem;
}}
[data-baseweb="popover"] li {{ font-size: 0.84rem; }}

/* dataframes — flatten to match the card language */
[data-testid="stDataFrame"] {{
  border: 1px solid var(--border); border-radius: var(--r-md);
  overflow: hidden;
}}
[data-testid="stDataFrame"] * {{ font-family: var(--font-mono) !important; }}

/* alerts */
[data-testid="stAlert"] {{
  border-radius: var(--r-md); border: 1px solid var(--border-hi);
  background: var(--card); font-size: 0.86rem;
}}

/* ------------------------------------------------------------ topbar */

.rt-topbar {{
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; flex-wrap: wrap; margin-bottom: 18px;
}}
.rt-brand {{
  display: flex; align-items: center; gap: 10px;
  font-size: 1.02rem; font-weight: 600; color: var(--text);
  letter-spacing: -0.01em;
}}
.rt-brand .rt-mark {{
  width: 22px; height: 22px; border-radius: var(--r-sm);
  background: var(--accent); display: grid; place-items: center;
  box-shadow: 0 0 18px rgba(59,130,246,0.45);
}}
.rt-brand .rt-mark svg {{ display: block; }}
.rt-pills {{ display: flex; gap: 6px; flex-wrap: wrap; }}

/* --------------------------------------------------------------- pill */

.rt-pill {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 999px;
  font-family: var(--font-mono); font-size: 0.7rem; font-weight: 500;
  letter-spacing: 0.04em; text-transform: uppercase;
  border: 1px solid var(--border-hi); background: var(--card);
  color: var(--text-2); white-space: nowrap;
}}
.rt-pill .rt-dot {{
  width: 6px; height: 6px; border-radius: 50%; background: currentColor;
  flex: none;
}}
.rt-pill.is-ok   {{ color: var(--pos);    border-color: rgba(34,197,94,0.30);  background: var(--pos-wash); }}
.rt-pill.is-warn {{ color: var(--warn);   border-color: rgba(245,165,36,0.30); background: var(--warn-wash); }}
.rt-pill.is-bad  {{ color: var(--neg);    border-color: rgba(239,68,68,0.30);  background: var(--neg-wash); }}
.rt-pill.is-info {{ color: var(--accent); border-color: rgba(59,130,246,0.30); background: var(--accent-wash); }}
.rt-pill.is-live .rt-dot {{ animation: rt-pulse 2s var(--ease) infinite; }}
@keyframes rt-pulse {{
  0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }}
}}

/* ---------------------------------------------------------- hero band */

.rt-hero {{
  position: relative; overflow: hidden;
  border: 1px solid var(--accent); border-radius: var(--r-lg);
  background: var(--bg-elev); padding: 20px 24px; margin-bottom: 4px;
}}
/* Verity's vertical-line texture, faded so it never fights the label */
.rt-hero::after {{
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: repeating-linear-gradient(90deg,
    transparent 0 7px, rgba(59,130,246,0.14) 7px 8px);
  -webkit-mask-image: linear-gradient(0deg, #000 0%, transparent 78%);
  mask-image: linear-gradient(0deg, #000 0%, transparent 78%);
  opacity: 0.7;
}}
.rt-hero-in {{
  position: relative; z-index: 1; display: flex; align-items: center;
  justify-content: space-between; gap: 20px; flex-wrap: wrap;
}}
.rt-hero-label {{
  font-size: 0.66rem; font-weight: 600; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--text-3); margin-bottom: 6px;
}}
.rt-hero-value {{
  font-size: 2.1rem; font-weight: 600; line-height: 1.05;
  letter-spacing: -0.03em; color: var(--text);
}}
.rt-hero-sub {{
  font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-2);
  margin-top: 8px;
}}
.rt-hero-meta {{ display: flex; gap: 26px; flex-wrap: wrap; }}

/* -------------------------------------------------------------- cards */

.rt-card {{
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 16px 18px; height: 100%;
  transition: border-color 200ms var(--ease);
}}
.rt-card:hover {{ border-color: var(--border-hi); }}
.rt-card-head {{
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 14px;
}}
.rt-card-title {{
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.11em;
  text-transform: uppercase; color: var(--text-3);
}}

/* stat tile */
.rt-stat {{ display: flex; flex-direction: column; gap: 7px; }}
.rt-stat-label {{
  font-size: 0.68rem; font-weight: 600; letter-spacing: 0.11em;
  text-transform: uppercase; color: var(--text-3);
}}
.rt-stat-value {{
  font-family: var(--font-mono); font-size: 1.6rem; font-weight: 600;
  letter-spacing: -0.02em; color: var(--text); line-height: 1.1;
  font-variant-numeric: tabular-nums;
}}
.rt-stat-value.is-muted {{ color: var(--text-3); font-weight: 400; }}
.rt-delta {{
  display: inline-flex; align-items: center; gap: 4px; align-self: flex-start;
  padding: 2px 7px; border-radius: var(--r-sm);
  font-family: var(--font-mono); font-size: 0.72rem; font-weight: 500;
  font-variant-numeric: tabular-nums;
}}
.rt-delta.is-pos {{ color: var(--pos); background: var(--pos-wash); }}
.rt-delta.is-neg {{ color: var(--neg); background: var(--neg-wash); }}
.rt-delta.is-flat {{ color: var(--text-3); background: rgba(255,255,255,0.04); }}

/* ------------------------------------------------------------ list rows */

.rt-rows {{ display: flex; flex-direction: column; }}
.rt-row {{
  display: flex; align-items: center; gap: 12px;
  padding: 9px 10px; border-radius: var(--r-sm);
  border-bottom: 1px solid var(--border);
  transition: background 160ms var(--ease);
}}
.rt-row:last-child {{ border-bottom: none; }}
.rt-row:hover {{ background: var(--card-hi); }}
.rt-row-key {{
  font-family: var(--font-mono); font-size: 0.82rem; font-weight: 600;
  color: var(--text); min-width: 62px;
}}
.rt-row-main {{ flex: 1; min-width: 0; }}
.rt-row-sub {{
  font-size: 0.74rem; color: var(--text-3); margin-top: 2px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}
.rt-row-num {{
  font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-2);
  font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap;
}}
.rt-row-num.is-pos {{ color: var(--pos); }}
.rt-row-num.is-neg {{ color: var(--neg); }}

/* --------------------------------------------------------- meter / bar */

.rt-meter {{ display: flex; flex-direction: column; gap: 7px; }}
.rt-meter-head {{
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 10px;
}}
.rt-meter-name {{ font-size: 0.8rem; color: var(--text-2); }}
.rt-meter-val {{
  font-family: var(--font-mono); font-size: 0.8rem; color: var(--text);
  font-variant-numeric: tabular-nums;
}}
.rt-meter-track {{
  height: 6px; border-radius: 999px; background: rgba(255,255,255,0.06);
  overflow: hidden;
}}
.rt-meter-fill {{
  height: 100%; border-radius: 999px;
  transition: width 400ms var(--ease);
}}

/* ------------------------------------------------------------- ribbon */

.rt-ribbon {{
  display: flex; height: 30px; border-radius: var(--r-sm);
  overflow: hidden; border: 1px solid var(--border); gap: 1px;
  background: var(--border);
}}
.rt-ribbon span {{ flex: 1 1 auto; min-width: 1px; }}
.rt-ribbon-axis {{
  display: flex; justify-content: space-between;
  font-family: var(--font-mono); font-size: 0.68rem; color: var(--text-3);
  margin-top: 6px;
}}
.rt-legend {{
  display: flex; gap: 14px; flex-wrap: wrap; margin-top: 10px;
  font-size: 0.72rem; color: var(--text-2);
}}
.rt-legend i {{
  display: inline-block; width: 9px; height: 9px; border-radius: 2px;
  margin-right: 6px; vertical-align: -1px;
}}

/* -------------------------------------------------------- empty state */

.rt-empty {{
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 30px 20px; text-align: center;
  border: 1px dashed var(--border-hi); border-radius: var(--r-md);
  color: var(--text-3);
}}
.rt-empty-title {{ font-size: 0.86rem; font-weight: 500; color: var(--text-2); }}
.rt-empty-hint {{ font-size: 0.76rem; max-width: 46ch; line-height: 1.55; }}
.rt-empty code {{
  font-family: var(--font-mono); font-size: 0.74rem; color: var(--accent-hi);
  background: var(--accent-wash); padding: 1px 5px; border-radius: 4px;
}}

/* Cards that must wrap real Streamlit widgets (charts, tables) can't be a
   single markdown string, so they use st.container(key="panel-*") and get
   the card treatment through the generated st-key-* class. */
[class*="st-key-panel-"] {{
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 16px 18px;
  transition: border-color 200ms var(--ease);
}}
[class*="st-key-panel-"]:hover {{ border-color: var(--border-hi); }}
[class*="st-key-panel-"] [data-testid="stDataFrame"] {{ border: none; }}

/* ------------------------------------------------------------- misc */

.rt-section {{
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.11em;
  text-transform: uppercase; color: var(--text-3);
  margin: 22px 0 2px;
}}
.rt-gauge-wrap {{
  display: flex; align-items: center; gap: 14px;
}}
.rt-gauge-txt {{ display: flex; flex-direction: column; gap: 3px; }}
.rt-gauge-name {{ font-size: 0.78rem; color: var(--text-2); }}
.rt-gauge-note {{
  font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-3);
}}
.rt-foot {{
  font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-3);
  margin-top: 10px;
}}

/* ------------------------------------------------------------ responsive

   Streamlit only stacks st.columns at true mobile widths, but the sidebar
   takes ~300px — so a 1000px window leaves a four-up KPI row at ~150px per
   tile and the numbers wrap. Stack the panel rows early and let the KPI row
   fall back to two-up before it goes single file. */

@media (max-width: 1180px) {{
  [data-testid="stMainBlockContainer"] {{ padding: 1.25rem 1.25rem 3rem; }}
  [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; }}
  [data-testid="stColumn"] {{
    flex: 1 1 100% !important; min-width: 100% !important; width: 100% !important;
  }}
  [class*="st-key-kpirow"] [data-testid="stColumn"] {{
    flex: 1 1 calc(50% - 0.45rem) !important;
    min-width: calc(50% - 0.45rem) !important; width: auto !important;
  }}
  .rt-hero-value {{ font-size: 1.75rem; }}
  .rt-hero-meta {{ gap: 18px; }}
}}
@media (max-width: 680px) {{
  [class*="st-key-kpirow"] [data-testid="stColumn"] {{
    flex: 1 1 100% !important; min-width: 100% !important;
  }}
  .rt-stat-value {{ font-size: 1.4rem; }}
  .rt-row {{ flex-wrap: wrap; }}
  .rt-row-num {{ text-align: left; }}
}}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.01ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }}
}}
</style>"""
