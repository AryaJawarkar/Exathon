"""Churn probability + CLV, prioritised by risk x value."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from common import load_churn, page, require_db

page("Churn & CLV", "⚠️")
st.title("⚠️ Churn & Lifetime Value")
st.caption("Behavioural features from Exasol → gradient-boosted churn risk, paired with CLV.")

if not require_db():
    st.stop()

df = load_churn()

c1, c2, c3 = st.columns(3)
c1.metric("Customers scored", f"{len(df):,}")
c2.metric("Avg churn risk", f"{df['CHURN_PROB'].mean():.0%}")
c3.metric("CLV at risk (non-low)", f"₹{df.loc[df.RISK_BAND!='Low','CLV'].sum():,.0f}")

st.subheader("Risk vs. value — target the top-right")
fig = px.scatter(
    df, x="CHURN_PROB", y="CLV", color="RISK_BAND",
    color_discrete_map={"Low": "#5fbf7f", "Medium": "#f0994f", "High": "#e05a5a"},
    hover_data=["CUSTOMER_ID", "FREQUENCY", "MONETARY"], opacity=0.6,
)
fig.update_layout(height=420, xaxis_title="Churn probability", yaxis_title="CLV (₹)",
                  margin=dict(t=20, b=10))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Retention priority list (risk × value)")
cols = ["CUSTOMER_ID", "RECENCY_DAYS", "FREQUENCY", "MONETARY",
        "CHURN_PROB", "CLV", "RISK_BAND", "PRIORITY"]
top = df[cols].head(200).copy()
top["CHURN_PROB"] = (top["CHURN_PROB"] * 100).round(1)
st.dataframe(top, use_container_width=True, hide_index=True,
             column_config={"CHURN_PROB": st.column_config.NumberColumn("CHURN_%")})
st.caption(
    f"Churn label = no purchase in {90} days. CLV = monthly margin × 12 months × "
    "retention odds. Spend retention budget top-down this list for best ROI."
)
