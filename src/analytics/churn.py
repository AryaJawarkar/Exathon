"""Churn probability + Customer Lifetime Value (CLV).

Feature engineering runs in Exasol (one GROUP BY over FACT_SALES); a gradient
boosting classifier learns churn from behaviour, and CLV is a transparent
margin * frequency * expected-horizon estimate. The output pairs *risk* with
*value* so retention spend goes where it actually pays back.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import cross_val_predict

from ..config import settings
from ..db import query_df

CHURN_WINDOW_DAYS = 90          # no purchase in this window => churned (label)
ASSUMED_MARGIN = 0.30           # gross margin for CLV
HORIZON_MONTHS = 12

FEATURE_SQL = """
SELECT
    s.CUSTOMER_ID,
    CURRENT_DATE - MAX(s.ORDER_DATE)                 AS RECENCY_DAYS,
    CURRENT_DATE - MIN(s.ORDER_DATE)                 AS TENURE_DAYS,
    COUNT(DISTINCT s.ORDER_ID)                       AS FREQUENCY,
    SUM(s.LINE_REVENUE)                              AS MONETARY,
    AVG(s.LINE_REVENUE)                              AS AVG_LINE,
    COUNT(DISTINCT s.CHANNEL)                        AS CHANNELS_USED,
    SUM(CASE WHEN s.CHANNEL='ONLINE' THEN s.LINE_REVENUE ELSE 0 END)
        / NULLIF(SUM(s.LINE_REVENUE),0)              AS ONLINE_SHARE
FROM {schema}.FACT_SALES s
GROUP BY s.CUSTOMER_ID
HAVING COUNT(DISTINCT s.ORDER_ID) >= 1
"""


def _features() -> pd.DataFrame:
    df = query_df(FEATURE_SQL.format(schema=settings.schema))
    df["ORDERS_PER_MONTH"] = df["FREQUENCY"] / (
        (df["TENURE_DAYS"] / 30).clip(lower=1)
    )
    return df


def score_customers() -> pd.DataFrame:
    df = _features()
    df["CHURNED"] = (df["RECENCY_DAYS"] > CHURN_WINDOW_DAYS).astype(int)

    feats = [
        "RECENCY_DAYS", "TENURE_DAYS", "FREQUENCY", "MONETARY",
        "AVG_LINE", "CHANNELS_USED", "ONLINE_SHARE", "ORDERS_PER_MONTH",
    ]
    X, y = df[feats].fillna(0.0), df["CHURNED"]

    if y.nunique() < 2:
        df["CHURN_PROB"] = y.astype(float)
    else:
        model = HistGradientBoostingClassifier(
            max_depth=4, learning_rate=0.08, random_state=settings.seed
        )
        # out-of-fold probabilities => honest, non-leaky scores
        df["CHURN_PROB"] = cross_val_predict(
            model, X, y, cv=5, method="predict_proba"
        )[:, 1]

    # Transparent CLV: monthly margin * expected active months ahead
    monthly_margin = (df["MONETARY"] / (df["TENURE_DAYS"] / 30).clip(lower=1)) * ASSUMED_MARGIN
    df["CLV"] = (monthly_margin * HORIZON_MONTHS * (1 - df["CHURN_PROB"])).round(0)

    df["RISK_BAND"] = pd.cut(
        df["CHURN_PROB"], [-0.01, 0.33, 0.66, 1.0], labels=["Low", "Medium", "High"]
    )
    df["PRIORITY"] = (df["CHURN_PROB"] * df["CLV"]).round(0)  # risk x value
    return df.sort_values("PRIORITY", ascending=False)


def retention_targets(top_n: int = 100) -> pd.DataFrame:
    """High-value customers at real risk — where retention budget should go."""
    df = score_customers()
    at_risk = df[(df["RISK_BAND"] != "Low") & (df["CLV"] > df["CLV"].median())]
    return at_risk.head(top_n)


if __name__ == "__main__":
    scored = score_customers()
    print(f"Customers scored: {len(scored)}")
    print(f"Mean churn prob : {scored['CHURN_PROB'].mean():.2%}")
    print(f"CLV at risk     : {scored.loc[scored.RISK_BAND!='Low','CLV'].sum():,.0f}")
