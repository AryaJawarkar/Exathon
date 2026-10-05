"""Demand forecasting by channel or category."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from common import PALETTE, load_forecast, page, require_db

page("Demand Forecast", "📈")
st.title("📈 Demand Forecast")
st.caption("Daily units aggregated in Exasol, projected forward with a seasonal model.")

if not require_db():
    st.stop()

col1, col2 = st.columns(2)
level = col1.selectbox("Break down by", ["channel", "category", "total"], index=0)
horizon = col2.slider("Forecast horizon (days)", 7, 90, 30, step=7)

series = load_forecast(level, horizon)
names = sorted(series.keys())
chosen = st.multiselect("Series", names, default=names[: min(3, len(names))])

if not chosen:
    st.info("Pick at least one series.")
    st.stop()

tab_chart, tab_table = st.tabs(["Chart", "Forecast totals"])

with tab_chart:
    for name in chosen:
        df = series[name]
        hist = df[df.KIND == "actual"]
        fc = df[df.KIND == "forecast"]
        color = PALETTE.get(name, "#8884d8")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.ORDER_DATE, y=hist.UNITS, name="actual",
                                 line=dict(color=color, width=1.3)))
        fig.add_trace(go.Scatter(x=fc.ORDER_DATE, y=fc.UNITS, name="forecast",
                                 line=dict(color=color, dash="dash", width=2)))
        fig.add_trace(go.Scatter(
            x=list(fc.ORDER_DATE) + list(fc.ORDER_DATE[::-1]),
            y=list(fc.UPPER) + list(fc.LOWER[::-1]),
            fill="toself", fillcolor="rgba(120,120,160,0.15)",
            line=dict(width=0), name="95% band", hoverinfo="skip",
        ))
        fig.update_layout(title=f"{name}", height=300,
                          margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

with tab_table:
    rows = []
    for name in chosen:
        fc = series[name][series[name].KIND == "forecast"]
        rows.append({"Series": name,
                     f"Next {horizon}d units": round(fc.UNITS.sum()),
                     "Avg/day": round(fc.UNITS.mean(), 1)})
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption("Use these to drive purchase orders and channel-level inventory splits.")
