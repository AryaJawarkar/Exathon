"""Shared dashboard helpers: path bootstrap, cached loaders, connection guard."""
from __future__ import annotations

import sys
from pathlib import Path

# Make `src` importable when launched via `streamlit run app/Home.py`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from src.db import ping  # noqa: E402

PALETTE = {
    "ONLINE": "#4f8bf0",
    "STORE": "#f0994f",
    "MARKETPLACE": "#5fbf7f",
}


def page(title: str, icon: str) -> None:
    st.set_page_config(page_title=f"{title} · Omnichannel IQ", page_icon=icon, layout="wide")


def require_db() -> bool:
    """Render a friendly setup panel if Exasol is unreachable; return False then."""
    if ping():
        return True
    st.error("Not connected to Exasol.")
    st.markdown(
        """
        **Get the data flowing (one time):**
        ```bash
        docker compose up -d            # start Exasol Personal (first boot ~2-3 min)
        pip install -r requirements.txt
        cp .env.example .env
        python -m src.data.generate_synthetic_data
        python -m src.etl.load
        ```
        Then refresh this page.
        """
    )
    return False


@st.cache_data(ttl=600, show_spinner="Querying Exasol…")
def load_rfm():
    from src.analytics.segmentation import rfm_table, segment_summary

    return rfm_table(), segment_summary()


@st.cache_data(ttl=600, show_spinner="Forecasting demand…")
def load_forecast(level: str, horizon: int):
    from src.analytics.forecasting import forecast

    return forecast(level, horizon)


@st.cache_data(ttl=600, show_spinner="Scoring customers…")
def load_churn():
    from src.analytics.churn import score_customers

    return score_customers()


@st.cache_data(ttl=600, show_spinner="Loading KPIs…")
def load_kpis():
    from src.config import settings
    from src.db import query_df

    sql = f"""
        SELECT
            COUNT(*)                       AS SALES_LINES,
            COUNT(DISTINCT CUSTOMER_ID)    AS CUSTOMERS,
            COUNT(DISTINCT ORDER_ID)       AS ORDERS,
            ROUND(SUM(LINE_REVENUE),0)     AS REVENUE
        FROM {settings.schema}.FACT_SALES
    """
    by_channel = query_df(
        f"""SELECT CHANNEL, ROUND(SUM(LINE_REVENUE),0) AS REVENUE,
                   COUNT(DISTINCT ORDER_ID) AS ORDERS
            FROM {settings.schema}.FACT_SALES GROUP BY CHANNEL ORDER BY REVENUE DESC"""
    )
    return query_df(sql).iloc[0], by_channel
