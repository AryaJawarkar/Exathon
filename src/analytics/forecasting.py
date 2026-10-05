"""Demand forecasting per channel / category.

Aggregation (the heavy part) happens in Exasol; Python fits a light, explainable
model (linear trend + weekly + monthly seasonality via one-hot features) and
projects demand forward. Deliberately dependency-light and reproducible.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import OneHotEncoder

from ..config import settings
from ..db import query_df

DAILY_SQL = """
SELECT
    ORDER_DATE,
    {dim} AS SERIES,
    SUM(QUANTITY)     AS UNITS,
    SUM(LINE_REVENUE) AS REVENUE
FROM {schema}.FACT_SALES
GROUP BY ORDER_DATE, {dim}
ORDER BY ORDER_DATE
"""

_DIM = {"channel": "CHANNEL", "category": "P.CATEGORY", "total": "'ALL'"}


def _daily(level: str) -> pd.DataFrame:
    if level == "category":
        sql = """
        SELECT s.ORDER_DATE, p.CATEGORY AS SERIES,
               SUM(s.QUANTITY) AS UNITS, SUM(s.LINE_REVENUE) AS REVENUE
        FROM {schema}.FACT_SALES s
        JOIN {schema}.DIM_PRODUCT p ON p.PRODUCT_ID = s.PRODUCT_ID
        GROUP BY s.ORDER_DATE, p.CATEGORY ORDER BY s.ORDER_DATE
        """.format(schema=settings.schema)
    else:
        sql = DAILY_SQL.format(schema=settings.schema, dim=_DIM[level])
    df = query_df(sql)
    df["ORDER_DATE"] = pd.to_datetime(df["ORDER_DATE"])
    return df


def _features(dates: pd.Series, origin: pd.Timestamp) -> np.ndarray:
    t = (dates - origin).dt.days.to_numpy().reshape(-1, 1)
    dow = dates.dt.dayofweek.to_numpy().reshape(-1, 1)
    month = dates.dt.month.to_numpy().reshape(-1, 1)
    enc = OneHotEncoder(categories=[range(7), range(1, 13)], sparse_output=False)
    seasonal = enc.fit_transform(np.hstack([dow, month]))
    return np.hstack([t, seasonal]), enc


def forecast_series(series_df: pd.DataFrame, horizon: int = 30) -> pd.DataFrame:
    """Fit on one series' history and return history + forecast with a band."""
    s = series_df.sort_values("ORDER_DATE").copy()
    full_idx = pd.date_range(s["ORDER_DATE"].min(), s["ORDER_DATE"].max(), freq="D")
    s = s.set_index("ORDER_DATE").reindex(full_idx).fillna({"UNITS": 0}).rename_axis(
        "ORDER_DATE"
    ).reset_index()

    origin = s["ORDER_DATE"].min()
    X, enc = _features(s["ORDER_DATE"], origin)
    y = s["UNITS"].to_numpy()
    model = Ridge(alpha=1.0).fit(X, y)
    resid_std = float(np.std(y - model.predict(X)))

    future_dates = pd.date_range(
        s["ORDER_DATE"].max() + pd.Timedelta(days=1), periods=horizon, freq="D"
    )
    t = (future_dates - origin).days.to_numpy().reshape(-1, 1)
    seasonal = enc.transform(
        np.hstack(
            [
                future_dates.dayofweek.to_numpy().reshape(-1, 1),
                future_dates.month.to_numpy().reshape(-1, 1),
            ]
        )
    )
    Xf = np.hstack([t, seasonal])
    yhat = np.clip(model.predict(Xf), 0, None)

    hist = pd.DataFrame(
        {"ORDER_DATE": s["ORDER_DATE"], "UNITS": y, "KIND": "actual"}
    )
    fc = pd.DataFrame(
        {
            "ORDER_DATE": future_dates,
            "UNITS": yhat,
            "LOWER": np.clip(yhat - 1.96 * resid_std, 0, None),
            "UPPER": yhat + 1.96 * resid_std,
            "KIND": "forecast",
        }
    )
    return pd.concat([hist, fc], ignore_index=True)


def forecast(level: str = "channel", horizon: int = 30) -> dict[str, pd.DataFrame]:
    """Return {series_name: history+forecast df} for each series at this level."""
    daily = _daily(level)
    return {
        name: forecast_series(grp, horizon)
        for name, grp in daily.groupby("SERIES")
    }


if __name__ == "__main__":
    out = forecast("channel", horizon=30)
    for name, df in out.items():
        nxt = df[df.KIND == "forecast"]["UNITS"].sum()
        print(f"{name}: next-30-day forecast = {nxt:,.0f} units")
