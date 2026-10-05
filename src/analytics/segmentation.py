"""RFM customer segmentation — scored entirely in Exasol with window functions.

Python receives only the final, small result set. Recency/Frequency/Monetary
quintiles and the segment label are computed in-database via NTILE, which is
exactly the analytical workload Exasol is built for.
"""
from __future__ import annotations

import pandas as pd

from ..config import settings
from ..db import query_df

RFM_SQL = """
WITH base AS (
    SELECT
        CUSTOMER_ID,
        MAX(ORDER_DATE)                              AS LAST_ORDER,
        COUNT(DISTINCT ORDER_ID)                     AS FREQUENCY,
        SUM(LINE_REVENUE)                            AS MONETARY,
        CURRENT_DATE - MAX(ORDER_DATE)               AS RECENCY_DAYS
    FROM {schema}.FACT_SALES
    GROUP BY CUSTOMER_ID
),
scored AS (
    SELECT
        b.*,
        NTILE(5) OVER (ORDER BY RECENCY_DAYS DESC) AS R,  -- recent = high score
        NTILE(5) OVER (ORDER BY FREQUENCY)         AS F,
        NTILE(5) OVER (ORDER BY MONETARY)          AS M
    FROM base b
)
SELECT
    s.CUSTOMER_ID,
    c.FULL_NAME,
    c.CITY,
    s.RECENCY_DAYS,
    s.FREQUENCY,
    s.MONETARY,
    s.R, s.F, s.M,
    (s.R + s.F + s.M)                               AS RFM_SCORE,
    CASE
        WHEN s.R >= 4 AND s.F >= 4 AND s.M >= 4 THEN 'Champions'
        WHEN s.R >= 4 AND s.F >= 3               THEN 'Loyal'
        WHEN s.R >= 4 AND s.F <= 2               THEN 'New / Promising'
        WHEN s.R = 3                             THEN 'Needs Attention'
        WHEN s.R <= 2 AND s.M >= 4               THEN 'At Risk (high value)'
        WHEN s.R <= 2 AND s.F >= 3               THEN 'Hibernating'
        ELSE 'Lost'
    END                                            AS SEGMENT
FROM scored s
JOIN {schema}.DIM_CUSTOMER c ON c.CUSTOMER_ID = s.CUSTOMER_ID
"""


def rfm_table() -> pd.DataFrame:
    return query_df(RFM_SQL.format(schema=settings.schema))


def segment_summary() -> pd.DataFrame:
    df = rfm_table()
    summary = (
        df.groupby("SEGMENT")
        .agg(
            CUSTOMERS=("CUSTOMER_ID", "count"),
            AVG_RECENCY=("RECENCY_DAYS", "mean"),
            AVG_FREQUENCY=("FREQUENCY", "mean"),
            TOTAL_MONETARY=("MONETARY", "sum"),
        )
        .reset_index()
        .sort_values("TOTAL_MONETARY", ascending=False)
    )
    summary["REVENUE_SHARE_%"] = (
        100 * summary["TOTAL_MONETARY"] / summary["TOTAL_MONETARY"].sum()
    ).round(1)
    return summary


if __name__ == "__main__":
    print(segment_summary().to_string(index=False))
