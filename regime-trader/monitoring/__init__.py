"""Monitoring package: structured logging, live dashboards, and alerts.

Two dashboards share one data source. ``dashboard.py`` renders the terminal
view with rich; ``streamlit_app.py`` renders the web control room from
``theme.py`` (design tokens), ``ui.py`` (components) and ``history.py``
(the rolling snapshot log behind the time-series views).
"""
