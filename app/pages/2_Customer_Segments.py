"""RFM customer segmentation."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from common import load_rfm, page, require_db

page("Customer Segments", "👥")
st.title("👥 Customer Segments (RFM)")
st.caption("Recency / Frequency / Monetary quintiles scored in Exasol with NTILE.")

if not require_db():
    st.stop()

rfm, summary = load_rfm()

c1, c2, c3 = st.columns(3)
champions = summary.loc[summary.SEGMENT == "Champions", "CUSTOMERS"].sum()
at_risk = summary.loc[summary.SEGMENT.str.startswith("At Risk"), "TOTAL_MONETARY"].sum()
c1.metric("Segments", summary.shape[0])
c2.metric("Champions", f"{int(champions):,}")
c3.metric("Revenue in 'At Risk (high value)'", f"₹{at_risk:,.0f}")

left, right = st.columns([3, 2])
with left:
    fig = px.bar(summary, x="SEGMENT", y="TOTAL_MONETARY", color="SEGMENT",
                 text="REVENUE_SHARE_%")
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(showlegend=False, height=380, xaxis_title="",
                      yaxis_title="Revenue", margin=dict(t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.dataframe(summary, use_container_width=True, hide_index=True)

st.subheader("Explore customers")
seg = st.selectbox("Segment", ["(all)"] + list(summary.SEGMENT))
view = rfm if seg == "(all)" else rfm[rfm.SEGMENT == seg]
st.dataframe(
    view.sort_values("RFM_SCORE", ascending=False)[
        ["CUSTOMER_ID", "FULL_NAME", "CITY", "RECENCY_DAYS",
         "FREQUENCY", "MONETARY", "RFM_SCORE", "SEGMENT"]
    ].head(500),
    use_container_width=True, hide_index=True,
)
st.caption(
    "Actionable cuts: win-back offers for *At Risk (high value)*, VIP perks for "
    "*Champions*, onboarding nudges for *New / Promising*."
)
