"""Omnichannel Customer & Demand Intelligence — dashboard home.

Run:  streamlit run app/Home.py
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from common import PALETTE, load_kpis, page, require_db

page("Overview", "🛍️")

st.title("🛍️ Omnichannel Customer & Demand Intelligence")
st.caption(
    "ExaThon India 2026 · Track: *Customers, Channels & Demand* · "
    "One unified Exasol warehouse → forecasting, segmentation, and churn in one place."
)

if not require_db():
    st.stop()

kpis, by_channel = load_kpis()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue (unified)", f"₹{kpis['REVENUE']:,.0f}")
c2.metric("Orders", f"{kpis['ORDERS']:,}")
c3.metric("Customers", f"{kpis['CUSTOMERS']:,}")
c4.metric("Sales lines", f"{kpis['SALES_LINES']:,}")

st.subheader("Where revenue comes from")
left, right = st.columns([2, 3])
with left:
    fig = px.pie(
        by_channel, names="CHANNEL", values="REVENUE", hole=0.55,
        color="CHANNEL", color_discrete_map=PALETTE,
    )
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.dataframe(by_channel, use_container_width=True, hide_index=True)
    st.info(
        "These three channels arrive as **three fragmented feeds** with different "
        "schemas, date formats and revenue conventions. The ETL reconciles them "
        "into one `FACT_SALES` table — so every page below is a single query, not a "
        "data-wrangling project."
    )

st.subheader("The three questions this answers")
a, b, c = st.columns(3)
a.markdown("### 📈 Demand\nHow much of what, where, next 30 days?\n\n→ *Demand Forecast*")
b.markdown("### 👥 Customers\nWho are my best / at-risk segments?\n\n→ *Customer Segments*")
c.markdown("### ⚠️ Retention\nWhich valuable customers will churn?\n\n→ *Churn & CLV*")

st.caption("Use the sidebar to open each module.")
